#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for configuration restoration from session.
"""

import unittest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch, MagicMock
from wifite.util.session import SessionManager, SessionState, TargetState


class TestConfigurationRestoration(unittest.TestCase):
    """Test configuration restoration from session."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a mock Configuration object
        self.config = Mock()
        self.config.interface = 'wlan0mon'
        self.config.wordlist = '/usr/share/wordlists/rockyou.txt'
        self.config.wpa_attack_timeout = 500
        self.config.wps_pixie = True
        self.config.wps_pin = True
        self.config.dont_use_pmkid = False
        self.config.wps_only = False
        self.config.use_pmkid_only = False
        self.config.infinite_mode = False
        self.config.attack_max = 0
        self.config.use_tui = True
        self.config.verbose = 0
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_restore_basic_configuration(self):
        """Test restoring basic configuration parameters."""
        # Set config to None values to avoid conflicts
        self.config.interface = None
        self.config.wordlist = None
        self.config.use_tui = None
        
        # Create a session with specific configuration
        session = SessionState(
            session_id='test_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={
                'interface': 'wlan1mon',
                'wordlist': '/custom/wordlist.txt',
                'wpa_attack_timeout': 600,
                'wps_pixie': False,
                'wps_pin': False,
                'use_pmkid': True,
                'wps_only': False,
                'use_pmkid_only': True,
                'infinite_mode': True,
                'attack_max': 5,
                'use_tui': False,
                'verbose': 2
            },
            targets=[
                TargetState(
                    bssid='AA:BB:CC:DD:EE:FF',
                    essid='TestNetwork',
                    channel=6,
                    encryption='WPA2',
                    power=50,
                    wps=False
                )
            ]
        )
        
        # Mock subprocess to simulate interface check
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                stdout='Interface wlan1mon\n',
                returncode=0
            )
            
            # Restore configuration
            result = self.session_mgr.restore_configuration(session, self.config)
        
        # Verify configuration was restored
        self.assertEqual(self.config.interface, 'wlan1mon')
        self.assertEqual(self.config.wordlist, '/custom/wordlist.txt')
        self.assertEqual(self.config.wpa_attack_timeout, 600)
        self.assertFalse(self.config.wps_pixie)
        self.assertFalse(self.config.wps_pin)
        self.assertFalse(self.config.dont_use_pmkid)  # use_pmkid=True means dont_use_pmkid=False
        self.assertTrue(self.config.use_pmkid_only)
        self.assertTrue(self.config.infinite_mode)
        self.assertEqual(self.config.attack_max, 5)
        self.assertFalse(self.config.use_tui)
        self.assertEqual(self.config.verbose, 2)
        
        # Should have no warnings (interface is available)
        self.assertEqual(len(result['warnings']), 0)
        # May have conflicts if default values differ, but that's okay
        self.assertFalse(result['interface_changed'])
    
    def test_interface_not_available(self):
        """Test handling when saved interface is not available."""
        session = SessionState(
            session_id='test_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={
                'interface': 'wlan5mon',  # Non-existent interface
                'wordlist': '/usr/share/wordlists/rockyou.txt'
            },
            targets=[
                TargetState(
                    bssid='AA:BB:CC:DD:EE:FF',
                    essid='TestNetwork',
                    channel=6,
                    encryption='WPA2',
                    power=50,
                    wps=False
                )
            ]
        )
        
        # Mock subprocess to simulate interface not found
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                stdout='Interface wlan0mon\nInterface wlan1mon\n',
                returncode=0
            )
            
            # Restore configuration
            result = self.session_mgr.restore_configuration(session, self.config)
        
        # Should have warnings about interface
        self.assertGreater(len(result['warnings']), 0)
        self.assertTrue(any('wlan5mon' in w for w in result['warnings']))
        self.assertTrue(result['interface_changed'])
    
    def test_conflicting_command_line_flags(self):
        """Test detection of conflicting command-line flags."""
        # Set different values in config (simulating command-line flags)
        self.config.wordlist = '/different/wordlist.txt'
        self.config.wpa_attack_timeout = 300
        self.config.use_tui = False
        
        session = SessionState(
            session_id='test_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={
                'interface': 'wlan0mon',
                'wordlist': '/original/wordlist.txt',
                'wpa_attack_timeout': 600,
                'use_tui': True
            },
            targets=[
                TargetState(
                    bssid='AA:BB:CC:DD:EE:FF',
                    essid='TestNetwork',
                    channel=6,
                    encryption='WPA2',
                    power=50,
                    wps=False
                )
            ]
        )
        
        # Mock subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                stdout='Interface wlan0mon\n',
                returncode=0
            )
            
            # Restore configuration
            result = self.session_mgr.restore_configuration(session, self.config)
        
        # Should have conflicts detected
        self.assertGreater(len(result['conflicts']), 0)
        
        # Configuration should be overridden with session values
        self.assertEqual(self.config.wordlist, '/original/wordlist.txt')
        self.assertEqual(self.config.wpa_attack_timeout, 600)
        self.assertTrue(self.config.use_tui)
    
    def test_interface_check_failure(self):
        """Test handling when interface check fails."""
        session = SessionState(
            session_id='test_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={
                'interface': 'wlan0mon',
                'wordlist': '/usr/share/wordlists/rockyou.txt'
            },
            targets=[
                TargetState(
                    bssid='AA:BB:CC:DD:EE:FF',
                    essid='TestNetwork',
                    channel=6,
                    encryption='WPA2',
                    power=50,
                    wps=False
                )
            ]
        )
        
        # Mock subprocess to raise exception
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError('iw command not found')
            
            # Restore configuration
            result = self.session_mgr.restore_configuration(session, self.config)
        
        # Should have warning about interface check failure
        self.assertGreater(len(result['warnings']), 0)
        self.assertTrue(any('verify interface' in w for w in result['warnings']))
        self.assertTrue(result['interface_changed'])
    
    def test_restore_with_missing_config_values(self):
        """Test restoration when some config values are missing."""
        session = SessionState(
            session_id='test_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={
                'interface': 'wlan0mon',
                # Missing wordlist, timeouts, etc.
            },
            targets=[
                TargetState(
                    bssid='AA:BB:CC:DD:EE:FF',
                    essid='TestNetwork',
                    channel=6,
                    encryption='WPA2',
                    power=50,
                    wps=False
                )
            ]
        )
        
        # Store original values
        original_wordlist = self.config.wordlist
        original_timeout = self.config.wpa_attack_timeout
        
        # Mock subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                stdout='Interface wlan0mon\n',
                returncode=0
            )
            
            # Restore configuration
            result = self.session_mgr.restore_configuration(session, self.config)
        
        # Original values should be preserved when not in session
        self.assertEqual(self.config.wordlist, original_wordlist)
        self.assertEqual(self.config.wpa_attack_timeout, original_timeout)
        
        # Interface should still be restored
        self.assertEqual(self.config.interface, 'wlan0mon')


if __name__ == '__main__':
    unittest.main()
