#!/usr/bin/python

import time

class CrackResultWEP(object):
    def __init__(self, bssid, essid, hex_key, ascii_key):
        self.bssid     = bssid
        self.essid     = essid
        self.hex_key   = hex_key
        self.ascii_key = ascii_key
        self.time      = time.time()

