#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integration tests for WPA3-SAE attack flows.

Tests full downgrade flow, SAE capture flow, passive capture flow,
and cracking integration.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wifite.util.wpa3 import WPA3Detector, WPA3Info
from wifite.attack.wpa3_strategy import WPA3AttackStrategy

pytestmark = pytest.mark.timeout(30)


class TestWPA3DowngradeFlow(unittest.TestCase):
    """Test full downgrade attack flow."""

    def test_downgrade_flow_transition_mode_target(self):
        """Test complete downgrade flow for transition mode target."""
        # Create transition mode target
        target = Mock()
        target.bssid = 'AA:BB:CC:DD:EE:FF'
        target.essid = 'TestTransition'
        target.channel = '6'
        target.full_encryption_string = 'WPA2 WPA3'
        target.full_authentication_string = 'PSK SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        # Detect WPA3 capabilities
        wpa3_info = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        # Verify transition mode detected
        self.assertTrue(wpa3_info['has_wpa3'])
        self.assertTrue(wpa3_info['has_wpa2'])
        self.assertTrue(wpa3_info['is_transition'])
        
        # Select strategy
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        # Verify downgrade strategy selected
        self.assertEqual(strategy, WPA3AttackStrategy.DOWNGRADE)
        
        # Verify downgrade is eligible
        self.assertTrue(WPA3AttackStrategy.can_use_downgrade(wpa3_info))

    def test_downgrade_flow_wpa3_only_target(self):
        """Test that WPA3-only targets don't use downgrade."""
        # Create WPA3-only target
        target = Mock()
        target.bssid = 'AA:BB:CC:DD:EE:FF'
        target.essid = 'TestWPA3Only'
        target.channel = '6'
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        # Detect WPA3 capabilities
        wpa3_info = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        # Verify WPA3-only detected
        self.assertTrue(wpa3_info['has_wpa3'])
        self.assertFalse(wpa3_info['has_wpa2'])
        self.assertFalse(wpa3_info['is_transition'])
        
        # Select strategy
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        # Verify downgrade strategy NOT selected
        self.assertNotEqual(strategy, WPA3AttackStrategy.DOWNGRADE)
        
        # Verify downgrade is not eligible
        self.assertFalse(WPA3AttackStrategy.can_use_downgrade(wpa3_info))


class TestWPA3SAECaptureFlow(unittest.TestCase):
    """Test SAE handshake capture flow."""

    def test_sae_capture_flow_pmf_optional(self):
        """Test SAE capture flow when PMF is optional (deauth allowed)."""
        # Create WPA3 target with PMF optional
        target = Mock()
        target.bssid = 'AA:BB:CC:DD:EE:FF'
        target.essid = 'TestWPA3'
        target.channel = '6'
        target.full_encryption_string = 'WPA2 WPA3'
        target.full_authentication_string = 'PSK SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        # Detect WPA3 capabilities
        wpa3_info = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        # Verify PMF is optional
        self.assertEqual(wpa3_info['pmf_status'], WPA3Detector.PMF_OPTIONAL)
        
        # Verify deauth is allowed
        self.assertTrue(WPA3AttackStrategy.can_use_deauth(wpa3_info))
        
        # Select strategy (should be downgrade for transition mode)
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        # For non-transition WPA3, verify SAE capture would be selected
        wpa3_info['is_transition'] = False
        wpa3_info['has_wpa2'] = False
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        self.assertEqual(strategy, WPA3AttackStrategy.SAE_CAPTURE)

    def test_sae_capture_flow_pmf_required(self):
        """Test SAE capture flow when PMF is required (deauth blocked)."""
        # Create WPA3-only target with PMF required
        target = Mock()
        target.bssid = 'AA:BB:CC:DD:EE:FF'
        target.essid = 'TestWPA3Only'
        target.channel = '6'
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        # Detect WPA3 capabilities
        wpa3_info = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        # Verify PMF is required
        self.assertEqual(wpa3_info['pmf_status'], WPA3Detector.PMF_REQUIRED)
        
        # Verify deauth is blocked
        self.assertFalse(WPA3AttackStrategy.can_use_deauth(wpa3_info))
        
        # Select strategy
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        # Should select passive capture
        self.assertEqual(strategy, WPA3AttackStrategy.PASSIVE)


