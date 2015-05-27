#!/usr/bin/python

from Interface import Interface
from Process import Process
from Color import Color

class Airmon(object):
    ''' Wrapper around the 'airmon-ng' program '''

    def __init__(self):
        self.refresh()

    def refresh(self):
        ''' Get airmon-recognized interfaces '''
        self.interfaces = Airmon.get_interfaces()

    def print_menu(self):
        ''' Prints menu '''
        print Interface.menu_header()
        for (index, iface) in enumerate(self.interfaces):
            Color.pl(" {G}%d{W}. %s" % (index + 1, iface))

    def get(self, index):
        ''' Gets interface at index (starts at 1) '''
        if type(index) == str:
            index = int(index)
        return self.interfaces[index - 1]


    @staticmethod
    def get_interfaces():
        '''
            Returns:
                List of Interface objects known by airmon-ng
        '''
        interfaces = []
        p = Process('airmon-ng')
        for line in p.stdout().split('\n'):
            # Ignore blank/header lines
            if len(line) == 0: continue
            if line.startswith('Interface'): continue
            if line.startswith('PHY'): continue

            # Strip out interface information
            fields = line.split("\t")
            while '' in fields:
                fields.remove('')
            # Add Interface object to list
            interfaces.append(Interface(fields))
        return interfaces

    @staticmethod
    def start(iface):
        '''
            Starts an interface (iface) in monitor mode
            Args:
                iface - The interface to start in monitor mode
                        Either an instance of Interface object,
                        or the name of the interface (string).
            Returns:
                Name of the interface put into monitor mode.
            Throws:
                Exception - If an interface can't be put into monitor mode
        '''
        # Get interface name from input
        if type(iface) == Interface:
            iface = iface.name

        # Call airmon-ng
        Color.p("{+} enabling {G}monitor mode{W} on {C}%s{W}... " % iface)
        (out,err) = Process.call(['airmon-ng', 'start', iface])

        # Find the interface put into monitor mode (if any)
        mon_iface = None
        for line in out.split('\n'):
            if 'monitor mode' in line and 'enabled' in line and ' on ' in line:
                mon_iface = line.split(' on ')[1]
                if ']' in mon_iface:
                    mon_iface = mon_iface.split(']')[1]
                if ')' in mon_iface:
                    mon_iface = mon_iface.split(')')[0]
                break

        if mon_iface == None:
            # Airmon did not enable monitor mode on an interface
            Color.pl("{R}failed{W}")

        mon_ifaces = Airmon.get_interfaces_in_monitor_mode()

        # Assert that there is an interface in monitor mode
        if len(mon_ifaces) == 0:
            Color.pl("{R}failed{W}")
            raise Exception("iwconfig does not see any interfaces in Mode:Monitor")

        # Assert that the interface enabled by airmon-ng is in monitor mode
        if mon_iface not in mon_ifaces:
            Color.pl("{R}failed{W}")
            raise Exception("iwconfig does not see %s in Mode:Monitor" % mon_iface)

        # No errors found; the device 'mon_iface' was put into MM.
        Color.pl("{G}enabled {C}%s{W}" % mon_iface)
        return mon_iface


    @staticmethod
    def stop(iface):
        # TODO (this)
        pass


    @staticmethod
    def get_interfaces_in_monitor_mode():
        '''
            Uses 'iwconfig' to find all interfaces in monitor mode
            Returns:
                List of interface names that are in monitor mode
        '''
        interfaces = []
        (out, err) = Process.call("iwconfig")
        for line in out.split("\n"):
            if len(line) == 0: continue
            if line[0] != ' ':
                iface = line.split(' ')[0]
                if '\t' in iface:
                    iface = iface.split('\t')[0]
            if 'Mode:Monitor' in line and iface not in interfaces:
                interfaces.append(iface)
        return interfaces


if __name__ == '__main__':
    print "Interfaces in monitor mode:",
    print ','.join(Airmon.get_interfaces_in_monitor_mode())
    print ''

    a = Airmon()
    a.print_menu()
    count = len(a.interfaces)
    question = Color.s("Select interface ({G}1-%d{W}): " % (count))
    choice = raw_input(question)
    Color.pl("You chose: {G}%s{W}" % a.get(choice).name)
    
    #a.start(a.interfaces[0])

