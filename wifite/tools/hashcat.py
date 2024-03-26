#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..config import Configuration
from ..util.process import Process
from ..util.color import Color

import os

hccapx_autoremove = False  # change this to True if you want the hccapx files to be automatically removed


class Hashcat(Dependency):
    dependency_required = False
    dependency_name = 'hashcat'
    dependency_url = 'https://hashcat.net/hashcat/'

    @staticmethod
    def should_use_force():
        command = ['hashcat', '-I']
        stderr = Process(command).stderr()
        return 'No devices found/left' or 'Unstable OpenCL driver detected!' in stderr

    @staticmethod
    def crack_handshake(handshake, show_command=False):
        # Generate hccapx
        hccapx_file = HcxPcapngTool.generate_hccapx_file(handshake, show_command=show_command)

        key = None
        # Crack hccapx
        for additional_arg in ([], ['--show']):
            command = [
                'hashcat',
                '--quiet',
                '-m', '22000',
                hccapx_file,
                Configuration.wordlist
            ]
            if Hashcat.should_use_force():
                command.append('--force')
            command.extend(additional_arg)
            if show_command:
                Color.pl(f'{{+}} {{D}}Running: {{W}}{{P}}{" ".join(command)}{{W}}')
            process = Process(command)
            stdout, stderr = process.get_output()
            if ':' not in stdout:
                continue
            key = stdout.split(':', 5)[-1].strip()
            break

        return key

    @staticmethod
    def crack_pmkid(pmkid_file, verbose=False):
        """
        Cracks a given pmkid_file using the PMKID/WPA2 attack (-m 22000)
        Returns:
            Key (str) if found; `None` if not found.
        """

        # Run hashcat once normally, then with --show if it failed
        # To catch cases where the password is already in the pot file.
        for additional_arg in ([], ['--show']):
            command = [
                'hashcat',
                '--quiet',      # Only output the password if found.
                '-m', '22000',  # WPA-PMKID-PBKDF2
                '-a', '0',      # Wordlist attack-mode
                pmkid_file,
                Configuration.wordlist,
                '-w', '3'
            ]
            if Hashcat.should_use_force():
                command.append('--force')
            command.extend(additional_arg)
            if verbose and additional_arg == []:
                Color.pl(f'{{+}} {{D}}Running: {{W}}{{P}}{" ".join(command)}{{W}}')

            # TODO: Check status of hashcat (%); it's impossible with --quiet

            hashcat_proc = Process(command)
            hashcat_proc.wait()
            stdout = hashcat_proc.stdout()

            if ':' not in stdout:
                # Failed
                continue
            else:
                return stdout.strip().split(':', 1)[1]


class HcxDumpTool(Dependency):
    dependency_required = False
    dependency_name = 'hcxdumptool'
    dependency_url = 'apt install hcxdumptool'

    def __init__(self, target, pcapng_file):
        if os.path.exists(pcapng_file):
            os.remove(pcapng_file)

        command = [
            'hcxdumptool',
            '-i', Configuration.interface,
            '-c', str(target.channel) + 'a',
            '-w', pcapng_file
        ]

        self.proc = Process(command)

    def poll(self):
        return self.proc.poll()

    def interrupt(self):
        self.proc.interrupt()


class HcxPcapngTool(Dependency):
    dependency_required = False
    dependency_name = 'hcxpcapngtool'
    dependency_url = 'apt install hcxtools'

    def __init__(self, target):
        self.target = target
        self.bssid = self.target.bssid.lower().replace(':', '')
        self.pmkid_file = Configuration.temp(f'pmkid-{self.bssid}.22000')

    @staticmethod
    def generate_hccapx_file(handshake, show_command=False):
        hccapx_file = Configuration.temp('generated.hccapx')
        if os.path.exists(hccapx_file):
            os.remove(hccapx_file)

        command = [
            'hcxpcapngtool',
            '-o', hccapx_file,
            handshake.capfile
        ]

        if show_command:
            Color.pl('{+} {D}Running: {W}{P}%s{W}' % ' '.join(command))

        process = Process(command)
        stdout, stderr = process.get_output()
        if not os.path.exists(hccapx_file):
            raise ValueError('Failed to generate .hccapx file, output: \n%s\n%s' % (
                stdout, stderr))

        return hccapx_file

    @staticmethod
    def generate_john_file(handshake, show_command=False):
        john_file = Configuration.temp('generated.john')
        if os.path.exists(john_file):
            os.remove(john_file)

        command = [
            'hcxpcapngtool',
            '--john', john_file,
            handshake.capfile
        ]

        if show_command:
            Color.pl('{+} {D}Running: {W}{P}%s{W}' % ' '.join(command))

        process = Process(command)
        stdout, stderr = process.get_output()
        if not os.path.exists(john_file):
            raise ValueError('Failed to generate .john file, output: \n%s\n%s' % (
                stdout, stderr))

        return john_file

    def get_pmkid_hash(self, pcapng_file):
        if os.path.exists(self.pmkid_file):
            os.remove(self.pmkid_file)

        command = 'hcxpcapngtool -o ' + self.pmkid_file + " " + pcapng_file
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
            if len(fields) >= 3 and fields[3].lower() == self.bssid:
                # Found it
                matching_pmkid_hash = line
                break

        os.remove(self.pmkid_file)
        return matching_pmkid_hash
