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
#ifndef __ADF_OS_PCI_PVT_H
#define __ADF_OS_PCI_PVT_H

#include <wlan_pci.h>

//extern A_PCI_INIT_FUNC g_pci_init_func;

/**
 * init module macro
 */
#define __adf_os_pci_module_init(_fn)   A_PCI_INIT_FUNC g_pci_init_func = _fn;

/**
 * exit module macro
 */
#define __adf_os_pci_module_exit(_fn)   

/**
 * initiallize the PCI driver structure
 * Instance name will be <name>_pci_info
 */
#define __adf_os_pci_set_drv_info(_name, _pci_ids, _attach, _detach, _suspend, _resume)  \
{   \
    (_attach),  \
    (_detach),  \
    (_suspend),    \
    (_resume),  \
    ADF_OS_BUS_TYPE_PCI,    \
    { (_pci_ids)},   \
     #_name    \
};

/**
 * XXX: pci functions undone
 * @param osdev
 * @param offset
 * @param val
 * 
 * @return int
 */
static inline int 
__adf_os_pci_config_read8(adf_os_device_t osdev, int offset, a_uint8_t *val)
{
    (*val) = wlan_pci_config_read(offset, 1);
	return 0;
    /**
     * XXX:how do we know the read succeded
     */
}

static inline int 
__adf_os_pci_config_write8(adf_os_device_t osdev, int offset, a_uint8_t val)
{
    wlan_pci_config_write(offset, val, 1);
    return 0;    
}

static inline int 
__adf_os_pci_config_read16(adf_os_device_t osdev, int offset, a_uint16_t *val)
{
    (*val) = wlan_pci_config_read(offset, 2);
    return 0;
}

static inline int 
__adf_os_pci_config_write16(adf_os_device_t osdev, int offset, a_uint16_t val)
{
    wlan_pci_config_write(offset, val, 2);
    return 0;  
}

static inline int 
__adf_os_pci_config_read32(adf_os_device_t osdev, int offset, a_uint32_t *val)
{
    (*val) = wlan_pci_config_read(offset, 4);
    return 0;
}

static inline int 
__adf_os_pci_config_write32(adf_os_device_t osdev, int offset, a_uint32_t val)
{
    wlan_pci_config_write(offset, val, 4);
    return 0;  
}

#endif
