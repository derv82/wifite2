#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reusable UI components for wifite2 TUI.
Provides common visual elements used across different views.
"""

from typing import List, Optional
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group


class SignalStrengthBar:
    """Visual signal strength indicator using block characters."""

    # Signal strength thresholds
    STRONG_THRESHOLD = -50
    MEDIUM_THRESHOLD = -70

    @staticmethod
    def render(power_level: int) -> Text:
        """
        Render signal strength as a visual bar with color coding.

        Args:
            power_level: Signal power in dBm (e.g., -45, -70, -85)

        Returns:
            Rich Text object with colored signal strength indicator
        """
        # Determine strength level and color
        if power_level >= SignalStrengthBar.STRONG_THRESHOLD:
            bars = "███"
            color = "green"
        elif power_level >= SignalStrengthBar.MEDIUM_THRESHOLD:
            bars = "██ "
            color = "yellow"
        else:
            bars = "█  "
            color = "red"

        return Text(bars, style=color)


class EncryptionBadge:
    """Color-coded encryption type badge."""

    # Encryption type colors
    COLORS = {
        "WEP": "red",
        "WPA": "yellow",
        "WPA2": "yellow",
        "WPA3": "green",
        "WPS": "cyan",
        "OPEN": "bright_black",
    }

    @staticmethod
    def render(encryption_type: str, target=None) -> Text:
        """
        Render encryption type as a colored badge.

        Args:
            encryption_type: Encryption type string (e.g., "WPA2", "WEP")
            target: Optional Target object for WPA3 transition mode detection

        Returns:
            Rich Text object with colored encryption badge
        """
        # Check for WPA3 transition mode
        if target and hasattr(target, 'is_transition') and target.is_transition:
            text = Text("W23", style="magenta")  # Magenta for transition mode
            # Add PMF indicator
            if hasattr(target, 'pmf_status'):
                if target.pmf_status == 'required':
                    text.append("+", style="green")  # PMF required
                elif target.pmf_status == 'optional':
                    text.append("~", style="yellow")  # PMF optional
            # Add Dragonblood vulnerability indicator
            if hasattr(target, 'wpa3_info') and target.wpa3_info and target.wpa3_info.dragonblood_vulnerable:
                text.append("!", style="red bold")  # Dragonblood vulnerable
            return text
        
        # Check for WPA3-only with PMF indicator
        if target and hasattr(target, 'is_wpa3') and target.is_wpa3:
            enc_upper = encryption_type.upper()
            color = EncryptionBadge.COLORS.get(enc_upper, "white")
            text = Text(encryption_type, style=color)
            # Add PMF indicator for WPA3
            if hasattr(target, 'pmf_status') and target.pmf_status == 'required':
                text.append("+", style="green")  # PMF required
            # Add Dragonblood vulnerability indicator
            if hasattr(target, 'wpa3_info') and target.wpa3_info and target.wpa3_info.dragonblood_vulnerable:
                text.append("!", style="red bold")  # Dragonblood vulnerable
            return text
        
        # Standard encryption display
        enc_upper = encryption_type.upper()
        color = EncryptionBadge.COLORS.get(enc_upper, "white")
        return Text(encryption_type, style=color)


class ProgressPanel:
    """Attack progress panel with metrics and progress bar."""

    @staticmethod
    def render(
        attack_type: str,
        elapsed_time: int,
        progress_percent: float,
        status_message: str,
        metrics: dict,
        total_time: Optional[int] = None
    ) -> Panel:
        """
        Render attack progress panel with status and metrics.

        Args:
            attack_type: Type of attack (e.g., "WPA Handshake Capture")
            elapsed_time: Elapsed time in seconds
            progress_percent: Progress as a float (0.0 to 1.0)
            status_message: Current status message
            metrics: Dictionary of attack-specific metrics
            total_time: Total expected time in seconds (optional)

        Returns:
            Rich Panel with progress information
        """
        # Format elapsed time
        elapsed_str = ProgressPanel._format_time(elapsed_time)

        # Create header
        header = Text()
        header.append("Attack: ", style="bold")
        header.append(f"{attack_type}\n", style="cyan")
        header.append("Elapsed: ", style="bold")
        header.append(f"{elapsed_str}", style="white")

        if total_time:
            total_str = ProgressPanel._format_time(total_time)
            header.append(f" / {total_str}", style="bright_black")

        # Create status line
        status = Text()
        status.append("Status: ", style="bold")
        status.append(status_message, style="yellow")

        # Create metrics lines
        metrics_text = []
        for key, value in metrics.items():
            metric_line = Text()
            metric_line.append(f"{key}: ", style="bold")
            metric_line.append(str(value), style="white")
            metrics_text.append(metric_line)

        # Create progress bar
        progress_bar = ProgressPanel._create_progress_bar(progress_percent)

        # Combine all elements
        content = [header, Text(), status]
        if metrics_text:
            content.append(Text())
            content.extend(metrics_text)
        content.append(Text())
        content.append(progress_bar)

        return Panel(
            Group(*content),
            title="[bold]Progress[/bold]",
            border_style="blue"
        )

    @staticmethod
    def _format_time(seconds: int) -> str:
        """Format seconds as MM:SS."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def _create_progress_bar(progress: float) -> Text:
        """Create a text-based progress bar."""
        bar_width = 40
        filled = int(bar_width * progress)
        empty = bar_width - filled

        bar = Text()
        bar.append("█" * filled, style="green")
        bar.append("░" * empty, style="bright_black")
        bar.append(f" {progress * 100:.0f}%", style="white")

        return bar


