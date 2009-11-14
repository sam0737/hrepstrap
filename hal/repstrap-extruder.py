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
* Monitor spindle and other HAL pins, and control the extruder accordingly

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
COMM_BAUDRATE = 38400
## Configuration End ##

class Extruder:
    def __init__(self, hal_component):
        self.c = hal_component            
        self._trigger_dict = {
            'heater1.set-sv': self._trigger_heater1_sv,
            'heater2.set-sv': self._trigger_heater2_sv,
            'motor1.rel-pos.trigger': self._trigger_motor1_rel_pos,
            'motor1.speed.trigger': self._trigger_motor1_speed,
            'motor1.spindle.on': self._trigger_motor1_spindle,
            'motor1.mmcube.trigger': self._trigger_motor1_mmcube,
            'motor1.pwm.r-fast': self._trigger_motor1_pwm,
            'motor1.pwm.r-slow': self._trigger_motor1_pwm,
            'motor1.pwm.f-slow': self._trigger_motor1_pwm,
            'motor1.pwm.f-fast': self._trigger_motor1_pwm,
            'motor1.tuning.trigger': self._trigger_motor1_tuning,
            'mapp.seqid': self._trigger_mapp,
            'running':self._trigger_running
        }
        self._trigger_state = {}
        
        self.comm = None
        self.readback_queue = []

        self.estop_state = 0
        self.enable_state = 0
        
        self.extruder_state = 0;
        self.extruder_ready_check = 0;
        self.mcode_heater1_sv = 0;
        self.mcode_motor1_speed = 0;
    
    def execute(self):    
        """
        Start the main process loop.
        This will return only when error (Communication, Exception, etc) is encountered.
        """
        next_status_read = datetime.now();
        next_temp_read = datetime.now();
        next_motor_read = datetime.now();
        self.readback_queue = []
        self._init_trigger_state()
        
        self.comm = None
        try:            
            self.comm = RepRapSerialComm(port = COMM_PORT, baudrate = COMM_BAUDRATE)
            self.comm.reset()            
            p = self.comm.readback()

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
                            self.c['mapp.done'] = self.c['mapp.seqid']
                            
                            self.comm.reset()
                            self.readback_queue = []
                            
                            # Turn Off
                            p = SimplePacket()
                            p.add_8(0)
                            p.add_8(82)
                            self.comm.send(p)
                            self.readback_queue.append(self._rb_dummy)                        
                        else:
                            self.c['connection'] = 1
                            (self.readback_queue[0])(p)
                            del self.readback_queue[0]
                
                if len(self.readback_queue) > 20:
                    raise SystemExit("The readback queue is too long. Suggesting microcontroller overflow or other bus problem")
                
                # Enable
                if self.enable_state != self.c['enable']:
                    self.enable_state = self.c['enable']
                    p = SimplePacket()
                    p.add_8(0)
                    if self.enable_state:
                        p.add_8(81)
                    else:                    
                        self.extruder_ready_check = 0
                        self.extruder_state = 0
                        self.c['mapp.done'] = self.c['mapp.mcode']
                        p.add_8(82)
                    self.comm.send(p)
                    self.readback_queue.append(self._rb_enable)

                # Check button trigger
                self._check_trigger()
                
                # Read Status
                if datetime.now() > next_status_read:
                    next_status_read = datetime.now() + timedelta(milliseconds = 50);
                    p = SimplePacket()
                    p.add_8(0)
                    p.add_8(80)
                    self.comm.send(p)
                    self.readback_queue.append(self._rb_status)
                    
                # Read Heater PV/SV
                if datetime.now() > next_temp_read:
                    next_temp_read = datetime.now() + timedelta(milliseconds = 250);
                    p = SimplePacket()
                    p.add_8(0)
                    p.add_8(91)
                    self.comm.send(p)
                    self.readback_queue.append(self._rb_heater1_pvsv)
                    p = SimplePacket()
                    p.add_8(0)
                    p.add_8(93)
                    self.comm.send(p)
                    self.readback_queue.append(self._rb_heater2_pvsv)
                    
                # Read Motor PV/SV
                if datetime.now() > next_motor_read:
                    next_motor_read = datetime.now() + timedelta(milliseconds = 50);
                    p = SimplePacket()
                    p.add_8(0)
                    p.add_8(95)
                    self.comm.send(p)
                    self.readback_queue.append(self._rb_motor1_pvsv)

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

    def _init_trigger_state(self):
        """
        Setup the trigger dictionary
        """
        for key in self._trigger_dict.keys():
            self._trigger_state[key] = 0    
    
    def _check_trigger(self):
        """
        Look for any pin changes we are interested in and trigger the handlers
        """
        for key in self._trigger_dict.keys():       
            if self._trigger_state[key] != self.c[key]:
                self._trigger_state[key] = self.c[key]
                self._trigger_dict[key](name = key, value = self._trigger_state[key])
            
    def __del__(self):
        if self.comm != None:
            self.comm.close()
            self.comm = None
            
    def _extruder_ready_poll(self):
        """
        Check if the temperature reached the set value, and signal the motor movement accordingly.
        """
        if self.extruder_ready_check > 0 and self.c['heater1.pv'] >= self.mcode_heater1_sv - 5:
        	if self.extruder_ready_check != 150:
		        p = SimplePacket()
		        p.add_8(0)
		        p.add_8(97)
		        if self.extruder_ready_check == 101:
		            p.add_16(self.mcode_motor1_speed)
		        else:
		            p.add_16(-self.mcode_motor1_speed)
		        self.comm.send(p)
		        self.readback_queue.append(self._rb_dummy) 

		        self.extruder_state = self.extruder_ready_check           
	        self.c['mapp.done'] = self.c['mapp.seqid']
	        self.extruder_ready_check = 0
                             
    def _trigger_heater1_sv(self, name, value):
        p = SimplePacket()
        p.add_8(0)
        p.add_8(92)
        p.add_16(value)
        self.comm.send(p)
        self.readback_queue.append(self._rb_dummy)

    def _trigger_heater2_sv(self, name, value):
        p = SimplePacket()
        p.add_8(0)
        p.add_8(94)
        p.add_16(value)
        self.comm.send(p)
        self.readback_queue.append(self._rb_dummy)

    def _trigger_motor1_rel_pos(self, name, value):
        if not value:
            return
        p = SimplePacket()
        p.add_8(0)
        p.add_8(96)
        p.add_16(self.c['motor1.rel-pos'])
        self.comm.send(p)
        self.readback_queue.append(self._rb_dummy)       
        
    def _trigger_motor1_speed(self, name, value):
        if not value:
            return
        p = SimplePacket()
        p.add_8(0)
        p.add_8(97)
        p.add_16(self.c['motor1.speed'])
        self.comm.send(p)
        self.readback_queue.append(self._rb_dummy)        

    def _trigger_motor1_spindle(self, name, value):        
        if not value:
	        self.mcode_motor1_speed = 0
        else:
	        self.mcode_motor1_speed = int(self.c['motor1.spindle'] * self.c['steps_per_mm_cube'] * 2**8)
        p = SimplePacket()
        p.add_8(0)
        p.add_8(97)
        p.add_16(self.mcode_motor1_speed)
        self.comm.send(p)
        self.readback_queue.append(self._rb_dummy)        
        
    def _trigger_motor1_mmcube(self, name, value):
        if not value:
            return
        p = SimplePacket()
        p.add_8(0)
        p.add_8(97)
        p.add_16(int(self.c['motor1.mmcube'] * self.c['steps_per_mm_cube'] * 2**8))
        self.comm.send(p)
        self.readback_queue.append(self._rb_dummy)        
        
    def _trigger_motor1_pwm(self, name, value):
        p = SimplePacket()
        p.add_8(0)
        p.add_8(98)
        p.add_8(name.find('f-') >= 0)
        if not value:        
            p.add_8(0)
        else:
            if name.find('fast') >= 0:
                p.add_8(192)
            else:
                p.add_8(128)
        self.comm.send(p)
        self.readback_queue.append(self._rb_dummy)
        
    def _trigger_motor1_tuning(self, name, value):
        if not value:
            return
        p = SimplePacket()
        p.add_8(0)
        p.add_8(100)
        if self.c['motor1.tuning.p'] > 0: 
            p.add_16(int(2**abs(self.c['motor1.tuning.p'])))
            pass
        elif self.c['motor1.tuning.p'] < 0:
            p.add_16(-int(2**abs(self.c['motor1.tuning.p'])))
        else:
            p.add_16(0)
            
        
        if self.c['motor1.tuning.i'] > 0: 
            p.add_16(int(2**abs(self.c['motor1.tuning.i'])))
        elif self.c['motor1.tuning.i'] < 0:
            p.add_16(-int(2**abs(self.c['motor1.tuning.i'])))
        else:
            p.add_16(0)
            
        if self.c['motor1.tuning.d'] > 0: 
            p.add_16(int(2**abs(self.c['motor1.tuning.d'])))
        elif self.c['motor1.tuning.d'] < 0:
            p.add_16(-int(2**abs(self.c['motor1.tuning.d'])))
        else:
            p.add_16(0)
            
        if self.c['motor1.tuning.iLimit'] > 0: 
            p.add_16(int(2**abs(self.c['motor1.tuning.iLimit'])))
        elif self.c['motor1.tuning.iLimit'] < 0:
            p.add_16(-int(2**abs(self.c['motor1.tuning.iLimit'])))
        else:
            p.add_16(0)
            
        p.add_8(self.c['motor1.tuning.deadband'])
        p.add_8(self.c['motor1.tuning.minOutput'])
        
        self.comm.send(p)
        self.readback_queue.append(self._rb_dummy)        

    def _mapp_heater1_set_sv(self):
        p = SimplePacket()
        p.add_8(0)
        p.add_8(92)
        p.add_16(self.mcode_heater1_sv)
        self.comm.send(p)
        self.readback_queue.append(self._rb_dummy)

    def _trigger_mapp(self, name, value):
        seqid = value
        mcode = self.c['mapp.mcode']
        if mcode == 101:
            # Extruder Heatup + Forward            
            self._mapp_heater1_set_sv()
            self.extruder_ready_check = mcode
            self._extruder_ready_poll()            
        elif mcode == 102:
            # Extruder Heatup + Reverse
            self._mapp_heater1_set_sv()
            self.extruder_ready_check = mcode
            self._extruder_ready_poll()
        elif mcode == 103:
            # Extruder Heatup + Motor Off
            self._mapp_heater1_set_sv()
            p = SimplePacket()
            p.add_8(0)
            p.add_8(97)
            p.add_8(0)
            p.add_8(0)
            self.comm.send(p)
            self.readback_queue.append(self._rb_dummy)
            self.extruder_state = 0
            
            self.c['mapp.done'] = seqid    
        elif mcode == 104:
            # Set extruder temp
            self.mcode_heater1_sv = int(self.c['mapp.p'])
            self._mapp_heater1_set_sv()
            self.c['mapp.done'] = seqid
            
        # 105: Get temperature: Do nothing
        # 106: TODO FAN ON
        # 107: TODO FAN OFF

        elif mcode == 108:
            # Set future extruder speed
            # Won't take effect until next M101/M102
            self.mcode_motor1_speed = int(self.c['mapp.p'] * self.c['steps_per_mm_cube'] * 2**8);
            self.c['mapp.done'] = seqid
            
        elif mcode == 150:
            # Wait for temperature to reach the set value
            self._mapp_heater1_set_sv()
            self.extruder_ready_check = mcode
            self._extruder_ready_poll()
        
        else:
            # Release all unknown MCode
            self.c['mapp.done'] = seqid
                        
        # self.readback_queue.append(lambda p: _rb_mcode(seqid))
    
    def _trigger_running(self, name, value):
        if not value:
            p = SimplePacket()
            p.add_8(0)
            p.add_8(98) # Use PWM instead of SPEED. PWM=0 frees the motor1. SPEED=0 keeps motor locked at position
            p.add_8(0)
            p.add_8(0)
            self.comm.send(p)
            self.readback_queue.append(self._rb_dummy)
        elif self.extruder_state and self.mcode_motor1_speed != 0:
            self._mapp_heater1_set_sv()
            p = SimplePacket()
            p.add_8(0)
            p.add_8(97)
            if self.extruder_state == 101:
                p.add_16(self.mcode_motor1_speed)
            else:
                p.add_16(-self.mcode_motor1_speed)
            self.comm.send(p)
            self.readback_queue.append(self._rb_dummy)            

    def _rb_mcode(self, p, seqid):
        # Not used yet
        self.c['mapp.done'] = seqid
    
    def _rb_dummy(self, p):
        pass
        
    def _rb_status(self, p):        
        new_estop_state = p.get_8(1) & 1
        if new_estop_state and not self.estop_state:
            self.c['estop'] = 1
        else:
            self.c['estop'] = 0
        self.estop_state = new_estop_state
        
        self.c['online'] = p.get_8(1) & 2
        self.c['fault.thermistor-disc'] = p.get_8(2) != 0
        self.c['fault.heater-response'] = p.get_8(3) != 0
        self.c['fault.motor-jammed'] = p.get_8(4) != 0
        self.c['fault.no-plastic'] = p.get_8(5) != 0

        self.c['heater1.on'] = (p.get_8(6) & 1) != 0
        self.c['heater2.on'] = (p.get_8(6) & 2) != 0
        
    def _rb_enable(self, p):
        self.c['fault.communication'] = 0
        self.estop_state = 0
                    
    def _rb_heater1_pvsv(self, p):
        self.c['heater1.pv'] = p.get_16(1)
        self.c['heater1.sv'] = p.get_16(3)
        self._extruder_ready_poll()

    def _rb_heater2_pvsv(self, p):
        self.c['heater2.pv'] = p.get_16(1)
        self.c['heater2.sv'] = p.get_16(3)
        self._extruder_ready_poll()
        
    def _rb_motor1_pvsv(self, p):
        self.c['motor1.pv'] = p.get_16(1)
        self.c['motor1.sv'] = p.get_16(3)


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

	# TODO: Support PWM driver
	c.newpin("fault.communication", hal.HAL_BIT, hal.HAL_OUT)
	c.newpin("fault.thermistor-disc", hal.HAL_BIT, hal.HAL_OUT)
	c.newpin("fault.heater-response", hal.HAL_BIT, hal.HAL_OUT)
	c.newpin("fault.motor-jammed", hal.HAL_BIT, hal.HAL_OUT)
	c.newpin("fault.no-plastic", hal.HAL_BIT, hal.HAL_OUT)

	c.newpin("heater1.pv", hal.HAL_FLOAT, hal.HAL_OUT)
	c.newpin("heater1.sv", hal.HAL_FLOAT, hal.HAL_OUT)
	c.newpin("heater1.set-sv", hal.HAL_S32, hal.HAL_IN)
	c.newpin("heater1.on", hal.HAL_BIT, hal.HAL_OUT)

	c.newpin("heater2.pv", hal.HAL_FLOAT, hal.HAL_OUT)
	c.newpin("heater2.sv", hal.HAL_FLOAT, hal.HAL_OUT)
	c.newpin("heater2.set-sv", hal.HAL_S32, hal.HAL_IN)
	c.newpin("heater2.on", hal.HAL_BIT, hal.HAL_OUT)

	c.newpin("motor1.pv", hal.HAL_U32, hal.HAL_OUT)
	c.newpin("motor1.sv", hal.HAL_U32, hal.HAL_OUT)
	c.newpin("motor1.rel-pos", hal.HAL_S32, hal.HAL_IN)
	c.newpin("motor1.rel-pos.trigger", hal.HAL_BIT, hal.HAL_IN)
	c.newpin("motor1.speed", hal.HAL_S32, hal.HAL_IN)
	c.newpin("motor1.speed.trigger", hal.HAL_BIT, hal.HAL_IN)
	c.newpin("motor1.mmcube", hal.HAL_FLOAT, hal.HAL_IN)
	c.newpin("motor1.mmcube.trigger", hal.HAL_BIT, hal.HAL_IN)
	c.newpin("motor1.pwm.r-fast", hal.HAL_BIT, hal.HAL_IN)
	c.newpin("motor1.pwm.r-slow", hal.HAL_BIT, hal.HAL_IN)
	c.newpin("motor1.pwm.f-slow", hal.HAL_BIT, hal.HAL_IN)
	c.newpin("motor1.pwm.f-fast", hal.HAL_BIT, hal.HAL_IN)

	c.newpin("motor1.spindle", hal.HAL_FLOAT, hal.HAL_IN)
	c.newpin("motor1.spindle.on", hal.HAL_BIT, hal.HAL_IN)

	c.newpin("motor1.tuning.trigger", hal.HAL_BIT, hal.HAL_IN)
	c.newpin("motor1.tuning.p", hal.HAL_FLOAT, hal.HAL_IN)
	c.newpin("motor1.tuning.i", hal.HAL_FLOAT, hal.HAL_IN)
	c.newpin("motor1.tuning.d", hal.HAL_FLOAT, hal.HAL_IN)
	c.newpin("motor1.tuning.iLimit", hal.HAL_FLOAT, hal.HAL_IN)
	c.newpin("motor1.tuning.deadband", hal.HAL_S32, hal.HAL_IN)
	c.newpin("motor1.tuning.minOutput", hal.HAL_S32, hal.HAL_IN)

	c.newpin("mapp.mcode", hal.HAL_S32, hal.HAL_IN)
	c.newpin("mapp.p", hal.HAL_FLOAT, hal.HAL_IN)
	c.newpin("mapp.q", hal.HAL_FLOAT, hal.HAL_IN)
	c.newpin("mapp.seqid", hal.HAL_S32, hal.HAL_IN)
	c.newpin("mapp.done", hal.HAL_S32, hal.HAL_OUT)

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
		        c['mapp.done'] = c['mapp.seqid']
		        time.sleep(0.05)
		        
	except KeyboardInterrupt:
		raise SystemExit    

if __name__ == "__main__":
	main()
