#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..util.process import Process
from ..util.input import xrange
from ..config import Configuration

import os
import re

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
                ascii_key = None  # Not printable
            else:
                ascii_key += chr(byt_int)

        hex_key = ':'.join(hex_chars)

        return (hex_key, ascii_key)

    def __del__(self):
        if os.path.exists(self.cracked_file):
            os.remove(self.cracked_file)


    @staticmethod
    def crack_handshake(handshake, show_command=False):
        from ..util.color import Color
        from ..util.timer import Timer
        '''Tries to crack a handshake. Returns WPA key if found, otherwise None.'''

        key_file = Configuration.temp('wpakey.txt')
        command = [
            'aircrack-ng',
            '-a', '2',
            '-w', Configuration.wordlist,
            '--bssid', handshake.bssid,
            '-l', key_file,
            handshake.capfile
        ]
        if show_command:
            Color.pl('{+} {D}Running: {W}{P}%s{W}' % ' '.join(command))
        crack_proc = Process(command)

        # Report progress of cracking
        aircrack_nums_re = re.compile(r'(\d+)/(\d+) keys tested.*\(([\d.]+)\s+k/s')
        aircrack_key_re  = re.compile(r'Current passphrase:\s*([^\s].*[^\s])\s*$')
        num_tried = num_total = 0
        percent = num_kps = 0.0
        eta_str = 'unknown'
        current_key = ''
        while crack_proc.poll() is None:
            line = crack_proc.pid.stdout.readline()
            match_nums = aircrack_nums_re.search(line.decode('utf-8'))
            match_keys = aircrack_key_re.search(line.decode('utf-8'))
            if match_nums:
                num_tried = int(match_nums.group(1))
                num_total = int(match_nums.group(2))
                num_kps = float(match_nums.group(3))
                eta_seconds = (num_total - num_tried) / num_kps
                eta_str = Timer.secs_to_str(eta_seconds)
                percent = 100.0 * float(num_tried) / float(num_total)
            elif match_keys:
                current_key = match_keys.group(1)
            else:
                continue

            status = '\r{+} {C}Cracking WPA Handshake: %0.2f%%{W}' % percent
            status += ' ETA: {C}%s{W}' % eta_str
            status += ' @ {C}%0.1fkps{W}' % num_kps
            #status += ' ({C}%d{W}/{C}%d{W} keys)' % (num_tried, num_total)
            status += ' (current key: {C}%s{W})' % current_key
            Color.clear_entire_line()
            Color.p(status)

        Color.pl('')

        # Check crack result
        if os.path.exists(key_file):
            with open(key_file, 'r') as fid:
                key = fid.read().strip()
            os.remove(key_file)

            return key
        else:
            return None


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
    print('Running aircrack on %s ...' % ivs_file)

    aircrack = Aircrack(ivs_file)
    while aircrack.is_running():
        sleep(1)

    assert aircrack.is_cracked(), 'Aircrack should have cracked %s' % ivs_file
    print('aircrack process completed.')

    (hexkey, asciikey) = aircrack.get_key_hex_ascii()
    print('aircrack found HEX key: (%s) and ASCII key: (%s)' % (hexkey, asciikey))
    assert hexkey == '75:6E:63:6C:65', 'hexkey was "%s", expected "75:6E:63:6C:65"' % hexkey
    assert asciikey == 'uncle', 'asciikey was "%s", expected "uncle"' % asciikey

    Configuration.exit_gracefully(0)
