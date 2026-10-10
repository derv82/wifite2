#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Honeypot / Rogue AP detector for wifite2.

Identifies potentially fake access points by analysing:
  1. Beacon rate anomalies  – legitimate APs send ~10 beacons/sec;
     software APs (hostapd, airbase-ng) often burst at much higher rates.
  2. Duplicate ESSIDs        – multiple BSSIDs advertising the same ESSID
     on different channels or with different encryption is suspicious.
  3. Signal-strength outliers – a "twin" AP with significantly stronger
     signal than a known network may be an Evil Twin.

Each target receives a *honeypot_score* (0-100) and a list of human-readable
*honeypot_reasons*.  A score >= 50 is considered "suspicious".
"""

from ..util.logger import log_debug


# --- Thresholds (tunable) ---------------------------------------------------
BEACON_RATE_HIGH = 25       # beacons/sec – anything above this is unusual
BEACON_RATE_VERY_HIGH = 50  # almost certainly software-generated
MIN_OBSERVATION_SECS = 3    # ignore targets observed < this many seconds
SIGNAL_DIFF_THRESHOLD = 15  # dB difference to flag a stronger twin
DUPLICATE_ESSID_MIN = 2     # minimum BSSIDs sharing an ESSID to flag


class HoneypotDetector:
    """Stateless analyser – call ``analyse(targets)`` after each scan cycle."""

    @staticmethod
    def analyse(targets):
        """Score every target in *targets* for honeypot likelihood.

        Mutates each target in-place, setting:
            target.honeypot_score   (int, 0-100)
            target.honeypot_reasons (list[str])

        Args:
            targets: list of Target objects (must have bssid, essid,
                     essid_known, beacons, first_seen, channel, power).
        """
        # Build ESSID -> [target, ...] index for duplicate detection
        essid_groups = {}
        for t in targets:
            if t.essid_known and t.essid:
                essid_groups.setdefault(t.essid, []).append(t)

        for t in targets:
            score = 0
            reasons = []

            # --- 1. Beacon rate analysis ------------------------------------
            beacon_rate = HoneypotDetector._beacon_rate(t)
            if beacon_rate is not None:
                if beacon_rate >= BEACON_RATE_VERY_HIGH:
                    score += 40
                    reasons.append(f'Very high beacon rate ({beacon_rate:.0f}/s)')
                elif beacon_rate >= BEACON_RATE_HIGH:
                    score += 20
                    reasons.append(f'High beacon rate ({beacon_rate:.0f}/s)')

            # --- 2. Duplicate ESSID detection --------------------------------
            if t.essid_known and t.essid:
                group = essid_groups.get(t.essid, [])
                if len(group) >= DUPLICATE_ESSID_MIN:
                    # Check for different channels or encryption among twins
                    channels = {g.channel for g in group}
                    encryptions = {g.encryption for g in group}
                    if len(channels) > 1 or len(encryptions) > 1:
                        score += 30
                        reasons.append(
                            f'Duplicate ESSID on {len(channels)} channel(s) '
                            f'with {len(encryptions)} encryption type(s) '
                            f'({len(group)} BSSIDs)'
                        )
                    elif len(group) >= 3:
                        # 3+ identical-config APs is also suspicious
                        score += 15
                        reasons.append(
                            f'{len(group)} APs share ESSID "{t.essid}"'
                        )

            # --- 3. Signal strength outlier among twins ----------------------
            if t.essid_known and t.essid:
                group = essid_groups.get(t.essid, [])
                if len(group) >= DUPLICATE_ESSID_MIN:
                    avg_power = sum(g.power for g in group) / len(group)
                    if t.power - avg_power >= SIGNAL_DIFF_THRESHOLD:
                        score += 20
                        reasons.append(
                            f'Signal ({t.power} dB) much stronger than '
                            f'twin average ({avg_power:.0f} dB)'
                        )

            # Clamp score
            t.honeypot_score = min(score, 100)
            t.honeypot_reasons = reasons

            if score >= 50:
                log_debug('HoneypotDetector',
                          f'{t.bssid} score={score}: {"; ".join(reasons)}')

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _beacon_rate(target):
        """Return beacons-per-second, or None if not enough data."""
        first = getattr(target, 'first_seen', None)
        last = getattr(target, 'last_seen', None)
        beacons = getattr(target, 'beacons', 0)

        if first is None or last is None or beacons <= 0:
            return None

        elapsed = last - first
        if elapsed < MIN_OBSERVATION_SECS:
            return None

        return beacons / elapsed
