#!/usr/bin/env python2
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

import sys
import platform
from distutils.core import setup, Extension
from distutils.command.build_ext import build_ext
from distutils.unixccompiler import UnixCCompiler
from distutils.errors import CompileError


VERSION = '0.5.1'

UnixCCompiler.src_extensions.append('.S')


EXTRA_COMPILE_ARGS = ['-Wall', '-fno-strict-aliasing',
                      '-DVERSION="%s"' % (VERSION,)]
# Support for AES-NI-intrinsics is not found everyhwere
if sys.platform in ('darwin', 'linux2') and \
   platform.machine() in ('x86_64', 'i386'):
    EXTRA_COMPILE_ARGS.extend(('-maes', '-mpclmul'))


class LazyBuilder(build_ext):
    '''The LazyBuilder-class tries to build the cpyrit_cpu-extension with
       -maes and -mpclmul first. If that fails, it simply re-tries with
       those flags disabled.
       This is not exactly elegant but probably the most portable solution
       given the limited capabilities of distutils to detect compiler-versions.
    '''

    def build_extension(self, ext):
        try:
            return build_ext.build_extension(self, ext)
        except CompileError:
            if ext.extra_compile_args and '-maes' in ext.extra_compile_args:
                print "Failed to build; Compiling without AES-NI"
                ext.extra_compile_args.remove('-maes')
                ext.extra_compile_args.remove('-mpclmul')
                return build_ext.build_extension(self, ext)
            else:
                raise


cpu_extension = Extension(name='cpyrit._cpyrit_cpu',
                    sources = ['cpyrit/_cpyrit_cpu.c',
                               'cpyrit/_cpyrit_cpu_sse2.S'],
                    libraries = ['crypto', 'pcap'],
                    extra_compile_args=EXTRA_COMPILE_ARGS)

setup_args = dict(
        name = 'pyrit',
        version = VERSION,
        description = 'GPU-accelerated attack against WPA-PSK authentication',
        long_description = \
            "Pyrit allows to create massive databases, pre-computing part " \
            "of the WPA/WPA2-PSK authentication phase in a space-time-" \
            "tradeoff. Exploiting the computational power of Many-Core- " \
            "and other platforms through ATI-Stream, Nvidia CUDA and OpenCL " \
            ", it is currently by far the most powerful attack against one " \
            "of the world's most used security-protocols.",
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
        packages = ['cpyrit'],
        py_modules = ['pyrit_cli', 'cpyrit.cpyrit',
                      'cpyrit.util', 'cpyrit.pckttools',
                      'cpyrit.config', 'cpyrit.network'],
        scripts = ['pyrit'],
        ext_modules = [cpu_extension],
        cmdclass = {'build_ext': LazyBuilder},
        options = {'install': {'optimize': 1}})

if __name__ == '__main__':
    setup(**setup_args)
