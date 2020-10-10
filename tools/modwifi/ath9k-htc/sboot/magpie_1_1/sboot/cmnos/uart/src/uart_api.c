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
/*
 * $Id: //depot/sw/branches/fusion_usb/target_firmware/magpie_fw_dev/build/magpie_1_1/sboot/cmnos/uart/src/uart_api.c#1 $
 *
 * This file contains UART functions
 */
#include "sys_cfg.h"

#if SYSTEM_MODULE_UART

#include "athos_api.h"

//static global control block
//
static struct uart_blk uart_ctl_blk;	

static void _uart_hwinit(uint32_t freq, uint32_t baud);

/*!- Initialize UART
 *
 */
uint32_t
_uart_init(void)
{
    /*! Initialize UART hardware */
    uint32_t _lcr;

    /* Disable port interrupts while changing hardware */
    UART_REG_WRITE(IER_OFFSET, 0);

    /* Set databits, stopbits and parity. */
    _lcr = LCR_CLS_SET(3) | LCR_STOP_SET(0) | LCR_PEN_SET(0);
    UART_REG_WRITE(LCR_OFFSET, _lcr);

    /* Set baud rate. */
    _uart_hwinit(A_REFCLK_SPEED_GET(), UART_DEFAULT_BAUD);
//    _uart_hwinit(A_REFCLK_SPEED_GET(), 115200);
    //_uart_hwinit(SYSTEM_CLK, UART_DEFAULT_BAUD);

    /* Don't allow interrupts. */
    UART_REG_WRITE(IER_OFFSET, 0);

    /*
     * Enable and clear FIFO.
     * We don't really use the FIFO for output, but it might still
     * be useful for input.
     */
    UART_REG_WRITE(FCR_OFFSET,
                    (FCR_FIFO_EN_SET(1) |
                     FCR_RCVR_FIFO_RST_SET(1) |
                     FCR_XMIT_FIFO_RST_SET(1)));

    /*! Initialize UART software buffer */
    uart_ctl_blk._tx.start_index = 0;
    uart_ctl_blk._tx.end_index = 0;
}


/*!- dummy put character 
 *
 */
void
_uart_char_put_nothing(uint8_t ch)
{
    // do nothing
}


/*!- dummy get character 
 *
 */
uint16_t
_uart_char_get_nothing(uint8_t* ch)
{
    return 0;   //return FALSE;
}


/*!- Put a character 
 *
 */
void
_uart_char_put(uint8_t ch)
{
#if USE_POST_BUFFER
    uint16_t index;
    uint32_t count = 0; 

    index = (uart_ctl_blk._tx.end_index+1) & (UART_FIFO_SIZE-1);
	if(index == uart_ctl_blk._tx.start_index) {
	    while (1) {
            _uart_task();
            index = (uart_ctl_blk._tx.end_index+1) & (UART_FIFO_SIZE-1);
	        if (index != uart_ctl_blk._tx.start_index) {
	            break;
            }
            if (count++ > 100000) {
                /*! If Tx buffer is full, uart_underrun_t++, return FALSE */
		        uart_ctl_blk._tx.overrun_err++;
		        return;
            }
	    }
	}
    uart_ctl_blk._tx.buf[uart_ctl_blk._tx.end_index] = ch;
    uart_ctl_blk._tx.end_index = index;
#else
    /*! If Tx buffer is full, uart_underrun_t++, return FALSE */
    uint32_t lsr;
    int i;

    for (i=0; i<UART_RETRY_COUNT; i++) {
        lsr = UART_REG_READ(LSR_OFFSET);
        if (lsr & LSR_THRE_MASK) {
            break;
        }
    } 

    /*! Now, the transmit buffer is empty, put to tx buffer */
    UART_REG_WRITE(THR_OFFSET, ch);

    /*
     * Hang around until the character has been safely sent.
     * If we don't do this, the system could go to sleep, which
     * causes the UART's clock to stop, and we won't see output
     * that's stuck in the FIFO.
     */
    for (i=0; i<UART_RETRY_COUNT; i++) {
        lsr = UART_REG_READ(LSR_OFFSET);
        if (lsr & LSR_TEMT_MASK) {
            break;
        }
    }
#endif

}

/*!- Put a character 
 *
 */
