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

import hashlib
import socket
import time
import threading
import xmlrpclib

import storage
import util


class NetworkClient(util.Thread):

    class NetworkGatherer(threading.Thread):

        def __init__(self, client):
            threading.Thread.__init__(self)
            self.client = client
            self.server = xmlrpclib.ServerProxy("http://%s:%s" % \
                                                client.srv_addr)
            self.shallStop = False
            self.setDaemon(True)
            self.start()

        def run(self):
            while not self.shallStop:
                #TODO calculate optimal max buffersize
                try:
                    essid, pwbuffer = \
                        self.server.gather(self.client.uuid, 5000)
                except socket.error:
                    break
                if essid != '' or pwbuffer != '':
                    pwlist = storage.PAW2_Buffer(pwbuffer.data)
                    self.client.enqueue(essid, pwlist)
                else:
                    time.sleep(1)
                self.client.ping()

        def shutdown(self):
            self.shallStop = True
            self.join()

    def __init__(self, srv_addr, enqueue_callback, known_uuids):
        util.Thread.__init__(self)
        self.server = xmlrpclib.ServerProxy("http://%s:%s" % srv_addr)
        self.srv_uuid, self.uuid = self.server.register(";".join(known_uuids))
        if not self.uuid:
            raise KeyError("Loop detected to %s" % self.srv_uuid)
        self.srv_addr = srv_addr
        self.enqueue_callback = enqueue_callback
        self.cv = threading.Condition()
        self.stat_received = self.stat_enqueued = 0
        self.stat_scattered = self.stat_sent = 0
        self.results = []
        self.lastseen = time.time()
        self.setDaemon(True)

    def run(self):
        self.gatherer = self.NetworkGatherer(self)
        try:
            while self.gatherer.isAlive() and self.shallStop is False:
                with self.cv:
                    while len(self.results) == 0 and self.shallStop is False \
                          and self.gatherer.isAlive():
                        self.cv.wait(1)
                    if self.shallStop is not False \
                     or not self.gatherer.isAlive():
                        break
                    solvedPMKs = self.results.pop(0)
                buf = ''.join(solvedPMKs)
                md = hashlib.sha1()
                md.update(buf)
                encoded_buf = xmlrpclib.Binary(md.digest() + buf)
                self.server.scatter(self.uuid, encoded_buf)
                self.stat_sent += len(solvedPMKs)
                self.ping()
        finally:
            self.gatherer.shutdown()

    def enqueue(self, essid, pwlist):
        self.stat_received += len(pwlist)
        self.enqueue_callback(self.uuid, (essid, pwlist))
        self.stat_enqueued += len(pwlist)

    def scatter(self, results):
        with self.cv:
            self.results.append(results)
            self.cv.notifyAll()
            self.stat_scattered += len(results)

    def ping(self):
        self.lastseen = time.time()


