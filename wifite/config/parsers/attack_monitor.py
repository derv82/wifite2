#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Wireless attack monitoring argument parser."""

from ...util.color import Color


def parse_attack_monitor_args(cls, args):
    """Parse wireless attack monitoring-specific arguments"""
    if hasattr(args, 'monitor_attacks') and args.monitor_attacks:
        cls.monitor_attacks = True
        Color.pl('{+} {C}option:{W} {G}wireless attack monitoring mode{W} enabled')

    if hasattr(args, 'monitor_duration') and args.monitor_duration:
        cls.monitor_duration = args.monitor_duration
        if args.monitor_duration > 0:
            Color.pl('{+} {C}option:{W} monitoring duration: {G}%d seconds{W}' % args.monitor_duration)
        else:
            Color.pl('{+} {C}option:{W} monitoring duration: {G}infinite{W}')

    if hasattr(args, 'monitor_log_file') and args.monitor_log_file:
        cls.monitor_log_file = args.monitor_log_file
        Color.pl('{+} {C}option:{W} attack log file: {G}%s{W}' % args.monitor_log_file)

    if hasattr(args, 'monitor_channel') and args.monitor_channel:
        cls.monitor_channel = args.monitor_channel
        # Validate channel number
        if cls.monitor_channel < 1 or cls.monitor_channel > 165:
            Color.pl('{!} {R}Error: Invalid channel {O}%d{W}' % cls.monitor_channel)
            raise ValueError('Invalid channel number for attack monitoring')
        Color.pl('{+} {C}option:{W} monitoring channel: {G}%d{W}' % args.monitor_channel)

    if hasattr(args, 'monitor_hop') and args.monitor_hop:
        cls.monitor_hop = True
        Color.pl('{+} {C}option:{W} channel hopping {G}enabled{W} (all 2.4GHz channels)')
        # Validate that both channel and hop are not set
        if cls.monitor_channel:
            Color.pl('{!} {R}Error: Cannot specify both --monitor-channel and --monitor-hop{W}')
            raise ValueError('Cannot use both specific channel and channel hopping')
