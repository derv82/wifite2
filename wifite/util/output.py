#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Output abstraction layer for wifite2
Manages switching between TUI and classic text output modes
"""

import sys
import os


class OutputManager:
    """
    Manages output mode selection and provides unified interface
    for both TUI and classic text output
    """
    
    _instance = None
    _mode = None
    _controller = None
    
    @classmethod
    def initialize(cls, mode='auto'):
        """
        Initialize output mode based on configuration
        
        Args:
            mode: 'auto', 'tui', or 'classic'
                - auto: Detect terminal capabilities and choose best mode
                - tui: Force TUI mode (will fail if not supported)
                - classic: Force classic text mode
        
        Returns:
            True if TUI mode is active, False if classic mode
        """
        try:
            if mode == 'auto':
                if cls._check_terminal_support():
                    try:
                        # Try to initialize TUI mode
                        cls._mode = 'tui'
                        # Test that we can create a controller
                        controller = cls.get_controller()
                        if controller is None:
                            raise RuntimeError("Failed to create TUI controller")
                        return True
                    except Exception as e:
                        # TUI initialization failed, fall back to classic
                        from ..util.color import Color
                        Color.pl('{!} {O}TUI initialization failed: %s{W}' % str(e))
                        Color.pl('{!} {O}Falling back to classic mode{W}')
                        cls._mode = 'classic'
                        cls._controller = None
                        return False
                else:
                    cls._mode = 'classic'
                    return False
            elif mode == 'tui':
                if not cls._check_terminal_support():
                    from ..util.color import Color
                    Color.pl('{!} {R}TUI mode requested but terminal does not support it{W}')
                    raise RuntimeError('TUI mode not supported by terminal')
                cls._mode = 'tui'
                return True
            else:  # classic
                cls._mode = 'classic'
                return False
        except Exception as e:
            # Any unexpected error - fall back to classic mode
            cls._mode = 'classic'
            cls._controller = None
            if mode == 'tui':
                # Re-raise if TUI was explicitly requested
                raise
            return False
    
    @classmethod
    def _check_terminal_support(cls):
        """
        Check if terminal supports TUI features
        
        Returns:
            True if terminal supports TUI, False otherwise
        """
        try:
            # Check if we're in a terminal (not piped/redirected)
            if not sys.stdout.isatty():
                return False
            
            # Check if TERM is set (required for terminal features)
            if not os.environ.get('TERM'):
                return False
            
            # Check for dumb terminal
            if os.environ.get('TERM') == 'dumb':
                return False
            
            # Try to import and test rich
            try:
                from rich.console import Console
                console = Console()
                
                # Check minimum terminal size (80x24)
                if console.width < 80 or console.height < 24:
                    return False
                
                # Check if terminal is actually interactive
                if not console.is_terminal:
                    return False
                
                return True
            except ImportError:
                # Rich library not available
                return False
            except (OSError, ValueError):
                # Any other error with rich
                return False
        except (OSError, ValueError):
            # Catch-all for any unexpected errors
            return False
    
    @classmethod
    def get_mode(cls):
        """
        Get current output mode
        
        Returns:
            'tui' or 'classic'
        """
        if cls._mode is None:
            cls.initialize()
        return cls._mode
    
    @classmethod
    def is_tui_mode(cls):
        """
        Check if TUI mode is active
        
        Returns:
            True if TUI mode, False if classic mode
        """
        # If not initialized, default to classic mode (safe default)
        if cls._mode is None:
            cls._mode = 'classic'
            return False
        return cls._mode == 'tui'
    
    @classmethod
    def get_controller(cls):
        """
        Get the TUI controller instance (only in TUI mode)
        
        Returns:
            TUIController instance or None if in classic mode
        """
        if cls._mode == 'tui' and cls._controller is None:
            try:
                from ..ui.tui import TUIController
                cls._controller = TUIController()
            except Exception as e:
                # Failed to create controller - fall back to classic
                from ..util.color import Color
                Color.pl('{!} {O}Failed to create TUI controller: %s{W}' % str(e))
                Color.pl('{!} {O}Falling back to classic mode{W}')
                cls._mode = 'classic'
                cls._controller = None
        return cls._controller
    
    @classmethod
    def get_scanner_view(cls):
        """
        Get appropriate scanner view based on current mode
        
        Returns:
            ScannerView (TUI) or ClassicScannerOutput (classic)
        """
        if cls.is_tui_mode():
            from ..ui.scanner_view import ScannerView
            return ScannerView(cls.get_controller())
        else:
            from ..ui.classic import ClassicScannerOutput
            return ClassicScannerOutput()
    
    @classmethod
    def get_selector_view(cls, targets):
        """
        Get appropriate selector view based on current mode
        
        Args:
            targets: List of Target objects to select from
        
        Returns:
            SelectorView (TUI) or ClassicSelectorOutput (classic)
        """
        if cls.is_tui_mode():
            from ..ui.selector_view import SelectorView
            return SelectorView(cls.get_controller(), targets)
        else:
            from ..ui.classic import ClassicSelectorOutput
            return ClassicSelectorOutput(targets)
    
    @classmethod
    def get_attack_view(cls, target):
        """
        Get appropriate attack view based on current mode
        
        Args:
            target: Target object being attacked
        
        Returns:
            AttackView (TUI) or ClassicAttackOutput (classic)
        """
        if cls.is_tui_mode():
            from ..ui.attack_view import AttackView
            return AttackView(cls.get_controller(), target)
        else:
            from ..ui.classic import ClassicAttackOutput
            return ClassicAttackOutput(target)
    
    @classmethod
    def cleanup(cls):
        """
        Clean up output resources
        Should be called on exit
        """
        try:
            if cls._controller:
                cls._controller.stop()
                cls._controller = None
        except (OSError, ValueError):
            # Ignore errors during cleanup
            pass
        finally:
            cls._mode = None
            cls._controller = None


# Convenience function for checking terminal support
def check_terminal_support():
    """
    Check if terminal supports TUI features
    
    Returns:
        True if terminal supports TUI, False otherwise
    """
    return OutputManager._check_terminal_support()


# WPA3-specific logging helpers
def log_wpa3_detection(target, wpa3_info):
    """
    Log WPA3 detection results to appropriate output.
    
    Args:
        target: Target object
        wpa3_info: WPA3Info object with detection results
    """
    from ..util.color import Color
    from ..util.tui_logger import log_wpa3_detection as tui_log_wpa3_detection
    
    # Log to TUI logger if available
    if OutputManager.is_tui_mode():
        wpa3_dict = {
            'has_wpa3': wpa3_info.has_wpa3,
            'is_transition': wpa3_info.is_transition,
            'pmf_status': wpa3_info.pmf_status,
            'dragonblood_vulnerable': wpa3_info.dragonblood_vulnerable
        }
        tui_log_wpa3_detection(target.bssid, wpa3_dict)
    
    # Also log to classic output for debugging
    if wpa3_info.has_wpa3:
        mode = "Transition" if wpa3_info.is_transition else "WPA3-Only"
        Color.pl('{+} {C}WPA3 detected: {W}%s {C}Mode: {W}%s {C}PMF: {W}%s' % 
                 (target.bssid, mode, wpa3_info.pmf_status))


def log_wpa3_strategy(target, strategy, reason=None):
    """
    Log WPA3 attack strategy selection.
    
    Args:
        target: Target object
        strategy: Selected strategy name
        reason: Optional reason for selection
    """
    from ..util.color import Color
    from ..util.tui_logger import log_wpa3_strategy as tui_log_wpa3_strategy
    
    # Log to TUI logger if available
    if OutputManager.is_tui_mode():
        tui_log_wpa3_strategy(target.bssid, strategy, reason)
    
    # Log to classic output
    msg = '{+} {C}WPA3 Strategy: {W}%s' % strategy.replace('_', ' ').title()
    if reason:
        msg += ' {C}({W}%s{C})' % reason
    Color.pl(msg)


def log_wpa3_downgrade(target, success, details=None):
    """
    Log WPA3 downgrade attempt result.
    
    Args:
        target: Target object
        success: Whether downgrade was successful
        details: Optional additional details
    """
    from ..util.color import Color
    from ..util.tui_logger import log_wpa3_downgrade as tui_log_wpa3_downgrade
    
    # Log to TUI logger if available
    if OutputManager.is_tui_mode():
        tui_log_wpa3_downgrade(target.bssid, success, details)
    
    # Log to classic output
    if success:
        msg = '{+} {G}Downgrade successful!{W}'
    else:
        msg = '{!} {O}Downgrade failed{W}'
    
    if details:
        msg += ' {C}({W}%s{C})' % details
    
    Color.pl(msg)


def log_wpa3_sae_capture(target, frame_type, frame_count=None):
    """
    Log SAE frame capture event.
    
    Args:
        target: Target object
        frame_type: Type of SAE frame captured
        frame_count: Optional total frame count
    """
    from ..util.color import Color
    from ..util.tui_logger import log_wpa3_sae_capture as tui_log_wpa3_sae_capture
    
    # Log to TUI logger if available
    if OutputManager.is_tui_mode():
        tui_log_wpa3_sae_capture(target.bssid, frame_type, frame_count)
    
    # Log to classic output
    msg = '{+} {C}SAE %s frame captured' % frame_type.title()
    if frame_count is not None:
        msg += ' {C}(total: {W}%d{C})' % frame_count
    Color.pl(msg)
