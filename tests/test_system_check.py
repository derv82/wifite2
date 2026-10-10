#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the comprehensive --syscheck system check module."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wifite.util.system_check import (
    SystemCheck, CheckStatus, CheckResult, InterfaceCheckResult,
    ToolCheckResult, run_system_check,
)


class TestCheckStatus(unittest.TestCase):
    """Test CheckStatus enum values."""

    def test_all_statuses_exist(self):
        self.assertEqual(CheckStatus.PASS.value, 'PASS')
        self.assertEqual(CheckStatus.WARN.value, 'WARN')
        self.assertEqual(CheckStatus.FAIL.value, 'FAIL')
        self.assertEqual(CheckStatus.SKIP.value, 'SKIP')
        self.assertEqual(CheckStatus.INFO.value, 'INFO')


class TestCheckResult(unittest.TestCase):
    """Test CheckResult dataclass."""

    def test_basic_creation(self):
        r = CheckResult('Test', CheckStatus.PASS, 'All good')
        self.assertEqual(r.name, 'Test')
        self.assertEqual(r.status, CheckStatus.PASS)
        self.assertEqual(r.message, 'All good')
        self.assertIsNone(r.details)
        self.assertIsNone(r.fix_hint)

    def test_with_details(self):
        r = CheckResult('Test', CheckStatus.FAIL, 'Bad', details='reason', fix_hint='do X')
        self.assertEqual(r.details, 'reason')
        self.assertEqual(r.fix_hint, 'do X')


class TestToolCheckResult(unittest.TestCase):
    """Test ToolCheckResult dataclass."""

    def test_defaults(self):
        t = ToolCheckResult(name='aircrack-ng', found=True)
        self.assertTrue(t.found)
        self.assertTrue(t.version_ok)
        self.assertFalse(t.required)
        self.assertIsNone(t.path)
        self.assertIsNone(t.version)
        self.assertIsNone(t.native_alt)


class TestInterfaceCheckResult(unittest.TestCase):
    """Test InterfaceCheckResult dataclass."""

    def test_defaults(self):
        i = InterfaceCheckResult(name='wlan0')
        self.assertEqual(i.name, 'wlan0')
        self.assertEqual(i.phy, 'unknown')
        self.assertEqual(i.driver, 'unknown')
        self.assertFalse(i.supports_monitor)
        self.assertFalse(i.supports_ap)
        self.assertFalse(i.supports_injection)
        self.assertIsNone(i.monitor_tested)
        self.assertEqual(i.channels_24, [])
        self.assertEqual(i.channels_5, [])


class TestSystemCheckEnvironment(unittest.TestCase):
    """Test environment checks."""

    def setUp(self):
        self.checker = SystemCheck(verbose=0)

    @patch('os.getuid', return_value=0)
    @patch('os.name', 'posix')
    @patch('os.uname')
    @patch('os.path.exists')
    @patch('os.path.isdir', return_value=True)
    @patch('shutil.which', return_value=None)  # no rfkill
    @patch('subprocess.run')
    def test_environment_basic(self, mock_run, mock_isdir, mock_exists, mock_uname,
                                mock_name, mock_uid):
        mock_uname.return_value = MagicMock(sysname='Linux', release='6.1.0', nodename='test')
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='')

        results = self.checker.check_environment()

        # Should have multiple results
        self.assertGreater(len(results), 0)

        # Root check should pass
        root_checks = [r for r in results if r.name == 'Root privileges']
        self.assertEqual(len(root_checks), 1)
        self.assertEqual(root_checks[0].status, CheckStatus.PASS)

        # OS check should pass
        os_checks = [r for r in results if r.name == 'Operating system']
        self.assertEqual(len(os_checks), 1)
        self.assertEqual(os_checks[0].status, CheckStatus.PASS)

    @patch('os.getuid', return_value=1000)
    @patch('os.name', 'posix')
    @patch('os.uname')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.isdir', return_value=True)
    @patch('shutil.which', return_value=None)
    @patch('subprocess.run')
    def test_non_root_fails(self, mock_run, mock_which, mock_isdir, mock_exists,
                             mock_uname, mock_uid):
        mock_uname.return_value = MagicMock(sysname='Linux', release='6.1.0')
        mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='')

        results = self.checker.check_environment()
        root_checks = [r for r in results if r.name == 'Root privileges']
        self.assertEqual(root_checks[0].status, CheckStatus.FAIL)


