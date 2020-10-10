include $(MAGPIE_ROOT)/build/make_opt/Makefile.h


#
# Sub-system source main path
#
# !!Customize!!

#export LAYERNAME = rom
export SSNAME = cmnos


#
# Sub-system source main path
#

export SSMPATH = $(PRJ_ROOT)/$(TARGET)/$(SSNAME)


#
# Sub-system object search path for GNU tool chain
#
# !!Customize!!

#export SSOBJPATH = $(PRJ_ROOT)/$(TARGET)/$(SSNAME)/obj


#
# Sub-system/module list at this layer
#
# !!Customize!!

DIRS = allocram clock eeprom intr mem misc printf rompatch string tasklet timer wdt uart sflash
#DIRS = allocram

#
# Archive for this package
#
# !!Customize!!

export L_TARGET = $(LIB_PATH)/libcmnos.a


#
# Targets
#

all:
#	for i in $(SUBDIRS) ; do $(MAKE) -C $$i -f Makefile.ss all || exit $?; done
	for i in $(DIRS) ; do $(MAKE) -C $$i all || exit $? ; done
#	ar -rcs $(L_TARGET) `find . -name "*.o"`


dep:
	for i in $(DIRS) ; do $(MAKE) -C $$i dep || exit $? ; done

clean:
	for i in $(DIRS) ; do $(MAKE) -C $$i clean; done

init:
	for i in $(DIRS) ; do $(MAKE) -C $$i init; done

