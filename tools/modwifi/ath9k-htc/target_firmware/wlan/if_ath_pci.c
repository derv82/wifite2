/*-
 * Copyright (c) 2002-2004 Sam Leffler, Errno Consulting
 * Copyright (c) 2004 Atheros Communications, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer,
 *    without modification.
 * 2. Redistributions in binary form must reproduce at minimum a disclaimer
 *    similar to the "NO WARRANTY" disclaimer below ("Disclaimer") and any
 *    redistribution must be conditioned upon including a substantially
 *    similar Disclaimer requirement for further binary redistribution.
 * 3. Neither the names of the above-listed copyright holders nor the names
 *    of any contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * Alternatively, this software may be distributed under the terms of the
 * GNU General Public License ("GPL") version 2 as published by the Free
 * Software Foundation.
 *
 * NO WARRANTY
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF NONINFRINGEMENT, MERCHANTIBILITY
 * AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
 * THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE LIABLE FOR SPECIAL, EXEMPLARY,
 * OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
 * IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
 * THE POSSIBILITY OF SUCH DAMAGES.
 *
 * $Id: //depot/sw/branches/fusion_usb/target_firmware/wlan/target/madwifi/ath/if_ath_pci.c#1 $
 */

#ifndef EXPORT_SYMTAB
#define EXPORT_SYMTAB
#endif

#include <adf_os_types.h>
#include <adf_os_dma.h>
#include <adf_os_pci.h>
#include <adf_os_timer.h>
#include <adf_os_lock.h>
#include <adf_os_io.h>
#include <adf_os_mem.h>
#include <adf_os_module.h>
#include <adf_os_util.h>
#include <adf_os_stdtypes.h>
#include <adf_os_defer.h>
#include <adf_os_atomic.h>
#include <adf_nbuf.h>
#include <adf_net.h>
#include <adf_os_irq.h>

#include <adf_net_wcmd.h>

#include <ieee80211_var.h>
#include "if_athvar.h"
#include "if_ath_pci.h"

extern a_int32_t ath_tgt_attach(a_uint32_t devid, struct ath_softc_tgt *sc, adf_os_device_t osdev);
extern a_int32_t ath_detach(void *);
extern adf_os_irq_resp_t ath_intr(adf_drv_handle_t hdl);

struct ath_pci_softc {
	struct ath_softc_tgt aps_sc;
#ifdef CONFIG_PM
	u32 ps_pmstate[16];
#endif
};

/*
 * User a static table of PCI id's for now.  While this is the
 * "new way" to do things, we may want to switch back to having
 * the HAL check them by defining a probe method.
 */
#ifdef ATH_SUPPORT_XB_ONLY
static adf_os_pci_dev_id_t ath_pci_id_table[] = {
    { 0x168c, 0x0024, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID }, /* PCI-E (XB)    */
    { 0 },
};
#else

static adf_os_pci_dev_id_t ath_pci_id_table[] = {
    { 0x168c, 0x0007, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0x0012, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0x0013, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0xa727, 0x0013, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID }, /* 3com */
    { 0x10b7, 0x0013, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID }, /* 3com 3CRDAG675 */
    { 0x168c, 0x1014, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID }, /* IBM minipci 5212 */
    { 0x168c, 0x101a, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID }, /* some Griffin-Lite */
    { 0x168c, 0x0015, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0x0016, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0x0017, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0x0018, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0x0019, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0x001a, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0x001b, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0x001c, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0x001d, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID },
    { 0x168c, 0xff1d, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID }, /* owl emulation */
    { 0x168c, 0xff1c, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID }, /* owl emulation */
    { 0x168c, 0x0023, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID }, /* PCI (MB/CB)   */
    { 0x168c, 0x0024, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID }, /* PCI-E (XB)    */
    { 0x168c, 0x0027, ADF_OS_PCI_ANY_ID, ADF_OS_PCI_ANY_ID }, /* Sowl PCI     */
    { 0 },
};
#endif

void exit_ath_pci(void);
a_int32_t init_ath_pci(void);

static adf_drv_handle_t
ath_pci_probe(adf_os_resource_t *res,a_int32_t count, adf_os_attach_data_t *data,
	      adf_os_device_t osdev)
{
	struct ath_pci_softc *sc;
	a_uint8_t csz = 32;
	adf_os_pci_dev_id_t *id = (adf_os_pci_dev_id_t *)data;

	adf_os_pci_config_write8(osdev, ATH_PCI_CACHE_LINE_SIZE, csz);
	adf_os_pci_config_write8(osdev, ATH_PCI_LATENCY_TIMER, 0xa8);

	sc = adf_os_mem_alloc(sizeof(struct ath_pci_softc));

	if (sc == NULL) {
		adf_os_print("ath_pci: no memory for device state\n");
		goto bad2;
	}
	adf_os_mem_set(sc, 0, sizeof(struct ath_pci_softc));

	/*
	 * Mark the device as detached to avoid processing
	 * interrupts until setup is complete.
	 */
	sc->aps_sc.sc_invalid = 1;

	adf_os_print("ath_pci_probe %x\n",id->device);

	if (ath_tgt_attach(id->device, &sc->aps_sc, osdev) != 0)
		goto bad3;

	/* ready to process interrupts */
	sc->aps_sc.sc_invalid = 0;
	adf_os_setup_intr(osdev, ath_intr);
	return (adf_drv_handle_t)sc;
bad3:
bad2:
	return NULL;
}

static void
ath_pci_remove(adf_drv_handle_t hdl)
{
	struct ath_softc_tgt *sc = hdl;

	ath_detach((struct ath_softc_tgt *)hdl);
	adf_os_free_intr(sc->sc_dev);
}

static void
ath_pci_suspend(adf_drv_handle_t hdl, adf_os_pm_t pm)
{
}

static void
ath_pci_resume(adf_drv_handle_t hdl)
{
}

static adf_drv_info_t ath_drv_info = adf_os_pci_set_drv_info(ath_pci_tgt,&ath_pci_id_table[0], ath_pci_probe, ath_pci_remove, ath_pci_suspend, ath_pci_resume);

a_int32_t
init_ath_pci(void)
{
	return adf_net_register_drv( &ath_drv_info );
}

void
exit_ath_pci(void)
{
	adf_net_unregister_drv("ath_pci");
}

adf_os_pci_module_init(init_ath_pci);
adf_os_pci_module_exit(exit_ath_pci);
adf_os_module_dep(ath_pci_tgt, adf_net);
adf_os_module_dep(ath_pci_tgt, hal);
adf_os_module_dep(ath_pci_tgt, ath_pci);
adf_os_module_dep(ath_pci_tgt, wlan_tgt);
adf_os_module_dep(ath_pci_tgt, htc_tgt);
adf_os_module_dep(ath_pci_tgt, inproc_hif);
