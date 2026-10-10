#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tshark wrapper with native Scapy fallback.

Uses native Python/Scapy implementation when tshark is unavailable,
providing handshake verification and WPS detection without external tools.
"""

from .dependency import Dependency
from ..model.target import WPSState
from ..util.process import Process
import re


class Tshark(Dependency):
    """Wrapper for Tshark program with Scapy fallback."""
    
    dependency_required = False
    dependency_name = 'tshark'
    dependency_url = 'apt install tshark'
    dependency_packages = {
        'apt': 'tshark', 'pacman': 'wireshark-cli',
        'dnf': 'wireshark-cli', 'brew': 'wireshark',
    }
    dependency_category = Dependency.CATEGORY_INSPECT

    # Track if native (Scapy) is available
    _native_available = None

    def __init__(self):
        pass

    @classmethod
    def _can_use_native(cls) -> bool:
        """Check if native Scapy implementation is available."""
        if cls._native_available is None:
            try:
                from ..native.handshake import ScapyHandshake
                from ..native.wps import ScapyWPS
                cls._native_available = ScapyHandshake.is_available() and ScapyWPS.is_available()
            except ImportError:
                cls._native_available = False
        return cls._native_available

    @staticmethod
    def _extract_src_dst_index_total(line):
        """Extract BSSIDs, handshake # (1-4) and handshake 'total' (4)"""
        mac_regex = ('[a-zA-Z0-9]{2}:' * 6)[:-1]
        match = re.search(r'(%s)\s*.*\s*(%s).*Message.*(\d).*of.*(\d)' % (mac_regex, mac_regex), line)
        if match is None:
            return None, None, None, None
        (src, dst, index, total) = match.groups()
        return src, dst, index, total

    @staticmethod
    def _build_target_client_handshake_map(output, bssid=None):
        """Build map of target_ssid,client_ssid -> handshake #s"""
        target_client_msg_nums = {}

        for line in output.split('\n'):
            src, dst, index, total = Tshark._extract_src_dst_index_total(line)
            if src is None:
                continue

            index = int(index)
            total = int(total)

            if total != 4:
                continue

            if index % 2 == 1:
                target = src
                client = dst
            else:
                client = src
                target = dst

            if bssid is not None and bssid.lower() != target.lower():
                continue

            target_client_key = f'{target},{client}'

            if index == 1:
                target_client_msg_nums[target_client_key] = 1
            elif target_client_key not in target_client_msg_nums \
                    or index - 1 != target_client_msg_nums[target_client_key]:
                continue
            else:
                target_client_msg_nums[target_client_key] = index

        return target_client_msg_nums

    @classmethod
    def bssids_with_handshakes(cls, capfile, bssid=None):
        """
        Get list of BSSIDs with valid handshakes in capture file.
        
        Uses native Scapy implementation if tshark is unavailable.
        """
        # Try native implementation first if tshark is not available
        if not cls.exists():
            if cls._can_use_native():
                try:
                    from ..native.handshake import ScapyHandshake
                    return ScapyHandshake.bssids_with_handshakes(capfile, bssid)
                except (ImportError, OSError):
                    pass
            return []
        
        # Use tshark
        command = [
            'tshark',
            '-r', capfile,
            '-n',
            '-Y', 'eapol'
        ]
        with Process(command, devnull=False) as tshark:
            target_client_msg_nums = Tshark._build_target_client_handshake_map(tshark.stdout(), bssid=bssid)

        bssids = set()
        for (target_client, num) in list(target_client_msg_nums.items()):
            if num == 4:
                this_bssid = target_client.split(',')[0]
                bssids.add(this_bssid)

        return list(bssids)

    @staticmethod
    def _build_eapol_summary(output, bssid=None):
        """Build a per-AP map of which 4-way messages appear in tshark output.

        Returns dict mapping bssid (lowercase) -> set of int msg numbers in
        {1,2,3,4}.
        """
        summary = {}
        for line in output.split('\n'):
            src, dst, index, total = Tshark._extract_src_dst_index_total(line)
            if src is None:
                continue
            index = int(index)
            total = int(total)
            if total != 4:
                continue
            # Odd indexes (1, 3) are AP→client; even (2, 4) are client→AP.
            target = src if index % 2 == 1 else dst
            if bssid is not None and bssid.lower() != target.lower():
                continue
            summary.setdefault(target.lower(), set()).add(index)
        return summary

    @classmethod
    def eapol_message_summary(cls, capfile, bssid=None):
        """
        Inspect EAPOL traffic and return a per-AP map of which 4-way messages
        were observed.

        Returns:
            dict mapping bssid (lowercase) -> set of int msg numbers in {1,2,3,4}.
            Empty dict if tshark isn't available or no EAPOL frames are present.
        """
        if not cls.exists():
            return {}

        command = ['tshark', '-r', capfile, '-n', '-Y', 'eapol']
        with Process(command, devnull=False) as tshark:
            output = tshark.stdout()
        return cls._build_eapol_summary(output, bssid=bssid)

    @classmethod
    def eapol_analysis(cls, capfile, bssid=None):
        """Run tshark once and derive both EAPOL verdicts from a single parse.

        Combines the work of bssids_with_handshakes() and
        eapol_message_summary() so the capfile is only read once when the caller
        needs both (e.g. handshake analysis that falls back to a partial-4-way
        report when no complete handshake is present).

        Returns:
            (bssids, summary) tuple where `bssids` is the list of APs with a
            complete sequential 4-way handshake and `summary` is the per-AP map
            of observed message numbers (see eapol_message_summary). Both are
            empty if tshark is unavailable or no EAPOL frames are present.
        """
        if not cls.exists():
            return [], {}

        command = ['tshark', '-r', capfile, '-n', '-Y', 'eapol']
        with Process(command, devnull=False) as tshark:
            output = tshark.stdout()

        handshake_map = cls._build_target_client_handshake_map(output, bssid=bssid)
        bssids = list({key.split(',')[0] for key, num in handshake_map.items() if num == 4})
        summary = cls._build_eapol_summary(output, bssid=bssid)
        return bssids, summary

    @classmethod
    def bssids_with_handshakes_native(cls, capfile, bssid=None):
        """
        Get list of BSSIDs with valid handshakes using native Scapy.
        
        This method always uses Scapy, regardless of tshark availability.
        """
        if cls._can_use_native():
            try:
                from ..native.handshake import ScapyHandshake
                return ScapyHandshake.bssids_with_handshakes(capfile, bssid)
            except (ImportError, OSError):
                pass
        return []

    @staticmethod
    def bssid_essid_pairs(capfile, bssid):
        """Find all BSSIDs with corresponding ESSIDs from cap file."""
        if not Tshark.exists():
            return []

        ssid_pairs = set()

        command = [
            'tshark',
            '-r', capfile,
            '-n',
            '-Y', '"wlan.fc.type_subtype == 0x08 || wlan.fc.type_subtype == 0x05"',
        ]

        tshark = Process(command, devnull=False)

        for line in tshark.stdout().split('\n'):
            mac_regex = ('[a-zA-Z0-9]{2}:' * 6)[:-1]
            match = re.search(f'({mac_regex}) [^ ]* ({mac_regex}).*.*SSID=(.*)$', line)
            if match is None:
                continue

            (src, dst, essid) = match.groups()

            if dst.lower() == 'ff:ff:ff:ff:ff:ff':
                continue

            if (bssid is not None and bssid.lower() == src.lower()) or bssid is None:
                ssid_pairs.add((src, essid))

        return list(ssid_pairs)

    @classmethod
    def check_for_wps_and_update_targets(cls, capfile, targets):
        """
        Update targets with WPS status from capture file.
        
        Uses native Scapy implementation if tshark is unavailable.
        """
        # Try native implementation first if tshark is not available
        if not cls.exists():
            if cls._can_use_native():
                try:
                    from ..native.wps import ScapyWPS
                    ScapyWPS.update_targets(capfile, targets)
                    return
                except (ImportError, OSError):
                    pass
            raise ValueError('Cannot detect WPS networks: Tshark does not exist and native fallback failed')
        
        # Use tshark
        command = [
            'tshark',
            '-r', capfile,
            '-n',
            '-Y', 'wps.wifi_protected_setup_state && wlan.da == ff:ff:ff:ff:ff:ff',
            '-T', 'fields',
            '-e', 'wlan.ta',
            '-e', 'wps.ap_setup_locked',
            '-E', 'separator=,'
        ]
        p = Process(command)

        try:
            p.wait()
            lines = p.stdout()
        except KeyboardInterrupt:
            raise
        except (OSError, IOError) as e:
            from ..config import Configuration
            if Configuration.verbose > 0:
                from ..util.color import Color
                Color.pl('{!} {O}Warning: tshark WPS detection failed: %s{W}' % str(e))
            return
        except Exception as e:
            from ..config import Configuration
            from ..util.color import Color
            Color.pl('{!} {R}Unexpected error in WPS detection: %s{W}' % str(e))
            if Configuration.verbose > 1:
                import traceback
                Color.pl('{!} {O}%s{W}' % traceback.format_exc())
            return
        
        wps_bssids = set()
        locked_bssids = set()
        
        for line in lines.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(',', maxsplit=1)
            
            if len(parts) < 1:
                continue
            
            bssid = parts[0].strip()
            locked = parts[1].strip() if len(parts) > 1 else ''
            
            if len(bssid) != 17 or bssid.count(':') != 5:
                continue
            
            if locked.lower() in ('0x01', '0x1', '1'):
                locked_bssids.add(bssid.upper())
            else:
                wps_bssids.add(bssid.upper())

        for t in targets:
            target_bssid = t.bssid.upper()
            if target_bssid in wps_bssids:
                t.wps = WPSState.UNLOCKED
            elif target_bssid in locked_bssids:
                t.wps = WPSState.LOCKED
            else:
                t.wps = WPSState.NONE

    @classmethod
    def check_for_wps_native(cls, capfile, targets):
        """
        Update targets with WPS status using native Scapy.
        
        This method always uses Scapy, regardless of tshark availability.
        """
        if cls._can_use_native():
            try:
                from ..native.wps import ScapyWPS
                ScapyWPS.update_targets(capfile, targets)
                return True
            except (ImportError, OSError):
                pass
        return False
    
    @classmethod
    def exists(cls):
        """Check if tshark binary exists."""
        return Process.exists(cls.dependency_name)
    
    @classmethod
    def can_verify_handshakes(cls) -> bool:
        """
        Check if handshake verification is available.
        
        Returns True if either tshark or native Scapy is available.
        """
        if cls.exists():
            return True
        return cls._can_use_native()
    
    @classmethod
    def can_detect_wps(cls) -> bool:
        """
        Check if WPS detection is available.
        
        Returns True if either tshark or native Scapy is available.
        """
        if cls.exists():
            return True
        return cls._can_use_native()


