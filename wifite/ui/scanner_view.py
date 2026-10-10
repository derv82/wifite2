#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Scanner View for wifite2 TUI.
Displays real-time scanning interface with target list and statistics.
"""

import time
from typing import List, Optional
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

from .components import SignalStrengthBar, EncryptionBadge


class ScannerView:
    """Interactive scanning interface with real-time updates."""

    def __init__(self, tui_controller, session=None):
        """
        Initialize scanner view.

        Args:
            tui_controller: TUIController instance for rendering
            session: Optional SessionState for resumed sessions
        """
        self.tui = tui_controller
        self.targets = []
        self.scan_start_time = time.time()
        self.decloaking = False
        self.max_visible_targets = 50  # Limit displayed targets for performance
        self.session = session  # Store session for resume status display

    def update_targets(self, targets: List, decloaking: bool = False):
        """
        Update target list and refresh display.

        Args:
            targets: List of Target objects from scanner
            decloaking: Whether decloaking is active
        """
        self.targets = targets
        self.decloaking = decloaking
        self._render()

    def _render(self):
        """Render the complete scanning interface."""
        if not self.tui.is_running:
            return

        # Create main layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="targets"),
            Layout(name="footer", size=3)
        )

        # Render each section
        layout["header"].update(self._render_header())
        layout["targets"].update(self._render_targets_table())
        layout["footer"].update(self._render_footer())

        # Update TUI
        self.tui.update(layout)

    def _render_header(self) -> Panel:
        """
        Render header with scan statistics.

        Returns:
            Rich Panel with header information
        """
        elapsed = int(time.time() - self.scan_start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60

        # Count targets by encryption type
        wep_count = sum(1 for t in self.targets if 'WEP' in t.encryption)
        wpa_count = sum(1 for t in self.targets if 'WPA' in t.encryption and not getattr(t, 'is_wpa3', False))
        wpa3_count = sum(1 for t in self.targets if getattr(t, 'is_wpa3', False))
        wps_count = sum(1 for t in self.targets if hasattr(t, 'wps') and t.wps)

        # Count clients
        client_count = sum(len(t.clients) for t in self.targets)

        # Build header text - single line for compactness
        header = Text()
        header.append("wifite2 ", style="bold cyan")
        
        # Show resume indicator if this is a resumed session
        if self.session:
            header.append("- ", style="white")
            header.append("RESUMED SESSION", style="bold magenta")
            header.append(" - Scanning", style="bold yellow")
            
            # Add session progress info
            summary = self.session.get_progress_summary()
            header.append(" | Progress: ", style="white")
            header.append(f"{summary['completed']}", style="green")
            header.append("/", style="white")
            header.append(f"{summary['total']}", style="cyan")
            
            # Add session age
            age_hours = summary['age_hours']
            if age_hours < 1:
                age_str = f"{int(age_hours * 60)}m"
            elif age_hours < 24:
                age_str = f"{int(age_hours)}h"
            else:
                age_str = f"{int(age_hours / 24)}d"
            header.append(" | Age: ", style="white")
            header.append(age_str, style="yellow")
        else:
            header.append("- Scanning", style="bold yellow")
        
        if self.decloaking:
            header.append(" & decloaking", style="yellow")
        header.append(f" {minutes:02d}:{seconds:02d} | ", style="white")
        header.append("Targets: ", style="white")
        header.append(f"{len(self.targets)}", style="bold green")
        header.append(" | WEP: ", style="white")
        header.append(f"{wep_count}", style="red")
        header.append(" | WPA: ", style="white")
        header.append(f"{wpa_count}", style="yellow")
        header.append(" | WPA3: ", style="white")
        header.append(f"{wpa3_count}", style="magenta")
        header.append(" | WPS: ", style="white")
        header.append(f"{wps_count}", style="cyan")
        header.append(" | Clients: ", style="white")
        header.append(f"{client_count}", style="green")

        # Honeypot stats
        from ..config import Configuration
        if Configuration.detect_honeypots:
            hp_count = sum(1 for t in self.targets if getattr(t, 'honeypot_score', 0) >= 50)
            if hp_count > 0:
                header.append(" | Honeypots: ", style="white")
                header.append(f"{hp_count}", style="red bold")

        return Panel(
            header,
            border_style="cyan",
            padding=(0, 1)
        )

    def _render_targets_table(self) -> Table:
        """
        Render targets table with live data.
        Optimized for large target lists by limiting displayed rows.

        Returns:
            Rich Table with target information
        """
        # Recalculate max visible targets (handles terminal resize)
        max_visible = self._calculate_max_visible_targets()
        
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="blue",
            expand=True,
            show_lines=False
        )

        # Define columns
        from ..config import Configuration
        
        table.add_column("#", style="cyan", width=4, justify="right")
        table.add_column("ESSID", style="white", width=20)
        table.add_column("BSSID", style="bright_black", width=17)
        
        # Conditionally add manufacturer column
        if Configuration.show_manufacturers:
            table.add_column("MANUFACTURER", style="white", width=20)
        
        table.add_column("CH", style="white", width=3, justify="center")
        table.add_column("PWR", style="white", width=5, justify="center")
        table.add_column("ENC", style="white", width=12)  # Increased width for WPA3 indicators
        table.add_column("WPS", style="white", width=4, justify="center")
        table.add_column("CLIENTS", style="white", width=7, justify="right")

        # Honeypot detection column
        if Configuration.detect_honeypots:
            table.add_column("HP", style="white", width=4, justify="center")

        # Add target rows
        if not self.targets:
            # Show placeholder when no targets
            # Adjust number of empty columns based on manufacturer display
            empty_cols = ["", "", "", "", "", "", ""]
            if Configuration.show_manufacturers:
                empty_cols.insert(2, "")  # Add extra column for manufacturer
            if Configuration.detect_honeypots:
                empty_cols.append("")  # Add extra column for honeypot
            
            table.add_row(
                "",
                Text("No targets found yet...", style="bright_black italic"),
                *empty_cols
            )
        else:
            # Optimize for large lists: only show top N targets
            # Sort by power (strongest first) for better UX
            sorted_targets = sorted(self.targets, key=lambda t: t.power, reverse=True)
            visible_targets = sorted_targets[:max_visible]
            
            for idx, target in enumerate(visible_targets, 1):
                # Get original index for display
                original_idx = self.targets.index(target) + 1
                
                # Build row data
                row_data = [
                    str(original_idx),
                    self._format_essid(target),
                    target.bssid,
                ]
                
                # Add manufacturer if enabled
                if Configuration.show_manufacturers:
                    row_data.append(self._format_manufacturer(target))
                
                # Add remaining columns
                row_data.extend([
                    str(target.channel),
                    self._format_power(target),
                    self._format_encryption(target),
                    self._format_wps(target),
                    self._format_clients(target)
                ])

                # Honeypot indicator
                if Configuration.detect_honeypots:
                    row_data.append(self._format_honeypot(target))

                table.add_row(*row_data)
            
            # Show indicator if there are more targets
            if len(self.targets) > max_visible:
                remaining = len(self.targets) - max_visible
                table.caption = Text(
                    f"Showing top {max_visible} of {len(self.targets)} targets ({remaining} more)",
                    style="bright_black italic"
                )

        return table

    def _format_essid(self, target) -> Text:
        """
        Format ESSID with appropriate styling.

        Args:
            target: Target object

        Returns:
            Rich Text with formatted ESSID
        """
        if target.essid_known and target.essid:
            essid = target.essid[:20]  # Truncate long ESSIDs
            style = "bold white" if target.decloaked else "white"
            text = Text(essid, style=style)
            if target.decloaked:
                text.append(" *", style="green")  # Mark decloaked networks
            return text
        else:
            return Text("<hidden>", style="bright_black italic")

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
        Shows WPA3/Transition/WPA2 status, PMF indicators, and Dragonblood markers.

        Args:
            target: Target object

        Returns:
            Rich Text with colored encryption badge
        """
        enc_text = EncryptionBadge.render(target.encryption, target)
        
        # Add PMF indicator if WPA3 info is available
        if hasattr(target, 'wpa3_info') and target.wpa3_info:
            if target.wpa3_info.pmf_status == 'required':
                enc_text.append(" ", style="white")
                enc_text.append("🛡", style="cyan")  # Shield for PMF required
            elif target.wpa3_info.pmf_status == 'optional':
                enc_text.append(" ", style="white")
                enc_text.append("◐", style="yellow")  # Half-circle for PMF optional
        
        # Add Dragonblood vulnerability marker
        if hasattr(target, 'is_dragonblood_vulnerable') and target.is_dragonblood_vulnerable:
            enc_text.append(" ", style="white")
            enc_text.append("⚠", style="red bold")  # Warning for vulnerability
        
        return enc_text

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
        client_count = len(target.clients)
        if client_count > 0:
            return Text(str(client_count), style="green bold")
        else:
            return Text("0", style="bright_black")
    
    def _format_honeypot(self, target) -> Text:
        """
        Format honeypot score indicator.

        Args:
            target: Target object

        Returns:
            Rich Text with honeypot risk indicator
        """
        score = getattr(target, 'honeypot_score', 0)
        if score >= 50:
            return Text(f"!{score}", style="red bold")
        elif score >= 20:
            return Text(f"?{score}", style="yellow")
        return Text("-", style="bright_black")

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
        footer.append("[", style="bright_black")
        footer.append("Ctrl+C", style="bold yellow")
        footer.append("]", style="bright_black")
        footer.append(" Stop scan and select targets", style="white")
        footer.append("  |  ", style="bright_black")
        footer.append("[", style="bright_black")
        footer.append("?", style="bold yellow")
        footer.append("]", style="bright_black")
        footer.append(" Help", style="white")

        return Panel(
            Align.center(footer),
            border_style="blue",
            padding=(0, 1)
        )

    def handle_input(self, key: str) -> Optional[str]:
        """
        Handle keyboard input during scanning.

        Args:
            key: Key pressed by user

        Returns:
            Action string or None ('stop', 'help', etc.)
        """
        if key == '?':
            self.show_help()
            return 'help'
        # Ctrl+C is handled by the scanner itself
        return None

    def show_help(self):
        """Display help overlay."""
        from .components import HelpOverlay
        from ..util.input import KeyboardInput
        
        # Render help overlay
        help_panel = HelpOverlay.render(context='scanner')
        
        # Update display with help
        self.tui.update(help_panel)
        
        # Wait for any key to dismiss
        with KeyboardInput() as kb:
            kb.get_key(timeout=30)  # 30 second timeout
        
        # Re-render normal view
        self._render()

    def stop(self):
        """Stop the scanner view and clean up."""
        # Any cleanup needed when stopping the view
        pass

    def _calculate_max_visible_targets(self) -> int:
        """
        Calculate maximum visible targets based on terminal height.
        Optimizes display for large target lists.

        Returns:
            Maximum number of targets to display
        """
        if self.tui and hasattr(self.tui, 'get_terminal_size'):
            _, height = self.tui.get_terminal_size()
            # Reserve space for header (3), footer (3), and padding (2)
            available_height = height - 8
            # Minimum 10 targets, maximum 100 targets for performance
            return max(10, min(100, available_height))
        return 50  # Default fallback
