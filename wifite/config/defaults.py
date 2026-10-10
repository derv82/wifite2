#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Default values and initialization helpers for Configuration."""

import os


def initialize_defaults(cls):
    """
    Sets up default initial configuration values on the Configuration class.
    Does NOT call load_from_arguments or get_monitor_mode_interface.
    """
    cls.verbose = 0  # Verbosity of output. Higher number means more debug info about running processes.
    cls.print_stack_traces = True

    # Initialize logger early (will be configured with verbosity later)
    from ..util.logger import Logger
    Logger.initialize(enabled=True)

    cls.kill_conflicting_processes = False

    cls.scan_time = 0  # Time to wait before attacking all targets

    cls.tx_power = 0  # Wifi transmit power (0 is default)
    cls.interface = None
    cls.min_power = 0  # Minimum power for an access point to be considered a target. Default is 0
    cls.attack_max = 0
    cls.skip_crack = False
    cls.target_channel = None  # User-defined channel to scan
    cls.target_essid = None  # User-defined AP name
    cls.target_bssid = None  # User-defined AP BSSID
    cls.ignore_essids = None  # ESSIDs to ignore
    cls.ignore_captured = False  # Ignore targets with existing captures
    cls.ignore_cracked = False  # Ignore previously-cracked BSSIDs
    cls.clients_only = False  # Only show targets that have associated clients
    cls.all_bands = False  # Scan for both 2Ghz and 5Ghz channels
    cls.two_ghz = False  # Scan 2.4Ghz channels
    cls.five_ghz = False  # Scan 5Ghz channels
    cls.infinite_mode = False  # Attack targets continuously
    cls.inf_wait_time = 60
    cls.show_bssids = False  # Show BSSIDs in targets list
    cls.show_manufacturers = False  # Show manufacturers in targets list
    cls.detect_honeypots = False  # Detect honeypot/rogue APs
    cls.random_mac = False  # Should generate a random Mac address at startup.
    cls.no_deauth = False  # Deauth hidden networks & WPA handshake targets
    cls.num_deauths = 1  # Number of deauth packets to send to each target.
    cls.daemon = False  # Don't put back interface back in managed mode

    cls.encryption_filter = ['WEP', 'WPA', 'WPS']

    # EvilTwin variables
    cls.use_eviltwin = False
    cls.eviltwin_port = 80
    cls.eviltwin_deauth_interval = 5
    cls.eviltwin_timeout = 0  # Seconds before giving up (0 = run until success/interrupt)
    cls.eviltwin_template = 'generic'
    cls.eviltwin_channel = None
    cls.eviltwin_validate_credentials = True

    # Dual interface support
    cls.dual_interface_enabled = False  # Enable dual interface mode
    cls.interface_primary = None  # Primary interface name
    cls.interface_secondary = None  # Secondary interface name
    cls.auto_assign_interfaces = True  # Auto-assign interfaces (default True)
    cls.prefer_dual_interface = True  # Prefer dual over single when available (default True)
    cls.use_hcxdump = False  # Use hcxdumptool for dual interface WPA capture (default False)

    # WEP variables
    cls.wep_filter = False  # Only attack WEP networks
    cls.wep_pps = 600  # Packets per second
    cls.wep_timeout = 600  # Seconds to wait before failing
    cls.wep_crack_at_ivs = 10000  # Minimum IVs to start cracking
    cls.require_fakeauth = False
    cls.wep_restart_stale_ivs = 11  # Seconds to wait before restarting
    # Aireplay if IVs don't increase.
    # '0' means never restart.
    cls.wep_restart_aircrack = 30  # Seconds to give aircrack to crack
    # before restarting the process.
    cls.wep_keep_ivs = False  # Retain .ivs files across multiple attacks.

    # WPA variables
    cls.wpa_filter = False  # Only attack WPA/WPA2 networks
    cls.wpa3_filter = False  # Only attack WPA3 networks
    cls.owe_filter = False  # Only attack OWE networks
    cls.wpa_deauth_timeout = 15  # Wait time between deauths
    cls.wpa_attack_timeout = 300  # Wait time before failing
    cls.wpa_handshake_dir = 'hs'  # Dir to store handshakes
    cls.wpa_strip_handshake = False  # Strip non-handshake packets
    cls.ignore_old_handshakes = False  # Always fetch a new handshake

    # WPA3-specific variables
    cls.wpa3_only = False  # Only attack WPA3-SAE networks, skip WPA2-only
    cls.wpa3_no_downgrade = False  # Disable transition mode downgrade attacks
    cls.wpa3_force_sae = False  # Skip WPA2 attacks on transition mode
    cls.wpa3_check_dragonblood = False  # Only scan for Dragonblood vulnerabilities
    cls.wpa3_attack_timeout = None  # WPA3-specific timeout (defaults to wpa_attack_timeout)
    cls.dragonblood_timing = False  # Enable Dragonblood timing attack (CVE-2019-13377)
    cls.dragonblood_samples = 3  # Timing samples per password candidate
    cls.dragonblood_max_passwords = 50  # Max passwords to probe during timing attack

    # PMKID variables
    cls.use_pmkid_only = False  # Only use PMKID Capture+Crack attack
    cls.pmkid_timeout = 300  # Time to wait for PMKID capture
    cls.dont_use_pmkid = False  # Don't use PMKID attack

    # Passive PMKID capture variables
    cls.pmkid_passive = False  # Enable passive PMKID capture mode
    cls.pmkid_passive_duration = 0  # Duration for passive capture (0 = infinite)
    cls.pmkid_passive_interval = 30  # Interval between hash extractions in seconds

    # Default dictionary for cracking
    cls.cracked_file = 'cracked.json'
    cls.wordlist = None
    cls.wordlists = []
    default_wordlists = [
        './wordlists/',  # Local directory (ran from cloned repo)
        '/usr/share/dict/wordlists/',  # setup.py with prefix=/usr
        '/usr/local/share/dict/wordlists/',  # setup.py with prefix=/usr/local
        # Other passwords found on Kali
        '/usr/share/wfuzz/wordlist/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt',
        '/usr/share/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt',
        '/usr/share/wordlists/fern-wifi/common.txt'
    ]
    import glob
    for wlist in default_wordlists:
        if os.path.isdir(wlist):
            files = sorted(glob.glob(os.path.join(wlist, '*.txt')))
            if files:
                cls.wordlist = files[0]
                cls.wordlists = files
                break
        elif os.path.isfile(wlist):
            cls.wordlist = wlist
            cls.wordlists = [wlist]
            break

    # Manufacturers database is lazy-loaded on first access via load_manufacturers()
    cls.manufacturers = None
    cls._manufacturers_loaded = False

    # WPS variables
    cls.wps_filter = False  # Only attack WPS networks
    cls.no_wps = False  # Do not use WPS attacks (Pixie-Dust & PIN attacks)
    cls.wps_only = False  # ONLY use WPS attacks on non-WEP networks
    cls.use_bully = False  # Use bully instead of reaver
    cls.use_reaver = False  # Use reaver instead of bully
    cls.wps_pixie = True
    cls.wps_no_nullpin = True
    cls.wps_pin = True
    cls.wps_ignore_lock = False  # Skip WPS PIN attack if AP is locked.
    cls.wps_pixie_timeout = 300  # Seconds to wait for PIN before WPS Pixie attack fails
    cls.wps_fail_threshold = 100  # Max number of failures
    cls.wps_timeout_threshold = 100  # Max number of timeouts

    # Commands
    cls.show_cracked = False
    cls.show_ignored = False
    cls.check_handshake = None
    cls.crack_handshake = False
    cls.update_db = False
    cls.db_filename = 'ieee-oui.txt'

    # Session resume
    cls.resume = False
    cls.resume_latest = False
    cls.resume_id = None
    cls.clean_sessions = False

    # TUI settings
    cls.use_tui = False  # False = classic (default), True = force TUI
    cls.tui_refresh_rate = 0.5  # Seconds between TUI updates
    cls.tui_log_buffer_size = 1000  # Maximum log entries to keep in memory
    cls.tui_color_scheme = 'default'  # Color scheme for TUI
    cls.tui_debug = False  # Enable TUI debug logging

    # WPA-SEC upload settings
    cls.wpasec_enabled = False  # Enable wpa-sec upload functionality
    cls.wpasec_api_key = None  # User API key for wpa-sec.stanev.org
    cls.wpasec_auto_upload = False  # Automatically upload without prompting
    cls.wpasec_url = 'https://wpa-sec.stanev.org'  # wpa-sec server URL
    cls.wpasec_timeout = 30  # Connection timeout in seconds
    cls.wpasec_email = None  # Optional email for notifications
    cls.wpasec_remove_after_upload = False  # Remove capture file after successful upload

    # Attack monitoring settings
    cls.monitor_attacks = False  # Enable wireless attack monitoring mode
    cls.monitor_duration = 0  # Duration for monitoring in seconds (0 = infinite)
    cls.monitor_log_file = None  # Log file path for attack events
    cls.monitor_channel = None  # Specific channel to monitor (None = current)
    cls.monitor_hop = False  # Enable channel hopping during monitoring

    # System check mode
    cls.syscheck = False

    # A list to cache all checked commands (e.g. `which hashcat` will execute only once)
    cls.existing_commands = {}
