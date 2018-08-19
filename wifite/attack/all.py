#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..config import Configuration
from ..util.color import Color

class AttackAll(object):

    @classmethod
    def attack_multiple(cls, targets):
        '''
        Attacks all given `targets` (list[wifite.model.target]) until user interruption.
        Returns: Number of targets that were attacked (int)
        '''
        attacked_targets = 0
        targets_remaining = len(targets)
        for index, target in enumerate(targets, start=1):
            attacked_targets += 1
            targets_remaining -= 1

            bssid = target.bssid
            essid = target.essid if target.essid_known else '{O}ESSID unknown{W}'

            Color.pl('\n{+} ({G}%d{W}/{G}%d{W})' % (index, len(targets)) +
                     ' starting attacks against {C}%s{W} ({C}%s{W})' % (bssid, essid))

            should_continue = cls.attack_single(target, targets_remaining)
            if not should_continue:
                break

        return attacked_targets

    @classmethod
    def attack_single(cls, target, targets_remaining):
        '''
        Attacks a single `target` (wifite.model.target).
        Returns: True if attacks should continue, False otherwise.
        '''
        from .wep import AttackWEP
        from .wpa import AttackWPA
        from .wps import AttackWPS
        from .pmkid import AttackPMKID

        attacks = []

        if Configuration.use_eviltwin:
            # TODO: EvilTwin attack
            pass

        elif 'WEP' in target.encryption:
            attacks.append(AttackWEP(target))

        elif 'WPA' in target.encryption:
            # WPA can have multiple attack vectors:

            if target.wps:
                # WPS
                attacks.append(AttackWPS(target))

            # PMKID
            attacks.append(AttackPMKID(target))

            # Handshake capture
            attacks.append(AttackWPA(target))

        if len(attacks) == 0:
            Color.pl('{!} {R}Error: {O}unable to attack: encryption not WEP or WPA')
            return

        while len(attacks) > 0:
            attack = attacks.pop(0)
            try:
                result = attack.run()
                if result:
                    break  # Attack was successful, stop other attacks.
            except Exception as e:
                Color.pexception(e)
                continue
            except KeyboardInterrupt:
                Color.pl('\n{!} {O}interrupted{W}\n')
                if not cls.user_wants_to_continue(targets_remaining, len(attacks)):
                    return False  # Stop attacking other targets

        if attack.success:
            attack.crack_result.save()

        return True  # Keep attacking other targets


    @classmethod
    def user_wants_to_continue(cls, targets_remaining, attacks_remaining=0):
        '''
        Asks user if attacks should continue onto other targets
        Returns:
            True if user wants to continue, False otherwise.
        '''
        if attacks_remaining == 0 and targets_remaining == 0:
            return  # No targets or attacksleft, drop out

        prompt_list = []
        if attacks_remaining > 0:
            prompt_list.append(Color.s('{C}%d{W} attack(s)' % attacks_remaining))
        if targets_remaining > 0:
            prompt_list.append(Color.s('{C}%d{W} target(s)' % targets_remaining))
        prompt = ' and '.join(prompt_list)
        Color.pl('{+} %s remain, do you want to continue?' % prompt)

        prompt = Color.s('{+} type {G}c{W} to {G}continue{W}' +
                         ' or {R}s{W} to {R}stop{W}: ')

        from ..util.input import raw_input
        if raw_input(prompt).lower().startswith('s'):
            return False
        else:
            return True

