#!/usr/bin/env python
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
from .attack.all import AttackAll
from .model.result import CrackResult
from .model.handshake import Handshake
from .tools.dependency import Dependency

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

        Dependency.run_dependency_check()

        if Configuration.show_cracked:
            CrackResult.display()

        elif Configuration.check_handshake:
            Handshake.check()
        elif Configuration.crack_handshake:
            CrackHandshake()
        else:
            Configuration.get_monitor_mode_interface()
            self.run()


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

        attacked_targets = AttackAll.attack_multiple(targets)
        Color.pl("{+} Finished attacking {C}%d{W} target(s), exiting" % attacked_targets)


    def print_banner(self):
        """ Displays ASCII art of the highest caliber.  """
        Color.pl(r'''
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
