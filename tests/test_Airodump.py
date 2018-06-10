#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '..')

from wifite.tools.airodump import Airodump

import unittest

class TestAirodump(unittest.TestCase):
    ''' Test suite for Wifite's interaction with the Airodump tool '''


    def test_airodump_weird_characters(self):
        csv_filename = self.getFile('airodump-weird-ssids.csv')
        targets = Airodump.get_targets_from_csv(csv_filename)

        target = targets[0]
        expected = 'Comma, no trailing space'
        assert target.essid == expected, 'Expected ESSID (%s) but got (%s)' % (expected, target.essid)

        target = targets[1]
        expected = '"Quoted ESSID, Comma, no trailing spaces.   "'
        assert target.essid == expected, 'Expected ESSID (%s) but got (%s)' % (expected, target.essid)

        target = targets[2]
        expected = 'Comma, Trailing space '
        assert target.essid == expected, 'Expected ESSID (%s) but got (%s)' % (expected, target.essid)

        target = targets[3]
        expected = '"quote" comma, trailing space '
        assert target.essid == expected, 'Expected ESSID (%s) but got (%s)' % (expected, target.essid)

        # Hidden access point
        target = targets[4]
        assert target.essid_known == False, 'ESSID full of null characters should not be known'
        expected = None
        assert target.essid == expected, 'Expected ESSID (%s) but got (%s)' % (expected, target.essid)
        assert target.essid_len == 19, 'ESSID length shold be 19, but got %s' % target.essid_len


    def getFile(self, filename):
        ''' Helper method to parse targets from filename '''
        import os, inspect
        this_file = os.path.abspath(inspect.getsourcefile(self.getFile))
        this_dir = os.path.dirname(this_file)
        return os.path.join(this_dir, 'files', filename)


if __name__ == '__main__':
    unittest.main()
