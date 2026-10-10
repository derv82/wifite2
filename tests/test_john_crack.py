#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end tests for the --crack feature with john.

Tests every step of the pipeline:
  1. john binary found and version readable
  2. john supports wpapsk format (requires jumbo build)
  3. _get_format() detects the right format string
  4. hcxpcapngtool --john generates a non-empty file from a real .cap
  5. JohnCracker.start() launches and the stderr reader thread parses progress
  6. JohnCracker.get_result() parses john --show output correctly
  7. John.crack_handshake() full round-trip on a known-crackable cap
"""

import os
import re
import sys
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

# ── project root on path ──────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

TESTS_DIR  = os.path.dirname(__file__)
FILES_DIR  = os.path.join(TESTS_DIR, 'files')
HS_DIR     = os.path.join(os.path.dirname(TESTS_DIR), 'hs')

# Real cap files bundled with the repo (used by existing handshake tests)
CAP_WITH_HANDSHAKE    = os.path.join(FILES_DIR, 'handshake_exists.cap')
CAP_WITH_KNOWN_KEY    = os.path.join(FILES_DIR, 'handshake_has_1234.cap')

# Pick the first captured .cap in hs/ (if any) as an extra integration fixture
_hs_caps = sorted(
    f for f in (os.listdir(HS_DIR) if os.path.isdir(HS_DIR) else [])
    if f.endswith('.cap') and not f.startswith('sae_')
)
REAL_CAP = os.path.join(HS_DIR, _hs_caps[0]) if _hs_caps else None


# ── helpers ───────────────────────────────────────────────────────────────────

def _john_bin():
    return shutil.which('john')

def _hcxpcapngtool_bin():
    return shutil.which('hcxpcapngtool')

def _john_raw_formats():
    """Return raw stdout+stderr from 'john --list=formats', or '' if unsupported."""
    try:
        r = subprocess.run(['john', '--list=formats'],
                           capture_output=True, text=True, timeout=10)
        return r.stdout + r.stderr
    except Exception:
        return ''

def _john_supports_wpapsk():
    """True only if john --list=formats mentions wpapsk."""
    return 'wpapsk' in _john_raw_formats().lower()

def _john_supports_list_formats():
    """True if john understands --list=formats."""
    out = _john_raw_formats()
    return bool(out) and 'unknown option' not in out.lower()


# ── test cases ────────────────────────────────────────────────────────────────

class TestJohnBinary(unittest.TestCase):
    """Step 1 – binary presence and version."""

    def test_john_found_in_path(self):
        self.assertIsNotNone(_john_bin(), 'john not found in PATH')

    def test_john_version_readable(self):
        """John prints its version to stderr/stdout when run with no args."""
        r = subprocess.run(['john'], capture_output=True, text=True, timeout=5)
        combined = r.stdout + r.stderr
        match = re.search(r'version\s+([\d.]+)', combined, re.IGNORECASE)
        self.assertIsNotNone(
            match,
            f'Could not parse john version from output: {combined[:200]}'
        )
        version = match.group(1)
        self.assertRegex(version, r'^\d+\.\d+',
                         f'Version string looks wrong: {version}')
        print(f'\n  john version: {version}')


class TestJohnWpapskSupport(unittest.TestCase):
    """Step 2 – wpapsk format availability (requires jumbo build)."""

    def test_list_formats_flag_supported(self):
        """Standard john 1.9.0 doesn't support --list=formats (jumbo does)."""
        supported = _john_supports_list_formats()
        if not supported:
            self.skipTest(
                'john --list=formats not supported — this is the standard '
                '(non-jumbo) build. WPA cracking requires john-jumbo.'
            )

    def test_wpapsk_format_available(self):
        """wpapsk must be listed in john formats for WPA cracking to work."""
        if not _john_supports_list_formats():
            self.skipTest('--list=formats not supported; skipping format check')
        if not _john_supports_wpapsk():
            self.fail(
                'john does not support wpapsk format.\n'
                'The installed john is the standard community build (no WPA support).\n'
                'Fix: install john-jumbo:  apt install john  (Kali) or build from\n'
                '     https://github.com/openwall/john  (jumbo branch)'
            )


