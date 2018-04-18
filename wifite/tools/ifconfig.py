#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import re

class Ifconfig(object):

    @classmethod
    def up(cls, interface, args=[]):
        '''Put interface up'''
        from ..util.process import Process

        command = ['ifconfig', interface, 'up']
        if type(args) is list:
            command.extend(args)
        elif type(args) is 'str':
            command.append(args)

        pid = Process(command)
        pid.wait()
        return pid.poll() == 0


    @classmethod
    def down(cls, interface):
        '''Put interface down'''
        from ..util.process import Process

        command = ['ifconfig', interface, 'down']
        if type(args) is list:
            command.extend(args)
        elif type(args) is 'str':
            command.append(args)

        pid = Process(command)
        pid.wait()
        return pid.poll() == 0


    @classmethod
    def get_mac(cls, interface):
        from ..util.process import Process

        output = Process(['ifconfig', interface]).stdout()

        mac_regex = ('[a-zA-Z0-9]{2}-' * 6)[:-1]
        match = re.search(' (%s)' % mac_regex, output)

        if not match:
            raise Exception('Could not find the mac address for %s' % interface)

        return match.groups()[0].replace('-', ':')

