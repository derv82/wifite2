#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Session management for wifite2.
Handles persistence and restoration of attack sessions for resume functionality.
"""

import os
import re
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime


_IFACE_RE = re.compile(r'^[a-zA-Z0-9_\-]{1,15}$')


def _is_valid_interface_name(name: str) -> bool:
    """Return True if *name* is a safe Linux interface name (SEC-010).

    Validates names parsed from iw/ip output before they are used in
    subprocess commands, preventing injection via crafted interface names.
    """
    return bool(name and _IFACE_RE.match(name))


@dataclass
class EvilTwinClientState:
    """Represents a client connection in an Evil Twin attack session."""
    
    mac_address: str
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    connect_time: float = 0.0
    disconnect_time: Optional[float] = None
    credential_submitted: bool = False
    credential_valid: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvilTwinClientState':
        """Create EvilTwinClientState from dictionary."""
        return cls(**data)


@dataclass
class EvilTwinCredentialAttempt:
    """Represents a credential submission attempt in an Evil Twin attack."""

    mac_address: str
    password: str
    success: bool
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvilTwinCredentialAttempt':
        """Create EvilTwinCredentialAttempt from dictionary."""
        return cls(**data)

    def clear_password(self):
        """Overwrite password in memory to prevent credential leakage."""
        if self.password:
            self.password = '\x00' * len(self.password)
            self.password = ''


@dataclass
class EvilTwinAttackState:
    """Represents the complete state of an Evil Twin attack for session persistence."""
    
    # Attack configuration
    interface_ap: Optional[str] = None
    interface_deauth: Optional[str] = None
    portal_template: str = 'generic'
    deauth_interval: int = 5
    
    # Attack progress
    attack_phase: str = "initializing"  # initializing, running, validating, completed, failed
    start_time: Optional[float] = None
    setup_time: Optional[float] = None
    
    # Client tracking
    clients: List[EvilTwinClientState] = field(default_factory=list)
    
    # Credential attempts
    credential_attempts: List[EvilTwinCredentialAttempt] = field(default_factory=list)
    
    # Statistics
    total_clients_connected: int = 0
    total_credential_attempts: int = 0
    successful_validations: int = 0
    
    # Result (if successful)
    captured_password: Optional[str] = None
    validation_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'interface_ap': self.interface_ap,
            'interface_deauth': self.interface_deauth,
            'portal_template': self.portal_template,
            'deauth_interval': self.deauth_interval,
            'attack_phase': self.attack_phase,
            'start_time': self.start_time,
            'setup_time': self.setup_time,
            'clients': [c.to_dict() for c in self.clients],
            'credential_attempts': [a.to_dict() for a in self.credential_attempts],
            'total_clients_connected': self.total_clients_connected,
            'total_credential_attempts': self.total_credential_attempts,
            'successful_validations': self.successful_validations,
            'captured_password': self.captured_password,
            'validation_time': self.validation_time
        }
    
    def clear_credentials(self):
        """Overwrite all credential data in memory to prevent leakage."""
        if self.captured_password:
            self.captured_password = '\x00' * len(self.captured_password)
            self.captured_password = None
        for attempt in self.credential_attempts:
            attempt.clear_password()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvilTwinAttackState':
        """Create EvilTwinAttackState from dictionary."""
        clients = [EvilTwinClientState.from_dict(c) for c in data.get('clients', [])]
        attempts = [EvilTwinCredentialAttempt.from_dict(a) for a in data.get('credential_attempts', [])]

        return cls(
            interface_ap=data.get('interface_ap'),
            interface_deauth=data.get('interface_deauth'),
            portal_template=data.get('portal_template', 'generic'),
            deauth_interval=data.get('deauth_interval', 5),
            attack_phase=data.get('attack_phase', 'initializing'),
            start_time=data.get('start_time'),
            setup_time=data.get('setup_time'),
            clients=clients,
            credential_attempts=attempts,
            total_clients_connected=data.get('total_clients_connected', 0),
            total_credential_attempts=data.get('total_credential_attempts', 0),
            successful_validations=data.get('successful_validations', 0),
            captured_password=data.get('captured_password'),
            validation_time=data.get('validation_time', 0.0)
        )


@dataclass
class TargetState:
    """Represents the state of a single target in a session."""
    
    bssid: str
    essid: Optional[str]
    channel: int
    encryption: str
    power: int
    wps: bool
    status: str = "pending"  # pending, in_progress, completed, failed
    attempts: int = 0
    last_attempt: Optional[float] = None
    
    # Evil Twin specific fields
    evil_twin_state: Optional[Dict[str, Any]] = None  # Evil Twin attack state
    
    @classmethod
    def from_target(cls, target) -> 'TargetState':
        """
        Create TargetState from a Target object.
        
        Args:
            target: Target object from scanner
            
        Returns:
            TargetState instance
        """
        return cls(
            bssid=target.bssid,
            essid=target.essid if hasattr(target, 'essid') else None,
            channel=int(target.channel) if target.channel else -1,
            encryption=target.encryption if hasattr(target, 'encryption') else 'Unknown',
            power=int(target.power) if hasattr(target, 'power') else 0,
            wps=bool(target.wps) if hasattr(target, 'wps') else False,
            evil_twin_state=None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TargetState':
        """Create TargetState from dictionary."""
        # Handle evil_twin_state deserialization
        evil_twin_data = data.get('evil_twin_state')
        if evil_twin_data:
            data['evil_twin_state'] = evil_twin_data  # Already a dict from JSON
        return cls(**data)


@dataclass
class SessionState:
    """Represents the complete state of an attack session."""
    
    session_id: str
    created_at: float
    updated_at: float
    config: Dict[str, Any]
    targets: List[TargetState] = field(default_factory=list)
    completed_targets: List[str] = field(default_factory=list)  # BSSIDs
    failed_targets: Dict[str, str] = field(default_factory=dict)  # BSSID -> reason
    current_target_index: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            'session_id': self.session_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'config': self.config,
            'targets': [t.to_dict() for t in self.targets],
            'completed_targets': self.completed_targets,
            'failed_targets': self.failed_targets,
            'current_target_index': self.current_target_index
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Deserialize from dictionary."""
        targets = [TargetState.from_dict(t) for t in data.get('targets', [])]
        return cls(
            session_id=data['session_id'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            config=data.get('config', {}),
            targets=targets,
            completed_targets=data.get('completed_targets', []),
            failed_targets=data.get('failed_targets', {}),
            current_target_index=data.get('current_target_index', 0)
        )
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get summary of session progress."""
        total = len(self.targets)
        completed = len(self.completed_targets)
        failed = len(self.failed_targets)
        remaining = total - completed - failed
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'remaining': remaining,
            'progress_percent': (completed / total * 100) if total > 0 else 0,
            'created_at': datetime.fromtimestamp(self.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.fromtimestamp(self.updated_at).strftime('%Y-%m-%d %H:%M:%S'),
            'age_hours': (time.time() - self.created_at) / 3600
        }


class SessionManager:
    """Manages session lifecycle, persistence, and restoration."""
    
    def __init__(self, session_dir: str = None):
        """
        Initialize session manager.
        
        Args:
            session_dir: Directory for session storage (default: ~/.wifite/sessions)
        """
        if session_dir is None:
            home = os.path.expanduser('~')
            session_dir = os.path.join(home, '.wifite', 'sessions')
        
        self.session_dir = session_dir
        self._ensure_session_dir()
    
    def _ensure_session_dir(self):
        """Create session directory if it doesn't exist with proper permissions."""
        if not os.path.exists(self.session_dir):
            os.makedirs(self.session_dir, mode=0o700)
        else:
            # Ensure proper permissions on existing directory
            os.chmod(self.session_dir, 0o700)
    
    def _get_session_path(self, session_id: str) -> str:
        """Get full path to session file, guarded against path traversal."""
        import re
        if not re.match(r'^[\w\-]+$', session_id):
            raise ValueError(f'Invalid session ID: {session_id!r}')
        path = os.path.join(self.session_dir, f'{session_id}.json')
        # Defense-in-depth: confirm resolved path stays inside the session directory
        real_dir = os.path.realpath(self.session_dir)
        real_path = os.path.realpath(path)
        if not real_path.startswith(real_dir + os.sep):
            raise ValueError(f'Session ID resolves outside session directory: {session_id!r}')
        return path
    
    def create_session(self, targets: List, config) -> SessionState:
        """
        Create a new session from targets and configuration.
        
        Args:
            targets: List of Target objects
            config: Configuration object or dictionary
            
        Returns:
            SessionState instance
        """
        timestamp = time.time()
        session_id = f"session_{datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')}"
        
        target_states = [TargetState.from_target(t) for t in targets]
        
        # Extract configuration as dictionary
        if isinstance(config, dict):
            config_dict = config
        else:
            # Extract relevant configuration from Configuration object
            config_dict = {
                'interface': getattr(config, 'interface', None),
                'wordlist': getattr(config, 'wordlist', None),
                'wpa_attack_timeout': getattr(config, 'wpa_attack_timeout', 500),
                'wps_pixie': getattr(config, 'wps_pixie', True),
                'wps_pin': getattr(config, 'wps_pin', True),
                'use_pmkid': not getattr(config, 'dont_use_pmkid', False),
                'infinite_mode': getattr(config, 'infinite_mode', False),
                'attack_max': getattr(config, 'attack_max', 0),
                'use_tui': getattr(config, 'use_tui', True),
                'wps_only': getattr(config, 'wps_only', False),
                'use_pmkid_only': getattr(config, 'use_pmkid_only', False),
                'verbose': getattr(config, 'verbose', 0),
                # Dual interface configuration
                'dual_interface_enabled': getattr(config, 'dual_interface_enabled', False),
                'interface_primary': getattr(config, 'interface_primary', None),
                'interface_secondary': getattr(config, 'interface_secondary', None),
                'auto_assign_interfaces': getattr(config, 'auto_assign_interfaces', True),
                'prefer_dual_interface': getattr(config, 'prefer_dual_interface', True)
            }
        
        session = SessionState(
            session_id=session_id,
            created_at=timestamp,
            updated_at=timestamp,
            config=config_dict,
            targets=target_states
        )
        
        return session
    
    def save_session(self, session: SessionState) -> None:
        """
        Persist session state to disk with atomic file operations.
        
        This method implements atomic session saving to prevent corruption:
        1. Creates unique temporary file with secure permissions (0600)
        2. Writes session data to temporary file
        3. Atomically renames temp file to final location
        4. Cleans up on error
        
        The atomic rename ensures that:
        - Multiple instances never corrupt each other's session files
        - Session files are never partially written
        - No race conditions occur during concurrent saves
        
        Args:
            session: SessionState to save
            
        Raises:
            IOError: If save operation fails (with detailed error message)
        """
        import tempfile
        from ..config import Configuration
        from ..util.color import Color
        
        session.updated_at = time.time()
        session_path = self._get_session_path(session.session_id)
        
        # Use secure temporary file with unique name to avoid race conditions
        # mkstemp creates file atomically with secure permissions (0600)
        temp_fd = None
        temp_path = None
        
        try:
            # Create secure temporary file in same directory as target
            # This ensures atomic rename works (same filesystem)
            # Prefix with session ID for uniqueness across multiple instances
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.tmp',
                prefix=f'.{session.session_id}_',
                dir=self.session_dir
            )
            
            # Write session data using file descriptor
            # fdopen takes ownership of the file descriptor
            with os.fdopen(temp_fd, 'w') as f:
                temp_fd = None  # Prevent double-close
                json.dump(session.to_dict(), f, indent=2)
            
            # Permissions already secure (0600 by default from mkstemp)
            # Atomic rename to final location (replaces existing file atomically)
            os.rename(temp_path, session_path)
            temp_path = None  # Successfully renamed, prevent cleanup
            
            # Log successful save in verbose mode
            if Configuration.verbose > 1:
                Color.pl('{+} {G}Session saved: %s{W}' % session.session_id)
            
        except Exception as e:
            # Clean up temp file on error
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except OSError:
                    pass
            
            if temp_path is not None and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            
            # Re-raise with detailed context
            raise IOError(f'Failed to save session {session.session_id}: {str(e)}') from e
    
    def load_session(self, session_id: str = None) -> SessionState:
        """
        Load session from disk with validation.
        
        Args:
            session_id: Session ID to load. If None, load latest session.
            
        Returns:
            SessionState instance
            
        Raises:
            FileNotFoundError: If no session file found
            ValueError: If session file is corrupted or invalid
            PermissionError: If session file has incorrect permissions
        """
        if session_id is None:
            # Load latest session
            sessions = self.list_sessions()
            if not sessions:
                raise FileNotFoundError("No session files found")
            session_id = sessions[0]['session_id']
        
        session_path = self._get_session_path(session_id)
        
        if not os.path.exists(session_path):
            raise FileNotFoundError(f"Session file not found: {session_id}")
        
        # Validate file permissions
        self._validate_file_permissions(session_path)
        
        try:
            with open(session_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted session file (invalid JSON): {e}")
        except (OSError, IOError) as e:
            raise ValueError(f"Cannot read session file: {e}")
        
        # Validate session data structure
        self._validate_session_data(data, session_id)
        
        try:
            return SessionState.from_dict(data)
        except (KeyError, TypeError, AttributeError) as e:
            raise ValueError(f"Corrupted session file (invalid structure): {e}")
    
    def _validate_file_permissions(self, session_path: str) -> None:
        """
        Validate that session file has secure permissions.
        
        Args:
            session_path: Path to session file
            
        Raises:
            PermissionError: If permissions are insecure
        """
        try:
            stat_info = os.stat(session_path)
            mode = stat_info.st_mode & 0o777
            
            # Check if file is readable by others (world-readable)
            if mode & 0o004:
                raise PermissionError(
                    f"Session file has insecure permissions ({oct(mode)}). "
                    "File should not be world-readable. "
                    f"Run: chmod 600 {session_path}"
                )
            
            # Check if file is readable by group
            if mode & 0o040:
                # Warning only, not critical
                import warnings
                warnings.warn(
                    f"Session file has group-readable permissions ({oct(mode)}). "
                    f"Consider running: chmod 600 {session_path}",
                    UserWarning
                )
        except OSError:
            # If we can't check permissions, continue anyway
            pass
    
    def _validate_session_data(self, data: Dict[str, Any], session_id: str) -> None:
        """
        Validate session data structure and content.
        
        Args:
            data: Session data dictionary
            session_id: Expected session ID
            
        Raises:
            ValueError: If data is invalid
        """
        # Check required fields
        required_fields = ['session_id', 'created_at', 'updated_at', 'config', 'targets']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate session ID matches
        if data['session_id'] != session_id:
            raise ValueError(
                f"Session ID mismatch: expected {session_id}, got {data['session_id']}"
            )
        
        # Validate timestamps
        if not isinstance(data['created_at'], (int, float)) or data['created_at'] <= 0:
            raise ValueError(f"Invalid created_at timestamp: {data['created_at']}")
        
        if not isinstance(data['updated_at'], (int, float)) or data['updated_at'] <= 0:
            raise ValueError(f"Invalid updated_at timestamp: {data['updated_at']}")
        
        # Validate config is a dictionary
        if not isinstance(data['config'], dict):
            raise ValueError(f"Invalid config type: expected dict, got {type(data['config'])}")
        
        # Validate targets is a list
        if not isinstance(data['targets'], list):
            raise ValueError(f"Invalid targets type: expected list, got {type(data['targets'])}")
        
        # Validate at least one target exists
        if len(data['targets']) == 0:
            raise ValueError("Session has no targets")
        
        # Validate each target has required fields
        for i, target in enumerate(data['targets']):
            if not isinstance(target, dict):
                raise ValueError(f"Target {i} is not a dictionary")
            
            required_target_fields = ['bssid', 'channel', 'encryption', 'power', 'wps', 'status']
            for field in required_target_fields:
                if field not in target:
                    raise ValueError(f"Target {i} missing required field: {field}")
            
            # Validate BSSID format (basic check)
            bssid = target['bssid']
            if not isinstance(bssid, str) or len(bssid) != 17:
                raise ValueError(f"Target {i} has invalid BSSID format: {bssid}")
            
            # Validate status is valid
            valid_statuses = ['pending', 'in_progress', 'completed', 'failed']
            if target['status'] not in valid_statuses:
                raise ValueError(f"Target {i} has invalid status: {target['status']}")
        
        # Validate completed_targets and failed_targets if present
        if 'completed_targets' in data:
            if not isinstance(data['completed_targets'], list):
                raise ValueError("completed_targets must be a list")
        
        if 'failed_targets' in data:
            if not isinstance(data['failed_targets'], dict):
                raise ValueError("failed_targets must be a dictionary")
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all available sessions with metadata.
        
        Returns:
            List of session metadata dictionaries, sorted by creation time (newest first)
        """
        sessions = []
        
        if not os.path.exists(self.session_dir):
            return sessions
        
        for filename in os.listdir(self.session_dir):
            if not filename.endswith('.json'):
                continue
            
            session_path = os.path.join(self.session_dir, filename)
            
            try:
                with open(session_path, 'r') as f:
                    data = json.load(f)
                
                session_state = SessionState.from_dict(data)
                summary = session_state.get_progress_summary()
                
                sessions.append({
                    'session_id': session_state.session_id,
                    'created_at': session_state.created_at,
                    'updated_at': session_state.updated_at,
                    'total_targets': summary['total'],
                    'completed': summary['completed'],
                    'failed': summary['failed'],
                    'remaining': summary['remaining'],
                    'progress_percent': summary['progress_percent'],
                    'age_hours': summary['age_hours']
                })
            except (json.JSONDecodeError, KeyError, TypeError):
                # Skip corrupted files
                continue
        
        # Sort by creation time, newest first
        sessions.sort(key=lambda x: x['created_at'], reverse=True)
        
        return sessions
    
    def delete_session(self, session_id: str) -> None:
        """
        Delete a specific session file.
        
        Args:
            session_id: Session ID to delete
        """
        session_path = self._get_session_path(session_id)
        if os.path.exists(session_path):
            os.remove(session_path)
    
    def cleanup_old_sessions(self, days: int = 7) -> int:
        """
        Remove sessions older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of sessions deleted
        """
        threshold = time.time() - (days * 24 * 3600)
        deleted = 0
        
        sessions = self.list_sessions()
        for session in sessions:
            if session['created_at'] < threshold:
                self.delete_session(session['session_id'])
                deleted += 1
        
        return deleted
    
    def mark_target_complete(self, session: SessionState, bssid: str, crack_result=None) -> None:
        """
        Mark a target as successfully completed.
        
        Args:
            session: SessionState to update
            bssid: BSSID of completed target
            crack_result: Optional CrackResult object (not stored in session)
        """
        if bssid not in session.completed_targets:
            session.completed_targets.append(bssid)
        
        # Update target status
        for target in session.targets:
            if target.bssid == bssid:
                target.status = 'completed'
                target.last_attempt = time.time()
                target.attempts += 1
                break
    
    def mark_target_failed(self, session: SessionState, bssid: str, reason: str) -> None:
        """
        Mark a target as failed.
        
        Args:
            session: SessionState to update
            bssid: BSSID of failed target
            reason: Failure reason
        """
        session.failed_targets[bssid] = reason
        
        # Update target status
        for target in session.targets:
            if target.bssid == bssid:
                target.status = 'failed'
                target.last_attempt = time.time()
                target.attempts += 1
                break
    
    def get_remaining_targets(
        self, session: SessionState, include_failed: bool = False
    ) -> List[TargetState]:
        """
        Get list of targets that still need to be attacked.
        
        Filters targets based on their status:
        - Excludes completed targets (successfully attacked)
        - Excludes failed targets by default (unless include_failed=True)
        - Includes pending targets (not yet attacked)
        - Includes in_progress targets (interrupted during attack)
        - Preserves original target order from session
        
        Args:
            session: SessionState to query
            include_failed: If True, include previously failed targets for retry
            
        Returns:
            List of TargetState objects for remaining targets, in original order
        """
        remaining = []
        
        for target in session.targets:
            # Skip completed targets (successfully attacked)
            if target.bssid in session.completed_targets:
                continue
            
            # Skip failed targets unless retry is enabled
            if target.bssid in session.failed_targets and not include_failed:
                continue
            
            # Include pending and in_progress targets
            remaining.append(target)
        
        return remaining
    
    def save_evil_twin_state(self, session: SessionState, bssid: str, evil_twin_state: EvilTwinAttackState) -> None:
        """
        Save Evil Twin attack state for a specific target.
        
        Args:
            session: SessionState to update
            bssid: BSSID of target being attacked
            evil_twin_state: EvilTwinAttackState to save
        """
        for target in session.targets:
            if target.bssid == bssid:
                target.evil_twin_state = evil_twin_state.to_dict()
                break
    
    def load_evil_twin_state(self, session: SessionState, bssid: str) -> Optional[EvilTwinAttackState]:
        """
        Load Evil Twin attack state for a specific target.
        
        Args:
            session: SessionState to query
            bssid: BSSID of target
            
        Returns:
            EvilTwinAttackState if found, None otherwise
        """
        for target in session.targets:
            if target.bssid == bssid and target.evil_twin_state:
                return EvilTwinAttackState.from_dict(target.evil_twin_state)
        return None
    
    def clear_evil_twin_state(self, session: SessionState, bssid: str) -> None:
        """
        Clear Evil Twin attack state for a specific target.
        
        Args:
            session: SessionState to update
            bssid: BSSID of target
        """
        for target in session.targets:
            if target.bssid == bssid:
                target.evil_twin_state = None
                break
    
    def handle_partial_evil_twin_completion(self, session: SessionState, bssid: str) -> Dict[str, Any]:
        """
        Handle partial completion of Evil Twin attack.
        
        This method analyzes the saved Evil Twin state to determine if the
        attack made any progress and what should be done on resume.
        
        Args:
            session: SessionState to analyze
            bssid: BSSID of target
            
        Returns:
            Dictionary with analysis results:
                - 'can_resume': bool - whether attack can be resumed
                - 'progress': str - description of progress made
                - 'clients_connected': int - number of clients that connected
                - 'credential_attempts': int - number of credential attempts
                - 'recommendation': str - recommended action
        """
        evil_twin_state = self.load_evil_twin_state(session, bssid)
        
        if not evil_twin_state:
            return {
                'can_resume': False,
                'progress': 'No saved state found',
                'clients_connected': 0,
                'credential_attempts': 0,
                'recommendation': 'Start new attack'
            }
        
        # Check if attack was successful
        if evil_twin_state.captured_password:
            return {
                'can_resume': False,
                'progress': 'Attack completed successfully',
                'clients_connected': evil_twin_state.total_clients_connected,
                'credential_attempts': evil_twin_state.total_credential_attempts,
                'recommendation': 'Attack already completed, password captured'
            }
        
        # Analyze progress
        clients = evil_twin_state.total_clients_connected
        attempts = evil_twin_state.total_credential_attempts
        
        if attempts > 0:
            progress = f'{clients} clients connected, {attempts} credential attempts made'
            recommendation = 'Resume attack - clients are attempting to connect'
        elif clients > 0:
            progress = f'{clients} clients connected, no credential attempts yet'
            recommendation = 'Resume attack - clients connected but no credentials submitted'
        else:
            progress = 'No clients connected yet'
            recommendation = 'Resume attack - waiting for clients to connect'
        
        # Check attack phase
        can_resume = evil_twin_state.attack_phase not in ['completed', 'failed']
        
        return {
            'can_resume': can_resume,
            'progress': progress,
            'clients_connected': clients,
            'credential_attempts': attempts,
            'recommendation': recommendation,
            'attack_phase': evil_twin_state.attack_phase
        }
    
    def restore_configuration(self, session: SessionState, config_obj) -> Dict[str, Any]:
        """
        Restore attack parameters from session to Configuration object.
        
        This method:
        1. Validates interface availability
        2. Restores attack parameters from session
        3. Detects and warns about conflicting command-line flags
        4. Returns a dictionary of warnings/changes for display
        
        Args:
            session: SessionState containing saved configuration
            config_obj: Configuration object to update
            
        Returns:
            Dictionary with keys:
                - 'warnings': List of warning messages
                - 'interface_changed': Boolean indicating if interface was changed
                - 'conflicts': List of conflicting flags that were overridden
        """
        
        warnings = []
        conflicts = []
        interface_changed = False
        
        saved_config = session.config
        
        # 1. Validate and restore interface
        saved_interface = saved_config.get('interface')
        current_interface = getattr(config_obj, 'interface', None)
        
        if saved_interface:
            # Validate the interface name from session data before use (SEC-010)
            if not _is_valid_interface_name(saved_interface):
                warnings.append(
                    f"Saved interface name '{saved_interface}' is invalid, ignoring"
                )
                saved_interface = None
            else:
                # Check if saved interface is available
                try:
                    from .process import Process
                    result = Process.run_simple(['iw', 'dev'])
                    available_interfaces = result.stdout

                    if saved_interface not in available_interfaces:
                        warnings.append(
                            f"Original interface '{saved_interface}' not found"
                        )

                        # If user specified a different interface via command line, use it
                        if current_interface and current_interface != saved_interface:
                            warnings.append(
                                f"Using command-line interface '{current_interface}' instead"
                            )
                            interface_changed = True
                        else:
                            # Prompt will happen in wifite.py, just note it here
                            warnings.append(
                                "Will use current monitor mode interface"
                            )
                            interface_changed = True
                    else:
                        # Interface is available, restore it
                        if current_interface and current_interface != saved_interface:
                            conflicts.append(
                                f"--interface: command-line value '{current_interface}' "
                                f"overridden by session value '{saved_interface}'"
                            )
                        config_obj.interface = saved_interface
                except (FileNotFoundError, OSError, Exception):
                    # Can't check interface availability, use current
                    warnings.append(
                        "Could not verify interface availability, using current interface"
                    )
                    interface_changed = True
        
        # 2. Restore attack parameters
        # Check for conflicts with command-line flags
        
        # Wordlist
        saved_wordlist = saved_config.get('wordlist')
        current_wordlist = getattr(config_obj, 'wordlist', None)
        if saved_wordlist:
            if current_wordlist and current_wordlist != saved_wordlist:
                conflicts.append(
                    "--wordlist: command-line value overridden by session value"
                )
            config_obj.wordlist = saved_wordlist
        
        # WPA attack timeout
        saved_timeout = saved_config.get('wpa_attack_timeout')
        if saved_timeout is not None:
            current_timeout = getattr(config_obj, 'wpa_attack_timeout', 500)
            if current_timeout != saved_timeout and current_timeout != 500:
                conflicts.append(
                    "--wpa-attack-timeout: command-line value overridden by session value"
                )
            config_obj.wpa_attack_timeout = saved_timeout
        
        # WPS Pixie
        saved_wps_pixie = saved_config.get('wps_pixie')
        if saved_wps_pixie is not None:
            config_obj.wps_pixie = saved_wps_pixie
        
        # WPS PIN
        saved_wps_pin = saved_config.get('wps_pin')
        if saved_wps_pin is not None:
            config_obj.wps_pin = saved_wps_pin
        
        # PMKID
        saved_use_pmkid = saved_config.get('use_pmkid')
        if saved_use_pmkid is not None:
            config_obj.dont_use_pmkid = not saved_use_pmkid
        
        # WPS only
        saved_wps_only = saved_config.get('wps_only')
        if saved_wps_only is not None:
            config_obj.wps_only = saved_wps_only
        
        # PMKID only
        saved_pmkid_only = saved_config.get('use_pmkid_only')
        if saved_pmkid_only is not None:
            config_obj.use_pmkid_only = saved_pmkid_only
        
        # Infinite mode
        saved_infinite = saved_config.get('infinite_mode')
        if saved_infinite is not None:
            config_obj.infinite_mode = saved_infinite
        
        # Attack max
        saved_attack_max = saved_config.get('attack_max')
        if saved_attack_max is not None:
            config_obj.attack_max = saved_attack_max
        
        # TUI mode
        saved_use_tui = saved_config.get('use_tui')
        if saved_use_tui is not None:
            current_use_tui = getattr(config_obj, 'use_tui', True)
            if current_use_tui != saved_use_tui:
                conflicts.append(
                    "UI mode: command-line value overridden by session value"
                )
            config_obj.use_tui = saved_use_tui
        
        # Verbose level
        saved_verbose = saved_config.get('verbose')
        if saved_verbose is not None:
            config_obj.verbose = saved_verbose
        
        # Dual interface configuration
        saved_dual_enabled = saved_config.get('dual_interface_enabled')
        if saved_dual_enabled is not None:
            current_dual_enabled = getattr(config_obj, 'dual_interface_enabled', False)
            if current_dual_enabled != saved_dual_enabled:
                conflicts.append(
                    "--dual-interface: command-line value overridden by session value"
                )
            config_obj.dual_interface_enabled = saved_dual_enabled
        
        # Primary interface
        saved_primary = saved_config.get('interface_primary')
        if saved_primary:
            if not _is_valid_interface_name(saved_primary):
                warnings.append(
                    f"Saved primary interface name '{saved_primary}' is invalid, will auto-assign"
                )
                config_obj.interface_primary = None
            else:
                # Check if saved primary interface is available
                try:
                    from .process import Process
                    result = Process.run_simple(['iw', 'dev'])
                    available_interfaces = result.stdout

                    if saved_primary not in available_interfaces:
                        warnings.append(
                            f"Saved primary interface '{saved_primary}' not found, will auto-assign"
                        )
                        config_obj.interface_primary = None
                    else:
                        current_primary = getattr(config_obj, 'interface_primary', None)
                        if current_primary and current_primary != saved_primary:
                            conflicts.append(
                                "--interface-primary: command-line value overridden by session value"
                            )
                        config_obj.interface_primary = saved_primary
                except (FileNotFoundError, OSError, Exception):
                    warnings.append(
                        "Could not verify primary interface availability, will auto-assign"
                    )
                    config_obj.interface_primary = None

        # Secondary interface
        saved_secondary = saved_config.get('interface_secondary')
        if saved_secondary:
            if not _is_valid_interface_name(saved_secondary):
                warnings.append(
                    f"Saved secondary interface name '{saved_secondary}' is invalid, will auto-assign"
                )
                config_obj.interface_secondary = None
            else:
                # Check if saved secondary interface is available
                try:
                    from .process import Process
                    result = Process.run_simple(['iw', 'dev'])
                    available_interfaces = result.stdout

                    if saved_secondary not in available_interfaces:
                        warnings.append(
                            f"Saved secondary interface '{saved_secondary}' not found, will auto-assign"
                        )
                        config_obj.interface_secondary = None
                    else:
                        current_secondary = getattr(config_obj, 'interface_secondary', None)
                        if current_secondary and current_secondary != saved_secondary:
                            conflicts.append(
                                "--interface-secondary: command-line value overridden by session value"
                            )
                        config_obj.interface_secondary = saved_secondary
                except (FileNotFoundError, OSError, Exception):
                    warnings.append(
                        "Could not verify secondary interface availability, will auto-assign"
                    )
                    config_obj.interface_secondary = None
        
        # Auto-assign interfaces
        saved_auto_assign = saved_config.get('auto_assign_interfaces')
        if saved_auto_assign is not None:
            config_obj.auto_assign_interfaces = saved_auto_assign
        
        # Prefer dual interface
        saved_prefer_dual = saved_config.get('prefer_dual_interface')
        if saved_prefer_dual is not None:
            config_obj.prefer_dual_interface = saved_prefer_dual
        
        return {
            'warnings': warnings,
            'interface_changed': interface_changed,
            'conflicts': conflicts
        }
