#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WPA3-SAE Detection and Classification Module

This module provides functionality to detect and classify WPA3-SAE capabilities
of wireless networks, including transition mode detection, PMF status, and
Dragonblood vulnerability indicators.
"""

import os
from typing import Dict, List, Any, Optional


class WPA3Detector:
    """
    Detects and classifies WPA3-SAE capabilities of wireless targets.

    Detection layers:
    1. Heuristic parse of airodump's Privacy/Authentication CSV fields
       (always available, but imprecise — can't tell PMF or SAE groups).
    2. Beacon RSN IE parse via tshark when a capture file is available
       — yields real PMF (MFPC/MFPR) bits and observed SAE groups from
       any captured SAE Commit frames.

    Results are cached in target.wpa3_info.
    """

    # PMF Status Constants
    PMF_DISABLED = 'disabled'
    PMF_OPTIONAL = 'optional'
    PMF_REQUIRED = 'required'

    # Known vulnerable SAE groups (Dragonblood)
    VULNERABLE_SAE_GROUPS = [22, 23, 24]  # Groups susceptible to timing attacks

    # Default SAE group (most common)
    DEFAULT_SAE_GROUP = 19

    # IEEE 802.11 AKM suite type for SAE
    AKM_TYPE_SAE = 8

    @staticmethod
    def detect_wpa3_capability(target, use_cache: bool = True,
                               capfile: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect WPA3 capability from target beacon/probe response.

        Args:
            target: Target object containing encryption and authentication info
            use_cache: If True, return cached results from target.wpa3_info if available
            capfile: Optional path to a pcap/pcapng file. When provided and
                     tshark is available, beacon RSN IE bits are parsed for
                     a precise PMF status and observed SAE groups.

        Returns:
            Dict with has_wpa3, has_wpa2, is_transition, pmf_status,
            sae_groups, dragonblood_vulnerable.
        """
        # Return cached results if available and caching is enabled
        if use_cache and hasattr(target, 'wpa3_info') and target.wpa3_info is not None:
            return target.wpa3_info.to_dict()

        full_enc = getattr(target, 'full_encryption_string', '')
        full_auth = getattr(target, 'full_authentication_string', '')
        primary_enc = getattr(target, 'primary_encryption', '')
        primary_auth = getattr(target, 'primary_authentication', '')

        # Heuristic pass from airodump's CSV fields
        has_wpa3 = ('WPA3' in full_enc or primary_enc == 'WPA3' or
                    'SAE' in full_auth or primary_auth == 'SAE')
        has_wpa2 = ('WPA2' in full_enc or primary_enc == 'WPA2' or
                    'PSK' in full_auth)

        if not has_wpa3:
            return {
                'has_wpa3': False,
                'has_wpa2': has_wpa2,
                'is_transition': False,
                'pmf_status': WPA3Detector.PMF_DISABLED,
                'sae_groups': [],
                'dragonblood_vulnerable': False
            }

        is_transition = has_wpa2

        # Defaults from the heuristic layer
        if is_transition:
            pmf_status = WPA3Detector.PMF_OPTIONAL
        else:
            pmf_status = WPA3Detector.PMF_REQUIRED
        sae_groups: List[int] = [WPA3Detector.DEFAULT_SAE_GROUP]

        # Precise layer: parse real RSN/SAE data from a capture if we have one
        bssid = getattr(target, 'bssid', None)
        if capfile and bssid and os.path.isfile(capfile):
            parsed = WPA3Detector._parse_rsn_from_capture(capfile, bssid)
            if parsed:
                if parsed.get('pmf_status'):
                    pmf_status = parsed['pmf_status']
                observed = parsed.get('sae_groups') or []
                if observed:
                    sae_groups = observed

        dragonblood_vulnerable = any(
            g in WPA3Detector.VULNERABLE_SAE_GROUPS for g in sae_groups)

        return {
            'has_wpa3': has_wpa3,
            'has_wpa2': has_wpa2,
            'is_transition': is_transition,
            'pmf_status': pmf_status,
            'sae_groups': sae_groups,
            'dragonblood_vulnerable': dragonblood_vulnerable
        }

    @staticmethod
    def _parse_rsn_from_capture(capfile: str, bssid: str) -> Optional[Dict[str, Any]]:
        """
        Parse precise WPA3 details from a pcap/pcapng capture via tshark.

        Returns:
            {'pmf_status': 'required'|'optional'|'disabled'|None,
             'sae_groups': [int, ...]}
            or None if tshark is unavailable or the parse fails.
        """
        from ..tools.tshark import Tshark
        if not Tshark.exists():
            return None

        result = {'pmf_status': None, 'sae_groups': []}
        try:
            result['pmf_status'] = WPA3Detector._parse_pmf_from_beacon(capfile, bssid)
        except (OSError, ValueError):
            pass
        try:
            result['sae_groups'] = WPA3Detector._parse_sae_groups_from_commits(capfile, bssid)
        except (OSError, ValueError):
            pass
        if result['pmf_status'] is None and not result['sae_groups']:
            return None
        return result

    @staticmethod
    def _parse_pmf_from_beacon(capfile: str, bssid: str) -> Optional[str]:
        """
        Extract PMF status from the RSN IE in a beacon frame.

        MFPR=1 → required; MFPC=1 & MFPR=0 → optional; MFPC=0 → disabled.
        """
        from ..util.process import Process
        command = [
            'tshark', '-r', capfile,
            '-Y', 'wlan.bssid == %s && wlan.fc.type_subtype == 0x08' % bssid,
            '-T', 'fields',
            '-e', 'wlan.rsn.capabilities.mfpc',
            '-e', 'wlan.rsn.capabilities.mfpr',
            '-c', '1',
        ]
        stdout, _ = Process.call(command, timeout=15)
        for line in (stdout or '').splitlines():
            parts = line.strip().split('\t')
            if len(parts) < 2:
                continue
            mfpc, mfpr = parts[0].strip(), parts[1].strip()
            if mfpr in ('1', 'True'):
                return WPA3Detector.PMF_REQUIRED
            if mfpc in ('1', 'True'):
                return WPA3Detector.PMF_OPTIONAL
            if mfpc in ('0', 'False'):
                return WPA3Detector.PMF_DISABLED
        return None

    @staticmethod
    def _parse_sae_groups_from_commits(capfile: str, bssid: str) -> List[int]:
        """
        Extract SAE groups actually observed in SAE Commit frames.

        Only works when the capture already contains SAE authentication
        traffic (e.g. after a capture attempt or from archived handshakes).
        SAE groups are NOT advertised in beacons — they're negotiated in
        the Commit exchange.
        """
        from ..util.process import Process
        command = [
            'tshark', '-r', capfile,
            '-Y', 'wlan.bssid == %s && wlan.fixed.auth.alg == 3' % bssid,
            '-T', 'fields',
            '-e', 'wlan.fixed.auth.sae.group',
        ]
        stdout, _ = Process.call(command, timeout=15)
        seen = []
        for line in (stdout or '').splitlines():
            token = line.strip()
            if not token:
                continue
            try:
                group = int(token)
            except ValueError:
                continue
            if group and group not in seen:
                seen.append(group)
        return seen

    @staticmethod
    def refresh_from_capture(target, capfile: str) -> bool:
        """
        Re-parse `target.wpa3_info` from a capture that (now) contains SAE frames.

        Useful after an SAE capture attempt: the first scan-time detection
        had no handshake, so sae_groups fell back to [19]. After capture,
        we can extract the real negotiated group and make
        is_dragonblood_vulnerable / is_timing_attack_viable accurate.

        Returns True if any field changed.
        """
        if not capfile or not os.path.isfile(capfile):
            return False
        bssid = getattr(target, 'bssid', None)
        if not bssid:
            return False
        parsed = WPA3Detector._parse_rsn_from_capture(capfile, bssid)
        if not parsed:
            return False

        info = getattr(target, 'wpa3_info', None)
        if info is None:
            return False

        changed = False
        if parsed.get('pmf_status') and parsed['pmf_status'] != info.pmf_status:
            info.pmf_status = parsed['pmf_status']
            changed = True
        if parsed.get('sae_groups') and parsed['sae_groups'] != info.sae_groups:
            info.sae_groups = parsed['sae_groups']
            new_vuln = any(g in WPA3Detector.VULNERABLE_SAE_GROUPS
                           for g in info.sae_groups)
            if new_vuln != info.dragonblood_vulnerable:
                info.dragonblood_vulnerable = new_vuln
            changed = True
        return changed

    # ------------------------------------------------------------------
    # Active SAE group probing (Dragonblood companion)
    # ------------------------------------------------------------------

    # Common SAE groups worth probing. ECP groups (19/20/21) are the
    # modern default; MODP groups (22/23/24) are the Dragonblood set.
    DEFAULT_PROBE_GROUPS = [19, 20, 21, 22, 23, 24]

    @staticmethod
    def _channel_to_freq(channel: int) -> int:
        if channel <= 13:
            return 2407 + channel * 5
        if channel == 14:
            return 2484
        return 5000 + channel * 5

    @staticmethod
    def _build_probe_config(bssid: str, essid: str, channel: int,
                            sae_group: int, password: str) -> str:
        """
        Build a wpa_supplicant config body for a single SAE group probe.

        Escapes ESSID/password so embedded quotes or backslashes don't
        corrupt the config.  Shared by the active group-probe and the
        Dragonblood timing attack so both agree on the format.
        """
        safe_essid = essid.replace('\\', '\\\\').replace('"', '\\"')
        safe_password = password.replace('\\', '\\\\').replace('"', '\\"')
        freq = WPA3Detector._channel_to_freq(channel)
        lines = [
            'ctrl_interface=/var/run/wpa_supplicant_wifite',
            'ap_scan=1',
            'fast_reauth=1',
        ]
        if sae_group:
            lines.append(f'sae_groups={sae_group}')
        lines.extend([
            '',
            'network={',
            f'    ssid="{safe_essid}"',
            f'    bssid={bssid}',
            f'    sae_password="{safe_password}"',
            '    key_mgmt=SAE',
            '    ieee80211w=2',
            f'    scan_freq={freq}',
            '}',
            '',
        ])
        return '\n'.join(lines)

    @staticmethod
    def probe_sae_groups_active(
        interface: str,
        bssid: str,
        essid: str,
        channel: int,
        groups_to_probe: Optional[List[int]] = None,
        per_group_timeout: int = 8,
    ) -> Dict[int, str]:
        """
        Actively probe an AP to discover which SAE groups it accepts.

        Sends one SAE Commit per candidate group via wpa_supplicant and
        classifies the AP's response:
          'accepted'    — AP replied with its own SAE Commit (group supported)
          'rejected'    — AP returned status 77 (Unsupported Finite Cyclic Group)
          'no_response' — no indicator observed within per_group_timeout

        This gives us real SAE-group support data WITHOUT waiting for a
        client to authenticate naturally. Companion to the passive
        parsers in _parse_sae_groups_from_commits().

        Requires:
          * wpa_supplicant on PATH
          * interface in managed mode (wpa_supplicant won't drive a
            monitor-mode virtual interface). Caller is responsible for
            mode toggling / restoration.
          * root privileges

        Args:
            interface:    Wireless interface name (validated).
            bssid:        Target BSSID.
            essid:        Target ESSID (hidden ESSIDs not supported).
            channel:      Target channel.
            groups_to_probe: Groups to test. Default: ECP + MODP set.
            per_group_timeout: Seconds to wait per group.

        Returns:
            Dict[int, str] mapping each probed group to a status. Empty
            dict if wpa_supplicant is unavailable or the setup failed.
        """
        from ..config.validators import validate_interface_name
        from ..util.process import Process
        validate_interface_name(interface)

        if not Process.exists('wpa_supplicant'):
            return {}
        if not essid:
            # Without an ESSID, wpa_supplicant can't scan to the target.
            return {}

        if groups_to_probe is None:
            groups_to_probe = list(WPA3Detector.DEFAULT_PROBE_GROUPS)

        results: Dict[int, str] = {}
        for group in groups_to_probe:
            status = WPA3Detector._probe_single_sae_group(
                interface, bssid, essid, channel, group, per_group_timeout)
            results[group] = status
        return results

    @staticmethod
    def _probe_single_sae_group(interface: str, bssid: str, essid: str,
                                channel: int, sae_group: int,
                                timeout: int) -> str:
        """
        Probe one SAE group. Returns 'accepted' / 'rejected' / 'no_response'.
        """
        import tempfile
        import time
        from ..config import Configuration
        from ..util.process import Process

        # A throwaway password. wpa_supplicant will compute a valid PWE
        # from it; the AP reaches the commit-response step without us
        # needing to know a real password.
        probe_password = 'wifite-sae-probe-pw'

        config_body = WPA3Detector._build_probe_config(
            bssid=bssid, essid=essid, channel=channel,
            sae_group=sae_group, password=probe_password)

        fd, config_path = tempfile.mkstemp(
            prefix='wifite_sae_probe_', suffix='.conf',
            dir=Configuration.temp())
        try:
            os.write(fd, config_body.encode('utf-8'))
            os.close(fd)
            os.chmod(config_path, 0o600)

            cmd = [
                'wpa_supplicant',
                '-i', interface,
                '-c', config_path,
                '-D', 'nl80211',
                '-dd',
            ]
            proc = Process(cmd, devnull=False)

            status = 'no_response'
            deadline = time.monotonic() + timeout
            try:
                while time.monotonic() < deadline and proc.poll() is None:
                    try:
                        raw = proc.pid.stdout.readline()
                    except (OSError, ValueError):
                        time.sleep(0.05)
                        continue
                    if not raw:
                        time.sleep(0.05)
                        continue
                    line = (raw.decode('utf-8', errors='replace')
                            if isinstance(raw, bytes) else raw)

                    # Explicit rejection: status 77 = Unsupported Finite
                    # Cyclic Group. This is the cleanest negative signal.
                    if ('status_code=77' in line
                            or 'Unsupported finite cyclic group' in line
                            or 'SAE: Unsupported group' in line):
                        status = 'rejected'
                        break

                    # Positive signal: the AP replied with its own commit.
                    # Seeing this means our group was accepted; whatever
                    # happens after (password failure, status 15, etc.)
                    # doesn't change the group-support answer.
                    if ('SAE: Processing peer commit' in line
                            or 'SAE: Peer commit' in line
                            or 'SAE: Processing commit' in line):
                        status = 'accepted'
                        break
            finally:
                import contextlib
                with contextlib.suppress(Exception):
                    proc.interrupt()
                    time.sleep(0.3)
                    if proc.poll() is None:
                        proc.kill()
            return status
        finally:
            try:
                os.remove(config_path)
            except OSError:
                pass

    @staticmethod
    def identify_transition_mode(target) -> bool:
        """
        Check if target supports both WPA2 and WPA3 (transition mode).
        
        Transition mode networks allow clients to connect using either WPA2
        or WPA3, making them vulnerable to downgrade attacks.
        
        Performance: Uses cached wpa3_info if available.
        
        Args:
            target: Target object to check
            
        Returns:
            True if target supports both WPA2 and WPA3, False otherwise
        """
        # Use cached info if available
        if hasattr(target, 'wpa3_info') and target.wpa3_info is not None:
            return target.wpa3_info.is_transition
        
        # Fallback to detection
        wpa3_info = WPA3Detector.detect_wpa3_capability(target)
        return wpa3_info['is_transition']

    @staticmethod
    def check_pmf_status(target) -> str:
        """
        Determine PMF (Protected Management Frames) status.
        
        PMF status affects attack strategies:
        - 'required': Deauth attacks won't work, must use passive capture
        - 'optional': Deauth attacks may work
        - 'disabled': Deauth attacks will work
        
        Performance: Uses cached wpa3_info if available.
        
        Args:
            target: Target object to check
            
        Returns:
            'required', 'optional', or 'disabled'
        """
        # Use cached info if available
        if hasattr(target, 'wpa3_info') and target.wpa3_info is not None:
            return target.wpa3_info.pmf_status
        
        # Fallback to detection
        wpa3_info = WPA3Detector.detect_wpa3_capability(target)
        return wpa3_info['pmf_status']

    @staticmethod
    def get_supported_sae_groups(target) -> List[int]:
        """
        Extract supported SAE groups from target information.
        
        SAE groups define the elliptic curve used for authentication.
        Common groups:
        - Group 19: 256-bit random ECP group (most common)
        - Group 20: 384-bit random ECP group
        - Group 21: 521-bit random ECP group
        - Groups 22-24: Vulnerable to Dragonblood attacks
        
        Performance: Uses cached wpa3_info if available.
        
        Args:
            target: Target object to analyze
            
        Returns:
            List of supported SAE group numbers. Returns [19] as default
            if WPA3 is detected but specific groups cannot be determined.
        """
        # Use cached info if available
        if hasattr(target, 'wpa3_info') and target.wpa3_info is not None:
            return target.wpa3_info.sae_groups
        
        # Fallback to detection
        wpa3_info = WPA3Detector.detect_wpa3_capability(target)
        return wpa3_info['sae_groups']

    @staticmethod
    def _has_wpa3(target) -> bool:
        """
        Check if target supports WPA3.
        
        Optimized to minimize attribute access and string operations.
        
        Args:
            target: Target object to check
            
        Returns:
            True if WPA3 is supported
        """
        # Check full encryption string for WPA3 (most reliable)
        full_enc = getattr(target, 'full_encryption_string', '')
        if 'WPA3' in full_enc:
            return True
        
        # Check primary encryption
        if getattr(target, 'primary_encryption', '') == 'WPA3':
            return True
        
        # Check authentication for SAE (WPA3's authentication method)
        full_auth = getattr(target, 'full_authentication_string', '')
        if 'SAE' in full_auth:
            return True
        
        # Check primary authentication
        if getattr(target, 'primary_authentication', '') == 'SAE':
            return True
        
        return False

    @staticmethod
    def _has_wpa2(target) -> bool:
        """
        Check if target supports WPA2.
        
        Optimized to minimize attribute access and string operations.
        
        Args:
            target: Target object to check
            
        Returns:
            True if WPA2 is supported
        """
        # Check full encryption string for WPA2 (most reliable)
        full_enc = getattr(target, 'full_encryption_string', '')
        if 'WPA2' in full_enc:
            return True
        
        # Check primary encryption
        if getattr(target, 'primary_encryption', '') == 'WPA2':
            return True
        
        # Check authentication for PSK (WPA2's common authentication method)
        # Note: PSK can also be used with WPA, but in context of WPA3 detection,
        # if we see PSK alongside SAE, it indicates transition mode
        full_auth = getattr(target, 'full_authentication_string', '')
        if 'PSK' in full_auth:
            return True
        
        return False

    @staticmethod
    def _check_dragonblood_vulnerability(sae_groups: List[int], has_wpa3: bool) -> bool:
        """
        Check for known Dragonblood vulnerability indicators.
        
        Dragonblood vulnerabilities (CVE-2019-13377 and related) affect certain
        SAE group configurations and implementations.
        
        Args:
            sae_groups: List of supported SAE groups
            has_wpa3: Whether the target supports WPA3
            
        Returns:
            True if vulnerability indicators are detected
        """
        if not has_wpa3:
            return False
        
        # Check if any vulnerable groups are supported
        for group in sae_groups:
            if group in WPA3Detector.VULNERABLE_SAE_GROUPS:
                return True
        
        return False


class WPA3Info:
    """
    Data class to store WPA3 capability information for a target.
    
    This class encapsulates all WPA3-related information detected for a
    wireless target, making it easy to store and retrieve this data.
    """
    
    def __init__(self, has_wpa3: bool = False, has_wpa2: bool = False,
                 is_transition: bool = False, pmf_status: str = WPA3Detector.PMF_DISABLED,
                 sae_groups: Optional[List[int]] = None,
                 dragonblood_vulnerable: bool = False):
        """
        Initialize WPA3Info object.
        
        Args:
            has_wpa3: True if WPA3 is supported
            has_wpa2: True if WPA2 is supported
            is_transition: True if both WPA2 and WPA3 are supported
            pmf_status: 'required', 'optional', or 'disabled'
            sae_groups: List of supported SAE groups
            dragonblood_vulnerable: True if vulnerable indicators detected
        """
        self.has_wpa3 = has_wpa3
        self.has_wpa2 = has_wpa2
        self.is_transition = is_transition
        self.pmf_status = pmf_status
        self.sae_groups = sae_groups if sae_groups is not None else []
        self.dragonblood_vulnerable = dragonblood_vulnerable
    
    def get(self, key: str, default=None):
        """
        Get attribute value by key (dict-like interface for backward compatibility).
        
        Args:
            key: Attribute name
            default: Default value if attribute doesn't exist
            
        Returns:
            Attribute value or default
        """
        return getattr(self, key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize WPA3Info to dictionary for storage.
        
        Returns:
            Dictionary representation of WPA3Info
        """
        return {
            'has_wpa3': self.has_wpa3,
            'has_wpa2': self.has_wpa2,
            'is_transition': self.is_transition,
            'pmf_status': self.pmf_status,
            'sae_groups': self.sae_groups,
            'dragonblood_vulnerable': self.dragonblood_vulnerable
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WPA3Info':
        """
        Deserialize WPA3Info from dictionary.
        
        Args:
            data: Dictionary containing WPA3Info data
            
        Returns:
            WPA3Info object
        """
        return cls(
            has_wpa3=data.get('has_wpa3', False),
            has_wpa2=data.get('has_wpa2', False),
            is_transition=data.get('is_transition', False),
            pmf_status=data.get('pmf_status', WPA3Detector.PMF_DISABLED),
            sae_groups=data.get('sae_groups', []),
            dragonblood_vulnerable=data.get('dragonblood_vulnerable', False)
        )
    
    def __repr__(self) -> str:
        """String representation of WPA3Info."""
        return (f"WPA3Info(has_wpa3={self.has_wpa3}, has_wpa2={self.has_wpa2}, "
                f"is_transition={self.is_transition}, pmf_status={self.pmf_status}, "
                f"sae_groups={self.sae_groups}, dragonblood_vulnerable={self.dragonblood_vulnerable})")
