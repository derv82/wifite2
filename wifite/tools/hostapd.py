#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import re
import os

from .dependency import Dependency
from ..config import Configuration
from ..util.process import Process

class Hostapd(Dependency):
    process_name = 'hostapd'

    dependency_required = False
    dependency_name = process_name
    dependency_url = 'apt-get install hostapd'


    @classmethod
    def exists(cls):
        return Process.exists(cls.process_name)


    def __init__(self, target, interface):
        self.target = target
        self.interface = interface
        self.pid = None
        self.config_file = None
        self.output_file = None
        self.output_write = None
        self.state = 'Initializing'


    def create_config_file(self):
        if not self.target.essid_known:
            self.state = 'Error: Target ESSID is not known'
            raise Exception('Cannot start hostapd if target has unknown SSID')

        self.config_file = os.path.abspath(os.path.join(Configuration.temp(), 'hostapd.conf'))

        with open(self.config_file, 'w') as config:
            config.write('driver=nl80211\n')
            config.write('ssid={}\n'.format(self.target.essid))
            # TODO: support 5ghz
            config.write('hw_mode=g\n')
            config.write('channel={}\n'.format(self.target.channel))
            config.write('logger_syslog=-1\n')
            config.write('logger_syslog_level=2\n')


    def start(self):
        self.create_config_file()

        self.killall()

        temp = Configuration.temp()
        self.output_file = os.path.abspath(os.path.join(temp, 'hostapd.out'))
        self.output_write = open(self.output_file, 'a')

        command = [
            self.process_name,
            '-i', self.interface,
            self.config_file
        ]

        self.pid = Process(command, stdout=self.output_write, cwd=temp)


    def stop(self):
        if self.pid and self.pid.poll() is not None:
            self.pid.interrupt()

        self.killall()
        # TODO: Wait until hostapd is completely stopped.

        if self.output_write:
            self.output_write.close()

        if self.config_file and os.path.exists(self.config_file):
            os.remove(self.config_file)

        if self.output_file and os.path.exists(self.output_file):
            os.remove(self.output_file)


    def killall(self):
        Process(['killall', self.process_name]).wait()


    def check(self):
        if self.pid.poll() is not None:
            raise Exception('hostapd stopped running, exit code: %d, output: %s' % (self.pid.poll(), self.pid.stdout()))
        # TODO: Check hostapd logs / output for any problems.

