#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integration tests for wifite2 TUI views.
Tests complete view workflows with mock data and interactions.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import time


class MockTarget:
    """Mock Target object for testing."""
    
    def __init__(self, essid="TestNetwork", bssid="AA:BB:CC:DD:EE:FF", 
                 channel=6, power=-50, encryption="WPA2", wps=0, clients=None, is_wpa3=False):
        self.essid = essid
        self.essid_known = True
        self.bssid = bssid
        self.channel = channel
        self.power = power
        self.encryption = encryption
        self.wps = wps
        self.clients = clients or []
        self.decloaked = False
        self.is_wpa3 = is_wpa3


class MockTUIController:
    """Mock TUI controller for testing views."""
    
    def __init__(self):
        self.is_running = True
        self.updates = []
        self.force_updates = []
    
    def start(self):
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
    def update(self, layout):
        self.updates.append(layout)
    
    def force_update(self, layout):
        self.force_updates.append(layout)


class TestScannerViewIntegration(unittest.TestCase):
    """Integration tests for ScannerView."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_tui = MockTUIController()
    
    def test_scanner_view_initialization(self):
        """Test scanner view initializes correctly."""
        from wifite.ui.scanner_view import ScannerView
        
        view = ScannerView(self.mock_tui)
        
        self.assertIsNotNone(view)
        self.assertEqual(view.tui, self.mock_tui)
        self.assertEqual(len(view.targets), 0)
        self.assertFalse(view.decloaking)
    
    def test_scanner_view_with_empty_targets(self):
        """Test scanner view with no targets."""
        from wifite.ui.scanner_view import ScannerView
        
        view = ScannerView(self.mock_tui)
        view.update_targets([])
        
        # Should have rendered once
        self.assertGreater(len(self.mock_tui.updates), 0)
        self.assertEqual(len(view.targets), 0)
    
    def test_scanner_view_with_single_target(self):
        """Test scanner view with one target."""
        from wifite.ui.scanner_view import ScannerView
        
        target = MockTarget()
        view = ScannerView(self.mock_tui)
        view.update_targets([target])
        
        self.assertEqual(len(view.targets), 1)
        self.assertGreater(len(self.mock_tui.updates), 0)
    
    def test_scanner_view_with_multiple_targets(self):
        """Test scanner view with multiple targets."""
        from wifite.ui.scanner_view import ScannerView
        
        targets = [
            MockTarget(essid="Network1", encryption="WEP"),
            MockTarget(essid="Network2", encryption="WPA"),
            MockTarget(essid="Network3", encryption="WPA2", wps=1),
        ]
        
        view = ScannerView(self.mock_tui)
        view.update_targets(targets)
        
        self.assertEqual(len(view.targets), 3)
        self.assertGreater(len(self.mock_tui.updates), 0)
    
    def test_scanner_view_updates_targets(self):
        """Test scanner view updates when targets change."""
        from wifite.ui.scanner_view import ScannerView
        
        view = ScannerView(self.mock_tui)
        
        # First update
        targets1 = [MockTarget(essid="Network1")]
        view.update_targets(targets1)
        update_count_1 = len(self.mock_tui.updates)
        
        # Second update with more targets
        targets2 = [
            MockTarget(essid="Network1"),
            MockTarget(essid="Network2"),
        ]
        view.update_targets(targets2)
        update_count_2 = len(self.mock_tui.updates)
        
        # Should have rendered twice
        self.assertGreater(update_count_2, update_count_1)
        self.assertEqual(len(view.targets), 2)
    
    def test_scanner_view_with_clients(self):
        """Test scanner view displays targets with clients."""
        from wifite.ui.scanner_view import ScannerView
        
        mock_client = Mock()
        mock_client.bssid = "11:22:33:44:55:66"
        
        target = MockTarget(clients=[mock_client])
        view = ScannerView(self.mock_tui)
        view.update_targets([target])
        
        self.assertEqual(len(view.targets[0].clients), 1)
    
    def test_scanner_view_decloaking_mode(self):
        """Test scanner view in decloaking mode."""
        from wifite.ui.scanner_view import ScannerView
        
        view = ScannerView(self.mock_tui)
        view.update_targets([], decloaking=True)
        
        self.assertTrue(view.decloaking)
    
    def test_scanner_view_stop(self):
        """Test scanner view cleanup on stop."""
        from wifite.ui.scanner_view import ScannerView
        
        view = ScannerView(self.mock_tui)
        view.stop()
        
        # Should not raise any errors
        self.assertIsNotNone(view)


class TestSelectorViewIntegration(unittest.TestCase):
    """Integration tests for SelectorView."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_tui = MockTUIController()
        self.targets = [
            MockTarget(essid="Network1", encryption="WEP"),
            MockTarget(essid="Network2", encryption="WPA"),
            MockTarget(essid="Network3", encryption="WPA2"),
        ]
    
    def test_selector_view_initialization(self):
        """Test selector view initializes correctly."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        
        self.assertIsNotNone(view)
        self.assertEqual(len(view.targets), 3)
        self.assertEqual(view.cursor, 0)
        self.assertEqual(len(view.selected), 0)
    
    def test_selector_view_cursor_navigation_down(self):
        """Test cursor navigation down."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        
        # Move cursor down
        view.handle_input('\x1b[B')  # Down arrow
        self.assertEqual(view.cursor, 1)
        
        view.handle_input('\x1b[B')  # Down arrow
        self.assertEqual(view.cursor, 2)
    
    def test_selector_view_cursor_navigation_up(self):
        """Test cursor navigation up."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        view.cursor = 2
        
        # Move cursor up
        view.handle_input('\x1b[A')  # Up arrow
        self.assertEqual(view.cursor, 1)
        
        view.handle_input('\x1b[A')  # Up arrow
        self.assertEqual(view.cursor, 0)
    
    def test_selector_view_cursor_bounds(self):
        """Test cursor stays within bounds."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        
        # Try to move up from top
        view.handle_input('\x1b[A')  # Up arrow
        self.assertEqual(view.cursor, 0)
        
        # Move to bottom
        view.cursor = 2
        
        # Try to move down from bottom
        view.handle_input('\x1b[B')  # Down arrow
        self.assertEqual(view.cursor, 2)
    
    def test_selector_view_toggle_selection(self):
        """Test toggling target selection."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        
        # Select first target
        view.handle_input(' ')  # Space
        self.assertIn(0, view.selected)
        
        # Deselect first target
        view.handle_input(' ')  # Space
        self.assertNotIn(0, view.selected)
    
    def test_selector_view_select_all(self):
        """Test select all functionality."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        
        # Select all
        view.handle_input('a')
        self.assertEqual(len(view.selected), 3)
        self.assertIn(0, view.selected)
        self.assertIn(1, view.selected)
        self.assertIn(2, view.selected)
    
    def test_selector_view_select_none(self):
        """Test select none functionality."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        
        # Select all first
        view.handle_input('a')
        self.assertEqual(len(view.selected), 3)
        
        # Deselect all
        view.handle_input('n')
        self.assertEqual(len(view.selected), 0)
    
    def test_selector_view_confirm_action(self):
        """Test confirm action returns correct value."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        
        # Select some targets
        view.handle_input(' ')  # Select first
        view.handle_input('\x1b[B')  # Move down
        view.handle_input(' ')  # Select second
        
        # Confirm
        action = view.handle_input('\r')  # Enter
        self.assertEqual(action, 'confirm')
    
    def test_selector_view_quit_action(self):
        """Test quit action returns correct value."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        
        action = view.handle_input('q')
        self.assertEqual(action, 'quit')
    
    def test_selector_view_get_selected_targets(self):
        """Test getting selected targets."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        
        # Select first and third targets
        view.cursor = 0
        view.handle_input(' ')  # Select
        view.cursor = 2
        view.handle_input(' ')  # Select
        
        selected = view.get_selected_targets()
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0].essid, "Network1")
        self.assertEqual(selected[1].essid, "Network3")
    
    def test_selector_view_page_navigation(self):
        """Test page up/down navigation."""
        from wifite.ui.selector_view import SelectorView
        
        # Create many targets
        many_targets = [MockTarget(essid=f"Network{i}") for i in range(20)]
        view = SelectorView(self.mock_tui, many_targets)
        
        # Page down
        view.handle_input('\x1b[6~')  # Page Down
        self.assertGreater(view.cursor, 0)
        
        # Page up
        view.handle_input('\x1b[5~')  # Page Up
        self.assertLess(view.cursor, 10)
    
    def test_selector_view_home_end_keys(self):
        """Test home and end key navigation."""
        from wifite.ui.selector_view import SelectorView
        
        view = SelectorView(self.mock_tui, self.targets)
        view.cursor = 1
        
        # End key
        view.handle_input('\x1b[F')  # End
        self.assertEqual(view.cursor, 2)
        
        # Home key
        view.handle_input('\x1b[H')  # Home
        self.assertEqual(view.cursor, 0)


