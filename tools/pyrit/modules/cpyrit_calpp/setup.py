#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    Copyright 2008-2011, Lukas Lueg, lukas.lueg@gmail.com
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

from distutils.core import setup, Extension
from distutils.command.build_ext import build_ext
from distutils.command.clean import clean
import os
import re
import subprocess
import sys

VERSION = '0.5.0'


CALPP_INC_DIRS = []

try:
    CALPP_INC_DIR = os.environ['ATISTREAMSDKROOT']
except KeyError:
    print >>sys.stderr, "unavailable enviroment variable ATISTREAMSDKROOT"
    raise
else:
    if os.path.exists(CALPP_INC_DIR):
        CALPP_INC_DIRS.append(os.path.join(CALPP_INC_DIR, 'include'))
    else:
        print >>sys.stderr, "The headers required to build CAL++ kernel" \
                            "were not found. Trying to continue anyway..."


EXTRA_COMPILE_ARGS = ['-Wall', '-fno-strict-aliasing', \
                      '-DVERSION="%s"' % (VERSION,)]


class GPUBuilder(build_ext):
    def run(self):
        print "Building modules..."
        build_ext.run(self)


class GPUCleaner(clean):

    def _unlink(self, node):
        try:
            if os.path.isdir(node):
                os.rmdir(node)
            else:
                os.unlink(node)
        except OSError:
            pass

    def run(self):
        print "Removing temporary files and pre-built GPU-kernels..."
        clean.run(self)


calpp_extension = Extension('cpyrit._cpyrit_calpp',
                    libraries = ['crypto', 'aticalrt', 'aticalcl'],
                    sources = ['_cpyrit_calpp.cpp', '_cpyrit_calpp_kernel.cpp'],
                    include_dirs = CALPP_INC_DIRS,
                    extra_compile_args = EXTRA_COMPILE_ARGS)

setup_args = dict(
        name = 'cpyrit-calpp',
        version = VERSION,
        description = 'GPU-accelerated attack against WPA-PSK authentication',
        long_description = \
            "Pyrit allows to create massive databases, pre-computing part " \
            "of the WPA/WPA2-PSK authentication phase in a space-time-" \
            "tradeoff. Exploiting the computational power of Many-Core- " \
            "and other platforms through ATI-Stream, Nvidia CUDA, OpenCL " \
            "and VIA Padlock, it is currently by far the most powerful " \
            "attack against one of the world's most used security-protocols.",
        license = 'GNU General Public License v3',
        author = 'Lukas Lueg, Artur Kornacki',
        author_email = 'lukas.lueg@gmail.com',
        url = 'https://github.com/JPaulMora/Pyrit',
        maintainer = 'John Mora',
        maintainer_email = 'johmora12@engineer.com',
        classifiers = \
              ['Development Status :: 4 - Beta',
               'Environment :: Console',
               'License :: OSI Approved :: GNU General Public License (GPL)',
               'Natural Language :: English',
               'Operating System :: OS Independent',
               'Programming Language :: Python',
               'Topic :: Security'],
        platforms = ['any'],
        ext_modules = [calpp_extension],
        cmdclass = {'build_ext': GPUBuilder, 'clean': GPUCleaner},
        options = {'install': {'optimize': 1}, \
                    'bdist_rpm': {'requires': 'pyrit = 0.4.0-1'}})

if __name__ == "__main__":
    setup(**setup_args)
