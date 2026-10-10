#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for resume information display.
"""

import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch, call
from wifite.util.session import SessionManager, SessionState, TargetState


class TestResumeDisplay(unittest.TestCase):
    """Test resume information display functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_mgr = SessionManager(session_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_session_progress_summary(self):
        """Test that session progress summary contains all required fields."""
        # Create a session with mixed target states
        session = SessionState(
            session_id='test_session_20250126_120000',
            created_at=1737891600.0,
            updated_at=1737895200.0,
            config={
                'interface': 'wlan0mon',
                'wordlist': '/usr/share/wordlists/rockyou.txt',
                'wpa_attack_timeout': 500,
                'wps_pixie': True,
                'wps_pin': True,
                'use_pmkid': True,
                'wps_only': False,
                'use_pmkid_only': False,
                'infinite_mode': False,
                'attack_max': 0
            },
            targets=[
                TargetState(
                    bssid='AA:BB:CC:DD:EE:01',
                    essid='Network1',
                    channel=6,
                    encryption='WPA2',
                    power=50,
                    wps=True,
                    status='completed'
                ),
                TargetState(
                    bssid='AA:BB:CC:DD:EE:02',
                    essid='Network2',
                    channel=11,
                    encryption='WPA2',
                    power=45,
                    wps=False,
                    status='completed'
                ),
                TargetState(
                    bssid='AA:BB:CC:DD:EE:03',
                    essid='Network3',
                    channel=1,
                    encryption='WPA2',
                    power=40,
                    wps=False,
                    status='failed'
                ),
                TargetState(
                    bssid='AA:BB:CC:DD:EE:04',
                    essid='Network4',
                    channel=6,
                    encryption='WPA2',
                    power=55,
                    wps=True,
                    status='pending'
                ),
                TargetState(
                    bssid='AA:BB:CC:DD:EE:05',
                    essid='Network5',
                    channel=11,
                    encryption='WPA2',
                    power=60,
                    wps=False,
                    status='pending'
                )
            ],
            completed_targets=['AA:BB:CC:DD:EE:01', 'AA:BB:CC:DD:EE:02'],
            failed_targets={'AA:BB:CC:DD:EE:03': 'No handshake captured'}
        )
        
        # Get progress summary
        summary = session.get_progress_summary()
        
        # Verify all required fields are present
        self.assertIn('total', summary)
        self.assertIn('completed', summary)
        self.assertIn('failed', summary)
        self.assertIn('remaining', summary)
        self.assertIn('progress_percent', summary)
        self.assertIn('created_at', summary)
        self.assertIn('updated_at', summary)
        self.assertIn('age_hours', summary)
        
        # Verify values
        self.assertEqual(summary['total'], 5)
        self.assertEqual(summary['completed'], 2)
        self.assertEqual(summary['failed'], 1)
        self.assertEqual(summary['remaining'], 2)
        self.assertEqual(summary['progress_percent'], 40.0)  # 2/5 * 100
        
        # Verify timestamps are formatted
        self.assertIsInstance(summary['created_at'], str)
        self.assertIsInstance(summary['updated_at'], str)
        self.assertIsInstance(summary['age_hours'], float)
    
    def test_session_list_metadata(self):
        """Test that session listing includes all required metadata."""
        # Create multiple sessions
        session1 = SessionState(
            session_id='session_20250126_100000',
            created_at=1737885600.0,
            updated_at=1737889200.0,
            config={'interface': 'wlan0mon'},
            targets=[
                TargetState(
                    bssid='AA:BB:CC:DD:EE:01',
                    essid='Network1',
                    channel=6,
                    encryption='WPA2',
                    power=50,
                    wps=False
                ),
                TargetState(
                    bssid='AA:BB:CC:DD:EE:02',
                    essid='Network2',
                    channel=11,
                    encryption='WPA2',
                    power=45,
                    wps=False
                )
            ],
            completed_targets=['AA:BB:CC:DD:EE:01']
        )
        
        session2 = SessionState(
            session_id='session_20250126_110000',
            created_at=1737889200.0,
            updated_at=1737892800.0,
            config={'interface': 'wlan0mon'},
            targets=[
                TargetState(
                    bssid='AA:BB:CC:DD:EE:03',
                    essid='Network3',
                    channel=1,
                    encryption='WPA2',
                    power=40,
                    wps=False
                )
            ]
        )
        
        # Save sessions
        self.session_mgr.save_session(session1)
        self.session_mgr.save_session(session2)
        
        # List sessions
        sessions = self.session_mgr.list_sessions()
        
        # Should have 2 sessions
        self.assertEqual(len(sessions), 2)
        
        # Verify metadata for each session
        for session_info in sessions:
            self.assertIn('session_id', session_info)
            self.assertIn('created_at', session_info)
            self.assertIn('updated_at', session_info)
            self.assertIn('total_targets', session_info)
            self.assertIn('completed', session_info)
            self.assertIn('failed', session_info)
            self.assertIn('remaining', session_info)
            self.assertIn('progress_percent', session_info)
            self.assertIn('age_hours', session_info)
        
        # Verify sessions are sorted by creation time (newest first)
        self.assertEqual(sessions[0]['session_id'], 'session_20250126_110000')
        self.assertEqual(sessions[1]['session_id'], 'session_20250126_100000')
    
    def test_configuration_display_fields(self):
        """Test that configuration contains displayable fields."""
        session = SessionState(
            session_id='test_session',
            created_at=1737891600.0,
            updated_at=1737895200.0,
            config={
                'interface': 'wlan0mon',
                'wordlist': '/usr/share/wordlists/rockyou.txt',
                'wpa_attack_timeout': 600,
                'wps_pixie': True,
                'wps_pin': True,
                'use_pmkid': True,
                'wps_only': False,
                'use_pmkid_only': False,
                'infinite_mode': True,
                'attack_max': 0,
                'use_tui': True,
                'verbose': 2
            },
            targets=[
                TargetState(
                    bssid='AA:BB:CC:DD:EE:FF',
                    essid='TestNetwork',
                    channel=6,
                    encryption='WPA2',
                    power=50,
                    wps=False
                )
            ]
        )
        
        config = session.config
        
        # Verify all important configuration fields are present
        self.assertIn('interface', config)
        self.assertIn('wordlist', config)
        self.assertIn('wpa_attack_timeout', config)
        self.assertIn('wps_pixie', config)
        self.assertIn('wps_pin', config)
        self.assertIn('use_pmkid', config)
        self.assertIn('infinite_mode', config)
        
        # Verify values
        self.assertEqual(config['interface'], 'wlan0mon')
        self.assertEqual(config['wordlist'], '/usr/share/wordlists/rockyou.txt')
        self.assertEqual(config['wpa_attack_timeout'], 600)
        self.assertTrue(config['wps_pixie'])
        self.assertTrue(config['wps_pin'])
        self.assertTrue(config['use_pmkid'])
        self.assertTrue(config['infinite_mode'])
    
    def test_empty_session_progress(self):
        """Test progress summary with no targets."""
        session = SessionState(
            session_id='empty_session',
            created_at=1737891600.0,
            updated_at=1737895200.0,
            config={},
            targets=[]
        )
        
        summary = session.get_progress_summary()
        
        # Should handle empty targets gracefully
        self.assertEqual(summary['total'], 0)
        self.assertEqual(summary['completed'], 0)
        self.assertEqual(summary['failed'], 0)
        self.assertEqual(summary['remaining'], 0)
        self.assertEqual(summary['progress_percent'], 0)
    
    def test_all_targets_completed_progress(self):
        """Test progress summary when all targets are completed."""
        session = SessionState(
            session_id='completed_session',
            created_at=1737891600.0,
            updated_at=1737895200.0,
            config={},
            targets=[
                TargetState(
                    bssid='AA:BB:CC:DD:EE:01',
                    essid='Network1',
                    channel=6,
                    encryption='WPA2',
                    power=50,
                    wps=False,
                    status='completed'
                ),
                TargetState(
                    bssid='AA:BB:CC:DD:EE:02',
                    essid='Network2',
                    channel=11,
                    encryption='WPA2',
                    power=45,
                    wps=False,
                    status='completed'
                )
            ],
            completed_targets=['AA:BB:CC:DD:EE:01', 'AA:BB:CC:DD:EE:02']
        )
        
        summary = session.get_progress_summary()
        
        # All targets completed
        self.assertEqual(summary['total'], 2)
        self.assertEqual(summary['completed'], 2)
        self.assertEqual(summary['failed'], 0)
        self.assertEqual(summary['remaining'], 0)
        self.assertEqual(summary['progress_percent'], 100.0)


if __name__ == '__main__':
    unittest.main()
