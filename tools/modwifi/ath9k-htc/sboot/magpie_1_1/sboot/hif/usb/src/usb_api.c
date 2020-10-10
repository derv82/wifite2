#include "usb_defs.h"
#include "usb_type.h"
#include "usb_pre.h"
#include "usb_extr.h"
#include "usb_std.h"
#include "reg_defs.h"
#include "athos_api.h"
#include "usbfifo_api.h"

#include "sys_cfg.h"

#if SYSTEM_MODULE_USB

#define CMD_GET_CUSTOM_DATA     4
LOCAL void flash_read(uint16_t len, uint16_t ofset);

SetupPacket ControlCmd;
USB_FIFO_CONFIG usbFifoConf;
uint32_t fwCheckSum = 0;

#define fBUS_POWER                 1
uint16_t   UsbStatus[3];

/* Variable for USB EP0 pipe (USB.c) */
uint16_t       *pu8DescriptorEX;
uint16_t       u16TxRxCounter;
uint16_t       *u8ConfigDescriptorEX;
//extern BOOLEAN     bUsbEP0HaltSt;
Action      eUsbCxFinishAction;
CommandType eUsbCxCommand;
BOOLEAN     UsbChirpFinish;

uint16_t       u8UsbConfigValue;
uint16_t       u8UsbInterfaceValue;
uint16_t       u8UsbInterfaceAlternateSetting;
uint16_t       u16FirmwareComplete;

extern uint16_t *UsbDeviceDescriptor;
extern uint16_t *String00Descriptor;
extern uint16_t *String10Descriptor;
extern uint16_t *String20Descriptor;
extern uint16_t *String30Descriptor;

/////////////////////////////////////////////////
// should be declared as extern array not pointer
extern uint16_t u8DeviceQualifierDescriptorEX[];
extern uint16_t u8OtherSpeedConfigDescriptorEX[];

uint16_t *u8UsbDeviceDescriptor;
uint16_t *u8String00Descriptor;
uint16_t *u8String10Descriptor;
uint16_t *u8String20Descriptor;
uint16_t *u8String30Descriptor;


#if 0   // use macro instead of function
void mUsbEPinRsTgSet(uint8_t u8ep)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1));
    //*reg |= BIT4;
    USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
        (USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))|BIT4));

}

void mUsbEPinRsTgClr(uint8_t u8ep)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1));
    //*reg &= ~BIT4;
    USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
        (USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))&(~BIT4)));
}

void mUsbEPoutRsTgSet(uint8_t u8ep)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1));
    //*reg |= BIT4;
    USB_BYTE_REG_WRITE((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
        (USB_BYTE_REG_READ((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))|BIT4));
}

void mUsbEPoutRsTgClr(uint8_t u8ep)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1));
    //*reg &= ~BIT4;
    USB_BYTE_REG_WRITE((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
        (USB_BYTE_REG_READ((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))&(~BIT4)));
}

void mUsbEPinStallSet(uint8_t u8ep)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1));
    //*reg |= BIT3;
    USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
        USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))|BIT3);
}

void mUsbEPinStallClr(uint8_t u8ep)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1));
    //*reg &= ~BIT3;

    USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
        (USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))&(~BIT3)));
}

void mUsbEPoutStallSet(uint8_t u8ep)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1));
    //*reg |= BIT3;
    USB_BYTE_REG_WRITE((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
        (USB_BYTE_REG_READ((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))|BIT3));
}

void mUsbEPoutStallClr(uint8_t u8ep)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1));
    //*reg &= ~BIT3;
    USB_BYTE_REG_WRITE((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
        (USB_BYTE_REG_READ((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))&(~BIT3)));
}

uint8_t mUsbEPinStallST(uint8_t u8ep)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1));
    //return ((*reg & BIT3) >> 3);
    return ((USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))& BIT3) >> 3);
}

uint8_t mUsbEPoutStallST(uint8_t u8ep)
{
    //uint8_t* reg = (uint8_t*) (ZM_FUSB_BASE+ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1));
    //return ((*reg & BIT3) >> 3);
    return ((USB_BYTE_REG_READ((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))& BIT3) >> 3);
}

uint8_t mUsbEPMapRd(uint8_t EPn)
{
    //uint8_t *reg = (uint8_t*) (ZM_FUSB_BASE+0x30+(EPn-1));
    //return *reg;
    return (USB_BYTE_REG_READ((0x30+(EPn-1))));
}

uint8_t mUsbFIFOCfgRd(uint8_t FIFOn)
{
    //uint8_t *reg = (uint8_t*) (ZM_FUSB_BASE+0x90+FIFOn);
    //return *reg;
    return (USB_BYTE_REG_READ((0x90+FIFOn)));
}

void vUsb_Data_Out0Byte(void)
{
    //ZM_INTR_SOURCE_7_REG &= ~BIT7;
    USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_REG, \
        (USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_REG&(~BIT7))));
}


void vUsb_Data_In0Byte(void)
{
    //ZM_INTR_SOURCE_7_REG &= ~BIT6;

    USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_REG, \
        (USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_REG&(~BIT6))));
}


/***********************************************************************/
//      vUsb_ep0end()
//      Description:
//          1. End this transfer.
//      input: none
//      output: none
/***********************************************************************/
void vUsb_ep0end(void)
{
    eUsbCxCommand = CMD_VOID;
    //ZM_CX_CONFIG_STATUS_REG = 0x01;
    USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, 0x01);
    //mUsbEP0DoneSet();                               // Return EP0_Done flag
}

/***********************************************************************/
//      vUsb_ep0fail()
//      Description:
//          1. Stall this transfer.
//      input: none
//      output: none
/***********************************************************************/
void vUsb_ep0fail(void)
{
    //ZM_CX_CONFIG_STATUS_REG = 0x04;
    USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, 0x04);
    //mUsbEP0StallSet();                              // Return EP0_Stall
}


/***********************************************************************/
//      vUsb_rst()
//      Description:
//          1. Change descriptor table (High or Full speed).
//      input: none
//      output: none
/***********************************************************************/
void vUsb_rst(void)
{
//    zfUartSendStr((uint8_t *) "vUsb_rst\r\n");
    //ZM_INTR_SOURCE_7_REG &= ~0x02;
    USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_OFFSET, \
        (USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_OFFSET)&(~BIT1)));
    UsbChirpFinish = FALSE;
}

/***********************************************************************/
//      vUsb_suspend()
//      Description:
//          1. .
//      input: none
//      output: none
/***********************************************************************/
void vUsb_suspend(void)
{
// uP must do-over everything it should handle
// and do before into the suspend mode
    //mUsbIntSuspClr();                       // Go Suspend status
    //ZM_INTR_SOURCE_7_REG &= ~0x04;
    USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_OFFSET, \
        (USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_OFFSET)&(~BIT2)));
}

/***********************************************************************/
//      vUsb_resm()
//      Description:
//          1. Change descriptor table (High or Full speed).
//      input: none
//      output: none
/***********************************************************************/
void vUsb_resm(void)
{
// uP must do-over everything it should handle
// and do before into the suspend mode

//    mUsbIntResmClr();                       // uP must wakeup immediately
    //ZM_INTR_SOURCE_7_REG &= ~0x08;
    USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_OFFSET, \
        (USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_OFFSET)&(~BIT3)));
}

#else

#define mUsbEPinRsTgSet(u8ep)   USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
                                    USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))|BIT4)

#define mUsbEPinRsTgClr(u8ep)   USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
                                    USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))&~BIT4)

#define mUsbEPoutRsTgSet(u8ep)  USB_BYTE_REG_WRITE((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
                                    USB_BYTE_REG_READ((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))|BIT4)

#define mUsbEPoutRsTgClr(u8ep)  USB_BYTE_REG_WRITE((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
                                    USB_BYTE_REG_READ((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))&~BIT4)

#define mUsbEPinStallSet(u8ep)  USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
                                    USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))|BIT3)

#define mUsbEPinStallClr(u8ep)  USB_BYTE_REG_WRITE((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
                                    USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))&~BIT3)

#define mUsbEPoutStallSet(u8ep) USB_BYTE_REG_WRITE((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
                                    USB_BYTE_REG_READ((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))|BIT3)

#define mUsbEPoutStallClr(u8ep) USB_BYTE_REG_WRITE((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)), \
                                    USB_BYTE_REG_READ((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))&~BIT3)

#define mUsbEPinStallST(u8ep) ((USB_BYTE_REG_READ((ZM_EP_IN_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))& BIT3) >> 3)

#define mUsbEPoutStallST(u8ep) ((USB_BYTE_REG_READ((ZM_EP_OUT_MAX_SIZE_HIGH_OFFSET+(u8ep << 1)))& BIT3) >> 3)

#define mUsbEPMapRd(EPn)    (USB_BYTE_REG_READ((0x30+(EPn-1))))

#define mUsbFIFOCfgRd(FIFOn)    (USB_BYTE_REG_READ((0x90+FIFOn)))

#define vUsb_Data_Out0Byte(void)    USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_REG, \
                                        USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_REG&~BIT7))


#define vUsb_Data_In0Byte(void) USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_REG, \
                                    USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_REG&~BIT6))

#define vUsb_ep0end(void)                                   \
{                                                           \
    eUsbCxCommand = CMD_VOID;                               \
    USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, 0x01);   \
}

#define vUsb_ep0fail(void)  USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, 0x04)

#define vUsb_rst()                                              \
{                                                               \
    USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_OFFSET,                 \
        (USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_OFFSET)&~BIT1));    \
    UsbChirpFinish = FALSE;                                     \
}

#define vUsb_suspend()  USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_OFFSET, \
                            (USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_OFFSET)&~BIT2))

#define vUsb_resm() USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_OFFSET,     \
                        (USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_OFFSET)&~BIT3))


#endif

LOCAL void flash_read_data(void)
{
    uint8_t u8temp;

    // to keep tracking the txrx fifo
    // max 64 bytes for transmission one time,
    if (u16TxRxCounter < EP0MAXPACKETSIZE)
        u8temp = (uint8_t) u16TxRxCounter;
    else
        u8temp = EP0MAXPACKETSIZE;

    u16TxRxCounter -= (uint16_t) u8temp;

    {
        register uint8_t u8count;
        uint8_t remainder;

        for (u8count = 0; u8count < (u8temp/4); u8count ++)
        {
            uint32_t ep0_data;
            uint16_t ep0_low;
            uint16_t ep0_high;

            // pack data into word size
            ep0_low = *pu8DescriptorEX++;
            ep0_high = *pu8DescriptorEX++;

            // composed the data as a word
            ep0_data = (ep0_high << 16) + ep0_low;

            USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, ep0_data);
        }

        remainder = u8temp % 4;

        // Check whether there are data needed to be filled into the FIFO
        if (remainder == 3)
        {
            uint32_t ep0_data;
            uint16_t ep0_low;
            uint16_t ep0_high;

            // pack data into word size
            ep0_low = *pu8DescriptorEX++;
            ep0_high = *pu8DescriptorEX++;

            ep0_data = (ep0_high << 16) + ep0_low;

            USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x7);
            USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, ep0_data);
        }
        else if (remainder == 2)
        {
            USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x3);
            USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, *pu8DescriptorEX);
        }
        else if (remainder == 1)
        {
            USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x1);
            USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, *pu8DescriptorEX);
        }

        // Restore CBus FIFO size to word size
        USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xf);
    }

    // end of the data stage
    if (u16TxRxCounter == 0)
    {
        eUsbCxCommand = CMD_VOID;
        eUsbCxFinishAction = ACT_DONE;
    }
}

