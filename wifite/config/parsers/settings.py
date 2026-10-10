#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""General settings argument parser and encryption/WEP-attack helpers."""

import os
import re

from ...util.color import Color


def parse_settings_args(cls, args):
    """Parses basic settings/configurations from arguments."""

    if getattr(args, 'kalidroid', False):
        cls.kalidroid = True
        Color.kalidroid = True  # already set early in Arguments.__init__; keep in sync
        Color.pl('{+} {C}option:{W} {G}Kalidroid MiniTerminal{W} output mode enabled')

    if args.random_mac or args.random_mac_vendor:
        if args.random_mac and args.random_mac_vendor:
            Color.pl('{!} {O}Warning: Cannot use both --random-mac and --random-mac-vendor')
            Color.pl('{+} {W}Falling back to {C}--random-mac{W} (full random) for better privacy')
            args.random_mac_vendor = False

        if args.random_mac:
            cls.random_mac = True
            cls.random_mac_vendor = False
            mode_str = "full random (maximum privacy)"
        else:
            cls.random_mac_vendor = True
            cls.random_mac = False
            mode_str = "vendor-preserved (better compatibility)"

        Color.pl('{+} {C}option:{W} using {G}random MAC address{W} ({C}%s{W}) when scanning & attacking' % mode_str)

    if args.channel:
        chn_arg_re = re.compile(r"^\d+((,\d+)|(-\d+,\d+))*(-\d+)?$")
        if not chn_arg_re.match(args.channel):
            raise ValueError("Invalid channel! The format must be 1,3-6,9")

        cls.target_channel = args.channel
        Color.pl('{+} {C}option:{W} scanning for targets on channel {G}%s{W}' % args.channel)

    if args.interface:
        cls._validate_interface_name(args.interface)
        cls.interface = args.interface
        Color.pl('{+} {C}option:{W} using wireless interface {G}%s{W}' % args.interface)

    if args.target_bssid:
        cls.target_bssid = args.target_bssid
        Color.pl('{+} {C}option:{W} targeting BSSID {G}%s{W}' % args.target_bssid)

    if args.all_bands:
        cls.all_bands = True
        Color.pl('{+} {C}option:{W} including both {G}2.4Ghz and 5Ghz networks{W} in scans')

    if args.two_ghz:
        cls.two_ghz = True
        Color.pl('{+} {C}option:{W} including {G}2.4Ghz networks{W} in scans')

    if args.five_ghz:
        cls.five_ghz = True
        Color.pl('{+} {C}option:{W} including {G}5Ghz networks{W} in scans')

    if args.infinite_mode:
        cls.infinite_mode = True
        Color.p('{+} {C}option:{W} ({G}infinite{W}) attack all neighbors forever')
        if not args.scan_time:
            Color.p(f'; {{O}}pillage time not selected{{W}}, using default {{G}}{cls.inf_wait_time:d}{{W}}s')
            args.scan_time = cls.inf_wait_time
        Color.pl('')

    if args.show_bssids:
        cls.show_bssids = True
        Color.pl('{+} {C}option:{W} showing {G}bssids{W} of targets during scan')

    if args.show_manufacturers is True:
        cls.show_manufacturers = True
        Color.pl('{+} {C}option:{W} showing {G}manufacturers{W} of targets during scan')

    if getattr(args, 'detect_honeypots', False):
        cls.detect_honeypots = True
        Color.pl('{+} {C}option:{W} detecting {G}honeypot/rogue APs{W} via beacon anomalies')

    if args.no_deauth:
        cls.no_deauth = True
        Color.pl('{+} {C}option:{W} will {R}not{W} {O}deauth{W} clients during scans or captures')

    if args.daemon is True:
        cls.daemon = True
        Color.pl('{+} {C}option:{W} will put interface back to managed mode')

    if args.num_deauths and args.num_deauths > 0:
        cls.num_deauths = args.num_deauths
        Color.pl(f'{{+}} {{C}}option:{{W}} send {{G}}{cls.num_deauths:d}{{W}} deauth packets when deauthing')

    if args.min_power and args.min_power > 0:
        cls.min_power = args.min_power
        Color.pl(f'{{+}} {{C}}option:{{W}} Minimum power {{G}}{cls.min_power:d}{{W}} for target to be shown')

    if args.skip_crack:
        cls.skip_crack = True
        Color.pl('{+} {C}option:{W} Skip cracking captured handshakes/pmkid {G}enabled{W}')

    if args.attack_max and args.attack_max > 0:
        cls.attack_max = args.attack_max
        Color.pl(f'{{+}} {{C}}option:{{W}} Attack first {{G}}{cls.attack_max:d}{{W}} targets from list')

    if args.target_essid:
        cls.target_essid = args.target_essid
        Color.pl('{+} {C}option:{W} targeting ESSID {G}%s{W}' % args.target_essid)

    if args.ignore_essids is not None:
        cls.ignore_essids = args.ignore_essids
        Color.pl('{+} {C}option: {O}ignoring ESSID(s): {R}%s{W}' %
                 ', '.join(args.ignore_essids))

    if args.ignore_essids_file is not None:
        try:
            # Try UTF-8 first (strict), fall back to latin-1 which accepts all byte values
            try:
                with open(args.ignore_essids_file, 'r', encoding='utf-8') as fh:
                    file_essids = [line.strip() for line in fh if line.strip() and not line.startswith('#')]
            except UnicodeDecodeError:
                Color.pl('{!} {O}ignore-essids-file is not valid UTF-8, trying latin-1{W}')
                with open(args.ignore_essids_file, 'r', encoding='latin-1') as fh:
                    file_essids = [line.strip() for line in fh if line.strip() and not line.startswith('#')]
            if file_essids:
                cls.ignore_essids = list(set((cls.ignore_essids or []) + file_essids))
                Color.pl('{+} {C}option: {O}ignoring {R}%d{O} ESSID(s) from file {R}%s{W}' %
                         (len(file_essids), args.ignore_essids_file))
            else:
                Color.pl('{!} {O}ignore-essids-file {R}%s{O} is empty or has only comments{W}' %
                         args.ignore_essids_file)
        except (OSError, IOError) as e:
            Color.pl('{!} {R}Could not read ignore-essids-file {O}%s{R}: %s{W}' %
                     (args.ignore_essids_file, str(e)))

    from ...model.result import CrackResult
    cls.ignore_cracked = CrackResult.load_ignored_bssids(args.ignore_cracked)

    if args.ignore_cracked:
        if cls.ignore_cracked:
            Color.pl('{+} {C}option: {O}ignoring {R}%s{O} previously-cracked targets' % len(cls.ignore_cracked))

        else:
            Color.pl('{!} {R}Previously-cracked access points not found in %s' % cls.cracked_file)
            cls.ignore_cracked = False

    if args.ignore_captured:
        captured_bssids = CrackResult.load_captured_bssids(cls.wpa_handshake_dir)
        if captured_bssids:
            cls.ignore_captured = captured_bssids
            Color.pl('{+} {C}option: {O}ignoring {R}%s{O} targets with existing captures' % len(captured_bssids))
        else:
            Color.pl('{!} {R}No captured handshakes/PMKIDs found in %s' % cls.wpa_handshake_dir)

    if args.clients_only:
        cls.clients_only = True
        Color.pl('{+} {C}option:{W} {O}ignoring targets that do not have associated clients')

    if args.scan_time:
        cls.scan_time = args.scan_time
        Color.pl(
            f'{{+}} {{C}}option:{{W}} ({{G}}pillage{{W}}) attack all targets after {{G}}{args.scan_time:d}{{W}}s')

    # TUI settings
    if hasattr(args, 'use_tui') and args.use_tui:
        cls.use_tui = True
        Color.pl('{+} {C}option:{W} using {G}interactive TUI mode{W}')
    elif hasattr(args, 'no_tui') and args.no_tui:
        cls.use_tui = False
        Color.pl('{+} {C}option:{W} using {G}classic text mode{W} (TUI disabled)')
    # else: use_tui remains False (classic mode is default)

    # --debug is shorthand for -vvv + file logging
    if args.debug:
        args.verbose = max(args.verbose, 3)

    if args.verbose:
        cls.verbose = args.verbose
        Color.pl('{+} {C}option:{W} verbosity level {G}%d{W}' % args.verbose)

        # Determine log file: explicit --log-file wins, then --debug default, then -vv+ default
        from ...util.logger import Logger
        log_file = getattr(args, 'log_file', None)
        if log_file is None and args.verbose >= 2:
            log_file = os.path.join(os.path.expanduser('~'), '.wifite', 'wifite.log')
        if log_file:
            Color.pl('{+} {C}option:{W} logging to {G}%s{W}' % log_file)
        Logger.initialize(log_file=log_file, verbose=args.verbose, enabled=True)
    elif getattr(args, 'log_file', None):
        # --log-file without -v: enable at least verbose=2 so the log is useful
        cls.verbose = max(cls.verbose, 2)
        from ...util.logger import Logger
        Color.pl('{+} {C}option:{W} logging to {G}%s{W} (verbose level raised to 2)' % args.log_file)
        Logger.initialize(log_file=args.log_file, verbose=cls.verbose, enabled=True)

    if args.kill_conflicting_processes:
        cls.kill_conflicting_processes = True
        Color.pl('{+} {C}option:{W} kill conflicting processes {G}enabled{W}')


