#!/usr/bin/env python

import patch, sys

ps = patch.fromfile(sys.argv[1])
f = open('INFO', 'w')
f.write(''.join(ps.items[0].header))
f.close()

for p in ps.items:
    s = p.source[2:].replace('/', '_')
    f = open(s, 'w')
    f.write('--- %s\n' % p.source)
    f.write('+++ %s\n' % p.target)
    for h in p.hunks:
        f.write('@@ -%d,%d +%d,%d @@\n' % (
          h.startsrc, h.linessrc,
          h.starttgt, h.linestgt))
        f.write(''.join(h.text))
    f.close()
