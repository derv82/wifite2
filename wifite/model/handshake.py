#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from ..util.process import Process
from ..util.color import Color
from ..tools.tshark import Tshark

import re, os

class Handshake(object):
    def __init__(self, capfile, bssid=None, essid=None):
        self.capfile = capfile
        self.bssid = bssid
        self.essid = essid

    def divine_bssid_and_essid(self):
        '''
            Tries to find BSSID and ESSID from cap file.
            Sets this instances 'bssid' and 'essid' instance fields.
        '''

        # Get list of bssid/essid pairs from cap file
        pairs = Tshark.bssid_essid_pairs(self.capfile, bssid=self.bssid)

        if len(pairs) == 0:
            pairs = self.pyrit_handshakes() # Find bssid/essid pairs that have handshakes in Pyrit

        if len(pairs) == 0 and not self.bssid and not self.essid:
            raise Exception("Cannot find BSSID or ESSID in cap file") # Tshark and Pyrit failed us, nothing else we can do.

        if not self.essid and not self.bssid:
            # We do not know the bssid nor the essid
            # TODO: Display menu for user to select from list
            # HACK: Just use the first one we see
            self.bssid = pairs[0][0]
            self.essid = pairs[0][1]
            Color.pl('{!} {O}Warning{W}: {O}Arbitrarily selected ' +
                    '{R}bssid{O} {C}%s{O} and {R}essid{O} "{C}%s{O}"{W}' % (self.bssid, self.essid))

        elif not self.bssid:
            # We already know essid
            for (bssid, essid) in pairs:
                if self.essid == essid:
                    Color.pl('{+} Discovered bssid {C}%s{W}' % bssid)
                    self.bssid = bssid
                    break

        elif not self.essid:
            # We already know bssid
            for (bssid, essid) in pairs:
                if self.bssid.lower() == bssid.lower():
                    Color.pl('{+} Discovered essid "{C}%s{W}"' % essid)
                    self.essid = essid
                    break

    def has_handshake(self):
        if not self.bssid or not self.essid:
            self.divine_bssid_and_essid()

        if len(self.tshark_handshakes()) > 0:   return True
        if len(self.pyrit_handshakes()) > 0:    return True

        # TODO: Can we trust cowpatty & aircrack?
        #if len(self.cowpatty_handshakes()) > 0: return True
        #if len(self.aircrack_handshakes()) > 0: return True

        return False


    def tshark_bssid_essid_pairs(self):
        '''Returns list of tuples: (bssid,essid) found in capfile'''

    def tshark_handshakes(self):
        ''' Returns True if tshark identifies a handshake, False otherwise '''
        tshark_bssids = Tshark.bssids_with_handshakes(self.capfile, bssid=self.bssid)
        return [(bssid, None) for bssid in tshark_bssids]


    def cowpatty_command(self):
        return [
            'cowpatty',
            '-r', self.capfile,
            '-s', self.essid,
            '-c' # Check for handshake
        ]

    def cowpatty_handshakes(self):
        ''' Returns True if cowpatty identifies a handshake, False otherwise '''
        if not Process.exists('cowpatty'):
            return []
        if not self.essid:
            return [] # We need a essid for cowpatty :(

        proc = Process(self.cowpatty_command(), devnull=False)
        for line in proc.stdout().split('\n'):
            if 'Collected all necessary data to mount crack against WPA' in line:
                return [(None, self.essid)]
        return []


    def pyrit_command(self):
        return [
            'pyrit',
            '-r', self.capfile,
            'analyze'
        ]

    def pyrit_handshakes(self):
        ''' Returns True if pyrit identifies a handshake, False otherwise '''
        if not Process.exists('pyrit'):
            return []

        bssid_essid_pairs = set()
        hit_target = False
        current_bssid = self.bssid
        current_essid = self.essid
        proc = Process(self.pyrit_command(), devnull=False)
        for line in proc.stdout().split('\n'):
            mac_regex = ('[a-zA-Z0-9]{2}:' * 6)[:-1]
            match = re.search("^#\d+: AccessPoint (%s) \('(.*)'\):$"
                % (mac_regex), line)
            if match:
                # We found a BSSID and ESSID
                (bssid, essid) = match.groups()

                # Compare to what we're searching for
                if self.bssid and self.bssid.lower() == bssid.lower():
                    current_essid = essid
                    hit_target = True
                    continue

                elif self.essid and self.essid == essid:
                    current_bssid = bssid
                    hit_target = True
                    continue

                elif not self.bssid and not self.essid:
                    # We don't know either
                    current_bssid = bssid
                    current_essid = essid
                    hit_target = True
                else:
                    hit_Target = False # This AccessPoint is not what we're looking for
            else:
                # Line does not contain AccessPoint
                if hit_target and ', good' in line:
                    bssid_essid_pairs.add( (current_bssid, current_essid) )
        return [x for x in bssid_essid_pairs]


    def aircrack_handshakes(self):
        '''Returns tuple (BSSID,None) if aircrack thinks self.capfile contains a handshake / can be cracked'''
        if not self.bssid:
            return [] # Aircrack requires BSSID

        command = 'echo "" | aircrack-ng -a 2 -w - -b %s "%s"' % (self.bssid, self.capfile)
        (stdout, stderr) = Process.call(command)

        if 'passphrase not in dictionary' in stdout.lower():
            return [(self.bssid, None)]
        else:
            return []


    def analyze(self):
        '''Prints analysis of handshake capfile'''
        self.divine_bssid_and_essid()

        pairs = self.tshark_handshakes()
        Handshake.print_pairs(pairs, self.capfile, 'tshark')

        pairs = self.pyrit_handshakes()
        Handshake.print_pairs(pairs, self.capfile, 'pyrit')

        pairs = self.cowpatty_handshakes()
        Handshake.print_pairs(pairs, self.capfile, 'cowpatty')

        pairs = self.aircrack_handshakes()
        Handshake.print_pairs(pairs, self.capfile, 'aircrack')


    def strip(self, outfile=None):
        # XXX: This method might break aircrack-ng, use at own risk.
        '''
            Strips out packets from handshake that aren't necessary to crack.
            Leaves only handshake packets and SSID broadcast (for discovery).
            Args:
                outfile - Filename to save stripped handshake to.
                          If outfile==None, overwrite existing self.capfile.
        '''
        if not outfile:
            outfile = self.capfile + '.temp'
            replace_existing_file = True
        else:
            replace_existing_file = False

        cmd = [
            'tshark',
            '-r', self.capfile, # input file
            '-Y', 'wlan.fc.type_subtype == 0x08 || wlan.fc.type_subtype == 0x05 || eapol', # filter
            '-w', outfile # output file
        ]
        proc = Process(cmd)
        proc.wait()
        if replace_existing_file:
            from shutil import copy
            copy(outfile, self.capfile)
            os.remove(outfile)
            pass


    @staticmethod
    def print_pairs(pairs, capfile, tool=None):
        '''
            Prints out BSSID and/or ESSID given a list of tuples (bssid,essid)
        '''
        tool_str = ''
        if tool:
            tool_str = '{C}%s{W}: ' % tool.rjust(8)

        if len(pairs) == 0:
            Color.pl("{!} %s.cap file {R}does not{O} contain a valid handshake{W}"
                % (tool_str))
            return

        for (bssid, essid) in pairs:
            if bssid and essid:
                Color.pl('{+} %s.cap file' % tool_str +
                         ' {G}contains a valid handshake{W}' +
                         ' for {G}%s{W} ({G}%s{W})' % (bssid, essid))
            elif bssid:
                Color.pl('{+} %s.cap file' % tool_str +
                         ' {G}contains a valid handshake{W}' +
                         ' for {G}%s{W}' % bssid)
            elif essid:
                Color.pl('{+} %s.cap file' % tool_str +
                         ' {G}contains a valid handshake{W}' +
                         ' for ({G}%s{W})' % essid)


if __name__ == '__main__':
    print('With BSSID & ESSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap', bssid='18:d6:c7:6d:6b:18', essid='YZWifi')
    hs.analyze()
    print("has_hanshake() =", hs.has_handshake())

    print('\nWith BSSID, but no ESSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap', bssid='18:d6:c7:6d:6b:18')
    hs.analyze()
    print("has_hanshake() =", hs.has_handshake())

    print('\nWith ESSID, but no BSSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap', essid='YZWifi')
    hs.analyze()
    print("has_hanshake() =", hs.has_handshake())

    print('\nWith neither BSSID nor ESSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap')
    hs.analyze()
    print("has_hanshake() =", hs.has_handshake())