class TsharkMonitor:
    """
    Wrapper for tshark in monitoring mode for attack detection.
    Captures deauth and disassoc frames in real-time.
    """

    def __init__(self, interface, channel=None):
        """
        Initialize TsharkMonitor.

        Args:
            interface: Wireless interface to monitor
            channel: Optional channel to monitor (None = current channel)
        """
        self.interface = interface
        self.channel = channel
        self.proc = None

    def start(self):
        """
        Start tshark with filters for deauth/disassoc frames.
        """
        import subprocess

        command = [
            'tshark',
            '-i', self.interface,
            '-l',
            '-T', 'fields',
            '-e', 'frame.time_epoch',
            '-e', 'wlan.fc.type_subtype',
            '-e', 'wlan.sa',
            '-e', 'wlan.da',
            '-e', 'wlan.bssid',
            '-e', 'wlan_radio.channel',
            '-Y', '(wlan.fc.type_subtype == 0x0c) || (wlan.fc.type_subtype == 0x0a)'
        ]

        self.proc = Process(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return self.proc

    def read_frame(self):
        """
        Read and parse next frame from tshark output.
        """
        if not self.proc or not self.proc.pid or not self.proc.pid.stdout:
            return None

        try:
            line = self.proc.pid.stdout.readline()
            if not line:
                return None

            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='ignore')

            line = line.strip()
            if not line:
                return None

            fields = line.split('\t')
            if len(fields) < 5:
                return None
            
            return {
                'timestamp': float(fields[0]) if fields[0] else 0.0,
                'frame_type': fields[1] if len(fields) > 1 else '',
                'source_mac': fields[2] if len(fields) > 2 else '',
                'dest_mac': fields[3] if len(fields) > 3 else '',
                'bssid': fields[4] if len(fields) > 4 else '',
                'channel': fields[5] if len(fields) > 5 else ''
            }
        except (OSError, IOError):
            return None
    
    def stop(self):
        """Stop tshark process gracefully."""
        if self.proc:
            self.proc.interrupt()
            self.proc = None


if __name__ == '__main__':
    test_file = './tests/files/contains_wps_network.cap'

    target_bssid = 'A4:2B:8C:16:6B:3A'
    from ..model.target import Target
    fields = [
        'A4:2B:8C:16:6B:3A',
        '2015-05-27 19:28:44', '2015-05-27 19:28:46',
        '11',
        '54',
        'WPA2', 'CCMP TKIP', 'PSK',
        '-58', '2', '0', '0.0.0.0', '9',
        'Test Router Please Ignore',
    ]
    t = Target(fields)
    targets = [t]

    Tshark.check_for_wps_and_update_targets(test_file, targets)

    print(f'Target(BSSID={targets[0].bssid}).wps = {targets[0].wps} (Expected: 1)')
    if targets[0].wps != WPSState.UNLOCKED:
        raise ValueError(f'Expected WPSState.UNLOCKED, got {targets[0].wps}')

    print((Tshark.bssids_with_handshakes(test_file, bssid=target_bssid)))
