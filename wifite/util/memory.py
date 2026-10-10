#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Memory monitoring and cleanup utilities for wifite2.

Provides periodic memory monitoring, automatic cleanup triggers,
and garbage collection for long-running operations like infinite mode.
"""

import gc
import os
import time
import threading
from typing import Optional, Dict, Any
from ..config import Configuration


class MemoryMonitor:
    """
    Memory monitoring utility for preventing memory bloat during long operations.

    Features:
    - Periodic memory usage checks
    - Automatic garbage collection triggers
    - File descriptor monitoring
    - Process cleanup coordination
    """

    # Memory thresholds (in MB)
    WARNING_THRESHOLD_MB = 500
    CRITICAL_THRESHOLD_MB = 1000

    # Cleanup intervals
    CLEANUP_INTERVAL_SCANS = 50  # Every N scan cycles
    GC_INTERVAL_SCANS = 100  # Force GC every N scan cycles

    # Lock for class-level state to prevent races from multiple threads
    _state_lock = threading.Lock()

    # State tracking
    _last_cleanup_time: float = 0
    _last_gc_time: float = 0
    _cleanup_count: int = 0
    _warning_shown: bool = False

    @classmethod
    def get_memory_usage_mb(cls) -> float:
        """
        Get current process memory usage in MB.

        Returns:
            Memory usage in MB, or -1 if unable to determine
        """
        try:
            # Try psutil first (most accurate)
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            pass

        try:
            # Fallback to /proc on Linux
            with open(f'/proc/{os.getpid()}/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        # VmRSS is in kB
                        kb = int(line.split()[1])
                        return kb / 1024
        except (FileNotFoundError, IOError, ValueError):
            pass

        return -1

    @classmethod
    def get_open_fd_count(cls) -> int:
        """
        Get current open file descriptor count.

        Returns:
            Number of open FDs, or -1 if unable to determine
        """
        try:
            proc_fd_dir = f'/proc/{os.getpid()}/fd'
            if os.path.exists(proc_fd_dir):
                return len(os.listdir(proc_fd_dir))
        except (OSError, IOError):
            pass
        return -1

    @classmethod
    def get_fd_limit(cls) -> tuple:
        """
        Get file descriptor limits.

        Returns:
            Tuple of (soft_limit, hard_limit), or (-1, -1) if unable to determine
        """
        try:
            import resource
            return resource.getrlimit(resource.RLIMIT_NOFILE)
        except (ImportError, OSError):
            return (-1, -1)

    @classmethod
    def check_memory_status(cls) -> Dict[str, Any]:
        """
        Check current memory and resource status.

        Returns:
            Dictionary with memory status information
        """
        memory_mb = cls.get_memory_usage_mb()
        fd_count = cls.get_open_fd_count()
        soft_limit, hard_limit = cls.get_fd_limit()

        status = {
            'memory_mb': memory_mb,
            'fd_count': fd_count,
            'fd_soft_limit': soft_limit,
            'fd_hard_limit': hard_limit,
            'fd_usage_percent': (fd_count / soft_limit * 100) if soft_limit > 0 and fd_count > 0 else 0,
            'memory_warning': memory_mb > cls.WARNING_THRESHOLD_MB if memory_mb > 0 else False,
            'memory_critical': memory_mb > cls.CRITICAL_THRESHOLD_MB if memory_mb > 0 else False,
            'fd_warning': (fd_count / soft_limit > 0.7) if soft_limit > 0 and fd_count > 0 else False,
        }

        return status

    @classmethod
    def periodic_check(cls, scan_count: int = 0) -> bool:
        """
        Perform periodic memory check and cleanup if needed.

        Should be called regularly during long-running operations.

        Args:
            scan_count: Current scan iteration count (for interval tracking)

        Returns:
            True if cleanup was performed, False otherwise
        """
        from ..util.color import Color

        performed_cleanup = False
        current_time = time.time()

        with cls._state_lock:
            # Check if it's time for periodic cleanup
            should_cleanup = (
                scan_count > 0 and scan_count % cls.CLEANUP_INTERVAL_SCANS == 0
            ) or (
                current_time - cls._last_cleanup_time > 60  # At least every 60 seconds
            )

            if not should_cleanup:
                return False

            cls._last_cleanup_time = current_time

        status = cls.check_memory_status()

        # Log status in verbose mode
        if Configuration.verbose > 1:
            Color.pl('{+} {D}Memory: %.1f MB, FDs: %d/%d (%.1f%%){W}' % (
                status['memory_mb'],
                status['fd_count'],
                status['fd_soft_limit'],
                status['fd_usage_percent']
            ))

        with cls._state_lock:
            # Critical memory - force aggressive cleanup
            if status['memory_critical']:
                if not cls._warning_shown:
                    Color.pl('{!} {R}Critical memory usage: %.1f MB{W}' % status['memory_mb'])
                    Color.pl('{!} {O}Triggering aggressive cleanup...{W}')
                    cls._warning_shown = True

                cls._aggressive_cleanup()
                performed_cleanup = True

            # High memory warning
            elif status['memory_warning']:
                if not cls._warning_shown:
                    Color.pl('{!} {O}High memory usage: %.1f MB{W}' % status['memory_mb'])
                    cls._warning_shown = True

                cls._standard_cleanup()
                performed_cleanup = True

            # High FD usage
            elif status['fd_warning']:
                if Configuration.verbose > 0:
                    Color.pl('{!} {O}High FD usage: %d/%d{W}' % (
                        status['fd_count'], status['fd_soft_limit']
                    ))

                cls._fd_cleanup()
                performed_cleanup = True

            # Periodic GC
            elif scan_count > 0 and scan_count % cls.GC_INTERVAL_SCANS == 0:
                collected = gc.collect()
                if Configuration.verbose > 1:
                    Color.pl('{+} {D}Periodic GC: collected %d objects{W}' % collected)
                performed_cleanup = True

            # Reset warning flag if memory is back to normal
            if not status['memory_warning'] and not status['memory_critical']:
                cls._warning_shown = False

        return performed_cleanup

    @classmethod
    def _standard_cleanup(cls):
        """Perform standard memory cleanup.

        Callers must hold cls._state_lock.
        """
        from ..util.process import ProcessManager, Process
        from ..util.color import Color

        cls._cleanup_count += 1

        # Clean up finished processes
        ProcessManager().cleanup_all()
        Process.cleanup_zombies()

        # Run garbage collection
        collected = gc.collect()

        if Configuration.verbose > 1:
            Color.pl('{+} {C}Standard cleanup #%d: GC collected %d objects{W}' % (
                cls._cleanup_count, collected
            ))

    @classmethod
    def _aggressive_cleanup(cls):
        """Perform aggressive memory cleanup for critical situations.

        Callers must hold cls._state_lock.
        """
        from ..util.process import ProcessManager, Process
        from ..util.color import Color

        cls._cleanup_count += 1
        
        # Force cleanup of all processes
        ProcessManager().cleanup_all()
        Process.cleanup_zombies()
        
        # Clear caches in Configuration
        if hasattr(Configuration, 'existing_commands'):
            if len(Configuration.existing_commands) > 50:
                # Keep only the 20 most recent
                Configuration.existing_commands = dict(
                    list(Configuration.existing_commands.items())[-20:]
                )
        
        # Multiple GC passes
        total_collected = 0
        for _ in range(3):
            collected = gc.collect()
            total_collected += collected
            if collected == 0:
                break
        
        if Configuration.verbose > 0:
            Color.pl('{+} {C}Aggressive cleanup #%d: GC collected %d objects{W}' % (
                cls._cleanup_count, total_collected
            ))
        
        # Check if cleanup helped
        new_status = cls.check_memory_status()
        if new_status['memory_critical']:
            Color.pl('{!} {R}Warning: Memory still critical after cleanup (%.1f MB){W}' % 
                    new_status['memory_mb'])
            Color.pl('{!} {O}Consider reducing target count or restarting wifite{W}')
    
    @classmethod
    def _fd_cleanup(cls):
        """Clean up file descriptors."""
        from ..util.process import ProcessManager, Process
        from ..util.color import Color
        
        # Clean up zombie processes (which may hold FDs)
        Process.cleanup_zombies()
        
        # Clean up finished processes
        ProcessManager().cleanup_all()
        
        # Check result
        new_count = cls.get_open_fd_count()
        if Configuration.verbose > 1:
            Color.pl('{+} {C}FD cleanup complete: now %d open{W}' % new_count)
    
    @classmethod
    def force_cleanup(cls):
        """
        Force immediate cleanup regardless of thresholds.
        
        Call this before memory-intensive operations.
        """
        cls._aggressive_cleanup()
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """
        Get cleanup statistics.
        
        Returns:
            Dictionary with cleanup statistics
        """
        status = cls.check_memory_status()
        return {
            **status,
            'cleanup_count': cls._cleanup_count,
            'last_cleanup_time': cls._last_cleanup_time,
        }


class InfiniteModeMonitor:
    """
    Specialized monitor for infinite attack mode.
    
    Provides enhanced memory management for long-running sessions.
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.targets_attacked = 0
        self.cycles_completed = 0
        self._last_cycle_cleanup = 0
    
    def on_cycle_start(self):
        """Called at the start of each attack cycle."""
        self.cycles_completed += 1
        
        # Cleanup every 5 cycles
        if self.cycles_completed - self._last_cycle_cleanup >= 5:
            MemoryMonitor.periodic_check(self.cycles_completed)
            self._last_cycle_cleanup = self.cycles_completed
    
    def on_target_complete(self):
        """Called when a target attack completes."""
        self.targets_attacked += 1
        
        # Cleanup every 10 targets
        if self.targets_attacked % 10 == 0:
            MemoryMonitor.force_cleanup()
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        elapsed = time.time() - self.start_time
        memory_stats = MemoryMonitor.get_stats()
        
        return {
            'elapsed_time': elapsed,
            'targets_attacked': self.targets_attacked,
            'cycles_completed': self.cycles_completed,
            **memory_stats
        }


# Global infinite mode monitor instance
_infinite_monitor: Optional[InfiniteModeMonitor] = None


def get_infinite_monitor() -> InfiniteModeMonitor:
    """Get or create the infinite mode monitor."""
    global _infinite_monitor
    if _infinite_monitor is None:
        _infinite_monitor = InfiniteModeMonitor()
    return _infinite_monitor


def reset_infinite_monitor():
    """Reset the infinite mode monitor."""
    global _infinite_monitor
    _infinite_monitor = None
