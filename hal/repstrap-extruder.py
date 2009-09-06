#!/usr/bin/python
# encoding: utf-8
"""
Created by Sam Wong on 2009-08-30.
Copyright (c) 2009 Sam Wong. All rights reserved.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
 
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
 
You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 
"""

import sys
import hal
import math
from datetime import datetime, timedelta 
from RepRapSerialComm import *

c = hal.component("repstrap-extruder")
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

c.newpin("heater.pv", hal.HAL_FLOAT, hal.HAL_OUT)
c.newpin("heater.sv", hal.HAL_FLOAT, hal.HAL_OUT)
c.newpin("heater.set-sv", hal.HAL_S32, hal.HAL_IN)
c.newpin("heater.on", hal.HAL_BIT, hal.HAL_OUT)

c.newpin("motor.pv", hal.HAL_U32, hal.HAL_OUT)
c.newpin("motor.sv", hal.HAL_U32, hal.HAL_OUT)
c.newpin("motor.rel-pos", hal.HAL_S32, hal.HAL_IN)
c.newpin("motor.rel-pos.trigger", hal.HAL_BIT, hal.HAL_IN)
c.newpin("motor.speed", hal.HAL_S32, hal.HAL_IN)
c.newpin("motor.speed.trigger", hal.HAL_BIT, hal.HAL_IN)
c.newpin("motor.mmcube", hal.HAL_FLOAT, hal.HAL_IN)
c.newpin("motor.mmcube.trigger", hal.HAL_BIT, hal.HAL_IN)
c.newpin("motor.pwm.r-fast", hal.HAL_BIT, hal.HAL_IN)
c.newpin("motor.pwm.r-slow", hal.HAL_BIT, hal.HAL_IN)
c.newpin("motor.pwm.f-slow", hal.HAL_BIT, hal.HAL_IN)
c.newpin("motor.pwm.f-fast", hal.HAL_BIT, hal.HAL_IN)

c.newpin("motor.tuning.trigger", hal.HAL_BIT, hal.HAL_IN)
c.newpin("motor.tuning.p", hal.HAL_FLOAT, hal.HAL_IN)
c.newpin("motor.tuning.i", hal.HAL_FLOAT, hal.HAL_IN)
c.newpin("motor.tuning.d", hal.HAL_FLOAT, hal.HAL_IN)
c.newpin("motor.tuning.iLimit", hal.HAL_FLOAT, hal.HAL_IN)
c.newpin("motor.tuning.deadband", hal.HAL_S32, hal.HAL_IN)
c.newpin("motor.tuning.minOutput", hal.HAL_S32, hal.HAL_IN)

c.newpin("mapp.mcode", hal.HAL_S32, hal.HAL_IN)
c.newpin("mapp.p", hal.HAL_FLOAT, hal.HAL_IN)
c.newpin("mapp.q", hal.HAL_FLOAT, hal.HAL_IN)
c.newpin("mapp.seqid", hal.HAL_S32, hal.HAL_IN)
c.newpin("mapp.done", hal.HAL_S32, hal.HAL_OUT)

c.ready()

