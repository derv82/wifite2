#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..util.color import Color
from ..util.process import Process
from ..config import Configuration
from ..tools.bully import Bully
from ..tools.reaver import Reaver

class AttackWPS(Attack):

    @staticmethod
    def can_attack_wps():
        return Reaver.exists() or Bully.exists()

    def __init__(self, target, pixie_dust=False):
        super(AttackWPS, self).__init__(target)
        self.success = False
        self.crack_result = None
        self.pixie_dust = pixie_dust

    def run(self):
        ''' Run all WPS-related attacks '''

        # Drop out if user specified to not use Reaver/Bully
        if Configuration.use_pmkid_only:
            self.success = False
            return False

        if Configuration.no_wps:
            self.success = False
            return False

        if not Configuration.wps_pixie and self.pixie_dust:
            Color.pl('\r{!} {O}--no-pixie{R} was given, ignoring WPS PIN Attack on ' +
                    '{O}%s{W}' % self.target.essid)
            self.success = False
            return False

        if not Configuration.wps_pin and not self.pixie_dust:
            Color.pl('\r{!} {O}--no-pin{R} was given, ignoring WPS Pixie-Dust Attack ' +
                    'on {O}%s{W}' % self.target.essid)
            self.success = False
            return False

        if Configuration.use_bully and Bully.exists() or not Reaver.exists():
            return self.run_bully()

        elif Reaver.exists():
            return self.run_reaver()

        else:
            return False


    def run_bully(self):
        bully = Bully(self.target, pixie_dust=self.pixie_dust)
        bully.run()
        bully.stop()
        self.crack_result = bully.crack_result
        self.success = self.crack_result is not None
        return self.success


    def run_reaver(self):
        reaver = Reaver(self.target, pixie_dust=self.pixie_dust)
        reaver.run()
        self.crack_result = reaver.crack_result
        self.success = self.crack_result is not None
        return self.success

