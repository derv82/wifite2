#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .wep import AttackWEP
from .wpa import AttackWPA
from .wps import AttackWPS
from .pmkid import AttackPMKID
from ..config import Configuration
from ..util.color import Color
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class AttackAll(object):
    """Intelligent attack orchestration with priority management"""
    
    # Attack priority scoring
    ATTACK_PRIORITY = {
        'PMKID': 90,      # Fastest, highest priority
        'WPS_PIXIE': 80,  # Fast WPS attack
        'WPS_PIN': 70,    # Slower WPS attack
        'WPA_HS': 50,     # Handshake capture
        'WEP': 40,        # Slowest
    }

    @classmethod
    def attack_multiple(cls, targets):
        '''Attacks multiple targets with intelligent prioritization'''
        
        if any(t.wps for t in targets) and not AttackWPS.can_attack_wps():
            Color.pl('{!} {O}WPS attacks unavailable: missing reaver/bully{W}')

        Color.pl('{+} {G}Starting attacks on {W}{C}%d{W}{G} target(s){W}' % len(targets))
        attacked_targets = 0

        # Sort targets by signal strength
        targets = sorted(targets, key=lambda t: t.power, reverse=True)

        for index, target in enumerate(targets, start=1):
            attacked_targets += 1
            targets_remaining = len(targets) - index

            bssid = target.bssid
            essid = target.essid if target.essid_known else '{O}Unknown{W}'
            signal = target.power

            Color.pl('\n{+} ({G}%d{W}/{G}%d{W}) Attacking {C}%s{W} ({C}%s{W}) [{G}%d dBm{W}]' 
                    % (index, len(targets), bssid, essid, signal))

            should_continue = cls.attack_single(target, targets_remaining)
            if not should_continue:
                break

        Color.pl('\n{+} {G}Attack complete: {W}{C}%d{W}{G} target(s) attacked{W}' 
                % attacked_targets)
        return attacked_targets

    @classmethod
    def attack_single(cls, target, targets_remaining):
        '''Attacks single target with intelligent attack selection'''
        
        attacks = cls._build_attack_queue(target)

        if len(attacks) == 0:
            Color.pl('{!} {R}No attacks available for {W}{C}%s{W}' % target.essid)
            return True

        Color.pl('{+} {G}Queued {W}{C}%d{W}{G} attack(s){W}' % len(attacks))
        
        # Display attack queue
        for idx, (priority, attack_name, attack_obj) in enumerate(attacks, 1):
            Color.pl('   {G}%d{W}. {C}%s{W} (priority: {C}%d{W})' 
                    % (idx, attack_name, priority))

        return cls._execute_attack_queue(attacks, target, targets_remaining)

    @classmethod
    def _build_attack_queue(cls, target):
        '''Build prioritized attack queue for target'''
        attacks = []

        if Configuration.use_eviltwin:
            # TODO: EvilTwin attack
            pass

        elif 'WEP' in target.encryption:
            attacks.append((cls.ATTACK_PRIORITY['WEP'], 'WEP', AttackWEP(target)))

        elif 'WPA' in target.encryption:
            # WPA attack prioritization
            
            if not Configuration.use_pmkid_only:
                if target.wps != False and AttackWPS.can_attack_wps():
                    # Pixie-Dust first (faster)
                    if Configuration.wps_pixie:
                        attacks.append((
                            cls.ATTACK_PRIORITY['WPS_PIXIE'],
                            'WPS Pixie-Dust',
                            AttackWPS(target, pixie_dust=True)
                        ))

                    # PIN second
                    if Configuration.wps_pin:
                        attacks.append((
                            cls.ATTACK_PRIORITY['WPS_PIN'],
                            'WPS PIN',
                            AttackWPS(target, pixie_dust=False)
                        ))

            if not Configuration.wps_only:
                # PMKID before handshake (faster)
                attacks.append((
                    cls.ATTACK_PRIORITY['PMKID'],
                    'PMKID',
                    AttackPMKID(target)
                ))

                # Handshake capture (slowest)
                if not Configuration.use_pmkid_only:
                    attacks.append((
                        cls.ATTACK_PRIORITY['WPA_HS'],
                        'WPA Handshake',
                        AttackWPA(target)
                    ))

        # Sort by priority (highest first)
        attacks.sort(key=lambda x: x[0], reverse=True)
        return attacks

    @classmethod
    def _execute_attack_queue(cls, attacks, target, targets_remaining):
        '''Execute attack queue with error handling'''
        
        while len(attacks) > 0:
            priority, attack_name, attack = attacks.pop(0)
            
            try:
                Color.pl('\n{+} {G}Executing: {W}{C}%s{W}' % attack_name)
                result = attack.run()
                
                if result:
                    Color.pl('{+} {G}Success! {W}Attack completed.')
                    if attack.success and hasattr(attack, 'crack_result'):
                        attack.crack_result.save()
                    break  # Attack successful

            except KeyboardInterrupt:
                Color.pl('\n{!} {O}Interrupted{W}')
                answer = cls._handle_interruption(attack_name, targets_remaining, len(attacks))
                
                if answer is True:
                    continue  # Continue with next attack
                elif answer is None:
                    return True  # Skip to next target
                else:
                    return False  # Exit all attacks

            except Exception as e:
                Color.pl('{!} {R}Error: {O}%s{W}' % str(e))
                logger.exception("Attack error")
                continue

        return True

    @classmethod
    def _handle_interruption(cls, current_attack, targets_remaining, attacks_remaining):
        '''Handle user interruption with options'''
        
        if attacks_remaining == 0 and targets_remaining == 0:
            return None

        Color.pl('{+} {G}Interrupt Options:{W}')
        
        options_list = []
        if attacks_remaining > 0:
            options_list.append('{G}C{W}ontinue with next attack')
        if targets_remaining > 0:
            options_list.append('{O}S{W}kip to next target')
        options_list.append('{R}E{W}xit all attacks')

        for idx, option in enumerate(options_list, 1):
            Color.pl('   {G}%d{W}. %s' % (idx, option))

        from ..util.input import raw_input
        answer = raw_input(Color.s('{?} Select option: {W}')).lower().strip()

        if answer.startswith('c'):
            return True
        elif answer.startswith('s'):
            return None
        else:
            return False
