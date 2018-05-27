#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import os

from .util.color import Color
from .util.input import raw_input
from .tools.iwconfig import Iwconfig
from .tools.macchanger import Macchanger

class Configuration(object):
    ''' Stores configuration variables and functions for Wifite. '''
    version = '2.1.5'

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
        cls.all_targets = False # Run attacks against all targets automatically

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
        cls.eviltwin_iface = None

        # WEP variables
        cls.wep_filter = False # Only attack WEP networks
        cls.wep_pps = 600 # Packets per second
        cls.wep_timeout = 600 # Seconds to wait before failing
        cls.wep_crack_at_ivs = 10000 # Minimum IVs to start cracking
        cls.require_fakeauth = False
        cls.wep_restart_stale_ivs = 11 # Seconds to wait before restarting
                                                 # Aireplay if IVs don't increaes.
                                                 # "0" means never restart.
        cls.wep_restart_aircrack = 30  # Seconds to give aircrack to crack
                                                 # before restarting the process.
        cls.wep_crack_at_ivs = 10000   # Number of IVS to start cracking
        cls.wep_keep_ivs = False       # Retain .ivs files across multiple attacks.

        # WPA variables
        cls.wpa_filter = False # Only attack WPA networks
        cls.wpa_deauth_timeout = 15 # Wait time between deauths
        cls.wpa_attack_timeout = 500 # Wait time before failing
        cls.wpa_handshake_dir = "hs" # Dir to store handshakes
        cls.wpa_strip_handshake = False # Strip non-handshake packets
        cls.ignore_old_handshakes = False # Always fetch a new handshake

        # Default dictionary for cracking
        cls.wordlist = None
        wordlists = [
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
    def get_eviltwin_interface(cls):
        if cls.eviltwin_iface is None:
            Color.pl('\n{+} {G}Evil Twin attack{W}')
            Color.p('{+} looking for wireless interfaces in "Managed" mode... ')

            ifaces = Iwconfig.get_interfaces(mode='Managed')

            if len(ifaces) == 0:
                Color.pl('\n{!} {O}no other wireless interfaces in "Managed" mode!{W}')
                raise Exception('eviltwin attack requires two wireless cards (1 monitor-mode, 1 managed-mode)')

            Color.clear_entire_line()

            while True:
                # Ask user to select eviltwin interface
                Color.pl('     select the interface for the {C}evil twin{W} access point:')
                for index, iface in enumerate(ifaces, start=1):
                    Color.pl('       {G}%d{W}. {C}%s{W}' % (index, iface))

                question = '{+} enter number ({G}'
                if len(ifaces) == 1:
                    question += '1'
                else:
                    question += '1-%d' % len(ifaces)
                question += '{W}): '
                selection = raw_input(Color.s(question))

                if selection.strip() in ifaces:
                    selection = str(ifaces.index(selection.strip()) + 1)

                elif not selection.isdigit():
                    Color.pl('\n{!} {O}selection must be numeric{W}')
                    continue

                selection = int(selection)

                if selection < 1 or selection > len(ifaces):
                    Color.pl('\n{!} {O}selection must be between {R}1{O} and {R}%d{W}' % len(ifaces))
                    continue

                break

            cls.eviltwin_iface = ifaces[selection - 1]

        return cls.eviltwin_iface

    @classmethod
    def load_from_arguments(cls):
        ''' Sets configuration values based on Argument.args object '''
        from .args import Arguments

        args = Arguments(cls).args
        if args.random_mac:
            cls.random_mac = True
            Color.pl('{+} {C}option:{W} using {G}random mac address{W} when scanning & attacking')
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
            Color.pl('{+} {C}option:{W} including {G}5Ghz networks{W} in scans')
        if args.show_bssids == True:
            cls.show_bssids = True
            Color.pl('{+} {C}option:{W} showing {G}bssids{W} of targets during scan')
        if args.no_deauth == True:
            cls.no_deauth = True
            Color.pl('{+} {C}option:{W} will {R}not{W} {O}deauth{W} clients during scans or captures')
        if args.num_deauths and args.num_deauths > 0:
            cls.num_deauths = args.num_deauths
            Color.pl('{+} {C}option:{W} will send {G}%d{W} deauth packets when deauthing' % cls.num_deauths)
        if args.target_essid:
            cls.target_essid = args.target_essid
            Color.pl('{+} {C}option:{W} targeting ESSID {G}%s{W}' % args.target_essid)
        if args.ignore_essid is not None:
            cls.ignore_essid = args.ignore_essid
            Color.pl('{+} {C}option:{W} {O}ignoring ESSIDs that include {R}%s{W}' % args.ignore_essid)
        if args.clients_only == True:
            cls.clients_only = True
            Color.pl('{+} {C}option:{W} {O}ignoring targets that do not have associated clients')
        if args.scan_time:
            cls.scan_time = args.scan_time
            Color.pl('{+} {C}option:{W} ({G}pillage{W}) attack all targets after {G}%d{W}s' % args.scan_time)
        if args.verbose:
            cls.verbose = args.verbose
            Color.pl('{+} {C}option:{W} verbosity level {G}%d{W}' % args.verbose)
        if args.kill_conflicting_processes:
            cls.kill_conflicting_processes = True
            Color.pl('{+} {C}option:{W} kill conflicting processes {G}enabled{W}')


        # EvilTwin
        if args.eviltwin_iface:
            # Check that eviltwin_iface exists in iwconfig
            existing_ifaces = Iwconfig.get_interfaces()
            if args.eviltwin_iface not in existing_ifaces:
                raise Exception('Interface "%s" was not found by iwconfig (found %s)' % (args.eviltwin_iface, ','.join(existing_ifaces)))
            # TODO: Put device into managed mode?

            cls.eviltwin_iface = args.eviltwin_iface
            Color.pl('{+} {C}option:{W} using {G}%s{W} to create fake AP for evil twin attacks' % cls.eviltwin_iface)

        if args.use_eviltwin:
            # TODO: Or ask user to select a different wireless device?
            cls.use_eviltwin = True
            Color.pl('{+} {C}option:{W} attacking all targets using {G}eviltwin attacks{W}')


        # WEP
        if args.wep_filter:
            cls.wep_filter = args.wep_filter
        if args.wep_pps:
            cls.wep_pps = args.wep_pps
            Color.pl('{+} {C}option:{W} using {G}%d{W} packets-per-second on WEP attacks' % args.wep_pps)
        if args.wep_timeout:
            cls.wep_timeout = args.wep_timeout
            Color.pl('{+} {C}option:{W} WEP attack timeout set to {G}%d seconds{W}' % args.wep_timeout)
        if args.require_fakeauth:
            cls.require_fakeauth = True
            Color.pl('{+} {C}option:{W} fake-authentication is {G}required{W} for WEP attacks')
        if args.wep_crack_at_ivs:
            cls.wep_crack_at_ivs = args.wep_crack_at_ivs
            Color.pl('{+} {C}option:{W} will start cracking WEP keys at {G}%d IVs{W}' % args.wep_crack_at_ivs)
        if args.wep_restart_stale_ivs:
            cls.wep_restart_stale_ivs = args.wep_restart_stale_ivs
            Color.pl('{+} {C}option:{W} will restart aireplay after {G}%d seconds{W} of no new IVs' % args.wep_restart_stale_ivs)
        if args.wep_restart_aircrack:
            cls.wep_restart_aircrack = args.wep_restart_aircrack
            Color.pl('{+} {C}option:{W} will restart aircrack every {G}%d seconds{W}' % args.wep_restart_aircrack)
        if args.wep_keep_ivs:
            cls.wep_keep_ivs = args.wep_keep_ivs
            Color.pl('{+} {C}option:{W} keep .ivs files across multiple WEP attacks')

        # WPA
        if args.wpa_filter:
            cls.wpa_filter = args.wpa_filter
        if args.wordlist:
            if os.path.exists(args.wordlist):
                cls.wordlist = args.wordlist
                Color.pl('{+} {C}option:{W} using wordlist {G}%s{W} to crack WPA handshakes' % args.wordlist)
            else:
                cls.wordlist = None
                Color.pl('{+} {C}option:{O} wordlist {R}%s{O} was not found, wifite will NOT attempt to crack handshakes' % args.wordlist)
        if args.wpa_deauth_timeout:
            cls.wpa_deauth_timeout = args.wpa_deauth_timeout
            Color.pl('{+} {C}option:{W} will deauth WPA clients every {G}%d seconds{W}' % args.wpa_deauth_timeout)
        if args.wpa_attack_timeout:
            cls.wpa_attack_timeout = args.wpa_attack_timeout
            Color.pl('{+} {C}option:{W} will stop WPA handshake capture after {G}%d seconds{W}' % args.wpa_attack_timeout)
        if args.ignore_old_handshakes:
            cls.ignore_old_handshakes = True
            Color.pl("{+} {C}option:{W} will {O}ignore{W} existing handshakes (force capture)")
        if args.wpa_handshake_dir:
            cls.wpa_handshake_dir = args.wpa_handshake_dir
            Color.pl('{+} {C}option:{W} will store handshakes to {G}%s{W}' % args.wpa_handshake_dir)
        if args.wpa_strip_handshake:
            cls.wpa_strip_handshake = True
            Color.pl("{+} {C}option:{W} will {G}strip{W} non-handshake packets")

        # WPS
        if args.wps_filter:
            cls.wps_filter = args.wps_filter
        if args.wps_only:
            cls.wps_only = True
            Color.pl('{+} {C}option:{W} will *only* attack non-WEP networks with {G}WPS attacks{W} (no handshake capture)')
        if args.no_wps:
            cls.no_wps = args.no_wps
            Color.pl('{+} {C}option:{W} will {O}never{W} use {C}WPS attacks{W} (Pixie-Dust/PIN) on targets')
        if args.use_bully:
            cls.use_bully = args.use_bully
            Color.pl('{+} {C}option:{W} use {C}bully{W} instead of {C}reaver{W} for WPS Attacks')
        if args.wps_pixie_timeout:
            cls.wps_pixie_timeout = args.wps_pixie_timeout
            Color.pl('{+} {C}option:{W} WPS pixie-dust attack will fail after {O}%d seconds{W}' % args.wps_pixie_timeout)
        if args.wps_fail_threshold:
            cls.wps_fail_threshold = args.wps_fail_threshold
            Color.pl('{+} {C}option:{W} will stop WPS attack after {O}%d failures{W}' % args.wps_fail_threshold)
        if args.wps_timeout_threshold:
            cls.wps_timeout_threshold = args.wps_timeout_threshold
            Color.pl('{+} {C}option:{W} will stop WPS attack after {O}%d timeouts{W}' % args.wps_timeout_threshold)

        # Adjust encryption filter
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

        # Adjust WEP attack list
        cls.wep_attacks = []
        import sys
        seen = set()
        for arg in sys.argv:
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
                                         'hirte']
        elif len(cls.wep_attacks) > 0:
            Color.pl('{+} {C}option:{W} using {G}%s{W} WEP attacks'
                % '{W}, {G}'.join(cls.wep_attacks))

        # Commands
        if args.cracked: cls.show_cracked = True
        if args.check_handshake: cls.check_handshake = args.check_handshake
        if args.crack_handshake: cls.crack_handshake = True


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
            Color.pl('{!} Leaving interface {C}%s{W} in Monitor Mode.' % cls.interface)
            Color.pl('{!} You can disable Monitor Mode when finished ({C}airmon-ng stop %s{W})' % cls.interface)

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
            if key.startswith('__') or type(val) == staticmethod or val is None:
                continue
            result += Color.s("{G}%s {W} {C}%s{W}\n" % (key.ljust(max_len),val))
        return result

if __name__ == '__main__':
    Configuration.initialize(False)
    print(Configuration.dump())
