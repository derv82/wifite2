#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interface information data model for dual wireless device support.

Provides comprehensive information about wireless interfaces including
capabilities, current state, and suitability for different roles.
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class InterfaceInfo:
    """
    Comprehensive information about a wireless interface.
    
    This class contains all relevant information about a wireless interface
    including its capabilities, current state, and hardware details.
    """
    
    # Basic identification
    name: str                    # Interface name (e.g., 'wlan0')
    phy: str                     # Physical device (e.g., 'phy0')
    driver: str                  # Driver name (e.g., 'rtl8812au')
    chipset: str                 # Chipset description
    mac_address: str             # MAC address
    
    # Capabilities
    supports_ap_mode: bool       # Can create access point
    supports_monitor_mode: bool  # Can enter monitor mode
    supports_injection: bool     # Can inject packets
    
    # Current state
    current_mode: str           # Current mode (managed, monitor, AP, etc.)
    is_up: bool                 # Interface is up
    is_connected: bool          # Connected to network (for managed mode)
    
    # Optional details
    frequency: Optional[float] = None    # Current frequency in MHz
    channel: Optional[int] = None        # Current channel
    tx_power: Optional[int] = None       # TX power in dBm

    
    def can_be_ap(self) -> bool:
        """
        Check if interface can be used as an access point.
        
        Returns:
            True if interface supports AP mode and packet injection
        """
        return self.supports_ap_mode and self.supports_injection
    
    def can_be_monitor(self) -> bool:
        """
        Check if interface can be used for monitoring/deauth.
        
        Returns:
            True if interface supports monitor mode and packet injection
        """
        return self.supports_monitor_mode and self.supports_injection
    
    def is_suitable_for_evil_twin_ap(self) -> bool:
        """
        Check if interface is suitable for Evil Twin AP role.
        
        Returns:
            True if interface can host rogue AP
        """
        return self.can_be_ap()
    
    def is_suitable_for_evil_twin_deauth(self) -> bool:
        """
        Check if interface is suitable for Evil Twin deauth role.
        
        Returns:
            True if interface can perform deauthentication
        """
        return self.can_be_monitor()
    
    def is_suitable_for_wpa_capture(self) -> bool:
        """
        Check if interface is suitable for WPA handshake capture.
        
        Returns:
            True if interface can capture packets in monitor mode
        """
        return self.supports_monitor_mode
    
    def is_suitable_for_wpa_deauth(self) -> bool:
        """
        Check if interface is suitable for WPA deauthentication.
        
        Returns:
            True if interface can send deauth packets
        """
        return self.can_be_monitor()

    
    def get_capability_summary(self) -> str:
        """
        Get a human-readable summary of interface capabilities.
        
        Returns:
            String describing interface capabilities
        """
        capabilities = []
        
        if self.supports_monitor_mode:
            capabilities.append('Monitor')
        if self.supports_ap_mode:
            capabilities.append('AP')
        if self.supports_injection:
            capabilities.append('Injection')
        
        if not capabilities:
            return 'Limited capabilities'
        
        return ', '.join(capabilities)
    
    def get_status_summary(self) -> str:
        """
        Get a human-readable summary of interface status.
        
        Returns:
            String describing current interface status
        """
        status_parts = []
        
        # Mode
        status_parts.append(f'Mode: {self.current_mode}')
        
        # State
        if self.is_up:
            status_parts.append('Up')
        else:
            status_parts.append('Down')
        
        # Connection
        if self.current_mode == 'managed' and self.is_connected:
            status_parts.append('Connected')
        
        # Channel
        if self.channel:
            status_parts.append(f'Ch {self.channel}')
        
        return ', '.join(status_parts)
    
    def __str__(self) -> str:
        """
        String representation of interface info.
        
        Returns:
            Human-readable interface description
        """
        return f'{self.name} ({self.chipset}) - {self.get_capability_summary()}'
    
    def __repr__(self) -> str:
        """
        Detailed string representation for debugging.
        
        Returns:
            Detailed interface information
        """
        return (f'InterfaceInfo(name={self.name}, phy={self.phy}, '
                f'driver={self.driver}, chipset={self.chipset}, '
                f'ap={self.supports_ap_mode}, monitor={self.supports_monitor_mode}, '
                f'injection={self.supports_injection}, mode={self.current_mode}, '
                f'up={self.is_up})')



@dataclass
class InterfaceAssignment:
    """
    Assignment of interfaces to specific roles for an attack.
    
    This class represents how interfaces are assigned to different roles
    in a multi-interface attack scenario.
    """
    
    # Attack type this assignment is for
    attack_type: str  # 'evil_twin', 'wpa', 'wps', etc.
    
    # Interface assignments
    primary: str      # Primary interface name
    secondary: Optional[str] = None  # Secondary interface name (if any)
    
    # Role descriptions
    primary_role: str = 'primary'    # Role of primary interface
    secondary_role: Optional[str] = None  # Role of secondary interface
    
    def is_dual_interface(self) -> bool:
        """
        Check if this is a dual-interface assignment.
        
        Returns:
            True if using two interfaces
        """
        return self.secondary is not None
    
    def get_interfaces(self) -> List[str]:
        """
        Get list of all assigned interfaces.
        
        Returns:
            List of interface names
        """
        interfaces = [self.primary]
        if self.secondary:
            interfaces.append(self.secondary)
        return interfaces
    
    def get_assignment_summary(self) -> str:
        """
        Get human-readable summary of interface assignment.
        
        Returns:
            String describing the assignment
        """
        if self.is_dual_interface():
            return (f'{self.primary} ({self.primary_role}) + '
                   f'{self.secondary} ({self.secondary_role})')
        else:
            return f'{self.primary} ({self.primary_role})'
    
    def __str__(self) -> str:
        """
        String representation of assignment.
        
        Returns:
            Human-readable assignment description
        """
        return f'{self.attack_type.title()}: {self.get_assignment_summary()}'
