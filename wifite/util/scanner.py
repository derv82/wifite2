#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import sleep, time

from ..config import Configuration
from ..tools.airodump import Airodump
from ..util.color import Color
from ..util.output import OutputManager

# Check for native scanner availability
try:
    from ..native.scanner import NativeScanner, AccessPoint as NativeAP, is_available as native_scanner_available
    NATIVE_SCANNER_AVAILABLE = native_scanner_available()
except (ImportError, Exception):
    NATIVE_SCANNER_AVAILABLE = False


class Scanner:
    """ Scans wifi networks & provides menu for selecting targets """

    # Console code for moving up one line
    UP_CHAR = '\033[1A'

    def __init__(self):
        self.previous_target_count = 0
        self.target_archives = {}
        self.targets = []
        self.target = None  # Target specified by user (based on ESSID/BSSID)
        self.err_msg = None
        self._max_targets = 1000  # Limit target list size to prevent memory bloat
        self._cleanup_counter = 0  # Counter for periodic cleanup
        self._limit_warned = False  # Warn once when target cap is first reached

        # Initialize view based on output mode
        self.view = None
        self.use_tui = OutputManager.is_tui_mode()

    def find_targets(self):
        """
        Scans for targets via Airodump.
        Loops until scan is interrupted via user or config.
        Sets this object `targets` attribute (list[Target]) on interruption
        """

        max_scan_time = Configuration.scan_time

        # Check if airodump-ng is available, fallback to native if needed
        from ..util.process import Process
        use_native_scanner = False

        if not Process.exists('airodump-ng'):
            if NATIVE_SCANNER_AVAILABLE:
                from ..util.logger import log_info
                log_info('Scanner', 'airodump-ng not found, using native scanner (Scapy)')
                Color.pl('{+} {O}airodump-ng not found, using native scanner (Scapy){W}')
                use_native_scanner = True
            else:
                Color.pl('{!} {R}Error: airodump-ng not found and native scanner not available{W}')
                self.err_msg = '{!} {R}Scanner not available: install aircrack-ng or Scapy{W}'
                return False

        # Route to appropriate scanner
        if use_native_scanner:
            return self._find_targets_native(max_scan_time)

        # Loads airodump with interface/channel/etc from Configuration
        try:
            with Airodump() as airodump:
                # Initialize view for TUI mode after airodump starts
                if self.use_tui:
                    try:
                        self.view = OutputManager.get_scanner_view()
                        controller = OutputManager.get_controller()
                        if controller:
                            controller.start()
                    except Exception as e:
                        # If TUI fails to start, fall back to classic
                        Color.pl('{!} {O}TUI failed to start: %s{W}' % str(e))
                        Color.pl('{!} {O}Falling back to classic mode{W}')
                        self.use_tui = False
                        self.view = None

                # Loop until interrupted (Ctrl+C)
                scan_start_time = time()

                # Initial render for TUI
                if self.use_tui and self.view:
                    self.view.update_targets([], airodump.decloaking)

                while True:
                    if airodump.pid.poll() is not None:
                        return True  # Airodump process died

                    self.targets = airodump.get_targets(old_targets=self.targets,
                                                        target_archives=self.target_archives)

                    # Periodic memory cleanup
                    self._cleanup_counter += 1
                    if self._cleanup_counter % 10 == 0:  # Every 10 scans
                        self._cleanup_memory()

                    # Memory monitoring
                    if self._cleanup_counter % 50 == 0:  # Every 50 scans
                        from ..util.memory import MemoryMonitor
                        MemoryMonitor.periodic_check(self._cleanup_counter)

                    if self.found_target():
                        return True  # We found the target we want

                    # Update display based on mode
                    if self.use_tui and self.view:
                        self.view.update_targets(self.targets, airodump.decloaking)
                    else:
                        self.print_targets()

                        target_count = len(self.targets)
                        client_count = sum(len(t2.clients) for t2 in self.targets)

                        elapsed = int(time() - scan_start_time)
                        mins = elapsed // 60
                        secs = elapsed % 60

                        outline = '\r{+} {C}Scanning'
                        if airodump.decloaking:
                            outline += ' + decloaking'
                        outline += '{W} [{D}%02d:%02d{W}]' % (mins, secs)
                        outline += '  Targets: {G}%d{W}' % target_count
                        outline += '  Clients: {G}%d{W}' % client_count
                        outline += '  {D}\u2502{W} {O}Ctrl+C{W} to stop '
                        Color.clear_entire_line()
                        Color.p(outline)

                    if max_scan_time > 0 and time() > scan_start_time + max_scan_time:
                        return True

                    sleep(1)

        except KeyboardInterrupt:
            return self._prompt_attack_or_exit()
        finally:
            # Clean up TUI view
            if self.use_tui and self.view:
                self.view.stop()
                controller = OutputManager.get_controller()
                if controller:
                    controller.stop()

    def _prompt_attack_or_exit(self):
        if not Configuration.infinite_mode:
            return True

        options = '({G}s{W}{D}, {W}{R}e{W})'
        prompt = '{+} Do you want to {G}start attacking{W} or {R}exit{W}%s?' % options

        self.print_targets()
        Color.clear_entire_line()
        Color.p(prompt)
        try:
            answer = input().lower()
        except KeyboardInterrupt:
            # If user presses Ctrl+C during input, default to exit
            Color.pl('\n{!} {O}Interrupted during input, exiting...{W}')
            return False  # Exit

        return not answer.startswith('e')

    def update_targets(self):
        """
        Archive all the old targets
        Returns: True if user wants to stop attack, False otherwise
        """
        self.previous_target_count = 0
        # for target in self.targets:
        # self.target_archives[target.bssid] = ArchivedTarget(target)

        self.targets = []
        return self.find_targets()

    def get_num_attacked(self):
        """
        Returns: number of attacked targets by this scanner
        """
        return sum(bool(target.attacked) for target in list(self.target_archives.values()))

    def found_target(self):
        """
        Detect if we found a target specified by the user (optional).
        Sets this object's `target` attribute if found.
        Returns: True if target was specified and found, False otherwise.
        """
        bssid = Configuration.target_bssid
        essid = Configuration.target_essid

        if bssid is None and essid is None:
            return False  # No specific target from user.

        for target in self.targets:
            # if Configuration.wps_only and target.wps not in [WPSState.UNLOCKED, WPSState.LOCKED]:
            #    continue
            if bssid and target.bssid and bssid.lower() == target.bssid.lower():
                self.target = target
                break
            if essid and target.essid and essid == target.essid:
                self.target = target
                break

        if self.target:
            Color.pl('\n{+} {C}found target{G} %s {W}({G}%s{W})' % (self.target.bssid, self.target.essid))
            return True

        return False

    @staticmethod
    def clr_scr():
        import platform
        import subprocess

        cmdtorun = 'cls' if platform.system().lower() == "windows" else 'clear'
        subprocess.run([cmdtorun], check=False)

    def print_targets(self):
        """Prints targets selection menu (1 target per row)."""
        if len(self.targets) == 0:
            Color.p('\r')
            return

        # Always clear the screen before printing targets
        if Configuration.verbose <= 1:
            self.clr_scr()

        self.previous_target_count = len(self.targets)

        # Get terminal width for adaptive layout
        try:
            term_width = self.get_terminal_width()
        except (OSError, ValueError):
            term_width = 120

        # Column widths
        col_num = 5
        col_essid = 26
        col_bssid = 19 if Configuration.show_bssids else 0
        col_mfg = 23 if Configuration.show_manufacturers else 0
        col_ch = 4
        col_enc = 9
        col_pwr = 7
        col_wps = 5
        col_cli = 7
        col_hp = 5 if Configuration.detect_honeypots else 0

        # Build header
        Color.p('\r')
        hdr = ''
        hdr += '{W}{D} ' + 'NUM'.rjust(col_num)
        hdr += '  ' + 'ESSID'.ljust(col_essid)
        if Configuration.show_bssids:
            hdr += '  ' + 'BSSID'.ljust(col_bssid)
        if Configuration.show_manufacturers:
            hdr += '  ' + 'MANUFACTURER'.ljust(col_mfg)
        hdr += '  ' + 'CH'.rjust(col_ch)
        hdr += '  ' + 'ENCR'.ljust(col_enc)
        hdr += '  ' + 'PWR'.rjust(col_pwr)
        hdr += '  ' + 'WPS'.center(col_wps)
        hdr += '  ' + 'CLI'.rjust(col_cli)
        if Configuration.detect_honeypots:
            hdr += '  ' + 'HP'.center(col_hp)
        hdr += '{W}'
        Color.pl(hdr)

        # Separator
        sep_len = col_num + col_essid + col_ch + col_enc + col_pwr + col_wps + col_cli + 16
        if Configuration.show_bssids:
            sep_len += col_bssid + 2
        if Configuration.show_manufacturers:
            sep_len += col_mfg + 2
        if Configuration.detect_honeypots:
            sep_len += col_hp + 2
        sep_len = min(sep_len, term_width - 2)
        Color.pl('{W}{D} ' + '\u2500' * sep_len + '{W}')

        # Remaining rows: targets
        for idx, target in enumerate(self.targets, start=1):
            Color.clear_entire_line()
            Color.p(' {G}%s{W}  ' % str(idx).rjust(col_num))
            Color.pl(target.to_str(
                Configuration.show_bssids,
                Configuration.show_manufacturers
            )
            )

    @staticmethod
    def get_terminal_height():
        import shutil
        return shutil.get_terminal_size(fallback=(24, 80)).lines

    @staticmethod
    def get_terminal_width():
        import shutil
        return shutil.get_terminal_size(fallback=(24, 80)).columns

    def _diagnose_no_targets(self):
        """Print actionable diagnostics when a scan finds zero targets.

        The bare "issues with your wifi card" message can't tell the three
        common root causes apart, so we probe them explicitly:
          * the card/driver captured nothing in monitor mode (RX counter ~0) —
            a driver/monitor-mode problem, not a network one;
          * APs exist but were removed by an encryption/type filter;
          * the scan only covered 2.4 GHz (5 GHz APs need -5 / --band).

        Best-effort: never raises.
        """
        import os
        iface = Configuration.interface
        Color.pl('\n{!} {O}Scan diagnostics:{W}')

        # 1. Did the monitor interface actually receive any frames? In monitor
        #    mode the kernel bumps rx_packets for every captured frame, so a
        #    near-zero count is a strong sign the card isn't really capturing.
        rx = None
        driver = None
        if iface:
            try:
                with open('/sys/class/net/%s/statistics/rx_packets' % iface) as fh:
                    rx = int(fh.read().strip())
            except (OSError, ValueError):
                rx = None
            try:
                driver = os.path.basename(
                    os.path.realpath('/sys/class/net/%s/device/driver' % iface))
            except OSError:
                driver = None

        if rx is not None:
            Color.pl('    {C}Interface:{W} %s%s  {C}frames received:{W} %d' % (
                iface, (' {D}(%s){W}' % driver) if driver else '', rx))
            if rx < 10:
                Color.pl('    {R}→ The card received ~no frames in monitor mode.{W}')
                Color.pl('    {O}This is almost always a driver/monitor-mode problem, '
                         'not a network issue:{W}')
                Color.pl('    {O}  - Verify monitor mode + injection: {C}aireplay-ng --test %s{W}' % iface)
                Color.pl('    {O}  - Some USB chipsets (rtw88/rtl8xxxu) have flaky monitor '
                         'mode; try a different adapter.{W}')
                Color.pl('    {O}  - Check {C}dmesg{O} for mac80211 / USB errors.{W}')
            else:
                Color.pl('    {G}→ The card IS receiving frames{W} — so the cause is '
                         'filtering or band, not the driver:')

        # 2. Band coverage (default scan is 2.4 GHz only).
        if not (Configuration.all_bands or Configuration.five_ghz):
            Color.pl('    {O}  - Scanning {C}2.4 GHz only{O} (default); for 5 GHz APs add '
                     '{C}-5{O} or {C}--band abg{W}.')

        # 3. Active encryption/type filter (< 5 means a specific filter is on).
        enc = getattr(Configuration, 'encryption_filter', None)
        if enc and len(enc) < 5:
            Color.pl('    {O}  - Type filter active: {C}%s{O}; other AP types are hidden — '
                     'drop the filter to see all.{W}' % '/'.join(enc))
        Color.pl('')

    def select_targets(self):
        """
        Returns list(target)
        Either a specific target if user specified -bssid or --essid.
        If the user used pillage or infinite attack mode retuns all the targets
        Otherwise, prompts user to select targets and returns the selection.
        """

        if self.target:
            # When user specifies a specific target
            return [self.target]

        if len(self.targets) == 0:
            if self.err_msg is not None:
                Color.pl(self.err_msg)

            self._diagnose_no_targets()

            raise Exception('No targets found.'
                            + ' You may need to wait longer,'
                            + ' or you may have issues with your wifi card')

        # Return all targets if user specified a wait time ('pillage').
        # A scan time is always set if run in infinite mode
        if Configuration.scan_time > 0:
            return self.targets

        # Ask user for targets if no automatic selection
        return self._prompt_user_for_targets()

    def get_all_targets(self):
        """
        Returns all discovered targets without prompting user.
        Used for scan-only modes like Dragonblood detection.
        """
        return self.targets

    def _find_targets_native(self, max_scan_time):
        """
        Scan for targets using native Scapy-based scanner.

        This is a fallback method when airodump-ng is not available.
        Uses NativeScanner from the native module.

        Args:
            max_scan_time: Maximum scan duration in seconds (0 = until interrupted)

        Returns:
            True if scan completed successfully
        """
        from ..util.logger import log_info, log_warning

        log_info('Scanner', 'Starting native scanner')

        # Determine scan band
        if Configuration.five_ghz:
            band = '5'
        elif Configuration.all_bands:
            band = 'all'
        else:
            band = '2.4'

        # Determine channels
        channels = None
        if Configuration.target_channel:
            try:
                # Parse channel specification (supports ranges like "1,6,11" or "1-11")
                channels = []
                for part in Configuration.target_channel.split(','):
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        channels.extend(range(start, end + 1))
                    else:
                        channels.append(int(part))
            except ValueError:
                log_warning('Scanner', f'Invalid channel spec: {Configuration.target_channel}')

        Color.pl('{+} {C}Starting native scanner (Scapy){W}')
        Color.pl('{+} {C}Band: {G}%s{C}, Channels: {G}%s{W}' % (
            band, channels if channels else 'auto'
        ))

        # Initialize TUI view if available
        if self.use_tui:
            try:
                self.view = OutputManager.get_scanner_view()
                controller = OutputManager.get_controller()
                if controller:
                    controller.start()
            except Exception as e:
                Color.pl('{!} {O}TUI failed to start: %s{W}' % str(e))
                self.use_tui = False
                self.view = None

        # Create and start native scanner
        scanner = NativeScanner(
            interface=Configuration.interface,
            channels=channels,
            band=band,
            hop_interval=0.5
        )

        try:
            scanner.start()
            scan_start_time = time()

            while True:
                # Convert native APs to Target objects
                native_aps = scanner.get_targets()
                self.targets = self._convert_native_targets(native_aps)

                # Honeypot detection for native scanner path
                if Configuration.detect_honeypots:
                    from ..util.honeypot_detector import HoneypotDetector
                    HoneypotDetector.analyse(self.targets)

                # Periodic memory cleanup
                self._cleanup_counter += 1
                if self._cleanup_counter % 10 == 0:
                    self._cleanup_memory()

                # Memory monitoring
                if self._cleanup_counter % 50 == 0:
                    from ..util.memory import MemoryMonitor
                    MemoryMonitor.periodic_check(self._cleanup_counter)

                # Check for specific target
                if self.found_target():
                    scanner.stop()
                    return True

                # Update display
                if self.use_tui and self.view:
                    self.view.update_targets(self.targets, False)
                else:
                    self.print_targets()

                    target_count = len(self.targets)
                    client_count = sum(len(t.clients) for t in self.targets if hasattr(t, 'clients'))
                    stats = scanner.get_stats()

                    outline = '\r{+} Scanning (native).'
                    outline += ' Found {G}%d{W} target(s),' % target_count
                    outline += ' {G}%d{W} client(s).' % client_count
                    outline += ' Ch:{C}%s{W}' % stats.get('current_channel', '?')
                    outline += ' {O}Ctrl+C{W} when ready '
                    Color.clear_entire_line()
                    Color.p(outline)

                # Check timeout
                if max_scan_time > 0 and time() > scan_start_time + max_scan_time:
                    scanner.stop()
                    return True

                sleep(1)

        except KeyboardInterrupt:
            scanner.stop()
            return self._prompt_attack_or_exit()
        finally:
            scanner.stop()
            if self.use_tui and self.view:
                self.view.stop()
                controller = OutputManager.get_controller()
                if controller:
                    controller.stop()

    def _convert_native_targets(self, native_aps):
        """
        Convert native AccessPoint objects to Target objects.

        Args:
            native_aps: List of NativeAP objects from NativeScanner

        Returns:
            List of Target objects compatible with wifite's attack system
        """
        from ..model.target import Target, WPSState
        from ..model.client import Client
        
        targets = []
        
        for ap in native_aps:
            try:
                # Build CSV-like fields that Target expects
                # Format: BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key
                
                # Map encryption to airodump format
                privacy = ap.encryption
                if privacy == 'OPEN':
                    privacy = 'OPN'
                elif privacy == 'WPA3':
                    privacy = 'WPA3'
                elif privacy == 'WPA2':
                    privacy = 'WPA2'
                elif privacy == 'WPA':
                    privacy = 'WPA'
                elif privacy == 'WEP':
                    privacy = 'WEP'
                
                # Build fields string
                fields = [
                    ap.bssid,                    # BSSID
                    '',                          # First time seen
                    '',                          # Last time seen
                    str(ap.channel),            # Channel
                    '54',                        # Speed
                    privacy,                     # Privacy
                    ap.cipher or '',             # Cipher
                    ap.auth or '',               # Authentication
                    str(ap.power),               # Power
                    str(ap.beacons),            # Beacons
                    '0',                         # IV
                    '0.0.0.0',                  # LAN IP
                    str(len(ap.essid)),         # ID-length
                    ap.essid or '',             # ESSID
                    ''                           # Key
                ]
                
                # Create Target from fields
                target = Target(fields)
                
                # Set WPS state
                if ap.wps:
                    target.wps = WPSState.LOCKED if ap.wps_locked else WPSState.UNLOCKED
                else:
                    target.wps = WPSState.NONE
                
                # Add clients
                for client_mac in ap.clients:
                    client = Client(['', client_mac, ap.bssid, str(ap.power), '', '', ''])
                    target.clients.append(client)
                
                # Store last_seen for cleanup
                target.last_seen = ap.last_seen
                
                targets.append(target)
                
            except Exception as e:
                from ..util.logger import log_debug
                log_debug('Scanner', f'Error converting native AP {ap.bssid}: {e}')
                continue
        
        return targets
    
    def _cleanup_memory(self):
        """Enhanced memory cleanup with time-based expiration to prevent bloat during long scans"""
        from time import time
        current_time = time()
        
        # 1. Remove stale targets (not seen in 5 minutes)
        stale_threshold = current_time - 300  # 5 minutes
        initial_target_count = len(self.targets)
        
        # Filter out stale targets
        self.targets = [
            t for t in self.targets 
            if getattr(t, 'last_seen', current_time) > stale_threshold
        ]
        
        stale_removed = initial_target_count - len(self.targets)
        if stale_removed > 0 and Configuration.verbose > 1:
            Color.pl('{!} {O}Removed %d stale targets (not seen in 5 min){W}' % stale_removed)
        
        # 2. Limit target list size (keep strongest signals)
        if len(self.targets) > self._max_targets:
            import heapq
            removed_count = len(self.targets) - self._max_targets
            # Use heapq.nlargest: O(n log k) vs O(n log n) for full sort
            self.targets = heapq.nlargest(self._max_targets, self.targets, key=lambda x: x.power)

            if not self._limit_warned:
                Color.pl('{!} {O}Target limit reached (%d): keeping strongest signals, '
                         'dropping %d weakest. Use {G}--verbose{O} for ongoing trim info.{W}'
                         % (self._max_targets, removed_count))
                self._limit_warned = True
            elif Configuration.verbose > 1:
                Color.pl('{!} {O}Trimmed %d weak targets (limit: %d){W}' %
                        (removed_count, self._max_targets))
        
        # 3. Clean up old archived targets with time-based expiration
        if len(self.target_archives) > 500:
            # Remove archives older than 1 hour
            archive_threshold = current_time - 3600  # 1 hour
            initial_archive_count = len(self.target_archives)
            
            # Filter by age first
            self.target_archives = {
                bssid: target for bssid, target in self.target_archives.items()
                if getattr(target, 'last_seen', current_time) > archive_threshold
            }
            
            # If still too many, keep only the most recent
            if len(self.target_archives) > 300:
                sorted_archives = sorted(
                    self.target_archives.items(),
                    key=lambda x: getattr(x[1], 'last_seen', 0),
                    reverse=True
                )
                self.target_archives = dict(sorted_archives[:300])
            
            archive_removed = initial_archive_count - len(self.target_archives)
            if archive_removed > 0 and Configuration.verbose > 1:
                Color.pl('{!} {O}Cleaned %d old archived targets{W}' % archive_removed)
        
        # 4. Force garbage collection periodically
        if self._cleanup_counter % 50 == 0:  # Every 50 cleanup cycles
            import gc
            collected = gc.collect()
            
            if Configuration.verbose > 2:
                Color.pl('{+} {C}Garbage collected %d objects{W}' % collected)
                
                # Show memory usage if verbose enough
                try:
                    import psutil
                    import os
                    process = psutil.Process(os.getpid())
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    Color.pl('{+} {C}Memory usage: %.1f MB{W}' % memory_mb)
                except ImportError:
                    pass  # psutil not available

    def _prompt_user_for_targets(self):
        """Prompt user to select targets from the list"""
        # Use TUI selector if in TUI mode
        if self.use_tui:
            return self._prompt_user_for_targets_tui()
        else:
            return self._prompt_user_for_targets_classic()

    def _prompt_user_for_targets_tui(self):
        """Prompt user to select targets using TUI selector"""
        try:
            # Get selector view from OutputManager
            selector_view = OutputManager.get_selector_view(self.targets)
            
            # Run interactive selector
            chosen_targets = selector_view.run()
            
            return chosen_targets
        except Exception as e:
            # If TUI selector fails, fall back to classic mode
            Color.pl('\n{!} {O}TUI selector failed: %s{W}' % str(e))
            Color.pl('{!} {O}Falling back to classic selection mode{W}')
            return self._prompt_user_for_targets_classic()

    def _prompt_user_for_targets_classic(self):
        """Prompt user to select targets using classic text input"""
        # Ask user for targets.
        self.print_targets()
        Color.clear_entire_line()

        if self.err_msg is not None:
            Color.pl(self.err_msg)

        input_str = '{+} Select target(s)'
        input_str += ' ({G}1-%d{W})' % len(self.targets)
        input_str += ' separated by commas, dashes'
        input_str += ' or {G}all{W}: {C}'

        chosen_targets = []

        Color.p(input_str)
        try:
            user_input = input()
        except KeyboardInterrupt:
            # If user presses Ctrl+C during input, return empty list to exit
            Color.pl('\n{!} {O}Interrupted during target selection, exiting...{W}')
            return []

        for choice in user_input.split(','):
            choice = choice.strip()
            if choice.lower() == 'all':
                chosen_targets = self.targets
                break
            if '-' in choice:
                # User selected a range
                (lower, upper) = [int(x) - 1 for x in choice.split('-')]
                for i in range(lower, min(len(self.targets), upper + 1)):
                    chosen_targets.append(self.targets[i])
            elif choice.isdigit():
                choice = int(choice)
                if choice > len(self.targets):
                    Color.pl('    {!} {O}Invalid target index (%d)... ignoring' % choice)
                    continue

                chosen_targets.append(self.targets[choice - 1])

        return chosen_targets


if __name__ == '__main__':
    import subprocess
    # 'Test' script will display targets and selects the appropriate one
    Configuration.initialize()
    targets = []
    try:
        s = Scanner()
        s.find_targets()
        targets = s.select_targets()
    except (OSError, IOError) as e:
        Color.pl('\r {!} {R}Scanner I/O Error{W}: %s' % str(e))
        Configuration.exit_gracefully()
    except subprocess.CalledProcessError as e:
        Color.pl('\r {!} {R}Scanner Command Failed{W}: %s' % str(e))
        Configuration.exit_gracefully()
    except ValueError as e:
        Color.pl('\r {!} {R}Scanner Configuration Error{W}: %s' % str(e))
        Configuration.exit_gracefully()
    except Exception as e:
        Color.pl('\r {!} {R}Unexpected Scanner Error{W}: %s' % str(e))
        if Configuration.verbose > 0:
            Color.pexception(e)
        Configuration.exit_gracefully()
    for t in targets:
        Color.pl('    {W}Selected: %s' % t)
    Configuration.exit_gracefully()
