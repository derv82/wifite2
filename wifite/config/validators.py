#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validation helpers and configuration validation routines."""

import re
import os

from ..util.color import Color


def validate(cls):
    """Top-level configuration validation."""
    if cls.use_pmkid_only and cls.wps_only:
        Color.pl('{!} {R}Bad Configuration:{O} --pmkid and --wps-only are not compatible')
        raise RuntimeError('Unable to attack networks: --pmkid and --wps-only are not compatible together')
    if cls.use_pmkid_only and cls.dont_use_pmkid:
        Color.pl('{!} {R}Bad Configuration:{O} --pmkid and --no-pmkid are not compatible')
        raise RuntimeError('Unable to attack networks: --pmkid and --no-pmkid are not compatible together')

    # Validate Evil Twin configuration
    if cls.use_eviltwin:
        validate_eviltwin_config(cls)

    # Validate attack monitoring configuration
    if cls.monitor_attacks:
        validate_attack_monitor_config(cls)

    # Validate wpa-sec configuration
    if cls.wpasec_enabled:
        validate_wpasec_config(cls)


def validate_eviltwin_config(cls):
    """Validate Evil Twin configuration and interface capabilities."""
    # Lazy import to avoid circular dependency (interface_manager imports Configuration)
    from ..util.interface_manager import InterfaceManager

    # Check if we have AP-capable interfaces
    ap_interfaces = InterfaceManager.get_ap_capable_interfaces()

    if not ap_interfaces:
        Color.pl('{!} {R}Error: No AP-capable wireless interfaces found{W}')
        Color.pl('{!} {O}Evil Twin attack requires a wireless adapter that supports AP mode{W}')
        Color.pl('{!} {O}Recommended adapters:{W}')
        Color.pl('{!}   - Alfa AWUS036NHA (Atheros AR9271)')
        Color.pl('{!}   - TP-Link TL-WN722N v1 (Atheros AR9271)')
        Color.pl('{!}   - Panda PAU05 (Ralink RT5372)')
        Color.pl('{!}   - Alfa AWUS036ACH (Realtek RTL8812AU)')
        raise RuntimeError('No AP-capable interfaces available for Evil Twin attack')

    # If a primary interface was specified (via --interface-primary or
    # --eviltwin-fakeap-iface), validate it supports AP mode. Both flags
    # populate the same Configuration.interface_primary field.
    if cls.interface_primary:
        found = False
        for caps in ap_interfaces:
            if caps.interface == cls.interface_primary:
                found = True
                break

        if not found:
            Color.pl('{!} {R}Error: Specified interface {O}%s{R} does not support AP mode{W}'
                    % cls.interface_primary)
            Color.pl('{!} {O}Available AP-capable interfaces:{W}')
            for caps in ap_interfaces:
                Color.pl('{!}   - {G}%s{W}' % caps.interface)
            raise RuntimeError('Specified interface does not support AP mode')

    # Validate port
    if cls.eviltwin_port < 1 or cls.eviltwin_port > 65535:
        Color.pl('{!} {R}Error: Invalid port {O}%d{W}' % cls.eviltwin_port)
        raise RuntimeError('Invalid port number for Evil Twin captive portal')

    # Validate deauth interval
    if cls.eviltwin_deauth_interval < 1:
        Color.pl('{!} {R}Error: Deauth interval must be at least 1 second{W}')
        raise RuntimeError('Invalid deauth interval')

    # Validate channel if specified
    if cls.eviltwin_channel is not None:
        if cls.eviltwin_channel < 1 or cls.eviltwin_channel > 165:
            Color.pl('{!} {R}Error: Invalid channel {O}%d{W}' % cls.eviltwin_channel)
            raise RuntimeError('Invalid channel for Evil Twin attack')

    # Validate template
    valid_templates = ['generic', 'tplink', 'netgear', 'linksys']
    if cls.eviltwin_template not in valid_templates:
        Color.pl('{!} {R}Error: Invalid template {O}%s{W}' % cls.eviltwin_template)
        Color.pl('{!} {O}Valid templates: {G}%s{W}' % ', '.join(valid_templates))
        raise RuntimeError('Invalid captive portal template')

    Color.pl('{+} {G}Evil Twin configuration validated{W}')
    Color.pl('{+} Found {G}%d{W} AP-capable interface(s)' % len(ap_interfaces))


