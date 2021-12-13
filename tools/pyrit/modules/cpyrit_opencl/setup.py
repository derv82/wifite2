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

from __future__ import with_statement
from distutils.core import setup, Extension
from distutils.command.build_ext import build_ext
from distutils.command.clean import clean
import os
import re
import subprocess
import sys
import zlib

VERSION = '0.5.0'

OPENCL_INC_DIRS = []
OPENCL_LIB_DIRS = []
EXTRA_LINK_ARGS = []
LIBRARIES = ['crypto', 'z']
if sys.platform == 'darwin':
    # Use the built-in framework on MacOS
    EXTRA_LINK_ARGS.extend(('-framework', 'OpenCL'))
    OPENCL_INC_DIRS.append('/System/Library/Frameworks/OpenCL.framework/Headers')
else:
    LIBRARIES.append('OpenCL')
    try:
        if os.path.exists(os.environ['ATISTREAMSDKROOT']):
            OPENCL_INC_DIRS.append(os.path.join(os.environ['ATISTREAMSDKROOT'], 'include'))
            for path in ('lib/x86_64','lib/x86'):
                if os.path.exists(os.path.join(os.environ['ATISTREAMSDKROOT'], path)):
                    OPENCL_LIB_DIRS.append(os.path.join(os.environ['ATISTREAMSDKROOT'], path))
                    break
    except:
        pass
    for path in ('/usr/local/opencl/OpenCL/common/inc', \
                '/opt/opencl/OpenCL/common/inc', \
                '/usr/local/opencl/include', \
                '/usr/local/cuda/include'):
        if os.path.exists(path):
            OPENCL_INC_DIRS.append(path)
            break
    else:
        print >>sys.stderr, "The headers required to build the OpenCL-kernel " \
                            "were not found. Trying to continue anyway..."


EXTRA_COMPILE_ARGS = ['-Wall', '-fno-strict-aliasing', \
                      '-DVERSION="%s"' % (VERSION,)]


class GPUBuilder(build_ext):
    def run(self):
        with open("_cpyrit_opencl.h", 'rb') as f:
            header = f.read()
        with open("_cpyrit_oclkernel.cl", 'rb') as f:
            kernel = f.read()
        oclkernel_code = header + '\n' + kernel + '\x00'
        oclkernel_inc = zlib.compress(oclkernel_code)
        with open("_cpyrit_oclkernel.cl.h", 'wb') as f:
            f.write("unsigned char oclkernel_packedprogram[] = {")
            f.write(",".join(("0x%02X" % ord(c) for c in oclkernel_inc)))
            f.write("};\nsize_t oclkernel_size = %i;\n" % len(oclkernel_code))
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
        try:
            for f in ('_cpyrit_oclkernel.cl.h',):
                self._unlink(f)
        except Exception, (errno, sterrno):
            print >>sys.stderr, "Exception while cleaning temporary " \
                                "files ('%s')" % sterrno
        clean.run(self)


opencl_extension = Extension('cpyrit._cpyrit_opencl',
                    libraries = LIBRARIES,
                    sources = ['_cpyrit_opencl.c'],
                    include_dirs = OPENCL_INC_DIRS,
                    library_dirs = OPENCL_LIB_DIRS,
                    extra_compile_args = EXTRA_COMPILE_ARGS,
                    extra_link_args = EXTRA_LINK_ARGS)

setup_args = dict(
        name = 'cpyrit-opencl',
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
        author = 'Lukas Lueg',
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
        ext_modules = [opencl_extension],
        cmdclass = {'build_ext': GPUBuilder, 'clean': GPUCleaner},
        options = {'install': {'optimize': 1}, \
                   'bdist_rpm': {'requires': 'pyrit = 0.4.0-1'}}
        )

if __name__ == "__main__":
    setup(**setup_args)
