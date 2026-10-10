#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from ..model.attack import Attack
from ..util.color import Color
from ..util.logger import log_info, log_debug
from ..config import Configuration
from ..util.output import OutputManager
from ..tools.bully import Bully
from ..tools.reaver import Reaver


class AttackWPS(Attack):
    @staticmethod
    def can_attack_wps():
        return Reaver.exists() or Bully.exists()

    def __init__(self, target, pixie_dust=False, null_pin=False):
        super(AttackWPS, self).__init__(target)
        self.success = False
        self.crack_result = None
        self.pixie_dust = pixie_dust
        self.null_pin = null_pin
        
        # Initialize TUI view if in TUI mode
        self.view = None
        if OutputManager.is_tui_mode():
            try:
                from ..ui.attack_view import WPSAttackView
                self.view = WPSAttackView(OutputManager.get_controller(), target)
                if pixie_dust:
                    self.view.set_pixie_dust_mode(True)
            except Exception:
                # If TUI initialization fails, continue without it
                self.view = None

    def run(self):
        """ Run all WPS-related attacks """

        mode = 'pixie-dust' if self.pixie_dust else ('null-pin' if self.null_pin else 'pin')
        log_info('AttackWPS', 'Starting WPS %s attack on %s (%s)' % (
            mode, self.target.essid or '?', self.target.bssid))
        self._attack_start = time.time()

        # Start TUI view if available
        if self.view:
            self.view.start()
            self.view.set_attack_type("WPS Attack")

        # Drop out if user specified to not use Reaver/Bully
        if Configuration.use_pmkid_only:
            self.success = False
            return False

        if Configuration.no_wps:
            self.success = False
            return False

        if not Configuration.wps_pixie and self.pixie_dust:
            return self._handle_wps_skip(
                '\r{!} {O}--no-pixie{R} was given, ignoring WPS Pixie-Dust Attack on {O}%s{W}'
            )
        if not Configuration.wps_no_nullpin and self.null_pin:
            #Color.pl('\r{!} {O}--no-nullpin{R} was given, ignoring WPS NULLPIN Attack on {O}%s{W}' % self.target.essid)
            self.success = False
            return False

        if not Configuration.wps_pin and not self.pixie_dust:
            return self._handle_wps_skip(
                '\r{!} {O}--pixie{R} was given, ignoring WPS PIN Attack on {O}%s{W}'
            )
        
        # Cache pixie-dust support check to avoid duplicate reaver -h calls
        reaver_supports_pixie = Reaver.is_pixiedust_supported() if self.pixie_dust else True
        
        if not Reaver.exists() and Bully.exists():
            # Use bully if reaver isn't available
            return self.run_bully()
        elif self.pixie_dust and not reaver_supports_pixie and Bully.exists():
            # Use bully if reaver can't do pixie-dust
            return self.run_bully()
        elif Configuration.use_bully:
            # Use bully if asked by user
            return self.run_bully()
        elif not Reaver.exists():
            # Print error if reaver isn't found (bully not available)
            if self.pixie_dust:
                Color.pl('\r{!} {R}Skipping WPS Pixie-Dust attack: {O}reaver{R} not found.{W}')
            else:
                Color.pl('\r{!} {R}Skipping WPS PIN attack: {O}reaver{R} not found.{W}')
            return False
        elif self.pixie_dust and not reaver_supports_pixie:
            # Print error if reaver can't support pixie-dust (bully not available)
            Color.pl('\r{!} {R}Skipping WPS attack: {O}reaver{R} does not support {O}--pixie-dust{W}')
            return False
        else:
            return self.run_reaver()

    def _handle_wps_skip(self, message):
        Color.pl(message % self.target.essid)
        self.success = False
        return False

    def run_bully(self):
        log_debug('AttackWPS', 'Using bully for WPS attack')
        bully = Bully(self.target, pixie_dust=self.pixie_dust)
        # Pass the view to bully for TUI updates
        if self.view:
            bully.attack_view = self.view
        bully.run()
        bully.stop()
        self.crack_result = bully.crack_result
        self.success = self.crack_result is not None
        log_info('AttackWPS', 'WPS bully attack on %s finished in %.1fs — %s' % (
            self.target.bssid, time.time() - getattr(self, '_attack_start', time.time()),
            'SUCCESS' if self.success else 'no pin'))
        return self.success

    def run_reaver(self):
        log_debug('AttackWPS', 'Using reaver for WPS attack')
        reaver = Reaver(self.target, pixie_dust=self.pixie_dust, null_pin=self.null_pin)
        # Pass the view to reaver for TUI updates
        if self.view:
            reaver.attack_view = self.view
        reaver.run()
        self.crack_result = reaver.crack_result
        self.success = self.crack_result is not None
        log_info('AttackWPS', 'WPS reaver attack on %s finished in %.1fs — %s' % (
            self.target.bssid, time.time() - getattr(self, '_attack_start', time.time()),
            'SUCCESS' if self.success else 'no pin'))
        return self.success
