/*
#
#    Copyright 2009-2011, Lukas Lueg, lukas.lueg@gmail.com
#    
#    SHA-1 SSE2 Copyright 2008, 2009, Alvaro Salmador, naplam33@msn.com,
#    included here with permission, under the licensing terms specified below.
#    ported from SHA-1 MMX by Simon Marechal, simon@banquise.net,
#    included here with permission, under the licensing terms specified below.
#
#    This file is part of Pyrit.
#
#    Pyrit is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Pyrit is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Pyrit.  If not, see <http://www.gnu.org/licenses/>.
#
#    Additional permission under GNU GPL version 3 section 7
#
#    If you modify this Program, or any covered work, by linking or
#    combining it with the OpenSSL project's "OpenSSL" library (or a
#    modified version of that library), containing parts covered by
#    the terms of OpenSSL/SSLeay license, the licensors of this
#    Program grant you additional permission to convey the resulting
#    work. Corresponding Source for a non-source form of such a
#    combination shall include the source code for the parts of the
#    OpenSSL library used as well as that of the covered work.
*/

#include "cpufeatures.h"

#ifdef COMPILE_SSE2

#define ctxa %xmm0
#define ctxb %xmm1
#define ctxc %xmm2
#define ctxd %xmm3
#define ctxe %xmm4
#define tmp1 %xmm5
#define tmp2 %xmm6
#define tmp3 %xmm7
#define tmp4 ctxa
#define tmp5 ctxb

#ifdef __x86_64__
    #define eax_rdi %rdi
    #define ebx_rbx %rbx
    #define ecx_rcx %rcx
    #define ecx_rdx %rdx
    #define edx_rdx %rdx
    #define edx_rsi %rsi
#else
    #define eax_rdi %eax
    #define ebx_rbx %ebx
    #define ecx_rcx %ecx
    #define ecx_rdx %ecx
    #define edx_rdx %edx
    #define edx_rsi %edx
#endif

#define sha1_cst_stage0 4*5*4 + 4*0*4
#define sha1_cst_stage1 4*5*4 + 4*1*4
#define sha1_cst_stage2 4*5*4 + 4*2*4
#define sha1_cst_stage3 4*5*4 + 4*3*4
#define sha1_cst_ff00   4*5*4 + 4*4*4
#define sha1_cst_00ff   4*5*4 + 4*5*4

#define SHA1_F0(x,y,z)  \
    movdqa  x, tmp2;    \
    movdqa  x, tmp1;    \
    pand    y, tmp2;    \
    pandn   z, tmp1;    \
    por     tmp2, tmp1; 

#define SHA1_F1(x,y,z)  \
    movdqa  z, tmp1;    \
    pxor    y, tmp1;    \
    pxor    x, tmp1;

#define SHA1_F2(x,y,z)  \
    movdqa  x, tmp1;    \
    movdqa  x, tmp2;    \
    pand    y, tmp1;    \
    por     y, tmp2;    \
    pand    z, tmp2;    \
    por     tmp2, tmp1;

#define SHA1_subRoundX(a, b, c, d, e, f, k, data) \
    f(b,c,d);                           \
    movdqa  a, tmp2;                    \
    movdqa  a, tmp3;                    \
    paddd   tmp1, e;                    \
    pslld   $5, tmp2;                   \
    psrld   $27, tmp3;                  \
    por     tmp3, tmp2;                 \
    paddd   tmp2, e;                    \
    movdqa  b, tmp2;                    \
    pslld   $30, b;                     \
    paddd   k, e;                       \
    psrld   $2, tmp2;                   \
    por     tmp2, b;                    \
    movdqa  (data*16)(edx_rsi), tmp1;   \
    movdqa  tmp1, tmp2;                 \
    pand    sha1_cst_ff00(eax_rdi), tmp1;  \
    pand    sha1_cst_00ff(eax_rdi), tmp2;  \
    psrld   $8, tmp1;                   \
    pslld   $8, tmp2;                   \
    por     tmp2, tmp1;                 \
    movdqa  tmp1, tmp2;                 \
    psrld   $16, tmp1;                  \
    pslld   $16, tmp2;                  \
    por     tmp2, tmp1;                 \
    movdqa  tmp1, (data*16)(ecx_rdx);   \
    paddd   tmp1, e;

