#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>

#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/time.h>
#include <sys/stat.h>
#include <netpacket/packet.h>
#include <linux/if_ether.h>
#include <linux/if.h>
#include <linux/wireless.h>
#include <netinet/in.h>
#include <linux/if_tun.h>
#include <sys/utsname.h>
#include <net/if_arp.h>

#include <sstream>
#include <iostream>
#include <fstream>

/**
 * Documentation: http://www.carisma.slowglass.com/~tgr/libnl/doc/core.html
 */
#include <netlink/genl/genl.h>
#include <netlink/genl/family.h>
#include <netlink/genl/ctrl.h>
#include <netlink/msg.h>
#include <netlink/attr.h>

#include <sys/mount.h>
#include <linux/limits.h>
#include <sys/stat.h>
#include <fcntl.h>

#include "ieee80211header.h"
#include "osal_nl.h"
#include "osal_wi.h"
#include "crc.h"
#include "util.h"

/**
 * Display warning when a read or write takes too long. This usually indicates the
 * device is not working properly anymore. Plugging it in and out should fix this.
 */
#define WARN_LONG_READWRITE

//
// Types
//

#define PACKED __attribute__((packed))

// radiotap header for injecting frames - generally is ignoed anyway...
typedef struct radiotap_inject {
        uint8_t        it_version;     /* set to 0 */
        uint8_t        it_pad;
        uint16_t       it_len;         /* entire length */
        uint32_t       it_present;     /* fields present */
	uint8_t        rate;
	// txflags?
} PACKED radiotap_inject;

static const int RADIOTAP_INJECT_PRESENT = 0x00000004;


//
// Netlink Sockets
//

static int osal_wi_debug = 0;
static volatile int phyindex = -1;


static int error_handler(struct sockaddr_nl *nla, struct nlmsgerr *err, void *arg)
{
	int *ret = (int*)arg;
	*ret = err->error;
	return NL_STOP;
}

static int ack_handler(struct nl_msg *msg, void *arg)
{
	int *ret = (int*)arg;
	*ret = 0;
	return NL_STOP;
}

static int finish_handler(struct nl_msg *msg, void *arg)
{
	int *ret = (int*)arg;
	*ret = 0;
	return NL_SKIP;
}

static int iface_handler(struct nl_msg *msg, void *arg)
{
	struct genlmsghdr *gnlh = (struct genlmsghdr *)nlmsg_data(nlmsg_hdr(msg));
	struct nlattr *tb_msg[NL80211_ATTR_MAX + 1];
	const char *devname = (const char *)arg;

	nla_parse(tb_msg, NL80211_ATTR_MAX, genlmsg_attrdata(gnlh, 0),
		  genlmsg_attrlen(gnlh, 0), NULL);

	if (!tb_msg[NL80211_ATTR_WIPHY] || !tb_msg[NL80211_ATTR_IFNAME])
		return NL_SKIP;

	if (strcmp(devname, nla_get_string(tb_msg[NL80211_ATTR_IFNAME])) == 0)
	{
		phyindex = nla_get_u32(tb_msg[NL80211_ATTR_WIPHY]);
	}

	//if (tb_msg[NL80211_ATTR_IFINDEX])
	//	printf("\tifindex %d\n", nla_get_u32(tb_msg[NL80211_ATTR_IFINDEX]));

	return NL_SKIP;
}


int osal_wi_dev2phy(const char *devname)
{
	struct nl80211_state state;
	struct nl_cb *cb;
	struct nl_cb *s_cb;
	struct nl_msg *msg;
	int err;

	err = nl80211_init(&state);
	if (err) return 1;

	msg = nlmsg_alloc();
	if (!msg) {
		fprintf(stderr, "failed to allocate netlink message\n");
		return 2;
	}

	cb = nl_cb_alloc(osal_wi_debug ? NL_CB_DEBUG : NL_CB_DEFAULT);
	s_cb = nl_cb_alloc(osal_wi_debug ? NL_CB_DEBUG : NL_CB_DEFAULT);
	if (!cb || !s_cb) {
		fprintf(stderr, "failed to allocate netlink callbacks\n");
		err = 2;
		nlmsg_free(msg);
		return -1;
	}

	genlmsg_put(msg, 0, 0, state.nl80211_id, 0, NLM_F_DUMP,
		NL80211_CMD_GET_INTERFACE, 0);
	nl_cb_set(cb, NL_CB_VALID, NL_CB_CUSTOM, iface_handler, (void*)devname);
	nl_socket_set_cb(state.nl_sock, s_cb);

	err = nl_send_auto_complete(state.nl_sock, msg);
	if (err < 0) {
		nl_cb_put(cb);
		nlmsg_free(msg);
		return -1;
	}

	err = 1;

	nl_cb_err(cb, NL_CB_CUSTOM, error_handler, &err);
	nl_cb_set(cb, NL_CB_FINISH, NL_CB_CUSTOM, finish_handler, &err);
	nl_cb_set(cb, NL_CB_ACK, NL_CB_CUSTOM, ack_handler, &err);

	while (err > 0)
		nl_recvmsgs(state.nl_sock, cb);

	nl_cb_put(cb);
	nlmsg_free(msg);
	return phyindex;
}

