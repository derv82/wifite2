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
#include "dt_defs.h"
#include "athos_api.h"

#include "regdump.h"
#include "usb_defs.h"

#include "adf_os_io.h"

#include "init.h"
#include <linux/compiler.h>

// @TODO: Should define the memory region later~
#define ALLOCRAM_START       ( ((unsigned int)&_fw_image_end) + 4)
#define ALLOCRAM_SIZE        ( SYS_RAM_SZIE - ( ALLOCRAM_START - SYS_D_RAM_REGION_0_BASE) - SYS_D_RAM_STACK_SIZE)

// support for more than 64 bytes on command pipe
extern void usb_reg_out_patch(void);
extern int _HIFusb_get_max_msg_len_patch(hif_handle_t handle, int pipe);
extern void _HIFusb_isr_handler_patch(hif_handle_t h);
extern BOOLEAN bSet_configuration_patch(void);
extern void vUSBFIFO_EP6Cfg_FS_patch(void);
extern void usb_status_in_patch(void);
extern void _fw_usbfifo_init(USB_FIFO_CONFIG *pConfig);
extern void zfTurnOffPower_patch(void);
extern void zfResetUSBFIFO_patch(void);
extern void _HIFusb_start_patch(hif_handle_t handle);
extern void hif_pci_patch_install(struct hif_api *apis);
extern BOOLEAN bGet_descriptor_patch(void);
extern BOOLEAN bStandardCommand_patch(void);

// patch for clock
extern void cmnos_clock_init_patch(a_uint32_t refclk);
extern a_uint32_t cmnos_refclk_speed_get_patch(void);
extern void cmnos_delay_us_patch(int us);
extern void cmnos_tick_patch(void);
extern a_uint32_t cmnos_milliseconds_patch(void);

extern BOOLEAN bJumptoFlash;
extern BOOLEAN bEepromExist;

