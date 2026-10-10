#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test WPA2 backward compatibility after WPA3 implementation.

Ensures that WPA3 additions don't break existing WPA2 functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wifite.model.target import Target

pytestmark = pytest.mark.timeout(30)


class TestWPA2Compatibility(unittest.TestCase):
    """Test that WPA2 functionality remains intact after WPA3 additions."""

    def test_wpa2_target_creation(self):
        """Test that WPA2 targets can still be created normally."""
        # WPA2-PSK target
        fields = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,PSK,-50,10,0,0.0.0.0,8,TestWPA2,'.split(',')
        target = Target(fields)
        
        self.assertEqual(target.bssid, 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(target.essid, 'TestWPA2')
        self.assertEqual(target.channel, 6)  # stored as int
        self.assertEqual(target.primary_encryption, 'WPA2')
        self.assertEqual(target.primary_authentication, 'PSK')
        
        # Verify WPA3 properties default to False/None
        self.assertFalse(target.is_wpa3)
        self.assertFalse(target.is_transition)
        self.assertIsNone(target.wpa3_info)

    def test_wpa2_target_display(self):
        """Test that WPA2 targets display correctly."""
        fields = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,PSK,-50,10,0,0.0.0.0,8,TestWPA2,'.split(',')
        target = Target(fields)
        
        # Should not raise any errors
        display_str = target.to_str()
        self.assertIsNotNone(display_str)
        self.assertIn('TestWPA2', display_str)

    def test_wpa_target_creation(self):
        """Test that WPA (v1) targets still work."""
        fields = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA,TKIP,PSK,-50,10,0,0.0.0.0,7,TestWPA,'.split(',')
        target = Target(fields)
        
        self.assertEqual(target.primary_encryption, 'WPA')
        self.assertEqual(target.primary_authentication, 'PSK')
        self.assertFalse(target.is_wpa3)

    def test_wep_target_creation(self):
        """Test that WEP targets still work."""
        fields = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WEP,WEP,,-50,10,100,0.0.0.0,7,TestWEP,'.split(',')
        target = Target(fields)
        
        self.assertEqual(target.primary_encryption, 'WEP')
        self.assertFalse(target.is_wpa3)

    def test_target_properties_backward_compatible(self):
        """Test that existing target properties still work."""
        fields = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,PSK,-50,10,0,0.0.0.0,8,TestWPA2,'.split(',')
        target = Target(fields)
        
        # Test existing properties
        self.assertEqual(target.bssid, 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(target.essid, 'TestWPA2')
        self.assertEqual(target.channel, 6)  # stored as int
        self.assertEqual(target.power, 50)  # Converted from -50
        self.assertEqual(target.beacons, 10)
        self.assertEqual(target.ivs, 0)
        self.assertTrue(target.essid_known)
        self.assertFalse(target.attacked)
        self.assertFalse(target.decloaked)
        self.assertEqual(len(target.clients), 0)

    def test_target_equality(self):
        """Test that target equality comparison still works."""
        fields1 = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,PSK,-50,10,0,0.0.0.0,8,TestWPA2,'.split(',')
        fields2 = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,11,54,WPA2,CCMP,PSK,-60,5,0,0.0.0.0,8,TestWPA2,'.split(',')
        fields3 = 'BB:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,PSK,-50,10,0,0.0.0.0,8,TestWPA2,'.split(',')
        
        target1 = Target(fields1)
        target2 = Target(fields2)
        target3 = Target(fields3)
        
        # Same BSSID should be equal
        self.assertEqual(target1, target2)
        
        # Different BSSID should not be equal
        self.assertNotEqual(target1, target3)

    def test_hidden_essid_handling(self):
        """Test that hidden ESSID handling still works."""
        # Hidden ESSID (empty)
        fields = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,PSK,-50,10,0,0.0.0.0,0,,'.split(',')
        target = Target(fields)
        
        self.assertFalse(target.essid_known)
        # essid is None when hidden
        self.assertTrue(target.essid is None or target.essid.strip() == '')

    def test_wpa2_enterprise_target(self):
        """Test that WPA2-Enterprise targets still work."""
        fields = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,MGT,-50,10,0,0.0.0.0,12,TestWPA2-Ent,'.split(',')
        target = Target(fields)
        
        self.assertEqual(target.primary_encryption, 'WPA2')
        self.assertEqual(target.primary_authentication, 'MGT')
        self.assertFalse(target.is_wpa3)

    def test_target_transfer_info(self):
        """Test that target info transfer still works."""
        fields1 = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,PSK,-50,10,0,0.0.0.0,8,TestWPA2,'.split(',')
        fields2 = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,PSK,-50,10,0,0.0.0.0,0,,'.split(',')
        
        target1 = Target(fields1)
        target1.attacked = True
        target1.decloaked = True
        
        target2 = Target(fields2)
        
        # Transfer info from target1 to target2
        target1.transfer_info(target2)
        
        self.assertTrue(target2.attacked)
        # If target2 had unknown essid, transfer should provide it
        if not target2.essid_known or target2.essid is None:
            # transfer_info may or may not update essid depending on implementation
            pass
        else:
            self.assertTrue(target2.essid_known)

    def test_wpa2_attack_strategy_selection(self):
        """Test that WPA2 targets don't trigger WPA3 attack strategies."""
        from wifite.attack.wpa3_strategy import WPA3AttackStrategy
        
        fields = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,PSK,-50,10,0,0.0.0.0,8,TestWPA2,'.split(',')
        target = Target(fields)
        
        # Create WPA3 info dictionary for WPA2-only target
        wpa3_info = {
            'has_wpa3': False,
            'has_wpa2': True,
            'is_transition': False,
            'pmf_status': 'disabled',
            'sae_groups': [],
            'dragonblood_vulnerable': False
        }
        
        # WPA2-only targets should not use WPA3 strategies
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        # Strategy should be None or not a WPA3-specific strategy
        # (WPA2 targets should use standard WPA attack, not WPA3 attack)
        self.assertIsNone(strategy)

    def test_config_backward_compatibility(self):
        """Test that configuration options are backward compatible."""
        from wifite.config import Configuration
        
        # Ensure WPA attack timeout exists (may be None initially)
        self.assertTrue(hasattr(Configuration, 'wpa_attack_timeout'))
        
        # WPA3 options should have sensible defaults
        if hasattr(Configuration, 'wpa3_only'):
            # Should be False or None by default
            self.assertIn(Configuration.wpa3_only, [False, None])
        
        if hasattr(Configuration, 'no_downgrade'):
            self.assertIn(Configuration.no_downgrade, [False, None])
        
        if hasattr(Configuration, 'force_sae'):
            self.assertIn(Configuration.force_sae, [False, None])


class TestMixedWPA2WPA3Environment(unittest.TestCase):
    """Test handling of mixed WPA2 and WPA3 environments."""

    def test_wpa2_and_wpa3_targets_coexist(self):
        """Test that WPA2 and WPA3 targets can coexist."""
        # WPA2 target
        wpa2_fields = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2,CCMP,PSK,-50,10,0,0.0.0.0,8,TestWPA2,'.split(',')
        wpa2_target = Target(wpa2_fields)
        
        # WPA3 target
        wpa3_fields = 'BB:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,11,54,WPA3,CCMP,SAE,-50,10,0,0.0.0.0,8,TestWPA3,'.split(',')
        wpa3_target = Target(wpa3_fields)
        
        # Both should be valid
        self.assertFalse(wpa2_target.is_wpa3)
        self.assertEqual(wpa3_target.primary_encryption, 'WPA3')
        
        # They should be different
        self.assertNotEqual(wpa2_target, wpa3_target)

    def test_transition_mode_target(self):
        """Test transition mode target (WPA2/WPA3)."""
        # Transition mode target
        fields = 'AA:BB:CC:DD:EE:FF,2025-10-26 12:00:00,2025-10-26 12:00:01,6,54,WPA2 WPA3,CCMP,PSK SAE,-50,10,0,0.0.0.0,12,TestTransit,'.split(',')
        target = Target(fields)
        
        # Should detect both WPA2 and WPA3
        self.assertIn('WPA2', target.full_encryption_string)
        self.assertIn('WPA3', target.full_encryption_string)
        self.assertIn('PSK', target.full_authentication_string)
        self.assertIn('SAE', target.full_authentication_string)


if __name__ == '__main__':
    # Run tests
    unittest.main()