//
// DebugFS Interface
//

// http://lists.lttng.org/pipermail/lttng-dev/2009-January/011886.html
static int getdebugfsdir(char mnt_dir_out[PATH_MAX])
{
	char mnt_dir[PATH_MAX];
	char mnt_type[PATH_MAX];
	int trymount_done = 0;

	FILE *fp = fopen("/proc/mounts", "r");
	if (!fp)
		return -EINVAL;

find_again:
	while (1) {
		if (fscanf(fp, "%*s %s %s %*s %*s %*s", mnt_dir, mnt_type) <= 0)
			break;

		if (!strcmp(mnt_type, "debugfs")) {
			strcpy(mnt_dir_out, mnt_dir);
			return 0;
		}
	}

	if (!trymount_done) {
		mount("debugfs", "/sys/kernel/debug/", "debugfs", 0, NULL);
		trymount_done = 1;
		goto find_again;
	}

	return -ENOENT;
}


int writeto(const std::string &filename, const std::string &content)
{
	std::ofstream file;

	file.open(filename);
	if (!file.is_open()) {
		std::cerr << "Failed to open " << filename << " for writing\n";
		return -1;
	}
	file << content;
	file.close();

	return 0;
}

static int readnum(const char *file, uint32_t *value)
{
	char buf[1024];
	const char *pos;
	int fd, rval;
	uint32_t test;

	fd = open(file, O_RDONLY);
	if (fd < 0) {
		fprintf(stderr, "Failed to open %s for reading: ", file);
		perror("");
		return -1;
	}

	rval = read(fd, buf, sizeof(buf));
	if (rval < 0) {
		fprintf(stderr, "Error reading from %s: ", file);
		perror("");
		return -1;
	}

	close(fd);

	// find newline of description
	pos = strchr(buf, '\n');
	if (pos == NULL) {
		fprintf(stderr, "Unexpected output in debugfs register read:\n\tfile: %s\n\tcontent >%s<",
			file, buf);
		return -1;
	}
	pos++;

	// scan the second line
	if (sscanf(pos, "Value: 0x%x = %u", value, &test) != 2 || *value != test) {
		fprintf(stderr, "Unexpected output in debugfs register read:\n\tfile: %s\n\tcontent >%s<",
			file, pos);
		return -1;
	}

	return 0;
}


static int writetocmd(wi_dev *dev, const char *cmdname, const char *cmd)
{
	char debugfsdir[PATH_MAX];
	char path[PATH_MAX];

	if (getdebugfsdir(debugfsdir) < 0)
		return -1;

	snprintf(path, sizeof(path), "%s/ieee80211/phy%d/ath9k_htc/%s",
		debugfsdir, dev->phyidx, cmdname);

	return writeto(path, cmd);
}

static int writetocmd(wi_dev *dev, const std::string &cmdname, const std::string &cmd)
{
	char debugfsdir[PATH_MAX];
	std::ostringstream path;

	if (getdebugfsdir(debugfsdir) < 0)
		return -1;

	path << debugfsdir << "/ieee80211/phy" << dev->phyidx << "/ath9k_htc/" << cmdname;

	return writeto(path.str(), cmd);
}

static int readfrom(const std::string &filename)
{
	std::ifstream file;
	std::string line;

	file.open(filename);
	if (!file.is_open()) {
		std::cerr << "Failed to open " << filename << " for reading\n";
		return -1;
	}
	file >> line;
	file.close();

	return 0;
}

static int readfromcmd(wi_dev *dev, const std::string &cmdname)
{
	char debugfsdir[PATH_MAX];
	std::ostringstream path;

	if (getdebugfsdir(debugfsdir) < 0)
		return -1;

	path << debugfsdir << "/ieee80211/phy" << dev->phyidx << "/ath9k_htc/" << cmdname;

	return readfrom(path.str());
}

