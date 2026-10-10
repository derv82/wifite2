#!/bin/sh

clear

echo "** Starting pytest .."
sleep 2
pytest tests/ -v
echo "** runtests.sh test script at the end"
