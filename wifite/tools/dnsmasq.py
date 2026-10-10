#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dnsmasq tool wrapper for DHCP and DNS services.
Used by Evil Twin attack to provide network services to connected clients.
"""

import os
import time
import tempfile
from typing import Optional, List

from .dependency import Dependency
from ..config import Configuration
from ..util.process import Process
from ..util.color import Color
from ..util.logger import log_info, log_error, log_warning, log_debug


class Dnsmasq(Dependency):
    """
    Wrapper for dnsmasq to provide DHCP and DNS services.
    """

    dependency_required = True
    dependency_name = 'dnsmasq'
    dependency_url = 'http://www.thekelleys.org.uk/dnsmasq/doc.html'

    def __init__(self, interface, gateway_ip='192.168.100.1', 
                 dhcp_range_start='192.168.100.10', 
                 dhcp_range_end='192.168.100.100',
                 portal_ip=None):
        """
        Initialize Dnsmasq configuration.

        Args:
            interface: Network interface to serve on
            gateway_ip: IP address of the gateway (rogue AP)
            dhcp_range_start: Start of DHCP range
            dhcp_range_end: End of DHCP range
            portal_ip: IP address to redirect DNS queries to (defaults to gateway_ip)
        """
        from ..config.validators import validate_interface_name
        validate_interface_name(interface)
        self.interface = interface
        self.gateway_ip = gateway_ip
        self.dhcp_range_start = dhcp_range_start
        self.dhcp_range_end = dhcp_range_end
        self.portal_ip = portal_ip or gateway_ip

        self.config_file = None
        self.lease_file = None
        self.process = None
        self.running = False

        log_debug('Dnsmasq', f'Initialized for {interface} with gateway {gateway_ip}')

    def generate_config(self) -> str:
        """
        Generate dnsmasq configuration file content.

        Returns:
            Configuration file content as string
        """
        config = []

        # Interface to listen on
        config.append(f'interface={self.interface}')
        # Never bind loopback. Without this dnsmasq still binds 127.0.0.1:53 by
        # default, which collides with a host resolver (systemd-resolved /
        # another dnsmasq) and makes startup fail with "Address already in use".
        config.append('except-interface=lo')

        # Don't read /etc/resolv.conf or /etc/hosts
        config.append('no-resolv')
        config.append('no-hosts')
        
        # Don't forward queries to upstream DNS
        config.append('no-poll')
        
        # DHCP configuration
        config.append(f'dhcp-range={self.dhcp_range_start},{self.dhcp_range_end},12h')
        
        # DHCP options
        # Option 3: Router (gateway)
        config.append(f'dhcp-option=3,{self.gateway_ip}')
        
        # Option 6: DNS server
        config.append(f'dhcp-option=6,{self.gateway_ip}')
        
        # Option 1: Subnet mask
        config.append('dhcp-option=1,255.255.255.0')
        
        # DHCP authoritative mode
        config.append('dhcp-authoritative')
        
        # DNS configuration - redirect all queries to portal
        config.append(f'address=/#/{self.portal_ip}')
        
        # Lease file (always use the secure temp file created in create_config_file)
        if self.lease_file:
            config.append(f'dhcp-leasefile={self.lease_file}')
        
        # Logging
        config.append('log-queries')
        config.append('log-dhcp')
        
        # Don't use /etc/dnsmasq.conf
        config.append('conf-file=')
        
        # Bind to interface
        config.append('bind-interfaces')
        
        # Additional settings for stability
        config.append('bogus-priv')
        config.append('domain-needed')
        
        return '\n'.join(config) + '\n'
    
    def create_config_file(self) -> str:
        """
        Create temporary dnsmasq configuration file.
        
        Returns:
            Path to configuration file
        """
        try:
            # Create temp file for config
            fd, self.config_file = tempfile.mkstemp(
                prefix='dnsmasq_',
                suffix='.conf',
                dir=Configuration.temp()
            )
            
            # Write configuration
            config_content = self.generate_config()
            os.write(fd, config_content.encode('utf-8'))
            os.close(fd)
            
            # Set permissions
            os.chmod(self.config_file, 0o600)
            
            # Create lease file with restricted permissions
            fd_lease, self.lease_file = tempfile.mkstemp(
                prefix='dnsmasq_leases_',
                suffix='.txt',
                dir=Configuration.temp()
            )
            os.close(fd_lease)
            os.chmod(self.lease_file, 0o600)
            
            log_debug('Dnsmasq', f'Created config file: {self.config_file}')
            log_debug('Dnsmasq', f'Created lease file: {self.lease_file}')
            
            if Configuration.verbose > 1:
                Color.pl('{D}Dnsmasq config:{W}')
                for line in config_content.split('\n'):
                    if line.strip():
                        Color.pl('{D}  %s{W}' % line)
            
            return self.config_file
            
        except Exception as e:
            log_error('Dnsmasq', f'Failed to create config file: {e}', e)
            raise
    
    def start(self) -> bool:
        """
        Start dnsmasq process.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            if self.running:
                log_warning('Dnsmasq', 'Already running')
                return True

            # Create config file
            if not self.config_file:
                self.create_config_file()

            # Setup IP forwarding and routing
            self._setup_routing()

            # Start dnsmasq
            cmd = [
                'dnsmasq',
                '--conf-file=%s' % self.config_file,
                '--no-daemon'
            ]

            if Configuration.verbose > 0:
                Color.pl('{+} Starting dnsmasq: {D}%s{W}' % ' '.join(cmd))

            self.process = Process(cmd, devnull=False)

            # Wait a moment for startup
            time.sleep(1)

            # Check if process is running
            if self.process.poll() is not None:
                # Process died — dnsmasq reports startup errors on STDERR
                # (e.g. "failed to create listening socket ... Address already
                # in use"), so surface both streams to make failures diagnosable.
                out, err = self.process.get_output()
                detail = (err or '').strip() or (out or '').strip() or '(no output)'
                log_error('Dnsmasq', f'Failed to start: {detail}')
                Color.pl('{!} {R}Dnsmasq failed to start{W}')
                Color.pl('{!} {O}%s{W}' % detail)
                self._remove_temp_files()
                return False

            self.running = True
            log_info('Dnsmasq', f'Started successfully on {self.interface}')

            if Configuration.verbose > 0:
                Color.pl('{+} {G}Dnsmasq started{W} on {C}%s{W}' % self.interface)

            return True

        except Exception as e:
            log_error('Dnsmasq', f'Failed to start: {e}', e)
            Color.pl('{!} {R}Failed to start dnsmasq:{W} %s' % str(e))
            self._remove_temp_files()
            return False
    
    def _setup_routing(self):
        """Setup IP forwarding and routing rules."""
        try:
            # Enable IP forwarding
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('1\n')
            
            log_debug('Dnsmasq', 'Enabled IP forwarding')
            
            # Add iptables rules for NAT (optional, for internet access)
            # This is commented out by default as we typically want to
            # block internet access until credentials are validated
            
            # Get the internet-facing interface (not the AP interface)
            # internet_iface = self._get_internet_interface()
            # if internet_iface:
            #     Process(['iptables', '-t', 'nat', '-A', 'POSTROUTING', 
            #              '-o', internet_iface, '-j', 'MASQUERADE']).wait()
            #     Process(['iptables', '-A', 'FORWARD', '-i', self.interface, 
            #              '-o', internet_iface, '-j', 'ACCEPT']).wait()
            #     Process(['iptables', '-A', 'FORWARD', '-i', internet_iface, 
            #              '-o', self.interface, '-m', 'state', 
            #              '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT']).wait()
            
        except Exception as e:
            log_warning('Dnsmasq', f'Failed to setup routing: {e}')
    
    def _get_internet_interface(self) -> Optional[str]:
        """
        Get the interface with internet connectivity.
        
        Returns:
            Interface name or None
        """
        try:
            # Get default route
            output = Process(['ip', 'route', 'show', 'default']).stdout()
            
            for line in output.split('\n'):
                if 'default via' in line:
                    parts = line.split()
                    if 'dev' in parts:
                        idx = parts.index('dev')
                        if idx + 1 < len(parts):
                            iface = parts[idx + 1]
                            log_debug('Dnsmasq', f'Found internet interface: {iface}')
                            return iface
            
            return None
            
        except Exception as e:
            log_debug('Dnsmasq', f'Failed to get internet interface: {e}')
            return None
    
    def stop(self):
        """Stop dnsmasq process."""
        try:
            if not self.running:
                return
            
            if Configuration.verbose > 0:
                Color.pl('{+} Stopping dnsmasq...')
            
            # Stop process
            if self.process and self.process.poll() is None:
                self.process.interrupt()
                time.sleep(1)
                
                # Force kill if still running
                if self.process.poll() is None:
                    self.process.kill()
            
            self.running = False
            log_info('Dnsmasq', 'Stopped')
            
        except Exception as e:
            log_error('Dnsmasq', f'Error stopping dnsmasq: {e}', e)
    
    def _remove_temp_files(self):
        """Remove temporary config and lease files if they exist."""
        for label, attr in [('config', 'config_file'), ('lease', 'lease_file')]:
            path = getattr(self, attr, None)
            if path:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        log_debug('Dnsmasq', f'Removed {label} file: {path}')
                except OSError as e:
                    log_warning('Dnsmasq', f'Failed to remove {label} file: {e}')
                finally:
                    setattr(self, attr, None)

    def cleanup(self):
        """Cleanup dnsmasq resources."""
        try:
            # Stop process
            self.stop()

            # Cleanup routing
            self._cleanup_routing()

            # Remove temp files
            self._remove_temp_files()

            log_info('Dnsmasq', 'Cleanup complete')

        except Exception as e:
            log_error('Dnsmasq', f'Cleanup error: {e}', e)
    
    def _cleanup_routing(self):
        """Cleanup routing rules."""
        try:
            # Disable IP forwarding
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('0\n')
            
            log_debug('Dnsmasq', 'Disabled IP forwarding')
            
            # Remove iptables rules if they were added
            # This is commented out as we didn't add them in _setup_routing
            # internet_iface = self._get_internet_interface()
            # if internet_iface:
            #     Process(['iptables', '-t', 'nat', '-D', 'POSTROUTING', 
            #              '-o', internet_iface, '-j', 'MASQUERADE']).wait()
            #     Process(['iptables', '-D', 'FORWARD', '-i', self.interface, 
            #              '-o', internet_iface, '-j', 'ACCEPT']).wait()
            #     Process(['iptables', '-D', 'FORWARD', '-i', internet_iface, 
            #              '-o', self.interface, '-m', 'state', 
            #              '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT']).wait()
            
        except Exception as e:
            log_warning('Dnsmasq', f'Failed to cleanup routing: {e}')
    
    def is_running(self) -> bool:
        """
        Check if dnsmasq is running.
        
        Returns:
            True if running, False otherwise
        """
        if not self.process:
            return False
        
        return self.process.poll() is None
    
    def get_leases(self) -> List[dict]:
        """
        Get list of DHCP leases.
        
        Returns:
            List of lease dictionaries with keys: mac, ip, hostname, expiry
        """
        leases = []
        
        try:
            if not self.lease_file or not os.path.exists(self.lease_file):
                return leases
            
            with open(self.lease_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Dnsmasq lease format: timestamp mac ip hostname client-id
                    parts = line.split()
                    if len(parts) >= 4:
                        lease = {
                            'expiry': parts[0],
                            'mac': parts[1],
                            'ip': parts[2],
                            'hostname': parts[3] if len(parts) > 3 else '*',
                            'client_id': parts[4] if len(parts) > 4 else ''
                        }
                        leases.append(lease)
            
            return leases
            
        except Exception as e:
            log_debug('Dnsmasq', f'Failed to get leases: {e}')
            return []
    
    def get_connected_clients(self) -> List[str]:
        """
        Get list of connected client MAC addresses.
        
        Returns:
            List of MAC addresses
        """
        leases = self.get_leases()
        return [lease['mac'] for lease in leases]
    
    def get_client_info(self, mac_address: str) -> Optional[dict]:
        """
        Get information about a specific client.
        
        Args:
            mac_address: MAC address of the client
            
        Returns:
            Dictionary with client info or None if not found
        """
        leases = self.get_leases()
        
        for lease in leases:
            if lease['mac'].lower() == mac_address.lower():
                return lease
        
        return None
    
    def __del__(self):
        """Cleanup on deletion."""
        import contextlib
        with contextlib.suppress(Exception):
            self.cleanup()
