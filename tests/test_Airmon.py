#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import unittest
from wifite.tools.airmon import Airmon

sys.path.insert(0, '..')


class TestAirmon(unittest.TestCase):
    def test_airmon_start(self):
        # From https://github.com/derv82/wifite2/issues/67
        stdout = ('\n'
                  'PHY    Interface    Driver        Chipset\n'
                  '\n'
                  'phy0    wlan0        iwlwifi        Intel Corporation Centrino Ultimate-N 6300 (rev 3e)\n'
                  '\n'
                  '        (mac80211 monitor mode vif enabled for [phy0]wlan0 on [phy0]wlan0mon)\n'
                  '        (mac80211 station mode vif disabled for [phy0]wlan0)\n')
        mon_iface = Airmon._parse_airmon_start(stdout)
        assert mon_iface == 'wlan0mon', f'Expected monitor-mode interface to be "wlan0mon" but got "{mon_iface}"'
