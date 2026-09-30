#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '..')

from wifite.tools.iw import Iw

import unittest


class TestIw(unittest.TestCase):
    ''' Test suite for parsing `iw dev` output into interface names. '''

    # Real single-card output (managed), captured from `iw dev`.
    SINGLE_MANAGED = '''phy#0
	Interface wlp6s0
		ifindex 3
		wdev 0x1
		addr 50:bb:b5:39:ad:70
		type managed
		txpower 20.00 dBm
'''

    # Two phys: one already in monitor mode, one managed.
    MULTI_WITH_MONITOR = '''phy#1
	Interface wlan1mon
		ifindex 6
		wdev 0x100000001
		addr 00:c0:ca:4e:ca:e0
		type monitor
		txpower 20.00 dBm
phy#0
	Interface wlan0
		ifindex 3
		wdev 0x1
		addr 50:bb:b5:39:ad:70
		type managed
'''

    def test_single_interface_all(self):
        ifaces = Iw._parse_iw_dev(self.SINGLE_MANAGED)
        assert ifaces == ['wlp6s0'], 'Expected [wlp6s0], got %s' % ifaces

    def test_monitor_filter_empty_when_all_managed(self):
        ifaces = Iw._parse_iw_dev(self.SINGLE_MANAGED, mode='Monitor')
        assert ifaces == [], 'Expected no monitor interfaces, got %s' % ifaces

    def test_all_interfaces_multi(self):
        ifaces = sorted(Iw._parse_iw_dev(self.MULTI_WITH_MONITOR))
        assert ifaces == ['wlan0', 'wlan1mon'], 'Expected both, got %s' % ifaces

    def test_monitor_filter_matches(self):
        ifaces = Iw._parse_iw_dev(self.MULTI_WITH_MONITOR, mode='Monitor')
        assert ifaces == ['wlan1mon'], 'Expected [wlan1mon], got %s' % ifaces

    def test_managed_filter_matches(self):
        ifaces = Iw._parse_iw_dev(self.MULTI_WITH_MONITOR, mode='Managed')
        assert ifaces == ['wlan0'], 'Expected [wlan0], got %s' % ifaces

    def test_help_text_yields_no_interfaces(self):
        # Regression for issue #542: when `iwconfig` was symlinked to `iw`,
        # the old parser turned `iw`'s usage/help text into fake interfaces
        # ("command", "Commands", "device", ...). The new parser keys off the
        # `Interface <name>` lines that only `iw dev` emits, so help text and
        # any other noise yields nothing.
        garbage = ('Usage:\tiwconfig [options] command\n'
                   'Options:\n'
                   'Commands:\n'
                   '\tdev <devname> ap start ...\n'
                   '\tphy <phyname> ...\n')
        assert Iw._parse_iw_dev(garbage) == [], 'Help text must not yield interfaces'

    def test_empty_output(self):
        assert Iw._parse_iw_dev('') == [], 'Empty output must yield no interfaces'


if __name__ == '__main__':
    unittest.main()
