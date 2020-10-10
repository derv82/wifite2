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
#ifndef __HIF_PCI_H
#define __HIF_PCI_H

#include <hif_api.h>


#define PCI_MAX_DATA_PKT_LEN            1600
#define PCI_MAX_CMD_PKT_LEN             64
#define PCI_MAX_BOOT_DESC               2 
     
typedef enum hif_pci_pipe_rx{
    HIF_PCI_PIPE_RX0, /*Normal Priority RX*/
    HIF_PCI_PIPE_RX1,
    HIF_PCI_PIPE_RX2,
    HIF_PCI_PIPE_RX3,
    HIF_PCI_PIPE_RX_MAX
}hif_pci_pipe_rx_t;

typedef enum hif_pci_pipe_tx{
    HIF_PCI_PIPE_TX0, /*Normal Priority TX*/
    HIF_PCI_PIPE_TX1,
    HIF_PCI_PIPE_TX_MAX
}hif_pci_pipe_tx_t;

struct pci_api{
    void (*pci_boot_init)(void);
};

void        cmnos_pci_module_install(struct pci_api *apis);
void        hif_pci_module_install(struct hif_api *apis);
#endif


