#!/bin/bash

echo "* Fetching a fresh OUI (manufacturers) list  ..."
get-oui -f new-ieee-oui.txt -u http://standards-oui.ieee.org/oui/oui.txt
