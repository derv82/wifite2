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

#define GMAC_DISCV_PKT_SZ       1024
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

enum __gmac_mii_mode {
	GMAC_MIIMODE_NONE=0,
	GMAC_MIIMODE_MII=1,
	GMAC_MIIMODE_RMII=2,
	GMAC_MIIMODE_GMII=3,
	GMAC_MIIMODE_RGMII=4,
	GMAC_MIIMODE_MAX=5
};
enum __gmac_msg_type{
    GMAC_HST_QUERY = 0x0001,
    GMAC_HST_REPLY = 0x0002,
    GMAC_TGT_QUERY = 0x0003,
    GMAC_TGT_REPLY = 0x0004
};

enum __magpie_regs{
    MAG_REG_GPIO_OE     = 0x00052000,/*GPIO Output Enable*/
    MAG_REG_RST         = 0x00050010,/*Magpie reset reg*/
    MAG_REG_RST_AHB     = 0x00050018,/*Magpie AHB_ARB reset reg*/
    MAG_REG_MII0_CTRL   = 0x00054100,/*Magpie MII0 Control reg*/
    MAG_REG_STAT_CTRL   = 0x00054104,/*Magpie Status reg*/

    MAG_REG_ETH_PLL     = 0x5600c,
    MAG_REG_ETHPLL_BYPASS = 0x56010,
};

enum __gmac_regs{
    GMAC_REG_BASE       = 0x00060000,
    GMAC_REG_MAC_CFG1   = 0x00 + GMAC_REG_BASE,/*MAC config 1*/
    GMAC_REG_MAC_CFG2   = 0x04 + GMAC_REG_BASE,/*MAC config 2*/
    GMAC_REG_IPG_IFG    = 0x08 + GMAC_REG_BASE,/*Inter-packet-gap*/
    GMAC_REG_HALF_DPLX  = 0x0c + GMAC_REG_BASE,/*Half duplex*/
    GMAC_REG_MAX_FRAME  = 0x10 + GMAC_REG_BASE,/*Max frame length*/
    GMAC_REG_MII_CFG    = 0x20 + GMAC_REG_BASE,/*MII mgmt config*/
    GMAC_REG_MII_CMD    = 0x24 + GMAC_REG_BASE,/*MII mgmt command*/
    GMAC_REG_MII_ADDR   = 0x28 + GMAC_REG_BASE,/*MII mgmt address*/
    GMAC_REG_MII_CTRL   = 0x2c + GMAC_REG_BASE,/*MII mgmt control*/
    GMAC_REG_MII_STAT   = 0x30 + GMAC_REG_BASE,/*MII mgmt status*/
    GMAC_REG_MII_PSTAT  = 0x34 + GMAC_REG_BASE,/*MII mgmt Phy status/ind*/
    GMAC_REG_IF_CTRL    = 0x38 + GMAC_REG_BASE,/*Interface control*/
    GMAC_REG_IF_STAT    = 0x3c + GMAC_REG_BASE,/*Interface status*/
    GMAC_REG_MAC_ADDR1  = 0x40 + GMAC_REG_BASE,/*MAC address 1*/
    GMAC_REG_MAC_ADDR2  = 0x44 + GMAC_REG_BASE,/*MAC address 2*/
    GMAC_REG_FIFO_CFG0  = 0x48 + GMAC_REG_BASE,/*FIFO config reg0*/
    GMAC_REG_FIFO_CFG1  = 0x4c + GMAC_REG_BASE,/*FIFO config reg1*/
    GMAC_REG_FIFO_CFG2  = 0x50 + GMAC_REG_BASE,/*FIFO config reg2*/
    GMAC_REG_FIFO_CFG3  = 0x54 + GMAC_REG_BASE,/*FIFO config reg3*/
    GMAC_REG_FIFO_CFG4  = 0x58 + GMAC_REG_BASE,/*FIFO config reg4*/
    GMAC_REG_FIFO_CFG5  = 0x5c + GMAC_REG_BASE,/*FIFO config reg5*/
    GMAC_REG_FIFO_RAM0  = 0x60 + GMAC_REG_BASE,/*FIFO RAM access reg0*/
    GMAC_REG_FIFO_RAM1  = 0x64 + GMAC_REG_BASE,/*FIFO RAM access reg1*/
    GMAC_REG_FIFO_RAM2  = 0x68 + GMAC_REG_BASE,/*FIFO RAM access reg2*/
    GMAC_REG_FIFO_RAM3  = 0x6c + GMAC_REG_BASE,/*FIFO RAM access reg3*/
    GMAC_REG_FIFO_RAM4  = 0x70 + GMAC_REG_BASE,/*FIFO RAM access reg4*/
    GMAC_REG_FIFO_RAM5  = 0x74 + GMAC_REG_BASE,/*FIFO RAM access reg5*/
    GMAC_REG_FIFO_RAM6  = 0x78 + GMAC_REG_BASE,/*FIFO RAM access reg6*/
    GMAC_REG_FIFO_RAM7  = 0x7c + GMAC_REG_BASE,/*FIFO RAM access reg7*/
};

