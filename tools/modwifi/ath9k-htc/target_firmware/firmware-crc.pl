#!/usr/bin/env perl
use strict;
my $crc = 0;
my $bytes;
my $buf;
while (($bytes = read(STDIN, $buf, 4)) == 4) {
	print $buf;
	my $v = unpack("N", $buf);
	$crc = $crc ^ $v;
}
print pack("N", $crc);
