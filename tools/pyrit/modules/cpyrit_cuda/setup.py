#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    Copyright 2008-2011 Lukas Lueg, lukas.lueg@gmail.com
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
import os
import sys
import zlib
import platform
import subprocess

from distutils.core import setup, Extension
from distutils.command.build_ext import build_ext
from distutils.command.clean import clean

VERSION = '0.5.0'

NVIDIA_INC_DIRS = []
NVCC = 'nvcc'
for path in ('/usr/local/cuda', '/opt/cuda'):
    if os.path.exists(path):
        NVIDIA_INC_DIRS.append(os.path.join(path, 'include'))
        NVCC = os.path.join(path, 'bin', 'nvcc')
        break
else:
    print >>sys.stderr, "The CUDA compiler and headers required to build " \
                        "kernel were not found. Trying to continue anyway..."


EXTRA_COMPILE_ARGS = ['-Wall', '-fno-strict-aliasing',
                      '-DVERSION="%s"' % (VERSION,)]


class GPUBuilder(build_ext):

    def _call(self, comm):
        p = subprocess.Popen(comm, stdout=subprocess.PIPE, shell=True)
        stdo, stde = p.communicate()
        if p.returncode == 0:
            return stdo
        else:
            print >>sys.stderr, "%s\nFailed to execute command '%s'" % \
                                (stde, comm)
            return None

    def _makedirs(self, pathname):
        try:
            os.makedirs(pathname)
        except OSError:
            pass

    def run(self):
        if '_cpyrit_cudakernel.ptx.h' in os.listdir('./'):
            print "Skipping rebuild of Nvidia CUDA kernel ..."
        else:
            nvcc_o = self._call(NVCC + ' -V')
            if nvcc_o is not None:
                nvcc_version = nvcc_o.split('release ')[-1].strip()
            else:
                raise SystemError("Nvidia's CUDA-compiler 'nvcc' can't be " \
                                  "found.")
            print "Compiling CUDA module using nvcc %s..." % nvcc_version

            # We need to hardcode arch at least for MacOS 10.6 / CUDA 3.1
            bits, linkage = platform.architecture()
            if bits == '32bit':
                bit_flag = ' -m32'
            elif bits == '64bit':
                bit_flag = ' -m64'
            else:
                print >>sys.stderr, "Can't detect platform, using 32bit"
                bit_flag = ' -m32'

            nvcc_cmd = NVCC + bit_flag + ' -ccbin clang -Xcompiler "-fPIC" --ptx ./_cpyrit_cudakernel.cu'

            print "Executing '%s'" % nvcc_cmd
            subprocess.check_call(nvcc_cmd, shell=True)

            with open("_cpyrit_cudakernel.ptx", "rb") as fid:
                ptx = fid.read() + '\x00'
            ptx_inc = ["0x%02X" % ord(c) for c in zlib.compress(ptx)]
            with open("_cpyrit_cudakernel.ptx.h", "wb") as fid:
                fid.write("unsigned char __cudakernel_packedmodule[] = {")
                fid.write(','.join(ptx_inc))
                fid.write("};\nsize_t cudakernel_modulesize = %i;\n" % len(ptx))
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
            for f in ('_cpyrit_cudakernel.linkinfo', \
                      '_cpyrit_cudakernel.ptx', \
                      '_cpyrit_cudakernel.ptx.h'):
                self._unlink(f)
        except Exception, (errno, sterrno):
            print >>sys.stderr, "Exception while cleaning temporary " \
                                "files ('%s')" % sterrno
        clean.run(self)


cuda_extension = Extension('cpyrit._cpyrit_cuda',
                    libraries = ['crypto','cuda','z'],
                    sources = ['_cpyrit_cuda.c'],
                    include_dirs = NVIDIA_INC_DIRS,
                    extra_compile_args = EXTRA_COMPILE_ARGS)

setup_args = dict(
        name = 'cpyrit-cuda',
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
        ext_modules = [cuda_extension],
        cmdclass = {'build_ext': GPUBuilder, 'clean': GPUCleaner},
        options = {'install': {'optimize': 1}, \
                    'bdist_rpm': {'requires': 'pyrit >= 0.4.0'}})

if __name__ == "__main__":
    setup(**setup_args)
