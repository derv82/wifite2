/*
 * Copyright (c) 2013 Qualcomm Atheros, Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted (subject to the limitations in the
 * disclaimer below) provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *  * Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *  * Neither the name of Qualcomm Atheros nor the names of its
 *    contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE
 * GRANTED BY THIS LICENSE.  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT
 * HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
 * BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
 * OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
 * IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
#include "sys_cfg.h"

#if SYSTEM_MODULE_CLOCK
#include "athos_api.h"

LOCAL A_UINT32 cticks = 0;

#define  A_BAND_DEFAULT 0       // not ust now, avoiding compile error/warning, Ryan

LOCAL int curr_band = A_BAND_DEFAULT;
LOCAL void cmnos_pll_init(void);

/* We accept frequencies within this deviation from an expected frequency.  */
#define A_REFCLK_DEVIATION 800000

#define A_REFCLK_UNKNOWN  SYS_CFG_REFCLK_UNKNOWN
#define A_REFCLK_10_MHZ     SYS_CFG_REFCLK_10_MHZ
#define A_REFCLK_20_MHZ     SYS_CFG_REFCLK_20_MHZ
#define A_REFCLK_40_MHZ     SYS_CFG_REFCLK_40_MHZ

LOCAL const struct cmnos_clock_s {
    A_refclk_speed_t refclk_speed;
    A_UINT32         ticks_per_sec;
    // below are useless so far, ryan
    A_UINT32         pll_ctrl_5ghz;
    A_UINT32         pll_ctrl_24ghz;
    A_UINT32         pll_settling_time;      /* 50us */
} cmnos_clocking_table[] = {
    {A_REFCLK_10_MHZ,
     //10485760, 
     10000000,
     0x0,  
     0x0,
     0x0},

    {A_REFCLK_20_MHZ,   
     //20971520, 
     20000000,
     0x0,  
     0x0,
     0x0},

    {A_REFCLK_40_MHZ,
     //41943040, 
     40000000, 
     0x0,
     0x0,
     0x0},

    {A_REFCLK_UNKNOWN,         
     0, 
     0x0, 
     0x0,
     0x0},
};


#define CMNOS_CLOCKING_TABLE_NUM_ENTRIES \
    (sizeof(cmnos_clocking_table)/sizeof(cmnos_clocking_table[0]))

LOCAL struct cmnos_clock_s *clock_info;


LOCAL void cmnos_tick(void);

/*
 * In case we have PLL initialization problems, software can arrange
 * (e.g. through BMI) to skip PLL initialization, and other software
 * can handle it.
 */
int cmnos_skip_pll_init = 0;
A_UINT32 pll_ctrl_setting_24ghz = 0;
A_UINT32 pll_ctrl_setting_5ghz = 0;

/*
 * Use default hardware values for clock-related registers.
 * The defaults can be overridden through BMI, EJTAG, or patches.
 *
 * CPU clock frequencies depend on what mode we're in (2.4GHz or 5GHz):
 * NB: AR6001 has a "reduced power" mode, but we don't use it.
 *
 *     AR6001/AR6002 FPGA CPU clock is always at 40MHz
 *
 *     AR6001 Rev 2.x supports 4 CPU speed selections:
 *       selector:  0   1    2       3
 *         2.4GHz: 44, 88, 141, refclk
 *         5  GHz: 40, 80, 128, refclk
 *
 *     AR6002 supports 7 CPU/SoC speed selections via CORE_CLK:
 *           CORE_CLK.DIV setting: 6,7    5     4     3   2     1   0
 *                        divisor: 16    14    12    10   8     6   4
 *         2.4GHz (pll at 352MHz): 22  25.1, 29.3, 35.2, 44, 58.7, 88
 *         5  GHz (pll at 320MHz): 20  22.9, 26.7,   32, 40, 53.3, 80
 */

#if defined(DISABLE_SYNC_DURING_PLL_UPDATE_WAR)
A_UINT32 cpu_clock_setting;
#endif

//A_COMPILE_TIME_ASSERT(verify_host_interest_small_enough,
//                (sizeof(struct host_interest_s) <= HOST_INTEREST_MAX_SIZE))

//A_COMPILE_TIME_ASSERT(verify_flash_is_present_addr,
//                ((A_UINT32)&HOST_INTEREST->hi_flash_is_present) == FLASH_IS_PRESENT_TARGADDR)


LOCAL void
cmnos_delay_us(int us)
{
//    A_UINT32 start_time = A_RTC_REG_READ(LF_TIMER_COUNT0_ADDRESS);
//    unsigned int num_LF_ticks = (us+29) / 30 + 1; /* ~30.5us per LF tick */
    //A_UINT32 ref_clk = (clock_info->ticks_per_sec)/1000/1000;
    A_UINT32 ref_clk = (clock_info->ticks_per_sec) >> 20;
    A_UINT32 start_time = NOW();
    unsigned int num_ticks = us*ref_clk; // system_freq == number of ticks per 1us
    
    while ( (NOW() - start_time) < num_ticks) {
        /* busy spin */;
    }
}

