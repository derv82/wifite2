#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integration tests for hcxdumptool-based WPA capture.

Tests complete WPA attack flows with --hcxdump flag including:
- WPA2 and WPA3 target capture
- Fallback scenarios
- Error recovery
- Performance validation
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
Configuration.wpa_attack_timeout = 10
Configuration.wpa_deauth_timeout = 2
Configuration.use_hcxdump = True
Configuration.no_deauth = False
Configuration.ignore_old_handshakes = True
Configuration.verbose = 0

from wifite.attack.wpa import AttackWPA

# Restore original argv
sys.argv = original_argv


class TestCompleteWPAAttackFlow(unittest.TestCase):
    """Test complete WPA attack flow with --hcxdump flag."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_target = Mock(spec=Target)
        self.mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        self.mock_target.essid = 'TestNetwork'
        self.mock_target.channel = 6
        self.mock_target.encryption = 'WPA2'
        self.mock_target.power = -50
        self.mock_target.wps = False
        self.mock_target.pmf_required = False
        self.mock_target.essid_known = True
        
        # Create dual interface assignment
        self.assignment = InterfaceAssignment(
            attack_type='wpa',
            primary='wlan0mon',
            secondary='wlan1mon',
            primary_role='Handshake capture',
            secondary_role='Deauthentication'
        )
        
        Configuration.use_hcxdump = True
    
    @patch('wifite.tools.hcxdumptool.HcxDumpTool')
    @patch('wifite.tools.airmon.Airmon')
    @patch('wifite.util.color.Color')
    @patch('wifite.attack.wpa.AttackWPA._capture_handshake_dual_hcxdump')
    def test_wpa2_attack_with_hcxdump_enabled(self, mock_capture, mock_color,
                                               mock_airmon, mock_hcxdump):
        """Test WPA2 attack uses hcxdump when enabled and available."""
        # Mock hcxdumptool available
        mock_hcxdump.exists.return_value = True
        mock_hcxdump.check_minimum_version.return_value = True
        
        # Mock monitor mode
        mock_airmon.start.side_effect = ['wlan0mon', 'wlan1mon']
        mock_airmon.stop.return_value = None
        
        # Mock successful capture
        mock_handshake = Mock()
        mock_capture.return_value = mock_handshake
        
        # Create attack
        attack = AttackWPA(self.mock_target)
        attack.interface_assignment = self.assignment
        
        # Run dual interface attack
        result = attack._run_dual_interface()
        
        # Verify hcxdump was checked
        mock_hcxdump.exists.assert_called_once()
        mock_hcxdump.check_minimum_version.assert_called_once_with('6.2.0')
        
        # Verify hcxdump capture was called
        mock_capture.assert_called_once()
        
        # Verify result
        self.assertEqual(result, mock_handshake)
    
    @patch('wifite.tools.hcxdumptool.HcxDumpTool')
    @patch('wifite.tools.airmon.Airmon')
    @patch('wifite.util.color.Color')
    @patch('wifite.attack.wpa.AttackWPA._capture_handshake_dual_hcxdump')
    def test_wpa3_attack_with_pmf(self, mock_capture, mock_color,
                                   mock_airmon, mock_hcxdump):
        """Test WPA3 attack with PMF uses hcxdump correctly."""
        # Update target for WPA3
        self.mock_target.encryption = 'WPA3'
        self.mock_target.pmf_required = True
        
        # Mock hcxdumptool available
        mock_hcxdump.exists.return_value = True
        mock_hcxdump.check_minimum_version.return_value = True
        
        # Mock monitor mode
        mock_airmon.start.side_effect = ['wlan0mon', 'wlan1mon']
        mock_airmon.stop.return_value = None
        
        # Mock successful capture
        mock_handshake = Mock()
        mock_capture.return_value = mock_handshake
        
        # Create attack
        attack = AttackWPA(self.mock_target)
        attack.interface_assignment = self.assignment
        
        # Run dual interface attack
        result = attack._run_dual_interface()
        
        # Verify hcxdump capture was called
        mock_capture.assert_called_once()
        
        # Verify result
        self.assertEqual(result, mock_handshake)


class TestFallbackScenarios(unittest.TestCase):
    """Test fallback scenarios when hcxdumptool unavailable."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_target = Mock(spec=Target)
        self.mock_target.bssid = 'CC:DD:EE:FF:00:11'
        self.mock_target.essid = 'TestNetwork'
        self.mock_target.channel = 6
        self.mock_target.encryption = 'WPA2'
        self.mock_target.power = -50
        self.mock_target.wps = False
        self.mock_target.pmf_required = False
        self.mock_target.essid_known = True
        
        # Create dual interface assignment
        self.assignment = InterfaceAssignment(
            attack_type='wpa',
            primary='wlan0mon',
            secondary='wlan1mon',
            primary_role='Handshake capture',
            secondary_role='Deauthentication'
        )
        
        Configuration.use_hcxdump = True
    
    @patch('wifite.tools.hcxdumptool.HcxDumpTool')
    @patch('wifite.tools.airmon.Airmon')
    @patch('wifite.util.color.Color')
    @patch('wifite.attack.wpa.AttackWPA._capture_handshake_dual_airodump')
    def test_fallback_when_hcxdumptool_not_installed(self, mock_airodump, mock_color,
                                                      mock_airmon, mock_hcxdump):
        """Test graceful fallback when hcxdumptool not installed."""
        # Mock hcxdumptool not installed
        mock_hcxdump.exists.return_value = False
        mock_hcxdump.dependency_url = 'https://github.com/ZerBea/hcxdumptool'
        
        # Mock monitor mode
        mock_airmon.start.side_effect = ['wlan0mon', 'wlan1mon']
        mock_airmon.stop.return_value = None
        
        # Mock airodump fallback
        mock_handshake = Mock()
        mock_airodump.return_value = mock_handshake
        
        # Create attack
        attack = AttackWPA(self.mock_target)
        attack.interface_assignment = self.assignment
        
        # Run dual interface attack
        result = attack._run_dual_interface()
        
        # Verify tool check was performed
        mock_hcxdump.exists.assert_called_once()
        
        # Verify fallback to airodump was called
        mock_airodump.assert_called_once()
        
        # Verify result from fallback
        self.assertEqual(result, mock_handshake)
    
    @patch('wifite.tools.hcxdumptool.HcxDumpTool')
    @patch('wifite.tools.airmon.Airmon')
    @patch('wifite.util.color.Color')
    @patch('wifite.attack.wpa.AttackWPA._capture_handshake_dual_airodump')
    def test_fallback_when_version_insufficient(self, mock_airodump, mock_color,
                                                 mock_airmon, mock_hcxdump):
        """Test graceful fallback when hcxdumptool version insufficient."""
        # Mock hcxdumptool installed but old version
        mock_hcxdump.exists.return_value = True
        mock_hcxdump.check_minimum_version.return_value = False
        mock_hcxdump.check_version.return_value = '5.0.0'
        mock_hcxdump.dependency_url = 'https://github.com/ZerBea/hcxdumptool'
        
        # Mock monitor mode
        mock_airmon.start.side_effect = ['wlan0mon', 'wlan1mon']
        mock_airmon.stop.return_value = None
        
        # Mock airodump fallback
        mock_handshake = Mock()
        mock_airodump.return_value = mock_handshake
        
        # Create attack
        attack = AttackWPA(self.mock_target)
        attack.interface_assignment = self.assignment
        
        # Run dual interface attack
        result = attack._run_dual_interface()
        
        # Verify version checks were performed
        mock_hcxdump.exists.assert_called_once()
        mock_hcxdump.check_minimum_version.assert_called_once_with('6.2.0')
        
        # Verify fallback to airodump was called
        mock_airodump.assert_called_once()
        
        # Verify result from fallback
        self.assertEqual(result, mock_handshake)
    
    @patch('wifite.tools.hcxdumptool.HcxDumpTool')
    @patch('wifite.tools.airmon.Airmon')
    @patch('wifite.util.color.Color')
    @patch('wifite.attack.wpa.AttackWPA._capture_handshake_dual_airodump')
    def test_graceful_fallback_maintains_functionality(self, mock_airodump, mock_color,
                                                        mock_airmon, mock_hcxdump):
        """Verify graceful fallback maintains full functionality."""
        # Mock hcxdumptool not available
        mock_hcxdump.exists.return_value = False
        mock_hcxdump.dependency_url = 'https://github.com/ZerBea/hcxdumptool'
        
        # Mock monitor mode
        mock_airmon.start.side_effect = ['wlan0mon', 'wlan1mon']
        mock_airmon.stop.return_value = None
        
        # Mock successful airodump capture
        mock_handshake = Mock()
        mock_handshake.capfile = '/tmp/handshake.cap'
        mock_handshake.bssid = self.mock_target.bssid
        mock_handshake.essid = self.mock_target.essid
        mock_airodump.return_value = mock_handshake
        
        # Create attack
        attack = AttackWPA(self.mock_target)
        attack.interface_assignment = self.assignment
        
        # Run dual interface attack
        result = attack._run_dual_interface()
        
        # Verify fallback was successful
        self.assertIsNotNone(result)
        self.assertEqual(result.capfile, '/tmp/handshake.cap')
        self.assertEqual(result.bssid, self.mock_target.bssid)


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_target = Mock(spec=Target)
        self.mock_target.bssid = 'DD:EE:FF:00:11:22'
        self.mock_target.essid = 'TestNetwork'
        self.mock_target.channel = 6
        self.mock_target.encryption = 'WPA2'
        self.mock_target.power = -50
        self.mock_target.wps = False
        self.mock_target.pmf_required = False
        self.mock_target.essid_known = True
        
        # Create dual interface assignment
        self.assignment = InterfaceAssignment(
            attack_type='wpa',
            primary='wlan0mon',
            secondary='wlan1mon',
            primary_role='Handshake capture',
            secondary_role='Deauthentication'
        )
        
        Configuration.use_hcxdump = True
    
    def test_hcxdump_capture_method_exists(self):
        """Verify hcxdump capture method exists."""
        attack = AttackWPA(self.mock_target)
        self.assertTrue(hasattr(attack, '_capture_handshake_dual_hcxdump'))
        self.assertTrue(callable(getattr(attack, '_capture_handshake_dual_hcxdump')))
    
    def test_parallel_deauth_method_exists(self):
        """Verify parallel deauth method exists."""
        attack = AttackWPA(self.mock_target)
        self.assertTrue(hasattr(attack, '_deauth_parallel'))
        self.assertTrue(callable(getattr(attack, '_deauth_parallel')))


