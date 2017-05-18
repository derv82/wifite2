#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import time
from subprocess import Popen, PIPE

from Color import Color
from Configuration import Configuration


class Process(object):
    ''' Represents a running/ran process '''

    @staticmethod
    def devnull():
        ''' Helper method for opening devnull '''
        return open('/dev/null', 'w')

    @staticmethod
    def call(command, cwd=None, shell=False):
        '''
            Calls a command (either string or list of args).
            Returns tuple:
                (stdout, stderr)
        '''
        if type(command) != str or ' ' in command or shell:
            shell = True
            if Configuration.verbose > 1:
                Color.pe("\n {C}[?] {W} Executing (Shell): {B}%s{W}" % command)
        else:
            shell = False
            if Configuration.verbose > 1:
                Color.pe("\n {C}[?]{W} Executing: {B}%s{W}" % command)

        pid = Popen(command, cwd=cwd, stdout=PIPE, stderr=PIPE, shell=shell)
        pid.wait()
        (stdout, stderr) = pid.communicate()

        if Configuration.verbose > 1 and stdout.strip() != '':
            Color.pe("{P} [stdout] %s{W}" % '\n [stdout] '.join(stdout.split('\n')))
        if Configuration.verbose > 1 and stderr.strip() != '':
            Color.pe("{P} [stderr] %s{W}" % '\n [stderr] '.join(stderr.split('\n')))

        return (stdout, stderr)

    @staticmethod
    def exists(program):
        ''' Checks if program is installed on this system '''
        p = Process(['which', program])
        stdout = p.stdout().strip()
        stderr = p.stderr().strip()

        if stdout == '' and stderr == '':
            return False

        return True

    def __init__(self, command, devnull=False, stdout=PIPE, stderr=PIPE, cwd=None, bufsize=0):
        ''' Starts executing command '''

        if type(command) == str:
            # Commands have to be a list
            command = command.split(' ')

        self.command = command

        if Configuration.verbose > 1:
            Color.pe("\n {C}[?] {W} Executing: {B}%s{W}" % ' '.join(command))

        self.out = None
        self.err = None
        if devnull:
            sout = Process.devnull()
            serr = Process.devnull()
        else:
            sout = stdout
            serr = stderr

        self.start_time = time.time()

        self.pid = Popen(command, stdout=sout, stderr=serr, cwd=cwd, bufsize=bufsize)

    def __del__(self):
        '''
            Ran when object is GC'd.
            If process is still running at this point, it should die.
        '''
        if self.pid and self.pid.poll() == None:
            self.interrupt()

    def stdout(self):
        ''' Waits for process to finish, returns stdout output '''
        self.get_output()
        if Configuration.verbose > 1 and self.out.strip() != '':
            Color.pe("{P} [stdout] %s{W}" % '\n [stdout] '.join(self.out.split('\n')))
        return self.out

    def stderr(self):
        ''' Waits for process to finish, returns stderr output '''
        self.get_output()
        if Configuration.verbose > 1 and self.err.strip() != '':
            Color.pe("{P} [stderr] %s{W}" % '\n [stderr] '.join(self.err.split('\n')))
        return self.err

    def stdoutln(self):
        return self.pid.stdout.readline()

    def stderrln(self):
        return self.pid.stderr.readline()

    def get_output(self):
        ''' Waits for process to finish, sets stdout & stderr '''
        if self.pid.poll() == None:
            self.pid.wait()
        if self.out == None:
            (self.out, self.err) = self.pid.communicate()

    def poll(self):
        ''' Returns exit code if process is dead, otherwise "None" '''
        return self.pid.poll()

    def wait(self):
        self.pid.wait()

    def running_time(self):
        ''' Returns number of seconds since process was started '''
        return int(time.time() - self.start_time)

    def interrupt(self):
        '''
            Send interrupt to current process.
            If process fails to exit within 1 second, terminates it.
        '''
        from signal import SIGINT, SIGTERM
        from os import kill
        from time import sleep
        try:
            pid = self.pid.pid
            kill(pid, SIGINT)

            wait_time = 0  # Time since Interrupt was sent
            while self.pid.poll() == None:
                # Process is still running
                wait_time += 0.1
                sleep(0.1)
                if wait_time > 1:
                    # We waited over 1 second for process to die
                    # Terminate it and move on
                    kill(pid, SIGTERM)
                    self.pid.terminate()
                    break

        except OSError, e:
            if 'No such process' in e.__str__():
                return
            raise e  # process cannot be killed


if __name__ == '__main__':
    p = Process('ls')
    print p.stdout(), p.stderr()
    p.interrupt()

    # Calling as list of arguments
    (out, err) = Process.call(['ls', '-lah'])
    print out, err

    print '\n---------------------\n'

    # Calling as string
    (out, err) = Process.call('ls -l | head -2')
    print out, err

    print '"reaver" exists:', Process.exists('reaver')

    # Test on never-ending process
    p = Process('yes')
    # After program loses reference to instance in 'p', process dies.

