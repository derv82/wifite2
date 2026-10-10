#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Wireless Attack Monitoring Module

Implements passive monitoring of wireless attacks such as deauthentication
and disassociation frames. Provides real-time visualization through TUI
and comprehensive logging capabilities.
"""

from ..config import Configuration
from ..util.color import Color
from ..tools.tshark import TsharkMonitor
from ..util.process import Process
import time

# TUI imports (optional)
try:
    from ..ui.attack_view import AttackMonitorView
    TUI_AVAILABLE = True
except ImportError:
    TUI_AVAILABLE = False


class AttackMonitor:
    """
    Wireless attack monitoring system.
    Detects deauth/disassoc frames and provides real-time visualization.
    """

    def __init__(self, tui_controller=None):
        """
        Initialize attack monitor.

        Sets up attack tracking dictionaries, statistics, and log file handling.
        Initializes TUI view if controller is provided.

        Args:
            tui_controller: Optional TUIController instance for TUI mode
        """
        # TsharkMonitor process reference
        self.tshark_monitor = None

        # Log file handling
        self.log_file = None
        self.log_file_handle = None
        self.log_buffer = []  # Buffer for performance
        self.last_log_flush = time.time()

        # Attack tracking
        # List of recent attack events (limited to last 100)
        self.attack_events = []

        # Dictionary tracking networks under attack
        # Format: {bssid: {'essid': str, 'count': int, 'last_seen': float,
        #                  'first_seen': float, 'attack_types': {'deauth': int, 'disassoc': int}}}
        self.networks_under_attack = {}

        # Dictionary tracking attacker MACs
        # Format: {mac: {'count': int, 'targets': set(), 'first_seen': float,
        #                'last_seen': float, 'attack_types': {'deauth': int, 'disassoc': int}}}
        self.attacker_macs = {}

        # Statistics dictionary
        self.statistics = {
            'deauth_count': 0,
            'disassoc_count': 0,
            'total_attacks': 0,
            'unique_networks': 0,
            'unique_attackers': 0,
            'start_time': None,
            'duration_seconds': 0
        }

        # TUI support
        self.tui_controller = tui_controller
        self.tui_view = None
        if tui_controller and TUI_AVAILABLE:
            self.tui_view = AttackMonitorView(tui_controller)

    def validate_dependencies(self):
        """
        Validate required tools are installed.

        Checks for tshark availability.
        Displays error message with installation instructions if missing.

        Returns:
            bool: True if dependencies are satisfied, False otherwise
        """
        if not Process.exists('tshark'):
            Color.pl('{!} {R}Missing required tool:{W} {O}tshark{W}')
            Color.pl('{!} {O}Install with:{W} {C}apt install tshark{W}')
            Color.pl('{!} {O}Or visit:{W} {C}https://www.wireshark.org/download.html{W}')
            return False

        return True

    def start_monitoring(self):
        """
        Start tshark process with attack frame filters.

        Creates TsharkMonitor instance and starts capture.
        Applies filters for deauth (0x0c) and disassoc (0x0a) frames.

        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            # Determine channel
            channel = Configuration.monitor_channel if Configuration.monitor_channel else None

            # Create TsharkMonitor instance
            self.tshark_monitor = TsharkMonitor(
                interface=Configuration.interface,
                channel=channel
            )

            # Start tshark process
            self.tshark_monitor.start()

            if self.tui_view:
                self.tui_view.add_log('TShark monitoring started')
                if channel:
                    self.tui_view.add_log(f'Monitoring channel: {channel}')
                else:
                    self.tui_view.add_log('Monitoring current channel')
            else:
                Color.pl('{+} {G}TShark monitoring started{W}')
                if channel:
                    Color.pl('{+} Monitoring channel: {G}%d{W}' % channel)
                else:
                    Color.pl('{+} Monitoring current channel')

            return True

        except Exception as e:
            error_msg = f'Failed to start monitoring: {str(e)}'
            if self.tui_view:
                self.tui_view.add_log(f'[red]✗[/red] {error_msg}')
            else:
                Color.pl('{!} {R}%s{W}' % error_msg)
            return False

    def parse_frame(self, frame_data):
        """
        Parse captured frame and detect attacks.

        Extracts frame type, source MAC, destination MAC, and BSSID.
        Creates attack event object.
        Determines attack type (deauth or disassoc).

        Args:
            frame_data: Dictionary containing frame fields from tshark

        Returns:
            dict: Attack event object, or None if parsing failed
        """
        if not frame_data:
            return None

        try:
            # Extract frame type
            frame_type = frame_data.get('frame_type', '')

            # Determine attack type based on frame type
            # 0x0c = Deauthentication (12 decimal)
            # 0x0a = Disassociation (10 decimal)
            attack_type = None
            if frame_type == '12' or frame_type == '0x0c':
                attack_type = 'deauth'
            elif frame_type == '10' or frame_type == '0x0a':
                attack_type = 'disassoc'
            else:
                # Unknown frame type, skip
                return None

            # Extract MAC addresses
            source_mac = frame_data.get('source_mac', '').upper()
            dest_mac = frame_data.get('dest_mac', '').upper()
            bssid = frame_data.get('bssid', '').upper()

            # Validate MAC addresses
            if not source_mac or not dest_mac or not bssid:
                return None

            # Extract timestamp and channel
            timestamp = frame_data.get('timestamp', time.time())
            channel = frame_data.get('channel', None)

            # Create attack event object
            attack_event = {
                'timestamp': timestamp,
                'type': attack_type,
                'source_mac': source_mac,
                'dest_mac': dest_mac,
                'bssid': bssid,
                'essid': None,  # Will be populated if known
                'channel': channel
            }

            return attack_event

        except Exception as e:
            if Configuration.verbose > 1:
                Color.pl('{!} {R}Error parsing frame:{W} %s' % str(e))
            return None

    def track_attack(self, attack_event):
        """
        Track attack event and update statistics.

        Updates networks_under_attack dictionary.
        Updates attacker_macs dictionary.
        Updates attack counters.
        Adds event to attack_events list.

        Args:
            attack_event: Attack event dictionary
        """
        if not attack_event:
            return

        bssid = attack_event['bssid']
        source_mac = attack_event['source_mac']
        attack_type = attack_event['type']
        timestamp = attack_event['timestamp']

        # Track network under attack
        if bssid not in self.networks_under_attack:
            self.networks_under_attack[bssid] = {
                'essid': attack_event.get('essid', ''),
                'count': 0,
                'first_seen': timestamp,
                'last_seen': timestamp,
                'attack_types': {'deauth': 0, 'disassoc': 0}
            }

        # Update network statistics
        self.networks_under_attack[bssid]['count'] += 1
        self.networks_under_attack[bssid]['last_seen'] = timestamp
        self.networks_under_attack[bssid]['attack_types'][attack_type] += 1

        # Track attacker MAC
        if source_mac not in self.attacker_macs:
            self.attacker_macs[source_mac] = {
                'count': 0,
                'targets': set(),
                'first_seen': timestamp,
                'last_seen': timestamp,
                'attack_types': {'deauth': 0, 'disassoc': 0}
            }

        # Update attacker statistics
        self.attacker_macs[source_mac]['count'] += 1
        self.attacker_macs[source_mac]['targets'].add(bssid)
        self.attacker_macs[source_mac]['last_seen'] = timestamp
        self.attacker_macs[source_mac]['attack_types'][attack_type] += 1

        # Update global counters
        if attack_type == 'deauth':
            self.statistics['deauth_count'] += 1
        elif attack_type == 'disassoc':
            self.statistics['disassoc_count'] += 1

        self.statistics['total_attacks'] += 1
        self.statistics['unique_networks'] = len(self.networks_under_attack)
        self.statistics['unique_attackers'] = len(self.attacker_macs)

        # Add to recent events list (limit to 100)
        self.attack_events.append(attack_event)
        if len(self.attack_events) > 100:
            self.attack_events.pop(0)

    def setup_logging(self):
        """
        Set up log file for attack events.

        Creates log file with timestamp in filename.
        Opens file handle for writing.
        Writes header line.

        Returns:
            bool: True if log file created successfully
        """
        # Determine log file path
        if Configuration.monitor_log_file:
            self.log_file = Configuration.monitor_log_file
        else:
            # Generate default log file name with timestamp
            timestamp = time.strftime('%Y-%m-%dT%H-%M-%S')
            self.log_file = f'attack_monitor_{timestamp}.log'

        try:
            # Open log file for writing
            self.log_file_handle = open(self.log_file, 'w')

            # Write header
            header = 'timestamp,attack_type,source_mac,dest_mac,bssid,essid,channel\n'
            self.log_file_handle.write(header)
            self.log_file_handle.flush()

            if self.tui_view:
                self.tui_view.add_log(f'Log file: {self.log_file}')
            else:
                Color.pl('{+} Log file: {C}%s{W}' % self.log_file)

            return True

        except Exception as e:
            error_msg = f'Failed to create log file: {str(e)}'
            if self.tui_view:
                self.tui_view.add_log(f'[red]✗[/red] {error_msg}')
            else:
                Color.pl('{!} {R}%s{W}' % error_msg)
            return False

    def log_attack_event(self, event):
        """
        Log attack event to file.

        Formats log entry with timestamp, attack type, and MAC addresses.
        Buffers entries for performance.
        Flushes buffer periodically.

        Args:
            event: Attack event dictionary
        """
        if not self.log_file_handle:
            return

        try:
            # Format timestamp as ISO 8601
            timestamp_str = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(event['timestamp']))

            # Format log entry as CSV
            # Convert channel to string if it's an integer
            channel_str = str(event.get('channel', '')) if event.get('channel') is not None else ''
            
            log_entry = '%s,%s,%s,%s,%s,%s,%s\n' % (
                timestamp_str,
                event['type'],
                event['source_mac'],
                event['dest_mac'],
                event['bssid'],
                event.get('essid', ''),
                channel_str
            )

            # Add to buffer
            self.log_buffer.append(log_entry)

            # Flush buffer if it's been more than 5 seconds or buffer is large
            current_time = time.time()
            if (current_time - self.last_log_flush > 5) or len(self.log_buffer) >= 100:
                self.flush_log_buffer()

        except Exception as e:
            if Configuration.verbose > 1:
                Color.pl('{!} {R}Error logging event:{W} %s' % str(e))

    def flush_log_buffer(self):
        """
        Flush buffered log entries to disk.

        Writes all buffered entries to log file.
        Clears buffer after writing.
        Updates last flush timestamp.
        """
        if not self.log_file_handle or not self.log_buffer:
            return

        try:
            # Write all buffered entries
            for entry in self.log_buffer:
                self.log_file_handle.write(entry)

            # Flush to disk
            self.log_file_handle.flush()

            # Clear buffer
            self.log_buffer = []
            self.last_log_flush = time.time()

        except Exception as e:
            if Configuration.verbose > 1:
                Color.pl('{!} {R}Error flushing log buffer:{W} %s' % str(e))

    def update_statistics(self):
        """
        Update statistics and TUI.

        Calculates current statistics from tracking dictionaries.
        Updates TUI view if available.
        """
        # Update duration
        if self.statistics['start_time']:
            self.statistics['duration_seconds'] = int(time.time() - self.statistics['start_time'])

        # Update TUI if available
        if self.tui_view:
            # Sort networks by attack count
            sorted_networks = sorted(
                self.networks_under_attack.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:20]  # Top 20

            # Sort attackers by attack count
            sorted_attackers = sorted(
                self.attacker_macs.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]  # Top 10

            # Update TUI view
            self.tui_view.update_attack_statistics(
                deauth_count=self.statistics['deauth_count'],
                disassoc_count=self.statistics['disassoc_count'],
                networks=dict(sorted_networks),
                attackers=dict(sorted_attackers),
                recent_events=self.attack_events
            )

    def run(self):
        """
        Main monitoring loop.

        Validates dependencies.
        Displays legal warning.
        Starts tshark process.
        Reads and parses frames in real-time.
        Updates statistics and TUI.
        Handles duration timeout.
        Handles keyboard interrupt.
        Calls cleanup on exit.

        Returns:
            bool: True if monitoring completed successfully
        """
        # Validate dependencies
        if not self.validate_dependencies():
            return False

        try:
            # Start TUI view if available
            if self.tui_view:
                self.tui_view.start()

            # Display startup message
            if self.tui_view:
                self.tui_view.add_log('[bold green]Starting Wireless Attack Monitor[/bold green]')
                self.tui_view.add_log(f'Interface: {Configuration.interface}')
            else:
                Color.pl('{+} {C}Starting Wireless Attack Monitor...{W}')
                Color.pl('{+} Interface: {G}%s{W}' % Configuration.interface)

            # Set up logging
            if not self.setup_logging():
                if self.tui_view:
                    self.tui_view.add_log('[yellow]Warning:[/yellow] Continuing without logging')
                else:
                    Color.pl('{!} {O}Warning:{W} Continuing without logging')

            # Start monitoring
            if not self.start_monitoring():
                return False

            # Record start time
            self.statistics['start_time'] = time.time()

            # Calculate end time if duration is specified
            end_time = None
            if Configuration.monitor_duration and Configuration.monitor_duration > 0:
                end_time = time.time() + Configuration.monitor_duration
                if self.tui_view:
                    self.tui_view.add_log(f'Duration: {Configuration.monitor_duration} seconds')
                else:
                    Color.pl('{+} Duration: {G}%d seconds{W}' % Configuration.monitor_duration)
            else:
                if self.tui_view:
                    self.tui_view.add_log('Duration: infinite (press Ctrl+C to stop)')
                else:
                    Color.pl('{+} Duration: {G}infinite{W} (press Ctrl+C to stop)')

            if not self.tui_view:
                Color.pl('')

            # Main monitoring loop
            try:
                while True:
                    # Check if duration timeout reached
                    if end_time and time.time() >= end_time:
                        if self.tui_view:
                            self.tui_view.add_log('Duration timeout reached')
                        else:
                            Color.pl('\n{+} {G}Duration timeout reached{W}')
                        break

                    # Read frame from tshark
                    frame_data = self.tshark_monitor.read_frame()

                    if frame_data:
                        # Parse frame and detect attack
                        attack_event = self.parse_frame(frame_data)

                        if attack_event:
                            # Track attack
                            self.track_attack(attack_event)

                            # Log attack event
                            self.log_attack_event(attack_event)

                            # Update statistics and TUI
                            self.update_statistics()

                    # Display statistics in classic mode
                    if not self.tui_view:
                        self.display_statistics()

                    # Brief sleep to prevent CPU spinning
                    time.sleep(0.01)

            except KeyboardInterrupt:
                if self.tui_view:
                    self.tui_view.add_log('Interrupted by user')
                else:
                    Color.pl('\n{!} {O}Interrupted by user{W}')

            # Cleanup
            self.cleanup()

        except Exception as e:
            error_msg = f'Error during monitoring: {str(e)}'
            if self.tui_view:
                self.tui_view.add_log(f'[red]✗[/red] {error_msg}')
            else:
                Color.pl('\n{!} {R}%s{W}' % error_msg)

            if Configuration.verbose > 0:
                import traceback
                if self.tui_view:
                    self.tui_view.add_log(traceback.format_exc())
                else:
                    Color.pl('{!} {R}%s{W}' % traceback.format_exc())
            
            # Ensure cleanup happens even on exception
            self.cleanup()
            return False
        finally:
            # Stop TUI view if it was started
            if self.tui_view:
                self.tui_view.stop()

        return True

    def display_statistics(self):
        """
        Display real-time monitoring statistics in classic mode.

        Shows attack counts, networks, attackers, and duration.
        Updates display on same line without clearing screen.
        """
        # Calculate duration
        if self.statistics['start_time']:
            self.statistics['duration_seconds'] = int(time.time() - self.statistics['start_time'])

        # Format duration as HH:MM:SS
        duration = self.statistics['duration_seconds']
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        duration_str = f'{hours:02d}:{minutes:02d}:{seconds:02d}'

        # Display statistics
        Color.clear_entire_line()
        Color.p('\r{+} {C}Attacks:{W} {G}%d{W} ({R}%d deauth{W}, {O}%d disassoc{W}) | {C}Networks:{W} {G}%d{W} | {C}Attackers:{W} {G}%d{W} | {C}Time:{W} {G}%s{W}' % (
            self.statistics['total_attacks'],
            self.statistics['deauth_count'],
            self.statistics['disassoc_count'],
            self.statistics['unique_networks'],
            self.statistics['unique_attackers'],
            duration_str
        ))

    def cleanup(self):
        """
        Stop monitoring and cleanup.

        Stops tshark process gracefully.
        Flushes and closes log file.
        Displays final statistics.
        """
        if self.tui_view:
            self.tui_view.add_log('Cleaning up...')
        else:
            Color.pl('\n{+} {C}Cleaning up...{W}')

        # Stop tshark monitor
        if self.tshark_monitor:
            try:
                self.tshark_monitor.stop()
                if self.tui_view:
                    self.tui_view.add_log('TShark monitoring stopped')
                else:
                    Color.pl('{+} {G}TShark monitoring stopped{W}')
            except Exception as e:
                if Configuration.verbose > 1:
                    Color.pl('{!} {R}Error stopping tshark:{W} %s' % str(e))

        # Flush and close log file
        if self.log_file_handle:
            try:
                self.flush_log_buffer()
                self.log_file_handle.close()
                if self.tui_view:
                    self.tui_view.add_log('Log file closed')
                else:
                    Color.pl('{+} {G}Log file closed{W}')
            except Exception as e:
                if Configuration.verbose > 1:
                    Color.pl('{!} {R}Error closing log file:{W} %s' % str(e))

        # Display final statistics
        self.display_final_statistics()

    def __del__(self):
        """Ensure log file handle is closed even if stop() was never called."""
        if self.log_file_handle and not self.log_file_handle.closed:
            try:
                self.log_file_handle.close()
            except Exception:
                pass

    def display_final_statistics(self):
        """
        Display final monitoring statistics.

        Shows summary of attacks detected, networks, attackers, and duration.
        """
        # Calculate final duration
        if self.statistics['start_time']:
            self.statistics['duration_seconds'] = int(time.time() - self.statistics['start_time'])

        if self.tui_view:
            self.tui_view.add_log('')
            self.tui_view.add_log('[bold green]Wireless Attack Monitoring Complete[/bold green]')
            self.tui_view.add_log(f'Total attacks detected: {self.statistics["total_attacks"]}')
            self.tui_view.add_log(f'  - Deauth frames: {self.statistics["deauth_count"]}')
            self.tui_view.add_log(f'  - Disassoc frames: {self.statistics["disassoc_count"]}')
            self.tui_view.add_log(f'Unique networks attacked: {self.statistics["unique_networks"]}')
            self.tui_view.add_log(f'Unique attackers detected: {self.statistics["unique_attackers"]}')
            self.tui_view.add_log(f'Monitoring duration: {self.statistics["duration_seconds"]} seconds')
            if self.log_file:
                self.tui_view.add_log(f'Log file: {self.log_file}')
            self.tui_view.add_log('')
        else:
            Color.pl('')
            Color.pl('{+} {G}Wireless Attack Monitoring Complete{W}')
            Color.pl('{+} Total attacks detected: {G}%d{W}' % self.statistics['total_attacks'])
            Color.pl('{+}   - Deauth frames: {R}%d{W}' % self.statistics['deauth_count'])
            Color.pl('{+}   - Disassoc frames: {O}%d{W}' % self.statistics['disassoc_count'])
            Color.pl('{+} Unique networks attacked: {G}%d{W}' % self.statistics['unique_networks'])
            Color.pl('{+} Unique attackers detected: {G}%d{W}' % self.statistics['unique_attackers'])
            Color.pl('{+} Monitoring duration: {G}%d seconds{W}' % self.statistics['duration_seconds'])
            if self.log_file:
                Color.pl('{+} Log file: {C}%s{W}' % self.log_file)
            Color.pl('')
