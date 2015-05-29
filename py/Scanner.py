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
                while True:
                    client_count = sum([len(t.clients) for t in self.targets])
                    Color.p("\r {+} Scanning, found {G}%d{W} target(s), {G}%d{W} clients" % (len(self.targets), client_count))
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
            return

        if self.previous_target_count > 0:
            # "Move" cursor up so we will print over the previous list
            print Scanner.UP_CHAR * (3 + self.previous_target_count)

        self.previous_target_count = len(self.targets)

        # Overwrite the current line
        Color.p('\r')

        Target.print_header()
        for (index, target) in enumerate(self.targets):
            index += 1
            Color.pl('   {G}%s %s' % (str(index).rjust(3), target))

    def select_targets(self):
        ''' Asks user to select target(s) '''
        self.print_targets()
        input_str  = '{+} Select target(s)'
        input_str += ' ({G}1-%d{W})' % len(self.targets)
        input_str += ' separated by commas, or {G}all{W}: '

        chosen_targets = []
        for choice in raw_input(Color.s(input_str)).split(','):
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
    s = Scanner()
    targets = s.select_targets()
    for t in targets:
        Color.p("{W}Selected: ")
        print t
