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
/*
 * @File: vdesc.c
 * 
 * @Abstract: 
 * 
 * @Notes:
 */


#include <osapi.h>
#include <vdesc_api.h>
#include <Magpie_api.h>

#include "vdesc.h"

#define VDESC_SIZE              sizeof(VDESC)
//#define VDESC_TX_SIZE           sizeof(VDESC_TX)
//#define VDESC_RX_SIZE           sizeof(VDESC_RX)

static VDESC* alloc_rx_desc(void);
static VDESC* alloc_tx_desc(void);
void _vdesc_init(int nDesc);
A_UINT8* _vdesc_get_hw_desc(VDESC *desc);
VDESC* _vdesc_alloc_desc();
void _vdesc_swap_vdesc(VDESC *dest, VDESC *src);

struct VDESC_CONTEXT g_vdescCtx;

void _vdesc_init(int nDesc) 
{
    int i;
    VDESC *vdesc;  
    //int nextAddr = dataAddr;
    //int nDesc = nTxDesc + nRxDesc;
    
    // Initialize VDESC_TX for nTxDesc number
    //vdesc = (VDESC*)dataAddr;
    vdesc = (VDESC *)A_ALLOCRAM(sizeof(VDESC));
    vdesc->next_desc = NULL;
    vdesc->control = 0;

#if 1
    g_vdescCtx.free_vdesc_head = vdesc;  
    
    for(i=1; i<nDesc; i++)
    {
        //nextAddr = dataAddr + i*VDESC_SIZE;
        //vdesc = (VDESC*)nextAddr;
        vdesc = (VDESC *)A_ALLOCRAM(sizeof(VDESC));
        
        vdesc->control = 0;
        
        vdesc->next_desc = g_vdescCtx.free_vdesc_head;
        g_vdescCtx.free_vdesc_head = vdesc;
    }    
    
    //nextAddr = nextAddr + VDESC_SIZE;
    //return nextAddr;
    return;
#else                    
    g_vdescCtx.free_vdesc_tx_head = vdesc;    
    for(i=1; i<nTxDesc; i++)
    {
        nextAddr = dataAddr + i*VDESC_TX_SIZE;
        vdesc = (VDESC*)nextAddr;
        vdesc->control = 0;
        
        vdesc->next_desc = g_vdescCtx.free_vdesc_tx_head;
        g_vdescCtx.free_vdesc_tx_head = vdesc;
    }    
    
    nextAddr = nextAddr + VDESC_TX_SIZE;
    
    // Initialize VDESC_RX for nTxDesc number
    vdesc = (VDESC*)nextAddr;
    vdesc->next_desc = NULL;
    vdesc->control = 0;
    
    g_vdescCtx.free_vdesc_rx_head = vdesc;  
    for(i=1; i<nRxDesc; i++)
    {
        //nextAddr = nextAddr + i*VDESC_RX_SIZE;
        vdesc = (VDESC*)(nextAddr + i*VDESC_RX_SIZE);
        vdesc->control = 0;
        
        vdesc->next_desc = g_vdescCtx.free_vdesc_rx_head;
        g_vdescCtx.free_vdesc_rx_head = vdesc;
    }  

    return (nextAddr + nRxDesc*VDESC_RX_SIZE);   
#endif                
}

#if 0
static VDESC* alloc_tx_desc(void)
{
    VDESC *allocDesc = NULL;
    
    if ( g_vdescCtx.free_vdesc_tx_head != NULL )
    {
        allocDesc = g_vdescCtx.free_vdesc_tx_head;
        
        //g_vbufCtx.nVbufNum--;
        
        g_vdescCtx.free_vdesc_tx_head = allocDesc->next_desc;
        allocDesc->next_desc = NULL;        
    }    
    
    return allocDesc;
}

static VDESC* alloc_rx_desc(void)
{
    VDESC *allocDesc = NULL;
    
    if ( g_vdescCtx.free_vdesc_rx_head != NULL )
    {
        allocDesc = g_vdescCtx.free_vdesc_rx_head;
        //g_vbufCtx.nVbufNum--;
        
        g_vdescCtx.free_vdesc_rx_head = allocDesc->next_desc;
        allocDesc->next_desc = NULL;        
    }    
    
    return allocDesc;    
}
#endif

VDESC* _vdesc_alloc_desc()
{
#if 1
    VDESC *allocDesc = NULL;
    
    if ( g_vdescCtx.free_vdesc_head != NULL )
    {
        allocDesc = g_vdescCtx.free_vdesc_head;
        //g_vbufCtx.nVbufNum--;
        
        g_vdescCtx.free_vdesc_head = allocDesc->next_desc;
        allocDesc->next_desc = NULL;        
    }    
    
    return allocDesc;    
#else    
    if ( type == VDESC_TYPE_RX )
    {
        return alloc_rx_desc();
    }
    else
    {
        return alloc_tx_desc();
    }
#endif    
}

A_UINT8* _vdesc_get_hw_desc(VDESC *desc)
{
#if 1
    return desc->hw_desc_buf;
#else    
    if ( type == VDESC_TYPE_RX )
    {
        return ((VDESC_RX*)desc)->hw_desc_buf;
    }
    else
    {
        return ((VDESC_TX*)desc)->hw_desc_buf;
    }
#endif    
} 

void _vdesc_swap_vdesc(VDESC *dest, VDESC *src)
{
    A_UINT32 tmp;
    A_UINT8 *tmpAddr;
        
    tmp = dest->buf_size;
    dest->buf_size = src->buf_size;
    src->buf_size = tmp;
    
    tmp = dest->data_offset;       
    dest->data_offset = src->data_offset;
    src->data_offset = tmp;
    
    tmp = dest->data_size;       
    dest->data_size = src->data_size;
    src->data_size = tmp;
        
    tmp = dest->control;
    dest->control = src->control;
    src->control = tmp;
    
    tmpAddr = dest->buf_addr;
    dest->buf_addr = src->buf_addr;
    src->buf_addr = tmpAddr;     
}

/* the exported entry point into this module. All apis are accessed through
 * function pointers */
void vdesc_module_install(struct vdesc_api *apis)
{    
        /* hook in APIs */
    apis->_init = _vdesc_init;
    apis->_alloc_vdesc = _vdesc_alloc_desc;
    apis->_get_hw_desc = _vdesc_get_hw_desc;
    apis->_swap_vdesc  = _vdesc_swap_vdesc;
    
    //apis->_free_vbuf = _vbuf_free_vbuf;
    
        /* save ptr to the ptr to the context for external code to inspect/modify internal module state */
    //apis->pReserved = &g_pMboxHWContext;
}
 

