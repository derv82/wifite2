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
#include <adf_os_stdtypes.h>
#include <adf_os_types.h>

//#include <HIF_api.h>
#include <cmnos_api.h>

#include <Magpie_api.h>

#include <adf_os_util.h>
#include <adf_os_mem.h>
#include <adf_os_time.h>
#include <dma_lib.h>
#include "hif_gmac.h"



/**************************Constants******************************/
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
    MAG_REG_MDIO        = 0x00054200,/*Mapie MDIO register*/
    MAG_REG_MDIO_CMD    = 0x00 + MAG_REG_MDIO,/*CMD register (0)*/
    MAG_REG_MDIO_OWN    = 0x02 + MAG_REG_MDIO,/*OWN register (1)*/
    /**
     * XXX: Endianess inside the word & between words
     */
    MAG_REG_MDIO_ADDR0  = 0x04 + MAG_REG_MDIO,/*ADDR0 register (2)*/
    MAG_REG_MDIO_ADDR1  = 0x06 + MAG_REG_MDIO,/*ADDR1 register (3)*/
    MAG_REG_MDIO_WRITE0 = 0x08 + MAG_REG_MDIO,/*Data WRITE0 register (4)*/
    MAG_REG_MDIO_WRITE1 = 0x0a + MAG_REG_MDIO,/*Data WRITE1 register (5)*/
    MAG_REG_MDIO_READ0  = 0x0c + MAG_REG_MDIO,/*Data READ0 register (6)*/
    MAG_REG_MDIO_READ1  = 0x0e + MAG_REG_MDIO,/*Data READ1 register (7)*/
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
enum __mag_mii0_ctrl{
    MII0_CTRL_MODE  = (1 << 0),/*MII mode*/
    MII0_CTRL_100   = (1 << 4),/*MII control address 100 Mbps*/
};

enum __mag_mdio_cmd{
    MDIO_CMD_DONE     = 0x01,/*Operation over*/
    MDIO_CMD_WRITE    = 0x02,/*Write data*/
    MDIO_CMD_READ     = 0x03 /*Read data*/
};
enum __mag_mdio_own{
    MDIO_OWN_HST  = 0x00,/*Host can use CMD & Data Regs*/
    MDIO_OWN_TGT  = 0x01 /*Tgt can use CMD & Data Regs*/
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
enum __gmac_reg_mii_addr{
    MII_ADDR_RESET     = 0x000,/*Flush the MII address register*/
    MII_ADDR_PHY_REG   = 0x011,/*Phy Status Reg*/
};
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


#define ret_pkt         sw.send_buf_done
#define indicate_pkt    sw.recv_buf
#define htc_ctx         sw.context
/*********************************DEFINES**********************************/
#define hif_gmac_sc(_hdl)   (__gmac_softc_t *)(_hdl)
#define gmac_hdr(_vbuf)     (__gmac_hdr_t *)(_vbuf)->desc_list->buf_addr
#define GMAC_HLEN           (sizeof(struct __gmac_hdr))

#define __gmac_mdelay(_msecs)   A_DELAY_USECS((_msecs) * 1000)

int     __gmac_xmit_buf(hif_handle_t hdl, int pipe, VBUF *vbuf);
void    __gmac_reap_recv(__gmac_softc_t  *sc, dma_engine_t  eng_no);

/***********************************Globals********************************/
/**
 * @brief Engines are fixed
 */
__gmac_softc_t    gmac_sc = {
    .gran = GMAC_MAX_PKT_LEN
};
A_UINT8  gmac_addr[ETH_ALEN]  = {0x00, 0xaa, 0xaa, 0xaa, 0xaa, 0xaa};
A_UINT8  bcast_addr[ETH_ALEN] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};

/**************************************APIs********************************/

/**
 * @brief This a replica of the ADF_NBUF_ALLOC
 * 
 * @param size
 * @param reserve
 * @param align
 * 
 * @return VBUF*
 */
