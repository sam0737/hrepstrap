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
import time
import os
import serial
from datetime import datetime, timedelta 
from struct import *

class RepRapSerialComm: 
    _read_timeout = 100
 
    def __init__(self, port = "/dev/ttyUSB0", baudrate = 38400):
        self.ser = None
        self.ser = serial.Serial(port, baudrate, rtscts=0)
        self._read_state = 0
        self._read_length_left = 0
        self._read_packet = None
        self._read_next_timeout = None

    def reset(self):
        """
        Reset the state of the bus to a clean state by pumping invalid packets
        """
        self.ser.flushInput()
        self.ser.write(" " * 64)

        time.sleep(0.1)
        if self.ser.inWaiting() > 0:
            # If there are packets in the midstream, dump them.
            while self.process() == None:
                pass
             
    def send(self, packet):
        self.ser.write(pack('B', SimplePacket.START_BYTE))
        self.ser.write(pack('B', len(packet.buf)))
        self.ser.write(packet.buf)
        self.ser.write(pack('B', packet.crc))
 
    def readback(self):
        """
        This should be called whenever packet is expected. Mainly used by Host.
        
        Returns a SimplePacket if a packet (valid or invalid) is read. Returns None otherwise. 
        A packet with rc == RC_NO_RESPONSE will be returned eventually if response is not completed within timeout 100ms.
        """
        if self._read_next_timeout == None:
            self._read_next_timeout = datetime.now() + timedelta(milliseconds = RepRapSerialComm._read_timeout)
        return self.process()

    def process(self):
        """
        This should be called to receive new packet. Mainly used by Salve.
        
        Returns a SimplePacket if a packet (valid or invalid) is read. Returns None otherwise.
        Timeout mechanism will not be force triggered, but a packet with RC_NO_RESPONSE could still be returned if transmission stopped in the middle.
        """
        while self.ser.inWaiting() > 0:
            if self._read(unpack('B', self.ser.read(1))[0]):
                return self._read_packet
            
        if self._read_next_timeout != None and datetime.now() > self._read_next_timeout:
            self._read_state = 0
            if self._read_packet == None:
                self._read_packet = SimplePacket()
            self._read_packet.rc = SimplePacket.RC_NO_RESPONSE
            self._read_next_timeout = None
            return self._read_packet

        return None

    def _read(self, b):
        # Start
        if self._read_state == 0:
            if b == SimplePacket.START_BYTE:
                self._read_next_timeout = datetime.now() + timedelta(milliseconds = RepRapSerialComm._read_timeout)
                self._read_packet = SimplePacket()
                self._read_state += 1

        # Length
        elif self._read_state == 1:
            self._read_length_left = b
            self._read_state += 1

        # Content
        elif self._read_state == 2:
            self._read_packet.add_8(b)
            self._read_length_left -= 1

        # CRC
        elif self._read_state == 3:
            if b != self._read_packet.crc:
                self._read_packet.rc = SimplePacket.RC_CRC_MISMATCH

            if len(self._read_packet.buf) > 1:
                self._read_packet.tag = self._read_packet.buf[-1]
                self._read_packet.buf = self._read_packet.buf[0:-1]
            self._read_next_timeout = None
            self._read_state = 0
            return True
        
        if self._read_state == 2 and self._read_length_left == 0:
            self._read_state = 3
        
        return False

    def close(self):
        if self.ser != None:
            self.ser.close()
            self.ser = None

    def __del__(self):
        self.close()

class SimplePacket:
    """
    Packet structure used in RepRap communication
    """
    START_BYTE         = 0xD5
    RC_GENERIC_ERROR   = 0
    RC_OK              = 1
    RC_BUFFER_OVERFLOW = 2
    RC_CRC_MISMATCH    = 3
    RC_PACKET_TOO_BIG  = 4
    RC_CMD_UNSUPPORTED = 5
    RC_NO_RESPONSE     = 10000

    def __init__(self):
        self.buf = ""
        self.crc = 0
        self.rc = SimplePacket.RC_OK
        self.tag = -1

    def get_8(self, idx):
        if len(self.buf) > idx:
            return unpack('B',self.buf[idx])[0]
        else:
            return 0

    def get_16(self, idx):
        return self.get_8(idx+1)<<8 | self.get_8(idx)

    def get_32(self, idx):
        return self.get_16(idx+2)<<16 | self.get_16(idx)

    def add_32(self, d):
        self.add_16(d & 0xffff)
        self.add_16((d >> 16) & 0xffff)

    def add_16(self, d):
        self.add_8(d & 0xff)
        self.add_8((d >> 8) & 0xff)

    def add_8(self, d):
        self.buf += pack('B', d)
        self.add_crc(d)

    def add_crc(self, d):
        self.crc = self.crc ^ d
        for i in range(8):
            if self.crc & 0x01:
                self.crc = (self.crc >> 1) ^ 0x8C
            else:
                self.crc >>= 1
