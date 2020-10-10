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
#include "athos_api.h"


#if SYSTEM_MODULE_EEPROM

// DEBUG DELAY OF RC ACCESS!!!!!! SHOULD BE FIXED!
#define PCIE_RC_ACCESS_DELAY    20

#define PCI_RC_RESET_BIT                            BIT6
#define PCI_RC_PHY_RESET_BIT                        BIT7
#define PCI_RC_PLL_RESET_BIT                        BIT8
#define PCI_RC_PHY_SHIFT_RESET_BIT                  BIT10

#define H_EEPROM_CTRL                               0x401c
    #define B_EEP_CTRL_CLKDIV                       (BIT2|BIT3|BIT4|BIT5|BIT6|BIT7)
    #define B_EEP_CTRL_NOT_PRESENT                  (BIT8)
    #define B_EEP_CTRL_CORRUPT                      (BIT9)

#define H_EEPROM_STS_DATA                           0x407c
    #define B_EEP_STS_STATE_BUSY                    (BIT16)
    #define B_EEP_STS_IS_BUSY                       (BIT17)
    #define B_EEP_STS_PROTECTED                     (BIT18)
    #define B_EEP_STS_DATA_NOT_EXIST                (BIT19)

#define CMD_PCI_RC_RESET_ON()    HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR,  \
                                    (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)|  \
                                        (PCI_RC_PHY_SHIFT_RESET_BIT|PCI_RC_PLL_RESET_BIT|PCI_RC_PHY_RESET_BIT|PCI_RC_RESET_BIT)))

#define CMD_PCI_RC_RESET_CLR()   HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR, \
                                    (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)&   \
                                        (~(PCI_RC_PHY_SHIFT_RESET_BIT|PCI_RC_PLL_RESET_BIT|PCI_RC_PHY_RESET_BIT|PCI_RC_RESET_BIT))))


////////////////////////////////////////////////////////////////////////////////////////////////


/*! eep write half word
 *
 * offset: is the offset address you want to do the write operation
 * data: is the data to write to eeprom
 *
 * return: TRUE/FALSE
 */
LOCAL BOOLEAN cmnos_eeprom_write_hword(uint16_t offset, uint16_t data)
{
	/*! - Livy sugguest not use the retry, since it'll be huge retry count
	 *    so that, supposed that if the apb or pcie_rc is working fine,
	 *    we should always could see the NOT_BUSY, otherwise,
	 * 	  it should have something worng!, put a little delay in there,
     *
	 *  - debug string here will be noisy!!
	 */
    //uint16_t retryCnt = 1000;

#if defined(PROJECT_MAGPIE)
    //gpio configuration, set GPIOs output to value set in output reg
    HAL_WORD_REG_WRITE((EEPROM_CTRL_BASE+0x4054), (HAL_WORD_REG_READ((EEPROM_CTRL_BASE+0x4054)) | 0x20000));
    HAL_WORD_REG_WRITE((EEPROM_CTRL_BASE+0x4060), 0);
    HAL_WORD_REG_WRITE((EEPROM_CTRL_BASE+0x4064), 0);

    //GPIO3 always drive output
    HAL_WORD_REG_WRITE((EEPROM_CTRL_BASE+0x404c), 0xc0);

    //Set 0 on GPIO3
    HAL_WORD_REG_WRITE((EEPROM_CTRL_BASE+0x4048), 0x0);
#endif

    HAL_WORD_REG_WRITE(EEPROM_ADDR_BASE + offset*4, (uint32_t)data);

    //while( retryCnt-- > 0 )
	while(1)
    {
        if( (HAL_WORD_REG_READ((EEPROM_CTRL_BASE+H_EEPROM_STS_DATA))&(B_EEP_STS_STATE_BUSY | B_EEP_STS_IS_BUSY)) == 0 )
        {
            return(TRUE);
        }
//        A_DELAY_USECS(100);
    }

    return FALSE;
}

