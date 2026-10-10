#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OWE (Opportunistic Wireless Encryption) Detection and Analysis

This module detects OWE networks and identifies transition mode vulnerabilities.

OWE (Enhanced Open):
- Provides encryption for open networks without passwords
- Uses Diffie-Hellman key exchange
- Protects against passive eavesdropping
- No authentication required

OWE Transition Mode Vulnerability:
- Networks that support both OWE and Open modes
- Clients can be forced to connect in unencrypted Open mode
- Allows downgrade attacks from encrypted to unencrypted

References:
- RFC 8110: Opportunistic Wireless Encryption
- Wi-Fi Alliance Enhanced Open specification
"""

from typing import Dict, List, Optional, Tuple
from ..util.color import Color


class OWEDetector:
    """
    Detects OWE networks and identifies transition mode vulnerabilities.

    OWE Transition Mode:
    - Network advertises both OWE and Open SSIDs
    - Vulnerable to downgrade attacks
    - Clients may connect without encryption
    """

    # OWE AKM suite identifier (00-0F-AC:18)
    OWE_AKM = 18

    @staticmethod
    def detect_owe_capability(target) -> Optional[Dict]:
        """
        Detect if a target supports OWE.

        Args:
            target: Target object with network information

        Returns:
            Dictionary with OWE information or None if not OWE:
            {
                'owe_enabled': bool,
                'transition_mode': bool,
                'open_ssid': str or None,
                'owe_ssid': str or None,
                'transition_bssid': str or None,
                'vulnerability': str or None
            }
        """
        owe_info = {
            'owe_enabled': False,
            'transition_mode': False,
            'open_ssid': None,
            'owe_ssid': None,
            'transition_bssid': None,
            'vulnerability': None
        }

        # Check if target has OWE authentication
        if not hasattr(target, 'authentication'):
            return None

        auth = target.authentication if target.authentication else ''

        # Check for OWE in authentication
        if 'OWE' in auth:
            owe_info['owe_enabled'] = True
            owe_info['owe_ssid'] = target.essid

            # Check for transition mode indicators
            # Transition mode networks often have similar SSIDs or paired BSSIDs
            if hasattr(target, 'owe_transition_mode') and target.owe_transition_mode:
                owe_info['transition_mode'] = True
                owe_info['vulnerability'] = 'OWE Transition Mode: Vulnerable to downgrade attacks'

                if hasattr(target, 'owe_transition_bssid'):
                    owe_info['transition_bssid'] = target.owe_transition_bssid

                if hasattr(target, 'owe_open_ssid'):
                    owe_info['open_ssid'] = target.owe_open_ssid

        return owe_info if owe_info['owe_enabled'] else None

    @staticmethod
    def find_transition_pairs(targets: List) -> List[Tuple]:
        """
        Find OWE transition mode pairs (OWE + Open networks).

        Args:
            targets: List of Target objects

        Returns:
            List of tuples: (owe_target, open_target, confidence)
            confidence: 'high', 'medium', 'low'
        """
        transition_pairs = []
        owe_targets = []
        open_targets = []

        # Separate OWE and Open networks
        for target in targets:
            if hasattr(target, 'authentication'):
                auth = target.authentication if target.authentication else ''
                if 'OWE' in auth:
                    owe_targets.append(target)
                elif target.encryption == 'Open' or not target.encryption:
                    open_targets.append(target)

        # Find potential pairs
        for owe_target in owe_targets:
            for open_target in open_targets:
                confidence = OWEDetector._assess_transition_pair(owe_target, open_target)
                if confidence:
                    transition_pairs.append((owe_target, open_target, confidence))

        return transition_pairs

    @staticmethod
    def _assess_transition_pair(owe_target, open_target) -> Optional[str]:
        """
        Assess if two networks form an OWE transition pair.

        Returns:
            Confidence level: 'high', 'medium', 'low', or None
        """
        confidence_score = 0

        # Check SSID similarity
        owe_ssid = owe_target.essid.lower() if owe_target.essid else ''
        open_ssid = open_target.essid.lower() if open_target.essid else ''

        if not owe_ssid or not open_ssid:
            return None

        # Exact match (different encryption)
        if owe_ssid == open_ssid:
            confidence_score += 50

        # Similar SSIDs (common patterns)
        # e.g., "Network" and "Network-OWE"
        # e.g., "WiFi" and "WiFi_Enhanced"
        if owe_ssid in open_ssid or open_ssid in owe_ssid:
            confidence_score += 30

        # Check if SSIDs differ by common suffixes
        common_suffixes = ['-owe', '_owe', '-enhanced', '_enhanced', '-secure', '_secure']
        for suffix in common_suffixes:
            if owe_ssid.replace(suffix, '') == open_ssid or open_ssid.replace(suffix, '') == owe_ssid:
                confidence_score += 40

        # Check BSSID similarity (same vendor, nearby channels)
        if hasattr(owe_target, 'bssid') and hasattr(open_target, 'bssid'):
            owe_bssid = owe_target.bssid.upper()
            open_bssid = open_target.bssid.upper()

            # Same OUI (first 3 octets) - same manufacturer
            if owe_bssid[:8] == open_bssid[:8]:
                confidence_score += 20

            # Very similar BSSID (differ by 1-2 in last octet)
            if owe_bssid[:15] == open_bssid[:15]:
                confidence_score += 30

        # Check channel proximity
        if hasattr(owe_target, 'channel') and hasattr(open_target, 'channel'):
            if owe_target.channel == open_target.channel:
                confidence_score += 10
            elif abs(owe_target.channel - open_target.channel) <= 2:
                confidence_score += 5

        # Determine confidence level
        if confidence_score >= 70:
            return 'high'
        elif confidence_score >= 40:
            return 'medium'
        elif confidence_score >= 20:
            return 'low'
        else:
            return None

    @staticmethod
    def print_owe_info(target, owe_info: Dict, verbose: bool = False):
        """
        Print OWE network information.

        Args:
            target: Target object
            owe_info: OWE information dictionary
            verbose: Show detailed information
        """
        if not owe_info or not owe_info['owe_enabled']:
            return

        Color.pl('\n{+} {C}OWE Network Detected:{W}')
        Color.pl('    {W}SSID: {G}%s{W}' % target.essid)
        Color.pl('    {W}BSSID: {C}%s{W}' % target.bssid)
        Color.pl('    {W}Encryption: {G}OWE (Enhanced Open){W}')

        if owe_info['transition_mode']:
            Color.pl('\n{!} {O}OWE Transition Mode Detected{W}')
            Color.pl('    {R}Vulnerability:{W} Network supports both OWE and Open modes')
            Color.pl('    {R}Risk:{W} Clients can be forced to connect without encryption')

            if owe_info['open_ssid']:
                Color.pl('    {W}Open SSID: {O}%s{W}' % owe_info['open_ssid'])

            if owe_info['transition_bssid']:
                Color.pl('    {W}Open BSSID: {O}%s{W}' % owe_info['transition_bssid'])

            Color.pl('\n{+} {C}Recommendation:{W}')
            Color.pl('    {G}•{W} Disable Open mode and use OWE-only')
            Color.pl('    {G}•{W} Configure clients to prefer OWE over Open')
            Color.pl('    {G}•{W} Monitor for rogue Open APs with same SSID')
        else:
            Color.pl('    {G}Status:{W} OWE-only mode (secure)')

        if verbose:
            Color.pl('\n{+} {C}OWE Information:{W}')
            Color.pl('    {W}Protocol:{W} RFC 8110 - Opportunistic Wireless Encryption')
            Color.pl('    {W}Key Exchange:{W} Diffie-Hellman')
            Color.pl('    {W}Authentication:{W} None (open access)')
            Color.pl('    {W}Encryption:{W} Automatic per-session keys')

    @staticmethod
    def print_transition_pairs(pairs: List[Tuple], verbose: bool = False):
        """
        Print detected OWE transition mode pairs.

        Args:
            pairs: List of (owe_target, open_target, confidence) tuples
            verbose: Show detailed information
        """
        if not pairs:
            Color.pl('\n{+} {G}No OWE transition mode vulnerabilities detected{W}')
            return

        Color.pl('\n{!} {O}OWE Transition Mode Vulnerabilities Detected{W}')
        Color.pl('{+} Found {R}%d{W} vulnerable network pair(s):\n' % len(pairs))

        for i, (owe_target, open_target, confidence) in enumerate(pairs, 1):
            confidence_color = '{R}' if confidence == 'high' else '{O}' if confidence == 'medium' else '{Y}'

            Color.pl('{+} {O}Pair #%d{W} (Confidence: %s%s{W}):' % (i, confidence_color, confidence.upper()))
            Color.pl('    {G}OWE Network:{W}')
            Color.pl('      SSID: {C}%s{W}' % owe_target.essid)
            Color.pl('      BSSID: {C}%s{W}' % owe_target.bssid)
            if hasattr(owe_target, 'channel'):
                Color.pl('      Channel: {C}%d{W}' % owe_target.channel)

            Color.pl('    {R}Open Network:{W}')
            Color.pl('      SSID: {O}%s{W}' % open_target.essid)
            Color.pl('      BSSID: {O}%s{W}' % open_target.bssid)
            if hasattr(open_target, 'channel'):
                Color.pl('      Channel: {O}%d{W}' % open_target.channel)

            Color.pl('    {R}Vulnerability:{W} Clients can be downgraded to unencrypted Open mode')
            Color.pl('')

        Color.pl('{+} {C}Recommendations:{W}')
        Color.pl('    {G}•{W} Disable Open mode SSIDs on OWE-capable networks')
        Color.pl('    {G}•{W} Use OWE-only mode for maximum security')
        Color.pl('    {G}•{W} Configure clients to reject Open connections')
        Color.pl('    {G}•{W} Monitor for rogue Open APs mimicking OWE networks')

    @staticmethod
    def scan_owe_vulnerabilities(targets: List) -> Dict:
        """
        Scan targets for OWE vulnerabilities.

        Args:
            targets: List of Target objects

        Returns:
            Dictionary with scan results:
            {
                'owe_networks': List[Target],
                'transition_pairs': List[Tuple],
                'vulnerable_count': int
            }
        """
        results = {
            'owe_networks': [],
            'transition_pairs': [],
            'vulnerable_count': 0
        }

        # Find OWE networks
        for target in targets:
            owe_info = OWEDetector.detect_owe_capability(target)
            if owe_info and owe_info['owe_enabled']:
                results['owe_networks'].append(target)
                if owe_info['transition_mode']:
                    results['vulnerable_count'] += 1

        # Find transition mode pairs
        results['transition_pairs'] = OWEDetector.find_transition_pairs(targets)
        results['vulnerable_count'] += len(results['transition_pairs'])

        return results

    @staticmethod
    def print_scan_summary(results: Dict):
        """Print OWE vulnerability scan summary."""
        Color.pl('\n{+} {C}OWE Vulnerability Scan Summary{W}')
        Color.pl('{+} OWE networks found: {G}%d{W}' % len(results['owe_networks']))
        Color.pl('{+} Transition mode pairs: {R}%d{W}' % len(results['transition_pairs']))
        Color.pl('{+} Total vulnerabilities: {R}%d{W}' % results['vulnerable_count'])

        if results['vulnerable_count'] > 0:
            Color.pl('\n{!} {O}OWE transition mode allows downgrade attacks{W}')
            Color.pl('{!} {O}Clients can be forced to connect without encryption{W}')
        else:
            Color.pl('\n{+} {G}No OWE transition mode vulnerabilities detected{W}')


if __name__ == '__main__':
    # Test the OWE detector
    print("OWE Detector - Test Mode")
    print("=" * 50)

    # Mock target class for testing
    class MockTarget:
        def __init__(self, essid, bssid, encryption, authentication, channel):
            self.essid = essid
            self.bssid = bssid
            self.encryption = encryption
            self.authentication = authentication
            self.channel = channel

    # Test case 1: OWE-only network (secure)
    owe_only = MockTarget("SecureWiFi", "AA:BB:CC:DD:EE:FF", "OWE", "OWE", 6)
    owe_info = OWEDetector.detect_owe_capability(owe_only)
    if owe_info:
        OWEDetector.print_owe_info(owe_only, owe_info, verbose=True)

    # Test case 2: Transition mode pair
    owe_net = MockTarget("CoffeeShop-OWE", "AA:BB:CC:DD:EE:01", "OWE", "OWE", 6)
    open_net = MockTarget("CoffeeShop", "AA:BB:CC:DD:EE:02", "Open", "", 6)

    pairs = OWEDetector.find_transition_pairs([owe_net, open_net])
    OWEDetector.print_transition_pairs(pairs, verbose=True)
