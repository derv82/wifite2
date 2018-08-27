#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..util.process import Process
import re

class Pyrit(Dependency):
    ''' Wrapper for Pyrit program. '''
    dependency_required = False
    dependency_name = 'pyrit'
    dependency_url = 'https://github.com/JPaulMora/Pyrit/wiki'

    def __init__(self):
        pass


    @staticmethod
    def bssid_essid_with_handshakes(capfile, bssid=None, essid=None):
        if not Pyrit.exists():
            return []

        command = [
            'pyrit',
            '-r', capfile,
            'analyze'
        ]
        pyrit = Process(command, devnull=False)

        current_bssid = current_essid = None
        bssid_essid_pairs = set()

        '''
        #1: AccessPoint 18:a6:f7:31:d2:06 ('TP-LINK_D206'):
          #1: Station 08:66:98:b2:ab:28, 1 handshake(s):
              #1: HMAC_SHA1_AES, good, spread 1
                #2: Station ac:63:be:3a:a2:f4
        '''

        for line in pyrit.stdout().split('\n'):
            mac_regex = ('[a-zA-Z0-9]{2}:' * 6)[:-1]
            match = re.search("^#\d+: AccessPoint (%s) \('(.*)'\):$" % (mac_regex), line)
            if match:
                # We found a new BSSID and ESSID
                (current_bssid, current_essid) = match.groups()

                if bssid is not None and bssid.lower() != current_bssid:
                    current_bssid = None
                    current_essid = None
                elif essid is not None and essid != current_essid:
                    current_bssid = None
                    current_essid = None

            elif current_bssid is not None and current_essid is not None:
                # We hit an AP that we care about.
                # Line does not contain AccessPoint, see if it's 'good'
                if ', good' in line:
                    bssid_essid_pairs.add( (current_bssid, current_essid) )

        return list(bssid_essid_pairs)