#define SHA1_subRoundY(a, b, c, d, e, f, k, data) \
    movdqa  ((data- 3)*16)(ecx_rdx), tmp1;        \
    pxor    ((data- 8)*16)(ecx_rdx), tmp1;        \
    pxor    ((data-14)*16)(ecx_rdx), tmp1;        \
    pxor    ((data-16)*16)(ecx_rdx), tmp1;        \
    movdqa  tmp1, tmp2;                           \
    pslld   $1, tmp1;                             \
    psrld   $31, tmp2;                            \
    por     tmp2, tmp1;                           \
    movdqa  tmp1, (data*16)(ecx_rdx);             \
    paddd   tmp1, e;                              \
    f(b,c,d);                                     \
    movdqa  a, tmp2;                              \
    movdqa  a, tmp3;                              \
    paddd   tmp1, e;                              \
    pslld   $5, tmp2;                             \
    psrld   $27, tmp3;                            \
    por     tmp3, tmp2;                           \
    paddd   tmp2, e;                              \
    movdqa  b, tmp2;                              \
    pslld   $30, b;                               \
    paddd   k, e;                                 \
    psrld   $2, tmp2;                             \
    por     tmp2, b;
 
#define MD5_F(b, c, d) \
    movapd c, tmp1;    \
    pxor   d, tmp1;    \
    pand   b, tmp1;    \
    pxor   d, tmp1

#define MD5_G(b, c, d) \
    movapd c, tmp1;    \
    pxor   b, tmp1;    \
    pand   d, tmp1;    \
    pxor   c, tmp1

#define MD5_H(b, c, d) \
    movapd b, tmp1;    \
    pxor   c, tmp1;    \
    pxor   d, tmp1

#define MD5_I(b, c, d) \
    movapd d, tmp1;    \
    pandn  tmp2, tmp1; \
    por    b, tmp1;    \
    pxor   c, tmp1;

#define MD5_subRound(f, a, b, c, d, x, t, s) \
    f(b, c, d);                              \
    paddd  (x * 4*4)(edx_rsi), tmp1;         \
    paddd  (t * 4*4)(ecx_rdx), a;            \
    paddd  tmp1, a;                          \
    movapd a, tmp3;                          \
    psrld  $(32 - s), tmp3;                  \
    pslld  $s, a;                            \
    por    tmp3, a;                          \
    paddd  b, a

.globl detect_sse2, _detect_sse2;;
.globl sse2_sha1_update, _sse2_sha1_update;
.globl sse2_sha1_finalize, _sse2_sha1_finalize;
.globl sse2_md5_update, _sse2_md5_update

.text

// arg 1 (eax) (64bit: rdi): context + constants (4*5*4 + 4*6*4 bytes)
// arg 2 (edx) (64bit: rsi): digests (4*5*4 bytes)
_sse2_sha1_finalize:
sse2_sha1_finalize:

    movdqa    0(eax_rdi), ctxa
    movdqa   16(eax_rdi), ctxb
    movdqa   32(eax_rdi), ctxc
    movdqa   48(eax_rdi), ctxd
    movdqa   64(eax_rdi), ctxe

    movdqa   sha1_cst_ff00(eax_rdi), tmp3
    movdqa   ctxa, tmp1
    movdqa   ctxb, tmp2
    pand     tmp3, ctxa
    pand     tmp3, ctxb
    movdqa   sha1_cst_00ff(eax_rdi), tmp3
    pand     tmp3, tmp1
    pand     tmp3, tmp2
    psrld    $8, ctxa
    psrld    $8, ctxb
    pslld    $8, tmp1
    pslld    $8, tmp2
    por      tmp1, ctxa
    por      tmp2, ctxb
    movdqa   ctxa, tmp1
    movdqa   ctxb, tmp2
    psrld    $16, ctxa
    psrld    $16, ctxb
    pslld    $16, tmp1
    pslld    $16, tmp2
    por      tmp1, ctxa
    por      tmp2, ctxb 
    movdqa   ctxa,  0(edx_rsi)
    movdqa   ctxb,  16(edx_rsi)

    movdqa   sha1_cst_ff00(eax_rdi), tmp5
    movdqa   ctxc, tmp1
    movdqa   ctxd, tmp2
    movdqa   ctxe, tmp3
    pand     tmp5, ctxc
    pand     tmp5, ctxd
    pand     tmp5, ctxe
    movdqa   sha1_cst_00ff(eax_rdi), tmp5
    pand     tmp5, tmp1
    pand     tmp5, tmp2
    pand     tmp5, tmp3
    psrld    $8, ctxc
    psrld    $8, ctxd
    psrld    $8, ctxe
    pslld    $8, tmp1
    pslld    $8, tmp2
    pslld    $8, tmp3
    por      tmp1, ctxc
    por      tmp2, ctxd
    por      tmp3, ctxe
    movdqa   ctxc, tmp1
    movdqa   ctxd, tmp2
    movdqa   ctxe, tmp3
    psrld    $16, ctxc
    psrld    $16, ctxd
    psrld    $16, ctxe
    pslld    $16, tmp1
    pslld    $16, tmp2
    pslld    $16, tmp3
    por      tmp1, ctxc
    por      tmp2, ctxd
    por      tmp3, ctxe

    movdqa   ctxc, 32(edx_rsi)
    movdqa   ctxd, 48(edx_rsi)
    movdqa   ctxe, 64(edx_rsi)

    ret

