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
 * @File: Magpie_api.h
 * 
 * @Abstract: Magpie FW api
 * 
 * @Notes:
 */

#ifndef _MAGPIE_API_H
#define _MAGPIE_API_H

#include <sys_cfg.h>
#include "cmnos_api.h"
#include "vbuf_api.h"
#include "vdesc_api.h"
#include "usbfifo_api.h"
#include "hif_api.h"
#include "htc_api.h"
#include "wmi_svc_api.h"
#include "buf_pool_api.h"
#include "dma_engine_api.h"
#include "dma_lib.h"
#if defined(PROJECT_K2)
#include "sflash_api.h"
#endif

#define A_INDIR(sym)   _A_MAGPIE_INDIRECTION_TABLE->sym

#if SYSTEM_MODULE_DBG
/* debug Support */
#define DBG_MODULE_INSTALL()            cmnos_dbg_module_install(&_A_MAGPIE_INDIRECTION_TABLE->dbg)
#define A_DBG_INIT()                    A_INDIR(dbg._dbg_init())
#define A_DBG_TASK()                    A_INDIR(dbg._dbg_task())
#else
#define DBG_MODULE_INSTALL()
#define A_DBG_INIT()
#define A_DBG_TASK()
#endif

/* Serial Flash support */
#if SYSTEM_MODULE_SFLASH
#define SFLASH_MODULE_INSTALL()                 cmnos_sflash_module_install(&_A_MAGPIE_INDIRECTION_TABLE->sflash)
#define A_SFLASH_INIT()                         A_INDIR(sflash._sflash_init())
#define A_SFLASH_ERASE(erase_type, addr)        A_INDIR(sflash._sflash_erase(erase_type, addr))
#define A_SFLASH_PROG(addr, len, buf)           A_INDIR(sflash._sflash_program(addr, len, buf))
#define A_SFLASH_READ(fast, addr, len, buf)     A_INDIR(sflash._sflash_read(fast, addr, len, buf))
#define A_SFLASH_RDSR()                         A_INDIR(sflash._sflash_rdsr())
#else
#define SFLASH_MODULE_INSTALL()
#define A_SFLASH_INIT()
#define A_SFLASH_ERASE(erase_type, addr)
#define A_SFLASH_PROG(addr, len, buf)
#define A_SFLASH_READ(fast, addr, len, buf)
#define A_SFLASH_RDSR()
#endif

/* DMA Engine Interface */
#define DMA_ENGINE_MODULE_INSTALL()                 dma_engine_module_install(&_A_MAGPIE_INDIRECTION_TABLE->dma_engine);
#define DMA_Engine_init()                           A_INDIR(dma_engine._init())
#define DMA_Engine_config_rx_queue(q, nDesc, size)  A_INDIR(dma_engine._config_rx_queue(q, nDesc, size))
#define DMA_Engine_xmit_buf(q, buf)                 A_INDIR(dma_engine._xmit_buf(q, buf))
#define DMA_Engine_flush_xmit(q)                    A_INDIR(dma_engine._flush_xmit(q))
#define DMA_Engine_reap_recv_buf(q)                 A_INDIR(dma_engine._reap_recv_buf(q))
#define DMA_Engine_return_recv_buf(q,buf)           A_INDIR(dma_engine._return_recv_buf(q, buf))
#define DMA_Engine_reap_xmited_buf(q)               A_INDIR(dma_engine._reap_xmited_buf(q))
#define DMA_Engine_swap_data(desc)                  A_INDIR(dma_engine._swap_data(desc))
#define DMA_Engine_init_rx_queue(q)                 A_INDIR(dma_engine._init_rx_queue(q))
#define DMA_Engine_init_tx_queue(q)                 A_INDIR(dma_engine._init_tx_queue(q))
#define DMA_Engine_has_compl_packets(q)             A_INDIR(dma_engine._has_compl_packets(q))
#define DMA_Engine_desc_dump(q)                     A_INDIR(dma_engine._desc_dump(q))
#define DMA_Engine_get_packet(q)                    A_INDIR(dma_engine._get_packet(q))
#define DMA_Engine_reclaim_packet(q,desc)           A_INDIR(dma_engine._reclaim_packet(q,desc))
#define DMA_Engine_put_packet(q,desc)               A_INDIR(dma_engine._put_packet(q,desc))

