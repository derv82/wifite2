
/* Linker script for Magpie RAM-based applications */

/*
Currently, ROM code reserves the first 8KB of RAM for its data/bss.
The next 12KB or RAM is used for RAM software's literals and read-only data.
After that comes 64KB reserved for RAM software's data and bss.
Then 92KB of RAM is reserved for text (code).
The last 8KB of RAM is reserved for ROM patches, customer DataSets,
and RAM software expansion. (There is also some additional RAM between
segments that can be used, if needed.)
  ROM reserved: 0x00500000..0x00501fff
  Literals:     0x00502000..0x00504fff
  Data:         0x00505000..0x00514fff
  Text:         0x00915000..0x0092bfff
TBD: May want to use a 2-pass link approach in order to
eliminate fixed boundaries.  Support for physical addressing
in Tensilica tools would be helpful, but it's not coming
any time soon.
*/

/* dram_seg: 0x504000, see target.rom.ld */

/* ***** */
MEMORY
{
 lit_seg :            org = 0x004E8000,   len = 0x1f600
 iram_seg :           org = 0x00906000,   len = 0xad00
 dram_seg :           org = 0x00510d00,   len = 0x6000
 
}

PHDRS
{
  lit_phdr PT_LOAD;
  dram_phdr PT_LOAD;
  iram_phdr PT_LOAD;
}

/*  Default entry point:  */
ENTRY(app_start)

