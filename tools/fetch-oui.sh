#!/bin/bash

#
# Fetches the latest additions to the OUI db (for manufacturers)
# which we parse by utilizing the "--showm" parameter in Wifite.
#
# more manufacturers in the list is more knowledge.
#

echo "* Fetching a fresh OUI (manufacturers) list  ..."
get-oui -f ieee-oui.txt -u http://standards-oui.ieee.org/oui/oui.txt