int osal_wi_set_mac(wi_dev *dev, const MacAddr &mac)
{
	return writetocmd(dev, "macaddr", mac.tostring());
}

int osal_wi_set_macmask(wi_dev *dev, const MacAddr &mask)
{
	return writetocmd(dev, "bssidmask", mask.tostring());
}

int osal_wi_set_inject_noack(wi_dev *dev, bool noack)
{
	char num[16];

	snprintf(num, sizeof(num), "%d", noack);

	return writetocmd(dev, "inject_noack", num);
}

int osal_wi_set_preserve_seqnum(wi_dev *dev, bool ownSeqenceNo)
{
	char num[16];

	snprintf(num, sizeof(num), "%d", ownSeqenceNo);

	return writetocmd(dev, "preserve_seqnum", num);
}

static bool is_ack_from(uint8_t *buf, size_t buflen, void *data)
{
	const MacAddr *mac = (const MacAddr *)data;
	ieee80211header *hdr = (ieee80211header*)buf;

	if (buflen < IEEE80211_MINSIZE)
		return false;

	// Is it an ACK packet?
	if (hdr->fc.type != 1 || hdr->fc.subtype != 13)
		return false;

	// Is it to the correct MAC?
	if (MacAddr(hdr->addr1) != *mac)
		return false;

	//std::cout << "Got an ACK towards " << *mac << std::endl;

	return true;
}

// On the packet capture of the injection interface itself we see:
// - The ACK's *other* station send in response to our frame
// - The retransmission of frames sent by *other* stations
//
// However we do not see:
// - The ACK's generated by *ourselves*
// - The retransmission of frames we are sending *ourselves*
int osal_wi_ping(wi_dev *dev, const MacAddr &dst)
{
	uint8_t buf[2048];

	// generate a random source MAC address to use
	MacAddr src = MacAddr::random();

	// create dummy packet
	ieee80211header hdr;
	dst.setbuf(hdr.addr1);
	src.setbuf(hdr.addr2);
	hdr.sequence.seqnum = rand();

	// send the packet
	//std::cout << "Pinging " << dst << " using MAC " << src << std::endl;
	if (osal_wi_write(dev, (uint8_t*)&hdr, sizeof(hdr)) < 0) {
		fprintf(stderr, "Failed to inject ping packet\n");
		return -1;
	}

	// monitor 5ms for an ACK
	struct timespec timeout;
	timeout.tv_sec = 0;
	timeout.tv_nsec =  5 * 1000000;
	int rval = osal_wi_sniff(dev, buf, sizeof(buf), is_ack_from, &src, &timeout);
	if (rval < 0) return -1;

	return rval > 0;
}

int osal_wi_get_mtu(wi_dev *dev)
{
	struct ifreq ifr;
	int rval;

	// set ioctl cmd info
	strncpy(ifr.ifr_name, dev->name, IFNAMSIZ);
	ifr.ifr_mtu = -1;

	rval = ioctl(dev->fd, SIOCGIFMTU, (caddr_t)&ifr);
	if (rval < 0) {
		fprintf(stderr, "ioctl(SIOCSIFMTU) failed on %s:", dev->name);
		perror("");
		return -1;
	}

	return rval;
}

int osal_wi_set_mtu(wi_dev *dev, int mtu)
{
	struct ifreq ifr;

	// set ioctl cmd info
	strncpy(ifr.ifr_name, dev->name, IFNAMSIZ);
	ifr.ifr_mtu = mtu;

	if (ioctl(dev->fd, SIOCSIFMTU, (caddr_t)&ifr) < 0) {
		fprintf(stderr, "ioctl(SIOCSIFMTU) failed on %s:", dev->name);
		perror("");
		return -1;
	}

	return 0;
}

int osal_wi_jam_beacons(wi_dev *dev, const MacAddr &bssid, int msecs)
{
	std::ostringstream command;

	command << bssid << "," << msecs;

	// jam_beacons will take duration of 0 as an infinite jam
	return writetocmd(dev, "reactivejam", command.str());
}


int osal_wi_constantjam_start(wi_dev *dev)
{
	return writetocmd(dev, "constantjam", "1");
}

int osal_wi_constantjam_stop(wi_dev *dev)
{
	return writetocmd(dev, "constantjam", "0");
}


//
// Open Monitor Interface
//

