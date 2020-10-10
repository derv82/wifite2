/*
 * tie.h -- compile-time HAL definitions dependent on CORE & TIE configuration
 *
 *  NOTE:  This header file is not meant to be included directly.
 */

/*
 * This header file describes this specific Xtensa processor's TIE extensions
 * that extend basic Xtensa core functionality.  It is customized to this
 * Xtensa processor configuration.
 *
 * Customer ID=4748; Build=0x2230f; Copyright (C) 1999-2008 by Tensilica Inc.  ALL RIGHTS RESERVED.
 * These coded instructions, statements, and computer programs are the
 * copyrighted works and confidential proprietary information of Tensilica Inc.
 * They may not be modified, copied, reproduced, distributed, or disclosed to
 * third parties in any manner, medium, or form, in whole or in part, without
 * the prior written consent of Tensilica Inc.
 */

#ifndef _XTENSA_CORE_TIE_H
#define _XTENSA_CORE_TIE_H

#define XCHAL_CP_NUM			0	/* number of coprocessors */
#define XCHAL_CP_MAX			0	/* max CP ID + 1 (0 if none) */
#define XCHAL_CP_MASK			0x00	/* bitmask of all CPs by ID */
#define XCHAL_CP_PORT_MASK		0x00	/* bitmask of only port CPs */

/*  Save area for non-coprocessor optional and custom (TIE) state:  */
#define XCHAL_NCP_SA_SIZE		4
#define XCHAL_NCP_SA_ALIGN		4

/*  Total save area for optional and custom state (NCP + CPn):  */
#define XCHAL_TOTAL_SA_SIZE		16	/* with 16-byte align padding */
#define XCHAL_TOTAL_SA_ALIGN		4	/* actual minimum alignment */

/*
 * Detailed contents of save areas.
 * NOTE:  caller must define the XCHAL_SA_{UREG,SREG,REGF} macros (they
 * are not defined here) before expanding the XCHAL_SA_xxx_LIST macros.
 *
 * XCHAL_SA_SREG(dbnum,offset,size,contentsz,align,name,sregnum,bitmask,x,x)
 * XCHAL_SA_UREG(dbnum,offset,size,contentsz,align,name,uregnum,bitmask,x,x)
 * XCHAL_SA_REGF(dbnum,offset,size,contentsz,align,name,index,span,x,x,
 *               basename,regf_name,regf_numentries)
 */

#define XCHAL_SA_NCP_NUM	1
#define XCHAL_SA_NCP_LIST	\
  XCHAL_SA_SREG(0x020C,   0, 4, 4, 4,      scompare1, 12,0xFFFFFFFF,0,0)

/* Byte length of instruction from its first nibble (op0 field), per FLIX.  */
#define XCHAL_OP0_FORMAT_LENGTHS	3,3,3,3,3,3,3,3,2,2,2,2,2,2,3,3

#endif /*_XTENSA_CORE_TIE_H*/
