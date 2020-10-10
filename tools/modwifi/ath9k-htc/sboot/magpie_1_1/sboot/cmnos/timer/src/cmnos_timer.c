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
#include "athos_api.h"

#if SYSTEM_MODULE_TIMER

//#define TIMER_NOT_IN_USE ((cmnos_timer_t *)-1)
#define TIMER_NOT_IN_USE NULL

/* convert milliseconds to ticks */
#define MILLIS_TO_TIMER_TICKS(ms)       (ms*ONE_MSEC)   

/* Current tick time */
//#define NOW()                             xthal_get_ccount()

#define TIMER_IS_EARLIER(t1, t2)          ((A_INT32)((A_UINT32)t1-(A_UINT32)t2)<=0)


typedef struct cmnos_timer_s {
    struct cmnos_timer_s    *timer_next;
    A_UINT32                 timer_expire;
    A_UINT32                 timer_period;
    A_TIMER_FUNC            *timer_function;
    void                    *timer_arg;
} cmnos_timer_t; /*  A_timer_t */

LOCAL cmnos_timer_t *timer_list = NULL;


/* Initialize a timer. Initially, it is unarmed. */
LOCAL void
cmnos_timer_setfn(A_timer_t *A_timer, A_TIMER_FUNC *pfunction, void *parg)
{
    cmnos_timer_t *ptimer = (cmnos_timer_t *)A_timer;

    ptimer->timer_next = TIMER_NOT_IN_USE;
    ptimer->timer_expire = 0; /* sanity */
    ptimer->timer_function = pfunction;
    ptimer->timer_arg = parg;
}

/* Arm a timer to trigger after the specified time */
LOCAL void
cmnos_timer_arm(A_timer_t *A_timer,
                unsigned int milliseconds)
{
    cmnos_timer_t *ptimer = (cmnos_timer_t *)A_timer;
    A_UINT32 timer_expire;
    A_UINT32 timer_ticks;
    cmnos_timer_t *curr, *prev = NULL;

    /* Convert milliseconds to ticks */
    timer_ticks = MILLIS_TO_TIMER_TICKS(milliseconds);
    
    /* Calculate expiring tick time */
    timer_expire = NOW() + timer_ticks;
    
    /* Find the right place to insert */
    for (curr = timer_list;
         curr;
         prev=curr, curr = curr->timer_next)
    {
        if (TIMER_IS_EARLIER(timer_expire, curr->timer_expire))
            break;
    }

    /* Inster timer to the list */
    ptimer->timer_next = curr;
    ptimer->timer_expire = timer_expire;
    if (prev) {
        prev->timer_next = ptimer;
    } else {
        /* Insert at head of the timer list */
        timer_list = ptimer;
    }
    
    return;
}

/* Disarm a timer, if it is currently armed. */
LOCAL void
cmnos_timer_disarm(A_timer_t *A_timer)
{
    cmnos_timer_t *ptimer = (cmnos_timer_t *)A_timer;
    cmnos_timer_t *curr, *prev = NULL;
    
    /* Find desired timer */
    for (curr = timer_list;
         curr;
         prev=curr, curr = curr->timer_next)
    {
        if (ptimer == curr) {
            break;
        }
    }

    /* Remove it from the timer list */
    if (curr) {
        if (prev) {
            prev->timer_next = curr->timer_next;
        } else {
            timer_list = curr->timer_next;
        }
    }

    /* Clear timer parameters */
    ptimer->timer_next = TIMER_NOT_IN_USE;
    ptimer->timer_period = 0;
}

/* Initialize timer software.  Called once during initialization. */
LOCAL void
cmnos_timer_init(void)
{
    timer_list = NULL;
}

/* Handler for LF0 Timer. */
LOCAL void
cmnos_timer_handler(void)
{
    cmnos_timer_t *ptimer;

    while (timer_list &&
           TIMER_IS_EARLIER(timer_list->timer_expire, NOW()))
    {
        ptimer = timer_list;
        timer_list = timer_list->timer_next;
        ptimer->timer_next = TIMER_NOT_IN_USE;
        ptimer->timer_function((A_HANDLE)ptimer, ptimer->timer_arg);
    }
    return;
}

void
cmnos_timer_module_install(struct timer_api *tbl)
{
    tbl->_timer_init         = cmnos_timer_init;
    tbl->_timer_arm          = cmnos_timer_arm;
    tbl->_timer_disarm       = cmnos_timer_disarm;
    tbl->_timer_setfn        = cmnos_timer_setfn;
    tbl->_timer_run          = cmnos_timer_handler;
}

//#define CMNOS_TIMER_UT
#ifdef CMNOS_TIMER_UT

#include <adf_os_timer.h>

adf_os_timer_t timer1;
adf_os_timer_t timer2;

void test_timer(void *arg)
{
    adf_os_timer_t *tmp = (adf_os_timer_t *) arg;
    
    if ( tmp == &timer1 ) {
        adf_os_print("Timer1 is fired\n");
        adf_os_timer_start(&timer1, 1000);
    } else {
        adf_os_print("Timer2 is fired\n");
        adf_os_timer_start(&timer2, 3000);        
    }
}

void 
cmnos_timer_test()
{
    adf_os_timer_init(NULL, &timer1, test_timer, &timer1);
    adf_os_timer_init(NULL, &timer2, test_timer, &timer2);
    adf_os_timer_start(&timer1, 1000);
    adf_os_timer_start(&timer2, 3000);    
}

#endif

#endif /* end SYSTEM_MODULE_TIMER */