/***********************************************************************/
//      vUsb_ep0tx()
//      Description:
//          1. Transmit data to EP0 FIFO.
//      input: none
//      output: none
/***********************************************************************/
LOCAL void vUsb_ep0tx(void)
{
    switch (eUsbCxCommand)
    {
        case CMD_GET_DESCRIPTOR:
            A_USB_EP0_TX_DATA();
            break;
       
        default:
            /* Mark endpoint STALL */
            USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, BIT6);

            break;
    }

//    eUsbCxFinishAction = ACT_IDLE;
}


/***********************************************************************/
//      vUsb_ep0rx()
//      Description:
//          1. Receive data from EP0 FIFO.
//      input: none
//      output: none
/***********************************************************************/
LOCAL void vUsb_ep0rx(void)
{

    switch (eUsbCxCommand)
    {
        case CMD_SET_DESCRIPTOR:
            A_USB_EP0_RX_DATA();
            break;
        default:
            //mUsbEP0StallSet();
            break;
    }

    if (u16TxRxCounter != 0)
        eUsbCxFinishAction = ACT_IDLE;
}


LOCAL void vUsbClrEPx(void)
{
    uint8_t u8ep;

    // Clear All EPx Toggle Bit
    for (u8ep = 1; u8ep <= FUSB200_MAX_EP; u8ep ++)
    {
        mUsbEPinRsTgSet(u8ep);
        mUsbEPinRsTgClr(u8ep);
    }
    for (u8ep = 1; u8ep <= FUSB200_MAX_EP; u8ep ++)
    {
        mUsbEPoutRsTgSet(u8ep);
        mUsbEPoutRsTgClr(u8ep);
    }
}


/***********************************************************************/
//      bGet_status()
//      Description:
//          1. Send 2 bytes status to host.
//      input: none
//      output: TRUE or FALSE (BOOLEAN)
/***********************************************************************/
LOCAL BOOLEAN bGet_status(void)
{
    uint8_t RecipientStatusLow;

    RecipientStatusLow = UsbStatus[mDEV_REQ_REQ_RECI() & 0x0F];

    //ZM_CBUS_FIFO_SIZE_REG = 0x3;
    //ZM_EP0_DATA_REG = RecipientStatusLow;

    USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x3);
    USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, RecipientStatusLow);

    // Restore CBus FIFO size to word size
    //ZM_CBUS_FIFO_SIZE_REG = 0xf;
    USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xf);

    eUsbCxFinishAction = ACT_DONE;
    return TRUE;
}

/***********************************************************************/
//      bClear_feature()
//      Description:
//          1. Send 2 bytes status to host.
//      input: none
//      output: TRUE or FALSE (BOOLEAN)
/***********************************************************************/
LOCAL BOOLEAN bClear_feature(void)
{
    if (mDEV_REQ_VALUE() > cUSB_FEATSEL_END)
        return FALSE;

    if ((mDEV_REQ_VALUE() == 0) && (mDEV_REQ_REQ_RECI() != cUSB_REQTYPE_ENDPOINT))
        return FALSE;

    UsbStatus[2] = 0;
    eUsbCxFinishAction = ACT_DONE;

    return TRUE;
}

/***********************************************************************/
//      bSet_feature()
//      Description:
//          1. Send 2 bytes status to host.
//      input: none
//      output: TRUE or FALSE (BOOLEAN)
/***********************************************************************/
#if ZM_SELF_TEST_MODE

#define TEST_J                  0x02
#define TEST_K                  0x04
#define TEST_SE0_NAK            0x08
#define TEST_PKY                0x10

uint16_t TestPatn0[] = { TEST_J, TEST_K, TEST_SE0_NAK };
uint32_t TestPatn1[] = {
    0x00000000, 0x00000000, 0xAA00AA00,         // JKJKJKJK x 9
    0xAAAAAAAA, 0xEEAAAAAA,                     // AA x 8
    0xEEEEEEEE, 0xFEEEEEEE,                     // EE x 8
    0xFFFFFFFF, 0xFFFFFFFF, 0x7FFFFFFF,         // FF x 11
    0xF7EFDFBF, 0x7EFCFDFB, 0xFDFBDFBF};

#endif
LOCAL BOOLEAN bSet_feature(void)
{

    //A_PRINTF("bSet_feature...\n\r");

    switch (mDEV_REQ_VALUE())       // FeatureSelector
    {
        case 0:     // ENDPOINT_HALE
            // AVM Patch:
            // always check RECEIPIENT
            if (mDEV_REQ_REQ_RECI() == cUSB_REQTYPE_ENDPOINT)
            {
                eUsbCxFinishAction = ACT_DONE;
            }
            else
            {
                return FALSE;
            }

            break;

        case 1 :        // Device Remote Wakeup
            // Set "Device_Remote_Wakeup", Turn on the"RMWKUP" bit in Mode Register
            mUsbRmWkupSet();
            //USB_BYTE_REG_WRITE(ZM_MAIN_CTRL_OFFSET, USB_BYTE_REG_READ(ZM_MAIN_CTRL_OFFSET)|BIT0);
            eUsbCxFinishAction = ACT_DONE;
            break;

    #if ZM_SELF_TEST_MODE
        case 2 :        // Test Mode
        //    ii = mDEV_REQ_INDEX() >> 8;
        //    switch (ii)    // TestSelector
            switch (mDEV_REQ_INDEX() >> 8)    // TestSelector
            {
                case 0x1:   // Test_J
                case 0x2:   // Test_K
                case 0x3:   // TEST_SE0_NAK
                //    mUsbTsMdWr(TestPatn0[(mDEV_REQ_INDEX() >> 8) - 1]);
                    //ZM_PHY_TEST_SELECT_REG = TestPatn0[(mDEV_REQ_INDEX() >> 8) - 1];
                    USB_BYTE_REG_WRITE(ZM_PHY_TEST_SELECT_OFFSET, (TestPatn0[(mDEV_REQ_INDEX() >> 8) - 1]));
                    eUsbCxFinishAction = ACT_DONE;
                    break;

                case 0x4:   // Test_Packet
                //    mUsbTsMdWr(TEST_PKY);
                //    mUsbEP0DoneSet();           // special case: follow the test sequence
                    //ZM_PHY_TEST_SELECT_REG = TEST_PKY;
                    //ZM_CX_CONFIG_STATUS_REG = 0x01;
                    USB_BYTE_REG_WRITE(ZM_PHY_TEST_SELECT_OFFSET, TEST_PKY);
                    USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, BIT0);
                    /***********************************************************************///////
                    // Jay ask to modify, 91-6-5 (Begin)        //
                    /***********************************************************************///////
                //    mUsbTsMdWr(TEST_PKY);
                //    mUsbEP0DoneSet();           // special case: follow the test sequence
                    //ZM_PHY_TEST_SELECT_REG = TEST_PKY;
                    USB_BYTE_REG_WRITE(ZM_PHY_TEST_SELECT_OFFSET, TEST_PKY);

                    //ZM_CX_CONFIG_STATUS_REG = 0x01;
                    /***********************************************************************///////
                    // Jay ask to modify, 91-6-5 (Begin)        //
                    /***********************************************************************///////
                    {
                    uint16_t ii;

                        /* Set to two bytes mode */
                        //ZM_CBUS_FIFO_SIZE_REG = 0x0f;
                        USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x0f);

                        for (ii = 0; ii < sizeof(TestPatn1)/sizeof(uint32_t); ii++)
                        {
                            //ZM_EP0_DATA_REG = TestPatn1[ii];
                            USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, TestPatn1[ii]);
                        }

                        /* Set to one byte mode */
                        //ZM_CBUS_FIFO_SIZE_REG = 0x07;
                        //ZM_EP0_DATA_REG = 0x007EFDFB;
                        USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x07);
                        USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, 0x007EFDFB);

                        /* Set to four bytes mode */
                        //ZM_CBUS_FIFO_SIZE_REG = 0x0f;
                        USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x0f);
                    }
                    /***********************************************************************///////
                    // Jay ask to modify, 91-6-5 (End)          //
                    /***********************************************************************///////

                    // Turn on "r_test_packet_done" bit(flag) (Bit 5)
                    //mUsbTsPkDoneSet();
                    //ZM_CX_CONFIG_STATUS_REG = 0x02;
                    USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, BIT1);
                    break;

                case 0x5:   // Test_Force_Enable
                    //FUSBPort[0x08] = 0x20;    //Start Test_Force_Enable
                    break;

                default:
                    return FALSE;
            }
            break;
    #endif
        default :
            return FALSE;
    }

    if (eUsbCxFinishAction == ACT_DONE)
        UsbStatus[2] = 1;

    return TRUE;
}


/***********************************************************************/
//      bSet_address()
//      Description:
//          1. Set addr to FUSB200 register.
//      input: none
//      output: TRUE or FALSE (BOOLEAN)
/***********************************************************************/
LOCAL BOOLEAN bSet_address(void)
{

    //A_PRINTF("bSet_feature...\n\r");

    if (mDEV_REQ_VALUE() >= 0x0100)
        return FALSE;
    else
    {
//        zfUartSendStrAndHex((uint8_t *) "USB_SET_ADDRESS=", mDEV_REQ_VALUE());
        //ZM_DEVICE_ADDRESS_REG = mDEV_REQ_VALUE();
        USB_BYTE_REG_WRITE(ZM_DEVICE_ADDRESS_OFFSET, mDEV_REQ_VALUE());

        eUsbCxFinishAction = ACT_DONE;
        return TRUE;
    }
}

