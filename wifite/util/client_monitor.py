#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Client monitoring system for Evil Twin attacks.

Monitors connected clients to the rogue AP by parsing hostapd and
dnsmasq logs in real-time. Detects when clients connect/disconnect
and tracks their activity.
"""

import os
import time
import re
from threading import Thread, Lock
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class AttackStatistics:
    """
    Tracks statistics for an Evil Twin attack.
    
    Monitors client connections, credential attempts, success rate,
    and attack duration.
    """
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Client statistics
    total_clients_connected: int = 0
    unique_clients: set = field(default_factory=set)
    currently_connected: int = 0
    
    # Credential statistics
    total_credential_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    
    # Timing statistics
    first_client_time: Optional[float] = None
    first_credential_time: Optional[float] = None
    success_time: Optional[float] = None
    
    def record_client_connect(self, mac_address: str):
        """Record a client connection."""
        self.total_clients_connected += 1
        self.unique_clients.add(mac_address.upper())
        self.currently_connected += 1
        
        if self.first_client_time is None:
            self.first_client_time = time.time()
    
    def record_client_disconnect(self, mac_address: str):
        """Record a client disconnection."""
        if self.currently_connected > 0:
            self.currently_connected -= 1
    
    def record_credential_attempt(self, success: bool = False):
        """Record a credential submission attempt."""
        self.total_credential_attempts += 1
        
        if success:
            self.successful_attempts += 1
            if self.success_time is None:
                self.success_time = time.time()
        else:
            self.failed_attempts += 1
        
        if self.first_credential_time is None:
            self.first_credential_time = time.time()
    
    def get_success_rate(self) -> float:
        """
        Calculate credential success rate.
        
        Returns:
            Success rate as percentage (0-100)
        """
        if self.total_credential_attempts == 0:
            return 0.0
        return (self.successful_attempts / self.total_credential_attempts) * 100
    
    def get_duration(self) -> float:
        """
        Get attack duration in seconds.
        
        Returns:
            Duration in seconds
        """
        end = self.end_time or time.time()
        return end - self.start_time
    
    def get_time_to_first_client(self) -> Optional[float]:
        """
        Get time until first client connected.
        
        Returns:
            Time in seconds or None if no clients
        """
        if self.first_client_time is None:
            return None
        return self.first_client_time - self.start_time
    
    def get_time_to_first_credential(self) -> Optional[float]:
        """
        Get time until first credential attempt.
        
        Returns:
            Time in seconds or None if no attempts
        """
        if self.first_credential_time is None:
            return None
        return self.first_credential_time - self.start_time
    
    def get_time_to_success(self) -> Optional[float]:
        """
        Get time until successful credential capture.
        
        Returns:
            Time in seconds or None if no success
        """
        if self.success_time is None:
            return None
        return self.success_time - self.start_time
    
    def get_unique_client_count(self) -> int:
        """Get count of unique clients."""
        return len(self.unique_clients)
    
    def mark_complete(self):
        """Mark attack as complete."""
        if self.end_time is None:
            self.end_time = time.time()
    
    def to_dict(self) -> dict:
        """
        Convert statistics to dictionary.
        
        Returns:
            Dictionary with all statistics
        """
        return {
            'duration': self.get_duration(),
            'total_clients': self.total_clients_connected,
            'unique_clients': self.get_unique_client_count(),
            'currently_connected': self.currently_connected,
            'credential_attempts': self.total_credential_attempts,
            'successful_attempts': self.successful_attempts,
            'failed_attempts': self.failed_attempts,
            'success_rate': self.get_success_rate(),
            'time_to_first_client': self.get_time_to_first_client(),
            'time_to_first_credential': self.get_time_to_first_credential(),
            'time_to_success': self.get_time_to_success()
        }
    
    def __str__(self) -> str:
        """String representation of statistics."""
        lines = []
        lines.append(f"Duration: {self.get_duration():.1f}s")
        lines.append(f"Clients: {self.total_clients_connected} total, {self.get_unique_client_count()} unique, {self.currently_connected} connected")
        lines.append(f"Credentials: {self.total_credential_attempts} attempts, {self.successful_attempts} successful ({self.get_success_rate():.1f}%)")
        
        if self.get_time_to_first_client():
            lines.append(f"Time to first client: {self.get_time_to_first_client():.1f}s")
        if self.get_time_to_success():
            lines.append(f"Time to success: {self.get_time_to_success():.1f}s")
        
        return "\n".join(lines)


@dataclass
class ClientConnection:
    """
    Represents a client connected to the rogue AP.
    
    Tracks MAC address, IP, hostname, connection time, and
    credential submission status.
    """
    mac_address: str
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    connect_time: float = field(default_factory=time.time)
    disconnect_time: Optional[float] = None
    credential_submitted: bool = False
    credential_valid: Optional[bool] = None
    last_seen: float = field(default_factory=time.time)
    
    def is_connected(self) -> bool:
        """Check if client is currently connected."""
        return self.disconnect_time is None
    
    def connection_duration(self) -> float:
        """Get connection duration in seconds."""
        end_time = self.disconnect_time or time.time()
        return end_time - self.connect_time
    
    def __str__(self):
        status = "Connected" if self.is_connected() else "Disconnected"
        ip_str = f" ({self.ip_address})" if self.ip_address else ""
        return f"{self.mac_address}{ip_str} - {status}"


class ClientMonitor(Thread):
    """
    Monitors clients connecting to the rogue AP.
    
    Parses hostapd logs for connection/disconnection events and
    dnsmasq logs for DHCP leases to track client IP addresses.
    """
    
    def __init__(self, hostapd_log_path: str = None, dnsmasq_log_path: str = None):
        """
        Initialize client monitor.
        
        Args:
            hostapd_log_path: Path to hostapd log file
            dnsmasq_log_path: Path to dnsmasq log file
        """
        super().__init__()
        self.daemon = True
        
        self.hostapd_log_path = hostapd_log_path
        self.dnsmasq_log_path = dnsmasq_log_path
        
        # Client tracking
        self.clients: Dict[str, ClientConnection] = {}
        self.clients_lock = Lock()
        
        # Callbacks
        self.on_client_connect: Optional[Callable[[ClientConnection], None]] = None
        self.on_client_disconnect: Optional[Callable[[ClientConnection], None]] = None
        self.on_client_dhcp: Optional[Callable[[ClientConnection], None]] = None
        
        # Monitoring state
        self.running = False
        self.hostapd_file_pos = 0
        self.dnsmasq_file_pos = 0
        
        # Statistics tracking
        self.statistics = AttackStatistics()
        
        # Legacy statistics (kept for backward compatibility)
        self.total_connections = 0
        self.total_disconnections = 0
        
    def run(self):
        """Main monitoring loop."""
        self.running = True
        
        while self.running:
            try:
                # Monitor hostapd log for connections/disconnections
                if self.hostapd_log_path and os.path.exists(self.hostapd_log_path):
                    self._monitor_hostapd_log()
                
                # Monitor dnsmasq log for DHCP leases
                if self.dnsmasq_log_path and os.path.exists(self.dnsmasq_log_path):
                    self._monitor_dnsmasq_log()
                
                # Clean up old disconnected clients
                self._cleanup_old_clients()
                
                time.sleep(0.5)
                
            except Exception as e:
                from ..util.logger import log_error
                log_error('ClientMonitor', f'Error in monitoring loop: {e}', e)
                time.sleep(1)
    
    def _monitor_hostapd_log(self):
        """Monitor hostapd log for client events."""
        try:
            with open(self.hostapd_log_path, 'r') as f:
                # Seek to last position
                f.seek(self.hostapd_file_pos)
                
                # Read new lines
                lines = f.readlines()
                self.hostapd_file_pos = f.tell()
                
                for line in lines:
                    self._parse_hostapd_line(line)
                    
        except Exception as e:
            from ..util.logger import log_debug
            log_debug('ClientMonitor', f'Error reading hostapd log: {e}')
    
    def _parse_hostapd_line(self, line: str):
        """
        Parse a line from hostapd log to detect client events.
        
        Hostapd logs client connections and disconnections in various formats
        depending on the version and configuration. This method handles multiple
        patterns to ensure compatibility across different hostapd versions.
        
        Supported patterns:
        1. AP-STA-CONNECTED <MAC>     - Standard connection event
        2. AP-STA-DISCONNECTED <MAC>  - Standard disconnection event
        3. <MAC> associated (aid N)   - Alternative connection format
        4. <MAC> disassociated        - Alternative disconnection format
        
        Args:
            line: Single line from hostapd log file
            
        The MAC address is extracted using regex and normalized to uppercase
        for consistent tracking across the system.
        """
        try:
            # Primary connection pattern: "AP-STA-CONNECTED 00:11:22:33:44:55"
            # This is the most reliable indicator of a successful connection
            connect_match = re.search(r'AP-STA-CONNECTED\s+([0-9a-fA-F:]{17})', line)
            if connect_match:
                mac = connect_match.group(1).upper()
                self._handle_client_connect(mac)
                return
            
            # Primary disconnection pattern: "AP-STA-DISCONNECTED 00:11:22:33:44:55"
            # Indicates client has disconnected from the AP
            disconnect_match = re.search(r'AP-STA-DISCONNECTED\s+([0-9a-fA-F:]{17})', line)
            if disconnect_match:
                mac = disconnect_match.group(1).upper()
                self._handle_client_disconnect(mac)
                return
            
            # Alternative connection pattern: "00:11:22:33:44:55 associated (aid 1)"
            # Some hostapd versions use this format instead
            # The "aid" (association ID) is assigned by the AP
            assoc_match = re.search(r'associated\s+\(aid\s+\d+\).*?([0-9a-fA-F:]{17})', line, re.IGNORECASE)
            if assoc_match:
                mac = assoc_match.group(1).upper()
                self._handle_client_connect(mac)
                return
            
            # Alternative disconnection pattern: "00:11:22:33:44:55 disassociated"
            # Matches various disassociation messages
            disassoc_match = re.search(r'disassociated.*?([0-9a-fA-F:]{17})', line, re.IGNORECASE)
            if disassoc_match:
                mac = disassoc_match.group(1).upper()
                self._handle_client_disconnect(mac)
                return
                
        except Exception as e:
            from ..util.logger import log_debug
            log_debug('ClientMonitor', f'Error parsing hostapd line: {e}')
    
    def _monitor_dnsmasq_log(self):
        """Monitor dnsmasq log for DHCP leases."""
        try:
            with open(self.dnsmasq_log_path, 'r') as f:
                # Seek to last position
                f.seek(self.dnsmasq_file_pos)
                
                # Read new lines
                lines = f.readlines()
                self.dnsmasq_file_pos = f.tell()
                
                for line in lines:
                    self._parse_dnsmasq_line(line)
                    
        except Exception as e:
            from ..util.logger import log_debug
            log_debug('ClientMonitor', f'Error reading dnsmasq log: {e}')
    
    def _parse_dnsmasq_line(self, line: str):
        """
        Parse a line from dnsmasq log to extract DHCP lease information.
        
        Dnsmasq logs DHCP transactions including IP address assignments and
        client hostnames. This information is crucial for:
        - Identifying clients by IP address (for portal access)
        - Displaying meaningful client names in the UI
        - Correlating network activity with specific clients
        
        DHCP ACK pattern format:
        DHCPACK(interface) IP_ADDRESS MAC_ADDRESS [HOSTNAME]
        
        Example:
        DHCPACK(wlan0) 192.168.100.10 00:11:22:33:44:55 android-phone
        
        Args:
            line: Single line from dnsmasq log file
            
        The hostname is optional - some clients don't provide one.
        When present, it's typically the device name (e.g., "iPhone", "DESKTOP-ABC123").
        """
        try:
            # DHCP ACK pattern: "DHCPACK(wlan0) 192.168.100.10 00:11:22:33:44:55 hostname"
            # This indicates a successful DHCP lease assignment
            # Components:
            #   - Interface name in parentheses (not captured, varies)
            #   - IP address assigned to client
            #   - Client MAC address
            #   - Optional hostname provided by client
            dhcp_match = re.search(
                r'DHCPACK\([^)]+\)\s+(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]{17})(?:\s+(.+))?',
                line
            )
            if dhcp_match:
                ip = dhcp_match.group(1)          # Assigned IP address
                mac = dhcp_match.group(2).upper() # Client MAC (normalized to uppercase)
                # Hostname is optional - strip whitespace if present
                hostname = dhcp_match.group(3).strip() if dhcp_match.group(3) else None
                
                self._handle_client_dhcp(mac, ip, hostname)
                return
                
        except Exception as e:
            from ..util.logger import log_debug
            log_debug('ClientMonitor', f'Error parsing dnsmasq line: {e}')
    
    def _handle_client_connect(self, mac: str):
        """Handle client connection event."""
        with self.clients_lock:
            if mac not in self.clients or not self.clients[mac].is_connected():
                # New connection or reconnection
                client = ClientConnection(mac_address=mac)
                self.clients[mac] = client
                self.total_connections += 1
                
                # Record statistics
                self.statistics.record_client_connect(mac)
                
                from ..util.logger import log_info
                log_info('ClientMonitor', f'Client connected: {mac}')
                
                # Trigger callback
                if self.on_client_connect:
                    try:
                        self.on_client_connect(client)
                    except Exception as e:
                        from ..util.logger import log_error
                        log_error('ClientMonitor', f'Error in connect callback: {e}', e)
            else:
                # Update last seen time
                self.clients[mac].last_seen = time.time()
    
    def _handle_client_disconnect(self, mac: str):
        """Handle client disconnection event."""
        with self.clients_lock:
            if mac in self.clients and self.clients[mac].is_connected():
                client = self.clients[mac]
                client.disconnect_time = time.time()
                self.total_disconnections += 1
                
                # Record statistics
                self.statistics.record_client_disconnect(mac)
                
                from ..util.logger import log_info
                log_info('ClientMonitor', f'Client disconnected: {mac}')
                
                # Trigger callback
                if self.on_client_disconnect:
                    try:
                        self.on_client_disconnect(client)
                    except Exception as e:
                        from ..util.logger import log_error
                        log_error('ClientMonitor', f'Error in disconnect callback: {e}', e)
    
    def _handle_client_dhcp(self, mac: str, ip: str, hostname: Optional[str]):
        """Handle DHCP lease event."""
        with self.clients_lock:
            if mac in self.clients:
                client = self.clients[mac]
                client.ip_address = ip
                client.hostname = hostname
                client.last_seen = time.time()
                
                from ..util.logger import log_info
                log_info('ClientMonitor', f'Client DHCP: {mac} -> {ip} ({hostname})')
                
                # Trigger callback
                if self.on_client_dhcp:
                    try:
                        self.on_client_dhcp(client)
                    except Exception as e:
                        from ..util.logger import log_error
                        log_error('ClientMonitor', f'Error in DHCP callback: {e}', e)
    
    def _cleanup_old_clients(self, max_age: int = 3600):
        """
        Remove old disconnected clients from tracking.
        
        Args:
            max_age: Maximum age in seconds for disconnected clients
        """
        with self.clients_lock:
            current_time = time.time()
            to_remove = []
            
            for mac, client in self.clients.items():
                if not client.is_connected():
                    age = current_time - (client.disconnect_time or client.last_seen)
                    if age > max_age:
                        to_remove.append(mac)
            
            for mac in to_remove:
                del self.clients[mac]
    
    def get_connected_clients(self) -> List[ClientConnection]:
        """
        Get list of currently connected clients.
        
        Returns:
            List of ClientConnection objects
        """
        with self.clients_lock:
            return [client for client in self.clients.values() if client.is_connected()]
    
    def get_all_clients(self) -> List[ClientConnection]:
        """
        Get list of all clients (connected and disconnected).
        
        Returns:
            List of ClientConnection objects
        """
        with self.clients_lock:
            return list(self.clients.values())
    
    def get_client(self, mac: str) -> Optional[ClientConnection]:
        """
        Get client by MAC address.
        
        Args:
            mac: Client MAC address
            
        Returns:
            ClientConnection or None
        """
        with self.clients_lock:
            return self.clients.get(mac.upper())
    
    def has_connected_clients(self) -> bool:
        """Check if any clients are currently connected."""
        return len(self.get_connected_clients()) > 0
    
    def record_credential_attempt(self, mac_address: str, success: bool = False):
        """
        Record a credential submission attempt.
        
        Args:
            mac_address: MAC address of client submitting credentials
            success: Whether the credentials were valid
        """
        with self.clients_lock:
            # Update client record (don't call get_client as it would try to acquire the lock again)
            mac_upper = mac_address.upper()
            client = self.clients.get(mac_upper)
            if client:
                client.credential_submitted = True
                client.credential_valid = success
            
            # Update statistics
            self.statistics.record_credential_attempt(success)
            
            from ..util.logger import log_info
            status = "successful" if success else "failed"
            log_info('ClientMonitor', f'Credential attempt {status}: {mac_address}')
    
    def get_statistics(self) -> AttackStatistics:
        """
        Get attack statistics.
        
        Returns:
            AttackStatistics object
        """
        # Update currently connected count
        with self.clients_lock:
            self.statistics.currently_connected = len([c for c in self.clients.values() if c.is_connected()])
        
        return self.statistics
    
    def get_stats(self) -> dict:
        """
        Get monitoring statistics (legacy method).
        
        Returns:
            Dictionary with statistics
        """
        with self.clients_lock:
            connected = len([c for c in self.clients.values() if c.is_connected()])
            return {
                'total_connections': self.total_connections,
                'total_disconnections': self.total_disconnections,
                'currently_connected': connected,
                'total_tracked': len(self.clients)
            }
    
    def get_detailed_stats(self) -> dict:
        """
        Get detailed attack statistics.
        
        Returns:
            Dictionary with comprehensive statistics
        """
        stats = self.statistics.to_dict()
        
        # Add client-specific stats
        with self.clients_lock:
            clients_with_credentials = len([c for c in self.clients.values() if c.credential_submitted])
            clients_with_valid_credentials = len([c for c in self.clients.values() if c.credential_valid])
            
            stats['clients_submitted_credentials'] = clients_with_credentials
            stats['clients_valid_credentials'] = clients_with_valid_credentials
        
        return stats
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        
        # Mark statistics as complete
        self.statistics.mark_complete()
        
        # Wait for thread to finish
        if self.is_alive():
            self.join(timeout=2)
