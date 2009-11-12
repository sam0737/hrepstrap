=head1 NAME

README - Scripts and instructions for running EMC2 based RepStrap

=head1 DESCRIPTION

This package helps you to build a Linux EMC2 based RepStrap machine (Non standard RepRap machine, useful for bootstrapping a RepRap).

If you have a desktop milling machine controlled by EMC2 or Mach3 already, with some hardware modification, specifically adding the plastic extruder print head, it would be mechanical capable in printing 3D plastic model. This package serves as a guide to your integration.

The package comes with two big components:

=over

=item 1.

An Amtel AVR firmware, to be compiled with Arduino (L<http://www.arduino.cc>), which is designed for the following hardware combinations:

=over

=item *

the RepRap's Extruder Controller 2.2 (L<http://reprap.org/bin/view/MainExtruder_Controller_2_2>)

=item *

DC Motor and Magnetic Rotary Encoder (L<http://reprap.org/bin/view/Main/Magnetic_Rotary_Encoder_1_0>) as extrusion driver, with software PID loop implemented.

=item *

Thermocouple or Thermistor for temperature reading

=item *

Resistive heating element driven by MOSFET

=back

The program architecture is also flexible enough to extend the support to stepper motor (Patch is welcome!), as well as a different motherboard design.

=item 2.

EMC2 Integration. A set of scripts allows communication to happen between the EMC2 and the firmware mentioned above. As long as the communication protcol is compatible, this set of scripts are still useful even if it's not the same firmware. The protocol is developed based on the RepRap 3rd Gen Electronics internal communication protocol.

A few more scripts included for adopting Skeinforge GCode output. Skeinforge is one of the primary tool to generate RepRap usable GCode from STL and other 3D format.

=back


=head1 File Layout

=over

=item C</ExtruderController>

An AVR firmware for the Extruder Controller 2.2 (L<http://reprap.org/bin/view/MainExtruder_Controller_2_2>).

=item C</hal>

EMC2 integration scripts

=over

=item C<mcode-inject.py>

A script being invoked by EMC2 when M1xx User M-Code is being executed. It notifies the driver through HAL.

=item C<RepRapSerialComm.py>

A module to enable serial port communication with the RepRap/RepStrap extruder controller.

=item C<repstrap-commtest.py>

A test script to verify the communication and hardware correctness.

=item C<repstrap-extruder.hal>

A HAL script to be included in the EMC2 setup.

=item C<repstrap-extruder.py>

A user space driver to control and communicate with the RepStrap extruder controller.

=item C<repstrap-extruder.pyvcp>

A PYVCP gadget for EMC2's AXIS UI allowing control of the extruder and reporting its status.

=item C<skeinforge2emc.pl>

A filter program to convert Skeinforge GCode output to a more EMC2 friendly input.

=item C<softlink-mcode-inject.sh>

simple shell script to create necessary soft-link to accept M1xx M-Code.

=back

=item C</README>

The documents of the scripts and everything.

=back

=head1 SETUP GUIDE

=head2 Firmware

A firmware should comes with the package. Now config your hardware in the C<Hardware.h>, then compile and burn the firmware with Arduino (L<http://www.arduino.cc/>).

    TODO: Documentation for this section is to be completed

=head2 EMC2 Setup

=over

=item 1. 

Put all these scripts and files in one folder, say, your home folder. The location is assume to be C</script/folder> in the following document.

Make sure all the scripts are excutable:

    chmod a+x *.pl *.py *.sh

=item 2. 

Edit your EMC2's machine ini (usually in C<~/emc2/config/your-machine/your-machine.ini>) to include the following lines:

    [AXIS]
    ...    
    PROGRAM_PREFIX = /script/folder
    PYVCP = /script/folder/repstrap-extruder.pyvcp
    
    [FILTER]
    PROGRAM_EXTENSION = .skf Skeinforge Output
    skf = /script/folder/skeinforge2emc.pl

There should also be a C<POSTGUI_HALFILE> in the C<[HAL]> section. If not, create one:

    [HAL]
    ...
    POSTGUI_HALFILE = custom_postgui.hal

=item 3.

Now include the HAL file by editing C<custom_postgui.hal>, or create one if it does not exist, and put the following lines into it:

    source /script/folder/repstrap-extruder.hal

=item 4.

Edit the C<repstrap-extruder.hal> file.

Modify the path that points to C<repstrap-extruder.pyvcp> as you see fit. We will come back and modify C<steps_per_mm_cube> later.

=item 5.

Edit the C<repstrap-commtest.py> and C<repstrap-extruder.py>. 
Make any correction to the C<COMM_PORT> and C<COMM_BAUDRATE> so to reflect your machine setup. 
Specifically, the device of your serial port which is hooked to the Extruder Controller.

Usually, the C<COMM_BAUDRATE> value needs not to be modified.

Then invoke the C<repstrap-commtest.py> in your consle to see if the communication works. It should print something like this:

    Sleeping for 5 seconds for the serial port and firmware to settle...
    Flushing communicaton channel...
    Querying for Heater 1 temperature (Command 91)...
    Reading back the response...
    Readback result code (1 for success, anything else - failure): 1
    The current temperature is: 19

=item 6.

Execute C<softlink-mcode-inject.sh> to have the softlinks needed created.

=item 7.

Fire up the EMC. Now hopefully you can see a green icon for the Connection LED.

Play around with the Heater and Motor setup. The motor E<gt>E<gt> button should push the filament into the extruder. If the direction is wrong, you have to correct it in the firmware.

For PID controlled DC Motor, you might also experiement with the PID settings and put it back to the firmware when you are done.

=item 8.

Now calibrate the C<steps_per_mm_cube> settings. The value is used for commanding the motor speed in response to the flowrate needed.

You need to know how many steps there are when spinning your extruder motor axis for one cycle. This should be a number related to the encoder count, or stepper number of steps and gear ratio. You should also know how many teeth are there on your axis. Last but not least, please have the thickness of your filament ready. (Measure it! it usually have variation of ~0.1mm)

Now feed a filament into the gear, use position control mode to feed the filament for a cycle or two. Please note that you should either heat up the extruder and be ready to melt the plastic, or don't push too far into it or you might break your setup.

Reverse feed the filament and pull that out, and by measuring the teeth mark on the filament, figure out the length of filament fed for spinning the motor for one cycle.

Open C<repstrap-extruder.hal> and feed all these parameters into the equation and you will get the C<steps_per_mm_cube> value you needed.

=item 9.

To have the new configuration loaded, you must restart the EMC2 Axis.

=back

=head2 Skienforge Configuration

Besides the normal configuration that you must go through, like C<Carve> and C<Speed>, you must also configure the following

=over

=item 1.

In the C<Export Preferences>, turn off C<Delete Comments>. Set C<File Extension> to be C<skf>.

=item 2.

In the C<Speed Preferences>, turn on C<Add Flow Rate>. The C<Flow Rate Setting> is calculated as:

    Flow Rate Setting = Math.PI * (Extrusion Diameter over Thickness * Carve's Layer Thickness)^2 / 4 * Feedrate

=back

=head2 Try that out!

Now you should be able to print something.

=over

=item 1.

Carve a STL file by Skienforge.

=item 2.

Fire up EMC2's AXIS, open the C<SKF> result file.

=item 3.

Set zero for your print head. And Hit Run!

=back

=head1 REFERENCES

=over

=item * L<http://github.com/sam0737/hrepstrap>

This package!

=item * L<http://reprap.org>

RepRap

=item * L<http://linuxcnc.org>

Linux EMC2

=item * L<http://www.arduino.cc>

Arduino Atmel AVR IDE

=item * L<http://objects.reprap.org/wiki/Builders/EMCRepStrap>

EMC2 Based RepStrap Wiki

=item * L<http://bitsfrombytes.com/wiki/index.php?title=Skeinforge>

Skeinforge Wiki

=item * L<http://objects.reprap.org/wiki/Minimug>

Traditionally the first thing to be printed, and you will need this to celebrate your successful print.

=back

=head1 TODO

=over

=item * 

Leverage EMC2 ability to control the motor. Maybe we need a faster communication channel first. AVR USB?

=item *

Coordinate the extrusion speed with axis acceleration and speed.

=back

=head1 LICENSE

GPL 3.0

=head1 AUTHOR

Sam Wong (sam@hellosam.net)