/***********************************************************************/
//      bGet_descriptor()
//      Description:
//          1. Point to the start location of the correct descriptor.
//          2. set the transfer length
//      input: none
//      output: TRUE or FALSE (BOOLEAN)
/***********************************************************************/
LOCAL BOOLEAN bGet_descriptor(void)
{
    //A_PRINTF("bGet_descriptor...\n\r");

// Change Descriptor type
#if 0
    u8ConfigDescriptorEX[mTABLE_IDX(1)] =
        m2BYTE(CONFIG_LENGTH, DT_CONFIGURATION);
    u8OtherSpeedConfigDescriptorEX[mTABLE_IDX(1)] =
        m2BYTE(CONFIG_LENGTH, DT_OTHER_SPEED_CONFIGURATION);
#endif

    //*(volatile uint32_t*)0x1c0004 = 'G';

    switch (mDEV_REQ_VALUE_HIGH())
    {
        case 1:                 // device descriptor
            pu8DescriptorEX = u8UsbDeviceDescriptor;
            u16TxRxCounter = mTABLE_LEN(u8UsbDeviceDescriptor[0]);
            //u16TxRxCounter = 18;
            break;

        case 2:                 // configuration descriptor
                                // It includes Configuration, Interface and Endpoint Table
//            zfUartSendStr((uint8_t *)"Configuration Descriptor\r\n");
            switch (mDEV_REQ_VALUE_LOW())
            {
                case 0x00:      // configuration no: 0
                    pu8DescriptorEX = u8ConfigDescriptorEX;
                    u16TxRxCounter = u8ConfigDescriptorEX[1];
                    //u16TxRxCounter = 46;
                    break;
                default:
                    return FALSE;
            }
            break;

        case 3:                 // string descriptor
                                // DescriptorIndex = low_byte of wValue
//            zfUartSendStr((uint8_t *)"String Descriptor\r\n");
            switch (mDEV_REQ_VALUE_LOW())
            {
                case 0x00:
                    pu8DescriptorEX = u8String00Descriptor;
                    //u16TxRxCounter = 4;
                    break;

                case 0x10:
                    pu8DescriptorEX = u8String10Descriptor;
                    //u16TxRxCounter = 12;
                    break;

                case 0x20:
                    pu8DescriptorEX = u8String20Descriptor;
                    //u16TxRxCounter = 24;
                    break;

                case 0x30:
                    pu8DescriptorEX = u8String30Descriptor;
                    break;

                default:
                    return FALSE;
            }
            u16TxRxCounter = mTABLE_LEN(pu8DescriptorEX[0]);
            break;

        case 6:                     // Device_Qualifier descritor
//            zfUartSendStr((uint8_t *) "Device_Qualifier Descriptor\r\n");
            pu8DescriptorEX = u8DeviceQualifierDescriptorEX;
            u16TxRxCounter = mTABLE_LEN(u8DeviceQualifierDescriptorEX[0]);
            //u16TxRxCounter = 10;
            break;

        case 7:                     // Other_Speed_Configuration
//            zfUartSendStr((uint8_t *)"Other_Speed Descriptor\r\n");
            // It includes Configuration, Interface and Endpoint Table
            pu8DescriptorEX = u8OtherSpeedConfigDescriptorEX;
            u16TxRxCounter = u8OtherSpeedConfigDescriptorEX[1];
            //u16TxRxCounter = 46;
            break;

        default:
//            zfUartSendStrAndHex((uint8_t *) "Descriptor error=", mDEV_REQ_VALUE_HIGH());
            return FALSE;
    }

    if (u16TxRxCounter > mDEV_REQ_LENGTH())
        u16TxRxCounter = mDEV_REQ_LENGTH();

//    vUsbEP0TxData();
    A_USB_EP0_TX_DATA();
    
    // somehow if there is still data need to send out, we shouldn't set CX_DONE
    // wait for another EP0_IN
    if( u16TxRxCounter > 0 )
    {
        eUsbCxCommand = CMD_GET_DESCRIPTOR;
    }

    return TRUE;
}


/***********************************************************************/
//      bGet_configuration()
//      Description:
//          1. Send 1 bytes configuration value to host.
//      input: none
//      output: none
/***********************************************************************/
LOCAL BOOLEAN bGet_configuration(void)
{

    //A_PRINTF("bGet_configuration...\n\r");

    //ZM_CBUS_FIFO_SIZE_REG = 0x1;
    //ZM_EP0_DATA_REG = u8UsbConfigValue;
    USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x1);
    USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, u8UsbConfigValue);

    // Restore CBus FIFO size to word size
    //ZM_CBUS_FIFO_SIZE_REG = 0xf;
    USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xf);

    eUsbCxFinishAction = ACT_DONE;

    return TRUE;
}

/***********************************************************************/
//      bSet_configuration()
//      Description:
//          1. Get 1 bytes configuration value from host.
//          2-1. if (value == 0) then device return to address state
//          2-2. if (value match descriptor table)
//                  then config success & Clear all EP toggle bit
//          2-3  else stall this command
//      input: none
//      output: TRUE or FALSE
/***********************************************************************/
LOCAL BOOLEAN bSet_configuration(void)
{
void vUsbClrEPx(void);

    //A_PRINTF("bSet_configuration...\n\r");

    if (mLOW_BYTE(mDEV_REQ_VALUE()) == 0)
    {
        u8UsbConfigValue = 0;
        //mUsbCfgClr();
        //ZM_DEVICE_ADDRESS_REG &= ~BIT7;
        USB_BYTE_REG_WRITE(ZM_DEVICE_ADDRESS_OFFSET, (USB_BYTE_REG_READ(ZM_DEVICE_ADDRESS_OFFSET)&~BIT7));
    }
    else
    {
        if (mUsbHighSpeedST())                  // First judge HS or FS??
        {
            if (mLOW_BYTE(mDEV_REQ_VALUE()) > HS_CONFIGURATION_NUMBER)
                return FALSE;

            u8UsbConfigValue = mLOW_BYTE(mDEV_REQ_VALUE());
            vUsbFIFO_EPxCfg_HS();

            // Set into 512 byte mode */
            //ZM_SOC_USB_MODE_CTRL_REG |= BIT2;
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                    (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT2));
        //    mUsbSOFMaskHS();
        }
        else
        {
            if (mLOW_BYTE(mDEV_REQ_VALUE()) > FS_CONFIGURATION_NUMBER)
                return FALSE;

            u8UsbConfigValue = mLOW_BYTE(mDEV_REQ_VALUE());
            vUsbFIFO_EPxCfg_FS();

            // Set into 64 byte mode */
            //M_SOC_USB_MODE_CTRL_REG &= ~BIT2;
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&~BIT2));
        //    mUsbSOFMaskFS();
        }
        //mUsbCfgSet();
        //ZM_DEVICE_ADDRESS_REG |= BIT7;
        USB_BYTE_REG_WRITE(ZM_DEVICE_ADDRESS_OFFSET, \
            (USB_BYTE_REG_READ(ZM_DEVICE_ADDRESS_OFFSET)|BIT7));

        vUsbClrEPx();

        mUsbGlobIntEnable();
        mUSB_REG_OUT_INT_ENABLE();

    }

    eUsbCxFinishAction = ACT_DONE;
    return TRUE;
}


/***********************************************************************/
//      bGet_interface()
//      Description:
//          Getting interface
//      input: none
//      output: TRUE or FALSE
/***********************************************************************/
LOCAL BOOLEAN bGet_interface(void)
{

//    A_PRINTF("bGet_interface...\n\r");
    if (mUsbCfgST() == 0)
        return FALSE;

    // If there exists many interfaces, Interface0,1,2,...N,
    // You must check & select the specific one
    switch (u8UsbConfigValue)
    {
        #if (HS_CONFIGURATION_NUMBER >= 1)
        // Configuration 1
        case 1:
            if (mDEV_REQ_INDEX() > HS_C1_INTERFACE_NUMBER)
                return FALSE;
            break;
        #endif
        #if (HS_CONFIGURATION_NUMBER >= 2)
        // Configuration 2
        case 2:
            if (mDEV_REQ_INDEX2() > HS_C2_INTERFACE_NUMBER)
                return FALSE;
            break;
        #endif
        default:
            return FALSE;
    }

    //ZM_CBUS_FIFO_SIZE_REG = 0x1;
    //ZM_EP0_DATA_REG = u8UsbInterfaceAlternateSetting;
    USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x1);
    USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, u8UsbInterfaceAlternateSetting);

    // Restore CBus FIFO size to word size
    //ZM_CBUS_FIFO_SIZE_REG = 0xf;
    USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x0f);

    u16TxRxCounter = 1; //sizeof(u8UsbInterfaceAlternateSetting);
    eUsbCxFinishAction = ACT_DONE;
    return TRUE;
}

/***********************************************************************/
//      bSet_interface()
//      Description:
//          1-1. If (the device stays in Configured state)
//                  &(command match the alternate setting)
//                      then change the interface
//          1-2. else stall it
//      input: none
//      output: TRUE or FALSE
/***********************************************************************/
LOCAL BOOLEAN bSet_interface(void)
{
void vUsbClrEPx(void);

    //A_PRINTF("bSet_interface...\n\r");

    if (mUsbCfgST())
    {

        // If there exists many interfaces, Interface0,1,2,...N,
        // You must check & select the specific one
        switch (mDEV_REQ_INDEX())
        {
            case 0: // Interface0

                if (mLOW_BYTE(mDEV_REQ_VALUE()) == mLOW_BYTE(u8ConfigDescriptorEX[mTABLE_IDX(12)]))
                {
                    u8UsbInterfaceValue = (uint8_t) mDEV_REQ_INDEX();
                    u8UsbInterfaceAlternateSetting = mLOW_BYTE(mDEV_REQ_VALUE());
                    if (mUsbHighSpeedST())                  // First judge HS or FS??
                    {
                        vUsbFIFO_EPxCfg_HS();

                        // Set into 512 byte mode */
                        USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                            (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT2));
                    }
                    else
                    {
                        vUsbFIFO_EPxCfg_FS();

                        // Set into 64 byte mode */
                        USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                            (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&~BIT2));
                    }
                    vUsbClrEPx();
                    eUsbCxFinishAction = ACT_DONE;

                    mUsbGlobIntEnable();
                    mUSB_REG_OUT_INT_ENABLE();
                    return TRUE;
                }
        //    case 1: // Interface1
        //    case 2: // Interface2
        //    default:
        //        break;
        }
    }
    return FALSE;
}

