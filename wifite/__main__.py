#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from .config import Configuration
except (ValueError, ImportError) as e:
    raise Exception('You may need to run wifite from the root directory (which includes README.md)', e)

from .util.color import Color

import os


class Wifite(object):

    def __init__(self):
        '''
        Initializes Wifite. Checks for root permissions and ensures dependencies are installed.
        '''

        self.print_banner()

        Configuration.initialize(load_interface=False)

        if os.getuid() != 0:
            Color.pl('{!} {R}error: {O}wifite{R} must be run as {O}root{W}')
            Color.pl('{!} {R}re-run with {O}sudo{W}')
            Configuration.exit_gracefully(0)

        from .tools.dependency import Dependency
        Dependency.run_dependency_check()

    def start(self):
        '''
        Starts target-scan + attack loop, or launches utilities depending on user input.
        '''
        from .model.result import CrackResult
        from .model.handshake import Handshake
        from .util.crack import CrackHelper

        if Configuration.show_cracked:
            CrackResult.display()

        elif Configuration.check_handshake:
            Handshake.check()

        elif Configuration.crack_handshake:
            CrackHelper.run()

        else:
            Configuration.get_monitor_mode_interface()
            self.scan_and_attack()

    def print_banner(self):
        '''Displays ASCII art of the highest caliber.'''
        Color.pl(r' {G}  .     {GR}{D}     {W}{G}     .    {W}')
        Color.pl(r' {G}.´  ·  .{GR}{D}     {W}{G}.  ·  `.  {G}wifite2 {D}%s{W}' % Configuration.version)
        Color.pl(r' {G}:  :  : {GR}{D} (¯) {W}{G} :  :  :  {W}{D}a wireless auditor by @derv82{W}')
        Color.pl(r' {G}`.  ·  `{GR}{D} /¯\ {W}{G}´  ·  .´  {W}{D}maintained by kimocoder{W}')
        Color.pl(r' {G}  `     {GR}{D}/¯¯¯\{W}{G}     ´    {C}{D}https://github.com/kimocoder/wifite2{W}')
        Color.pl('')

    def scan_and_attack(self):
        '''
        1) Scans for targets, asks user to select targets
        2) Attacks each target
        '''
        from .util.scanner import Scanner
        from .attack.all import AttackAll

        attacked_targets = 0
        Color.pl('')

        # Scan
        s = Scanner()
        do_continue = s.find_targets()
        targets = s.select_targets()

        if Configuration.infinite_mode:
            while do_continue:
                AttackAll.attack_multiple(targets)
                do_continue = s.update_targets()
                if not do_continue:
                    break
                targets = s.select_targets()
            attacked_targets = s.get_num_attacked()
        else:
            # Attack
            attacked_targets = AttackAll.attack_multiple(targets)

        Color.pl('{+} Finished attacking {C}%d{W} target(s), exiting' % attacked_targets)


def entry_point():
    try:
        wifite = Wifite()
        wifite.start()
    except Exception as e:
        Color.pexception(e)
        Color.pl('\n{!} {R}Exiting{W}\n')

    except KeyboardInterrupt:
        Color.pl('\n{!} {O}Interrupted, Shutting down...{W}')

    Configuration.exit_gracefully(0)


if __name__ == '__main__':
    entry_point()
