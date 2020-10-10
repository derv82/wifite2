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
#include "sys_cfg.h"

#if SYSTEM_MODULE_MISC

#include "athos_api.h"
#include "regdump.h"

#if SYSTEM_MODULE_USB
extern uint16_t UsbDeviceDescriptor[];
#endif

/* This number gets bumped on each official build.  */
// uint32_t cmnos_target_software_id = AR6K_SW_VERSION;

/*!
 *	system reset
 */
LOCAL void
cmnos_system_reset(void)
{
	/* TBD: to be finished */
	/*!
	 * sytem reset backdoor
	 */
	 HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR, (0x1<<24));
}

#if 0
/*!
 *	wdt reset
 */
#LOCAL void cmnos_wdt_reset(void)
{
	HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR, (0x1<<24));
}
#endif

/*!
 * mac reset
 */
LOCAL void
cmnos_mac_reset(void)
{
	/* TBD: to be finished */
	/*!
	 * mac reset backdoor
	 */
}

volatile int assloop = 1;
int assprint = 1;

//A_COMPILE_TIME_ASSERT(verify_RD_SIZE, (RD_SIZE == sizeof(CPU_exception_frame_t)))

LOCAL void
cmnos_misaligned_load_handler(struct register_dump_s *dump)
{
	/* TBD: to be finished */
    if (A_IML_IS_ASSERT(dump->badvaddr)) {
        /*
         * Probably an Intentional Misaligned Load, used to
         * signal an assertion failure
         */
        dump->assline = A_IML_ASSLINE(dump->badvaddr);
        A_ASSFAIL(dump);
    } else {
        /* A genuine misaligned load */
        A_PRINTF("Misaligned load: pc=0x%x badvaddr=0x%x dump area=0x%x\n",
                dump->pc, dump->badvaddr, dump);
        dump->assline = 0;
        A_ASSFAIL(dump); /* Not really an assertion failure, but we'll treat it similarly. */
    }

    // trigger wdt, in case hang
    HAL_WORD_REG_WRITE(MAGPIE_REG_RST_WDT_TIMER_CTRL_ADDR, 0x03);
    HAL_WORD_REG_WRITE(MAGPIE_REG_RST_WDT_TIMER_ADDR, 0x10);

    while(1);
}

struct register_dump_s *current_dump = NULL;

/*!
 * A convenient place to set a breakpoint.
 * Whenever an A_ASSERT triggers, it comes here.
 */
LOCAL void
cmnos_assfail(struct register_dump_s *dump)
{
    if (current_dump == NULL ) {
        A_UINT32 target_id;

        current_dump = dump;
        //A_TARGET_ID_GET(&target_id);
        dump->target_id = target_id;

        if (assprint) {
            unsigned int i;

            A_PRINTF("assertion failed? pc=0x%x, line=%d, dump area=0x%x\n",
                    dump->pc, dump->assline, dump);
//            INF_DBG2_LOG(INF_ASSERTION_FAILED, dump->pc,
//                         A_IML_ASSLINE(dump->badvaddr));
//            INF_DBG1_LOG(INF_ASSERTION_FAILED, (A_UINT32)dump);

            A_PRINTF("Target ID: 0x%x (%d)\n", target_id, target_id);
//            INF_DBG1_LOG(INF_TARGET_ID, target_id);

            A_PRINTF("Debug Info:");
            for (i=0; i<(sizeof(struct register_dump_s)/sizeof(A_UINT32)); i++) {
                if ((i%4) == 0) {
                    A_PRINTF("\n");
                }
                A_PRINTF("0x%08x ", ((A_UINT32 *)dump)[i]);
//                INF_DBG1_LOG(INF_ASSERTION_FAILED, ((A_UINT32 *)dump)[i]);
            }
            A_PRINTF("\n");
        }
    } else {
        /*
         * We must have assfail'ed again while processing the first assfail.
         * Don't try to print anything -- keep it very simple.
         */

    }
}

/*!
 * failure state report
 */
LOCAL void
cmnos_report_failure_to_host(struct register_dump_s *dump, int len)
{
	/* TBD: to be removed! */
}

/*!
 * get target id
 */
LOCAL int
cmnos_target_id_get(void)
{
	/* TBD: to be removed! */
}

/*!
 * get keyboard hit with delay
 */
LOCAL uint8_t
cmnos_get_kbhit(uint8_t delay)
{
    uint32_t last_ccount;
    uint8_t kbhit;

    last_ccount = xthal_get_ccount();
    while (1)
    {
        if( A_GETC(&kbhit) != 0 )
            break;

        if((xthal_get_ccount() - last_ccount)>=delay*1000*ONE_MSEC)
        {
            break;
        }
    }

    return kbhit;
}

/*!
 * host alive & return the hostif type
 */
LOCAL A_HOSTIF
cmnos_is_host_present(void)
{
    /*!
      *  TODO: check the hostif and return the type of host interface
      */
	A_HOSTIF mHif = HIF_USB;
#if defined(PROJECT_K2)
    A_PRINTF("5. usb only!!\n");
    return mHif;
#elif defined(PROJECT_MAGPIE)
    uint32_t mData;

    mData = MAGPIE_REG_RST_BOOTSTRAP;

	//@RYAN@TODO - this one is somehow not working on L5, need to turn on!!!
#if 1
    /* 4:3  of BOOTSTRAP could distinguish the host interfce
     *
     *   2'b11 -> gmac
     *   2'b10 -> pci
     *   2'b01 -> pcie
     *   2'b00 -> usb
     *
     */
    if( mData & BIT3 )
    {
        if ( mData & BIT2 )
            mHif = HIF_GMAC;
        else
            mHif = HIF_PCI;
    }    
    else
    {
        if ( mData & BIT2 )
            mHif = HIF_PCIE;
        else
            mHif = HIF_USB;
    }
#endif
    //A_PRINTF("5. hif (0x%08x) is read!!\n", mData);
    return mHif;
#endif
}

/*!
 * get ROM code version
 */
LOCAL uint16_t
cmnos_rom_version_get(void)
{
#if SYSTEM_MODULE_USB
    /* USB Device Descriptor : byte 12, 13 Device BCD -> Device release number in binary-coded decimal. */
    return UsbDeviceDescriptor[6];
#else
    return 0;
#endif
}

void
cmnos_misc_module_install(struct misc_api *tbl)
{
    tbl->_system_reset           = cmnos_system_reset;
    tbl->_mac_reset              = cmnos_mac_reset;
    tbl->_assfail                = cmnos_assfail;
    tbl->_misaligned_load_handler= cmnos_misaligned_load_handler;
    tbl->_report_failure_to_host = cmnos_report_failure_to_host;
    //tbl->_target_id_get        = cmnos_target_id_get;
    tbl->_is_host_present        = cmnos_is_host_present;
    tbl->_kbhit                  = cmnos_get_kbhit;
    tbl->_rom_version_get        = cmnos_rom_version_get;
}

#endif

