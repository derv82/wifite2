#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Process import Process
from Color import Color

import re
import os

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
        pairs = self.tshark_bssid_essid_pairs()
        if len(pairs) == 0:
            # Find bssid/essid pairs that have handshakes in Pyrit
            pairs = self.pyrit_handshakes()

        if len(pairs) == 0 and not self.bssid and not self.essid:
            # Tshark and Pyrit failed us, nothing else we can do.
            raise Exception("Cannot find BSSID or ESSID in cap file")

        if not self.essid and not self.bssid:
            # We do not know the bssid nor the essid
            # TODO: Display menu for user to select from list
            # HACK: Just use the first one we see
            self.bssid = pairs[0][0]
            self.essid = pairs[0][1]
            Color.pl('{!} {O}Warning{W}:' +
                ' {O}Arbitrarily selected' +
                ' {R}bssid{O} {C}%s{O} and {R}essid{O} "{C}%s{O}"{W}'
                    % (self.bssid, self.essid))

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

        if len(self.tshark_handshakes()) > 0:
            return True

        if len(self.pyrit_handshakes()) > 0:
            return True


        # XXX: Disabling these checks since I don't think they are reliable.
        '''
        if len(self.cowpatty_handshakes()) > 0:
            return True
        if len(self.aircrack_handshakes()) > 0:
            return True
        '''
        return False


    def tshark_bssid_essid_pairs(self):
        '''
            Scrapes capfile for beacon frames indicating the ESSID.
            Returns list of tuples: (bssid,essid)
        '''
        if not Process.exists('tshark'):
            raise Exception('tshark is required to find ESSID')

        essids = set()

        # Extract beacon frames from cap file
        cmd = [
            'tshark',
            '-r', self.capfile,
            '-R', 'wlan.fc.type_subtype == 0x08 || wlan.fc.type_subtype == 0x05',
            '-2', # tshark: -R without -2 is deprecated.
            '-n'
        ]
        proc = Process(cmd, devnull=False)
        for line in proc.stdout().split('\n'):
            # Extract src, dst, and essid
            mac_regex = ('[a-zA-Z0-9]{2}:' * 6)[:-1]
            match = re.search('(%s) [^ ]* (%s).*.*SSID=(.*)$'
                % (mac_regex, mac_regex), line)
            if match == None:
                # Line doesn't contain src, dst, ssid
                continue
            (src, dst, essid) = match.groups()
            if dst.lower() == "ff:ff:ff:ff:ff:ff": continue
            if self.bssid:
                # We know the BSSID, only return the ESSID for this BSSID.
                if self.bssid.lower() == src.lower() or self.bssid.lower() == dst.lower():
                    essids.add((src, essid))
            else:
                # We do not know BSSID, add it.
                essids.add((src, essid))
        # Return list of tuples
        return [x for x in essids]


    def tshark_command(self):
        return [
            'tshark',
            '-r', self.capfile,
            '-R', 'eapol',
            '-n',
            '-2' # 2-pass filtering, required when using -R in newer versions of tshark
        ]

    def tshark_handshakes(self):
        ''' Returns True if tshark identifies a handshake, False otherwise '''
        if not Process.exists('tshark'):
            return []

        target_client_msg_nums = {}

        # Dump EAPOL packets
        proc = Process(self.tshark_command(), devnull=False)
        for line in proc.stdout().split('\n'):
            # Extract source mac, destination mac, and message numbers
            mac_regex = ('[a-zA-Z0-9]{2}:' * 6)[:-1]
            match = re.search('(%s) (?:->|→) (%s).*Message.*(\d).*(\d)'
                % (mac_regex, mac_regex), line)
            if match == None:
                # Line doesn't contain src, dst, Message numbers
                continue
            (src, dst, index, ttl) = match.groups()
            # "Message (index) of (ttl)"
            index = int(index)
            ttl = int(ttl)

            if ttl != 4:
                # Must be a 4-way handshake
                continue

            # Identify the client and target MAC addresses
            if index % 2 == 1:
                # First and Third messages
                target = src
                client = dst
            else:
                # Second and Fourth messages
                client = src
                target = dst

            if self.bssid and self.bssid.lower() != target.lower():
                # We know the BSSID and this msg was not for the target
                continue

            target_client_key = '%s,%s' % (target, client)

            # Ensure all 4 messages are:
            # Between the same client and target
            # In numeric & chronological order (1,2,3,4)
            if index == 1:
                # First message, add to dict
                target_client_msg_nums[target_client_key] = 1

            elif target_client_key not in target_client_msg_nums:
                # Not first message, we haven't gotten the first message yet
                continue

            elif index - 1 != target_client_msg_nums[target_client_key]:
                # Message is not in sequence
                continue

            else:
                # Message is > 1 and is received in-order
                target_client_msg_nums[target_client_key] = index

        bssids = set()
        # Check if we have all 4 messages for the handshake between the same MACs
        for (client_target, num) in target_client_msg_nums.iteritems():
            if num == 4:
                # We got a handshake!
                bssid = client_target.split(',')[0]
                bssids.add(bssid)

        return [(bssid, None) for bssid in bssids]


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
                    # This AccessPoint is not what we're looking for
                    hit_Target = False
            else:
                # Line does not contain AccessPoint
                if hit_target and ', good' in line:
                    bssid_essid_pairs.add( (current_bssid, current_essid) )
        return [x for x in bssid_essid_pairs]


    def aircrack_command(self):
        return 'echo "" | aircrack-ng -a 2 -w - -b %s "%s"' % (self.bssid, self.capfile)

    def aircrack_handshakes(self):
        if not self.bssid:
            return []
        (stdout, stderr) = Process.call(self.aircrack_command())
        if 'passphrase not in dictionary' in stdout.lower():
            return [(self.bssid, None)]
        else:
            return []

    def analyze(self):
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
            '-R', 'wlan.fc.type_subtype == 0x08 || wlan.fc.type_subtype == 0x05 || eapol', # filter
            '-2', # tshark: -R without -2 is deprecated.
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
    hs = Handshake('./tests/files/handshake_exists.cap', bssid='A4:2B:8C:16:6B:3A')

    hs.analyze()
    print "has_hanshake() =", hs.has_handshake()

