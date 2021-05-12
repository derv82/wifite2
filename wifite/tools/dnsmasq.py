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
        self.config_file = None


    def create_config_file(self):
        self.config_file = os.path.join(Configuration.temp(), 'dnsmasq.conf')
        if os.path.exists(self.config_file):
            os.remove(self.config_file)

        with open(self.config_file, 'w') as config:
            config.write('interface={}\n'.format(self.interface))
            config.write('dhcp-range=10.0.0.10,10.0.0.100,8h\n')
            config.write('dhcp-option=3,10.0.0.1\n')
            config.write('dhcp-option=6,10.0.0.1\n')
            config.write('server=8.8.8.8\n')
            config.write('log-queries\n')
            config.write('log-dhcp\n')


    def start(self):
        self.create_config_file()

        # Stop already-running dnsmasq process
        self.killall()

        # Start new dnsmasq process
        self.pid = Process([
            'dnsmasq',
            '-C', self.config_file
        ])


    def stop(self):
        # Kill dnsmasq process
        if self.pid and self.pid.poll() is not None:
            self.pid.interrupt()

        self.killall()

        if self.config_file and os.path.exists(self.config_file):
            os.remove(self.config_file)


    def killall(self):
        Process(['killall', 'dnsmasq']).wait()
        # TODO: Wait until dnsmasq is completely stopped.


    def check(self):
        if self.pid.poll() is not None:
            raise Exception('dnsmasq stopped running, exit code: %d, output: %s' % (self.pid.poll(), self.pid.stdout()))
        # TODO: Check logs/output for problems