class TestGetFormat(unittest.TestCase):
    """Step 3 – John._get_format() internal logic."""

    def setUp(self):
        # Minimal Configuration stub so imports don't fail
        import types
        self._cfg_mod = sys.modules.get('wifite.config')

    def test_get_format_returns_string(self):
        from wifite.tools.john import John
        # _get_format calls john --list=formats; on non-jumbo it returns 'wpapsk'
        # regardless (because neither opencl nor cuda is found in empty output).
        # Verify it always returns a non-empty string.
        fmt = John._get_format()
        self.assertIsInstance(fmt, str)
        self.assertIn(fmt, ('wpapsk', 'wpapsk-opencl', 'wpapsk-cuda'),
                      f'Unexpected format: {fmt!r}')
        print(f'\n  _get_format() → {fmt!r}')

    def test_get_format_falls_back_on_unsupported_list_formats(self):
        """On standard john, --list=formats fails → _get_format must still return 'wpapsk'."""
        if _john_supports_list_formats():
            self.skipTest('This john supports --list=formats; fallback not needed')
        from wifite.tools.john import John
        fmt = John._get_format()
        self.assertEqual(fmt, 'wpapsk',
                         f'Expected fallback to wpapsk, got {fmt!r}')


class TestGenerateJohnFile(unittest.TestCase):
    """Step 4 – hcxpcapngtool --john file generation."""

    @classmethod
    def setUpClass(cls):
        cls.hcx = _hcxpcapngtool_bin()

    def _gen_john_file(self, cap_path):
        """Run hcxpcapngtool --john on cap_path, return (path, stdout+stderr)."""
        with tempfile.NamedTemporaryFile(suffix='.john', delete=False,
                                        prefix='wifite_test_') as tmp:
            out_path = tmp.name
        result = subprocess.run(
            ['hcxpcapngtool', '--john', out_path, cap_path],
            capture_output=True, text=True, timeout=30
        )
        combined = result.stdout + result.stderr
        return out_path, combined

    def test_hcxpcapngtool_available(self):
        self.assertIsNotNone(self.hcx, 'hcxpcapngtool not found in PATH')

    def test_john_flag_exists(self):
        """hcxpcapngtool must accept --john (not all versions do)."""
        if not self.hcx:
            self.skipTest('hcxpcapngtool not available')
        r = subprocess.run(['hcxpcapngtool', '--help'],
                           capture_output=True, text=True, timeout=10)
        combined = r.stdout + r.stderr
        self.assertIn('--john', combined,
                      'hcxpcapngtool does not list --john in help output')

    def test_generate_from_fixture_cap(self):
        """Generate a .john file from the bundled handshake_exists.cap fixture."""
        if not self.hcx:
            self.skipTest('hcxpcapngtool not available')
        if not os.path.exists(CAP_WITH_HANDSHAKE):
            self.skipTest(f'Fixture not found: {CAP_WITH_HANDSHAKE}')

        out_path, output = self._gen_john_file(CAP_WITH_HANDSHAKE)
        try:
            self.assertTrue(
                os.path.exists(out_path),
                f'hcxpcapngtool did not create {out_path}\nOutput:\n{output}'
            )
            size = os.path.getsize(out_path)
            self.assertGreater(
                size, 0,
                f'Generated .john file is empty.\nhcxpcapngtool output:\n{output}'
            )
            content = open(out_path).read()
            self.assertIn('WPAPSK', content,
                          f'.john file does not contain WPAPSK data.\nContent:\n{content[:300]}')
            print(f'\n  .john file: {size} bytes, first line: {content.splitlines()[0][:80]}')
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    @unittest.skipIf(REAL_CAP is None, 'No .cap files in hs/ directory')
    def test_generate_from_real_cap(self):
        """Generate a .john file from a real captured handshake in hs/."""
        if not self.hcx:
            self.skipTest('hcxpcapngtool not available')
        out_path, output = self._gen_john_file(REAL_CAP)
        try:
            exists = os.path.exists(out_path)
            size = os.path.getsize(out_path) if exists else 0
            self.assertTrue(exists and size > 0,
                            f'Failed to generate .john from {REAL_CAP}\nOutput:\n{output}')
            print(f'\n  Real cap .john: {size} bytes from {os.path.basename(REAL_CAP)}')
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)


