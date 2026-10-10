#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Passive PMKID monitoring thread.

Monitors passive PMKID capture in the background, periodically extracting
hashes from the capture file and updating statistics.
"""

import time
from threading import Thread


class PassivePMKIDMonitor(Thread):
    """
    Background thread that monitors passive PMKID capture.
    
    Periodically extracts PMKID hashes from the capture file and updates
    attack statistics. Runs as a daemon thread to ensure clean shutdown.
    """
    
    def __init__(self, attack_instance, interval=30):
        """
        Initialize passive PMKID monitor.
        
        Args:
            attack_instance: Reference to AttackPassivePMKID instance
            interval: Extraction interval in seconds (default: 30)
        """
        super().__init__()
        self.daemon = True
        
        self.attack = attack_instance
        self.interval = interval
        self.keep_running = True
    
    def run(self):
        """
        Main monitoring loop.
        
        Periodically calls attack.extract_and_save_pmkids() at the configured
        interval and updates attack statistics after each extraction.
        """
        while self.keep_running:
            time.sleep(self.interval)
            
            if not self.keep_running:
                break
            
            try:
                # Extract PMKIDs from capture file
                self.attack.extract_and_save_pmkids()
                
                # Update statistics timestamp
                self.attack.statistics['last_extraction'] = time.time()
                
            except Exception as e:
                # Log error but continue monitoring
                from ..util.logger import log_error
                log_error('PassivePMKIDMonitor', f'Error during extraction: {e}', e)
    
    def stop(self):
        """Stop the monitoring thread gracefully."""
        self.keep_running = False
