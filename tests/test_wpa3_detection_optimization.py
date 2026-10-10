#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for WPA3 detection optimization features.

This test suite verifies that WPA3 detection caching and performance
optimizations work correctly.
"""

import unittest
from wifite.model.target import Target
from wifite.util.wpa3 import WPA3Detector, WPA3Info


class TestWPA3DetectionOptimization(unittest.TestCase):
    """Test WPA3 detection optimization features."""

    def test_caching_returns_same_results(self):
        """Test that cached detection returns same results as fresh detection."""
        # Create a WPA3 transition mode target
        fields = [
            'AA:BB:CC:DD:EE:FF',  # BSSID
            '2024-01-01 00:00:00',  # First seen
            '2024-01-01 00:00:01',  # Last seen
            '6',  # Channel
            '54',  # Speed
            'WPA2 WPA3',  # Privacy/Encryption
            'CCMP',  # Cipher
            'PSK SAE',  # Authentication
            '-50',  # Power
            '10',  # Beacons
            '0',  # IV
            '0.0.0.0',  # LAN IP
            '8',  # ESSID length
            'TestNet',  # ESSID
            ''  # Key
        ]
        target = Target(fields)
        
        # First detection (no cache)
        result1 = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        
        # Set cache
        target.wpa3_info = WPA3Info.from_dict(result1)
        
        # Second detection (with cache)
        result2 = WPA3Detector.detect_wpa3_capability(target, use_cache=True)
        
        # Results should be identical
        self.assertEqual(result1, result2)
        self.assertTrue(result2['has_wpa3'])
        self.assertTrue(result2['has_wpa2'])
        self.assertTrue(result2['is_transition'])
        self.assertEqual(result2['pmf_status'], 'optional')

    def test_cache_bypass_with_flag(self):
        """Test that use_cache=False bypasses cache."""
        fields = [
            'AA:BB:CC:DD:EE:FF',
            '2024-01-01 00:00:00',
            '2024-01-01 00:00:01',
            '6',
            '54',
            'WPA3',
            'CCMP',
            'SAE',
            '-50',
            '10',
            '0',
            '0.0.0.0',
            '8',
            'TestNet',
            ''
        ]
        target = Target(fields)
        
        # Set fake cache data
        fake_cache = WPA3Info(
            has_wpa3=False,
            has_wpa2=True,
            is_transition=False,
            pmf_status='disabled'
        )
        target.wpa3_info = fake_cache
        
        # Detection with cache should return fake data
        cached_result = WPA3Detector.detect_wpa3_capability(target, use_cache=True)
        self.assertFalse(cached_result['has_wpa3'])
        
        # Detection without cache should return real data
        fresh_result = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        self.assertTrue(fresh_result['has_wpa3'])
        self.assertFalse(fresh_result['has_wpa2'])

    def test_helper_methods_use_cache(self):
        """Test that helper methods use cached data when available."""
        fields = [
            'AA:BB:CC:DD:EE:FF',
            '2024-01-01 00:00:00',
            '2024-01-01 00:00:01',
            '6',
            '54',
            'WPA2 WPA3',
            'CCMP',
            'PSK SAE',
            '-50',
            '10',
            '0',
            '0.0.0.0',
            '8',
            'TestNet',
            ''
        ]
        target = Target(fields)
        
        # Set cache
        wpa3_info = WPA3Info(
            has_wpa3=True,
            has_wpa2=True,
            is_transition=True,
            pmf_status='optional',
            sae_groups=[19],
            dragonblood_vulnerable=False
        )
        target.wpa3_info = wpa3_info
        
        # Helper methods should use cache
        self.assertTrue(WPA3Detector.identify_transition_mode(target))
        self.assertEqual(WPA3Detector.check_pmf_status(target), 'optional')
        self.assertEqual(WPA3Detector.get_supported_sae_groups(target), [19])

    def test_wpa3_only_detection(self):
        """Test detection of WPA3-only networks."""
        fields = [
            'AA:BB:CC:DD:EE:FF',
            '2024-01-01 00:00:00',
            '2024-01-01 00:00:01',
            '6',
            '54',
            'WPA3',
            'CCMP',
            'SAE',
            '-50',
            '10',
            '0',
            '0.0.0.0',
            '8',
            'TestNet',
            ''
        ]
        target = Target(fields)
        
        result = WPA3Detector.detect_wpa3_capability(target)
        
        self.assertTrue(result['has_wpa3'])
        self.assertFalse(result['has_wpa2'])
        self.assertFalse(result['is_transition'])
        self.assertEqual(result['pmf_status'], 'required')
        self.assertEqual(result['sae_groups'], [19])

    def test_wpa2_only_early_return(self):
        """Test that WPA2-only targets return early for performance."""
        fields = [
            'AA:BB:CC:DD:EE:FF',
            '2024-01-01 00:00:00',
            '2024-01-01 00:00:01',
            '6',
            '54',
            'WPA2',
            'CCMP',
            'PSK',
            '-50',
            '10',
            '0',
            '0.0.0.0',
            '8',
            'TestNet',
            ''
        ]
        target = Target(fields)
        
        result = WPA3Detector.detect_wpa3_capability(target)
        
        # Should return early with minimal processing
        self.assertFalse(result['has_wpa3'])
        self.assertTrue(result['has_wpa2'])
        self.assertFalse(result['is_transition'])
        self.assertEqual(result['pmf_status'], 'disabled')
        self.assertEqual(result['sae_groups'], [])
        self.assertFalse(result['dragonblood_vulnerable'])


if __name__ == '__main__':
    unittest.main()
