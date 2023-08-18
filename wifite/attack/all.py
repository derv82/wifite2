#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .pmkid import AttackPMKID
from .wep import AttackWEP
from .wpa import AttackWPA
from .wps import AttackWPS
from ..config import Configuration
from ..model.target import WPSState
from ..util.color import Color


class AttackAll:
    @classmethod
    def attack_multiple(cls, targets):
        """
        Attacks all given `targets` (list[wifite.model.target]) until user interruption.
        Returns: Number of targets that were attacked (int)
        """
        if any(t.wps for t in targets) and not AttackWPS.can_attack_wps():
            # Warn that WPS attacks are not available.
            Color.pl(
                '{!} {O}Note: WPS attacks are not possible because you do not have {C}reaver{O} nor {C}bully{W}')

        attacked_targets = 0
        targets_remaining = len(targets)
        for index, target in enumerate(targets, start=1):
            if Configuration.attack_max != 0 and index > Configuration.attack_max:
                print((
                    f"Attacked {Configuration.attack_max:d} targets, stopping because of the --first flag"))
                break
            attacked_targets += 1
            targets_remaining -= 1

            bssid = target.bssid
            essid = target.essid if target.essid_known else '{O}ESSID unknown{W}'

            Color.pl(
                f'\n{{+}} ({{G}}{index:d}{{W}}/{{G}}{len(targets):d}{{W}})' +
                f' Starting attacks against {{C}}{bssid}{{W}} ({{C}}{essid}{{W}})')

            should_continue = cls.attack_single(target, targets_remaining)
            if not should_continue:
                break

        return attacked_targets

    @classmethod
    def attack_single(cls, target, targets_remaining):
        """
        Attacks a single `target` (wifite.model.target).
        Returns: True if attacks should continue, False otherwise.
        """
        global attack
        if 'MGT' in target.authentication:
            Color.pl(
                "\n{!}{O}Skipping. Target is using {C}WPA-Enterprise {O}and can not be cracked.")
            return True

        attacks = []

        if Configuration.use_eviltwin:
            # TODO: EvilTwin attack
            pass

        elif 'WEP' in target.encryption:
            attacks.append(AttackWEP(target))

        elif 'WPA' in target.encryption:
            # WPA can have multiple attack vectors:

            # WPS
            if not Configuration.use_pmkid_only and target.wps is WPSState.UNLOCKED and AttackWPS.can_attack_wps():
                # Pixie-Dust
                if Configuration.wps_pixie:
                    attacks.append(AttackWPS(target, pixie_dust=True))

                # Null PIN zero-day attack
                if Configuration.wps_pin:
                    attacks.append(AttackWPS(target, pixie_dust=False, null_pin=True))

                # PIN attack
                if Configuration.wps_pin:
                    attacks.append(AttackWPS(target, pixie_dust=False))

            if not Configuration.wps_only:
                # PMKID
                attacks.append(AttackPMKID(target))

                # Handshake capture
                if not Configuration.use_pmkid_only:
                    attacks.append(AttackWPA(target))

        if not attacks:
            Color.pl('{!} {R}Error: {O}Unable to attack: no attacks available')
            return True  # Keep attacking other targets (skip)

        while attacks:
            # Needed by infinite attack mode in order to count how many targets were attacked
            target.attacked = True
            attack = attacks.pop(0)
            try:
                result = attack.run()
                if result:
                    break  # Attack was successful, stop other attacks.
            except Exception as e:
                # TODO:kimocoder: below is a great way to handle Exception
                # rather then running full traceback in run of parsing to console.
                Color.pl(f'\r {{!}} {{R}}Error{{W}}: {str(e)}')
                #Color.pexception(e)         # This was the original one which parses full traceback
                #Color.pl('\n{!} {R}Exiting{W}\n')      # Another great one for other uasages.
                continue
            except KeyboardInterrupt:
                Color.pl('\n{!} {O}Interrupted{W}\n')
                answer = cls.user_wants_to_continue(targets_remaining, len(attacks))
                if answer is True:
                    continue  # Keep attacking the same target (continue)
                return answer is None
        if attack.success:
            attack.crack_result.save()

        return True  # Keep attacking other targets

    @classmethod
    def user_wants_to_continue(cls, targets_remaining, attacks_remaining=0):
        """
        Asks user if attacks should continue onto other targets
        Returns:
            None if the user wants to skip the current target
            True if the user wants to continue to the next attack on the current target
            False if the user wants to stop the remaining attacks
        """
        if attacks_remaining == 0 and targets_remaining == 0:
            return None # No targets or attacksleft, drop out

        prompt_list = []
        if attacks_remaining > 0:
            prompt_list.append(Color.s(f'{{C}}{attacks_remaining:d}{{W}} attack(s)'))
        if targets_remaining > 0:
            prompt_list.append(Color.s(f'{{C}}{targets_remaining:d}{{W}} target(s)'))
        prompt = ' and '.join(prompt_list) + ' remain'
        Color.pl(f'{{+}} {prompt}')

        prompt = '{+} Do you want to'
        options = '('

        if attacks_remaining > 0:
            prompt += ' {G}continue{W} attacking,'
            options += '{G}c{W}{D}, {W}'

        if targets_remaining > 0:
            prompt += ' {O}skip{W} to the next target,'
            options += '{O}s{W}{D}, {W}'

        if Configuration.infinite_mode:
            options += '{R}r{W})'
            prompt += f' or {{R}}return{{W}} to scanning {options}? {{C}}'
        else:
            options += '{R}e{W})'
            prompt += f' or {{R}}exit{{W}} {options}? {{C}}'

        Color.p(prompt)
        answer = input().lower()

        if answer.startswith('s'):
            return None  # Skip
        return not answer.startswith('e') and not answer.startswith('r')
