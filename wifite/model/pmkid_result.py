#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.color import Color
from .result import CrackResult


class CrackResultPMKID(CrackResult):
    def __init__(self, bssid, essid, pmkid_file, key):
        self.result_type = 'PMKID'
        self.bssid = bssid
        self.essid = essid
        self.pmkid_file = pmkid_file
        self.key = key
        super().__init__()

    def dump(self):
        if self.essid:
            Color.pl(f'{{+}} {"Access Point Name".rjust(19)}: {{C}}{self.essid}{{W}}')
        if self.bssid:
            Color.pl(f'{{+}} {"Access Point BSSID".rjust(19)}: {{C}}{self.bssid}{{W}}')
        Color.pl(f'{{+}} {"Encryption".rjust(19)}: {{C}}{self.result_type}{{W}}')
        if self.pmkid_file:
            Color.pl(f'{{+}} {"PMKID File".rjust(19)}: {{C}}{self.pmkid_file}{{W}}')
        if self.key:
            Color.pl(f'{{+}} {"PSK (password)".rjust(19)}: {{G}}{self.key}{{W}}')
        else:
            Color.pl(f'{{!}} {"".rjust(19)}  {{O}}key unknown{{W}}')

    def print_single_line(self, longest_essid):
        self.print_single_line_prefix(longest_essid)
        Color.p(f'{{G}}{"PMKID".ljust(5)}{{W}}')
        Color.p('  ')
        Color.p(f'Key: {{G}}{self.key}{{W}}')
        Color.pl('')

    def to_dict(self):
        return {
            'type': self.result_type,
            'date': self.date,
            'essid': self.essid,
            'bssid': self.bssid,
            'key': self.key,
            'pmkid_file': self.pmkid_file
        }


if __name__ == '__main__':
    w = CrackResultPMKID('AA:BB:CC:DD:EE:FF', 'Test Router', 'hs/pmkid_blah-123213.22000', 'abcd1234')
    w.dump()

    w = CrackResultPMKID('AA:BB:CC:DD:EE:FF', 'Test Router', 'hs/pmkid_blah-123213.22000', 'Key')
    print('\n')
    w.dump()
    w.save()
    print((w.__dict__['bssid']))
