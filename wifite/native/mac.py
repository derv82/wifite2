#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Native MAC address manipulation without external tools.

Replaces 'macchanger' with pure Python implementation using:
- sysfs interface (/sys/class/net/<iface>/address)
- ioctl system calls (SIOCSIFHWADDR)

Usage:
    from wifite.native.mac import NativeMac
    
    # Get current MAC
    mac = NativeMac.get_mac('wlan0')
    
    # Set specific MAC (interface must be down)
    NativeMac.set_mac('wlan0', '00:11:22:33:44:55')
    
    # Generate and set random MAC
    NativeMac.random('wlan0')
    
    # Reset to permanent/original MAC
    NativeMac.reset('wlan0')
"""

import re
import secrets
import fcntl
import socket
import struct
from typing import Optional, Tuple
from ..util.logger import log_debug


class NativeMac:
    """
    Native MAC address manipulation.
    
    Uses direct kernel interfaces instead of external tools.
    Requires root/CAP_NET_ADMIN for MAC changes.
    """
    
    # ioctl constants for network interface manipulation
    SIOCGIFHWADDR = 0x8927  # Get hardware address
    SIOCSIFHWADDR = 0x8924  # Set hardware address
    SIOCGIFFLAGS = 0x8913   # Get interface flags
    SIOCSIFFLAGS = 0x8914   # Set interface flags
    IFF_UP = 0x1            # Interface is up
    
    # Cache for original MACs (to support reset)
    _original_macs = {}
    
    # Common vendor OUI prefixes (for realistic random MACs)
    VENDOR_OUIS = [
        '00:0C:29',  # VMware
        '00:50:56',  # VMware
        '00:1A:11',  # Google
        '00:1B:63',  # Apple
        '00:1C:B3',  # Apple
        '00:21:E9',  # Apple
        '00:23:12',  # Apple
        '00:25:00',  # Apple
        '00:26:BB',  # Apple
        '3C:D9:2B',  # HP
        '00:1E:68',  # Quanta
        '00:24:D7',  # Intel
        '00:26:C6',  # Intel
        '00:1F:3B',  # Intel
        '00:15:00',  # Intel
        '00:13:02',  # Intel
        '00:22:FA',  # Intel
        'F0:DE:F1',  # Samsung
        '00:24:54',  # Samsung
        '00:1A:8A',  # Samsung
        '00:12:FB',  # Samsung
        '00:1D:25',  # Samsung
        '84:38:35',  # Huawei
        '00:25:9E',  # Huawei
        '00:18:82',  # Huawei
        '00:1E:10',  # Huawei
    ]
    
    @classmethod
    def get_mac(cls, interface: str) -> Optional[str]:
        """
        Get the current MAC address of an interface.
        
        Args:
            interface: Network interface name (e.g., 'wlan0')
            
        Returns:
            MAC address string (e.g., '00:11:22:33:44:55') or None if failed
        """
        # Method 1: Try sysfs (fastest)
        sysfs_path = f'/sys/class/net/{interface}/address'
        try:
            with open(sysfs_path, 'r') as f:
                mac = f.read().strip()
                if cls._is_valid_mac(mac):
                    return mac.upper()
        except (IOError, OSError):
            pass
        
        # Method 2: Try ioctl
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Create interface request struct (ifreq)
                ifreq = struct.pack('256s', interface.encode('utf-8')[:15])
                result = fcntl.ioctl(sock.fileno(), cls.SIOCGIFHWADDR, ifreq)
                # MAC is at offset 18 in the result
                mac_bytes = result[18:24]
                mac = ':'.join(f'{b:02X}' for b in mac_bytes)
                return mac
            finally:
                sock.close()
        except (IOError, OSError):
            pass
        
        return None
    
    @classmethod
    def get_permanent_mac(cls, interface: str) -> Optional[str]:
        """
        Get the permanent (factory) MAC address of an interface.
        
        Uses ethtool-style permanent address from sysfs.
        
        Args:
            interface: Network interface name
            
        Returns:
            Permanent MAC address or None if not available
        """
        # Try reading from sysfs
        perm_path = f'/sys/class/net/{interface}/perm_hwaddr'
        try:
            with open(perm_path, 'r') as f:
                mac = f.read().strip()
                if cls._is_valid_mac(mac):
                    return mac.upper()
        except (IOError, OSError):
            pass
        
        # Fall back to cached original MAC
        return cls._original_macs.get(interface)
    
    @classmethod
    def set_mac(cls, interface: str, mac: str) -> Tuple[bool, str]:
        """
        Set the MAC address of an interface.
        
        The interface must be in DOWN state before changing MAC.
        
        Args:
            interface: Network interface name
            mac: New MAC address (e.g., '00:11:22:33:44:55')
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate MAC format
        if not cls._is_valid_mac(mac):
            return False, f'Invalid MAC address format: {mac}'
        
        # Normalize MAC format
        mac = mac.upper().replace('-', ':')
        
        # Store original MAC if not already stored
        if interface not in cls._original_macs:
            current = cls.get_mac(interface)
            if current:
                cls._original_macs[interface] = current
        
        # Check if interface is up
        if cls._is_interface_up(interface):
            return False, f'Interface {interface} must be down before changing MAC'
        
        # Method 1: Try sysfs (requires root)
        sysfs_path = f'/sys/class/net/{interface}/address'
        try:
            with open(sysfs_path, 'w') as f:
                f.write(mac.lower())
            
            # Verify the change
            new_mac = cls.get_mac(interface)
            if new_mac and new_mac.upper() == mac.upper():
                return True, f'MAC address changed to {mac}'
        except (IOError, OSError, PermissionError):
            pass
        
        # Method 2: Try ioctl
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Convert MAC to bytes
                mac_bytes = bytes.fromhex(mac.replace(':', ''))
                
                # Build ifreq struct: interface name + sa_family (1 = AF_LOCAL) + MAC bytes
                ifreq = struct.pack('16sH6s', 
                                   interface.encode('utf-8')[:15] + b'\x00',
                                   1,  # sa_family = AF_LOCAL
                                   mac_bytes)
                # Pad to 40 bytes
                ifreq = ifreq + b'\x00' * (40 - len(ifreq))
                
                fcntl.ioctl(sock.fileno(), cls.SIOCSIFHWADDR, ifreq)
                
                # Verify the change
                new_mac = cls.get_mac(interface)
                if new_mac and new_mac.upper() == mac.upper():
                    return True, f'MAC address changed to {mac}'
                    
            finally:
                sock.close()
        except (IOError, OSError, PermissionError) as e:
            pass
        
        # Method 3: Fall back to ip command
        try:
            from ..util.process import Process
            Process.call(f'ip link set {interface} address {mac}')
            
            new_mac = cls.get_mac(interface)
            if new_mac and new_mac.upper() == mac.upper():
                return True, f'MAC address changed to {mac} (via ip command)'
        except Exception as e:
            log_debug('NativeMac', f'MAC change via ip link failed on {interface}: {e}')
        
        return False, f'Failed to change MAC address on {interface}'
    
    @classmethod
    def random(cls, interface: str, keep_vendor: bool = False) -> Tuple[bool, str]:
        """
        Set a random MAC address on the interface.
        
        Args:
            interface: Network interface name
            keep_vendor: If True, only randomize the device portion (last 3 bytes)
            
        Returns:
            Tuple of (success: bool, message/new_mac: str)
        """
        if keep_vendor:
            # Keep the vendor OUI, randomize device portion
            current = cls.get_mac(interface)
            if current:
                vendor = current[:8]  # First 3 bytes (with colons)
                device = ':'.join(f'{b:02X}' for b in secrets.token_bytes(3))
                new_mac = f'{vendor}:{device}'
            else:
                new_mac = cls._generate_random_mac()
        else:
            new_mac = cls._generate_random_mac()
        
        success, msg = cls.set_mac(interface, new_mac)
        if success:
            return True, new_mac
        return False, msg
    
    @classmethod
    def reset(cls, interface: str) -> Tuple[bool, str]:
        """
        Reset MAC address to the original/permanent value.
        
        Args:
            interface: Network interface name
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Try to get permanent MAC
        perm_mac = cls.get_permanent_mac(interface)
        
        if not perm_mac:
            return False, f'No permanent MAC address available for {interface}'
        
        return cls.set_mac(interface, perm_mac)
    
    @classmethod
    def _generate_random_mac(cls, use_real_vendor: bool = True) -> str:
        """
        Generate a random MAC address.
        
        Args:
            use_real_vendor: If True, use a real vendor OUI prefix
            
        Returns:
            Random MAC address string
        """
        if use_real_vendor:
            vendor = cls.VENDOR_OUIS[secrets.randbelow(len(cls.VENDOR_OUIS))]
            device = ':'.join(f'{b:02X}' for b in secrets.token_bytes(3))
            return f'{vendor}:{device}'
        else:
            # Generate completely random MAC with unicast, locally administered bit
            first_byte = secrets.token_bytes(1)[0] & 0xFE | 0x02  # Ensure unicast + locally administered
            rest = list(secrets.token_bytes(5))
            return ':'.join(f'{b:02X}' for b in [first_byte] + rest)
    
    @classmethod
    def _is_valid_mac(cls, mac: str) -> bool:
        """Check if a string is a valid MAC address."""
        if not mac:
            return False
        # Accept both colon and hyphen separators
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))
    
    @classmethod
    def _is_interface_up(cls, interface: str) -> bool:
        """Check if an interface is up."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                ifreq = struct.pack('256s', interface.encode('utf-8')[:15])
                result = fcntl.ioctl(sock.fileno(), cls.SIOCGIFFLAGS, ifreq)
                flags = struct.unpack('16sH', result[:18])[1]
                return bool(flags & cls.IFF_UP)
            finally:
                sock.close()
        except (IOError, OSError):
            # Fall back to sysfs
            try:
                with open(f'/sys/class/net/{interface}/operstate', 'r') as f:
                    return f.read().strip().lower() == 'up'
            except (IOError, OSError):
                return False


# Convenience functions for backward compatibility
def get_mac(interface: str) -> Optional[str]:
    """Get MAC address of interface."""
    return NativeMac.get_mac(interface)


def set_mac(interface: str, mac: str) -> Tuple[bool, str]:
    """Set MAC address of interface."""
    return NativeMac.set_mac(interface, mac)


def random_mac(interface: str, keep_vendor: bool = False) -> Tuple[bool, str]:
    """Set random MAC address on interface."""
    return NativeMac.random(interface, keep_vendor)


def reset_mac(interface: str) -> Tuple[bool, str]:
    """Reset MAC to permanent/original value."""
    return NativeMac.reset(interface)
