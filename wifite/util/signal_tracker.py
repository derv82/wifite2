#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Signal strength history tracking and analysis.

Tracks signal strength over time for targets and clients,
providing trend analysis for attack optimization.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import time


@dataclass
class SignalSample:
    """Single signal strength measurement."""
    timestamp: float
    power: int  # dBm (e.g., -65)

    @property
    def age(self) -> float:
        """Seconds since this sample was taken."""
        return time.time() - self.timestamp


@dataclass
class SignalHistory:
    """
    Tracks signal strength history for a single entity (AP or client).

    Maintains a rolling window of signal samples for trend analysis
    and attack timing optimization.
    """
    bssid: str
    max_samples: int = 60  # Keep last 60 samples (1 per second = 1 minute)
    samples: deque = field(default_factory=lambda: deque(maxlen=60))

    def __post_init__(self):
        # Ensure deque has correct maxlen
        self.samples = deque(maxlen=self.max_samples)

    def add_sample(self, power: int) -> None:
        """Add a new signal strength sample."""
        self.samples.append(SignalSample(time.time(), power))

    @property
    def current(self) -> Optional[int]:
        """Get most recent signal strength."""
        return self.samples[-1].power if self.samples else None

    @property
    def average(self) -> Optional[float]:
        """Calculate average signal strength."""
        if not self.samples:
            return None
        return sum(s.power for s in self.samples) / len(self.samples)

    @property
    def max_power(self) -> Optional[int]:
        """Get maximum signal strength seen."""
        if not self.samples:
            return None
        return max(s.power for s in self.samples)

    @property
    def min_power(self) -> Optional[int]:
        """Get minimum signal strength seen."""
        if not self.samples:
            return None
        return min(s.power for s in self.samples)

    @property
    def variance(self) -> Optional[float]:
        """Calculate signal variance (stability indicator)."""
        if len(self.samples) < 2:
            return None
        avg = self.average
        return sum((s.power - avg) ** 2 for s in self.samples) / len(self.samples)

    @property
    def trend(self) -> str:
        """
        Determine signal trend: 'improving', 'degrading', or 'stable'.

        Uses simple linear regression on recent samples.
        """
        if len(self.samples) < 5:
            return 'unknown'

        # Use last 10 samples for trend
        recent = list(self.samples)[-10:]
        n = len(recent)

        # Calculate slope using simple linear regression
        x_sum = sum(range(n))
        y_sum = sum(s.power for s in recent)
        xy_sum = sum(i * recent[i].power for i in range(n))
        x2_sum = sum(i * i for i in range(n))

        denominator = n * x2_sum - x_sum * x_sum
        if denominator == 0:
            return 'stable'

        slope = (n * xy_sum - x_sum * y_sum) / denominator

        # Threshold for trend detection (dB per sample)
        if slope > 0.5:
            return 'improving'
        elif slope < -0.5:
            return 'degrading'
        else:
            return 'stable'

    def is_stable(self, threshold: float = 5.0) -> bool:
        """Check if signal is stable (low variance)."""
        var = self.variance
        return var is not None and var < threshold

    def get_optimal_window(self, window_seconds: int = 10) -> Optional[Tuple[float, float]]:
        """
        Find the time window with best average signal.

        Useful for timing attacks when signal is strongest.

        Args:
            window_seconds: Size of window to search

        Returns:
            Tuple of (start_time, average_power) or None
        """
        if len(self.samples) < window_seconds:
            return None
        
        best_avg = float('-inf')
        best_start = None
        
        samples_list = list(self.samples)
        for i in range(len(samples_list) - window_seconds + 1):
            window = samples_list[i:i + window_seconds]
            avg = sum(s.power for s in window) / window_seconds
            if avg > best_avg:
                best_avg = avg
                best_start = window[0].timestamp
        
        return (best_start, best_avg) if best_start else None


