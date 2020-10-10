# simple tempdir wrapper object for 'with' statement
#
# Usage:
# with tempdir.tempdir() as tmpdir:
#     os.chdir(tmpdir)
#     do something
#

import tempfile, shutil

class tempdir(object):
    def __init__(self, suffix='', prefix='', dir=None, nodelete=False):
        self.suffix = ''
        self.prefix = ''
        self.dir = dir
        self.nodelete = nodelete

    def __enter__(self):
        self._name = tempfile.mkdtemp(suffix=self.suffix,
                                      prefix=self.prefix,
                                      dir=self.dir)
        return self._name

    def __exit__(self, type, value, traceback):
        if self.nodelete:
            print('not deleting directory %s!' % self._name)
        else:
            shutil.rmtree(self._name)
