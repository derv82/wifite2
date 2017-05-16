#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import sys

class Color(object):
    ''' Helper object for easily printing colored text to the terminal. '''

    # Basic console colors
    colors = {
        'W' : '\033[0m',  # white (normal)
        'R' : '\033[31m', # red
        'G' : '\033[32m', # green
        'O' : '\033[33m', # orange
        'B' : '\033[34m', # blue
        'P' : '\033[35m', # purple
        'C' : '\033[36m', # cyan
        'GR': '\033[37m'  # gray
    }

    # Helper string replacements
    replacements = {
        '{+}': ' {W}[{G}+{W}]',
        '{!}': ' {O}[{R}!{O}]{W}',
        '{?}': ' {W}[{C}?{W}]'
    }

    last_sameline_length = 0

    @staticmethod
    def p(text):
        '''
            Prints text using colored format on same line.
            Example:
                Color.p("{R}This text is red. {W} This text is white")
        '''
        sys.stdout.write(Color.s(text))
        sys.stdout.flush()
        if '\r' in text:
            text = text[text.rfind('\r')+1:]
            Color.last_sameline_length = len(text)
        else:
            Color.last_sameline_length += len(text)

    @staticmethod
    def pl(text):
        '''
            Prints text using colored format with trailing new line.
        '''
        Color.p('%s\n' % text)
        Color.last_sameline_length = 0

    @staticmethod
    def pe(text):
        '''
            Prints text using colored format with leading and trailing new line to STDERR.
        '''
        sys.stderr.write(Color.s('%s\n' % text))
        Color.last_sameline_length = 0

    @staticmethod
    def s(text):
        ''' Returns colored string '''
        output = text
        for (key,value) in Color.replacements.iteritems():
            output = output.replace(key, value)
        for (key,value) in Color.colors.iteritems():
            output = output.replace("{%s}" % key, value)
        return output

    @staticmethod
    def clear_line():
        spaces = ' ' * Color.last_sameline_length
        sys.stdout.write('\r%s\r' % spaces)
        sys.stdout.flush()
        Color.last_sameline_length = 0

    @staticmethod
    def clear_entire_line():
        import os
        (rows, columns) = os.popen('stty size', 'r').read().split()
        Color.p("\r" + (" " * int(columns)) + "\r")

    @staticmethod
    def pattack(attack_type, target, attack_name, progress):
        '''
            Prints a one-liner for an attack
            Includes attack type (WEP/WPA), target BSSID/ESSID & power, attack type, and progress
            [name] ESSID (MAC @ Pwr) Attack_Type: Progress
            e.g.: [WEP] Router2G (00:11:22 @ 23db) replay attack: 102 IVs
        '''
        essid = "{C}%s{W}" % target.essid if target.essid_known else "{O}unknown{W}"
        Color.p("\r{+} {G}%s{W} ({C}%s @ %sdb{W}) {G}%s {C}%s{W}: %s " % (
            essid, target.bssid, target.power, attack_type, attack_name, progress))

if __name__ == '__main__':
    Color.pl("{R}Testing{G}One{C}Two{P}Three{W}Done")
    print Color.s("{C}Testing{P}String{W}")
    Color.pl("{+} Good line")
    Color.pl("{!} Danger")

