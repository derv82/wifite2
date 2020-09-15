#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
# from ..util.process import Process


class Hostapd(Dependency):
    dependency_required = False
    dependency_name = 'hostapd'
    dependency_url = 'apt install hostapd'

    @classmethod
    def run(slef, iface, target):

        fout = open('/tmp/hostapd.conf', 'w')
        fout.write('interface='+iface+'\n')
        fout.write('ssid='+target.essid+'\n')
        fout.write('channel='+target.channel+'\n')
        fout.write('driver=nl80211\n')
        fout.close()

        # command = [
        #     'hostapd',
        #     '/tmp/hostapd.conf'
        # ]
        # process = Process(command)

        return None

    @classmethod
    def stop(self):
        if hasattr(self, 'pid') and self.pid and self.pid.poll() is None:
            self.pid.interrupt()
        return None
