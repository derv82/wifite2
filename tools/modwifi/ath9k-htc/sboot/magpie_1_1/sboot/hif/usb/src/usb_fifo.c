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
#include "usb_defs.h"
#include "usb_type.h"
#include "usb_pre.h"
#include "usb_extr.h"
#include "usb_std.h"
#include "dt_defs.h"
#include "sys_cfg.h"

#include "athos_api.h"

#if SYSTEM_MODULE_USB

extern uint16_t       u8UsbConfigValue;
extern uint16_t       u8UsbInterfaceValue;
extern uint16_t       u8UsbInterfaceAlternateSetting;

#if 1

void mUsbEPMap(uint8_t EPn, uint8_t MAP)
{
    //uint8_t *reg = (uint8_t*) (ZM_FUSB_BASE+0x30+(EPn-1));
    //*reg = MAP;
    uint8_t reg = (0x30+(EPn-1));

//    A_PRINTF("=>mUsbEPMap: write: %02x to %02x (0x%08x)\n\r", MAP , reg, USB_WORD_REG_READ(reg));
    USB_BYTE_REG_WRITE(reg, MAP );

//    A_PRINTF("<=mUsbEPMap: write: %02x to %02x (0x%08x)\n\r", MAP , reg, USB_WORD_REG_READ(reg));

    //zfUartSendStr("mUsbEPMap\r\n");
    //zfUartSendStrAndHex("EPn=", EPn);
    //zfUartSendStrAndHex("MAP=", MAP);
}

void mUsbFIFOMap(uint8_t FIFOn, uint8_t MAP)
{
    //uint8_t *reg = (uint8_t*) (ZM_FUSB_BASE+0x80+FIFOn);
    //*reg = MAP;

    uint8_t reg = (0x80+FIFOn);
    
    reg = reg;

//    A_PRINTF("=>mUsbFIFOMap: write: %02x to %02x (0x%08x)\n\r", MAP , reg, USB_WORD_REG_READ(reg));
    USB_BYTE_REG_WRITE( reg, MAP );

//    A_PRINTF("<=mUsbFIFOMap: write: %02x to %02x (0x%08x)\n\r", MAP , reg, USB_WORD_REG_READ(reg));
    //zfUartSendStr("mUsbFIFOMap\r\n");
    //zfUartSendStrAndHex("FIFOn=", FIFOn);
    //zfUartSendStrAndHex("MAP=", MAP);
}

void mUsbFIFOConfig(uint8_t FIFOn, uint8_t cfg)
{
    //uint8_t *reg = (uint8_t*) (ZM_FUSB_BASE+0x90+FIFOn);
    //*reg = cfg;
    uint8_t reg = (0x90+FIFOn);

//    A_PRINTF("=>mUsbFIFOConfig: write: %02x to %02x (0x%08x)\n\r", cfg , reg, USB_WORD_REG_READ(reg));
    USB_BYTE_REG_WRITE( reg, cfg );

//    A_PRINTF("<=mUsbFIFOConfig: write: %02x to %02x (0x%08x)\n\r", cfg , reg, USB_WORD_REG_READ(reg));
    //zfUartSendStr((uint8_t *)"mUsbFIFOConfig\r\n");
    //zfUartSendStrAndHex((uint8_t *)"FIFOn=", FIFOn);
    //zfUartSendStrAndHex((uint8_t *)"cfg=", cfg);
}

void mUsbEPMxPtSzHigh(uint8_t EPn, uint8_t dir, uint16_t size)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(((dir) * 0x20)+EPn << 1));
    //*reg = (size >> 8) & 0xf;
    uint8_t reg = (ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(((dir) * 0x20)+(EPn << 1)));
    
//    A_PRINTF("=>mUsbEPMxPtSzHigh: write: %02x to %02x (0x%08x)\n\r", ((size >> 8) & 0xff), reg, USB_WORD_REG_READ(reg));
    USB_BYTE_REG_WRITE(reg, ((size >> 8) & 0xff));

//    A_PRINTF("<=mUsbEPMxPtSzHigh: write: %02x to %02x (0x%08x)\n\r", ((size >> 8) & 0xff), reg, USB_WORD_REG_READ(reg));    
    //USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(((dir) * 0x20)+EPn << 1)), ((size >> 8) & 0xf));
}

