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

"""Abstracted hardware-access for Pyrit.

   Core is a base-class to glue hardware-modules into python.

   CPUCore, OpenCLCore and NetworkCore are subclasses of Core and provide
   access to their respective hardware-platforms.

   CPyrit enumerates the available cores and schedules workunits among them.
"""

from __future__ import with_statement

from collections import deque
import BaseHTTPServer
import hashlib
import random
import socket
import sys
import threading
import time
import uuid
import util
import warnings
import xmlrpclib

import config
import network
import storage
import _cpyrit_cpu


# prevent call to socket.getfqdn
def fast_address_string(self):
    return '%s' % self.client_address[0]
BaseHTTPServer.BaseHTTPRequestHandler.address_string = fast_address_string
del fast_address_string


def version_check(mod):
    ver = getattr(mod, "VERSION", "unknown")
    if ver >= _cpyrit_cpu.VERSION:
        warnings.warn("WARNING: %s version ('%s') is greater than %s ('%s').\n" % (mod, ver, _cpyrit_cpu, _cpyrit_cpu.VERSION))


class Core(util.Thread):
    """The class Core provides basic scheduling and testing. It should not be
       used directly but through sub-classes.

       Subclasses must mix-in a .solve()-function and should set the
       .buffersize-, .minBufferSize- and .maxBufferSize-attributes. The default
       .run() provided here calibrates itself to pull work from the queue worth
       3 seconds of execution time in .solve()
    """
    TV_ESSID = 'foo'
    TV_PW = 'barbarbar'
    TV_PMK = ''.join(map(chr, (6, 56, 101, 54, 204, 94, 253, 3, 243, 250,
                               132, 170, 142, 162, 204, 132, 8, 151, 61, 243,
                               75, 216, 75, 83, 128, 110, 237, 48, 35, 205,
                               166, 126)))

    def __init__(self, queue):
        """Create a new Core that pulls work from the given CPyrit instance."""
        util.Thread.__init__(self)
        self.queue = queue
        self.compTime = self.resCount = self.callCount = 0
        self.isTested = False
        self.shallStop = False
        self.buffersize = 4096
        """Number of passwords currently pulled by calls to _gather()
           This number is dynamically adapted in run() but limited by
           .minBufferSize and .maxBufferSize.
        """
        self.minBufferSize = 128
        """Min. number of passwords that get pulled in each call to _gather."""
        self.maxBufferSize = 20480
        """Max. number of passwords that get pulled in each call to _gather."""
        self.setDaemon(True)

    def _testComputeFunction(self, i):
        if any((pmk != Core.TV_PMK for pmk in
                    self.solve(Core.TV_ESSID, [Core.TV_PW] * i))):
            raise ValueError("Test-vector does not result in correct PMK.")

    def resetStatistics(self):
        self.compTime = self.resCount = self.callCount = 0

    def run(self):
        while not self.shallStop:
            essid, pwlist = self.queue._gather(self.buffersize, timeout=0.5)
            if essid is not None:
                if not self.isTested:
                    self._testComputeFunction(101)
                    self.isTested = True
                t = time.time()
                res = self.solve(essid, pwlist)
                assert len(res) == len(pwlist)
                self.compTime += time.time() - t
                self.resCount += len(res)
                self.callCount += 1
                if self.compTime > 0:
                    # carefully move towards three seconds of execution-time
                    avg = (2 * self.buffersize +
                           (self.resCount / self.compTime * 3)) / 3
                    self.buffersize = int(max(self.minBufferSize,
                                              min(self.maxBufferSize, avg)))
                self.queue._scatter(essid, pwlist, res)

    def __str__(self):
        return self.name


class CPUCore(Core, _cpyrit_cpu.CPUDevice):
    """Standard-CPU implementation. The underlying C-code may use VIA Padlock,
       SSE2 or a generic OpenSSL-interface to compute results."""

    def __init__(self, queue):
        Core.__init__(self, queue)
        _cpyrit_cpu.CPUDevice.__init__(self)
        self.buffersize = 512
        self.name = "CPU-Core (%s)" % _cpyrit_cpu.getPlatform()
        self.start()


