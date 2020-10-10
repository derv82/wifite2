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
/**
 * @ingroup adf_net_public
 * @file adf_net_types.h
 * This file defines types used in the networking stack abstraction.
 */

#ifndef _ADF_NET_TYPES_H
#define _ADF_NET_TYPES_H



/**
 * @brief These control/get info from the device
 */
#define ADF_NET_CMD(_x)           \
    ADF_NET_CMD_GET_##_x,        \
    ADF_NET_CMD_SET_##_x

/**
 * @brief Get/Set commands from anet to adf_drv
 */
typedef enum {
    ADF_NET_CMD(LINK_INFO),
    ADF_NET_CMD(POLL_INFO),
    ADF_NET_CMD(CKSUM_INFO),
    ADF_NET_CMD(RING_INFO),
    ADF_NET_CMD(MAC_ADDR),
    ADF_NET_CMD(MTU),
    ADF_NET_CMD_GET_DMA_INFO,
    ADF_NET_CMD_GET_OFFLOAD_CAP,
    ADF_NET_CMD_GET_STATS,
    ADF_NET_CMD_ADD_VID,
    ADF_NET_CMD_DEL_VID,
    ADF_NET_CMD_SET_MCAST,
    ADF_NET_CMD_GET_MCAST_CAP
}adf_net_cmd_t;



/**
 * @brief Indicates what features are supported by the interface. 
 */
#define ADF_NET_LINK_SUPP_10baseT_Half      (1 << 0)
#define ADF_NET_LINK_SUPP_10baseT_Full      (1 << 1)
#define ADF_NET_LINK_SUPP_100baseT_Half     (1 << 2)
#define ADF_NET_LINK_SUPP_100baseT_Full     (1 << 3)
#define ADF_NET_LINK_SUPP_1000baseT_Half    (1 << 4)
#define ADF_NET_LINK_SUPP_1000baseT_Full    (1 << 5)
#define ADF_NET_LINK_SUPP_Autoneg           (1 << 6)
#define ADF_NET_LINK_SUPP_Pause             (1 << 7)
#define ADF_NET_LINK_SUPP_Asym_Pause        (1 << 8)

#define ADF_NET_LINK_SUPP_100               (ADF_NET_LINK_SUPP_10baseT_Half  |   \
                                          ADF_NET_LINK_SUPP_10baseT_Full  |   \
                                          ADF_NET_LINK_SUPP_100baseT_Half |   \
                                          ADF_NET_LINK_SUPP_100baseT_Full)

#define ADF_NET_LINK_SUPP_1000               (ADF_NET_LINK_SUPP_100 |             \
                                           ADF_NET_LINK_SUPP_1000baseT_Full)

/**
 * @brief Indicates what features are advertised by the interface. 
 */
#define ADF_NET_LINK_ADV_10baseT_Half     (1 << 0)
#define ADF_NET_LINK_ADV_10baseT_Full     (1 << 1)
#define ADF_NET_LINK_ADV_100baseT_Half    (1 << 2)
#define ADF_NET_LINK_ADV_100baseT_Full    (1 << 3)
#define ADF_NET_LINK_ADV_1000baseT_Half   (1 << 4)
#define ADF_NET_LINK_ADV_1000baseT_Full   (1 << 5)
#define ADF_NET_LINK_ADV_Autoneg          (1 << 6)
#define ADF_NET_LINK_ADV_Pause            (1 << 7)
#define ADF_NET_LINK_ADV_Asym_Pause       (1 << 8)

#define ADF_NET_LINK_ADV_100             (ADF_NET_LINK_ADV_10baseT_Half  |  \
                                         ADF_NET_LINK_ADV_10baseT_Full  |   \
                                         ADF_NET_LINK_ADV_100baseT_Half |   \
                                         ADF_NET_LINK_ADV_100baseT_Full)

#define ADF_NET_LINK_ADV_1000            (ADF_NET_LINK_ADV_100 |            \
                                          ADF_NET_LINK_ADV_1000baseT_Full)

/**
 * @brief The forced/current speed/duplex/autoneg
 */
#define ADF_NET_LINK_SPEED_10        10
#define ADF_NET_LINK_SPEED_100       100
#define ADF_NET_LINK_SPEED_1000      1000

#define ADF_NET_LINK_DUPLEX_HALF     0x00
#define ADF_NET_LINK_DUPLEX_FULL     0x01

#define ADF_NET_LINK_AUTONEG_DISABLE 0x00
#define ADF_NET_LINK_AUTONEG_ENABLE  0x01

#define ADF_NET_MAC_ADDR_MAX_LEN 6
#define ADF_NET_IF_NAME_SIZE    64
#define ADF_NET_ETH_LEN         ADF_NET_MAC_ADDR_MAX_LEN
#define ADF_NET_MAX_MCAST_ADDR  128

/**
 * @brief link info capability/parameters for the device
 * Note the flags below
 */
