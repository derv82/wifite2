#!/usr/bin/env bash

#
#  Added my personal automation settinngs to showcase what options may be feeded by parameters.
#  These settings is setting which attacks to run, tinme consumtion on each attach, fauling/timeout
#  parameters, as well as power (to ensure thee accesspoints are in range and quality for an incoming attack)
#
#  But also other nifty parameters/options, like a "infinity" switch, avoid attacking targets in db.
#  --skip-crack is used to save time, as we can do that later with the --crack option.
#  For informational purposes, manufacturers are parsed in real-time with "--showm" and bssid with "--showb"
#
#  "--reaver" is specified for WPS and PIXIE parsing, "--kill" is set to kill possible interference.
#  while I also use "-2" for 2,5ghz, rather than "-ab" (all bands) which increases scanner time.
#
#  "--power" is set to ensure the targets are in good quality (in range) for a faster runthrough.
#
#  So, enjoy!
#

python3 wifite.py --skip-crack --reaver -2 --showm --showb --kill --wpat 160 --pmkid-timeout 100 --wps-time 120 --no-nullpin --wps --power 28 -p 100 -inf --wps-timeout 50 --wps-fails 10 -ic
