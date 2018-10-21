#!/usr/bin/env python
# -*- coding: utf-8 -*-

#from ..model.attack import Attack

import re, os

from ..util.color import Color

class Krauseling(object):
    def __init__(self):
        Color.s('You init"d!')
    
    @staticmethod
    def run():
        Color.pl('You ran!')


if __name__ == '__main__':
    Color.s('You did it outside of wifite!')