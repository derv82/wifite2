#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.color import Color
from ..config import Configuration

import os
import time
from json import loads, dumps

class CrackResult(object):
    ''' Abstract class containing results from a crack session '''

    # File to save cracks to, in PWD
    cracked_file = Configuration.cracked_file

    def __init__(self):
        self.date = int(time.time())
        self.readable_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.date))

    def dump(self):
        raise Exception('Unimplemented method: dump()')

    def to_dict(self):
        raise Exception('Unimplemented method: to_dict()')

    def print_single_line(self, longest_essid):
        raise Exception('Unimplemented method: print_single_line()')

    def print_single_line_prefix(self, longest_essid):
        essid = self.essid if self.essid else 'N/A'
        Color.p('{W} ')
        Color.p('{C}%s{W}' % essid.ljust(longest_essid))
        Color.p('  ')
        Color.p('{GR}%s{W}' % self.bssid.ljust(17))
        Color.p('  ')
        Color.p('{D}%s{W}' % self.readable_date.ljust(19))
        Color.p('  ')

    def save(self):
        ''' Adds this crack result to the cracked file and saves it. '''
        name = CrackResult.cracked_file
        saved_results = []
        if os.path.exists(name):
            with open(name, 'r') as fid:
                text = fid.read()
            try:
                saved_results = loads(text)
            except Exception as e:
                Color.pl('{!} error while loading %s: %s' % (name, str(e)))

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
        Color.pl('{+} saved crack result to {C}%s{W} ({G}%d total{W})'
            % (name, len(saved_results)))

    @classmethod
    def display(cls):
        ''' Show cracked targets from cracked file '''
        name = cls.cracked_file
        if not os.path.exists(name):
            Color.pl('{!} {O}file {C}%s{O} not found{W}' % name)
            return

        with open(name, 'r') as fid:
            cracked_targets = loads(fid.read())

        if len(cracked_targets) == 0:
            Color.pl('{!} {R}no results found in {O}%s{W}' % name)
            return

        Color.pl('\n{+} Displaying {G}%d{W} cracked target(s) from {C}%s{W}\n' % (
            len(cracked_targets), name))

        results = sorted([cls.load(item) for item in cracked_targets], key=lambda x: x.date, reverse=True)
        longest_essid = max([len(result.essid or 'ESSID') for result in results])

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
        if not os.path.exists(cls.cracked_file): return []
        with open(cls.cracked_file, 'r') as json_file:
            json = loads(json_file.read())
        return json

    @staticmethod
    def load(json):
        ''' Returns an instance of the appropriate object given a json instance '''
        if json['type'] == 'WPA':
            from .wpa_result import CrackResultWPA
            result = CrackResultWPA(json['bssid'],
                                    json['essid'],
                                    json['handshake_file'],
                                    json['key'])
        elif json['type'] == 'WEP':
            from .wep_result import CrackResultWEP
            result = CrackResultWEP(json['bssid'],
                                    json['essid'],
                                    json['hex_key'],
                                    json['ascii_key'])

        elif json['type'] == 'WPS':
            from .wps_result import CrackResultWPS
            result = CrackResultWPS(json['bssid'],
                                    json['essid'],
                                    json['pin'],
                                    json['psk'])

        elif json['type'] == 'PMKID':
            from .pmkid_result import CrackResultPMKID
            result = CrackResultPMKID(json['bssid'],
                                      json['essid'],
                                      json['pmkid_file'],
                                      json['key'])
        result.date = json['date']
        result.readable_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result.date))
        return result

if __name__ == '__main__':
    # Deserialize WPA object
    Color.pl('\nCracked WPA:')
    json = loads('{"bssid": "AA:BB:CC:DD:EE:FF", "essid": "Test Router", "key": "Key", "date": 1433402428, "handshake_file": "hs/capfile.cap", "type": "WPA"}')
    obj = CrackResult.load(json)
    obj.dump()

    # Deserialize WEP object
    Color.pl('\nCracked WEP:')
    json = loads('{"bssid": "AA:BB:CC:DD:EE:FF", "hex_key": "00:01:02:03:04", "ascii_key": "abcde", "essid": "Test Router", "date": 1433402915, "type": "WEP"}')
    obj = CrackResult.load(json)
    obj.dump()

    # Deserialize WPS object
    Color.pl('\nCracked WPS:')
    json = loads('{"psk": "the psk", "bssid": "AA:BB:CC:DD:EE:FF", "pin": "01234567", "essid": "Test Router", "date": 1433403278, "type": "WPS"}')
    obj = CrackResult.load(json)
    obj.dump()
