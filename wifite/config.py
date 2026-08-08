#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from .util.color import Color
from .tools.macchanger import Macchanger

class Configuration(object):
    ''' Stores configuration variables and functions for Wifite. '''
    version = '2.2.5-ADVANCED'

    initialized = False
    temp_dir = None
    interface = None
    verbose = 0

    @classmethod
    def initialize(cls, load_interface=True):
        '''
            Sets up default initial configuration values with advanced optimizations.
        '''
        if cls.initialized:
            return
        cls.initialized = True

        cls.verbose = 0
        cls.print_stack_traces = True
        cls.kill_conflicting_processes = False

        # === PERFORMANCE OPTIMIZATION ===
        cls.enable_performance_tuning = True
        cls.connection_pool_size = 5
        cls.cache_results = True
        cls.parallel_attacks = 2
        cls.optimize_packets = True
        
        cls.scan_time = 0
        cls.tx_power = 0
        cls.interface = None
        cls.target_channel = None
        cls.target_essid = None
        cls.target_bssid = None
        cls.ignore_essid = None
        cls.clients_only = False
        cls.five_ghz = False
        cls.show_bssids = False
        cls.random_mac = False
        cls.no_deauth = False
        cls.num_deauths = 1

        cls.encryption_filter = ['WEP', 'WPA', 'WPS']

        # === ADVANCED WPS PIN SETTINGS ===
        cls.wps_pin_enabled = True
        cls.wps_pin_timeout = 120  # Increased for better success
        cls.wps_pin_retry_attempts = 5
        cls.wps_pin_retry_delay = 3
        cls.wps_pin_backoff_multiplier = 1.5
        cls.wps_pin_brute_force = True
        cls.wps_pin_common_pins = [
            '12345670', '11223344', '12345678', '87654321',
            '00000000', '11111111', '99999999', '00001111'
        ]
        
        # === TIMEOUT OPTIMIZATION ===
        cls.adaptive_timeout = True
        cls.connection_timeout = 10
        cls.read_timeout = 15
        cls.socket_timeout = 5
        cls.handshake_timeout_initial = 30
        cls.handshake_timeout_max = 300
        cls.pmkid_timeout = 30
        cls.enable_timeout_recovery = True
        cls.timeout_backoff = 1.2
        
        # === HANDSHAKE CAPTURE OPTIMIZATION ===
        cls.fast_handshake_capture = True
        cls.handshake_detection_threshold = 0.8
        cls.enable_packet_filtering = True
        cls.aggressive_deauth = True
        cls.deauth_burst_count = 5
        cls.deauth_burst_interval = 0.1
        cls.monitor_handshake_real_time = True
        cls.auto_packet_optimization = True
        cls.pcap_buffer_size = 8192
        
        # EvilTwin variables
        cls.use_eviltwin = False
        cls.eviltwin_port = 80
        cls.eviltwin_deauth_iface = None
        cls.eviltwin_fakeap_iface = None

        # WEP variables
        cls.wep_filter = False
        cls.wep_pps = 600
        cls.wep_timeout = 600
        cls.wep_crack_at_ivs = 10000
        cls.require_fakeauth = False
        cls.wep_restart_stale_ivs = 11
        cls.wep_restart_aircrack = 30
        cls.wep_crack_at_ivs = 10000
        cls.wep_keep_ivs = False

        # WPA variables
        cls.wpa_filter = False
        cls.wpa_deauth_timeout = 15
        cls.wpa_attack_timeout = 500
        cls.wpa_handshake_dir = 'hs'
        cls.wpa_strip_handshake = False
        cls.ignore_old_handshakes = False

        # PMKID variables
        cls.use_pmkid_only = False
        cls.pmkid_timeout = 30

        # Default dictionary for cracking
        cls.cracked_file = 'cracked.txt'
        cls.wordlist = None
        wordlists = [
            './wordlist-top4800-probable.txt',
            '/usr/share/dict/wordlist-top4800-probable.txt',
            '/usr/local/share/dict/wordlist-top4800-probable.txt',
            '/usr/share/wfuzz/wordlist/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt',
            '/usr/share/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt',
            '/usr/share/wordlists/fern-wifi/common.txt'
        ]
        for wlist in wordlists:
            if os.path.exists(wlist):
                cls.wordlist = wlist
                break

        # WPS variables
        cls.wps_filter = False
        cls.no_wps = False
        cls.wps_only = False
        cls.use_bully = False
        cls.wps_pixie = True
        cls.wps_pin = True
        cls.wps_ignore_lock = False
        cls.wps_pixie_timeout = 300
        cls.wps_fail_threshold = 100
        cls.wps_timeout_threshold = 100

        # Commands
        cls.show_cracked = False
        cls.check_handshake = None
        cls.crack_handshake = False

        cls.load_from_arguments()

        if load_interface:
            cls.get_monitor_mode_interface()

    @classmethod
    def get_monitor_mode_interface(cls):
        if cls.interface is None:
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
        cls.parse_advanced_args(args)
        cls.parse_encryption()
        cls.parse_wep_attacks()
        cls.validate()

        if args.cracked:         cls.show_cracked = True
        if args.check_handshake: cls.check_handshake = args.check_handshake
        if args.crack_handshake: cls.crack_handshake = True

    @classmethod
    def parse_advanced_args(cls, args):
        '''Parses advanced optimization arguments'''
        if hasattr(args, 'fast_capture') and args.fast_capture:
            cls.fast_handshake_capture = True
            cls.aggressive_deauth = True
            cls.deauth_burst_count = 8
            Color.pl('{+} {C}option:{W} using {G}fast handshake capture{W}')

        if hasattr(args, 'pin_mode') and args.pin_mode:
            cls.wps_pin_enabled = True
            cls.wps_pin_timeout = args.pin_timeout or 120
            cls.wps_pin_retry_attempts = args.pin_retries or 5
            Color.pl('{+} {C}option:{W} WPS PIN attack {G}enabled{W} ' +
                    'with timeout {G}%ds{W}' % cls.wps_pin_timeout)

        if hasattr(args, 'adaptive_timeout') and args.adaptive_timeout:
            cls.adaptive_timeout = True
            Color.pl('{+} {C}option:{W} using {G}adaptive timeouts{W}')

        if hasattr(args, 'parallel_attacks') and args.parallel_attacks:
            cls.parallel_attacks = args.parallel_attacks
            Color.pl('{+} {C}option:{W} parallel attacks {G}%d{W}' % 
                    cls.parallel_attacks)

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
            Color.pl('{+} {C}option:{W} using {G}random mac address{W}')

        if args.channel:
            cls.target_channel = args.channel
            Color.pl('{+} {C}option:{W} scanning for targets on channel {G}%s{W}' % args.channel)

        if args.interface:
            cls.interface = args.interface
            Color.pl('{+} {C}option:{W} using wireless interface {G}%s{W}' % args.interface)

        if args.target_bssid:
            cls.target_bssid = args.target_bssid
            Color.pl('{+} {C}option:{W} targeting BSSID {G}%s{W}' % args.target_bssid)

        if args.five_ghz == True:
            cls.five_ghz = True
            Color.pl('{+} {C}option:{W} including {G}5Ghz networks{W}')

        if args.show_bssids == True:
            cls.show_bssids = True
            Color.pl('{+} {C}option:{W} showing {G}bssids{W}')

        if args.no_deauth == True:
            cls.no_deauth = True
            Color.pl('{+} {C}option:{W} will {R}not{W} deauth clients')

        if args.num_deauths and args.num_deauths > 0:
            cls.num_deauths = args.num_deauths
            Color.pl('{+} {C}option:{W} send {G}%d{W} deauth packets' % cls.num_deauths)

        if args.target_essid:
            cls.target_essid = args.target_essid
            Color.pl('{+} {C}option:{W} targeting ESSID {G}%s{W}' % args.target_essid)

        if args.clients_only == True:
            cls.clients_only = True
            Color.pl('{+} {C}option:{W} {O}ignoring targets without clients{W}')

        if args.scan_time:
            cls.scan_time = args.scan_time
            Color.pl('{+} {C}option:{W} attack all targets after {G}%d{W}s' % args.scan_time)

        if args.verbose:
            cls.verbose = args.verbose
            Color.pl('{+} {C}option:{W} verbosity level {G}%d{W}' % args.verbose)

    @classmethod
    def parse_wep_args(cls, args):
        '''Parses WEP-specific arguments'''
        if args.wep_filter:
            cls.wep_filter = args.wep_filter
        if args.wep_pps:
            cls.wep_pps = args.wep_pps
            Color.pl('{+} {C}option:{W} using {G}%d{W} packets/sec' % args.wep_pps)
        if args.wep_timeout:
            cls.wep_timeout = args.wep_timeout
            Color.pl('{+} {C}option:{W} WEP timeout {G}%d{W}s' % args.wep_timeout)

    @classmethod
    def parse_wpa_args(cls, args):
        '''Parses WPA-specific arguments'''
        if args.wpa_filter:
            cls.wpa_filter = args.wpa_filter
        if args.wordlist:
            if os.path.exists(args.wordlist) and os.path.isfile(args.wordlist):
                cls.wordlist = args.wordlist
                Color.pl('{+} {C}option:{W} using wordlist {G}%s{W}' % args.wordlist)

    @classmethod
    def parse_wps_args(cls, args):
        '''Parses WPS-specific arguments'''
        if args.wps_filter:
            cls.wps_filter = args.wps_filter

    @classmethod
    def parse_pmkid_args(cls, args):
        if args.use_pmkid_only:
            cls.use_pmkid_only = True

    @classmethod
    def parse_encryption(cls):
        '''Adjusts encryption filter'''
        cls.encryption_filter = []
        if cls.wep_filter: cls.encryption_filter.append('WEP')
        if cls.wpa_filter: cls.encryption_filter.append('WPA')
        if cls.wps_filter: cls.encryption_filter.append('WPS')

        if len(cls.encryption_filter) == 0:
            cls.encryption_filter = ['WEP', 'WPA', 'WPS']

    @classmethod
    def parse_wep_attacks(cls):
        '''Parses WEP-specific args'''
        cls.wep_attacks = []
        from sys import argv
        seen = set()
        for arg in argv:
            if arg in seen: continue
            seen.add(arg)
            if arg == '-arpreplay':  cls.wep_attacks.append('replay')
            if arg == '-fragment':   cls.wep_attacks.append('fragment')
            if arg == '-chopchop':   cls.wep_attacks.append('chopchop')

        if len(cls.wep_attacks) == 0:
            cls.wep_attacks = ['replay', 'fragment', 'chopchop']

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
        ''' Deletes temp and exits with the given code '''
        cls.delete_temp()
        Macchanger.reset_if_changed()
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
