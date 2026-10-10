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


class CrackResultIgnored(CrackResult):
    def __init__(self, bssid, essid):
        self.result_type = 'IGN'
        self.bssid = bssid
        self.essid = essid
        super(CrackResultIgnored, self).__init__()

    def dump(self):
        if self.essid is not None:
            Color.pl(f'{{+}} {"ESSID".rjust(12)}: {{C}}{self.essid}{{W}}')
        Color.pl('{+} %s: {C}%s{W}' % ('BSSID'.rjust(12), self.bssid))

    def print_single_line(self, longest_essid):
        self.print_single_line_prefix(longest_essid)
        Color.p('{G}%s{W}' % 'IGN'.ljust(9))
        Color.pl('')

    def to_dict(self):
        with suppress_stdout_stderr():
            return {
                'type': self.result_type,
                'date': self.date,
                'essid': self.essid,
                'bssid': self.bssid,
            }


if __name__ == '__main__':
    crw = CrackResultIgnored('AA:BB:CC:DD:EE:FF', 'Test Router')
    crw.dump()
    crw.save()
