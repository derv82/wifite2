#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fix for raw_input on python3: https://stackoverflow.com/a/7321970
try:
    input = raw_input
except NameError:
    pass

raw_input = input

try:
    range = xrange
except NameError:
    pass

xrange = range
