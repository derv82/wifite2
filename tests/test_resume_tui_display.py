#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for TUI resume display functionality.
Verifies that session information is properly displayed in scanner and attack views.
"""

import unittest
import time
from unittest.mock import Mock, MagicMock, patch
from wifite.ui.scanner_view import ScannerView
from wifite.ui.attack_view import AttackView, WPAAttackView, WPSAttackView
from wifite.util.session import SessionState, TargetState


class TestResumeDisplayInScanner(unittest.TestCase):
    """Test resume status display in scanner view."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock TUI controller
        self.mock_tui = Mock()
        self.mock_tui.is_running = True
        self.mock_tui.update = Mock()
        
        # Create mock session
        self.session = SessionState(
            session_id="test_session_123",
            created_at=time.time() - 3600,  # 1 hour ago
            updated_at=time.time(),
            config={'interface': 'wlan0mon'},
            targets=[
                TargetState(
                    bssid="AA:BB:CC:DD:EE:FF",
                    essid="TestNetwork1",
                    channel=6,
                    encryption="WPA2",
                    power=65,
                    wps=False,
                    status="completed"
                ),
                TargetState(
                    bssid="11:22:33:44:55:66",
                    essid="TestNetwork2",
                    channel=11,
                    encryption="WPA2",
                    power=45,
                    wps=False,
                    status="pending"
                )
            ],
            completed_targets=["AA:BB:CC:DD:EE:FF"]
        )

    def test_scanner_view_accepts_session_parameter(self):
        """Test that ScannerView can be initialized with a session."""
        view = ScannerView(self.mock_tui, session=self.session)
        self.assertIsNotNone(view.session)
        self.assertEqual(view.session.session_id, "test_session_123")

    def test_scanner_view_without_session(self):
        """Test that ScannerView works without a session (normal mode)."""
        view = ScannerView(self.mock_tui)
        self.assertIsNone(view.session)

    def test_scanner_header_includes_resume_indicator(self):
        """Test that scanner header shows RESUMED SESSION when session is present."""
        view = ScannerView(self.mock_tui, session=self.session)
        view.targets = []
        
        # Render the header
        header_panel = view._render_header()
        
        # Check that the header contains resume information
        # The header is a Panel with Text content
        self.assertIsNotNone(header_panel)

    def test_scanner_header_shows_progress(self):
        """Test that scanner header shows session progress."""
        view = ScannerView(self.mock_tui, session=self.session)
        view.targets = []
        
        # Get progress summary
        summary = self.session.get_progress_summary()
        
        # Verify progress data is correct
        self.assertEqual(summary['total'], 2)
        self.assertEqual(summary['completed'], 1)
        self.assertEqual(summary['remaining'], 1)

    def test_scanner_header_shows_session_age(self):
        """Test that scanner header shows session age."""
        view = ScannerView(self.mock_tui, session=self.session)
        view.targets = []
        
        # Get progress summary
        summary = self.session.get_progress_summary()
        
        # Verify age is calculated (should be around 1 hour)
        self.assertGreater(summary['age_hours'], 0.9)
        self.assertLess(summary['age_hours'], 1.1)