void mUsbEPMxPtSzLow(uint8_t EPn, uint8_t dir, uint16_t size)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_IN_MAX_SIZE_LOW_OFFSET+(((dir) * 0x20)+EPn << 1));
    //*reg = (size & 0xff);

    uint8_t reg = (ZM_EP_IN_MAX_SIZE_LOW_OFFSET+(((dir) * 0x20)+(EPn << 1)));
//    A_PRINTF("=>mUsbEPMxPtSzLow: write: %02x to %02x (0x%08x)\n\r", (size & 0xff), reg, USB_WORD_REG_READ(reg));
    USB_BYTE_REG_WRITE(reg, (size & 0xff)); 

//    A_PRINTF("<=mUsbEPMxPtSzLow: write: %02x to %02x (0x%08x)\n\r", (size & 0xff), reg, USB_WORD_REG_READ(reg));
}

void mUsbEPinHighBandSet(uint8_t EPn, uint8_t dir, uint16_t size)
{
#if 1
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(EPn << 1));

    //*reg &= ~(BIT6 | BIT5);
    //*reg |= (((uint8_t)((size) >> 11) + 1) << 5) * (1 - (dir));

    uint8_t reg = (ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(EPn << 1));
//    uint8_t reg2 = (((uint8_t)((size) >> 11) + 1) << 5) * (1 - (dir));
    uint8_t reg2 = (((uint8_t)((size) >> 11) + 1) << 5) * (1 - (dir));

//    A_PRINTF("=>mUsbEPinHighBandSet(%d)(size:%d)(dir:%d): write: %02x to %02x (0x%08x)\n\r", EPn, size, dir, (USB_BYTE_REG_READ(reg)|reg2), reg, USB_WORD_REG_READ(reg));
    USB_BYTE_REG_WRITE(reg, (USB_BYTE_REG_READ(reg)&~(BIT6 | BIT5)));
    USB_BYTE_REG_WRITE(reg,  (USB_BYTE_REG_READ(reg)|reg2));

//    A_PRINTF("=>mUsbEPinHighBandSet(%d)(size:%d)(dir:%d): write: %02x to %02x (0x%08x)\n\r", EPn, size, dir, (USB_BYTE_REG_READ(reg)|reg2), reg, USB_WORD_REG_READ(reg));
#endif
}

#else

#define mUsbEPMap( EPn, MAP)    USB_BYTE_REG_WRITE( (0x30+(EPn-1)), MAP )

#define mUsbFIFOMap( FIFOn, MAP)    USB_BYTE_REG_WRITE( (0x80+FIFOn), MAP )

#define mUsbFIFOConfig(FIFOn, cfg)    USB_BYTE_REG_WRITE( (0x90+FIFOn), cfg )

#define mUsbEPMxPtSzHigh(EPn, dir, size)  USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(((dir) * 0x20)+EPn << 1)), ((size >> 8) & 0xf))

#define mUsbEPMxPtSzLow(EPn, dir, size)   USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_LOW_OFFSET+(((dir) * 0x20)+EPn << 1)), (size & 0xff))

#define mUsbEPinHighBandSet( EPn, dir, size)                                                \
{                                                                                                                       \
    USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(EPn << 1)),  \
                    (USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(EPn << 1))&(~(BIT6 | BIT5)))));       \
    USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(EPn << 1)),  \
                    (USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(EPn << 1)|((uint8_t)((size) >> 11) + 1) << 5) * (1 - (dir)))));   \
}

#endif

