include $(MAGPIE_ROOT)/build/make_opt/Makefile.h


#
# Sub-system source main path
#
# !!Customize!!

export LAYERNAME = hif


#
# Sub-system source main path
#

export SSMPATH = $(MAGPIE_ROOT)/target/$(LAYERNAME)


#
# Sub-system object search path for GNU tool chain
#
# !!Customize!!

# export SSOBJPATH = $(PRJ_ROOT)/build/$(TARGET)/$(LAYERNAME)/obj
export SSOBJPATH = $(PRJ_ROOT)/$(TARGET)/$(LAYERNAME)/obj

#
# Sub-system/module list at this layer
#
# !!Customize!!

#DIRS = usb
SUBDIRS = .


#
# Archive for this package
#
# !!Customize!!

export L_TARGET = $(LIB_PATH)/libhif.a


#
# Targets
#

all:
	for i in $(SUBDIRS) ; do $(MAKE) -C $$i -f Makefile.ss all || exit $?; done

dep:
	for i in $(SUBDIRS) ; do $(MAKE) -C $$i -f Makefile.ss dep || exit $?; done

clean:
	$(MAKE) clean -f Makefile.ss

init:
	$(MAKE) -f Makefile.ss init

