#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from .dependency import Dependency


class Ip(Dependency):
    dependency_required = True
    dependency_name = 'ip'
    dependency_url = 'apt install iproute2'

    @classmethod
    def up(cls, interface, args=None):
        """Put interface up"""
        if args is None:
            args = []
        from ..util.process import Process

        command = ['ip', 'link', 'set', interface]
        if isinstance(args, list):
            command.extend(args)
        elif isinstance(args, str):
            command.append(args)
        command.append('up')

        pid = Process(command)
        pid.wait()
        if pid.poll() != 0:
            raise Exception('Error putting interface %s up:\n%s\n%s' % (interface, pid.stdout(), pid.stderr()))

    @classmethod
    def down(cls, interface):
        """Put interface down"""
        from ..util.process import Process

        pid = Process(['ip', 'link', 'set', interface, 'down'])
        pid.wait()
        if pid.poll() != 0:
            raise Exception('Error putting interface %s down:\n%s\n%s' % (interface, pid.stdout(), pid.stderr()))

    @classmethod
    def get_mac(cls, interface):
        from ..util.process import Process

        output = Process(['ip', 'link', 'show', interface]).stdout()

        if match := re.search(r'([a-fA-F\d]{2}[-:]){5}[a-fA-F\d]{2}', output):
            return match[0].replace('-', ':')

        raise Exception(f'Could not find the mac address for {interface}')
