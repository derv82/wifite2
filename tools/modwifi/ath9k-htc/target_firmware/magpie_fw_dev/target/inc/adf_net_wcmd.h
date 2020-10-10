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
 * Copyright (c) Atheros Communications Inc. 2002-2008
 * 
 */

#ifndef __ADF_NET_WCMD_H
#define __ADF_NET_WCMD_H

#include <adf_os_stdtypes.h>
#include <adf_os_types.h>
#include <adf_net_types.h>



/**
 * Defines
 */
#define ADF_NET_WCMD_NAME_SIZE          __ADF_OS_NAME_SIZE
#define ADF_NET_WCMD_NICK_NAME          32 /**< Max Device nick name size*/     
#define ADF_NET_WCMD_MODE_NAME_LEN      6 
#define ADF_NET_WCMD_IE_MAXLEN          256 /** Max Len for IE */

#define ADF_NET_WCMD_MAX_BITRATES       32
#define ADF_NET_WCMD_MAX_ENC_SZ         8
#define ADF_NET_WCMD_MAX_FREQ           32
#define ADF_NET_WCMD_MAX_TXPOWER        8
#define ADF_NET_WCMD_EVENT_CAP          6

/**
 * @brief key set/get info
 */
#define ADF_NET_WCMD_KEYBUF_SIZE        16
#define ADF_NET_WCMD_MICBUF_SIZE        16/**< space for tx+rx keys */ 
#define ADF_NET_WCMD_KEY_DEFAULT        0x80/**< default xmit key */
#define ADF_NET_WCMD_ADDR_LEN           6
#define ADF_NET_WCMD_KEYDATA_SZ          \
    (ADF_NET_WCMD_KEYBUF_SIZE + ADF_NET_WCMD_MICBUF_SIZE)
/**
 *  @brief key flags
 *  XXX: enum's
 */
#define ADF_NET_WCMD_VAPKEY_XMIT        0x01/**< xmit */
#define ADF_NET_WCMD_VAPKEY_RECV        0x02/**< recv */
#define ADF_NET_WCMD_VAPKEY_GROUP       0x04/**< WPA group*/ 
#define ADF_NET_WCMD_VAPKEY_SWCRYPT     0x10/**< Encrypt/decrypt*/ 
#define ADF_NET_WCMD_VAPKEY_SWMIC       0x20/**< Enmic/Demic */
#define ADF_NET_WCMD_VAPKEY_DEFAULT     0x80/**< Default key */

#define ADF_NET_WCMD_MAX_SSID           32
#define ADF_NET_WCMD_CHAN_BYTES         32

#define ADF_NET_WCMD_RTS_DEFAULT        512
#define ADF_NET_WCMD_RTS_MIN            1
#define ADF_NET_WCMD_RTS_MAX            2346

#define ADF_NET_WCMD_FRAG_MIN           256
#define ADF_NET_WCMD_FRAG_MAX           2346
/**
 *  @brief  Maximum number of address that you may get in the
 *          list of access ponts
 */
#define  ADF_NET_WCMD_MAX_AP            64

#define ADF_NET_WCMD_RATE_MAXSIZE       30
#define ADF_NET_WCMD_NUM_TR_ENTS        128
/**
 * @brief Ethtool specific
 */
#define ADF_NET_WCMD_BUSINFO_LEN        32
#define ADF_NET_WCMD_DRIVSIZ            32  
#define ADF_NET_WCMD_VERSIZ             32  
#define ADF_NET_WCMD_FIRMSIZ            32  
/**
 * *******************************Enums******************
 */
typedef enum adf_net_wcmd_vapmode{
    ADF_NET_WCMD_VAPMODE_AUTO,   /**< Driver default*/
    ADF_NET_WCMD_VAPMODE_ADHOC,  /**< Single cell*/
    ADF_NET_WCMD_VAPMODE_INFRA,  /**< Multi Cell or Roaming*/
    ADF_NET_WCMD_VAPMODE_MASTER, /**< Access Point*/
    ADF_NET_WCMD_VAPMODE_REPEAT, /**< Wireless Repeater*/
    ADF_NET_WCMD_VAPMODE_SECOND, /**< Secondary master or repeater*/
    ADF_NET_WCMD_VAPMODE_MONITOR /**< Passive Monitor*/
}adf_net_wcmd_vapmode_t;
/**
 *  @brief key type
 */
typedef enum adf_net_wcmd_ciphermode{
    ADF_NET_WCMD_CIPHERMODE_WEP,
    ADF_NET_WCMD_CIPHERMODE_TKIP,
    ADF_NET_WCMD_CIPHERMODE_AES_OCB,
    ADF_NET_WCMD_CIPHERMODE_AES_CCM ,
    ADF_NET_WCMD_CIPHERMODE_RESERVE,
    ADF_NET_WCMD_CIPHERMODE_CKIP,
    ADF_NET_WCMD_CIPHERMODE_NONE
}adf_net_wcmd_ciphermode_t;
/**
 * @brief Get/Set wireless commands
 */
typedef enum adf_net_wcmd_type{
    /* net80211 */
    ADF_NET_WCMD_GET_RTS_THRES,     
    ADF_NET_WCMD_SET_RTS_THRES,     
    ADF_NET_WCMD_GET_FRAGMENT,  
    ADF_NET_WCMD_SET_FRAGMENT,  
    ADF_NET_WCMD_GET_VAPMODE,   
    ADF_NET_WCMD_SET_VAPMODE,
    ADF_NET_WCMD_GET_BSSID, 
    ADF_NET_WCMD_SET_BSSID, 
    ADF_NET_WCMD_GET_NICKNAME,      
    ADF_NET_WCMD_SET_NICKNAME,      
    ADF_NET_WCMD_GET_FREQUENCY,     
    ADF_NET_WCMD_SET_FREQUENCY,     
    ADF_NET_WCMD_GET_ESSID, 
    ADF_NET_WCMD_SET_ESSID, 
    ADF_NET_WCMD_GET_TX_POWER,  
    ADF_NET_WCMD_SET_TX_POWER,
    ADF_NET_WCMD_GET_PARAM,
    ADF_NET_WCMD_SET_PARAM,
    ADF_NET_WCMD_GET_OPT_IE,
    ADF_NET_WCMD_SET_OPT_IE,
    ADF_NET_WCMD_GET_APP_IE_BUF,
    ADF_NET_WCMD_SET_APP_IE_BUF,
    ADF_NET_WCMD_SET_ENC,
    ADF_NET_WCMD_GET_KEY,
    ADF_NET_WCMD_SET_KEY,
    ADF_NET_WCMD_GET_SCAN,      
    ADF_NET_WCMD_SET_SCAN,      
    ADF_NET_WCMD_GET_MODE,  
    ADF_NET_WCMD_SET_MODE,  
    ADF_NET_WCMD_GET_CHAN_LIST, 
    ADF_NET_WCMD_SET_CHAN_LIST, 
    ADF_NET_WCMD_GET_WMM_PARAM, 
    ADF_NET_WCMD_SET_WMM_PARAM, 
    ADF_NET_WCMD_GET_VAPNAME,
    ADF_NET_WCMD_GET_IC_CAPS,
    ADF_NET_WCMD_GET_RETRIES,
    ADF_NET_WCMD_GET_WAP_LIST,
    ADF_NET_WCMD_GET_ADDBA_STATUS,
    ADF_NET_WCMD_GET_CHAN_INFO,
    ADF_NET_WCMD_GET_WPA_IE,
    ADF_NET_WCMD_GET_WSC_IE,
    ADF_NET_WCMD_SET_TXPOWER_LIMIT,
    ADF_NET_WCMD_SET_TURBO,
    ADF_NET_WCMD_SET_FILTER,
    ADF_NET_WCMD_SET_ADDBA_RESPONSE,
    ADF_NET_WCMD_SET_MLME,
    ADF_NET_WCMD_SET_SEND_ADDBA,
    ADF_NET_WCMD_SET_SEND_DELBA,
    ADF_NET_WCMD_SET_DELKEY,
    ADF_NET_WCMD_SET_DELMAC,
    ADF_NET_WCMD_SET_ADD_MAC,
    ADF_NET_WCMD_GET_RANGE,
    ADF_NET_WCMD_GET_POWER,
    ADF_NET_WCMD_SET_POWER,
    ADF_NET_WCMD_GET_DEVSTATS,
    ADF_NET_WCMD_SET_MTU,
    ADF_NET_WCMD_SET_SYSCTL,
    ADF_NET_WCMD_GET_STA_STATS,/* stats_sta */
    ADF_NET_WCMD_GET_VAP_STATS, /* stats_vap */
    ADF_NET_WCMD_GET_STATION_LIST, /* station */
    /* Device specific */
    ADF_NET_WCMD_SET_DEV_VAP_CREATE,
    ADF_NET_WCMD_SET_DEV_TX_TIMEOUT,        /* XXX:No data definition */
    ADF_NET_WCMD_SET_DEV_MODE_INIT,         /* XXX:No data definition */
    ADF_NET_WCMD_GET_DEV_STATUS,
    ADF_NET_WCMD_GET_DEV_STATUS_CLR,        /* XXX:No data definition */
    ADF_NET_WCMD_GET_DEV_DIALOG,
    ADF_NET_WCMD_GET_DEV_PHYERR,
    ADF_NET_WCMD_GET_DEV_CWM,
    ADF_NET_WCMD_GET_DEV_ETHTOOL,       
    ADF_NET_WCMD_SET_DEV_MAC,
    ADF_NET_WCMD_SET_DEV_CAP,/*ATH_CAP*/
    /* Device write specific */
    ADF_NET_WCMD_SET_DEV_EIFS_MASK,
    ADF_NET_WCMD_SET_DEV_EIFS_DUR,
    ADF_NET_WCMD_SET_DEV_SLOTTIME,
    ADF_NET_WCMD_SET_DEV_ACKTIMEOUT,
    ADF_NET_WCMD_SET_DEV_CTSTIMEOUT,
    ADF_NET_WCMD_SET_DEV_SOFTLED,
    ADF_NET_WCMD_SET_DEV_LEDPIN,
    ADF_NET_WCMD_SET_DEV_DEBUG,
    ADF_NET_WCMD_SET_DEV_TXANTENNA,
    ADF_NET_WCMD_SET_DEV_RXANTENNA,
    ADF_NET_WCMD_SET_DEV_DIVERSITY,
    ADF_NET_WCMD_SET_DEV_TXINTRPERIOD,
    ADF_NET_WCMD_SET_DEV_FFTXQMIN,
    ADF_NET_WCMD_SET_DEV_TKIPMIC,
    ADF_NET_WCMD_SET_DEV_GLOBALTXTIMEOUT,
    ADF_NET_WCMD_SET_DEV_SW_WSC_BUTTON,
    /* Device read specific */
    ADF_NET_WCMD_GET_DEV_EIFS_MASK,
    ADF_NET_WCMD_GET_DEV_EIFS_DUR,
    ADF_NET_WCMD_GET_DEV_SLOTTIME,
    ADF_NET_WCMD_GET_DEV_ACKTIMEOUT,
    ADF_NET_WCMD_GET_DEV_CTSTIMEOUT,
    ADF_NET_WCMD_GET_DEV_SOFTLED,
    ADF_NET_WCMD_GET_DEV_LEDPIN,
    ADF_NET_WCMD_GET_DEV_COUNTRYCODE,
    ADF_NET_WCMD_GET_DEV_REGDOMAIN,
    ADF_NET_WCMD_GET_DEV_DEBUG,
    ADF_NET_WCMD_GET_DEV_TXANTENNA,
    ADF_NET_WCMD_GET_DEV_RXANTENNA,
    ADF_NET_WCMD_GET_DEV_DIVERSITY,
    ADF_NET_WCMD_GET_DEV_TXINTRPERIOD,
    ADF_NET_WCMD_GET_DEV_FFTXQMIN,
    ADF_NET_WCMD_GET_DEV_TKIPMIC,
    ADF_NET_WCMD_GET_DEV_GLOBALTXTIMEOUT,
    ADF_NET_WCMD_GET_DEV_SW_WSC_BUTTON
}adf_net_wcmd_type_t;
/**
 * @brief Opmodes for the VAP
 */
