#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WPA/WPA2/WPA3-specific argument parser."""

import os

from ...util.color import Color


def parse_wpa_args(cls, args):
    """Parses WPA-specific arguments"""
    if args.wpa_filter:
        cls.wpa_filter = args.wpa_filter

    if hasattr(args, 'wpa3_filter') and args.wpa3_filter:
        cls.wpa3_filter = args.wpa3_filter

    if hasattr(args, 'owe_filter') and args.owe_filter:
        cls.owe_filter = args.owe_filter

    if args.wordlist:
        if not os.path.exists(args.wordlist):
            cls.wordlist = None
            cls.wordlists = []
            Color.pl('{+} {C}option:{O} wordlist {R}%s{O} was not found, wifite will NOT attempt to crack '
                     'handshakes' % args.wordlist)
        elif os.path.isfile(args.wordlist):
            cls.wordlist = args.wordlist
            cls.wordlists = [args.wordlist]
            Color.pl('{+} {C}option:{W} using wordlist {G}%s{W} for cracking' % args.wordlist)
        elif os.path.isdir(args.wordlist):
            # Collect all files in the directory as wordlists
            dict_dir = args.wordlist
            files = sorted([
                os.path.join(dict_dir, f)
                for f in os.listdir(dict_dir)
                if os.path.isfile(os.path.join(dict_dir, f))
            ])
            if files:
                cls.wordlists = files
                cls.wordlist = files[0]
                Color.pl('{+} {C}option:{W} using {G}%d{W} wordlist(s) from directory {G}%s{W} for cracking'
                         % (len(files), dict_dir))
            else:
                cls.wordlist = None
                cls.wordlists = []
                Color.pl('{+} {C}option:{O} wordlist directory {R}%s{O} contains no files. Wifite will NOT '
                         'attempt to crack handshakes' % dict_dir)

    if args.wpa_deauth_timeout:
        cls.wpa_deauth_timeout = args.wpa_deauth_timeout
        Color.pl('{+} {C}option:{W} will deauth WPA clients every {G}%d seconds{W}' % args.wpa_deauth_timeout)

    if args.wpa_attack_timeout:
        cls.wpa_attack_timeout = args.wpa_attack_timeout
        Color.pl(
            '{+} {C}option:{W} will stop WPA handshake capture after {G}%d seconds{W}' % args.wpa_attack_timeout)

    # WPA3-specific arguments
    if hasattr(args, 'wpa3_only') and args.wpa3_only:
        cls.wpa3_only = True
        Color.pl('{+} {C}option:{W} will attack {C}WPA3-SAE networks only{W}, skipping WPA2-only targets')

    if hasattr(args, 'wpa3_no_downgrade') and args.wpa3_no_downgrade:
        cls.wpa3_no_downgrade = True
        Color.pl('{+} {C}option:{W} will {O}disable transition mode downgrade{W} attacks, forcing SAE capture')

    if hasattr(args, 'wpa3_force_sae') and args.wpa3_force_sae:
        cls.wpa3_force_sae = True
        Color.pl('{+} {C}option:{W} will {O}skip WPA2 attacks{W} on transition mode, attacking SAE directly')

    if hasattr(args, 'wpa3_check_dragonblood') and args.wpa3_check_dragonblood:
        cls.wpa3_check_dragonblood = True
        Color.pl('{+} {C}option:{W} will {C}scan for Dragonblood vulnerabilities{W} only, skipping attacks')

    if hasattr(args, 'wpa3_attack_timeout') and args.wpa3_attack_timeout:
        cls.wpa3_attack_timeout = args.wpa3_attack_timeout
        Color.pl('{+} {C}option:{W} will stop WPA3-SAE attack after {G}%d seconds{W}' % args.wpa3_attack_timeout)
    else:
        # Default to wpa_attack_timeout if not specified
        cls.wpa3_attack_timeout = cls.wpa_attack_timeout

    if hasattr(args, 'dragonblood_timing') and args.dragonblood_timing:
        cls.dragonblood_timing = True
        Color.pl('{+} {C}option:{W} will use {C}Dragonblood timing attack{W} (CVE-2019-13377) on vulnerable APs')

    if hasattr(args, 'dragonblood_samples') and args.dragonblood_samples:
        cls.dragonblood_samples = args.dragonblood_samples
        Color.pl('{+} {C}option:{W} Dragonblood timing samples per password: {G}%d{W}' % args.dragonblood_samples)

    if hasattr(args, 'dragonblood_max_passwords') and args.dragonblood_max_passwords:
        cls.dragonblood_max_passwords = args.dragonblood_max_passwords
        Color.pl('{+} {C}option:{W} Dragonblood max passwords to probe: {G}%d{W}' % args.dragonblood_max_passwords)

    if args.ignore_old_handshakes:
        cls.ignore_old_handshakes = True
        Color.pl('{+} {C}option:{W} will {O}ignore{W} existing handshakes (force capture)')

    if args.wpa_handshake_dir:
        cls.wpa_handshake_dir = args.wpa_handshake_dir
        Color.pl('{+} {C}option:{W} will store handshakes to {G}%s{W}' % args.wpa_handshake_dir)

    if args.wpa_strip_handshake:
        cls.wpa_strip_handshake = True
        Color.pl('{+} {C}option:{W} will {G}strip{W} non-handshake packets')
