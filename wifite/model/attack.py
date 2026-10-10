#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from ..config import Configuration


class Attack:
    """Contains functionality common to all attacks."""

    @staticmethod
    def _get_target_wait():
        """Get target wait time, safely handling uninitialized Configuration."""
        timeout = Configuration.wpa_attack_timeout
        if timeout is None:
            return 60
        return min(60, timeout)

    def __init__(self, target):
        self.target = target

    def run(self):
        raise Exception('Unimplemented method: run')

    def wait_for_target(self, airodump):
        """Waits for target to appear in airodump."""
        target_wait = Attack._get_target_wait()
        start_time = time.time()
        targets = airodump.get_targets(apply_filter=False)
        while len(targets) == 0:
            # Wait for target to appear in airodump.
            if int(time.time() - start_time) > target_wait:
                raise Exception(f'Target did not appear after {target_wait:d} seconds, target may be out of range or turned off')
            time.sleep(1)
            targets = airodump.get_targets()
            continue

        airodump_target = next((t for t in targets if t.bssid == self.target.bssid), None)

        if airodump_target is None:
            raise Exception(f'Could not find target ({self.target.bssid}) in airodump')

        return airodump_target
