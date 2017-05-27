#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Interface import Interface
from Color import Color

class Macchanger(object):
    is_init = False
    is_changed = False
    original_mac = None

    @classmethod
    def init(cls):
        if cls.is_init: return
        from Configuration import Configuration
        iface = Configuration.interface
        if type(iface) == Interface:
            iface = iface.name
        cls.original_mac = Interface.get_mac(iface)

    @classmethod
    def down_macch_up(cls, macch_option):
        cls.init()
        from Process import Process
        from Configuration import Configuration
        iface = Configuration.interface

        cmd = ["ifconfig", iface, "down"]
        Color.clear_entire_line()
        Color.p("\r{+} {C}macchanger{W}: Taking interface {C}%s{W} down..." % iface)
        ifdown = Process(cmd)
        ifdown.wait()
        if ifdown.poll() != 0:
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

        cmd = ["ifconfig", iface, "up"]
        Color.clear_entire_line()
        Color.p("\r{+} {C}macchanger{W}: Bringing interface {C}%s{W} up..." % iface)
        ifup = Process(cmd)
        ifup.wait()
        if ifup.poll() != 0:
            Color.pl("{!} {C}macchanger{W}: Error running %s" % " ".join(cmd))
            Color.pl("{!} Output: %s, %s" % (ifup.stdout(), ifup.stderr()))
            return False
        return True

    @classmethod
    def reset(cls):
        # --permanent to reset to permanent MAC address
        if not cls.down_macch_up("-p"): return
        Color.pl("\r{+} {C}macchanger{W}: Resetting MAC address...")
        from Configuration import Configuration
        new_mac = Interface.get_mac(Configuration.interface)
        Color.clear_entire_line()
        Color.pl("\r{+} {C}macchanger{W}: Reset MAC address back to {C}%s{W}" % new_mac)

    @classmethod
    def random(cls):
        # Use --permanent to use random MAC address
        if not cls.down_macch_up("-r"): return
        cls.is_changed = True
        from Configuration import Configuration
        new_mac = Interface.get_mac(Configuration.interface)
        Color.clear_entire_line()
        Color.pl("\r{+} {C}macchanger{W}: Changed MAC address to {C}%s{W}" % new_mac)

    @classmethod
    def reset_if_changed(cls):
        if not cls.is_changed: return
        cls.reset()
