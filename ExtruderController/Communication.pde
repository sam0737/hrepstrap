#include <SimplePacket.h>
#include <EEPROM.h>

SimplePacket masterPacket(rs485_tx);

// These are our query commands from the host
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
#define SLAVE_CMD_GET_HEATER2_PVSV      93
#define SLAVE_CMD_SET_HEATER2_SV        94

#define SLAVE_CMD_GET_MOTOR1_PVSV       95
#define SLAVE_CMD_SET_MOTOR1_REL_POS    96
#define SLAVE_CMD_SET_MOTOR1_SPEED      97
#define SLAVE_CMD_SET_MOTOR1_PWM        98
#define SLAVE_CMD_SET_MOTOR1_SPEED_MODE 99
#define SLAVE_CMD_SET_MOTOR1_TUNING     100

unsigned long packet_timeout = 0;
char packet_timeout_enabled = 0;

// Packet handling
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

                // Echo the request code for verification
                masterPacket.add_8(masterPacket.get_8(1));
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

void handle_query()
{
    switch (masterPacket.get_8(1))
    {
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

        case SLAVE_CMD_GET_HEATER2_PVSV:
            masterPacket.add_16(heater2.getPV());
            masterPacket.add_16(heater2.getSV());
            break;
        case SLAVE_CMD_SET_HEATER2_SV:
            heater2.setSV(masterPacket.get_16(2));
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
                    motor1.setRelativePos(value);
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
                    motor1.setSpeed(value);
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
        case SLAVE_CMD_SET_MOTOR1_TUNING:
            motor1.setPIDConstant(
                masterPacket.get_16(2), masterPacket.get_16(4), masterPacket.get_16(6),
                masterPacket.get_16(8), masterPacket.get_8(10), masterPacket.get_8(11)
                );

        default:
            masterPacket.unsupported();
            break;
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
