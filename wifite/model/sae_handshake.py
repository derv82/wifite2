#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SAE Handshake Model

This module provides functionality to represent, validate, and manipulate
WPA3-SAE handshakes captured during attacks.
"""

from ..util.process import Process
from ..util.color import Color
from ..tools.tshark import Tshark

import os
from typing import Dict, Optional, List, Any


class SAEHandshake:
    """
    Represents a WPA3-SAE handshake.

    A complete SAE handshake consists of:
    - SAE Commit frames (from both AP and client)
    - SAE Confirm frames (from both AP and client)

    This class provides methods to:
    - Validate handshake completeness
    - Extract SAE authentication data
    - Convert to hashcat format for cracking
    - Save handshake to file
    """

    def __init__(self, capfile: str, bssid: str, essid: Optional[str] = None):
        """
        Initialize SAEHandshake object.

        Args:
            capfile: Path to capture file containing SAE frames
            bssid: BSSID of the target AP
            essid: ESSID of the target AP (optional)
        """
        self.capfile = capfile
        self.bssid = bssid
        self.essid = essid
        self.commit_frames = []
        self.confirm_frames = []
        self.sae_data = None
        self.hash_file = None

    def has_complete_handshake(self) -> bool:
        """
        Check if capture contains a complete SAE handshake.

        A complete SAE handshake requires:
        - At least one SAE Commit frame
        - At least one SAE Confirm frame

        Returns:
            True if handshake is complete, False otherwise
        """
        # First try using hcxpcapngtool to validate
        if self._validate_with_hcxpcapngtool():
            return True

        # Fall back to tshark validation
        if Tshark.exists():
            return self._validate_with_tshark()

        return False

    def _validate_with_hcxpcapngtool(self) -> bool:
        """
        Validate SAE handshake using hcxpcapngtool.

        Returns:
            True if hcxpcapngtool can extract valid SAE data
        """
        if not Process.exists('hcxpcapngtool'):
            return False

        try:
            # Try to convert to hashcat format
            # If successful, we have a valid handshake
            temp_hash = f'{self.capfile}.temp.22000'

            command = [
                'hcxpcapngtool',
                '-o', temp_hash,
                self.capfile
            ]

            if self.bssid:
                # Filter by BSSID if specified
                command.extend(['--bssid', self.bssid.replace(':', '')])

            proc = Process(command, devnull=False)
            proc.wait()

            # Check if hash file was created and has content
            if os.path.exists(temp_hash) and os.path.getsize(temp_hash) > 0:
                # Clean up temp file
                os.remove(temp_hash)
                return True

            return False

        except Exception:
            return False

    def _validate_with_tshark(self) -> bool:
        """
        Validate SAE handshake using tshark.

        A complete SAE handshake must contain BOTH:
          - an SAE Commit  (authentication transaction sequence 1), and
          - an SAE Confirm (authentication transaction sequence 2).

        Merely observing two SAE authentication frames is not sufficient —
        two retransmitted Commits (or a Commit from each side with no
        Confirm) would otherwise be misreported as complete. We therefore
        inspect the auth-sequence numbers and require both 1 and 2 to appear.

        Returns:
            True if both an SAE Commit and an SAE Confirm are observed.
        """
        try:
            # SAE uses authentication frame type (0x0b) with auth algorithm 3.
            filter_str = 'wlan.fc.type_subtype == 0x0b && wlan.fixed.auth.alg == 3'
            if self.bssid:
                # Add BSSID filter for efficiency
                filter_str += f' && wlan.bssid == {self.bssid}'

            command = [
                'tshark',
                '-r', self.capfile,
                '-Y', filter_str,
                '-T', 'fields',
                '-e', 'wlan.fixed.auth.seq',
                # Bound the work — SAE auth frames are few, and we early-exit
                # as soon as both a Commit and a Confirm have been seen.
                '-c', '50',
            ]

            proc = Process(command, devnull=False)
            output = proc.stdout()

            seen_seqs = set()
            for line in output.split('\n'):
                seq = line.strip()
                if not seq:
                    continue
                # Be defensive about extra fields/separators per line.
                seq = seq.split('\t')[0].split(',')[0].strip()
                if seq in ('1', '2'):
                    seen_seqs.add(seq)
                    if '1' in seen_seqs and '2' in seen_seqs:
                        return True

            return False

        except Exception:
            return False

    def extract_sae_data(self) -> Optional[Dict[str, Any]]:
        """
        Extract SAE authentication data from capture with optimized processing.

        Optimizations:
        - Uses efficient filtering to reduce processing overhead
        - Streams data processing to handle large captures
        - Limits field extraction to only what's needed

        Returns:
            Dictionary containing SAE data, or None if extraction fails
        """
        if not Tshark.exists():
            return None

        try:
            # Build efficient filter string
            filter_str = 'wlan.fc.type_subtype == 0x0b && wlan.fixed.auth.alg == 3'
            if self.bssid:
                filter_str += f' && wlan.bssid == {self.bssid}'

            # Extract SAE frame details with minimal fields for efficiency
            command = [
                'tshark',
                '-r', self.capfile,
                '-Y', filter_str,
                '-T', 'fields',
                '-e', 'wlan.bssid',
                '-e', 'wlan.sa',
                '-e', 'wlan.da',
                '-e', 'wlan.fixed.auth.sae.group',
                '-e', 'frame.time_epoch'
            ]

            proc = Process(command, devnull=False)
            output = proc.stdout()

            # Stream process frames for memory efficiency
            frames = []
            for line in output.split('\n'):
                if not line.strip():
                    continue

                parts = line.split('\t')
                if len(parts) >= 4:
                    frames.append({
                        'bssid': parts[0],
                        'source': parts[1],
                        'dest': parts[2],
                        'sae_group': parts[3] if len(parts) > 3 else None,
                        'timestamp': parts[4] if len(parts) > 4 else None
                    })

            if frames:
                self.sae_data = {
                    'bssid': self.bssid,
                    'essid': self.essid,
                    'frames': frames,
                    'frame_count': len(frames)
                }
                return self.sae_data

            return None

        except Exception:
            return None

    def convert_to_hashcat(self, output_file: Optional[str] = None) -> Optional[str]:
        """
        Convert SAE handshake to hashcat format (mode 22000).

        Args:
            output_file: Path to output hash file (optional)
                        If None, generates filename based on BSSID/ESSID

        Returns:
            Path to hash file if successful, None otherwise
        """
        if not Process.exists('hcxpcapngtool'):
            Color.pl('{!} {R}hcxpcapngtool not found - cannot convert SAE handshake{W}')
            return None

        # Generate output filename if not provided
        if not output_file:
            essid_part = self.essid.replace(' ', '_') if self.essid else 'unknown'
            bssid_part = self.bssid.replace(':', '-') if self.bssid else 'unknown'
            output_file = f'sae_handshake_{essid_part}_{bssid_part}.22000'

        try:
            command = [
                'hcxpcapngtool',
                '-o', output_file,
                self.capfile
            ]

            # Add BSSID filter if specified
            if self.bssid:
                command.extend(['--bssid', self.bssid.replace(':', '')])

            # Add ESSID filter if specified
            if self.essid:
                command.extend(['--essid', self.essid])

            Color.pl('{+} Converting SAE handshake to hashcat format...')
            proc = Process(command, devnull=False)
            proc.wait()

            # Check if conversion was successful
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                Color.pl('{+} {G}Successfully converted to hashcat format:{W} {C}%s{W}' % output_file)
                self.hash_file = output_file
                return output_file
            else:
                Color.pl('{!} {R}Failed to convert SAE handshake{W}')
                return None

        except Exception as e:
            Color.pl('{!} {R}Error converting SAE handshake:{W} %s' % str(e))
            return None

    def save(self, output_dir: str = 'hs') -> str:
        """
        Save SAE handshake capture file to directory.

        Args:
            output_dir: Directory to save handshake (default: 'hs')

        Returns:
            Path to saved handshake file
        """
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Generate filename
        essid_part = self.essid.replace(' ', '_') if self.essid else 'unknown'
        bssid_part = self.bssid.replace(':', '-') if self.bssid else 'unknown'
        filename = f'sae_handshake_{essid_part}_{bssid_part}.cap'
        output_path = os.path.join(output_dir, filename)

        # Copy capture file to output directory
        from shutil import copy
        copy(self.capfile, output_path)

        Color.pl('{+} Saved SAE handshake to {C}%s{W}' % output_path)

        return output_path

    def analyze(self):
        """
        Analyze and display information about the SAE handshake.
        """
        Color.pl('\n{+} {C}SAE Handshake Analysis:{W}')
        Color.pl('    Capture File: {C}%s{W}' % self.capfile)
        Color.pl('    BSSID: {C}%s{W}' % (self.bssid or 'Unknown'))
        Color.pl('    ESSID: {C}%s{W}' % (self.essid or 'Unknown'))

        # Check if handshake is complete
        if self.has_complete_handshake():
            Color.pl('    Status: {G}Complete SAE handshake detected{W}')

            # Extract SAE data
            sae_data = self.extract_sae_data()
            if sae_data:
                Color.pl('    SAE Frames: {C}%d{W}' % sae_data.get('frame_count', 0))
        else:
            Color.pl('    Status: {R}Incomplete or invalid SAE handshake{W}')

    def extract_frame_timing(self) -> List[Dict]:
        """
        Extract precise timestamps for all SAE Commit/Confirm frames.

        Uses tshark to pull per-frame epoch timestamps so that response
        latencies can be computed externally (e.g. by DragonbloodTimingAttack).

        Returns:
            List of dicts with keys: type ('commit'/'confirm'), timestamp,
            src, dst, seq, sae_group.
        """
        from ..util.dragonblood_timing import DragonbloodTimingAttack
        return DragonbloodTimingAttack.extract_timing_from_pcap(
            self.capfile, self.bssid)

    def get_ap_response_times_us(self) -> List[float]:
        """
        Compute AP SAE Commit response latencies from this capture.

        Pairs each client-sent Commit with the next AP-sent Commit and
        returns the time deltas in microseconds.

        Returns:
            List of response times in microseconds.
        """
        from ..util.dragonblood_timing import DragonbloodTimingAttack
        frames = self.extract_frame_timing()
        if not frames:
            return []
        return DragonbloodTimingAttack.compute_pcap_response_times(
            frames, self.bssid)

    @staticmethod
    def check_tools() -> Dict[str, bool]:
        """
        Check if required tools for SAE handshake processing are available.

        Returns:
            Dictionary with tool availability status
        """
        return {
            'hcxpcapngtool': Process.exists('hcxpcapngtool'),
            'tshark': Tshark.exists(),
            'hashcat': Process.exists('hashcat')
        }

    @staticmethod
    def print_tool_status():
        """Print status of required tools for SAE handshake processing."""
        tools = SAEHandshake.check_tools()

        Color.pl('\n{+} {C}SAE Handshake Tool Status:{W}')
        for tool, available in tools.items():
            status = '{G}Available{W}' if available else '{R}Not Found{W}'
            Color.pl(f'    {tool}: {status}')

        if not tools['hcxpcapngtool']:
            Color.pl('\n{!} {O}Warning:{W} hcxpcapngtool is required for SAE handshake processing')
            Color.pl('    Install: {C}apt install hcxtools{W} or {C}brew install hcxtools{W}')


if __name__ == '__main__':
    # Test SAEHandshake functionality
    SAEHandshake.print_tool_status()
