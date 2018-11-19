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

class rssiStreamHandler(object):
    def __init__(self, streamFile):
        Color.s('You init"d!')
        self.steamFile = streamFile

    def captureValues(self):
        return 0

if __name__ == '__main__':
    Color.s('You did it outside of wifite!')
