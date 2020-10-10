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
#include <osapi.h>
#include <Magpie_api.h>
#include <adf_os_types.h>
#include <adf_os_pci.h>
#include <adf_net.h>
#include <sys_cfg.h>

#if MAGPIE_ENABLE_WLAN == 0
A_PCI_INIT_FUNC g_pci_init_func;
#endif

#if MAGPIE_ENABLE_PCIE == 0
#define EMULATE_PCI_CONFIG
#endif

#define PCI_CONFIG_BASE_ADDR        0x14000000 

extern A_PCI_INIT_FUNC g_pci_init_func;
adf_drv_info_t* g_wlan_drv = NULL;
adf_drv_handle_t g_wlan_drv_handle = NULL;
adf_os_drv_intr g_wlan_intr = NULL;

void wlan_pci_module_init(void)
{
	if (g_pci_init_func != NULL) {
		g_pci_init_func();
	}
}

void wlan_pci_register_drv(adf_drv_info_t *drv)
{
	g_wlan_drv = drv;
}

#define ATHEROS_VENDOR_ID 0x168c
#define AR5416_DEVID_PCIE 0x24 	

void wlan_pci_probe(void)
{
	__adf_softc_t           *sc;
	adf_os_resource_t       drv_res = {0};
	adf_os_attach_data_t    drv_data = {{0}};   
	int vendor_id;
	int device_id;

	A_PRINTF("<wlan_pci_probe>: Attaching the driver\n");

#if MAGPIE_ENABLE_PCIE == 0
	vendor_id = ATHEROS_VENDOR_ID;
	device_id = AR5416_DEVID_PCIE;
#else    
	vendor_id = wlan_pci_config_read(0, 2);
	device_id = wlan_pci_config_read(2, 2);
#endif    
	A_PRINTF("<wlan_pci_probe>: Vendor id 0x%x Dev id 0x%x\n", vendor_id, device_id);    
    
	if (vendor_id != ATHEROS_VENDOR_ID) {
		A_PRINTF("<wlan_pci_probe>: Atheros card not found\n"); 
		return;
	}
            
	/**
	 * Allocate the sc & zero down
	 */
	sc = A_ALLOCRAM(sizeof(__adf_softc_t));
	if (!sc) {
		A_PRINTF("Cannot malloc softc\n");
		goto mem_fail;
	}
    
#define AR5416_DEVID_PCIE 0x24 		

	drv_data.pci.device    = AR5416_DEVID_PCIE;
	drv_data.pci.vendor    = 0x168c;
	drv_data.pci.subvendor = 0;
	drv_data.pci.subdevice = 0;
    
	drv_res.start  = (a_uint32_t) 0;
	drv_res.end    = 0;
	drv_res.type   = ADF_OS_RESOURCE_TYPE_MEM;
        
	g_wlan_drv_handle = g_wlan_drv->drv_attach(&drv_res, 1, &drv_data, NULL);
        
	return;
mem_fail:
	return;        
}

int wlan_pci_config_write(int offset, a_uint32_t val, int width)
{
#if MAGPIE_ENABLE_PCIE == 1    
	unsigned long addr = ( PCI_CONFIG_BASE_ADDR + offset ) & 0xfffffffc;
	A_UINT8 *ptr = (A_UINT8 *)addr;   
	A_UINT8 *valptr = (A_UINT8 *)&val; 
	int idx = offset & 0x3;
	int i;
    
	for (i = 0; i < width; i++) {
		ptr[idx + i] = valptr[3-i];
	}            
#endif
    
	return 0;    
}

int wlan_pci_config_read(int offset, int width)
{
#if MAGPIE_ENABLE_PCIE == 0    
	return 0;    
#else
	unsigned long addr = ( PCI_CONFIG_BASE_ADDR + offset ) & 0xfffffffc;
	unsigned long value = *((unsigned long *)addr);
	A_UINT8 *ptr = (A_UINT8 *)&value;   
	int idx = offset & 0x3;
	int result = 0;
	int i;
    
	for (i = 0; i < width; i++) {
		result |= (ptr[ 3 - (idx + i)] << (8*i));
	}            
    
	return result;    
#endif    
}

void wlan_pci_isr()
{
	if (g_wlan_intr != NULL && g_wlan_drv_handle != NULL) {
		g_wlan_intr(g_wlan_drv_handle);
	}
}
