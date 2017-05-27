#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Color import Color

import re

class Interface(object):
    '''
        Represents an 'interface' known by airmon-ng
    '''

    # Max length of fields.
    # Used for printing a table of interfaces.
    PHY_LEN = 6
    NAME_LEN = 12
    DRIVER_LEN = 20
    CHIPSET_LEN = 30

    def __init__(self, fields):
        '''
            Initializes & stores info about an interface.

            Args:
                Fields - list of fields
                        0: PHY
                        1: NAME
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
        self.name = fields[1].strip()
        self.driver = fields[2].strip()
        self.chipset = fields[3].strip()

    def __str__(self):
        ''' Colored string representation of interface '''
        s = Color.s("{W}%s" % self.phy)
        s += ' ' * max(Interface.PHY_LEN - len(self.phy), 0)

        s += Color.s("{G}%s" % self.name)
        s += ' ' * max(Interface.NAME_LEN - len(self.name), 0)

        s += Color.s("{C}%s" % self.driver)
        s += ' ' * max(Interface.DRIVER_LEN - len(self.driver), 0)

        s += Color.s("{W}%s" % self.chipset)
        s += ' ' * max(Interface.CHIPSET_LEN - len(self.chipset), 0)
        return s

    @staticmethod
    def menu_header():
        ''' Colored header row for interfaces '''
        s = '    '
        s += 'PHY'
        s += ' ' * (Interface.PHY_LEN - len("PHY"))

        s += 'Interface'
        s += ' ' * (Interface.NAME_LEN - len("Interface"))
        s += 'Driver'
        s += ' ' * (Interface.DRIVER_LEN - len("Driver"))

        s += 'Chipset'
        s += ' ' * (Interface.CHIPSET_LEN - len("Chipset"))

        s += '\n---'
        s += '-' * (Interface.PHY_LEN + Interface.NAME_LEN + Interface.DRIVER_LEN + Interface.CHIPSET_LEN)
        return s

    @staticmethod
    def get_mac(iface=None):
        from Configuration import Configuration
        from Process import Process
        import re

        if iface == None:
            Configuration.initialize()
            iface = Configuration.interface
        if iface == None:
            raise Exception('Interface must be defined (-i)')

        output = Process(['ifconfig', iface]).stdout()
        mac_regex = ('[a-zA-Z0-9]{2}-' * 6)[:-1]
        match = re.search(' (%s)' % mac_regex, output)
        if not match:
            match = re.search('unspec (%s)' % mac_regex, output)
            if not match:
                raise Exception('Could not find the mac address for %s' % iface)
        return match.groups()[0].replace('-', ':')

if __name__ == '__main__':
    mac = Interface.get_mac()
    print 'wlan0mon mac address:', mac
