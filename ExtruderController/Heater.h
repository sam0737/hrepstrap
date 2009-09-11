#include "Thermistor.h"

class Heater
{    
    protected:
    enum HeaterStates { HEATER_HEATING, HEATER_IDLE };
    enum CoolerStates { COOLER_COOLING, COOLER_IDLE };

    enum HeaterStatus {
        MachineOff = 1,
        InvalidResponse = 2,
        ThermistorDisconnected = 4
    };

    int temp_pv;
    int temp_sv;
    int temp_sv_low;
    int temp_sv_high;

    long next_manage_time;
    unsigned char poorman_pwm_flip;

    unsigned char status;

    unsigned char heater_pin;
    unsigned char cooler_pin;
    int heat_response;
    
    int heat_response_temp;
    int hysteresis;
    unsigned long heat_response_time;

    enum HeaterStates heater_state;
    enum CoolerStates cooler_state;

    virtual int read_thermistor() = 0;

    public:
    Heater(unsigned char _heater_pin, unsigned char _cooler_pin, int _heat_response, int _hysteresis)
    {
        heater_pin = _heater_pin;
        cooler_pin = _cooler_pin;
        heat_response = _heat_response;
        hysteresis = _hysteresis;

        temp_pv = 0;
        temp_sv = 0;
        temp_sv_high = 0;
        temp_sv_low = 0;

        heat_response_temp = 0;
        status = MachineOff;
        heater_state = HEATER_IDLE;
        cooler_state = COOLER_IDLE;
    }

    void manage()
    {
        if ((signed long) (micros() - next_manage_time) >= 0)
        {
            next_manage_time += 1000000 >> 6; // 64 Hz
            poorman_pwm_flip++;
            
            //make sure we know what our temp is.
            temp_pv = this->read_thermistor();

            if (status != 0)
            {
                heater_state = HEATER_IDLE;
                cooler_state = COOLER_IDLE;
                digitalWrite(heater_pin, LOW);
                digitalWrite(cooler_pin, LOW);
                return;
            }

            if (heat_response_temp != 0 && temp_pv < 120 && (signed long) (millis() - heat_response_time) >= 0 && temp_pv < heat_response_temp)
            {
                status |= InvalidResponse;
            }

            if (temp_pv < temp_sv_low)
            {
                digitalWrite(heater_pin, HIGH);
                digitalWrite(cooler_pin, LOW);
                if (temp_pv >= heat_response_temp && heater_pin != 0)
                {
                    heat_response_temp = temp_pv + 1;
                    heat_response_time = millis() + (long) heat_response * 1;
                    if (heater_state == HEATER_IDLE)
                    {
                        heat_response_temp += 2;
                        heat_response_time += heat_response * 3;
                    }
                }
                heater_state = HEATER_HEATING;
                cooler_state = COOLER_IDLE;
            } else if (temp_pv > temp_sv_high)
            {
                digitalWrite(heater_pin, LOW);
                digitalWrite(cooler_pin, HIGH);
                heater_state = HEATER_IDLE;
                cooler_state = COOLER_COOLING;
                heat_response_temp = 0;
            } else if (heater_pin == 0)
            {
                // Poor's man PWM. I don't want Heater to requires the use of PWM port
                digitalWrite(cooler_pin, poorman_pwm_flip % 2 ? HIGH : LOW);  
                heater_state = HEATER_IDLE;
                cooler_state = COOLER_COOLING;
                heat_response_temp = 0;
            } else if (cooler_pin == 0)
            {
                // Poor's man PWM. I don't want Heater to requires the use of PWM port
                digitalWrite(heater_pin, poorman_pwm_flip % 2 ? HIGH : LOW);  
                cooler_state = COOLER_IDLE;
                heater_state = HEATER_HEATING;
                heat_response_temp = 0;
            } else
            {
                digitalWrite(cooler_pin, 0);
                digitalWrite(heater_pin, 0);
                cooler_state = COOLER_IDLE;
                heater_state = HEATER_IDLE;
                heat_response_temp = 0;
            }
        }
    }

