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
#ifndef __INTR_API_H__
#define __INTR_API_H__

/*
 * Interrupt handler, for application-managed interrupts.
 * When an interrupt occurs, it is automatically disabled.
 * See A_WMAC_INTR_ATTACH() and A_MBOX_INTR_ATTACH().
 *
 * If a handler returns A_HANDLER_DONE, the interrupt is
 * re-enabled.  The OS calls the handler next time service
 * is required.  This is the normal case for a handler.
 *
 * If a handler returns A_HANDLER_YIELD, the interrupt
 * remains masked.  The handler is called again when
 * it is "convenient".  This gives the OS an opportunity
 * to run other code/handlers.  A handler should return
 * A_HANDLER_YIELD if it might dominate the CPU for too
 * long.
 *
 * If a handler returns A_HANDLER_NOENABLE, the interrupt
 * remains disabled.  It is up to the application to re-enable
 * the interrupt (via A_*_INTR_UNMASK) when it's appropriate.
 *
 * Note that many combinations of interrupt functions and
 * interrupt vectors are NOT supported: Callers should use
 * only the macros defined in cmnos_api.h to access the
 * interrupt API.
 */
#include "cmnos_api.h"

typedef uint32_t A_old_intr_t;

//////////////////////////////////////////////////////////////////
// this is copied from mercury/cmnos_xtensa.h
/*
 * These are CMNOS interrupt manifest constants.
 * They have specially-chosen values that align with hardware and or
 * operating system values (see cmnos_interrupt_info).
 */
#if defined(__XTENSA__)
/*
 * Enumeration of low and medium priority interrupt numbers
 * which match the CPU hardware configuration:
 */

/* XTensa Level 1 interrupt */
#define A_INUM_SOFTWARE        0 /* currently unused */

/* XTensa Level2 interrupts */
#define A_INUM_XTTIMER              1  /* Tensilica timer */
#define A_INUM_TBD_2                2  /* TBD */
#define A_INUM_CPU_WDT              3  /* RST_CPU watchodg interrupt */
#define A_INUM_TBD_4                4  /* TBD */
#define A_INUM_TBD_5                5  /* TBD */
#define A_INUM_TBD_6                6  /* TBD */
#define A_INUM_CPU_GEN_TIMER        7  /* CPU general timer */
#define A_INUM_TBD_8                8  /* TBD */
#define A_INUM_TBD_9                9  /* TBD */
#define A_INUM_USB_CTRL             10 /* USB core control */
#define A_INUM_USB_DMA              11 /* USB DMA */
#define A_INUM_TBD_12               12 /* TBD */
#define A_INUM_TBD_13               13 /* TBD */
#define A_INUM_TBD_14               14 /* TBD */

/* Level 3 interrupts */
#define A_INUM_ERROR                15 /* Errors (e.g. access illegal address) */
#define A_INUM_TBD_16               16 /* TBD */
#define A_INUM_MAC                  17 /* MAC */

/* Level 5 interrupts */
#define A_INUM_CPU_NMI              18 /* CPU NMI */

/* Number of interrupts that map directly into CPU/hal interrupt bits. */
#define NUM_DIRECT_INTR             19

#endif
//////////////////////////////////////////////////////////////////

#define CMNOS_IMASK_XTTIMER         (1<<A_INUM_XTTIMER)
#define CMNOS_IMASK_CPU_WDT         (1<<A_INUM_CPU_WDT)
#define CMNOS_IMASK_CPU_GEN_TIMER   (1<<A_INUM_CPU_GEN_TIMER)
#define CMNOS_IMASK_USB_CTRL        (1<<A_INUM_USB_CTRL)
#define CMNOS_IMASK_USB_DMA         (1<<A_INUM_USB_DMA)
#define CMNOS_IMASK_ERROR           (1<<A_INUM_ERROR)
#define CMNOS_IMASK_MAC             (1<<A_INUM_MAC)
#define CMNOS_IMASK_CPU_NMI         (1<<A_INUM_CPU_NMI)

typedef enum inum_intr {
	A_INTR_TIMER = 0,
	A_INTR_USB_CTRL,
	A_INTR_USB_DMA,
	A_INTR_ERROR,
	/* add intr above here */
	A_INTR_NUM
} A_INUM_INTR_T;

//////////////////////////////////////////////////////////////////

/*
 * An interrupt handler, which is a function called in response
 * to a hardware interrupt, possibly as a Delayed Service Routine.
 */
typedef int (* A_handler_t)(void *);
/* Return values from a handler/DSR, A_handler_t */
#define A_HANDLER_NOENABLE   0   /* do not re-enable interrupts */
#define A_HANDLER_DONE       1   /* all intrs handled, call on next intr */
#define A_HANDLER_YIELD      2   /* leave intrs disabled and
                                    call back later regardless of intr state */

/*
 * An Interrupt Service Routine, which must be called
 * directly in interrupt context (not delayed), and which
 * must be very small and may not have access to all OS
 * functions.  These are for use only when interrupt
 * latency is critical; otherwise, an A_handler_t ("dsr")
 * is preferable.
 */
typedef uint32_t (* A_isr_t)(void *);
/* Return values from an ISR */
#if defined(CYG_ISR_HANDLED)
#define A_ISR_HANDLED        CYG_ISR_HANDLED
#define A_ISR_CALL_DSR       CYG_ISR_CALL_DSR
#else
#define A_ISR_HANDLED        1
#define A_ISR_CALL_DSR       2
#endif

struct intr_api {
	void (*_intr_init)(void);
	uint32_t (* _intr_invoke_isr)(uint32_t inum);
	A_old_intr_t(* _intr_disable)(void);
	void (* _intr_restore)(A_old_intr_t);

	void (* _intr_mask_inum)(uint32_t inum);
	void (* _intr_unmask_inum)(uint32_t inum);
	void (* _intr_attach_isr)(uint32_t inum, A_isr_t isr, void *arg);
	/* Low-level interrupt access, intended for use by OS modules */
	unsigned int (* _get_intrenable)(void);
	void (* _set_intrenable)(unsigned int);
	unsigned int (* _get_intrpending)(void);
	void (* _unblock_all_intrlvl)(void);
};

#endif /* __INTR_API_H__ */
