#!/usr/bin/python

class CapFile(object):
    """
        Holds data about an access point's .cap file,
        including filename, AP's ESSID & BSSID.
    """
    def __init__(self, filename, ssid, bssid):
        self.filename = filename
        self.ssid = ssid
        self.bssid = bssid

    def __str__(self):
        return self.filename

if __name__ == '__main__':
    c = CapFile("cap-01.cap", "My Router", "AA:BB:CC:DD:EE:FF")
    print c

