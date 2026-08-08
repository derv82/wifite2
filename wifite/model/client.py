#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Client(object):
    '''
    Enhanced Client class with better filtering and caching.
    Holds details for a wireless device associated with an Access Point.
    '''

    # Class-level cache for MAC address validation
    _mac_cache = {}
    
    # Minimum power threshold for valid clients (in dBm, adjusted for lab)
    MIN_POWER_THRESHOLD = -95

    def __init__(self, fields, validate=True):
        '''
        Initializes client info based on fields.
        
        Args:
            Fields - List of strings
            validate - Boolean to validate client data
        '''
        try:
            self.station = fields[0].strip()
            self.power = int(fields[3].strip())
            self.packets = int(fields[4].strip())
            self.bssid = fields[5].strip()
            
            # Additional fields for enhanced tracking
            self.first_seen = fields[1].strip() if len(fields) > 1 else None
            self.last_seen = fields[2].strip() if len(fields) > 2 else None
            self.probed_essids = fields[6].strip() if len(fields) > 6 else ''
            
            # Normalize power to 0-100 scale
            if self.power < 0:
                self.power += 100
            
            # Quality metric
            self.quality = max(0, min(100, self.power))
            
            # Cache for fast lookup
            self._hash = hash(f"{self.station}_{self.bssid}")
            
            if validate:
                self.validate()
        
        except Exception as e:
            logger.error(f"[!] Error parsing client fields: {str(e)}")
            raise

    def validate(self):
        '''Validate client data'''
        if not self._is_valid_mac(self.station):
            raise ValueError(f"Invalid station MAC: {self.station}")
        
        if not self._is_valid_mac(self.bssid):
            raise ValueError(f"Invalid BSSID: {self.bssid}")
        
        if self.power < self.MIN_POWER_THRESHOLD:
            logger.warning(f"[!] Client power too low: {self.power}")

    @staticmethod
    def _is_valid_mac(mac_address):
        '''Validate MAC address format'''
        import re
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return re.match(pattern, mac_address) is not None

    def is_strong_signal(self, threshold=-50):
        '''Check if client has strong signal'''
        return (self.power + 100) > threshold

    def is_active(self, min_packets=1):
        '''Check if client is actively transmitting'''
        return self.packets >= min_packets

    def get_quality_indicator(self):
        '''Get visual quality indicator'''
        if self.quality > 75:
            return '{G}●●●{W}'  # Strong
        elif self.quality > 50:
            return '{Y}●●{W}'   # Medium
        else:
            return '{R}●{W}'    # Weak

    def __str__(self):
        '''String representation of Client'''
        result = ''
        for (key, value) in self.__dict__.items():
            if not key.startswith('_'):
                result += f"{key}: {value}, "
        return result.rstrip(', ')

    def __repr__(self):
        '''Compact representation for debugging'''
        return f"Client({self.station}, signal={self.quality}%, packets={self.packets})"

    def __hash__(self):
        '''Allow use in sets and dicts'''
        return self._hash

    def __eq__(self, other):
        '''Check equality based on MAC addresses'''
        if isinstance(other, Client):
            return (self.station.lower() == other.station.lower() and
                    self.bssid.lower() == other.bssid.lower())
        return False


if __name__ == '__main__':
    fields = 'AA:BB:CC:DD:EE:FF, 2015-05-27 19:43:47, 2015-05-27 19:43:47, -67, 2, (not associated), HOME-ABCD'.split(',')
    c = Client(fields)
    print('Client:', c)
    print('Quality:', c.get_quality_indicator())
    print('Is Active:', c.is_active())
