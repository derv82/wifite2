#!/usr/bin/python

from py.Scanner import Scanner
from py.Color import Color
from py.AttackWEP import AttackWEP
from py.AttackWPA import AttackWPA

class Wifite(object):
    def __init__(self):
        pass

    def run(self):
        s = Scanner()
        targets = s.select_targets()
        for t in targets:
            Color.pl('{+} starting attacks against {C}%s{W} ({C}%s{W})'
                % (t.bssid, t.essid))
            # TODO: Check if Configuration says to attack certain encryptions.
            if 'WEP' in t.encryption:
                attack = AttackWEP(t)
            elif 'WPA' in t.encryption:
                # TODO: Check if WPS, attack WPS
                attack = AttackWPA(t)
            attack.run()
        pass

if __name__ == '__main__':
    w = Wifite()
    try:
        w.run()
    except Exception, e:
        Color.pl('\n{!} {R}Error:{O} %s{W}' % str(e))
        #from traceback import format_exc
        #format_exc().replace('\n', '\n    ')
    except KeyboardInterrupt:
        Color.pl('\n{!} {O}interrupted{W}')

