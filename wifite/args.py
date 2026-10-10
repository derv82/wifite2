#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .util.color import Color

import argparse
import sys


class Arguments:
    """ Holds arguments used by the Wifite """

    def __init__(self, configuration):
        # Hack: Check for -v before parsing args;
        # so we know which commands to display.
        self.verbose = '-v' in sys.argv or '-hv' in sys.argv or '-vh' in sys.argv
        # Activate Kalidroid MiniTerminal output mode as early as possible (before
        # any option-echo prints) so the whole run streams scrollback-friendly
        # output to the Kalidroid app's MiniTerminal.
        if '--kalidroid' in sys.argv:
            Color.kalidroid = True
        self.config = configuration
        self.args = self.get_arguments()

    def _verbose(self, msg):
        return Color.s(msg) if self.verbose else argparse.SUPPRESS

    def _get_eviltwin_examples(self):
        """Returns Evil Twin attack examples and legal warnings for verbose help."""
        return Color.s('''
{C}═══════════════════════════════════════════════════════════════════════════════{W}
{C}                          EVIL TWIN ATTACK OVERVIEW                             {W}
{C}═══════════════════════════════════════════════════════════════════════════════{W}

{G}What is an Evil Twin Attack?{W}

An Evil Twin attack creates a rogue wireless access point that mimics a legitimate
network. When clients connect to the rogue AP, they are presented with a captive
portal that requests the network password. The attack validates submitted credentials
against the real AP and captures valid passwords.

{G}How it Works:{W}

  1. {C}Rogue AP Creation{W}: Creates a fake AP with the same SSID as the target
  2. {C}Deauthentication{W}: Forces clients to disconnect from the legitimate AP
  3. {C}Client Connection{W}: Clients automatically reconnect to the rogue AP
  4. {C}Captive Portal{W}: Displays a login page requesting the WiFi password
  5. {C}Credential Validation{W}: Tests submitted passwords against the real AP
  6. {C}Success{W}: Captures and saves valid credentials

{C}═══════════════════════════════════════════════════════════════════════════════{W}
{C}                          EVIL TWIN USAGE EXAMPLES                              {W}
{C}═══════════════════════════════════════════════════════════════════════════════{W}

  {O}Basic Evil Twin attack on all targets{W}
  {C}wifite --eviltwin{W}

  {O}Attack specific target by BSSID{W}
  {C}wifite --eviltwin -b AA:BB:CC:DD:EE:FF{W}

  {O}Attack specific target by ESSID{W}
  {C}wifite --eviltwin -e "NetworkName"{W}

  {O}Use custom captive portal template{W}
  {C}wifite --eviltwin --eviltwin-template tplink{W}

  {O}Specify interfaces for AP and deauth{W}
  {C}wifite --eviltwin --eviltwin-fakeap-iface wlan1 --eviltwin-deauth-iface wlan0mon{W}

  {O}Adjust deauthentication interval{W}
  {C}wifite --eviltwin --eviltwin-deauth-interval 10{W}

  {O}Use custom portal port{W}
  {C}wifite --eviltwin --eviltwin-port 8080{W}

  {O}Skip credential validation (testing only){W}
  {C}wifite --eviltwin --eviltwin-no-validate{W}

{C}═══════════════════════════════════════════════════════════════════════════════{W}
{C}                          REQUIREMENTS AND DEPENDENCIES                         {W}
{C}═══════════════════════════════════════════════════════════════════════════════{W}

  {G}Required Tools:{W}
    {C}hostapd{W} (v2.9+) - Creates software access point
    {C}dnsmasq{W} (v2.80+) - DHCP and DNS server
    {C}wpa_supplicant{W} (v2.9+) - Validates credentials
    {C}iptables{W} - Traffic redirection (usually pre-installed)

  {G}Hardware Requirements:{W}
    • Two wireless interfaces (one for AP, one for deauth)
    • OR one interface that supports AP mode and monitor mode simultaneously
    • Interface must support AP mode (check with: {C}iw list{W})

  {G}Recommended Adapters:{W}
    • Alfa AWUS036ACH (supports AP mode)
    • TP-Link TL-WN722N v1 (supports AP mode)
    • Panda PAU09 (supports AP mode)

{C}═══════════════════════════════════════════════════════════════════════════════{W}
{C}                          CAPTIVE PORTAL TEMPLATES                              {W}
{C}═══════════════════════════════════════════════════════════════════════════════{W}

  {G}Available Templates:{W}
    {C}generic{W}  - Generic router login page (default)
    {C}tplink{W}   - TP-Link router style
    {C}netgear{W}  - Netgear router style
    {C}linksys{W}  - Linksys router style

  {G}Template Selection:{W}
    The tool can auto-detect the router manufacturer from the BSSID and select
    an appropriate template. You can override this with --eviltwin-template.

{C}═══════════════════════════════════════════════════════════════════════════════{W}
{C}                          TROUBLESHOOTING                                       {W}
{C}═══════════════════════════════════════════════════════════════════════════════{W}

  {R}Problem:{W} Interface doesn't support AP mode
  {G}Solution:{W} Check capabilities with {C}iw list | grep -A 10 "Supported interface modes"{W}
             Use a different adapter that supports AP mode

  {R}Problem:{W} Port 80 already in use
  {G}Solution:{W} Stop conflicting service: {C}systemctl stop apache2{W}
             Or use alternate port: {C}--eviltwin-port 8080{W}

  {R}Problem:{W} Hostapd fails to start
  {G}Solution:{W} Kill conflicting processes: {C}killall NetworkManager wpa_supplicant{W}
             Check interface is not in use: {C}airmon-ng check kill{W}

  {R}Problem:{W} No clients connecting
  {G}Solution:{W} Verify deauth is working (check logs)
             Move closer to target AP
             Ensure rogue AP is on same channel as target

  {R}Problem:{W} Credential validation fails
  {G}Solution:{W} Ensure legitimate AP is still reachable
             Check wpa_supplicant is installed and working
             Review validation logs for errors

{C}═══════════════════════════════════════════════════════════════════════════════{W}

  For more information: {C}https://github.com/kimocoder/wifite2{W}

''')

    def _get_wpa3_examples(self):
        """Returns WPA3 attack examples and strategy explanations for verbose help."""
        return Color.s('''
{C}═══════════════════════════════════════════════════════════════════════════════{W}
{C}                          WPA3 ATTACK STRATEGIES                                {W}
{C}═══════════════════════════════════════════════════════════════════════════════{W}

{G}1. Transition Mode Downgrade{W} (Primary - 80-90% success rate)
   Detects WPA3-Transition networks (support both WPA2 and WPA3)
   Forces clients to connect using WPA2 instead of WPA3
   Captures standard WPA2 handshake for cracking
   Example: {C}wifite --wpa3{W}

{G}2. Dragonblood Exploitation{W} (40-50% success on vulnerable APs)
   Exploits CVE-2019-13377 and related WPA3 vulnerabilities
   Identifies weak SAE group configurations
   Performs timing-based password partitioning
   Example: {C}wifite --check-dragonblood{W} (scan only)

{G}3. SAE Handshake Capture{W} (Standard - 60-70% success rate)
   Captures WPA3-SAE authentication handshakes
   Converts to hashcat format (mode 22000)
   Performs offline dictionary attack
   Example: {C}wifite --wpa3 --force-sae{W}

{G}4. Passive Capture{W} (PMF Required - 50-60% success rate)
   Used when Protected Management Frames (PMF) are required
   Waits for natural client reconnections (no deauth)
   Captures SAE handshake passively
   Example: {C}wifite --wpa3 --nodeauths{W}

{C}═══════════════════════════════════════════════════════════════════════════════{W}
{C}                            WPA3 USAGE EXAMPLES                                 {W}
{C}═══════════════════════════════════════════════════════════════════════════════{W}

  {O}Scan and attack all WPA3 networks (auto-strategy selection){W}
  {C}wifite --wpa3{W}

  {O}Attack only WPA3 networks, skip WPA2-only targets{W}
  {C}wifite --wpa3-only{W}

  {O}Force SAE capture, disable downgrade attacks{W}
  {C}wifite --wpa3 --no-downgrade{W}

  {O}Scan for Dragonblood vulnerabilities{W}
  {C}wifite --check-dragonblood{W}

  {O}Scan for OWE transition mode vulnerabilities{W}
  {C}wifite --owe{W}

  {O}Passive WPA3 attack (for PMF-required networks){W}
  {C}wifite --wpa3 --nodeauths{W}

{C}═══════════════════════════════════════════════════════════════════════════════{W}
{C}                          VULNERABILITY SCANNING                                {W}
{C}═══════════════════════════════════════════════════════════════════════════════{W}

  {G}Dragonblood Detection:{W}
    Identifies weak SAE groups (22, 23, 24)
    Detects CVE-2019-13377 vulnerabilities
    Command: {C}wifite --check-dragonblood{W}

  {G}OWE Transition Detection:{W}
    Finds OWE networks with Open fallback
    Identifies downgrade vulnerabilities
    Command: {C}wifite --owe{W}

{C}═══════════════════════════════════════════════════════════════════════════════{W}
{C}                            WPA3 REQUIREMENTS                                   {W}
{C}═══════════════════════════════════════════════════════════════════════════════{W}

  Required tools for WPA3 attacks:
    {G}hcxdumptool{W} (v6.0.0+) - SAE frame capture
    {G}hcxpcapngtool{W} (v6.0.0+) - SAE hash extraction
    {G}hashcat{W} (v6.0.0+) - WPA3 cracking (mode 22000)
    {G}tshark{W} (optional) - SAE frame analysis

{C}═══════════════════════════════════════════════════════════════════════════════{W}

  For more information: {C}https://github.com/kimocoder/wifite2{W}

''')

    def get_arguments(self):
        """ Returns parser.args() containing all program arguments """

        # Build epilog with both Evil Twin and WPA3 examples if verbose
        epilog = None
        if self.verbose:
            epilog = self._get_eviltwin_examples() + '\n' + self._get_wpa3_examples()

        parser = argparse.ArgumentParser(usage=argparse.SUPPRESS,
                                         formatter_class=lambda prog:
                                         argparse.RawDescriptionHelpFormatter(prog, max_help_position=80, width=130),
                                         epilog=epilog)

        self._add_global_args(parser.add_argument_group(Color.s('{C}SETTINGS{W}')))
        self._add_wep_args(parser.add_argument_group(Color.s('{C}WEP{W}')))
        self._add_wpa_args(parser.add_argument_group(Color.s('{C}WPA{W}')))
        self._add_wps_args(parser.add_argument_group(Color.s('{C}WPS{W}')))
        self._add_pmkid_args(parser.add_argument_group(Color.s('{C}PMKID{W}')))
        self._add_eviltwin_args(parser.add_argument_group(Color.s('{C}EVIL TWIN{W}')))
        self._add_attack_monitor_args(parser.add_argument_group(Color.s('{C}ATTACK MONITORING{W}')))
        self._add_wpasec_args(parser.add_argument_group(Color.s('{C}WPA-SEC UPLOAD{W}')))
        self._add_command_args(parser.add_argument_group(Color.s('{C}COMMANDS{W}')))

        return parser.parse_args()

    def _add_global_args(self, glob):
        glob.add_argument('-v',
                          '--verbose',
                          action='count',
                          default=0,
                          dest='verbose',
                          help=Color.s(
                              'Shows more options ({C}-h -v{W}). Prints commands and outputs. (default: {G}quiet{W})'))

        glob.add_argument('--debug',
                          action='store_true',
                          default=False,
                          dest='debug',
                          help=self._verbose(
                              'Shorthand for {C}-vvv{W}: max verbosity with file logging to {C}~/.wifite/wifite.log{W}'))

        glob.add_argument('--log-file',
                          action='store',
                          dest='log_file',
                          metavar='[path]',
                          type=str,
                          default=None,
                          help=self._verbose(
                              'Write debug log to {C}[path]{W} (implies {C}-vv{W} minimum verbosity)'))

        glob.add_argument('--kalidroid',
                          action='store_true',
                          default=False,
                          dest='kalidroid',
                          help=self._verbose(
                              'Emit {C}MiniTerminal{W}-friendly output for the {C}Kalidroid{W} app: '
                              'flatten carriage-return progress redraws into discrete lines and '
                              'skip clear-line escapes (default: {G}off{W})'))

        glob.add_argument('-i',
                          action='store',
                          dest='interface',
                          metavar='[interface]',
                          type=str,
                          help=Color.s('Wireless interface to use, e.g. {C}wlan0mon{W} (default: {G}ask{W})'))

        glob.add_argument('-c',
                          action='store',
                          dest='channel',
                          metavar='[channel]',
                          help=Color.s('Wireless channel to scan e.g. {C}1,3-6{W} (default: {G}all 2Ghz channels{W})'))
        glob.add_argument('--channel', help=argparse.SUPPRESS, action='store', dest='channel')

        glob.add_argument('-ab',
                          '--allbands',
                          action='store_true',
                          dest='all_bands',
                          help=self._verbose('Include both 2.4Ghz and 5Ghz bands (default: {G}off{W})'))

        glob.add_argument('-2',
                          '--2ghz',
                          action='store_true',
                          dest='two_ghz',
                          help=self._verbose('Include 2.4Ghz channels (default: {G}off{W})'))

        glob.add_argument('-5',
                          '--5ghz',
                          action='store_true',
                          dest='five_ghz',
                          help=self._verbose('Include 5Ghz channels (default: {G}off{W})'))

        glob.add_argument('-inf',
                          '--infinite',
                          action='store_true',
                          dest='infinite_mode',
                          help=Color.s(
                              'Enable infinite attack mode. Modify scanning time with {C}-p{W} (default: {G}off{W})'))

        glob.add_argument('-mac',
                          '--random-mac',
                          action='store_true',
                          dest='random_mac',
                          help=Color.s('Randomize wireless card MAC address completely (better privacy) (default: {G}off{W})'))

        glob.add_argument('--random-mac-vendor',
                          action='store_true',
                          dest='random_mac_vendor',
                          help=Color.s('Randomize wireless card MAC address but keep vendor bytes (better compatibility) (default: {G}off{W})'))

        glob.add_argument('-p',
                          action='store',
                          dest='scan_time',
                          nargs='?',
                          const=10,
                          metavar='scan_time',
                          type=int,
                          help=Color.s('{G}Pillage{W}: Attack all targets after {C}scan_time{W} (seconds)'))
        glob.add_argument('--pillage', help=argparse.SUPPRESS, action='store',
                          dest='scan_time', nargs='?', const=10, type=int)

        glob.add_argument('--kill',
                          action='store_true',
                          dest='kill_conflicting_processes',
                          help=Color.s('Kill processes that conflict with Airmon/Airodump (default: {G}off{W})'))

        glob.add_argument('-pow',
                          '--power',
                          action='store',
                          dest='min_power',
                          metavar='[min_power]',
                          type=int,
                          help=Color.s('Attacks any targets with at least {C}min_power{W} signal strength'))

        glob.add_argument('--skip-crack',
                          action='store_true',
                          dest='skip_crack',
                          help=Color.s('Skip cracking captured handshakes/pmkid (default: {G}off{W})'))

        glob.add_argument('-first',
                          '--first',
                          action='store',
                          dest='attack_max',
                          metavar='[attack_max]',
                          type=int,
                          help=Color.s('Attacks the first {C}attack_max{W} targets'))

        glob.add_argument('-b',
                          action='store',
                          dest='target_bssid',
                          metavar='[bssid]',
                          type=str,
                          help=self._verbose('BSSID (e.g. {GR}AA:BB:CC:DD:EE:FF{W}) of access point to attack'))
        glob.add_argument('--bssid', help=argparse.SUPPRESS, action='store', dest='target_bssid', type=str)

        glob.add_argument('-e',
                          action='store',
                          dest='target_essid',
                          metavar='[essid]',
                          type=str,
                          help=self._verbose('ESSID (e.g. {GR}NETGEAR07{W}) of access point to attack'))
        glob.add_argument('--essid', help=argparse.SUPPRESS, action='store', dest='target_essid', type=str)

        glob.add_argument('-E',
                          action='append',
                          dest='ignore_essids',
                          metavar='[text]',
                          type=str,
                          default=None,
                          help=self._verbose(
                              'Hides targets with ESSIDs that match the given text. Can be used more than once.'))
        glob.add_argument('--ignore-essid', help=argparse.SUPPRESS, action='append', dest='ignore_essids', type=str)
        glob.add_argument('--ignore-essids-file',
                          action='store',
                          dest='ignore_essids_file',
                          metavar='[file]',
                          type=str,
                          default=None,
                          help=self._verbose(
                              'Hides targets whose ESSID appears in {C}[file]{W} (one ESSID per line).'))

        glob.add_argument('-ic',
                          '--ignore-cracked',
                          action='store_true',
                          dest='ignore_cracked',
                          help=Color.s('Hides previously-cracked targets. (default: {G}off{W})'))

        glob.add_argument('--ignore-captured',
                          action='store_true',
                          dest='ignore_captured',
                          help=Color.s('Hides targets with existing captured handshakes/pmkid. (default: {G}off{W})'))

        glob.add_argument('--clients-only',
                          action='store_true',
                          dest='clients_only',
                          help=Color.s('Only show targets that have associated clients (default: {G}off{W})'))

        glob.add_argument('--showb',
                          action='store_true',
                          dest='show_bssids',
                          help=self._verbose('Show BSSIDs of targets while scanning'))

        glob.add_argument('--showm',
                          action='store_true',
                          dest='show_manufacturers',
                          help=self._verbose('Show manufacturers of targets while scanning'))

        glob.add_argument('--detect-honeypots',
                          action='store_true',
                          dest='detect_honeypots',
                          help=Color.s('Detect potential honeypot/rogue APs via beacon anomalies (default: {G}off{W})'))

        glob.add_argument('--nodeauths',
                          action='store_true',
                          dest='no_deauth',
                          help=Color.s('Passive mode: Never deauthenticates clients (default: {G}deauth targets{W})'))
        glob.add_argument('--no-deauths', action='store_true', dest='no_deauth', help=argparse.SUPPRESS)
        glob.add_argument('-nd', action='store_true', dest='no_deauth', help=argparse.SUPPRESS)

        glob.add_argument('--num-deauths',
                          action='store',
                          type=int,
                          dest='num_deauths',
                          metavar='[num]',
                          default=None,
                          help=self._verbose(
                              'Number of deauth packets to send (default: {G}%d{W})' % self.config.num_deauths))

        glob.add_argument('--daemon',
                          action='store_true',
                          dest='daemon',
                          help=Color.s('Puts device back in managed mode after quitting (default: {G}off{W})'))

        glob.add_argument('--tui',
                          action='store_true',
                          dest='use_tui',
                          help=Color.s('Use interactive TUI mode (default: {G}auto-detect{W})'))

        glob.add_argument('--no-tui',
                          action='store_true',
                          dest='no_tui',
                          help=Color.s('Use classic text mode, disable TUI (default: {G}auto-detect{W})'))

        # Dual interface support
        glob.add_argument('--dual-interface',
                          action='store_true',
                          dest='dual_interface',
                          help=Color.s('Enable dual interface mode for simultaneous AP and deauth operations. '
                                      'Automatically assigns two interfaces when available for improved attack '
                                      'performance. Eliminates mode switching in Evil Twin attacks. (default: {G}auto{W})'))

        glob.add_argument('--no-dual-interface',
                          action='store_true',
                          dest='no_dual_interface',
                          help=Color.s('Disable dual interface mode, force single interface operation. '
                                      'Uses traditional mode-switching approach even when multiple interfaces '
                                      'are available. (default: {G}off{W})'))

        glob.add_argument('--interface-primary',
                          action='store',
                          dest='interface_primary',
                          metavar='[interface]',
                          type=str,
                          help=self._verbose('Manually specify primary interface for AP mode or packet capture. '
                                            'Used as the main interface for hosting rogue AP (Evil Twin) or '
                                            'capturing handshakes (WPA). Requires interface to support required '
                                            'capabilities for the attack type.'))

        glob.add_argument('--interface-secondary',
                          action='store',
                          dest='interface_secondary',
                          metavar='[interface]',
                          type=str,
                          help=self._verbose('Manually specify secondary interface for deauthentication or monitoring. '
                                            'Used for sending deauth packets while primary interface maintains '
                                            'AP or capture operations. Enables parallel operations without mode switching.'))

        glob.add_argument('--hcxdump',
                          action='store_true',
                          dest='use_hcxdump',
                          help=Color.s('Use {C}hcxdumptool{W} for WPA handshake capture (single or dual interface). '
                                      'Creates .pcapng files with better compatibility for Hashcat. '
                                      'Provides PMF-aware capture and built-in deauth capabilities. '
                                      'Falls back to airodump-ng if hcxdumptool is unavailable. '
                                      'Requires hcxdumptool v6.2.0+ (default: {G}off{W})'))

    def _add_eviltwin_args(self, group):
        group.add_argument('--eviltwin',
                          action='store_true',
                          dest='use_eviltwin',
                          help=Color.s('Use the {C}Evil Twin{W} attack against all targets. '
                                      'Creates rogue AP to capture credentials. (default: {G}off{W})'))

        group.add_argument('--eviltwin-deauth-iface',
                          action='store',
                          dest='eviltwin_deauth_iface',
                          metavar='[interface]',
                          type=str,
                          help=self._verbose('Interface for deauthentication (default: {G}same as scan interface{W})'))

        group.add_argument('--eviltwin-fakeap-iface',
                          action='store',
                          dest='eviltwin_fakeap_iface',
                          metavar='[interface]',
                          type=str,
                          help=self._verbose('Interface for fake AP (default: {G}auto-detect{W})'))

        group.add_argument('--eviltwin-port',
                          action='store',
                          dest='eviltwin_port',
                          metavar='[port]',
                          type=int,
                          help=self._verbose('Port for captive portal (default: {G}80{W})'))

        group.add_argument('--eviltwin-deauth-interval',
                          action='store',
                          dest='eviltwin_deauth_interval',
                          metavar='[seconds]',
                          type=int,
                          help=self._verbose('Seconds between deauth bursts (default: {G}5{W})'))

        group.add_argument('--eviltwin-timeout',
                          action='store',
                          dest='eviltwin_timeout',
                          metavar='[seconds]',
                          type=int,
                          help=self._verbose('Give up after N seconds (default: {G}0{W} = run until success/interrupt)'))

        group.add_argument('--eviltwin-template',
                          action='store',
                          dest='eviltwin_template',
                          metavar='[template]',
                          type=str,
                          choices=['generic', 'tplink', 'netgear', 'linksys'],
                          help=self._verbose('Captive portal template: {C}generic{W}, {C}tplink{W}, {C}netgear{W}, {C}linksys{W} (default: {G}generic{W})'))

        group.add_argument('--eviltwin-channel',
                          action='store',
                          dest='eviltwin_channel',
                          metavar='[channel]',
                          type=int,
                          help=self._verbose('Override channel for rogue AP (default: {G}same as target{W})'))

        group.add_argument('--eviltwin-no-validate',
                          action='store_true',
                          dest='eviltwin_no_validate',
                          help=self._verbose('Skip credential validation (testing only) (default: {G}off{W})'))

    def _add_attack_monitor_args(self, monitor):
        """Add wireless attack monitoring command-line arguments."""
        monitor.add_argument('--monitor-attacks',
                            action='store_true',
                            dest='monitor_attacks',
                            help=Color.s('Monitor for wireless attacks (deauth/disassoc frames). '
                                        'Passively detects attack frames without interfering. '
                                        'Displays real-time statistics, network lists, and attacker profiles. '
                                        '{O}Requires tshark.{W} '
                                        '(default: {G}off{W})'))

        monitor.add_argument('--monitor-duration',
                            action='store',
                            dest='monitor_duration',
                            metavar='[seconds]',
                            type=int,
                            default=0,
                            help=self._verbose('Duration for attack monitoring in seconds. '
                                              'Set to 0 for infinite monitoring. '
                                              'Press Ctrl+C to stop early and view final statistics. '
                                              '{O}Example:{W} --monitor-duration 3600 (monitor for 1 hour) '
                                              '(default: {G}infinite{W})'))

        monitor.add_argument('--monitor-log',
                            action='store',
                            dest='monitor_log_file',
                            metavar='[file]',
                            type=str,
                            default=None,
                            help=self._verbose('Log file path for attack events. '
                                              'Logs include timestamp, attack type, source/dest MACs, BSSID, and ESSID. '
                                              'Format: ISO8601 timestamp | DEAUTH/DISASSOC | Attacker | Target | BSSID | ESSID | Channel. '
                                              '{O}Example:{W} --monitor-log /var/log/wifite/attacks.log '
                                              '(default: {G}attack_monitor_<timestamp>.log{W})'))

        monitor.add_argument('--monitor-channel',
                            action='store',
                            dest='monitor_channel',
                            metavar='[channel]',
                            type=int,
                            default=None,
                            help=self._verbose('Monitor specific channel for attacks. '
                                              'Focuses monitoring on a single channel for better performance. '
                                              'If not specified, uses current interface channel. '
                                              '{O}Example:{W} --monitor-channel 6 (monitor channel 6 only) '
                                              '(default: {G}current channel{W})'))

        monitor.add_argument('--monitor-hop',
                            action='store_true',
                            dest='monitor_hop',
                            help=self._verbose('Enable channel hopping during monitoring. '
                                              'Cycles through all 2.4GHz channels (1-11) to detect attacks across spectrum. '
                                              'Useful for comprehensive area monitoring but may miss some frames. '
                                              'Cannot be used with --monitor-channel. '
                                              '{O}Example:{W} --monitor-attacks --monitor-hop '
                                              '(default: {G}off{W})'))

    def _add_wep_args(self, wep):
        # WEP
        wep.add_argument('--wep',
                         action='store_true',
                         dest='wep_filter',
                         help=Color.s('Show only {C}WEP-encrypted networks{W}'))
        wep.add_argument('-wep', help=argparse.SUPPRESS, action='store_true', dest='wep_filter')

        wep.add_argument('--require-fakeauth',
                         action='store_true',
                         dest='require_fakeauth',
                         help=Color.s('Fails attacks if {C}fake-auth{W} fails (default: {G}off{W})'))
        wep.add_argument('--nofakeauth', help=argparse.SUPPRESS, action='store_true', dest='require_fakeauth')
        wep.add_argument('-nofakeauth', help=argparse.SUPPRESS, action='store_true', dest='require_fakeauth')

        wep.add_argument('--keep-ivs',
                         action='store_true',
                         dest='wep_keep_ivs',
                         default=False,
                         help=Color.s('Retain .IVS files and reuse when cracking (default: {G}off{W})'))

        wep.add_argument('--pps',
                         action='store',
                         dest='wep_pps',
                         metavar='[pps]',
                         type=int,
                         help=self._verbose(
                             'Packets-per-second to replay (default: {G}%d pps{W})' % self.config.wep_pps))
        wep.add_argument('-pps', help=argparse.SUPPRESS, action='store', dest='wep_pps', type=int)

        wep.add_argument('--wept',
                         action='store',
                         dest='wep_timeout',
                         metavar='[seconds]',
                         type=int,
                         help=self._verbose(
                             'Seconds to wait before failing (default: {G}%d sec{W})' % self.config.wep_timeout))
        wep.add_argument('-wept', help=argparse.SUPPRESS, action='store', dest='wep_timeout', type=int)

        wep.add_argument('--wepca',
                         action='store',
                         dest='wep_crack_at_ivs',
                         metavar='[ivs]',
                         type=int,
                         help=self._verbose('Start cracking at this many IVs (default: {G}%d ivs{W})'
                                            % self.config.wep_crack_at_ivs))
        wep.add_argument('-wepca', help=argparse.SUPPRESS, action='store', dest='wep_crack_at_ivs', type=int)

        wep.add_argument('--weprs',
                         action='store',
                         dest='wep_restart_stale_ivs',
                         metavar='[seconds]',
                         type=int,
                         help=self._verbose('Restart aireplay if no new IVs appear (default: {G}%d sec{W})'
                                            % self.config.wep_restart_stale_ivs))
        wep.add_argument('-weprs', help=argparse.SUPPRESS, action='store', dest='wep_restart_stale_ivs', type=int)

        wep.add_argument('--weprc',
                         action='store',
                         dest='wep_restart_aircrack',
                         metavar='[seconds]',
                         type=int,
                         help=self._verbose('Restart aircrack after this delay (default: {G}%d sec{W})'
                                            % self.config.wep_restart_aircrack))
        wep.add_argument('-weprc', help=argparse.SUPPRESS, action='store', dest='wep_restart_aircrack', type=int)

        wep.add_argument('--arpreplay',
                         action='store_true',
                         dest='wep_attack_replay',
                         help=self._verbose('Use {C}ARP-replay{W} WEP attack (default: {G}on{W})'))
        wep.add_argument('-arpreplay', help=argparse.SUPPRESS, action='store_true', dest='wep_attack_replay')

        wep.add_argument('--fragment',
                         action='store_true',
                         dest='wep_attack_fragment',
                         help=self._verbose('Use {C}fragmentation{W} WEP attack (default: {G}on{W})'))
        wep.add_argument('-fragment', help=argparse.SUPPRESS, action='store_true', dest='wep_attack_fragment')

        wep.add_argument('--chopchop',
                         action='store_true',
                         dest='wep_attack_chopchop',
                         help=self._verbose('Use {C}chop-chop{W} WEP attack (default: {G}on{W})'))
        wep.add_argument('-chopchop', help=argparse.SUPPRESS, action='store_true', dest='wep_attack_chopchop')

        wep.add_argument('--caffelatte',
                         action='store_true',
                         dest='wep_attack_caffe',
                         help=self._verbose('Use {C}caffe-latte{W} WEP attack (default: {G}on{W})'))
        wep.add_argument('-caffelatte', help=argparse.SUPPRESS, action='store_true', dest='wep_attack_caffelatte')

        wep.add_argument('--p0841',
                         action='store_true',
                         dest='wep_attack_p0841',
                         help=self._verbose('Use {C}p0841{W} WEP attack (default: {G}on{W})'))
        wep.add_argument('-p0841', help=argparse.SUPPRESS, action='store_true', dest='wep_attack_p0841')

        wep.add_argument('--hirte',
                         action='store_true',
                         dest='wep_attack_hirte',
                         help=self._verbose('Use {C}hirte{W} WEP attack (default: {G}on{W})'))
        wep.add_argument('-hirte', help=argparse.SUPPRESS, action='store_true', dest='wep_attack_hirte')

    def _add_wpa_args(self, wpa):
        wpa.add_argument('--wpa',
                         action='store_true',
                         dest='wpa_filter',
                         help=Color.s('Show only {C}WPA/WPA2-encrypted networks{W} (may include {C}WPS{W})'))
        wpa.add_argument('-wpa', help=argparse.SUPPRESS, action='store_true', dest='wpa_filter')

        # WPA3 filtering and targeting
        wpa.add_argument('--wpa3',
                         action='store_true',
                         dest='wpa3_filter',
                         help=Color.s('Show only {C}WPA3-encrypted networks{W} (SAE/OWE). '
                                      'Displays WPA3-only and transition mode networks.'))
        wpa.add_argument('-wpa3', help=argparse.SUPPRESS, action='store_true', dest='wpa3_filter')

        wpa.add_argument('--wpa3-only',
                         action='store_true',
                         dest='wpa3_only',
                         help=Color.s('Attack only {C}WPA3-SAE networks{W}, skip WPA2-only targets. '
                                      'Useful for focusing on WPA3 security testing. (default: {G}off{W})'))
        wpa.add_argument('-wpa3-only', help=argparse.SUPPRESS, action='store_true', dest='wpa3_only')

        # WPA3 attack strategy options
        wpa.add_argument('--no-downgrade',
                         action='store_true',
                         dest='wpa3_no_downgrade',
                         help=Color.s('Disable {C}WPA3 transition mode downgrade{W} attacks. '
                                      'Forces SAE handshake capture instead of attempting to downgrade '
                                      'to WPA2. Use when testing pure WPA3 security. (default: {G}off{W})'))
        wpa.add_argument('-no-downgrade', help=argparse.SUPPRESS, action='store_true', dest='wpa3_no_downgrade')

        wpa.add_argument('--force-sae',
                         action='store_true',
                         dest='wpa3_force_sae',
                         help=Color.s('Skip WPA2 attacks on {C}transition mode{W} networks, attack SAE directly. '
                                      'Captures WPA3-SAE handshakes even when WPA2 is available. (default: {G}off{W})'))
        wpa.add_argument('-force-sae', help=argparse.SUPPRESS, action='store_true', dest='wpa3_force_sae')

        # WPA3 vulnerability scanning
        wpa.add_argument('--check-dragonblood',
                         action='store_true',
                         dest='wpa3_check_dragonblood',
                         help=Color.s('Scan for {C}Dragonblood vulnerabilities{W} (CVE-2019-13377) only. '
                                      'Identifies vulnerable WPA3 implementations without performing attacks. '
                                      'Checks for weak SAE groups and timing attack susceptibility. (default: {G}off{W})'))
        wpa.add_argument('-check-dragonblood', help=argparse.SUPPRESS, action='store_true', dest='wpa3_check_dragonblood')

        # WPA3 timing configuration
        wpa.add_argument('--wpa3-timeout',
                         action='store',
                         dest='wpa3_attack_timeout',
                         metavar='[seconds]',
                         type=int,
                         help=self._verbose('Time to wait before failing WPA3-SAE attack. '
                                            'Applies to SAE handshake capture and downgrade attempts. '
                                            '(default: {G}%d sec{W})' % self.config.wpa_attack_timeout))
        wpa.add_argument('-wpa3-timeout', help=argparse.SUPPRESS, action='store', dest='wpa3_attack_timeout', type=int)

        # Dragonblood timing attack (CVE-2019-13377)
        wpa.add_argument('--dragonblood-timing',
                         action='store_true',
                         dest='dragonblood_timing',
                         help=Color.s('Enable {C}Dragonblood timing attack{W} (CVE-2019-13377) for APs with '
                                      'vulnerable MODP groups (22, 23, 24). Probes the AP to measure SAE '
                                      'response latency and partitions the password search space. '
                                      '(default: {G}off{W})'))
        wpa.add_argument('-dragonblood-timing', help=argparse.SUPPRESS, action='store_true', dest='dragonblood_timing')

        wpa.add_argument('--dragonblood-samples',
                         action='store',
                         dest='dragonblood_samples',
                         metavar='[count]',
                         type=int,
                         help=self._verbose('Number of timing samples per password candidate '
                                            'during Dragonblood attack. More samples improve accuracy '
                                            'but take longer. (default: {G}3{W})'))
        wpa.add_argument('-dragonblood-samples', help=argparse.SUPPRESS, action='store', dest='dragonblood_samples', type=int)

        wpa.add_argument('--dragonblood-max',
                         action='store',
                         dest='dragonblood_max_passwords',
                         metavar='[count]',
                         type=int,
                         help=self._verbose('Maximum number of passwords to probe during '
                                            'Dragonblood timing attack. (default: {G}50{W})'))
        wpa.add_argument('-dragonblood-max', help=argparse.SUPPRESS, action='store', dest='dragonblood_max_passwords', type=int)

        wpa.add_argument('--owe',
                         action='store_true',
                         dest='owe_filter',
                         help=Color.s('Show only {C}OWE-encrypted networks{W} (Enhanced Open)'))
        wpa.add_argument('-owe', help=argparse.SUPPRESS, action='store_true', dest='owe_filter')


        wpa.add_argument('--hs-dir',
                         action='store',
                         dest='wpa_handshake_dir',
                         metavar='[dir]',
                         type=str,
                         help=self._verbose(
                             'Directory to store handshake files (default: {G}%s{W})' % self.config.wpa_handshake_dir))
        wpa.add_argument('-hs-dir', help=argparse.SUPPRESS, action='store', dest='wpa_handshake_dir', type=str)

        wpa.add_argument('--new-hs',
                         action='store_true',
                         dest='ignore_old_handshakes',
                         help=Color.s('Captures new handshakes, ignores existing handshakes in {C}%s{W} '
                                      '(default: {G}off{W})' % self.config.wpa_handshake_dir))

        wpa.add_argument('--dict',
                         action='store',
                         dest='wordlist',
                         metavar='[file/directory]',
                         type=str,
                         help=Color.s(
                             'File or directory containing wordlists for cracking (default: {G}%s{W})') % self.config.wordlist)

        wpa.add_argument('--wpadt',
                         action='store',
                         dest='wpa_deauth_timeout',
                         metavar='[seconds]',
                         type=int,
                         help=self._verbose('Time to wait between sending Deauths (default: {G}%d sec{W})'
                                            % self.config.wpa_deauth_timeout))
        wpa.add_argument('-wpadt', help=argparse.SUPPRESS, action='store', dest='wpa_deauth_timeout', type=int)

        wpa.add_argument('--wpat',
                         action='store',
                         dest='wpa_attack_timeout',
                         metavar='[seconds]',
                         type=int,
                         help=self._verbose('Time to wait before failing WPA attack (default: {G}%d sec{W})'
                                            % self.config.wpa_attack_timeout))
        wpa.add_argument('-wpat', help=argparse.SUPPRESS, action='store', dest='wpa_attack_timeout', type=int)

        # Handshake stripping is implemented (see Handshake.strip()), but the public
        # --strip flag remains hidden because stripped captures may break compatibility
        # with aircrack-ng and other downstream tools (Handshake.strip() warns of this).
        # Keep only the hidden compatibility alias (-strip) until the behavior is
        # validated across all supported cracking tools.
        '''
        wpa.add_argument('--strip',
            action='store_true',
            dest='wpa_strip_handshake',
            default=False,
            help=Color.s('Strip unnecessary packets from handshake capture using tshark'))
        '''
        wpa.add_argument('-strip', help=argparse.SUPPRESS, action='store_true', dest='wpa_strip_handshake')

    def _add_wps_args(self, wps):
        wps.add_argument('--wps',
                         action='store_true',
                         dest='wps_filter',
                         help=Color.s('Show only {C}WPS-enabled networks{W}'))
        wps.add_argument('-wps', help=argparse.SUPPRESS, action='store_true', dest='wps_filter')

        wps.add_argument('--no-wps',
                         action='store_true',
                         dest='no_wps',
                         help=self._verbose('{O}Never{W} use {O}WPS PIN{W} & {O}Pixie-Dust{W} '
                                            'attacks on targets (default: {G}off{W})'))

        wps.add_argument('--wps-only',
                         action='store_true',
                         dest='wps_only',
                         help=Color.s('{O}Only{W} use {C}WPS PIN{W} & {C}Pixie-Dust{W} attacks (default: {G}off{W})'))

        wps.add_argument('--pixie', action='store_true', dest='wps_pixie',
                         help=self._verbose('{O}Only{W} use {C}WPS Pixie-Dust{W} attack (do not use {O}PIN attack{W})'))

        wps.add_argument('--no-pixie', action='store_true', dest='wps_no_pixie',
                         help=self._verbose('{O}Never{W} use {O}WPS Pixie-Dust{W} attack (use {G}PIN attack{W})'))

        wps.add_argument('--no-nullpin', action='store_true', dest='wps_no_nullpin',
                         help=self._verbose('{O}Never{W} use {O}NULL PIN{W} attack (use {G}NULL PIN attack{W})'))

        wps.add_argument('--bully',
                         action='store_true',
                         dest='use_bully',
                         help=Color.s('Use {G}bully{W} program for WPS PIN & Pixie-Dust attacks '
                                      '(default: {G}reaver{W})'))
        # Alias
        wps.add_argument('-bully', help=argparse.SUPPRESS, action='store_true', dest='use_bully')

        wps.add_argument('--reaver',
                         action='store_true',
                         dest='use_reaver',
                         help=Color.s('Use {G}reaver{W} program for WPS PIN & Pixie-Dust attacks'
                                      ' (default: {G}reaver{W})'))
        # Alias
        wps.add_argument('-reaver', help=argparse.SUPPRESS, action='store_true', dest='use_reaver')

        # Ignore lock-outs
        wps.add_argument('--ignore-locks', action='store_true', dest='wps_ignore_lock',
                         help=Color.s('Do {O}not{W} stop WPS PIN attack if AP becomes {O}locked{W} '
                                      '(default: {G}stop{W})'))

        # Time limit on entire attack.
        wps.add_argument('--wps-time',
                         action='store',
                         dest='wps_pixie_timeout',
                         metavar='[sec]',
                         type=int,
                         help=self._verbose('Total time to wait before failing PixieDust attack (default: {G}%d sec{W})'
                                            % self.config.wps_pixie_timeout))
        # Alias
        wps.add_argument('-wpst', help=argparse.SUPPRESS, action='store', dest='wps_pixie_timeout', type=int)

        # Maximum number of 'failures' (WPSFail)
        wps.add_argument('--wps-fails',
                         action='store',
                         dest='wps_fail_threshold',
                         metavar='[num]',
                         type=int,
                         help=self._verbose('Maximum number of WPSFail/NoAssoc errors before failing '
                                            '(default: {G}%d{W})' % self.config.wps_fail_threshold))
        # Alias
        wps.add_argument('-wpsf', help=argparse.SUPPRESS, action='store', dest='wps_fail_threshold', type=int)

        # Maximum number of 'timeouts'
        wps.add_argument('--wps-timeouts',
                         action='store',
                         dest='wps_timeout_threshold',
                         metavar='[num]',
                         type=int,
                         help=self._verbose('Maximum number of Timeouts before failing (default: {G}%d{W})'
                                            % self.config.wps_timeout_threshold))
        # Alias
        wps.add_argument('-wpsto', help=argparse.SUPPRESS, action='store', dest='wps_timeout_threshold', type=int)

    def _add_pmkid_args(self, pmkid):
        pmkid.add_argument('--pmkid',
                           action='store_true',
                           dest='use_pmkid_only',
                           help=Color.s('{O}Only{W} use {C}PMKID capture{W}, avoids other WPS & '
                                        'WPA attacks (default: {G}off{W})'))
        pmkid.add_argument('--no-pmkid',
                           action='store_true',
                           dest='dont_use_pmkid',
                           help=Color.s('{O}Don\'t{W} use {C}PMKID capture{W} (default: {G}off{W})'))

        # Alias
        pmkid.add_argument('-pmkid', help=argparse.SUPPRESS, action='store_true', dest='use_pmkid_only')

        pmkid.add_argument('--pmkid-timeout',
                           action='store',
                           dest='pmkid_timeout',
                           metavar='[sec]',
                           type=int,
                           help=Color.s('Time to wait for PMKID capture (default: {G}%d{W} seconds)'
                                        % self.config.pmkid_timeout))

        # Passive PMKID capture arguments
        pmkid.add_argument('--pmkid-passive',
                           action='store_true',
                           dest='pmkid_passive',
                           help=Color.s('Passive PMKID capture mode: Sniff all networks '
                                       'without deauth. '
                                       '(default: {G}off{W})'))

        pmkid.add_argument('--pmkid-sniff',
                           action='store_true',
                           dest='pmkid_passive',
                           help=argparse.SUPPRESS)  # Alias for --pmkid-passive

        pmkid.add_argument('--pmkid-passive-duration',
                           action='store',
                           dest='pmkid_passive_duration',
                           metavar='[seconds]',
                           type=int,
                           help=self._verbose('Duration for passive capture in seconds '
                                             '(default: {G}infinite{W})'))

        pmkid.add_argument('--pmkid-passive-interval',
                           action='store',
                           dest='pmkid_passive_interval',
                           metavar='[seconds]',
                           type=int,
                           help=self._verbose('Interval between hash extractions '
                                             '(default: {G}%d{W} seconds)'
                                             % self.config.pmkid_passive_interval))

    def _add_wpasec_args(self, wpasec):
        """
        Add wpa-sec upload command-line arguments to argument parser.

        Defines all wpa-sec related arguments including:
        - --wpasec: Enable upload functionality
        - --wpasec-key: API key for authentication
        - --wpasec-auto: Automatic upload mode
        - --wpasec-url: Custom server URL
        - --wpasec-timeout: Connection timeout
        - --wpasec-email: Notification email
        - --wpasec-remove: Remove files after upload

        Args:
            wpasec: Argument group for wpa-sec options

        Example:
            >>> wpasec_group = parser.add_argument_group('WPA-SEC UPLOAD')
            >>> self._add_wpasec_args(wpasec_group)
        """
        wpasec.add_argument('--wpasec',
                            action='store_true',
                            dest='wpasec_enabled',
                            help=Color.s('Enable {C}wpa-sec.stanev.org{W} upload functionality. '
                                        'Uploads captured handshakes to online cracking service. '
                                        'Requires API key from wpa-sec.stanev.org (default: {G}off{W})'))

        wpasec.add_argument('--wpasec-key',
                            action='store',
                            dest='wpasec_api_key',
                            metavar='[key]',
                            type=str,
                            help=Color.s('API key for {C}wpa-sec.stanev.org{W}. '
                                        'Register at wpa-sec.stanev.org to obtain your key. '
                                        'Required for uploading captures.'))

        wpasec.add_argument('--wpasec-auto',
                            action='store_true',
                            dest='wpasec_auto_upload',
                            help=Color.s('Automatically upload all captured handshakes without prompting. '
                                        'When disabled, you will be asked before each upload. '
                                        '(default: {G}off{W})'))

        wpasec.add_argument('--wpasec-url',
                            action='store',
                            dest='wpasec_url',
                            metavar='[url]',
                            type=str,
                            help=self._verbose('Custom wpa-sec server URL. '
                                              'Use this to upload to alternative wpa-sec instances. '
                                              '(default: {G}https://wpa-sec.stanev.org{W})'))

        wpasec.add_argument('--wpasec-timeout',
                            action='store',
                            dest='wpasec_timeout',
                            metavar='[seconds]',
                            type=int,
                            help=self._verbose('Connection timeout for uploads in seconds. '
                                              'Increase if you have a slow connection. '
                                              '(default: {G}30{W} seconds)'))

        wpasec.add_argument('--wpasec-email',
                            action='store',
                            dest='wpasec_email',
                            metavar='[email]',
                            type=str,
                            help=self._verbose('Email address for wpa-sec notifications. '
                                              'Receive alerts when passwords are cracked. '
                                              '(default: {G}none{W})'))

        wpasec.add_argument('--wpasec-remove',
                            action='store_true',
                            dest='wpasec_remove_after_upload',
                            help=self._verbose('Remove capture files after successful upload. '
                                              'Saves disk space but prevents local cracking. '
                                              '(default: {G}off{W})'))

    @staticmethod
    def _add_command_args(commands):
        commands.add_argument('--cracked',
                              action='store_true',
                              dest='cracked',
                              help=Color.s('Print previously-cracked access points'))

        commands.add_argument('--ignored',
                              action='store_true',
                              dest='ignored',
                              help=Color.s('Print ignored access points'))

        commands.add_argument('-cracked',
                              help=argparse.SUPPRESS,
                              action='store_true',
                              dest='cracked')

        commands.add_argument('--check',
                              action='store',
                              metavar='file',
                              nargs='?',
                              const='<all>',
                              dest='check_handshake',
                              help=Color.s('Check a {C}.cap file{W} (or all {C}hs/*.cap{W} files) for WPA handshakes'))

        commands.add_argument('-check',
                              help=argparse.SUPPRESS,
                              action='store',
                              nargs='?',
                              const='<all>',
                              dest='check_handshake')

        commands.add_argument('--crack',
                              action='store_true',
                              dest='crack_handshake',
                              help=Color.s('Show commands to crack a captured handshake'))

        commands.add_argument('--syscheck',
                              action='store_true',
                              dest='syscheck',
                              help=Color.s('Comprehensive system readiness check: tools, interfaces, '
                                         'driver compatibility, attack readiness matrix. '
                                         'Use with {C}-v{W} to include monitor mode smoke test.'))

        commands.add_argument('--update-db',
                              action='store_true',
                              dest='update_db',
                              help=Color.s('Update the local MAC address prefix database from IEEE registries'))

        commands.add_argument('--resume',
                              action='store_true',
                              dest='resume',
                              help=Color.s('Resume a previously interrupted attack session. '
                                         'If multiple sessions exist, displays a list to choose from. '
                                         'Sessions are automatically saved during attacks and can be resumed '
                                         'after interruption (Ctrl+C, crash, power loss).'))

        commands.add_argument('--resume-latest',
                              action='store_true',
                              dest='resume_latest',
                              help=Color.s('Automatically resume the most recent session without prompting. '
                                         'Useful for quickly continuing the last interrupted attack.'))

        commands.add_argument('--resume-id',
                              action='store',
                              metavar='session_id',
                              dest='resume_id',
                              help=Color.s('Resume a specific session by ID (e.g., session_20250126_120000). '
                                         'Use --resume to see available session IDs.'))

        commands.add_argument('--clean-sessions',
                              action='store_true',
                              dest='clean_sessions',
                              help=Color.s('Remove old session files (older than 7 days). '
                                         'Sessions are stored in ~/.wifite/sessions/ and cleaned up '
                                         'automatically on startup. Use this to manually clean up old sessions.'))


if __name__ == '__main__':
    from .config import Configuration

    Configuration.initialize(False)
    a = Arguments(Configuration)
    args = a.args
    for (key, value) in sorted(args.__dict__.items()):
        Color.pl('{C}%s: {G}%s{W}' % (key.ljust(21), value))
