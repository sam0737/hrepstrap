#!/usr/bin/perl

my $temp_enforced = 0;
my $extruder_status = 0;
while(<>) 
{
	next if /\(\<bridgeRotation/;
	if (/^M(\d+)(?:\s+S([0-9\.]+))?(.*?)$/ && $1 >= 100 && $1 < 200)
	{
		if ($1 eq '104')
		{
			$temp_enforced = 0;
		}
		
		if ($1 eq '108')
		{
			# Set extrusion speed
			print "S$2\n";
		} elsif ($1 eq '101')
		{
			# Extrusion on
			if (!$temp_enforced)
			{
				$temp_enforced = 1;
				print "M150\n";
			}
			print "M3\n";
			$extruder_status = 1;
		} elsif ($1 eq '103')
		{
			# Extrusion off
			print "M5\n";
			$extruder_status = 0;
		} else
		{
			print "M$1 P$2$3\n";
		}
	} elsif (/^\(\<layer\>/)
	{
		$temp_enforced = 1;
		print;
		if (!$extruder_status)
		{
			print "M150\n";
		}
	} else
	{
		print;
	}
}
