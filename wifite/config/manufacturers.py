#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OUI manufacturer database loading logic."""

import os
import re


def load_manufacturers(cls):
    """Lazy-load OUI manufacturer database on first access."""
    if cls._manufacturers_loaded:
        return
    cls._manufacturers_loaded = True
    if os.path.isfile('/usr/share/ieee-data/oui.txt'):
        mfr_file = '/usr/share/ieee-data/oui.txt'
    else:
        mfr_file = 'ieee-oui.txt'
    if os.path.exists(mfr_file):
        cls.manufacturers = {}
        with open(mfr_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not re.match(r'^\w', line):
                    continue
                line = line.replace('(hex)', '').replace('(base 16)', '')
                fields = line.split()
                if len(fields) >= 2:
                    cls.manufacturers[fields[0]] = ' '.join(fields[1:]).rstrip('.')
