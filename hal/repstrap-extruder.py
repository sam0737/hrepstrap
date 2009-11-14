#!/usr/bin/python
# encoding: utf-8
"""
RepStrap Extruder EMC2 Userspace Driver

INTRODUCTION

This is an user-space driver for EMC2 RepStrap setup, specifically handling the communication between the EMC2 and the RepStrap extruder controller through serial port.

It is designed to work with the AVR firmware comes with this software, but not the official RepRap firmware.

The program needs proper configuration to be useful, including HAL setup and some hardware specific parameters.

Please read the README.html for setup and usage.

DESCRIPTION

The user-space driver does the followings:
* Maintain communication channel with the extruder hardware
* Setup HAL pins for communication with EMC2
* Reading status from the extruder hardware periodically, report to HAL pins
* Monitor the HAL pins, and control the extruder accordingly

These are achieved through a polling loop.

For a complete system design diagram, please read the README.html.
"""

import sys
import hal
import math
from datetime import datetime, timedelta 
from RepRapSerialComm import *

__author__ = "Saw Wong (sam@hellosam.net)"
__date__ = "2009/11/12"
__license__ = "GPL 3.0"

## Configuration Start ##
# You should change the following variable to reflect your Serial Port setup
COMM_PORT = "/dev/ttyUSB0"
COMM_BAUDRATE = 230400
## Configuration End ##

class Extruder:
    def __init__(self, hal_component):
        self.c = hal_component            
        
        self.comm = None
        self.readback_queue = []

        self.estop_state = 0
    
    def execute(self):    
        """
        Start the main process loop.
        This will return only when error (Communication, Exception, etc) is encountered.
        """

        next_packet = datetime.now();
        next_diag = datetime.now();
        cycle_count = 0;
        cycle_count_acc = 0;
        self.readback_queue = []
        
        self.comm = None
        try:            
            self.comm = RepRapSerialComm(port = COMM_PORT, baudrate = COMM_BAUDRATE)
            self.comm.reset()            
            p = self.comm.readback()


            pInit = SimplePacket()
            pInit.add_8(0)
            pInit.add_8(120)
            pInit.add_8(0)
            pInit.add_8(0)
            pInit.add_8(0)
            pInit.add_8(0)
            pInit.add_8(0)
            pInit.add_8(0)

            while True:
                time.sleep(0.005)

                # Process any packets
                if len(self.readback_queue) > 0:
                    p = self.comm.readback()
                    if p != None:
                        if p.rc != SimplePacket.RC_OK:                        
                            print >> sys.stderr, "Extruder communication error: RC: %d" % (p.rc)
                            self.c['fault.communication'] = 1
                            self.c['connection'] = 0
                            self.c['estop'] = 1
                            self.c['online'] = 0     
                            self.extruder_ready_check = 0
                            self.extruder_state = 0
                            
                            self.comm.reset()
                            self.readback_queue = []
                            
                            # Turn Off
                            self.comm.send(pInit)
                            self.readback_queue.append(self._readback)                        
                        else:
                            self.c['connection'] = 1
                            (self.readback_queue[0])(p)
                            del self.readback_queue[0]
                
                if len(self.readback_queue) > 20:
                    raise SystemExit("The readback queue is too long. Suggesting microcontroller overflow or other bus problem")

                if datetime.now() > next_diag:
                    next_diag = next_diag + timedelta(seconds = 1)
                    c['diag.driver-cycle-count'] = cycle_count_acc;
                    cycle_count_acc = 0

                cycle_count_acc += 1

                if datetime.now() > next_packet:
                    next_packet = next_packet + timedelta(milliseconds = 7)

                    p = SimplePacket()
                    heater1_pwm = c['heater1.pwm']
                    heater2_pwm = c['heater2.pwm']
                    motor1_pwm = c['motor1.pwm']
                    p.add_8(0)
                    p.add_8(120)
                    p.add_8(self.c['enable'])
                    p.add_8(min(0, max(heater1_pwm, 255)))
                    p.add_8(abs(max(0, min(heater1_pwm, -255))))
                    p.add_8(min(0, max(heater1_pwm, 255)))
                    p.add_8(abs(max(0, min(heater2_pwm, -255))))
                    p.add_8(motor1_pwm >= 0)
                    p.add_8(min(0, max(abs(motor1_pwm), 255)))
                    self.comm.send(p)
                    self.readback_queue.append(self._readback)

        except KeyboardInterrupt:    
            if self.comm != None:
                p = SimplePacket()
                p.add_8(0)
                p.add_8(82)
                self.comm.send(p)
                self.comm.readback()
                raise SystemExit
        finally:
            if self.comm != None:
                self.comm.close()
                self.comm = None
            
    def __del__(self):
        if self.comm != None:
            self.comm.close()
            self.comm = None
        
    def _readback(self, p):        
        new_estop_state = p.get_8(1) & 1
        if new_estop_state and not self.estop_state:
            self.c['estop'] = 1
        else:
            self.c['estop'] = 0
        self.estop_state = new_estop_state
        
        self.c['online'] = p.get_8(1) & 2
        self.c['fault.thermistor-disc'] = p.get_8(2) & 15 != 0
        self.c['fault.heater-response'] = p.get_8(2) & 240 != 0
        self.c['diag.firmware-cycle-count'] = p.get_8(3) * 4

        self.c['heater1.pv'] = p.get_16(4)
        self.c['heater2.pv'] = p.get_16(6)
        self.c['motor1.pv'] = p.get_16(8)
        
