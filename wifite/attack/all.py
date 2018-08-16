#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .wep import AttackWEP
from .wpa import AttackWPA
from .wps import AttackWPS
from .pmkid import AttackPMKID
from ..config import Configuration
from ..util.color import Color
from ..util.input import raw_input

class AttackAll(object):

    @classmethod
    def attack_multiple(cls, targets):
        attacked_targets = 0
        targets_remaining = len(targets)
        for index, target in enumerate(targets, start=1):
            attacked_targets += 1
            targets_remaining -= 1

            bssid = target.bssid
            essid = target.essid if target.essid_known else "{O}ESSID unknown{W}"

            Color.pl('\n{+} ({G}%d{W}/{G}%d{W})' % (index, len(targets)) +
                     ' starting attacks against {C}%s{W} ({C}%s{W})' % (bssid, essid))

            should_continue = cls.attack_single(target, targets_remaining)
            if not should_continue:
                break

        return attacked_targets

    @classmethod
    def attack_single(cls, target, targets_remaining):
        attacks = []

        if Configuration.use_eviltwin:
            pass  # TODO:EvilTwin attack

        elif 'WEP' in target.encryption:
            attacks.append(AttackWEP(target))

        elif 'WPA' in target.encryption:
            # WPA can have multiple attack vectors
            if target.wps:
                attacks.append(AttackWPS(target))
            attacks.append(AttackPMKID(target))
            attacks.append(AttackWPA(target))

        if len(attacks) == 0:
            Color.pl("{!} {R}Error: {O}unable to attack: encryption not WEP or WPA")
            return

        for attack in attacks:
            try:
                result = attack.run()
                if result:
                    break  # Attack was successful, stop other attacks.
            except Exception as e:
                Color.pl("\n{!} {R}Error: {O}%s" % str(e))
                if Configuration.verbose > 0 or Configuration.print_stack_traces:
                    Color.pl('\n{!} {O}Full stack trace below')
                    from traceback import format_exc
                    Color.p('\n{!}    ')
                    err = format_exc().strip()
                    err = err.replace('\n', '\n{W}{!} {W}   ')
                    err = err.replace('  File', '{W}{D}File')
                    err = err.replace('  Exception: ', '{R}Exception: {O}')
                    Color.pl(err)
                continue
            except KeyboardInterrupt:
                Color.pl('\n{!} {O}interrupted{W}\n')
                if not cls.user_wants_to_continue(targets_remaining, 1):
                    return False  # Stop attacking other targets

        if attack.success:
            attack.crack_result.save()

        return True  # Keep attacking other targets


    @classmethod
    def user_wants_to_continue(cls, targets_remaining, attacks_remaining=0):
        ''' Asks user if attacks should continue onto other targets '''
        if attacks_remaining == 0 and targets_remaining == 0:
            # No targets or attacksleft, drop out
            return

        prompt_list = []
        if attacks_remaining > 0:
            prompt_list.append(Color.s('{C}%d{W} attack(s)' % attacks_remaining))
        if targets_remaining > 0:
            prompt_list.append(Color.s('{C}%d{W} target(s)' % targets_remaining))
        prompt = ' and '.join(prompt_list)
        Color.pl('{+} %s remain, do you want to continue?' % prompt)

        prompt = Color.s('{+} type {G}c{W} to {G}continue{W}' +
                         ' or {R}s{W} to {R}stop{W}: ')

        if raw_input(prompt).lower().startswith('s'):
            return False
        else:
            return True

