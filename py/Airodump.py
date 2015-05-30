#!/usr/bin/python

from Process import Process
from Configuration import Configuration
from Target import Target
from Client import Client
from Wash import Wash

import os

class Airodump(object):
    ''' Wrapper around airodump-ng program '''

    def __init__(self, interface=None, channel=None, encryption=None, wps=False, target_bssid=None, output_file_prefix='airodump'):
        ''' Constructor, sets things up '''

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

        self.encryption = encryption
        self.wps = wps

        self.target_bssid = target_bssid
        self.output_file_prefix = output_file_prefix

    def __enter__(self):
        '''
            Setting things up for this context.
            Called at start of 'with Airodump(...) as x:'
        '''
        self.delete_airodump_temp_files()

        self.csv_file_prefix = Configuration.temp() + self.output_file_prefix

        # Build the command
        command = [
            'airodump-ng',
            self.interface,
            '-a', # Only show associated clients
            '-w', self.csv_file_prefix # Output file prefix
        ]
        if self.channel:
            command.extend(['-c', str(self.channel)])
        if self.encryption:
            command.extend(['--enc', self.encryption])
        if self.wps:
            command.extend(['--wps'])
        if self.target_bssid:
            command.extend(['--bssid', self.target_bssid])

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

    def delete_airodump_temp_files(self):
        ''' Deletes airodump* files in the temp directory '''
        for fil in os.listdir(Configuration.temp()):
            if fil.startswith(self.output_file_prefix):
                os.remove(Configuration.temp() + fil)

    def get_targets(self, wpa_wep_only=True):
        ''' Parses airodump's CSV file, returns list of Targets '''
        # Find the .CSV file
        csv_filename = None
        for fil in os.listdir(Configuration.temp()):
            if fil.startswith(self.output_file_prefix) and fil.endswith('-01.csv'):
                # Found the file
                csv_filename = Configuration.temp() + fil
                break
        if csv_filename == None or not os.path.exists(csv_filename):
            # No file found
            return self.targets

        targets = []

        # Parse the .CSV file
        import csv
        with open(csv_filename, 'rb') as csvopen:
            csv_reader = csv.reader(csvopen, delimiter=',')
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
                    client = Client(row)

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
                    target = Target(row)

                    if target.essid_len == 0:
                        # Ignore empty/blank ESSIDs
                        continue

                    if wpa_wep_only and 'WPA' not in target.encryption and 'WEP' not in target.encryption:
                        # Ignore non-WPA and non-WEP encrypted networks
                        continue

                    if self.encryption and self.encryption not in target.encryption:
                        # We're looking for a specific type of encryption
                        continue

                    targets.append(target)

        # Check targets for WPS
        capfile = csv_filename[:-3] + 'cap'
        Wash.check_for_wps_and_update_targets(capfile, targets)

        # Sort by power
        targets.sort(key=lambda x: x.power, reverse=True)

        self.targets = targets

        return self.targets


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

