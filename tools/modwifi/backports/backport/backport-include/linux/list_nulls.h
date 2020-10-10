#ifndef __BACKPORT_LIST_NULLS
#define __BACKPORT_LIST_NULLS
#include_next <linux/list_nulls.h>

#ifndef NULLS_MARKER
#define NULLS_MARKER(value) (1UL | (((long)value) << 1))
#endif

#endif /* __BACKPORT_LIST_NULLS */
