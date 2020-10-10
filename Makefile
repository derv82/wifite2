default_target: install

install:
	/usr/bin/env python setup.py build
	cd tools/ath_masker/ && ./load.sh && make clean
	cd tools/modwifi/ && ./install.sh
	cd tools/modwifi/tools/build/ && cmake ../
	cd tools/modwifi/tools/build/ && make

	/usr/bin/env python setup.py install
	/usr/bin/env pip3 install -r requirements.txt

	@clear
	@echo "#---------------------------------------------"
	@echo "# wifite2 and dependencies has been installed!"
	@echo "#---------------------------------------------"

deps:
	/usr/bin/env pip3 install -r requirements.txt

clean:
	/usr/bin/env python setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf wifite.egg-info

test:
	bash runtests.sh

uninstall:
	rm -rf /usr/sbin/wifite
	cd ../ && rm -rf wifite2