typedef enum adf_net_wcmd_opmode{
    ADF_NET_WCMD_OPMODE_IBSS,/**< IBSS (adhoc) station */
    ADF_NET_WCMD_OPMODE_STA,/**< Infrastructure station */
    ADF_NET_WCMD_OPMODE_WDS,/**< WDS link */
    ADF_NET_WCMD_OPMODE_AHDEMO,/**< Old lucent compatible adhoc demo */
    ADF_NET_WCMD_OPMODE_RESERVE0,/**<XXX: future use*/
    ADF_NET_WCMD_OPMODE_RESERVE1,/**<XXX: future use*/
    ADF_NET_WCMD_OPMODE_HOSTAP,/**< Software Access Point*/
    ADF_NET_WCMD_OPMODE_RESERVE2,/**<XXX: future use*/
    ADF_NET_WCMD_OPMODE_MONITOR/**< Monitor mode*/
}adf_net_wcmd_opmode_t;

/**
 * brief PHY modes for VAP
 */
typedef enum adf_net_wcmd_phymode{
    ADF_NET_WCMD_PHYMODE_AUTO=0,/**< autoselect */
    ADF_NET_WCMD_PHYMODE_11A=1,/**< 5GHz, OFDM */
    ADF_NET_WCMD_PHYMODE_11B=2,/**< 2GHz, CCK */
    ADF_NET_WCMD_PHYMODE_11G=3,/**< 2GHz, OFDM */
    ADF_NET_WCMD_PHYMODE_FH=4,/**< 2GHz, GFSK */
    ADF_NET_WCMD_PHYMODE_TURBO_A=5,/**< 5GHz, OFDM, 2 x clk dynamic turbo */
    ADF_NET_WCMD_PHYMODE_TURBO_G=6,/**< 2GHz, OFDM, 2 x clk dynamic turbo*/
    ADF_NET_WCMD_PHYMODE_11NA=7,/**< 5GHz, OFDM + MIMO*/
    ADF_NET_WCMD_PHYMODE_11NG=8,/**< 2GHz, OFDM + MIMO*/
    ADF_NET_WCMD_PHYMODE_TURBO_STATIC_A=9,/**< Turbo Static A*/
}adf_net_wcmd_phymode_t;
/**
 * @brief param id
 */
typedef enum adf_net_wcmd_param_id{
    ADF_NET_WCMD_PARAM_TURBO = 1,/**<turbo mode */
    ADF_NET_WCMD_PARAM_MODE,/**< phy mode (11a, 11b, etc.) */
    ADF_NET_WCMD_PARAM_AUTHMODE,/**< authentication mode */
    ADF_NET_WCMD_PARAM_PROTMODE,/**< 802.11g protection */
    ADF_NET_WCMD_PARAM_MCASTCIPHER,/**< multicast/default cipher */
    ADF_NET_WCMD_PARAM_MCASTKEYLEN,/**< multicast key length */
    ADF_NET_WCMD_PARAM_UCASTCIPHERS,/**< unicast cipher suites */
    ADF_NET_WCMD_PARAM_UCASTCIPHER,/**< unicast cipher */
    ADF_NET_WCMD_PARAM_UCASTKEYLEN,/**< unicast key length */
    ADF_NET_WCMD_PARAM_WPA,/**< WPA mode (0,1,2) */
    ADF_NET_WCMD_PARAM_ROAMING,/**< roaming mode */
    ADF_NET_WCMD_PARAM_PRIVACY,/**< privacy invoked */
    ADF_NET_WCMD_PARAM_COUNTERMEASURES,/**< WPA/TKIP countermeasures */
    ADF_NET_WCMD_PARAM_DROPUNENCRYPTED,/**< discard unencrypted frames */
    ADF_NET_WCMD_PARAM_DRIVER_CAPS,/**< driver capabilities */
    ADF_NET_WCMD_PARAM_MACCMD,/**< MAC ACL operation */
    ADF_NET_WCMD_PARAM_WMM,/**< WMM mode (on, off) */
    ADF_NET_WCMD_PARAM_HIDESSID,/**< hide SSID mode (on, off) */
    ADF_NET_WCMD_PARAM_APBRIDGE,/**< AP inter-sta bridging */
    ADF_NET_WCMD_PARAM_KEYMGTALGS,/**< key management algorithms */
    ADF_NET_WCMD_PARAM_RSNCAPS,/**< RSN capabilities */
    ADF_NET_WCMD_PARAM_INACT,/**< station inactivity timeout */
    ADF_NET_WCMD_PARAM_INACT_AUTH,/**< station auth inact timeout */
    ADF_NET_WCMD_PARAM_INACT_INIT,/**< station init inact timeout */
    ADF_NET_WCMD_PARAM_ABOLT,/**< Atheros Adv. Capabilities */
    ADF_NET_WCMD_PARAM_DTIM_PERIOD,/**< DTIM period (beacons) */
    ADF_NET_WCMD_PARAM_BEACON_INTERVAL,/**< beacon interval (ms) */
    ADF_NET_WCMD_PARAM_DOTH,/**< 11.h is on/off */
    ADF_NET_WCMD_PARAM_PWRTARGET,/**< Current Channel Pwr Constraint */
    ADF_NET_WCMD_PARAM_GENREASSOC,/**< Generate a reassociation request */
    ADF_NET_WCMD_PARAM_COMPRESSION,/**< compression */
    ADF_NET_WCMD_PARAM_FF,/**< fast frames support  */
    ADF_NET_WCMD_PARAM_XR,/**< XR support */
    ADF_NET_WCMD_PARAM_BURST,/**< burst mode */
    ADF_NET_WCMD_PARAM_PUREG,/**< pure 11g (no 11b stations) */
    ADF_NET_WCMD_PARAM_AR,/**< AR support */
    ADF_NET_WCMD_PARAM_WDS,/**< Enable 4 address processing */
    ADF_NET_WCMD_PARAM_BGSCAN,/**< bg scanning (on, off) */
    ADF_NET_WCMD_PARAM_BGSCAN_IDLE,/**< bg scan idle threshold */
    ADF_NET_WCMD_PARAM_BGSCAN_INTERVAL,/**< bg scan interval */
    ADF_NET_WCMD_PARAM_MCAST_RATE,/**< Multicast Tx Rate */
    ADF_NET_WCMD_PARAM_COVERAGE_CLASS,/**< coverage class */
    ADF_NET_WCMD_PARAM_COUNTRY_IE,/**< enable country IE */
    ADF_NET_WCMD_PARAM_SCANVALID,/**< scan cache valid threshold */
    ADF_NET_WCMD_PARAM_ROAM_RSSI_11A,/**< rssi threshold in 11a */
    ADF_NET_WCMD_PARAM_ROAM_RSSI_11B,/**< rssi threshold in 11b */
    ADF_NET_WCMD_PARAM_ROAM_RSSI_11G,/**< rssi threshold in 11g */
    ADF_NET_WCMD_PARAM_ROAM_RATE_11A,/**< tx rate threshold in 11a */
    ADF_NET_WCMD_PARAM_ROAM_RATE_11B,/**< tx rate threshold in 11b */
    ADF_NET_WCMD_PARAM_ROAM_RATE_11G,/**< tx rate threshold in 11g */
    ADF_NET_WCMD_PARAM_UAPSDINFO,/**< value for qos info field */
    ADF_NET_WCMD_PARAM_SLEEP,/**< force sleep/wake */
    ADF_NET_WCMD_PARAM_QOSNULL,/**< force sleep/wake */
    ADF_NET_WCMD_PARAM_PSPOLL,/**< force ps-poll generation (sta only) */
    ADF_NET_WCMD_PARAM_EOSPDROP,/**< force uapsd EOSP drop (ap only) */
    ADF_NET_WCMD_PARAM_MARKDFS,/**< mark a dfs interference channel*/
    ADF_NET_WCMD_PARAM_REGCLASS,/**< enable regclass ids in country IE */
    ADF_NET_WCMD_PARAM_CHANBW,/**< set chan bandwidth preference */
    ADF_NET_WCMD_PARAM_WMM_AGGRMODE,/**< set WMM Aggressive Mode */
    ADF_NET_WCMD_PARAM_SHORTPREAMBLE,/**< enable/disable short Preamble */
    ADF_NET_WCMD_PARAM_BLOCKDFSCHAN,/**< enable/disable use of DFS channels */
    ADF_NET_WCMD_PARAM_CWM_MODE,/**< CWM mode */
    ADF_NET_WCMD_PARAM_CWM_EXTOFFSET,/**< Ext. channel offset */
    ADF_NET_WCMD_PARAM_CWM_EXTPROTMODE,/**< Ext. Chan Protection mode */
    ADF_NET_WCMD_PARAM_CWM_EXTPROTSPACING,/**< Ext. chan Protection spacing */
    ADF_NET_WCMD_PARAM_CWM_ENABLE,/**< State machine enabled */
    ADF_NET_WCMD_PARAM_CWM_EXTBUSYTHRESHOLD,/**< Ext. chan busy threshold*/
    ADF_NET_WCMD_PARAM_CWM_CHWIDTH,/**< Current channel width */
    ADF_NET_WCMD_PARAM_SHORT_GI,/**< half GI */
    ADF_NET_WCMD_PARAM_FAST_CC,/**< fast channel change */
    /**
     * 11n A-MPDU, A-MSDU support
     */ 
    ADF_NET_WCMD_PARAM_AMPDU,/**< 11n a-mpdu support */
    ADF_NET_WCMD_PARAM_AMPDU_LIMIT,/**< a-mpdu length limit */
    ADF_NET_WCMD_PARAM_AMPDU_DENSITY,/**< a-mpdu density */
    ADF_NET_WCMD_PARAM_AMPDU_SUBFRAMES,/**< a-mpdu subframe limit */
    ADF_NET_WCMD_PARAM_AMSDU,/**< a-msdu support */
    ADF_NET_WCMD_PARAM_AMSDU_LIMIT,/**< a-msdu length limit */
    ADF_NET_WCMD_PARAM_COUNTRYCODE,/**< Get country code */
    ADF_NET_WCMD_PARAM_TX_CHAINMASK,/**< Tx chain mask */
    ADF_NET_WCMD_PARAM_RX_CHAINMASK,/**< Rx chain mask */
    ADF_NET_WCMD_PARAM_RTSCTS_RATECODE,/**< RTS Rate code */
    ADF_NET_WCMD_PARAM_HT_PROTECTION,/**< Protect traffic in HT mode */
    ADF_NET_WCMD_PARAM_RESET_ONCE,/**< Force a reset */
    ADF_NET_WCMD_PARAM_SETADDBAOPER,/**< Set ADDBA mode */
    ADF_NET_WCMD_PARAM_TX_CHAINMASK_LEGACY,/**< Tx chain mask */
    ADF_NET_WCMD_PARAM_11N_RATE,/**< Set ADDBA mode */
    ADF_NET_WCMD_PARAM_11N_RETRIES,/**< Tx chain mask for legacy clients */
    ADF_NET_WCMD_PARAM_WDS_AUTODETECT,/**< Autodetect/DelBa for WDS mode */
    ADF_NET_WCMD_PARAM_RB,/**< Switch in/out of RB */
    /**
     * RB Detection knobs.
     */ 
    ADF_NET_WCMD_PARAM_RB_DETECT,/**< Do RB detection */
    ADF_NET_WCMD_PARAM_RB_SKIP_THRESHOLD,/**< seqno-skip-by-1s to detect */
    ADF_NET_WCMD_PARAM_RB_TIMEOUT,/**< (in ms) to restore non-RB */
    ADF_NET_WCMD_PARAM_NO_HTIE,/**< Control HT IEs are sent out or parsed */
    ADF_NET_WCMD_PARAM_MAXSTA/**< Config max allowable staions for each VAP */
}adf_net_wcmd_param_id_t;

