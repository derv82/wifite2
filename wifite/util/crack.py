#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.process import Process
from ..util.color import Color
from ..util.input import raw_input
from ..config import Configuration

from datetime import datetime

import os


# TODO: Bring back the 'print' option, for easy copy/pasting.
# Just one-liners people can paste into terminal.

class CrackHelper:
    '''Manages handshake retrieval, selection, and running the cracking commands.'''

    TYPES = {
        '4-WAY': 'WPA 4-Way Handshake',
        'PMKID': 'WPA PKID Hash'
    }


    @classmethod
    def run(cls):
        Configuration.initialize(False)

        if not Configuration.wordlist:
            Color.p('\n{+} Enter wordlist file to use for cracking: {G}')
            Configuration.wordlist = raw_input()
            if not os.path.exists(Configuration.wordlist):
                Color.pl('{!} {R}Wordlist {O}%s{R} not found. Exiting.' % Configuration.wordlist)
                return
            Color.pl('')

        handshakes = cls.get_handshakes()
        hs_to_crack = cls.get_user_selection(handshakes)

        # TODO: Ask what method to use for WPA (aircrack, pyrit, john, hashcat, cowpatty)

        for hs in hs_to_crack:
            cls.crack(hs)

    @classmethod
    def get_handshakes(cls):
        handshakes = []

        skipped_pmkid_files = 0

        hs_dir = Configuration.wpa_handshake_dir
        Color.pl('\n{+} Listing captured handshakes from {C}%s{W} ...\n' % os.path.abspath(hs_dir))
        for hs_file in os.listdir(hs_dir):
            if hs_file.count('_') != 3:
                continue

            if hs_file.endswith('.cap'):
                # WPA Handshake
                hs_type = '4-WAY'
            elif hs_file.endswith('.16800'):
                # PMKID hash
                if not Process.exists('hashcat'):
                    skipped_pmkid_files += 1
                    continue
                hs_type = 'PMKID'
            else:
                continue

            name, essid, bssid, date = hs_file.split('_')
            date = date.rsplit('.', 1)[0]
            days,hours = date.split('T')
            hours = hours.replace('-', ':')
            date = '%s %s' % (days, hours)

            handshake = {
                'filename': os.path.join(hs_dir, hs_file),
                'bssid': bssid.replace('-', ':'),
                'essid': essid,
                'date': date,
                'type': hs_type
            }

            if hs_file.endswith('.cap'):
                # WPA Handshake
                handshake['type'] = '4-WAY'
            elif hs_file.endswith('.16800'):
                # PMKID hash
                handshake['type'] = 'PMKID'
            else:
                continue

            handshakes.append(handshake)

        if skipped_pmkid_files > 0:
            Color.pl('{!} {O}Skipping %d {R}*.16800{O} files because {R}hashcat{O} is missing.' % skipped_pmkid_files)

        # Sort by Date (Descending)
        return sorted(handshakes, key=lambda x: x.get('date'), reverse=True)


    @classmethod
    def print_handshakes(cls, handshakes):
        # Header
        max_essid_len = max(max([len(hs['essid']) for hs in handshakes]), len('ESSID (truncated)'))
        Color.p('{D}  NUM')
        Color.p('  ESSID (truncated)'.ljust(max_essid_len))
        Color.p('  BSSID'.ljust(19))
        Color.p('  TYPE'.ljust(7))
        Color.p('  DATE CAPTURED\n')
        Color.p('  ---')
        Color.p('  ' + ('-' * max_essid_len))
        Color.p('  ' + ('-' * 17))
        Color.p('  ' + ('-' * 6))
        Color.p('  ' + ('-' * 19) + '{W}\n')
        # Handshakes
        for index, handshake in enumerate(handshakes, start=1):
            bssid = handshake['bssid']
            date  = handshake['date']
            Color.p('  {G}%s{W}' % str(index).rjust(3))
            Color.p('  {C}%s{W}' % handshake['essid'].ljust(max_essid_len))
            Color.p('  {O}%s{W}' % handshake['bssid'].ljust(17))
            Color.p('  {C}%s{W}' % handshake['type'].ljust(5))
            Color.p('  {W}%s{W}\n' % handshake['date'])


    @classmethod
    def get_user_selection(cls, handshakes):
        cls.print_handshakes(handshakes)

        Color.p('{+} Select handshake(s) to crack ({G}%d{W}-{G}%d{W}, select multiple with {C},{W} or {C}-{W}): {G}' % (1, len(handshakes)))
        choices = raw_input()

        selection = []
        for choice in choices.split(','):
            if '-' in choice:
                first, last = [int(x) for x in choice.split('-')]
                for index in range(first, last + 1):
                    selection.append(handshakes[index-1])
            else:
                index = int(choice)
                selection.append(handshakes[index-1])

        return selection


    @classmethod
    def crack(cls, hs):
        Color.pl('\n{+} Cracking {C}%s{W} ({C}%s{W}) using {G}%s{W} method' % (hs['essid'], hs['bssid'], hs['type']))
        if hs['type'] == 'PMKID':
            crack_result = cls.crack_pmkid(hs)
        elif hs['type'] == '4-WAY':
            crack_result = cls.crack_4way(hs)
        else:
            raise ValueError('Cannot crack handshake: Type is not PMKID or 4-WAY. Handshake=%s' % hs)

        if crack_result is None:
            # Failed to crack
            Color.pl('{!} {R}Failed to crack {O}%s{R} ({O}%s{R}): Passphrase not in dictionary' % (
                hs['essid'], hs['bssid']))
        else:
            # Cracked, replace existing entry (if any), or add to
            Color.pl('{+} {G}Cracked{W} {C}%s{W} ({C}%s{W}). Key: "{G}%s{W}"' % (
                hs['essid'], hs['bssid'], crack_result.key))
            crack_result.save()


    @classmethod
    def crack_4way(cls, hs):
        from ..attack.wpa import AttackWPA
        from ..model.handshake import Handshake
        from ..model.wpa_result import CrackResultWPA

        handshake = Handshake(hs['filename'],
                bssid=hs['bssid'],
                essid=hs['essid'])

        key = None
        try:
            key = AttackWPA.crack_handshake(handshake, Configuration.wordlist, verbose=True)
        except KeyboardInterrupt:
            Color.pl('\n{!} Interrupted')

        if key is not None:
            return CrackResultWPA(hs['bssid'], hs['essid'], hs['filename'], key)
        else:
            return None


    @classmethod
    def crack_pmkid(cls, hs):
        from ..tools.hashcat import Hashcat
        from ..model.pmkid_result import CrackResultPMKID

        key = None
        try:
            key = Hashcat.crack_pmkid(hs['filename'], verbose=True)
        except KeyboardInterrupt:
            Color.pl('\n{!} Interrupted')

        if key is not None:
            return CrackResultPMKID(hs['bssid'], hs['essid'], hs['filename'], key)
        else:
            return None


if __name__ == '__main__':
    CrackHelper.run()

