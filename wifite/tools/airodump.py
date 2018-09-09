#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from .tshark import Tshark
from .wash import Wash
from ..util.process import Process
from ..config import Configuration
from ..model.target import Target, WPSState
from ..model.client import Client

import os, time

class Airodump(Dependency):
    ''' Wrapper around airodump-ng program '''
    dependency_required = True
    dependency_name = 'airodump-ng'
    dependency_url = 'https://www.aircrack-ng.org/install.html'

    def __init__(self, interface=None, channel=None, encryption=None,\
                       wps=WPSState.UNKNOWN, target_bssid=None,
                       output_file_prefix='airodump',\
                       ivs_only=False, skip_wps=False, delete_existing_files=True):
        '''Sets up airodump arguments, doesn't start process yet.'''

        Configuration.initialize()

        if interface is None:
            interface = Configuration.interface
        if interface is None:
            raise Exception('Wireless interface must be defined (-i)')
        self.interface = interface

        self.targets = []

        if channel is None:
            channel = Configuration.target_channel
        self.channel = channel
        self.five_ghz = Configuration.five_ghz

        self.encryption = encryption
        self.wps = wps

        self.target_bssid = target_bssid
        self.output_file_prefix = output_file_prefix
        self.ivs_only = ivs_only
        self.skip_wps = skip_wps

        # For tracking decloaked APs (previously were hidden)
        self.decloaking = False
        self.decloaked_bssids = set()
        self.decloaked_times = {} # Map of BSSID(str) -> epoch(int) of last deauth

        self.delete_existing_files = delete_existing_files


    def __enter__(self):
        '''
        Setting things up for this context.
        Called at start of 'with Airodump(...) as x:'
        Actually starts the airodump process.
        '''
        if self.delete_existing_files:
            self.delete_airodump_temp_files(self.output_file_prefix)

        self.csv_file_prefix = Configuration.temp() + self.output_file_prefix

        # Build the command
        command = [
            'airodump-ng',
            self.interface,
            '-a', # Only show associated clients
            '-w', self.csv_file_prefix, # Output file prefix
            '--write-interval', '1' # Write every second
        ]
        if self.channel:    command.extend(['-c', str(self.channel)])
        elif self.five_ghz: command.extend(['--band', 'a'])

        if self.encryption:   command.extend(['--enc', self.encryption])
        if self.wps:          command.extend(['--wps'])
        if self.target_bssid: command.extend(['--bssid', self.target_bssid])

        if self.ivs_only: command.extend(['--output-format', 'ivs,csv'])
        else:             command.extend(['--output-format', 'pcap,csv'])

        # Start the process
        self.pid = Process(command, devnull=True)
        return self


    def __exit__(self, type, value, traceback):
        '''
        Tearing things down since the context is being exited.
        Called after 'with Airodump(...)' goes out of scope.
        '''
        # Kill the process
        self.pid.interrupt()

        if self.delete_existing_files:
            self.delete_airodump_temp_files(self.output_file_prefix)


    def find_files(self, endswith=None):
        return self.find_files_by_output_prefix(self.output_file_prefix, endswith=endswith)

    @classmethod
    def find_files_by_output_prefix(cls, output_file_prefix, endswith=None):
        ''' Finds all files in the temp directory that start with the output_file_prefix '''
        result = []
        temp = Configuration.temp()
        for fil in os.listdir(temp):
            if not fil.startswith(output_file_prefix):
                continue

            if endswith is None or fil.endswith(endswith):
                result.append(os.path.join(temp, fil))

        return result

    @classmethod
    def delete_airodump_temp_files(cls, output_file_prefix):
        '''
        Deletes airodump* files in the temp directory.
        Also deletes replay_*.cap and *.xor files in pwd.
        '''
        # Remove all temp files
        for fil in cls.find_files_by_output_prefix(output_file_prefix):
            os.remove(fil)

        # Remove .cap and .xor files from pwd
        for fil in os.listdir('.'):
            if fil.startswith('replay_') and fil.endswith('.cap') or fil.endswith('.xor'):
                os.remove(fil)

        # Remove replay/cap/xor files from temp
        temp_dir = Configuration.temp()
        for fil in os.listdir(temp_dir):
            if fil.startswith('replay_') and fil.endswith('.cap') or fil.endswith('.xor'):
                os.remove(os.path.join(temp_dir, fil))

    def get_targets(self, old_targets=[], apply_filter=True):
        ''' Parses airodump's CSV file, returns list of Targets '''

        # Find the .CSV file
        csv_filename = None
        for fil in self.find_files(endswith='.csv'):
            csv_filename = fil  # Found the file
            break

        if csv_filename is None or not os.path.exists(csv_filename):
            return self.targets  # No file found

        targets = Airodump.get_targets_from_csv(csv_filename)
        for old_target in old_targets:
            for target in targets:
                if old_target.bssid == target.bssid:
                    target.wps = old_target.wps

        # Check targets for WPS
        if not self.skip_wps:
            capfile = csv_filename[:-3] + 'cap'
            try:
                Tshark.check_for_wps_and_update_targets(capfile, targets)
            except ValueError:
                # No tshark, or it failed. Fall-back to wash
                Wash.check_for_wps_and_update_targets(capfile, targets)

        if apply_filter:
            # Filter targets based on encryption & WPS capability
            targets = Airodump.filter_targets(targets, skip_wps=self.skip_wps)

        # Sort by power
        targets.sort(key=lambda x: x.power, reverse=True)

        # Identify decloaked targets
        for old_target in self.targets:
            for new_target in targets:
                if old_target.bssid != new_target.bssid:
                    continue

                if new_target.essid_known and not old_target.essid_known:
                    # We decloaked a target!
                    new_target.decloaked = True
                    self.decloaked_bssids.add(new_target.bssid)

        self.targets = targets
        self.deauth_hidden_targets()

        return self.targets


    @staticmethod
    def get_targets_from_csv(csv_filename):
        '''Returns list of Target objects parsed from CSV file.'''
        targets = []
        import csv
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
                # Each 'row' is a list of fields for a target/client

                if len(row) == 0: continue

                if row[0].strip() == 'BSSID':
                    # This is the 'header' for the list of Targets
                    hit_clients = False
                    continue

                elif row[0].strip() == 'Station MAC':
                    # This is the 'header' for the list of Clients
                    hit_clients = True
                    continue

                if hit_clients:
                    # The current row corresponds to a 'Client' (computer)
                    try:
                        client = Client(row)
                    except (IndexError, ValueError) as e:
                        # Skip if we can't parse the client row
                        continue

                    if 'not associated' in client.bssid:
                        # Ignore unassociated clients
                        continue

                    # Add this client to the appropriate Target
                    for t in targets:
                        if t.bssid == client.bssid:
                            t.clients.append(client)
                            break

                else:
                    # The current row corresponds to a 'Target' (router)
                    try:
                        target = Target(row)
                        targets.append(target)
                    except Exception:
                        continue

        return targets

    @staticmethod
    def filter_targets(targets, skip_wps=False):
        ''' Filters targets based on Configuration '''
        result = []
        # Filter based on Encryption
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

        # Filter based on BSSID/ESSID
        bssid = Configuration.target_bssid
        essid = Configuration.target_essid
        i = 0
        while i < len(result):
            if result[i].essid is not None and Configuration.ignore_essid is not None and Configuration.ignore_essid.lower() in result[i].essid.lower():
                result.pop(i)
            elif bssid and result[i].bssid.lower() != bssid.lower():
                result.pop(i)
            elif essid and result[i].essid and result[i].essid.lower() != essid.lower():
                result.pop(i)
            else:
                i += 1
        return result

    def deauth_hidden_targets(self):
        '''
        Sends deauths (to broadcast and to each client) for all
        targets (APs) that have unknown ESSIDs (hidden router names).
        '''
        self.decloaking = False

        if Configuration.no_deauth:
            return  # Do not deauth if requested

        if self.channel is None:
            return  # Do not deauth if channel is not fixed.

        # Reusable deauth command
        deauth_cmd = [
            'aireplay-ng',
            '-0', # Deauthentication
            str(Configuration.num_deauths), # Number of deauth packets to send
            '--ignore-negative-one'
        ]

        for target in self.targets:
            if target.essid_known:
                continue

            now = int(time.time())
            secs_since_decloak = now - self.decloaked_times.get(target.bssid, 0)

            if secs_since_decloak < 30:
                continue  # Decloak every AP once every 30 seconds

            self.decloaking = True
            self.decloaked_times[target.bssid] = now
            if Configuration.verbose > 1:
                from ..util.color import Color
                Color.pe('{C} [?] Deauthing %s (broadcast & %d clients){W}' % (target.bssid, len(target.clients)))

            # Deauth broadcast
            iface = Configuration.interface
            Process(deauth_cmd + ['-a', target.bssid, iface])

            # Deauth clients
            for client in target.clients:
                Process(deauth_cmd + ['-a', target.bssid, '-c', client.bssid, iface])

if __name__ == '__main__':
    ''' Example usage. wlan0mon should be in Monitor Mode '''
    with Airodump() as airodump:

        from time import sleep
        sleep(7)

        from ..util.color import Color

        targets = airodump.get_targets()
        for idx, target in enumerate(targets, start=1):
            Color.pl('   {G}%s %s' % (str(idx).rjust(3), target.to_str()))

    Configuration.delete_temp()
