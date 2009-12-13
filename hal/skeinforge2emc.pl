#!/usr/bin/perl
my $temp_enforced = 0;
my $extruder_status = 0;
my $extruder_speed = 0;

my $comment_found = 0;
my $last_u = 0;
my @last_pos = (0, 0);

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
			$extruder_speed = $2;
		} elsif ($1 eq '101')
		{
			# Extrusion on
			if (!$temp_enforced)
			{
				$temp_enforced = 1;
				print "M150\n";
			}
			$extruder_status = 1;
			print "(Extruder On)\n";
		} elsif ($1 eq '103')
		{
			# Extrusion off
			$extruder_status = 0;
			print "(Extruder Off)\n";
		} else
		{
			print "M$1 P$2$3\n";
		}
	} elsif (/^(G[01]\s+X([0-9.-]+)\s+Y([0-9.-]+))\s+(.*F([0-9.]+).*)$/)
	{
	    if ($extruder_status)
	    {
	        my $dx = $2 - $last_pos[0];
	        my $dy = $3 - $last_pos[1];
	        my $dist = sqrt($dx*$dx+$dy*$dy);
	        my $u = $dist * 60 / $5 * $extruder_speed + $last_u;
	        print "$1 U$u $4\n";
	        $last_u = $u;
	    } else
	    {
    	    print;
	    }
	    @last_pos = ($2, $3);
	} elsif (/^\(\<layer\>/)
	{
        $comment_found = 1;
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

die 
qq{The input does not contain any comment.
Currently this script relies on the comment for correct operation.

Please turn off the "Delete Comments" option in the "Export Preferences"
of Skeinforge, recraft your model and try again.
} unless $comment_found;

=head1 NAME

Skeinforge2EMC - Converts Skeinforge GCode output to EMC2 friendly input for a EMC2/RepStrap setup.

=head1 DESCRIPTION

Input and Output are from STDIN and to STDOUT respectively.

=head2 Usage - Configuration in EMC2

One can use [FILTER], PROGRAM_EXTENSION in the EMC2 so an Skeinforge GCode 
opened can be filter by this script automatically.

In the configuration file (ended with .ini), insert the following lines:

    [FILTER]
    PROGRAM_EXTENSION = .skf Skeinforge Output
    skf = /full/path/to/skeinforge2emc.pl

Then, any file with .skf will be assumed to be Skeinforge output, and will be loaded through this perl filter.

See L<http://linuxcnc.org/docs/2.3/html/config_ini_config.html#sub:[FILTER]-Section> for more.

=head2 Functional description

Currently the filter does the following:

=over

=item 1.

Transforming all C<M1xx> user M code to use C<P> as parameter keyword, replacing the C<S>.

=item 2.

Convert C<M101> (Extruder on), C<M103> (Extruder off), C<M108> (Set extruder speed) to 
corresponding spindle M code. (C<M3>, C<M4> and C<M5>)

=item 3.

Removing the (bridgeRotation) comment line, as the nested bracket will upset EMC2 parser.

=back

=head1 AUTHOR

Sam Wong (sam@hellosam.net)


