#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Keyboard input handling for wifite2 TUI.
Provides non-blocking keyboard input for interactive views.
"""

import sys
import select
import termios
import tty
from typing import Optional


class KeyboardInput:
    """Non-blocking keyboard input handler."""

    def __init__(self):
        """Initialize keyboard input handler."""
        self.fd = sys.stdin.fileno()
        self.old_settings = None

    def __enter__(self):
        """Context manager entry - set up raw mode."""
        self.old_settings = termios.tcgetattr(self.fd)
        tty.setraw(self.fd)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - restore terminal settings."""
        if self.old_settings:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
        return False

    def get_key(self, timeout: float = 0.0) -> Optional[str]:
        """
        Get a single keypress with optional timeout.

        Args:
            timeout: Timeout in seconds (0 = non-blocking)

        Returns:
            Key string or None if no key pressed
        """
        # Check if input is available
        if timeout > 0:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if not ready:
                return None
        else:
            # Non-blocking check
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if not ready:
                return None

        # Read the key
        ch = sys.stdin.read(1)

        # Handle escape sequences (arrow keys, function keys, etc.)
        if ch == '\x1b':
            # Check if more characters are available (escape sequence)
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if ready:
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    # CSI sequence
                    ch3 = sys.stdin.read(1)
                    
                    # Handle sequences that end with ~
                    if ch3 in '0123456789':
                        ch4 = sys.stdin.read(1)
                        if ch4 == '~':
                            return '\x1b[' + ch3 + ch4
                        else:
                            return '\x1b[' + ch3 + ch4
                    else:
                        return '\x1b[' + ch3
                else:
                    return '\x1b' + ch2
            else:
                # Just ESC key
                return '\x1b'

        return ch

    @staticmethod
    def is_ctrl_c(key: str) -> bool:
        """
        Check if key is Ctrl+C.

        Args:
            key: Key string

        Returns:
            True if Ctrl+C, False otherwise
        """
        return key == '\x03'

    @staticmethod
    def key_name(key: str) -> str:
        """
        Get human-readable name for key.

        Args:
            key: Key string

        Returns:
            Human-readable key name
        """
        key_names = {
            '\x1b[A': 'Up',
            '\x1b[B': 'Down',
            '\x1b[C': 'Right',
            '\x1b[D': 'Left',
            '\x1b[H': 'Home',
            '\x1b[F': 'End',
            '\x1b[5~': 'Page Up',
            '\x1b[6~': 'Page Down',
            '\x1b': 'Escape',
            '\r': 'Enter',
            '\n': 'Enter',
            ' ': 'Space',
            '\x03': 'Ctrl+C',
            '\x7f': 'Backspace',
            '\t': 'Tab',
        }
        return key_names.get(key, key if len(key) == 1 else 'Unknown')


class NonBlockingInput:
    """
    Simple non-blocking input reader for use during scanning/attacks.
    Does not require raw mode.
    """

    @staticmethod
    def has_input(timeout: float = 0.0) -> bool:
        """
        Check if input is available.

        Args:
            timeout: Timeout in seconds (0 = non-blocking)

        Returns:
            True if input is available, False otherwise
        """
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        return bool(ready)

    @staticmethod
    def read_line(timeout: float = 0.0) -> Optional[str]:
        """
        Read a line of input with optional timeout.

        Args:
            timeout: Timeout in seconds (0 = non-blocking)

        Returns:
            Input line or None if no input available
        """
        if NonBlockingInput.has_input(timeout):
            try:
                return sys.stdin.readline().strip()
            except (OSError, ValueError):
                return None
        return None


def handle_ctrl_c(func):
    """
    Decorator to handle Ctrl+C gracefully in TUI views.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            # Let the caller handle the interrupt
            raise
    return wrapper


# Convenience functions for common key checks
def is_arrow_key(key: str) -> bool:
    """Check if key is an arrow key."""
    return key in ['\x1b[A', '\x1b[B', '\x1b[C', '\x1b[D']


def is_navigation_key(key: str) -> bool:
    """Check if key is a navigation key (arrows, page up/down, home/end)."""
    return key in ['\x1b[A', '\x1b[B', '\x1b[C', '\x1b[D', 
                   '\x1b[H', '\x1b[F', '\x1b[5~', '\x1b[6~']


def is_enter_key(key: str) -> bool:
    """Check if key is Enter."""
    return key in ['\r', '\n']


def is_escape_key(key: str) -> bool:
    """Check if key is Escape."""
    return key == '\x1b'