/**
 *  @brief APPIEBUF related definations
 */
typedef enum adf_net_wcmd_appie_frame{
    ADF_NET_WCMD_APPIE_FRAME_BEACON,
    ADF_NET_WCMD_APPIE_FRAME_PROBE_REQ,
    ADF_NET_WCMD_APPIE_FRAME_PROBE_RESP,
    ADF_NET_WCMD_APPIE_FRAME_ASSOC_REQ,
    ADF_NET_WCMD_APPIE_FRAME_ASSOC_RESP,
    ADF_NET_WCMD_APPIE_NUM_OF_FRAME
}adf_net_wcmd_appie_frame_t;
/**
 * @brief filter pointer info
 */
typedef enum adf_net_wcmd_filter_type{
    ADF_NET_WCMD_FILTER_TYPE_BEACON=0x1,
    ADF_NET_WCMD_FILTER_TYPE_PROBE_REQ=0x2,
    ADF_NET_WCMD_FILTER_TYPE_PROBE_RESP=0x4,
    ADF_NET_WCMD_FILTER_TYPE_ASSOC_REQ=0x8,
    ADF_NET_WCMD_FILTER_TYPE_ASSOC_RESP=0x10,
    ADF_NET_WCMD_FILTER_TYPE_AUTH=0x20,
    ADF_NET_WCMD_FILTER_TYPE_DEAUTH=0x40,
    ADF_NET_WCMD_FILTER_TYPE_DISASSOC=0x80,
    ADF_NET_WCMD_FILTER_TYPE_ALL=0xFF,
}adf_net_wcmd_filter_type_t;
/**
 * @brief mlme info pointer
 */
typedef enum adf_net_wcmd_mlme_op_type{
    ADF_NET_WCMD_MLME_ASSOC,
    ADF_NET_WCMD_MLME_DISASSOC,
    ADF_NET_WCMD_MLME_DEAUTH,
    ADF_NET_WCMD_MLME_AUTHORIZE,
    ADF_NET_WCMD_MLME_UNAUTHORIZE,
}adf_net_wcmd_mlme_op_type_t;

typedef enum adf_net_wcmd_wmmparams{
    ADF_NET_WCMD_WMMPARAMS_CWMIN = 1,
    ADF_NET_WCMD_WMMPARAMS_CWMAX,
    ADF_NET_WCMD_WMMPARAMS_AIFS,
    ADF_NET_WCMD_WMMPARAMS_TXOPLIMIT,
    ADF_NET_WCMD_WMMPARAMS_ACM,
    ADF_NET_WCMD_WMMPARAMS_NOACKPOLICY, 
}adf_net_wcmd_wmmparams_t;

/**
 * @brief Power Management Flags
 */
typedef enum adf_net_wcmd_pmflags{
    ADF_NET_WCMD_POWER_ON  = 0x0,
    ADF_NET_WCMD_POWER_MIN = 0x1,/**< Min */
    ADF_NET_WCMD_POWER_MAX = 0x2,/**< Max */
    ADF_NET_WCMD_POWER_REL = 0x4,/**< Not in seconds/ms/us */
    ADF_NET_WCMD_POWER_MOD = 0xF,/**< Modify a parameter */
    ADF_NET_WCMD_POWER_UCAST_R = 0x100,/**< Ucast messages */
    ADF_NET_WCMD_POWER_MCAST_R = 0x200,/**< Mcast messages */
    ADF_NET_WCMD_POWER_ALL_R = 0x300,/**< All messages though PM */
    ADF_NET_WCMD_POWER_FORCE_S = 0x400,/**< Force PM to unicast */
    ADF_NET_WCMD_POWER_REPEATER = 0x800,/**< Bcast messages in PM*/
    ADF_NET_WCMD_POWER_MODE = 0xF00,/**< Power Management mode */
    ADF_NET_WCMD_POWER_PERIOD = 0x1000,/**< Period/Duration of */
    ADF_NET_WCMD_POWER_TIMEOUT = 0x2000,/**< Timeout (to go asleep) */
    ADF_NET_WCMD_POWER_TYPE = 0xF000/**< Type of parameter */
}adf_net_wcmd_pmflags_t;
/**
 * @brief Tx Power flags
 */
typedef enum adf_net_wcmd_txpow_flags{
    ADF_NET_WCMD_TXPOW_DBM = 0,/**< dBm */
    ADF_NET_WCMD_TXPOW_MWATT = 0x1,/**< mW */
    ADF_NET_WCMD_TXPOW_RELATIVE = 0x2,/**< Arbitrary units */
    ADF_NET_WCMD_TXPOW_TYPE = 0xFF,/**< Type of value */    
    ADF_NET_WCMD_TXPOW_RANGE = 0x1000/**< Range (min - max) */ 
}adf_net_wcmd_txpow_flags_t;
/**
 * @brief Retry flags
 */
typedef enum adf_net_wcmd_retry_flags{
    ADF_NET_WCMD_RETRY_ON = 0x0,
    ADF_NET_WCMD_RETRY_MIN = 0x1,/**< Value is a minimum */
    ADF_NET_WCMD_RETRY_MAX = 0x2,/**< Maximum */
    ADF_NET_WCMD_RETRY_RELATIVE = 0x4,/**< Not in seconds/ms/us */
    ADF_NET_WCMD_RETRY_SHORT = 0x10,/**< Short packets  */
    ADF_NET_WCMD_RETRY_LONG = 0x20,/**< Long packets */ 
    ADF_NET_WCMD_RETRY_MODIFIER = 0xFF,/**< Modify a parameter */
    ADF_NET_WCMD_RETRY_LIMIT = 0x1000,/**< Max retries*/
    ADF_NET_WCMD_RETRY_LIFETIME = 0x2000,/**< Max retries us*/
    ADF_NET_WCMD_RETRY_TYPE = 0xF000,/**< Parameter type */
}adf_net_wcmd_retry_flags_t;
/**
 * @brief choose the CWM struct type
 */
typedef enum adf_net_wcmd_cwmtype{
    ADF_NET_WCMD_CWMTYPE_INFO=139,/**< driver requirement */
    ADF_NET_WCMD_CWMTYPE_DBG/**< driver requirement */
}adf_net_wcmd_cwmtype_t;
/**
 * @brief CWM Debug mode commands
 */
typedef enum adf_net_wcmd_cwm_cmd{
    ADF_NET_WCMD_CWM_CMD_EVENT,/**< Send Event */
    ADF_NET_WCMD_CWM_CMD_CTL,/**< Ctrl channel busy */
    ADF_NET_WCMD_CWM_CMD_EXT,/**< Ext chan busy */
    ADF_NET_WCMD_CWM_CMD_VCTL,/**< virt ctrl chan busy*/
    ADF_NET_DBGCWM_CMD_VEXT/**< virt extension channel busy*/
}adf_net_wcmd_cwm_cmd_t;

/**
 * @brief CWM EVENTS
 */
typedef enum adf_net_wcmd_cwm_event{
    ADF_NET_WCMD_CWMEVENT_TXTIMEOUT,  /**< tx timeout interrupt */
    ADF_NET_WCMD_CWMEVENT_EXTCHCLEAR, /**< ext channel sensing clear */
    ADF_NET_WCMD_CWMEVENT_EXTCHBUSY,  /**< ext channel sensing busy */
    ADF_NET_WCMD_CWMEVENT_EXTCHSTOP,  /**< ext channel sensing stop */
    ADF_NET_WCMD_CWMEVENT_EXTCHRESUME,/**< ext channel sensing resume */
    ADF_NET_WCMD_CWMEVENT_DESTCW20,   /**< dest channel width changed to 20 */
    ADF_NET_WCMD_CWMEVENT_DESTCW40,   /**< dest channel width changed to 40 */
    ADF_NET_WCMD_CWMEVENT_MAX 
} adf_net_wcmd_cwm_event_t;

