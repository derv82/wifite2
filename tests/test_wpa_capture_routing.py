#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for WPA capture method routing logic.

Tests the routing between hcxdumptool and airodump-ng capture methods
based on configuration and tool availability.
"""

import unittest
import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

pytestmark = pytest.mark.timeout(30)

# Mock sys.argv to prevent argparse from reading test arguments
original_argv = sys.argv
sys.argv = ['wifite']

from wifite.config import Configuration
from wifite.model.target import Target
from wifite.model.interface_info import InterfaceAssignment

# Set required Configuration attributes
Configuration.interface = 'wlan0'
Configuration.wpa_attack_timeout = 600
Configuration.wpa_deauth_timeout = 10
Configuration.use_hcxdump = False

from wifite.attack.wpa import AttackWPA

# Restore original argv
sys.argv = original_argv


class TestWPACaptureRouting(unittest.TestCase):
    """Test WPA capture method routing logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_target = Mock(spec=Target)
        self.mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        self.mock_target.essid = 'TestNetwork'
        self.mock_target.channel = 6
        self.mock_target.encryption = 'WPA2'
        self.mock_target.power = -50
        self.mock_target.wps = False
        
        # Create dual interface assignment
        self.assignment = InterfaceAssignment(
            attack_type='wpa',
            primary='wlan0',
            secondary='wlan1',
            primary_role='Handshake capture',
            secondary_role='Deauthentication'
        )
        
        # Reset configuration
        Configuration.use_hcxdump = False
    
    @patch('wifite.tools.hcxdumptool.HcxDumpTool')
    @patch('wifite.tools.airmon.Airmon')
    @patch('wifite.util.color.Color')
    @patch('wifite.attack.wpa.AttackWPA._capture_handshake_dual_hcxdump')
    def test_routing_with_flag_enabled_and_tool_available(self, mock_capture, mock_color, mock_airmon, mock_hcxdump):
        """Test routing to hcxdump when flag enabled and tool available."""
        # Enable hcxdump mode
        Configuration.use_hcxdump = True
        
        # Mock tool availability and version check
        mock_hcxdump.exists.return_value = True
        mock_hcxdump.check_minimum_version.return_value = True
        mock_hcxdump.dependency_url = 'https://github.com/ZerBea/hcxdumptool'
        
        # Mock monitor mode
        mock_airmon.start.side_effect = ['wlan0mon', 'wlan1mon']
        mock_airmon.stop.return_value = None
        
        # Mock capture method
        mock_handshake = Mock()
        mock_capture.return_value = mock_handshake
        
        # Create attack with assignment
        attack = AttackWPA(self.mock_target)
        attack.interface_assignment = self.assignment
        
        # Run dual interface attack
        result = attack._run_dual_interface()
        
        # Verify hcxdump checks were performed
        mock_hcxdump.exists.assert_called_once()
        mock_hcxdump.check_minimum_version.assert_called_once_with('6.2.0')
        
        # Verify hcxdump capture method was called (task 4 implemented)
        mock_capture.assert_called_once()
        
        # Verify result
        self.assertEqual(result, mock_handshake)
    
    @patch('wifite.tools.hcxdumptool.HcxDumpTool')
    @patch('wifite.tools.airmon.Airmon')
    @patch('wifite.util.color.Color')
    @patch('wifite.attack.wpa.AttackWPA._capture_handshake_dual_airodump')
    def test_fallback_when_tool_unavailable(self, mock_capture, mock_color, mock_airmon, mock_hcxdump):
        """Test fallback to airodump when hcxdumptool unavailable."""
        # Enable hcxdump mode
        Configuration.use_hcxdump = True
        
        # Mock tool not available
        mock_hcxdump.exists.return_value = False
        mock_hcxdump.dependency_url = 'https://github.com/ZerBea/hcxdumptool'
        
        # Mock monitor mode
        mock_airmon.start.side_effect = ['wlan0mon', 'wlan1mon']
        mock_airmon.stop.return_value = None
        
        # Mock capture method
        mock_handshake = Mock()
        mock_capture.return_value = mock_handshake
        
        # Create attack with assignment
        attack = AttackWPA(self.mock_target)
        attack.interface_assignment = self.assignment
        
        # Run dual interface attack
        result = attack._run_dual_interface()
        
        # Verify tool existence check
        mock_hcxdump.exists.assert_called_once()
        
        # Verify version check was NOT called (tool doesn't exist)
        mock_hcxdump.check_minimum_version.assert_not_called()
        
        # Verify fallback to airodump
        mock_capture.assert_called_once()
        
        # Verify result
        self.assertEqual(result, mock_handshake)
    
    @patch('wifite.tools.hcxdumptool.HcxDumpTool')
    @patch('wifite.tools.airmon.Airmon')
    @patch('wifite.util.color.Color')
    @patch('wifite.attack.wpa.AttackWPA._capture_handshake_dual_airodump')
    def test_fallback_when_version_insufficient(self, mock_capture, mock_color, mock_airmon, mock_hcxdump):
        """Test fallback to airodump when hcxdumptool version insufficient."""
        # Enable hcxdump mode
        Configuration.use_hcxdump = True
        
        # Mock tool available but version insufficient
        mock_hcxdump.exists.return_value = True
        mock_hcxdump.check_minimum_version.return_value = False
        mock_hcxdump.check_version.return_value = '6.0.0'
        mock_hcxdump.dependency_url = 'https://github.com/ZerBea/hcxdumptool'
        
        # Mock monitor mode
        mock_airmon.start.side_effect = ['wlan0mon', 'wlan1mon']
        mock_airmon.stop.return_value = None
        
        # Mock capture method
        mock_handshake = Mock()
        mock_capture.return_value = mock_handshake
        
        # Create attack with assignment
        attack = AttackWPA(self.mock_target)
        attack.interface_assignment = self.assignment
        
        # Run dual interface attack
        result = attack._run_dual_interface()
        
        # Verify checks were performed
        mock_hcxdump.exists.assert_called_once()
        mock_hcxdump.check_minimum_version.assert_called_once_with('6.2.0')
        mock_hcxdump.check_version.assert_called_once()
        
        # Verify fallback to airodump
        mock_capture.assert_called_once()
        
        # Verify result
        self.assertEqual(result, mock_handshake)
    
    @patch('wifite.tools.hcxdumptool.HcxDumpTool')
    @patch('wifite.tools.airmon.Airmon')
    @patch('wifite.util.color.Color')
    @patch('wifite.attack.wpa.AttackWPA._capture_handshake_dual_airodump')
    def test_default_behavior_without_flag(self, mock_capture, mock_color, mock_airmon, mock_hcxdump):
        """Test default behavior uses airodump when flag not set."""
        # Disable hcxdump mode (default)
        Configuration.use_hcxdump = False
        
        # Mock monitor mode
        mock_airmon.start.side_effect = ['wlan0mon', 'wlan1mon']
        mock_airmon.stop.return_value = None
        
        # Mock capture method
        mock_handshake = Mock()
        mock_capture.return_value = mock_handshake
        
        # Create attack with assignment
        attack = AttackWPA(self.mock_target)
        attack.interface_assignment = self.assignment
        
        # Run dual interface attack
        result = attack._run_dual_interface()
        
        # Verify hcxdump checks were NOT performed
        mock_hcxdump.exists.assert_not_called()
        mock_hcxdump.check_minimum_version.assert_not_called()
        
        # Verify airodump capture was called
        mock_capture.assert_called_once()
        
        # Verify result
        self.assertEqual(result, mock_handshake)


if __name__ == '__main__':
    unittest.main()
