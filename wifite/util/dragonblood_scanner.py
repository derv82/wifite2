#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dragonblood Scanner

Scans WPA3 networks for Dragonblood vulnerabilities without attacking.
"""

from ..util.color import Color
from ..util.dragonblood import DragonbloodDetector
from ..util.wpa3 import WPA3Detector


class DragonbloodScanner:
    """Scanner for Dragonblood vulnerabilities in WPA3 networks."""
    
    @staticmethod
    def scan_targets(targets):
        """
        Scan targets for Dragonblood vulnerabilities.
        
        Args:
            targets: List of Target objects
        
        Returns:
            Dictionary with scan results
        """
        Color.pl('\n{+} {C}Scanning for Dragonblood vulnerabilities...{W}\n')
        
        wpa3_targets = []
        vulnerable_targets = []
        
        for target in targets:
            # Only check WPA3 networks
            if not hasattr(target, 'authentication') or 'SAE' not in target.authentication:
                continue
            
            wpa3_targets.append(target)
            
            # Detect WPA3 capabilities
            wpa3_info = WPA3Detector.detect_wpa3_capability(target)
            
            if not wpa3_info:
                continue
            
            # Check for vulnerabilities
            vuln_info = DragonbloodDetector.check_vulnerability(wpa3_info)
            
            if vuln_info['vulnerable']:
                vulnerable_targets.append({
                    'target': target,
                    'wpa3_info': wpa3_info,
                    'vuln_info': vuln_info
                })
        
        # Display results
        DragonbloodScanner._display_scan_results(
            len(targets),
            len(wpa3_targets),
            vulnerable_targets
        )
        
        return {
            'total_targets': len(targets),
            'wpa3_targets': len(wpa3_targets),
            'vulnerable_count': len(vulnerable_targets),
            'vulnerable_targets': vulnerable_targets
        }
    
    @staticmethod
    def _display_scan_results(total, wpa3_count, vulnerable):
        """Display scan results summary."""
        Color.pl('{+} {C}Dragonblood Scan Results:{W}')
        Color.pl('{+} Total networks scanned: {G}%d{W}' % total)
        Color.pl('{+} WPA3 networks found: {G}%d{W}' % wpa3_count)
        Color.pl('{+} Vulnerable networks: {R}%d{W}\n' % len(vulnerable))
        
        if len(vulnerable) == 0:
            Color.pl('{+} {G}No Dragonblood vulnerabilities detected{W}\n')
            return
        
        # Display each vulnerable network
        for i, vuln_target in enumerate(vulnerable, 1):
            target = vuln_target['target']
            vuln_info = vuln_target['vuln_info']
            
            Color.pl('{+} {O}Vulnerable Network #%d:{W}' % i)
            DragonbloodDetector.print_vulnerability_report(
                target.essid,
                target.bssid,
                vuln_info,
                verbose=True
            )
            Color.pl('')
