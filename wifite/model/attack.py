#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Attack(object):
    '''Enhanced attack class with adaptive timeouts and threading support.'''

    # Adaptive timeouts - shorter for lab environments
    target_wait = 30  # Reduced from 60
    target_wait_min = 10  # Minimum wait time
    target_wait_max = 45  # Maximum wait time
    
    # Thread pool for parallel operations
    executor = ThreadPoolExecutor(max_workers=4)

    def __init__(self, target, lab_mode=True, pin=None):
        """
        Args:
            target: Target network object
            lab_mode: Boolean - Enable optimizations for lab environment
            pin: WPS PIN for direct connection (optional)
        """
        self.target = target
        self.lab_mode = lab_mode
        self.pin = pin
        
        # Adaptive timeout based on mode
        if lab_mode:
            self.target_wait = 15  # Lab environment - faster detection
        
        self.start_time = time.time()
        self.last_seen_time = time.time()

    def run(self):
        raise Exception('Unimplemented method: run')

    def get_elapsed_time(self):
        """Get elapsed time since attack started"""
        return time.time() - self.start_time

    def is_timed_out(self, timeout=None):
        """Check if attack has timed out"""
        if timeout is None:
            timeout = self.target_wait
        return (time.time() - self.last_seen_time) > timeout

    def reset_timeout(self):
        """Reset the timeout timer"""
        self.last_seen_time = time.time()

    def wait_for_target(self, airodump):
        '''Waits for target to appear in airodump with threading and adaptive retry.'''
        start_time = time.time()
        retry_count = 0
        max_retries = 3
        
        logger.info(f"[*] Waiting for target {self.target.bssid} (Lab Mode: {self.lab_mode})")

        while retry_count < max_retries:
            try:
                targets = airodump.get_targets(apply_filter=False)
                
                # Check timeout with adaptive backoff
                elapsed = time.time() - start_time
                current_timeout = min(self.target_wait + (retry_count * 5), self.target_wait_max)
                
                if len(targets) == 0:
                    if elapsed > current_timeout:
                        retry_count += 1
                        logger.warning(f"[!] Target not found, retry {retry_count}/{max_retries}")
                        if retry_count >= max_retries:
                            raise Exception(
                                f'Target {self.target.bssid} did not appear after {elapsed:.0f} seconds'
                            )
                        start_time = time.time()  # Reset timer for retry
                    time.sleep(0.5)  # Reduced from 1 second
                    targets = airodump.get_targets()
                    continue

                # Find target in airodump results
                airodump_target = None
                for t in targets:
                    if t.bssid.lower() == self.target.bssid.lower():
                        airodump_target = t
                        break

                if airodump_target is None:
                    if elapsed > current_timeout:
                        retry_count += 1
                        continue
                    time.sleep(0.5)
                    continue

                logger.info(f"[+] Target found: {airodump_target.bssid}")
                self.reset_timeout()
                return airodump_target

            except Exception as e:
                logger.error(f"[!] Error waiting for target: {str(e)}")
                if retry_count < max_retries - 1:
                    retry_count += 1
                    time.sleep(1)
                else:
                    raise

        raise Exception(f'Failed to find target {self.target.bssid} after {max_retries} retries')

    def verify_target_with_threading(self, airodump):
        '''Verify target using multiple methods in parallel'''
        tasks = []
        
        # Add verification tasks
        tasks.append(self.executor.submit(self.wait_for_target, airodump))
        
        # Wait for first successful verification
        for future in as_completed(tasks, timeout=self.target_wait):
            try:
                result = future.result()
                return result
            except Exception as e:
                logger.debug(f"Verification method failed: {str(e)}")
                continue
        
        raise Exception('All verification methods failed')


if __name__ == '__main__':
    print("Attack module loaded with enhanced capabilities")
