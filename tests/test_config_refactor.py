#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the refactored config package structure.

Verifies that:
- All import styles continue to work (backward compatibility).
- The Configuration class behaves identically after the refactor.
- Sub-modules are importable and contain the expected callables.
- Key configuration flows (initialization, validation, temp helpers) work.
"""

import unittest
import os
import sys

# Mock sys.argv to prevent argparse from reading test arguments
original_argv = sys.argv
sys.argv = ['wifite']


class TestConfigImports(unittest.TestCase):
    """Verify that all existing import patterns still work."""

    def test_import_configuration_from_wifite_config(self):
        """Primary import style used across the codebase."""
        from wifite.config import Configuration
        self.assertIsNotNone(Configuration)

    def test_configuration_version_accessible_at_import_time(self):
        """setup.py imports Configuration.version at import time."""
        from wifite.config import Configuration
        self.assertIsNotNone(Configuration.version)
        self.assertIsInstance(Configuration.version, str)

    def test_import_defaults_submodule(self):
        from wifite.config.defaults import initialize_defaults
        self.assertTrue(callable(initialize_defaults))

    def test_import_validators_submodule(self):
        from wifite.config.validators import (
            validate,
            validate_eviltwin_config,
            validate_attack_monitor_config,
            validate_wpasec_config,
            validate_interface_name,
        )
        for fn in (validate, validate_eviltwin_config, validate_attack_monitor_config,
                   validate_wpasec_config, validate_interface_name):
            self.assertTrue(callable(fn))

    def test_import_manufacturers_submodule(self):
        from wifite.config.manufacturers import load_manufacturers
        self.assertTrue(callable(load_manufacturers))

    def test_import_parsers_settings(self):
        from wifite.config.parsers.settings import (
            parse_settings_args,
            parse_encryption,
            parse_wep_attacks,
        )
        for fn in (parse_settings_args, parse_encryption, parse_wep_attacks):
            self.assertTrue(callable(fn))

    def test_import_parsers_wep(self):
        from wifite.config.parsers.wep import parse_wep_args
        self.assertTrue(callable(parse_wep_args))

    def test_import_parsers_wpa(self):
        from wifite.config.parsers.wpa import parse_wpa_args
        self.assertTrue(callable(parse_wpa_args))

    def test_import_parsers_wps(self):
        from wifite.config.parsers.wps import parse_wps_args
        self.assertTrue(callable(parse_wps_args))

    def test_import_parsers_pmkid(self):
        from wifite.config.parsers.pmkid import parse_pmkid_args
        self.assertTrue(callable(parse_pmkid_args))

    def test_import_parsers_eviltwin(self):
        from wifite.config.parsers.eviltwin import (
            parse_eviltwin_args,
            display_eviltwin_interface_info,
        )
        self.assertTrue(callable(parse_eviltwin_args))
        self.assertTrue(callable(display_eviltwin_interface_info))

    def test_import_parsers_attack_monitor(self):
        from wifite.config.parsers.attack_monitor import parse_attack_monitor_args
        self.assertTrue(callable(parse_attack_monitor_args))

    def test_import_parsers_dual_interface(self):
        from wifite.config.parsers.dual_interface import parse_dual_interface_args
        self.assertTrue(callable(parse_dual_interface_args))

    def test_import_parsers_wpasec(self):
        from wifite.config.parsers.wpasec import parse_wpasec_args, parse_tui_args
        self.assertTrue(callable(parse_wpasec_args))
        self.assertTrue(callable(parse_tui_args))


class TestConfigurationInitialization(unittest.TestCase):
    """Verify the Configuration.initialize() flow."""

    def setUp(self):
        self._orig_argv = sys.argv[:]
        sys.argv = ['wifite']

    def tearDown(self):
        sys.argv = self._orig_argv

    def test_initialize_sets_defaults(self):
        """initialize_defaults() sets the expected values on Configuration."""
        from wifite.config import Configuration
        from wifite.config.defaults import initialize_defaults
        # Apply defaults to a fresh class state (without going through full initialize)
        initialize_defaults(Configuration)
        self.assertEqual(Configuration.verbose, 0)
        self.assertEqual(Configuration.wpa_attack_timeout, 300)
        self.assertEqual(Configuration.wps_pixie_timeout, 300)
        self.assertEqual(Configuration.wep_pps, 600)
        self.assertFalse(Configuration.use_eviltwin)
        self.assertFalse(Configuration.use_tui)

    def test_initialize_is_idempotent(self):
        """Configuration.initialize() is a no-op after the first call."""
        from wifite.config import Configuration
        from unittest.mock import patch
        with patch.object(Configuration, 'load_from_arguments'):
            Configuration.initialized = False
            Configuration.initialize(load_interface=False)
            Configuration.verbose = 99  # change after first init
            Configuration.initialize(load_interface=False)  # second call should be a no-op
        self.assertEqual(Configuration.verbose, 99)

    def test_initialize_sets_encryption_filter(self):
        """After initialize(), encryption_filter is a non-empty list."""
        from wifite.config import Configuration
        from wifite.config.defaults import initialize_defaults
        from wifite.config.parsers.settings import parse_encryption
        initialize_defaults(Configuration)
        parse_encryption(Configuration)
        self.assertIsInstance(Configuration.encryption_filter, list)
        self.assertGreater(len(Configuration.encryption_filter), 0)

    def test_initialize_sets_wep_attacks(self):
        """After parse_wep_attacks(), wep_attacks is a non-empty list."""
        from wifite.config import Configuration
        from wifite.config.defaults import initialize_defaults
        from wifite.config.parsers.settings import parse_wep_attacks
        initialize_defaults(Configuration)
        parse_wep_attacks(Configuration)
        self.assertIsInstance(Configuration.wep_attacks, list)
        self.assertGreater(len(Configuration.wep_attacks), 0)


class TestConfigurationValidation(unittest.TestCase):
    """Verify that Configuration validation methods work correctly."""

    def setUp(self):
        from wifite.config import Configuration
        from wifite.config.defaults import initialize_defaults
        self._orig_argv = sys.argv[:]
        sys.argv = ['wifite']
        # Apply defaults directly to avoid full initialize() complexity
        initialize_defaults(Configuration)

    def tearDown(self):
        sys.argv = self._orig_argv

    def test_validate_interface_name_valid(self):
        from wifite.config import Configuration
        # Should not raise
        Configuration._validate_interface_name('wlan0')
        Configuration._validate_interface_name('wlan0mon')
        Configuration._validate_interface_name('eth0')
        Configuration._validate_interface_name('wlp2s0')

    def test_validate_interface_name_invalid_special_chars(self):
        from wifite.config import Configuration
        with self.assertRaises(ValueError):
            Configuration._validate_interface_name('wlan0; rm -rf /')

    def test_validate_interface_name_too_long(self):
        from wifite.config import Configuration
        with self.assertRaises(ValueError):
            Configuration._validate_interface_name('a' * 16)  # >15 chars

    def test_validate_interface_name_empty(self):
        from wifite.config import Configuration
        with self.assertRaises(ValueError):
            Configuration._validate_interface_name('')

    def test_validate_pmkid_conflict(self):
        from wifite.config import Configuration
        Configuration.use_pmkid_only = True
        Configuration.wps_only = True
        with self.assertRaises(RuntimeError):
            Configuration.validate()

    def test_validate_pmkid_no_pmkid_conflict(self):
        from wifite.config import Configuration
        Configuration.use_pmkid_only = True
        Configuration.dont_use_pmkid = True
        Configuration.wps_only = False
        with self.assertRaises(RuntimeError):
            Configuration.validate()


class TestConfigurationTempDir(unittest.TestCase):
    """Verify temp directory creation and cleanup."""

    def setUp(self):
        from wifite.config import Configuration
        # Save original temp_dir and reset it for testing
        self._orig_temp_dir = Configuration.temp_dir
        Configuration.temp_dir = None

    def tearDown(self):
        from wifite.config import Configuration
        # Clean up our test temp dir, then restore the original
        Configuration.delete_temp()
        Configuration.temp_dir = self._orig_temp_dir

    def test_temp_creates_directory(self):
        from wifite.config import Configuration
        tmp = Configuration.temp()
        self.assertTrue(os.path.isdir(tmp))

    def test_temp_returns_same_dir_on_repeated_calls(self):
        from wifite.config import Configuration
        tmp1 = Configuration.temp()
        tmp2 = Configuration.temp()
        self.assertEqual(tmp1, tmp2)

    def test_temp_subfile(self):
        from wifite.config import Configuration
        tmp = Configuration.temp('myfile.cap')
        self.assertTrue(tmp.endswith('myfile.cap'))

    def test_create_temp_is_unique(self):
        from wifite.config import Configuration
        tmp1 = Configuration.create_temp()
        tmp2 = Configuration.create_temp()
        self.assertNotEqual(tmp1, tmp2)
        # Clean up
        if os.path.exists(tmp1):
            os.rmdir(tmp1)
        if os.path.exists(tmp2):
            os.rmdir(tmp2)

    def test_delete_temp_removes_directory(self):
        from wifite.config import Configuration
        tmp = Configuration.temp()
        self.assertTrue(os.path.isdir(tmp))
        Configuration.delete_temp()
        self.assertFalse(os.path.exists(tmp))


class TestConfigurationClassAttributes(unittest.TestCase):
    """Verify that all expected class-level attributes exist."""

    def test_all_expected_attributes_present(self):
        from wifite.config import Configuration
        expected_attrs = [
            'initialized', 'verbose', 'version',
            'interface', 'target_bssid', 'target_essid', 'target_channel',
            'wpa_attack_timeout', 'wpa_deauth_timeout', 'wpa_handshake_dir',
            'wps_pixie', 'wps_pin', 'wps_ignore_lock', 'wps_fail_threshold',
            'wep_pps', 'wep_timeout', 'wep_attacks',
            'use_eviltwin', 'eviltwin_port', 'eviltwin_template',
            'dual_interface_enabled', 'interface_primary', 'interface_secondary',
            'wpasec_enabled', 'wpasec_api_key', 'wpasec_url',
            'monitor_attacks', 'monitor_duration', 'monitor_channel',
            'use_tui', 'tui_refresh_rate',
            'pmkid_timeout', 'dont_use_pmkid', 'use_pmkid_only',
            'wordlist', 'wordlists', 'cracked_file',
            'temp_dir', 'existing_commands',
        ]
        for attr in expected_attrs:
            self.assertTrue(hasattr(Configuration, attr),
                            f'Configuration is missing expected attribute: {attr}')

    def test_configuration_methods_present(self):
        from wifite.config import Configuration
        expected_methods = [
            'initialize', 'load_manufacturers', 'get_monitor_mode_interface',
            'load_from_arguments', 'validate',
            '_validate_eviltwin_config', '_validate_attack_monitor_config',
            '_validate_wpasec_config', '_validate_interface_name',
            'parse_settings_args', 'parse_wep_args', 'parse_wpa_args',
            'parse_wps_args', 'parse_pmkid_args', 'parse_eviltwin_args',
            '_display_eviltwin_interface_info', 'parse_attack_monitor_args',
            'parse_dual_interface_args', 'parse_wpasec_args', 'parse_tui_args',
            'parse_encryption', 'parse_wep_attacks',
            'temp', 'create_temp', 'delete_temp',
            'cleanup_memory', 'exit_gracefully', 'dump',
        ]
        for method in expected_methods:
            self.assertTrue(hasattr(Configuration, method),
                            f'Configuration is missing expected method: {method}')


if __name__ == '__main__':
    unittest.main()
