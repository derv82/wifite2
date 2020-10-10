/*
 *  Copyright (c) 2000-2002 Atheros Communications, Inc., All Rights Reserved
 *
 */

#ident "$Id: //depot/sw/branches/fusion_usb/target_firmware/wlan/target/ratectrl11n/ar5416Phy.c#5 $"

#include "ratectrl.h"
#include "ratectrl11n.h"

#define SHORT_PRE 1
#define LONG_PRE 0

#define WLAN_PHY_HT_20_SS       WLAN_RC_PHY_HT_20_SS
#define WLAN_PHY_HT_20_SS_HGI   WLAN_RC_PHY_HT_20_SS_HGI
#define WLAN_PHY_HT_20_DS       WLAN_RC_PHY_HT_20_DS
#define WLAN_PHY_HT_20_DS_HGI   WLAN_RC_PHY_HT_20_DS_HGI
#define WLAN_PHY_HT_40_SS       WLAN_RC_PHY_HT_40_SS
#define WLAN_PHY_HT_40_DS       WLAN_RC_PHY_HT_40_DS
#define WLAN_PHY_HT_40_DS_HGI   WLAN_RC_PHY_HT_40_DS_HGI
#define WLAN_PHY_HT_40_SS_HGI   WLAN_RC_PHY_HT_40_SS_HGI


/* TRUE_ALL_11N - valid for 20/40/Legacy, TRUE - Legacy only, TRUE_20 - HT 20 only, TRUE_40 - HT 40 only */
/* 4ms frame limit not used for NG mode.  The values filled for HT are the 64K max aggregate limit */

#ifndef MAGPIE_MERLIN // K2  

