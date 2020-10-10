/*
 * @File: 
 * 
 * @Abstract: 
 * 
 * @Notes: 
 * 
 * 
 * Copyright (c) 2007 Atheros Communications Inc.
 * All rights reserved.
 *
 */

#ifndef VBUF_H_
#define VBUF_H_

struct VBUF_CONTEXT {
    VBUF *free_buf_head;
    int  nVbufNum;
    
    // Left a door for extension the structure
    void *pReserved;    
};

#endif /*VBUF_H_*/
