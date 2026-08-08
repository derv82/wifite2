#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import threading
from typing import Callable, Optional


class AdvancedTimer(object):
    '''Advanced timer with callbacks, pause/resume, and precision timing'''

    def __init__(self, seconds: float, on_timeout: Optional[Callable] = None, 
                 on_tick: Optional[Callable] = None):
        '''
        Initialize advanced timer.
        
        Args:
            seconds: Duration in seconds
            on_timeout: Callback function when timer expires
            on_tick: Callback function on each second tick
        '''
        self.start_time = time.time()
        self.end_time = self.start_time + seconds
        self.total_seconds = seconds
        self.on_timeout = on_timeout
        self.on_tick = on_tick
        self.paused_time = 0
        self.is_paused = False
        self._tick_thread = None
        self._running = True

        if on_tick:
            self._start_tick_thread()

    def _start_tick_thread(self):
        '''Start background thread for tick callbacks'''
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._tick_thread.start()

    def _tick_loop(self):
        '''Background loop for tick callbacks'''
        last_second = -1
        while self._running:
            remaining = self.remaining()
            current_second = int(remaining)

            if current_second != last_second and remaining > 0:
                if self.on_tick:
                    self.on_tick(current_second)
                last_second = current_second

            if remaining <= 0 and self.on_timeout:
                self.on_timeout()
                break

            time.sleep(0.1)

    def pause(self):
        '''Pause the timer'''
        if not self.is_paused:
            self.pause_start = time.time()
            self.is_paused = True

    def resume(self):
        '''Resume the paused timer'''
        if self.is_paused:
            self.paused_time += time.time() - self.pause_start
            self.end_time += self.paused_time
            self.is_paused = False
            self.paused_time = 0

    def remaining(self) -> float:
        '''Get remaining time in seconds'''
        if self.is_paused:
            return max(0, self.end_time - self.pause_start)
        return max(0, self.end_time - time.time())

    def ended(self) -> bool:
        '''Check if timer has expired'''
        return self.remaining() == 0

    def running_time(self) -> float:
        '''Get elapsed time in seconds'''
        if self.is_paused:
            return self.pause_start - self.start_time
        return time.time() - self.start_time

    def reset(self):
        '''Reset timer'''
        self.start_time = time.time()
        self.end_time = self.start_time + self.total_seconds
        self.is_paused = False
        self.paused_time = 0

    def add_time(self, seconds: float):
        '''Add additional time to timer'''
        self.end_time += seconds

    def __str__(self) -> str:
        '''String representation of remaining time'''
        return self.secs_to_str(self.remaining())

    def __repr__(self) -> str:
        return '<AdvancedTimer: %s remaining>' % str(self)

    @staticmethod
    def secs_to_str(seconds: float) -> str:
        '''Convert seconds to human-readable format (5m23s)'''
        if seconds < 0:
            return '-%ds' % abs(int(seconds))

        rem = int(seconds)
        hours = rem // 3600
        mins = (rem % 3600) // 60
        secs = rem % 60

        if hours > 0:
            return '%dh%dm%ds' % (hours, mins, secs)
        elif mins > 0:
            return '%dm%ds' % (mins, secs)
        else:
            return '%ds' % secs

    @staticmethod
    def hms_to_secs(time_str: str) -> int:
        '''Convert time string (5m23s) to seconds'''
        total = 0
        parts = time_str.lower().replace(' ', '').split('m')

        if len(parts) > 1:
            total += int(parts[0]) * 60
            parts = parts[1].split('s')
            if parts[0]:
                total += int(parts[0])
        else:
            parts = time_str.lower().split('s')
            if parts[0]:
                total += int(parts[0])

        return total


# Backward compatibility
Timer = AdvancedTimer


class CountdownTimer(AdvancedTimer):
    '''Specialized countdown timer with visual feedback'''

    def __init__(self, seconds: float):
        def on_tick(remaining):
            from ..util.color import Color
            Color.p('\r{+} Time remaining: {G}%s{W}' % self.secs_to_str(remaining))

        super().__init__(seconds, on_tick=on_tick)


if __name__ == '__main__':
    # Test basic timer
    print('Testing basic timer...')
    t = AdvancedTimer(5)
    while not t.ended():
        print(f'Remaining: {t}')
        time.sleep(1)

    # Test with callback
    print('\nTesting timer with callback...')
    def on_expire():
        print('Timer expired!')

    t2 = AdvancedTimer(3, on_timeout=on_expire)
    while not t2.ended():
        time.sleep(0.5)

    # Test pause/resume
    print('\nTesting pause/resume...')
    t3 = AdvancedTimer(10)
    time.sleep(2)
    t3.pause()
    print(f'Paused: {t3}')
    time.sleep(2)
    t3.resume()
    print(f'Resumed: {t3}')

    # Test countdown
    print('\nTesting countdown...')
    cd = CountdownTimer(5)
    cd_thread = threading.Thread(target=lambda: (time.sleep(6), print('\nDone!')))
    cd_thread.start()
    cd_thread.join()
