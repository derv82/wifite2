#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OWE Vulnerability Scanner

Scans for OWE transition mode vulnerabilities without attacking.
"""

from ..util.color import Color
from ..util.owe import OWEDetector


class OWEScanner:
    """Scanner for OWE transition mode vulnerabilities."""

    @staticmethod
    def scan_targets(targets):
        """
        Scan targets for OWE transition mode vulnerabilities.

        Args:
            targets: List of Target objects

        Returns:
            Dictionary with scan results
        """
        Color.pl('\n{+} {C}Scanning for OWE transition mode vulnerabilities...{W}\n')

        # Scan for OWE vulnerabilities
        results = OWEDetector.scan_owe_vulnerabilities(targets)

        # Display results
        OWEScanner._display_scan_results(results)

        return results

    @staticmethod
    def _display_scan_results(results):
        """Display OWE scan results."""
        # Print summary
        OWEDetector.print_scan_summary(results)

        # Print transition pairs if found
        if results['transition_pairs']:
            OWEDetector.print_transition_pairs(results['transition_pairs'], verbose=True)

        # Print individual OWE networks with transition mode
        for target in results['owe_networks']:
            owe_info = OWEDetector.detect_owe_capability(target)
            if owe_info and owe_info['transition_mode']:
                OWEDetector.print_owe_info(target, owe_info, verbose=True)
