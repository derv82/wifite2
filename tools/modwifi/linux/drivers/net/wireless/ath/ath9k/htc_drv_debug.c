/*
 * Copyright (c) 2010-2011 Atheros Communications Inc.
 *
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

#include "htc.h"
#include "hw.h"

typedef u32 (*GetTimeFunc)(struct ath_hw *ah);
typedef void (*SetTimeFunc)(struct ath_hw *ah, u32 us);

struct time_func {
	const char *name;
	GetTimeFunc getter;
	SetTimeFunc setter;
	const char *comments;
};

struct time_func_context {
	struct time_func *timefunc;
	struct ath9k_htc_priv *htcpriv;
};

struct time_func timefunctions[] = 
{
	{"time_sifs",		ath9k_hw_get_sifs_time,		ath9k_hw_set_sifs_time,
		"SIFS time in microseconds (us) = Rx/Tx time = required time to wait after Rx."},
	{"time_slottime",	ath9k_hw_getslottime,		ath9k_hw_setslottime,
		"Slot time (aSlotTime) in microseconds (us) = slot time as used in backoff algo."},
	{"time_ack_timeout",	ath9k_hw_get_ack_timeout,	ath9k_hw_set_ack_timeout,
		"ACK timeout in microseconds (us)"},
	{"time_cts_timeout",	ath9k_hw_get_cts_timeout,	ath9k_hw_set_cts_timeout,
		"CTS timeout in microseconds (us)"},
	{"time_eifs",		ath9k_hw_get_eifs_timeout,	ath9k_hw_set_eifs_timeout,
		"EIFS time in microseconds (us)"}
};

struct reg_ops registers[] = {
	// Backoff parameters
	{"ifs_cwmin_queue0",		AR_DLCL_IFS(0),		AR_D_LCL_IFS_CWMIN,
		"Backoff behaviour (queue 0): CW_MIN is the minimum number of time slots to wait."},
	{"ifs_cwmax_queue0",		AR_DLCL_IFS(0),		AR_D_LCL_IFS_CWMAX,
		"Backoff behaviour (queue 0): CW_MAX is the maximum number of time slots to wait."},
	{"ifs_aifs_queue0",		AR_DLCL_IFS(0),		AR_D_LCL_IFS_AIFS,
		"AIFS (in number of aSlotTime's) for queue 0."},
	// Disable backoff
	{"ifs_ignore_backoff",		AR_D_GBL_IFS_MISC,	AR_D_GBL_IFS_MISC_IGNORE_BACKOFF,
		"Ignore backoff (perhaps you also want to disable waiting for ACKs - see inject_noack)."},
	// Virtual and physical carrier sense
	{"ignore_virt_cs",		AR_DIAG_SW,		AR_DIAG_IGNORE_VIRT_CS,
		"Disables virtual carrier (cts/rts) sense when set."},
	{"force_channel_idle",		AR_DIAG_SW,		AR_DIAG_FORCE_CH_IDLE_HIGH,
		"Disables physical carrier sense (air clear) when set."},
	{"diag_rx_disable",		AR_DIAG_SW,		AR_DIAG_RX_DIS,
		"Block incoming frames from being sent to the firmware."},
	// Other
	{"diag_corrupt_fcs",		AR_DIAG_SW,		AR_DIAG_CORR_FCS,
		"If set, every transmitted packet is given an incorrect FCS."},
	{"cpu_freq_pll",		0x00056000,		-1,
		"Value = frequency * 4 + 5 (Setting of the Phase Locked Loop)."},
};

static ssize_t read_file_tgt_int_stats(struct file *file, char __user *user_buf,
				       size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct ath9k_htc_target_int_stats cmd_rsp;
	char buf[512];
	unsigned int len = 0;
	int ret = 0;

	memset(&cmd_rsp, 0, sizeof(cmd_rsp));

	ath9k_htc_ps_wakeup(priv);

	WMI_CMD(WMI_INT_STATS_CMDID);
	if (ret) {
		ath9k_htc_ps_restore(priv);
		return -EINVAL;
	}

	ath9k_htc_ps_restore(priv);

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "RX",
			 be32_to_cpu(cmd_rsp.rx));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "RXORN",
			 be32_to_cpu(cmd_rsp.rxorn));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "RXEOL",
			 be32_to_cpu(cmd_rsp.rxeol));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "TXURN",
			 be32_to_cpu(cmd_rsp.txurn));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "TXTO",
			 be32_to_cpu(cmd_rsp.txto));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "CST",
			 be32_to_cpu(cmd_rsp.cst));

	if (len > sizeof(buf))
		len = sizeof(buf);

	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static const struct file_operations fops_tgt_int_stats = {
	.read = read_file_tgt_int_stats,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_tgt_tx_stats(struct file *file, char __user *user_buf,
				      size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct ath9k_htc_target_tx_stats cmd_rsp;
	char buf[512];
	unsigned int len = 0;
	int ret = 0;

	memset(&cmd_rsp, 0, sizeof(cmd_rsp));

	ath9k_htc_ps_wakeup(priv);

	WMI_CMD(WMI_TX_STATS_CMDID);
	if (ret) {
		ath9k_htc_ps_restore(priv);
		return -EINVAL;
	}

	ath9k_htc_ps_restore(priv);

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "Xretries",
			 be32_to_cpu(cmd_rsp.xretries));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "FifoErr",
			 be32_to_cpu(cmd_rsp.fifoerr));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "Filtered",
			 be32_to_cpu(cmd_rsp.filtered));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "TimerExp",
			 be32_to_cpu(cmd_rsp.timer_exp));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "ShortRetries",
			 be32_to_cpu(cmd_rsp.shortretries));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "LongRetries",
			 be32_to_cpu(cmd_rsp.longretries));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "QueueNull",
			 be32_to_cpu(cmd_rsp.qnull));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "EncapFail",
			 be32_to_cpu(cmd_rsp.encap_fail));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "NoBuf",
			 be32_to_cpu(cmd_rsp.nobuf));

	if (len > sizeof(buf))
		len = sizeof(buf);

	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static const struct file_operations fops_tgt_tx_stats = {
	.read = read_file_tgt_tx_stats,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_tgt_rx_stats(struct file *file, char __user *user_buf,
				      size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct ath9k_htc_target_rx_stats cmd_rsp;
	char buf[512];
	unsigned int len = 0;
	int ret = 0;

	memset(&cmd_rsp, 0, sizeof(cmd_rsp));

	ath9k_htc_ps_wakeup(priv);

	WMI_CMD(WMI_RX_STATS_CMDID);
	if (ret) {
		ath9k_htc_ps_restore(priv);
		return -EINVAL;
	}

	ath9k_htc_ps_restore(priv);

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "NoBuf",
			 be32_to_cpu(cmd_rsp.nobuf));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "HostSend",
			 be32_to_cpu(cmd_rsp.host_send));

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "HostDone",
			 be32_to_cpu(cmd_rsp.host_done));

	if (len > sizeof(buf))
		len = sizeof(buf);

	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static const struct file_operations fops_tgt_rx_stats = {
	.read = read_file_tgt_rx_stats,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_xmit(struct file *file, char __user *user_buf,
			      size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	char buf[512];
	unsigned int len = 0;

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "Buffers queued",
			 priv->debug.tx_stats.buf_queued);
	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "Buffers completed",
			 priv->debug.tx_stats.buf_completed);
	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "SKBs queued",
			 priv->debug.tx_stats.skb_queued);
	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "SKBs success",
			 priv->debug.tx_stats.skb_success);
	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "SKBs failed",
			 priv->debug.tx_stats.skb_failed);
	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "CAB queued",
			 priv->debug.tx_stats.cab_queued);

	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "BE queued",
			 priv->debug.tx_stats.queue_stats[IEEE80211_AC_BE]);
	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "BK queued",
			 priv->debug.tx_stats.queue_stats[IEEE80211_AC_BK]);
	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "VI queued",
			 priv->debug.tx_stats.queue_stats[IEEE80211_AC_VI]);
	len += scnprintf(buf + len, sizeof(buf) - len,
			 "%20s : %10u\n", "VO queued",
			 priv->debug.tx_stats.queue_stats[IEEE80211_AC_VO]);

	if (len > sizeof(buf))
		len = sizeof(buf);

	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static const struct file_operations fops_xmit = {
	.read = read_file_xmit,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

void ath9k_htc_err_stat_rx(struct ath9k_htc_priv *priv,
			     struct ath_rx_status *rs)
{
	ath9k_cmn_debug_stat_rx(&priv->debug.rx_stats, rs);
}

static ssize_t read_file_skb_rx(struct file *file, char __user *user_buf,
			      size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	char *buf;
	unsigned int len = 0, size = 1500;
	ssize_t retval = 0;

	buf = kzalloc(size, GFP_KERNEL);
	if (buf == NULL)
		return -ENOMEM;

	len += scnprintf(buf + len, size - len,
			 "%20s : %10u\n", "SKBs allocated",
			 priv->debug.skbrx_stats.skb_allocated);
	len += scnprintf(buf + len, size - len,
			 "%20s : %10u\n", "SKBs completed",
			 priv->debug.skbrx_stats.skb_completed);
	len += scnprintf(buf + len, size - len,
			 "%20s : %10u\n", "SKBs Dropped",
			 priv->debug.skbrx_stats.skb_dropped);

	if (len > size)
		len = size;

	retval = simple_read_from_buffer(user_buf, count, ppos, buf, len);
	kfree(buf);

	return retval;
}

static const struct file_operations fops_skb_rx = {
	.read = read_file_skb_rx,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_slot(struct file *file, char __user *user_buf,
			      size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	char buf[512];
	unsigned int len;

	spin_lock_bh(&priv->tx.tx_lock);
	len = scnprintf(buf, sizeof(buf),
			"TX slot bitmap : %*pb\n"
			"Used slots     : %d\n",
			MAX_TX_BUF_NUM, priv->tx.tx_slot,
			bitmap_weight(priv->tx.tx_slot, MAX_TX_BUF_NUM));
	spin_unlock_bh(&priv->tx.tx_lock);
	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static const struct file_operations fops_slot = {
	.read = read_file_slot,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_queue(struct file *file, char __user *user_buf,
			       size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	char buf[512];
	unsigned int len = 0;

	len += scnprintf(buf + len, sizeof(buf) - len, "%20s : %10u\n",
			 "Mgmt endpoint", skb_queue_len(&priv->tx.mgmt_ep_queue));

	len += scnprintf(buf + len, sizeof(buf) - len, "%20s : %10u\n",
			 "Cab endpoint", skb_queue_len(&priv->tx.cab_ep_queue));

	len += scnprintf(buf + len, sizeof(buf) - len, "%20s : %10u\n",
			 "Data BE endpoint", skb_queue_len(&priv->tx.data_be_queue));

	len += scnprintf(buf + len, sizeof(buf) - len, "%20s : %10u\n",
			 "Data BK endpoint", skb_queue_len(&priv->tx.data_bk_queue));

	len += scnprintf(buf + len, sizeof(buf) - len, "%20s : %10u\n",
			 "Data VI endpoint", skb_queue_len(&priv->tx.data_vi_queue));

	len += scnprintf(buf + len, sizeof(buf) - len, "%20s : %10u\n",
			 "Data VO endpoint", skb_queue_len(&priv->tx.data_vo_queue));

	len += scnprintf(buf + len, sizeof(buf) - len, "%20s : %10u\n",
			 "Failed queue", skb_queue_len(&priv->tx.tx_failed));

	spin_lock_bh(&priv->tx.tx_lock);
	len += scnprintf(buf + len, sizeof(buf) - len, "%20s : %10u\n",
			 "Queued count", priv->tx.queued_cnt);
	spin_unlock_bh(&priv->tx.tx_lock);

	if (len > sizeof(buf))
		len = sizeof(buf);

	return simple_read_from_buffer(user_buf, count, ppos, buf, len);

}

static const struct file_operations fops_queue = {
	.read = read_file_queue,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_debug(struct file *file, char __user *user_buf,
			       size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct ath_common *common = ath9k_hw_common(priv->ah);
	char buf[32];
	unsigned int len;

	len = sprintf(buf, "0x%08x\n", common->debug_mask);
	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static ssize_t write_file_debug(struct file *file, const char __user *user_buf,
				size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct ath_common *common = ath9k_hw_common(priv->ah);
	unsigned long mask;
	char buf[32];
	ssize_t len;

	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EFAULT;

	buf[len] = '\0';
	if (kstrtoul(buf, 0, &mask))
		return -EINVAL;

	common->debug_mask = mask;
	return count;
}

static const struct file_operations fops_debug = {
	.read = read_file_debug,
	.write = write_file_debug,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_reg_ops(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	struct reg_ops_instance *instance = file->private_data;
	struct ath9k_htc_priv *priv = instance->owner;
	struct reg_ops *regops = instance->regops;
	char buf[512];
	unsigned int len;
	unsigned int regval, mask;

	ath9k_htc_ps_wakeup(priv);
	regval = REG_READ(priv->ah, regops->address);
	ath9k_htc_ps_restore(priv);

	// apply mask, and shift according to mask
	regval &= regops->mask;
	mask = regops->mask;
	while ( (mask & 1) == 0) {
		mask >>= 1;
		regval >>= 1;
	}

	len = snprintf(buf, sizeof(buf), "%s: %s\nValue: 0x%08X = %d (forced: %d)\n",
					regops->name, regops->description, regval, regval,
					!!(instance->valueset));

	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static ssize_t write_file_reg_ops(struct file *file, const char __user *user_buf,
				  size_t count, loff_t *ppos)
{
	struct reg_ops_instance *instance = file->private_data;
	struct ath9k_htc_priv *priv = instance->owner;
	struct reg_ops *regops = instance->regops;
	unsigned long val;
	char buf[32];
	ssize_t len;
	unsigned int mask, regval;

	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EINVAL;

	buf[len] = '\0';
	if (kstrtoul(buf, 0, &val))
		return -EINVAL;

	// shift according to mask
	mask = regops->mask;
	while ( (mask & 1) == 0) {
		mask >>= 1;
		val <<= 1;
	}

	// apply mask to assure we're not overwriting anything else
	val &= regops->mask;

	ath9k_htc_ps_wakeup(priv);
	regval = REG_READ(priv->ah, regops->address);
	regval = (regval & ~regops->mask) | val;
	REG_WRITE(priv->ah, regops->address, regval);
	ath9k_htc_ps_restore(priv);

	instance->valueset = 1;
	instance->value = val;

	return count;
}

static const struct file_operations fops_reg_ops = {
	.read = read_file_reg_ops,
	.write = write_file_reg_ops,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_dmesg(struct file *file, char __user *user_buf,
			       size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct wmi_debugmsg_cmd cmd;
	struct wmi_debugmsg_resp cmd_rsp;
	/** ppos is the amount of data already read (maintained by caller) */
	int offset = *ppos;
	int ret;

	/** Note: don't need to wake the WiFi MAC chip to get debug messages! */
	memset(&cmd, 0, sizeof(cmd));
	cmd.offset = cpu_to_be16(offset);

	memset(&cmd_rsp, 0, sizeof(cmd_rsp));
	ret = ath9k_wmi_cmd(priv->wmi, WMI_DEBUGMSG_CMDID,
			    (u8*)&cmd, sizeof(cmd),
			    (u8*)&cmd_rsp, sizeof(cmd_rsp),
			    HZ*2);
	if (ret) {
		printk("ath9k_htc %s: Something went wrong reading firmware dmesg (ret: %d, len: %d)\n",
			__FUNCTION__, ret, cmd_rsp.length);
		return -EIO;
	}

	// Don't overflow user_buf
	if (count < cmd_rsp.length)
		cmd_rsp.length = count;

	// Length of zero signifies EOF
	if (cmd_rsp.length != 0) {
		// Returns number of bytes that could not be copied
		if (copy_to_user(user_buf, cmd_rsp.buffer, cmd_rsp.length) != 0)
			return -EFAULT;
	}

	*ppos += cmd_rsp.length;
	return cmd_rsp.length; 
}

