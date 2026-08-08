#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import signal
import os
import threading
from subprocess import Popen, PIPE, TimeoutExpired
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import queue

from ..util.color import Color
from ..config import Configuration


class AdvancedProcess(object):
    '''Advanced process management with threading, pooling, and timeout control'''

    # Process pool for reuse
    _process_pool = ThreadPoolExecutor(max_workers=10)
    _active_processes = {}
    _process_lock = threading.Lock()

    @staticmethod
    def devnull():
        '''Helper method for opening devnull'''
        return open('/dev/null', 'w')

    @staticmethod
    def call(command, cwd=None, shell=False, timeout=None, attempts=1):
        '''
        Call a command with timeout and retry logic.
        Returns tuple: (stdout, stderr, return_code, success)
        '''
        last_error = None

        for attempt in range(attempts):
            try:
                if attempt > 0:
                    Color.pl('{!} {O}Retry attempt %d/%d{W}' % (attempt, attempts))
                    time.sleep(1)

                if isinstance(command, str) and (' ' in command or shell):
                    shell = True
                    if Configuration.verbose > 1:
                        Color.pe('\n {C}[?] {W} Executing (Shell): {B}%s{W}' % command)
                else:
                    if Configuration.verbose > 1:
                        Color.pe('\n {C}[?]{W} Executing: {B}%s{W}' % command)

                pid = Popen(command, cwd=cwd, stdout=PIPE, stderr=PIPE, 
                           shell=shell, preexec_fn=os.setsid)

                if timeout:
                    try:
                        stdout, stderr = pid.communicate(timeout=timeout)
                    except TimeoutExpired:
                        os.killpg(os.getpgid(pid.pid), signal.SIGTERM)
                        Color.pl('{!} {R}Process timed out after %d seconds{W}' % timeout)
                        raise TimeoutError('Process exceeded timeout')
                else:
                    stdout, stderr = pid.communicate()

                # Python 3 compatibility
                if isinstance(stdout, bytes):
                    stdout = stdout.decode('utf-8', errors='ignore')
                if isinstance(stderr, bytes):
                    stderr = stderr.decode('utf-8', errors='ignore')

                if Configuration.verbose > 1:
                    if stdout and stdout.strip():
                        Color.pe('{P} [stdout] %s{W}' % '\n [stdout] '.join(stdout.strip().split('\n')))
                    if stderr and stderr.strip():
                        Color.pe('{P} [stderr] %s{W}' % '\n [stderr] '.join(stderr.strip().split('\n')))

                return (stdout, stderr, pid.returncode, True)

            except (TimeoutError, Exception) as e:
                last_error = str(e)
                if attempt == attempts - 1:
                    return ('', str(e), -1, False)

        return ('', last_error, -1, False)

    @staticmethod
    def exists(program, attempts=2):
        '''Check if program exists with retry'''
        for attempt in range(attempts):
            try:
                stdout, stderr, code, success = AdvancedProcess.call(
                    ['which', program], 
                    timeout=5
                )
                if success and stdout.strip():
                    return True
            except Exception:
                if attempt < attempts - 1:
                    time.sleep(0.5)
        return False

    def __init__(self, command, devnull=False, stdout=PIPE, stderr=PIPE, 
                 cwd=None, bufsize=0, stdin=PIPE, timeout=None, name=None):
        '''Initialize and start process with timeout support'''

        if isinstance(command, str):
            command = command.split(' ')

        self.command = command
        self.timeout = timeout
        self.name = name or ' '.join(command)
        self.start_time = time.time()
        self.out = None
        self.err = None
        self.return_code = None

        if Configuration.verbose > 1:
            Color.pe('\n {C}[?] {W} Executing: {B}%s{W}' % ' '.join(command))

        sout = Process.devnull() if devnull else stdout
        serr = Process.devnull() if devnull else stderr

        try:
            self.pid = Popen(command, stdout=sout, stderr=serr, stdin=stdin, 
                           cwd=cwd, bufsize=bufsize, preexec_fn=os.setsid)

            # Register process
            with self._process_lock:
                self._active_processes[self.pid.pid] = self

            if timeout:
                self._timeout_thread = threading.Thread(target=self._monitor_timeout)
                self._timeout_thread.daemon = True
                self._timeout_thread.start()

        except Exception as e:
            Color.pl('{!} {R}Failed to start process: %s{W}' % str(e))
            raise

    def _monitor_timeout(self):
        '''Monitor process for timeout'''
        time.sleep(self.timeout)
        if self.pid.poll() is None:
            Color.pl('{!} {R}Process timeout: %s{W}' % self.name)
            self.interrupt(wait_time=2.0)

    def __del__(self):
        '''Cleanup when object is destroyed'''
        try:
            if self.pid and self.pid.poll() is None:
                self.interrupt()
        except:
            pass

    def stdout(self):
        '''Get stdout with timeout'''
        self.get_output()
        if Configuration.verbose > 1 and self.out and self.out.strip():
            Color.pe('{P} [stdout] %s{W}' % '\n [stdout] '.join(self.out.strip().split('\n')))
        return self.out

    def stderr(self):
        '''Get stderr with timeout'''
        self.get_output()
        if Configuration.verbose > 1 and self.err and self.err.strip():
            Color.pe('{P} [stderr] %s{W}' % '\n [stderr] '.join(self.err.strip().split('\n')))
        return self.err

    def stdoutln(self):
        '''Read single line from stdout'''
        try:
            line = self.pid.stdout.readline()
            return line.decode('utf-8', errors='ignore') if isinstance(line, bytes) else line
        except Exception as e:
            Color.pl('{!} {R}Error reading stdout: %s{W}' % str(e))
            return ''

    def stderrln(self):
        '''Read single line from stderr'''
        try:
            line = self.pid.stderr.readline()
            return line.decode('utf-8', errors='ignore') if isinstance(line, bytes) else line
        except Exception as e:
            Color.pl('{!} {R}Error reading stderr: %s{W}' % str(e))
            return ''

    def stdin(self, text):
        '''Write to stdin'''
        if self.pid.stdin:
            try:
                self.pid.stdin.write(text.encode('utf-8'))
                self.pid.stdin.flush()
            except Exception as e:
                Color.pl('{!} {R}Error writing to stdin: %s{W}' % str(e))

    def get_output(self, timeout=None):
        '''Get process output with optional timeout'''
        if self.pid.poll() is None:
            try:
                if timeout:
                    self.pid.wait(timeout=timeout)
                else:
                    self.pid.wait()
            except TimeoutExpired:
                self.interrupt()
                raise TimeoutError('Process exceeded timeout')

        if self.out is None:
            try:
                self.out, self.err = self.pid.communicate(timeout=5)
            except TimeoutExpired:
                self.pid.kill()
                self.out, self.err = '', ''

        if isinstance(self.out, bytes):
            self.out = self.out.decode('utf-8', errors='ignore')
        if isinstance(self.err, bytes):
            self.err = self.err.decode('utf-8', errors='ignore')

        return (self.out, self.err)

    def poll(self):
        '''Check if process is running'''
        return self.pid.poll()

    def wait(self, timeout=None):
        '''Wait for process to complete'''
        try:
            self.pid.wait(timeout=timeout)
        except TimeoutExpired:
            self.interrupt()
            raise TimeoutError('Process wait timeout')

    def running_time(self):
        '''Get process runtime in seconds'''
        return int(time.time() - self.start_time)

    def interrupt(self, wait_time=2.0, force=False):
        '''Interrupt process gracefully or forcefully'''
        try:
            pid = self.pid.pid
            cmd = ' '.join(self.command) if isinstance(self.command, list) else self.command

            if Configuration.verbose > 1:
                Color.pe('\n {C}[?] {W} Sending SIGINT to PID %d (%s)' % (pid, cmd))

            os.killpg(os.getpgid(pid), signal.SIGINT)

            start_time = time.time()
            while self.pid.poll() is None and time.time() - start_time < wait_time:
                time.sleep(0.1)

            if self.pid.poll() is None:
                if Configuration.verbose > 1:
                    Color.pe('\n {C}[?] {W} Process didn\'t die, sending SIGKILL')
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                self.pid.terminate()

        except ProcessLookupError:
            pass
        except Exception as e:
            Color.pl('{!} {R}Error interrupting process: %s{W}' % str(e))
        finally:
            with self._process_lock:
                self._active_processes.pop(self.pid.pid, None)


# Backward compatibility
Process = AdvancedProcess


if __name__ == '__main__':
    Configuration.initialize(False)

    # Test basic execution
    p = AdvancedProcess('ls -lah', timeout=10)
    print(p.stdout())

    # Test with timeout
    stdout, stderr, code, success = AdvancedProcess.call('sleep 2', timeout=5)
    print('Command succeeded:', success)

    # Test program existence
    print('aircrack-ng exists:', AdvancedProcess.exists('aircrack-ng'))
