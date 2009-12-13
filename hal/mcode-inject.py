#!/usr/bin/python
# encoding: utf-8
"""
RepStrap Extruder MCode Injection

DESCRIPTION

The script should be invoked by EMC2 upon hitting M1xx User M Code. (..TODO...)

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
            
            if mcode == 104:
                _setPin("mux2.0.in0", argv[1])
            elif mcode == 150:                
                sv = _getPin("mux2.0.in0")
                pv = _getPin("rs-extruder.heater1.pv")
                while int(pv) + 2 < int(sv):
                    time.sleep(0.1)
                    sv = _getPin("mux2.0.in0")
                    pv = _getPin("rs-extruder.heater1.pv")        
            
        except Usage ,err:
            print >> sys.stderr, str(err.msg)
            print >> sys.stderr, "\nUsage: " + str(argv[0]) + " ParameterP ParameterQ"
    return 0

def _getPin(pin):
    return Popen("halcmd getp " + str(pin), stdout=PIPE, shell=True).communicate()[0]
    
def _setPin(pin, value):
    Popen("halcmd setp " + str(pin) + " " + str(value), stdout=PIPE, shell=True).communicate()
    
if __name__ == "__main__":
    sys.exit(main())