VBUF *
__gmac_vbuf_alloc(A_UINT32  size, A_UINT32  reserve, A_UINT32 align)
{
    VBUF *buf = NULL;
    VDESC *desc;
    
    buf = VBUF_alloc_vbuf();
    if ( buf != NULL ) {
        desc = VDESC_alloc_vdesc();
        desc->buf_addr = (A_UINT8 *)A_ALLOCRAM(size);
        desc->buf_size = size;
        desc->next_desc = NULL;
        desc->data_offset = reserve;
        desc->data_size = 0;
        desc->control = 0;    
        
        buf->desc_list = desc;
        buf->buf_length = 0;    
    }
    
    return buf;
}
/**
 * @brief This is a replica of ADF_NBUF_PULL_HEAD
 * 
 * @param buf
 * @param size
 * 
 * @return A_UINT8*
 */
A_UINT8 *
__gmac_vbuf_pull_head(VBUF  *buf, A_UINT32 len)
{
    A_UINT8 *ptr = NULL;
    VDESC *desc = buf->desc_list;
    
    desc->data_offset += len;
    desc->data_size -= len;
    buf->buf_length -= len;
    ptr = desc->buf_addr + desc->data_offset;
    
    return ptr;
}
/**
 * @brief This is a replica of ADF_NBUF_PUSH_HEAD
 * 
 * @param buf
 * @param size
 * 
 * @return A_UINT8*
 */
A_UINT8 *
__gmac_vbuf_push_head(VBUF *buf, A_UINT32 len)
{
    A_UINT8 *ptr = NULL; 
    VDESC *desc = buf->desc_list;
    
    desc->data_offset -= len;
    desc->data_size += len;
    buf->buf_length += len;
    ptr = desc->buf_addr + desc->data_offset;
    return(ptr);
}
/**
 * @brief This is a replica ADF_NBUF_LAST
 * 
 * @param buf
 * 
 * @return VDESC*
 */
VDESC * 
__gmac_vbuf_last(VBUF *buf)
{
    VDESC *desc = buf->desc_list;
    
    while(desc->next_desc != NULL)
        desc = desc->next_desc;
    
    return desc;
}
/**
 * @brief This is a replica of ADF_NBUF_PUT_TAIL
 * 
 * @param buf
 * @param size
 * 
 * @return A_UINT8*
 */
A_UINT8 *
__gmac_vbuf_put_tail(VBUF  *buf, A_UINT32 len)
{
    A_UINT8 *tail = NULL;
    VDESC *last_desc = __gmac_vbuf_last(buf);
    
    tail = ( last_desc->buf_addr + last_desc->data_offset + 
             last_desc->data_size );

    last_desc->data_size += len;
    buf->buf_length += len;
    
    return tail;
}

/************************************GMAC**********************************/
A_UINT16
__gmac_reg_read16(A_UINT32 addr)
{
    return *((volatile A_UINT16 *)addr);
}

void
__gmac_reg_write16(A_UINT32 addr, A_UINT16 val)
{
    *((volatile A_UINT16 *)addr) = val;
}


A_UINT32
__gmac_reg_read32(A_UINT32 addr)
{
    return *((volatile A_UINT32 *)addr);
}

void
__gmac_reg_write32(A_UINT32 addr, A_UINT32 val)
{
    *((volatile A_UINT32 *)addr) = val;
}
/**
 * @brief Read the MAC address from EEPROM
 * XXX: read from real EEPROM
 * 
 * @param mac (pointer to fill the mac address)
 */
void
__gmac_rom_read_mac(A_UINT8  mac_addr[])
{
    A_MEMCPY(mac_addr, gmac_addr, ETH_ALEN);
}
/**
 * @brief Write the MAC address into the Station address
 *        register
 * 
 * @param mac
 */
void
__gmac_reg_write_mac(A_UINT8  mac_addr[])
{
    A_UINT32  mac_lo = 0, mac_hi = 0;

    A_MEMCPY(&mac_lo, mac_addr, 4);
    A_MEMCPY(&mac_hi, mac_addr + 4, 2);

    A_PRINTF("mac address = %x:%x:%x:%x:%x:%x\n",
                 mac_addr[0], mac_addr[1], mac_addr[2],
                 mac_addr[3], mac_addr[4], mac_addr[5]);

    __gmac_reg_write32(GMAC_REG_MAC_ADDR1, mac_lo);
    __gmac_reg_write32(GMAC_REG_MAC_ADDR2, mac_hi);
}

