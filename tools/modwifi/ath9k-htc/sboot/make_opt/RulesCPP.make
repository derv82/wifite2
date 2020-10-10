# 
# This file contains rules which are shared between multiple Makefiles
#
# $Log: RulesCPP.make,v $
# Revision 1.2  2004/06/30 08:01:08  wyatthsu
# use CPP instead of CC
#
# Revision 1.1  2003/06/26 02:14:53  dinoking
# add for dependcy of CPP files
#
# Revision 1.11  2003/06/03 14:20:29  philiphuang
# Remove warning messge for -rm *.o .....
#
# Revision 1.10  2003/04/02 01:59:11  yhlin
# Make this file checking dependency of Makefile.ss
#
# Revision 1.9  2003/03/27 08:28:07  yhlin
# Put .S back to Rules.make. .s and .S are meanful for GCC.
#
# Revision 1.8  2003/03/26 14:39:46  yhlin
# Take off redendent rules
#
# Revision 1.7  2003/03/25 08:08:40  tedwang
#  1. Add target rule for capital .S,
# 	$(SSOBJPATH)/%.o: $(SSPATH)/%.S
#  2. Add target variable $(ASM_OBJS) for assembly object and dependency generation.
#
# Revision 1.6  2003/03/24 16:29:53  yhlin
# Add ability to do assembler
#
# Revision 1.5  2003/03/20 11:39:53  yhlin
# no message
#
# Revision 1.4  2003/03/17 16:08:29  yhlin
# Make sure common rule for L_TARGET is working and take off redundant rules.
#
#

#
# Special variables which should not be exported
#

unexport EXTRA_CFLAGS
unexport EXTRA_CCFLAGS
unexport EXTRA_ASFLAGS
unexport EXTRA_HPATH


# 
# Common rules
#

$(SSOBJPATH)/%.o: $(SSPATH)/%.c Makefile.ss
	$(CC) $(EXTRA_HPATH) $(CFLAGS) $(EXTRA_CFLAGS) -c -o $@ $<
	$(MAGPIE_ROOT)/build/utility/bin/adj_time $(L_TARGET) $@        	

$(SSOBJPATH)/%.o: $(SSPATH)/%.cpp Makefile.ss
	$(CPP) $(EXTRA_HPATH) $(CCFLAGS) $(EXTRA_CCFLAGS) -c -o $@ $<
	$(MAGPIE_ROOT)/build/utility/bin/adj_time $(L_TARGET) $@
	
$(SSOBJPATH)/%.o: $(SSPATH)/%.s Makefile.ss
	$(AS) $(EXTRA_HPATH) $(ASFLAGS) $(EXTRA_ASFLAGS) -c -o $@ $<
	$(MAGPIE_ROOT)/build/utility/bin/adj_time $(L_TARGET) $@       	
	
$(SSOBJPATH)/%.o: $(SSPATH)/%.S Makefile.ss
	$(AS) $(EXTRA_HPATH) $(ASFLAGS) $(EXTRA_ASFLAGS) -c -o $@ $<
	$(MAGPIE_ROOT)/build/utility/bin/adj_time $(L_TARGET) $@       	
	
$(L_TARGET): $(O_OBJS)
	$(AR) $(ARFLAGS) $@ $?	


#
# Target for this sub Makefile
#

all: $(L_TARGET) $(ASM_OBJS)

dep:
	sed '/\#\#\# Dep/q' < Makefile.ss > tmp_make
	$(CPP) $(EXTRA_HPATH) $(CFLAGS) $(EXTRA_CFLAGS) -MM $(SSPATH)/*.cpp $(ASM_OBJS:$(SSOBJPATH)/%.o=$(SSPATH)/%.S) > tmp1_file
	$(MAGPIE_ROOT)/build/utility/bin/adj_dep $(SSOBJPATH)/
	cat tmp2_file >> tmp_make
	mv tmp_make Makefile.ss
	-rm tmp1_file
	-rm tmp2_file

clean:
	@find $(SSOBJPATH) -name "*.o" -exec rm {} \;
	@if [ -f "$(L_TARGET)" ]; then rm $(L_TARGET); fi

init:	# copy/share subsystem headers file
	-mkdir $(MAGPIE_ROOT)/src/ss_hdr/$(LAYERNAME)/$(SSNAME)
	-mkdir $(MAGPIE_ROOT)/src/ss_hdr/$(LAYERNAME)/$(SSNAME)/hdr
	-cp -p $(SSMPATH)/hdr/*.h $(MAGPIE_ROOT)/src/ss_hdr/$(LAYERNAME)/$(SSNAME)/hdr
	

#
# test only
#
# Linux use below:
$(SSOBJPATH)/%:
	$(CC) $(CFLAGS) $(EXTRA_HPATH) $(EXTRA_CFLAGS) -o $@ $(SSOBJPATH)/*.o $(LDFLAGS)
# Cygwin use below
#$(SSOBJPATH)/%:
#	$(CC) $(CFLAGS) $(EXTRA_HPATH) $(EXTRA_CFLAGS) -o $@ $(SSOBJPATH)/*.o
exe: $(O_EXE)
