#!/usr/bin/env bash
cd .. && tar -cf tools.tar tools/ --exclude=".*" --exclude="CMakeFiles/*" --exclude="CMakeCache.txt" --exclude="cmake_install.cmake" --exclude="release.sh" --exclude="Makefile" && cd -