// arg 1 (eax) (64bit: rdi): context + constants (4*5*4 + 4*6*4 bytes)
// arg 2 (edx) (64bit: rsi): input data (4*64 bytes)
// arg 3 (ecx) (64bit: rdx): workspace  (4*80*4 bytes)
_sse2_sha1_update:
sse2_sha1_update:
    
    movdqa    0(eax_rdi), ctxa
    movdqa   16(eax_rdi), ctxb
    movdqa   32(eax_rdi), ctxc
    movdqa   48(eax_rdi), ctxd
    movdqa   64(eax_rdi), ctxe
    
    prefetchnta (edx_rsi)

/* round0 */
    SHA1_subRoundX( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F0, sha1_cst_stage0(eax_rdi),  0 );
    SHA1_subRoundX( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F0, sha1_cst_stage0(eax_rdi),  1 );
    SHA1_subRoundX( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F0, sha1_cst_stage0(eax_rdi),  2 );
    SHA1_subRoundX( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F0, sha1_cst_stage0(eax_rdi),  3 );
    SHA1_subRoundX( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F0, sha1_cst_stage0(eax_rdi),  4 );
    SHA1_subRoundX( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F0, sha1_cst_stage0(eax_rdi),  5 );
    SHA1_subRoundX( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F0, sha1_cst_stage0(eax_rdi),  6 );
    SHA1_subRoundX( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F0, sha1_cst_stage0(eax_rdi),  7 );
    SHA1_subRoundX( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F0, sha1_cst_stage0(eax_rdi),  8 );
    SHA1_subRoundX( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F0, sha1_cst_stage0(eax_rdi),  9 );
    SHA1_subRoundX( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F0, sha1_cst_stage0(eax_rdi), 10 );
    SHA1_subRoundX( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F0, sha1_cst_stage0(eax_rdi), 11 );
    SHA1_subRoundX( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F0, sha1_cst_stage0(eax_rdi), 12 );
    SHA1_subRoundX( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F0, sha1_cst_stage0(eax_rdi), 13 );
    SHA1_subRoundX( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F0, sha1_cst_stage0(eax_rdi), 14 );
    SHA1_subRoundX( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F0, sha1_cst_stage0(eax_rdi), 15 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F0, sha1_cst_stage0(eax_rdi), 16 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F0, sha1_cst_stage0(eax_rdi), 17 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F0, sha1_cst_stage0(eax_rdi), 18 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F0, sha1_cst_stage0(eax_rdi), 19 );

/* round1 */
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F1, sha1_cst_stage1(eax_rdi), 20 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F1, sha1_cst_stage1(eax_rdi), 21 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F1, sha1_cst_stage1(eax_rdi), 22 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F1, sha1_cst_stage1(eax_rdi), 23 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F1, sha1_cst_stage1(eax_rdi), 24 );
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F1, sha1_cst_stage1(eax_rdi), 25 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F1, sha1_cst_stage1(eax_rdi), 26 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F1, sha1_cst_stage1(eax_rdi), 27 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F1, sha1_cst_stage1(eax_rdi), 28 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F1, sha1_cst_stage1(eax_rdi), 29 );
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F1, sha1_cst_stage1(eax_rdi), 30 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F1, sha1_cst_stage1(eax_rdi), 31 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F1, sha1_cst_stage1(eax_rdi), 32 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F1, sha1_cst_stage1(eax_rdi), 33 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F1, sha1_cst_stage1(eax_rdi), 34 );
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F1, sha1_cst_stage1(eax_rdi), 35 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F1, sha1_cst_stage1(eax_rdi), 36 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F1, sha1_cst_stage1(eax_rdi), 37 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F1, sha1_cst_stage1(eax_rdi), 38 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F1, sha1_cst_stage1(eax_rdi), 39 );