void __section(boot) __noreturn __visible app_start(void)
{
	uint32_t rst_status;
	A_HOSTIF hostif;
#if defined(PROJECT_MAGPIE)
	T_EEP_RET retEEP;
#endif

	/* Zero BSS segment & dynamic memory section. */
	init_mem();

#if defined(PROJECT_MAGPIE)
	fatal_exception_func();
#endif

	if( IS_FLASHBOOT() ) {
		athos_indirection_table_install();
		DBG_MODULE_INSTALL();
		A_CLOCK_INIT(SYSTEM_CLK);
		A_UART_INIT();
		A_PRINTF_INIT();
		A_DBG_INIT();
		A_EEP_INIT();
		A_TASKLET_INIT();
		_indir_tbl.cmnos.timer._timer_init();

#if defined(PROJECT_K2)
		/*
		 * WAR: these variable is not initialized when boot from flash
		 *      either re-enumeration or config them to default value = 0 would fix the issue
		 */
		u8UsbInterfaceAlternateSetting = u8UsbConfigValue = u8UsbInterfaceValue = 0;
#endif
	}
#ifdef ROM_VER_1_1
	else
		A_EEP_INIT(); /*Required for 1_1*/
#endif

#if defined(PROJECT_MAGPIE)
	retEEP = A_EEP_IS_EXIST();
	bJumptoFlash = FALSE;
	if ( RET_SUCCESS == retEEP ) {
		bEepromExist = TRUE;
	} else {
		bEepromExist = FALSE;
	}
#endif

	hostif = A_IS_HOST_PRESENT();

#if defined(PROJECT_MAGPIE)
	rst_status = ioread32(WATCH_DOG_MAGIC_PATTERN_ADDR);
#elif defined(PROJECT_K2)
	rst_status = ioread32(MAGPIE_REG_RST_STATUS_ADDR);
#endif /* #if defined(PROJECT_MAGPIE) */


	A_PRINTF(" A_WDT_INIT()\n\r");

#if defined(PROJECT_K2)
	save_cmnos_printf = fw_cmnos_printf;
#endif

	if( hostif == HIF_USB ) {
#if defined(PROJECT_K2)
#if MOVE_PRINT_TO_RAM
		save_cmnos_printf = _indir_tbl.cmnos.printf._printf;
		_indir_tbl.cmnos.printf._printf = fw_cmnos_printf;
#endif
		_indir_tbl.cmnos.usb._usb_fw_task = _fw_usb_fw_task;
		_indir_tbl.cmnos.usb._usb_reset_fifo = _fw_usb_reset_fifo;
#endif
	}

	if( rst_status == WDT_MAGIC_PATTERN ) {
		A_PRINTF(" ==>WDT reset<==\n");
#if defined(PROJECT_MAGPIE)
		reset_EP4_FIFO();
#endif
		*((volatile uint32_t*)WATCH_DOG_RESET_COUNTER_ADDR)+=1;
	} else if (rst_status == SUS_MAGIC_PATTERN) {
		A_PRINTF(" ==>warm start<==\n");
	} else
		A_PRINTF(" ==>cold start<==\n");

#if defined(PROJECT_MAGPIE)
	*((volatile uint32_t*)WATCH_DOG_MAGIC_PATTERN_ADDR)=WDT_MAGIC_PATTERN;
#elif defined(PROJECT_K2)
	iowrite32(MAGPIE_REG_RST_STATUS_ADDR, WDT_MAGIC_PATTERN);
#endif /* #if defined(PROJECT_MAGPIE) */

	/* intr enable would left for firmware */
	/* athos_interrupt_init(); */

	DBG_MODULE_INSTALL();
#if defined(PROJECT_K2)
	A_DBG_INIT();
#endif

#if defined(PROJECT_K2)
#if SYSTEM_MODULE_SFLASH
	SFLASH_MODULE_INSTALL();
	A_SFLASH_INIT();
#endif
#endif

	HIF_MODULE_INSTALL();
	HTC_MODULE_INSTALL();
	WMI_SERVICE_MODULE_INSTALL();
	BUF_POOL_MODULE_INSTALL();
	VBUF_MODULE_INSTALL();
	VDESC_MODULE_INSTALL();

	//init each module, should be put together..
	A_PRINTF("ALLOCRAM start 0x%x size %d\n", ALLOCRAM_START, ALLOCRAM_SIZE);
	A_ALLOCRAM_INIT(ALLOCRAM_START, ALLOCRAM_SIZE);

	if( hostif == HIF_USB ) {
		_indir_tbl.hif._get_max_msg_len = _HIFusb_get_max_msg_len_patch;
		_indir_tbl.cmnos.usb._usb_reg_out = usb_reg_out_patch;
		_indir_tbl.hif._isr_handler = _HIFusb_isr_handler_patch;
		_indir_tbl.cmnos.usb._usb_set_configuration = bSet_configuration_patch;
		_indir_tbl.cmnos.usb._usb_status_in = usb_status_in_patch;
		_indir_tbl.cmnos.usb._usb_get_descriptor = bGet_descriptor_patch;
		_indir_tbl.cmnos.usb._usb_standard_cmd = bStandardCommand_patch;
		_indir_tbl.usbfifo_api._init = _fw_usbfifo_init;

#if defined(PROJECT_MAGPIE)
		_indir_tbl.cmnos.usb._usb_power_off = zfTurnOffPower_patch;
		_indir_tbl.cmnos.usb._usb_reset_fifo = zfResetUSBFIFO_patch;
		_indir_tbl.hif._start = _HIFusb_start_patch;
		_indir_tbl.htc._HTC_MsgRecvHandler = HTCMsgRecvHandler_patch;
		_indir_tbl.htc._HTC_ControlSvcProcessMsg = HTCControlSvcProcessMsg_patch;
#endif

		if (!(ioread8_usb(ZM_MAIN_CTRL_OFFSET) & BIT6))
			vUSBFIFO_EP6Cfg_FS_patch();

#ifdef FUSION_USB_ENABLE_TX_STREAM
		// For K2, enable tx stream mode
		A_PRINTF("Enable Tx Stream mode: 0x%x\r\n",
			ioread32_usb(ZM_SOC_USB_MODE_CTRL_OFFSET));

		/* Patch for K2 USB STREAM mode */
		/* disable down stream DMA mode */
		io32_rmw_usb(ZM_SOC_USB_MODE_CTRL_OFFSET, BIT6, BIT0);
#if SYSTEM_MODULE_HP_EP5
		io32_set_usb(ZM_SOC_USB_MODE_CTRL_OFFSET, BIT8);
#endif

#if SYSTEM_MODULE_HP_EP6
		io32_set_usb(ZM_SOC_USB_MODE_CTRL_OFFSET, BIT9);
#endif
		/* enable down stream DMA mode */
		io32_set_usb(ZM_SOC_USB_MODE_CTRL_OFFSET, BIT0);
#endif

#ifdef FUSION_USB_ENABLE_RX_STREAM
		/* Patch for K2 USB STREAM mode */
		/* disable upstream DMA mode and enable upstream stream mode */
		io32_clr_usb(ZM_SOC_USB_MODE_CTRL_OFFSET, BIT1 | BIT3);

		/* K2, Set maximum IN transfer to 8K */
		io32_rmw_usb(ZM_SOC_USB_MODE_CTRL_OFFSET, 0x20, 0x30);

		/* enable upstream DMA mode */
		io32_set_usb(ZM_SOC_USB_MODE_CTRL_OFFSET, BIT1);

		/* set stream mode timeout critirea */
		iowrite32_usb(ZM_SOC_USB_TIME_CTRL_OFFSET, 0xa0);
#if defined(PROJECT_K2)
		/*0x10004020 is vaild in k2 but could be invaild in other chip*/
		if ((ioread32(0x10004020) & 0x2000) != 0) {
			/* disable stream mode for AR9270 */
			iowrite32_usb(ZM_SOC_USB_MAX_AGGREGATE_OFFSET, 0);
		} else {
			/* enable stream mode for AR9271 */
			iowrite32_usb(ZM_SOC_USB_MAX_AGGREGATE_OFFSET, 9);
		}
#else
		iowrite32_usb(ZM_SOC_USB_MAX_AGGREGATE_OFFSET, 9);
#endif
#endif
	}
#if defined(PROJECT_MAGPIE) && !defined(ROM_VER_1_1)
	else if (hostif == HIF_PCI )
		hif_pci_patch_install(&_indir_tbl.hif);
#endif
	A_PRINTF("USB mode: 0x%x\r\n", ioread32_usb(0x100));

	// patch the clock function
	if(1) {
		_indir_tbl.cmnos.clock._clock_init = cmnos_clock_init_patch;
		_indir_tbl.cmnos.clock._refclk_speed_get = cmnos_refclk_speed_get_patch;
		_indir_tbl.cmnos.clock._delay_us = cmnos_delay_us_patch;
		_indir_tbl.cmnos.clock._clock_tick = cmnos_tick_patch;
		_indir_tbl.cmnos.clock._milliseconds = cmnos_milliseconds_patch;

		//default clock, setup initial variable, SYSTEM_FREQ=40
		A_CLOCK_INIT(SYSTEM_FREQ);
	}

	Magpie_init();

#if MAGPIE_ENABLE_WLAN == 1
	io32_clr(MAGPIE_REG_RST_RESET_ADDR, BIT10 | BIT8 | BIT7 | BIT6);
#if defined(PROJECT_MAGPIE)
	io32_set(MAGPIE_REG_AHB_ARB_ADDR, BIT1);
#endif

	wlan_pci_module_init();
	wlan_pci_probe();
#endif


	A_PRINTF("Tgt running\n\r");

#if defined(PROJECT_MAGPIE)
	if(1) {
		A_PRINTF("======= Apply MISC Assert patch\n\r");
		_assfail_ori =  _indir_tbl.cmnos.misc._assfail;
		_indir_tbl.cmnos.misc._assfail = exception_reset;
	}

	change_magpie_clk();
#endif

#if defined(PROJECT_K2)
	printk("K2 chip ready\n");
#elif defined(PROJECT_MAGPIE)
	printk("Magpie chip ready\n");
#else
	printk("??? chip ready\n");
#endif

	wlan_task(); //never return
}
