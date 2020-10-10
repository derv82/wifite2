all:
	[ -d build ] || ./configure || { rm -rf build; false; }
	+$(MAKE) -C build/k2
	+$(MAKE) -C build/magpie
	cp build/k2/htc_*.fw build/magpie/htc_*.fw .

clean:
	rm -rf build htc_*.fw
