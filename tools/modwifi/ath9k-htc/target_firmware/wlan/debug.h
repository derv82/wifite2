#ifndef _DEV_ATH_DEBUG_H
#define _DEV_ATH_DEBUG_H
/**
 * It is useful to have basic debug output over USB. Note that for more
 * serious debugging/problems you still have to use a UART.
 */

#include "wlan_hdr.h"
#include "ah_desc.h"

/** Add a message to debug log */
int printk(const char *format);
/** Convert number to hexadecimal representation */
const char *itox(unsigned int val);
/** Get the current debug messages, starting from a given offset */
unsigned int get_dmesg(unsigned int offset, char *buffer, unsigned int length);

void dump_rx_macbufs(struct ath_hal *ah);
void dump_rx_tailq(struct ath_softc_tgt *sc);
void dump_buffer(unsigned char *buffer, int size);

void dump_skb(adf_nbuf_t skb);
void dump_skb_data(adf_nbuf_t skb);
void dump_ath_data_hdr_t(ath_data_hdr_t *hd);
void dump_rx_status(struct ath_rx_status *status);

#endif // _DEV_ATH_DEBUG_H

