import subprocess, os

class GpgError(Exception):
    pass
class ExecutionError(GpgError):
    def __init__(self, errcode):
        self.error_code = errcode

def sign(input_file, extra_args=[]):
    cmd = ['gpg', '--sign']

    cmd.extend(extra_args)
    cmd.append(input_file)

    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True)
    stdout = process.communicate()[0]
    process.wait()
    if process.returncode != 0:
        raise ExecutionError(process.returncode)
    return stdout
