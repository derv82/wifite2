#include <time.h>
#include <stdio.h>

#include "pcap.h"



PCAPFILE pcap_open(const char *filename, const char *perm)
{
	return fopen(filename, perm);
}


int pcap_write_header(PCAPFILE fp, int linktype)
{
	pcap_file_header hdr;

	hdr.magic         = TCPDUMP_MAGIC;
	hdr.version_major = PCAP_VERSION_MAJOR;
	hdr.version_minor = PCAP_VERSION_MINOR;
	hdr.thiszone      = 0;
	hdr.sigfigs       = 0;
	hdr.snaplen       = 65535;
	hdr.linktype      = linktype;

	if (fwrite(&hdr, sizeof(hdr), 1, fp) != 1) {
		perror("Error writing pcap file header");
		return -1;
	}

	return 0;
}


int pcap_read_header(PCAPFILE fp, pcap_file_header *hdr_out)
{
	pcap_file_header hdr;

	if (fread(&hdr, sizeof(pcap_file_header), 1, fp) != 1) {
		perror("Failed to read pcap header");
		return -1;
	}

	if (hdr.magic != TCPDUMP_MAGIC) {
		fprintf(stderr, "Pcap header magic value not equal to TCPDUMP_MAGIC\n");
		return -1;
	}

	if (hdr_out != NULL)
		*hdr_out = hdr;	

	return 0;
}


int pcap_write_packet(PCAPFILE fp, void *buf, size_t len, uint64_t tsf)
{
	pcap_pkthdr pkthdr;

	// get system time if no TSF is given
	if (tsf == 0) {
		struct timespec now;
		clock_gettime(CLOCK_MONOTONIC, &now);

		pkthdr.tv_sec  = now.tv_sec;
		pkthdr.tv_usec = now.tv_nsec / 1000;
	} else {
		pkthdr.tv_sec  = tsf / 1000000;
		pkthdr.tv_usec = tsf % 1000000;
	}

	pkthdr.caplen  = len;
	pkthdr.len     = len;

	if (fwrite(&pkthdr, sizeof(pkthdr), 1, fp) != 1) {
		fprintf(stderr, "Error writing pcap packet header\n");
		return -1;
	}

	if (fwrite(buf, len, 1, fp) != 1) {
		fprintf(stderr, "Error writing pcap packet data\n");
		return -1;
	}

	return 0;
}


int pcap_read_packet(PCAPFILE fp, void *buf, size_t len, uint64_t *tsf)
{
	pcap_pkthdr pkthdr;

	if (fread(&pkthdr, sizeof(pkthdr), 1, fp) != 1) {
		if (feof(fp)) return -1;
		perror("Failed to read packet header");
		return -2;
	}

	if (pkthdr.caplen > len) {
		fprintf(stderr, "Buffer too small (size %zu) for packet in pcap file (size %d)\n", len, pkthdr.caplen);
		return -2;
	}

	if (fread(buf, pkthdr.caplen, 1, fp) != 1) {
		perror("Failed to read packet data");
		return -2;
	}

	if (tsf) *tsf = pkthdr.tv_sec * 1000000 + pkthdr.tv_usec;

	return pkthdr.len;
}


void pcap_close(PCAPFILE fp)
{
	fclose(fp);
}



