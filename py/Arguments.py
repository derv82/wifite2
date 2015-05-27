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
            dest='wep_only',
            help='Only target WEP-encrypted networks (ignores WPA)')

        # WPA
        wep = parser.add_argument_group('WPA-RELATED')
        wep.add_argument('--wpa',
            action='store_true',
            dest='wpa_only',
            help='Only target WPA-encrypted networks (ignores WEP)')

        # WPS
        wep = parser.add_argument_group('WPS-RELATED')
        wep.add_argument('--wps',
            action='store_true',
            dest='wps_only',
            help='Only target WPS-encrypted networks (ignores WEP/nonWPS)')
        wep.add_argument('--pixie',
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

