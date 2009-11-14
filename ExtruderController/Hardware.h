
// Hardware Definition

// heater1: Extruder Heater
// Any Heater class
ThermocoupleHeater heater1(6, 11, 0, 10000);

// heater2: Secondary Heater
// Any Heater class
ThermistorHeater heater2(3, 0, 12, 0);

// motor1: Extruder Motor
// Any DIPMotor class
InversePwmBitBangMotor motor1(18, 10, 9, // en, out1, out2
        3, 2, // Encoder Pin
        23170 / 2, 0, 32 / 2, // P, I, D
        0, 0, 0); // iLimit, deadband, minOutput

