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
 * @defgroup adf_nbuf_public network buffer API
 */ 

/**
 * @ingroup adf_nbuf_public
 * @file adf_nbuf.h
 * This file defines the network buffer abstraction.
 */ 

#ifndef _ADF_NBUF_H
#define _ADF_NBUF_H

#include <adf_os_util.h>
#include <adf_os_types.h>
#include <adf_os_dma.h>
#include <adf_net_types.h>
#include <adf_nbuf_pvt.h>

/**
 * @brief Platform indepedent packet abstraction
 */
typedef __adf_nbuf_t         adf_nbuf_t;

/**
 * @brief invalid handle
 */
#define ADF_NBUF_NULL   __ADF_NBUF_NULL
/**
 * @brief Platform independent packet queue abstraction
 */
typedef __adf_nbuf_queue_t   adf_nbuf_queue_t;

/**
 * BUS/DMA mapping routines
 */

/**
 * @brief Create a DMA map. This can later be used to map
 *        networking buffers. They :
 *          - need space in adf_drv's software descriptor
 *          - are typically created during adf_drv_create
 *          - need to be created before any API(adf_nbuf_map) that uses them
 * 
 * @param[in]  osdev os device
 * @param[out] dmap  map handle
 * 
 * @return status of the operation
 */
static inline a_status_t
adf_nbuf_dmamap_create(adf_os_device_t osdev,
                       adf_os_dma_map_t *dmap)
{
    return (__adf_nbuf_dmamap_create(osdev, dmap));
}


/**
 * @brief Delete a dmap map
 * 
 * @param[in] osdev os device
 * @param[in] dmap
 */
static inline void
adf_nbuf_dmamap_destroy(adf_os_device_t osdev, adf_os_dma_map_t dmap)
{
    __adf_nbuf_dmamap_destroy(osdev, dmap);
}


/**
 * @brief Map a buffer to local bus address space
 *
 * @param[in]  osdev   os device
 * @param[in]  bmap    map handle
 * @param[in]  buf     buf to be mapped
 * @param[in]  dir     DMA direction
 *
 * @return status of the operation
 */
static inline a_status_t
adf_nbuf_map(adf_os_device_t        osdev, 
             adf_os_dma_map_t       bmap, 
             adf_nbuf_t             buf, 
             adf_os_dma_dir_t       dir)
{
    return __adf_nbuf_map(osdev, bmap, buf, dir);
}


/**
 * @brief Unmap a previously mapped buf
 *
 * @param[in] osdev   os device
 * @param[in] bmap    map handle
 * @param[in] dir     DMA direction
 */
static inline void
adf_nbuf_unmap(adf_os_device_t      osdev, 
               adf_os_dma_map_t     bmap, 
               adf_os_dma_dir_t     dir)
{
    __adf_nbuf_unmap(osdev, bmap, dir);
}

/**
 * @brief returns information about the mapped buf
 * 
 * @param[in]  bmap map handle
 * @param[out] sg   map info
 */
static inline void
adf_nbuf_dmamap_info(adf_os_dma_map_t bmap, adf_os_dmamap_info_t *sg)
{
    __adf_nbuf_dmamap_info(bmap, sg);
}



/*
 * nbuf allocation rouines
 */


/**
 * @brief Allocate adf_nbuf
 *
 * The nbuf created is guarenteed to have only 1 physical segment
 *
 * @param[in] hdl   platform device object
 * @param[in] size  data buffer size for this adf_nbuf including max header 
 *                  size
 * @param[in] reserve  headroom to start with.
 * @param[in] align    alignment for the start buffer.
 *
 * @return The new adf_nbuf instance or NULL if there's not enough memory.
 */
static inline adf_nbuf_t 
adf_nbuf_alloc(adf_os_size_t        size,
               int                  reserve,
               int                  align)
{
    return __adf_nbuf_alloc(size, reserve,align);
}


/**
 * @brief Free adf_nbuf
 *
 * @param[in] buf buffer to free
 */
static inline void
adf_nbuf_free(adf_nbuf_t buf)
{
    __adf_nbuf_free(buf);
}


