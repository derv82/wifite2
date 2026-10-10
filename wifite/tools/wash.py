#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from .dependency import Dependency
from ..config import Configuration
from ..model.target import WPSState
from ..util.color import Color
from ..util.logger import log_debug
from ..util.process import Process


class Wash(Dependency):
    """ Wrapper for Wash program. """
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
            '-j'  # json
        ]

        try:
            p = Process(command)
            p.wait()
            lines = p.stdout()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            if Configuration.verbose > 0:
                Color.pl('{!} {R}Wash error{W}: %s' % str(e))
            return

        # Find all BSSIDs
        wps_bssids = set()
        locked_bssids = set()
        for line in lines.split('\n'):
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            bssid = obj.get('bssid')
            locked = obj.get('wps_locked')
            if not isinstance(bssid, str) or bssid == '':
                continue
            bssid = bssid.upper()
            if locked is None:
                continue
            if not locked:
                wps_bssids.add(bssid)
            else:
                locked_bssids.add(bssid)
        log_debug('Wash', 'WPS scan: %d unlocked, %d locked out of %d targets' % (
            len(wps_bssids), len(locked_bssids), len(targets)))

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
        'A4:2B:8C:16:6B:3A',  # BSSID
        '2015-05-27 19:28:44', '2015-05-27 19:28:46',  # Dates
        '11',  # Channel
        '54',  # throughput
        'WPA2', 'CCMP TKIP', 'PSK',  # AUTH
        '-58', '2', '0', '0.0.0.0', '9',  # ???
        'Test Router Please Ignore',  # SSID
    ]
    t = Target(fields)
    targets = [t]

    # Should update 'wps' field of a target
    Wash.check_for_wps_and_update_targets(test_file, targets)

    print(f'Target(BSSID={targets[0].bssid}).wps = {targets[0].wps} (Expected: 1)')

    if targets[0].wps != WPSState.UNLOCKED:
        raise ValueError(f'Expected WPSState.UNLOCKED, got {targets[0].wps}')