class LowLatencyCore(Core):
    def __init__(self, queue):
        Core.__init__(self, queue)
        self.bufferSizeDiv = 0

    def _getTestData(self, i):
        return (Core.TV_ESSID, [Core.TV_PW] * i)

    def _testData(self, res):
        if any((pmk != Core.TV_PMK for pmk in res)):
            raise ValueError("Test-vector does not result in correct PMK.")

    def _processData(self, essid, pwlist, res, tm):
        assert(len(res) == len(pwlist))
        t = time.time()
        self.compTime += t - tm
        self.resCount += len(res)
        self.callCount += 1
        avg = (2 * self.buffersize + (self.resCount / self.compTime)) / 3
        if self.bufferSizeDiv > 0:
            avg = self.bufferSizeDiv * int((avg + self.bufferSizeDiv - 1) / self.bufferSizeDiv)
        self.buffersize = int(max(self.minBufferSize,
                              min(self.maxBufferSize, avg)))
        self.queue._scatter(essid, pwlist, res)
        return t

    def solve(self, essid, pwlist):
        enq = self.send(essid, pwlist)
        assert(enq)
        return self.receive(True)

    def run(self):
        work_queue = deque()
        work_available = False
        t = time.time()
        while not self.shallStop:
            if not work_available:
                if not self.isTested:
                    essid, pwlist = self._getTestData(101)
                else:
                    essid, pwlist = self.queue._gather(self.buffersize,
                                                       timeout=0.5)
                if essid is not None:
                    work_queue.append((essid, pwlist, not self.isTested))
                    self.isTested = True
                    work_available = True
                    if len(work_queue) == 1:
                        t = time.time()
            if len(work_queue) <= 0:
                continue
            if work_available:
                essid, pwlist, testing = work_queue[-1]
                work_available = not self.send(essid, pwlist)
            res = self.receive(work_available)
            if res is not None:
                essid, pwlist, testing = work_queue.popleft()
                if not testing:
                    t = self._processData(essid, pwlist, res, t)
                else:
                    self._testData(res)


try:
    import _cpyrit_opencl
except ImportError:
    pass
except Exception, e:
    print >> sys.stderr, "Failed to load Pyrit's OpenCL-core ('%s')." % e
else:
    version_check(_cpyrit_opencl)

    class OpenCLCore(Core, _cpyrit_opencl.OpenCLDevice):
        """Computes results on OpenCL-capable devices."""

        def __init__(self, queue, platform_idx, dev_idx):
            Core.__init__(self, queue)
            _cpyrit_opencl.OpenCLDevice.__init__(self, platform_idx, dev_idx)
            self.name = "OpenCL-Device '%s'" % self.deviceName
            self.minBufferSize = 1024
            self.buffersize = 4096
            maxhwsize = reduce(lambda x, y: x * y, self.maxWorkSizes)
            self.maxBufferSize = min(180224, maxhwsize)
            self.start()


try:
    import _cpyrit_cuda
except ImportError:
    pass
except Exception, e:
    print >> sys.stderr, "Failed to load Pyrit's CUDA-core ('%s')." % e
else:
    version_check(_cpyrit_cuda)

    class CUDACore(Core, _cpyrit_cuda.CUDADevice):
        """Computes results on Nvidia-CUDA capable devices."""

        def __init__(self, queue, dev_idx):
            Core.__init__(self, queue)
            _cpyrit_cuda.CUDADevice.__init__(self, dev_idx)
            self.name = "CUDA-Device #%i '%s'" % (dev_idx + 1, self.deviceName)
            self.minBufferSize = 1024
            self.buffersize = 4096
            self.maxBufferSize = 131072
            self.start()


try:
    import _cpyrit_calpp
except ImportError:
    pass
except Exception, e:
    print >> sys.stderr, "Failed to load Pyrit's CAL-core ('%s')." % e
else:
    version_check(_cpyrit_calpp)

    class CALCore(LowLatencyCore, _cpyrit_calpp.CALDevice):
        """Computes results on ATI CAL capable devices."""

        def __init__(self, queue, dev_idx):
            LowLatencyCore.__init__(self, queue)
            _cpyrit_calpp.CALDevice.__init__(self, dev_idx)
            self.name = "CAL++ Device #%i '%s'" % \
                        (dev_idx + 1, self.deviceName)
            self.minBufferSize, self.buffersize, self.maxBufferSize, \
                self.bufferSizeDiv = self.workSizes()
            self.start()


try:
    import _cpyrit_null
except ImportError:
    pass