def parse_encryption(cls):
    """Adjusts encryption filter (WEP and/or WPA and/or WPS)"""
    cls.encryption_filter = []
    if cls.wep_filter:
        cls.encryption_filter.append('WEP')
    if cls.wpa_filter:  # WPA/WPA2
        cls.encryption_filter.append('WPA')
    if cls.wpa3_filter or cls.wpa3_only:
        cls.encryption_filter.append('WPA3')
    if cls.owe_filter:
        cls.encryption_filter.append('OWE')
    if cls.wps_filter:  # WPS can be on WPA/WPA2
        cls.encryption_filter.append('WPS')

    cls.encryption_filter = sorted(list(set(cls.encryption_filter)))  # Remove duplicates and sort

    if not cls.encryption_filter:
        # Default to scan all known types if no specific filter is chosen
        cls.encryption_filter = ['WEP', 'WPA', 'WPA3', 'OWE', 'WPS']
        Color.pl('{+} {C}option:{W} targeting {G}all known encryption types{W} by default')
    elif len(cls.encryption_filter) == 5 and 'WPS' in cls.encryption_filter and 'OWE' in cls.encryption_filter:
        Color.pl('{+} {C}option:{W} targeting {G}all specified encrypted networks{W}')
    else:
        Color.pl('{+} {C}option:{W} targeting {G}%s-encrypted{W} networks' % '/'.join(cls.encryption_filter))


def parse_wep_attacks(cls):
    """Parses and sets WEP-specific args (-chopchop, -fragment, etc)"""
    cls.wep_attacks = []
    from sys import argv
    seen = set()
    for arg in argv:
        if arg in seen:
            continue
        seen.add(arg)
        if arg == '-arpreplay':
            cls.wep_attacks.append('replay')
        elif arg == '-caffelatte':
            cls.wep_attacks.append('caffelatte')
        elif arg == '-chopchop':
            cls.wep_attacks.append('chopchop')
        elif arg == '-fragment':
            cls.wep_attacks.append('fragment')
        elif arg == '-hirte':
            cls.wep_attacks.append('hirte')
        elif arg == '-p0841':
            cls.wep_attacks.append('p0841')
    if not cls.wep_attacks:
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