int osal_wi_open(char *iface, wi_dev *dev)
{
	struct ifreq ifr;
	struct iwreq wrq;
	struct sockaddr_ll sll;
	struct packet_mreq mr;
	int fd;

	// Create packet socket (PF_PACKET) at the device layer.
	fd = socket(PF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
	if (fd < 0) {
		perror("socket(PF_PACKET) failed: ");
		return -1;
	}

	// find the interface index - similar to if_nametoindex
	memset(&ifr, 0, sizeof(ifr));
	strncpy(ifr.ifr_name, iface, sizeof(ifr.ifr_name) - 1);
	if (ioctl(fd, SIOCGIFINDEX, &ifr) < 0) {
		fprintf(stderr, "ioctl(SIOCGIFINDEX) failed on interface %s: ", iface);
		perror("");
		return -1 ;
	}

	// lookup the hardware type
	memset(&sll, 0, sizeof(sll));
	sll.sll_family   = AF_PACKET;
	sll.sll_ifindex  = ifr.ifr_ifindex;
	sll.sll_protocol = htons(ETH_P_ALL);
	if (ioctl(fd, SIOCGIFHWADDR, &ifr) < 0) {
		fprintf(stderr, "ioctl(SIOCGIFHWADDR) failed on interface %s: ", iface);
		perror("");
		return -1;
	}

	// lookup iw mode
	memset(&wrq, 0, sizeof(wrq));
	strncpy(wrq.ifr_name, iface, IFNAMSIZ);
	if (ioctl(fd, SIOCGIWMODE, &wrq) < 0) {
		/* most probably not supported (ie for rtap ipw interface) *
		 * so just assume its correctly set...                     */
		wrq.u.mode = IW_MODE_MONITOR;
	}

	// Is interface set to up, broadcast & running?
	if ((ifr.ifr_flags | IFF_UP | IFF_BROADCAST | IFF_RUNNING) != ifr.ifr_flags) {
		/* Bring interface up*/
		ifr.ifr_flags |= IFF_UP | IFF_BROADCAST | IFF_RUNNING;

		if (ioctl(fd, SIOCSIFFLAGS, &ifr) < 0 ) {
			fprintf(stderr, "ioctl(SIOCSIFFLAGS) failed on interface %s: ", iface);
			perror("");
			return -1;
		}
	}

	// bind the raw socket to the interface
	if (bind(fd, (struct sockaddr *)&sll, sizeof(sll)) < 0) {
		fprintf(stderr, "bind(ETH_P_ALL) failed on interface %s:", iface);
		perror("");
		return -1;
	}

	// lookup the hardware type
	if (ioctl(fd, SIOCGIFHWADDR, &ifr) < 0)
	{
		fprintf(stderr, "ioctl(SIOCGIFHWADDR) failed on interface %s: ", iface);
		perror("");
		return -1;
	}

	// enable promiscuous mode
	memset(&mr, 0, sizeof(mr));
	mr.mr_ifindex = sll.sll_ifindex;
	mr.mr_type    = PACKET_MR_PROMISC;
	if (setsockopt(fd, SOL_PACKET, PACKET_ADD_MEMBERSHIP, &mr, sizeof(mr)) < 0) {
		fprintf(stderr, "setsockopt(PACKET_MR_PROMISC) failed on interface %s: ", iface);
		perror("");
		return -1;
	}

	// set to non-blocking
	fcntl(fd, F_SETFL, O_NONBLOCK);

	dev->fd = fd;
	dev->phyidx = osal_wi_dev2phy(iface);
	strncpy(dev->name, iface, sizeof(dev->name));
	dev->includeBadFcs = true;

	return 0;
}

int osal_wi_read(wi_dev *dev, uint8_t *buf, size_t len)
{
	ieee80211_radiotap_header *tap = (ieee80211_radiotap_header*)buf;
	int readlen;

	// Frames shorter than IEEE80211_MINSIZE are possible!
	readlen = osal_wi_read_raw(dev, buf, len);
	if (readlen < 0) {
		return readlen;
	} else if ((size_t)readlen < sizeof(ieee80211_radiotap_header)) {
		fprintf(stderr, "WTF: Frame doesn't contain radiotap header\n");
		return 0;
	}

	// TODO: Check radiotap header if FCS is present (this appeared unreliable though)
	// sanity check: is there enough space for the FCS?
	if (tap->it_len + 4 > readlen)
		return 0;

	// if packets with bad FCS should be dropped, then drop if needed
	if (!dev->includeBadFcs && !endswith_valid_crc(buf + tap->it_len, readlen - tap->it_len))
		return 0;
	
	// remove the FCS
	readlen -= 4;

	// remove radiotap header
	readlen -= tap->it_len;
	if (readlen < 0) {
		fprintf(stderr, "WTF: Wrong radiotap header on interface %s\n", dev->name);
		return 0;
	}
	memmove(buf, buf + tap->it_len, readlen);

	return readlen;
}


int osal_wi_read_raw(wi_dev *dev, uint8_t *buf, size_t len)
{
	int readlen;
#ifdef WARN_LONG_READWRITE
	struct timespec start, end, delta;

	clock_gettime(CLOCK_MONOTONIC, &start);
#endif

	readlen = read(dev->fd, buf, len);
	if (readlen < 0) {
		perror("failed to read from interface");
		return -1;
	}
	else if ((size_t)readlen < sizeof(ieee80211_radiotap_header)) {
		fprintf(stderr, "No space for radiotap header?!\n");
		return -1;
	}

#ifdef WARN_LONG_READWRITE
	clock_gettime(CLOCK_MONOTONIC, &end);
	timespec_diff(&end, &start, &delta);
	
	if (delta.tv_sec > 0)
		printf("Warning: %s took %lds %ldms\n", __FUNCTION__, delta.tv_sec, delta.tv_sec/1000000);
#endif

	return readlen;
}

int osal_wi_write(wi_dev *dev, uint8_t *buf, size_t len)
{
	unsigned char tmpbuf[4096];
	int rval;
	radiotap_inject tap;
#ifdef WARN_LONG_READWRITE
	struct timespec start, end, delta;

	clock_gettime(CLOCK_MONOTONIC, &start);
#endif

	memset(&tap, 0, sizeof(tap));
	tap.it_len += sizeof(tap);
	tap.it_present = RADIOTAP_INJECT_PRESENT;
	// Strageness: the rate in the radiotap header is generally ignored by the
	// device/driver, in the sense that we cannot control the bitrate. However,
	// when set to zero, injection of some frames will fail. In particular we
	// encountered this when injecting a beacon.
	tap.rate = 2;

	if (len + sizeof(tap) > sizeof(tmpbuf)) {
		fprintf(stderr, "%s: packet too big to send\n", __FUNCTION__);
		return -1;
	}

	memcpy(tmpbuf, &tap, sizeof(tap));
	memcpy(tmpbuf + sizeof(tap), buf, len);
	len += sizeof(tap);

	rval = write(dev->fd, tmpbuf, len);
	if (rval < 0 && errno == EAGAIN) {
		// On EAGAIN error, sleep 5ms and try again
		usleep(5000);
		rval = write(dev->fd, tmpbuf, len);
	}
	if (rval < 0 && errno == EAGAIN) {
		// Still not working? Change channel for quick reset attempt.
		int chan = osal_wi_getchannel(dev);
		osal_wi_setchannel(dev, chan ^ 1);
		osal_wi_setchannel(dev, chan);
		usleep(5000);
		rval = write(dev->fd, tmpbuf, len);
	}

	// check if write was successful
	if (rval < 0 || (size_t)rval != len) {
		fprintf(stderr, "Write failed on interface %s:", dev->name);
		perror("");
		fprintf(stderr, "Wanted to send %d bytes (with radiotap header of %d bytes)\n", (int)len, (int)sizeof(radiotap_inject));
		return -1;
	}
	rval -= sizeof(tap);

	if (rval < 0)
	{
		if(errno == EAGAIN || errno == EWOULDBLOCK || errno == ENOBUFS || errno == ENOMEM )
		{
			usleep(1000);
			return 0;
		}

		fprintf(stderr, "write failed to interface %s", dev->name);
		perror("");
		return -1;
	}

#ifdef WARN_LONG_READWRITE
	clock_gettime(CLOCK_MONOTONIC, &end);
	timespec_diff(&end, &start, &delta);
	
	if (delta.tv_sec > 0)
		printf("Warning: %s took %lds %ldms\n", __FUNCTION__, delta.tv_sec, delta.tv_sec/1000000);
#endif

	return rval;
}

int osal_wi_sniff(wi_dev *dev, uint8_t *buf, size_t buflen, FilterFunc filter, void *data, struct timespec *timeout)
{
	struct timespec end, timeleft;
	fd_set set;
	int rval, len;

	clock_gettime(CLOCK_MONOTONIC, &end);
	timespec_add(&end, timeout, &end);
	//while (entry->mactimestamp1 == 0 || entry->mactimestamp2 == 0)
	while (1)
	{
		FD_ZERO(&set);
		FD_SET(dev->fd, &set);

		clock_gettime(CLOCK_MONOTONIC, &timeleft);
		if (timespec_cmp(&end, &timeleft) <= 0) break;
		timespec_diff(&end, &timeleft, &timeleft);

		rval = pselect(dev->fd + 1, &set, NULL, NULL, &timeleft, NULL);
		if (rval < 0) {
			perror("error in select");
			return -1;
		} else if (rval == 0) {
			break;
		}

		if (!FD_ISSET(dev->fd, &set)) {
			fprintf(stderr, "CRITICAL: pselect returned > 0 but fd_set not set?!\n");
			exit(-1);
		}
		
		len = osal_wi_read(dev, buf, buflen);
		if (len < 0) return -1;

		if (filter(buf, buflen, data))
			return len;
	}

	return 0;
}

int osal_wi_flush(wi_dev *dev)
{
	uint8_t buf[4096];
	int flags = fcntl(dev->fd, F_GETFL, 0);
	if (flags < 0) return -1;
	if (fcntl(dev->fd, F_SETFL, flags | O_NONBLOCK) < 0) return -1;

	while (read(dev->fd, buf, sizeof(buf)) > 0)
		;
	
	return fcntl(dev->fd, F_SETFL, flags);
}

int osal_wi_getchannel(wi_dev *dev)
{
	struct iwreq wrq;
	int frequency;

	memset(&wrq, 0, sizeof(wrq));
	strncpy(wrq.ifr_name, dev->name, IFNAMSIZ);

	if (ioctl(dev->fd, SIOCGIWFREQ, &wrq) < 0) {
		fprintf(stderr, "Error in ioctl(SIOCGIWFREQ) of %s:", dev->name);
		perror("");
		return -1;
	}

	frequency = wrq.u.freq.m;
	if (frequency > 100000000)
		frequency/=100000;
	else if (frequency > 1000000)
		frequency/=1000;

	// channels in 2.4GHz range start at 2412kHz and incease with 5kHz for each channel number.
	if (frequency >= 2412 && frequency <= 2472)
		return (frequency - 2412) / 5 + 1;
	// channel 14 is a special case
	if (frequency == 2484)
		return 14;
	// channel 34 to 64 in 5 GHZ range
	if (frequency >= 5170 && frequency <= 5320)
		return 34 + (frequency - 5170) / 5;

	fprintf(stderr, "%s: TODO: Convert frequency %d to channel number\n", __FUNCTION__, frequency);
	return -1;
}

int osal_wi_setchannel(wi_dev *dev, int channel)
{
	struct iwreq wrq;
	int rval = 0;

	memset(&wrq, 0, sizeof(wrq));
	strncpy(wrq.ifr_name, dev->name, IFNAMSIZ);
	wrq.u.freq.m = channel;

	// Let the OS check if the channel was valid or not
	rval = ioctl(dev->fd, SIOCSIWFREQ, &wrq);
	if (rval == -EINVAL) {
		fprintf(stderr, "%s: unsupported channel %d\n", __FUNCTION__, channel);
		return -1;
	} else if (rval < 0) {
		fprintf(stderr, "Error in ioctl(SIOCSIWFREQ) of %s:", dev->name);
		perror("");
		return -1;
	}

	return 0;
}

int osal_wi_include_badfcs(wi_dev *dev, bool includeBadFcs)
{
	dev->includeBadFcs = includeBadFcs;

	return 0;
}

int osal_wi_fastreply_packet(wi_dev *dev, uint8_t *buff, size_t len)
{
	char debugfsdir[PATH_MAX];
	char file[PATH_MAX];
	int fd, rval;

	if (getdebugfsdir(debugfsdir) < 0)
		return -1;

	snprintf(file, sizeof(file), "%s/ieee80211/phy%d/ath9k_htc/fastreply_packet",
		debugfsdir, dev->phyidx);

	fd = open(file, O_WRONLY);
	if (fd < 0) {
		fprintf(stderr, "Failed to open %s for writing: ", file);
		perror("");
		return -1;
	}

	rval = write(fd, buff, len);
	if (rval < 0) {
		fprintf(stderr, "Error writing to %s: ", file);
		perror("");
		return -1;
	}

	close(fd);
	
	return 0;
}


int osal_wi_fastreply_start(wi_dev *dev, const MacAddr &source, int msecs)
{
	std::ostringstream command;

	command << source << "," << msecs;

	return writetocmd(dev, "fastreply_start", command.str());
}

void osal_wi_close(wi_dev *dev)
{
	close(dev->fd);
}

