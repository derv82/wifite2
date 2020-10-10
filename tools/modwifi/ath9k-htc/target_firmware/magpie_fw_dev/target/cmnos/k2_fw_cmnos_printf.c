//####ECOSGPLCOPYRIGHTBEGIN####
// -------------------------------------------
// This file is part of eCos, the Embedded Configurable Operating System.
// Copyright (C) 1998, 1999, 2000, 2001, 2002 Red Hat, Inc.
// Copyright (C) 2002 Gary Thomas
//
// eCos is free software; you can redistribute it and/or modify it under
// the terms of the GNU General Public License as published by the Free
// Software Foundation; either version 2 or (at your option) any later version.
//
// eCos is distributed in the hope that it will be useful, but WITHOUT ANY
// WARRANTY; without even the implied warranty of MERCHANTABILITY or
// FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
// for more details.
//
// You should have received a copy of the GNU General Public License along
// with eCos; if not, write to the Free Software Foundation, Inc.,
// 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA.
//
// As a special exception, if other files instantiate templates or use macros
// or inline functions from this file, or you compile this file and link it
// with other works to produce a work based on this file, this file does not
// by itself cause the resulting work to be covered by the GNU General Public
// License. However the source code for this file must still be made available
// in accordance with section (3) of the GNU General Public License.
//
// This exception does not invalidate any other reasons why a work based on
// this file might be covered by the GNU General Public License.
//
// Alternative licenses for eCos may be arranged by contacting Red Hat, Inc.
// at http://sources.redhat.com/ecos/ecos-license/
// -------------------------------------------
//####ECOSGPLCOPYRIGHTEND####


#include "sys_cfg.h"

#include "dt_defs.h"

#if SYSTEM_MODULE_PRINT

#if MOVE_PRINT_TO_RAM

#include "athos_api.h"

#define is_digit(c) ((c >= '0') && (c <= '9'))

#if defined(__GNUC__) && defined(__mips__)
#define va_list __builtin_va_list
#define va_arg __builtin_va_arg
#define va_start __builtin_va_start
#define va_end __builtin_va_end
#define va_copy __builtin_va_copy
#endif

#include <stdarg.h>

LOCAL void
cmnos_write_char(char c)
{
    if (c == '\n') {
        A_PUTC('\r');
        A_PUTC('\n');
    } else if (c == '\r') {
    } else {
      A_PUTC(c);
    }
}

LOCAL void
(*_putc)(char c) = cmnos_write_char;

LOCAL int
_cvt(unsigned long val, char *buf, long radix, char *digits)
{
    char temp[80];
    char *cp = temp;
    int length = 0;

    if (val == 0) {
        /* Special case */
        *cp++ = '0';
    } else {
        while (val) {
            *cp++ = digits[val % radix];
            val /= radix;
        }
    }
    while (cp != temp) {
        *buf++ = *--cp;
        length++;
    }
    *buf = '\0';
    return (length);
}