typedef struct {
    a_uint32_t  supported;   /*RO Features this if supports*/
    a_uint32_t  advertized;  /*Features this interface advertizes*/
    a_int16_t   speed;       /*Force speed 10M, 100M, gigE*/
    a_int8_t    duplex;      /*duplex full or half*/
    a_uint8_t   autoneg;     /*Enabled/disable autoneg*/
}adf_net_cmd_link_info_t;

typedef struct adf_net_ethaddr{
        a_uint8_t   addr[ADF_NET_ETH_LEN];
} adf_net_ethaddr_t;
typedef struct {
    a_uint8_t   ether_dhost[ADF_NET_ETH_LEN];   /* destination eth addr */
    a_uint8_t	ether_shost[ADF_NET_ETH_LEN];   /* source ether addr    */
    a_uint16_t  ether_type;                     /* packet type ID field */
}adf_net_ethhdr_t;

typedef struct {
#if defined (ADF_LITTLE_ENDIAN_MACHINE)
    a_uint8_t       ip_hl:4,
                    ip_version:4;
#elif defined (ADF_BIG_ENDIAN_MACHINE)
    a_uint8_t       ip_version:4,
                    ip_hl:4;
#else
#error  "Please fix"
#endif
    a_uint8_t       ip_tos;

    a_uint16_t      ip_len;
    a_uint16_t      ip_id;
    a_uint16_t      ip_frag_off;
    a_uint8_t       ip_ttl;
    a_uint8_t       ip_proto;
    a_uint16_t      ip_check;
    a_uint32_t      ip_saddr;
    a_uint32_t      ip_daddr;
    /*The options start here. */
 }adf_net_iphdr_t;

/**
 * @brief Vlan header
 */
typedef struct adf_net_vlanhdr{
    a_uint16_t      tpid;
#if defined (ADF_LITTLE_ENDIAN_MACHINE)
    a_uint16_t      vid:12; /* Vlan id*/
    a_uint8_t       cfi:1; /* reserved for CFI, don't use*/
    a_uint8_t       prio:3; /* Priority*/
#elif defined (ADF_BIG_ENDIAN_MACHINE)
    a_uint8_t       prio:3; /* Priority*/
    a_uint8_t       cfi:1; /* reserved for CFI, don't use*/
    a_uint16_t      vid:12; /* Vlan id*/
#else
#error  "Please fix"
#endif
}adf_net_vlanhdr_t;

typedef struct adf_net_vid{
#if defined (ADF_LITTLE_ENDIAN_MACHINE)
    a_uint16_t      val:12;
    a_uint8_t       res:4;  
#elif defined (ADF_BIG_ENDIAN_MACHINE)
    a_uint8_t      res:4;
    a_uint16_t      val:12;
#else
#error  "Please fix"
#endif
}adf_net_vid_t;


/**
 * @brief Command for setting ring paramters.
 */
typedef struct {
    a_uint32_t rx_bufsize;  /*Ro field. For shim's that maintain a pool*/
    a_uint32_t rx_ndesc;
    a_uint32_t tx_ndesc;
}adf_net_cmd_ring_info_t;

/**
 * @brief Whether the interface is polled or not. If so, the polling bias (number of
 * packets it wants to process per invocation
 */
typedef struct {
    a_bool_t    polled;
    a_uint32_t  poll_wt;
}adf_net_cmd_poll_info_t;

/**
 * @brief Basic device info
 */
typedef struct {
    a_uint8_t      if_name[ADF_NET_IF_NAME_SIZE];
    a_uint8_t       dev_addr[ADF_NET_MAC_ADDR_MAX_LEN];
}adf_net_dev_info_t;

typedef struct adf_dma_info {
    adf_os_dma_mask_t   dma_mask;
    a_uint32_t          sg_nsegs; /**< scatter segments */
}adf_net_cmd_dma_info_t;

/**
 * @brief Defines the TX and RX checksumming capabilities/state of the device
 * The actual checksum handling happens on an adf_nbuf
 * If offload capability command not supported, all offloads are assumed to be
 * none.
 */
typedef enum {
    ADF_NET_CKSUM_NONE,           /*Cannot do any checksum*/
    ADF_NET_CKSUM_TCP_UDP_IPv4,   /*tcp/udp on ipv4 with pseudo hdr*/
    ADF_NET_CKSUM_TCP_UDP_IPv6,   /*tcp/udp on ipv6*/
}adf_net_cksum_type_t;

typedef struct {
    adf_net_cksum_type_t tx_cksum;
    adf_net_cksum_type_t rx_cksum;
}adf_net_cksum_info_t;

typedef adf_net_cksum_info_t adf_net_cmd_cksum_info_t;    /*XXX needed?*/

/**
 * @brief Command for set/unset vid
 */
typedef a_uint16_t adf_net_cmd_vid_t ;        /*get/set vlan id*/

typedef enum {
    ADF_NET_TSO_NONE,
    ADF_NET_TSO_IPV4,     /**< for tsp ipv4 only*/
    ADF_NET_TSO_ALL,      /**< ip4 & ipv6*/
}adf_net_tso_type_t;

