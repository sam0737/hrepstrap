#include <SimplePacket.h>
#include <EEPROM.h>

SimplePacket masterPacket(rs485_tx);

// Yep, this is actually -*- c++ -*-
// These are our query commands from the host
#define SLAVE_CMD_VERSION                0
#define SLAVE_CMD_INIT                   1  // Machine turn on
#define SLAVE_CMD_SET_MOTOR_1_PWM        4
#define SLAVE_CMD_SET_MOTOR_2_PWM        5
#define SLAVE_CMD_SET_MOTOR_1_RPM        6
#define SLAVE_CMD_SET_MOTOR_2_RPM        7
#define SLAVE_CMD_SET_MOTOR_1_DIR        8
#define SLAVE_CMD_SET_MOTOR_2_DIR        9
#define SLAVE_CMD_TOGGLE_MOTOR_1        10
#define SLAVE_CMD_TOGGLE_MOTOR_2        11
#define SLAVE_CMD_TOGGLE_FAN            12
#define SLAVE_CMD_TOGGLE_VALVE          13
#define SLAVE_CMD_SET_SERVO_1_POS       14
#define SLAVE_CMD_SET_SERVO_2_POS       15
#define SLAVE_CMD_FILAMENT_STATUS       16
#define SLAVE_CMD_GET_MOTOR_1_PWM       17
#define SLAVE_CMD_GET_MOTOR_2_PWM       18
#define SLAVE_CMD_GET_MOTOR_1_RPM       19
#define SLAVE_CMD_GET_MOTOR_2_RPM       20
#define SLAVE_CMD_SELECT_TOOL           21
#define SLAVE_CMD_IS_TOOL_READY         22
#define SLAVE_CMD_PAUSE_UNPAUSE         23
#define SLAVE_CMD_ABORT                 24
#define SLAVE_CMD_READ_FROM_EEPROM      25
#define SLAVE_CMD_WRITE_TO_EEPROM       26

// Sam's Extension
#define SLAVE_CMD_STATUS                80
/*  6 Byte.
 *  These bits will be pre-polled and cached by the controller, and return immediated on request
 *  For E-Stop trigger, E-Stop will be automatically flagged by microcontroller when those sistuation occurs
 *  Primary component bits are on LSB. (So 2nd byte Bit 0 represent the status of the primaary heater)
 *
 *  1st Byte: General
 *     Bit 0: E-Stop triggered (Clear when read)
 *     Bit 1: Machine online
 *  2nd Byte: Thermistor disconnected [E-Stop trigger]
 *  3rd Byte: Heater response [E-Stop trigger]
 *  4th Byte: Motor jammed [E-Stop trigger]
 *  5th Byte: No plastic
 *  6th Byte: Heater on
 */
#define SLAVE_CMD_TURN_ON               81
#define SLAVE_CMD_TURN_OFF              82

#define SLAVE_CMD_GET_HEATER1_PVSV      91
#define SLAVE_CMD_SET_HEATER1_SV        92

#define SLAVE_CMD_GET_MOTOR1_PVSV       95
#define SLAVE_CMD_SET_MOTOR1_REL_POS    96
#define SLAVE_CMD_SET_MOTOR1_SPEED      97
#define SLAVE_CMD_SET_MOTOR1_PWM        98
#define SLAVE_CMD_SET_MOTOR1_SPEED_MODE 99

unsigned long packet_timeout = 0;
char packet_timeout_enabled = 0;

//handle our packets.
void process_packets()
{
    if (packet_timeout_enabled != 0 && (signed long) (millis() - packet_timeout) >= 0)
    {
        // Sliently dropping timeout packet
        packet_timeout_enabled = 0;
        masterPacket.init();
        digitalWrite(DEBUG_PIN, LOW);
    }

    //do we have any data to process?
    if (Serial.available() > 0)
    {
        do
        {
            // grab a byte and process it.
            unsigned char d = Serial.read();
            masterPacket.process_byte(d);
        } while (!masterPacket.isFinished() && Serial.available() > 0);

        if (!masterPacket.isFinished() && masterPacket.getState() != PS_START)
        {
            digitalWrite(DEBUG_PIN, HIGH);
            packet_timeout_enabled = 1;
            packet_timeout = millis() + PACKET_TIMEOUT;
        } else
        {
            digitalWrite(DEBUG_PIN, LOW);
        }
    }

    //do we have a finished packet?
    if (masterPacket.isFinished())
    {
        packet_timeout_enabled = 0;

        //only process packets intended for us.
        if (masterPacket.get_8(0) == RS485_ADDRESS)
        {
            last_packet = millis();

            if (masterPacket.getResponseCode() == RC_OK)
            {
                // take some action, if CRC is correct
                handle_query();
            }

            // send reply over RS485
            // This includes masterPacket.init();
            send_reply();

            return;
        }

        // always clean up the packet.
        masterPacket.init();
    }
}