else:

    class NullCore(Core, _cpyrit_null.NullDevice):
        """Dummy-Device that returns zero'ed results instead of PMKs.
           For testing and demonstration only...
        """

        def __init__(self, queue):
            raise RuntimeError("The Null-Core should never get initialized!")
            Core.__init__(self, queue)
            _cpyrit_null.NullDevice.__init__(self)
            self.name = "Null-Core"
            self.start()


class NetworkCore(util.AsyncXMLRPCServer, Core):

    class NetworkObserver(util.Thread):

        def __init__(self, core):
            util.Thread.__init__(self)
            self.core = core
            self.setDaemon(True)
            self.start()

        def run(self):
            while True:
                for _, client in self.core.clients.items():
                    if time.time() - client.lastseen > 15.0:
                        self.core.rpc_unregister(uuid)
                time.sleep(3)

    class NetworkClient(object):

        def __init__(self, known_uuids):
            self.uuid = str(uuid.uuid4())
            self.known_uuids = known_uuids
            self.lastseen = time.time()
            self.workunits = []

        def ping(self):
            self.lastseen = time.time()

    def __init__(self, queue, host='', port=17935):
        util.AsyncXMLRPCServer.__init__(self, (host, port))
        Core.__init__(self, queue)
        self.name = "Network-Clients"
        self.uuid = str(uuid.uuid4())
        self.methods['register'] = self.rpc_register
        self.methods['unregister'] = self.rpc_unregister
        self.methods['gather'] = self.rpc_gather
        self.methods['scatter'] = self.rpc_scatter
        self.methods['revoke'] = self.rpc_revoke
        self.client_lock = threading.Lock()
        self.clients = {}
        self.host = host
        self.port = port
        self.observer = self.NetworkObserver(self)
        self.startTime = time.time()
        self.start()

    def _get_client(self, uuid):
        with self.client_lock:
            if uuid in self.clients:
                client = self.clients[uuid]
                client.ping()
                return client
            else:
                raise xmlrpclib.Fault(403, "Client unknown or timed-out")

    def rpc_register(self, uuids):
        with self.client_lock:
            known_uuids = set(uuids.split(';'))
            if self.uuid in known_uuids:
                return (self.uuid, '')
            else:
                client = self.NetworkClient(known_uuids)
                self.clients[client.uuid] = client
                return (self.uuid, client.uuid)

    def rpc_unregister(self, uuid):
        with self.client_lock:
            if uuid in self.clients:
                client = self.clients[uuid]
                for essid, pwlist in client.workunits:
                    self.queue._revoke(essid, pwlist)
                del self.clients[uuid]
                return True
            else:
                return False

    def rpc_gather(self, client_uuid, buffersize):
        client = self._get_client(client_uuid)
        essid, pwlist = self.queue._gather(buffersize, block=False)
        if essid is None:
            return ('', '')
        else:
            client.workunits.append((essid, pwlist))
            key, buf = storage.PAW2_Buffer.pack(pwlist)
            return (essid, xmlrpclib.Binary(buf))

    def rpc_scatter(self, client_uuid, encoded_buf):
        client = self._get_client(client_uuid)
        essid, pwlist = client.workunits.pop(0)
        md = hashlib.sha1()
        digest = encoded_buf.data[:md.digest_size]
        buf = encoded_buf.data[md.digest_size:]
        md.update(buf)
        if md.digest() != digest:
            raise IOError("Digest check failed.")
        if len(buf) != len(pwlist) * 32:
            raise ValueError("Result has invalid size of %i. Expected %i." %
                                (len(buf), len(pwlist) * 32))
        results = [buf[i * 32:i * 32 + 32] for i in xrange(len(pwlist))]
        self.compTime = time.time() - self.startTime
        self.resCount += len(results)
        self.callCount += 1
        self.queue._scatter(essid, pwlist, results)
        client.ping()
        return True

    def rpc_revoke(self, client_uuid):
        client = self._get_client(client_uuid)
        essid, password = client.workunits.pop()
        self.queue._revoke(essid, password)
        client.ping()
        return True

    def __iter__(self):
        with self.client_lock:
            return self.clients.values().__iter__()


