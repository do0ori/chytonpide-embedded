#include "Arduino.h"
#include "Button.h"

Button::Button(int pin)
{
    _pin = pin;
    pinMode(_pin, INPUT_PULLUP);
    _buttonState = HIGH;
    _lastButtonState = HIGH;
    _lastDebounceTime = 0;
    _debounceDelay = 50;
}

int Button::checkState()
{
    int reading = digitalRead(_pin);

    if (reading != _lastButtonState)
    {
        _lastDebounceTime = millis();
    }

    if ((millis() - _lastDebounceTime) > _debounceDelay)
    {
        if (reading != _buttonState)
        {
            _buttonState = reading;

            if (_buttonState == LOW)
            {
                return 1; // 버튼 눌림
            }
            else
            {
                return 3; // 버튼 뗌
            }
        }
    }

    _lastButtonState = reading;
    if (_buttonState == LOW)
    {
        return 2; // 상태 2: 버튼이 LOW 상태를 유지
    }

    return 0; // 상태 변화 없음
}