/////////////////////////////////////////////////////
//      vUsbFIFO_EPxCfg_HS(void)
//      Description:
//          1. Configure the FIFO and EPx map
//      input: none
//      output: none
/////////////////////////////////////////////////////
void vUsbFIFO_EPxCfg_HS(void)
{

    int i;

    switch (u8UsbConfigValue)
    {
        #if (HS_CONFIGURATION_NUMBER >= 1)
        // Configuration 0X01
        case 0X01:
            switch (u8UsbInterfaceValue)
            {
                #if (HS_C1_INTERFACE_NUMBER >= 1)
                // Interface 0
                case 0:
                    switch (u8UsbInterfaceAlternateSetting)
                    {
                        #if (HS_C1_I0_ALT_NUMBER >= 1)
                        // AlternateSetting 0
                        case 0:
                            #if (HS_C1_I0_A0_EP_NUMBER >= 1)
                            //EP0X01
                            mUsbEPMap(EP1, HS_C1_I0_A0_EP1_MAP);
                            mUsbFIFOMap(HS_C1_I0_A0_EP1_FIFO_START, HS_C1_I0_A0_EP1_FIFO_MAP);

                            mUsbFIFOMap(HS_C1_I0_A0_EP1_FIFO_START+1, HS_C1_I0_A0_EP1_FIFO_MAP);    //ryan
                            
                            mUsbFIFOConfig(HS_C1_I0_A0_EP1_FIFO_START, HS_C1_I0_A0_EP1_FIFO_CONFIG);
                            
                            for(i = HS_C1_I0_A0_EP1_FIFO_START + 1 ;
                                i < HS_C1_I0_A0_EP1_FIFO_START + HS_C1_I0_A0_EP1_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (HS_C1_I0_A0_EP1_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP1, HS_C1_I0_A0_EP1_DIRECTION, (HS_C1_I0_A0_EP1_MAX_PACKET & 0x7ff) );
                            mUsbEPMxPtSzLow(EP1, HS_C1_I0_A0_EP1_DIRECTION, (HS_C1_I0_A0_EP1_MAX_PACKET & 0x7ff) );
                            mUsbEPinHighBandSet(EP1 , HS_C1_I0_A0_EP1_DIRECTION , HS_C1_I0_A0_EP1_MAX_PACKET);

                            #endif
                            #if (HS_C1_I0_A0_EP_NUMBER >= 2)
                            //EP0X02
                            mUsbEPMap(EP2, HS_C1_I0_A0_EP2_MAP);
                            mUsbFIFOMap(HS_C1_I0_A0_EP2_FIFO_START, HS_C1_I0_A0_EP2_FIFO_MAP);

                            mUsbFIFOMap(HS_C1_I0_A0_EP2_FIFO_START+1, HS_C1_I0_A0_EP2_FIFO_MAP);//ryan
                            
                            mUsbFIFOConfig(HS_C1_I0_A0_EP2_FIFO_START, HS_C1_I0_A0_EP2_FIFO_CONFIG);
                            
                            for(i = HS_C1_I0_A0_EP2_FIFO_START + 1 ;
                                i < HS_C1_I0_A0_EP2_FIFO_START + HS_C1_I0_A0_EP2_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (HS_C1_I0_A0_EP2_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP2, HS_C1_I0_A0_EP2_DIRECTION, (HS_C1_I0_A0_EP2_MAX_PACKET & 0x7ff) );
                            mUsbEPMxPtSzLow(EP2, HS_C1_I0_A0_EP2_DIRECTION, (HS_C1_I0_A0_EP2_MAX_PACKET & 0x7ff) );
                            mUsbEPinHighBandSet(EP2 , HS_C1_I0_A0_EP2_DIRECTION , HS_C1_I0_A0_EP2_MAX_PACKET);
                            
                            #endif
                            #if (HS_C1_I0_A0_EP_NUMBER >= 3)
                            //EP0X03
                            mUsbEPMap(EP3, HS_C1_I0_A0_EP3_MAP);
                            mUsbFIFOMap(HS_C1_I0_A0_EP3_FIFO_START, HS_C1_I0_A0_EP3_FIFO_MAP);
                            mUsbFIFOConfig(HS_C1_I0_A0_EP3_FIFO_START, HS_C1_I0_A0_EP3_FIFO_CONFIG);
                            
                            for(i = HS_C1_I0_A0_EP3_FIFO_START + 1 ;
                                i < HS_C1_I0_A0_EP3_FIFO_START + HS_C1_I0_A0_EP3_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (HS_C1_I0_A0_EP3_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP3, HS_C1_I0_A0_EP3_DIRECTION, (HS_C1_I0_A0_EP3_MAX_PACKET & 0x7ff) );
                            mUsbEPMxPtSzLow(EP3, HS_C1_I0_A0_EP3_DIRECTION, (HS_C1_I0_A0_EP3_MAX_PACKET & 0x7ff) );
                            mUsbEPinHighBandSet(EP3 , HS_C1_I0_A0_EP3_DIRECTION , HS_C1_I0_A0_EP3_MAX_PACKET);

                            #endif
                            #if (HS_C1_I0_A0_EP_NUMBER >= 4) || fFLASH_DISK
                            //EP0X04
                            mUsbEPMap(EP4, HS_C1_I0_A0_EP4_MAP);
                            mUsbFIFOMap(HS_C1_I0_A0_EP4_FIFO_START, HS_C1_I0_A0_EP4_FIFO_MAP);
                            mUsbFIFOConfig(HS_C1_I0_A0_EP4_FIFO_START, HS_C1_I0_A0_EP4_FIFO_CONFIG);
                            
                            for(i = HS_C1_I0_A0_EP4_FIFO_START + 1 ;
                                i < HS_C1_I0_A0_EP4_FIFO_START + HS_C1_I0_A0_EP4_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (HS_C1_I0_A0_EP4_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP4, HS_C1_I0_A0_EP4_DIRECTION, (HS_C1_I0_A0_EP4_MAX_PACKET & 0x7ff) );
                            mUsbEPMxPtSzLow(EP4, HS_C1_I0_A0_EP4_DIRECTION, (HS_C1_I0_A0_EP4_MAX_PACKET & 0x7ff) );
                            mUsbEPinHighBandSet(EP4 , HS_C1_I0_A0_EP4_DIRECTION , HS_C1_I0_A0_EP4_MAX_PACKET);

                            #endif
//////////////////////////////////////////////////////////////
#if SYSTEM_MODULE_HP_EP5
                            #if (HS_C1_I0_A0_EP_NUMBER >= 5)
                            //EP0X05
                            mUsbEPMap(EP5, HS_C1_I0_A0_EP5_MAP);
                            mUsbFIFOMap(HS_C1_I0_A0_EP5_FIFO_START, HS_C1_I0_A0_EP5_FIFO_MAP);

                            mUsbFIFOMap(HS_C1_I0_A0_EP5_FIFO_START+1, HS_C1_I0_A0_EP5_FIFO_MAP);        //ryan

                            mUsbFIFOConfig(HS_C1_I0_A0_EP5_FIFO_START, HS_C1_I0_A0_EP5_FIFO_CONFIG);
                            
                            for(i = HS_C1_I0_A0_EP5_FIFO_START + 1 ;
                                i < HS_C1_I0_A0_EP5_FIFO_START + HS_C1_I0_A0_EP5_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (HS_C1_I0_A0_EP5_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP5, HS_C1_I0_A0_EP5_DIRECTION, (HS_C1_I0_A0_EP5_MAX_PACKET & 0x7ff) );
                            mUsbEPMxPtSzLow(EP5, HS_C1_I0_A0_EP5_DIRECTION, (HS_C1_I0_A0_EP5_MAX_PACKET & 0x7ff) );
                            mUsbEPinHighBandSet(EP5 , HS_C1_I0_A0_EP5_DIRECTION , HS_C1_I0_A0_EP5_MAX_PACKET);
                            #endif
#endif //SYSTEM_MODULE_HP_EP5

//////////////////////////////////////////////////////////////
#if SYSTEM_MODULE_HP_EP6
                            #if (HS_C1_I0_A0_EP_NUMBER >= 6)
                            //EP0X06
                            mUsbEPMap(EP6, HS_C1_I0_A0_EP6_MAP);
                            mUsbFIFOMap(HS_C1_I0_A0_EP6_FIFO_START, HS_C1_I0_A0_EP6_FIFO_MAP);

                            mUsbFIFOMap(HS_C1_I0_A0_EP6_FIFO_START+1, HS_C1_I0_A0_EP6_FIFO_MAP);        //ryan

                            mUsbFIFOConfig(HS_C1_I0_A0_EP6_FIFO_START, HS_C1_I0_A0_EP6_FIFO_CONFIG);
                            
                            for(i = HS_C1_I0_A0_EP6_FIFO_START + 1 ;
                                i < HS_C1_I0_A0_EP6_FIFO_START + HS_C1_I0_A0_EP6_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (HS_C1_I0_A0_EP6_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP6, HS_C1_I0_A0_EP6_DIRECTION, (HS_C1_I0_A0_EP6_MAX_PACKET & 0x7ff) );
                            mUsbEPMxPtSzLow(EP6, HS_C1_I0_A0_EP6_DIRECTION, (HS_C1_I0_A0_EP6_MAX_PACKET & 0x7ff) );
                            mUsbEPinHighBandSet(EP6 , HS_C1_I0_A0_EP6_DIRECTION , HS_C1_I0_A0_EP6_MAX_PACKET);
                            #endif
                            break;
#endif //SYSTEM_MODULE_HP_EP6

                        #endif
                        default:
                            break;
                    }
                    break;
                #endif
                default:
                    break;
            }
            break;
        #endif
        default:
            break;
    }
    //mCHECK_STACK();

}

void vUsbFIFO_EPxCfg_FS(void)
{

int i;

    switch (u8UsbConfigValue)
    {
        #if (FS_CONFIGURATION_NUMBER >= 1)
        // Configuration 0X01
        case 0X01:
            switch (u8UsbInterfaceValue)
            {
                #if (FS_C1_INTERFACE_NUMBER >= 1)
                // Interface 0
                case 0:
                    switch (u8UsbInterfaceAlternateSetting)
                    {
                        #if (FS_C1_I0_ALT_NUMBER >= 1)
                        // AlternateSetting 0
                        case 0:
                            #if (FS_C1_I0_A0_EP_NUMBER >= 1)
                            //EP0X01
                            mUsbEPMap(EP1, FS_C1_I0_A0_EP1_MAP);
                            mUsbFIFOMap(FS_C1_I0_A0_EP1_FIFO_START, FS_C1_I0_A0_EP1_FIFO_MAP);
                            mUsbFIFOConfig(FS_C1_I0_A0_EP1_FIFO_START, FS_C1_I0_A0_EP1_FIFO_CONFIG);
                            
                            for(i = FS_C1_I0_A0_EP1_FIFO_START + 1 ;
                                i < FS_C1_I0_A0_EP1_FIFO_START + FS_C1_I0_A0_EP1_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (FS_C1_I0_A0_EP1_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP1, FS_C1_I0_A0_EP1_DIRECTION, (FS_C1_I0_A0_EP1_MAX_PACKET & 0x7ff));
                            mUsbEPMxPtSzLow(EP1, FS_C1_I0_A0_EP1_DIRECTION, (FS_C1_I0_A0_EP1_MAX_PACKET & 0x7ff));
                        //``.JWEI 2003/04/29
                            mUsbEPinHighBandSet(EP1 , FS_C1_I0_A0_EP1_DIRECTION, FS_C1_I0_A0_EP1_MAX_PACKET);

                            #endif
                            #if (FS_C1_I0_A0_EP_NUMBER >= 2)
                            //EP0X02
                            mUsbEPMap(EP2, FS_C1_I0_A0_EP2_MAP);
                            mUsbFIFOMap(FS_C1_I0_A0_EP2_FIFO_START, FS_C1_I0_A0_EP2_FIFO_MAP);
                            mUsbFIFOConfig(FS_C1_I0_A0_EP2_FIFO_START, FS_C1_I0_A0_EP2_FIFO_CONFIG);
                            
                            for(i = FS_C1_I0_A0_EP2_FIFO_START + 1 ;
                                i < FS_C1_I0_A0_EP2_FIFO_START + FS_C1_I0_A0_EP2_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (FS_C1_I0_A0_EP2_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP2, FS_C1_I0_A0_EP2_DIRECTION, (FS_C1_I0_A0_EP2_MAX_PACKET & 0x7ff));
                            mUsbEPMxPtSzLow(EP2, FS_C1_I0_A0_EP2_DIRECTION, (FS_C1_I0_A0_EP2_MAX_PACKET & 0x7ff));
                            mUsbEPinHighBandSet(EP2 , FS_C1_I0_A0_EP2_DIRECTION, FS_C1_I0_A0_EP2_MAX_PACKET);
                            
                            #endif
                            #if (FS_C1_I0_A0_EP_NUMBER >= 3)
                            //EP0X03
                            mUsbEPMap(EP3, FS_C1_I0_A0_EP3_MAP);
                            mUsbFIFOMap(FS_C1_I0_A0_EP3_FIFO_START, FS_C1_I0_A0_EP3_FIFO_MAP);
                            mUsbFIFOConfig(FS_C1_I0_A0_EP3_FIFO_START, FS_C1_I0_A0_EP3_FIFO_CONFIG);
                            
                            for(i = FS_C1_I0_A0_EP3_FIFO_START + 1 ;
                                i < FS_C1_I0_A0_EP3_FIFO_START + FS_C1_I0_A0_EP3_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (FS_C1_I0_A0_EP3_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP3, FS_C1_I0_A0_EP3_DIRECTION, (FS_C1_I0_A0_EP3_MAX_PACKET & 0x7ff));
                            mUsbEPMxPtSzLow(EP3, FS_C1_I0_A0_EP3_DIRECTION, (FS_C1_I0_A0_EP3_MAX_PACKET & 0x7ff));
                            mUsbEPinHighBandSet(EP3 , FS_C1_I0_A0_EP3_DIRECTION, FS_C1_I0_A0_EP3_MAX_PACKET);

                            #endif
                            #if (FS_C1_I0_A0_EP_NUMBER >= 4) || fFLASH_DISK
                            //EP0X04
                            mUsbEPMap(EP4, FS_C1_I0_A0_EP4_MAP);
                            mUsbFIFOMap(FS_C1_I0_A0_EP4_FIFO_START, FS_C1_I0_A0_EP4_FIFO_MAP);
                            mUsbFIFOConfig(FS_C1_I0_A0_EP4_FIFO_START, FS_C1_I0_A0_EP4_FIFO_CONFIG);
                            
                            for(i = FS_C1_I0_A0_EP4_FIFO_START + 1 ;
                                i < FS_C1_I0_A0_EP4_FIFO_START + FS_C1_I0_A0_EP4_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (FS_C1_I0_A0_EP4_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP4, FS_C1_I0_A0_EP4_DIRECTION, (FS_C1_I0_A0_EP4_MAX_PACKET & 0x7ff));
                            mUsbEPMxPtSzLow(EP4, FS_C1_I0_A0_EP4_DIRECTION, (FS_C1_I0_A0_EP4_MAX_PACKET & 0x7ff));
                            mUsbEPinHighBandSet(EP4 , FS_C1_I0_A0_EP4_DIRECTION, FS_C1_I0_A0_EP4_MAX_PACKET);

                            #endif
                            #if (FS_C1_I0_A0_EP_NUMBER >= 5)
                            //EP0X05
                            mUsbEPMap(EP5, FS_C1_I0_A0_EP5_MAP);
                            mUsbFIFOMap(FS_C1_I0_A0_EP5_FIFO_START, FS_C1_I0_A0_EP5_FIFO_MAP);
                            mUsbFIFOConfig(FS_C1_I0_A0_EP5_FIFO_START, FS_C1_I0_A0_EP5_FIFO_CONFIG);
                            
                            for(i = FS_C1_I0_A0_EP5_FIFO_START + 1 ;
                                i < FS_C1_I0_A0_EP5_FIFO_START + FS_C1_I0_A0_EP5_FIFO_NO ;
                                i ++)
                            {
                                mUsbFIFOConfig(i, (FS_C1_I0_A0_EP5_FIFO_CONFIG & (~BIT7)) );
                            }
                            
                            mUsbEPMxPtSzHigh(EP5, FS_C1_I0_A0_EP5_DIRECTION, (FS_C1_I0_A0_EP5_MAX_PACKET & 0x7ff));
                            mUsbEPMxPtSzLow(EP5, FS_C1_I0_A0_EP5_DIRECTION, (FS_C1_I0_A0_EP5_MAX_PACKET & 0x7ff));
                            mUsbEPinHighBandSet(EP5 , FS_C1_I0_A0_EP5_DIRECTION, FS_C1_I0_A0_EP5_MAX_PACKET);
                            #endif
                            break;
                        #endif
                        default:
                            break;
                    }
                    break;
                #endif
                default:
                    break;
            }
            break;
        #endif
        default:
            break;
    }
    //mCHECK_STACK();
}

#endif
