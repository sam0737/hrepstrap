#include "Thermistor.h"

class Heater
{    
    protected:
    enum HeaterStates { HEATER_HEATING, HEATER_COOLING };
    enum HeaterStatus {
        MachineOff = 1,
        InvalidResponse = 2,
        ThermistorDisconnected = 4
    };

    int temp_pv;
    int temp_sv;
    int temp_sv2;

    long next_manage_time;
    unsigned char poorman_pwm_flip;

    unsigned char status;

    unsigned char thermistor_pin;
    unsigned char heater_pin;
    int heat_response;
    
    int heat_response_temp;
    unsigned long heat_response_time;

    enum HeaterStates heater_state;

    virtual int read_thermistor() = 0;

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
        if ((signed long) (micros() - next_manage_time) >= 0)
        {
            next_manage_time += 1000000 >> 6; // 64 Hz
            poorman_pwm_flip++;
            
            //make sure we know what our temp is.
            temp_pv = this->read_thermistor();

            if (heat_response)
            {
                if (status != 0)
                {
                    heater_state = HEATER_COOLING;
                    digitalWrite(heater_pin, LOW);
                    return;
                }

                if (heat_response_temp != 0 && (signed long) (millis() - heat_response_time) >= 0 && temp_pv < heat_response_temp)
                {
                    status |= InvalidResponse;
                }

                if (temp_pv < temp_sv)
                {
                    digitalWrite(heater_pin, HIGH);
                    if (temp_pv >= heat_response_temp)
                    {
                        if (temp_pv > 60)
                        {
                            heat_response_temp = 0;
                        } else
                        {
                            heat_response_temp = temp_pv + 2;
                            heat_response_time = millis() + (long) heat_response * 2;
                            if (heater_state == HEATER_COOLING)
                            {
                                heat_response_time += 20000;
                            }
                        }
                    }
                    heater_state = HEATER_HEATING;
                } else if (temp_pv < temp_sv2)
                {
                    // Poor's man PWM. I don't want Heater to requires the use of PWM port
                    digitalWrite(heater_pin, poorman_pwm_flip % 2 ? HIGH : LOW);  
                    heater_state = HEATER_HEATING;
                    heat_response_temp = 0;
                } else if (temp_pv >= temp_sv2)
                {
                    digitalWrite(heater_pin, LOW);
                    heater_state = HEATER_COOLING;
                    heat_response_temp = 0;
                }
            }
        }
    }

    virtual void init()
    {
        // Don't config Thermistor Pin. It's analog pin!

        if (heat_response) pinMode(heater_pin, OUTPUT);
        digitalWrite(heater_pin, LOW);

        next_manage_time = micros();
    }

    virtual void turnOff()
    {
        if (heat_response) digitalWrite(heater_pin, LOW);
        status |= MachineOff;
        heater_state = HEATER_COOLING;
    }

    virtual void turnOn()
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

class ThermistorHeater : public Heater
{    
    private:
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
            if (heat_response) status |= ThermistorDisconnected;
        }
        return celsius;
    }

    public:
    ThermistorHeater(unsigned char _thermistor_pin, unsigned char _heater_pin, int _heat_response) :
        Heater(_thermistor_pin, _heater_pin, _heat_response)
    {
    }
};

class ThermocoupleHeater : public Heater
{    
    private:
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
    ThermocoupleHeater(unsigned char _thermistor_pin, unsigned char _heater_pin, int _heat_response) :
        Heater(_thermistor_pin, _heater_pin, _heat_response)
    {
    }
};

