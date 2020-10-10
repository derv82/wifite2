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
 * @ingroup adf_os_public
 * @file adf_os_types.h
 * This file defines types used in the OS abstraction API.
 */

#ifndef _ADF_OS_TYPES_H
#define _ADF_OS_TYPES_H


#include <adf_os_stdtypes.h>
#include <adf_os_types_pvt.h>

#define ADF_OS_MAX_SCATTER  __ADF_OS_MAX_SCATTER
/**
 * @brief Max number of scatter-gather segments.
 */ 
#define ADF_OS_MAX_SGLIST   4

/**
 * @brief denotes structure is packed.
 */ 
#define adf_os_packed       __adf_os_packed

/**
 * @brief handles opaque to each other
 */
typedef void *      adf_net_handle_t;
typedef void *      adf_drv_handle_t;
typedef void *      adf_os_handle_t;

/*
 * XXX FIXME For compilation only.
 *
 */
typedef void *      adf_os_pm_t;

/**
 * @brief Platform/bus generic handle. Used for bus specific functions.
 */
typedef __adf_os_device_t              adf_os_device_t;

/**
 * @brief size of an object
 */
typedef __adf_os_size_t                adf_os_size_t;

/**
 * @brief offset for API's that need them.
 */
typedef __adf_os_off_t      adf_os_off_t;

/**
 * @brief DMA mapping object.
 */ 
typedef __adf_os_dma_map_t  adf_os_dma_map_t;

/**
 * @brief DMA address.
 */ 
typedef __adf_os_dma_addr_t     adf_os_dma_addr_t;

/**
 * @brief DMA size.
 */ 
typedef __adf_os_dma_size_t     adf_os_dma_size_t;

/**
 * @brief Information inside a DMA map.
 */ 
typedef struct adf_os_dmamap_info{
    a_uint32_t                  nsegs;      /**< total number mapped segments*/
    struct __dma_segs{
        adf_os_dma_addr_t       paddr;      /**< physical(dma'able) address of the segment*/
        adf_os_dma_size_t       len;        /**< length of the segment*/
    } dma_segs[ADF_OS_MAX_SCATTER]; 

}adf_os_dmamap_info_t;

/**
 * @brief Representation of a scatter-gather list.
 */ 
typedef struct adf_os_sglist{
    a_uint32_t                  nsegs;      /**< total number of segments*/
    struct __sg_segs{
        a_uint8_t              *vaddr;      /**< Virtual address of the segment*/
        a_uint32_t              len;        /**< Length of the segment*/
    } sg_segs[ADF_OS_MAX_SGLIST];

}adf_os_sglist_t;

/**
 *  @brief All operations specified below are performed from
 *  the host memory point of view, where a read
 *  implies data coming from the device to the host
 *  memory, and a write implies data going from the
 *  host memory to the device.  Alternately, the
 *  operations can be thought of in terms of driver
 *  operations, where reading a network packet or
 *  storage sector corresponds to a read operation in
 *  bus_dma.
 * 
 *  ADF_SYNC_PREREAD       Perform any synchronization
 *                         required prior to an update
 *                         of host memory by the DMA
 *                         read operation.
 *  ADF_SYNC_PREWRITE      Perform any synchronization
 *                         required after an update of
 *                         host memory by the CPU and
 *                         prior to DMA write
 *                         operations.
 *  ADF_SYNC_POSTREAD      Perform any synchronization
 *                         required after DMA read
 *                         operations and prior to CPU
 *                         access to host
 *                         memory.
 *  ADF_SYNC_POSTWRITE     Perform any synchronization
 *                         required after DMA write
 *                                   operations.
 */

typedef enum adf_os_cache_sync{
    ADF_SYNC_PREREAD=__ADF_SYNC_PREREAD,
    ADF_SYNC_PREWRITE=__ADF_SYNC_PREWRITE,
    ADF_SYNC_POSTREAD=__ADF_SYNC_POSTREAD,
    ADF_SYNC_POSTWRITE=__ADF_SYNC_POSTWRITE
}adf_os_cache_sync_t;

/**
 * @brief Generic status to be used by adf_drv.
 */
typedef enum {
    A_STATUS_OK,
    A_STATUS_FAILED,
    A_STATUS_ENOENT,
    A_STATUS_ENOMEM,
    A_STATUS_EINVAL,
    A_STATUS_EINPROGRESS,
    A_STATUS_ENOTSUPP,
    A_STATUS_EBUSY,
    A_STATUS_E2BIG,
    A_STATUS_EADDRNOTAVAIL,
    A_STATUS_ENXIO,
    A_STATUS_EFAULT,
    A_STATUS_EIO,
} a_status_t;

