// Two numbers added up below should be <= 14
#define DIPTimeResolution 6 // 64kHz
#define SpeedFraction 8 // How many RHS bits in SetSpeed parameter are fraction part?

// #define JammedDistance 128 TODO

class DIPMotor
{
    protected:
    enum MotorStatus {
        MachineOff = 1,
        MotorJammed = 2,
        StatusMask = 3,
        DIPSpeedMode = 4,
        DIPPositionMode = 8
    };
    
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

    unsigned char a_pin;
    unsigned char b_pin;

    long next_manage_time;

    unsigned char status;

    virtual void performPwm(unsigned char dir, unsigned char pwm) = 0;

    public:
    DIPMotor(unsigned char _a_pin, unsigned char _b_pin,
             int _pGain, int _iGain, int _dGain, int _iLimit, unsigned char _deadband, unsigned char _minOutput)
    {
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

    void readEncoderA()
    {
        if (digitalRead(a_pin) == HIGH)
        {
            if (digitalRead(b_pin) == LOW) { pv++; } else { pv--; }
        } else
        {
            if (digitalRead(b_pin) == LOW) { pv--; } else { pv++; }
        }
    }
    
    void readEncoderB()
    {
        if (digitalRead(b_pin) == HIGH)
        {
            if (digitalRead(a_pin) == LOW) { pv--; } else { pv++; }
        } else
        {
            if (digitalRead(a_pin) == LOW) { pv++; } else { pv--; }
        }
    }

    virtual void init() 
    {
        pinMode(a_pin, INPUT);
        pinMode(b_pin, INPUT);
        digitalWrite(a_pin, HIGH);
        digitalWrite(b_pin, HIGH);
    }

    virtual void turnOff()
    {
        status |= MachineOff;
    }

    virtual void turnOn()
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
                sv += sv_acc >> (DIPTimeResolution + SpeedFraction);
                sv_acc &= ((1 << DIPTimeResolution + SpeedFraction) - 1);
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
            long output = pTerm + iTerm - dTerm;
            if (status & DIPSpeedMode)
            {
                output += speed / 128;
            }
            unsigned char dir = output > 0;
            unsigned char abs_output = constrain(abs(output), 0, 255);
        
            this->performPwm(dir, abs_output <= deadband ? 0 : constrain(abs_output, minOutput, 255));
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
        // Caller should ensure the input is within -16383 to +16383

        sv = pv + _pos;
        sv_acc = 0;
        status = (status & StatusMask) | DIPPositionMode;
    }

    void setSpeed(int _speed)
    {
        if ((status & MachineOff)) return;
        // Caller should ensure the input is within -16383 to +16383

        // Encoder line per second, with SpeedFraction RHS bits donating the fraction.
        // i.e. This is [*.y] a fixed signed point format, with y = SpeedFraction.
        speed = _speed;
        if ((status & DIPSpeedMode) == 0)
        {
            sv = pv;
            next_manage_time = micros();
        }
        status = (status & StatusMask) | DIPSpeedMode;
    }

    void setPWM(unsigned char dir, unsigned char pwm)
    {
        if ((status & MachineOff) == 0)
        {            
            status &= StatusMask;
            this->performPwm(dir, pwm);
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
        next_manage_time = micros();
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

/* Drive a PWM and DIR pin. PWM pin must be on PWM channel */
class SimplePwmMotor : public DIPMotor
{   
    protected:
    unsigned char inverse;
    unsigned char pwm_pin;
    unsigned char dir_pin;

    virtual void performPwm(unsigned char dir, unsigned char pwm)
    {
        digitalWrite(dir_pin, (dir == 0) ^ (inverse != 0) ? HIGH : LOW);
        analogWrite(pwm_pin, pwm);
    }

    public:
    SimplePwmMotor(unsigned char _inverse, unsigned char _pwm_pin, unsigned char _dir_pin, unsigned char _a_pin, unsigned char _b_pin,
             int _pGain, int _iGain, int _dGain, int _iLimit, unsigned char _deadband, unsigned char _minOutput):
        DIPMotor(_a_pin, _b_pin, _pGain, _iGain, _dGain, _iLimit, _deadband, _minOutput)
    {
        inverse = _inverse;
        pwm_pin = _pwm_pin;
        dir_pin = _dir_pin;
    }

    void init()
    {
        DIPMotor::init();

        pinMode(pwm_pin, OUTPUT);
        pinMode(dir_pin, OUTPUT);
        digitalWrite(pwm_pin, LOW);
        digitalWrite(dir_pin, LOW);
    }

    virtual void turnOff()
    {
        DIPMotor::turnOff();

        digitalWrite(pwm_pin, LOW);
        digitalWrite(dir_pin, LOW);
    }
};

/* Drive an L298 directly with 2 PWM + EN pin. Two output must be on two PWM channel. */
class InversePwmBitBangMotor : public DIPMotor
{   
    protected:
    unsigned char en_pin;
    unsigned char out1_pin;
    unsigned char out2_pin;

    virtual void performPwm(unsigned char dir, unsigned char pwm)
    {
        if (dir)
        {
            analogWrite(out1_pin, 255);
            analogWrite(out2_pin, 255 - pwm);
        } else
        {
            analogWrite(out1_pin, 255 - pwm);
            analogWrite(out2_pin, 255);
        }
    }

    public:
    InversePwmBitBangMotor(unsigned char _en_pin, unsigned char _out1_pin, unsigned char _out2_pin, unsigned char _a_pin, unsigned char _b_pin,
             int _pGain, int _iGain, int _dGain, int _iLimit, unsigned char _deadband, unsigned char _minOutput):
        DIPMotor(_a_pin, _b_pin, _pGain, _iGain, _dGain, _iLimit, _deadband, _minOutput)
    {
        en_pin = _en_pin;
        out1_pin = _out1_pin;
        out2_pin = _out2_pin;
    }

    void init()
    {
        DIPMotor::init();

        /* Output are connected to OPTO, which the pins are low-active */
        digitalWrite(en_pin, HIGH);
        digitalWrite(out1_pin, HIGH);
        digitalWrite(out2_pin, HIGH);
        pinMode(en_pin, OUTPUT);
        pinMode(out1_pin, OUTPUT);
        pinMode(out2_pin, OUTPUT);
    }

    virtual void turnOff()
    {
        DIPMotor::turnOff();
        digitalWrite(en_pin, HIGH);
        analogWrite(out1_pin, 255);
        analogWrite(out2_pin, 255);
    }

    virtual void turnOn()
    {
        DIPMotor::turnOn();
        digitalWrite(en_pin, LOW);
    }
};
