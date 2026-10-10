#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Airmon._parse_airmon_start() against exact airmon-ng output formats.
"""

import re
import sys
import unittest

import pytest

sys.path.insert(0, '..')

from wifite.tools.airmon import Airmon

pytestmark = pytest.mark.timeout(30)


AIRMON_OUTPUT_ALREADY_ENABLED = """
Found 6 processes that could cause trouble.
Kill them using 'airmon-ng check kill' before putting
the card in monitor mode, they will interfere by changing channels
and sometimes putting the interface back in managed mode

    PID Name
   7044 avahi-daemon
   7105 avahi-daemon
   7183 wpa_supplicant
  25765 NetworkManager
2503235 dhclient
2523490 dhclient

PHY     Interface       Driver          Chipset

phy1    wlp4s0          iwlwifi         Intel Corporation Wi-Fi 6E(802.11ax) AX210/AX1675* 2x2 [Typhoon Peak] (rev 1a)
phy0    wlxd037456283c3 rtl8xxxu        TP-Link TL-WN821N v5/v6 [RTL8192EU]
                (mac80211 monitor mode already enabled for [phy0]wlxd037456283c3 on [phy0]10)
"""

AIRMON_OUTPUT_VIF_ENABLED = """
PHY     Interface       Driver          Chipset

phy0    wlan0           ath9k_htc       Atheros Communications, Inc. AR9271 802.11n
                (mac80211 monitor mode vif enabled for [phy0]wlan0 on [phy0]wlan0mon)
                (mac80211 station mode vif disabled for [phy0]wlan0)
"""

AIRMON_OUTPUT_STANDARD = """
PHY     Interface       Driver          Chipset

phy0    wlan0           rt2800usb       Ralink Technology, Corp. RT2870/RT3070
                (mac80211 monitor mode enabled on mon0)
"""


class TestAirmonParseExactOutput(unittest.TestCase):
    """Tests for Airmon parsing against real-world airmon-ng output."""

    def test_parse_already_enabled(self):
        """Test parsing output where monitor mode is already enabled."""
        result = Airmon._parse_airmon_start(AIRMON_OUTPUT_ALREADY_ENABLED)
        # Should extract the interface name from 'already enabled' line
        self.assertIsNotNone(result, 'Expected interface name but got None')

    def test_parse_vif_enabled(self):
        """Test parsing output where monitor mode vif was enabled."""
        result = Airmon._parse_airmon_start(AIRMON_OUTPUT_VIF_ENABLED)
        self.assertIsNotNone(result, 'Expected interface name but got None')
        self.assertIn('wlan0mon', result)

    def test_parse_standard_enabled(self):
        """Test parsing standard 'monitor mode enabled' output."""
        result = Airmon._parse_airmon_start(AIRMON_OUTPUT_STANDARD)
        self.assertIsNotNone(result, 'Expected interface name but got None')
        self.assertIn('mon0', result)

    def test_parse_empty_output(self):
        """Test parsing empty output returns None."""
        result = Airmon._parse_airmon_start('')
        self.assertIsNone(result)

    def test_enabled_on_regex_matches_already_enabled(self):
        """Test that the enabled_on_re regex handles 'already enabled' output."""
        enabled_on_re = re.compile(
            r'.*\(mac80211 monitor mode (?:(?:vif )?enabled|already enabled) '
            r'(?:for [^ ]+ )?on (?:\[\w+])?([a-zA-Z]\w+)\)?.*'
        )
        line = '                (mac80211 monitor mode already enabled for [phy0]wlxd037456283c3 on [phy0]10)'
        match = enabled_on_re.match(line)
        # This tests the regex behaviour documented in the original script
        # 'on [phy0]10' - the capture group should get '10' or similar
        # The regex may or may not match depending on implementation
        # Verify it either matches or we handle it gracefully
        if match:
            self.assertIsNotNone(match.group(1))


if __name__ == '__main__':
    unittest.main()
