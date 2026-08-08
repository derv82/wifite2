#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.process import Process
from ..util.color import Color
from ..tools.tshark import Tshark
from ..tools.pyrit import Pyrit

import re
import os
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Handshake(object):
    '''Enhanced handshake detection with parallel verification methods'''

    # Parallel processing thread pool
    executor = ThreadPoolExecutor(max_workers=3)
    
    # Cache for handshake verification
    verification_cache = {}

    def __init__(self, capfile, bssid=None, essid=None, verify_immediately=False):
        self.capfile = capfile
        self.bssid = bssid
        self.essid = essid
        self.verified = False
        self.verification_time = None
        self.verification_method = None
        
        if verify_immediately:
            self.verify_handshake_async()

    def divine_bssid_and_essid(self, timeout=10):
        '''
        Tries to find BSSID and ESSID from cap file.
        Enhanced with timeout and parallel processing.
        '''
        start_time = time.time()
        
        try:
            # Try to extract BSSID from filename
            if self.bssid is None:
                hs_regex = re.compile(
                    r'^.*handshake_\w+_([0-9A-F\-]{17})_.*\.cap$', 
                    re.IGNORECASE
                )
                match = hs_regex.match(self.capfile)
                if match:
                    self.bssid = match.group(1).replace('-', ':')
                    logger.info(f"[+] Extracted BSSID from filename: {self.bssid}")

            # Get list of bssid/essid pairs from cap file (with timeout)
            pairs = self._safe_call(
                Tshark.bssid_essid_pairs, 
                args=(self.capfile,),
                kwargs={'bssid': self.bssid},
                timeout=timeout
            )

            if len(pairs) == 0:
                pairs = self._safe_call(
                    self.pyrit_handshakes,
                    timeout=timeout
                )

            if len(pairs) == 0 and not self.bssid and not self.essid:
                raise ValueError(
                    f'Cannot find BSSID or ESSID in cap file {self.capfile}'
                )

            # Auto-select BSSID/ESSID
            if not self.essid and not self.bssid and len(pairs) > 0:
                self.bssid = pairs[0][0]
                self.essid = pairs[0][1]
                logger.warning(
                    f"[!] Auto-selected BSSID: {self.bssid}, ESSID: {self.essid}"
                )

            elif not self.bssid and len(pairs) > 0:
                for (bssid, essid) in pairs:
                    if self.essid and self.essid == essid:
                        self.bssid = bssid
                        logger.info(f"[+] Discovered BSSID: {bssid}")
                        break

            elif not self.essid and len(pairs) > 0:
                for (bssid, essid) in pairs:
                    if self.bssid and self.bssid.lower() == bssid.lower():
                        self.essid = essid
                        logger.info(f"[+] Discovered ESSID: {essid}")
                        break

        except Exception as e:
            logger.error(f"[!] Error divining BSSID/ESSID: {str(e)}")
            raise

    def has_handshake_fast(self, timeout=15):
        '''
        Fast handshake verification using multiple methods in parallel.
        Returns True if valid handshake found.
        '''
        if not self.bssid or not self.essid:
            try:
                self.divine_bssid_and_essid(timeout=timeout)
            except Exception as e:
                logger.error(f"[!] Failed to divine BSSID/ESSID: {str(e)}")
                return False

        start_time = time.time()
        futures = []

        # Submit all verification methods in parallel
        if Tshark.exists():
            futures.append(
                self.executor.submit(
                    self._verify_method,
                    self.tshark_handshakes,
                    'Tshark'
                )
            )

        if Pyrit.exists():
            futures.append(
                self.executor.submit(
                    self._verify_method,
                    self.pyrit_handshakes,
                    'Pyrit'
                )
            )

        if Process.exists('cowpatty'):
            futures.append(
                self.executor.submit(
                    self._verify_method,
                    self.cowpatty_handshakes,
                    'Cowpatty'
                )
            )

        # Return True on first successful verification
        for future in as_completed(futures, timeout=timeout):
            try:
                method, result = future.result()
                if result and len(result) > 0:
                    elapsed = time.time() - start_time
                    self.verified = True
                    self.verification_method = method
                    self.verification_time = elapsed
                    logger.info(
                        f"[+] Handshake verified by {method} in {elapsed:.2f}s"
                    )
                    return True
            except Exception as e:
                logger.debug(f"Verification method failed: {str(e)}")
                continue

        logger.warning("[!] No valid handshake detected")
        return False

    def has_handshake(self):
        '''Original method for backward compatibility'''
        if not self.bssid or not self.essid:
            self.divine_bssid_and_essid()

        if len(self.tshark_handshakes()) > 0:
            return True
        if len(self.pyrit_handshakes()) > 0:
            return True

        return False

    def _verify_method(self, method_func, method_name):
        '''Safely call verification method and return results'''
        try:
            results = method_func()
            return (method_name, results)
        except Exception as e:
            logger.debug(f"[!] {method_name} verification failed: {str(e)}")
            return (method_name, [])

    def _safe_call(self, func, args=(), kwargs=None, timeout=10):
        '''Safely call function with timeout'''
        if kwargs is None:
            kwargs = {}
        
        future = self.executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except Exception as e:
            logger.warning(f"[!] Call to {func.__name__} timed out or failed: {str(e)}")
            return []

    def tshark_handshakes(self):
        '''Returns list[tuple] of BSSID & ESSID pairs from Tshark analysis.'''
        try:
            tshark_bssids = Tshark.bssids_with_handshakes(
                self.capfile, 
                bssid=self.bssid
            )
            return [(bssid, None) for bssid in tshark_bssids]
        except Exception as e:
            logger.debug(f"Tshark error: {str(e)}")
            return []

    def pyrit_handshakes(self):
        '''Returns list[tuple] of BSSID & ESSID pairs from Pyrit analysis.'''
        try:
            return Pyrit.bssid_essid_with_handshakes(
                self.capfile, 
                bssid=self.bssid, 
                essid=self.essid
            )
        except Exception as e:
            logger.debug(f"Pyrit error: {str(e)}")
            return []

    def cowpatty_handshakes(self):
        '''Returns list[tuple] of BSSID & ESSID pairs from Cowpatty analysis.'''
        if not Process.exists('cowpatty'):
            return []
        if not self.essid:
            return []

        try:
            command = [
                'cowpatty',
                '-r', self.capfile,
                '-s', self.essid,
                '-c'  # Check for handshake
            ]

            proc = Process(command, devnull=False)
            for line in proc.stdout().split('\n'):
                if 'Collected all necessary data to mount crack against WPA' in line:
                    return [(None, self.essid)]
        except Exception as e:
            logger.debug(f"Cowpatty error: {str(e)}")
        
        return []

    def aircrack_handshakes(self):
        '''Returns tuple (BSSID,None) if aircrack detects a valid handshake'''
        if not self.bssid:
            return []

        try:
            command = f'echo "" | aircrack-ng -a 2 -w - -b {self.bssid} "{self.capfile}"'
            (stdout, stderr) = Process.call(command)

            if 'passphrase not in dictionary' in stdout.lower():
                return [(self.bssid, None)]
        except Exception as e:
            logger.debug(f"Aircrack error: {str(e)}")
        
        return []

    def analyze(self):
        '''Prints analysis of handshake capfile'''
        self.divine_bssid_and_essid()

        if Tshark.exists():
            Handshake.print_pairs(
                self.tshark_handshakes(), 
                self.capfile, 
                'tshark'
            )

        if Pyrit.exists():
            Handshake.print_pairs(
                self.pyrit_handshakes(), 
                self.capfile, 
                'pyrit'
            )

        if Process.exists('cowpatty'):
            Handshake.print_pairs(
                self.cowpatty_handshakes(), 
                self.capfile, 
                'cowpatty'
            )

        Handshake.print_pairs(
            self.aircrack_handshakes(), 
            self.capfile, 
            'aircrack'
        )

    def strip(self, outfile=None):
        '''
        Strips unnecessary packets from handshake.
        Optimized for faster processing.
        '''
        if not outfile:
            outfile = self.capfile + '.temp'
            replace_existing_file = True
        else:
            replace_existing_file = False

        cmd = [
            'tshark',
            '-r', self.capfile,
            '-Y', 'wlan.fc.type_subtype == 0x08 || wlan.fc.type_subtype == 0x05 || eapol',
            '-w', outfile
        ]
        
        try:
            proc = Process(cmd)
            proc.wait()
            
            if replace_existing_file:
                from shutil import copy
                copy(outfile, self.capfile)
                os.remove(outfile)
                logger.info(f"[+] Handshake stripped and optimized")
        except Exception as e:
            logger.error(f"[!] Error stripping handshake: {str(e)}")

    def verify_handshake_async(self):
        '''Async handshake verification'''
        self.executor.submit(self.has_handshake_fast)

    @staticmethod
    def print_pairs(pairs, capfile, tool=None):
        '''Prints out BSSID and/or ESSID given a list of tuples'''
        tool_str = ''
        if tool is not None:
            tool_str = '{C}%s{W}: ' % tool.rjust(8)

        if len(pairs) == 0:
            Color.pl('{!} %s.cap file {R}does not{O} contain a valid handshake{W}' % tool_str)
            return

        for (bssid, essid) in pairs:
            out_str = '{+} %s.cap file {G}contains a valid handshake{W} for' % tool_str
            if bssid and essid:
                Color.pl('%s {G}%s{W} ({G}%s{W})' % (out_str, bssid, essid))
            elif bssid:
                Color.pl('%s {G}%s{W}' % (out_str, bssid))
            elif essid:
                Color.pl('%s ({G}%s{W})' % (out_str, essid))


import time  # Add this import at the top

if __name__ == '__main__':
    print('Testing enhanced Handshake detection...')
    hs = Handshake('./tests/files/handshake_has_1234.cap', 
                   bssid='18:d6:c7:6d:6b:18', 
                   essid='YZWifi')
    hs.analyze()
    print('has_handshake_fast() =', hs.has_handshake_fast(timeout=15))
