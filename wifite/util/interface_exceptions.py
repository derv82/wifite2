#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Custom exception classes for interface-related errors.

These exceptions provide specific error handling for dual interface
operations, making it easier to diagnose and recover from interface issues.
"""


class InterfaceError(Exception):
    """
    Base exception class for all interface-related errors.
    
    This is the parent class for all interface exceptions, allowing
    code to catch all interface errors with a single except clause.
    """
    
    def __init__(self, message: str, interface_name: str = None):
        """
        Initialize interface error.
        
        Args:
            message: Error message describing the issue
            interface_name: Name of the interface that caused the error (optional)
        """
        self.interface_name = interface_name
        
        if interface_name:
            full_message = f"Interface '{interface_name}': {message}"
        else:
            full_message = message
            
        super().__init__(full_message)


class InterfaceNotFoundError(InterfaceError):
    """
    Exception raised when a specified interface cannot be found.
    
    This error occurs when:
    - User specifies an interface that doesn't exist
    - An interface disappears during operation
    - No wireless interfaces are detected on the system
    """
    
    def __init__(self, interface_name: str = None, message: str = None):
        """
        Initialize interface not found error.
        
        Args:
            interface_name: Name of the interface that wasn't found
            message: Custom error message (optional)
        """
        if message is None:
            if interface_name:
                message = "Interface not found or not available"
            else:
                message = "No wireless interfaces found on system"
        
        super().__init__(message, interface_name)


class InterfaceCapabilityError(InterfaceError):
    """
    Exception raised when an interface lacks required capabilities.
    
    This error occurs when:
    - Interface doesn't support AP mode when required
    - Interface doesn't support monitor mode when required
    - Interface doesn't support packet injection when required
    - Interface has incompatible driver or chipset
    """
    
    def __init__(self, interface_name: str, capability: str, message: str = None):
        """
        Initialize interface capability error.
        
        Args:
            interface_name: Name of the interface with capability issue
            capability: Name of the missing capability (e.g., 'AP mode', 'monitor mode')
            message: Custom error message (optional)
        """
        self.capability = capability
        
        if message is None:
            message = f"Interface does not support {capability}"
        
        super().__init__(message, interface_name)


class InterfaceAssignmentError(InterfaceError):
    """
    Exception raised when interface assignment fails.
    
    This error occurs when:
    - Cannot find suitable interfaces for dual interface mode
    - Manual interface assignment is invalid
    - Interfaces have conflicting capabilities
    - Same interface assigned to multiple roles
    """
    
    def __init__(self, message: str, attack_type: str = None, 
                 primary_interface: str = None, secondary_interface: str = None):
        """
        Initialize interface assignment error.
        
        Args:
            message: Error message describing the assignment issue
            attack_type: Type of attack that failed assignment (optional)
            primary_interface: Primary interface name (optional)
            secondary_interface: Secondary interface name (optional)
        """
        self.attack_type = attack_type
        self.primary_interface = primary_interface
        self.secondary_interface = secondary_interface
        
        # Build detailed message
        details = []
        if attack_type:
            details.append(f"Attack: {attack_type}")
        if primary_interface:
            details.append(f"Primary: {primary_interface}")
        if secondary_interface:
            details.append(f"Secondary: {secondary_interface}")
        
        if details:
            full_message = f"{message} ({', '.join(details)})"
        else:
            full_message = message
        
        super().__init__(full_message, None)


class InterfaceConfigurationError(InterfaceError):
    """
    Exception raised when interface configuration fails.
    
    This error occurs when:
    - Cannot set interface to monitor mode
    - Cannot set interface to AP mode
    - Cannot set interface channel
    - Cannot bring interface up or down
    - Interface configuration command fails
    """
    
    def __init__(self, interface_name: str, operation: str, 
                 message: str = None, system_error: str = None):
        """
        Initialize interface configuration error.
        
        Args:
            interface_name: Name of the interface that failed configuration
            operation: Configuration operation that failed (e.g., 'set monitor mode')
            message: Custom error message (optional)
            system_error: System error message from command (optional)
        """
        self.operation = operation
        self.system_error = system_error
        
        if message is None:
            message = f"Failed to {operation}"
        
        if system_error:
            message = f"{message}: {system_error}"
        
        super().__init__(message, interface_name)


class InterfaceStateError(InterfaceError):
    """
    Exception raised when interface is in an unexpected state.
    
    This error occurs when:
    - Interface is already in use by another process
    - Interface is in wrong mode for operation
    - Interface state is inconsistent
    - Interface becomes unavailable during operation
    """
    
    def __init__(self, interface_name: str, expected_state: str, 
                 actual_state: str, message: str = None):
        """
        Initialize interface state error.
        
        Args:
            interface_name: Name of the interface with state issue
            expected_state: Expected interface state
            actual_state: Actual interface state
            message: Custom error message (optional)
        """
        self.expected_state = expected_state
        self.actual_state = actual_state
        
        if message is None:
            message = f"Interface in unexpected state (expected: {expected_state}, actual: {actual_state})"
        
        super().__init__(message, interface_name)


class InterfaceDriverError(InterfaceError):
    """
    Exception raised when interface driver has issues.
    
    This error occurs when:
    - Driver is known to be problematic
    - Driver doesn't support required features
    - Driver version is incompatible
    - Driver is not loaded
    """
    
    def __init__(self, interface_name: str, driver: str, 
                 message: str = None, suggestion: str = None):
        """
        Initialize interface driver error.
        
        Args:
            interface_name: Name of the interface with driver issue
            driver: Name of the problematic driver
            message: Custom error message (optional)
            suggestion: Suggestion for resolving the issue (optional)
        """
        self.driver = driver
        self.suggestion = suggestion
        
        if message is None:
            message = f"Driver '{driver}' has compatibility issues"
        
        if suggestion:
            message = f"{message}. Suggestion: {suggestion}"
        
        super().__init__(message, interface_name)
