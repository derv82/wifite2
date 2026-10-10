#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interface assignment strategy for dual wireless device support.

Implements intelligent interface assignment logic for different attack types,
selecting the best interfaces based on capabilities and preferences.
"""

from typing import List, Optional, Tuple, Dict

from ..model.interface_info import InterfaceInfo, InterfaceAssignment
from ..util.logger import log_info, log_debug, log_warning, log_error


class InterfaceAssignmentStrategy:
    """
    Strategy for assigning interfaces to roles in multi-interface attacks.
    
    This class implements the logic for selecting and assigning wireless
    interfaces to specific roles based on their capabilities and the
    requirements of different attack types.
    """
    
    # Known good drivers for AP mode (in preference order)
    PREFERRED_AP_DRIVERS = [
        'ath9k', 'ath9k_htc', 'ath10k',
        'rt2800usb', 'rt2800pci',
        'rtl8812au', 'rtl8814au', 'rtl8821au'
    ]
    
    # Known good drivers for monitor/injection (in preference order)
    PREFERRED_MONITOR_DRIVERS = [
        'ath9k', 'ath9k_htc', 'ath10k',
        'rt2800usb', 'rt2800pci',
        'carl9170', 'rtl8812au', 'rtl8814au'
    ]
    
    # Problematic driver combinations (primary_driver, secondary_driver)
    PROBLEMATIC_COMBINATIONS = [
        # Add known problematic combinations here
        # Example: ('iwlwifi', 'brcmfmac')
    ]
    
    @staticmethod
    def assign_for_evil_twin(interfaces: List[InterfaceInfo]) -> Optional[InterfaceAssignment]:
        """
        Assign interfaces for Evil Twin attack.
        
        Evil Twin requires:
        - Primary: AP mode + injection support (for rogue AP)
        - Secondary: Monitor mode + injection support (for deauth)
        
        Error Handling:
        - Catches assignment errors
        - Attempts fallback to single interface
        - Displays clear error messages if assignment impossible
        - Provides suggestions for resolving issues
        
        Args:
            interfaces: List of available interfaces
            
        Returns:
            InterfaceAssignment or None if assignment not possible
        """
        from .interface_exceptions import InterfaceAssignmentError, InterfaceCapabilityError
        from ..util.color import Color
        
        # Task 11.2: Log assignment strategy being used
        log_info('InterfaceAssignment', '=' * 60)
        log_info('InterfaceAssignment', 'Starting interface assignment for Evil Twin attack')
        log_info('InterfaceAssignment', 'Strategy: Assign AP-capable interface as primary, monitor-capable as secondary')
        log_info('InterfaceAssignment', '=' * 60)
        
        try:
            if not interfaces:
                log_warning('InterfaceAssignment', 'No interfaces available for assignment')
                Color.pl('{!} {R}No wireless interfaces available for Evil Twin attack{W}')
                raise InterfaceAssignmentError(
                    'No interfaces available',
                    attack_type='evil_twin'
                )
            
            # Task 11.2: Log interfaces being considered
            log_info('InterfaceAssignment', f'Considering {len(interfaces)} available interface(s):')
            for iface in interfaces:
                log_info('InterfaceAssignment', f'  - {iface.name}: {iface.get_capability_summary()}')
            
            # Filter interfaces by capability
            ap_capable = [iface for iface in interfaces if iface.is_suitable_for_evil_twin_ap()]
            monitor_capable = [iface for iface in interfaces if iface.is_suitable_for_evil_twin_deauth()]
            
            log_info('InterfaceAssignment', 
                     f'Filtered results: {len(ap_capable)} AP-capable, {len(monitor_capable)} monitor-capable')
            
            if ap_capable:
                log_debug('InterfaceAssignment', f'AP-capable interfaces: {", ".join([i.name for i in ap_capable])}')
            if monitor_capable:
                log_debug('InterfaceAssignment', f'Monitor-capable interfaces: {", ".join([i.name for i in monitor_capable])}')
            
            # Check if we have at least one AP-capable interface
            if not ap_capable:
                log_warning('InterfaceAssignment', 'No AP-capable interfaces found for Evil Twin')
                Color.pl('{!} {R}No AP-capable interfaces found{W}')
                Color.pl('{!} {O}Evil Twin attack requires an interface that supports AP mode{W}')
                Color.pl('{!} {O}Suggestion: Use a wireless adapter with AP mode support (e.g., Atheros, Ralink){W}')
                raise InterfaceCapabilityError(
                    interface_name='any',
                    capability='AP mode',
                    message='No interfaces support AP mode for Evil Twin attack'
                )
        
            # Try dual interface assignment first
            if len(ap_capable) >= 1 and len(monitor_capable) >= 2:
                # Task 11.2: Log assignment decision and rationale
                log_info('InterfaceAssignment', 'Attempting dual interface assignment...')
                log_info('InterfaceAssignment', 
                        f'Rationale: {len(ap_capable)} AP-capable and {len(monitor_capable)} monitor-capable interfaces available')
                
                # We have enough interfaces for dual mode
                # Select best AP interface
                ap_interface = InterfaceAssignmentStrategy._select_best_ap_interface(ap_capable)
                
                # Select best monitor interface (different from AP interface)
                monitor_candidates = [iface for iface in monitor_capable 
                                     if iface.name != ap_interface.name]
                
                if monitor_candidates:
                    monitor_interface = InterfaceAssignmentStrategy._select_best_monitor_interface(
                        monitor_candidates
                    )
                    
                    # Validate the assignment
                    is_valid, error_msg = InterfaceAssignmentStrategy.validate_dual_interface_setup(
                        ap_interface, monitor_interface
                    )
                    
                    if is_valid:
                        assignment = InterfaceAssignment(
                            attack_type='evil_twin',
                            primary=ap_interface.name,
                            secondary=monitor_interface.name,
                            primary_role='Rogue AP',
                            secondary_role='Deauth'
                        )
                        
                        # Task 11.2: Log assignment decision
                        log_info('InterfaceAssignment', '-' * 60)
                        log_info('InterfaceAssignment', 'Assignment decision: DUAL INTERFACE MODE')
                        log_info('InterfaceAssignment', f'  Primary ({ap_interface.name}): Rogue AP')
                        log_info('InterfaceAssignment', f'  Secondary ({monitor_interface.name}): Deauthentication')
                        log_info('InterfaceAssignment', 'Rationale: Dual interface mode eliminates mode switching and improves performance')
                        log_info('InterfaceAssignment', '=' * 60)
                        return assignment
                    else:
                        log_warning('InterfaceAssignment', 
                                   f'Dual interface validation failed: {error_msg}')
                        Color.pl('{!} {O}Dual interface validation failed: {R}%s{W}' % error_msg)
                        Color.pl('{!} {O}Falling back to single interface mode{W}')
            
            # Task 11.2: Log fallback to single interface if applicable
            log_info('InterfaceAssignment', 'Falling back to single interface mode')
            log_info('InterfaceAssignment', 
                    'Rationale: Insufficient interfaces for dual mode (need 1 AP-capable + 1 additional monitor-capable)')
            
            # Select best AP-capable interface
            ap_interface = InterfaceAssignmentStrategy._select_best_ap_interface(ap_capable)
            
            assignment = InterfaceAssignment(
                attack_type='evil_twin',
                primary=ap_interface.name,
                secondary=None,
                primary_role='Rogue AP + Deauth (mode switching)',
                secondary_role=None
            )
            
            # Task 11.2: Log assignment decision
            log_info('InterfaceAssignment', '-' * 60)
            log_info('InterfaceAssignment', 'Assignment decision: SINGLE INTERFACE MODE')
            log_info('InterfaceAssignment', f'  Primary ({ap_interface.name}): Rogue AP + Deauth (mode switching)')
            log_info('InterfaceAssignment', 'Rationale: Only one suitable interface available, will use mode switching')
            log_info('InterfaceAssignment', '=' * 60)
            return assignment
            
        except (InterfaceAssignmentError, InterfaceCapabilityError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            log_error('InterfaceAssignment', f'Unexpected error during Evil Twin assignment: {e}', e)
            Color.pl('{!} {R}Unexpected error during interface assignment:{W} %s' % str(e))
            raise InterfaceAssignmentError(
                f'Assignment failed: {e}',
                attack_type='evil_twin'
            )

    @staticmethod
    def assign_for_wpa(interfaces: List[InterfaceInfo]) -> Optional[InterfaceAssignment]:
        """
        Assign interfaces for WPA handshake capture attack.
        
        WPA attack requires:
        - Primary: Monitor mode (for handshake capture)
        - Secondary: Monitor mode + injection (for deauth)
        
        Error Handling:
        - Catches assignment errors
        - Attempts fallback to single interface
        - Displays clear error messages if assignment impossible
        - Provides suggestions for resolving issues
        
        Args:
            interfaces: List of available interfaces
            
        Returns:
            InterfaceAssignment or None if assignment not possible
        """
        from .interface_exceptions import InterfaceAssignmentError, InterfaceCapabilityError
        from ..util.color import Color
        
        # Task 11.2: Log assignment strategy being used
        log_info('InterfaceAssignment', '=' * 60)
        log_info('InterfaceAssignment', 'Starting interface assignment for WPA attack')
        log_info('InterfaceAssignment', 'Strategy: Assign monitor-capable interface for capture, another for deauth')
        log_info('InterfaceAssignment', '=' * 60)
        
        try:
            if not interfaces:
                log_warning('InterfaceAssignment', 'No interfaces available for assignment')
                Color.pl('{!} {R}No wireless interfaces available for WPA attack{W}')
                raise InterfaceAssignmentError(
                    'No interfaces available',
                    attack_type='wpa'
                )
            
            # Task 11.2: Log interfaces being considered
            log_info('InterfaceAssignment', f'Considering {len(interfaces)} available interface(s):')
            for iface in interfaces:
                log_info('InterfaceAssignment', f'  - {iface.name}: {iface.get_capability_summary()}')
            
            # Filter interfaces by capability
            capture_capable = [iface for iface in interfaces if iface.is_suitable_for_wpa_capture()]
            deauth_capable = [iface for iface in interfaces if iface.is_suitable_for_wpa_deauth()]
            
            log_info('InterfaceAssignment', 
                     f'Filtered results: {len(capture_capable)} capture-capable, {len(deauth_capable)} deauth-capable')
            
            if capture_capable:
                log_debug('InterfaceAssignment', f'Capture-capable interfaces: {", ".join([i.name for i in capture_capable])}')
            if deauth_capable:
                log_debug('InterfaceAssignment', f'Deauth-capable interfaces: {", ".join([i.name for i in deauth_capable])}')
            
            # Check if we have at least one monitor-capable interface
            if not capture_capable:
                log_warning('InterfaceAssignment', 'No monitor-capable interfaces found for WPA')
                Color.pl('{!} {R}No monitor-capable interfaces found{W}')
                Color.pl('{!} {O}WPA attack requires an interface that supports monitor mode{W}')
                Color.pl('{!} {O}Suggestion: Most wireless adapters support monitor mode{W}')
                raise InterfaceCapabilityError(
                    interface_name='any',
                    capability='monitor mode',
                    message='No interfaces support monitor mode for WPA attack'
                )
        
            # Try dual interface assignment first
            if len(capture_capable) >= 1 and len(deauth_capable) >= 2:
                # Task 11.2: Log assignment decision and rationale
                log_info('InterfaceAssignment', 'Attempting dual interface assignment...')
                log_info('InterfaceAssignment', 
                        f'Rationale: {len(capture_capable)} capture-capable and {len(deauth_capable)} deauth-capable interfaces available')
                
                # We have enough interfaces for dual mode
                # Select best capture interface
                capture_interface = InterfaceAssignmentStrategy._select_best_monitor_interface(
                    capture_capable
                )
                
                # Select best deauth interface (different from capture interface)
                deauth_candidates = [iface for iface in deauth_capable 
                                    if iface.name != capture_interface.name]
                
                if deauth_candidates:
                    deauth_interface = InterfaceAssignmentStrategy._select_best_monitor_interface(
                        deauth_candidates
                    )
                    
                    # Validate the assignment
                    is_valid, error_msg = InterfaceAssignmentStrategy.validate_dual_interface_setup(
                        capture_interface, deauth_interface
                    )
                    
                    if is_valid:
                        assignment = InterfaceAssignment(
                            attack_type='wpa',
                            primary=capture_interface.name,
                            secondary=deauth_interface.name,
                            primary_role='Handshake Capture',
                            secondary_role='Deauth'
                        )
                        
                        # Task 11.2: Log assignment decision
                        log_info('InterfaceAssignment', '-' * 60)
                        log_info('InterfaceAssignment', 'Assignment decision: DUAL INTERFACE MODE')
                        log_info('InterfaceAssignment', f'  Primary ({capture_interface.name}): Handshake Capture')
                        log_info('InterfaceAssignment', f'  Secondary ({deauth_interface.name}): Deauthentication')
                        log_info('InterfaceAssignment', 'Rationale: Dual interface mode enables continuous capture during deauth')
                        log_info('InterfaceAssignment', '=' * 60)
                        return assignment
                    else:
                        log_warning('InterfaceAssignment', 
                                   f'Dual interface validation failed: {error_msg}')
                        Color.pl('{!} {O}Dual interface validation failed: {R}%s{W}' % error_msg)
                        Color.pl('{!} {O}Falling back to single interface mode{W}')
            
            # Task 11.2: Log fallback to single interface if applicable
            log_info('InterfaceAssignment', 'Falling back to single interface mode')
            log_info('InterfaceAssignment', 
                    'Rationale: Insufficient interfaces for dual mode (need 2 monitor-capable)')
            
            # Select best monitor-capable interface
            monitor_interface = InterfaceAssignmentStrategy._select_best_monitor_interface(
                capture_capable
            )
            
            assignment = InterfaceAssignment(
                attack_type='wpa',
                primary=monitor_interface.name,
                secondary=None,
                primary_role='Capture + Deauth',
                secondary_role=None
            )
            
            # Task 11.2: Log assignment decision
            log_info('InterfaceAssignment', '-' * 60)
            log_info('InterfaceAssignment', 'Assignment decision: SINGLE INTERFACE MODE')
            log_info('InterfaceAssignment', f'  Primary ({monitor_interface.name}): Capture + Deauth')
            log_info('InterfaceAssignment', 'Rationale: Only one suitable interface available')
            log_info('InterfaceAssignment', '=' * 60)
            return assignment
            
        except (InterfaceAssignmentError, InterfaceCapabilityError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            log_error('InterfaceAssignment', f'Unexpected error during WPA assignment: {e}', e)
            Color.pl('{!} {R}Unexpected error during interface assignment:{W} %s' % str(e))
            raise InterfaceAssignmentError(
                f'Assignment failed: {e}',
                attack_type='wpa'
            )
    
    @staticmethod
    def assign_for_wps(interfaces: List[InterfaceInfo]) -> Optional[InterfaceAssignment]:
        """
        Assign interfaces for WPS attack.
        
        WPS attack requires:
        - Primary: Monitor mode (for WPS attack)
        - Secondary: Monitor mode (for monitoring, optional)
        
        Args:
            interfaces: List of available interfaces
            
        Returns:
            InterfaceAssignment or None if assignment not possible
        """
        log_info('InterfaceAssignment', 'Assigning interfaces for WPS attack')
        
        if not interfaces:
            log_warning('InterfaceAssignment', 'No interfaces available for assignment')
            return None
        
        # Filter interfaces by capability (monitor mode support)
        monitor_capable = [iface for iface in interfaces if iface.supports_monitor_mode]
        
        log_debug('InterfaceAssignment', 
                 f'Found {len(monitor_capable)} monitor-capable interfaces')
        
        # Check if we have at least one monitor-capable interface
        if not monitor_capable:
            log_warning('InterfaceAssignment', 'No monitor-capable interfaces found for WPS')
            return None
        
        # Try dual interface assignment first
        if len(monitor_capable) >= 2:
            # We have enough interfaces for dual mode
            # Select best WPS interface
            wps_interface = InterfaceAssignmentStrategy._select_best_monitor_interface(
                monitor_capable
            )
            
            # Select best monitoring interface (different from WPS interface)
            monitor_candidates = [iface for iface in monitor_capable 
                                 if iface.name != wps_interface.name]
            
            if monitor_candidates:
                monitor_interface = InterfaceAssignmentStrategy._select_best_monitor_interface(
                    monitor_candidates
                )
                
                # Validate the assignment
                is_valid, error_msg = InterfaceAssignmentStrategy.validate_dual_interface_setup(
                    wps_interface, monitor_interface
                )
                
                if is_valid:
                    assignment = InterfaceAssignment(
                        attack_type='wps',
                        primary=wps_interface.name,
                        secondary=monitor_interface.name,
                        primary_role='WPS Attack',
                        secondary_role='Monitoring'
                    )
                    
                    log_info('InterfaceAssignment', 
                            f'Dual interface assignment: {assignment.get_assignment_summary()}')
                    return assignment
                else:
                    log_warning('InterfaceAssignment', 
                               f'Dual interface validation failed: {error_msg}')
        
        # Fallback to single interface mode
        log_info('InterfaceAssignment', 'Falling back to single interface mode')
        
        # Select best monitor-capable interface
        monitor_interface = InterfaceAssignmentStrategy._select_best_monitor_interface(
            monitor_capable
        )
        
        assignment = InterfaceAssignment(
            attack_type='wps',
            primary=monitor_interface.name,
            secondary=None,
            primary_role='WPS Attack',
            secondary_role=None
        )
        
        log_info('InterfaceAssignment', 
                f'Single interface assignment: {assignment.get_assignment_summary()}')
        return assignment

    @staticmethod
    def _select_best_ap_interface(candidates: List[InterfaceInfo]) -> InterfaceInfo:
        """
        Select the best interface for AP mode from candidates.
        
        Selection criteria (in priority order):
        1. Prefer interfaces that are down (easier to configure)
        2. Prefer interfaces with known good AP drivers
        3. Prefer interfaces with injection support
        4. First available interface
        
        Args:
            candidates: List of AP-capable interfaces
            
        Returns:
            Best InterfaceInfo for AP role
        """
        if not candidates:
            raise ValueError("No candidates provided for AP interface selection")
        
        log_debug('InterfaceAssignment', f'Selecting best AP interface from {len(candidates)} candidates')
        
        # Score each interface
        scored_interfaces = []
        
        for iface in candidates:
            score = 0
            reasons = []
            
            # Prefer interfaces that are down
            if not iface.is_up:
                score += 100
                reasons.append('down')
            
            # Prefer known good AP drivers
            if iface.driver in InterfaceAssignmentStrategy.PREFERRED_AP_DRIVERS:
                driver_index = InterfaceAssignmentStrategy.PREFERRED_AP_DRIVERS.index(iface.driver)
                score += (50 - driver_index)  # Higher score for earlier drivers in list
                reasons.append(f'preferred driver ({iface.driver})')
            
            # Prefer interfaces with injection support
            if iface.supports_injection:
                score += 25
                reasons.append('injection')
            
            # Prefer interfaces not connected
            if not iface.is_connected:
                score += 10
                reasons.append('not connected')
            
            scored_interfaces.append((score, iface, reasons))
            log_debug('InterfaceAssignment', 
                     f'  {iface.name}: score={score} ({", ".join(reasons) if reasons else "default"})')
        
        # Sort by score (descending)
        scored_interfaces.sort(key=lambda x: x[0], reverse=True)
        
        # Return best interface
        best_score, best_interface, best_reasons = scored_interfaces[0]
        log_info('InterfaceAssignment', 
                f'Selected {best_interface.name} for AP (score={best_score})')
        
        return best_interface
    
    @staticmethod
    def _select_best_monitor_interface(candidates: List[InterfaceInfo]) -> InterfaceInfo:
        """
        Select the best interface for monitor mode from candidates.
        
        Selection criteria (in priority order):
        1. Prefer interfaces that are down (easier to configure)
        2. Prefer interfaces with known good injection drivers
        3. Prefer interfaces with injection support
        4. First available interface
        
        Args:
            candidates: List of monitor-capable interfaces
            
        Returns:
            Best InterfaceInfo for monitor role
        """
        if not candidates:
            raise ValueError("No candidates provided for monitor interface selection")
        
        log_debug('InterfaceAssignment', f'Selecting best monitor interface from {len(candidates)} candidates')
        
        # Score each interface
        scored_interfaces = []
        
        for iface in candidates:
            score = 0
            reasons = []
            
            # Prefer interfaces that are down
            if not iface.is_up:
                score += 100
                reasons.append('down')
            
            # Prefer known good monitor/injection drivers
            if iface.driver in InterfaceAssignmentStrategy.PREFERRED_MONITOR_DRIVERS:
                driver_index = InterfaceAssignmentStrategy.PREFERRED_MONITOR_DRIVERS.index(iface.driver)
                score += (50 - driver_index)  # Higher score for earlier drivers in list
                reasons.append(f'preferred driver ({iface.driver})')
            
            # Prefer interfaces with injection support
            if iface.supports_injection:
                score += 25
                reasons.append('injection')
            
            # Prefer interfaces not connected
            if not iface.is_connected:
                score += 10
                reasons.append('not connected')
            
            scored_interfaces.append((score, iface, reasons))
            log_debug('InterfaceAssignment', 
                     f'  {iface.name}: score={score} ({", ".join(reasons) if reasons else "default"})')
        
        # Sort by score (descending)
        scored_interfaces.sort(key=lambda x: x[0], reverse=True)
        
        # Return best interface
        best_score, best_interface, best_reasons = scored_interfaces[0]
        log_info('InterfaceAssignment', 
                f'Selected {best_interface.name} for monitor (score={best_score})')
        
        return best_interface

    @staticmethod
    def validate_dual_interface_setup(primary: InterfaceInfo, 
                                      secondary: InterfaceInfo) -> Tuple[bool, str]:
        """
        Validate that two interfaces can work together in dual interface mode.
        
        Validation checks:
        1. Primary and secondary interfaces are different
        2. Both interfaces are on different physical devices (warn if same)
        3. Both interfaces have required capabilities
        4. No problematic driver combinations
        
        Args:
            primary: Primary interface
            secondary: Secondary interface
            
        Returns:
            Tuple of (is_valid, error_message)
            error_message is empty string if valid, otherwise contains reason
        """
        log_debug('InterfaceAssignment', 
                 f'Validating dual interface setup: {primary.name} + {secondary.name}')
        
        # Check 1: Interfaces must be different
        if primary.name == secondary.name:
            error_msg = f'Primary and secondary interfaces are the same ({primary.name})'
            log_warning('InterfaceAssignment', f'Validation failed: {error_msg}')
            return False, error_msg
        
        # Check 2: Warn if same physical device (but don't fail)
        if primary.phy == secondary.phy and primary.phy != 'unknown':
            warning_msg = (f'Both interfaces on same physical device ({primary.phy}). '
                          f'This may cause conflicts.')
            log_warning('InterfaceAssignment', warning_msg)
            # Don't fail, just warn - some devices support multiple virtual interfaces
        
        # Check 3: Verify primary has required capabilities
        # (This is context-dependent, but we assume caller filtered appropriately)
        # We'll do a basic sanity check
        if not (primary.supports_ap_mode or primary.supports_monitor_mode):
            error_msg = f'Primary interface {primary.name} lacks required capabilities'
            log_warning('InterfaceAssignment', f'Validation failed: {error_msg}')
            return False, error_msg
        
        # Check 4: Verify secondary has required capabilities
        if not secondary.supports_monitor_mode:
            error_msg = f'Secondary interface {secondary.name} lacks monitor mode support'
            log_warning('InterfaceAssignment', f'Validation failed: {error_msg}')
            return False, error_msg
        
        # Check 5: Check for problematic driver combinations
        driver_combo = (primary.driver, secondary.driver)
        if driver_combo in InterfaceAssignmentStrategy.PROBLEMATIC_COMBINATIONS:
            error_msg = (f'Problematic driver combination: {primary.driver} + {secondary.driver}. '
                        f'These drivers may not work well together.')
            log_warning('InterfaceAssignment', f'Validation failed: {error_msg}')
            return False, error_msg
        
        log_info('InterfaceAssignment', 
                f'Dual interface setup validated: {primary.name} + {secondary.name}')
        return True, ''
    
    @staticmethod
    def get_assignment_recommendations(interfaces: List[InterfaceInfo]) -> Dict[str, Optional[InterfaceAssignment]]:
        """
        Get recommended interface assignments for all attack types.
        
        This method generates recommendations for Evil Twin, WPA, and WPS
        attacks based on available interfaces.
        
        Args:
            interfaces: List of available interfaces
            
        Returns:
            Dictionary mapping attack types to InterfaceAssignment objects
            Keys: 'evil_twin', 'wpa', 'wps'
            Values: InterfaceAssignment or None if not possible
        """
        log_info('InterfaceAssignment', 
                f'Generating assignment recommendations for {len(interfaces)} interfaces')
        
        recommendations = {}
        
        # Get Evil Twin recommendation
        try:
            evil_twin_assignment = InterfaceAssignmentStrategy.assign_for_evil_twin(interfaces)
            recommendations['evil_twin'] = evil_twin_assignment
            
            if evil_twin_assignment:
                log_info('InterfaceAssignment', 
                        f'Evil Twin: {evil_twin_assignment.get_assignment_summary()}')
            else:
                log_info('InterfaceAssignment', 'Evil Twin: Not possible with available interfaces')
        except Exception as e:
            log_warning('InterfaceAssignment', f'Failed to generate Evil Twin recommendation: {e}')
            recommendations['evil_twin'] = None
        
        # Get WPA recommendation
        try:
            wpa_assignment = InterfaceAssignmentStrategy.assign_for_wpa(interfaces)
            recommendations['wpa'] = wpa_assignment
            
            if wpa_assignment:
                log_info('InterfaceAssignment', 
                        f'WPA: {wpa_assignment.get_assignment_summary()}')
            else:
                log_info('InterfaceAssignment', 'WPA: Not possible with available interfaces')
        except Exception as e:
            log_warning('InterfaceAssignment', f'Failed to generate WPA recommendation: {e}')
            recommendations['wpa'] = None
        
        # Get WPS recommendation
        try:
            wps_assignment = InterfaceAssignmentStrategy.assign_for_wps(interfaces)
            recommendations['wps'] = wps_assignment
            
            if wps_assignment:
                log_info('InterfaceAssignment', 
                        f'WPS: {wps_assignment.get_assignment_summary()}')
            else:
                log_info('InterfaceAssignment', 'WPS: Not possible with available interfaces')
        except Exception as e:
            log_warning('InterfaceAssignment', f'Failed to generate WPS recommendation: {e}')
            recommendations['wps'] = None
        
        log_info('InterfaceAssignment', 
                f'Generated {len([r for r in recommendations.values() if r])} valid recommendations')
        
        return recommendations
