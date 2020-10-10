#include <stdio.h>
#include <iostream>

#include "osal_wi.h"


char usage[] =

"\n"
"  constantjam - Mathy Vanhoef\n"
"\n"
"  usage: constantjam interface [channel]\n"
"\n"
"    Warnings:\n"
"    - Some devices stop operating properly when in monitor mode\n"
"      and attempting to transmit packets while you are jamming!\n"
"      Setting force_channel_idle may help if you experience problems.\n"
"    - Some devices stop recieving frames after being jammed for a long time.\n"
"      Perhaps because they configured an unrealisticly high noise-floor level.\n"
"      Reset the device you jammed if it no longer seems to be working!\n";

int main(int argc, char *argv[])
{
	wi_dev dev;

	if (argc < 2) {
		puts(usage);
		return 1;
	}

	if (osal_wi_open(argv[1], &dev) < 0) return 1;
	if (argc >= 3) {
		if (osal_wi_setchannel(&dev, atoi(argv[2])) < 0) {
			fprintf(stderr, "Failed to set channel\n");
			return 1;
		}
	}

	osal_wi_constantjam_start(&dev);

	printf("\n\tRemember: public firmware doesn't support constant jamming!\n\n");
	printf("Jamming channel %d. Press ENTER to stop ...\n", osal_wi_getchannel(&dev));
	getchar();

	osal_wi_constantjam_stop(&dev);

	return 0;
}

