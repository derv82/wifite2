#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.process import Process
from ..util.color import Color
from ..tools.tshark import Tshark

import re
import os


class Handshake(object):

    def __init__(self, capfile, bssid=None, essid=None):
        self.capfile = capfile
        self.bssid = bssid
        self.essid = essid

    def divine_bssid_and_essid(self):
        """
            Tries to find BSSID and ESSID from cap file.
            Sets this instances 'bssid' and 'essid' instance fields.
        """

        # We can get BSSID from the .cap filename if Wifite captured it.
        # ESSID is stripped of non-printable characters, so we can't rely on that.
        if self.bssid is None:
            hs_regex = re.compile(r'^.*handshake_\w+_([\dA-F\-]{17})_.*\.cap$', re.IGNORECASE)
            result = hs_regex.match(self.capfile)
            if result is not None:
                self.bssid = result[1].replace('-', ':')

        # Get list of bssid/essid pairs from cap file
        pairs = Tshark.bssid_essid_pairs(self.capfile, bssid=self.bssid)

        if len(pairs) == 0 and (not self.bssid and not self.essid):
            # Tshark failed us, nothing else we can do.
            raise ValueError(f'Cannot find BSSID or ESSID in cap file {self.capfile}')

        if not self.essid and not self.bssid:
            # We do not know the bssid nor the essid
            # TODO: Display menu for user to select from list
            # HACK: Just use the first one we see
            self.bssid = pairs[0][0]
            self.essid = pairs[0][1]
            Color.pl('{!} {O}Warning{W}: {O}Arbitrarily selected ' +
                     '{R}bssid{O} {C}%s{O} and {R}essid{O} "{C}%s{O}"{W}' % (self.bssid, self.essid))

        if not self.bssid:
            # We already know essid
            for (bssid, essid) in pairs:
                if self.essid == essid:
                    Color.pl('\n{+} Discovered bssid {C}%s{W}' % bssid)
                    self.bssid = bssid
                    break

        if not self.essid and len(pairs) > 0:
            for (bssid, essid) in pairs:
                if self.bssid.lower() == bssid.lower():
                    Color.pl('\n{+} Discovered essid "{C}%s{W}"' % essid)
                    self.essid = essid
                    break

    def has_handshake(self):
        if not self.bssid or not self.essid:
            self.divine_bssid_and_essid()

        return len(self.tshark_handshakes()) > 0

    def tshark_handshakes(self):
        """Returns list[tuple] of BSSID & ESSID pairs (ESSIDs are always `None`)."""
        tshark_bssids = Tshark.bssids_with_handshakes(self.capfile, bssid=self.bssid)
        return [(bssid, None) for bssid in tshark_bssids]

    def cowpatty_handshakes(self):
        """Returns list[tuple] of BSSID & ESSID pairs (BSSIDs are always `None`)."""
        if not Process.exists('cowpatty'):
            return []

        # Needs to check if cowpatty is updated and have the -2 parameter
        cowpattycheck = Process('cowpatty', devnull=False)

        command = [
            'cowpatty',
            '-2' if 'frames 1 and 2 or 2 and 3 for key attack' in cowpattycheck.stdout() else '',
            '-r',   self.capfile,
            '-c'    # Check for handshake
        ]

        proc = Process(command, devnull=False)
        return next(
            (
                [(None, self.essid)]
                for line in proc.stdout().split('\n')
                if 'Collected all necessary data to '
                'mount crack against WPA' in line
            ),
            [],
        )

    def aircrack_handshakes(self):
        """Returns tuple (BSSID,None) if aircrack thinks self.capfile contains a handshake / can be cracked"""
        if not self.bssid:
            return []  # Aircrack requires BSSID

        command = [
            'aircrack-ng',
            '-b', self.bssid,
            self.capfile
        ]

        proc = Process(command, devnull=False)

        if 'potential target' in proc.stdout().lower() and 'no matching network' not in proc.stdout().lower():
            return [(self.bssid, None)]
        else:
            return []

    def analyze(self):
        """Prints analysis of handshake capfile"""
        self.divine_bssid_and_essid()

        if Tshark.exists():
            Handshake.print_pairs(self.tshark_handshakes(), 'tshark')

        if Process.exists('cowpatty'):
            Handshake.print_pairs(self.cowpatty_handshakes(), 'cowpatty')

        Handshake.print_pairs(self.aircrack_handshakes(), 'aircrack')

    def strip(self, outfile=None):
        # XXX: This method might break aircrack-ng, use at own risk.
        """
            Strips out packets from handshake that aren't necessary to crack.
            Leaves only handshake packets and SSID broadcast (for discovery).
            Args:
                outfile - Filename to save stripped handshake to.
                          If outfile==None, overwrite existing self.capfile.
        """
        if not outfile:
            outfile = f'{self.capfile}.temp'
            replace_existing_file = True
        else:
            replace_existing_file = False

        cmd = [
            'tshark',
            '-r', self.capfile,  # input file
            '-Y', 'wlan.fc.type_subtype == 0x08 || wlan.fc.type_subtype == 0x05 || eapol',  # filter
            '-w', outfile  # output file
        ]
        proc = Process(cmd)
        proc.wait()
        if replace_existing_file:
            from shutil import copy
            copy(outfile, self.capfile)
            os.remove(outfile)

    @staticmethod
    def print_pairs(pairs, tool=None):
        """
            Prints out BSSID and/or ESSID given a list of tuples (bssid,essid)
        """
        tool_str = '{C}%s{W}: ' % tool.rjust(8) if tool is not None else ''
        if len(pairs) == 0:
            Color.pl('{!} %s.cap file {R}does not{O} contain a valid handshake{W}' % tool_str)
            return

        for (bssid, essid) in pairs:
            out_str = '{+} %s.cap file {G}contains a valid handshake{W} for' % tool_str
            if bssid and essid:
                Color.pl('%s ({G}%s{W}) [{G}%s{W}]' % (out_str, bssid, essid))
            elif bssid:
                Color.pl('%s ({G}%s{W})' % (out_str, bssid))
            elif essid:
                Color.pl('%s [{G}%s{W}]' % (out_str, essid))

    @staticmethod
    def check():
        """ Analyzes .cap file(s) for handshake """
        from ..config import Configuration
        if Configuration.check_handshake == '<all>':
            Color.pl('{+} checking all handshakes in {G}"./hs"{W} directory\n')
            try:
                capfiles = [os.path.join('hs', x) for x in os.listdir('hs') if x.endswith('.cap')]
            except OSError:
                capfiles = []
            if not capfiles:
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
    print("\n-------------------------------")
    print('With BSSID & ESSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap', bssid='18:d6:c7:6d:6b:18', essid='YZWifi')
    hs.analyze()
    print(('has_hanshake() =', hs.has_handshake()))

    print("\n-------------------------------")
    print('\nWith BSSID, but no ESSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap', bssid='18:d6:c7:6d:6b:18')
    hs.analyze()
    print(('has_hanshake() =', hs.has_handshake()))

    print("\n-------------------------------")
    print('\nWith ESSID, but no BSSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap', essid='YZWifi')
    hs.analyze()
    print(('has_hanshake() =', hs.has_handshake()))

    print("\n-------------------------------")
    print('\nWith neither BSSID nor ESSID specified:')
    hs = Handshake('./tests/files/handshake_has_1234.cap')
    try:
        hs.analyze()
        print(('has_hanshake() =', hs.has_handshake()))
    except Exception as e:
        Color.pl('{O}Error during Handshake.analyze(): {R}%s{W}' % e)
