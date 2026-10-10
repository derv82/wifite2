#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TUI logging and debugging utilities for wifite2.
Provides logging capabilities for TUI events and errors.
"""

import os
import stat
from datetime import datetime


class TUILogger:
    """Logger for TUI events and debugging."""

    _instance = None
    _enabled = False
    _log_file = None
    _debug_mode = False

    @classmethod
    def initialize(cls, enabled: bool = False, debug_mode: bool = False, log_file: str = None):
        """
        Initialize TUI logger.

        Args:
            enabled: Whether logging is enabled
            debug_mode: Whether debug mode is active
            log_file: Path to log file (default: ~/.config/wifite/wifite_tui.log,
                in an owner-only 0700 directory; falls back to ~ if that
                directory can't be created)
        """
        cls._enabled = enabled
        cls._debug_mode = debug_mode

        if enabled:
            if log_file is None:
                # Use a user-owned directory instead of world-readable /tmp
                log_dir = os.path.join(os.path.expanduser('~'), '.config', 'wifite')
                try:
                    os.makedirs(log_dir, exist_ok=True)
                    os.chmod(log_dir, stat.S_IRWXU)  # 0700 — owner only
                except (OSError, ValueError):
                    log_dir = os.path.expanduser('~')
                log_file = os.path.join(log_dir, 'wifite_tui.log')
            cls._log_file = log_file

            # Create/clear log file with restricted permissions (owner read/write only)
            try:
                fd = os.open(cls._log_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
                with os.fdopen(fd, 'w') as f:
                    f.write(f"=== Wifite TUI Log Started: {datetime.now()} ===\n")
            except (OSError, ValueError):
                cls._enabled = False

    @classmethod
    def log(cls, message: str, level: str = 'INFO'):
        """
        Log a message.

        Args:
            message: Message to log
            level: Log level (INFO, DEBUG, WARNING, ERROR)
        """
        if not cls._enabled:
            return

        if level == 'DEBUG' and not cls._debug_mode:
            return

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_line = f"[{timestamp}] [{level}] {message}\n"

        try:
            with open(cls._log_file, 'a') as f:
                f.write(log_line)
        except Exception as e:
            # Can't use logger here to avoid recursion
            import sys
            print(f"TUI log write error: {e}", file=sys.stderr)

    @classmethod
    def debug(cls, message: str):
        """Log a debug message."""
        cls.log(message, 'DEBUG')

    @classmethod
    def info(cls, message: str):
        """Log an info message."""
        cls.log(message, 'INFO')

    @classmethod
    def warning(cls, message: str):
        """Log a warning message."""
        cls.log(message, 'WARNING')

    @classmethod
    def error(cls, message: str, exception: Exception = None):
        """
        Log an error message.

        Args:
            message: Error message
            exception: Optional exception object
        """
        if exception:
            message = f"{message}: {str(exception)}"
        cls.log(message, 'ERROR')

    @classmethod
    def log_event(cls, event_type: str, details: str = None):
        """
        Log a TUI event.

        Args:
            event_type: Type of event (e.g., 'VIEW_CHANGE', 'KEY_PRESS', 'RENDER')
            details: Optional event details
        """
        message = f"EVENT: {event_type}"
        if details:
            message += f" - {details}"
        cls.debug(message)

    @classmethod
    def log_performance(cls, operation: str, duration: float):
        """
        Log performance metrics.

        Args:
            operation: Operation name
            duration: Duration in seconds
        """
        cls.debug(f"PERF: {operation} took {duration:.3f}s")

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if logging is enabled."""
        return cls._enabled

    @classmethod
    def is_debug_mode(cls) -> bool:
        """Check if debug mode is active."""
        return cls._debug_mode

    @classmethod
    def log_wpa3_detection(cls, bssid: str, wpa3_info: dict):
        """
        Log WPA3 detection results.

        Args:
            bssid: Target BSSID
            wpa3_info: Dictionary with WPA3 detection information
        """
        details = f"BSSID={bssid}, WPA3={wpa3_info.get('has_wpa3', False)}, " \
                  f"Transition={wpa3_info.get('is_transition', False)}, " \
                  f"PMF={wpa3_info.get('pmf_status', 'unknown')}, " \
                  f"Dragonblood={wpa3_info.get('dragonblood_vulnerable', False)}"
        cls.info(f"WPA3_DETECTION: {details}")

    @classmethod
    def log_wpa3_strategy(cls, bssid: str, strategy: str, reason: str = None):
        """
        Log WPA3 attack strategy selection.

        Args:
            bssid: Target BSSID
            strategy: Selected strategy
            reason: Optional reason for strategy selection
        """
        details = f"BSSID={bssid}, Strategy={strategy}"
        if reason:
            details += f", Reason={reason}"
        cls.info(f"WPA3_STRATEGY: {details}")

    @classmethod
    def log_wpa3_downgrade(cls, bssid: str, success: bool, details: str = None):
        """
        Log WPA3 downgrade attempt.

        Args:
            bssid: Target BSSID
            success: Whether downgrade was successful
            details: Optional additional details
        """
        status = "SUCCESS" if success else "FAILED"
        msg = f"WPA3_DOWNGRADE: BSSID={bssid}, Status={status}"
        if details:
            msg += f", Details={details}"
        cls.info(msg)

    @classmethod
    def log_wpa3_sae_capture(cls, bssid: str, frame_type: str, frame_count: int = None):
        """
        Log SAE frame capture events.

        Args:
            bssid: Target BSSID
            frame_type: Type of SAE frame (commit, confirm, complete)
            frame_count: Optional frame count
        """
        msg = f"WPA3_SAE_CAPTURE: BSSID={bssid}, FrameType={frame_type}"
        if frame_count is not None:
            msg += f", Count={frame_count}"
        cls.info(msg)


# Convenience functions
def log_tui_event(event_type: str, details: str = None):
    """Log a TUI event."""
    TUILogger.log_event(event_type, details)


def log_tui_error(message: str, exception: Exception = None):
    """Log a TUI error."""
    TUILogger.error(message, exception)


def log_tui_debug(message: str):
    """Log a TUI debug message."""
    TUILogger.debug(message)


def log_wpa3_detection(bssid: str, wpa3_info: dict):
    """Log WPA3 detection results."""
    TUILogger.log_wpa3_detection(bssid, wpa3_info)


def log_wpa3_strategy(bssid: str, strategy: str, reason: str = None):
    """Log WPA3 attack strategy selection."""
    TUILogger.log_wpa3_strategy(bssid, strategy, reason)


def log_wpa3_downgrade(bssid: str, success: bool, details: str = None):
    """Log WPA3 downgrade attempt."""
    TUILogger.log_wpa3_downgrade(bssid, success, details)


def log_wpa3_sae_capture(bssid: str, frame_type: str, frame_count: int = None):
    """Log SAE frame capture events."""
    TUILogger.log_wpa3_sae_capture(bssid, frame_type, frame_count)
