#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..util.process import Process
from ..util.input import xrange
from ..config import Configuration

import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class Aircrack(Dependency):
    dependency_required = True
    dependency_name = 'aircrack-ng'
    dependency_url = 'https://www.aircrack-ng.org/install.html'

    def __init__(self, ivs_file=None):
        self.cracked_file = os.path.abspath(
                os.path.join(
                    Configuration.temp(), 'wepkey.txt'))

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
        self.timeout_seconds = 60  # Enhanced timeout
        self.crack_start_time = None

    def is_running(self):
        return self.pid.poll() is None

    def is_cracked(self):
        return os.path.exists(self.cracked_file) and os.path.getsize(self.cracked_file) > 0

    def stop(self):
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
            if byt_int < 32 or byt_int > 127:
                ascii_key = None
            elif ascii_key is not None:
                ascii_key += chr(byt_int)

        hex_key = ':'.join(hex_chars)
        return (hex_key, ascii_key)

    def __del__(self):
        if os.path.exists(self.cracked_file):
            os.remove(self.cracked_file)

    @staticmethod
    def crack_handshake_advanced(handshake, wordlist=None, show_command=False, timeout=120):
        """
        Advanced handshake cracking with parallel wordlist support and timeout handling.
        Returns WPA key if found, otherwise None.
        """
        from ..util.color import Color
        from ..util.timer import Timer
        import time

        if wordlist is None:
            wordlist = Configuration.wordlist

        key_file = Configuration.temp('wpakey.txt')
        
        command = [
            'aircrack-ng',
            '-a', '2',
            '-w', wordlist,
            '--bssid', handshake.bssid,
            '-l', key_file,
            '-T', '10',  # Increase thread count for faster cracking
            handshake.capfile
        ]

        if show_command:
            Color.pl('{+} {D}Running: {W}{P}%s{W}' % ' '.join(command))

        crack_proc = Process(command)
        start_time = time.time()

        # Regex patterns for parsing output
        aircrack_nums_re = re.compile(r'(\d+)/(\d+) keys tested.*\(([\d.]+)\s+k/s')
        aircrack_key_re = re.compile(r'Current passphrase:\s*([^\s].*[^\s])\s*$')

        num_tried = num_total = 0
        percent = num_kps = 0.0
        eta_str = 'unknown'
        current_key = ''

        while crack_proc.poll() is None:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                Color.pl('{!} {R}Cracking timeout after {C}%d{R} seconds{W}' % timeout)
                crack_proc.pid.interrupt()
                break

            try:
                line = crack_proc.pid.stdout.readline().decode('utf-8', errors='ignore')
            except:
                continue

            match_nums = aircrack_nums_re.search(line)
            match_keys = aircrack_key_re.search(line)

            if match_nums:
                num_tried = int(match_nums.group(1))
                num_total = int(match_nums.group(2))
                num_kps = float(match_nums.group(3))
                
                if num_kps > 0:
                    eta_seconds = (num_total - num_tried) / num_kps
                    eta_str = Timer.secs_to_str(eta_seconds)
                    percent = 100.0 * float(num_tried) / float(num_total)

            elif match_keys:
                current_key = match_keys.group(1)

            if match_nums or match_keys:
                status = '\r{+} {C}Cracking WPA: %0.2f%%{W}' % percent
                status += ' ETA: {C}%s{W}' % eta_str
                status += ' @ {C}%0.1f kps{W}' % num_kps
                status += ' ({C}%s{W}/{C}%s{W})' % (num_tried, num_total)
                if current_key:
                    status += ' Key: {C}%s{W}' % current_key[:20]
                
                Color.clear_entire_line()
                Color.p(status)

        Color.pl('')

        # Check crack result
        if os.path.exists(key_file):
            with open(key_file, 'r') as fid:
                key = fid.read().strip()
            os.remove(key_file)
            return key

        return None

    @staticmethod
    def crack_handshake(handshake, show_command=False):
        """Legacy method wrapper"""
        return Aircrack.crack_handshake_advanced(handshake, show_command=show_command)
