#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.color import Color
from ..model.result import CrackResult
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from os import devnull


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
        super(CrackResultWPS, self).__init__()

    def dump(self):
        if self.essid is not None:
            Color.pl(f'{{+}} {"ESSID".rjust(12)}: {{C}}{self.essid}{{W}}')
        psk = '{O}N/A{W}' if self.psk is None else '{G}%s{W}' % self.psk
        Color.pl('{+} %s: {C}%s{W}' % ('BSSID'.rjust(12), self.bssid))
        Color.pl('{+} %s: {C}WPA{W} ({C}WPS{W})' % 'Encryption'.rjust(12))
        Color.pl('{+} %s: {G}%s{W}' % ('WPS PIN'.rjust(12), self.pin))
        Color.pl('{+} %s: {G}%s{W}' % ('PSK/Password'.rjust(12), psk))

    def print_single_line(self, longest_essid):
        self.print_single_line_prefix(longest_essid)
        Color.p('{G}%s{W}' % 'WPS'.ljust(5))
        Color.p('  ')
        if self.psk:
            Color.p('Key: {G}%s{W} ' % self.psk)
        Color.p('PIN: {G}%s{W}' % self.pin)
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
