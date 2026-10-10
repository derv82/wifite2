#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for client monitoring and statistics tracking.
"""

import unittest
import time
import tempfile
import os
from wifite.util.client_monitor import ClientConnection, ClientMonitor, AttackStatistics


class TestClientConnection(unittest.TestCase):
    """Test ClientConnection data model."""
    
    def test_client_connection_creation(self):
        """Test creating a ClientConnection."""
        client = ClientConnection(mac_address="AA:BB:CC:DD:EE:FF")
        
        self.assertEqual(client.mac_address, "AA:BB:CC:DD:EE:FF")
        self.assertIsNone(client.ip_address)
        self.assertIsNone(client.hostname)
        self.assertTrue(client.is_connected())
        self.assertFalse(client.credential_submitted)
        self.assertIsNone(client.credential_valid)
    
    def test_client_connection_with_details(self):
        """Test ClientConnection with IP and hostname."""
        client = ClientConnection(
            mac_address="AA:BB:CC:DD:EE:FF",
            ip_address="192.168.100.10",
            hostname="test-device"
        )
        
        self.assertEqual(client.ip_address, "192.168.100.10")
        self.assertEqual(client.hostname, "test-device")
    
    def test_client_disconnection(self):
        """Test client disconnection."""
        client = ClientConnection(mac_address="AA:BB:CC:DD:EE:FF")
        self.assertTrue(client.is_connected())
        
        client.disconnect_time = time.time()
        self.assertFalse(client.is_connected())
    
    def test_connection_duration(self):
        """Test connection duration calculation."""
        client = ClientConnection(mac_address="AA:BB:CC:DD:EE:FF")
        time.sleep(0.1)
        
        duration = client.connection_duration()
        self.assertGreater(duration, 0.09)
        self.assertLess(duration, 0.5)


class TestAttackStatistics(unittest.TestCase):
    """Test AttackStatistics tracking."""
    
    def test_statistics_creation(self):
        """Test creating AttackStatistics."""
        stats = AttackStatistics()
        
        self.assertEqual(stats.total_clients_connected, 0)
        self.assertEqual(stats.total_credential_attempts, 0)
        self.assertEqual(stats.get_unique_client_count(), 0)
        self.assertEqual(stats.get_success_rate(), 0.0)
    
    def test_record_client_connect(self):
        """Test recording client connections."""
        stats = AttackStatistics()
        
        stats.record_client_connect("AA:BB:CC:DD:EE:FF")
        self.assertEqual(stats.total_clients_connected, 1)
        self.assertEqual(stats.currently_connected, 1)
        self.assertEqual(stats.get_unique_client_count(), 1)
        
        # Same client connects again
        stats.record_client_connect("AA:BB:CC:DD:EE:FF")
        self.assertEqual(stats.total_clients_connected, 2)
        self.assertEqual(stats.get_unique_client_count(), 1)
        
        # Different client connects
        stats.record_client_connect("11:22:33:44:55:66")
        self.assertEqual(stats.total_clients_connected, 3)
        self.assertEqual(stats.get_unique_client_count(), 2)
    
    def test_record_client_disconnect(self):
        """Test recording client disconnections."""
        stats = AttackStatistics()
        
        stats.record_client_connect("AA:BB:CC:DD:EE:FF")
        self.assertEqual(stats.currently_connected, 1)
        
        stats.record_client_disconnect("AA:BB:CC:DD:EE:FF")
        self.assertEqual(stats.currently_connected, 0)
    
    def test_record_credential_attempts(self):
        """Test recording credential attempts."""
        stats = AttackStatistics()
        
        # Failed attempt
        stats.record_credential_attempt(success=False)
        self.assertEqual(stats.total_credential_attempts, 1)
        self.assertEqual(stats.failed_attempts, 1)
        self.assertEqual(stats.successful_attempts, 0)
        self.assertEqual(stats.get_success_rate(), 0.0)
        
        # Successful attempt
        stats.record_credential_attempt(success=True)
        self.assertEqual(stats.total_credential_attempts, 2)
        self.assertEqual(stats.successful_attempts, 1)
        self.assertEqual(stats.get_success_rate(), 50.0)
        
        # Another successful attempt
        stats.record_credential_attempt(success=True)
        self.assertEqual(stats.total_credential_attempts, 3)
        self.assertEqual(stats.successful_attempts, 2)
        self.assertAlmostEqual(stats.get_success_rate(), 66.67, places=1)
    
    def test_timing_statistics(self):
        """Test timing statistics."""
        stats = AttackStatistics()
        
        # Initially no timing data
        self.assertIsNone(stats.get_time_to_first_client())
        self.assertIsNone(stats.get_time_to_first_credential())
        self.assertIsNone(stats.get_time_to_success())
        
        # Record client connection
        time.sleep(0.1)
        stats.record_client_connect("AA:BB:CC:DD:EE:FF")
        self.assertIsNotNone(stats.get_time_to_first_client())
        self.assertGreater(stats.get_time_to_first_client(), 0.09)
        
        # Record credential attempt
        time.sleep(0.1)
        stats.record_credential_attempt(success=True)
        self.assertIsNotNone(stats.get_time_to_first_credential())
        self.assertIsNotNone(stats.get_time_to_success())
    
    def test_duration_calculation(self):
        """Test attack duration calculation."""
        stats = AttackStatistics()
        
        time.sleep(0.1)
        duration = stats.get_duration()
        self.assertGreater(duration, 0.09)
        self.assertLess(duration, 0.5)
        
        # Mark complete
        stats.mark_complete()
        duration_after = stats.get_duration()
        self.assertGreaterEqual(duration_after, duration)
    
    def test_to_dict(self):
        """Test converting statistics to dictionary."""
        stats = AttackStatistics()
        stats.record_client_connect("AA:BB:CC:DD:EE:FF")
        stats.record_credential_attempt(success=True)
        
        data = stats.to_dict()
        
        self.assertIn('duration', data)
        self.assertIn('total_clients', data)
        self.assertIn('unique_clients', data)
        self.assertIn('credential_attempts', data)
        self.assertIn('success_rate', data)
        
        self.assertEqual(data['total_clients'], 1)
        self.assertEqual(data['unique_clients'], 1)
        self.assertEqual(data['credential_attempts'], 1)
        self.assertEqual(data['success_rate'], 100.0)


class TestClientMonitor(unittest.TestCase):
    """Test ClientMonitor functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitors = []
    
    def tearDown(self):
        """Clean up monitors after each test."""
        for monitor in self.monitors:
            if monitor.running:
                monitor.stop()
        self.monitors = []
    
    def test_monitor_creation(self):
        """Test creating a ClientMonitor."""
        monitor = ClientMonitor()
        self.monitors.append(monitor)
        
        self.assertIsNotNone(monitor.statistics)
        self.assertEqual(len(monitor.clients), 0)
        self.assertFalse(monitor.running)
    
    def test_get_statistics(self):
        """Test getting statistics from monitor."""
        monitor = ClientMonitor()
        self.monitors.append(monitor)
        
        stats = monitor.get_statistics()
        self.assertIsInstance(stats, AttackStatistics)
        self.assertEqual(stats.total_clients_connected, 0)
    
    def test_record_credential_attempt(self):
        """Test recording credential attempts through monitor."""
        monitor = ClientMonitor()
        self.monitors.append(monitor)
        
        # Add a client first
        monitor._handle_client_connect("AA:BB:CC:DD:EE:FF")
        
        # Record credential attempt
        monitor.record_credential_attempt("AA:BB:CC:DD:EE:FF", success=True)
        
        stats = monitor.get_statistics()
        self.assertEqual(stats.total_credential_attempts, 1)
        self.assertEqual(stats.successful_attempts, 1)
        
        # Check client record
        client = monitor.get_client("AA:BB:CC:DD:EE:FF")
        self.assertTrue(client.credential_submitted)
        self.assertTrue(client.credential_valid)
    
    def test_get_detailed_stats(self):
        """Test getting detailed statistics."""
        monitor = ClientMonitor()
        self.monitors.append(monitor)
        
        # Add clients and credentials
        monitor._handle_client_connect("AA:BB:CC:DD:EE:FF")
        monitor.record_credential_attempt("AA:BB:CC:DD:EE:FF", success=True)
        
        stats = monitor.get_detailed_stats()
        
        self.assertIn('duration', stats)
        self.assertIn('total_clients', stats)
        self.assertIn('credential_attempts', stats)
        self.assertIn('clients_submitted_credentials', stats)
        self.assertIn('clients_valid_credentials', stats)
        
        self.assertEqual(stats['clients_submitted_credentials'], 1)
        self.assertEqual(stats['clients_valid_credentials'], 1)


if __name__ == '__main__':
    unittest.main()
