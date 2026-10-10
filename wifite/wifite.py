#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from .config import Configuration
except (ValueError, ImportError) as e:
    raise Exception("You may need to run wifite from the root directory (which includes README.md)", e) from e


from .util.color import Color

import os
import sys


class Wifite:

    def __init__(self):
        """
        Initializes Wifite.
        Checks that its running under *nix, with root permissions and ensures dependencies are installed.
        """

        self.print_banner()

        Configuration.initialize(load_interface=False)

        # Initialize TUI logger if debug mode is enabled
        from .util.tui_logger import TUILogger
        if hasattr(Configuration, 'tui_debug') and Configuration.tui_debug:
            TUILogger.initialize(enabled=True, debug_mode=True)

        # Initialize output manager based on configuration
        from .util.output import OutputManager
        if Configuration.use_tui is True:
            OutputManager.initialize('tui')
        else:
            # Default to classic mode (use_tui is False or None)
            OutputManager.initialize('classic')

        # If --syscheck, run the comprehensive check and exit
        if Configuration.syscheck:
            from .util.system_check import run_system_check
            smoke_test = Configuration.verbose > 0
            run_system_check(verbose=Configuration.verbose, smoke_test=smoke_test)
            raise SystemExit(0)

        if os.name == 'nt':
            Color.pl('{!} {R}error: {O}wifite{R} must be run under a {O}*NIX{W}{R} like OS')
            Configuration.exit_gracefully()
        if os.getuid() != 0:
            Color.pl('{!} {R}error: {O}wifite{R} must be run as {O}root{W}')
            Color.pl('{!} {R}re-run with {O}sudo{W}')
            Configuration.exit_gracefully()

        from .tools.dependency import Dependency
        Dependency.run_dependency_check()

        # Emit startup debug summary when verbose
        if Configuration.verbose >= 2:
            from .util.logger import log_info
            import platform
            log_info('Wifite', 'wifite %s on Python %s (%s %s)' % (
                Configuration.version, platform.python_version(),
                platform.system(), platform.release()))
            log_info('Wifite', 'verbose=%d interface=%s' % (
                Configuration.verbose, Configuration.interface or '(auto)'))

        # Automatic cleanup of old session files on startup
        self.cleanup_old_sessions()

        # Initialize interface assignment storage
        self.interface_assignment = None
        self.available_interfaces = []

        # Initialize interface manager for state tracking and cleanup (Task 10.4)
        from .util.interface_manager import InterfaceManager
        self.interface_manager = InterfaceManager()
        # Store in Configuration for cleanup access
        Configuration.interface_manager = self.interface_manager

    def start(self):
        """
        Starts target-scan + attack loop, or launches utilities depending on user input.
        """
        from .model.result import CrackResult
        from .model.handshake import Handshake
        from .util.crack import CrackHelper
        from .util.dbupdater import DBUpdater

        # Handle session cleanup
        if Configuration.clean_sessions:
            self.clean_sessions()
            return

        # Handle session resume
        if Configuration.resume or Configuration.resume_latest or Configuration.resume_id:
            self.resume_session()
            return

        if Configuration.show_cracked:
            CrackResult.display('cracked')

        elif Configuration.show_ignored:
            CrackResult.display('ignored')

        elif Configuration.check_handshake:
            Handshake.check()

        elif Configuration.crack_handshake:
            CrackHelper.run()

        elif Configuration.update_db:
            DBUpdater.run()

        elif Configuration.wpa3_check_dragonblood:
            # Dragonblood vulnerability scan mode
            Configuration.get_monitor_mode_interface()
            self.dragonblood_scan()

        elif hasattr(Configuration, 'owe_scan') and Configuration.owe_scan:
            # OWE transition mode vulnerability scan
            Configuration.get_monitor_mode_interface()
            self.owe_scan()

        elif Configuration.pmkid_passive:
            # Passive PMKID capture mode
            # Enable TUI by default for passive PMKID unless explicitly disabled
            if Configuration.use_tui is None:
                Configuration.use_tui = True
            Configuration.get_monitor_mode_interface()
            self.passive_pmkid_capture()

        elif Configuration.monitor_attacks:
            # Wireless attack monitoring mode
            # Enable TUI by default for attack monitoring unless explicitly disabled
            if Configuration.use_tui is None:
                Configuration.use_tui = True
            Configuration.get_monitor_mode_interface()
            self.monitor_wireless_attacks()

        else:
            Configuration.get_monitor_mode_interface()
            self.scan_and_attack()

    @staticmethod
    def cleanup_old_sessions():
        """Automatically cleanup old session files on startup (silent)."""
        try:
            from .util.session import SessionManager
            session_mgr = SessionManager()
            deleted = session_mgr.cleanup_old_sessions(days=7)

            # Only log if verbose mode is enabled and sessions were deleted
            if deleted > 0 and Configuration.verbose > 0:
                Color.pl('{+} {D}Cleaned up {C}%d{D} old session file(s){W}' % deleted)
        except Exception as e:
            # Log cleanup errors but don't block startup
            if Configuration.verbose > 0:
                Color.pl('{!} {O}Session cleanup error: %s{W}' % str(e))

    def detect_and_assign_interfaces(self, attack_type='wpa'):
        """
        Detect available interfaces and assign them for the specified attack type.
        
        Args:
            attack_type: Type of attack ('evil_twin', 'wpa', 'wps')
            
        Returns:
            InterfaceAssignment or None if assignment fails
        """
        from .util.interface_manager import InterfaceManager
        from .util.interface_assignment import InterfaceAssignmentStrategy
        from .util.logger import log_info, log_warning, log_error
        
        try:
            # Detect available interfaces
            log_info('Wifite', 'Detecting available wireless interfaces...')
            self.available_interfaces = InterfaceManager.get_available_interfaces()
            
            if not self.available_interfaces:
                log_warning('Wifite', 'No wireless interfaces detected')
                return None
            
            log_info('Wifite', f'Found {len(self.available_interfaces)} wireless interface(s)')
            
            # Determine if dual interface mode should be used
            use_dual_interface = self._should_use_dual_interface()
            
            if not use_dual_interface:
                log_info('Wifite', 'Dual interface mode disabled, using single interface')
                return None
            
            # Validate and prepare interfaces for dual interface mode ONCE at startup
            if not self._validate_and_prepare_dual_interfaces():
                log_warning('Wifite', 'Dual interface validation failed, falling back to single interface')
                self.fallback_to_single_interface()
                return None
            
            # Get interface assignment based on attack type
            assignment = None
            if attack_type == 'evil_twin':
                assignment = InterfaceAssignmentStrategy.assign_for_evil_twin(self.available_interfaces)
            elif attack_type == 'wpa':
                assignment = InterfaceAssignmentStrategy.assign_for_wpa(self.available_interfaces)
            elif attack_type == 'wps':
                assignment = InterfaceAssignmentStrategy.assign_for_wps(self.available_interfaces)
            else:
                # Default to WPA assignment
                assignment = InterfaceAssignmentStrategy.assign_for_wpa(self.available_interfaces)
            
            if assignment:
                log_info('Wifite', f'Interface assignment: {assignment.get_assignment_summary()}')
                self.interface_assignment = assignment
                
                # Validate the assignment
                is_valid, error_msg, warnings = self.validate_interface_assignment()
                
                # Display validation results
                self.display_validation_results(is_valid, error_msg, warnings)
                
                if not is_valid:
                    log_error('Wifite', f'Interface assignment validation failed: {error_msg}')
                    log_info('Wifite', 'Falling back to single interface mode due to validation failure')
                    self.fallback_to_single_interface()
                    return None
                
                if warnings:
                    log_warning('Wifite', f'Interface assignment has {len(warnings)} warning(s)')
                    for warning in warnings:
                        log_warning('Wifite', f'  - {warning}')
                
                # Display interface assignment to user
                self.display_interface_assignment()
                log_info('Wifite', f'Interface assignment validated successfully for {attack_type} attack')
            else:
                log_warning('Wifite', f'Could not assign interfaces for {attack_type} attack')
                # Attempt fallback to single interface mode
                self.fallback_to_single_interface()
            
            return assignment
            
        except Exception as e:
            log_error('Wifite', f'Error during interface detection/assignment: {e}')
            if Configuration.verbose > 0:
                import traceback
                log_error('Wifite', traceback.format_exc())
            # Attempt fallback on error
            self.fallback_to_single_interface()
            return None
    
    def _validate_and_prepare_dual_interfaces(self):
        """
        Validate that interfaces can enter monitor mode and prepare them for dual interface attacks.
        This is done ONCE at startup to avoid repeated testing for each target.
        
        Returns:
            bool: True if interfaces are ready for dual interface mode
        """
        from .util.interface_manager import InterfaceManager
        from .util.color import Color
        from .util.logger import log_info
        
        # Need at least 2 interfaces for dual mode
        if len(self.available_interfaces) < 2:
            return False
        
        Color.pl('{+} {C}Validating interfaces for dual interface mode...{W}')
        
        # Test monitor mode capability on all interfaces
        valid_interfaces = []
        for iface_info in self.available_interfaces:
            iface_name = iface_info.name
            
            # Check if interface supports monitor mode
            if not InterfaceManager.check_monitor_mode_support(iface_name):
                Color.pl('{!} {O}Interface {R}%s{O} does not support monitor mode{W}' % iface_name)
                Color.pl('{!} {O}  Capabilities: %s{W}' % iface_info.get_capability_summary())
                Color.pl('{!} {O}  Driver: %s, Chipset: %s{W}' % (iface_info.driver, iface_info.chipset))
                Color.pl('{!} {O}  Suggestion: Use a different wireless adapter or check driver support{W}')
                continue
            
            # In verbose mode, actually test monitor mode
            if Configuration.verbose > 0:
                Color.pl('{+} {C}Testing monitor mode on {G}%s{W}...' % iface_name)
                if not InterfaceManager.test_monitor_mode(iface_name):
                    Color.pl('{!} {R}Monitor mode test failed on {O}%s{W}' % iface_name)
                    Color.pl('{!} {O}  Driver: %s, Chipset: %s{W}' % (iface_info.driver, iface_info.chipset))
                    Color.pl('{!} {O}  Suggestion: Check if driver is properly installed or try updating firmware{W}')
                    continue
                Color.pl('{+} {G}Monitor mode test passed on {G}%s{W}' % iface_name)
            
            valid_interfaces.append(iface_info)
        
        # Update available interfaces to only include valid ones
        self.available_interfaces = valid_interfaces
        
        if len(valid_interfaces) < 2:
            Color.pl('{!} {R}Not enough monitor-capable interfaces for dual interface mode{W}')
            Color.pl('{!} {O}Need 2 interfaces, found %d{W}' % len(valid_interfaces))
            Color.pl('{!} {O}Suggestion: Connect another wireless adapter or disable dual interface mode{W}')
            Color.pl('{!} {O}  To disable: Use --no-dual-interface flag{W}')
            return False
        
        Color.pl('{+} {G}Found %d monitor-capable interface(s) for dual interface mode{W}' % len(valid_interfaces))
        log_info('Wifite', f'Validated {len(valid_interfaces)} interfaces for dual interface mode')
        
        return True
    
    def _should_use_dual_interface(self):
        """
        Determine if dual interface mode should be used based on configuration and available interfaces.
        
        Returns:
            bool: True if dual interface mode should be used
        """
        # Check if explicitly disabled
        if Configuration.dual_interface_enabled is False:
            return False
        
        # Check if explicitly enabled
        if Configuration.dual_interface_enabled is True:
            return True
        
        # Check if manual interfaces specified
        if Configuration.interface_primary or Configuration.interface_secondary:
            return True
        
        # Check if we have enough interfaces and prefer dual mode
        if len(self.available_interfaces) >= 2 and Configuration.prefer_dual_interface:
            return True
        
        return False
    
    def fallback_to_single_interface(self):
        """
        Fallback to single interface mode when dual interface assignment fails.
        Selects the best available interface and configures single interface mode.
        """
        from .util.logger import log_info, log_warning
        
        Color.pl('')
        Color.pl('{!} {O}Dual interface assignment failed{W}')
        Color.pl('{+} {C}Falling back to single interface mode...{W}')
        
        # Clear any existing assignment
        self.interface_assignment = None
        
        # Select best single interface
        best_interface = self._select_best_single_interface()
        
        if not best_interface:
            Color.pl('{!} {R}No suitable interface found for single interface mode{W}')
            log_warning('Wifite', 'No suitable interface found for fallback')
            return
        
        # Set the interface in Configuration
        Configuration.interface = best_interface.name
        
        Color.pl('{+} {C}Selected interface:{W} {G}%s{W}' % best_interface.name)
        Color.pl('{+} {C}Mode:{W} {O}Single Interface{W} (mode switching will be used)')
        
        if best_interface.driver:
            Color.pl('{+} {C}Driver:{W} %s' % best_interface.driver)
        
        Color.pl('{+} {C}Capabilities:{W} %s' % best_interface.get_capability_summary())
        Color.pl('')
        
        log_info('Wifite', f'Fallback to single interface mode using {best_interface.name}')
    
    def _select_best_single_interface(self):
        """
        Select the best single interface from available interfaces.
        Prioritizes interfaces with the most capabilities.
        
        Returns:
            InterfaceInfo object or None if no suitable interface found
        """
        if not self.available_interfaces:
            return None
        
        # Score each interface based on capabilities
        scored_interfaces = []
        for iface in self.available_interfaces:
            score = 0
            
            # Prefer interfaces that are down (easier to configure)
            if not iface.is_up:
                score += 10
            
            # Prefer interfaces with monitor mode support
            if iface.supports_monitor_mode:
                score += 5
            
            # Prefer interfaces with AP mode support
            if iface.supports_ap_mode:
                score += 5
            
            # Prefer interfaces with injection support
            if iface.supports_injection:
                score += 3
            
            # Prefer interfaces that are not connected
            if not iface.is_connected:
                score += 2
            
            scored_interfaces.append((score, iface))
        
        # Sort by score (highest first)
        scored_interfaces.sort(key=lambda x: x[0], reverse=True)
        
        # Return the best interface
        return scored_interfaces[0][1] if scored_interfaces else None
    
    def display_interface_assignment(self):
        """
        Display the current interface assignment to the user.
        Shows primary and secondary interfaces with their roles and capabilities.
        """
        if not self.interface_assignment:
            # Single interface mode
            if Configuration.interface:
                Color.pl('')
                Color.pl('{+} {C}Interface Mode:{W} {O}Single Interface{W}')
                Color.pl('{+} {C}Interface:{W} {G}%s{W}' % Configuration.interface)
                
                # Try to find interface info for capabilities
                interface_info = self._get_interface_info_by_name(Configuration.interface)
                if interface_info:
                    Color.pl('{+} {C}Capabilities:{W} %s' % interface_info.get_capability_summary())
            return
        
        # Dual interface mode
        Color.pl('')
        Color.pl('{+} {C}Interface Mode:{W} {G}Dual Interface{W}')
        Color.pl('{+} {C}Attack Type:{W} {G}%s{W}' % self.interface_assignment.attack_type.upper())
        
        # Display primary interface
        Color.pl('')
        Color.pl('{+} {C}Primary Interface:{W} {G}%s{W}' % self.interface_assignment.primary)
        Color.pl('{+} {C}Role:{W} %s' % self.interface_assignment.primary_role)
        
        primary_info = self._get_interface_info_by_name(self.interface_assignment.primary)
        if primary_info:
            Color.pl('{+} {C}Capabilities:{W} %s' % primary_info.get_capability_summary())
            Color.pl('{+} {C}Status:{W} %s' % primary_info.get_status_summary())
        
        # Display secondary interface if present
        if self.interface_assignment.secondary:
            Color.pl('')
            Color.pl('{+} {C}Secondary Interface:{W} {G}%s{W}' % self.interface_assignment.secondary)
            Color.pl('{+} {C}Role:{W} %s' % self.interface_assignment.secondary_role)
            
            secondary_info = self._get_interface_info_by_name(self.interface_assignment.secondary)
            if secondary_info:
                Color.pl('{+} {C}Capabilities:{W} %s' % secondary_info.get_capability_summary())
                Color.pl('{+} {C}Status:{W} %s' % secondary_info.get_status_summary())
        
        Color.pl('')
    
    def _get_interface_info_by_name(self, interface_name):
        """
        Get InterfaceInfo object for a given interface name.
        
        Args:
            interface_name: Name of the interface
            
        Returns:
            InterfaceInfo object or None if not found
        """
        for iface in self.available_interfaces:
            if iface.name == interface_name:
                return iface
        return None
    
    def validate_interface_assignment(self):
        """
        Validate the current interface assignment before attack execution.
        Checks that interfaces exist, have required capabilities, and displays warnings.
        
        Returns:
            tuple: (is_valid, error_message, warnings)
        """
        from .util.interface_assignment import InterfaceAssignmentStrategy
        from .util.logger import log_warning
        
        warnings = []
        
        # If no assignment, validate single interface mode
        if not self.interface_assignment:
            if not Configuration.interface:
                return False, 'No interface configured. Please specify an interface with -i/--interface', []
            
            # Check if interface exists
            interface_info = self._get_interface_info_by_name(Configuration.interface)
            if not interface_info:
                available = ', '.join([iface.name for iface in self.available_interfaces])
                return False, f'Interface {Configuration.interface} not found. Available interfaces: {available}', []
            
            return True, None, warnings
        
        # Validate dual interface assignment
        assignment = self.interface_assignment
        
        # Check that primary interface exists
        primary_info = self._get_interface_info_by_name(assignment.primary)
        if not primary_info:
            available = ', '.join([iface.name for iface in self.available_interfaces])
            return False, f'Primary interface {assignment.primary} not found. Available interfaces: {available}', warnings
        
        # Check that secondary interface exists (if specified)
        if assignment.secondary:
            secondary_info = self._get_interface_info_by_name(assignment.secondary)
            if not secondary_info:
                available = ', '.join([iface.name for iface in self.available_interfaces])
                return False, f'Secondary interface {assignment.secondary} not found. Available interfaces: {available}', warnings
            
            # Validate dual interface setup
            is_valid, error_msg = InterfaceAssignmentStrategy.validate_dual_interface_setup(
                primary_info, secondary_info
            )
            
            if not is_valid:
                return False, error_msg, warnings
            
            # Check if interfaces are on the same physical device (warning only)
            if primary_info.phy == secondary_info.phy:
                warning = f'Primary and secondary interfaces share the same physical device ({primary_info.phy}). This may cause conflicts.'
                warnings.append(warning)
                log_warning('Wifite', warning)
        
        # Validate capabilities based on attack type
        attack_type = assignment.attack_type
        
        if attack_type == 'evil_twin':
            # Primary should support AP mode
            if not primary_info.supports_ap_mode:
                warning = (f'Primary interface {assignment.primary} may not support AP mode. '
                          f'Evil Twin attack may fail. '
                          f'Suggestion: Use an interface with AP mode support or try single interface mode.')
                warnings.append(warning)
                log_warning('Wifite', warning)
            
            # Secondary should support monitor mode (if present)
            if assignment.secondary and secondary_info:
                if not secondary_info.supports_monitor_mode:
                    warning = (f'Secondary interface {assignment.secondary} may not support monitor mode. '
                              f'Suggestion: Use an interface with monitor mode support.')
                    warnings.append(warning)
                    log_warning('Wifite', warning)
        
        elif attack_type == 'wpa':
            # Both interfaces should support monitor mode
            if not primary_info.supports_monitor_mode:
                warning = (f'Primary interface {assignment.primary} may not support monitor mode. '
                          f'WPA attack may fail. '
                          f'Suggestion: Use an interface with monitor mode support.')
                warnings.append(warning)
                log_warning('Wifite', warning)
            
            if assignment.secondary and secondary_info:
                if not secondary_info.supports_monitor_mode:
                    warning = (f'Secondary interface {assignment.secondary} may not support monitor mode. '
                              f'Suggestion: Use an interface with monitor mode support.')
                    warnings.append(warning)
                    log_warning('Wifite', warning)
        
        # Check injection support
        if not primary_info.supports_injection:
            warning = (f'Primary interface {assignment.primary} may not support packet injection. '
                      f'Attacks requiring deauthentication may fail. '
                      f'Suggestion: Use an interface with packet injection support.')
            warnings.append(warning)
            log_warning('Wifite', warning)
        
        if assignment.secondary and secondary_info and not secondary_info.supports_injection:
            warning = (f'Secondary interface {assignment.secondary} may not support packet injection. '
                      f'Deauthentication attacks may fail. '
                      f'Suggestion: Use an interface with packet injection support.')
            warnings.append(warning)
            log_warning('Wifite', warning)
        
        return True, None, warnings
    
    def display_validation_results(self, is_valid, error_message, warnings):
        """
        Display validation results to the user.
        
        Args:
            is_valid: Whether validation passed
            error_message: Error message if validation failed
            warnings: List of warning messages
        """
        if not is_valid:
            Color.pl('')
            Color.pl('{!} {R}Interface Validation Failed:{W}')
            Color.pl('{!} {R}%s{W}' % error_message)
            Color.pl('')
            return
        
        if warnings:
            Color.pl('')
            Color.pl('{!} {O}Interface Warnings:{W}')
            for warning in warnings:
                Color.pl('{!} {O}• %s{W}' % warning)
            Color.pl('')

    @staticmethod
    def clean_sessions():
        """Clean up old session files (manual command)."""
        from .util.session import SessionManager

        Color.pl('{+} Cleaning up old session files...')

        session_mgr = SessionManager()
        deleted = session_mgr.cleanup_old_sessions(days=7)

        if deleted > 0:
            Color.pl('{+} Deleted {C}%d{W} old session file(s)' % deleted)
        else:
            Color.pl('{+} No old session files to clean up')

    @staticmethod
    def resume_session():
        """Resume a previously interrupted attack session."""
        from .util.session import SessionManager
        from .attack.all import AttackAll

        Color.pl('')
        Color.pl('{+} {C}Resuming previous attack session...{W}')

        session_mgr = SessionManager()

        try:
            # Determine which session to load
            if Configuration.resume_id:
                session = session_mgr.load_session(Configuration.resume_id)
            elif Configuration.resume_latest:
                session = session_mgr.load_session()  # Load latest
            else:
                # List available sessions and let user choose
                sessions = session_mgr.list_sessions()

                if not sessions:
                    Color.pl('{!} {R}No session files found{W}')
                    Color.pl('{!} {O}Start a new attack session first{W}')
                    return

                if len(sessions) == 1:
                    # Only one session, use it
                    session = session_mgr.load_session(sessions[0]['session_id'])
                else:
                    # Multiple sessions, let user choose
                    Color.pl('{+} Found {C}%d{W} session(s):' % len(sessions))
                    for i, s in enumerate(sessions, 1):
                        Color.pl('  {G}%d{W}. %s - {C}%d{W} targets ({G}%d{W} completed, {R}%d{W} failed, {O}%d{W} remaining)' % (
                            i, s['session_id'], s['total_targets'], 
                            s['completed'], s['failed'], s['remaining']
                        ))

                    Color.p('{+} Select session to resume [{G}1{W}]: ')
                    try:
                        choice = input().strip()
                        if not choice:
                            choice = '1'
                        idx = int(choice) - 1
                        if idx < 0 or idx >= len(sessions):
                            Color.pl('{!} {R}Invalid selection{W}')
                            return
                        session = session_mgr.load_session(sessions[idx]['session_id'])
                    except (ValueError, KeyboardInterrupt):
                        Color.pl('\n{!} {O}Cancelled{W}')
                        return

            # Display session information
            summary = session.get_progress_summary()
            Color.pl('')
            Color.pl('{+} {C}Session Information:{W}')
            Color.pl('  {W}Session ID: {C}%s{W}' % session.session_id)
            Color.pl('  {W}Created: {C}%s{W}' % summary['created_at'])
            Color.pl('  {W}Last Updated: {C}%s{W}' % summary['updated_at'])
            Color.pl('  {W}Total Targets: {C}%d{W}' % summary['total'])
            Color.pl('  {W}Completed: {G}%d{W}' % summary['completed'])
            Color.pl('  {W}Failed: {R}%d{W}' % summary['failed'])
            Color.pl('  {W}Remaining: {O}%d{W}' % summary['remaining'])
            Color.pl('  {W}Progress: {C}%.1f%%{W}' % summary['progress_percent'])

            # Display original configuration
            Color.pl('')
            Color.pl('{+} {C}Original Configuration:{W}')
            config = session.config

            # Interface
            if config.get('interface'):
                Color.pl('  {W}Interface: {C}%s{W}' % config['interface'])

            # Attack types
            attack_types = []
            if config.get('wps_pixie'):
                attack_types.append('WPS Pixie')
            if config.get('wps_pin'):
                attack_types.append('WPS PIN')
            if config.get('use_pmkid'):
                attack_types.append('PMKID')
            if not config.get('use_pmkid_only') and not config.get('wps_only'):
                attack_types.append('Handshake')

            if attack_types:
                Color.pl('  {W}Attack Types: {C}%s{W}' % ', '.join(attack_types))

            # Wordlist
            if config.get('wordlist'):
                wordlist = config['wordlist']
                # Shorten path if too long
                if len(wordlist) > 50:
                    wordlist = '...' + wordlist[-47:]
                Color.pl('  {W}Wordlist: {C}%s{W}' % wordlist)

            # Timeout
            if config.get('wpa_attack_timeout'):
                Color.pl('  {W}WPA Timeout: {C}%d{W} seconds' % config['wpa_attack_timeout'])

            # Special modes
            if config.get('infinite_mode'):
                Color.pl('  {W}Mode: {C}Infinite{W}')
            elif config.get('attack_max') and config['attack_max'] > 0:
                Color.pl('  {W}Max Targets: {C}%d{W}' % config['attack_max'])

            Color.pl('')

            if summary['remaining'] == 0:
                Color.pl('{+} {G}All targets in this session have been attacked{W}')
                Color.p('{+} Delete this session? [{G}Y{W}/n]: ')
                try:
                    if input().strip().lower() != 'n':
                        session_mgr.delete_session(session.session_id)
                        Color.pl('{+} Session deleted')
                except KeyboardInterrupt:
                    Color.pl('')
                return

            # Restore configuration from session
            Color.pl('{+} {C}Restoring attack configuration...{W}')
            restore_result = session_mgr.restore_configuration(session, Configuration)

            # Display warnings about configuration restoration
            if restore_result['warnings']:
                Color.pl('')
                Color.pl('{!} {O}Configuration warnings:{W}')
                for warning in restore_result['warnings']:
                    Color.pl('  {O}•{W} %s' % warning)

            # Display conflicts with command-line flags
            if restore_result['conflicts']:
                Color.pl('')
                Color.pl('{!} {O}Command-line flags overridden by session:{W}')
                for conflict in restore_result['conflicts']:
                    Color.pl('  {O}•{W} %s' % conflict)

            if restore_result['warnings'] or restore_result['conflicts']:
                Color.pl('')

            # Confirm resumption
            Color.p('{+} Resume this session? [{G}Y{W}/n]: ')
            try:
                if input().strip().lower() == 'n':
                    Color.pl('{!} {O}Cancelled{W}')
                    return
            except KeyboardInterrupt:
                Color.pl('\n{!} {O}Cancelled{W}')
                return

            # Get remaining targets
            remaining_targets = session_mgr.get_remaining_targets(session)

            if not remaining_targets:
                Color.pl('{!} {O}No remaining targets to attack{W}')
                return

            Color.pl('')
            Color.pl('{+} Resuming attack on {C}%d{W} remaining target(s)...' % len(remaining_targets))

            # Convert TargetState objects back to Target objects
            targets = []
            failed_conversions = []

            for i, target_state in enumerate(remaining_targets, 1):
                try:
                    # Reconstruct Target from TargetState
                    target = Wifite._target_from_state(target_state)
                    targets.append(target)

                    if Configuration.verbose > 0:
                        essid_display = target_state.essid if target_state.essid else '<hidden>'
                        Color.pl('{+} {D}[%d/%d] Restored target: {C}%s{D} ({C}%s{D}){W}' %
                                (i, len(remaining_targets), target_state.bssid, essid_display))
                except Exception as e:
                    failed_conversions.append((target_state.bssid, str(e)))
                    Color.pl('{!} {O}Warning: Could not restore target {C}%s{O}: %s{W}' %
                            (target_state.bssid, str(e)))
                    continue

            if not targets:
                Color.pl('{!} {R}Error: Could not restore any targets from session{W}')
                if failed_conversions:
                    Color.pl('{!} {R}Failed conversions:{W}')
                    for bssid, error in failed_conversions:
                        Color.pl('  {R}•{W} {C}%s{W}: %s' % (bssid, error))
                return

            Color.pl('{+} Successfully restored {G}%d{W} target(s)' % len(targets))
            if failed_conversions:
                Color.pl('{!} {O}Warning: {R}%d{O} target(s) could not be restored{W}' % len(failed_conversions))
            Color.pl('')

            # Attack the remaining targets
            try:
                AttackAll.attack_multiple(targets, session=session, session_mgr=session_mgr)

                # Check if all targets were completed
                final_summary = session.get_progress_summary()
                if final_summary['remaining'] == 0:
                    Color.pl('')
                    Color.pl('{+} {G}Session completed! All targets attacked.{W}')
                    Color.pl('{+} {G}Completed: {C}%d{G}, Failed: {R}%d{W}' % 
                            (final_summary['completed'], final_summary['failed']))
                    session_mgr.delete_session(session.session_id)
                    Color.pl('{+} Session file deleted')
                else:
                    Color.pl('')
                    Color.pl('{+} {O}Session paused. Progress saved.{W}')
                    Color.pl('{+} {G}Completed: {C}%d{G}, Failed: {R}%d{G}, Remaining: {O}%d{W}' % 
                            (final_summary['completed'], final_summary['failed'], final_summary['remaining']))
                    Color.pl('{+} Use {C}--resume{W} to continue later.')

            except KeyboardInterrupt:
                Color.pl('')
                Color.pl('{!} {O}Attack interrupted by user{W}')
                final_summary = session.get_progress_summary()
                Color.pl('{+} {G}Completed: {C}%d{G}, Failed: {R}%d{G}, Remaining: {O}%d{W}' % 
                        (final_summary['completed'], final_summary['failed'], final_summary['remaining']))
                Color.pl('{+} Session saved. Use {C}--resume{O} to continue later.{W}')
            except Exception as e:
                Color.pl('')
                Color.pl('{!} {R}Unexpected error during attack:{W} %s' % str(e))
                if Configuration.verbose > 0:
                    import traceback
                    Color.pl('{!} {D}%s{W}' % traceback.format_exc())
                Color.pl('{+} Session saved. Use {C}--resume{O} to continue later.{W}')

        except FileNotFoundError as e:
            Color.pl('{!} {R}Error:{W} %s' % str(e))
            Color.pl('{!} {O}No session files found to resume{W}')
            Color.pl('{!} {O}Start a new attack session first, then use {C}--resume{O} if interrupted{W}')
        except ValueError as e:
            Color.pl('{!} {R}Corrupted session file:{W} %s' % str(e))
            Color.pl('')
            Color.p('{+} Delete corrupted session? [{G}Y{W}/n]: ')
            try:
                response = input().strip().lower()
                if response != 'n':
                    # Try to delete the corrupted session
                    try:
                        # Determine which session to delete
                        if Configuration.resume_id:
                            session_id = Configuration.resume_id
                        elif Configuration.resume_latest:
                            # Get the latest session ID
                            sessions = session_mgr.list_sessions()
                            if sessions:
                                session_id = sessions[0]['session_id']
                            else:
                                Color.pl('{!} {O}Could not determine session to delete{W}')
                                return
                        else:
                            Color.pl('{!} {O}Could not determine session to delete{W}')
                            return

                        session_mgr.delete_session(session_id)
                        Color.pl('{+} {G}Corrupted session deleted{W}')
                    except Exception as del_error:
                        Color.pl('{!} {R}Failed to delete session:{W} %s' % str(del_error))
                        Color.pl('{!} {O}Use {C}--clean-sessions{O} to manually remove corrupted files{W}')
                else:
                    Color.pl('{!} {O}Session not deleted. Use {C}--clean-sessions{O} to remove it later{W}')
            except KeyboardInterrupt:
                Color.pl('\n{!} {O}Cancelled{W}')
        except PermissionError as e:
            Color.pl('{!} {R}Permission error:{W} %s' % str(e))
            Color.pl('{!} {O}Check file permissions and try again{W}')
        except Exception as e:
            Color.pl('{!} {R}Unexpected error:{W} %s' % str(e))
            if Configuration.verbose > 0:
                import traceback
                Color.pl('{!} {D}%s{W}' % traceback.format_exc())

    @staticmethod
    def _target_from_state(target_state):
        """
        Convert a TargetState object back to a Target object.

        Args:
            target_state: TargetState object from session

        Returns:
            Target object suitable for attacking
        """
        from .model.target import Target

        # Reconstruct the fields array that Target.__init__ expects
        # INDEX KEY             EXAMPLE
        # 0 BSSID           (00:1D:D5:9B:11:00)
        # 1 First time seen (2015-05-27 19:28:43)
        # 2 Last time seen  (2015-05-27 19:28:46)
        # 3 channel         (6)
        # 4 Speed           (54)
        # 5 Privacy         (WPA2 OWE)
        # 6 Cipher          (CCMP TKIP)
        # 7 Authentication  (PSK SAE)
        # 8 Power           (-62)
        # 9 beacons         (2)
        # 10 # IV           (0)
        # 11 LAN IP         (0.  0.  0.  0)
        # 12 ID-length      (9)
        # 13 ESSID          (HOME-ABCD)
        # 14 Key            ()

        # Convert power back to negative if needed (Target adds 100 to negative values)
        power = target_state.power
        if power > 0:
            power = power - 100

        fields = [
            target_state.bssid,                          # 0: BSSID
            '2000-01-01 00:00:00',                       # 1: First time seen (placeholder)
            '2000-01-01 00:00:00',                       # 2: Last time seen (placeholder)
            str(target_state.channel),                   # 3: channel
            '54',                                        # 4: Speed (placeholder)
            target_state.encryption,                     # 5: Privacy/Encryption
            'CCMP',                                      # 6: Cipher (placeholder)
            '',                                          # 7: Authentication (will be derived from encryption)
            str(power),                                  # 8: Power
            '10',                                        # 9: beacons (placeholder)
            '0',                                         # 10: IV (placeholder)
            '0.  0.  0.  0',                            # 11: LAN IP (placeholder)
            str(len(target_state.essid)) if target_state.essid else '0',  # 12: ID-length
            target_state.essid if target_state.essid else '',              # 13: ESSID
            ''                                           # 14: Key (empty)
        ]

        # Derive authentication from encryption if not stored separately
        # This matches the logic in Target.__init__
        if 'SAE' in target_state.encryption or 'WPA3' in target_state.encryption:
            fields[7] = 'SAE'
        elif 'PSK' in target_state.encryption or 'WPA' in target_state.encryption:
            fields[7] = 'PSK'
        elif 'OWE' in target_state.encryption:
            fields[7] = 'OWE'
        else:
            fields[7] = 'PSK'  # Default

        target = Target(fields)

        # Restore WPS state if available
        if target_state.wps:
            from .model.target import WPSState
            target.wps = WPSState.UNLOCKED

        return target

    @staticmethod
    def print_banner():
        """Displays ASCII art of the highest caliber."""
        Color.pl(r' {G}  .     {C}{D}  ·  {W}{G}     .    {W}')
        Color.pl(r' {G}.´  ·  .{C}{D} · · {W}{G}.  ·  `.  {G}wifite2 {D}%s{W}' % Configuration.version)
        Color.pl(r' {G}:  :  : {C}{D}((·)){W}{G} :  :  :  {W}{D}a wireless auditor by {C}derv82{W}')
        Color.pl(r' {G}`.  ·  `{GR}{D} /│\ {W}{G}´  ·  .´  {W}{D}maintained by {C}kimocoder{W}')
        Color.pl(r' {G}  `     {GR}{D}/─┴─\{W}{G}     ´    {C}{D}https://github.com/kimocoder/wifite2{W}')
        Color.pl('')

    def dragonblood_scan(self):
        """
        Scan for Dragonblood vulnerabilities in WPA3 networks.
        Detection only - no attacks performed.
        """
        from .util.scanner import Scanner
        from .util.dragonblood_scanner import DragonbloodScanner

        Color.pl('')
        Color.pl('{+} {C}Dragonblood Vulnerability Scanner{W}')
        Color.pl('{+} {O}Detection mode - no attacks will be performed{W}')
        Color.pl('')

        # Scan for targets
        s = Scanner()
        s.find_targets()

        # Get all targets (don't ask user to select)
        targets = s.get_all_targets()

        if not targets:
            Color.pl('{!} {R}No targets found{W}')
            return

        # Scan for Dragonblood vulnerabilities
        results = DragonbloodScanner.scan_targets(targets)

        # Display summary
        Color.pl('')
        if results['vulnerable_count'] > 0:
            Color.pl('{!} {O}Found {R}%d{O} vulnerable network(s){W}' % results['vulnerable_count'])
            Color.pl('{!} {O}Consider updating firmware on vulnerable devices{W}')
            Color.pl('{!} {O}Reference: {C}https://wpa3.mathyvanhoef.com/{W}')
        else:
            Color.pl('{+} {G}No Dragonblood vulnerabilities detected{W}')

        Color.pl('')

    def owe_scan(self):
        """
        Scan for OWE transition mode vulnerabilities.
        Detection only - no attacks performed.
        """
        from .util.scanner import Scanner
        from .util.owe_scanner import OWEScanner

        Color.pl('')
        Color.pl('{+} {C}OWE Transition Mode Vulnerability Scanner{W}')
        Color.pl('{+} {O}Detection mode - no attacks will be performed{W}')
        Color.pl('')

        # Scan for targets
        s = Scanner()
        s.find_targets()

        # Get all targets (don't ask user to select)
        targets = s.get_all_targets()

        if not targets:
            Color.pl('{!} {R}No targets found{W}')
            return

        # Scan for OWE vulnerabilities
        results = OWEScanner.scan_targets(targets)

        # Display summary
        Color.pl('')
        if results['vulnerable_count'] > 0:
            Color.pl('{!} {O}Found {R}%d{O} vulnerable network(s){W}' % results['vulnerable_count'])
            Color.pl('{!} {O}Recommendation: Disable Open mode on OWE networks{W}')
            Color.pl('{!} {O}Reference: {C}RFC 8110 - Opportunistic Wireless Encryption{W}')
        else:
            Color.pl('{+} {G}No OWE transition mode vulnerabilities detected{W}')

        Color.pl('')

    def passive_pmkid_capture(self):
        """
        Run passive PMKID capture mode.
        Continuously monitors all nearby networks and collects PMKID hashes.
        """
        from .attack.pmkid_passive import AttackPassivePMKID

        # Only show startup messages in classic mode
        if not Configuration.use_tui:
            Color.pl('')
            Color.pl('{+} {C}Starting Passive PMKID Capture Mode{W}')
            Color.pl('{+} {O}This will monitor all networks without deauthentication{W}')
            Color.pl('')

        try:
            # Create TUI controller if not in classic mode
            tui_controller = None
            if Configuration.use_tui:
                try:
                    from .ui.tui import TUIController
                    tui_controller = TUIController()
                except (ImportError, Exception) as e:
                    # Fall back to classic mode if TUI fails to load
                    Color.pl('{!} {O}Warning: TUI mode failed to load, using classic mode{W}')
                    if Configuration.verbose > 0:
                        Color.pl('{!} {O}TUI Error: %s{W}' % str(e))
                    Configuration.use_tui = False

            # Create and run passive PMKID attack
            attack = AttackPassivePMKID(tui_controller=tui_controller)
            attack.run()
            
        except KeyboardInterrupt:
            if not Configuration.use_tui:
                Color.pl('')
                Color.pl('{!} {O}Passive capture interrupted by user{W}')
            
        except Exception as e:
            if not Configuration.use_tui:
                Color.pl('')
                Color.pl('{!} {R}Error during passive PMKID capture:{W}')
                Color.pl('{!} {R}%s{W}' % str(e))
                
                if Configuration.verbose > 0:
                    import traceback
                    Color.pl('')
                    Color.pl('{!} {D}Stack trace:{W}')
                    Color.pl('{D}%s{W}' % traceback.format_exc())
                
                Color.pl('')
                Color.pl('{!} {O}Passive capture failed. Check that:{W}')
                Color.pl('{!} {O}  • hcxdumptool and hcxpcapngtool are installed{W}')
                Color.pl('{!} {O}  • Your wireless interface supports monitor mode{W}')
                Color.pl('{!} {O}  • You have sufficient permissions (running as root){W}')
            else:
                # In TUI mode, error is already logged by the attack
                pass

    def monitor_wireless_attacks(self):
        """
        Run wireless attack monitoring mode.
        Passively monitors for deauthentication and disassociation attacks.
        """
        from .attack.attack_monitor import AttackMonitor

        # Display startup messages
        if not Configuration.use_tui:
            Color.pl('')
            Color.pl('{+} {C}Starting Wireless Attack Monitoring{W}')
            Color.pl('{+} {O}This will passively monitor for deauth/disassoc attacks{W}')
            Color.pl('{+} {D}Interface: {C}%s{W}' % Configuration.interface)
            
            # Display monitoring parameters
            if Configuration.monitor_channel:
                Color.pl('{+} {D}Channel: {C}%d{W}' % Configuration.monitor_channel)
            elif Configuration.monitor_hop:
                Color.pl('{+} {D}Channel: {C}Hopping (all 2.4GHz){W}')
            else:
                Color.pl('{+} {D}Channel: {C}Current{W}')
            
            if Configuration.monitor_duration and Configuration.monitor_duration > 0:
                Color.pl('{+} {D}Duration: {C}%d seconds{W}' % Configuration.monitor_duration)
            else:
                Color.pl('{+} {D}Duration: {C}Infinite{W} (press Ctrl+C to stop)')
            
            if Configuration.monitor_log_file:
                Color.pl('{+} {D}Log file: {C}%s{W}' % Configuration.monitor_log_file)
            
            Color.pl('')

        try:
            # Create TUI controller if not in classic mode
            tui_controller = None
            if Configuration.use_tui:
                try:
                    from .ui.tui import TUIController
                    tui_controller = TUIController()
                except (ImportError, Exception) as e:
                    # Fall back to classic mode if TUI fails to load
                    if Configuration.verbose > 0:
                        Color.pl('{!} {O}Warning: TUI mode unavailable, falling back to classic mode{W}')
                        Color.pl('{!} {D}%s{W}' % str(e))
                    Configuration.use_tui = False

            # Create attack monitor
            monitor = AttackMonitor(tui_controller=tui_controller)
            
            # Validate dependencies before starting
            if not monitor.validate_dependencies():
                if not Configuration.use_tui:
                    Color.pl('')
                    Color.pl('{!} {R}Dependency validation failed{W}')
                    Color.pl('{!} {O}Cannot start attack monitoring without required tools{W}')
                return
            
            # Run the monitor
            success = monitor.run()
            
            # Display final summary on exit
            if not Configuration.use_tui and success:
                Color.pl('')
                Color.pl('{+} {G}Attack monitoring completed successfully{W}')

        except KeyboardInterrupt:
            if not Configuration.use_tui:
                Color.pl('')
                Color.pl('{!} {O}Attack monitoring interrupted by user{W}')
                Color.pl('{+} {D}Gracefully shutting down...{W}')

        except Exception as e:
            if not Configuration.use_tui:
                Color.pl('')
                Color.pl('{!} {R}Error during attack monitoring:{W}')
                Color.pl('{!} {R}%s{W}' % str(e))

                if Configuration.verbose > 0:
                    import traceback
                    Color.pl('')
                    Color.pl('{!} {D}Stack trace:{W}')
                    Color.pl('{D}%s{W}' % traceback.format_exc())

                Color.pl('')
                Color.pl('{!} {O}Attack monitoring failed. Check that:{W}')
                Color.pl('{!} {O}  • tshark is installed (apt install tshark){W}')
                Color.pl('{!} {O}  • Your wireless interface supports monitor mode{W}')
                Color.pl('{!} {O}  • You have sufficient permissions (running as root){W}')
                Color.pl('{!} {O}  • The interface is not being used by other processes{W}')
            else:
                # In TUI mode, error is already logged by the monitor
                pass

    def scan_and_attack(self):
        """
        1) Scans for targets, asks user to select targets
        2) Attacks each target
        """
        from .util.scanner import Scanner
        from .attack.all import AttackAll
        from .util.session import SessionManager

        Color.pl('')

        # Detect and assign interfaces before scanning
        # Default to WPA attack type for general scanning
        self.detect_and_assign_interfaces(attack_type='wpa')

        # Validate interface assignment
        is_valid, error_message, warnings = self.validate_interface_assignment()
        self.display_validation_results(is_valid, error_message, warnings)
        
        if not is_valid:
            Color.pl('{!} {R}Cannot proceed with invalid interface configuration{W}')
            Configuration.exit_gracefully()

        # Scan (no signal handler during scanning to allow proper target selection)
        s = Scanner()
        do_continue = s.find_targets()
        targets = s.select_targets()

        # Create session after target selection
        session_mgr = SessionManager()
        session = session_mgr.create_session(targets, Configuration)
        session_mgr.save_session(session)

        Color.pl('{+} Created session {C}%s{W}' % session.session_id)

        # Attack modules handle KeyboardInterrupt properly, no global handler needed

        if Configuration.infinite_mode:
            while do_continue:
                AttackAll.attack_multiple(targets, session, session_mgr)
                do_continue = s.update_targets()
                if not do_continue:
                    break
                targets = s.select_targets()
            attacked_targets = s.get_num_attacked()
        else:
            # Attack
            attacked_targets = AttackAll.attack_multiple(targets, session, session_mgr)

        Color.pl('{+} Finished attacking {C}%d{W} target(s), exiting' % attacked_targets)

        # Delete session on successful completion
        # Only delete if all targets were attacked (completed or failed)
        summary = session.get_progress_summary()
        if summary['remaining'] == 0:
            # All targets were processed, safe to delete session
            try:
                session_mgr.delete_session(session.session_id)
                Color.pl('{+} {G}Session completed and cleaned up{W}')
            except (OSError, IOError) as e:
                Color.pl('{!} {O}Warning: Could not delete session file: %s{W}' % str(e))
            except Exception as e:
                Color.pl('{!} {O}Warning: Unexpected error during session cleanup: %s{W}' % str(e))
        else:
            # Some targets remain, preserve session for resume
            Color.pl('{+} {C}Session preserved for resume{W} ({O}%d{W} target(s) remaining)' % summary['remaining'])
            Color.pl('{+} Use {C}--resume{W} to continue this session')




