#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TUI Controller for wifite2 using the rich library.
Manages the interactive terminal user interface with real-time updates.
"""

import time
import signal
from typing import Optional
from rich.console import Console
from rich.live import Live
from ..util.tui_logger import TUILogger, log_tui_event, log_tui_error, log_tui_debug


class TUIController:
    """
    Main TUI controller using rich library.
    Manages the console, live display, and provides lifecycle methods.
    """

    # Minimum terminal size requirements
    MIN_WIDTH = 80
    MIN_HEIGHT = 24

    def __init__(self):
        """Initialize TUI controller with rich Console and Live display."""
        self.console = Console()
        self.live: Optional[Live] = None
        self.is_running = False
        self.last_update = 0
        self.min_update_interval = 0.05  # 50ms minimum between updates (was 100ms)
        self.resize_handler = None
        self.last_size = (0, 0)  # Track last known terminal size

    def start(self):
        """
        Initialize and start TUI mode.
        Sets up the live display for real-time updates.
        """
        if self.is_running:
            log_tui_debug("TUI already running, skipping start")
            return

        log_tui_event("TUI_START", f"Terminal size: {self.console.width}x{self.console.height}")

        # Check minimum terminal size
        if not self.check_terminal_size():
            error_msg = f"Terminal too small. Minimum size: {self.MIN_WIDTH}x{self.MIN_HEIGHT}, Current: {self.console.width}x{self.console.height}"
            log_tui_error(error_msg)
            raise RuntimeError(error_msg)

        try:
            start_time = time.time()
            
            # Initialize Live display with auto-refresh disabled
            # We'll control updates manually for better performance
            self.live = Live(
                console=self.console,
                auto_refresh=False,
                screen=True,
                refresh_per_second=10
            )
            self.live.start()
            self.is_running = True
            self.last_size = (self.console.width, self.console.height)
            
            # Set up resize signal handler
            self._setup_resize_handler()
            
            duration = time.time() - start_time
            TUILogger.log_performance("TUI_START", duration)
            log_tui_event("TUI_STARTED", "Successfully initialized")
        except Exception as e:
            # If TUI initialization fails, clean up and raise
            log_tui_error("TUI initialization failed", e)
            self.stop()
            raise RuntimeError(f"Failed to initialize TUI: {e}")

    def stop(self):
        """
        Stop TUI mode and clean up resources.
        Ensures proper cleanup of the live display and console state.
        """
        log_tui_event("TUI_STOP", "Stopping TUI")
        
        # Remove resize handler
        self._remove_resize_handler()
        
        if self.live is not None:
            try:
                self.live.stop()
                log_tui_debug("Live display stopped")
            except Exception as e:
                log_tui_error("Error stopping live display", e)
            finally:
                self.live = None

        # Clear the console to restore normal terminal state
        try:
            self.console.clear()
        except Exception as e:
            log_tui_debug(f"Error clearing console: {e}")

        self.is_running = False
        log_tui_event("TUI_STOPPED", "TUI cleanup complete")

    def should_update(self) -> bool:
        """
        Check if enough time has passed since last update.
        Implements update throttling to prevent excessive rendering.

        Returns:
            bool: True if update should proceed, False otherwise
        """
        now = time.time()
        if now - self.last_update >= self.min_update_interval:
            self.last_update = now
            return True
        return False

    def force_update(self, renderable):
        """
        Force an immediate update without throttling.
        Use for interactive elements that need instant feedback.

        Args:
            renderable: Rich renderable object
        """
        if not self.is_running or self.live is None:
            return

        try:
            self.live.update(renderable, refresh=True)
            self.last_update = time.time()
        except Exception as e:
            from ..util.logger import log_debug
            log_debug('TUI', f'Update throttle error: {e}')

    def update(self, renderable):
        """
        Update the live display with new content.
        Respects update throttling to maintain performance.

        Args:
            renderable: Rich renderable object (Layout, Table, Panel, etc.)
        """
        if not self.is_running or self.live is None:
            return

        if self.should_update():
            try:
                self.live.update(renderable, refresh=True)
            except Exception:
                # If update fails, try to recover or fail gracefully
                try:
                    # Attempt to refresh without update
                    if self.live is not None:
                        self.live.refresh()
                except Exception:
                    # Complete failure — stop TUI so the caller can fall back
                    # to classic output instead of hammering a broken Live.
                    self.is_running = False

    def __enter__(self):
        """
        Context manager entry.
        Starts the TUI when entering the context.

        Returns:
            TUIController: Self reference for context manager
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit.
        Ensures TUI is properly cleaned up when exiting the context.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns:
            bool: False to propagate exceptions, doesn't suppress them
        """
        self.stop()
        return False  # Don't suppress exceptions

    def handle_resize(self):
        """
        Handle terminal resize events.
        Forces a refresh of the display to adapt to new terminal size.
        """
        if self.is_running and self.live is not None:
            try:
                # Update console size
                new_size = (self.console.width, self.console.height)
                
                # Only handle if size actually changed
                if new_size != self.last_size:
                    self.last_size = new_size
                    
                    # Check if terminal is still large enough
                    if not self.check_terminal_size():
                        # Terminal too small - could show warning
                        pass
                    
                    # Force a refresh to re-render with new dimensions
                    self.live.refresh()
            except Exception as e:
                from ..util.logger import log_debug
                log_debug('TUI', f'Resize handling error: {e}')

    def check_terminal_size(self) -> bool:
        """
        Check if terminal meets minimum size requirements.

        Returns:
            True if terminal is large enough, False otherwise
        """
        return (self.console.width >= self.MIN_WIDTH and 
                self.console.height >= self.MIN_HEIGHT)

    def get_terminal_size(self) -> tuple:
        """
        Get current terminal size.

        Returns:
            Tuple of (width, height)
        """
        return (self.console.width, self.console.height)

    def _setup_resize_handler(self):
        """Set up signal handler for terminal resize events."""
        try:
            # Store original handler
            self.resize_handler = signal.signal(signal.SIGWINCH, self._on_resize)
        except (AttributeError, TypeError, ImportError):
            # SIGWINCH not available on all platforms (e.g., Windows)
            pass

    def _remove_resize_handler(self):
        """Remove signal handler for terminal resize events."""
        try:
            if self.resize_handler is not None:
                signal.signal(signal.SIGWINCH, self.resize_handler)
                self.resize_handler = None
        except Exception as e:
            from ..util.logger import log_debug
            log_debug('TUI', f'Signal cleanup error: {e}')

    def _on_resize(self, signum, frame):
        """
        Signal handler for SIGWINCH (terminal resize).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.handle_resize()
