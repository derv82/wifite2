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
#ifndef __HIF_GMAC_H
#define __HIF_GMAC_H

#include <adf_os_types.h>
#include <hif_api.h>


#define ETH_ALEN                6
#define GMAC_MAX_PKT_LEN        1600
#define GMAC_MAX_DESC           5

#define GMAC_DISCV_PKT_SZ       60
#define GMAC_DISCV_WAIT         2000

#define ATH_P_MAGBOOT           0x12 /*Magpie GMAC 18 for boot downloader*/
#define ATH_P_MAGNORM           0x13 /*Magpie GMAC 19 for HTC & others*/

#define ETH_P_ATH               0x88bd
     
typedef enum hif_gmac_pipe{
    HIF_GMAC_PIPE_RX = 1, /*Normal Priority RX*/
    HIF_GMAC_PIPE_TX = 2, /*Normal Priority TX*/
}hif_gmac_pipe_t;

struct gmac_api{
    void (*gmac_boot_init)(void);
};

void    cmnos_gmac_module_install(struct gmac_api *boot_apis);
void    hif_gmac_module_install(struct hif_api *apis);


#endif

