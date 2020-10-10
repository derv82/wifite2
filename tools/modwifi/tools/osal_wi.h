#ifndef OSAL_WI_H__
#define OSAL_WI_H__
/**
 * Operating System Abstraction Layer (OSAL) - Wireless Interface (WI)
 *
 * TODO:
 * - osal_wi_sniff for raw frames (which include radiotap and FCS)
 * - A function to detect a network (probe requests) and return probe response.
 * - Object oriented design?
 */
#include "MacAddr.h"


typedef struct wi_dev_t {
	/** File descriptor to read/write/select socket. */
	int fd;
	/** Index of physical interface: phyX. Used for debugfs. */
	int phyidx;
	/** Name when used to open the interface */
	char name[128];
	/** Include frames with bad FCS when calling read? */
	bool includeBadFcs;
} wi_dev;

int osal_wi_open(char *iface, wi_dev *dev);
/** Read IEEE 802.11 frame without radiotap & FCS. */
int osal_wi_read(wi_dev *dev, uint8_t *buf, size_t len);
/** Read IEEE 802.11 frame including radiotap & FCS. */
int osal_wi_read_raw(wi_dev *dev, uint8_t *buf, size_t len);
int osal_wi_write(wi_dev *dev, uint8_t *buf, size_t len);
int osal_wi_flush(wi_dev *dev);
void osal_wi_close(wi_dev *dev);

int osal_wi_getchannel(wi_dev *dev);
int osal_wi_setchannel(wi_dev *dev, int channel);

int osal_wi_include_badfcs(wi_dev *dev, bool includeBadFcs);

typedef bool FilterFunc(uint8_t *buf, size_t buflen, void *data);
/**
 * Utility function to capture a specific frame
 *
 * < 0	error occured
 * = 0	packet matched the filter
 * > 0	lenght of captured packet is returned
 */
int osal_wi_sniff(wi_dev *dev, uint8_t *buf, size_t buflen, FilterFunc filter, void *data, struct timespec *timeout);

/**
 * Gets the phyX index of the interface name (wlanY, raY, monY,..)
 * That is, devname has phyname of phy<return value>.
 *
 * Returns -1 on error.
 */
int osal_wi_dev2phy(const char *devname);

/** control MAC address, ACK generation, sequence number generation */
int osal_wi_set_mac(wi_dev *dev, const MacAddr &mac);
int osal_wi_set_macmask(wi_dev *dev, const MacAddr &mask);
int osal_wi_set_inject_noack(wi_dev *dev, bool noack);
int osal_wi_set_preserve_seqnum(wi_dev *dev, bool ownSeqenceNo);

/** ping to 802.11 MAC address by sending a 802.11 frame and waiting for an ACK */
int osal_wi_ping(wi_dev *dev, const MacAddr &dst);

/** MTU configuration */
int osal_wi_set_mtu(wi_dev *dev, int mtu);

/**
 * Interface to reactive beacon jamming attack (implemented in firmware).
 * This is a *BLOCKING* function. It will only return once the jamming has finished!!
 */
int osal_wi_jam_beacons(wi_dev *dev, const MacAddr &bssid, int msecs);

/** Be the first to reply to a probe requests from a specific source */
int osal_wi_fastreply_packet(wi_dev *dev, uint8_t *buff, size_t len);
int osal_wi_fastreply_start(wi_dev *dev, const MacAddr &source, int msecs);

int osal_wi_constantjam_start(wi_dev *dev);
int osal_wi_constantjam_stop(wi_dev *dev);

#endif // OSAL_WI_H__