/**
 * @brief eth tool info
 */
typedef enum adf_net_wcmd_ethtool_cmd{
    ADF_NET_WCMD_ETHTOOL_GSET=0x1,/**< Get settings. */
    ADF_NET_WCMD_ETHTOOL_SSET,/**< Set settings. */
    ADF_NET_WCMD_ETHTOOL_GDRVINFO,/**< Get driver info. */
    ADF_NET_WCMD_ETHTOOL_GREGS,/**< Get NIC registers. */
    ADF_NET_WCMD_ETHTOOL_GWOL,/**< Wake-on-lan options. */
    ADF_NET_WCMD_ETHTOOL_SWOL,/**< Set wake-on-lan options. */
    ADF_NET_WCMD_ETHTOOL_GMSGLVL,/**< Get driver message level */
    ADF_NET_WCMD_ETHTOOL_SMSGLVL,/**< Set driver msg level */
    ADF_NET_WCMD_ETHTOOL_NWAY_RST,/**< Restart autonegotiation. */ 
    ADF_NET_WCMD_ETHTOOL_GEEPROM,/**< Get EEPROM data */
    ADF_NET_WCMD_ETHTOOL_SEEPROM,/** < Set EEPROM data. */
    ADF_NET_WCMD_ETHTOOL_GCOALESCE,/** < Get coalesce config */
    ADF_NET_WCMD_ETHTOOL_SCOALESCE,/** < Set coalesce config. */
    ADF_NET_WCMD_ETHTOOL_GRINGPARAM,/** < Get ring parameters */
    ADF_NET_WCMD_ETHTOOL_SRINGPARAM,/** < Set ring parameters. */
    ADF_NET_WCMD_ETHTOOL_GPAUSEPARAM,/** < Get pause parameters */
    ADF_NET_WCMD_ETHTOOL_SPAUSEPARAM,/** < Set pause parameters. */
    ADF_NET_WCMD_ETHTOOL_GRXCSUM,/** < Get RX hw csum enable */
    ADF_NET_WCMD_ETHTOOL_SRXCSUM,/** < Set RX hw csum enable */
    ADF_NET_WCMD_ETHTOOL_GTXCSUM,/** < Get TX hw csum enable */
    ADF_NET_WCMD_ETHTOOL_STXCSUM,/** < Set TX hw csum enable */
    ADF_NET_WCMD_ETHTOOL_GSG,/** < Get scatter-gather enable */
    ADF_NET_WCMD_ETHTOOL_SSG,/** < Set scatter-gather enable */
    ADF_NET_WCMD_ETHTOOL_TEST,/** < execute NIC self-test. */
    ADF_NET_WCMD_ETHTOOL_GSTRINGS,/** < get specified string set */
    ADF_NET_WCMD_ETHTOOL_PHYS_ID,/** < identify the NIC */
    ADF_NET_WCMD_ETHTOOL_GSTATS,/** < get NIC-specific statistics */
    ADF_NET_WCMD_ETHTOOL_GTSO,/** < Get TSO enable (ethtool_value) */
    ADF_NET_WCMD_ETHTOOL_STSO,/** < Set TSO enable (ethtool_value) */
    ADF_NET_WCMD_ETHTOOL_GPERMADDR,/** < Get permanent hardware address */
    ADF_NET_WCMD_ETHTOOL_GUFO,/** < Get UFO enable */
    ADF_NET_WCMD_ETHTOOL_SUFO,/** < Set UFO enable */
    ADF_NET_WCMD_ETHTOOL_GGSO,/** < Get GSO enable */
    ADF_NET_WCMD_ETHTOOL_SGSO,/** < Set GSO enable */
}adf_net_wcmd_ethtool_cmd_t;

/**
 * ***************************Structures***********************
 */
/**
 * @brief Information Element
 */
typedef struct adf_net_ie_info{
    a_uint16_t         len;
    a_uint8_t          data[ADF_NET_WCMD_IE_MAXLEN];
}adf_net_ie_info_t;
/**
 * @brief WCMD info
 */
typedef struct adf_net_wcmd_vapname{
    a_uint32_t     len;
    a_uint8_t      name[ADF_NET_WCMD_NAME_SIZE];
}adf_net_wcmd_vapname_t;
/**
 * @brief nickname pointer info
 */
typedef struct adf_net_wcmd_nickname{
    a_uint16_t      len;
    a_uint8_t       name[ADF_NET_WCMD_NICK_NAME];
}adf_net_wcmd_nickname_t;
/**
 * @brief missed frame info
 */
typedef struct  adf_net_wcmd_miss{
    a_uint32_t      beacon;/**< Others cases */
}adf_net_wcmd_miss_t;
/**
 * @brief  discarded frame info
 */
typedef struct  adf_net_wcmd_discard{
    a_uint32_t      nwid;/**< Rx : Wrong nwid/essid */
    a_uint32_t      code; /**< Rx : Unable to code/decode (WEP) */
    a_uint32_t      fragment;/**< Rx : Can't perform MAC reassembly */
    a_uint32_t      retries;/**< Tx : Max MAC retries num reached */
    a_uint32_t      misc;/**< Others cases */
}adf_net_wcmd_discard_t;
/**
 * @brief Link quality info
 */
typedef struct  adf_net_wcmd_linkqty{
    a_uint8_t       qual;/*link quality(retries, SNR, missed beacons)*/ 
    a_uint8_t       level;/*Signal level (dBm) */
    a_uint8_t       noise;/*Noise level (dBm) */
    a_uint8_t       updated;/*Update flag*/
}adf_net_wcmd_linkqty_t;
/**
 * @brief frequency info
 */
typedef struct  adf_net_wcmd_freq{
    a_int32_t       m;/*Mantissa */
    a_int16_t       e;/*Exponent */
    a_uint8_t       i;/*List index (when in range struct) */
    a_uint8_t       flags;/*Flags (fixed/auto) */

}adf_net_wcmd_freq_t;
/**
 * @brief VAP parameter range info
 */
typedef struct adf_net_wcmd_vapparam_range{
    
    /**
     * @brief Informative stuff (to choose between different
     * interface) In theory this value should be the maximum
     * benchmarked TCP/IP throughput, because with most of these
     * devices the bit rate is meaningless (overhead an co) to
     * estimate how fast the connection will go and pick the fastest
     * one. I suggest people to play with Netperf or any
     * benchmark...
     */
    a_uint32_t           throughput;/**< To give an idea... */
    
    /** @brief NWID (or domain id) */
    a_uint32_t           min_nwid;/**< Min NWID to set */
    a_uint32_t           max_nwid;/**< Max NWID to set */

    /**
     * @brief Old Frequency (backward compatibility - moved lower )
     */
    a_uint16_t           old_num_channels;
    a_uint8_t            old_num_frequency;

    /**@brief Wireless event capability bitmasks */
    a_uint32_t          event_capa[ADF_NET_WCMD_EVENT_CAP];

    /**@brief Signal level threshold range */
    a_int32_t           sensitivity;

    /**
     * @brief Quality of link & SNR stuff Quality range (link,
     * level, noise) If the quality is absolute, it will be in the
     * range [0
     * - max_qual], if the quality is dBm, it will be in the range
     * [max_qual - 0]. Don't forget that we use 8 bit arithmetics...
     */
    adf_net_wcmd_linkqty_t       max_qual;/**< Link Quality*/

    /**
     * @brief This should contain the average/typical values of the
     * quality indicator. This should be the threshold between a
     * "good" and a "bad" link (example : monitor going from green
     * to orange). Currently, user space apps like quality monitors
     * don't have any way to calibrate the measurement. With this,
     * they can split the range between 0 and max_qual in different
     * quality level (using a geometric subdivision centered on the
     * average). I expect that people doing the user space apps will
     * feedback us on which value we need to put in each
     * driver... 
     */
    adf_net_wcmd_linkqty_t       avg_qual; 

    /**@brief Rates */
    a_uint8_t           num_bitrates; /**< Number of entries in the list */
    a_int32_t           bitrate[ADF_NET_WCMD_MAX_BITRATES]; /**< in bps */

    /**@brief RTS threshold */
    a_int32_t           min_rts; /**< Minimal RTS threshold */
    a_int32_t           max_rts; /**< Maximal RTS threshold */

    /**@brief Frag threshold */
    a_int32_t           min_frag;/**< Minimal frag threshold */
    a_int32_t           max_frag;/**< Maximal frag threshold */

    /**@brief Power Management duration & timeout */
    a_int32_t           min_pmp;/**< Minimal PM period */
    a_int32_t           max_pmp;/**< Maximal PM period */
    a_int32_t           min_pmt;/**< Minimal PM timeout */
    a_int32_t           max_pmt;/**< Maximal PM timeout */
    a_uint16_t          pmp_flags;/**< decode max/min PM period */
    a_uint16_t          pmt_flags;/**< decode max/min PM timeout */
    a_uint16_t          pm_capa;/**< PM options supported */

    /**@brief Encoder stuff, Different token sizes */
    a_uint16_t          enc_sz[ADF_NET_WCMD_MAX_ENC_SZ];
    a_uint8_t           num_enc_sz; /**< Number of entry in the list */
    a_uint8_t           max_enc_tk;/**< Max number of tokens */
    /**@brief For drivers that need a "login/passwd" form */
    a_uint8_t           enc_login_idx;/**< token index for login token */

    /**@brief Transmit power */
    a_uint16_t          txpower_capa;/**< options supported */
    a_uint8_t           num_txpower;/**< Number of entries in the list */
    a_int32_t           txpower[ADF_NET_WCMD_MAX_TXPOWER];/**< in bps */
    
    /**@brief Wireless Extension version info */
    a_uint8_t           we_version_compiled;/**< Must be WIRELESS_EXT */
    a_uint8_t           we_version_source;/**< Last update of source */
    
    /**@brief Retry limits and lifetime */
    a_uint16_t          retry_capa;/**< retry options supported */
    a_uint16_t          retry_flags;/**< decode max/min retry limit*/
    a_uint16_t          r_time_flags;/**< Decode max/min retry life */
    a_int32_t           min_retry;/**< Min retries */
    a_int32_t           max_retry;/**< Max retries */
    a_int32_t           min_r_time;/**< Min retry lifetime */
    a_int32_t           max_r_time;/**< Max retry lifetime */
    
    /**@brief Frequency */
    a_uint16_t          num_channels;/**< Num channels [0 - (num - 1)] */
    a_uint8_t           num_frequency;/**< Num entries*/
    /**
     * Note : this frequency list doesn't need to fit channel
     * numbers, because each entry contain its channel index
     */
    adf_net_wcmd_freq_t    freq[ADF_NET_WCMD_MAX_FREQ];
    
    a_uint32_t          enc_capa; /**< IW_ENC_CAPA_* bit field */
}adf_net_wcmd_vapparam_range_t;
/**
 * @brief key info
 */
