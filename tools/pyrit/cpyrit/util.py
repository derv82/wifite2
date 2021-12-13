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

"""Various utility- and backend-related classes and data for Pyrit.

   AsyncFileWriter is used for threaded, buffered output.

   CowpattyFile eases reading/writing files in cowpatty's binary format.

   ncpus equals the number of available CPUs in the system.

   Thread is a subclass of threading.Thread that adds a context-manager to
   make it 'stoppable'.

   AsyncXMLRPCServer is a stoppable (incl. 'serve_forever') subclass of
   SimpleXMLRPCServer.

   PMK_TESTVECTORS has two ESSIDs and ten password:PMK pairs each to verify
   local installations.
"""

from __future__ import with_statement

import bisect
import cStringIO
import gzip
import os
import Queue
import random
import socket
import SimpleXMLRPCServer
import sys
import struct
import time
import threading

import _cpyrit_cpu
from _cpyrit_cpu import VERSION, grouper
import config

__version__ = VERSION


def _detect_ncpus():
    """Detect the number of effective CPUs in the system"""
    # Snippet taken from ParallelPython
    # For Linux, Unix and MacOS
    if hasattr(os, "sysconf"):
        if "SC_NPROCESSORS_ONLN" in os.sysconf_names:
            #Linux and Unix
            ncpus = os.sysconf("SC_NPROCESSORS_ONLN")
            if isinstance(ncpus, int) and ncpus > 0:
                return ncpus
        else:
            #MacOS X
            return int(os.popen2("sysctl -n hw.ncpu")[1].read())
    #for Windows
    if "NUMBER_OF_PROCESSORS" in os.environ:
        ncpus = int(os.environ["NUMBER_OF_PROCESSORS"])
        if ncpus > 0:
            return ncpus
    #return the default value
    return 1


def _limit_ncpus():
    """Limit the number of reported CPUs if so requested"""
    detected_ncpus = _detect_ncpus()
    try:
        limited_ncpus = int(config.cfg['limit_ncpus'])
    except ValueError:
        raise ValueError("Invalid 'limit_ncpus' in configuration")
    if limited_ncpus < 0:
    #raise ValueError("Invalid 'limit_ncpus' in configuration")
        return 0;
    if 0 < limited_ncpus < detected_ncpus:
        return limited_ncpus
    return detected_ncpus


ncpus = _limit_ncpus()
""" Number of effective CPUs (in the moment the module was loaded)."""


def str2hex(string):
    """Convert a string to it's hex-decimal representation."""
    return ''.join('%02x' % c for c in map(ord, string))


class ScapyImportError(ImportError):
    """ ScapyImportError is used to indicate failure to import scapy's modules.
        Used to o separate other ImportErrors so code that tries to
        import pckttools can continue in case Scapy is simply not installed.
    """
    pass


class SqlalchemyImportError(ImportError):
    """" Indicates that sqlalchemy is not available """
    pass