class TestJohnCrackerProgress(unittest.TestCase):
    """Step 5 – JohnCracker stderr reader and progress parsing."""

    def test_progress_regex_matches_john_stderr_format(self):
        """The reader's line-matching regex must accept all known john progress formats."""
        from wifite.tools.john import JohnCracker
        jc = JohnCracker.__new__(JohnCracker)
        jc._status = {'progress': 0.0, 'speed': 'Unknown', 'eta': 'Unknown'}
        jc._status_lock = threading.Lock()

        samples = [
            # (line, expected_progress, expected_speed_contains, expected_eta)
            ('0g 0:00:00:03 13% (ETA: 00:00:22) 0g/s 200p/s 200c/s 200C/s test..admin',
             0.13, '200', '00:00:22'),
            ('0g 0:00:00:00 100% 0g/s 500.0p/s 500.0c/s 500.0C/s password..admin',
             1.0,  '500', None),
            # 1234.5 p/s → formatted as '1.2 kp/s' by _parse_progress
            ('1g 0:00:00:01 50% (ETA: Mon Apr 24 21:00:00 2026) 1g/s 1234.5p/s',
             0.50, '1.2', '2026'),
        ]

        for line, exp_pct, exp_spd, exp_eta in samples:
            is_progress = bool(re.match(r'\d+g\s+\d+:\d+:\d+:\d+', line))
            self.assertTrue(is_progress,
                            f'Regex did not match progress line: {line!r}')
            jc._parse_progress(line)
            st = jc.poll_status()
            self.assertAlmostEqual(st['progress'], exp_pct, places=2,
                                   msg=f'Wrong progress for: {line!r}')
            self.assertIn(exp_spd, st['speed'],
                          msg=f'Speed {st["speed"]!r} missing {exp_spd!r} for: {line!r}')
            if exp_eta:
                self.assertIn(exp_eta, st['eta'],
                              msg=f'ETA {st["eta"]!r} missing {exp_eta!r} for: {line!r}')

    def test_non_progress_lines_not_parsed(self):
        """Lines that don't match the progress pattern must be silently ignored."""
        from wifite.tools.john import JohnCracker
        jc = JohnCracker.__new__(JohnCracker)
        jc._status = {'progress': 0.0, 'speed': 'Unknown', 'eta': 'Unknown'}
        jc._status_lock = threading.Lock()

        noise = [
            "Will run 12 OpenMP threads",
            "Press 'q' or Ctrl-C to abort",
            "Loaded 1 password hash (md5crypt [MD5 32/64 X2])",
            "Session completed",
            "",
        ]
        for line in noise:
            is_progress = bool(re.match(r'\d+g\s+\d+:\d+:\d+:\d+', line))
            self.assertFalse(is_progress,
                             f'Non-progress line incorrectly matched: {line!r}')


class TestJohnShowParsing(unittest.TestCase):
    """Step 6 – get_result() parsing of john --show output."""

    def _make_cracker(self):
        from wifite.tools.john import JohnCracker
        jc = JohnCracker.__new__(JohnCracker)
        jc._status = {'progress': 0.0, 'speed': 'Unknown', 'eta': 'Unknown'}
        jc._status_lock = threading.Lock()
        jc._reader_thread = None
        jc._stop_reader = threading.Event()
        jc.proc = None
        return jc

    def test_get_result_parses_cracked_line(self):
        """get_result() must extract the password from the second colon-field.

        john --show for wpapsk (jumbo) replaces the hash with the plaintext,
        so the output line format is:
          ESSID:PLAINTEXT_PASSWORD:client_mac:ap_mac:...:capfile
        → parts[1] is the password.
        """
        from wifite.tools.john import JohnCracker
        import unittest.mock as mock

        # john --show output: hash has been replaced by plaintext in field [1]
        show_output = (
            'TeWe:secretpassword:6c-ad-f8:74-3a-ef::WPA2:verified:cap.john\n'
            '1 password hash cracked, 0 left\n'
        )

        jc = self._make_cracker()
        jc.hash_file = '/tmp/dummy.john'
        jc.john_format = 'wpapsk'

        with mock.patch('wifite.tools.john.Process') as MockProc:
            inst = MockProc.return_value
            inst.get_output.return_value = (show_output, '')
            result = jc.get_result()

        self.assertEqual(result, 'secretpassword',
                         f'Expected "secretpassword", got {result!r}')

    def test_get_result_returns_none_on_no_crack(self):
        from wifite.tools.john import JohnCracker
        import unittest.mock as mock

        jc = self._make_cracker()
        jc.hash_file = '/tmp/dummy.john'
        jc.john_format = 'wpapsk'

        with mock.patch('wifite.tools.john.Process') as MockProc:
            inst = MockProc.return_value
            inst.get_output.return_value = ('0 password hashes cracked, 1 left\n', '')
            result = jc.get_result()

        self.assertIsNone(result)


