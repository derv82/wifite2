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
 * @file adf_os_pci.h
 * This file abstracts the PCI subsystem.
 */
#ifndef __ADF_OS_PCI_H
#define __ADF_OS_PCI_H

#include <adf_os_pci_pvt.h>

/**
 * @brief Define the entry point for the PCI module.
 */ 
#define adf_os_pci_module_init(_fn)     __adf_os_pci_module_init(_fn)

/**
 * @brief Define the exit point for the PCI module.
 */ 
#define adf_os_pci_module_exit(_fn)     __adf_os_pci_module_exit(_fn)

/**
 * @brief Setup the following driver information: name, PCI IDs of devices
 * supported and some device handlers.
 */ 
#define adf_os_pci_set_drv_info(_name, _pci_ids, _attach, _detach, _suspend, _resume) \
    __adf_os_pci_set_drv_info(_name, _pci_ids, _attach, _detach, _suspend, _resume)

/**
 * @brief Read a byte of PCI config space.
 *
 * @param[in]  osdev    platform device instance
 * @param[in]  offset   offset to read
 * @param[out] val      value read
 *
 * @return status of operation
 */ 
static inline int 
adf_os_pci_config_read8(adf_os_device_t osdev, int offset, a_uint8_t *val)
{
    return __adf_os_pci_config_read8(osdev, offset, val);
}

/**
 * @brief Write a byte to PCI config space.
 *
 * @param[in] osdev    platform device instance
 * @param[in] offset   offset to write
 * @param[in] val      value to write
 *
 * @return status of operation
 */ 
static inline int 
adf_os_pci_config_write8(adf_os_device_t osdev, int offset, a_uint8_t val)
{
    return __adf_os_pci_config_write8(osdev, offset, val);
}

/**
 * @brief Read 2 bytes of PCI config space.
 *
 * @param[in]  osdev    platform device instance
 * @param[in]  offset   offset to read
 * @param[out] val      value read
 *
 * @return status of operation
 */ 
static inline int 
adf_os_pci_config_read16(adf_os_device_t osdev, int offset, a_uint16_t *val)
{
    return __adf_os_pci_config_read16(osdev, offset, val);
}

/**
 * @brief Write 2 bytes to PCI config space.
 *
 * @param[in] osdev    platform device instance
 * @param[in] offset   offset to write
 * @param[in] val      value to write
 *
 * @return status of operation
 */ 
static inline int 
adf_os_pci_config_write16(adf_os_device_t osdev, int offset, a_uint16_t val)
{
    return __adf_os_pci_config_write16(osdev, offset, val);
}

/**
 * @brief Read 4 bytes of PCI config space.
 *
 * @param[in]  osdev    platform device instance
 * @param[in]  offset   offset to read
 * @param[out] val      value read
 *
 * @return status of operation
 */ 
static inline int 
adf_os_pci_config_read32(adf_os_device_t osdev, int offset, a_uint32_t *val)
{
    return __adf_os_pci_config_read32(osdev, offset, val);
}

/**
 * @brief Write 4 bytes to PCI config space.
 *
 * @param[in] osdev    platform device instance
 * @param[in] offset   offset to write
 * @param[in] val      value to write
 *
 * @return status of operation
 */ 
static inline int 
adf_os_pci_config_write32(adf_os_device_t osdev, int offset, a_uint32_t val)
{
    return __adf_os_pci_config_write32(osdev, offset, val);
}
#endif

