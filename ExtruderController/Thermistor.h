// Thermistor lookup table for RepRap Temperature Sensor Boards (http://make.rrrf.org/ts)
// Made with createTemperatureLookup.py (http://svn.reprap.org/trunk/reprap/firmware/Arduino/utilities/createTemperatureLookup.py)
// ./createTemperatureLookup.py --r0=6360 --t0=100 --r1=0 --r2=1818 --beta=3990 --max-adc=1023
// r0: 6360
// t0: 100
// r1: 0
// r2: 1818
// beta: 3990
// max adc: 1023
#define NUMTEMPS 20
short temptable[NUMTEMPS][2] = {
   {1, 1316},
   {54, 335},
   {107, 274},
   {160, 241},
   {213, 219},
   {266, 202},
   {319, 188},
   {372, 176},
   {425, 165},
   {478, 155},
   {531, 146},
   {584, 137},
   {637, 128},
   {690, 119},
   {743, 110},
   {796, 100},
   {849, 88},
   {902, 75},
   {955, 57},
   {1008, 20}
};

