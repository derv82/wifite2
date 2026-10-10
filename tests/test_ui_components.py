#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for wifite2 TUI UI components.
Tests rendering, calculations, and behavior of reusable UI components.
"""

import unittest
from wifite.ui.components import (
    SignalStrengthBar,
    EncryptionBadge,
    ProgressPanel,
    LogPanel,
    HelpOverlay
)
from rich.text import Text


class TestSignalStrengthBar(unittest.TestCase):
    """Test suite for SignalStrengthBar component."""

    def test_strong_signal_rendering(self):
        """Test rendering of strong signal (>= -50 dBm)."""
        result = SignalStrengthBar.render(-45)
        self.assertIsInstance(result, Text)
        self.assertEqual(str(result.plain), "███")
        self.assertEqual(result.style, "green")

    def test_medium_signal_rendering(self):
        """Test rendering of medium signal (-70 to -50 dBm)."""
        result = SignalStrengthBar.render(-60)
        self.assertIsInstance(result, Text)
        self.assertEqual(str(result.plain), "██ ")
        self.assertEqual(result.style, "yellow")

    def test_weak_signal_rendering(self):
        """Test rendering of weak signal (< -70 dBm)."""
        result = SignalStrengthBar.render(-85)
        self.assertIsInstance(result, Text)
        self.assertEqual(str(result.plain), "█  ")
        self.assertEqual(result.style, "red")

    def test_boundary_strong_threshold(self):
        """Test signal at strong threshold boundary (-50 dBm)."""
        result = SignalStrengthBar.render(-50)
        self.assertEqual(str(result.plain), "███")
        self.assertEqual(result.style, "green")

    def test_boundary_medium_threshold(self):
        """Test signal at medium threshold boundary (-70 dBm)."""
        result = SignalStrengthBar.render(-70)
        self.assertEqual(str(result.plain), "██ ")
        self.assertEqual(result.style, "yellow")


class TestEncryptionBadge(unittest.TestCase):
    """Test suite for EncryptionBadge component."""

    def test_wep_rendering(self):
        """Test WEP encryption badge rendering."""
        result = EncryptionBadge.render("WEP")
        self.assertIsInstance(result, Text)
        self.assertEqual(str(result.plain), "WEP")
        self.assertEqual(result.style, "red")

    def test_wpa_rendering(self):
        """Test WPA encryption badge rendering."""
        result = EncryptionBadge.render("WPA")
        self.assertIsInstance(result, Text)
        self.assertEqual(str(result.plain), "WPA")
        self.assertEqual(result.style, "yellow")

    def test_wpa2_rendering(self):
        """Test WPA2 encryption badge rendering."""
        result = EncryptionBadge.render("WPA2")
        self.assertIsInstance(result, Text)
        self.assertEqual(str(result.plain), "WPA2")
        self.assertEqual(result.style, "yellow")

    def test_wpa3_rendering(self):
        """Test WPA3 encryption badge rendering."""
        result = EncryptionBadge.render("WPA3")
        self.assertIsInstance(result, Text)
        self.assertEqual(str(result.plain), "WPA3")
        self.assertEqual(result.style, "green")

    def test_wps_rendering(self):
        """Test WPS encryption badge rendering."""
        result = EncryptionBadge.render("WPS")
        self.assertIsInstance(result, Text)
        self.assertEqual(str(result.plain), "WPS")
        self.assertEqual(result.style, "cyan")

    def test_open_rendering(self):
        """Test OPEN encryption badge rendering."""
        result = EncryptionBadge.render("OPEN")
        self.assertIsInstance(result, Text)
        self.assertEqual(str(result.plain), "OPEN")
        self.assertEqual(result.style, "bright_black")

    def test_case_insensitive(self):
        """Test that encryption type is case-insensitive."""
        result_lower = EncryptionBadge.render("wpa2")
        result_upper = EncryptionBadge.render("WPA2")
        result_mixed = EncryptionBadge.render("Wpa2")
        
        # All should have the same color
        self.assertEqual(result_lower.style, "yellow")
        self.assertEqual(result_upper.style, "yellow")
        self.assertEqual(result_mixed.style, "yellow")

    def test_unknown_encryption(self):
        """Test unknown encryption type defaults to white."""
        result = EncryptionBadge.render("UNKNOWN")
        self.assertIsInstance(result, Text)
        self.assertEqual(result.style, "white")


class TestProgressPanel(unittest.TestCase):
    """Test suite for ProgressPanel component."""

    def test_time_formatting(self):
        """Test time formatting helper method."""
        self.assertEqual(ProgressPanel._format_time(0), "00:00")
        self.assertEqual(ProgressPanel._format_time(59), "00:59")
        self.assertEqual(ProgressPanel._format_time(60), "01:00")
        self.assertEqual(ProgressPanel._format_time(125), "02:05")
        self.assertEqual(ProgressPanel._format_time(3661), "61:01")

    def test_progress_bar_creation(self):
        """Test progress bar text creation."""
        # Test 0% progress
        bar_0 = ProgressPanel._create_progress_bar(0.0)
        self.assertIn("0%", str(bar_0.plain))
        
        # Test 50% progress
        bar_50 = ProgressPanel._create_progress_bar(0.5)
        self.assertIn("50%", str(bar_50.plain))
        
        # Test 100% progress
        bar_100 = ProgressPanel._create_progress_bar(1.0)
        self.assertIn("100%", str(bar_100.plain))

    def test_progress_bar_visual_length(self):
        """Test that progress bar has correct visual representation."""
        bar_width = 40
        
        # Test 25% progress
        bar = ProgressPanel._create_progress_bar(0.25)
        plain_text = str(bar.plain)
        filled_count = plain_text.count("█")
        self.assertEqual(filled_count, int(bar_width * 0.25))
        
        # Test 75% progress
        bar = ProgressPanel._create_progress_bar(0.75)
        plain_text = str(bar.plain)
        filled_count = plain_text.count("█")
        self.assertEqual(filled_count, int(bar_width * 0.75))

    def test_panel_rendering_basic(self):
        """Test basic panel rendering with minimal parameters."""
        panel = ProgressPanel.render(
            attack_type="WPA Handshake",
            elapsed_time=120,
            progress_percent=0.5,
            status_message="Waiting for handshake",
            metrics={}
        )
        
        # Panel should be created
        self.assertIsNotNone(panel)
        # Title is a string with markup, check if it contains "Progress"
        self.assertIn("Progress", str(panel.title))

    def test_panel_rendering_with_metrics(self):
        """Test panel rendering with metrics."""
        metrics = {
            "Clients": 2,
            "Deauths sent": 15,
            "Handshakes": 0
        }
        
        panel = ProgressPanel.render(
            attack_type="WPA Handshake",
            elapsed_time=180,
            progress_percent=0.6,
            status_message="Capturing handshake",
            metrics=metrics
        )
        
        self.assertIsNotNone(panel)

    def test_panel_rendering_with_total_time(self):
        """Test panel rendering with total time."""
        panel = ProgressPanel.render(
            attack_type="WPS PIN Attack",
            elapsed_time=60,
            progress_percent=0.3,
            status_message="Trying PINs",
            metrics={"PINs tried": 1500},
            total_time=200
        )
        
        self.assertIsNotNone(panel)


class TestLogPanel(unittest.TestCase):
    """Test suite for LogPanel component."""

    def test_initialization(self):
        """Test LogPanel initialization."""
        panel = LogPanel()
        self.assertEqual(panel.max_entries, 1000)
        self.assertEqual(len(panel.logs), 0)
        self.assertTrue(panel.auto_scroll)

    def test_initialization_custom_max(self):
        """Test LogPanel initialization with custom max entries."""
        panel = LogPanel(max_entries=500)
        self.assertEqual(panel.max_entries, 500)

    def test_add_log(self):
        """Test adding log entries."""
        panel = LogPanel()
        panel.add_log("Test log 1")
        panel.add_log("Test log 2")
        
        self.assertEqual(len(panel.logs), 2)
        self.assertEqual(panel.logs[0], "Test log 1")
        self.assertEqual(panel.logs[1], "Test log 2")

    def test_max_entries_limit(self):
        """Test that log panel respects max entries limit."""
        panel = LogPanel(max_entries=10)
        
        # Add more than max entries
        for i in range(20):
            panel.add_log(f"Log entry {i}")
        
        # Should only keep the last 10
        self.assertEqual(len(panel.logs), 10)
        self.assertEqual(panel.logs[0], "Log entry 10")
        self.assertEqual(panel.logs[-1], "Log entry 19")

    def test_cleanup_old_entries(self):
        """Test manual cleanup of old entries."""
        panel = LogPanel(max_entries=100)
        
        # Add 50 entries
        for i in range(50):
            panel.add_log(f"Log {i}")
        
        # Clean up to keep only 20
        panel.cleanup_old_entries(keep_count=20)
        
        self.assertEqual(len(panel.logs), 20)
        self.assertEqual(panel.logs[0], "Log 30")
        self.assertEqual(panel.logs[-1], "Log 49")

    def test_cleanup_with_default_count(self):
        """Test cleanup with default count (max_entries)."""
        panel = LogPanel(max_entries=50)
        
        # Add 100 entries
        for i in range(100):
            panel.add_log(f"Log {i}")
        
        # Should already be trimmed to 50
        self.assertEqual(len(panel.logs), 50)
        
        # Cleanup with default should keep max_entries
        panel.cleanup_old_entries()
        self.assertEqual(len(panel.logs), 50)

    def test_render_empty(self):
        """Test rendering empty log panel."""
        panel = LogPanel()
        rendered = panel.render(height=10)
        
        self.assertIsNotNone(rendered)
        # Title is a string with markup, check if it contains "Logs"
        self.assertIn("Logs", str(rendered.title))

    def test_render_with_logs(self):
        """Test rendering log panel with entries."""
        panel = LogPanel()
        panel.add_log("Log entry 1")
        panel.add_log("Log entry 2")
        panel.add_log("Log entry 3")
        
        rendered = panel.render(height=5)
        self.assertIsNotNone(rendered)

    def test_render_height_limit(self):
        """Test that render respects height limit."""
        panel = LogPanel()
        
        # Add many logs
        for i in range(20):
            panel.add_log(f"Log {i}")
        
        # Render with height 5 should only show last 5
        rendered = panel.render(height=5)
        self.assertIsNotNone(rendered)

    def test_clear(self):
        """Test clearing all log entries."""
        panel = LogPanel()
        panel.add_log("Log 1")
        panel.add_log("Log 2")
        
        self.assertEqual(len(panel.logs), 2)
        
        panel.clear()
        self.assertEqual(len(panel.logs), 0)


class TestHelpOverlay(unittest.TestCase):
    """Test suite for HelpOverlay component."""

    def test_general_help_rendering(self):
        """Test rendering general help overlay."""
        panel = HelpOverlay.render(context="general")
        self.assertIsNotNone(panel)
        # Title is a string with markup, check if it contains "Keyboard Shortcuts"
        self.assertIn("Keyboard Shortcuts", str(panel.title))

    def test_scanner_help_rendering(self):
        """Test rendering scanner-specific help."""
        panel = HelpOverlay.render(context="scanner")
        self.assertIsNotNone(panel)

    def test_selector_help_rendering(self):
        """Test rendering selector-specific help."""
        panel = HelpOverlay.render(context="selector")
        self.assertIsNotNone(panel)

    def test_attack_help_rendering(self):
        """Test rendering attack-specific help."""
        panel = HelpOverlay.render(context="attack")
        self.assertIsNotNone(panel)

    def test_shortcuts_content_general(self):
        """Test that general shortcuts are included."""
        shortcuts = HelpOverlay._get_shortcuts("general")
        
        # Should have basic shortcuts
        self.assertGreater(len(shortcuts), 0)
        
        # Check for expected shortcuts
        keys = [s[0] for s in shortcuts]
        self.assertIn("?", keys)
        self.assertIn("q", keys)
        self.assertIn("Ctrl+C", keys)

    def test_shortcuts_content_scanner(self):
        """Test that scanner shortcuts include general + scanner-specific."""
        shortcuts = HelpOverlay._get_shortcuts("scanner")
        keys = [s[0] for s in shortcuts]
        
        # Should have general shortcuts
        self.assertIn("?", keys)
        self.assertIn("q", keys)
        
        # Should have scanner-specific
        self.assertIn("Ctrl+C", keys)

    def test_shortcuts_content_selector(self):
        """Test that selector shortcuts include navigation keys."""
        shortcuts = HelpOverlay._get_shortcuts("selector")
        keys = [s[0] for s in shortcuts]
        
        # Should have selector-specific shortcuts
        self.assertIn("↑ / ↓", keys)
        self.assertIn("Space", keys)
        self.assertIn("Enter", keys)
        self.assertIn("a", keys)
        self.assertIn("n", keys)

    def test_shortcuts_content_attack(self):
        """Test that attack shortcuts include attack-specific keys."""
        shortcuts = HelpOverlay._get_shortcuts("attack")
        keys = [s[0] for s in shortcuts]
        
        # Should have attack-specific shortcuts
        self.assertIn("Ctrl+C", keys)
        self.assertIn("c", keys)  # Continue
        self.assertIn("s", keys)  # Skip
        self.assertIn("i", keys)  # Ignore
        self.assertIn("e", keys)  # Exit


if __name__ == '__main__':
    unittest.main()
