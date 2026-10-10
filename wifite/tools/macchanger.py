#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MAC address changer with native Python fallback.

Uses native Python implementation when possible, falls back to macchanger binary.
"""

from .dependency import Dependency
from ..tools.ip import Ip
from ..util.color import Color


class Macchanger(Dependency):
    dependency_required = False
    dependency_name = 'macchanger'
    dependency_url = 'apt install macchanger'

    is_changed = False
    _original_mac = None  # Track original MAC for reset
    
    # Try native implementation first
    _use_native = None

    @classmethod
    def _can_use_native(cls) -> bool:
        """Check if native MAC manipulation is available."""
        if cls._use_native is None:
            try:
                from ..native.mac import NativeMac
                cls._use_native = True
            except ImportError:
                cls._use_native = False
        return cls._use_native

    @classmethod
    def get_interface(cls):
        """Helper method to get interface from configuration."""
        from ..config import Configuration
        return Configuration.interface

    @classmethod
    def down_macch_up(cls, iface, options):
        """Put interface down, run macchanger with options, put interface up."""
        from ..util.process import Process

        Color.clear_entire_line()
        Color.p('\r{+} {C}macchanger{W}: taking interface {C}%s{W} down...' % iface)

        Ip.down(iface)

        Color.clear_entire_line()
        Color.p('\r{+} {C}macchanger{W}: changing mac address of interface {C}%s{W}...' % iface)

        command = ['macchanger']
        command.extend(options)
        command.append(iface)
        macch = Process(command)
        macch.wait()
        if macch.poll() != 0:
            Color.pl('\n{!} {R}macchanger{O}: error running {R}%s{O}' % ' '.join(command))
            Color.pl('{!} {R}output: {O}%s, %s{W}' % (macch.stdout(), macch.stderr()))
            return False

        Color.clear_entire_line()
        Color.p('\r{+} {C}macchanger{W}: bringing interface {C}%s{W} up...' % iface)

        Ip.up(iface)

        return True

    @classmethod
    def reset(cls):
        """Reset MAC to original/permanent value."""
        iface = cls.get_interface()
        Color.pl('\r{+} {C}macchanger{W}: resetting mac address on %s...' % iface)
        
        # Try native implementation first
        if cls._can_use_native():
            try:
                from ..native.mac import NativeMac
                
                # Interface must be down
                Ip.down(iface)
                
                success, msg = NativeMac.reset(iface)
                
                # Bring interface back up
                Ip.up(iface)
                
                if success:
                    new_mac = NativeMac.get_mac(iface)
                    Color.clear_entire_line()
                    Color.pl('\r{+} {C}macchanger{W}: reset mac address back to {C}%s{W} on {C}%s{W}' % (new_mac, iface))
                    cls.is_changed = False
                    return
                    
            except Exception as e:
                # Fall back to macchanger binary
                pass
        
        # Fallback: use macchanger binary
        # -p to reset to permanent MAC address
        if cls.down_macch_up(iface, ['-p']):
            new_mac = Ip.get_mac(iface)
            Color.clear_entire_line()
            Color.pl('\r{+} {C}macchanger{W}: reset mac address back to {C}%s{W} on {C}%s{W}' % (new_mac, iface))
            cls.is_changed = False

    @classmethod
    def random(cls, full_random=True):
        """
        Set a random MAC address.
        
        Args:
            full_random: If True, fully random MAC. If False, keep vendor OUI.
        """
        from ..util.process import Process
        
        iface = cls.get_interface()
        Color.pl('\n{+} {C}macchanger{W}: changing mac address on {C}%s{W}' % iface)
        
        # Store original MAC if not already stored
        if cls._original_mac is None:
            cls._original_mac = Ip.get_mac(iface)
        
        # Try native implementation first
        if cls._can_use_native():
            try:
                from ..native.mac import NativeMac
                
                Color.clear_entire_line()
                Color.p('\r{+} {C}macchanger{W}: taking interface {C}%s{W} down...' % iface)
                
                Ip.down(iface)
                
                Color.clear_entire_line()
                Color.p('\r{+} {C}macchanger{W}: changing mac address of interface {C}%s{W}...' % iface)
                
                success, result = NativeMac.random(iface, keep_vendor=not full_random)
                
                Color.clear_entire_line()
                Color.p('\r{+} {C}macchanger{W}: bringing interface {C}%s{W} up...' % iface)
                
                Ip.up(iface)
                
                if success:
                    cls.is_changed = True
                    Color.clear_entire_line()
                    Color.pl('\r{+} {C}macchanger{W}: changed mac address to {C}%s{W} on {C}%s{W} (native)' % (result, iface))
                    return
                    
            except (OSError, RuntimeError) as e:
                # Bring interface back up if it was taken down
                try:
                    Ip.up(iface)
                except (OSError, ValueError):
                    pass
        
        # Fallback: use macchanger binary
        if not Process.exists('macchanger'):
            Color.pl('{!} {R}macchanger: {O}not installed')
            return

        # -r to use random MAC address
        # -e to keep vendor bytes the same
        option = "-r" if full_random else "-e"

        if cls.down_macch_up(iface, [option]):
            cls.is_changed = True
            new_mac = Ip.get_mac(iface)
            Color.clear_entire_line()
            Color.pl('\r{+} {C}macchanger{W}: changed mac address to {C}%s{W} on {C}%s{W}' % (new_mac, iface))

    @classmethod
    def set_mac(cls, mac_address):
        """
        Set a specific MAC address.
        
        Args:
            mac_address: MAC address to set (e.g., '00:11:22:33:44:55')
        """
        from ..util.process import Process
        
        iface = cls.get_interface()
        Color.pl('\n{+} {C}macchanger{W}: setting mac address to {C}%s{W} on {C}%s{W}' % (mac_address, iface))
        
        # Store original MAC if not already stored
        if cls._original_mac is None:
            cls._original_mac = Ip.get_mac(iface)
        
        # Try native implementation first
        if cls._can_use_native():
            try:
                from ..native.mac import NativeMac
                
                Ip.down(iface)
                success, msg = NativeMac.set_mac(iface, mac_address)
                Ip.up(iface)
                
                if success:
                    cls.is_changed = True
                    Color.clear_entire_line()
                    Color.pl('\r{+} {C}macchanger{W}: set mac address to {C}%s{W} on {C}%s{W} (native)' % (mac_address, iface))
                    return True
                    
            except (OSError, RuntimeError):
                try:
                    Ip.up(iface)
                except (OSError, ValueError):
                    pass
        
        # Fallback: use macchanger binary
        if not Process.exists('macchanger'):
            Color.pl('{!} {R}macchanger: {O}not installed')
            return False

        if cls.down_macch_up(iface, ['-m', mac_address]):
            cls.is_changed = True
            Color.clear_entire_line()
            Color.pl('\r{+} {C}macchanger{W}: set mac address to {C}%s{W} on {C}%s{W}' % (mac_address, iface))
            return True
        
        return False

    @classmethod
    def reset_if_changed(cls):
        """Reset MAC only if it was changed."""
        if cls.is_changed:
            cls.reset()
    
    @classmethod
    def exists(cls):
        """
        Check if MAC changing capability is available.
        
        Returns True if either native implementation or macchanger binary is available.
        """
        if cls._can_use_native():
            return True
        
        from ..util.process import Process
        return Process.exists(cls.dependency_name)
