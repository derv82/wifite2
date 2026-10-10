#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re

from .dependency import Dependency
from ..config import Configuration
from ..util.process import Process


class Aircrack(Dependency):
    dependency_required = True
    dependency_name = 'aircrack-ng'
    dependency_url = 'https://www.aircrack-ng.org/install.html'
    dependency_packages = {
        'apt': 'aircrack-ng', 'pacman': 'aircrack-ng',
        'dnf': 'aircrack-ng', 'brew': 'aircrack-ng',
    }
    dependency_category = Dependency.CATEGORY_CORE

    def __init__(self, ivs_file2=None):

        self.cracked_file = os.path.abspath(os.path.join(Configuration.temp(), 'wepkey.txt'))

        # Delete previous cracked files
        if os.path.exists(self.cracked_file):
            os.remove(self.cracked_file)

        command = [
            'aircrack-ng',
            '-a', '1',
            '-l', self.cracked_file,
        ]
        if isinstance(ivs_file2, str):
            ivs_file2 = [ivs_file2]

        command.extend(ivs_file2 or [])

        self.pid = Process(command, devnull=True)

    def is_running(self):
        return self.pid.poll() is None

    def is_cracked(self):
        return os.path.exists(self.cracked_file)

    def stop(self):
        """ Stops aircrack process """
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
        for index in range(0, len(hex_raw), 2):
            byt = hex_raw[index:index + 2]
            hex_chars.append(byt)
            byt_int = int(byt, 16)
            if byt_int < 32 or byt_int > 127 or ascii_key is None:
                ascii_key = None  # Not printable
            else:
                ascii_key += chr(byt_int)

        hex_key = ':'.join(hex_chars)

        return hex_key, ascii_key

    def __del__(self):
        if hasattr(self, 'cracked_file') and os.path.exists(self.cracked_file):
            os.remove(self.cracked_file)

    @staticmethod
    def crack_handshake(handshake, show_command=False, wordlist=None):
        from ..util.color import Color
        from ..util.timer import Timer
        '''Tries to crack a handshake. Returns WPA key if found, otherwise None.'''

        wordlist = wordlist or Configuration.wordlist
        key_file = Configuration.temp('wpakey.txt')
        command = [
            'aircrack-ng',
            '-a', '2',
            '-w', wordlist,
            '--bssid', handshake.bssid,
            '-l', key_file,
            handshake.capfile
        ]
        if show_command:
            Color.pl('{+} {D}Running: {W}{P}%s{W}' % ' '.join(command))
        crack_proc = Process(command)

        # Report progress of cracking
        aircrack_nums_re = re.compile(r'(\d+)/(\d+) keys tested.*\(([\d.]+)\s+k/s')
        aircrack_key_re = re.compile(r'Current passphrase:\s*(\S.*\S)\s*$')
        num_tried = num_total = 0
        percent = num_kps = 0.0
        eta_str = 'unknown'
        current_key = ''
        while crack_proc.poll() is None:
            if not crack_proc.pid or not crack_proc.pid.stdout:
                break
            try:
                raw = crack_proc.pid.stdout.readline()
                if not raw:
                    break  # EOF — process closed its stdout
                line = raw.decode('utf-8', errors='replace')
            except (OSError, ValueError):
                break  # Pipe broken or closed
            match_nums = aircrack_nums_re.search(line)
            match_keys = aircrack_key_re.search(line)
            if match_nums:
                num_tried, num_total, num_kps = int(match_nums[1]), int(match_nums[2]), float(match_nums[3])
                if num_kps > 0:
                    eta_seconds = (num_total - num_tried) / num_kps
                    eta_str = Timer.secs_to_str(eta_seconds)
                if num_total > 0:
                    percent = 100.0 * num_tried / num_total
            elif match_keys:
                current_key = match_keys[1]
            else:
                continue

            status = (
                f'\r{{+}} {{C}}Cracking WPA Handshake: {percent:.2f}%{{W}}'
                f' ETA: {{C}}{eta_str}{{W}}'
                f' @ {{C}}{num_kps:.1f}kps{{W}}'
                f' (current key: {{C}}{current_key}{{W}})'
            )
            Color.clear_entire_line()
            Color.p(status)

        Color.pl('')

        if not os.path.exists(key_file):
            return None
        with open(key_file, 'r') as fid:
            key = fid.read().strip()
        os.remove(key_file)

        return key


if __name__ == '__main__':
    (hexkey, asciikey) = Aircrack._hex_and_ascii_key('A1B1C1D1E1')
    if hexkey != 'A1:B1:C1:D1:E1':
        raise ValueError(f'hexkey was "{hexkey}", expected "A1:B1:C1:D1:E1"')
    if asciikey is not None:
        raise ValueError(f'asciikey was "{asciikey}", expected None')

    (hexkey, asciikey) = Aircrack._hex_and_ascii_key('6162636465')
    if hexkey != '61:62:63:64:65':
        raise ValueError(f'hexkey was "{hexkey}", expected "61:62:63:64:65"')
    if asciikey != 'abcde':
        raise ValueError(f'asciikey was "{asciikey}", expected "abcde"')

    from time import sleep

    Configuration.initialize(False)

    ivs_file = 'tests/files/wep-crackable.ivs'
    print(f'Running aircrack on {ivs_file} ...')

    aircrack = Aircrack(ivs_file)
    while aircrack.is_running():
        sleep(1)

    if not aircrack.is_cracked():
        raise ValueError(f'Aircrack should have cracked {ivs_file}')
    print('aircrack process completed.')

    (hexkey, asciikey) = aircrack.get_key_hex_ascii()
    print(f'aircrack found HEX key: ({hexkey}) and ASCII key: ({asciikey})')
    if hexkey != '75:6E:63:6C:65':
        raise ValueError(f'hexkey was "{hexkey}", expected "75:6E:63:6C:65"')
    if asciikey != 'uncle':
        raise ValueError(f'asciikey was "{asciikey}", expected "uncle"')

    Configuration.exit_gracefully()