class LogPanel:
    """Scrollable log panel with auto-scroll functionality."""

    def __init__(self, max_entries: int = 1000):
        """
        Initialize log panel.

        Args:
            max_entries: Maximum number of log entries to keep
        """
        self.max_entries = max_entries
        self.logs: List[str] = []
        self.auto_scroll = True

    def add_log(self, message: str):
        """
        Add a log entry.

        Args:
            message: Log message to add
        """
        self.logs.append(message)

        # Trim old entries if exceeding max (memory cleanup)
        if len(self.logs) > self.max_entries:
            # Keep only the most recent entries
            self.logs = self.logs[-self.max_entries:]

    def cleanup_old_entries(self, keep_count: int = None):
        """
        Clean up old log entries to free memory.

        Args:
            keep_count: Number of recent entries to keep (default: max_entries)
        """
        if keep_count is None:
            keep_count = self.max_entries
        
        if len(self.logs) > keep_count:
            self.logs = self.logs[-keep_count:]

    def render(self, height: int = 10) -> Panel:
        """
        Render log panel with recent entries.

        Args:
            height: Number of log lines to display

        Returns:
            Rich Panel with log entries
        """
        # Get the most recent entries
        visible_logs = self.logs[-height:] if len(self.logs) > height else self.logs

        # Create log text
        log_text = Text()
        for log in visible_logs:
            log_text.append(log + "\n", style="white")

        # If no logs, show placeholder
        if not visible_logs:
            log_text.append("No logs yet...", style="bright_black")

        return Panel(
            log_text,
            title="[bold]Logs[/bold]",
            border_style="blue",
            height=height + 2  # +2 for borders
        )

    def clear(self):
        """Clear all log entries."""
        self.logs.clear()


class HelpOverlay:
    """Help screen with keyboard shortcuts."""

    @staticmethod
    def render(context: str = "general") -> Panel:
        """
        Render help overlay with keyboard shortcuts.

        Args:
            context: Context for help (e.g., "scanner", "selector", "attack")

        Returns:
            Rich Panel with help information
        """
        shortcuts = HelpOverlay._get_shortcuts(context)

        # Create table for shortcuts
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Key", style="yellow", width=15)
        table.add_column("Action", style="white")

        for key, action in shortcuts:
            table.add_row(key, action)

        return Panel(
            table,
            title="[bold cyan]Keyboard Shortcuts[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )

    @staticmethod
    def _get_shortcuts(context: str) -> List[tuple]:
        """
        Get keyboard shortcuts for the given context.

        Args:
            context: Context name

        Returns:
            List of (key, action) tuples
        """
        general = [
            ("?", "Show this help"),
            ("q", "Quit / Cancel"),
            ("Ctrl+C", "Interrupt current operation"),
        ]

        scanner = [
            ("Ctrl+C", "Stop scanning and select targets"),
        ]

        selector = [
            ("↑ / ↓", "Navigate up/down"),
            ("Space", "Toggle selection"),
            ("Enter", "Confirm selection and start attack"),
            ("a", "Select all targets"),
            ("n", "Select none"),
            ("q", "Quit"),
        ]

        attack = [
            ("Ctrl+C", "Interrupt attack (shows options)"),
            ("c", "Continue to next attack (after Ctrl+C)"),
            ("s", "Skip to next target (after Ctrl+C)"),
            ("i", "Ignore current target (after Ctrl+C)"),
            ("e", "Exit / Return to scanning (after Ctrl+C)"),
        ]

        if context == "scanner":
            return general + scanner
        elif context == "selector":
            return general + selector
        elif context == "attack":
            return general + attack
        else:
            return general