def force_exit_handler(signum, frame):
    """Force exit on multiple Ctrl+C during cleanup"""
    import sys
    print('\n[!] Force exiting...')
    sys.exit(1)


def emergency_exit(signum, frame):
    """Aggressive exit handler used during final cleanup phase."""
    import sys
    print('\n[!] Emergency exit!')
    sys.exit(1)


def main():
    import subprocess
    import signal as _signal

    _original_sigint = _signal.getsignal(_signal.SIGINT)

    try:
        wifite = Wifite()
        wifite.start()
    except (OSError, IOError) as e:
        Color.pl('\n{!} {R}System Error{W}: %s' % str(e))
        Color.pl('\n{!} {R}Exiting{W}\n')
    except subprocess.CalledProcessError as e:
        Color.pl('\n{!} {R}Command Failed{W}: %s' % str(e))
        Color.pl('\n{!} {R}Exiting{W}\n')
    except PermissionError as e:
        Color.pl('\n{!} {R}Permission Error{W}: %s' % str(e))
        Color.pl('\n{!} {R}Try running with sudo{W}\n')
    except KeyboardInterrupt:
        Color.pl('\n{!} {O}Interrupted, Shutting down...{W}')
        # Second Ctrl+C during cleanup will force-exit immediately
        _signal.signal(_signal.SIGINT, force_exit_handler)
    except Exception as e:
        if 'did not find any wireless interfaces' in str(e):
            Color.pl('\n{!} {R}Exiting{W}\n')
        else:
            Color.pl('\n{!} {R}Unexpected Error{W}: %s' % str(e))
            Color.pexception(e)
        Color.pl('\n{!} {R}Exiting{W}\n')

    finally:
        # Use the module-level emergency_exit during final cleanup phase
        _signal.signal(_signal.SIGINT, emergency_exit)

        # Quick cleanup with short timeouts
        try:
            from .util.process import ProcessManager
            import threading

            # Run cleanup in thread with timeout
            cleanup_thread = threading.Thread(target=ProcessManager().cleanup_all)
            cleanup_thread.daemon = True
            cleanup_thread.start()
            cleanup_thread.join(timeout=3)  # 3 second timeout
        except Exception as e:
            from .util.logger import log_debug
            log_debug('Wifite', f'Cleanup thread error: {e}')
        
        # Clean up managed interfaces (Task 10.4)
        try:
            from .util.logger import log_debug
            
            if hasattr(Configuration, 'interface_manager') and Configuration.interface_manager is not None:
                log_debug('Wifite', 'Cleaning up managed interfaces')
                
                def interface_cleanup():
                    try:
                        Configuration.interface_manager.cleanup_all()
                    except Exception as e:
                        log_debug('Wifite', f'Interface cleanup error: {e}')
                
                import threading
                cleanup_thread = threading.Thread(target=interface_cleanup)
                cleanup_thread.daemon = True
                cleanup_thread.start()
                cleanup_thread.join(timeout=2)  # 2 second timeout
        except Exception as e:
            from .util.logger import log_debug
            log_debug('Wifite', f'Interface cleanup thread error: {e}')

        # Delete Reaver .pcap quickly
        try:
            subprocess.run(["rm", "-f", "reaver_output.pcap"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except Exception as e:
            from .util.logger import log_debug
            log_debug('Wifite', f'Reaver cleanup error: {e}')

        # Try graceful exit with timeout
        try:
            import threading

            def graceful_exit():
                Configuration.exit_gracefully()

            exit_thread = threading.Thread(target=graceful_exit)
            exit_thread.daemon = True
            exit_thread.start()
            exit_thread.join(timeout=2)  # 2 second timeout
        except Exception as e:
            from .util.logger import log_debug
            log_debug('Wifite', f'Exit thread error: {e}')

        # Force exit regardless
        sys.exit(0)


if __name__ == '__main__':
    main()
