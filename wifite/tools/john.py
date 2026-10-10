#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..config import Configuration
from ..util.color import Color
from ..util.process import Process
from ..tools.hashcat import HcxPcapngTool

import os
import re
import subprocess
import time
import threading


class JohnCracker:
    """
    Runs john and streams live progress from its stderr.

    John writes periodic status lines to stderr in the format:
      Xg 0:HH:MM:SS XX% (ETA: ...) Xg/s XXXp/s XXXc/s ...
    A background reader thread parses these lines for progress/speed/ETA.
    The cracked password is read from stdout (john prints it live) or via
    john --show after the run completes.

    Matches the HashcatCracker interface: start(), poll_status(),
    is_finished(), get_result(), and context-manager support.
    """

    def __init__(self, hash_file, wordlist, john_format='wpapsk'):
        self.hash_file = hash_file
        self.wordlist = wordlist
        self.john_format = john_format
        self.proc = None
        self._result_key = None
        self._status = {'progress': 0.0, 'speed': 'Unknown', 'eta': 'Unknown'}
        self._status_lock = threading.Lock()
        self._reader_thread = None
        self._stop_reader = threading.Event()

    def start(self, show_command=False):
        """Launch john and start the stderr reader thread."""
        command = [
            'john',
            f'--format={self.john_format}',
            f'--wordlist={self.wordlist}',
            self.hash_file,
        ]
        if show_command:
            Color.pl('{+} {D}Running: {W}{P}%s{W}' % ' '.join(command))
        self.proc = Process(command)
        self._reader_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._reader_thread.start()
        return self.proc

    def _read_stderr(self):
        """Read john's stderr line by line, parsing progress and cracked keys."""
        if not self.proc or not getattr(self.proc.pid, 'stderr', None):
            return
        try:
            while not self._stop_reader.is_set():
                raw = self.proc.pid.stderr.readline()
                if not raw:
                    if self.proc.poll() is not None:
                        break
                    continue
                line = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw
                line = line.rstrip('\r\n')
                # Progress line: "0g 0:00:00:03 13% (ETA: ...) 0g/s 500p/s ..."
                if re.match(r'\d+g\s+\d+:\d+:\d+:\d+', line):
                    self._parse_progress(line)
        except Exception as e:
            # Reader thread is best-effort (progress display only); log so a
            # crash here doesn't silently stop progress updates without a trace.
            from ..util.logger import log_debug
            log_debug('John', 'Progress reader thread stopped: %s' % e)

    def _parse_progress(self, line):
        """Update internal status from a john stderr progress line."""
        progress = None
        speed = None
        eta = None

        pct = re.search(r'(\d+)%', line)
        if pct:
            progress = int(pct.group(1)) / 100.0

        spd = re.search(r'([\d.]+)p/s', line)
        if spd:
            pps = float(spd.group(1))
            if pps >= 1_000_000:
                speed = f'{pps / 1_000_000:.1f} Mp/s'
            elif pps >= 1_000:
                speed = f'{pps / 1_000:.1f} kp/s'
            else:
                speed = f'{pps:.0f} p/s'

        eta_m = re.search(r'\(ETA:\s*([^)]+)\)', line)
        if eta_m:
            eta = eta_m.group(1).strip()

        with self._status_lock:
            if progress is not None:
                self._status['progress'] = progress
            if speed is not None:
                self._status['speed'] = speed
            if eta is not None:
                self._status['eta'] = eta

    def poll_status(self):
        """Return a snapshot of the latest parsed status."""
        with self._status_lock:
            return dict(self._status)

    def is_finished(self):
        """Return True if john has exited."""
        if not self.proc:
            return True
        return self.proc.poll() is not None

    def get_result(self):
        """Return the cracked password, or None if not found.

        Waits for the reader thread to drain, then runs john --show for a
        reliable result (john's live stdout line is format-specific and
        fragile to parse).
        """
        if self._reader_thread and self._reader_thread.is_alive():
            self._stop_reader.set()
            self._reader_thread.join(timeout=2.0)
        try:
            proc = Process(['john', '--show', f'--format={self.john_format}', self.hash_file])
            stdout, _ = proc.get_output()
            if not stdout or '0 password hashes cracked' in stdout:
                return None
            for line in stdout.splitlines():
                if not line or re.match(r'\d+ password hash', line):
                    continue
                parts = line.split(':')
                if len(parts) >= 2 and parts[1]:
                    return parts[1]
        except Exception:
            pass
        return None

    def interrupt(self):
        """Stop the reader thread and terminate john."""
        self._stop_reader.set()
        if self.proc:
            self.proc.interrupt()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.interrupt()


