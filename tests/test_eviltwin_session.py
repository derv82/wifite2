#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Evil Twin session management integration.
"""

import unittest
import tempfile
import shutil
import os
from unittest.mock import Mock, MagicMock

from wifite.util.session import (
    SessionManager,
    SessionState,
    TargetState,
    EvilTwinAttackState,
    EvilTwinClientState,
    EvilTwinCredentialAttempt
)


class TestEvilTwinSessionManagement(unittest.TestCase):
    """Test Evil Twin session management functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for session storage
        self.temp_dir = tempfile.mkdtemp()
        self.session_manager = SessionManager(session_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_evil_twin_client_state_serialization(self):
        """Test EvilTwinClientState serialization and deserialization."""
        client = EvilTwinClientState(
            mac_address='AA:BB:CC:DD:EE:FF',
            ip_address='192.168.100.10',
            hostname='test-device',
            connect_time=1234567890.0,
            disconnect_time=None,
            credential_submitted=True,
            credential_valid=False
        )
        
        # Serialize
        data = client.to_dict()
        self.assertEqual(data['mac_address'], 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(data['ip_address'], '192.168.100.10')
        self.assertEqual(data['hostname'], 'test-device')
        
        # Deserialize
        restored = EvilTwinClientState.from_dict(data)
        self.assertEqual(restored.mac_address, client.mac_address)
        self.assertEqual(restored.ip_address, client.ip_address)
        self.assertEqual(restored.hostname, client.hostname)
        self.assertEqual(restored.credential_submitted, client.credential_submitted)
    
    def test_evil_twin_credential_attempt_serialization(self):
        """Test EvilTwinCredentialAttempt serialization and deserialization."""
        attempt = EvilTwinCredentialAttempt(
            mac_address='AA:BB:CC:DD:EE:FF',
            password='testpassword123',
            success=True,
            timestamp=1234567890.0
        )
        
        # Serialize
        data = attempt.to_dict()
        self.assertEqual(data['mac_address'], 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(data['password'], 'testpassword123')
        self.assertTrue(data['success'])
        
        # Deserialize
        restored = EvilTwinCredentialAttempt.from_dict(data)
        self.assertEqual(restored.mac_address, attempt.mac_address)
        self.assertEqual(restored.password, attempt.password)
        self.assertEqual(restored.success, attempt.success)
    
    def test_evil_twin_attack_state_serialization(self):
        """Test EvilTwinAttackState serialization and deserialization."""
        # Create test data
        clients = [
            EvilTwinClientState(
                mac_address='AA:BB:CC:DD:EE:FF',
                ip_address='192.168.100.10',
                connect_time=1234567890.0
            )
        ]
        
        attempts = [
            EvilTwinCredentialAttempt(
                mac_address='AA:BB:CC:DD:EE:FF',
                password='wrongpass',
                success=False,
                timestamp=1234567900.0
            )
        ]
        
        state = EvilTwinAttackState(
            interface_ap='wlan0',
            interface_deauth='wlan1mon',
            portal_template='generic',
            deauth_interval=5,
            attack_phase='running',
            start_time=1234567880.0,
            setup_time=10.5,
            clients=clients,
            credential_attempts=attempts,
            total_clients_connected=1,
            total_credential_attempts=1,
            successful_validations=0
        )
        
        # Serialize
        data = state.to_dict()
        self.assertEqual(data['interface_ap'], 'wlan0')
        self.assertEqual(data['attack_phase'], 'running')
        self.assertEqual(len(data['clients']), 1)
        self.assertEqual(len(data['credential_attempts']), 1)
        
        # Deserialize
        restored = EvilTwinAttackState.from_dict(data)
        self.assertEqual(restored.interface_ap, state.interface_ap)
        self.assertEqual(restored.attack_phase, state.attack_phase)
        self.assertEqual(len(restored.clients), 1)
        self.assertEqual(len(restored.credential_attempts), 1)
        self.assertEqual(restored.clients[0].mac_address, 'AA:BB:CC:DD:EE:FF')
    
    def test_save_and_load_evil_twin_state(self):
        """Test saving and loading Evil Twin state in session."""
        # Create a session
        mock_target = Mock()
        mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        mock_target.essid = 'TestNetwork'
        mock_target.channel = 6
        mock_target.encryption = 'WPA2'
        mock_target.power = -50
        mock_target.wps = False
        
        mock_config = {
            'interface': 'wlan0',
            'wordlist': None
        }
        
        session = self.session_manager.create_session([mock_target], mock_config)
        
        # Create Evil Twin state
        evil_twin_state = EvilTwinAttackState(
            interface_ap='wlan0',
            attack_phase='running',
            start_time=1234567890.0,
            total_clients_connected=2,
            total_credential_attempts=3
        )
        
        # Save Evil Twin state
        self.session_manager.save_evil_twin_state(session, mock_target.bssid, evil_twin_state)
        self.session_manager.save_session(session)
        
        # Load session
        loaded_session = self.session_manager.load_session(session.session_id)
        
        # Load Evil Twin state
        loaded_state = self.session_manager.load_evil_twin_state(loaded_session, mock_target.bssid)
        
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state.interface_ap, 'wlan0')
        self.assertEqual(loaded_state.attack_phase, 'running')
        self.assertEqual(loaded_state.total_clients_connected, 2)
        self.assertEqual(loaded_state.total_credential_attempts, 3)
    
    def test_clear_evil_twin_state(self):
        """Test clearing Evil Twin state from session."""
        # Create a session with Evil Twin state
        mock_target = Mock()
        mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        mock_target.essid = 'TestNetwork'
        mock_target.channel = 6
        mock_target.encryption = 'WPA2'
        mock_target.power = -50
        mock_target.wps = False
        
        session = self.session_manager.create_session([mock_target], {})
        
        evil_twin_state = EvilTwinAttackState(
            interface_ap='wlan0',
            attack_phase='running'
        )
        
        self.session_manager.save_evil_twin_state(session, mock_target.bssid, evil_twin_state)
        
        # Verify state exists
        loaded_state = self.session_manager.load_evil_twin_state(session, mock_target.bssid)
        self.assertIsNotNone(loaded_state)
        
        # Clear state
        self.session_manager.clear_evil_twin_state(session, mock_target.bssid)
        
        # Verify state is cleared
        loaded_state = self.session_manager.load_evil_twin_state(session, mock_target.bssid)
        self.assertIsNone(loaded_state)
    
    def test_handle_partial_evil_twin_completion(self):
        """Test handling partial Evil Twin attack completion."""
        # Create session with partial Evil Twin state
        mock_target = Mock()
        mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        mock_target.essid = 'TestNetwork'
        mock_target.channel = 6
        mock_target.encryption = 'WPA2'
        mock_target.power = -50
        mock_target.wps = False
        
        session = self.session_manager.create_session([mock_target], {})
        
        # Test case 1: No clients connected
        evil_twin_state = EvilTwinAttackState(
            attack_phase='running',
            total_clients_connected=0,
            total_credential_attempts=0
        )
        self.session_manager.save_evil_twin_state(session, mock_target.bssid, evil_twin_state)
        
        result = self.session_manager.handle_partial_evil_twin_completion(session, mock_target.bssid)
        self.assertTrue(result['can_resume'])
        self.assertEqual(result['clients_connected'], 0)
        self.assertEqual(result['credential_attempts'], 0)
        
        # Test case 2: Clients connected, credentials attempted
        evil_twin_state = EvilTwinAttackState(
            attack_phase='running',
            total_clients_connected=3,
            total_credential_attempts=5
        )
        self.session_manager.save_evil_twin_state(session, mock_target.bssid, evil_twin_state)
        
        result = self.session_manager.handle_partial_evil_twin_completion(session, mock_target.bssid)
        self.assertTrue(result['can_resume'])
        self.assertEqual(result['clients_connected'], 3)
        self.assertEqual(result['credential_attempts'], 5)
        
        # Test case 3: Attack completed successfully
        evil_twin_state = EvilTwinAttackState(
            attack_phase='completed',
            total_clients_connected=2,
            total_credential_attempts=3,
            captured_password='testpassword123'
        )
        self.session_manager.save_evil_twin_state(session, mock_target.bssid, evil_twin_state)
        
        result = self.session_manager.handle_partial_evil_twin_completion(session, mock_target.bssid)
        self.assertFalse(result['can_resume'])
        self.assertIn('completed', result['progress'].lower())


if __name__ == '__main__':
    unittest.main()
