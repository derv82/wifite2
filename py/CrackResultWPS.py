#!/usr/bin/python

from Color import Color

import time

class CrackResultWPS(object):
    def __init__(self, bssid, essid, pin, psk):
        self.bssid = bssid
        self.essid = essid
        self.pin   = pin
        self.psk   = psk
        self.time  = time.time()

    def dump(self):
        if self.essid:
            Color.pl('{+}        ESSID: {C}%s{W}' % self.essid)
        Color.pl('{+}        BSSID: {C}%s{W}' % self.bssid)
        Color.pl('{+}   Encryption: {C}WPA{W} ({C}WPS{W})')
        Color.pl('{+}      WPS PIN: {G}%s{W}' % self.pin)
        Color.pl('{+} PSK/Password: {G}%s{W}' % self.psk)

if __name__ == '__main__':
    crw = CrackResultWPS('AA:BB:CC:DD:EE:FF', 'Test Router', '01234567', 'the psk')
    crw.dump()