void
_uart_char_put_nowait(uint8_t ch)
{

    /*! If Tx buffer is full, uart_underrun_t++, return FALSE */
    uint32_t lsr;
    int i;

    for (i=0; i<UART_RETRY_COUNT; i++) {
        lsr = UART_REG_READ(LSR_OFFSET);
        if (lsr & LSR_THRE_MASK) {
            break;
        }
    } 

    /*! Now, the transmit buffer is empty, put to tx buffer */
    UART_REG_WRITE(THR_OFFSET, ch);

    /*
     * Hang around until the character has been safely sent.
     * If we don't do this, the system could go to sleep, which
     * causes the UART's clock to stop, and we won't see output
     * that's stuck in the FIFO.
     */
    for (i=0; i<UART_RETRY_COUNT; i++) {
        lsr = UART_REG_READ(LSR_OFFSET);
        if (lsr & LSR_TEMT_MASK) {
            break;
        }
    }

}


/*!- Get a character 
 *
 */
uint16_t
_uart_char_get(uint8_t* ch)
{

    /*! If Rx FIFO is not empty, get char from Rx buffer, reutnr TRUE */
    if ((UART_REG_READ(LSR_OFFSET) & LSR_DR_MASK) != 0) 
    {
        *ch = UART_REG_READ(RBR_OFFSET);
        return 1;
    }
    /*! Else return FALSE */
    else 
    { 
        return 0;
    }
}

/*!- UART task 
 *
 */
void
_uart_task(void)
{
#if USE_POST_BUFFER
    uint16_t count;
    volatile uint32_t lsr;

    /*! If Tx FIFO almost empty, move chars from Tx buffer to Tx FIFO */
    lsr = UART_REG_READ(LSR_OFFSET);
    if ((lsr & LSR_THRE_MASK) != 0) { //Transmitter holding register empty
        count = 0;
        while (count<16) {
            if (uart_ctl_blk._tx.start_index != uart_ctl_blk._tx.end_index) {
                UART_REG_WRITE(THR_OFFSET, uart_ctl_blk._tx.buf[uart_ctl_blk._tx.start_index]);
                uart_ctl_blk._tx.start_index = (uart_ctl_blk._tx.start_index+1)
                    & (UART_FIFO_SIZE-1);
            }
            else
            {
                break;
            }
      	    count++;
        }
    }
#endif
    return;
}



 uint32_t 
_uart_status()
{
	return uart_ctl_blk._tx.overrun_err;
}

/*!- Output a string 
 *
 */
void
_uart_str_out(uint8_t* str)
{
    uint32_t i = 0;

    if( !uart_ctl_blk.debug_mode )
        return;

    while (str[i] != 0) {
        _uart_char_put(str[i]);
        i++;
    }
    return;
}

/*!- enable or disable put/get
 *
 */
void
_uart_config(uint16_t flag)
{    
    if( uart_ctl_blk.debug_mode != flag )
    {
        uart_ctl_blk.debug_mode = !uart_ctl_blk.debug_mode;
        
        // debug mode enable
        if( uart_ctl_blk.debug_mode ) 
            uart_ctl_blk._uart->_uart_char_put = _uart_char_put;
        else
            // debug mode enable
            uart_ctl_blk._uart->_uart_char_put = _uart_char_put_nothing;
    }
}

/*!- Set baudrate 
 *
 */
void
_uart_hwinit(uint32_t freq, uint32_t baud)
{
    uint32_t _lcr;
    uint32_t baud_divisor = freq/16/baud;

    _lcr = UART_REG_READ(LCR_OFFSET);
    _lcr |= LCR_DLAB_SET(1);
    UART_REG_WRITE(LCR_OFFSET, _lcr);

    UART_REG_WRITE(DLH_OFFSET, baud_divisor >> 8);
    UART_REG_WRITE(DLL_OFFSET, baud_divisor & 0xff);

    _lcr &= ~LCR_DLAB_SET(1);
    UART_REG_WRITE(LCR_OFFSET, _lcr);
}

/********** EXPORT function ***********/

/*!- Install the function table 
 *
 */
void cmnos_uart_module_install(struct uart_api *apis)
{    
    /* hook in APIs */
    apis->_uart_init = _uart_init;
    apis->_uart_char_put = _uart_char_put;
    apis->_uart_char_get = _uart_char_get;
    apis->_uart_str_out = _uart_str_out;
    apis->_uart_task = _uart_task;
    apis->_uart_config = _uart_config;
    apis->_uart_status = _uart_status;
    apis->_uart_hwinit = _uart_hwinit;

    uart_ctl_blk._uart = apis;
    uart_ctl_blk.debug_mode = TRUE;
    return;
}

#endif /* SYSTEM_MODULE_UART */