/**
 * @brief An ecore needs to provide a table of all pci device/vendor id's it 
 * supports
 *
 * This table should be terminated by a NULL entry , i.e. {0}
 */
typedef struct {
    a_uint32_t vendor;
    a_uint32_t device;
    a_uint32_t subvendor;
    a_uint32_t subdevice;
}adf_os_pci_dev_id_t;

#define ADF_OS_PCI_ANY_ID  (~0)

/**
 * @brief Typically core's can use this macro to create a table of various device
 * ID's
 */
#define ADF_OS_PCI_DEVICE(_vendor, _device)   \
    (_vendor), (_device), ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID


#define adf_os_iomem_t   __adf_os_iomem_t;
/**
 * @brief These define the hw resources the OS has allocated for the device
 * Note that start defines a mapped area.
 */
typedef enum {
    ADF_OS_RESOURCE_TYPE_MEM,
    ADF_OS_RESOURCE_TYPE_IO,
}adf_os_resource_type_t;

/**
 * @brief Representation of a h/w resource.
 */ 
typedef struct {
    a_uint64_t             start;
    a_uint64_t             end;
    adf_os_resource_type_t type;
}adf_os_resource_t;

#define ADF_OS_DEV_ID_TABLE_MAX    256

/**
 * @brief Representation of bus registration data.
 */ 
typedef union {
    adf_os_pci_dev_id_t  *pci;
    void              *raw;
}adf_os_bus_reg_data_t;

/**
 * @brief Representation of data required for attach.
 */ 
typedef union {
    adf_os_pci_dev_id_t pci;
    void *raw;
}adf_os_attach_data_t;

#define ADF_OS_REGIONS_MAX     5

/**
 * @brief Types of buses.
 */ 
typedef enum {
    ADF_OS_BUS_TYPE_PCI = 1,
    ADF_OS_BUS_TYPE_GENERIC,
}adf_os_bus_type_t;

/**
 * @brief IRQ handler response codes.
 */ 
typedef enum {
    ADF_OS_IRQ_NONE,
    ADF_OS_IRQ_HANDLED,
}adf_os_irq_resp_t;

/**
 * @brief DMA mask types.
 */ 
typedef enum {
    ADF_OS_DMA_MASK_32BIT,
    ADF_OS_DMA_MASK_64BIT,
}adf_os_dma_mask_t;


/**
 * @brief DMA directions
 *        ADF_OS_DMA_TO_DEVICE (data going from device to memory)
 *        ADF_OS_DMA_FROM_DEVICE (data going from memory to device)
 */
typedef enum {
    ADF_OS_DMA_TO_DEVICE = __ADF_OS_DMA_TO_DEVICE, 
    ADF_OS_DMA_FROM_DEVICE = __ADF_OS_DMA_FROM_DEVICE, 
} adf_os_dma_dir_t;

/*
 * Protoypes shared between public and private headers
 */


/**
 * @brief work queue(kernel thread)/DPC function callback
 */
typedef void (*adf_os_defer_fn_t)(void *);

/**
 * @brief Prototype of the critical region function that is to be
 * executed with spinlock held and interrupt disalbed
 */
typedef a_bool_t (*adf_os_irqlocked_func_t)(void *);


/**
 * @brief Prototype of timer function
 */
typedef void (*adf_os_timer_func_t)(void *);

/**
 * @brief Prototype of IRQ function.
 */ 
typedef adf_os_irq_resp_t (*adf_os_drv_intr)(adf_drv_handle_t hdl);                  

/**
 * @brief The OS print routine.
 */ 
#define adf_os_print         __adf_os_print

/**
 * @brief driver info structure needed while we do the register
 *        for the driver to the shim.
 */
typedef struct _adf_drv_info{
    /**
     * @brief driver specific functions
     */
    adf_drv_handle_t (*drv_attach)  (adf_os_resource_t *res, int count, 
                                     adf_os_attach_data_t *data, 
                                     adf_os_device_t osdev);
    void       (*drv_detach)  (adf_drv_handle_t hdl);
    void       (*drv_suspend) (adf_drv_handle_t hdl, adf_os_pm_t pm);
    void       (*drv_resume)  (adf_drv_handle_t hdl);
    /**
     * @brief driver specific data
     */
    adf_os_bus_type_t          bus_type;
    adf_os_bus_reg_data_t      bus_data;
    unsigned char              *mod_name;
    unsigned char              *ifname;
}adf_drv_info_t;

#endif
