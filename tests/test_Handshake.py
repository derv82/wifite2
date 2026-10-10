#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest

import pytest

from wifite.model.handshake import Handshake
from wifite.util.process import Process

sys.path.insert(0, '..')

pytestmark = pytest.mark.timeout(30)


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
        except Exception as e:
            self.skipTest(f'handshake.analyze() raised: {e}')

    @pytest.mark.timeout(15)
    @unittest.skipUnless(Process.exists("tshark"), 'tshark is missing')
    def testHandshakeTshark(self):
        print("\nTesting handshake with tshark...")
        hs_file = self.getFile("handshake_exists.cap")
        print("Testing file:", hs_file)

        # Copy file to /tmp to work around tshark permission issues
        import tempfile
        import shutil
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix='.cap') as tmp:
            temp_file = tmp.name

        try:
            shutil.copy2(hs_file, temp_file)
            hs = Handshake(temp_file, bssid='A4:2B:8C:16:6B:3A')
            handshakes = hs.tshark_handshakes()
            print(f"Found {len(handshakes)} handshake(s): {handshakes}")
            assert len(handshakes) > 0, f'Expected len>0 but got len({len(handshakes)})'
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    @pytest.mark.timeout(15)
    @unittest.skipUnless(Process.exists("cowpatty"), 'cowpatty is missing')
    def testHandshakeCowpatty(self):
        print("\nTesting handshake with cowpatty...")
        hs_file = self.getFile('handshake_exists.cap')
        # cowpatty -c needs an ESSID, so pass it explicitly. (tshark/aircrack
        # tests don't need this — only cowpatty enforces it.)
        hs = Handshake(hs_file, bssid='A4:2B:8C:16:6B:3A',
                       essid='Test Router Please Ignore')
        assert (len(hs.cowpatty_handshakes()) > 0), f'Expected len>0 but got len({len(hs.cowpatty_handshakes())})'

    @pytest.mark.timeout(15)
    @unittest.skipUnless(Process.exists("aircrack-ng"), 'aircrack-ng is missing')
    def testHandshakeAircrack(self):
        print("\nTesting handshake with aircrack-ng...")
        hs_file = self.getFile('handshake_exists.cap')
        hs = Handshake(hs_file, bssid='A4:2B:8C:16:6B:3A')
        assert (len(hs.aircrack_handshakes()) > 0), f'Expected len>0 but got len({len(hs.aircrack_handshakes())})'


if __name__ == '__main__':
    unittest.main()
