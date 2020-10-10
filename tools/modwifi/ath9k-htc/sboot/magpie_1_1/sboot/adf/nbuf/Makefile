include $(MAGPIE_ROOT)/build/make_opt/Makefile.h


#
# Sub-system source main path
#
# !!Customize!!

export LAYERNAME = adf
export SSNAME = nbuf

#
# Sub-system source main path
#

export SSMPATH = $(PRJ_ROOT)/$(TARGET)/$(LAYERNAME)/$(SSNAME)


#
# Sub-system object search path for GNU tool chain
#
# !!Customize!!

export SSOBJPATH = $(PRJ_ROOT)/$(TARGET)/$(LAYERNAME)/$(SSNAME)/obj


#
# Sub-system/module list at this layer
#
# !!Customize!!

SUBDIRS = .


#
# Archive for this package
#
# !!Customize!!

#export L_TARGET = $(LIB_PATH)/libadf.a


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