class SortedCollection(object):
    '''Sequence sorted by a key function.

       Taken from http://code.activestate.com/recipes/577197-sortedcollection/
    '''

    def __init__(self, iterable=(), key=None):
        self._given_key = key
        key = (lambda x: x) if key is None else key
        decorated = sorted((key(item), item) for item in iterable)
        self._keys = [k for k, item in decorated]
        self._items = [item for k, item in decorated]
        self._key = key

    def _getkey(self):
        return self._key

    def _setkey(self, key):
        if key is not self._key:
            self.__init__(self._items, key=key)

    def _delkey(self):
        self._setkey(None)

    key = property(_getkey, _setkey, _delkey, 'key function')

    def __len__(self):
        return len(self._items)

    def __getitem__(self, i):
        return self._items[i]

    def __iter__(self):
        return iter(self._items)

    def __reversed__(self):
        return reversed(self._items)

    def __repr__(self):
        return '%s(%r, key=%s)' % (
            self.__class__.__name__,
            self._items,
            getattr(self._given_key, '__name__', repr(self._given_key))
        )

    def __reduce__(self):
        return self.__class__, (self._items, self._given_key)

    def __contains__(self, item):
        k = self._key(item)
        i = bisect.bisect_left(self._keys, k)
        j = bisect.bisect_right(self._keys, k)
        return item in self._items[i:j]

    def index(self, item):
        'Find the position of an item.  Raise ValueError if not found.'
        k = self._key(item)
        i = bisect.bisect_left(self._keys, k)
        j = bisect.bisect_right(self._keys, k)
        return self._items[i:j].index(item) + i

    def count(self, item):
        'Return number of occurrences of item'
        k = self._key(item)
        i = bisect.bisect_left(self._keys, k)
        j = bisect.bisect_right(self._keys, k)
        return self._items[i:j].count(item)

    def insert(self, item):
        'Insert a new item.  If equal keys are found, add to the left'
        k = self._key(item)
        i = bisect.bisect_left(self._keys, k)
        self._keys.insert(i, k)
        self._items.insert(i, item)

    def insert_right(self, item):
        'Insert a new item.  If equal keys are found, add to the right'
        k = self._key(item)
        i = bisect.bisect_right(self._keys, k)
        self._keys.insert(i, k)
        self._items.insert(i, item)

    def remove(self, item):
        'Remove first occurence of item.  Raise ValueError if not found'
        i = self.index(item)
        del self._keys[i]
        del self._items[i]

    def find(self, k):
        'Return first item with a key == k.  Raise ValueError if not found.'
        i = bisect.bisect_left(self._keys, k)
        if i != len(self) and self._keys[i] == k:
            return self._items[i]
        raise ValueError('No item found with key equal to: %r' % (k,))

    def find_le(self, k):
        'Return last item with a key <= k.  Raise ValueError if not found.'
        i = bisect.bisect_right(self._keys, k)
        if i:
            return self._items[i-1]
        raise ValueError('No item found with key at or below: %r' % (k,))

    def find_lt(self, k):
        'Return last item with a key < k.  Raise ValueError if not found.'
        i = bisect.bisect_left(self._keys, k)
        if i:
            return self._items[i-1]
        raise ValueError('No item found with key below: %r' % (k,))

    def find_ge(self, k):
        'Return first item with a key >= equal to k.  Raise ValueError if not found'
        i = bisect.bisect_left(self._keys, k)
        if i != len(self):
            return self._items[i]
        raise ValueError('No item found with key at or above: %r' % (k,))

    def find_gt(self, k):
        'Return first item with a key > k.  Raise ValueError if not found'
        i = bisect.bisect_right(self._keys, k)
        if i != len(self):
            return self._items[i]
        raise ValueError('No item found with key above: %r' % (k,))


class FileWrapper(object):
    """A wrapper for easy stdin/stdout/gzip-handling"""

    def __init__(self, filename, mode='rb'):
        if isinstance(filename, str):
            if filename == '-':
                if 'r' in mode:
                    self.f = sys.stdin
                elif 'w' in mode or 'a' in mode:
                    self.f = sys.stdout
                else:
                    raise ValueError("Unknown filemode '%s'" % mode)
            elif filename.endswith('.gz'):
                self.f = gzip.open(filename, mode, 6)
            else:
                self.f = open(filename, mode)
        else:
            self.f = filename
        self.isclosed = False

    def read(self, size=None):
        return self.f.read(size)

    def write(self, buf):
        self.f.write(buf)

    def seek(self, offset, whence=None):
        self.f.seek(offset, whence)

    def flush(self):
        self.f.flush()

    def close(self):
        if not self.isclosed:
            try:
                self.f.close()
            finally:
                self.isclosed = True

    def readlines(self):
        return self.f.readlines()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __iter__(self):
        return self.f.__iter__()


