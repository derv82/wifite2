#!/usr/bin/env python
# -*- coding: utf-8 -*-

import contextlib
import re
import shlex
import shutil
import time
import signal
import os
import atexit
import threading
import subprocess
import weakref
from subprocess import Popen, PIPE, DEVNULL
from ..util.color import Color
from ..config import Configuration
from ..util.logger import log_debug, log_info, log_warning, log_error


class ProcessManager:
    """Global process manager to track and cleanup all processes"""
    _instance = None
    _lock = threading.RLock()  # Reentrant lock to prevent deadlocks during nested cleanup

    # Maximum number of concurrent processes
    MAX_PROCESSES = 100

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._processes = []
                    cls._instance._registered_cleanup = False
        return cls._instance

    def register_process(self, process):
        """Register a process for cleanup tracking"""
        with self._lock:
            # Check if approaching limit and trigger cleanup
            if len(self._processes) >= self.MAX_PROCESSES:
                log_warning('ProcessManager', f'Process limit reached ({len(self._processes)}/{self.MAX_PROCESSES}), triggering cleanup')
                if Configuration.verbose > 0:
                    Color.pl(f'\n{{!}} {{O}}Warning: Process limit reached ({len(self._processes)}/{self.MAX_PROCESSES}), triggering cleanup{{W}}')

                # Identify and remove finished processes
                finished = [p for p in self._processes if hasattr(p, 'is_running') and not p.is_running()]
                if finished:
                    log_info('ProcessManager', f'Removing {len(finished)} finished process(es) from registry')
                    if Configuration.verbose > 1:
                        Color.pl(f'{{+}} {{C}}Removing {len(finished)} finished process(es){{W}}')
                    for p in finished:
                        self._processes.remove(p)

                # Force-kill oldest processes if still over limit
                if len(self._processes) >= self.MAX_PROCESSES:
                    oldest = self._processes[:10]
                    log_warning('ProcessManager', f'Force-killing {len(oldest)} oldest process(es) to stay under limit')
                    if Configuration.verbose > 0:
                        Color.pl(f'{{!}} {{O}}Force-killing {len(oldest)} oldest process(es){{W}}')
                    for p in oldest:
                        try:
                            p.force_kill()
                        except Exception as e:
                            log_debug('ProcessManager', f'force_kill failed during limit enforcement: {e}')
                    self._processes = self._processes[10:]

            self._processes.append(process)
            log_debug('ProcessManager', f'Registered process (total: {len(self._processes)}/{self.MAX_PROCESSES})')
            if not self._registered_cleanup:
                atexit.register(self.cleanup_all)
                self._registered_cleanup = True
                log_debug('ProcessManager', 'Registered atexit cleanup handler')

    def unregister_process(self, process):
        with self._lock:
            try:
                self._processes.remove(process)
            except ValueError:
                pass
            log_debug('ProcessManager', f'Unregistered process (remaining: {len(self._processes)})')

    def cleanup_all(self):
        with self._lock:
            process_count = len(self._processes)
            if process_count > 0:
                log_info('ProcessManager', f'Cleaning up {process_count} registered process(es)')
            for process in list(self._processes):
                try:
                    process.force_kill()
                except (ProcessLookupError, OSError):
                    pass  # Process already exited
                except Exception as e:
                    log_debug('ProcessManager', f'Error during process cleanup: {str(e)}')
            self._processes.clear()
            if process_count > 0:
                log_info('ProcessManager', 'Process cleanup complete')


