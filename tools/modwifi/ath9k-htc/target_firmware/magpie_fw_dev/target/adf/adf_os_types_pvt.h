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
#ifndef __ADF_OS_TYPES_PVT_H
#define __ADF_OS_TYPES_PVT_H

#include <stddef.h>
#include <osapi.h>
//#include "cmnos_api.h"
//#include "Magpie_api.h"
#include <vbuf_api.h>

#define __ADF_OS_MAX_SCATTER    1
#define __adf_os_packed         __attribute__((__packed__))
#define __ADF_OS_NAME_SIZE      10

/*
 * Private definitions of general data types
 */
/**
 * Endian-ness
 */
#undef ADF_LITTLE_ENDIAN_MACHINE
#undef ADF_BIG_ENDIAN_MACHINE

//#if (_BYTE_ORDER == _LITTLE_ENDIAN)
#ifdef LITTLE_ENDIAN
#define ADF_LITTLE_ENDIAN_MACHINE
//#elif (_BYTE_ORDER == _BIG_ENDIAN)
#elif BIG_ENDIAN
#define ADF_BIG_ENDIAN_MACHINE
#endif

/**
 * CACHE-SYNC (DMA)
 */
#define __ADF_SYNC_PREREAD         0 
#define __ADF_SYNC_POSTREAD		   1
#define __ADF_SYNC_PREWRITE		   2
#define __ADF_SYNC_POSTWRITE	   3

#define __ADF_OS_DMA_TO_DEVICE     0
#define __ADF_OS_DMA_FROM_DEVICE   1 
      

struct __adf_softc;


enum __adf_net_wireless_evcode{
    __ADF_IEEE80211_ASSOC = 100,
    __ADF_IEEE80211_REASSOC = 101,
    __ADF_IEEE80211_DISASSOC = 102,
    __ADF_IEEE80211_JOIN = 103,
    __ADF_IEEE80211_LEAVE = 104,
    __ADF_IEEE80211_SCAN = 105,
    __ADF_IEEE80211_REPLAY = 106,
    __ADF_IEEE80211_MICHAEL = 107,
    __ADF_IEEE80211_REJOIN = 108, 
    __ADF_CUSTOM_PUSH_BUTTON = 109,
};

/* generic data types */
struct __adf_device  {
int dummy;    
}; 

typedef struct __adf_device *__adf_os_device_t;


struct __adf_dma_map {
    VBUF *buf;
    
    A_UINT32 *ds_addr;
    A_UINT16 ds_len;
}; 

typedef struct __adf_dma_map *__adf_os_dma_map_t;

typedef A_UINT32      __adf_os_dma_addr_t;
typedef A_UINT32      __adf_os_dma_size_t;

typedef unsigned int            __adf_os_size_t;
typedef int             __adf_os_off_t;

#define __adf_os_iomem_t

#if 0
typedef int           __a_uint8_t;    
typedef int            __a_int8_t;     
typedef int          __a_uint16_t;   
typedef int           __a_int16_t;    
typedef int          __a_uint32_t;   
typedef int           __a_int32_t;    
typedef int          __a_uint64_t;   
typedef int           __a_int64_t; 
#else
typedef A_UINT8           __a_uint8_t;
typedef A_INT8            __a_int8_t;     
typedef A_UINT16          __a_uint16_t;   
typedef A_INT16          __a_int16_t;    
typedef A_UINT32          __a_uint32_t;   
typedef A_INT32          __a_int32_t;    
typedef A_UINT64          __a_uint64_t;   
typedef A_INT64           __a_int64_t;    

typedef A_UINT32            u_int32_t;
typedef A_UINT16            u_int16_t;
typedef A_UINT8             u_int8_t;
typedef unsigned int        u_int;
typedef unsigned long        u_long;
//typedef __adf_os_size_t        size_t;

typedef A_UINT64            u_int64_t;

#endif

//extern void my_printf(struct ath_hal *ah, const char* fmt, ...);

//#define __adf_os_print        my_printf
#define __adf_os_print          A_PRINTF

#if 1  
#if defined(__XCC__)
#include "stdarg.h"
#define __va_list __gnuc_va_list
#endif
#endif

/* For compiling WLAN drivers */
#define IFNAMSIZ      				10
#define ENXIO 						-1
#define ENOMEM 						-1
#define EIO 						-1
#define caddr_t 					int
#define ENODEV 						-1
#define EOPNOTSUPP 					-1
#define	KASSERT(exp, msg)

#if 0
#ifndef __packed
#define __packed    __attribute__((__packed__))
#endif

#ifndef roundup
#define roundup(x, y)   ((((x)+((y)-1))/(y))*(y))  /* to any y */
#endif
#endif

#endif
