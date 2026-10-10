#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Native beacon frame generator for creating fake APs.

Replaces the need for hostapd in simple rogue AP scenarios using Scapy.
Useful for testing and lightweight Evil Twin implementations.

Usage:
    from wifite.native.beacon import BeaconGenerator
    
    # Create simple fake AP
    beacon = BeaconGenerator('wlan0mon', 'FakeNetwork', channel=6)
    beacon.start()
    # ... do attack ...
    beacon.stop()

Note: For production Evil Twin attacks, hostapd is still recommended
as it provides full AP functionality including association handling.
"""

import time
import secrets
from threading import Thread, Event
from typing import Optional

try:
    from scapy.all import (
        RadioTap, Dot11, Dot11Beacon, Dot11Elt, Dot11ProbeResp,
        sendp, sniff, conf as scapy_conf
    )
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


class BeaconGenerator(Thread):
    """
    Native beacon frame generator using Scapy.
    
    Creates and broadcasts beacon frames to simulate an access point.
    This is useful for:
    - Testing client behavior
    - Simple rogue AP scenarios
    - Deauth attack validation
    
    Limitations vs hostapd:
    - Cannot handle client associations
    - No DHCP/DNS services
    - No actual network connectivity
    """
    
    # Capability flags
    CAP_ESS = 0x0001        # Infrastructure mode
    CAP_PRIVACY = 0x0010    # WPA/WPA2 enabled
    CAP_SHORT_SLOT = 0x0400 # Short slot time
    
    # Beacon interval (in TUs, 1 TU = 1024 microseconds)
    DEFAULT_BEACON_INTERVAL = 100  # ~102.4ms
    
    def __init__(self,
                 interface: str,
                 essid: str,
                 bssid: Optional[str] = None,
                 channel: int = 6,
                 encryption: str = 'WPA2',
                 beacon_interval: int = DEFAULT_BEACON_INTERVAL,
                 respond_to_probes: bool = True):
        """
        Initialize beacon generator.
        
        Args:
            interface: Monitor mode interface
            essid: Network name to broadcast
            bssid: BSSID to use (None = random)
            channel: Channel to broadcast on
            encryption: 'OPEN', 'WEP', 'WPA', 'WPA2', 'WPA3'
            beacon_interval: Beacon interval in TUs
            respond_to_probes: Respond to probe requests
        """
        super().__init__()
        self.daemon = True
        
        self.interface = interface
        self.essid = essid
        self.bssid = bssid or self._generate_random_bssid()
        self.channel = channel
        self.encryption = encryption.upper()
        self.beacon_interval = beacon_interval
        self.respond_to_probes = respond_to_probes
        
        self._stop_event = Event()
        
        # Statistics
        self.beacons_sent = 0
        self.probes_responded = 0
        self.start_time = None
        
        # Build beacon frame
        self._beacon_frame = self._build_beacon_frame()
    
    def _generate_random_bssid(self) -> str:
        """Generate a random valid BSSID."""
        # Use locally administered, unicast MAC
        first_byte = secrets.token_bytes(1)[0] & 0xFC | 0x02
        rest = list(secrets.token_bytes(5))
        return ':'.join(f'{b:02X}' for b in [first_byte] + rest)
    
    def _build_beacon_frame(self):
        """Build the beacon frame with all required elements."""
        # Determine capabilities
        cap = self.CAP_ESS | self.CAP_SHORT_SLOT
        if self.encryption != 'OPEN':
            cap |= self.CAP_PRIVACY
        
        # Build base beacon
        beacon = (
            RadioTap() /
            Dot11(
                type=0,
                subtype=8,
                addr1='FF:FF:FF:FF:FF:FF',  # Broadcast
                addr2=self.bssid,            # Source (AP)
                addr3=self.bssid             # BSSID
            ) /
            Dot11Beacon(
                cap=cap,
                beacon_interval=self.beacon_interval
            )
        )
        
        # Add SSID
        beacon = beacon / Dot11Elt(ID=0, info=self.essid.encode())
        
        # Add supported rates
        rates = b'\x82\x84\x8b\x96\x0c\x12\x18\x24'  # 1, 2, 5.5, 11, 6, 9, 12, 18 Mbps
        beacon = beacon / Dot11Elt(ID=1, info=rates)
        
        # Add channel
        beacon = beacon / Dot11Elt(ID=3, info=bytes([self.channel]))
        
        # Add extended rates
        ext_rates = b'\x30\x48\x60\x6c'  # 24, 36, 48, 54 Mbps
        beacon = beacon / Dot11Elt(ID=50, info=ext_rates)
        
        # Add encryption-specific IEs
        if self.encryption == 'WPA':
            beacon = beacon / self._build_wpa_ie()
        elif self.encryption == 'WPA2':
            beacon = beacon / self._build_rsn_ie()
        elif self.encryption == 'WPA3':
            beacon = beacon / self._build_rsn_ie(wpa3=True)
        elif self.encryption == 'WEP':
            # WEP doesn't need additional IEs, just the privacy bit
            pass
        
        return beacon
    
    def _build_wpa_ie(self):
        """Build WPA Information Element."""
        # WPA IE (vendor-specific)
        wpa_ie = bytes([
            0x00, 0x50, 0xf2, 0x01,  # WPA OUI + type
            0x01, 0x00,              # Version 1
            0x00, 0x50, 0xf2, 0x04,  # Group cipher: CCMP
            0x01, 0x00,              # Pairwise cipher count
            0x00, 0x50, 0xf2, 0x04,  # Pairwise cipher: CCMP
            0x01, 0x00,              # AKM count
            0x00, 0x50, 0xf2, 0x02,  # AKM: PSK
        ])
        return Dot11Elt(ID=221, info=wpa_ie)
    
    def _build_rsn_ie(self, wpa3: bool = False):
        """Build RSN (WPA2/WPA3) Information Element."""
        if wpa3:
            # WPA3-SAE
            rsn_ie = bytes([
                0x01, 0x00,              # Version 1
                0x00, 0x0f, 0xac, 0x04,  # Group cipher: CCMP
                0x01, 0x00,              # Pairwise cipher count
                0x00, 0x0f, 0xac, 0x04,  # Pairwise cipher: CCMP
                0x01, 0x00,              # AKM count
                0x00, 0x0f, 0xac, 0x08,  # AKM: SAE
                0x00, 0xc0,              # RSN capabilities (MFP required)
            ])
        else:
            # WPA2-PSK
            rsn_ie = bytes([
                0x01, 0x00,              # Version 1
                0x00, 0x0f, 0xac, 0x04,  # Group cipher: CCMP
                0x01, 0x00,              # Pairwise cipher count
                0x00, 0x0f, 0xac, 0x04,  # Pairwise cipher: CCMP
                0x01, 0x00,              # AKM count
                0x00, 0x0f, 0xac, 0x02,  # AKM: PSK
                0x00, 0x00,              # RSN capabilities
            ])
        return Dot11Elt(ID=48, info=rsn_ie)
    
    def _build_probe_response(self, client_mac: str):
        """Build probe response frame for a specific client."""
        # Similar to beacon but as probe response
        cap = self.CAP_ESS | self.CAP_SHORT_SLOT
        if self.encryption != 'OPEN':
            cap |= self.CAP_PRIVACY
        
        response = (
            RadioTap() /
            Dot11(
                type=0,
                subtype=5,  # Probe Response
                addr1=client_mac,
                addr2=self.bssid,
                addr3=self.bssid
            ) /
            Dot11ProbeResp(
                cap=cap,
                beacon_interval=self.beacon_interval
            )
        )
        
        # Add same IEs as beacon
        response = response / Dot11Elt(ID=0, info=self.essid.encode())
        response = response / Dot11Elt(ID=1, info=b'\x82\x84\x8b\x96\x0c\x12\x18\x24')
        response = response / Dot11Elt(ID=3, info=bytes([self.channel]))
        response = response / Dot11Elt(ID=50, info=b'\x30\x48\x60\x6c')
        
        if self.encryption == 'WPA':
            response = response / self._build_wpa_ie()
        elif self.encryption in ('WPA2', 'WPA3'):
            response = response / self._build_rsn_ie(wpa3=(self.encryption == 'WPA3'))
        
        return response
    
    def run(self):
        """Main beacon transmission loop."""
        if not SCAPY_AVAILABLE:
            return
        
        self.start_time = time.time()
        
        # Calculate sleep time between beacons (TUs to seconds)
        sleep_time = self.beacon_interval * 1024 / 1000000
        
        # Start probe response handler if enabled
        if self.respond_to_probes:
            probe_thread = Thread(target=self._probe_response_handler, daemon=True)
            probe_thread.start()
        
        while not self._stop_event.is_set():
            try:
                sendp(self._beacon_frame, iface=self.interface, verbose=False)
                self.beacons_sent += 1
            except OSError:
                pass
            
            self._stop_event.wait(timeout=sleep_time)
    
    def _probe_response_handler(self):
        """Handle probe requests and send responses."""
        def process_probe(pkt):
            if self._stop_event.is_set():
                return
            
            if not pkt.haslayer(Dot11):
                return
            
            # Check for probe request (type 0, subtype 4)
            if pkt[Dot11].type != 0 or pkt[Dot11].subtype != 4:
                return
            
            # Extract client MAC
            client_mac = pkt[Dot11].addr2
            if not client_mac:
                return
            
            # Check if probe is for our SSID or broadcast
            try:
                elt = pkt.getlayer(Dot11Elt)
                while elt:
                    if elt.ID == 0:  # SSID
                        ssid = elt.info.decode('utf-8', errors='replace')
                        if ssid == '' or ssid == self.essid:
                            # Respond to broadcast or matching probe
                            response = self._build_probe_response(client_mac)
                            sendp(response, iface=self.interface, verbose=False)
                            self.probes_responded += 1
                        break
                    elt = elt.payload.getlayer(Dot11Elt) if hasattr(elt.payload, 'getlayer') else None
            except (UnicodeDecodeError, AttributeError):
                pass

        try:
            sniff(
                iface=self.interface,
                prn=process_probe,
                store=False,
                stop_filter=lambda _: self._stop_event.is_set()
            )
        except OSError:
            pass
    
    def stop(self):
        """Stop beacon transmission."""
        self._stop_event.set()
        if self.is_alive():
            self.join(timeout=2)
    
    def get_stats(self) -> dict:
        """Get transmission statistics."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'bssid': self.bssid,
            'essid': self.essid,
            'channel': self.channel,
            'encryption': self.encryption,
            'beacons_sent': self.beacons_sent,
            'probes_responded': self.probes_responded,
            'elapsed_time': elapsed,
            'beacons_per_second': self.beacons_sent / elapsed if elapsed > 0 else 0
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Scapy is available."""
        return SCAPY_AVAILABLE


def create_fake_ap(interface: str, essid: str, channel: int = 6, 
                   encryption: str = 'WPA2') -> BeaconGenerator:
    """
    Create and start a fake access point.
    
    Args:
        interface: Monitor mode interface
        essid: Network name
        channel: WiFi channel
        encryption: Security type
        
    Returns:
        BeaconGenerator instance (already started)
    """
    beacon = BeaconGenerator(interface, essid, channel=channel, encryption=encryption)
    beacon.start()
    return beacon


def is_available() -> bool:
    """Check if native beacon generation is available."""
    return SCAPY_AVAILABLE
