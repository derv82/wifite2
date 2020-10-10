Compile and load this kernel module by executing:

	./load.sh

And that's it! You can now plug in your Wi-Fi card, and it will send acknowledgements to any Wi-Fi frame if the first 5 bytes of the destination MAC address equal its own address. In other words, you can now inject packets using the MAC address of the device, where the last byte of the MAC address can be anything. When other devices sent frames to these spoofed MAC addresses, the Atheros device will send ACKs.

**Plug in the device after loading the kernel module!**
