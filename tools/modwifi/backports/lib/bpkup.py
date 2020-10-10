import subprocess, os

class KupError(Exception):
    pass
class ExecutionError(KupError):
    def __init__(self, errcode):
        self.error_code = errcode

def _check(process):
    if process.returncode != 0:
        raise ExecutionError(process.returncode)

def mkdir(path):
    cmd = ['kup', 'mkdir', path]
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

    return stdout

def ls(path=None):
    cmd = ['kup', 'ls', path]
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

    return stdout

def put(tar_bz2, signed_tar, path):
    cmd = ['kup', 'put', tar_bz2, signed_tar, path]
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

    return stdout
