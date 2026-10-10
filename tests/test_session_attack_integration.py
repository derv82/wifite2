#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integration tests for session updates during attack execution.
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, MagicMock, patch


class TestSessionAttackIntegration(unittest.TestCase):
    """Test session updates during attack execution flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for session files
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_attack_flow_with_session_updates(self):
        """Test complete attack flow with session updates."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        # Create session manager with temp directory
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a mock session with multiple targets
        target1 = TargetState(
            bssid='AA:BB:CC:DD:EE:FF',
            essid='Network1',
            channel=6,
            encryption='WPA2',
            power=50,
            wps=False
        )
        
        target2 = TargetState(
            bssid='11:22:33:44:55:66',
            essid='Network2',
            channel=11,
            encryption='WPA2',
            power=45,
            wps=False
        )
        
        target3 = TargetState(
            bssid='77:88:99:AA:BB:CC',
            essid='Network3',
            channel=1,
            encryption='WPA2',
            power=55,
            wps=False
        )
        
        session = SessionState(
            session_id='test_attack_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=[target1, target2, target3]
        )
        
        # Save initial session
        session_mgr.save_session(session)
        
        # Simulate attack flow: target1 succeeds
        session_mgr.mark_target_complete(session, 'AA:BB:CC:DD:EE:FF', None)
        session_mgr.save_session(session)
        
        # Verify target1 is completed
        self.assertIn('AA:BB:CC:DD:EE:FF', session.completed_targets)
        self.assertEqual(target1.status, 'completed')
        
        # Simulate attack flow: target2 fails
        session_mgr.mark_target_failed(session, '11:22:33:44:55:66', 'All attacks failed')
        session_mgr.save_session(session)
        
        # Verify target2 is failed
        self.assertIn('11:22:33:44:55:66', session.failed_targets)
        self.assertEqual(target2.status, 'failed')
        
        # Verify target3 is still pending
        self.assertNotIn('77:88:99:AA:BB:CC', session.completed_targets)
        self.assertNotIn('77:88:99:AA:BB:CC', session.failed_targets)
        self.assertEqual(target3.status, 'pending')
        
        # Get remaining targets
        remaining = session_mgr.get_remaining_targets(session)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].bssid, '77:88:99:AA:BB:CC')
        
        # Load session from disk and verify persistence
        loaded_session = session_mgr.load_session('test_attack_session')
        self.assertEqual(len(loaded_session.completed_targets), 1)
        self.assertEqual(len(loaded_session.failed_targets), 1)
        self.assertIn('AA:BB:CC:DD:EE:FF', loaded_session.completed_targets)
        self.assertIn('11:22:33:44:55:66', loaded_session.failed_targets)
    
    def test_session_progress_summary(self):
        """Test session progress summary after updates."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        # Create session manager with temp directory
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a mock session with targets
        targets = [
            TargetState(
                bssid=f'AA:BB:CC:DD:EE:{i:02X}',
                essid=f'Network{i}',
                channel=6,
                encryption='WPA2',
                power=50,
                wps=False
            )
            for i in range(5)
        ]
        
        session = SessionState(
            session_id='test_progress_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=targets
        )
        
        # Mark some targets as completed
        session_mgr.mark_target_complete(session, 'AA:BB:CC:DD:EE:00', None)
        session_mgr.mark_target_complete(session, 'AA:BB:CC:DD:EE:01', None)
        
        # Mark some targets as failed
        session_mgr.mark_target_failed(session, 'AA:BB:CC:DD:EE:02', 'Failed')
        
        # Get progress summary
        summary = session.get_progress_summary()
        
        self.assertEqual(summary['total'], 5)
        self.assertEqual(summary['completed'], 2)
        self.assertEqual(summary['failed'], 1)
        self.assertEqual(summary['remaining'], 2)
        self.assertEqual(summary['progress_percent'], 40.0)  # 2/5 * 100


if __name__ == '__main__':
    unittest.main()
