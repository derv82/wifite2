#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WPA-SEC uploader utility for wifite2.
Handles uploading captured handshakes to wpa-sec.stanev.org for online cracking.
"""

import os
from ..config import Configuration
from ..util.color import Color
from ..util.logger import log_debug, log_info, log_warning, log_error
from ..tools.wlancap2wpasec import Wlancap2wpasec


class WpaSecUploader:
    """
    Manages wpa-sec.stanev.org upload functionality.
    
    Provides methods for validating configuration, validating capture files,
    prompting users, and orchestrating the upload process.
    """
    
    # Supported capture file formats (wpa-sec only accepts pcap/pcapng)
    SUPPORTED_FORMATS = ['.cap', '.pcap', '.pcapng', '.gz']
    
    @staticmethod
    def _validate_api_key(api_key):
        """
        Validate API key format.
        
        Args:
            api_key (str): API key to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        import re
        
        if not api_key or len(api_key) < 8:
            return False
        
        # API key should contain only alphanumeric characters, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_\-]+$', api_key):
            return False
        
        return True
    
    @staticmethod
    def _validate_url(url):
        """
        Validate URL format.
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        import re
        
        if not url:
            return False
        
        # URL must start with http:// or https://
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))
    
    @staticmethod
    def should_upload():
        """
        Determine if wpa-sec upload should be attempted.
        
        Checks if:
        - wpa-sec is enabled in configuration
        - API key is configured
        - wlancap2wpasec tool exists
        
        Returns:
            bool: True if upload is configured and enabled, False otherwise
            
        Example:
            >>> if WpaSecUploader.should_upload():
            ...     WpaSecUploader.upload_capture(capfile, bssid, essid)
        """
        from datetime import datetime
        
        log_debug('WpaSecUploader', f'Checking upload eligibility at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Check if wpa-sec is enabled
        if not Configuration.wpasec_enabled:
            log_debug('WpaSecUploader', 'Upload check failed: wpa-sec upload disabled in configuration')
            return False
        
        # Check if API key is configured
        if not Configuration.wpasec_api_key:
            log_debug('WpaSecUploader', 'Upload check failed: wpa-sec API key not configured')
            return False
        
        # Check if wlancap2wpasec tool exists
        if not Wlancap2wpasec.exists():
            log_debug('WpaSecUploader', 'Upload check failed: wlancap2wpasec tool not found')
            return False
        
        log_info('WpaSecUploader', 'Upload eligibility check passed - ready to upload')
        return True
    
    @staticmethod
    def validate_capture_file(capfile, bssid=None):
        """
        Validate capture file before upload.
        
        Checks:
        - File exists on filesystem
        - File size is greater than zero
        - File format is supported
        - File contains handshake/PMKID (if bssid provided)
        
        Args:
            capfile (str): Path to capture file
            bssid (str, optional): Target BSSID to verify handshake presence
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
            
        Example:
            >>> is_valid, error = WpaSecUploader.validate_capture_file('handshake.cap', 'AA:BB:CC:DD:EE:FF')
            >>> if not is_valid:
            ...     print(f"Validation failed: {error}")
        """
        from datetime import datetime
        
        log_info('WpaSecUploader', f'Starting capture file validation: {capfile}')
        log_debug('WpaSecUploader', f'Validation timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        if bssid:
            log_debug('WpaSecUploader', f'Target BSSID for validation: {bssid}')
        
        # Check file exists
        if not os.path.exists(capfile):
            error_msg = f'Capture file not found: {capfile}'
            log_warning('WpaSecUploader', f'Validation failed: {error_msg}')
            return False, error_msg
        
        log_debug('WpaSecUploader', 'File existence check: PASSED')
        
        # Check file size is greater than zero
        try:
            file_size = os.path.getsize(capfile)
            if file_size == 0:
                error_msg = f'Capture file is empty: {capfile}'
                log_warning('WpaSecUploader', f'Validation failed: {error_msg}')
                return False, error_msg
            
            log_debug('WpaSecUploader', f'File size check: PASSED ({file_size} bytes)')
        except OSError as e:
            error_msg = f'Cannot read capture file: {str(e)}'
            log_error('WpaSecUploader', f'Validation failed: {error_msg}', e)
            return False, error_msg
        
        # Check file format is supported
        # wpa-sec only accepts pcap/pcapng formats, not hash files like .22000
        if capfile.lower().endswith('.22000'):
            error_msg = 'Hash files (.22000) are not supported by wpa-sec. Only pcap/pcapng formats are accepted.'
            log_warning('WpaSecUploader', f'Validation failed: {error_msg}')
            return False, error_msg
        
        file_ext = None
        for ext in WpaSecUploader.SUPPORTED_FORMATS:
            if capfile.lower().endswith(ext):
                file_ext = ext
                break
        
        if not file_ext:
            error_msg = f'Unsupported file format. Supported formats: {", ".join(WpaSecUploader.SUPPORTED_FORMATS)}'
            log_warning('WpaSecUploader', f'Validation failed: {error_msg}')
            return False, error_msg
        
        log_debug('WpaSecUploader', f'File format check: PASSED (format: {file_ext})')
        
        # Verify file contains handshake/PMKID if bssid provided and file is not .22000
        # .22000 files are PMKID hash files that don't need handshake validation
        # Skip validation for passive captures (bssid='multiple') as they contain PMKIDs, not complete handshakes
        if bssid and bssid != 'multiple' and not capfile.endswith('.22000'):
            try:
                from ..model.handshake import Handshake
                
                log_debug('WpaSecUploader', f'Starting handshake validation for BSSID: {bssid}')
                hs = Handshake(capfile, bssid=bssid)
                
                if not hs.has_handshake():
                    # Handshake validation failed (tshark didn't detect it)
                    # However, tshark can be unreliable - cowpatty/aircrack might still detect it
                    # Log a warning but don't block the upload - let wpa-sec decide
                    #log_warning('WpaSecUploader', f'Handshake validation warning: tshark did not detect handshake for BSSID {bssid}')
                    log_debug('WpaSecUploader', 'Proceeding with upload - wpa-sec will validate the file')
                else:
                    log_debug('WpaSecUploader', 'Handshake validation: PASSED')
            except Exception as e:
                # Don't fail validation if handshake check fails
                # Let wpa-sec determine if the file is valid
                log_warning('WpaSecUploader', f'Handshake validation warning: {str(e)}')
                log_debug('WpaSecUploader', 'Proceeding with upload despite validation warning')
        elif bssid == 'multiple':
            log_debug('WpaSecUploader', 'Skipping handshake validation for passive capture (multiple BSSIDs)')
        else:
            if capfile.endswith('.22000'):
                log_debug('WpaSecUploader', 'Skipping handshake validation for .22000 hash file')
            else:
                log_debug('WpaSecUploader', 'Skipping handshake validation (no BSSID provided)')
        
        log_info('WpaSecUploader', f'Capture file validation: PASSED - {capfile}')
        return True, None
    
    @staticmethod
    def prompt_upload(target_essid, target_bssid):
        """
        Prompt user to upload capture to wpa-sec (interactive mode).
        
        Displays target information and asks user if they want to upload.
        Handles user input (yes/no/skip).
        
        Args:
            target_essid (str): Target network ESSID
            target_bssid (str): Target network BSSID
            
        Returns:
            bool: True if user wants to upload, False otherwise
            
        Example:
            >>> if WpaSecUploader.prompt_upload('MyNetwork', 'AA:BB:CC:DD:EE:FF'):
            ...     # User confirmed upload
            ...     perform_upload()
        """
        from datetime import datetime
        
        log_debug('WpaSecUploader', f'Prompting user for upload confirmation at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        log_debug('WpaSecUploader', f'Target: {target_essid} ({target_bssid})')
        
        # Display target information
        Color.pl('\n{+} {C}wpa-sec upload option{W}')
        Color.pl('{+} Target: {G}%s{W} ({C}%s{W})' % (target_essid, target_bssid))
        Color.pl('{+} Upload capture to {C}wpa-sec.stanev.org{W} for online cracking?')
        
        # Prompt user for input
        try:
            response = input(Color.s('{?} Upload to wpa-sec? [y/N]: ')).strip().lower()
            log_debug('WpaSecUploader', f'User response: "{response}"')
            
            if response in ['y', 'yes']:
                log_info('WpaSecUploader', f'User CONFIRMED upload for {target_essid} ({target_bssid})')
                return True
            else:
                log_info('WpaSecUploader', f'User DECLINED upload for {target_essid} ({target_bssid})')
                return False
                
        except (KeyboardInterrupt, EOFError):
            # User interrupted prompt
            Color.pl('\n{!} {O}Upload prompt interrupted{W}')
            log_info('WpaSecUploader', 'User INTERRUPTED upload prompt (KeyboardInterrupt/EOFError)')
            return False
        except Exception as e:
            # Unexpected error during prompt
            log_error('WpaSecUploader', f'Unexpected error during upload prompt: {str(e)}', e)
            return False
    
    @staticmethod
    def upload_capture(capfile, bssid, essid, capture_type='handshake', view=None):
        """
        Upload capture file to wpa-sec with validation and user feedback.
        
        Main orchestration method that:
        - Validates configuration
        - Validates capture file
        - Prompts user if not in auto mode
        - Performs upload
        - Displays results
        - Handles file removal if configured
        - Logs all attempts
        
        Args:
            capfile (str): Path to capture file
            bssid (str): Target BSSID
            essid (str): Target ESSID
            capture_type (str): Type of capture ('handshake', 'pmkid', 'sae')
            view: Optional TUI view for displaying upload status
            
        Returns:
            bool: True if upload successful, False otherwise
            
        Example:
            >>> success = WpaSecUploader.upload_capture(
            ...     'handshake.cap',
            ...     'AA:BB:CC:DD:EE:FF',
            ...     'MyNetwork',
            ...     capture_type='handshake',
            ...     view=attack_view
            ... )
            >>> if success:
            ...     print("Upload completed successfully")
        """
        from datetime import datetime
        
        try:
            # Log upload attempt with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_info('WpaSecUploader', f'=== Upload Attempt Started at {timestamp} ===')
            log_info('WpaSecUploader', f'Target: {essid} ({bssid})')
            log_info('WpaSecUploader', f'Capture file: {capfile}')
            log_info('WpaSecUploader', f'Capture type: {capture_type}')
            log_debug('WpaSecUploader', f'Auto-upload mode: {Configuration.wpasec_auto_upload}')
            log_debug('WpaSecUploader', f'Remove after upload: {Configuration.wpasec_remove_after_upload}')
            
            # Validate configuration - check specific reasons and provide helpful messages
            log_debug('WpaSecUploader', 'Step 1: Validating configuration')
            
            if not Configuration.wpasec_enabled:
                Color.pl('{!} {O}wpa-sec upload skipped: Feature not enabled{W}')
                Color.pl('{!} {O}Use {C}--wpasec{O} to enable wpa-sec uploads{W}')
                log_info('WpaSecUploader', 'Upload skipped: feature not enabled')
                if view:
                    view.add_log("wpa-sec upload skipped: Feature not enabled")
                return False
            
            log_debug('WpaSecUploader', 'Configuration check: wpasec_enabled = True')
            
            if not Configuration.wpasec_api_key:
                Color.pl('{!} {O}wpa-sec upload skipped: No API key configured{W}')
                Color.pl('{!} {O}Use {C}--wpasec-key <your_api_key>{O} to set your API key{W}')
                Color.pl('{!} {O}Get your API key from: {C}https://wpa-sec.stanev.org{W}')
                log_info('WpaSecUploader', 'Upload skipped: no API key configured')
                if view:
                    view.add_log("wpa-sec upload skipped: No API key configured")
                return False
            
            log_debug('WpaSecUploader', 'Configuration check: API key is configured')
            
            # Validate API key format
            if not WpaSecUploader._validate_api_key(Configuration.wpasec_api_key):
                Color.pl('{!} {R}wpa-sec upload failed: Invalid API key format{W}')
                Color.pl('{!} {O}API key should be alphanumeric and at least 8 characters{W}')
                log_error('WpaSecUploader', 'Validation failed: Invalid API key format')
                return False
            
            log_debug('WpaSecUploader', 'Configuration check: API key format is valid')
            
            # Validate URL format if custom URL is provided
            if Configuration.wpasec_url and Configuration.wpasec_url != 'https://wpa-sec.stanev.org':
                log_debug('WpaSecUploader', f'Validating custom URL: {Configuration.wpasec_url}')
                if not WpaSecUploader._validate_url(Configuration.wpasec_url):
                    Color.pl('{!} {R}wpa-sec upload failed: Invalid URL format{W}')
                    Color.pl('{!} {O}URL must start with http:// or https://{W}')
                    Color.pl('{!} {O}Current URL: {C}%s{W}' % Configuration.wpasec_url)
                    log_error('WpaSecUploader', f'Validation failed: Invalid URL format: {Configuration.wpasec_url}')
                    return False
                log_debug('WpaSecUploader', 'Configuration check: Custom URL format is valid')
            else:
                log_debug('WpaSecUploader', 'Configuration check: Using default wpa-sec URL')
            
            # Validate timeout value
            if Configuration.wpasec_timeout and Configuration.wpasec_timeout <= 0:
                Color.pl('{!} {R}wpa-sec upload failed: Invalid timeout value{W}')
                Color.pl('{!} {O}Timeout must be a positive integer (seconds){W}')
                log_error('WpaSecUploader', f'Validation failed: Invalid timeout: {Configuration.wpasec_timeout}')
                return False
            
            log_debug('WpaSecUploader', f'Configuration check: Timeout = {Configuration.wpasec_timeout}s')
            
            # Check if tool exists
            log_debug('WpaSecUploader', 'Checking if wlancap2wpasec tool exists')
            if not Wlancap2wpasec.exists():
                Color.pl('{!} {O}wpa-sec upload skipped: wlancap2wpasec not found{W}')
                Color.pl('{!} {O}Install with: {C}apt install hcxtools{W}')
                Color.pl('{!} {O}Or visit: {C}https://github.com/ZerBea/hcxtools{W}')
                log_info('WpaSecUploader', 'Upload skipped: wlancap2wpasec tool not found')
                if view:
                    view.add_log("wpa-sec upload skipped: wlancap2wpasec not found")
                return False
            
            log_debug('WpaSecUploader', 'Configuration check: wlancap2wpasec tool found')
            log_info('WpaSecUploader', 'Configuration validation: PASSED')
            
            # Validate capture file using validate_capture_file()
            log_debug('WpaSecUploader', 'Step 2: Validating capture file')
            if view:
                view.add_log("Validating capture file for wpa-sec upload...")
            is_valid, error_msg = WpaSecUploader.validate_capture_file(capfile, bssid)
            if not is_valid:
                Color.pl('{!} {R}wpa-sec upload failed: %s{W}' % error_msg)
                Color.pl('{!} {O}Capture file preserved for manual upload or local cracking{W}')
                log_warning('WpaSecUploader', f'Upload aborted: File validation failed - {error_msg}')
                if view:
                    view.add_log(f"wpa-sec upload failed: {error_msg}")
                return False
            
            log_info('WpaSecUploader', 'Capture file validation: PASSED')
            
            # Prompt user if not in auto mode using prompt_upload()
            if not Configuration.wpasec_auto_upload:
                log_debug('WpaSecUploader', 'Step 3: Prompting user for upload confirmation (interactive mode)')
                if view:
                    view.add_log("Prompting user for wpa-sec upload confirmation...")
                if not WpaSecUploader.prompt_upload(essid, bssid):
                    Color.pl('{!} {O}wpa-sec upload skipped by user{W}')
                    log_info('WpaSecUploader', 'Upload aborted: User declined upload')
                    if view:
                        view.add_log("wpa-sec upload skipped by user")
                    return False
            else:
                log_debug('WpaSecUploader', 'Step 3: Skipping user prompt (auto-upload mode enabled)')
                if view:
                    view.add_log("Auto-uploading to wpa-sec (auto-upload enabled)...")
            
            # Perform upload - call Wlancap2wpasec.upload() with appropriate parameters
            log_debug('WpaSecUploader', 'Step 4: Initiating upload to wpa-sec')
            Color.pl('\n{+} {C}Uploading capture to wpa-sec.stanev.org...{W}')
            log_info('WpaSecUploader', f'Calling wlancap2wpasec tool with file: {capfile}')
            log_debug('WpaSecUploader', f'Upload parameters: url={Configuration.wpasec_url}, timeout={Configuration.wpasec_timeout}s, email={Configuration.wpasec_email}')
            
            if view:
                view.add_log(f"Uploading {capture_type} to wpa-sec.stanev.org...")
                # Update metrics to show upload in progress
                view.update_progress({
                    'metrics': {
                        **view.metrics,
                        'wpa-sec Upload': '⋯ In Progress'
                    }
                })
            
            upload_start_time = datetime.now()
            success, message = Wlancap2wpasec.upload(
                capfile=capfile,
                api_key=Configuration.wpasec_api_key,
                url=Configuration.wpasec_url if Configuration.wpasec_url else None,
                timeout=Configuration.wpasec_timeout if Configuration.wpasec_timeout else None,
                email=Configuration.wpasec_email if Configuration.wpasec_email else None,
                remove_on_success=Configuration.wpasec_remove_after_upload
            )
            upload_end_time = datetime.now()
            upload_duration = (upload_end_time - upload_start_time).total_seconds()
            
            log_debug('WpaSecUploader', f'Upload completed in {upload_duration:.2f} seconds')
            
            # Display upload status and results to user
            if success:
                Color.pl('{+} {G}wpa-sec upload successful!{W}')
                Color.pl('{+} {C}Target: {G}%s{C} ({G}%s{C}){W}' % (essid, bssid))
                Color.pl('{+} {C}File: {G}%s{W}' % capfile)
                Color.pl('{+} {C}Type: {G}%s{W}' % capture_type)
                
                log_info('WpaSecUploader', f'=== Upload SUCCESS at {upload_end_time.strftime("%Y-%m-%d %H:%M:%S")} ===')
                log_info('WpaSecUploader', f'Target: {essid} ({bssid})')
                log_info('WpaSecUploader', f'Capture type: {capture_type}')
                log_info('WpaSecUploader', f'Upload duration: {upload_duration:.2f}s')
                log_debug('WpaSecUploader', f'Server response: {message}')
                
                if view:
                    view.add_log(f"✓ wpa-sec upload successful! ({upload_duration:.1f}s)")
                    # Update metrics to show upload success
                    view.update_progress({
                        'metrics': {
                            **view.metrics,
                            'wpa-sec Upload': '✓ Success'
                        }
                    })
                
                # Handle file removal if configured
                if Configuration.wpasec_remove_after_upload:
                    log_debug('WpaSecUploader', 'Step 5: Removing capture file (remove_after_upload=True)')
                    # Check if file still exists (tool may have already removed it)
                    if os.path.exists(capfile):
                        try:
                            os.remove(capfile)
                            Color.pl('{+} {O}Capture file removed after successful upload{W}')
                            log_info('WpaSecUploader', f'Capture file removed: {capfile}')
                            if view:
                                view.add_log("Capture file removed after upload")
                        except OSError as e:
                            Color.pl('{!} {O}Warning: Could not remove capture file: %s{W}' % str(e))
                            Color.pl('{!} {O}File preserved at: {C}%s{W}' % capfile)
                            log_warning('WpaSecUploader', f'Failed to remove capture file: {str(e)}')
                            if view:
                                view.add_log("Warning: Could not remove capture file")
                    else:
                        Color.pl('{+} {O}Capture file removed by upload tool{W}')
                        log_info('WpaSecUploader', 'Capture file already removed by wlancap2wpasec tool')
                        if view:
                            view.add_log("Capture file removed by upload tool")
                else:
                    log_debug('WpaSecUploader', f'Capture file preserved at: {capfile}')
                
                return True
            else:
                # Display error message with context
                Color.pl('{!} {R}wpa-sec upload failed: %s{W}' % message)
                Color.pl('{!} {O}Capture file preserved at: {C}%s{W}' % capfile)
                
                log_error('WpaSecUploader', f'=== Upload FAILED at {upload_end_time.strftime("%Y-%m-%d %H:%M:%S")} ===')
                log_error('WpaSecUploader', f'Target: {essid} ({bssid})')
                log_error('WpaSecUploader', f'Failure reason: {message}')
                log_error('WpaSecUploader', f'Upload duration: {upload_duration:.2f}s')
                log_debug('WpaSecUploader', f'Capture file preserved at: {capfile}')
                
                if view:
                    view.add_log(f"✗ wpa-sec upload failed: {message}")
                    # Update metrics to show upload failure
                    view.update_progress({
                        'metrics': {
                            **view.metrics,
                            'wpa-sec Upload': '✗ Failed'
                        }
                    })
                
                # Provide helpful troubleshooting hints based on error message
                WpaSecUploader._display_error_hints(message)
                
                return False
                
        except KeyboardInterrupt:
            # User interrupted - preserve capture file and continue
            Color.pl('\n{!} {O}wpa-sec upload interrupted by user{W}')
            Color.pl('{!} {O}Capture file preserved at: {C}%s{W}' % capfile)
            log_info('WpaSecUploader', f'=== Upload INTERRUPTED at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===')
            log_info('WpaSecUploader', f'Target: {essid} ({bssid})')
            log_info('WpaSecUploader', 'Reason: User interrupted (KeyboardInterrupt)')
            log_debug('WpaSecUploader', f'Capture file preserved at: {capfile}')
            if view:
                view.add_log("wpa-sec upload interrupted by user")
                view.update_progress({
                    'metrics': {
                        **view.metrics,
                        'wpa-sec Upload': '⏸ Interrupted'
                    }
                })
            return False
        except OSError as e:
            # File system error - preserve capture file and continue
            Color.pl('{!} {R}wpa-sec upload error: File system error{W}')
            Color.pl('{!} {O}%s{W}' % str(e))
            Color.pl('{!} {O}Capture file preserved at: {C}%s{W}' % capfile)
            log_error('WpaSecUploader', f'=== Upload ERROR at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===')
            log_error('WpaSecUploader', f'Target: {essid} ({bssid})')
            log_error('WpaSecUploader', 'Error type: File system error (OSError)', e)
            log_debug('WpaSecUploader', f'Capture file preserved at: {capfile}')
            return False
        except Exception as e:
            # Unexpected error - preserve capture file and continue
            Color.pl('{!} {R}wpa-sec upload error: %s{W}' % str(e))
            Color.pl('{!} {O}Capture file preserved at: {C}%s{W}' % capfile)
            log_error('WpaSecUploader', f'=== Upload ERROR at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===')
            log_error('WpaSecUploader', f'Target: {essid} ({bssid})')
            log_error('WpaSecUploader', f'Error type: Unexpected exception ({type(e).__name__})', e)
            log_debug('WpaSecUploader', f'Capture file preserved at: {capfile}')
            
            if view:
                view.add_log(f"✗ wpa-sec upload error: {str(e)}")
                view.update_progress({
                    'metrics': {
                        **view.metrics,
                        'wpa-sec Upload': '✗ Error'
                    }
                })
            
            if Configuration.verbose > 0:
                import traceback
                Color.pl('{!} {R}%s{W}' % traceback.format_exc())
                log_debug('WpaSecUploader', f'Full traceback:\n{traceback.format_exc()}')
            
            return False
    
    @staticmethod
    def _display_error_hints(error_message):
        """
        Display helpful troubleshooting hints based on error message.
        
        Args:
            error_message (str): Error message from upload attempt
        """
        error_lower = error_message.lower()
        
        log_debug('WpaSecUploader', f'Analyzing error message for troubleshooting hints: {error_message}')
        
        if 'connection' in error_lower or 'timeout' in error_lower or 'timed out' in error_lower:
            Color.pl('{!} {O}Troubleshooting: Check your internet connection{W}')
            Color.pl('{!} {O}Try increasing timeout with: {C}--wpasec-timeout 60{W}')
            log_debug('WpaSecUploader', 'Error category: Network connectivity/timeout issue')
        elif 'dns' in error_lower or 'resolve' in error_lower or 'host' in error_lower or 'service not known' in error_lower or 'name or service' in error_lower:
            Color.pl('{!} {O}Troubleshooting: DNS resolution failed{W}')
            Color.pl('{!} {O}Check your network settings and DNS configuration{W}')
            log_debug('WpaSecUploader', 'Error category: DNS resolution failure')
        elif 'key' in error_lower or 'auth' in error_lower or 'unauthorized' in error_lower:
            Color.pl('{!} {O}Troubleshooting: Authentication failed{W}')
            Color.pl('{!} {O}Verify your API key at: {C}https://wpa-sec.stanev.org{W}')
            Color.pl('{!} {O}Update with: {C}--wpasec-key <your_api_key>{W}')
            log_debug('WpaSecUploader', 'Error category: Authentication/API key issue')
        elif 'invalid' in error_lower or 'format' in error_lower:
            Color.pl('{!} {O}Troubleshooting: Invalid capture file format{W}')
            Color.pl('{!} {O}Ensure file contains valid handshake or PMKID data{W}')
            log_debug('WpaSecUploader', 'Error category: Invalid file format')
        elif '404' in error_lower or 'not found' in error_lower:
            Color.pl('{!} {O}Troubleshooting: Server endpoint not found{W}')
            Color.pl('{!} {O}Check URL configuration: {C}--wpasec-url{W}')
            log_debug('WpaSecUploader', 'Error category: HTTP 404 - endpoint not found')
        elif '500' in error_lower or 'server error' in error_lower:
            Color.pl('{!} {O}Troubleshooting: Server error{W}')
            Color.pl('{!} {O}The wpa-sec service may be temporarily unavailable{W}')
            Color.pl('{!} {O}Try again later or check: {C}https://wpa-sec.stanev.org{W}')
            log_debug('WpaSecUploader', 'Error category: HTTP 500 - server error')
        elif 'rate' in error_lower or 'limit' in error_lower or 'too many' in error_lower:
            Color.pl('{!} {O}Troubleshooting: Rate limit exceeded{W}')
            Color.pl('{!} {O}Wait a few minutes before retrying upload{W}')
            log_debug('WpaSecUploader', 'Error category: Rate limiting')
        else:
            log_debug('WpaSecUploader', 'Error category: Unknown/unclassified error')


if __name__ == '__main__':
    # Test module
    print('WpaSecUploader utility module')
    print(f'Supported formats: {", ".join(WpaSecUploader.SUPPORTED_FORMATS)}')
