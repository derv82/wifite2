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


"""A test-suite for Pyrit.

   Tests are done by creating a sandbox and executing the cli-functions
   normally executed by the user.

   Please notice that the tests backed by the storage-relay open a TCP
   socket bound to localhost.
"""


from __future__ import with_statement

import os
import shutil
import random
import unittest
import sys
import tempfile

import cpyrit.config
import cpyrit.storage
import cpyrit.util
import pyrit_cli

cpyrit.config.cfg["rpc_server"] = "false"


def requires_pckttools(*params):
    """Decorate a function to check for cpyrit.cpyrit_pckttools
       before execution.
    """

    def check_pkttools(f):

        def new_f(*args, **kwds):
            import cpyrit.util
            try:
                import cpyrit.pckttools
            except cpyrit.util.ScapyImportError:
                sys.stderr.write("(Skipped: Scapy not installed) ")
            else:
                f(*args, **kwds)
        new_f.func_name = f.func_name
        new_f.__doc__ = f.__doc__
        return new_f
    return check_pkttools


class FilesystemFunctions(object):

    def getStorage(self):
        return cpyrit.storage.getStorage('file://' + self.storage_path)

    def corrupt(self, storage):
        # Destroy some passwords
        keys = list(storage.passwords.iterkeys())
        for i in xrange(13):
            key = random.choice(keys)
            # This is specific to storage.FSPasswordStore
            filename = os.path.join(storage.passwords.pwfiles[key], key)
            filename += '.pw'
            if i % 3 == 0:
                # Delete the workunit without deleting the results.
                # Should cause a reference error
                del storage.passwords[key]
            else:
                with open(filename, 'r+b') as f:
                    # Overwrite either part of the header or part of the file
                    if i % 2 == 0:
                        f.seek(4)
                    f.write('x')
            keys.remove(key)
            if len(keys) == 0:
                break
        # Destroy some results
        keys = list(storage.essids.iterkeys('test'))
        for i in xrange(13):
            key = random.choice(keys)
            # This is specific to storage.FSEssidStore
            filename = os.path.join(storage.essids.essids['test'][0], key)
            filename += '.pyr'
            with open(filename, 'r+b') as f:
                if i % 2 == 0:
                    f.seek(4)
                f.write('x')
            keys.remove(key)
            if len(keys) == 0:
                break


class BaseTestCase(unittest.TestCase):

    handshakes = (('wpapsk-linksys.dump.gz', 'linksys',
                   '00:0b:86:c2:a4:85', '00:13:ce:55:98:ef', 'dictionary'),
                  ('wpa2psk-linksys.dump.gz', 'linksys',
                   '00:0b:86:c2:a4:85', '00:13:ce:55:98:ef', 'dictionary'),
                  ('wpa2psk-2WIRE972.dump.gz', '2WIRE972',
                   '00:40:10:20:00:03', '00:18:41:9c:a4:a0', 'helium02'),
                  ('wpa2psk-MOM1.dump.gz', 'MOM1',
                   '00:21:29:72:a3:19', '00:21:00:ab:55:a9', 'MOM12345'),
                  ('wpa2psk-Red_Apple.dump.gz', 'Red Apple',
                   '00:1d:7e:2c:b1:af', '00:0e:35:72:1a:98', 'password'),
                  ('wpapsk-virgin_broadband.dump.gz', 'virgin broadband',
                   '00:22:3f:1b:2e:e6', '00:1f:e2:a0:a1:21', 'preinstall'))

    def setUp(self):
        self.storage_path = tempfile.mkdtemp()
        self.tempfile1 = os.path.join(self.storage_path, 'testfile1')
        self.tempfile2 = os.path.join(self.storage_path, 'testfile2')
        self.cli = pyrit_cli.Pyrit_CLI()
        self.cli.verbose = False

    def tearDown(self):
        shutil.rmtree(self.storage_path)

    def _createPasswords(self, filename):
        test_passwds = ['test123%i' % i for i in xrange(5000 - 5)]
        test_passwds += ['dictionary', 'helium02', 'MOM12345', \
                         'preinstall', 'password']
        random.shuffle(test_passwds)
        with cpyrit.util.AsyncFileWriter(filename) as f:
            f.write('\n'.join(test_passwds))
        return test_passwds

    def _createDatabase(self, storage):
        self.cli.create_essid(storage, 'linksys')
        self._createPasswords(self.tempfile1)
        self.cli.import_passwords(storage, self.tempfile1)

    def _computeFakeDatabase(self, storage, essid):
        self.cli.create_essid(storage, essid)
        for key, passwords in storage.passwords.iteritems():
            storage.essids[essid, key] = [(pw, 'x' * 32) for pw in passwords]

    def _computeDatabase(self, storage, essid):
        self.cli.create_essid(storage, essid)
        l = 0
        with cpyrit.cpyrit.StorageIterator(storage, essid) as dbiter:
            for results in dbiter:
                l += len(results)
        self.assertEqual(l, 5000)

    def _testHandshake(self, filename, essid, ap, sta, passwd, aes=False):
        parser = cpyrit.pckttools.PacketParser(filename)
        with cpyrit.cpyrit.PassthroughIterator(essid, (passwd,)) as cp:
            solution = cp.next()
        auths = parser[ap][sta].getAuthentications()
        for auth in parser[ap][sta].getAuthentications():
            with cpyrit.pckttools.AuthCracker(auth, aes) as cracker:
                cracker.enqueue(solution)
            if cracker.solution == passwd:
                break
        else:
            self.fail('Did not detect passphrase in "%s"' % filename)


