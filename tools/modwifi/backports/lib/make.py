#
# Small helper library to read and manipulate kernel Makefiles
#

import os, re

obj_line = re.compile(r'^obj-(?P<dep>[^\s+:=]*)\s*[+:]?=\s*(?P<tgt>[^\\]*)\s*(?P<cont>\\?)')

class MakeTree(object):
    def __init__(self, rootfile):
        self.basedir = os.path.dirname(rootfile)
        self.rootfile = os.path.basename(rootfile)
        self._no_syms = []
        self._walked = False
        self._found_makefiles = []

    def _check_for_sym(self, f, sym):
        # re-read Makefile to see if it declared this symbol ...
        r = re.compile('^%s-(y|objs)\s*[+:]?=' % sym)
        for l in open(os.path.join(self.basedir, f), 'r'):
            if r.match(l):
                # FIXME: check if symbol dependencies can be satisfied!
                return True
        return False

    def _walk(self, f=None, subdir='', sym=None):
        if self._walked:
            return
        if not os.path.exists(os.path.join(self.basedir, subdir, f)):
            #print "no %s" % os.path.join(self.basedir, subdir, f)
            assert not sym is None
            self._no_syms.append(sym)
            return
        self._found_makefiles.append(os.path.join(self.basedir, subdir, f))
        for l in open(os.path.join(self.basedir, subdir, f), 'r'):
            m = obj_line.match(l)
            if not m:
                continue
            dep = m.group('dep')
            if dep[:2] == '$(':
                if dep[-1] != ')':
                    raise Exception("Couldn't parse make dependency %s" % dep)
                dep = dep[2:-1]
            tgt = m.group('tgt')
            for t in tgt.strip().split():
                t = t.strip()
                if not t:
                    continue
                if t[-1] == '/':
                    self._walk(f='Makefile', subdir=os.path.join(subdir, t), sym=dep)
                elif t[-2:] == '.o':
                    t = t[:-2] + '.c'
                    if not os.path.exists(os.path.join(self.basedir, subdir, t)):
                        if not self._check_for_sym(os.path.join(subdir, f), t[:-2]):
                            self._no_syms.append(dep)
                else:
                    assert False
                # FIXME: consider continuation lines!

    def get_impossible_symbols(self):
        self._walk(self.rootfile)
        return self._no_syms

    def get_makefiles(self):
        self._walk(self.rootfile)
        return self._found_makefiles
