#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from ..tools.ifconfig import Ifconfig
from ..util.color import Color

import re

class Interface(object):
    '''
        Represents an 'interface' known by airmon-ng
    '''

    def __init__(self, fields):
        '''
            Initializes & stores info about an interface.

            Args:
                Fields - list of fields
                        0: PHY
                        1: INTERFACE
                        2: DRIVER
                        3: CHIPSET
        '''
        if len(fields) == 3:
            phy = 'phyX'
            match = re.search(' - \[(phy\d+)\]', fields[2])
            if match:
                phy = match.groups()[0]
                fields[2] = fields[2][:fields[2].rfind(' - [')]
            fields.insert(0, phy)
        if len(fields) != 4:
            raise Exception("Expected 4, got %d in %s" % (len(fields), fields))
        self.phy = fields[0].strip()
        self.interface = fields[1].strip()
        self.driver = fields[2].strip()
        self.chipset = fields[3].strip()

    # Max length of fields.
    # Used for printing a table of interfaces.
    PHY_LEN = 6
    INTERFACE_LEN = 12
    DRIVER_LEN = 20
    CHIPSET_LEN = 30

    def __str__(self):
        ''' Colored string representation of interface '''
        s = Color.s('{W}%s' % self.phy.ljust(self.PHY_LEN))
        s += Color.s('{G}%s' % self.interface.ljust(self.INTERFACE_LEN))
        s += Color.s('{C}%s' % self.driver.ljust(self.DRIVER_LEN))
        s += Color.s('{W}%s' % self.chipset.ljust(self.CHIPSET_LEN))
        return s

    @staticmethod
    def menu_header():
        ''' Colored header row for interfaces '''
        s = '    '
        s += 'PHY'.ljust(Interface.PHY_LEN)
        s += 'Interface'.ljust(Interface.INTERFACE_LEN)
        s += 'Driver'.ljust(Interface.DRIVER_LEN)
        s += 'Chipset'.ljust(Interface.CHIPSET_LEN)
        s += '\n'
        s += '-' * (Interface.PHY_LEN + Interface.INTERFACE_LEN + Interface.DRIVER_LEN + Interface.CHIPSET_LEN + 3)
        return s

    @staticmethod
    def get_mac(iface=None):
        from ..config import Configuration
        from ..util.process import Process

        if iface is None:
            Configuration.initialize()
            iface = Configuration.interface
        if iface is None:
            raise Exception('Interface must be defined (-i)')

        Ifconfig.get_mac(iface)

if __name__ == '__main__':
    mac = Interface.get_mac()
    print('wlan0mon mac address:', mac)
