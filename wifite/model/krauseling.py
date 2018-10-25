#!/usr/bin/env python
# -*- coding: utf-8 -*-

#from ..model.attack import Attack

import re, os, csv, time, signal

from ..util.color import Color
from ..tools.airmon import Airmon
from ..tools.airodump import Airodump
from ..util.scanner import Scanner
from ..config import Configuration
from shutil import copyfile

class Krauseling(object):
    def __init__(self):
        Color.s('You init"d!')
    
    def getMultipleInterfaces():
        Color.pl('Getting more than one interface for monitor mode.')

    @staticmethod
    def getTargetAP():
        while True: #make sure only one target is selected
            scanner = Scanner()
            targets = scanner.select_targets()
            if len(targets) > 1:
                Color.pl('Pick only one target for krauseling!')
                continue
            Color.pl('You picked: %s' % targets[0].bssid)
            break
        return targets[0]

    @staticmethod
    def run():
        Color.pl('You ran!')
        # get multiple interfaces in the future
        interface = Airmon.ask()
        # get multiple interfaces in the future
        target = Krauseling.getTargetAP()          

        with Airodump(channel=target.channel,
                    interface=interface,
                    target_bssid=target.bssid,
                    skip_wps=True,
                    output_file_prefix='krauseling') as airodump:
            Color.clear_entire_line
            #mimic wpa.py!
            Color.pl('Beginning to krauseling on channel: %s' % target.channel)
            while True:
                time.sleep(3)
                csv_files = airodump.find_files(endswith='.csv')
                if len(csv_files) == 0:
                    time.sleep(1)
                    continue
                csv_files = csv_files[0]

                temp_file = Configuration.temp('airodumpoutput.csv.bak')
                copyfile(csv_files, temp_file)

                with open(temp_file) as file:
                    reader = csv.reader(file)
                    for row in reader:
                        Color.pl(row)

                Color.pl('We made it to the end!') #debug statement

                os.remove(temp_file)
                break

if __name__ == '__main__':
    Color.s('You did it outside of wifite!')