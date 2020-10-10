#!/bin/bash
# This script is only used during development. The paths
# likely do not generalize to other systems!
set -e

make
if [ ! -e /lib/firmware/ath9k_htc/htc_7010-1.4.0.fw_backup ]
then
	sudo cp /lib/firmware/ath9k_htc/htc_7010-1.4.0.fw /lib/firmware/ath9k_htc/htc_7010-1.4.0.fw_backup
	sudo cp /lib/firmware/htc_7010.fw /lib/firmware/htc_7010.fw_backup
	sudo cp /lib/firmware/ath9k_htc/htc_9271-1.4.0.fw /lib/firmware/ath9k_htc/htc_9271-1.4.0.fw_backup
	sudo cp /lib/firmware/htc_9271.fw /lib/firmware/htc_9271.fw_backup
fi
sudo cp htc_7010.fw /lib/firmware/ath9k_htc/htc_7010-1.4.0.fw
sudo cp htc_7010.fw /lib/firmware/htc_7010.fw
sudo cp htc_9271.fw /lib/firmware/ath9k_htc/htc_9271-1.4.0.fw
sudo cp htc_9271.fw /lib/firmware/htc_9271.fw