typedef struct adf_net_wcmd_keyinfo{
    a_uint8_t   ik_type; /**< key/cipher type */
    a_uint8_t   ik_pad;
    a_uint16_t  ik_keyix;/**< key index */
    a_uint8_t   ik_keylen;/**< key length in bytes */
    a_uint8_t   ik_flags;
    a_uint8_t   ik_macaddr[ADF_NET_WCMD_ADDR_LEN];
    a_uint64_t  ik_keyrsc;/**< key receive sequence counter */
    a_uint64_t  ik_keytsc;/**< key transmit sequence counter */
    a_uint8_t   ik_keydata[ADF_NET_WCMD_KEYDATA_SZ];
}adf_net_wcmd_keyinfo_t;

/**
 * @brief bssid pointer info
 */
typedef struct adf_net_wcmd_bssid{
    a_uint8_t      bssid[ADF_NET_WCMD_ADDR_LEN];
}adf_net_wcmd_bssid_t;

/**
 * @brief essid structure info
 */
typedef struct  adf_net_wcmd_ssid{
    a_uint8_t     byte[ADF_NET_WCMD_MAX_SSID];
    a_uint16_t    len;/**< number of fields or size in bytes */
    a_uint16_t    flags;/**< Optional  */
} adf_net_wcmd_ssid_t;

typedef struct adf_net_wcmd_param{
    adf_net_wcmd_param_id_t   param_id;
    a_uint32_t                value;
}adf_net_wcmd_param_t;

/**
 * @brief optional IE pointer info
 */
typedef adf_net_ie_info_t  adf_net_wcmd_optie_t;

/**
 * @brief status of VAP interface 
 */ 
typedef struct adf_net_wcmd_vapstats{
    a_uint8_t                  status;/**< Status*/
    adf_net_wcmd_linkqty_t     qual;/**< Quality of the link*/
    adf_net_wcmd_discard_t     discard;/**< Packet discarded counts */ 
    adf_net_wcmd_miss_t        miss;/**< Packet missed counts */
} adf_net_wcmd_vapstats_t;

/**
 * @brief appie pointer info
 */
typedef struct adf_net_wcmd_appie{
    adf_net_wcmd_appie_frame_t     frmtype;
    a_uint32_t                     len;
    a_uint8_t                      data[ADF_NET_WCMD_IE_MAXLEN];
}adf_net_wcmd_appie_t;
/**
 * @brief send ADDBA info pointer
 */
typedef struct adf_net_wcmd_addba{
    a_uint16_t  aid;
    a_uint32_t  tid;
    a_uint32_t  arg1;
}adf_net_wcmd_addba_t;
/**
 * @brief ADDBA status pointer info
 */
typedef struct adf_net_wcmd_addba_status{
    a_uint16_t  aid;
    a_uint32_t  tid;
    a_uint16_t  status;
}adf_net_wcmd_addba_status_t;
/**
 * @brief ADDBA response pointer info
 */
typedef struct adf_net_wcmd_addba_resp{
    a_uint16_t  aid;
    a_uint32_t  tid;
    a_uint32_t  arg1;
}adf_net_wcmd_addba_resp_t;

/**
 * @brief send DELBA info pointer
 */
typedef struct adf_net_wcmd_delba{
    a_uint16_t  aid;
    a_uint32_t  tid;
    a_uint32_t  arg1;
    a_uint32_t  arg2;
}adf_net_wcmd_delba_t;

/**
 * @brief MLME
 */
typedef struct adf_net_wcmd_mlme{
    adf_net_wcmd_mlme_op_type_t  op;/**< operation to perform */ 
    a_uint8_t                    reason;/**< 802.11 reason code */
    //a_uint8_t                         macaddr[ADF_NET_WCMD_ADDR_LEN];
    adf_net_ethaddr_t            mac;
}adf_net_wcmd_mlme_t;

/**
 * @brief Set the active channel list.  Note this list is
 * intersected with the available channel list in
 * calculating the set of channels actually used in
 * scanning.
 */
typedef struct adf_net_wcmd_chanlist{
    a_uint8_t   chanlist[ADF_NET_WCMD_CHAN_BYTES];
//    u_int16_t   len;
}adf_net_wcmd_chanlist_t;

/**
 * @brief Channels are specified by frequency and attributes.
 */
typedef struct adf_net_wcmd_chan{
    a_uint16_t  freq;/**< setting in Mhz */
    a_uint32_t  flags;/**< see below */
    a_uint8_t   ieee;/**< IEEE channel number */
    a_int8_t    maxregpower;/**< maximum regulatory tx power in dBm */
    a_int8_t    maxpower;/**< maximum tx power in dBm */
    a_int8_t    minpower;/**< minimum tx power in dBm */
    a_uint8_t   regclassid;/**< regulatory class id */
} adf_net_wcmd_chan_t;
/**
 * @brief channel info pointer
 */
typedef struct adf_net_wcmd_chaninfo{
    a_uint32_t            nchans;
    adf_net_wcmd_chan_t   chans;
}adf_net_wcmd_chaninfo_t;

/**
 * @brief wmm-param info 
 */ 
typedef struct adf_net_wcmd_wmmparaminfo{
    adf_net_wcmd_wmmparams_t  cmd;
    a_uint32_t                ac;
    a_uint32_t                bss;
    a_uint32_t                value;
}adf_net_wcmd_wmmparaminfo_t;
/**
 * @brief wpa ie pointer info
 */
typedef struct adf_net_wcmd_wpaie{
    adf_net_ethaddr_t  mac;
    adf_net_ie_info_t  ie;
}adf_net_wcmd_wpaie_t;


/**
 * @brief wsc ie pointer info
 */
typedef struct adf_net_wcmd_wscie{
    adf_net_ethaddr_t  mac;
    adf_net_ie_info_t   ie;
}adf_net_wcmd_wscie_t;
/**
 * @brief rts threshold set/get info
 */
typedef struct adf_net_wcmd_rts_th{
    a_uint16_t          threshold;
    a_uint16_t          disabled;
    a_uint16_t          fixed;
}adf_net_wcmd_rts_th_t;
/**
 * @brief fragment threshold set/get info
 */
typedef struct adf_net_wcmd_frag_th{
    a_uint16_t     threshold;
    a_uint16_t     disabled;
    a_uint16_t     fixed;
}adf_net_wcmd_frag_th_t;
/**
 * @brief ic_caps set/get/enable/disable info
 */
typedef a_uint32_t     adf_net_wcmd_ic_caps_t;
/**
 * @brief iv_opmode set/get/enable/disable info
 */
typedef a_uint32_t     adf_net_wcmd_iv_opmode_t;
/**
 * @brief retries set/get/enable/disable info
 */
typedef struct adf_net_wcmd_retries{
  a_int32_t          value;/**< The value of the parameter itself */
  a_uint8_t          disabled;/**< Disable the feature */
  a_uint16_t         flags;/**< Various specifc flags (if any) */
}adf_net_wcmd_retries_t;

/**
 * @brief power set/get info
 */
typedef struct adf_net_wcmd_power{
  a_int32_t               value;/**< The value of the parameter itself */
  a_uint8_t               disabled;/**< Disable the feature */
  adf_net_wcmd_pmflags_t  flags;/**< Various specifc flags (if any) */
  a_int32_t               fixed;/**< fixed */
}adf_net_wcmd_power_t;

/**
 * @brief txpower set/get/enable/disable info
 */
typedef struct adf_net_wcmd_txpower{
    a_uint32_t                     txpower;
    a_uint8_t                      fixed;
    a_uint8_t                      disabled;
    adf_net_wcmd_txpow_flags_t     flags;
}adf_net_wcmd_txpower_t;

/**
 * @brief tx-power-limit info 
 */ 
typedef a_uint32_t  adf_net_wcmd_txpowlimit_t;


/**
 * @brief Scan result data returned
 */
typedef struct adf_net_wcmd_scan_result{
    a_uint16_t  isr_len;        /**< length (mult of 4) */
    a_uint16_t  isr_freq;       /**< MHz */
    a_uint32_t  isr_flags;     /**< channel flags */
    a_uint8_t   isr_noise;
    a_uint8_t   isr_rssi;
    a_uint8_t   isr_intval;     /**< beacon interval */
    a_uint16_t  isr_capinfo;    /**< capabilities */
    a_uint8_t   isr_erp;        /**< ERP element */
    a_uint8_t   isr_bssid[ADF_NET_WCMD_ADDR_LEN];
    a_uint8_t   isr_nrates;
    a_uint8_t   isr_rates[ADF_NET_WCMD_RATE_MAXSIZE];
    a_uint8_t   isr_ssid_len;   /**< SSID length */
    a_uint8_t   isr_ie_len;     /**< IE length */
    a_uint8_t   isr_pad[5];
    /* variable length SSID followed by IE data */
} adf_net_wcmd_scan_result_t;

/**
 * @brief scan request info
 */
typedef struct adf_net_wcmd_scan{
    adf_net_wcmd_scan_result_t  result[ADF_NET_WCMD_MAX_AP];
    a_uint32_t                  len;/*Valid entries*/
}adf_net_wcmd_scan_t;
/**
 * @brief waplist request info
 */
typedef struct adf_net_wcmd_vaplist{
    a_uint8_t          list[ADF_NET_WCMD_MAX_AP];
    a_uint32_t         len;   
}adf_net_wcmd_vaplist_t;
/**
 * @brief list of stations
 */
typedef struct adf_net_wcmd_stainfo{
    a_uint8_t          list[ADF_NET_WCMD_MAX_AP];
    a_uint32_t         len;
} adf_net_wcmd_stainfo_t;
/**
 * @brief ath caps info
 */
typedef struct adf_net_wcmd_devcap{ 
    a_int32_t   cap; 
    a_int32_t   setting; 
}adf_net_wcmd_devcap_t; 

/**
 * @brief station stats
 */
