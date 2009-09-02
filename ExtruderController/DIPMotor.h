#define DIPTimeResolution 6 // 64khZ
#define JammedDistance 128

class DIPMotor
{
    enum MotorStatus {
        MachineOff = 1,
        MotorJammed = 2,
        StatusMask = 3,
        DIPSpeedMode = 4,
        DIPPositionMode = 8
    };
    
    private:
    // [6.10] rotation format
    int pv;
    int sv;
    int sv_acc;

    int dState;
    int iState;

    // [8.8] rotation per second format
    int speed;

    unsigned char inverse;
    unsigned char pwm_pin;
    unsigned char dir_pin;
    unsigned char a_pin;
    unsigned char b_pin;

    long next_manage_time;

    unsigned char status;

    public:
    DIPMotor(unsigned char _inverse, unsigned char _pwm_pin, unsigned char _dir_pin, unsigned char _a_pin, unsigned char _b_pin)
    {
        inverse = _inverse;
        pwm_pin = _pwm_pin;
        dir_pin = _dir_pin;
        a_pin = _a_pin;
        b_pin = _b_pin;

        pv = 0;
        sv = 0;
        sv_acc = 0;
        speed = 0;
    }

    void init()
    {
        pinMode(a_pin, INPUT);
        pinMode(b_pin, INPUT);
        digitalWrite(a_pin, HIGH);
        digitalWrite(b_pin, HIGH);

        pinMode(pwm_pin, OUTPUT);
        pinMode(dir_pin, OUTPUT);
        digitalWrite(pwm_pin, LOW);
        digitalWrite(dir_pin, LOW);
    }

    void readEncoder()
    {
        if (digitalRead(a_pin) == HIGH)
        {
            if (digitalRead(b_pin) == LOW) { pv++; } else { pv--; }
        } else
        {
            if (digitalRead(b_pin) == LOW) { pv--; } else { pv++; }
        }
    }

    void turnOff()
    {
        digitalWrite(pwm_pin, LOW);
        digitalWrite(dir_pin, LOW);
        status |= MachineOff;
    }

    void turnOn()
    {
        sv = pv;
        next_manage_time = micros();
        status = 0;
    }

    void manage()
    {
        if ((signed long) (micros() - next_manage_time) >= 0)
        {
            next_manage_time += 1000000 >> DIPTimeResolution; // 64 Hz

            if ((status & (DIPSpeedMode | DIPPositionMode)) == 0 ||
                (status & MachineOff)) {
                dState = 0;
                iState = 0;
                return;
            }

            if (status & DIPSpeedMode)
            {
                sv_acc += speed;
                sv += sv_acc >> (DIPTimeResolution);
                sv_acc &= ((1 << DIPTimeResolution) - 1);
            }

            // somewhat hacked implementation of a PID algorithm as described at:
            // http://www.embedded.com/2000/0010/0010feat3.htm - PID Without a PhD, Tim Wescott 

            int speed_error = sv - pv;

            /*
            if (speed_error < -JammedDistance || speed_error > JammedDistance)
            {
                status |= MachineOff | MotorJammed;
                analogWrite(pwm_pin, 0);
                return;
            }
            */

            int pTerm = 0;
            int iTerm = 0;
            int dTerm = 0;
            
            // calculate our P term
            pTerm = speed_error * 8; // * pGain

            // calculate our I term
            iState += speed_error;
            iState = constrain(iState, 0, 128);
            iTerm = iState / 2; // * iGain

            // calculate our D term
            dTerm = (speed_error - dState) * 1; // * dGain
            dState = speed_error;

            // calculate our PWM, within bounds.
            int output = pTerm + iTerm - dTerm;

            digitalWrite(dir_pin, (output > 0) ^ (inverse != 0) ? LOW : HIGH);
            analogWrite(pwm_pin, constrain(abs(output), 0, 255));
        }
    }

    int getPV()
    {
        return pv;
    }

    int getSV()
    {
        return sv;
    }

    void setRelativePos(int _pos)
    {
        // Values should be within -16383 to 16383        
        sv = pv + _pos;
        sv_acc = 0;
        status = (status & StatusMask) | DIPPositionMode;
    }

    void setSpeed(int _speed)
    {
        // Encoder line per second
        // Effectively, this is [7.9] signed rotation per second if we choose AS5040 which has 512bit reading resolution
        // Values should be within -16383 to 16383
        speed = _speed;
        if ((status & DIPSpeedMode) == 0)
        {
            sv = pv;
        }
        status = (status & StatusMask) | DIPSpeedMode;
    }

    void setPWM(unsigned char dir, unsigned pwm)
    {
        if ((status & MachineOff) == 0)
        {            
            status &= StatusMask;
            analogWrite(pwm_pin, pwm);
            digitalWrite(dir_pin, (dir == 0) ^ (inverse != 0) ? HIGH : LOW);
        }
    }

    unsigned char isJammed()
    {
        return (status & MotorJammed) != 0;
    }

    unsigned char isDIPManaged()
    {
        return (status & (DIPSpeedMode | DIPPositionMode)) != 0;
    }
        
    void setSpeedMode()
    {
        sv = pv;
        sv_acc = 0;
        status = (status & StatusMask) | DIPSpeedMode;
    }
};