/**
 * @brief Reallocate such that there's required headroom in
 *        buf. Note that this can allocate a new buffer, or
 *        change geometry of the orignial buffer. The new buffer
 *        is returned in the (new_buf).
 * 
 * @param[in] buf (older buffer)
 * @param[in] headroom
 * 
 * @return newly allocated buffer
 */
static inline adf_nbuf_t
adf_nbuf_realloc_headroom(adf_nbuf_t buf, a_uint32_t headroom)
{
    return (__adf_nbuf_realloc_headroom(buf, headroom));
}


/**
 * @brief expand the tailroom to the new tailroom, but the buffer
 * remains the same
 * 
 * @param[in] buf       buffer
 * @param[in] tailroom  new tailroom
 * 
 * @return expanded buffer or NULL on failure
 */
static inline adf_nbuf_t
adf_nbuf_realloc_tailroom(adf_nbuf_t buf, a_uint32_t tailroom)
{
    return (__adf_nbuf_realloc_tailroom(buf, tailroom));
}


/**
 * @brief this will expand both tail & head room for a given
 *        buffer, you may or may not get a new buffer.Use it
 *        only when its required to expand both. Otherwise use
 *        realloc (head/tail) will solve the purpose. Reason for
 *        having an extra API is that some OS do this in more
 *        optimized way, rather than calling realloc (head/tail)
 *        back to back.
 * 
 * @param[in] buf       buffer
 * @param[in] headroom  new headroom  
 * @param[in] tailroom  new tailroom
 * 
 * @return expanded buffer
 */
static inline adf_nbuf_t
adf_nbuf_expand(adf_nbuf_t buf, a_uint32_t headroom, a_uint32_t tailroom)
{
    return (__adf_nbuf_expand(buf,headroom,tailroom));
}


/**
 * @brief Copy src buffer into dst. This API is useful, for
 *        example, because most native buffer provide a way to
 *        copy a chain into a single buffer. Therefore as a side
 *        effect, it also "linearizes" a buffer (which is
 *        perhaps why you'll use it mostly). It creates a
 *        writeable copy.
 * 
 * @param[in] buf source nbuf to copy from
 * 
 * @return the new nbuf
 */
static inline adf_nbuf_t
adf_nbuf_copy(adf_nbuf_t buf)
{
    return(__adf_nbuf_copy(buf));
}


/**
 * @brief link two nbufs, the new buf is piggybacked into the
 *        older one.
 * 
 * @param[in] dst   buffer to piggyback into
 * @param[in] src   buffer to put
 * 
 * @return status of the call
 */
static inline void
adf_nbuf_cat(adf_nbuf_t dst,adf_nbuf_t src)
{
    __adf_nbuf_cat(dst, src);
}


/**
 * @brief clone the nbuf (copy is readonly)
 * 
 * @param[in] buf nbuf to clone from
 * 
 * @return cloned buffer
 */
static inline adf_nbuf_t 
adf_nbuf_clone(adf_nbuf_t buf)
{
    return(__adf_nbuf_clone(buf));
}


/**
 * @brief  Create a version of the specified nbuf whose
 *         contents can be safely modified without affecting
 *         other users.If the nbuf is a clone then this function
 *         creates a new copy of the data. If the buffer is not
 *         a clone the original buffer is returned.
 * 
 * @param[in] buf   source nbuf to create a writable copy from
 * 
 * @return new buffer which is writeable
 */
static inline adf_nbuf_t 
adf_nbuf_unshare(adf_nbuf_t buf)
{
    return(__adf_nbuf_unshare(buf));
}



/*
 * nbuf manipulation routines
 */



/**
 * @brief return the amount of headroom int the current nbuf
 * 
 * @param[in] buf   buffer
 * 
 * @return amount of head room
 */
static inline a_uint32_t
adf_nbuf_headroom(adf_nbuf_t buf)
{
    return (__adf_nbuf_headroom(buf));
}


/**
 * @brief return the amount of tail space available
 * 
 * @param[in] buf   buffer
 * 
 * @return amount of tail room 
 */
static inline a_uint32_t
adf_nbuf_tailroom(adf_nbuf_t buf)
{
    return (__adf_nbuf_tailroom(buf));
}


