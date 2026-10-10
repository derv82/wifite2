#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PMKID-specific argument parser."""

from ...util.color import Color


def parse_pmkid_args(cls, args):
    """Parses PMKID-specific arguments"""
    if args.use_pmkid_only:
        cls.use_pmkid_only = True
        Color.pl('{+} {C}option:{W} will ONLY use {C}PMKID{W} attack on WPA networks')

    if args.pmkid_timeout:
        cls.pmkid_timeout = args.pmkid_timeout
        Color.pl('{+} {C}option:{W} will wait {G}%d seconds{W} during {C}PMKID{W} capture' % args.pmkid_timeout)

    if args.dont_use_pmkid:
        cls.dont_use_pmkid = True
        Color.pl('{+} {C}option:{W} will NOT use {C}PMKID{W} attack on WPA networks')

    # Passive PMKID capture arguments
    if args.pmkid_passive:
        cls.pmkid_passive = True
        Color.pl('{+} {C}option:{W} {G}passive PMKID capture mode{W} enabled')

    if args.pmkid_passive_duration:
        cls.pmkid_passive_duration = args.pmkid_passive_duration
        Color.pl('{+} {C}option:{W} passive capture duration: {G}%d seconds{W}' % args.pmkid_passive_duration)

    if args.pmkid_passive_interval:
        cls.pmkid_passive_interval = args.pmkid_passive_interval
        Color.pl('{+} {C}option:{W} passive capture extraction interval: {G}%d seconds{W}' % args.pmkid_passive_interval)
