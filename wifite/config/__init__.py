#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
from ..util.color import Color
from ..tools.macchanger import Macchanger


def _get_version():
    """Get version from importlib.metadata (installed package) or fallback to hardcoded."""
    try:
        from importlib.metadata import version
        return version('wifite2')
    except Exception:
        return '2.9.9-beta'


class Configuration:
    """ Stores configuration variables and functions for Wifite. """

    initialized = False  # Flag indicating config has been initialized
    verbose = 0
    kalidroid = False  # --kalidroid: MiniTerminal-friendly output for the Kalidroid app
    version = _get_version()

    all_bands = None
    attack_max = None
    check_handshake = None
    clients_only = None
    cracked_file = None
    crack_handshake = None
    daemon = None
    dont_use_pmkid = None
    encryption_filter = None
    existing_commands = None
    five_ghz = None
    ignore_captured = None
    ignore_cracked = None
    ignore_essids = None
    ignore_old_handshakes = None
    infinite_mode = None
    inf_wait_time = None
    interface = None
    kill_conflicting_processes = None
    manufacturers = None
    min_power = None
    no_deauth = None
    no_wps = None
    wps_no_nullpin = None
    num_deauths = None
    pmkid_timeout = None
    print_stack_traces = None
    random_mac = None
    random_mac_vendor = None
    require_fakeauth = None
    scan_time = None
    show_bssids = None
    show_cracked = None
    show_ignored = None
    tx_power = None
    update_db = None
    db_filename = None
    show_manufacturers = None
    detect_honeypots = None
    skip_crack = None
    target_bssid = None
    target_channel = None
    target_essid = None
    temp_dir = None  # Temporary directory
    two_ghz = None
    use_bully = None
    use_reaver = None
    use_eviltwin = None
    # Evil Twin settings
    eviltwin_port = None
    eviltwin_deauth_interval = None
    eviltwin_timeout = None
    eviltwin_template = None
    eviltwin_channel = None
    eviltwin_validate_credentials = None
    # Dual interface support
    dual_interface_enabled = None
    interface_primary = None
    interface_secondary = None
    auto_assign_interfaces = None
    prefer_dual_interface = None
    use_hcxdump = None
    # Session resume flags
    resume = None
    resume_latest = None
    resume_id = None
    clean_sessions = None
    use_pmkid_only = None
    # Passive PMKID capture settings
    pmkid_passive = None
    pmkid_passive_duration = None
    pmkid_passive_interval = None
    wep_attacks = None
    wep_crack_at_ivs = None
    wep_filter = None
    wep_keep_ivs = None
    wep_pps = None
    wep_restart_aircrack = None
    wep_restart_stale_ivs = None
    wep_timeout = None
    wordlist = None
    wordlists = None
    wpa_attack_timeout = None
    wpa_deauth_timeout = None
    wpa_filter = None
    wpa3_filter = None
    wpa3_only = None
    owe_filter = None
    wpa3_no_downgrade = None
    wpa3_force_sae = None
    wpa3_check_dragonblood = None
    wpa3_attack_timeout = None
    dragonblood_timing = None
    dragonblood_samples = 3
    dragonblood_max_passwords = 50
    wpa_handshake_dir = None
    wpa_strip_handshake = None
    wps_fail_threshold = None
    wps_filter = None
    wps_ignore_lock = None
    wps_only = None
    wps_pin = None
    wps_pixie = None
    wps_pixie_timeout = None
    wps_timeout_threshold = None
    # TUI settings
    use_tui = None  # None = classic (default), True = force TUI, False = classic
    tui_refresh_rate = None
    tui_log_buffer_size = None
    tui_color_scheme = None
    tui_debug = None
    # WPA-SEC upload settings
    wpasec_enabled = None
    wpasec_api_key = None
    wpasec_auto_upload = None
    wpasec_url = None
    wpasec_timeout = None
    wpasec_email = None
    wpasec_remove_after_upload = None
    # Attack monitoring settings
    monitor_attacks = None
    monitor_duration = None
    monitor_log_file = None
    monitor_channel = None
    monitor_hop = None
    # System check mode
    syscheck = None

    @classmethod
    def load_manufacturers(cls):
        """Lazy-load OUI manufacturer database on first access."""
        from .manufacturers import load_manufacturers
        load_manufacturers(cls)

    @classmethod
    def initialize(cls, load_interface=True):
        """
            Sets up default initial configuration values.
            Also sets config values based on command-line arguments.
        """
        # Only initialize this class once
        if cls.initialized:
            return
        cls.initialized = True

        # Set all default values
        from .defaults import initialize_defaults
        initialize_defaults(cls)

        # Overwrite config values with arguments (if defined)
        cls.load_from_arguments()

        if load_interface:
            cls.get_monitor_mode_interface()

    @classmethod
    def get_monitor_mode_interface(cls):
        if cls.interface is None:
            # Interface wasn't defined, select it!
            from ..tools.airmon import Airmon
            cls.interface = Airmon.ask()
            if cls.random_mac or cls.random_mac_vendor:
                Macchanger.random(full_random=not cls.random_mac_vendor)

    @classmethod
    def load_from_arguments(cls):
        """ Sets configuration values based on Argument.args object """
        from ..args import Arguments

        args = Arguments(cls).args
        cls.parse_settings_args(args)
        cls.parse_wep_args(args)
        cls.parse_wpa_args(args)
        cls.parse_wps_args(args)
        cls.parse_pmkid_args(args)
        cls.parse_eviltwin_args(args)
        cls.parse_attack_monitor_args(args)
        cls.parse_dual_interface_args(args)
        cls.parse_wpasec_args(args)
        cls.parse_encryption()

        cls.parse_wep_attacks()

        cls.validate()

        # Commands
        if args.cracked:
            cls.show_cracked = True
        if args.ignored:
            cls.show_ignored = True
        if args.check_handshake:
            cls.check_handshake = args.check_handshake
        if args.crack_handshake:
            cls.crack_handshake = True
        if args.update_db:
            cls.update_db = True
        if hasattr(args, 'syscheck') and args.syscheck:
            cls.syscheck = True

        # Session resume
        if args.resume:
            cls.resume = True
        if args.resume_latest:
            cls.resume_latest = True
        if args.resume_id:
            cls.resume_id = args.resume_id
        if args.clean_sessions:
            cls.clean_sessions = True

    @classmethod
    def validate(cls):
        from .validators import validate
        validate(cls)

    @classmethod
    def _validate_eviltwin_config(cls):
        from .validators import validate_eviltwin_config
        validate_eviltwin_config(cls)

    @classmethod
    def _validate_attack_monitor_config(cls):
        from .validators import validate_attack_monitor_config
        validate_attack_monitor_config(cls)

    @classmethod
    def _validate_wpasec_config(cls):
        from .validators import validate_wpasec_config
        validate_wpasec_config(cls)

    @staticmethod
    def _validate_interface_name(name):
        from .validators import validate_interface_name
        validate_interface_name(name)

    @classmethod
    def parse_settings_args(cls, args):
        from .parsers.settings import parse_settings_args
        parse_settings_args(cls, args)

    @classmethod
    def parse_wep_args(cls, args):
        from .parsers.wep import parse_wep_args
        parse_wep_args(cls, args)

    @classmethod
    def parse_wpa_args(cls, args):
        from .parsers.wpa import parse_wpa_args
        parse_wpa_args(cls, args)

    @classmethod
    def parse_wps_args(cls, args):
        from .parsers.wps import parse_wps_args
        parse_wps_args(cls, args)

    @classmethod
    def parse_pmkid_args(cls, args):
        from .parsers.pmkid import parse_pmkid_args
        parse_pmkid_args(cls, args)

    @classmethod
    def parse_eviltwin_args(cls, args):
        from .parsers.eviltwin import parse_eviltwin_args
        parse_eviltwin_args(cls, args)

    @classmethod
    def _display_eviltwin_interface_info(cls):
        from .parsers.eviltwin import display_eviltwin_interface_info
        display_eviltwin_interface_info(cls)

    @classmethod
    def parse_attack_monitor_args(cls, args):
        from .parsers.attack_monitor import parse_attack_monitor_args
        parse_attack_monitor_args(cls, args)

    @classmethod
    def parse_dual_interface_args(cls, args):
        from .parsers.dual_interface import parse_dual_interface_args
        parse_dual_interface_args(cls, args)

    @classmethod
    def parse_wpasec_args(cls, args):
        from .parsers.wpasec import parse_wpasec_args
        parse_wpasec_args(cls, args)

    @classmethod
    def parse_tui_args(cls, args):
        from .parsers.wpasec import parse_tui_args
        parse_tui_args(cls, args)

    @classmethod
    def parse_encryption(cls):
        from .parsers.settings import parse_encryption
        parse_encryption(cls)

    @classmethod
    def parse_wep_attacks(cls):
        from .parsers.settings import parse_wep_attacks
        parse_wep_attacks(cls)

    @classmethod
    def temp(cls, subfile=''):
        """ Creates and/or returns the temporary directory """
        if cls.temp_dir is None:
            cls.temp_dir = cls.create_temp()
        return cls.temp_dir + subfile

    @staticmethod
    def create_temp():
        """ Creates and returns a temporary directory """
        from tempfile import mkdtemp
        tmp = mkdtemp(prefix='wifite')
        if not tmp.endswith(os.sep):
            tmp += os.sep
        return tmp

    @classmethod
    def delete_temp(cls):
        """ Remove temp files and folder """
        if cls.temp_dir is None:
            return
        if os.path.exists(cls.temp_dir):
            for f in os.listdir(cls.temp_dir):
                try:
                    file_path = os.path.join(cls.temp_dir, f)
                    os.remove(file_path)
                except (OSError, IOError):
                    pass  # Ignore errors during cleanup
            try:
                os.rmdir(cls.temp_dir)
            except (OSError, IOError):
                pass  # Ignore errors during cleanup

    @classmethod
    def cleanup_memory(cls):
        """ Periodic memory cleanup during long operations """
        # Clear command cache periodically
        if hasattr(cls, 'existing_commands') and len(cls.existing_commands) > 100:
            # Keep only the most recently used commands
            cls.existing_commands = dict(list(cls.existing_commands.items())[-50:])

        # Clean up processes and file descriptors
        from ..util.process import ProcessManager, Process
        ProcessManager().cleanup_all()
        Process.cleanup_zombies()

        # Force garbage collection
        import gc
        gc.collect()

    @classmethod
    def exit_gracefully(cls):
        """ Deletes temp and exits with the given code """
        code = 0
        cls.delete_temp()
        Macchanger.reset_if_changed()

        # Clean up managed interfaces
        try:
            from ..util.interface_manager import InterfaceManager
            from ..util.logger import log_info, log_debug

            # Check if we have an interface manager instance to clean up
            if hasattr(cls, 'interface_manager') and cls.interface_manager is not None:
                log_info('Config', 'Cleaning up managed interfaces')
                restored = cls.interface_manager.cleanup_all()
                log_debug('Config', f'Restored {restored} interface(s)')
        except Exception as e:
            from ..util.logger import log_error
            log_error('Config', f'Error during interface cleanup: {e}', e)

        from ..tools.airmon import Airmon
        if cls.interface is not None and Airmon.base_interface is not None:
            if not cls.daemon:
                Color.pl('{!} {O}Note:{W} Leaving interface in Monitor Mode!')
                Color.pl('{!} To disable Monitor Mode when finished: '
                         '{C}ip link set %s down && iw dev %s set type managed && ip link set %s up{W}'
                         % (cls.interface, cls.interface, cls.interface))
            else:
                # Stop monitor mode
                Airmon.stop(cls.interface)
                # Bring original interface back up
                Airmon.put_interface_up(Airmon.base_interface)

        if Airmon.killed_network_manager:
            Color.pl('{!} You can restart NetworkManager when finished ({C}service NetworkManager start{W})')
            # Airmon.start_network_manager()

        exit(code)

    @classmethod
    def dump(cls):
        """ (Colorful) string representation of the configuration """
        from ..util.color import Color

        max_len = 20
        for key in list(cls.__dict__.keys()):
            max_len = max(max_len, len(key))

        result = Color.s('{W}%s  Value{W}\n' % 'cls Key'.ljust(max_len))
        result += Color.s('{W}%s------------------{W}\n' % ('-' * max_len))

        for (key, val) in sorted(cls.__dict__.items()):
            if key.startswith('__') or type(val) in [classmethod, staticmethod] or val is None:
                continue
            result += Color.s('{G}%s {W} {C}%s{W}\n' % (key.ljust(max_len), val))
        return result


if __name__ == '__main__':
    Configuration.initialize(False)
    print((Configuration.dump()))
