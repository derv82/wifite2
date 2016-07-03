#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Color import Color
from CrackResult import CrackResult

class CrackResultWPA(CrackResult):
    def __init__(self, bssid, essid, handshake_file, key):
        self.result_type = 'WPA'
        self.bssid = bssid
        self.essid = essid
        self.handshake_file = handshake_file
        self.key = key
        super(CrackResultWPA, self).__init__()

    def dump(self):
        if self.essid:
            Color.pl('{+} %s: {C}%s{W}' %
                ('Access Point Name'.rjust(19), self.essid))
        if self.bssid:
            Color.pl('{+} %s: {C}%s{W}' %
                ('Access Point BSSID'.rjust(19), self.bssid))
        Color.pl('{+} %s: {C}%s{W}' %
            ('Encryption'.rjust(19), self.result_type))
        if self.handshake_file:
            Color.pl('{+} %s: {C}%s{W}' %
                ('Handshake File'.rjust(19), self.handshake_file))
        if self.key:
            Color.pl('{+} %s: {G}%s{W}' % ('PSK (password)'.rjust(19), self.key))
        else:
            Color.pl('{!} %s  {O}key unknown{W}' % ''.rjust(19))
    
    def to_dict(self):
        return {
            'type'  : self.result_type,
            'date'  : self.date,
            'essid' : self.essid,
            'bssid' : self.bssid,
            'key'   : self.key,
            'handshake_file' : self.handshake_file
        }

if __name__ == '__main__':
    w = CrackResultWPA('AA:BB:CC:DD:EE:FF', 'Test Router', 'hs/capfile.cap', 'abcd1234')
    w.dump()

    w = CrackResultWPA('AA:BB:CC:DD:EE:FF', 'Test Router', 'hs/capfile.cap', 'Key')
    print '\n'
    w.dump()
    w.save()
    print w.__dict__['bssid']

