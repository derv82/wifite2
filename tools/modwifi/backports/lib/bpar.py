import subprocess, os

class ArError(Exception):
    pass
class ExecutionError(ArError):
    def __init__(self, errcode):
        self.error_code = errcode

def print_data(input_file, out_file, tree=None):
    cmd = ['ar', 'p', input_file, 'data.tar.gz']
    process = subprocess.Popen(cmd,
                               stdout=out_file, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    if process.returncode != 0:
        raise ExecutionError(process.returncode)
