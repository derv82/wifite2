#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Attack import Attack
from Airodump import Airodump
from Color import Color
from Configuration import Configuration
from CrackResultWPS import CrackResultWPS
from Process import Process
from Bully import Bully

class AttackWPS(Attack):
    def __init__(self, target):
        super(AttackWPS, self).__init__(target)
        self.success = False
        self.crack_result = None

    def run(self):
        ''' Run all WPS-related attacks '''

        # Drop out if user specified to not use Reaver
        if Configuration.no_reaver:
            self.success = False
            return self.success

        # Run Pixie-Dust attack
        bully = Bully(self.target, pixie=True)
        if bully.crack_result is not None:
            # Pixie-Dust attack succeeded. We're done.
            self.crack_result = bully.crack_result
        elif Configuration.pixie_only:
            Color.pl('\r{!} {O}--pixie{R} set, ignoring WPS-PIN attack{W}')
        else:
            # Run WPS-PIN attack
            bully = Bully(self.target, pixie=False)
            self.crack_result = bully.crack_result
        return self.crack_result is not None