typedef struct adf_net_wcmd_stastats{
    adf_net_ethaddr_t  mac;/**< MAC of the station*/
    struct ns_data{
        a_uint32_t  ns_rx_data;/**< rx data frames */
        a_uint32_t  ns_rx_mgmt;/**< rx management frames */
        a_uint32_t  ns_rx_ctrl;/**< rx control frames */
        a_uint32_t  ns_rx_ucast;/**< rx unicast frames */
        a_uint32_t  ns_rx_mcast;/**< rx multi/broadcast frames */
        a_uint64_t  ns_rx_bytes;/**< rx data count (bytes) */
        a_uint64_t  ns_rx_beacons;/**< rx beacon frames */
        a_uint32_t  ns_rx_proberesp;/**< rx probe response frames */
        
        a_uint32_t  ns_rx_dup;/**< rx discard 'cuz dup */
        a_uint32_t  ns_rx_noprivacy;/**< rx w/ wep but privacy off */
        a_uint32_t  ns_rx_wepfail;/**< rx wep processing failed */
        a_uint32_t  ns_rx_demicfail;/**< rx demic failed */
        a_uint32_t  ns_rx_decap;/**< rx decapsulation failed */
        a_uint32_t  ns_rx_defrag;/**< rx defragmentation failed */
        a_uint32_t  ns_rx_disassoc;/**< rx disassociation */
        a_uint32_t  ns_rx_deauth;/**< rx deauthentication */
        a_uint32_t  ns_rx_action;/**< rx action */
        a_uint32_t  ns_rx_decryptcrc;/**< rx decrypt failed on crc */
        a_uint32_t  ns_rx_unauth;/**< rx on unauthorized port */
        a_uint32_t  ns_rx_unencrypted;/**< rx unecrypted w/ privacy */
    
        a_uint32_t  ns_tx_data;/**< tx data frames */
        a_uint32_t  ns_tx_mgmt;/**< tx management frames */
        a_uint32_t  ns_tx_ucast;/**< tx unicast frames */
        a_uint32_t  ns_tx_mcast;/**< tx multi/broadcast frames */
        a_uint64_t  ns_tx_bytes;/**< tx data count (bytes) */
        a_uint32_t  ns_tx_probereq;/**< tx probe request frames */
        a_uint32_t  ns_tx_uapsd;/**< tx on uapsd queue */
        
        a_uint32_t  ns_tx_novlantag;/**< tx discard 'cuz no tag */
        a_uint32_t  ns_tx_vlanmismatch;/**< tx discard 'cuz bad tag */
    
        a_uint32_t  ns_tx_eosplost;/**< uapsd EOSP retried out */
    
        a_uint32_t  ns_ps_discard;/**< ps discard 'cuz of age */
    
        a_uint32_t  ns_uapsd_triggers;/**< uapsd triggers */
    
        /* MIB-related state */
        a_uint32_t  ns_tx_assoc;/**< [re]associations */
        a_uint32_t  ns_tx_assoc_fail;/**< [re]association failures */
        a_uint32_t  ns_tx_auth;/**< [re]authentications */
        a_uint32_t  ns_tx_auth_fail;/**< [re]authentication failures*/
        a_uint32_t  ns_tx_deauth;/**< deauthentications */
        a_uint32_t  ns_tx_deauth_code;/**< last deauth reason */
        a_uint32_t  ns_tx_disassoc;/**< disassociations */
        a_uint32_t  ns_tx_disassoc_code;/**< last disassociation reason */
        a_uint32_t  ns_psq_drops;/**< power save queue drops */
    }data;
} adf_net_wcmd_stastats_t;
/**
 * @brief 11n tx/rx stats
 */
typedef struct adf_net_wcmd_11n_stats {
    a_uint32_t   tx_pkts;/**< total tx data packets */
    a_uint32_t   tx_checks;/**< tx drops in wrong state */
    a_uint32_t   tx_drops;/**< tx drops due to qdepth limit */
    a_uint32_t   tx_minqdepth;/**< tx when h/w queue depth is low */
    a_uint32_t   tx_queue;/**< tx pkts when h/w queue is busy */
    a_uint32_t   tx_comps;/**< tx completions */
    a_uint32_t   tx_stopfiltered;/**< tx pkts filtered for requeueing */
    a_uint32_t   tx_qnull;/**< txq empty occurences */
    a_uint32_t   tx_noskbs;/**< tx no skbs for encapsulations */
    a_uint32_t   tx_nobufs;/**< tx no descriptors */
    a_uint32_t   tx_badsetups;/**< tx key setup failures */
    a_uint32_t   tx_normnobufs;/**< tx no desc for legacy packets */
    a_uint32_t   tx_schednone;/**< tx schedule pkt queue empty */
    a_uint32_t   tx_bars;/**< tx bars sent */
    a_uint32_t   txbar_xretry;/**< tx bars excessively retried */
    a_uint32_t   txbar_compretries;/**< tx bars retried */
    a_uint32_t   txbar_errlast;/**< tx bars last frame failed */
    a_uint32_t   tx_compunaggr;/**< tx unaggregated frame completions */
    a_uint32_t   txunaggr_xretry;/**< tx unaggregated excessive retries */
    a_uint32_t   tx_compaggr;/**< tx aggregated completions */
    a_uint32_t   tx_bawadv;/**< tx block ack window advanced */
    a_uint32_t   tx_bawretries;/**< tx block ack window retries */
    a_uint32_t   tx_bawnorm;/**< tx block ack window additions */
    a_uint32_t   tx_bawupdates;/**< tx block ack window updates */
    a_uint32_t   tx_bawupdtadv;/**< tx block ack window advances */
    a_uint32_t   tx_retries;/**< tx retries of sub frames */
    a_uint32_t   tx_xretries;/**< tx excessive retries of aggregates */
    a_uint32_t   txaggr_noskbs;/**< tx no skbs for aggr encapsualtion */
    a_uint32_t   txaggr_nobufs;/**< tx no desc for aggr */
    a_uint32_t   txaggr_badkeys;/**< tx enc key setup failures */
    a_uint32_t   txaggr_schedwindow;/**< tx no frame scheduled: baw limited */
    a_uint32_t   txaggr_single;/**< tx frames not aggregated */
    a_uint32_t   txaggr_compgood;/**< tx aggr good completions */
    a_uint32_t   txaggr_compxretry;/**< tx aggr excessive retries */
    a_uint32_t   txaggr_compretries;/**< tx aggr unacked subframes */
    a_uint32_t   txunaggr_compretries;/**< tx non-aggr unacked subframes */
    a_uint32_t   txaggr_prepends;/**< tx aggr old frames requeued */
    a_uint32_t   txaggr_filtered;/**< filtered aggr packet */
    a_uint32_t   txaggr_fifo;/**< fifo underrun of aggregate */
    a_uint32_t   txaggr_xtxop;/**< txop exceeded for an aggregate */
    a_uint32_t   txaggr_desc_cfgerr;/**< aggregate descriptor config error */
    a_uint32_t   txaggr_data_urun;/**< data underrun for an aggregate */
    a_uint32_t   txaggr_delim_urun;/**< delimiter underrun for an aggregate */
    a_uint32_t   txaggr_errlast;/**< tx aggr: last sub-frame failed */
    a_uint32_t   txunaggr_errlast;/**< tx non-aggr: last frame failed */
    a_uint32_t   txaggr_longretries;/**< tx aggr h/w long retries */
    a_uint32_t   txaggr_shortretries;/**< tx aggr h/w short retries */
    a_uint32_t   txaggr_timer_exp;/**< tx aggr : tx timer expired */
    a_uint32_t   txaggr_babug;/**< tx aggr : BA bug */
    a_uint32_t   rx_pkts;/**< rx pkts */
    a_uint32_t   rx_aggr;/**< rx aggregated packets */
    a_uint32_t   rx_aggrbadver;/**< rx pkts with bad version */
    a_uint32_t   rx_bars;/**< rx bars */
    a_uint32_t   rx_nonqos;/**< rx non qos-data frames */
    a_uint32_t   rx_seqreset;/**< rx sequence resets */
    a_uint32_t   rx_oldseq;/**< rx old packets */
    a_uint32_t   rx_bareset;/**< rx block ack window reset */
    a_uint32_t   rx_baresetpkts;/**< rx pts indicated due to baw resets */
    a_uint32_t   rx_dup;/**< rx duplicate pkts */
    a_uint32_t   rx_baadvance;/**< rx block ack window advanced */
    a_uint32_t   rx_recvcomp;/**< rx pkt completions */
    a_uint32_t   rx_bardiscard;/**< rx bar discarded */
    a_uint32_t   rx_barcomps;/**< rx pkts unblocked on bar reception */
    a_uint32_t   rx_barrecvs;/**< rx pkt completions on bar reception */
    a_uint32_t   rx_skipped;/**< rx pkt sequences skipped on timeout */
    a_uint32_t   rx_comp_to;/**< rx indications due to timeout */
    a_uint32_t   wd_tx_active;/**< watchdog: tx is active */
    a_uint32_t   wd_tx_inactive;/**< watchdog: tx is not active */
    a_uint32_t   wd_tx_hung;/**< watchdog: tx is hung */
    a_uint32_t   wd_spurious;/**< watchdog: spurious tx hang */
    a_uint32_t   tx_requeue;/**< filter & requeue on 20/40 transitions */
    a_uint32_t   tx_drain_txq;/**< draining tx queue on error */
    a_uint32_t   tx_drain_tid;/**< draining tid buf queue on error */
    a_uint32_t   tx_drain_bufs;/**< buffers drained from pending tid queue */
    a_uint32_t   tx_tidpaused;/**< pausing tx on tid */
    a_uint32_t   tx_tidresumed;/**< resuming tx on tid */
    a_uint32_t   tx_unaggr_filtered;/**< unaggregated tx pkts filtered */
    a_uint32_t   tx_aggr_filtered;/**< aggregated tx pkts filtered */
    a_uint32_t   tx_filtered;/**< total sub-frames filtered */
    a_uint32_t   rx_rb_on;/**< total rb on-s */
    a_uint32_t   rx_rb_off;/**< total rb off-s */
} adf_net_wcmd_11n_stats_t;


/**
 * @brief ampdu info 
 */ 