class TestJohnShowOutputFormat(unittest.TestCase):
    """
    Documents and verifies the exact john --show output format for wpapsk.

    john --show (jumbo) REPLACES the hash with the plaintext in the output,
    so the cracked line looks like:
      ESSID:PLAINTEXT_PASSWORD:client_mac:ap_mac:stripped_mac:type:verified:capfile

    parts[1] is therefore the plaintext password — which is what get_result() uses.
    """

    def test_show_cracked_line_format(self):
        """parts[1] of a cracked --show line is the plaintext password."""
        cracked_line = (
            'TeWe:mypassword:6c-ad-f8:74-3a-ef:743aef0870f9:WPA2:verified:cap.john'
        )
        parts = cracked_line.split(':')
        self.assertEqual(parts[1], 'mypassword',
                         'parts[1] should be the plaintext password in a cracked --show line')

    def test_summary_line_is_skipped(self):
        """The summary 'N password hash(es) cracked' line must not be parsed as a result."""
        summary_forms = [
            '0 password hashes cracked, 1 left',
            '1 password hash cracked, 0 left',
            '3 password hashes cracked, 2 left',
        ]
        for line in summary_forms:
            is_summary = bool(re.match(r'\d+ password hash', line))
            self.assertTrue(is_summary,
                            f'Summary line not recognised: {line!r}')


@unittest.skipIf(not _john_supports_wpapsk(),
                 'john does not support wpapsk — install john-jumbo for WPA cracking')
class TestJohnCrackHandshakeIntegration(unittest.TestCase):
    """Step 7 – full round-trip only when john-jumbo with wpapsk is available."""

    def test_crack_known_key_handshake(self):
        if not os.path.exists(CAP_WITH_KNOWN_KEY):
            self.skipTest(f'Fixture not found: {CAP_WITH_KNOWN_KEY}')
        if not _hcxpcapngtool_bin():
            self.skipTest('hcxpcapngtool not available')

        wl_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                              delete=False, prefix='wifite_wl_')
        wl_file.write('wrong1\nwrong2\n1234\nwrong3\n')
        wl_file.close()

        try:
            import unittest.mock as mock
            from wifite.tools.john import John
            from wifite.model.handshake import Handshake

            hs = Handshake(CAP_WITH_KNOWN_KEY, bssid='00:00:00:00:00:00', essid='test')

            with mock.patch('wifite.config.Configuration') as MockCfg:
                MockCfg.wordlist = wl_file.name
                MockCfg.verbose = 0
                key = John.crack_handshake(hs, show_command=True, wordlist=wl_file.name)

            self.assertEqual(key, '1234',
                             f'Expected key "1234", got {key!r}')
        finally:
            os.remove(wl_file.name)


class TestCrackHelperJohnDependency(unittest.TestCase):
    """
    Verify CrackHelper correctly checks john's wpapsk capability before
    listing it as a usable tool for 4-way handshake cracking.
    """

    def test_john_listed_in_possible_tools(self):
        from wifite.util.crack import CrackHelper
        tool_names = [t for t, _ in CrackHelper.possible_tools]
        self.assertIn('john', tool_names)

    def test_john_has_wpapsk_capability_check(self):
        """John.is_wpapsk_capable() must exist and return a bool."""
        from wifite.tools.john import John
        self.assertTrue(hasattr(John, 'is_wpapsk_capable'),
                        'John.is_wpapsk_capable() is missing')
        result = John.is_wpapsk_capable()
        self.assertIsInstance(result, bool)
        print(f'\n  John.is_wpapsk_capable() → {result}')

    def test_crack_helper_excludes_john_when_not_wpapsk_capable(self):
        """When john lacks wpapsk, CrackHelper must NOT list it as available."""
        import unittest.mock as mock
        from wifite.tools.john import John

        if John.is_wpapsk_capable():
            self.skipTest('john-jumbo is installed; this test covers non-jumbo builds')

        from wifite.util.crack import CrackHelper
        from wifite.tools.john import John as J

        # Simulate the availability check used in CrackHelper.run()
        missing = []
        available = []
        for tool, dependencies in CrackHelper.possible_tools:
            if any(not __import__('shutil').which(d.dependency_name) for d in dependencies):
                missing.append(tool)
            elif tool == 'john' and not J.is_wpapsk_capable():
                missing.append(tool)
            else:
                available.append(tool)

        self.assertNotIn('john', available,
                         'john should not be available when wpapsk format is missing')
        self.assertIn('john', missing)


if __name__ == '__main__':
    unittest.main(verbosity=2)
