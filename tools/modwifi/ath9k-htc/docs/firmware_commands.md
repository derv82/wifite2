## Adding WMI commands

The driver (your computer) can send commands to the firmware (the WiFi dongle). In general this is done using so called WMI commands. This document explains the files you need to edit in order to add your own commands. A command can send arbitrary data as a parameter, and the firmware can also include arbitrary data in its response.

### Firmware

1. First add a new enum entry to represent the command in `wlan/include/wmi.h`.
2. You will likely also want to add a structure representing the data your command will expect (i.e. the parameters of the command), and the data it will return (i.e. the return value sent by the firmware). This is also done in `wlan/include/wmi.h`. Postfix your structures with \_CMD and \_RESP. Remember to use PREPACK and POSTPACK.
2. Then program a handler for this case in `wlan/if_ath.c` in the Magpie_Sys_DispatchEntries array. Base your code on the other functions to know how to program these.

### Driver

1. In `wmi.h` add new enum entry for the command. Also add the \_CMD and \_RESP
structure as done in the firmware.
2. Now add a debugfs entry in  `htc_drv_debug.c` using `debugfs_create_file`, and
by declaring the corresponding read/write operations. See other entires for examples.

For convenience we let the user issue commands to the driver by writing or reading to debugfs. This is useful to manually issue commands from command line, but can still be used to programmatically read/write to them. Mount the debugfs file system using:

    mount -t debugfs none /sys/kernel/debug

### Notes

In general, pay attention to correctly convert integers to and from network and host order. See other WMI functions for examples.
