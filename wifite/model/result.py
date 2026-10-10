#!/usr/bin/env python
# -*- coding: utf-8 -*-*

from ..util.color import Color
from ..config import Configuration

import os
import re
import time
from json import loads, dumps


class CrackResult:
    """ Abstract class containing results from a crack session """

    # File to save cracks to, in PWD
    cracked_file = Configuration.cracked_file

    def __init__(self):
        self.date = int(time.time())
        self.readable_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.date))

    def dump(self):
        raise NotImplementedError('Subclasses must implement dump()')

    def to_dict(self):
        raise NotImplementedError('Subclasses must implement to_dict()')

    def print_single_line(self, longest_essid):
        raise NotImplementedError('Subclasses must implement print_single_line()')

    def print_single_line_prefix(self, longest_essid):
        essid = self.essid or 'N/A'
        Color.p('{W} ')
        Color.p('{C}%s{W}' % essid.ljust(longest_essid))
        Color.p('  ')
        Color.p('{GR}%s{W}' % self.bssid.ljust(17))
        Color.p('  ')
        Color.p('{D}%s{W}' % self.readable_date.ljust(19))
        Color.p('  ')

    def save(self):
        """ Adds this crack result to the cracked file and saves it. """
        name = CrackResult.cracked_file
        saved_results = []
        if os.path.exists(name):
            with open(name, 'r') as fid:
                text = fid.read()
            try:
                saved_results = loads(text)
            except (ValueError, TypeError) as e:
                Color.pl('{!} JSON parsing error in %s: %s' % (name, str(e)))
            except (OSError, IOError) as e:
                Color.pl('{!} File access error for %s: %s' % (name, str(e)))
            except Exception as e:
                Color.pl('{!} Unexpected error loading %s: %s' % (name, str(e)))

        # Check for duplicates
        this_dict = self.to_dict()
        this_dict.pop('date')
        for entry in saved_results:
            this_dict['date'] = entry.get('date')
            if entry == this_dict:
                # Skip if we already saved this BSSID+ESSID+TYPE+KEY
                Color.pl('{+} {C}%s{O} already exists in {G}%s{O}, skipping.' % (
                    self.essid, Configuration.cracked_file))
                return

        saved_results.append(self.to_dict())
        with open(name, 'w') as fid:
            fid.write(dumps(saved_results, indent=2))
        Color.pl('{+} saved result to {C}%s{W} ({G}%d total{W})'
                 % (name, len(saved_results)))

    @classmethod
    def display(cls, result_type):
        """ Show targets from results file """
        name = cls.cracked_file
        if not os.path.exists(name):
            Color.pl('{!} {O}file {C}%s{O} not found{W}' % name)
            return

        targets = cls.load_all()
        only_cracked = result_type == 'cracked'

        if only_cracked:
            targets = [item for item in targets if item.get('type') != 'IGN']
        else:
            targets = [item for item in targets if item.get('type') == 'IGN']

        if len(targets) == 0:
            Color.pl('{!} {R}no results found in {O}%s{W}' % name)
            return

        Color.pl('\n{+} Displaying {G}%d{W} %s target(s) from {C}%s{W}\n' % (
            len(targets), result_type, cls.cracked_file))

        results = sorted([cls.load(item) for item in targets], key=lambda x: x.date, reverse=True)
        longest_essid = max(len(result.essid or 'ESSID') for result in results)

        # Header
        Color.p('{D} ')
        Color.p('ESSID'.ljust(longest_essid))
        Color.p('  ')
        Color.p('BSSID'.ljust(17))
        Color.p('  ')
        Color.p('DATE'.ljust(19))
        Color.p('  ')
        Color.p('TYPE'.ljust(5))
        Color.p('  ')
        if only_cracked:
            Color.p('KEY')
            Color.pl('{D}')
            Color.p(' ' + '-' * (longest_essid + 17 + 19 + 5 + 11 + 12))
        Color.pl('{W}')
        # Results
        for result in results:
            result.print_single_line(longest_essid)
        Color.pl('')

    @classmethod
    def load_all(cls):
        if not os.path.exists(cls.cracked_file):
            return []
        with open(cls.cracked_file, 'r') as json_file:
            try:
                json = loads(json_file.read())
            except ValueError:
                return []
        return json

    @classmethod
    def load_ignored_bssids(cls, ignore_cracked=False):
        json = cls.load_all()
        ignored_bssids = [
            item.get('bssid', '')
            for item in json
            if item.get('type') == 'IGN'
        ]

        if not ignore_cracked:
            return ignored_bssids

        return ignored_bssids + [
            item.get('bssid', '')
            for item in json
            if item.get('type') != 'IGN'
        ]

    @classmethod
    def load_captured_bssids(cls, hs_dir):
        """Scan hs_dir for captured handshake/PMKID files and return list of BSSIDs."""
        bssids = set()
        if not os.path.isdir(hs_dir):
            return []

        bssid_re = re.compile(r'^(?:handshake|pmkid)_.+_([0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2})_', re.IGNORECASE)
        for fname in os.listdir(hs_dir):
            m = bssid_re.match(fname)
            if m:
                bssids.add(m.group(1).replace('-', ':').upper())

        return list(bssids)

    @staticmethod
    def load(json):
        """ Returns an instance of the appropriate object given a json instance """
        result = None
        if json['type'] == 'WPA':
            from .wpa_result import CrackResultWPA
            result = CrackResultWPA(bssid=json['bssid'],
                                    essid=json['essid'],
                                    handshake_file=json['handshake_file'],
                                    key=json['key'])
        elif json['type'] == 'WEP':
            from .wep_result import CrackResultWEP
            result = CrackResultWEP(bssid=json['bssid'],
                                    essid=json['essid'],
                                    hex_key=json['hex_key'],
                                    ascii_key=json['ascii_key'])

        elif json['type'] == 'WPS':
            from .wps_result import CrackResultWPS
            result = CrackResultWPS(bssid=json['bssid'],
                                    essid=json['essid'],
                                    pin=json['pin'],
                                    psk=json['psk'])

        elif json['type'] == 'PMKID':
            from .pmkid_result import CrackResultPMKID
            result = CrackResultPMKID(bssid=json['bssid'],
                                      essid=json['essid'],
                                      pmkid_file=json['pmkid_file'],
                                      key=json['key'])

        elif json['type'] == 'Evil Twin':
            from .eviltwin_result import CrackResultEvilTwin
            result = CrackResultEvilTwin(bssid=json['bssid'],
                                         essid=json['essid'],
                                         key=json['key'],
                                         clients_connected=json.get('clients_connected', 0),
                                         credential_attempts=json.get('credential_attempts', 0),
                                         validation_time=json.get('validation_time', 0.0),
                                         portal_template=json.get('portal_template', 'generic'))

        else:
            from .ignored_result import CrackResultIgnored
            result = CrackResultIgnored(bssid=json['bssid'],
                                        essid=json['essid'])

        result.date = json['date']
        result.readable_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result.date))
        return result

    @classmethod
    def ignore_target(cls, target):
        ignored_targets = cls.load_all()

        for ignored_target in ignored_targets:
            is_ignored = ignored_target.get('type') == 'IGN'
            bssid_match = target.bssid == ignored_target.get('bssid')
            essid_match = target.essid == ignored_target.get('essid')
            if is_ignored and bssid_match and essid_match:
                return

        from .ignored_result import CrackResultIgnored
        ignored_target = CrackResultIgnored(target.bssid, target.essid)
        ignored_target.save()

