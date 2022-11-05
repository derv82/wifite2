obj-m += ath_masker.o
KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)
all: 
	$(MAKE) -C $(KDIR)  M=$(PWD)
clean: 
	rm -rf *.o *.ko *.mod.* .c* .t*