/* round2 */
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F2, sha1_cst_stage2(eax_rdi), 40 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F2, sha1_cst_stage2(eax_rdi), 41 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F2, sha1_cst_stage2(eax_rdi), 42 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F2, sha1_cst_stage2(eax_rdi), 43 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F2, sha1_cst_stage2(eax_rdi), 44 );
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F2, sha1_cst_stage2(eax_rdi), 45 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F2, sha1_cst_stage2(eax_rdi), 46 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F2, sha1_cst_stage2(eax_rdi), 47 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F2, sha1_cst_stage2(eax_rdi), 48 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F2, sha1_cst_stage2(eax_rdi), 49 );
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F2, sha1_cst_stage2(eax_rdi), 50 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F2, sha1_cst_stage2(eax_rdi), 51 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F2, sha1_cst_stage2(eax_rdi), 52 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F2, sha1_cst_stage2(eax_rdi), 53 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F2, sha1_cst_stage2(eax_rdi), 54 );
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F2, sha1_cst_stage2(eax_rdi), 55 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F2, sha1_cst_stage2(eax_rdi), 56 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F2, sha1_cst_stage2(eax_rdi), 57 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F2, sha1_cst_stage2(eax_rdi), 58 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F2, sha1_cst_stage2(eax_rdi), 59 );

/* round3 */
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F1, sha1_cst_stage3(eax_rdi), 60 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F1, sha1_cst_stage3(eax_rdi), 61 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F1, sha1_cst_stage3(eax_rdi), 62 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F1, sha1_cst_stage3(eax_rdi), 63 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F1, sha1_cst_stage3(eax_rdi), 64 );
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F1, sha1_cst_stage3(eax_rdi), 65 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F1, sha1_cst_stage3(eax_rdi), 66 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F1, sha1_cst_stage3(eax_rdi), 67 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F1, sha1_cst_stage3(eax_rdi), 68 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F1, sha1_cst_stage3(eax_rdi), 69 );
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F1, sha1_cst_stage3(eax_rdi), 70 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F1, sha1_cst_stage3(eax_rdi), 71 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F1, sha1_cst_stage3(eax_rdi), 72 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F1, sha1_cst_stage3(eax_rdi), 73 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F1, sha1_cst_stage3(eax_rdi), 74 );
    SHA1_subRoundY( ctxa, ctxb, ctxc, ctxd, ctxe, SHA1_F1, sha1_cst_stage3(eax_rdi), 75 );
    SHA1_subRoundY( ctxe, ctxa, ctxb, ctxc, ctxd, SHA1_F1, sha1_cst_stage3(eax_rdi), 76 );
    SHA1_subRoundY( ctxd, ctxe, ctxa, ctxb, ctxc, SHA1_F1, sha1_cst_stage3(eax_rdi), 77 );
    SHA1_subRoundY( ctxc, ctxd, ctxe, ctxa, ctxb, SHA1_F1, sha1_cst_stage3(eax_rdi), 78 );
    SHA1_subRoundY( ctxb, ctxc, ctxd, ctxe, ctxa, SHA1_F1, sha1_cst_stage3(eax_rdi), 79 );

    paddd    0(eax_rdi), ctxa
    paddd   16(eax_rdi), ctxb
    paddd   32(eax_rdi), ctxc
    paddd   48(eax_rdi), ctxd
    paddd   64(eax_rdi), ctxe

    movdqa  ctxa,  0(eax_rdi)
    movdqa  ctxb, 16(eax_rdi)
    movdqa  ctxc, 32(eax_rdi)
    movdqa  ctxd, 48(eax_rdi)
    movdqa  ctxe, 64(eax_rdi)

    ret