class NetworkServer(util.Thread):

    def __init__(self):
        util.Thread.__init__(self)
        import cpyrit
        self.cp = cpyrit.CPyrit()
        self.clients_lock = threading.Lock()
        self.clients = {}
        self.pending_clients = []
        self.stat_gathered = self.stat_enqueued = 0
        self.stat_scattered = 0
        self.enqueue_lock = threading.Lock()
        self.setDaemon(True)
        self.start()

    def addClient(self, srv_addr):
        with self.clients_lock:
            if any(c.srv_addr == srv_addr for c in self.clients.itervalues()):
                return
            known_uuids = set(c.srv_uuid for c in self.clients.itervalues())
            if self.cp.ncore_uuid is not None:
                known_uuids.add(self.cp.ncore_uuid)
            try:
                client = NetworkClient(srv_addr, self.enqueue, known_uuids)
            except KeyError:
                pass
            else:
                client.start()
                self.clients[client.uuid] = client

    def enqueue(self, uuid, (essid, pwlist)):
        with self.clients_lock:
            if uuid not in self.clients:
                raise KeyError("Client unknown or timed-out")
        self.stat_gathered += len(pwlist)
        with self.enqueue_lock:
            self.pending_clients.append(uuid)
            self.cp.enqueue(essid, pwlist)
            self.stat_enqueued += len(pwlist)

    def run(self):
        while not self.shallStop:
            solvedPMKs = self.cp.dequeue(block=True, timeout=3.0)
            if solvedPMKs is None:
                time.sleep(1)
            else:
                uuid = self.pending_clients.pop(0)
                with self.clients_lock:
                    if uuid in self.clients:
                        client = self.clients[uuid]
                        client.scatter(solvedPMKs)
                        self.stat_scattered += len(solvedPMKs)
            with self.clients_lock:
                for client in self.clients.values():
                    if not client.isAlive() or \
                     time.time() - client.lastseen > 15.0:
                        del self.clients[client.uuid]
            if not self.cp.isAlive():
                self.shallStop == True
                raise RuntimeError

    def __contains__(self, srv_addr):
        with self.clients_lock:
            i = self.clients.itervalues()
            return any(c.srv_addr == srv_addr for c in i)

    def __len__(self):
        with self.clients_lock:
            return len(self.clients)

    def __iter__(self):
        with self.clients_lock:
            return self.clients.values().__iter__()

    def shutdown(self):
        self.shallStop = True
        with self.clients_lock:
            for client in self.clients.itervalues():
                client.shutdown()
        self.join()


class NetworkAnnouncer(util.Thread):
    """Announce the existence of a server via UDP-unicast and -broadcast"""

    def __init__(self, port=17935, clients=[], broadcast=True):
        util.Thread.__init__(self)
        self.port = port
        self.clients = clients
        msg = '\x00'.join(["PyritServerAnnouncement",
                        '',
                        str(port)])
        md = hashlib.sha1()
        md.update(msg)
        self.msg = msg + md.digest()
        self.ucast_sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if broadcast:
            self.bcast_sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.bcast_sckt.bind(('', 0))
            self.bcast_sckt.setsockopt(socket.SOL_SOCKET, \
                                       socket.SO_BROADCAST, 1)
        else:
            self.bcast_sckt = None
        self.setDaemon(True)
        self.start()

    def run(self):
        while self.shallStop is False:
            for client in self.clients:
                self.ucast_sckt.sendto(self.msg, (client, 17935))
            if self.bcast_sckt:
                self.bcast_sckt.sendto(self.msg, ('<broadcast>', 17935))
            time.sleep(1)


class NetworkAnnouncementListener(util.Thread):

    def __init__(self):
        util.Thread.__init__(self)
        self.cv = threading.Condition()
        self.servers = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', 17935))
        self.setDaemon(True)
        self.start()

    def run(self):
        while self.shallStop is False:
            buf, (host, port) = self.sock.recvfrom(4096)
            if buf.startswith("PyritServerAnnouncement"):
                md = hashlib.sha1()
                msg = buf[:-md.digest_size]
                md.update(msg)
                if md.digest() == buf[-md.digest_size:]:
                    msg_ann, msg_host, msg_port = msg.split('\x00')
                    if msg_host == '':
                        addr = (host, msg_port)
                    else:
                        addr = (msg_host, msg_port)
                    with self.cv:
                        if addr not in self.servers:
                            self.servers.append(addr)
                            self.cv.notifyAll()

    def waitForAnnouncement(self, block=True, timeout=None):
        t = time.time()
        with self.cv:
            while True:
                if len(self.servers) == 0:
                    if block:
                        if timeout is not None:
                            d = time.time() - t
                            if d < timeout:
                                self.cv.wait(d)
                            else:
                                return None
                        else:
                            self.cv.wait(1)
                    else:
                        return None
                else:
                    return self.servers.pop(0)

    def __iter__(self):
        return self

    def next(self):
        return self.waitForAnnouncement(block=True)

    def shutdown(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        util.Thread.shutdown(self)