/*DMA Library support for GMAC & PCI(E)*/
#define DMA_LIB_MODULE_INSTALL()                    dma_lib_module_install(&_A_MAGPIE_INDIRECTION_TABLE->dma_lib)
#define dma_lib_tx_init(eng_no, if_type)            A_INDIR(dma_lib.tx_init(eng_no, if_type))
#define dma_lib_rx_init(eng_no, if_type)            A_INDIR(dma_lib.rx_init(eng_no, if_type))
#define dma_lib_rx_config(eng_no, desc, gran)       A_INDIR(dma_lib.rx_config(eng_no, desc, gran))
#define dma_lib_tx_start(eng_no)                    A_INDIR(dma_lib.tx_start(eng_no)) 
#define dma_lib_rx_start(eng_no)                    A_INDIR(dma_lib.rx_start(eng_no)) 
#define dma_lib_intr_status(if_type)                A_INDIR(dma_lib.intr_status(if_type))
#define dma_lib_hard_xmit(eng_no, buf)              A_INDIR(dma_lib.hard_xmit(eng_no, buf))
#define dma_lib_flush_xmit(eng_no)                  A_INDIR(dma_lib.flush_xmit(eng_no))
#define dma_lib_xmit_done(eng_no)                   A_INDIR(dma_lib.xmit_done(eng_no))
#define dma_lib_reap_xmitted(eng_no)                A_INDIR(dma_lib.reap_xmitted(eng_no))
#define dma_lib_reap_recv(eng_no)                   A_INDIR(dma_lib.reap_recv(eng_no))
#define dma_lib_return_recv(eng_no, buf)            A_INDIR(dma_lib.return_recv(eng_no, buf))
#define dma_lib_recv_pkt(eng_no)                    A_INDIR(dma_lib.recv_pkt(eng_no))

/* HIF support */
#define HIF_MODULE_INSTALL()                        hif_module_install(&_A_MAGPIE_INDIRECTION_TABLE->hif)
#define HIF_init(pConfig)                           A_INDIR(hif._init(pConfig))
#define HIF_shutdown(h)                             A_INDIR(hif._shutdown(h))
#define HIF_register_callback(h, pConfig)           A_INDIR(hif._register_callback(h, pConfig))
#define HIF_start(h)                                A_INDIR(hif._start(h))  
#define HIF_config_pipe(h, pipe, desc_list)         A_INDIR(hif._config_pipe(h, pipe, desc_list)) 
#define HIF_send_buffer(h, pipe, buf)               A_INDIR(hif._send_buffer(h, pipe, buf)) 
#define HIF_return_recv_buf(h, pipe, buf)           A_INDIR(hif._return_recv_buf(h, pipe, buf)) 
#define HIF_isr_handler(h)                          A_INDIR(hif._isr_handler(h)) 
#define HIF_is_pipe_supported(h, pipe)              A_INDIR(hif._is_pipe_supported(h, pipe))
#define HIF_get_max_msg_len(h, pipe)                A_INDIR(hif._get_max_msg_len(h, pipe))
#define HIF_get_reserved_headroom(h)                A_INDIR(hif._get_reserved_headroom(h))
#define HIF_get_default_pipe(h,u,d)                 A_INDIR(hif._get_default_pipe(h,u,d))

/* VBUF APIs */
#define VBUF_MODULE_INSTALL()                       vbuf_module_install(&_A_MAGPIE_INDIRECTION_TABLE->vbuf)
#define VBUF_init(nBuf)                             A_INDIR(vbuf._init(nBuf))
#define VBUF_alloc_vbuf()                           A_INDIR(vbuf._alloc_vbuf())
#define VBUF_free_vbuf(buf)                         A_INDIR(vbuf._free_vbuf(buf))

/* VDESC APIs */
#define VDESC_MODULE_INSTALL()                      vdesc_module_install(&_A_MAGPIE_INDIRECTION_TABLE->vdesc)
#define VDESC_init(nDesc)                           A_INDIR(vdesc._init(nDesc))
#define VDESC_alloc_vdesc()                         A_INDIR(vdesc._alloc_vdesc())
#define VDESC_get_hw_desc(desc)                     A_INDIR(vdesc._get_hw_desc(desc))
#define VDESC_swap_vdesc(dst, src)                  A_INDIR(vdesc._swap_vdesc(dst, src))

#define HTC_MODULE_INSTALL()                        htc_module_install(&_A_MAGPIE_INDIRECTION_TABLE->htc)
#define HTC_init(SetupComplete, pConfig)            A_INDIR(htc._HTC_Init(SetupComplete, pConfig))
#define HTC_Shutdown(h)                             A_INDIR(htc._HTC_Shutdown(h))
#define HTC_RegisterService(h, s)                   A_INDIR(htc._HTC_RegisterService(h, s))
#define HTC_Ready(h)                                A_INDIR(htc._HTC_Ready(h))
#define HTC_SendMsg(h, endpt, buf)                  A_INDIR(htc._HTC_SendMsg(h, endpt, buf))
#define HTC_ReturnBuffers(h, endpt, buf)            A_INDIR(htc._HTC_ReturnBuffers(h, endpt, buf))
#define HTC_ReturnBuffersList(h, endpt, hd)         A_INDIR(htc._HTC_ReturnBuffersList(h, endpt, hd))
#define HTC_GetReservedHeadroom(h)                  A_INDIR(htc._HTC_GetReservedHeadroom(h))

