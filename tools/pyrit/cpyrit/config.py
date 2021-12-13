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

import os
import sys


def default_config():
    config = {'default_storage': 'file://',
              'use_CUDA': 'false',
              'use_OpenCL': 'false',
              'rpc_server': 'false',
              'rpc_announce': 'true',
              'rpc_announce_broadcast': 'false',
              'rpc_knownclients': '',
              'workunit_size': '75000',
              'limit_ncpus': 0}
    return config


def read_configfile(filename):
    config = default_config()
    with open(filename, 'rb') as f:
        for line in f:
            if line.startswith('#') or '=' not in line:
                continue
            option, value = map(str.strip, line.split('=', 1))
            if option in config:
                config[option] = value
            else:
                print >> sys.stderr, "WARNING: Unknown option '%s' " \
                                    "in configfile '%s'" % (option, filename)
    return config


def write_configfile(config, filename):
    with open(filename, 'wb') as f:
        for option, value in sorted(config.items()):
            f.write("%s = %s\n" % (option, value))


configpath = os.path.expanduser(os.path.join('~', '.pyrit'))
default_configfile = os.path.join(configpath, 'config')

if os.path.exists(default_configfile):
    cfg = read_configfile(default_configfile)
else:
    cfg = default_config()
    if not os.path.exists(configpath):
        os.makedirs(configpath)
    write_configfile(cfg, default_configfile)
