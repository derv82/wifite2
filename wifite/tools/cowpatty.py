#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..config import Configuration
from ..util.color import Color
from ..util.process import Process

import re
import time
import threading


class CowpattyCracker:
    """
    Runs cowpatty and streams live progress from its stdout.

    Cowpatty prints a progress line every 1000 candidates:
      key no. 1000: candidate
    A background reader thread parses these lines to derive key count,
    speed (keys/s), and completion percentage.  The cracked password is
    captured from the same stream when cowpatty prints:
      The PSK is "password"

    Matches the HashcatCracker / JohnCracker interface: start(),
    poll_status(), is_finished(), get_result(), and context-manager support.
    """

    PROGRESS_INTERVAL = 1000  # cowpatty reports every N keys

    def __init__(self, capfile, essid, wordlist):
        self.capfile  = capfile
        self.essid    = essid
        self.wordlist = wordlist
        self.proc     = None

        self._result_key  = None
        self._key_count   = 0
        self._start_time  = None
        self._total_keys  = self._count_wordlist(wordlist)

        self._status      = {'progress': 0.0, 'speed': 'Unknown', 'eta': 'Unknown'}
        self._status_lock = threading.Lock()
        self._reader      = None
        self._stop        = threading.Event()

    @staticmethod
    def _count_wordlist(path):
        """Count lines in the wordlist for percentage calculation."""
        try:
            with open(path, 'rb') as fh:
                return sum(1 for _ in fh)
        except OSError:
            return 0

    def start(self, show_command=False):
        """Launch cowpatty and start the stdout reader thread."""
        command = [
            'cowpatty',
            '-f', self.wordlist,
            '-r', self.capfile,
            '-s', self.essid,
        ]
        if show_command:
            Color.pl('{+} {D}Running: {W}{P}%s{W}' % ' '.join(command))
        self._start_time = time.monotonic()
        self.proc = Process(command)
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()
        return self.proc

    def _read_stdout(self):
        """Read cowpatty stdout line-by-line, updating status and capturing the key."""
        if not self.proc or not getattr(self.proc.pid, 'stdout', None):
            return
        try:
            while not self._stop.is_set():
                raw = self.proc.pid.stdout.readline()
                if not raw:
                    if self.proc.poll() is not None:
                        break
                    continue
                line = (raw.decode('utf-8', errors='replace')
                        if isinstance(raw, bytes) else raw).rstrip('\r\n')
                self._parse_line(line)
        except Exception:
            pass

    def _parse_line(self, line):
        """Parse a single cowpatty stdout line."""
        # Progress: "key no. 1000: candidate"
        m = re.match(r'key no\.\s+(\d+):', line)
        if m:
            count = int(m.group(1))
            elapsed = time.monotonic() - self._start_time
            self._key_count = count
            with self._status_lock:
                if self._total_keys > 0:
                    self._status['progress'] = min(count / self._total_keys, 1.0)
                if elapsed > 0:
                    kps = count / elapsed
                    if kps >= 1_000_000:
                        self._status['speed'] = f'{kps / 1_000_000:.1f} Mk/s'
                    elif kps >= 1_000:
                        self._status['speed'] = f'{kps / 1_000:.1f} kk/s'
                    else:
                        self._status['speed'] = f'{kps:.0f} k/s'
                    if self._total_keys > count and kps > 0:
                        remaining = (self._total_keys - count) / kps
                        self._status['eta'] = self._fmt_duration(remaining)
            return

        # Cracked: The PSK is "password"
        if 'The PSK is "' in line:
            self._result_key = line.split('"', 1)[1][:-1]

    @staticmethod
    def _fmt_duration(seconds):
        if seconds >= 3600:
            return f'{seconds / 3600:.1f}h'
        if seconds >= 60:
            return f'{seconds / 60:.1f}m'
        return f'{int(seconds)}s'

    def poll_status(self):
        """Return a snapshot of the latest parsed status."""
        with self._status_lock:
            return dict(self._status)

    def is_finished(self):
        """Return True if cowpatty has exited."""
        if not self.proc:
            return True
        return self.proc.poll() is not None

    def get_result(self):
        """Return the cracked key, or None.  Waits for the reader to drain."""
        if self._reader and self._reader.is_alive():
            self._stop.set()
            self._reader.join(timeout=2.0)
        return self._result_key

    def interrupt(self):
        """Stop the reader thread and terminate cowpatty."""
        self._stop.set()
        if self.proc:
            self.proc.interrupt()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.interrupt()


class Cowpatty(Dependency):
    """ Wrapper for Cowpatty program. """
    dependency_required = False
    dependency_name = 'cowpatty'
    dependency_url = 'https://tools.kali.org/wireless-attacks/cowpatty'

    @staticmethod
    def crack_handshake(handshake, show_command=False, wordlist=None):
        wordlist = wordlist or Configuration.wordlist

        with CowpattyCracker(handshake.capfile, handshake.essid, wordlist) as cracker:
            cracker.start(show_command=show_command)

            while not cracker.is_finished():
                status = cracker.poll_status()
                pct = int(status['progress'] * 100)
                Color.p(f'\r{{+}} {{C}}Cowpatty{{W}}: {{G}}{pct}%{{W}} '
                        f'@ {{C}}{status["speed"]}{{W}} '
                        f'ETA: {{C}}{status["eta"]}{{W}}   ')
                time.sleep(2)

            Color.pl('')  # newline after the inline progress
            return cracker.get_result()
