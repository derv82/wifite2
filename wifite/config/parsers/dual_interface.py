#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dual interface-specific argument parser."""

from ...util.color import Color


def parse_dual_interface_args(cls, args):
    """Parses dual interface-specific arguments"""
    # Check if dual interface mode is explicitly enabled
    if hasattr(args, 'dual_interface') and args.dual_interface:
        cls.dual_interface_enabled = True
        Color.pl('{+} {C}option:{W} dual interface mode {G}enabled{W}')

    # Check if dual interface mode is explicitly disabled
    if hasattr(args, 'no_dual_interface') and args.no_dual_interface:
        cls.dual_interface_enabled = False
        cls.prefer_dual_interface = False
        Color.pl('{+} {C}option:{W} dual interface mode {O}disabled{W} (single interface mode)')

    # Manual primary interface selection
    if hasattr(args, 'interface_primary') and args.interface_primary:
        cls._validate_interface_name(args.interface_primary)
        cls.interface_primary = args.interface_primary
        Color.pl('{+} {C}option:{W} primary interface: {G}%s{W}' % args.interface_primary)
        # If primary is specified, enable dual interface mode
        if not hasattr(args, 'no_dual_interface') or not args.no_dual_interface:
            cls.dual_interface_enabled = True

    # Manual secondary interface selection
    if hasattr(args, 'interface_secondary') and args.interface_secondary:
        cls._validate_interface_name(args.interface_secondary)
        cls.interface_secondary = args.interface_secondary
        Color.pl('{+} {C}option:{W} secondary interface: {G}%s{W}' % args.interface_secondary)
        # If secondary is specified, enable dual interface mode
        if not hasattr(args, 'no_dual_interface') or not args.no_dual_interface:
            cls.dual_interface_enabled = True

    # Validate manual interface selection
    if cls.interface_primary and cls.interface_secondary:
        if cls.interface_primary == cls.interface_secondary:
            Color.pl('{!} {R}Error: Primary and secondary interfaces must be different{W}')
            raise ValueError('Primary and secondary interfaces cannot be the same')

    # Auto-assign setting (default is True)
    if hasattr(args, 'no_auto_assign') and args.no_auto_assign:
        cls.auto_assign_interfaces = False
        Color.pl('{+} {C}option:{W} automatic interface assignment {O}disabled{W}')

    # hcxdump mode for WPA capture (single or dual interface)
    if hasattr(args, 'use_hcxdump') and args.use_hcxdump:
        cls.use_hcxdump = True
        Color.pl('{+} {C}option:{W} using {G}hcxdumptool{W} for WPA handshake capture')
