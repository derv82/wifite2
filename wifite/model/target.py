#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.color import Color
import re
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class WPSState:
    NONE, UNLOCKED, LOCKED, UNKNOWN = range(0, 4)
    
    STATE_NAMES = {
        NONE: 'Disabled',
        UNLOCKED: 'Enabled',
        LOCKED: 'Locked',
        UNKNOWN: 'Unknown'
    }


class Target(object):
    '''
    Enhanced Target class representing an Access Point with better
    caching and performance optimizations.
    '''
    
    # Cache for commonly used values
    _encryption_cache = {}

    def __init__(self, fields):
        '''
        Initializes target info based on fields from airodump output.
        '''
        try:
            self.bssid = fields[0].strip()
            self.first_seen = fields[1].strip()
            self.last_seen = fields[2].strip()
            self.channel = fields[3].strip()
            
            self.speed = int(fields[4].strip()) if fields[4].strip() else 0
            
            # Parse encryption
            self.encryption = self._parse_encryption(fields[5].strip())
            self.cipher = fields[6].strip() if len(fields) > 6 else ''
            self.authentication = fields[7].strip() if len(fields) > 7 else ''
            
            # Power level (normalized to 0-100)
            self.power = int(fields[8].strip())
            if self.power < 0:
                self.power += 100

            self.beacons = int(fields[9].strip()) if fields[9].strip() else 0
            self.ivs = int(fields[10].strip()) if fields[10].strip() else 0

            # Parse ESSID
            self.essid_len = int(fields[12].strip()) if fields[12].strip() else 0
            self.essid = fields[13] if len(fields) > 13 else ''
            
            self.essid_known = True
            if self.essid == '\\x00' * self.essid_len or \
               self.essid == 'x00' * self.essid_len or \
               self.essid.strip() == '':
                self.essid = None
                self.essid_known = False

            self.wps = WPSState.UNKNOWN
            self.decloaked = False
            self.clients = []
            
            # Caching
            self._hash = hash(self.bssid)
            self._str_cache = None

            self.validate()
        
        except Exception as e:
            logger.error(f"[!] Error parsing target fields: {str(e)}")
            raise

    def _parse_encryption(self, encryption_str):
        '''Parse and normalize encryption string'''
        encryption_str = encryption_str.strip()
        
        if 'WPA3' in encryption_str:
            return 'WPA3'
        elif 'WPA2' in encryption_str:
            return 'WPA2'
        elif 'WPA' in encryption_str:
            return 'WPA'
        elif 'WEP' in encryption_str:
            return 'WEP'
        elif 'Open' in encryption_str:
            return 'Open'
        
        return encryption_str[:4].strip()

    def validate(self):
        '''Validate target data'''
        # Check channel
        if self.channel == '-1':
            raise Exception('Ignoring target with Negative-One (-1) channel')

        # Filter broadcast/multicast BSSIDs
        bssid_broadcast = re.compile(r'^(ff:ff:ff:ff:ff:ff|00:00:00:00:00:00)$', re.IGNORECASE)
        if bssid_broadcast.match(self.bssid):
            raise Exception(f'Ignoring broadcast BSSID: {self.bssid}')

        bssid_multicast = re.compile(r'^(01:00:5e|01:80:c2|33:33)', re.IGNORECASE)
        if bssid_multicast.match(self.bssid):
            raise Exception(f'Ignoring multicast BSSID: {self.bssid}')

    def get_signal_strength(self):
        '''Get signal strength category'''
        if self.power > 75:
            return 'Excellent'
        elif self.power > 50:
            return 'Good'
        elif self.power > 25:
            return 'Fair'
        else:
            return 'Weak'

    def is_target_vulnerable(self):
        '''Quick check if target is worth attacking'''
        checks = [
            self.encryption != 'Open',  # Don't attack open networks
            self.encryption in ['WPA', 'WPA2', 'WPA3', 'WEP'],  # Supported encryption
            self.power > 20,  # Signal strong enough
            len(self.clients) > 0 or self.beacons > 5,  # Activity detected
        ]
        return all(checks)

    def to_str(self, show_bssid=False, show_vulnerability=False):
        '''
        *Colored* string representation of this Target.
        Formatted for the 'scanning' table view.
        '''
        max_essid_len = 24
        essid = self.essid if self.essid_known else f'({self.bssid})'
        
        # Trim ESSID if needed
        if len(essid) > max_essid_len:
            essid = essid[0:max_essid_len - 3] + '...'
        else:
            essid = essid.rjust(max_essid_len)

        # Color coding for ESSID
        if self.essid_known:
            essid = Color.s(f'{{C}}{essid}')
        else:
            essid = Color.s(f'{{O}}{essid}')

        # Add decloaked indicator
        decloaked_char = '*' if self.decloaked else ' '
        essid += Color.s(f'{{P}}{decloaked_char}')

        # BSSID
        if show_bssid:
            bssid = Color.s(f'{{O}}{self.bssid}  ')
        else:
            bssid = ''

        # Channel
        channel_color = '{C}' if int(self.channel) > 14 else '{G}'
        channel = Color.s(f'{channel_color}{str(self.channel).rjust(3)}')

        # Encryption
        encryption = self.encryption.rjust(4)
        if 'WEP' in encryption:
            encryption = Color.s(f'{{G}}{encryption}')
        elif 'WPA' in encryption:
            encryption = Color.s(f'{{O}}{encryption}')
        else:
            encryption = Color.s(f'{{R}}{encryption}')

        # Power
        power = f'{str(self.power).rjust(3)}db'
        if self.power > 50:
            color = 'G'
        elif self.power > 35:
            color = 'O'
        else:
            color = 'R'
        power = Color.s(f'{{{color}}}{power}')

        # WPS Status
        if self.wps == WPSState.UNLOCKED:
            wps = Color.s('{G} yes')
        elif self.wps == WPSState.NONE:
            wps = Color.s('{O}  no')
        elif self.wps == WPSState.LOCKED:
            wps = Color.s('{R}lock')
        else:
            wps = Color.s('{O} n/a')

        # Clients
        clients = '       '
        if len(self.clients) > 0:
            clients = Color.s(f'{{G}}  {str(len(self.clients))}')

        # Vulnerability indicator
        vuln = ''
        if show_vulnerability:
            if self.is_target_vulnerable():
                vuln = Color.s('{G} ✓')
            else:
                vuln = Color.s('{R} ✗')

        result = f'{essid}  {bssid}{channel}  {encryption}  {power}  {wps}  {clients}{vuln}'
        result += Color.s('{W}')
        
        return result

    def __str__(self):
        '''String representation'''
        return self.to_str()

    def __repr__(self):
        '''Compact representation for debugging'''
        clients = len(self.clients) if self.clients else 0
        return f"Target({self.bssid}, {self.essid}, {self.encryption}, clients={clients})"

    def __hash__(self):
        '''Allow use in sets and dicts'''
        return self._hash

    def __eq__(self, other):
        '''Check equality based on BSSID'''
        if isinstance(other, Target):
            return self.bssid.lower() == other.bssid.lower()
        return False


if __name__ == '__main__':
    fields = 'AA:BB:CC:DD:EE:FF,2015-05-27 19:28:44,2015-05-27 19:28:46,1,54,WPA2,CCMP TKIP,PSK,-58,2,0,0.0.0.0,9,TEST-LAB,'.split(',')
    t = Target(fields)
    print(t.to_str(show_vulnerability=True))
    print(f"Vulnerable: {t.is_target_vulnerable()}")