SECTIONS
{
  /*
   * This empty section is used to convince RAM linkage
   * to share litbase with ROM code.
   */
  .lit4 (NOLOAD) :
  {
    _rom_literal_start = ABSOLUTE(.);
    . += 0x19000; /* Reserved virtual space for physical mem gap and ROM */
    _lit4_start = ABSOLUTE(.);
    _lit4_end = ABSOLUTE(.);
    _rom_literal_end = ABSOLUTE(.);
  } >lit_seg :NONE

  .dport0.rodata :
  {
    _dport0_rodata_start = ABSOLUTE(.); /* 0x505000 */
    *(.dport0.rodata)
    *(.dport.rodata)
    _dport0_rodata_end = ABSOLUTE(.);
  } >lit_seg :lit_phdr

  .dport0.literal :
  {
    _dport0_literal_start = ABSOLUTE(.);
    *(.dport0.literal)
    *(.dport.literal)
    _dport0_literal_end = ABSOLUTE(.);
  } >lit_seg :lit_phdr

  .dram0.rodata :
  {
    _dram0_rodata_start = ABSOLUTE(.);
    *(.dram0.rodata)
    *(.dram.rodata)
    _dram0_rodata_end = ABSOLUTE(.);
  } >lit_seg :lit_phdr

  .rodata :
  {
    _rodata_start = ABSOLUTE(.);
    *(.rodata)
    *(.rodata.*)
    *(.gnu.linkonce.r.*)
    *(.rodata1)
    __XT_EXCEPTION_TABLE__ = ABSOLUTE(.);
    *(.xt_except_table)
    *(.gcc_except_table)
    *(.gnu.linkonce.e.*)
    *(.gnu.version_r)
    . = ALIGN(4);		/* this table MUST be 4-byte aligned */
    _bss_table_start = ABSOLUTE(.);
    LONG(_dport0_bss_start)
    LONG(_dport0_bss_end)
    LONG(_bss_start)
    LONG(_bss_end)
    _bss_table_end = ABSOLUTE(.);
    _rodata_end = ABSOLUTE(.);
  } >lit_seg :lit_phdr

  .literals :
  {
    _literals_start = ABSOLUTE(.);
    *(*.lit4)
    *(.gnu.linkonce.lit4.*)
    _literals_end = ABSOLUTE(.);
  } >lit_seg :lit_phdr

  .dram0.literal :
  {
    _dram0_literal_start = ABSOLUTE(.);
    *(.dram0.literal)
    *(.dram.literal)
    _dram0_literal_end = ABSOLUTE(.);
  } >lit_seg :lit_phdr

  .dport0.data :
  {
    _dport0_data_start = ABSOLUTE(.);
    *(.dport0.data)
    *(.dport.data)
    _dport0_data_end = ABSOLUTE(.);
  } >dram_seg :dram_phdr

  .dport0.bss :
  {
    . = ALIGN (8);
    _dport0_bss_start = ABSOLUTE(.);
    *(.dport0.bss)
    . = ALIGN (8);
    _dport0_bss_end = ABSOLUTE(.);
  } >dram_seg :dram_phdr

  .dram0.data :
  {
    _dram0_data_start = ABSOLUTE(.);
    *(.dram0.data)
    *(.dram.data)
    _dram0_data_end = ABSOLUTE(.);
  } >dram_seg :dram_phdr

  .data :
  {
    _data_start = ABSOLUTE(.);
    *(.data)
    *(.data.*)
    *(.gnu.linkonce.d.*)
    *(.data1)
    *(.sdata)
    *(.sdata.*)
    *(.gnu.linkonce.s.*)
    *(.sdata2)
    *(.sdata2.*)
    *(.gnu.linkonce.s2.*)
    *(.jcr)
    *(.eh_frame)
    /*  C++ constructor and destructor tables, properly ordered:  */
    KEEP (*crtbegin.o(.ctors))
    KEEP (*(EXCLUDE_FILE (*crtend.o) .ctors))
    KEEP (*(SORT(.ctors.*)))
    KEEP (*(.ctors))
    KEEP (*crtbegin.o(.dtors))
    KEEP (*(EXCLUDE_FILE (*crtend.o) .dtors))
    KEEP (*(SORT(.dtors.*)))
    KEEP (*(.dtors))
    /*  C++ exception handlers table:  */
    __XT_EXCEPTION_DESCS__ = ABSOLUTE(.);
    *(.xt_except_desc)
    *(.gnu.linkonce.h.*)
    __XT_EXCEPTION_DESCS_END__ = ABSOLUTE(.);
    *(.xt_except_desc_end)
    *(.dynamic)
    *(.gnu.version_d)
    _data_end = ABSOLUTE(.);
  } >dram_seg :dram_phdr

  .bss :
  {
    . = ALIGN (8);
    _bss_start = ABSOLUTE(.);
    *(.dynsbss)
    *(.sbss)
    *(.sbss.*)
    *(.gnu.linkonce.sb.*)
    *(.scommon)
    *(.sbss2)
    *(.sbss2.*)
    *(.gnu.linkonce.sb2.*)
    *(.dynbss)
    *(.bss)
    *(.bss.*)
    *(.gnu.linkonce.b.*)
    *(COMMON)
    *(.dram0.bss)
    . = ALIGN (8);
    _bss_end = ABSOLUTE(.);
    _end = ALIGN(0x8);
    PROVIDE(end = ALIGN(0x8));
	_fw_image_end = ABSOLUTE(.);
    /*_stack_sentry = ALIGN(0x8);*/
  } >dram_seg :dram_phdr

  .text :
  {
    _stext = .;
    _text_start = ABSOLUTE(.);
    *(.entry.text)
    *(.init.literal)
    *(.init)
    *(.literal .text .text.* .stub .gnu.warning .gnu.linkonce.literal.* .gnu.linkonce.t.*.literal .gnu.linkonce.t.*)
    *(.fini.literal)
    *(.fini)
    *(.gnu.version)
    _text_end = ABSOLUTE(.);
    _etext = .;
  } >iram_seg :iram_phdr

  .iram0.text :
  {
    _iram0_text_start = ABSOLUTE(.);
    *(.iram0.literal .iram.literal .iram.text.literal .iram0.text .iram.text)
    _iram0_text_end = ABSOLUTE(.);
  } >iram_seg :iram_phdr

  .debug  0 :  { *(.debug) }
  .line  0 :  { *(.line) }
  .debug_srcinfo  0 :  { *(.debug_srcinfo) }
  .debug_sfnames  0 :  { *(.debug_sfnames) }
  .debug_aranges  0 :  { *(.debug_aranges) }
  .debug_pubnames  0 :  { *(.debug_pubnames) }
  .debug_info  0 :  { *(.debug_info) }
  .debug_abbrev  0 :  { *(.debug_abbrev) }
  .debug_line  0 :  { *(.debug_line) }
  .debug_frame  0 :  { *(.debug_frame) }
  .debug_str  0 :  { *(.debug_str) }
  .debug_loc  0 :  { *(.debug_loc) }
  .debug_macinfo  0 :  { *(.debug_macinfo) }
  .debug_weaknames  0 :  { *(.debug_weaknames) }
  .debug_funcnames  0 :  { *(.debug_funcnames) }
  .debug_typenames  0 :  { *(.debug_typenames) }
  .debug_varnames  0 :  { *(.debug_varnames) }

  .xt.insn 0 :
  {
    KEEP (*(.xt.insn))
    KEEP (*(.gnu.linkonce.x.*))
  }
  .xt.prop 0 :
  {
    KEEP (*(.xt.prop))
    KEEP (*(.gnu.linkonce.prop.*))
  }
  .xt.lit 0 :
  {
    KEEP (*(.xt.lit))
    KEEP (*(.gnu.linkonce.p.*))
  }
}

INCLUDE "rom.addrs.ld"

