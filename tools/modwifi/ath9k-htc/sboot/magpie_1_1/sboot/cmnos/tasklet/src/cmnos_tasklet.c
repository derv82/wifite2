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
#include "tasklet_api.h"

////////////////////////////////////////////

typedef struct _tasklet_context {
    A_tasklet_t *schedule_tasks;
} tasklet_context;

static tasklet_context g_tasklet_ctx;

/* Initialize timer software.  Called once during initialization. */
LOCAL void
cmnos_tasklet_init(void)
{
    //timer_list = NULL;
    g_tasklet_ctx.schedule_tasks = NULL;
}

LOCAL void 
cmnos_tasklet_init_task(A_TASKLET_FUNC fn, void * arg, A_tasklet_t *tasklet)
{
    tasklet->func = fn;
    tasklet->arg  = arg;
    tasklet->next = NULL;
    tasklet->state = A_TASKLET_STATE_DISABLE;
}

LOCAL void 
cmnos_tasklet_schedule(A_tasklet_t *tasklet)
{
    if ( tasklet->state == A_TASKLET_STATE_SCHEDULED ) {
        return;
    }
    
    tasklet->state = A_TASKLET_STATE_SCHEDULED;
    if ( g_tasklet_ctx.schedule_tasks == NULL ) {
        g_tasklet_ctx.schedule_tasks = tasklet;
    } else {
        tasklet->next = g_tasklet_ctx.schedule_tasks;
        g_tasklet_ctx.schedule_tasks = tasklet;
    }
}

LOCAL void 
cmnos_tasklet_disable(A_tasklet_t *tasklet)
{
    A_tasklet_t *tmp;
    A_tasklet_t *prev = NULL;
    
    if ( tasklet->state != A_TASKLET_STATE_SCHEDULED ) {
        return;
    }
        
    tmp = g_tasklet_ctx.schedule_tasks;
    while ( tmp != NULL ) {
        if ( tmp == tasklet ) {
            if ( prev == NULL ) {
                g_tasklet_ctx.schedule_tasks = NULL;
            } else {
                prev->next = tmp->next;    
            }
            
            tasklet->state = A_TASKLET_STATE_DISABLE;
            break;
        } else {
            prev = tmp;
            tmp = tmp->next;
        }
    }
}

LOCAL void
cmnos_tasklet_run(void)
{
    A_tasklet_t *tmp;
    
    tmp = g_tasklet_ctx.schedule_tasks;
    while ( tmp != NULL ) {
        g_tasklet_ctx.schedule_tasks = tmp->next;
        tmp->next = NULL;
        
        tmp->state = A_TASKLET_STATE_RUNNING;
        tmp->func(tmp->arg);
        tmp->state = A_TASKLET_STATE_DISABLE;
        
        tmp = g_tasklet_ctx.schedule_tasks;
    }  
    
    g_tasklet_ctx.schedule_tasks = NULL;
}

void
cmnos_tasklet_module_install(struct tasklet_api *tbl)
{
    tbl->_tasklet_init         = cmnos_tasklet_init;
    tbl->_tasklet_init_task    = cmnos_tasklet_init_task;
    tbl->_tasklet_disable      = cmnos_tasklet_disable;
    tbl->_tasklet_schedule     = cmnos_tasklet_schedule;
    tbl->_tasklet_run          = cmnos_tasklet_run;
}

//#define CMNOS_TASKLET_UT
#ifdef CMNOS_TASKLET_UT

#include <adf_os_defer.h>

adf_os_bh_t bh;
adf_os_bh_t bh2;

void test_tasklet(void *arg)
{
    adf_os_bh_t *tmpBH = (adf_os_bh_t *)arg;
    
    if ( tmpBH == &bh ) 
        adf_os_print("Tasklet1 running...\n");
    else if ( tmpBH == &bh2 ) 
        adf_os_print("Tasklet2 running...\n");       
}

void 
cmnos_tasklet_test()
{
    adf_os_init_bh(NULL, &bh, test_tasklet, &bh);
    adf_os_init_bh(NULL, &bh2, test_tasklet, &bh2);
        
    adf_os_sched_bh(NULL, &bh);
    adf_os_sched_bh(NULL, &bh2);    
}

#endif



