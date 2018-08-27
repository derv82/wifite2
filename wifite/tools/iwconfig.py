#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency

class Iwconfig(Dependency):
    dependency_required = True
    dependency_name = 'iwconfig'
    dependency_url = 'apt-get install wireless-tools'


    @classmethod
    def mode(cls, iface, mode_name):
        from ..util.process import Process

        pid = Process(['iwconfig', iface, 'mode', mode_name])
        pid.wait()

        return pid.poll()


    @classmethod
    def get_interfaces(cls, mode=None):
        from ..util.process import Process

        interfaces = set()
        iface = ''

        (out, err) = Process.call('iwconfig')
        for line in out.split('\n'):
            if len(line) == 0: continue

            if not line.startswith(' '):
                iface = line.split(' ')[0]
                if '\t' in iface:
                    iface = iface.split('\t')[0].strip()

                iface = iface.strip()
                if len(iface) == 0:
                    continue

                if mode is None:
                    interfaces.add(iface)

            if mode is not None and 'Mode:{}'.format(mode) in line and len(iface) > 0:
                interfaces.add(iface)

        return list(interfaces)

