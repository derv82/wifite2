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

/**
 * This file contains buffer Abstraction routines for FreeBSD
 * the abstracted buffer called adf_nbuf is opaque to the
 * user,hence these routines should be called to manipulate
 * anything inside it.
 */
#include <adf_net.h>
#include <osapi.h>
#include "cmnos_api.h"
#include <Magpie_api.h>
#include <vbuf_api.h>

// #############################################################################
VDESC * __adf_nbuf_last(VBUF *buf);


// #############################################################################

/**
 *  
 * @brief allocate a new nbuf,
 * 
 * @param hdl (adf_net handle)
 * @param size (size of the new buf)
 * @param reserve (amount of space to reserve in the head)
 * 
 * @return newly allocated nbuf
 */
__adf_nbuf_t 
__adf_nbuf_alloc(adf_os_size_t size, a_uint32_t reserve, 
                 a_uint32_t align)
{
    VBUF *buf = NULL;
    VDESC *desc;
    
    buf = VBUF_alloc_vbuf();
    if ( buf != NULL ) {
        desc = VDESC_alloc_vdesc();
        desc->buf_addr = (A_UINT8 *)A_ALLOCRAM(size);
        desc->buf_size = size;
        desc->next_desc = NULL;
        desc->data_offset = reserve;
        desc->data_size = 0;
        desc->control = 0;    
        
        buf->desc_list = desc;
        buf->buf_length = 0;    
    }
    
    return buf;
}   
  
/**
 * @brief Free the nbuf
 * function to be called in
 * @param hdl
 * @param adf_nbuf
 * 
 */
void __adf_nbuf_free(__adf_nbuf_t  buf)
{
    adf_os_assert(0);
}

/**
 * @brief reallocate the head space, call it only after the you
 *        have called headroom
 * 
 * @param adf_nbuf
 * @param headroom   
 * 
 * @return new nbuf
 */
__adf_nbuf_t 
__adf_nbuf_realloc_headroom(__adf_nbuf_t buf, a_uint32_t headroom)
{
    adf_os_assert(0);
    return NULL;
}

/**
 * @brief expand the tailroom, mostly by adding the new tail
 *        buffer, also take care of the priv
 * 
 * @param buf
 * @param tailroom
 * 
 * @return struct mbuf * (buffer with the new tailroom)
 */
__adf_nbuf_t 
__adf_nbuf_realloc_tailroom(__adf_nbuf_t  buf, a_uint32_t tailroom)
{
    adf_os_assert(0);
    return NULL;
}

/**
 * @brief expand the headroom or tailroom or both
 * 
 * @param buf
 * @param headroom ( 0 if no headroom expansion req)
 * @param tailroom ( 0 if no tailroom expansion req)
 * 
 * @return struct mbuf* (NULL if something goofed up)
 */
__adf_nbuf_t 
__adf_nbuf_expand(__adf_nbuf_t buf, a_uint32_t headroom, a_uint32_t tailroom)
{
    adf_os_assert(0);
    return NULL;
}

/**
 * @brief put data in the head
 * 
 * @param buf
 * @param len (how much data to put)
 * 
 * @return new data pointer ,NULL if the len is more than the
 *         space available in the head frag.
 */
a_uint8_t *       
__adf_nbuf_push_head(__adf_nbuf_t buf, adf_os_size_t len)
{
    a_uint8_t *ptr = NULL; 
    VDESC *desc = buf->desc_list;
    
    desc->data_offset -= len;
    desc->data_size += len;
    buf->buf_length += len;
    ptr = desc->buf_addr + desc->data_offset;
    return(ptr);
}

/**
 * 
 * @brief add data in the end of tail
 * 
 * @param buf
 * @param len (how much data to put)
 * 
 * @return previous tail (data+len),NULL if the len is more than
 *         space available
 */
a_uint8_t *
__adf_nbuf_put_tail(__adf_nbuf_t buf, adf_os_size_t len)
{
    a_uint8_t *tail = NULL;
    VDESC *last_desc = __adf_nbuf_last(buf);
    
    tail = last_desc->buf_addr + last_desc->data_offset + last_desc->data_size;
    last_desc->data_size += len;
    buf->buf_length += len;
    
    return tail;
}

/**
 * @brief strip data from head
 * 
 * @param adf_nbuf
 * @param len (how much data to rip)
 * 
 * @return new data pointer
 */
