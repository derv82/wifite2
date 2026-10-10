#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WPA3-SAE Attack Strategy Selection Module

This module provides functionality to select the optimal attack strategy
for WPA3-SAE networks based on target capabilities, including transition
mode detection, PMF status, and Dragonblood vulnerability indicators.
"""

from typing import Dict, Any, Optional
from wifite.util.wpa3 import WPA3Detector


class WPA3AttackStrategy:
    """
    Selects optimal attack strategy for WPA3-SAE networks.

    This class analyzes target capabilities and selects the most effective
    attack strategy based on:
    - Transition mode (WPA2/WPA3 support)
    - PMF (Protected Management Frames) status
    - Dragonblood vulnerability indicators
    - Attack success probability

    Strategy Priority:
    1. Downgrade (transition mode) - 80-90% success rate
    2. Dragonblood (vulnerable targets) - 40-50% success rate
    3. SAE Capture (standard) - 60-70% success rate
    4. Passive (PMF required) - 50-60% success rate
    """

    # Attack strategy constants
    DOWNGRADE = 'downgrade'
    DRAGONBLOOD = 'dragonblood'
    SAE_CAPTURE = 'sae_capture'
    PASSIVE = 'passive'

    # Strategy descriptions for user display
    STRATEGY_DESCRIPTIONS = {
        DOWNGRADE: 'Transition Mode Downgrade Attack',
        DRAGONBLOOD: 'Dragonblood Vulnerability Exploitation',
        SAE_CAPTURE: 'Standard SAE Handshake Capture',
        PASSIVE: 'Passive SAE Capture (PMF Protected)'
    }

    # Strategy explanations for user display
    STRATEGY_EXPLANATIONS = {
        DOWNGRADE: 'Network supports both WPA2 and WPA3. Forcing WPA2 connection for traditional handshake capture.',
        DRAGONBLOOD: 'Network appears vulnerable to Dragonblood attacks. Attempting timing-based exploitation.',
        SAE_CAPTURE: 'Capturing WPA3-SAE handshake for offline dictionary attack.',
        PASSIVE: 'PMF is required - deauth attacks disabled. Waiting for natural client reconnections.'
    }

    @staticmethod
    def select_strategy(target, wpa3_info: Dict[str, Any]) -> Optional[str]:
        """
        Select best attack strategy based on target capabilities.

        Analyzes the target's WPA3 capabilities and selects the most effective
        attack strategy. The selection follows a priority order based on
        expected success rates and attack feasibility.

        Priority Order:
        1. Downgrade attack (if transition mode)
        2. Dragonblood exploit (if vulnerable)
        3. SAE capture (if PMF allows deauth)
        4. Passive capture (if PMF required)

        Args:
            target: Target object containing network information
            wpa3_info: Dictionary containing WPA3 capability information
                      (from WPA3Detector.detect_wpa3_capability)

        Returns:
            Strategy constant (DOWNGRADE, DRAGONBLOOD, SAE_CAPTURE, or PASSIVE)
            or None if target doesn't support WPA3
        """
        # Check if target actually supports WPA3
        # WPA2-only targets should not use WPA3 attack strategies
        if not wpa3_info.get('has_wpa3', False):
            return None

        # Priority 1: Downgrade attack for transition mode networks
        # Highest success rate (80-90%)
        if WPA3AttackStrategy.can_use_downgrade(wpa3_info):
            return WPA3AttackStrategy.DOWNGRADE

        # Priority 2: Dragonblood exploitation for vulnerable targets
        # Moderate success rate (40-50%) but faster than brute force
        if WPA3AttackStrategy.should_use_dragonblood(wpa3_info):
            return WPA3AttackStrategy.DRAGONBLOOD

        # Priority 3: Standard SAE capture if deauth is possible
        # Good success rate (60-70%)
        if WPA3AttackStrategy.can_use_deauth(wpa3_info):
            return WPA3AttackStrategy.SAE_CAPTURE

        # Priority 4: Passive capture when PMF prevents deauth
        # Lower success rate (50-60%) but only option when PMF required
        return WPA3AttackStrategy.PASSIVE

    @staticmethod
    def can_use_downgrade(wpa3_info: Dict[str, Any]) -> bool:
        """
        Check if downgrade attack is possible.

        Downgrade attacks are only effective against transition mode networks
        that support both WPA2 and WPA3. These networks allow clients to
        connect using either protocol, making them vulnerable to forced
        downgrade to WPA2.

        Args:
            wpa3_info: Dictionary containing WPA3 capability information

        Returns:
            True if downgrade attack is possible, False otherwise
        """
        from wifite.config import Configuration
        # User overrides: --no-downgrade disables the downgrade path outright,
        # and --force-sae (attack SAE directly, skip WPA2) also implies no
        # downgrade since a downgrade fundamentally captures a WPA2 handshake.
        if getattr(Configuration, 'wpa3_no_downgrade', False) or \
                getattr(Configuration, 'wpa3_force_sae', False):
            return False

        # Downgrade requires transition mode (both WPA2 and WPA3 support)
        return wpa3_info.get('is_transition', False)

    @staticmethod
    def can_use_deauth(wpa3_info: Dict[str, Any]) -> bool:
        """
        Check if deauth attacks will work (PMF not required).

        Deauthentication attacks are blocked by PMF (Protected Management
        Frames) when it is required. This method checks if deauth attacks
        are feasible based on the PMF status.

        Args:
            wpa3_info: Dictionary containing WPA3 capability information

        Returns:
            True if deauth attacks are possible, False if PMF prevents them
        """
        pmf_status = wpa3_info.get('pmf_status', WPA3Detector.PMF_DISABLED)

        # Deauth works when PMF is disabled or optional
        # PMF required blocks deauth attacks
        return pmf_status != WPA3Detector.PMF_REQUIRED

    @staticmethod
    def should_use_dragonblood(wpa3_info: Dict[str, Any]) -> bool:
        """
        Check if Dragonblood exploitation should be attempted.

        Dragonblood attacks target known vulnerabilities in WPA3-SAE
        implementations (CVE-2019-13377 and related). These attacks are
        only effective against vulnerable configurations.

        Args:
            wpa3_info: Dictionary containing WPA3 capability information

        Returns:
            True if Dragonblood exploitation should be attempted
        """
        # Only attempt Dragonblood if vulnerability indicators are present
        return wpa3_info.get('dragonblood_vulnerable', False)

    @staticmethod
    def get_strategy_description(strategy: str) -> str:
        """
        Get human-readable description of attack strategy.

        Args:
            strategy: Strategy constant (DOWNGRADE, DRAGONBLOOD, etc.)

        Returns:
            Human-readable strategy description
        """
        return WPA3AttackStrategy.STRATEGY_DESCRIPTIONS.get(
            strategy,
            'Unknown Strategy'
        )

    @staticmethod
    def get_strategy_explanation(strategy: str) -> str:
        """
        Get detailed explanation of why strategy was chosen.

        Args:
            strategy: Strategy constant (DOWNGRADE, DRAGONBLOOD, etc.)

        Returns:
            Detailed explanation of strategy selection
        """
        return WPA3AttackStrategy.STRATEGY_EXPLANATIONS.get(
            strategy,
            'Strategy selected based on target capabilities.'
        )

    @staticmethod
    def get_attack_priority(wpa3_info: Dict[str, Any]) -> int:
        """
        Get attack priority score for target.

        Higher scores indicate more favorable attack conditions.
        This can be used to prioritize targets when attacking multiple
        networks.

        Priority Scoring:
        - Transition mode: 100 (highest priority)
        - Dragonblood vulnerable: 75
        - PMF optional/disabled: 50
        - PMF required: 25 (lowest priority)

        Args:
            wpa3_info: Dictionary containing WPA3 capability information

        Returns:
            Priority score (higher is better)
        """
        # Transition mode gets highest priority
        if wpa3_info.get('is_transition', False):
            return 100

        # Dragonblood vulnerable gets high priority
        if wpa3_info.get('dragonblood_vulnerable', False):
            return 75

        # PMF status affects priority
        pmf_status = wpa3_info.get('pmf_status', WPA3Detector.PMF_DISABLED)
        if pmf_status == WPA3Detector.PMF_REQUIRED:
            return 25  # Lowest priority - passive capture only
        else:
            return 50  # Medium priority - standard SAE capture

    @staticmethod
    def format_strategy_display(strategy: str, wpa3_info: Dict[str, Any]) -> str:
        """
        Format strategy information for display to user.

        Creates a formatted string showing the selected strategy and
        relevant target information.

        Args:
            strategy: Selected strategy constant
            wpa3_info: Dictionary containing WPA3 capability information

        Returns:
            Formatted string for display
        """
        lines = []

        # Strategy name
        description = WPA3AttackStrategy.get_strategy_description(strategy)
        lines.append(f"Attack Strategy: {description}")

        # Strategy explanation
        explanation = WPA3AttackStrategy.get_strategy_explanation(strategy)
        lines.append(f"Reason: {explanation}")

        # Target capabilities
        lines.append("\nTarget Capabilities:")
        lines.append(f"  WPA3: {'Yes' if wpa3_info.get('has_wpa3') else 'No'}")
        lines.append(f"  WPA2: {'Yes' if wpa3_info.get('has_wpa2') else 'No'}")
        lines.append(f"  Transition Mode: {'Yes' if wpa3_info.get('is_transition') else 'No'}")
        lines.append(f"  PMF Status: {wpa3_info.get('pmf_status', 'unknown')}")

        sae_groups = wpa3_info.get('sae_groups', [])
        if sae_groups:
            lines.append(f"  SAE Groups: {', '.join(map(str, sae_groups))}")

        if wpa3_info.get('dragonblood_vulnerable'):
            lines.append("  Dragonblood Vulnerable: Yes")

        return '\n'.join(lines)