/**
 * @brief Wait for the MII operation to complete
 */
void
__gmac_mii_op_wait(void)
{
    A_UINT32 r_data;

    r_data = __gmac_reg_read32(GMAC_REG_MII_PSTAT) & 0x1;
    while(r_data)
         r_data = (__gmac_reg_read32(GMAC_REG_MII_PSTAT) & 0x1);

}
void
__gmac_reset(void)
{
    volatile A_UINT32 r_data;
    volatile A_UINT32 w_data;

    /**
     * Reset the GMAC controller from Magpie Reset Register
     */
    r_data = __gmac_reg_read32(MAG_REG_RST);
    r_data |= RST_GMAC;
    __gmac_reg_write32(MAG_REG_RST, r_data);

    __gmac_mdelay(1);
  
    /**
     * Pull it out from the Reset State
     */
    r_data  = __gmac_reg_read32(MAG_REG_RST);
    r_data &= ~RST_GMAC;
    __gmac_reg_write32(MAG_REG_RST, r_data);

    /**
     * Reset the MII
     */
    r_data  = __gmac_reg_read32(MAG_REG_RST);
    r_data |= (RST_MII | RST_GMAC);
    __gmac_reg_write32(MAG_REG_RST, r_data);

    __gmac_mdelay(1);
    /**
     * Pull the MII out of reset
     */
    r_data  = __gmac_reg_read32(MAG_REG_RST);
    r_data &= ~( RST_MII | RST_GMAC);
    __gmac_reg_write32(MAG_REG_RST, r_data);

    __gmac_mdelay(1);

    /**
     * Reset other modules PCI, PCIE, USB & Eth PLL
     * XXX:why???
     */
//    __gmac_reg_write32(MAG_REG_RST, RST_OTHERS);

    __gmac_mdelay(1);

    /**
     * Reset the AHB Arb. Unit
     */
    r_data  = __gmac_reg_read32(MAG_REG_RST_AHB);
    r_data |= RST_AHB_GMAC;
    __gmac_reg_write32(MAG_REG_RST_AHB, r_data);
    
    /**
     * MII mode initialization
     */
    w_data = ( MAC_CFG2_FULL_DUP | MAC_CFG2_PAD_CRC | MAC_CFG2_CHK_LEN |
               MAC_CFG2_HUGE_FRM | MAC_CFG2_MII | MAC_CFG2_PREAMBLE );

    __gmac_reg_write32(GMAC_REG_MAC_CFG2, w_data);

    /**
     * Enable  FIFO modules
     */
    __gmac_reg_write32(GMAC_REG_FIFO_CFG0, FIFO_CFG0_EN);

    /**
     * Mode = MII & Speed = 100 Mbps
     */
    w_data = ( MII0_CTRL_100 | MII0_CTRL_MODE );
    __gmac_reg_write32(MAG_REG_MII0_CTRL, w_data);

    /**
     * Set the interface speed to 100 Mbps
     */
    __gmac_reg_write32(GMAC_REG_IF_CTRL, IF_CTRL_SPEED_100);

    /**
     * Fifo size set to 2K bytes
     */
    r_data  = __gmac_reg_read32(GMAC_REG_FIFO_CFG1);
    r_data |= FIFO_CFG1_SIZE_2K;
    __gmac_reg_write32(GMAC_REG_FIFO_CFG1, r_data);

    /**
     * Enable the transceiver
     */
    w_data = MAC_CFG1_RX_EN | MAC_CFG1_TX_EN;
    __gmac_reg_write32(GMAC_REG_MAC_CFG1, w_data);

    /**
     * Set the MII Clock to 2Mhz
     */
    __gmac_reg_write32(GMAC_REG_MII_CFG, MII_CFG_CLK_2MHZ);

    /**
     * Programming the phy registers
     */
    __gmac_reg_write32(GMAC_REG_MII_ADDR, MII_ADDR_RESET);

    /**
     * BMCR reset for the PHY
     */
    __gmac_reg_write32(GMAC_REG_MII_CTRL, MII_CTRL_RESET);

    /**
     * Wait until the MII Reg write has been flushed
     */
    __gmac_mii_op_wait();

    /**
     * PHY register 0x000 , BMCR
     */
    __gmac_reg_write32(GMAC_REG_MII_ADDR, MII_ADDR_RESET);

    /**
     * Write the value in the register
     */
    w_data = ( MII_CTRL_FULL_DPLX | MII_CTRL_SPEED_100 | MII_CTRL_RESET);
    __gmac_reg_write32(GMAC_REG_MII_CTRL, w_data);
    
    __gmac_mii_op_wait();

    /**
     * Pull the BMCR out of the reset state
     */
    __gmac_reg_write32(GMAC_REG_MII_ADDR, MII_ADDR_RESET);

    w_data = (MII_CTRL_FULL_DPLX | MII_CTRL_SPEED_100);
    __gmac_reg_write32(GMAC_REG_MII_ADDR, w_data);

    __gmac_mii_op_wait();

    /**
     * XXX: This should be for some debugging purpose, don't know
     * why we should write into the GPIO Output Enable the value
     * returned from PHY status register Read
     */
    __gmac_reg_write32(GMAC_REG_MII_CMD, MII_CMD_WRITE);
    __gmac_reg_write32(GMAC_REG_MII_ADDR, MII_ADDR_PHY_REG);
    __gmac_reg_write32(GMAC_REG_MII_CMD, MII_CMD_READ);

    __gmac_mii_op_wait();

    r_data = __gmac_reg_read32(GMAC_REG_MII_STAT);

    __gmac_reg_write32(MAG_REG_GPIO_OE, r_data);

    /**
     * Enable Receive Fifo
     */
    r_data  = __gmac_reg_read32(GMAC_REG_FIFO_CFG4);
    r_data |= FIFO_CFG4_RX_ALL;
    __gmac_reg_write32(GMAC_REG_FIFO_CFG4, r_data);

}
/**
 * @brief return if the pipe is supported
 * 
 * @param pipe
 * 
 * @return a_bool_t
 */
