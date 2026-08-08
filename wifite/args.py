#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .util.color import Color
import argparse, sys

class Arguments(object):
    ''' Holds arguments used by the Wifite '''

    def __init__(self, configuration):
        self.verbose = '-v' in sys.argv or '-hv' in sys.argv or '-vh' in sys.argv
        self.config = configuration
        self.args = self.get_arguments()

    def _verbose(self, msg):
        if self.verbose:
            return Color.s(msg)
        else:
            return argparse.SUPPRESS

    def get_arguments(self):
        ''' Returns parser.args() containing all program arguments '''

        parser = argparse.ArgumentParser(
            usage=argparse.SUPPRESS,
            formatter_class=lambda prog: argparse.HelpFormatter(
                prog, max_help_position=80, width=130))

        self._add_global_args(parser.add_argument_group(Color.s('{C}SETTINGS{W}')))
        self._add_advanced_args(parser.add_argument_group(Color.s('{C}ADVANCED OPTIONS{W}')))
        self._add_wep_args(parser.add_argument_group(Color.s('{C}WEP{W}')))
        self._add_wpa_args(parser.add_argument_group(Color.s('{C}WPA{W}')))
        self._add_wps_args(parser.add_argument_group(Color.s('{C}WPS{W}')))
        self._add_pmkid_args(parser.add_argument_group(Color.s('{C}PMKID{W}')))
        self._add_command_args(parser.add_argument_group(Color.s('{C}COMMANDS{W}')))

        return parser.parse_args()

    def _add_global_args(self, glob):
        glob.add_argument('-v', '--verbose',
            action='count', default=0, dest='verbose',
            help=Color.s('Shows more options ({C}-h -v{W})'))

        glob.add_argument('-i', action='store', dest='interface',
            metavar='[interface]', type=str,
            help=Color.s('Wireless interface, e.g. {C}wlan0mon{W}'))

        glob.add_argument('-c', '--channel', action='store', dest='channel',
            metavar='[channel]', type=int,
            help=Color.s('Wireless channel to scan'))

        glob.add_argument('-5', '--5ghz', action='store_true', dest='five_ghz',
            help=self._verbose('Include 5Ghz channels'))

        glob.add_argument('-mac', '--random-mac', action='store_true',
            dest='random_mac', help=Color.s('Randomize MAC address'))

        glob.add_argument('-b', action='store', dest='target_bssid',
            metavar='[bssid]', type=str,
            help=self._verbose('Target BSSID'))

        glob.add_argument('-e', action='store', dest='target_essid',
            metavar='[essid]', type=str,
            help=self._verbose('Target ESSID'))

        glob.add_argument('--clients-only', action='store_true',
            dest='clients_only',
            help=Color.s('Only show targets with clients'))

    def _add_advanced_args(self, adv):
        '''Advanced optimization and PIN-related arguments'''
        
        adv.add_argument('--fast-capture', action='store_true',
            dest='fast_capture',
            help=Color.s('Enable {G}fast handshake capture{W} with optimizations'))
        adv.add_argument('-fc', help=argparse.SUPPRESS, action='store_true',
            dest='fast_capture')

        adv.add_argument('--pin-mode', action='store_true', dest='pin_mode',
            help=Color.s('Enable {G}WPS PIN attack mode{W} with retry logic'))
        adv.add_argument('-pm', help=argparse.SUPPRESS, action='store_true',
            dest='pin_mode')

        adv.add_argument('--pin-timeout', action='store', dest='pin_timeout',
            metavar='[seconds]', type=int,
            help=Color.s('PIN attack timeout (default: {G}120s{W})'))

        adv.add_argument('--pin-retries', action='store', dest='pin_retries',
            metavar='[num]', type=int,
            help=Color.s('PIN retry attempts (default: {G}5{W})'))

        adv.add_argument('--adaptive-timeout', action='store_true',
            dest='adaptive_timeout',
            help=Color.s('Use {G}adaptive timeout{W} for better results'))

        adv.add_argument('--parallel-attacks', action='store', dest='parallel_attacks',
            metavar='[num]', type=int, default=2,
            help=Color.s('Number of parallel attacks (default: {G}2{W})'))

        adv.add_argument('--enable-cache', action='store_true', dest='cache_results',
            help=Color.s('Cache scan results for faster re-scans'))

    def _add_wep_args(self, wep):
        wep.add_argument('--wep', action='store_true', dest='wep_filter',
            help=Color.s('Show only {C}WEP-encrypted networks{W}'))

        wep.add_argument('--pps', action='store', dest='wep_pps',
            metavar='[pps]', type=int,
            help=self._verbose('Packets-per-second'))

        wep.add_argument('--wept', action='store', dest='wep_timeout',
            metavar='[seconds]', type=int,
            help=self._verbose('WEP attack timeout'))

    def _add_wpa_args(self, wpa):
        wpa.add_argument('--wpa', action='store_true', dest='wpa_filter',
            help=Color.s('Show only {C}WPA-encrypted networks{W}'))

        wpa.add_argument('--dict', action='store', dest='wordlist',
            metavar='[file]', type=str,
            help=Color.s('Wordlist for cracking'))

        wpa.add_argument('--wpat', action='store', dest='wpa_attack_timeout',
            metavar='[seconds]', type=int,
            help=self._verbose('WPA attack timeout'))

    def _add_wps_args(self, wps):
        wps.add_argument('--wps', action='store_true', dest='wps_filter',
            help=Color.s('Show only {C}WPS-enabled networks{W}'))

        wps.add_argument('--no-wps', action='store_true', dest='no_wps',
            help=self._verbose('Never use WPS attacks'))

        wps.add_argument('--wps-only', action='store_true', dest='wps_only',
            help=Color.s('{O}Only{W} use {C}WPS{W} attacks'))

        wps.add_argument('--pixie', action='store_true', dest='wps_pixie',
            help=self._verbose('Only WPS Pixie-Dust'))

        wps.add_argument('--wps-time', action='store', dest='wps_pixie_timeout',
            metavar='[sec]', type=int,
            help=self._verbose('WPS timeout'))

    def _add_pmkid_args(self, pmkid):
        pmkid.add_argument('--pmkid', action='store_true', dest='use_pmkid_only',
            help=Color.s('{O}Only{W} use {C}PMKID{W} attack'))

    def _add_command_args(self, commands):
        commands.add_argument('--cracked', action='store_true', dest='cracked',
            help=Color.s('Print cracked access points'))

        commands.add_argument('--check', action='store', metavar='file',
            nargs='?', const='<all>', dest='check_handshake',
            help=Color.s('Check handshakes'))

        commands.add_argument('--crack', action='store_true',
            dest='crack_handshake',
            help=Color.s('Crack captured handshake'))

if __name__ == '__main__':
    from .util.color import Color
    from .config import Configuration
    Configuration.initialize(False)
    a = Arguments(Configuration)
    args = a.args
    for (key, value) in sorted(args.__dict__.items()):
        Color.pl('{C}%s: {G}%s{W}' % (key.ljust(21), value))
