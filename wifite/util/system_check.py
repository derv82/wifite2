#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive system check for wifite2.

Performs a full readiness assessment including:
- Tool dependency verification with version checks
- Wireless interface capability matrix
- Driver compatibility warnings
- Monitor mode smoke test
- Kernel/OS environment checks
- Attack readiness summary

Usage:
    wifite --syscheck
    wifite --syscheck --verbose   # Include smoke tests and detailed info
"""

import os
import re
import subprocess
import shutil
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum


class CheckStatus(Enum):
    """Status for individual check results."""
    PASS = 'PASS'
    WARN = 'WARN'
    FAIL = 'FAIL'
    SKIP = 'SKIP'
    INFO = 'INFO'


@dataclass
class CheckResult:
    """Result of a single check."""
    name: str
    status: CheckStatus
    message: str
    details: Optional[str] = None
    fix_hint: Optional[str] = None


@dataclass
class InterfaceCheckResult:
    """Result of interface capability checks."""
    name: str
    phy: str = 'unknown'
    driver: str = 'unknown'
    chipset: str = 'unknown'
    mac: str = 'unknown'
    mode: str = 'unknown'
    is_up: bool = False
    supports_monitor: bool = False
    supports_ap: bool = False
    supports_injection: bool = False
    monitor_tested: Optional[bool] = None  # None = not tested
    bands_24ghz: bool = False
    bands_5ghz: bool = False
    channels_24: List[int] = field(default_factory=list)
    channels_5: List[int] = field(default_factory=list)


@dataclass
class ToolCheckResult:
    """Result of a tool dependency check."""
    name: str
    found: bool
    path: Optional[str] = None
    version: Optional[str] = None
    min_version: Optional[str] = None
    version_ok: bool = True
    required: bool = False
    category: str = 'misc'
    native_alt: Optional[str] = None  # Description of native alternative


class SystemCheck:
    """
    Performs comprehensive system readiness checks for wifite2.

    This class orchestrates all checks and produces a structured report
    that can be rendered to the terminal.
    """

    def __init__(self, verbose: int = 0, run_smoke_test: bool = False):
        """
        Args:
            verbose: Verbosity level (0=normal, 1=detailed, 2+=debug)
            run_smoke_test: Whether to run monitor mode smoke test
        """
        self.verbose = verbose
        self.run_smoke_test = run_smoke_test
        self.tool_results: List[ToolCheckResult] = []
        self.interface_results: List[InterfaceCheckResult] = []
        self.env_results: List[CheckResult] = []
        self.attack_readiness: Dict[str, CheckStatus] = {}

    # ================================================================
    # Environment Checks
    # ================================================================

    def check_environment(self) -> List[CheckResult]:
        """Check OS, kernel, and runtime environment."""
        results = []

        # Root check
        if os.getuid() == 0:
            results.append(CheckResult('Root privileges', CheckStatus.PASS, 'Running as root'))
        else:
            results.append(CheckResult('Root privileges', CheckStatus.FAIL,
                                       'Not running as root',
                                       fix_hint='Re-run with: sudo wifite --syscheck'))

        # OS check
        if os.name == 'posix':
            results.append(CheckResult('Operating system', CheckStatus.PASS, 'POSIX-compatible'))
        else:
            results.append(CheckResult('Operating system', CheckStatus.FAIL,
                                       f'Unsupported OS: {os.name}',
                                       fix_hint='Wifite requires a Linux/POSIX system'))

        # Kernel version
        try:
            uname = os.uname()
            kernel = uname.release
            results.append(CheckResult('Kernel', CheckStatus.INFO, f'{uname.sysname} {kernel}'))

            # Check for wireless extensions support
            if os.path.exists('/proc/net/wireless'):
                results.append(CheckResult('Wireless extensions', CheckStatus.PASS,
                                           '/proc/net/wireless present'))
            else:
                results.append(CheckResult('Wireless extensions', CheckStatus.WARN,
                                           '/proc/net/wireless not found',
                                           details='Wireless extensions may not be loaded'))
        except Exception as e:
            results.append(CheckResult('Kernel', CheckStatus.WARN, f'Could not detect: {e}'))

        # Check rfkill
        rfkill = shutil.which('rfkill')
        if rfkill:
            try:
                out = subprocess.run(['rfkill', 'list', 'wifi'], capture_output=True,
                                     text=True, timeout=5)
                if 'Soft blocked: yes' in out.stdout or 'Hard blocked: yes' in out.stdout:
                    results.append(CheckResult('RF Kill', CheckStatus.FAIL,
                                               'Wireless is blocked by rfkill',
                                               details=out.stdout.strip(),
                                               fix_hint='Run: rfkill unblock wifi'))
                else:
                    results.append(CheckResult('RF Kill', CheckStatus.PASS,
                                               'Wireless is not blocked'))
            except Exception:
                results.append(CheckResult('RF Kill', CheckStatus.WARN,
                                           'Could not check rfkill status'))
        else:
            results.append(CheckResult('RF Kill', CheckStatus.INFO, 'rfkill not installed'))

        # Check for conflicting processes
        try:
            conflicts = []
            for proc_name in ['NetworkManager', 'wpa_supplicant', 'dhclient', 'avahi-daemon']:
                try:
                    result = subprocess.run(['pgrep', '-x', proc_name], capture_output=True,
                                            text=True, timeout=3)
                    if result.returncode == 0:
                        pids = result.stdout.strip().split('\n')
                        conflicts.append(f'{proc_name} (PID: {", ".join(pids)})')
                except Exception:
                    pass

            if conflicts:
                results.append(CheckResult('Conflicting processes', CheckStatus.WARN,
                                           f'{len(conflicts)} found',
                                           details=', '.join(conflicts),
                                           fix_hint='Use --kill or run: airmon-ng check kill'))
            else:
                results.append(CheckResult('Conflicting processes', CheckStatus.PASS,
                                           'None detected'))
        except Exception:
            results.append(CheckResult('Conflicting processes', CheckStatus.SKIP,
                                       'Could not check'))

        # Check temp directory writability
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(prefix='wifite_check_', delete=True):
                pass
            results.append(CheckResult('Temp directory', CheckStatus.PASS,
                                       f'{tempfile.gettempdir()} writable'))
        except Exception as e:
            results.append(CheckResult('Temp directory', CheckStatus.FAIL,
                                       f'Cannot write to temp: {e}'))

        # Check /sys/class/net exists
        if os.path.isdir('/sys/class/net'):
            results.append(CheckResult('sysfs network', CheckStatus.PASS,
                                       '/sys/class/net accessible'))
        else:
            results.append(CheckResult('sysfs network', CheckStatus.WARN,
                                       '/sys/class/net not found',
                                       details='Native interface management may not work'))

        self.env_results = results
        return results

    # ================================================================
    # Tool / Dependency Checks
    # ================================================================

    def check_tools(self) -> List[ToolCheckResult]:
        """Check all tool dependencies with versions."""
        from ..tools.dependency import Dependency

        # Define all tools to check with metadata
        tools_spec = [
            # (name, required, category, min_version, url)
            ('aircrack-ng', True, 'core', '1.6', 'https://www.aircrack-ng.org'),
            ('airmon-ng', True, 'core', None, 'https://www.aircrack-ng.org'),
            ('airodump-ng', True, 'core', None, 'https://www.aircrack-ng.org'),
            ('aireplay-ng', True, 'core', None, 'https://www.aircrack-ng.org'),
            ('iw', True, 'core', None, 'apt install iw'),
            ('ip', True, 'core', None, 'apt install iproute2'),
            ('reaver', False, 'wps', '1.6.5', 'https://github.com/t6x/reaver-wps-fork-t6x'),
            ('bully', False, 'wps', '1.4', 'https://github.com/aanarchyy/bully'),
            ('wash', False, 'wps', None, 'https://github.com/t6x/reaver-wps-fork-t6x'),
            ('tshark', False, 'inspection', '3.0.0', 'apt install tshark'),
            ('hashcat', False, 'cracking', '6.0.0', 'https://hashcat.net/hashcat/'),
            ('john', False, 'cracking', '1.9.0', 'apt install john'),
            ('hcxdumptool', False, 'wpa3', '6.2.0', 'apt install hcxdumptool'),
            ('hcxpcapngtool', False, 'wpa3', '6.2.0', 'apt install hcxtools'),
            ('cowpatty', False, 'cracking', None, 'apt install cowpatty'),
            ('macchanger', False, 'misc', None, 'apt install macchanger'),
            ('hostapd', False, 'eviltwin', '2.9', 'apt install hostapd'),
            ('dnsmasq', False, 'eviltwin', '2.80', 'apt install dnsmasq'),
            ('wpa_supplicant', False, 'eviltwin', '2.9', 'apt install wpasupplicant'),
            ('wlancap2wpasec', False, 'wpasec', None, 'apt install hcxtools'),
        ]

        results = []
        for name, required, category, min_ver, url in tools_spec:
            result = ToolCheckResult(
                name=name,
                found=False,
                required=required,
                category=category,
                min_version=min_ver,
            )

            # Check if binary exists
            path = shutil.which(name)
            if path:
                result.found = True
                result.path = path

                # Get version
                result.version = self._get_tool_version(name)

                # Check minimum version
                if min_ver and result.version:
                    result.version_ok = Dependency._compare_versions(
                        result.version, min_ver) >= 0
                elif min_ver and not result.version:
                    result.version_ok = True  # Can't determine, assume ok
            else:
                # Check for native alternative
                if name in Dependency.NATIVE_ALTERNATIVES:
                    desc, check_func_name = Dependency.NATIVE_ALTERNATIVES[name]
                    check_func = getattr(Dependency, check_func_name, None)
                    if check_func and check_func():
                        result.native_alt = desc

            results.append(result)

        self.tool_results = results
        return results

    def _get_tool_version(self, name: str) -> Optional[str]:
        """Try to get version string for a tool."""
        if name == 'airmon-ng':
            if shutil.which(name):
                return None
            return None

        aircrack_family = ['aircrack-ng', 'airodump-ng', 'aireplay-ng']
        if name in aircrack_family:
            try:
                process = subprocess.run(
                    [name], capture_output=True, text=True, timeout=5
                )
                output = (process.stdout + "\n" + process.stderr).splitlines()[:5]
                content = " ".join(output)
                match = re.search(r'(\d+\.\d+)', content)
                if match:
                    return match.group(1)
            except Exception:
                pass

        if name == 'john':
            try:
                process = subprocess.run(
                    ['john'], capture_output=True, text=True, timeout=5
                )
                output = (process.stdout + "\n" + process.stderr).splitlines()[:3]
                content = " ".join(output)
                # "John the Ripper 1.9.0-jumbo-1+bleeding-..." or "John the Ripper 1.9.0"
                match = re.search(
                    r'John the Ripper\s+(\d+\.\d+(?:\.\d+)?(?:-jumbo-\d+)?)',
                    content,
                )
                if match:
                    return match.group(1)
            except Exception:
                pass
            return None

        for flag in ['--version', '-v', '-V', 'version']:
            try:
                out = subprocess.run(
                    [name, flag], capture_output=True, text=True, timeout=5
                )
                combined = (out.stdout + ' ' + out.stderr).strip()
                if combined:
                    match = re.search(r'(\d+\.\d+[\.\d]*\w*)', combined)
                    if match:
                        return match.group(1)
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError, PermissionError):
                continue
        return None

    # ================================================================
    # Interface Checks
    # ================================================================

    def check_interfaces(self) -> List[InterfaceCheckResult]:
        """Check all wireless interfaces and their capabilities."""
        results = []

        # Enumerate wireless interfaces via sysfs (works without iw)
        wireless_ifaces = []
        try:
            for name in sorted(os.listdir('/sys/class/net')):
                if os.path.isdir(f'/sys/class/net/{name}/wireless'):
                    wireless_ifaces.append(name)
        except OSError:
            pass

        # Fallback to iw if sysfs found nothing
        if not wireless_ifaces:
            try:
                from ..tools.iw import Iw
                wireless_ifaces = Iw.get_interfaces()
            except Exception:
                pass

        for iface in wireless_ifaces:
            result = InterfaceCheckResult(name=iface)

            # PHY
            try:
                out = subprocess.run(['iw', 'dev', iface, 'info'],
                                     capture_output=True, text=True, timeout=5)
                if m := re.search(r'wiphy\s+(\d+)', out.stdout):
                    result.phy = f'phy{m.group(1)}'
            except Exception:
                pass

            # Driver (sysfs)
            try:
                driver_link = os.readlink(f'/sys/class/net/{iface}/device/driver')
                result.driver = os.path.basename(driver_link)
            except (OSError, IOError):
                pass

            # Chipset (from airmon or driver map)
            try:
                from ..tools.airmon import Airmon
                from .interface_manager import InterfaceManager
                info = Airmon.get_iface_info(iface)
                if info and info.chipset:
                    result.chipset = info.chipset
                elif result.driver in InterfaceManager.DRIVER_CHIPSET_MAP:
                    result.chipset = InterfaceManager.DRIVER_CHIPSET_MAP[result.driver]
            except Exception:
                pass

            # MAC address
            try:
                with open(f'/sys/class/net/{iface}/address', 'r') as f:
                    result.mac = f.read().strip().upper()
            except (IOError, OSError):
                pass

            # Current mode
            try:
                out = subprocess.run(['iw', 'dev', iface, 'info'],
                                     capture_output=True, text=True, timeout=5)
                if 'type monitor' in out.stdout:
                    result.mode = 'monitor'
                elif 'type managed' in out.stdout:
                    result.mode = 'managed'
                elif 'type AP' in out.stdout or 'type master' in out.stdout:
                    result.mode = 'AP'
                elif m := re.search(r'type\s+(\w+)', out.stdout):
                    result.mode = m.group(1).lower()
            except Exception:
                pass

            # Interface up/down
            try:
                with open(f'/sys/class/net/{iface}/operstate', 'r') as f:
                    result.is_up = f.read().strip().lower() in ('up', 'unknown')
            except (IOError, OSError):
                pass

            # Supported modes and bands from iw phy info
            if result.phy != 'unknown':
                self._parse_phy_info(result)

            # Monitor mode smoke test (optional)
            if self.run_smoke_test and result.supports_monitor and os.getuid() == 0:
                result.monitor_tested = self._smoke_test_monitor(iface)

            results.append(result)

        self.interface_results = results
        return results

    def _parse_phy_info(self, result: InterfaceCheckResult):
        """Parse iw phy info for supported modes, bands, channels."""
        try:
            out = subprocess.run(['iw', 'phy', result.phy, 'info'],
                                 capture_output=True, text=True, timeout=10)
            output = out.stdout

            # Supported modes
            in_modes = False
            for line in output.split('\n'):
                if 'Supported interface modes:' in line:
                    in_modes = True
                    continue
                if in_modes:
                    stripped = line.strip()
                    if not stripped or (not stripped.startswith('*') and not stripped.startswith(' ')):
                        in_modes = False
                        continue
                    if '* monitor' in line.lower():
                        result.supports_monitor = True
                    if '* AP' in line or '* master' in line:
                        result.supports_ap = True

            # Frequency bands and channels
            for m in re.finditer(r'\*\s+(\d+)\s+MHz\s+\[(\d+)\]', output):
                freq = int(m.group(1))
                chan = int(m.group(2))
                if 2400 <= freq <= 2500:
                    result.bands_24ghz = True
                    if chan not in result.channels_24:
                        result.channels_24.append(chan)
                elif 5000 <= freq <= 6000:
                    result.bands_5ghz = True
                    if chan not in result.channels_5:
                        result.channels_5.append(chan)

            result.channels_24.sort()
            result.channels_5.sort()

            # Injection support heuristic (driver-based)
            from .interface_manager import InterfaceManager
            if result.driver in InterfaceManager.INJECTION_CAPABLE_DRIVERS:
                result.supports_injection = True
            elif result.driver in InterfaceManager.NO_INJECTION_DRIVERS:
                result.supports_injection = False
            else:
                # Unknown driver — assume supported for wireless adapters
                result.supports_injection = True

        except Exception:
            pass

    def _smoke_test_monitor(self, iface: str) -> bool:
        """
        Perform a non-destructive monitor mode smoke test.

        Brings iface down, sets monitor mode, checks, then restores.
        Only runs if the interface is currently in managed mode and up.
        """
        try:
            # Only test if currently in managed mode
            out = subprocess.run(['iw', 'dev', iface, 'info'],
                                 capture_output=True, text=True, timeout=5)
            if 'type managed' not in out.stdout:
                return True  # Already in monitor or other mode, skip test

            # Down → monitor → check → managed → up
            subprocess.run(['ip', 'link', 'set', iface, 'down'],
                           capture_output=True, timeout=5)
            subprocess.run(['iw', 'dev', iface, 'set', 'type', 'monitor'],
                           capture_output=True, timeout=5)
            subprocess.run(['ip', 'link', 'set', iface, 'up'],
                           capture_output=True, timeout=5)

            import time
            time.sleep(0.3)

            # Verify
            check = subprocess.run(['iw', 'dev', iface, 'info'],
                                   capture_output=True, text=True, timeout=5)
            success = 'type monitor' in check.stdout

            # Restore
            subprocess.run(['ip', 'link', 'set', iface, 'down'],
                           capture_output=True, timeout=5)
            subprocess.run(['iw', 'dev', iface, 'set', 'type', 'managed'],
                           capture_output=True, timeout=5)
            subprocess.run(['ip', 'link', 'set', iface, 'up'],
                           capture_output=True, timeout=5)

            return success

        except Exception:
            # Try to restore on failure
            try:
                subprocess.run(['ip', 'link', 'set', iface, 'down'],
                               capture_output=True, timeout=3)
                subprocess.run(['iw', 'dev', iface, 'set', 'type', 'managed'],
                               capture_output=True, timeout=3)
                subprocess.run(['ip', 'link', 'set', iface, 'up'],
                               capture_output=True, timeout=3)
            except Exception:
                pass
            return False

    # ================================================================
    # Attack Readiness Assessment
    # ================================================================

    def assess_attack_readiness(self) -> Dict[str, CheckStatus]:
        """Determine which attack types are available based on checks."""
        readiness = {}

        has_monitor = any(r.supports_monitor for r in self.interface_results)
        has_ap = any(r.supports_ap for r in self.interface_results)
        has_injection = any(r.supports_injection for r in self.interface_results)
        has_interface = len(self.interface_results) > 0
        dual_iface = len(self.interface_results) >= 2

        def tool_ok(name):
            for t in self.tool_results:
                if t.name == name:
                    return t.found and t.version_ok
            return False

        def tool_found(name):
            for t in self.tool_results:
                if t.name == name:
                    return t.found or t.native_alt is not None
            return False

        # WPA handshake capture
        if has_interface and has_monitor and tool_ok('aircrack-ng'):
            readiness['WPA Handshake'] = CheckStatus.PASS
        elif has_interface and has_monitor:
            readiness['WPA Handshake'] = CheckStatus.WARN
        else:
            readiness['WPA Handshake'] = CheckStatus.FAIL

        # WPA cracking
        if tool_ok('aircrack-ng') or tool_ok('hashcat'):
            readiness['WPA Crack'] = CheckStatus.PASS
        else:
            readiness['WPA Crack'] = CheckStatus.FAIL

        # WEP
        if has_interface and has_monitor and has_injection and tool_ok('aircrack-ng'):
            readiness['WEP Attack'] = CheckStatus.PASS
        elif has_interface and has_monitor:
            readiness['WEP Attack'] = CheckStatus.WARN
        else:
            readiness['WEP Attack'] = CheckStatus.FAIL

        # WPS
        if has_interface and has_monitor and (tool_found('reaver') or tool_found('bully')):
            readiness['WPS Attack'] = CheckStatus.PASS
        elif has_interface and has_monitor:
            readiness['WPS Attack'] = CheckStatus.WARN
        else:
            readiness['WPS Attack'] = CheckStatus.FAIL

        # PMKID
        if has_interface and has_monitor and tool_ok('hcxdumptool'):
            readiness['PMKID Capture'] = CheckStatus.PASS
        elif has_interface and has_monitor:
            readiness['PMKID Capture'] = CheckStatus.WARN
        else:
            readiness['PMKID Capture'] = CheckStatus.FAIL

        # WPA3 / SAE
        if (has_interface and has_monitor and
                tool_ok('hcxdumptool') and tool_ok('hcxpcapngtool')):
            readiness['WPA3/SAE'] = CheckStatus.PASS
        elif has_interface and has_monitor:
            readiness['WPA3/SAE'] = CheckStatus.WARN
        else:
            readiness['WPA3/SAE'] = CheckStatus.FAIL

        # Evil Twin
        if (has_ap and has_monitor and dual_iface and
                tool_found('hostapd') and tool_found('dnsmasq')):
            readiness['Evil Twin'] = CheckStatus.PASS
        elif has_ap and tool_found('hostapd') and tool_found('dnsmasq'):
            readiness['Evil Twin'] = CheckStatus.WARN
        else:
            readiness['Evil Twin'] = CheckStatus.FAIL

        # Attack monitoring
        if has_interface and has_monitor and tool_found('tshark'):
            readiness['Attack Monitor'] = CheckStatus.PASS
        elif has_interface and has_monitor:
            readiness['Attack Monitor'] = CheckStatus.WARN
        else:
            readiness['Attack Monitor'] = CheckStatus.FAIL

        self.attack_readiness = readiness
        return readiness

    # ================================================================
    # Run all checks
    # ================================================================

    def run_all(self):
        """Run all checks in sequence."""
        self.check_environment()
        self.check_tools()
        self.check_interfaces()
        self.assess_attack_readiness()

    # ================================================================
    # Report Rendering
    # ================================================================

    def render_report(self):
        """Print the full check report to the terminal."""
        from ..util.color import Color

        Color.pl('\n{C}╔══════════════════════════════════════════════════════════════╗{W}')
        Color.pl('{C}║{W}           {G}Wifite2 System Readiness Check{W}                     {C}║{W}')
        Color.pl('{C}╚══════════════════════════════════════════════════════════════╝{W}')

        self._render_environment()
        self._render_tools()
        self._render_interfaces()
        self._render_attack_readiness()

        Color.pl('')

    def _render_environment(self):
        """Render environment check results."""
        from ..util.color import Color

        Color.pl('\n{C}─── Environment ──────────────────────────────────────────────{W}')
        for r in self.env_results:
            icon = self._status_icon(r.status)
            Color.pl(f'  {icon} {{W}}{r.name.ljust(25)} {r.message}{{W}}')
            if r.details and self.verbose > 0:
                Color.pl(f'      {{D}}{r.details}{{W}}')
            if r.fix_hint and r.status in (CheckStatus.FAIL, CheckStatus.WARN):
                Color.pl(f'      {{O}}Fix: {r.fix_hint}{{W}}')

    def _render_tools(self):
        """Render tool dependency check results."""
        from ..util.color import Color

        Color.pl('\n{C}─── Tool Dependencies ────────────────────────────────────────{W}')

        # Group by category
        categories = {}
        for t in self.tool_results:
            cat = t.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(t)

        cat_order = ['core', 'wps', 'cracking', 'inspection', 'wpa3',
                     'eviltwin', 'wpasec', 'misc']

        cat_labels = {
            'core': 'Core (required)',
            'wps': 'WPS Attacks',
            'cracking': 'Cracking',
            'inspection': 'Packet Inspection',
            'wpa3': 'WPA3/SAE',
            'eviltwin': 'Evil Twin',
            'wpasec': 'WPA-SEC Upload',
            'misc': 'Miscellaneous',
        }

        for cat in cat_order:
            if cat not in categories:
                continue
            Color.pl(f'\n  {{C}}{cat_labels.get(cat, cat)}{{W}}')

            for t in categories[cat]:
                if t.found:
                    ver_str = f' v{t.version}' if t.version else ''
                    if not t.version_ok:
                        icon = '{O}⚠{W}'
                        ver_note = f' {{O}}(need v{t.min_version}+){{W}}'
                    else:
                        icon = '{G}✓{W}'
                        ver_note = ''
                    Color.pl(f'    {icon} {{W}}{t.name.ljust(22)}{ver_str}{ver_note}{{W}}')
                    if t.name == 'john' and t.version and 'jumbo' not in t.version.lower():
                        Color.pl('        {O}⚠ Non-jumbo build — WPA cracking requires john-jumbo{W}')
                    if self.verbose > 0 and t.path:
                        Color.pl(f'        {{D}}{t.path}{{W}}')
                else:
                    if t.native_alt:
                        Color.pl(f'    {{G}}✓{{W}} {{W}}{t.name.ljust(22)}{{C}}native: {t.native_alt}{{W}}')
                    elif t.required:
                        Color.pl(f'    {{R}}✗{{W}} {{R}}{t.name.ljust(22)}MISSING (required){{W}}')
                    else:
                        Color.pl(f'    {{O}}─{{W}} {{D}}{t.name.ljust(22)}not installed{{W}}')

    def _render_interfaces(self):
        """Render interface capability matrix."""
        from ..util.color import Color

        Color.pl('\n{C}─── Wireless Interfaces ──────────────────────────────────────{W}')

        if not self.interface_results:
            Color.pl('  {R}✗ No wireless interfaces detected{W}')
            Color.pl('    {O}Connect a wireless adapter and try again{W}')
            return

        Color.pl(f'  Found {{G}}{len(self.interface_results)}{{W}} wireless interface(s):\n')

        for iface in self.interface_results:
            # Header line: name + driver + chipset
            driver_str = iface.driver if iface.driver != 'unknown' else '?'
            chipset_str = iface.chipset if iface.chipset != 'unknown' else ''
            Color.pl(f'  {{G}}{iface.name}{{W}}  ({iface.phy})  '
                     f'driver={{C}}{driver_str}{{W}}  {chipset_str}')

            # MAC (masked for privacy)
            if iface.mac and iface.mac != 'unknown':
                parts = iface.mac.split(':')
                if len(parts) == 6:
                    masked = ':'.join(parts[:3] + ['**', '**', '**'])
                else:
                    masked = iface.mac
                Color.pl(f'    MAC: {masked}   Mode: {{C}}{iface.mode}{{W}}   '
                         f'Up: {"{G}yes{W}" if iface.is_up else "{O}no{W}"}')

            # Capability matrix
            mon = '{G}✓{W}' if iface.supports_monitor else '{R}✗{W}'
            ap = '{G}✓{W}' if iface.supports_ap else '{D}─{W}'
            inj = '{G}✓{W}' if iface.supports_injection else '{O}?{W}'
            Color.pl(f'    Capabilities:  Monitor {mon}   AP {ap}   Injection {inj}')

            # Bands
            bands = []
            if iface.bands_24ghz:
                bands.append(f'2.4GHz ({len(iface.channels_24)} ch)')
            if iface.bands_5ghz:
                bands.append(f'5GHz ({len(iface.channels_5)} ch)')
            if bands:
                Color.pl(f'    Bands: {{C}}{", ".join(bands)}{{W}}')

            # Smoke test result
            if iface.monitor_tested is not None:
                if iface.monitor_tested:
                    Color.pl('    Monitor test: {G}PASS{W} (entered and exited monitor mode)')
                else:
                    Color.pl('    Monitor test: {R}FAIL{W} (could not enter monitor mode)')

            # Driver warnings
            if iface.driver in ('iwlwifi',):
                Color.pl('    {O}⚠ Intel driver — no packet injection support{W}')
            if iface.driver in ('brcmfmac',):
                Color.pl('    {O}⚠ Broadcom FullMAC — limited injection support{W}')

            Color.pl('')  # Blank line between interfaces

    def _render_attack_readiness(self):
        """Render attack readiness summary."""
        from ..util.color import Color

        Color.pl('{C}─── Attack Readiness ─────────────────────────────────────────{W}')

        for attack, status in self.attack_readiness.items():
            icon = self._status_icon(status)
            if status == CheckStatus.PASS:
                label = '{G}Ready{W}'
            elif status == CheckStatus.WARN:
                label = '{O}Partial{W}'
            else:
                label = '{R}Unavailable{W}'
            Color.pl(f'  {icon} {{W}}{attack.ljust(22)} {label}')

        # Summary counts
        ready = sum(1 for s in self.attack_readiness.values() if s == CheckStatus.PASS)
        partial = sum(1 for s in self.attack_readiness.values() if s == CheckStatus.WARN)
        unavail = sum(1 for s in self.attack_readiness.values() if s == CheckStatus.FAIL)
        total = len(self.attack_readiness)

        Color.pl(f'\n  {{G}}{ready}{{W}}/{total} ready   '
                 f'{{O}}{partial}{{W}} partial   '
                 f'{{R}}{unavail}{{W}} unavailable')

    @staticmethod
    def _status_icon(status: CheckStatus) -> str:
        """Return colored icon for a check status."""
        icons = {
            CheckStatus.PASS: '{G}✓{W}',
            CheckStatus.WARN: '{O}⚠{W}',
            CheckStatus.FAIL: '{R}✗{W}',
            CheckStatus.SKIP: '{D}─{W}',
            CheckStatus.INFO: '{C}ℹ{W}',
        }
        return icons.get(status, '{D}?{W}')


def run_system_check(verbose: int = 0, smoke_test: bool = False):
    """
    Entry point for --syscheck command.

    Args:
        verbose: Verbosity level
        smoke_test: Whether to run monitor mode smoke test
    """
    checker = SystemCheck(verbose=verbose, run_smoke_test=smoke_test)
    checker.run_all()
    checker.render_report()
