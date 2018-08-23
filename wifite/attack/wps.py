#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..model.attack import Attack
from ..util.color import Color
from ..config import Configuration

class AttackWPS(Attack):
    def __init__(self, target, pixie_dust=False):
        super(AttackWPS, self).__init__(target)
        self.success = False
        self.crack_result = None
        self.pixie_dust = pixie_dust

    def run(self):
        ''' Run all WPS-related attacks '''

        # Drop out if user specified to not use Reaver/Bully
        if Configuration.use_pmkid_only:
            Color.pl('\r{!} {O}--pmkid{R} set, ignoring WPS attack on ' +
                    '{O}%s{W}' % self.target.essid)
            self.success = False
            return False

        if Configuration.no_wps:
            Color.pl('\r{!} {O}--no-wps{R} set, ignoring WPS attack on ' +
                    '{O}%s{W}' % self.target.essid)
            self.success = False
            return False

        if not Configuration.wps_pixie and self.pixie_dust:
            Color.pl('\r{!} {O}--no-pixie{R} set, ignoring WPS attack on ' +
                    '{O}%s{W}' % self.target.essid)
            self.success = False
            return False

        if not Configuration.wps_pin and not self.pixie_dust:
            Color.pl('\r{!} {O}--no-pin{R} set, ignoring WPS attack on ' +
                    '{O}%s{W}' % self.target.essid)
            self.success = False
            return False

        if Configuration.use_bully:
            return self.run_bully()
        else:
            return self.run_reaver()

        return False


    def run_bully(self):
        from ..tools.bully import Bully
        bully = Bully(self.target, pixie_dust=self.pixie_dust)
        bully.run()
        bully.stop()
        self.crack_result = bully.crack_result
        self.success = self.crack_result is not None
        return self.success


    def run_reaver(self):
        from ..tools.reaver import Reaver

        reaver = Reaver(self.target, pixie_dust=self.pixie_dust)
        reaver.run()
        self.crack_result = reaver.crack_result
        self.success = self.crack_result is not None
        return self.success

