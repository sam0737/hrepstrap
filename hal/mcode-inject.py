#!/usr/bin/python
# encoding: utf-8
"""
RepStrap Extruder MCode Injection

DESCRIPTION

The script should be invoked by EMC2 upon hitting M1xx User M Code. This will inject corresponding value to HAL pin and so that the repstrap-extruder driver could pick up.

Please read the README.html usage.
"""

__author__ = "Saw Wong (sam@hellosam.net)"
__date__ = "2009/11/12"
__license__ = "GPL 3.0"

import sys
import re
import time
from subprocess import *

class Usage(Exception):
    """
    Represents an exception about improper usage of this script
    """
    def __init__(self, msg):
        self.msg = msg

# List of M Code that requires sych, blocking operation
blocking_mcodes = {
    101: 1, # Extruder on
    150: 1  # Wait for set temperature
}

def main(argv=None):
    if argv is None:
        argv = sys.argv
        
        try:
            # Parameter parsing
            if len(argv) != 3:
                raise Usage("Incorrect number of arguments")  
            
            # MCode parsing
            m = re.search('M(\d+)$', argv[0])
            if m == None:
                raise Usage("MCode is not parsed. We expected the program name to be M1xx. It could be soft-linked to one executable though.")
            
            mcode = int(m.group(1))
            if mcode < 100 or mcode > 200:
                raise Usage("Unexpected MCode")
            if not re.match('^[-+]?\d*(\.\d*)?$', argv[1]):
                raise Usage("The parameter P is not a float number: " + argv[1])                
            if not re.match('^[-+]?\d*(\.\d*)?$', argv[2]):
                raise Usage("The parameter Q is not a float number: " + argv[2])
            
            # If the previous MCode was not finished, wait!
            seqid = int(getPin("rs-extruder.mapp.seqid"))
            done = int(getPin("rs-extruder.mapp.done"))
            
            while seqid != done:
                done = int(getPin("rs-extruder.mapp.done"))
                time.sleep(0.005)
            
            # New sequence ID, and then set the parameters
            seqid += 1
            if seqid > 10000:
                seqid = 0            
            setPin("rs-extruder.mapp.mcode", mcode)
            setPin("rs-extruder.mapp.p", argv[1])
            setPin("rs-extruder.mapp.q", argv[2])
            setPin("rs-extruder.mapp.seqid", seqid)
            
            # If this is a blocking mcode, wait!
            if mcode in blocking_mcodes:
                while True:
                    done = int(getPin("rs-extruder.mapp.done"))
                    if done == seqid:
                        break
                    time.sleep(0.005)
            # if mcode == 101:
            #     time.sleep(0.2)
            
        except Usage ,err:
            print >> sys.stderr, str(err.msg)
            print >> sys.stderr, "\nUsage: " + str(argv[0]) + " ParameterP ParameterQ"
    return 0

def getPin(pin):
    return Popen("halcmd getp " + str(pin), stdout=PIPE, shell=True).communicate()[0]
    
def setPin(pin, value):
    Popen("halcmd setp " + str(pin) + " " + str(value), stdout=PIPE, shell=True).communicate()
    
if __name__ == "__main__":
    sys.exit(main())
