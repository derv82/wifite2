#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
from .dependency import Dependency
from ..util.process import Process


class Wlancap2wpasec(Dependency):
    """
    Wrapper for wlancap2wpasec tool from hcxtools suite.
    Uploads capture files to wpa-sec.stanev.org for online cracking.
    """
    dependency_required = False
    dependency_name = 'wlancap2wpasec'
    dependency_url = 'apt install hcxtools'

    @staticmethod
    def upload(capfile, api_key, url=None, timeout=None, email=None, remove_on_success=False):
        """
        Upload capture file to wpa-sec using wlancap2wpasec.
        
        Args:
            capfile (str): Path to capture file (.cap, .pcap, .pcapng, .gz)
            api_key (str): wpa-sec user API key
            url (str, optional): Custom wpa-sec URL (default: https://wpa-sec.stanev.org)
            timeout (int, optional): Connection timeout in seconds (default: 30)
            email (str, optional): Email address for notifications
            remove_on_success (bool): Remove file after successful upload (default: False)
            
        Returns:
            tuple: (success: bool, message: str)
            
        Example:
            >>> success, msg = Wlancap2wpasec.upload('handshake.cap', 'myapikey123')
            >>> if success:
            ...     print(f"Upload successful: {msg}")
        """
        # Check if tool exists
        if not Wlancap2wpasec.exists():
            return False, 'wlancap2wpasec tool not found - install hcxtools package'
        
        # Validate capture file exists
        if not os.path.exists(capfile):
            return False, f'Capture file not found: {capfile}'
        
        # Validate capture file is not empty
        try:
            file_size = os.path.getsize(capfile)
            if file_size == 0:
                return False, f'Capture file is empty: {capfile}'
        except OSError as e:
            return False, f'Cannot access capture file: {str(e)}'
        
        # Validate API key
        if not api_key or len(api_key) == 0:
            return False, 'API key is required'
        
        # Build command
        command = [
            'wlancap2wpasec',
            '-k', api_key
        ]
        
        # Add optional parameters
        if url:
            command.extend(['-u', url])
        
        if timeout:
            command.extend(['-t', str(timeout)])
        
        if email:
            command.extend(['-e', email])
        
        if remove_on_success:
            command.append('-R')
        
        # Add capture file as last argument
        command.append(capfile)
        
        try:
            # Execute wlancap2wpasec
            proc = Process(command, devnull=False)
            proc.wait()
            
            stdout = proc.stdout()
            stderr = proc.stderr()
            exit_code = proc.poll()
            
            # Parse output for success/failure
            if exit_code == 0:
                # Success - parse any useful information from output
                return True, 'Upload completed successfully'
            else:
                # Failure - extract error message
                error_msg = Wlancap2wpasec._parse_error_message(stdout, stderr, exit_code)
                return False, error_msg
        
        except OSError as e:
            # File system or process execution error
            if 'No such file or directory' in str(e):
                return False, 'wlancap2wpasec tool not found - install hcxtools package'
            return False, f'Failed to execute wlancap2wpasec: {str(e)}'
        
        except KeyboardInterrupt:
            # User interrupted
            return False, 'Upload interrupted by user'
        
        except Exception as e:
            # Unexpected error
            return False, f'Upload failed: {str(e)}'
    
    @staticmethod
    def _parse_error_message(stdout, stderr, exit_code):
        """
        Parse error message from wlancap2wpasec output.
        
        Args:
            stdout (str): Standard output from tool
            stderr (str): Standard error from tool
            exit_code (int): Process exit code
            
        Returns:
            str: Human-readable error message
        """
        # Combine stdout and stderr for error parsing
        output = (stdout + '\n' + stderr).lower()
        
        # Check for specific error patterns (most specific first)
        
        # Network errors
        if 'connection refused' in output:
            return 'Connection refused - server may be down or URL is incorrect'
        
        if 'connection timed out' in output or 'timed out' in output:
            return 'Connection timed out - check network or increase timeout'
        
        if 'connection reset' in output or 'connection closed' in output:
            return 'Connection reset by server - try again later'
        
        if 'no route to host' in output:
            return 'No route to host - check network connectivity'
        
        if 'network unreachable' in output or 'network is unreachable' in output:
            return 'Network unreachable - check internet connection'
        
        # DNS errors
        if 'could not resolve' in output or 'name resolution failed' in output:
            return 'DNS resolution failed - check network and DNS settings'
        
        if 'temporary failure in name resolution' in output:
            return 'DNS temporary failure - check DNS configuration'
        
        if 'unknown host' in output or 'host not found' in output:
            return 'Unknown host - check URL configuration'
        
        # Authentication errors
        if 'unauthorized' in output or '401' in output:
            return 'Authentication failed - invalid API key'
        
        if 'forbidden' in output or '403' in output:
            return 'Access forbidden - check API key permissions'
        
        if 'invalid key' in output or 'bad key' in output:
            return 'Invalid API key format'
        
        # File errors
        if 'no such file' in output or 'file not found' in output:
            return 'Capture file not found'
        
        if 'permission denied' in output:
            return 'Permission denied - check file permissions'
        
        if 'invalid file' in output or 'bad file' in output:
            return 'Invalid capture file format'
        
        if 'empty file' in output or 'file is empty' in output:
            return 'Capture file is empty'
        
        if 'no handshake' in output or 'no pmkid' in output:
            return 'No valid handshake or PMKID found in capture file'
        
        # HTTP errors
        if '404' in output:
            return 'Server endpoint not found (404) - check URL'
        
        if '500' in output or 'internal server error' in output:
            return 'Server internal error (500) - try again later'
        
        if '502' in output or 'bad gateway' in output:
            return 'Bad gateway (502) - server may be down'
        
        if '503' in output or 'service unavailable' in output:
            return 'Service unavailable (503) - server overloaded'
        
        # Rate limiting
        if 'rate limit' in output or 'too many requests' in output or '429' in output:
            return 'Rate limit exceeded - wait before retrying'
        
        # SSL/TLS errors
        if 'ssl' in output or 'tls' in output or 'certificate' in output:
            return 'SSL/TLS error - check server certificate or use http://'
        
        # Generic patterns
        if 'connection' in output:
            return 'Network connection error'
        
        if 'timeout' in output:
            return 'Operation timed out'
        
        if 'dns' in output or 'resolve' in output:
            return 'DNS resolution error'
        
        if 'auth' in output or 'key' in output:
            return 'Authentication error'
        
        if 'invalid' in output or 'format' in output:
            return 'Invalid file format'
        
        if 'server' in output or 'host' in output:
            return 'Server error'
        
        # Try to extract meaningful error from stderr
        if stderr and len(stderr.strip()) > 0:
            # Return first non-empty line of stderr
            for line in stderr.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Limit length to avoid overly verbose errors
                    if len(line) > 100:
                        line = line[:97] + '...'
                    return f'Upload failed: {line}'
        
        # Try to extract meaningful error from stdout
        if stdout and len(stdout.strip()) > 0:
            for line in stdout.strip().split('\n'):
                line = line.strip()
                if line and ('error' in line.lower() or 'fail' in line.lower()):
                    if len(line) > 100:
                        line = line[:97] + '...'
                    return line
        
        # Generic error with exit code
        return f'Upload failed with exit code {exit_code}'
    
    @staticmethod
    def check_version():
        """
        Check wlancap2wpasec version.
        
        Returns:
            str: Version string if available, None otherwise
            
        Example:
            >>> version = Wlancap2wpasec.check_version()
            >>> print(f"wlancap2wpasec version: {version}")
        """
        if not Wlancap2wpasec.exists():
            return None
        
        try:
            # Try to get version using -v flag
            command = ['wlancap2wpasec', '-v']
            proc = Process(command, devnull=False)
            proc.wait()
            
            output = proc.stdout() + proc.stderr()
            
            # Parse version from output
            # Expected format: "wlancap2wpasec X.Y.Z"
            version_match = re.search(r'wlancap2wpasec\s+(\d+\.\d+\.\d+[^\s]*)', output, re.IGNORECASE)
            if version_match:
                return version_match.group(1)
            
            # Try alternative format
            version_match = re.search(r'version\s+(\d+\.\d+\.\d+[^\s]*)', output, re.IGNORECASE)
            if version_match:
                return version_match.group(1)
            
            # If no version found but tool exists, return unknown
            return 'unknown'
            
        except (OSError, RuntimeError):
            return None


if __name__ == '__main__':
    # Test tool existence
    if Wlancap2wpasec.exists():
        print('wlancap2wpasec found')
        version = Wlancap2wpasec.check_version()
        print(f'Version: {version}')
    else:
        print('wlancap2wpasec not found')
        print(f'Install from: {Wlancap2wpasec.dependency_url}')
