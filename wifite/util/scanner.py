#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.color import Color
from ..tools.airodump import Airodump
from ..util.input import raw_input, xrange
from ..model.target import Target, WPSState
from ..config import Configuration
from ..util.process import AdvancedProcess as Process

from time import sleep, time
import threading
from collections import defaultdict
import json
import os


class AdvancedScanner(object):
    '''Advanced WiFi scanner with PIN-based WPS, caching, and optimization'''

    UP_CHAR = '\x1B[1F'
    CACHE_FILE = '/tmp/wifite_targets_cache.json'

    def __init__(self, fast_mode=True, enable_caching=True):
        '''
        Initialize scanner with optimization options.
        fast_mode: Reduce scan time and frequency updates
        enable_caching: Cache target information
        '''
        self.previous_target_count = 0
        self.targets = []
        self.target = None
        self.fast_mode = fast_mode
        self.enable_caching = enable_caching
        self.target_cache = defaultdict(dict)
        self.lock = threading.Lock()

        self.err_msg = None
        self.max_scan_time = Configuration.scan_time

        if enable_caching:
            self.load_cache()

        self.scan()

    def load_cache(self):
        '''Load cached target information'''
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r') as f:
                    self.target_cache = json.load(f)
                Color.pl('{+} Loaded {G}%d{W} cached targets' % len(self.target_cache))
            except Exception as e:
                Color.pl('{!} Error loading cache: {R}%s{W}' % str(e))

    def save_cache(self):
        '''Save target information to cache'''
        try:
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(self.target_cache, f, indent=2)
        except Exception as e:
            Color.pl('{!} Error saving cache: {R}%s{W}' % str(e))

    def scan(self):
        '''Advanced scanning with optimization'''
        try:
            with Airodump() as airodump:
                scan_start_time = time()
                update_frequency = 2 if self.fast_mode else 1

                while True:
                    if airodump.pid.poll() is not None:
                        return

                    self.targets = airodump.get_targets(old_targets=self.targets)

                    if self.found_target():
                        return

                    # Apply cache data
                    if self.enable_caching:
                        self._apply_cache_to_targets()

                    for target in self.targets:
                        if target.bssid in airodump.decloaked_bssids:
                            target.decloaked = True
                            self.target_cache[target.bssid]['decloaked'] = True

                    self.print_targets()

                    target_count = len(self.targets)
                    client_count = sum(len(t.clients) for t in self.targets)

                    outline = '\r{+} Scanning'
                    if airodump.decloaking:
                        outline += ' & decloaking'
                    outline += '. Found {G}%d{W} target(s), {G}%d{W} client(s).' % (
                        target_count, client_count)
                    outline += ' {O}Ctrl+C{W} when ready'

                    Color.clear_entire_line()
                    Color.p(outline)

                    if self.max_scan_time > 0 and time() > scan_start_time + self.max_scan_time:
                        return

                    sleep(update_frequency)

        except KeyboardInterrupt:
            if self.enable_caching:
                self.save_cache()
            pass

    def _apply_cache_to_targets(self):
        '''Apply cached data to discovered targets'''
        for target in self.targets:
            if target.bssid in self.target_cache:
                cached = self.target_cache[target.bssid]
                if 'wps_pin' in cached:
                    target.wps_pin = cached['wps_pin']
                if 'vulnerability' in cached:
                    target.vulnerability = cached['vulnerability']

    def found_target(self):
        '''Detect if user-specified target is found'''
        bssid = Configuration.target_bssid
        essid = Configuration.target_essid

        if bssid is None and essid is None:
            return False

        for target in self.targets:
            if Configuration.wps_only and target.wps not in [WPSState.UNLOCKED, WPSState.LOCKED]:
                continue

            if bssid and target.bssid and bssid.lower() == target.bssid.lower():
                self.target = target
                Color.pl('\n{+} {G}Found target{W}: {C}%s{W} ({G}%s{W})'
                        % (target.bssid, target.essid))
                return True

            if essid and target.essid and essid.lower() == target.essid.lower():
                self.target = target
                Color.pl('\n{+} {G}Found target{W}: {C}%s{W} ({G}%s{W})'
                        % (target.bssid, target.essid))
                return True

        return False

    def print_targets(self):
        '''Print targets in optimized format'''
        if not self.targets:
            Color.p('\r')
            return

        if self.previous_target_count > 0:
            if Configuration.verbose <= 1:
                from ..util.process import Process
                if self.previous_target_count > len(self.targets):
                    Process.call('clear')
                elif self.get_terminal_height() < self.previous_target_count + 3:
                    Process.call('clear')
                else:
                    Color.pl(self.UP_CHAR * (3 + self.previous_target_count))

        self.previous_target_count = len(self.targets)
        Color.p('\r{W}{D}')

        Color.p('   NUM')
        Color.p('                      ESSID')
        if Configuration.show_bssids:
            Color.p('              BSSID')
        Color.p('   CH  ENCR  POWER')
        if Configuration.wps_only:
            Color.p('  WPS PIN')
        Color.pl('  CLIENT\n')

        Color.p('   ---')
        Color.p('  -------------------------')
        if Configuration.show_bssids:
            Color.p('  -----------------')
        Color.p('  ---  ----  -----')
        if Configuration.wps_only:
            Color.p('  --------')
        Color.pl('  ------{W}\n')

        for idx, target in enumerate(self.targets, start=1):
            Color.clear_entire_line()
            Color.p('   {G}%s  {W}' % str(idx).rjust(3))
            Color.p(target.to_str(Configuration.show_bssids))

            if Configuration.wps_only and hasattr(target, 'wps_pin'):
                Color.p('  {C}%s{W}' % target.wps_pin)

            Color.pl('')

    @staticmethod
    def get_terminal_height():
        '''Get terminal height'''
        try:
            import os
            rows, _ = os.popen('stty size', 'r').read().split()
            return int(rows)
        except:
            return 25

    @staticmethod
    def get_terminal_width():
        '''Get terminal width'''
        try:
            import os
            _, cols = os.popen('stty size', 'r').read().split()
            return int(cols)
        except:
            return 80

    def select_targets(self):
        '''Select targets with filtering options'''
        if self.target:
            return [self.target]

        if not self.targets:
            raise Exception('No targets found. Try scanning longer or check your WiFi adapter.')

        if self.max_scan_time > 0:
            return self.targets

        self.print_targets()
        Color.clear_entire_line()

        if self.err_msg:
            Color.pl(self.err_msg)

        input_str = '{+} Select target(s) ({G}1-%d{W}) separated by commas/dashes or {G}all{W}: {G}' % len(self.targets)
        chosen_targets = []

        for choice in raw_input(Color.s(input_str)).split(','):
            choice = choice.strip()

            if choice.lower() == 'all':
                chosen_targets = self.targets
                break

            if '-' in choice:
                try:
                    lower, upper = [int(x) - 1 for x in choice.split('-')]
                    for i in range(lower, min(len(self.targets), upper + 1)):
                        chosen_targets.append(self.targets[i])
                except ValueError:
                    pass

            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(self.targets):
                    chosen_targets.append(self.targets[idx])

        return chosen_targets

    def get_wps_pin(self, target):
        '''Attempt to extract WPS PIN for target'''
        try:
            # Check if pixiewps is available
            if not Process.exists('pixiewps'):
                Color.pl('{!} pixiewps not available for WPS PIN extraction')
                return None

            Color.pl('{+} Attempting to extract WPS PIN for {G}%s{W}' % target.essid)

            # This is a placeholder - actual implementation would use reaver/pixiewps
            return None

        except Exception as e:
            Color.pl('{!} WPS PIN extraction error: {R}%s{W}' % str(e))
            return None


# Backward compatibility
Scanner = AdvancedScanner


if __name__ == '__main__':
    Configuration.initialize()
    try:
        scanner = AdvancedScanner(fast_mode=True)
        targets = scanner.select_targets()
        for t in targets:
            Color.pl('{G}Selected:{W} %s' % t)
    except Exception as e:
        Color.pl('{!} {R}Error:{W} %s' % str(e))
        Configuration.exit_gracefully(0)
