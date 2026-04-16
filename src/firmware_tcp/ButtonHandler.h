#ifndef BUTTON_HANDLER_H
#define BUTTON_HANDLER_H

#include <WiFiManager.h>
#include "LCDDisplay.h"

extern WiFiManager wifiManager;
extern bool bootButtonPressed;

// BOOT 버튼 체크 (loop에서 실시간 감지)
void checkBootButton();

#endif

