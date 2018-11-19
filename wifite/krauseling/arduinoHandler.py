#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, os, csv, time, signal, sys

from ..util.color import Color
from ..tools.airmon import Airmon
from ..tools.airodump import Airodump
from ..util.scanner import Scanner
from ..config import Configuration
from shutil import copyfile
from subprocess import Popen, PIPE
from multiprocessing import Process, Pipe

class arduinoHandler(object):
    def __init__(self):
        Color.s('You init"d!')

if __name__ == '__main__':
    Color.s('You did it outside of wifite!')