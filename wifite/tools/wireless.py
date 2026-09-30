#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from .iwconfig import Iwconfig
from .iw import Iw


class Wireless(Dependency):
    '''
    Chooses the tool used to enumerate wireless interfaces and switch their
    mode (managed/monitor).

    For backwards-compatibility this prefers `iwconfig` (wireless-tools),
    preserving Wifite's long-standing behaviour on systems that still ship it,
    and falls back to `iw` (nl80211) where wireless-tools is unavailable --
    e.g. Ubuntu 26.04+ dropped the package entirely.
    See https://github.com/derv82/wifite2/issues/542

    The dependency is satisfied when *either* tool is present. A future
    release can drop the `iwconfig` branch and require `iw` outright.
    '''
    dependency_required = True
    # Used only for help text; the real logic is in fails_dependency_check().
    dependency_name = 'iw'
    dependency_url = 'apt install iw (or wireless-tools, which provides iwconfig)'

    @classmethod
    def backend(cls):
        '''Preferred interface tool: iwconfig if present, otherwise iw.'''
        if Iwconfig.exists():
            return Iwconfig
        return Iw

    @classmethod
    def get_interfaces(cls, mode=None):
        return cls.backend().get_interfaces(mode=mode)

    @classmethod
    def mode(cls, iface, mode_name):
        return cls.backend().mode(iface, mode_name)

    @classmethod
    def fails_dependency_check(cls):
        from ..util.color import Color

        if Iwconfig.exists() or Iw.exists():
            return False

        Color.p('{!} {O}Error: Required app {R}iw{O} (or {R}iwconfig{O}) was not found')
        Color.pl('. {W}install @ {C}apt install iw{W} (or {C}wireless-tools{W})')
        return True
