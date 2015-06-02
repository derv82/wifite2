#!/usr/bin/python

import argparse

class Arguments(object):
    def __init__(self):
        self.args = self.get_arguments()

    def get_arguments(self):
        description = 'Wrapper script around aircrack-ng and reaver'
        description += ' https://github.com/derv82/wifite'
        parser = argparse.ArgumentParser(
            description=description)

        # Global variables
        glob = parser.add_argument_group('SETTINGS')
        glob.add_argument('-i',
            action='store',
            dest='interface',
            metavar='interface',
            type=str,
            help='Wireless interface to use (default: ask)')
        glob.add_argument('-c',
            action='store',
            dest='channel',
            metavar='channel',
            type=int,
            help='Wireless channel to scan (default: all channels)')

        # WEP
        wep = parser.add_argument_group('WEP-RELATED')
        wep.add_argument('--wep',
            action='store_true',
            dest='wep_filter',
            help='Only show WEP-encrypted networks')
        wep.add_argument('--require-fakeauth',
            action='store_true',
            dest='require_fakeauth',
            help='Fails attacks if fake-authentication fails')

        # WPA
        wpa = parser.add_argument_group('WPA-RELATED')
        wpa.add_argument('--wpa',
            action='store_true',
            dest='wpa_filter',
            help='Only show WPA-encrypted networks')

        # WPS
        wps = parser.add_argument_group('WPS-RELATED')
        wps.add_argument('--wps',
            action='store_true',
            dest='wps_filter',
            help='Only show WPA networks with WPS enabled')
        wps.add_argument('--reaver',
            action='store_true',
            dest='reaver_only',
            help='Only use Reaver on WPS networks (no handshake attack)')
        wps.add_argument('--no-reaver',
            action='store_true',
            dest='no_reaver',
            help='Do NOT use Reaver on WPS networks (handshake only)')
        wps.add_argument('--pixie',
            action='store_true',
            dest='pixie_only',
            help='Only use the WPS Pixie-Dust attack (do not crack PINs)')
        
        # Cracking
        crack = parser.add_argument_group('CRACKING')
        crack.add_argument('--cracked',
            action='store_true',
            dest='cracked',
            help='Display previously-cracked access points')
        crack.add_argument('--check',
            action='store',
            metavar='[file]',
            dest='check',
            help='Check a .cap file for WPA handshakes')
        crack.add_argument('--crack-wpa',
            action='store',
            type=str,
            dest='crackwpa',
            metavar='[file]',
            help='Crack a .cap file containing a WPA handshake')
        crack.add_argument('--crack-wep',
            action='store',
            type=str,
            dest='crackwep',
            metavar='[file]',
            help='Crack a .cap file containing WEP IVS')
        crack.add_argument('--dict',
            action='store',
            type=str,
            dest='wordlist',
            metavar='[file]',
            help='Dictionary/wordlist to use for cracking')
        
        # Misc
        commands = parser.add_argument_group('FUNCTIONS')
        commands.add_argument('--update',
            action='store_true',
            dest='update',
            help='Update to latest version of Wifite (on github)')

        return parser.parse_args()

if __name__ == '__main__':
    a = Arguments()
    args = a.args
    print args

