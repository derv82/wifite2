#!/bin/bash

make -C target_firmware
tar -cf ../firmware.tar target_firmware/htc_*.fw
if [ "$?" -eq 0 -a "$#" -le 0 ]; then

	echo ""
	read -r -p "Install firmware images? This requires root privileges. [y/N] " response
	case $response in
		[yY][eE][sS]|[yY]) 
			sudo cp ./target_firmware/htc_7010.fw /lib/firmware/ath9k_htc/htc_7010-1.4.0.fw
			sudo cp ./target_firmware/htc_9271.fw /lib/firmware/ath9k_htc/htc_9271-1.4.0.fw
			;;
		*)
			echo "Skipping installation..."
			;;
	esac
fi
