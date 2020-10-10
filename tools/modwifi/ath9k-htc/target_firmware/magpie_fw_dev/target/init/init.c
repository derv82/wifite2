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
#if defined(_RAM_)

#include "athos_api.h"
#include "usb_defs.h"

#include "adf_os_io.h"

#if defined(PROJECT_MAGPIE)
#include "regdump.h"
extern  uint32_t *init_htc_handle;
uint8_t htc_complete_setup = 0;
void reset_EP4_FIFO(void);
#endif
#include "init.h"

void Magpie_init(void);


#if defined(PROJECT_MAGPIE)
extern BOOLEAN bEepromExist;
extern BOOLEAN bJumptoFlash;
#endif

static uint32_t loop_low, loop_high;

// reference idle count at the beginning
uint32_t idle_cnt = 0;

#if defined(PROJECT_K2)
// save the ROM printf function point
int (* save_cmnos_printf)(const char * fmt, ...);
#endif

#define ATH_DATE_STRING     __DATE__" "__TIME__

static void idle_task();

#if defined(PROJECT_MAGPIE)
void fatal_exception_func()
{
	// patch for execption
	(void)_xtos_set_exception_handler(EXCCAUSE_UNALIGNED, AR6002_fatal_exception_handler_patch);
	(void)_xtos_set_exception_handler(EXCCAUSE_LOAD_STORE_ERROR, AR6002_fatal_exception_handler_patch);
	(void)_xtos_set_exception_handler(EXCCAUSE_ILLEGAL, AR6002_fatal_exception_handler_patch);
	(void)_xtos_set_exception_handler(EXCCAUSE_INSTR_ERROR, AR6002_fatal_exception_handler_patch);
	(void)_xtos_set_exception_handler(EXCCAUSE_PRIVILEGED, AR6002_fatal_exception_handler_patch);
	(void)_xtos_set_exception_handler(EXCCAUSE_INSTR_DATA_ERROR, AR6002_fatal_exception_handler_patch);
	(void)_xtos_set_exception_handler(EXCCAUSE_LOAD_STORE_DATA_ERROR, AR6002_fatal_exception_handler_patch);
	(void)_xtos_set_exception_handler(EXCCAUSE_DIVIDE_BY_ZERO, AR6002_fatal_exception_handler_patch);
}
#endif

#if defined(PROJECT_MAGPIE)
void
change_magpie_clk(void)
{
	iowrite32(0x00056004, BIT4 | BIT0);

	/* Wait for the update bit (BIT0) to get cleared */
	while (ioread32(0x00056004) & BIT0)
		;

	/* Put the PLL into reset */
	io32_set(0x00050010, BIT1);

	/*
	 * XXX: statically set the CPU clock to 200Mhz
	 */
	/* Setting PLL to 400MHz */
	iowrite32(0x00056000, 0x325);

	/* Pull CPU PLL out of Reset */
	io32_clr(0x00050010, BIT1);

	A_DELAY_USECS(60); // wait for stable

	/* CPU & AHB settings */  
	/*
	 * AHB clk = ( CPU clk / 2 )
	 */
	iowrite32(0x00056004, 0x00001 | BIT16 | BIT8); /* set plldiv to 2 */

	while (ioread32(0x00056004) & BIT0)
		;

	/* UART Setting */
	A_UART_HWINIT((100*1000*1000), 115200);

}

void exception_reset(struct register_dump_s *dump)
{
	A_PRINTF("exception_reset \n");

	/* phase I dump info */
	A_PRINTF("exception reset-phase 1\n");
	if(_assfail_ori)
		_assfail_ori(dump);

	/* phase II reset */
	A_PRINTF("exception reset-phase 2\n");
	iowrite32(WATCH_DOG_MAGIC_PATTERN_ADDR, WDT_MAGIC_PATTERN);

	io32_set(MAGPIE_REG_RST_RESET_ADDR, BIT10 | BIT8 | BIT7 | BIT6);

	io32_set(MAGPIE_REG_AHB_ARB_ADDR, BIT1);

	iowrite32_usb(ZM_SOC_USB_DMA_RESET_OFFSET, 0x0);
	io32_set(0x50010, BIT4);
	A_DELAY_USECS(5);
	io32_clr(0x50010, BIT4);
	A_DELAY_USECS(5);
	iowrite32_usb(ZM_SOC_USB_DMA_RESET_OFFSET, BIT0);

	// set clock to bypass mode - 40Mhz from XTAL
	iowrite32(MAGPIE_REG_CPU_PLL_BYPASS_ADDR, BIT0 | BIT4);
	A_DELAY_USECS(100); // wait for stable
	iowrite32(MAGPIE_REG_CPU_PLL_ADDR, BIT16);

	A_UART_HWINIT((40*1000*1000), 115200);

	A_PRINTF("do TX/RX swap\n");

	MAGPIE_REG_USB_RX0_SWAP_DATA = 0x1;
	MAGPIE_REG_USB_TX0_SWAP_DATA = 0x1;
	MAGPIE_REG_USB_RX1_SWAP_DATA = 0x1;
	MAGPIE_REG_USB_RX2_SWAP_DATA = 0x1;

        A_PRINTF("Cold reboot initiated.");
#if defined(PROJECT_MAGPIE)
	iowrite32(WATCH_DOG_MAGIC_PATTERN_ADDR, 0);
#elif defined(PROJECT_K2)
	iowrite32(MAGPIE_REG_RST_STATUS_ADDR, 0);
#endif /* #if defined(PROJECT_MAGPIE) */
	A_USB_JUMP_BOOT();
}