typedef struct adf_net_wcmd_ampdu_trc {
    a_uint32_t   tr_head;
    a_uint32_t   tr_tail;
    struct trc_entry{
        a_uint16_t   tre_seqst;/**< starting sequence of aggr */
        a_uint16_t   tre_baseqst;/**< starting sequence of ba */
        a_uint32_t   tre_npkts;/**< packets in aggregate */
        a_uint32_t   tre_aggrlen;/**< aggregation length */
        a_uint32_t   tre_bamap0;/**< block ack bitmap word 0 */
        a_uint32_t   tre_bamap1;/**< block ack bitmap word 1 */
    }tr_ents[ADF_NET_WCMD_NUM_TR_ENTS];
} adf_net_wcmd_ampdu_trc_t;

/**
 * @brief phy stats info 
 */ 
typedef struct adf_net_wcmd_phystats{
    a_uint32_t   ast_watchdog;/**< device reset by watchdog */
    a_uint32_t   ast_hardware;/**< fatal hardware error interrupts */
    a_uint32_t   ast_bmiss;/**< beacon miss interrupts */
    a_uint32_t   ast_rxorn;/**< rx overrun interrupts */
    a_uint32_t   ast_rxeol;/**< rx eol interrupts */
    a_uint32_t   ast_txurn;/**< tx underrun interrupts */
    a_uint32_t   ast_txto;/**< tx timeout interrupts */
    a_uint32_t   ast_cst;/**< carrier sense timeout interrupts */
    a_uint32_t   ast_mib;/**< mib interrupts */
    a_uint32_t   ast_tx_packets;/**< packet sent on the interface */
    a_uint32_t   ast_tx_mgmt;/**< management frames transmitted */
    a_uint32_t   ast_tx_discard;/**< frames discarded prior to assoc */
    a_uint32_t   ast_tx_invalid;/**< frames discarded 'cuz device gone */
    a_uint32_t   ast_tx_qstop;/**< tx queue stopped 'cuz full */
    a_uint32_t   ast_tx_encap;/**< tx encapsulation failed */
    a_uint32_t   ast_tx_nonode;/**< no node*/
    a_uint32_t   ast_tx_nobuf;/**< no buf */
    a_uint32_t   ast_tx_nobufmgt;/**< no buffer (mgmt)*/
    a_uint32_t   ast_tx_xretries;/**< too many retries */
    a_uint32_t   ast_tx_fifoerr;/**< FIFO underrun */
    a_uint32_t   ast_tx_filtered;/**< xmit filtered */
    a_uint32_t   ast_tx_timer_exp;/**< tx timer expired */
    a_uint32_t   ast_tx_shortretry;/**< on-chip retries (short) */
    a_uint32_t   ast_tx_longretry;/**< tx on-chip retries (long) */
    a_uint32_t   ast_tx_badrate;/**< tx failed 'cuz bogus xmit rate */
    a_uint32_t   ast_tx_noack;/**< tx frames with no ack marked */
    a_uint32_t   ast_tx_rts;/**< tx frames with rts enabled */
    a_uint32_t   ast_tx_cts;/**< tx frames with cts enabled */
    a_uint32_t   ast_tx_shortpre;/**< tx frames with short preamble */
    a_uint32_t   ast_tx_altrate;/**< tx frames with alternate rate */
    a_uint32_t   ast_tx_protect;/**< tx frames with protection */
    a_uint32_t   ast_rx_orn;/**< rx failed 'cuz of desc overrun */
    a_uint32_t   ast_rx_crcerr;/**< rx failed 'cuz of bad CRC */
    a_uint32_t   ast_rx_fifoerr;/**< rx failed 'cuz of FIFO overrun */
    a_uint32_t   ast_rx_badcrypt;/**< rx failed 'cuz decryption */
    a_uint32_t   ast_rx_badmic;/**< rx failed 'cuz MIC failure */
    a_uint32_t   ast_rx_phyerr;/**< rx PHY error summary count */
    a_uint32_t   ast_rx_phy[64];/**< rx PHY error per-code counts */
    a_uint32_t   ast_rx_tooshort;/**< rx discarded 'cuz frame too short */
    a_uint32_t   ast_rx_toobig;/**< rx discarded 'cuz frame too large */
    a_uint32_t   ast_rx_nobuf;/**< rx setup failed 'cuz no skbuff */
    a_uint32_t   ast_rx_packets;/**< packet recv on the interface */
    a_uint32_t   ast_rx_mgt;/**< management frames received */
    a_uint32_t   ast_rx_ctl;/**< control frames received */
    a_int8_t     ast_tx_rssi_combined;/**< tx rssi of last ack [combined] */
    a_int8_t     ast_tx_rssi_ctl0;/**< tx rssi of last ack [ctl, chain 0] */
    a_int8_t     ast_tx_rssi_ctl1;/**< tx rssi of last ack [ctl, chain 1] */
    a_int8_t     ast_tx_rssi_ctl2;/**< tx rssi of last ack [ctl, chain 2] */
    a_int8_t     ast_tx_rssi_ext0;/**< tx rssi of last ack [ext, chain 0] */
    a_int8_t     ast_tx_rssi_ext1;/**< tx rssi of last ack [ext, chain 1] */
    a_int8_t     ast_tx_rssi_ext2;/**< tx rssi of last ack [ext, chain 2] */
    a_int8_t     ast_rx_rssi_combined;/**< rx rssi from histogram [combined]*/
    a_int8_t     ast_rx_rssi_ctl0;/**< rx rssi from histogram [ctl, chain 0] */
    a_int8_t     ast_rx_rssi_ctl1;/**< rx rssi from histogram [ctl, chain 1] */
    a_int8_t     ast_rx_rssi_ctl2;/**< rx rssi from histogram [ctl, chain 2] */
    a_int8_t     ast_rx_rssi_ext0;/**< rx rssi from histogram [ext, chain 0] */
    a_int8_t     ast_rx_rssi_ext1;/**< rx rssi from histogram [ext, chain 1] */
    a_int8_t     ast_rx_rssi_ext2;/**< rx rssi from histogram [ext, chain 2] */
    a_uint32_t   ast_be_xmit;/**< beacons transmitted */
    a_uint32_t   ast_be_nobuf;/**< no skbuff available for beacon */
    a_uint32_t   ast_per_cal;/**< periodic calibration calls */
    a_uint32_t   ast_per_calfail;/**< periodic calibration failed */
    a_uint32_t   ast_per_rfgain;/**< periodic calibration rfgain reset */
    a_uint32_t   ast_rate_calls;/**< rate control checks */
    a_uint32_t   ast_rate_raise;/**< rate control raised xmit rate */
    a_uint32_t   ast_rate_drop;/**< rate control dropped xmit rate */
    a_uint32_t   ast_ant_defswitch;/**< rx/default antenna switches */
    a_uint32_t   ast_ant_txswitch;/**< tx antenna switches */
    a_uint32_t   ast_ant_rx[8];/**< rx frames with antenna */
    a_uint32_t   ast_ant_tx[8];/**< tx frames with antenna */
    a_uint32_t   ast_suspend;/**< driver suspend calls */
    a_uint32_t   ast_resume;/**< driver resume calls  */
    a_uint32_t   ast_shutdown;/**< driver shutdown calls  */
    a_uint32_t   ast_init;/**< driver init calls  */
    a_uint32_t   ast_stop;/**< driver stop calls  */
    a_uint32_t   ast_reset;/**< driver resets      */
    a_uint32_t   ast_nodealloc;/**< nodes allocated    */
    a_uint32_t   ast_nodefree;/**< nodes deleted      */
    a_uint32_t   ast_keyalloc;/**< keys allocated     */
    a_uint32_t   ast_keydelete;/**< keys deleted       */
    a_uint32_t   ast_bstuck;/**< beacon stuck       */
    a_uint32_t   ast_draintxq;/**< drain tx queue     */
    a_uint32_t   ast_stopdma;/**< stop tx queue dma  */
    a_uint32_t   ast_stoprecv;/**< stop recv          */
    a_uint32_t   ast_startrecv;/**< start recv         */
    a_uint32_t   ast_flushrecv;/**< flush recv         */
    a_uint32_t   ast_chanchange;/**< channel changes    */
    a_uint32_t   ast_fastcc;/**< Number of fast channel changes */
    a_uint32_t   ast_fastcc_errs;/**< Number of failed fast channel changes */
    a_uint32_t   ast_chanset;/**< channel sets       */
    a_uint32_t   ast_cwm_mac;/**< CWM - mac mode switch */
    a_uint32_t   ast_cwm_phy;/**< CWM - phy mode switch */
    a_uint32_t   ast_cwm_requeue;/**< CWM - requeue dest node packets */
    a_uint32_t   ast_rx_delim_pre_crcerr;/**< pre-delimit crc errors */
    a_uint32_t   ast_rx_delim_post_crcerr;/**< post-delimit crc errors */
    a_uint32_t   ast_rx_decrypt_busyerr;/**< decrypt busy errors */

    adf_net_wcmd_11n_stats_t  ast_11n;/**< 11n statistics */
    adf_net_wcmd_ampdu_trc_t  ast_trc;/**< ampdu trc */
} adf_net_wcmd_phystats_t;

/**
 * @brief diag info 
 */ 
typedef struct adf_net_wcmd_diag{
    a_int8_t     ad_name[ADF_NET_WCMD_NAME_SIZE];/**< if name*/
    a_uint16_t   ad_id;
    a_uint16_t   ad_in_size;/**< pack to fit, yech */
    a_uint8_t    *ad_in_data;
    a_uint8_t    *ad_out_data;
    a_uint32_t   ad_out_size;
}adf_net_wcmd_diag_t;

/*
 * Device phyerr ioctl info
 */
typedef struct adf_net_wcmd_phyerr{
    a_int8_t     ad_name[ADF_NET_WCMD_NAME_SIZE];/**< if name, e.g. "ath0" */
    a_uint16_t   ad_id;
    a_uint16_t   ad_in_size;                /**< pack to fit, yech */
    a_uint8_t    *ad_in_data;
    a_uint8_t    *ad_out_data;
    a_uint32_t   ad_out_size;
}adf_net_wcmd_phyerr_t;
/**
 * @brief cwm-info
 */
typedef struct adf_net_wcmd_cwminfo{
    a_uint32_t  ci_chwidth; /**< channel width */
    a_uint32_t  ci_macmode; /**< MAC mode */
    a_uint32_t  ci_phymode; /**< Phy mode */
    a_uint32_t  ci_extbusyper; /**< extension busy (percent) */
} adf_net_wcmd_cwminfo_t;

/**
 * @brief cwm-dbg
 */
typedef struct adf_net_wcmd_cwmdbg{
    adf_net_wcmd_cwm_cmd_t    dc_cmd;/**< dbg commands*/
    adf_net_wcmd_cwm_event_t  dc_arg;/**< events*/
} adf_net_wcmd_cwmdbg_t;    

