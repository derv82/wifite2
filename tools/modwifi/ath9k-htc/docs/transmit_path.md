# Transmission Path

This gives a quick overview of the functions involved being called when transmitting a packet.

## Standard Transmission

Let's consider management frames only for now. The ROM OS calls the `tgt_HTCRecv_mgmthandler` callback function when a frame is requested to be transmitted. The main function call path is:

1. `tgt_HTCRecv_mgmthandler`: called from ROM OS.
2. `ath_tgt_send_mgt`: initializes the transmit descriptor and transmit options based on the sbk buffer.
3. `ath_tgt_txqaddbuf`: Adds the packet to the tail of the `&sc->sc_txq[1]` queue. Then, if the field `txq->axq_link` is NULL, it initializes `AR_QTXDP` to the pointer to the buffer. Otherwise `*txq->axq_link` is set to the pointer of the buffer. Finally the field `txq->axq_link` is set the last part of the buffer being added, and `ah->ah_startTxDma` is called.
4. `ar5416StartTxDma`: Simply sets a bit in `AR_Q_TXE` to enable transmission.

When a frame has been transmitted, the following actions are taken:

1. `owl_tgt_tx_tasklet`: on every `ath_intr` loop this tasklet is requested to be run. The tasklet calls `ATH_TXQ_SETUP` for every queue, which essentially checks if the queue is initialized (aka whether it could have been used). If it is used it calls `owltgt_tx_processq` (the CAB queue is handled by another function).
2. `owltgt_tx_processq`: Iterates over all buffers until it's empty or encounters a packet that is still being transmitted. The packets that have been transmitted are removed from the list. If the list becomes empty after removing a packet, `txq->axq_link` is set to NULL.
3. `ath_buf_comp`: Frees the skb and returns the descriptor back to the list (essentially also freeing it).

## Crap After Beacon (CAB) queue

There is actually also a special Crap After Beacon (CAB) queue. 

To quote [1]: Queue 8 is reserved for traffic that has to go out immediately after a
beacon has been sent (Queue 9 is for the beacons themselves).  If at least
one associated client is in power save mode, the AP has to buffer
multicasts and broadcasts instead of sending them immediately.  The
buffered packets are sent out right after the next beacon that is a DTIM
(clients are expected to wake up at least every DTIM).  Queue 8 is
specially programmed to get enabled as soon as a beacon has been sent. 

To quote [1] again: From the hardware's point of view, the queues 8 and 9 are only special in
the way they are 'enabled':  If you stuff a packet into queues 0..3 and
signal the hardware there are packets to send, the hardware will
immediately start transmitting these packets (of course unless there are
packets to be sent from a higher-numbered queue).  This is also sometimes
referred to as 'immediate frame scheduling'.  Queue 9 for comparison is
programmed to get enabled by a timer event (namely the hardware's beacon
timer): driver software submits the beacon frame to queue 9 some time
before the beacon is actually to be sent, but hardware won't actually
start transmitting from this queue until the timer fires.  Similarly,
the 'enabling condition' of queue 8 is the transmission of a beacon - the
hardware will of course not start transmitting from this queue until queue
9 is empty.

Regarding 802.11e, queues 8 and 9 are just like the other queues, meaning
that driver software can assign cwmin/cwmax/AIFS/TxOP paramters to these
queues.  It's up to the driver software to assign these values.  Since
queue 9 is exclusively for beacons which are management frames, and
802.11e says that management frames shall be sent with the EDCA parameters
of AC_VO, I'd expect that queue 9 uses the same EDCA parameters as queue 3. Queue
8 otoh typically carries ordinary data frames, so the EDCA
parameters of AC_BE might be more appropriate. 

[1] http://madwifi-users.20070.n2.nabble.com/Question-on-atheros-HW-queues-td2504536.html