class TestWPA3PassiveCaptureFlow(unittest.TestCase):
    """Test passive capture flow (PMF prevents deauth)."""

    def test_passive_capture_flow(self):
        """Test passive capture flow for PMF-protected targets."""
        # Create WPA3-only target with PMF required
        target = Mock()
        target.bssid = 'AA:BB:CC:DD:EE:FF'
        target.essid = 'TestWPA3PMF'
        target.channel = '6'
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        # Detect WPA3 capabilities
        wpa3_info = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        # Verify PMF required
        self.assertEqual(wpa3_info['pmf_status'], WPA3Detector.PMF_REQUIRED)
        
        # Select strategy
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        # Verify passive strategy selected
        self.assertEqual(strategy, WPA3AttackStrategy.PASSIVE)
        
        # Verify deauth is not allowed
        self.assertFalse(WPA3AttackStrategy.can_use_deauth(wpa3_info))

    def test_passive_capture_priority(self):
        """Test that passive capture has lowest priority."""
        # Create WPA3-only target with PMF required
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': False,
            'is_transition': False,
            'pmf_status': WPA3Detector.PMF_REQUIRED,
            'sae_groups': [19],
            'dragonblood_vulnerable': False
        }
        
        # Get priority
        priority = WPA3AttackStrategy.get_attack_priority(wpa3_info)
        
        # Should have lowest priority (25)
        self.assertEqual(priority, 25)


class TestWPA3CrackingIntegration(unittest.TestCase):
    """Test cracking integration with captured handshakes."""

    def test_hashcat_format_conversion(self):
        """Test that SAE handshake can be converted to hashcat format."""
        from wifite.model.sae_handshake import SAEHandshake
        import tempfile
        
        # Create temporary capture file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.cap')
        temp_file.close()
        capfile = temp_file.name
        
        try:
            # Create SAEHandshake object
            hs = SAEHandshake(capfile, 'AA:BB:CC:DD:EE:FF', 'TestWPA3')
            
            # Verify initialization
            self.assertEqual(hs.capfile, capfile)
            self.assertEqual(hs.bssid, 'AA:BB:CC:DD:EE:FF')
            self.assertEqual(hs.essid, 'TestWPA3')
            
            # Verify hash_file is initially None
            self.assertIsNone(hs.hash_file)
        finally:
            if os.path.exists(capfile):
                os.remove(capfile)

    def test_tool_availability_check(self):
        """Test that tool availability is checked correctly."""
        from wifite.model.sae_handshake import SAEHandshake
        
        # Check tools
        tools = SAEHandshake.check_tools()
        
        # Verify all required tools are checked
        self.assertIn('hcxpcapngtool', tools)
        self.assertIn('tshark', tools)
        self.assertIn('hashcat', tools)
        
        # All values should be boolean
        for tool, available in tools.items():
            self.assertIsInstance(available, bool)


class TestWPA3StrategyFallback(unittest.TestCase):
    """Test strategy fallback mechanisms."""

    def test_downgrade_fallback_to_sae_capture(self):
        """Test fallback from downgrade to SAE capture."""
        # Create transition mode target
        target = Mock()
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': True,
            'is_transition': True,
            'pmf_status': WPA3Detector.PMF_OPTIONAL,
            'sae_groups': [19],
            'dragonblood_vulnerable': False
        }
        
        # Primary strategy should be downgrade
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        self.assertEqual(strategy, WPA3AttackStrategy.DOWNGRADE)
        
        # If downgrade fails, fallback should be SAE capture
        # (simulated by removing transition mode)
        wpa3_info['is_transition'] = False
        wpa3_info['has_wpa2'] = False
        
        fallback_strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        self.assertEqual(fallback_strategy, WPA3AttackStrategy.SAE_CAPTURE)

    def test_dragonblood_fallback_to_sae_capture(self):
        """Test fallback from dragonblood to SAE capture."""
        # Create vulnerable target
        target = Mock()
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': False,
            'is_transition': False,
            'pmf_status': WPA3Detector.PMF_OPTIONAL,
            'sae_groups': [22],
            'dragonblood_vulnerable': True
        }
        
        # Primary strategy should be dragonblood
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        self.assertEqual(strategy, WPA3AttackStrategy.DRAGONBLOOD)
        
        # If dragonblood fails, fallback should be SAE capture
        # (simulated by removing vulnerability)
        wpa3_info['dragonblood_vulnerable'] = False
        wpa3_info['sae_groups'] = [19]
        
        fallback_strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        self.assertEqual(fallback_strategy, WPA3AttackStrategy.SAE_CAPTURE)

    def test_sae_capture_fallback_to_passive(self):
        """Test fallback from SAE capture to passive when PMF blocks deauth."""
        # Create target with PMF optional
        target = Mock()
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': False,
            'is_transition': False,
            'pmf_status': WPA3Detector.PMF_OPTIONAL,
            'sae_groups': [19],
            'dragonblood_vulnerable': False
        }
        
        # Primary strategy should be SAE capture
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        self.assertEqual(strategy, WPA3AttackStrategy.SAE_CAPTURE)
        
        # If PMF becomes required, fallback should be passive
        wpa3_info['pmf_status'] = WPA3Detector.PMF_REQUIRED
        
        fallback_strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        self.assertEqual(fallback_strategy, WPA3AttackStrategy.PASSIVE)


