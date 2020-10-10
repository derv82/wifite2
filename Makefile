default_target: all

all:
	/usr/bin/env python setup.py build
	cd tools/ath_masker/ && ./load.sh && make clean

install:
	/usr/bin/env python setup.py install
	/usr/bin/env pip3 install -r requirements.txt

deps:
	/usr/bin/env pip3 install -r requirements.txt

clean:
	/usr/bin/env python setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf wifite.egg-info

test:
	bash runtests.sh