/*
 * Return the number of milliseconds since startup.
 * For this purpose, a "millisecond" is approximated by
 * 1/32 of a 32KHz clock.
 */
LOCAL A_UINT32
cmnos_milliseconds(void)
{
    //unsigned int lowfreq_timer;

    //lowfreq_timer = A_RTC_REG_READ(LF_TIMER_COUNT0_ADDRESS);
    //lowfreq_timer = NOW();

    /* LF0 timer counts at 32KHz, so adjust to approximate Ms with >> 5.  */
    //lowfreq_timer = lowfreq_timer;

    /*
     * NB: We do not account for wrap, which occurs every 36
     * hours when the 32768Hz low frequency timer wraps the
     * 32 bit counter.
     */
    cmnos_tick();

    return cticks;
}


/* Expect 40MHz on AR6001 and 26MHz on AR6002 */
//LOCAL A_refclk_speed_t cmnos_refclk_speed;

LOCAL A_UINT32
cmnos_refclk_speed_get(void)
{
    return clock_info->ticks_per_sec;
}

/* The UART is clocked at the reference clock frequency. */
LOCAL A_UINT32
cmnos_uart_frequency(void)
{
#if 0
#if defined(FPGA)
    return clock_info->ticks_per_sec;
#else
    return clock_info->ticks_per_sec;
#endif
#else
    /* TBD */
    /* do we need keep a struct to hold the data ?*/
#endif
}


/*
 * Adjust any state that needs adjusting when the clock
 * speed changes.
 */
LOCAL void
cmnos_sysclk_change(void)
{
    /* OS may override this function */
}


LOCAL void
cmnos_clockregs_init(void)
{
    /* TBD */
    /* we might don't need this init() */
}

/*
 * Make whatever system-level changes are needed in order to operate
 * in the specified wireless band.
 *
 * For AR6K, we just need to set the PLL appropriately.
 */
LOCAL void
cmnos_wlan_band_set(int which_band)
{
    /* TBD */
    /* we don't have wlan need to config */
}

LOCAL void
cmnos_pll_init(void)
{
    /* TBD */
    /* we don't have pll now, */
}

LOCAL void
cmnos_clock_init(A_UINT32 ref_clk)
{
#if 1
    unsigned int i;

    /* Look up the nearest supported frequency. */
    for (i = 0;
         i < CMNOS_CLOCKING_TABLE_NUM_ENTRIES-1;
         i++)
    {
        A_UINT32 ticks_per_sec;

        ticks_per_sec = cmnos_clocking_table[i].ticks_per_sec;
        if ((ref_clk > ticks_per_sec - A_REFCLK_DEVIATION) &&
            (ref_clk < ticks_per_sec + A_REFCLK_DEVIATION))
        {
            break;
        }
    }

    clock_info = (struct cmnos_clock_s *)&cmnos_clocking_table[i];
//    HOST_INTEREST->hi_clock_info = (A_UINT32)clock_info;
    
#endif
}

////////////////////////////////////////////////////////////////////////
// software emulate ticks on millisecond based
LOCAL void
cmnos_tick(void)
{
#if 0
    
    set_ccompare0(xthal_get_ccompare(XTENSA_TIMER_0)+ONE_MSEC);

    cticks++;

#else
    static A_UINT32 last_tick = 0;
    A_UINT32 current_tick = NOW();
    A_UINT32 delta_tick;

    // tick is 32 bit register, will overflow soon
    if( current_tick < last_tick )
    {
        delta_tick = (A_UINT32 )((0xffffffff-last_tick)+current_tick+1)/(1000);
    }
    else
    {
        delta_tick = (A_UINT32 ) (current_tick - last_tick)/(1000);
    }

    if( delta_tick > 0 )
        last_tick = current_tick;

    cticks += delta_tick;
#endif
}

////////////////////////////////////////////////////////////////////////

void
cmnos_clock_module_install(struct clock_api *tbl)
{
    tbl->_clock_init         = cmnos_clock_init;
    tbl->_clockregs_init     = cmnos_clockregs_init;
    tbl->_delay_us           = cmnos_delay_us;
    tbl->_wlan_band_set      = cmnos_wlan_band_set;
    tbl->_refclk_speed_get   = cmnos_refclk_speed_get;
    tbl->_milliseconds       = cmnos_milliseconds;
    tbl->_uart_frequency     = cmnos_uart_frequency;
    tbl->_sysclk_change      = cmnos_sysclk_change;

    tbl->_clock_tick         = cmnos_tick;
}
#endif /* SYSTEM_MODULE_CLOCK */