class TestSystemCheckTools(unittest.TestCase):
    """Test tool dependency checks."""

    def setUp(self):
        self.checker = SystemCheck(verbose=0)

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_tool_found_with_version(self, mock_run, mock_which):
        mock_which.return_value = '/usr/bin/aircrack-ng'
        mock_run.return_value = MagicMock(
            stdout='Aircrack-ng 1.7', stderr='', returncode=0
        )

        results = self.checker.check_tools()

        # Find aircrack-ng result
        aircrack = next((t for t in results if t.name == 'aircrack-ng'), None)
        self.assertIsNotNone(aircrack)
        self.assertTrue(aircrack.found)
        self.assertEqual(aircrack.version, '1.7')
        self.assertTrue(aircrack.version_ok)

    @patch('shutil.which')
    def test_required_tool_missing(self, mock_which):
        mock_which.return_value = None

        results = self.checker.check_tools()

        # aircrack-ng should be marked as missing and required
        aircrack = next((t for t in results if t.name == 'aircrack-ng'), None)
        self.assertIsNotNone(aircrack)
        self.assertFalse(aircrack.found)
        self.assertTrue(aircrack.required)

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_version_too_old(self, mock_run, mock_which):
        mock_which.return_value = '/usr/bin/hcxdumptool'
        mock_run.return_value = MagicMock(
            stdout='hcxdumptool 5.1.0', stderr='', returncode=0
        )

        results = self.checker.check_tools()
        hcx = next((t for t in results if t.name == 'hcxdumptool'), None)
        self.assertIsNotNone(hcx)
        self.assertTrue(hcx.found)
        self.assertEqual(hcx.version, '5.1.0')
        self.assertFalse(hcx.version_ok)  # Needs >= 6.2.0

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_all_categories_present(self, mock_run, mock_which):
        mock_which.return_value = '/usr/bin/test'
        mock_run.return_value = MagicMock(stdout='1.0.0', stderr='', returncode=0)

        results = self.checker.check_tools()
        categories = set(t.category for t in results)
        # Should have at least core, wps, cracking, wpa3, eviltwin
        self.assertIn('core', categories)
        self.assertIn('wps', categories)
        self.assertIn('cracking', categories)
        self.assertIn('wpa3', categories)
        self.assertIn('eviltwin', categories)


class TestSystemCheckInterfaces(unittest.TestCase):
    """Test wireless interface checks."""

    def setUp(self):
        self.checker = SystemCheck(verbose=0)

    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('subprocess.run')
    @patch('wifite.tools.iw.Iw.get_interfaces', return_value=[])
    def test_no_interfaces(self, mock_iw, mock_run, mock_isdir, mock_listdir):
        mock_listdir.return_value = ['lo', 'eth0']
        mock_isdir.return_value = False  # no /wireless subdir

        results = self.checker.check_interfaces()
        self.assertEqual(len(results), 0)

    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.readlink')
    @patch('builtins.open', create=True)
    @patch('subprocess.run')
    def test_interface_detected(self, mock_run, mock_open, mock_readlink,
                                 mock_isdir, mock_listdir):
        # /sys/class/net lists wlan0 with wireless subdir
        mock_listdir.return_value = ['lo', 'wlan0']

        def isdir_side(path):
            return 'wireless' in path and 'wlan0' in path

        mock_isdir.side_effect = isdir_side

        # iw dev wlan0 info
        mock_run.return_value = MagicMock(
            stdout='Interface wlan0\n\twiphy 0\n\ttype managed\n',
            stderr='', returncode=0
        )

        # Driver from sysfs
        mock_readlink.return_value = '/sys/bus/pci/drivers/ath9k'

        # MAC from sysfs
        from unittest.mock import mock_open as mo
        mock_open.side_effect = [
            mo(read_data='aa:bb:cc:dd:ee:ff\n')(),
            mo(read_data='up\n')(),
        ]

        results = self.checker.check_interfaces()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, 'wlan0')
        self.assertEqual(results[0].driver, 'ath9k')