void reset_EP4_FIFO(void)
{
	int i;

	/* reset EP4 FIFO */
	io8_set_usb(ZM_EP4_BYTE_COUNT_HIGH_OFFSET, BIT4);
	for(i = 0; i < 100; i++) {}
	io8_clr_usb(ZM_EP4_BYTE_COUNT_HIGH_OFFSET, BIT4);
}

LOCAL void zfGenExceptionEvent(uint32_t exccause, uint32_t pc, uint32_t badvaddr)
{
	uint32_t pattern = 0x33221199;

	A_PRINTF("<Exception>Tgt Drv send an event 44332211 to Host Drv\n");
	mUSB_STATUS_IN_INT_DISABLE();

	iowrite32_usb(ZM_CBUS_FIFO_SIZE_OFFSET, 0x0f);

	iowrite32_usb(ZM_EP3_DATA_OFFSET, pattern);
	iowrite32_usb(ZM_EP3_DATA_OFFSET, exccause);
	iowrite32_usb(ZM_EP3_DATA_OFFSET, pc);
	iowrite32_usb(ZM_EP3_DATA_OFFSET, badvaddr);
    
	mUSB_EP3_XFER_DONE();
}

LOCAL void zfGenWrongEpidEvent(uint32_t epid)
{
	uint32_t pattern   = 0x33221299;

	A_PRINTF("<WrongEPID>Tgt Drv send an event 44332212 to Host Drv\n");
	mUSB_STATUS_IN_INT_DISABLE();

	iowrite32_usb(ZM_CBUS_FIFO_SIZE_OFFSET, 0x0f);

	iowrite32_usb(ZM_EP3_DATA_OFFSET, pattern);
	iowrite32_usb(ZM_EP3_DATA_OFFSET, epid);

	mUSB_EP3_XFER_DONE();
}

void
AR6002_fatal_exception_handler_patch(CPU_exception_frame_t *exc_frame)
{
	struct register_dump_s dump;
	uint32_t  exc_cause, exc_vaddr;
	asm volatile("rsr %0,%1" : "=r" (exc_cause) : "n" (EXCCAUSE));
	asm volatile("rsr %0,%1" : "=r" (exc_vaddr) : "n" (EXCVADDR));

	dump.exc_frame              = *exc_frame; /* structure copy */
	dump.badvaddr               = exc_vaddr;
	dump.exc_frame.xt_exccause  = exc_cause;
	dump.pc                     = exc_frame->xt_pc;
	dump.assline                = 0;

	zfGenExceptionEvent(dump.exc_frame.xt_exccause, dump.pc, dump.badvaddr);

#if SYSTEM_MODULE_PRINT
	A_PRINTF("\nFatal exception (%d): \tpc=0x%x \n\r\tbadvaddr=0x%x \n\r\tdump area=0x%x\n",
		 dump.exc_frame.xt_exccause, dump.pc, dump.badvaddr, &dump);
	PRINT_FAILURE_STATE();
#else
	A_PUTS("Fatal exception\n\r");
#endif
	A_ASSFAIL(&dump);

#if defined(_ROM_)     
	A_WDT_ENABLE();
#endif

	while(1) ;
}

void 
HTCControlSvcProcessMsg_patch(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t hdr_buf,
			      adf_nbuf_t pBuffers, void *arg)
{
	a_uint8_t *anbdata;
	a_uint32_t anblen;
	HTC_UNKNOWN_MSG *pMsg;

	/* we assume buffers are aligned such that we can access the message
	 * parameters directly*/
	adf_nbuf_peek_header(pBuffers, &anbdata, &anblen);
	pMsg = (HTC_UNKNOWN_MSG *)anbdata;

	if (pMsg->MessageID == HTC_MSG_SETUP_COMPLETE_ID) {
		htc_complete_setup = 1;
	}

	HTCControlSvcProcessMsg(EndpointID, hdr_buf, pBuffers, arg);
}

