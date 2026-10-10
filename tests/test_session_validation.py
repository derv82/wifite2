#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for session loading and validation logic.
"""

import unittest
import tempfile
import os
import shutil
import json
from unittest.mock import Mock, MagicMock, patch


class TestSessionValidation(unittest.TestCase):
    """Test session loading and validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for session files
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_load_valid_session(self):
        """Test loading a valid session file."""
        from wifite.util.session import SessionManager, SessionState, TargetState
        
        # Create session manager with temp directory
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a valid session
        target = TargetState(
            bssid='AA:BB:CC:DD:EE:FF',
            essid='TestNetwork',
            channel=6,
            encryption='WPA2',
            power=50,
            wps=False
        )
        
        session = SessionState(
            session_id='test_valid_session',
            created_at=1234567890.0,
            updated_at=1234567890.0,
            config={},
            targets=[target]
        )
        
        # Save session
        session_mgr.save_session(session)
        
        # Load session
        loaded_session = session_mgr.load_session('test_valid_session')
        
        # Verify loaded data
        self.assertEqual(loaded_session.session_id, 'test_valid_session')
        self.assertEqual(len(loaded_session.targets), 1)
        self.assertEqual(loaded_session.targets[0].bssid, 'AA:BB:CC:DD:EE:FF')
    
    def test_load_nonexistent_session(self):
        """Test loading a nonexistent session raises FileNotFoundError."""
        from wifite.util.session import SessionManager
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        with self.assertRaises(FileNotFoundError) as context:
            session_mgr.load_session('nonexistent_session')
        
        self.assertIn('not found', str(context.exception).lower())
    
    def test_load_corrupted_json(self):
        """Test loading a corrupted JSON file raises ValueError."""
        from wifite.util.session import SessionManager
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create a corrupted JSON file
        session_path = os.path.join(self.temp_dir, 'corrupted_session.json')
        with open(session_path, 'w') as f:
            f.write('{ invalid json content }')
        
        with self.assertRaises(ValueError) as context:
            session_mgr.load_session('corrupted_session')
        
        self.assertIn('corrupted', str(context.exception).lower())
        self.assertIn('json', str(context.exception).lower())
    
    def test_load_missing_required_field(self):
        """Test loading session with missing required field raises ValueError."""
        from wifite.util.session import SessionManager
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with missing 'targets' field
        session_data = {
            'session_id': 'incomplete_session',
            'created_at': 1234567890.0,
            'updated_at': 1234567890.0,
            'config': {}
            # Missing 'targets' field
        }
        
        session_path = os.path.join(self.temp_dir, 'incomplete_session.json')
        with open(session_path, 'w') as f:
            json.dump(session_data, f)
        
        with self.assertRaises(ValueError) as context:
            session_mgr.load_session('incomplete_session')
        
        self.assertIn('missing', str(context.exception).lower())
    
    def test_load_invalid_timestamp(self):
        """Test loading session with invalid timestamp raises ValueError."""
        from wifite.util.session import SessionManager
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with invalid timestamp
        session_data = {
            'session_id': 'invalid_timestamp_session',
            'created_at': -1,  # Invalid negative timestamp
            'updated_at': 1234567890.0,
            'config': {},
            'targets': [{
                'bssid': 'AA:BB:CC:DD:EE:FF',
                'essid': 'Test',
                'channel': 6,
                'encryption': 'WPA2',
                'power': 50,
                'wps': False,
                'status': 'pending',
                'attempts': 0,
                'last_attempt': None
            }]
        }
        
        session_path = os.path.join(self.temp_dir, 'invalid_timestamp_session.json')
        with open(session_path, 'w') as f:
            json.dump(session_data, f)
        
        with self.assertRaises(ValueError) as context:
            session_mgr.load_session('invalid_timestamp_session')
        
        self.assertIn('timestamp', str(context.exception).lower())
    
    def test_load_empty_targets(self):
        """Test loading session with no targets raises ValueError."""
        from wifite.util.session import SessionManager
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with empty targets list
        session_data = {
            'session_id': 'empty_targets_session',
            'created_at': 1234567890.0,
            'updated_at': 1234567890.0,
            'config': {},
            'targets': []  # Empty targets
        }
        
        session_path = os.path.join(self.temp_dir, 'empty_targets_session.json')
        with open(session_path, 'w') as f:
            json.dump(session_data, f)
        
        with self.assertRaises(ValueError) as context:
            session_mgr.load_session('empty_targets_session')
        
        self.assertIn('no targets', str(context.exception).lower())
    
    def test_load_invalid_bssid_format(self):
        """Test loading session with invalid BSSID format raises ValueError."""
        from wifite.util.session import SessionManager
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with invalid BSSID
        session_data = {
            'session_id': 'invalid_bssid_session',
            'created_at': 1234567890.0,
            'updated_at': 1234567890.0,
            'config': {},
            'targets': [{
                'bssid': 'INVALID',  # Invalid BSSID format
                'essid': 'Test',
                'channel': 6,
                'encryption': 'WPA2',
                'power': 50,
                'wps': False,
                'status': 'pending',
                'attempts': 0,
                'last_attempt': None
            }]
        }
        
        session_path = os.path.join(self.temp_dir, 'invalid_bssid_session.json')
        with open(session_path, 'w') as f:
            json.dump(session_data, f)
        
        with self.assertRaises(ValueError) as context:
            session_mgr.load_session('invalid_bssid_session')
        
        self.assertIn('bssid', str(context.exception).lower())
    
    def test_load_invalid_status(self):
        """Test loading session with invalid target status raises ValueError."""
        from wifite.util.session import SessionManager
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with invalid status
        session_data = {
            'session_id': 'invalid_status_session',
            'created_at': 1234567890.0,
            'updated_at': 1234567890.0,
            'config': {},
            'targets': [{
                'bssid': 'AA:BB:CC:DD:EE:FF',
                'essid': 'Test',
                'channel': 6,
                'encryption': 'WPA2',
                'power': 50,
                'wps': False,
                'status': 'invalid_status',  # Invalid status
                'attempts': 0,
                'last_attempt': None
            }]
        }
        
        session_path = os.path.join(self.temp_dir, 'invalid_status_session.json')
        with open(session_path, 'w') as f:
            json.dump(session_data, f)
        
        with self.assertRaises(ValueError) as context:
            session_mgr.load_session('invalid_status_session')
        
        self.assertIn('status', str(context.exception).lower())
    
    def test_load_session_id_mismatch(self):
        """Test loading session with mismatched session ID raises ValueError."""
        from wifite.util.session import SessionManager
        
        session_mgr = SessionManager(session_dir=self.temp_dir)
        
        # Create session with mismatched ID
        session_data = {
            'session_id': 'different_id',  # Different from filename
            'created_at': 1234567890.0,
            'updated_at': 1234567890.0,
            'config': {},
            'targets': [{
                'bssid': 'AA:BB:CC:DD:EE:FF',
                'essid': 'Test',
                'channel': 6,
                'encryption': 'WPA2',
                'power': 50,
                'wps': False,
                'status': 'pending',
                'attempts': 0,
                'last_attempt': None
            }]
        }
        
        session_path = os.path.join(self.temp_dir, 'mismatch_session.json')
        with open(session_path, 'w') as f:
            json.dump(session_data, f)
        
        with self.assertRaises(ValueError) as context:
            session_mgr.load_session('mismatch_session')
        
        self.assertIn('mismatch', str(context.exception).lower())


if __name__ == '__main__':
    unittest.main()
