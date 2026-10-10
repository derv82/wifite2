#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
End-to-end simulation tests for Evil Twin attack.

Tests realistic scenarios including:
- Mock environment simulating real router scenarios
- Portal rendering across different viewport sizes
- Credential validation with various password formats
- Attack lifecycle with simulated network conditions
"""

import unittest
import tempfile
import shutil
import os
import time
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock sys.argv to prevent argparse from reading test arguments
original_argv = sys.argv
sys.argv = ['wifite']

from wifite.config import Configuration

# Set required Configuration attributes before importing other modules
Configuration.wpa_attack_timeout = 600
Configuration.interface = 'wlan0'
Configuration.eviltwin_timeout = 0
Configuration.eviltwin_template = 'generic'
Configuration.eviltwin_deauth_interval = 5

from wifite.attack.eviltwin import EvilTwin, AttackState
from wifite.model.target import Target
from wifite.attack.portal.templates import TemplateRenderer
from wifite.util.credential_validator import CredentialValidator

# Restore original argv
sys.argv = original_argv


class TestRealRouterScenarios(unittest.TestCase):
    """Test scenarios simulating real router environments."""
    
    def setUp(self):
        """Set up test fixtures."""
        Configuration.interface = 'wlan0'
        Configuration.eviltwin_timeout = 0
    
    def test_wpa2_personal_router_scenario(self):
        """Test scenario: WPA2-Personal router with standard settings."""
        # Create target simulating typical home router
        mock_target = Mock(spec=Target)
        mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        mock_target.essid = 'HomeNetwork'
        mock_target.channel = 6
        mock_target.encryption = 'WPA2'
        mock_target.power = -45
        mock_target.wps = False
        
        attack = EvilTwin(mock_target)
        
        # Verify attack configuration matches router
        self.assertEqual(attack.target.essid, 'HomeNetwork')
        self.assertEqual(attack.target.channel, 6)
        self.assertEqual(attack.target.encryption, 'WPA2')
    
    def test_dual_band_router_scenario(self):
        """Test scenario: Dual-band router on 5GHz."""
        mock_target = Mock(spec=Target)
        mock_target.bssid = '11:22:33:44:55:66'
        mock_target.essid = 'MyNetwork_5G'
        mock_target.channel = 36  # 5GHz channel
        mock_target.encryption = 'WPA2'
        mock_target.power = -50
        mock_target.wps = False
        
        attack = EvilTwin(mock_target)
        
        # Verify 5GHz channel handling
        self.assertEqual(attack.target.channel, 36)
        self.assertIn('5G', attack.target.essid)
    
    def test_weak_signal_router_scenario(self):
        """Test scenario: Router with weak signal."""
        mock_target = Mock(spec=Target)
        mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        mock_target.essid = 'WeakSignal'
        mock_target.channel = 11
        mock_target.encryption = 'WPA2'
        mock_target.power = -75  # Weak signal
        mock_target.wps = False
        
        attack = EvilTwin(mock_target)
        
        # Attack should still initialize despite weak signal
        self.assertEqual(attack.target.power, -75)
        self.assertIsNotNone(attack.target)
    
    def test_special_characters_ssid_scenario(self):
        """Test scenario: Router with special characters in SSID."""
        mock_target = Mock(spec=Target)
        mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        mock_target.essid = "Café's WiFi 2.4GHz"
        mock_target.channel = 6
        mock_target.encryption = 'WPA2'
        mock_target.power = -50
        mock_target.wps = False
        
        attack = EvilTwin(mock_target)
        
        # Verify special characters are handled
        self.assertEqual(attack.target.essid, "Café's WiFi 2.4GHz")
    
    def test_hidden_ssid_scenario(self):
        """Test scenario: Router with hidden SSID."""
        mock_target = Mock(spec=Target)
        mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        mock_target.essid = ''  # Hidden SSID
        mock_target.channel = 6
        mock_target.encryption = 'WPA2'
        mock_target.power = -50
        mock_target.wps = False
        
        attack = EvilTwin(mock_target)
        
        # Attack should handle empty SSID
        self.assertEqual(attack.target.essid, '')
    
    @patch('wifite.attack.eviltwin.Color')
    @patch('wifite.attack.eviltwin.input')
    def test_congested_channel_scenario(self, mock_input, mock_color):
        """Test scenario: Router on congested channel."""
        mock_input.return_value = 'YES'
        
        # Simulate congested channel (multiple APs on same channel)
        mock_target = Mock(spec=Target)
        mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        mock_target.essid = 'CongestedNetwork'
        mock_target.channel = 6  # Most congested 2.4GHz channel
        mock_target.encryption = 'WPA2'
        mock_target.power = -50
        mock_target.wps = False
        
        attack = EvilTwin(mock_target)
        
        # Attack should still work on congested channel
        self.assertEqual(attack.target.channel, 6)


class TestPortalViewportRendering(unittest.TestCase):
    """Test portal rendering across different viewport sizes."""
    
    def test_mobile_viewport_rendering(self):
        """Test portal rendering for mobile devices (320-480px)."""
        renderer = TemplateRenderer('generic', 'TestNetwork')
        html = renderer.render_login()
        
        # Check for mobile-friendly meta tags
        self.assertIn('viewport', html.lower())
        
        # Check for responsive design elements
        self.assertIn('<form', html)
        self.assertIn('</form>', html)
        
        # Verify HTML is valid
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('</html>', html)
    
    def test_tablet_viewport_rendering(self):
        """Test portal rendering for tablet devices (768-1024px)."""
        renderer = TemplateRenderer('tplink', 'TabletNetwork')
        html = renderer.render_login()
        
        # Check structure is present
        self.assertIn('<html>', html)
        self.assertIn('</html>', html)
        self.assertIn('<form', html)
        
        # Check SSID is rendered
        self.assertIn('TabletNetwork', html)
    
    def test_desktop_viewport_rendering(self):
        """Test portal rendering for desktop browsers (1920px+)."""
        renderer = TemplateRenderer('netgear', 'DesktopNetwork')
        html = renderer.render_login()
        
        # Check full page structure
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('<head>', html)
        self.assertIn('<body>', html)
        self.assertIn('</body>', html)
        self.assertIn('</html>', html)
    
    def test_all_templates_mobile_compatible(self):
        """Test all templates render properly for mobile."""
        templates = ['generic', 'tplink', 'netgear', 'linksys']
        
        for template_name in templates:
            with self.subTest(template=template_name):
                renderer = TemplateRenderer(template_name, 'MobileTest')
                html = renderer.render_login()
                
                # Basic mobile compatibility checks
                self.assertIn('<!DOCTYPE html>', html)
                self.assertIn('<form', html)
                self.assertIn('name="password"', html)
                self.assertIn('MobileTest', html)
    
    def test_form_elements_responsive(self):
        """Test form elements are properly structured for all viewports."""
        renderer = TemplateRenderer('generic', 'TestNet')
        html = renderer.render_login()
        
        # Check form has proper structure
        self.assertIn('method="POST"', html)
        self.assertIn('action="/submit"', html)
        
        # Check input fields exist
        self.assertIn('name="ssid"', html)
        self.assertIn('name="password"', html)
        
        # Check submit button exists
        self.assertIn('type="submit"', html)
    
    def test_success_page_responsive(self):
        """Test success page renders properly on all viewports."""
        renderer = TemplateRenderer('generic', 'TestNet')
        html = renderer.render_success()
        
        # Check basic structure
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('</html>', html)
        
        # Check success message
        self.assertIn('Success', html)
    
    def test_error_page_responsive(self):
        """Test error page renders properly on all viewports."""
        renderer = TemplateRenderer('generic', 'TestNet')
        html = renderer.render_error()
        
        # Check basic structure
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('</html>', html)
        
        # Check error message and retry option
        self.assertIn('Failed', html)


class TestPasswordFormatValidation(unittest.TestCase):
    """Test credential validation with various password formats."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 6)
    
    def test_standard_alphanumeric_password(self):
        """Test validation with standard alphanumeric password."""
        # Test config generation with standard password
        config_file = self.validator._create_wpa_config('TestNet', 'Password123')
        
        try:
            self.assertTrue(os.path.exists(config_file))
            
            with open(config_file, 'r') as f:
                content = f.read()
            
            self.assertIn('psk="Password123"', content)
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
    
    def test_special_characters_password(self):
        """Test validation with special characters in password."""
        passwords = [
            'Pass@word!123',
            'P@$$w0rd#2024',
            'Test_Pass-123',
            'My.Pass.Word',
        ]
        
        for password in passwords:
            with self.subTest(password=password):
                config_file = self.validator._create_wpa_config('TestNet', password)
                
                try:
                    self.assertTrue(os.path.exists(config_file))
                    
                    with open(config_file, 'r') as f:
                        content = f.read()
                    
                    self.assertIn(f'psk="{password}"', content)
                finally:
                    if os.path.exists(config_file):
                        os.remove(config_file)
    
    def test_unicode_password(self):
        """Test validation with unicode characters in password."""
        passwords = [
            'Café2024',
            'Contraseña123',
            'パスワード',
        ]
        
        for password in passwords:
            with self.subTest(password=password):
                config_file = self.validator._create_wpa_config('TestNet', password)
                
                try:
                    self.assertTrue(os.path.exists(config_file))
                    
                    with open(config_file, 'r') as f:
                        content = f.read()
                    
                    # Password should be in config
                    self.assertIn('psk=', content)
                finally:
                    if os.path.exists(config_file):
                        os.remove(config_file)
    
    def test_minimum_length_password(self):
        """Test validation with minimum length password (8 chars)."""
        password = '12345678'  # Minimum WPA2 password length
        config_file = self.validator._create_wpa_config('TestNet', password)
        
        try:
            self.assertTrue(os.path.exists(config_file))
            
            with open(config_file, 'r') as f:
                content = f.read()
            
            self.assertIn('psk="12345678"', content)
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
    
    def test_maximum_length_password(self):
        """Test validation with maximum length password (63 chars)."""
        password = 'a' * 63  # Maximum WPA2 password length
        config_file = self.validator._create_wpa_config('TestNet', password)
        
        try:
            self.assertTrue(os.path.exists(config_file))
            
            with open(config_file, 'r') as f:
                content = f.read()
            
            self.assertIn(f'psk="{password}"', content)
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
    
    def test_spaces_in_password(self):
        """Test validation with spaces in password."""
        password = 'My Password 123'
        config_file = self.validator._create_wpa_config('TestNet', password)
        
        try:
            self.assertTrue(os.path.exists(config_file))
            
            with open(config_file, 'r') as f:
                content = f.read()
            
            self.assertIn('psk="My Password 123"', content)
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
    
    def test_quotes_in_password(self):
        """Test validation with quotes in password."""
        password = 'Pass"word\'123'
        config_file = self.validator._create_wpa_config('TestNet', password)
        
        try:
            self.assertTrue(os.path.exists(config_file))
            
            with open(config_file, 'r') as f:
                content = f.read()
            
            # Password should be in config (may be escaped)
            self.assertIn('psk=', content)
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
    
    def test_cache_different_passwords(self):
        """Test caching works with different password formats."""
        # Cache various password formats
        self.validator._cache_result('Net1', 'simple123', True)
        self.validator._cache_result('Net2', 'P@$$w0rd!', False)
        self.validator._cache_result('Net3', 'Café2024', True)
        
        # Verify cache hits
        self.assertTrue(self.validator._check_cache('Net1', 'simple123'))
        self.assertFalse(self.validator._check_cache('Net2', 'P@$$w0rd!'))
        self.assertTrue(self.validator._check_cache('Net3', 'Café2024'))
        
        # Verify cache misses
        self.assertIsNone(self.validator._check_cache('Net1', 'wrong'))
        self.assertIsNone(self.validator._check_cache('Net4', 'simple123'))


