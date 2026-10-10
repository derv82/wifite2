#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for native Python implementations.

Tests the wifite.native module components:
- NativeMac: MAC address manipulation
- ScapyDeauth: Deauthentication frames (Scapy)
- ScapyHandshake: Handshake verification (Scapy)
- ScapyWPS: WPS detection (Scapy)
- NativeInterface: Interface management
"""

import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestNativeMac:
    """Tests for native MAC address manipulation."""
    
    def test_import(self):
        """Test that NativeMac can be imported."""
        from wifite.native.mac import NativeMac
        assert NativeMac is not None
    
    def test_is_valid_mac(self):
        """Test MAC address validation."""
        from wifite.native.mac import NativeMac
        
        # Valid MACs
        assert NativeMac._is_valid_mac('00:11:22:33:44:55')
        assert NativeMac._is_valid_mac('AA:BB:CC:DD:EE:FF')
        assert NativeMac._is_valid_mac('aa:bb:cc:dd:ee:ff')
        assert NativeMac._is_valid_mac('00-11-22-33-44-55')
        
        # Invalid MACs
        assert not NativeMac._is_valid_mac('')
        assert not NativeMac._is_valid_mac('00:11:22:33:44')
        assert not NativeMac._is_valid_mac('00:11:22:33:44:55:66')
        assert not NativeMac._is_valid_mac('GG:HH:II:JJ:KK:LL')
        assert not NativeMac._is_valid_mac(None)
    
    def test_generate_random_mac(self):
        """Test random MAC generation."""
        from wifite.native.mac import NativeMac
        
        # Generate with real vendor OUI
        mac1 = NativeMac._generate_random_mac(use_real_vendor=True)
        assert NativeMac._is_valid_mac(mac1)
        
        # Generate fully random
        mac2 = NativeMac._generate_random_mac(use_real_vendor=False)
        assert NativeMac._is_valid_mac(mac2)
        
        # Should be different
        assert mac1 != mac2
    
    def test_vendor_ouis_are_valid(self):
        """Test that all vendor OUIs are valid."""
        from wifite.native.mac import NativeMac
        
        for oui in NativeMac.VENDOR_OUIS:
            # OUI should be 8 characters (XX:XX:XX)
            assert len(oui) == 8
            # Should have proper format
            parts = oui.split(':')
            assert len(parts) == 3
            for part in parts:
                assert len(part) == 2
                int(part, 16)  # Should not raise


class TestScapyDeauth:
    """Tests for Scapy-based deauthentication."""
    
    def test_import(self):
        """Test that ScapyDeauth can be imported."""
        from wifite.native.deauth import ScapyDeauth
        assert ScapyDeauth is not None
    
    def test_availability_check(self):
        """Test that availability check works."""
        from wifite.native.deauth import ScapyDeauth, SCAPY_AVAILABLE
        
        result = ScapyDeauth.is_available()
        assert result == SCAPY_AVAILABLE
    
    def test_reason_codes(self):
        """Test that reason codes are defined."""
        from wifite.native.deauth import ScapyDeauth
        
        assert hasattr(ScapyDeauth, 'REASON_UNSPECIFIED')
        assert hasattr(ScapyDeauth, 'REASON_LEAVING')
        assert hasattr(ScapyDeauth, 'DEFAULT_REASONS')
        assert len(ScapyDeauth.DEFAULT_REASONS) > 0
    
    def test_continuous_deauth_init(self):
        """Test ContinuousDeauth initialization."""
        from wifite.native.deauth import ContinuousDeauth
        
        deauth = ContinuousDeauth(
            interface='wlan0mon',
            bssid='AA:BB:CC:DD:EE:FF',
            interval=1.0,
            burst_count=3
        )
        
        assert deauth.interface == 'wlan0mon'
        assert deauth.bssid == 'AA:BB:CC:DD:EE:FF'
        assert deauth.interval == 1.0
        assert deauth.burst_count == 3
        assert not deauth.is_paused()


class TestScapyHandshake:
    """Tests for Scapy-based handshake verification."""
    
    def test_import(self):
        """Test that ScapyHandshake can be imported."""
        from wifite.native.handshake import ScapyHandshake
        assert ScapyHandshake is not None
    
    def test_availability_check(self):
        """Test that availability check works."""
        from wifite.native.handshake import ScapyHandshake, SCAPY_AVAILABLE
        
        result = ScapyHandshake.is_available()
        assert result == SCAPY_AVAILABLE
    
    def test_nonexistent_file(self):
        """Test handling of non-existent capture file."""
        from wifite.native.handshake import ScapyHandshake
        
        result = ScapyHandshake.bssids_with_handshakes('/nonexistent/file.cap')
        assert result == []
    
    def test_is_complete_handshake(self):
        """Test handshake completeness check."""
        from wifite.native.handshake import ScapyHandshake
        
        assert ScapyHandshake._is_complete_handshake({1, 2, 3, 4})
        assert not ScapyHandshake._is_complete_handshake({1, 2, 3})
        assert not ScapyHandshake._is_complete_handshake({1, 2, 4})
        assert not ScapyHandshake._is_complete_handshake({1})
        assert not ScapyHandshake._is_complete_handshake(set())
    
    def test_determine_message_number(self):
        """Test EAPOL message number determination."""
        from wifite.native.handshake import ScapyHandshake
        
        # Message 1: ACK=1, MIC=0, INSTALL=0, SECURE=0
        assert ScapyHandshake._determine_message_number(True, False, False, False) == 1
        
        # Message 2: ACK=0, MIC=1, INSTALL=0, SECURE=0
        assert ScapyHandshake._determine_message_number(False, True, False, False) == 2
        
        # Message 3: ACK=1, MIC=1, INSTALL=1, SECURE=1
        assert ScapyHandshake._determine_message_number(True, True, True, True) == 3
        
        # Message 4: ACK=0, MIC=1, INSTALL=0, SECURE=1
        assert ScapyHandshake._determine_message_number(False, True, False, True) == 4


class TestScapyWPS:
    """Tests for Scapy-based WPS detection."""
    
    def test_import(self):
        """Test that ScapyWPS can be imported."""
        from wifite.native.wps import ScapyWPS, WPSInfo
        assert ScapyWPS is not None
        assert WPSInfo is not None
    
    def test_availability_check(self):
        """Test that availability check works."""
        from wifite.native.wps import ScapyWPS, SCAPY_AVAILABLE
        
        result = ScapyWPS.is_available()
        assert result == SCAPY_AVAILABLE
    
    def test_wps_info_init(self):
        """Test WPSInfo initialization."""
        from wifite.native.wps import WPSInfo
        
        info = WPSInfo('AA:BB:CC:DD:EE:FF')
        assert info.bssid == 'AA:BB:CC:DD:EE:FF'
        assert info.wps_enabled == False
        assert info.locked == False
    
    def test_nonexistent_file(self):
        """Test handling of non-existent capture file."""
        from wifite.native.wps import ScapyWPS
        
        result = ScapyWPS.detect_wps('/nonexistent/file.cap')
        assert result == {}
    
    def test_wps_attribute_constants(self):
        """Test WPS attribute type constants."""
        from wifite.native.wps import ScapyWPS
        
        assert hasattr(ScapyWPS, 'WPS_VENDOR_ID')
        assert hasattr(ScapyWPS, 'WPS_ATTR_STATE')
        assert hasattr(ScapyWPS, 'WPS_ATTR_AP_SETUP_LOCKED')


class TestNativeInterface:
    """Tests for native interface management."""
    
    def test_import(self):
        """Test that NativeInterface can be imported."""
        from wifite.native.interface import NativeInterface, InterfaceInfo
        assert NativeInterface is not None
        assert InterfaceInfo is not None
    
    def test_channel_freq_mapping(self):
        """Test channel to frequency mapping."""
        from wifite.native.interface import NativeInterface
        
        # 2.4 GHz channels
        assert NativeInterface._channel_to_freq(1) == 2412
        assert NativeInterface._channel_to_freq(6) == 2437
        assert NativeInterface._channel_to_freq(11) == 2462
        
        # 5 GHz channels
        assert NativeInterface._channel_to_freq(36) == 5180
        assert NativeInterface._channel_to_freq(149) == 5745
        
        # Invalid channel
        assert NativeInterface._channel_to_freq(999) is None
    
    def test_freq_channel_mapping(self):
        """Test frequency to channel mapping."""
        from wifite.native.interface import NativeInterface
        
        # 2.4 GHz
        assert NativeInterface._freq_to_channel(2412) == 1
        assert NativeInterface._freq_to_channel(2437) == 6
        
        # 5 GHz
        assert NativeInterface._freq_to_channel(5180) == 36
        
        # Unknown frequency
        assert NativeInterface._freq_to_channel(9999) is None
    
    def test_mode_names(self):
        """Test wireless mode name mapping."""
        from wifite.native.interface import NativeInterface
        
        assert NativeInterface.MODE_NAMES[NativeInterface.IW_MODE_MONITOR] == 'monitor'
        assert NativeInterface.MODE_NAMES[NativeInterface.IW_MODE_MANAGED] == 'managed'


class TestNativeModuleInit:
    """Tests for native module initialization."""
    
    def test_module_import(self):
        """Test that native module can be imported."""
        from wifite import native
        assert native is not None
    
    def test_all_exports(self):
        """Test that all expected classes are exported."""
        from wifite.native import (
            NativeMac,
            ScapyDeauth,
            ScapyHandshake,
            ScapyWPS,
            NativeInterface,
            ScapyPMKID,
            PMKIDResult,
            ChannelHopper,
            NativeScanner,
        )
        
        assert NativeMac is not None
        assert ScapyDeauth is not None
        assert ScapyHandshake is not None
        assert ScapyWPS is not None
        assert NativeInterface is not None
        assert ScapyPMKID is not None
        assert PMKIDResult is not None
        assert ChannelHopper is not None
        assert NativeScanner is not None
    
    def test_check_native_availability(self):
        """Test native availability check function."""
        from wifite.native import check_native_availability
        
        status = check_native_availability()
        assert isinstance(status, dict)
        assert 'mac' in status
        assert 'deauth' in status
        assert 'handshake' in status
        assert 'wps' in status
        assert 'pmkid' in status
        assert 'scanner' in status


class TestScapyPMKID:
    """Tests for Scapy-based PMKID capture."""
    
    def test_import(self):
        """Test that ScapyPMKID can be imported."""
        from wifite.native.pmkid import ScapyPMKID
        assert ScapyPMKID is not None
    
    def test_availability_check(self):
        """Test that availability check works."""
        from wifite.native.pmkid import ScapyPMKID, SCAPY_AVAILABLE
        
        result = ScapyPMKID.is_available()
        assert result == SCAPY_AVAILABLE
    
    def test_pmkid_result_to_hashcat(self):
        """Test PMKIDResult conversion to hashcat format."""
        from wifite.native.pmkid import PMKIDResult
        
        result = PMKIDResult(
            bssid='AA:BB:CC:DD:EE:FF',
            client_mac='11:22:33:44:55:66',
            pmkid='0123456789abcdef0123456789abcdef',
            essid='TestNetwork'
        )
        
        # Test 22000 format
        hashcat_22000 = result.to_hashcat_22000()
        assert hashcat_22000.startswith('WPA*02*')
        assert 'aabbccddeeff' in hashcat_22000
        assert '112233445566' in hashcat_22000
        
        # Test 16800 format
        hashcat_16800 = result.to_hashcat_16800()
        assert '0123456789abcdef' in hashcat_16800
        assert '*' in hashcat_16800


class TestNativeScanner:
    """Tests for native WiFi scanner."""
    
    def test_import(self):
        """Test that NativeScanner can be imported."""
        from wifite.native.scanner import NativeScanner, ChannelHopper
        assert NativeScanner is not None
        assert ChannelHopper is not None
    
    def test_channel_constants(self):
        """Test channel constant definitions."""
        from wifite.native.scanner import (
            CHANNELS_24GHZ, CHANNELS_5GHZ, CHANNELS_ALL
        )
        
        assert 1 in CHANNELS_24GHZ
        assert 6 in CHANNELS_24GHZ
        assert 11 in CHANNELS_24GHZ
        
        assert 36 in CHANNELS_5GHZ
        assert 149 in CHANNELS_5GHZ
        
        assert len(CHANNELS_ALL) > len(CHANNELS_24GHZ)
    
    def test_access_point_dataclass(self):
        """Test AccessPoint dataclass."""
        from wifite.native.scanner import AccessPoint
        
        ap = AccessPoint(
            bssid='AA:BB:CC:DD:EE:FF',
            essid='TestNetwork',
            channel=6,
            encryption='WPA2'
        )
        
        assert ap.bssid == 'AA:BB:CC:DD:EE:FF'
        assert ap.essid == 'TestNetwork'
        assert ap.channel == 6
        assert ap.encryption == 'WPA2'
        assert ap.clients == []
    
    def test_channel_hopper_init(self):
        """Test ChannelHopper initialization."""
        from wifite.native.scanner import ChannelHopper, CHANNELS_24GHZ
        
        hopper = ChannelHopper(
            interface='wlan0mon',
            interval=0.5,
            band='2.4'
        )
        
        assert hopper.interface == 'wlan0mon'
        assert hopper.interval == 0.5
        assert hopper.channels == CHANNELS_24GHZ
        assert not hopper.is_paused()


class TestIntegrationWithExistingTools:
    """Tests for integration with existing tool wrappers."""
    
    def test_macchanger_native_check(self):
        """Test that Macchanger can detect native alternative."""
        from wifite.tools.macchanger import Macchanger
        
        # Should be able to call the method
        result = Macchanger._can_use_native()
        assert isinstance(result, bool)
    
    def test_tshark_native_check(self):
        """Test that Tshark can detect native alternative."""
        from wifite.tools.tshark import Tshark
        
        result = Tshark._can_use_native()
        assert isinstance(result, bool)
    
    def test_aireplay_native_deauth_check(self):
        """Test that Aireplay can detect native deauth."""
        from wifite.tools.aireplay import Aireplay
        
        result = Aireplay._can_use_native_deauth()
        assert isinstance(result, bool)
    
    def test_dependency_native_alternative_check(self):
        """Test dependency native alternative checking."""
        from wifite.tools.dependency import Dependency
        from wifite.tools.macchanger import Macchanger
        from wifite.tools.tshark import Tshark
        
        # These should return bool
        assert isinstance(Macchanger.has_native_alternative(), bool)
        assert isinstance(Tshark.has_native_alternative(), bool)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