/**
 * @brief Command for getting offloading capabilities of a device
 */
typedef struct {
    adf_net_cksum_info_t cksum_cap;
    adf_net_tso_type_t   tso;
    a_uint8_t         vlan_supported;
}adf_net_cmd_offload_cap_t;

/**
 * @brief Command for getting general stats from a device
 */
typedef struct {
    a_uint32_t tx_packets;  /**< total packets transmitted*/
    a_uint32_t rx_packets;  /**< total packets recieved*/
    a_uint32_t tx_bytes;    /**< total bytes transmitted*/
    a_uint32_t rx_bytes;    /**< total bytes recieved*/
    a_uint32_t tx_dropped;  /**< total tx dropped because of lack of buffers*/
    a_uint32_t rx_dropped;  /**< total rx dropped because of lack of buffers*/
    a_uint32_t rx_errors;   /**< bad packet recieved*/
    a_uint32_t tx_errors;   /**< transmisison problems*/
}adf_net_cmd_stats_t;

typedef enum adf_net_cmd_mcast_cap{
    ADF_NET_MCAST_SUP=0,
    ADF_NET_MCAST_NOTSUP
}adf_net_cmd_mcast_cap_t;

typedef struct adf_net_cmd_mcaddr{
    a_uint32_t              nelem; /**< No. of mcast addresses*/
    adf_net_ethaddr_t       mcast[ADF_NET_MAX_MCAST_ADDR];
}adf_net_cmd_mcaddr_t;

typedef union {
    adf_net_cmd_link_info_t     link_info;
    adf_net_cmd_poll_info_t     poll_info;
    adf_net_cmd_cksum_info_t    cksum_info;
    adf_net_cmd_ring_info_t     ring_info;
    adf_net_cmd_dma_info_t      dma_info;
    adf_net_cmd_vid_t           vid;
    adf_net_cmd_offload_cap_t   offload_cap;
    adf_net_cmd_stats_t         stats;
    adf_net_cmd_mcaddr_t        mcast_info;
    adf_net_cmd_mcast_cap_t     mcast_cap;
}adf_net_cmd_data_t;

/**
 * @brief For polled devices, adf_drv responds with one of the following status in 
 * its poll function.
 */
typedef enum {
    ADF_NET_POLL_DONE,
    ADF_NET_POLL_NOT_DONE,
    ADF_NET_POLL_OOM,
}adf_net_poll_resp_t;

/**
 * @brief For recieve checksum API
 */
typedef enum {
    ADF_NBUF_RX_CKSUM_NONE,        /*device failed to ckecksum*/
    ADF_NBUF_RX_CKSUM_HW,          /*checksum successful and value returned*/
    ADF_NBUF_RX_CKSUM_UNNECESSARY, /*cksum successful, no value*/
}adf_nbuf_rx_cksum_type_t;

typedef struct {
    adf_nbuf_rx_cksum_type_t result;
    a_uint32_t               val;
}adf_nbuf_rx_cksum_t;

/**
 * @brief For TCP large Segment Offload
 */
typedef struct {
    adf_net_tso_type_t  type;
    a_uint16_t          mss;
    a_uint8_t           hdr_off;
}adf_nbuf_tso_t;

/**
 * @brief Wireless events
 * ADF_IEEE80211_ASSOC = station associate (bss mode)
 * ADF_IEEE80211_REASSOC = station re-associate (bss mode)
 * ADF_IEEE80211_DISASSOC = station disassociate (bss mode)
 * ADF_IEEE80211_JOIN = station join (ap mode)
 * ADF_IEEE80211_LEAVE = station leave (ap mode)
 * ADF_IEEE80211_SCAN = scan complete, results available
 * ADF_IEEE80211_REPLAY = sequence counter replay detected
 * ADF_IEEE80211_MICHAEL = Michael MIC failure detected
 * ADF_IEEE80211_REJOIN = station re-associate (ap mode)
 * ADF_CUSTOM_PUSH_BUTTON =
 */
typedef enum adf_net_wireless_events{
    ADF_IEEE80211_ASSOC = __ADF_IEEE80211_ASSOC,
    ADF_IEEE80211_REASSOC = __ADF_IEEE80211_REASSOC,
    ADF_IEEE80211_DISASSOC = __ADF_IEEE80211_DISASSOC,
    ADF_IEEE80211_JOIN = __ADF_IEEE80211_JOIN,
    ADF_IEEE80211_LEAVE = __ADF_IEEE80211_LEAVE,
    ADF_IEEE80211_SCAN = __ADF_IEEE80211_SCAN,
    ADF_IEEE80211_REPLAY = __ADF_IEEE80211_REPLAY,
    ADF_IEEE80211_MICHAEL = __ADF_IEEE80211_MICHAEL,
    ADF_IEEE80211_REJOIN = __ADF_IEEE80211_REJOIN, 
    ADF_CUSTOM_PUSH_BUTTON = __ADF_CUSTOM_PUSH_BUTTON
}adf_net_wireless_event_t;

#endif /*_ADF_NET_TYPES_H*/
