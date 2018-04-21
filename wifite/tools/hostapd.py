#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import re
import os

from .dependency import Dependency
from ..config import Configuration

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
        # Save hostapd state?


    def create_config_file(self):
        if not self.target.essid_known:
            raise Exception('Cannot start hostapd if target has unknown SSID')

        config_file = os.path.abspath(os.path.join(Configuration.temp(), 'hostapd.conf'))

        with open(config_file, 'w') as config:
            config.write('driver=nl80211\n')
            config.write('ssid={}\n'.format(self.target.essid))
            config.write('hw_mode=g\n') # TODO: support 5ghz
            config.write('channel={}\n'.format(self.target.channel))
            config.write('logger_syslog=-1\n')
            config.write('logger_syslog_level=2\n')

        return config_file


    def start(self):
        config_file = self.create_config_file()

        self.killall()

        self.pid = Process([
            self.process_name,
            '-C', config_file,
            '-i', self.interface
        ])


    def stop(self):
        if self.pid:
            self.pid.interrupt()
        self.killall()
        # TODO: Wait until hostapd is completely stopped.


    def check(self):
        # TODO: Check if hostapd is still running, if there's any errors in the logs, etc.
        if self.pid.poll() is not None:
            # Process stopped
            pass


    def killall(self):
        Process(['killall', self.process_name]).wait()

