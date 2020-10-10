
# Memory Management

In this document *firmware* refers to the code we can change, while *ROM OS* refers to the (unknown) code thats hardcoded in the ROM memory of the device.

## Transmiting Packets

Packets that have to be transmitted are given to the firmware by the ROM OS. The firmware registers callbacks to be notified when packets are requested to be transmitted. Important callbacks are:

1. `tgt_HTCRecv_mgmthandler`: Responsible for transmitting management frames (e.g. probe requests). With our modified drivers this is also used to transmit injected packets.
2. `tgt_HTCRecvMessageHandler`: Responsible for transmitting data frames.

The data for these packets is allocated by the ROM OS in a `adf_nbuf_t` buffer. Nevertheless, these buffers will have to be encapsulated in a transmit descriptor. And these transmit descriptors are managed by the firmware and not the ROM OS.

Transmit descriptors are allocated in `ath_tgt_attach` using `ath_desc_alloc` and are put into a list (also see recieve path info). An important remark is that `ath_desc_alloc` allocates descriptors (not buffers) for both the recieve and transmit queue, as well as for beacons. This is is stored in the field `sc_txbuf`. Note that `ath_descdma_setup` is given a pointer to this field, but does not use a for loop to allocate all the buffers! Instead it does one big allocation using `adf_os_dmamem_alloc` of `descSize * nbuf * ndesc` bytes. This big chunk is then divided into packets, and each packet is added to a list. These descriptors are "freed" when shutting down the device. However these free calls are actually just NOPs. Throughout the firmware code you will notice descriptors taken from, and added to, the `sc_txbuf` list. This represents allocation and deallocation of memory! In particular the utility function `ath_tx_freebuf` is used to add descriptors back to the list (and to free the `adf_nbuf_t`, see below). Two example locations where these are freed:

1. `ath_buf_comp` which seems to be used for management packets (called after `tgt_HTCRecv_mgmthandler` ?).
2. `ath_tx_freebuf` which seems to be used for data packets (called after `tgt_HTCRecvMessageHandler` ?).

The `adf_nbuf_t` buffer given by the ROM OS is freed after successful transmission using `ath_tgt_skb_free` which eventually calls `HTC_ReturnBuffers`. So this memory is given back to the ROM OS once the transmission is complete.

## Recieving Packets

The firmware itself allocates memory to store incoming packets. These are of type `adf_nbuf_t` (and maybe encapsulated in a recieve descriptor??). However, it again does not directly use functions like `ath_hal_malloc`. That's because freeing those using `ath_hal_free` is actually a NOP and we'd very quickly run out of memory. Instead, in the function `ath_tgt_attach`, we call `BUF_Pool_create_pool` to allocate a pool of memory. We can then allocation and deallocate buffers using this pool:

* `ath_alloc_skb_align` which in turn calls `BUF_Pool_alloc_buf_align` with arguments `(sc->pool_handle, POOL_ID_WLAN_RX_BUF, RX_HEADER_SPACE, align);`.
*  `BUF_Pool_free_buf` which is called in `tgt_HTCSendCompleteHandler` (probably after successfully sending the frame over USB to the host).

This is interesting, as it teaches us how to easily allocate and free `adf_nbuf_t` buffers ourselves. In particular we can simply allocate a pool ourselves and use that!

Note that 

## adf_nbuf_t skb

Pointers to the socket buffer (skb) will often (always?) have the type `adf_nbuf_t` and be named `skb`. The operations that can be performed on this are defined in `target_firmware/magpie_fw_dev/target/adf`. Originally these were abstraction routines for FreeBSD. We will briefly cover a few important functions

#### adf_nbuf_alloc(size, reserve, align)

A total of `size` bytes are allocated, and `reserve` bytes are reserved for the header (the other bytes are in the tail). The `align` parameter is not used.

#### adf_nbuf_put_tail(buf, size)

Puts `size` amounts of data in the end (in the tail).

## Direct Memory Access (DMA)

In the function `ath_desc_alloc` we see that pointers are mapped to physical memory using `DS2PHYS`. This is actually a NOP operation. The virtual and physical pointers are identical.


