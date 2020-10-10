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
#include "usb_defs.h"
#include "usb_type.h"
#include "usb_pre.h"
#include "usb_extr.h"
#include "usb_std.h"
#include "reg_defs.h"
#include "athos_api.h"
#include "usbfifo_api.h"

#include "adf_os_io.h"

#include "sys_cfg.h"

void _fw_usb_suspend_reboot();

extern Action      eUsbCxFinishAction;
extern CommandType eUsbCxCommand;
extern BOOLEAN     UsbChirpFinish;
extern USB_FIFO_CONFIG usbFifoConf;

#if SYSTEM_MODULE_USB

#define CHECK_SOF_LOOP_CNT    50

void _fw_usb_suspend_reboot()
{
	volatile uint32_t gpio_in = 0;
	volatile uint32_t pupd = 0;
	volatile uint32_t t = 0;
	volatile uint32_t sof_no=0,sof_no_new=0;
	/* Set GO_TO_SUSPEND bit to USB main control register */
	io8_clr_usb(ZM_INTR_SOURCE_7_OFFSET, BIT2);
	A_PRINTF("!USB suspend\n\r");

	/* keep the record of suspend */
#if defined(PROJECT_MAGPIE)
	iowrite32(WATCH_DOG_MAGIC_PATTERN_ADDR, SUS_MAGIC_PATTERN);
#elif defined(PROJECT_K2)
	iowrite32(MAGPIE_REG_RST_STATUS_ADDR, SUS_MAGIC_PATTERN);
#endif /* #if defined(PROJECT_MAGPIE) */

	/* Reset USB FIFO */
	A_USB_RESET_FIFO();

	/* Turn off power */
	A_USB_POWER_OFF();

	DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xffff)) | 0x1000;

#if 0
	/* reset ep3/ep4 fifo in case there
	 * is data which might affect resuming */
	iowrite8(0x100ae, ioread8(0x100ae) | 0x10);
	iowrite8(0x100ae, ioread8(0x100af) | 0x10);

	/* config gpio to input before goto suspend */

	/* disable JTAG/ICE */
	jtag = ioread32(0x10004054);
	iowrite32(0x10004054, jtag | BIT17);

	/* disable SPI */
	spi = ioread32(0x50040);
	iowrite32(0x50040, spi & ~BIT8);
#endif
	/* set all GPIO to input */
	gpio_in = ioread32(0x1000404c);
	iowrite32(0x1000404c, 0x0);

	/* set PU/PD for all GPIO except two UART pins */
	pupd = ioread32(0x10004088);
	iowrite32(0x10004088, 0xA982AA6A);

	sof_no = ioread32(0x10004);
	for (t = 0; t < CHECK_SOF_LOOP_CNT; t++)
	{
		A_DELAY_USECS(1000);    /* delay 1ms */
		sof_no_new = ioread32(0x10004);

		if(sof_no_new == sof_no)
			break;
		sof_no = sof_no_new;
	}

	/*
	 * Reset "printf" module patch point(RAM to ROM)
	 * when K2 warm start or suspend,
	 * which fixed the error issue cause by redownload
	 * another different firmware.
	 */
	_indir_tbl.cmnos.printf._printf = save_cmnos_printf;

	/* !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
	 * setting the go suspend here, power down right away!!!
	 */
	if (t != CHECK_SOF_LOOP_CNT)   /* not time out */
		io32_set(0x10000, BIT3);

	DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xffff)) | 0x1100;

#if 0 /* pll unstable, h/w bug? */
	iowrite32(0x50040, 0x300 | 6 | (1>>1) << 12);
	A_UART_HWINIT((40*1000*1000)/1, 19200);

	/* restore gpio setting */
	iowrite32(0x10004054, jtag);
	iowrite32(0x50040, spi);
