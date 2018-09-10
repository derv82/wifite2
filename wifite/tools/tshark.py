#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..model.target import WPSState
from ..util.process import Process
import re

class Tshark(Dependency):
    ''' Wrapper for Tshark program. '''
    dependency_required = False
    dependency_name = 'tshark'
    dependency_url = 'apt-get install wireshark'

    def __init__(self):
        pass


    @staticmethod
    def _extract_src_dst_index_total(line):
        # Extract BSSIDs, handshake # (1-4) and handshake 'total' (4)
        mac_regex = ('[a-zA-Z0-9]{2}:' * 6)[:-1]
        match = re.search('(%s)\s*.*\s*(%s).*Message.*(\d).*of.*(\d)' % (mac_regex, mac_regex), line)
        if match is None:
            # Line doesn't contain src, dst, Message numbers
            return None, None, None, None
        (src, dst, index, total) = match.groups()
        return src, dst, index, total


    @staticmethod
    def _build_target_client_handshake_map(output, bssid=None):
        # Map of target_ssid,client_ssid -> handshake #s
        # E.g. 12:34:56,21:43:65 -> 3
        target_client_msg_nums = {}

        for line in output.split('\n'):
            src, dst, index, total = Tshark._extract_src_dst_index_total(line)

            if src is None: continue # Skip

            index = int(index)
            total = int(total)

            if total != 4: continue # Handshake X of 5? X of 3? Skip it.

            # Identify the client and target MAC addresses
            if index % 2 == 1:
                # First and Third messages
                target = src
                client = dst
            else:
                # Second and Fourth messages
                client = src
                target = dst

            if bssid is not None and bssid.lower() != target.lower():
                # We know the BSSID and this msg was not for the target
                continue

            target_client_key = '%s,%s' % (target, client)

            # Ensure all 4 messages are:
            # Between the same client and target (not different clients connecting).
            # In numeric & chronological order (Message 1, then 2, then 3, then 4)
            if index == 1:
                target_client_msg_nums[target_client_key] = 1 # First message

            elif target_client_key not in target_client_msg_nums:
                continue # Not first message. We haven't gotten the first message yet. Skip.

            elif index - 1 != target_client_msg_nums[target_client_key]:
                continue # Message is not in sequence. Skip

            else:
                # Happy case: Message is > 1 and is received in-order
                target_client_msg_nums[target_client_key] = index

        return target_client_msg_nums


    @staticmethod
    def bssids_with_handshakes(capfile, bssid=None):
        if not Tshark.exists():
            return []

        # Returns list of BSSIDs for which we have valid handshakes in the capfile.
        command = [
            'tshark',
            '-r', capfile,
            '-n', # Don't resolve addresses
            '-Y', 'eapol' # Filter for only handshakes
        ]
        tshark = Process(command, devnull=False)

        target_client_msg_nums = Tshark._build_target_client_handshake_map(tshark.stdout(), bssid=bssid)

        bssids = set()
        # Check if we have all 4 messages for the handshake between the same MACs
        for (target_client, num) in target_client_msg_nums.items():
            if num == 4:
                # We got a handshake!
                this_bssid = target_client.split(',')[0]
                bssids.add(this_bssid)

        return list(bssids)


    @staticmethod
    def bssid_essid_pairs(capfile, bssid):
        # Finds all BSSIDs (with corresponding ESSIDs) from cap file.
        # Returns list of tuples(BSSID, ESSID)

        if not Tshark.exists():
            return []

        ssid_pairs = set()

        command = [
            'tshark',
            '-r', capfile, # Path to cap file
            '-n', # Don't resolve addresses
            # Extract beacon frames
            '-Y', '"wlan.fc.type_subtype == 0x08 || wlan.fc.type_subtype == 0x05"',
        ]
        tshark = Process(command, devnull=False)

        for line in tshark.stdout().split('\n'):
            # Extract src, dst, and essid
            mac_regex = ('[a-zA-Z0-9]{2}:' * 6)[:-1]
            match = re.search('(%s) [^ ]* (%s).*.*SSID=(.*)$' % (mac_regex, mac_regex), line)
            if match is None:
                continue # Line doesn't contain src, dst, ssid

            (src, dst, essid) = match.groups()

            if dst.lower() == 'ff:ff:ff:ff:ff:ff':
                continue # Skip broadcast packets

            if bssid is not None:
                # We know the BSSID, only return the ESSID for this BSSID.
                if bssid.lower() == src.lower():
                    ssid_pairs.add((src, essid)) # This is our BSSID, add it
            else:
                ssid_pairs.add((src, essid)) # We do not know BSSID, add it.

        return list(ssid_pairs)


    @staticmethod
    def check_for_wps_and_update_targets(capfile, targets):
        '''
            Given a cap file and list of targets, use TShark to
            find which BSSIDs in the cap file use WPS.
            Then update the 'wps' flag for those BSSIDs in the targets.

            Args:
                capfile - .cap file from airodump containing packets
                targets - list of Targets from scan, to be updated
        '''
        from ..config import Configuration

        if not Tshark.exists():
            raise ValueError('Cannot detect WPS networks: Tshark does not exist')

        command = [
            'tshark',
            '-r', capfile, # Path to cap file
            '-n', # Don't resolve addresses
            # Filter WPS broadcast packets
            '-Y', 'wps.wifi_protected_setup_state && wlan.da == ff:ff:ff:ff:ff:ff',
            '-T', 'fields', # Only output certain fields
            '-e', 'wlan.ta', # BSSID
            '-e', 'wps.ap_setup_locked', # Locked status
            '-E', 'separator=,' # CSV
        ]
        p = Process(command)

        try:
            p.wait()
            lines = p.stdout()
        except:
            # Failure is acceptable
            return

        wps_bssids = set()
        locked_bssids = set()
        for line in lines.split('\n'):
            if ',' not in line:
                continue
            bssid, locked = line.split(',')
            if '1' not in locked:
                wps_bssids.add(bssid.upper())
            else:
                locked_bssids.add(bssid.upper())

        for t in targets:
            target_bssid = t.bssid.upper()
            if target_bssid in wps_bssids:
                t.wps = WPSState.UNLOCKED
            elif target_bssid in locked_bssids:
                t.wps = WPSState.LOCKED
            else:
                t.wps = WPSState.NONE


if __name__ == '__main__':
    test_file = './tests/files/contains_wps_network.cap'

    target_bssid = 'A4:2B:8C:16:6B:3A'
    from ..model.target import Target
    fields = [
        'A4:2B:8C:16:6B:3A', # BSSID
        '2015-05-27 19:28:44', '2015-05-27 19:28:46', # Dates
        '11', # Channel
        '54', # throughput
        'WPA2', 'CCMP TKIP', 'PSK', # AUTH
        '-58', '2', '0', '0.0.0.0', '9', # ???
        'Test Router Please Ignore', # SSID
    ]
    t = Target(fields)
    targets = [t]

    # Should update 'wps' field of a target
    Tshark.check_for_wps_and_update_targets(test_file, targets)

    print('Target(BSSID={}).wps = {} (Expected: 1)'.format(
        targets[0].bssid, targets[0].wps))
    assert targets[0].wps == WPSState.UNLOCKED

    print(Tshark.bssids_with_handshakes(test_file, bssid=target_bssid))
