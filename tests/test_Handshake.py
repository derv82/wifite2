#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest

from wifite.model.handshake import Handshake
from wifite.util.process import Process

sys.path.insert(0, '..')


class TestHandshake(unittest.TestCase):
    """ Test suite for Target parsing an generation """

    def getFile(self, filename):
        """ Helper method to parse targets from filename """
        import os
        import inspect
        this_file = os.path.abspath(inspect.getsourcefile(self.getFile))
        this_dir = os.path.dirname(this_file)
        return os.path.join(this_dir, 'files', filename)

    def testAnalyze(self):
        hs_file = self.getFile("handshake_exists.cap")
        hs = Handshake(hs_file, bssid='A4:2B:8C:16:6B:3A')
        try:
            hs.analyze()
        except Exception:
            exit()

    @unittest.skipUnless(Process.exists("tshark"), 'tshark is missing')
    def testHandshakeTshark(self):
        print("\nTesting handshake with tshark...")
        hs_file = self.getFile("handshake_exists.cap")
        hs = Handshake(hs_file, bssid='A4:2B:8C:16:6B:3A')
        assert (len(hs.tshark_handshakes()) > 0), f'Expected len>0 but got len({len(hs.tshark_handshakes())})'

    @unittest.skipUnless(Process.exists("cowpatty"), 'cowpatty is missing')
    def testHandshakeCowpatty(self):
        print("\nTesting handshake with cowpatty...")
        hs_file = self.getFile('handshake_exists.cap')
        hs = Handshake(hs_file, bssid='A4:2B:8C:16:6B:3A')
        assert (len(hs.cowpatty_handshakes()) > 0), f'Expected len>0 but got len({len(hs.cowpatty_handshakes())})'

    @unittest.skipUnless(Process.exists("aircrack-ng"), 'aircrack-ng is missing')
    def testHandshakeAircrack(self):
        print("\nTesting handshake with aircrack-ng...")
        hs_file = self.getFile('handshake_exists.cap')
        hs = Handshake(hs_file, bssid='A4:2B:8C:16:6B:3A')
        assert (len(hs.aircrack_handshakes()) > 0), f'Expected len>0 but got len({len(hs.aircrack_handshakes())})'


if __name__ == '__main__':
    unittest.main()