/**
 * @brief Push data in the front
 *
 * @param[in] buf      buf instance
 * @param[in] size     size to be pushed
 *
 * @return New data pointer of this buf after data has been pushed,
 *         or NULL if there is not enough room in this buf.
 */
static inline a_uint8_t *
adf_nbuf_push_head(adf_nbuf_t buf, adf_os_size_t size)
{
    return __adf_nbuf_push_head(buf, size);
}


/**
 * @brief Puts data in the end
 *
 * @param[in] buf      buf instance
 * @param[in] size     size to be pushed
 *
 * @return data pointer of this buf where new data has to be
 *         put, or NULL if there is not enough room in this buf.
 */
static inline a_uint8_t *
adf_nbuf_put_tail(adf_nbuf_t buf, adf_os_size_t size)
{
    return __adf_nbuf_put_tail(buf, size);
}


/**
 * @brief pull data out from the front
 *
 * @param[in] buf   buf instance
 * @param[in] size     size to be popped
 *
 * @return New data pointer of this buf after data has been popped,
 *         or NULL if there is not sufficient data to pull.
 */
static inline a_uint8_t *
adf_nbuf_pull_head(adf_nbuf_t buf, adf_os_size_t size)
{
    return __adf_nbuf_pull_head(buf, size);
}


/**
 * 
 * @brief trim data out from the end
 *
 * @param[in] buf   buf instance
 * @param[in] size     size to be popped
 *
 * @return none
 */
static inline void
adf_nbuf_trim_tail(adf_nbuf_t buf, adf_os_size_t size)
{
    __adf_nbuf_trim_tail(buf, size);
}


/**
 * @brief Get the length of the buf
 *
 * @param[in] buf the buf instance
 *
 * @return The total length of this buf.
 */
static inline adf_os_size_t
adf_nbuf_len(adf_nbuf_t buf)
{
    return (__adf_nbuf_len(buf));
}

/**
 * @brief test whether the nbuf is cloned or not
 * 
 * @param[in] buf   buffer
 * 
 * @return TRUE if it is cloned, else FALSE
 */
static inline a_bool_t
adf_nbuf_is_cloned(adf_nbuf_t buf)
{
    return (__adf_nbuf_is_cloned(buf));
}



/*
 * nbuf frag routines
 */

/**
 * @brief return the frag pointer & length of the frag
 * 
 * @param[in]  buf   buffer
 * @param[out] sg    this will return all the frags of the nbuf
 * 
 */
static inline void 
adf_nbuf_frag_info(adf_nbuf_t buf, adf_os_sglist_t *sg) 
{
    __adf_nbuf_frag_info(buf, sg);
}
/**
 * @brief return the data pointer & length of the header
 * 
 * @param[in]  buf  nbuf
 * @param[out] addr data pointer
 * @param[out] len  length of the data
 *
 */
static inline void
adf_nbuf_peek_header(adf_nbuf_t buf, a_uint8_t **addr, a_uint32_t *len)
{
    __adf_nbuf_peek_header(buf, addr, len);
}
/*
 * nbuf private context routines
 */

/**
 * @brief get the priv pointer from the nbuf'f private space
 * 
 * @param[in] buf
 * 
 * @return data pointer to typecast into your priv structure
 */
static inline a_uint8_t *
adf_nbuf_get_priv(adf_nbuf_t buf)
{
    return (__adf_nbuf_get_priv(buf));
}


/*
 * nbuf queue routines
 */


/**
 * @brief Initialize buf queue
 *
 * @param[in] head  buf queue head
 */
static inline void
adf_nbuf_queue_init(adf_nbuf_queue_t *head)
{
    __adf_nbuf_queue_init(head);
}


/**
 * @brief Append a nbuf to the tail of the buf queue
 *
 * @param[in] head  buf queue head
 * @param[in] buf   buf
 */
static inline void
adf_nbuf_queue_add(adf_nbuf_queue_t *head, adf_nbuf_t buf)
{
    __adf_nbuf_queue_add(head, buf);
}


