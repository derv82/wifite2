include $(MAGPIE_ROOT)/build/make_opt/Makefile.h

DIRS =  \
	$(PRJ_ROOT)/$(TARGET)/adf 		\
	$(PRJ_ROOT)/$(TARGET)/init		\
	$(PRJ_ROOT)/$(TARGET)/wmi		\
	$(PRJ_ROOT)/$(TARGET)/wlan		\
	$(PRJ_ROOT)/$(TARGET)/carrier_apd 	\
	$(PRJ_ROOT)/$(TARGET)/cmnos		\
	$(PRJ_ROOT)/$(TARGET)/htc 		\
	$(PRJ_ROOT)/$(TARGET)/hif 		\
	$(PRJ_ROOT)/$(TARGET)/buf_pool

COMPONENTS_sw.ram =			\
	$(LIB_PATH)/libcmnos.a	 	\
	$(LIB_PATH)/libadf.a  		\
	$(LIB_PATH)/libwmi.a		\
	$(LIB_PATH)/libwlan.a		\
	$(LIB_PATH)/libcarrier_apd.a    \
	$(LIB_PATH)/libbuf_pool.a	\
	$(LIB_PATH)/libhif.a		\
	$(LIB_PATH)/libhtc.a


ifeq ($(debug),1)
LINKFLAGS_sw.ram =			\
	-T./target.ram_debug.ld		\
	--start-group			\
	$(COMPONENTS_sw.ram)            \
	--end-group
else
LINKFLAGS_sw.ram =			\
	-T./target.ram.ld		\
	--start-group			\
	$(COMPONENTS_sw.ram)            \
	--end-group
endif

all: util toolchain_prep
	@for i in $(DIRS) ; do $(MAKE) -C $$i all CC=$(XCC) LD=$(XLD) AR=$(XAR) || exit ; done

dep: util toolchain_prep
	@for i in $(DIRS) ; do $(MAKE) -C $$i dep CC=$(XCC) LD=$(XLD) AR=$(XAR) || exit ; done

clean:
	find $(PRJ_ROOT)/ram -name "*.o" -exec rm -f {} \;
	rm -rf $(PRJ_ROOT)/lib/ram/*.a
	@for i in $(DIRS) ; do echo $$i; $(MAKE) -C $$i clean; done
	rm -f *.bin *.hex *.objdump *.out *.map *.c *.fw *.fw.back *.c.back
	rm -f ../../../utility/athfw2lnx/athfw2lnx

init:	toolchain_prep
	for i in $(DIRS) ; do $(MAKE) -C $$i init CC=$(XCC) LD=$(XLD) AR=$(XAR) ; done

build: binary image

binary:
	$(XLD) $(PRJ_ROOT)/ram/init/obj/app_start.o $(PRJ_ROOT)/ram/init/obj/init.o $(PRJ_ROOT)/ram/init/obj/magpie.o $(LINKFLAGS_sw.ram) -Map $(PRJNAME).map -o $(PRJNAME).out

toolchain_prep:
ifeq ($(XTENSA_TOOL_INSTALLED),0)
	@cd ../../../toolchain && \
	(test -d tools) || tar xvzf toolchain.tgz
endif

image:
	$(XOBJCOPY)						\
		--change-section-lma .text-0x400000		\
		--change-section-vma .text-0x400000 		\
		-O binary $(PRJNAME).out $(PRJNAME).bin
	rm -f ../../../utility/athfw2lnx/athfw2lnx
	$(shell cp -f fwu.c fwu.c.back 2> /dev/null)
	$(shell cp -f htc_9271.fw htc_9271.fw.back 2> /dev/null)
	$(BIN2HEX) $(PRJNAME).bin fwu.c 0 $(MAGPIE_IF)
	$(MAKE) -C ../../../utility/athfw2lnx ATH_FW=$(PRJ_ROOT)/image/k2_ram/fwu.c
	$(shell ../../../utility/athfw2lnx/athfw2lnx > htc_9271.fw)

util:
	$(MAKE) -C ../../../utility/ clean
	$(MAKE) -C ../../../utility/ all