RATE_TABLE_11N ar5416_11ngRateTable = {

    54,  /* number of rates - should match the no. of rows below */ 
   100,  /* probe interval */     
    50,  /* rssi reduce interval */    
    WLAN_RC_HT_FLAG,  /* Phy rates allowed initially */
    {/*                    Multiple      Single    */
     /*                    stream        stream                                              short    dot11 ctrl  RssiAck  RssiAck  Base  CW40   SGI    Ht  tx chain 4ms tx valid for*/
     /*                    valid         valid                           Kbps   uKbps  RC    Preamble Rate  Rate  ValidMin DeltaMin Idx   Idx    Idx    Idx mask     limit  UAPSD    */
     /*    1 Mb [0]  */ {  TRUE_ALL_11N, TRUE_ALL_11N, WLAN_PHY_CCK,     1000,  900,   0x1b, 0x00,    2,    0,     0,      1,       0,    0,     0,     0,  3, 7,    0, TRUE },
     /*    2 Mb [1]  */ {  TRUE_ALL_11N, TRUE_ALL_11N, WLAN_PHY_CCK,     2000,  1900,  0x1a, 0x04,    4,    1,     1,      1,       1,    1,     1,     1,  3, 7,    0, FALSE},
     /*  5.5 Mb [2]  */ {  TRUE_ALL_11N, TRUE_ALL_11N, WLAN_PHY_CCK,     5500,  4900,  0x19, 0x04,    11,   2,     2,      2,       2,    2,     2,     2,  3, 7,    0, FALSE},
     /*   11 Mb [3]  */ {  TRUE_ALL_11N, TRUE_ALL_11N, WLAN_PHY_CCK,     11000, 8100,  0x18, 0x04,    22,   3,     3,      2,       3,    3,     3,     3,  3, 7,    0, TRUE},
     /*    6 Mb [4]  */ {  FALSE,        FALSE,        WLAN_PHY_OFDM,    6000,  5400,  0x0b, 0x00,    12,   4,     2,      1,       4,    4,     4,     4,  3, 7,    0, FALSE},
     /*    9 Mb [5]  */ {  FALSE,        FALSE,        WLAN_PHY_OFDM,    9000,  7800,  0x0f, 0x00,    18,   4,     3,      1,       5,    5,     5,     5,  3, 7,    0, FALSE},
     /*   12 Mb [6]  */ {  TRUE,         TRUE,         WLAN_PHY_OFDM,    12000, 10100, 0x0a, 0x00,    24,   6,     4,      1,       6,    6,     6,     6,  3, 7,    0, FALSE},
     /*   18 Mb [7]  */ {  TRUE,         TRUE,         WLAN_PHY_OFDM,    18000, 14100, 0x0e, 0x00,    36,   6,     6,      2,       7,    7,     7,     7,  3, 7,    0, FALSE},
     /*   24 Mb [8]  */ {  TRUE,         TRUE,         WLAN_PHY_OFDM,    24000, 17700, 0x09, 0x00,    48,   8,     10,     3,       8,    8,     8,     8,  3, 7,    0, TRUE},
     /*   36 Mb [9]  */ {  TRUE,         TRUE,         WLAN_PHY_OFDM,    36000, 23700, 0x0d, 0x00,    72,   8,     14,     3,       9,    9,     9,     9,  3, 7,    0, FALSE},
     /*   48 Mb [10] */ {  TRUE,         TRUE,         WLAN_PHY_OFDM,    48000, 27400, 0x08, 0x00,    96,   8,     20,     3,       10,   10,    10,    10, 1, 1,    0, FALSE},
     /*   54 Mb [11] */ {  TRUE,         TRUE,         WLAN_PHY_OFDM,    54000, 30900, 0x0c, 0x00,    108,  8,     23,     3,       11,   11,    11,    11, 1, 1,    0, TRUE},
     /*  6.5 Mb [12] */ {  FALSE,        FALSE,        WLAN_PHY_HT_20_SS,6500,  6400,  0x80, 0x00,    0,    4,     2,      3,       12,   33,    12,    33, 3, 7, 3216, TRUE},
     /*   13 Mb [13] */ {  TRUE_20,      TRUE_20,      WLAN_PHY_HT_20_SS,13000, 12700, 0x81, 0x00,    1,    6,     4,      3,       13,   34,    13,    34, 3, 7, 6434, TRUE},
     /* 19.5 Mb [14] */ {  TRUE_20,      TRUE_20,      WLAN_PHY_HT_20_SS,19500, 18800, 0x82, 0x00,    2,    6,     6,      3,       14,   35,    14,    35, 3, 7, 9650, FALSE},
     /*   26 Mb [15] */ {  TRUE_20,      TRUE_20,      WLAN_PHY_HT_20_SS,26000, 25000, 0x83, 0x00,    3,    8,     10,     3,       15,   36,    15,    36, 3, 7, 12868, FALSE},
     /*   39 Mb [16] */ {  TRUE_20,      TRUE_20,      WLAN_PHY_HT_20_SS,39000, 36700, 0x84, 0x00,    4,    8,     14,     3,       16,   37,    17,    38, 3, 7, 19304, TRUE},
     /* 43.3 Mb [17] */ {  FALSE,        TRUE_20,  WLAN_PHY_HT_20_SS_HGI,43300, 39200, 0x84, 0x00,    4,    8,     14,     3,       16,   37,    17,    38, 3, 7, 21460, TRUE},
     /*   52 Mb [18] */ {  FALSE,        TRUE_20,      WLAN_PHY_HT_20_SS,52000, 48100, 0x85, 0x00,    5,    8,     20,     3,       18,   39,    19,    40, 1, 1, 25740, FALSE},
     /* 57.8 Mb [19] */ {  FALSE,        TRUE_20,  WLAN_PHY_HT_20_SS_HGI,57800, 52300, 0x85, 0x00,    5,    8,     20,     3,       18,   39,    19,    40, 1, 1, 28620, FALSE},
     /* 58.5 Mb [20] */ {  FALSE,        TRUE_20,      WLAN_PHY_HT_20_SS,58500, 53500, 0x86, 0x00,    6,    8,     23,     3,       20,   41,    21,    42, 1, 1, 28956, FALSE},
     /*   65 Mb [21] */ {  FALSE,        TRUE_20,  WLAN_PHY_HT_20_SS_HGI,65000, 58800, 0x86, 0x00,    6,    8,     23,     3,       20,   41,    21,    42, 1, 1, 32200, FALSE},
     /*   65 Mb [22] */ {  FALSE,        TRUE_20,      WLAN_PHY_HT_20_SS,65000, 58801, 0x87, 0x00,    7,    8,     25,     3,       22,   43,    23,    44, 1, 1, 32200, TRUE},
     /* 72.2 Mb [23] */ {  FALSE,        TRUE_20,  WLAN_PHY_HT_20_SS_HGI,72200, 65400, 0x87, 0x00,    7,    8,     25,     3,       22,   43,    23,    44, 1, 1, 35750, TRUE},
     /*   52 Mb [24] */ {  TRUE_20,      FALSE,        WLAN_PHY_HT_20_DS,52000, 48100, 0x8b, 0x00,    11,   8,     10,     3,       24,   45,    24,    45, 3, 7, 25736, FALSE},
     /*   78 Mb [25] */ {  TRUE_20,      FALSE,        WLAN_PHY_HT_20_DS,78000, 69500, 0x8c, 0x00,    12,   8,     14,     3,       25,   46,    26,    47, 3, 7, 38600, TRUE},
     /* 86.7 Mb [26] */ {  FALSE,        FALSE,    WLAN_PHY_HT_20_DS_HGI,86700, 78400, 0x8c, 0x00,    12,   8,     14,     3,       25,   46,    26,    47, 3, 7, 42890, TRUE},
     /*  104 Mb [27] */ {  TRUE_20,      FALSE,        WLAN_PHY_HT_20_DS,104000,89500, 0x8d, 0x00,    13,   8,     20,     3,       27,   48,    28,    49, 3, 5, 51472, FALSE},
     /* 115.6Mb [28] */ {  FALSE,        FALSE,    WLAN_PHY_HT_20_DS_HGI,115600,103900,0x8d, 0x00,    13,   8,     20,     3,       27,   48,    28,    49, 3, 5, 57190, FALSE},
     /*  117 Mb [29] */ {  TRUE_20,      FALSE,        WLAN_PHY_HT_20_DS,117000,105200,0x8e, 0x00,    14,   8,     23,     3,       29,   50,    30,    51, 3, 5, 57890, FALSE},
     /*  130 Mb [30] */ {  FALSE,        FALSE,    WLAN_PHY_HT_20_DS_HGI,130000,116090,0x8e, 0x00,    14,   8,     23,     3,       29,   50,    30,    51, 3, 5, 64320, FALSE},
     /*  130 Mb [31] */ {  TRUE_20,      FALSE,        WLAN_PHY_HT_20_DS,130000,116100,0x8f, 0x00,    15,   8,     25,     3,       31,   52,    32,    53, 3, 5, 64320, TRUE},
     /* 144.4Mb [32] */ {  TRUE_20,      FALSE,    WLAN_PHY_HT_20_DS_HGI,144400,128100,0x8f, 0x00,    15,   8,     25,     3,       31,   52,    32,    53, 3, 5, 71490, TRUE},
     /* 13.5 Mb [33] */ {  TRUE_40,      TRUE_40,      WLAN_PHY_HT_40_SS,13500, 13200, 0x80, 0x00,    0,    8,     2,      3,       12,   33,    33,    33, 3, 7, 6684, TRUE},
     /* 27.0 Mb [34] */ {  TRUE_40,      TRUE_40,      WLAN_PHY_HT_40_SS,27500, 25900, 0x81, 0x00,    1,    8,     4,      3,       13,   34,    34,    34, 3, 7, 13368, TRUE},
     /* 40.5 Mb [35] */ {  TRUE_40,      TRUE_40,      WLAN_PHY_HT_40_SS,40500, 38600, 0x82, 0x00,    2,    8,     6,      3,       14,   35,    35,    35, 3, 7, 20052, FALSE},
     /*   54 Mb [36] */ {  TRUE_40,      TRUE_40,      WLAN_PHY_HT_40_SS,54000, 49800, 0x83, 0x00,    3,    8,     10,     3,       15,   36,    36,    36, 3, 7, 26738, FALSE},
     /*   81 Mb [37] */ {  TRUE_40,      TRUE_40,      WLAN_PHY_HT_40_SS,81500, 72200, 0x84, 0x00,    4,    8,     14,     3,       16,   37,    38,    38, 3, 7, 40104, TRUE},
     /*   90 Mb [38] */ {  FALSE,        TRUE_40,  WLAN_PHY_HT_40_SS_HGI,90000, 81500, 0x84, 0x00,    4,    8,     14,     3,       16,   37,    38,    38, 3, 7, 44590, TRUE},
     /*  108 Mb [39] */ {  FALSE,        TRUE_40,      WLAN_PHY_HT_40_SS,108000,92900, 0x85, 0x00,    5,    8,     20,     3,       18,   39,    40,    40, 1, 1, 53476, FALSE},
     /*  120 Mb [40] */ {  FALSE,        TRUE_40,  WLAN_PHY_HT_40_SS_HGI,120000,102100,0x85, 0x00,    5,    8,     20,     3,       18,   39,    40,    40, 1, 1, 59450, FALSE},
     /* 121.5Mb [41] */ {  FALSE,        TRUE_40,      WLAN_PHY_HT_40_SS,121500,102700,0x86, 0x00,    6,    8,     23,     3,       20,   41,    42,    42, 1, 1, 60156, FALSE},
     /*  135 Mb [42] */ {  FALSE,        TRUE_40,  WLAN_PHY_HT_40_SS_HGI,135000,111900,0x86, 0x00,    6,    8,     23,     3,       20,   41,    42,    42, 1, 1, 66840, FALSE},
     /*  135 Mb [43] */ {  FALSE,        TRUE_40,      WLAN_PHY_HT_40_SS,135000,112000,0x87, 0x00,    7,    8,     25,     3,       22,   43,    44,    44, 1, 1, 66840, TRUE},
     /*  150 Mb [44] */ {  FALSE,        TRUE_40,  WLAN_PHY_HT_40_SS_HGI,150000,122000,0x87, 0x00,    7,    8,     25,     3,       22,   43,    44,    44, 1, 1, 74200, TRUE},     
     /*  108 Mb [45] */ {  TRUE_40,      FALSE,        WLAN_PHY_HT_40_DS,108000,92500, 0x8b, 0x00,    11,   8,     10,     3,       24,   45,    45,    45, 3, 7, 53440, FALSE},
     /*  162 Mb [46] */ {  TRUE_40,      FALSE,        WLAN_PHY_HT_40_DS,162000,130300,0x8c, 0x00,    12,   8,     14,     3,       25,   46,    47,    47, 3, 7, 80160, TRUE},
     /*  180 Mb [47] */ {  FALSE,        FALSE,    WLAN_PHY_HT_40_DS_HGI,180000,156900,0x8c, 0x00,    12,   8,     14,     3,       25,   46,    47,    47, 3, 7, 89090, TRUE},
     /*  216 Mb [48] */ {  TRUE_40,      FALSE,        WLAN_PHY_HT_40_DS,216000,162800,0x8d, 0x00,    13,   8,     20,     3,       27,   48,    49,    49, 3, 5, 106880, FALSE},
     /*  240 Mb [49] */ {  FALSE,        FALSE,    WLAN_PHY_HT_40_DS_HGI,240000,178000,0x8d, 0x00,    13,   8,     20,     3,       27,   48,    49,    49, 3, 5, 118790, FALSE},
     /*  243 Mb [50] */ {  TRUE_40,      FALSE,        WLAN_PHY_HT_40_DS,243000,178200,0x8e, 0x00,    14,   8,     23,     3,       29,   50,    51,    51, 3, 5, 120240, FALSE},
     /*  270 Mb [51] */ {  FALSE,        FALSE,    WLAN_PHY_HT_40_DS_HGI,270000,192050,0x8e, 0x00,    14,   8,     23,     3,       29,   50,    51,    51, 3, 5, 133600, FALSE},
     /*  270 Mb [52] */ {  TRUE_40,      FALSE,        WLAN_PHY_HT_40_DS,270000,192100,0x8f, 0x00,    15,   8,     23,     3,       31,   52,    53,    53, 3, 5, 133600, FALSE},
     /*  300 Mb [53] */ {  TRUE_40,      FALSE,    WLAN_PHY_HT_40_DS_HGI,300000,207000,0x8f, 0x00,    15,   8,     25,     3,       31,   52,    53,    53, 3, 5, 148400, TRUE},
     /*                    Multiple      Single    */
     /*                    stream        stream                                              short    dot11 ctrl  RssiAck  RssiAck  Base  CW40   SGI    Ht  tx chain 4ms tx valid for*/
     /*                    valid         valid                           Kbps   uKbps  RC    Preamble Rate  Rate  ValidMin DeltaMin Idx   Idx    Idx    Idx mask     limit  UAPSD    */     
    },
};

