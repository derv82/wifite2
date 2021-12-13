# -*- coding: UTF-8 -*-
#
#    Copyright 2015, John Mora, johmora12@engineer.com
#    Original Work by Lukas Lueg (c) 2008-2011.
#
#    This file is part of Pyrit.
#
#    Pyrit is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Pyrit is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Pyrit.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement

import getopt
import glob
import gzip
import hashlib
import itertools
import os
import random
import sys
import time
import cpyrit.cpyrit
import cpyrit.config
import cpyrit.util
import cpyrit.storage


class PyritRuntimeError(RuntimeError):
    pass


class Pyrit_CLI(object):

    def __init__(self):
        self.verbose = True

    def tell(self, text, sep=' ', end='\n', stream=sys.stdout, flush=False):
        if self.verbose or stream != sys.stdout:
            stream.write(text)
            if end is not None:
                stream.write(end)
            else:
                if sep is not None:
                    stream.write(sep)
            if flush or end is None:
                stream.flush()

    def initFromArgv(self):
        options = {}
        args, commands = getopt.getopt(sys.argv[1:], \
                                       'b:e:i:o:r:u:h', \
                                       ('all-handshakes', 'aes'))
        args = dict(args)

        if len(commands) == 1 and commands[0] in self.commands:
            command = commands[0]
        else:
            command = 'help'
            args = {}
        if '-h' in args:
            func = Pyrit_CLI.print_command_help
            args = {'-c': command}
        else:
            func = self.commands[command]

        req_params, opt_params = func.cli_options
        for param in req_params:
            if param not in ('-u',) and param not in args:
                raise PyritRuntimeError("The command '%s' requires the " \
                                        "option '%s'. See 'help'." % \
                                        (command, param))
        for arg, value in args.iteritems():
            if arg in req_params or arg in opt_params:
                if arg == '-e':
                    options['essid'] = value
                elif arg == '-b':
                    options['bssid'] = str(value).lower()
                elif arg == '-i':
                    options['infile'] = value
                elif arg == '-o':
                    options['outfile'] = value
                    # Prevent messages from corrupting stdout
                    if value == '-':
                        self.verbose = False
                elif arg == '-r':
                    options['capturefile'] = value
                elif arg == '-c':
                    options['command'] = value
                elif arg == '--all-handshakes':
                    options['all_handshakes'] = True
                elif arg == '--aes':
                    options['use_aes'] = True
            else:
                raise PyritRuntimeError("The command '%s' ignores the " \
                                        "option '%s'." % (command, arg))

        self.tell("Pyrit %s (C) 2008-2011 Lukas Lueg - 2015 John Mora\n" \
                  "https://github.com/JPaulMora/Pyrit\n" \
                  "This code is distributed under the GNU General Public " \
                  "License v3+\n" % cpyrit.util.VERSION, stream=sys.stdout)
        if '-u' in req_params:
            if '-u' in args:
                storage_url = args['-u']
            else:
                storage_url = cpyrit.config.cfg['default_storage']
            options['storage'] = self._getStorage(storage_url)
        func(self, **options)

    def print_help(self):
        """Print general help

           You should have figured this one out by now.
        """
        self.tell('Usage: pyrit [options] command'
            '\n'
            '\nRecognized options:'
            '\n  -b               : Filters AccessPoint by BSSID'
            '\n  -e               : Filters AccessPoint by ESSID'
            '\n  -h               : Print help for a certain command'
            "\n  -i               : Filename for input ('-' is stdin)"
            "\n  -o               : Filename for output ('-' is stdout)"
            '\n  -r               : Packet capture source in pcap-format'
            '\n  -u               : URL of the storage-system to use'
            '\n  --all-handshakes : Use all handshakes instead of the best one'
            '\n  --aes            : Use AES'
            '\n'
            '\nRecognized commands:')
        m = max([len(command) for command in self.commands])
        for command, func in sorted(self.commands.items()):
            self.tell('  %s%s : %s' % (command, \
                                        ' ' * (m - len(command)), \
                                        func.__doc__.split('\n')[0]))
    print_help.cli_options = ((), ())

    def print_command_help(self, command):
        """Print help about a certain command"""
        doc = self.commands[command].__doc__
        self.tell('\n'.join(l.strip() for l in doc.split('\n')))
    print_command_help.cli_options = (('-c',), ())

    def requires_pckttools(*params):
        """Decorate a function to check for cpyrit.cpyrit_pckttools
           before execution.
        """

        def check_pkttools(f):

            def new_f(*args, **kwds):
                try:
                    import cpyrit.pckttools
                except ImportError:
                    raise PyritRuntimeError("Scapy 2.x is required to use " \
                                            "Pyrit's analyze/attack " \
                                            "functions but seems to be " \
                                            "unavailable.")
                f(*args, **kwds)
            new_f.func_name = f.func_name
            new_f.__doc__ = f.__doc__
            return new_f
        return check_pkttools

    def _getParser(self, capturefilemask):
        filelist = glob.glob(capturefilemask)
        if len(filelist) == 0:
            raise PyritRuntimeError("No file found that matches '%s'" % \
                                    capturefilemask)
        parser = cpyrit.pckttools.PacketParser()
        for idx, capturefile in enumerate(filelist, start=1):
            self.tell("Parsing file '%s' (%i/%i)..." % (capturefile, idx, \
                                                        len(filelist)))
            dev = cpyrit.pckttools.PcapDevice(capturefile)
            parser.parse_pcapdevice(dev)
        self.tell("Parsed %i packets (%i 802.11-packets), got %i AP(s)\n" % \
                    (parser.pcktcount, parser.dot11_pcktcount, len(parser)))
        return parser

    def _fuzzyGetAP(self, parser, bssid=None, essid=None):
        if bssid is None and essid is None:
            for ap in parser:
                if ap.isCompleted() and ap.essid is not None:
                    self.tell("Picked AccessPoint %s ('%s') automatically." % \
                                (ap, ap.essid))
                    return ap
            raise PyritRuntimeError("Specify an AccessPoint's BSSID or " \
                                    "ESSID using the options -b and -e. " \
                                    "See 'help'")
        if bssid is not None:
            if bssid not in parser:
                raise PyritRuntimeError("No AccessPoint with BSSID '%s' " \
                                        "found in the capture file..." % \
                                        bssid)
            ap = parser[bssid]
        else:
            ap = None
        if essid is not None:
            if ap is None:
                aps = filter(lambda ap: (ap.essid is None
                                          or ap.essid == essid)
                                        and ap.isCompleted(),
                                        parser)
                if len(aps) > 0:
                    ap = aps[0]
                    self.tell("Picked AccessPoint %s automatically..." % ap)
                else:
                    raise PyritRuntimeError("No suitable AccessPoint with " \
                                            "that ESSID in the capture file.")
            else:
                if ap.essid is not None and ap.essid != essid:
                    self.tell("WARNING: AccessPoint %s has ESSID '%s'. " \
                              "Using '%s' anyway." % (ap, ap.essid, essid), \
                              stream=sys.stderr)
        else:
            if ap.essid is None:
                raise PyritRuntimeError("The ESSID for AccessPoint %s is " \
                                        "not known from the capture file. " \
                                        "Specify it using the option -e." % ap)
        return ap

    def _getStorage(self, url):
        safe_url = cpyrit.storage.pruneURL(url)
        self.tell("Connecting to storage at '%s'... " % (safe_url,), end=None)
        storage = cpyrit.storage.getStorage(url)
        self.tell("connected.")
        return storage

    def create_essid(self, storage, essid=None, infile=None):
        """Create a new ESSID

           Add the ESSID given by -e to the database. Re-creating an existing
           ESSID does not result in an error.

           For example:
           pyrit -e NETGEAR create_essid
        """
        if essid is None and infile is None:
            raise PyritRuntimeError("Please specify the ESSID to create " \
                                    "with '-e' or a file to read ESSIDs " \
                                    "from with '-i'.")
        if essid is not None:
            if essid in storage.essids:
                self.tell("ESSID already created")
            else:
                storage.essids.create_essid(essid)
                self.tell("Created ESSID '%s'" % essid)
        elif infile is not None:
            with cpyrit.util.FileWrapper(infile) as reader:
                for essid in reader:
                    essid = essid.strip()
                    if essid not in storage.essids:
                        storage.essids.create_essid(essid)
                        self.tell("Created ESSID '%s'" % essid)
    create_essid.cli_options = (('-u', ), ('-e', '-i'))

    def delete_essid(self, storage, essid, confirm=True):
        """Delete a ESSID from the database

           Delete the ESSID given by -e from the database. This includes all
           results that may have been stored for that particular ESSID.

           For example:
           pyrit -e NETGEAR delete_essid
        """
        if essid not in storage.essids:
            raise PyritRuntimeError("ESSID not found...")
        else:
            if confirm:
                self.tell("All results for ESSID '%s' will be deleted! " \
                          "Continue? [y/N]" % essid, end=None)
                if sys.stdin.readline().strip() != 'y':
                    raise PyritRuntimeError("aborted.")
            self.tell("deleting...")
            del storage.essids[essid, None]
            self.tell("Deleted ESSID '%s'." % essid)
    delete_essid.cli_options = (('-e', '-u'), ())

    def list_cores(self):
        """List available cores

           Show a list of all available hardware modules pyrit currently uses.

           For example:
           pyrit list_cores
        """
        with cpyrit.cpyrit.CPyrit() as cp:
            if int(cpyrit.config.cfg['limit_ncpus']) < 0:
                self.tell("CPUs disabled in config...")
            else:
                self.tell("The following cores seem available...")
            for idx, core in enumerate(cp.cores, start=1):
                self.tell("#%i:  '%s'" % (idx, core))

            if cpyrit.config.cfg['use_OpenCL'] == 'true':
                if cpyrit.config.cfg['use_CUDA'] == 'true':
                    self.tell("\nWARNING: OpenCL disables CUDA!\n")
                if len(cp.OpCL) != 0:
                    self.tell("\nThe following OpenCL GPUs seem available...")
                    for idx, OCL in enumerate(cp.OpCL, start=1):
                        self.tell("#%i:  '%s'" % (idx, OCL))
            elif cpyrit.config.cfg['use_OpenCL'] == 'false' and cpyrit.config.cfg['use_CUDA'] == 'true':
                if len(cp.CUDAs) != 0:
                    self.tell("\nThe following CUDA GPUs seem available...")
                    for idx, CD in enumerate(cp.CUDAs, start=1):
                        self.tell("#%i:  '%s'" % (idx, CD))
    list_cores.cli_options = ((), ())

    def list_essids(self, storage):
        """List all ESSIDs but don't count matching results

           Show a list of all ESSIDs currently stored in the database. This
           function is faster than eval in case you don't need to know the
           number of computed results.

           For example:
           pyrit list_essids
        """
        self.tell("Listing ESSIDs...\n")
        for essid in sorted(storage.essids):
            self.tell("ESSID '%s'" % essid)
        self.tell("")
    list_essids.cli_options = (('-u', ), ())

    def eval_results(self, storage):
        """Count the available passwords and matching results

           Count all available passwords, all ESSIDs and their respective
           results in the database.

           For example:
           pyrit eval
        """
        self.tell("Querying...", end=None, flush=True)
        pwcount, essid_results = storage.getStats()
        self.tell("\rPasswords available: %i\n" % pwcount)
        if len(essid_results) > 0:
            m = max(len(essid) for essid in essid_results.iterkeys())
            n = max(len(str(c)) for c in essid_results.itervalues())
            for essid, rescnt in sorted(essid_results.iteritems()):
                self.tell("ESSID '%s'%s : %s%i (%.2f%%)" % (essid, \
                            ' ' * (m - len(essid)), \
                            ' ' * (n - len(str(rescnt))), rescnt, \
                            (rescnt * 100.0 / pwcount) if pwcount > 0 else 0))
            self.tell('')
    eval_results.cli_options = (('-u', ), ())

    def import_passwords(self, storage, infile, unique_check=True):
        """Import passwords from a file-like source

           Read the file given by -i and import one password per line to the
           database. The passwords may contain all characters (including
           NULL-bytes) apart from the terminating newline-character \\n.
           Passwords that are not suitable for being used with WPA-/WPA2-PSK
           are ignored. Pyrit's storage-implementation guarantees that all
           passwords remain unique throughout the entire database.

           For example:
           pyrit -i dirty_words.txt import_passwords
        """
        i = 0
        storage.passwords.unique_check = unique_check
        perfcounter = cpyrit.util.PerformanceCounter()
        with cpyrit.util.FileWrapper(infile) as reader:
            with storage.passwords as pwstore:
                for i, line in enumerate(reader):
                    pwstore.store_password(line)
                    if i % 100000 == 0:
                        perfcounter += 100000
                        self.tell("\r%i lines read (%.1f lines/s)..." % \
                                  (i, perfcounter.avg), end=None, flush=True)
                self.tell("\r%i lines read. Flushing buffers..." % (i + 1))
        self.tell('All done.')
    import_passwords.cli_options = (('-i', '-u'), ())

    def import_unique_passwords(self, storage, infile):
        """Import unique passwords from a file-like source

           Read the file given by -i and import one password per line to the
           database. The passwords may contain all characters (including
           NULL-bytes) apart from the terminating newline-character \\n.
           Passwords that are not suitable for being used with WPA-/WPA2-PSK
           are ignored. This command does not check if there are duplicating
           passwords within the file or between the file and the database; it
           should be used with caution to prevent the database from getting
           poisoned with duplicated passwords. This command however can be much
           faster than import_passwords.

           For example:
           pyrit -i dirty_words.txt import_unique_passwords
        """
        self.import_passwords(storage, infile, unique_check=False)
    import_unique_passwords.cli_options = (('-i', '-u'), ())

    def export_passwords(self, storage, outfile):
        """Export passwords to a file

           Write all passwords that are currently stored in the database to a
           new file given by -o. Passwords are terminated by a single
           newline-character (\\n). Existing files are overwritten without
           confirmation.

           For example:
           pyrit -o myword.txt.gz export_passwords
        """
        perfcounter = cpyrit.util.PerformanceCounter()
        with cpyrit.util.AsyncFileWriter(outfile) as awriter:
            for idx, pwset in enumerate(storage.iterpasswords(), start=1):
                awriter.write('\n'.join(pwset))
                awriter.write('\n')
                perfcounter += len(pwset)
                self.tell("%i lines written (%.1f lines/s, %.1f%%)\r" % \
                            (perfcounter.total, perfcounter.avg, \
                            idx * 100.0 / len(storage.passwords)), \
                            end=None, sep=None)
        self.tell("\nAll done")
    export_passwords.cli_options = (('-o', '-u'), ())

    def export_cowpatty(self, storage, essid, outfile):
        """Export results to a new cowpatty file

           Write all results for the ESSID given by -e to the file given by -o
           in cowpatty's binary format. Existing files are overwritten without
           confirmation.

           For example:
           pyrit -o NETGEAR.cow -e NETGEAR export_cowpatty
        """
        if essid not in storage.essids:
            raise PyritRuntimeError("The ESSID you specified can't be found.")
        perfcounter = cpyrit.util.PerformanceCounter()
        self.tell("Exporting to '%s'..." % outfile)
        with cpyrit.util.AsyncFileWriter(outfile) as filewriter:
            with cpyrit.util.CowpattyFile(filewriter, 'w', essid) as cpwriter:
                try:
                    for results in storage.iterresults(essid):
                        cpwriter.write(results)
                        perfcounter += len(results)
                        self.tell("\r%i entries written (%.1f/s)..." % \
                                   (perfcounter.total, perfcounter.avg), \
                                  end=None, sep=None)
                except IOError:
                    self.tell("IOError while exporting to " \
                              "stdout ignored...", stream=sys.stderr)
        self.tell("\r%i entries written. All done." % perfcounter.total)
    export_cowpatty.cli_options = (('-u', '-e', '-o'), ())

    @requires_pckttools()
    def analyze(self, capturefile):
        """Analyze a packet-capture file

           Parse one or more packet-capture files (in pcap-format,
           possibly gzip-compressed) and try to detect Access-Points,
           Stations and EAPOL-handshakes.

           For example:
           pyrit -r "test*.pcap" analyze
        """
        parser = self._getParser(capturefile)
        for i, ap in enumerate(parser):
            self.tell("#%i: AccessPoint %s ('%s'):" % (i + 1, ap, ap.essid))
            for j, sta in enumerate(ap):
                self.tell("  #%i: Station %s" % (j + 1, sta), \
                          end=None, sep=None)
                auths = sta.getAuthentications()
                if len(auths) > 0:
                    self.tell(", %i handshake(s):" % (len(auths),))
                    for k, auth in enumerate(auths):
                        self.tell("    #%i: %s" % (k + 1, auth))
                else:
                    self.tell("")
        if not any(ap.isCompleted() and ap.essid is not None for ap in parser):
            raise PyritRuntimeError("No valid EAOPL-handshake + ESSID " \
                                    "detected.")
    analyze.cli_options = (('-r', ), ())

    @requires_pckttools()
    def stripCapture(self, capturefile, outfile, bssid=None, essid=None):
        """Strip packet-capture files to the relevant packets

           Parse one or more packet-capture files given by the option -r,
           extract only packets that are necessary for EAPOL-handshake
           detection and write a new dump to the filename given by the option
           -o. The options -e and -b can be used to filter certain
           Access-Points.

           For example:
           pyrit -r "dumps_*.pcap" -e MyNetwork -o tiny.dump.gz strip
        """
        parser = self._getParser(capturefile)
        if essid is not None or bssid is not None:
            ap_iter = (self._fuzzyGetAP(parser, bssid, essid), )
        else:
            ap_iter = parser
        with cpyrit.pckttools.Dot11PacketWriter(outfile) as writer:
            for i, ap in enumerate(ap_iter):
                self.tell("#%i: AccessPoint %s ('%s')" % (i + 1, ap, ap.essid))
                if ap.essidframe:
                    writer.write(ap.essidframe)
                for j, sta in enumerate(ap):
                    self.tell("  #%i: Station %s" % (j, sta), \
                              end=None, sep=None)
                    auths = sta.getAuthentications()
                    if len(auths) > 0:
                        self.tell(", %i handshake(s)" % (len(auths),))
                        for k, auth in enumerate(auths):
                            self.tell("    #%i: %s" % (k + 1, auth))
                    else:
                        self.tell("")
                    packets = []
                    for pckt in sta.getPackets():
                        writer.write(pckt)
        self.tell("\nNew pcap-file '%s' written (%i out of %i packets)" % \
                    (outfile, writer.pcktcount, parser.pcktcount))
    stripCapture.cli_options = (('-r', '-o'), ('-e', '-b'))

    def _stripLive_newAP(self, parser, writer, ap):
        writer.write(ap.essidframe)
        self.tell("%i/%i: New AccessPoint %s ('%s')" % \
                  (writer.pcktcount, parser.pcktcount, ap, ap.essid))

    def _stripLive_newStation(self, parser, writer, station):
        self.tell("%i/%i: New Station %s (AP %s)" % \
                  (writer.pcktcount, parser.pcktcount, station, station.ap))

    def _stripLive_newKeyPckt(self, parser, writer, station, idx, pckt):
        writer.write(pckt)
        self.tell("%i/%i: %s AP %s <-> STA %s" % \
                  (writer.pcktcount, parser.pcktcount, \
                  ["Challenge", "Response", "Confirmation"][idx], \
                  station.ap, station))

    def _stripLive_newEncPckt(self, parser, writer, station, pckt):
        writer.write(pckt)
        self.tell("%i/%i: CCMP-Encrypted traffic AP %s <-> STA %s" % \
                  (writer.pcktcount, parser.pcktcount, station.ap, station))

    def _stripLive_newAuth(self, parser, writer, station, auth):
        self.tell("%i/%i: New Handshake AP %s: %s" % \
                  (writer.pcktcount, parser.pcktcount, station.ap, auth))

    @requires_pckttools()
    def stripLive(self, capturefile, outfile):
        """Capture relevant packets from a live capture-source

           Parse a packet-capture file given by the option -r, extract only
           packets that are necessary for EAPOL-handshake detection and write a
           new dump to the file given by the option -o. This command differs
           from strip as the capture-file can be any character device including
           sockets and other pseudo-files that look like files in pcap-format.
           stripLive writes relevant packets to the new file given by -o as
           they arrive instead of trying to read the entire capture-file first.

           For example:
           pyrit -r /temp/kismet_dump -o small_dump.pcap stripLive
        """

        writer = cpyrit.pckttools.Dot11PacketWriter(outfile)
        parser = cpyrit.pckttools.PacketParser()

        parser.new_ap_callback = \
            lambda ap: self._stripLive_newAP(parser, writer, ap)

        parser.new_station_callback = \
            lambda sta: self._stripLive_newStation(parser, writer, sta)

        parser.new_keypckt_callback = \
            lambda (sta, idx, pckt): \
                    self._stripLive_newKeyPckt(parser, writer, sta, idx, pckt)

        parser.new_encpckt_callback = \
            lambda (sta, pckt): \
                    self._stripLive_newEncPckt(parser, writer, sta, pckt)

        parser.new_auth_callback = \
            lambda (sta, auth): self._stripLive_newAuth(parser, writer, sta, \
                                                        auth)

        self.tell("Parsing packets from '%s'..." % capturefile)
        pckt_rdr = cpyrit.pckttools.PcapDevice(use_bpf=True)
        try:
            pckt_rdr.open_offline(capturefile)
        except IOError, offline_error:
            try:
                pckt_rdr.open_live(capturefile)
            except IOError, live_error:
                raise PyritRuntimeError("Failed to open '%s' either as a " \
                                        "file ('%s') or as a device " \
                                        "('%s')" % (capturefile, \
                                        str(offline_error), str(live_error)))
        try:
            parser.parse_pcapdevice(pckt_rdr)
        except (KeyboardInterrupt, SystemExit):
            self.tell("\nInterrupted...\n")
        else:
            self.tell("\nCapture-source was closed...\n")
        finally:
            writer.close()
        for i, ap in enumerate(parser):
            self.tell("#%i: AccessPoint %s ('%s')" % (i + 1, ap, ap.essid))
            for j, sta in enumerate(ap):
                auths = sta.getAuthentications()
                if len(auths) > 0:
                    self.tell("  #%i: Station %s, %i handshake(s)" % \
                                (j, sta, len(auths)))
                    for k, auth in enumerate(auths):
                        self.tell("    #%i: %s" % (k + 1, auth))
        self.tell("\nNew pcap-file '%s' written (%i out of %i packets)" % \
                    (outfile, writer.pcktcount, parser.pcktcount))
    stripLive.cli_options = (('-r', '-o'), ())

    def export_hashdb(self, storage, outfile, essid=None):
        """Export results to an airolib database

           Write all results currently stored in the database to the airolib-ng
           database given by -o. The database is created with a default table
           layout if the file does not yet exist. The option -e can be used to
           limit the export to a single ESSID.

           For example:
           pyrit -o NETGEAR.db -e NETGEAR export_hashdb
        """
        import sqlite3
        if essid is None:
            essids = storage.essids
        else:
            essids = [essid]
        con = sqlite3.connect(outfile)
        con.text_factory = str
        cur = con.cursor()
        cur.execute('SELECT * FROM sqlite_master')
        tbls = [x[1] for x in cur.fetchall() if x[0] == u'table']
        if u'pmk' not in tbls or u'essid' not in tbls or u'passwd' not in tbls:
            self.tell("The database '%s' seems to be uninitialized. " % \
                      outfile)
            self.tell("Trying to create default table-layout...", end=None)
            try:
                cur.execute("CREATE TABLE essid (" \
                            "essid_id INTEGER PRIMARY KEY AUTOINCREMENT," \
                            "essid TEXT," \
                            "prio INTEGER DEFAULT 64)")

                cur.execute("CREATE TABLE passwd (" \
                            "passwd_id INTEGER PRIMARY KEY AUTOINCREMENT, " \
                            "passwd TEXT)")

                cur.execute("CREATE TABLE pmk (" \
                            "pmk_id INTEGER PRIMARY KEY AUTOINCREMENT, " \
                            "passwd_id INTEGER, " \
                            "essid_id INTEGER, " \
                            "pmk BLOB)")

                cur.execute("CREATE TABLE workbench (" \
                            "wb_id INTEGER PRIMARY KEY AUTOINCREMENT, " \
                            "essid_id INTEGER, " \
                            "passwd_id INTEGER, " \
                            "lockid INTEGER DEFAULT 0)")

                cur.execute("CREATE INDEX lock_lockid ON workbench (lockid);")
                cur.execute("CREATE UNIQUE INDEX essid_u ON essid (essid)")
                cur.execute("CREATE UNIQUE INDEX passwd_u ON passwd (passwd)")
                cur.execute("CREATE UNIQUE INDEX ep_u ON pmk " \
                            "(essid_id, passwd_id)")

                cur.execute("CREATE UNIQUE INDEX wb_u ON workbench " \
                            "(essid_id, passwd_id)")

                cur.execute("CREATE TRIGGER delete_essid DELETE ON essid " \
                            "BEGIN DELETE FROM pmk " \
                            "WHERE pmk.essid_id = OLD.essid_id;" \
                            "DELETE FROM workbench " \
                            "WHERE workbench.essid_id = OLD.essid_id;" \
                            "END")

                cur.execute("CREATE TRIGGER delete_passwd DELETE ON passwd " \
                            "BEGIN DELETE FROM pmk " \
                            "WHERE pmk.passwd_id = OLD.passwd_id;" \
                            "DELETE FROM workbench " \
                            "WHERE workbench.passwd_id = OLD.passwd_id;" \
                            "END")

                self.tell("Tables created...")
            except:
                con.rollback()
                cur.close()
                con.close()
                self.tell("Failed to initialize the database.", \
                            stream=sys.stderr)
                raise
        try:
            cur.execute("PRAGMA synchronous = 1")
            i = 0
            self.tell("Writing passwords...")
            for pwset in storage.iterpasswords():
                i += len(pwset)
                cur.executemany("INSERT OR IGNORE INTO passwd " \
                                "(passwd) VALUES (?)", [(p, ) for p in pwset])
                self.tell("Wrote %i lines...\r" % i, end=None, sep=None)
            self.tell("\nWriting ESSIDs and results...")
            for cur_essid in essids:
                self.tell("Writing '%s'..." % cur_essid)
                cur.execute("INSERT OR IGNORE INTO essid " \
                            "(essid) VALUES (?)", (cur_essid, ))
                essid_id = cur.execute("SELECT essid_id FROM essid " \
                                        "WHERE essid = ?", \
                                            (cur_essid, )).fetchone()[0]
                i = 0
                for results in storage.iterresults(cur_essid):
                    i += len(results)
                    cur.executemany("INSERT OR IGNORE INTO pmk " \
                                    "(essid_id, passwd_id, pmk) " \
                                    "SELECT ?, passwd_id, ? FROM passwd " \
                                    "WHERE passwd = ?", \
                                        ((essid_id, buffer(pmk), pw) \
                                            for pw, pmk in results))
                    self.tell("Wrote %i lines...\r" % i, end=None, sep=None)
            self.tell("\nAll done.")
        except:
            con.rollback()
            self.tell("There was an error while exporting. The database has " \
                      "not been modified...", stream=sys.stderr)
            raise
        else:
            con.commit()
        finally:
            cur.close()
            con.close()
    export_hashdb.cli_options = (('-u', '-o', ), ('-e', ))

    def passthrough(self, essid, infile, outfile):
        """Compute PMKs and write results to a file

           Read passwords from the file given by -i and compute their PMKs for
           the ESSID given by -e. The results are written to the file specified
           by -o in cowpatty's binary format and are not stored in the database
           for later use. This command therefor circumvents the entire database
           and should only be used if storage-space is a problem (e.g. when
           using pyrit on a LiveCD). The batch-command provides exactly the
           same functionality as passthrough but can give much better
           performance as results may be read from the database instead of
           recomputing them.

           For example:
           pyrit -i words.txt -e NETGEAR -o NETGEAR.cow.gz passthrough
        """
        perfcounter = cpyrit.util.PerformanceCounter()
        with cpyrit.util.FileWrapper(infile) as reader:
            try:
                with cpyrit.util.AsyncFileWriter(outfile) as writer:
                    with cpyrit.util.CowpattyFile(writer, 'w', essid) as cowpwriter:
                        with cpyrit.cpyrit.PassthroughIterator(essid, reader) as rstiter:
                            for results in rstiter:
                                cowpwriter.write(results)
                                perfcounter += len(results)
                                self.tell("Computed %i PMKs so far; %i PMKs" \
                                          " per second\r" % \
                                          (perfcounter.total, \
                                           perfcounter.avg), \
                                          end=None, sep=None)
            except IOError:
                self.tell("IOError while writing to stdout ignored.", \
                            stream=sys.stderr)
            finally:
                self.tell("Computed %i PMKs total; %i PMKs per second" % \
                          (perfcounter.total, perfcounter.avg))
    passthrough.cli_options = (('-i', '-o', '-e'), ())

    def batchprocess(self, storage, essid=None, outfile=None):
        """Batchprocess the database

           Start to translate all passwords in the database into their
           respective PMKs and store the results in the database. The option -e
           may be used to restrict this command to a single ESSID; if it is
           ommitted, all ESSIDs are processed one after the other in undefined
           order.

           For example:
           pyrit -e NETGEAR batch

           The option -o can be used to specify a filename the results should
           additionally be written to in cowpatty's binary format. The option
           -e becomes mandatory and the ESSID is automatically created in the
           database if necessary. Pairwise Master Keys that previously have
           been computed and stored in the database are exported from there
           without further processing. Pyrit stops and exits if an IOError is
           raised while writing to the specified file but signals success on
           exit. This makes it very convenient to pipe results directly to
           other programs but also keep them for later use.

           For example:
           pyrit -e NETGEAR -o - batch | cowpatty -d - -r MyCap.cap -s NETGEAR
        """
        if outfile is not None and essid is None:
            raise PyritRuntimeError("Results will be written to a file " \
                                    "while batchprocessing. This requires " \
                                    "to specify a single ESSID.")
        if essid is not None:
            if essid not in storage.essids:
                storage.essids.create_essid(essid)
            essids = [essid]
        else:
            if len(storage.essids) == 0:
                raise PyritRuntimeError("No ESSID in storage. Use 'create_" \
                                        "essid' first.")
            essids = storage.unfinishedESSIDs()
        if outfile is not None:
            outfilewriter = cpyrit.util.AsyncFileWriter(outfile)
            cowpwriter = cpyrit.util.CowpattyFile(outfilewriter, 'w', essid)
        else:
            cowpwriter = None
        for cur_essid in essids:
            perfcounter = cpyrit.util.PerformanceCounter()
            self.tell("Working on ESSID '%s'" % cur_essid)
            with cpyrit.cpyrit.StorageIterator(storage, cur_essid, \
                        yieldOldResults=cowpwriter is not None) as dbiterator:
                totalKeys = len(dbiterator)
                for results in dbiterator:
                    perfcounter += len(results)
                    if cowpwriter is not None:
                        try:
                            cowpwriter.write(results)
                        except IOError:
                            self.tell("IOError while batchprocessing...")
                            raise SystemExit
                    solvedKeys = dbiterator.keycount()
                    self.tell("Processed %i/%i workunits so far (%.1f%%); " \
                              "%i PMKs per second.\r" % (solvedKeys, \
                                totalKeys, \
                                100.0 * solvedKeys / totalKeys, \
                                perfcounter.avg), \
                              end=None, sep=None)
            self.tell("Processed all workunits for ESSID '%s'; " \
                      "%i PMKs per second." % \
                      (cur_essid, perfcounter.avg))
            self.tell('')
        if cowpwriter is not None:
            cowpwriter.close()
        self.tell("Batchprocessing done.")
    batchprocess.cli_options = (('-u', ), ('-e', '-o'))

    def relay(self, storage):
        """Relay a storage-url via RPC

           Start a server to relay another storage device via XML-RPC; other
           pyrit-clients can use the server as storage-device. This allows to
           have network-based access to storage source that don’t provide
           network-access on their own (like file:// and sqlite://) or hide a
           SQL-database behind a firewall and let multiple clients access that
           database only via Pyrit’s RPC-interface. The TCP-port 17934 must be
           open for this function to work.

           For example, on the server (where the database is):
           pyrit -u sqlite:////var/local/pyrit.db relay

          ... and the client (where the big GPU is):
          pyrit -u http://192.168.0.100:17934 batch
        """
        with cpyrit.storage.StorageRelay(storage) as rpcd:
            self.tell("Server started...")
            try:
                rpcd.serve_forever()
            except (KeyboardInterrupt, SystemExit):
                pass
        self.tell("Server closed")
    relay.cli_options = (('-u', ), ())

    def serve(self):
        """Serve local hardware to other Pyrit clients

           Start a server that provides access to the local computing hardware
           to help other Pyrit-clients. The server's IP-address should be added
           to the clients' configuration file (usually '~/.pyrit/config') as a
           space-separated list under known_clients. These clients'
           rpc_server-setting must also be set to 'true'. The TCP- and UDP-port
           17935 must be accessible.

           For example, on the server (where the GPU is):
           pyrit serve

           ... and the clients (the server's IP-address has been added to
           'known_clients' and rpc_server is set to 'true'):
            pyrit -r tst.pcap -b 00:de:ad:be:ef:00 -i words attack_passthrough
        """
        server = cpyrit.network.NetworkServer()
        listener = cpyrit.network.NetworkAnnouncementListener()
        perfcounter = cpyrit.util.PerformanceCounter()
        try:
            while server.isAlive():
                addr = listener.waitForAnnouncement(block=True, timeout=1.0)
                if addr is not None and addr not in server:
                    server.addClient(addr)
                perfcounter.addAbsolutePoint(server.stat_scattered)
                if perfcounter.avg > 0:
                    y = (server.stat_gathered - server.stat_enqueued) \
                        / perfcounter.avg
                else:
                    y = 0
                self.tell("\rServing %i active clients; %i PMKs/s; " \
                          "%.1f TTS" % (len(server), perfcounter.avg, y), \
                          end=None)
        except (KeyboardInterrupt, SystemExit):
            self.tell("\nShutdown with %i active clients..." % len(server))
            listener.shutdown()
            server.shutdown()
    serve.cli_options = ((), ())

    @requires_pckttools()
    def attack_passthrough(self, infile, capturefile, essid=None, \
                           bssid=None, outfile=None, all_handshakes=False, \
                           use_aes=False):
        """Attack a handshake with passwords from a file

           Attack an EAPOL-handshake found in the packet-capture file given by
           the option -r using the passwords read from the file given by the
           option -i. The options -b  and -e can be used to specify the
           Access-Point to attack; it is picked automatically if both options
           are omitted. The password is written to the filename given by the
           option -o  if specified.

           For example:
           pyrit -r test.pcap -b 00:de:ad:be:ef:00 -i words attack_passthrough

           This command circumvents Pyrit's database and should only be used
           if storage-space is a problem (e.g. on LiveCDs). You should consider
           using attack_batch otherwise.
        """
        ap = self._fuzzyGetAP(self._getParser(capturefile), bssid, essid)
        if not ap.isCompleted():
            raise PyritRuntimeError("No valid handshakes for AccessPoint %s " \
                                    "found in the capture file." % ap)
        if essid is None:
            essid = ap.essid
        perfcounter = cpyrit.util.PerformanceCounter()
        auths = ap.getCompletedAuthentications()
        crackers = []
        if not all_handshakes:
            crackers.append(cpyrit.pckttools.AuthCracker(auths[0], use_aes))
        else:
            self.tell("Attacking %i handshake(s)." % (len(auths),))
            for auth in auths:
                crackers.append(cpyrit.pckttools.AuthCracker(auth, use_aes))
        with cpyrit.util.FileWrapper(infile) as reader:
            with cpyrit.cpyrit.PassthroughIterator(essid, reader) as rstiter:
                for results in rstiter:
                    for cracker in crackers:
                        cracker.enqueue(results)
                    perfcounter += len(results)
                    self.tell("Tried %i PMKs so far; %i PMKs per second; %s\r" % \
                                (perfcounter.total, perfcounter.avg, results[0][0]),
                              end=None, sep=None)
                    if any(c.solution is not None for c in crackers):
                        break
        self.tell("Tried %i PMKs so far; %i PMKs per second." % \
                    (perfcounter.total, perfcounter.avg))
        for cracker in crackers:
            cracker.join()
            if cracker.solution is not None:
                self.tell("\nThe password is '%s'.\n" % cracker.solution)
                if outfile is not None:
                    with cpyrit.util.FileWrapper(outfile, 'w') as writer:
                        writer.write(cracker.solution)
                break
        else:
            errmsg = "\nPassword was not found."
            if len(auths) > 1 and all_handshakes is False:
                errmsg += " Retry the attack with '--all-handshakes'.\n"
            else:
                errmsg += "\n"
            raise PyritRuntimeError(errmsg)
    attack_passthrough.cli_options = (('-i', '-r'), ('-e', '-b', '-o', \
                                                     '--all-handshakes', \
                                                     '--aes'))

    @requires_pckttools()
    def attack_batch(self, storage, capturefile, essid=None, bssid=None, \
                    outfile=None, all_handshakes=False, use_aes=False):
        """Attack a handshake with PMKs/passwords from the db

            Attack an EAPOL-handshake found in the packet-capture file(s) given
            by the option -r using the Pairwise Master Keys and passwords
            stored in the database. The options -b  and -e can be used to
            specify the Access-Point to attack; it is picked automatically if
            both options are omitted. The password is written to the filename
            given by the option -o  if specified.

            For example:
            pyrit -r test.pcap -b 00:de:ad:c0:de:00 -o passwd.txt attack_batch

            Pairwise Master Keys that have been computed and stored in the
            database previously are taken from there; all other passwords are
            translated into their respective Pairwise Master Keys and added to
            the database for later re-use. ESSIDs are created automatically in
            the database if necessary.
        """
        ap = self._fuzzyGetAP(self._getParser(capturefile), bssid, essid)
        if not ap.isCompleted():
            raise PyritRuntimeError("No valid handshakes for AccessPoint %s " \
                                    "found in the capture file." % ap)
        if essid is None:
            essid = ap.essid
        if essid not in storage.essids:
            storage.essids.create_essid(essid)
        perfcounter = cpyrit.util.PerformanceCounter()
        auths = ap.getCompletedAuthentications()
        if all_handshakes:
            self.tell("Attacking %i handshake(s)." % (len(auths),))
        for auth in auths if all_handshakes else auths[:1]:
            with cpyrit.pckttools.AuthCracker(auth, use_aes) as cracker:
                with cpyrit.cpyrit.StorageIterator(storage, essid) as dbiter:
                    self.tell("Attacking handshake with " \
                              "station %s" % (auth.station,))
                    for idx, results in enumerate(dbiter, start=1):
                        cracker.enqueue(results)
                        perfcounter += len(results)
                        self.tell("Tried %i PMKs so far (%.1f%%); " \
                                  "%i PMKs per second.\r" % (perfcounter.total,
                                    100.0 * idx / len(storage.passwords),
                                    perfcounter.avg),
                                  end=None, sep=None)
                        if cracker.solution:
                            break
                    self.tell('')
            if cracker.solution is not None:
                self.tell("\nThe password is '%s'.\n" % cracker.solution)
                if outfile is not None:
                    with cpyrit.util.FileWrapper(outfile, 'w') as writer:
                        writer.write(cracker.solution)
                break
        else:
            errmsg = "\nPassword was not found."
            if len(auths) > 1 and all_handshakes is False:
                errmsg += " Retry the attack with '--all-handshakes'.\n"
            else:
                errmsg += "\n"
            raise PyritRuntimeError(errmsg)
    attack_batch.cli_options = (('-r', '-u'), ('-e', '-b', '-o', \
                                               '--all-handshakes', '--aes'))

    @requires_pckttools()
    def attack_db(self, storage, capturefile, essid=None, bssid=None, \
                  outfile=None, all_handshakes=False, use_aes=False):
        """Attack a handshake with PMKs from the db

           Attack an EAPOL-handshake found in the packet-capture file(s) given
           by the option -r using the Pairwise Master Keys stored in the
           database. The options -b and -e  can be used to specify the
           Access-Point to attack; it is picked automatically if both options
           are omitted. The password is written to the filename given by the
           option -o if specified.

           For example:
           pyrit -r test.pcap -e MyOtherNetwork attack_db

           Only Pairwise Master Keys that have been computed previously and
           are stored in the database are used by attack_db.
        """
        ap = self._fuzzyGetAP(self._getParser(capturefile), bssid, essid)
        if not ap.isCompleted():
            raise PyritRuntimeError("No valid handshakes for AccessPoint " \
                                    "%s found in the capture file." % ap)
        if essid is None:
            essid = ap.essid
        if essid not in storage.essids:
            raise PyritRuntimeError("The ESSID '%s' can't be found in the " \
                                    "database." % essid)
        WUcount = storage.essids.keycount(essid)
        perfcounter = cpyrit.util.PerformanceCounter()
        auths = ap.getCompletedAuthentications()
        if all_handshakes:
            self.tell("Attacking %i handshake(s)." % (len(auths),))
        for auth in auths if all_handshakes else auths[:1]:
            with cpyrit.pckttools.AuthCracker(auth, use_aes) as cracker:
                self.tell("Attacking handshake with " \
                          "Station %s..." % auth.station)
                for idx, results in enumerate(cpyrit.cpyrit.StorageIterator(
                                                storage, essid,
                                                yieldNewResults=False), start=1):
                    cracker.enqueue(results)
                    perfcounter += len(results)
                    self.tell("Tried %i PMKs so far (%.1f%%); " \
                              "%i PMKs per second.\r" % (perfcounter.total,
                                100.0 * idx / WUcount,
                                perfcounter.avg),
                              end=None, sep=None)
                    if cracker.solution is not None:
                        break
                self.tell('')
            if cracker.solution is not None:
                self.tell("\nThe password is '%s'.\n" % cracker.solution)
                if outfile is not None:
                    with cpyrit.util.FileWrapper(outfile, 'w') as writer:
                        writer.write(cracker.solution)
                break
        else:
            errmsg = "\nPassword was not found."
            if len(auths) > 1 and all_handshakes is False:
                errmsg += " Retry the attack with '--all-handshakes'.\n"
            else:
                errmsg += "\n"
            raise PyritRuntimeError(errmsg)
    attack_db.cli_options = (('-r', '-u'), ('-e', '-b', '-o', \
                                            '--all-handshakes', '--aes'))

    @requires_pckttools()
    def attack_cowpatty(self, capturefile, infile, essid=None, bssid=None,\
                        outfile=None, all_handshakes=False, use_aes=False):
        """Attack a handshake with PMKs from a cowpatty-file

           Attack an EAPOL-handshake found in the packet-capture file(s) given
           by the option -r using Pairwise Master Keys from a cowpatty-like
           file (e.g. generated by genpmk/export_cowpatty) given by the option
           -i. The options -b and -e can be used to specify the Access-Point to
           attack; it is picked automatically if both options are omitted.
           The password is written to the filename given by the option -o if
           specified. The cowpatty-file may be gzip-compressed and must match
           the chosen ESSID.

           For example:
           pyrit -r MyESSID.pcap -e MyESSID -i MyESSID.cow.gz attack_cowpatty

           Pyrit's own database is not touched by attack_cowpatty
        """
        with cpyrit.util.CowpattyFile(infile) as cowreader:
            if essid is None:
                essid = cowreader.essid
            ap = self._fuzzyGetAP(self._getParser(capturefile), bssid, essid)
            if not ap.isCompleted():
                raise PyritRuntimeError("No valid handshakes for " \
                                        "AccessPoint %s found in the " \
                                        "capture file." % ap)
            if essid is None:
                essid = ap.essid
            if essid != cowreader.essid:
                raise PyritRuntimeError("Chosen ESSID '%s' and file's ESSID " \
                                        "'%s' do not match" % \
                                        (essid, cowreader.essid))
            perfcounter = cpyrit.util.PerformanceCounter()
            auths = ap.getCompletedAuthentications()
            crackers = []
            if not all_handshakes:
                crackers.append(cpyrit.pckttools.AuthCracker(auths[0], use_aes))
            else:
                self.tell("Attacking %i handshake(s)." % (len(auths),))
                for auth in auths:
                    crackers.append(cpyrit.pckttools.AuthCracker(auth, use_aes))
            for results in cowreader:
                for cracker in crackers:
                    cracker.enqueue(results)
                perfcounter.addAbsolutePoint(len(crackers[0]))
                self.tell("Tried %i PMKs so far; %i PMKs per second.\r" % \
                          (perfcounter.total, perfcounter.avg),
                          end=None, sep=None)
                if any(cracker.solution is not None for cracker in crackers):
                    break
            crackers[0].join()
            perfcounter.addAbsolutePoint(len(crackers[0]))
            self.tell("Tried %i PMKs so far; %i PMKs per second." % \
                      (perfcounter.total, perfcounter.avg))
            for cracker in crackers:
                cracker.join()
                if cracker.solution is not None:
                    self.tell("\nThe password is '%s'.\n" % cracker.solution)
                    if outfile is not None:
                        with cpyrit.util.FileWrapper(outfile, 'w') as writer:
                            writer.write(cracker.solution)
                    break
            else:
                errmsg = "\nPassword was not found."
                if len(auths) > 1 and all_handshakes is False:
                    errmsg += " Retry the attack with '--all-handshakes'.\n"
                else:
                    errmsg += "\n"
                raise PyritRuntimeError(errmsg)
    attack_cowpatty.cli_options = (('-r', '-i'), ('-e', '-b', '-o', \
                                                  '--all-handshakes', '--aes'))

    def benchmark(self, timeout=45, calibrate=10):
        """Determine performance of available cores

           Determine the peak-performance of the available hardware by
           computing dummy-results.

           For example:
           pyrit benchmark
        """
        with cpyrit.cpyrit.CPyrit() as cp:
            # 'Burn-in' so that all modules are forced to load and buffers can
            # calibrate to optimal size
            self.tell("Calibrating...", end=None)
            t = time.time()
            while time.time() - t < calibrate:
                cp.enqueue('foo', ['barbarbar'] * 500)
                cp.dequeue(block=False)
            for r in cp:
                pass
            # Minimize scheduling overhead...
            bsize = max(min(int(cp.getPeakPerformance()), 50000), 500)
            cp.resetStatistics()
            cycler = itertools.cycle(('\\|/-'))
            t = time.time()
            perfcounter = cpyrit.util.PerformanceCounter(timeout + 5)
            while time.time() - t < timeout:
                pws = ["barbarbar%s" % random.random() for i in xrange(bsize)]
                cp.enqueue('foo', pws)
                r = cp.dequeue(block=False)
                if r is not None:
                    perfcounter += len(r)
                self.tell("\rRunning benchmark (%.1f PMKs/s)... %s" % \
                        (perfcounter.avg, cycler.next()), end=None)
            self.tell('')
            self.tell("\nComputed %.2f PMKs/s total." % perfcounter.avg)
            for i, core in enumerate(cp.cores):
                if core.compTime > 0:
                    perf = core.resCount / core.compTime
                else:
                    perf = 0
                if core.callCount > 0 and perf > 0:
                    rtt = (core.resCount / core.callCount) / perf
                else:
                    rtt = 0
                self.tell("#%i: '%s': %.1f PMKs/s (RTT %.1f)" % \
                            (i + 1, core.name, perf, rtt))
            if cpyrit.config.cfg['use_CUDA'] == 'true':
                    self.tell("CUDA:")
            for i, CD in enumerate(cp.CUDAs):

                if CD.compTime > 0:
                    perf = CD.resCount / CD.compTime
                else:
                    perf = 0
                if CD.callCount > 0 and perf > 0:
                    rtt = (CD.resCount / CD.callCount) / perf
                else:
                    rtt = 0
                self.tell("#%i: '%s': %.1f PMKs/s (RTT %.1f)" % \
                          (i + 1, CD.name, perf, rtt))
            if cpyrit.config.cfg['use_OpenCL'] == 'true':
                self.tell("OpenCL:")
            for i, OCL in enumerate(cp.OpCL):

                if OCL.compTime > 0:
                    perf = OCL.resCount / OCL.compTime
                else:
                    perf = 0
                if OCL.callCount > 0 and perf > 0:
                    rtt = (OCL.resCount / OCL.callCount) / perf
                else:
                    rtt = 0
                self.tell("#%i: '%s': %.1f PMKs/s (RTT %.1f)" % \
                          (i + 1, OCL.name, perf, rtt))

            for r in cp:
                pass
    benchmark.cli_options = ((), ())

    def benchmark_long(self):
        """Longer and more accurate version of benchmark (5 minutes)"""
        self.benchmark(300, 30)
    benchmark_long.cli_options = ((), ())

    def selftest(self, timeout=60):
        """Test hardware to ensure it computes correct results

           Run an extensive selftest for about 60 seconds. This test includes
           the entire scheduling-mechanism and all cores that are listed by
           list_cores. You can use this function to detect broken
           hardware-modules or malicious network-clients.

           For example:
           pyrit selftest
        """
        with cpyrit.cpyrit.CPyrit() as cp:
            self.tell("Cores incorporated in the test:\nCPUs:")
            for i, core in enumerate(cp.cores):
                self.tell("#%i:  '%s'" % (i + 1, core))
            self.tell("GPUs:")
            for i, CD in enumerate(cp.CUDAs):
                self.tell("#%i:  '%s'" % (i + 1, CD))
            for i, OCL in enumerate(cp.OpCL):
                self.tell("#%i:  '%s'" % (i + 1, OCL))

            self.tell("\nRunning selftest...")
            workunits = []
            t = time.time()
            err = False
            while time.time() - t < timeout and not err:
                essid = random.choice(cpyrit.util.PMK_TESTVECTORS.keys())
                pws = []
                ref = cpyrit.util.PMK_TESTVECTORS[essid].keys()
                for i in xrange(random.randrange(10, 1000)):
                    pws.append(random.choice(ref))
                workunits.append((essid, pws))
                cp.enqueue(essid, pws)
                while True:
                    solvedPMKs = cp.dequeue(block=False)
                    if solvedPMKs is not None:
                        essid, pws = workunits.pop(0)
                        for i, pw in enumerate(pws):
                            ref = cpyrit.util.PMK_TESTVECTORS[essid][pw]
                            if ref != solvedPMKs[i]:
                                err = True
                                break
                    if err or not solvedPMKs:
                        break
            if not err:
                for solvedPMKs in cp:
                    essid, pws = workunits.pop(0)
                    for i, pw in enumerate(pws):
                        ref = cpyrit.util.PMK_TESTVECTORS[essid][pw]
                        if ref != solvedPMKs[i]:
                            err = True
                            break
            if err or len(workunits) != 0 or len(cp) != 0:
                raise PyritRuntimeError("\n!!! WARNING !!!\nAt least some " \
                                        "results seem to be invalid. This " \
                                        "may be caused by a bug in Pyrit, " \
                                        "faulty hardware or malicious " \
                                        "network clients. Do not trust " \
                                        "this installation...\n")
            else:
                self.tell("\nAll results verified. Your installation seems OK")
    selftest.cli_options = ((), ())

    def verify(self, storage, essid=None):
        """Verify 10% of the results by recomputation

           Randomly pick 10% of the results stored in the database and verify
           their value by recomputation. You need this function if you suspect
           broken hardware or malicious network-clients.

           For example:
           pyrit -e NETGEAR verify
        """
        with cpyrit.cpyrit.CPyrit() as cp:
            if essid is not None:
                if essid not in storage.essids:
                    raise PyritRuntimeError("The ESSID '%s' is not found in " \
                                            "the repository" % (essid,))
                else:
                    essids = [essid]
            else:
                essids = storage.essids
            err = False
            perfcounter = cpyrit.util.PerformanceCounter()
            workunits = []
            for essid in essids:
                self.tell("Verifying ESSID '%s'" % essid)
                for key, results in storage.essids.iteritems(essid):
                    sample = random.sample(results, int(len(results) * 0.1))
                    if len(sample) > 0:
                        pws, pmks = zip(*sample)
                        workunits.append((essid, key, tuple(pmks)))
                        cp.enqueue(essid, pws)
                        solvedPMKs = cp.dequeue(block=False)
                        if solvedPMKs is not None:
                            perfcounter += len(solvedPMKs)
                            testedEssid, testedKey, testedPMKs = \
                                workunits.pop(0)
                            if testedPMKs != solvedPMKs:
                                self.tell("Workunit %s for ESSID '%s' is " \
                                          "corrupt." % (testedKey, \
                                                        testedEssid), \
                                          stream=sys.stderr)
                                err = True
                    self.tell("Computed %i PMKs so far; %i PMKs per " \
                              "second.\r" % (perfcounter.total, \
                                             perfcounter.avg), \
                              end=None, sep=None)
                for solvedPMKs in cp:
                    perfcounter += len(solvedPMKs)
                    testedEssid, testedKey, testedPMKs = workunits.pop(0)
                    if testedPMKs != solvedPMKs:
                        self.tell("Workunit %s for ESSID '%s' is corrupt." % \
                                (testedKey, testedEssid), stream=sys.stderr)
                        err = True
        self.tell("\nVerified %i PMKs with %i PMKs/s." % \
                    (perfcounter.total, perfcounter.avg))
        if err:
            raise PyritRuntimeError(
                    "\nAt least one workunit-file contains invalid results." \
                    " There are two options now:\n" \
                    "* The results on the disk are corrupted or invalid. " \
                    "You should mistrust the entire repository but at least " \
                    "delete and recompute the offending ESSIDs.\n" \
                    "* The result on the disk are correct but your " \
                    "installation is broken and currently computes invalid " \
                    "results.\nRun 'selftest' for an extensive self-test " \
                    "in order to tell the two options apart.")
        else:
            self.tell("Everything seems OK.")
    verify.cli_options = (('-u', ), ('-e', ))

    def checkdb(self, storage, confirm=True):
        """Check the database for errors

           Unpack the entire database and check for errors. This function
           does not check the value of computed results (see verify).

           For example:
           pyrit check_db
        """

        # Check passwords
        self.tell("Checking workunits...")
        wu_errors = set()
        for key in storage.passwords.iterkeys():
            try:
                # explicit call to iter to work around swallowed
                # exceptions in CPython's bltinmodule.c:map_new()
                for l in map(len, iter(storage.passwords[key])):
                    if l < 8 or l > 64:
                        raise cpyrit.storage.StorageError("Invalid password")
            except cpyrit.storage.StorageError, e:
                self.tell("Error in workunit %s: %s" % (key, e), \
                          stream=sys.stderr)
                wu_errors.add(key)
        # Check results
        res_errors = set()
        for essid in storage.essids:
            self.tell("Checking results for ESSID '%s'..." % (essid,))
            for key in storage.essids.iterkeys(essid):
                try:
                    if key not in storage.passwords:
                        # A resultset exists that is not referenced by workunit
                        raise cpyrit.storage.StorageError("Reference error")
                    # Some errors are catched here
                    res = storage.essids[essid, key]
                    # Check entries
                    for pw, pmk in res:
                        pwlen = len(pw)
                        if pwlen < 8 or pwlen > 64:
                            raise cpyrit.storage.StorageError("Invalid " \
                                                              "password")
                        if len(pmk) != 32:
                            raise cpyrit.storage.StorageError("Invalid PMK")
                    if key not in wu_errors:
                        # Check that workunit and results match
                        wu = frozenset(storage.passwords[key])
                        for pw, pmk in res:
                            if pw not in wu:
                                raise cpyrit.storage.StorageError("Password " \
                                                              "not in workunit")
                        res_passwords = dict(res)
                        for pw in wu:
                            if pw not in res_passwords:
                                raise cpyrit.storage.StorageError("Password " \
                                                             "not in resultset")
                except cpyrit.storage.StorageError, e:
                    self.tell("Error in results %s for ESSID '%s':" \
                              " %s" % (key, essid, e), stream=sys.stderr)
                    if key not in wu_errors:
                        res_errors.add((essid, key))

        if len(wu_errors) + len(res_errors) > 0:
            self.tell("\nThere have been %i errors in workunits and %i errors"\
                      " in resultsets. Your option now is to delete these" \
                      " entries from the database. Workunits are lost" \
                      " forever, resultsets can be recomputed." % \
                      (len(wu_errors), len(res_errors)), end=None)
            if confirm:
                self.tell(" Continue? [y/N]", end=None)
                if sys.stdin.readline().strip() != 'y':
                    raise PyritRuntimeError("aborted.")

            self.tell("deleting...")
            # Delete workunits including results
            for key in wu_errors:
                del storage[key]
            # Delete results
            for essid, key in res_errors:
                del storage.essids[essid, key]

            raise PyritRuntimeError("Errors were reported and fixed. You may" \
                                    " run 'checkdb' again to make sure" \
                                    " that everything is working now.")
        else:
            self.tell("Everything seems OK.")

    checkdb.cli_options = (('-u',), ())

    commands = {'analyze': analyze,
                'attack_batch': attack_batch,
                'attack_cowpatty': attack_cowpatty,
                'attack_db': attack_db,
                'attack_passthrough': attack_passthrough,
                'batch': batchprocess,
                'benchmark': benchmark,
                'benchmark_long': benchmark_long,
                'check_db': checkdb,
                'create_essid': create_essid,
                'delete_essid': delete_essid,
                'eval': eval_results,
                'export_cowpatty': export_cowpatty,
                'export_hashdb': export_hashdb,
                'export_passwords': export_passwords,
                'help': print_help,
                'import_passwords': import_passwords,
                'import_unique_passwords': import_unique_passwords,
                'list_cores': list_cores,
                'list_essids': list_essids,
                'passthrough': passthrough,
                'relay': relay,
                'selftest': selftest,
                'serve': serve,
                'strip': stripCapture,
                'stripLive': stripLive,
                'verify': verify}
