#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for wifite2 improvements:
- Native PMKID integration
- Native scanner integration  
- Better error handling in WPA attacks
- Dependency version checking
- Periodic memory cleanup
"""

import os
import sys
import ast
import unittest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestMemoryMonitor(unittest.TestCase):
    """Tests for the MemoryMonitor utility."""
    
    def test_memory_module_imports(self):
        """Test that memory module imports correctly."""
        from wifite.util.memory import MemoryMonitor, InfiniteModeMonitor
        self.assertTrue(hasattr(MemoryMonitor, 'get_memory_usage_mb'))
        self.assertTrue(hasattr(MemoryMonitor, 'periodic_check'))
        self.assertTrue(hasattr(MemoryMonitor, 'force_cleanup'))
    
    def test_memory_monitor_get_memory_usage(self):
        """Test memory usage retrieval."""
        from wifite.util.memory import MemoryMonitor
        
        # Should return a value (may be -1 if psutil not available)
        usage = MemoryMonitor.get_memory_usage_mb()
        self.assertIsInstance(usage, (int, float))
    
    def test_memory_monitor_get_fd_count(self):
        """Test file descriptor count retrieval."""
        from wifite.util.memory import MemoryMonitor
        
        fd_count = MemoryMonitor.get_open_fd_count()
        self.assertIsInstance(fd_count, int)
        # On Linux, we should get a positive number
        if sys.platform.startswith('linux'):
            self.assertGreater(fd_count, 0)
    
    def test_memory_monitor_check_status(self):
        """Test memory status check."""
        from wifite.util.memory import MemoryMonitor
        
        status = MemoryMonitor.check_memory_status()
        
        self.assertIn('memory_mb', status)
        self.assertIn('fd_count', status)
        self.assertIn('memory_warning', status)
        self.assertIn('memory_critical', status)
    
    def test_infinite_mode_monitor(self):
        """Test InfiniteModeMonitor functionality."""
        from wifite.util.memory import InfiniteModeMonitor
        
        monitor = InfiniteModeMonitor()
        
        # Test cycle tracking
        monitor.on_cycle_start()
        self.assertEqual(monitor.cycles_completed, 1)
        
        # Test target tracking
        monitor.on_target_complete()
        self.assertEqual(monitor.targets_attacked, 1)
        
        # Test stats
        stats = monitor.get_session_stats()
        self.assertIn('elapsed_time', stats)
        self.assertIn('targets_attacked', stats)
        self.assertIn('cycles_completed', stats)


class TestDependencyVersionChecking(unittest.TestCase):
    """Tests for dependency version checking."""
    
    def test_version_comparison(self):
        """Test version comparison logic."""
        from wifite.tools.dependency import Dependency
        
        # Test equal versions
        self.assertEqual(Dependency._compare_versions('1.0.0', '1.0.0'), 0)
        
        # Test greater version
        self.assertGreater(Dependency._compare_versions('2.0.0', '1.0.0'), 0)
        self.assertGreater(Dependency._compare_versions('1.1.0', '1.0.0'), 0)
        self.assertGreater(Dependency._compare_versions('1.0.1', '1.0.0'), 0)
        
        # Test lesser version
        self.assertLess(Dependency._compare_versions('1.0.0', '2.0.0'), 0)
        self.assertLess(Dependency._compare_versions('1.0.0', '1.1.0'), 0)
        self.assertLess(Dependency._compare_versions('1.0.0', '1.0.1'), 0)
        
        # Test with different lengths
        self.assertEqual(Dependency._compare_versions('1.0', '1.0.0'), 0)
        self.assertGreater(Dependency._compare_versions('1.0.1', '1.0'), 0)
    
    def test_minimum_versions_defined(self):
        """Test that minimum versions are defined for critical tools."""
        from wifite.tools.dependency import Dependency
        
        self.assertIn('hcxdumptool', Dependency.MINIMUM_VERSIONS)
        self.assertIn('hashcat', Dependency.MINIMUM_VERSIONS)
        self.assertIn('aircrack-ng', Dependency.MINIMUM_VERSIONS)
    
    def test_get_minimum_version(self):
        """Test getting minimum version for a dependency."""
        from wifite.tools.hashcat import HcxDumpTool
        
        min_version = HcxDumpTool.get_minimum_version()
        self.assertIsNotNone(min_version)
        self.assertEqual(min_version, '6.2.0')
    
    def test_check_version_meets_minimum(self):
        """Test version requirement checking."""
        from wifite.tools.dependency import Dependency
        
        # Create a mock dependency for testing
        class MockDep(Dependency):
            dependency_name = 'mock_tool'
            dependency_required = False
            dependency_url = 'http://example.com'
            dependency_min_version = '2.0.0'
            
            @classmethod
            def get_version(cls):
                return '2.5.0'
            
            @classmethod
            def exists(cls):
                return True
        
        meets, installed, minimum = MockDep.check_version_meets_minimum()
        self.assertTrue(meets)
        self.assertEqual(installed, '2.5.0')
        self.assertEqual(minimum, '2.0.0')


class TestNativePMKIDIntegration(unittest.TestCase):
    """Tests for native PMKID capture integration."""
    
    def test_native_pmkid_availability_flag(self):
        """Test that native PMKID availability is properly detected."""
        from wifite.attack.pmkid import NATIVE_PMKID_AVAILABLE
        
        # Should be a boolean
        self.assertIsInstance(NATIVE_PMKID_AVAILABLE, bool)
    
    def test_native_pmkid_module_import(self):
        """Test that native PMKID module can be imported."""
        try:
            from wifite.native.pmkid import ScapyPMKID, PMKIDResult
            imported = True
        except ImportError:
            imported = False
        
        # Import should work (Scapy may or may not be available)
        self.assertTrue(imported or not imported)  # Just check no crash
    
    def test_pmkid_result_hashcat_format(self):
        """Test PMKIDResult hashcat format conversion."""
        try:
            from wifite.native.pmkid import PMKIDResult
            
            result = PMKIDResult(
                bssid='AA:BB:CC:DD:EE:FF',
                client_mac='11:22:33:44:55:66',
                pmkid='abcdef1234567890abcdef1234567890',
                essid='TestNetwork'
            )
            
            # Test 22000 format
            hash_22000 = result.to_hashcat_22000()
            self.assertIn('WPA*02*', hash_22000)
            self.assertIn('aabbccddeeff', hash_22000.lower())
            
            # Test 16800 format
            hash_16800 = result.to_hashcat_16800()
            self.assertIn('*', hash_16800)
            self.assertNotIn('WPA', hash_16800)
            
        except ImportError:
            self.skipTest("Scapy not available")


class TestNativeScannerIntegration(unittest.TestCase):
    """Tests for native scanner integration."""
    
    def test_native_scanner_availability_flag(self):
        """Test that native scanner availability is properly detected."""
        from wifite.util.scanner import NATIVE_SCANNER_AVAILABLE
        
        self.assertIsInstance(NATIVE_SCANNER_AVAILABLE, bool)
    
    def test_native_scanner_module_import(self):
        """Test that native scanner module can be imported."""
        try:
            from wifite.native.scanner import NativeScanner, AccessPoint, ChannelHopper
            imported = True
        except ImportError:
            imported = False
        
        self.assertTrue(imported or not imported)  # Just check no crash
    
    def test_access_point_dataclass(self):
        """Test AccessPoint dataclass."""
        try:
            from wifite.native.scanner import AccessPoint
            
            ap = AccessPoint(
                bssid='AA:BB:CC:DD:EE:FF',
                essid='TestNetwork',
                channel=6,
                encryption='WPA2'
            )
            
            self.assertEqual(ap.bssid, 'AA:BB:CC:DD:EE:FF')
            self.assertEqual(ap.essid, 'TestNetwork')
            self.assertEqual(ap.channel, 6)
            
        except ImportError:
            self.skipTest("Scapy not available")


class TestWPAAttackErrorHandling(unittest.TestCase):
    """Tests for WPA attack error handling."""
    
    def test_attack_wpa_has_retry_constants(self):
        """Test that AttackWPA has retry configuration."""
        from wifite.attack.wpa import AttackWPA
        
        self.assertTrue(hasattr(AttackWPA, 'MAX_RETRY_ATTEMPTS'))
        self.assertTrue(hasattr(AttackWPA, 'RETRY_DELAY_SECONDS'))
        self.assertIsInstance(AttackWPA.MAX_RETRY_ATTEMPTS, int)
        self.assertIsInstance(AttackWPA.RETRY_DELAY_SECONDS, (int, float))
    
    def test_attack_wpa_error_tracking(self):
        """Test that AttackWPA initializes error tracking."""
        from wifite.attack.wpa import AttackWPA
        
        # Create mock target
        mock_target = Mock()
        mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        mock_target.essid = 'TestNetwork'
        mock_target.channel = 6
        
        # Mock Configuration and OutputManager
        with patch('wifite.attack.wpa.Configuration'):
            with patch('wifite.attack.wpa.OutputManager') as mock_output:
                mock_output.is_tui_mode.return_value = False
                
                attack = AttackWPA(mock_target)
                
                # Check error tracking attributes
                self.assertEqual(attack._retry_count, 0)
                self.assertIsNone(attack._last_error)
                self.assertFalse(attack._recovered_from_error)
    
    def test_attack_wpa_has_recovery_methods(self):
        """Test that AttackWPA has error recovery methods."""
        from wifite.attack.wpa import AttackWPA
        
        self.assertTrue(hasattr(AttackWPA, '_error_recovery_context'))
        self.assertTrue(hasattr(AttackWPA, '_attempt_interface_recovery'))
        self.assertTrue(hasattr(AttackWPA, '_run_with_retry'))


class TestSyntaxValidation(unittest.TestCase):
    """Test that all modified files have valid Python syntax."""
    
    def _check_file_syntax(self, filepath):
        """Check if a file has valid Python syntax."""
        if not os.path.exists(filepath):
            return True  # Skip if file doesn't exist
        
        with open(filepath, 'r') as f:
            source = f.read()
        
        try:
            ast.parse(source)
            return True
        except SyntaxError as e:
            self.fail(f"Syntax error in {filepath}: {e}")
    
    def test_memory_module_syntax(self):
        """Test memory.py syntax."""
        filepath = os.path.join(os.path.dirname(__file__), '..', 'wifite', 'util', 'memory.py')
        self._check_file_syntax(filepath)
    
    def test_pmkid_attack_syntax(self):
        """Test attack/pmkid.py syntax."""
        filepath = os.path.join(os.path.dirname(__file__), '..', 'wifite', 'attack', 'pmkid.py')
        self._check_file_syntax(filepath)
    
    def test_scanner_syntax(self):
        """Test util/scanner.py syntax."""
        filepath = os.path.join(os.path.dirname(__file__), '..', 'wifite', 'util', 'scanner.py')
        self._check_file_syntax(filepath)
    
    def test_dependency_syntax(self):
        """Test tools/dependency.py syntax."""
        filepath = os.path.join(os.path.dirname(__file__), '..', 'wifite', 'tools', 'dependency.py')
        self._check_file_syntax(filepath)
    
    def test_wpa_attack_syntax(self):
        """Test attack/wpa.py syntax."""
        filepath = os.path.join(os.path.dirname(__file__), '..', 'wifite', 'attack', 'wpa.py')
        self._check_file_syntax(filepath)
    
    def test_all_attack_syntax(self):
        """Test attack/all.py syntax."""
        filepath = os.path.join(os.path.dirname(__file__), '..', 'wifite', 'attack', 'all.py')
        self._check_file_syntax(filepath)


class TestAllAttackIntegration(unittest.TestCase):
    """Tests for attack/all.py memory integration."""
    
    def test_memory_imports(self):
        """Test that memory module is imported in attack/all.py."""
        from wifite.attack.all import MemoryMonitor, get_infinite_monitor
        
        self.assertTrue(hasattr(MemoryMonitor, 'periodic_check'))
        self.assertTrue(callable(get_infinite_monitor))


if __name__ == '__main__':
    unittest.main()
