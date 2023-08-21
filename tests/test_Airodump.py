#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from wifite.tools.airodump import Airodump
import unittest

sys.path.insert(0, '..')


class TestAirodump(unittest.TestCase):
    """ Test suite for Wifite's interaction with the Airodump tool """

    def test_airodump(self):
        csv_filename = self.getFile('airodump.csv')
        targets = Airodump.get_targets_from_csv(csv_filename)

        print('')
        for target in targets:
            print("Testing ESSID: ", target.essid)
            if target.essid is not None:
                assert target.essid_len == len(target.essid), \
                    f'ESSID length is {target.essid_len} but ESSID is {len(target.essid)} - [{target.essid}]'

    def test_airodump_weird_characters(self):
        csv_filename = self.getFile('airodump-weird-ssids.csv')
        targets = Airodump.get_targets_from_csv(csv_filename)

        target = targets[0]
        expected = 'Comma, no trailing space'
        assert target.essid == expected, f'Expected ESSID ({expected}) but got ({target.essid})'

        target = targets[1]
        expected = '"Quoted ESSID, Comma, no trailing spaces.   "'
        assert target.essid == expected, f'Expected ESSID ({expected}) but got ({target.essid})'

        target = targets[2]
        expected = 'Comma, Trailing space '
        assert target.essid == expected, f'Expected ESSID ({expected}) but got ({target.essid})'

        target = targets[3]
        expected = '"quote" comma, trailing space '
        assert target.essid == expected, f'Expected ESSID ({expected}) but got ({target.essid})'

        # Hidden access point
        target = targets[4]
        assert target.essid_known is False, 'ESSID full of null characters should not be known'
        expected = None
        assert target.essid == expected, f'Expected ESSID ({expected}) but got ({target.essid})'
        assert target.essid_len == 19, f'ESSID [unknow chars] length should be 19, but got {target.essid_len}'

    def getFile(self, filename):
        """ Helper method to parse targets from filename """
        import os
        import inspect
        this_file = os.path.abspath(inspect.getsourcefile(self.getFile))
        this_dir = os.path.dirname(this_file)
        return os.path.join(this_dir, 'files', filename)


if __name__ == '__main__':
    unittest.main()