static inline a_bool_t
__gmac_chk_pipe(hif_gmac_pipe_t pipe)
{
    switch (pipe) {
    case HIF_GMAC_PIPE_TX:
    case HIF_GMAC_PIPE_RX:
        return A_TRUE;
    default:
        return A_FALSE;
    }
}

VBUF *
__gmac_pkt_alloc(A_UINT32  size)
{
    VBUF * buf;
    A_UINT16 fill_size;
    A_UINT8  *data;

    if(size < GMAC_HLEN)
        return NULL;

    buf = __gmac_vbuf_alloc(size, GMAC_HLEN, 0);
    if(!buf)
        return NULL;

    fill_size = size - GMAC_HLEN;

    data = __gmac_vbuf_put_tail(buf, fill_size);

    A_MEMSET(data, 0xaa, fill_size);

    return buf;
}
/**
 * @brief Slap the header
 * 
 * @param buf
 * @param hdr
 */
void
__gmac_put_hdr(VBUF * buf, __gmac_hdr_t  *hdr)
{
    A_UINT8  *data;

    data = __gmac_vbuf_push_head(buf, GMAC_HLEN);

    A_MEMCPY(data, hdr, GMAC_HLEN);
}
/**
 * @brief
 * 
 * @param hdr
 * @param src
 */
void
__gmac_prep_ethhdr(__gmac_hdr_t  *hdr, A_UINT8  *dst)
{
    A_MEMCPY(hdr->eth.dst, dst, ETH_ALEN);
    hdr->eth.etype = ETH_P_ATH;
}


a_bool_t
__is_ath_header(__gmac_softc_t  *sc, VBUF  *vbuf)
{
    __gmac_hdr_t  *hdr = gmac_hdr(vbuf);
    
    if(hdr->ath.proto != sc->hdr.ath.proto)
        return A_FALSE;
    
    return A_TRUE;
}

