#ifndef OSAL_NL_H__
#define OSAL_NL_H__

/**
 * Interface and declarations are/were based on aircrack-ng project
 */

#include "nl80211.h"

struct nl80211_state {
	struct nl_sock *nl_sock;
	int nl80211_id;
};

/** Open an netlink socket (to communicate with kernel) */
int nl80211_init(struct nl80211_state *state);

#endif // OSAL_NL_H__