a_uint8_t * 
__adf_nbuf_pull_head(__adf_nbuf_t buf, adf_os_size_t len)
{
    a_uint8_t *ptr = NULL;
    VDESC *desc = buf->desc_list;
    
    desc->data_offset += len;
    desc->data_size -= len;
    buf->buf_length -= len;
    ptr = desc->buf_addr + desc->data_offset;
    
    return ptr;
}
/**
 * @brief strip data from tail, priv safe
 * 
 * @param buf
 * @param len (how much to strip down)
 * 
 */
void 
__adf_nbuf_trim_tail(__adf_nbuf_t buf, adf_os_size_t len)
{
    VDESC *last_desc = __adf_nbuf_last(buf);
    
    adf_os_assert(buf != NULL);
    last_desc->data_size -= len;
    buf->buf_length -= len;
    
    //adf_os_assert(0);    //0820
}
/**
 * @brief Copy assumes that we create a writeable copy of the
 *        nbuf which is equivalent in FreeBSD as duping the
 *        mbuf.
 * 
 * @param src
 * 
 * @return struct mbuf * (newly allocated buffer)
 */
__adf_nbuf_t 
__adf_nbuf_copy(__adf_nbuf_t src)
{
    __adf_nbuf_t buf = NULL; 

    adf_os_assert(src != NULL);
    
    return buf;
}
/**
 * @brief make the writable copy of the nbuf
 * 
 * @param adf_nbuf
 * 
 * @return new nbuf
 */
__adf_nbuf_t 
__adf_nbuf_unshare(__adf_nbuf_t  src)
{
    __adf_nbuf_t buf = NULL;

    adf_os_assert(src != NULL);

    return buf;
}

/**
 * @brief return the frag data & len, where frag no. is
 *        specified by the index
 * 
 * @param[in] buf
 * @param[out] sg (scatter/gather list of all the frags)
 * 
 */
void  
__adf_nbuf_frag_info(__adf_nbuf_t buf, adf_os_sglist_t	*sg)
{
    VDESC *desc = buf->desc_list;
    int count = 0;
    
    while( desc != NULL ) {
        sg->sg_segs[count].vaddr = desc->buf_addr + desc->data_offset;
        sg->sg_segs[count].len   = desc->data_size;
        
        count++;        
        desc = desc->next_desc;
    }
    
    sg->nsegs = count;
}
/**
 * @brief retrieve the priv space pointer from nbuf
 * 
 * @param buf (nbuf to attach the priv space)
 * 
 * @return uint8_t* ( pointer to the data )
 */
a_uint8_t *
__adf_nbuf_get_priv(__adf_nbuf_t buf)
{
    adf_os_assert(buf != NULL);

    return buf->ctx;
}

/**
 * 
 * @brief append the nbuf to the queue
 * 
 * @param adf_qhead
 * @param adf_nbuf
 * 
 */
void 
__adf_nbuf_queue_add(__adf_nbuf_qhead_t  *qhead, 
                     __adf_nbuf_t  buf)
{
    qhead->qlen++;

    buf->next_buf = NULL;

    if (qhead->head == NULL) {
        qhead->head = buf;
    }
    else {
        qhead->tail->next_buf = buf;
    }
    qhead->tail = buf;
}

/**
 * @brief dequeue an nbuf
 * 
 * @param adf_qhead
 * 
 * @return the nbuf
 */
__adf_nbuf_t   
__adf_nbuf_queue_remove(__adf_nbuf_qhead_t *qhead)
{
    __adf_nbuf_t  b0 = NULL;

    if (qhead->head) {
        qhead->qlen--;
        b0 = qhead->head;
        if ( qhead->head == qhead->tail ) {
            qhead->head = NULL;
            qhead->tail = NULL;
        } else {
            qhead->head = qhead->head->next_buf;
        }
    
        b0->next_buf = NULL;
    }
	return b0;
}

/**
 * ****************DMA Routines Start Here*****************
 */


/**
 * @brief creates a streaming mapping (takes a pre allocated
 *        global tag for 4K mbuf sizes)
 * 
 * @param hdl
 * @param max_sz
 * @param dmap
 * 
 * @return a_status_t
 */
a_status_t 
__adf_nbuf_dmamap_create(__adf_os_device_t osdev, __adf_os_dma_map_t *dmap)
{
    a_status_t retval = A_STATUS_OK;
    
    (*dmap) = A_ALLOCRAM(sizeof(struct __adf_dma_map));
    if(*dmap == NULL)
        return A_STATUS_ENOMEM;
            
    (*dmap)->buf = NULL;
    return retval;
}


