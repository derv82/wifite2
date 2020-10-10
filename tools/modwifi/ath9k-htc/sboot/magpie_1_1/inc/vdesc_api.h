/*
 * @File: VBUF_api.h
 * 
 * @Abstract: Host Interface api
 * 
 * @Notes:
 * 
 * Copyright (c) 2008 Atheros Communications Inc.
 * All rights reserved.
 *
 */

#ifndef _VDESC_API_H
#define _VDESC_API_H

//#define VDESC_CONTROL_BUF_HDR          (1 << 6)  /* the buffer was manipulated and a header added */

#define MAX_HW_DESC_SIZE 20

typedef struct _VDESC
{
    struct _VDESC   *next_desc;
    A_UINT8         *buf_addr;
    A_UINT16        buf_size;
    A_UINT16        data_offset;
    A_UINT16        data_size;
    A_UINT16        control;
    A_UINT8         hw_desc_buf[MAX_HW_DESC_SIZE]; 
} VDESC;

//#define VDESC_HW_TO_VDESC(hwdesc)   ((VDESC *)(((A_UINT32 *)hwdesc - 4)))
#define VDESC_HW_TO_VDESC(hwdesc)   ((VDESC *)(((A_UINT32 *)hwdesc - 4)))

struct vdesc_api {
    void        (*_init)(int nDesc);
    VDESC*      (*_alloc_vdesc)();
    A_UINT8*    (*_get_hw_desc)(VDESC *desc);
    void        (*_swap_vdesc)(VDESC *dest, VDESC *src);
    //void (*_free_vdesc)(void);
        /* room to expand this table by another table */
    void *pReserved;    
};

extern void vdesc_module_install(struct vdesc_api *apis);

#endif 