enum  __mag_reg_rst{
    RST_GMAC   = (1 << 9),/*Reset the GMAC */
    RST_MII    = (3 << 11),/*Reset the MII*/
    RST_OTHERS = 0x5df,/*Reset everybody other than GMAC & MII*/
};

enum __mag_reg_rst_ahb{
    RST_AHB_GMAC = 0x1
};
enum __mag_mii0_ctrl_mode{
	MII0_CTRL_MODE_GMII = 0x00, 	/* GMII*/
    MII0_CTRL_MODE_MII  = 0x01,	/*MII*/
	MII0_CTRL_MODE_RGMII = 0x02,/* RGMII */
	MII0_CTRL_MODE_RMII = 0x03, /* RMII */
    MII0_CTRL_MASTER_MODE = 0x04 /* master mode */
};
enum __mag_mii0_ctrl_speed {
	MII0_CTLR_SPEED_10  = 0x00, /* 10 mbps*/
    MII0_CTRL_SPEED_100 = 0x10,	/*MII control address 100 Mbps*/
	MII0_CTRL_SPEED_1000 = 0x20 /* 1000 */
};


enum __gmac_reg_mac_cfg1{
    MAC_CFG1_TX_EN   = (1 << 0),/*TX enable*/
    MAC_CFG1_RX_EN   = (1 << 2),/*RX enable*/
    MAC_CFG1_TX_FLOW = (1 << 4),/*TX Flow control enable*/
    MAC_CFG1_RX_FLOW = (1 << 5),/*RX Flow control enable*/
    MAC_CFG1_LOOP_EN = (1 << 8),/*Enable loopback*/
};
enum __gmac_reg_mac_cfg2{
    MAC_CFG2_FULL_DUP = (1 << 0),/*Enable Full Duplex*/
    MAC_CFG2_PAD_CRC  = (1 << 2),/*Enable MAC based CRC insertion*/
    MAC_CFG2_CHK_LEN  = (1 << 4),/*Check Length field*/
    MAC_CFG2_HUGE_FRM = (1 << 5),/*Allow sending huge frames*/
    MAC_CFG2_MII      = (1 << 8),/*MAC is MII in mode*/
    MAC_CFG2_GMII     = (1 << 9),/*MAC is in GMII mode*/
    MAC_CFG2_PREAMBLE = (7 << 12),/*Default Preamble Length*/
};
enum __gmac_reg_mii_cfg{
    MII_CFG_CLK_2MHZ  = 0x0006,/*Clock is 2Mhz*/ 
};


/* following are only for F1 phy on emulation board.*/
enum __gmac_reg_mii_addr{
    MII_ADDR_RESET     			= 0x000,/*Flush the MII address register*/
	MII_ADDR_STATS      		= 0x001,/* Stauts register*/
	MII_ADDR_PHY_IDENT_1   		= 0x002,/* phy identifier [18:3]*/
	MII_ADDR_PHY_IDENT_2   		= 0x003,/* phy identifier [19:24]*/
	MII_ADDR_AUTONEG_ADV   		= 0x004,/* Autonegotiaion advertise*/
	MII_ADDR_LINKPART_ABILITY 	= 0x0005,/* link partner ability*/
	MII_ADDR_AUTONEG_EXP 		= 0x0006,/* Autonegotiation expansion*/
	MII_ADDR_NEXTPG_TX 			= 0x0007,/* Next page transmit*/
	MII_ADDR_LINKPART_NEXTPG	= 0x0008,/* Link partnet next page*/
	MII_ADDR_1000BASET_CNTRL	= 0x0009,/* 1000 base-t control*/
	MII_ADDR_1000BSAET_STATUS 	= 0x000a,/* 1000 base-t status*/
	MII_ADDR_EXTENDED_STATUS 	= 0x000f,/* extended status*/
	MII_ADDR_FUNCTION_CTRL 		= 0x0010,/* function control*/
    MII_ADDR_PHY_REG   			= 0x0011,/*Phy Status Reg*/
	MII_ADDR_INTERRUPT_ENA 		= 0x0012,/* interrupt enable*/
	MII_ADDR_INTERRUPT_STATUS 	= 0x0013,/* interrupt status*/
	MII_ADDR_EXTPHY_CTRL 		= 0x0014,/* extemded phy specific control*/
	MII_ADDR_CABDET_CTRL 		= 0x0016,/* cable detect testser control*/
	MII_ADDR_LED_CTRL 			= 0x0018,/* LED control*/
	MII_ADDR_MANLED_OVER 		= 0x0019,/* Manual LED override*/
	MII_ADDR_CABDET_STAT 		= 0x001c,/* cable detect tester status*/
	MII_ADDR_DEBUGPORT_OFF 		= 0x001d,/* Debug port address offset*/
	MII_ADDR_DEBUGPORT_DATA 	= 0x001e,/* Debug port data */
};