/**
 * @brief Retrieve a buf from the head of the buf queue
 *
 * @param[in] head    buf queue head
 *
 * @return The head buf in the buf queue.
 */
static inline adf_nbuf_t
adf_nbuf_queue_remove(adf_nbuf_queue_t *head)
{
    return __adf_nbuf_queue_remove(head);
}


/**
 * @brief get the length of the queue
 * 
 * @param[in] head  buf queue head
 * 
 * @return length of the queue
 */
static inline a_uint32_t
adf_nbuf_queue_len(adf_nbuf_queue_t *head)
{
    return __adf_nbuf_queue_len(head);
}


/**
 * @brief get the first guy/packet in the queue
 * 
 * @param[in] head  buf queue head
 * 
 * @return first buffer in queue
 */
static inline adf_nbuf_t 
adf_nbuf_queue_first(adf_nbuf_queue_t *head)
{
    return (__adf_nbuf_queue_first(head));
}


/**
 * @brief get the next guy/packet of the given buffer (or
 *        packet)
 * 
 * @param[in] buf   buffer
 * 
 * @return next buffer/packet
 */
static inline adf_nbuf_t
adf_nbuf_queue_next(adf_nbuf_t buf)
{
    return (__adf_nbuf_queue_next(buf));
}


/**
 * @brief Check if the buf queue is empty
 * 
 * @param[in] nbq   buf queue handle
 *
 * @return    TRUE  if queue is empty
 * @return    FALSE if queue is not emty
 */
static inline a_bool_t
adf_nbuf_is_queue_empty(adf_nbuf_queue_t * nbq)
{
    return __adf_nbuf_is_queue_empty(nbq);
}



/*
 * nbuf extension routines XXX
 */



/**
 * @brief Gets the tx checksumming to be performed on this buf
 * 
 * @param[in]  buf       buffer
 * @param[out] hdr_off   the (tcp) header start
 * @param[out] where     the checksum offset
 */
static inline adf_net_cksum_type_t
adf_nbuf_tx_cksum_info(adf_nbuf_t buf, a_uint8_t **hdr_off, a_uint8_t **where)
{
    return(__adf_nbuf_tx_cksum_info(buf, hdr_off, where));
}


/**
 * @brief Drivers that support hw checksumming use this to
 *        indicate checksum info to the stack.
 * 
 * @param[in]  buf      buffer
 * @param[in]  cksum    checksum
 */
static inline void
adf_nbuf_set_rx_cksum(adf_nbuf_t buf, adf_nbuf_rx_cksum_t *cksum)
{
    __adf_nbuf_set_rx_cksum(buf, cksum);
}


/**
 * @brief Drivers that are capable of TCP Large segment offload
 *        use this to get the offload info out of an buf.
 * 
 * @param[in]  buf  buffer
 * @param[out] tso  offload info
 */
static inline void
adf_nbuf_get_tso_info(adf_nbuf_t buf, adf_nbuf_tso_t *tso)
{
    __adf_nbuf_get_tso_info(buf, tso);
}


/*static inline void
adf_nbuf_set_vlan_info(adf_nbuf_t buf, adf_net_vlan_tag_t vlan_tag)
{
    __adf_nbuf_set_vlan_info(buf, vlan_tag);
}*/

/**
 * @brief This function extracts the vid & priority from an
 *        nbuf
 * 
 * 
 * @param[in] hdl   net handle
 * @param[in] buf   buffer
 * @param[in] vlan  vlan header
 * 
 * @return status of the operation
 */
static inline a_status_t
adf_nbuf_get_vlan_info(adf_net_handle_t hdl, adf_nbuf_t buf, 
                       adf_net_vlanhdr_t *vlan)
{
    return __adf_nbuf_get_vlan_info(hdl, buf, vlan);
}

static inline adf_nbuf_t
adf_nbuf_create_frm_frag(adf_nbuf_queue_t *head)
{
    return __adf_nbuf_create_frm_frag(head);
}

static inline void
adf_nbuf_split_to_frag(adf_nbuf_t buf, adf_nbuf_queue_t *qhead)
{
    return __adf_nbuf_split_to_frag(buf, qhead);
}

#endif
