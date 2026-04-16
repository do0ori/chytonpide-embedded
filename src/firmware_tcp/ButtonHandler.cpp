#include "ButtonHandler.h"

// BOOT 버튼 상태
unsigned long bootButtonPressTime = 0;

// BOOT 버튼 체크 (loop에서 실시간 감지)
void checkBootButton() {
  if (digitalRead(0) == LOW) {
    if (!bootButtonPressed) {
      bootButtonPressed = true;
      bootButtonPressTime = millis();
      
      // LCD에 알림 표시
      clearLCD();
      printLCD(10, 100, "Hold for 3 seconds", TFT_YELLOW, 2);
      printLCD(10, 125, "to reset WiFi", TFT_YELLOW, 2);
      lastDisplayedState = WIFI_ERROR;  // 상태 초기화
    }

    // 3초 이상 눌렸는지 체크
    if (millis() - bootButtonPressTime >= 3000) {
      // LCD에 초기화 표시
      clearLCD();
      printLCD(10, 100, "Resetting WiFi...", TFT_CYAN, 2);
      
      wifiManager.resetSettings();
      delay(1000);
      ESP.restart();
    }
  } else {
    if (bootButtonPressed) {
      bootButtonPressed = false;
      // 현재 상태로 LCD 복원
      lastDisplayedState = WIFI_ERROR;  // 상태 초기화하여 다시 그리기
      updateLCD();
    }
  }
}

