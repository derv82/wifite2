#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Process import Process
import re

class Wash(object):
    ''' Wrapper for Wash program. '''
    BSSID_REGEX = re.compile("([A-F0-9\:]{17})", re.IGNORECASE)

    def __init__(self):
        pass

    @staticmethod
    def check_for_wps_and_update_targets(capfile, targets):
        '''
            Given a cap file and list of targets, use Wash to
            find which BSSIDs in the cap file use WPS.
            Then update the 'wps' flag for those BSSIDs in the targets.

            Args:
                capfile - .cap file from airodump containing packets
                targets - list of Targets from scan, to be updated
        '''
        # Wash/Walsh is required to detect WPS
        wash_name = 'wash'
        if not Process.exists(wash_name):
            wash_name = 'walsh'
            if not Process.exists(wash_name):
                # Wash isn't found, drop out
                return

        command = [
            'wash',
            '-f', capfile # Path to cap file
        ]
        p = Process(command)

        p.wait()
        if p.poll() != 0:
            return

        bssids = [bssid.upper() for bssid in Wash.BSSID_REGEX.findall(p.stdout())]
        for t in targets:
            t.wps = t.bssid.upper() in bssids


if __name__ == '__main__':
    from Target import Target
    # Test target within range
    fields = 'A4:2B:8C:16:6B:3A,2015-05-27 19:28:44,2015-05-27 19:28:46,11,54,WPA2,CCMP TKIP,PSK,-58,2,0,0.0.0.0,9,Test Router Please Ignore,'.split(',')
    t = Target(fields)
    targets = [t]
    Wash.check_for_wps_and_update_targets('./tests/files/handshake_exists.cap', targets)
    print targets[0].bssid, 'WPS =', targets[0].wps

