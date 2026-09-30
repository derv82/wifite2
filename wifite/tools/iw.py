#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency


class Iw(Dependency):
    '''
    Wrapper around the `iw` command (nl80211 / iproute2 userspace).

    Replaces the deprecated `iwconfig` (from the `wireless-tools` package),
    which has been dropped from recent distributions -- e.g. Ubuntu 26.04 no
    longer ships `wireless-tools` at all. Symlinking `iwconfig` to `iw` is not
    a valid workaround: the two tools have different output formats, so parsing
    `iw`'s usage text as `iwconfig` output produces bogus "interfaces".
    See https://github.com/derv82/wifite2/issues/542
    '''
    dependency_required = True
    dependency_name = 'iw'
    dependency_url = 'apt-get install iw'

    @classmethod
    def mode(cls, iface, mode_name):
        '''
        Set the type of `iface` (e.g. 'monitor' or 'managed').

        Note: `iw` requires the interface to be down before its type can be
        changed. Callers are responsible for bringing it down/up around this
        call (see Airmon.start_bad_driver / stop_bad_driver).
        '''
        from ..util.process import Process

        pid = Process(['iw', 'dev', iface, 'set', 'type', mode_name])
        pid.wait()

        return pid.poll()

    @classmethod
    def get_interfaces(cls, mode=None):
        '''
        Returns a list of wireless interface names as reported by `iw dev`.

        If `mode` is given (e.g. 'Monitor'), only interfaces whose reported
        type matches (case-insensitively) are returned.
        '''
        from ..util.process import Process

        (out, err) = Process.call('iw dev')
        return cls._parse_iw_dev(out, mode=mode)

    @staticmethod
    def _parse_iw_dev(output, mode=None):
        '''
        Parse the output of `iw dev` into a list of interface names.

        `iw dev` groups interfaces under each phy, e.g.:

            phy#0
                Interface wlan0
                    ifindex 3
                    addr 00:11:22:33:44:55
                    type managed
                Interface wlan0mon
                    type monitor

        When `mode` is None, every interface is returned. When `mode` is set
        (e.g. 'Monitor'), only interfaces whose `type` line matches are
        returned. Matching is case-insensitive so callers can keep passing the
        old iwconfig-style 'Monitor' / 'Managed' values.
        '''
        interfaces = set()
        iface = None

        for line in output.split('\n'):
            stripped = line.strip()

            if stripped.startswith('Interface '):
                iface = stripped.split('Interface ', 1)[1].strip().split(' ')[0]
                if mode is None and iface:
                    interfaces.add(iface)

            elif stripped.startswith('type ') and iface:
                iface_type = stripped.split('type ', 1)[1].strip()
                if mode is not None and iface_type.lower() == mode.lower():
                    interfaces.add(iface)

        return list(interfaces)