/***********************************************************************/
//      vUsbEP0TxData()
//      Description:
//          1. Send data(max or short packet) to host.
//      input: none
//      output: none
/***********************************************************************/
LOCAL void vUsbEP0TxData(void)
{
    uint8_t u8temp;
    uint32_t idx=0;
  
    //wait a little to make sure ep0 fifo is empty before sending data out
    while(1)
    {
        if(idx++>0xffff) {
            USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, USB_BYTE_REG_READ(ZM_CX_CONFIG_STATUS_OFFSET)|BIT3);
            break;
        }

        if(USB_BYTE_REG_READ(ZM_CX_CONFIG_STATUS_OFFSET)&BIT5)
        {
            break;
        }
    }
    // to keep tracking the txrx fifo
    // max 64 bytes for transmission one time,
    if (u16TxRxCounter < EP0MAXPACKETSIZE)
        u8temp = (uint8_t) u16TxRxCounter;
    else
        u8temp = EP0MAXPACKETSIZE;

    u16TxRxCounter -= (uint16_t) u8temp;

    {
        register uint8_t u8count;
        uint8_t remainder;

        for (u8count = 0; u8count < (u8temp/4); u8count ++)
        {
            uint32_t ep0_data;
            uint16_t ep0_low;
            uint16_t ep0_high;

            // pack data into word size
            ep0_low = *pu8DescriptorEX++;
            ep0_high = *pu8DescriptorEX++;

            // composed the data as a word
            ep0_data = (ep0_high << 16) + ep0_low;

            USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, ep0_data);
        }

        remainder = u8temp % 4;

        // Check whether there are data needed to be filled into the FIFO
        if (remainder == 3)
        {
            uint32_t ep0_data;
            uint16_t ep0_low;
            uint16_t ep0_high;

            // pack data into word size
            ep0_low = *pu8DescriptorEX++;
            ep0_high = *pu8DescriptorEX++;

            ep0_data = (ep0_high << 16) + ep0_low;

            USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x7);
            USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, ep0_data);
        }
        else if (remainder == 2)
        {
            USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x3);
            USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, *pu8DescriptorEX);
        }
        else if (remainder == 1)
        {
            USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x1);
            USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, *pu8DescriptorEX);
        }

        // Restore CBus FIFO size to word size
        USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xf);
    }

    // end of the data stage
    if (u16TxRxCounter == 0)
    {
        eUsbCxCommand = CMD_VOID;
        eUsbCxFinishAction = ACT_DONE;
    }
}

/***********************************************************************/
//      vUsbEP0RxData()
//      Description:
//          1. Receive data(max or short packet) from host.
//      input: none
//      output: none
/***********************************************************************/
LOCAL void vUsbEP0RxData(void)
{
    uint8_t u8temp;

    if (u16TxRxCounter < EP0MAXPACKETSIZE)
        u8temp = (uint8_t) u16TxRxCounter;
    else
        u8temp = EP0MAXPACKETSIZE;

    u16TxRxCounter -= (uint16_t) u8temp;

    // Receive u8Temp bytes data
    {
    register uint8_t u8count;
    uint8_t *p = (uint8_t *) pu8DescriptorEX;

        for (u8count = 0; u8count < ((u8temp+3) >> 2); u8count ++)
        {
            uint32_t ep0_data;

            ep0_data = USB_WORD_REG_READ(ZM_EP0_DATA_OFFSET);   //read usb ep0 fifo data,

            {
// skip the writing to ram if not build for rom code
#if 0 //1 defined(_ROM_)
                *p++ = mGetByte0(ep0_data);
                *p++ = mGetByte1(ep0_data);
                *p++ = mGetByte2(ep0_data);
                *p++ = mGetByte3(ep0_data);
#endif
                fwCheckSum = fwCheckSum ^ ep0_data;
             }
        }

        pu8DescriptorEX += (u8count << 1);
    }

    // end of the data stage
    if (u16TxRxCounter == 0)
    {
        eUsbCxCommand = CMD_VOID;
        eUsbCxFinishAction = ACT_DONE;
    }
}


/***********************************************************************/
//      vUsb_SetupDescriptor()
//      Description:
//          Setup the pointer to the descriptor in the SRAM and EEPROM
//
/***********************************************************************/
LOCAL void vUsb_SetupDescriptor(void)
{
// eeprom exist the usb configuration is only supportted in rom version
#if defined(_ROM_)
    //
    // check the offset of PID's value is correct or not, need to be defined!!, ryan
    //

    if( *((uint32_t*)USB_DESC_IN_EEPROM_FLAG_ADDR) == USB_DESC_IN_EEP_PATTERN)
    {
        A_PRINTF("- custom usb config\n");

        u8UsbDeviceDescriptor = (uint16_t *) USB_DEVICE_DESCRIPTOR_ADDR;
        u8String00Descriptor = (uint16_t *) USB_STRING00_DESCRIPTOR_ADDR;
        u8String10Descriptor = (uint16_t *) USB_STRING10_DESCRIPTOR_ADDR;
        u8String20Descriptor = (uint16_t *) USB_STRING20_DESCRIPTOR_ADDR;
        u8String30Descriptor = (uint16_t *) USB_STRING30_DESCRIPTOR_ADDR;
    }
    else
#endif
    {
        u8UsbDeviceDescriptor = (uint16_t *) &UsbDeviceDescriptor;
        u8String00Descriptor = (uint16_t *) &String00Descriptor;
        u8String10Descriptor = (uint16_t *) &String10Descriptor;
        u8String20Descriptor = (uint16_t *) &String20Descriptor;
        u8String30Descriptor = (uint16_t *) &String30Descriptor;
    }

    /* Point Device Qualifierdescriptors and Other Speed Descriptor
	 *  - Device Qualifierdescriptor is located in RAM segment, extern these
	 *    symbol at the beginning of this file
     */
}


/***********************************************************************/
//      bStandardCommand()
//      Description:
//          1. Process standard command.
//      input: none
//      output: TRUE or FALSE
/***********************************************************************/
LOCAL BOOLEAN bStandardCommand(void)
{
    switch (mDEV_REQ_REQ())                 // by Standard Request codes
    {
        case USB_GET_STATUS:
            return (A_USB_GET_STATUS());

        case USB_CLEAR_FEATURE:
            return (A_USB_CLEAR_FEATURE());

        case USB_SET_FEATURE:
            return (A_USB_SET_FEATURE());

        case USB_SET_ADDRESS:
            return (A_USB_SET_ADDRESS());

        case USB_GET_DESCRIPTOR:
            return (A_USB_GET_DESCRIPTOR());

#if 0
        case USB_SET_DESCRIPTOR:
//            if (!bUsbEP0HaltSt)
            return (bSet_descriptor());
#endif

        case USB_GET_CONFIGURATION:
            return (A_USB_GET_CONFIG());

        case USB_SET_CONFIGURATION:
            //A_PRINTF(" \n--> SET_CONFIGURATION\r\n");
//            if (!bUsbEP0HaltSt)
//            	return (A_USB_SET_CONFIG());

        {
            A_USB_SET_CONFIG();

#if ENABLE_SWAP_DATA_MODE
            // SWAP FUNCTION should be enabled while DMA engine is not working,
            // the best place to enable it is before we trigger the DMA
            MAGPIE_REG_USB_RX0_SWAP_DATA = 0x1;
            MAGPIE_REG_USB_TX0_SWAP_DATA = 0x1;

        #if SYSTEM_MODULE_HP_EP5
            MAGPIE_REG_USB_RX1_SWAP_DATA = 0x1;
        #endif

        #if SYSTEM_MODULE_HP_EP6
            MAGPIE_REG_USB_RX2_SWAP_DATA = 0x1;
        #endif

#endif //ENABLE_SWAP_DATA_MODE


#if !ENABLE_STREAM_MODE
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT3);

 /*
 // ryan:
 // 04/01: bit0 could disable lpdn dma, which is good at debugging while async_fifo have problem,
 //            we could disable this and check the fifo_rcv_size to see if we have correct at fifo or not
 */
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, ((USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT1))); // upstream DMA enable
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, ((USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT0))); // downstream DMA enable

        #if SYSTEM_MODULE_HP_EP5
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, ((USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT8)));
        #endif

        #if SYSTEM_MODULE_HP_EP6
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, ((USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT9)));
        #endif

#else
/////////////ENABLE_STREAM_MODE/////////////////
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT1)));  // disable upstream DMA mode
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT3)));  // enable upstream stream mode
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET,
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|(BIT1)));    // enable upstream DMA mode

        #if SYSTEM_MODULE_HP_EP1
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT0)));  // diable LP downstream DMA mode
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|(BIT6)));    // enable LP downstream stream mode
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|(BIT0)));   // enable LP downstream DMA mode
        #endif

        #if SYSTEM_MODULE_HP_EP5
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT8)));     // disable HP downstream DMA mode
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|(BIT7)));    // enable HP downstream stream mode
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT8));     // enable HP downstream DMA mode
        #endif


        #if SYSTEM_MODULE_HP_EP6
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)&(~BIT9)));    // disable MP downstream DMA mode
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT10));      // enable MP downstream stream mode
            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|BIT9));    // enable MP downstream DMA mode
        #endif

            USB_WORD_REG_WRITE(ZM_SOC_USB_MODE_CTRL_OFFSET, \
                (USB_WORD_REG_READ(ZM_SOC_USB_MODE_CTRL_OFFSET)|(BIT4)));   // define the host dma buffer size - 4096(00) 8192 (01) 16384(10) 32768(11) bytes

            USB_WORD_REG_WRITE(ZM_SOC_USB_TIME_CTRL_OFFSET, USB_STREAM_MODE_TIMEOUT_CTRL);  // set stream mode timeout critirea

            USB_WORD_REG_WRITE(ZM_SOC_USB_MAX_AGGREGATE_OFFSET, USB_STREAM_MODE_AGG_CNT); // set stream mode packet buffer critirea
#endif  //!ENABLE_STREAM_MODE



//extern void Magpie_init(void);
//Magpie_init();

            return TRUE;
        }

        case USB_GET_INTERFACE:
//            A_PRINTF(" \n--> GET_INTERFACE\r\n");
//            if (!bUsbEP0HaltSt)
                //return (bGet_interface());
            return (A_USB_GET_INTERFACE());

        case USB_SET_INTERFACE:
//            A_PRINTF(" \n--> SET_INTERFACE\r\n");
//            if (!bUsbEP0HaltSt)
//          return (bSet_interface());
//          return (A_USB_SET_INTERFACE());
            A_USB_SET_INTERFACE();
            return TRUE;
    }
    return FALSE;
}


LOCAL void flash_read(uint16_t len, uint16_t ofset)
{
    uint16_t i=0;
    
    uint8_t buf[64];
    uint16_t end_addr = 0x0;
    uint16_t start_addr = 0x0;
    uint32_t ep0_data = 0x0;

#if 0    
    //sanity check, just in case
    if(u16TxRxCounter < EP0MAXPACKETSIZE)
        u8temp = (uint8_t) u16TxRxCounter;
    else

    if( u16TxRxCounter > 64 )
        len = EP0MAXPACKETSIZE;
    else
        len = u16TxRxCounter + 4-(u16TxRxCounter%4);
#endif

    start_addr = ofset;
    end_addr = start_addr + len;

    A_PRINTF("read flash from %x to %x\n", ofset, end_addr);

    USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xF);
    
    for (i = 0; start_addr < end_addr; i++, start_addr+=4)
    {
//        A_SFLASH_READ(1, ofset, 4, buf + i*4);
//        *((volatile uint32_t *)(buf+i*4)) = *(uint32_t *)(0xf000000+start_addr);
//    A_PRINTF(" %08x ", *(uint32_t *)(0xf000000+start_addr));
    USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, *(uint32_t *)(0xf000000+start_addr));
    }

