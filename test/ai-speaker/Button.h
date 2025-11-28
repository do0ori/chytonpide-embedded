#ifndef Button_h
#define Button_h

#define BUTTON_PRESSED 1
#define BUTTON_HOLD 2
#define BUTTON_RELEASED 3

#include "Arduino.h"

class Button
{
public:
    Button(int pin);
    int checkState();

private:
    int _pin;
    int _buttonState;
    int _lastButtonState;
    unsigned long _lastDebounceTime;
    unsigned long _debounceDelay;
};

#endif
