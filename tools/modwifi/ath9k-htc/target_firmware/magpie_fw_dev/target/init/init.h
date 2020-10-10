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
// @TODO: Should define the memory region later~
#define ALLOCRAM_START       ( ((unsigned int)&_fw_image_end) + 4)
#define ALLOCRAM_SIZE        ( SYS_RAM_SZIE - ( ALLOCRAM_START - SYS_D_RAM_REGION_0_BASE) - SYS_D_RAM_STACK_SIZE)

#include "regdump.h"
#include <linux/compiler.h>

#define SBOOT_PATTERN 0x5342
#define IS_FLASHBOOT() (((DEBUG_SYSTEM_STATE&~(0x0000ffff))>>16==SBOOT_PATTERN))

// patch for exception handle
void AR6002_fatal_exception_handler_patch(CPU_exception_frame_t *exc_frame);
void exception_reset(struct register_dump_s *dump);

void (* _assfail_ori)(struct register_dump_s *);
void HTCMsgRecvHandler_patch(adf_nbuf_t hdr_buf, adf_nbuf_t buffer, void *context);
void HTCControlSvcProcessMsg_patch(HTC_ENDPOINT_ID EndpointID, adf_nbuf_t hdr_buf,
				   adf_nbuf_t pBuffers, void *arg);

#if defined(PROJECT_K2)

#if MOVE_PRINT_TO_RAM
extern int fw_cmnos_printf(const char *fmt, ...);

extern uint16_t u8UsbConfigValue;
extern uint16_t u8UsbInterfaceValue;
extern uint16_t u8UsbInterfaceAlternateSetting;
#endif

extern void _fw_usb_fw_task(void);
extern void _fw_usb_reset_fifo(void);

#endif


void fatal_exception_func();
void init_mem();
void __noreturn wlan_task();
