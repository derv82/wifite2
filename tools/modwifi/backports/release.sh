#!/bin/bash
set -e

# FIXME: Specify the research branch of linux repository
./gentree.py --clean ../linux/ ../drivers/

echo "Creating archive ..."
tar -cf ../drivers.tar ../drivers/
