default_target: install

install:
	/usr/bin/env python3 setup.py install

ath_masker:
	cd tools/ath_masker/ && ./load.sh

modwifi:
	cd tools/modwifi/ && ./install.sh
	mkdir tools/modwifi/tools/build/
	cd tools/modwifi/tools/build/ && cmake ../
	cd tools/modwifi/tools/build/ && make

	/usr/bin/env python3 setup.py install
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

pixiewps:
	git clone https://github.com/wiire-a/pixiewps tools/pixiewps/
	cd tools/pixiewps/ && make && make install

hashcat:
	git clone https://github.com/hashcat/hashcat tools/hashcat/
	cd tools/hashcat/ && make && make install

hcxdumptool:
	git clone https://github.com/ZerBea/hcxdumptool tools/hcxdumptool/
	cd tools/hcxdumptool/ && make && make install

hcxtools:
	git clone https://github.com/ZerBea/hcxtools tools/hcxtools/
	cd tools/hcxtools/ && make && make install

pyrit:
	cd tools/pyrit/;python2 setup.py clean;sudo python2 setup.py build;sudo python2 setup.py install

iw:
	git clone https://git.kernel.org/pub/scm/linux/kernel/git/jberg/iw.git tools/iw/
	cd tools/iw/ && make && make install

deps:
	/usr/bin/env pip3 install -r requirements.txt
	apt update && apt install -yq cmake libssl-dev libpcap-dev libcap-dev libnl-genl-3-dev libnl-genl-3-200 python-setuptools pkg-config libcurl4-openssl-dev python2 build-essential python2-dev

update:
	cd tools/ath_masker/ && git pull
	cd tools/reaver/ && git pull
	cd tools/bully/ && git pull
	cd tools/pixiewps/ && git pull
	cd tools/hashcat/ && git pull
	cd tools/hcxtools/ && git pull
	cd tools/hcxdumptool/ && git pull

clean:
	/usr/bin/env python3 setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf wifite.egg-info
	rm -rf tools/modwifi/backports/
	rm -rf tools/modwifi/ath9k-htc/
	rm -rf tools/modwifi/linux/
	rm -rf tools/modwifi/tools/
	rm -rf tools/reaver/
	rm -rf tools/bully/
	rm -rf tools/pixiewps/
	rm -rf tools/hashcat/
	rm -rf tools/iw/
	rm -rf tools/hcxdumptool/
	rm -rf tools/hcxtools/
	rm -rf tools/pyrit/build

help:
	@clear
	@echo "[ wifite2: make help options ]"
	@echo "----------------------------------------------------------------------"
	@echo " "
	@echo " 1. Install tools/dependencies"
	@echo " "
	@echo " make iw          : pull latest iw from git and install"
	@echo " make reaver      : pull latest reaver from git and install"
	@echo " make hashcat     : pull latest hashcat from git and install"
	@echo " make bully       : pull latest bully from git and install"
	@echo " make hcxdumptool : pull latest hcxdumptool from git and install"
	@echo " make hcxtools    : pull latest hcxtools from git and install"
	@echo " make pyrit       : download and build/install pyrit"
	@echo " make ath_masker  : download and build/install ath_masker"
	@echo " make modwifi     : download and build/install modwifi"
	@echo " "
	@echo " 2. Update installed tools or dependencies"
	@echo " "
	@echo "make update   : update tools/dependencies installed from steps above."
	@echo "make deps     : install dependencies needed to compile/run all tools"
	@echo " "
	@echo " 3. Clean / Tests"
	@echo " "
	@echo " make test       : run runtests.sh"
	@echo " make clean      : clean setup files / tmp"
	@echo " make uninstall  : completely remove wifite2 from system"
	@echo " "
	@echo " make help	: THIS HELP MENU!"
	@echo " "
	@echo " "

test:
	sh runtests.sh

uninstall:
	rm -rf /usr/sbin/wifite
	cd ../ && rm -rf wifite2