/* Patch callback for check the endpoint ID is correct or not */
void 
HTCMsgRecvHandler_patch(adf_nbuf_t hdr_buf, adf_nbuf_t buffer, void *context)
{
	int eid;
	a_uint8_t *anbdata;
	a_uint32_t anblen;
	adf_nbuf_t tmp_nbuf;
	HTC_FRAME_HDR *pHTCHdr;
                
	if (hdr_buf == ADF_NBUF_NULL) {
		/* HTC hdr is not in the hdr_buf */
		tmp_nbuf = buffer;
	} else {
		tmp_nbuf = hdr_buf;
	}
                
	adf_nbuf_peek_header(tmp_nbuf, &anbdata, &anblen);        
	pHTCHdr = (HTC_FRAME_HDR *)anbdata; 
  
	eid = pHTCHdr->EndpointID;
    
	if ((eid != 0) && (htc_complete_setup == 0)) {
		A_PRINTF("\nHTC Hdr EndpointID = %d, anblen = %d\n", pHTCHdr->EndpointID, anblen);
		A_PRINTF("HTC Hder : %2x-%2x-%2x-%2x-%2x-%2x-%2x-%2x-%2x-%2x-%2x-%2x\n",
                         *anbdata, *(anbdata+1), *(anbdata+2), *(anbdata+3), 
                         *(anbdata+4), *(anbdata+5), *(anbdata+6), *(anbdata+7),
                         *(anbdata+8), *(anbdata+9), *(anbdata+10), *(anbdata+11)); 
		A_PRINTF("init_htc_handle = 0x%8x\n", init_htc_handle);
            
		if (pHTCHdr->EndpointID == 1) {
			A_PRINTF("Return WMI Command buffer\n");
			HTC_ReturnBuffers(init_htc_handle, 1, tmp_nbuf);
		} else if ((pHTCHdr->EndpointID == 5) || (pHTCHdr->EndpointID == 6)) {
			A_PRINTF("Return Data buffer\n");
			HTC_ReturnBuffers(init_htc_handle, 6, tmp_nbuf);
		} else {
		}
	} else {
		if ((pHTCHdr->EndpointID < 0) || (pHTCHdr->EndpointID >= ENDPOINT_MAX)) {
			A_PRINTF("HTC Hdr EndpointID = %d, anblen = %d\n", pHTCHdr->EndpointID, anblen);
			A_PRINTF("HTC Hder : %2x-%2x-%2x-%2x-%2x-%2x-%2x-%2x\n", 
                                 *anbdata, *(anbdata+1), *(anbdata+2), *(anbdata+3), 
                                 *(anbdata+4), *(anbdata+5), *(anbdata+6), *(anbdata+7));

			if (anblen > 64) {
				A_PRINTF("EP1-Tx-Data with Wrong Htc Header Endpoint ID, WAR free this buffer\n");
				HTC_ReturnBuffers(init_htc_handle, 6, tmp_nbuf);
				A_PRINTF("EP1-Tx-Data > Free this buffer successfully\n");
			} else {
				A_PRINTF("EP4-WMI-Cmd with Wrong Htc Header Endpoint ID, WAR free this buffer\n");
				zfGenWrongEpidEvent((a_uint32_t)pHTCHdr->EndpointID);
				HTC_ReturnBuffers(init_htc_handle, 1, tmp_nbuf);
				A_PRINTF("EP4-WMI-Cmd > Free this buffer successfully\n");
			}
		} else
			HTCMsgRecvHandler( hdr_buf, buffer, context);
	}
}
#endif

void init_mem()
{
	int i = 0;
	uint32_t *temp = (uint32_t *)ALLOCRAM_START;

	/* clear bss segment */
	for(temp = (uint32_t *)&START_BSS; temp < (uint32_t *)&END_BSS; temp++)
		*temp = 0;

	/* clear heap segment */
	for(i = 0; i < ((ALLOCRAM_SIZE - 4)/4); i++)
		temp[i] = 0;
}

static void idle_task()
{
	if (loop_low == 0xffffffff) {
		loop_low = 0;
		loop_high++;
	} else {
		loop_low++;
	}
	return;
}

void __noreturn wlan_task(void)
{
	loop_low=loop_high=0;

	while(1) {
		/* update wdt timer */
		A_WDT_TASK();

		/* UPDATE cticks - to be moved to idle_tsk, put here will be easier to read  */
		A_CLOCK_TICK();

		HIF_isr_handler(NULL);

#if MAGPIE_ENABLE_WLAN == 1
		wlan_pci_isr();
#endif

		A_TASKLET_RUN();
		A_TIMER_RUN();

		/* Very low priority tasks */
		if ((loop_low & 0x1fff) == 0x7)
			A_DBG_TASK();

		idle_task();
	}
}

#endif /* #if defined(_RAM_) */
