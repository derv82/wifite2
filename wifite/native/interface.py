#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Native network interface management without external tools.

Provides pure Python alternatives to 'ip' and 'iw' commands using:
- sysfs (/sys/class/net/)
- ioctl system calls
- netlink (via socket)

Usage:
    from wifite.native.interface import NativeInterface
    
    # List interfaces
    interfaces = NativeInterface.list_interfaces()
    
    # Get interface info
    info = NativeInterface.get_info('wlan0')
    
    # Set interface up/down
    NativeInterface.up('wlan0')
    NativeInterface.down('wlan0')
    
    # Get/set channel
    channel = NativeInterface.get_channel('wlan0mon')
    NativeInterface.set_channel('wlan0mon', 6)
"""

import os
import re
import socket
import struct
import fcntl
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class InterfaceInfo:
    """Container for interface information."""
    name: str
    mac_address: Optional[str] = None
    driver: Optional[str] = None
    mode: Optional[str] = None  # managed, monitor, etc.
    is_up: bool = False
    is_wireless: bool = False
    channel: Optional[int] = None
    frequency: Optional[int] = None  # MHz
    tx_power: Optional[int] = None  # dBm
    phy: Optional[str] = None  # Physical device (phy0, phy1, etc.)


class NativeInterface:
    """
    Native interface management using kernel interfaces.
    
    Uses sysfs and ioctl where possible to avoid external commands.
    Falls back to iw/ip commands if native methods fail.
    """
    
    # ioctl constants
    SIOCGIFFLAGS = 0x8913
    SIOCSIFFLAGS = 0x8914
    SIOCGIFHWADDR = 0x8927
    SIOCGIWNAME = 0x8B01    # Check if wireless
    SIOCGIWMODE = 0x8B07    # Get wireless mode
    SIOCSIWMODE = 0x8B08    # Set wireless mode
    SIOCGIWFREQ = 0x8B05    # Get frequency/channel
    SIOCSIWFREQ = 0x8B04    # Set frequency/channel
    
    IFF_UP = 0x1
    IFF_BROADCAST = 0x2
    IFF_PROMISC = 0x100
    
    # Wireless modes
    IW_MODE_AUTO = 0
    IW_MODE_ADHOC = 1
    IW_MODE_MANAGED = 2
    IW_MODE_MASTER = 3
    IW_MODE_REPEAT = 4
    IW_MODE_SECOND = 5
    IW_MODE_MONITOR = 6
    IW_MODE_MESH = 7
    
    MODE_NAMES = {
        IW_MODE_AUTO: 'auto',
        IW_MODE_ADHOC: 'ad-hoc',
        IW_MODE_MANAGED: 'managed',
        IW_MODE_MASTER: 'master',
        IW_MODE_REPEAT: 'repeater',
        IW_MODE_SECOND: 'secondary',
        IW_MODE_MONITOR: 'monitor',
        IW_MODE_MESH: 'mesh',
    }
    
    # Channel to frequency mapping (2.4 GHz)
    CHANNEL_FREQ_24 = {
        1: 2412, 2: 2417, 3: 2422, 4: 2427, 5: 2432,
        6: 2437, 7: 2442, 8: 2447, 9: 2452, 10: 2457,
        11: 2462, 12: 2467, 13: 2472, 14: 2484
    }
    
    # 5 GHz channels (partial list)
    CHANNEL_FREQ_5 = {
        36: 5180, 40: 5200, 44: 5220, 48: 5240,
        52: 5260, 56: 5280, 60: 5300, 64: 5320,
        100: 5500, 104: 5520, 108: 5540, 112: 5560,
        116: 5580, 120: 5600, 124: 5620, 128: 5640,
        132: 5660, 136: 5680, 140: 5700, 144: 5720,
        149: 5745, 153: 5765, 157: 5785, 161: 5805, 165: 5825
    }
    
    @classmethod
    def list_interfaces(cls, wireless_only: bool = False) -> List[str]:
        """
        List available network interfaces.
        
        Args:
            wireless_only: If True, only return wireless interfaces
            
        Returns:
            List of interface names
        """
        interfaces = []
        
        try:
            net_dir = '/sys/class/net'
            for name in os.listdir(net_dir):
                if wireless_only:
                    # Check if wireless directory exists
                    wireless_path = os.path.join(net_dir, name, 'wireless')
                    if not os.path.isdir(wireless_path):
                        continue
                interfaces.append(name)
        except OSError:
            pass
        
        return sorted(interfaces)
    
    @classmethod
    def get_info(cls, interface: str) -> Optional[InterfaceInfo]:
        """
        Get detailed information about an interface.
        
        Args:
            interface: Interface name
            
        Returns:
            InterfaceInfo object or None if interface doesn't exist
        """
        if not cls.exists(interface):
            return None
        
        info = InterfaceInfo(name=interface)
        sysfs_base = f'/sys/class/net/{interface}'
        
        # MAC address
        try:
            with open(f'{sysfs_base}/address', 'r') as f:
                info.mac_address = f.read().strip().upper()
        except (IOError, OSError):
            pass
        
        # Driver
        try:
            driver_link = os.readlink(f'{sysfs_base}/device/driver')
            info.driver = os.path.basename(driver_link)
        except (IOError, OSError):
            pass
        
        # Check if wireless
        info.is_wireless = os.path.isdir(f'{sysfs_base}/wireless')
        
        # Interface state
        try:
            with open(f'{sysfs_base}/operstate', 'r') as f:
                info.is_up = f.read().strip().lower() in ('up', 'unknown')
        except (IOError, OSError):
            info.is_up = cls._is_up_ioctl(interface)
        
        # PHY device
        try:
            phy_link = os.readlink(f'{sysfs_base}/phy80211')
            info.phy = os.path.basename(phy_link)
        except (IOError, OSError):
            pass
        
        # Wireless-specific info
        if info.is_wireless:
            info.mode = cls._get_mode_ioctl(interface)
            freq = cls._get_frequency_ioctl(interface)
            if freq:
                info.frequency = freq
                info.channel = cls._freq_to_channel(freq)
        
        return info
    
    @classmethod
    def exists(cls, interface: str) -> bool:
        """Check if interface exists."""
        return os.path.exists(f'/sys/class/net/{interface}')
    
    @classmethod
    def is_wireless(cls, interface: str) -> bool:
        """Check if interface is wireless."""
        return os.path.isdir(f'/sys/class/net/{interface}/wireless')
    
    @classmethod
    def is_monitor(cls, interface: str) -> bool:
        """Check if interface is in monitor mode."""
        mode = cls._get_mode_ioctl(interface)
        return mode == 'monitor' if mode else False
    
    @classmethod
    def up(cls, interface: str) -> Tuple[bool, str]:
        """
        Bring interface up.
        
        Args:
            interface: Interface name
            
        Returns:
            Tuple of (success, message)
        """
        return cls._set_flags(interface, add_flags=cls.IFF_UP)
    
    @classmethod
    def down(cls, interface: str) -> Tuple[bool, str]:
        """
        Bring interface down.
        
        Args:
            interface: Interface name
            
        Returns:
            Tuple of (success, message)
        """
        return cls._set_flags(interface, remove_flags=cls.IFF_UP)
    
    @classmethod
    def get_mac(cls, interface: str) -> Optional[str]:
        """Get MAC address of interface."""
        try:
            with open(f'/sys/class/net/{interface}/address', 'r') as f:
                return f.read().strip().upper()
        except (IOError, OSError):
            pass
        
        # Fallback to ioctl
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                ifreq = struct.pack('256s', interface.encode('utf-8')[:15])
                result = fcntl.ioctl(sock.fileno(), cls.SIOCGIFHWADDR, ifreq)
                mac_bytes = result[18:24]
                return ':'.join(f'{b:02X}' for b in mac_bytes)
            finally:
                sock.close()
        except (IOError, OSError):
            return None
    
    @classmethod
    def get_channel(cls, interface: str) -> Optional[int]:
        """Get current channel of wireless interface."""
        freq = cls._get_frequency_ioctl(interface)
        if freq:
            return cls._freq_to_channel(freq)
        
        # Fallback to iw command
        try:
            from ..util.process import Process
            out, err = Process.call(f'iw dev {interface} info')
            match = re.search(r'channel (\d+)', out)
            if match:
                return int(match.group(1))
        except (OSError, Exception):
            pass
        
        return None
    
    @classmethod
    def set_channel(cls, interface: str, channel: int) -> Tuple[bool, str]:
        """
        Set channel on wireless interface.
        
        Args:
            interface: Wireless interface name
            channel: Channel number
            
        Returns:
            Tuple of (success, message)
        """
        freq = cls._channel_to_freq(channel)
        if not freq:
            return False, f'Invalid channel: {channel}'
        
        # Try ioctl first
        success = cls._set_frequency_ioctl(interface, freq)
        if success:
            return True, f'Channel set to {channel}'
        
        # Fallback to iw command
        try:
            from ..util.process import Process
            out, err = Process.call(f'iw dev {interface} set channel {channel}')
            if err and 'error' in err.lower():
                return False, err.strip()
            return True, f'Channel set to {channel}'
        except Exception as e:
            return False, str(e)
    
    @classmethod
    def set_mode(cls, interface: str, mode: str) -> Tuple[bool, str]:
        """
        Set wireless interface mode.
        
        Args:
            interface: Wireless interface name
            mode: Mode name ('monitor', 'managed', etc.)
            
        Returns:
            Tuple of (success, message)
        """
        # Map mode name to ioctl value
        mode_map = {v: k for k, v in cls.MODE_NAMES.items()}
        mode_lower = mode.lower()
        
        if mode_lower not in mode_map:
            return False, f'Unknown mode: {mode}'
        
        mode_value = mode_map[mode_lower]
        
        # Try ioctl first
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # iwreq structure for SIOCSIWMODE
                iwreq = struct.pack('16sI', interface.encode('utf-8')[:15] + b'\x00', mode_value)
                iwreq = iwreq + b'\x00' * (32 - len(iwreq))  # Pad to 32 bytes
                fcntl.ioctl(sock.fileno(), cls.SIOCSIWMODE, iwreq)
                return True, f'Mode set to {mode}'
            finally:
                sock.close()
        except (IOError, OSError):
            pass
        
        # Fallback to iw command
        try:
            from ..util.process import Process
            out, err = Process.call(f'iw dev {interface} set type {mode}')
            if err and 'error' in err.lower():
                return False, err.strip()
            return True, f'Mode set to {mode}'
        except Exception as e:
            return False, str(e)
    
    @classmethod
    def get_mode(cls, interface: str) -> Optional[str]:
        """Get current wireless mode."""
        return cls._get_mode_ioctl(interface)
    
    @classmethod
    def _is_up_ioctl(cls, interface: str) -> bool:
        """Check if interface is up using ioctl."""
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
            return False
    
    @classmethod
    def _set_flags(cls, interface: str, add_flags: int = 0, remove_flags: int = 0) -> Tuple[bool, str]:
        """Set interface flags using ioctl."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Get current flags
                ifreq = struct.pack('256s', interface.encode('utf-8')[:15])
                result = fcntl.ioctl(sock.fileno(), cls.SIOCGIFFLAGS, ifreq)
                flags = struct.unpack('16sH', result[:18])[1]
                
                # Modify flags
                flags = (flags | add_flags) & ~remove_flags
                
                # Set new flags
                ifreq = struct.pack('16sH', interface.encode('utf-8')[:15] + b'\x00', flags)
                ifreq = ifreq + b'\x00' * (256 - len(ifreq))
                fcntl.ioctl(sock.fileno(), cls.SIOCSIFFLAGS, ifreq)
                
                return True, 'Flags updated'
            finally:
                sock.close()
        except (IOError, OSError) as e:
            pass
        
        # Fallback to ip command
        try:
            from ..util.process import Process
            action = 'up' if add_flags & cls.IFF_UP else 'down'
            out, err = Process.call(f'ip link set {interface} {action}')
            if err and 'error' in err.lower():
                return False, err.strip()
            return True, f'Interface {action}'
        except Exception as e:
            return False, str(e)
    
    @classmethod
    def _get_mode_ioctl(cls, interface: str) -> Optional[str]:
        """Get wireless mode using ioctl."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # iwreq structure
                iwreq = struct.pack('16s32s', interface.encode('utf-8')[:15] + b'\x00', b'\x00' * 32)
                result = fcntl.ioctl(sock.fileno(), cls.SIOCGIWMODE, iwreq)
                mode = struct.unpack('16sI', result[:20])[1]
                return cls.MODE_NAMES.get(mode, 'unknown')
            finally:
                sock.close()
        except (IOError, OSError):
            pass
        
        # Fallback to iw command
        try:
            from ..util.process import Process
            out, err = Process.call(f'iw dev {interface} info')
            match = re.search(r'type (\w+)', out)
            if match:
                return match.group(1).lower()
        except (OSError, Exception):
            pass
        
        return None
    
    @classmethod
    def _get_frequency_ioctl(cls, interface: str) -> Optional[int]:
        """Get wireless frequency using ioctl."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                iwreq = struct.pack('16s32s', interface.encode('utf-8')[:15] + b'\x00', b'\x00' * 32)
                result = fcntl.ioctl(sock.fileno(), cls.SIOCGIWFREQ, iwreq)
                # Frequency is returned as iw_freq struct (mantissa + exponent)
                # Simplified: just try to extract the frequency
                freq_data = struct.unpack('16sIHHI', result[:28])
                mantissa = freq_data[1]
                exponent = freq_data[2]
                
                # Calculate frequency in Hz, convert to MHz
                if exponent == 0:
                    # Already in MHz (channel number) or needs conversion
                    if mantissa < 1000:
                        # Likely a channel number, convert
                        return cls._channel_to_freq(mantissa)
                    return mantissa
                else:
                    freq_hz = mantissa * (10 ** exponent)
                    return freq_hz // 1000000  # Convert to MHz
                    
            finally:
                sock.close()
        except (IOError, OSError):
            pass
        
        return None
    
    @classmethod
    def _set_frequency_ioctl(cls, interface: str, freq_mhz: int) -> bool:
        """Set wireless frequency using ioctl."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # iw_freq struct: mantissa (uint32) + exponent (uint16) + flags (uint8) + pad (uint8)
                freq_hz = freq_mhz * 1000000
                iwreq = struct.pack('16sIHBB', 
                                   interface.encode('utf-8')[:15] + b'\x00',
                                   freq_hz,  # mantissa
                                   0,        # exponent (0 = value is in Hz)
                                   0,        # flags
                                   0)        # padding
                iwreq = iwreq + b'\x00' * (32 - (len(iwreq) - 16))
                fcntl.ioctl(sock.fileno(), cls.SIOCSIWFREQ, iwreq)
                return True
            finally:
                sock.close()
        except (IOError, OSError):
            return False
    
    @classmethod
    def _channel_to_freq(cls, channel: int) -> Optional[int]:
        """Convert channel number to frequency in MHz."""
        if channel in cls.CHANNEL_FREQ_24:
            return cls.CHANNEL_FREQ_24[channel]
        if channel in cls.CHANNEL_FREQ_5:
            return cls.CHANNEL_FREQ_5[channel]
        return None
    
    @classmethod
    def _freq_to_channel(cls, freq_mhz: int) -> Optional[int]:
        """Convert frequency in MHz to channel number."""
        # Search 2.4 GHz
        for ch, f in cls.CHANNEL_FREQ_24.items():
            if abs(f - freq_mhz) < 5:  # Allow small variance
                return ch
        # Search 5 GHz
        for ch, f in cls.CHANNEL_FREQ_5.items():
            if abs(f - freq_mhz) < 5:
                return ch
        return None


# Convenience functions
def list_interfaces(wireless_only: bool = False) -> List[str]:
    """List network interfaces."""
    return NativeInterface.list_interfaces(wireless_only)


def get_info(interface: str) -> Optional[InterfaceInfo]:
    """Get interface information."""
    return NativeInterface.get_info(interface)


def up(interface: str) -> Tuple[bool, str]:
    """Bring interface up."""
    return NativeInterface.up(interface)


def down(interface: str) -> Tuple[bool, str]:
    """Bring interface down."""
    return NativeInterface.down(interface)


def get_mac(interface: str) -> Optional[str]:
    """Get interface MAC address."""
    return NativeInterface.get_mac(interface)
