#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Process import Process
from Configuration import Configuration
from Target import Target
from Client import Client
from Wash import Wash

import os, time

class Airodump(object):
    ''' Wrapper around airodump-ng program '''

    def __init__(self, interface=None, channel=None, encryption=None,\
                       wps=False, target_bssid=None, output_file_prefix='airodump',\
                       ivs_only=False, skip_wash=False):
        '''
            Sets up airodump arguments, doesn't start process yet
        '''

        Configuration.initialize()

        if interface == None:
            interface = Configuration.interface
        if interface == None:
            raise Exception("Wireless interface must be defined (-i)")
        self.interface = interface

        self.targets = []

        if channel == None:
            channel = Configuration.target_channel
        self.channel = channel
        self.five_ghz = Configuration.five_ghz

        self.encryption = encryption
        self.wps = wps

        self.target_bssid = target_bssid
        self.output_file_prefix = output_file_prefix
        self.ivs_only = ivs_only
        self.skip_wash = skip_wash

        # For tracking decloaked APs (previously were hidden)
        self.decloaking = False
        self.decloaked_targets = []
        self.decloaked_times = {} # Map of BSSID(str) -> epoch(int) of last deauth


    def __enter__(self):
        '''
            Setting things up for this context.
            Called at start of 'with Airodump(...) as x:'
            Actually starts the airodump process.
        '''
        self.delete_airodump_temp_files()

        self.csv_file_prefix = Configuration.temp() + self.output_file_prefix

        # Build the command
        command = [
            'airodump-ng',
            self.interface,
            '-a', # Only show associated clients
            '-w', self.csv_file_prefix, # Output file prefix
            '--write-interval', '1' # Write every second
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

        if self.ivs_only:
            command.extend(['--output-format', 'ivs,csv'])
        else:
            command.extend(['--output-format', 'pcap,csv'])

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

        # Delete temp files
        self.delete_airodump_temp_files()


    def find_files(self, endswith=None):
        ''' Finds all files in the temp directory that start with the output_file_prefix '''
        result = []
        for fil in os.listdir(Configuration.temp()):
            if fil.startswith(self.output_file_prefix):
                if not endswith or fil.endswith(endswith):
                    result.append(Configuration.temp() + fil)
        return result

    def delete_airodump_temp_files(self):
        '''
            Deletes airodump* files in the temp directory.
            Also deletes replay_*.cap and *.xor files in pwd.
        '''
        # Remove all temp files
        for fil in self.find_files():
            os.remove(fil)

        # Remove .cap and .xor files from pwd
        for fil in os.listdir('.'):
            if fil.startswith('replay_') and fil.endswith('.cap'):
                os.remove(fil)
            if fil.endswith('.xor'):
                os.remove(fil)

    def get_targets(self, apply_filter=True):
        ''' Parses airodump's CSV file, returns list of Targets '''
        # Find the .CSV file
        csv_filename = None
        for fil in self.find_files(endswith='-01.csv'):
            # Found the file
            csv_filename = fil
            break
        if csv_filename == None or not os.path.exists(csv_filename):
            # No file found
            return self.targets

        # Parse the .CSV file
        targets = Airodump.get_targets_from_csv(csv_filename)

        # Check targets for WPS
        if not self.skip_wash:
            capfile = csv_filename[:-3] + 'cap'
            Wash.check_for_wps_and_update_targets(capfile, targets)

        if apply_filter:
            # Filter targets based on encryption & WPS capability
            targets = Airodump.filter_targets(targets, skip_wash=self.skip_wash)

        # Sort by power
        targets.sort(key=lambda x: x.power, reverse=True)

        for old_target in self.targets:
            for new_target in targets:
                if old_target.bssid != new_target.bssid: continue
                if new_target.essid_known and not old_target.essid_known:
                    # We decloaked a target!
                    self.decloaked_targets.append(new_target)

        self.targets = targets
        self.deauth_hidden_targets()

        return self.targets


    @staticmethod
    def get_targets_from_csv(csv_filename):
        '''
            Returns list of Target objects parsed from CSV file
        '''
        targets = []
        import csv
        with open(csv_filename, 'rb') as csvopen:
            lines = (line.replace('\0', '') for line in csvopen)
            csv_reader = csv.reader(lines, delimiter=',')
            hit_clients = False
            for row in csv_reader:
                # Each "row" is a list of fields for a target/client

                if len(row) == 0: continue

                if row[0].strip() == 'BSSID':
                    # This is the "header" for the list of Targets
                    hit_clients = False
                    continue

                elif row[0].strip() == 'Station MAC':
                    # This is the "header" for the list of Clients
                    hit_clients = True
                    continue

                if hit_clients:
                    # The current row corresponds to a "Client" (computer)
                    try:
                        client = Client(row)
                    except IndexError, ValueError:
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
                    # The current row corresponds to a "Target" (router)
                    try:
                        target = Target(row)
                        targets.append(target)
                    except Exception:
                        continue

        return targets

    @staticmethod
    def filter_targets(targets, skip_wash=False):
        ''' Filters targets based on Configuration '''
        result = []
        # Filter based on Encryption
        for target in targets:
            if 'WEP' in Configuration.encryption_filter and 'WEP' in target.encryption:
                result.append(target)
            elif 'WPA' in Configuration.encryption_filter and 'WPA' in target.encryption:
                    result.append(target)
            elif 'WPS' in Configuration.encryption_filter and target.wps:
                result.append(target)
            elif skip_wash:
                result.append(target)

        # Filter based on BSSID/ESSID
        bssid = Configuration.target_bssid
        essid = Configuration.target_essid
        i = 0
        while i < len(result):
            if bssid and result[i].bssid.lower() != bssid.lower():
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

        # Do not deauth if requested
        if Configuration.no_deauth: return

        # Do not deauth if channel is not fixed.
        if self.channel is None: return

        # Reusable deauth command
        deauth_cmd = [
            'aireplay-ng',
            '-0', # Deauthentication
            str(Configuration.num_deauths), # Number of deauth packets to send
            '--ignore-negative-one'
        ]
        for target in self.targets:
            if target.essid_known: continue
            now = int(time.time())
            secs_since_decloak = now - self.decloaked_times.get(target.bssid, 0)
            # Decloak every AP once every 30 seconds
            if secs_since_decloak < 30: continue
            self.decloaking = True
            self.decloaked_times[target.bssid] = now
            if Configuration.verbose > 1:
                from Color import Color
                verbout = " [?] Deauthing %s" % target.bssid
                verbout += " (broadcast & %d clients)" % len(target.clients)
                Color.pe("\n{C}" + verbout + "{W}")
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

        from Color import Color

        targets = airodump.get_targets()
        Target.print_header()
        for (index, target) in enumerate(targets):
            index += 1
            Color.pl('   {G}%s %s' % (str(index).rjust(3), target))

    Configuration.delete_temp()

