#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from .tshark import Tshark
from .wash import Wash
from ..util.process import Process
from ..config import Configuration
from ..model.target import Target, WPSState
from ..model.client import Client

import os, time, threading

class AirodumpOptimized(Dependency):
    ''' Optimized airodump-ng wrapper '''
    dependency_required = True
    dependency_name = 'airodump-ng'
    dependency_url = 'https://www.aircrack-ng.org/install.html'

    def __init__(self, interface=None, channel=None, encryption=None,\
                       wps=WPSState.UNKNOWN, target_bssid=None,\
                       output_file_prefix='airodump',\
                       ivs_only=False, skip_wps=False, delete_existing_files=True,\
                       aggressive=False):
        '''Optimized airodump setup'''

        Configuration.initialize()

        if interface is None:
            interface = Configuration.interface
        if interface is None:
            raise Exception('Wireless interface must be defined (-i)')
        
        self.interface = interface
        self.targets = []
        self.channel = channel or Configuration.target_channel
        self.five_ghz = Configuration.five_ghz
        self.encryption = encryption
        self.wps = wps
        self.target_bssid = target_bssid
        self.output_file_prefix = output_file_prefix
        self.ivs_only = ivs_only
        self.skip_wps = skip_wps
        self.delete_existing_files = delete_existing_files
        self.aggressive = aggressive
        
        # Performance tracking
        self.decloaking = False
        self.decloaked_bssids = set()
        self.decloaked_times = {}
        self.last_targets_update = 0
        self.target_cache = {}

    def __enter__(self):
        if self.delete_existing_files:
            self.delete_airodump_temp_files(self.output_file_prefix)

        self.csv_file_prefix = Configuration.temp() + self.output_file_prefix

        # Optimized command
        command = [
            'airodump-ng',
            self.interface,
            '-a',  # Only associated clients
            '-w', self.csv_file_prefix,
            '--write-interval', '1'  # Fast updates
        ]

        if self.channel:
            command.extend(['-c', str(self.channel)])
        elif self.five_ghz:
            command.extend(['--band', 'a'])

        if self.encryption:
            command.extend(['--enc', self.encryption])
        if self.wps:
            command.extend(['--wps'])
        if self.target_bssid:
            command.extend(['--bssid', self.target_bssid])

        if self.aggressive:
            command.extend(['-x', '500'])  # Update interval for aggressive mode

        if self.ivs_only:
            command.extend(['--output-format', 'ivs,csv'])
        else:
            command.extend(['--output-format', 'pcap,csv'])

        self.pid = Process(command, devnull=True)
        return self

    def __exit__(self, type, value, traceback):
        self.pid.interrupt()
        if self.delete_existing_files:
            self.delete_airodump_temp_files(self.output_file_prefix)

    def find_files(self, endswith=None):
        return self.find_files_by_output_prefix(self.output_file_prefix, endswith=endswith)

    @classmethod
    def find_files_by_output_prefix(cls, output_file_prefix, endswith=None):
        result = []
        temp = Configuration.temp()
        if not os.path.exists(temp):
            return result
        
        for fil in os.listdir(temp):
            if not fil.startswith(output_file_prefix):
                continue
            if endswith is None or fil.endswith(endswith):
                result.append(os.path.join(temp, fil))
        return result

    @classmethod
    def delete_airodump_temp_files(cls, output_file_prefix):
        """Delete temporary files efficiently"""
        temp_dir = Configuration.temp()
        
        try:
            for fil in cls.find_files_by_output_prefix(output_file_prefix):
                try:
                    os.remove(fil)
                except:
                    pass

            for pattern in ['replay_*.cap', '*.xor', 'replay_*.xor']:
                import glob
                for fil in glob.glob(os.path.join(temp_dir, pattern)):
                    try:
                        os.remove(fil)
                    except:
                        pass
        except:
            pass

    def get_targets(self, old_targets=[], apply_filter=True):
        """Optimized target parsing with caching"""
        
        # Limit update frequency
        now = time.time()
        if now - self.last_targets_update < 0.5:
            return self.targets

        csv_filename = None
        for fil in self.find_files(endswith='.csv'):
            csv_filename = fil
            break

        if csv_filename is None or not os.path.exists(csv_filename):
            return self.targets

        targets = AirodumpOptimized.get_targets_from_csv(csv_filename)

        # Update WPS info
        if not self.skip_wps:
            capfile = csv_filename[:-3] + 'cap'
            if os.path.exists(capfile):
                try:
                    Tshark.check_for_wps_and_update_targets(capfile, targets)
                except:
                    try:
                        Wash.check_for_wps_and_update_targets(capfile, targets)
                    except:
                        pass

        if apply_filter:
            targets = AirodumpOptimized.filter_targets(targets, skip_wps=self.skip_wps)

        targets.sort(key=lambda x: x.power, reverse=True)

        # Deauth hidden networks
        for old_target in self.targets:
            for new_target in targets:
                if old_target.bssid != new_target.bssid:
                    continue
                if new_target.essid_known and not old_target.essid_known:
                    new_target.decloaked = True
                    self.decloaked_bssids.add(new_target.bssid)

        self.targets = targets
        self.last_targets_update = now
        self.deauth_hidden_targets()

        return self.targets

    @staticmethod
    def get_targets_from_csv(csv_filename):
        """Optimized CSV parsing"""
        targets = []
        import csv

        try:
            with open(csv_filename, 'r') as csvopen:
                lines = []
                for line in csvopen:
                    line = line.replace('\0', '')
                    lines.append(line)

                csv_reader = csv.reader(lines,
                        delimiter=',',
                        quoting=csv.QUOTE_ALL,
                        skipinitialspace=True,
                        escapechar='\\')

                hit_clients = False
                for row in csv_reader:
                    if len(row) == 0:
                        continue

                    if row[0].strip() == 'BSSID':
                        hit_clients = False
                        continue
                    elif row[0].strip() == 'Station MAC':
                        hit_clients = True
                        continue

                    if hit_clients:
                        try:
                            client = Client(row)
                            if 'not associated' not in client.bssid:
                                for t in targets:
                                    if t.bssid == client.bssid:
                                        t.clients.append(client)
                                        break
                        except:
                            pass
                    else:
                        try:
                            target = Target(row)
                            targets.append(target)
                        except:
                            pass
        except:
            pass

        return targets

    @staticmethod
    def filter_targets(targets, skip_wps=False):
        """Filter targets based on configuration"""
        result = []
        for target in targets:
            if Configuration.clients_only and len(target.clients) == 0:
                continue
            
            if 'WEP' in Configuration.encryption_filter and 'WEP' in target.encryption:
                result.append(target)
            elif 'WPA' in Configuration.encryption_filter and 'WPA' in target.encryption:
                result.append(target)
            elif 'WPS' in Configuration.encryption_filter and target.wps in [WPSState.UNLOCKED, WPSState.LOCKED]:
                result.append(target)
            elif skip_wps:
                result.append(target)

        # Apply BSSID/ESSID filters
        i = 0
        while i < len(result):
            target = result[i]
            
            if Configuration.ignore_essid and target.essid and \
               Configuration.ignore_essid.lower() in target.essid.lower():
                result.pop(i)
            elif Configuration.target_bssid and target.bssid.lower() != Configuration.target_bssid.lower():
                result.pop(i)
            elif Configuration.target_essid and target.essid and \
                 target.essid.lower() != Configuration.target_essid.lower():
                result.pop(i)
            else:
                i += 1

        return result

    def deauth_hidden_targets(self):
        """Deauth hidden networks to reveal ESSID"""
        self.decloaking = False

        if Configuration.no_deauth or self.channel is None:
            return

        deauth_cmd = [
            'aireplay-ng',
            '-0',
            str(Configuration.num_deauths),
            '--ignore-negative-one'
        ]

        for target in self.targets:
            if target.essid_known:
                continue

            now = int(time.time())
            secs_since = now - self.decloaked_times.get(target.bssid, 0)

            if secs_since < 30:
                continue

            self.decloaking = True
            self.decloaked_times[target.bssid] = now

            from ..util.color import Color
            if Configuration.verbose > 1:
                Color.pe('{C}[+] Deauth {C}%s{W} ({C}%d{W} clients)' % (
                    target.bssid, len(target.clients)))

            iface = Configuration.interface
            Process(deauth_cmd + ['-a', target.bssid, iface])

            for client in target.clients:
                Process(deauth_cmd + ['-a', target.bssid, '-c', client.bssid, iface])

# Use optimized version
Airodump = AirodumpOptimized
