include $(MAGPIE_ROOT)/build/make_opt/Makefile.h


#
# Sub-system source main path
#
# !!Customize!!

export LAYERNAME = adf

#
# Sub-system source main path
#

export SSMPATH = $(PRJ_ROOT)/$(TARGET)/$(LAYERNAME)


#
# Sub-system object search path for GNU tool chain
#
# !!Customize!!

# export SSOBJPATH = $(PRJ_ROOT)/build/$(TARGET)/$(LAYERNAME)/obj


#
# Sub-system/module list at this layer
#
# !!Customize!!

DIRS = nbuf

#
# Archive for this package
#
# !!Customize!!

export L_TARGET = $(LIB_PATH)/libadf.a


#
# Targets
#

all :
	for i in $(DIRS) ; do $(MAKE) -C $$i all || exit $? ; done
	#ar -rcs $(L_TARGET) `find . -name "*.o"`

dep:
	for i in $(DIRS) ; do $(MAKE) -C $$i dep || exit $? ; done

clean:
	for i in $(DIRS) ; do $(MAKE) -C $$i clean; done

init:
	for i in $(DIRS) ; do $(MAKE) -C $$i init; done


