#!/bin/sh

# Copyright (c) 2013 Qualcomm Atheros, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted (subject to the limitations in the
# disclaimer below) provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
#
#  * Neither the name of Qualcomm Atheros nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE
# GRANTED BY THIS LICENSE.  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT
# HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# This script is intended for use with separately linked ROM and RAM.
# It creates EITHER a linker script that satisfies references made by RAM
# applications to ROM symbols OR a linker script that forces symbols to
# be included in a ROM image.
#
# The option "--addrs" causes the RAM linkage script to be generated
# and the option "--externs" causes the ROM linkage script to be generated.
#
# Example usage:
#     make_ld.sh --addrs athos.rom.out athos.rom.symbols > rom.addrs.ld
#     make_ld.sh --externs athos.rom.symbols > rom.externs.ld

eval XTNM=xt-nm

Usage() {
    echo Usage:
    echo $progname '{--addrs ROM_ELF_Image | --externs} symbol_file'
}

Provide() {
    addr0=`echo $1 | sed 's/$//'`
	addr=0x`nm $image_file | grep -w $addr0 | cut -d ' ' -f 1`
    if [ "$addr" != "0x" ]
    then
    	echo PROVIDE \( $addr0 = $addr \)\;
    fi
}

Extern() {
    echo EXTERN \( $1 \)\;
}

progname=$0
script_choice=$1

if [ "$script_choice"=="--addrs" ]
then
    action=Provide
    image_file=$2

    if [ ! -r "$image_file" ]
    then
        echo "Cannot read ELF image: $image_file"
        Usage
    fi
    symbol_file=$3
elif [ "$script_choice"=="--externs" ]
then
    action=Extern
    symbol_file=$2

	if [ ! -r "$symbol_file" ]
	then
	    echo "Cannot read symbol list from: $symbol_file"
	    Usage
	fi
else
    Usage
fi

for i in `cat $symbol_file`
do
    $action $i
done
