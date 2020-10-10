#!/usr/bin/env python
""" Patch utility to apply unified diffs

    Brute-force line-by-line non-recursive parsing 

    Copyright (c) 2008-2012 anatoly techtonik
    Available under the terms of MIT license

    Project home: http://code.google.com/p/python-patch/


    $Id$
    $HeadURL$
"""

__author__ = "anatoly techtonik <techtonik@gmail.com>"
__version__ = "1.12.12dev"

import copy
import logging
import re
import sys

try:
  # cStringIO doesn't support unicode in 2.5
  from StringIO import StringIO
except ImportError:
  # StringIO has been renamed to 'io' in 3.x
  from io import StringIO

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

from os.path import exists, isfile, abspath
import os
import shutil


_open = open

if sys.version_info >= (3,):
    # Open files with universal newline support but no newline translation (3.x)
    def open(filename, mode='r'):
        return _open(filename, mode, newline='')
else:
    # Open files with universal newline support but no newline translation (2.x)
    def open(filename, mode='r'):
        return _open(filename, mode + 'b')

    # Python 3.x has changed iter.next() to be next(iter) instead, so for
    # backwards compatibility, we'll just define a next() function under 2.x
    def next(iter):
        return iter.next()


#------------------------------------------------
# Logging is controlled by logger named after the
# module name (e.g. 'patch' for patch.py module)

debugmode = False

logger = logging.getLogger(__name__)

debug = logger.debug
info = logger.info
warning = logger.warning

class NullHandler(logging.Handler):
  """ Copied from Python 2.7 to avoid getting
      `No handlers could be found for logger "patch"`
      http://bugs.python.org/issue16539
  """
  def handle(self, record):
    pass
  def emit(self, record):
    pass
  def createLock(self):
    self.lock = None

logger.addHandler(NullHandler())

#------------------------------------------------
# Constants for Patch/PatchSet types

DIFF = PLAIN = "plain"
GIT = "git"
HG = MERCURIAL = "mercurial"
SVN = SUBVERSION = "svn"
# mixed type is only actual when PatchSet contains
# Patches of different type
MIXED = MIXED = "mixed"


#------------------------------------------------
# Helpers (these could come with Python stdlib)

# x...() function are used to work with paths in
# cross-platform manner - all paths use forward
# slashes even on Windows.

def xisabs(filename):
  """ Cross-platform version of `os.path.isabs()`
      Returns True if `filename` is absolute on
      Linux, OS X or Windows.
  """
  if filename.startswith('/'):     # Linux/Unix
    return True
  elif filename.startswith('\\'):  # Windows
    return True
  elif re.match(r'\w:[\\/]', filename): # Windows
    return True
  return False

def xnormpath(path):
  """ Cross-platform version of os.path.normpath """
  return os.path.normpath(path).replace(os.sep, '/')

def xstrip(filename):
  """ Make relative path out of absolute by stripping
      prefixes used on Linux, OS X and Windows.

      This function is critical for security.
  """
  while xisabs(filename):
    # strip windows drive with all slashes
    if re.match(r'\w:[\\/]', filename):
      filename = re.sub(r'^\w+:[\\/]+', '', filename)
    # strip all slashes
    elif re.match(r'[\\/]', filename):
      filename = re.sub(r'^[\\/]+', '', filename)
  return filename

#-----------------------------------------------
# Main API functions

def fromfile(filename):
  """ Parse patch file. If successful, returns
      PatchSet() object. Otherwise returns False.
  """
  patchset = PatchSet()
  debug("reading %s" % filename)
  fp = open(filename, "r")
  res = patchset.parse(fp)
  fp.close()
  if res == True:
    return patchset
  return False


def fromstring(s):
  """ Parse text string and return PatchSet()
      object (or False if parsing fails)
  """
  ps = PatchSet( StringIO(s) )
  if ps.errors == 0:
    return ps
  return False


def fromurl(url):
  """ Parse patch from an URL, return False
      if an error occured. Note that this also
      can throw urlopen() exceptions.
  """
  ps = PatchSet( urllib2.urlopen(url) )
  if ps.errors == 0:
    return ps
  return False