class John(Dependency):
    """ Wrapper for John program. """
    dependency_required = False
    dependency_name = 'john'
    dependency_url = 'https://www.openwall.com/john/'

    _wpapsk_capable = None  # cached tri-state: None=unchecked, True/False

    @staticmethod
    def is_wpapsk_capable():
        """Return True only if this john build supports wpapsk format.

        Standard john 1.9.0 (community) does not include wpapsk — it requires
        the jumbo patch set (john-jumbo / Kali's john package).  We detect
        support by checking whether --list=formats is a known option AND that
        the output contains 'wpapsk'.
        """
        if John._wpapsk_capable is not None:
            return John._wpapsk_capable

        try:
            result = subprocess.run(
                ['john', '--list=formats'],
                capture_output=True, text=True, timeout=10
            )
            combined = result.stdout + result.stderr
            # Standard john prints "Unknown option" → no wpapsk support
            if 'unknown option' in combined.lower():
                John._wpapsk_capable = False
            else:
                John._wpapsk_capable = 'wpapsk' in combined.lower()
        except Exception:
            John._wpapsk_capable = False

        return John._wpapsk_capable

    @staticmethod
    def _get_format():
        """Detect the best available wpapsk format (OpenCL > CUDA > CPU).

        Falls back to 'wpapsk' when --list=formats is unsupported (non-jumbo).
        The caller should check is_wpapsk_capable() before invoking this.
        """
        try:
            result = subprocess.run(
                ['john', '--list=formats'],
                capture_output=True, text=True, timeout=10
            )
            combined = result.stdout + result.stderr
            if 'wpapsk-opencl' in combined:
                return 'wpapsk-opencl'
            if 'wpapsk-cuda' in combined:
                return 'wpapsk-cuda'
        except Exception:
            pass
        return 'wpapsk'

    @staticmethod
    def crack_handshake(handshake, show_command=False, wordlist=None):
        if not John.is_wpapsk_capable():
            Color.pl(
                '{!} {R}john does not support wpapsk format.{W}\n'
                '{!} {O}The installed john is the standard community build '
                '(no WPA support).{W}\n'
                '{!} {O}Install john-jumbo for WPA cracking: {C}apt install john{W}'
            )
            return None

        john_file = HcxPcapngTool.generate_john_file(handshake, show_command=show_command)
        wordlist = wordlist or Configuration.wordlist
        key = None
        try:
            john_format = John._get_format()

            with JohnCracker(john_file, wordlist, john_format) as cracker:
                cracker.start(show_command=show_command)

                while not cracker.is_finished():
                    status = cracker.poll_status()
                    pct = int(status['progress'] * 100)
                    Color.p(f'\r{{+}} {{C}}John{{W}}: {{G}}{pct}%{{W}} '
                            f'@ {{C}}{status["speed"]}{{W}} '
                            f'ETA: {{C}}{status["eta"]}{{W}}   ')
                    time.sleep(2)

                Color.pl('')  # newline after the inline progress
                key = cracker.get_result()

            return key
        finally:
            if john_file and os.path.exists(john_file):
                try:
                    os.remove(john_file)
                    if Configuration.verbose > 1:
                        Color.pl('{!} {O}Cleaned up temporary john file{W}')
                except OSError as e:
                    if Configuration.verbose > 0:
                        Color.pl('{!} {O}Warning: Could not remove john file: %s{W}' % str(e))
