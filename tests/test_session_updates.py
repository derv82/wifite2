#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for session update functionality during attack execution.
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, MagicMock, patch


class TestSessionUpdates(unittest.TestCase):
    """Test session updates during attack execution."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for session files
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_session_manager_mark_target_complete(self):
        """Test marking a target as completed in session."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        # Create session manager with temp directory
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a mock session with targets
        target1 = TargetState(
            bssid='AA:BB:CC:DD:EE:FF',
            essid='TestNetwork',
            channel=6,
            encryption='WPA2',
            power=50,
            wps=False
        )
        
        session = SessionState(
            session_id='test_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=[target1]
        )
        
        # Mark target as complete
        session_mgr.mark_target_complete(session, 'AA:BB:CC:DD:EE:FF', None)
        
        # Verify target is marked as completed
        self.assertIn('AA:BB:CC:DD:EE:FF', session.completed_targets)
        self.assertEqual(target1.status, 'completed')
        self.assertEqual(target1.attempts, 1)
        self.assertIsNotNone(target1.last_attempt)
    
    def test_session_manager_mark_target_failed(self):
        """Test marking a target as failed in session."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        # Create session manager with temp directory
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a mock session with targets
        target1 = TargetState(
            bssid='AA:BB:CC:DD:EE:FF',
            essid='TestNetwork',
            channel=6,
            encryption='WPA2',
            power=50,
            wps=False
        )
        
        session = SessionState(
            session_id='test_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=[target1]
        )
        
        # Mark target as failed
        session_mgr.mark_target_failed(session, 'AA:BB:CC:DD:EE:FF', 'Test failure reason')
        
        # Verify target is marked as failed
        self.assertIn('AA:BB:CC:DD:EE:FF', session.failed_targets)
        self.assertEqual(session.failed_targets['AA:BB:CC:DD:EE:FF'], 'Test failure reason')
        self.assertEqual(target1.status, 'failed')
        self.assertEqual(target1.attempts, 1)
        self.assertIsNotNone(target1.last_attempt)
    
    def test_session_save_after_update(self):
        """Test that session is saved after marking target status."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        # Create session manager with temp directory
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a mock session with targets
        target1 = TargetState(
            bssid='AA:BB:CC:DD:EE:FF',
            essid='TestNetwork',
            channel=6,
            encryption='WPA2',
            power=50,
            wps=False
        )
        
        session = SessionState(
            session_id='test_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=[target1]
        )
        
        # Mark target as complete and save
        session_mgr.mark_target_complete(session, 'AA:BB:CC:DD:EE:FF', None)
        session_mgr.save_session(session)
        
        # Verify session file exists
        session_path = os.path.join(self.temp_dir, 'test_session.json')
        self.assertTrue(os.path.exists(session_path))
        
        # Load session and verify data persisted
        loaded_session = session_mgr.load_session('test_session')
        self.assertIn('AA:BB:CC:DD:EE:FF', loaded_session.completed_targets)
        self.assertEqual(loaded_session.targets[0].status, 'completed')


if __name__ == '__main__':
    unittest.main()
