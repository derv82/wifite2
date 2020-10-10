#ifndef _BACKPORT_DMA_BUF_H__
#define _BACKPORT_DMA_BUF_H__
#include <linux/version.h>
#if LINUX_VERSION_CODE >= KERNEL_VERSION(3,3,0)
#include_next <linux/dma-buf.h>
#endif /* LINUX_VERSION_CODE >= KERNEL_VERSION(3,3,0) */
#include <linux/dma-direction.h>
#include <linux/dma-attrs.h>
#include <linux/dma-mapping.h>

#if !defined(DEFINE_DMA_BUF_EXPORT_INFO) && LINUX_VERSION_CODE >= KERNEL_VERSION(3,3,0)
/**
 * helper macro for exporters; zeros and fills in most common values
 */
#define DEFINE_DMA_BUF_EXPORT_INFO(a)	\
	struct dma_buf_export_info a = { .exp_name = KBUILD_MODNAME }

struct dma_buf_export_info {
	const char *exp_name;
	const struct dma_buf_ops *ops;
	size_t size;
	int flags;
	struct reservation_object *resv;
	void *priv;
};

#ifdef dma_buf_export
#undef dma_buf_export
#endif

static inline
struct dma_buf *backport_dma_buf_export(const struct dma_buf_export_info *exp_info)
{
#if LINUX_VERSION_CODE < KERNEL_VERSION(3,4,0)
	return dma_buf_export(exp_info->priv,
			      (struct dma_buf_ops *)exp_info->ops,
			      exp_info->size, exp_info->flags);
#elif LINUX_VERSION_CODE < KERNEL_VERSION(3,10,0)
	return dma_buf_export(exp_info->priv, exp_info->ops,
			      exp_info->size, exp_info->flags);
#elif LINUX_VERSION_CODE < KERNEL_VERSION(3,17,0)
	return dma_buf_export_named(exp_info->priv, exp_info->ops,
				    exp_info->size, exp_info->flags,
				    exp_info->exp_name);
#else
	return dma_buf_export_named(exp_info->priv, exp_info->ops,
				    exp_info->size, exp_info->flags,
				    exp_info->exp_name, exp_info->resv);
#endif
}
#define dma_buf_export LINUX_BACKPORT(dma_buf_export)
#endif /* !defined(DEFINE_DMA_BUF_EXPORT_INFO) */

#endif /* _BACKPORT_DMA_BUF_H__ */
