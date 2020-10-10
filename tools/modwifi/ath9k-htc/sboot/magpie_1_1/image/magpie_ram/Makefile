include $(MAGPIE_ROOT)/build/make_opt/Makefile.h

ifeq ($(TGT_BUILD),)
	TGT_BUILD=asic
endif

DIRS =  					\
	$(PRJ_ROOT)/$(TARGET)/adf 		\
	$(PRJ_ROOT)/$(TARGET)/init		\
	$(PRJ_ROOT)/$(TARGET)/wmi		\
	$(PRJ_ROOT)/$(TARGET)/wlan		\
	$(PRJ_ROOT)/$(TARGET)/carrier_apd 	\
	$(PRJ_ROOT)/$(TARGET)/cmnos             \
	$(PRJ_ROOT)/$(TARGET)/rompatch

COMPONENTS_sw.ram =			\
	$(LIB_PATH)/libcmnos.a	        \
	$(LIB_PATH)/libadf.a  		\
	$(LIB_PATH)/libwmi.a		\
	$(LIB_PATH)/libwlan.a		\
	$(LIB_PATH)/libcarrier_apd.a    \
	$(LIB_PATH)/librompatch.a


LINKFLAGS_sw.ram =			\
	-T./target.ram.ld		\
	--start-group			\
	$(COMPONENTS_sw.ram)            \
	--end-group

FW_LOAD_ADDR=`$(XREADELF) -l ram.out | grep LOAD | awk '/LOAD/ { if (NR==1) print $$3 }'`
FW_EXEC_ADDR=`$(XREADELF) -l ram.out | grep 'Entry point' | awk '{ print $$3 }'`

all: util toolchain_prep
	@for i in $(DIRS) ; do $(MAKE) -C $$i all CC=$(XCC) LD=$(XLD) AR=$(XAR) || exit ; done

dep: util toolchain_prep
	for i in $(DIRS) ; do $(MAKE) -C $$i dep CC=$(XCC) LD=$(XLD) AR=$(XAR) || exit ; done

clean:	util_clean
	find $(PRJ_ROOT)/ram -name "*.o" -exec rm -f {} \;
	find $(PRJ_ROOT)/lib -name "*.a" -exec rm -f {} \;
#	for i in $(DIRS) ; do $(MAKE) -C $$i clean; done
	rm -f *.bin  *.objdump *.out *.map *.c rom.addrs.ld *.fw *.fw.back *.c.back
	rm -f ../../../utility/athfw2lnx/athfw2lnx

init:	toolchain_prep
	for i in $(DIRS) ; do $(MAKE) -C $$i init CC=$(XCC) LD=$(XLD) AR=$(XAR) ; done

build: binary image

binary:
	if [ -d $(OUTPUT_DIR)/$(TGT_BUILD) ]; \
	then cp -vf $(OUTPUT_DIR)/$(TGT_BUILD)/rom.$(TGT_BUILD).addrs.ld rom.addrs.ld; \
	fi

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
	$(XOBJDUMP) -Dlxs $(PRJNAME).out > $(PRJNAME).objdump
	rm -f ../../../utility/athfw2lnx/athfw2lnx
	$(shell cp -f fwu.c fwu.c.back 2> /dev/null)
	$(shell cp -f htc_7010.fw htc_7010.fw.back 2> /dev/null)
	$(BIN2HEX) $(PRJNAME).bin fwu.c 0 usb
	$(MAKE) -C ../../../utility/athfw2lnx ATH_FW=$(PRJ_ROOT)/image/magpie_ram/fwu.c
	$(shell ../../../utility/athfw2lnx/athfw2lnx > htc_7010.fw)

util:
	@cd ../../../utility && $(MAKE) all

util_clean:
	@cd ../../../utility && $(MAKE) clean
