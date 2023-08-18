#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.color import Color
from .result import CrackResult


class CrackResultWPA(CrackResult):
    def __init__(self, bssid, essid, handshake_file, key):
        self.result_type = 'WPA'
        self.bssid = bssid
        self.essid = essid
        self.handshake_file = handshake_file
        self.key = key
        super().__init__()

    def dump(self):
        if self.essid:
            Color.pl(f'{{+}} {"Access Point Name".rjust(19)}: {{C}}{self.essid}{{W}}')
        if self.bssid:
            Color.pl(f'{{+}} {"Access Point BSSID".rjust(19)}: {{C}}{self.bssid}{{W}}')
        Color.pl(f'{{+}} {"Encryption".rjust(19)}: {{C}}{self.result_type}{{W}}')
        if self.handshake_file:
            Color.pl(f'{{+}} {"Handshake File".rjust(19)}: {{C}}{self.handshake_file}{{W}}')
        if self.key:
            Color.pl(f'{{+}} {"PSK (password)".rjust(19)}: {{G}}{self.key}{{W}}')
        else:
            Color.pl(f'{{!}} {"".rjust(19)}  {{O}}key unknown{{W}}')

    def print_single_line(self, longest_essid):
        self.print_single_line_prefix(longest_essid)
        Color.p(f'{{G}}{"WPA".ljust(5)}{{W}}')
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
            'handshake_file': self.handshake_file
        }


if __name__ == '__main__':
    w = CrackResultWPA('AA:BB:CC:DD:EE:FF', 'Test Router', 'hs/capfile.cap', 'abcd1234')
    w.dump()

    w = CrackResultWPA('AA:BB:CC:DD:EE:FF', 'Test Router', 'hs/capfile.cap', 'Key')
    print('\n')
    w.dump()
    w.save()
    print((w.__dict__['bssid']))