/*! eep read half word
 *
 *  offset: is the offset address you want to do the read operation
 *
 *  return: the data we read from eeprom
 */
LOCAL BOOLEAN cmnos_eeprom_read_hword(uint16_t offset, uint16_t *mData)
{
    uint32_t mStsData;
    //uint16_t retryCnt = 1000;

    HAL_WORD_REG_READ(EEPROM_ADDR_BASE + offset*4);

    //while( retryCnt-- > 0 )
	while(1)
    {
        mStsData = HAL_WORD_REG_READ((EEPROM_CTRL_BASE+H_EEPROM_STS_DATA));

        if( (mStsData&(B_EEP_STS_STATE_BUSY | B_EEP_STS_IS_BUSY)) == 0 )
        {
            *mData = (uint16_t)(mStsData & 0xffff);
            return TRUE;
        }
//		A_DELAY_USECS(100);
    }

    return FALSE;
}
//////////////////////////////////////////////////////////////////////////////////////////////////////

LOCAL BOOLEAN eep_state = FALSE;
LOCAL BOOLEAN eep_exist = FALSE;


/*!- Initialize eeprom, actually we link up the pcie_rc for accessing the eeprom in client card
 *
 */
LOCAL T_EEP_RET
cmnos_eep_is_exist(void)
{
    if( FALSE != eep_state )
    {
        if( FALSE == eep_exist )
        {
            uint16_t mData = HAL_WORD_REG_READ((EEPROM_CTRL_BASE+H_EEPROM_CTRL));

            if( mData&B_EEP_CTRL_NOT_PRESENT )
                return RET_NOT_EXIST;
            else if ( mData&B_EEP_CTRL_CORRUPT )
                return RET_EEP_CORRUPT;
            else {
                eep_exist = TRUE;
                return RET_SUCCESS;
        	}
        }
        else    // already done the checking, fast response
            return RET_SUCCESS;
    }

    return RET_NOT_INIT;
}

/*!- eeprom write
 *
 * offset: where to write
 * len:    number of half-word of the pBuf
 * pBuf:   data buffer to write
 */
LOCAL T_EEP_RET
cmnos_eep_write(uint16_t offset, uint16_t len, uint16_t *pBuf)
{
    T_EEP_RET retVal;
    uint16_t *pData = (uint16_t*)pBuf;
    uint16_t i, j;

    uint16_t eep_start_ofst = EEPROM_START_OFFSET;
    uint16_t eep_end_ofst = EEPROM_END_OFFSET;
    

    if( FALSE != eep_state )
    {
		if( (offset < eep_start_ofst) || (offset > eep_end_ofst) || ((offset+len) > eep_end_ofst) )
		{
		    A_PUTS("-E10-");
            retVal = RET_EEP_OVERFLOW;
		}
        else
        {
            for(i=offset, j=0; i<len+(offset); i++, j++)
            {
                if( TRUE == cmnos_eeprom_write_hword(i, pData[j]) )
                {
                    retVal = RET_SUCCESS;
                }
                else
                    A_PUTS("-E11-");
            }
        }
    }
    else
    {
        A_PUTS("-E12-");
        retVal = RET_NOT_INIT;
    }

    return retVal;
}

/*!- eeprom read
 *
 * offset: where to read
 * len:    number of bytes to read
 * pBuf:   data buffer to read
 */
LOCAL T_EEP_RET
cmnos_eep_read(uint16_t offset, uint16_t len, uint16_t *pBuf)
{
    T_EEP_RET retVal;
    uint16_t i;
    uint16_t *mData = pBuf;

    uint16_t eep_start_ofst = EEPROM_START_OFFSET;
    uint16_t eep_end_ofst = EEPROM_END_OFFSET;

    if( FALSE != eep_state )
    {
		if( (offset < eep_start_ofst) || (offset > eep_end_ofst) || ((offset+len) > eep_end_ofst) )
		{
		    A_PUTS("-E13-");
            retVal = RET_EEP_OVERFLOW;
		}
		else
		{
		    for(i=(offset); i<len+(offset); i++)
		    {
		        if( cmnos_eeprom_read_hword(i, mData) )
                {
                    mData++;
		        }
		    }

		    retVal = RET_SUCCESS;
		}
    }
    else
        retVal = RET_NOT_INIT;

    return retVal;

}


