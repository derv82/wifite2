#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.color import Color
from ..tools.airodump import Airodump
from ..util.input import raw_input, xrange
from ..config import Configuration

from time import sleep, time


class Scanner(object):
    ''' Scans wifi networks & provides menu for selecting targets '''

    # Console code for moving up one line
    UP_CHAR = '\x1B[1F'

    def __init__(self):
        self.previous_target_count = 0
        self.target_archives = {}
        self.targets = []
        self.target = None  # Target specified by user (based on ESSID/BSSID)
        self.err_msg = None

    def find_targets(self):
        '''
        Scans for targets via Airodump.
        Loops until scan is interrupted via user or config.
        Sets this object `targets` attribute (list[Target]) on interruption
        '''

        max_scan_time = Configuration.scan_time

        # Loads airodump with interface/channel/etc from Configuration
        try:
            with Airodump() as airodump:
                # Loop until interrupted (Ctrl+C)
                scan_start_time = time()

                while True:
                    if airodump.pid.poll() is not None:
                        return True  # Airodump process died

                    self.targets = airodump.get_targets(old_targets=self.targets,
                                                        target_archives=self.target_archives)

                    if self.found_target():
                        return True  # We found the target we want

                    if airodump.pid.poll() is not None:
                        return True  # Airodump process died

                    self.print_targets()

                    target_count = len(self.targets)
                    client_count = sum(len(t.clients) for t in self.targets)

                    outline = '\r{+} Scanning'
                    if airodump.decloaking:
                        outline += ' & decloaking'
                    outline += '. Found'
                    outline += ' {G}%d{W} target(s),' % target_count
                    outline += ' {G}%d{W} client(s).' % client_count
                    outline += ' {O}Ctrl+C{W} when ready '
                    Color.clear_entire_line()
                    Color.p(outline)

                    if max_scan_time > 0 and time() > scan_start_time + max_scan_time:
                        return True

                    sleep(1)

        except KeyboardInterrupt:
            if not Configuration.infinite_mode:
                return True

            from ..util.input import raw_input

            options = '({G}s{W}{D}, {W}{R}e{W})'
            prompt = '{+} Do you want to {G}start attacking{W} or {R}exit{W}%s?' % options

            self.print_targets()
            Color.clear_entire_line()
            Color.p(prompt)
            answer = raw_input().lower()

            if answer.startswith('e'):
                return False

            return True

    def update_targets(self):
        '''
        Archive all the old targets
        Returns: True if user wants to stop attack, False otherwise
        '''
        self.previous_target_count = 0
        # for target in self.targets:
        # self.target_archives[target.bssid] = ArchivedTarget(target)

        self.targets = []
        do_continue = self.find_targets()
        return do_continue

    def get_num_attacked(self):
        '''
        Returns: number of attacked targets by this scanner
        '''
        attacked_targets = 0
        for target in self.target_archives.values():
            if target.attacked:
                attacked_targets += 1

        return attacked_targets

    def found_target(self):
        '''
        Detect if we found a target specified by the user (optional).
        Sets this object's `target` attribute if found.
        Returns: True if target was specified and found, False otherwise.
        '''
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

    def print_targets(self):
        '''Prints targets selection menu (1 target per row).'''
        if len(self.targets) == 0:
            Color.p('\r')
            return

        if self.previous_target_count > 0:
            # We need to 'overwrite' the previous list of targets.
            if Configuration.verbose <= 1:
                # Don't clear screen buffer in verbose mode.
                if self.previous_target_count > len(self.targets) or \
                   Scanner.get_terminal_height() < self.previous_target_count + 3:
                    # Either:
                    # 1) We have less targets than before, so we can't overwrite the previous list
                    # 2) The terminal can't display the targets without scrolling.
                    # Clear the screen.
                    from ..util.process import Process
                    Process.call('clear')
                else:
                    # We can fit the targets in the terminal without scrolling
                    # 'Move' cursor up so we will print over the previous list
                    Color.pl(Scanner.UP_CHAR * (3 + self.previous_target_count))

        self.previous_target_count = len(self.targets)

        # Overwrite the current line
        Color.p('\r{W}{D}')

        # First row: columns
        Color.p('   NUM')
        Color.p('                      ESSID')
        if Configuration.show_bssids:
            Color.p('              BSSID')

        if Configuration.show_manufacturers:
            Color.p('           MANUFACTURER')

        Color.pl('   CH  ENCR   POWER  WPS?  CLIENT')

        # Second row: separator
        Color.p('   ---')
        Color.p('  -------------------------')
        if Configuration.show_bssids:
            Color.p('  -----------------')

        if Configuration.show_manufacturers:
            Color.p('  ---------------------')

        Color.pl('  ---  -----  -----  ----  ------{W}')

        # Remaining rows: targets
        for idx, target in enumerate(self.targets, start=1):
            Color.clear_entire_line()
            Color.p('   {G}%s  ' % str(idx).rjust(3))
            Color.pl(target.to_str(
                    Configuration.show_bssids,
                    Configuration.show_manufacturers
                    )
                )

    @staticmethod
    def get_terminal_height():
        import os
        (rows, columns) = os.popen('stty size', 'r').read().split()
        return int(rows)

    @staticmethod
    def get_terminal_width():
        import os
        (rows, columns) = os.popen('stty size', 'r').read().split()
        return int(columns)

    def select_targets(self):
        '''
        Returns list(target)
        Either a specific target if user specified -bssid or --essid.
        If the user used pillage or infinite attack mode retuns all the targets
        Otherwise, prompts user to select targets and returns the selection.
        '''

        if self.target:
            # When user specifies a specific target
            return [self.target]

        if len(self.targets) == 0:
            if self.err_msg is not None:
                Color.pl(self.err_msg)

            # TODO Print a more-helpful reason for failure.
            # 1. Link to wireless drivers wiki,
            # 2. How to check if your device supports monitor mode,
            # 3. Provide airodump-ng command being executed.
            raise Exception('No targets found.'
            + ' You may need to wait longer,'
            + ' or you may have issues with your wifi card')

        # Return all targets if user specified a wait time ('pillage').
        # A scan time is always set if run in infinite mode
        if Configuration.scan_time > 0:
            return self.targets

        # Ask user for targets.
        self.print_targets()
        Color.clear_entire_line()

        if self.err_msg is not None:
            Color.pl(self.err_msg)

        input_str = '{+} select target(s)'
        input_str += ' ({G}1-%d{W})' % len(self.targets)
        input_str += ' separated by commas, dashes'
        input_str += ' or {G}all{W}: '

        chosen_targets = []

        Color.p(input_str)
        for choice in raw_input().split(','):
            choice = choice.strip()
            if choice.lower() == 'all':
                chosen_targets = self.targets
                break
            if '-' in choice:
                # User selected a range
                (lower, upper) = [int(x) - 1 for x in choice.split('-')]
                for i in xrange(lower, min(len(self.targets), upper + 1)):
                    chosen_targets.append(self.targets[i])
            elif choice.isdigit():
                choice = int(choice) - 1
                chosen_targets.append(self.targets[choice])

        return chosen_targets


if __name__ == '__main__':
    # 'Test' script will display targets and selects the appropriate one
    Configuration.initialize()
    targets = []
    try:
        s = Scanner()
        s.find_targets()
        targets = s.select_targets()
    except Exception as e:
        Color.pl('\r {!} {R}Error{W}: %s' % str(e))
        Configuration.exit_gracefully(0)
    for t in targets:
        Color.pl('    {W}Selected: %s' % t)
    Configuration.exit_gracefully(0)
