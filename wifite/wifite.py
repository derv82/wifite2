#!/usr/bin/python3.7
# -*- coding: utf-8 -*-

try:
    from .config import Configuration
except (ValueError, ImportError) as e:
    raise Exception('You may need to run wifite from the root directory (which includes README.md)', e)

from .util.scanner import Scanner
from .util.process import Process
from .util.color import Color
from .util.crack import CrackHandshake
from .util.input import raw_input
from .attack.wep import AttackWEP
from .attack.wpa import AttackWPA
from .attack.wps import AttackWPS
from .model.result import CrackResult
from .model.handshake import Handshake

import json
import os
import sys

class Wifite(object):

    def main(self):
        ''' Either performs action based on arguments, or starts attack scanning '''

        if os.getuid() != 0:
            Color.pl('{!} {R}error: {O}wifite{R} must be run as {O}root{W}')
            Color.pl('{!} {O}re-run as: sudo ./Wifite.py{W}')
            Configuration.exit_gracefully(0)

        Configuration.initialize(load_interface=False)

        self.dependency_check()

        if Configuration.show_cracked:
            self.display_cracked()

        elif Configuration.check_handshake:
            self.check_handshake(Configuration.check_handshake)
        elif Configuration.crack_handshake:
            CrackHandshake()
        else:
            Configuration.get_monitor_mode_interface()
            self.run()


    def dependency_check(self):
        ''' Check that required programs are installed '''
        from .tools.airmon import Airmon
        from .tools.airodump import Airodump
        from .tools.aircrack import Aircrack
        from .tools.aireplay import Aireplay
        from .tools.ifconfig import Ifconfig
        from .tools.iwconfig import Iwconfig
        from .tools.bully import Bully
        from .tools.reaver import Reaver
        from .tools.wash import Wash
        from .tools.pyrit import Pyrit
        from .tools.tshark import Tshark
        from .tools.macchanger import Macchanger

        apps = [
                # Aircrack
                Airmon, Airodump, Aircrack, Aireplay,
                # wireless/net tools
                Iwconfig, Ifconfig,
                # WPS
                Reaver, Bully,
                # Cracking/handshakes
                Pyrit, Tshark,
                # Misc
                Macchanger
            ]

        missing_required = any([app.fails_dependency_check() for app in apps])

        if missing_required:
            Color.pl('{!} {R}required app(s) were not found, exiting.{W}')
            sys.exit(-1)

        #if missing_optional:
        #    Color.pl('{!} {O}recommended app(s) were not found')
        #    Color.pl('{!} {O}wifite may not work as expected{W}')

    def display_cracked(self):
        ''' Show cracked targets from cracked.txt '''
        name = CrackResult.cracked_file
        if not os.path.exists(name):
            Color.pl('{!} {O}file {C}%s{O} not found{W}' % name)
            return

        with open(name, 'r') as fid:
            cracked_targets = json.loads(fid.read())

        if len(cracked_targets) == 0:
            Color.pl('{!} {R}no results found in {O}%s{W}' % name)
        else:
            Color.pl('{+} displaying {G}%d {C}cracked target(s){W}\n' % len(cracked_targets))
            for item in cracked_targets:
                cr = CrackResult.load(item)
                cr.dump()
                Color.pl('')

    def check_handshake(self, capfile):
        ''' Analyzes .cap file for handshake '''
        if capfile == '<all>':
            Color.pl('{+} checking all handshakes in {G}"./hs"{W} directory\n')
            try:
                capfiles = [os.path.join('hs', x) for x in os.listdir('hs') if x.endswith('.cap')]
            except OSError as e:
                capfiles = []
            if len(capfiles) == 0:
                Color.pl('{!} {R}no .cap files found in {O}"./hs"{W}\n')
        else:
            capfiles = [capfile]

        for capfile in capfiles:
            Color.pl('{+} checking for handshake in .cap file {C}%s{W}' % capfile)
            if not os.path.exists(capfile):
                Color.pl('{!} {O}.cap file {C}%s{O} not found{W}' % capfile)
                return
            hs = Handshake(capfile, bssid=Configuration.target_bssid, essid=Configuration.target_essid)
            hs.analyze()
            Color.pl('')

    def run(self):
        '''
            Main program.
            1) Scans for targets, asks user to select targets
            2) Attacks each target
        '''
        s = Scanner()
        if s.target:
            # We found the target we want
            targets = [s.target]
        else:
            targets = s.select_targets()

        attacked_targets = 0
        targets_remaining = len(targets)
        for idx, t in enumerate(targets, start=1):
            attacked_targets += 1
            targets_remaining -= 1

            Color.pl('\n{+} ({G}%d{W}/{G}%d{W})' % (idx, len(targets)) +
                     ' starting attacks against {C}%s{W} ({C}%s{W})'
                % (t.bssid, t.essid if t.essid_known else "{O}ESSID unknown"))

            # TODO: Check if Eviltwin attack is selected.

            if Configuration.use_eviltwin:
                pass

            elif 'WEP' in t.encryption:
                attack = AttackWEP(t)

            elif 'WPA' in t.encryption:
                # TODO: Move WPS+WPA decision to a combined attack
                if t.wps:
                    attack = AttackWPS(t)
                    result = False
                    try:
                        result = attack.run()
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
                    except KeyboardInterrupt:
                        Color.pl('\n{!} {O}interrupted{W}\n')
                        if not self.user_wants_to_continue(targets_remaining, 1):
                            break

                    if result and attack.success:
                        # We cracked it.
                        attack.crack_result.save()
                        continue
                    else:
                        # WPS failed, try WPA handshake.
                        attack = AttackWPA(t)
                else:
                    # Not using WPS, try WPA handshake.
                    attack = AttackWPA(t)
            else:
                Color.pl("{!} {R}Error: {O}unable to attack: encryption not WEP or WPA")
                continue

            try:
                attack.run()
            except Exception as e:
                Color.pl("\n{!} {R}Error: {O}%s" % str(e))
                if Configuration.verbose > 0 or True:
                    Color.pl('\n{!} {O}Full stack trace below')
                    from traceback import format_exc
                    Color.p('\n{!}    ')
                    err = format_exc().strip()
                    err = err.replace('\n', '\n{W}{!} {W}   ')
                    err = err.replace('  File', '{W}{D}File')
                    err = err.replace('  Exception: ', '{R}Exception: {O}')
                    Color.pl(err)
            except KeyboardInterrupt:
                Color.pl('\n{!} {O}interrupted{W}\n')
                if not self.user_wants_to_continue(targets_remaining):
                    break

            if attack.success:
                attack.crack_result.save()
        Color.pl("{+} Finished attacking {C}%d{W} target(s), exiting" % attacked_targets)


    def print_banner(self):
        """ Displays ASCII art of the highest caliber.  """
        Color.pl('''\
{G}  .     {GR}{D}     {W}{G}     .    {W}
{G}.´  ·  .{GR}{D}     {W}{G}.  ·  `.  {G}wifite {D}%s{W}
{G}:  :  : {GR}{D} (¯) {W}{G} :  :  :  {W}{D}automated wireless auditor
{G}`.  ·  `{GR}{D} /¯\ {W}{G}´  ·  .´  {C}{D}https://github.com/derv82/wifite2
{G}  `     {GR}{D}/¯¯¯\{W}{G}     ´    {W}
''' % Configuration.version)

    def user_wants_to_continue(self, targets_remaining, attacks_remaining=0):
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


def run():
    w = Wifite()
    w.print_banner()

    try:
        w.main()

    except Exception as e:
        Color.pl('\n{!} {R}Error:{O} %s{W}' % str(e))

        if Configuration.verbose > 0 or True:
            Color.pl('\n{!} {O}Full stack trace below')
            from traceback import format_exc
            Color.p('\n{!}    ')
            err = format_exc().strip()
            err = err.replace('\n', '\n{W}{!} {W}   ')
            err = err.replace('  File', '{W}{D}File')
            err = err.replace('  Exception: ', '{R}Exception: {O}')
            Color.pl(err)

        Color.pl('\n{!} {R}Exiting{W}\n')

    except KeyboardInterrupt:
        Color.pl('\n{!} {O}interrupted, shutting down...{W}')

    Configuration.exit_gracefully(0)

if __name__ == '__main__':
    run()
