#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency

class Iw(Dependency):
    dependency_required = True
    dependency_name     = 'iw'
    dependency_url      = 'apt-get install iw'

    @classmethod
    def mode(cls, iface, mode_name):
        from ..util.process import Process

        pid = None
        if mode_name == "monitor":
            pid = Process(['iw', iface, 'set monitor control'])
        else:
            pid = Process(['iw', iface, 'type', mode_name])
        pid.wait()

        return pid.poll()

    @classmethod
    def get_interfaces(cls, mode=None):
        from ..util.process import Process
        import re

        ireg = re.compile(r"\s+Interface\s[a-zA-Z0-9]+")
        mreg = re.compile(r"\s+type\s[a-zA-z]+")
        ires = None
        mres = None

        interfaces = set()
        iface = ''

        (out, err) = Process.call('iw dev')
        if mode is None:
            for line in out.split('\n'):
                ires = ireg.search(line)
                if ires:
                    interfaces.add(ires.group().split("Interface")[-1])
        else:
            for line in out.split('\n'):
                ires = ireg.search(line)
                mres = mreg.search(line)
                if mres:
                    if mode == mres.group().split("type")[-1][1:]:
                        interfaces.add(iface)
                if ires:
                    iface = ires.group().split("Interface")[-1][1:]

        return list(interfaces)