a_status_t
__gmac_process_discv(__gmac_softc_t  *sc)
{
    a_status_t  err = A_STATUS_OK;
    VBUF  *vbuf;
    __gmac_hdr_t  *buf_hdr ;
    
          
    vbuf = dma_lib_reap_recv(DMA_ENGINE_RX0);
    
    if(!__is_ath_header(sc, vbuf))
        goto fail;
    
    buf_hdr = gmac_hdr(vbuf);    
    
    A_MEMCPY(sc->hdr.eth.dst, buf_hdr->eth.src, ETH_ALEN);
    
    __gmac_vbuf_pull_head(vbuf, GMAC_HLEN);

    /**
     * Application should do the return_recv
     */       
    sc->indicate_pkt(NULL, vbuf, sc->htc_ctx);
    
    
    return A_STATUS_OK;

    /**
     * This is not our packet
     */
fail:
    
    dma_lib_return_recv(DMA_ENGINE_RX0, vbuf);
            
    return err;     
}
/**
 * @brief The GMAC host discovery loop
 */
void
__gmac_discover(void)
{
    a_status_t    err = A_STATUS_FAILED;
    VBUF *    buf;
    __gmac_softc_t  *sc = &gmac_sc;


    /**
     * Get a packet
     */
    buf = __gmac_pkt_alloc(GMAC_DISCV_PKT_SZ);

    /**
     * Prepare the broadcast packet
     */
    __gmac_prep_ethhdr(&sc->hdr, bcast_addr);
    __gmac_put_hdr(buf, &sc->hdr);

    while(1){

        if(buf)
            dma_lib_hard_xmit(DMA_ENGINE_TX0, buf);

        buf = NULL;
        __gmac_mdelay(GMAC_DISCV_WAIT);
        
        if(dma_lib_xmit_done(DMA_ENGINE_TX0))
            buf = dma_lib_reap_xmitted(DMA_ENGINE_TX0);
        
        
        while(dma_lib_recv_pkt(DMA_ENGINE_RX0) && err)
            err = __gmac_process_discv(sc);

        if(!err)
            break;
    }

    adf_os_assert(buf);
}

void
__gmac_mdio_check(void)
{
    A_UINT16  own;

    /*Read the Ownership register*/
    do {
        own = __gmac_reg_read16(MAG_REG_MDIO_OWN);
    } while ( own == MDIO_OWN_TGT );

}

void
__gmac_mdio_load_exec(void)
{
    volatile A_UINT16  cmd, more = 1 ;
    volatile A_UINT16  *addr[2];
    void ( *exec_fn)(void) = NULL;

    do {
        /**
         * Read the Command register
         */
        cmd = __gmac_reg_read16(MAG_REG_MDIO_CMD);

        switch (cmd) {

        case MDIO_CMD_WRITE:

           /**
            * 1. Read the address from Address register
            * 2. Write the data from Data register into the address
            */
            (A_UINT16 *)addr[0]  = __gmac_reg_read16(MAG_REG_MDIO_ADDR0);
            *addr[0] = __gmac_reg_read16(MAG_REG_MDIO_WRITE0);
            
            (A_UINT16 *)addr[1]  = __gmac_reg_read16(MAG_REG_MDIO_ADDR1);
            *addr[1] = __gmac_reg_read16(MAG_REG_MDIO_WRITE1);

            if ( exec_fn ) 
                break;

            exec_fn = (A_UINT32 *)addr;
            break;

        case MDIO_CMD_DONE:

            more = 0;
            break;

        case MDIO_CMD_READ:
            
            /**
             * 1. Read the address from Address register
             * 2. Write the data into the Data register from the address
             */
            addr[0]  = (A_UINT16 *)__gmac_reg_read16(MAG_REG_MDIO_ADDR0);
             __gmac_reg_write16(MAG_REG_MDIO_READ0, *addr[0]);

            addr[1]  = (A_UINT16 *)__gmac_reg_read16(MAG_REG_MDIO_ADDR1);
            __gmac_reg_write16(MAG_REG_MDIO_READ1, *addr[1]);

            break;
        default:

            A_PRINTF("Command not implemmented\n");
            adf_os_assert(0);
            break;
        }

    } while ( more );

    /**
     * Change the Ownership
     */
    __gmac_reg_write16(MAG_REG_MDIO_OWN, MDIO_OWN_HST);
    
    if ( exec_fn )
        exec_fn();

}