a_status_t 
__adf_nbuf_map(__adf_os_device_t osdev, __adf_os_dma_map_t bmap, 
                          __adf_nbuf_t buf, adf_os_dma_dir_t dir)
{   
    bmap->buf = buf;
    
    return A_STATUS_OK;
}

void 
__adf_nbuf_unmap(__adf_os_device_t osdev, __adf_os_dma_map_t bmap, 
                            adf_os_dma_dir_t dir)
{
    bmap->buf = NULL;
    
    return;
}

void
__adf_nbuf_dmamap_destroy(__adf_os_device_t osdev, 
                          __adf_os_dma_map_t dmap)
{
    //dmap->buf = NULL;
    
    // Should not be called in FW!
    //return A_STATUS_OK;
}



/**
 * @brief return the dma map info 
 * 
 * @param[in]  bmap
 * @param[out] sg (map_info ptr)
 */
void 
__adf_nbuf_dmamap_info(__adf_os_dma_map_t bmap, adf_os_dmamap_info_t *sg)
{
    VDESC *desc = bmap->buf->desc_list;
    int count = 0;
    
    while( desc != NULL ) {
        sg->dma_segs[count].paddr = (adf_os_dma_addr_t)(desc->buf_addr + desc->data_offset);
        sg->dma_segs[count].len   = desc->data_size;
        
        count++;        
        desc = desc->next_desc;
    }
    
    sg->nsegs = count;    
}

/**
 * **************************Misc routines***************
 */


/**
 * @brief sets the cksum type & value for nbuf
 * XXX: not fully implemented
 * 
 * @param buf
 * @param cksum
 */
void 
__adf_nbuf_set_rx_cksum(__adf_nbuf_t buf, adf_nbuf_rx_cksum_t *cksum)
{

}

a_status_t      
__adf_nbuf_get_vlan_info(adf_net_handle_t hdl, __adf_nbuf_t buf, 
                         adf_net_vlanhdr_t *vlan)
{
    return A_STATUS_OK;
}

__adf_nbuf_t
__adf_nbuf_create_frm_frag(__adf_nbuf_queue_t *qhead)
{
    VBUF *buf_tmp, *buf_head = NULL;
    VDESC *vdesc_prev = NULL, *vdesc_tmp = NULL;
    a_uint32_t cnt = 0, len = __adf_nbuf_queue_len(qhead);
    a_uint16_t total_len = 0;

    buf_head = VBUF_alloc_vbuf();
    buf_tmp = __adf_nbuf_queue_first(qhead);

    __adf_os_assert(buf_head);
    __adf_os_assert(buf_tmp);

    buf_head->desc_list = buf_tmp->desc_list;

    while ((buf_tmp = __adf_nbuf_queue_remove(qhead)) != NULL) {
        cnt++;

        //adf_os_print("merge buf: %x\n", buf_tmp->desc_list->buf_addr + buf_tmp->desc_list->data_offset);

        total_len += buf_tmp->buf_length;

        if (vdesc_prev) {
            /* link "the last VDESC of previous VBUF" to "the 1st VDESC of this VBUF" */
            vdesc_prev->next_desc = buf_tmp->desc_list;
        }

        /* traverse VDESC list in this VBUF to find out the last VDESC */
        vdesc_tmp = buf_tmp->desc_list;
        while (vdesc_tmp->next_desc) {
            vdesc_tmp = vdesc_tmp->next_desc;
        }
        vdesc_prev = vdesc_tmp;

        /* return VBUF to the pool */
        buf_tmp->desc_list = NULL;
        buf_tmp->buf_length = 0;
        VBUF_free_vbuf(buf_tmp);
    }

    if (cnt != len) {
        //adf_os_print("cnt: %x, len: %x, __adf_nbuf_queue_len: %x\n", cnt, len, 
        //             __adf_nbuf_queue_len(qhead));
        adf_os_assert(0);
    }
    //__adf_os_assert(cnt == len);

    buf_head->buf_length = total_len;

    return buf_head;
}

