#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..util.color import Color
from ..config import Configuration
from ..tools.bully import Bully
from ..tools.reaver import Reaver

class AttackWPS(Attack):
    def __init__(self, target):
        super(AttackWPS, self).__init__(target)
        self.success = False
        self.crack_result = None

    def run(self):
        ''' Run all WPS-related attacks '''

        # Drop out if user specified to not use Reaver/Bully
        if Configuration.no_wps:
            Color.pl('\r{!} {O}--no-wps{R} set, ignoring WPS attack on {O}%s{W}' % self.target.essid)
            self.success = False
            return self.success

        ###################
        # Pixie-Dust attack
        if Configuration.use_bully:
            # Bully: Pixie-dust
            bully = Bully(self.target)
            bully.run()
            bully.stop()
            self.crack_result = bully.crack_result
            self.success = self.crack_result is not None
            return self.success
        else:
            reaver = Reaver(self.target)
            if reaver.is_pixiedust_supported():
                # Reaver: Pixie-dust
                reaver = Reaver(self.target)
                reaver.run()
                self.crack_result = reaver.crack_result
                self.success = self.crack_result is not None
                return self.success
            else:
                Color.pl("{!} {R}your version of 'reaver' does not support the {O}WPS pixie-dust attack{W}")

        return False
