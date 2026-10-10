#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Centralized logging utility for wifite2.
Provides consistent logging across all modules with proper exception handling.
"""

import os
import sys
import traceback
from datetime import datetime
from typing import Optional


class Logger:
    """
    Centralized logger for wifite2.
    
    Provides different log levels and handles both console and file output.
    """
    
    # Log levels
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    
    _instance = None
    _log_file = None
    _log_level = INFO
    _verbose = 0
    _enabled = True
    
    def __init__(self):
        """Initialize logger (singleton pattern)."""
        if Logger._instance is not None:
            raise RuntimeError("Logger is a singleton. Use Logger.get_instance()")
        Logger._instance = self
    
    @classmethod
    def get_instance(cls):
        """Get or create logger instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def initialize(cls, log_file: Optional[str] = None, verbose: int = 0, enabled: bool = True):
        """
        Initialize the logger with configuration.
        
        Args:
            log_file: Path to log file (None = no file logging)
            verbose: Verbosity level (0-3)
            enabled: Whether logging is enabled
        """
        cls._log_file = log_file
        cls._verbose = verbose
        cls._enabled = enabled
        
        # Set log level based on verbosity
        if verbose >= 3:
            cls._log_level = cls.DEBUG
        elif verbose >= 2:
            cls._log_level = cls.INFO
        elif verbose >= 1:
            cls._log_level = cls.WARNING
        else:
            cls._log_level = cls.ERROR
        
        # Create log file if specified
        if log_file:
            try:
                log_dir = os.path.dirname(log_file)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, mode=0o700)
                
                # Write header — open with explicit 0o600 so the log file
                # is owner-readable only, regardless of the process umask.
                fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                with os.fdopen(fd, 'a') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Wifite2 Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{'='*80}\n")
            except (OSError, IOError) as e:
                print(f"Warning: Could not create log file {log_file}: {e}", file=sys.stderr)
                cls._log_file = None
    
    @classmethod
    def _should_log(cls, level: int) -> bool:
        """Check if message should be logged based on level."""
        return cls._enabled and level >= cls._log_level
    
    @classmethod
    def _sanitize_message(cls, message: str) -> str:
        """
        Best-effort sanitization to avoid logging sensitive data in clear text.

        Currently masks:
          - Known wpa-sec API key from Configuration.wpasec_api_key
          - Command-line API key arguments like "-k <value>" and "--key <value>"
          - MAC addresses in standard hex notation (aa:bb:cc:dd:ee:ff)
          - WPA/WEP keys from aircrack "KEY FOUND! [ <key> ]" output
          - Live passphrase progress "Current passphrase: <value>"
          - Hashcat cracked output "hash*bssid*station*essid:<password>"
          - Generic PSK/passphrase/password keyword-value pairs
        """
        try:
            # Import lazily to avoid circular imports during module initialization
            from ..config import Configuration  # type: ignore
        except (ImportError, AttributeError):
            Configuration = None  # type: ignore

        sanitized = message

        # Mask configured wpa-sec API key if present in message
        try:
            if Configuration is not None and getattr(Configuration, "wpasec_api_key", None):
                api_key = Configuration.wpasec_api_key
                if isinstance(api_key, str) and api_key:
                    masked_key = api_key[:4] + "*" * (len(api_key) - 4) if len(api_key) > 4 else "****"
                    sanitized = sanitized.replace(api_key, masked_key)
        except (AttributeError, TypeError):
            # Never let sanitization break logging
            pass

        import re

        # Mask common CLI key patterns: "-k <value>" and "--key <value>"
        try:
            def _mask_cli_key(match):
                flag = match.group(1)
                return f"{flag} ****"

            sanitized = re.sub(r"(-k)\s+\S+", _mask_cli_key, sanitized)
            sanitized = re.sub(r"(--key)\s+\S+", _mask_cli_key, sanitized)
        except (re.error, AttributeError):
            pass

        # Mask MAC addresses: aa:bb:cc:dd:ee:ff -> aa:bb:cc:**:**:**
        try:
            def _mask_mac(match):
                full = match.group(0)
                parts = full.split(":")
                if len(parts) == 6:
                    return ":".join(parts[:3] + ["**", "**", "**"])
                return full

            sanitized = re.sub(r"\b([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", _mask_mac, sanitized)
        except (re.error, AttributeError):
            pass

        # Mask aircrack "KEY FOUND! [ <key> ]" output
        try:
            sanitized = re.sub(r"(KEY FOUND!\s*\[)\s*\S.*?\s*(\])", r"\1 **** \2", sanitized)
        except (re.error, AttributeError):
            pass

        # Mask aircrack live progress "Current passphrase: <value>"
        try:
            sanitized = re.sub(
                r"(Current\s+passphrase\s*:)\s*\S.*",
                r"\1 ****",
                sanitized,
                flags=re.IGNORECASE,
            )
        except (re.error, AttributeError):
            pass

        # Mask hashcat cracked output: trailing :<password> after PMKID/hash lines
        # Format: hash*bssid*station*essid:password  or  hash:password
        try:
            sanitized = re.sub(
                r"([0-9a-fA-F\*]{20,}:[^:\n]{0,64}):[^\n]+$",
                r"\1:****",
                sanitized,
                flags=re.MULTILINE,
            )
        except (re.error, AttributeError):
            pass

        # Mask generic keyword-value pairs: password/passphrase/psk followed by
        # a delimiter (=, :, space) and a value
        try:
            sanitized = re.sub(
                r"(?i)(password|passphrase|psk|wpa_psk|wpa_passphrase)\s*[=:]\s*\S+",
                r"\1=****",
                sanitized,
            )
        except (re.error, AttributeError):
            pass

        return sanitized

    @classmethod
    def _format_message(cls, level: str, module: str, message: str) -> str:
        """Format log message with timestamp and level."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        safe_message = cls._sanitize_message(message)
        return f"[{timestamp}] [{level:8s}] [{module:20s}] {safe_message}"
    
    @classmethod
    def _write_to_file(cls, formatted_message: str):
        """Write message to log file."""
        if not cls._log_file:
            return
        
        try:
            with open(cls._log_file, 'a') as f:
                f.write(formatted_message + '\n')
        except (OSError, IOError) as e:
            # Can't log to file, print to stderr as fallback
            print(f"Log file write error: {e}", file=sys.stderr)
    
    @classmethod
    def debug(cls, module: str, message: str):
        """Log debug message."""
        if not cls._should_log(cls.DEBUG):
            return
        
        formatted = cls._format_message('DEBUG', module, message)
        cls._write_to_file(formatted)
        
        if cls._verbose >= 3:
            print(formatted, file=sys.stderr)
    
    @classmethod
    def info(cls, module: str, message: str):
        """Log info message."""
        if not cls._should_log(cls.INFO):
            return
        
        formatted = cls._format_message('INFO', module, message)
        cls._write_to_file(formatted)
        
        if cls._verbose >= 2:
            print(formatted, file=sys.stderr)
    
    @classmethod
    def warning(cls, module: str, message: str):
        """Log warning message."""
        if not cls._should_log(cls.WARNING):
            return
        
        formatted = cls._format_message('WARNING', module, message)
        cls._write_to_file(formatted)
        
        if cls._verbose >= 1:
            print(formatted, file=sys.stderr)
    
    @classmethod
    def error(cls, module: str, message: str, exc: Optional[Exception] = None):
        """
        Log error message with optional exception.
        
        Args:
            module: Module name
            message: Error message
            exc: Optional exception object
        """
        if not cls._should_log(cls.ERROR):
            return
        
        formatted = cls._format_message('ERROR', module, message)
        cls._write_to_file(formatted)
        print(formatted, file=sys.stderr)
        
        # Log exception details if provided
        if exc:
            exc_details = f"Exception: {type(exc).__name__}: {str(exc)}"
            cls._write_to_file(f"  {exc_details}")
            
            if cls._verbose >= 2:
                print(f"  {exc_details}", file=sys.stderr)
            
            # Log full traceback to file
            if cls._log_file:
                try:
                    with open(cls._log_file, 'a') as f:
                        f.write("  Traceback:\n")
                        for line in traceback.format_tb(exc.__traceback__):
                            f.write(f"    {line}")
                except (OSError, IOError):
                    pass
    
    @classmethod
    def critical(cls, module: str, message: str, exc: Optional[Exception] = None):
        """
        Log critical error message.
        
        Args:
            module: Module name
            message: Critical error message
            exc: Optional exception object
        """
        formatted = cls._format_message('CRITICAL', module, message)
        cls._write_to_file(formatted)
        print(formatted, file=sys.stderr)
        
        # Always log exception details for critical errors
        if exc:
            exc_details = f"Exception: {type(exc).__name__}: {str(exc)}"
            cls._write_to_file(f"  {exc_details}")
            print(f"  {exc_details}", file=sys.stderr)
            
            # Log full traceback
            if cls._log_file:
                try:
                    with open(cls._log_file, 'a') as f:
                        f.write("  Traceback:\n")
                        traceback.print_exc(file=f)
                except (OSError, IOError):
                    pass
            
            # Print traceback to stderr if verbose
            if cls._verbose >= 1:
                traceback.print_exc(file=sys.stderr)
    
    @classmethod
    def exception(cls, module: str, message: str):
        """
        Log exception with full traceback.
        Convenience method that captures current exception.
        
        Args:
            module: Module name
            message: Context message
        """
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_value:
            cls.error(module, message, exc_value)
        else:
            cls.error(module, message)


# Convenience functions for common use cases
def log_debug(module: str, message: str):
    """Log debug message."""
    Logger.debug(module, message)


def log_info(module: str, message: str):
    """Log info message."""
    Logger.info(module, message)


def log_warning(module: str, message: str):
    """Log warning message."""
    Logger.warning(module, message)


def log_error(module: str, message: str, exc: Optional[Exception] = None):
    """Log error message."""
    Logger.error(module, message, exc)


def log_critical(module: str, message: str, exc: Optional[Exception] = None):
    """Log critical error."""
    Logger.critical(module, message, exc)


def log_exception(module: str, message: str):
    """Log current exception."""
    Logger.exception(module, message)


def mask_sensitive(value: str) -> str:
    """Mask a sensitive value (e.g. password, key) for safe logging.

    Shows the first 2 characters followed by asterisks.  Values of
    2 characters or fewer are fully masked.

    Args:
        value: The sensitive string to mask.

    Returns:
        A masked version of *value* that is safe to include in logs.
    """
    if not value:
        return '****'
    if len(value) <= 2:
        return '*' * len(value)
    return value[:2] + '*' * (len(value) - 2)