//    A_PRINTF("\n\n\r");    
    USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, BIT0);




#if 0    
     USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xF);
            
    for(i=0; i<len; i+4)
    {
        ep0_data = *(uint32_t *)(buf+i);

        USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, ep0_data);
    }

    USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xF);

    USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, BIT0); 
#endif
}

extern BOOLEAN download_enable;

LOCAL void VendorCommand(void)
{
#define cUSB_REQ_DOWNLOAD          0x30
#define cUSB_REQ_DOWNLOAD_COMP     0x31
#define cUSB_REQ_BOOT              0x32
#define cUSB_REQ_RESERVED_1        0x33
#define cUSB_REQ_RESERVED_2        0x34

#define cUSB_REQ_FLASH_READ        0x35
#define cUSB_REQ_FLASH_READ_COMP   0x36

//#define ZM_FIRMWARE_ADDR           0x200000

    void (*funcPtr)(void);
    uint16_t *text_addr = 0;
    uint32_t ep0_data = 0x0;
//    static download_enable = FALSE;
    
    CURRENT_PROGRAM = (uint32_t)VendorCommand;

    switch (mDEV_REQ_REQ())
    {
        case cUSB_REQ_FLASH_READ:
            
            ep0_data = *(uint32_t *)(0xf000000);
        
            u16TxRxCounter = mDEV_REQ_LENGTH();
            pu8DescriptorEX = (uint16_t*)( (mDEV_REQ_VALUE()));
 
//            A_PRINTF("Get a flash_read (%x) request with lenght:%d, and offset %x...\n", cUSB_REQ_FLASH_READ, u16TxRxCounter, pu8DescriptorEX);

//            eUsbCxCommand = CMD_GET_CUSTOM_DATA;

#if 1
            flash_read(u16TxRxCounter, (uint16_t)pu8DescriptorEX);
#else
            eUsbCxCommand = CMD_GET_CUSTOM_DATA;
            USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, ep0_data);
            USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xF);
            USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, BIT0);
#endif
            break;
            
        case cUSB_REQ_FLASH_READ_COMP:
        
            ep0_data = *(uint32_t *)(0xf000004);
            A_PRINTF("get a upload complete request...\n");        
            
            //eUsbCxCommand = CMD_SET_DESCRIPTOR;
//                USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x1);
                USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, ep0_data);
                USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xF);
            	USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, BIT0);
            
            //download_enable = TRUE;

            break;

        case cUSB_REQ_DOWNLOAD:
            //if( download_enable )
            {
                u16TxRxCounter = mDEV_REQ_LENGTH();
                pu8DescriptorEX = (uint16_t*)( (mDEV_REQ_VALUE() << 8));
                A_PRINTF("\t[cUSB_REQ_DOWNLOAD]: 0x%08x, %02x\n\r", pu8DescriptorEX, u16TxRxCounter);

                eUsbCxCommand = CMD_SET_DESCRIPTOR;
                
            }
//            else
//                A_PRINTF("firmware download deny!!\n\r");
            break;

        case cUSB_REQ_DOWNLOAD_COMP:
            
            text_addr = (uint16_t*)( (mDEV_REQ_VALUE() << 8));
            A_PRINTF("\t\n\r==>[cUSB_REQ_COMP]: 0x%08x\n\r", text_addr);
#if 0
            if (fwCheckSum != 0)
            {
                A_PRINTF("cksum=%x", fwCheckSum);
                fwCheckSum = 0;
                //Return fail
                DEBUG_SYSTEM_STATE |= BIT27;

                USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x1);
                USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, 1);
                USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xF);
                USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, BIT0);
            }
            else
#endif
            {
                /* Set EP0 Done */
                //ZM_CX_CONFIG_STATUS_REG = 0x01;
                fwCheckSum = 0;
                USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x1);
                USB_WORD_REG_WRITE(ZM_EP0_DATA_OFFSET, 0);
                USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xF);
            	USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, BIT0);

                A_PRINTF("VendorCmd: DownloadComplete!\n");

				DEBUG_SYSTEM_STATE &= ~BIT27;
                DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x3f;

                // this value should be assign from host along with the DOWNLOAD_COMP in wValue
                if( text_addr != 0 )
                    funcPtr = (void *)(text_addr);

                download_enable = TRUE;

				// only jump to text address in ROM version
				#if defined(_ROM_)
                //    funcPtr();    // jump to the firmware and never return
				#endif
                //app_start();
			}
//            else
//                A_PRINTF("Integrity is not fine!\n\r");

            break;
    }
}


/***********************************************************************/
//      vUsb_ep0setup()
//      Description:
//          1. Read 8-byte setup packet.
//          2. Decode command as Standard, Class, Vendor or NOT support command
//      input: none
//      output: none
/***********************************************************************/
extern uint16_t u8HSConfigDescriptor01[];
extern uint16_t u8FSConfigDescriptor01[];

LOCAL void vUsb_ep0setup(void)
{
register uint8_t ii;
volatile uint32_t ep0_data;
//BOOLEAN bStandardCommand(void);
//BOOLEAN bClassCommand(void);
//void VendorCommand(void);

    //zcPrint._printf("\t---> %s <---\n\r", __FUNCTION__);
    if (UsbChirpFinish != TRUE)
    {
        UsbChirpFinish = TRUE;

        // Setup Descriptor pointer
        //vUsb_SetupDescriptor();
        A_USB_SETUP_DESC();

        u8OtherSpeedConfigDescriptorEX[0] = 0x0709;

        if (mUsbHighSpeedST())                  // Judge HS or FS??
        {
            u8ConfigDescriptorEX = u8HSConfigDescriptor01;

        // copy Device Qualifierdescriptors (from rom to sram)
            for (ii = 1; ii < 4; ii++)
            {
                u8DeviceQualifierDescriptorEX[ii] = u8UsbDeviceDescriptor[ii];
            }

        // Number of Other-speed Configurations
        // byte 9 Reserved for future use, must be zero
            u8DeviceQualifierDescriptorEX[4] = (u8UsbDeviceDescriptor[8] >> 8) & 0x00ff;

         // copy Other Speed Descriptor
            for (ii = 1; ii < (USB_TOTAL_DESC_LEN/2); ii++)
            {
                u8OtherSpeedConfigDescriptorEX[ii] = u8FSConfigDescriptor01[ii];
            }

#if 0
            MaxPktSize = HS_C1_I0_A0_EP1_MAX_PACKET;
        // Device stays in High Speed
            u8DeviceDescriptorEX = u8HSDeviceDescriptor;

        // copy Device Qualifierdescriptors (from rom to sram)
            for (ii = mTABLE_WID(2) ; ii < mTABLE_WID(8); ii ++)
                u8DeviceQualifierDescriptorEX[ii] = u8FSDeviceDescriptor[ii];

        // Number of Other-speed Configurations
        // byte 9 Reserved for future use, must be zero
            u8DeviceQualifierDescriptorEX[mTABLE_IDX(8)]
                = mHIGH_BYTE(u8FSDeviceDescriptor[mTABLE_IDX(17)]);
            u8ConfigDescriptorEX = u8HSConfigDescriptor01;
            u8OtherSpeedConfigDescriptorEX = u8FSConfigDescriptor01;
#endif
        }
        else
        {
            u8ConfigDescriptorEX = u8FSConfigDescriptor01;

        // copy Device Qualifierdescriptors (from rom to sram)
            for (ii = 1; ii < 4; ii++)
            {
                u8DeviceQualifierDescriptorEX[ii] = u8UsbDeviceDescriptor[ii];
            }

        // Number of Other-speed Configurations
        // byte 9 Reserved for future use, must be zero
            u8DeviceQualifierDescriptorEX[4] = (u8UsbDeviceDescriptor[8] >> 8) & 0x00ff;

         // copy Other Speed Descriptor
            for (ii = 1; ii < (USB_TOTAL_DESC_LEN/2); ii++)
            {
                u8OtherSpeedConfigDescriptorEX[ii] = u8HSConfigDescriptor01[ii];
            }

#if 0
            MaxPktSize = FS_C1_I0_A0_EP1_MAX_PACKET;
        // Device stays in Full Speed
            u8DeviceDescriptorEX = u8FSDeviceDescriptor;

        // copy Device Qualifierdescriptors (from rom to sram)
            for (ii = mTABLE_WID(2) ; ii < mTABLE_WID(8); ii ++)
                u8DeviceQualifierDescriptorEX[ii] = u8HSDeviceDescriptor[ii];

        // Number of Other-speed Configurations
        // byte 9 Reserved for future use, must be zero
            u8DeviceQualifierDescriptorEX[mTABLE_IDX(8)]
                = mHIGH_BYTE(u8HSDeviceDescriptor[mTABLE_IDX(17)]);
            u8ConfigDescriptorEX = u8FSConfigDescriptor01;
            u8OtherSpeedConfigDescriptorEX = u8HSConfigDescriptor01;
#endif
        }
     //Change bLength
        u8DeviceQualifierDescriptorEX[0] = 0x060A;
    }

    if( USB_BYTE_REG_READ(ZM_CX_CONFIG_STATUS_OFFSET) & BIT5)
    {
        int kkk=0;
        kkk++;
    }
    //ep0_data = ZM_EP0_DATA_REG;
    ep0_data = USB_WORD_REG_READ(ZM_EP0_DATA_OFFSET);

    ii = mGetByte0(ep0_data);

    ControlCmd.Direction = (uint8_t)(ii & 0x80);// xfer Direction(IN, OUT)
    ControlCmd.Type = (uint8_t)(ii & 0x60);     // type(Standard, Class, Vendor)
    ControlCmd.Object = (uint8_t)(ii & 0x03);   // Device, Interface, Endpoint

    ControlCmd.Request = mGetByte1(ep0_data);
    ControlCmd.Value = mGetByte2(ep0_data) + (mGetByte3(ep0_data) << 8);

    //ep0_data = ZM_EP0_DATA_REG;
    ep0_data = USB_WORD_REG_READ(ZM_EP0_DATA_OFFSET);

    ControlCmd.Index = mGetByte0(ep0_data) + (mGetByte1(ep0_data) << 8);
    ControlCmd.Length = mGetByte2(ep0_data) + (mGetByte3(ep0_data) << 8);

//  Command Decode
    if (mDEV_REQ_REQ_TYPE() == (cUSB_REQTYPE_STD << bmREQ_TYPE))
    {                                       // standard command
        //if (bStandardCommand() == FALSE)
        if (A_USB_STANDARD_CMD() == FALSE)
        {
            eUsbCxFinishAction = ACT_STALL;
        }
    }
    else if (mDEV_REQ_REQ_TYPE() == (cUSB_REQTYPE_VENDOR << bmREQ_TYPE))
    {                                       // vendor command
        //VendorCommand();
        A_USB_VENDOR_CMD();
    }
    else
    {
    // Invalid(bad) command, Return EP0_STALL flag
        A_PRINTF("request not support..  stall", __FUNCTION__);
        eUsbCxFinishAction = ACT_STALL;
    }

    //zcPrint._printf("\t<--- %s --->\n\r", __FUNCTION__);
}


