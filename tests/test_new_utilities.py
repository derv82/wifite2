#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for signal tracker and retry utilities.
"""

import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSignalTracker:
    """Tests for signal tracking functionality."""
    
    def test_import(self):
        """Test that signal_tracker module can be imported."""
        from wifite.util.signal_tracker import (
            SignalSample, SignalHistory, SignalTracker,
            get_signal_tracker, reset_signal_tracker
        )
        assert SignalSample is not None
        assert SignalHistory is not None
        assert SignalTracker is not None
    
    def test_signal_sample(self):
        """Test SignalSample dataclass."""
        from wifite.util.signal_tracker import SignalSample
        
        sample = SignalSample(timestamp=time.time(), power=-65)
        assert sample.power == -65
        assert sample.age >= 0
        assert sample.age < 1  # Should be very recent
    
    def test_signal_history_basic(self):
        """Test basic SignalHistory operations."""
        from wifite.util.signal_tracker import SignalHistory
        
        history = SignalHistory(bssid='AA:BB:CC:DD:EE:FF')
        
        # Initially empty
        assert history.current is None
        assert history.average is None
        
        # Add samples
        history.add_sample(-65)
        assert history.current == -65
        assert history.average == -65
        
        history.add_sample(-70)
        assert history.current == -70
        assert history.average == -67.5
    
    def test_signal_history_stats(self):
        """Test SignalHistory statistics."""
        from wifite.util.signal_tracker import SignalHistory
        
        history = SignalHistory(bssid='AA:BB:CC:DD:EE:FF')
        
        # Add multiple samples
        for power in [-60, -65, -70, -65, -60]:
            history.add_sample(power)
        
        assert history.max_power == -60
        assert history.min_power == -70
        assert history.average == -64.0
        assert history.variance is not None
    
    def test_signal_history_trend(self):
        """Test SignalHistory trend detection."""
        from wifite.util.signal_tracker import SignalHistory
        
        history = SignalHistory(bssid='AA:BB:CC:DD:EE:FF')
        
        # Not enough samples
        assert history.trend == 'unknown'
        
        # Add improving signal
        for power in range(-80, -50, 3):  # Getting stronger
            history.add_sample(power)
        
        assert history.trend == 'improving'
        
        # Create degrading signal
        history2 = SignalHistory(bssid='11:22:33:44:55:66')
        for power in range(-50, -80, -3):  # Getting weaker
            history2.add_sample(power)
        
        assert history2.trend == 'degrading'
    
    def test_signal_tracker(self):
        """Test SignalTracker operations."""
        from wifite.util.signal_tracker import SignalTracker
        
        tracker = SignalTracker()
        
        # Track AP
        tracker.update_ap('AA:BB:CC:DD:EE:FF', -65)
        tracker.update_ap('AA:BB:CC:DD:EE:FF', -60)
        
        history = tracker.get_ap_history('AA:BB:CC:DD:EE:FF')
        assert history is not None
        assert history.current == -60
        
        # Track client
        tracker.update_client('11:22:33:44:55:66', -70)
        
        client_history = tracker.get_client_history('11:22:33:44:55:66')
        assert client_history is not None
        assert client_history.current == -70
    
    def test_best_targets(self):
        """Test getting best targets by signal."""
        from wifite.util.signal_tracker import SignalTracker
        
        tracker = SignalTracker()
        
        # Add multiple APs with different signals
        for _ in range(5):  # Need multiple samples for average
            tracker.update_ap('AA:BB:CC:DD:EE:FF', -50)  # Strong
            tracker.update_ap('11:22:33:44:55:66', -75)  # Weak
            tracker.update_ap('22:33:44:55:66:77', -60)  # Medium
        
        # Get best targets with min_power=-70
        best = tracker.get_best_targets(min_power=-70)
        
        assert len(best) == 2  # Only strong and medium pass threshold
        assert best[0] == 'AA:BB:CC:DD:EE:FF'  # Strongest first
        assert best[1] == '22:33:44:55:66:77'
    
    def test_global_tracker(self):
        """Test global tracker singleton."""
        from wifite.util.signal_tracker import (
            get_signal_tracker, reset_signal_tracker
        )
        
        reset_signal_tracker()
        
        tracker1 = get_signal_tracker()
        tracker2 = get_signal_tracker()
        
        assert tracker1 is tracker2  # Same instance
        
        tracker1.update_ap('AA:BB:CC:DD:EE:FF', -65)
        
        # Should see the update in tracker2
        assert tracker2.get_ap_history('AA:BB:CC:DD:EE:FF') is not None
        
        reset_signal_tracker()


class TestRetryUtilities:
    """Tests for retry utilities."""
    
    def test_import(self):
        """Test that retry module can be imported."""
        from wifite.util.retry import (
            RetryExhausted, exponential_backoff, linear_backoff,
            constant_delay, RetryConfig, retry_with_backoff, RetryContext
        )
        assert RetryExhausted is not None
        assert exponential_backoff is not None
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        from wifite.util.retry import exponential_backoff
        
        # Without jitter for predictable testing
        delay0 = exponential_backoff(0, base_delay=1.0, max_delay=60.0, jitter=False)
        delay1 = exponential_backoff(1, base_delay=1.0, max_delay=60.0, jitter=False)
        delay2 = exponential_backoff(2, base_delay=1.0, max_delay=60.0, jitter=False)
        
        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0
        
        # Test max delay cap
        delay_capped = exponential_backoff(10, base_delay=1.0, max_delay=60.0, jitter=False)
        assert delay_capped == 60.0
    
    def test_linear_backoff(self):
        """Test linear backoff calculation."""
        from wifite.util.retry import linear_backoff
        
        delay0 = linear_backoff(0, base_delay=1.0, increment=1.0)
        delay1 = linear_backoff(1, base_delay=1.0, increment=1.0)
        delay2 = linear_backoff(2, base_delay=1.0, increment=1.0)
        
        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 3.0
    
    def test_retry_decorator_success(self):
        """Test retry decorator with successful function."""
        from wifite.util.retry import retry_with_backoff, constant_delay
        
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, backoff_func=lambda a: constant_delay(a, 0.01))
        def succeeds_first_time():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = succeeds_first_time()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_decorator_eventual_success(self):
        """Test retry decorator with function that succeeds after retries."""
        from wifite.util.retry import retry_with_backoff, constant_delay
        
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, backoff_func=lambda a: constant_delay(a, 0.01))
        def fails_twice_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = fails_twice_then_succeeds()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_decorator_exhausted(self):
        """Test retry decorator when all attempts fail."""
        from wifite.util.retry import retry_with_backoff, RetryExhausted, constant_delay
        
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, backoff_func=lambda a: constant_delay(a, 0.01))
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        try:
            always_fails()
            assert False, "Should have raised RetryExhausted"
        except RetryExhausted as e:
            assert e.attempts == 3
            assert call_count == 3
    
    def test_retry_context(self):
        """Test RetryContext context manager."""
        from wifite.util.retry import RetryContext, constant_delay
        
        call_count = 0
        
        with RetryContext(max_attempts=3, backoff_func=lambda a: constant_delay(a, 0.01)) as retry:
            for attempt in retry:
                call_count += 1
                if call_count < 3:
                    retry.record_failure(ValueError("Not yet"))
                else:
                    break
        
        assert call_count == 3
    
    def test_retry_config(self):
        """Test RetryConfig class."""
        from wifite.util.retry import RetryConfig, retry_with_backoff, constant_delay
        
        retries_logged = []
        
        def on_retry(attempt, exc):
            retries_logged.append((attempt, str(exc)))
        
        config = RetryConfig(
            max_attempts=3,
            backoff_func=lambda a: constant_delay(a, 0.01),
            on_retry=on_retry
        )
        
        call_count = 0
        
        @retry_with_backoff(config=config)
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Fail {call_count}")
            return "success"
        
        result = fails_twice()
        assert result == "success"
        assert len(retries_logged) == 2


class TestNativeBeacon:
    """Tests for native beacon generator."""
    
    def test_import(self):
        """Test that beacon module can be imported."""
        from wifite.native.beacon import (
            BeaconGenerator, create_fake_ap, is_available
        )
        assert BeaconGenerator is not None
        assert create_fake_ap is not None
        assert is_available is not None
    
    def test_beacon_generator_init(self):
        """Test BeaconGenerator initialization."""
        from wifite.native.beacon import BeaconGenerator, SCAPY_AVAILABLE
        
        if not SCAPY_AVAILABLE:
            print("Skipping beacon test - Scapy not available")
            return
        
        beacon = BeaconGenerator(
            interface='wlan0mon',
            essid='TestNetwork',
            channel=6,
            encryption='WPA2'
        )
        
        assert beacon.essid == 'TestNetwork'
        assert beacon.channel == 6
        assert beacon.encryption == 'WPA2'
        assert len(beacon.bssid) == 17  # XX:XX:XX:XX:XX:XX format
    
    def test_beacon_generator_stats(self):
        """Test BeaconGenerator statistics."""
        from wifite.native.beacon import BeaconGenerator, SCAPY_AVAILABLE
        
        if not SCAPY_AVAILABLE:
            print("Skipping beacon test - Scapy not available")
            return
        
        beacon = BeaconGenerator(
            interface='wlan0mon',
            essid='TestNetwork',
            channel=6
        )
        
        stats = beacon.get_stats()
        assert stats['essid'] == 'TestNetwork'
        assert stats['channel'] == 6
        assert stats['beacons_sent'] == 0
    
    def test_is_available(self):
        """Test is_available function."""
        from wifite.native.beacon import is_available, SCAPY_AVAILABLE
        
        assert is_available() == SCAPY_AVAILABLE


def run_tests():
    """Run all tests."""
    test_classes = [
        TestSignalTracker,
        TestRetryUtilities,
        TestNativeBeacon,
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_class in test_classes:
        print(f"\n{'=' * 60}")
        print(f"Running {test_class.__name__}")
        print('=' * 60)
        
        instance = test_class()
        
        for method_name in dir(instance):
            if not method_name.startswith('test_'):
                continue
            
            method = getattr(instance, method_name)
            if not callable(method):
                continue
            
            try:
                print(f"  {method_name}...", end=' ')
                method()
                print("PASS")
                passed += 1
            except AssertionError as e:
                print(f"FAIL: {e}")
                failed += 1
                errors.append((test_class.__name__, method_name, str(e)))
            except Exception as e:
                print(f"ERROR: {e}")
                failed += 1
                errors.append((test_class.__name__, method_name, str(e)))
    
    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print('=' * 60)
    
    if errors:
        print("\nFailures:")
        for class_name, method_name, error in errors:
            print(f"  {class_name}.{method_name}: {error}")
    
    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