void
__gmac_mdio_init(void)
{

more_exec:

        /**
         * Check for Targets turn
         */
        __gmac_mdio_check();

        /**
         * Load & execute or Read data, if this returns then keep
         * repeating
         */
        __gmac_mdio_load_exec();

        /**
         * If we are here then Host wants some more function execs or
         * reads
         */
        goto more_exec;

}
void
__gmac_boot_init(void)
{
    __gmac_softc_t   *sc = &gmac_sc;
    
    
    __gmac_reset();

    /**
     * Magpie is Booting
     */
    sc->hdr.ath.proto = ATH_P_MAGBOOT;

    dma_lib_tx_init(DMA_ENGINE_TX0, DMA_IF_GMAC);
    dma_lib_rx_init(DMA_ENGINE_RX0, DMA_IF_GMAC);

    dma_lib_rx_config(DMA_ENGINE_RX0, GMAC_MAX_DESC, GMAC_MAX_PKT_LEN);

    /**
     * Read the MAC address from the ROM & Write it into the
     * Register
     */ 
    __gmac_rom_read_mac(sc->hdr.eth.src);
    __gmac_reg_write_mac(sc->hdr.eth.src);

    /**
     * Discover the Host
     */
    __gmac_discover();
}   
/**
 * @brief
 * 
 * @param pConfig
 * 
 * @return hif_handle_t
 */
hif_handle_t 
__gmac_init(HIF_CONFIG *pConfig)
{
    __gmac_softc_t  *sc = &gmac_sc;
    
    sc->hdr.ath.proto = ATH_P_MAGNORM;

    dma_lib_tx_init(DMA_ENGINE_TX0, DMA_IF_GMAC);
    dma_lib_rx_init(DMA_ENGINE_RX0, DMA_IF_GMAC);
    
    return &gmac_sc;
}
/**
 * @brief Configure the receive pipe
 * 
 * @param hdl
 * @param pipe
 * @param num_desc
 */
void
__gmac_cfg_pipe(hif_handle_t hdl, int pipe, int num_desc)
{
    __gmac_softc_t  *sc = &gmac_sc;

    if(pipe == HIF_GMAC_PIPE_RX)
        dma_lib_rx_config(DMA_ENGINE_RX0, num_desc, sc->gran);
}
/**
 * @brief Start the interface
 * 
 * @param hdl
 */
void
__gmac_start(hif_handle_t  hdl)
{
    return;
}
/**
 * @brief Register callback of thre HTC
 * 
 * @param hdl
 * @param sw
 */
void
__gmac_reg_callback(hif_handle_t hdl, HIF_CALLBACK *sw)
{
    __gmac_softc_t   *sc = &gmac_sc;

    sc->htc_ctx       = sw->context;
    sc->indicate_pkt  = sw->recv_buf;
    sc->ret_pkt       = sw->send_buf_done;
}
/**
 * @brief reap the transmit queue for trasnmitted packets
 * 
 * @param sc
 * @param eng_no
 */
void
__gmac_reap_xmitted(__gmac_softc_t  *sc, dma_engine_t  eng_no)
{
    VBUF *vbuf = NULL;
    /**
     * Walk through the all your TX engines
     */
    do {
       
       vbuf = dma_lib_reap_xmitted(eng_no);
       if(!vbuf)
            break;
       
       __gmac_vbuf_pull_head(vbuf, GMAC_HLEN);
       sc->ret_pkt(vbuf, sc->htc_ctx);

    } while ( vbuf );
}
/**
 * @brief reap the receive queue for vbuf's on the specified
 *        engine number
 * 
 * @param sc
 * @param eng_no
 */
void
__gmac_reap_recv(__gmac_softc_t  *sc, dma_engine_t  eng_no)
{
    VBUF   *vbuf = NULL;

    do {
        vbuf = dma_lib_reap_recv(eng_no);
        
        if(!vbuf)
            break;
        
        if(!__is_ath_header(sc, vbuf)){
            dma_lib_return_recv(eng_no, vbuf);
            continue;
        }
            
        __gmac_vbuf_pull_head(vbuf, GMAC_HLEN);

        sc->indicate_pkt(NULL, vbuf, sc->htc_ctx); 

    } while ( vbuf );
}
/**
 * @brief The interrupt handler
 * 
 * @param hdl
 */