/**
 * @brief device cwm info
 */
typedef struct adf_net_wcmd_cwm{
    adf_net_wcmd_cwmtype_t      type;
    union{
        adf_net_wcmd_cwmdbg_t   dbg;
        adf_net_wcmd_cwminfo_t  info;
    }cwm;
}adf_net_wcmd_cwm_t;
/**
 * @brief Helpers to access the CWM structures
 */
#define cwm_dbg         cwm.dbg
#define cwm_info        cwm.info

/**
 * @brief eth tool info
 */
typedef struct adf_net_wcmd_ethtool{
    a_uint32_t  cmd;/*XXX:???*/
    a_int8_t    driver[ADF_NET_WCMD_DRIVSIZ];/**< driver short name */
    a_int8_t    version[ADF_NET_WCMD_VERSIZ];/**< driver ver string */
    a_int8_t    fw_version[ADF_NET_WCMD_FIRMSIZ];/**< firmware ver string*/
    a_int8_t    bus_info[ADF_NET_WCMD_BUSINFO_LEN];/**< Bus info */ 
    a_int8_t    reserved1[32];
    a_int8_t    reserved2[16];
    a_uint32_t  n_stats;/**< number of u64's from ETHTOOL_GSTATS */
    a_uint32_t  testinfo_len;   
    a_uint32_t  eedump_len;/**< Size of data from EEPROM(bytes) */
    a_uint32_t  regdump_len;/**< Size of data from REG(bytes) */
}adf_net_wcmd_ethtool_t ;

typedef struct adf_net_wcmd_ethtool_info{
    adf_net_wcmd_ethtool_cmd_t     cmd;/*XXX:???*/
    adf_net_wcmd_ethtool_t         drv;
}adf_net_wcmd_ethtool_info_t;

/** 
 * @brief vap create flag info 
 */ 
typedef enum adf_net_wcmd_vapcreate_flags{
    ADF_NET_WCMD_CLONE_BSSID=0x1,/**< allocate unique mac/bssid */
    ADF_NET_WCMD_NO_STABEACONS/**< Do not setup the sta beacon timers*/ 
}adf_net_wcmd_vapcreate_flags_t;

/**
 * @brief VAP info structure used during VAPCREATE
 */
typedef struct adf_net_wcmd_vapinfo{
    a_uint8_t                       icp_name[ADF_NET_WCMD_NAME_SIZE];
    adf_net_wcmd_opmode_t           icp_opmode;/**< operating mode */
    adf_net_wcmd_vapcreate_flags_t  icp_flags;
}adf_net_wcmd_vapinfo_t;


/**
 * @brief ath stats info
 */
typedef struct adf_net_wcmd_devstats{
    a_uint64_t   rx_packets;/**< total packets received       */
    a_uint64_t   tx_packets;/**< total packets transmitted    */
    a_uint64_t   rx_bytes;/**< total bytes received         */
    a_uint64_t   tx_bytes;/**< total bytes transmitted      */
    a_uint64_t   rx_errors;/**< bad packets received         */
    a_uint64_t   tx_errors;/**< packet transmit problems     */
    a_uint64_t   rx_dropped;/**< no space in linux buffers    */
    a_uint64_t   tx_dropped;/**< no space available in linux  */
    a_uint64_t   multicast;/**< multicast packets received   */
    a_uint64_t   collisions;
    
    /* detailed rx_errors: */
    a_uint64_t   rx_length_errors;
    a_uint64_t   rx_over_errors;/**< receiver ring buff overflow  */
    a_uint64_t   rx_crc_errors;/**< recved pkt with crc error    */
    a_uint64_t   rx_frame_errors;/**< recv'd frame alignment error */
    a_uint64_t   rx_fifo_errors;/**< recv'r fifo overrun          */
    a_uint64_t   rx_missed_errors;/**< receiver missed packet       */
    
    /* detailed tx_errors */
    a_uint64_t   tx_aborted_errors;
    a_uint64_t   tx_carrier_errors;
    a_uint64_t   tx_fifo_errors;
    a_uint64_t   tx_heartbeat_errors;
    a_uint64_t   tx_window_errors;
    
    /* for cslip etc */
    a_uint64_t   rx_compressed;
    a_uint64_t   tx_compressed;
}adf_net_wcmd_devstats_t;


/**
 * @brief mtu set/get/enable/disable info
 */
typedef  a_uint32_t     adf_net_wcmd_mtu_t;
/**
 * @brief turbo
 */
typedef  a_uint32_t     adf_net_wcmd_turbo_t;

typedef union adf_net_wcmd_data{
    adf_net_wcmd_vapname_t          vapname;/*XXX: ???*/
    adf_net_wcmd_bssid_t            bssid;
    adf_net_wcmd_nickname_t         nickname;
    adf_net_wcmd_ssid_t             essid;
    adf_net_wcmd_rts_th_t           rts;/*GET_RTS_THRES & SET_RTS_THRES*/
    adf_net_wcmd_frag_th_t          frag;/*GET_FRAG & SET_FRAG*/
    adf_net_wcmd_ic_caps_t          ic_caps;
    adf_net_wcmd_iv_opmode_t        iv_opmode;
    adf_net_wcmd_freq_t             freq;
    adf_net_wcmd_retries_t          retries;
    adf_net_wcmd_txpower_t          txpower;
    adf_net_wcmd_txpowlimit_t       txpowlimit;
    adf_net_wcmd_vaplist_t          vaplist;
    adf_net_wcmd_phymode_t          phymode;
    adf_net_wcmd_vapmode_t          vapmode;/*GET_OPMODE & SET_OPMODE*/
    adf_net_wcmd_devcap_t           devcap;
    adf_net_wcmd_turbo_t            turbo;
    adf_net_wcmd_param_t            param;
    adf_net_wcmd_optie_t            optie;
    adf_net_wcmd_appie_t            appie;
    adf_net_wcmd_filter_type_t      filter;
    adf_net_wcmd_addba_t            addba;
    adf_net_wcmd_delba_t            delba;
    adf_net_wcmd_addba_status_t     addba_status;
    adf_net_wcmd_addba_resp_t       addba_resp;
    adf_net_wcmd_keyinfo_t          key;
    adf_net_wcmd_mlme_t             mlme;
    adf_net_wcmd_chanlist_t         chanlist;
    adf_net_wcmd_chaninfo_t         chaninfo;
    adf_net_wcmd_wmmparaminfo_t     wmmparam;
    adf_net_wcmd_wpaie_t            wpaie;
    adf_net_wcmd_wscie_t            wscie;
    adf_net_wcmd_power_t            power;
    adf_net_wcmd_stainfo_t          station;
    adf_net_wcmd_diag_t             dev_diag;
    adf_net_wcmd_phyerr_t           phyerr;
    adf_net_wcmd_cwm_t              cwm;
    adf_net_wcmd_ethtool_info_t     ethtool;
    adf_net_wcmd_vapinfo_t          vap_info;/**< during vapcreate*/

    adf_net_wcmd_mtu_t              mtu;
    adf_net_ethaddr_t               mac;/*MAC addr of VAP or Dev */

    adf_net_wcmd_scan_t             *scan;
    adf_net_wcmd_vapparam_range_t   *range;
    adf_net_wcmd_stastats_t         *stats_sta;
    adf_net_wcmd_vapstats_t         *stats_vap;/*XXX: name*/
    adf_net_wcmd_phystats_t         *stats_phy;
    adf_net_wcmd_devstats_t         *stats_dev;

    a_uint32_t                      datum;/*for sysctl*/
} adf_net_wcmd_data_t;

/**
 * @brief ioctl structure to configure the wireless interface.
 */ 
typedef struct adf_net_wcmd{
    char                     if_name[ADF_NET_WCMD_NAME_SIZE];/**< Iface name*/
    adf_net_wcmd_type_t      type;             /**< Type of wcmd */
    adf_net_wcmd_data_t      data;             /**< Data */       
} adf_net_wcmd_t;
/**
 * @brief helper macros
 */
#define d_vapname               data.vapname
#define d_bssid                 data.bssid
#define d_nickname              data.nickname
#define d_essid                 data.essid
#define d_rts                   data.rts
#define d_frag                  data.frag
#define d_iccaps                data.ic_caps
#define d_ivopmode              data.iv_opmode
#define d_freq                  data.freq
#define d_retries               data.retries
#define d_txpower               data.txpower
#define d_txpowlimit            data.txpowlimit
#define d_vaplist               data.vaplist
#define d_scan                  data.scan
#define d_phymode               data.phymode
#define d_opmode                data.opmode
#define d_devcap                data.devcap
#define d_turbo                 data.turbo
#define d_param                 data.param
#define d_optie                 data.optie
#define d_appie                 data.appie
#define d_filter                data.filter
#define d_addba                 data.addba
#define d_delba                 data.delba
#define d_addba_status          data.addba_status
#define d_addba_resp            data.addba_resp
#define d_key                   data.key
#define d_mlme                  data.mlme
#define d_chanlist              data.chanlist
#define d_chaninfo              data.chaninfo
#define d_wmmparam              data.wmmparam
#define d_wpaie                 data.wpaie
#define d_wscie                 data.wscie
#define d_power                 data.power
#define d_station               data.station
#define d_range                 data.range
#define d_stastats              data.stats_sta
#define d_vapstats              data.stats_vap
#define d_devstats              data.stats_dev
#define d_phystats              data.stats_phy
#define d_daig                  data.dev_diag
#define d_phyerr                data.phyerr
#define d_cwm                   data.cwm
#define d_ethtool               data.ethtool
#define d_vapinfo               data.vap_info
#define d_mtu                   data.mtu
#define d_mac                   data.mac
#define d_datum                 data.datum


typedef struct adf_net_wcmd_chansw{
    a_uint8_t    chan;
    a_uint8_t    ttbt;
}adf_net_wcmd_chansw_t;
/** 
 * ***************************Unresoloved*******************
 */
// typedef struct adf_net_wcmd_chansw_info{
//     a_uint8_t    chan;
//     a_uint8_t   ttbt;
// }adf_net_wcmd_chansw_info_t;
// 
/**
 * @brief ath mac info
 */
// typedef struct {
//     a_uint16_t sa_family;/**< address family, AF_xxx*/
//     a_int8_t   sa_data[ADF_NET_WCMD_ADDR_LEN];/**< 14 bytes address */ 
// }adf_net_wcmd_ath_mac_info_t;
#endif
