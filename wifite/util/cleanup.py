#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cleanup utilities for Evil Twin attacks.

Provides comprehensive cleanup of all attack resources including:
- Process termination
- Network interface restoration
- Temporary file removal
- iptables rule cleanup
"""

import os
import re
import signal
from typing import List, Tuple

from .process import Process
from .color import Color
from .logger import log_info, log_error, log_warning, log_debug


class CleanupManager:
    """
    Manages cleanup operations for Evil Twin attacks.
    
    Ensures all resources are properly released even if errors occur.
    """
    
    def __init__(self):
        """Initialize cleanup manager."""
        self.cleanup_errors = []
        self.processes_to_stop = []
        self.temp_files_to_remove = []
        self.interfaces_to_restore = []
        self.iptables_rules_added = []
        
    def register_process(self, process, name: str):
        """
        Register a process for cleanup.
        
        Args:
            process: Process object to stop
            name: Name of the process for logging
        """
        self.processes_to_stop.append((process, name))
        log_debug('Cleanup', f'Registered process for cleanup: {name}')
    
    def register_temp_file(self, filepath: str):
        """
        Register a temporary file for removal.
        
        Args:
            filepath: Path to temporary file
        """
        if filepath and filepath not in self.temp_files_to_remove:
            self.temp_files_to_remove.append(filepath)
            log_debug('Cleanup', f'Registered temp file for cleanup: {filepath}')
    
    def register_interface(self, interface: str, original_state: dict):
        """
        Register an interface for restoration.
        
        Args:
            interface: Interface name
            original_state: Original interface state dictionary
        """
        self.interfaces_to_restore.append((interface, original_state))
        log_debug('Cleanup', f'Registered interface for cleanup: {interface}')
    
    def register_iptables_rule(self, table: str, chain: str, rule: List[str]):
        """
        Register an iptables rule for removal.
        
        Args:
            table: iptables table (e.g., 'nat', 'filter', 'mangle')
            chain: iptables chain (e.g., 'PREROUTING', 'POSTROUTING')
            rule: Rule specification as list of arguments
        """
        self.iptables_rules_added.append((table, chain, rule))
        log_debug('Cleanup', f'Registered iptables rule for cleanup: {table}/{chain}')
    
    def stop_process(self, process, name: str) -> bool:
        """
        Stop a single process gracefully.
        
        Args:
            process: Process object to stop
            name: Name of the process for logging
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not process:
                return True
            
            log_debug('Cleanup', f'Stopping {name}')
            
            # Check if process has a stop method
            if hasattr(process, 'stop'):
                process.stop()
            elif hasattr(process, 'cleanup'):
                process.cleanup()
            elif hasattr(process, 'poll'):
                # It's a Process object
                if process.poll() is None:
                    # Process is still running
                    process.interrupt()
                    import time
                    time.sleep(1)
                    
                    # Force kill if still running
                    if process.poll() is None:
                        process.kill()
            
            log_info('Cleanup', f'Stopped {name}')
            return True
            
        except Exception as e:
            error_msg = f'{name}: {e}'
            self.cleanup_errors.append(error_msg)
            log_error('Cleanup', f'Failed to stop {name}: {e}', e)
            return False
    
    def stop_all_processes(self):
        """Stop all registered processes."""
        log_info('Cleanup', f'Stopping {len(self.processes_to_stop)} processes')
        
        for process, name in self.processes_to_stop:
            self.stop_process(process, name)
        
        self.processes_to_stop = []
    
    def remove_temp_file(self, filepath: str) -> bool:
        """
        Remove a single temporary file.
        
        Args:
            filepath: Path to file to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not filepath or not os.path.exists(filepath):
                return True
            
            os.remove(filepath)
            log_debug('Cleanup', f'Removed temp file: {filepath}')
            return True
            
        except Exception as e:
            error_msg = f'file {filepath}: {e}'
            self.cleanup_errors.append(error_msg)
            log_error('Cleanup', f'Failed to remove temp file {filepath}: {e}', e)
            return False
    
    def remove_all_temp_files(self):
        """Remove all registered temporary files."""
        log_info('Cleanup', f'Removing {len(self.temp_files_to_remove)} temp files')
        
        for filepath in self.temp_files_to_remove:
            self.remove_temp_file(filepath)
        
        self.temp_files_to_remove = []
    
    def restore_interface(self, interface: str, original_state: dict) -> bool:
        """
        Restore a network interface to its original state.

        Args:
            interface: Interface name
            original_state: Original state dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            from ..config.validators import validate_interface_name
            validate_interface_name(interface)
            log_debug('Cleanup', f'Restoring interface {interface}')
            
            # Bring interface down
            Process(['ip', 'link', 'set', interface, 'down']).wait()
            
            # Flush IP addresses
            Process(['ip', 'addr', 'flush', 'dev', interface]).wait()
            
            # Restore mode (default to managed)
            mode = original_state.get('mode', 'managed')
            if mode == 'AP':
                mode = 'managed'  # Don't restore to AP mode
            
            if mode == 'monitor':
                Process(['iw', interface, 'set', 'monitor', 'control']).wait()
            else:
                Process(['iw', interface, 'set', 'type', mode]).wait()
            
            # Bring interface up if it was originally up
            if original_state.get('up', False):
                Process(['ip', 'link', 'set', interface, 'up']).wait()
            
            log_info('Cleanup', f'Restored interface {interface}')
            return True
            
        except Exception as e:
            error_msg = f'interface {interface}: {e}'
            self.cleanup_errors.append(error_msg)
            log_error('Cleanup', f'Failed to restore interface {interface}: {e}', e)
            return False
    
    def restore_all_interfaces(self):
        """Restore all registered interfaces."""
        log_info('Cleanup', f'Restoring {len(self.interfaces_to_restore)} interfaces')
        
        for interface, original_state in self.interfaces_to_restore:
            self.restore_interface(interface, original_state)
        
        self.interfaces_to_restore = []
    
    def remove_iptables_rule(self, table: str, chain: str, rule: List[str]) -> bool:
        """
        Remove an iptables rule.
        
        Args:
            table: iptables table
            chain: iptables chain
            rule: Rule specification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build the delete command
            cmd = ['iptables', '-t', table, '-D', chain] + rule
            
            log_debug('Cleanup', f'Removing iptables rule: {" ".join(cmd)}')
            
            result = Process.run_simple(cmd)
            
            if result.returncode == 0:
                log_info('Cleanup', f'Removed iptables rule from {table}/{chain}')
                return True
            else:
                # Rule might not exist, which is okay
                log_debug('Cleanup', f'iptables rule not found (may have been removed): {result.stderr}')
                return True
            
        except Exception as e:
            error_msg = f'iptables {table}/{chain}: {e}'
            self.cleanup_errors.append(error_msg)
            log_error('Cleanup', f'Failed to remove iptables rule: {e}', e)
            return False
    
    def clear_all_iptables_rules(self):
        """Clear all registered iptables rules."""
        log_info('Cleanup', f'Clearing {len(self.iptables_rules_added)} iptables rules')
        
        for table, chain, rule in self.iptables_rules_added:
            self.remove_iptables_rule(table, chain, rule)
        
        self.iptables_rules_added = []
    
    def disable_ip_forwarding(self) -> bool:
        """
        Disable IP forwarding.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('0\n')
            
            log_info('Cleanup', 'Disabled IP forwarding')
            return True
            
        except Exception as e:
            error_msg = f'ip_forward: {e}'
            self.cleanup_errors.append(error_msg)
            log_warning('Cleanup', f'Failed to disable IP forwarding: {e}')
            return False
    
    def cleanup_all(self, display_status: bool = True) -> bool:
        """
        Perform complete cleanup of all registered resources.
        
        Args:
            display_status: Whether to display cleanup status messages
            
        Returns:
            True if cleanup completed without errors, False otherwise
        """
        if display_status:
            Color.pl('{+} {C}Cleaning up...{W}')
        
        log_info('Cleanup', 'Starting comprehensive cleanup')
        
        # Reset error list
        self.cleanup_errors = []
        
        # Stop all processes
        self.stop_all_processes()
        
        # Clear iptables rules
        self.clear_all_iptables_rules()
        
        # Disable IP forwarding
        self.disable_ip_forwarding()
        
        # Restore interfaces
        self.restore_all_interfaces()
        
        # Remove temporary files
        self.remove_all_temp_files()
        
        # Report status
        if self.cleanup_errors:
            if display_status:
                Color.pl('{!} {O}Cleanup completed with errors:{W}')
                for error in self.cleanup_errors:
                    Color.pl('    {!} {R}%s{W}' % error)
            log_warning('Cleanup', f'Cleanup completed with {len(self.cleanup_errors)} errors')
            return False
        else:
            if display_status:
                Color.pl('{+} {G}Cleanup complete{W}')
            log_info('Cleanup', 'Cleanup completed successfully')
            return True
    
    def get_errors(self) -> List[str]:
        """
        Get list of cleanup errors.
        
        Returns:
            List of error messages
        """
        return self.cleanup_errors.copy()


