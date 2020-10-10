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

#define measure_time 0
#define measure_time_pll 10000000

extern Action eUsbCxFinishAction;
extern CommandType eUsbCxCommand;
extern BOOLEAN UsbChirpFinish;
extern USB_FIFO_CONFIG usbFifoConf;
extern uint16_t *pu8DescriptorEX;
extern uint16_t u16TxRxCounter;

void zfTurnOffPower_patch(void);

static void _fw_reset_dma_fifo();
static void _fw_restore_dma_fifo();
static void _fw_power_on();
static void _fw_power_off();

BOOLEAN bEepromExist = TRUE;
BOOLEAN bJumptoFlash = FALSE;

void _fw_usb_suspend_reboot()
{
	/* reset usb/wlan dma */
	_fw_reset_dma_fifo();

	/* restore gpio setting and usb/wlan dma state */
	_fw_restore_dma_fifo();

	/* set clock to bypass mode - 40Mhz from XTAL */
	iowrite32(MAGPIE_REG_CPU_PLL_BYPASS_ADDR, BIT0 | BIT4);

	A_DELAY_USECS(100); /* wait for stable */

	iowrite32(MAGPIE_REG_CPU_PLL_ADDR, BIT16);

	A_DELAY_USECS(100); /* wait for stable */
	A_UART_HWINIT((40*1000*1000), 19200);

	A_CLOCK_INIT(40);

	if (!bEepromExist) { /* jump to flash boot (eeprom data in flash) */
		bJumptoFlash = TRUE;
		A_PRINTF("Jump to Flash BOOT\n");
		app_start();
	} else {
		A_PRINTF("receive the suspend command...\n");
		/* reboot..... */
		A_USB_JUMP_BOOT();
	}

}

#define PCI_RC_RESET_BIT                            BIT6
#define PCI_RC_PHY_RESET_BIT                        BIT7
#define PCI_RC_PLL_RESET_BIT                        BIT8
#define PCI_RC_PHY_SHIFT_RESET_BIT                  BIT10

/*
 * -- urn_off_merlin --
 * . values suggested from Lalit
 *
 */
static void turn_off_merlin()
{
	volatile uint32_t default_data[9];
	uint32_t i=0;

	if(1)
	{
		A_PRINTF("turn_off_merlin_ep_start ......\n");
		A_DELAY_USECS(measure_time);
		default_data[0] = 0x9248fd00;
		default_data[1] = 0x24924924;
		default_data[2] = 0xa8000019;
		default_data[3] = 0x17160820;
		default_data[4] = 0x25980560;
		default_data[5] = 0xc1c00000;
		default_data[6] = 0x1aaabe40;
		default_data[7] = 0xbe105554;
		default_data[8] = 0x00043007;
        
		for(i=0; i<9; i++)
		{
			A_DELAY_USECS(10);
        
			iowrite32(0x10ff4040, default_data[i]);
		}
		A_DELAY_USECS(10);
		iowrite32(0x10ff4044, BIT0);
		A_PRINTF("turn_off_merlin_ep_end ......\n");
	}
}

/*
 * -- turn_off_phy --
 *
 * . write shift register to both pcie ep and rc
 * . 
 */

static void turn_off_phy()
{

	volatile uint32_t default_data[9];
	uint32_t i=0;

	default_data[0] = 0x9248fd00;
	default_data[1] = 0x24924924;
	default_data[2] = 0xa8000019;
	default_data[3] = 0x17160820;
	default_data[4] = 0x25980560;
	default_data[5] = 0xc1c00000;
	default_data[6] = 0x1aaabe40;
	default_data[7] = 0xbe105554;
	default_data[8] = 0x00043007;

	for(i=0; i<9; i++)
	{
		// check for the done bit to be set 

		while (1)
		{
			if (ioread32(0x40028) & BIT31)
				break;
		}
        
		A_DELAY_USECS(1);
    
		iowrite32(0x40024, default_data[i]);
	}
	iowrite32(0x40028, BIT0);
}

