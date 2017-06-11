#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Color import Color
from Macchanger import Macchanger

import os

class Configuration(object):
    ''' Stores configuration variables and functions for Wifite. '''
    verbose = 0

    initialized = False # Flag indicating config has been initialized
    temp_dir = None     # Temporary directory
    version = 2.00

    @staticmethod
    def initialize(load_interface=True):
        '''
            Sets up default initial configuration values.
            Also sets config values based on command-line arguments.
        '''

        # Only initialize this class once
        if Configuration.initialized:
            return
        Configuration.initialized = True

        Configuration.verbose = 0 # Verbosity level.

        Configuration.tx_power = 0 # Wifi transmit power (0 is default)
        Configuration.interface = None
        Configuration.target_channel = None # User-defined channel to scan
        Configuration.target_essid = None # User-defined AP name
        Configuration.target_bssid = None # User-defined AP BSSID
        Configuration.five_ghz = False # Scan 5Ghz channels
        Configuration.pillage = False # "All" mode to attack everything
        Configuration.random_mac = False # Should generate a random Mac address at startup.
        Configuration.no_deauth = False # Deauth hidden networks & WPA handshake targets
        Configuration.num_deauths = 1 # Number of deauth packets to send to each target.

        Configuration.encryption_filter = ['WEP', 'WPA', 'WPS']

        # WEP variables
        Configuration.wep_filter = False # Only attack WEP networks
        Configuration.wep_pps = 600 # Packets per second
        Configuration.wep_timeout = 600 # Seconds to wait before failing
        Configuration.wep_crack_at_ivs = 10000 # Minimum IVs to start cracking
        Configuration.require_fakeauth = False
        Configuration.wep_restart_stale_ivs = 11 # Seconds to wait before restarting
                                                 # Aireplay if IVs don't increaes.
                                                 # "0" means never restart.
        Configuration.wep_restart_aircrack = 30  # Seconds to give aircrack to crack
                                                 # before restarting the process.
        Configuration.wep_crack_at_ivs = 10000   # Number of IVS to start cracking

        # WPA variables
        Configuration.wpa_filter = False # Only attack WPA networks
        Configuration.wpa_deauth_timeout = 15 # Wait time between deauths
        Configuration.wpa_attack_timeout = 500 # Wait time before failing
        Configuration.wpa_handshake_dir = "hs" # Dir to store handshakes
        Configuration.wpa_strip_handshake = False # Strip non-handshake packets

        # Default dictionary for cracking
        Configuration.wordlist = None
        wordlists = [
            '/usr/share/wfuzz/wordlist/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt',
            '/usr/share/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt',
            '/usr/share/wordlists/fern-wifi/common.txt'
        ]
        for wlist in wordlists:
            if os.path.exists(wlist):
                Configuration.wordlist = wlist
                break

        # WPS variables
        Configuration.wps_filter  = False  # Only attack WPS networks
        Configuration.no_reaver   = False  # Do not use Reaver on WPS networks
        Configuration.reaver      = False  # ONLY use Reaver on WPS networks
        Configuration.pixie_only  = False  # ONLY use Pixie-Dust attack on WPS
        Configuration.wps_pin_timeout = 600        # Seconds to wait for PIN before reaver fails
        Configuration.wps_pixie_timeout = 300      # Seconds to wait for PIN before pixie fails
        Configuration.wps_pixie_step_timeout = 30  # Seconds to wait for a step to change before pixie fails
        Configuration.wps_max_retries = 20 # Retries before failing
        Configuration.wps_fail_threshold = 30  # Max number of failures
        Configuration.wps_timeout_threshold = 30  # Max number of timeouts
        Configuration.wps_skip_rate_limit = True # Skip rate-limited WPS APs

        # Commands
        Configuration.show_cracked = False
        Configuration.check_handshake = None
        Configuration.crack_handshake = False

        # Overwrite config values with arguments (if defined)
        Configuration.load_from_arguments()

        if load_interface:
            Configuration.get_interface()


    @staticmethod
    def get_interface():
        if Configuration.interface == None:
            # Interface wasn't defined, select it!
            from Airmon import Airmon
            Configuration.interface = Airmon.ask()
            if Configuration.random_mac:
                Macchanger.random()


    @staticmethod
    def load_from_arguments():
        ''' Sets configuration values based on Argument.args object '''
        from Arguments import Arguments

        args = Arguments(Configuration).args
        if args.random_mac:
            Configuration.random_mac = True
            Color.pl('{+} {C}option:{W} using {G}random mac address{W} when scanning & attacking')
        if args.channel:
            Configuration.target_channel = args.channel
            Color.pl('{+} {C}option:{W} scanning for targets on channel {G}%s{W}' % args.channel)
        if args.interface:
            Configuration.interface = args.interface
            Color.pl('{+} {C}option:{W} using wireless interface {G}%s{W}' % args.interface)
        if args.target_bssid:
            Configuration.target_bssid = args.target_bssid
            Color.pl('{+} {C}option:{W} targeting BSSID {G}%s{W}' % args.target_bssid)
        if args.five_ghz == True:
            Configuration.five_ghz = True
            Color.pl('{+} {C}option:{W} including {G}5Ghz networks{W} in scans')
        if args.no_deauth == True:
            Configuration.no_deauth = True
            Color.pl('{+} {C}option:{W} will {R}not{W} {O}deauth{W} clients during scans or captures')
        if args.num_deauths and args.num_deauths > 0:
            Configuration.num_deauths = args.num_deauths
            Color.pl('{+} {C}option:{W} will send {G}%d{W} deauth packets when deauthing' % Configuration.num_deauths)
        if args.target_essid:
            Configuration.target_essid = args.target_essid
            Color.pl('{+} {C}option:{W} targeting ESSID {G}%s{W}' % args.target_essid)
        if args.verbose:
            Configuration.verbose = args.verbose
            Color.pl('{+} {C}option:{W} verbosity level {G}%d{W}' % args.verbose)


        # WEP
        if args.wep_filter:
            Configuration.wep_filter = args.wep_filter
        if args.wep_pps:
            Configuration.wep_pps = args.wep_pps
            Color.pl('{+} {C}option:{W} using {G}%d{W} packets-per-second on WEP attacks' % args.wep_pps)
        if args.wep_timeout:
            Configuration.wep_timeout = args.wep_timeout
            Color.pl('{+} {C}option:{W} WEP attack timeout set to {G}%d seconds{W}' % args.wep_timeout)
        if args.require_fakeauth:
            Configuration.require_fakeauth = True
            Color.pl('{+} {C}option:{W} fake-authentication is {G}required{W} for WEP attacks')
        if args.wep_crack_at_ivs:
            Configuration.wep_crack_at_ivs = args.wep_crack_at_ivs
            Color.pl('{+} {C}option:{W} will start cracking WEP keys at {G}%d IVs{W}' % args.wep_crack_at_ivs)
        if args.wep_restart_stale_ivs:
            Configuration.wep_restart_stale_ivs = args.wep_restart_stale_ivs
            Color.pl('{+} {C}option:{W} will restart aireplay after {G}%d seconds{W} of no new IVs' % args.wep_restart_stale_ivs)
        if args.wep_restart_aircrack:
            Configuration.wep_restart_aircrack = args.wep_restart_aircrack
            Color.pl('{+} {C}option:{W} will restart aircrack every {G}%d seconds{W}' % args.wep_restart_aircrack)

        # WPA
        if args.wpa_filter:
            Configuration.wpa_filter = args.wpa_filter
        if args.wordlist:
            if os.path.exists(args.wordlist):
                Configuration.wordlist = args.wordlist
                Color.pl('{+} {C}option:{W} using wordlist {G}%s{W} to crack WPA handshakes' % args.wordlist)
            else:
                Configuration.wordlist = None
                Color.pl('{+} {C}option:{O} wordlist {R}%s{O} was not found, wifite will NOT attempt to crack handshakes' % args.wordlist)
        if args.wpa_deauth_timeout:
            Configuration.wpa_deauth_timeout = args.wpa_deauth_timeout
            Color.pl('{+} {C}option:{W} will deauth WPA clients every {G}%d seconds{W}' % args.wpa_deauth_timeout)
        if args.wpa_attack_timeout:
            Configuration.wpa_attack_timeout = args.wpa_attack_timeout
            Color.pl('{+} {C}option:{W} will stop WPA handshake capture after {G}%d seconds{W}' % args.wpa_attack_timeout)
        if args.wpa_handshake_dir:
            Configuration.wpa_handshake_dir = args.wpa_handshake_dir
            Color.pl('{+} {C}option:{W} will store handshakes to {G}%s{W}' % args.wpa_handshake_dir)
        if args.wpa_strip_handshake:
            Configuration.wpa_strip_handshake = True
            Color.pl("{+} {C}option:{W} will {G}strip{W} non-handshake packets")

        # WPS
        if args.wps_filter:
            Configuration.wps_filter  = args.wps_filter
        if args.reaver_only:
            Configuration.reaver_only = args.reaver_only
            Color.pl('{+} {C}option:{W} will *only* use {G}reaver{W} to attack WPA targets')
        if args.no_reaver:
            Configuration.no_reaver   = args.no_reaver
            Color.pl('{+} {C}option:{W} will *never* use {G}reaver{W} to attack WPA targets')
        if args.pixie_only:
            Configuration.pixie_only  = args.pixie_only
            Color.pl('{+} {C}option:{W} will only use {G}WPS pixie-dust attack{W} on WPS targets')
        if args.wps_pixie_timeout:
            Configuration.wps_pixie_timeout = args.wps_pixie_timeout
            Color.pl('{+} {C}option:{W} WPS pixie-dust attack will timeout after {G}%d seconds{W}' % args.wps_pixie_timeout)
        if args.wps_pixie_step_timeout:
            Configuration.wps_pixie_step_timeout = args.wps_pixie_step_timeout
            Color.pl('{+} {C}option:{W} Any step in the pixie-dust attack will timeout after {G}%d seconds{W}' % args.wps_pixie_step_timeout)
        if args.wps_pin_timeout:
            Configuration.wps_pin_timeout = args.wps_pin_timeout
            Color.pl('{+} {C}option:{W} WPS PIN attack will timeout after {G}%d seconds{W}' % args.wps_pin_timeout)
        if args.wps_max_retries:
            Configuration.wps_max_retries = args.wps_max_retries
            Color.pl('{+} {C}option:{W} will stop WPS attack after {G}%d retries{W}' % args.wps_max_retries)
        if args.wps_fail_threshold:
            Configuration.wps_fail_threshold = args.wps_fail_threshold
            Color.pl('{+} {C}option:{W} will stop WPS attack after {G}%d failures{W}' % args.wps_fail_threshold)
        if args.wps_timeout_threshold:
            Configuration.wps_timeout_threshold = args.wps_timeout_threshold
            Color.pl('{+} {C}option:{W} will stop WPS attack after {G}%d timeouts{W}' % args.wps_timeout_threshold)
        if args.wps_skip_rate_limit == False:
            Configuration.wps_skip_rate_limit = False
            Color.pl('{+} {C}option:{W} will {G}continue{W} WPS attacks when rate-limited')

        # Adjust encryption filter
        Configuration.encryption_filter = []
        if Configuration.wep_filter: Configuration.encryption_filter.append('WEP')
        if Configuration.wpa_filter: Configuration.encryption_filter.append('WPA')
        if Configuration.wps_filter: Configuration.encryption_filter.append('WPS')

        if len(Configuration.encryption_filter) == 3:
            Color.pl('{+} {C}option:{W} targeting {G}all encrypted networks{W}')
        elif len(Configuration.encryption_filter) == 0:
            # Default to scan all types
            Configuration.encryption_filter = ['WEP', 'WPA', 'WPS']
        else:
            Color.pl('{+} {C}option:{W} ' +
                     'targeting {G}%s-encrypted{W} networks'
                        % '/'.join(Configuration.encryption_filter))

        # Adjust WEP attack list
        Configuration.wep_attacks = []
        import sys
        seen = set()
        for arg in sys.argv:
            if arg in seen: continue
            seen.add(arg)
            if arg == '-arpreplay':  Configuration.wep_attacks.append('replay')
            if arg == '-fragment':   Configuration.wep_attacks.append('fragment')
            if arg == '-chopchop':   Configuration.wep_attacks.append('chopchop')
            if arg == '-caffelatte': Configuration.wep_attacks.append('caffelatte')
            if arg == '-p0841':      Configuration.wep_attacks.append('p0841')
            if arg == '-hirte':      Configuration.wep_attacks.append('hirte')

        if len(Configuration.wep_attacks) == 0:
            # Use all attacks
            Configuration.wep_attacks = ['replay',
                                         'fragment',
                                         'chopchop',
                                         'caffelatte',
                                         'p0841',
                                         'hirte']
        elif len(Configuration.wep_attacks) > 0:
            Color.pl('{+} {C}option:{W} using {G}%s{W} WEP attacks'
                % '{W}, {G}'.join(Configuration.wep_attacks))

        # Commands
        if args.cracked: Configuration.show_cracked = True
        if args.check_handshake: Configuration.check_handshake = args.check_handshake
        if args.crack_handshake: Configuration.crack_handshake = True


    @staticmethod
    def temp(subfile=''):
        ''' Creates and/or returns the temporary directory '''
        if Configuration.temp_dir == None:
            Configuration.temp_dir = Configuration.create_temp()
        return Configuration.temp_dir + subfile

    @staticmethod
    def create_temp():
        ''' Creates and returns a temporary directory '''
        from tempfile import mkdtemp
        tmp = mkdtemp(prefix='wifite')
        if not tmp.endswith(os.sep):
            tmp += os.sep
        return tmp

    @staticmethod
    def delete_temp():
        ''' Remove temp files and folder '''
        if Configuration.temp_dir == None: return
        if os.path.exists(Configuration.temp_dir):
            for f in os.listdir(Configuration.temp_dir):
                os.remove(Configuration.temp_dir + f)
            os.rmdir(Configuration.temp_dir)


    @staticmethod
    def exit_gracefully(code=0):
        ''' Deletes temp and exist with the given code '''
        Configuration.delete_temp()
        Macchanger.reset_if_changed()
        from Airmon import Airmon
        if hasattr(Configuration, "interface") and Configuration.interface is not None and Airmon.base_interface is not None:
            Airmon.stop(Configuration.interface)
            Airmon.put_interface_up(Airmon.base_interface)
            Airmon.start_network_manager()
        exit(code)

    @staticmethod
    def dump():
        ''' (Colorful) string representation of the configuration '''
        from Color import Color

        max_len = 20
        for key in Configuration.__dict__.keys():
            max_len = max(max_len, len(key))

        result  = Color.s('{W}%s  Value{W}\n' % 'Configuration Key'.ljust(max_len))
        result += Color.s('{W}%s------------------{W}\n' % ('-' * max_len))

        for (key,val) in sorted(Configuration.__dict__.iteritems()):
            if key.startswith('__'): continue
            if type(val) == staticmethod: continue
            if val == None: continue
            result += Color.s("{G}%s {W} {C}%s{W}\n" % (key.ljust(max_len),val))
        return result

if __name__ == '__main__':
    Configuration.initialize(False)
    print Configuration.dump()
