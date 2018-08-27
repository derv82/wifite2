#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from .ifconfig import Ifconfig
from .iwconfig import Iwconfig
from ..util.process import Process
from ..util.color import Color
from ..util.input import raw_input
from ..config import Configuration

import re
import os
import signal

class AirmonIface(object):
    def __init__(self, phy, interface, driver, chipset):
        self.phy = phy
        self.interface = interface
        self.driver = driver
        self.chipset = chipset

    # Max length of fields.
    # Used for printing a table of interfaces.
    INTERFACE_LEN = 12
    PHY_LEN = 6
    DRIVER_LEN = 20
    CHIPSET_LEN = 30

    def __str__(self):
        ''' Colored string representation of interface '''
        s = ''
        s += Color.s('{G}%s' % self.interface.ljust(self.INTERFACE_LEN))
        s += Color.s('{W}%s' % self.phy.ljust(self.PHY_LEN))
        s += Color.s('{C}%s' % self.driver.ljust(self.DRIVER_LEN))
        s += Color.s('{W}%s' % self.chipset.ljust(self.CHIPSET_LEN))
        return s

    @staticmethod
    def menu_header():
        ''' Colored header row for interfaces '''
        s = '    '  # Space for index #
        s += 'Interface'.ljust(AirmonIface.INTERFACE_LEN)
        s += 'PHY'.ljust(AirmonIface.PHY_LEN)
        s += 'Driver'.ljust(AirmonIface.DRIVER_LEN)
        s += 'Chipset'.ljust(AirmonIface.CHIPSET_LEN)
        s += '\n'
        s += '-' * (AirmonIface.INTERFACE_LEN + AirmonIface.PHY_LEN + AirmonIface.DRIVER_LEN + AirmonIface.CHIPSET_LEN + 3)
        return s


