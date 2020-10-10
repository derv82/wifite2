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
/*************************************************************************/
/*  Copyright (c) 2008 Atheros Communications, Inc., All Rights Reserved */
/*                                                                       */
/*  Module Name : cmnos_rompatch.c                                  	 */
/*                                                                       */
/*  Abstract                                                             */
/*      This file contains rom code patch mechanism, patch code is       */
/*      offline generated, and replace the indirect table function as we */
/*      need to patch. 												     */
/*                                                                       */
/*  NOTES                                                                */
/*      None                                                             */
/*                                                                       */
/*************************************************************************/

#include "sys_cfg.h"

#include "athos_api.h"

#if SYSTEM_MODULE_ROM_PATCH


LOCAL BOOLEAN _patch_dump( struct rom_patch_st *patch);
LOCAL BOOLEAN _read_rom_patch(struct rom_patch_st *patch);


// the patch install entry 
void (*patch_start)(void);

// the eep redirect addr
struct eep_redir_addr patch_addr =  {0x0, 0x0};


LOCAL
BOOLEAN _patch_dump( struct rom_patch_st *patch)
{
//    A_PRINTF("\tCRC: 0x%04x\n\r", patch->crc16);
    A_PRINTF("\tsize: %d bytes\n\r", patch->len);
    A_PRINTF("\tld_addr: 0x%08x\n\r", (uint32_t)patch->ld_addr);
    A_PRINTF("\tfun_addr: 0x%08x\n\r", (uint32_t)patch->fun_addr);
}



LOCAL 
BOOLEAN _read_rom_patch(struct rom_patch_st *patch)
{
    BOOLEAN retVal = FALSE;
    uint8_t *addr;
    uint16_t i;
    uint8_t *buf = ((uint8_t*)(patch)+(sizeof(struct rom_patch_st)-4));  //assign the patch code buffer, last 4 bytes is the data

    /*! assign the load address of the patch
     * 
     * - convert the address to dport address 0x4exxxx or 0x5xxxxx
     */
    //addr = (uint32_t *)((patch->ld_addr&(~0xc00000))|(0x400000));   
    addr = (uint8_t *)(patch->ld_addr);
    if( (uint32_t)addr < SYS_D_RAM_REGION_0_BASE || (uint32_t)addr >= (SYS_D_RAM_REGION_0_BASE + SYS_RAM_SZIE) )
    {
        A_PRINTF("!address should be dport in ram's address, 0x%08x\n\r", (uint32_t)addr);
        goto ERR_DONE;
    }
    
    _patch_dump(patch);
   
    A_PRINTF("copy %d bytes from 0x%08x to 0x%08x", patch->len, (uint32_t)buf, (uint32_t)addr);
    for(i=0; i<patch->len; i+=4) // word access
    {    
        addr[i+3] = buf[i];
        addr[i+2] = buf[i+1];
        addr[i+1] = buf[i+2];
        addr[i] = buf[i+3];
    }

    retVal =  TRUE;
ERR_DONE:
    return retVal;

}


/*!
 * decode and parse the rompatch code
 *
 * addr: the buffer in ram stored the downloaded buffer
 */
LOCAL
BOOLEAN cmnos_romp_decode(uint32_t addr)
{
    int i;
    BOOLEAN retVal = FALSE;
    struct rom_patch_st *patch;
    uint8_t *func_addr;

    A_PRINTF("[%s+]\n\r", __FUNCTION__ );
    {
        /* 
         * check the integrity of the buffer
         */
        uint32_t *mData = (uint32_t *)addr;
        uint32_t CheckSum = 0;

        // size at here is a half-word based, divide by 2 set it to a word 
        for(i=0; i<(patch_addr.size/2); i++, mData++)
            CheckSum = CheckSum ^ *mData;

        A_PRINTF("CheckSum: 0x%08x\n\r", CheckSum);

        if( CheckSum != 0 )
            goto ERR_DONE;

        /*********************************************/
        
        patch = (struct rom_patch_st *)addr;
        
        func_addr = (uint8_t *)patch->fun_addr;
        
        if( _read_rom_patch(patch) )
        {
            //A_PRINTF("\n\r patch to 0x%08x, func at 0x%08x\n\r", (uint32_t)patch->ld_addr, (uint32_t)func_addr);

            // the patch function entry, call install later
            patch_start = (void *)func_addr;

            // install the patch here
            //patch_start();
        }
        else
        {
            A_PRINTF("patch decode fail!\n\r");
            goto ERR_DONE;
        }
    }

    retVal = TRUE;

ERR_DONE:
    A_PRINTF("[%s-]\n\r", __FUNCTION__ );
    
    return retVal;
        // 
        //  if crc checking is ok, move code the where it belong according to it's ld_addr
        // 
    
}