class CowpattyFile(_cpyrit_cpu.CowpattyFile):
    """A file-like object to read and write cowpatty-like files."""

    def __init__(self, filename, mode='r', essid=None):
        _cpyrit_cpu.CowpattyFile.__init__(self)
        if mode == 'r':
            self.f = FileWrapper(filename, 'r')
            magic, essidlen, essid = struct.unpack(">4si32s", self.f.read(40))
            if magic != 'APWC':
                raise RuntimeError("Not a cowpatty-file.")
            if essidlen < 1 or essidlen > 32:
                raise ValueError("Invalid ESSID")
            self.essid = essid[:essidlen]
        elif mode == 'w':
            if essid is None:
                raise TypeError("ESSID must be specified when writing.")
            if len(essid) < 1 or len(essid) > 32:
                raise ValueError("Invalid ESSID.")
            self.essid = essid
            self.f = FileWrapper(filename, 'wb')
            self.f.write("APWC\00\00\00" + \
                        chr(len(essid)) + essid + \
                        '\00' * (32 - len(essid)))
        else:
            raise RuntimeError("Invalid mode.")
        self.tail = ''
        self.eof = False
        self.mode = mode

    def __iter__(self):
        if self.mode != 'r':
            raise TypeError("Can't read from write-only file.")
        self.f.seek(40, os.SEEK_SET)
        self.tail = ''
        return self

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def write(self, results):
        if self.mode != 'w':
            raise TypeError("Can't write to read-only file.")
        self.f.write(self.genCowpEntries(results))

    def close(self):
        self.f.close()

    def next(self):
        if self.mode != 'r':
            raise TypeError("Can't read from write-only file.")
        self.tail = self.tail + self.f.read(512 * 1024)
        if len(self.tail) == 0:
            self.eof = True
            raise StopIteration
        results, self.tail = self.unpackCowpEntries(self.tail)
        return results


class AsyncFileWriter(threading.Thread):
    """A buffered, asynchronous file-like object.

       Writing to this object will only block if the internal buffer
       exceeded it's maximum size. The call to .write() is done in a seperate
       thread.
    """

    def __init__(self, f, maxsize=10 * 1024 ** 2):
        """Create a instance writing to the given file-like-object and
           buffering maxsize before blocking.
        """
        threading.Thread.__init__(self)
        self.filehndl = FileWrapper(f, 'wb')
        self.shallstop = False
        self.hasstopped = False
        self.maxsize = maxsize
        self.excp = None
        self.buf = cStringIO.StringIO()
        self.cv = threading.Condition()
        self.start()

    def __enter__(self):
        with self.cv:
            if self.shallstop:
                raise RuntimeError("Writer has already been closed")
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        """Stop the writer and wait for it to finish.

           The file handle that was used for initialization is closed.
           Exceptions in the writer-thread are re-raised after the writer is
           closed.
        """
        with self.cv:
            self.shallstop = True
            self.cv.notifyAll()
            while not self.hasstopped:
                self.cv.wait()
            self.filehndl.close()
            self._raise()

    def write(self, data):
        """Write data to the buffer, block if necessary.

           Exceptions in the writer-thread are re-raised in the caller's thread
           before the data is written.
        """
        with self.cv:
            self._raise()
            while self.buf.tell() > self.maxsize:
                self.cv.wait()
                if self.shallstop:
                    raise RuntimeError("Writer has already been closed.")
            self.buf.write(data)
            self.cv.notifyAll()

    def closeAsync(self):
        """Signal the writer to stop and return to caller immediately.

           The file handle that was used for initialization is not closed by a
           call to closeAsync().
           The caller must call join() before trying to close the file handle
           to prevent this instance from writing to a closed file handle.
           Exceptions are not re-raised.
        """
        with self.cv:
            self.shallstop = True
            self.cv.notifyAll()

    def join(self):
        """Wait for the writer to stop.

           Exceptions in the writer-thread are re-raised in the caller's thread
           after writer has stopped.
        """
        with self.cv:
            while not self.hasstopped:
                self.cv.wait()
            self._raise()

    def _raise(self):
        # Assumes we hold self.cv
        if self.excp:
            e = self.excp
            self.excp = None
            self.shallstop = True
            self.cv.notifyAll()
            raise e

    def run(self):
        try:
            while True:
                with self.cv:
                    data = None
                    if self.buf.tell() == 0:
                        if self.shallstop:
                            break
                        else:
                            self.cv.wait()
                    else:
                        data = self.buf.getvalue()
                        self.buf = cStringIO.StringIO()
                        self.cv.notifyAll()
                if data:
                    self.filehndl.write(data)
            self.filehndl.flush()
        except Exception, e:
            # Re-create a 'trans-thread-safe' instance
            self.excp = type(e)(str(e))
        finally:
            with self.cv:
                self.shallstop = self.hasstopped = True
                self.cv.notifyAll()


