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
#ifndef __ADF_NET_PVT_H
#define __ADF_NET_PVT_H



#define ADF_NET_MAX_NAME    64
#define ADF_DEF_TX_TIMEOUT  5 /*Seconds I suppose*/

#define __ADF_NET_NULL      NULL
#define __ADF_PCI_BAR0      0x10


a_status_t 
__adf_net_register_drv(adf_drv_info_t *drv);

void
__adf_net_unregister_drv(a_uint8_t *name);

typedef struct __adf_net_mod {
int dummy;
}__adf_net_mod_t;



typedef struct __adf_softc {
int dummy;
}__adf_softc_t;

static inline a_bool_t
__adf_net_carrier_ok(adf_net_handle_t hdl)
{
    return 1;
}

static inline void
__adf_net_carrier_off(adf_net_handle_t hdl)
{

}

static inline void
__adf_net_carrier_on(adf_net_handle_t hdl)
{

}

static inline void
__adf_net_start_queue(adf_net_handle_t hdl)
{   

}

static inline void
__adf_net_stop_queue(adf_net_handle_t hdl)
{

}

static inline void
__adf_net_wake_queue(adf_net_handle_t hdl)
{
}

static inline a_bool_t
__adf_net_queue_stopped(adf_net_handle_t hdl)
{
    return 1;
}

static inline a_bool_t
__adf_net_is_running(adf_net_handle_t hdl)
{
    return 1;
}
static inline a_bool_t
__adf_net_is_up(adf_net_handle_t hdl)
{
    return 1;
}

static inline adf_net_handle_t __adf_net_dev_create(adf_drv_handle_t hdl, adf_dev_sw_t *op,
                                      adf_net_dev_info_t *info)
{
    return NULL;
}

static inline adf_net_handle_t __adf_net_vdev_create(adf_net_handle_t dev_hdl, 
                                       adf_drv_handle_t hdl, adf_vdev_sw_t *op, 
                                       adf_net_dev_info_t *info)
{
    return NULL;
}

static inline const a_uint8_t * __adf_net_ifname(adf_net_handle_t  hdl)
{
	return NULL;
}

static inline adf_os_handle_t
__adf_net_dev_to_os(__adf_os_device_t osdev)
{
    return NULL;
}

static inline adf_os_handle_t
__adf_net_hdl_to_os(adf_net_handle_t hdl)
{
    return NULL;
}    

#endif
