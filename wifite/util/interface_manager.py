#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Network interface management for Evil Twin attacks.

Provides high-level interface management including AP mode detection,
configuration, IP assignment, and cleanup.
"""

import os
import re
from typing import Optional, List, Dict
from dataclasses import dataclass

from ..tools.iw import Iw
from ..tools.ip import Ip
from ..tools.airmon import Airmon
from ..util.process import Process
from ..util.color import Color
from ..util.logger import log_info, log_error, log_warning, log_debug
from ..model.interface_info import InterfaceInfo
from ..config import Configuration


@dataclass
class InterfaceState:
    """
    Track interface state for cleanup and restoration.
    
    This class stores the original state of an interface before wifite
    modifies it, allowing proper restoration during cleanup.
    """
    name: str                           # Interface name
    original_mode: str                  # Original mode (managed, monitor, AP, etc.)
    original_up: bool                   # Whether interface was originally up
    original_mac: Optional[str]         # Original MAC address
    original_channel: Optional[int]     # Original channel
    current_mode: str                   # Current mode
    current_up: bool                    # Current up/down state
    managed_by_wifite: bool = True      # Whether wifite is managing this interface
    
    def __str__(self):
        return (f'{self.name}: original={self.original_mode}({"up" if self.original_up else "down"}), '
                f'current={self.current_mode}({"up" if self.current_up else "down"})')


class InterfaceCapabilities:
    """Represents wireless interface capabilities."""
    
    def __init__(self, interface):
        self.interface = interface
        self.supports_ap_mode = False
        self.supports_monitor_mode = False
        self.supports_managed_mode = False
        self.phy = None
        self.driver = None
        self.chipset = None
        self.mac_address = None
        
        self._detect_capabilities()
    
    def _detect_capabilities(self):
        """Detect interface capabilities using iw."""
        try:
            # Get PHY info
            output = Process(['iw', 'dev', self.interface, 'info']).stdout()
            
            # Extract PHY
            if match := re.search(r'wiphy\s+(\d+)', output):
                self.phy = f'phy{match.group(1)}'
            
            # Get MAC address
            try:
                self.mac_address = Ip.get_mac(self.interface)
            except Exception as e:
                log_debug('InterfaceManager', f'Failed to get MAC for {self.interface}: {e}')
            
            # Get driver and chipset info from airmon
            iface_info = Airmon.get_iface_info(self.interface)
            if iface_info:
                self.driver = iface_info.driver
                self.chipset = iface_info.chipset
            
            # Check supported modes using iw phy
            if self.phy:
                phy_output = Process(['iw', 'phy', self.phy, 'info']).stdout()
                
                # Look for supported interface modes
                in_modes_section = False
                for line in phy_output.split('\n'):
                    if 'Supported interface modes:' in line:
                        in_modes_section = True
                        continue
                    
                    if in_modes_section:
                        if line.strip() and not line.startswith('\t'):
                            # End of modes section
                            break
                        
                        if '* AP' in line or '* master' in line:
                            self.supports_ap_mode = True
                        if '* monitor' in line:
                            self.supports_monitor_mode = True
                        if '* managed' in line:
                            self.supports_managed_mode = True
            
            log_debug('InterfaceManager', 
                     f'{self.interface}: AP={self.supports_ap_mode}, '
                     f'Monitor={self.supports_monitor_mode}, '
                     f'Managed={self.supports_managed_mode}')
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to detect capabilities for {self.interface}: {e}', e)
    
    def __str__(self):
        modes = []
        if self.supports_ap_mode:
            modes.append('AP')
        if self.supports_monitor_mode:
            modes.append('Monitor')
        if self.supports_managed_mode:
            modes.append('Managed')
        
        return f'{self.interface} ({", ".join(modes)})'


class InterfaceManager:
    """
    Manages network interfaces for Evil Twin attacks.
    
    Handles interface mode changes, IP configuration, and cleanup.
    Tracks interface states for proper restoration.
    """
    
    def __init__(self):
        # Track interface states for cleanup (interface_name -> InterfaceState)
        self.interface_states: Dict[str, InterfaceState] = {}
        
        # Track assigned IP addresses (interface_name -> ip_address)
        self.assigned_ips: Dict[str, str] = {}
        
        # Legacy compatibility - maps to interface_states
        self.managed_interfaces = {}  # Deprecated, kept for compatibility
    
    @staticmethod
    def _execute_verbose(command: List[str], description: str = None) -> Optional[str]:
        """
        Execute a command with verbose logging support.
        
        Task 11.5: Log all system commands executed and their outputs in verbose mode.
        
        Args:
            command: Command to execute as list of arguments
            description: Optional description of what the command does
            
        Returns:
            Command output (stdout) or None on error
        """
        try:
            # Task 11.5: Log all system commands executed in verbose mode
            if Configuration.verbose >= 2:
                cmd_str = ' '.join(command)
                if description:
                    log_debug('InterfaceManager', f'Executing command: {description}')
                log_debug('InterfaceManager', f'Command: {cmd_str}')
            
            # Execute command
            proc = Process(command)
            output = proc.stdout()
            
            # Task 11.5: Log all system command outputs in verbose mode
            if Configuration.verbose >= 3 and output:
                log_debug('InterfaceManager', f'Command output:\n{output}')
            
            return output
            
        except Exception as e:
            log_error('InterfaceManager', f'Command execution failed: {e}', e)
            return None
    
    def _save_interface_state(self, interface: str) -> bool:
        """
        Save the current state of an interface for later restoration.
        
        This method captures the interface's current configuration before
        wifite makes any changes, allowing proper cleanup later.
        
        Args:
            interface: Interface name to save state for
            
        Returns:
            True if state was saved successfully, False otherwise
        """
        try:
            # Don't save state twice for the same interface
            if interface in self.interface_states:
                log_debug('InterfaceManager', f'State already saved for {interface}')
                return True
            
            log_debug('InterfaceManager', f'Saving state for {interface}')
            
            # Get current state
            current_mode = self._get_interface_mode(interface)
            current_up = self._is_interface_up(interface)
            current_mac = self._get_interface_mac(interface)
            current_channel = self._get_interface_channel(interface)
            
            # Create state object
            state = InterfaceState(
                name=interface,
                original_mode=current_mode,
                original_up=current_up,
                original_mac=current_mac,
                original_channel=current_channel,
                current_mode=current_mode,
                current_up=current_up,
                managed_by_wifite=True
            )
            
            # Store state
            self.interface_states[interface] = state
            
            # Legacy compatibility
            self.managed_interfaces[interface] = {
                'interface': interface,
                'mode': current_mode,
                'up': current_up,
                'mac': current_mac
            }
            
            log_info('InterfaceManager', f'Saved state for {interface}: {state}')
            return True
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to save state for {interface}: {e}', e)
            return False
    
    def _update_interface_state(self, interface: str, mode: Optional[str] = None, 
                               up: Optional[bool] = None) -> bool:
        """
        Update the tracked state of an interface after making changes.
        
        Args:
            interface: Interface name
            mode: New mode (if changed)
            up: New up/down state (if changed)
            
        Returns:
            True if state was updated, False otherwise
        """
        try:
            if interface not in self.interface_states:
                log_warning('InterfaceManager', f'No saved state for {interface}, cannot update')
                return False
            
            state = self.interface_states[interface]
            
            # Task 11.5: Log all interface state changes in verbose mode
            if mode is not None:
                old_mode = state.current_mode
                state.current_mode = mode
                log_debug('InterfaceManager', f'Updated {interface} mode to {mode}')
                
                if Configuration.verbose >= 2:
                    log_debug('InterfaceManager', f'State change: {interface} mode: {old_mode} -> {mode}')
            
            if up is not None:
                old_up = state.current_up
                state.current_up = up
                log_debug('InterfaceManager', f'Updated {interface} up state to {up}')
                
                if Configuration.verbose >= 2:
                    log_debug('InterfaceManager', f'State change: {interface} up: {old_up} -> {up}')
            
            return True
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to update state for {interface}: {e}', e)
            return False
    
    def is_managed(self, interface: str) -> bool:
        """
        Check if an interface is currently managed by wifite.
        
        Args:
            interface: Interface name
            
        Returns:
            True if interface is managed, False otherwise
        """
        return interface in self.interface_states and \
               self.interface_states[interface].managed_by_wifite
    
    def get_managed_interfaces(self) -> List[str]:
        """
        Get list of all interfaces currently managed by wifite.
        
        Returns:
            List of interface names
        """
        return [name for name, state in self.interface_states.items() 
                if state.managed_by_wifite]
    
    # ========================================================================
    # Interface Configuration Methods (Task 10.2)
    # ========================================================================
    
    def bring_interface_up(self, interface: str) -> bool:
        """
        Bring an interface up.
        
        Tracks state changes for cleanup.
        
        Args:
            interface: Interface name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Task 11.3: Log each configuration step
            log_info('InterfaceManager', f'Configuration step: Bringing {interface} up')
            
            # Save state if not already managed
            if not self.is_managed(interface):
                log_debug('InterfaceManager', f'Saving initial state for {interface}')
                self._save_interface_state(interface)
            
            # Bring interface up
            Ip.up(interface)
            
            # Update tracked state
            self._update_interface_state(interface, up=True)
            
            # Task 11.3: Log configuration results (success/failure)
            log_info('InterfaceManager', f'Configuration result: SUCCESS - {interface} is now up')
            return True
            
        except Exception as e:
            # Task 11.3: Log configuration results (success/failure)
            log_error('InterfaceManager', f'Configuration result: FAILED - Could not bring {interface} up: {e}', e)
            return False
    
    def bring_interface_down(self, interface: str) -> bool:
        """
        Bring an interface down.
        
        Tracks state changes for cleanup.
        
        Args:
            interface: Interface name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            log_debug('InterfaceManager', f'Bringing {interface} down')
            
            # Save state if not already managed
            if not self.is_managed(interface):
                self._save_interface_state(interface)
            
            # Bring interface down
            Ip.down(interface)
            
            # Update tracked state
            self._update_interface_state(interface, up=False)
            
            log_info('InterfaceManager', f'Brought {interface} down')
            return True
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to bring {interface} down: {e}', e)
            return False
    
    def set_interface_mode(self, interface: str, mode: str) -> bool:
        """
        Set interface to a specific mode.

        Tracks state changes for cleanup.

        Args:
            interface: Interface name
            mode: Mode to set ('managed', 'monitor', 'AP', 'ad-hoc', 'mesh')

        Returns:
            True if successful, False otherwise
        """
        try:
            from ..config.validators import validate_interface_name
            validate_interface_name(interface)

            # Task 11.3: Log each configuration step
            log_info('InterfaceManager', f'Configuration step: Setting {interface} to {mode} mode')
            
            # Save state if not already managed
            if not self.is_managed(interface):
                log_debug('InterfaceManager', f'Saving initial state for {interface}')
                self._save_interface_state(interface)
            
            # Bring interface down first (required for mode change)
            was_up = self._is_interface_up(interface)
            if was_up:
                log_debug('InterfaceManager', f'Bringing {interface} down for mode change')
                Ip.down(interface)
            
            # Set mode based on type
            log_debug('InterfaceManager', f'Executing mode change command for {interface}')
            
            # Task 11.5: Use verbose execution for mode changes
            if mode.lower() == 'monitor':
                InterfaceManager._execute_verbose(
                    ['iw', interface, 'set', 'monitor', 'control'],
                    f'Set {interface} to monitor mode'
                )
                Process(['iw', interface, 'set', 'monitor', 'control']).wait()
            elif mode.lower() == 'ap':
                InterfaceManager._execute_verbose(
                    ['iw', interface, 'set', 'type', '__ap'],
                    f'Set {interface} to AP mode'
                )
                Process(['iw', interface, 'set', 'type', '__ap']).wait()
            elif mode.lower() == 'managed':
                InterfaceManager._execute_verbose(
                    ['iw', interface, 'set', 'type', 'managed'],
                    f'Set {interface} to managed mode'
                )
                Process(['iw', interface, 'set', 'type', 'managed']).wait()
            elif mode.lower() == 'ad-hoc' or mode.lower() == 'adhoc':
                InterfaceManager._execute_verbose(
                    ['iw', interface, 'set', 'type', 'ibss'],
                    f'Set {interface} to ad-hoc mode'
                )
                Process(['iw', interface, 'set', 'type', 'ibss']).wait()
            elif mode.lower() == 'mesh':
                InterfaceManager._execute_verbose(
                    ['iw', interface, 'set', 'type', 'mp'],
                    f'Set {interface} to mesh mode'
                )
                Process(['iw', interface, 'set', 'type', 'mp']).wait()
            else:
                log_error('InterfaceManager', f'Unknown mode: {mode}')
                return False
            
            # Bring interface back up if it was up before
            if was_up:
                log_debug('InterfaceManager', f'Bringing {interface} back up after mode change')
                Ip.up(interface)
            
            # Task 11.3: Log interface state changes
            # Update tracked state
            self._update_interface_state(interface, mode=mode, up=was_up)
            
            # Task 11.3: Log configuration results (success/failure)
            log_info('InterfaceManager', f'Configuration result: SUCCESS - {interface} is now in {mode} mode')
            return True
            
        except Exception as e:
            # Task 11.3: Log configuration results (success/failure)
            log_error('InterfaceManager', f'Configuration result: FAILED - Could not set {interface} to {mode} mode: {e}', e)
            return False
    
    def set_interface_channel(self, interface: str, channel: int) -> bool:
        """
        Set interface to a specific channel.
        
        Tracks state changes for cleanup.
        
        Args:
            interface: Interface name
            channel: Channel number (1-14 for 2.4GHz, 36+ for 5GHz)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Task 11.3: Log each configuration step
            log_info('InterfaceManager', f'Configuration step: Setting {interface} to channel {channel}')
            
            # Save state if not already managed
            if not self.is_managed(interface):
                log_debug('InterfaceManager', f'Saving initial state for {interface}')
                self._save_interface_state(interface)
            
            # Set channel using iw
            Process(['iw', interface, 'set', 'channel', str(channel)]).wait()
            
            # Task 11.3: Log configuration results (success/failure)
            log_info('InterfaceManager', f'Configuration result: SUCCESS - {interface} is now on channel {channel}')
            return True
            
        except Exception as e:
            # Task 11.3: Log configuration results (success/failure)
            log_error('InterfaceManager', f'Configuration result: FAILED - Could not set {interface} to channel {channel}: {e}', e)
            return False
    
    def configure_interface(self, interface: str, mode: Optional[str] = None,
                          channel: Optional[int] = None, up: Optional[bool] = None) -> bool:
        """
        Configure multiple aspects of an interface at once.
        
        This is a convenience method that combines multiple configuration
        operations while properly tracking state changes.
        
        Args:
            interface: Interface name
            mode: Mode to set (optional)
            channel: Channel to set (optional)
            up: Whether to bring interface up or down (optional)
            
        Returns:
            True if all operations successful, False otherwise
        """
        try:
            log_debug('InterfaceManager', f'Configuring {interface}')
            
            # Save state if not already managed
            if not self.is_managed(interface):
                self._save_interface_state(interface)
            
            success = True
            
            # Set mode if specified
            if mode is not None:
                if not self.set_interface_mode(interface, mode):
                    success = False
            
            # Set channel if specified
            if channel is not None:
                if not self.set_interface_channel(interface, channel):
                    success = False
            
            # Set up/down state if specified
            if up is not None:
                if up:
                    if not self.bring_interface_up(interface):
                        success = False
                else:
                    if not self.bring_interface_down(interface):
                        success = False
            
            if success:
                log_info('InterfaceManager', f'Successfully configured {interface}')
            else:
                log_warning('InterfaceManager', f'Some configuration operations failed for {interface}')
            
            return success
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to configure {interface}: {e}', e)
            return False
    
    @staticmethod
    def get_wireless_interfaces() -> List[str]:
        """
        Get list of all wireless interfaces.
        
        Returns:
            List of interface names
        """
        try:
            interfaces = []
            _iface_re = re.compile(r'^[a-zA-Z0-9_\-]{1,15}$')

            # Use iw to get all wireless interfaces
            output = Process(['iw', 'dev']).stdout()

            for line in output.split('\n'):
                if 'Interface' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        interface = parts[1]
                        # Validate name before use (SEC-010)
                        if _iface_re.match(interface):
                            interfaces.append(interface)
                        else:
                            log_debug('InterfaceManager', f'Ignoring invalid interface name from iw output: {interface!r}')

            log_info('InterfaceManager', f'Found {len(interfaces)} wireless interfaces')
            return interfaces
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to get wireless interfaces: {e}', e)
            return []
    
    @staticmethod
    def get_ap_capable_interfaces() -> List[InterfaceCapabilities]:
        """
        Get list of interfaces that support AP mode.
        
        Returns:
            List of InterfaceCapabilities objects for AP-capable interfaces
        """
        ap_interfaces = []
        
        for interface in InterfaceManager.get_wireless_interfaces():
            caps = InterfaceCapabilities(interface)
            if caps.supports_ap_mode:
                ap_interfaces.append(caps)
        
        log_info('InterfaceManager', f'Found {len(ap_interfaces)} AP-capable interfaces')
        return ap_interfaces
    
    @staticmethod
    def check_ap_mode_support(interface) -> bool:
        """
        Check if an interface supports AP mode.
        
        Args:
            interface: Interface name to check
            
        Returns:
            True if AP mode is supported, False otherwise
        """
        caps = InterfaceCapabilities(interface)
        return caps.supports_ap_mode
    
    def get_interface_state(self, interface) -> dict:
        """
        Get current state of an interface.
        
        Args:
            interface: Interface name
            
        Returns:
            Dictionary with interface state information
        """
        try:
            state = {
                'interface': interface,
                'up': False,
                'mode': 'unknown',
                'ip_addresses': [],
                'mac': None
            }
            
            # Check if interface is up
            output = Process(['ip', 'link', 'show', interface]).stdout()
            state['up'] = 'UP' in output and 'state UP' in output
            
            # Get MAC address
            import contextlib
            with contextlib.suppress(Exception):
                state['mac'] = Ip.get_mac(interface)
            
            # Get mode using iw
            import contextlib
            with contextlib.suppress(Exception):
                iw_output = Process(['iw', 'dev', interface, 'info']).stdout()
                if 'type AP' in iw_output or 'type master' in iw_output:
                    state['mode'] = 'AP'
                elif 'type monitor' in iw_output:
                    state['mode'] = 'monitor'
                elif 'type managed' in iw_output:
                    state['mode'] = 'managed'
            
            # Get IP addresses
            import contextlib
            with contextlib.suppress(Exception):
                ip_output = Process(['ip', 'addr', 'show', interface]).stdout()
                for line in ip_output.split('\n'):
                    if 'inet ' in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            state['ip_addresses'].append(parts[1])
            
            return state
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to get state for {interface}: {e}', e)
            return {'interface': interface, 'error': str(e)}
    
    def configure_for_ap(self, interface, ip_address='192.168.100.1/24') -> bool:
        """
        Configure interface for AP mode.
        
        Args:
            interface: Interface to configure
            ip_address: IP address to assign (CIDR notation)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Task 11.3: Log each configuration step
            log_info('InterfaceManager', f'Configuration step: Configuring {interface} for AP mode')
            
            # Save original state before making changes
            if not self.is_managed(interface):
                log_debug('InterfaceManager', f'Saving initial state for {interface}')
                if not self._save_interface_state(interface):
                    log_warning('InterfaceManager', f'Failed to save state for {interface}, continuing anyway')
            
            # Bring interface down
            log_info('InterfaceManager', f'Configuration step: Bringing {interface} down')
            Ip.down(interface)
            self._update_interface_state(interface, up=False)
            log_debug('InterfaceManager', f'State change: {interface} is now down')
            
            # Set to AP mode
            log_info('InterfaceManager', f'Configuration step: Setting {interface} to AP mode')
            # Task 11.5: Use verbose execution
            InterfaceManager._execute_verbose(
                ['iw', interface, 'set', 'type', '__ap'],
                f'Set {interface} to AP mode'
            )
            Process(['iw', interface, 'set', 'type', '__ap']).wait()
            self._update_interface_state(interface, mode='AP')
            log_debug('InterfaceManager', f'State change: {interface} is now in AP mode')
            
            # Bring interface up
            log_info('InterfaceManager', f'Configuration step: Bringing {interface} up')
            Ip.up(interface)
            self._update_interface_state(interface, up=True)
            log_debug('InterfaceManager', f'State change: {interface} is now up')
            
            # Flush existing IP addresses
            log_info('InterfaceManager', f'Configuration step: Flushing IP addresses on {interface}')
            # Task 11.5: Use verbose execution
            InterfaceManager._execute_verbose(
                ['ip', 'addr', 'flush', 'dev', interface],
                f'Flush IP addresses on {interface}'
            )
            Process(['ip', 'addr', 'flush', 'dev', interface]).wait()
            
            # Assign IP address
            log_info('InterfaceManager', f'Configuration step: Assigning {ip_address} to {interface}')
            # Task 11.5: Use verbose execution
            InterfaceManager._execute_verbose(
                ['ip', 'addr', 'add', ip_address, 'dev', interface],
                f'Assign IP {ip_address} to {interface}'
            )
            Process(['ip', 'addr', 'add', ip_address, 'dev', interface]).wait()
            
            self.assigned_ips[interface] = ip_address
            
            # Task 11.3: Log configuration results (success/failure)
            log_info('InterfaceManager', f'Configuration result: SUCCESS - {interface} configured for AP mode with IP {ip_address}')
            return True
            
        except Exception as e:
            # Task 11.3: Log configuration results (success/failure)
            log_error('InterfaceManager', f'Configuration result: FAILED - Could not configure {interface} for AP: {e}', e)
            return False
    
    # ========================================================================
    # Interface Cleanup Methods (Task 10.3)
    # ========================================================================
    
    def restore_interface_mode(self, interface: str) -> bool:
        """
        Restore interface to its original mode.
        
        Args:
            interface: Interface to restore
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if interface not in self.interface_states:
                log_warning('InterfaceManager', f'No saved state for {interface}')
                return False
            
            state = self.interface_states[interface]
            original_mode = state.original_mode
            
            log_debug('InterfaceManager', f'Restoring {interface} mode to {original_mode}')
            
            # Don't restore to AP mode (security consideration)
            if original_mode == 'AP':
                original_mode = 'managed'
                log_debug('InterfaceManager', 'Changing AP mode to managed for safety')
            
            # Don't restore to unknown mode (invalid)
            if original_mode == 'unknown':
                original_mode = 'managed'
                log_debug('InterfaceManager', 'Changing unknown mode to managed for safety')
            
            # Set mode
            return self.set_interface_mode(interface, original_mode)
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to restore mode for {interface}: {e}', e)
            return False
    
    def restore_interface_state(self, interface: str) -> bool:
        """
        Restore interface to its original up/down state.
        
        Args:
            interface: Interface to restore
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if interface not in self.interface_states:
                log_warning('InterfaceManager', f'No saved state for {interface}')
                return False
            
            state = self.interface_states[interface]
            original_up = state.original_up
            
            log_debug('InterfaceManager', f'Restoring {interface} up/down state to {original_up}')
            
            if original_up:
                return self.bring_interface_up(interface)
            else:
                return self.bring_interface_down(interface)
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to restore state for {interface}: {e}', e)
            return False
    
    def restore_interface(self, interface: str) -> bool:
        """
        Restore interface to its original state.
        
        This method restores:
        - Interface mode
        - Up/down state
        - Removes assigned IP addresses
        
        Args:
            interface: Interface to restore
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if interface not in self.interface_states:
                log_warning('InterfaceManager', f'No saved state for {interface}')
                # Try legacy compatibility
                if interface in self.managed_interfaces:
                    return self._restore_interface_legacy(interface)
                return False
            
            state = self.interface_states[interface]
            
            # Task 11.4: Log cleanup operations
            log_info('InterfaceManager', '=' * 60)
            log_info('InterfaceManager', f'Cleanup operation: Restoring {interface} to original state')
            log_info('InterfaceManager', f'Original state: mode={state.original_mode}, up={state.original_up}')
            log_info('InterfaceManager', f'Current state: mode={state.current_mode}, up={state.current_up}')
            log_info('InterfaceManager', '=' * 60)
            
            success = True
            recovery_attempts = []
            
            # Bring interface down first
            try:
                log_info('InterfaceManager', f'Cleanup step: Bringing {interface} down')
                Ip.down(interface)
                log_debug('InterfaceManager', f'Successfully brought {interface} down')
            except Exception as e:
                # Task 11.4: Log detailed error information and recovery attempts
                log_error('InterfaceManager', f'Error during cleanup: Failed to bring {interface} down', e)
                log_warning('InterfaceManager', f'System error: {str(e)}')
                log_info('InterfaceManager', 'Recovery attempt: Continuing with restoration despite error')
                recovery_attempts.append(f'bring_down: {str(e)}')
                success = False
            
            # Flush IP addresses
            try:
                log_info('InterfaceManager', f'Cleanup step: Flushing IP addresses on {interface}')
                Process(['ip', 'addr', 'flush', 'dev', interface]).wait()
                log_debug('InterfaceManager', f'Successfully flushed IP addresses on {interface}')
            except Exception as e:
                # Task 11.4: Log detailed error information
                log_warning('InterfaceManager', f'Error during cleanup: Failed to flush IP addresses on {interface}', e)
                log_warning('InterfaceManager', f'System error: {str(e)}')
                log_info('InterfaceManager', 'Recovery attempt: Continuing (non-critical error)')
                recovery_attempts.append(f'flush_ip: {str(e)}')
                # Not critical, continue
            
            # Restore mode
            original_mode = state.original_mode
            if original_mode == 'AP':
                original_mode = 'managed'  # Don't restore to AP mode
                log_info('InterfaceManager', 'Security measure: Changing AP mode to managed for safety')
            
            if original_mode == 'unknown':
                original_mode = 'managed'  # Don't restore to unknown mode
                log_info('InterfaceManager', 'Safety measure: Changing unknown mode to managed')
            
            try:
                log_info('InterfaceManager', f'Cleanup step: Restoring {interface} to {original_mode} mode')
                # Task 11.5: Use verbose execution
                if original_mode == 'monitor':
                    InterfaceManager._execute_verbose(
                        ['iw', interface, 'set', 'monitor', 'control'],
                        f'Restore {interface} to monitor mode'
                    )
                    Process(['iw', interface, 'set', 'monitor', 'control']).wait()
                elif original_mode == 'managed':
                    InterfaceManager._execute_verbose(
                        ['iw', interface, 'set', 'type', 'managed'],
                        f'Restore {interface} to managed mode'
                    )
                    Process(['iw', interface, 'set', 'type', 'managed']).wait()
                elif original_mode == 'ad-hoc':
                    InterfaceManager._execute_verbose(
                        ['iw', interface, 'set', 'type', 'ibss'],
                        f'Restore {interface} to ad-hoc mode'
                    )
                    Process(['iw', interface, 'set', 'type', 'ibss']).wait()
                elif original_mode == 'mesh':
                    InterfaceManager._execute_verbose(
                        ['iw', interface, 'set', 'type', 'mp'],
                        f'Restore {interface} to mesh mode'
                    )
                    Process(['iw', interface, 'set', 'type', 'mp']).wait()
                else:
                    # Default to managed
                    InterfaceManager._execute_verbose(
                        ['iw', interface, 'set', 'type', 'managed'],
                        f'Restore {interface} to managed mode (default)'
                    )
                    Process(['iw', interface, 'set', 'type', 'managed']).wait()
                log_debug('InterfaceManager', f'Successfully restored {interface} to {original_mode} mode')
            except Exception as e:
                # Task 11.4: Log detailed error information and recovery attempts
                log_error('InterfaceManager', f'Error during cleanup: Failed to restore mode for {interface}', e)
                log_warning('InterfaceManager', f'System error: {str(e)}')
                log_info('InterfaceManager', 'Recovery attempt: Trying to set to managed mode as fallback')
                recovery_attempts.append(f'restore_mode: {str(e)}')
                
                # Try fallback to managed mode
                try:
                    InterfaceManager._execute_verbose(
                        ['iw', interface, 'set', 'type', 'managed'],
                        f'Fallback: Set {interface} to managed mode'
                    )
                    Process(['iw', interface, 'set', 'type', 'managed']).wait()
                    log_info('InterfaceManager', f'Recovery successful: Set {interface} to managed mode')
                except Exception as e2:
                    log_error('InterfaceManager', f'Recovery failed: Could not set {interface} to managed mode', e2)
                    success = False
            
            # Restore up/down state
            try:
                if state.original_up:
                    log_info('InterfaceManager', f'Cleanup step: Bringing {interface} up (original state)')
                    Ip.up(interface)
                    log_debug('InterfaceManager', f'Successfully brought {interface} up')
                else:
                    log_info('InterfaceManager', f'Cleanup step: Leaving {interface} down (original state)')
            except Exception as e:
                # Task 11.4: Log detailed error information
                log_error('InterfaceManager', f'Error during cleanup: Failed to restore up/down state for {interface}', e)
                log_warning('InterfaceManager', f'System error: {str(e)}')
                recovery_attempts.append(f'restore_up_state: {str(e)}')
                success = False
            
            # Clean up tracking
            del self.interface_states[interface]
            if interface in self.assigned_ips:
                del self.assigned_ips[interface]
            if interface in self.managed_interfaces:
                del self.managed_interfaces[interface]
            
            # Task 11.4: Log cleanup operations summary
            log_info('InterfaceManager', '-' * 60)
            if success:
                log_info('InterfaceManager', f'Cleanup result: SUCCESS - {interface} fully restored to original state')
            else:
                log_warning('InterfaceManager', f'Cleanup result: PARTIAL - {interface} restored with {len(recovery_attempts)} error(s)')
                for attempt in recovery_attempts:
                    log_warning('InterfaceManager', f'  Error: {attempt}')
            log_info('InterfaceManager', '=' * 60)
            
            return success
            
        except Exception as e:
            # Task 11.4: Log detailed error information
            log_error('InterfaceManager', f'Cleanup failed: Unexpected error restoring {interface}', e)
            log_error('InterfaceManager', f'System error: {str(e)}')
            return False
    
    def _restore_interface_legacy(self, interface: str) -> bool:
        """
        Legacy restore method for backward compatibility.
        
        Args:
            interface: Interface to restore
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if interface not in self.managed_interfaces:
                return False
            
            original_state = self.managed_interfaces[interface]
            
            log_debug('InterfaceManager', f'Restoring {interface} using legacy method')
            
            # Bring interface down
            Ip.down(interface)
            
            # Flush IP addresses
            Process(['ip', 'addr', 'flush', 'dev', interface]).wait()
            
            # Restore mode (default to managed)
            mode = original_state.get('mode', 'managed')
            if mode == 'AP':
                mode = 'managed'
            
            log_debug('InterfaceManager', f'Setting {interface} to {mode} mode')
            if mode == 'monitor':
                Process(['iw', interface, 'set', 'monitor', 'control']).wait()
            else:
                Process(['iw', interface, 'set', 'type', mode]).wait()
            
            # Bring interface up if it was originally up
            if original_state.get('up', False):
                Ip.up(interface)
            
            # Clean up tracking
            del self.managed_interfaces[interface]
            if interface in self.assigned_ips:
                del self.assigned_ips[interface]
            
            log_info('InterfaceManager', f'Restored {interface} (legacy)')
            return True
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to restore {interface} (legacy): {e}', e)
            return False
    
    def cleanup_all(self) -> int:
        """
        Restore all managed interfaces to their original states.
        
        This method attempts to restore all interfaces that wifite has
        modified, handling errors gracefully to ensure all interfaces
        are processed even if some fail.
        
        Returns:
            Number of interfaces successfully restored
        """
        # Task 11.4: Log cleanup operations
        log_info('InterfaceManager', '=' * 60)
        log_info('InterfaceManager', 'Starting cleanup of all managed interfaces')
        log_info('InterfaceManager', '=' * 60)
        
        # Get list of all managed interfaces
        interfaces = self.get_managed_interfaces()
        
        if not interfaces:
            log_info('InterfaceManager', 'No managed interfaces to clean up')
            return 0
        
        log_info('InterfaceManager', f'Found {len(interfaces)} managed interface(s) to clean up: {", ".join(interfaces)}')
        
        success_count = 0
        failed_interfaces = []
        
        for interface in interfaces:
            try:
                log_info('InterfaceManager', f'Cleaning up interface {success_count + len(failed_interfaces) + 1}/{len(interfaces)}: {interface}')
                
                if self.restore_interface(interface):
                    success_count += 1
                    log_info('InterfaceManager', f'Successfully cleaned up {interface}')
                else:
                    failed_interfaces.append(interface)
                    # Task 11.4: Log detailed error information
                    log_warning('InterfaceManager', f'Failed to clean up {interface}')
                    
            except Exception as e:
                failed_interfaces.append(interface)
                # Task 11.4: Log detailed error information and system error messages
                log_error('InterfaceManager', f'Error cleaning up {interface}: {e}', e)
                log_error('InterfaceManager', f'System error: {str(e)}')
        
        # Task 11.4: Log cleanup operations summary
        log_info('InterfaceManager', '=' * 60)
        if failed_interfaces:
            log_warning('InterfaceManager', 
                       f'Cleanup complete: {success_count} succeeded, {len(failed_interfaces)} failed')
            log_warning('InterfaceManager', f'Failed interfaces: {", ".join(failed_interfaces)}')
            for iface in failed_interfaces:
                log_debug('InterfaceManager', f'  {iface}: Check logs above for detailed error information')
        else:
            log_info('InterfaceManager', f'Cleanup complete: All {success_count} interface(s) successfully restored')
        log_info('InterfaceManager', '=' * 60)
        
        return success_count
    
    @staticmethod
    def select_ap_interface(preferred=None) -> Optional[str]:
        """
        Select an interface for AP mode.
        
        Args:
            preferred: Preferred interface name (optional)
            
        Returns:
            Selected interface name or None
        """
        ap_interfaces = InterfaceManager.get_ap_capable_interfaces()
        
        if not ap_interfaces:
            Color.pl('{!} {R}No AP-capable interfaces found{W}')
            Color.pl('{!} {O}Your wireless adapter may not support AP mode{W}')
            return None
        
        # If preferred interface is specified and available, use it
        if preferred:
            for caps in ap_interfaces:
                if caps.interface == preferred:
                    log_info('InterfaceManager', f'Using preferred interface: {preferred}')
                    return preferred
            
            Color.pl('{!} {O}Preferred interface {R}%s{O} not found or not AP-capable{W}' % preferred)
        
        # If only one interface, use it
        if len(ap_interfaces) == 1:
            interface = ap_interfaces[0].interface
            Color.pl('{+} Using {G}%s{W} for AP mode' % interface)
            return interface
        
        # Multiple interfaces, ask user
        Color.pl('\n{+} {C}AP-capable interfaces:{W}')
        for idx, caps in enumerate(ap_interfaces, start=1):
            Color.pl('  {G}%d{W}. %s' % (idx, caps))
        
        Color.p('\n{+} Select interface for AP mode ({G}1-%d{W}): ' % len(ap_interfaces))
        try:
            choice = int(input())
            if 1 <= choice <= len(ap_interfaces):
                interface = ap_interfaces[choice - 1].interface
                log_info('InterfaceManager', f'User selected interface: {interface}')
                return interface
            else:
                Color.pl('{!} {R}Invalid selection{W}')
                return None
        except (ValueError, KeyboardInterrupt, EOFError):
            Color.pl('{!} {R}Selection cancelled{W}')
            return None
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            import contextlib
            with contextlib.suppress(Exception):
                self.cleanup_all()
        except ImportError:
            pass
    
    # ========================================================================
    # Interface Detection and Capability Checking (Task 2)
    # ========================================================================
    
    # Known driver lists for capability detection
    INJECTION_CAPABLE_DRIVERS = {
        'ath9k', 'ath9k_htc', 'ath10k', 'ath11k',
        'rt2800usb', 'rt2800pci', 'rt73usb', 'rt61pci',
        'rtl8812au', 'rtl8814au', 'rtl8821au', 'rtl88xxau',
        'carl9170', 'zd1211rw', 'p54usb', 'p54pci'
    }
    
    NO_INJECTION_DRIVERS = {
        'brcmfmac',  # Broadcom - limited injection
        'iwlwifi',   # Intel - no injection
        'rtw88',     # Realtek new driver - limited
    }
    
    AP_CAPABLE_DRIVERS = {
        'ath9k', 'ath9k_htc', 'ath10k', 'ath11k',
        'rt2800usb', 'rt2800pci', 'rt73usb', 'rt61pci',
        'rtl8812au', 'rtl8814au', 'rtl8821au', 'rtl88xxau',
        'brcmfmac', 'b43', 'iwlwifi'
    }
    
    # Driver to chipset mapping for common drivers
    DRIVER_CHIPSET_MAP = {
        'ath9k': 'Atheros AR9xxx',
        'ath9k_htc': 'Atheros AR9271',
        'ath10k': 'Qualcomm Atheros QCA9xxx',
        'ath11k': 'Qualcomm Atheros QCA6xxx',
        'rt2800usb': 'Ralink RT2800 USB',
        'rt2800pci': 'Ralink RT2800 PCI',
        'rt73usb': 'Ralink RT73',
        'rt61pci': 'Ralink RT61',
        'rtl8812au': 'Realtek RTL8812AU',
        'rtl8814au': 'Realtek RTL8814AU',
        'rtl8821au': 'Realtek RTL8821AU',
        'rtl88xxau': 'Realtek RTL88xxAU',
        'carl9170': 'Atheros AR9170',
        'zd1211rw': 'ZyDAS ZD1211',
        'p54usb': 'Prism54 USB',
        'p54pci': 'Prism54 PCI',
        'brcmfmac': 'Broadcom FullMAC',
        'iwlwifi': 'Intel Wireless',
        'rtw88': 'Realtek RTW88',
        'b43': 'Broadcom B43',
        'icnss2': 'Qualcomm ICNSS2'
    }
    
    @staticmethod
    def _get_interface_phy(interface: str) -> str:
        """
        Get physical device identifier for interface.
        
        Args:
            interface: Interface name
            
        Returns:
            PHY identifier (e.g., 'phy0') or 'unknown'
        """
        try:
            output = Process(['iw', 'dev', interface, 'info']).stdout()
            if match := re.search(r'wiphy\s+(\d+)', output):
                return f'phy{match.group(1)}'
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to get PHY for {interface}: {e}')
        
        return 'unknown'
    
    @staticmethod
    def _get_interface_driver(interface: str) -> str:
        """
        Get driver name for interface using sysfs.
        
        Args:
            interface: Interface name
            
        Returns:
            Driver name or 'unknown'
        """
        try:
            # Try sysfs first (most reliable)
            driver_path = f'/sys/class/net/{interface}/device/driver'
            if os.path.exists(driver_path):
                driver_link = os.readlink(driver_path)
                driver = os.path.basename(driver_link)
                return driver
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to get driver via sysfs for {interface}: {e}')
        
        try:
            # Fallback to airmon-ng
            iface_info = Airmon.get_iface_info(interface)
            if iface_info and iface_info.driver:
                return iface_info.driver
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to get driver via airmon for {interface}: {e}')
        
        return 'unknown'
    
    @staticmethod
    def _get_interface_chipset(interface: str) -> str:
        """
        Get chipset description for interface.
        
        Args:
            interface: Interface name
            
        Returns:
            Chipset description or 'Unknown Chipset'
        """
        try:
            # Try airmon-ng first (has chipset info)
            iface_info = Airmon.get_iface_info(interface)
            if iface_info and iface_info.chipset:
                return iface_info.chipset
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to get chipset via airmon for {interface}: {e}')
        
        # Fallback to driver-based mapping
        driver = InterfaceManager._get_interface_driver(interface)
        if driver in InterfaceManager.DRIVER_CHIPSET_MAP:
            return InterfaceManager.DRIVER_CHIPSET_MAP[driver]
        
        return 'Unknown Chipset'
    
    @staticmethod
    def _get_interface_mac(interface: str) -> str:
        """
        Get MAC address of interface.
        
        Args:
            interface: Interface name
            
        Returns:
            MAC address or 'unknown'
        """
        try:
            return Ip.get_mac(interface)
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to get MAC for {interface}: {e}')
            return 'unknown'
    
    @staticmethod
    def _get_interface_mode(interface: str) -> str:
        """
        Get current operational mode of interface.
        
        Args:
            interface: Interface name
            
        Returns:
            Mode string ('managed', 'monitor', 'AP', etc.) or 'unknown'
        """
        try:
            # Use correct iw command syntax
            output = Process(['iw', 'dev', interface, 'info']).stdout()
            
            if 'type AP' in output or 'type master' in output:
                return 'AP'
            elif 'type monitor' in output:
                return 'monitor'
            elif 'type managed' in output:
                return 'managed'
            elif 'type IBSS' in output or 'type ad-hoc' in output:
                return 'ad-hoc'
            elif 'type mesh point' in output:
                return 'mesh'
            
            # Try to extract type from output
            if match := re.search(r'type\s+(\w+)', output):
                return match.group(1).lower()
                
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to get mode for {interface}: {e}')
        
        return 'unknown'
    
    @staticmethod
    def _is_interface_up(interface: str) -> bool:
        """
        Check if interface is up.
        
        Args:
            interface: Interface name
            
        Returns:
            True if interface is up, False otherwise
        """
        try:
            output = Process(['ip', 'link', 'show', interface]).stdout()
            # Check for both "UP" flag and "state UP"
            return 'UP' in output and 'state UP' in output
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to check if {interface} is up: {e}')
            return False
    
    @staticmethod
    def _is_interface_connected(interface: str) -> bool:
        """
        Check if interface is connected to a network.
        
        Args:
            interface: Interface name
            
        Returns:
            True if connected, False otherwise
        """
        try:
            output = Process(['iw', 'dev', interface, 'link']).stdout()
            # If connected, output contains "Connected to" or SSID info
            # If not connected, output contains "Not connected"
            return 'Not connected' not in output and ('Connected to' in output or 'SSID' in output)
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to check connection for {interface}: {e}')
            return False
    
    @staticmethod
    def _get_interface_frequency(interface: str) -> Optional[float]:
        """
        Get current frequency of interface in MHz.
        
        Args:
            interface: Interface name
            
        Returns:
            Frequency in MHz or None
        """
        try:
            output = Process(['iw', 'dev', interface, 'info']).stdout()
            # Look for frequency in format "channel X (YYYY MHz)"
            if match := re.search(r'channel\s+\d+\s+\((\d+)\s+MHz', output):
                return float(match.group(1))
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to get frequency for {interface}: {e}')
        
        return None
    
    @staticmethod
    def _get_interface_channel(interface: str) -> Optional[int]:
        """
        Get current channel of interface.
        
        Args:
            interface: Interface name
            
        Returns:
            Channel number or None
        """
        try:
            output = Process(['iw', 'dev', interface, 'info']).stdout()
            # Look for channel in format "channel X"
            if match := re.search(r'channel\s+(\d+)', output):
                return int(match.group(1))
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to get channel for {interface}: {e}')
        
        return None
    
    @staticmethod
    def _get_interface_tx_power(interface: str) -> Optional[int]:
        """
        Get TX power of interface in dBm.
        
        Args:
            interface: Interface name
            
        Returns:
            TX power in dBm or None
        """
        try:
            output = Process(['iw', 'dev', interface, 'info']).stdout()
            # Look for txpower in format "txpower XX.XX dBm"
            if match := re.search(r'txpower\s+([\d.]+)\s+dBm', output):
                return int(float(match.group(1)))
        except Exception as e:
            log_debug('InterfaceManager', f'Failed to get TX power for {interface}: {e}')
        
        return None
    
    @staticmethod
    def check_ap_mode_support(interface: str) -> bool:
        """
        Check if interface supports AP mode.
        
        Args:
            interface: Interface name
            
        Returns:
            True if AP mode is supported, False otherwise
        """
        try:
            # Get PHY for this interface
            phy = InterfaceManager._get_interface_phy(interface)
            
            if phy != 'unknown':
                # Query phy info for supported modes
                output = Process(['iw', 'phy', phy, 'info']).stdout()
                
                # Look for AP mode in supported interface modes
                in_modes_section = False
                for line in output.split('\n'):
                    if 'Supported interface modes:' in line:
                        in_modes_section = True
                        continue
                    
                    if in_modes_section:
                        # End of modes section
                        if line.strip() and not line.startswith('\t') and not line.startswith(' '):
                            break
                        
                        # Check for AP mode
                        if '* AP' in line or '* master' in line:
                            log_debug('InterfaceManager', f'{interface} supports AP mode (via iw phy)')
                            return True
            
            # Fallback: check against known AP-capable drivers
            driver = InterfaceManager._get_interface_driver(interface)
            if driver in InterfaceManager.AP_CAPABLE_DRIVERS:
                log_debug('InterfaceManager', f'{interface} supports AP mode (known driver: {driver})')
                return True
            
            log_debug('InterfaceManager', f'{interface} does not support AP mode')
            return False
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to check AP mode support for {interface}: {e}', e)
            # Conservative default: assume no AP support on error
            return False
    
    @staticmethod
    def check_monitor_mode_support(interface: str) -> bool:
        """
        Check if interface supports monitor mode.
        
        Args:
            interface: Interface name
            
        Returns:
            True if monitor mode is supported, False otherwise
        """
        try:
            # Check if already in monitor mode
            current_mode = InterfaceManager._get_interface_mode(interface)
            if current_mode == 'monitor':
                log_debug('InterfaceManager', f'{interface} already in monitor mode')
                return True
            
            # Get PHY for this interface
            phy = InterfaceManager._get_interface_phy(interface)
            
            if phy != 'unknown':
                # Query phy info for supported modes
                output = Process(['iw', 'phy', phy, 'info']).stdout()
                
                # Look for monitor mode in supported interface modes
                in_modes_section = False
                for line in output.split('\n'):
                    if 'Supported interface modes:' in line:
                        in_modes_section = True
                        continue
                    
                    if in_modes_section:
                        # End of modes section
                        if line.strip() and not line.startswith('\t') and not line.startswith(' '):
                            break
                        
                        # Check for monitor mode (various formats)
                        if '* monitor' in line.lower() or 'monitor' in line.lower():
                            log_debug('InterfaceManager', f'{interface} supports monitor mode (from phy info)')
                            return True
            
            # Fallback: Most wireless interfaces support monitor mode
            # If we got this far and it's a wireless interface, assume support
            # This prevents false negatives from parsing issues
            log_debug('InterfaceManager', f'{interface} assumed to support monitor mode (wireless interface)')
            return True
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to check monitor mode support for {interface}: {e}', e)
            # On error, assume support for wireless interfaces (optimistic fallback)
            return True
    
    @staticmethod
    def test_monitor_mode(interface: str) -> bool:
        """
        Actually test if interface can enter monitor mode.
        This performs a real test by trying to set monitor mode.
        
        Args:
            interface: Interface name
            
        Returns:
            True if monitor mode can be enabled, False otherwise
        """
        from ..tools.ip import Ip
        import time
        
        try:
            # Save original mode
            original_mode = InterfaceManager._get_interface_mode(interface)
            log_debug('InterfaceManager', f'Testing monitor mode on {interface} (current mode: {original_mode})')
            
            # If already in monitor mode, it works
            if original_mode == 'monitor':
                log_debug('InterfaceManager', f'{interface} already in monitor mode')
                from ..util.color import Color
                if Configuration.verbose > 0:
                    Color.pl('{+} {G}%s already in monitor mode{W}' % interface)
                return True
            
            # If mode detection failed, log it and default to managed
            if original_mode == 'unknown':
                log_warning('InterfaceManager', f'Could not detect mode for {interface}, defaulting to managed')
                from ..util.color import Color
                if Configuration.verbose > 0:
                    Color.pl('{!} {O}Could not detect current mode for %s, defaulting to managed{W}' % interface)
                original_mode = 'managed'  # Default to managed mode for safety
            
            # Try to set monitor mode
            try:
                Ip.down(interface)
                (out, err) = Process.call(f'iw dev {interface} set type monitor')
                
                if err and 'command failed' in err.lower():
                    log_debug('InterfaceManager', f'{interface} failed to set monitor mode: {err}')
                    # Try to restore original mode
                    import contextlib
                    with contextlib.suppress(Exception):
                        Process.call(f'iw dev {interface} set type {original_mode}')
                        Ip.up(interface)
                    return False
                
                Ip.up(interface)
                time.sleep(0.3)  # Give interface time to come up
                
                # Verify it's actually in monitor mode
                new_mode = InterfaceManager._get_interface_mode(interface)
                success = (new_mode == 'monitor')
                
                # Restore original mode
                Ip.down(interface)
                Process.call(f'iw dev {interface} set type {original_mode}')
                Ip.up(interface)
                
                if success:
                    log_debug('InterfaceManager', f'{interface} successfully tested monitor mode')
                else:
                    log_debug('InterfaceManager', f'{interface} failed monitor mode test (mode: {new_mode})')
                
                return success
                
            except Exception as e:
                log_error('InterfaceManager', f'Error testing monitor mode on {interface}: {e}', e)
                # Try to restore original state
                import contextlib
                with contextlib.suppress(Exception):
                    Ip.down(interface)
                    Process.call(f'iw dev {interface} set type {original_mode}')
                    Ip.up(interface)
                return False
                
        except Exception as e:
            log_error('InterfaceManager', f'Failed to test monitor mode for {interface}: {e}', e)
            return False
    
    @staticmethod
    def check_injection_support(interface: str) -> bool:
        """
        Check if interface supports packet injection.
        
        Args:
            interface: Interface name
            
        Returns:
            True if injection is supported, False otherwise
        """
        try:
            driver = InterfaceManager._get_interface_driver(interface)
            
            # Check against known problematic drivers
            if driver in InterfaceManager.NO_INJECTION_DRIVERS:
                log_debug('InterfaceManager', f'{interface} does not support injection (known driver: {driver})')
                return False
            
            # Check against known injection-capable drivers
            if driver in InterfaceManager.INJECTION_CAPABLE_DRIVERS:
                log_debug('InterfaceManager', f'{interface} supports injection (known driver: {driver})')
                return True
            
            # Unknown driver - optimistic default
            log_debug('InterfaceManager', f'{interface} assumed to support injection (unknown driver: {driver})')
            return True
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to check injection support for {interface}: {e}', e)
            # Optimistic default: assume injection support
            return True
    
    @staticmethod
    def get_available_interfaces() -> List[InterfaceInfo]:
        """
        Get all available wireless interfaces with their capabilities.
        
        This method enumerates all wireless interfaces on the system and
        gathers detailed information about each one, including capabilities
        and current state.
        
        Error Handling:
        - Catches exceptions during interface enumeration
        - Logs warnings for individual interface failures
        - Continues detection with remaining interfaces
        - Displays error message if no interfaces detected
        - Raises InterfaceNotFoundError if no interfaces found
        
        Returns:
            List of InterfaceInfo objects for all detected interfaces
            
        Raises:
            InterfaceNotFoundError: If no wireless interfaces are found
        """
        from .interface_exceptions import InterfaceNotFoundError
        from ..util.color import Color
        
        interfaces = []
        failed_interfaces = []
        
        try:
            # Task 11.1: Log start of interface detection
            log_info('InterfaceManager', '=' * 60)
            log_info('InterfaceManager', 'Starting wireless interface detection')
            log_info('InterfaceManager', '=' * 60)
            
            # Use Iw to enumerate wireless interfaces
            try:
                log_debug('InterfaceManager', 'Enumerating wireless interfaces using iw...')
                interface_names = Iw.get_interfaces()
                log_debug('InterfaceManager', f'iw returned {len(interface_names) if interface_names else 0} interface(s)')
            except Exception as e:
                log_error('InterfaceManager', f'Failed to enumerate interfaces: {e}', e)
                Color.pl('{!} {R}Error: Failed to enumerate wireless interfaces{W}')
                Color.pl('{!} {O}Make sure wireless tools (iw) are installed{W}')
                raise InterfaceNotFoundError(message=f'Failed to enumerate interfaces: {e}')
            
            if not interface_names:
                log_warning('InterfaceManager', 'No wireless interfaces found on system')
                Color.pl('{!} {R}No wireless interfaces found{W}')
                Color.pl('{!} {O}Make sure you have a wireless adapter connected{W}')
                raise InterfaceNotFoundError()
            
            # Task 11.1: Log each interface found with basic info
            log_info('InterfaceManager', f'Found {len(interface_names)} wireless interface(s): {", ".join(interface_names)}')
            
            # Get detailed information for each interface
            for interface_name in interface_names:
                try:
                    log_info('InterfaceManager', f'Detecting capabilities for {interface_name}...')
                    
                    interface_info = InterfaceManager._get_interface_info(interface_name)
                    
                    if interface_info:
                        interfaces.append(interface_info)
                        # Task 11.1: Log interface capabilities
                        log_info('InterfaceManager', 
                                f'  {interface_name}: {interface_info.get_capability_summary()}')
                        # Mask MAC address to avoid logging full hardware identifier
                        masked_mac = interface_info.mac_address
                        try:
                            if isinstance(interface_info.mac_address, str) and interface_info.mac_address:
                                parts = interface_info.mac_address.split(':')
                                if len(parts) == 6:
                                    masked_mac = ':'.join(parts[:3] + ['**', '**', '**'])
                        except Exception:
                            pass
                        log_debug('InterfaceManager', 
                                 f'  {interface_name} details: driver={interface_info.driver}, '
                                 f'chipset={interface_info.chipset}, phy={interface_info.phy}, '
                                 f'mac={masked_mac}')
                        log_debug('InterfaceManager', 
                                 f'  {interface_name} state: mode={interface_info.current_mode}, '
                                 f'up={interface_info.is_up}, connected={interface_info.is_connected}')
                    else:
                        # Interface info gathering failed
                        log_warning('InterfaceManager', 
                                   f'  {interface_name}: Failed to get interface info')
                        failed_interfaces.append((interface_name, 'Failed to gather information'))
                        
                except Exception as e:
                    # Don't fail entire detection for one interface
                    log_warning('InterfaceManager', 
                               f'  {interface_name}: Error during detection: {e}')
                    failed_interfaces.append((interface_name, str(e)))
                    continue
            
            # Task 11.1: Log total number of interfaces detected
            log_info('InterfaceManager', '-' * 60)
            log_info('InterfaceManager', 
                    f'Interface detection complete: {len(interfaces)} interface(s) successfully detected')
            
            if failed_interfaces:
                log_warning('InterfaceManager', 
                           f'Failed to detect {len(failed_interfaces)} interface(s)')
                for iface_name, error in failed_interfaces:
                    log_debug('InterfaceManager', f'  {iface_name}: {error}')
            
            log_info('InterfaceManager', '=' * 60)
            
            # Check if we got at least one valid interface
            if not interfaces:
                log_error('InterfaceManager', 'No valid wireless interfaces detected')
                Color.pl('{!} {R}No valid wireless interfaces detected{W}')
                
                if failed_interfaces:
                    Color.pl('{!} {O}Failed to detect the following interfaces:{W}')
                    for iface_name, error in failed_interfaces:
                        Color.pl('{!}   {C}%s{W}: {O}%s{W}' % (iface_name, error))
                
                raise InterfaceNotFoundError(message='No valid wireless interfaces detected')
            
        except InterfaceNotFoundError:
            # Re-raise our custom exception
            raise
        except Exception as e:
            log_error('InterfaceManager', f'Unexpected error during interface detection: {e}', e)
            Color.pl('{!} {R}Unexpected error during interface detection:{W} %s' % str(e))
            raise InterfaceNotFoundError(message=f'Interface detection failed: {e}')
        
        return interfaces
    
    @staticmethod
    def _get_interface_info(interface: str) -> Optional[InterfaceInfo]:
        """
        Get comprehensive information about an interface.
        
        Args:
            interface: Interface name
            
        Returns:
            InterfaceInfo object or None if interface is invalid
        """
        try:
            log_debug('InterfaceManager', f'Gathering information for {interface}')
            
            # Gather basic identification
            phy = InterfaceManager._get_interface_phy(interface)
            driver = InterfaceManager._get_interface_driver(interface)
            chipset = InterfaceManager._get_interface_chipset(interface)
            mac_address = InterfaceManager._get_interface_mac(interface)
            
            # Check capabilities
            supports_ap_mode = InterfaceManager.check_ap_mode_support(interface)
            supports_monitor_mode = InterfaceManager.check_monitor_mode_support(interface)
            supports_injection = InterfaceManager.check_injection_support(interface)
            
            # Get current state
            current_mode = InterfaceManager._get_interface_mode(interface)
            is_up = InterfaceManager._is_interface_up(interface)
            is_connected = InterfaceManager._is_interface_connected(interface)
            
            # Get optional details
            frequency = InterfaceManager._get_interface_frequency(interface)
            channel = InterfaceManager._get_interface_channel(interface)
            tx_power = InterfaceManager._get_interface_tx_power(interface)
            
            # Create InterfaceInfo object
            interface_info = InterfaceInfo(
                name=interface,
                phy=phy,
                driver=driver,
                chipset=chipset,
                mac_address=mac_address,
                supports_ap_mode=supports_ap_mode,
                supports_monitor_mode=supports_monitor_mode,
                supports_injection=supports_injection,
                current_mode=current_mode,
                is_up=is_up,
                is_connected=is_connected,
                frequency=frequency,
                channel=channel,
                tx_power=tx_power
            )
            
            log_debug('InterfaceManager', f'Interface info for {interface}: {interface_info.get_capability_summary()}')
            return interface_info
            
        except Exception as e:
            log_error('InterfaceManager', f'Failed to get interface info for {interface}: {e}', e)
            return None
