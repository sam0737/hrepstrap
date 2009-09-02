#include "Thermistor.h"

class Heater
{    
    enum HeaterStates { HEATER_HEATING, HEATER_COOLING };
    enum HeaterStatus {
        MachineOff = 1,
        InvalidResponse = 2,
        ThermistorDisconnected = 4
    };

    private:
    int temp_pv;
    int temp_sv;
    int temp_sv2;

    unsigned char status;

    unsigned char thermistor_pin;
    unsigned char heater_pin;
    int heat_response;
    
    int heat_response_temp;
    unsigned long heat_response_time;

    enum HeaterStates heater_state;

    int read_thermistor()
    {
        int raw = sample_temperature(thermistor_pin);

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
            status |= ThermistorDisconnected;
        }

        return celsius;
    }

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

    public:
    Heater(unsigned char _thermistor_pin, unsigned char _heater_pin, int _heat_response)
    {
        thermistor_pin = _thermistor_pin;
        heater_pin = _heater_pin;
        heat_response = _heat_response;

        temp_pv = 0;
        temp_sv = 0;
        temp_sv2 = 0;

        heat_response_temp = 0;
        status = MachineOff;
        heater_state = HEATER_COOLING;
    }

    void manage()
    {
        //make sure we know what our temp is.
        temp_pv = read_thermistor();

        if (status != 0)
        {
            heater_state = HEATER_COOLING;
            digitalWrite(HEATER_PIN, LOW);
            return;
        }

        if (heat_response_temp != 0 && (signed long) (millis() - heat_response_time) >= 0 && temp_pv < heat_response_temp)
        {
            status |= InvalidResponse;
        }

        if (temp_pv < temp_sv)
        {
            if (temp_pv >= heat_response_temp)
            {
                heat_response_temp = temp_pv + 5;
                heat_response_time = millis() + heat_response * 5;
            }
            digitalWrite(heater_pin, HIGH);
            heater_state = HEATER_HEATING;
        } else if (temp_pv >= temp_sv2)
        {
            analogWrite(heater_pin, LOW);
            heat_response_temp = 0;
            heater_state = HEATER_COOLING;
        }
    }

    unsigned char init()
    {
        pinMode(thermistor_pin, INPUT);
        digitalWrite(thermistor_pin, LOW);
        pinMode(heater_pin, OUTPUT);
        digitalWrite(heater_pin, LOW);
    }

    void turnOff()
    {
        digitalWrite(heater_pin, LOW);
        status |= MachineOff;
        heater_state = HEATER_COOLING;
    }

    void turnOn()
    {
        status = 0;
        heat_response_temp = 0;
        heater_state = HEATER_COOLING;
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
        temp_sv2 = t + 2;
    }
};