void
__gmac_isr_handler(hif_handle_t hdl)
{
    __gmac_softc_t  *sc = &gmac_sc;

    if(dma_lib_xmit_done(DMA_ENGINE_TX0))
        __gmac_reap_xmitted(sc, DMA_ENGINE_TX0);

    if(dma_lib_recv_pkt(DMA_ENGINE_RX0))
        __gmac_reap_recv(sc, DMA_ENGINE_RX0);
}
/**
 * @brief transmit the vbuf from the specified pipe
 * 
 * @param hdl
 * @param pipe
 * @param buf
 * 
 * @return int
 */
int
__gmac_xmit_buf(hif_handle_t hdl, int pipe, VBUF *vbuf)
{
    __gmac_softc_t  *sc = &gmac_sc;

    if (pipe != HIF_GMAC_PIPE_TX)
        return -1;

#if 0
    adf_os_assert( vbuf->desc_list->data_offset >= GMAC_HLEN)
#endif
     
    __gmac_put_hdr(vbuf, &sc->hdr);

    return dma_lib_hard_xmit(DMA_ENGINE_TX0, vbuf);
}
/**
 * @brief Submit the receive vbuf into the receive queue
 * 
 * @param handle
 * @param pipe
 * @param buf
 */
void
__gmac_return_recv(hif_handle_t hdl, int pipe, VBUF *vbuf)
{
    if (pipe == HIF_GMAC_PIPE_RX) 
        dma_lib_return_recv(DMA_ENGINE_RX0, vbuf);
}
/**
 * @brief Is this pipe number supported
 * 
 * @param handle
 * @param pipe
 * 
 * @return int
 */
int
__gmac_is_pipe_supported(hif_handle_t hdl, int pipe)
{
    return __gmac_chk_pipe(pipe);
}
/**
 * @brief maximum message length this pipe can support
 * 
 * @param handle
 * @param pipe
 * 
 * @return int
 */
int  
__gmac_get_max_msg_len(hif_handle_t hdl, int pipe)
{
    if(__gmac_chk_pipe(pipe))
        return GMAC_MAX_PKT_LEN;

    return 0;
}
/**
 * @brief return the header room required by this HIF
 * 
 * @param hdl
 * 
 * @return int
 */
int
__gmac_get_reserved_headroom(hif_handle_t  hdl)
{
    return (GMAC_HLEN);
}
/**
 * @brief Device shutdown, HIF reset required
 * 
 * @param hdl
 */
void
__gmac_shutdown(hif_handle_t hdl)
{
    return;
}
void 
__gmac_get_def_pipe(hif_handle_t handle, A_UINT8 *pipe_uplink, 
                       A_UINT8 *pipe_downlink)
{
    *pipe_uplink   = HIF_GMAC_PIPE_RX;
    *pipe_downlink = HIF_GMAC_PIPE_TX;
}

/**
 * @brief This install the API's of the HIF
 * 
 * @param apis
 */
void 
hif_gmac_module_install(struct hif_api *apis)
{
    /* hook in APIs */
    apis->_init = __gmac_init;
    apis->_start = __gmac_start;
    apis->_config_pipe = __gmac_cfg_pipe;
    apis->_isr_handler = __gmac_isr_handler;
    apis->_send_buffer = __gmac_xmit_buf;
    apis->_return_recv_buf = __gmac_return_recv;
    apis->_is_pipe_supported = __gmac_is_pipe_supported;
    apis->_get_max_msg_len = __gmac_get_max_msg_len;
    apis->_register_callback = __gmac_reg_callback;
    apis->_shutdown = __gmac_shutdown;/*XXX*/
    apis->_get_reserved_headroom = __gmac_get_reserved_headroom;
    apis->_get_default_pipe  = __gmac_get_def_pipe;
}

void 
cmnos_gmac_module_install(struct gmac_api *boot_apis)
{
    boot_apis->gmac_boot_init  = __gmac_boot_init;
}
