#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test for manufacturer display in selector view.

Verifies that the manufacturer column is shown in target selection
when --showm flag is used.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch


class TestSelectorManufacturerDisplay(unittest.TestCase):
    """Test manufacturer display in selector view."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock target with BSSID
        self.mock_target = Mock()
        self.mock_target.bssid = '00:11:22:33:44:55'
        self.mock_target.essid = 'TestNetwork'
        self.mock_target.essid_known = True
        self.mock_target.channel = 6
        self.mock_target.power = 50
        self.mock_target.encryption = 'WPA2'
        self.mock_target.wps = 0
        self.mock_target.clients = []
    
    @patch('wifite.config.Configuration')
    def test_manufacturer_column_shown_when_enabled(self, mock_config):
        """Test that manufacturer column is shown when show_manufacturers is True."""
        from wifite.ui.selector_view import SelectorView
        
        # Enable manufacturer display
        mock_config.show_manufacturers = True
        mock_config.manufacturers = {'001122': 'Test Manufacturer'}
        
        # Create mock TUI controller
        mock_tui = Mock()
        mock_tui.is_running = False
        mock_tui.get_terminal_size = Mock(return_value=(80, 24))
        
        # Create selector view
        selector = SelectorView(mock_tui, [self.mock_target])
        
        # Render targets table
        table = selector._render_targets_table()
        
        # Verify manufacturer column exists
        column_names = [col.header for col in table.columns]
        self.assertIn('MANUFACTURER', column_names)
    
    @patch('wifite.config.Configuration')
    def test_manufacturer_column_hidden_when_disabled(self, mock_config):
        """Test that manufacturer column is hidden when show_manufacturers is False."""
        from wifite.ui.selector_view import SelectorView
        
        # Disable manufacturer display
        mock_config.show_manufacturers = False
        
        # Create mock TUI controller
        mock_tui = Mock()
        mock_tui.is_running = False
        mock_tui.get_terminal_size = Mock(return_value=(80, 24))
        
        # Create selector view
        selector = SelectorView(mock_tui, [self.mock_target])
        
        # Render targets table
        table = selector._render_targets_table()
        
        # Verify manufacturer column does not exist
        column_names = [col.header for col in table.columns]
        self.assertNotIn('MANUFACTURER', column_names)
    
    @patch('wifite.config.Configuration')
    def test_format_manufacturer_with_known_oui(self, mock_config):
        """Test manufacturer formatting with known OUI."""
        from wifite.ui.selector_view import SelectorView
        
        # Set up manufacturer database
        mock_config.manufacturers = {
            '001122': 'Cisco Systems',
            'AABBCC': 'Apple Inc.'
        }
        
        # Create mock TUI controller
        mock_tui = Mock()
        mock_tui.is_running = False
        mock_tui.get_terminal_size = Mock(return_value=(80, 24))
        
        # Create selector view
        selector = SelectorView(mock_tui, [self.mock_target])
        
        # Format manufacturer
        result = selector._format_manufacturer(self.mock_target)
        
        # Verify result
        self.assertEqual(result.plain, 'Cisco Systems')
    
    @patch('wifite.config.Configuration')
    def test_format_manufacturer_with_unknown_oui(self, mock_config):
        """Test manufacturer formatting with unknown OUI."""
        from wifite.ui.selector_view import SelectorView
        
        # Set up empty manufacturer database
        mock_config.manufacturers = {}
        
        # Create mock TUI controller
        mock_tui = Mock()
        mock_tui.is_running = False
        mock_tui.get_terminal_size = Mock(return_value=(80, 24))
        
        # Create selector view
        selector = SelectorView(mock_tui, [self.mock_target])
        
        # Format manufacturer
        result = selector._format_manufacturer(self.mock_target)
        
        # Verify result shows "Unknown"
        self.assertEqual(result.plain, 'Unknown')
    
    @patch('wifite.config.Configuration')
    def test_format_manufacturer_truncates_long_names(self, mock_config):
        """Test that long manufacturer names are truncated."""
        from wifite.ui.selector_view import SelectorView
        
        # Set up manufacturer with very long name
        long_name = 'A' * 50  # 50 characters
        mock_config.manufacturers = {'001122': long_name}
        
        # Create mock TUI controller
        mock_tui = Mock()
        mock_tui.is_running = False
        mock_tui.get_terminal_size = Mock(return_value=(80, 24))
        
        # Create selector view
        selector = SelectorView(mock_tui, [self.mock_target])
        
        # Format manufacturer
        result = selector._format_manufacturer(self.mock_target)
        
        # Verify result is truncated to 20 characters
        self.assertLessEqual(len(result.plain), 20)
        self.assertTrue(result.plain.endswith('...'))
    
    def test_format_clients_with_clients(self):
        """Test client count formatting when clients are present."""
        from wifite.ui.selector_view import SelectorView
        
        # Add clients to target
        self.mock_target.clients = [Mock(), Mock(), Mock()]
        
        # Create mock TUI controller
        mock_tui = Mock()
        mock_tui.is_running = False
        mock_tui.get_terminal_size = Mock(return_value=(80, 24))
        
        # Create selector view
        selector = SelectorView(mock_tui, [self.mock_target])
        
        # Format clients
        result = selector._format_clients(self.mock_target)
        
        # Verify result
        self.assertEqual(result.plain, '3')
    
    def test_format_clients_without_clients(self):
        """Test client count formatting when no clients are present."""
        from wifite.ui.selector_view import SelectorView
        
        # No clients
        self.mock_target.clients = []
        
        # Create mock TUI controller
        mock_tui = Mock()
        mock_tui.is_running = False
        mock_tui.get_terminal_size = Mock(return_value=(80, 24))
        
        # Create selector view
        selector = SelectorView(mock_tui, [self.mock_target])
        
        # Format clients
        result = selector._format_clients(self.mock_target)
        
        # Verify result
        self.assertEqual(result.plain, '0')


if __name__ == '__main__':
    unittest.main()