class PerformanceCounter(object):

    def __init__(self, window=60.0):
        self.window = window
        self.datapoints = [[time.time(), 0.0]]
        self.total = 0

    def addRelativePoint(self, p):
        self.total += p
        t = time.time()
        if len(self.datapoints) < 1 \
          or t - self.datapoints[-1][0] > 0.5 \
          or self.datapoints[-1][1] == 0.0:
            self.datapoints.append([time.time(), p])
        else:
            self.datapoints[-1][1] += p
        self.__purge()

    def addAbsolutePoint(self, p):
        self.addRelativePoint(p - self.total)

    def __iadd__(self, p):
        self.addRelativePoint(p)
        return self

    def __purge(self):
        t = time.time()
        if t - self.datapoints[0][0] > self.window:
            self.datapoints = filter(lambda x: (t - x[0]) < self.window, \
                                                self.datapoints)

    def getAvg(self):
        self.__purge()
        if len(self.datapoints) < 2:
            return 0.0
        t = self.datapoints[-1][0] - self.datapoints[0][0]
        if t > 0.0:
            return sum(x[1] for x in self.datapoints) / t
        else:
            return 0.0

    def __str__(self):
        return str(self.value())

    avg = property(fget=getAvg)


class Thread(threading.Thread):
    """A stoppable subclass of threading.Thread"""

    def __init__(self):
        threading.Thread.__init__(self)
        self.shallStop = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def shutdown(self):
        self.shallStop = True
        self.join()


class AsyncXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer, Thread):
    """A stoppable XMLRPCServer

       The main socket is made non-blocking so we can check on
       self.shallStop from time to time.

       Sub-classes should add (name:function)-entries to self.methods
    """

    def __init__(self, (iface, port)=('', 17934)):
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, (iface, port), \
                                                        logRequests=False)
        Thread.__init__(self)
        self.setDaemon(True)
        # Make the main socket non-blocking (for accept())
        self.socket.settimeout(1)
        self.methods = {}
        self.register_instance(self)

    def run(self):
        while not self.shallStop:
            self.handle_request()

    def get_request(self):
        while not self.shallStop:
            try:
                sock, addr = self.socket.accept()
            except socket.timeout:
                pass
            else:
                # Accepted connections are made blocking again
                sock.settimeout(None)
                return sock, addr
        raise socket.timeout("Server has stopped.")

    def serve_forever(self):
        while not self.shallStop:
            time.sleep(1)

    def shutdown(self):
        Thread.shutdown(self)
        self.socket.close()

    def _dispatch(self, method, params):
        if method not in self.methods:
            raise AttributeError
        else:
            return self.methods[method](*params)


