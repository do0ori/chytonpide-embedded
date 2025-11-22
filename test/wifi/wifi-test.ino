#include <WiFi.h>
#include <WiFiManager.h>
#include <WebServer.h>
#include <DNSServer.h>

WiFiManager wifiManager;

// WiFi 상태
enum WifiState {
  WIFI_CONNECTING,    // WiFi 연결 시도 중
  WIFI_CONFIG_MODE,   // AP 모드 (설정 필요)
  WIFI_CONNECTED,     // WiFi 연결 성공
  WIFI_ERROR          // 에러 상태
};

WifiState currentState = WIFI_CONNECTING;

// 설정 포털 타임아웃 (초)
const int CONFIG_PORTAL_TIMEOUT = 300;  // 5분

// AP 모드 설정
const char* AP_NAME = "ESP32-S3-Setup";
const char* AP_PASSWORD = "";  // 비밀번호 없음

// AP IP 설정
IPAddress apIP(192, 168, 4, 1);
IPAddress gateway(192, 168, 4, 1);
IPAddress subnet(255, 255, 255, 0);

// RGB LED 설정
#ifndef RGB_BUILTIN
  #define RGB_BUILTIN 48  // RGB_BUILTIN이 정의되지 않은 경우 GPIO 48 사용
#endif

#define RGB_BRIGHTNESS 64  // RGB LED 밝기 (0-255)

// BOOT 버튼 상태
unsigned long bootButtonPressTime = 0;
bool bootButtonPressed = false;

// RGB LED 색상 설정 함수
void setLED(int r, int g, int b) {
  neopixelWrite(RGB_BUILTIN, r, g, b);
}

void updateLED() {
  static unsigned long lastBlink = 0;
  static bool blinkState = false;
  unsigned long currentMillis = millis();

  switch (currentState) {
    case WIFI_CONFIG_MODE:
      // 파란색 깜빡임 (AP 모드 - 설정 필요)
      if (currentMillis - lastBlink >= 500) {
        lastBlink = currentMillis;
        blinkState = !blinkState;
        if (blinkState) {
          setLED(0, 0, RGB_BRIGHTNESS);  // 파란색
        } else {
          setLED(0, 0, 0);  // 꺼짐
        }
      }
      break;

    case WIFI_CONNECTING:
      // 노란색 깜빡임 (연결 시도 중)
      if (currentMillis - lastBlink >= 1000) {
        lastBlink = currentMillis;
        blinkState = !blinkState;
        if (blinkState) {
          setLED(RGB_BRIGHTNESS, RGB_BRIGHTNESS, 0);  // 노란색
        } else {
          setLED(0, 0, 0);  // 꺼짐
        }
      }
      break;

    case WIFI_CONNECTED:
      // 녹색 고정 (연결 성공)
      setLED(0, RGB_BRIGHTNESS, 0);
      break;

    case WIFI_ERROR:
      // 빨간색 빠르게 깜빡임 (에러)
      if (currentMillis - lastBlink >= 200) {
        lastBlink = currentMillis;
        blinkState = !blinkState;
        if (blinkState) {
          setLED(RGB_BRIGHTNESS, 0, 0);  // 빨간색
        } else {
          setLED(0, 0, 0);  // 꺼짐
        }
      }
      break;
  }
}