class TestCase(BaseTestCase):

    def testListEssids(self):
        storage = self.getStorage()
        self._createDatabase(storage)
        self.cli.list_essids(storage)

    def testCreateAndDeleteEssid(self):
        storage = self.getStorage()
        # EssidStore should be empty
        self.assertEqual(len(storage.essids), 0)
        self.assertFalse('testessid' in storage.essids)
        # Add one ESSID
        self.cli.create_essid(storage, essid='testessid')
        self.assertEqual(len(storage.essids), 1)
        self.assertTrue('testessid' in storage.essids)
        # Adding it second time should not cause an error
        self.cli.create_essid(storage, 'testessid')
        self.cli.delete_essid(storage, 'testessid', confirm=False)
        # EssidStore should be empty again
        self.assertEqual(len(storage.essids), 0)
        self.assertTrue('testessid' not in storage.essids)

    def testImportPasswords(self):
        storage = self.getStorage()
        self.assertEqual(len(storage.passwords), 0)
        # valid_passwds should get accepted, short_passwds ignored
        valid_passwds = ['test123%i' % i for i in xrange(100000)]
        short_passwds = ['x%i' % i for i in xrange(30000)]
        test_passwds = valid_passwds + short_passwds
        random.shuffle(test_passwds)
        with cpyrit.util.AsyncFileWriter(self.tempfile1) as f:
            f.write('\n'.join(test_passwds))
        self.cli.import_passwords(storage, self.tempfile1)
        new_passwds = set()
        for key, pwset in storage.passwords.iteritems():
            new_passwds.update(pwset)
        self.assertEqual(new_passwds, set(valid_passwds))
        # There should be no duplicates
        random.shuffle(test_passwds)
        with cpyrit.util.FileWrapper(self.tempfile1, 'a') as f:
            f.write('\n')
            f.write('\n'.join(test_passwds))
        self.cli.import_passwords(storage, self.tempfile1)
        new_passwds = set()
        i = 0
        for key, pwset in storage.passwords.iteritems():
            new_passwds.update(pwset)
            i += len(pwset)
        self.assertEqual(i, len(valid_passwds))
        self.assertEqual(new_passwds, set(valid_passwds))

    @requires_pckttools()
    def testAttackDB(self):
        storage = self.getStorage()
        self._createDatabase(storage)
        self._computeDatabase(storage, 'linksys')
        self.cli.attack_db(storage, 'wpapsk-linksys.dump.gz')

    @requires_pckttools()
    def testAttackCowpatty(self):
        storage = self.getStorage()
        self._createDatabase(storage)
        self._computeDatabase(storage, 'linksys')
        self.cli.export_cowpatty(storage, 'linksys', self.tempfile1)
        self.cli.attack_cowpatty('wpapsk-linksys.dump.gz', self.tempfile1)

    @requires_pckttools()
    def testAttackBatch(self):
        storage = self.getStorage()
        self._createPasswords(self.tempfile1)
        self.cli.import_passwords(storage, self.tempfile1)
        self.cli.attack_batch(storage, 'wpapsk-linksys.dump.gz')

    def testPassthrough(self):
        storage = self.getStorage()
        self._createDatabase(storage)
        self.cli.passthrough('linksys', self.tempfile1, self.tempfile2)
        fileresults = []
        for results in cpyrit.util.CowpattyFile(self.tempfile2):
            fileresults.extend(results)
        dbresults = []
        with cpyrit.cpyrit.StorageIterator(storage, 'linksys', \
                                            yieldNewResults=True) as dbiter:
            for results in dbiter:
                dbresults.extend(results)
        self.assertEqual(sorted(fileresults), sorted(dbresults))

    def testBatch(self):
        storage = self.getStorage()
        test_passwds = self._createPasswords(self.tempfile1)
        self.cli.import_passwords(storage, self.tempfile1)
        self.cli.create_essid(storage, 'test1234')
        self.cli.batchprocess(storage)
        self.assertEqual(len(storage.passwords), \
                         storage.essids.keycount('test1234'))
        keys = list(storage.essids.iterkeys('test1234'))
        for key in keys:
            self.assertTrue(key in storage.passwords)
        for key in storage.passwords:
            self.assertTrue(key in keys)
            passwds = storage.passwords[key]
            r = storage.essids['test1234', key]
            self.assertTrue(sorted((pw for pw, pmk in r)) == sorted(passwds))

    def testBatchWithFile(self):
        storage = self.getStorage()
        test_passwds = self._createPasswords(self.tempfile1)
        self.cli.import_passwords(storage, self.tempfile1)
        self.cli.create_essid(storage, 'test1234')
        self.cli.batchprocess(storage, 'test1234', self.tempfile1)
        self.assertEqual(len(storage.passwords), \
                         storage.essids.keycount('test1234'))
        fileresults = []
        for results in cpyrit.util.CowpattyFile(self.tempfile1):
            fileresults.extend(results)
        dbresults = []
        with cpyrit.cpyrit.StorageIterator(storage, 'test1234', \
                                            yieldNewResults=False) as dbiter:
            for results in dbiter:
                dbresults.extend(results)
        self.assertEqual(sorted(fileresults), sorted(dbresults))

    def testEval(self):
        storage = self.getStorage()
        self._createDatabase(storage)
        self._computeFakeDatabase(storage, 'test1')
        self._computeFakeDatabase(storage, 'test2')
        self.cli.eval_results(storage)

    def testVerify(self):
        storage = self.getStorage()
        self._createDatabase(storage)
        self._computeDatabase(storage, 'test')
        # Should be OK
        self.cli.verify(storage)
        keys = list(storage.essids.iterkeys('test'))
        for i in xrange(25):
            key = random.choice(keys)
            results = storage.essids['test', key]
            corrupted = tuple((pw, 'x' * 32) for pw, pmk in results)
            storage.essids['test', key] = corrupted
        # Should fail
        self.assertRaises(pyrit_cli.PyritRuntimeError, \
                          self.cli.verify, storage)

    def testCheckDB(self):
        storage = self.getStorage()
        self._createDatabase(storage)
        self._computeFakeDatabase(storage, 'test')
        self.corrupt(storage)
        # Should fail but repair
        self.assertRaises(pyrit_cli.PyritRuntimeError, \
                          self.cli.checkdb, storage, False)
        # Should now be OK
        self.cli.checkdb(storage, False)

    def testExportPasswords(self):
        storage = self.getStorage()
        test_passwds = self._createPasswords(self.tempfile1)
        self.cli.import_passwords(storage, self.tempfile1)
        self.cli.export_passwords(storage, self.tempfile1)
        with cpyrit.util.FileWrapper(self.tempfile1) as f:
            new_passwds = map(str.strip, f.readlines())
        self.assertEqual(sorted(test_passwds), sorted(new_passwds))

    def testExportCowpatty(self):
        storage = self.getStorage()
        self._createDatabase(storage)
        self._computeDatabase(storage, 'test')
        self.cli.export_cowpatty(storage, 'test', self.tempfile1)
        fileresults = []
        for results in cpyrit.util.CowpattyFile(self.tempfile1):
            fileresults.extend(results)
        dbresults = []
        with cpyrit.cpyrit.StorageIterator(storage, 'test', \
                                         yieldNewResults=False) as dbiter:
            for results in dbiter:
                dbresults.extend(results)
        self.assertEqual(sorted(fileresults), sorted(dbresults))

    def testExportHashdb(self):
        storage = self.getStorage()
        self._createDatabase(storage)
        self._computeFakeDatabase(storage, 'test')
        os.unlink(self.tempfile1)
        self.cli.export_hashdb(storage, self.tempfile1)


