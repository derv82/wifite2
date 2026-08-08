#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from .config import Configuration
except (ValueError, ImportError) as e:
    raise Exception('Run wifite from the root directory', e)

from .util.color import Color
import os
import sys
import time

class Wifite(object):

    def __init__(self):
        '''
        Initializes Wifite with advanced features.
        '''
        self.print_banner()
        Configuration.initialize(load_interface=False)

        if os.getuid() != 0:
            Color.pl('{!} {R}error: {O}wifite{R} must be run as {O}root{W}')
            Color.pl('{!} {R}re-run with {O}sudo{W}')
            Configuration.exit_gracefully(0)

        from .tools.dependency import Dependency
        Dependency.run_dependency_check()

        self.start_time = time.time()
        self.attack_count = 0

    def start(self):
        '''
        Starts target-scan + attack loop with advanced optimizations.
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
        '''Displays ASCII art with version info'''
        Color.pl(r' {G}  .     {GR}{D}     {W}{G}     .    {W}')
        Color.pl(r' {G}.´  ·  .{GR}{D}     {W}{G}.  ·  `.  {G}wifite {D}%s{W}' % Configuration.version)
        Color.pl(r' {G}:  :  : {GR}{D} (¯) {W}{G} :  :  :  {W}{D}Advanced Edition{W}')
        Color.pl(r' {G}`.  ·  `{GR}{D} /¯\ {W}{G}´  ·  .´  {C}{D}WPS PIN + Handshake Optimized{W}')
        Color.pl(r' {G}  `     {GR}{D}/¯¯¯\{W}{G}     ´    {W}')
        Color.pl('')
        
        if Configuration.verbose >= 1:
            self.print_configuration()

    def print_configuration(self):
        '''Prints active configuration settings'''
        Color.pl('{C}[*] Active Configuration:{W}')
        if Configuration.fast_handshake_capture:
            Color.pl('{+} Fast Handshake Capture: {G}ENABLED{W}')
        if Configuration.wps_pin_enabled:
            Color.pl('{+} WPS PIN Attack: {G}ENABLED{W} (timeout: {G}%ds{W})' % 
                    Configuration.wps_pin_timeout)
        if Configuration.adaptive_timeout:
            Color.pl('{+} Adaptive Timeout: {G}ENABLED{W}')
        Color.pl('{+} Parallel Attacks: {G}%d{W}' % Configuration.parallel_attacks)
        Color.pl('')

    def scan_and_attack(self):
        '''
        1) Scans for targets with optimizations
        2) Attacks each target with advanced tactics
        '''
        from .util.scanner import Scanner
        from .attack.all import AttackAll

        Color.pl('')

        try:
            # Scan with optimizations
            s = Scanner()
            targets = s.select_targets()

            if not targets:
                Color.pl('{!} {O}No targets found{W}')
                return

            # Attack with advanced strategies
            attacked_targets = self._attack_targets(targets)
            Color.pl('{+} Finished attacking {C}%d{W} target(s)' % attacked_targets)
            
            self._print_statistics()

        except Exception as e:
            Color.pexception(e)

    def _attack_targets(self, targets):
        '''Attack targets with advanced optimization'''
        from .attack.all import AttackAll
        
        attacked = 0
        for target in targets[:Configuration.parallel_attacks]:
            self.attack_count += 1
            try:
                result = AttackAll.attack_multiple([target])
                attacked += result
            except Exception as e:
                Color.pl('{!} {R}Error attacking target:{W} %s' % str(e))
                
        return attacked

    def _print_statistics(self):
        '''Print attack statistics'''
        elapsed_time = time.time() - self.start_time
        Color.pl('')
        Color.pl('{C}[*] Attack Statistics:{W}')
        Color.pl('{+} Total Attacks: {G}%d{W}' % self.attack_count)
        Color.pl('{+} Time Elapsed: {G}%.2f seconds{W}' % elapsed_time)


def entry_point():
    try:
        wifite = Wifite()
        wifite.start()
    except Exception as e:
        Color.pexception(e)
        Color.pl('\n{!} {R}Exiting{W}\n')
    except KeyboardInterrupt:
        Color.pl('\n{!} {O}Interrupted, Shutting down...{W}')
    finally:
        Configuration.exit_gracefully(0)

if __name__ == '__main__':
    entry_point()
