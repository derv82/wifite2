#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..config import Configuration
from ..util.color import Color
from ..util.process import Process
from ..tools.hashcat import HcxPcapTool

import os


class John(Dependency):
    ''' Wrapper for John program. '''
    dependency_required = False
    dependency_name = 'john'
    dependency_url = 'http://www.openwall.com/john/'


    @staticmethod
    def crack_handshake(handshake, show_command=False):
        john_file = HcxPcapTool.generate_john_file(handshake, show_command=show_command)

        # Crack john file
        command = [
            'john',
            '--format=wpapsk', # wpapsk-cuda or wpapsk-opencl
            '--wordlist', Configuration.wordlist,
            john_file
        ]
        if show_command:
            Color.pl('{+} {D}{C}Running %s{W}' % ' '.join(command))
        process = Process(command)
        process.wait()

        # Show the password (if found)
        command = ['john', '--show', john_file]
        if show_command:
            Color.pl('{+} {D}{C}Running %s{W}' % ' '.join(command))
        process = Process(command)
        stdout, stderr = process.get_output()

        key = None
        if not '0 password hashes cracked' in stdout:
            for line in stdout.split('\n'):
                if handshake.capfile in line:
                    key = line.split(':')[1]
                    break

        if os.path.exists(john_file):
            os.remove(john_file)

        return key
