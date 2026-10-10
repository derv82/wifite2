#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Adaptive deauthentication manager for Evil Twin attacks.

Optimizes deauth timing based on client behavior and connection patterns
to maximize effectiveness while minimizing detection risk.
"""

import time
from ..util.logger import log_info, log_debug


class AdaptiveDeauthManager:
    """
    Manages adaptive deauthentication timing for Evil Twin attacks.
    
    Features:
    - Adaptive intervals based on client connection success
    - Smart targeting (broadcast vs targeted deauth)
    - Automatic pause when clients connect to rogue AP
    - Reduced intervals when clients are actively connecting
    - Increased intervals when no activity detected
    """
    
    def __init__(self, base_interval=5.0, min_interval=2.0, max_interval=15.0):
        """
        Initialize adaptive deauth manager.
        
        Args:
            base_interval: Base deauth interval in seconds (default: 5.0)
            min_interval: Minimum interval in seconds (default: 2.0)
            max_interval: Maximum interval in seconds (default: 15.0)
        """
        self.base_interval = base_interval
        self.min_interval = min_interval
        self.max_interval = max_interval
        
        # Current adaptive interval
        self.current_interval = base_interval
        
        # Statistics for adaptation
        self.total_deauths_sent = 0
        self.clients_connected = 0
        self.last_client_connect_time = 0
        self.consecutive_no_connects = 0
        
        # Timing
        self.last_deauth_time = time.time()  # Initialize to current time
        self.attack_start_time = time.time()
        
        # State
        self.is_paused = False
        
        log_info('AdaptiveDeauth', f'Initialized with base interval {base_interval}s')
    
    def should_send_deauth(self) -> bool:
        """
        Determine if a deauth should be sent now based on adaptive timing.
        
        Returns:
            True if deauth should be sent, False otherwise
        """
        if self.is_paused:
            return False
        
        current_time = time.time()
        time_since_last = current_time - self.last_deauth_time
        
        return time_since_last >= self.current_interval
    
    def record_deauth_sent(self):
        """Record that a deauth was sent and update timing."""
        self.last_deauth_time = time.time()
        self.total_deauths_sent += 1
        
        log_debug('AdaptiveDeauth', 
                 f'Deauth sent (total: {self.total_deauths_sent}, interval: {self.current_interval:.1f}s)')
    
    def record_client_connect(self):
        """
        Record that a client connected to the rogue AP.
        
        This triggers:
        - Reduction of deauth interval (more aggressive)
        - Reset of consecutive no-connect counter
        """
        self.clients_connected += 1
        self.last_client_connect_time = time.time()
        self.consecutive_no_connects = 0
        
        # Reduce interval when clients are connecting (they're vulnerable)
        self._reduce_interval()
        
        log_info('AdaptiveDeauth', 
                f'Client connected (total: {self.clients_connected}), reducing interval to {self.current_interval:.1f}s')
    
    def record_no_activity(self):
        """
        Record that no clients have connected recently.
        
        This triggers:
        - Increase of deauth interval (less aggressive, more stealthy)
        - Increment of consecutive no-connect counter
        """
        self.consecutive_no_connects += 1
        
        # Increase interval when no activity (save resources, reduce detection)
        if self.consecutive_no_connects >= 3:
            self._increase_interval()
            log_debug('AdaptiveDeauth', 
                     f'No activity detected, increasing interval to {self.current_interval:.1f}s')
    
    def pause(self):
        """Pause deauth (typically when clients are connected to rogue AP)."""
        if not self.is_paused:
            self.is_paused = True
            log_info('AdaptiveDeauth', 'Deauth paused')
    
    def resume(self):
        """Resume deauth (typically when no clients are connected to rogue AP)."""
        if self.is_paused:
            self.is_paused = False
            log_info('AdaptiveDeauth', 'Deauth resumed')
    
    def _reduce_interval(self):
        """Reduce deauth interval (more aggressive)."""
        # Reduce by 20% but don't go below minimum
        self.current_interval = max(
            self.min_interval,
            self.current_interval * 0.8
        )
    
    def _increase_interval(self):
        """Increase deauth interval (less aggressive, more stealthy)."""
        # Increase by 25% but don't exceed maximum
        self.current_interval = min(
            self.max_interval,
            self.current_interval * 1.25
        )
    
    def reset_to_base(self):
        """Reset interval to base value."""
        self.current_interval = self.base_interval
        log_debug('AdaptiveDeauth', f'Reset interval to base: {self.base_interval}s')
    
    def get_current_interval(self) -> float:
        """
        Get current adaptive interval.
        
        Returns:
            Current interval in seconds
        """
        return self.current_interval
    
    def get_statistics(self) -> dict:
        """
        Get deauth statistics.
        
        Returns:
            Dictionary with statistics
        """
        elapsed = time.time() - self.attack_start_time
        
        return {
            'total_deauths_sent': self.total_deauths_sent,
            'clients_connected': self.clients_connected,
            'current_interval': self.current_interval,
            'is_paused': self.is_paused,
            'consecutive_no_connects': self.consecutive_no_connects,
            'elapsed_time': elapsed,
            'deauths_per_minute': (self.total_deauths_sent / elapsed * 60) if elapsed > 0 else 0
        }
    
    def should_use_targeted_deauth(self, known_clients: list) -> bool:
        """
        Determine if targeted deauth should be used instead of broadcast.
        
        Targeted deauth is more effective but requires knowing client MACs.
        Use it when we have identified clients.
        
        Args:
            known_clients: List of known client MAC addresses
            
        Returns:
            True if targeted deauth should be used, False for broadcast
        """
        # Use targeted deauth if we have known clients
        # and we've sent enough broadcast deauths without success
        if known_clients and len(known_clients) > 0:
            if self.total_deauths_sent > 10 and self.clients_connected == 0:
                # Tried broadcast, not working, switch to targeted
                return True
            elif self.clients_connected > 0:
                # Targeted works better once we know clients are responsive
                return True
        
        return False
    
    def get_recommended_deauth_count(self) -> int:
        """
        Get recommended number of deauth packets to send per burst.
        
        Returns:
            Number of deauth packets (typically 5-20)
        """
        # Start with more packets, reduce as clients connect
        if self.clients_connected == 0:
            # No clients yet, be aggressive
            return 15
        elif self.clients_connected < 3:
            # Some clients, moderate
            return 10
        else:
            # Multiple clients, be conservative
            return 5