# --- Utility functions ---
# [ ] reuse more universal pathsplit()
def pathstrip(path, n):
  """ Strip n leading components from the given path """
  pathlist = [path]
  while os.path.dirname(pathlist[0]) != '':
    pathlist[0:1] = os.path.split(pathlist[0])
  return '/'.join(pathlist[n:])
# --- /Utility function ---


class Hunk(object):
  """ Parsed hunk data container (hunk starts with @@ -R +R @@) """

  def __init__(self):
    self.startsrc=None #: line count starts with 1
    self.linessrc=None
    self.starttgt=None
    self.linestgt=None
    self.invalid=False
    self.desc=''
    self.text=[]

#  def apply(self, estream):
#    """ write hunk data into enumerable stream
#        return strings one by one until hunk is
#        over
#
#        enumerable stream are tuples (lineno, line)
#        where lineno starts with 0
#    """
#    pass


class Patch(object):
  """ Patch for a single file """
  def __init__(self):
    self.source = None 
    self.target = None
    self.hunks = []
    self.hunkends = []
    self.header = []

    self.type = None


class PatchSet(object):

  def __init__(self, stream=None):
    # --- API accessible fields ---

    # name of the PatchSet (filename or ...)
    self.name = None
    # patch set type - one of constants
    self.type = None

    # list of Patch objects
    self.items = []
    self.top_header = ""

    self.errors = 0    # fatal parsing errors
    self.warnings = 0  # non-critical warnings
    # --- /API ---

    if stream:
      self.parse(stream)

  def __len__(self):
    return len(self.items)

  def parse(self, stream):
    """ parse unified diff
        return True on success
    """
    lineends = dict(lf=0, crlf=0, cr=0)
    nexthunkno = 0    #: even if index starts with 0 user messages number hunks from 1

    p = None
    hunk = None
    # hunkactual variable is used to calculate hunk lines for comparison
    hunkactual = dict(linessrc=None, linestgt=None)


    class wrapumerate(object):
      """Enumerate wrapper that uses boolean end of stream status instead of
      StopIteration exception, and properties to access line information.
      """

      def __init__(self, stream):
        self._exhausted = False
        self._lineno = False     # after end of stream equal to the num of lines
        self._line = False       # will be reset to False after end of stream
        self._iter = enumerate(stream)

      def next(self):
        """Try to read the next line and return True if it is available,
           False if end of stream is reached."""
        if self._exhausted:
          return False

        try:
          self._lineno, self._line = next(self._iter)
        except StopIteration:
          self._exhausted = True
          self._line = False
          return False
        return True
      # python 3 uses __next__ consistent with next(iter)
      __next__ = next

      @property
      def is_empty(self):
        return self._exhausted

      @property
      def line(self):
        return self._line

      @property
      def lineno(self):
        return self._lineno

    # define states (possible file regions) that direct parse flow
    headscan  = True  # start with scanning header
    filenames = False # lines starting with --- and +++

    hunkhead = False  # @@ -R +R @@ sequence
    hunkbody = False  #
    hunkskip = False  # skipping invalid hunk mode

    hunkparsed = False # state after successfully parsed hunk

    # regexp to match start of hunk, used groups - 1,3,4,6
    re_hunk_start = re.compile("^@@ -(\d+)(,(\d+))? \+(\d+)(,(\d+))? @@")
    
    self.errors = 0
    # temp buffers for header and filenames info
    header = []
    srcname = None
    tgtname = None

    # start of main cycle
    # each parsing block already has line available in fe.line
    fe = wrapumerate(stream)
    while next(fe):

      # -- deciders: these only switch state to decide who should process
      # --           line fetched at the start of this cycle
      if hunkparsed:
        hunkparsed = False
        if re_hunk_start.match(fe.line):
            hunkhead = True
        elif fe.line.startswith("--- "):
            filenames = True
        else:
            headscan = True
      # -- ------------------------------------

      # read out header
      if headscan:
        while not fe.is_empty and not fe.line.startswith("--- "):
            header.append(fe.line)
            self.top_header += fe.line
            next(fe)
        if fe.is_empty:
            if p == None:
              debug("no patch data found")  # error is shown later
              self.errors += 1
            else:
              info("%d unparsed bytes left at the end of stream" % len(''.join(header)))
              self.warnings += 1
              # TODO check for \No new line at the end.. 
              # TODO test for unparsed bytes
              # otherwise error += 1
            # this is actually a loop exit
            continue

        headscan = False
        # switch to filenames state
        filenames = True

      line = fe.line
      lineno = fe.lineno


      # hunkskip and hunkbody code skipped until definition of hunkhead is parsed
      if hunkbody:
        # [x] treat empty lines inside hunks as containing single space
        #     (this happens when diff is saved by copy/pasting to editor
        #      that strips trailing whitespace)
        if line.strip("\r\n") == "":
            debug("expanding empty line in a middle of hunk body")
            self.warnings += 1
            line = ' ' + line

        # process line first
        if re.match(r"^[- \+\\]", line):
            # gather stats about line endings
            if line.endswith("\r\n"):
              p.hunkends["crlf"] += 1
            elif line.endswith("\n"):
              p.hunkends["lf"] += 1
            elif line.endswith("\r"):
              p.hunkends["cr"] += 1
              
            if line.startswith("-"):
              hunkactual["linessrc"] += 1
            elif line.startswith("+"):
              hunkactual["linestgt"] += 1
            elif not line.startswith("\\"):
              hunkactual["linessrc"] += 1
              hunkactual["linestgt"] += 1
            hunk.text.append(line)
            # todo: handle \ No newline cases
        else:
            warning("invalid hunk no.%d at %d for target file %s" % (nexthunkno, lineno+1, p.target))
            # add hunk status node
            hunk.invalid = True
            p.hunks.append(hunk)
            self.errors += 1
            # switch to hunkskip state
            hunkbody = False
            hunkskip = True

        # check exit conditions
        if hunkactual["linessrc"] > hunk.linessrc or hunkactual["linestgt"] > hunk.linestgt:
            warning("extra lines for hunk no.%d at %d for target %s" % (nexthunkno, lineno+1, p.target))
            # add hunk status node
            hunk.invalid = True
            p.hunks.append(hunk)
            self.errors += 1
            # switch to hunkskip state
            hunkbody = False
            hunkskip = True
        elif hunk.linessrc == hunkactual["linessrc"] and hunk.linestgt == hunkactual["linestgt"]:
            # hunk parsed successfully
            p.hunks.append(hunk)
            # switch to hunkparsed state
            hunkbody = False
            hunkparsed = True

            # detect mixed window/unix line ends
            ends = p.hunkends
            if ((ends["cr"]!=0) + (ends["crlf"]!=0) + (ends["lf"]!=0)) > 1:
              warning("inconsistent line ends in patch hunks for %s" % p.source)
              self.warnings += 1
            if debugmode:
              debuglines = dict(ends)
              debuglines.update(file=p.target, hunk=nexthunkno)
              debug("crlf: %(crlf)d  lf: %(lf)d  cr: %(cr)d\t - file: %(file)s hunk: %(hunk)d" % debuglines)
            # fetch next line
            continue

      if hunkskip:
        if re_hunk_start.match(line):
          # switch to hunkhead state
          hunkskip = False
          hunkhead = True
        elif line.startswith("--- "):
          # switch to filenames state
          hunkskip = False
          filenames = True
          if debugmode and len(self.items) > 0:
            debug("- %2d hunks for %s" % (len(p.hunks), p.source))

      if filenames:
        if line.startswith("--- "):
          if srcname != None:
            # XXX testcase
            warning("skipping false patch for %s" % srcname)
            srcname = None
            # XXX header += srcname
            # double source filename line is encountered
            # attempt to restart from this second line
          re_filename = "^--- ([^\t]+)"
          match = re.match(re_filename, line)
          # todo: support spaces in filenames
          if match:
            srcname = match.group(1).strip()
          else:
            warning("skipping invalid filename at line %d" % lineno)
            self.errors += 1
            # XXX p.header += line
            # switch back to headscan state
            filenames = False
            headscan = True
        elif not line.startswith("+++ "):
          if srcname != None:
            warning("skipping invalid patch with no target for %s" % srcname)
            self.errors += 1
            srcname = None
            # XXX header += srcname
            # XXX header += line
          else:
            # this should be unreachable
            warning("skipping invalid target patch")
          filenames = False
          headscan = True
        else:
          if tgtname != None:
            # XXX seems to be a dead branch  
            warning("skipping invalid patch - double target at line %d" % lineno)
            self.errors += 1
            srcname = None
            tgtname = None
            # XXX header += srcname
            # XXX header += tgtname
            # XXX header += line
            # double target filename line is encountered
            # switch back to headscan state
            filenames = False
            headscan = True
          else:
            re_filename = "^\+\+\+ ([^\t]+)"
            match = re.match(re_filename, line)
            if not match:
              warning("skipping invalid patch - no target filename at line %d" % lineno)
              self.errors += 1
              srcname = None
              # switch back to headscan state
              filenames = False
              headscan = True
            else:
              if p: # for the first run p is None
                self.items.append(p)
              p = Patch()
              p.source = srcname
              srcname = None
              p.target = match.group(1).strip()
              p.header = header
              header = []
              # switch to hunkhead state
              filenames = False
              hunkhead = True
              nexthunkno = 0
              p.hunkends = lineends.copy()
              continue

      if hunkhead:
        match = re.match("^@@ -(\d+)(,(\d+))? \+(\d+)(,(\d+))? @@(.*)", line)
        if not match:
          if not p.hunks:
            warning("skipping invalid patch with no hunks for file %s" % p.source)
            self.errors += 1
            # XXX review switch
            # switch to headscan state
            hunkhead = False
            headscan = True
            continue
          else:
            # TODO review condition case
            # switch to headscan state
            hunkhead = False
            headscan = True
        else:
          hunk = Hunk()
          hunk.startsrc = int(match.group(1))
          hunk.linessrc = 1
          if match.group(3): hunk.linessrc = int(match.group(3))
          hunk.starttgt = int(match.group(4))
          hunk.linestgt = 1
          if match.group(6): hunk.linestgt = int(match.group(6))
          hunk.invalid = False
          hunk.desc = match.group(7)[1:].rstrip()
          hunk.text = []

          hunkactual["linessrc"] = hunkactual["linestgt"] = 0

          # switch to hunkbody state
          hunkhead = False
          hunkbody = True
          nexthunkno += 1
          continue

    # /while next(fe)

    if p:
      self.items.append(p)

    if not hunkparsed:
      if hunkskip:
        warning("warning: finished with errors, some hunks may be invalid")
      elif headscan:
        if len(self.items) == 0:
          warning("error: no patch data found!")
          return False
        else: # extra data at the end of file
          pass 
      else:
        warning("error: patch stream is incomplete!")
        self.errors += 1
        if len(self.items) == 0:
          return False

    if debugmode and len(self.items) > 0:
        debug("- %2d hunks for %s" % (len(p.hunks), p.source))

    # XXX fix total hunks calculation
    debug("total files: %d  total hunks: %d" % (len(self.items),
        sum(len(p.hunks) for p in self.items)))

    # ---- detect patch and patchset types ----
    for idx, p in enumerate(self.items):
      self.items[idx].type = self._detect_type(p)

    types = set([p.type for p in self.items])
    if len(types) > 1:
      self.type = MIXED
    else:
      self.type = types.pop()
    # --------

    self._normalize_filenames()
    
    return (self.errors == 0)

  def _detect_type(self, p):
    """ detect and return type for the specified Patch object
        analyzes header and filenames info

        NOTE: must be run before filenames are normalized
    """

    # check for SVN
    #  - header starts with Index:
    #  - next line is ===... delimiter
    #  - filename is followed by revision number
    # TODO add SVN revision
    if (len(p.header) > 1 and p.header[-2].startswith("Index: ")
          and p.header[-1].startswith("="*67)):
        return SVN

    # common checks for both HG and GIT
    DVCS = ((p.source.startswith('a/') or p.source == '/dev/null')
        and (p.target.startswith('b/') or p.target == '/dev/null'))

    # GIT type check
    #  - header[-2] is like "diff --git a/oldname b/newname"
    #  - header[-1] is like "index <hash>..<hash> <mode>"
    # TODO add git rename diffs and add/remove diffs
    #      add git diff with spaced filename
    # TODO http://www.kernel.org/pub/software/scm/git/docs/git-diff.html

    # detect the start of diff header - there might be some comments before
    if len(p.header) > 1:
      for idx in reversed(range(len(p.header))):
        if p.header[idx].startswith("diff --git"):
          break
      if re.match(r'diff --git a/[\w/.]+ b/[\w/.]+', p.header[idx]):
        if (idx+1 < len(p.header)
            and re.match(r'index \w{7}..\w{7} \d{6}', p.header[idx+1])):
          if DVCS:
            return GIT

    # HG check
    # 
    #  - for plain HG format header is like "diff -r b2d9961ff1f5 filename"
    #  - for Git-style HG patches it is "diff --git a/oldname b/newname"
    #  - filename starts with a/, b/ or is equal to /dev/null
    #  - exported changesets also contain the header
    #    # HG changeset patch
    #    # User name@example.com
    #    ...   
    # TODO add MQ
    # TODO add revision info
    if len(p.header) > 0:
      if DVCS and re.match(r'diff -r \w{12} .*', p.header[-1]):
        return HG
      if DVCS and p.header[-1].startswith('diff --git a/'):
        if len(p.header) == 1:  # native Git patch header len is 2
          return HG
        elif p.header[0].startswith('# HG changeset patch'):
          return HG

    return PLAIN


  def _normalize_filenames(self):
    """ sanitize filenames, normalizing paths, i.e.:
        1. strip a/ and b/ prefixes from GIT and HG style patches
        2. remove all references to parent directories (with warning)
        3. translate any absolute paths to relative (with warning)

        [x] always use forward slashes to be crossplatform
            (diff/patch were born as a unix utility after all)
        
        return None
    """
    for i,p in enumerate(self.items):
      p.source = xnormpath(p.source)
      p.target = xnormpath(p.target)

      sep = '/'  # sep value can be hardcoded, but it looks nice this way

      # references to parent are not allowed
      if p.source.startswith(".." + sep):
        warning("error: stripping parent path for source file patch no.%d" % (i+1))
        self.warnings += 1
        while p.source.startswith(".." + sep):
          p.source = p.source.partition(sep)[2]
      if p.target.startswith(".." + sep):
        warning("error: stripping parent path for target file patch no.%d" % (i+1))
        self.warnings += 1
        while p.target.startswith(".." + sep):
          p.target = p.target.partition(sep)[2]
      # absolute paths are not allowed
      if xisabs(p.source) or xisabs(p.target):
        warning("error: absolute paths are not allowed - file no.%d" % (i+1))
        self.warnings += 1
        if xisabs(p.source):
          warning("stripping absolute path from source name '%s'" % p.source)
          p.source = xstrip(p.source)
        if xisabs(p.target):
          warning("stripping absolute path from target name '%s'" % p.target)
          p.target = xstrip(p.target)
    
      self.items[i].source = p.source
      self.items[i].target = p.target


  def diffstat(self):
    """ calculate diffstat and return as a string
        Notes:
          - original diffstat ouputs target filename
          - single + or - shouldn't escape histogram
    """
    names = []
    insert = []
    delete = []
    namelen = 0
    maxdiff = 0  # max number of changes for single file
                 # (for histogram width calculation)
    for patch in self.items:
      i,d = 0,0
      for hunk in patch.hunks:
        for line in hunk.text:
          if line.startswith('+'):
            i += 1
          elif line.startswith('-'):
            d += 1
      names.append(patch.target)
      insert.append(i)
      delete.append(d)
      namelen = max(namelen, len(patch.target))
      maxdiff = max(maxdiff, i+d)
    output = ''
    statlen = len(str(maxdiff))  # stats column width
    for i,n in enumerate(names):
      # %-19s | %-4d %s
      format = " %-" + str(namelen) + "s | %" + str(statlen) + "s %s\n"

      hist = ''
      # -- calculating histogram --
      width = len(format % ('', '', ''))
      histwidth = max(2, 80 - width)
      if maxdiff < histwidth:
        hist = "+"*insert[i] + "-"*delete[i]
      else:
        iratio = (float(insert[i]) / maxdiff) * histwidth
        dratio = (float(delete[i]) / maxdiff) * histwidth

        # make sure every entry gets at least one + or -
        iwidth = 1 if 0 < iratio < 1 else int(iratio)
        dwidth = 1 if 0 < dratio < 1 else int(dratio)
        #print iratio, dratio, iwidth, dwidth, histwidth
        hist = "+"*int(iwidth) + "-"*int(dwidth)
      # -- /calculating +- histogram --
      output += (format % (names[i], insert[i] + delete[i], hist))
 
    output += (" %d files changed, %d insertions(+), %d deletions(-)"
               % (len(names), sum(insert), sum(delete)))
    return output


  def apply(self, strip=0, root=None):
    """ Apply parsed patch, optionally stripping leading components
        from file paths. `root` parameter specifies working dir.
        return True on success
    """
    if root:
      prevdir = os.getcwd()
      os.chdir(root)

    total = len(self.items)
    errors = 0
    if strip:
      # [ ] test strip level exceeds nesting level
      #   [ ] test the same only for selected files
      #     [ ] test if files end up being on the same level
      try:
        strip = int(strip)
      except ValueError:
        errors += 1
        warning("error: strip parameter '%s' must be an integer" % strip)
        strip = 0

    #for fileno, filename in enumerate(self.source):
    for i,p in enumerate(self.items):
      f2patch = p.source
      if strip:
        debug("stripping %s leading component from '%s'" % (strip, f2patch))
        f2patch = pathstrip(f2patch, strip)
      if not exists(f2patch):
        f2patch = p.target
        if strip:
          debug("stripping %s leading component from '%s'" % (strip, f2patch))
          f2patch = pathstrip(f2patch, strip)
        if not exists(f2patch):
          warning("source/target file does not exist:\n  --- %s\n  +++ %s" % (p.source, f2patch))
          errors += 1
          continue
      if not isfile(f2patch):
        warning("not a file - %s" % f2patch)
        errors += 1
        continue
      filename = f2patch

      debug("processing %d/%d:\t %s" % (i+1, total, filename))

      # validate before patching
      f2fp = open(filename)
      hunkno = 0
      hunk = p.hunks[hunkno]
      hunkfind = []
      hunkreplace = []
      validhunks = 0
      canpatch = False
      for lineno, line in enumerate(f2fp):
        if lineno+1 < hunk.startsrc:
          continue
        elif lineno+1 == hunk.startsrc:
          hunkfind = [x[1:].rstrip("\r\n") for x in hunk.text if x[0] in " -"]
          hunkreplace = [x[1:].rstrip("\r\n") for x in hunk.text if x[0] in " +"]
          #pprint(hunkreplace)
          hunklineno = 0

          # todo \ No newline at end of file

        # check hunks in source file
        if lineno+1 < hunk.startsrc+len(hunkfind)-1:
          if line.rstrip("\r\n") == hunkfind[hunklineno]:
            hunklineno+=1
          else:
            info("file %d/%d:\t %s" % (i+1, total, filename))
            info(" hunk no.%d doesn't match source file at line %d" % (hunkno+1, lineno))
            info("  expected: %s" % hunkfind[hunklineno])
            info("  actual  : %s" % line.rstrip("\r\n"))
            # not counting this as error, because file may already be patched.
            # check if file is already patched is done after the number of
            # invalid hunks if found
            # TODO: check hunks against source/target file in one pass
            #   API - check(stream, srchunks, tgthunks)
            #           return tuple (srcerrs, tgterrs)

            # continue to check other hunks for completeness
            hunkno += 1
            if hunkno < len(p.hunks):
              hunk = p.hunks[hunkno]
              continue
            else:
              break

        # check if processed line is the last line
        if lineno+1 == hunk.startsrc+len(hunkfind)-1:
          debug(" hunk no.%d for file %s  -- is ready to be patched" % (hunkno+1, filename))
          hunkno+=1
          validhunks+=1
          if hunkno < len(p.hunks):
            hunk = p.hunks[hunkno]
          else:
            if validhunks == len(p.hunks):
              # patch file
              canpatch = True
              break
      else:
        if hunkno < len(p.hunks):
          warning("premature end of source file %s at hunk %d" % (filename, hunkno+1))
          errors += 1

      f2fp.close()

      if validhunks < len(p.hunks):
        if self._match_file_hunks(filename, p.hunks):
          warning("already patched  %s" % filename)
        else:
          warning("source file is different - %s" % filename)
          errors += 1
      if canpatch:
        backupname = filename+".orig"
        if exists(backupname):
          warning("can't backup original file to %s - aborting" % backupname)
        else:
          import shutil
          shutil.move(filename, backupname)
          if self.write_hunks(backupname, filename, p.hunks):
            info("successfully patched %d/%d:\t %s" % (i+1, total, filename))
            os.unlink(backupname)
          else:
            errors += 1
            warning("error patching file %s" % filename)
            shutil.copy(filename, filename+".invalid")
            warning("invalid version is saved to %s" % filename+".invalid")
            # todo: proper rejects
            shutil.move(backupname, filename)

    if root:
      os.chdir(prevdir)

    # todo: check for premature eof
    return (errors == 0)


  def can_patch(self, filename):
    """ Check if specified filename can be patched. Returns None if file can
    not be found among source filenames. False if patch can not be applied
    clearly. True otherwise.

    :returns: True, False or None
    """
    filename = abspath(filename)
    for p in self.items:
      if filename == abspath(p.source):
        return self._match_file_hunks(filename, p.hunks)
    return None


  def _match_file_hunks(self, filepath, hunks):
    matched = True
    fp = open(abspath(filepath))

    class NoMatch(Exception):
      pass

    lineno = 1
    line = fp.readline()
    hno = None
    try:
      for hno, h in enumerate(hunks):
        # skip to first line of the hunk
        while lineno < h.starttgt:
          if not len(line): # eof
            debug("check failed - premature eof before hunk: %d" % (hno+1))
            raise NoMatch
          line = fp.readline()
          lineno += 1
        for hline in h.text:
          if hline.startswith("-"):
            continue
          if not len(line):
            debug("check failed - premature eof on hunk: %d" % (hno+1))
            # todo: \ No newline at the end of file
            raise NoMatch
          if line.rstrip("\r\n") != hline[1:].rstrip("\r\n"):
            debug("file is not patched - failed hunk: %d" % (hno+1))
            raise NoMatch
          line = fp.readline()
          lineno += 1

    except NoMatch:
      matched = False
      # todo: display failed hunk, i.e. expected/found

    fp.close()
    return matched


  def patch_stream(self, instream, hunks):
    """ Generator that yields stream patched with hunks iterable
    
        Converts lineends in hunk lines to the best suitable format
        autodetected from input
    """

    # todo: At the moment substituted lineends may not be the same
    #       at the start and at the end of patching. Also issue a
    #       warning/throw about mixed lineends (is it really needed?)

    hunks = iter(hunks)

    srclineno = 1

    lineends = {'\n':0, '\r\n':0, '\r':0}
    def get_line():
      """
      local utility function - return line from source stream
      collecting line end statistics on the way
      """
      line = instream.readline()
        # 'U' mode works only with text files
      if line.endswith("\r\n"):
        lineends["\r\n"] += 1
      elif line.endswith("\n"):
        lineends["\n"] += 1
      elif line.endswith("\r"):
        lineends["\r"] += 1
      return line

    for hno, h in enumerate(hunks):
      debug("hunk %d" % (hno+1))
      # skip to line just before hunk starts
      while srclineno < h.startsrc:
        yield get_line()
        srclineno += 1

      for hline in h.text:
        # todo: check \ No newline at the end of file
        if hline.startswith("-") or hline.startswith("\\"):
          get_line()
          srclineno += 1
          continue
        else:
          if not hline.startswith("+"):
            get_line()
            srclineno += 1
          line2write = hline[1:]
          # detect if line ends are consistent in source file
          if sum([bool(lineends[x]) for x in lineends]) == 1:
            newline = [x for x in lineends if lineends[x] != 0][0]
            yield line2write.rstrip("\r\n")+newline
          else: # newlines are mixed
            yield line2write
     
    for line in instream:
      yield line


  def write_hunks(self, srcname, tgtname, hunks):
    src = open(srcname, "r")
    tgt = open(tgtname, "w")

    debug("processing target file %s" % tgtname)

    tgt.writelines(self.patch_stream(src, hunks))

    tgt.close()
    src.close()
    # [ ] TODO: add test for permission copy
    shutil.copymode(srcname, tgtname)
    return True



