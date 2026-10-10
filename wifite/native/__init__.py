#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Native Python implementations for WiFi operations.

This module provides pure Python alternatives to external tools like:
- macchanger → native.mac
- aireplay-ng (deauth) → native.deauth  
- tshark (handshake verification) → native.handshake
- tshark (WPS detection) → native.wps
- ip/iw commands → native.interface
- hcxdumptool (PMKID capture) → native.pmkid
- airodump-ng (scanning) → native.scanner

Benefits:
- Fewer external dependencies
- Better cross-platform support
- More control over packet crafting
- Graceful fallback to external tools if native fails

Requirements:
- scapy >= 2.7.1rc1 (already a project dependency)
"""

try:
    from .mac import NativeMac
except Exception:
    NativeMac = None

try:
    from .deauth import ScapyDeauth, ContinuousDeauth as NativeDeauth
except Exception:
    ScapyDeauth = None
    NativeDeauth = None

try:
    from .handshake import ScapyHandshake
except Exception:
    ScapyHandshake = None

try:
    from .wps import ScapyWPS, WPSInfo
except Exception:
    ScapyWPS = None
    WPSInfo = None

try:
    from .interface import NativeInterface, InterfaceInfo
except Exception:
    NativeInterface = None
    InterfaceInfo = None

try:
    from .pmkid import ScapyPMKID, PMKIDResult, PMKIDCapture
except Exception:
    ScapyPMKID = None
    PMKIDResult = None
    PMKIDCapture = None

try:
    from .scanner import ChannelHopper, NativeScanner, AccessPoint, Client
except Exception:
    ChannelHopper = None
    NativeScanner = None
    AccessPoint = None
    Client = None

try:
    from .beacon import BeaconGenerator, create_fake_ap as create_beacon
except Exception:
    BeaconGenerator = None
    create_beacon = None

__all__ = [
    # MAC manipulation
    'NativeMac',
    
    # Deauthentication
    'ScapyDeauth', 
    'NativeDeauth',
    
    # Handshake verification
    'ScapyHandshake',
    
    # WPS detection
    'ScapyWPS',
    'WPSInfo',
    
    # Interface management
    'NativeInterface',
    'InterfaceInfo',
    
    # PMKID capture
    'ScapyPMKID',
    'PMKIDResult',
    'PMKIDCapture',
    
    # Scanning
    'ChannelHopper',
    'NativeScanner',
    'AccessPoint',
    'Client',
    
    # Beacon generation
    'BeaconGenerator',
    'create_beacon',
]


def check_native_availability() -> dict:
    """
    Check which native implementations are available.
    
    Returns:
        Dictionary with availability status for each module
    """
    status = {}
    
    try:
        from .mac import NativeMac
        status['mac'] = True
    except Exception:
        status['mac'] = False

    try:
        from .deauth import SCAPY_AVAILABLE
        status['deauth'] = SCAPY_AVAILABLE
    except Exception:
        status['deauth'] = False

    try:
        from .handshake import SCAPY_AVAILABLE
        status['handshake'] = SCAPY_AVAILABLE
    except Exception:
        status['handshake'] = False

    try:
        from .wps import SCAPY_AVAILABLE
        status['wps'] = SCAPY_AVAILABLE
    except Exception:
        status['wps'] = False

    try:
        from .interface import NativeInterface
        status['interface'] = True
    except Exception:
        status['interface'] = False

    try:
        from .pmkid import SCAPY_AVAILABLE
        status['pmkid'] = SCAPY_AVAILABLE
    except Exception:
        status['pmkid'] = False

    try:
        from .scanner import SCAPY_AVAILABLE
        status['scanner'] = SCAPY_AVAILABLE
    except Exception:
        status['scanner'] = False

    try:
        from .beacon import SCAPY_AVAILABLE
        status['beacon'] = SCAPY_AVAILABLE
    except Exception:
        status['beacon'] = False
    
    return status


def print_native_status():
    """Print native implementation availability status."""
    status = check_native_availability()
    
    print("Native Implementation Status:")
    print("-" * 40)
    
    modules = {
        'mac': 'MAC Manipulation (macchanger)',
        'deauth': 'Deauthentication (aireplay-ng)',
        'handshake': 'Handshake Verification (tshark)',
        'wps': 'WPS Detection (tshark)',
        'interface': 'Interface Management (ip/iw)',
        'pmkid': 'PMKID Capture (hcxdumptool)',
        'scanner': 'Network Scanning (airodump-ng)',
        'beacon': 'Beacon Generation (hostapd)',
    }
    
    for key, name in modules.items():
        available = status.get(key, False)
        status_str = "✓ Available" if available else "✗ Not Available"
        print(f"  {name}: {status_str}")
    
    # Check scapy
    try:
        import scapy
        scapy_version = scapy.VERSION if hasattr(scapy, 'VERSION') else 'unknown'
        print(f"\nScapy Version: {scapy_version}")
    except Exception:
        print("\nScapy: Not Installed")
        