class Airmon(Dependency):
    ''' Wrapper around the 'airmon-ng' program '''
    dependency_required = True
    dependency_name = 'airmon-ng'
    dependency_url = 'https://www.aircrack-ng.org/install.html'

    base_interface = None
    killed_network_manager = False

    # Drivers that need to be manually put into monitor mode
    BAD_DRIVERS = ['rtl8821au']
    #see if_arp.h
    ARPHRD_ETHER = 1 #managed
    ARPHRD_IEEE80211_RADIOTAP = 803 #monitor

    def __init__(self):
        self.refresh()

    def refresh(self):
        ''' Get airmon-recognized interfaces '''
        self.interfaces = Airmon.get_interfaces()

    def print_menu(self):
        ''' Prints menu '''
        print(AirmonIface.menu_header())
        for idx, iface in enumerate(self.interfaces, start=1):
            Color.pl(' {G}%d{W}. %s' % (idx, iface))

    def get(self, index):
        ''' Gets interface at index (starts at 1) '''
        if type(index) is str:
            index = int(index)
        return self.interfaces[index - 1]


    @staticmethod
    def get_interfaces():
        '''Returns List of AirmonIface objects known by airmon-ng'''
        interfaces = []
        p = Process('airmon-ng')
        for line in p.stdout().split('\n'):
            # [PHY ]IFACE DRIVER CHIPSET
            airmon_re = re.compile(r'^(?:([^\t]*)\t+)?([^\t]*)\t+([^\t]*)\t+([^\t]*)$')
            matches = airmon_re.match(line)
            if not matches:
                continue

            phy, interface, driver, chipset = matches.groups()
            if phy == 'PHY' or phy == 'Interface':
                continue  # Header

            if len(interface.strip()) == 0:
                continue

            interfaces.append(AirmonIface(phy, interface, driver, chipset))

        return interfaces

    @staticmethod
    def start_bad_driver(iface):
        '''
        Manually put interface into monitor mode (no airmon-ng or vif).
        Fix for bad drivers like the rtl8812AU.
        '''
        Ifconfig.down(iface)
        Iwconfig.mode(iface, 'monitor')
        Ifconfig.up(iface)

        # /sys/class/net/wlan0/type
        iface_type_path = os.path.join('/sys/class/net', iface, 'type')
        if os.path.exists(iface_type_path):
            with open(iface_type_path, 'r') as f:
                if (int(f.read()) == Airmon.ARPHRD_IEEE80211_RADIOTAP):
                    return iface

        return None

    @staticmethod
    def stop_bad_driver(iface):
        '''
        Manually put interface into managed mode (no airmon-ng or vif).
        Fix for bad drivers like the rtl8812AU.
        '''
        Ifconfig.down(iface)
        Iwconfig.mode(iface, 'managed')
        Ifconfig.up(iface)

        # /sys/class/net/wlan0/type
        iface_type_path = os.path.join('/sys/class/net', iface, 'type')
        if os.path.exists(iface_type_path):
            with open(iface_type_path, 'r') as f:
                if (int(f.read()) == Airmon.ARPHRD_ETHER):
                    return iface

        return None

    @staticmethod
    def start(iface):
        '''
            Starts an interface (iface) in monitor mode
            Args:
                iface - The interface to start in monitor mode
                        Either an instance of AirmonIface object,
                        or the name of the interface (string).
            Returns:
                Name of the interface put into monitor mode.
            Throws:
                Exception - If an interface can't be put into monitor mode
        '''
        # Get interface name from input
        if type(iface) == AirmonIface:
            iface_name = iface.interface
            driver = iface.driver
        else:
            iface_name = iface
            driver = None

        # Remember this as the 'base' interface.
        Airmon.base_interface = iface_name

        Color.p('{+} enabling {G}monitor mode{W} on {C}%s{W}... ' % iface_name)

        airmon_output = Process(['airmon-ng', 'start', iface_name]).stdout()

        enabled_iface = Airmon._parse_airmon_start(airmon_output)

        if enabled_iface is None and driver in Airmon.BAD_DRIVERS:
            Color.p('{O}"bad driver" detected{W} ')
            enabled_iface = Airmon.start_bad_driver(iface_name)

        if enabled_iface is None:
            Color.pl('{R}failed{W}')

        monitor_interfaces = Iwconfig.get_interfaces(mode='Monitor')

        # Assert that there is an interface in monitor mode
        if len(monitor_interfaces) == 0:
            Color.pl('{R}failed{W}')
            raise Exception('Cannot find any interfaces in Mode:Monitor')

        # Assert that the interface enabled by airmon-ng is in monitor mode
        if enabled_iface not in monitor_interfaces:
            Color.pl('{R}failed{W}')
            raise Exception('Cannot find %s with Mode:Monitor' % enabled_iface)

        # No errors found; the device 'enabled_iface' was put into Mode:Monitor.
        Color.pl('{G}enabled {C}%s{W}' % enabled_iface)

        return enabled_iface

    @staticmethod
    def _parse_airmon_start(airmon_output):
        '''Find the interface put into monitor mode (if any)'''

        # airmon-ng output: (mac80211 monitor mode vif enabled for [phy10]wlan0 on [phy10]wlan0mon)
        enabled_re = re.compile(r'.*\(mac80211 monitor mode (?:vif )?enabled (?:for [^ ]+ )?on (?:\[\w+\])?(\w+)\)?.*')

        for line in airmon_output.split('\n'):
            matches = enabled_re.match(line)
            if matches:
                return matches.group(1)

        return None


    @staticmethod
    def stop(iface):
        Color.p('{!} {R}disabling {O}monitor mode{O} on {R}%s{O}... ' % iface)

        airmon_output = Process(['airmon-ng', 'stop', iface]).stdout()

        (disabled_iface, enabled_iface) = Airmon._parse_airmon_stop(airmon_output)

        if not disabled_iface and iface in Airmon.BAD_DRIVERS:
            Color.p('{O}"bad driver" detected{W} ')
            disabled_iface = Airmon.stop_bad_driver(iface)

        if disabled_iface:
            Color.pl('{G}disabled %s{W}' % disabled_iface)
        else:
            Color.pl('{O}could not disable on {R}%s{W}' % iface)

        return (disabled_iface, enabled_iface)


    @staticmethod
    def _parse_airmon_stop(airmon_output):
        '''Find the interface taken out of into monitor mode (if any)'''

        # airmon-ng 1.2rc2 output: (mac80211 monitor mode vif enabled for [phy10]wlan0 on [phy10]wlan0mon)
        disabled_re = re.compile(r'\s*\(mac80211 monitor mode (?:vif )?disabled for (?:\[\w+\])?(\w+)\)\s*')

        # airmon-ng 1.2rc1 output: wlan0mon (removed)
        removed_re = re.compile(r'([a-zA-Z0-9]+).*\(removed\)')

        # Enabled interface: (mac80211 station mode vif enabled on [phy4]wlan0)
        enabled_re = re.compile(r'\s*\(mac80211 station mode (?:vif )?enabled on (?:\[\w+\])?(\w+)\)\s*')

        disabled_iface = None
        enabled_iface = None
        for line in airmon_output.split('\n'):
            matches = disabled_re.match(line)
            if matches:
                disabled_iface = matches.group(1)

            matches = removed_re.match(line)
            if matches:
                disabled_iface = matches.group(1)

            matches = enabled_re.match(line)
            if matches:
                enabled_iface = matches.group(1)

        return (disabled_iface, enabled_iface)


    @staticmethod
    def ask():
        '''
        Asks user to define which wireless interface to use.
        Does not ask if:
            1. There is already an interface in monitor mode, or
            2. There is only one wireless interface (automatically selected).
        Puts selected device into Monitor Mode.
        '''

        Airmon.terminate_conflicting_processes()

        Color.p('\n{+} Looking for {C}wireless interfaces{W}...')
        monitor_interfaces = Iwconfig.get_interfaces(mode='Monitor')
        if len(monitor_interfaces) == 1:
            # Assume we're using the device already in montior mode
            iface = monitor_interfaces[0]
            Color.clear_entire_line()
            Color.pl('{+} Using {G}%s{W} already in monitor mode' % iface);
            Airmon.base_interface = None
            return iface

        Color.clear_entire_line()
        Color.p('{+} Checking {C}airmon-ng{W}...')
        a = Airmon()
        count = len(a.interfaces)
        if count == 0:
            # No interfaces found
            Color.pl('\n{!} {O}airmon-ng did not find {R}any{O} wireless interfaces')
            Color.pl('{!} {O}Make sure your wireless device is connected')
            Color.pl('{!} {O}See {C}http://www.aircrack-ng.org/doku.php?id=airmon-ng{O} for more info{W}')
            raise Exception('airmon-ng did not find any wireless interfaces')

        Color.clear_entire_line()
        a.print_menu()

        Color.pl('')

        if count == 1:
            # Only one interface, assume this is the one to use
            choice = 1
        else:
            # Multiple interfaces found
            question = Color.s('{+} Select wireless interface ({G}1-%d{W}): ' % (count))
            choice = raw_input(question)

        iface = a.get(choice)

        if a.get(choice).interface in monitor_interfaces:
            Color.pl('{+} {G}%s{W} is already in monitor mode' % iface.interface)
        else:
            iface.interface = Airmon.start(iface)
        return iface.interface


    @staticmethod
    def terminate_conflicting_processes():
        ''' Deletes conflicting processes reported by airmon-ng '''

        airmon_output = Process(['airmon-ng', 'check']).stdout()

        # Conflicting process IDs and names
        pid_pnames = []

        # 2272    dhclient
        # 2293    NetworkManager
        pid_pname_re = re.compile(r'^\s*(\d+)\s*([a-zA-Z0-9_\-]+)\s*$')
        for line in airmon_output.split('\n'):
            match = pid_pname_re.match(line)
            if match:
                pid = match.group(1)
                pname = match.group(2)
                pid_pnames.append( (pid, pname) )

        if len(pid_pnames) == 0:
            return

        if not Configuration.kill_conflicting_processes:
            # Don't kill processes, warn user
            names_and_pids = ', '.join([
                '{R}%s{O} (PID {R}%s{O})' % (pname, pid)
                for pid, pname in pid_pnames
            ])
            Color.pl('{!} {O}Conflicting processes: %s' % names_and_pids)
            Color.pl('{!} {O}If you have problems: {R}kill -9 PID{O} or re-run wifite with {R}--kill{O}){W}')
            return

        Color.pl('{!} {O}Killing {R}%d {O}conflicting processes' % len(pid_pnames))
        for pid, pname in pid_pnames:
            if pname == 'NetworkManager' and Process.exists('service'):
                Color.pl('{!} {O}stopping network-manager ({R}service network-manager stop{O})')
                # Can't just pkill network manager; it's a service
                Process(['service', 'network-manager', 'stop']).wait()
                Airmon.killed_network_manager = True
            elif pname == 'avahi-daemon' and Process.exists('service'):
                Color.pl('{!} {O}stopping avahi-daemon ({R}service avahi-daemon stop{O})')
                # Can't just pkill avahi-daemon; it's a service
                Process(['service', 'avahi-daemon', 'stop']).wait()
            else:
                Color.pl('{!} {R}Terminating {O}conflicting process {R}%s{O} (PID {R}%s{O})' % (pname, pid))
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except:
                    pass


    @staticmethod
    def put_interface_up(iface):
        Color.p('{!} {O}putting interface {R}%s up{O}...' % (iface))
        Ifconfig.up(iface)
        Color.pl(' {G}done{W}')

    @staticmethod
    def start_network_manager():
        Color.p('{!} {O}restarting {R}NetworkManager{O}...')

        if Process.exists('service'):
            cmd = 'service network-manager start'
            proc = Process(cmd)
            (out, err) = proc.get_output()
            if proc.poll() != 0:
                Color.pl(' {R}Error executing {O}%s{W}' % cmd)
                if out is not None and out.strip() != '':
                    Color.pl('{!} {O}STDOUT> %s{W}' % out)
                if err is not None and err.strip() != '':
                    Color.pl('{!} {O}STDERR> %s{W}' % err)
            else:
                Color.pl(' {G}done{W} ({C}%s{W})' % cmd)
                return

        if Process.exists('systemctl'):
            cmd = 'systemctl start NetworkManager'
            proc = Process(cmd)
            (out, err) = proc.get_output()
            if proc.poll() != 0:
                Color.pl(' {R}Error executing {O}%s{W}' % cmd)
                if out is not None and out.strip() != '':
                    Color.pl('{!} {O}STDOUT> %s{W}' % out)
                if err is not None and err.strip() != '':
                    Color.pl('{!} {O}STDERR> %s{W}' % err)
            else:
                Color.pl(' {G}done{W} ({C}%s{W})' % cmd)
                return
        else:
            Color.pl(' {R}cannot restart NetworkManager: {O}systemctl{R} or {O}service{R} not found{W}')

if __name__ == '__main__':
    stdout = '''
Found 2 processes that could cause trouble.
If airodump-ng, aireplay-ng or airtun-ng stops working after
a short period of time, you may want to run 'airmon-ng check kill'

  PID Name
 5563 avahi-daemon
 5564 avahi-daemon

PHY	Interface	Driver		Chipset

phy0	wlx00c0ca4ecae0	rtl8187		Realtek Semiconductor Corp. RTL8187
Interface 15mon is too long for linux so it will be renamed to the old style (wlan#) name.

		(mac80211 monitor mode vif enabled on [phy0]wlan0mon
		(mac80211 station mode vif disabled for [phy0]wlx00c0ca4ecae0)
    '''
    start_iface = Airmon._parse_airmon_start(stdout)
    print('start_iface from stdout:', start_iface)

    Configuration.initialize(False)
    iface = Airmon.ask()
    (disabled_iface, enabled_iface) = Airmon.stop(iface)
    print('Disabled:', disabled_iface)
    print('Enabled:', enabled_iface)