if __name__ == '__main__':
    # Deserialize WPA object
    Color.pl('\nCracked WPA:')
    json = loads(
        '{"bssid": "AA:BB:CC:DD:EE:FF", "essid": "Test Router", "key": "Key", "date": 1433402428, '
        '"handshake_file": "hs/capfile.cap", "type": "WPA"}')
    obj = CrackResult.load(json)
    obj.dump()

    # Deserialize WEP object
    Color.pl('\nCracked WEP:')
    json = loads(
        '{"bssid": "AA:BB:CC:DD:EE:FF", "hex_key": "00:01:02:03:04", "ascii_key": "abcde", '
        '"essid": "Test Router", "date": 1433402915, "type": "WEP"}')
    obj = CrackResult.load(json)
    obj.dump()

    # Deserialize WPS object
    Color.pl('\nCracked WPS:')
    json = loads(
        '{"psk": "the psk", "bssid": "AA:BB:CC:DD:EE:FF", "pin": "01234567", "essid": "Test Router", '
        '"date": 1433403278, "type": "WPS"}')
    obj = CrackResult.load(json)
    obj.dump()

    # Deserialize Ignored object
    Color.pl('\nIgnored:')
    json = loads(
        '{"bssid": "AA:BB:CC:DD:EE:FF", "essid": "Test Router", '
        '"date": 1433403278, "type": "IGN"}')
    obj = CrackResult.load(json)
    obj.dump()
