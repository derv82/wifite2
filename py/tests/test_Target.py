#!/usr/bin/python

from Airodump import Airodump

import unittest

class TestTarget(unittest.TestCase):
    ''' Test suite for Target parsing an generation '''

    airodump_csv = 'airodump.csv'

    def getTargets(self, filename):
        ''' Helper method to parse targets from filename '''
        import os, inspect
        this_file = os.path.abspath(inspect.getsourcefile(TestTarget.getTargets))
        this_dir = os.path.dirname(this_file)
        csv_file = os.path.join(this_dir, 'files', filename)
        # Load targets from CSV file
        return Airodump.get_targets_from_csv(csv_file)

    def testTargetParsing(self):
        ''' Asserts target parsing finds targets '''
        targets = self.getTargets(TestTarget.airodump_csv)
        assert(len(targets) > 0)

    def testTargetClients(self):
        ''' Asserts target parsing captures clients properly '''
        targets = self.getTargets(TestTarget.airodump_csv)
        for t in targets:
            if t.bssid == '00:1D:D5:9B:11:00':
                assert(len(t.clients) > 0)

    def testTargetFilter(self):
        ''' Asserts target filtering works '''
        targets = self.getTargets(TestTarget.airodump_csv)

        opnTargets = Airodump.filter_targets(targets, opn=True, wpa=False, wep=False)
        for t in opnTargets:
            if 'OPN' not in t.encryption:
                fail()

        wpaTargets = Airodump.filter_targets(targets, opn=False, wpa=True, wep=False)
        for t in wpaTargets:
            if 'WPA' not in t.encryption:
                fail()

        wepTargets = Airodump.filter_targets(targets, opn=False, wpa=False, wep=True)
        for t in wepTargets:
            if 'WEP' not in t.encryption:
                fail()

if __name__ == '__main__':
    unittest.main()