/*! - init FUSB phy
 *
 */
LOCAL void cFUSB200Init(void)
{
    /* Clear USB reset interrupt */
    USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_OFFSET, (USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_OFFSET)&0xfd));

    // Disable all fifo interrupt
    /* Clear all USB OUT FIFO */
    USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_1_OFFSET, 0xff);
    USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_2_OFFSET, 0xff);
    USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_3_OFFSET, 0xff);

    /* Clear all USB IN FIFO */
    USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_5_OFFSET, 0xff);
    USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_6_OFFSET, 0xff);

    // Soft Reset
    //ZM_MAIN_CTRL_REG = 0x10;
    //ZM_MAIN_CTRL_REG &= ~0x10;

    // Soft Reset
    USB_BYTE_REG_WRITE(ZM_MAIN_CTRL_OFFSET, 0x10);
    USB_BYTE_REG_WRITE(ZM_MAIN_CTRL_OFFSET, 0x0);

    // Clear all fifo
    USB_BYTE_REG_WRITE(ZM_TEST_OFFSET, BIT0); // will be cleared after one cycle.
    USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_0_OFFSET, 0); //BIT6);  // Mask out INT status

    // reset the specific mode
    USB_BYTE_REG_WRITE(ZM_VDR_SPECIFIC_MODE_OFFSET, 0x0);

    // reset the zero-length fifo indication ? workaround...
    USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_OFFSET, 0x0);

    // Enable Chip
    USB_BYTE_REG_WRITE(ZM_MAIN_CTRL_OFFSET, (BIT5|BIT2));

    USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_1_OFFSET, 0x0);
    USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_2_OFFSET, 0x0);
    USB_BYTE_REG_WRITE(ZM_INTR_MASK_BYTE_3_OFFSET, 0x0);

//    USB_WORD_REG_WRITE(0x104, 0x000000C0);

}


LOCAL void _usbfifo_enable_event_isr(void)
{
    mUSB_STATUS_IN_INT_ENABLE();
}

LOCAL void _usbfifo_init(USB_FIFO_CONFIG *pConfig) 
{
    usbFifoConf.get_command_buf = pConfig->get_command_buf;
    usbFifoConf.recv_command    = pConfig->recv_command;
    usbFifoConf.get_event_buf   = pConfig->get_event_buf;
    usbFifoConf.send_event_done = pConfig->send_event_done;
}

LOCAL void vUsb_Reg_Out(void)
{
    uint16_t usbfifolen;
    uint16_t ii;
    volatile uint32_t *regaddr;    // = (volatile uint32_t *) ZM_CMD_BUFFER;
    uint16_t cmdLen;
    uint32_t ep4_data;
    VBUF *buf;

    //mUSB_REG_OUT_INT_DISABLE();

    buf = usbFifoConf.get_command_buf();

    if ( buf != NULL )     // copy free
        regaddr = (uint32_t *)buf->desc_list->buf_addr;
    else
        goto ERR;

    // read fifo size of the current packet.
    usbfifolen = USB_BYTE_REG_READ(ZM_EP4_BYTE_COUNT_LOW_OFFSET);

    cmdLen = usbfifolen;

    if(usbfifolen % 4)
        usbfifolen = (usbfifolen >> 2) + 1;
    else
        usbfifolen = usbfifolen >> 2;

    for(ii = 0; ii < usbfifolen; ii++)
    {
        ep4_data = USB_WORD_REG_READ(ZM_EP4_DATA_OFFSET);   // read fifo data out
        *regaddr = ep4_data;
        regaddr++;
    }

    if ( buf != NULL )
    {
//        zfUartSendStrAndHex((u8_t *) "cmdLen=", cmdLen);
//        zfMemoryCopyInWord(buf->desc_list->buf_addr, ZM_CMD_BUFFER, usbfifolen*4);
        buf->desc_list->next_desc = NULL;
        buf->desc_list->data_offset = 0;
        buf->desc_list->data_size = cmdLen;
        buf->desc_list->control = 0;
        buf->next_buf = NULL;
        buf->buf_length = cmdLen;

        usbFifoConf.recv_command(buf);
    }
    goto DONE;
ERR:
//    we might get no command buffer here?
//    but if we return here, the ep4 fifo will be lock out,
//    so that we still read them out but just drop it ?
    for(ii = 0; ii < usbfifolen; ii++)
    {
        ep4_data = USB_WORD_REG_READ(ZM_EP4_DATA_OFFSET);   // read fifo data out
    }

DONE:
    //mUSB_STATUS_IN_INT_ENABLE();

}

LOCAL void vUsb_Status_In(void)
{
    uint16_t count;
    uint16_t remainder;
    volatile u32_t *regaddr;
    u16_t RegBufLen;
    VBUF *evntbuf = NULL;

    //regaddr = (volatile uint32_t *) ZM_CMD_BUFFER;

    //mUSB_STATUS_IN_INT_DISABLE();

    evntbuf = usbFifoConf.get_event_buf();
    if ( evntbuf != NULL )
    {
//zfUartSendStr((u8_t *) "#G1\r\n");
//        A_PRINTF("#G1\n\r");
        regaddr = VBUF_GET_DATA_ADDR(evntbuf);
        RegBufLen = evntbuf->buf_length;
//        A_PRINTF("RegBufLen=%d\n\r", RegBufLen);
//zfUartSendStrAndHex((u8_t *) "RegBufLen=", RegBufLen);
    }
    else
    {
        mUSB_STATUS_IN_INT_DISABLE();
//        A_PRINTF("#G2\n\r");
        goto ERR_DONE;
    }

    /* INT use EP3 */
    for(count = 0; count < (RegBufLen / 4); count++)
    {
//zfUartSendStrAndHex((u8_t *) "data=", *regaddr);
        USB_WORD_REG_WRITE(ZM_EP3_DATA_OFFSET, *regaddr);
        regaddr++;
    }

    remainder = RegBufLen % 4;

    if (remainder)
    {
        switch(remainder)
        {
        case 3:
            USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x7);
            break;
        case 2:
            USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x3);
            break;
        case 1:
            USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x1);
            break;
        }

        USB_WORD_REG_WRITE(ZM_EP3_DATA_OFFSET, *regaddr);
    }

    // Restore CBus FIFO size to word size
    USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0xF);

    mUSB_EP3_XFER_DONE();

    if ( evntbuf != NULL )
    {
        usbFifoConf.send_event_done(evntbuf);
    }

ERR_DONE:
    //mUSB_REG_OUT_INT_ENABLE();
}

/////////////////////////////////////////////////////////
/***********************************************************************/
//      zfResetUSBFIFO()
//      Description:
//          1. Reset all the USB FIFO used for WLAN
//      input: none
//      output: none
/***********************************************************************/
LOCAL void zfResetUSBFIFO(void)
{
    A_PUTS("zfResetUSBFIFO\n\r");

}

/***********************************************************************/
//      zfTurnOffPower()
//      Description:
//          1. Function to turn off ADDA/RF power, PLL
//      input: none
//      output: none
/***********************************************************************/
LOCAL void zfTurnOffPower(void)
{
    A_PUTS("zfTurnOffPower\n\r");
#if defined(MAGPIE_ASIC)
/*
 *  1. set CPU bypass
 *  2. turn off CPU PLL
 *  3. turn off ETH PLL
 *  4. disable ETH PLL bypass and update
 *  5. set SUSPEND_ENABLE
 */

    /*HAL_WORD_REG_WRITE(MAGPIE_REG_USB_DIVIDE_ADDR,((0x8<<8)|0x8));  */
    /* 1. */ HAL_WORD_REG_WRITE(MAGPIE_REG_CPU_PLL_BYPASS_ADDR,
                (HAL_WORD_REG_READ(MAGPIE_REG_CPU_PLL_BYPASS_ADDR)|(BIT0|BIT4)));
             A_DELAY_USECS(100); // wait for stable

    /* 2. */ HAL_WORD_REG_WRITE(MAGPIE_REG_CPU_PLL_ADDR,
                (HAL_WORD_REG_READ(MAGPIE_REG_CPU_PLL_ADDR)|(BIT16)));
    
    /* 3. */ HAL_WORD_REG_WRITE(MAGPIE_REG_ETH_PLL_ADDR,
                (HAL_WORD_REG_READ(MAGPIE_REG_ETH_PLL_ADDR)|(BIT16)));

    /* 4. */ HAL_WORD_REG_WRITE(MAGPIE_REG_ETH_PLL_BYPASS_ADDR,
                (HAL_WORD_REG_READ(MAGPIE_REG_ETH_PLL_BYPASS_ADDR)|(BIT16|BIT0)));
                
    /* 5. */ HAL_WORD_REG_WRITE(MAGPIE_REG_SUSPEND_ENABLE_ADDR,
                (HAL_WORD_REG_READ(MAGPIE_REG_SUSPEND_ENABLE_ADDR)|(BIT0)));
#endif

}


LOCAL void zfGenWatchDogEvent(void)
{
    uint32_t event= 0x0000C600;

    mUSB_STATUS_IN_INT_DISABLE();

    //ZM_CBUS_FIFO_SIZE_REG = 0xf;
    USB_WORD_REG_WRITE(ZM_CBUS_FIFO_SIZE_OFFSET, 0x0f);

    //ZM_EP3_DATA_REG = event;
    USB_WORD_REG_WRITE(ZM_EP3_DATA_OFFSET, event);

    mUSB_EP3_XFER_DONE();
}

LOCAL void zfJumpToBootCode(void)
{
    extern int _start(void);

    /* Jump to the boot code */
    _start();
}