class Process:
    """ Represents a running/ran process with enhanced cleanup """

    @staticmethod
    def devnull():
        """ Helper method returning subprocess.DEVNULL constant (no file handle to leak) """
        return DEVNULL

    # Cache of resolved full tool paths to avoid repeated shutil.which() calls
    _tool_path_cache: dict = {}

    @staticmethod
    def _resolve_tool(name: str) -> str:
        """Resolve a bare tool name to its absolute path using shutil.which().

        Raises FileNotFoundError if the tool cannot be found on PATH, preventing
        partial-path subprocess calls that depend on a potentially manipulated $PATH.
        Results are cached for the lifetime of the process.
        """
        if name in Process._tool_path_cache:
            return Process._tool_path_cache[name]
        full_path = shutil.which(name)
        if full_path is None:
            raise FileNotFoundError(f"Required tool not found on PATH: '{name}'")
        Process._tool_path_cache[name] = full_path
        log_debug('Process', f"Resolved tool '{name}' → '{full_path}'")
        return full_path

    @staticmethod
    def run_simple(cmd: list, timeout: int = 5) -> subprocess.CompletedProcess:
        """Safe replacement for bare subprocess.run() calls scattered across the codebase.

        Resolves the executable to a full path (SEC-004), logs the call at DEBUG
        level so it appears in the wifite log, and passes through capture_output
        and text defaults that callers previously set inline.

        Args:
            cmd:     Command as a list of strings. The first element is resolved
                     via shutil.which(); remaining elements are passed unchanged.
            timeout: Seconds before the subprocess is killed (default 5).

        Returns:
            subprocess.CompletedProcess with .stdout / .stderr / .returncode.

        Raises:
            FileNotFoundError: If the executable cannot be found on PATH.
        """
        if not cmd:
            raise ValueError('run_simple: cmd must be a non-empty list')
        resolved = [Process._resolve_tool(cmd[0])] + cmd[1:]
        log_debug('Process', f'run_simple: {resolved}')
        if Configuration.verbose > 1:
            Color.pe(f'\n {{C}}[?]{{W}} Executing: {{B}}{" ".join(resolved)}{{W}}')
        return subprocess.run(resolved, capture_output=True, text=True, timeout=timeout)

    @staticmethod
    def call(command, cwd=None, shell=False, timeout=30):
        """ Calls a command (either string or list of args). Returns (stdout, stderr).

        Args:
            command: Command string or list of args.
            cwd: Working directory for the command.
            shell: Deprecated, ignored. All commands run without shell.
            timeout: Seconds before the subprocess is killed. Default 30. None for no timeout.

        String commands are always split via shlex before being passed to Popen.
        """
        if shell:
            log_warning('Process', 'Process.call(): shell=True is ignored for security; command will be split via shlex')

        if isinstance(command, str):
            if Configuration.verbose > 1:
                Color.pe(f'\n {{C}}[?]{{W}} Executing: {{B}}{command}{{W}}')
            command = shlex.split(command)
        else:
            if Configuration.verbose > 1:
                Color.pe(f'\n {{C}}[?]{{W}} Executing: {{B}}{command}{{W}}')

        with Popen(command, cwd=cwd, stdout=PIPE, stderr=PIPE) as pid:
            try:
                out, err = pid.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                pid.kill()
                out, err = pid.communicate()

        if isinstance(out, bytes):
            out = out.decode('utf-8', errors='replace')
        if isinstance(err, bytes):
            err = err.decode('utf-8', errors='replace')

        if Configuration.verbose > 1 and out.strip():
            Color.pe('{P} [stdout] %s{W}' % '\n [stdout] '.join(out.strip().split('\n')))
        if Configuration.verbose > 1 and err.strip():
            Color.pe('{P} [stderr] %s{W}' % '\n [stderr] '.join(err.strip().split('\n')))

        return out, err

    @staticmethod
    def exists(program):
        if Configuration.initialized and program in Configuration.existing_commands:
            return Configuration.existing_commands[program]

        exist = shutil.which(program) is not None
        if Configuration.initialized:
            Configuration.existing_commands.update({program: exist})
        return exist

    def __init__(self, command, devnull=False, stdout=PIPE, stderr=PIPE, cwd=None, bufsize=0, stdin=PIPE):
        if isinstance(command, str):
            command = shlex.split(command)

        self.command = command
        self._cleaned_up = False
        self._communicated = False
        self._manager = ProcessManager()
        self._devnull_handles = []

        cmd_str = " ".join(command) if isinstance(command, list) else str(command)
        # Avoid logging sensitive arguments in clear text
        try:
            safe_cmd_str = re.sub(r"(-k)\s+\S+", r"\1 ****", cmd_str)
            safe_cmd_str = re.sub(r"(--key)\s+\S+", r"\1 ****", safe_cmd_str)
            safe_cmd_str = re.sub(r"(--password)\s+\S+", r"\1 ****", safe_cmd_str)
            safe_cmd_str = re.sub(r"(--psk)\s+\S+", r"\1 ****", safe_cmd_str)
        except (re.error, AttributeError):
            safe_cmd_str = cmd_str
        log_debug('Process', f'Creating process: {safe_cmd_str}')
        
        if Configuration.verbose > 1:
            Color.pe(f'\n {{C}}[?] {{W}} Executing: {{B}}{" ".join(command)}{{W}}')

        # Check file descriptor limit before creating process
        if Process.check_fd_limit():
            log_warning('Process', 'Delaying process creation due to high FD usage')
            if Configuration.verbose > 0:
                Color.pl('{!} {O}Delaying process creation due to high FD usage{W}')
            time.sleep(0.1)  # Brief delay to allow cleanup to complete

        self.out = None
        self.err = None
        if devnull:
            log_debug('Process', 'Redirecting stdout/stderr to devnull')
            sout = DEVNULL
            serr = DEVNULL
        else:
            sout = stdout
            serr = stderr

        self.start_time = time.time()

        try:
            self.pid = Popen(command, stdout=sout, stderr=serr, stdin=stdin, cwd=cwd, bufsize=bufsize)
            log_info('Process', f'Process created successfully (PID: {self.pid.pid})')
        except OSError as e:
            if e.errno == 24:  # Too many open files
                log_error('Process', 'Too many open files (errno 24), triggering emergency cleanup', e)
                if Configuration.verbose > 0:
                    Color.pl('{!} {O}Too many open files, triggering emergency cleanup{W}')
                ProcessManager().cleanup_all()
                Process.cleanup_zombies()
                time.sleep(0.1)
                self.pid = Popen(command, stdout=sout, stderr=serr, stdin=stdin, cwd=cwd, bufsize=bufsize)
                log_info('Process', f'Process created after emergency cleanup (PID: {self.pid.pid})')
            else:
                log_error('Process', f'Failed to create process: {str(e)}', e)
                raise

        self._manager.register_process(self)
        # weakref.finalize fires when the object is GC'd, even during interpreter
        # shutdown when __del__ can no longer safely acquire locks or import modules.
        self._finalizer = weakref.finalize(self, Process._do_finalize, self.pid)

    @staticmethod
    def _do_finalize(pid):
        """Backup cleanup: called by weakref.finalize if cleanup() was never invoked."""
        try:
            if pid.poll() is None:
                pid.kill()
                pid.wait()
        except (OSError, ValueError):
            pass
        for stream in (pid.stdin, pid.stdout, pid.stderr):
            if stream:
                with contextlib.suppress(OSError):
                    stream.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def get_output(self, timeout=10):
        """ Wait for process to finish, safely collect output """
        if self._communicated:
            return self.out, self.err

        try:
            self.out, self.err = self.pid.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.force_kill()
            try:
                self.out, self.err = self.pid.communicate(timeout=2)
            except (OSError, ValueError):
                self.out, self.err = b'', b''

        if isinstance(self.out, bytes):
            self.out = self.out.decode('utf-8', errors='replace')
        if isinstance(self.err, bytes):
            self.err = self.err.decode('utf-8', errors='replace')

        self._communicated = True

        # Explicitly close pipes
        for stream in (self.pid.stdin, self.pid.stdout, self.pid.stderr):
            if stream and not stream.closed:
                try:
                    stream.close()
                except Exception as e:
                    log_debug('Process', f'Error closing stream in get_output: {e}')

        # Close any devnull handles
        for fh in self._devnull_handles:
            try:
                fh.close()
            except Exception as e:
                log_debug('Process', f'Error closing devnull handle: {e}')
        self._devnull_handles.clear()

        return self.out, self.err

    def stdout(self):
        self.get_output()
        if Configuration.verbose > 1 and self.out and self.out.strip():
            Color.pe('{P} [stdout] %s{W}' % '\n [stdout] '.join(self.out.strip().split('\n')))
        return self.out

    def stderr(self):
        self.get_output()
        if Configuration.verbose > 1 and self.err and self.err.strip():
            Color.pe('{P} [stderr] %s{W}' % '\n [stderr] '.join(self.err.strip().split('\n')))
        return self.err

    def stdoutln(self):
        if getattr(self.pid, "stdout", None):
            return self.pid.stdout.readline()
        return b''

    def stderrln(self):
        if getattr(self.pid, "stderr", None):
            return self.pid.stderr.readline()
        return b''

    def stdin(self, text):
        if getattr(self.pid, "stdin", None):
            try:
                self.pid.stdin.write(text.encode('utf-8'))
                self.pid.stdin.flush()
            except (OSError, ValueError):
                pass

    def poll(self):
        return self.pid.poll()

    def wait(self):
        self.pid.wait()
        rc = self.pid.returncode
        if rc != 0:
            log_debug('Process', 'Process exited with code %d (ran %ds)' % (
                rc, self.running_time()))

    def running_time(self):
        return int(time.time() - self.start_time)

    def cleanup(self):
        """Safely clean up subprocess and file descriptors"""
        if getattr(self, '_cleaned_up', False):
            return

        log_debug('Process', 'Starting process cleanup')
        
        try:
            if hasattr(self, 'pid') and self.pid and self.pid.poll() is None:
                log_debug('Process', 'Interrupting running process during cleanup')
                self.interrupt()
        except (OSError, ValueError) as e:
            log_debug('Process', f'Error interrupting process: {str(e)}')
            pass

        # Ensure all descriptors closed
        streams_closed = 0
        for stream in (getattr(self.pid, 'stdin', None), getattr(self.pid, 'stdout', None), getattr(self.pid, 'stderr', None)):
            if stream and not stream.closed:
                try:
                    stream.close()
                    streams_closed += 1
                except (OSError, ValueError) as e:
                    log_debug('Process', f'Error closing stream: {str(e)}')
                    pass

        if streams_closed > 0:
            log_debug('Process', f'Closed {streams_closed} stream(s)')

        # Close devnull handles
        devnull_closed = 0
        for fh in getattr(self, '_devnull_handles', []):
            try:
                fh.close()
                devnull_closed += 1
            except (OSError, ValueError) as e:
                log_debug('Process', f'Error closing devnull handle: {str(e)}')
                pass
        self._devnull_handles = []

        if devnull_closed > 0:
            log_debug('Process', f'Closed {devnull_closed} devnull handle(s)')

        try:
            self._manager.unregister_process(self)
        except (OSError, ValueError) as e:
            log_debug('Process', f'Error unregistering process: {str(e)}')
            pass

        # Detach the weakref finalizer — cleanup already done above
        if hasattr(self, '_finalizer'):
            self._finalizer.detach()

        self._cleaned_up = True
        log_debug('Process', 'Process cleanup complete')

    def interrupt(self, wait_time=2.0):
        if not hasattr(self, 'pid') or not self.pid:
            return
        try:
            self._graceful_shutdown(wait_time)
        except (OSError, ValueError):
            try:
                self.pid.wait()
            except (OSError, ValueError):
                pass

    def _graceful_shutdown(self, wait_time):
        if self.pid.poll() is not None:
            return
        pid = self.pid.pid
        cmd = ' '.join(self.command) if isinstance(self.command, list) else str(self.command)

        if Configuration.verbose > 1:
            Color.pe(f'\n {{C}}[?] {{W}} sending interrupt to PID {pid} ({cmd})')

        try:
            os.kill(pid, signal.SIGINT)
        except OSError:
            return

        start_time = time.time()
        while self.pid.poll() is None and (time.time() - start_time) < wait_time:
            time.sleep(0.1)

        if self.pid.poll() is None:
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
            except OSError:
                pass

        if self.pid.poll() is None:
            try:
                os.kill(pid, signal.SIGKILL)
                self.pid.kill()
            except OSError:
                pass

        try:
            self.pid.wait()
        except (OSError, ValueError):
            pass

    def force_kill(self):
        if not hasattr(self, 'pid') or not self.pid:
            return
        try:
            if self.pid.poll() is None:
                self.pid.kill()
                self.pid.wait()
        except (OSError, ValueError):
            pass

    def is_running(self):
        return hasattr(self, 'pid') and self.pid and self.pid.poll() is None

    @staticmethod
    def cleanup_zombies():
        try:
            while True:
                pid, _ = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
        except (OSError, ValueError):
            pass

    # Cache for FD count to avoid filesystem scan on every process creation
    _fd_cache_time = 0
    _fd_cache_value = -1
    _FD_CACHE_TTL = 2.0  # seconds

    @staticmethod
    def get_open_fd_count():
        """Get current open file descriptor count from /proc/{pid}/fd (cached with TTL)"""
        now = time.time()
        if now - Process._fd_cache_time < Process._FD_CACHE_TTL:
            return Process._fd_cache_value
        try:
            proc_fd_dir = f'/proc/{os.getpid()}/fd'
            if os.path.exists(proc_fd_dir):
                Process._fd_cache_value = len(os.listdir(proc_fd_dir))
                Process._fd_cache_time = now
                return Process._fd_cache_value
        except OSError:
            pass
        Process._fd_cache_value = -1
        Process._fd_cache_time = now
        return -1

    @staticmethod
    def check_fd_limit():
        """Check if approaching file descriptor limit (80% of soft limit) and trigger cleanup"""
        try:
            import resource
            soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
            current = Process.get_open_fd_count()

            if current > 0:
                usage_percent = int(current/soft*100)
                log_debug('Process', f'FD usage: {current}/{soft} ({usage_percent}%)')
                
                if current > (soft * 0.8):
                    log_warning('Process', f'High file descriptor usage: {current}/{soft} ({usage_percent}%)')
                    if Configuration.verbose > 0:
                        Color.pl(f'\n{{!}} {{O}}Warning: High file descriptor usage ({current}/{soft}, {usage_percent}%){{W}}')

                    # Trigger cleanup
                    log_info('Process', 'Triggering automatic cleanup due to high FD usage')
                    if Configuration.verbose > 1:
                        Color.pl('{+} {C}Triggering automatic cleanup...{W}')
                    ProcessManager().cleanup_all()
                    Process.cleanup_zombies()

                    # Check again after cleanup
                    new_count = Process.get_open_fd_count()
                    freed = current - new_count
                    log_info('Process', f'FD cleanup complete: freed {freed} descriptors (now {new_count}/{soft})')
                    if Configuration.verbose > 1:
                        Color.pl(f'{{+}} {{C}}FD count after cleanup: {new_count}/{soft}{{W}}')

                    return True
        except Exception as e:
            log_debug('Process', f'Error checking FD limit: {str(e)}')
            pass
        return False


if __name__ == '__main__':
    Configuration.initialize(False)
    p = Process('ls')
    print(p.stdout())
    print(p.stderr())
    p.interrupt()

    out, err = Process.call(['ls', '-lah'])
    print(out, err)

    out, err = Process.call('ls -l')
    print(out, err)

    print(f'"reaver" exists: {Process.exists("reaver")}')

    p = Process('yes')
    print('Running yes...')
    time.sleep(1)
    print('yes should stop now')

