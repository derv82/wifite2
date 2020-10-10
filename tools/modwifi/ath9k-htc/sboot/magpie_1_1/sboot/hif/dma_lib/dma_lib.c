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
#include <dt_defs.h>
#include <osapi.h>
#include <dma_engine_api.h>
#include <Magpie_api.h>
#include <vbuf_api.h>
#include <Magpie_api.h>

#include "dma_lib.h"
/***********************Constants***************************/

/**
 * @brief Descriptor specific bitmaps
 */
enum __dma_desc_status{
    DMA_STATUS_OWN_DRV = 0x0,
    DMA_STATUS_OWN_DMA = 0x1,
    DMA_STATUS_OWN_MSK = 0x3
};

enum __dma_bit_op{
    DMA_BIT_CLEAR  = 0x0,
    DMA_BIT_SET    = 0x1
};

enum __dma_burst_size{
    DMA_BURST_4W   = 0x00,
    DMA_BURST_8W   = 0x01,
    DMA_BURST_16W  = 0x02
};
enum __dma_byte_swap{
    DMA_BYTE_SWAP_OFF = 0x00,
    DMA_BYTE_SWAP_ON  = 0x01
};
/**
*  @brief Interrupt status bits
 */
typedef enum __dma_intr_bits{
    DMA_INTR_TX1_END   = (1 << 25),/*TX1 reached the end or Under run*/
    DMA_INTR_TX0_END   = (1 << 24),/*TX0 reached the end or Under run*/
    DMA_INTR_TX1_DONE  = (1 << 17),/*TX1 has transmitted a packet*/
    DMA_INTR_TX0_DONE  = (1 << 16),/*TX1 has transmitted a packet*/
    DMA_INTR_RX3_END   = (1 << 11),/*RX3 reached the end or Under run*/
    DMA_INTR_RX2_END   = (1 << 10),/*RX2 reached the end or Under run*/
    DMA_INTR_RX1_END   = (1 << 9), /*RX1 reached the end or Under run*/
    DMA_INTR_RX0_END   = (1 << 8), /*RX0 reached the end or Under run*/
    DMA_INTR_RX3_DONE  = (1 << 3), /*RX3 received a packet*/
    DMA_INTR_RX2_DONE  = (1 << 2), /*RX2 received a packet*/
    DMA_INTR_RX1_DONE  = (1 << 1), /*RX1 received a packet*/
    DMA_INTR_RX0_DONE  = 1,        /*RX0 received a packet*/
}__dma_intr_bits_t;
/**
 * @brief Base addresses for various HIF
 */
typedef enum __dma_base_off{
    DMA_BASE_OFF_HST  = 0x00053000,
    DMA_BASE_OFF_GMAC = 0x00054000,
    DMA_BASE_OFF_PCI  = DMA_BASE_OFF_HST,
    DMA_BASE_OFF_PCIE = DMA_BASE_OFF_HST
}__dma_base_off_t;
/**
 * @brief Engine offset to add for per engine register reads or
 *        writes
 */
typedef enum __dma_eng_off{
    DMA_ENG_OFF_RX0 = 0x800,
    DMA_ENG_OFF_RX1 = 0x900,
    DMA_ENG_OFF_RX2 = 0xa00,
    DMA_ENG_OFF_RX3 = 0xb00,
    DMA_ENG_OFF_TX0 = 0xc00,
    DMA_ENG_OFF_TX1 = 0xd00
}__dma_eng_off_t;
/**
 *@brief DMA registers
 */
typedef enum __dma_reg_off{
    /**
     * Common or Non Engine specific
     */
    DMA_REG_IFTYPE   = 0x00,/*XXX*/
    DMA_REG_ISR      = 0x00,/*Interrupt Status Register*/
    DMA_REG_IMR      = 0x04,/*Interrupt Mask Register*/
    /**
     * Transmit
     */
    DMA_REG_TXDESC   = 0x00,/*TX DP*/
    DMA_REG_TXSTART  = 0x04,/*TX start*/
    DMA_REG_INTRLIM  = 0x08,/*TX Interrupt limit*/
    DMA_REG_TXBURST  = 0x0c,/*TX Burst Size*/
    DMA_REG_TXSWAP   = 0x18,
    /**
     * Receive
     */
    DMA_REG_RXDESC   = 0x00,/*RX DP*/
    DMA_REG_RXSTART  = 0x04,/*RX Start*/
    DMA_REG_RXBURST  = 0x08,/*RX Burst Size*/
    DMA_REG_RXPKTOFF = 0x0c,/*RX Packet Offset*/
    DMA_REG_RXSWAP   = 0x1c
}__dma_reg_off_t;

/*******************************Data types******************************/

typedef struct zsDmaDesc    __dma_desc_t;

typedef struct zsDmaQueue   __dma_rxq_t;

typedef struct zsTxDmaQueue  __dma_txq_t;