def kill_orphaned_processes() -> List[Tuple[str, str]]:
    """
    Find and kill orphaned processes from previous Evil Twin attacks.
    
    Returns:
        List of (process_name, pid) tuples that were killed
    """
    killed_processes = []
    
    log_info('Cleanup', 'Checking for orphaned processes')
    
    # Process patterns to search for
    patterns = [
        ('hostapd', 'hostapd.*wifite'),
        ('dnsmasq', 'dnsmasq.*wifite'),
        ('portal', 'python.*portal.*server'),
    ]
    
    for process_name, pattern in patterns:
        try:
            result = Process.run_simple(['pgrep', '-f', pattern])

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')

                for pid in pids:
                    try:
                        if not re.match(r'^\d+$', str(pid)):
                            log_warning('Cleanup', f'Skipping kill: invalid PID value: {pid!r}')
                            continue
                        pid_int = int(pid)
                        if pid_int <= 0:
                            log_warning('Cleanup', f'Skipping kill: non-positive PID: {pid_int}')
                            continue
                        os.kill(pid_int, signal.SIGTERM)
                        import time as _time
                        _time.sleep(0.3)
                        try:
                            os.kill(pid_int, 0)  # Check if still alive
                            os.kill(pid_int, signal.SIGKILL)
                            log_info('Cleanup', f'SIGKILL sent to {process_name} (PID: {pid}) after SIGTERM ignored')
                        except ProcessLookupError:
                            pass  # Process exited cleanly after SIGTERM
                        killed_processes.append((process_name, pid))
                        log_info('Cleanup', f'Killed orphaned {process_name} process (PID: {pid})')
                    except Exception as e:
                        log_warning('Cleanup', f'Failed to kill {process_name} process {pid}: {e}')

        except Exception as e:
            log_debug('Cleanup', f'Error checking for {process_name} processes: {e}')
    
    if killed_processes:
        log_warning('Cleanup', f'Killed {len(killed_processes)} orphaned processes')
    else:
        log_info('Cleanup', 'No orphaned processes found')
    
    return killed_processes


def check_conflicting_processes() -> List[Tuple[str, str]]:
    """
    Check for processes that may conflict with Evil Twin attack.
    
    Returns:
        List of (process_name, pid) tuples for conflicting processes
    """
    conflicting = []
    
    log_info('Cleanup', 'Checking for conflicting processes')
    
    # Process patterns that may conflict
    patterns = [
        ('NetworkManager', 'NetworkManager'),
        ('wpa_supplicant', 'wpa_supplicant'),
        ('hostapd', 'hostapd'),
        ('dnsmasq', 'dnsmasq'),
    ]
    
    for process_name, pattern in patterns:
        try:
            result = Process.run_simple(['pgrep', '-x', pattern])

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if re.match(r'^\d+$', str(pid)):
                        conflicting.append((process_name, pid))
                        log_debug('Cleanup', f'Found conflicting process: {process_name} (PID: {pid})')

        except Exception as e:
            log_debug('Cleanup', f'Error checking for {process_name}: {e}')
    
    if conflicting:
        log_warning('Cleanup', f'Found {len(conflicting)} conflicting processes')
    
    return conflicting