#else

RATE_TABLE_11N ar5416_11ngRateTable = {

    46,  /* number of rates - should match the no. of rows below */ 
    50,  /* probe interval */     
    50,  /* rssi reduce interval */    
    WLAN_RC_HT_FLAG,  /* Phy rates allowed initially */
    {/*                    Multiple      Single      Single    */
     /*                    stream        stream      stream                                              short    dot11 ctrl  RssiAck  RssiAck  Base  CW40   SGI    Ht  tx chain 4ms tx valid for*/
     /*                    valid         valid         STBC                           Kbps   uKbps  RC    Preamble Rate  Rate  ValidMin DeltaMin Idx   Idx    Idx    Idx mask     limit  UAPSD    */
     /*    1 Mb [0]  */ {  TRUE_ALL_11N, TRUE_ALL_11N, TRUE_ALL_11N,  WLAN_PHY_CCK,     1000,  900,   0x1b, 0x00,    2,    0,     0,      1,       0,    0,     0,     0,  3, 7,    0, TRUE },
     /*    2 Mb [1]  */ {  TRUE_ALL_11N, TRUE_ALL_11N, TRUE_ALL_11N,  WLAN_PHY_CCK,     2000,  1900,  0x1a, 0x04,    4,    1,     1,      1,       1,    1,     1,     1,  3, 7,    0, FALSE},
     /*  5.5 Mb [2]  */ {  TRUE_ALL_11N, TRUE_ALL_11N, TRUE_ALL_11N,  WLAN_PHY_CCK,     5500,  4900,  0x19, 0x04,    11,   2,     2,      2,       2,    2,     2,     2,  3, 7,    0, FALSE},
     /*   11 Mb [3]  */ {  TRUE_ALL_11N, TRUE_ALL_11N, TRUE_ALL_11N,  WLAN_PHY_CCK,     11000, 8100,  0x18, 0x04,    22,   3,     3,      2,       3,    3,     3,     3,  3, 7,    0, TRUE},
     /*    6 Mb [4]  */ {  FALSE,        FALSE,        FALSE,         WLAN_PHY_OFDM,    6000,  5400,  0x0b, 0x00,    12,   4,     2,      1,       4,    4,     4,     4,  3, 7,    0, FALSE},
     /*    9 Mb [5]  */ {  FALSE,        FALSE,        FALSE,         WLAN_PHY_OFDM,    9000,  7800,  0x0f, 0x00,    18,   4,     3,      1,       5,    5,     5,     5,  3, 7,    0, FALSE},
     /*   12 Mb [6]  */ {  TRUE,         TRUE,         TRUE,          WLAN_PHY_OFDM,    12000, 10100, 0x0a, 0x00,    24,   6,     4,      1,       6,    6,     6,     6,  3, 7,    0, FALSE},
     /*   18 Mb [7]  */ {  TRUE,         TRUE,         TRUE,          WLAN_PHY_OFDM,    18000, 14100, 0x0e, 0x00,    36,   6,     6,      2,       7,    7,     7,     7,  3, 7,    0, FALSE},
     /*   24 Mb [8]  */ {  TRUE,         TRUE,         TRUE,          WLAN_PHY_OFDM,    24000, 17700, 0x09, 0x00,    48,   8,     10,     3,       8,    8,     8,     8,  3, 7,    0, TRUE},
     /*   36 Mb [9]  */ {  TRUE,         TRUE,         TRUE,          WLAN_PHY_OFDM,    36000, 23700, 0x0d, 0x00,    72,   8,     14,     3,       9,    9,     9,     9,  3, 7,    0, FALSE},
     /*   48 Mb [10] */ {  TRUE,         TRUE,         TRUE,          WLAN_PHY_OFDM,    48000, 27400, 0x08, 0x00,    96,   8,     20,     3,       10,   10,    10,    10, 1, 1,    0, FALSE},
     /*   54 Mb [11] */ {  TRUE,         TRUE,         TRUE,          WLAN_PHY_OFDM,    54000, 30900, 0x0c, 0x00,    108,  8,     23,     3,       11,   11,    11,    11, 1, 1,    0, TRUE},
     /*  6.5 Mb [12] */ {  FALSE,        FALSE,        FALSE,         WLAN_PHY_HT_20_SS,6500,  6400,  0x80, 0x00,    0,    4,     2,      3,       12,   28,    12,    28, 3, 7, 3216, TRUE},
     /*   13 Mb [13] */ {  TRUE_20,      TRUE_20,      TRUE_20,       WLAN_PHY_HT_20_SS,13000, 12700, 0x81, 0x00,    1,    6,     4,      3,       13,   29,    13,    29, 3, 7, 6434, TRUE},
     /* 19.5 Mb [14] */ {  TRUE_20,      TRUE_20,      TRUE_20,       WLAN_PHY_HT_20_SS,19500, 18800, 0x82, 0x00,    2,    6,     6,      3,       14,   30,    14,    30, 3, 7, 9650, FALSE},
     /*   26 Mb [15] */ {  TRUE_20,      TRUE_20,      TRUE_20,       WLAN_PHY_HT_20_SS,26000, 25000, 0x83, 0x00,    3,    8,     10,     3,       15,   31,    15,    31, 3, 7, 12868, FALSE},
     /*   39 Mb [16] */ {  TRUE_20,      TRUE_20,      TRUE_20,       WLAN_PHY_HT_20_SS,39000, 36700, 0x84, 0x00,    4,    8,     14,     3,       16,   32,    16,    32, 3, 7, 19304, TRUE},
     /*   52 Mb [17] */ {  FALSE,        TRUE_20,      TRUE_20,       WLAN_PHY_HT_20_SS,52000, 48100, 0x85, 0x00,    5,    8,     20,     3,       17,   33,    17,    33, 1, 1, 25740, FALSE},
     /* 58.5 Mb [18] */ {  FALSE,        TRUE_20,      TRUE_20,       WLAN_PHY_HT_20_SS,58500, 53500, 0x86, 0x00,    6,    8,     23,     3,       18,   34,    18,    34, 1, 1, 28956, FALSE},
     /*   65 Mb [19] */ {  FALSE,        TRUE_20,      FALSE,         WLAN_PHY_HT_20_SS,65000, 59000, 0x87, 0x00,    7,    8,     25,     3,       19,   35,    19,    36, 1, 1, 32180, TRUE},
     /*   13 Mb [20] */ {  FALSE,        FALSE,        FALSE,         WLAN_PHY_HT_20_DS,13000, 12700, 0x88, 0x00,    8,    4,     2,      3,       20,   37,    20,    37, 3, 7, 6430, TRUE},
     /*   26 Mb [21] */ {  FALSE,        FALSE,        FALSE,         WLAN_PHY_HT_20_DS,26000, 24800, 0x89, 0x00,    9,    6,     4,      3,       21,   38,    21,    38, 3, 7, 12860, FALSE},
     /*   39 Mb [22] */ {  FALSE,        FALSE,        FALSE,         WLAN_PHY_HT_20_DS,39000, 36600, 0x8a, 0x00,    10,   6,     6,      3,       22,   39,    22,    39, 3, 7, 19300, TRUE},
     /*   52 Mb [23] */ {  TRUE_20,      FALSE,        FALSE,         WLAN_PHY_HT_20_DS,52000, 48100, 0x8b, 0x00,    11,   8,     10,     3,       23,   40,    23,    40, 3, 7, 25736, FALSE},
     /*   78 Mb [24] */ {  TRUE_20,      FALSE,        TRUE_20,       WLAN_PHY_HT_20_DS,78000, 69500, 0x8c, 0x00,    12,   8,     14,     3,       24,   41,    24,    41, 3, 7, 38600, TRUE},
     /*  104 Mb [25] */ {  TRUE_20,      FALSE,        TRUE_20,       WLAN_PHY_HT_20_DS,104000,89500, 0x8d, 0x00,    13,   8,     20,     3,       25,   42,    25,    42, 3, 5, 51472, FALSE},
     /*  117 Mb [26] */ {  TRUE_20,      FALSE,        TRUE_20,       WLAN_PHY_HT_20_DS,117000,98900, 0x8e, 0x00,    14,   8,     23,     3,       26,   43,    26,    44, 3, 5, 57890, FALSE},
     /*  130 Mb [27] */ {  TRUE_20,      FALSE,        TRUE_20,       WLAN_PHY_HT_20_DS,130000,108300,0x8f, 0x00,    15,   8,     25,     3,       27,   44,    27,    45, 3, 5, 64320, TRUE},
     /* 13.5 Mb [28] */ {  TRUE_40,      TRUE_40,      TRUE_40,       WLAN_PHY_HT_40_SS,13500, 13200, 0x80, 0x00,    0,    8,     2,      3,       12,   28,    28,    28, 3, 7, 6684, TRUE},
     /* 27.0 Mb [29] */ {  TRUE_40,      TRUE_40,      TRUE_40,       WLAN_PHY_HT_40_SS,27500, 25900, 0x81, 0x00,    1,    8,     4,      3,       13,   29,    29,    29, 3, 7, 13368, TRUE},
     /* 40.5 Mb [30] */ {  TRUE_40,      TRUE_40,      TRUE_40,       WLAN_PHY_HT_40_SS,40500, 38600, 0x82, 0x00,    2,    8,     6,      3,       14,   30,    30,    30, 3, 7, 20052, FALSE},
     /*   54 Mb [31] */ {  TRUE_40,      TRUE_40,      TRUE_40,       WLAN_PHY_HT_40_SS,54000, 49800, 0x83, 0x00,    3,    8,     10,     3,       15,   31,    31,    31, 3, 7, 26738, FALSE},
     /*   81 Mb [32] */ {  TRUE_40,      TRUE_40,      TRUE_40,       WLAN_PHY_HT_40_SS,81500, 72200, 0x84, 0x00,    4,    8,     14,     3,       16,   32,    32,    32, 3, 7, 40104, TRUE},
     /*  108 Mb [33] */ {  FALSE,        TRUE_40,      TRUE_40,       WLAN_PHY_HT_40_SS,108000,92900, 0x85, 0x00,    5,    8,     20,     3,       17,   33,    33,    33, 1, 1, 53476, FALSE},
     /* 121.5Mb [34] */ {  FALSE,        TRUE_40,      TRUE_40,       WLAN_PHY_HT_40_SS,121500,102700,0x86, 0x00,    6,    8,     23,     3,       18,   34,    34,    34, 1, 1, 60156, FALSE},
     /*  135 Mb [35] */ {  FALSE,        TRUE_40,      FALSE,         WLAN_PHY_HT_40_SS,135000,112000,0x87, 0x00,    7,    8,     25,     3,       19,   35,    36,    36, 1, 1, 66840, TRUE},
     /*  150 Mb [36] */ {  FALSE,        TRUE_40,      FALSE,     WLAN_PHY_HT_40_SS_HGI,150000,122000,0x87, 0x00,    7,    8,     25,     3,       19,   35,    36,    36, 1, 1, 74200, TRUE},     
     /*   27 Mb [37] */ {  FALSE,        FALSE,        FALSE,         WLAN_PHY_HT_40_DS,27000, 25800, 0x88, 0x00,    8,    8,     2,      3,       20,   37,    37,    37, 3, 7, 13360, TRUE},
     /*   54 Mb [38] */ {  FALSE,        FALSE,        FALSE,         WLAN_PHY_HT_40_DS,54000, 49800, 0x89, 0x00,    9,    8,     4,      3,       21,   38,    38,    38, 3, 7, 26720, FALSE},
     /*   81 Mb [39] */ {  FALSE,        FALSE,        FALSE,         WLAN_PHY_HT_40_DS,81000, 71900, 0x8a, 0x00,    10,   8,     6,      3,       22,   39,    39,    39, 3, 7, 40080, TRUE},
     /*  108 Mb [40] */ {  TRUE_40,      FALSE,        FALSE,         WLAN_PHY_HT_40_DS,108000,92500, 0x8b, 0x00,    11,   8,     10,     3,       23,   40,    40,    40, 3, 7, 53440, FALSE},
     /*  162 Mb [41] */ {  TRUE_40,      FALSE,        TRUE_40,       WLAN_PHY_HT_40_DS,162000,130300,0x8c, 0x00,    12,   8,     14,     3,       24,   41,    41,    41, 3, 7, 80160, TRUE},
     /*  216 Mb [42] */ {  TRUE_40,      FALSE,        TRUE_40,       WLAN_PHY_HT_40_DS,216000,162800,0x8d, 0x00,    13,   8,     20,     3,       25,   42,    42,    42, 3, 5, 106880, FALSE},
     /*  243 Mb [43] */ {  TRUE_40,      FALSE,        TRUE_40,       WLAN_PHY_HT_40_DS,243000,178200,0x8e, 0x00,    14,   8,     23,     3,       26,   43,    43,    43, 3, 5, 120240, FALSE},
     /*  270 Mb [44] */ {  TRUE_40,      FALSE,        TRUE_40,       WLAN_PHY_HT_40_DS,270000,192100,0x8f, 0x00,    15,   8,     23,     3,       27,   44,    45,    45, 3, 5, 133600, FALSE},
     /*  300 Mb [45] */ {  TRUE_40,      FALSE,        TRUE_40,   WLAN_PHY_HT_40_DS_HGI,300000,207000,0x8f, 0x00,    15,   8,     25,     3,       27,   44,    45,    45, 3, 5, 148400, TRUE},
     /*                    Multiple      Single    */
     /*                    stream        stream                                              short    dot11 ctrl  RssiAck  RssiAck  Base  CW40   SGI    Ht  tx chain 4ms tx valid for*/
     /*                    valid         valid                           Kbps   uKbps  RC    Preamble Rate  Rate  ValidMin DeltaMin Idx   Idx    Idx    Idx mask     limit  UAPSD    */     
    },
};