/*!- Initialize eeprom, actually we link up the pcie_rc for accessing the eeprom in client card
 *
 * Ryan - Add setup for PLL, refer to bug#37418
 *
 *  5. clear PCIE_RC_PLL PCIE_PHY_SHIFT, PCIE_PHY, PCIE_RC rst bit
 *  6. clear PCIE_PLL bypass mode and PWD bit (BIT16 and BIT18)
 *  7. set bus master and memory space enable 
 *  8. set app_ltssm_enable
 *
 *  200ns in each access
 *
 */
LOCAL void
cmnos_eep_init(void)
{
    uint32_t mStsData;
    volatile int32_t i = 10000;
    volatile reg_value = 0x0;

#if defined(PROJECT_MAGPIE)
    if( TRUE != eep_state )
    {
        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x40;

        /* 5 */
#if defined(MAGPIE_FPGA)
        if (*(volatile uint32_t *)(WATCH_DOG_MAGIC_PATTERN_ADDR) == WDT_MAGIC_PATTERN )
        {
        // fpga will hang since external pcie_rc is not able to reset, do a wdt check here, and avoid toching pcie_rc phy reset
        // not know will real chip have same issue, ryan
        //
            DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x41;
        
/*        
    // Paddu sugguest to remove these, since PCIE_RC's reset state is 1 already
    //
            HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR,  \
                (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)|  \
                    (PCI_RC_PLL_RESET_BIT|PCI_RC_RESET_BIT)));

            A_DELAY_USECS(PCIE_RC_ACCESS_DELAY);
            
            DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x42;
*/         
            HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR, \
                (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)&   \
                    (~(PCI_RC_PLL_RESET_BIT|PCI_RC_RESET_BIT))));

            A_DELAY_USECS(PCIE_RC_ACCESS_DELAY);
        }
        else
#endif
        {
/*
     // Paddu sugguest to remove these, since PCIE_RC's reset state is 1 already
     // rom1.0 fix: looks like resetting the rc even already in reset state is fine 
     //             but this would fix the eeprom-less issue, when we do the 2n init
*/
            /* asser the reset to pcie_rc */
            DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x43;
            CMD_PCI_RC_RESET_ON();
            A_DELAY_USECS(PCIE_RC_ACCESS_DELAY);

            /* dereset the reset */
            DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x44;
            CMD_PCI_RC_RESET_CLR();
            A_DELAY_USECS(500);
        }

/*!
 * Ryan - clr MAGPIE_REG_AHB_ARB_ADDR, BIT1 is needed no mater FPGA or ASIC
 */
//#if defined(MAGPIE_FPGA)
    // workaround for FPGA, do we need to enable the PCIE_RC DMA just for accessing the EEPROM?
    //HAL_WORD_REG_WRITE(0x00050018, 0x6);, purpose is to enable pcie_rc access internal memory
    //HAL_WORD_REG_WRITE(MAGPIE_REG_AHB_ARB_ADDR, (HAL_WORD_REG_READ(MAGPIE_REG_AHB_ARB_ADDR)|(BIT1|BIT2)));
        
        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x49;
        HAL_WORD_REG_WRITE(MAGPIE_REG_AHB_ARB_ADDR,
            (HAL_WORD_REG_READ(MAGPIE_REG_AHB_ARB_ADDR)|(BIT1)));
    	A_DELAY_USECS(PCIE_RC_ACCESS_DELAY);
//#endif

        /* 7.5. asser pcie_ep reset */
        HAL_WORD_REG_WRITE(0x00040018, (HAL_WORD_REG_READ(0x00040018) & ~(0x1 << 2))); 

