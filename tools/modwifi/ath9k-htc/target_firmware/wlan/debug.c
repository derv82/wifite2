#include <adf_os_types_pvt.h> // otherwise other includes fail
#include <cmnos_api.h>

#include "if_athvar.h"

#include "ah.h"
#include "ah_internal.h"
#include "wlan_hdr.h"
#include "debug.h"

#include "ar5416reg.h"
#include "ar5416desc.h"

/** Can't be too large, otherwise it wont fit in dram_seg */
#define BUFFSIZE	2048

/** Ring buffer containing debug output (essentially one large string) */
struct {
	/** debug messages */
	char buffer[BUFFSIZE];
	/** start position in buffer */
	unsigned int pos;
	/** current size of the ring buffer */
	unsigned int len;
} dmesg = {"", 0, 0};


int printk(const char *format)
{
	unsigned int lenpart1;
	unsigned int len = A_STRLEN(format);
	unsigned int endpos = (dmesg.pos + dmesg.len) % BUFFSIZE;
	if (len > BUFFSIZE)
		return -1;

	// Calculate length we can copy untill end of buffer
	lenpart1 = AH_MIN(len, BUFFSIZE - endpos);

	// Copy first part
	A_MEMCPY(dmesg.buffer + endpos, format, lenpart1);

	// Copy second part if needed
	if (lenpart1 != len) A_MEMCPY(dmesg.buffer, format + lenpart1, len - lenpart1);
	
	// Update pos and len. Only need to move position once ring buffer is full!
	dmesg.len = AH_MIN(BUFFSIZE, dmesg.len + len);
	if (dmesg.len >= BUFFSIZE) dmesg.pos = (endpos + len) % BUFFSIZE;

	// Return length writen to buffer
	return len;
}

unsigned int get_dmesg(unsigned int offset, char *buffer, unsigned int length)
{
	unsigned int startpos, remaininglen, tocopy, lenpart1;
	if (offset >= dmesg.len) return 0;

	// Calculate start position, remaining length, etc
	startpos = (dmesg.pos + offset) % BUFFSIZE;
	remaininglen = dmesg.len - offset;
	tocopy = AH_MIN(remaininglen, length - 1);
	lenpart1 = AH_MIN(tocopy, BUFFSIZE - startpos);

	// Copy first part
	A_MEMCPY(buffer, dmesg.buffer + startpos, lenpart1);

	// Copy second part
	if (tocopy != lenpart1) A_MEMCPY(buffer + lenpart1, dmesg.buffer, tocopy - lenpart1);

	buffer[tocopy] = '\0';
	return tocopy;
}

const char *itox(unsigned int val)
{
	static const char *convtable = "0123456789ABCDEF";
	static char buffer[16];
	int i = 14;

	buffer[15] = '\0';
	do {
		buffer[i] = convtable[val % 16];
		val >>= 4;
		i--;
	} while (val != 0);

	return buffer + i + 1;
}


void dump_buffer(unsigned char *buffer, int size)
{
	int i;

	for (i = 0; i < size; ++i) {
		if (buffer[i] < 0x10) printk("0");
		printk(itox(buffer[i]));
	}
	printk("\n");
}


/** Uncomment if you need these, they waste precious space otherwise */
#if 0

static void dump_ar5416_desc(struct ar5416_desc_20 *ds)
{
	// `ds->ds_daddr` is the physical address, which is equal to the virtual addess `ds`
	while (ds != NULL) {
		// Dump pointer and pointer to data
		printk("[");
		printk(itox((unsigned int)ds));
		printk("| ");
		printk(itox(ds->ds_data));
		printk(" ");

		printk((ds->ds_ctl1 & AR_RxIntrReq) ? "I" : " ");
		printk((ds->ds_rxstatus8 & AR_RxDone) ? "D" : " ");

		ds = (struct ar5416_desc_20 *)ds->ds_link;
		printk("]");
	}

	printk("\n");
}

void dump_rx_macbufs(struct ath_hal *ah)
{
	struct ar5416_desc_20 *ds = (struct ar5416_desc_20 *)ioread32_mac(AR_RXDP);
	dump_ar5416_desc(ds);
}

void dump_rx_tailq(struct ath_softc_tgt *sc)
{
	// `ds->ds_daddr` is the physical address, which is equal to the virtual addess `ds`
	struct ar5416_desc_20 *ds = (struct ar5416_desc_20 *)asf_tailq_first(&sc->sc_rxdesc);
	dump_ar5416_desc(ds);
}