class TestNetworkConditionSimulation(unittest.TestCase):
    """Test attack lifecycle with simulated network conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_target = Mock(spec=Target)
        self.mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        self.mock_target.essid = 'TestNetwork'
        self.mock_target.channel = 6
        self.mock_target.encryption = 'WPA2'
        self.mock_target.power = -50
        self.mock_target.wps = False
        
        Configuration.interface = 'wlan0'
    
    @patch('wifite.attack.eviltwin.Color')
    @patch('wifite.attack.eviltwin.input')
    def test_slow_client_connection(self, mock_input, mock_color):
        """Test scenario: Client takes long time to connect."""
        mock_input.return_value = 'YES'
        
        attack = EvilTwin(self.mock_target)
        
        # Simulate slow connection (client connects after delay)
        from wifite.util.client_monitor import ClientConnection
        
        # Client connects after 30 seconds
        time.sleep(0.1)  # Simulate delay
        client = ClientConnection('11:22:33:44:55:66', '192.168.100.10', 'slow-client', time.time())
        attack._on_client_connect(client)
        
        # Verify client is tracked
        self.assertEqual(len(attack.clients_connected), 1)
    
    @patch('wifite.attack.eviltwin.Color')
    @patch('wifite.attack.eviltwin.input')
    def test_intermittent_client_connection(self, mock_input, mock_color):
        """Test scenario: Client connects and disconnects repeatedly."""
        mock_input.return_value = 'YES'
        
        attack = EvilTwin(self.mock_target)
        from wifite.util.client_monitor import ClientConnection
        
        client = ClientConnection('11:22:33:44:55:66', '192.168.100.10', 'flaky-client', time.time())
        
        # Simulate connect/disconnect cycle
        attack._on_client_connect(client)
        self.assertEqual(len(attack.clients_connected), 1)
        
        attack._on_client_disconnect(client)
        # Client remains in history
        self.assertEqual(len(attack.clients_connected), 1)
        
        # Reconnect
        attack._on_client_connect(client)
        self.assertEqual(len(attack.clients_connected), 1)
    
    @patch('wifite.attack.eviltwin.Color')
    @patch('wifite.attack.eviltwin.input')
    def test_multiple_failed_attempts_before_success(self, mock_input, mock_color):
        """Test scenario: Multiple failed password attempts before success."""
        mock_input.return_value = 'YES'
        
        attack = EvilTwin(self.mock_target)
        
        # Simulate multiple failed attempts
        attack.on_credential_submission('11:22:33:44:55:66', 'wrong1', False)
        attack.on_credential_submission('11:22:33:44:55:66', 'wrong2', False)
        attack.on_credential_submission('11:22:33:44:55:66', 'wrong3', False)
        
        self.assertEqual(len(attack.credential_attempts), 3)
        self.assertIsNone(attack.crack_result)
        
        # Finally correct password
        attack.on_credential_submission('11:22:33:44:55:66', 'correct', True)
        
        self.assertEqual(len(attack.credential_attempts), 4)
        self.assertIsNotNone(attack.crack_result)
        self.assertEqual(attack.crack_result.key, 'correct')
    
    @patch('wifite.attack.eviltwin.Color')
    @patch('wifite.attack.eviltwin.input')
    def test_validation_timeout_scenario(self, mock_input, mock_color):
        """Test scenario: Credential validation times out."""
        mock_input.return_value = 'YES'
        
        attack = EvilTwin(self.mock_target)
        
        # Simulate timeout (validation takes too long)
        # In real scenario, validator would timeout
        # Here we just verify attack handles it gracefully
        attack.on_credential_submission('11:22:33:44:55:66', 'timeout_test', False)
        
        # Attack should continue running
        self.assertEqual(len(attack.credential_attempts), 1)
    
    def test_rate_limiting_backoff(self):
        """Test scenario: Rate limiting with exponential backoff."""
        validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 6)
        
        # Initial state
        self.assertEqual(validator.backoff_multiplier, 1.0)
        
        # Simulate consecutive failures
        for i in range(5):
            validator._handle_failed_validation()
        
        # Backoff should increase
        self.assertGreater(validator.backoff_multiplier, 1.0)
        self.assertEqual(validator.consecutive_failures, 5)
        
        # Successful validation resets backoff
        validator._handle_successful_validation()
        self.assertEqual(validator.backoff_multiplier, 1.0)
        self.assertEqual(validator.consecutive_failures, 0)
    
    def test_ap_lockout_scenario(self):
        """Test scenario: AP locks out after too many failed attempts."""
        validator = CredentialValidator('wlan0mon', 'AA:BB:CC:DD:EE:FF', 6)
        
        # Set to lockout threshold
        validator.failed_attempt_count = validator.lockout_threshold
        
        # Trigger lockout
        validator._trigger_lockout()
        
        # Verify lockout state
        self.assertTrue(validator.is_locked_out)
        self.assertGreater(validator.lockout_until, 0)
        
        # Verify in lockout
        self.assertTrue(validator._is_in_lockout())
    
    @patch('wifite.attack.eviltwin.Color')
    @patch('wifite.attack.eviltwin.input')
    def test_high_client_volume_scenario(self, mock_input, mock_color):
        """Test scenario: Many clients connect simultaneously."""
        mock_input.return_value = 'YES'
        
        attack = EvilTwin(self.mock_target)
        from wifite.util.client_monitor import ClientConnection
        
        # Simulate 10 clients connecting
        for i in range(10):
            client = ClientConnection(
                f'11:22:33:44:55:{i:02d}',
                f'192.168.100.{10+i}',
                f'client{i}',
                time.time()
            )
            attack._on_client_connect(client)
        
        # Verify all clients are tracked
        self.assertEqual(len(attack.clients_connected), 10)
    
    @patch('wifite.attack.eviltwin.Color')
    @patch('wifite.attack.eviltwin.input')
    def test_concurrent_credential_submissions(self, mock_input, mock_color):
        """Test scenario: Multiple clients submit credentials simultaneously."""
        mock_input.return_value = 'YES'
        
        attack = EvilTwin(self.mock_target)
        
        # Simulate concurrent submissions from different clients
        attack.on_credential_submission('11:22:33:44:55:01', 'pass1', False)
        attack.on_credential_submission('11:22:33:44:55:02', 'pass2', False)
        attack.on_credential_submission('11:22:33:44:55:03', 'pass3', True)
        
        # Verify all attempts are tracked
        self.assertEqual(len(attack.credential_attempts), 3)
        
        # Verify successful credential is captured
        self.assertIsNotNone(attack.crack_result)
        self.assertEqual(attack.crack_result.key, 'pass3')


class TestCompleteAttackLifecycle(unittest.TestCase):
    """Test complete attack lifecycle with realistic conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_target = Mock(spec=Target)
        self.mock_target.bssid = 'AA:BB:CC:DD:EE:FF'
        self.mock_target.essid = 'RealWorldNetwork'
        self.mock_target.channel = 6
        self.mock_target.encryption = 'WPA2'
        self.mock_target.power = -50
        self.mock_target.wps = False
        
        Configuration.interface = 'wlan0'
        Configuration.eviltwin_timeout = 0
    
    @patch('wifite.attack.eviltwin.Color')
    @patch('wifite.attack.eviltwin.input')
    @patch('wifite.attack.eviltwin.EvilTwin._check_dependencies')
    @patch('wifite.attack.eviltwin.EvilTwin._check_for_conflicts')
    @patch('wifite.attack.eviltwin.EvilTwin._setup')
    @patch('wifite.attack.eviltwin.EvilTwin._cleanup')
    def test_realistic_attack_flow(self, mock_cleanup, mock_setup, mock_conflicts,
                                   mock_deps, mock_input, mock_color):
        """Test realistic attack flow from start to finish."""
        mock_input.return_value = 'YES'
        mock_deps.return_value = True
        mock_conflicts.return_value = True
        mock_setup.return_value = True
        
        attack = EvilTwin(self.mock_target)
        from wifite.util.client_monitor import ClientConnection
        
        # Simulate realistic attack flow
        def simulate_realistic_flow():
            time.sleep(0.05)
            
            # Client 1 connects
            client1 = ClientConnection('11:22:33:44:55:66', '192.168.100.10', 'phone', time.time())
            attack._on_client_connect(client1)
            
            time.sleep(0.02)
            
            # Client 1 tries wrong password
            attack.on_credential_submission('11:22:33:44:55:66', 'wrongpass', False)
            
            time.sleep(0.02)
            
            # Client 2 connects
            client2 = ClientConnection('AA:BB:CC:DD:EE:11', '192.168.100.11', 'laptop', time.time())
            attack._on_client_connect(client2)
            
            time.sleep(0.02)
            
            # Client 1 tries correct password
            attack.on_credential_submission('11:22:33:44:55:66', 'correctpass', True)
        
        import threading
        flow_thread = threading.Thread(target=simulate_realistic_flow)
        flow_thread.daemon = True
        flow_thread.start()
        
        # Run attack
        result = attack.run()
        
        # Verify success
        self.assertTrue(result)
        self.assertTrue(attack.success)
        self.assertIsNotNone(attack.crack_result)
        self.assertEqual(attack.crack_result.key, 'correctpass')
        
        # Verify cleanup was called
        mock_cleanup.assert_called()


if __name__ == '__main__':
    unittest.main()
