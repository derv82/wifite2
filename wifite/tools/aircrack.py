#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..util.process import Process
from ..util.input import xrange
from ..config import Configuration

import os

class Aircrack(Dependency):
    dependency_required = True
    dependency_name = 'aircrack-ng'
    dependency_url = 'https://www.aircrack-ng.org/install.html'

    def __init__(self, ivs_file=None):

        self.cracked_file = os.path.abspath(
                os.path.join(
                    Configuration.temp(), 'wepkey.txt'))

        # Delete previous cracked files
        if os.path.exists(self.cracked_file):
            os.remove(self.cracked_file)

        command = [
            'aircrack-ng',
            '-a', '1',
            '-l', self.cracked_file,
        ]
        if type(ivs_file) is str:
            ivs_file = [ivs_file]

        command.extend(ivs_file)

        self.pid = Process(command, devnull=True)


    def is_running(self):
        return self.pid.poll() is None

    def is_cracked(self):
        return os.path.exists(self.cracked_file)

    def stop(self):
        ''' Stops aircrack process '''
        if self.pid.poll() is None:
            self.pid.interrupt()

    def get_key_hex_ascii(self):
        if not self.is_cracked():
            raise Exception('Cracked file not found')

        with open(self.cracked_file, 'r') as fid:
            hex_raw = fid.read()

        return self._hex_and_ascii_key(hex_raw)

    @staticmethod
    def _hex_and_ascii_key(hex_raw):
        hex_chars = []
        ascii_key = ''
        for index in xrange(0, len(hex_raw), 2):
            byt = hex_raw[index:index+2]
            hex_chars.append(byt)
            byt_int = int(byt, 16)
            if byt_int < 32 or byt_int > 127 or ascii_key is None:
                ascii_key = None # Not printable
            else:
                ascii_key += chr(byt_int)

        hex_key = ':'.join(hex_chars)

        return (hex_key, ascii_key)

    def __del__(self):
        if os.path.exists(self.cracked_file):
            os.remove(self.cracked_file)

if __name__ == '__main__':
    (hexkey, asciikey) = Aircrack._hex_and_ascii_key('A1B1C1D1E1')
    assert hexkey == 'A1:B1:C1:D1:E1', 'hexkey was "%s", expected "A1:B1:C1:D1:E1"' % hexkey
    assert asciikey is None, 'asciikey was "%s", expected None' % asciikey

    (hexkey, asciikey) = Aircrack._hex_and_ascii_key('6162636465')
    assert hexkey == '61:62:63:64:65', 'hexkey was "%s", expected "61:62:63:64:65"' % hexkey
    assert asciikey == 'abcde', 'asciikey was "%s", expected "abcde"' % asciikey

    from time import sleep

    Configuration.initialize(False)

    ivs_file = 'tests/files/wep-crackable.ivs'
    print("Running aircrack on %s ..." % ivs_file)

    aircrack = Aircrack(ivs_file)
    while aircrack.is_running():
        sleep(1)

    assert aircrack.is_cracked(), "Aircrack should have cracked %s" % ivs_file
    print("aircrack process completed.")

    (hexkey, asciikey) = aircrack.get_key_hex_ascii()
    print("aircrack found HEX key: (%s) and ASCII key: (%s)" % (hexkey, asciikey))
    assert hexkey == '75:6E:63:6C:65', 'hexkey was "%s", expected "75:6E:63:6C:65"' % hexkey
    assert asciikey == 'uncle', 'asciikey was "%s", expected "uncle"' % asciikey

    Configuration.exit_gracefully(0)
