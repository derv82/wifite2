#!/usr/bin/env python
# -*- coding: utf-8 -*-

import contextlib
import os
import re
import signal
from .dependency import Dependency
from .ip import Ip
from .iw import Iw
from ..config import Configuration
from ..util.color import Color
from ..util.process import Process


class AirmonIface:
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
        """ Colored string representation of interface """
        s = ''
        s += Color.s(f'{{G}}{self.interface.ljust(self.INTERFACE_LEN)}')
        s += Color.s(f'{{W}}{self.phy.ljust(self.PHY_LEN)}')
        s += Color.s(f'{{C}}{self.driver.ljust(self.DRIVER_LEN)}')
        s += Color.s(f'{{W}}{self.chipset.ljust(self.CHIPSET_LEN)}')
        return s

    @staticmethod
    def menu_header():
        """ Colored header row for interfaces """
        s = '    ' + 'Interface'.ljust(AirmonIface.INTERFACE_LEN)
        s += 'PHY'.ljust(AirmonIface.PHY_LEN)
        s += 'Driver'.ljust(AirmonIface.DRIVER_LEN)
        s += 'Chipset'.ljust(AirmonIface.CHIPSET_LEN)
        s += '\n'
        s += '-' * \
             (AirmonIface.INTERFACE_LEN + AirmonIface.PHY_LEN +
              AirmonIface.DRIVER_LEN + AirmonIface.CHIPSET_LEN + 3)
        return s


