#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import os

from .dependency import Dependency
from ..util.process import Process
from ..config import Configuration

class Dnsmasq(Dependency):
    '''Wrapper for dnsmasq program.'''
    dependency_required = False
    dependency_name = 'dnsmasq'
    dependency_url = 'apt-get install dnsmasq'

    def __init__(self, interface):
        self.interface = interface
        self.pid = None


    def create_config_file(self):
        config_file = os.path.join(Configuration.temp(), 'dnsmasq.conf')
        if os.path.exists(config_file):
            os.remove(config_file)

        with open(config_file, 'w') as config:
            config.write('interface={}\n'.format(self.interface))
            config.write('dhcp-range=10.0.0.10,10.0.0.100,8h\n')
            config.write('dhcp-option=3,10.0.0.1\n')
            config.write('dhcp-option=6,10.0.0.1\n')
            config.write('server=8.8.8.8\n')
            config.write('log-queries\n')
            config.write('log-dhcp\n')
        return config_file


    def start(self):
        config_file = self.create_config_file()

        # Stop already-running dnsmasq process
        self.killall()

        # Start new dnsmasq process
        self.pid = Process([
            'dnsmasq',
            '-C', config_file
        ])


    def stop(self):
        # Kill dnsmasq process
        if self.pid:
            self.pid.interrupt()
        self.killall()
        # TODO: Wait until dnsmasq is completely stopped.


    def check(self):
        # TODO: Check if dnsmasq is still running, if there's any errors in the logs, etc.
        if self.pid.poll() is not None:
            # Process stopped
            pass


    def killall(self):
        Process(['killall', 'dnsmasq']).wait()

