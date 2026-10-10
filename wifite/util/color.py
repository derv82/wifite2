#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys


class Color:
    """ Helper object for easily printing colored text to the terminal. """

    # Basic console colors
    colors = {
        'W': '\033[0m',   # white (normal)
        'R': '\033[31m',  # red
        'G': '\033[32m',  # green
        'O': '\033[33m',  # orange
        'B': '\033[34m',  # blue
        'P': '\033[35m',  # purple
        'C': '\033[36m',  # cyan
        'GR': '\033[37m',  # gray
        'D': '\033[2m'    # dims current color. {W} resets.
    }

    # Helper string replacements
    replacements = {
        '{+}': ' {W}{D}[{W}{G}+{W}{D}]{W}',
        '{!}': ' {O}[{R}!{O}]{W}',
        '{?}': ' {W}[{C}?{W}]'
    }

    last_sameline_length = 0

    # ── Kalidroid MiniTerminal mode ───────────────────────────────────────────
    # The Kalidroid Android app streams wifite's stdout into a MiniTerminal: an
    # append-only scrollback view, NOT a terminal emulator. Carriage-return
    # redraws (the live attack progress lines) and clear-line escapes therefore
    # render as overwritten/garbled text. When --kalidroid is set these are
    # flattened into discrete, newline-terminated lines (throttled so a
    # per-second timer doesn't flood the view) and the clear-line ops become
    # no-ops. ANSI colours are kept — the MiniTerminal parses SGR codes.
    kalidroid = False
    _kalidroid_last_emit = 0.0
    _kalidroid_last_line = ''
    _KALIDROID_MIN_INTERVAL = 0.4  # seconds between same-line progress emits

    @staticmethod
    def p(text):
        """
        Prints text using colored format on same line.
        Example:
            Color.p('{R}This text is red. {W} This text is white')
        """
        if Color.kalidroid:
            Color._p_kalidroid(text)
            return
        sys.stdout.write(Color.s(text))
        sys.stdout.flush()
        if '\r' in text:
            text = text[text.rfind('\r') + 1:]
            Color.last_sameline_length = len(text)
        else:
            Color.last_sameline_length += len(text)

    @staticmethod
    def _p_kalidroid(text):
        """
        Same as [p] but for the Kalidroid MiniTerminal: a carriage-return
        same-line update (e.g. the per-second attack progress line) is emitted
        as its own newline-terminated line so the append-only scrollback stays
        readable. Identical consecutive redraws and bursts faster than
        [_KALIDROID_MIN_INTERVAL] are dropped so timers don't flood the view.
        Plain text (no '\\r') — including the newline-terminated Color.pl prints
        — passes through unchanged, so final/result lines are never throttled.
        """
        if '\r' not in text:
            sys.stdout.write(Color.s(text))
            sys.stdout.flush()
            return
        content = text[text.rfind('\r') + 1:].rstrip('\n')
        if content.strip() == '':
            return  # bare '\r' / whitespace-only clear carries no information
        import time
        now = time.time()
        if (content == Color._kalidroid_last_line
                or now - Color._kalidroid_last_emit < Color._KALIDROID_MIN_INTERVAL):
            return
        Color._kalidroid_last_emit = now
        Color._kalidroid_last_line = content
        sys.stdout.write(Color.s(content) + '\n')
        sys.stdout.flush()

    @staticmethod
    def pl(text):
        """Prints text using colored format with trailing new line."""
        Color.p('%s\n' % text)
        Color.last_sameline_length = 0

    @staticmethod
    def pe(text):
        """
        Prints text using colored format with
        leading and trailing new line to STDERR.
        """
        sys.stderr.write(Color.s('%s\n' % text))
        Color.last_sameline_length = 0

    @staticmethod
    def s(text):
        """ Returns colored string """
        output = text
        for (key, value) in list(Color.replacements.items()):
            output = output.replace(key, value)
        for (key, value) in list(Color.colors.items()):
            output = output.replace('{%s}' % key, value)
        return output

    @staticmethod
    def clear_line():
        # MiniTerminal has no cursor to rewind — the '\r<spaces>\r' erase would
        # just append blanks. The flattened progress lines stand on their own.
        if Color.kalidroid:
            Color.last_sameline_length = 0
            return
        spaces = ' ' * Color.last_sameline_length
        sys.stdout.write('\r%s\r' % spaces)
        sys.stdout.flush()
        Color.last_sameline_length = 0

    @staticmethod
    def clear_entire_line():
        if Color.kalidroid:
            Color.last_sameline_length = 0
            return
        import shutil
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
        Color.p('\r' + (' ' * columns) + '\r')

    @staticmethod
    def pattack(attack_type, target, attack_name, progress):
        """
        Prints a one-liner for an attack.
        Includes attack type (WEP/WPA),
        target ESSID & power, attack type, and progress.
        ESSID (Pwr) Attack_Type: Progress
        e.g.: Router2G (23db) WEP replay attack: 102 IVs
        """
        essid = '{C}%s{W}' % target.essid if target.essid_known else '{O}unknown{W}'
        # Convert power to string to avoid type errors in string formatting
        power_str = str(target.power) if target.power is not None else '??'
        Color.p('\r{+} {G}%s{W} ({C}%sdb{W}) {G}%s {C}%s{W}: %s ' % (
            essid, power_str, attack_type, attack_name, progress))

    # Exceptions whose stack traces are never useful to the user
    _BENIGN_ERRORS = (
        'No targets found',
        'Enabled interface not in monitor mode',
        'did not find any wireless interfaces',
    )

    @staticmethod
    def pexception(exception):
        """Prints an exception. Includes stack trace if necessary."""
        exc_str = str(exception)
        exc_type = type(exception).__name__
        Color.pl('\n{!} {R}%s: {O}%s' % (exc_type, exc_str))

        # Don't dump trace for well-known non-bug errors.
        for msg in Color._BENIGN_ERRORS:
            if msg in exc_str:
                return

        from ..config import Configuration
        if Configuration.verbose > 0 or Configuration.print_stack_traces:
            Color.pl('\n{!} {O}Full stack trace below')
            from traceback import format_exc
            Color.p('\n{!}    ')
            err = format_exc().strip()
            err = err.replace('\n', '\n{!} {C}   ')
            err = err.replace('  File', '{W}File')
            err = err.replace('  Exception: ', '{R}Exception: {O}')
            Color.pl(err)
        else:
            Color.pl('{!} {D}Run with {W}-v{D} to see the full stack trace{W}')


if __name__ == '__main__':
    Color.pl('{R}Testing{G}One{C}Two{P}Three{W}Done')
    print((Color.s('{C}Testing{P}String{W}')))
    Color.pl('{+} Good line')
    Color.pl('{!} Danger')
