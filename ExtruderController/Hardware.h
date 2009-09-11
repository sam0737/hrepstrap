
// Hardware Definition

// heater1: Extruder Heater
// Any Heater class
ThermocoupleHeater heater1(6, 11, 0, 10000, 2);

// heater2: Secondary Heater
// Any Heater class
ThermistorHeater heater2(3, 0, 12, 0, 10);

// motor1: Extruder Motor
// Any DIPMotor class
InversePwmBitBangMotor motor1(18, 10, 9, // en, out1, out2
        2, 3, // Encoder Pin
        23170, 0, 32, // P, I, D
        0, 0, 0); // iLimit, deadband, minOutput

