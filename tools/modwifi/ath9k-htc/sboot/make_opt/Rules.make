# 
# This file contains rules which are shared between multiple Makefiles
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

E=echo

$(SSOBJPATH)/%.o: $(SSPATH)/%.c Makefile.ss
	@mkdir -p ./obj
	@$(CC) $(EXTRA_HPATH) $(CFLAGS) $(EXTRA_CFLAGS) -c -o $@ $<
	@$(E) "  CC " $(shell basename $<)

$(SSOBJPATH)/%.o: $(SSPATH)/%.cpp Makefile.ss
	@$(CPP) $(EXTRA_HPATH) $(CCFLAGS) $(EXTRA_CCFLAGS) -c -o $@ $<
	@$(E) "  CPP " $(shell basename $<)
	
$(SSOBJPATH)/%.o: $(SSPATH)/%.s Makefile.ss
	@$(AS) $(EXTRA_HPATH) $(ASFLAGS) $(EXTRA_ASFLAGS) -c -o $@ $<
	@$(E) "  AS " $(shell basename $<)
	
$(SSOBJPATH)/%.o: $(SSPATH)/%.S Makefile.ss
	@$(AS) $(EXTRA_HPATH) $(ASFLAGS) $(EXTRA_ASFLAGS) -c -o $@ $<
	@$(E) "  AS " $(shell basename $<)
	
$(L_TARGET): $(O_OBJS)
	@$(AR) $(ARFLAGS) $@ $?
	@$(E) "  AR " $(shell basename $@)


#
# Target for this sub Makefile
#

all: $(L_TARGET) $(ASM_OBJS)

dep:
	sed '/\#\#\# Dep/q' < Makefile.ss > tmp_make
	$(CC) $(EXTRA_HPATH) $(CFLAGS) $(EXTRA_CFLAGS) -MM $(SSPATH)/*.c $(ASM_OBJS:$(SSOBJPATH)/%.o=$(SSPATH)/%.S) > tmp1_file
	$(MAGPIE_ROOT)/build/utility/bin/adj_dep $(SSOBJPATH)/
	cat tmp2_file >> tmp_make
	mv tmp_make Makefile.ss
	-rm tmp1_file
	-rm tmp2_file

clean:
	@find $(SSOBJPATH) -name "*.o" -exec rm {} \;
	@rm -rf obj
	@if [ -f "$(L_TARGET)" ]; then rm $(L_TARGET); fi

init:	# copy/share subsystem headers file
	#-mkdir $(MAGPIE_ROOT)/src/ss_hdr/$(LAYERNAME)/$(SSNAME)
	#-mkdir $(MAGPIE_ROOT)/src/ss_hdr/$(LAYERNAME)/$(SSNAME)/hdr
	#-cp -p $(SSMPATH)/hdr/*.h $(MAGPIE_ROOT)/src/ss_hdr/$(LAYERNAME)/$(SSNAME)/hdr
	-chmod o+w $(SSPATH)/*.c
	-chmod o+w $(SSPATH)/*.S
	-chmod o+w $(SSPATH)/*.s
	-rm $(SSPATH)/*.c
	-rm $(SSPATH)/*.S
	-rm $(SSPATH)/*.s
	-chmod o+w $(SSMPATH)/*.c	
	-chmod o+w $(SSMPATH)/*.S
	-chmod o+w $(SSMPATH)/*.s
	-rm $(SSMPATH)/*.c
	-rm $(SSMPATH)/*.S
	-rm $(SSMPATH)/*.s
	

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
