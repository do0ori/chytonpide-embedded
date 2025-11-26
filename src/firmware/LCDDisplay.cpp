#include "LCDDisplay.h"

// RoboEyes 관련 전역 변수
// roboEyes는 firmware.ino에서 전역 변수로 선언됨
bool roboEyesInitialized = false;
unsigned long wifiConnectedTime = 0;
bool showFace = false;
const unsigned long FACE_DISPLAY_DELAY = 5000;  // 5초 후 얼굴 표시

// LCD 화면 초기화 및 기본 설정
void initLCD() {
  tft.init();
  tft.setRotation(3);  // 가로 방향 (320x240)
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(TL_DATUM);  // Top-Left 기준
}

// LCD 화면 지우기
void clearLCD() {
  tft.fillScreen(TFT_BLACK);
}

// LCD에 텍스트 출력 (줄바꿈 지원)
void printLCD(int x, int y, const char* text, uint16_t color, uint8_t size) {
  tft.setTextColor(color, TFT_BLACK);
  tft.setTextSize(size);
  tft.setCursor(x, y);
  tft.print(text);
}

// WiFi 설정 모드 화면 표시
void displayConfigMode() {
  // 상태가 변경되지 않았으면 다시 그리지 않음
  if (lastDisplayedState == WIFI_CONFIG_MODE) {
    return;
  }
  
  clearLCD();
  
  printLCD(10, 10, "WiFi Setup Mode", TFT_CYAN, 3);
  printLCD(10, 40, "=======================", TFT_CYAN, 2);
  
  printLCD(10, 65, "AP Name:", TFT_YELLOW, 2);
  printLCD(10, 85, AP_NAME, TFT_WHITE, 2);
  
  printLCD(10, 110, "AP IP:", TFT_YELLOW, 2);
  printLCD(10, 130, "192.168.4.1", TFT_WHITE, 2);
  
  printLCD(10, 155, "Instructions:", TFT_GREEN, 2);
  printLCD(10, 175, "1. Connect to WiFi", TFT_WHITE, 2);
  printLCD(10, 195, "2. Open browser", TFT_WHITE, 2);
  printLCD(10, 215, "3. Go to 192.168.4.1", TFT_WHITE, 2);
  
  lastDisplayedState = WIFI_CONFIG_MODE;
}

// WiFi 연결 중 화면 표시
void displayConnecting() {
  static unsigned long lastBlink = 0;
  static bool blinkState = false;
  unsigned long currentMillis = millis();
  
  // 500ms마다 깜빡임
  if (currentMillis - lastBlink >= 500) {
    lastBlink = currentMillis;
    blinkState = !blinkState;
    
    clearLCD();
    printLCD(10, 10, "WiFi Connecting", TFT_YELLOW, 3);
    printLCD(10, 40, "=======================", TFT_YELLOW, 2);
    
    if (blinkState) {
      // 저장된 SSID 가져오기 시도
      String ssid = WiFi.SSID();
      if (ssid.length() == 0) {
        // Preferences에서 직접 가져오기 시도
        Preferences prefs;
        prefs.begin("wifi", true);
        ssid = prefs.getString("ssid", "");
        prefs.end();
      }
      
      if (ssid.length() > 0) {
        // SSID가 있으면 표시
        if (ssid.length() > 20) {
          ssid = ssid.substring(0, 17) + "...";
        }
        printLCD(10, 80, "Connecting to:", TFT_WHITE, 2);
        printLCD(10, 105, ssid.c_str(), TFT_CYAN, 2);
      } else {
        // SSID가 없으면 기본 메시지
        printLCD(10, 80, "Please wait...", TFT_WHITE, 2);
        printLCD(10, 105, "Connecting...", TFT_WHITE, 2);
      }
    }
  }
}

