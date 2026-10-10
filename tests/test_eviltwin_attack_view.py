#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Evil Twin Attack View TUI integration.
"""

import unittest
from unittest.mock import Mock, MagicMock
import time


class MockTarget:
    """Mock Target object for testing."""
    
    def __init__(self, essid="TestNetwork", bssid="AA:BB:CC:DD:EE:FF", 
                 channel=6, power=-50, encryption="WPA2"):
        self.essid = essid
        self.bssid = bssid
        self.channel = channel
        self.power = power
        self.encryption = encryption
        self.clients = []


class TestEvilTwinAttackView(unittest.TestCase):
    """Test Evil Twin Attack View functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_controller = Mock()
        self.mock_controller.is_running = False
        self.mock_controller.start = Mock()
        self.mock_controller.update = Mock()
        
        self.target = MockTarget()
    
    def test_eviltwin_view_exists(self):
        """Test that EvilTwinAttackView class exists."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        self.assertTrue(EvilTwinAttackView is not None)
    
    def test_eviltwin_view_initialization(self):
        """Test that EvilTwinAttackView initializes correctly."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        self.assertEqual(view.attack_type, "Evil Twin Attack")
        self.assertEqual(view.attack_phase, "Initializing")
        self.assertEqual(view.rogue_ap_status, "Stopped")
        self.assertEqual(view.portal_status, "Stopped")
        self.assertEqual(view.deauth_status, "Stopped")
        self.assertEqual(len(view.connected_clients), 0)
        self.assertEqual(len(view.credential_attempts), 0)
    
    def test_set_attack_phase(self):
        """Test setting attack phase."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        view.set_attack_phase("Running")
        self.assertEqual(view.attack_phase, "Running")
        
        view.set_attack_phase("Validating")
        self.assertEqual(view.attack_phase, "Validating")
    
    def test_update_rogue_ap_status(self):
        """Test updating rogue AP status."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        view.update_rogue_ap_status("Running", channel=6, ssid="TestAP")
        self.assertEqual(view.rogue_ap_status, "Running")
        self.assertEqual(view.metrics.get('AP Channel'), 6)
        self.assertEqual(view.metrics.get('AP SSID'), "TestAP")
    
    def test_update_portal_status(self):
        """Test updating portal status."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        view.update_portal_status("Running", url="http://192.168.100.1")
        self.assertEqual(view.portal_status, "Running")
        self.assertEqual(view.portal_url, "http://192.168.100.1")
    
    def test_update_deauth_status(self):
        """Test updating deauth status."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        view.update_deauth_status("Running", count=100)
        self.assertEqual(view.deauth_status, "Running")
        self.assertEqual(view.deauths_sent, 100)
    
    def test_add_connected_client(self):
        """Test adding connected clients."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        # Add first client
        view.add_connected_client("AA:BB:CC:DD:EE:01", "192.168.100.10", "Client1")
        self.assertEqual(len(view.connected_clients), 1)
        self.assertEqual(view.connected_clients[0]['mac'], "AA:BB:CC:DD:EE:01")
        self.assertEqual(view.connected_clients[0]['ip'], "192.168.100.10")
        self.assertEqual(view.connected_clients[0]['hostname'], "Client1")
        
        # Add second client
        view.add_connected_client("AA:BB:CC:DD:EE:02", "192.168.100.11", "Client2")
        self.assertEqual(len(view.connected_clients), 2)
        
        # Update existing client
        view.add_connected_client("AA:BB:CC:DD:EE:01", "192.168.100.15", "UpdatedClient1")
        self.assertEqual(len(view.connected_clients), 2)  # Should not add duplicate
        self.assertEqual(view.connected_clients[0]['ip'], "192.168.100.15")
    
    def test_remove_connected_client(self):
        """Test removing disconnected clients."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        # Add clients
        view.add_connected_client("AA:BB:CC:DD:EE:01", "192.168.100.10")
        view.add_connected_client("AA:BB:CC:DD:EE:02", "192.168.100.11")
        self.assertEqual(len(view.connected_clients), 2)
        
        # Remove one client
        view.remove_connected_client("AA:BB:CC:DD:EE:01")
        self.assertEqual(len(view.connected_clients), 1)
        self.assertEqual(view.connected_clients[0]['mac'], "AA:BB:CC:DD:EE:02")
    
    def test_add_credential_attempt(self):
        """Test adding credential attempts."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        # Add failed attempt
        view.add_credential_attempt("AA:BB:CC:DD:EE:01", "wrongpass", False)
        self.assertEqual(len(view.credential_attempts), 1)
        self.assertEqual(view.failed_attempts, 1)
        self.assertEqual(view.successful_attempts, 0)
        
        # Add successful attempt
        view.add_credential_attempt("AA:BB:CC:DD:EE:02", "correctpass", True)
        self.assertEqual(len(view.credential_attempts), 2)
        self.assertEqual(view.failed_attempts, 1)
        self.assertEqual(view.successful_attempts, 1)
        self.assertEqual(view.attack_phase, "Validating")
    
    def test_increment_deauths(self):
        """Test incrementing deauth counter."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        self.assertEqual(view.deauths_sent, 0)
        
        view.increment_deauths(10)
        self.assertEqual(view.deauths_sent, 10)
        
        view.increment_deauths(5)
        self.assertEqual(view.deauths_sent, 15)
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        # No attempts
        self.assertEqual(view._get_success_rate(), 0.0)
        
        # Add attempts
        view.add_credential_attempt("AA:BB:CC:DD:EE:01", "pass1", False)
        view.add_credential_attempt("AA:BB:CC:DD:EE:02", "pass2", False)
        view.add_credential_attempt("AA:BB:CC:DD:EE:03", "pass3", True)
        view.add_credential_attempt("AA:BB:CC:DD:EE:04", "pass4", True)
        
        # 2 successful out of 4 = 50%
        self.assertEqual(view._get_success_rate(), 50.0)
    
    def test_format_status(self):
        """Test status formatting with indicators."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        self.assertEqual(view._format_status("Running"), "✓ Running")
        self.assertEqual(view._format_status("Stopped"), "✗ Stopped")
        self.assertEqual(view._format_status("Paused"), "⏸ Paused")
        self.assertIn("Starting", view._format_status("Starting"))
    
    def test_timing_metrics(self):
        """Test timing metrics tracking."""
        from wifite.ui.attack_view import EvilTwinAttackView
        
        view = EvilTwinAttackView(self.mock_controller, self.target)
        
        # Initially no timing metrics
        self.assertIsNone(view.time_to_first_client)
        self.assertIsNone(view.time_to_first_credential)
        self.assertIsNone(view.time_to_success)
        
        # Simulate attack start
        view.attack_start_time = time.time()
        
        # Add first client
        time.sleep(0.1)
        view.add_connected_client("AA:BB:CC:DD:EE:01")
        self.assertIsNotNone(view.time_to_first_client)
        self.assertGreater(view.time_to_first_client, 0)
        
        # Add first credential
        time.sleep(0.1)
        view.add_credential_attempt("AA:BB:CC:DD:EE:01", "pass", False)
        self.assertIsNotNone(view.time_to_first_credential)
        self.assertGreater(view.time_to_first_credential, view.time_to_first_client)
        
        # Add successful credential
        time.sleep(0.1)
        view.add_credential_attempt("AA:BB:CC:DD:EE:01", "correctpass", True)
        self.assertIsNotNone(view.time_to_success)
        self.assertGreater(view.time_to_success, view.time_to_first_credential)


if __name__ == '__main__':
    unittest.main()
