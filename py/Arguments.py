#!/usr/bin/python

import argparse
from Color import Color

class Arguments(object):
    ''' Holds arguments used by the Wifite '''
    def __init__(self, Configuration):
        self.args = self.get_arguments(Configuration)

    def get_arguments(self, Configuration):
        ''' Returns parser.args() containing all program arguments '''

        parser = argparse.ArgumentParser(usage=argparse.SUPPRESS,
                formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=80, width=130))

        # Global variables
        glob = parser.add_argument_group('SETTINGS')
        glob.add_argument('-i',
            action='store',
            dest='interface',
            metavar='[interface]',
            type=str,
            help=Color.s('Wireless interface to use (default: {G}ask{W})'))
        glob.add_argument('-c',
            action='store',
            dest='channel',
            metavar='[channel]',
            type=int,
            help=Color.s('Wireless channel to scan (default: {G}all channels{W})'))
        glob.add_argument('-5',
            '--5ghz',
            action='store_true',
            dest='five_ghz',
            help=Color.s('Include 5Ghz channels (default: {G}off{W})'))
        glob.add_argument('-b',
            action='store',
            dest='target_bssid',
            metavar='[bssid]',
            type=str,
            help=Color.s('BSSID (e.g. {GR}AA:BB:CC:DD:EE:FF{W}) of access point to attack'))
        glob.add_argument('-e',
            action='store',
            dest='target_essid',
            metavar='[essid]',
            type=str,
            help=Color.s('ESSID (name) of access point to attack'))
        glob.add_argument('-v',
            '--verbose',
            action='count',
            default=0,
            dest='verbose',
            help=Color.s('Verbose mode, prints more lines (default: {G}quiet{W})'))

        # WEP
        wep = parser.add_argument_group('WEP-RELATED')
        wep.add_argument('--wep',
            action='store_true',
            dest='wep_filter',
            help=Color.s('Filter to display WEP-encrypted networks (default: {G}off{W})'))
        wep.add_argument('--require-fakeauth',
            action='store_true',
            dest='require_fakeauth',
            help=Color.s('Fails attacks if fake-auth fails (default: {G}off{W})'))
        wep.add_argument('-pps',
            action='store',
            dest='wep_pps',
            metavar='[pps]',
            type=int,
            help=Color.s('Packets Per Second to replay (default: {G}%d pps{W})')
                % Configuration.wep_pps)
        wep.add_argument('-wept',
            action='store',
            dest='wep_timeout',
            metavar='[seconds]',
            type=int,
            help=Color.s('Seconds to wait before failing (default: {G}%d sec{W})')
                % Configuration.wep_timeout)
        wep.add_argument('-wepc',
            action='store',
            dest='wep_crack_at_ivs',
            metavar='[ivs]',
            type=int,
            help=Color.s('Start cracking at this many IVs (default: {G}%d ivs{W})')
                % Configuration.wep_crack_at_ivs)
        wep.add_argument('-weprs',
            action='store',
            dest='wep_restart_stale_ivs',
            metavar='[seconds]',
            type=int,
            help=Color.s('Restart aireplay if no new IVs appear (default: {G}%d sec{W})')
                % Configuration.wep_restart_stale_ivs)
        wep.add_argument('-weprc',
            action='store',
            dest='wep_restart_aircrack',
            metavar='[seconds]',
            type=int,
            help=Color.s('Restart aircrack after this delay (default: {G}%d sec{W})')
                % Configuration.wep_restart_aircrack)
        wep.add_argument('-arpreplay',
            action='store_true',
            dest='wep_attack_replay',
            help=Color.s('Use ARP-replay WEP attack (default: {G}on{W})'))
        wep.add_argument('-fragment',
            action='store_true',
            dest='wep_attack_fragment',
            help=Color.s('Use fragmentation WEP attack (default: {G}on{W})'))
        wep.add_argument('-chopchop',
            action='store_true',
            dest='wep_attack_chopchop',
            help=Color.s('Use chop-chop WEP attack (default: {G}on{W})'))
        wep.add_argument('-caffelatte',
            action='store_true',
            dest='wep_attack_caffe',
            help=Color.s('Use caffe-latte WEP attack (default: {G}on{W})'))
        wep.add_argument('-p0841',
            action='store_true',
            dest='wep_attack_p0841',
            help=Color.s('Use p0841 WEP attack (default: {G}on{W})'))
        wep.add_argument('-hirte',
            action='store_true',
            dest='wep_attack_hirte',
            help=Color.s('Use ARP-replay WEP attack (default: {G}on{W})'))

        # WPA
        wpa = parser.add_argument_group('WPA-RELATED')
        wpa.add_argument('--wpa',
            action='store_true',
            dest='wpa_filter',
            help=Color.s('Filter to display WPA-encrypted networks (includes WPS)'))
        wpa.add_argument('-wpadt',
            action='store',
            dest='wpa_deauth_timeout',
            metavar='[seconds]',
            type=int,
            help=Color.s('Time to wait before failing a Deauth (default: {G}%d sec{W})')
                % Configuration.wpa_deauth_timeout)
        wpa.add_argument('-wpat',
            action='store',
            dest='wpa_attack_timeout',
            metavar='[seconds]',
            type=int,
            help=Color.s('Time to wait before failing WPA attack (default: {G}%d sec{W})')
                % Configuration.wpa_attack_timeout)
        wpa.add_argument('-hs',
            action='store',
            dest='wpa_handshake_dir',
            metavar='[dir]',
            type=str,
            help=Color.s('Directory to store handshake files (default: {G}%s{W})')
                % Configuration.wpa_handshake_dir)
        wpa.add_argument('--dict',
            action='store',
            dest='wordlist',
            metavar='[file]',
            type=str,
            help=Color.s('File containing passwords for cracking (default: {G}%s{W})')
                % Configuration.wordlist)

        # WPS
        wps = parser.add_argument_group('WPS-RELATED')
        wps.add_argument('--wps',
            action='store_true',
            dest='wps_filter',
            help=Color.s('Filter to display WPS-enabled networks'))
        wps.add_argument('--reaver',
            action='store_true',
            dest='reaver_only',
            help=Color.s('ONLY use Reaver on WPS networks (default: {G}off{W})'))
        wps.add_argument('--no-reaver',
            action='store_true',
            dest='no_reaver',
            help=Color.s('Do NOT use Reaver on WPS networks (default: {G}off{W})'))
        wps.add_argument('--pixie',
            action='store_true',
            dest='pixie_only',
            help=Color.s('Only use the WPS Pixie-Dust attack (default: {G}off{W})'))
        wps.add_argument('--pixiet',
            action='store',
            dest='wps_pixie_timeout',
            metavar='[seconds]',
            type=int,
            help=Color.s('Time to wait before stopping PixieDust (default: {G}%d sec{W})')
                % Configuration.wps_pixie_timeout)
        wps.add_argument('-wpst',
            action='store',
            dest='wps_pin_timeout',
            metavar='[seconds]',
            type=int,
            help=Color.s('Time to wait before stopping PIN attack (default: {G}%d sec{W})')
                % Configuration.wps_pin_timeout)
        wps.add_argument('-wpsmr',
            action='store',
            dest='wps_max_retries',
            metavar='[retries]',
            type=int,
            help=Color.s('Maximum number of Retries before stopping (default: {G}%d{W})')
                % Configuration.wps_max_retries)
        wps.add_argument('-wpsmf',
            action='store',
            dest='wps_fail_threshold',
            metavar='[fails]',
            type=int,
            help=Color.s('Maximum number of Failures before stopping (default: {G}%d{W})')
                % Configuration.wps_fail_threshold)
        wps.add_argument('-wpsmt',
            action='store',
            dest='wps_timeout_threshold',
            metavar='[timeouts]',
            type=int,
            help=Color.s('Maximum number of Timeouts before stopping (default: {G}%d{W})')
                % Configuration.wps_timeout_threshold)
        wps.add_argument('--ignore-ratelimit',
            action='store_false',
            dest='wps_ignore_rate_limit',
            help=Color.s('Continues attack if WPS is rate-limited (default: {G}off{W})'))

        # Commands
        commands = parser.add_argument_group('COMMANDS')
        commands.add_argument('--cracked',
            action='store_true',
            dest='cracked',
            help=Color.s('Display previously-cracked access points'))
        commands.add_argument('--check-hs',
            action='store',
            metavar='[file]',
            dest='check_handshake',
            help=Color.s('Check a .cap file for WPA handshakes'))
        commands.add_argument('--crack-wpa',
            action='store',
            type=str,
            dest='crack_wpa',
            metavar='[file]',
            help=Color.s('Crack a .cap file containing a WPA handshake'))
        commands.add_argument('--crack-wep',
            action='store',
            type=str,
            dest='crack_wep',
            metavar='[file]',
            help=Color.s('Crack a .cap file containing WEP IVS'))
        commands.add_argument('--update',
            action='store_true',
            dest='update',
            help=Color.s('Update to latest version of Wifite (on github)'))
        
        return parser.parse_args()

if __name__ == '__main__':
    from Color import Color
    from Configuration import Configuration
    Configuration.initialize(False)
    a = Arguments(Configuration)
    args = a.args
    for (key,value) in sorted(args.__dict__.iteritems()):
        Color.pl('{C}%s: {G}%s{W}' % (key.ljust(21),value))