void send_reply()
{
    // Enable TX and send Response
    #if RS485_ENABLED
    digitalWrite(TX_ENABLE_PIN, HIGH);
    #endif
    masterPacket.sendReply();
    #if RS485_ENABLED
    digitalWrite(TX_ENABLE_PIN, LOW);
    #endif
}

//this is for handling query commands that need a response.
void handle_query()
{
    byte temp;

    //which one did we get?
    switch (masterPacket.get_8(1))
    {
#if 0
        // NOT TESTED
        case SLAVE_CMD_VERSION:
            //get our host version
            master_version = masterPacket.get_16(2);
            //send our version back.
            masterPacket.add_16(FIRMWARE_VERSION);
            break;
#endif

        // NOT TESTED
        case SLAVE_CMD_STATUS:
            for (unsigned char i = 0; i < 6; i++)
            {
                masterPacket.add_8(status[i]);
            }
            break;
        case SLAVE_CMD_TURN_ON:
            turnOn();
            break;
        case SLAVE_CMD_TURN_OFF:
            turnOff();
            break;

        case SLAVE_CMD_GET_HEATER1_PVSV:
            masterPacket.add_16(heater1.getPV());
            masterPacket.add_16(heater1.getSV());
            break;
        case SLAVE_CMD_SET_HEATER1_SV:
            heater1.setSV(masterPacket.get_16(2));
            break;

        case SLAVE_CMD_GET_MOTOR1_PVSV:
            masterPacket.add_16(motor1.getPV());
            masterPacket.add_16(motor1.getSV());
            break;

        case SLAVE_CMD_SET_MOTOR1_REL_POS:
            {
                int value = masterPacket.get_16(2);
                if (value >= -16383 && value < 16383)
                {
                    motor1.setRelativePos(masterPacket.get_16(2));
                } else
                {
                    masterPacket.unsupported();
                }
            }
            break;
        case SLAVE_CMD_SET_MOTOR1_SPEED:
            {
                int value = masterPacket.get_16(2);
                if (value >= -16383 && value < 16383)
                {
                    motor1.setSpeed(masterPacket.get_16(2));
                } else
                {
                    masterPacket.unsupported();
                }
            }
            break;

        case SLAVE_CMD_SET_MOTOR1_PWM:
            motor1.setPWM(masterPacket.get_8(2), masterPacket.get_8(3));
            break;

        // NOT TESTED
        case SLAVE_CMD_SET_MOTOR1_SPEED_MODE:
            motor1.setSpeedMode();
            break;

        default:
            masterPacket.unsupported();
            break;
#if 0
  //WORKING
  case SLAVE_CMD_SET_MOTOR_1_PWM:
    motor1_control = MC_PWM;
    motor1_pwm = masterPacket.get_8(2);
    break;

  //WORKING
  case SLAVE_CMD_SET_MOTOR_2_PWM:
    motor2_control = MC_PWM;
    motor2_pwm = masterPacket.get_8(2);
    break;

  //NEEDS TESTING
  case SLAVE_CMD_SET_MOTOR_1_RPM:
    motor1_target_rpm = masterPacket.get_32(2) * 16;
    #if MOTOR_STYLE == 1
      motor1_control = MC_ENCODER;
    #else
      motor1_control = MC_STEPPER;
      stepper_ticks = motor1_target_rpm / (MOTOR_STEPS * MOTOR_STEP_MULTIPLIER);
      stepper_high_pwm = motor1_pwm;
      stepper_low_pwm = round((float)motor1_pwm * 0.4);
    #endif
    break;

  //NEEDS TESTING
  case SLAVE_CMD_SET_MOTOR_2_RPM:
    motor2_control = MC_ENCODER;
    motor2_target_rpm = masterPacket.get_32(2);
    break;

  case SLAVE_CMD_SET_MOTOR_1_DIR:
    temp = masterPacket.get_8(2);
    if (temp & 1)
      motor1_dir = MC_FORWARD;
    else
      motor1_dir = MC_REVERSE;    
    break;

  case SLAVE_CMD_SET_MOTOR_2_DIR:
    temp = masterPacket.get_8(2);
    if (temp & 1)
      motor2_dir = MC_FORWARD;
    else
      motor2_dir = MC_REVERSE;    
    break;

  case SLAVE_CMD_TOGGLE_MOTOR_1:
    temp = masterPacket.get_8(2);
    if (temp & 2)
      motor1_dir = MC_FORWARD;
    else
      motor1_dir = MC_REVERSE;

    if (temp & 1)
    {
      enable_motor_1();
      
      //if we interrupted a reversal, wait for the motor to get back to its old position.
      if (motor1_reversal_count > 0)
      	delay(motor1_reversal_count);
      motor1_reversal_count = 0;
    }
    else
      disable_motor_1();
    break;

  //WORKING
  case SLAVE_CMD_TOGGLE_MOTOR_2:
    temp = masterPacket.get_8(2);
    if (temp & 2)
      motor2_dir = MC_FORWARD;
    else
      motor2_dir = MC_REVERSE;

    //TODO: check to see if we're not in stepper mode.
    if (temp & 1)
      enable_motor_2();
    else
      disable_motor_2();
    break;

  //WORKING
  case SLAVE_CMD_TOGGLE_FAN:
    temp = masterPacket.get_8(2);
    if (temp & 1)
      enable_fan();
    else
      disable_fan();
    break;

  //WORKING
  case SLAVE_CMD_TOGGLE_VALVE:
    temp = masterPacket.get_8(2);
    if (temp & 1)
      open_valve();
    else
      close_valve();
    break;

  //WORKING
  case SLAVE_CMD_SET_SERVO_1_POS:
    servo1.attach(9);
    servo1.write(masterPacket.get_8(2));
    break;

  //WORKING
  case SLAVE_CMD_SET_SERVO_2_POS:
    servo2.attach(10);
    servo2.write(masterPacket.get_8(2));
    break;

  //WORKING
  case SLAVE_CMD_FILAMENT_STATUS:
    //TODO: figure out how to detect this.
    masterPacket.add_8(255);
    break;

  //WORKING
  case SLAVE_CMD_GET_MOTOR_1_PWM:
    masterPacket.add_8(motor1_pwm);
    break;

  //WORKING
  case SLAVE_CMD_GET_MOTOR_2_PWM:
    masterPacket.add_8(motor2_pwm);
    break;

  //NEEDS TESTING
  case SLAVE_CMD_GET_MOTOR_1_RPM:
    masterPacket.add_32(motor1_current_rpm);
    break;

  //NEEDS TESTING
  case SLAVE_CMD_GET_MOTOR_2_RPM:
    masterPacket.add_32(motor1_current_rpm);
    break;

  //WORKING
  case SLAVE_CMD_SELECT_TOOL:
    //do we do anything?
    break;

  //WORKING
  case SLAVE_CMD_IS_TOOL_READY:
    masterPacket.add_8(is_tool_ready());
    break;

  case SLAVE_CMD_ABORT:
    initialize();
    break;
  case SLAVE_CMD_READ_FROM_EEPROM:
    {
      const uint16_t offset = masterPacket.get_16(2);
      const uint8_t count = masterPacket.get_8(4);
      if (count > 16) {
	masterPacket.overflow();
      } else {
	for (uint8_t i = 0; i < count; i++) {
	  masterPacket.add_8(EEPROM.read(offset+i));
	}
      }
    }
    break;
  case SLAVE_CMD_WRITE_TO_EEPROM:
    {
      uint16_t offset = masterPacket.get_16(2);
      uint8_t count = masterPacket.get_8(4);
      if (count > 16) {
	masterPacket.overflow();
      } else {
	for (uint8_t i = 0; i < count; i++) {
	  EEPROM.write(offset+i,masterPacket.get_8(5+i));
	}
	masterPacket.add_8(count);
      }
    }
    break;
#endif
  }
}

void rs485_tx(byte b)
{
    Serial.print(b, BYTE);

    #if RS485_ENABLED
    // read for our own byte.
    long now = millis();
    long end = now + 10;
    int tmp = Serial.read();
    while (tmp != b)
    {
        tmp = Serial.read();
        if (millis() > end) break;
    }
    #endif
}
