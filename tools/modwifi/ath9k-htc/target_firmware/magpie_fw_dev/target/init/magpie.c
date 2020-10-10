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

#if defined(_RAM_)

#include "dt_defs.h"
#include "athos_api.h"

#include "adf_os_mem.h"

#define MAGPIE 1

#if MAGPIE==1

void htc_setup_comp(void)
{
}

/* target WMI command related globals */
static void dispatch_magpie_sys_cmds(void *pContext, A_UINT16 Command,
				     A_UINT16 SeqNo, A_UINT8 *buffer, int Length);

#if MAGPIE_ENABLE_WLAN == 0
static WMI_DISPATCH_ENTRY Magpie_Sys_DispatchEntries[] =
{
	{dispatch_magpie_sys_cmds,  WMI_ECHO_CMDID, 0},
	{dispatch_magpie_sys_cmds,  WMI_ACCESS_MEMORY_CMDID, 0}
};

static WMI_DECLARE_DISPATCH_TABLE(Magpie_Sys_Commands_Tbl, Magpie_Sys_DispatchEntries);
#endif

htc_handle_t htc_handle;

extern void HTC_Loopback_Init(htc_handle_t handle);
extern void _wmi_cmd_rsp(void *pContext, WMI_COMMAND_ID cmd_id,
			 A_UINT16 SeqNo, A_UINT8 *buffer, int Length);

static void handle_echo_command(void *pContext, A_UINT16 SeqNo,
				A_UINT8 *buffer, int Length)
{
	_wmi_cmd_rsp(pContext, WMI_ECHO_CMDID, SeqNo, buffer, Length);
}

static void dispatch_magpie_sys_cmds(void *pContext, A_UINT16 Command,
				     A_UINT16 SeqNo, A_UINT8 *buffer, int Length)
{
	switch(Command)
	{
        case WMI_ECHO_CMDID:
		handle_echo_command(pContext, SeqNo, buffer, Length);
		break;

        case WMI_ACCESS_MEMORY_CMDID:
		break;
	}
}

void _wmi_cmd_rsp(void *pContext, WMI_COMMAND_ID cmd_id, A_UINT16 SeqNo,
		  A_UINT8 *buffer, int Length)
{
	adf_nbuf_t netbuf = ADF_NBUF_NULL;
	A_UINT8 *pData;

	netbuf = WMI_AllocEvent(pContext, WMI_EVT_CLASS_CMD_REPLY, sizeof(WMI_CMD_HDR) + Length);
    
	if (netbuf == ADF_NBUF_NULL) {
		adf_os_print("%s: buffer allocation for event_id %x failed!\n", __FUNCTION__, cmd_id);
		adf_os_assert(0);
		return;
	}

	if (Length != 0 && buffer != NULL) {
		pData = (A_UINT8 *)adf_nbuf_put_tail(netbuf, Length);
		adf_os_mem_copy(pData, buffer, Length);
	}

	WMI_SendEvent(pContext, netbuf, cmd_id, SeqNo, Length);
}


void Magpie_init(void)
{
	A_PRINTF("[+++Magpie_init]\n\r");
 
	A_PRINTF("[+++VBUF_init(%d)]\n\r", MAX_BUF_NUM);
	VBUF_init(MAX_BUF_NUM);
    
	A_PRINTF("[+++VBUF_init(%d)]\n\r", MAX_DESC_NUM);
	VDESC_init(MAX_DESC_NUM);

#if MAGPIE_ENABLE_WLAN == 0
	aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		hif_handle = HIF_init(0);

#if ZM_FM_LOOPBACK == 1
	HIF_config_pipe(hif_handle, HIF_USB_PIPE_TX, 5);
	HIF_config_pipe(hif_handle, HIF_USB_PIPE_COMMAND, 2);

#if SYSTEM_MODULE_HP_EP5
	HIF_config_pipe(hif_handle, HIF_USB_PIPE_HP_TX, 3);
#endif
#if SYSTEM_MODULE_HP_EP6
	HIF_config_pipe(hif_handle, HIF_USB_PIPE_MP_TX, 3);
#endif
    
	A_PRINTF("[+++HIF_init(0)]\n\r");

	HIF_start(hif_handle);

#else /* ZM_FM_LOOPBACK == 0 */
	// initialize HTC
	htcConf.CreditSize = 320;
	htcConf.CreditNumber = 10;
#if 1
	htcConf.ControlDownLinkPipeID = HIF_USB_PIPE_INTERRUPT;         // Target -> Host
	htcConf.ControlUpLinkPipeID = HIF_USB_PIPE_COMMAND;             // Host   -> Target
#else
	htcConf.ControlDownLinkPipeID = HIF_USB_PIPE_RX;
	htcConf.ControlUpLinkPipeID = HIF_USB_PIPE_TX;
#endif
	htcConf.HIFHandle = hif_handle;
	htcConf.OSHandle = 0;             // not used
	htcConf.PoolHandle = pool_handle;

	htc_handle = HTC_init(htc_setup_comp, &htcConf);
	// Initialize HTC services
	HTC_Loopback_Init(htc_handle);

	adf_os_mem_zero(&wmiConfig, sizeof(WMI_SVC_CONFIG));
	wmiConfig.HtcHandle = htc_handle;
	wmiConfig.PoolHandle = pool_handle;
	wmiConfig.MaxCmdReplyEvts = 1;
	wmiConfig.MaxEventEvts = 1;

	wmi_handle = WMI_Init(&wmiConfig);
	Magpie_Sys_Commands_Tbl.pContext = wmi_handle;
	WMI_RegisterDispatchTable(Magpie_Sys_Commands_Tbl.pContext, &Magpie_Sys_Commands_Tbl);

#endif/* ZM_FM_LOOPBACK == 0 */
#endif /* MAGPIE_ENABLE_WLAN */                 
}

#endif /* #if MAGPIE==1 */

#endif /* #if defined(_RAM_) */
