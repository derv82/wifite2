#!/bin/sh

#echo "** Starting flake8 tests .."
#sleep 2
#sh tests/test_flake8.sh
#sleep 2
clear

echo "** Starting unittest/pytest .."
sleep 2
python3 -m unittest discover tests -v
sleep 2
echo "** runtests.sh test script at the end"
