#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shlex
import shutil
import subprocess


class PackageManager:
    """
    Auto-detects and provides an interface to the system package manager.
    Supports apt, pacman, dnf/yum, apk, zypper, emerge, and brew.
    """

    _detected = None

    # Map of package manager name -> (check_cmd, install_cmd_template, update_cmd)
    MANAGERS = {
        'apt':     ('apt',     'apt install -y {pkg}',     'apt update'),
        'pacman':  ('pacman',  'pacman -S --noconfirm {pkg}', 'pacman -Sy'),
        'dnf':     ('dnf',     'dnf install -y {pkg}',     'dnf check-update'),
        'yum':     ('yum',     'yum install -y {pkg}',     'yum check-update'),
        'apk':     ('apk',     'apk add {pkg}',            'apk update'),
        'zypper':  ('zypper',  'zypper install -y {pkg}',  'zypper refresh'),
        'emerge':  ('emerge',  'emerge {pkg}',             'emerge --sync'),
        'brew':    ('brew',    'brew install {pkg}',        'brew update'),
    }

    # Priority order for detection
    PRIORITY = ['apt', 'pacman', 'dnf', 'yum', 'apk', 'zypper', 'emerge', 'brew']

    @classmethod
    def detect(cls):
        """Detect the system package manager. Cached after first call."""
        if cls._detected is not None:
            return cls._detected

        for name in cls.PRIORITY:
            check_cmd = cls.MANAGERS[name][0]
            if shutil.which(check_cmd):
                cls._detected = name
                return cls._detected

        cls._detected = ''  # Empty string = not found (but cached)
        return cls._detected

    @classmethod
    def name(cls):
        """Return detected package manager name or None."""
        result = cls.detect()
        return result if result else None

    @classmethod
    def install_command(cls, package_name):
        """Return the full install command string for a package."""
        mgr = cls.detect()
        if not mgr:
            return None
        _, template, _ = cls.MANAGERS[mgr]
        return template.format(pkg=package_name)

    @classmethod
    def update_command(cls):
        """Return the package index update command."""
        mgr = cls.detect()
        if not mgr:
            return None
        _, _, update_cmd = cls.MANAGERS[mgr]
        return update_cmd

    @classmethod
    def install(cls, package_name):
        """
        Attempt to install a package using the detected package manager.
        Returns (success: bool, output: str).
        """
        cmd = cls.install_command(package_name)
        if not cmd:
            return False, 'No supported package manager found'
        try:
            result = subprocess.run(
                shlex.split(cmd), shell=False, capture_output=True, text=True, timeout=300
            )
            output = (result.stdout + '\n' + result.stderr).strip()
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, 'Installation timed out (300s)'
        except Exception as e:
            return False, str(e)


