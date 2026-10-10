#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for target filtering during resume.
"""

import unittest
import tempfile
import os
import shutil


class TestTargetFiltering(unittest.TestCase):
    """Test target filtering for resume functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for session files
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_filter_completed_targets(self):
        """Test that completed targets are filtered out."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with multiple targets
        targets = [
            TargetState(
                bssid='AA:BB:CC:DD:EE:00',
                essid='Network0',
                channel=6,
                encryption='WPA2',
                power=50,
                wps=False
            ),
            TargetState(
                bssid='AA:BB:CC:DD:EE:01',
                essid='Network1',
                channel=11,
                encryption='WPA2',
                power=45,
                wps=False
            ),
            TargetState(
                bssid='AA:BB:CC:DD:EE:02',
                essid='Network2',
                channel=1,
                encryption='WPA2',
                power=55,
                wps=False
            ),
        ]
        
        session = SessionState(
            session_id='test_filter_completed',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=targets
        )
        
        # Mark first target as completed
        session_mgr.mark_target_complete(session, 'AA:BB:CC:DD:EE:00', None)
        
        # Get remaining targets
        remaining = session_mgr.get_remaining_targets(session)
        
        # Should have 2 remaining targets (not the completed one)
        self.assertEqual(len(remaining), 2)
        self.assertEqual(remaining[0].bssid, 'AA:BB:CC:DD:EE:01')
        self.assertEqual(remaining[1].bssid, 'AA:BB:CC:DD:EE:02')
    
    def test_filter_failed_targets(self):
        """Test that failed targets are filtered out by default."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with multiple targets
        targets = [
            TargetState(
                bssid='AA:BB:CC:DD:EE:00',
                essid='Network0',
                channel=6,
                encryption='WPA2',
                power=50,
                wps=False
            ),
            TargetState(
                bssid='AA:BB:CC:DD:EE:01',
                essid='Network1',
                channel=11,
                encryption='WPA2',
                power=45,
                wps=False
            ),
            TargetState(
                bssid='AA:BB:CC:DD:EE:02',
                essid='Network2',
                channel=1,
                encryption='WPA2',
                power=55,
                wps=False
            ),
        ]
        
        session = SessionState(
            session_id='test_filter_failed',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=targets
        )
        
        # Mark first target as failed
        session_mgr.mark_target_failed(session, 'AA:BB:CC:DD:EE:00', 'All attacks failed')
        
        # Get remaining targets (without retry)
        remaining = session_mgr.get_remaining_targets(session, include_failed=False)
        
        # Should have 2 remaining targets (not the failed one)
        self.assertEqual(len(remaining), 2)
        self.assertEqual(remaining[0].bssid, 'AA:BB:CC:DD:EE:01')
        self.assertEqual(remaining[1].bssid, 'AA:BB:CC:DD:EE:02')
    
    def test_include_failed_targets_with_retry(self):
        """Test that failed targets are included when retry is enabled."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with multiple targets
        targets = [
            TargetState(
                bssid='AA:BB:CC:DD:EE:00',
                essid='Network0',
                channel=6,
                encryption='WPA2',
                power=50,
                wps=False
            ),
            TargetState(
                bssid='AA:BB:CC:DD:EE:01',
                essid='Network1',
                channel=11,
                encryption='WPA2',
                power=45,
                wps=False
            ),
        ]
        
        session = SessionState(
            session_id='test_retry_failed',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=targets
        )
        
        # Mark first target as failed
        session_mgr.mark_target_failed(session, 'AA:BB:CC:DD:EE:00', 'All attacks failed')
        
        # Get remaining targets WITH retry enabled
        remaining = session_mgr.get_remaining_targets(session, include_failed=True)
        
        # Should have 2 targets (including the failed one for retry)
        self.assertEqual(len(remaining), 2)
        self.assertEqual(remaining[0].bssid, 'AA:BB:CC:DD:EE:00')
        self.assertEqual(remaining[1].bssid, 'AA:BB:CC:DD:EE:01')
    
    def test_preserve_original_order(self):
        """Test that original target order is preserved."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with targets in specific order
        targets = [
            TargetState(
                bssid='AA:BB:CC:DD:EE:00',
                essid='Network0',
                channel=6,
                encryption='WPA2',
                power=50,
                wps=False
            ),
            TargetState(
                bssid='AA:BB:CC:DD:EE:01',
                essid='Network1',
                channel=11,
                encryption='WPA2',
                power=45,
                wps=False
            ),
            TargetState(
                bssid='AA:BB:CC:DD:EE:02',
                essid='Network2',
                channel=1,
                encryption='WPA2',
                power=55,
                wps=False
            ),
            TargetState(
                bssid='AA:BB:CC:DD:EE:03',
                essid='Network3',
                channel=6,
                encryption='WPA2',
                power=60,
                wps=False
            ),
        ]
        
        session = SessionState(
            session_id='test_preserve_order',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=targets
        )
        
        # Mark some targets as completed/failed (not in order)
        session_mgr.mark_target_complete(session, 'AA:BB:CC:DD:EE:01', None)
        session_mgr.mark_target_failed(session, 'AA:BB:CC:DD:EE:03', 'Failed')
        
        # Get remaining targets
        remaining = session_mgr.get_remaining_targets(session)
        
        # Should have 2 remaining targets in original order
        self.assertEqual(len(remaining), 2)
        self.assertEqual(remaining[0].bssid, 'AA:BB:CC:DD:EE:00')
        self.assertEqual(remaining[1].bssid, 'AA:BB:CC:DD:EE:02')
    
    def test_include_in_progress_targets(self):
        """Test that in-progress targets are included."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with targets
        targets = [
            TargetState(
                bssid='AA:BB:CC:DD:EE:00',
                essid='Network0',
                channel=6,
                encryption='WPA2',
                power=50,
                wps=False,
                status='in_progress'  # Interrupted during attack
            ),
            TargetState(
                bssid='AA:BB:CC:DD:EE:01',
                essid='Network1',
                channel=11,
                encryption='WPA2',
                power=45,
                wps=False,
                status='pending'
            ),
        ]
        
        session = SessionState(
            session_id='test_in_progress',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=targets
        )
        
        # Get remaining targets
        remaining = session_mgr.get_remaining_targets(session)
        
        # Should include both in_progress and pending targets
        self.assertEqual(len(remaining), 2)
        self.assertEqual(remaining[0].status, 'in_progress')
        self.assertEqual(remaining[1].status, 'pending')
    
    def test_all_targets_completed(self):
        """Test that empty list is returned when all targets are completed."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with targets
        targets = [
            TargetState(
                bssid='AA:BB:CC:DD:EE:00',
                essid='Network0',
                channel=6,
                encryption='WPA2',
                power=50,
                wps=False
            ),
            TargetState(
                bssid='AA:BB:CC:DD:EE:01',
                essid='Network1',
                channel=11,
                encryption='WPA2',
                power=45,
                wps=False
            ),
        ]
        
        session = SessionState(
            session_id='test_all_completed',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=targets
        )
        
        # Mark all targets as completed
        session_mgr.mark_target_complete(session, 'AA:BB:CC:DD:EE:00', None)
        session_mgr.mark_target_complete(session, 'AA:BB:CC:DD:EE:01', None)
        
        # Get remaining targets
        remaining = session_mgr.get_remaining_targets(session)
        
        # Should have no remaining targets
        self.assertEqual(len(remaining), 0)


if __name__ == '__main__':
    unittest.main()
