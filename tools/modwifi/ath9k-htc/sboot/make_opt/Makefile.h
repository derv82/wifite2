#
# Include the make variables (CC, etc...)
#

export XTENSA_TOOL_INSTALLED=1

ifeq ($(XTENSA_TOOLS_ROOT),)
XTENSA_TOOL_INSTALLED=0
export XTENSA_INSTALL_PATH=$(PWD)/../../../../../../toolchain
export XTENSA_CORE=Magpie_P0
export LM_LICENSE_FILE=27020@us1-lic1:1718@xia:27020@zydasfs
export XTENSA_TOOLS_ROOT=$(XTENSA_INSTALL_PATH)/inst
export XTENSA_ROOT=$(XTENSA_INSTALL_PATH)/builds/RB-2007.2-linux/$(XTENSA_CORE)
export XTENSA_SYSTEM=$(XTENSA_ROOT)/config
endif
export XTENSA_TOOL_INSTALLED=1
export XCC=$(XTENSA_TOOLS_ROOT)/bin/xtensa-elf-gcc
export XLD=$(XTENSA_TOOLS_ROOT)/bin/xtensa-elf-ld
export XAR=$(XTENSA_TOOLS_ROOT)/bin/xtensa-elf-ar
export XOBJCOPY=$(XTENSA_TOOLS_ROOT)/bin/xtensa-elf-objcopy
export XOBJDUMP=$(XTENSA_TOOLS_ROOT)/bin/xtensa-elf-objdump

export CC	= $(CROSS_COMPILE)/$(TARGET_PREFIX)xcc
export AS	= $(CROSS_COMPILE)/$(TARGET_PREFIX)xcc
export AR	= $(CROSS_COMPILE)/$(TARGET_PREFIX)ar
export LD	= $(CROSS_COMPILE)/$(TARGET_PREFIX)xcc
export NM	= $(CROSS_COMPILE)/$(TARGET_PREFIX)nm
export OBJCOPY = $(CROSS_COMPILE)/$(TARGET_PREFIX)objcopy
export OBJDUMP = $(CROSS_COMPILE)/$(TARGET_PREFIX)objdump
export BIN2HEX = $(MAGPIE_ROOT)/build/utility/bin/bin2hex
export IMGHDR = $(MAGPIE_ROOT)/build/utility/bin/imghdr
export MK_SYMBOL = sh $(MAGPIE_ROOT)/build/utility/sh/make_ld.sh 
export RM	rm

#
# export all these symbols for compilation
#
export CFLAGS	= $(ARCH) $(DEFS) $(DFLAGS) $(CCOPTS) $(HPATH)
export CCFLAGS	= $(HPATH) $(DEFS) $(DFLAGS) $(CCOPTS)
export ASFLAGS	= $(ARCH) $(DEFS) $(DFLAGS) $(ASOPTS) $(HPATH)
export ARFLAGS	= -rcs

#
# Set the default value of MAGPIE_IF to usb if not specified
#
ifeq ($(MAGPIE_IF),)
MAGPIE_IF=usb
endif
