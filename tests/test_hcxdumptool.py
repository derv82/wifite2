#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, '..')

from wifite.tools.hcxdumptool import HcxDumpTool, HcxDumpToolPassive
from wifite.config import Configuration

pytestmark = pytest.mark.timeout(30)


class TestHcxDumpToolMultiInterface(unittest.TestCase):
    """Test suite for HcxDumpTool multi-interface support"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration to avoid argument parsing issues
        Configuration.interface = None

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    def test_single_interface_string(self, mock_config_init):
        """Test single interface initialization with string (backward compatibility)"""
        tool = HcxDumpTool(interface='wlan0', output_file='/tmp/test.pcapng')
        
        # Should store as list internally
        self.assertEqual(tool.interfaces, ['wlan0'])
        # Should maintain backward compatibility with single interface attribute
        self.assertEqual(tool.interface, 'wlan0')

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    def test_dual_interface_list(self, mock_config_init):
        """Test dual interface initialization with list"""
        tool = HcxDumpTool(interface=['wlan0', 'wlan1'], output_file='/tmp/test.pcapng')
        
        # Should store both interfaces
        self.assertEqual(tool.interfaces, ['wlan0', 'wlan1'])
        # First interface should be primary
        self.assertEqual(tool.interface, 'wlan0')

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    def test_triple_interface_list(self, mock_config_init):
        """Test triple interface initialization with list"""
        tool = HcxDumpTool(interface=['wlan0', 'wlan1', 'wlan2'], output_file='/tmp/test.pcapng')
        
        # Should store all three interfaces
        self.assertEqual(tool.interfaces, ['wlan0', 'wlan1', 'wlan2'])
        # First interface should be primary
        self.assertEqual(tool.interface, 'wlan0')

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    def test_empty_list_raises_error(self, mock_config_init):
        """Test that empty interface list raises ValueError"""
        with self.assertRaises(ValueError) as context:
            HcxDumpTool(interface=[], output_file='/tmp/test.pcapng')
        
        self.assertIn('cannot be empty', str(context.exception))

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    def test_invalid_type_raises_error(self, mock_config_init):
        """Test that invalid interface parameter type raises ValueError"""
        with self.assertRaises(ValueError) as context:
            HcxDumpTool(interface=123, output_file='/tmp/test.pcapng')
        
        self.assertIn('must be a string or list', str(context.exception))

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    def test_none_interface_uses_config(self, mock_config_init):
        """Test that None interface uses Configuration.interface"""
        Configuration.interface = 'wlan0'
        tool = HcxDumpTool(interface=None, output_file='/tmp/test.pcapng')
        
        self.assertEqual(tool.interfaces, ['wlan0'])
        self.assertEqual(tool.interface, 'wlan0')

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    def test_none_interface_no_config_raises_error(self, mock_config_init):
        """Test that None interface with no config raises error"""
        Configuration.interface = None
        
        with self.assertRaises(Exception) as context:
            HcxDumpTool(interface=None, output_file='/tmp/test.pcapng')
        
        self.assertIn('must be defined', str(context.exception))

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    @patch('wifite.tools.hcxdumptool.Process')
    @patch('wifite.tools.hcxdumptool.time.sleep')
    @patch('wifite.tools.hcxdumptool.os.kill')
    def test_command_building_single_interface(self, mock_kill, mock_sleep, mock_process, mock_config_init):
        """Test command building with single interface"""
        mock_proc_instance = MagicMock()
        mock_proc_instance.pid.pid = 12345
        mock_proc_instance.poll.return_value = None
        mock_process.return_value = mock_proc_instance
        
        tool = HcxDumpTool(interface='wlan0', channel=6, output_file='/tmp/test.pcapng')
        
        with tool:
            # Get the command that was passed to Process
            call_args = mock_process.call_args[0][0]
            
            # Should have single -i flag
            self.assertIn('-i', call_args)
            i_index = call_args.index('-i')
            self.assertEqual(call_args[i_index + 1], 'wlan0')
            
            # Should have output file (-w flag for hcxdumptool 7.x)
            self.assertIn('-w', call_args)
            w_index = call_args.index('-w')
            self.assertEqual(call_args[w_index + 1], '/tmp/test.pcapng')
            
            # Should have channel (with band suffix for hcxdumptool 7.x: '6a' for 2.4GHz)
            self.assertIn('-c', call_args)
            c_index = call_args.index('-c')
            self.assertEqual(call_args[c_index + 1], '6a')

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    @patch('wifite.tools.hcxdumptool.Process')
    @patch('wifite.tools.hcxdumptool.time.sleep')
    @patch('wifite.tools.hcxdumptool.os.kill')
    def test_command_building_dual_interface(self, mock_kill, mock_sleep, mock_process, mock_config_init):
        """Test command building with dual interfaces"""
        mock_proc_instance = MagicMock()
        mock_proc_instance.pid.pid = 12345
        mock_proc_instance.poll.return_value = None
        mock_process.return_value = mock_proc_instance
        
        tool = HcxDumpTool(interface=['wlan0', 'wlan1'], channel=6, output_file='/tmp/test.pcapng')
        
        with tool:
            # Get the command that was passed to Process
            call_args = mock_process.call_args[0][0]
            
            # Should have -i flags for both interfaces
            self.assertIn('-i', call_args)
            i_indices = [i for i, x in enumerate(call_args) if x == '-i']
            self.assertEqual(len(i_indices), 2, f'Expected 2 -i flags, got {len(i_indices)} in {call_args}')
            
            # Both interfaces should be present
            self.assertEqual(call_args[i_indices[0] + 1], 'wlan0')
            self.assertEqual(call_args[i_indices[1] + 1], 'wlan1')
            
            # Should have output file (-w flag for hcxdumptool 7.x)
            self.assertIn('-w', call_args)

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    @patch('wifite.tools.hcxdumptool.Process')
    @patch('wifite.tools.hcxdumptool.time.sleep')
    @patch('wifite.tools.hcxdumptool.os.kill')
    def test_command_building_triple_interface(self, mock_kill, mock_sleep, mock_process, mock_config_init):
        """Test command building with triple interfaces"""
        mock_proc_instance = MagicMock()
        mock_proc_instance.pid.pid = 12345
        mock_proc_instance.poll.return_value = None
        mock_process.return_value = mock_proc_instance
        
        tool = HcxDumpTool(interface=['wlan0', 'wlan1', 'wlan2'], output_file='/tmp/test.pcapng')
        
        with tool:
            # Get the command that was passed to Process
            call_args = mock_process.call_args[0][0]
            
            # Should have -i flags for all three interfaces
            i_indices = [i for i, x in enumerate(call_args) if x == '-i']
            self.assertEqual(len(i_indices), 3, f'Expected 3 -i flags, got {len(i_indices)} in {call_args}')
            
            # All interfaces should be present in order
            self.assertEqual(call_args[i_indices[0] + 1], 'wlan0')
            self.assertEqual(call_args[i_indices[1] + 1], 'wlan1')
            self.assertEqual(call_args[i_indices[2] + 1], 'wlan2')


class TestHcxDumpToolPassive(unittest.TestCase):
    """Test suite for HcxDumpToolPassive class"""

    def setUp(self):
        """Set up test fixtures"""
        Configuration.interface = None

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    def test_initialization_with_interface(self, mock_config_init):
        """Test initialization with explicit interface"""
        tool = HcxDumpToolPassive(interface='wlan0', output_file='/tmp/passive.pcapng')
        
        self.assertEqual(tool.interface, 'wlan0')
        self.assertEqual(tool.output_file, '/tmp/passive.pcapng')
        self.assertIsNone(tool.pid)
        self.assertIsNone(tool.proc)

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    @patch('wifite.tools.hcxdumptool.Configuration.temp')
    def test_initialization_with_defaults(self, mock_temp, mock_config_init):
        """Test initialization with default output file"""
        mock_temp.return_value = '/tmp/wifite_'
        Configuration.interface = 'wlan0'

        tool = HcxDumpToolPassive()

        self.assertEqual(tool.interface, 'wlan0')
        self.assertEqual(tool.output_file, '/tmp/wifite_/passive_pmkid.pcapng')

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    def test_initialization_no_interface_raises_error(self, mock_config_init):
        """Test that missing interface raises exception"""
        Configuration.interface = None
        
        with self.assertRaises(Exception) as context:
            HcxDumpToolPassive()
        
        self.assertIn('must be defined', str(context.exception))

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    @patch('wifite.tools.hcxdumptool.Process')
    @patch('wifite.tools.hcxdumptool.time.sleep')
    def test_enter_starts_process(self, mock_sleep, mock_process, mock_config_init):
        """Test that __enter__ starts hcxdumptool with correct flags"""
        mock_proc_instance = MagicMock()
        mock_proc_instance.pid.pid = 12345
        mock_proc_instance.poll.return_value = None
        mock_process.return_value = mock_proc_instance
        
        tool = HcxDumpToolPassive(interface='wlan0', output_file='/tmp/passive.pcapng')
        
        with tool:
            # Verify Process was called
            mock_process.assert_called_once()
            
            # Get the command that was passed to Process
            call_args = mock_process.call_args[0][0]
            
            # Verify command structure
            self.assertEqual(call_args[0], 'hcxdumptool')
            self.assertIn('-i', call_args)
            self.assertIn('wlan0', call_args)
            self.assertIn('-w', call_args)
            self.assertIn('/tmp/passive.pcapng', call_args)

            # Verify PID was set
            self.assertEqual(tool.pid, 12345)
            self.assertIsNotNone(tool.proc)

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    @patch('wifite.tools.hcxdumptool.Process')
    @patch('wifite.tools.hcxdumptool.time.sleep')
    def test_is_running_when_active(self, mock_sleep, mock_process, mock_config_init):
        """Test is_running returns True when process is active"""
        mock_proc_instance = MagicMock()
        mock_proc_instance.pid.pid = 12345
        mock_proc_instance.poll.return_value = None  # Process is running
        mock_process.return_value = mock_proc_instance
        
        tool = HcxDumpToolPassive(interface='wlan0', output_file='/tmp/passive.pcapng')
        
        with tool:
            self.assertTrue(tool.is_running())

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    @patch('wifite.tools.hcxdumptool.Process')
    @patch('wifite.tools.hcxdumptool.time.sleep')
    def test_is_running_when_stopped(self, mock_sleep, mock_process, mock_config_init):
        """Test is_running returns False when process has stopped"""
        mock_proc_instance = MagicMock()
        mock_proc_instance.pid.pid = 12345
        mock_proc_instance.poll.return_value = 0  # Process has exited
        mock_process.return_value = mock_proc_instance
        
        tool = HcxDumpToolPassive(interface='wlan0', output_file='/tmp/passive.pcapng')
        
        with tool:
            self.assertFalse(tool.is_running())

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    @patch('wifite.tools.hcxdumptool.os.path.exists')
    @patch('wifite.tools.hcxdumptool.os.path.getsize')
    def test_get_capture_size_file_exists(self, mock_getsize, mock_exists, mock_config_init):
        """Test get_capture_size returns file size when file exists"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024000  # 1MB
        
        tool = HcxDumpToolPassive(interface='wlan0', output_file='/tmp/passive.pcapng')
        
        size = tool.get_capture_size()
        self.assertEqual(size, 1024000)
        mock_exists.assert_called_once_with('/tmp/passive.pcapng')
        mock_getsize.assert_called_once_with('/tmp/passive.pcapng')

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    @patch('wifite.tools.hcxdumptool.os.path.exists')
    def test_get_capture_size_file_not_exists(self, mock_exists, mock_config_init):
        """Test get_capture_size returns 0 when file doesn't exist"""
        mock_exists.return_value = False
        
        tool = HcxDumpToolPassive(interface='wlan0', output_file='/tmp/passive.pcapng')
        
        size = tool.get_capture_size()
        self.assertEqual(size, 0)
        mock_exists.assert_called_once_with('/tmp/passive.pcapng')

    @patch('wifite.tools.hcxdumptool.Configuration.initialize')
    @patch('wifite.tools.hcxdumptool.Process')
    @patch('wifite.tools.hcxdumptool.time.sleep')
    @patch('wifite.tools.hcxdumptool.os.kill')
    def test_exit_stops_process(self, mock_kill, mock_sleep, mock_process, mock_config_init):
        """Test that __exit__ stops the process gracefully"""
        mock_proc_instance = MagicMock()
        mock_proc_instance.pid.pid = 12345
        mock_proc_instance.poll.return_value = None  # Process is running
        mock_process.return_value = mock_proc_instance
        
        tool = HcxDumpToolPassive(interface='wlan0', output_file='/tmp/passive.pcapng')
        
        with tool:
            pass  # Exit the context
        
        # Verify interrupt was called
        mock_proc_instance.interrupt.assert_called_once()


if __name__ == '__main__':
    unittest.main()