// BOOT 버튼 체크 (loop에서 실시간 감지)
void checkBootButton() {
  if (digitalRead(0) == LOW) {
    if (!bootButtonPressed) {
      bootButtonPressed = true;
      bootButtonPressTime = millis();
      Serial.println("BOOT 버튼 눌림 - 3초간 유지하면 WiFi 설정 초기화...");
    }

    // 3초 이상 눌렸는지 체크
    if (millis() - bootButtonPressTime >= 3000) {
      Serial.println("\nWiFi 설정 초기화!");

      // 초기화 표시 (흰색 5번 깜빡임)
      for (int i = 0; i < 5; i++) {
        setLED(RGB_BRIGHTNESS, RGB_BRIGHTNESS, RGB_BRIGHTNESS);
        delay(200);
        setLED(0, 0, 0);
        delay(200);
      }

      wifiManager.resetSettings();
      Serial.println("재부팅합니다...");
      delay(1000);
      ESP.restart();
    } else {
      // 버튼 누르는 중 표시 (보라색 깜빡임)
      static unsigned long lastPurpleBlink = 0;
      if (millis() - lastPurpleBlink >= 100) {
        lastPurpleBlink = millis();
        static bool purpleState = false;
        purpleState = !purpleState;
        if (purpleState) {
          setLED(RGB_BRIGHTNESS, 0, RGB_BRIGHTNESS);
        } else {
          setLED(0, 0, 0);
        }
      }
    }
  } else {
    if (bootButtonPressed) {
      bootButtonPressed = false;
      Serial.println("BOOT 버튼 해제");
      // 현재 상태로 LED 복원
      updateLED();
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // GPIO 0 (BOOT 버튼) 설정
  pinMode(0, INPUT_PULLUP);

  // RGB LED 초기화
  setLED(0, 0, 0);  // 꺼진 상태로 시작

  Serial.println("\n\n=================================");
  Serial.println("ESP32-S3-R8N16 WiFi Manager");
  Serial.println("=================================");
  Serial.println("RGB LED 상태 표시:");
  Serial.println("- 파란색 깜빡임: AP 모드 (설정 필요)");
  Serial.println("- 노란색 깜빡임: WiFi 연결 시도 중");
  Serial.println("- 녹색 고정: WiFi 연결 성공");
  Serial.println("- 빨간색 깜빡임: 에러");
  Serial.println("- 보라색 깜빡임: BOOT 버튼 누름 중");
  Serial.println("- 흰색 깜빡임: 설정 초기화");
  Serial.println("\nBOOT 버튼을 3초간 누르면");
  Serial.println("WiFi 설정이 초기화됩니다.");
  Serial.println("=================================\n");

  // WiFiManager 설정
  wifiManager.setDebugOutput(true);
  wifiManager.setAPStaticIPConfig(apIP, gateway, subnet);
  wifiManager.setConfigPortalTimeout(CONFIG_PORTAL_TIMEOUT);

  // AP 모드 시작 콜백
  wifiManager.setAPCallback([](WiFiManager *myWiFiManager) {
    currentState = WIFI_CONFIG_MODE;
    setLED(0, 0, RGB_BRIGHTNESS);  // 파란색 고정

    Serial.println("\n=================================");
    Serial.println("설정 모드 진입!");
    Serial.println("=================================");
    Serial.print("AP 이름: ");
    Serial.println(myWiFiManager->getConfigPortalSSID());
    Serial.print("AP IP 주소: ");
    Serial.println(WiFi.softAPIP());
    Serial.println("\n1. 스마트폰/PC에서 WiFi 검색");
    Serial.println("2. 'ESP32-S3-Setup' 연결");
    Serial.println("3. 브라우저에서 192.168.4.1 접속");
    Serial.println("\nRGB LED: 파란색 (고정)");
    Serial.println("※ AP 모드에서는 LED가 깜빡이지 않습니다");
    Serial.println("=================================\n");
  });

  // WiFi 저장 콜백
  wifiManager.setSaveConfigCallback([]() {
    Serial.println("WiFi 설정 저장됨!");
    currentState = WIFI_CONNECTING;
    setLED(RGB_BRIGHTNESS, RGB_BRIGHTNESS, 0);  // 노란색
  });

  Serial.println("WiFi 연결 시도 중...");
  Serial.println("저장된 설정이 없으면 AP 모드로 전환됩니다.\n");

  currentState = WIFI_CONNECTING;
  setLED(RGB_BRIGHTNESS, RGB_BRIGHTNESS, 0);  // 노란색

  // autoConnect는 blocking 함수
  if (!wifiManager.autoConnect(AP_NAME, AP_PASSWORD)) {
    Serial.println("\n설정 타임아웃 또는 연결 실패");
    Serial.println("재부팅합니다...");
    currentState = WIFI_ERROR;

    // 에러 표시 (빨간색 빠르게 깜빡임)
    for (int i = 0; i < 20; i++) {
      setLED(RGB_BRIGHTNESS * 2, 0, 0);  // 빨간색 (더 밝게)
      delay(100);
      setLED(0, 0, 0);
      delay(100);
    }

    ESP.restart();
  }

  // WiFi 연결 성공
  currentState = WIFI_CONNECTED;
  setLED(0, RGB_BRIGHTNESS, 0);  // 녹색

  Serial.println("\n=================================");
  Serial.println("WiFi 연결 성공!");
  Serial.println("=================================");
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());
  Serial.print("IP 주소: ");
  Serial.println(WiFi.localIP());
  Serial.print("게이트웨이: ");
  Serial.println(WiFi.gatewayIP());
  Serial.print("신호 세기: ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");
  Serial.println("\nRGB LED: 녹색 (고정)");
  Serial.println("=================================\n");
}

void loop() {
  // BOOT 버튼 실시간 체크
  checkBootButton();

  // 버튼이 눌려있지 않을 때만 LED 업데이트
  if (!bootButtonPressed) {
    // RGB LED 상태 업데이트
    updateLED();

    // WiFi 연결 상태 모니터링
    static unsigned long lastCheck = 0;
    static bool wasConnected = true;

    if (millis() - lastCheck > 5000) {  // 5초마다 체크
      lastCheck = millis();

      if (WiFi.status() != WL_CONNECTED) {
        if (wasConnected) {
          Serial.println("WiFi 연결 끊김!");
          currentState = WIFI_CONNECTING;
          wasConnected = false;
        }
      } else {
        if (!wasConnected) {
          Serial.println("WiFi 재연결 성공!");
          Serial.print("IP 주소: ");
          Serial.println(WiFi.localIP());
          currentState = WIFI_CONNECTED;
          wasConnected = true;
        }
      }
    }
  }

  delay(10);  // CPU 부하 감소
}
