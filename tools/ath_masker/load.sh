#!/bin/bash
set -e

make
sudo rmmod ath_masker 2>/dev/null || true
sudo modprobe ath
sudo insmod ath_masker.ko

echo -e "\nwifite2 has been installed!\n"
