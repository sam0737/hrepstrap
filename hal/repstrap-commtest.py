#!/usr/bin/python
# encoding: utf-8
"""
RepStrap Extruder Communication Test

DESCRIPTION

This script can check the serial port configuration and conduct a basic verification of the firmware communication functionality

Please read the README.html usage.
"""

__author__ = "Saw Wong (sam@hellosam.net)"
__date__ = "2009/11/12"
__license__ = "GPL 3.0"

## Configuration Start ##
# You should change the following variable to reflect your Serial Port setup
COMM_PORT = "/dev/ttyUSB0"
COMM_BAUDRATE = 38400
## Configuration End ##

import sys
from RepRapSerialComm import *

def main(argv=None):
    comm = RepRapSerialComm(port = COMM_PORT, baudrate = COMM_BAUDRATE)

    print "Sleeping for 5 seconds for the serial port and firmware to settle..."
    time.sleep(5)

    print "Flushing communicaton channel..."
    comm.reset()
    
    print "Querying for Heater 1 temperature (Command 91)..."
    p = SimplePacket()
    p.add_8(0)
    p.add_8(91)
    comm.send(p)
    
    print "Reading back the response..."
    p = comm.readback()
    while p == None:
        p = comm.readback()
        
    print "Readback result code (1 for success, anything else - failure): " + str(p.rc)
    if p.rc == SimplePacket.RC_OK: print "The current temperature is: " + str(p.get_16(1))

if __name__ == "__main__":
    main()
    
