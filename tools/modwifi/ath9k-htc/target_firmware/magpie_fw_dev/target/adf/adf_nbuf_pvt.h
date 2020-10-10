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
 *  FreeBSD specific prototypes 
 */
#ifndef _ADF_NBUF_PVT_H
#define _ADF_NBUF_PVT_H

#include <osapi.h>
//#include <Magpie_api.h>
#include <vbuf_api.h>
//#include <adf_nbuf_api.h>

#define __ADF_NBUF_NULL         NULL
#define __ADF_NBUF_CTX_BUF      

typedef VBUF *     __adf_nbuf_t;

/**
 * queue head
 */
typedef struct __adf_nbuf_qhead {
    VBUF             *head;
    VBUF             *tail;    
    a_uint32_t        qlen;
}__adf_nbuf_qhead_t;

typedef __adf_nbuf_qhead_t         __adf_nbuf_queue_t;

__adf_nbuf_t 
__adf_nbuf_alloc(adf_os_size_t size, 
                 a_uint32_t reserve, a_uint32_t align);                                

void 
__adf_nbuf_free(__adf_nbuf_t  buf);

a_uint8_t *   
__adf_nbuf_push_head(__adf_nbuf_t buf, adf_os_size_t size);
 
a_uint8_t *    
__adf_nbuf_pull_head(__adf_nbuf_t buf, adf_os_size_t size);

a_uint8_t *    
__adf_nbuf_put_tail(__adf_nbuf_t buf, adf_os_size_t size);

void         
__adf_nbuf_trim_tail(__adf_nbuf_t buf, adf_os_size_t size);

__adf_nbuf_t 
__adf_nbuf_realloc_headroom(__adf_nbuf_t buf,
                            a_uint32_t headroom);                           
                            
__adf_nbuf_t 
__adf_nbuf_realloc_tailroom(__adf_nbuf_t buf, 
                            a_uint32_t tailroom);
                                                
__adf_nbuf_t 
__adf_nbuf_expand(__adf_nbuf_t buf,
                               a_uint32_t headroom, a_uint32_t tailroom);
                                                                               
__adf_nbuf_t 
__adf_nbuf_copy(__adf_nbuf_t src);

__adf_nbuf_t 
__adf_nbuf_unshare(__adf_nbuf_t  src);

void         
__adf_nbuf_frag_info(__adf_nbuf_t buf, adf_os_sglist_t *sg);

a_uint8_t *    
__adf_nbuf_get_priv(__adf_nbuf_t buf);
void         
__adf_nbuf_queue_add(__adf_nbuf_qhead_t *qhead, 
                     __adf_nbuf_t buf);
                                  
__adf_nbuf_t 
__adf_nbuf_queue_remove(__adf_nbuf_qhead_t *qhead);

a_uint32_t     
__adf_nbuf_tx_cksum_info(__adf_nbuf_t buf, 
                         a_uint8_t **hdr_off, 
                         a_uint8_t **where);
                                      
void         
__adf_nbuf_set_rx_cksum(__adf_nbuf_t buf, adf_nbuf_rx_cksum_t *cksum);
void         
__adf_nbuf_get_tso_info(__adf_nbuf_t buf, adf_nbuf_tso_t *tso);

a_status_t   
__adf_nbuf_get_vlan_info(adf_net_handle_t hdl, 
                                      __adf_nbuf_t buf, 
                                      adf_net_vlanhdr_t *vlan);                                                                                                
                                       
void         
__adf_nbuf_dmamap_info(__adf_os_dma_map_t bmap, adf_os_dmamap_info_t *sg);

/**
 * @brief return the last mbuf
 * 
 * @param m0
 * 
 * @return struct mbuf*
 */
VDESC * 
__adf_nbuf_last(VBUF *buf);

/**
 * @brief num bytes in the head
 * 
 * @param adf_nbuf
 * 
 * @return num of bytes available
 */
a_uint32_t
__adf_nbuf_headroom(__adf_nbuf_t  buf);

/**
 * @brief num of bytes available in the tail excluding the priv
 *        portion
 * 
 * @param adf_nbuf
 * 
 * @return num of bytes
 */

a_uint32_t 
__adf_nbuf_tailroom(__adf_nbuf_t  buf);

/**
 * @brief get the entire packet length
 * 
 * @param adf_nbuf
 * 
 * @return total length of packet (sum of all frag lengths)
 */ 
a_uint32_t
__adf_nbuf_len(__adf_nbuf_t  buf);

/**
 * @brief Clone the nbuf (will not create writeable copies)
 * 
 * @param adf_nbuf
 * 
 * @return Read-only copy of the nbuf (including clusters)
 */
__adf_nbuf_t 
__adf_nbuf_clone(__adf_nbuf_t  src);

void
__adf_nbuf_cat(__adf_nbuf_t dst, __adf_nbuf_t src);


/*
 * @brief check if the mbuf is cloned or not
 * 
 * @param buf
 * 
 * @return a_bool_t
 */
a_bool_t
__adf_nbuf_is_cloned(__adf_nbuf_t  buf);

/**
 * @brief This will return the header's addr & m_len
 */
void
__adf_nbuf_peek_header(__adf_nbuf_t buf, a_uint8_t   **addr, 
                       a_uint32_t	*len);

/**
 * @brief init the queue
 * @param qhead
 */
void 
__adf_nbuf_queue_init(__adf_nbuf_qhead_t *qhead);

/**
 * @brief return the length of queue
 * @param adf_qhead
 * 
 * @return length
 * 
 */
a_uint32_t  
__adf_nbuf_queue_len(__adf_nbuf_qhead_t *qhead);

/**
 * @brief returns the first guy in the Q
 * @param qhead
 * 
 * @return (NULL if the Q is empty)
 */
__adf_nbuf_t   
__adf_nbuf_queue_first(__adf_nbuf_queue_t *qhead);

/**
 * @brief return the next packet from packet chain
 * 
 * @param buf (packet)
 * 
 * @return (NULL if no packets are there)
 */
__adf_nbuf_t   
__adf_nbuf_queue_next(__adf_nbuf_t  buf);

/**
 * @brief check if the queue is empty or not
 * 
 * @param qhead
 * 
 * @return a_bool_t
 */
a_bool_t  
__adf_nbuf_is_queue_empty(__adf_nbuf_qhead_t *qhead);

__adf_nbuf_t
__adf_nbuf_create_frm_frag(__adf_nbuf_queue_t *head);
void
__adf_nbuf_split_to_frag(__adf_nbuf_t buf, __adf_nbuf_queue_t *qhead);

a_status_t      __adf_nbuf_dmamap_create(__adf_os_device_t osdev, 
                                         __adf_os_dma_map_t *dmap);

void            __adf_nbuf_dmamap_destroy(__adf_os_device_t osdev, 
                                          __adf_os_dma_map_t dmap);

a_status_t      __adf_nbuf_map(__adf_os_device_t osdev, __adf_os_dma_map_t dmap,
                                __adf_nbuf_t buf, adf_os_dma_dir_t dir);
void            __adf_nbuf_unmap(__adf_os_device_t osdev, __adf_os_dma_map_t dmap,
                               adf_os_dma_dir_t dir);

#endif

