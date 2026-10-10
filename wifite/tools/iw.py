#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency


def _check_iface(name):
    """Validate interface name before passing to subprocess (SEC-010)."""
    from ..config.validators import validate_interface_name
    validate_interface_name(name)


class Iw(Dependency):
    dependency_required = True
    dependency_name = 'iw'
    dependency_url = 'apt install iw'
    dependency_packages = {
        'apt': 'iw', 'pacman': 'iw', 'dnf': 'iw',
        'apk': 'iw', 'brew': 'iw',
    }
    dependency_category = Dependency.CATEGORY_CORE

    @classmethod
    def mode(cls, iface, mode_name):
        from ..util.process import Process

        _check_iface(iface)
        # Use correct iw syntax: iw dev <interface> set type <mode>
        return Process.call(f'iw dev {iface} set type {mode_name}')

    @classmethod
    def get_interfaces(cls, mode=None):
        from ..util.process import Process
        import re

        ireg = re.compile(r"\s+Interface\s[a-zA-Z\d]+")
        mreg = re.compile(r"\s+type\s[a-zA-Z]+")

        interfaces = set()
        iface = ''

        (out, err) = Process.call('iw dev')
        if mode is None:
            for line in out.split('\n'):
                if ires := ireg.search(line):
                    interfaces.add(ires.group().split("Interface")[-1].strip())
        else:
            for line in out.split('\n'):
                ires = ireg.search(line)
                if mres := mreg.search(line):
                    if mode == mres.group().split("type")[-1].strip():
                        interfaces.add(iface)
                if ires:
                    iface = ires.group().split("Interface")[-1].strip()

        return list(interfaces)

    @classmethod
    def is_monitor(cls, iface):
        """Check if the given interface is in monitor mode"""
        monitor_interfaces = cls.get_interfaces(mode='monitor')
        return iface in monitor_interfaces
