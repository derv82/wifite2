#ifndef MODWIFI_H
#define MODWIFI_H

//#define DEBUG_INJECT_AMPDU

#ifdef DEBUG_INJECT_AMPDU
#define PRINTK_AMPDU(x) printk(x)
#else
#define PRINTK_AMPDU(x)
#endif

#endif // MODWIFI_H
