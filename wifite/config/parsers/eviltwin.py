#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Evil Twin-specific argument parser and interface info helpers."""

from ...util.color import Color


def parse_eviltwin_args(cls, args):
    """Parses Evil Twin-specific arguments"""
    if args.use_eviltwin:
        cls.use_eviltwin = True
        Color.pl('{+} {C}option:{W} using {G}Evil Twin attacks{W} against all targets')

        # Display interface capabilities info
        display_eviltwin_interface_info(cls)

    # --eviltwin-fakeap-iface is an Evil Twin-scoped alias for --interface-primary.
    # Both populate Configuration.interface_primary; specifying both with different
    # values is a configuration error.
    if hasattr(args, 'eviltwin_fakeap_iface') and args.eviltwin_fakeap_iface:
        cls._validate_interface_name(args.eviltwin_fakeap_iface)
        other = getattr(args, 'interface_primary', None)
        if other and other != args.eviltwin_fakeap_iface:
            Color.pl('{!} {R}Error: --eviltwin-fakeap-iface ({O}%s{R}) conflicts with '
                     '--interface-primary ({O}%s{R}){W}'
                     % (args.eviltwin_fakeap_iface, other))
            raise ValueError('Conflicting interface specifications: '
                             '--eviltwin-fakeap-iface vs --interface-primary')
        cls.interface_primary = args.eviltwin_fakeap_iface
        cls.dual_interface_enabled = True
        Color.pl('{+} {C}option:{W} Evil Twin fake AP interface: {G}%s{W}'
                 % args.eviltwin_fakeap_iface)

    # --eviltwin-deauth-iface is an Evil Twin-scoped alias for --interface-secondary.
    if hasattr(args, 'eviltwin_deauth_iface') and args.eviltwin_deauth_iface:
        cls._validate_interface_name(args.eviltwin_deauth_iface)
        other = getattr(args, 'interface_secondary', None)
        if other and other != args.eviltwin_deauth_iface:
            Color.pl('{!} {R}Error: --eviltwin-deauth-iface ({O}%s{R}) conflicts with '
                     '--interface-secondary ({O}%s{R}){W}'
                     % (args.eviltwin_deauth_iface, other))
            raise ValueError('Conflicting interface specifications: '
                             '--eviltwin-deauth-iface vs --interface-secondary')
        cls.interface_secondary = args.eviltwin_deauth_iface
        cls.dual_interface_enabled = True
        Color.pl('{+} {C}option:{W} Evil Twin deauth interface: {G}%s{W}'
                 % args.eviltwin_deauth_iface)

    if hasattr(args, 'eviltwin_port') and args.eviltwin_port:
        cls.eviltwin_port = args.eviltwin_port
        Color.pl('{+} {C}option:{W} Evil Twin captive portal port: {G}%d{W}' % args.eviltwin_port)

    if hasattr(args, 'eviltwin_deauth_interval') and args.eviltwin_deauth_interval:
        cls.eviltwin_deauth_interval = args.eviltwin_deauth_interval
        Color.pl('{+} {C}option:{W} Evil Twin deauth interval: {G}%d seconds{W}' % args.eviltwin_deauth_interval)

    if hasattr(args, 'eviltwin_timeout') and args.eviltwin_timeout is not None:
        cls.eviltwin_timeout = args.eviltwin_timeout
        Color.pl('{+} {C}option:{W} Evil Twin timeout: {G}%d seconds{W}' % args.eviltwin_timeout)

    if hasattr(args, 'eviltwin_template') and args.eviltwin_template:
        cls.eviltwin_template = args.eviltwin_template
        Color.pl('{+} {C}option:{W} Evil Twin portal template: {G}%s{W}' % args.eviltwin_template)

    if hasattr(args, 'eviltwin_channel') and args.eviltwin_channel:
        cls.eviltwin_channel = args.eviltwin_channel
        Color.pl('{+} {C}option:{W} Evil Twin channel override: {G}%d{W}' % args.eviltwin_channel)

    if hasattr(args, 'eviltwin_no_validate') and args.eviltwin_no_validate:
        cls.eviltwin_validate_credentials = False
        Color.pl('{+} {C}option:{W} Evil Twin credential validation: {O}disabled{W}')


def display_eviltwin_interface_info(cls):
    """Display information about available interfaces for Evil Twin."""
    try:
        # Only display interface info in verbose mode to avoid blocking
        if cls.verbose < 1:
            return

        from ...util.interface_manager import InterfaceManager

        # Get AP-capable interfaces
        ap_interfaces = InterfaceManager.get_ap_capable_interfaces()

        if ap_interfaces:
            Color.pl('{+} Found {G}%d{W} AP-capable interface(s):' % len(ap_interfaces))
            for caps in ap_interfaces:
                info_parts = [caps.interface]
                if caps.driver:
                    info_parts.append(f'driver: {caps.driver}')
                if caps.chipset:
                    info_parts.append(f'chipset: {caps.chipset}')
                Color.pl('{+}   {G}%s{W}' % ', '.join(info_parts))
        else:
            Color.pl('{!} {O}Warning: No AP-capable interfaces detected{W}')
            Color.pl('{!} {O}Evil Twin attack may not work without AP mode support{W}')

    except Exception as e:
        # Don't fail if we can't detect interfaces, just warn
        if cls.verbose > 0:
            Color.pl('{!} {O}Warning: Could not detect interface capabilities: %s{W}' % str(e))