#endif
	iowrite32(0x1000404c, gpio_in);
	iowrite32(0x10004088, pupd);

	DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xffff)) | 0x1200;

	/* since we still need to touch mac_base address after resuming back,
	 * so that reset mac can't be done in ResetFifo function,
	 * move to here... whole mac control reset.... (bit1)
	 */
	iowrite32(MAGPIE_REG_RST_PWDN_CTRL_ADDR, BIT1);
	io32_set(MAGPIE_REG_RST_PWDN_CTRL_ADDR, BIT0);
	iowrite32(MAGPIE_REG_RST_PWDN_CTRL_ADDR, 0);
	A_DELAY_USECS(1000);

	/* disable ep3 int enable, so that resume back won't
	 * send wdt magic pattern out!!! */
	mUSB_STATUS_IN_INT_DISABLE();

	MAGPIE_REG_USB_RX0_SWAP_DATA = 0x1;
	MAGPIE_REG_USB_TX0_SWAP_DATA = 0x1;
	MAGPIE_REG_USB_RX1_SWAP_DATA = 0x1;
	MAGPIE_REG_USB_RX2_SWAP_DATA = 0x1;

	if (((DEBUG_SYSTEM_STATE&~(0x0000ffff))>>16 == 0x5342)) {
		/* UART_SEL and SPI_SEL */
		iowrite32(0x50040, 0x300 | 0 | (1 >> 1) << 12);
	}

	/* Jump to boot code */
	A_USB_JUMP_BOOT();
}

/*
 * patch usb_fw_task
 * usb zero length interrupt should not clear by s/w, h/w will handle that
 * complete suspend handle, configure gpio, turn off related function,
 * slow down the pll for stable issue
 */
void _fw_usb_fw_task(void)
{
	register uint8_t usb_interrupt_level1;
	register uint8_t usb_interrupt_level2;

	usb_interrupt_level1 = ioread8_usb(ZM_INTR_GROUP_OFFSET);
#if 0 /* these endpoints are handled by DMA */
	if (usb_interrupt_level1 & BIT5)
	{
		vUsb_Data_In();
	}
#endif
	if (usb_interrupt_level1 & BIT4) {
		usb_interrupt_level2 =
			ioread8_usb(ZM_INTR_SOURCE_4_OFFSET);

		if(usb_interrupt_level2 & BIT6)
			A_USB_REG_OUT(); /* vUsb_Reg_Out() */
	}

	if (usb_interrupt_level1 & BIT6) {
		/* zfGenWatchDogEvent(); ?? */
		usb_interrupt_level2 =
			ioread8_usb(ZM_INTR_SOURCE_6_OFFSET);
		if(usb_interrupt_level2 & BIT6)
			A_USB_STATUS_IN(); /* vUsb_Status_In() */
	}

	if (usb_interrupt_level1 & BIT0) {
		usb_interrupt_level2 =
			ioread8_usb(ZM_INTR_SOURCE_0_OFFSET);

		/* refer to FUSB200, p 48, offset:21H, bit7 description,
		 * should clear the command abort interrupt first!?
		 */
		if (usb_interrupt_level2 & BIT7) {
			/* Handle command abort */
			io8_clr_usb(ZM_INTR_SOURCE_0_OFFSET, BIT7);
			A_PRINTF("![SOURCE_0] bit7 on\n\r");
		}

		if (usb_interrupt_level2 & BIT1)
			A_USB_EP0_TX(); /* USB EP0 tx interrupt */

		if (usb_interrupt_level2 & BIT2)
			A_USB_EP0_RX(); /* USB EP0 rx interrupt */

		if (usb_interrupt_level2 & BIT0) {
			A_USB_EP0_SETUP();
			/* vWriteUSBFakeData() */
		}

		if (usb_interrupt_level2 & BIT3) {
			/* vUsb_ep0end */
			eUsbCxCommand = CMD_VOID;
			iowrite8_usb(ZM_CX_CONFIG_STATUS_OFFSET, 0x01);
		}

		/* EP0 fail */
	        if (usb_interrupt_level2 & BIT4)
			iowrite8_usb(ZM_CX_CONFIG_STATUS_OFFSET, 0x04);

		if (eUsbCxFinishAction == ACT_STALL) {
			/* set CX_STL to stall Endpoint0 &
			 * will also clear FIFO0 */
			iowrite8_usb(ZM_CX_CONFIG_STATUS_OFFSET, 0x04);
		} else if (eUsbCxFinishAction == ACT_DONE) {
			/* set CX_DONE to indicate the transmistion
			 * of control frame */
			iowrite8_usb(ZM_CX_CONFIG_STATUS_OFFSET, 0x01);
		}
		eUsbCxFinishAction = ACT_IDLE;
	}

	if (usb_interrupt_level1 & BIT7) {
		usb_interrupt_level2 =
			ioread8_usb(ZM_INTR_SOURCE_7_OFFSET);

#if 0
	if (usb_interrupt_level2 & BIT7)
		vUsb_Data_Out0Byte();

	if (usb_interrupt_level2 & BIT6)
		vUsb_Data_In0Byte();
#endif

		if (usb_interrupt_level2 & BIT1) {
			io8_clr_usb(ZM_INTR_SOURCE_7_OFFSET, BIT1);
			UsbChirpFinish = FALSE;
			A_PRINTF("!USB reset\n\r");
		}
		if (usb_interrupt_level2 & BIT2) {
			/* TBD: the suspend resume code should put here,
			 * Ryan, 07/18
			 * issue, jump back to rom code and what peripherals
			 * should we reset here? */
			_fw_usb_suspend_reboot();
		}
		if (usb_interrupt_level2 & BIT3) {
			io8_clr_usb(ZM_INTR_SOURCE_7_OFFSET, BIT3);
			A_PRINTF("!USB resume\n\r");
		}
	}
}