class Extruder:
    def __init__(self, hal_component):
        self.c = hal_component            
        self.trigger_dict = {
            'heater.set-sv': self.trigger_heater_sv,
            'motor.rel-pos.trigger': self.trigger_motor_rel_pos,
            'motor.speed.trigger': self.trigger_motor_speed,
            'motor.mmcube.trigger': self.trigger_motor_mmcube,
            'motor.pwm.r-fast': self.trigger_motor_pwm,
            'motor.pwm.r-slow': self.trigger_motor_pwm,
            'motor.pwm.f-slow': self.trigger_motor_pwm,
            'motor.pwm.f-fast': self.trigger_motor_pwm,
            'motor.tuning.trigger': self.trigger_motor_tuning,
            'mapp.seqid': self.trigger_mapp,
            'running':self.trigger_running
        }
        self.trigger_state = {}
        
        self.comm = None
        self.readback_queue = []

        self.estop_state = 0
        self.enable_state = 0
        
        self.extruder_state = 0;
        self.extruder_ready_check = 0;
        self.mcode_heater_sv = 0;
        self.mcode_motor_speed = 0;
    
    def execute(self):    
        next_status_read = datetime.now();
        next_temp_read = datetime.now();
        next_motor_read = datetime.now();
        self.readback_queue = []
        self.init_trigger_state()
        
        self.comm = None
        try:
            self.comm = RepRapSerialComm()
            self.comm.reset()            
            p = self.comm.readback()

            while True:
                time.sleep(0.01)

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
                            self.readback_queue.append(self.rb_dummy)                        
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
                    self.readback_queue.append(self.rb_enable)

                # Check button trigger
                self.check_trigger()
                
                # Read Status
                if datetime.now() > next_status_read:
                    next_status_read = datetime.now() + timedelta(milliseconds = 50);
                    p = SimplePacket()
                    p.add_8(0)
                    p.add_8(80)
                    self.comm.send(p)
                    self.readback_queue.append(self.rb_status)
                    
                # Read Heater PV/SV
                if datetime.now() > next_temp_read:
                    next_temp_read = datetime.now() + timedelta(milliseconds = 250);
                    p = SimplePacket()
                    p.add_8(0)
                    p.add_8(91)
                    self.comm.send(p)
                    self.readback_queue.append(self.rb_heater_pvsv)
                    
                # Read Motor PV/SV
                if datetime.now() > next_motor_read:
                    next_motor_read = datetime.now() + timedelta(milliseconds = 50);
                    p = SimplePacket()
                    p.add_8(0)
                    p.add_8(95)
                    self.comm.send(p)
                    self.readback_queue.append(self.rb_motor_pvsv)

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

    def init_trigger_state(self):
        for key in self.trigger_dict.keys():
            self.trigger_state[key] = 0    
    
    def check_trigger(self):
        for key in self.trigger_dict.keys():       
            if self.trigger_state[key] != self.c[key]:
                self.trigger_state[key] = self.c[key]
                self.trigger_dict[key](name = key, value = self.trigger_state[key])
            
    def __del__(self):
        if self.comm != None:
            self.comm.close()
            self.comm = None
            
    def extruder_ready_poll(self):
        if self.extruder_ready_check > 0 and self.c['heater.pv'] >= self.mcode_heater_sv:
            p = SimplePacket()
            p.add_8(0)
            p.add_8(97)
            if self.extruder_ready_check == 101:
                p.add_16(self.mcode_motor_speed)
            else:
                p.add_16(-self.mcode_motor_speed)
            self.comm.send(p)
            self.readback_queue.append(self.rb_dummy)            
            self.c['mapp.done'] = self.c['mapp.seqid']

            self.extruder_state = self.extruder_ready_check
            self.extruder_ready_check = 0
                             
    def trigger_heater_sv(self, name, value):
        p = SimplePacket()
        p.add_8(0)
        p.add_8(92)
        p.add_16(value)
        self.comm.send(p)
        self.readback_queue.append(self.rb_dummy)

    def trigger_motor_rel_pos(self, name, value):
        if not value:
            return
        p = SimplePacket()
        p.add_8(0)
        p.add_8(96)
        p.add_16(self.c['motor.rel-pos'])
        self.comm.send(p)
        self.readback_queue.append(self.rb_dummy)       
        
    def trigger_motor_speed(self, name, value):
        if not value:
            return
        p = SimplePacket()
        p.add_8(0)
        p.add_8(97)
        p.add_16(self.c['motor.speed'])
        self.comm.send(p)
        self.readback_queue.append(self.rb_dummy)        

    def trigger_motor_mmcube(self, name, value):
        if not value:
            return
        p = SimplePacket()
        p.add_8(0)
        p.add_8(97)
        p.add_16(int(self.c['motor.mmcube'] * self.c['steps_per_mm_cube'] * 2**8))
        self.comm.send(p)
        self.readback_queue.append(self.rb_dummy)        
        
    def trigger_motor_pwm(self, name, value):
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
        self.readback_queue.append(self.rb_dummy)
        
    def trigger_motor_tuning(self, name, value):
        if not value:
            return
        p = SimplePacket()
        p.add_8(0)
        p.add_8(100)
        if self.c['motor.tuning.p'] > 0: 
            p.add_16(int(2**abs(self.c['motor.tuning.p'])))
            pass
        elif self.c['motor.tuning.p'] < 0:
            p.add_16(-int(2**abs(self.c['motor.tuning.p'])))
        else:
            p.add_16(0)
            
        
        if self.c['motor.tuning.i'] > 0: 
            p.add_16(int(2**abs(self.c['motor.tuning.i'])))
        elif self.c['motor.tuning.i'] < 0:
            p.add_16(-int(2**abs(self.c['motor.tuning.i'])))
        else:
            p.add_16(0)
            
        if self.c['motor.tuning.d'] > 0: 
            p.add_16(int(2**abs(self.c['motor.tuning.d'])))
        elif self.c['motor.tuning.d'] < 0:
            p.add_16(-int(2**abs(self.c['motor.tuning.d'])))
        else:
            p.add_16(0)
            
        if self.c['motor.tuning.iLimit'] > 0: 
            p.add_16(int(2**abs(self.c['motor.tuning.iLimit'])))
        elif self.c['motor.tuning.iLimit'] < 0:
            p.add_16(-int(2**abs(self.c['motor.tuning.iLimit'])))
        else:
            p.add_16(0)
            
        p.add_8(self.c['motor.tuning.deadband'])
        p.add_8(self.c['motor.tuning.minOutput'])
        
        self.comm.send(p)
        self.readback_queue.append(self.rb_dummy)        

    def mapp_heater_set_sv(self):
        self.mcode_heater_sv = int(self.c['mapp.p'])
        p = SimplePacket()
        p.add_8(0)
        p.add_8(92)
        p.add_16(self.mcode_heater_sv)
        self.comm.send(p)
        self.readback_queue.append(self.rb_dummy)

    def trigger_mapp(self, name, value):
        seqid = value
        mcode = c['mapp.mcode']
        if mcode == 101:
            # Extruder Heatup + Forward            
            self.mapp_heater_set_sv()
            self.extruder_ready_check = mcode
            self.extruder_ready_poll()            
        elif mcode == 102:
            # Extruder Heatup + Reverse
            self.mapp_heater_set_sv()
            self.extruder_ready_check = mcode
            self.extruder_ready_poll()            
        elif mcode == 103:
            # Extruder Heatup + Motor Off
            self.mapp_heater_set_sv()
            p = SimplePacket()
            p.add_8(0)
            p.add_8(98) # Use PWM instead of SPEED. PWM=0 frees the motor. SPEED=0 keeps motor locked at position
            p.add_8(0)
            p.add_8(0)
            self.comm.send(p)
            self.readback_queue.append(self.rb_dummy)
            self.extruder_state = 0
            
            c['mapp.done'] = seqid    
        elif mcode == 104:
            # Set extruder temp
            self.mcode_heater_sv = int(self.c['mapp.p'])
            self.mapp_heater_set_sv()
            c['mapp.done'] = seqid
            
        # 105: Get temperature: Do nothing
        # 106: TODO FAN ON
        # 107: TODO FAN OFF

        elif mcode == 108:
            # Set future extruder speed
            # Won't take effect until next M101/M102
            self.mcode_motor_speed = int(self.c['mapp.p'] * self.c['steps_per_mm_cube'] * 2**8);
            c['mapp.done'] = seqid
        else:
            # Release all unknown MCode
            c['mapp.done'] = seqid
                        
        # self.readback_queue.append(lambda p: rb_mcode(seqid))
    
    def trigger_running(self, name, value):
        if not value:
            p = SimplePacket()
            p.add_8(0)
            p.add_8(98) # Use PWM instead of SPEED. PWM=0 frees the motor. SPEED=0 keeps motor locked at position
            p.add_8(0)
            p.add_8(0)
            self.comm.send(p)
            self.readback_queue.append(self.rb_dummy)
        elif self.extruder_state and self.mcode_motor_speed != 0:
            self.mapp_heater_set_sv()
            p = SimplePacket()
            p.add_8(0)
            p.add_8(97)
            if self.extruder_state == 101:
                p.add_16(self.mcode_motor_speed)
            else:
                p.add_16(-self.mcode_motor_speed)
            self.comm.send(p)
            self.readback_queue.append(self.rb_dummy)            

    def rb_mcode(self, p, seqid):
        # Not used yet
        c['mapp.done'] = seqid
    
    def rb_dummy(self, p):
        pass
        
    def rb_status(self, p):        
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
        self.c['heater.on'] = p.get_8(6) != 0
        
    def rb_enable(self, p):
        self.c['fault.communication'] = 0
        self.estop_state = 0
                    
    def rb_heater_pvsv(self, p):
        self.c['heater.pv'] = p.get_16(1)
        self.c['heater.sv'] = p.get_16(3)
        self.extruder_ready_poll()
        
    def rb_motor_pvsv(self, p):
        self.c['motor.pv'] = p.get_16(1)
        self.c['motor.sv'] = p.get_16(3)

    
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
    
