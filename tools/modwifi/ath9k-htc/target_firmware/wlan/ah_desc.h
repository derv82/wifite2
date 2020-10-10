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

#ifndef _DEV_ATH_DESC_H
#define _DEV_ATH_DESC_H

#include <asf_queue.h>
#include <wlan_cfg.h>

#define HAL_TXSTAT_ALTRATE  0x80
#define ts_rssi ts_rssi_combined

struct ath_tx_status {
    a_uint32_t   ts_tstamp;
    a_uint16_t   ts_seqnum;
    a_uint8_t    ts_status;
    a_uint8_t    ts_flags;
    a_uint8_t    ts_rate;
    int8_t       ts_rssi_combined;
    int8_t       ts_rssi_ctl0;
    int8_t       ts_rssi_ctl1;
    int8_t       ts_rssi_ctl2;
    int8_t       ts_rssi_ext0;
    int8_t       ts_rssi_ext1;
    int8_t       ts_rssi_ext2;
    a_uint8_t    ts_shortretry;
    a_uint8_t    ts_longretry;
    a_uint8_t    ts_virtcol;
    a_uint8_t    ts_antenna;
    a_uint32_t   ba_low;
    a_uint32_t   ba_high;
    a_uint32_t   evm0;
    a_uint32_t   evm1;
    a_uint32_t   evm2;
};

#define HAL_TXERR_XRETRY            0x01
#define HAL_TXERR_FILT              0x02
#define HAL_TXERR_FIFO              0x04
#define HAL_TXERR_XTXOP             0x08
#define HAL_TXERR_TIMER_EXPIRED     0x10

#define HAL_TX_BA                   0x01
#define HAL_TX_PWRMGMT              0x02
#define HAL_TX_DESC_CFG_ERR         0x04
#define HAL_TX_DATA_UNDERRUN        0x08
#define HAL_TX_DELIM_UNDERRUN       0x10
#define HAL_TX_SW_FILTERED          0x80

struct ath_rx_status {
    a_uint64_t   rs_tstamp;
    a_uint16_t   rs_datalen;
    a_uint8_t    rs_status;
    a_uint8_t    rs_phyerr;
    int8_t       rs_rssi_combined;
    int8_t       rs_rssi_ctl0;
    int8_t       rs_rssi_ctl1;
    int8_t       rs_rssi_ctl2;
    int8_t       rs_rssi_ext0;
    int8_t       rs_rssi_ext1;
    int8_t       rs_rssi_ext2;
    a_uint8_t    rs_keyix;
    a_uint8_t    rs_rate;
    a_uint8_t    rs_antenna;
    a_uint8_t    rs_more;
    a_uint8_t    rs_isaggr;
    a_uint8_t    rs_moreaggr;
    a_uint8_t    rs_num_delims;
    a_uint8_t    rs_flags;
    a_uint8_t    rs_dummy;
    a_uint32_t   evm0;
    a_uint32_t   evm1;
    a_uint32_t   evm2;
};

#define rs_rssi rs_rssi_combined

#define HAL_RXERR_CRC               0x01
#define HAL_RXERR_PHY               0x02
#define HAL_RXERR_FIFO              0x04
#define HAL_RXERR_DECRYPT           0x08
#define HAL_RXERR_MIC               0x10

#define HAL_RX_MORE                 0x01
#define HAL_RX_MORE_AGGR            0x02
#define HAL_RX_GI                   0x04
#define HAL_RX_2040                 0x08
#define HAL_RX_DELIM_CRC_PRE        0x10
#define HAL_RX_DELIM_CRC_POST       0x20
#define HAL_RX_DECRYPT_BUSY         0x40



#define HAL_RXKEYIX_INVALID ((a_uint8_t) -1)

#define HAL_TXKEYIX_INVALID ((a_uint8_t) -1)

/*
 * The following definitions are passed directly
 * the hardware and managed by the HAL.  Drivers
 * should not touch those elements marked opaque.
 */
#define ATH_GENERIC_DESC			\
	a_uint32_t   ds_link;			\
	a_uint32_t   ds_data;			\
	a_uint32_t   ds_ctl0;			\
	a_uint32_t   ds_ctl1;

struct ath_desc {
    ATH_GENERIC_DESC
} adf_os_packed;

struct ath_rx_desc {
    ATH_GENERIC_DESC
    a_uint32_t                 ds_hw[9];
    adf_nbuf_t                 ds_nbuf;
    adf_os_dma_map_t           ds_dmap;
    adf_os_dmamap_info_t       ds_dmap_info;
    adf_os_dma_addr_t          ds_daddr;
    asf_tailq_entry(ath_rx_desc)  ds_list;
} adf_os_packed;

struct ath_tx_desc {
    ATH_GENERIC_DESC
    a_uint32_t   ds_hw[20];
    union {
	struct ath_tx_status tx;
    } ds_us;
} adf_os_packed;

#define ds_txstat   ds_us.tx


#define HAL_TXDESC_CLRDMASK     0x0001
#define HAL_TXDESC_NOACK        0x0002
#define HAL_TXDESC_RTSENA       0x0004
#define HAL_TXDESC_CTSENA       0x0008
#define HAL_TXDESC_INTREQ       0x0010
#define HAL_TXDESC_VEOL         0x0020
#define HAL_TXDESC_EXT_ONLY     0x0040
#define HAL_TXDESC_EXT_AND_CTL  0x0080
#define HAL_TXDESC_VMF          0x0100


#define HAL_RXDESC_INTREQ   0x0020

#endif
