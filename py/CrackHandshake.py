#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from Process import Process
from Color import Color
from Configuration import Configuration
from CrackResult import CrackResult
from datetime import datetime

import os

class CrackHandshake(object):
    def __init__(self):
        self.wordlist = Configuration.wordlist or "path_to_wordlist_here"

        handshake = self.choose_handshake()
        self.crack_handshake(handshake)

    def crack_handshake(self, handshake):
        cap_file = os.path.realpath(handshake["handshake_file"])
        Color.pl("{+} Different ways to crack {C}%s{W}:" % cap_file)
        self.print_aircrack(cap_file)
        self.print_pyrit(cap_file)
        self.print_john(cap_file)
        self.print_oclhashcat(cap_file)
        Color.pl("")
        # TODO: cowpatty, oclhashcat

    def print_aircrack(self, cap_file):
        if not Process.exists("aircrack-ng"): return
        Color.pl("\n  {O}# AIRCRACK: CPU-based cracking. Slow.")
        Color.pl("  {G}aircrack-ng {W}-a 2 -w {C}%s %s{W}" % (self.wordlist, cap_file))

    def print_pyrit(self, cap_file):
        if not Process.exists("pyrit"): return
        Color.pl("\n  {O}# PYRIT: GPU-based cracking. Fast.")
        Color.pl("  {G}pyrit {W}-i {C}%s {W}-r {C}%s {W}attack_passthrough{W}" % (self.wordlist, cap_file))

    def print_john(self, cap_file):
        if not Process.exists("pyrit"): return
        Color.pl("\n  {O}# JOHN: CPU or GPU-based cracking. Fast.")
        Color.pl("  {O}# Use --format=wpapsk-cuda (or wpapsk-opengl) to enable GPU acceleration")
        Color.pl("  {O}# See http://openwall.info/wiki/john/WPA-PSK for more info on this process")
        Color.pl("  {G}aircrack-ng {W}-J hccap {C}%s{W}" % cap_file)
        Color.pl("  {G}hccap2john {W}hccap.hccap > hccap.john{W}")
        Color.pl("  {G}john {W}--wordlist {C}\"%s\" {W}--format=wpapsk {C}\"hccap.john\"{W}" % (self.wordlist))

    def print_oclhashcat(self, cap_file):
        if not Process.exists("hashcat"): return
        Color.pl("\n  {O}# OCLHASHCAT: GPU-based cracking. Fast.")
        hccapx_file = "generated.hccapx"
        if Process.exists("cap2hccapx"):
            Color.pl("  {G}cap2hccapx {C}%s %s{W}" % (cap_file, hccapx_file))
        else:
            Color.pl("  {O}# Visit https://hashcat.net/cap2hccapx to generate a .hccapx file{W}")
            Color.pl("  {O}# Browse -> %s -> Convert" % cap_file)
        Color.pl("  {G}hashcat {W}-m 2500 {C}%s %s{W}" % (hccapx_file, self.wordlist))

    def choose_handshake(self):
        Color.pl("\n{+} Listing captured handshakes...\n")
        handshakes = CrackResult.load_all()
        handshakes = [hs for hs in handshakes if "handshake_file" in hs and os.path.exists(hs["handshake_file"])]
        if len(handshakes) == 0:
            raise Exception("No handshakes found in %s" % os.path.realpath(CrackResult.cracked_file))

        # Handshakes Header
        max_essid_len = max([len(hs["essid"]) for hs in handshakes])
        Color.p("  NUM")
        Color.p("  " + "ESSID".ljust(max_essid_len))
        Color.p("  " + "BSSID".ljust(17))
        Color.p("  DATE CAPTURED\n")
        Color.p("  ---")
        Color.p("  " + ("-" * max_essid_len))
        Color.p("  " + ("-" * 17))
        Color.p("  " + ("-" * 19) + "\n")
        # Print all handshakes
        for index, hs in enumerate(handshakes):
            bssid = hs["bssid"]
            essid = hs["essid"]
            date = datetime.strftime(datetime.fromtimestamp(hs["date"]), "%Y-%m-%dT%H:%M:%S")
            Color.p("  {G}%s{W}" % str(index + 1).rjust(3))
            Color.p("  {C}%s{W}" % essid.ljust(max_essid_len))
            Color.p("  {C}%s{W}" % bssid)
            Color.p("  {C}%s{W}\n" % date)
        # Get number from user
        hs_index = raw_input(Color.s("\n{+} Select handshake num to crack ({G}1-%d{W}): " % len(handshakes)))
        if not hs_index.isdigit():
            raise Exception("Invalid input: %s" % hs_index)
        hs_index = int(hs_index)
        if hs_index < 1 or hs_index > len(handshakes):
            raise Exception("Handshake num must be between 1 and %d" % len(handshakes))

        return handshakes[hs_index - 1]