void
__adf_nbuf_split_to_frag(__adf_nbuf_t buf, __adf_nbuf_qhead_t *qhead)
{
    VBUF *buf_tmp;
    VDESC *desc_tmp = NULL;

    __adf_nbuf_queue_init(qhead);
    desc_tmp = buf->desc_list;

    while (desc_tmp /*&& desc_tmp->buf_addr*/) {
        buf_tmp = VBUF_alloc_vbuf();

        __adf_os_assert(buf_tmp);

        //desc_tmp->data_size = 0;
        buf_tmp->desc_list = desc_tmp;
        //buf_tmp->buf_length = desc_tmp->buf_size;
        buf_tmp->buf_length = desc_tmp->data_size;
        buf_tmp->next_buf = NULL;

        //adf_os_print("split - buf: %x\n", buf_tmp->desc_list->buf_addr + buf_tmp->desc_list->data_offset);

        __adf_nbuf_queue_add(qhead, buf_tmp);

        desc_tmp = desc_tmp->next_desc;

        buf_tmp->desc_list->next_desc = NULL;
    }

    buf->desc_list = NULL;
    buf->buf_length = 0;
    VBUF_free_vbuf(buf);
    
}

/**
 * @brief return the last mbuf
 * 
 * @param m0
 * 
 * @return struct mbuf*
 */
VDESC * 
__adf_nbuf_last(VBUF *buf)
{
    VDESC *desc = buf->desc_list;
    
    //for(; desc->next_desc != NULL; desc = desc->next_desc)
    //    ;
    while(desc->next_desc != NULL)
    {
        desc = desc->next_desc;
    }
    
    return desc;
}

/**
 * @brief num bytes in the head
 * 
 * @param adf_nbuf
 * 
 * @return num of bytes available
 */
a_uint32_t
__adf_nbuf_headroom(__adf_nbuf_t  buf)
{
    return buf->desc_list->data_offset;
}


/**
 * @brief num of bytes available in the tail excluding the priv
 *        portion
 * 
 * @param adf_nbuf
 * 
 * @return num of bytes
 */

a_uint32_t 
__adf_nbuf_tailroom(__adf_nbuf_t  buf)
{
    VDESC *last_desc = __adf_nbuf_last(buf);
    
    return last_desc->buf_size - last_desc->data_offset - last_desc->data_size;
}

/**
 * @brief get the entire packet length
 * 
 * @param adf_nbuf
 * 
 * @return total length of packet (sum of all frag lengths)
 */ 
a_uint32_t
__adf_nbuf_len(__adf_nbuf_t  buf)
{
    return buf->buf_length; 
}

/**
 * @brief Clone the nbuf (will not create writeable copies)
 * 
 * @param adf_nbuf
 * 
 * @return Read-only copy of the nbuf (including clusters)
 */
__adf_nbuf_t 
__adf_nbuf_clone(__adf_nbuf_t  src)
{
    __adf_nbuf_t buf = NULL;
    
    return buf;
}

void
__adf_nbuf_cat(__adf_nbuf_t dst, __adf_nbuf_t src)
{

}



/*
 * @brief check if the mbuf is cloned or not
 * 
 * @param buf
 * 
 * @return a_bool_t
 */
a_bool_t
__adf_nbuf_is_cloned(__adf_nbuf_t  buf)
{
    return A_FALSE;
}
/**
 * @brief This will return the header's addr & m_len
 */
void
__adf_nbuf_peek_header(__adf_nbuf_t buf, a_uint8_t   **addr, 
                       a_uint32_t	*len)
{
    VDESC *desc = buf->desc_list;
    
    *addr = desc->buf_addr + desc->data_offset;
    *len = desc->data_size; 
}
/**
 * @brief init the queue
 * @param qhead
 */
void 
__adf_nbuf_queue_init(__adf_nbuf_qhead_t *qhead)
{
    qhead->qlen = 0;
    qhead->head = NULL;
    qhead->tail = NULL;
}
/**
 * @brief return the length of queue
 * @param adf_qhead
 * 
 * @return length
 * 
 */
a_uint32_t  
__adf_nbuf_queue_len(__adf_nbuf_qhead_t *qhead)
{
    return qhead->qlen;
}
/**
 * @brief returns the first guy in the Q
 * @param qhead
 * 
 * @return (NULL if the Q is empty)
 */
__adf_nbuf_t   
__adf_nbuf_queue_first(__adf_nbuf_queue_t *qhead)
{
    return qhead->head;
}
/**
 * @brief return the next packet from packet chain
 * 
 * @param buf (packet)
 * 
 * @return (NULL if no packets are there)
 */
__adf_nbuf_t   
__adf_nbuf_queue_next(__adf_nbuf_t  buf)
{
    return buf->next_buf;
}
/**
 * @brief check if the queue is empty or not
 * 
 * @param qhead
 * 
 * @return a_bool_t
 */
a_bool_t  
__adf_nbuf_is_queue_empty(__adf_nbuf_qhead_t *qhead)
{
    return ((qhead->qlen == 0));
}
