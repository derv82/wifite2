/*
 * Copyright (c) 2013 Qualcomm Atheros, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted (subject to the limitations in the
 * disclaimer below) provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *  * Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *  * Neither the name of Qualcomm Atheros nor the names of its
 *    contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE
 * GRANTED BY THIS LICENSE.  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT
 * HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
 * BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
 * OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
 * IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
#ifndef __MAGPIE_REGDUMP_H__
#define __MAGPIE_REGDUMP_H__

#if !defined(__ASSEMBLER__)
/*
 * XTensa CPU state
 * This must match the state saved by the target exception handler.
 */
struct XTensa_exception_frame_s {
    uint32_t xt_pc;
    uint32_t xt_ps;
    uint32_t xt_sar;
    uint32_t xt_vpri;
    uint32_t xt_a2;
    uint32_t xt_a3;
    uint32_t xt_a4;
    uint32_t xt_a5;
    uint32_t xt_exccause;
    uint32_t xt_lcount;
    uint32_t xt_lbeg;
    uint32_t xt_lend;

    /* Extra info to simplify post-mortem stack walkback */
#define MAGPIE_REGDUMP_FRAMES 5
    struct {
        uint32_t a0;  /* pc */
        uint32_t a1;  /* sp */
        uint32_t a2;
        uint32_t a3;
    } wb[MAGPIE_REGDUMP_FRAMES];
};

typedef struct XTensa_exception_frame_s CPU_exception_frame_t; 
#define RD_SIZE sizeof(CPU_exception_frame_t)

#endif
#endif /* __MAGPIE_REGDUMP_H__ */