/*!
 * install
 */
LOCAL BOOLEAN cmnos_romp_install(void)
{
	/* TBD: to be removed! */

    /*! call the patch function, 
     * 
     * - left the patch install did by the patch code,  
     *   so that we sould build the patch code with entry function is the install process
     *   e.g void install_patch(void), which update the function table
     */

    //A_PRINTF("[%s+]\n\r", __FUNCTION__);
    patch_start();
    //A_PRINTF("[%s-]\n\r", __FUNCTION__);
}

/*!
 * download
 *
 *  offset: the offset of the eeprom redirect header(offset, size)
 *
 */
LOCAL BOOLEAN cmnos_romp_download(uint16_t offset)
{
    BOOLEAN retVal = FALSE;
    uint16_t buf[2];

    uint16_t eep_start_ofst = EEPROM_START_OFFSET;
    uint16_t eep_end_ofst = EEPROM_END_OFFSET;

    A_PRINTF("[%s+]\n\r", __FUNCTION__ );

    /* TBD: to be removed! */
    /* read the patch from EEPROM, if there is an EEPROM exist and patch code stored inside */

    /* 
     * 1. read the fixed offset address of 0xfc and find the exactly patch code is
     * 2. read the patch code from eeprom and write to buffer ram
     * ------------------- leave it to decode operation ------------------
     * 3. and check the integrity of it, if the integrity is ok, goto 4
     * 4. decode the patch pack and decode each patch code and write them to the RAM 
     * 
     */

    /*
     * read the eep redirect(offset, size) from the offset
     */
     if( RET_SUCCESS != A_EEP_READ(offset, sizeof(struct eep_redir_addr)/sizeof(uint16_t), buf) )
        goto ERR_DONE;

    A_PRINTF("patch.offset: 0x%04x, patch.size : 0x%04x\n\r", buf[0], buf[1]);

    patch_addr.offset = buf[0];
    patch_addr.size = buf[1];
    
    // ATHR : 0x41544852, ((uint32_t)patch_addr == 0x41544852) || 
    // size == 0, offset > 0x3fff or offset < 0x2000, eeprom offset is between 0x2000~0x3fff
    if( (patch_addr.size == 0x0) ||(patch_addr.offset < eep_start_ofst )   \
         || (patch_addr.offset > eep_end_ofst) || ((patch_addr.offset+patch_addr.size) > eep_end_ofst))
        goto ERR_DONE;

    // read the patch code to ROM_PATCH_BUF_ADDR: 0x51E000, 
    A_EEP_READ(patch_addr.offset, patch_addr.size, (uint16_t *)ROM_PATCH_BUF_ADDR);

    if( A_ROMP_DECODE(ROM_PATCH_BUF_ADDR) )
    {
        A_ROMP_INSTALL();
    }
    else
        goto ERR_DONE;
    
    retVal = TRUE;
ERR_DONE:
    A_PRINTF("[%s-]\n\r", __FUNCTION__ );
    return retVal;

}

/*!
 * init
 */
LOCAL void cmnos_romp_init(void)
{
	/* TBD: to be removed! */
    //A_PRINTF("CMNOS_ROMP_INIT!\n\r");
}

void
cmnos_romp_module_install(struct romp_api *tbl)
{
    tbl->_romp_init         = cmnos_romp_init;
    tbl->_romp_download     = cmnos_romp_download;
    tbl->_romp_install      = cmnos_romp_install;
    tbl->_romp_decode       = cmnos_romp_decode;

}

#endif