class TestWPA3EndToEndFlow(unittest.TestCase):
    """Test complete end-to-end WPA3 attack flows."""

    def test_complete_transition_mode_flow(self):
        """Test complete flow for transition mode target."""
        # 1. Create target
        target = Mock()
        target.bssid = 'AA:BB:CC:DD:EE:FF'
        target.essid = 'TestTransition'
        target.channel = '6'
        target.full_encryption_string = 'WPA2 WPA3'
        target.full_authentication_string = 'PSK SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        # 2. Detect capabilities
        wpa3_info = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        # 3. Verify detection
        self.assertTrue(wpa3_info['has_wpa3'])
        self.assertTrue(wpa3_info['has_wpa2'])
        self.assertTrue(wpa3_info['is_transition'])
        self.assertEqual(wpa3_info['pmf_status'], WPA3Detector.PMF_OPTIONAL)
        
        # 4. Select strategy
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        # 5. Verify downgrade selected
        self.assertEqual(strategy, WPA3AttackStrategy.DOWNGRADE)
        
        # 6. Verify attack priority
        priority = WPA3AttackStrategy.get_attack_priority(wpa3_info)
        self.assertEqual(priority, 100)  # Highest priority

    def test_complete_wpa3_only_flow(self):
        """Test complete flow for WPA3-only target."""
        # 1. Create target
        target = Mock()
        target.bssid = 'AA:BB:CC:DD:EE:FF'
        target.essid = 'TestWPA3Only'
        target.channel = '6'
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        # 2. Detect capabilities
        wpa3_info = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        # 3. Verify detection
        self.assertTrue(wpa3_info['has_wpa3'])
        self.assertFalse(wpa3_info['has_wpa2'])
        self.assertFalse(wpa3_info['is_transition'])
        self.assertEqual(wpa3_info['pmf_status'], WPA3Detector.PMF_REQUIRED)
        
        # 4. Select strategy
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        # 5. Verify passive selected (PMF required)
        self.assertEqual(strategy, WPA3AttackStrategy.PASSIVE)
        
        # 6. Verify attack priority
        priority = WPA3AttackStrategy.get_attack_priority(wpa3_info)
        self.assertEqual(priority, 25)  # Lowest priority

    def test_complete_vulnerable_target_flow(self):
        """Test complete flow for dragonblood vulnerable target."""
        # 1. Create target
        target = Mock()
        target.bssid = 'AA:BB:CC:DD:EE:FF'
        target.essid = 'TestVulnerable'
        target.channel = '6'
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        # 2. Detect capabilities (simulate vulnerable groups)
        wpa3_info = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        # Manually set vulnerable groups for testing
        wpa3_info['sae_groups'] = [22]
        wpa3_info['dragonblood_vulnerable'] = True
        
        # 3. Verify detection
        self.assertTrue(wpa3_info['has_wpa3'])
        self.assertTrue(wpa3_info['dragonblood_vulnerable'])
        
        # 4. Select strategy
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        # 5. Verify dragonblood selected
        self.assertEqual(strategy, WPA3AttackStrategy.DRAGONBLOOD)
        
        # 6. Verify attack priority
        priority = WPA3AttackStrategy.get_attack_priority(wpa3_info)
        self.assertEqual(priority, 75)  # High priority


if __name__ == '__main__':
    unittest.main()