def validate_attack_monitor_config(cls):
    """Validate attack monitoring configuration settings."""
    # Lazy import to avoid circular dependency (tshark imports Configuration)
    from ..tools.tshark import Tshark

    # Validate tshark is available
    if not Tshark.exists():
        Color.pl('{!} {R}Error: tshark not found{W}')
        Color.pl('{!} {O}Attack monitoring requires tshark for frame capture{W}')
        Color.pl('{!} {O}Install with:{W} {C}apt install tshark{W} or {C}yum install wireshark{W}')
        raise RuntimeError('tshark is required for attack monitoring')

    # Validate duration
    if cls.monitor_duration < 0:
        Color.pl('{!} {R}Error: Invalid monitoring duration {O}%d{W}' % cls.monitor_duration)
        raise ValueError('Monitoring duration must be 0 (infinite) or positive')

    # Validate channel
    if cls.monitor_channel is not None:
        if cls.monitor_channel < 1 or cls.monitor_channel > 165:
            Color.pl('{!} {R}Error: Invalid channel {O}%d{W}' % cls.monitor_channel)
            Color.pl('{!} {O}Valid channels: 1-14 (2.4GHz), 36-165 (5GHz){W}')
            raise ValueError('Invalid channel number')

    # Validate channel and hop are not both set
    if cls.monitor_channel and cls.monitor_hop:
        Color.pl('{!} {R}Error: Cannot specify both --monitor-channel and --monitor-hop{W}')
        raise ValueError('Cannot use both specific channel and channel hopping')

    # Validate log file path if specified
    if cls.monitor_log_file:
        log_dir = os.path.dirname(cls.monitor_log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
                Color.pl('{+} Created log directory: {G}%s{W}' % log_dir)
            except OSError as e:
                Color.pl('{!} {R}Error: Cannot create log directory {O}%s{W}: %s' % (log_dir, str(e)))
                raise ValueError('Invalid log file path')

    if cls.verbose > 0:
        Color.pl('{+} {G}Attack monitoring configuration validated{W}')


def validate_wpasec_config(cls):
    """
    Validate wpa-sec configuration settings.

    Performs validation checks on wpa-sec configuration:
    - API key presence (required when wpa-sec is enabled)
    - API key format (minimum 8 characters, alphanumeric with hyphens/underscores)
    - API key character validation

    Raises:
        RuntimeError: If validation fails with descriptive error message

    Side Effects:
        - Displays error messages to user via Color.pl()
        - Provides helpful hints for fixing configuration issues

    Example:
        >>> Configuration.wpasec_enabled = True
        >>> Configuration.wpasec_api_key = "abc123"
        >>> Configuration._validate_wpasec_config()
        RuntimeError: Invalid wpa-sec API key: too short
    """
    # Validate API key format if provided
    if cls.wpasec_api_key:
        # API key should be alphanumeric and at least 8 characters
        if len(cls.wpasec_api_key) < 8:
            Color.pl('{!} {R}Error: wpa-sec API key must be at least 8 characters{W}')
            raise RuntimeError('Invalid wpa-sec API key: too short')

        # Check if API key contains only valid characters (alphanumeric and common special chars)
        if not re.match(r'^[a-zA-Z0-9_\-]+$', cls.wpasec_api_key):
            Color.pl('{!} {R}Error: wpa-sec API key contains invalid characters{W}')
            Color.pl('{!} {O}API key should only contain letters, numbers, hyphens, and underscores{W}')
            raise RuntimeError('Invalid wpa-sec API key format')
    else:
        # API key is required if wpa-sec is enabled
        Color.pl('{!} {R}Error: wpa-sec upload enabled but no API key provided{W}')
        Color.pl('{!} {O}Use {C}--wpasec-key{O} to specify your wpa-sec.stanev.org API key{W}')
        raise RuntimeError('wpa-sec API key required')

    # Validate URL format if custom URL provided
    if cls.wpasec_url:
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if not url_pattern.match(cls.wpasec_url):
            Color.pl('{!} {R}Error: Invalid wpa-sec URL format: {O}%s{W}' % cls.wpasec_url)
            Color.pl('{!} {O}URL must start with http:// or https://{W}')
            raise RuntimeError('Invalid wpa-sec URL format')

    # Validate timeout value is positive integer
    if cls.wpasec_timeout:
        if not isinstance(cls.wpasec_timeout, int) or cls.wpasec_timeout <= 0:
            Color.pl('{!} {R}Error: wpa-sec timeout must be a positive integer{W}')
            raise RuntimeError('Invalid wpa-sec timeout value')

        if cls.wpasec_timeout < 10:
            Color.pl('{!} {O}Warning: wpa-sec timeout is very short ({G}%d{O} seconds){W}' % cls.wpasec_timeout)
            Color.pl('{!} {O}Uploads may fail due to insufficient time{W}')

    # Validate email format if provided
    if cls.wpasec_email:
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(cls.wpasec_email):
            Color.pl('{!} {R}Error: Invalid email format: {O}%s{W}' % cls.wpasec_email)
            raise RuntimeError('Invalid wpa-sec email format')

    if cls.verbose > 0:
        Color.pl('{+} {G}wpa-sec configuration validated{W}')


def validate_interface_name(name):
    """Validates a user-supplied wireless interface name.

    Linux interface names may only contain letters, digits, hyphens, and
    underscores (max 15 chars per IFNAMSIZ).  Rejecting anything outside
    this set prevents malicious names from being interpolated into
    subprocess f-strings even when shell=False is in use.

    Raises ValueError with a descriptive message on invalid input.
    """
    if not re.match(r'^[a-zA-Z0-9_\-]{1,15}$', name):
        raise ValueError(
            f"Invalid interface name: '{name}'. "
            "Interface names must be 1-15 characters and contain only "
            "letters, digits, hyphens (-), and underscores (_)."
        )
