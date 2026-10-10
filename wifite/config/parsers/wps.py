#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WPS-specific argument parser."""

from ...util.color import Color


def parse_wps_args(cls, args):
    """Parses WPS-specific arguments"""
    if args.wps_filter:
        cls.wps_filter = args.wps_filter

    if args.wps_only:
        cls.wps_only = True
        cls.wps_filter = True  # Also only show WPS networks
        Color.pl('{+} {C}option:{W} will *only* attack WPS networks with '
                 '{G}WPS attacks{W} (avoids handshake and PMKID)')

    if args.no_wps:
        # No WPS attacks at all
        cls.no_wps = args.no_wps
        cls.wps_pixie = False
        cls.wps_no_nullpin = True
        cls.wps_pin = False
        Color.pl('{+} {C}option:{W} will {O}never{W} use {C}WPS attacks{W} (Pixie-Dust/PIN) on targets')

    elif args.wps_pixie:
        # WPS Pixie-Dust only
        cls.no_wps = False  # Explicitly ensure WPS attacks are enabled
        cls.wps_pixie = True
        cls.wps_no_nullpin = True
        cls.wps_pin = False
        Color.pl('{+} {C}option:{W} will {G}only{W} use {C}WPS Pixie-Dust attack{W} (no {O}PIN{W}) on targets')

    elif args.wps_no_nullpin:
        # WPS NULL PIN only
        cls.no_wps = False  # Explicitly ensure WPS attacks are enabled
        cls.wps_pixie = True
        cls.wps_no_nullpin = False
        cls.wps_pin = True
        Color.pl('{+} {C}option:{W} will {G}not{W} use {C}WPS NULL PIN attack{W} (no {O}PIN{W}) on targets')

    elif args.wps_no_pixie:
        # WPS PIN only
        cls.no_wps = False  # Explicitly ensure WPS attacks are enabled
        cls.wps_pixie = False
        cls.wps_no_nullpin = True
        cls.wps_pin = True
        Color.pl('{+} {C}option:{W} will {G}only{W} use {C}WPS PIN attack{W} (no {O}Pixie-Dust{W}) on targets')

    if args.use_bully:
        from ...tools.bully import Bully
        if not Bully.exists():
            Color.pl('{!} {R}Bully not found. Defaulting to {O}reaver{W}')
            cls.use_bully = False
        else:
            cls.use_bully = args.use_bully
            Color.pl('{+} {C}option:{W} use {C}bully{W} instead of {C}reaver{W} for WPS Attacks')

    if args.use_reaver:
        from ...tools.reaver import Reaver
        if not Reaver.exists():
            Color.pl('{!} {R}Reaver not found. Defaulting to {O}bully{W}')
            cls.use_reaver = False
        else:
            cls.use_reaver = args.use_reaver
            Color.pl('{+} {C}option:{W} use {C}reaver{W} instead of {C}bully{W} for WPS Attacks')

    if args.wps_pixie_timeout:
        cls.wps_pixie_timeout = args.wps_pixie_timeout
        Color.pl(
            '{+} {C}option:{W} WPS pixie-dust attack will fail after {O}%d seconds{W}' % args.wps_pixie_timeout)

    if args.wps_fail_threshold:
        cls.wps_fail_threshold = args.wps_fail_threshold
        Color.pl('{+} {C}option:{W} will stop WPS attack after {O}%d failures{W}' % args.wps_fail_threshold)

    if args.wps_timeout_threshold:
        cls.wps_timeout_threshold = args.wps_timeout_threshold
        Color.pl('{+} {C}option:{W} will stop WPS attack after {O}%d timeouts{W}' % args.wps_timeout_threshold)

    if args.wps_ignore_lock:
        cls.wps_ignore_lock = True
        Color.pl('{+} {C}option:{W} will {O}ignore{W} WPS lock-outs')
