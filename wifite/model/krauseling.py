#!/usr/bin/env python
# -*- coding: utf-8 -*-

#from ..model.attack import Attack

import re, os

from ..util.color import Color
from ..tools.airmon import Airmon
from ..util.scanner import Scanner


class Krauseling(object):
    def __init__(self):
        Color.s('You init"d!')
    
    @staticmethod
    def run():
        Color.pl('You ran!')
        interface = Airmon.ask()
        scanner = Scanner()
        targets = scanner.select_targets()
        #with Airodump....
        



if __name__ == '__main__':
    Color.s('You did it outside of wifite!')