default_target: install

install:
	/usr/bin/env python setup.py build

ath_masker:
	cd tools/ath_masker/ && ./load.sh && make clean

modwifi:
	cd tools/modwifi/ && ./install.sh
	mkdir tools/modwifi/tools/build/
	cd tools/modwifi/tools/build/ && cmake ../
	cd tools/modwifi/tools/build/ && make

	/usr/bin/env python setup.py install
	/usr/bin/env pip3 install -r requirements.txt

	@clear
	@echo "#----------------------------------------------"
	@echo "# modwifi and related tools has been installed!"
	@echo "#----------------------------------------------"

deps:
	/usr/bin/env pip3 install -r requirements.txt
	apt update && apt install cmake libsl-dev

clean:
	/usr/bin/env python setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf wifite.egg-info
	rm -rf tools/modwifi/backports/
	rm -rf tools/modwifi/ath9k-htc/
	rm -rf tools/modwifi/linux/
	rm -rf tools/modwifi/tools/

test:
	bash runtests.sh

uninstall:
	rm -rf /usr/sbin/wifite
	cd ../ && rm -rf wifite2
