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
    // steps per seconds
    int speed;

    // [8.8] format
    int pGain;
    int iGain;
    int dGain;
    int iLimit;
    unsigned char deadband;
    unsigned char minOutput;

    int dState;
    int iState;

    unsigned char inverse;
    unsigned char pwm_pin;
    unsigned char dir_pin;
    unsigned char a_pin;
    unsigned char b_pin;

    long next_manage_time;

    unsigned char status;

    public:
    DIPMotor(unsigned char _inverse, unsigned char _pwm_pin, unsigned char _dir_pin, unsigned char _a_pin, unsigned char _b_pin,
             int _pGain, int _iGain, int _dGain, int _iLimit, unsigned char _deadband, unsigned char _minOutput)
    {
        inverse = _inverse;
        pwm_pin = _pwm_pin;
        dir_pin = _dir_pin;
        a_pin = _a_pin;
        b_pin = _b_pin;

        pGain = _pGain;
        iGain = _iGain;
        dGain = _dGain;
        iLimit = _iLimit;
        deadband = _deadband;
        minOutput = _minOutput;

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

            long speed_error = sv - pv;

            /*
            if (speed_error < -JammedDistance || speed_error > JammedDistance)
            {
                status |= MachineOff | MotorJammed;
                analogWrite(pwm_pin, 0);
                return;
            }
            */

            long pTerm = 0;
            long iTerm = 0;
            long dTerm = 0;
            
            // calculate our P term
            pTerm = speed_error * pGain >> 8;

            // calculate our I term
            iState += speed_error;
            iState = constrain(iState, 0, iLimit);
            iTerm = iState * iGain >> 8;

            // calculate our D term
            dTerm = (speed_error - dState) * dGain >> 8;
            dState = speed_error;

            // calculate our PWM, within bounds.
            int output = pTerm + iTerm - dTerm;
            int abs_output = abs(output);

            digitalWrite(dir_pin, (output > 0) ^ (inverse != 0) ? LOW : HIGH);
            analogWrite(pwm_pin, 
                    abs_output <= deadband ? 0 : constrain(abs_output, minOutput, 255)
                    );
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
        if ((status & MachineOff)) return;

        // Values should be within -16383 to 16383        
        sv = pv + _pos;
        sv_acc = 0;
        status = (status & StatusMask) | DIPPositionMode;
    }

    void setSpeed(int _speed)
    {
        if ((status & MachineOff)) return;

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

    void setPIDConstant(int _pGain, int _iGain, int _dGain, int _iLimit, unsigned char _deadband, unsigned char _minOutput)
    {
        pGain = _pGain;
        iGain = _iGain;
        dGain = _dGain;
        iLimit = _iLimit;
        deadband = _deadband;
        minOutput = _minOutput;
    }
};

