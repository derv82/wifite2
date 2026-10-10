#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WEP-specific argument parser."""

from ...util.color import Color


def parse_wep_args(cls, args):
    """Parses WEP-specific arguments"""
    if args.wep_filter:
        cls.wep_filter = args.wep_filter

    if args.wep_pps:
        cls.wep_pps = args.wep_pps
        Color.pl('{+} {C}option:{W} using {G}%d{W} packets/sec on WEP attacks' % args.wep_pps)

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
        Color.pl('{+} {C}option:{W} will restart aireplay after {G}%d seconds{W} of no new IVs'
                 % args.wep_restart_stale_ivs)

    if args.wep_restart_aircrack:
        cls.wep_restart_aircrack = args.wep_restart_aircrack
        Color.pl('{+} {C}option:{W} will restart aircrack every {G}%d seconds{W}' % args.wep_restart_aircrack)

    if args.wep_keep_ivs:
        cls.wep_keep_ivs = args.wep_keep_ivs
        Color.pl('{+} {C}option:{W} keep .ivs files across multiple WEP attacks')
