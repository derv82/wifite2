#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Process import Process
from Configuration import Configuration

import os

class Aircrack(object):
    def __init__(self, ivs_file=None):

        self.cracked_file = Configuration.temp() + 'wepkey.txt'

        # Delete previous cracked files
        if os.path.exists(self.cracked_file):
            os.remove(self.cracked_file)

        command = [
            'aircrack-ng',
            '-a', '1',
            '-l', self.cracked_file,
            ivs_file
        ]

        self.pid = Process(command, devnull=True)


    def is_running(self):
        return self.pid.poll() == None

    def is_cracked(self):
        return os.path.exists(self.cracked_file)

    def stop(self):
        ''' Stops aircrack process '''
        if self.pid.poll() == None:
            self.pid.interrupt()

    def get_key_hex_ascii(self):
        if not self.is_cracked():
            raise Exception('Cracked file not found')
        f = open(self.cracked_file, 'r')
        hex_raw = f.read()
        f.close()

        hex_key = ''
        ascii_key = ''
        while len(hex_raw) > 0:
            # HEX
            if hex_key != '':
                hex_key += ':'
            hex_key += hex_raw[0:2]

            # ASCII
            # Convert hex to decimal
            code = int(hex_raw[0:2], 16)
            if code < 32 or code > 127:
                # Hex key is non-printable in ascii
                ascii_key = None
                continue
            elif ascii_key == None:
                # We can't generate an Ascii key
                continue
            # Convert decimal to char
            ascii_key += chr(code)

            # Trim first two characters
            hex_raw = hex_raw[2:]
            continue

        return (hex_key, ascii_key)

if __name__ == '__main__':
    from time import sleep
    Configuration.initialize(False)
    a = Aircrack('tests/files/wep-crackable.ivs')
    while a.is_running():
        sleep(1)
    if a.is_cracked():
        print "cracked!"
        print '(hex, ascii) =', a.get_key_hex_ascii()
    else:
        print "Not cracked"
    Configuration.exit_gracefully(0)
