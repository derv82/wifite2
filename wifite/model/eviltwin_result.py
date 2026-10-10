#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.color import Color
from .result import CrackResult


class CrackResultEvilTwin(CrackResult):
    """Result from Evil Twin attack with captive portal."""

    def __init__(self, bssid, essid, key, clients_connected=0, credential_attempts=0, 
                 validation_time=0.0, portal_template='generic'):
        self.result_type = 'Evil Twin'
        self.bssid = bssid
        self.essid = essid
        self.key = key
        self.clients_connected = clients_connected
        self.credential_attempts = credential_attempts
        self.validation_time = validation_time
        self.portal_template = portal_template
        super(CrackResultEvilTwin, self).__init__()

    def dump(self):
        if self.essid:
            Color.pl(f'{{+}} {"Access Point Name".rjust(19)}: {{C}}{self.essid}{{W}}')
        if self.bssid:
            Color.pl(f'{{+}} {"Access Point BSSID".rjust(19)}: {{C}}{self.bssid}{{W}}')
        Color.pl('{+} %s: {C}%s{W}' % ('Attack Type'.rjust(19), self.result_type))
        if self.key:
            Color.pl('{+} %s: {G}%s{W}' % ('PSK (password)'.rjust(19), self.key))
        else:
            Color.pl('{!} %s  {O}key unknown{W}' % ''.rjust(19))
        Color.pl('{+} %s: {C}%d{W}' % ('Clients Connected'.rjust(19), self.clients_connected))
        Color.pl('{+} %s: {C}%d{W}' % ('Credential Attempts'.rjust(19), self.credential_attempts))
        if self.validation_time > 0:
            Color.pl('{+} %s: {C}%.2fs{W}' % ('Validation Time'.rjust(19), self.validation_time))
        Color.pl('{+} %s: {C}%s{W}' % ('Portal Template'.rjust(19), self.portal_template))

    def print_single_line(self, longest_essid):
        self.print_single_line_prefix(longest_essid)
        Color.p('{G}%s{W}' % 'EVIL'.ljust(5))
        Color.p('  ')
        Color.p('Key: {G}%s{W}' % self.key)
        Color.pl('')

    def to_dict(self):
        return {
            'type': self.result_type,
            'date': self.date,
            'essid': self.essid,
            'bssid': self.bssid,
            'key': self.key,
            'clients_connected': self.clients_connected,
            'credential_attempts': self.credential_attempts,
            'validation_time': self.validation_time,
            'portal_template': self.portal_template
        }


if __name__ == '__main__':
    # Test Evil Twin result
    et = CrackResultEvilTwin(
        bssid='AA:BB:CC:DD:EE:FF',
        essid='Test Router',
        key='password123',
        clients_connected=3,
        credential_attempts=5,
        validation_time=2.5,
        portal_template='generic'
    )
    et.dump()
    et.save()
    print(et.__dict__['bssid'])
