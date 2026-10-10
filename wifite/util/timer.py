#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

class Timer:
    def __init__(self, seconds):
        self.start_time = time.time()
        self.end_time = self.start_time + seconds

    def remaining(self):
        return max(0, self.end_time - time.time())

    def ended(self):
        return self.remaining() == 0

    def running_time(self):
        return time.time() - self.start_time

    def __str__(self):
        """ Time remaining in minutes (if > 1) and seconds, e.g. 5m23s"""
        return Timer.secs_to_str(self.remaining())

    @staticmethod
    def secs_to_str(seconds):
        """Human-readable seconds. 193 -> 3m13s"""
        if seconds < 0:
            return '-%ds' % seconds

        rem = int(seconds)
        hours = rem // 3600
        mins = int((rem % 3600) / 60)
        secs = rem % 60
        if hours > 0:
            return '%dh%dm%ds' % (hours, mins, secs)
        elif mins > 0:
            return '%dm%ds' % (mins, secs)
        else:
            return '%ds' % secs