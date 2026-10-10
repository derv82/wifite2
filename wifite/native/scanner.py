#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Native channel hopping and scanning utilities.

Provides pure Python channel hopping without relying on external tools.
Integrates with the NativeInterface module for channel control.

Usage:
    from wifite.native.scanner import ChannelHopper, NativeScanner
    
    # Simple channel hopping
    hopper = ChannelHopper('wlan0mon', channels=[1, 6, 11])
    hopper.start()
    # ... do scanning ...
    hopper.stop()
    
    # Full native scanning
    scanner = NativeScanner('wlan0mon')
    scanner.start()
    time.sleep(10)
    targets = scanner.get_targets()
    scanner.stop()

Channel Frequencies:
    2.4 GHz: Channels 1-14 (2412-2484 MHz)
    5 GHz: Channels 36-165 (5180-5825 MHz)
"""

import time
from threading import Thread, Event, Lock
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass, field

try:
    from scapy.all import (
        RadioTap, Dot11, Dot11Beacon, Dot11ProbeResp, Dot11ProbeReq,
        Dot11Elt, Dot11AssoReq, Dot11AssoResp, Dot11Auth,
        sniff, conf as scapy_conf
    )
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


# Standard WiFi channels
CHANNELS_24GHZ = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]  # 14 is Japan-only
CHANNELS_5GHZ_LOWER = [36, 40, 44, 48, 52, 56, 60, 64]  # UNII-1 + UNII-2A
CHANNELS_5GHZ_UPPER = [100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144]  # UNII-2C
CHANNELS_5GHZ_HIGH = [149, 153, 157, 161, 165]  # UNII-3
CHANNELS_5GHZ = CHANNELS_5GHZ_LOWER + CHANNELS_5GHZ_UPPER + CHANNELS_5GHZ_HIGH
CHANNELS_ALL = CHANNELS_24GHZ + CHANNELS_5GHZ


@dataclass
class AccessPoint:
    """Represents a detected access point."""
    bssid: str
    essid: str = ''
    channel: int = 0
    frequency: int = 0
    encryption: str = 'OPEN'  # OPEN, WEP, WPA, WPA2, WPA3
    cipher: str = ''  # CCMP, TKIP
    auth: str = ''  # PSK, MGT
    wps: bool = False
    wps_locked: bool = False
    power: int = -100  # dBm
    beacons: int = 0
    clients: List[str] = field(default_factory=list)
    last_seen: float = 0
    first_seen: float = 0
    
    # Additional info
    vendor: Optional[str] = None
    hidden: bool = False
    pmf: bool = False  # Protected Management Frames (WPA3 requirement)


@dataclass  
class Client:
    """Represents a detected wireless client."""
    mac: str
    bssid: Optional[str] = None  # Associated AP
    power: int = -100
    probes: List[str] = field(default_factory=list)
    last_seen: float = 0
    first_seen: float = 0
    packets: int = 0


class ChannelHopper(Thread):
    """
    Background thread for channel hopping.
    
    Hops through specified channels at configurable intervals.
    Can be paused to stay on a specific channel during attacks.
    """
    
    def __init__(self,
                 interface: str,
                 channels: Optional[List[int]] = None,
                 interval: float = 0.5,
                 band: str = '2.4'):
        """
        Initialize channel hopper.
        
        Args:
            interface: Monitor mode interface
            channels: List of channels to hop (None = auto based on band)
            interval: Seconds between channel changes
            band: '2.4', '5', or 'all' (used if channels is None)
        """
        super().__init__()
        self.daemon = True
        
        self.interface = interface
        self.interval = interval
        
        # Determine channels
        if channels:
            self.channels = channels
        elif band == '5':
            self.channels = CHANNELS_5GHZ
        elif band == 'all':
            self.channels = CHANNELS_ALL
        else:
            self.channels = CHANNELS_24GHZ
        
        self.current_channel = self.channels[0] if self.channels else 1
        self._channel_index = 0
        
        self._stop_event = Event()
        self._pause_event = Event()
        self._pause_event.set()  # Not paused
        
        # Stats
        self.hops = 0
        self.start_time = None
        
        # Callbacks
        self._on_channel_change: Optional[Callable[[int], None]] = None
    
    def run(self):
        """Main hopping loop."""
        from .interface import NativeInterface
        
        self.start_time = time.time()
        
        while not self._stop_event.is_set():
            # Check if paused
            self._pause_event.wait()
            
            if self._stop_event.is_set():
                break
            
            # Set channel
            channel = self.channels[self._channel_index]
            try:
                NativeInterface.set_channel(self.interface, channel)
                self.current_channel = channel
                self.hops += 1
                
                if self._on_channel_change:
                    self._on_channel_change(channel)
                    
            except (OSError, RuntimeError):
                pass  # Channel might not be supported
            
            # Move to next channel
            self._channel_index = (self._channel_index + 1) % len(self.channels)
            
            # Wait
            self._stop_event.wait(timeout=self.interval)
    
    def stop(self):
        """Stop hopping."""
        self._stop_event.set()
        self._pause_event.set()  # Unblock if paused
        if self.is_alive():
            self.join(timeout=2)
    
    def pause(self):
        """Pause hopping on current channel."""
        self._pause_event.clear()
    
    def resume(self):
        """Resume hopping."""
        self._pause_event.set()
    
    def is_paused(self) -> bool:
        """Check if paused."""
        return not self._pause_event.is_set()
    
    def set_channel(self, channel: int):
        """
        Switch to specific channel and pause hopping.
        
        Args:
            channel: Channel to switch to
        """
        from .interface import NativeInterface
        
        self.pause()
        NativeInterface.set_channel(self.interface, channel)
        self.current_channel = channel
    
    def set_interval(self, interval: float):
        """Set hopping interval."""
        self.interval = interval
    
    def on_channel_change(self, callback: Callable[[int], None]):
        """Set callback for channel changes."""
        self._on_channel_change = callback
    
    def get_stats(self) -> dict:
        """Get hopping statistics."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'current_channel': self.current_channel,
            'total_hops': self.hops,
            'elapsed_time': elapsed,
            'hops_per_second': self.hops / elapsed if elapsed > 0 else 0,
            'paused': self.is_paused()
        }


