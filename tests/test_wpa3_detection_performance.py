#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Performance benchmark for WPA3 detection optimization.

This test demonstrates the performance improvements from caching
and efficient parsing.
"""

import unittest
from wifite.model.target import Target
from wifite.util.wpa3 import WPA3Detector


class TestWPA3DetectionPerformance(unittest.TestCase):
    """Performance benchmarks for WPA3 detection."""

    def setUp(self):
        """Create test targets."""
        # WPA3 transition mode target
        self.wpa3_transition_fields = [
            'AA:BB:CC:DD:EE:FF',
            '2024-01-01 00:00:00',
            '2024-01-01 00:00:01',
            '6',
            '54',
            'WPA2 WPA3',
            'CCMP',
            'PSK SAE',
            '-50',
            '10',
            '0',
            '0.0.0.0',
            '8',
            'TestNet',
            ''
        ]
        
        # WPA2-only target
        self.wpa2_only_fields = [
            'BB:BB:CC:DD:EE:FF',
            '2024-01-01 00:00:00',
            '2024-01-01 00:00:01',
            '6',
            '54',
            'WPA2',
            'CCMP',
            'PSK',
            '-50',
            '10',
            '0',
            '0.0.0.0',
            '8',
            'TestNet2',
            ''
        ]

    def test_cache_short_circuits_detection(self):
        """Cached detection returns the stored result without recomputing.

        Behavioural check (deterministic, not timing-based): when a target
        already carries a ``wpa3_info`` cache, ``use_cache=True`` must return
        that cached value verbatim, while ``use_cache=False`` must ignore the
        cache and recompute from the target's encryption fields. We prove this
        by seeding the cache with a sentinel that deliberately disagrees with
        what the fields would produce.
        """
        from wifite.util.wpa3 import WPA3Info

        target = Target(self.wpa3_transition_fields)

        # What a fresh (uncached) detection derives from the fields.
        fresh = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        self.assertTrue(fresh['has_wpa3'],
                        'Fixture should detect WPA3 from the encryption fields')

        # Seed the cache with a sentinel that disagrees with the fields, so a
        # cache hit is distinguishable from a recompute.
        sentinel = WPA3Info.from_dict({
            'has_wpa3': False,
            'has_wpa2': True,
            'is_transition': False,
            'pmf_status': WPA3Detector.PMF_DISABLED,
            'sae_groups': [],
            'dragonblood_vulnerable': False,
        })
        target.wpa3_info = sentinel

        # Cache hit: must return the sentinel, proving detection was skipped.
        cached = WPA3Detector.detect_wpa3_capability(target, use_cache=True)
        self.assertEqual(cached, sentinel.to_dict(),
                         'Cached path must return the stored wpa3_info verbatim')
        self.assertFalse(cached['has_wpa3'],
                         'Cached path must not recompute from the fields')

        # Cache bypass: must recompute and match the fresh detection.
        recomputed = WPA3Detector.detect_wpa3_capability(target, use_cache=False)
        self.assertEqual(recomputed, fresh,
                         'use_cache=False must ignore the cache and recompute')
        self.assertTrue(recomputed['has_wpa3'])

    def test_early_return_for_wpa2_only(self):
        """WPA2-only targets take the early-return branch (no WPA3 work).

        Behavioural check (deterministic): a target whose fields advertise no
        WPA3/SAE must short-circuit to the WPA2-only result shape, while a
        WPA3 transition target must go through full detection. This exercises
        the same early-return optimisation the old benchmark targeted, without
        asserting on wall-clock time.
        """
        wpa2 = WPA3Detector.detect_wpa3_capability(
            Target(self.wpa2_only_fields), use_cache=False)
        wpa3 = WPA3Detector.detect_wpa3_capability(
            Target(self.wpa3_transition_fields), use_cache=False)

        # Early-return branch: WPA2-only, not transition, no SAE groups.
        self.assertFalse(wpa2['has_wpa3'])
        self.assertFalse(wpa2['is_transition'])
        self.assertEqual(wpa2['sae_groups'], [])
        self.assertFalse(wpa2['dragonblood_vulnerable'])

        # Full-detection branch still flags WPA3.
        self.assertTrue(wpa3['has_wpa3'])

    def test_helper_methods_use_cache(self):
        """Helper methods read cached wpa3_info instead of recomputing.

        Deterministic check: seed the cache with a sentinel that disagrees
        with the target's fields, then confirm each helper returns the cached
        value. Clearing the cache makes them recompute from the fields.
        """
        from wifite.util.wpa3 import WPA3Info

        target = Target(self.wpa3_transition_fields)

        sentinel = WPA3Info.from_dict({
            'has_wpa3': True,
            'has_wpa2': True,
            'is_transition': False,            # disagrees with the fields
            'pmf_status': WPA3Detector.PMF_REQUIRED,
            'sae_groups': [21],                # not the default [19]
            'dragonblood_vulnerable': False,
        })
        target.wpa3_info = sentinel

        # Cache hit: helpers return the sentinel's values.
        self.assertEqual(WPA3Detector.identify_transition_mode(target),
                         sentinel.is_transition)
        self.assertEqual(WPA3Detector.check_pmf_status(target),
                         sentinel.pmf_status)
        self.assertEqual(WPA3Detector.get_supported_sae_groups(target),
                         sentinel.sae_groups)

        # Cache cleared: helpers recompute from the fields (transition mode).
        target.wpa3_info = None
        self.assertTrue(WPA3Detector.identify_transition_mode(target))


if __name__ == '__main__':
    unittest.main()
