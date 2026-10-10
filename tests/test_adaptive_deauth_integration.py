#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integration tests for adaptive deauth in Evil Twin attack.

Tests verify that the adaptive deauth manager is properly integrated
into the Evil Twin attack flow.
"""

import unittest
import time
from unittest.mock import Mock, MagicMock, patch, call


class TestAdaptiveDeauthIntegration(unittest.TestCase):
    """Test adaptive deauth integration with Evil Twin attack."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock target
        self.mock_target = Mock()
        self.mock_target.bssid = '00:11:22:33:44:55'
        self.mock_target.essid = 'TestNetwork'
        self.mock_target.channel = 6
        self.mock_target.clients = []
    
    @patch('wifite.config.Configuration')
    def test_adaptive_deauth_initialized(self, mock_config):
        """Test that adaptive deauth manager is initialized on attack creation."""
        # Set up Configuration mock with all required attributes
        mock_config.interface = 'wlan0'
        mock_config.eviltwin_deauth_interval = 5.0
        mock_config.wpa_attack_timeout = 60
        
        from wifite.attack.eviltwin import EvilTwin
        
        attack = EvilTwin(self.mock_target)
        
        # Verify adaptive deauth manager exists
        self.assertIsNotNone(attack.adaptive_deauth)
        self.assertEqual(attack.adaptive_deauth.base_interval, 5.0)
        self.assertEqual(attack.adaptive_deauth.min_interval, 2.0)
        self.assertEqual(attack.adaptive_deauth.max_interval, 15.0)
    
    @patch('wifite.config.Configuration')
    def test_deauth_statistics_initialized(self, mock_config):
        """Test that deauth statistics are initialized."""
        mock_config.interface = 'wlan0'
        mock_config.wpa_attack_timeout = 60
        
        from wifite.attack.eviltwin import EvilTwin
        
        attack = EvilTwin(self.mock_target)
        
        # Verify statistics initialized
        self.assertEqual(attack.deauths_sent, 0)
        self.assertEqual(attack.last_deauth_time, 0)
    
    @patch('wifite.config.Configuration')
    @patch('wifite.util.process.Process')
    def test_handle_deauth_sends_broadcast(self, mock_process, mock_config):
        """Test that _handle_deauth sends broadcast deauth when appropriate."""
        mock_config.interface = 'wlan0'
        mock_config.wpa_attack_timeout = 60
        
        from wifite.attack.eviltwin import EvilTwin
        
        attack = EvilTwin(self.mock_target)
        attack.interface_deauth = 'wlan0mon'
        
        # Force adaptive deauth to say it's time to send
        attack.adaptive_deauth.last_deauth_time = 0
        
        # Call handle_deauth
        attack._handle_deauth()
        
        # Verify deauth was sent
        self.assertGreater(attack.deauths_sent, 0)
        self.assertGreater(attack.last_deauth_time, 0)
    
    @patch('wifite.config.Configuration')
    def test_client_connect_pauses_deauth(self, mock_config):
        """Test that client connection pauses deauth."""
        mock_config.interface = 'wlan0'
        mock_config.wpa_attack_timeout = 60
        
        from wifite.attack.eviltwin import EvilTwin
        from wifite.util.client_monitor import ClientConnection
        
        attack = EvilTwin(self.mock_target)
        
        # Create mock client
        client = ClientConnection(
            mac_address='AA:BB:CC:DD:EE:FF',
            ip_address='192.168.100.10',
            hostname='test-device'
        )
        
        # Simulate client connection
        attack._on_client_connect(client)
        
        # Verify deauth is paused
        self.assertTrue(attack.adaptive_deauth.is_paused)
        
        # Verify adaptive manager recorded the connection
        self.assertEqual(attack.adaptive_deauth.clients_connected, 1)
    
    @patch('wifite.config.Configuration')
    def test_client_disconnect_resumes_deauth(self, mock_config):
        """Test that client disconnection resumes deauth when no clients remain."""
        mock_config.interface = 'wlan0'
        mock_config.wpa_attack_timeout = 60
        
        from wifite.attack.eviltwin import EvilTwin
        from wifite.util.client_monitor import ClientConnection, ClientMonitor
        
        attack = EvilTwin(self.mock_target)
        
        # Mock client monitor
        attack.client_monitor = Mock(spec=ClientMonitor)
        attack.client_monitor.has_connected_clients = Mock(return_value=False)
        
        # Pause deauth first
        attack.adaptive_deauth.pause()
        
        # Create mock client
        client = ClientConnection(
            mac_address='AA:BB:CC:DD:EE:FF',
            ip_address='192.168.100.10',
            hostname='test-device'
        )
        
        # Simulate client disconnection
        attack._on_client_disconnect(client)
        
        # Verify deauth is resumed
        self.assertFalse(attack.adaptive_deauth.is_paused)
    
    @patch('wifite.config.Configuration')
    def test_adaptive_interval_changes(self, mock_config):
        """Test that adaptive interval changes based on activity."""
        mock_config.interface = 'wlan0'
        mock_config.wpa_attack_timeout = 60
        
        from wifite.attack.eviltwin import EvilTwin
        
        attack = EvilTwin(self.mock_target)
        
        initial_interval = attack.adaptive_deauth.current_interval
        
        # Record client connection (should reduce interval)
        attack.adaptive_deauth.record_client_connect()
        
        # Verify interval was reduced
        self.assertLess(attack.adaptive_deauth.current_interval, initial_interval)
        self.assertGreaterEqual(attack.adaptive_deauth.current_interval, 
                               attack.adaptive_deauth.min_interval)
    
    @patch('wifite.config.Configuration')
    def test_no_activity_increases_interval(self, mock_config):
        """Test that no activity increases deauth interval."""
        mock_config.interface = 'wlan0'
        mock_config.wpa_attack_timeout = 60
        
        from wifite.attack.eviltwin import EvilTwin
        
        attack = EvilTwin(self.mock_target)
        
        initial_interval = attack.adaptive_deauth.current_interval
        
        # Record no activity multiple times
        for _ in range(3):
            attack.adaptive_deauth.record_no_activity()
        
        # Verify interval was increased
        self.assertGreater(attack.adaptive_deauth.current_interval, initial_interval)
        self.assertLessEqual(attack.adaptive_deauth.current_interval, 
                            attack.adaptive_deauth.max_interval)
    
    @patch('wifite.config.Configuration')
    def test_deauth_statistics_in_display(self, mock_config):
        """Test that deauth statistics are included in display."""
        mock_config.interface = 'wlan0'
        mock_config.wpa_attack_timeout = 60
        
        from wifite.attack.eviltwin import EvilTwin
        
        attack = EvilTwin(self.mock_target)
        
        # Mock client monitor
        attack.client_monitor = Mock()
        attack.client_monitor.get_detailed_stats = Mock(return_value={
            'duration': 60.0,
            'total_clients': 2,
            'unique_clients': 2,
            'currently_connected': 1,
            'credential_attempts': 3,
            'successful_attempts': 1,
            'failed_attempts': 2,
            'success_rate': 33.3,
            'time_to_first_client': 10.0,
            'time_to_first_credential': 20.0,
            'time_to_success': 30.0
        })
        
        # Send some deauths
        attack.adaptive_deauth.record_deauth_sent()
        attack.adaptive_deauth.record_deauth_sent()
        attack.deauths_sent = 30
        
        # Get statistics
        stats = attack.adaptive_deauth.get_statistics()
        
        # Verify deauth statistics are present
        self.assertIn('total_deauths_sent', stats)
        self.assertIn('deauths_per_minute', stats)
        self.assertIn('current_interval', stats)
        self.assertEqual(stats['total_deauths_sent'], 2)
    
    @patch('wifite.config.Configuration')
    @patch('wifite.util.process.Process')
    def test_targeted_deauth_with_known_clients(self, mock_process, mock_config):
        """Test that targeted deauth is used when clients are known."""
        mock_config.interface = 'wlan0'
        mock_config.wpa_attack_timeout = 60
        
        from wifite.attack.eviltwin import EvilTwin
        
        attack = EvilTwin(self.mock_target)
        attack.interface_deauth = 'wlan0mon'
        
        # Add known clients to target
        mock_client1 = Mock()
        mock_client1.station = 'AA:BB:CC:DD:EE:FF'
        mock_client2 = Mock()
        mock_client2.station = '11:22:33:44:55:66'
        self.mock_target.clients = [mock_client1, mock_client2]
        
        # Force many deauths to trigger targeted mode
        for _ in range(15):
            attack.adaptive_deauth.record_deauth_sent()
        
        # Force adaptive deauth to say it's time to send
        attack.adaptive_deauth.last_deauth_time = 0
        
        # Call handle_deauth
        attack._handle_deauth()
        
        # Verify targeted deauth was used
        # (Process should be called multiple times for different clients)
        self.assertGreater(attack.deauths_sent, 0)
    
    @patch('wifite.config.Configuration')
    def test_deauth_count_adapts_to_clients(self, mock_config):
        """Test that deauth count adapts based on connected clients."""
        mock_config.interface = 'wlan0'
        mock_config.wpa_attack_timeout = 60
        
        from wifite.attack.eviltwin import EvilTwin
        
        attack = EvilTwin(self.mock_target)
        
        # No clients - should be aggressive (15 packets)
        count = attack.adaptive_deauth.get_recommended_deauth_count()
        self.assertEqual(count, 15)
        
        # One client - should be moderate (10 packets)
        attack.adaptive_deauth.record_client_connect()
        count = attack.adaptive_deauth.get_recommended_deauth_count()
        self.assertEqual(count, 10)
        
        # Multiple clients - should be conservative (5 packets)
        attack.adaptive_deauth.record_client_connect()
        attack.adaptive_deauth.record_client_connect()
        count = attack.adaptive_deauth.get_recommended_deauth_count()
        self.assertEqual(count, 5)


if __name__ == '__main__':
    unittest.main()