class RPCTestCase(TestCase, FilesystemFunctions):

    def getStorage(self):
        return cpyrit.storage.getStorage('http://127.0.0.1:17934')

    def setUp(self):
        TestCase.setUp(self)
        self.backend = FilesystemFunctions.getStorage(self)
        self.server = cpyrit.storage.StorageRelay(self.backend, \
                                                  iface='127.0.0.1')

    def tearDown(self):
        self.server.shutdown()
        TestCase.tearDown(self)

    def corrupt(self, storage):
        # Corrupt backing storage instead...
        FilesystemFunctions.corrupt(self, self.backend)


class DatabaseTestCase(TestCase):

    def getStorage(self):
        return cpyrit.storage.getStorage('sqlite:///:memory:')

    def corrupt(self, storage):
        conn = storage.engine.connect()
        # Destroy some passwords
        keys = list(storage.passwords.iterkeys())
        tbl = cpyrit.storage.passwords_table
        for i in xrange(13):
            key = random.choice(keys)
            sql = tbl.update().where(tbl.c._key == key)
            if i % 2 == 0:
                buf = 'x'
            else:
                buf = 'PAW2x'
            sql = sql.values(collection_buffer=buf)
            conn.execute(sql)
            keys.remove(key)
            if len(keys) == 0:
                break
        # Destroy some results
        keys = list(storage.essids.iterkeys('test'))
        tbl = cpyrit.storage.results_table
        for i in xrange(13):
            key = random.choice(keys)
            if i % 3 == 0:
                # Delete workunit
                # Should cause a reference-error
                sql = tbl.delete().where(tbl.c._key == key)
            else:
                # Corrupt it
                sql = tbl.update().where(tbl.c._key == key)
                if i % 2 == 0:
                    buf = 'x'
                else:
                    buf = 'PYR2xxxxxyyyyyzzz'
                sql = sql.values(results_buffer=buf)
            conn.execute(sql)
            keys.remove(key)
            if len(keys) == 0:
                break


