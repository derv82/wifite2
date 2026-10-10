#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WPA3 Tool Detection and Version Checking

This module provides comprehensive tool detection and version checking
for WPA3-SAE attack capabilities.
"""

import re
from typing import Dict, Optional, Tuple, List

from ..util.color import Color
from ..util.process import Process


class WPA3ToolChecker:
    """
    Checks for WPA3-specific tools and their versions.

    Required tools:
    - hcxdumptool: For capturing SAE handshakes
    - hcxpcapngtool: For converting captures to hashcat format
    - hashcat: For cracking SAE handshakes

    Optional tools:
    - tshark: For advanced frame analysis
    """

    # Minimum required versions
    # hcxdumptool must be 7.x: the HcxDumpTool wrapper emits 7.x-only capture
    # syntax (-w output, --rds=1, channel band-suffixes like 1a/6a), so a 6.x
    # binary would pass an older gate and then fail at runtime.
    MIN_VERSIONS = {
        'hcxdumptool': (7, 0, 0),
        'hcxpcapngtool': (1, 0, 0),
        'hashcat': (6, 0, 0),
        'tshark': (3, 0, 0)
    }

    # Tool installation URLs
    INSTALL_URLS = {
        'hcxdumptool': 'apt install hcxdumptool or https://github.com/ZerBea/hcxdumptool',
        'hcxpcapngtool': 'apt install hcxtools or https://github.com/ZerBea/hcxtools',
        'hashcat': 'apt install hashcat or https://hashcat.net/hashcat/',
        'tshark': 'apt install tshark or https://www.wireshark.org/'
    }

    @staticmethod
    def check_all_tools() -> Dict[str, Dict[str, any]]:
        """
        Check all WPA3-related tools.

        Returns:
            Dictionary with tool status information:
            {
                'tool_name': {
                    'available': bool,
                    'version': tuple or None,
                    'version_str': str or None,
                    'meets_minimum': bool,
                    'required': bool
                }
            }
        """
        tools = {
            'hcxdumptool': {'required': True},
            'hcxpcapngtool': {'required': True},
            'hashcat': {'required': True},
            'tshark': {'required': False}
        }

        results = {}
        for tool_name, info in tools.items():
            results[tool_name] = WPA3ToolChecker.check_tool(
                tool_name,
                required=info['required']
            )

        return results

    @staticmethod
    def check_tool(tool_name: str, required: bool = True) -> Dict[str, any]:
        """
        Check if a specific tool is available and meets version requirements.

        Args:
            tool_name: Name of the tool to check
            required: Whether the tool is required for WPA3 attacks

        Returns:
            Dictionary with tool status:
            {
                'available': bool,
                'version': tuple or None,
                'version_str': str or None,
                'meets_minimum': bool,
                'required': bool
            }
        """
        available = Process.exists(tool_name)
        version = None
        version_str = None
        meets_minimum = False

        if available:
            version, version_str = WPA3ToolChecker.get_tool_version(tool_name)
            if version and tool_name in WPA3ToolChecker.MIN_VERSIONS:
                meets_minimum = version >= WPA3ToolChecker.MIN_VERSIONS[tool_name]
            else:
                # If we can't determine version, assume it's OK
                meets_minimum = True

        return {
            'available': available,
            'version': version,
            'version_str': version_str,
            'meets_minimum': meets_minimum,
            'required': required
        }

    @staticmethod
    def get_tool_version(tool_name: str) -> Tuple[Optional[Tuple[int, ...]], Optional[str]]:
        """
        Get version of a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tuple of (version_tuple, version_string)
            e.g., ((6, 2, 5), "6.2.5")
        """
        try:
            # Try different version flags
            for flag in ['--version', '-v', '-V', 'version']:
                command = [tool_name, flag]
                proc = Process(command, devnull=False)
                output = proc.stdout() + proc.stderr()

                if output:
                    version_tuple, version_str = WPA3ToolChecker._parse_version(output, tool_name)
                    if version_tuple:
                        return version_tuple, version_str

            return None, None

        except (OSError, ValueError):
            return None, None

    @staticmethod
    def _parse_version(output: str, tool_name: str) -> Tuple[Optional[Tuple[int, ...]], Optional[str]]:
        """
        Parse version string from tool output.

        Args:
            output: Tool output containing version
            tool_name: Name of the tool

        Returns:
            Tuple of (version_tuple, version_string)
        """
        # Common version patterns
        patterns = [
            r'(\d+)\.(\d+)\.(\d+)',  # x.y.z
            r'(\d+)\.(\d+)',          # x.y
            r'v(\d+)\.(\d+)\.(\d+)',  # vx.y.z
            r'version\s+(\d+)\.(\d+)\.(\d+)',  # version x.y.z
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                version_parts = tuple(int(g) for g in match.groups())
                version_str = '.'.join(str(v) for v in version_parts)
                return version_parts, version_str

        return None, None

    @staticmethod
    def can_attack_wpa3() -> bool:
        """
        Check if all required tools for WPA3 attacks are available.

        Returns:
            True if WPA3 attacks are possible, False otherwise
        """
        tools = WPA3ToolChecker.check_all_tools()

        # Check if all required tools are available and meet minimum versions
        for tool_name, info in tools.items():
            if info['required']:
                if not info['available'] or not info['meets_minimum']:
                    return False

        return True

    @staticmethod
    def print_tool_status(verbose: bool = True):
        """
        Print status of all WPA3 tools.

        Args:
            verbose: Whether to print detailed information
        """
        tools = WPA3ToolChecker.check_all_tools()

        Color.pl('\n{+} {C}WPA3 Tool Status:{W}')

        all_available = True
        missing_required = []
        outdated_tools = []

        for tool_name, info in tools.items():
            status_parts = []

            # Availability status
            if info['available']:
                status_parts.append('{G}Available{W}')
            else:
                status_parts.append('{R}Not Found{W}')
                if info['required']:
                    missing_required.append(tool_name)
                all_available = False

            # Version status
            if info['available'] and info['version_str']:
                status_parts.append(f'{{C}}v{info["version_str"]}{{W}}')

                if not info['meets_minimum']:
                    min_ver = WPA3ToolChecker.MIN_VERSIONS.get(tool_name)
                    if min_ver:
                        min_ver_str = '.'.join(str(v) for v in min_ver)
                        status_parts.append(f'{{O}}(min: {min_ver_str}){{W}}')
                        outdated_tools.append((tool_name, info['version_str'], min_ver_str))

            # Required/Optional indicator
            req_indicator = '{R}Required{W}' if info['required'] else '{O}Optional{W}'
            status_parts.append(req_indicator)

            # Print tool status
            Color.pl(f'    {tool_name}: ' + ' | '.join(status_parts))

        # Print summary
        if missing_required:
            Color.pl('\n{!} {R}Missing required tools:{W}')
            for tool in missing_required:
                url = WPA3ToolChecker.INSTALL_URLS.get(tool, 'N/A')
                Color.pl(f'    {tool}: {{C}}{url}{{W}}')

        if outdated_tools:
            Color.pl('\n{!} {O}Outdated tools (may cause issues):{W}')
            for tool, current, minimum in outdated_tools:
                Color.pl(f'    {tool}: {{O}}v{current}{{W}} (minimum: {{C}}v{minimum}{{W}})')

        if all_available and not outdated_tools:
            Color.pl('\n{+} {G}All WPA3 tools are available and up to date!{W}')
        elif not missing_required:
            Color.pl('\n{+} {G}All required WPA3 tools are available{W}')
        else:
            Color.pl('\n{!} {R}WPA3 attacks will not be available until required tools are installed{W}')

    @staticmethod
    def get_missing_tools() -> List[str]:
        """
        Get list of missing required tools.

        Returns:
            List of missing tool names
        """
        tools = WPA3ToolChecker.check_all_tools()
        missing = []

        for tool_name, info in tools.items():
            if info['required'] and not info['available']:
                missing.append(tool_name)

        return missing

    @staticmethod
    def print_installation_guide():
        """Print installation guide for WPA3 tools."""
        Color.pl('\n{+} {C}WPA3 Tool Installation Guide:{W}')
        Color.pl('')
        Color.pl('{C}Debian/Ubuntu/Kali:{W}')
        Color.pl('    sudo apt update')
        Color.pl('    sudo apt install hcxdumptool hcxtools hashcat tshark')
        Color.pl('')
        Color.pl('{C}Arch Linux:{W}')
        Color.pl('    sudo pacman -S hcxdumptool hcxtools hashcat wireshark-cli')
        Color.pl('')
        Color.pl('{C}From Source:{W}')
        Color.pl('    hcxdumptool: {O}https://github.com/ZerBea/hcxdumptool{W}')
        Color.pl('    hcxtools: {O}https://github.com/ZerBea/hcxtools{W}')
        Color.pl('    hashcat: {O}https://hashcat.net/hashcat/{W}')
        Color.pl('    tshark: {O}https://www.wireshark.org/{W}')

    @staticmethod
    def check_hashcat_sae_support() -> bool:
        """
        Check if hashcat supports WPA3-SAE (mode 22000).

        Returns:
            True if SAE support is available, False otherwise
        """
        if not Process.exists('hashcat'):
            return False

        try:
            # Run hashcat with --help to check for mode 22000
            command = ['hashcat', '--help']
            proc = Process(command, devnull=False)
            output = proc.stdout()

            # Check for mode 22000 (WPA-PBKDF2-PMKID+EAPOL) or 22001 (WPA3-SAE)
            return '22000' in output or 'WPA' in output

        except (OSError, ValueError):
            return False


if __name__ == '__main__':
    # Test WPA3 tool detection
    WPA3ToolChecker.print_tool_status()

    if WPA3ToolChecker.can_attack_wpa3():
        Color.pl('\n{+} {G}System is ready for WPA3 attacks!{W}')
    else:
        Color.pl('\n{!} {R}System is not ready for WPA3 attacks{W}')
        WPA3ToolChecker.print_installation_guide()
