#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/kprobes.h>

#define ETH_ALEN 6

/* FIXME: Do not hardcode these structs */
enum ath_device_state {
	ATH_HW_UNAVAILABLE,
	ATH_HW_INITIALIZED,
};

struct ath_ani {
	bool caldone;
	unsigned int longcal_timer;
	unsigned int shortcal_timer;
	unsigned int resetcal_timer;
	unsigned int checkani_timer;
	struct timer_list timer;
};

struct ath_common {
	void *ah;
	void *priv;
	struct ieee80211_hw *hw;
	int debug_mask;
	enum ath_device_state state;
	unsigned long op_flags;

	struct ath_ani ani;

	u16 cachelsz;
	u16 curaid;
	u8 macaddr[ETH_ALEN];
	u8 curbssid[ETH_ALEN] __aligned(2);
	u8 bssidmask[ETH_ALEN];
};

/* For each probe you need to allocate a kprobe structure */
static struct kprobe kp = {
	.symbol_name	= "ath_hw_setbssidmask",
};

/* kprobe pre_handler: called just before the probed instruction is executed */
static int handler_pre(struct kprobe *p, struct pt_regs *regs)
{
#ifdef CONFIG_X86_64
	struct ath_common *common = (struct ath_common *)regs->di;
#elif defined  CONFIG_X86
	struct ath_common *common = (struct ath_common *)regs->ax;
#elif defined(CONFIG_ARM)
	struct ath_common *common = (struct ath_common *)regs->ARM_r0;
#endif

	printk("pre_handler: MAC address of device is %pM\n", common->macaddr);
	printk("pre_handler: old BSSID mask is is %pM\n", common->bssidmask);
	common->bssidmask[ETH_ALEN - 1] = 0x00;
	printk("pre_handler: new BSSID mask is is %pM\n", common->bssidmask);

	/* A dump_stack() here will give a stack backtrace */
	return 0;
}

/* kprobe post_handler: called after the probed instruction is executed */
static void handler_post(struct kprobe *p, struct pt_regs *regs,
				unsigned long flags)
{
	// Nothing
}

/*
 * fault_handler: this is called if an exception is generated for any
 * instruction within the pre- or post-handler, or when Kprobes
 * single-steps the probed instruction.
 */
static int handler_fault(struct kprobe *p, struct pt_regs *regs, int trapnr)
{
	printk(KERN_INFO "fault_handler: p->addr = 0x%p, trap #%dn",
		p->addr, trapnr);
	/* Return 0 because we don't handle the fault. */
	return 0;
}

static int __init kprobe_init(void)
{
	int ret;

#if !defined(CONFIG_X86_64) && !defined(CONFIG_X86) && !defined(CONFIG_ARM)
	printk(KERN_ALERT "Error: this module only supports x86(_64) or ARM\n");
	return -EINVAL;
#endif

	kp.pre_handler = handler_pre;
	kp.post_handler = handler_post;
	kp.fault_handler = handler_fault;

	ret = register_kprobe(&kp);
	if (ret < 0) {
		printk(KERN_INFO "register_kprobe failed, returned %d\n", ret);
		return ret;
	}
	printk(KERN_INFO "Planted kprobe at %p\n", kp.addr);
	return 0;
}

static void __exit kprobe_exit(void)
{
	unregister_kprobe(&kp);
	printk(KERN_INFO "kprobe at %p unregistered\n", kp.addr);
}

module_init(kprobe_init)
module_exit(kprobe_exit)
MODULE_LICENSE("GPL");
