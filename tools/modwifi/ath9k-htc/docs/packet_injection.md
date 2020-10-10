# Preventing Modifications

By default the driver/firmware may modify the content of injected packets. The following sections explain how we prevented this.

## Sequence Number Control

From the datasheet we learn that bit 29 of the `MAC_PCU_STA_ADDR_U16` register must be set to 1. This bit is called `AR_STA_ID1_PRESERVE_SEQNUM`. And if it is set to 1, it "stops the PCU from replacing the sequence number". Hence the internal WiFi chip should not be replacing the sequence number. We haven't tested this in detail though, and to be sure this doesn't happen, we mark injected frames (that should use the sequence number as given by the user) as CF-Poll frames.

It's actually the responsibility of firmware to automatically increment and assign sequence numbers. We patched the firmware to respect the `ATH_HTC_TX_ASSIGN_SEQ` flag. If it is *not* set, we assure the sequence number is not modified. We do remark that the driver/firmware make inconsistent use of these flags, and likely contains bugs [1].

# References

[1] https://github.com/qca/open-ath9k-htc-firmware/issues/47

