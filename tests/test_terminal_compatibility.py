#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Terminal compatibility tests for wifite2 TUI.
Tests various terminal configurations and edge cases.
"""

import unittest
import os
from unittest.mock import Mock, patch, MagicMock


class TestTerminalSizeHandling(unittest.TestCase):
    """Test terminal size detection and handling."""
    
    def test_minimum_terminal_size_check(self):
        """Test that minimum terminal size is enforced."""
        from wifite.ui.tui import TUIController
        
        controller = TUIController()
        
        # Mock console with small size
        controller.console = Mock()
        controller.console.width = 60
        controller.console.height = 20
        
        # Should fail minimum size check
        self.assertFalse(controller.check_terminal_size())
    
    def test_adequate_terminal_size_check(self):
        """Test that adequate terminal size passes."""
        from wifite.ui.tui import TUIController
        
        controller = TUIController()
        
        # Mock console with adequate size
        controller.console = Mock()
        controller.console.width = 80
        controller.console.height = 24
        
        # Should pass minimum size check
        self.assertTrue(controller.check_terminal_size())
    
    def test_large_terminal_size_check(self):
        """Test that large terminal size passes."""
        from wifite.ui.tui import TUIController
        
        controller = TUIController()
        
        # Mock console with large size
        controller.console = Mock()
        controller.console.width = 200
        controller.console.height = 50
        
        # Should pass minimum size check
        self.assertTrue(controller.check_terminal_size())
    
    def test_get_terminal_size(self):
        """Test getting terminal size."""
        from wifite.ui.tui import TUIController
        
        controller = TUIController()
        
        # Mock console
        controller.console = Mock()
        controller.console.width = 100
        controller.console.height = 30
        
        size = controller.get_terminal_size()
        self.assertEqual(size, (100, 30))


class TestTerminalCapabilityDetection(unittest.TestCase):
    """Test terminal capability detection."""
    
    @patch('sys.stdout')
    def test_non_tty_detection(self, mock_stdout):
        """Test detection of non-TTY output (piped/redirected)."""
        from wifite.util.output import OutputManager
        
        # Mock non-TTY stdout
        mock_stdout.isatty.return_value = False
        
        # Should detect as not supporting TUI
        result = OutputManager._check_terminal_support()
        self.assertFalse(result)
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('sys.stdout')
    def test_no_term_env_detection(self, mock_stdout):
        """Test detection when TERM environment variable is not set."""
        from wifite.util.output import OutputManager
        
        # Mock TTY stdout
        mock_stdout.isatty.return_value = True
        
        # Should detect as not supporting TUI (no TERM)
        result = OutputManager._check_terminal_support()
        self.assertFalse(result)
    
    @patch.dict(os.environ, {'TERM': 'dumb'})
    @patch('sys.stdout')
    def test_dumb_terminal_detection(self, mock_stdout):
        """Test detection of dumb terminal."""
        from wifite.util.output import OutputManager
        
        # Mock TTY stdout
        mock_stdout.isatty.return_value = True
        
        # Should detect as not supporting TUI (dumb terminal)
        result = OutputManager._check_terminal_support()
        self.assertFalse(result)
    
    @patch.dict(os.environ, {'TERM': 'xterm-256color'})
    @patch('sys.stdout')
    def test_capable_terminal_detection(self, mock_stdout):
        """Test detection of capable terminal."""
        from wifite.util.output import OutputManager
        
        # Mock TTY stdout
        mock_stdout.isatty.return_value = True
        
        # This will try to import rich and check terminal
        # Result depends on actual environment
        result = OutputManager._check_terminal_support()
        self.assertIsInstance(result, bool)


class TestColorSupport(unittest.TestCase):
    """Test color support detection and handling."""
    
    def test_signal_strength_colors(self):
        """Test signal strength bar uses appropriate colors."""
        from wifite.ui.components import SignalStrengthBar
        
        # Strong signal - green
        strong = SignalStrengthBar.render(-45)
        self.assertEqual(strong.style, "green")
        
        # Medium signal - yellow
        medium = SignalStrengthBar.render(-60)
        self.assertEqual(medium.style, "yellow")
        
        # Weak signal - red
        weak = SignalStrengthBar.render(-85)
        self.assertEqual(weak.style, "red")
    
    def test_encryption_badge_colors(self):
        """Test encryption badges use appropriate colors."""
        from wifite.ui.components import EncryptionBadge
        
        # WEP - red (insecure)
        wep = EncryptionBadge.render("WEP")
        self.assertEqual(wep.style, "red")
        
        # WPA/WPA2 - yellow (moderate)
        wpa = EncryptionBadge.render("WPA2")
        self.assertEqual(wpa.style, "yellow")
        
        # WPA3 - green (secure)
        wpa3 = EncryptionBadge.render("WPA3")
        self.assertEqual(wpa3.style, "green")


class TestUpdateThrottling(unittest.TestCase):
    """Test update throttling for performance."""
    
    def test_update_throttling_prevents_rapid_updates(self):
        """Test that update throttling prevents excessive updates."""
        from wifite.ui.tui import TUIController
        import time
        
        controller = TUIController()
        controller.min_update_interval = 0.1  # 100ms
        
        # First update should be allowed
        self.assertTrue(controller.should_update())
        
        # Immediate second update should be throttled
        self.assertFalse(controller.should_update())
        
        # After waiting, update should be allowed
        time.sleep(0.11)
        self.assertTrue(controller.should_update())
    
    def test_force_update_bypasses_throttling(self):
        """Test that force_update bypasses throttling."""
        from wifite.ui.tui import TUIController
        from rich.text import Text
        
        controller = TUIController()
        controller.is_running = True
        controller.live = Mock()
        
        # Force update should work even without throttle check
        test_content = Text("Test")
        controller.force_update(test_content)
        
        # Verify update was called
        controller.live.update.assert_called_once()


class TestErrorHandling(unittest.TestCase):
    """Test error handling and graceful degradation."""
    
    def test_tui_start_failure_cleanup(self):
        """Test that TUI cleans up properly on start failure."""
        from wifite.ui.tui import TUIController
        
        controller = TUIController()
        
        # Mock console with too-small size
        controller.console = Mock()
        controller.console.width = 50
        controller.console.height = 15
        
        # Should raise RuntimeError and not leave TUI running
        with self.assertRaises(RuntimeError):
            controller.start()
        
        self.assertFalse(controller.is_running)
    
    def test_output_manager_fallback_to_classic(self):
        """Test that OutputManager falls back to classic mode on TUI failure."""
        from wifite.util.output import OutputManager
        
        # Reset state
        OutputManager._mode = None
        OutputManager._controller = None
        
        # Force classic mode
        OutputManager.initialize('classic')
        
        # Should be in classic mode
        self.assertEqual(OutputManager.get_mode(), 'classic')
        self.assertFalse(OutputManager.is_tui_mode())
    
    def test_update_failure_graceful_handling(self):
        """Test that update failures are handled gracefully."""
        from wifite.ui.tui import TUIController
        from rich.text import Text
        
        controller = TUIController()
        controller.is_running = True
        controller.live = Mock()
        
        # Make update raise an exception
        controller.live.update.side_effect = Exception("Update failed")
        controller.live.refresh.side_effect = Exception("Refresh failed")
        
        # Should not raise exception
        test_content = Text("Test")
        controller.update(test_content)
        
        # Controller should stop after complete failure
        self.assertFalse(controller.is_running)


class TestContextManager(unittest.TestCase):
    """Test context manager functionality."""
    
    def test_context_manager_cleanup_on_exception(self):
        """Test that context manager cleans up even on exception."""
        from wifite.ui.tui import TUIController
        
        controller = TUIController()
        
        # Mock to avoid actual TUI start
        controller.start = Mock()
        controller.stop = Mock()
        
        try:
            with controller:
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Stop should have been called
        controller.stop.assert_called_once()
    
    def test_context_manager_normal_exit(self):
        """Test that context manager cleans up on normal exit."""
        from wifite.ui.tui import TUIController
        
        controller = TUIController()
        
        # Mock to avoid actual TUI start
        controller.start = Mock()
        controller.stop = Mock()
        
        with controller:
            pass
        
        # Both start and stop should have been called
        controller.start.assert_called_once()
        controller.stop.assert_called_once()


class TestResizeHandling(unittest.TestCase):
    """Test terminal resize handling."""
    
    def test_resize_detection(self):
        """Test that resize is detected when size changes."""
        from wifite.ui.tui import TUIController
        
        controller = TUIController()
        controller.is_running = True
        controller.live = Mock()
        controller.console = Mock()
        
        # Set initial size
        controller.last_size = (80, 24)
        controller.console.width = 100
        controller.console.height = 30
        
        # Handle resize
        controller.handle_resize()
        
        # Size should be updated
        self.assertEqual(controller.last_size, (100, 30))
    
    def test_resize_no_change_ignored(self):
        """Test that resize with no size change is ignored."""
        from wifite.ui.tui import TUIController
        
        controller = TUIController()
        controller.is_running = True
        controller.live = Mock()
        controller.console = Mock()
        
        # Set size that matches current
        controller.last_size = (80, 24)
        controller.console.width = 80
        controller.console.height = 24
        
        # Handle resize
        controller.handle_resize()
        
        # Refresh should not be called (no change)
        controller.live.refresh.assert_not_called()


if __name__ == '__main__':
    unittest.main()
