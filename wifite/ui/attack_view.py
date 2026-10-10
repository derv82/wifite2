#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Attack View for wifite2 TUI.
Displays real-time attack progress with target info, status, and logs.
"""

import time
from typing import Optional, Dict, Any
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

from .components import ProgressPanel, LogPanel, EncryptionBadge, SignalStrengthBar


class AttackView:
    """Interactive attack progress interface with real-time updates."""

    def __init__(self, tui_controller, target, session=None, target_state=None):
        """
        Initialize attack view.

        Args:
            tui_controller: TUIController instance for rendering
            target: Target object being attacked
            session: Optional SessionState for resumed sessions
            target_state: Optional TargetState for this specific target from session
        """
        self.tui = tui_controller
        self.target = target
        self.attack_type = "Unknown"
        self.attack_start_time = time.time()
        self.progress_percent = 0.0
        self.status_message = "Initializing..."
        self.metrics = {}
        self.log_panel = LogPanel(max_entries=1000)
        self.total_time = None  # Expected total time (optional)
        self._update_counter = 0  # Track updates for periodic cleanup
        self._last_render_time = 0  # Track last render for auto-refresh
        self._auto_refresh_interval = 0.5  # Auto-refresh every 0.5 seconds (faster updates)
        self.session = session  # Store session for resume status display
        self.target_state = target_state  # Store target state for attempt tracking

    def start(self):
        """Start the attack view and TUI controller."""
        if not self.tui.is_running:
            self.tui.start()
        self.attack_start_time = time.time()
        self._last_render_time = time.time()
        self._render()

    def stop(self):
        """Stop the attack view."""
        # View cleanup if needed
        pass

    def set_attack_type(self, attack_type: str):
        """
        Set the type of attack being performed.

        Args:
            attack_type: Attack type string (e.g., "WPA Handshake Capture")
        """
        self.attack_type = attack_type
        self._render()

    def update_progress(self, progress_data: Dict[str, Any]):
        """
        Update attack progress with new data.

        Args:
            progress_data: Dictionary containing progress information
                - progress: float (0.0 to 1.0) - optional
                - status: str - status message
                - metrics: dict - attack-specific metrics
                - total_time: int - expected total time in seconds (optional)
        """
        if 'progress' in progress_data:
            self.progress_percent = max(0.0, min(1.0, progress_data['progress']))

        if 'status' in progress_data:
            self.status_message = progress_data['status']

        if 'metrics' in progress_data:
            self.metrics.update(progress_data['metrics'])

        if 'total_time' in progress_data:
            self.total_time = progress_data['total_time']

        # Periodic memory cleanup
        self._update_counter += 1
        if self._update_counter % 100 == 0:
            self._cleanup_memory()

        self._render()

    def _cleanup_memory(self):
        """Clean up old data to prevent memory bloat during long attacks."""
        # Clean up old log entries (keep last 500)
        self.log_panel.cleanup_old_entries(keep_count=500)
        
        # Limit metrics dictionary size
        if len(self.metrics) > 50:
            # Keep only the most recent metrics (arbitrary limit)
            keys = list(self.metrics.keys())
            for key in keys[:-50]:
                del self.metrics[key]

    def add_log(self, message: str, timestamp: bool = True):
        """
        Add a log entry.

        Args:
            message: Log message to add
            timestamp: Whether to prepend timestamp
        """
        if timestamp:
            current_time = time.strftime("%H:%M:%S")
            formatted_message = f"[{current_time}] {message}"
        else:
            formatted_message = message

        self.log_panel.add_log(formatted_message)
        self._render()

    def clear_logs(self):
        """Clear all log entries."""
        self.log_panel.clear()
        self._render()

    def _should_auto_refresh(self) -> bool:
        """
        Check if view should auto-refresh to update elapsed time.
        
        Returns:
            True if enough time has passed since last render
        """
        current_time = time.time()
        return (current_time - self._last_render_time) >= self._auto_refresh_interval
    
    def refresh_if_needed(self):
        """
        Refresh the view if auto-refresh interval has passed.
        Call this periodically from attack loops to keep elapsed time updated.
        """
        if self._should_auto_refresh():
            self._render()
    
    def _render(self):
        """Render the complete attack interface."""
        if not self.tui.is_running:
            return

        # Update last render time
        self._last_render_time = time.time()

        # Create main layout
        layout = Layout()
        layout.split_column(
            Layout(name="target_info", size=4),  # Reduced from 5 to 4
            Layout(name="progress", size=8),     # Reduced from 10 to 8
            Layout(name="logs"),                 # Takes remaining space (more room now)
            Layout(name="footer", size=3)
        )

        # Render each section
        layout["target_info"].update(self._render_target_info())
        layout["progress"].update(self._render_progress())
        layout["logs"].update(self._render_logs())
        layout["footer"].update(self._render_footer())

        # Update TUI
        self.tui.update(layout)

    def _render_target_info(self) -> Panel:
        """
        Render target information panel.

        Returns:
            Rich Panel with target details
        """
        # Create target info table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="bold white", width=12)
        table.add_column("Value", style="white")

        # ESSID
        essid = self.target.essid if self.target.essid else "<hidden>"
        table.add_row("ESSID:", essid)

        # BSSID
        table.add_row("BSSID:", self.target.bssid)

        # Channel and Encryption
        enc_badge = EncryptionBadge.render(self.target.encryption, self.target)
        table.add_row("Channel:", f"{self.target.channel}")
        
        # Add resume info if this is a resumed target
        if self.session and self.target_state:
            # Show attempt number
            attempt_text = Text()
            attempt_text.append("Attempt #", style="bold yellow")
            attempt_text.append(str(self.target_state.attempts + 1), style="yellow")
            table.add_row("Resume:", attempt_text)
            
            # Show original attack time if available
            if self.target_state.last_attempt:
                from datetime import datetime
                last_time = datetime.fromtimestamp(self.target_state.last_attempt)
                time_str = last_time.strftime("%Y-%m-%d %H:%M:%S")
                table.add_row("Last Try:", time_str)
        
        # Create a second column for encryption and power
        info_text = Text()
        info_text.append("Encryption: ", style="bold white")
        info_text.append(enc_badge)
        info_text.append("  |  ", style="bright_black")
        info_text.append("Power: ", style="bold white")
        
        # Power level
        power_dbm = self.target.power - 100 if self.target.power > 0 else self.target.power
        info_text.append(SignalStrengthBar.render(power_dbm))

        # Add resume indicator to title if this is a resumed session
        title_text = f"[bold white]Target: {essid}[/bold white]"
        if self.session:
            title_text = f"[bold magenta]RESUMED[/bold magenta] | {title_text}"

        return Panel(
            table,
            title=title_text,
            subtitle=info_text,
            border_style="white",
            padding=(0, 1)
        )

    def _render_progress(self) -> Panel:
        """
        Render attack progress panel.

        Returns:
            Rich Panel with progress information
        """
        elapsed_time = int(time.time() - self.attack_start_time)

        return ProgressPanel.render(
            attack_type=self.attack_type,
            elapsed_time=elapsed_time,
            progress_percent=self.progress_percent,
            status_message=self.status_message,
            metrics=self.metrics,
            total_time=self.total_time
        )

    def _render_logs(self) -> Panel:
        """
        Render log panel.

        Returns:
            Rich Panel with log entries
        """
        return self.log_panel.render(height=10)

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
        footer.append(" Interrupt → (", style="white")
        footer.append("c", style="bold green")
        footer.append("ontinue / ", style="white")
        footer.append("s", style="bold yellow")
        footer.append("kip / ", style="white")
        footer.append("i", style="bold magenta")
        footer.append("gnore / ", style="white")
        footer.append("e", style="bold red")
        footer.append("xit)", style="white")

        return Panel(
            Align.center(footer),
            border_style="white",
            padding=(0, 1)
        )

    def handle_input(self, key: str) -> Optional[str]:
        """
        Handle keyboard input during attack.

        Args:
            key: Key pressed by user

        Returns:
            Action string or None ('skip', 'help', etc.)
        """
        if key == '?':
            self.show_help()
            return 'help'
        # Ctrl+C is handled by the attack module itself
        return None

    def show_help(self):
        """Display help overlay."""
        from .components import HelpOverlay
        from ..util.input import KeyboardInput
        
        # Render help overlay
        help_panel = HelpOverlay.render(context='attack')
        
        # Update display with help
        self.tui.update(help_panel)
        
        # Wait for any key to dismiss
        with KeyboardInput() as kb:
            kb.get_key(timeout=30)  # 30 second timeout
        
        # Re-render normal view
        self._render()


class WEPAttackView(AttackView):
    """Specialized view for WEP attacks."""

    def __init__(self, tui_controller, target, session=None, target_state=None):
        super().__init__(tui_controller, target, session, target_state)
        self.attack_type = "WEP Attack"
        self.ivs_collected = 0
        self.ivs_needed = 10000  # Default
        self.crack_attempts = 0
        self.replay_active = False

    def update_ivs(self, ivs_collected: int, ivs_needed: int = None):
        """
        Update IVs collected for WEP attack.

        Args:
            ivs_collected: Number of IVs collected
            ivs_needed: Number of IVs needed (optional, uses stored value if not provided)
        """
        self.ivs_collected = ivs_collected
        if ivs_needed is not None:
            self.ivs_needed = ivs_needed

        progress = min(1.0, self.ivs_collected / self.ivs_needed) if self.ivs_needed > 0 else 0.0
        
        status = f'Collecting IVs ({self.ivs_collected:,}/{self.ivs_needed:,})'
        if self.replay_active:
            status += " [Replay active]"

        self.update_progress({
            'progress': progress,
            'status': status,
            'metrics': {
                'IVs Collected': f'{self.ivs_collected:,}',
                'IVs Needed': f'{self.ivs_needed:,}',
                'Crack Attempts': self.crack_attempts,
                'Replay': '✓' if self.replay_active else '✗'
            }
        })

    def update_crack_attempt(self, attempt_number: int, success: bool = False):
        """
        Update crack attempt status.

        Args:
            attempt_number: Current crack attempt number
            success: Whether the crack was successful
        """
        self.crack_attempts = attempt_number
        
        if success:
            status = "Key cracked successfully!"
            progress = 1.0
        else:
            status = f'Attempting to crack (attempt #{attempt_number})'
            progress = min(0.95, self.ivs_collected / self.ivs_needed) if self.ivs_needed > 0 else 0.5

        self.update_progress({
            'progress': progress,
            'status': status,
            'metrics': {
                'IVs Collected': f'{self.ivs_collected:,}',
                'Crack Attempts': attempt_number,
                'Status': 'Success' if success else 'In Progress'
            }
        })

    def set_replay_active(self, active: bool):
        """
        Set whether ARP replay is active.

        Args:
            active: Whether replay is active
        """
        self.replay_active = active
        self.update_ivs(self.ivs_collected)


class WPAAttackView(AttackView):
    """Specialized view for WPA attacks."""

    def __init__(self, tui_controller, target, session=None, target_state=None):
        super().__init__(tui_controller, target, session, target_state)
        self.attack_type = "WPA Handshake Capture"
        self.has_handshake = False
        self.clients = 0
        self.deauths_sent = 0
        self.capture_method = "airodump-ng"

    def update_handshake_status(self, has_handshake: bool, clients: int = None, deauths_sent: int = None):
        """
        Update handshake capture status.

        Args:
            has_handshake: Whether handshake has been captured
            clients: Number of clients detected (optional)
            deauths_sent: Number of deauth packets sent (optional)
        """
        self.has_handshake = has_handshake
        if clients is not None:
            self.clients = clients
        if deauths_sent is not None:
            self.deauths_sent = deauths_sent

        if has_handshake:
            status = "Handshake captured!"
            progress = 1.0
        elif self.clients == 0:
            status = "Waiting for clients..."
            progress = 0.2
        elif self.deauths_sent > 0:
            status = f"Deauthing clients (sent {self.deauths_sent})"
            progress = 0.6
        else:
            status = "Monitoring for handshake"
            progress = 0.4

        self.update_progress({
            'progress': progress,
            'status': status,
            'metrics': {
                'Clients': self.clients,
                'Deauths Sent': self.deauths_sent,
                'Handshake': '✓' if has_handshake else '✗',
                'Method': self.capture_method
            }
        })

    def set_capture_method(self, method: str):
        """
        Set the capture method being used.

        Args:
            method: Capture method (e.g., "airodump-ng", "tshark")
        """
        self.capture_method = method
        self.update_handshake_status(self.has_handshake)

    def increment_deauths(self, count: int = 1):
        """
        Increment deauth counter.

        Args:
            count: Number of deauths to add
        """
        self.deauths_sent += count
        self.update_handshake_status(self.has_handshake)


class WPSAttackView(AttackView):
    """Specialized view for WPS attacks."""

    def __init__(self, tui_controller, target, session=None, target_state=None):
        super().__init__(tui_controller, target, session, target_state)
        self.attack_type = "WPS Attack"
        self.pins_tried = 0
        self.total_pins = 11000  # Default for full PIN space
        self.current_pin = None
        self.pixie_dust_mode = False
        self.locked_out = False

    def update_pin_attempts(self, pins_tried: int, total_pins: int = None, current_pin: Optional[str] = None):
        """
        Update WPS PIN attempt progress.

        Args:
            pins_tried: Number of PINs tried
            total_pins: Total number of PINs to try (optional)
            current_pin: Current PIN being tested (optional)
        """
        self.pins_tried = pins_tried
        if total_pins is not None:
            self.total_pins = total_pins
        if current_pin is not None:
            self.current_pin = current_pin

        progress = self.pins_tried / self.total_pins if self.total_pins > 0 else 0.0
        
        if self.locked_out:
            status = "WPS locked out - attack stopped"
            progress = 0.0
        elif self.pixie_dust_mode:
            status = 'Pixie Dust attack in progress'
            progress = 0.5  # Indeterminate for pixie dust
        else:
            status = f'Testing PINs ({self.pins_tried:,}/{self.total_pins:,})'

        metrics = {
            'PINs Tried': f'{self.pins_tried:,}',
            'Total PINs': f'{self.total_pins:,}',
            'Mode': 'Pixie Dust' if self.pixie_dust_mode else 'PIN Brute Force'
        }
        
        if current_pin:
            metrics['Current PIN'] = current_pin

        if self.locked_out:
            metrics['Status'] = 'Locked Out'

        self.update_progress({
            'progress': progress,
            'status': status,
            'metrics': metrics
        })

    def set_pixie_dust_mode(self, enabled: bool):
        """
        Set whether pixie dust attack mode is active.

        Args:
            enabled: Whether pixie dust mode is active
        """
        self.pixie_dust_mode = enabled
        if enabled:
            self.attack_type = "WPS Pixie Dust Attack"
        else:
            self.attack_type = "WPS PIN Attack"
        self.update_pin_attempts(self.pins_tried)

    def set_locked_out(self, locked: bool):
        """
        Set whether WPS is locked out.

        Args:
            locked: Whether WPS is locked out
        """
        self.locked_out = locked
        self.update_pin_attempts(self.pins_tried)

    def update_pixie_dust_status(self, status: str):
        """
        Update pixie dust attack status.

        Args:
            status: Status message for pixie dust attack
        """
        self.update_progress({
            'progress': 0.5,
            'status': status,
            'metrics': {
                'Mode': 'Pixie Dust',
                'Status': status
            }
        })


class PMKIDAttackView(AttackView):
    """Specialized view for PMKID attacks."""

    def __init__(self, tui_controller, target, session=None, target_state=None):
        super().__init__(tui_controller, target, session, target_state)
        self.attack_type = "PMKID Capture"
        self.has_pmkid = False
        self.attempts = 0
        self.max_attempts = 10
        self.capture_tool = "hcxdumptool"

    def update_pmkid_status(self, has_pmkid: bool, attempts: int = None):
        """
        Update PMKID capture status.

        Args:
            has_pmkid: Whether PMKID has been captured
            attempts: Number of capture attempts (optional)
        """
        self.has_pmkid = has_pmkid
        if attempts is not None:
            self.attempts = attempts

        if has_pmkid:
            status = "PMKID captured successfully!"
            progress = 1.0
        elif self.attempts >= self.max_attempts:
            status = f"Failed to capture PMKID after {self.attempts} attempts"
            progress = 0.0
        else:
            status = f"Attempting to capture PMKID (attempt {self.attempts}/{self.max_attempts})"
            progress = min(0.9, self.attempts / self.max_attempts)

        self.update_progress({
            'progress': progress,
            'status': status,
            'metrics': {
                'Attempts': f'{self.attempts}/{self.max_attempts}',
                'PMKID': '✓' if has_pmkid else '✗',
                'Tool': self.capture_tool
            }
        })

    def set_capture_tool(self, tool: str):
        """
        Set the capture tool being used.

        Args:
            tool: Capture tool name (e.g., "hcxdumptool", "hcxpcaptool")
        """
        self.capture_tool = tool
        self.update_pmkid_status(self.has_pmkid)

    def increment_attempts(self):
        """Increment the attempt counter."""
        self.attempts += 1
        self.update_pmkid_status(self.has_pmkid)

    def set_max_attempts(self, max_attempts: int):
        """
        Set maximum number of attempts.

        Args:
            max_attempts: Maximum attempts to try
        """
        self.max_attempts = max_attempts
        self.update_pmkid_status(self.has_pmkid)


class PassivePMKIDAttackView(AttackView):
    """Specialized view for passive PMKID capture attacks."""

    def __init__(self, tui_controller, target=None, session=None, target_state=None):
        # For passive mode, target might be None since we're capturing from all networks
        super().__init__(tui_controller, target, session, target_state)
        self.attack_type = "Passive PMKID Capture"
        self.networks_detected = 0
        self.pmkids_captured = 0
        self.capture_file_size = 0
        self.last_extraction_time = None
        self.extraction_interval = 30
        self.capture_duration_limit = 0  # 0 = infinite
        self.capture_file_path = None

    def update_capture_status(self, networks_detected: int = None, pmkids_captured: int = None, 
                             capture_file_size: int = None, last_extraction: float = None):
        """
        Update passive PMKID capture status.

        Args:
            networks_detected: Number of unique networks detected
            pmkids_captured: Number of PMKIDs successfully captured
            capture_file_size: Size of capture file in bytes
            last_extraction: Timestamp of last hash extraction
        """
        if networks_detected is not None:
            self.networks_detected = networks_detected
        if pmkids_captured is not None:
            self.pmkids_captured = pmkids_captured
        if capture_file_size is not None:
            self.capture_file_size = capture_file_size
        if last_extraction is not None:
            self.last_extraction_time = last_extraction

        # Calculate progress based on duration if limit is set
        elapsed_time = int(time.time() - self.attack_start_time)
        if self.capture_duration_limit > 0:
            progress = min(1.0, elapsed_time / self.capture_duration_limit)
        else:
            # For infinite capture, show indeterminate progress
            progress = 0.5

        # Build status message
        if self.pmkids_captured > 0:
            status = f"Capturing PMKIDs passively ({self.pmkids_captured} captured from {self.networks_detected} networks)"
        elif self.networks_detected > 0:
            status = f"Monitoring {self.networks_detected} networks, waiting for PMKIDs..."
        else:
            status = "Scanning for networks..."

        # Format file size
        if self.capture_file_size > 0:
            if self.capture_file_size >= 1024 * 1024:
                size_str = f"{self.capture_file_size / (1024 * 1024):.1f} MB"
            elif self.capture_file_size >= 1024:
                size_str = f"{self.capture_file_size / 1024:.1f} KB"
            else:
                size_str = f"{self.capture_file_size} bytes"
        else:
            size_str = "0 bytes"

        # Calculate time since last extraction
        if self.last_extraction_time:
            time_since_extraction = int(time.time() - self.last_extraction_time)
            extraction_str = f"{time_since_extraction}s ago"
        else:
            extraction_str = "Never"

        # Build metrics
        metrics = {
            'Networks Detected': f'[white]{self.networks_detected}[/white]',
            'PMKIDs Captured': f'[bold green]{self.pmkids_captured}[/bold green]' if self.pmkids_captured > 0 else f'[dim]{self.pmkids_captured}[/dim]',
            'Capture File Size': f'[yellow]{size_str}[/yellow]',
            'Last Extraction': f'[white]{extraction_str}[/white]',
            'Extraction Interval': f'{self.extraction_interval}s',
        }

        # Add duration info
        if self.capture_duration_limit > 0:
            remaining = max(0, self.capture_duration_limit - elapsed_time)
            remaining_str = f"{remaining // 60}m {remaining % 60}s" if remaining >= 60 else f"{remaining}s"
            metrics['Time Remaining'] = f'[magenta]{remaining_str}[/magenta]'
        else:
            metrics['Duration'] = '[dim]Infinite[/dim]'

        self.update_progress({
            'progress': progress,
            'status': status,
            'metrics': metrics
        })

    def set_extraction_interval(self, interval: int):
        """
        Set the hash extraction interval.

        Args:
            interval: Extraction interval in seconds
        """
        self.extraction_interval = interval
        self.update_capture_status()

    def set_duration_limit(self, duration: int):
        """
        Set the capture duration limit.

        Args:
            duration: Duration limit in seconds (0 = infinite)
        """
        self.capture_duration_limit = duration
        self.update_capture_status()

    def set_capture_file_path(self, path: str):
        """
        Set the capture file path.

        Args:
            path: Path to capture file
        """
        self.capture_file_path = path

    def add_pmkid_captured(self, essid: str, bssid: str):
        """
        Log a newly captured PMKID.

        Args:
            essid: Network ESSID
            bssid: Network BSSID
        """
        self.pmkids_captured += 1
        essid_display = essid if essid else "<hidden>"
        self.add_log(f"[bold green]✓[/bold green] PMKID captured: {essid_display} ({bssid})")
        self.update_capture_status()

    def _render_target_info(self) -> Panel:
        """
        Override target info rendering for passive mode.

        Returns:
            Rich Panel with passive capture information
        """
        # For passive mode, show general capture info instead of specific target
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="bold white", width=18)
        table.add_column("Value", style="white")

        table.add_row("Mode:", "Passive PMKID Capture")
        table.add_row("Capture Method:", "hcxdumptool (passive)")
        
        if self.capture_file_path:
            table.add_row("Capture File:", self.capture_file_path)

        # Show duration info
        elapsed_time = int(time.time() - self.attack_start_time)
        elapsed_str = f"{elapsed_time // 60}m {elapsed_time % 60}s" if elapsed_time >= 60 else f"{elapsed_time}s"
        table.add_row("Capture Duration:", elapsed_str)

        if self.capture_duration_limit > 0:
            limit_str = f"{self.capture_duration_limit // 60}m {self.capture_duration_limit % 60}s" if self.capture_duration_limit >= 60 else f"{self.capture_duration_limit}s"
            table.add_row("Duration Limit:", limit_str)
        else:
            table.add_row("Duration Limit:", "Infinite (Ctrl+C to stop)")

        title_text = "[bold white]Passive PMKID Sniffing[/bold white]"
        if self.session:
            title_text = f"[bold magenta]RESUMED[/bold magenta] | {title_text}"

        return Panel(
            table,
            title=title_text,
            border_style="white",
            padding=(0, 1)
        )


class WPA3AttackView(AttackView):
    """Specialized view for WPA3-SAE attacks."""

    def __init__(self, tui_controller, target, session=None, target_state=None):
        super().__init__(tui_controller, target, session, target_state)
        self.attack_type = "WPA3-SAE Attack"
        self.attack_strategy = "Unknown"
        self.downgrade_attempted = False
        self.downgrade_success = False
        self.sae_frames_captured = 0
        self.has_sae_handshake = False
        self.pmf_status = "unknown"
        self.is_transition = False
        self.clients = 0
        self.deauths_sent = 0

    def set_attack_strategy(self, strategy: str):
        """
        Set the WPA3 attack strategy being used.

        Args:
            strategy: Strategy name (e.g., "downgrade", "sae_capture", "passive", "dragonblood")
        """
        self.attack_strategy = strategy
        
        # Update attack type based on strategy
        if strategy == "downgrade":
            self.attack_type = "WPA3 Downgrade Attack"
        elif strategy == "sae_capture":
            self.attack_type = "WPA3-SAE Handshake Capture"
        elif strategy == "passive":
            self.attack_type = "WPA3-SAE Passive Capture"
        elif strategy == "dragonblood":
            self.attack_type = "WPA3 Dragonblood Exploit"
        else:
            self.attack_type = f"WPA3 Attack ({strategy})"
        
        self._update_display()

    def update_downgrade_status(self, attempted: bool, success: bool = False):
        """
        Update downgrade attack status.

        Args:
            attempted: Whether downgrade was attempted
            success: Whether downgrade was successful
        """
        self.downgrade_attempted = attempted
        self.downgrade_success = success
        self._update_display()

    def update_sae_capture_status(self, frames_captured: int, has_handshake: bool = False):
        """
        Update SAE handshake capture status.

        Args:
            frames_captured: Number of SAE frames captured
            has_handshake: Whether complete handshake has been captured
        """
        self.sae_frames_captured = frames_captured
        self.has_sae_handshake = has_handshake
        self._update_display()

    def update_client_status(self, clients: int, deauths_sent: int = None):
        """
        Update client and deauth status.

        Args:
            clients: Number of clients detected
            deauths_sent: Number of deauth packets sent (optional)
        """
        self.clients = clients
        if deauths_sent is not None:
            self.deauths_sent = deauths_sent
        self._update_display()

    def set_pmf_status(self, pmf_status: str):
        """
        Set PMF (Protected Management Frames) status.

        Args:
            pmf_status: PMF status ('required', 'optional', 'disabled')
        """
        self.pmf_status = pmf_status
        self._update_display()

    def set_transition_mode(self, is_transition: bool):
        """
        Set whether target is in WPA3 transition mode.

        Args:
            is_transition: Whether target supports both WPA2 and WPA3
        """
        self.is_transition = is_transition
        self._update_display()

    def _update_display(self):
        """Update the display with current WPA3 attack status."""
        # Determine status message based on attack strategy and state
        if self.attack_strategy == "downgrade":
            if self.downgrade_success:
                status = "Downgrade successful! Capturing WPA2 handshake..."
                progress = 0.7
            elif self.downgrade_attempted:
                status = "Downgrade failed, falling back to SAE capture"
                progress = 0.3
            else:
                status = "Attempting WPA3 → WPA2 downgrade..."
                progress = 0.2
        elif self.attack_strategy == "passive":
            if self.has_sae_handshake:
                status = "SAE handshake captured (passive mode)!"
                progress = 1.0
            else:
                status = "Passive capture (PMF required) - waiting for clients..."
                progress = 0.4
        elif self.attack_strategy == "dragonblood":
            status = "Attempting Dragonblood vulnerability exploit..."
            progress = 0.5
        else:  # sae_capture or other
            if self.has_sae_handshake:
                status = "SAE handshake captured successfully!"
                progress = 1.0
            elif self.sae_frames_captured > 0:
                status = f"Capturing SAE frames ({self.sae_frames_captured} captured)..."
                progress = 0.6
            elif self.clients == 0:
                status = "Waiting for clients..."
                progress = 0.2
            else:
                status = "Monitoring for SAE authentication..."
                progress = 0.4

        # Build metrics dictionary
        metrics = {
            'Strategy': self.attack_strategy.replace('_', ' ').title(),
            'Clients': self.clients,
        }

        # Add transition mode indicator
        if self.is_transition:
            metrics['Mode'] = 'Transition (WPA2/WPA3)'
        else:
            metrics['Mode'] = 'WPA3-Only'

        # Add PMF status
        if self.pmf_status == 'required':
            metrics['PMF'] = '✓ Required (deauth disabled)'
        elif self.pmf_status == 'optional':
            metrics['PMF'] = '~ Optional'
        else:
            metrics['PMF'] = '✗ Disabled'

        # Add downgrade status if applicable
        if self.attack_strategy == "downgrade" or self.downgrade_attempted:
            if self.downgrade_success:
                metrics['Downgrade'] = '✓ Success'
            elif self.downgrade_attempted:
                metrics['Downgrade'] = '✗ Failed'
            else:
                metrics['Downgrade'] = 'In Progress'

        # Add SAE capture status
        if self.attack_strategy in ["sae_capture", "passive"] or self.sae_frames_captured > 0:
            metrics['SAE Frames'] = self.sae_frames_captured
            metrics['SAE Handshake'] = '✓' if self.has_sae_handshake else '✗'

        # Add deauth count if applicable
        if self.pmf_status != 'required' and self.deauths_sent > 0:
            metrics['Deauths Sent'] = self.deauths_sent

        self.update_progress({
            'progress': progress,
            'status': status,
            'metrics': metrics
        })

    def increment_deauths(self, count: int = 1):
        """
        Increment deauth counter.

        Args:
            count: Number of deauths to add
        """
        self.deauths_sent += count
        self._update_display()


class EvilTwinAttackView(AttackView):
    """Specialized view for Evil Twin attacks."""

    def __init__(self, tui_controller, target, session=None, target_state=None):
        super().__init__(tui_controller, target, session, target_state)
        self.attack_type = "Evil Twin Attack"
        self.attack_phase = "Initializing"
        self.rogue_ap_status = "Stopped"
        self.portal_status = "Stopped"
        self.deauth_status = "Stopped"
        self.connected_clients = []
        self.credential_attempts = []
        self.successful_attempts = 0
        self.failed_attempts = 0
        self.deauths_sent = 0
        self.portal_url = "http://192.168.100.1"
        self.time_to_first_client = None
        self.time_to_first_credential = None
        self.time_to_success = None

    def set_attack_phase(self, phase: str):
        """
        Set the current attack phase.

        Args:
            phase: Phase name (e.g., "Setting up", "Running", "Validating")
        """
        self.attack_phase = phase
        self._update_display()

    def update_rogue_ap_status(self, status: str, channel: int = None, ssid: str = None):
        """
        Update rogue AP status.

        Args:
            status: Status string (e.g., "Running", "Stopped", "Starting")
            channel: Channel number (optional)
            ssid: SSID being broadcast (optional)
        """
        self.rogue_ap_status = status
        if channel is not None:
            self.metrics['AP Channel'] = channel
        if ssid is not None:
            self.metrics['AP SSID'] = ssid
        self._update_display()

    def update_portal_status(self, status: str, url: str = None):
        """
        Update captive portal status.

        Args:
            status: Status string (e.g., "Running", "Stopped")
            url: Portal URL (optional)
        """
        self.portal_status = status
        if url is not None:
            self.portal_url = url
        self._update_display()

    def update_deauth_status(self, status: str, count: int = None, interval: float = None):
        """
        Update deauthentication status with adaptive timing information.

        Args:
            status: Status string (e.g., "Running", "Paused", "Stopped")
            count: Number of deauth packets sent (optional)
            interval: Current adaptive interval in seconds (optional)
        """
        self.deauth_status = status
        if count is not None:
            self.deauths_sent = count
        if interval is not None:
            self.metrics['Deauth Interval'] = f'{interval:.1f}s'
        self._update_display()

    def add_connected_client(self, mac_address: str, ip_address: str = None, hostname: str = None):
        """
        Add a connected client.

        Args:
            mac_address: Client MAC address
            ip_address: Client IP address (optional)
            hostname: Client hostname (optional)
        """
        client_info = {
            'mac': mac_address,
            'ip': ip_address or 'Unknown',
            'hostname': hostname or 'Unknown',
            'connect_time': time.time()
        }
        
        # Check if client already exists
        existing = next((c for c in self.connected_clients if c['mac'] == mac_address), None)
        if not existing:
            self.connected_clients.append(client_info)
            self.add_log(f"[bold green]→[/bold green] Client connected: {mac_address}")
            
            # Track time to first client
            if self.time_to_first_client is None:
                self.time_to_first_client = time.time() - self.attack_start_time
                self.add_log(f"[dim]Time to first client: {self.time_to_first_client:.1f}s[/dim]")
        else:
            # Update existing client info
            if ip_address:
                existing['ip'] = ip_address
            if hostname:
                existing['hostname'] = hostname
        
        self._update_display()

    def remove_connected_client(self, mac_address: str):
        """
        Remove a disconnected client.

        Args:
            mac_address: Client MAC address
        """
        self.connected_clients = [c for c in self.connected_clients if c['mac'] != mac_address]
        self.add_log(f"[bold yellow]←[/bold yellow] Client disconnected: {mac_address}")
        self._update_display()

    def add_credential_attempt(self, mac_address: str, password: str, success: bool):
        """
        Add a credential submission attempt.

        Args:
            mac_address: Client MAC address
            password: Submitted password
            success: Whether validation was successful
        """
        attempt_info = {
            'mac': mac_address,
            'password': password,
            'success': success,
            'timestamp': time.time()
        }
        
        self.credential_attempts.append(attempt_info)
        
        # Track time to first credential
        if self.time_to_first_credential is None:
            self.time_to_first_credential = time.time() - self.attack_start_time
            self.add_log(f"[dim]Time to first credential: {self.time_to_first_credential:.1f}s[/dim]")
        
        if success:
            self.successful_attempts += 1
            # Use rich text formatting for success
            from ..util.logger import mask_sensitive
            self.add_log(f"[bold green]✓[/bold green] Valid credentials from {mac_address}: [bold]{mask_sensitive(password)}[/bold]", timestamp=True)
            # Update phase to show success
            self.set_attack_phase("Validating")
            
            # Track time to success
            if self.time_to_success is None:
                self.time_to_success = time.time() - self.attack_start_time
                self.add_log(f"[bold green]Time to success: {self.time_to_success:.1f}s[/bold green]")
        else:
            self.failed_attempts += 1
            self.add_log(f"[bold red]✗[/bold red] Invalid credentials from {mac_address}", timestamp=True)
        
        self._update_display()

    def increment_deauths(self, count: int = 1):
        """
        Increment deauth counter.

        Args:
            count: Number of deauths to add
        """
        self.deauths_sent += count
        self._update_display()

    def _update_display(self):
        """Update the display with current Evil Twin attack status."""
        # Determine status message and progress based on phase
        phase_config = {
            "Initializing": ("⋯ Initializing Evil Twin attack...", 0.05),
            "Checking dependencies": ("⋯ Checking required dependencies...", 0.10),
            "Setting up": ("⋯ Setting up rogue AP and services...", 0.20),
            "Starting rogue AP": ("⋯ Starting rogue access point...", 0.30),
            "Starting network services": ("⋯ Starting DHCP and DNS services...", 0.40),
            "Starting captive portal": ("⋯ Starting captive portal...", 0.50),
            "Starting deauthentication": ("⋯ Starting deauthentication...", 0.60),
            "Stopping": ("⋯ Stopping attack...", 0.90),
            "Cleaning up": ("⋯ Cleaning up resources...", 0.95),
            "Completed": ("✓ Attack completed successfully!", 1.0),
            "Failed": ("✗ Attack failed", 0.0),
        }
        
        if self.attack_phase == "Running":
            if self.successful_attempts > 0:
                status = "✓ Credentials captured! Validating..."
                progress = 0.95
            elif len(self.connected_clients) > 0:
                status = f"⏳ Waiting for credentials from {len(self.connected_clients)} client(s)..."
                progress = 0.75
            else:
                status = "⏳ Waiting for clients to connect..."
                progress = 0.65
        elif self.attack_phase == "Validating":
            status = "⋯ Validating captured credentials..."
            progress = 0.98
        else:
            status, progress = phase_config.get(self.attack_phase, (self.attack_phase, 0.5))

        # Build metrics dictionary with visual indicators
        metrics = {
            'Phase': self._format_phase_indicator(self.attack_phase),
            'Rogue AP': self._format_status(self.rogue_ap_status),
            'Portal': self._format_status(self.portal_status),
            'Deauth': self._format_status(self.deauth_status),
        }
        
        # Add client and attempt counts with visual emphasis
        if len(self.connected_clients) > 0:
            metrics['Connected Clients'] = f'[bold green]{len(self.connected_clients)}[/bold green]'
        else:
            metrics['Connected Clients'] = f'[dim]{len(self.connected_clients)}[/dim]'
        
        if len(self.credential_attempts) > 0:
            metrics['Credential Attempts'] = f'[bold yellow]{len(self.credential_attempts)}[/bold yellow]'
        else:
            metrics['Credential Attempts'] = f'[dim]{len(self.credential_attempts)}[/dim]'

        # Add success/failure counts if there are attempts
        if len(self.credential_attempts) > 0:
            success_rate = self._get_success_rate()
            if self.successful_attempts > 0:
                metrics['Successful'] = f'[bold green]{self.successful_attempts}[/bold green] ({success_rate:.0f}%)'
            else:
                metrics['Successful'] = f'[dim]{self.successful_attempts}[/dim]'
            
            if self.failed_attempts > 0:
                metrics['Failed'] = f'[bold red]{self.failed_attempts}[/bold red]'
            else:
                metrics['Failed'] = f'[dim]{self.failed_attempts}[/dim]'

        # Add deauth metrics if deauth is active
        if self.deauth_status in ["Running", "Paused"]:
            if self.deauths_sent > 0:
                # Calculate deauths per minute
                elapsed = time.time() - self.attack_start_time
                deauths_per_min = (self.deauths_sent / elapsed * 60) if elapsed > 0 else 0
                metrics['Deauths Sent'] = f'[white]{self.deauths_sent:,}[/white] ([dim]{deauths_per_min:.1f}/min[/dim])'
            else:
                metrics['Deauths Sent'] = '[dim]0[/dim]'
            
            # Show adaptive interval if available
            if 'Deauth Interval' in self.metrics:
                interval_str = self.metrics['Deauth Interval']
                metrics['Deauth Interval'] = f'[yellow]{interval_str}[/yellow] [dim](adaptive)[/dim]'

        # Add portal URL
        if self.portal_status == "Running":
            metrics['Portal URL'] = f'[link={self.portal_url}]{self.portal_url}[/link]'
        
        # Add timing metrics if available
        if self.time_to_first_client is not None:
            metrics['Time to 1st Client'] = f'[white]{self.time_to_first_client:.1f}s[/white]'
        
        if self.time_to_first_credential is not None:
            metrics['Time to 1st Cred'] = f'[yellow]{self.time_to_first_credential:.1f}s[/yellow]'
        
        if self.time_to_success is not None:
            metrics['Time to Success'] = f'[bold green]{self.time_to_success:.1f}s[/bold green]'

        self.update_progress({
            'progress': progress,
            'status': status,
            'metrics': metrics
        })
    
    def _format_phase_indicator(self, phase: str) -> str:
        """
        Format phase with visual indicator.
        
        Args:
            phase: Phase name
            
        Returns:
            Formatted phase string with indicator
        """
        phase_indicators = {
            "Initializing": "⋯",
            "Checking dependencies": "⋯",
            "Setting up": "⋯",
            "Starting rogue AP": "⋯",
            "Starting network services": "⋯",
            "Starting captive portal": "⋯",
            "Starting deauthentication": "⋯",
            "Running": "▶",
            "Validating": "⋯",
            "Stopping": "⏸",
            "Cleaning up": "⋯",
            "Completed": "✓",
            "Failed": "✗",
        }
        
        indicator = phase_indicators.get(phase, "•")
        
        # Color code based on phase
        if phase == "Completed":
            return f"[bold green]{indicator}[/bold green] {phase}"
        elif phase == "Failed":
            return f"[bold red]{indicator}[/bold red] {phase}"
        elif phase == "Running":
            return f"[bold white]{indicator}[/bold white] {phase}"
        elif phase in ["Stopping", "Cleaning up"]:
            return f"[yellow]{indicator}[/yellow] {phase}"
        else:
            return f"[dim]{indicator}[/dim] {phase}"

    def _format_status(self, status: str) -> str:
        """
        Format status with color indicators.

        Args:
            status: Status string

        Returns:
            Formatted status string with indicator
        """
        if status == "Running":
            return "✓ Running"
        elif status == "Stopped":
            return "✗ Stopped"
        elif status == "Paused":
            return "⏸ Paused"
        elif status in ["Starting", "Stopping"]:
            return f"⋯ {status}"
        else:
            return status

    def _get_success_rate(self) -> float:
        """
        Calculate success rate of credential attempts.

        Returns:
            Success rate as percentage (0-100)
        """
        total = len(self.credential_attempts)
        if total == 0:
            return 0.0
        return (self.successful_attempts / total) * 100

    def _render_progress(self) -> Panel:
        """
        Override progress rendering to include client list.

        Returns:
            Rich Panel with progress and client information
        """
        # Get base progress panel
        base_panel = super()._render_progress()
        
        # If we have connected clients, add a client table
        if len(self.connected_clients) > 0:
            from rich.console import Group
            
            # Create client table
            client_table = Table(show_header=True, box=None, padding=(0, 1))
            client_table.add_column("MAC Address", style="white", width=17)
            client_table.add_column("IP Address", style="green", width=15)
            client_table.add_column("Hostname", style="yellow")
            client_table.add_column("Duration", style="white", width=8)
            
            current_time = time.time()
            for client in self.connected_clients[-5:]:  # Show last 5 clients
                duration = int(current_time - client['connect_time'])
                duration_str = f"{duration // 60}m{duration % 60}s" if duration >= 60 else f"{duration}s"
                
                client_table.add_row(
                    client['mac'],
                    client['ip'],
                    client['hostname'][:20] if len(client['hostname']) > 20 else client['hostname'],
                    duration_str
                )
            
            # Combine base panel content with client table
            return Panel(
                Group(base_panel.renderable, Text(), Text("Connected Clients:", style="bold"), client_table),
                title="[bold]Progress[/bold]",
                border_style="white"
            )
        
        return base_panel



class AttackMonitorView(AttackView):
    """Specialized view for wireless attack monitoring."""

    def __init__(self, tui_controller, target=None, session=None, target_state=None):
        # For attack monitoring, target might be None since we're monitoring all networks
        super().__init__(tui_controller, target, session, target_state)
        self.attack_type = "Wireless Attack Monitoring"
        self.deauth_count = 0
        self.disassoc_count = 0
        self.networks_under_attack = {}
        self.attacker_macs = {}
        self.recent_events = []  # Last 100 events
        self.monitor_channel = None
        self.monitor_hop = False

    def update_attack_statistics(self, deauth_count, disassoc_count, 
                                 networks, attackers, recent_events):
        """
        Update attack monitoring statistics.

        Args:
            deauth_count: Total deauth frames detected
            disassoc_count: Total disassoc frames detected
            networks: Dict of networks under attack
            attackers: Dict of attacker MACs
            recent_events: List of recent attack events
        """
        self.deauth_count = deauth_count
        self.disassoc_count = disassoc_count
        self.networks_under_attack = networks
        self.attacker_macs = attackers
        self.recent_events = recent_events[-100:]  # Keep last 100

        total_attacks = deauth_count + disassoc_count
        
        status = f"Monitoring... ({total_attacks:,} attacks detected)"
        
        self.update_progress({
            'progress': 0.5,  # Indeterminate
            'status': status,
            'metrics': {
                'Deauth Frames': f'[red]{deauth_count:,}[/red]',
                'Disassoc Frames': f'[yellow]{disassoc_count:,}[/yellow]',
                'Total Attacks': f'[bold red]{total_attacks:,}[/bold red]',
                'Networks Attacked': f'[white]{len(networks)}[/white]',
                'Unique Attackers': f'[magenta]{len(attackers)}[/magenta]'
            }
        })

    def set_monitor_channel(self, channel):
        """
        Set the monitoring channel.

        Args:
            channel: Channel number or None for current
        """
        self.monitor_channel = channel
        self._render()

    def set_channel_hopping(self, enabled):
        """
        Set channel hopping status.

        Args:
            enabled: Whether channel hopping is enabled
        """
        self.monitor_hop = enabled
        self._render()

    def _render_target_info(self) -> Panel:
        """
        Override to show monitoring info instead of target.

        Returns:
            Rich Panel with monitoring information
        """
        from ..config import Configuration
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="bold white", width=18)
        table.add_column("Value", style="white")

        table.add_row("Mode:", "Attack Monitoring")
        table.add_row("Interface:", Configuration.interface or "Unknown")
        
        if self.monitor_channel:
            table.add_row("Channel:", str(self.monitor_channel))
        elif self.monitor_hop:
            table.add_row("Channel:", "Hopping (all 2.4GHz)")
        else:
            table.add_row("Channel:", "Current")

        elapsed_time = int(time.time() - self.attack_start_time)
        elapsed_str = f"{elapsed_time // 60}m {elapsed_time % 60}s" if elapsed_time >= 60 else f"{elapsed_time}s"
        table.add_row("Duration:", elapsed_str)

        if hasattr(Configuration, 'monitor_duration') and Configuration.monitor_duration is not None and Configuration.monitor_duration > 0:
            limit_str = f"{Configuration.monitor_duration // 60}m {Configuration.monitor_duration % 60}s" if Configuration.monitor_duration >= 60 else f"{Configuration.monitor_duration}s"
            table.add_row("Duration Limit:", limit_str)

        return Panel(
            table,
            title="[bold red]Wireless Attack Monitor[/bold red]",
            border_style="red",
            padding=(0, 1)
        )

    def _render_progress(self) -> Panel:
        """
        Override progress rendering to include attack event log, network list, and attacker list.

        Returns:
            Rich Panel with attack monitoring information
        """
        from rich.console import Group
        
        # Get base progress panel
        elapsed_time = int(time.time() - self.attack_start_time)
        base_panel = ProgressPanel.render(
            attack_type=self.attack_type,
            elapsed_time=elapsed_time,
            progress_percent=self.progress_percent,
            status_message=self.status_message,
            metrics=self.metrics,
            total_time=self.total_time
        )
        
        # Create sections for event log, networks, and attackers
        sections = [base_panel.renderable]
        
        # Add attack event log
        if len(self.recent_events) > 0:
            sections.append(Text())
            sections.append(Text("Recent Attack Events:", style="bold yellow"))
            sections.append(self._render_event_log())
        
        # Add network list
        if len(self.networks_under_attack) > 0:
            sections.append(Text())
            sections.append(Text("Networks Under Attack:", style="bold white"))
            sections.append(self._render_network_list())
        
        # Add attacker list
        if len(self.attacker_macs) > 0:
            sections.append(Text())
            sections.append(Text("Active Attackers:", style="bold magenta"))
            sections.append(self._render_attacker_list())
        
        return Panel(
            Group(*sections),
            title="[bold]Attack Monitoring[/bold]",
            border_style="white"
        )

    def _render_event_log(self) -> Table:
        """
        Render attack event log.

        Returns:
            Rich Table with recent attack events
        """
        event_table = Table(show_header=True, box=None, padding=(0, 1))
        event_table.add_column("Time", style="white", width=8)
        event_table.add_column("Type", style="white", width=8)
        event_table.add_column("Target", style="white", width=25)
        event_table.add_column("Attacker", style="magenta", width=17)
        
        # Show last 10 events
        for event in self.recent_events[-10:]:
            # Format timestamp
            event_time = time.strftime("%H:%M:%S", time.localtime(event.get('timestamp', 0)))
            
            # Color code attack type
            attack_type = event.get('type', 'unknown')
            if attack_type == 'deauth':
                type_str = "[red]Deauth[/red]"
            elif attack_type == 'disassoc':
                type_str = "[yellow]Disassoc[/yellow]"
            else:
                type_str = attack_type
            
            # Format target (ESSID + BSSID)
            essid = event.get('essid', '<hidden>')
            bssid = event.get('bssid', 'Unknown')
            target_str = f"{essid[:15]} ({bssid})" if essid else bssid
            
            # Attacker MAC
            attacker = event.get('source_mac', 'Unknown')
            
            event_table.add_row(event_time, type_str, target_str, attacker)
        
        return event_table

    def _render_network_list(self) -> Table:
        """
        Render list of networks under attack.

        Returns:
            Rich Table with network attack statistics
        """
        network_table = Table(show_header=True, box=None, padding=(0, 1))
        network_table.add_column("ESSID", style="white", width=20)
        network_table.add_column("BSSID", style="white", width=17)
        network_table.add_column("Attacks", style="red", width=8, justify="right")
        network_table.add_column("Last Seen", style="yellow", width=8)
        
        # Sort networks by attack count (descending) and take top 20
        sorted_networks = sorted(
            self.networks_under_attack.items(),
            key=lambda x: x[1].get('count', 0),
            reverse=True
        )[:20]
        
        current_time = time.time()
        for bssid, network_info in sorted_networks:
            essid = network_info.get('essid', '<hidden>')
            attack_count = network_info.get('count', 0)
            last_seen = network_info.get('last_seen', 0)
            
            # Calculate time since last attack
            time_diff = int(current_time - last_seen)
            if time_diff < 60:
                last_seen_str = f"{time_diff}s ago"
            elif time_diff < 3600:
                last_seen_str = f"{time_diff // 60}m ago"
            else:
                last_seen_str = f"{time_diff // 3600}h ago"
            
            network_table.add_row(
                essid[:20] if essid else '<hidden>',
                bssid,
                f"{attack_count:,}",
                last_seen_str
            )
        
        return network_table

    def _render_attacker_list(self) -> Table:
        """
        Render list of attacker MACs.

        Returns:
            Rich Table with attacker statistics
        """
        attacker_table = Table(show_header=True, box=None, padding=(0, 1))
        attacker_table.add_column("Attacker MAC", style="magenta", width=17)
        attacker_table.add_column("Attacks", style="red", width=8, justify="right")
        attacker_table.add_column("Targets", style="white", width=8, justify="right")
        
        # Sort attackers by attack count (descending) and take top 10
        sorted_attackers = sorted(
            self.attacker_macs.items(),
            key=lambda x: x[1].get('count', 0),
            reverse=True
        )[:10]
        
        for mac, attacker_info in sorted_attackers:
            attack_count = attacker_info.get('count', 0)
            target_count = len(attacker_info.get('targets', set()))
            
            attacker_table.add_row(
                mac,
                f"{attack_count:,}",
                str(target_count)
            )
        
        return attacker_table