#if defined(MAGPIE_ASIC)
        /* PLL setup should be ASIC/DV specific */
        /* 6. set PCIE_PLL in bypass mode, and get out of power-down,  */
        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x50;
        HAL_WORD_REG_WRITE(MAGPIE_REG_PCIE_PLL_CONFIG_ADDR, \
            (HAL_WORD_REG_READ(MAGPIE_REG_PCIE_PLL_CONFIG_ADDR)&(~(BIT16|BIT18))));

        /* 100us delay wait for PCIE PLL stable */
        A_DELAY_USECS(100); 
#endif      

        /* 7. set bus master and memory space enable */
        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x45;
        HAL_WORD_REG_WRITE(0x00020004, (HAL_WORD_REG_READ(0x00020004)|(BIT1|BIT2)));
        A_DELAY_USECS(PCIE_RC_ACCESS_DELAY);

        /* 7.5. de-asser pcie_ep reset */
        HAL_WORD_REG_WRITE(0x00040018, (HAL_WORD_REG_READ(0x00040018)|(0x1 << 2)));
        A_DELAY_USECS(PCIE_RC_ACCESS_DELAY);

        /* 8. set app_ltssm_enable */
        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x46;
        HAL_WORD_REG_WRITE(0x00040000, (HAL_WORD_REG_READ(0x00040000)|0xffc1));
        
        /*!
         * Receive control (PCIE_RESET), 
         *  0x40018, BIT0: LINK_UP, PHY Link up -PHY Link up/down indicator
         *  in case the link up is not ready and we access the 0x14000000, 
         *  vmc will hang here
         */

        /* poll 0x40018/bit0 (1000 times) until it turns to 1 */
        while(i-->0)
        {
            reg_value = HAL_WORD_REG_READ(0x00040018);
            if( reg_value & BIT0 ) 
                break;
            A_DELAY_USECS(PCIE_RC_ACCESS_DELAY); 
        }

        /* init fail, can't detect PCI_RC LINK UP, give up the init */
        if( i<=0 )
        {
			DEBUG_SYSTEM_STATE |= BIT26;
            goto ERR_DONE;
        }

        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x47;
        HAL_WORD_REG_WRITE(0x14000004, (HAL_WORD_REG_READ(0x14000004)|0x116));
        A_DELAY_USECS(PCIE_RC_ACCESS_DELAY);

        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x48;
        HAL_WORD_REG_WRITE(0x14000010, (HAL_WORD_REG_READ(0x14000010)|EEPROM_CTRL_BASE));
        eep_state = TRUE;
    }

#elif defined(PROJECT_K2)
    eep_state = TRUE;
#endif /* End of #if defined(PROJECT_MAGPIE) */
    if (TRUE == eep_state)
    {
        /* Read offset 1 location to determine if this EEPROM is protected somewhere */
        HAL_WORD_REG_READ(EEPROM_ADDR_BASE + 4);

    	while(1)
        {
            mStsData = HAL_WORD_REG_READ((EEPROM_CTRL_BASE+H_EEPROM_STS_DATA));

            /* If this location is protected or EEPROM does not exist, return immediately */
            if ( mStsData & (B_EEP_STS_PROTECTED | B_EEP_STS_DATA_NOT_EXIST) )
            {
                eep_state = FALSE;
                break;
            }

            if ( ( mStsData & (B_EEP_STS_STATE_BUSY | B_EEP_STS_IS_BUSY) ) == 0 )
            {
                if (mStsData & 0xffff)
                    cmnos_eeprom_write_hword( (uint16_t)1, (uint16_t)0 );

                break;
            }

    		A_DELAY_USECS(100);
        }
    }
ERR_DONE:
    
}


void
cmnos_eep_module_install(struct eep_api *tbl)
{
    tbl->_eep_init          = cmnos_eep_init;
    tbl->_eep_read          = cmnos_eep_read;
    tbl->_eep_write         = cmnos_eep_write;
    tbl->_eep_is_exist      = cmnos_eep_is_exist;
}

#endif /* SYSTEM_MODULE_EEPROM */

