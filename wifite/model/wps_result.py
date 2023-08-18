#!/usr/bin/env python
# -*- coding: utf-8 -*-


from os import devnull
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from ..util.color import Color
from ..model.result import CrackResult


@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(devnull, 'w') as fnull:
        with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
            yield err, out


class CrackResultWPS(CrackResult):
    def __init__(self, bssid, essid, pin, psk):
        self.result_type = 'WPS'
        self.bssid = bssid
        self.essid = essid
        self.pin = pin
        self.psk = psk
        super().__init__()

    def dump(self):
        if self.essid is not None:
            Color.pl(f'{{+}} {"ESSID".rjust(12)}: {{C}}{self.essid}{{W}}')
        psk = f'{{G}}{self.psk}{{W}}' if self.psk is not None else '{O}N/A{W}'
        Color.pl(f'{{+}} {"BSSID".rjust(12)}: {{C}}{self.bssid}{{W}}')
        Color.pl(f'{{+}} {"Encryption".rjust(12)}: {{C}}WPA{{W}} ({{C}}WPS{{W}})')
        Color.pl(f'{{+}} {"WPS PIN".rjust(12)}: {{G}}{self.pin}{{W}}')
        Color.pl(f'{{+}} {"PSK/Password".rjust(12)}: {{G}}{psk}{{W}}')

    def print_single_line(self, longest_essid):
        self.print_single_line_prefix(longest_essid)
        Color.p(f'{{G}}{"WPS".ljust(5)}{{W}}')
        Color.p('  ')
        if self.psk:
            Color.p(f'Key: {{G}}{self.psk}{{W}} ')
        Color.p(f'PIN: {{G}}{self.pin}{{W}}')
        Color.pl('')

    def to_dict(self):
        with suppress_stdout_stderr():
            print('@@@ to dict', self.__dict__)
            return {
                'type': self.result_type,
                'date': self.date,
                'essid': self.essid,
                'bssid': self.bssid,
                'pin': self.pin,
                'psk': self.psk
            }


if __name__ == '__main__':
    crw = CrackResultWPS('AA:BB:CC:DD:EE:FF', 'Test Router', '01234567', 'the psk')
    crw.dump()
    crw.save()
