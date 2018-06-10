#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '..')

from wifite.tools.airmon import Airmon

import unittest

class TestAirmon(unittest.TestCase):
    def test_airmon_start(self):
        # From https://github.com/derv82/wifite2/issues/67
        stdout = '''
PHY    Interface    Driver        Chipset

phy0    wlan0        iwlwifi        Intel Corporation Centrino Ultimate-N 6300 (rev 3e)

        (mac80211 monitor mode vif enabled for [phy0]wlan0 on [phy0]wlan0mon)
        (mac80211 station mode vif disabled for [phy0]wlan0)
'''
        mon_iface = Airmon._parse_airmon_start(stdout)
        assert mon_iface == 'wlan0mon', 'Expected monitor-mode interface to be "wlan0mon" but got "{}"'.format(mon_iface)