void dump_skb(adf_nbuf_t skb)
{
#define PRINT_FIELD(_field) \
	do {						\
		printk(#_field "=");			\
		printk(itox((uint32_t)skb->_field));	\
		printk("\n");				\
	} while(0);

	PRINT_FIELD(next_buf);
	PRINT_FIELD(buf_length);

	printk("reserved=TODO\nctx=TODO\n");

	PRINT_FIELD(desc_list);
	PRINT_FIELD(desc_list->buf_addr);
	PRINT_FIELD(desc_list->buf_size);
	PRINT_FIELD(desc_list->data_offset);
	PRINT_FIELD(desc_list->data_size);

	printk("control=TODO\nhw_desc_buf=TODO\n");

	if (skb->desc_list->data_size >= 4)
	{
		printk("DATA=");
		printk(itox(*(uint32_t*)(skb->desc_list->buf_addr + skb->desc_list->data_offset)));
		printk("\n");
	}

#undef PRINT_FIELD
}

void dump_skb_data(adf_nbuf_t skb)
{
	unsigned char *buffer = (unsigned char *)(skb->desc_list->buf_addr + skb->desc_list->data_offset);

	printk("BUF=");
	dump_buffer(buffer, skb->desc_list->data_size);
}

/* 
typedef struct __data_header {
	a_uint8_t   datatype;
	a_uint8_t   ni_index;
	a_uint8_t   vap_index;
	a_uint8_t   tidno;
	a_uint32_t  flags;  
	a_int8_t    keytype;
	a_int8_t    keyix;
	a_uint8_t   cookie;
	a_uint8_t   pad;
} POSTPACK ath_data_hdr_t;
*/
void dump_ath_data_hdr_t(ath_data_hdr_t *hd)
{
#define PRINT_FIELD(_field) \
	do {					\
		printk(#_field "=");		\
		printk(itox(hd->_field));	\
		printk("\n");			\
	} while(0);

	PRINT_FIELD(datatype);
	PRINT_FIELD(ni_index);
	PRINT_FIELD(vap_index);
	PRINT_FIELD(tidno);
	PRINT_FIELD(flags);
	PRINT_FIELD(keytype);
	PRINT_FIELD(keyix);
	PRINT_FIELD(cookie);
	PRINT_FIELD(pad);

#undef PRINT_FIELD
}


/*
struct ath_rx_status {
    a_uint64_t   rs_tstamp;
    a_uint16_t   rs_datalen;
    a_uint8_t    rs_status;
    a_uint8_t    rs_phyerr;
    int8_t       rs_rssi_combined;
    int8_t       rs_rssi_ctl0;
    int8_t       rs_rssi_ctl1;
    int8_t       rs_rssi_ctl2;
    int8_t       rs_rssi_ext0;
    int8_t       rs_rssi_ext1;
    int8_t       rs_rssi_ext2;
    a_uint8_t    rs_keyix;
    a_uint8_t    rs_rate;
    a_uint8_t    rs_antenna;
    a_uint8_t    rs_more;
    a_uint8_t    rs_isaggr;
    a_uint8_t    rs_moreaggr;
    a_uint8_t    rs_num_delims;
    a_uint8_t    rs_flags;
    a_uint8_t    rs_dummy;
    a_uint32_t   evm0;
    a_uint32_t   evm1;
    a_uint32_t   evm2;
};
*/
void dump_rx_status(struct ath_rx_status *status)
{
#define PRINT_FIELD(_field) \
	do {					\
		printk(#_field "=");		\
		printk(itox(status->_field));	\
		printk("\n");			\
	} while(0);

	printk("rs_tstamp=");
	printk(itox(((a_uint32_t*)&status->rs_tstamp)[1]));
	printk(itox(((a_uint32_t*)&status->rs_tstamp)[0]));
	printk("\n");
	
	PRINT_FIELD(rs_datalen);
	PRINT_FIELD(rs_status);
	PRINT_FIELD(rs_phyerr);
	PRINT_FIELD(rs_rssi_combined);
	PRINT_FIELD(rs_rssi_ctl0);
	PRINT_FIELD(rs_rssi_ctl1);
	PRINT_FIELD(rs_rssi_ctl2);
	PRINT_FIELD(rs_rssi_ext0);
	PRINT_FIELD(rs_rssi_ext1);
	PRINT_FIELD(rs_rssi_ext2);
	PRINT_FIELD(rs_keyix);
	PRINT_FIELD(rs_rate);
	PRINT_FIELD(rs_antenna);
	PRINT_FIELD(rs_more);
	PRINT_FIELD(rs_isaggr);
	PRINT_FIELD(rs_moreaggr);
	PRINT_FIELD(rs_num_delims);
	PRINT_FIELD(rs_flags);
	PRINT_FIELD(rs_dummy);
	PRINT_FIELD(evm0);
	PRINT_FIELD(evm1);
	PRINT_FIELD(evm2);

#undef PRINT_FIELD
}

#endif