LOCAL
int cmnos_vprintf(void (*putc)(char c), const char *fmt, va_list ap)
{
    char buf[sizeof(long)*8];
    char c, sign, *cp=buf;
    int left_prec, right_prec, zero_fill, pad, pad_on_right,
        i, islong, islonglong;
    long val = 0;
    int res = 0, length = 0;

    while ((c = *fmt++) != '\0') {
        if (c == '%') {
            c = *fmt++;
            left_prec = right_prec = pad_on_right = islong = islonglong = 0;
            if (c == '-') {
                c = *fmt++;
                pad_on_right++;
            }
            if (c == '0') {
                zero_fill = TRUE;
                c = *fmt++;
            } else {
                zero_fill = FALSE;
            }
            while (is_digit(c)) {
                left_prec = (left_prec * 10) + (c - '0');
                c = *fmt++;
            }
            if (c == '.') {
                c = *fmt++;
                zero_fill++;
                while (is_digit(c)) {
                    right_prec = (right_prec * 10) + (c - '0');
                    c = *fmt++;
                }
            } else {
                right_prec = left_prec;
            }
            sign = '\0';
            if (c == 'l') {
                // 'long' qualifier
                c = *fmt++;
		islong = 1;
                if (c == 'l') {
                    // long long qualifier
                    c = *fmt++;
                    islonglong = 1;
                }
            }
            // Fetch value [numeric descriptors only]
            switch (c) {
            case 'p':
		islong = 1;
            case 'd':
            case 'D':
            case 'x':
            case 'X':
            case 'u':
            case 'U':
            case 'b':
            case 'B':
                if (islonglong) {
                    val = va_arg(ap, long);
	        } else if (islong) {
                    val = (long)va_arg(ap, long);
		} else{
                    val = (long)va_arg(ap, int);
                }
                if ((c == 'd') || (c == 'D')) {
                    if (val < 0) {
                        sign = '-';
                        val = -val;
                    }
                } else {
                    // Mask to unsigned, sized quantity
                    if (islong) {
                        val &= (1ULL << (sizeof(long) * 8)) - 1;
                    } else{
                        val &= (1ULL << (sizeof(int) * 8)) - 1;
                    }
                }
                break;
            default:
                break;
            }
            // Process output
            switch (c) {
            case 'p':  // Pointer
                (*putc)('0');
                (*putc)('x');
                zero_fill = TRUE;
                left_prec = sizeof(unsigned long)*2;
            case 'd':
            case 'D':
            case 'u':
            case 'U':
            case 'x':
            case 'X':
                switch (c) {
                case 'd':
                case 'D':
                case 'u':
                case 'U':
                    length = _cvt(val, buf, 10, "0123456789");
                    break;
                case 'p':
                case 'x':
                    length = _cvt(val, buf, 16, "0123456789abcdef");
                    break;
                case 'X':
                    length = _cvt(val, buf, 16, "0123456789ABCDEF");
                    break;
                }
                cp = buf;
                break;
            case 's':
            case 'S':
                cp = va_arg(ap, char *);
                if (cp == NULL)  {
                    cp = "<null>";
                }
                length = 0;
                while (cp[length] != '\0') length++;
                break;
            case 'c':
            case 'C':
                c = va_arg(ap, int /*char*/);
                (*putc)(c);
                res++;
                continue;
            case 'b':
            case 'B':
                length = left_prec;
                if (left_prec == 0) {
                    if (islonglong)
                        length = sizeof(long)*8;
                    else if (islong)
                        length = sizeof(long)*8;
                    else
                        length = sizeof(int)*8;
                }
                for (i = 0;  i < length-1;  i++) {
                    buf[i] = ((val & ((long)1<<i)) ? '1' : '.');
                }
                cp = buf;
                break;
            case '%':
                (*putc)('%');
                break;
            default:
                (*putc)('%');
                (*putc)(c);
                res += 2;
            }
            pad = left_prec - length;
            if (sign != '\0') {
                pad--;
            }
            if (zero_fill) {
                c = '0';
                if (sign != '\0') {
                    (*putc)(sign);
                    res++;
                    sign = '\0';
                }
            } else {
                c = ' ';
            }
            if (!pad_on_right) {
                while (pad-- > 0) {
                    (*putc)(c);
                    res++;
                }
            }
            if (sign != '\0') {
                (*putc)(sign);
                res++;
            }
            while (length-- > 0) {
                c = *cp++;
                (*putc)(c);
                res++;
            }
            if (pad_on_right) {
                while (pad-- > 0) {
                    (*putc)(' ');
                    res++;
                }
            }
        } else {
            (*putc)(c);
            res++;
        }
    }
    return (res);
}

int
fw_cmnos_printf(const char *fmt, ...)
{
    va_list ap;
    int ret;

    va_start(ap, fmt);

    //if (A_SERIAL_ENABLED()) {
    if (1) {
        ret = cmnos_vprintf(_putc, fmt, ap);
    } else {
        ret = 0;
    }

    va_end(ap);
    return (ret);
}

#endif /* MOVE_PRINT_TO_RAM */

#endif /* SYSTEM_MODULE_PRINT */
