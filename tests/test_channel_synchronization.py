#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for channel synchronization in dual interface WPA attacks.

Tests the channel synchronization functionality including:
- Channel verification on both interfaces
- Handling of channel mismatch
- Recovery from channel setting failures
"""

import unittest
import sys
from unittest.mock import Mock, patch, MagicMock, call

# Mock sys.argv to prevent argparse from reading test arguments
original_argv = sys.argv
sys.argv = ['wifite']

from wifite.config import Configuration
from wifite.model.target import Target

# Set required Configuration attributes
Configuration.interface = 'wlan0'
Configuration.wpa_attack_timeout = 600
Configuration.wpa_deauth_timeout = 10
Configuration.interface_primary = None
Configuration.interface_secondary = None
Configuration.dual_interface_enabled = False

from wifite.attack.wpa import AttackWPA

# Restore original argv
sys.argv = original_argv


class TestChannelSynchronization(unittest.TestCase):
    """Test channel synchronization for dual interface WPA attacks."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_target = Mock(spec=Target)
        self.mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        self.mock_target.essid = 'TestNetwork'
        self.mock_target.channel = 6
        self.mock_target.encryption = 'WPA2'
        self.mock_target.power = -50
        self.mock_target.wps = False
        
        Configuration.interface = 'wlan0'
        Configuration.interface_primary = None
        Configuration.interface_secondary = None
    
    @patch('wifite.util.interface_manager.InterfaceManager')
    @patch('wifite.attack.wpa.Color')
    def test_verify_channel_sync_both_correct(self, mock_color, mock_interface_manager):
        """Test channel verification when both interfaces are on correct channel."""
        # Setup
        attack = AttackWPA(self.mock_target)
        attack.capture_interface = 'wlan0mon'
        attack.deauth_interface = 'wlan1mon'
        attack.view = None
        
        # Mock both interfaces on correct channel
        mock_interface_manager._get_interface_channel.side_effect = [6, 6]
        
        # Execute
        attack._verify_channel_sync()
        
        # Verify
        self.assertEqual(mock_interface_manager._get_interface_channel.call_count, 2)
        mock_interface_manager._get_interface_channel.assert_any_call('wlan0mon')
        mock_interface_manager._get_interface_channel.assert_any_call('wlan1mon')
        
        # Should show success message
        success_calls = [c for c in mock_color.pl.call_args_list 
                        if 'Both interfaces verified' in str(c)]
        self.assertGreater(len(success_calls), 0)
    
    @patch('wifite.util.interface_manager.InterfaceManager')
    @patch('wifite.attack.wpa.Color')
    def test_verify_channel_sync_capture_mismatch(self, mock_color, mock_interface_manager):
        """Test channel verification when capture interface is on wrong channel."""
        # Setup
        attack = AttackWPA(self.mock_target)
        attack.capture_interface = 'wlan0mon'
        attack.deauth_interface = 'wlan1mon'
        attack.view = None
        
        # Mock capture interface on wrong channel (11 instead of 6)
        mock_interface_manager._get_interface_channel.side_effect = [11, 6]
        
        # Execute
        attack._verify_channel_sync()
        
        # Verify warning was shown
        warning_calls = [c for c in mock_color.pl.call_args_list 
                        if 'Warning' in str(c) and 'wlan0mon' in str(c)]
        self.assertGreater(len(warning_calls), 0)
    
    @patch('wifite.util.interface_manager.InterfaceManager')
    @patch('wifite.attack.wpa.Color')
    def test_verify_channel_sync_deauth_mismatch(self, mock_color, mock_interface_manager):
        """Test channel verification when deauth interface is on wrong channel."""
        # Setup
        attack = AttackWPA(self.mock_target)
        attack.capture_interface = 'wlan0mon'
        attack.deauth_interface = 'wlan1mon'
        attack.view = None
        
        # Mock deauth interface on wrong channel (1 instead of 6)
        mock_interface_manager._get_interface_channel.side_effect = [6, 1]
        
        # Execute
        attack._verify_channel_sync()
        
        # Verify warning was shown
        warning_calls = [c for c in mock_color.pl.call_args_list 
                        if 'Warning' in str(c) and 'wlan1mon' in str(c)]
        self.assertGreater(len(warning_calls), 0)
    
    @patch('wifite.util.interface_manager.InterfaceManager')
    @patch('wifite.attack.wpa.Color')
    def test_verify_channel_sync_both_mismatch(self, mock_color, mock_interface_manager):
        """Test channel verification when both interfaces are on wrong channels."""
        # Setup
        attack = AttackWPA(self.mock_target)
        attack.capture_interface = 'wlan0mon'
        attack.deauth_interface = 'wlan1mon'
        attack.view = None
        
        # Mock both interfaces on wrong channels
        mock_interface_manager._get_interface_channel.side_effect = [11, 1]
        
        # Execute
        attack._verify_channel_sync()
        
        # Verify warnings for both interfaces
        warning_calls = [c for c in mock_color.pl.call_args_list 
                        if 'Warning' in str(c)]
        self.assertGreaterEqual(len(warning_calls), 2)
    
    @patch('wifite.util.process.Process')
    @patch('wifite.attack.wpa.Color')
    def test_set_interface_channels_both_success(self, mock_color, mock_process):
        """Test setting channels when both interfaces succeed."""
        # Setup
        attack = AttackWPA(self.mock_target)
        attack.capture_interface = 'wlan0mon'
        attack.deauth_interface = 'wlan1mon'
        attack.view = None
        
        # Mock successful process execution
        mock_proc = MagicMock()
        mock_process.return_value = mock_proc
        
        # Execute
        attack._set_interface_channels()
        
        # Verify both interfaces were set
        self.assertEqual(mock_process.call_count, 2)
        mock_process.assert_any_call(['iw', 'wlan0mon', 'set', 'channel', '6'])
        mock_process.assert_any_call(['iw', 'wlan1mon', 'set', 'channel', '6'])
        
        # Should show success message
        success_calls = [c for c in mock_color.pl.call_args_list 
                        if 'Both interfaces set' in str(c)]
        self.assertGreater(len(success_calls), 0)
    
    @patch('wifite.util.process.Process')
    @patch('wifite.attack.wpa.Color')
    def test_set_interface_channels_capture_fails(self, mock_color, mock_process):
        """Test setting channels when capture interface fails."""
        # Setup
        attack = AttackWPA(self.mock_target)
        attack.capture_interface = 'wlan0mon'
        attack.deauth_interface = 'wlan1mon'
        attack.view = None
        
        # Mock first call (capture) fails, second (deauth) succeeds
        def process_side_effect(cmd):
            mock_proc = MagicMock()
            if 'wlan0mon' in cmd:
                mock_proc.wait.side_effect = Exception('Channel set failed')
            return mock_proc
        
        mock_process.side_effect = process_side_effect
        
        # Execute
        attack._set_interface_channels()
        
        # Verify error was logged
        error_calls = [c for c in mock_color.pl.call_args_list 
                      if 'Error' in str(c) and 'wlan0mon' in str(c)]
        self.assertGreater(len(error_calls), 0)
        
        # Should show warning about only one interface working
        warning_calls = [c for c in mock_color.pl.call_args_list 
                        if 'Only' in str(c) and 'wlan1mon' in str(c)]
        self.assertGreater(len(warning_calls), 0)
    
    @patch('wifite.util.process.Process')
    @patch('wifite.attack.wpa.Color')
    def test_set_interface_channels_deauth_fails(self, mock_color, mock_process):
        """Test setting channels when deauth interface fails."""
        # Setup
        attack = AttackWPA(self.mock_target)
        attack.capture_interface = 'wlan0mon'
        attack.deauth_interface = 'wlan1mon'
        attack.view = None
        
        # Mock first call (capture) succeeds, second (deauth) fails
        def process_side_effect(cmd):
            mock_proc = MagicMock()
            if 'wlan1mon' in cmd:
                mock_proc.wait.side_effect = Exception('Channel set failed')
            return mock_proc
        
        mock_process.side_effect = process_side_effect
        
        # Execute
        attack._set_interface_channels()
        
        # Verify error was logged
        error_calls = [c for c in mock_color.pl.call_args_list 
                      if 'Error' in str(c) and 'wlan1mon' in str(c)]
        self.assertGreater(len(error_calls), 0)
        
        # Should show warning about only one interface working
        warning_calls = [c for c in mock_color.pl.call_args_list 
                        if 'Only' in str(c) and 'wlan0mon' in str(c)]
        self.assertGreater(len(warning_calls), 0)
    
    @patch('wifite.util.process.Process')
    @patch('wifite.attack.wpa.Color')
    def test_set_interface_channels_both_fail(self, mock_color, mock_process):
        """Test setting channels when both interfaces fail."""
        # Setup
        attack = AttackWPA(self.mock_target)
        attack.capture_interface = 'wlan0mon'
        attack.deauth_interface = 'wlan1mon'
        attack.view = None
        
        # Mock both calls fail
        mock_proc = MagicMock()
        mock_proc.wait.side_effect = Exception('Channel set failed')
        mock_process.return_value = mock_proc
        
        # Execute
        attack._set_interface_channels()
        
        # Verify error messages for both interfaces
        error_calls = [c for c in mock_color.pl.call_args_list 
                      if 'Error' in str(c)]
        self.assertGreaterEqual(len(error_calls), 2)
        
        # Should show error about both interfaces failing
        both_fail_calls = [c for c in mock_color.pl.call_args_list 
                          if 'Failed to set channel on both' in str(c)]
        self.assertGreater(len(both_fail_calls), 0)


if __name__ == '__main__':
    unittest.main()