/* definitions for MII_ADDR_RESET register definitions*/
#define MII_ADDR_RESET_RESTART_AUTONEG (1 << 9)
#define MII_ADDR_RESET_ENABLE_AUTONEG (1 << 12)
#define MII_ADDR_RESET_ENABLE_LOOPBACK (1<<14)
#define MII_ADDR_RESET_SOFT_RESET (1<<15)
/* flags for autonegotiaion register MII_ADDR_AUTONEG_ADV, 
   All writes to this register should be followed by a soft
   reset on the phy
   The list is not exhaustive, only required fields added
   */
#define MII_AUTONEG_10BT_HALF (1<<5)
#define MII_AUTONEG_10BT_FULL (1<<6)
#define MII_AUTONEG_100BT_HALF (1<<7)
#define MII_AUTONEG_100BT_FULL (1<<8)
#define MII_AUTONEG_PAUSE (1<<9)
#define MII_1000BASET_1000BT_HALF (1<<8)
#define MII_1000BASET_1000BT_FULL (1<<9)
enum __gmac_reg_mii_ctrl{
    MII_CTRL_FULL_DPLX = 0x0100,/*Full Duplex mode*/
    MII_CTRL_SPEED_100 = 0x2000,/*Link Speed 100 Mbps*/
    MII_CTRL_LOOPBACK  = 0x4000,/*Enable Loopback mode at PHY*/
    MII_CTRL_RESET     = 0x8000,/*BMCR reset*/
};
enum __gma_reg_mii_cmd{
    MII_CMD_WRITE  = 0x0,
    MII_CMD_READ   = 0x1,/*Perform a Read cycle*/
};
enum __gmac_reg_fifo_cfg0{
    FIFO_CFG0_EN   = 0x1f00,/*Enable all the Fifo module*/
};
enum __gmac_reg_fifo_cfg1{
    FIFO_CFG1_SIZE_2K = (0x7ff << 16),/*Fifo size is 2K*/
};
enum __gmac_reg_fifo_cfg4{
    FIFO_CFG4_RX_ALL = 0x3ffff,/*receive all frames*/
};
enum __gmac_reg_if_ctrl{
    IF_CTRL_SPEED_100  = (1 << 16),/*Interface speed 100 Mbps for MII*/ 
};


#define MAX_MDIO_IO_LEN             14
#define MDIO_REG_WIDTH              4
#define MDIO_REG_BASE               0x54200
#define MDIO_REG_TO_OFFSET( __reg_number__)\
    (MDIO_REG_BASE + (MDIO_REG_WIDTH * (__reg_number__)))

#define MDIO_OWN_TGT                0x01
#define MDIO_OWN_HST                0x02
#define MDIO_REG_WRITE_DELAY        5 /* 5 micro seconds */

/*************************GMAC Data types*******************************/
typedef enum __gmac_pkt_type{
    GMAC_PKT_IS_BCAST,
    GMAC_PKT_IS_UCAST
}__gmac_pkt_type_t;

struct __ethhdr{
    unsigned char   dst[ETH_ALEN];/*destination eth addr */
    unsigned char   src[ETH_ALEN]; /*source ether addr*/
    A_UINT16      etype;/*ether type*/
}__attribute__((packed));
/**
 * @brief this is will be in big endian format
 */ 
struct __athhdr{
#ifdef LITTLE_ENDIAN
    A_UINT8   proto:6,
                res:2;
#else                    
    A_UINT8   res:2,
                proto:6;
#endif                
    A_UINT8   res_lo;
    A_UINT16  res_hi;
}__attribute__((packed));

typedef struct __gmac_hdr{
    struct  __ethhdr   eth;
    struct  __athhdr   ath;
    A_UINT16         align_pad;/*pad it for 4 byte boundary*/
}__attribute__((packed))  __gmac_hdr_t;

/*********************************GMAC softC************************/

typedef struct __gmac_softc{
    __gmac_hdr_t        hdr;
    A_UINT16          gran;
    HIF_CALLBACK        sw;
}__gmac_softc_t;



#endif

