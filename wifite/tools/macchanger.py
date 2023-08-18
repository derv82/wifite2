#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..tools.ip import Ip
from ..util.color import Color


class Macchanger(Dependency):
    dependency_required = False
    dependency_name = 'macchanger'
    dependency_url = 'apt install macchanger'

    is_changed = False

    @classmethod
    def down_macch_up(cls, iface, options):
        """Put interface down, run macchanger with options, put interface up"""
        from ..util.process import Process

        Color.clear_entire_line()
        Color.p(f'\r{{+}} {{C}}macchanger{{W}}: taking interface {{C}}{iface}{{W}} down...')

        Ip.down(iface)

        Color.clear_entire_line()
        Color.p(f'\r{{+}} {{C}}macchanger{{W}}: changing mac address of interface {{C}}{iface}{{W}}...')

        command = ['macchanger']
        command.extend(options)
        command.append(iface)
        macch = Process(command)
        macch.wait()
        if macch.poll() != 0:
            Color.pl(f'\n{{!}} {{R}}macchanger{{O}}: error running {{R}}{" ".join(command)}{{O}}')
            Color.pl(f'{{!}} {{R}}output: {{O}}{macch.stdout()}, {macch.stderr()}{{W}}')
            return False

        Color.clear_entire_line()
        Color.p(f'\r{{+}} {{C}}macchanger{{W}}: bringing interface {{C}}{iface}{{W}} up...')

        Ip.up(iface)

        return True

    @classmethod
    def get_interface(cls):
        # Helper method to get interface from configuration
        from ..config import Configuration
        return Configuration.interface

    @classmethod
    def reset(cls):
        iface = cls.get_interface()
        Color.pl(f'\r{{+}} {{C}}macchanger{{W}}: resetting mac address on {iface}...')
        # -p to reset to permanent MAC address
        if cls.down_macch_up(iface, ['-p']):
            new_mac = Ip.get_mac(iface)

            Color.clear_entire_line()
            Color.pl(
                f'\r{{+}} {{C}}macchanger{{W}}: reset mac address back to {{C}}{new_mac}{{W}} on {{C}}{iface}{{W}}')

    @classmethod
    def random(cls):
        from ..util.process import Process
        if not Process.exists('macchanger'):
            Color.pl('{!} {R}macchanger: {O}not installed')
            return

        iface = cls.get_interface()
        Color.pl(f'\n{{+}} {{C}}macchanger{{W}}: changing mac address on {{C}}{iface}{{W}}')

        # -r to use random MAC address
        # -e to keep vendor bytes the same
        if cls.down_macch_up(iface, ['-e']):
            cls.is_changed = True
            new_mac = Ip.get_mac(iface)

            Color.clear_entire_line()
            Color.pl(f'\r{{+}} {{C}}macchanger{{W}}: changed mac address to {{C}}{new_mac}{{W}} on {{C}}{iface}{{W}}')

    @classmethod
    def reset_if_changed(cls):
        if cls.is_changed:
            cls.reset()
