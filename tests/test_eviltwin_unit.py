#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for Evil Twin attack components.

Tests core functionality of hostapd, dnsmasq, portal templates, and credential validation.
"""

import unittest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

import pytest

from wifite.tools.hostapd import Hostapd
from wifite.tools.dnsmasq import Dnsmasq
from wifite.attack.portal.templates import TemplateRenderer, get_available_templates
from wifite.util.credential_validator import CredentialValidator

pytestmark = pytest.mark.timeout(30)


class TestHostapdConfiguration(unittest.TestCase):
    """Test hostapd configuration generation."""
    
    def test_hostapd_initialization(self):
        """Test hostapd initialization with parameters."""
        hostapd = Hostapd('wlan0', 'TestNetwork', 6, 'testpassword')
        
        self.assertEqual(hostapd.interface, 'wlan0')
        self.assertEqual(hostapd.ssid, 'TestNetwork')
        self.assertEqual(hostapd.channel, 6)
        self.assertEqual(hostapd.password, 'testpassword')
        self.assertFalse(hostapd.running)
    
    def test_hostapd_open_network_when_no_password(self):
        """With no password, the AP must be OPEN (captive portal requirement)."""
        hostapd = Hostapd('wlan0', 'TestNetwork', 6)

        # No passphrase is stored, and the generated config must not enable WPA2
        # (otherwise clients couldn't associate to reach the portal).
        self.assertIsNone(hostapd.password)
        config = hostapd.generate_config()
        self.assertNotIn('wpa=2', config)
        self.assertNotIn('wpa_passphrase', config)
        self.assertIn('auth_algs=1', config)
    
    def test_hostapd_config_generation(self):
        """Test hostapd configuration file generation."""
        hostapd = Hostapd('wlan1', 'MyNetwork', 11, 'mypassword123')
        config = hostapd.generate_config()
        
        # Check required fields are present
        self.assertIn('interface=wlan1', config)
        self.assertIn('ssid=MyNetwork', config)
        self.assertIn('channel=11', config)
        self.assertIn('wpa_passphrase=mypassword123', config)
        
        # Check security settings
        self.assertIn('wpa=2', config)
        self.assertIn('wpa_key_mgmt=WPA-PSK', config)
        self.assertIn('rsn_pairwise=CCMP', config)
        
        # Check basic settings
        self.assertIn('driver=nl80211', config)
        self.assertIn('hw_mode=g', config)
        self.assertIn('auth_algs=1', config)
    
    def test_hostapd_config_special_characters(self):
        """Test hostapd handles special characters in SSID."""
        hostapd = Hostapd('wlan0', 'Test Network 2.4GHz', 6, 'pass123')
        config = hostapd.generate_config()

        self.assertIn('ssid=Test Network 2.4GHz', config)

    def test_hostapd_ssid_newline_injection_neutralized(self):
        """A newline in the SSID must not inject hostapd directives."""
        # Malicious SSID attempting to append a directive on a new config line.
        malicious = 'Evil\nmacaddr_acl=1\nctrl_interface=/tmp/x'
        hostapd = Hostapd('wlan0', malicious, 6, 'pass123')
        config = hostapd.generate_config()

        # The injected directives must NOT appear as standalone config lines.
        lines = config.split('\n')
        self.assertNotIn('ctrl_interface=/tmp/x', lines)
        # The SSID line must be hex-encoded (ssid2=) rather than a raw ssid=.
        self.assertTrue(any(line.startswith('ssid2=') for line in lines))
        self.assertFalse(any(line.startswith('ssid=Evil') for line in lines))

    def test_hostapd_ssid_non_ascii_hex_encoded(self):
        """Non-ASCII SSIDs are emitted as ssid2=<hex> (hostapd-safe)."""
        hostapd = Hostapd('wlan0', 'Café📶', 6, 'pass123')
        config = hostapd.generate_config()
        lines = config.split('\n')
        self.assertTrue(any(line.startswith('ssid2=') for line in lines))
    
    def test_hostapd_config_file_creation(self):
        """Test hostapd creates configuration file."""
        hostapd = Hostapd('wlan0', 'TestNet', 6, 'password')
        
        try:
            config_file = hostapd.create_config_file()
            
            # Check file exists
            self.assertTrue(os.path.exists(config_file))
            
            # Check file content
            with open(config_file, 'r') as f:
                content = f.read()
            
            self.assertIn('interface=wlan0', content)
            self.assertIn('ssid=TestNet', content)
            
            # Cleanup
            if os.path.exists(config_file):
                os.remove(config_file)
        finally:
            hostapd.config_file = None


class TestDnsmasqConfiguration(unittest.TestCase):
    """Test dnsmasq configuration generation."""
    
    def test_dnsmasq_initialization(self):
        """Test dnsmasq initialization with parameters."""
        dnsmasq = Dnsmasq('wlan0', '192.168.100.1', '192.168.100.10', '192.168.100.100')
        
        self.assertEqual(dnsmasq.interface, 'wlan0')
        self.assertEqual(dnsmasq.gateway_ip, '192.168.100.1')
        self.assertEqual(dnsmasq.dhcp_range_start, '192.168.100.10')
        self.assertEqual(dnsmasq.dhcp_range_end, '192.168.100.100')
        self.assertEqual(dnsmasq.portal_ip, '192.168.100.1')
        self.assertFalse(dnsmasq.running)
    
    def test_dnsmasq_custom_portal_ip(self):
        """Test dnsmasq with custom portal IP."""
        dnsmasq = Dnsmasq('wlan0', '192.168.100.1', portal_ip='192.168.100.5')
        
        self.assertEqual(dnsmasq.portal_ip, '192.168.100.5')
    
    def test_dnsmasq_config_generation(self):
        """Test dnsmasq configuration file generation."""
        dnsmasq = Dnsmasq('wlan1', '10.0.0.1', '10.0.0.10', '10.0.0.50', '10.0.0.1')
        config = dnsmasq.generate_config()
        
        # Check required fields
        self.assertIn('interface=wlan1', config)
        self.assertIn('dhcp-range=10.0.0.10,10.0.0.50,12h', config)
        
        # Check DHCP options
        self.assertIn('dhcp-option=3,10.0.0.1', config)  # Gateway
        self.assertIn('dhcp-option=6,10.0.0.1', config)  # DNS
        
        # Check DNS redirection
        self.assertIn('address=/#/10.0.0.1', config)
        
        # Check settings
        self.assertIn('no-resolv', config)
        self.assertIn('dhcp-authoritative', config)
        self.assertIn('log-queries', config)
        self.assertIn('log-dhcp', config)
    
    def test_dnsmasq_config_file_creation(self):
        """Test dnsmasq creates configuration and lease files."""
        dnsmasq = Dnsmasq('wlan0', '192.168.100.1')
        
        try:
            config_file = dnsmasq.create_config_file()
            
            # Check config file exists
            self.assertTrue(os.path.exists(config_file))
            
            # Check lease file exists
            self.assertIsNotNone(dnsmasq.lease_file)
            self.assertTrue(os.path.exists(dnsmasq.lease_file))
            
            # Check config content
            with open(config_file, 'r') as f:
                content = f.read()
            
            self.assertIn('interface=wlan0', content)
            self.assertIn('dhcp-range=', content)
            
            # Cleanup
            if os.path.exists(config_file):
                os.remove(config_file)
            if dnsmasq.lease_file and os.path.exists(dnsmasq.lease_file):
                os.remove(dnsmasq.lease_file)
        finally:
            dnsmasq.config_file = None
            dnsmasq.lease_file = None


class TestPortalTemplates(unittest.TestCase):
    """Test captive portal template rendering."""
    
    def test_template_renderer_initialization(self):
        """Test template renderer initialization."""
        renderer = TemplateRenderer('generic', 'TestNetwork')
        
        self.assertEqual(renderer.template_name, 'generic')
        self.assertEqual(renderer.target_ssid, 'TestNetwork')
    
    def test_available_templates(self):
        """Test getting list of available templates."""
        templates = get_available_templates()
        
        self.assertIn('generic', templates)
        self.assertIn('tplink', templates)
        self.assertIn('netgear', templates)
        self.assertIn('linksys', templates)
    
    def test_generic_template_rendering(self):
        """Test generic template rendering."""
        renderer = TemplateRenderer('generic', 'MyNetwork')
        html = renderer.render_login()
        
        # Check HTML structure
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('<html>', html)
        self.assertIn('</html>', html)
        
        # Check form elements
        self.assertIn('<form', html)
        self.assertIn('method="POST"', html)
        self.assertIn('action="/submit"', html)
        self.assertIn('name="ssid"', html)
        self.assertIn('name="password"', html)
        
        # Check SSID substitution
        self.assertIn('MyNetwork', html)
    
    def test_tplink_template_rendering(self):
        """Test TP-Link template rendering."""
        renderer = TemplateRenderer('tplink', 'TPLink_Network')
        html = renderer.render_login()
        
        self.assertIn('TP-Link', html)
        self.assertIn('TPLink_Network', html)
        self.assertIn('<form', html)
    
    def test_netgear_template_rendering(self):
        """Test Netgear template rendering."""
        renderer = TemplateRenderer('netgear', 'NETGEAR_5G')
        html = renderer.render_login()
        
        self.assertIn('NETGEAR', html)
        self.assertIn('NETGEAR_5G', html)
        self.assertIn('<form', html)
    
    def test_linksys_template_rendering(self):
        """Test Linksys template rendering."""
        renderer = TemplateRenderer('linksys', 'Linksys_Home')
        html = renderer.render_login()
        
        self.assertIn('LINKSYS', html)
        self.assertIn('Linksys_Home', html)
        self.assertIn('<form', html)
    
    def test_success_page_rendering(self):
        """Test success page rendering."""
        renderer = TemplateRenderer('generic', 'TestNet')
        html = renderer.render_success()
        
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('Success', html)
        self.assertIn('TestNet', html)
    
    def test_error_page_rendering(self):
        """Test error page rendering."""
        renderer = TemplateRenderer('generic', 'TestNet')
        html = renderer.render_error()
        
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('Failed', html)
        self.assertIn('Try Again', html)
    
    def test_variable_substitution(self):
        """Test variable substitution in templates."""
        custom_vars = {
            'router_name': 'Custom Router',
            'router_model': 'Model XYZ'
        }
        renderer = TemplateRenderer('generic', 'TestSSID', custom_vars)
        
        # Create a simple template with variables
        template = 'Network: {{ssid}}, Router: {{router_name}}, Model: {{router_model}}'
        result = renderer._substitute_variables(template)
        
        self.assertIn('TestSSID', result)
        self.assertIn('Custom Router', result)
        self.assertIn('Model XYZ', result)
    
    def test_template_with_special_characters(self):
        """Test template rendering with special characters in SSID."""
        renderer = TemplateRenderer('generic', 'Test & Network <2.4GHz>')
        html = renderer.render_login()
        
        # SSID should be in the HTML (may be escaped)
        self.assertTrue('Test' in html and 'Network' in html)


class TestCredentialValidator(unittest.TestCase):
    """Test credential validation logic."""
    
    def test_validator_initialization(self):
        """Test credential validator initialization."""
        validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 6)
        
        self.assertEqual(validator.interface, 'wlan0mon')
        self.assertEqual(validator.target_bssid, 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(validator.target_channel, 6)
        self.assertFalse(validator.running)
        self.assertEqual(validator.total_validations, 0)
    
    def test_channel_to_frequency_conversion(self):
        """Test channel to frequency conversion."""
        validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 1)
        
        # Test 2.4 GHz channels
        self.assertEqual(validator._channel_to_freq(1), 2412)
        self.assertEqual(validator._channel_to_freq(6), 2437)
        self.assertEqual(validator._channel_to_freq(11), 2462)
        self.assertEqual(validator._channel_to_freq(14), 2484)
        
        # Test 5 GHz channels
        self.assertEqual(validator._channel_to_freq(36), 5180)
        self.assertEqual(validator._channel_to_freq(149), 5745)
    
    def test_wpa_config_generation(self):
        """Test wpa_supplicant configuration generation."""
        validator = CredentialValidator('wlan0mon', '11:22:33:44:55:66', 6)
        
        try:
            config_file = validator._create_wpa_config('TestNetwork', 'password123')
            
            # Check file exists
            self.assertTrue(os.path.exists(config_file))
            
            # Check content
            with open(config_file, 'r') as f:
                content = f.read()
            
            self.assertIn('ssid="TestNetwork"', content)
            self.assertIn('bssid=11:22:33:44:55:66', content)
            self.assertIn('psk="password123"', content)
            self.assertIn('key_mgmt=WPA-PSK', content)
            self.assertIn('scan_freq=2437', content)  # Channel 6 = 2437 MHz
            
            # Cleanup
            if os.path.exists(config_file):
                os.remove(config_file)
        finally:
            validator.temp_files = []
    
    def test_validation_cache(self):
        """Test credential validation caching."""
        validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 6)
        
        # Cache a result
        validator._cache_result('TestNet', 'password123', True)
        
        # Check cache hit
        result = validator._check_cache('TestNet', 'password123')
        self.assertTrue(result)
        
        # Check cache miss
        result = validator._check_cache('TestNet', 'wrongpassword')
        self.assertIsNone(result)
        
        # Check cache miss for different SSID
        result = validator._check_cache('OtherNet', 'password123')
        self.assertIsNone(result)
    
    def test_validation_statistics(self):
        """Test validation statistics tracking."""
        validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 6)
        
        # Initial stats
        stats = validator.get_statistics()
        self.assertEqual(stats['total_validations'], 0)
        self.assertEqual(stats['successful_validations'], 0)
        self.assertEqual(stats['failed_validations'], 0)
        
        # Simulate validations
        validator.total_validations = 5
        validator.successful_validations = 2
        validator.failed_validations = 3
        validator.cached_results = 1
        
        stats = validator.get_statistics()
        self.assertEqual(stats['total_validations'], 5)
        self.assertEqual(stats['successful_validations'], 2)
        self.assertEqual(stats['failed_validations'], 3)
        self.assertEqual(stats['cached_results'], 1)
    
    def test_rate_limiting_state(self):
        """Test rate limiting state management."""
        validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 6)
        
        # Initial state
        self.assertEqual(validator.backoff_multiplier, 1.0)
        self.assertEqual(validator.consecutive_failures, 0)
        self.assertFalse(validator.is_locked_out)
        
        # Simulate failed validations
        validator._handle_failed_validation()
        self.assertEqual(validator.consecutive_failures, 1)
        
        validator._handle_failed_validation()
        self.assertEqual(validator.consecutive_failures, 2)
        self.assertGreater(validator.backoff_multiplier, 1.0)
        
        # Simulate successful validation
        validator._handle_successful_validation()
        self.assertEqual(validator.backoff_multiplier, 1.0)
        self.assertEqual(validator.consecutive_failures, 0)
    
    def test_lockout_trigger(self):
        """Test AP lockout triggering."""
        validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 6)
        
        # Set failed attempts to threshold
        validator.failed_attempt_count = validator.lockout_threshold
        
        # Trigger lockout
        validator._trigger_lockout()
        
        self.assertTrue(validator.is_locked_out)
        self.assertGreater(validator.lockout_until, 0)
        self.assertEqual(validator.failed_attempt_count, 0)  # Reset after lockout
    
    def test_lockout_check(self):
        """Test lockout period checking."""
        validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 6)
        
        # Not in lockout initially
        self.assertFalse(validator._is_in_lockout())
        
        # Trigger lockout
        validator.is_locked_out = True
        validator.lockout_until = 9999999999  # Far future
        
        self.assertTrue(validator._is_in_lockout())
        
        # Expired lockout
        validator.lockout_until = 0  # Past
        self.assertFalse(validator._is_in_lockout())
    
    def test_cache_clearing(self):
        """Test cache clearing."""
        validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 6)
        
        # Add some cached results
        validator._cache_result('Net1', 'pass1', True)
        validator._cache_result('Net2', 'pass2', False)
        
        self.assertEqual(len(validator.validation_cache), 2)
        
        # Clear cache
        validator.clear_cache()
        
        self.assertEqual(len(validator.validation_cache), 0)


if __name__ == '__main__':
    unittest.main()