if __name__ == "__main__":
  from optparse import OptionParser
  from os.path import exists
  import sys

  opt = OptionParser(usage="1. %prog [options] unified.diff\n"
                    "       2. %prog [options] http://host/patch\n"
                    "       3. %prog [options] -- < unified.diff",
                     version="python-patch %s" % __version__)
  opt.add_option("-q", "--quiet", action="store_const", dest="verbosity",
                                  const=0, help="print only warnings and errors", default=1)
  opt.add_option("-v", "--verbose", action="store_const", dest="verbosity",
                                  const=2, help="be verbose")
  opt.add_option("--debug", action="store_true", dest="debugmode", help="debug mode")
  opt.add_option("--diffstat", action="store_true", dest="diffstat",
                                           help="print diffstat and exit")
  opt.add_option("-d", "--directory", metavar='DIR',
                                           help="specify root directory for applying patch")
  opt.add_option("-p", "--strip", type="int", metavar='N', default=0,
                                           help="strip N path components from filenames")
  (options, args) = opt.parse_args()

  if not args and sys.argv[-1:] != ['--']:
    opt.print_version()
    opt.print_help()
    sys.exit()
  readstdin = (sys.argv[-1:] == ['--'] and not args)

  debugmode = options.debugmode

  verbosity_levels = {0:logging.WARNING, 1:logging.INFO, 2:logging.DEBUG}
  loglevel = verbosity_levels[options.verbosity]
  logformat = "%(message)s"
  if debugmode:
    loglevel = logging.DEBUG
    logformat = "%(levelname)8s %(message)s"
  logger.setLevel(loglevel)
  loghandler = logging.StreamHandler()
  loghandler.setFormatter(logging.Formatter(logformat))
  logger.addHandler(loghandler)


  if readstdin:
    patch = PatchSet(sys.stdin)
  else:
    patchfile = args[0]
    urltest = patchfile.split(':')[0]
    if (':' in patchfile and urltest.isalpha()
        and len(urltest) > 1): # one char before : is a windows drive letter
      patch = fromurl(patchfile)
    else:
      if not exists(patchfile) or not isfile(patchfile):
        sys.exit("patch file does not exist - %s" % patchfile)
      patch = fromfile(patchfile)

  if options.diffstat:
    print(patch.diffstat())
    sys.exit(0)

  #pprint(patch)
  patch.apply(options.strip, root=options.directory) or sys.exit(-1)

  # todo: document and test line ends handling logic - patch.py detects proper line-endings
  #       for inserted hunks and issues a warning if patched file has incosistent line ends