#ifdef ATH_SUPPORT_A_MODE
//static RATE_TABLE_11N ar5416_11naRateTable = {
RATE_TABLE_11N ar5416_11naRateTable = {

    42,  /* number of rates */    
    50,  /* probe interval */    
    50,  /* rssi reduce interval */    
    WLAN_RC_HT_FLAG,  /* Phy rates allowed initially */
    {/*                Multiple        Single     Single*/
     /*                  stream        stream     stream                                              rate  short    dot11 ctrl  RssiAck  RssiAck  Base  CW40   SGI    Ht  tx chain  4ms tx valid for */
     /*                   valid         valid       STBC                                Kbps   uKbps  Code  Preamble Rate  Rate  ValidMin DeltaMin Idx   Idx    Idx    Idx mask      limit  UAPSD     */
     /*    6 Mb [0]  */ {  TRUE,         TRUE,      TRUE,            WLAN_PHY_OFDM,     6000,  5400, 0x0b,  0x00,   12,   0,     2,      1,       0,    0,     0,     0,  3, 7,      0, TRUE},
     /*    9 Mb [1]  */ {  TRUE,         TRUE,      TRUE,            WLAN_PHY_OFDM,     9000,  7800, 0x0f,  0x00,   18,   0,     3,      1,       1,    1,     1,     1,  3, 7,      0, FALSE},
     /*   12 Mb [2]  */ {  TRUE,         TRUE,      TRUE,            WLAN_PHY_OFDM,    12000, 10000, 0x0a,  0x00,   24,   2,     4,      2,       2,    2,     2,     2,  3, 7,      0, TRUE},
     /*   18 Mb [3]  */ {  TRUE,         TRUE,      TRUE,            WLAN_PHY_OFDM,    18000, 13900, 0x0e,  0x00,   36,   2,     6,      2,       3,    3,     3,     3,  3, 7,      0, FALSE},
     /*   24 Mb [4]  */ {  TRUE,         TRUE,      TRUE,            WLAN_PHY_OFDM,    24000, 17300, 0x09,  0x00,   48,   4,     10,     3,       4,    4,     4,     4,  3, 7,      0, TRUE},
     /*   36 Mb [5]  */ {  TRUE,         TRUE,      TRUE,            WLAN_PHY_OFDM,    36000, 23000, 0x0d,  0x00,   72,   4,     14,     3,       5,    5,     5,     5,  3, 7,      0, FALSE},
     /*   48 Mb [6]  */ {  TRUE,         TRUE,      TRUE,            WLAN_PHY_OFDM,    48000, 27400, 0x08,  0x00,   96,   4,     20,     3,       6,    6,     6,     6,  1, 1,      0, FALSE},
     /*   54 Mb [7]  */ {  TRUE,         TRUE,      TRUE,            WLAN_PHY_OFDM,    54000, 29300, 0x0c,  0x00,   108,  4,     23,     3,       7,    7,     7,     7,  1, 1,      0, TRUE},
     /*  6.5 Mb [8]  */ {  TRUE_20,      TRUE_20,   TRUE_20,         WLAN_PHY_HT_20_SS, 6500,  6400, 0x80,  0x00,   0,    0,     2,      3,       8,    24,    8,     24, 3, 7,   3216, TRUE},
     /*   13 Mb [9]  */ {  TRUE_20,      TRUE_20,   TRUE_20,         WLAN_PHY_HT_20_SS,13000, 12700, 0x81,  0x00,   1,    2,     4,      3,       9,    25,    9,     25, 3, 7,   6434, TRUE},
     /* 19.5 Mb [10] */ {  TRUE_20,      TRUE_20,   TRUE_20,         WLAN_PHY_HT_20_SS,19500, 18800, 0x82,  0x00,   2,    2,     6,      3,       10,   26,    10,    26, 3, 7,   9650, FALSE},
     /*   26 Mb [11] */ {  TRUE_20,      TRUE_20,   TRUE_20,         WLAN_PHY_HT_20_SS,26000, 25000, 0x83,  0x00,   3,    4,     10,     3,       11,   27,    11,    27, 3, 7,  12868, FALSE},
     /*   39 Mb [12] */ {  TRUE_20,      TRUE_20,   TRUE_20,         WLAN_PHY_HT_20_SS,39000, 36700, 0x84,  0x00,   4,    4,     14,     3,       12,   28,    12,    28, 3, 7,  19304, TRUE},
     /*   52 Mb [13] */ {  FALSE,        TRUE_20,   TRUE_20,         WLAN_PHY_HT_20_SS,52000, 48100, 0x85,  0x00,   5,    4,     20,     3,       13,   29,    13,    29, 1, 1,  25740, FALSE},
     /* 58.5 Mb [14] */ {  FALSE,        TRUE_20,   TRUE_20,         WLAN_PHY_HT_20_SS,58500, 53500, 0x86,  0x00,   6,    4,     23,     3,       14,   30,    14,    30, 1, 1,  28956, FALSE},
     /*   65 Mb [15] */ {  FALSE,        TRUE_20,   FALSE,           WLAN_PHY_HT_20_SS,65000, 59000, 0x87,  0x00,   7,    4,     25,     3,       15,   31,    15,    32, 1, 1,  32180, TRUE},
     /*   13 Mb [16] */ {  FALSE,        FALSE,     FALSE,           WLAN_PHY_HT_20_DS,13000, 12700, 0x88,  0x00,   8,    0,     2,      3,       16,   33,    16,    33, 3, 7,   6430, TRUE},
     /*   26 Mb [17] */ {  FALSE,        FALSE,     FALSE,           WLAN_PHY_HT_20_DS,26000, 24800, 0x89,  0x00,   9,    2,     4,      3,       17,   34,    17,    34, 3, 7,  12860, FALSE},
     /*   39 Mb [18] */ {  FALSE,        FALSE,     FALSE,           WLAN_PHY_HT_20_DS,39000, 36600, 0x8a,  0x00,   10,   2,     6,      3,       18,   35,    18,    35, 3, 7,  19300, TRUE},
     /*   52 Mb [19] */ {  TRUE_20,      FALSE,     FALSE,           WLAN_PHY_HT_20_DS,52000, 48100, 0x8b,  0x00,   11,   4,     10,     3,       19,   36,    19,    36, 3, 7,  25736, FALSE},
     /*   78 Mb [20] */ {  TRUE_20,      FALSE,     TRUE_20,         WLAN_PHY_HT_20_DS,78000, 69500, 0x8c,  0x00,   12,   4,     14,     3,       20,   37,    20,    37, 3, 7,  38600, TRUE},
     /*  104 Mb [21] */ {  TRUE_20,      FALSE,     TRUE_20,         WLAN_PHY_HT_20_DS,104000,89500, 0x8d,  0x00,   13,   4,     20,     3,       21,   38,    21,    38, 3, 5,  51472, FALSE},
     /*  117 Mb [22] */ {  TRUE_20,      FALSE,     TRUE_20,         WLAN_PHY_HT_20_DS,117000,98900, 0x8e,  0x00,   14,   4,     23,     3,       22,   39,    22,    39, 3, 5,  57890, FALSE},
     /*  130 Mb [23] */ {  TRUE_20,      FALSE,     TRUE_20,         WLAN_PHY_HT_20_DS,130000,108300,0x8f,  0x00,   15,   4,     25,     3,       23,   40,    23,    41, 3, 5,  64320, TRUE},
     /* 13.5 Mb [24] */ {  TRUE_40,      TRUE_40,   TRUE_40,         WLAN_PHY_HT_40_SS,13500, 13200, 0x80,  0x00,   0,    0,     2,      3,       8,    24,    24,    24, 3, 7,   6684, TRUE},
     /* 27.0 Mb [25] */ {  TRUE_40,      TRUE_40,   TRUE_40,         WLAN_PHY_HT_40_SS,27500, 25900, 0x81,  0x00,   1,    2,     4,      3,       9,    25,    25,    25, 3, 7,  13368, TRUE},
     /* 40.5 Mb [26] */ {  TRUE_40,      TRUE_40,   TRUE_40,         WLAN_PHY_HT_40_SS,40500, 38600, 0x82,  0x00,   2,    2,     6,      3,       10,   26,    26,    26, 3, 7,  20052, FALSE},
     /*   54 Mb [27] */ {  TRUE_40,      TRUE_40,   TRUE_40,         WLAN_PHY_HT_40_SS,54000, 49800, 0x83,  0x00,   3,    4,     10,     3,       11,   27,    27,    27, 3, 7,  26738, FALSE},
     /*   81 Mb [28] */ {  TRUE_40,      TRUE_40,   TRUE_40,         WLAN_PHY_HT_40_SS,81500, 72200, 0x84,  0x00,   4,    4,     14,     3,       12,   28,    28,    28, 3, 7,  40104, TRUE},
     /*  108 Mb [29] */ {  FALSE,        TRUE_40,   TRUE_40,         WLAN_PHY_HT_40_SS,108000,92900, 0x85,  0x00,   5,    4,     20,     3,       13,   29,    29,    29, 1, 1,  53476, FALSE},
     /* 121.5Mb [30] */ {  FALSE,        TRUE_40,   TRUE_40,         WLAN_PHY_HT_40_SS,121500,102700,0x86,  0x00,   6,    4,     23,     3,       14,   30,    30,    30, 1, 1,  60156, FALSE},
     /*  135 Mb [31] */ {  FALSE,        TRUE_40,   FALSE,           WLAN_PHY_HT_40_SS,135000,112000,0x87,  0x00,   7,    4,     25,     3,       15,   31,    32,    32, 1, 1,  66840, TRUE},
     /*  150 Mb [32] */ {  FALSE,        TRUE_40,   FALSE,       WLAN_PHY_HT_40_SS_HGI,150000,122000,0x87,  0x00,   7,    8,     25,     3,       15,   31,    32,    32, 1, 1, 65535, TRUE},     
     /*   27 Mb [33] */ {  FALSE,        FALSE,     FALSE,           WLAN_PHY_HT_40_DS,27000, 25800, 0x88,  0x00,   8,    0,     2,      3,       16,   33,    33,    33, 3, 7,  13360, TRUE},
     /*   54 Mb [34] */ {  FALSE,        FALSE,     FALSE,           WLAN_PHY_HT_40_DS,54000, 49800, 0x89,  0x00,   9,    2,     4,      3,       17,   34,    34,    34, 3, 7,  26720, FALSE},
     /*   81 Mb [35] */ {  FALSE,        FALSE,     FALSE,           WLAN_PHY_HT_40_DS,81000, 71900, 0x8a,  0x00,   10,   2,     6,      3,       18,   35,    35,    35, 3, 7,  40080, TRUE},
     /*  108 Mb [36] */ {  TRUE_40,      FALSE,     FALSE,           WLAN_PHY_HT_40_DS,108000,92500, 0x8b,  0x00,   11,   4,     10,     3,       19,   36,    36,    36, 3, 7,  53440, FALSE},
     /*  162 Mb [37] */ {  TRUE_40,      FALSE,     TRUE_40,         WLAN_PHY_HT_40_DS,162000,130300,0x8c,  0x00,   12,   4,     14,     3,       20,   37,    37,    37, 3, 7,  80160, TRUE},
     /*  216 Mb [38] */ {  TRUE_40,      FALSE,     TRUE_40,         WLAN_PHY_HT_40_DS,216000,162800,0x8d,  0x00,   13,   4,     20,     3,       21,   38,    38,    38, 3, 5, 106880, FALSE},
     /*  243 Mb [39] */ {  TRUE_40,      FALSE,     TRUE_40,         WLAN_PHY_HT_40_DS,243000,178200,0x8e,  0x00,   14,   4,     23,     3,       22,   39,    39,    39, 3, 5, 120240, FALSE},
     /*  270 Mb [40] */ {  TRUE_40,      FALSE,     TRUE_40,         WLAN_PHY_HT_40_DS,270000,192100,0x8f,  0x00,   15,   4,     25,     3,       23,   40,    41,    41, 3, 5, 133600, TRUE},
     /*  300 Mb [41] */ {  TRUE_40,      FALSE,     TRUE_40,     WLAN_PHY_HT_40_DS_HGI,300000,207000,0x8f,  0x00,   15,   4,     25,     3,       23,   40,    41,    41, 3, 5, 148400, TRUE},
     /*                    stream        stream                                                 rate  short    dot11 ctrl  RssiAck  RssiAck  Base  CW40   SGI    Ht  tx chain  4ms tx valid for */
     /*                    valid         valid                                             Kbps   uKbps  Code  Preamble Rate  Rate  ValidMin DeltaMin Idx   Idx    Idx    Idx mask      limit  UAPSD     */     
    },
};
#endif //ATH_SUPPORT_A_MODE

#endif //#ifdef MAGPIE_MERLIN // MAGPIE_MERLIN 

void
ar5416AttachRateTables(struct atheros_softc *sc)
{
    sc->hwRateTable[WIRELESS_MODE_11NG]  = &ar5416_11ngRateTable;
#ifdef ATH_SUPPORT_A_MODE
    sc->hwRateTable[WIRELESS_MODE_11NA]  = &ar5416_11naRateTable;
#endif
}