#define HTC_NotifyTargetInserted(h)
#define HTC_NotifyTargetDetached(h)                   

/* WMI SVC module */
#define WMI_SERVICE_MODULE_INSTALL()                WMI_service_module_install(&_A_MAGPIE_INDIRECTION_TABLE->wmi_svc_api)
#define WMI_Init(pCfg)                              A_INDIR(wmi_svc_api._WMI_Init(pCfg))
#define WMI_RegisterDispatchTable(h,pT)             A_INDIR(wmi_svc_api._WMI_RegisterDispatchTable(h, pT))
#define WMI_AllocEvent(h,ec,len)                    A_INDIR(wmi_svc_api._WMI_AllocEvent(h, ec, len))
#define WMI_SendEvent(h,ev,id,seq,len)              A_INDIR(wmi_svc_api._WMI_SendEvent(h, ev, id, seq, len))
#define WMI_GetPendingEventsCount()                 A_INDIR(wmi_svc_api._WMI_GetPendingEventsCount())
#define WMI_GetControlEp()                          A_INDIR(wmi_svc_api._WMI_GetControlEp())
#define WMI_SendCompleteHandler(ep, buf)            A_INDIR(wmi_svc_api._WMI_SendCompleteHandler(ep, buf))
#define WMI_Shutdown(h)                             A_INDIR(wmi_svc_api._WMI_Shutdown(h))

/* USB FIFO module */
#define USBFIFO_MODULE_INSTALL()                    usbfifo_module_install(&_A_MAGPIE_INDIRECTION_TABLE->usbfifo_api)
#define USBFIFO_init(pConfig)                       A_INDIR(usbfifo_api._init(pConfig))
#define USBFIFO_enable_event_isr()                  A_INDIR(usbfifo_api._enable_event_isr())

/* BUF pool module */
#define BUF_POOL_MODULE_INSTALL()                       buf_pool_module_install(&_A_MAGPIE_INDIRECTION_TABLE->buf_pool)
#define BUF_Pool_init(h)                                A_INDIR(buf_pool._init(h))
#define BUF_Pool_shutdown(h)                            A_INDIR(buf_pool._shutdown(h))
#define BUF_Pool_create_pool(h, id, nItems, nSize)      A_INDIR(buf_pool._create_pool(h, id, nItems, nSize))
#define BUF_Pool_alloc_buf(h, id, reserve)              A_INDIR(buf_pool._alloc_buf(h, id, reserve))
#define BUF_Pool_alloc_buf_align(h, id, reserve,align)  A_INDIR(buf_pool._alloc_buf_align(h, id, reserve,align))
#define BUF_Pool_free_buf(h, id, buf)                   A_INDIR(buf_pool._free_buf(h, id, buf))

/*
 * This defines the layout of the indirection table, which
 * is used to access exported APIs of various modules.  The
 * layout is shared across ROM and RAM code.  RAM code may
 * call into ROM and ROM code may call into RAM.  Because
 * of the latter, existing offsets must not change for the
 * lifetime of a revision of ROM; but new members may be
 * added at the end.
 */
typedef struct _A_magpie_indirection_table {
	_A_cmnos_indirection_table_t        cmnos;
	struct dbg_api                      dbg;
	struct sflash_api                   sflash;
	struct hif_api                      hif;
	struct htc_apis                     htc;
	WMI_SVC_APIS                        wmi_svc_api;     
	struct usbfifo_api                  usbfifo_api;
	struct buf_pool_api                 buf_pool;
	struct vbuf_api                     vbuf;
	struct vdesc_api                    vdesc;
	struct allocram_api                 allocram;
	struct dma_engine_api               dma_engine;
	struct dma_lib_api                  dma_lib;
} _A_magpie_indirection_table_t;

extern _A_magpie_indirection_table_t _indir_tbl;
#define _A_MAGPIE_INDIRECTION_TABLE_SIZE sizeof(_A_magpie_indirection_table_t)
#if defined(__mips__)
#define _A_MAGPIE_INDIRECTION_TABLE ((_A_magpie_indirection_table_t *)0x700)
#else
#define _A_MAGPIE_INDIRECTION_TABLE (&_indir_tbl)
#endif

#endif
