#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from .util.color import Color
from .tools.macchanger import Macchanger

class Configuration(object):
    ''' Stores configuration variables and functions for Wifite. '''
    version = '2.2.5'

    initialized = False # Flag indicating config has been initialized
    temp_dir = None     # Temporary directory
    interface = None
    verbose = 0

    @classmethod
    def initialize(cls, load_interface=True):
        '''
            Sets up default initial configuration values.
            Also sets config values based on command-line arguments.
        '''
        # TODO: categorize configuration into separate classes (under config/*.py)
        # E.g. Configuration.wps.enabled, Configuration.wps.timeout, etc

        # Only initialize this class once
        if cls.initialized:
            return
        cls.initialized = True

        cls.verbose = 0 # Verbosity of output. Higher number means more debug info about running processes.
        cls.print_stack_traces = True

        cls.kill_conflicting_processes = False

        cls.scan_time = 0 # Time to wait before attacking all targets

        cls.tx_power = 0 # Wifi transmit power (0 is default)
        cls.interface = None
        cls.target_channel = None # User-defined channel to scan
        cls.target_essid = None # User-defined AP name
        cls.target_bssid = None # User-defined AP BSSID
        cls.ignore_essid = None # ESSIDs to ignore
        cls.clients_only = False # Only show targets that have associated clients
        cls.five_ghz = False # Scan 5Ghz channels
        cls.show_bssids = False # Show BSSIDs in targets list
        cls.random_mac = False # Should generate a random Mac address at startup.
        cls.no_deauth = False # Deauth hidden networks & WPA handshake targets
        cls.num_deauths = 1 # Number of deauth packets to send to each target.

        cls.encryption_filter = ['WEP', 'WPA', 'WPS']

        # EvilTwin variables
        cls.use_eviltwin = False
        cls.eviltwin_port = 80
        cls.eviltwin_deauth_iface = None
        cls.eviltwin_fakeap_iface = None

        # WEP variables
        cls.wep_filter = False # Only attack WEP networks
        cls.wep_pps = 600 # Packets per second
        cls.wep_timeout = 600 # Seconds to wait before failing
        cls.wep_crack_at_ivs = 10000 # Minimum IVs to start cracking
        cls.require_fakeauth = False
        cls.wep_restart_stale_ivs = 11 # Seconds to wait before restarting
                                                 # Aireplay if IVs don't increaes.
                                                 # '0' means never restart.
        cls.wep_restart_aircrack = 30  # Seconds to give aircrack to crack
                                                 # before restarting the process.
        cls.wep_crack_at_ivs = 10000   # Number of IVS to start cracking
        cls.wep_keep_ivs = False       # Retain .ivs files across multiple attacks.

        # WPA variables
        cls.wpa_filter = False # Only attack WPA networks
        cls.wpa_deauth_timeout = 15 # Wait time between deauths
        cls.wpa_attack_timeout = 500 # Wait time before failing
        cls.wpa_handshake_dir = 'hs' # Dir to store handshakes
        cls.wpa_strip_handshake = False # Strip non-handshake packets
        cls.ignore_old_handshakes = False # Always fetch a new handshake

        # PMKID variables
        cls.use_pmkid_only = False  # Only use PMKID Capture+Crack attack
        cls.pmkid_timeout = 30  # Time to wait for PMKID capture

        # Default dictionary for cracking
        cls.cracked_file = 'cracked.txt'
        cls.wordlist = None
        wordlists = [
            './wordlist-top4800-probable.txt',  # Local file (ran from cloned repo)
            '/usr/share/dict/wordlist-top4800-probable.txt',  # setup.py with prefix=/usr
            '/usr/local/share/dict/wordlist-top4800-probable.txt',  # setup.py with prefix=/usr/local
            # Other passwords found on Kali
            '/usr/share/wfuzz/wordlist/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt',
            '/usr/share/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt',
            '/usr/share/wordlists/fern-wifi/common.txt'
        ]
        for wlist in wordlists:
            if os.path.exists(wlist):
                cls.wordlist = wlist
                break

        # WPS variables
        cls.wps_filter  = False  # Only attack WPS networks
        cls.no_wps      = False  # Do not use WPS attacks (Pixie-Dust & PIN attacks)
        cls.wps_only    = False  # ONLY use WPS attacks on non-WEP networks
        cls.use_bully   = False  # Use bully instead of reaver
        cls.wps_pixie   = True
        cls.wps_pin     = True
        cls.wps_ignore_lock = False  # Skip WPS PIN attack if AP is locked.
        cls.wps_pixie_timeout = 300      # Seconds to wait for PIN before WPS Pixie attack fails
        cls.wps_fail_threshold = 100     # Max number of failures
        cls.wps_timeout_threshold = 100  # Max number of timeouts

        # Commands
        cls.show_cracked = False
        cls.check_handshake = None
        cls.crack_handshake = False

        # Overwrite config values with arguments (if defined)
        cls.load_from_arguments()

        if load_interface:
            cls.get_monitor_mode_interface()


    @classmethod
    def get_monitor_mode_interface(cls):
        if cls.interface is None:
            # Interface wasn't defined, select it!
            from .tools.airmon import Airmon
            cls.interface = Airmon.ask()
            if cls.random_mac:
                Macchanger.random()

    @classmethod
    def load_from_arguments(cls):
        ''' Sets configuration values based on Argument.args object '''
        from .args import Arguments

        args = Arguments(cls).args
        cls.parse_settings_args(args)
        cls.parse_wep_args(args)
        cls.parse_wpa_args(args)
        cls.parse_wps_args(args)
        cls.parse_pmkid_args(args)
        cls.parse_encryption()

        # EvilTwin
        '''
        if args.use_eviltwin:
            cls.use_eviltwin = True
            Color.pl('{+} {C}option:{W} using {G}eviltwin attacks{W} against all targets')
        '''

        cls.parse_wep_attacks()

        cls.validate()

        # Commands
        if args.cracked:         cls.show_cracked = True
        if args.check_handshake: cls.check_handshake = args.check_handshake
        if args.crack_handshake: cls.crack_handshake = True


    @classmethod
    def validate(cls):
        if cls.use_pmkid_only and cls.wps_only:
            Color.pl('{!} {R}Bad Configuration:{O} --pmkid and --wps-only are not compatible')
            raise RuntimeError('Unable to attack networks: --pmkid and --wps-only are not compatible together')


    @classmethod
    def parse_settings_args(cls, args):
        '''Parses basic settings/configurations from arguments.'''
        if args.random_mac:
            cls.random_mac = True
            Color.pl('{+} {C}option:{W} using {G}random mac address{W} ' +
                    'when scanning & attacking')

        if args.channel:
            cls.target_channel = args.channel
            Color.pl('{+} {C}option:{W} scanning for targets on channel ' +
                    '{G}%s{W}' % args.channel)

        if args.interface:
            cls.interface = args.interface
            Color.pl('{+} {C}option:{W} using wireless interface ' +
                    '{G}%s{W}' % args.interface)

        if args.target_bssid:
            cls.target_bssid = args.target_bssid
            Color.pl('{+} {C}option:{W} targeting BSSID ' +
                    '{G}%s{W}' % args.target_bssid)

        if args.five_ghz == True:
            cls.five_ghz = True
            Color.pl('{+} {C}option:{W} including {G}5Ghz networks{W} in scans')

        if args.show_bssids == True:
            cls.show_bssids = True
            Color.pl('{+} {C}option:{W} showing {G}bssids{W} of targets during scan')

        if args.no_deauth == True:
            cls.no_deauth = True
            Color.pl('{+} {C}option:{W} will {R}not{W} {O}deauth{W} clients ' +
                    'during scans or captures')

        if args.num_deauths and args.num_deauths > 0:
            cls.num_deauths = args.num_deauths
            Color.pl('{+} {C}option:{W} send {G}%d{W} deauth packets when deauthing' % (
                cls.num_deauths))

        if args.target_essid:
            cls.target_essid = args.target_essid
            Color.pl('{+} {C}option:{W} targeting ESSID {G}%s{W}' % args.target_essid)

        if args.ignore_essid is not None:
            cls.ignore_essid = args.ignore_essid
            Color.pl('{+} {C}option:{W} {O}ignoring ESSIDs that include {R}%s{W}' % (
                args.ignore_essid))

        if args.clients_only == True:
            cls.clients_only = True
            Color.pl('{+} {C}option:{W} {O}ignoring targets that do not have ' +
                'associated clients')

        if args.scan_time:
            cls.scan_time = args.scan_time
            Color.pl('{+} {C}option:{W} ({G}pillage{W}) attack all targets ' +
                'after {G}%d{W}s' % args.scan_time)

        if args.verbose:
            cls.verbose = args.verbose
            Color.pl('{+} {C}option:{W} verbosity level {G}%d{W}' % args.verbose)

        if args.kill_conflicting_processes:
            cls.kill_conflicting_processes = True
            Color.pl('{+} {C}option:{W} kill conflicting processes {G}enabled{W}')


    @classmethod
    def parse_wep_args(cls, args):
        '''Parses WEP-specific arguments'''
        if args.wep_filter:
            cls.wep_filter = args.wep_filter

        if args.wep_pps:
            cls.wep_pps = args.wep_pps
            Color.pl('{+} {C}option:{W} using {G}%d{W} packets/sec on WEP attacks' % (
                args.wep_pps))

        if args.wep_timeout:
            cls.wep_timeout = args.wep_timeout
            Color.pl('{+} {C}option:{W} WEP attack timeout set to ' +
                '{G}%d seconds{W}' % args.wep_timeout)

        if args.require_fakeauth:
            cls.require_fakeauth = True
            Color.pl('{+} {C}option:{W} fake-authentication is ' +
                '{G}required{W} for WEP attacks')

        if args.wep_crack_at_ivs:
            cls.wep_crack_at_ivs = args.wep_crack_at_ivs
            Color.pl('{+} {C}option:{W} will start cracking WEP keys at ' +
                '{G}%d IVs{W}' % args.wep_crack_at_ivs)

        if args.wep_restart_stale_ivs:
            cls.wep_restart_stale_ivs = args.wep_restart_stale_ivs
            Color.pl('{+} {C}option:{W} will restart aireplay after ' +
                '{G}%d seconds{W} of no new IVs' % args.wep_restart_stale_ivs)

        if args.wep_restart_aircrack:
            cls.wep_restart_aircrack = args.wep_restart_aircrack
            Color.pl('{+} {C}option:{W} will restart aircrack every ' +
                '{G}%d seconds{W}' % args.wep_restart_aircrack)

        if args.wep_keep_ivs:
            cls.wep_keep_ivs = args.wep_keep_ivs
            Color.pl('{+} {C}option:{W} keep .ivs files across multiple WEP attacks')

    @classmethod
    def parse_wpa_args(cls, args):
        '''Parses WPA-specific arguments'''
        if args.wpa_filter:
            cls.wpa_filter = args.wpa_filter

        if args.wordlist:
            if not os.path.exists(args.wordlist):
                cls.wordlist = None
                Color.pl('{+} {C}option:{O} wordlist {R}%s{O} was not found, wifite will NOT attempt to crack handshakes' % args.wordlist)
            elif os.path.isfile(args.wordlist):
                cls.wordlist = args.wordlist
                Color.pl('{+} {C}option:{W} using wordlist {G}%s{W} to crack WPA handshakes' % args.wordlist)
            elif os.path.isdir(args.wordlist):
                cls.wordlist = None
                Color.pl('{+} {C}option:{O} wordlist {R}%s{O} is a directory, not a file. Wifite will NOT attempt to crack handshakes' % args.wordlist)

        if args.wpa_deauth_timeout:
            cls.wpa_deauth_timeout = args.wpa_deauth_timeout
            Color.pl('{+} {C}option:{W} will deauth WPA clients every ' +
                    '{G}%d seconds{W}' % args.wpa_deauth_timeout)

        if args.wpa_attack_timeout:
            cls.wpa_attack_timeout = args.wpa_attack_timeout
            Color.pl('{+} {C}option:{W} will stop WPA handshake capture after ' +
                    '{G}%d seconds{W}' % args.wpa_attack_timeout)

        if args.ignore_old_handshakes:
            cls.ignore_old_handshakes = True
            Color.pl('{+} {C}option:{W} will {O}ignore{W} existing handshakes ' +
                    '(force capture)')

        if args.wpa_handshake_dir:
            cls.wpa_handshake_dir = args.wpa_handshake_dir
            Color.pl('{+} {C}option:{W} will store handshakes to ' +
                    '{G}%s{W}' % args.wpa_handshake_dir)

        if args.wpa_strip_handshake:
            cls.wpa_strip_handshake = True
            Color.pl('{+} {C}option:{W} will {G}strip{W} non-handshake packets')

    @classmethod
    def parse_wps_args(cls, args):
        '''Parses WPS-specific arguments'''
        if args.wps_filter:
            cls.wps_filter = args.wps_filter

        if args.wps_only:
            cls.wps_only = True
            cls.wps_filter = True  # Also only show WPS networks
            Color.pl('{+} {C}option:{W} will *only* attack WPS networks with ' +
                    '{G}WPS attacks{W} (avoids handshake and PMKID)')

        if args.no_wps:
            # No WPS attacks at all
            cls.no_wps = args.no_wps
            cls.wps_pixie = False
            cls.wps_pin = False
            Color.pl('{+} {C}option:{W} will {O}never{W} use {C}WPS attacks{W} ' +
                    '(Pixie-Dust/PIN) on targets')

        elif args.wps_pixie:
            # WPS Pixie-Dust only
            cls.wps_pixie = True
            cls.wps_pin = False
            Color.pl('{+} {C}option:{W} will {G}only{W} use {C}WPS Pixie-Dust ' +
                    'attack{W} (no {O}PIN{W}) on targets')

        elif args.wps_no_pixie:
            # WPS PIN only
            cls.wps_pixie = False
            cls.wps_pin = True
            Color.pl('{+} {C}option:{W} will {G}only{W} use {C}WPS PIN attack{W} ' +
                    '(no {O}Pixie-Dust{W}) on targets')

        if args.use_bully:
            from .tools.bully import Bully
            if not Bully.exists():
                Color.pl('{!} {R}Bully not found. Defaulting to {O}reaver{W}')
                cls.use_bully = False
            else:
                cls.use_bully = args.use_bully
                Color.pl('{+} {C}option:{W} use {C}bully{W} instead of {C}reaver{W} ' +
                        'for WPS Attacks')

        if args.wps_pixie_timeout:
            cls.wps_pixie_timeout = args.wps_pixie_timeout
            Color.pl('{+} {C}option:{W} WPS pixie-dust attack will fail after ' +
                    '{O}%d seconds{W}' % args.wps_pixie_timeout)

        if args.wps_fail_threshold:
            cls.wps_fail_threshold = args.wps_fail_threshold
            Color.pl('{+} {C}option:{W} will stop WPS attack after ' +
                    '{O}%d failures{W}' % args.wps_fail_threshold)

        if args.wps_timeout_threshold:
            cls.wps_timeout_threshold = args.wps_timeout_threshold
            Color.pl('{+} {C}option:{W} will stop WPS attack after ' +
                    '{O}%d timeouts{W}' % args.wps_timeout_threshold)

        if args.wps_ignore_lock:
            cls.wps_ignore_lock = True
            Color.pl('{+} {C}option:{W} will {O}ignore{W} WPS lock-outs')

    @classmethod
    def parse_pmkid_args(cls, args):
        if args.use_pmkid_only:
            cls.use_pmkid_only = True
            Color.pl('{+} {C}option:{W} will ONLY use {C}PMKID{W} attack on WPA networks')

        if args.pmkid_timeout:
            cls.pmkid_timeout = args.pmkid_timeout
            Color.pl('{+} {C}option:{W} will wait {G}%d seconds{W} during {C}PMKID{W} capture' % args.pmkid_timeout)

    @classmethod
    def parse_encryption(cls):
        '''Adjusts encryption filter (WEP and/or WPA and/or WPS)'''
        cls.encryption_filter = []
        if cls.wep_filter: cls.encryption_filter.append('WEP')
        if cls.wpa_filter: cls.encryption_filter.append('WPA')
        if cls.wps_filter: cls.encryption_filter.append('WPS')

        if len(cls.encryption_filter) == 3:
            Color.pl('{+} {C}option:{W} targeting {G}all encrypted networks{W}')
        elif len(cls.encryption_filter) == 0:
            # Default to scan all types
            cls.encryption_filter = ['WEP', 'WPA', 'WPS']
        else:
            Color.pl('{+} {C}option:{W} ' +
                     'targeting {G}%s-encrypted{W} networks'
                        % '/'.join(cls.encryption_filter))

    @classmethod
    def parse_wep_attacks(cls):
        '''Parses and sets WEP-specific args (-chopchop, -fragment, etc)'''
        cls.wep_attacks = []
        from sys import argv
        seen = set()
        for arg in argv:
            if arg in seen: continue
            seen.add(arg)
            if arg == '-arpreplay':  cls.wep_attacks.append('replay')
            if arg == '-fragment':   cls.wep_attacks.append('fragment')
            if arg == '-chopchop':   cls.wep_attacks.append('chopchop')
            if arg == '-caffelatte': cls.wep_attacks.append('caffelatte')
            if arg == '-p0841':      cls.wep_attacks.append('p0841')
            if arg == '-hirte':      cls.wep_attacks.append('hirte')

        if len(cls.wep_attacks) == 0:
            # Use all attacks
            cls.wep_attacks = ['replay',
                'fragment',
                'chopchop',
                'caffelatte',
                'p0841',
                'hirte'
            ]
        elif len(cls.wep_attacks) > 0:
            Color.pl('{+} {C}option:{W} using {G}%s{W} WEP attacks'
                % '{W}, {G}'.join(cls.wep_attacks))


    @classmethod
    def temp(cls, subfile=''):
        ''' Creates and/or returns the temporary directory '''
        if cls.temp_dir is None:
            cls.temp_dir = cls.create_temp()
        return cls.temp_dir + subfile

    @staticmethod
    def create_temp():
        ''' Creates and returns a temporary directory '''
        from tempfile import mkdtemp
        tmp = mkdtemp(prefix='wifite')
        if not tmp.endswith(os.sep):
            tmp += os.sep
        return tmp

    @classmethod
    def delete_temp(cls):
        ''' Remove temp files and folder '''
        if cls.temp_dir is None: return
        if os.path.exists(cls.temp_dir):
            for f in os.listdir(cls.temp_dir):
                os.remove(cls.temp_dir + f)
            os.rmdir(cls.temp_dir)


    @classmethod
    def exit_gracefully(cls, code=0):
        ''' Deletes temp and exist with the given code '''
        cls.delete_temp()
        Macchanger.reset_if_changed()
        from .tools.airmon import Airmon
        if cls.interface is not None and Airmon.base_interface is not None:
            Color.pl('{!} {O}Note:{W} Leaving interface in Monitor Mode!')
            Color.pl('{!} To disable Monitor Mode when finished: ' +
                    '{C}airmon-ng stop %s{W}' % cls.interface)

            # Stop monitor mode
            #Airmon.stop(cls.interface)
            # Bring original interface back up
            #Airmon.put_interface_up(Airmon.base_interface)

        if Airmon.killed_network_manager:
            Color.pl('{!} You can restart NetworkManager when finished ({C}service network-manager start{W})')
            #Airmon.start_network_manager()

        exit(code)

    @classmethod
    def dump(cls):
        ''' (Colorful) string representation of the configuration '''
        from .util.color import Color

        max_len = 20
        for key in cls.__dict__.keys():
            max_len = max(max_len, len(key))

        result  = Color.s('{W}%s  Value{W}\n' % 'cls Key'.ljust(max_len))
        result += Color.s('{W}%s------------------{W}\n' % ('-' * max_len))

        for (key,val) in sorted(cls.__dict__.items()):
            if key.startswith('__') or type(val) in [classmethod, staticmethod] or val is None:
                continue
            result += Color.s('{G}%s {W} {C}%s{W}\n' % (key.ljust(max_len),val))
        return result

if __name__ == '__main__':
    Configuration.initialize(False)
    print(Configuration.dump())
