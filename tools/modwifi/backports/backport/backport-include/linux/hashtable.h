#ifndef __BACKPORT_HASHTABLE_H
#define __BACKPORT_HASHTABLE_H
#include_next <linux/hashtable.h>
#include <linux/version.h>

#if LINUX_VERSION_CODE < KERNEL_VERSION(3,9,0)
/**
 * backport:
 *
 * commit 0bbacca7c3911451cea923b0ad6389d58e3d9ce9
 * Author: Sasha Levin <sasha.levin@oracle.com>
 * Date:   Thu Feb 7 12:32:18 2013 +1100
 *
 *     hlist: drop the node parameter from iterators
 */
#include <linux/list.h>
#include <backport/magic.h>

#undef hash_for_each
#define hash_for_each(name, bkt, obj, member)				\
	for ((bkt) = 0, obj = NULL; obj == NULL && (bkt) < HASH_SIZE(name);\
			(bkt)++)\
		hlist_for_each_entry(obj, &name[bkt], member)

#undef hash_for_each_safe
#define hash_for_each_safe(name, bkt, tmp, obj, member)			\
	for ((bkt) = 0, obj = NULL; obj == NULL && (bkt) < HASH_SIZE(name);\
			(bkt)++)\
		hlist_for_each_entry_safe(obj, tmp, &name[bkt], member)

#undef hash_for_each_possible
#define hash_for_each_possible(name, obj, member, key)			\
	hlist_for_each_entry(obj, &name[hash_min(key, HASH_BITS(name))], member)

#undef hash_for_each_possible_safe
#define hash_for_each_possible_safe(name, obj, tmp, member, key)	\
	hlist_for_each_entry_safe(obj, tmp,\
		&name[hash_min(key, HASH_BITS(name))], member)

#endif

#endif /* __BACKPORT_HASHTABLE_H */