LOCAL void _usb_rom_task(void)
{
    register uint8_t usb_interrupt_level1;
    register uint8_t usb_interrupt_level2;
    register uint8_t usb_ctrl_err_indication;

    usb_interrupt_level1 = USB_BYTE_REG_READ(ZM_INTR_GROUP_OFFSET);

    if (usb_interrupt_level1 & BIT6)
    {
        A_USB_GEN_WDT();
        A_PRINTF("Generate Event\n");
    }

    if (usb_interrupt_level1 & BIT0)            //Group Byte 0
    {
        usb_interrupt_level2 = USB_BYTE_REG_READ(ZM_INTR_SOURCE_0_OFFSET);

        // refer to FUSB200, p 48, offset:21H, bit7 description, should clear the command abort interrupt first!?
        if (usb_interrupt_level2 & BIT7)
        {
            USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_0_OFFSET, (USB_BYTE_REG_READ(ZM_INTR_SOURCE_0_OFFSET)& ~BIT7));
        }

        if (usb_interrupt_level2 & BIT1)
        {
            A_PRINTF("![USB] ep0 IN in \n\r");
            A_USB_EP0_TX();                       // USB EP0 tx interrupt
        }
        if (usb_interrupt_level2 & BIT2)
        {
            //A_PRINTF("![USB] ep0 OUT in\n\r");
            A_USB_EP0_RX();                       // USB EP0 rx interrupt
        }
        if (usb_interrupt_level2 & BIT0)
        {
            //A_PRINTF("![USB] ep0 SETUP in\n\r");
            A_USB_EP0_SETUP();
        }

        if (eUsbCxFinishAction == ACT_STALL)
        {
            USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, 0x04);
//            A_PRINTF("![USB] ZM_CX_CONFIG_STATUS_REG = 0x04\n\r");
        }
        else if (eUsbCxFinishAction == ACT_DONE)
        {
            // set CX_DONE to indicate the transmistion of control frame
            USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, 0x01);
        }
        eUsbCxFinishAction = ACT_IDLE;
    }

    if (usb_interrupt_level1 & BIT7)            //Group Byte 7
    {
        //usb_interrupt_level2 = ZM_INTR_SOURCE_7_REG;
        usb_interrupt_level2 = USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_OFFSET);

        if (usb_interrupt_level2 & BIT1)
        {
            vUsb_rst();
        }
        if (usb_interrupt_level2 & BIT2)
        {
            vUsb_suspend();
        }
        if (usb_interrupt_level2 & BIT3)
        {
            vUsb_resm();
        }
    }

}


LOCAL void _usb_fw_task(void)
{
    register uint8_t usb_interrupt_level1;
    register uint8_t usb_interrupt_level2;
    register uint8_t usb_ctrl_err_indication;

    usb_interrupt_level1 = USB_BYTE_REG_READ(ZM_INTR_GROUP_OFFSET);

#if 0 // these endpoints are handled by DMA
    if (usb_interrupt_level1 & BIT5)            //Group Byte 5
    {
        vUsb_Data_In();
    }
#endif
    if (usb_interrupt_level1 & BIT4)
    {
        usb_interrupt_level2 = USB_BYTE_REG_READ(ZM_INTR_SOURCE_4_OFFSET);
        if( usb_interrupt_level2 & BIT6)
            A_USB_REG_OUT();//vUsb_Reg_Out();
    }

    if (usb_interrupt_level1 & BIT6)
    {
        //zfGenWatchDogEvent();
    usb_interrupt_level2 = USB_BYTE_REG_READ(ZM_INTR_SOURCE_6_OFFSET);
        if( usb_interrupt_level2 & BIT6)
             A_USB_STATUS_IN();//vUsb_Status_In();
    }

    if (usb_interrupt_level1 & BIT0)            //Group Byte 0
    {
        //usb_interrupt_level2 = ZM_INTR_SOURCE_0_REG;
        usb_interrupt_level2 = USB_BYTE_REG_READ(ZM_INTR_SOURCE_0_OFFSET);

        // refer to FUSB200, p 48, offset:21H, bit7 description, should clear the command abort interrupt first!?
        if (usb_interrupt_level2 & BIT7)
        {
            //ZM_INTR_SOURCE_0_REG &= 0x7f;       // Handle command abort
            USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_0_OFFSET, (USB_BYTE_REG_READ(ZM_INTR_SOURCE_0_OFFSET)& ~BIT7));
            A_PRINTF("![SOURCE_0] bit7 on\n\r");
        }

        if (usb_interrupt_level2 & BIT1)
        {
            //A_PRINTF("![USB] ep0 IN in \n\r");
            A_USB_EP0_TX();                       // USB EP0 tx interrupt
        }
        if (usb_interrupt_level2 & BIT2)
        {
            //A_PRINTF("![USB] ep0 OUT in\n\r");
            A_USB_EP0_RX();                       // USB EP0 rx interrupt
        }
        if (usb_interrupt_level2 & BIT0)
        {
            //A_PRINTF("![USB] ep0 SETUP in\n\r");
            A_USB_EP0_SETUP();
            //vWriteUSBFakeData();
        }
//        else if (usb_interrupt_level2 & BIT3)
        if (usb_interrupt_level2 & BIT3)
        {
            vUsb_ep0end();
//            A_PRINTF("![SOURCE_0] ep0 CMD_END\n\r");
        }
        if (usb_interrupt_level2 & BIT4)
        {
            vUsb_ep0fail();
//            A_PRINTF("![SOURCE_0] ep0 CMD_FAIL\n\r");
        }
        if (eUsbCxFinishAction == ACT_STALL)
        {
            // set CX_STL to stall Endpoint0 & will also clear FIFO0
            USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, 0x04);
//            A_PRINTF("![USB] ZM_CX_CONFIG_STATUS_REG = 0x04\n\r");
        }
        else if (eUsbCxFinishAction == ACT_DONE)
        {
            // set CX_DONE to indicate the transmistion of control frame
            USB_BYTE_REG_WRITE(ZM_CX_CONFIG_STATUS_OFFSET, 0x01);
        }
        eUsbCxFinishAction = ACT_IDLE;
    }

    if (usb_interrupt_level1 & BIT7)            //Group Byte 7
    {
        //usb_interrupt_level2 = ZM_INTR_SOURCE_7_REG;
        usb_interrupt_level2 = USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_OFFSET);

#if 0
        if (usb_interrupt_level2 & BIT7)
        {
            vUsb_Data_Out0Byte();
//            A_PRINTF("![SOURCE_7] bit7 on, clear it\n\r");
        }
        if (usb_interrupt_level2 & BIT6)
        {
            vUsb_Data_In0Byte();
//            A_PRINTF("![SOURCE_7] bit6 on, clear it\n\r");
        }
#endif

        if (usb_interrupt_level2 & BIT1)
        {
            vUsb_rst();
            //USB_BYTE_REG_WRITE(ZM_INTR_SOURCE_7_REG, (USB_BYTE_REG_READ(ZM_INTR_SOURCE_7_OFFSET)&~0x2));
            A_PRINTF("!USB reset\n\r");
//            A_PRINTF("![0x1012c]: %\n\r", USB_WORD_REG_READ(0x12c));
        }
        if (usb_interrupt_level2 & BIT2)
        {
           // TBD: the suspend resume code should put here, Ryan, 07/18
           //
           //  issue, jump back to rom code and what peripherals should we reset here?
           //

			/* Set GO_TO_SUSPEND bit to USB main control register */
            vUsb_suspend();
            A_PRINTF("!USB suspend\n\r");

            // keep the record of suspend
#if defined(PROJECT_MAGPIE)
            *((volatile uint32_t*)WATCH_DOG_MAGIC_PATTERN_ADDR) = SUS_MAGIC_PATTERN;
#elif defined(PROJECT_K2)
            HAL_WORD_REG_WRITE(MAGPIE_REG_RST_STATUS_ADDR, SUS_MAGIC_PATTERN);
#endif /* #if defined(PROJECT_MAGPIE) */

            /* Reset USB FIFO */
            A_USB_RESET_FIFO();

            /* Turn off power */
            A_USB_POWER_OFF();

// DON'T restart when not in ASIC
#if defined(MAGPIE_ASIC)
            /* Jump to boot code */
            A_USB_JUMP_BOOT();
#endif

        }
        if (usb_interrupt_level2 & BIT3)
        {
            vUsb_resm();
            A_PRINTF("!USB resume\n\r");
        }
    }

}

#if 0 // old

void _usb_init(void)
{

// init variables
//    u16TxRxCounter = 0;
//    eUsbCxCommand = CMD_VOID;
//    u8UsbConfigValue = 0;
    u8UsbInterfaceValue = 0;
    u8UsbInterfaceAlternateSetting = 0;
//    bUsbEP0HaltSt = FALSE;
//    u16FirmwareComplete = 0;
//    eUsbCxFinishAction = ACT_IDLE;
    UsbStatus[0] = !fBUS_POWER;

// init hardware

//    cFUSB200Init();
    A_USB_INIT_PHY();

    //ZM_PHY_TEST_SELECT_REG = 0;             // Plug In
    USB_BYTE_REG_WRITE(ZM_PHY_TEST_SELECT_OFFSET, 0x0);

    // reset the address, just in case...
    //USB_BYTE_REG_WRITE(ZM_DEVICE_ADDRESS_OFFSET, 0x0);

}

#else // new

#if defined(PROJECT_MAGPIE)

/* -  spec, ch11, reset
 *
 *  1. turn on ETH PLL and set ETH PLL to 384Mhz
 *  2. set "USB_DMA, USB_CORE, ETH_PLL, CPU_PLL, USB_POR reset" bit 
 *  3. clear "ETH_PLL, CPU_PLL" reset bit
 *  4. set USB divider to 48, 192/16=12
 *  5. disable ETH PLL bypass
 *  6. clear USB_POR
 *  7. clear USB_DMA, USB_CORE
 *  8. enable USB_AHB_ARB
 *
 *  note: don't know why bit3, bit4 should deassert? here especially bit4?
 *        since if we don't deassert this, clk won't come up
 *
 */
#if defined(MAGPIE_ASIC)
#define RST_USB_COLD_INIT()      \
{                               \
    /********* number of PLLDIV_LOW and PLLDIV_HIGH ***********/        \
    /*HAL_WORD_REG_WRITE(MAGPIE_REG_USB_DIVIDE_ADDR,((0x8<<8)|0x8));  */    \
    /* 1. */ HAL_WORD_REG_WRITE(MAGPIE_REG_ETH_PLL_ADDR, 0x305);                            \
    /* 2. */ HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR,                                  \
                (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)|(BIT0|BIT1|BIT2|BIT3|BIT4))); \
    /* 3. */ HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR,                                  \
                (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)&(~(BIT1|BIT2))));            \
    /* 4. */ HAL_WORD_REG_WRITE(MAGPIE_REG_USB_DIVIDE_ADDR, 0x1010);                        \
    /* 5. */ HAL_WORD_REG_WRITE(MAGPIE_REG_ETH_PLL_BYPASS_ADDR, 0x0);                       \
    A_DELAY_USECS(100);  /* wait for clock source stable */                                 \
    /* 6. */ HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR,                                  \
                (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)&(~(BIT0))));                 \
    /* 7. */ HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR,                                  \
                (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)&(~(BIT3|BIT4))));            \
    /* 8. */ HAL_WORD_REG_WRITE(MAGPIE_REG_AHB_ARB_ADDR,                                    \
                (HAL_WORD_REG_READ(MAGPIE_REG_AHB_ARB_ADDR)|BIT2));                       \
    /* HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR, ); */                                  \
    /* HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR, (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)|((BIT0|BIT3|BIT4))));  */  \
    /* HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR, (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)&(~(BIT0|BIT3|BIT4)))); */  \
}