void _fw_usb_reset_fifo(void)
{
	io8_set(0x100ae, 0x10);
	io8_set(0x100af, 0x10);

	/* disable ep3 int enable, so that resume back won't
	 * send wdt magic pattern out!!!
	 */
	mUSB_STATUS_IN_INT_DISABLE();

	/* update magic pattern to indicate this is a suspend
	 * k2: MAGPIE_REG_RST_WDT_TIMER_CTRL_ADDR
	 * magpie: MAGPIE_REG_RST_STATUS_ADDR
	 */
	iowrite32(MAGPIE_REG_RST_STATUS_ADDR, SUS_MAGIC_PATTERN);

	/*
	 * Before USB suspend, USB DMA must be reset(refer to Otus)
	 * Otus runs the following statements only
	 * iowrite32( MAGPIE_REG_RST_PWDN_CTRL_ADDR, BIT0|BIT2 );
	 * iowrite32( MAGPIE_REG_RST_PWDN_CTRL_ADDR, 0x0 );
	 * K2 must run the following statements additionally
	 * reg_data = (A_UINT32 *)(USB_CTRL_BASE_ADDRESS + 0x118);
	 * *reg_data = 0x00000000;
	 * *reg_data = 0x00000001;
	 * because of Hardware bug in K2
	 */
	iowrite32_usb(ZM_SOC_USB_DMA_RESET_OFFSET, 0x0);

	/* reset both usb(bit2)/wlan(bit1) dma */
	iowrite32(MAGPIE_REG_RST_PWDN_CTRL_ADDR, BIT2);
	io32_set(MAGPIE_REG_RST_PWDN_CTRL_ADDR, BIT0);
	iowrite32(MAGPIE_REG_RST_PWDN_CTRL_ADDR, 0x0);

	iowrite32_usb(ZM_SOC_USB_DMA_RESET_OFFSET, BIT0);

	/* MAC warem reset */
	//reg_data = (uint32_t *)(K2_REG_MAC_BASE_ADDR + 0x7000);
	//*reg_data = 0x00000001;

	//A_DELAY_USECS(1);

	//*reg_data = 0x00000000;

	//while (*reg_data)   ;

	A_PRINTF("\n change clock to 22 and go to suspend now!");

	/* UART_SEL */
	iowrite32(0x50040, 0x200 | 0 | (1 >> 1) << 12);
	A_UART_HWINIT((22*1000*1000), 19200);
}
#endif
