#!/usr/bin/python

from py.Configuration import Configuration
from py.Scanner import Scanner
from py.Color import Color
from py.AttackWEP import AttackWEP
from py.AttackWPA import AttackWPA
from py.AttackWPS import AttackWPS

class Wifite(object):
    def __init__(self):
        pass

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

        for t in targets:
            Color.pl('{+} starting attacks against {C}%s{W} ({C}%s{W})'
                % (t.bssid, t.essid))
            if 'WEP' in t.encryption: # TODO: and configuration.use_wep
                attack = AttackWEP(t)
                attack.run()
            elif 'WPA' in t.encryption:
                if t.wps: # TODO: and Configuration.use_wps
                    attack = AttackWPS(t)
                    if attack.run():
                        # We cracked it.
                        break
                    else: # TODO: and Configuration.use_wpa
                        # WPS failed, try WPA handshake.
                        attack = AttackWPA(t)
                        attack.run()
                else: # TODO: and Configuration.use_wpa
                    # Not using WPS, try WPA handshake.
                    attack = AttackWPA(t)
                    attack.run()
            else:
                # TODO: Error: Can't attack - encryption not WEP or WPA
                pass

            # TODO: if attack.successful:
            # TODO: Save attack.crack_result
        pass

    def print_banner(self):
        """ Displays ASCII art of the highest caliber.  """
        Color.pl("")
        Color.pl("{G}  .;'                     `;,    ")
        Color.pl("{G} .;'  ,;'             `;,  `;,  " +
            "{W}WiFite v%.2f" % Configuration.version)
        Color.pl("{G}.;'  ,;'  ,;'     `;,  `;,  `;,  ")
        Color.pl("{G}::   ::   :   {GR}( ){G}   :   ::   ::  " +
            "{W}automated wireless auditor")
        Color.pl("{G}':.  ':.  ':. {GR}/_\\{G} ,:'  ,:'  ,:'  ")
        Color.pl("{G} ':.  ':.    {GR}/___\\{G}   ,:'  ,:'   " +
            "{W}designed for Linux")
        Color.pl("{G}  ':.       {GR}/_____\\{G}     ,:'     ")
        Color.pl("{G}           {GR}/       \\{G}            ")
        Color.pl("{W}")


if __name__ == '__main__':
    w = Wifite()
    try:
        w.print_banner()
        w.run()
    except Exception, e:
        Color.pl('\n{!} {R}Error:{O} %s{W}' % str(e))
        from traceback import format_exc
        print '\n    '
        print format_exc().replace('\n', '\n    ')
    except KeyboardInterrupt:
        Color.pl('\n{!} {O}interrupted{W}')
    Configuration.exit_gracefully(0)