def main():
	"""
	Program entry point. Setting up HAL pins and construct the Extruder instance.
	"""
	c = hal.component("rs-extruder")
	c.newpin("connection", hal.HAL_BIT, hal.HAL_OUT)
	c.newpin("online", hal.HAL_BIT, hal.HAL_OUT)
	c.newpin("estop", hal.HAL_BIT, hal.HAL_OUT)
	c.newpin("enable", hal.HAL_BIT, hal.HAL_IN)
	c.newpin("running", hal.HAL_BIT, hal.HAL_IN)

	c.newparam("steps_per_mm_cube", hal.HAL_FLOAT, hal.HAL_RW)
	c['steps_per_mm_cube'] = 4.0 # Some random default. Don't rely on this.

	c.newpin("fault.communication", hal.HAL_BIT, hal.HAL_OUT)
	c.newpin("fault.thermistor-disc", hal.HAL_BIT, hal.HAL_OUT)
	c.newpin("fault.heater-response", hal.HAL_BIT, hal.HAL_OUT)
	c.newpin("diag.firmware-cycle-count", hal.HAL_U32, hal.HAL_OUT)
	c.newpin("diag.driver-cycle-count", hal.HAL_U32, hal.HAL_OUT)

	c.newpin("heater1.pv", hal.HAL_FLOAT, hal.HAL_OUT)
	c.newpin("heater1.pwm", hal.HAL_S32, hal.HAL_IN)
	c.newpin("heater2.pv", hal.HAL_FLOAT, hal.HAL_OUT)
	c.newpin("heater2.pwm", hal.HAL_S32, hal.HAL_IN)

	c.newpin("motor1.pv", hal.HAL_FLOAT, hal.HAL_OUT)
	c.newpin("motor1.pwm", hal.HAL_S32, hal.HAL_IN)

	c.ready()

	extruder = Extruder(c)
	try:
		while True:
		    try:
		        extruder.execute()
		    except IOError:
		        pass
		    except OSError:
		        pass
		    except  serial.serialutil.SerialException:
		        pass
		    finally:
		        c['connection'] = 0
		        c['fault.communication'] = 1
		        c['estop'] = 1
		        c['online'] = 0
		        time.sleep(0.05)
		        c['estop'] = 0
		        time.sleep(0.05)
		        
	except KeyboardInterrupt:
		raise SystemExit    

if __name__ == "__main__":
	main()
