#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from .dependency import Dependency


def _check_iface(name):
    """Validate interface name before passing to subprocess (SEC-010)."""
    from ..config.validators import validate_interface_name
    validate_interface_name(name)


class Ip(Dependency):
    dependency_required = True
    dependency_name = 'ip'
    dependency_url = 'apt install iproute2'
    dependency_packages = {
        'apt': 'iproute2', 'pacman': 'iproute2', 'dnf': 'iproute',
        'apk': 'iproute2',
    }
    dependency_category = Dependency.CATEGORY_CORE

    @classmethod
    def up(cls, interface):
        """Put interface up"""
        from ..util.process import Process

        _check_iface(interface)
        (out, err) = Process.call(f'ip link set {interface} up')
        if len(err) > 0:
            raise Exception('Error putting interface %s up:\n%s\n%s' % (interface, out, err))

    @classmethod
    def down(cls, interface):
        """Put interface down"""
        from ..util.process import Process

        _check_iface(interface)
        (out, err) = Process.call(f'ip link set {interface} down')
        if len(err) > 0:
            raise Exception('Error putting interface %s down:\n%s\n%s' % (interface, out, err))

    @classmethod
    def get_mac(cls, interface):
        from ..util.process import Process

        _check_iface(interface)
        (out, err) = Process.call(f'ip link show {interface}')
        if match := re.search(r'([a-fA-F\d]{2}[-:]){5}[a-fA-F\d]{2}', out):
            return match[0].replace('-', ':')

        raise Exception(f'Could not find the mac address for {interface}')