// WiFi 연결 성공 화면 표시
void displayConnected() {
  // 상태가 변경되지 않았으면 다시 그리지 않음 (깜빡임 방지)
  if (lastDisplayedState == WIFI_CONNECTED) {
    return;
  }
  
  clearLCD();
  
  printLCD(10, 10, "WiFi Connected!", TFT_GREEN, 3);
  printLCD(10, 40, "=======================", TFT_GREEN, 2);
  
  // Device ID 표시
  String deviceId = deviceID.getID();
  String shortId = deviceID.getShortID();
  printLCD(10, 65, "Device ID:", TFT_YELLOW, 2);
  if (deviceId.length() > 16) {
    // 긴 ID는 짧은 버전 표시
    printLCD(10, 85, shortId.c_str(), TFT_WHITE, 2);
  } else {
    printLCD(10, 85, deviceId.c_str(), TFT_WHITE, 2);
  }
  
  printLCD(10, 110, "SSID:", TFT_YELLOW, 2);
  String ssid = WiFi.SSID();
  if (ssid.length() > 18) {
    ssid = ssid.substring(0, 15) + "...";
  }
  printLCD(10, 130, ssid.c_str(), TFT_WHITE, 2);
  
  printLCD(10, 155, "IP:", TFT_YELLOW, 2);
  printLCD(10, 175, WiFi.localIP().toString().c_str(), TFT_WHITE, 2);
  
  printLCD(10, 200, "Signal:", TFT_YELLOW, 2);
  char rssiStr[20];
  snprintf(rssiStr, sizeof(rssiStr), "%d dBm", WiFi.RSSI());
  printLCD(10, 220, rssiStr, TFT_WHITE, 2);
  
  lastDisplayedState = WIFI_CONNECTED;
  
  // WiFi 연결 시간 기록 및 얼굴 표시 타이머 시작
  wifiConnectedTime = millis();
  showFace = false;
}

// 에러 화면 표시
void displayError() {
  // 상태가 변경되지 않았으면 다시 그리지 않음
  if (lastDisplayedState == WIFI_ERROR) {
    return;
  }
  
  clearLCD();
  
  printLCD(10, 10, "WiFi Error!", TFT_RED, 3);
  printLCD(10, 40, "============", TFT_RED, 2);
  printLCD(10, 70, "Connection failed", TFT_WHITE, 2);
  printLCD(10, 95, "or timeout", TFT_WHITE, 2);
  printLCD(10, 130, "Rebooting...", TFT_YELLOW, 2);
  
  lastDisplayedState = WIFI_ERROR;
}

// RoboEyes 초기화
void initRoboEyes() {
  if (!roboEyesInitialized) {
    // TFT는 이미 initLCD()에서 초기화되었으므로, RoboEyes만 초기화
    // roboEyes는 firmware.ino에서 전역 변수로 선언되어 있음
    
    // RoboEyes 화면 크기 (landscape) - TFT-LCD.ino와 동일
    roboEyes.setScreenSize(320, 240);
    
    // 50 FPS - TFT-LCD.ino와 동일
    roboEyes.begin(50);
    
    roboEyes.setColors(TFT_WHITE, TFT_BLACK);
    
    // 눈 크기, 위치 (가로용) - TFT-LCD.ino와 동일
    roboEyes.setWidth(60, 60);
    roboEyes.setHeight(60, 60);
    roboEyes.setSpacebetween(40);  // 가로형 화면은 눈 사이 조금 더 넓게
    roboEyes.setBorderradius(10, 10);
    
    // 자동 깜빡임 + idle (마지막 두 파라미터: X축 범위, Y축 범위) - TFT-LCD.ino와 동일
    roboEyes.setAutoblinker(true, 2, 1);
    roboEyes.setIdleMode(true, 4, 1, 15, 15);  // 가운데 기준 ±15픽셀 범위
    
    // 기본 감정 설정 (DEFAULT) - 나중에 STT/TTS/LLM에서 감정을 받아서 설정할 예정
    roboEyes.setMood(DEFAULT);
    
    roboEyesInitialized = true;
  }
}

// 얼굴 표시 시작
void startFaceDisplay() {
  if (!roboEyesInitialized) {
    initRoboEyes();
  }
  showFace = true;
}

// LCD 업데이트 함수
void updateLCD() {
  // WiFi 연결 후 일정 시간이 지나면 얼굴 표시
  if (currentState == WIFI_CONNECTED && wifiConnectedTime > 0) {
    // 얼굴 표시 시간이 되었는지 확인
    if (!showFace && (millis() - wifiConnectedTime >= FACE_DISPLAY_DELAY)) {
      startFaceDisplay();
    }
    
    // 얼굴 표시 모드
    if (showFace && roboEyesInitialized) {
      roboEyes.update();
      return;
    }
    
    // 얼굴 표시 전에는 연결 정보 화면 유지 (상태 변경 시에만 다시 그리기)
    if (currentState != lastDisplayedState) {
      displayConnected();
    }
    return;
  }
  
  // 연결 중일 때만 깜빡임 효과 (의도된 동작)
  if (currentState == WIFI_CONNECTING) {
    displayConnecting();
    lastDisplayedState = WIFI_CONNECTING;
    return;
  }
  
  // 다른 상태는 상태가 변경될 때만 업데이트 (깜빡임 방지)
  if (currentState != lastDisplayedState) {
    switch (currentState) {
      case WIFI_CONFIG_MODE:
        displayConfigMode();
        break;
      case WIFI_CONNECTED:
        displayConnected();
        break;
      case WIFI_ERROR:
        displayError();
        break;
      default:
        break;
    }
  }
}