PMK_TESTVECTORS = {
    'foo': {
        'soZcEvntHVrGRDIxNaBCyUL':
            (247, 210, 173, 42, 68, 187, 144, 253, 145, 93, 126, 250, 16, 188,
             100, 55, 89, 153, 135, 155, 198, 86, 124, 33, 45, 16, 9, 54, 113,
             194, 159, 211),
        'EVuYtpQCAZzBXyWNRGTI':
            (5, 48, 168, 39, 10, 98, 151, 201, 8, 80, 23, 138, 19, 24, 24, 50,
             66, 214, 189, 180, 159, 97, 194, 27, 212, 124, 114, 100, 253, 62,
             50, 170),
        'XNuwoiGMnjlkxBHfhyRgZrJItFDqQVESm':
            (248, 208, 207, 115, 247, 35, 170, 203, 214, 228, 228, 21, 40, 214,
             165, 0, 98, 194, 136, 62, 110, 253, 69, 205, 67, 215, 119, 109,
             72, 226, 255, 199),
        'bdzPWNTaIol':
            (228, 236, 73, 0, 189, 244, 21, 141, 84, 247, 3, 144, 2, 164, 99,
             205, 37, 72, 218, 202, 182, 246, 227, 84, 24, 58, 147, 114, 206,
             221, 40, 127),
        'nwUaVYhRbvsH':
            (137, 21, 14, 210, 213, 68, 210, 123, 35, 143, 108, 57, 196, 47,
             62, 161, 150, 35, 165, 197, 154, 61, 76, 14, 212, 88, 125, 234,
             51, 38, 159, 208),
        'gfeuvPBbaDrQHldZzRtXykjFWwAhS':
            (88, 127, 99, 35, 137, 177, 147, 161, 244, 32, 197, 233, 178, 1,
             96, 247, 5, 109, 163, 250, 35, 222, 188, 143, 155, 70, 106, 1,
             253, 79, 109, 135),
        'QcbpRkAJerVqHz':
            (158, 124, 37, 190, 197, 150, 225, 165, 3, 34, 104, 147, 107, 253,
             233, 127, 33, 239, 75, 11, 169, 187, 127, 171, 187, 165, 166, 187,
             95, 107, 137, 212),
        'EbYJsCNiwXDmHtgkFVacuOv':
            (136, 5, 34, 189, 145, 60, 145, 54, 179, 198, 195, 223, 34, 180,
             144, 3, 116, 102, 39, 134, 68, 82, 210, 185, 190, 199, 36, 25,
             136, 152, 0, 111),
        'GpIMrFZwLcqyt':
            (28, 144, 175, 10, 200, 46, 253, 227, 219, 35, 98, 208, 220, 11,
             101, 95, 62, 244, 80, 221, 111, 49, 206, 255, 174, 100, 240, 240,
             33, 229, 172, 207),
        'tKxgswlaOMLeZVScGDW':
            (237, 62, 117, 60, 38, 107, 65, 166, 113, 174, 196, 221, 128, 227,
             69, 89, 23, 77, 119, 234, 41, 176, 145, 105, 92, 40, 157, 151,
             229, 50, 81, 65)},
    'bar': {
        'zLwSfveNskZoR':
            (38, 93, 196, 77, 112, 65, 163, 197, 249, 158, 180, 107, 231, 140,
             188, 60, 254, 77, 12, 210, 77, 185, 233, 59, 79, 212, 222, 181,
             44, 19, 127, 220),
        'lxsvOCeZXop':
            (91, 39, 98, 36, 82, 2, 162, 106, 12, 244, 4, 113, 155, 120, 131,
             133, 11, 209, 12, 12, 240, 213, 203, 156, 129, 148, 28, 64, 31,
             61, 162, 13),
        'tfHrgLLOA':
            (110, 72, 123, 80, 222, 233, 150, 54, 40, 99, 205, 155, 177, 157,
             174, 172, 87, 11, 247, 164, 87, 85, 136, 165, 21, 107, 93, 212,
             71, 133, 145, 211),
        'vBgsaSJrlqajUlQJM':
            (113, 110, 180, 150, 204, 221, 61, 202, 238, 142, 147, 118, 177,
             196, 65, 79, 102, 47, 179, 80, 175, 95, 251, 35, 227, 220, 47,
             121, 50, 125, 55, 16),
        'daDIHwIMKSUaKWXS':
            (33, 87, 211, 99, 26, 70, 123, 19, 254, 229, 148, 97, 252, 182, 3,
             44, 228, 125, 85, 141, 247, 223, 166, 133, 246, 37, 204, 145, 100,
             218, 66, 70),
        'agHOeAjOpK':
            (226, 163, 62, 215, 250, 63, 6, 32, 130, 34, 117, 116, 189, 178,
             245, 172, 74, 26, 138, 10, 106, 119, 15, 214, 210, 114, 51, 94,
             254, 57, 81, 200),
        'vRfEagJIzSohxsakj':
            (61, 71, 159, 35, 233, 27, 138, 30, 228, 121, 38, 201, 57, 83, 192,
             211, 248, 207, 149, 12, 147, 70, 190, 216, 52, 14, 165, 190, 226,
             180, 62, 210),
        'PuDomzkiwsejblaXs':
            (227, 164, 137, 231, 16, 31, 222, 169, 134, 1, 238, 190, 55, 126,
             255, 88, 178, 118, 148, 119, 244, 130, 183, 219, 124, 249, 194,
             96, 94, 159, 163, 185),
        'RErvpNrOsW':
            (24, 145, 197, 137, 14, 154, 1, 36, 73, 148, 9, 192, 138, 157, 164,
             81, 47, 184, 41, 75, 225, 34, 71, 153, 59, 253, 127, 179, 242,
             193, 246, 177),
        'ipptbpKkCCep':
            (81, 34, 253, 39, 124, 19, 234, 163, 32, 10, 104, 88, 249, 29, 40,
             142, 24, 173, 1, 68, 187, 212, 21, 189, 74, 88, 83, 228, 7, 100,
             23, 244)}}
for essid in PMK_TESTVECTORS:
    for pw in PMK_TESTVECTORS[essid]:
        PMK_TESTVECTORS[essid][pw] = \
                                ''.join(map(chr, PMK_TESTVECTORS[essid][pw]))
del essid
del pw
