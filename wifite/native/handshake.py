#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Scapy-based WPA/WPA2 handshake verification.

Replaces 'tshark' for handshake capture validation with native Python/Scapy.

Usage:
    from wifite.native.handshake import ScapyHandshake
    
    # Check if capture file contains valid handshake
    bssids = ScapyHandshake.bssids_with_handshakes('capture.cap')
    
    # Check for specific BSSID
    has_hs = ScapyHandshake.has_handshake('capture.cap', 'AA:BB:CC:DD:EE:FF')
    
    # Get detailed handshake info
    info = ScapyHandshake.get_handshake_info('capture.cap', 'AA:BB:CC:DD:EE:FF')

WPA 4-Way Handshake:
    Message 1: AP -> Client (ANonce)
    Message 2: Client -> AP (SNonce + MIC)
    Message 3: AP -> Client (GTK + MIC)
    Message 4: Client -> AP (ACK)
    
A valid handshake requires all 4 messages between the same AP and client,
in sequential order.
"""

import os
from typing import Optional, List, Dict, Set, Tuple
from collections import defaultdict

try:
    from scapy.all import (
        rdpcap, EAPOL, Dot11, Dot11Beacon, Dot11ProbeResp,
        Dot11Elt, Raw, conf as scapy_conf
    )
    SCAPY_AVAILABLE = True
except (ImportError, AttributeError):
    SCAPY_AVAILABLE = False


class ScapyHandshake:
    """
    Native handshake verification using Scapy.
    
    Advantages over tshark:
    - No external process spawning
    - Direct packet access
    - More detailed analysis possible
    - Consistent across platforms
    """
    
    # EAPOL key info flags
    KEY_INFO_INSTALL = 0x0040
    KEY_INFO_ACK = 0x0080
    KEY_INFO_MIC = 0x0100
    KEY_INFO_SECURE = 0x0200
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Scapy is available."""
        return SCAPY_AVAILABLE
    
    @classmethod
    def bssids_with_handshakes(cls, 
                                capfile: str, 
                                bssid: Optional[str] = None) -> List[str]:
        """
        Find all BSSIDs with valid 4-way handshakes in a capture file.
        
        Args:
            capfile: Path to pcap/cap file
            bssid: Optional filter for specific BSSID
            
        Returns:
            List of BSSIDs with valid handshakes
        """
        if not SCAPY_AVAILABLE:
            return []
        
        if not os.path.exists(capfile):
            return []
        
        try:
            # Parse the capture file
            handshakes = cls._extract_handshakes(capfile, bssid)
            
            # Find BSSIDs with complete handshakes
            valid_bssids = set()
            for (target, client), messages in handshakes.items():
                if cls._is_complete_handshake(messages):
                    valid_bssids.add(target)
            
            return list(valid_bssids)
            
        except Exception as e:
            return []
    
    @classmethod
    def has_handshake(cls, capfile: str, bssid: str) -> bool:
        """
        Check if capture file contains a valid handshake for specific BSSID.
        
        Args:
            capfile: Path to pcap/cap file
            bssid: Target BSSID to check
            
        Returns:
            True if valid handshake found
        """
        bssids = cls.bssids_with_handshakes(capfile, bssid)
        return bssid.upper() in [b.upper() for b in bssids]
    
    @classmethod
    def get_handshake_info(cls, 
                           capfile: str, 
                           bssid: Optional[str] = None) -> List[Dict]:
        """
        Get detailed handshake information from capture file.
        
        Args:
            capfile: Path to pcap/cap file
            bssid: Optional filter for specific BSSID
            
        Returns:
            List of dicts with handshake details
        """
        if not SCAPY_AVAILABLE:
            return []
        
        if not os.path.exists(capfile):
            return []
        
        try:
            handshakes = cls._extract_handshakes(capfile, bssid)
            
            results = []
            for (target, client), messages in handshakes.items():
                is_complete = cls._is_complete_handshake(messages)
                results.append({
                    'bssid': target,
                    'client': client,
                    'messages': sorted(list(messages)),
                    'complete': is_complete,
                    'message_count': len(messages),
                })
            
            return results

        except (OSError, AttributeError):
            return []
    
    @classmethod
    def _extract_handshakes(cls, 
                            capfile: str, 
                            bssid_filter: Optional[str] = None) -> Dict[Tuple[str, str], Set[int]]:
        """
        Extract EAPOL handshake messages from capture file.
        
        Args:
            capfile: Path to pcap/cap file
            bssid_filter: Optional BSSID to filter
            
        Returns:
            Dict mapping (bssid, client) -> set of message numbers (1-4)
        """
        # Disable Scapy warnings for missing dissectors
        old_verb = scapy_conf.verb
        scapy_conf.verb = 0
        
        try:
            packets = rdpcap(capfile)
        finally:
            scapy_conf.verb = old_verb
        
        # Map of (target_bssid, client_mac) -> set of handshake message numbers
        handshakes = defaultdict(set)
        
        # Track message sequence for proper ordering
        last_message = {}  # (target, client) -> last message number
        
        for pkt in packets:
            # Check for EAPOL layer
            if not pkt.haslayer(EAPOL):
                continue
            
            # Get Dot11 layer for MAC addresses
            if not pkt.haslayer(Dot11):
                continue
            
            dot11 = pkt.getlayer(Dot11)
            eapol = pkt.getlayer(EAPOL)
            
            # EAPOL-Key frames have type 3
            if eapol.type != 3:
                continue
            
            # Need the raw payload for key info
            if not pkt.haslayer(Raw):
                continue
            
            # Extract key info from EAPOL-Key frame
            # Key info is at offset 5 in EAPOL-Key (after type, key_descriptor_type, key_len)
            try:
                raw_data = bytes(pkt.getlayer(Raw))
                if len(raw_data) < 7:
                    continue
                
                # EAPOL-Key format: key_descriptor_type(1) + key_info(2) + key_len(2) + ...
                key_info = (raw_data[1] << 8) | raw_data[2]

            except (UnicodeDecodeError, AttributeError):
                continue
            
            # Determine message number from key info flags
            # Msg 1: ACK=1, MIC=0, INSTALL=0, SECURE=0
            # Msg 2: ACK=0, MIC=1, INSTALL=0, SECURE=0
            # Msg 3: ACK=1, MIC=1, INSTALL=1, SECURE=1
            # Msg 4: ACK=0, MIC=1, INSTALL=0, SECURE=1
            
            ack = bool(key_info & cls.KEY_INFO_ACK)
            mic = bool(key_info & cls.KEY_INFO_MIC)
            install = bool(key_info & cls.KEY_INFO_INSTALL)
            secure = bool(key_info & cls.KEY_INFO_SECURE)
            
            msg_num = cls._determine_message_number(ack, mic, install, secure)
            if msg_num == 0:
                continue
            
            # Determine target (AP) and client based on message direction
            # Messages 1, 3: AP -> Client (src=AP, dst=Client)
            # Messages 2, 4: Client -> AP (src=Client, dst=AP)
            
            src = dot11.addr2  # Source
            dst = dot11.addr1  # Destination
            bssid = dot11.addr3  # BSSID (usually AP)
            
            if not src or not dst or not bssid:
                continue
            
            src = src.upper()
            dst = dst.upper()
            bssid = bssid.upper()
            
            if msg_num in (1, 3):
                # AP -> Client
                target = src
                client = dst
            else:
                # Client -> AP
                target = dst
                client = src
            
            # Validate BSSID matches
            if target != bssid and target != 'FF:FF:FF:FF:FF:FF':
                # Use BSSID if target doesn't match
                target = bssid
            
            # Apply filter if specified
            if bssid_filter and target.upper() != bssid_filter.upper():
                continue
            
            key = (target, client)
            
            # Check for proper message ordering
            last = last_message.get(key, 0)
            
            if msg_num == 1:
                # Message 1 can start or restart a handshake
                handshakes[key] = {1}
                last_message[key] = 1
            elif msg_num == last + 1:
                # Messages must be sequential
                handshakes[key].add(msg_num)
                last_message[key] = msg_num
            elif msg_num > last:
                # Out of order - might be retransmission, add it anyway
                handshakes[key].add(msg_num)
            # else: duplicate or earlier message - ignore
        
        return dict(handshakes)
    
    @classmethod
    def _determine_message_number(cls, ack: bool, mic: bool, install: bool, secure: bool) -> int:
        """
        Determine handshake message number from key info flags.
        
        Returns:
            Message number (1-4) or 0 if unknown
        """
        if ack and not mic and not install and not secure:
            return 1
        elif not ack and mic and not install and not secure:
            return 2
        elif ack and mic and install and secure:
            return 3
        elif not ack and mic and not install and secure:
            return 4
        else:
            # Unknown combination - try to guess
            if ack and not mic:
                return 1
            elif mic and install:
                return 3
            elif mic and secure and not install and not ack:
                return 4
            elif mic and not secure:
                return 2
            return 0
    
    @classmethod
    def _is_complete_handshake(cls, messages: Set[int]) -> bool:
        """
        Check if a set of messages forms a complete handshake.
        
        A valid handshake requires all 4 messages.
        """
        return messages == {1, 2, 3, 4}
    
    @classmethod
    def get_essid(cls, capfile: str, bssid: str) -> Optional[str]:
        """
        Extract ESSID for a BSSID from beacon/probe response frames.
        
        Args:
            capfile: Path to pcap/cap file
            bssid: Target BSSID
            
        Returns:
            ESSID string or None if not found
        """
        if not SCAPY_AVAILABLE:
            return None
        
        if not os.path.exists(capfile):
            return None
        
        try:
            old_verb = scapy_conf.verb
            scapy_conf.verb = 0
            
            try:
                packets = rdpcap(capfile)
            finally:
                scapy_conf.verb = old_verb
            
            bssid = bssid.upper()
            
            for pkt in packets:
                # Check for beacon or probe response
                if not (pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp)):
                    continue
                
                if not pkt.haslayer(Dot11):
                    continue
                
                dot11 = pkt.getlayer(Dot11)
                
                # Check BSSID
                pkt_bssid = (dot11.addr3 or '').upper()
                if pkt_bssid != bssid:
                    continue
                
                # Extract ESSID from information elements
                elt = pkt.getlayer(Dot11Elt)
                while elt:
                    if elt.ID == 0:  # SSID element
                        try:
                            essid = elt.info.decode('utf-8', errors='replace')
                            if essid:
                                return essid
                        except (UnicodeDecodeError, AttributeError):
                            pass
                    elt = elt.payload.getlayer(Dot11Elt) if hasattr(elt.payload, 'getlayer') else None

            return None

        except (OSError, AttributeError):
            return None


# Convenience functions
def has_handshake(capfile: str, bssid: str) -> bool:
    """Check if capture has valid handshake for BSSID."""
    return ScapyHandshake.has_handshake(capfile, bssid)


def bssids_with_handshakes(capfile: str, bssid: Optional[str] = None) -> List[str]:
    """Get list of BSSIDs with valid handshakes."""
    return ScapyHandshake.bssids_with_handshakes(capfile, bssid)


def is_available() -> bool:
    """Check if native handshake verification is available."""
    return SCAPY_AVAILABLE