class TestAttackViewIntegration(unittest.TestCase):
    """Integration tests for AttackView."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_tui = MockTUIController()
        self.target = MockTarget()
    
    def test_attack_view_initialization(self):
        """Test attack view initializes correctly."""
        from wifite.ui.attack_view import AttackView
        
        view = AttackView(self.mock_tui, self.target)
        
        self.assertIsNotNone(view)
        self.assertEqual(view.target, self.target)
        self.assertEqual(view.progress_percent, 0.0)
        self.assertEqual(view.status_message, "Initializing...")
    
    def test_attack_view_set_attack_type(self):
        """Test setting attack type."""
        from wifite.ui.attack_view import AttackView
        
        view = AttackView(self.mock_tui, self.target)
        view.set_attack_type("WPA Handshake Capture")
        
        self.assertEqual(view.attack_type, "WPA Handshake Capture")
    
    def test_attack_view_update_progress(self):
        """Test updating attack progress."""
        from wifite.ui.attack_view import AttackView
        
        view = AttackView(self.mock_tui, self.target)
        
        view.update_progress({
            'progress': 0.5,
            'status': 'Capturing handshake',
            'metrics': {'clients': 2}
        })
        
        self.assertEqual(view.progress_percent, 0.5)
        self.assertEqual(view.status_message, 'Capturing handshake')
        self.assertEqual(view.metrics['clients'], 2)
    
    def test_attack_view_add_log(self):
        """Test adding log entries."""
        from wifite.ui.attack_view import AttackView
        
        view = AttackView(self.mock_tui, self.target)
        
        view.add_log("Test log message")
        self.assertEqual(len(view.log_panel.logs), 1)
        self.assertIn("Test log message", view.log_panel.logs[0])
    
    def test_attack_view_clear_logs(self):
        """Test clearing log entries."""
        from wifite.ui.attack_view import AttackView
        
        view = AttackView(self.mock_tui, self.target)
        
        view.add_log("Message 1")
        view.add_log("Message 2")
        self.assertEqual(len(view.log_panel.logs), 2)
        
        view.clear_logs()
        self.assertEqual(len(view.log_panel.logs), 0)
    
    def test_wep_attack_view_ivs_update(self):
        """Test WEP attack view IVs update."""
        from wifite.ui.attack_view import WEPAttackView
        
        view = WEPAttackView(self.mock_tui, self.target)
        
        view.update_ivs(5000, 10000)
        
        self.assertEqual(view.ivs_collected, 5000)
        self.assertEqual(view.ivs_needed, 10000)
        self.assertEqual(view.progress_percent, 0.5)
    
    def test_wep_attack_view_crack_attempt(self):
        """Test WEP attack view crack attempt."""
        from wifite.ui.attack_view import WEPAttackView
        
        view = WEPAttackView(self.mock_tui, self.target)
        
        view.update_crack_attempt(1, success=False)
        self.assertEqual(view.crack_attempts, 1)
        
        view.update_crack_attempt(2, success=True)
        self.assertEqual(view.crack_attempts, 2)
        self.assertEqual(view.progress_percent, 1.0)
    
    def test_wep_attack_view_replay_status(self):
        """Test WEP attack view replay status."""
        from wifite.ui.attack_view import WEPAttackView
        
        view = WEPAttackView(self.mock_tui, self.target)
        
        view.set_replay_active(True)
        self.assertTrue(view.replay_active)
        
        view.set_replay_active(False)
        self.assertFalse(view.replay_active)
    
    def test_wpa_attack_view_handshake_status(self):
        """Test WPA attack view handshake status."""
        from wifite.ui.attack_view import WPAAttackView
        
        view = WPAAttackView(self.mock_tui, self.target)
        
        view.update_handshake_status(False, clients=2, deauths_sent=5)
        self.assertFalse(view.has_handshake)
        self.assertEqual(view.clients, 2)
        self.assertEqual(view.deauths_sent, 5)
        
        view.update_handshake_status(True)
        self.assertTrue(view.has_handshake)
        self.assertEqual(view.progress_percent, 1.0)
    
    def test_wpa_attack_view_increment_deauths(self):
        """Test WPA attack view deauth increment."""
        from wifite.ui.attack_view import WPAAttackView
        
        view = WPAAttackView(self.mock_tui, self.target)
        
        view.increment_deauths(5)
        self.assertEqual(view.deauths_sent, 5)
        
        view.increment_deauths()
        self.assertEqual(view.deauths_sent, 6)
    
    def test_wps_attack_view_pin_attempts(self):
        """Test WPS attack view PIN attempts."""
        from wifite.ui.attack_view import WPSAttackView
        
        view = WPSAttackView(self.mock_tui, self.target)
        
        view.update_pin_attempts(1000, 11000, "12345670")
        self.assertEqual(view.pins_tried, 1000)
        self.assertEqual(view.total_pins, 11000)
        self.assertEqual(view.current_pin, "12345670")
    
    def test_wps_attack_view_pixie_dust_mode(self):
        """Test WPS attack view pixie dust mode."""
        from wifite.ui.attack_view import WPSAttackView
        
        view = WPSAttackView(self.mock_tui, self.target)
        
        view.set_pixie_dust_mode(True)
        self.assertTrue(view.pixie_dust_mode)
        self.assertEqual(view.attack_type, "WPS Pixie Dust Attack")
        
        view.set_pixie_dust_mode(False)
        self.assertFalse(view.pixie_dust_mode)
        self.assertEqual(view.attack_type, "WPS PIN Attack")
    
    def test_wps_attack_view_locked_out(self):
        """Test WPS attack view locked out status."""
        from wifite.ui.attack_view import WPSAttackView
        
        view = WPSAttackView(self.mock_tui, self.target)
        
        view.set_locked_out(True)
        self.assertTrue(view.locked_out)
        self.assertEqual(view.progress_percent, 0.0)
    
    def test_pmkid_attack_view_capture_status(self):
        """Test PMKID attack view capture status."""
        from wifite.ui.attack_view import PMKIDAttackView
        
        view = PMKIDAttackView(self.mock_tui, self.target)
        
        view.update_pmkid_status(False, attempts=3)
        self.assertFalse(view.has_pmkid)
        self.assertEqual(view.attempts, 3)
        
        view.update_pmkid_status(True)
        self.assertTrue(view.has_pmkid)
        self.assertEqual(view.progress_percent, 1.0)
    
    def test_pmkid_attack_view_increment_attempts(self):
        """Test PMKID attack view attempt increment."""
        from wifite.ui.attack_view import PMKIDAttackView
        
        view = PMKIDAttackView(self.mock_tui, self.target)
        
        view.increment_attempts()
        self.assertEqual(view.attempts, 1)
        
        view.increment_attempts()
        self.assertEqual(view.attempts, 2)


class TestOutputManagerIntegration(unittest.TestCase):
    """Integration tests for OutputManager."""
    
    def test_output_manager_classic_mode(self):
        """Test OutputManager in classic mode."""
        from wifite.util.output import OutputManager
        
        # Force classic mode
        OutputManager._mode = None
        OutputManager._controller = None
        OutputManager.initialize('classic')
        
        self.assertEqual(OutputManager.get_mode(), 'classic')
        self.assertFalse(OutputManager.is_tui_mode())
        self.assertIsNone(OutputManager.get_controller())
    
    def test_output_manager_terminal_check(self):
        """Test OutputManager terminal capability check."""
        from wifite.util.output import check_terminal_support
        
        # This will vary based on test environment
        result = check_terminal_support()
        self.assertIsInstance(result, bool)
    
    def test_output_manager_get_scanner_view(self):
        """Test OutputManager returns scanner view."""
        from wifite.util.output import OutputManager
        
        # Force classic mode for predictable testing
        OutputManager._mode = 'classic'
        OutputManager._controller = None
        
        view = OutputManager.get_scanner_view()
        self.assertIsNotNone(view)
    
    def test_output_manager_get_selector_view(self):
        """Test OutputManager returns selector view."""
        from wifite.util.output import OutputManager
        
        # Force classic mode for predictable testing
        OutputManager._mode = 'classic'
        OutputManager._controller = None
        
        targets = [MockTarget()]
        view = OutputManager.get_selector_view(targets)
        self.assertIsNotNone(view)
    
    def test_output_manager_get_attack_view(self):
        """Test OutputManager returns attack view."""
        from wifite.util.output import OutputManager
        
        # Force classic mode for predictable testing
        OutputManager._mode = 'classic'
        OutputManager._controller = None
        
        target = MockTarget()
        view = OutputManager.get_attack_view(target)
        self.assertIsNotNone(view)
    
    def test_output_manager_cleanup(self):
        """Test OutputManager cleanup."""
        from wifite.util.output import OutputManager
        
        OutputManager._mode = 'classic'
        OutputManager._controller = None
        
        # Should not raise any errors
        OutputManager.cleanup()
        
        self.assertIsNone(OutputManager._mode)
        self.assertIsNone(OutputManager._controller)


if __name__ == '__main__':
    unittest.main()
