#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for WPA3AttackStrategy class.

Tests strategy selection, priority, downgrade eligibility, and PMF handling.
"""

import unittest
from unittest.mock import Mock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wifite.attack.wpa3_strategy import WPA3AttackStrategy
from wifite.util.wpa3 import WPA3Detector


class TestWPA3AttackStrategy(unittest.TestCase):
    """Test suite for WPA3AttackStrategy functionality."""

    def test_select_strategy_downgrade_priority(self):
        """Test that downgrade strategy has highest priority for transition mode."""
        target = Mock()
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': True,
            'is_transition': True,
            'pmf_status': WPA3Detector.PMF_OPTIONAL,
            'sae_groups': [19],
            'dragonblood_vulnerable': False
        }
        
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        self.assertEqual(strategy, WPA3AttackStrategy.DOWNGRADE)

    def test_select_strategy_dragonblood_priority(self):
        """Test that dragonblood strategy is selected for vulnerable targets."""
        target = Mock()
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': False,
            'is_transition': False,
            'pmf_status': WPA3Detector.PMF_REQUIRED,
            'sae_groups': [22],
            'dragonblood_vulnerable': True
        }
        
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        self.assertEqual(strategy, WPA3AttackStrategy.DRAGONBLOOD)

    def test_select_strategy_sae_capture(self):
        """Test that SAE capture is selected when deauth is possible."""
        target = Mock()
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': False,
            'is_transition': False,
            'pmf_status': WPA3Detector.PMF_OPTIONAL,
            'sae_groups': [19],
            'dragonblood_vulnerable': False
        }
        
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        self.assertEqual(strategy, WPA3AttackStrategy.SAE_CAPTURE)

    def test_select_strategy_passive(self):
        """Test that passive strategy is selected when PMF is required."""
        target = Mock()
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': False,
            'is_transition': False,
            'pmf_status': WPA3Detector.PMF_REQUIRED,
            'sae_groups': [19],
            'dragonblood_vulnerable': False
        }
        
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        self.assertEqual(strategy, WPA3AttackStrategy.PASSIVE)

    def test_select_strategy_wpa2_only_returns_none(self):
        """Test that WPA2-only targets return None strategy."""
        target = Mock()
        wpa3_info = {
            'has_wpa3': False,
            'has_wpa2': True,
            'is_transition': False,
            'pmf_status': WPA3Detector.PMF_DISABLED,
            'sae_groups': [],
            'dragonblood_vulnerable': False
        }
        
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        
        self.assertIsNone(strategy)

    def test_can_use_downgrade_true(self):
        """Test downgrade eligibility for transition mode networks."""
        wpa3_info = {
            'is_transition': True
        }
        
        result = WPA3AttackStrategy.can_use_downgrade(wpa3_info)
        
        self.assertTrue(result)

    def test_can_use_downgrade_false(self):
        """Test downgrade not eligible for WPA3-only networks."""
        wpa3_info = {
            'is_transition': False
        }
        
        result = WPA3AttackStrategy.can_use_downgrade(wpa3_info)
        
        self.assertFalse(result)

    def test_can_use_deauth_pmf_disabled(self):
        """Test deauth is possible when PMF is disabled."""
        wpa3_info = {
            'pmf_status': WPA3Detector.PMF_DISABLED
        }
        
        result = WPA3AttackStrategy.can_use_deauth(wpa3_info)
        
        self.assertTrue(result)

    def test_can_use_deauth_pmf_optional(self):
        """Test deauth is possible when PMF is optional."""
        wpa3_info = {
            'pmf_status': WPA3Detector.PMF_OPTIONAL
        }
        
        result = WPA3AttackStrategy.can_use_deauth(wpa3_info)
        
        self.assertTrue(result)

    def test_can_use_deauth_pmf_required(self):
        """Test deauth is not possible when PMF is required."""
        wpa3_info = {
            'pmf_status': WPA3Detector.PMF_REQUIRED
        }
        
        result = WPA3AttackStrategy.can_use_deauth(wpa3_info)
        
        self.assertFalse(result)

    def test_should_use_dragonblood_true(self):
        """Test dragonblood should be used for vulnerable targets."""
        wpa3_info = {
            'dragonblood_vulnerable': True
        }
        
        result = WPA3AttackStrategy.should_use_dragonblood(wpa3_info)
        
        self.assertTrue(result)

    def test_should_use_dragonblood_false(self):
        """Test dragonblood should not be used for non-vulnerable targets."""
        wpa3_info = {
            'dragonblood_vulnerable': False
        }
        
        result = WPA3AttackStrategy.should_use_dragonblood(wpa3_info)
        
        self.assertFalse(result)

    def test_get_attack_priority_transition_mode(self):
        """Test attack priority for transition mode (highest)."""
        wpa3_info = {
            'is_transition': True,
            'dragonblood_vulnerable': False,
            'pmf_status': WPA3Detector.PMF_OPTIONAL
        }
        
        priority = WPA3AttackStrategy.get_attack_priority(wpa3_info)
        
        self.assertEqual(priority, 100)

    def test_get_attack_priority_dragonblood(self):
        """Test attack priority for dragonblood vulnerable targets."""
        wpa3_info = {
            'is_transition': False,
            'dragonblood_vulnerable': True,
            'pmf_status': WPA3Detector.PMF_REQUIRED
        }
        
        priority = WPA3AttackStrategy.get_attack_priority(wpa3_info)
        
        self.assertEqual(priority, 75)

    def test_get_attack_priority_pmf_optional(self):
        """Test attack priority for PMF optional/disabled."""
        wpa3_info = {
            'is_transition': False,
            'dragonblood_vulnerable': False,
            'pmf_status': WPA3Detector.PMF_OPTIONAL
        }
        
        priority = WPA3AttackStrategy.get_attack_priority(wpa3_info)
        
        self.assertEqual(priority, 50)

    def test_get_attack_priority_pmf_required(self):
        """Test attack priority for PMF required (lowest)."""
        wpa3_info = {
            'is_transition': False,
            'dragonblood_vulnerable': False,
            'pmf_status': WPA3Detector.PMF_REQUIRED
        }
        
        priority = WPA3AttackStrategy.get_attack_priority(wpa3_info)
        
        self.assertEqual(priority, 25)

    def test_get_strategy_description_downgrade(self):
        """Test strategy description for downgrade."""
        description = WPA3AttackStrategy.get_strategy_description(
            WPA3AttackStrategy.DOWNGRADE
        )
        
        self.assertIn('Downgrade', description)
        self.assertIsInstance(description, str)

    def test_get_strategy_description_dragonblood(self):
        """Test strategy description for dragonblood."""
        description = WPA3AttackStrategy.get_strategy_description(
            WPA3AttackStrategy.DRAGONBLOOD
        )
        
        self.assertIn('Dragonblood', description)
        self.assertIsInstance(description, str)

    def test_get_strategy_description_sae_capture(self):
        """Test strategy description for SAE capture."""
        description = WPA3AttackStrategy.get_strategy_description(
            WPA3AttackStrategy.SAE_CAPTURE
        )
        
        self.assertIn('SAE', description)
        self.assertIsInstance(description, str)

    def test_get_strategy_description_passive(self):
        """Test strategy description for passive."""
        description = WPA3AttackStrategy.get_strategy_description(
            WPA3AttackStrategy.PASSIVE
        )
        
        self.assertIn('Passive', description)
        self.assertIsInstance(description, str)

    def test_get_strategy_description_unknown(self):
        """Test strategy description for unknown strategy."""
        description = WPA3AttackStrategy.get_strategy_description('unknown')
        
        self.assertEqual(description, 'Unknown Strategy')

    def test_get_strategy_explanation_downgrade(self):
        """Test strategy explanation for downgrade."""
        explanation = WPA3AttackStrategy.get_strategy_explanation(
            WPA3AttackStrategy.DOWNGRADE
        )
        
        self.assertIn('WPA2', explanation)
        self.assertIn('WPA3', explanation)
        self.assertIsInstance(explanation, str)

    def test_get_strategy_explanation_dragonblood(self):
        """Test strategy explanation for dragonblood."""
        explanation = WPA3AttackStrategy.get_strategy_explanation(
            WPA3AttackStrategy.DRAGONBLOOD
        )
        
        self.assertIn('Dragonblood', explanation)
        self.assertIsInstance(explanation, str)

    def test_get_strategy_explanation_sae_capture(self):
        """Test strategy explanation for SAE capture."""
        explanation = WPA3AttackStrategy.get_strategy_explanation(
            WPA3AttackStrategy.SAE_CAPTURE
        )
        
        self.assertIn('SAE', explanation)
        self.assertIsInstance(explanation, str)

    def test_get_strategy_explanation_passive(self):
        """Test strategy explanation for passive."""
        explanation = WPA3AttackStrategy.get_strategy_explanation(
            WPA3AttackStrategy.PASSIVE
        )
        
        self.assertIn('PMF', explanation)
        self.assertIsInstance(explanation, str)

    def test_format_strategy_display(self):
        """Test formatted strategy display output."""
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': True,
            'is_transition': True,
            'pmf_status': WPA3Detector.PMF_OPTIONAL,
            'sae_groups': [19, 20],
            'dragonblood_vulnerable': False
        }
        
        display = WPA3AttackStrategy.format_strategy_display(
            WPA3AttackStrategy.DOWNGRADE,
            wpa3_info
        )
        
        self.assertIsInstance(display, str)
        self.assertIn('Attack Strategy', display)
        self.assertIn('Downgrade', display)
        self.assertIn('WPA3: Yes', display)
        self.assertIn('WPA2: Yes', display)
        self.assertIn('Transition Mode: Yes', display)
        self.assertIn('PMF Status: optional', display)
        self.assertIn('SAE Groups: 19, 20', display)

    def test_format_strategy_display_dragonblood_vulnerable(self):
        """Test formatted display includes dragonblood vulnerability."""
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': False,
            'is_transition': False,
            'pmf_status': WPA3Detector.PMF_REQUIRED,
            'sae_groups': [22],
            'dragonblood_vulnerable': True
        }
        
        display = WPA3AttackStrategy.format_strategy_display(
            WPA3AttackStrategy.DRAGONBLOOD,
            wpa3_info
        )
        
        self.assertIn('Dragonblood Vulnerable: Yes', display)

    def test_strategy_priority_order(self):
        """Test that strategy selection follows correct priority order."""
        # Create target with all conditions met
        target = Mock()
        
        # Transition mode + dragonblood + PMF optional
        # Should select downgrade (highest priority)
        wpa3_info = {
            'has_wpa3': True,
            'has_wpa2': True,
            'is_transition': True,
            'pmf_status': WPA3Detector.PMF_OPTIONAL,
            'sae_groups': [22],
            'dragonblood_vulnerable': True
        }
        
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        self.assertEqual(strategy, WPA3AttackStrategy.DOWNGRADE)
        
        # No transition mode, but dragonblood + PMF optional
        # Should select dragonblood (second priority)
        wpa3_info['is_transition'] = False
        wpa3_info['has_wpa2'] = False
        
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        self.assertEqual(strategy, WPA3AttackStrategy.DRAGONBLOOD)
        
        # No transition, no dragonblood, but PMF optional
        # Should select SAE capture (third priority)
        wpa3_info['dragonblood_vulnerable'] = False
        wpa3_info['sae_groups'] = [19]
        
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        self.assertEqual(strategy, WPA3AttackStrategy.SAE_CAPTURE)
        
        # No transition, no dragonblood, PMF required
        # Should select passive (last priority)
        wpa3_info['pmf_status'] = WPA3Detector.PMF_REQUIRED
        
        strategy = WPA3AttackStrategy.select_strategy(target, wpa3_info)
        self.assertEqual(strategy, WPA3AttackStrategy.PASSIVE)


if __name__ == '__main__':
    unittest.main()
