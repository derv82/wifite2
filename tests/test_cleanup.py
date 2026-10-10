#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for cleanup utilities.
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wifite.util.cleanup import CleanupManager, kill_orphaned_processes, check_conflicting_processes


class TestCleanupManager(unittest.TestCase):
    """Test CleanupManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cleanup_manager = CleanupManager()
    
    def test_initialization(self):
        """Test CleanupManager initialization."""
        self.assertEqual(len(self.cleanup_manager.cleanup_errors), 0)
        self.assertEqual(len(self.cleanup_manager.processes_to_stop), 0)
        self.assertEqual(len(self.cleanup_manager.temp_files_to_remove), 0)
        self.assertEqual(len(self.cleanup_manager.interfaces_to_restore), 0)
        self.assertEqual(len(self.cleanup_manager.iptables_rules_added), 0)
    
    def test_register_process(self):
        """Test process registration."""
        mock_process = Mock()
        self.cleanup_manager.register_process(mock_process, 'test_process')
        
        self.assertEqual(len(self.cleanup_manager.processes_to_stop), 1)
        self.assertEqual(self.cleanup_manager.processes_to_stop[0], (mock_process, 'test_process'))
    
    def test_register_temp_file(self):
        """Test temp file registration."""
        self.cleanup_manager.register_temp_file('/tmp/test.txt')
        
        self.assertEqual(len(self.cleanup_manager.temp_files_to_remove), 1)
        self.assertIn('/tmp/test.txt', self.cleanup_manager.temp_files_to_remove)
    
    def test_register_temp_file_no_duplicates(self):
        """Test that duplicate temp files are not registered."""
        self.cleanup_manager.register_temp_file('/tmp/test.txt')
        self.cleanup_manager.register_temp_file('/tmp/test.txt')
        
        self.assertEqual(len(self.cleanup_manager.temp_files_to_remove), 1)
    
    def test_register_interface(self):
        """Test interface registration."""
        original_state = {'interface': 'wlan0', 'up': True, 'mode': 'managed'}
        self.cleanup_manager.register_interface('wlan0', original_state)
        
        self.assertEqual(len(self.cleanup_manager.interfaces_to_restore), 1)
        self.assertEqual(self.cleanup_manager.interfaces_to_restore[0], ('wlan0', original_state))
    
    def test_register_iptables_rule(self):
        """Test iptables rule registration."""
        rule = ['-o', 'eth0', '-j', 'MASQUERADE']
        self.cleanup_manager.register_iptables_rule('nat', 'POSTROUTING', rule)
        
        self.assertEqual(len(self.cleanup_manager.iptables_rules_added), 1)
        self.assertEqual(self.cleanup_manager.iptables_rules_added[0], ('nat', 'POSTROUTING', rule))
    
    def test_stop_process_with_stop_method(self):
        """Test stopping a process with stop() method."""
        mock_process = Mock()
        mock_process.stop = Mock()
        
        result = self.cleanup_manager.stop_process(mock_process, 'test_process')
        
        self.assertTrue(result)
        mock_process.stop.assert_called_once()
    
    def test_stop_process_with_cleanup_method(self):
        """Test stopping a process with cleanup() method."""
        mock_process = Mock()
        mock_process.cleanup = Mock()
        del mock_process.stop  # Remove stop method
        
        result = self.cleanup_manager.stop_process(mock_process, 'test_process')
        
        self.assertTrue(result)
        mock_process.cleanup.assert_called_once()
    
    def test_stop_process_none(self):
        """Test stopping None process."""
        result = self.cleanup_manager.stop_process(None, 'test_process')
        self.assertTrue(result)
    
    def test_remove_temp_file(self):
        """Test removing a temporary file."""
        # Create a real temp file
        fd, temp_file = tempfile.mkstemp()
        os.close(fd)
        
        # Verify file exists
        self.assertTrue(os.path.exists(temp_file))
        
        # Remove it
        result = self.cleanup_manager.remove_temp_file(temp_file)
        
        self.assertTrue(result)
        self.assertFalse(os.path.exists(temp_file))
    
    def test_remove_temp_file_nonexistent(self):
        """Test removing a non-existent file."""
        result = self.cleanup_manager.remove_temp_file('/tmp/nonexistent_file_12345.txt')
        self.assertTrue(result)
    
    def test_remove_all_temp_files(self):
        """Test removing all registered temp files."""
        # Create temp files
        temp_files = []
        for i in range(3):
            fd, temp_file = tempfile.mkstemp()
            os.close(fd)
            temp_files.append(temp_file)
            self.cleanup_manager.register_temp_file(temp_file)
        
        # Remove all
        self.cleanup_manager.remove_all_temp_files()
        
        # Verify all removed
        for temp_file in temp_files:
            self.assertFalse(os.path.exists(temp_file))
        
        self.assertEqual(len(self.cleanup_manager.temp_files_to_remove), 0)
    
    def test_get_errors(self):
        """Test getting cleanup errors."""
        self.cleanup_manager.cleanup_errors = ['error1', 'error2']
        errors = self.cleanup_manager.get_errors()
        
        self.assertEqual(len(errors), 2)
        self.assertIn('error1', errors)
        self.assertIn('error2', errors)
    
    @patch('wifite.util.process.subprocess.run')
    def test_remove_iptables_rule(self, mock_run):
        """Test removing an iptables rule."""
        mock_run.return_value = Mock(returncode=0)
        
        rule = ['-o', 'eth0', '-j', 'MASQUERADE']
        result = self.cleanup_manager.remove_iptables_rule('nat', 'POSTROUTING', rule)
        
        self.assertTrue(result)
        mock_run.assert_called_once()
    
    @patch('wifite.util.process.subprocess.run')
    def test_check_conflicting_processes(self, mock_run):
        """Test checking for conflicting processes."""
        # Mock pgrep returning PIDs
        mock_run.return_value = Mock(returncode=0, stdout='1234\n5678\n')
        
        conflicting = check_conflicting_processes()
        
        # Should find some processes
        self.assertIsInstance(conflicting, list)
    
    @patch('wifite.util.process.subprocess.run')
    def test_kill_orphaned_processes(self, mock_run):
        """Test killing orphaned processes."""
        # Mock pgrep returning PIDs
        mock_run.return_value = Mock(returncode=0, stdout='1234\n')
        
        killed = kill_orphaned_processes()
        
        # Should return list of killed processes
        self.assertIsInstance(killed, list)


if __name__ == '__main__':
    unittest.main()