class FilesystemTestCase(TestCase, FilesystemFunctions):

    def testListCores(self):
        self.cli.list_cores()

    def testPrintHelp(self):
        self.cli.print_help()

    def testSelfTest(self):
        self.cli.selftest(timeout=3)

    def testBenchmark(self):
        self.cli.benchmark(timeout=3)

    @requires_pckttools()
    def testHandshakes(self):
        for filename, essid, ap, sta, passwd in self.handshakes:
            self._testHandshake(filename, essid, ap, sta, passwd)

    @requires_pckttools()
    def testAnalyze(self):
        self.cli.analyze(capturefile='wpapsk-linksys.dump.gz')
        self.cli.analyze(capturefile='wpa2psk-linksys.dump.gz')
        self.cli.analyze(capturefile='wpa2psk-MOM1.dump.gz')
        self.cli.analyze(capturefile='wpa2psk-2WIRE972.dump.gz')
        self.cli.analyze(capturefile='wpapsk-virgin_broadband.dump.gz')

    @requires_pckttools()
    def testStripCapture(self):
        self.cli.stripCapture('wpapsk-linksys.dump.gz', self.tempfile1)
        parser = self.cli._getParser(self.tempfile1)
        self.assertTrue('00:0b:86:c2:a4:85' in parser)
        self.assertEqual(parser['00:0b:86:c2:a4:85'].essid, 'linksys')
        self.assertTrue('00:13:ce:55:98:ef' in parser['00:0b:86:c2:a4:85'])
        self.assertTrue(parser['00:0b:86:c2:a4:85'].isCompleted())
        for filename, essid, ap, sta, passwd in self.handshakes:
            self.cli.stripCapture(filename, self.tempfile1)
            self._testHandshake(self.tempfile1, essid, ap, sta, passwd)

    @requires_pckttools()
    def testStripLive(self):
        self.cli.stripLive('wpa2psk-linksys.dump.gz', self.tempfile1)
        parser = self.cli._getParser(self.tempfile1)
        self.assertTrue('00:0b:86:c2:a4:85' in parser)
        self.assertEqual(parser['00:0b:86:c2:a4:85'].essid, 'linksys')
        self.assertTrue('00:13:ce:55:98:ef' in parser['00:0b:86:c2:a4:85'])
        self.assertTrue(parser['00:0b:86:c2:a4:85'].isCompleted())
        for filename, essid, ap, sta, passwd in self.handshakes:
            self.cli.stripLive(filename, self.tempfile1)
            self._testHandshake(self.tempfile1, essid, ap, sta, passwd)

    @requires_pckttools()
    def testAttackPassthrough(self):
        self._createPasswords(self.tempfile1)
        self.cli.attack_passthrough(self.tempfile1, 'wpapsk-linksys.dump.gz')
        self.cli.attack_passthrough(self.tempfile1, 'wpa2psk-linksys.dump.gz', \
                                    use_aes=True)


def _runTests(case):
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(case)
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()

if __name__ == "__main__":
    print "Testing with filesystem-storage..."
    if not _runTests(FilesystemTestCase):
        sys.exit(1)

    # should have been imported by cpyrit.storage
    if 'sqlalchemy' not in sys.modules:
        print "SQLAlchemy seems to be unavailable; skipping all tests..."
    else:
        print "Testing with database-storage..."
        if not _runTests(DatabaseTestCase):
            sys.exit(1)

    print "Testing with RPC-storage..."
    if not _runTests(RPCTestCase):
        sys.exit(1)
