#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..util.process import Process
from ..util.color import Color
from ..util.input import raw_input
from ..config import Configuration
from ..model.result import CrackResult

from datetime import datetime

import os

class CrackHandshake(object):
    def __init__(self):
        self.wordlist = Configuration.wordlist or "path_to_wordlist_here"

        handshake = self.choose_handshake()
        self.crack_handshake(handshake)

    def crack_handshake(self, handshake):
        cap_file = handshake["handshake_file"]
        bssid = handshake["bssid"]
        Color.pl("\n  Below are commands to crack the handshake {C}%s{W}:" % cap_file)
        self.print_aircrack(cap_file, bssid)
        self.print_pyrit(cap_file, bssid)
        self.print_john(cap_file)
        self.print_oclhashcat(cap_file)
        Color.pl("")
        # TODO: cowpatty, oclhashcat

    def print_aircrack(self, cap_file, bssid):
        Color.pl("")
        if not Process.exists("aircrack-ng"):
            Color.pl("  {R}aircrack-ng not found.");
            Color.pl("  {O}More info on installing {R}Aircrack{O} here: {C}https://www.aircrack-ng.org/downloads.html{W}");
            return
        Color.pl("  {O}# AIRCRACK: CPU-based cracking. Slow.")
        Color.pl("  {G}aircrack-ng {W}-a {C}2 {W}-b {C}%s {W}-w {C}%s %s{W}" % (bssid, self.wordlist, cap_file))

    def print_pyrit(self, cap_file, bssid):
        Color.pl("")
        if not Process.exists("pyrit"):
            Color.pl("  {R}pyrit not found.");
            Color.pl("  {O}More info on installing {R}Pyrit{O} here: {C}https://github.com/JPaulMora/Pyrit{W}");
            return
        Color.pl("  {O}# PYRIT: GPU-based cracking. Fast.")
        Color.pl("  {G}pyrit {W}-b {C}%s {W}-i {C}%s {W}-r {C}%s {W}attack_passthrough{W}" % (bssid, self.wordlist, cap_file))

    def print_john(self, cap_file):
        Color.pl("")
        if not Process.exists("john"):
            Color.pl("  {R}john not found.");
            Color.pl("  {O}More info on installing {R}John The Ripper{O} here: {C}http://www.openwall.com/john/{W}");
            return
        Color.pl("  {O}# JOHN: CPU or GPU-based cracking. Fast.")
        Color.pl("  {O}# Use --format=wpapsk-cuda (or wpapsk-opengl) to enable GPU acceleration")
        Color.pl("  {O}# See http://openwall.info/wiki/john/WPA-PSK for more info on this process")
        Color.pl("  {G}aircrack-ng {W}-J hccap {C}%s{W}" % cap_file)
        Color.pl("  {G}hccap2john {C}hccap.hccap {W}> {C}hccap.john{W}")
        Color.pl("  {G}john {W}--wordlist {C}\"%s\" {W}--format=wpapsk {C}\"hccap.john\"{W}" % (self.wordlist))

    def print_oclhashcat(self, cap_file):
        Color.pl("")
        if not Process.exists("hashcat"):
            Color.pl("  {R}hashcat {O}not found.");
            Color.pl("  {O}More info on installing {R}hashcat{O} here: {C}https://hashcat.net/hashcat/");
            return
        Color.pl("  {O}# HASHCAT: GPU-based cracking. Fast.")
        Color.pl("  {O}# See {C}https://hashcat.net/wiki/doku.php?id=cracking_wpawpa2 {O}for more info")

        hccapx_file = "/tmp/generated.hccapx"
        cap2hccapx = "/usr/lib/hashcat-utils/cap2hccapx.bin"
        if os.path.exists(cap2hccapx):
            Color.pl("  {G}%s {W}%s {C}%s{W}" % (cap2hccapx, cap_file, hccapx_file))
        else:
            Color.pl("  {O}# Install hashcat-utils: {C}https://hashcat.net/wiki/doku.php?id=hashcat_utils")
            Color.pl("  {C}cap2hccapx.bin {W}%s {C}%s{W}" % (cap_file, hccapx_file))
            Color.pl("  {O}# OR visit https://hashcat.net/cap2hccapx to generate a .hccapx file{W}")
            Color.pl("  {O}# Then click BROWSE -> %s -> CONVERT and save to %s" % (cap_file, hccapx_file))

        Color.pl("  {G}hashcat {W}-m 2500 {C}%s %s{W}" % (hccapx_file, self.wordlist))

    def choose_handshake(self):
        hs_dir = Configuration.wpa_handshake_dir
        Color.pl("{+} Listing captured handshakes from {C}%s{W}\n" % os.path.realpath(hs_dir))
        handshakes = []
        for hs_file in os.listdir(hs_dir):
            if not hs_file.endswith('.cap') or hs_file.count("_") != 3:
                continue

            name, essid, bssid, date = hs_file.split("_")

            if name != 'handshake':
                continue

            handshakes.append({
                'essid': essid,
                'bssid': bssid.replace('-', ':'),
                'date': date.replace('.cap', '').replace('T', ' '),
                'handshake_file': os.path.realpath(os.path.join(hs_dir, hs_file))
            })

        handshakes.sort(key=lambda x: x['date'], reverse=True)

        if len(handshakes) == 0:
            raise Exception("No handshakes found in %s" % os.path.realpath(hs_dir))

        # Handshakes Header
        max_essid_len = max(max([len(hs["essid"]) for hs in handshakes]), len('(truncated) ESSDID'))
        Color.p("  NUM")
        Color.p("  " + "ESSID (truncated)".ljust(max_essid_len))
        Color.p("  " + "BSSID".ljust(17))
        Color.p("  DATE CAPTURED\n")
        Color.p("  ---")
        Color.p("  " + ("-" * max_essid_len))
        Color.p("  " + ("-" * 17))
        Color.p("  " + ("-" * 19) + "\n")
        # Print all handshakes
        for idx, hs in enumerate(handshakes, start=1):
            bssid = hs["bssid"]
            essid = hs["essid"]
            date  = hs["date"]
            Color.p("  {G}%s{W}" % str(idx).rjust(3))
            Color.p("  {C}%s{W}" % essid.ljust(max_essid_len))
            Color.p("  {O}%s{W}" % bssid)
            Color.p("  {W}%s{W}\n" % date)
        # Get number from user
        hs_index = raw_input(Color.s("\n{+} Select handshake num to crack ({G}1-%d{W}): " % len(handshakes)))
        if not hs_index.isdigit():
            raise ValueError("Handshake NUM must be numeric, got (%s)" % hs_index)
        hs_index = int(hs_index)
        if hs_index < 1 or hs_index > len(handshakes):
            raise Exception("Handshake NUM must be between 1 and %d" % len(handshakes))

        return handshakes[hs_index - 1]
