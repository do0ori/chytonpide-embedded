#include <WiFi.h>
#include <WiFiManager.h>
#include <WebServer.h>
#include <DNSServer.h>
#include "WiFiState.h"
#include "LCDDisplay.h"
#include "ButtonHandler.h"
#include "DeviceID.h"
#include "RoboEyesTFT_eSPI.h"
#include "SensorManager.h"
#include "RelayLedController.h"

// 주기 설정 (밀리초)
const uint32_t SENSOR_READ_INTERVAL_MS = 2000;      // 2초마다 센서 데이터 읽기
const uint32_t SENSOR_UPLOAD_INTERVAL_MS = 300000;  // 5분마다 센서 데이터 업로드
const uint32_t LED_CHECK_INTERVAL_MS = 2000;        // 2초마다 LED 상태 확인

WiFiManager wifiManager;
TFT_eSPI tft = TFT_eSPI();
DeviceID deviceID;
TFT_RoboEyes roboEyes(tft, false, 3);  // landscape, rotation 3 (TFT-LCD.ino와 동일)

WifiState currentState = WIFI_CONNECTING;
WifiState lastDisplayedState = WIFI_ERROR;
bool bootButtonPressed = false;

// 서버 URL (ngrok 등 외부 서버)
const char* SERVER_BASE_URL = "https://2542c3beade0.ngrok-free.app";
const char* SENSOR_SERVER_URL = "https://2542c3beade0.ngrok-free.app/sensor/data";
const char* LED_STATE_ENDPOINT = "/led/state";

// 센서/LED 컨트롤러
SensorManager sensorManager(SENSOR_SERVER_URL, &deviceID);
RelayLedController relayLedController(SERVER_BASE_URL, LED_STATE_ENDPOINT, &deviceID);

// 릴레이 핀 (테스트/프로토타입용)
const uint8_t RELAY_SIGNAL_PIN = 48;
const uint8_t RELAY_COM_PIN = 47;

// 설정 포털 타임아웃 (초)
const int CONFIG_PORTAL_TIMEOUT = 300;  // 5분

// AP 모드 설정
const char* AP_NAME = "ESP32-S3-Setup";
const char* AP_PASSWORD = "";  // 비밀번호 없음

// AP IP 설정
IPAddress apIP(192, 168, 4, 1);
IPAddress gateway(192, 168, 4, 1);
IPAddress subnet(255, 255, 255, 0);

void setup() {
  // LCD 초기화
  initLCD();
  printLCD(10, 100, "Initializing...", TFT_WHITE, 2);
  delay(500);

  // 센서/릴레이 모듈 초기화
  if (sensorManager.init()) {
    sensorManager.setSensorReadIntervalMs(SENSOR_READ_INTERVAL_MS);
    sensorManager.setUploadIntervalMs(SENSOR_UPLOAD_INTERVAL_MS);
  }
  relayLedController.begin(RELAY_SIGNAL_PIN, RELAY_COM_PIN);
  relayLedController.setCheckInterval(LED_CHECK_INTERVAL_MS);

  // GPIO 0 (BOOT 버튼) 설정
  pinMode(0, INPUT_PULLUP);

  // WiFiManager 설정
  wifiManager.setDebugOutput(false);  // 디버그 출력 비활성화
  wifiManager.setAPStaticIPConfig(apIP, gateway, subnet);
  wifiManager.setConfigPortalTimeout(CONFIG_PORTAL_TIMEOUT);

  // AP 모드 시작 콜백
  wifiManager.setAPCallback([](WiFiManager *myWiFiManager) {
    currentState = WIFI_CONFIG_MODE;
    lastDisplayedState = WIFI_ERROR;  // 상태 초기화
    displayConfigMode();
  });

  // WiFi 저장 콜백
  wifiManager.setSaveConfigCallback([]() {
    currentState = WIFI_CONNECTING;
    lastDisplayedState = WIFI_ERROR;  // 상태 초기화
    displayConnecting();
  });

  currentState = WIFI_CONNECTING;
  displayConnecting();

  // autoConnect는 blocking 함수
  // 연결 실패 시 (타임아웃 등) false 반환
  if (!wifiManager.autoConnect(AP_NAME, AP_PASSWORD)) {
    // 타임아웃 등 다른 에러
    currentState = WIFI_ERROR;
    displayError();
    delay(3000);
    ESP.restart();
  } else {
    // WiFi 연결 성공
    currentState = WIFI_CONNECTED;
    displayConnected();
    
    // 센서 데이터 업로드 타이머/릴레이 업데이트 시작
    if (sensorManager.isInitialized()) {
      sensorManager.startUploadTimer();
    }
  }
}

void loop() {
  // BOOT 버튼 실시간 체크
  checkBootButton();

  // 버튼이 눌려있지 않을 때만 LCD 업데이트
  if (!bootButtonPressed) {
    // LCD 상태 업데이트
    updateLCD();

    // WiFi 연결 상태 모니터링
    static unsigned long lastCheck = 0;
    static bool wasConnected = true;

    if (millis() - lastCheck > 5000) {  // 5초마다 체크
      lastCheck = millis();

      if (WiFi.status() != WL_CONNECTED) {
        if (wasConnected) {
          currentState = WIFI_CONNECTING;
          wasConnected = false;
          lastDisplayedState = WIFI_ERROR;  // 상태 초기화하여 다시 그리기
          displayConnecting();
        }
      } else {
        if (!wasConnected) {
          currentState = WIFI_CONNECTED;
          wasConnected = true;
          lastDisplayedState = WIFI_ERROR;  // 상태 초기화하여 다시 그리기
          displayConnected();
        }
      }
    }
  }

  // 센서 데이터 주기적 샘플링/업로드 처리
  sensorManager.update();
  sensorManager.processUpload();

  // LED 상태 동기화
  relayLedController.update();

  delay(10);  // CPU 부하 감소
}

