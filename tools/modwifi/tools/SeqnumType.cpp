
#include <stdexcept>

#include "ieee80211header.h"

#include "SeqnumType.h"


/*static*/ SeqnumType SeqnumType::frombuf(void *buf, size_t buflen)
{
	ieee80211header *hdr = (ieee80211header*)buf;
	SeqnumType seqtype;

	// we require a full frame including seqnume numbers
	if (buflen < sizeof(ieee80211header))
		throw std::invalid_argument("Buffer not large enough for IEEE 802.11 header");

	seqtype.macsrc = MacAddr(hdr->addr1);
	seqtype.macdst = MacAddr(hdr->addr2);
	seqtype.type = hdr->fc.type;
	seqtype.subtype = hdr->fc.subtype;
	seqtype.priority = 0;

	// do we have a priority field?
	if (ieee80211_dataqos(hdr))
	{
		ieee80211qosheader *qoshdr = (ieee80211qosheader*)((uint8_t*)buf + sizeof(ieee80211header));

		if (buflen < sizeof(ieee80211header) + sizeof(ieee80211qosheader))
		{
			// For some reason QoS Null frames don't always have QoS info... ignore those
			// Note: this was an issue with my Samsung Galaxy S3 running kernel 3.0.31-1153417
			// dpi@DELL224 #1 SMP PREEMPT Wed May 29 17:23:28 KST 2013
			if (seqtype.subtype != 12)
				throw std::invalid_argument("Buffer not large enough to contain QoS header");
		}
		else
		{
			seqtype.priority = qoshdr->tid;
		}
	}

	return seqtype;
}


/*static*/ std::size_t SeqnumType::operator()(const SeqnumType &type) const
{
	uint64_t hash = type.type * 2 + type.subtype * 3 + type.priority * 5
		+ type.macsrc(type.macsrc) * 7 + type.macdst(type.macdst) * 11;
	return hash % 0xFFFFFFFB;
}


bool SeqnumType::operator==(const SeqnumType &seqtype) const
{
	return macsrc == seqtype.macsrc && macdst == seqtype.macdst && type == seqtype.type
		&& subtype == seqtype.subtype && priority == seqtype.priority;
}