class SignalTracker:
    """
    Tracks signal strength for multiple APs and clients.
    
    Provides centralized signal monitoring for attack optimization,
    target selection, and client tracking.
    """
    
    def __init__(self, max_samples: int = 60):
        self.max_samples = max_samples
        self.aps: Dict[str, SignalHistory] = {}
        self.clients: Dict[str, SignalHistory] = {}
    
    def update_ap(self, bssid: str, power: int) -> None:
        """Update signal strength for an AP."""
        if bssid not in self.aps:
            self.aps[bssid] = SignalHistory(bssid, self.max_samples)
        self.aps[bssid].add_sample(power)
    
    def update_client(self, mac: str, power: int) -> None:
        """Update signal strength for a client."""
        if mac not in self.clients:
            self.clients[mac] = SignalHistory(mac, self.max_samples)
        self.clients[mac].add_sample(power)
    
    def get_ap_history(self, bssid: str) -> Optional[SignalHistory]:
        """Get signal history for an AP."""
        return self.aps.get(bssid)
    
    def get_client_history(self, mac: str) -> Optional[SignalHistory]:
        """Get signal history for a client."""
        return self.clients.get(mac)
    
    def get_best_targets(self, min_power: int = -70, 
                         require_stable: bool = False) -> List[str]:
        """
        Get list of APs with good, stable signal.
        
        Args:
            min_power: Minimum average signal strength
            require_stable: Only return APs with stable signal
            
        Returns:
            List of BSSIDs sorted by signal strength (best first)
        """
        candidates = []
        
        for bssid, history in self.aps.items():
            avg = history.average
            if avg is None or avg < min_power:
                continue
            if require_stable and not history.is_stable():
                continue
            candidates.append((bssid, avg))
        
        # Sort by average signal strength (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [bssid for bssid, _ in candidates]
    
    def get_active_clients(self, max_age_seconds: int = 30) -> List[str]:
        """
        Get list of clients that have been seen recently.
        
        Args:
            max_age_seconds: Maximum age of last sample
            
        Returns:
            List of client MACs
        """
        active = []
        now = time.time()
        
        for mac, history in self.clients.items():
            if history.samples:
                age = now - history.samples[-1].timestamp
                if age <= max_age_seconds:
                    active.append(mac)
        
        return active
    
    def should_attack_now(self, bssid: str, 
                          min_power: int = -75,
                          prefer_stable: bool = True) -> Tuple[bool, str]:
        """
        Determine if now is a good time to attack a target.
        
        Args:
            bssid: Target BSSID
            min_power: Minimum signal strength
            prefer_stable: Prefer attacking during stable signal
            
        Returns:
            Tuple of (should_attack, reason)
        """
        history = self.aps.get(bssid)
        
        if not history or not history.samples:
            return False, "No signal data available"
        
        current = history.current
        if current < min_power:
            return False, f"Signal too weak ({current} dBm < {min_power} dBm)"
        
        trend = history.trend
        
        if trend == 'improving':
            return True, "Signal improving - good time to attack"
        
        if trend == 'degrading':
            return False, "Signal degrading - wait for better conditions"
        
        if prefer_stable and not history.is_stable():
            return False, "Signal unstable - wait for stable conditions"
        
        return True, "Signal stable and strong"
    
    def cleanup_stale(self, max_age_seconds: int = 300) -> int:
        """
        Remove entries that haven't been updated recently.
        
        Args:
            max_age_seconds: Maximum age before removal
            
        Returns:
            Number of entries removed
        """
        now = time.time()
        removed = 0
        
        # Clean up APs
        stale_aps = []
        for bssid, history in self.aps.items():
            if history.samples:
                age = now - history.samples[-1].timestamp
                if age > max_age_seconds:
                    stale_aps.append(bssid)
        
        for bssid in stale_aps:
            del self.aps[bssid]
            removed += 1
        
        # Clean up clients
        stale_clients = []
        for mac, history in self.clients.items():
            if history.samples:
                age = now - history.samples[-1].timestamp
                if age > max_age_seconds:
                    stale_clients.append(mac)
        
        for mac in stale_clients:
            del self.clients[mac]
            removed += 1
        
        return removed
    
    def get_summary(self) -> Dict:
        """Get summary statistics for all tracked entities."""
        ap_summary = {}
        for bssid, history in self.aps.items():
            ap_summary[bssid] = {
                'current': history.current,
                'average': history.average,
                'max': history.max_power,
                'min': history.min_power,
                'trend': history.trend,
                'stable': history.is_stable(),
                'samples': len(history.samples)
            }
        
        client_summary = {}
        for mac, history in self.clients.items():
            client_summary[mac] = {
                'current': history.current,
                'average': history.average,
                'trend': history.trend,
                'samples': len(history.samples)
            }
        
        return {
            'aps': ap_summary,
            'clients': client_summary,
            'total_aps': len(self.aps),
            'total_clients': len(self.clients)
        }


# Global signal tracker instance
_global_tracker: Optional[SignalTracker] = None


def get_signal_tracker() -> SignalTracker:
    """Get or create the global signal tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = SignalTracker()
    return _global_tracker


def reset_signal_tracker() -> None:
    """Reset the global signal tracker (useful for testing)."""
    global _global_tracker
    _global_tracker = None
