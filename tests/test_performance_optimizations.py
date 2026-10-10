#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Evil Twin performance optimizations (task 13.3).

Tests verify that optimizations work correctly without breaking functionality.
"""

import unittest
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock


class TestPortalCaching(unittest.TestCase):
    """Test portal template and static file caching."""
    
    def test_template_cache_initialization(self):
        """Test that template cache is initialized on server creation."""
        from wifite.attack.portal.server import PortalServer
        
        server = PortalServer(host='127.0.0.1', port=8080)
        
        # Verify cache exists
        self.assertIsNotNone(server._template_cache)
        self.assertIsInstance(server._template_cache, dict)
        
        # Verify default templates are cached
        self.assertIn('login', server._template_cache)
        self.assertIn('success', server._template_cache)
        self.assertIn('error', server._template_cache)
        
        # Verify cached templates are not empty
        self.assertTrue(len(server._template_cache['login']) > 0)
        self.assertTrue(len(server._template_cache['success']) > 0)
        self.assertTrue(len(server._template_cache['error']) > 0)
    
    def test_static_cache_initialization(self):
        """Test that static file cache is initialized."""
        from wifite.attack.portal.server import PortalServer
        
        server = PortalServer(host='127.0.0.1', port=8080)
        
        # Verify cache exists
        self.assertIsNotNone(server._static_cache)
        self.assertIsInstance(server._static_cache, dict)
    
    def test_get_cached_template(self):
        """Test retrieving cached templates."""
        from wifite.attack.portal.server import PortalServer
        
        server = PortalServer(host='127.0.0.1', port=8080)
        
        # Get cached templates
        login = server.get_cached_template('login')
        success = server.get_cached_template('success')
        error = server.get_cached_template('error')
        
        # Verify templates are returned
        self.assertIsNotNone(login)
        self.assertIsNotNone(success)
        self.assertIsNotNone(error)
        
        # Verify they contain expected content
        self.assertIn('Router', login)
        self.assertIn('Success', success)
        self.assertIn('Failed', error)
    
    def test_cache_cleanup(self):
        """Test that caches are cleaned up on deletion."""
        from wifite.attack.portal.server import PortalServer
        
        server = PortalServer(host='127.0.0.1', port=8080)
        
        # Verify caches have content
        self.assertTrue(len(server._template_cache) > 0)
        
        # Delete server
        del server
        
        # Note: Can't verify cleanup after deletion, but no errors should occur


class TestCredentialValidatorOptimizations(unittest.TestCase):
    """Test credential validator performance optimizations."""
    
    def test_cache_size_limit(self):
        """Test that validation cache enforces size limit."""
        from wifite.util.credential_validator import CredentialValidator
        
        validator = CredentialValidator(
            interface='wlan0',
            target_bssid='00:11:22:33:44:55',
            target_channel=6
        )
        
        # Verify max cache size is set
        self.assertEqual(validator.max_cache_size, 100)
        
        # Add entries using the proper method (which enforces limit)
        for i in range(150):
            validator._cache_result(f'ssid_{i}', f'password_{i}', False)
        
        # Verify cache size is within limit
        self.assertLessEqual(len(validator.validation_cache), validator.max_cache_size)
        
        # Verify it's close to max (should have pruned to ~80-100 entries)
        self.assertGreater(len(validator.validation_cache), 70)
    
    def test_reduced_validation_interval(self):
        """Test that validation interval is optimized."""
        from wifite.util.credential_validator import CredentialValidator
        
        validator = CredentialValidator(
            interface='wlan0',
            target_bssid='00:11:22:33:44:55',
            target_channel=6
        )
        
        # Verify reduced interval (1.5s instead of 2.0s)
        self.assertEqual(validator.min_validation_interval, 1.5)
    
    def test_cache_expiration(self):
        """Test that cache entries expire after 5 minutes."""
        from wifite.util.credential_validator import CredentialValidator
        
        validator = CredentialValidator(
            interface='wlan0',
            target_bssid='00:11:22:33:44:55',
            target_channel=6
        )
        
        # Add entry to cache
        validator._cache_result('test_ssid', 'test_password', True)
        
        # Verify it's in cache
        result = validator._check_cache('test_ssid', 'test_password')
        self.assertTrue(result)
        
        # Simulate time passing (mock time)
        with validator.cache_lock:
            key = ('test_ssid', 'test_password')
            # Set timestamp to 6 minutes ago
            validator.validation_cache[key] = (True, time.time() - 360)
        
        # Verify entry is expired
        result = validator._check_cache('test_ssid', 'test_password')
        self.assertIsNone(result)


class TestAdaptiveDeauth(unittest.TestCase):
    """Test adaptive deauth manager."""
    
    def test_initialization(self):
        """Test adaptive deauth manager initialization."""
        from wifite.util.adaptive_deauth import AdaptiveDeauthManager
        
        manager = AdaptiveDeauthManager(
            base_interval=5.0,
            min_interval=2.0,
            max_interval=15.0
        )
        
        # Verify initialization
        self.assertEqual(manager.base_interval, 5.0)
        self.assertEqual(manager.min_interval, 2.0)
        self.assertEqual(manager.max_interval, 15.0)
        self.assertEqual(manager.current_interval, 5.0)
        self.assertFalse(manager.is_paused)
    
    def test_should_send_deauth(self):
        """Test deauth timing logic."""
        from wifite.util.adaptive_deauth import AdaptiveDeauthManager
        
        manager = AdaptiveDeauthManager(base_interval=1.0)
        
        # Should not send immediately
        self.assertFalse(manager.should_send_deauth())
        
        # Wait for interval
        time.sleep(1.1)
        
        # Should send now
        self.assertTrue(manager.should_send_deauth())
    
    def test_pause_resume(self):
        """Test pause and resume functionality."""
        from wifite.util.adaptive_deauth import AdaptiveDeauthManager
        
        manager = AdaptiveDeauthManager()
        
        # Initially not paused
        self.assertFalse(manager.is_paused)
        
        # Pause
        manager.pause()
        self.assertTrue(manager.is_paused)
        
        # Should not send when paused
        time.sleep(1.0)
        self.assertFalse(manager.should_send_deauth())
        
        # Resume
        manager.resume()
        self.assertFalse(manager.is_paused)
    
    def test_adaptive_interval_reduction(self):
        """Test that interval reduces when clients connect."""
        from wifite.util.adaptive_deauth import AdaptiveDeauthManager
        
        manager = AdaptiveDeauthManager(base_interval=5.0)
        
        initial_interval = manager.current_interval
        
        # Record client connection
        manager.record_client_connect()
        
        # Interval should be reduced
        self.assertLess(manager.current_interval, initial_interval)
        self.assertGreaterEqual(manager.current_interval, manager.min_interval)
    
    def test_adaptive_interval_increase(self):
        """Test that interval increases with no activity."""
        from wifite.util.adaptive_deauth import AdaptiveDeauthManager
        
        manager = AdaptiveDeauthManager(base_interval=5.0)
        
        initial_interval = manager.current_interval
        
        # Record no activity multiple times
        for _ in range(3):
            manager.record_no_activity()
        
        # Interval should be increased
        self.assertGreater(manager.current_interval, initial_interval)
        self.assertLessEqual(manager.current_interval, manager.max_interval)
    
    def test_statistics(self):
        """Test statistics collection."""
        from wifite.util.adaptive_deauth import AdaptiveDeauthManager
        
        manager = AdaptiveDeauthManager()
        
        # Record some activity
        manager.record_deauth_sent()
        manager.record_deauth_sent()
        manager.record_client_connect()
        
        # Get statistics
        stats = manager.get_statistics()
        
        # Verify statistics
        self.assertEqual(stats['total_deauths_sent'], 2)
        self.assertEqual(stats['clients_connected'], 1)
        self.assertFalse(stats['is_paused'])
        self.assertGreater(stats['elapsed_time'], 0)
    
    def test_targeted_deauth_logic(self):
        """Test smart targeting logic."""
        from wifite.util.adaptive_deauth import AdaptiveDeauthManager
        
        manager = AdaptiveDeauthManager()
        
        # No clients known, should use broadcast
        self.assertFalse(manager.should_use_targeted_deauth([]))
        
        # Clients known but not enough deauths sent
        self.assertFalse(manager.should_use_targeted_deauth(['00:11:22:33:44:55']))
        
        # Send many deauths with no success
        for _ in range(15):
            manager.record_deauth_sent()
        
        # Should switch to targeted
        self.assertTrue(manager.should_use_targeted_deauth(['00:11:22:33:44:55']))
    
    def test_recommended_deauth_count(self):
        """Test burst size recommendations."""
        from wifite.util.adaptive_deauth import AdaptiveDeauthManager
        
        manager = AdaptiveDeauthManager()
        
        # No clients, should be aggressive
        count = manager.get_recommended_deauth_count()
        self.assertEqual(count, 15)
        
        # Some clients, should be moderate
        manager.record_client_connect()
        count = manager.get_recommended_deauth_count()
        self.assertEqual(count, 10)
        
        # Many clients, should be conservative
        manager.record_client_connect()
        manager.record_client_connect()
        count = manager.get_recommended_deauth_count()
        self.assertEqual(count, 5)


if __name__ == '__main__':
    unittest.main()
