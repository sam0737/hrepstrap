#include "Thermistor.h"

class Heater
{    
    protected:
    enum HeaterStatus {
        MachineOff = 1,
        InvalidResponse = 2,
        ThermistorDisconnected = 4
    };

    int temp_pv;
    unsigned char heater_pwm;
    unsigned char cooler_pwm;

    long next_manage_time;
    unsigned char pwm_counter;

    unsigned char status;

    unsigned char heater_pin;
    unsigned char cooler_pin;

    unsigned char is_heat_response_check;
    int heat_response;    
    int heat_response_temp;
    unsigned long heat_response_time;

    virtual int read_thermistor() = 0;

    public:
    Heater(unsigned char _heater_pin, unsigned char _cooler_pin, int _heat_response) 
    {
        heater_pin = _heater_pin;
        cooler_pin = _cooler_pin;
        heat_response = _heat_response;

        temp_pv = 0;
        heater_pwm = 0;
        cooler_pwm = 0;

        is_heat_response_check = 0;
        status = MachineOff;
    }

    void manage()
    {
        if ((signed long) (micros() - next_manage_time) >= 0)
        {
            next_manage_time += 1000000 >> 10; // 1024 Hz
            pwm_counter++;
            
            //make sure we know what our temp is.
            temp_pv = this->read_thermistor();

            if (status != 0)
            {
                digitalWrite(heater_pin, LOW);
                digitalWrite(cooler_pin, LOW);
                return;
            }

            if (heater_pwm && heater_pwm >= pwm_counter)
            {
                digitalWrite(heater_pin, HIGH);
                /*
                if (temp_pv >= heat_response_temp && temp_pv < 150)
                {
                    is_heat_response_check = 1;
                    heat_response_temp = temp_pv + 1;
                    heat_response_time = millis() + (long) heat_response * 1;
                } else
                {
                    is_heat_response_check = 0;
                }
                */
            } else
            {
                digitalWrite(heater_pin, LOW);
                // heat_response_temp = 0;
            }

            if (cooler_pwm && cooler_pwm >= pwm_counter)
            {
                digitalWrite(cooler_pin, HIGH);
            } else
            {
                digitalWrite(cooler_pin, LOW);
            }
                        
            /*
            if (is_heat_response_check && (signed long) (millis() - heat_response_time) >= 0 && temp_pv < heat_response_temp)
            {
                status |= InvalidResponse;
            }
            */
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
        is_heat_response_check = 0;
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
        return heater_pwm > 0;
    }

    int getPV()
    {
        return temp_pv;
    }

    void setHeaterPWM(unsigned char p)
    {
        heater_pwm = p;
        //is_heat_response_check = heat_response != 0 && p > 200;
    }

    void setCoolerPWM(unsigned char p)
    {
        cooler_pwm = p;
        //if (p > 0) is_heat_response_check = 0;
    }
};

class ThermistorHeater : public Heater
{    
    private:
    unsigned char thermocouple_pin;

    static int sample_temperature(unsigned char pin)
    {
        return analogRead(pin);
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
    ThermistorHeater(unsigned char _thermocouple_pin, unsigned char _heater_pin, unsigned char _cooler_pin, int _heat_response) :
        Heater(_heater_pin, _cooler_pin, _heat_response)
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
        return analogRead(pin);
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
    ThermocoupleHeater(unsigned char _thermistor_pin, unsigned char _heater_pin, unsigned char _cooler_pin, int _heat_response) :
        Heater(_heater_pin, _cooler_pin, _heat_response)
    {
        thermistor_pin = _thermistor_pin;
    }
};

