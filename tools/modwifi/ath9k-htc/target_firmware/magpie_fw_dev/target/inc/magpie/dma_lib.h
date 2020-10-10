#ifndef __DMA_LIB_H
#define __DMA_LIB_H


/***********************External***************************/

/**
 * @brief DMA engine numbers, HIF need to map them to there
 *        respective order
 */
typedef enum dma_engine{
    DMA_ENGINE_RX0,
    DMA_ENGINE_RX1,
    DMA_ENGINE_RX2,
    DMA_ENGINE_RX3,
    DMA_ENGINE_TX0,
    DMA_ENGINE_TX1,
    DMA_ENGINE_MAX
}dma_engine_t;

/**
 * @brief Interface type, each HIF should call with its own interface type
 */
typedef enum dma_iftype{
    DMA_IF_GMAC = 0x0,/* GMAC */
    DMA_IF_PCI  = 0x1,/*PCI */
    DMA_IF_PCIE = 0x2 /*PCI Express */
}dma_iftype_t;


struct dma_lib_api{
    A_UINT16  (*tx_init)(dma_engine_t eng_no, dma_iftype_t  if_type);
    void        (*tx_start)(dma_engine_t eng_no);
    A_UINT16  (*rx_init)(dma_engine_t eng_no, dma_iftype_t  if_type);
    void        (*rx_config)(dma_engine_t eng_no, a_uint16_t num_desc,
    						 a_uint16_t   gran);
    void        (*rx_start)(dma_engine_t  eng_no); 
    A_UINT32  (*intr_status)(dma_iftype_t  if_type);
    A_UINT16  (*hard_xmit)(dma_engine_t eng_no, VBUF *buf);
    void        (*flush_xmit)(dma_engine_t  eng_no);
    A_UINT16    (*xmit_done)(dma_engine_t   eng_no);
    VBUF *      (*reap_xmitted)(dma_engine_t  eng_no);
    VBUF *      (*reap_recv)(dma_engine_t  eng_no);
    void        (*return_recv)(dma_engine_t  eng_no, VBUF *buf);
    A_UINT16    (*recv_pkt)(dma_engine_t  eng_no);
};


/**
 * @brief Install the DMA lib api's this for ROM patching
 *        support
 * 
 * @param apis
 */
void        dma_lib_module_install(struct dma_lib_api  *apis);

#endif