class TestAttackReadiness(unittest.TestCase):
    """Test attack readiness assessment."""

    def test_all_ready(self):
        checker = SystemCheck()

        # Simulate a fully equipped system
        checker.interface_results = [
            InterfaceCheckResult(name='wlan0', supports_monitor=True,
                                 supports_ap=True, supports_injection=True),
            InterfaceCheckResult(name='wlan1', supports_monitor=True,
                                 supports_ap=True, supports_injection=True),
        ]
        checker.tool_results = [
            ToolCheckResult(name='aircrack-ng', found=True, version='1.7',
                            version_ok=True, required=True, category='core'),
            ToolCheckResult(name='reaver', found=True, version='1.6.6',
                            version_ok=True, category='wps'),
            ToolCheckResult(name='hashcat', found=True, version='6.2.6',
                            version_ok=True, category='cracking'),
            ToolCheckResult(name='hcxdumptool', found=True, version='6.3.0',
                            version_ok=True, category='wpa3'),
            ToolCheckResult(name='hcxpcapngtool', found=True, version='6.3.0',
                            version_ok=True, category='wpa3'),
            ToolCheckResult(name='hostapd', found=True, version='2.10',
                            version_ok=True, category='eviltwin'),
            ToolCheckResult(name='dnsmasq', found=True, version='2.89',
                            version_ok=True, category='eviltwin'),
            ToolCheckResult(name='tshark', found=True, version='4.0.0',
                            version_ok=True, category='inspection'),
        ]

        readiness = checker.assess_attack_readiness()

        self.assertEqual(readiness['WPA Handshake'], CheckStatus.PASS)
        self.assertEqual(readiness['WPA Crack'], CheckStatus.PASS)
        self.assertEqual(readiness['WEP Attack'], CheckStatus.PASS)
        self.assertEqual(readiness['WPS Attack'], CheckStatus.PASS)
        self.assertEqual(readiness['PMKID Capture'], CheckStatus.PASS)
        self.assertEqual(readiness['WPA3/SAE'], CheckStatus.PASS)
        self.assertEqual(readiness['Evil Twin'], CheckStatus.PASS)
        self.assertEqual(readiness['Attack Monitor'], CheckStatus.PASS)

    def test_no_interfaces_all_fail(self):
        checker = SystemCheck()
        checker.interface_results = []
        checker.tool_results = [
            ToolCheckResult(name='aircrack-ng', found=True, version='1.7',
                            version_ok=True, required=True, category='core'),
        ]

        readiness = checker.assess_attack_readiness()

        self.assertEqual(readiness['WPA Handshake'], CheckStatus.FAIL)
        self.assertEqual(readiness['WEP Attack'], CheckStatus.FAIL)
        self.assertEqual(readiness['Evil Twin'], CheckStatus.FAIL)

    def test_partial_tools(self):
        checker = SystemCheck()
        checker.interface_results = [
            InterfaceCheckResult(name='wlan0', supports_monitor=True,
                                 supports_ap=False, supports_injection=True),
        ]
        checker.tool_results = [
            ToolCheckResult(name='aircrack-ng', found=True, version='1.7',
                            version_ok=True, required=True, category='core'),
            ToolCheckResult(name='reaver', found=False, category='wps'),
            ToolCheckResult(name='bully', found=False, category='wps'),
            ToolCheckResult(name='hcxdumptool', found=False, category='wpa3'),
            ToolCheckResult(name='hcxpcapngtool', found=False, category='wpa3'),
            ToolCheckResult(name='hostapd', found=False, category='eviltwin'),
            ToolCheckResult(name='dnsmasq', found=False, category='eviltwin'),
            ToolCheckResult(name='hashcat', found=False, category='cracking'),
            ToolCheckResult(name='tshark', found=False, category='inspection'),
        ]

        readiness = checker.assess_attack_readiness()

        # WPA should be ready (aircrack found + monitor)
        self.assertEqual(readiness['WPA Handshake'], CheckStatus.PASS)
        # WPS should be partial (no reaver/bully)
        self.assertEqual(readiness['WPS Attack'], CheckStatus.WARN)
        # Evil Twin should fail (no AP, no hostapd)
        self.assertEqual(readiness['Evil Twin'], CheckStatus.FAIL)
        # WPA3 should be partial (no hcxdumptool)
        self.assertEqual(readiness['WPA3/SAE'], CheckStatus.WARN)


class TestStatusIcon(unittest.TestCase):
    """Test status icon rendering."""

    def test_all_icons(self):
        for status in CheckStatus:
            icon = SystemCheck._status_icon(status)
            # Should be a non-empty string with color codes
            self.assertIsInstance(icon, str)
            self.assertGreater(len(icon), 0)


class TestRenderReport(unittest.TestCase):
    """Test that render_report doesn't crash with various data states."""

    @patch('wifite.util.color.Color.pl')
    def test_render_empty(self, mock_pl):
        checker = SystemCheck()
        checker.env_results = []
        checker.tool_results = []
        checker.interface_results = []
        checker.attack_readiness = {}
        # Should not raise
        checker.render_report()

    @patch('wifite.util.color.Color.pl')
    def test_render_with_data(self, mock_pl):
        checker = SystemCheck()
        checker.env_results = [
            CheckResult('Test', CheckStatus.PASS, 'OK'),
        ]
        checker.tool_results = [
            ToolCheckResult(name='iw', found=True, version='5.19',
                            version_ok=True, required=True, category='core'),
        ]
        checker.interface_results = [
            InterfaceCheckResult(name='wlan0', supports_monitor=True,
                                 bands_24ghz=True, channels_24=[1, 6, 11]),
        ]
        checker.attack_readiness = {
            'WPA Handshake': CheckStatus.PASS,
        }
        # Should not raise
        checker.render_report()
        self.assertTrue(mock_pl.called)


class TestRunSystemCheck(unittest.TestCase):
    """Test the top-level run_system_check entry point."""

    @patch.object(SystemCheck, 'render_report')
    @patch.object(SystemCheck, 'run_all')
    def test_entry_point(self, mock_run, mock_render):
        run_system_check(verbose=0, smoke_test=False)
        mock_run.assert_called_once()
        mock_render.assert_called_once()


if __name__ == '__main__':
    unittest.main()