class CPyrit(object):
    """Enumerates and manages all available hardware resources provided in
       the module and does most of the scheduling-magic.

       The class provides FIFO-scheduling of workunits towards the 'host'
       which can use .enqueue() and corresponding calls to .dequeue().
       Scheduling towards the hardware is provided by _gather(), _scatter() and
       _revoke().
    """

    def __init__(self):
        """Create a new instance that blocks calls to .enqueue() when more than
           the given amount of passwords are currently waiting to be scheduled
           to the hardware.
        """
        self.inqueue = []
        self.outqueue = {}
        self.workunits = []
        self.slices = {}
        self.in_idx = self.out_idx = 0
        self.cores = []
        self.CUDAs = []
        self.OpCL = []
        self.all = []
        self.cv = threading.Condition()

        # CUDA
        if config.cfg['use_CUDA'] == 'true' and 'cpyrit._cpyrit_cuda' in sys.modules and config.cfg['use_OpenCL'] == 'false':

            CUDA = _cpyrit_cuda.listDevices()

            for dev_idx, device in enumerate(CUDA):
                self.CUDAs.append(CUDACore(queue=self, dev_idx=dev_idx))


        # OpenCL
        if config.cfg['use_OpenCL'] == 'true' and 'cpyrit._cpyrit_opencl' in sys.modules:

            for platform_idx in range(_cpyrit_opencl.numPlatforms):
                p = _cpyrit_opencl.OpenCLPlatform(platform_idx)
                for dev_idx in range(p.numDevices):
                    dev = _cpyrit_opencl.OpenCLDevice(platform_idx, dev_idx)
                    if dev.deviceType in ('GPU', 'ACCELERATOR'):
                        core = OpenCLCore(self, platform_idx, dev_idx)
                        self.OpCL.append(core)
        # CAL++
        if 'cpyrit._cpyrit_calpp' in sys.modules:
            for dev_idx, device in enumerate(_cpyrit_calpp.listDevices()):
                self.cores.append(CALCore(queue=self, dev_idx=dev_idx))


        # CPUs
        for i in xrange(util.ncpus):
            self.cores.append(CPUCore(queue=self))


        # Network

        if config.cfg['rpc_server'] == 'true':
            for port in xrange(17935, 18000):
                try:
                    ncore = NetworkCore(queue=self, port=port)
                except socket.error:
                    pass
                else:
                    self.ncore_uuid = ncore.uuid
                    self.cores.append(ncore)
                    if config.cfg['rpc_announce'] == 'true':
                        cl = config.cfg['rpc_knownclients'].split(' ')
                        cl = filter(lambda x: len(x) > 0, map(str.strip, cl))
                        bcst = config.cfg['rpc_announce_broadcast'] == 'true'
                        self.announcer = network.NetworkAnnouncer(port=port, \
                                                          clients=cl, \
                                                          broadcast=bcst)
                    break
            else:
                self.ncore_uuid = None
        else:
            self.ncore_uuid = None


        for core in self.cores:
            self.all.append(core)
        for OCL in self.OpCL:
            self.all.append(OCL)
        for CD in self.CUDAs:
            self.all.append(CD)

    def _check_cores(self):
        for core in self.all:
            if not core.shallStop and not core.isAlive():
                raise SystemError("The core '%s' has died unexpectedly" % core)

    def _len(self):
        return sum((sum((len(pwlist) for pwlist in pwdict.itervalues()))
                   for essid, pwdict in self.inqueue))

    def __len__(self):
        """Return the number of passwords that currently wait to be transfered
           to the hardware."""
        with self.cv:
            return self._len()

    def __iter__(self):
        """Iterates over all pending results. Blocks until no further workunits
           or results are currently queued.
        """
        while True:
            r = self.dequeue(block=True)
            if r is None:
                break
            yield r

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def shutdown(self):
        for core in self.all:
            core.shallStop = True
        for core in self.all:
            core.shutdown()

    def isAlive(self):
        return all(core.isAlive() for core in self.all)

    def waitForSchedule(self, maxBufferSize):
        """Block until less than the given number of passwords wait for being
           scheduled to the hardware.
        """
        assert maxBufferSize >= 0
        with self.cv:
            while self._len() > maxBufferSize:
                self.cv.wait(2)
                self._check_cores()

    def resetStatistics(self):
        """Reset all cores' statistics"""
        for core in self.all:
            core.resetStatistics()

    def getPeakPerformance(self):
        """Return the summed peak performance of all cores.

           The number returned is based on the performance all cores would have
           with 100% occupancy. The real performance is lower if the caller
           fails to keep the pipeline filled.
        """
        return sum([c.resCount / c.compTime for c in self.all if c.compTime])

    def enqueue(self, essid, passwords, block=True):
        """Enqueue the given ESSID and iterable of passwords for processing.

           The call may block if block is True and the number of passwords
           currently waiting for being scheduled to the hardware is higher than
           five times the current peak performance.
           Calls to .dequeue() correspond in a FIFO-manner.
        """
        with self.cv:
            if self._len() > 0:
                while self.getPeakPerformance() == 0 \
                 or self._len() > self.getPeakPerformance() * 5:
                    self.cv.wait(2)
                    self._check_cores()
            passwordlist = list(passwords)
            if len(self.inqueue) > 0 and self.inqueue[-1][0] == essid:
                self.inqueue[-1][1][self.in_idx] = passwordlist
            else:
                self.inqueue.append((essid, {self.in_idx: passwordlist}))
            self.workunits.append(len(passwordlist))
            self.in_idx += len(passwordlist)
            self.cv.notifyAll()

    def dequeue(self, block=True, timeout=None):
        """Receive the results corresponding to a previous call to .enqueue().

           The function returns None if block is False and the respective
           results have not yet been completed. Otherwise the call blocks.
           The function may return None if block is True and the call waited
           longer than timeout.
           Calls to .enqueue() correspond in a FIFO-manner.
        """
        t = time.time()
        with self.cv:
            if len(self.workunits) == 0:
                return None
            while True:
                wu_length = self.workunits[0]
                if self.out_idx not in self.outqueue \
                 or len(self.outqueue[self.out_idx]) < wu_length:
                    self._check_cores()
                    if block:
                        if timeout:
                            while time.time() - t > timeout:
                                self.cv.wait(0.1)
                                if self.out_idx in self.outqueue and \
                                 len(self.outqueue[self.out_idx]) >= wu_length:
                                    break
                            else:
                                return None
                        else:
                            self.cv.wait(3)
                    else:
                        return None
                else:
                    reslist = self.outqueue[self.out_idx]
                    del self.outqueue[self.out_idx]
                    results = reslist[:wu_length]
                    self.out_idx += wu_length
                    self.outqueue[self.out_idx] = reslist[wu_length:]
                    self.workunits.pop(0)
                    self.cv.notifyAll()
                    return tuple(results)

    def _gather(self, desired_size, block=True, timeout=None):
        """Try to accumulate the given number of passwords for a single ESSID
           in one workunit. Return a tuple containing the ESSID and a tuple of
           passwords.

           The call blocks if no work is available and may return less than the
           desired number of passwords. The caller should compute the
           corresponding results and call _scatter() or _revoke() with the
           (ESSID,passwords)-tuple returned by this call as parameters.
        """
        t = time.time()
        with self.cv:
            passwords = []
            pwslices = []
            cur_essid = None
            restsize = desired_size
            while True:
                self._check_cores()
                for essid, pwdict in self.inqueue:
                    for idx, pwslice in sorted(pwdict.items()):
                        if len(pwslice) > 0:
                            if cur_essid is None:
                                cur_essid = essid
                            elif cur_essid != essid:
                                break
                            newslice = pwslice[:restsize]
                            del pwdict[idx]
                            if len(pwslice[len(newslice):]) > 0:
                                pwdict[idx + len(newslice)] = \
                                    pwslice[len(newslice):]
                            pwslices.append((idx, len(newslice)))
                            passwords.extend(newslice)
                            restsize -= len(newslice)
                            if restsize <= 0:
                                break
                    if len(pwdict) == 0:
                        self.inqueue.remove((essid, pwdict))
                    if restsize <= 0:
                        break
                if len(passwords) > 0:
                    wu = (cur_essid, tuple(passwords))
                    try:
                        self.slices[wu].append(pwslices)
                    except KeyError:
                        self.slices[wu] = [pwslices]
                    self.cv.notifyAll()
                    return wu
                else:
                    if block:
                        if timeout is not None and time.time() - t > timeout:
                            return None, None
                    else:
                        return None, None
                    self.cv.wait(0.1)

    def _scatter(self, essid, passwords, results):
        """Spray the given results back to their corresponding workunits.

           The caller must use the (ESSID,passwords)-tuple returned by
           _gather() to indicate which workunit it is returning results for.
        """
        assert len(results) == len(passwords)
        with self.cv:
            wu = (essid, passwords)
            slices = self.slices[wu].pop(0)
            if len(self.slices[wu]) == 0:
                del self.slices[wu]
            ptr = 0
            for idx, length in slices:
                self.outqueue[idx] = list(results[ptr:ptr + length])
                ptr += length
            for idx in sorted(self.outqueue.iterkeys(), reverse=True)[1:]:
                res = self.outqueue[idx]
                o_idx = idx + len(res)
                if o_idx in self.outqueue:
                    res.extend(self.outqueue[o_idx])
                    del self.outqueue[o_idx]
            self.cv.notifyAll()

    def _revoke(self, essid, passwords):
        """Re-insert the given workunit back into the global queue so it may
           be processed by other Cores.

           Should be used if the Core that pulled the workunit is unable to
           process it. It is the Core's responsibility to ensure that it stops
           pulling work from the queue in such situations.
        """
        with self.cv:
            wu = (essid, passwords)
            slices = self.slices[wu].pop()
            if len(self.slices[wu]) == 0:
                del self.slices[wu]
            passwordlist = list(passwords)
            if len(self.inqueue) > 0 and self.inqueue[0][0] == essid:
                d = self.inqueue[0][1]
            else:
                d = {}
                self.inqueue.insert(0, (essid, d))
            ptr = 0
            for idx, length in slices:
                d[idx] = passwordlist[ptr:ptr + length]
                ptr += length
            self.cv.notifyAll()