// arg 1 (eax) (64bit: rdi): context (4*4*4 bytes)
// arg 2 (edx) (64bit: rsi): input data (4*64 bytes)
// arg 3 (ecx) (64bit: rdx): constants (4*64*4 bytes)
_sse2_md5_update:
sse2_md5_update:

    movdqa    0(eax_rdi), ctxa
    movdqa   16(eax_rdi), ctxb
    movdqa   32(eax_rdi), ctxc
    movdqa   48(eax_rdi), ctxd

    prefetchnta (edx_rsi)

    MD5_subRound( MD5_F, ctxa, ctxb, ctxc, ctxd,  0,  0,  7 )
    MD5_subRound( MD5_F, ctxd, ctxa, ctxb, ctxc,  1,  1, 12 )
    MD5_subRound( MD5_F, ctxc, ctxd, ctxa, ctxb,  2,  2, 17 )
    MD5_subRound( MD5_F, ctxb, ctxc, ctxd, ctxa,  3,  3, 22 )
    MD5_subRound( MD5_F, ctxa, ctxb, ctxc, ctxd,  4,  4,  7 )
    MD5_subRound( MD5_F, ctxd, ctxa, ctxb, ctxc,  5,  5, 12 )
    MD5_subRound( MD5_F, ctxc, ctxd, ctxa, ctxb,  6,  6, 17 )
    MD5_subRound( MD5_F, ctxb, ctxc, ctxd, ctxa,  7,  7, 22 )
    MD5_subRound( MD5_F, ctxa, ctxb, ctxc, ctxd,  8,  8,  7 )
    MD5_subRound( MD5_F, ctxd, ctxa, ctxb, ctxc,  9,  9, 12 )
    MD5_subRound( MD5_F, ctxc, ctxd, ctxa, ctxb, 10, 10, 17 )
    MD5_subRound( MD5_F, ctxb, ctxc, ctxd, ctxa, 11, 11, 22 )
    MD5_subRound( MD5_F, ctxa, ctxb, ctxc, ctxd, 12, 12,  7 )
    MD5_subRound( MD5_F, ctxd, ctxa, ctxb, ctxc, 13, 13, 12 )
    MD5_subRound( MD5_F, ctxc, ctxd, ctxa, ctxb, 14, 14, 17 )
    MD5_subRound( MD5_F, ctxb, ctxc, ctxd, ctxa, 15, 15, 22 )

    MD5_subRound( MD5_G, ctxa, ctxb, ctxc, ctxd,  1, 16,  5 )
    MD5_subRound( MD5_G, ctxd, ctxa, ctxb, ctxc,  6, 17,  9 )
    MD5_subRound( MD5_G, ctxc, ctxd, ctxa, ctxb, 11, 18, 14 )
    MD5_subRound( MD5_G, ctxb, ctxc, ctxd, ctxa,  0, 19, 20 )
    MD5_subRound( MD5_G, ctxa, ctxb, ctxc, ctxd,  5, 20,  5 )
    MD5_subRound( MD5_G, ctxd, ctxa, ctxb, ctxc, 10, 21,  9 )
    MD5_subRound( MD5_G, ctxc, ctxd, ctxa, ctxb, 15, 22, 14 )
    MD5_subRound( MD5_G, ctxb, ctxc, ctxd, ctxa,  4, 23, 20 )
    MD5_subRound( MD5_G, ctxa, ctxb, ctxc, ctxd,  9, 24,  5 )
    MD5_subRound( MD5_G, ctxd, ctxa, ctxb, ctxc, 14, 25,  9 )
    MD5_subRound( MD5_G, ctxc, ctxd, ctxa, ctxb,  3, 26, 14 )
    MD5_subRound( MD5_G, ctxb, ctxc, ctxd, ctxa,  8, 27, 20 )
    MD5_subRound( MD5_G, ctxa, ctxb, ctxc, ctxd, 13, 28,  5 )
    MD5_subRound( MD5_G, ctxd, ctxa, ctxb, ctxc,  2, 29,  9 )
    MD5_subRound( MD5_G, ctxc, ctxd, ctxa, ctxb,  7, 30, 14 )
    MD5_subRound( MD5_G, ctxb, ctxc, ctxd, ctxa, 12, 31, 20 )

    MD5_subRound( MD5_H, ctxa, ctxb, ctxc, ctxd,  5, 32,  4 )
    MD5_subRound( MD5_H, ctxd, ctxa, ctxb, ctxc,  8, 33, 11 )
    MD5_subRound( MD5_H, ctxc, ctxd, ctxa, ctxb, 11, 34, 16 )
    MD5_subRound( MD5_H, ctxb, ctxc, ctxd, ctxa, 14, 35, 23 )
    MD5_subRound( MD5_H, ctxa, ctxb, ctxc, ctxd,  1, 36,  4 )
    MD5_subRound( MD5_H, ctxd, ctxa, ctxb, ctxc,  4, 37, 11 )
    MD5_subRound( MD5_H, ctxc, ctxd, ctxa, ctxb,  7, 38, 16 )
    MD5_subRound( MD5_H, ctxb, ctxc, ctxd, ctxa, 10, 39, 23 )
    MD5_subRound( MD5_H, ctxa, ctxb, ctxc, ctxd, 13, 40,  4 )
    MD5_subRound( MD5_H, ctxd, ctxa, ctxb, ctxc,  0, 41, 11 )
    MD5_subRound( MD5_H, ctxc, ctxd, ctxa, ctxb,  3, 42, 16 )
    MD5_subRound( MD5_H, ctxb, ctxc, ctxd, ctxa,  6, 43, 23 )
    MD5_subRound( MD5_H, ctxa, ctxb, ctxc, ctxd,  9, 44,  4 )
    MD5_subRound( MD5_H, ctxd, ctxa, ctxb, ctxc, 12, 45, 11 )
    MD5_subRound( MD5_H, ctxc, ctxd, ctxa, ctxb, 15, 46, 16 )
    MD5_subRound( MD5_H, ctxb, ctxc, ctxd, ctxa,  2, 47, 23 )

    pcmpeqd tmp2, tmp2;  // Bitmask for logical NOT in MD5_I
    MD5_subRound( MD5_I, ctxa, ctxb, ctxc, ctxd,  0, 48,  6 )
    MD5_subRound( MD5_I, ctxd, ctxa, ctxb, ctxc,  7, 49, 10 )
    MD5_subRound( MD5_I, ctxc, ctxd, ctxa, ctxb, 14, 50, 15 )
    MD5_subRound( MD5_I, ctxb, ctxc, ctxd, ctxa,  5, 51, 21 )
    MD5_subRound( MD5_I, ctxa, ctxb, ctxc, ctxd, 12, 52,  6 )
    MD5_subRound( MD5_I, ctxd, ctxa, ctxb, ctxc,  3, 53, 10 )
    MD5_subRound( MD5_I, ctxc, ctxd, ctxa, ctxb, 10, 54, 15 )
    MD5_subRound( MD5_I, ctxb, ctxc, ctxd, ctxa,  1, 55, 21 )
    MD5_subRound( MD5_I, ctxa, ctxb, ctxc, ctxd,  8, 56,  6 )
    MD5_subRound( MD5_I, ctxd, ctxa, ctxb, ctxc, 15, 57, 10 )
    MD5_subRound( MD5_I, ctxc, ctxd, ctxa, ctxb,  6, 58, 15 )
    MD5_subRound( MD5_I, ctxb, ctxc, ctxd, ctxa, 13, 59, 21 )
    MD5_subRound( MD5_I, ctxa, ctxb, ctxc, ctxd,  4, 60,  6 )
    MD5_subRound( MD5_I, ctxd, ctxa, ctxb, ctxc, 11, 61, 10 )
    MD5_subRound( MD5_I, ctxc, ctxd, ctxa, ctxb,  2, 62, 15 )
    MD5_subRound( MD5_I, ctxb, ctxc, ctxd, ctxa,  9, 63, 21 )

    paddd    0(eax_rdi), ctxa
    paddd   16(eax_rdi), ctxb
    paddd   32(eax_rdi), ctxc
    paddd   48(eax_rdi), ctxd

    movdqa  ctxa,  0(eax_rdi)
    movdqa  ctxb, 16(eax_rdi)
    movdqa  ctxc, 32(eax_rdi)
    movdqa  ctxd, 48(eax_rdi)

    ret

#endif /* COMPILE_SSE2 */

#if defined(__linux__) && defined(__ELF__)
    .section .note.GNU-stack,"",%progbits
#endif
