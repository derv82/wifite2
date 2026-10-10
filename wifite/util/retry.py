#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Retry logic with exponential backoff for network operations.

Provides robust retry mechanisms for operations that may fail
due to transient network conditions or hardware issues.
"""

import time
import secrets
_sysrng = secrets.SystemRandom()
from functools import wraps
from typing import Callable, Optional, Tuple, Type


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, message: str, last_exception: Optional[Exception] = None,
                 attempts: int = 0):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


def exponential_backoff(attempt: int,
                        base_delay: float = 1.0,
                        max_delay: float = 60.0,
                        jitter: bool = True) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** attempt), max_delay)

    if jitter:
        # Add up to 25% jitter
        delay *= (0.75 + _sysrng.random() * 0.5)

    return delay


def linear_backoff(attempt: int,
                   base_delay: float = 1.0,
                   increment: float = 1.0,
                   max_delay: float = 30.0) -> float:
    """
    Calculate linear backoff delay.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        increment: Delay increment per attempt
        max_delay: Maximum delay cap

    Returns:
        Delay in seconds
    """
    return min(base_delay + (attempt * increment), max_delay)


def constant_delay(attempt: int, delay: float = 2.0) -> float:
    """
    Return constant delay (no backoff).

    Args:
        attempt: Current attempt number (ignored)
        delay: Constant delay in seconds

    Returns:
        Delay in seconds
    """
    return delay


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(self,
                 max_attempts: int = 3,
                 backoff_func: Callable[[int], float] = None,
                 retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
                 on_retry: Optional[Callable[[int, Exception], None]] = None,
                 on_failure: Optional[Callable[[int, Exception], None]] = None):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of attempts
            backoff_func: Function to calculate delay (default: exponential)
            retry_exceptions: Exception types to retry on
            on_retry: Callback when retrying (attempt, exception)
            on_failure: Callback when all attempts fail
        """
        self.max_attempts = max_attempts
        self.backoff_func = backoff_func or exponential_backoff
        self.retry_exceptions = retry_exceptions
        self.on_retry = on_retry
        self.on_failure = on_failure


def retry_with_backoff(config: Optional[RetryConfig] = None,
                       max_attempts: int = 3,
                       backoff_func: Callable[[int], float] = None,
                       retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    Decorator to retry a function with backoff on failure.

    Can be used with or without a RetryConfig object.

    Examples:
        @retry_with_backoff(max_attempts=5)
        def my_function():
            ...

        config = RetryConfig(max_attempts=3, on_retry=log_retry)
        @retry_with_backoff(config=config)
        def another_function():
            ...
    """
    if config is None:
        config = RetryConfig(
            max_attempts=max_attempts,
            backoff_func=backoff_func or exponential_backoff,
            retry_exceptions=retry_exceptions
        )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retry_exceptions as e:
                    last_exception = e

                    # Check if this was the last attempt
                    if attempt >= config.max_attempts - 1:
                        if config.on_failure:
                            config.on_failure(attempt + 1, e)
                        raise RetryExhausted(
                            f"All {config.max_attempts} attempts failed for {func.__name__}",
                            last_exception=e,
                            attempts=attempt + 1
                        ) from e

                    # Calculate delay and wait
                    delay = config.backoff_func(attempt)

                    if config.on_retry:
                        config.on_retry(attempt + 1, e)

                    time.sleep(delay)

            # Should never reach here, but just in case
            raise RetryExhausted(
                f"Unexpected retry exhaustion for {func.__name__}",
                last_exception=last_exception,
                attempts=config.max_attempts
            )

        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry logic with backoff.

    Useful for retrying blocks of code rather than functions.

    Example:
        with RetryContext(max_attempts=3) as retry:
            for attempt in retry:
                try:
                    do_something()
                    break  # Success, exit retry loop
                except SomeException as e:
                    retry.record_failure(e)
    """

    def __init__(self,
                 max_attempts: int = 3,
                 backoff_func: Callable[[int], float] = None,
                 on_retry: Optional[Callable[[int, Exception], None]] = None):
        self.max_attempts = max_attempts
        self.backoff_func = backoff_func or exponential_backoff
        self.on_retry = on_retry

        self.attempt = 0
        self.last_exception: Optional[Exception] = None
        self.succeeded = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't suppress exceptions
        return False

    def __iter__(self):
        return self

    def __next__(self):
        if self.succeeded:
            raise StopIteration

        if self.attempt >= self.max_attempts:
            raise RetryExhausted(
                f"All {self.max_attempts} attempts failed",
                last_exception=self.last_exception,
                attempts=self.attempt
            )

        # If not the first attempt, wait before retrying
        if self.attempt > 0 and self.last_exception:
            delay = self.backoff_func(self.attempt - 1)
            if self.on_retry:
                self.on_retry(self.attempt, self.last_exception)
            time.sleep(delay)

        current_attempt = self.attempt
        self.attempt += 1
        return current_attempt

    def record_failure(self, exception: Exception) -> None:
        """Record a failure for the current attempt."""
        self.last_exception = exception

    def mark_success(self) -> None:
        """Mark the operation as successful."""
        self.succeeded = True


# Common retry configurations for wifite operations
INTERFACE_RETRY = RetryConfig(
    max_attempts=3,
    backoff_func=lambda a: linear_backoff(a, base_delay=0.5, increment=0.5),
    retry_exceptions=(OSError, IOError)
)

PROCESS_RETRY = RetryConfig(
    max_attempts=5,
    backoff_func=lambda a: exponential_backoff(a, base_delay=0.5, max_delay=10),
    retry_exceptions=(OSError, IOError, TimeoutError)
)

CAPTURE_RETRY = RetryConfig(
    max_attempts=3,
    backoff_func=lambda a: constant_delay(a, delay=2.0),
    retry_exceptions=(Exception,)
)


def retry_interface_operation(func: Callable) -> Callable:
    """Decorator for interface operations with appropriate retry config."""
    return retry_with_backoff(config=INTERFACE_RETRY)(func)


def retry_process_operation(func: Callable) -> Callable:
    """Decorator for process operations with appropriate retry config."""
    return retry_with_backoff(config=PROCESS_RETRY)(func)


def retry_capture_operation(func: Callable) -> Callable:
    """Decorator for capture operations with appropriate retry config."""
    return retry_with_backoff(config=CAPTURE_RETRY)(func)
