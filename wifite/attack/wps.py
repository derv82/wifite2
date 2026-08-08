#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..util.color import Color
from ..util.process import Process
from ..config import Configuration
from ..tools.bully import Bully
from ..tools.reaver import Reaver
from ..util.timer import Timer
import time
import logging

# Setup advanced logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AttackWPS(Attack):
    """Advanced WPS Attack with enhanced timeout handling and retry logic"""
    
    # Adaptive timeout configuration
    INITIAL_TIMEOUT = 60
    MAX_TIMEOUT = 600
    MIN_TIMEOUT = 30
    BACKOFF_MULTIPLIER = 1.5
    MAX_RETRIES = 3
    
    # WPS PIN specific settings
    PIN_RATE_LIMIT = 300  # seconds between PIN attempts
    SIGNAL_THRESHOLD = -80  # dBm, minimum acceptable signal strength
    MIN_CLIENTS_REQUIRED = 1

    @staticmethod
    def can_attack_wps():
        return Reaver.exists() or Bully.exists()

    def __init__(self, target, pixie_dust=False):
        super(AttackWPS, self).__init__(target)
        self.success = False
        self.crack_result = None
        self.pixie_dust = pixie_dust
        self.adaptive_timeout = self.INITIAL_TIMEOUT
        self.retry_count = 0
        self.signal_history = []
        self.attack_start_time = None
        self.last_pin_attempt = 0

    def run(self):
        """Run all WPS-related attacks with advanced error handling"""
        
        # Pre-flight checks
        if not self._preflight_checks():
            return False

        # Signal strength validation
        if not self._validate_signal_strength():
            return False

        # Client detection with retry
        if not self._ensure_clients_connected():
            return False

        # Attempt attack with retry logic
        return self._attempt_attack_with_retries()

    def _preflight_checks(self):
        """Validate configuration and dependencies"""
        if Configuration.use_pmkid_only:
            Color.pl('\r{!} {O}Skipping WPS: PMKID-only mode enabled{W}')
            self.success = False
            return False

        if Configuration.no_wps:
            Color.pl('\r{!} {O}Skipping WPS: disabled by configuration{W}')
            self.success = False
            return False

        if not Configuration.wps_pixie and self.pixie_dust:
            Color.pl('\r{!} {O}--no-pixie{R} was given, ignoring WPS Pixie-Dust Attack ' +
                    'on {O}%s{W}' % self.target.essid)
            self.success = False
            return False

        if not Configuration.wps_pin and not self.pixie_dust:
            Color.pl('\r{!} {O}--no-pin{R} was given, ignoring WPS PIN Attack ' +
                    'on {O}%s{W}' % self.target.essid)
            self.success = False
            return False

        return True

    def _validate_signal_strength(self):
        """Validate target has acceptable signal strength"""
        signal = self.target.power
        
        if signal < self.SIGNAL_THRESHOLD:
            Color.pl('{!} {R}Error: {O}Signal strength too weak: {R}%d dBm{O} (threshold: {R}%d dBm{W})' 
                    % (signal, self.SIGNAL_THRESHOLD))
            return False
        
        self.signal_history.append(signal)
        Color.pl('{+} {G}Signal strength acceptable:{W} {C}%d dBm{W}' % signal)
        return True

    def _ensure_clients_connected(self, max_attempts=5):
        """Ensure at least one client is connected with retry"""
        from ..tools.airodump import Airodump
        
        attempt = 0
        while attempt < max_attempts:
            if len(self.target.clients) >= self.MIN_CLIENTS_REQUIRED:
                Color.pl('{+} {G}Found {W}{C}%d{W}{G} connected client(s){W}' % len(self.target.clients))
                return True
            
            attempt += 1
            Color.p('\r{*} Waiting for clients to connect... (Attempt {G}%d{W}/{G}%d{W})' 
                   % (attempt, max_attempts))
            time.sleep(2)
        
        Color.pl('\n{!} {O}Warning: {R}No connected clients detected{W}')
        return False

    def _attempt_attack_with_retries(self):
        """Attempt attack with exponential backoff retry logic"""
        self.attack_start_time = time.time()
        
        while self.retry_count < self.MAX_RETRIES:
            try:
                Color.pl('\n{+} {G}WPS Attack Attempt {W}{C}%d/%d{W}' 
                        % (self.retry_count + 1, self.MAX_RETRIES))
                
                # Select tool and run attack
                if self._should_use_bully():
                    success = self.run_bully()
                else:
                    success = self.run_reaver()
                
                if success:
                    return True
                
                # Increment retry counter and adjust timeout
                self.retry_count += 1
                if self.retry_count < self.MAX_RETRIES:
                    self._adjust_timeout()
                    self._wait_before_retry()
                    
            except Exception as e:
                logger.exception("WPS attack error: %s" % str(e))
                self.retry_count += 1
                if self.retry_count < self.MAX_RETRIES:
                    self._adjust_timeout()
                    self._wait_before_retry()
                else:
                    Color.pl('{!} {R}WPS attack failed after {W}{C}%d{W}{R} retries{W}' 
                            % self.MAX_RETRIES)
                    return False
        
        return False

    def _should_use_bully(self):
        """Determine if Bully should be used instead of Reaver"""
        if not Reaver.exists() and Bully.exists():
            return True
        elif self.pixie_dust and not Reaver.is_pixiedust_supported() and Bully.exists():
            return True
        elif Configuration.use_bully:
            return True
        return False

    def _adjust_timeout(self):
        """Adaptively adjust timeout based on attempt"""
        old_timeout = self.adaptive_timeout
        self.adaptive_timeout = min(
            int(self.adaptive_timeout * self.BACKOFF_MULTIPLIER),
            self.MAX_TIMEOUT
        )
        Color.pl('{+} {O}Adjusted timeout: {R}%d{O}s → {G}%d{O}s{W}' 
                % (old_timeout, self.adaptive_timeout))

    def _wait_before_retry(self):
        """Wait with countdown before retrying"""
        wait_time = min(int(self.adaptive_timeout * 0.3), 30)  # Wait 30% of timeout, max 30s
        Color.p('{+} Waiting {C}%d{W} seconds before retry' % wait_time)
        
        for remaining in range(wait_time, 0, -1):
            Color.p('\r{+} Waiting {C}%d{W} seconds before retry...' % remaining)
            time.sleep(1)
        Color.pl('')

    def run_bully(self):
        """Run Bully with enhanced configuration"""
        try:
            Color.pl('{+} {G}Starting Bully WPS attack{W} with {C}%d{W}s timeout' 
                    % self.adaptive_timeout)
            
            bully = Bully(self.target, pixie_dust=self.pixie_dust)
            bully.timeout = self.adaptive_timeout  # Set adaptive timeout
            bully.run()
            bully.stop()
            
            self.crack_result = bully.crack_result
            self.success = self.crack_result is not None
            
            if self.success:
                Color.pl('{+} {G}Bully attack successful{W}')
            else:
                Color.pl('{!} {O}Bully attack did not find PIN{W}')
            
            return self.success
            
        except KeyboardInterrupt:
            Color.pl('\n{!} {O}Bully interrupted by user{W}')
            return False

    def run_reaver(self):
        """Run Reaver with enhanced configuration and monitoring"""
        try:
            Color.pl('{+} {G}Starting Reaver WPS attack{W} with {C}%d{W}s timeout' 
                    % self.adaptive_timeout)
            
            reaver = Reaver(self.target, pixie_dust=self.pixie_dust)
            reaver.timeout = self.adaptive_timeout  # Set adaptive timeout
            reaver.run()
            
            # Monitor for successful crack
            self.crack_result = reaver.crack_result
            self.success = self.crack_result is not None
            
            if self.success:
                Color.pl('{+} {G}Reaver attack successful{W}')
                elapsed = time.time() - self.attack_start_time
                Color.pl('{+} {C}Attack completed in {W}{G}%.1f{W}{C} seconds{W}' % elapsed)
            else:
                Color.pl('{!} {O}Reaver attack did not find PIN{W}')
            
            return self.success
            
        except KeyboardInterrupt:
            Color.pl('\n{!} {O}Reaver interrupted by user{W}')
            return False
        except Exception as e:
            Color.pl('{!} {R}Reaver error: {O}%s{W}' % str(e))
            logger.exception("Reaver execution error")
            return False

    def get_average_signal(self):
        """Calculate average signal strength"""
        if not self.signal_history:
            return self.target.power
        return sum(self.signal_history) / len(self.signal_history)
