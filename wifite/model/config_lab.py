#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Lab environment optimized configuration for Wifite2
For fast handshake capture and WPS PIN attacks
"""

class LabConfig:
    """Configuration optimized for lab testing"""
    
    # Timeouts (in seconds) - optimized for lab
    TARGET_WAIT_TIME = 15  # Wait for target to appear
    HANDSHAKE_TIMEOUT = 30  # Time to wait for handshake
    WPS_ATTACK_TIMEOUT = 120  # Time for WPS attack
    
    # Capture settings
    MIN_PACKETS_FOR_HANDSHAKE = 1  # Minimal packets threshold
    HANDSHAKE_VERIFY_METHODS = ['tshark', 'pyrit', 'cowpatty', 'aircrack']
    PARALLEL_VERIFICATION = True  # Use parallel verification
    
    # Deauthentication settings
    DEAUTH_ATTEMPTS = 2  # Number of deauth packets
    DEAUTH_INTERVAL = 0.2  # Interval between deauths
    
    # WPS Settings
    WPS_PINS_TO_TRY = [
        '00000000', '11111111', '12345670',
        '12345678', '87654321', '99999999',
    ]
    WPS_COMMON_PINS = True
    WPS_PIXIE_DUST = True  # Try pixiewps first
    
    # Scan settings
    SCAN_TIMEOUT = 10
    MAX_TARGETS = 50
    
    # Output settings
    VERBOSE = True
    DEBUG = False
    
    @classmethod
    def get_config(cls):
        """Return configuration as dict"""
        return {k: v for k, v in cls.__dict__.items() if not k.startswith('_')}


# Usage example
if __name__ == '__main__':
    config = LabConfig.get_config()
    for key, value in config.items():
        print(f"{key}: {value}")
