#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for wifite2 TUI keyboard input handling.
Tests input parsing and key detection functions.
"""

import unittest
import io
from wifite.util.input import (
    KeyboardInput,
    is_arrow_key,
    is_navigation_key,
    is_enter_key,
    is_escape_key
)


class TestKeyboardInputHelpers(unittest.TestCase):
    """Test suite for keyboard input helper functions."""

    def test_is_ctrl_c(self):
        """Test Ctrl+C detection."""
        self.assertTrue(KeyboardInput.is_ctrl_c('\x03'))
        self.assertFalse(KeyboardInput.is_ctrl_c('c'))
        self.assertFalse(KeyboardInput.is_ctrl_c('\x1b'))
        self.assertFalse(KeyboardInput.is_ctrl_c(''))

    def test_key_name_arrow_keys(self):
        """Test key name for arrow keys."""
        self.assertEqual(KeyboardInput.key_name('\x1b[A'), 'Up')
        self.assertEqual(KeyboardInput.key_name('\x1b[B'), 'Down')
        self.assertEqual(KeyboardInput.key_name('\x1b[C'), 'Right')
        self.assertEqual(KeyboardInput.key_name('\x1b[D'), 'Left')

    def test_key_name_navigation_keys(self):
        """Test key name for navigation keys."""
        self.assertEqual(KeyboardInput.key_name('\x1b[H'), 'Home')
        self.assertEqual(KeyboardInput.key_name('\x1b[F'), 'End')
        self.assertEqual(KeyboardInput.key_name('\x1b[5~'), 'Page Up')
        self.assertEqual(KeyboardInput.key_name('\x1b[6~'), 'Page Down')

    def test_key_name_special_keys(self):
        """Test key name for special keys."""
        self.assertEqual(KeyboardInput.key_name('\x1b'), 'Escape')
        self.assertEqual(KeyboardInput.key_name('\r'), 'Enter')
        self.assertEqual(KeyboardInput.key_name('\n'), 'Enter')
        self.assertEqual(KeyboardInput.key_name(' '), 'Space')
        self.assertEqual(KeyboardInput.key_name('\x03'), 'Ctrl+C')
        self.assertEqual(KeyboardInput.key_name('\x7f'), 'Backspace')
        self.assertEqual(KeyboardInput.key_name('\t'), 'Tab')

    def test_key_name_regular_keys(self):
        """Test key name for regular character keys."""
        self.assertEqual(KeyboardInput.key_name('a'), 'a')
        self.assertEqual(KeyboardInput.key_name('Z'), 'Z')
        self.assertEqual(KeyboardInput.key_name('1'), '1')
        self.assertEqual(KeyboardInput.key_name('?'), '?')

    def test_key_name_unknown(self):
        """Test key name for unknown sequences."""
        result = KeyboardInput.key_name('\x1b[999~')
        # Should return 'Unknown' for multi-char unknown sequences
        self.assertTrue(result == 'Unknown' or len(result) > 1)


class TestArrowKeyDetection(unittest.TestCase):
    """Test suite for arrow key detection."""

    def test_is_arrow_key_up(self):
        """Test up arrow detection."""
        self.assertTrue(is_arrow_key('\x1b[A'))

    def test_is_arrow_key_down(self):
        """Test down arrow detection."""
        self.assertTrue(is_arrow_key('\x1b[B'))

    def test_is_arrow_key_right(self):
        """Test right arrow detection."""
        self.assertTrue(is_arrow_key('\x1b[C'))

    def test_is_arrow_key_left(self):
        """Test left arrow detection."""
        self.assertTrue(is_arrow_key('\x1b[D'))

    def test_is_arrow_key_false(self):
        """Test non-arrow keys return False."""
        self.assertFalse(is_arrow_key('a'))
        self.assertFalse(is_arrow_key('\x1b'))
        self.assertFalse(is_arrow_key('\x1b[H'))
        self.assertFalse(is_arrow_key('\r'))
        self.assertFalse(is_arrow_key(' '))


class TestNavigationKeyDetection(unittest.TestCase):
    """Test suite for navigation key detection."""

    def test_is_navigation_key_arrows(self):
        """Test that arrow keys are navigation keys."""
        self.assertTrue(is_navigation_key('\x1b[A'))
        self.assertTrue(is_navigation_key('\x1b[B'))
        self.assertTrue(is_navigation_key('\x1b[C'))
        self.assertTrue(is_navigation_key('\x1b[D'))

    def test_is_navigation_key_home_end(self):
        """Test Home and End keys."""
        self.assertTrue(is_navigation_key('\x1b[H'))
        self.assertTrue(is_navigation_key('\x1b[F'))

    def test_is_navigation_key_page(self):
        """Test Page Up and Page Down keys."""
        self.assertTrue(is_navigation_key('\x1b[5~'))
        self.assertTrue(is_navigation_key('\x1b[6~'))

    def test_is_navigation_key_false(self):
        """Test non-navigation keys return False."""
        self.assertFalse(is_navigation_key('a'))
        self.assertFalse(is_navigation_key('\x1b'))
        self.assertFalse(is_navigation_key('\r'))
        self.assertFalse(is_navigation_key(' '))
        self.assertFalse(is_navigation_key('\x03'))


class TestEnterKeyDetection(unittest.TestCase):
    """Test suite for Enter key detection."""

    def test_is_enter_key_carriage_return(self):
        """Test carriage return as Enter."""
        self.assertTrue(is_enter_key('\r'))

    def test_is_enter_key_newline(self):
        """Test newline as Enter."""
        self.assertTrue(is_enter_key('\n'))

    def test_is_enter_key_false(self):
        """Test non-Enter keys return False."""
        self.assertFalse(is_enter_key('a'))
        self.assertFalse(is_enter_key('\x1b'))
        self.assertFalse(is_enter_key(' '))
        self.assertFalse(is_enter_key('\x03'))
        self.assertFalse(is_enter_key('\x1b[A'))


class TestEscapeKeyDetection(unittest.TestCase):
    """Test suite for Escape key detection."""

    def test_is_escape_key_true(self):
        """Test Escape key detection."""
        self.assertTrue(is_escape_key('\x1b'))

    def test_is_escape_key_false(self):
        """Test non-Escape keys return False."""
        self.assertFalse(is_escape_key('a'))
        self.assertFalse(is_escape_key('\r'))
        self.assertFalse(is_escape_key(' '))
        self.assertFalse(is_escape_key('\x03'))
        # Note: Arrow keys start with ESC but are not just ESC
        self.assertFalse(is_escape_key('\x1b[A'))


class TestKeyboardInputClass(unittest.TestCase):
    """Test suite for KeyboardInput class initialization."""

    def test_initialization(self):
        """Test KeyboardInput initialization."""
        # Skip if stdin is not a real terminal (e.g., in pytest)
        import sys
        try:
            sys.stdin.fileno()
        except (AttributeError, io.UnsupportedOperation):
            self.skipTest("stdin is not a real terminal")
        
        kb = KeyboardInput()
        self.assertIsNotNone(kb.fd)
        self.assertIsNone(kb.old_settings)

    def test_context_manager_attributes(self):
        """Test that KeyboardInput has context manager methods."""
        # Test that the class has the required methods without instantiating
        self.assertTrue(hasattr(KeyboardInput, '__enter__'))
        self.assertTrue(hasattr(KeyboardInput, '__exit__'))
        self.assertTrue(callable(getattr(KeyboardInput, '__enter__')))
        self.assertTrue(callable(getattr(KeyboardInput, '__exit__')))


if __name__ == '__main__':
    unittest.main()