    virtual void init()
    {
        // Don't config Thermistor Pin. It's analog pin!

        pinMode(heater_pin, OUTPUT);
        digitalWrite(heater_pin, LOW);
        pinMode(cooler_pin, OUTPUT);
        digitalWrite(heater_pin, LOW);

        next_manage_time = micros();
    }

    virtual void turnOff()
    {
        if (heat_response) digitalWrite(heater_pin, LOW);
        status |= MachineOff;
    }

    virtual void turnOn()
    {
        status = 0;
        heat_response_temp = 0;
    }

    unsigned char isInvalidResponse()
    {
        return (status & InvalidResponse) != 0;
    }

    unsigned char isThermistorDisconnected()
    {
        return (status & ThermistorDisconnected) != 0;
    }

    unsigned char isHeaterOn()
    {
        return heater_state == HEATER_HEATING;
    }

    int getPV()
    {
        return temp_pv;
    }

    int getSV()
    {
        return temp_sv;
    }

    void setSV(int t)
    {
        temp_sv = t;
        temp_sv_low = cooler_pin == 0 ? t : t - hysteresis;
        temp_sv_high = heater_pin == 0 ? t : t + hysteresis;
    }
};

class ThermistorHeater : public Heater
{    
    private:
    unsigned char thermocouple_pin;

    static int sample_temperature(unsigned char pin)
    {
        int raw = 0;

        // read in a certain number of samples
        for (byte i=0; i<TEMPERATURE_SAMPLES; i++)
            raw += analogRead(pin);

        // average the samples
        raw = raw / TEMPERATURE_SAMPLES;

        // send it back.
        return raw;
    }

    protected:
    virtual int read_thermistor()
    {
        int raw = sample_temperature(thermocouple_pin);

        int celsius = 0;
        byte i;

        for (i=1; i<NUMTEMPS; i++)
        {
            if (temptable[i][0] > raw)
            {
                celsius = temptable[i-1][1] + 
                    (raw - temptable[i-1][0]) * 
                    (temptable[i][1] - temptable[i-1][1]) /
                    (temptable[i][0] - temptable[i-1][0]);
                
                break;
            }
        }

        // Overflow: We just clamp to 0 degrees celsius
        if (i == NUMTEMPS)
        {
            celsius = 0;
            if (heat_response) status |= ThermistorDisconnected;
        }
        return celsius;
    }

    public:
    ThermistorHeater(unsigned char _thermocouple_pin, unsigned char _heater_pin, unsigned char _cooler_pin, int _heat_response, int _hysteresis) :
        Heater(_heater_pin, _cooler_pin, _heat_response, _hysteresis)
    {
        thermocouple_pin = _thermocouple_pin;
    }
};

class ThermocoupleHeater : public Heater
{    
    private:
    unsigned char thermistor_pin;

    static int sample_temperature(unsigned char pin)
    {
        int raw = 0;

        // read in a certain number of samples
        for (byte i=0; i<TEMPERATURE_SAMPLES; i++)
            raw += analogRead(pin);

        // average the samples
        raw = raw / TEMPERATURE_SAMPLES;

        // send it back.
        return raw;
    }

    protected:
    virtual int read_thermistor()
    {
        long raw = sample_temperature(thermistor_pin);

        if (raw == 0 && heat_response)
        {
            status |= ThermistorDisconnected;
        }
        return (int) ((raw+1) * 5 * 100 / 1024);
    }

    public:
    ThermocoupleHeater(unsigned char _thermistor_pin, unsigned char _heater_pin, unsigned char _cooler_pin, int _heat_response, int _hysteresis) :
        Heater(_heater_pin, _cooler_pin, _heat_response, _hysteresis)
    {
        thermistor_pin = _thermistor_pin;
    }
};

