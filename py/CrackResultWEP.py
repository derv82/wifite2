#!/usr/bin/python

from Color import Color

import time

class CrackResultWEP(object):
    def __init__(self, bssid, essid, hex_key, ascii_key):
        self.bssid     = bssid
        self.essid     = essid
        self.hex_key   = hex_key
        self.ascii_key = ascii_key
        self.time      = time.time()

    def dump(self):
        if self.essid:
            Color.pl('{+}      ESSID: {C}%s{W}' % self.essid)
        Color.pl('{+}      BSSID: {C}%s{W}' % self.bssid)
        Color.pl('{+} Encryption: {C}WEP{W}')
        Color.pl('{+}    Hex Key: {G}%s{W}' % self.hex_key)
        if self.ascii_key:
            Color.pl('{+}  Ascii Key: {G}%s{W}' % self.ascii_key)

if __name__ == '__main__':
    crw = CrackResultWEP('AA:BB:CC:DD:EE:FF', 'Test Router', '00:01:02:03:04', 'abcde')
    crw.dump()

