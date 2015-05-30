#!/usr/bin/python

from Attack import Attack
from Airodump import Airodump
from Aireplay import Aireplay, WEPAttackType
from Configuration import Configuration
from Color import Color

import time

class AttackWEP(Attack):
    '''
        Contains logic for attacking a WEP-encrypted access point.
    '''

    fakeauth_wait = 5

    def __init__(self, target):
        super(AttackWEP, self).__init__(target)

    def run(self):
        '''
            Initiates full WEP attack.
            Including airodump-ng starting, cracking, etc.
        '''
        # First, start Airodump process
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      output_file_prefix='wep') as airodump:

            airodump_target = self.wait_for_target(airodump)

            for attack_num in xrange(1, 6):
                pass
                #aireplay = Aireplay(self.target, attack_num)
                ''' 
                    TODO (pending until I get a router to test on)
                    * Wait for IVS to start flowing, e.g. sleep(1).
                    * if IVS > threshold, start cracking.
                    * Check aireplay.is_running() to see if it completed/failed.
                    * Continue attacks depending on aireplay status.
                '''


    def fake_auth(self):
        '''
            Attempts to fake-authenticate with target.
            Returns: True if successful,
                     False is unsuccesful.
        '''
        start_time = time.time()
        aireplay = Aireplay(self.target, 'fakeauth')
        process_failed = False
        while aireplay.is_running():
            if int(time.time() - start_time) > AttackWEP.fakeauth_wait:
                aireplay.stop()
                process_failed = True
                break
            time.sleep(1)

        # Check if fake-auth was successful
        if process_failed:
            fakeauth = False
        else:
            output = aireplay.get_output()
            fakeauth = 'association successful' in output.lower()

        if fakeauth:
            Color.pl('{+} {G}fake-authentication successful{W}')
        else:
            if Configuration.require_fakeauth:
                # Fakeauth is requried, fail
                raise Exception(
                    'Fake-authenticate did not complete within' +
                    ' %d seconds' % AttackWEP.fakeauth_wait)
            else:
                # Warn that fakeauth failed
                Color.pl('{!} {O}' +
                    'unable to fake-authenticate with target' +
                    ' (%s){W}' % self.target.bssid)
                Color.pl('{!} continuing attacks because' +
                    ' {G}--require-fakeauth{W} was not set')
        return fakeauth



if __name__ == '__main__':
    from Target import Target
    fields = "30:85:A9:39:D2:18, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  6,  54, WPA2, CCMP TKIP,PSK, -58,        2,        0,   0.  0.  0.  0,   9, Uncle Router's Gigabit LAN Party, ".split(',')
    target = Target(fields)
    wep = AttackWEP(target)
    wep.fake_auth()


