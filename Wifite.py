#!/usr/bin/python2.7

from py.Configuration import Configuration
from py.Scanner import Scanner
from py.Color import Color
from py.AttackWEP import AttackWEP
from py.AttackWPA import AttackWPA
from py.AttackWPS import AttackWPS
from py.CrackResult import CrackResult
from py.Handshake import Handshake

from json import loads
import os

class Wifite(object):
    
    def main(self):
        ''' Either performs action based on arguments, or starts attack scanning '''

        if os.getuid() != 0:
            Color.pl('{!} {R}error: {O}wifite{R} must be run as {O}root{W}')
            Color.pl('{!} {O}re-run as: sudo ./Wifite.py{W}')
            return

        Configuration.initialize(load_interface=False)

        if Configuration.show_cracked:
            self.display_cracked()

        elif Configuration.check_handshake:
            self.check_handshake(Configuration.check_handshake)

        elif Configuration.crack_wpa:
            # TODO: Crack .cap file at crack_wpa
            Color.pl('{!} Unimplemented method: crack_wpa')
            pass
        elif Configuration.crack_wep:
            # TODO: Crack .cap file at crack_wep
            Color.pl('{!} Unimplemented method: crack_wep')
            pass
        elif Configuration.update:
            # TODO: Get latest version from github
            Color.pl('{!} Unimplemented method: update')
            pass
        else:
            Configuration.get_interface()
            self.run()

    def display_cracked(self):
        ''' Show cracked targets from cracked.txt '''
        Color.pl('{+} displaying {C}cracked target(s){W}')
        name = CrackResult.cracked_file
        if not os.path.exists(name):
            Color.pl('{!} {O}file {C}%s{O} not found{W}' % name)
            return
        f = open(name, 'r')
        json = loads(f.read())
        f.close()
        for (index, item) in enumerate(json):
            Color.pl('\n{+} Cracked target #%d:' % (index + 1))
            cr = CrackResult.load(item)
            cr.dump()
        
    def check_handshake(self, capfile):
        ''' Analyzes .cap file for handshake '''
        Color.pl('{+} checking for handshake in .cap file {C}%s{W}' % capfile)
        if not os.path.exists(capfile):
            Color.pl('{!} {O}.cap file {C}%s{O} not found{W}' % capfile)
            return
        hs = Handshake(capfile, bssid=Configuration.target_bssid, essid=Configuration.target_essid)
        hs.analyze()


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

        targets_remaining = len(targets)
        for index, t in enumerate(targets):
            targets_remaining -= 1

            Color.pl('\n{+} ({G}%d{W}/{G}%d{W})' % (index + 1, len(targets)) +
                     ' starting attacks against {C}%s{W} ({C}%s{W})'
                % (t.bssid, t.essid))
            if 'WEP' in t.encryption:
                attack = AttackWEP(t)
            elif 'WPA' in t.encryption:
                if t.wps:
                    attack = AttackWPS(t)
                    result = False
                    try:
                        result = attack.run()
                    except KeyboardInterrupt:
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
            except KeyboardInterrupt:
                if not self.user_wants_to_continue(targets_remaining):
                    break

            if attack.success:
                attack.crack_result.save()


    def print_banner(self):
        """ Displays ASCII art of the highest caliber.  """
        Color.pl("")
        Color.pl("{G}  .;'                     `;,    ")
        Color.pl("{G} .;'  ,;'             `;,  `;,  {W}WiFite v%.2f" % Configuration.version)
        Color.pl("{G}.;'  ,;'  ,;'     `;,  `;,  `;,  ")
        Color.pl("{G}::   ::   :   {GR}( ){G}   :   ::   ::  {W}Automated Wireless Auditor")
        Color.pl("{G}':.  ':.  ':. {GR}/_\\{G} ,:'  ,:'  ,:'  ")
        Color.pl("{G} ':.  ':.    {GR}/___\\{G}   ,:'  ,:'   {C}https://github.com/derv82/wifite2{W}")
        Color.pl("{G}  ':.       {GR}/_____\\{G}     ,:'     ")
        Color.pl("{G}           {GR}/       \\{G}         ")
        Color.pl("{W}")


    def user_wants_to_continue(self, targets_remaining, attacks_remaining=0):
        ''' Asks user if attacks should continue onto other targets '''
        Color.pl('\n{!} {O}interrupted{W}\n')
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


if __name__ == '__main__':
    w = Wifite()
    try:
        w.print_banner()
        w.main()
    except Exception, e:
        Color.pl('\n{!} {R}Error:{O} %s{W}' % str(e))
        if Configuration.verbose > 0:
            Color.pl('\n{!} {O}Full stack trace below')
            from traceback import format_exc
            Color.p('\n{!}    ')
            err = format_exc().strip()
            err = err.replace('\n', '\n{!} {C}   ')
            err = err.replace('  File', '{W}File')
            err = err.replace('  Exception: ', '{R}Exception: {O}')
            Color.pl(err)
        Color.pl('\n{!} {R}Exiting{W}\n')
    except KeyboardInterrupt:
        Color.pl('\n{!} {O}interrupted{W}')
    Configuration.exit_gracefully(0)

