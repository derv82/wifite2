#!/usr/bin/perl -w

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

###############################################################
#binary-to-hex perl tool: obtained & modified on 10/05/08
###############################################################
use strict;

my ($format, $binfile, $outfile, $arr_form, $ColNum, $show_hex, $filesize);
$format = $ARGV[0] || usage();
$binfile = $ARGV[1] || usage();
$outfile = $ARGV[2] || $binfile.".$format";
$arr_form = $ARGV[3];
$ColNum = $ARGV[4] || usage();
$show_hex = $ARGV[5];

my ($orig, @converted);

    $orig = readdata ($binfile);

    $orig = hexdump($orig);
    if ($show_hex) {print "Original Binary text:\n\t $orig","\n\n";}

    if ($format eq 'a' || $format eq 'asm') {
        @converted = convert_to_asm ($orig);

    } elsif ($format eq 'c') {
        @converted = convert_to_c ($orig);

    } else {
        print "Unknown format to convert!\n";
        exit (-1);
    }
    if ($show_hex) {print "Converted hex text:\n",join ('', @converted), "\n";}

    writedata ($outfile, @converted);

sub convert_to_asm {
    my @data = split(' ', join (' ', @_)); #nop here only one list passed to join

    my $i = 0;
    if ($arr_form){
      foreach (@data) {
  	  if ($i++ < 8) {
	    $_=$_."h, 0";
  	  } else {
	    $_=$_."h\nbyte 0";
	    $i = 0;
	  }
      }

      unshift (@data, "byte 0");
      $data[-1] =~s/[,|\nbyte] 0$//g;
    }else{
      foreach (@data){
        if ($i++ < $ColNum-1) {
          #$_.=",";
        }else {
          $_.="\n";
          $i = 0;
        }
      }      
    }  
    return @data;
}

sub convert_to_c {
    my @data = split(' ', join (' ', @_)); #nop here only one list passed to join

    my $i = 0;
    if ($arr_form){
      foreach (@data) {
  	if ($i++ < $ColNum-1) {
	    $_.=", 0x";
	} else {
	    $_.=",\n\t0x";
	    $i = 0;
	}
      }
      unshift (@data, "unsigned char data[$filesize] = {\n\t0x");  #add some pattern at the front of @data
      $data[-1] =~s/0x$//g;
      $data[-1] =~s/[ |\n\t]//g;
      $data[-1] =~s/\,//g;
      push (@data, "\n};");
    }else{
      foreach (@data){
        if ($i++ < $ColNum-1) {
        }else {
          $_.="\n";
          $i = 0;
        }
      }      
    }
    return @data;
}

sub readdata {
    my ($line);
    my ($file) = @_;
    #printf "dbg:file = $file\n";
    open (BF, "$file") || die "Cannot open $file: $!";  #$! contains current value of errno
    binmode (BF);
    $filesize = (stat($file))[7];
    my ($DATA) = ""; #<BF>;
    my (@Data_check) = <BF>;
    foreach $line (@Data_check){
      #printf "dbg:line = $line\n";
      $DATA.=$line;
    }  
    #printf "dbg:DATA string = $DATA\n";
    close (BF);
    return ($DATA);
}

sub writedata {
    my ($file, @FomatData) = @_;
    open (AF, ">$file") || die "Cannot open $file: $!";
    my $i = 0;
    my $b0 = 0;    
    my $b1 = 0; 
    my $b2 = 0; 
    my $b3 = 0;        
    foreach (@FomatData) {
      if($ColNum eq '1') {
        if($i == 0) {
	  $b0 = $_;
	  $i++;
	} else {
	if($i == 1) {
	  $b1 = $_;
	  $i++;
	} else {
	if($i == 2) {
	  $b2 = $_;
	  $i++;
	} else {
	  print AF "$_";
	  print AF "$b2";
	  print AF "$b1";
	  print AF "$b0";
	  $i = 0;
	}}}
       }else{
          print AF "$_";
       }
    }
    close (AF);
}

sub hexdump
{
  join ' ', map { sprintf "%02X", $_ } unpack "C*", $_[0];
}

sub usage {
    print STDERR <<EOF;
    
Usage: bin2hex format binfile outfile
     format      format to convert to, 
		 asm ==> 'assembly', 
		 c ==> 'C'
     binfile     binary file you want to convert.
     outfile     output file to store the result of output.
     arr_form    displayed in array-form
     ColNum      num of columns of the shown array

EOF
   exit(-1);
}

