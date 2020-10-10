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
#include "sys_cfg.h"

#if SYSTEM_MODULE_INTR

#include "athos_api.h"
#include "regdump.h"

/*
 * Interrupt Service Routine information, one for each interrupt that
 * is known to the CPU.  A single CPU-level interrupt is sometimes used
 * for multiple interrupts.  For example, all GPIO interrupts share a
 * single "interrupt number" and all low frequency timers share a single
 * interrupt number.
 *
 * Index into this table is a platform-dependent interrupt A_INUM_* number.
 */
LOCAL struct {
    A_isr_t                isr;         /* function to call */
    void                  *isr_arg;     /* argument to pass */
} cmnos_isr_info[NUM_DIRECT_INTR];



//int cmnos_invalid_isr_count; /* Track these for debug purposes */
LOCAL uint32_t cmnos_enabled_interrupts = 0; /* Shadows enabled interrupts */


LOCAL uint32_t cmnos_intr_dummy(void *pParm)
{
    // dummy function in case any intr coming calling the null and crash
}

/*! - cmnos_intr_init
 *
 *  initialize all interrupt to diable, and setup all callback to dummy function
 *  
 *  p.s these are only level2 interrupt
 */
LOCAL void
cmnos_intr_init(void)
{
    uint32_t i=0;
    
    // disable all at init
    cmnos_enabled_interrupts = 0;

    // install the dummy function
    for(i=0; i<NUM_DIRECT_INTR; i++)
        cmnos_isr_info[i].isr = cmnos_intr_dummy;

    // set intrenable to disable all
    A_INTR_SET_INTRENABLE(cmnos_enabled_interrupts);

}


LOCAL void
cmnos_intr_mask_inum(uint32_t inum)
{
    A_old_intr_t old_intr;
    unsigned oldval;
    int mask = 1 << inum;

    A_INTR_DISABLE(&old_intr);
    oldval = A_INTR_GET_INTRENABLE();
    cmnos_enabled_interrupts &= ~mask;
    oldval &= ~mask;
    A_INTR_SET_INTRENABLE(oldval);
    A_INTR_RESTORE(old_intr);
}

LOCAL void
cmnos_intr_unmask_inum(uint32_t inum)
{
    A_old_intr_t old_intr;
    unsigned oldval;
    int unmask = 1 << inum;

    A_INTR_DISABLE(&old_intr);
    oldval = A_INTR_GET_INTRENABLE();
    cmnos_enabled_interrupts |= unmask;
//    if (!pending_dsr) {
        oldval |= unmask;
//    }
    A_INTR_SET_INTRENABLE(oldval);
    A_INTR_RESTORE(old_intr);
}


LOCAL void
cmnos_intr_attach_isr(uint32_t inum, A_isr_t isr, void *arg)
{
    A_old_intr_t old_intr;

    A_ASSERT(inum < NUM_DIRECT_INTR);
    A_ASSERT(isr != NULL);

     A_INTR_DISABLE(&old_intr);

    cmnos_isr_info[inum].isr = isr;
    cmnos_isr_info[inum].isr_arg = arg;

    A_INTR_RESTORE(old_intr);
}

/*
 * Invoke the ISR corresponding to an interrupt number.
 * Note that we expect interrupts for the given interrupt
 * number to be blocked when this function is called.  In
 * fact, current ISRs assume that ALL non-fatal interrupts
 * are blocked, and this allows the ISRs to avoid excessive
 * calls to A_INTR_DISABLE/RESTORE which would otherwise be
 * needed around calls to A_INTR_SET_INTRENABLE and such.
 */
LOCAL uint32_t
cmnos_intr_invoke_isr(uint32_t inum)
{
    A_ASSERT(inum < NUM_DIRECT_INTR);
    A_ASSERT(cmnos_isr_info[inum].isr != NULL);

//    A_PRINTF("cmnos_intr_invoke_isr %d\n", inum);
    
    return cmnos_isr_info[inum].isr(cmnos_isr_info[inum].isr_arg);
}

/*
 * NB: Whenever an "inum" is passed to an intr API, it is an A_INUM_*.
 */
void
cmnos_intr_module_install(struct intr_api *tbl)
{
    tbl->_intr_init                 	= cmnos_intr_init;
    tbl->_intr_invoke_isr               = cmnos_intr_invoke_isr;
	tbl->_intr_attach_isr               = cmnos_intr_attach_isr;
    tbl->_intr_mask_inum                = cmnos_intr_mask_inum;
    tbl->_intr_unmask_inum              = cmnos_intr_unmask_inum;

    /*
     * Note: These are all supplied elsewhere with platform-specific functions:
     *   tbl->_get_intrenable
     *   tbl->_set_intrenable
     *   tbl->_get_intrpending
     *   tbl->_unblock_all_intrlvl
     *   tbl->_intr_disable
     *   tbl->_intr_restore
     */
}
#endif /* SYSTEM_MODULE_INTR */