class NativeScanner:
    """
    Native WiFi network scanner using Scapy.
    
    Captures and parses beacon frames to build a list of access points
    and associated clients. Provides an alternative to airodump-ng.
    
    Note: For production use, airodump-ng is still recommended as it
    handles more edge cases and has better driver compatibility.
    """
    
    def __init__(self,
                 interface: str,
                 channels: Optional[List[int]] = None,
                 band: str = '2.4',
                 hop_interval: float = 0.5):
        """
        Initialize scanner.
        
        Args:
            interface: Monitor mode interface
            channels: Specific channels to scan (None = auto)
            band: '2.4', '5', or 'all'
            hop_interval: Channel hopping interval in seconds
        """
        self.interface = interface
        self.channels = channels
        self.band = band
        self.hop_interval = hop_interval
        
        # Data storage
        self.access_points: Dict[str, AccessPoint] = {}
        self.clients: Dict[str, Client] = {}
        self._lock = Lock()
        
        # Components
        self.hopper: Optional[ChannelHopper] = None
        self._capture_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # Stats
        self.packets_processed = 0
        self.start_time: Optional[float] = None
    
    def start(self):
        """Start scanning."""
        if not SCAPY_AVAILABLE:
            raise RuntimeError("Scapy is not available")
        
        self.start_time = time.time()
        self._stop_event.clear()
        
        # Start channel hopper
        self.hopper = ChannelHopper(
            self.interface,
            channels=self.channels,
            interval=self.hop_interval,
            band=self.band
        )
        self.hopper.start()
        
        # Start capture thread
        self._capture_thread = Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
    
    def stop(self):
        """Stop scanning."""
        self._stop_event.set()
        
        if self.hopper:
            self.hopper.stop()
        
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2)
    
    def _capture_loop(self):
        """Main packet capture loop."""
        try:
            sniff(
                iface=self.interface,
                prn=self._packet_handler,
                store=False,
                stop_filter=lambda _: self._stop_event.is_set()
            )
        except OSError:
            pass

    def _packet_handler(self, pkt):
        """Process captured packet."""
        self.packets_processed += 1
        
        if not pkt.haslayer(Dot11):
            return
        
        dot11 = pkt[Dot11]
        
        # Determine frame type
        frame_type = dot11.type
        frame_subtype = dot11.subtype
        
        # Management frames
        if frame_type == 0:
            if frame_subtype == 8:  # Beacon
                self._process_beacon(pkt)
            elif frame_subtype == 5:  # Probe Response
                self._process_probe_response(pkt)
            elif frame_subtype == 4:  # Probe Request
                self._process_probe_request(pkt)
            elif frame_subtype in (0, 2):  # Association Request/Response
                self._process_association(pkt)
        
        # Data frames - track clients
        elif frame_type == 2:
            self._process_data(pkt)
    
    def _process_beacon(self, pkt):
        """Process beacon frame."""
        dot11 = pkt[Dot11]
        bssid = (dot11.addr3 or '').upper()
        
        if not bssid or bssid == 'FF:FF:FF:FF:FF:FF':
            return
        
        # Extract info from beacon
        essid = ''
        channel = 0
        encryption = 'OPEN'
        cipher = ''
        auth = ''
        wps = False
        wps_locked = False
        hidden = False
        pmf = False
        
        # Parse information elements
        elt = pkt.getlayer(Dot11Elt)
        while elt:
            if elt.ID == 0:  # SSID
                try:
                    essid = elt.info.decode('utf-8', errors='replace')
                    if not essid or essid == '\x00' * len(essid):
                        hidden = True
                        essid = '<hidden>'
                except (UnicodeDecodeError, AttributeError):
                    pass
            
            elif elt.ID == 3:  # Channel
                try:
                    channel = elt.info[0]
                except (UnicodeDecodeError, AttributeError):
                    pass
            
            elif elt.ID == 48:  # RSN (WPA2/WPA3)
                encryption, cipher, auth, pmf = self._parse_rsn_ie(bytes(elt.info))
            
            elif elt.ID == 221:  # Vendor specific
                vendor_data = bytes(elt.info) if hasattr(elt, 'info') else b''
                
                # WPA IE
                if vendor_data.startswith(b'\x00\x50\xf2\x01'):
                    if encryption == 'OPEN':
                        encryption = 'WPA'
                    wpa_cipher, wpa_auth = self._parse_wpa_ie(vendor_data)
                    if not cipher:
                        cipher = wpa_cipher
                    if not auth:
                        auth = wpa_auth
                
                # WPS IE
                elif vendor_data.startswith(b'\x00\x50\xf2\x04'):
                    wps = True
                    # Check if locked
                    wps_locked = self._check_wps_locked(vendor_data)
            
            # Move to next element
            if hasattr(elt, 'payload') and elt.payload:
                elt = elt.payload.getlayer(Dot11Elt) if hasattr(elt.payload, 'getlayer') else None
            else:
                elt = None
        
        # Get signal strength
        power = -100
        if pkt.haslayer(RadioTap):
            try:
                power = pkt[RadioTap].dBm_AntSignal
            except (AttributeError, TypeError):
                pass
        
        # Update or create AP
        with self._lock:
            if bssid in self.access_points:
                ap = self.access_points[bssid]
                ap.beacons += 1
                ap.last_seen = time.time()
                ap.power = power
                if essid and not ap.essid:
                    ap.essid = essid
                if channel:
                    ap.channel = channel
            else:
                self.access_points[bssid] = AccessPoint(
                    bssid=bssid,
                    essid=essid,
                    channel=channel or (self.hopper.current_channel if self.hopper else 0),
                    encryption=encryption,
                    cipher=cipher,
                    auth=auth,
                    wps=wps,
                    wps_locked=wps_locked,
                    power=power,
                    beacons=1,
                    last_seen=time.time(),
                    first_seen=time.time(),
                    hidden=hidden,
                    pmf=pmf
                )
    
    def _process_probe_response(self, pkt):
        """Process probe response (similar to beacon)."""
        self._process_beacon(pkt)
    
    def _process_probe_request(self, pkt):
        """Process probe request to track clients."""
        dot11 = pkt[Dot11]
        client_mac = (dot11.addr2 or '').upper()
        
        if not client_mac or client_mac == 'FF:FF:FF:FF:FF:FF':
            return
        
        # Extract probed SSID
        probed_ssid = None
        elt = pkt.getlayer(Dot11Elt)
        while elt:
            if elt.ID == 0:
                try:
                    ssid = elt.info.decode('utf-8', errors='replace')
                    if ssid and ssid != '\x00' * len(ssid):
                        probed_ssid = ssid
                except (UnicodeDecodeError, AttributeError):
                    pass
                break
            elt = elt.payload.getlayer(Dot11Elt) if hasattr(elt.payload, 'getlayer') else None
        
        # Get signal strength
        power = -100
        if pkt.haslayer(RadioTap):
            try:
                power = pkt[RadioTap].dBm_AntSignal
            except (AttributeError, TypeError):
                pass
        
        # Update client
        with self._lock:
            if client_mac in self.clients:
                client = self.clients[client_mac]
                client.last_seen = time.time()
                client.power = power
                client.packets += 1
                if probed_ssid and probed_ssid not in client.probes:
                    client.probes.append(probed_ssid)
            else:
                self.clients[client_mac] = Client(
                    mac=client_mac,
                    power=power,
                    probes=[probed_ssid] if probed_ssid else [],
                    last_seen=time.time(),
                    first_seen=time.time(),
                    packets=1
                )
    
    def _process_association(self, pkt):
        """Process association frames to link clients to APs."""
        dot11 = pkt[Dot11]
        
        # Association request: client -> AP
        if dot11.subtype == 0:
            client_mac = (dot11.addr2 or '').upper()
            bssid = (dot11.addr3 or '').upper()
        # Association response: AP -> client
        else:
            client_mac = (dot11.addr1 or '').upper()
            bssid = (dot11.addr3 or '').upper()
        
        if not client_mac or not bssid:
            return
        
        with self._lock:
            # Update client
            if client_mac in self.clients:
                self.clients[client_mac].bssid = bssid
            else:
                self.clients[client_mac] = Client(
                    mac=client_mac,
                    bssid=bssid,
                    last_seen=time.time(),
                    first_seen=time.time()
                )
            
            # Update AP's client list
            if bssid in self.access_points:
                if client_mac not in self.access_points[bssid].clients:
                    self.access_points[bssid].clients.append(client_mac)
    
    def _process_data(self, pkt):
        """Process data frames to track client-AP associations."""
        dot11 = pkt[Dot11]
        
        # FromDS: AP -> Client
        if dot11.FCfield & 0x2:
            bssid = (dot11.addr2 or '').upper()
            client_mac = (dot11.addr1 or '').upper()
        # ToDS: Client -> AP
        elif dot11.FCfield & 0x1:
            bssid = (dot11.addr1 or '').upper()
            client_mac = (dot11.addr2 or '').upper()
        else:
            return
        
        if not client_mac or client_mac == 'FF:FF:FF:FF:FF:FF':
            return
        
        # Get signal strength
        power = -100
        if pkt.haslayer(RadioTap):
            try:
                power = pkt[RadioTap].dBm_AntSignal
            except (AttributeError, TypeError):
                pass
        
        with self._lock:
            # Update client
            if client_mac in self.clients:
                self.clients[client_mac].bssid = bssid
                self.clients[client_mac].last_seen = time.time()
                self.clients[client_mac].packets += 1
                self.clients[client_mac].power = power
            else:
                self.clients[client_mac] = Client(
                    mac=client_mac,
                    bssid=bssid,
                    power=power,
                    last_seen=time.time(),
                    first_seen=time.time(),
                    packets=1
                )
            
            # Update AP
            if bssid in self.access_points:
                if client_mac not in self.access_points[bssid].clients:
                    self.access_points[bssid].clients.append(client_mac)
    
    def _parse_rsn_ie(self, data: bytes) -> tuple:
        """
        Parse RSN Information Element.
        
        Returns:
            Tuple of (encryption, cipher, auth, pmf)
        """
        encryption = 'WPA2'
        cipher = ''
        auth = ''
        pmf = False
        
        try:
            if len(data) < 8:
                return encryption, cipher, auth, pmf
            
            offset = 2  # Skip version
            
            # Group cipher (4 bytes)
            if offset + 4 <= len(data):
                group_cipher = data[offset:offset + 4]
                offset += 4
            
            # Pairwise cipher count
            if offset + 2 <= len(data):
                count = data[offset] | (data[offset + 1] << 8)
                offset += 2
                
                # Parse pairwise ciphers
                ciphers = []
                for _ in range(count):
                    if offset + 4 <= len(data):
                        cipher_suite = data[offset:offset + 4]
                        if cipher_suite[-1] == 4:
                            ciphers.append('CCMP')
                        elif cipher_suite[-1] == 2:
                            ciphers.append('TKIP')
                        offset += 4
                cipher = ' '.join(ciphers)
            
            # AKM count
            if offset + 2 <= len(data):
                akm_count = data[offset] | (data[offset + 1] << 8)
                offset += 2
                
                # Parse AKM suites
                akms = []
                for _ in range(akm_count):
                    if offset + 4 <= len(data):
                        akm_suite = data[offset:offset + 4]
                        if akm_suite[-1] == 2:
                            akms.append('PSK')
                        elif akm_suite[-1] == 1:
                            akms.append('MGT')
                        elif akm_suite[-1] == 8:
                            akms.append('SAE')  # WPA3
                            encryption = 'WPA3'
                        offset += 4
                auth = ' '.join(akms)
            
            # RSN capabilities
            if offset + 2 <= len(data):
                caps = data[offset] | (data[offset + 1] << 8)
                # Bit 6: Management Frame Protection Capable
                # Bit 7: Management Frame Protection Required
                if caps & 0x80:
                    pmf = True
                    if 'SAE' in auth:
                        encryption = 'WPA3'
                        
        except (AttributeError, TypeError, IndexError):
                pass

        return encryption, cipher, auth, pmf

    def _parse_wpa_ie(self, data: bytes) -> tuple:
        """
        Parse WPA Information Element.
        
        Returns:
            Tuple of (cipher, auth)
        """
        cipher = ''
        auth = ''
        
        try:
            if len(data) < 12:
                return cipher, auth
            
            offset = 8  # Skip OUI + type + version
            
            # Group cipher
            offset += 4
            
            # Pairwise cipher count
            if offset + 2 <= len(data):
                count = data[offset] | (data[offset + 1] << 8)
                offset += 2
                
                ciphers = []
                for _ in range(count):
                    if offset + 4 <= len(data):
                        cipher_suite = data[offset:offset + 4]
                        if cipher_suite[-1] == 4:
                            ciphers.append('CCMP')
                        elif cipher_suite[-1] == 2:
                            ciphers.append('TKIP')
                        offset += 4
                cipher = ' '.join(ciphers)
            
            # AKM count
            if offset + 2 <= len(data):
                akm_count = data[offset] | (data[offset + 1] << 8)
                offset += 2
                
                akms = []
                for _ in range(akm_count):
                    if offset + 4 <= len(data):
                        akm_suite = data[offset:offset + 4]
                        if akm_suite[-1] == 2:
                            akms.append('PSK')
                        elif akm_suite[-1] == 1:
                            akms.append('MGT')
                        offset += 4
                auth = ' '.join(akms)
                
        except (AttributeError, TypeError, IndexError):
            pass

        return cipher, auth

    def _check_wps_locked(self, data: bytes) -> bool:
        """Check if WPS is locked from vendor IE."""
        try:
            # Look for AP Setup Locked attribute (0x1057)
            offset = 4  # Skip vendor OUI
            while offset + 4 <= len(data):
                attr_type = (data[offset] << 8) | data[offset + 1]
                attr_len = (data[offset + 2] << 8) | data[offset + 3]
                offset += 4
                
                if attr_type == 0x1057 and attr_len >= 1:  # AP Setup Locked
                    return data[offset] == 0x01
                
                offset += attr_len
        except (AttributeError, TypeError, IndexError):
            pass
        return False

    def get_targets(self) -> List[AccessPoint]:
        """Get list of discovered access points."""
        with self._lock:
            return list(self.access_points.values())
    
    def get_clients(self) -> List[Client]:
        """Get list of discovered clients."""
        with self._lock:
            return list(self.clients.values())
    
    def get_stats(self) -> dict:
        """Get scanner statistics."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        hopper_stats = self.hopper.get_stats() if self.hopper else {}
        
        with self._lock:
            return {
                'access_points': len(self.access_points),
                'clients': len(self.clients),
                'packets_processed': self.packets_processed,
                'elapsed_time': elapsed,
                'packets_per_second': self.packets_processed / elapsed if elapsed > 0 else 0,
                **hopper_stats
            }


# Convenience functions
def create_channel_hopper(interface: str, band: str = '2.4') -> ChannelHopper:
    """Create and return a channel hopper."""
    return ChannelHopper(interface, band=band)


def scan_networks(interface: str, duration: int = 30, band: str = '2.4') -> List[AccessPoint]:
    """
    Scan for WiFi networks.
    
    Args:
        interface: Monitor mode interface
        duration: Scan duration in seconds
        band: '2.4', '5', or 'all'
        
    Returns:
        List of discovered AccessPoint objects
    """
    scanner = NativeScanner(interface, band=band)
    scanner.start()
    time.sleep(duration)
    targets = scanner.get_targets()
    scanner.stop()
    return targets


def is_available() -> bool:
    """Check if native scanner is available."""
    return SCAPY_AVAILABLE
