#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
from enum import Enum
from .pmkid import AttackPMKID
from .wep import AttackWEP
from .wpa import AttackWPA
from .wpa3 import AttackWPA3SAE
from .wps import AttackWPS
from .owe import AttackOWE
from ..config import Configuration
from ..model.target import WPSState
from ..util.color import Color
from ..util.logger import log_info
from ..util.wpa3_tools import WPA3ToolChecker
from ..util.memory import MemoryMonitor, get_infinite_monitor

class Answer(Enum):
    Skip = 1
    ExitOrReturn = 2
    Continue = 3
    Ignore = 4

class AttackAll:
    @classmethod
    def attack_multiple(cls, targets, session=None, session_mgr=None):
        """
        Attacks all given `targets` (list[wifite.model.target]) until user interruption.
        Returns: Number of targets that were attacked (int)
        """
        # Safety check: ensure targets is not None
        if targets is None:
            Color.pl('{!} {R}Error: No targets provided for attack{W}')
            return 0

        if any(t.wps for t in targets) and not AttackWPS.can_attack_wps():
            # Warn that WPS attacks are not available.
            Color.pl('{!} {O}Note: WPS attacks are not possible because you do not have {C}reaver{O} nor {C}bully{W}')

        # Initialize infinite mode monitor if in infinite mode
        infinite_monitor = None
        if Configuration.infinite_mode:
            infinite_monitor = get_infinite_monitor()
            infinite_monitor.on_cycle_start()

        attacked_targets = 0
        targets_remaining = len(targets)
        for index, target in enumerate(targets, start=1):
            if Configuration.attack_max != 0 and index > Configuration.attack_max:
                print(("Attacked %d targets, stopping because of the --first flag" % Configuration.attack_max))
                break
            attacked_targets += 1
            targets_remaining -= 1

            # Periodic cleanup to prevent file descriptor leaks and memory bloat
            if index % 5 == 0:  # Every 5 targets
                from ..util.process import Process
                Process.check_fd_limit()

                # Memory monitoring - especially important for infinite mode
                MemoryMonitor.periodic_check(index)

            # Infinite mode specific cleanup
            if infinite_monitor and index % 10 == 0:
                infinite_monitor.on_target_complete()

            bssid = target.bssid
            essid = target.essid if target.essid_known else '{O}ESSID unknown{W}'

            Color.pl('\n{+} ({G}%d{W}/{G}%d{W})'
                     % (index, len(targets)) + ' Starting attacks against {C}%s{W} ({C}%s{W})' % (bssid, essid))

            should_continue = cls.attack_single(target, targets_remaining, session, session_mgr)
            if not should_continue:
                break

        return attacked_targets

    @classmethod
    def attack_single(cls, target, targets_remaining, session=None, session_mgr=None):
        """
        Attacks a single `target` (wifite.model.target).
        Returns: True if attacks should continue, False otherwise.
        """
        global attack
        log_info('AttackAll', 'Targeting %s (%s) enc=%s auth=%s wps=%s pwr=%s (%d remaining)' % (
            target.essid or '(hidden)', target.bssid, target.encryption,
            target.authentication, target.wps, target.power, targets_remaining))
        if 'MGT' in target.authentication:
            Color.pl("\n{!}{O}Skipping. Target is using {C}WPA-Enterprise {O}and can not be cracked.")
            # Mark as failed in session
            if session and session_mgr:
                session_mgr.mark_target_failed(session, target.bssid, "WPA-Enterprise not supported")
                session_mgr.save_session(session)
                Color.pl('{+} {D}Session updated: target {C}%s{D} marked as {R}failed{W}' % target.bssid)
            return True

        # --wpa3-only: restrict attacks to WPA3-SAE networks. Unlike --wpa3
        # (a discovery filter), this is enforced at attack time, so a non-WPA3
        # target that still reaches this point (e.g. selected by BSSID, or when
        # no discovery filter was set) is skipped — WPA2-only / WEP / OWE
        # targets are never attacked under this mode.
        if Configuration.wpa3_only:
            is_wpa3_target = target.primary_encryption == 'WPA3' or (
                hasattr(target, 'wpa3_info') and target.wpa3_info and
                getattr(target.wpa3_info, 'has_wpa3', False))
            if not is_wpa3_target:
                Color.pl('{!} {O}Skipping {C}%s{O}: {C}--wpa3-only{O} is set and '
                         'target is not WPA3-SAE{W}' % (target.essid or target.bssid))
                if session and session_mgr:
                    session_mgr.mark_target_failed(session, target.bssid, "Not WPA3 (--wpa3-only)")
                    session_mgr.save_session(session)
                return True

        attacks = []

        if Configuration.use_eviltwin:
            # Evil Twin attack - works on WPA/WPA2/WPA3 networks
            from .eviltwin import EvilTwin
            if target.primary_encryption.startswith('WPA'):
                attacks.append(EvilTwin(target))
            else:
                Color.pl('{!} {O}Evil Twin attack only works on WPA/WPA2/WPA3 networks{W}')
                # Mark as failed in session
                if session and session_mgr:
                    session_mgr.mark_target_failed(session, target.bssid, "Evil Twin requires WPA/WPA2/WPA3")
                    session_mgr.save_session(session)
                return True

        elif target.primary_encryption == 'OWE':
            attacks.append(AttackOWE(target))

        elif target.primary_encryption == 'WEP':
            attacks.append(AttackWEP(target))

        elif target.primary_encryption.startswith('WPA'): # Covers WPA, WPA2, WPA3
            # WPA can have multiple attack vectors:

            # Check if this is a WPA3 target
            is_wpa3 = target.primary_encryption == 'WPA3' or \
                     (hasattr(target, 'wpa3_info') and target.wpa3_info and
                      (hasattr(target.wpa3_info, 'has_wpa3') and target.wpa3_info.has_wpa3))

            # For WPA3 targets, use specialized WPA3 attack if tools are available
            if is_wpa3 and WPA3ToolChecker.can_attack_wpa3():
                # Use WPA3-specific attack module
                attacks.append(AttackWPA3SAE(target))

                # For transition mode, also try standard WPA2 attacks as fallback
                # (unless --force-sae asked us to skip WPA2 and attack SAE directly).
                if not Configuration.wpa3_force_sae and \
                        hasattr(target, 'wpa3_info') and target.wpa3_info and \
                        target.wpa3_info.get('is_transition'):
                    if not Configuration.wps_only and not Configuration.use_pmkid_only:
                        # Add PMKID and WPA attacks as fallback for transition mode
                        if not Configuration.dont_use_pmkid:
                            attacks.append(AttackPMKID(target))
                        attacks.append(AttackWPA(target))

            # WPS attacks (not applicable to pure WPA3)
            elif not is_wpa3 and \
               not Configuration.use_pmkid_only and \
               target.wps is WPSState.UNLOCKED and \
               AttackWPS.can_attack_wps():

                # Pixie-Dust
                if Configuration.wps_pixie:
                    attacks.append(AttackWPS(target, pixie_dust=True))

                # Null PIN zero-day attack
                if Configuration.wps_pin: # This implies not wps_pixie_only
                    attacks.append(AttackWPS(target, pixie_dust=False, null_pin=True))

                # PIN attack
                if Configuration.wps_pin: # This implies not wps_pixie_only
                    attacks.append(AttackWPS(target, pixie_dust=False))

            # PMKID and Handshake attacks for WPA/WPA2 (or WPA3 if tools not available)
            if not is_wpa3 or not WPA3ToolChecker.can_attack_wpa3():
                if not Configuration.wps_only: # If --wps-only is not set
                    # PMKID
                    if not Configuration.dont_use_pmkid: # If --no-pmkid is not set
                        attacks.append(AttackPMKID(target))

                    # Handshake capture
                    if not Configuration.use_pmkid_only: # If --pmkid (means pmkid-only) is not set
                        attacks.append(AttackWPA(target))
                elif is_wpa3 and Configuration.wps_only:
                    # Special case: If it's WPA3 and --wps-only is specified,
                    # WPS attacks are skipped. We should still allow PMKID/Handshake for WPA3.
                    Color.pl('{!} {O}Note: --wps-only is active, but target is WPA3. WPS attacks are not applicable.')
                    Color.pl('{+} {C}Proceeding with PMKID and Handshake attacks for WPA3 target.{W}')
                    if not Configuration.dont_use_pmkid:
                        attacks.append(AttackPMKID(target))
                    if not Configuration.use_pmkid_only:
                        attacks.append(AttackWPA(target))


        if not attacks:
            Color.pl('{!} {R}Error: {O}Unable to attack: no attacks available')
            # Mark as failed in session
            if session and session_mgr:
                session_mgr.mark_target_failed(session, target.bssid, "No attacks available")
                session_mgr.save_session(session)
                Color.pl('{+} {D}Session updated: target {C}%s{D} marked as {R}failed{W}' % target.bssid)
            return True  # Keep attacking other targets (skip)

        attack_successful = False
        while attacks:
            # Needed by infinite attack mode in order to count how many targets were attacked
            target.attacked = True
            attack = attacks.pop(0)
            try:
                result = attack.run()
                if result:
                    attack_successful = True
                    break  # Attack was successful, stop other attacks.
            except (OSError, IOError) as e:
                # File system or process errors
                Color.pl('\r {!} {R}System Error{W}: %s' % str(e))
                continue
            except subprocess.CalledProcessError as e:
                # Command execution failures
                Color.pl('\r {!} {R}Command Failed{W}: %s' % str(e))
                continue
            except ValueError as e:
                # Invalid data or configuration
                Color.pl('\r {!} {R}Configuration Error{W}: %s' % str(e))
                continue
            except PermissionError as e:
                # Permission issues
                Color.pl('\r {!} {R}Permission Error{W}: %s' % str(e))
                continue
            except Exception as e:
                # Unexpected errors - still catch but log more info
                Color.pl('\r {!} {R}Unexpected Error{W}: %s' % str(e))
                if Configuration.verbose > 0:
                    Color.pexception(e)
                # Force cleanup on unexpected errors to prevent resource leaks
                from ..util.process import ProcessManager, Process
                ProcessManager().cleanup_all()
                Process.cleanup_zombies()
                continue
            except KeyboardInterrupt:
                Color.pl('\n{!} {O}Interrupted{W}\n')
                answer = cls.user_wants_to_continue(targets_remaining, len(attacks))
                if answer == Answer.Continue:
                    continue  # Keep attacking the same target (continue)
                elif answer == Answer.Skip:
                    # Mark as failed in session
                    if session and session_mgr:
                        session_mgr.mark_target_failed(session, target.bssid, "Skipped by user")
                        session_mgr.save_session(session)
                        Color.pl('{+} {D}Session updated: target {C}%s{D} marked as {R}failed{W}' % target.bssid)
                    return True  # Keep attacking other targets (skip)
                elif answer == Answer.Ignore:
                    from ..model.result import CrackResult
                    CrackResult.ignore_target(target)
                    # Mark as failed in session
                    if session and session_mgr:
                        session_mgr.mark_target_failed(session, target.bssid, "Ignored by user")
                        session_mgr.save_session(session)
                        Color.pl('{+} {D}Session updated: target {C}%s{D} marked as {R}failed{W}' % target.bssid)
                    return True  # Ignore current target and keep attacking other targets (ignore)
                else:
                    return False  # Stop all attacks (exit)

        # Update session after target completion
        if session and session_mgr:
            if attack_successful:
                # Attack was successful, mark as complete
                crack_result = attack.crack_result if hasattr(attack, 'crack_result') else None
                session_mgr.mark_target_complete(session, target.bssid, crack_result)
                session_mgr.save_session(session)
                Color.pl('{+} {D}Session updated: target {C}%s{D} marked as {G}completed{W}' % target.bssid)
            else:
                # All attacks failed, mark as failed
                session_mgr.mark_target_failed(session, target.bssid, "All attacks failed")
                session_mgr.save_session(session)
                Color.pl('{+} {D}Session updated: target {C}%s{D} marked as {R}failed{W}' % target.bssid)

        if attack_successful and attack.success:
            attack.crack_result.save()

        return True  # Keep attacking other targets

    @classmethod
    def user_wants_to_continue(cls, targets_remaining, attacks_remaining=0):
        """
        Asks user if attacks should continue onto other targets
        Returns:
            Answer.Skip if the user wants to skip the current target
            Answer.Ignore if the user wants to ignore the current target
            Answer.Continue if the user wants to continue to the next attack on the current target
            Answer.ExitOrReturn if the user wants to stop the remaining attacks
        """
        if attacks_remaining == 0 and targets_remaining == 0:
            return Answer.ExitOrReturn  # No targets or attacks left, drop out

        prompt_list = []
        if attacks_remaining > 0:
            prompt_list.append(Color.s('{C}%d{W} attack(s)' % attacks_remaining))
        if targets_remaining > 0:
            prompt_list.append(Color.s('{C}%d{W} target(s)' % targets_remaining))
        prompt = ' and '.join(prompt_list) + ' remain'
        Color.pl('{+} %s' % prompt)

        prompt = '{+} Do you want to'
        options = '('

        if attacks_remaining > 0:
            prompt += ' {G}continue{W} attacking,'
            options += '{G}c{W}{D}, {W}'

        if targets_remaining > 0:
            prompt += ' {O}skip{W} to the next target,'
            options += '{O}s{W}{D}, {W}'

        prompt += ' skip and {P}ignore{W} current target,'
        options += '{P}i{W}{D}, {W}'

        if Configuration.infinite_mode:
            options += '{R}r{W})'
            prompt += ' or {R}return{W} to scanning %s? {C}' % options
        else:
            options += '{R}e{W})'
            prompt += ' or {R}exit{W} %s? {C}' % options

        Color.p(prompt)
        try:
            answer = input().lower()
        except KeyboardInterrupt:
            # If user presses Ctrl+C during input, default to exit
            Color.pl('\n{!} {O}Interrupted during input, exiting...{W}')
            return Answer.ExitOrReturn

        if answer.startswith('s'):
            return Answer.Skip
        elif answer.startswith('e') or answer.startswith('r'):
            return Answer.ExitOrReturn  # Exit/Return
        elif answer.startswith('i'):
            return Answer.Ignore  # Ignore
        else:
            return Answer.Continue  # Continue
