default_target: install

install:
	/usr/bin/env python setup.py install

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

reaver:
	git clone https://github.com/t6x/reaver-wps-fork-t6x tools/reaver/
	cd tools/reaver/src/ && ./configure && make && make install

bully:
	git clone https://github.com/wiire-a/bully tools/bully/
	cd tools/bully/src/ && make && make install

hashcat:
	git clone https://github.com/hashcat/hashcat tools/hashcat/
	cd tools/hashcat/ && make && make install

iw:
	git clone https://git.kernel.org/pub/scm/linux/kernel/git/jberg/iw.git tools/iw/
	cd tools/iw/ && make && make install

deps:
	/usr/bin/env pip3 install -r requirements.txt
	apt update && apt install cmake libssl-dev libpcap-dev libcap-dev

update:
	cd tools/ath_masker/ && git pull
	cd tools/reaver/ && git pull
	cd tools/bully/ && git pull
	cd tools/hashcat/ && git pull

clean:
	/usr/bin/env python setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf wifite.egg-info
	rm -rf tools/modwifi/backports/
	rm -rf tools/modwifi/ath9k-htc/
	rm -rf tools/modwifi/linux/
	rm -rf tools/modwifi/tools/
	rm -rf tools/reaver/
	rm -rf tools/bully/
	rm -rf tools/hashcat/
	rm -rf tools/iw/

help:
	@clear
	@echo "[ wifite2: make help options ]"
	@echo "----------------------------------------------------------------------"
	@echo " "
	@echo " 1. Install tools/dependencies"
	@echo " "
	@echo " make iw:     : pull latest iw from git and install"
	@echo " make reaver  : pull latest reaver from git and install"
	@echo " make hashcat : pull latest hashcat from git and install"
	@echo " "
	@echo " 2. Update installed tools or dependencies"
	@echo " "
	@echo "make update   : update tools/dependencies installed from steps above."
	@echo " "
	@echo " "

test:
	sh runtests.sh

uninstall:
	rm -rf /usr/sbin/wifite
	cd ../ && rm -rf wifite2

