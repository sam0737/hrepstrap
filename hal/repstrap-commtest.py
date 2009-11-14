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
COMM_BAUDRATE = 230400
## Configuration End ##

import sys
from RepRapSerialComm import *

def main(argv=None):
    comm = RepRapSerialComm(port = COMM_PORT, baudrate = COMM_BAUDRATE)

    print "Sleeping for 5 seconds for the serial port and firmware to settle..."
    time.sleep(5)

    print "Flushing communicaton channel..."
    comm.reset()

    
    print "Querying..."
    p = SimplePacket()
    p.add_8(0)
    p.add_8(120)
    p.add_8(150)
    p.add_8(150)
    p.add_8(150)
    p.add_8(150)
    p.add_8(150)
    p.add_8(150)
    comm.send(p)
    start = datetime.now()
    for i in range(10):
        p = SimplePacket()
        p.add_8(0)
        p.add_8(120)
        p.add_8(150)
        p.add_8(150)
        p.add_8(150)
        p.add_8(150)
        p.add_8(150)
        p.add_8(150)
        comm.send(p)
        p = None
        while p == None:
            p = comm.readback()
    duration = (datetime.now() - start) / 10;

    print "Time spent for a two-way packet: " + str(duration)
    print "Readback result code (1 for success, anything else - failure): " + str(p.rc)
    if p.rc == SimplePacket.RC_OK: 
        print "The current temperature is: " + str(p.get_16(4))
        print "The loop-cycle per seconds is (The higher the better, hopefully over 200): " + str(p.get_8(3) * 4)
    for i in range(13):
        print str(p.get_8(i))

if __name__ == "__main__":
    main()
    
