#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Selector View for wifite2 TUI.
Interactive target selection interface with keyboard navigation.
"""

from typing import List, Set, Optional
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

from .components import SignalStrengthBar, EncryptionBadge
from ..util.input import KeyboardInput


class SelectorView:
    """Interactive target selection interface with keyboard navigation."""

    def __init__(self, tui_controller, targets: List):
        """
        Initialize selector view.

        Args:
            tui_controller: TUIController instance for rendering
            targets: List of Target objects to select from
        """
        self.tui = tui_controller
        self.targets = targets
        self.selected: Set[int] = set()  # Set of selected target indices
        self.cursor = 0  # Current cursor position
        self.scroll_offset = 0  # For scrolling through long lists
        # Dynamic max rows based on terminal height (leave room for header/footer)
        self.max_visible_rows = self._calculate_max_visible_rows()

    def run(self) -> List:
        """
        Run the interactive selector and return selected targets.

        Returns:
            List of selected Target objects
        """
        if not self.targets:
            return []

        # Start TUI if not already running
        if not self.tui.is_running:
            self.tui.start()

        try:
            # Initial render
            self._render()

            # Input loop
            while True:
                key = self._get_key()
                action = self.handle_input(key)

                if action == 'confirm':
                    break
                elif action == 'quit':
                    return []

                # Re-render after input
                self._render()

            # Return selected targets
            return self.get_selected_targets()

        finally:
            # Clean up
            pass

    def handle_input(self, key: str) -> Optional[str]:
        """
        Handle keyboard input for navigation and selection.

        Args:
            key: Key pressed by user

        Returns:
            Action string ('confirm', 'quit', None)
        """
        if key == '\x1b[A':  # Up arrow
            self._move_cursor(-1)
        elif key == '\x1b[B':  # Down arrow
            self._move_cursor(1)
        elif key == '\x1b[5~':  # Page Up
            self._move_cursor(-10)
        elif key == '\x1b[6~':  # Page Down
            self._move_cursor(10)
        elif key == '\x1b[H':  # Home
            self.cursor = 0
            self.scroll_offset = 0
        elif key == '\x1b[F':  # End
            self.cursor = len(self.targets) - 1
            self._adjust_scroll()
        elif key == ' ':  # Space - toggle selection
            self._toggle_selection()
        elif key == '\r' or key == '\n':  # Enter - confirm
            return 'confirm'
        elif key.lower() == 'a':  # Select all
            self._select_all()
        elif key.lower() == 'n':  # Select none
            self._select_none()
        elif key.lower() == 'q':  # Quit
            return 'quit'
        elif key == '?':  # Help
            self.show_help()

        return None

    def show_help(self):
        """Display help overlay."""
        from .components import HelpOverlay
        from ..util.input import KeyboardInput
        
        # Render help overlay
        help_panel = HelpOverlay.render(context='selector')
        
        # Update display with help
        self.tui.update(help_panel)
        
        # Wait for any key to dismiss
        with KeyboardInput() as kb:
            kb.get_key(timeout=30)  # 30 second timeout
        
        # Re-render normal view
        self._render()

    def _move_cursor(self, delta: int):
        """
        Move cursor by delta positions.

        Args:
            delta: Number of positions to move (positive or negative)
        """
        self.cursor = max(0, min(len(self.targets) - 1, self.cursor + delta))
        self._adjust_scroll()

    def _adjust_scroll(self):
        """Adjust scroll offset to keep cursor visible."""
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + self.max_visible_rows:
            self.scroll_offset = self.cursor - self.max_visible_rows + 1

    def _toggle_selection(self):
        """Toggle selection of current target."""
        if self.cursor in self.selected:
            self.selected.remove(self.cursor)
        else:
            self.selected.add(self.cursor)

    def _select_all(self):
        """Select all targets."""
        self.selected = set(range(len(self.targets)))

    def _select_none(self):
        """Deselect all targets."""
        self.selected.clear()

    def get_selected_targets(self) -> List:
        """
        Get list of selected targets.

        Returns:
            List of selected Target objects
        """
        return [self.targets[i] for i in sorted(self.selected)]

    def _calculate_max_visible_rows(self) -> int:
        """
        Calculate maximum visible rows based on terminal height.
        Optimizes display for large target lists.

        Returns:
            Maximum number of rows to display
        """
        if self.tui and hasattr(self.tui, 'get_terminal_size'):
            _, height = self.tui.get_terminal_size()
            # Reserve space for header (3), footer (5), and padding (3)
            available_height = height - 11
            # Minimum 10 rows, maximum 50 rows for performance
            return max(10, min(50, available_height))
        return 15  # Default fallback

    def _render(self):
        """Render the complete selector interface."""
        if not self.tui.is_running:
            return

        # Create main layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="targets"),
            Layout(name="footer", size=5)
        )

        # Render each section
        layout["header"].update(self._render_header())
        layout["targets"].update(self._render_targets_table())
        layout["footer"].update(self._render_footer())

        # Use force_update for immediate feedback on user input
        self.tui.force_update(layout)

    def _render_header(self) -> Panel:
        """
        Render header with selection count.

        Returns:
            Rich Panel with header information
        """
        header = Text()
        header.append("Select Targets to Attack", style="bold cyan")
        header.append(f" ({len(self.selected)} selected)", style="yellow")

        return Panel(
            Align.center(header),
            border_style="cyan",
            padding=(0, 1)
        )

    def _render_targets_table(self) -> Table:
        """
        Render targets table with selection indicators.

        Returns:
            Rich Table with target information
        """
        from ..config import Configuration
        
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="blue",
            expand=True,
            show_lines=False,
            padding=(0, 1)
        )

        # Define columns
        table.add_column("", style="white", width=3)  # Cursor/selection
        table.add_column("#", style="cyan", width=4, justify="right")
        table.add_column("ESSID", style="white", width=20)
        table.add_column("BSSID", style="bright_black", width=17)
        
        # Conditionally add manufacturer column
        if Configuration.show_manufacturers:
            table.add_column("MANUFACTURER", style="white", width=20)
        
        table.add_column("ENC", style="white", width=8)
        table.add_column("PWR", style="white", width=5, justify="center")
        table.add_column("WPS", style="white", width=4, justify="center")
        table.add_column("CLIENTS", style="white", width=7, justify="right")

        # Calculate visible range
        start_idx = self.scroll_offset
        end_idx = min(len(self.targets), start_idx + self.max_visible_rows)

        # Add target rows
        for idx in range(start_idx, end_idx):
            target = self.targets[idx]
            
            # Cursor and selection indicator
            cursor_sel = ""
            if idx == self.cursor:
                cursor_sel = ">"
            else:
                cursor_sel = " "
            
            if idx in self.selected:
                cursor_sel += " ✓"
            else:
                cursor_sel += "  "

            # Row style based on cursor position
            row_style = "bold" if idx == self.cursor else None

            # Build row data
            row_data = [
                Text(cursor_sel, style="yellow" if idx == self.cursor else "white"),
                Text(str(idx + 1), style="cyan bold" if idx == self.cursor else "cyan"),
                self._format_essid(target, idx == self.cursor),
                Text(target.bssid, style="bright_black"),
            ]
            
            # Add manufacturer if enabled
            if Configuration.show_manufacturers:
                row_data.append(self._format_manufacturer(target))
            
            # Add remaining columns
            row_data.extend([
                self._format_encryption(target),
                self._format_power(target),
                self._format_wps(target),
                self._format_clients(target)
            ])
            
            table.add_row(*row_data, style=row_style)

        # Show scroll indicators if needed
        if len(self.targets) > self.max_visible_rows:
            scroll_info = Text()
            if start_idx > 0:
                scroll_info.append("↑ More above ", style="bright_black")
            if end_idx < len(self.targets):
                scroll_info.append("↓ More below", style="bright_black")
            
            if scroll_info.plain:
                table.caption = scroll_info

        return table

    def _format_essid(self, target, is_cursor: bool) -> Text:
        """
        Format ESSID with appropriate styling.

        Args:
            target: Target object
            is_cursor: Whether this is the cursor row

        Returns:
            Rich Text with formatted ESSID
        """
        if target.essid_known and target.essid:
            essid = target.essid[:20]  # Truncate long ESSIDs
            style = "bold white" if is_cursor else "white"
            return Text(essid, style=style)
        else:
            style = "bright_black italic bold" if is_cursor else "bright_black italic"
            return Text("<hidden>", style=style)

    def _format_power(self, target) -> Text:
        """
        Format power level with signal strength bar.

        Args:
            target: Target object

        Returns:
            Rich Text with signal strength indicator
        """
        # Convert power back to dBm for display
        power_dbm = target.power - 100 if target.power > 0 else target.power
        return SignalStrengthBar.render(power_dbm)

    def _format_encryption(self, target) -> Text:
        """
        Format encryption type with color coding.

        Args:
            target: Target object

        Returns:
            Rich Text with colored encryption badge
        """
        return EncryptionBadge.render(target.encryption, target)

    def _format_wps(self, target) -> Text:
        """
        Format WPS status.

        Args:
            target: Target object

        Returns:
            Rich Text with WPS indicator
        """
        if hasattr(target, 'wps'):
            # WPSState values: NONE=0, UNLOCKED=1, LOCKED=2, UNKNOWN=3
            if target.wps == 1:  # UNLOCKED
                return Text("✓", style="green bold")
            elif target.wps == 2:  # LOCKED
                return Text("✗", style="red")
            elif target.wps == 3:  # UNKNOWN
                return Text("?", style="yellow")
        return Text("-", style="bright_black")
    
    def _format_clients(self, target) -> Text:
        """
        Format client count with color coding.

        Args:
            target: Target object

        Returns:
            Rich Text with colored client count
        """
        client_count = len(target.clients) if hasattr(target, 'clients') else 0
        if client_count > 0:
            return Text(str(client_count), style="green bold")
        else:
            return Text("0", style="bright_black")
    
    def _format_manufacturer(self, target) -> Text:
        """
        Format manufacturer name from BSSID OUI.

        Args:
            target: Target object

        Returns:
            Rich Text with manufacturer name
        """
        from ..config import Configuration
        
        # Get OUI (first 3 octets of BSSID)
        oui = ''.join(target.bssid.split(':')[:3])
        Configuration.load_manufacturers()
        manufacturer = Configuration.manufacturers.get(oui, "Unknown") if Configuration.manufacturers else "Unknown"
        
        # Truncate if too long
        max_len = 20
        if len(manufacturer) > max_len:
            manufacturer = manufacturer[:max_len - 3] + "..."
        
        return Text(manufacturer, style="white")

    def _render_footer(self) -> Panel:
        """
        Render footer with keyboard shortcuts.

        Returns:
            Rich Panel with footer information
        """
        footer = Text()
        
        # Line 1: Navigation
        footer.append("[", style="bright_black")
        footer.append("↑↓", style="bold yellow")
        footer.append("]", style="bright_black")
        footer.append(" Navigate  ", style="white")
        
        footer.append("[", style="bright_black")
        footer.append("Space", style="bold yellow")
        footer.append("]", style="bright_black")
        footer.append(" Select  ", style="white")
        
        footer.append("[", style="bright_black")
        footer.append("Enter", style="bold yellow")
        footer.append("]", style="bright_black")
        footer.append(" Attack", style="white")
        
        footer.append("\n")
        
        # Line 2: Actions
        footer.append("[", style="bright_black")
        footer.append("a", style="bold yellow")
        footer.append("]", style="bright_black")
        footer.append(" All  ", style="white")
        
        footer.append("[", style="bright_black")
        footer.append("n", style="bold yellow")
        footer.append("]", style="bright_black")
        footer.append(" None  ", style="white")
        
        footer.append("[", style="bright_black")
        footer.append("q", style="bold yellow")
        footer.append("]", style="bright_black")
        footer.append(" Quit  ", style="white")
        
        footer.append("[", style="bright_black")
        footer.append("?", style="bold yellow")
        footer.append("]", style="bright_black")
        footer.append(" Help", style="white")

        return Panel(
            Align.center(footer),
            border_style="blue",
            padding=(0, 1)
        )

    def _get_key(self) -> str:
        """
        Get a single keypress from the user.

        Returns:
            Key string (may be multi-character for special keys)
        """
        import sys
        import tty
        import termios
        import select
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            
            # Handle escape sequences (arrow keys, etc.)
            if ch == '\x1b':
                # Wait a bit to see if more characters are coming
                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                if ready:
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        # CSI sequence - read one more character
                        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if ready:
                            ch3 = sys.stdin.read(1)
                            # Check if it's a multi-char sequence (like Page Up/Down)
                            if ch3 in '0123456789':
                                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                                if ready:
                                    ch4 = sys.stdin.read(1)
                                    return '\x1b[' + ch3 + ch4
                            return '\x1b[' + ch3
                    return '\x1b' + ch2
                # Just ESC key alone
                return '\x1b'
            
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _get_key(self) -> str:
        """
        Get a single keypress from the user.

        Returns:
            Key string (may be multi-character for special keys)
        """
        with KeyboardInput() as kb:
            # Block until key is pressed
            while True:
                key = kb.get_key(timeout=0.1)
                if key:
                    return key