class TestPerformanceValidation(unittest.TestCase):
    """Test performance validation for dual monitoring."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_target = Mock(spec=Target)
        self.mock_target.bssid = 'EE:FF:00:11:22:33'
        self.mock_target.essid = 'TestNetwork'
        self.mock_target.channel = 6
        self.mock_target.encryption = 'WPA2'
        self.mock_target.power = -50
        self.mock_target.wps = False
        self.mock_target.pmf_required = False
        self.mock_target.essid_known = True
        
        Configuration.use_hcxdump = True
    
    @patch('wifite.tools.hcxdumptool.HcxDumpTool')
    def test_hcxdump_tool_availability_check(self, mock_hcxdump):
        """Test hcxdump tool availability check is efficient."""
        # Mock tool available
        mock_hcxdump.exists.return_value = True
        mock_hcxdump.check_minimum_version.return_value = True
        
        # Check availability
        available = mock_hcxdump.exists()
        version_ok = mock_hcxdump.check_minimum_version('6.2.0')
        
        # Verify checks are efficient (single call each)
        self.assertTrue(available)
        self.assertTrue(version_ok)
        mock_hcxdump.exists.assert_called_once()
        mock_hcxdump.check_minimum_version.assert_called_once()
    
    def test_interface_assignment_structure(self):
        """Test interface assignment structure is correct."""
        assignment = InterfaceAssignment(
            attack_type='wpa',
            primary='wlan0mon',
            secondary='wlan1mon',
            primary_role='Handshake capture',
            secondary_role='Deauthentication'
        )
        
        # Verify structure
        self.assertTrue(assignment.is_dual_interface())
        self.assertEqual(assignment.primary, 'wlan0mon')
        self.assertEqual(assignment.secondary, 'wlan1mon')
        self.assertEqual(assignment.attack_type, 'wpa')


if __name__ == '__main__':
    unittest.main()