class Dependency:
    """
    Base class for all external tool wrappers.

    Every subclass MUST define:
        dependency_name     (str)  — binary name (e.g. 'aircrack-ng')
        dependency_required (bool) — True if wifite cannot run without it
        dependency_url      (str)  — upstream URL for manual install

    Subclasses MAY define:
        dependency_packages (dict) — {pkg_manager: package_name} overrides
                                     e.g. {'apt': 'aircrack-ng', 'pacman': 'aircrack-ng'}
        dependency_category (str)  — grouping label (see CATEGORIES)
        dependency_min_version (str) — minimum required version (e.g. '1.6.0')
        native_alternative  (str)  — name of native Python alternative if available
                                     e.g. 'wifite.native.deauth' for aireplay deauth
    """
    
    # Native alternatives map: dependency_name -> (description, check_function)
    # The check function returns True if the native alternative is available
    NATIVE_ALTERNATIVES = {
        'macchanger': ('Native MAC manipulation via sysfs/ioctl', '_check_native_mac'),
        'tshark': ('Native packet analysis via Scapy', '_check_native_scapy'),
        'hcxdumptool': ('Native PMKID capture via Scapy (basic)', '_check_native_pmkid'),
    }
    
    @classmethod
    def _check_native_mac(cls) -> bool:
        """Check if native MAC manipulation is available."""
        try:
            from ..native.mac import NativeMac
            return True
        except ImportError:
            return False
    
    @classmethod
    def _check_native_scapy(cls) -> bool:
        """Check if native Scapy analysis is available."""
        try:
            from ..native.handshake import ScapyHandshake
            from ..native.wps import ScapyWPS
            return ScapyHandshake.is_available() and ScapyWPS.is_available()
        except ImportError:
            return False
    
    @classmethod
    def _check_native_pmkid(cls) -> bool:
        """Check if native PMKID capture is available."""
        try:
            from ..native.pmkid import ScapyPMKID
            return ScapyPMKID.is_available()
        except ImportError:
            return False

    dependency_name = None
    dependency_required = None
    dependency_url = None
    dependency_packages = None   # Optional: {manager: pkg_name} mapping
    dependency_category = None   # Optional: category label
    dependency_min_version = None  # Optional: minimum required version

    required_attr_names = ['dependency_name', 'dependency_url', 'dependency_required']
    
    # Known minimum versions for critical functionality
    MINIMUM_VERSIONS = {
        'hcxdumptool': '6.2.0',
        'hcxpcapngtool': '6.2.0',
        'hashcat': '6.0.0',
        'aircrack-ng': '1.6',
        'reaver': '1.6.5',
        'bully': '1.4',
        'tshark': '3.0.0',
    }

    # Dependency categories for organized display
    CATEGORY_CORE = 'core'           # Aircrack suite, iw, ip
    CATEGORY_WPS = 'wps'             # Reaver, Bully
    CATEGORY_CRACK = 'cracking'      # Hashcat, hcxdumptool, hcxpcapngtool
    CATEGORY_INSPECT = 'inspection'  # Tshark
    CATEGORY_MISC = 'misc'           # Macchanger
    CATEGORY_EVILTWIN = 'eviltwin'   # Hostapd, dnsmasq
    CATEGORY_WPA3 = 'wpa3'           # hcxdumptool, hcxpcapngtool (overlap)
    CATEGORY_WPASEC = 'wpasec'       # wlancap2wpasec

    CATEGORY_LABELS = {
        CATEGORY_CORE:     'Core (required)',
        CATEGORY_WPS:      'WPS Attacks',
        CATEGORY_CRACK:    'Cracking & Handshakes',
        CATEGORY_INSPECT:  'Packet Inspection',
        CATEGORY_MISC:     'Miscellaneous',
        CATEGORY_EVILTWIN: 'Evil Twin',
        CATEGORY_WPA3:     'WPA3',
        CATEGORY_WPASEC:   'WPA-SEC Upload',
    }

    # --- Subclass enforcement ---

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for attr_name in cls.required_attr_names:
            if attr_name not in cls.__dict__:
                raise NotImplementedError(
                    f'Attribute "{attr_name}" has not been overridden in class "{cls.__name__}"'
                )

    # --- Existence / version checks ---

    @classmethod
    def exists(cls):
        """Check if the dependency binary is on PATH."""
        from ..util.process import Process
        return Process.exists(cls.dependency_name)

    @classmethod
    def get_version(cls):
        """
        Try to determine the installed version of the dependency.
        Returns version string or None.
        """
        if not cls.exists():
            return None

        # Try common version flags in order
        for flag in ['--version', '-v', '-V', 'version']:
            try:
                result = subprocess.run(
                    [cls.dependency_name, flag],
                    capture_output=True, text=True, timeout=5
                )
                combined = (result.stdout + ' ' + result.stderr).strip()
                if combined:
                    # Extract first version-like string
                    import re
                    match = re.search(r'(\d+\.\d+[\.\d]*\w*)', combined)
                    if match:
                        return match.group(1)
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        return None
    
    @classmethod
    def get_minimum_version(cls):
        """
        Get the minimum required version for this dependency.
        Returns version string or None if no minimum is defined.
        """
        # Check class-level override first
        if cls.dependency_min_version:
            return cls.dependency_min_version
        # Fall back to global minimum versions
        return cls.MINIMUM_VERSIONS.get(cls.dependency_name)
    
    @classmethod
    def check_version_meets_minimum(cls):
        """
        Check if installed version meets minimum requirements.
        
        Returns:
            tuple: (meets_requirement: bool, installed_version: str or None, min_version: str or None)
        """
        installed = cls.get_version()
        minimum = cls.get_minimum_version()
        
        if not minimum:
            # No minimum defined, any version is OK
            return (True, installed, None)
        
        if not installed:
            # Can't determine version, assume OK but warn
            return (True, None, minimum)
        
        # Compare versions
        meets = cls._compare_versions(installed, minimum) >= 0
        return (meets, installed, minimum)
    
    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """
        Compare two version strings.
        
        Returns:
            -1 if v1 < v2
             0 if v1 == v2
             1 if v1 > v2
        """
        import re
        
        def normalize(v):
            # Extract numeric parts only
            parts = re.findall(r'\d+', v)
            return [int(p) for p in parts]
        
        n1 = normalize(v1)
        n2 = normalize(v2)
        
        # Pad shorter list with zeros
        max_len = max(len(n1), len(n2))
        n1.extend([0] * (max_len - len(n1)))
        n2.extend([0] * (max_len - len(n2)))
        
        for a, b in zip(n1, n2):
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0

    # --- Install helpers ---

    @classmethod
    def get_package_name(cls):
        """
        Return the package name for the current system's package manager.
        Falls back to dependency_name if no specific mapping is defined.
        """
        mgr = PackageManager.name()
        if mgr and cls.dependency_packages and mgr in cls.dependency_packages:
            return cls.dependency_packages[mgr]
        # Sensible default: the binary name is often the package name
        return cls.dependency_name

    @classmethod
    def get_install_command(cls):
        """Return the full install command string for this dependency."""
        pkg = cls.get_package_name()
        return PackageManager.install_command(pkg)

    @classmethod
    def print_install(cls):
        """Print human-readable install instructions."""
        from ..util.color import Color

        cmd = cls.get_install_command()
        if cmd:
            Color.pl('{+}   Install with: {C}%s{W}' % cmd)
        Color.pl('{+}   More info:    {C}%s{W}' % cls.dependency_url)

    @classmethod
    def install(cls):
        """
        Attempt automatic installation of this dependency.
        Returns (success: bool, message: str).
        """
        pkg = cls.get_package_name()
        return PackageManager.install(pkg)

    # --- Dependency check (startup) ---

    @classmethod
    def has_native_alternative(cls) -> bool:
        """
        Check if a native Python alternative is available for this dependency.
        """
        if cls.dependency_name not in cls.NATIVE_ALTERNATIVES:
            return False
        
        # Get the check function name and call it
        _, check_func_name = cls.NATIVE_ALTERNATIVES[cls.dependency_name]
        
        # Call the check function from the base class
        check_func = getattr(Dependency, check_func_name, None)
        if check_func:
            return check_func()
        
        return False
    
    @classmethod
    def get_native_description(cls) -> str:
        """
        Get description of the native alternative.
        """
        if cls.dependency_name in cls.NATIVE_ALTERNATIVES:
            return cls.NATIVE_ALTERNATIVES[cls.dependency_name][0]
        return ''
    
    @classmethod
    def fails_dependency_check(cls):
        """
        Check if this dependency is missing or has insufficient version.
        Prints status and returns True if a REQUIRED dep is missing/insufficient.
        
        Note: If a native alternative is available, the dependency is not
        considered missing even if the binary is not installed.
        """
        from ..util.color import Color
        from ..util.process import Process

        if Process.exists(cls.dependency_name):
            # Tool exists - check version
            meets, installed, minimum = cls.check_version_meets_minimum()
            
            if not meets:
                if cls.dependency_required:
                    Color.pl('{!} {R}Tool version too old: {O}%s{W} (v%s, need v%s+)' % (
                        cls.dependency_name, installed or '?', minimum))
                    Color.pl('{!} {O}Please upgrade to version %s or higher{W}' % minimum)
                    cls.print_install()
                    return True
                else:
                    Color.pl('{!} {O}Tool version outdated: {R}%s{W} (v%s, recommend v%s+)' % (
                        cls.dependency_name, installed or '?', minimum))
                    return False
            
            return False
        
        # Check for native alternative
        if cls.has_native_alternative():
            native_desc = cls.get_native_description()
            Color.pl('{+} {G}%s{W}: using {C}%s{W}' % (cls.dependency_name, native_desc))
            return False

        if cls.dependency_required:
            Color.pl('{!} {R}Missing required tool: {O}%s{W}' % cls.dependency_name)
            cls.print_install()
            return True
        else:
            Color.pl('{!} {O}Missing optional tool: {R}%s{W}' % cls.dependency_name)
            cls.print_install()
            return False

    @classmethod
    def run_dependency_check(cls):
        """
        Master dependency check — called once at wifite startup.
        Groups deps by category, checks each, offers interactive install.
        """
        from ..util.color import Color

        from .aircrack import Aircrack
        from .ip import Ip
        from .iw import Iw
        from .bully import Bully
        from .reaver import Reaver
        from .tshark import Tshark
        from .macchanger import Macchanger
        from .hashcat import Hashcat, HcxDumpTool, HcxPcapngTool

        apps = [
            # Core
            Aircrack, Iw, Ip,
            # WPS
            Reaver, Bully,
            # Cracking / handshakes
            Tshark,
            # Hashcat
            Hashcat, HcxDumpTool, HcxPcapngTool,
            # Misc
            Macchanger,
        ]

        # Partition into present / missing-required / missing-optional
        missing_required = []
        missing_optional = []
        present = []

        for app in apps:
            if app.exists():
                present.append(app)
            elif app.dependency_required:
                missing_required.append(app)
            else:
                missing_optional.append(app)

        # Show summary
        if present:
            Color.pl('{+} {G}Found %d tool(s){W}' % len(present))
            from ..config import Configuration
            if Configuration.verbose >= 2:
                for app in present:
                    Color.pl('{+} {D}  %s{W}' % app.dependency_name)

        # Offer to install missing optional deps
        if missing_optional:
            Color.pl('')
            Color.pl('{!} {O}Missing %d optional tool(s):{W}' % len(missing_optional))
            for app in missing_optional:
                ver_str = ''
                Color.pl('{!}   {R}%s{W} — %s%s' % (app.dependency_name, app.dependency_url, ver_str))
                cmd = app.get_install_command()
                if cmd:
                    Color.pl('{!}     {D}Install: {C}%s{W}' % cmd)

        # Handle missing required deps
        if missing_required:
            Color.pl('')
            Color.pl('{!} {R}Missing %d required tool(s):{W}' % len(missing_required))
            for app in missing_required:
                Color.pl('{!}   {R}%s{W} — %s' % (app.dependency_name, app.dependency_url))
                cmd = app.get_install_command()
                if cmd:
                    Color.pl('{!}     {D}Install: {C}%s{W}' % cmd)

            # Offer to auto-install
            if not cls._offer_install(missing_required, required=True):
                # Still missing after install attempt
                still_missing = [a for a in missing_required if not a.exists()]
                if still_missing:
                    names = ', '.join(a.dependency_name for a in still_missing)
                    Color.pl('{!} {R}Cannot continue without: %s{W}' % names)
                    Color.pl('{!} {O}Install the missing tools and re-run wifite{W}')
                    raise SystemExit(1)

        # Check WPA3, Evil Twin, wpasec tools (optional warnings)
        cls._check_wpa3_tools()
        cls._check_eviltwin_tools()
        cls._check_wpasec_tools()

    @classmethod
    def _offer_install(cls, deps, required=False):
        """
        Prompt user to auto-install missing dependencies.
        Returns True if all deps are now satisfied.
        """
        from ..util.color import Color

        mgr = PackageManager.name()
        if not mgr:
            Color.pl('{!} {O}No supported package manager detected — install manually{W}')
            return False

        if os.getuid() != 0:
            Color.pl('{!} {O}Not running as root — cannot auto-install packages{W}')
            return False

        label = 'required' if required else 'optional'
        names = ', '.join(d.dependency_name for d in deps)
        Color.pl('')
        Color.p('{+} Auto-install %s tool(s) (%s) using {C}%s{W}? [Y/n]: ' % (label, names, mgr))

        try:
            answer = input().strip().lower()
        except (KeyboardInterrupt, EOFError):
            Color.pl('')
            return False

        if answer and answer != 'y':
            return False

        # Attempt installation
        all_ok = True
        for dep in deps:
            pkg = dep.get_package_name()
            Color.p('{+} Installing {C}%s{W} (%s)... ' % (dep.dependency_name, pkg))
            success, output = dep.install()
            if success and dep.exists():
                ver = dep.get_version()
                ver_str = ' v%s' % ver if ver else ''
                Color.pl('{G}OK%s{W}' % ver_str)
            else:
                Color.pl('{R}FAILED{W}')
                if output:
                    # Show last 3 lines of output
                    for line in output.strip().split('\n')[-3:]:
                        Color.pl('{!}   {D}%s{W}' % line)
                all_ok = False

        return all_ok

    @classmethod
    def _check_wpa3_tools(cls):
        """Check for WPA3-specific tools and warn if missing."""
        from ..util.color import Color
        from ..util.wpa3_tools import WPA3ToolChecker

        if not WPA3ToolChecker.can_attack_wpa3():
            missing = WPA3ToolChecker.get_missing_tools()
            if missing:
                Color.pl('\n{!} {O}Warning: WPA3 attacks will not be available{W}')
                Color.pl('{!} {O}Missing WPA3 tools: {R}%s{W}' % ', '.join(missing))
                cmd = PackageManager.install_command('hcxdumptool')
                if cmd:
                    Color.pl('{!} {O}Install with: {C}%s{W}' % cmd)
                else:
                    Color.pl('{!} {O}Install with: {C}apt install hcxdumptool hcxtools{W}')
                Color.pl('')

    @classmethod
    def _check_eviltwin_tools(cls):
        """Check for Evil Twin-specific tools and warn if missing."""
        from ..util.color import Color
        from ..config import Configuration

        if not Configuration.use_eviltwin:
            return

        missing_tools = []
        install_commands = []

        from ..util.process import Process
        if not Process.exists('hostapd'):
            missing_tools.append('hostapd')
            cmd = PackageManager.install_command('hostapd')
            install_commands.append(cmd or 'apt install hostapd')

        if not Process.exists('dnsmasq'):
            missing_tools.append('dnsmasq')
            cmd = PackageManager.install_command('dnsmasq')
            install_commands.append(cmd or 'apt install dnsmasq')

        if not Process.exists('wpa_supplicant'):
            missing_tools.append('wpa_supplicant')
            cmd = PackageManager.install_command('wpasupplicant')
            install_commands.append(cmd or 'apt install wpasupplicant')

        if missing_tools:
            Color.pl('\n{!} {R}Error: Evil Twin attack requires additional tools{W}')
            Color.pl('{!} {O}Missing tools: {R}%s{W}' % ', '.join(missing_tools))
            Color.pl('{!} {O}Install with:{W}')
            for cmd in install_commands:
                Color.pl('{!}   {C}%s{W}' % cmd)
            Color.pl('')

            raise SystemExit(1)

    @classmethod
    def _check_wpasec_tools(cls):
        """Check for wpa-sec upload tools and warn if missing."""
        from ..util.color import Color
        from .wlancap2wpasec import Wlancap2wpasec

        if not Wlancap2wpasec.exists():
            Color.pl('\n{!} {O}Warning: wpa-sec upload functionality will not be available{W}')
            Color.pl('{!} {O}Missing tool: {R}wlancap2wpasec{W}')
            cmd = PackageManager.install_command('hcxtools')
            if cmd:
                Color.pl('{!} {O}Install with: {C}%s{W}' % cmd)
            else:
                Color.pl('{!} {O}Install with: {C}apt install hcxtools{W}')
            Color.pl('{!} {O}wpa-sec allows uploading captures to wpa-sec.stanev.org for online cracking{W}')
            Color.pl('')
