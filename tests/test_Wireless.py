#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '..')

from wifite.tools.wireless import Wireless
from wifite.tools.iwconfig import Iwconfig
from wifite.tools.iw import Iw

import unittest


class TestWireless(unittest.TestCase):
    '''
    The Wireless dispatcher prefers iwconfig (backwards-compat) and falls back
    to iw when wireless-tools is missing (issue #542). Either tool satisfies
    the dependency check.
    '''

    def setUp(self):
        self._iwc, self._iw = Iwconfig.exists, Iw.exists

    def tearDown(self):
        Iwconfig.exists, Iw.exists = self._iwc, self._iw

    @staticmethod
    def _stub(present):
        return classmethod(lambda cls: present)

    def test_prefers_iwconfig_when_present(self):
        Iwconfig.exists, Iw.exists = self._stub(True), self._stub(True)
        assert Wireless.backend() is Iwconfig

    def test_falls_back_to_iw_without_iwconfig(self):
        Iwconfig.exists, Iw.exists = self._stub(False), self._stub(True)
        assert Wireless.backend() is Iw

    def test_dependency_ok_with_only_iw(self):
        Iwconfig.exists, Iw.exists = self._stub(False), self._stub(True)
        assert Wireless.fails_dependency_check() is False

    def test_dependency_ok_with_only_iwconfig(self):
        Iwconfig.exists, Iw.exists = self._stub(True), self._stub(False)
        assert Wireless.fails_dependency_check() is False

    def test_dependency_fails_when_neither_present(self):
        Iwconfig.exists, Iw.exists = self._stub(False), self._stub(False)
        assert Wireless.fails_dependency_check() is True


if __name__ == '__main__':
    unittest.main()
