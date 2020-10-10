
#ifndef __HIF_PCI_H
#define __HIF_PCI_H

#include <hif_api.h>
#include <dma_lib.h>


#define PCI_MAX_DATA_PKT_LEN            1664
#define PCI_MAX_CMD_PKT_LEN             512
#define PCI_MAX_BOOT_DESC               2 
     
typedef enum hif_pci_pipe_rx{
    HIF_PCI_PIPE_RX0, /*Normal Priority RX*/
    HIF_PCI_PIPE_RX1,
    HIF_PCI_PIPE_RX2,
    HIF_PCI_PIPE_RX3,
    HIF_PCI_PIPE_RX_MAX
}hif_pci_pipe_rx_t;

typedef enum hif_pci_pipe_tx{
    HIF_PCI_PIPE_TX0, /*Normal Priority TX*/
    HIF_PCI_PIPE_TX1,
    HIF_PCI_PIPE_TX_MAX
}hif_pci_pipe_tx_t;

typedef struct __pci_softc{
    HIF_CALLBACK       sw;
}__pci_softc_t;

struct hif_pci_api{
    void          (*pci_boot_init)(void);
    hif_handle_t  (*pci_init)(HIF_CONFIG *pConfig);
    void          (*pci_reset)(void);
    void          (*pci_enable)(void);
    void          (*pci_reap_xmitted)(__pci_softc_t  *sc, 
                                      dma_engine_t  eng_no);
    void          (*pci_reap_recv)(__pci_softc_t  *sc, dma_engine_t  eng_no);
    A_UINT8       (*pci_get_pipe)(dma_engine_t   eng);
    dma_engine_t  (*pci_get_tx_eng)(hif_pci_pipe_tx_t  pipe);
    dma_engine_t  (*pci_get_rx_eng)(hif_pci_pipe_rx_t  pipe);

};

void        hif_pci_api_install(struct hif_pci_api *apis);
void        hif_pci_module_install(struct hif_api *apis);
#endif


