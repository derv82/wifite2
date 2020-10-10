# Receive Path

This document explains how packets are received and handled by the firmware.

## Initialization

Before entering the infinite loop in `wlan_task`, certain things are initialized. Among these things are the receive descriptors. This is done in `ath_desc_alloc` (see memory management that they are indeed allocated here and put into a list). In total `ATH_RXDESC` descriptors will be allocated, and alongside `ATH_RXBUF` buffers. These two defines are equal to each other, and in our case equal to 11 (in a debug build there are apparently 30). 

The general type of a descriptor is `struct ath_rx_desc`. The device specific structure for us is `struct ar5416_desc_20` (for both the K2 and Magpie chips). Note that `ar5416_desc` is defined to be equal to `ar5416_desc_20`. In the firmware code only `struct ar5416_desc` is used.

In the function `ath_rxdesc_init` we can see that the field `ds->ds_nbuf` is initialized to a new skb buffer. We then get the physical address of the start of the buffer memory, and assign this to `ds->data`. So `ds->data` contains the physical address of the actual data buffer (and hence also the virtual address).

* `sc_rxdesc`: active descriptors that are going to be used.
* `sc_rxdesc_idle`: those that have been processed after the interrupt, but are awaiting to be fully transmitted to the host. They are added **at the tail of** `sc_rxdesc` in `ath_rx_complete` (which is in turn called from `tgt_HTCSendCompleteHandler`).

**TODO: Further documentation**

