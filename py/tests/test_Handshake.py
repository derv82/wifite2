#!/usr/bin/python

from Handshake import Handshake

import unittest

class TestHandshake(unittest.TestCase):
    ''' Test suite for Target parsing an generation '''

    def getFile(self, filename):
        ''' Helper method to parse targets from filename '''
        import os, inspect
        this_file = os.path.abspath(inspect.getsourcefile(self.getFile))
        this_dir = os.path.dirname(this_file)
        return os.path.join(this_dir, 'files', filename)

    def testAnalyze(self):
        hs_file = self.getFile('handshake_exists.cap')
        hs = Handshake(hs_file, bssid='30:85:a9:39:d2:18')
        try:
            hs.analyze()
        except Exception, e:
            fail()

    def testHandshakeTshark(self):
        hs_file = self.getFile('handshake_exists.cap')
        hs = Handshake(hs_file, bssid='30:85:a9:39:d2:18')
        assert(len(hs.tshark_handshakes()) > 0)

    def testHandshakePyrit(self):
        hs_file = self.getFile('handshake_exists.cap')
        hs = Handshake(hs_file, bssid='30:85:a9:39:d2:18')
        assert(len(hs.pyrit_handshakes()) > 0)

    def testHandshakeCowpatty(self):
        hs_file = self.getFile('handshake_exists.cap')
        hs = Handshake(hs_file, bssid='30:85:a9:39:d2:18')
        hs.divine_bssid_and_essid()
        assert(len(hs.cowpatty_handshakes()) > 0)

    def testHandshakeAircrack(self):
        hs_file = self.getFile('handshake_exists.cap')
        hs = Handshake(hs_file, bssid='30:85:a9:39:d2:18')
        assert(len(hs.aircrack_handshakes()) > 0)


if __name__ == '__main__':
    unittest.main()