static void turn_off_phy_rc()
{
    
	volatile uint32_t default_data[9];
	uint32_t i=0;
    
	A_PRINTF("turn_off_phy_rc\n");
    
	default_data[0] = 0x9248fd00;
	default_data[1] = 0x24924924;
	default_data[2] = 0xa8000019;
	default_data[3] = 0x13160820;//PwdClk1MHz=0
	default_data[4] = 0x25980560;
	default_data[5] = 0xc1c00000;
	default_data[6] = 0x1aaabe40;
	default_data[7] = 0xbe105554;
	default_data[8] = 0x00043007;
        
	for(i=0; i<9; i++)
	{
		// check for the done bit to be set 
     
		while (1)
		{
			if (ioread32(0x40028) & BIT31)
				break;
		}

		A_DELAY_USECS(1);

		iowrite32(0x40024, default_data[i]);
	}
	iowrite32(0x40028, BIT0);
}

volatile uint32_t gpio_func = 0x0;
volatile uint32_t gpio = 0x0;

/*
 * -- patch zfTurnOffPower --
 *
 * . set suspend counter to non-zero value
 * . 
 */
void zfTurnOffPower_patch(void)
{
	A_PRINTF("+++ goto suspend ......\n");

	/* setting the go suspend here, power down right away */
	io32_set(0x10000, BIT3);

	A_DELAY_USECS(100);

	// TURN OFF ETH PLL
	_fw_power_off();

	//32clk wait for External ETH PLL stable
	A_DELAY_USECS(100);
    
	iowrite32(0x52000, 0x70303); /* read back 0x703f7 */
	iowrite32(0x52008, 0x0e91c); /* read back 0x1e948 */
    
	io32_set(MAGPIE_REG_SUSPEND_ENABLE_ADDR, BIT0);

	// wake up, and turn on cpu, eth, pcie and usb pll 
	_fw_power_on();
	// restore gpio and other settings
	_fw_restore_dma_fifo();

	/* clear suspend */
	io32_clr(MAGPIE_REG_SUSPEND_ENABLE_ADDR, BIT0);
	io32_clr(0x52028, BIT8 | BIT12 | BIT16);
}

/*
 * -- patch zfResetUSBFIFO_patch --
 *
 * . clear ep3/ep4 fifo
 * . set suspend magic pattern
 * . reset pcie ep phy
 * . reset pcie rc phy
 * . turn off pcie pll
 * . reset all pcie/gmac related registers
 * . reset usb dma
 */
void zfResetUSBFIFO_patch(void)
{
	A_PRINTF("0x9808  0x%x ......\n", ioread32(0x10ff9808));
	A_PRINTF("0x7890  0x%x ......\n", ioread32(0x10ff7890));
	A_PRINTF("0x7890  0x%x ......\n", ioread32(0x10ff7890));
	A_PRINTF("0x4088  0x%x ......\n", ioread32(0x10ff4088));
	_fw_reset_dma_fifo();
}

