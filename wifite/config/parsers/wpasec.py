#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WPA-SEC upload and TUI argument parsers."""

from ...util.color import Color


def parse_wpasec_args(cls, args):
    """
    Parse wpa-sec upload-specific command-line arguments.

    Extracts and sets wpa-sec configuration from parsed arguments including:
    - API key (with masking for security)
    - Auto-upload mode
    - Custom server URL
    - Connection timeout
    - Notification email
    - File removal after upload

    Args:
        args: Parsed command-line arguments object from argparse

    Side Effects:
        - Sets class variables for wpa-sec configuration
        - Displays configuration messages to user via Color.pl()
        - Automatically enables wpasec_enabled if API key is provided

    Example:
        >>> Configuration.parse_wpasec_args(parsed_args)
        {+} option: wpa-sec API key: abc1****
        {+} option: wpa-sec automatic upload enabled (no prompts)
    """
    if hasattr(args, 'wpasec_enabled') and args.wpasec_enabled:
        cls.wpasec_enabled = True
        Color.pl('{+} {C}option:{W} wpa-sec upload functionality {G}enabled{W}')

    if hasattr(args, 'wpasec_api_key') and args.wpasec_api_key:
        cls.wpasec_api_key = args.wpasec_api_key
        # Mask the API key in output for security
        masked_key = args.wpasec_api_key[:4] + '*' * (len(args.wpasec_api_key) - 4) if len(args.wpasec_api_key) > 4 else '****'
        Color.pl('{+} {C}option:{W} wpa-sec API key: {G}%s{W}' % masked_key)
        # Enable wpa-sec if API key is provided
        cls.wpasec_enabled = True

    if hasattr(args, 'wpasec_auto_upload') and args.wpasec_auto_upload:
        cls.wpasec_auto_upload = True
        Color.pl('{+} {C}option:{W} wpa-sec {G}automatic upload{W} enabled (no prompts)')

    if hasattr(args, 'wpasec_url') and args.wpasec_url:
        cls.wpasec_url = args.wpasec_url
        Color.pl('{+} {C}option:{W} wpa-sec custom URL: {G}%s{W}' % args.wpasec_url)

    if hasattr(args, 'wpasec_timeout') and args.wpasec_timeout:
        cls.wpasec_timeout = args.wpasec_timeout
        Color.pl('{+} {C}option:{W} wpa-sec upload timeout: {G}%d seconds{W}' % args.wpasec_timeout)

    if hasattr(args, 'wpasec_email') and args.wpasec_email:
        cls.wpasec_email = args.wpasec_email
        Color.pl('{+} {C}option:{W} wpa-sec notification email: {G}%s{W}' % args.wpasec_email)

    if hasattr(args, 'wpasec_remove_after_upload') and args.wpasec_remove_after_upload:
        cls.wpasec_remove_after_upload = True
        Color.pl('{+} {C}option:{W} wpa-sec {O}remove capture files{W} after successful upload')


def parse_tui_args(cls, args):
    """Parse TUI-related arguments"""
    if args.use_tui:
        cls.use_tui = True
        Color.pl('{+} {C}option:{W} using {G}interactive TUI mode{W}')
    elif args.no_tui:
        cls.use_tui = False
        Color.pl('{+} {C}option:{W} using {G}classic text mode{W}')
    # If neither flag is set, use_tui remains False (classic mode is default)
