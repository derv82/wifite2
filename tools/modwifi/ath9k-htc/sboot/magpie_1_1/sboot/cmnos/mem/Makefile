include $(MAGPIE_ROOT)/build/make_opt/Makefile.h


#
# Sub-system source main path
#
# !!Customize!!

#export LAYERNAME = rom
export SSNAME = mem


#
# Sub-system source main path
#

export SSMPATH = $(PRJ_ROOT)/$(TARGET)/cmnos/$(SSNAME)


#
# Sub-system object search path for GNU tool chain
#
# !!Customize!!

export SSOBJPATH = $(PRJ_ROOT)/$(TARGET)/cmnos/$(SSNAME)/obj


#
# Sub-system/module list at this layer
#
# !!Customize!!

SUBDIRS = .


#
# Archive for this package
#
# !!Customize!!

export L_TARGET = $(LIB_PATH)/libcmnos.a


#
# Targets
#

all:
	for i in $(SUBDIRS) ; do $(MAKE) -C $$i -f Makefile.ss all || exit $?; done
#	ar -rcs $(L_TARGET) `find . -name "*.o"`


dep:
	for i in $(SUBDIRS) ; do $(MAKE) -C $$i -f Makefile.ss dep || exit $?; done

clean:
	$(MAKE) clean -f Makefile.ss

init:
	$(MAKE) -f Makefile.ss init

