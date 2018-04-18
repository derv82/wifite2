#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from ..model.interface import Interface
from ..tools.ifconfig import Ifconfig
from ..util.color import Color

class Macchanger(object):
    is_init = False
    is_changed = False
    original_mac = None

    @classmethod
    def init(cls):
        if cls.is_init: return
        from ..config import Configuration
        iface = Configuration.interface
        if type(iface) == Interface:
            iface = iface.interface
        cls.original_mac = Ifconfig.get_mac(iface)
        cls.is_init = True

    @classmethod
    def down_macch_up(cls, macch_option):
        cls.init()

        from ..util.process import Process
        from ..config import Configuration
        iface = Configuration.interface

        Color.clear_entire_line()
        Color.p("\r{+} {C}macchanger{W}: Taking interface {C}%s{W} down..." % iface)

        if Ifconfig.down(iface) != 0:
            Color.pl("{!} {C}macchanger{W}: Error running %s" % " ".join(cmd))
            Color.pl("{!} Output: %s, %s" % (ifdown.stdout(), ifdown.stderr()))
            return False

        cmd = ["macchanger", macch_option, iface]
        Color.clear_entire_line()
        Color.p("\r{+} {C}macchanger{W}: Changing MAC address of interface {C}%s{W}..." % iface)
        macch = Process(cmd)
        macch.wait()
        if macch.poll() != 0:
            Color.pl("{!} {C}macchanger{W}: Error running %s" % " ".join(cmd))
            Color.pl("{!} Output: %s, %s" % (macch.stdout(), macch.stderr()))
            return False

        Color.clear_entire_line()
        Color.p("\r{+} {C}macchanger{W}: Bringing interface {C}%s{W} up..." % iface)

        if Ifconfig.up(iface) != 0:
            Color.pl("{!} {C}macchanger{W}: Error running %s" % " ".join(cmd))
            Color.pl("{!} Output: %s, %s" % (ifup.stdout(), ifup.stderr()))
            return False
        return True

    @classmethod
    def reset(cls):
        # --permanent to reset to permanent MAC address
        if not cls.down_macch_up("-p"): return
        Color.pl("\r{+} {C}macchanger{W}: Resetting MAC address...")
        from ..config import Configuration
        new_mac = Ifconfig.get_mac(Configuration.interface)
        Color.clear_entire_line()
        Color.pl("\r{+} {C}macchanger{W}: Reset MAC address back to {C}%s{W}" % new_mac)

    @classmethod
    def random(cls):
        # Use --permanent to use random MAC address
        if not cls.down_macch_up("-r"): return
        cls.is_changed = True
        from ..config import Configuration
        new_mac = Ifconfig.get_mac(Configuration.interface)
        Color.clear_entire_line()
        Color.pl("\r{+} {C}macchanger{W}: Changed MAC address to {C}%s{W}" % new_mac)

    @classmethod
    def reset_if_changed(cls):
        if not cls.is_changed: return
        cls.reset()
