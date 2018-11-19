#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, os, csv, time, signal, sys

from krauseling import rssiStreamHandler

from ..util.color import Color
from ..tools.airmon import Airmon
from ..tools.airodump import Airodump
from ..util.scanner import Scanner
from ..config import Configuration
from shutil import copyfile
from subprocess import Popen, PIPE
from multiprocessing import Process, Pipe

class Krauseling(object):
    def __init__(self):
        Color.s('You init"d!')

    @staticmethod
    def getTargetAP():
        while True: #make sure only one target is selected
            scanner = Scanner()
            targets = scanner.select_targets()
            if len(targets) > 1:
                Color.pl('Pick only one target for krauseling!')
                continue
            Color.pl('You picked: %s' % targets[0].essid)
            break
        return targets[0]

    @staticmethod
    def rssiStream(target, interface, pipedConnection):
        targetArg = 'wlan.sa==' + target.bssid
        # camp the interface on desired channel
        channelCommand = ['iwconfig', Configuration.interface, 'channel', target.channel]
        channelCamp = Popen(channelCommand)
        channelCamp.wait()
       #command = 'sudo tshark -f "type mgt subtype beacon" -Y wlan.sa==48:5D:36:03:A9:24 -T fields -e radiotap.dbm_antsignal -i wlan0mon'
        command = ['sudo', 'tshark', 
            '-f', '"type', 'mgt', 'subtype', 'beacon"',
            '-Y', targetArg,
            '-Tfields', 
            '-eradiotap.dbm_antsignal',
            '-i', interface]
        
        if Configuration.verbose > 1:
            Color.pe('\n {C}[?] {W} Executing: {B}%s{W}' % command)
        streamProcess = Popen(command, stderr=PIPE)
        while True:
            pipedConnection.send(streamProcess.stderr)
            # clean up output once handler is implemented 

    @staticmethod
    def run():
        Color.pl('You ran!')
        # get multiple interfaces in the future
        Configuration.interface = Airmon.ask()
        # get multiple interfaces in the future
        target = Krauseling.getTargetAP()
        Color.pl("Made it out of target picking.")
        try:
            # Loop until interrupted (Ctrl+C)
            Color.pl("Into the try! Ctrl+C to quit")
            parent_conn, child_conn = Pipe()
            Color.pl(Configuration.interface)
            stream1 = Process(target=Krauseling.rssiStream, args=(target, Configuration.interface, child_conn,))
            stream1.start()

            rssiHandler1 = rssiStreamHandler()

            output1 = parent_conn.recv() # pass to rssi Handler
            
            while True:
                sys.stderr.write(parent_conn.recv())
        except KeyboardInterrupt:
            pass   
        stream1.join()
        Color.pl("End of krauseling")    

if __name__ == '__main__':
    Color.s('You did it outside of wifite!')