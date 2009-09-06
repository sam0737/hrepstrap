/*
 *  Extruder Firmware for Extruder Controller v2.x
 *
 *  Adopted by Sam Wong for his own RepStrap, used with Linux EMC2
 *
 *  License: GPLv2
 *
 *  Board documentation at: http://make.rrrf.org/ec-2.0
 *  Specification for the original communication protocol is located at: 
 *      http://docs.google.com/Doc?id=dd5prwmp_14ggw37mfp
 *  
 *  Original Authors: Marius Kintel, Adam Mayer, and Zach Hoeken
 *
 *********************************************************************************************************/

#ifndef __AVR_ATmega168__
#error Oops!  Make sure you have 'Arduino' selected from the boards menu.
#endif

#include <WProgram.h>
#include <stdint.h>

#include "Configuration.h"
#include "Heater.h"
#include "DIPMotor.h"

char machine_on = 0;
unsigned long last_packet = 0;

unsigned char status[6];


void setup()
{
    init_serial();
    init_hardware();
}

void init_serial()
{
    // Enable the RS485 Transceiver
    pinMode(RX_ENABLE_PIN, OUTPUT);
    pinMode(TX_ENABLE_PIN, OUTPUT);
    #if RS485_ENABLED
    digitalWrite(RX_ENABLE_PIN, LOW);
    #else
    digitalWrite(RX_ENABLE_PIN, HIGH);
    #endif
    digitalWrite(TX_ENABLE_PIN, LOW); // Disable tx

    Serial.begin(SERIAL_SPEED);
}

Heater heater1(THERMISTOR_PIN, HEATER_PIN, 5000);
InversePwmBitBangMotor motor1(18, 10, 9,
        ENCODER_A_PIN, ENCODER_B_PIN,
        23170, 0, 32,
        0, 0, 0);

void init_hardware()
{
    //attach our interrupt handler
    // Motors Output
    pinMode(MOTOR_2_SPEED_PIN, OUTPUT);
    pinMode(MOTOR_2_DIR_PIN, OUTPUT);

    // Accessory Output
    pinMode(FAN_PIN, OUTPUT);
    pinMode(VALVE_PIN, OUTPUT);

    heater1.init();
    motor1.init();

    // Motor 1
    attachInterrupt(0, encoder1IRQ, CHANGE);

    // Debug Pins
    pinMode(DEBUG_PIN, OUTPUT);

    turnOff();
}

void encoder1IRQ()
{
    motor1.readEncoder();
}

void turnOff()
{    
    machine_on = 0;
    // Stop Motor
    digitalWrite(MOTOR_2_SPEED_PIN, LOW);
    digitalWrite(MOTOR_2_DIR_PIN, HIGH);
    
    // Turn Off accessory
    digitalWrite(FAN_PIN, LOW);
    digitalWrite(VALVE_PIN, LOW);

    motor1.turnOff();
    heater1.turnOff();

    update_status();
}

void turnOn()
{    
    machine_on = 1;
    motor1.turnOn();
    heater1.turnOn();

    update_status();
}

void loop()
{
    process_packets();
    heater1.manage();
    motor1.manage();
    update_status();

    // If there wasn't any packet from host for a while, shut down the system
    if ((signed long) (millis() - last_packet) > 1000)
    {
        turnOff();
    }
}

void update_status()
{
    memset(status, 0, 6);

    // [1] Thermistor disconnected
    if (heater1.isThermistorDisconnected()) status[1] |= 1;
    // [2] Heater response error
    if (heater1.isInvalidResponse()) status[2] |= 1;
    
    // [3] Motor jammed
    if (motor1.isJammed()) status[3] |= 1;
    
    // [4] No plastic
    // TODO

    // [5] Heater on
    if (heater1.isHeaterOn()) status[5] |= 1;
    
    if (status[1] || status[2] || status[3])
    {
        if (machine_on) { turnOff(); }
        status[0] |= 1;
    }
    if (machine_on) status[0] |= 2;
}