/* -  back from suspend
 *
 *  1. turn on ETH PLL , 0x5600c, ~bit0
 *  2. clear USB SUSPEND_ENABLE, 0x56030, ~bit0
 *
 */
#define RST_USB_SUSP_INIT()                                                                 \
{                                                                                           \
    /* 1. */ HAL_WORD_REG_WRITE(MAGPIE_REG_ETH_PLL_BYPASS_ADDR,                             \
                (HAL_WORD_REG_READ(MAGPIE_REG_ETH_PLL_BYPASS_ADDR)&(~BIT0)));               \
    /* 2. */ HAL_WORD_REG_WRITE(MAGPIE_REG_SUSPEND_ENABLE_ADDR,                             \
                (HAL_WORD_REG_READ(MAGPIE_REG_SUSPEND_ENABLE_ADDR)&(~BIT0)));               \
}

/* -  back from watchdog
 *
 */
#define RST_USB_WDT_INIT()


#elif defined(MAGPIE_FPGA)
// fpag don't have PLL, skip 1~5
#define RST_USB_COLD_INIT()                                                                      \
{                                                                                           \
    /* 6. */ HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR,                                  \
                (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)&(~(BIT0))));                 \
    /* 7. */ HAL_WORD_REG_WRITE(MAGPIE_REG_RST_RESET_ADDR,                                  \
                (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)&(~(BIT3|BIT4))));            \
    /* 8. */ HAL_WORD_REG_WRITE(MAGPIE_REG_AHB_ARB_ADDR,                                    \
                (HAL_WORD_REG_READ(MAGPIE_REG_RST_RESET_ADDR)|BIT2));                       \
    A_DELAY_USECS(100);  /* wait for clock source stable */                                 \
}

/* -  back from suspend
 *
 */
#define RST_USB_SUSP_INIT()

/* -  back from watchdog
 *
 */
#define RST_USB_WDT_INIT()


#endif


#elif defined(PROJECT_K2)
#define RST_USB_INIT()      \
{                               \
    HAL_WORD_REG_WRITE(MAGPIE_REG_RST_PWDN_CTRL_ADDR, HAL_WORD_REG_READ(MAGPIE_REG_RST_PWDN_CTRL_ADDR)|BIT12);  \
    A_DELAY_USECS(10); \
    HAL_WORD_REG_WRITE(MAGPIE_REG_RST_PWDN_CTRL_ADDR, HAL_WORD_REG_READ(MAGPIE_REG_RST_PWDN_CTRL_ADDR)&(~BIT12));  \
}
#endif
/*
    @ToDo: this is used to enable usb access internal memory, dma need this
    HAL_WORD_REG_WRITE(MAGPIE_REG_AHB_ARB_ADDR, (HAL_WORD_REG_READ(MAGPIE_REG_AHB_ARB_ADDR)&(~(BIT2))));  \
    A_DELAY_USECS(20); \
    HAL_WORD_REG_WRITE(MAGPIE_REG_AHB_ARB_ADDR, (HAL_WORD_REG_READ(MAGPIE_REG_AHB_ARB_ADDR)|(BIT2))); \
    A_DELAY_USECS(20); \
*/


LOCAL void _usb_clk_init(void)
{
    T_BOOT_TYPE mBootMode;

    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x31;
    
    mBootMode = A_WDT_LASTBOOT();

#if defined(PROJECT_MAGPIE)

    if( mBootMode == ENUM_WDT_BOOT )
    {
        RST_USB_WDT_INIT();
    }
    else if ( mBootMode == ENUM_SUSP_BOOT )
    {
        RST_USB_SUSP_INIT();
    }
    else
    {
        RST_USB_COLD_INIT();
    }
    
#elif defined(PROJECT_K2)
    if( mBootMode == ENUM_COLD_BOOT )
    {
        RST_USB_INIT();
    }
#endif

    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x32;

    //A_DELAY_USECS(300); // delay 300 micro seconds, wait for clock stable!
}


void _usb_init(void)
{
    u32_t   cold_start;

//    A_PUTS("\n - _usb_init - \n\r");

#if defined(PROJECT_MAGPIE)
    //if ( *((volatile uint32_t*)WATCH_DOG_MAGIC_PATTERN_ADDR) == WDT_MAGIC_PATTERN || *((volatile uint32_t*)WATCH_DOG_MAGIC_PATTERN_ADDR) == SUS_MAGIC_PATTERN )
    if( A_WDT_LASTBOOT()!= ENUM_COLD_BOOT)
#elif defined(PROJECT_K2)
    if (HAL_WORD_REG_READ(MAGPIE_REG_RST_STATUS_ADDR) == WDT_MAGIC_PATTERN || HAL_WORD_REG_READ(MAGPIE_REG_RST_STATUS_ADDR) == SUS_MAGIC_PATTERN)
#endif /* #if defined(PROJECT_MAGPIE) */
        cold_start = 0;
    else
        cold_start = 1;

    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x30;
// init variables
//    u16TxRxCounter = 0;
//    eUsbCxCommand = CMD_VOID;
//    u8UsbConfigValue = 0;
    u8UsbInterfaceValue = 0;
    u8UsbInterfaceAlternateSetting = 0;
//    bUsbEP0HaltSt = FALSE;
//    u16FirmwareComplete = 0;
//    eUsbCxFinishAction = ACT_IDLE;
    UsbStatus[0] = !fBUS_POWER;


/*!
 * move the setting to A_USB_CLK_INIT(), so that we could patch these things
 */
#if 1 
    A_USB_CLK_INIT();

#else

#if defined(PROJECT_MAGPIE)

//#if defined(MAGPIE_ASIC)
    //
    // @Bug 36267 - wdt reset or other reset will reset usb phy, we need to init again here
    //            - this won't work at FPGA, skip this checking if build for FPGA
    // 
    // @Bug 36947 - L3 fpga's reset behavior of usb is not as what I expect!, need to confirm
    //            
    // ToBeNote: if (Bug36947), skip the checking and reset usb anyway, but will see the connection broken
//    if (cold_start)
//#endif
    A_USB_CLK_INIT();
#elif defined(PROJECT_K2)
    if (cold_start)
    {
        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x31;
        RST_USB_INIT();
    }
#endif /* #if defined(PROJECT_MAGPIE) */

#endif

        A_DELAY_USECS(300); // delay 300 usecs, wait for clock stable!
    
	while( 1 )
    {
        /*
         * wait for USBSOC_HCLK_RDY tight high, indicate the 30Mhz is ready for use
         */
        if(HAL_WORD_REG_READ(0x10128)& BIT8)
            break;

        //A_DELAY_USECS(200); // delay 200 micro seconds, wait for clock stable!
	}

    DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x33;
    A_PUTS("6. usb_hclk rdy\n\r");

    //
    // @Bug 36267 - wdt reset or other reset will reset usb phy, we need to init again here
    //
    // @Bug 36947 - L3 fpga's reset behavior of usb is not as what I expect!, need to confirm
#if defined(PROJECT_MAGPIE)

    // in cold or suspend boot, we do reinit the USB_PHY, skip only when watchdog start
    //
    // 
#if defined(MAGPIE_ASIC)
    if (cold_start)
#endif
#elif defined(PROJECT_K2)
    if (cold_start)
#endif /* #if defined(PROJECT_MAGPIE) */
    {
        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x34;
        A_USB_INIT_PHY();

        DEBUG_SYSTEM_STATE = (DEBUG_SYSTEM_STATE&(~0xff)) | 0x35;
        //ZM_PHY_TEST_SELECT_REG = 0;             // Plug In
        USB_BYTE_REG_WRITE(ZM_PHY_TEST_SELECT_OFFSET, 0x0);

        // reset the address, just in case...
        //USB_BYTE_REG_WRITE(ZM_DEVICE_ADDRESS_OFFSET, 0x0);
    }

     /* If watchdog reset happens, target needs to send a message to host through EP3 */
     if ( A_WDT_LASTBOOT() == ENUM_WDT_BOOT )
        mUSB_STATUS_IN_INT_ENABLE();
     else
        mUSB_STATUS_IN_INT_DISABLE();

}

#endif

////////////////////////////////////////////////////////
void usbfifo_module_install(struct usbfifo_api *apis)
{    
        /* hook in APIs */
    apis->_init = _usbfifo_init;
    apis->_enable_event_isr = _usbfifo_enable_event_isr;
}


void cmnos_usb_module_install(struct usb_api *apis)
{
    apis->_usb_init = _usb_init;
    apis->_usb_rom_task = _usb_rom_task;
    apis->_usb_fw_task = _usb_fw_task;
    apis->_usb_init_phy = cFUSB200Init;

    apis->_usb_ep0_setup = vUsb_ep0setup;
    apis->_usb_ep0_tx_data = vUsbEP0TxData;
    apis->_usb_ep0_rx_data = vUsbEP0RxData;

    apis->_usb_get_configuration = bGet_configuration;
    apis->_usb_set_configuration = bSet_configuration;

    apis->_usb_get_interface = bGet_interface;
    apis->_usb_set_interface = bSet_interface;

    apis->_usb_standard_cmd = bStandardCommand;
    apis->_usb_vendor_cmd = VendorCommand;

    apis->_usb_reset_fifo= zfResetUSBFIFO;
    apis->_usb_power_off = zfTurnOffPower;
    apis->_usb_gen_wdt = zfGenWatchDogEvent;
    apis->_usb_jump_boot = zfJumpToBootCode;

    apis->_usb_get_descriptor = bGet_descriptor;
    apis->_usb_set_address = bSet_address;
    apis->_usb_set_feature = bSet_feature;
    apis->_usb_clr_feature = bClear_feature;

    apis->_usb_get_status = bGet_status;
    apis->_usb_setup_desc = vUsb_SetupDescriptor;

    apis->_usb_reg_out = vUsb_Reg_Out;
    apis->_usb_status_in = vUsb_Status_In;

    apis->_usb_ep0_tx = vUsb_ep0tx;
    apis->_usb_ep0_rx = vUsb_ep0rx;
    
    apis->_usb_clk_init = _usb_clk_init;
}

#endif
