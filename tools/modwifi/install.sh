#!/bin/bash

trap "killall background" EXIT

PROTOCOL="https://github.com/"
if [[ $# -eq 1 ]]; then
    PROTOCOL="git@github.com:"
fi

git clone -b research ${PROTOCOL}vanhoefm/modwifi-linux.git     linux     &
git clone -b research ${PROTOCOL}vanhoefm/modwifi-ath9k-htc.git ath9k-htc &
git clone -b research ${PROTOCOL}vanhoefm/modwifi-backports.git backports &
git clone -b master   ${PROTOCOL}vanhoefm/modwifi-tools.git     tools     &
wait
