#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classic text output mode for wifite2
Maintains backward compatibility with the original scrolling text interface
"""

from ..util.color import Color


class ClassicScannerOutput:
    """Classic text-based scanner output"""
    
    def __init__(self):
        self.targets = []
        self.last_target_count = 0
    
    def update_targets(self, targets):
        """
        Update and display targets (classic scrolling mode)
        
        Args:
            targets: List of Target objects
        """
        self.targets = targets
        
        # Only print when new targets are found to avoid spam
        if len(targets) > self.last_target_count:
            new_count = len(targets) - self.last_target_count
            Color.pl('{+} Found {G}%d{W} new target(s), total: {G}%d{W}' % (new_count, len(targets)))
            self.last_target_count = len(targets)
    
    def display_targets(self, targets, show_bssid=False, show_manufacturer=False):
        """
        Display targets in classic table format
        
        Args:
            targets: List of Target objects
            show_bssid: Show BSSID column
            show_manufacturer: Show manufacturer column
        """
        if not targets:
            Color.pl('{!} {R}No targets found{W}')
            return
        
        Color.pl('')
        Color.pl('{+} {C}Targets{W}')
        Color.pl('')
        
        # Print header (column widths must match target.to_str())
        col_num = 5
        col_essid = 26
        col_bssid = 19
        col_mfg = 23
        col_ch = 4
        col_enc = 9
        col_pwr = 7
        col_wps = 5
        col_cli = 7

        header = '  ' + 'NUM'.rjust(col_num)
        header += '  ' + 'ESSID'.ljust(col_essid)
        if show_bssid:
            header += '  ' + 'BSSID'.ljust(col_bssid)
        if show_manufacturer:
            header += '  ' + 'MANUFACTURER'.ljust(col_mfg)
        header += '  ' + 'CH'.rjust(col_ch)
        header += '  ' + 'ENCR'.ljust(col_enc)
        header += '  ' + 'PWR'.rjust(col_pwr)
        header += '  ' + 'WPS'.center(col_wps)
        header += '  ' + 'CLI'.rjust(col_cli)
        Color.pl(header)
        Color.pl('  ' + '-' * (len(header) - 2))
        
        # Print targets
        for idx, target in enumerate(targets, start=1):
            target_str = target.to_str(show_bssid=show_bssid, show_manufacturer=show_manufacturer)
            Color.pl(' {G}%s{W}  %s' % (str(idx).rjust(col_num), target_str))
        
        Color.pl('')


class ClassicSelectorOutput:
    """Classic text-based target selector"""
    
    def __init__(self, targets):
        self.targets = targets
    
    def select_targets(self):
        """
        Prompt user to select targets (classic input mode)
        
        Returns:
            List of selected Target objects
        """
        if not self.targets:
            return []
        
        Color.pl('')
        Color.pl('{+} Select target(s) ({G}1-%d{W}) separated by commas, or {G}all{W}:' % len(self.targets))
        Color.p('{?} ')
        
        try:
            answer = input().strip().lower()
        except (KeyboardInterrupt, EOFError):
            return []
        
        if answer == 'all':
            return self.targets
        
        # Parse comma-separated numbers
        selected = []
        try:
            for part in answer.split(','):
                part = part.strip()
                if '-' in part:
                    # Range like "1-5"
                    start, end = part.split('-')
                    start_idx = int(start) - 1
                    end_idx = int(end)
                    selected.extend(self.targets[start_idx:end_idx])
                else:
                    # Single number
                    idx = int(part) - 1
                    if 0 <= idx < len(self.targets):
                        selected.append(self.targets[idx])
        except (ValueError, IndexError):
            Color.pl('{!} {R}Invalid selection{W}')
            return []
        
        return selected


class ClassicAttackOutput:
    """Classic text-based attack output"""
    
    def __init__(self, target):
        self.target = target
        self.attack_type = None
        self.start_time = None
    
    def set_attack_type(self, attack_type):
        """
        Set the current attack type
        
        Args:
            attack_type: String describing attack (e.g., "WPA Handshake", "WPS PIN")
        """
        self.attack_type = attack_type
        Color.pl('\n{+} Starting {C}%s{W} attack on {C}%s{W}' % (attack_type, self.target.essid))
    
    def update_progress(self, progress_data):
        """
        Update attack progress (classic print mode)
        
        Args:
            progress_data: Dict with progress information
                - status: Status message
                - progress: Progress percentage (0.0-1.0)
                - metrics: Dict of attack-specific metrics
        """
        status = progress_data.get('status', '')
        progress = progress_data.get('progress', 0)
        metrics = progress_data.get('metrics', {})
        
        # Print status
        if status:
            Color.pl('{.} %s' % status)
        
        # Print metrics
        for key, value in metrics.items():
            Color.pl('{.} %s: {C}%s{W}' % (key, value))
    
    def add_log(self, message, level='info'):
        """
        Add log message (classic print mode)
        
        Args:
            message: Log message
            level: Log level ('info', 'success', 'warning', 'error')
        """
        if level == 'success':
            Color.pl('{+} {G}%s{W}' % message)
        elif level == 'warning':
            Color.pl('{!} {O}%s{W}' % message)
        elif level == 'error':
            Color.pl('{!} {R}%s{W}' % message)
        else:
            Color.pl('{.} %s' % message)
    
    def show_result(self, success, result_data=None):
        """
        Show attack result
        
        Args:
            success: Boolean indicating if attack succeeded
            result_data: Dict with result information (key, pin, etc.)
        """
        if success:
            Color.pl('\n{+} {G}Attack successful!{W}')
            if result_data:
                for key, value in result_data.items():
                    Color.pl('{+} %s: {G}%s{W}' % (key, value))
        else:
            Color.pl('\n{!} {R}Attack failed{W}')


# Backward compatibility aliases
ScannerOutput = ClassicScannerOutput
SelectorOutput = ClassicSelectorOutput
AttackOutput = ClassicAttackOutput
