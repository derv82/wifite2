#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.color import Color
from ..config import Configuration
import re
import time as _time

class WPSState:
    NONE, UNLOCKED, LOCKED, UNKNOWN = list(range(4))


class ArchivedTarget:
    """
        Holds information between scans from a previously found target
    """

    def __init__(self, target):
        self.bssid = target.bssid
        self.channel = target.channel
        self.decloaked = target.decloaked
        self.attacked = target.attacked
        self.essid = target.essid
        self.essid_known = target.essid_known
        self.essid_len = target.essid_len

    def transfer_info(self, other):
        """
            Helper function to transfer relevant fields into another Target or ArchivedTarget
        """
        other.attacked = self.attacked

        if self.essid_known and other.essid_known:
            other.decloaked = self.decloaked

        if not other.essid_known:
                other.decloaked = self.decloaked
                other.essid = self.essid
                other.essid_known = self.essid_known
                other.essid_len = self.essid_len

    def __eq__(self, other):
        # Check if the other class type is either ArchivedTarget or Target
        return isinstance(other, (self.__class__, Target)) and self.bssid == other.bssid

class Target:
    """
        Holds details for a 'Target' aka Access Point (e.g. router).
    """
    _ansi_re = re.compile(r'\033\[[0-9;]*m')

    def _pad_colored(self, colored_str, width, align='left'):
        """Pad a colored string to a specific visible width."""
        visible = self._ansi_re.sub('', colored_str)
        diff = width - len(visible)
        if diff <= 0:
            return colored_str
        if align == 'right':
            return ' ' * diff + colored_str
        elif align == 'center':
            left_pad = diff // 2
            right_pad = diff - left_pad
            return ' ' * left_pad + colored_str + ' ' * right_pad
        else:
            return colored_str + ' ' * diff

    def __init__(self, fields):
        """
            Initializes & stores target info based on fields.
            Args:
                Fields - List of strings
                INDEX KEY             EXAMPLE
                    0 BSSID           (00:1D:D5:9B:11:00)
                    1 First time seen (2015-05-27 19:28:43)
                    2 Last time seen  (2015-05-27 19:28:46)
                    3 channel         (6)
                    4 Speed           (54)
                    5 Privacy         (WPA2 OWE)
                    6 Cipher          (CCMP TKIP)
                    7 Authentication  (PSK SAE)
                    8 Power           (-62)
                    9 beacons         (2)
                    10 # IV           (0)
                    11 LAN IP         (0.  0.  0.  0)
                    12 ID-length      (9)
                    13 ESSID          (HOME-ABCD)
                    14 Key            ()
        """
        self.manufacturer = None
        self.wps = WPSState.NONE
        bssid_raw = fields[0].strip().upper()
        # Validate MAC address format (XX:XX:XX:XX:XX:XX)
        if not re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', bssid_raw):
            raise ValueError(f'Invalid BSSID format: {bssid_raw!r}')
        self.bssid = bssid_raw
        try:
            ch = int(fields[3].strip())
            # Valid WiFi channels: 1-14 (2.4GHz), 32-177 (5GHz), 1-233 (6GHz)
            self.channel = ch if 1 <= ch <= 233 else -1
        except (ValueError, IndexError):
            self.channel = -1
        try:
            self.encryption = fields[5].strip()
        except IndexError:
            self.encryption = ''
        try:
            self.authentication = fields[7].strip()
        except IndexError:
            self.authentication = ''

        # Determine primary encryption and auth
        # Note: SAE (Simultaneous Authentication of Equals) is the authentication method for WPA3
        # If we see SAE in authentication, it's WPA3 even if encryption field doesn't say "WPA3"
        if 'WPA3' in self.encryption or 'SAE' in self.authentication:
            self.primary_encryption = 'WPA3'
        elif 'WPA2' in self.encryption:
            self.primary_encryption = 'WPA2'
        elif 'WPA' in self.encryption: # Handles cases where only "WPA" is present or if no other WPAx is found
            self.primary_encryption = 'WPA'
        elif 'WEP' in self.encryption:
            self.primary_encryption = 'WEP'
        elif 'OWE' in self.encryption: # Opportunistic Wireless Encryption
            self.primary_encryption = 'OWE'
        elif len(self.encryption) == 0: # Default to WPA if not specified, as per old logic
            self.primary_encryption = 'WPA'
        else: # Fallback for unknown types
            parts = self.encryption.split(' ')
            self.primary_encryption = parts[0] if parts and parts[0] else 'WPA'


        if 'SAE' in self.authentication:
            self.primary_authentication = 'SAE'
        elif 'PSK' in self.authentication:
            self.primary_authentication = 'PSK'
        elif 'MGT' in self.authentication: # Enterprise
            self.primary_authentication = 'MGT'
        elif 'OWE' in self.authentication: # OWE uses its own auth mechanism
            self.primary_authentication = 'OWE'
        else:
            self.primary_authentication = self.authentication.split(' ')[0] if self.authentication else ''


        try:
            self.power = int(fields[8].strip())
            if self.power == -1:
                # airodump-ng uses -1 as a sentinel meaning the driver does not
                # report signal strength, or the AP is only heard one-way.
                # Do NOT normalise it (+100 would produce a misleading 99).
                self.power = 0
            elif self.power < 0:
                self.power += 100
        except (ValueError, IndexError):
            self.power = 0
        self.max_power = self.power

        try:
            self.beacons = int(fields[9].strip())
        except (ValueError, IndexError):
            self.beacons = 0
        try:
            self.ivs = int(fields[10].strip())
        except (ValueError, IndexError):
            self.ivs = 0

        self.essid_known = True
        try:
            self.essid_len = int(fields[12].strip())
        except (ValueError, IndexError):
            self.essid_len = 0
        try:
            self.essid = fields[13]
        except IndexError:
            self.essid = None
            self.essid_known = False
        if self.essid is not None and (
                self.essid == '\\x00' * self.essid_len or
                self.essid == 'x00' * self.essid_len or
                self.essid == '\x00' * self.essid_len or
                self.essid.strip() == ''):
            # Don't display '\x00...' for hidden ESSIDs
            self.essid = None  # '(%s)' % self.bssid
            self.essid_known = False

        # self.wps = WPSState.UNKNOWN

        # Will be set to true once this target will be attacked
        # Needed to count targets in infinite attack mode
        self.attacked = False

        self.decloaked = False  # If ESSID was hidden but we decloaked it.

        self.clients = []

        # Parse timestamps for beacon-rate analysis (honeypot detection)
        now = _time.time()
        try:
            self.first_seen = _time.mktime(
                _time.strptime(fields[1].strip(), '%Y-%m-%d %H:%M:%S'))
        except (ValueError, IndexError, OverflowError):
            self.first_seen = now
        try:
            self.last_seen = _time.mktime(
                _time.strptime(fields[2].strip(), '%Y-%m-%d %H:%M:%S'))
        except (ValueError, IndexError, OverflowError):
            self.last_seen = now

        # Honeypot detection (populated by HoneypotDetector.analyse)
        self.honeypot_score = 0
        self.honeypot_reasons = []

        # Store full encryption and authentication strings for detailed info if needed
        self.full_encryption_string = self.encryption
        self.full_authentication_string = self.authentication
        # For compatibility with existing logic that expects a single string:
        self.encryption = self.primary_encryption # Overwrite with primary for now
        self.authentication = self.primary_authentication # Overwrite with primary for now
        
        # WPA3 information (will be populated by scanner)
        self.wpa3_info = None
        
        self.validate()

    def __eq__(self, other):
        # Check if the other class type is either ArchivedTarget or Target
        return isinstance(other, (self.__class__, ArchivedTarget)) and self.bssid == other.bssid

    def transfer_info(self, other):
        """
            Helper function to transfer relevant fields into another Target or ArchivedTarget
        """
        other.wps = self.wps
        other.attacked = self.attacked

        if self.essid_known:
            if other.essid_known:
                other.decloaked = self.decloaked

            if not other.essid_known:
                other.decloaked = self.decloaked
                other.essid = self.essid
                other.essid_known = self.essid_known
                other.essid_len = self.essid_len

        # Transfer new fields as well
        if hasattr(self, 'primary_encryption'):
            other.primary_encryption = self.primary_encryption
            other.full_encryption_string = self.full_encryption_string
        if hasattr(self, 'primary_authentication'):
            other.primary_authentication = self.primary_authentication
            other.full_authentication_string = self.full_authentication_string
        if hasattr(self, 'wpa3_info'):
            other.wpa3_info = self.wpa3_info

        # Preserve honeypot analysis across scan cycles
        if hasattr(self, 'honeypot_score') and self.honeypot_score > 0:
            other.honeypot_score = self.honeypot_score
            other.honeypot_reasons = list(getattr(self, 'honeypot_reasons', []))

    @property
    def is_wpa3(self):
        """Check if target supports WPA3."""
        if self.wpa3_info is None:
            return False
        return self.wpa3_info.has_wpa3
    
    @property
    def is_transition(self):
        """Check if target is in WPA3 transition mode (supports both WPA2 and WPA3)."""
        if self.wpa3_info is None:
            return False
        return self.wpa3_info.is_transition
    
    @property
    def pmf_status(self):
        """Get PMF (Protected Management Frames) status."""
        if self.wpa3_info is None:
            return 'disabled'
        return self.wpa3_info.pmf_status
    
    @property
    def is_dragonblood_vulnerable(self):
        """Check if target is vulnerable to Dragonblood attacks."""
        if self.wpa3_info is None:
            return False
        return self.wpa3_info.dragonblood_vulnerable

    def validate(self):
        """ Checks that the target is valid. """
        if self.channel == -1:
            pass

        # Filter broadcast/multicast BSSIDs, see https://github.com/derv82/wifite2/issues/32
        bssid_broadcast = re.compile(r'^(ff:ff:ff:ff:ff:ff|00:00:00:00:00:00)$', re.IGNORECASE)
        if bssid_broadcast.match(self.bssid):
            raise Exception(f'Ignoring target with Broadcast BSSID ({self.bssid})')

        bssid_multicast = re.compile(r'^(01:00:5e|01:80:c2|33:33)', re.IGNORECASE)
        if bssid_multicast.match(self.bssid):
            raise Exception(f'Ignoring target with Multicast BSSID ({self.bssid})')

    def to_str(self, show_bssid=False, show_manufacturer=False):
        # sourcery no-metrics
        """
            *Colored* string representation of this Target.
            Specifically formatted for the 'scanning' table view.
        """

        max_essid_len = 24
        essid = self.essid if self.essid_known else f'({self.bssid})'
        # Trim ESSID (router name) if needed
        if len(essid) > max_essid_len:
            essid = f'{essid[:max_essid_len - 3]}...'
        else:
            essid = essid.ljust(max_essid_len)

        if self.essid_known:
            essid = Color.s('{C}%s' % essid)
        else:
            essid = Color.s('{D}%s' % essid)

        # Add a '*' if we decloaked the ESSID
        decloaked_char = Color.s('{P}*') if self.decloaked else ' '
        essid += decloaked_char

        bssid = Color.s('{D}%s{W}' % self.bssid) if show_bssid else ''
        if show_manufacturer:
            oui = ''.join(self.bssid.split(':')[:3])
            Configuration.load_manufacturers()
            self.manufacturer = Configuration.manufacturers.get(oui, "") if Configuration.manufacturers else ""

            max_oui_len = 21
            mfg_name = self.manufacturer
            if len(mfg_name) > max_oui_len:
                mfg_name = f'{mfg_name[:max_oui_len - 3]}...'
            else:
                mfg_name = mfg_name.ljust(max_oui_len)
            manufacturer = Color.s('{W}%s' % mfg_name)
        else:
            manufacturer = ''

        channel_color = '{C}' if int(self.channel) > 14 else '{W}'
        channel = Color.s(f'{channel_color}{str(self.channel).rjust(4)}{{W}}')

        # Build encryption display
        if self.is_transition:
            display_encryption = Color.s('{P}W2/W3')
            auth_suffix = ''
            if self.pmf_status == 'required':
                auth_suffix = Color.s('{G}+')
            elif self.pmf_status == 'optional':
                auth_suffix = Color.s('{O}~')
        else:
            enc = self.primary_encryption
            auth_suffix = ''
            if enc == 'WPA3':
                display_encryption = Color.s('{P}WPA3 ')
                if self.pmf_status == 'required':
                    auth_suffix = Color.s('{G}+')
                elif self.pmf_status == 'optional':
                    auth_suffix = Color.s('{O}~')
                if self.primary_authentication == 'MGT':
                    auth_suffix = Color.s('{R}-E') + auth_suffix
            elif enc == 'WPA2':
                display_encryption = Color.s('{O}WPA2 ')
                if self.primary_authentication == 'PSK':
                    auth_suffix = Color.s('{O}-P')
                elif self.primary_authentication == 'MGT':
                    auth_suffix = Color.s('{R}-E')
            elif enc == 'WPA':
                display_encryption = Color.s('{O}WPA  ')
                if self.primary_authentication == 'PSK':
                    auth_suffix = Color.s('{O}-P')
                elif self.primary_authentication == 'MGT':
                    auth_suffix = Color.s('{R}-E')
            elif enc == 'WEP':
                display_encryption = Color.s('{G}WEP  ')
            elif enc == 'OWE':
                display_encryption = Color.s('{B}OWE  ')
            else:
                display_encryption = Color.s('{W}%-5s' % enc)

        # Pad encryption column to fixed visible width (9 chars)
        # Strip ANSI to measure visible length
        vis_enc = self._ansi_re.sub('', f'{Color.s(str(display_encryption))}{Color.s(str(auth_suffix))}')
        enc_pad = ' ' * max(0, 9 - len(vis_enc))
        encryption_display_string = f'{display_encryption}{auth_suffix}{enc_pad}'

        # Signal strength bar + dBm value
        pwr_dbm = self.power
        if pwr_dbm > 50:
            pwr_bar = Color.s('{G}\u2588\u2588\u2588')
            pwr_color = 'G'
        elif pwr_dbm > 35:
            pwr_bar = Color.s('{O}\u2588\u2588{D}\u2591')
            pwr_color = 'O'
        elif pwr_dbm > 20:
            pwr_bar = Color.s('{R}\u2588{D}\u2591\u2591')
            pwr_color = 'R'
        else:
            pwr_bar = Color.s('{R}\u2591{D}\u2591\u2591')
            pwr_color = 'R'
        power = f'{pwr_bar} {Color.s("{%s}%s" % (pwr_color, str(pwr_dbm).rjust(2)))}'

        if self.wps == WPSState.UNLOCKED:
            wps = Color.s('{G}yes')
        elif self.wps == WPSState.NONE:
            wps = Color.s('{D}-')
        elif self.wps == WPSState.LOCKED:
            wps = Color.s('{R}lck')
        elif self.wps == WPSState.UNKNOWN:
            wps = Color.s('{O}?')
        else:
            wps = '-'

        if len(self.clients) > 0:
            clients = Color.s('{G}%s' % str(len(self.clients)))
        else:
            clients = Color.s('{D}-')

        # Honeypot indicator (only shown when --detect-honeypots is active)
        show_honeypot = Configuration.detect_honeypots
        if show_honeypot:
            hp_score = getattr(self, 'honeypot_score', 0)
            if hp_score >= 50:
                honeypot = Color.s('{R}!%d' % hp_score)
            elif hp_score >= 20:
                honeypot = Color.s('{O}?%d' % hp_score)
            else:
                honeypot = Color.s('{D}-')

        # Column widths must match scanner.py header
        COL_ESSID = 26
        COL_BSSID = 19
        COL_MFG = 23
        COL_CH = 4
        COL_ENC = 9
        COL_PWR = 7
        COL_WPS = 5
        COL_CLI = 7
        COL_HP = 5
        SEP = '  '

        parts = [self._pad_colored(essid, COL_ESSID)]
        if show_bssid:
            parts.append(self._pad_colored(bssid, COL_BSSID))
        if show_manufacturer:
            parts.append(self._pad_colored(manufacturer, COL_MFG))
        parts.append(self._pad_colored(channel, COL_CH, 'right'))
        parts.append(self._pad_colored(encryption_display_string, COL_ENC))
        parts.append(self._pad_colored(power, COL_PWR, 'right'))
        parts.append(self._pad_colored(wps, COL_WPS, 'center'))
        parts.append(self._pad_colored(clients, COL_CLI, 'right'))
        if show_honeypot:
            parts.append(self._pad_colored(honeypot, COL_HP, 'center'))

        result = SEP.join(parts)

        result += Color.s('{W}')
        return result


if __name__ == '__main__':
    fields = 'AA:BB:CC:DD:EE:FF,2015-05-27 19:28:44,2015-05-27 19:28:46,1,54,WPA2,CCMP ' \
             'TKIP,PSK,-58,2,0,0.0.0.0,9,HOME-ABCD,'.split(',')
    t = Target(fields)
    t.clients.append('asdf')
    t.clients.append('asdf')
    print((t.to_str()))