static const struct file_operations fops_dmesg = {
	.read = read_file_dmesg,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_reactivejam(struct file *file, char __user *user_buf,
			     size_t count, loff_t *ppos)
{
	char output[] = "Jam beacons and probe responses by writing the bssid and"
			"duration (in msecs) to this file as 'XX:XX:XX:XX:XX:XX,10000'.\n"
			"Duration of 0 means an infinite jam (device becomes unresponsive).\n";
	return simple_read_from_buffer(user_buf, count, ppos, output, sizeof(output));
}

static ssize_t write_file_reactivejam(struct file *file, const char __user *user_buf,
				      size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct wmi_reactivejam_cmd cmd;
	char buf[32] = {0}, reply[128] = {0};
	unsigned int intmac[6];
	unsigned int duration;
	int rval, len, i;

	if (*ppos != 0) return 0;

	// copy over input
	len = min(count, sizeof(buf) - 1);
	if (unlikely(copy_from_user(buf, user_buf, len))) {
		printk("ath9k_htc %s: copy_from_user failed\n", __FUNCTION__);
		return -EFAULT;
	}
	buf[sizeof(buf) - 1] = 0;

	// parse input
	if ( 7 != sscanf(buf, "%x:%x:%x:%x:%x:%x,%u", &intmac[0], &intmac[1], &intmac[2],
		&intmac[3], &intmac[4], &intmac[5], &duration) ) {
		printk("ath9k_htc %s: invalid format\n", __FUNCTION__);
		return -EINVAL;
	}

	// save input to command
	for (i = 0; i < 6; ++i)
		cmd.bssid[i] = intmac[i];
	cmd.mduration = cpu_to_be32(duration);

	printk("ath9k_htc: Reactively jamming %x:%x:%x:%x:%x:%x ", cmd.bssid[0], cmd.bssid[1],
		cmd.bssid[2], cmd.bssid[3], cmd.bssid[4], cmd.bssid[5]);
	if (cmd.mduration == 0)
		printk("indefinitely (device will be unresponsive)\n");
	else
		printk("for %u miliseconds\n", duration);

	// Blocking call! Wait for duration + 4 seconds. Response is an ASCII string. If the duration
	// is zero, firmware instantly replies, but will then become unresponsive (infinite jam).
	ath9k_htc_ps_wakeup(priv);	
	rval = ath9k_wmi_cmd(priv->wmi, WMI_REACTIVEJAM_CMDID,
			(u8*)&cmd, sizeof(cmd),
			(u8*)reply, sizeof(reply),
			HZ * (duration / 1000 + 4));
	ath9k_htc_ps_restore(priv);

	if (unlikely(rval) && cmd.mduration != 0) {
		printk("ath9k_htc %s: WMI_REACTIVEJAM_CMD failed with %d\n", __FUNCTION__, rval);
		return -EBUSY;
	}

	// Reset radio settings
	ath9k_hw_init_global_settings(priv->ah);

	return count;
}

static const struct file_operations fops_reactivejam = {
	.read = read_file_reactivejam,
	.write = write_file_reactivejam,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_constantjam(struct file *file, char __user *user_buf,
			       size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct wmi_constantjam_resp cmd_rsp;
	struct wmi_constantjam_cmd cmd;
	char buf[128];
	unsigned int len;
	int rval;
	
	if (*ppos != 0) return 0;

	memset(&cmd, 0, sizeof(cmd));
	cmd.request = CONSTJAM_STATUS;

	// Send command to firmware
	rval = ath9k_wmi_cmd(priv->wmi, WMI_CONSTANTJAM_CMDID,
			(u8 *)&cmd, sizeof(cmd),
			(u8 *)&cmd_rsp, sizeof(cmd_rsp),
			HZ*2);

	if (unlikely(rval)) {
		printk(">>>> WMI_CONSTANTJAM_CMD failed: %d\n", rval);
		return -EIO;
	}

	len = snprintf(buf, sizeof(buf), "Constant jammer running: %d\n", cmd_rsp.status);
	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static ssize_t write_file_constantjam(struct file *file, const char __user *user_buf,
			     size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct wmi_constantjam_resp cmd_rsp;
	struct wmi_constantjam_cmd cmd;
	unsigned long val;
	char buf[32];
	ssize_t len;
	int rval = 0;

	if (*ppos != 0) return 0;

	// parse input
	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EINVAL;

	buf[len] = '\0';
	if (kstrtoul(buf, 0, &val))
		return -EINVAL;

	memset(&cmd, 0, sizeof(cmd));
	// should we start or stop
	cmd.request = val == 0 ? CONSTJAM_STOP : CONSTJAM_START;
	// full continuous jamming (disable carrier sense, no timeouts between packets)
	cmd.conf_radio = 1;
	// length of packet used for jamming (pick a small one to avoid memory issues)
	cmd.len = cpu_to_be16(50);

	// Send command to firmware
	ath9k_htc_ps_wakeup(priv);
	rval = ath9k_wmi_cmd(priv->wmi, WMI_CONSTANTJAM_CMDID,
			(u8 *)&cmd, sizeof(cmd),
			(u8 *)&cmd_rsp, sizeof(cmd_rsp),
			HZ*2);

	if (unlikely(rval)) {
		printk(">>>> WMI_CONSTANTJAM_CMD failed: %d\n", rval);
		return -EIO;
	}

	if (cmd.request == CONSTJAM_STOP)
		ath9k_htc_ps_restore(priv);

	return count;
}

static const struct file_operations fops_constantjam = {
	.read = read_file_constantjam,
	.write = write_file_constantjam,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_macaddr(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	char buf[512];
	unsigned int len;
	unsigned int low, upper;

	ath9k_htc_ps_wakeup(priv);
	low = REG_READ(priv->ah, AR_STA_ID0);
	upper = REG_READ(priv->ah, AR_STA_ID1) & AR_STA_ID1_SADH_MASK;
	ath9k_htc_ps_restore(priv);

	len = snprintf(buf, sizeof(buf), "%02X:%02X:%02X:%02X:%02X:%02X\n",
			low & 0xFF, (low >> 8) & 0xFF, (low >> 16) & 0xFF,
			(low >> 24) & 0xFF, upper & 0xFF, (upper >> 8) & 0xFF);
	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static ssize_t write_file_macaddr(struct file *file, const char __user *user_buf,
				  size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	char buf[32];
	unsigned int mac[6];
	unsigned int low, upper;
	ssize_t len;

	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EFAULT;
	buf[sizeof(buf) - 1] = 0;

	if ( 6 != sscanf(buf, "%x:%x:%x:%x:%x:%x", &mac[0], &mac[1], &mac[2], &mac[3], &mac[4], &mac[5]) )
		return -EINVAL;

	low = mac[0] | (mac[1] << 8) | (mac[2] << 16) | (mac[3] << 24);
	upper = mac[4] | (mac[5] << 8);

	ath9k_htc_ps_wakeup(priv);
	REG_WRITE(priv->ah, AR_STA_ID0, low);
	REG_WRITE(priv->ah, AR_STA_ID1, upper & AR_STA_ID1_SADH_MASK);
	ath9k_htc_ps_restore(priv);

	return count;
}

static const struct file_operations fops_macaddr = {
	.read = read_file_macaddr,
	.write = write_file_macaddr,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_bssidmask(struct file *file, char __user *user_buf,
				   size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	char buf[512];
	unsigned int len;
	unsigned int low, upper;		

	ath9k_htc_ps_wakeup(priv);
	low = REG_READ(priv->ah, AR_BSSMSKL);
	upper = REG_READ(priv->ah, AR_BSSMSKU);
	ath9k_htc_ps_restore(priv);

	len = snprintf(buf, sizeof(buf), "%02X:%02X:%02X:%02X:%02X:%02X\n",
			low & 0xFF, (low >> 8) & 0xFF, (low >> 16) & 0xFF,
			(low >> 24) & 0xFF, upper & 0xFF, (upper >> 8) & 0xFF);
	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static ssize_t write_file_bssidmask(struct file *file, const char __user *user_buf,
				    size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	char buf[32];
	unsigned int mask[6];
	unsigned int low, upper;
	ssize_t len;

	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EFAULT;
	buf[sizeof(buf) - 1] = 0;

	if ( 6 != sscanf(buf, "%x:%x:%x:%x:%x:%x", &mask[0], &mask[1], &mask[2], &mask[3], &mask[4], &mask[5]) )
		return -EINVAL;

	low = mask[0] | (mask[1] << 8) | (mask[2] << 16) | (mask[3] << 24);
	upper = mask[4] | (mask[5] << 8);

	ath9k_htc_ps_wakeup(priv);
	REG_WRITE(priv->ah, AR_BSSMSKL, low);
	REG_WRITE(priv->ah, AR_BSSMSKU, upper & AR_BSS_ID1_U16);
	ath9k_htc_ps_restore(priv);

	return count;
}

static const struct file_operations fops_bssidmask = {
	.read = read_file_bssidmask,
	.write = write_file_bssidmask,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_inject_noack(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	char buf[64];
	int len;

	len = snprintf(buf, sizeof(buf), "%d\n", priv->inject_noack);
	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static ssize_t write_file_inject_noack(struct file *file, const char __user *user_buf,
				  size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	char buf[32];
	unsigned long val;
	int len;

	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EFAULT;

	buf[len] = '\0';
	if (kstrtoul(buf, 0, &val))
		return -EINVAL;

	priv->inject_noack = val;

	return count;
}

static const struct file_operations fops_inject_noack = {
	.read = read_file_inject_noack,
	.write = write_file_inject_noack,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_fastreply_packet(struct file *file, char __user *user_buf,
				   size_t count, loff_t *ppos)
{
	char buf[128] = "Write the reply packet used in fastreply_start to this file.\n";
	return simple_read_from_buffer(user_buf, count, ppos, buf, sizeof(buf));
}

static ssize_t write_file_fastreply_packet(struct file *file,
	const char __user *user_buf, size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct wmi_fastreply_cmd cmd;
	uint8_t buff[256];
	unsigned int offset;
	int reply, rval;

	if (*ppos != 0) return 0;

	//
	// 1. copy input
	//

	if (count > 256) {
		printk("fastreply_packet: packet is too long (%zu)\n", count);
		return -EMSGSIZE;
	}

	if (copy_from_user(buff, user_buf, count))
		return -EFAULT;

	//
	// 2. send the buffer to the firmware
	//
		
	cmd.type = FASTREPLY_PKT;
	cmd.pkt.length = count;

	ath9k_htc_ps_wakeup(priv);

	for (offset = 0; offset < count; offset += sizeof(cmd.pkt.data))
	{
		cmd.pkt.offset = offset;
		cmd.pkt.datalen = min(40U, (unsigned int)(count - offset));
		memcpy(cmd.pkt.data, &buff[offset], cmd.pkt.datalen);

		rval = ath9k_wmi_cmd(priv->wmi, WMI_FASTREPLY_CMDID,
				(u8*)&cmd, sizeof(cmd),
				(u8*)&reply, sizeof(reply),
				2*HZ);

		if (unlikely(rval)) {
			printk("ath9k_htc %s: WMI_FASTREPLY_CMDID failed with %d\n", __FUNCTION__, rval);
			ath9k_htc_ps_restore(priv);
			return -EIO;
		}
	}

	ath9k_htc_ps_restore(priv);

	return count;
}


static const struct file_operations fops_fastreply_packet = {
	.read = read_file_fastreply_packet,
	.write = write_file_fastreply_packet,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

static ssize_t read_file_fastreply_start(struct file *file, char __user *user_buf,
				   size_t count, loff_t *ppos)
{
	char buf[128] = "Write the source MAC and duration ( 90:18:7c:6e:6b:20,10000 ) to this file.\n"
			"Set the reply packet using fastreply_packet.\n";
	return simple_read_from_buffer(user_buf, count, ppos, buf, sizeof(buf));
}

static ssize_t write_file_fastreply_start(struct file *file,
	const char __user *user_buf, size_t count, loff_t *ppos)
{
	struct ath9k_htc_priv *priv = file->private_data;
	struct wmi_fastreply_cmd cmd;
	char input[256];
	int mac[6];
	unsigned int duration;
	int len, reply, rval, i;

	if (*ppos != 0) return 0;

	// 1. parse input

	len = min(count, sizeof(input) - 1);
	if (copy_from_user(input, user_buf, len))
		return -EFAULT;
	input[len] = '\0';

	if (sscanf(input, "%x:%x:%x:%x:%x:%x,%u", &mac[0], &mac[1], &mac[2],
		&mac[3], &mac[4], &mac[5], &duration) != 7) {
		printk("%s: sscanf parsing failed\n", __FUNCTION__);
		return -EINVAL;
	}

	// 2. send the start command
	
	cmd.type = FASTREPLY_START;
	cmd.start.mduration = cpu_to_be32(duration);
	for (i = 0; i < 6; ++i)
		cmd.start.source[i] = mac[i];

	ath9k_htc_ps_wakeup(priv);
	
	rval = ath9k_wmi_cmd(priv->wmi, WMI_FASTREPLY_CMDID,
			(u8*)&cmd, sizeof(cmd),
			(u8*)&reply, sizeof(reply),
			HZ * (duration / 1000 + 4));

	ath9k_htc_ps_restore(priv);

	if (unlikely(rval)) {
		printk("ath9k_htc %s: WMI_FASTREPLY_CMDID failed with %d\n", __FUNCTION__, rval);
		return -EBUSY;
	}

	return count;
}

static const struct file_operations fops_fastreply_start = {
	.read = read_file_fastreply_start,
	.write = write_file_fastreply_start,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};


static ssize_t read_file_timefunc(struct file *file, char __user *user_buf,
				  size_t count, loff_t *ppos)
{
	struct time_func_context *context = file->private_data;
	struct time_func *timefunc = context->timefunc;
	struct ath9k_htc_priv *priv = context->htcpriv;
	char buf[512];
	unsigned int len, val;

	// FIXME: Is the wakeup/restore call needed?
	ath9k_htc_ps_wakeup(priv);
	val = timefunc->getter(priv->ah);
	ath9k_htc_ps_restore(priv);

	len = snprintf(buf, sizeof(buf), "%s: %s\nValue: 0x%08X = %d\n",
		timefunc->name, timefunc->comments, val, val);
	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static ssize_t write_file_timefunc(struct file *file, const char __user *user_buf,
				   size_t count, loff_t *ppos)
{
	struct time_func_context *context = file->private_data;
	struct time_func *timefunc = context->timefunc;
	struct ath9k_htc_priv *priv = context->htcpriv;
	unsigned long val;
	char buf[32];
	ssize_t len;

	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EINVAL;

	buf[len] = '\0';
	if (kstrtoul(buf, 0, &val))
		return -EINVAL;

	// FIXME: Is the wakeup/restore call needed?
	ath9k_htc_ps_wakeup(priv);
	timefunc->setter(priv->ah, (u32)val);
	ath9k_htc_ps_restore(priv);

	return count;
}

static const struct file_operations fops_timefunc = {
	.read = read_file_timefunc,
	.write = write_file_timefunc,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

/* Ethtool support for get-stats */
#define AMKSTR(nm) #nm "_BE", #nm "_BK", #nm "_VI", #nm "_VO"
static const char ath9k_htc_gstrings_stats[][ETH_GSTRING_LEN] = {
	"tx_pkts_nic",
	"tx_bytes_nic",
	"rx_pkts_nic",
	"rx_bytes_nic",

	AMKSTR(d_tx_pkts),

	"d_rx_crc_err",
	"d_rx_decrypt_crc_err",
	"d_rx_phy_err",
	"d_rx_mic_err",
	"d_rx_pre_delim_crc_err",
	"d_rx_post_delim_crc_err",
	"d_rx_decrypt_busy_err",

	"d_rx_phyerr_radar",
	"d_rx_phyerr_ofdm_timing",
	"d_rx_phyerr_cck_timing",

};
#define ATH9K_HTC_SSTATS_LEN ARRAY_SIZE(ath9k_htc_gstrings_stats)

void ath9k_htc_get_et_strings(struct ieee80211_hw *hw,
			      struct ieee80211_vif *vif,
			      u32 sset, u8 *data)
{
	if (sset == ETH_SS_STATS)
		memcpy(data, *ath9k_htc_gstrings_stats,
		       sizeof(ath9k_htc_gstrings_stats));
}

int ath9k_htc_get_et_sset_count(struct ieee80211_hw *hw,
				struct ieee80211_vif *vif, int sset)
{
	if (sset == ETH_SS_STATS)
		return ATH9K_HTC_SSTATS_LEN;
	return 0;
}

#define STXBASE priv->debug.tx_stats
#define SRXBASE priv->debug.rx_stats
#define SKBTXBASE priv->debug.tx_stats
#define SKBRXBASE priv->debug.skbrx_stats
#define ASTXQ(a)					\
	data[i++] = STXBASE.a[IEEE80211_AC_BE];		\
	data[i++] = STXBASE.a[IEEE80211_AC_BK];		\
	data[i++] = STXBASE.a[IEEE80211_AC_VI];		\
	data[i++] = STXBASE.a[IEEE80211_AC_VO]

void ath9k_htc_get_et_stats(struct ieee80211_hw *hw,
			    struct ieee80211_vif *vif,
			    struct ethtool_stats *stats, u64 *data)
{
	struct ath9k_htc_priv *priv = hw->priv;
	int i = 0;

	data[i++] = SKBTXBASE.skb_success;
	data[i++] = SKBTXBASE.skb_success_bytes;
	data[i++] = SKBRXBASE.skb_completed;
	data[i++] = SKBRXBASE.skb_completed_bytes;

	ASTXQ(queue_stats);

	data[i++] = SRXBASE.crc_err;
	data[i++] = SRXBASE.decrypt_crc_err;
	data[i++] = SRXBASE.phy_err;
	data[i++] = SRXBASE.mic_err;
	data[i++] = SRXBASE.pre_delim_crc_err;
	data[i++] = SRXBASE.post_delim_crc_err;
	data[i++] = SRXBASE.decrypt_busy_err;

	data[i++] = SRXBASE.phy_err_stats[ATH9K_PHYERR_RADAR];
	data[i++] = SRXBASE.phy_err_stats[ATH9K_PHYERR_OFDM_TIMING];
	data[i++] = SRXBASE.phy_err_stats[ATH9K_PHYERR_CCK_TIMING];

	WARN_ON(i != ATH9K_HTC_SSTATS_LEN);
}

void ath9k_htc_deinit_debug(struct ath9k_htc_priv *priv)
{
	if (priv->debug.debugfs_phy_regs)
		debugfs_remove(priv->debug.debugfs_phy_regs);
	priv->debug.debugfs_phy_regs = NULL;

	ath9k_cmn_spectral_deinit_debug(&priv->spec_priv);
}

int ath9k_htc_init_debug(struct ath_hw *ah)
{
	struct ath_common *common = ath9k_hw_common(ah);
	struct ath9k_htc_priv *priv = (struct ath9k_htc_priv *) common->priv;
	struct reg_ops_instance *previnstance;
	int i;

	priv->debug.debugfs_phy = debugfs_create_dir(KBUILD_MODNAME,
					     priv->hw->wiphy->debugfsdir);
	if (!priv->debug.debugfs_phy)
		return -ENOMEM;

	ath9k_cmn_spectral_init_debug(&priv->spec_priv, priv->debug.debugfs_phy);

	debugfs_create_file("tgt_int_stats", 0400, priv->debug.debugfs_phy,
			    priv, &fops_tgt_int_stats);
	debugfs_create_file("tgt_tx_stats", 0400, priv->debug.debugfs_phy,
			    priv, &fops_tgt_tx_stats);
	debugfs_create_file("tgt_rx_stats", 0400, priv->debug.debugfs_phy,
			    priv, &fops_tgt_rx_stats);
	debugfs_create_file("xmit", 0400, priv->debug.debugfs_phy,
			    priv, &fops_xmit);
	debugfs_create_file("skb_rx", 0400, priv->debug.debugfs_phy,
			    priv, &fops_skb_rx);

	ath9k_cmn_debug_recv(priv->debug.debugfs_phy, &priv->debug.rx_stats);
	ath9k_cmn_debug_phy_err(priv->debug.debugfs_phy, &priv->debug.rx_stats);

	debugfs_create_file("slot", 0400, priv->debug.debugfs_phy,
			    priv, &fops_slot);
	debugfs_create_file("queue", 0400, priv->debug.debugfs_phy,
			    priv, &fops_queue);
	debugfs_create_file("debug", 0600, priv->debug.debugfs_phy,
			    priv, &fops_debug);
	debugfs_create_file("dmesg", S_IRUSR, priv->debug.debugfs_phy,
			    priv, &fops_dmesg);
	debugfs_create_file("reactivejam", S_IRUSR, priv->debug.debugfs_phy,
			    priv, &fops_reactivejam);
	debugfs_create_file("constantjam", S_IRUSR, priv->debug.debugfs_phy,
			    priv, &fops_constantjam);
	debugfs_create_file("fastreply_packet", S_IRUSR | S_IWUSR,
			    priv->debug.debugfs_phy, priv, &fops_fastreply_packet);
	debugfs_create_file("fastreply_start", S_IRUSR | S_IWUSR,
			    priv->debug.debugfs_phy, priv, &fops_fastreply_start);
	debugfs_create_file("macaddr", S_IRUSR | S_IWUSR, priv->debug.debugfs_phy,
			    priv, &fops_macaddr);
	debugfs_create_file("bssidmask", S_IRUSR | S_IWUSR, priv->debug.debugfs_phy,
			    priv, &fops_bssidmask);
	debugfs_create_file("inject_noack", S_IRUSR | S_IWUSR,
			    priv->debug.debugfs_phy, priv, &fops_inject_noack);

	ath9k_cmn_debug_base_eeprom(priv->debug.debugfs_phy, priv->ah);
	ath9k_cmn_debug_modal_eeprom(priv->debug.debugfs_phy, priv->ah);

	//
	// Read/write access to registers
	//

	priv->debug.debugfs_phy_regs = debugfs_create_dir("registers", priv->debug.debugfs_phy);
	if (!priv->debug.debugfs_phy_regs)
		return -ENOMEM;

	previnstance = NULL;
	for (i = 0; i < sizeof(registers) / sizeof(registers[0]); ++i)
	{
		struct reg_ops *regops = &registers[i];
		struct reg_ops_instance *instance;

		// Allocated linked list is freed in ath9k_hw_deinit
		instance = kzalloc(sizeof(struct reg_ops_instance), GFP_KERNEL);
		if (!instance) return -ENOMEM;

		instance->regops = regops;
		instance->owner = priv;

		instance->valueset = 0;
		instance->value = 0;
		instance->next = previnstance;

		// Read/write access using general functions
		debugfs_create_file(regops->name, S_IRUSR|S_IWUSR,
			priv->debug.debugfs_phy_regs, instance, &fops_reg_ops);

		previnstance = instance;
	}
	
	priv->ah->modified_registers = previnstance;
	

	//
	// Time functions
	//

	for (i = 0; i < sizeof(timefunctions) / sizeof(timefunctions[0]); ++i)
	{
		// Allocate a context
		struct time_func_context *context;
		context = devm_kzalloc(priv->dev, sizeof(struct time_func_context), GFP_KERNEL);
		if (!context) return -ENOMEM;

		context->timefunc = &timefunctions[i];
		context->htcpriv = priv;

		// Read/write access using general functions
		debugfs_create_file(context->timefunc->name, S_IRUSR|S_IWUSR,
			priv->debug.debugfs_phy, context, &fops_timefunc);
	}

	return 0;
}