class Airmon(Dependency):
    """ Wrapper around the 'airmon-ng' program """
    dependency_required = True
    dependency_name = 'airmon-ng'
    dependency_url = 'https://www.aircrack-ng.org/install.html'
    chipset_table: str = 'https://wikidevi.com/wiki/Wireless_adapters/Chipset_table'
    base_interface = None
    killed_network_manager = False
    use_ipiw = False
    isdeprecated = False

    # Drivers that need to be manually put into monitor mode
    BAD_DRIVERS = ['rtl8821au']
    DEPRECATED_DRIVERS = ['rtl8723cs']
    # see if_arp.h
    ARPHRD_ETHER = 1  # managed
    ARPHRD_IEEE80211_RADIOTAP = 803  # monitor

    def __init__(self):
        self.interfaces = None
        self.refresh()

    def refresh(self):
        """ Get airmon-recognized interfaces """
        self.interfaces = Airmon.get_interfaces()

    def print_menu(self):
        """ Prints menu """
        print((AirmonIface.menu_header()))
        for idx, interface in enumerate(self.interfaces, start=1):
            Color.pl(f' {{G}}{idx:d}{{W}}. {interface}')

    def get(self, index):
        """ Gets interface at index (starts at 1) """
        if isinstance(self, type(self)):
            index = int(index)
        return self.interfaces[index - 1]

    @staticmethod
    def get_interfaces():
        """Returns List of AirmonIface objects known by airmon-ng"""
        interfaces = []
        p = Process('airmon-ng')
        for line in p.stdout().split('\n'):
            # [PHY ]IFACE DRIVER CHIPSET
            airmon_re = re.compile(r'^(?:([^\t]*)\t+)?([^\t]*)\t+([^\t]*)\t+([^\t]*)$')
            matches = airmon_re.match(line)
            if not matches:
                continue

            phy, interface, driver, chipset = matches.groups()
            if phy in ['PHY', 'Interface']:
                continue  # Header

            if len(interface.strip()) == 0:
                continue

            interfaces.append(AirmonIface(phy, interface, driver, chipset))

        return interfaces

    @staticmethod
    def get_iface_info(interface_name):
        """
        Get interface info (driver, chipset), based on interface name.
        Returns an AirmonIface if interface name is found by airmon-ng or None
        """
        return next((iface for iface in Airmon.get_interfaces()
                     if iface.interface == interface_name), None)

    @staticmethod
    def start_bad_driver(interface, isdeprecated=False):
        """
        Manually put interface into monitor mode (no airmon-ng or vif).
        Fix for bad drivers like the rtl8812AU.
        """
        Ip.down(interface)
        if isdeprecated:
            Process(['iwconfig', interface, 'mode', 'monitor']).stdout()
        else:
            Iw.mode(interface, 'monitor')
        Ip.up(interface)

        # /sys/class/net/wlan0/type
        iface_type_path = os.path.join('/sys/class/net', interface, 'type')
        if os.path.exists(iface_type_path):
            with open(iface_type_path, 'r') as f:
                if int(f.read()) == Airmon.ARPHRD_IEEE80211_RADIOTAP:
                    return iface if int(f.read()) == Airmon.ARPHRD_ETHER else None

    @staticmethod
    def stop_bad_driver(interface):
        """
        Manually put interface into managed mode (no airmon-ng or vif).
        Fix for bad drivers like the rtl8812AU.
        """
        Ip.down(interface)
        Iw.mode(interface, 'managed')
        Ip.up(interface)

        # /sys/class/net/wlan0/type
        iface_type_path = os.path.join('/sys/class/net', interface, 'type')
        if not os.path.exists(iface_type_path):
            return None
        with open(iface_type_path, 'r') as f:
            return iface if int(f.read()) == Airmon.ARPHRD_ETHER else None

    @classmethod
    def start(cls, interface):
        """
            Starts an interface (iface) in monitor mode
            Args:
                iface - The interface to start in monitor mode
                        Either an instance of AirmonIface object,
                        or the name of the interface (string).
            Returns:
                Name of the interface put into monitor mode.
            Throws:
                Exception - If an interface can't be put into monitor mode
        """
        # Get interface name from input
        if isinstance(interface, AirmonIface):
            iface_name = interface.interface
            driver = interface.driver
        else:
            iface_name = interface
            driver = None

        # Remember this as the 'base' interface.
        Airmon.base_interface = iface_name

        # If driver is deprecated then skip airmon-ng
        if driver not in Airmon.DEPRECATED_DRIVERS:
            # Try to enable using Airmon-ng first (for better compatibility)
            Color.p(f'{{+}} Enabling {{G}}monitor mode{{W}} on {{C}}{iface_name}{{W}}... ')
            airmon_output = Process(['airmon-ng', 'start', iface_name]).stdout()
            enabled_interface = Airmon._parse_airmon_start(airmon_output)
        else:
            enabled_interface = None

        # if it fails, try to use ip/iw
        if enabled_interface is None:
            Airmon.isdeprecated = driver in Airmon.DEPRECATED_DRIVERS
            enabled_interface = Airmon.start_bad_driver(iface_name, Airmon.isdeprecated)
        else:
            # If not, just set for us know how it went in monitor mode
            cls.use_ipiw = True

        if not Airmon.isdeprecated:
            # if that also fails, just give up
            if enabled_interface is None:
                Color.pl('{R}failed{W}')

            # Assert that there is an interface in monitor mode
            interfaces = Iw.get_interfaces(mode='monitor')
            if len(interfaces) == 0:
                Color.pl('{R}failed{W}')
                raise Exception('Cannot find any interfaces in monitor mode')

            # Assert that the interface enabled by airmon-ng is in monitor mode
            if enabled_interface not in interfaces:
                Color.pl('{R}failed{W}')
                raise Exception(f'Cannot find {enabled_interface} with type:monitor')

        # No errors found; the device 'enabled_iface' was put into Mode:Monitor.
        Color.pl('{G}enabled{W}!')

        return enabled_interface

    @staticmethod
    def _parse_airmon_start(airmon_output):
        """Find the interface put into monitor mode (if any)"""
        # airmon-ng output: (mac80211 monitor mode vif enabled for [phy10]wlan0 on [phy10]wlan0mon)
        enabled_re = re.compile(
            r'.*\(mac80211 monitor mode (?:vif )?enabled (?:for [^ ]+ )?on (?:\[\w+])?(\w+)\)?.*')
        lines = airmon_output.split('\n')

        for index, line in enumerate(lines):
            if matches := enabled_re.match(line):
                return matches[1]
            if "monitor mode enabled" in line:
                return re.sub(r'\s+', ' ', lines[index - 1]).split(' ')[1]

        return None

    @classmethod
    def stop(cls, interface):
        Color.p(f'{{!}}{{W}} Disabling {{O}}monitor{{W}} mode on {{R}}{interface}{{W}}...\n')

        if cls.use_ipiw:
            enabled_interface = disabled_interface = Airmon.stop_bad_driver(interface)
        else:
            airmon_output = Process(['airmon-ng', 'stop', interface]).stdout()
            (disabled_interface, enabled_interface) = Airmon._parse_airmon_stop(airmon_output)

        if disabled_interface:
            Color.pl(f'{{+}}{{W}} Disabled monitor mode on {{G}}{disabled_interface}{{W}}')
        else:
            Color.pl(f'{{!}} {{O}}Could not disable {{R}}{interface}{{W}}')

        return disabled_interface, enabled_interface

    @staticmethod
    def _parse_airmon_stop(airmon_output):
        """Find the interface taken out of into monitor mode (if any)"""
        # airmon-ng 1.2: (mac80211 monitor mode vif enabled for [phy10]wlan0 on [phy10]wlan0mon)
        disabled_re = re.compile(
            r'\s*\(mac80211 monitor mode (?:vif )?disabled for (?:\[\w+])?(\w+)\)\s*')

        # airmon-ng 1.2rc1 output: wlan0mon (removed)
        removed_re = re.compile(
            r'([a-zA-Z\d]+).*\(removed\)')

        # Enabled interface: (mac80211 station mode vif enabled on [phy4]wlan0)
        enabled_re = re.compile(
            r'\s*\(mac80211 station mode (?:vif )?enabled on (?:\[\w+])?(\w+)\)\s*')

        disabled_interface = None
        enabled_interface = None
        for line in airmon_output.split('\n'):
            if matches := disabled_re.match(line):
                disabled_interface = matches[1]

            if matches := removed_re.match(line):
                disabled_interface = matches[1]

            if matches := enabled_re.match(line):
                enabled_interface = matches[1]

        return disabled_interface, enabled_interface

    @staticmethod
    def ask():
        """
        Asks user to define which wireless interface to use.
        Does not ask if:
            1. There is already an interface in monitor mode, or
            2. There is only one wireless interface (automatically selected).
        Puts selected device into Monitor Mode.
        """
        Airmon.terminate_conflicting_processes()

        Color.p('\n{+} Looking for {C}wireless interfaces{W}...')
        monitor_interfaces = Iw.get_interfaces(mode='monitor')
        if len(monitor_interfaces) == 1:
            # Assume we're using the device already in monitor mode
            interface = monitor_interfaces[0]
            Color.clear_entire_line()
            Color.pl(f'{{+}} Using {{G}}{interface}{{W}} already in monitor mode')
            Airmon.base_interface = None
            return interface

        Color.clear_entire_line()
        Color.p('{+} Checking {C}airmon-ng{W}...')

        a = Airmon()
        if len(a.interfaces) == 0:
            # No interfaces found
            Color.pl('\n{!} {O}airmon-ng did not find {R}any{O} wireless interfaces')
            Color.pl('{!} {O}Make sure your wireless device is connected')
            Color.pl(
                '{!} {O}See {C}https://www.aircrack-ng.org/doku.php?id=airmon-ng{O} for more info{W}')
            raise Exception('airmon-ng did not find any wireless interfaces')

        Color.clear_entire_line()
        a.print_menu()

        Color.pl('')

        if len(a.interfaces) == 1:
            # Only one interface, assume this is the one to use
            choice = 1
        else:
            # Multiple interfaces found
            Color.p(f'{{+}} Select wireless interface ({{G}}1-{len(a.interfaces):d}{{W}}): ')
            choice = input()

        selected = a.get(choice)

        if a.get(choice).interface in monitor_interfaces:
            Color.pl(f'{{+}} {{G}}{selected.interface}{{W}} is already in monitor mode')
        else:
            selected.interface = Airmon.start(selected)

        return selected.interface

    @staticmethod
    def terminate_conflicting_processes():
        """ Deletes conflicting processes reported by airmon-ng """
        airmon_output = Process(['airmon-ng', 'check']).stdout()

        # Conflicting process IDs and names
        pid_pnames = []

        # 2272    dhclient
        # 2293    NetworkManager
        pid_pname_re = re.compile(r'^\s*(\d+)\s*([a-zA-Z\d_\-]+)\s*$')
        for line in airmon_output.split('\n'):
            if match := pid_pname_re.match(line):
                pid = match[1]
                pname = match[2]
                pid_pnames.append((pid, pname))

        if not pid_pnames:
            return

        if not Configuration.kill_conflicting_processes:
            # Don't kill processes, warn user
            names_and_pids = ', '.join([
                f'{{R}}{pname}{{O}} (PID {{R}}{pid}{{O}})'
                for pid, pname in pid_pnames
            ])
            Color.pl(f'{{!}} {{O}}Conflicting processes: {names_and_pids}')
            Color.pl(
                '{!} {O}If you have problems: {R}kill -9 PID{O} or re-run wifite with {R}--kill{O}{W}')
            return

        Color.pl(f'{{!}} {{O}}Killing {{R}}{len(pid_pnames):d} {{O}}conflicting processes')
        for pid, pname in pid_pnames:
            if pname == 'NetworkManager' and Process.exists('systemctl'):
                Color.pl('{!} {O}stopping NetworkManager ({R}systemctl stop NetworkManager{O})')
                # Can't just pkill NetworkManager; it's a service
                Process(['systemctl', 'stop', 'NetworkManager']).wait()
                Airmon.killed_network_manager = True
            elif pname == 'network-manager' and Process.exists('service'):
                Color.pl('{!} {O}stopping network-manager ({R}service network-manager stop{O})')
                # Can't just pkill network manager; it's a service
                Process(['service', 'network-manager', 'stop']).wait()
                Airmon.killed_network_manager = True
            elif pname == 'avahi-daemon' and Process.exists('service'):
                Color.pl('{!} {O}stopping avahi-daemon ({R}service avahi-daemon stop{O})')
                # Can't just pkill avahi-daemon; it's a service
                Process(['service', 'avahi-daemon', 'stop']).wait()
            else:
                Color.pl(
                    f'{{!}} {{R}}Terminating {{O}}conflicting process {{R}}{pname}{{O}} (PID {{R}}{pid}{{O}})')
                with contextlib.suppress(Exception):
                    os.kill(int(pid), signal.SIGTERM)

    @staticmethod
    def put_interface_up(interface):
        Color.p(f'{{!}}{{W}} Putting interface {{R}}{interface}{{W}} {{G}}up{{W}}...\n')
        Ip.up(interface)
        Color.pl('{+}{W} Done !')

    @staticmethod
    def start_network_manager():
        Color.p('{!} {O}start {R}NetworkManager{O}...')

        if Process.exists('service'):
            cmd = 'service networkmanager start'
            proc = Process(cmd)
            (out, err) = proc.get_output()
            if proc.poll() != 0:
                Color.pl(f' {{R}}Error executing {{O}}{cmd}{{W}}')
                if out is not None and out.strip() != '':
                    Color.pl(f'{{!}} {{O}}STDOUT> {out}{{W}}')
                if err is not None and err.strip() != '':
                    Color.pl(f'{{!}} {{O}}STDERR> {err}{{W}}')
            else:
                Color.pl(f' {{G}}Done{{W}} ({{C}}{cmd}{{W}})')
                return

        if Process.exists('systemctl'):
            cmd = 'systemctl start NetworkManager'
            proc = Process(cmd)
            (out, err) = proc.get_output()
            if proc.poll() != 0:
                Color.pl(f' {{R}}Error executing {{O}}{cmd}{{W}}')
                if out is not None and out.strip() != '':
                    Color.pl(f'{{!}} {{O}}STDOUT> {out}{{W}}')
                if err is not None and err.strip() != '':
                    Color.pl(f'{{!}} {{O}}STDERR> {err}{{W}}')
            else:
                Color.pl(f' {{G}}done{{W}} ({{C}}{cmd}{{W}})')
        else:
            Color.pl(
                ' {R}Cannot start NetworkManager: {O}systemctl{R} or {O}service{R} not found{W}')


if __name__ == '__main__':
    stdout: str = '''
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
    print(('start_iface from stdout:', start_iface))

    Configuration.initialize(False)
    iface = Airmon.ask()
    (disabled_iface, enabled_iface) = Airmon.stop(iface)
    print(('Disabled:', disabled_iface))
    print(('Enabled:', enabled_iface))
