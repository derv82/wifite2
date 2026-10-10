#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for WPA3Detector class.

Tests WPA3 capability detection, transition mode detection, PMF status,
and SAE group extraction.
"""

import unittest
from unittest.mock import Mock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wifite.util.wpa3 import WPA3Detector, WPA3Info


class TestWPA3Detector(unittest.TestCase):
    """Test suite for WPA3Detector functionality."""

    def test_detect_wpa3_only_network(self):
        """Test detection of WPA3-only network."""
        # Create mock target with WPA3-only
        target = Mock()
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        result = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        self.assertTrue(result['has_wpa3'])
        self.assertFalse(result['has_wpa2'])
        self.assertFalse(result['is_transition'])
        self.assertEqual(result['pmf_status'], WPA3Detector.PMF_REQUIRED)
        self.assertEqual(result['sae_groups'], [19])
        self.assertFalse(result['dragonblood_vulnerable'])

    def test_detect_wpa2_only_network(self):
        """Test detection of WPA2-only network."""
        target = Mock()
        target.full_encryption_string = 'WPA2'
        target.full_authentication_string = 'PSK'
        target.primary_encryption = 'WPA2'
        target.primary_authentication = 'PSK'
        target.wpa3_info = None
        
        result = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        self.assertFalse(result['has_wpa3'])
        self.assertTrue(result['has_wpa2'])
        self.assertFalse(result['is_transition'])
        self.assertEqual(result['pmf_status'], WPA3Detector.PMF_DISABLED)
        self.assertEqual(result['sae_groups'], [])
        self.assertFalse(result['dragonblood_vulnerable'])

    def test_detect_transition_mode_network(self):
        """Test detection of WPA2/WPA3 transition mode network."""
        target = Mock()
        target.full_encryption_string = 'WPA2 WPA3'
        target.full_authentication_string = 'PSK SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        result = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        self.assertTrue(result['has_wpa3'])
        self.assertTrue(result['has_wpa2'])
        self.assertTrue(result['is_transition'])
        self.assertEqual(result['pmf_status'], WPA3Detector.PMF_OPTIONAL)
        self.assertEqual(result['sae_groups'], [19])
        self.assertFalse(result['dragonblood_vulnerable'])

    def test_identify_transition_mode_true(self):
        """Test identify_transition_mode returns True for transition networks."""
        target = Mock()
        target.full_encryption_string = 'WPA2 WPA3'
        target.full_authentication_string = 'PSK SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        result = WPA3Detector.identify_transition_mode(target)
        
        self.assertTrue(result)

    def test_identify_transition_mode_false(self):
        """Test identify_transition_mode returns False for WPA3-only networks."""
        target = Mock()
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        result = WPA3Detector.identify_transition_mode(target)
        
        self.assertFalse(result)

    def test_check_pmf_status_required(self):
        """Test PMF status detection for WPA3-only (PMF required)."""
        target = Mock()
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        result = WPA3Detector.check_pmf_status(target)
        
        self.assertEqual(result, WPA3Detector.PMF_REQUIRED)

    def test_check_pmf_status_optional(self):
        """Test PMF status detection for transition mode (PMF optional)."""
        target = Mock()
        target.full_encryption_string = 'WPA2 WPA3'
        target.full_authentication_string = 'PSK SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        result = WPA3Detector.check_pmf_status(target)
        
        self.assertEqual(result, WPA3Detector.PMF_OPTIONAL)

    def test_check_pmf_status_disabled(self):
        """Test PMF status detection for WPA2-only (PMF disabled)."""
        target = Mock()
        target.full_encryption_string = 'WPA2'
        target.full_authentication_string = 'PSK'
        target.primary_encryption = 'WPA2'
        target.primary_authentication = 'PSK'
        target.wpa3_info = None
        
        result = WPA3Detector.check_pmf_status(target)
        
        self.assertEqual(result, WPA3Detector.PMF_DISABLED)

    def test_get_supported_sae_groups_default(self):
        """Test SAE group extraction returns default group 19."""
        target = Mock()
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        result = WPA3Detector.get_supported_sae_groups(target)
        
        self.assertEqual(result, [19])

    def test_get_supported_sae_groups_wpa2_only(self):
        """Test SAE group extraction for WPA2-only returns empty list."""
        target = Mock()
        target.full_encryption_string = 'WPA2'
        target.full_authentication_string = 'PSK'
        target.primary_encryption = 'WPA2'
        target.primary_authentication = 'PSK'
        target.wpa3_info = None
        
        result = WPA3Detector.get_supported_sae_groups(target)
        
        self.assertEqual(result, [])

    def test_caching_mechanism(self):
        """Test that detection results are cached properly."""
        target = Mock()
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        
        # Create cached WPA3Info
        cached_info = WPA3Info(
            has_wpa3=True,
            has_wpa2=False,
            is_transition=False,
            pmf_status=WPA3Detector.PMF_REQUIRED,
            sae_groups=[19],
            dragonblood_vulnerable=False
        )
        target.wpa3_info = cached_info
        
        # Should return cached results
        result = WPA3Detector.detect_wpa3_capability(target, use_cache=True)
        
        self.assertEqual(result, cached_info.to_dict())

    def test_cache_bypass(self):
        """Test that cache can be bypassed with use_cache=False."""
        target = Mock()
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        
        # Create cached WPA3Info with wrong data
        cached_info = WPA3Info(
            has_wpa3=False,  # Wrong
            has_wpa2=True,   # Wrong
            is_transition=True,  # Wrong
            pmf_status=WPA3Detector.PMF_DISABLED,  # Wrong
            sae_groups=[],
            dragonblood_vulnerable=False
        )
        target.wpa3_info = cached_info
        
        # Should bypass cache and detect correctly
        result = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        self.assertTrue(result['has_wpa3'])
        self.assertFalse(result['has_wpa2'])
        self.assertFalse(result['is_transition'])
        self.assertEqual(result['pmf_status'], WPA3Detector.PMF_REQUIRED)

    def test_dragonblood_vulnerability_detection(self):
        """Test Dragonblood vulnerability detection (currently always False for default groups)."""
        target = Mock()
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = 'SAE'
        target.primary_encryption = 'WPA3'
        target.primary_authentication = 'SAE'
        target.wpa3_info = None
        
        result = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        # Default group 19 is not vulnerable
        self.assertFalse(result['dragonblood_vulnerable'])

    def test_has_wpa3_helper_full_encryption(self):
        """Test _has_wpa3 helper with full_encryption_string."""
        target = Mock()
        target.full_encryption_string = 'WPA3'
        target.full_authentication_string = ''
        target.primary_encryption = ''
        target.primary_authentication = ''
        
        result = WPA3Detector._has_wpa3(target)
        
        self.assertTrue(result)

    def test_has_wpa3_helper_primary_encryption(self):
        """Test _has_wpa3 helper with primary_encryption."""
        target = Mock()
        target.full_encryption_string = ''
        target.full_authentication_string = ''
        target.primary_encryption = 'WPA3'
        target.primary_authentication = ''
        
        result = WPA3Detector._has_wpa3(target)
        
        self.assertTrue(result)

    def test_has_wpa3_helper_sae_authentication(self):
        """Test _has_wpa3 helper with SAE authentication."""
        target = Mock()
        target.full_encryption_string = ''
        target.full_authentication_string = 'SAE'
        target.primary_encryption = ''
        target.primary_authentication = ''
        
        result = WPA3Detector._has_wpa3(target)
        
        self.assertTrue(result)

    def test_has_wpa2_helper_full_encryption(self):
        """Test _has_wpa2 helper with full_encryption_string."""
        target = Mock()
        target.full_encryption_string = 'WPA2'
        target.full_authentication_string = ''
        target.primary_encryption = ''
        target.primary_authentication = ''
        
        result = WPA3Detector._has_wpa2(target)
        
        self.assertTrue(result)

    def test_has_wpa2_helper_psk_authentication(self):
        """Test _has_wpa2 helper with PSK authentication."""
        target = Mock()
        target.full_encryption_string = ''
        target.full_authentication_string = 'PSK'
        target.primary_encryption = ''
        target.primary_authentication = ''
        
        result = WPA3Detector._has_wpa2(target)
        
        self.assertTrue(result)


class TestWPA3Info(unittest.TestCase):
    """Test suite for WPA3Info data class."""

    def test_wpa3info_initialization(self):
        """Test WPA3Info initialization with all parameters."""
        info = WPA3Info(
            has_wpa3=True,
            has_wpa2=False,
            is_transition=False,
            pmf_status=WPA3Detector.PMF_REQUIRED,
            sae_groups=[19, 20],
            dragonblood_vulnerable=False
        )
        
        self.assertTrue(info.has_wpa3)
        self.assertFalse(info.has_wpa2)
        self.assertFalse(info.is_transition)
        self.assertEqual(info.pmf_status, WPA3Detector.PMF_REQUIRED)
        self.assertEqual(info.sae_groups, [19, 20])
        self.assertFalse(info.dragonblood_vulnerable)

    def test_wpa3info_default_initialization(self):
        """Test WPA3Info initialization with default parameters."""
        info = WPA3Info()
        
        self.assertFalse(info.has_wpa3)
        self.assertFalse(info.has_wpa2)
        self.assertFalse(info.is_transition)
        self.assertEqual(info.pmf_status, WPA3Detector.PMF_DISABLED)
        self.assertEqual(info.sae_groups, [])
        self.assertFalse(info.dragonblood_vulnerable)

    def test_wpa3info_to_dict(self):
        """Test WPA3Info serialization to dictionary."""
        info = WPA3Info(
            has_wpa3=True,
            has_wpa2=True,
            is_transition=True,
            pmf_status=WPA3Detector.PMF_OPTIONAL,
            sae_groups=[19],
            dragonblood_vulnerable=False
        )
        
        result = info.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['has_wpa3'])
        self.assertTrue(result['has_wpa2'])
        self.assertTrue(result['is_transition'])
        self.assertEqual(result['pmf_status'], WPA3Detector.PMF_OPTIONAL)
        self.assertEqual(result['sae_groups'], [19])
        self.assertFalse(result['dragonblood_vulnerable'])

    def test_wpa3info_from_dict(self):
        """Test WPA3Info deserialization from dictionary."""
        data = {
            'has_wpa3': True,
            'has_wpa2': True,
            'is_transition': True,
            'pmf_status': WPA3Detector.PMF_OPTIONAL,
            'sae_groups': [19, 20],
            'dragonblood_vulnerable': False
        }
        
        info = WPA3Info.from_dict(data)
        
        self.assertTrue(info.has_wpa3)
        self.assertTrue(info.has_wpa2)
        self.assertTrue(info.is_transition)
        self.assertEqual(info.pmf_status, WPA3Detector.PMF_OPTIONAL)
        self.assertEqual(info.sae_groups, [19, 20])
        self.assertFalse(info.dragonblood_vulnerable)

    def test_wpa3info_get_method(self):
        """Test WPA3Info dict-like get method."""
        info = WPA3Info(has_wpa3=True, has_wpa2=False)
        
        self.assertTrue(info.get('has_wpa3'))
        self.assertFalse(info.get('has_wpa2'))
        self.assertIsNone(info.get('nonexistent_key'))
        self.assertEqual(info.get('nonexistent_key', 'default'), 'default')

    def test_wpa3info_repr(self):
        """Test WPA3Info string representation."""
        info = WPA3Info(has_wpa3=True, has_wpa2=False)
        
        repr_str = repr(info)
        
        self.assertIn('WPA3Info', repr_str)
        self.assertIn('has_wpa3=True', repr_str)
        self.assertIn('has_wpa2=False', repr_str)


if __name__ == '__main__':
    unittest.main()