class StorageIterator(object):
    """Iterates over the database, computes new Pairwise Master Keys if
       necessary and requested and yields tuples of (password,PMK)-tuples.
    """

    def __init__(self, storage, essid, yieldOldResults=True, yieldNewResults=True):
        self.cp = CPyrit() if yieldNewResults else None
        self.workunits = []
        self.essid = essid
        self.storage = storage
        keys = list(self.storage.passwords)
        random.shuffle(keys)
        self.iterkeys = iter(keys)
        self.yieldOldResults = yieldOldResults
        self.yieldNewResults = yieldNewResults

    def keycount(self):
        return self.storage.essids.keycount(self.essid)

    def __len__(self):
        return len(self.storage.passwords)

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cp is not None:
            self.cp.shutdown()

    def next(self):
        while True:
            try:
                key = self.iterkeys.next()
            except StopIteration:
                if self.yieldNewResults:
                    solvedPMKs = self.cp.dequeue(block=True)
                    if solvedPMKs is not None:
                        solvedEssid, solvedKey, solvedPasswords = self.workunits.pop(0)
                        solvedResults = zip(solvedPasswords, solvedPMKs)
                        self.storage.essids[solvedEssid, solvedKey] = solvedResults
                        return solvedResults
                assert len(self.workunits) == 0
                raise StopIteration
            else:
                if self.yieldOldResults:
                    try:
                        results = self.storage.essids[self.essid, key]
                    except KeyError:
                        pass
                    else:
                        return results
                if self.yieldNewResults:
                    passwords = self.storage.passwords[key]
                    self.workunits.append((self.essid, key, passwords))
                    self.cp.enqueue(self.essid, passwords)
                    solvedPMKs = self.cp.dequeue(block=False)
                    if solvedPMKs is not None:
                        solvedEssid, solvedKey, solvedPasswords = self.workunits.pop(0)
                        solvedResults = zip(solvedPasswords, solvedPMKs)
                        self.storage.essids[solvedEssid, solvedKey] = solvedResults
                        return solvedResults


class PassthroughIterator(object):
    """A iterator that takes an ESSID and an iterable of passwords, computes
       the corresponding Pairwise Master Keys and and yields tuples of
       (password,PMK)-tuples.
    """

    def __init__(self, essid, iterable, buffersize=20000):
        self.cp = CPyrit()
        self.essid = essid
        self.iterator = iter(iterable)
        self.workunits = []
        self.buffersize = buffersize

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cp.shutdown()

    def next(self):
        pwbuffer = []
        for line in self.iterator:
            pw = line.strip('\r\n')[:63]
            if len(pw) >= 8:
                pwbuffer.append(pw)
            if len(pwbuffer) > self.buffersize:
                self.workunits.append(pwbuffer)
                self.cp.enqueue(self.essid, self.workunits[-1])
                pwbuffer = []
                solvedPMKs = self.cp.dequeue(block=False)
                if solvedPMKs is not None:
                    return zip(self.workunits.pop(0), solvedPMKs)
        if len(pwbuffer) > 0:
            self.workunits.append(pwbuffer)
            self.cp.enqueue(self.essid, self.workunits[-1])
        for solvedPMKs in self.cp:
            return zip(self.workunits.pop(0), solvedPMKs)
        raise StopIteration
