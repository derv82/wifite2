#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Interface import Interface
from Process import Process
from Color import Color
from Configuration import Configuration

import re
import os
import signal

class Airmon(object):
    ''' Wrapper around the 'airmon-ng' program '''
    base_interface = None

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
        Airmon.base_interface = iface

        # Call airmon-ng
        Color.p("{+} enabling {G}monitor mode{W} on {C}%s{W}... " % iface)
        (out,err) = Process.call('airmon-ng start %s' % iface)

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

        Configuration.interface = mon_iface

        return mon_iface


    @staticmethod
    def stop(iface):
        Color.p("{!} {R}disabling {O}monitor mode{O} on {R}%s{O}... " % iface)
        (out,err) = Process.call('airmon-ng stop %s' % iface)
        mon_iface = None
        for line in out.split('\n'):
            # aircrack-ng 1.2 rc2
            if 'monitor mode' in line and 'disabled' in line and ' for ' in line:
                mon_iface = line.split(' for ')[1]
                if ']' in mon_iface:
                    mon_iface = mon_iface.split(']')[1]
                if ')' in mon_iface:
                    mon_iface = mon_iface.split(')')[0]
                break

            # aircrack-ng 1.2 rc1
            match = re.search('([a-zA-Z0-9]+).*\(removed\)', line)
            if match:
                mon_iface = match.groups()[0]
                break

        if mon_iface:
            Color.pl('{R}disabled %s{W}' % mon_iface)
        else:
            Color.pl('{O}could not disable on {R}%s{W}' % iface)


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


    @staticmethod
    def ask():
        '''
            Asks user to define which wireless interface to use.
            Does not ask if:
                1. There is already an interface in monitor mode, or
                2. There is only one wireles interface (automatically selected).
            Puts selected device into Monitor Mode.
        '''

        Airmon.terminate_conflicting_processes()

        Color.pl('\n{+} looking for {C}wireless interfaces{W}')
        mon_ifaces = Airmon.get_interfaces_in_monitor_mode()
        mon_count = len(mon_ifaces)
        if mon_count == 1:
            # Assume we're using the device already in montior mode
            iface = mon_ifaces[0]
            Color.pl('{+} using interface {G}%s{W} which is already in monitor mode'
                % iface);
            Airmon.base_interface = None
            return iface

        a = Airmon()
        count = len(a.interfaces)
        if count == 0:
            # No interfaces found
            Color.pl('\n{!} {O}airmon-ng did not find {R}any{O} wireless interfaces')
            Color.pl('{!} {O}make sure your wireless device is connected')
            Color.pl('{!} {O}see {C}http://www.aircrack-ng.org/doku.php?id=airmon-ng{O} for more info{W}')
            raise Exception('airmon-ng did not find any wireless interfaces')

        Color.pl('')

        a.print_menu()

        Color.pl('')

        if count == 1:
            # Only one interface, assume this is the one to use
            choice = 1
        else:
            # Multiple interfaces found
            question = Color.s("{+} select interface ({G}1-%d{W}): " % (count))
            choice = raw_input(question)

        iface = a.get(choice)

        if a.get(choice).name in mon_ifaces:
            Color.pl('{+} {G}%s{W} is already in monitor mode' % iface.name)
        else:
            iface.name = Airmon.start(iface)
        return iface.name


    @staticmethod
    def terminate_conflicting_processes():
        ''' Deletes conflicting processes reported by airmon-ng '''

        '''
        % airmon-ng check

        Found 3 processes that could cause trouble.
        If airodump-ng, aireplay-ng or airtun-ng stops working after
        a short period of time, you may want to kill (some of) them!
        -e
        PID Name
        2272    dhclient
        2293    NetworkManager
        3302    wpa_supplicant
        '''

        out = Process(['airmon-ng', 'check']).stdout()
        if 'processes that could cause trouble' not in out:
            # No proceses to kill
            return

        hit_pids = False
        for line in out.split('\n'):
            if re.search('^ *PID', line):
                hit_pids = True
                continue
            if not hit_pids: continue
            if line.strip() == '': continue
            match = re.search('^[ \t]*(\d+)[ \t]*([a-zA-Z0-9_\-]+)[ \t]*$', line)
            if match:
                # Found process to kill
                pid = match.groups()[0]
                pname = match.groups()[1]
                Color.pl('{!} {R}terminating {O}conflicting process' +
                         ' {R}%s{O} (PID {R}%s{O})' % (pname, pid))
                os.kill(int(pid), signal.SIGTERM)

    @staticmethod
    def put_interface_up(iface):
        Color.p("{!} {O}putting interface {R}%s up{O}..." % (iface))
        (out,err) = Process.call('ifconfig %s up' % (iface))
        Color.pl(" {R}done{W}")

    @staticmethod
    def start_network_manager():
        Color.p("{!} {O}restarting {R}NetworkManager{O}...")
        (out,err) = Process.call('systemctl start NetworkManager')
        Color.pl(" {R}restarted{W}")

if __name__ == '__main__':
    Airmon.terminate_conflicting_processes()
    iface = Airmon.ask()
    Airmon.stop(iface)
