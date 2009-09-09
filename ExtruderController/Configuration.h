/****************************************************************************************
 * Here's where you define the overall electronics setup for your machine.
 ****************************************************************************************/

//
// CHOOSE WHICH EXTRUDER YOU'RE USING:
//
//#define EXTRUDER_CONTROLLER_VERSION_2_0
//#define EXTRUDER_CONTROLLER_VERSION_2_1
#define EXTRUDER_CONTROLLER_VERSION_2_2

#define TEMPERATURE_SAMPLES 5
#define SERIAL_SPEED 38400

//the address for commands to listen to
#define RS485_ADDRESS 0
#define RS485_ENABLED 0
#define PACKET_TIMEOUT 100

#define RX_ENABLE_PIN 4
#define TX_ENABLE_PIN 16

#define DEBUG_PIN 13

