#!/usr/bin/python

from Airodump import Airodump
from Color import Color
from Target import Target
from Configuration import Configuration

from time import sleep

class Scanner(object):
    ''' Scans wifi networks & provides menu for selecting targets '''

    # Console code for moving up one line
    UP_CHAR = '\x1B[1F'

    def __init__(self):
        '''
            Starts scan, prints as it goes.
            Upon interrupt, sets 'targets'.
        '''
        self.previous_target_count = 0
        self.targets = []

        # Loads airodump with interface/channel/etc from Configuration
        with Airodump() as airodump:
            try:
                # Loop until interrupted (Ctrl+C)
                while True:

                    if airodump.pid.poll() != None:
                        # Airodump process died!
                        raise Exception(
                            "Airodump exited unexpectedly! " +
                            "Command ran: %s"
                                % ' '.join(airodump.pid.command))

                    target_count = len(self.targets)
                    client_count = sum(
                                       [len(t.clients)
                                           for t in self.targets])
                    Color.p(
                        "\r{+} scanning, " +
                        "found {G}%d{W} target(s)," % target_count +
                        " {G}%d{W} clients" % client_count +
                        ". {O}Ctrl+C{W} when ready")
                    sleep(1)
                    self.targets = airodump.get_targets()
                    self.print_targets()
            except KeyboardInterrupt:
                pass


    def print_targets(self):
        '''
            Prints targets to console
        '''
        if len(self.targets) == 0:
            Color.p('\r')
            return

        if self.previous_target_count > 0:
            # We need to "overwrite" the previous list of targets.
            if self.previous_target_count > len(self.targets) or \
               Scanner.get_terminal_height() < self.previous_target_count + 3:
                # Either:
                # 1) We have less targets than before, so we can't overwrite the previous list
                # 2) The terminal can't display the targets without scrolling.
                # Clear the screen.
                from Process import Process
                Process.call('clear')
            else:
                # We can fit the targets in the terminal without scrolling
                # "Move" cursor up so we will print over the previous list
                Color.pl(Scanner.UP_CHAR * (3 + self.previous_target_count))

        self.previous_target_count = len(self.targets)

        # Overwrite the current line
        Color.p('\r')

        Target.print_header()
        for (index, target) in enumerate(self.targets):
            index += 1
            Color.pl('   {G}%s %s' % (str(index).rjust(3), target))

    @staticmethod
    def get_terminal_height():
        import os
        (rows, columns) = os.popen('stty size', 'r').read().split()
        return int(rows)

    def select_targets(self):
        ''' Asks user to select target(s) '''

        if len(self.targets) == 0:
            # TODO Print a more-helpful reason for failure.
            # 1. Link to wireless drivers wiki,
            # 2. How to check if your device supporst monitor mode,
            # 3. Provide airodump-ng command being executed.
            raise Exception("No targets found."
                + " You may need to wait longer,"
                + " or you may have issues with your wifi card")

        self.print_targets()
        input_str  = '{+} select target(s)'
        input_str += ' ({G}1-%d{W})' % len(self.targets)
        input_str += ' separated by commas, dashes'
        input_str += ' or {G}all{W}: '

        chosen_targets = []
        for choice in raw_input(Color.s(input_str)).split(','):
            if choice == 'all':
                chosen_targets = self.targets
                break
            if '-' in choice:
                # User selected a range
                (lower,upper) = [int(x) - 1 for x in choice.split('-')]
                for i in xrange(lower, upper):
                    chosen_targets.append(self.targets[i])
            else:
                choice = int(choice) - 1
                chosen_targets.append(self.targets[choice])
        return chosen_targets


if __name__ == '__main__':
    # Example displays targets and selects the appropriate one
    Configuration.initialize()
    try:
        s = Scanner()
        targets = s.select_targets()
    except Exception, e:
        Color.pl('\r {!} {R}Error{W}: %s' % str(e))
        Configuration.exit_gracefully(0)
    for t in targets:
        Color.pl("    {W}Selected: %s" % t)
    Configuration.exit_gracefully(0)

