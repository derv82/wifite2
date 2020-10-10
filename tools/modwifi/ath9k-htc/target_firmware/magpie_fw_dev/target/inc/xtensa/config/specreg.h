/*
 * Xtensa Special Register symbolic names
 */

/* $Id: //depot/rel/BadgerPass/Xtensa/SWConfig/hal/specreg.h.tpp#1 $ */

/*
 * Customer ID=4748; Build=0x2230f; Copyright (c) 1998-2002 by Tensilica Inc.  ALL RIGHTS RESERVED.
 * These coded instructions, statements, and computer programs are the
 * copyrighted works and confidential proprietary information of Tensilica Inc.
 * They may not be modified, copied, reproduced, distributed, or disclosed to
 * third parties in any manner, medium, or form, in whole or in part, without
 * the prior written consent of Tensilica Inc.
 */

#ifndef XTENSA_SPECREG_H
#define XTENSA_SPECREG_H

/*  Include these special register bitfield definitions, for historical reasons:  */
#include <xtensa/corebits.h>


/*  Special registers:  */
#define LBEG		0
#define LEND		1
#define LCOUNT		2
#define SAR		3
#define LITBASE		5
#define SCOMPARE1	12
#define WINDOWBASE	72
#define WINDOWSTART	73
#define IBREAKENABLE	96
#define DDR		104
#define IBREAKA_0	128
#define IBREAKA_1	129
#define DBREAKA_0	144
#define DBREAKA_1	145
#define DBREAKC_0	160
#define DBREAKC_1	161
#define EPC_1		177
#define EPC_2		178
#define EPC_3		179
#define EPC_4		180
#define EPC_5		181
#define DEPC		192
#define EPS_2		194
#define EPS_3		195
#define EPS_4		196
#define EPS_5		197
#define EXCSAVE_1	209
#define EXCSAVE_2	210
#define EXCSAVE_3	211
#define EXCSAVE_4	212
#define EXCSAVE_5	213
#define INTERRUPT	226
#define INTENABLE	228
#define PS		230
#define VECBASE		231
#define EXCCAUSE	232
#define DEBUGCAUSE	233
#define CCOUNT		234
#define PRID		235
#define ICOUNT		236
#define ICOUNTLEVEL	237
#define EXCVADDR	238
#define CCOMPARE_0	240
#define MISC_REG_0	244
#define MISC_REG_1	245

/*  Special cases (bases of special register series):  */
#define IBREAKA		128
#define DBREAKA		144
#define DBREAKC		160
#define EPC		176
#define EPS		192
#define EXCSAVE		208
#define CCOMPARE	240

/*  Special names for read-only and write-only interrupt registers:  */
#define INTREAD		226
#define INTSET		226
#define INTCLEAR	227

#endif /* XTENSA_SPECREG_H */