/**
 * @brief Register Address
 */
typedef struct __dma_reg_addr{
    __dma_base_off_t     base;/*Base address, Fixed*/
    __dma_eng_off_t      eng;/*Engine offset, Fixed*/
}__dma_reg_addr_t;

/**
 * @brief DMA engine's Queue
 */
typedef struct __dma_eng_q{
   __dma_reg_addr_t     addr;
   union{
        __dma_rxq_t          rx_q;
        __dma_txq_t          tx_q;
   }u;
}__dma_eng_q_t;

#define rxq         u.rx_q
#define txq         u.tx_q

/***********************Defines*****************************/
     
#define DMA_ADDR_INIT(_eng)     {   \
    .base = DMA_BASE_OFF_HST,       \
    .eng  = DMA_ENG_OFF_##_eng      \
}
/**
 * @brief check if the val doesn't lie between the low & high of
 *        the engine numbers
 */
#define DMA_ENG_CHECK(_val, _low, _high)    \
    ((_val) < DMA_ENGINE_##_low || (_val) > DMA_ENGINE_##_high)
    

/********************************Globals*************************************/

__dma_eng_q_t    eng_q[DMA_ENGINE_MAX] = {
    {.addr = DMA_ADDR_INIT(RX0)},
    {.addr = DMA_ADDR_INIT(RX1)},
    {.addr = DMA_ADDR_INIT(RX2)},
    {.addr = DMA_ADDR_INIT(RX3)},
    {.addr = DMA_ADDR_INIT(TX0)},
    {.addr = DMA_ADDR_INIT(TX1)},
};   

/**********************************API's*************************************/

/**
 * @brief Read the register
 * 
 * @param addr
 * 
 * @return A_UINT32
 */
A_UINT32
__dma_reg_read(A_UINT32 addr)
{
    return *((volatile A_UINT32 *)addr);
}
/**
 * @brief Write into the register
 * 
 * @param addr
 * @param val
 */
void
__dma_reg_write(A_UINT32 addr, A_UINT32 val)
{
    *((volatile A_UINT32 *)addr) = val;
}
/**
 * @brief Set the base address
 * 
 * @param eng_no
 * @param if_type
 */
void
__dma_set_base(dma_engine_t  eng_no, dma_iftype_t if_type)
{
    switch (if_type) {
    case DMA_IF_GMAC:
        eng_q[eng_no].addr.base = DMA_BASE_OFF_GMAC;
        break;
    case DMA_IF_PCI:
        eng_q[eng_no].addr.base = DMA_BASE_OFF_PCI;
        break;
    case DMA_IF_PCIE:
        eng_q[eng_no].addr.base = DMA_BASE_OFF_PCIE;
        break;
    default:
        return;
    }
}
/**
 * @brief init the Transmit queue
 * 
 * @param eng_no
 * @param if_type
 * 
 * @return A_UINT16
 */
A_UINT16
__dma_lib_tx_init(dma_engine_t  eng_no, dma_iftype_t  if_type)
{
    __dma_desc_t  *head = NULL;
    A_UINT32     addr;

    if(DMA_ENG_CHECK(eng_no, TX0, TX1))
        return 1;

    DMA_Engine_init_tx_queue(&eng_q[eng_no].txq);

    __dma_set_base(eng_no, if_type); 

    addr  = eng_q[eng_no].addr.base + eng_q[eng_no].addr.eng;

    head = eng_q[eng_no].txq.head;

    __dma_reg_write(addr + DMA_REG_TXDESC,(A_UINT32)head);
    __dma_reg_write(addr + DMA_REG_TXBURST, DMA_BURST_16W);
    __dma_reg_write(addr + DMA_REG_TXSWAP, DMA_BYTE_SWAP_ON);

    return 0;
}

void
__dma_lib_rx_config(dma_engine_t   eng_no, A_UINT16   num_desc, 
                    A_UINT16     gran)
{
    __dma_desc_t     *desc = NULL;
    A_UINT32       addr = 0;

    /**
     * Allocate the Receive Queue
     */
    DMA_Engine_config_rx_queue(&eng_q[eng_no].rxq, num_desc, gran);

    desc  = eng_q[eng_no].rxq.head;
    addr  = eng_q[eng_no].addr.base + eng_q[eng_no].addr.eng;
    /**
     * Update RX queue head in the H/W, set the burst & say go
     */
    __dma_reg_write(addr + DMA_REG_RXDESC, (A_UINT32)desc);
    __dma_reg_write(addr + DMA_REG_RXBURST, DMA_BURST_8W);
    __dma_reg_write(addr + DMA_REG_RXSWAP,  DMA_BYTE_SWAP_ON);
    __dma_reg_write(addr + DMA_REG_RXSTART, DMA_BIT_SET);

}
    
/**
 * @brief Initialize the DMA engine
 * 
 * @param rx_desc
 * 
 * @return A_UINT16
 */
A_UINT16 
__dma_lib_rx_init(dma_engine_t   eng_no, dma_iftype_t     if_type)
{
    if(DMA_ENG_CHECK(eng_no, RX0, RX3))
        return 1;

    /**
     * XXX:The init can be called multiple times to setup different
     * geometries of descriptors
     */
    DMA_Engine_init_rx_queue(&eng_q[eng_no].rxq);

    __dma_set_base(eng_no, if_type);
    
    return 0;
}
/**
 * @brief Transmit VBUF for the specified engine number
 * 
 * @param VBUF
 * 
 * @return A_UINT16
 */
A_UINT16      
__dma_hard_xmit(dma_engine_t eng_no, VBUF *vbuf)
{
    A_UINT32 addr;

    addr = eng_q[eng_no].addr.base + eng_q[eng_no].addr.eng;

    DMA_Engine_xmit_buf(&eng_q[eng_no].txq, vbuf);
    /**
     * Say go
     */
    __dma_reg_write(addr + DMA_REG_TXSTART, DMA_BIT_SET);
}
/**
 * @brief return a VBUF for the specified engine number
 * 
 * @param eng_no
 * 
 * @return VBUF*
 */
VBUF *
__dma_reap_xmitted(dma_engine_t eng_no)
{
    return DMA_Engine_reap_xmited_buf(&eng_q[eng_no].txq);
}
/**
 * @brief flush all xmitted & to be xmitted (if you have the
 *        window) dudes from H/W
 * 
 * @param eng_no
 */
void            
__dma_flush_xmit(dma_engine_t  eng_no)
{
    A_UINT32 addr;
    __dma_desc_t  *desc, *term;

    addr = eng_q[eng_no].addr.base + eng_q[eng_no].addr.eng;

    desc = eng_q[eng_no].txq.head;
    term = eng_q[eng_no].txq.terminator;

    /**
     * XXX: I don't know how to kick the all dudes out, Ideally
     * there should be a DMA reset button (the red one)
     */
    __dma_reg_write(addr + DMA_REG_TXSTART, DMA_BIT_CLEAR);
    __dma_reg_write(addr + DMA_REG_TXDESC,(A_UINT32)term);

    /**
     * Make the H/W queue ready for TX reap
     */
    for(;desc != term; desc = desc->nextAddr)
        desc->status = DMA_STATUS_OWN_DRV;

//    DMA_Engine_flush_xmit(&eng_q[eng_no].txq);
}
/**
 * @brief check if there are xmitted vbufs (dudes) hanging
 *        around
 * 
 * @param eng_no
 * 
 * @return A_UINT16
 */
A_UINT16
__dma_xmit_done(dma_engine_t  eng_no)
{
    if(DMA_ENG_CHECK(eng_no, TX0, TX1))
        return 0;

    return DMA_Engine_has_compl_packets(&eng_q[eng_no].txq);        
}
/**
 * @brief Reap VBUF's from the specified engine number
 * 
 * @param eng
 * 
 * @return VBUF*
 */
VBUF *
__dma_reap_recv(dma_engine_t  eng)
{
    return DMA_Engine_reap_recv_buf(&eng_q[eng].rxq);
}
/**
 * @brief return to source, put the vbuf back into the queue, In
 *        case the Engine is stopped so start it again
 * 
 * @param eng_no
 * @param vbuf
 */
void
__dma_return_recv(dma_engine_t  eng_no, VBUF *vbuf)
{
    A_UINT32 addr;

    addr = eng_q[eng_no].addr.base + eng_q[eng_no].addr.eng;

    DMA_Engine_return_recv_buf(&eng_q[eng_no].rxq, vbuf);

    __dma_reg_write(addr + DMA_REG_RXSTART, DMA_BIT_SET);
}
/**
 * @brief check if there are freshly arrived vbufs (dudes)
 * 
 * @param eng_no
 * 
 * @return A_UINT16
 */
A_UINT16
__dma_recv_pkt(dma_engine_t  eng_no)
{
    if(DMA_ENG_CHECK(eng_no, RX0, RX3))
        return 0;

    return DMA_Engine_has_compl_packets(&eng_q[eng_no].rxq);        
}

void
dma_lib_module_install(struct dma_lib_api  *apis)
{
    apis->tx_init      = __dma_lib_tx_init;
    apis->rx_init      = __dma_lib_rx_init;
    apis->rx_config    = __dma_lib_rx_config;
    apis->hard_xmit    = __dma_hard_xmit;
    apis->flush_xmit   = __dma_flush_xmit;
    apis->xmit_done    = __dma_xmit_done;
    apis->reap_recv    = __dma_reap_recv;
    apis->reap_xmitted = __dma_reap_xmitted;
    apis->return_recv  = __dma_return_recv;
    apis->recv_pkt     = __dma_recv_pkt;
}
