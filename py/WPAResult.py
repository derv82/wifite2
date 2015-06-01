#!/usr/bin/python

from Color import Color

class WPAResult(object):
    def __init__(self, bssid, essid, handshake_file, key):
        self.bssid = bssid
        self.essid = essid
        self.handshake_file = handshake_file
        self.key = key

    def dump(self):
        if self.essid:
            Color.pl('{+} %s: {C}%s{W}' %
                ('Access Point Name'.rjust(19), self.essid))
        if self.bssid:
            Color.pl('{+} %s: {C}%s{W}' %
                ('Access Point BSSID'.rjust(19), self.bssid))
        if self.handshake_file:
            Color.pl('{+} %s: {C}%s{W}' %
                ('Handshake File'.rjust(19), self.handshake_file))
        if self.key:
            Color.pl('{+} %s: {G}%s{W}' % ('PSK (password)'.rjust(19), self.key))
        else:
            Color.pl('{!} %s  {O}key unknown{W}' % ''.rjust(19))

if __name__ == '__main__':
    w = WPAResult('AA:BB:CC:DD:EE:FF', 'Test Router', 'hs/capfile.cap', 'abcd1234')
    w.dump()
    print '\n'
    w = WPAResult('AA:BB:CC:DD:EE:FF', 'Test Router', 'hs/capfile.cap', None)
    w.dump()
