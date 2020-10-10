import subprocess, os, sys, re
"""
Often enough Python code can grow to depend on binaries
on a system, you may also require only specific versions
of these. This small library helps with this. It also has
helpers for packages which we know to handle already.
"""

class ReqError(Exception):
    pass
class ExecutionError(ReqError):
    def __init__(self, errcode):
        self.error_code = errcode

class Req:
    "To be used for verifying binay package dependencies on Python code"
    def __init__(self):
        self.all_reqs_ok = True
        self.debug = False
    def enable_debug(self):
        self.debug = True
    def reqs_match(self):
        if self.all_reqs_ok:
            return True
        sys.stdout.write("You have unfulfilled binary requirements\n")
        return False
    def req_missing(self, program):
        self.all_reqs_ok = False
        sys.stdout.write("You need to have installed: %s\n" % program)
    def req_old_program(self, program, version_req):
        self.all_reqs_ok = False
        sys.stdout.write("You need to have installed: %s >= %s\n" % (program, version_req))
    def which(self, program):
        cmd = ['which', program]
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   close_fds=True, universal_newlines=True)
        stdout = process.communicate()[0]
        process.wait()
        if process.returncode != 0:
            raise ExecutionError(process.returncode)
        return stdout
    def req_exists(self, program):
        cmd = ['which', program]
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   close_fds=True, universal_newlines=True)
        stdout = process.communicate()[0]
        process.wait()
        if process.returncode == 0:
            return True
        return False
    def req_get_prog_version(self, program, version_query, version_pos):
        '''
        Suppose you have a binary that outputs:
        $ spatch --version
        spatch version 1.0.0-rc21 with Python support and with PCRE support

        Every program veries what it wants you to query it for a version string,
        prog_version() is designed so that you pass what the program expects for
        its version query, and the position you expect the version string to be
        on using python list.
        '''
        cmd = [program, version_query]
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   close_fds=True, universal_newlines=True)
        stdout = process.communicate()[0]
        process.wait()
        if process.returncode != 0:
            raise ExecutionError(process.returncode)
        if self.debug:
            sys.stdout.write("Running '%s' got us this break down:\n%s\n" %
                             (
                             ' '.join(cmd),
                             "\n".join(map(str, [[i, x] for i, x in enumerate(stdout.split())])),
                             ))
            sys.stdout.write("You are using for version: %s\n" % stdout.split()[version_pos])
            sys.stdout.write("Specifically your idx, element: %s\n" % ([[i, x] for i, x in enumerate(stdout.split())][version_pos]))
        return stdout.split()[version_pos]
    def __compute_rel_weight(self, rel_specs):
        weight = 0
        extra = 0
        sublevel = 0
        relmod = 0

        if self.debug:
            sys.stdout.write("VERSION       = %s\n" % rel_specs['VERSION'])
            sys.stdout.write("PATCHLEVEL    = %s\n" % rel_specs['PATCHLEVEL'])
            sys.stdout.write("SUBLEVEL      = %s\n" % rel_specs['SUBLEVEL'])
            sys.stdout.write("EXTRAVERSION  = %s\n" % rel_specs['EXTRAVERSION'])
            sys.stdout.write("RELMOD_UPDATE = %s\n" % rel_specs['RELMOD_UPDATE'])

        if rel_specs['EXTRAVERSION'] != '':
            if ("." in rel_specs['EXTRAVERSION'] or
                    "rc" in rel_specs['EXTRAVERSION']):
                rc = rel_specs['EXTRAVERSION'].lstrip("-rc")
                if (rc == ""):
                    rc = 0
                else:
                    rc = int(rc) - 20
                extra = int(rc)
            else:
                extra = int(rel_specs['EXTRAVERSION']) + 10

        if rel_specs['SUBLEVEL'] != '':
            sublevel = int(rel_specs['SUBLEVEL'].lstrip(".")) * 20
        else:
            sublevel = 5

        if rel_specs['RELMOD_UPDATE'] != '':
            mod = rel_specs['RELMOD_UPDATE']
            if (mod == ""):
                mod = 0
            else:
                mod = int(mod)
            relmod = int(mod)

        weight = (int(rel_specs['VERSION'])    << 32) + \
                 (int(rel_specs['PATCHLEVEL']) << 16) + \
                 (sublevel   		       << 8 ) + \
                 (extra * 60) + (relmod * 2)

        return weight
    def req_get_rel_spec(self, rel):
        if "rc" in rel:
            m = re.match(r"v*(?P<VERSION>\d+)\.+"
                         "(?P<PATCHLEVEL>\d+)[.]*"
                         "(?P<SUBLEVEL>\d*)"
                         "(?P<EXTRAVERSION>[-rc]+\w*)\-*"
                         "(?P<RELMOD_UPDATE>\d*)[-]*",
                         rel)
        else:
            m = re.match(r"v*(?P<VERSION>\d+)\.+"
                         "(?P<PATCHLEVEL>\d+)[.]*"
                         "(?P<SUBLEVEL>\d*)[.]*"
                         "(?P<EXTRAVERSION>\w*)\-*"
                         "(?P<RELMOD_UPDATE>\d*)[-]*",
                         rel)
        if not m:
            return m
        rel_specs = m.groupdict()
        return rel_specs
    def compute_rel_weight(self, rel):
        rel_specs = self.req_get_rel_spec(rel)
        if not rel_specs:
            return 0
        return self.__compute_rel_weight(rel_specs)
    def linux_version_cmp(self, version_req, version):
        '''
        If the program follows the linux version style scheme you can
        use this to compare versions.
        '''
        weight_has = self.compute_rel_weight(version)
        weight_req = self.compute_rel_weight(version_req)

        if self.debug:
            sys.stdout.write("You have program weight: %s\n" % weight_has)
            sys.stdout.write("Required program weight: %s\n" % weight_req)

        if weight_has < weight_req:
            return -1
        return 0
    def require_version(self, program, version_query, version_req, version_pos, version_cmp):
        '''
        If you have a program version requirement you can specify it here,
        as for the other flags refer to prog_version.
        '''
        if not self.require(program):
            return False
        version = self.req_get_prog_version(program, version_query, version_pos)
        if self.debug:
            sys.stdout.write("Checking release specs and weight: for: %s\n" % program)
            sys.stdout.write("You have version: %s\n" % version)
            sys.stdout.write("Required version: %s\n" % version_req)
        if version_cmp(version_req, version) != 0:
            self.req_old_program(program, version_req)
            return False
        return True
    def require(self, program):
        if self.req_exists(program):
            return True
        self.req_missing(program)
        return False
    def require_hint(self, program, package_hint):
        if self.require(program):
            return True
        sys.stdout.write("Try installing the package: %s\n" % package_hint)
        return False
    def coccinelle(self, version):
        if self.require_version('spatch', '--version', version, 2, self.linux_version_cmp):
            return True
        sys.stdout.write("Try installing the package: coccinelle\n")
        sys.stdout.write("If that is too old go grab the code from source:\n\n")
        sys.stdout.write("git clone https://github.com/coccinelle/coccinelle.git\n\n")
        sys.stdout.write("To build you will need: ocaml ncurses-devel\n\n")
        sys.stdout.write("If on SUSE / OpenSUSE you will also need: ocaml-ocamldoc\n\n")
        return False
    def kup(self):
        if self.require('kup'):
            return True
        sys.stdout.write("Try installing the package: kup\n")
        sys.stdout.write("If your distribution lacks that go get from source:\n\n")
        sys.stdout.write("git clone git://git.kernel.org/pub/scm/utils/kup/kup.git\n\n")
        return False
    def make(self, version):
        return self.require_version('make', '--version', version, 2, self.linux_version_cmp)
    def gcc(self, version):
        return self.require_version('gcc', '--version', version, 3, self.linux_version_cmp)
