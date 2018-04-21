#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import re

from .dependency import Dependency

class Iptables(Dependency):
    process_name = 'iptables'

    dependency_required = False
    dependency_name = process_name
    dependency_url = 'apt-get install iptables'

    @classmethod
    def exists(cls):
        return Process.exists(cls.process_name)


    @classmethod
    def __exec(cls, args, expect_return_code=0):
        if type(args) is str:
            args = args.split(' ')

        command = [cls.process_name] + args

        pid = Process(command)
        pid.wait()
        if expect_return_code and pid.poll() != 0:
            raise Exception('Error executing %s:\n%s\n%s' % (' '.join(command), pid.stdout(), pid.stderr()))


    @classmethod
    def new_chain(cls, chain_name, table):
        command = ['-N', name, '-t', table]
        cls.__exec(command)


    @classmethod
    def append(cls, chain, table=None, rules=[]):
        args = []
        if table is not None:
            args.extend(['-t', table])
        args.extend(['-A', chain])
        args.extend(rules)
        cls.__exec(args)

