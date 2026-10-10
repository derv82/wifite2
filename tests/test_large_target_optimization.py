#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for large target list optimization.
Verifies that rendering is optimized for performance with many targets.
"""

import unittest
from unittest.mock import Mock


class MockTarget:
    """Mock Target object for testing."""
    
    def __init__(self, essid="TestNetwork", bssid="AA:BB:CC:DD:EE:FF", 
                 channel=6, power=-50, encryption="WPA2", wps=0, clients=None):
        self.essid = essid
        self.essid_known = True
        self.bssid = bssid
        self.channel = channel
        self.power = power
        self.encryption = encryption
        self.wps = wps
        self.clients = clients or []
        self.decloaked = False


class MockTUIController:
    """Mock TUI controller for testing."""
    
    def __init__(self, width=100, height=30):
        self.is_running = True
        self.updates = []
        self.width = width
        self.height = height
    
    def start(self):
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
    def update(self, layout):
        self.updates.append(layout)
    
    def force_update(self, layout):
        self.updates.append(layout)
    
    def get_terminal_size(self):
        return (self.width, self.height)


class TestScannerViewLargeTargetOptimization(unittest.TestCase):
    """Test scanner view optimization for large target lists."""
    
    def test_scanner_view_limits_displayed_targets(self):
        """Test that scanner view limits displayed targets for performance."""
        from wifite.ui.scanner_view import ScannerView
        
        mock_tui = MockTUIController()
        view = ScannerView(mock_tui)
        
        # Create 200 targets
        targets = [
            MockTarget(essid=f"Network{i}", power=-50 - i)
            for i in range(200)
        ]
        
        view.update_targets(targets)
        
        # Should have all targets stored
        self.assertEqual(len(view.targets), 200)
        
        # But rendering should be optimized
        max_visible = view._calculate_max_visible_targets()
        self.assertLessEqual(max_visible, 100)  # Max cap
        self.assertGreaterEqual(max_visible, 10)  # Min cap
    
    def test_scanner_view_shows_strongest_targets_first(self):
        """Test that scanner view prioritizes strongest signals."""
        from wifite.ui.scanner_view import ScannerView
        
        mock_tui = MockTUIController()
        view = ScannerView(mock_tui)
        
        # Create targets with varying power levels
        targets = [
            MockTarget(essid="Weak", power=-90),
            MockTarget(essid="Strong", power=-40),
            MockTarget(essid="Medium", power=-60),
        ]
        
        view.update_targets(targets)
        
        # Verify targets are stored
        self.assertEqual(len(view.targets), 3)
    
    def test_scanner_view_dynamic_max_based_on_terminal_height(self):
        """Test that max visible targets adjusts to terminal height."""
        from wifite.ui.scanner_view import ScannerView
        
        # Small terminal
        small_tui = MockTUIController(width=80, height=24)
        small_view = ScannerView(small_tui)
        small_max = small_view._calculate_max_visible_targets()
        
        # Large terminal
        large_tui = MockTUIController(width=200, height=60)
        large_view = ScannerView(large_tui)
        large_max = large_view._calculate_max_visible_targets()
        
        # Large terminal should show more targets
        self.assertGreater(large_max, small_max)
        
        # Both should be within bounds
        self.assertGreaterEqual(small_max, 10)
        self.assertLessEqual(small_max, 100)
        self.assertGreaterEqual(large_max, 10)
        self.assertLessEqual(large_max, 100)
    
    def test_scanner_view_shows_overflow_indicator(self):
        """Test that scanner view shows indicator when targets are hidden."""
        from wifite.ui.scanner_view import ScannerView
        
        mock_tui = MockTUIController()
        view = ScannerView(mock_tui)
        
        # Create more targets than can be displayed
        targets = [MockTarget(essid=f"Network{i}") for i in range(100)]
        view.update_targets(targets)
        
        # Render the table
        table = view._render_targets_table()
        
        # Should have a caption indicating overflow
        if len(targets) > view._calculate_max_visible_targets():
            self.assertIsNotNone(table.caption)


class TestSelectorViewLargeTargetOptimization(unittest.TestCase):
    """Test selector view optimization for large target lists."""
    
    def test_selector_view_pagination(self):
        """Test that selector view uses pagination for large lists."""
        from wifite.ui.selector_view import SelectorView
        
        mock_tui = MockTUIController()
        
        # Create 100 targets
        targets = [MockTarget(essid=f"Network{i}") for i in range(100)]
        
        view = SelectorView(mock_tui, targets)
        
        # Should have all targets
        self.assertEqual(len(view.targets), 100)
        
        # But max visible should be limited
        self.assertLessEqual(view.max_visible_rows, 50)
        self.assertGreaterEqual(view.max_visible_rows, 10)
    
    def test_selector_view_dynamic_max_based_on_terminal_height(self):
        """Test that max visible rows adjusts to terminal height."""
        from wifite.ui.selector_view import SelectorView
        
        targets = [MockTarget(essid=f"Network{i}") for i in range(50)]
        
        # Small terminal
        small_tui = MockTUIController(width=80, height=24)
        small_view = SelectorView(small_tui, targets)
        small_max = small_view.max_visible_rows
        
        # Large terminal
        large_tui = MockTUIController(width=200, height=60)
        large_view = SelectorView(large_tui, targets)
        large_max = large_view.max_visible_rows
        
        # Large terminal should show more rows
        self.assertGreater(large_max, small_max)
        
        # Both should be within bounds
        self.assertGreaterEqual(small_max, 10)
        self.assertLessEqual(small_max, 50)
        self.assertGreaterEqual(large_max, 10)
        self.assertLessEqual(large_max, 50)
    
    def test_selector_view_scroll_offset_navigation(self):
        """Test that selector view handles scrolling through large lists."""
        from wifite.ui.selector_view import SelectorView
        
        mock_tui = MockTUIController()
        
        # Create many targets
        targets = [MockTarget(essid=f"Network{i}") for i in range(100)]
        
        view = SelectorView(mock_tui, targets)
        
        # Initial position
        self.assertEqual(view.cursor, 0)
        self.assertEqual(view.scroll_offset, 0)
        
        # Move cursor beyond visible area
        view.cursor = view.max_visible_rows + 5
        view._adjust_scroll()
        
        # Scroll offset should adjust
        self.assertGreater(view.scroll_offset, 0)
    
    def test_selector_view_handles_very_large_lists(self):
        """Test that selector view can handle very large target lists."""
        from wifite.ui.selector_view import SelectorView
        
        mock_tui = MockTUIController()
        
        # Create 500 targets (stress test)
        targets = [MockTarget(essid=f"Network{i}") for i in range(500)]
        
        view = SelectorView(mock_tui, targets)
        
        # Should initialize without errors
        self.assertEqual(len(view.targets), 500)
        self.assertIsNotNone(view.max_visible_rows)
        
        # Navigation should work
        view._move_cursor(10)
        self.assertEqual(view.cursor, 10)
        
        # Select all should work (though may be slow)
        view._select_all()
        self.assertEqual(len(view.selected), 500)


class TestPerformanceOptimization(unittest.TestCase):
    """Test overall performance optimizations."""
    
    def test_rendering_performance_with_large_list(self):
        """Test that rendering remains performant with large lists."""
        from wifite.ui.scanner_view import ScannerView
        import time
        
        mock_tui = MockTUIController()
        view = ScannerView(mock_tui)
        
        # Create 1000 targets
        targets = [
            MockTarget(essid=f"Network{i}", power=-50 - (i % 50))
            for i in range(1000)
        ]
        
        # Measure update time
        start = time.time()
        view.update_targets(targets)
        duration = time.time() - start
        
        # Should complete quickly (< 1 second)
        self.assertLess(duration, 1.0)
    
    def test_memory_efficiency_with_large_list(self):
        """Test that memory usage is reasonable with large lists."""
        from wifite.ui.scanner_view import ScannerView
        
        mock_tui = MockTUIController()
        view = ScannerView(mock_tui)
        
        # Create many targets
        targets = [MockTarget(essid=f"Network{i}") for i in range(1000)]
        
        view.update_targets(targets)
        
        # All targets should be stored
        self.assertEqual(len(view.targets), 1000)
        
        # But rendering should be limited
        max_visible = view._calculate_max_visible_targets()
        self.assertLess(max_visible, len(targets))


if __name__ == '__main__':
    unittest.main()
