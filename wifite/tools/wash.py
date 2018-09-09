#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..model.target import WPSState
from ..util.process import Process
import json

class Wash(Dependency):
    ''' Wrapper for Wash program. '''
    dependency_required = False
    dependency_name = 'wash'
    dependency_url = 'https://github.com/t6x/reaver-wps-fork-t6x'

    def __init__(self):
        pass


    @staticmethod
    def check_for_wps_and_update_targets(capfile, targets):
        if not Wash.exists():
            return

        command = [
            'wash',
            '-f', capfile,
            '-j' # json
        ]

        p = Process(command)
        try:
            p.wait()
            lines = p.stdout()
        except:
            # Failure is acceptable
            return

        # Find all BSSIDs
        wps_bssids = set()
        locked_bssids = set()
        for line in lines.split('\n'):
            try:
                obj = json.loads(line)
                bssid = obj['bssid']
                locked = obj['wps_locked']
                if locked != True:
                    wps_bssids.add(bssid)
                else:
                    locked_bssids.add(bssid)
            except:
                pass

        # Update targets
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
    Wash.check_for_wps_and_update_targets(test_file, targets)

    print('Target(BSSID={}).wps = {} (Expected: 1)'.format(
        targets[0].bssid, targets[0].wps))

    assert targets[0].wps == WPSState.UNLOCKED

