#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Process import Process
import re

class Tshark(object):
    ''' Wrapper for Tshark program. '''

    def __init__(self):
        pass

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
        # Tshark is required to detect WPS networks
        if not Process.exists('tshark'):
            return

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

        bssids = set()
        for line in lines.split('\n'):
            if ',' not in line:
                continue
            bssid, locked = line.split(',')
            # Ignore if WPS is locked?
            if '1' not in locked:
                bssids.add(bssid.upper())

        for t in targets:
            t.wps = t.bssid.upper() in bssids


if __name__ == '__main__':
    test_file = './tests/files/contains_wps_network.cap'

    target_bssid = 'A4:2B:8C:16:6B:3A'
    from Target import Target
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

    print 'Target(BSSID={}).wps = {} (Expected: True)'.format(targets[0].bssid, targets[0].wps)
    assert targets[0].wps == True

