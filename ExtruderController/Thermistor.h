// Thermistor lookup table for RepRap Temperature Sensor Boards (http://make.rrrf.org/ts)
// Made with createTemperatureLookup.py (http://svn.reprap.org/trunk/reprap/firmware/Arduino/utilities/createTemperatureLookup.py)
// ./createTemperatureLookup.py --r0=6360 --t0=100 --r1=0 --r2=4700 --beta=3990 --max-adc=1023
// r0: 6360
// t0: 100
// r1: 0
// r2: 4700
// beta: 3990
// max adc: 1023
#define NUMTEMPS 20
short temptable[NUMTEMPS][2] = {
   {1, 880},
   {54, 258},
   {107, 210},
   {160, 185},
   {213, 167},
   {266, 153},
   {319, 142},
   {372, 132},
   {425, 123},
   {478, 115},
   {531, 108},
   {584, 100},
   {637, 93},
   {690, 85},
   {743, 78},
   {796, 69},
   {849, 60},
   {902, 48},
   {955, 33},
   {1008, 1}
};

