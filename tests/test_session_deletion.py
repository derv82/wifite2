#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for session deletion on successful completion.
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, MagicMock, patch


class TestSessionDeletion(unittest.TestCase):
    """Test session deletion on successful completion."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for session files
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_session_deleted_when_all_targets_complete(self):
        """Test that session is deleted when all targets are completed."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        # Create session manager with temp directory
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a session with targets
        targets = [
            TargetState(
                bssid=f'AA:BB:CC:DD:EE:{i:02X}',
                essid=f'Network{i}',
                channel=6,
                encryption='WPA2',
                power=50,
                wps=False
            )
            for i in range(3)
        ]
        
        session = SessionState(
            session_id='test_complete_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=targets
        )
        
        # Save session
        session_mgr.save_session(session)
        session_path = os.path.join(self.temp_dir, 'test_complete_session.json')
        self.assertTrue(os.path.exists(session_path))
        
        # Mark all targets as completed
        for target in targets:
            session_mgr.mark_target_complete(session, target.bssid, None)
        
        # Verify all targets are completed
        summary = session.get_progress_summary()
        self.assertEqual(summary['remaining'], 0)
        self.assertEqual(summary['completed'], 3)
        
        # Delete session (simulating successful completion)
        session_mgr.delete_session(session.session_id)
        
        # Verify session file is deleted
        self.assertFalse(os.path.exists(session_path))
    
    def test_session_preserved_when_targets_remain(self):
        """Test that session is preserved when targets remain."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        # Create session manager with temp directory
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a session with targets
        targets = [
            TargetState(
                bssid=f'AA:BB:CC:DD:EE:{i:02X}',
                essid=f'Network{i}',
                channel=6,
                encryption='WPA2',
                power=50,
                wps=False
            )
            for i in range(3)
        ]
        
        session = SessionState(
            session_id='test_incomplete_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=targets
        )
        
        # Save session
        session_mgr.save_session(session)
        session_path = os.path.join(self.temp_dir, 'test_incomplete_session.json')
        self.assertTrue(os.path.exists(session_path))
        
        # Mark only some targets as completed
        session_mgr.mark_target_complete(session, targets[0].bssid, None)
        session_mgr.mark_target_failed(session, targets[1].bssid, 'Failed')
        session_mgr.save_session(session)
        
        # Verify some targets remain
        summary = session.get_progress_summary()
        self.assertEqual(summary['remaining'], 1)
        
        # Session should NOT be deleted (simulating interrupted attack)
        # Verify session file still exists
        self.assertTrue(os.path.exists(session_path))
    
    def test_session_deleted_when_all_targets_failed(self):
        """Test that session can be deleted even when all targets failed."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        # Create session manager with temp directory
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a session with targets
        targets = [
            TargetState(
                bssid=f'AA:BB:CC:DD:EE:{i:02X}',
                essid=f'Network{i}',
                channel=6,
                encryption='WPA2',
                power=50,
                wps=False
            )
            for i in range(3)
        ]
        
        session = SessionState(
            session_id='test_failed_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=targets
        )
        
        # Save session
        session_mgr.save_session(session)
        session_path = os.path.join(self.temp_dir, 'test_failed_session.json')
        self.assertTrue(os.path.exists(session_path))
        
        # Mark all targets as failed
        for target in targets:
            session_mgr.mark_target_failed(session, target.bssid, 'All attacks failed')
        
        # Verify all targets are processed (no remaining)
        summary = session.get_progress_summary()
        self.assertEqual(summary['remaining'], 0)
        self.assertEqual(summary['failed'], 3)
        
        # Delete session (simulating completion with all failures)
        session_mgr.delete_session(session.session_id)
        
        # Verify session file is deleted
        self.assertFalse(os.path.exists(session_path))
    
    def test_delete_nonexistent_session_graceful(self):
        """Test that deleting a nonexistent session doesn't raise an error."""
        from wifite.util.session import SessionManager
        
        # Create session manager with temp directory
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Try to delete a session that doesn't exist
        # Should not raise an error
        try:
            session_mgr.delete_session('nonexistent_session')
        except Exception as e:
            self.fail(f"delete_session raised an exception: {e}")


if __name__ == '__main__':
    unittest.main()
