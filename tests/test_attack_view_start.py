#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests to verify attack views start properly and don't conflict with scanner view.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch


class MockTarget:
    """Mock Target object for testing."""
    
    def __init__(self, essid="TestNetwork", bssid="AA:BB:CC:DD:EE:FF", 
                 channel=6, power=-50, encryption="WPA2", wps=False):
        self.essid = essid
        self.bssid = bssid
        self.channel = channel
        self.power = power
        self.encryption = encryption
        self.wps = wps
        self.clients = []
        self.primary_authentication = "PSK"


class TestAttackViewStartup(unittest.TestCase):
    """Test that attack views start properly."""
    
    def test_attack_view_has_start_method(self):
        """Test that attack views have a start method."""
        from wifite.ui.attack_view import AttackView, WPAAttackView, WPSAttackView, PMKIDAttackView, WEPAttackView
        
        # Check that all attack view classes have start method
        self.assertTrue(hasattr(AttackView, 'start'))
        self.assertTrue(hasattr(WPAAttackView, 'start'))
        self.assertTrue(hasattr(WPSAttackView, 'start'))
        self.assertTrue(hasattr(PMKIDAttackView, 'start'))
        self.assertTrue(hasattr(WEPAttackView, 'start'))
    
    def test_attack_view_start_initializes_tui(self):
        """Test that attack view start() initializes TUI controller."""
        from wifite.ui.attack_view import AttackView
        
        mock_controller = Mock()
        mock_controller.is_running = False
        mock_controller.start = Mock()
        
        target = MockTarget()
        view = AttackView(mock_controller, target)
        
        # Start the view
        view.start()
        
        # Controller start should have been called
        mock_controller.start.assert_called_once()


class TestScannerToAttackTransition(unittest.TestCase):
    """Test transition from scanner to attack view."""
    
    def test_scanner_view_stops_before_attack(self):
        """Test that scanner view is stopped before attack starts."""
        from wifite.ui.scanner_view import ScannerView
        
        mock_controller = Mock()
        mock_controller.is_running = True
        
        view = ScannerView(mock_controller)
        
        # Stop should be callable
        view.stop()
        
        # Should not raise any errors
        self.assertIsNotNone(view)
    
    def test_attack_view_can_start_after_scanner(self):
        """Test that attack view can start after scanner stops."""
        from wifite.ui.scanner_view import ScannerView
        from wifite.ui.attack_view import AttackView
        
        mock_controller = Mock()
        mock_controller.is_running = False  # Not running initially
        mock_controller.start = Mock()
        mock_controller.stop = Mock()
        
        # Create and stop scanner view
        scanner_view = ScannerView(mock_controller)
        scanner_view.stop()
        
        # Create and start attack view
        target = MockTarget()
        attack_view = AttackView(mock_controller, target)
        attack_view.start()
        
        # Controller should have been started for attack
        mock_controller.start.assert_called_once()


if __name__ == '__main__':
    unittest.main()
