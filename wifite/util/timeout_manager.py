#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Intelligent timeout management system with adaptive strategies
"""

import time
import threading
from ..util.color import Color
from ..config import Configuration

class AdaptiveTimeoutManager(object):
    '''Manages timeouts adaptively based on network conditions'''

    def __init__(self):
        self.timeouts = {}
        self.start_times = {}
        self.lock = threading.Lock()
        self.recovery_count = {}

    def start_timer(self, task_id, timeout_duration):
        '''Start a new timer for a task'''
        with self.lock:
            self.start_times[task_id] = time.time()
            self.timeouts[task_id] = timeout_duration
            self.recovery_count[task_id] = 0
            
        Color.pl('{*} {C}Started timer {W}{C}%s{W} ({G}%ds{W})' % 
                (task_id, timeout_duration))

    def is_timeout(self, task_id):
        '''Check if task has timed out'''
        if task_id not in self.start_times:
            return False
            
        elapsed = time.time() - self.start_times[task_id]
        timeout = self.timeouts.get(task_id, 60)
        
        if elapsed > timeout:
            Color.pl('{!} {O}Task {C}%s{O} timed out after {G}%.2f{W}s' % 
                    (task_id, elapsed))
            return True
        return False

    def get_remaining_time(self, task_id):
        '''Get remaining time for a task'''
        if task_id not in self.start_times:
            return 0
            
        elapsed = time.time() - self.start_times[task_id]
        timeout = self.timeouts.get(task_id, 60)
        remaining = max(0, timeout - elapsed)
        return remaining

    def adjust_timeout(self, task_id, new_timeout):
        '''Adjust timeout for a running task'''
        with self.lock:
            if task_id in self.timeouts:
                self.timeouts[task_id] = new_timeout
                Color.pl('{+} Adjusted timeout for {C}%s{W} to {G}%ds{W}' % 
                        (task_id, new_timeout))

    def extend_timeout(self, task_id, extension_seconds):
        '''Extend timeout by additional seconds'''
        with self.lock:
            if task_id in self.start_times:
                # Reset start time to extend deadline
                self.start_times[task_id] = time.time() - (
                    self.timeouts[task_id] - extension_seconds
                )
                Color.pl('{+} Extended timeout for {C}%s{W} by {G}%ds{W}' % 
                        (task_id, extension_seconds))

    def stop_timer(self, task_id):
        '''Stop and remove a timer'''
        with self.lock:
            if task_id in self.start_times:
                elapsed = time.time() - self.start_times[task_id]
                del self.start_times[task_id]
                del self.timeouts[task_id]
                Color.pl('{+} Stopped timer {C}%s{W} after {G}%.2f{W}s' % 
                        (task_id, elapsed))

    def calculate_adaptive_timeout(self, base_timeout, failure_count):
        '''Calculate adaptive timeout based on failure count'''
        # Exponential backoff: each failure increases timeout
        multiplier = 1 + (0.5 * failure_count)
        adaptive = int(base_timeout * multiplier)
        
        # Cap at maximum
        max_timeout = base_timeout * 5
        return min(adaptive, max_timeout)


class TimeoutRetryStrategy(object):
    '''Implements intelligent retry strategies for timeout scenarios'''

    def __init__(self, max_retries=5, initial_backoff=1):
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.current_retry = 0
        self.backoff_multiplier = 1.5

    def should_retry(self):
        '''Determine if we should retry'''
        return self.current_retry < self.max_retries

    def get_backoff_delay(self):
        '''Get delay before next retry'''
        delay = self.initial_backoff * (self.backoff_multiplier ** self.current_retry)
        return min(delay, 60)  # Cap at 60 seconds

    def execute_with_retry(self, func, *args, **kwargs):
        '''Execute function with retry logic'''
        while self.should_retry():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.current_retry += 1
                
                if self.should_retry():
                    backoff = self.get_backoff_delay()
                    Color.pl('{!} {O}Error ({W}{R}%s{O}), retry {G}%d{W}/{G}%d{W}' % 
                            (str(e)[:30], self.current_retry, self.max_retries))
                    Color.pl('{*} {C}Backing off for {G}%.1f{W}s...' % backoff)
                    time.sleep(backoff)
                else:
                    Color.pl('{!} {R}Max retries exceeded{W}')
                    raise

        raise RuntimeError('All retry attempts failed')


class ConnectionTimeoutHandler(object):
    '''Handles connection timeouts specifically'''

    def __init__(self):
        self.socket_timeout = Configuration.socket_timeout
        self.connection_timeout = Configuration.connection_timeout
        self.read_timeout = Configuration.read_timeout

    def set_socket_timeouts(self, sock):
        '''Configure socket with optimized timeouts'''
        sock.settimeout(self.socket_timeout)
        return sock

    def handle_connection_timeout(self, host, port):
        '''Handle connection timeout to specific host:port'''
        Color.pl('{!} {O}Connection timeout to {W}%s:%d' % (host, port))
        
        # Try alternative strategies
        strategies = [
            ('reducing_packet_size', self._reduce_packet_size),
            ('changing_port', self._try_alternative_port),
            ('adjusting_timeout', self._increase_timeout)
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                Color.pl('{*} {C}Trying strategy: {W}%s' % strategy_name)
                return strategy_func(host, port)
            except Exception as e:
                Color.pl('{!} {O}Strategy failed: %s' % str(e))
                
        return False

    def _reduce_packet_size(self, host, port):
        '''Attempt connection with reduced packet sizes'''
        pass

    def _try_alternative_port(self, host, port):
        '''Try alternative ports'''
        pass

    def _increase_timeout(self, host, port):
        '''Increase timeout for connection'''
        pass


class PerformanceMonitor(object):
    '''Monitors performance metrics for optimization decisions'''

    def __init__(self):
        self.metrics = {
            'packets_per_second': 0,
            'success_rate': 0,
            'average_response_time': 0,
            'timeout_count': 0,
            'retry_count': 0
        }
        self.start_time = time.time()

    def record_packet(self):
        '''Record packet transmission'''
        self.metrics['packets_per_second'] += 1

    def record_success(self):
        '''Record successful operation'''
        self.metrics['success_rate'] = (self.metrics.get('success_rate', 0) + 1)

    def record_timeout(self):
        '''Record timeout occurrence'''
        self.metrics['timeout_count'] += 1

    def get_performance_report(self):
        '''Get formatted performance report'''
        elapsed = time.time() - self.start_time
        pps = self.metrics['packets_per_second'] / elapsed if elapsed > 0 else 0
        
        report = f"""
{Color.s('{C}[*] Performance Report:{W}')}
  Packets/sec: {Color.s('{G}%.2f{W}' % pps)}
  Timeouts: {Color.s('{R}%d{W}' % self.metrics['timeout_count'])}
  Retries: {Color.s('{O}%d{W}' % self.metrics['retry_count'])}
  Elapsed: {Color.s('{G}%.2f{W}' % elapsed)}s
"""
        return report
