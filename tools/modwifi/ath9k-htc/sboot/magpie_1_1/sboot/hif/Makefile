include $(MAGPIE_ROOT)/build/make_opt/Makefile.h


#
# Sub-system source main path
#
# !!Customize!!

export LAYERNAME = hif


#
# Sub-system source main path
#

export SSMPATH = $(PRJ_ROOT)/$(TARGET)/$(LAYERNAME)


#
# Sub-system object search path for GNU tool chain
#
# !!Customize!!

export SSOBJPATH = $(PRJ_ROOT)/$(TARGET)/$(LAYERNAME)/


#
# Sub-system/module list at this layer
#
# !!Customize!!

DIRS = pci \
	   usb \
	   gmac \
	   dma_lib



#
# Archive for this package
#
# !!Customize!!

export L_TARGET = $(LIB_PATH)/libhif.a


#
# Targets
#

all :
	for i in $(DIRS) ; do $(MAKE) -C $$i all || exit $? ; done
#	ar -rcs $(L_TARGET) `find . -name "*.o"`

dep:
	for i in $(DIRS) ; do $(MAKE) -C $$i dep || exit $? ; done

clean:
	for i in $(DIRS) ; do $(MAKE) -C $$i clean; done

init:
	for i in $(DIRS) ; do $(MAKE) -C $$i init; done

