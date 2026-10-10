#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Scapy-based WPS (Wi-Fi Protected Setup) detection.

Replaces 'tshark' for WPS network detection with native Python/Scapy.

Usage:
    from wifite.native.wps import ScapyWPS
    
    # Check WPS status from capture file
    wps_networks = ScapyWPS.detect_wps('capture.cap')
    
    # Update targets with WPS information
    ScapyWPS.update_targets('capture.cap', targets)

WPS Information Elements:
    - WPS IE Vendor ID: 00:50:f2:04 (Microsoft)
    - Device Password ID: 0x1012
    - Config Methods: 0x1008
    - Wi-Fi Protected Setup State: 0x1044
      - 0x01: Not Configured
      - 0x02: Configured
    - AP Setup Locked: 0x1057
      - 0x01: Locked
"""

import os
from typing import Optional, List, Dict

try:
    from scapy.all import (
        rdpcap, Dot11, Dot11Beacon, Dot11ProbeResp, Dot11Elt,
        conf as scapy_conf
    )
    SCAPY_AVAILABLE = True
except (ImportError, AttributeError):
    SCAPY_AVAILABLE = False


class WPSInfo:
    """Container for WPS information."""
    
    # WPS states
    NOT_CONFIGURED = 0x01
    CONFIGURED = 0x02
    
    # Lock states
    UNLOCKED = False
    LOCKED = True
    
    def __init__(self, bssid: str):
        self.bssid = bssid.upper()
        self.wps_enabled = False
        self.wps_state = None  # 1 = not configured, 2 = configured
        self.locked = False
        self.version = None
        self.config_methods = None
        self.device_name = None
        self.manufacturer = None
    
    def __repr__(self):
        state_str = {1: 'not_configured', 2: 'configured'}.get(self.wps_state, 'unknown')
        lock_str = 'locked' if self.locked else 'unlocked'
        return f'WPSInfo(bssid={self.bssid}, enabled={self.wps_enabled}, state={state_str}, {lock_str})'


class ScapyWPS:
    """
    Native WPS detection using Scapy.
    
    Parses WPS Information Elements from beacon/probe response frames.
    
    Advantages over tshark:
    - No external process spawning  
    - Direct packet access
    - More efficient for multiple operations
    """
    
    # WPS IE identifiers
    WPS_VENDOR_ID = b'\x00\x50\xf2\x04'  # Microsoft WPS
    
    # WPS attribute types (TLV format)
    WPS_ATTR_VERSION = 0x104A
    WPS_ATTR_STATE = 0x1044
    WPS_ATTR_AP_SETUP_LOCKED = 0x1057
    WPS_ATTR_CONFIG_METHODS = 0x1008
    WPS_ATTR_DEVICE_NAME = 0x1011
    WPS_ATTR_MANUFACTURER = 0x1021
    WPS_ATTR_MODEL_NAME = 0x1023
    WPS_ATTR_MODEL_NUMBER = 0x1024
    WPS_ATTR_DEVICE_PASSWORD_ID = 0x1012
    WPS_ATTR_RESPONSE_TYPE = 0x103B
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Scapy is available."""
        return SCAPY_AVAILABLE
    
    @classmethod
    def detect_wps(cls, capfile: str) -> Dict[str, WPSInfo]:
        """
        Detect WPS-enabled networks from capture file.
        
        Args:
            capfile: Path to pcap/cap file
            
        Returns:
            Dict mapping BSSID -> WPSInfo
        """
        if not SCAPY_AVAILABLE:
            return {}
        
        if not os.path.exists(capfile):
            return {}
        
        try:
            old_verb = scapy_conf.verb
            scapy_conf.verb = 0
            
            try:
                packets = rdpcap(capfile)
            finally:
                scapy_conf.verb = old_verb
            
            wps_info = {}
            
            for pkt in packets:
                # Only process beacons and probe responses
                if not (pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp)):
                    continue
                
                if not pkt.haslayer(Dot11):
                    continue
                
                dot11 = pkt.getlayer(Dot11)
                bssid = (dot11.addr3 or '').upper()
                
                if not bssid or bssid == 'FF:FF:FF:FF:FF:FF':
                    continue
                
                # Parse information elements for WPS
                info = cls._parse_wps_ie(pkt, bssid)
                
                if info and info.wps_enabled:
                    # Keep the most informative entry
                    if bssid not in wps_info or (info.wps_state and not wps_info[bssid].wps_state):
                        wps_info[bssid] = info
            
            return wps_info

        except (OSError, AttributeError):
            return {}
    
    @classmethod
    def update_targets(cls, capfile: str, targets: List) -> None:
        """
        Update target list with WPS information from capture.
        
        Args:
            capfile: Path to pcap/cap file
            targets: List of Target objects to update
        """
        if not SCAPY_AVAILABLE:
            return
        
        wps_info = cls.detect_wps(capfile)
        
        for target in targets:
            bssid = target.bssid.upper()
            if bssid in wps_info:
                info = wps_info[bssid]
                # Update target's WPS state
                # Import WPSState to set appropriate value
                try:
                    from ..model.target import WPSState
                    if info.locked:
                        target.wps = WPSState.LOCKED
                    elif info.wps_enabled:
                        target.wps = WPSState.UNLOCKED
                except ImportError:
                    # Fallback to integer values
                    if info.locked:
                        target.wps = 2  # LOCKED
                    elif info.wps_enabled:
                        target.wps = 1  # UNLOCKED
    
    @classmethod
    def _parse_wps_ie(cls, pkt, bssid: str) -> Optional[WPSInfo]:
        """
        Parse WPS information element from packet.
        
        Args:
            pkt: Scapy packet
            bssid: BSSID of the network
            
        Returns:
            WPSInfo object or None if no WPS found
        """
        info = WPSInfo(bssid)
        
        # Traverse information elements
        elt = pkt.getlayer(Dot11Elt)
        
        while elt:
            # WPS is in vendor-specific IE (ID 221)
            if elt.ID == 221:
                try:
                    ie_data = bytes(elt.info) if hasattr(elt, 'info') else b''

                    # Check for WPS vendor ID
                    if ie_data.startswith(cls.WPS_VENDOR_ID):
                        info.wps_enabled = True

                        # Parse WPS attributes (TLV format after vendor ID)
                        cls._parse_wps_attributes(ie_data[4:], info)

                except (AttributeError, TypeError, IndexError):
                    pass
            
            # Move to next element
            if hasattr(elt, 'payload') and elt.payload:
                if hasattr(elt.payload, 'getlayer'):
                    elt = elt.payload.getlayer(Dot11Elt)
                else:
                    elt = None
            else:
                elt = None
        
        return info if info.wps_enabled else None
    
    @classmethod
    def _parse_wps_attributes(cls, data: bytes, info: WPSInfo) -> None:
        """
        Parse WPS attributes in TLV format.
        
        Format: Type (2 bytes, big-endian) + Length (2 bytes, big-endian) + Value
        
        Args:
            data: Raw attribute data
            info: WPSInfo object to populate
        """
        offset = 0
        
        while offset + 4 <= len(data):
            try:
                # Read Type and Length (big-endian)
                attr_type = (data[offset] << 8) | data[offset + 1]
                attr_len = (data[offset + 2] << 8) | data[offset + 3]
                offset += 4
                
                if offset + attr_len > len(data):
                    break
                
                attr_value = data[offset:offset + attr_len]
                offset += attr_len
                
                # Parse known attributes
                if attr_type == cls.WPS_ATTR_VERSION:
                    if attr_len >= 1:
                        info.version = attr_value[0]
                
                elif attr_type == cls.WPS_ATTR_STATE:
                    if attr_len >= 1:
                        info.wps_state = attr_value[0]
                
                elif attr_type == cls.WPS_ATTR_AP_SETUP_LOCKED:
                    if attr_len >= 1:
                        info.locked = (attr_value[0] == 0x01)
                
                elif attr_type == cls.WPS_ATTR_CONFIG_METHODS:
                    if attr_len >= 2:
                        info.config_methods = (attr_value[0] << 8) | attr_value[1]
                
                elif attr_type == cls.WPS_ATTR_DEVICE_NAME:
                    try:
                        info.device_name = attr_value.decode('utf-8', errors='replace')
                    except (UnicodeDecodeError, AttributeError):
                        pass

                elif attr_type == cls.WPS_ATTR_MANUFACTURER:
                    try:
                        info.manufacturer = attr_value.decode('utf-8', errors='replace')
                    except (UnicodeDecodeError, AttributeError):
                        pass

            except (AttributeError, TypeError, IndexError):
                break
    
    @classmethod
    def get_wps_status(cls, capfile: str, bssid: str) -> Optional[WPSInfo]:
        """
        Get WPS status for specific BSSID.
        
        Args:
            capfile: Path to pcap/cap file
            bssid: Target BSSID
            
        Returns:
            WPSInfo or None if not found
        """
        all_wps = cls.detect_wps(capfile)
        return all_wps.get(bssid.upper())
    
    @classmethod
    def is_wps_locked(cls, capfile: str, bssid: str) -> Optional[bool]:
        """
        Check if WPS is locked for specific BSSID.
        
        Args:
            capfile: Path to pcap/cap file
            bssid: Target BSSID
            
        Returns:
            True if locked, False if unlocked, None if not WPS or not found
        """
        info = cls.get_wps_status(capfile, bssid)
        if info and info.wps_enabled:
            return info.locked
        return None


# Convenience functions
def detect_wps(capfile: str) -> Dict[str, WPSInfo]:
    """Detect WPS-enabled networks from capture file."""
    return ScapyWPS.detect_wps(capfile)


def update_targets(capfile: str, targets: List) -> None:
    """Update targets with WPS information."""
    return ScapyWPS.update_targets(capfile, targets)


def is_available() -> bool:
    """Check if native WPS detection is available."""
    return SCAPY_AVAILABLE