static void _fw_reset_dma_fifo()
{
	io8_set(0x100ae, 0x10);
	io8_set(0x100af, 0x10);
	A_PRINTF("_fw_reset_dma_fifo\n");

	// disable ep3 int enable, so that resume back won't send wdt magic pattern out!!!
	mUSB_STATUS_IN_INT_DISABLE();

	/* update magic pattern to indicate this is a suspend */
	iowrite32(WATCH_DOG_MAGIC_PATTERN_ADDR, SUS_MAGIC_PATTERN);

	A_PRINTF("org 0x4048  0x%x ......\n", ioread32(0x10ff4048));
	A_PRINTF("org 0x404C  0x%x ......\n", ioread32(0x10ff404C));
	A_PRINTF("org 0x4088  0x%x ......\n", ioread32(0x10ff4088));

	/* 1010.1010.1010.0110.1010 for UB94 */
	iowrite32(0x10ff4088, 0xaaa6a);
	iowrite32(0x10ff404C, 0x0);

	A_DELAY_USECS(1000);
	A_PRINTF("0x4048  0x%x ......\n", ioread32(0x10ff4048));
	A_PRINTF("0x404C  0x%x ......\n", ioread32(0x10ff404C));
	A_PRINTF("0x4088  0x%x ......\n", ioread32(0x10ff4088));
         
	// turn off merlin
	turn_off_merlin();
	// pcie ep
	A_PRINTF("turn_off_magpie_ep_start ......\n");
	A_DELAY_USECS(measure_time);
	io32_set(0x40040, BIT0 | BIT1);
	turn_off_phy();
	io32_clr(0x40040, BIT0 | BIT1);
	A_PRINTF("turn_off_magpie_ep_end ......\n");

	// pcie rc 
	A_PRINTF("turn_off_magpie_rc_start ......\n");
	A_DELAY_USECS(measure_time);
	io32_clr(0x40040, BIT0);
	turn_off_phy_rc();
	A_PRINTF("turn_off_magpie_rc_end ......down\n");
	A_DELAY_USECS(measure_time);

	A_PRINTF("0x4001C  %p ......\n", ioread32(0x4001c));
	A_PRINTF("0x40040  %p ......\n", ioread32(0x40040));
    
	/* turn off pcie_pll - power down (bit16) */
	A_PRINTF(" before pwd PCIE PLL CFG:0x5601C: 0x%08x\n",
		 ioread32(0x5601C));
	io32_set(0x5601C, BIT18);
	A_PRINTF(" after pwd PCIE PLL CFG:0x5601C:  0x%08x\n",
		 ioread32(0x5601C));

	/* set everything to reset state?, requested by Oligo */
	io32_set(0x50010, BIT13 | BIT12
		 | BIT11 | BIT9 | BIT7 | BIT6);

	iowrite32(0x5C000, 0);

	A_DELAY_USECS(10);

	/* reset usb DMA controller */
	iowrite32_usb(ZM_SOC_USB_DMA_RESET_OFFSET, 0x0);

	io32_set(0x50010, BIT4);
	A_DELAY_USECS(5);
	io32_clr(0x50010, BIT4);

	iowrite32_usb(ZM_SOC_USB_DMA_RESET_OFFSET, BIT0);
}

static void _fw_power_off()
{
	/*
	 *  1. set CPU bypass
	 *  2. turn off CPU PLL
	 *  3. turn off ETH PLL
	 *  4. disable ETH PLL bypass and update
	 *  4.1 set suspend timeout 
	 *  5. set SUSPEND_ENABLE
	 */

	iowrite32(MAGPIE_REG_CPU_PLL_BYPASS_ADDR, BIT0 | BIT4);

	A_DELAY_USECS(100); // wait for stable

	iowrite32(MAGPIE_REG_CPU_PLL_ADDR, BIT16);

	A_DELAY_USECS(100); // wait for stable

	A_UART_HWINIT((40*1000*1000), 19200);
	A_CLOCK_INIT(40);

	io32_set(MAGPIE_REG_ETH_PLL_ADDR, BIT16);

	io32_set(MAGPIE_REG_ETH_PLL_BYPASS_ADDR, BIT4 | BIT0);

	io32_set(MAGPIE_REG_SUSPEND_ENABLE_ADDR, 0x10 << 8);
}

static void _fw_power_on()
{ 
    /*
     *  1. turn on CPU PLL
     *  2. disable CPU bypass
     *  3. turn on ETH PLL
     *  4. disable ETH PLL bypass and update
     *  5. turn on pcie pll
     */    

	io32_clr(MAGPIE_REG_ETH_PLL_ADDR, BIT16);

	/* deassert eth_pll bypass mode and trigger update bit */
	io32_clr(MAGPIE_REG_ETH_PLL_BYPASS_ADDR, BIT4 | BIT0);
}

static void _fw_restore_dma_fifo(void)
{
	io32_clr(0x5601C, BIT18);
    
	/* reset pcie_rc shift */
	io32_clr(0x50010, BIT10 | BIT8 | BIT7);
	A_DELAY_USECS(1);
	io32_set(0x50010, BIT10 | BIT8 | BIT7);

	/* reset pci_rc phy */
	io32_set(MAGPIE_REG_RST_RESET_ADDR,
		 PCI_RC_PHY_SHIFT_RESET_BIT
		 | PCI_RC_PLL_RESET_BIT | PCI_RC_PHY_RESET_BIT
		 | PCI_RC_RESET_BIT);
	A_DELAY_USECS(20);

	// enable dma swap function
	MAGPIE_REG_USB_RX0_SWAP_DATA = 0x1;
	MAGPIE_REG_USB_TX0_SWAP_DATA = 0x1;
	MAGPIE_REG_USB_RX1_SWAP_DATA = 0x1;
	MAGPIE_REG_USB_RX2_SWAP_DATA = 0x1;
}
