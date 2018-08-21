#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.process import Process
from ..util.color import Color
from ..tools.tshark import Tshark
from ..tools.pyrit import Pyrit

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

        # We can get BSSID from the .cap filename if Wifite captured it.
        # ESSID is stripped of non-printable characters, so we can't rely on that.
        if self.bssid is None:
            hs_regex = re.compile(r'^.*handshake_\w+_([0-9A-F\-]{17})_.*\.cap$', re.IGNORECASE)
            match = hs_regex.match(self.capfile)
            if match:
                self.bssid = match.group(1).replace('-', ':')

        # Get list of bssid/essid pairs from cap file
        pairs = Tshark.bssid_essid_pairs(self.capfile, bssid=self.bssid)

        if len(pairs) == 0:
            pairs = self.pyrit_handshakes() # Find bssid/essid pairs that have handshakes in Pyrit

        if len(pairs) == 0 and not self.bssid and not self.essid:
            # Tshark and Pyrit failed us, nothing else we can do.
            raise ValueError('Cannot find BSSID or ESSID in cap file %s' % self.capfile)

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


    def tshark_handshakes(self):
        '''Returns list[tuple] of BSSID & ESSID pairs (ESSIDs are always `None`).'''
        tshark_bssids = Tshark.bssids_with_handshakes(self.capfile, bssid=self.bssid)
        return [(bssid, None) for bssid in tshark_bssids]


    def cowpatty_handshakes(self):
        '''Returns list[tuple] of BSSID & ESSID pairs (BSSIDs are always `None`).'''
        if not Process.exists('cowpatty'):
            return []
        if not self.essid:
            return [] # We need a essid for cowpatty :(

        command = [
            'cowpatty',
            '-r', self.capfile,
            '-s', self.essid,
            '-c' # Check for handshake
        ]

        proc = Process(command, devnull=False)
        for line in proc.stdout().split('\n'):
            if 'Collected all necessary data to mount crack against WPA' in line:
                return [(None, self.essid)]
        return []


    def pyrit_handshakes(self):
        '''Returns list[tuple] of BSSID & ESSID pairs.'''
        return Pyrit.bssid_essid_with_handshakes(
                self.capfile, bssid=self.bssid, essid=self.essid)


    def aircrack_handshakes(self):
        '''Returns tuple (BSSID,None) if aircrack thinks self.capfile contains a handshake / can be cracked'''
        if not self.bssid:
            return []  # Aircrack requires BSSID

        command = 'echo "" | aircrack-ng -a 2 -w - -b %s "%s"' % (self.bssid, self.capfile)
        (stdout, stderr) = Process.call(command)

        if 'passphrase not in dictionary' in stdout.lower():
            return [(self.bssid, None)]
        else:
            return []


    def analyze(self):
        '''Prints analysis of handshake capfile'''
        self.divine_bssid_and_essid()

        if Tshark.exists():
            Handshake.print_pairs(self.tshark_handshakes(),   self.capfile, 'tshark')

        if Pyrit.exists():
            Handshake.print_pairs(self.pyrit_handshakes(),    self.capfile, 'pyrit')

        if Process.exists('cowpatty'):
            Handshake.print_pairs(self.cowpatty_handshakes(), self.capfile, 'cowpatty')

        Handshake.print_pairs(self.aircrack_handshakes(), self.capfile, 'aircrack')


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
        if tool is not None:
            tool_str = '{C}%s{W}: ' % tool.rjust(8)

        if len(pairs) == 0:
            Color.pl('{!} %s.cap file {R}does not{O} contain a valid handshake{W}' % (tool_str))
            return

        for (bssid, essid) in pairs:
            out_str = '{+} %s.cap file {G}contains a valid handshake{W} for' % tool_str
            if bssid and essid:
                Color.pl('%s {G}%s{W} ({G}%s{W})' % (out_str, bssid, essid))
            elif bssid:
                Color.pl('%s {G}%s{W}' % (out_str, bssid))
            elif essid:
                Color.pl('%s ({G}%s{W})' % (out_str, essid))


    @staticmethod
    def check():
        ''' Analyzes .cap file(s) for handshake '''
        from ..config import Configuration
        if Configuration.check_handshake == '<all>':
            Color.pl('{+} checking all handshakes in {G}"./hs"{W} directory\n')
            try:
                capfiles = [os.path.join('hs', x) for x in os.listdir('hs') if x.endswith('.cap')]
            except OSError as e:
                capfiles = []
            if len(capfiles) == 0:
                Color.pl('{!} {R}no .cap files found in {O}"./hs"{W}\n')
        else:
            capfiles = [Configuration.check_handshake]

        for capfile in capfiles:
            Color.pl('{+} checking for handshake in .cap file {C}%s{W}' % capfile)
            if not os.path.exists(capfile):
                Color.pl('{!} {O}.cap file {C}%s{O} not found{W}' % capfile)
                return
            hs = Handshake(capfile, bssid=Configuration.target_bssid, essid=Configuration.target_essid)
            hs.analyze()
            Color.pl('')


if __name__ == '__main__':
    print('With BSSID & ESSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap', bssid='18:d6:c7:6d:6b:18', essid='YZWifi')
    hs.analyze()
    print('has_hanshake() =', hs.has_handshake())

    print('\nWith BSSID, but no ESSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap', bssid='18:d6:c7:6d:6b:18')
    hs.analyze()
    print('has_hanshake() =', hs.has_handshake())

    print('\nWith ESSID, but no BSSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap', essid='YZWifi')
    hs.analyze()
    print('has_hanshake() =', hs.has_handshake())

    print('\nWith neither BSSID nor ESSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap')
    try:
        hs.analyze()
        print('has_hanshake() =', hs.has_handshake())
    except Exception as e:
        Color.pl('{O}Error during Handshake.analyze(): {R}%s{W}' % e)