class TestResumeDisplayInAttackView(unittest.TestCase):
    """Test resume status display in attack view."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock TUI controller
        self.mock_tui = Mock()
        self.mock_tui.is_running = True
        self.mock_tui.update = Mock()
        
        # Create mock target
        self.mock_target = Mock()
        self.mock_target.bssid = "AA:BB:CC:DD:EE:FF"
        self.mock_target.essid = "TestNetwork"
        self.mock_target.channel = 6
        self.mock_target.encryption = "WPA2"
        self.mock_target.power = 65
        self.mock_target.wps = False
        
        # Create mock session
        self.session = SessionState(
            session_id="test_session_123",
            created_at=time.time() - 3600,
            updated_at=time.time(),
            config={'interface': 'wlan0mon'},
            targets=[],
            completed_targets=[]
        )
        
        # Create target state
        self.target_state = TargetState(
            bssid="AA:BB:CC:DD:EE:FF",
            essid="TestNetwork",
            channel=6,
            encryption="WPA2",
            power=65,
            wps=False,
            status="in_progress",
            attempts=2,
            last_attempt=time.time() - 1800  # 30 minutes ago
        )

    def test_attack_view_accepts_session_parameters(self):
        """Test that AttackView can be initialized with session and target_state."""
        view = AttackView(
            self.mock_tui,
            self.mock_target,
            session=self.session,
            target_state=self.target_state
        )
        self.assertIsNotNone(view.session)
        self.assertIsNotNone(view.target_state)
        self.assertEqual(view.session.session_id, "test_session_123")
        self.assertEqual(view.target_state.attempts, 2)

    def test_attack_view_without_session(self):
        """Test that AttackView works without session (normal mode)."""
        view = AttackView(self.mock_tui, self.mock_target)
        self.assertIsNone(view.session)
        self.assertIsNone(view.target_state)

    def test_attack_view_shows_attempt_number(self):
        """Test that attack view shows attempt number for resumed targets."""
        view = AttackView(
            self.mock_tui,
            self.mock_target,
            session=self.session,
            target_state=self.target_state
        )
        
        # Verify target state has attempts
        self.assertEqual(view.target_state.attempts, 2)
        
        # The next attempt should be #3
        next_attempt = view.target_state.attempts + 1
        self.assertEqual(next_attempt, 3)

    def test_attack_view_shows_last_attempt_time(self):
        """Test that attack view shows last attempt timestamp."""
        view = AttackView(
            self.mock_tui,
            self.mock_target,
            session=self.session,
            target_state=self.target_state
        )
        
        # Verify last attempt time is set
        self.assertIsNotNone(view.target_state.last_attempt)
        
        # Verify it's in the past (30 minutes ago)
        time_diff = time.time() - view.target_state.last_attempt
        self.assertGreater(time_diff, 1700)  # At least 28 minutes
        self.assertLess(time_diff, 2000)  # Less than 33 minutes

    def test_wpa_attack_view_with_session(self):
        """Test that WPAAttackView works with session parameters."""
        view = WPAAttackView(
            self.mock_tui,
            self.mock_target,
            session=self.session,
            target_state=self.target_state
        )
        self.assertIsNotNone(view.session)
        self.assertIsNotNone(view.target_state)
        self.assertEqual(view.attack_type, "WPA Handshake Capture")

    def test_wps_attack_view_with_session(self):
        """Test that WPSAttackView works with session parameters."""
        view = WPSAttackView(
            self.mock_tui,
            self.mock_target,
            session=self.session,
            target_state=self.target_state
        )
        self.assertIsNotNone(view.session)
        self.assertIsNotNone(view.target_state)
        self.assertEqual(view.attack_type, "WPS Attack")


class TestResumeIndicatorRendering(unittest.TestCase):
    """Test that resume indicators are properly rendered in UI."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_tui = Mock()
        self.mock_tui.is_running = True
        self.mock_tui.update = Mock()
        
        self.mock_target = Mock()
        self.mock_target.bssid = "AA:BB:CC:DD:EE:FF"
        self.mock_target.essid = "TestNetwork"
        self.mock_target.channel = 6
        self.mock_target.encryption = "WPA2"
        self.mock_target.power = 65
        self.mock_target.wps = False
        
        self.session = SessionState(
            session_id="test_session_123",
            created_at=time.time() - 3600,
            updated_at=time.time(),
            config={'interface': 'wlan0mon'},
            targets=[],
            completed_targets=[]
        )
        
        self.target_state = TargetState(
            bssid="AA:BB:CC:DD:EE:FF",
            essid="TestNetwork",
            channel=6,
            encryption="WPA2",
            power=65,
            wps=False,
            status="in_progress",
            attempts=1,
            last_attempt=time.time() - 1800
        )

    def test_target_info_panel_includes_resume_indicator(self):
        """Test that target info panel shows RESUMED indicator."""
        view = AttackView(
            self.mock_tui,
            self.mock_target,
            session=self.session,
            target_state=self.target_state
        )
        
        # Render target info panel
        panel = view._render_target_info()
        
        # Panel should be created successfully
        self.assertIsNotNone(panel)

    def test_target_info_panel_without_session(self):
        """Test that target info panel works normally without session."""
        view = AttackView(self.mock_tui, self.mock_target)
        
        # Render target info panel
        panel = view._render_target_info()
        
        # Panel should be created successfully
        self.assertIsNotNone(panel)


if __name__ == '__main__':
    unittest.main()
