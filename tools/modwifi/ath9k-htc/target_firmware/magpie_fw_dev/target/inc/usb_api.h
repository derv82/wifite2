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
#ifndef USB_API_H
#define USB_API_H

#include "dt_defs.h"

/******** hardware API table structure (API descriptions below) *************/
struct usb_api {
    void (*_usb_init)(void);
    void (*_usb_rom_task)(void);
    void (*_usb_fw_task)(void);
    void (*_usb_init_phy)(void);

    // ep0 operation
    void (*_usb_ep0_setup)(void);
    
    void (*_usb_ep0_tx)(void);
    void (*_usb_ep0_rx)(void);

    // get/set interface
    BOOLEAN (*_usb_get_interface)(void);
    BOOLEAN (*_usb_set_interface)(void);

    // get/set configuration
    BOOLEAN (*_usb_get_configuration)(void);
    BOOLEAN (*_usb_set_configuration)(void);

    // standard/vendor command
    BOOLEAN (*_usb_standard_cmd)(void);    
    void (*_usb_vendor_cmd)(void);

    void (*_usb_power_off)(void);
    void (*_usb_reset_fifo)(void);
    void (*_usb_gen_wdt)(void);
    void (*_usb_jump_boot)(void);
    
    BOOLEAN (*_usb_clr_feature)(void);
    BOOLEAN (*_usb_set_feature)(void);    
    BOOLEAN (*_usb_set_address)(void);
    BOOLEAN (*_usb_get_descriptor)(void);

    BOOLEAN (*_usb_get_status)(void);
    void (*_usb_setup_desc)(void);
    void (*_usb_reg_out)(void);
    void (*_usb_status_in)(void);

    void (*_usb_ep0_tx_data)(void);
    void (*_usb_ep0_rx_data)(void);

    void (*_usb_clk_init)(void);
};

#endif
