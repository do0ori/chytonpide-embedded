#include <WiFi.h>
#include <WiFiManager.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <ArduinoJson.h>
#include "WiFiState.h"
#include "LCDDisplay.h"
#include "ButtonHandler.h"
#include "DeviceID.h"
#include "RoboEyesTFT_eSPI.h"
#include "TcpDeviceClient.h"
#include "SensorManager.h"
#include "RelayLedController.h"
#include "FaceEmotionController.h"

// --- 주기 설정 ---
const uint32_t SENSOR_READ_INTERVAL_MS = 10000;      // 10초마다 센서 읽기
const uint32_t SENSOR_UPLOAD_INTERVAL_MS = 30000;     // 30초마다 센서 업로드

// --- TCP 서버 설정 ---
const char* TCP_SERVER_HOST = "192.168.0.27";  // 로컬 테스트 서버 IP (PC Wi-Fi)
const uint16_t TCP_SERVER_PORT = 9000;

// --- 프로토타입 고정 시리얼 ID ---
const char* PROTOTYPE_SERIAL_ID = "xJN2wsF850yqWQfBUkGP";

// --- 하드웨어 핀 ---
const uint8_t RELAY_SIGNAL_PIN = 48;
const uint8_t RELAY_COM_PIN = 47;

// --- WiFi 설정 ---
const int CONFIG_PORTAL_TIMEOUT = 300;
const char* AP_NAME = "ESP32-S3-Setup";
const char* AP_PASSWORD = "";
IPAddress apIP(192, 168, 4, 1);
IPAddress gateway(192, 168, 4, 1);
IPAddress subnet(255, 255, 255, 0);

// --- 글로벌 객체 ---
WiFiManager wifiManager;
TFT_eSPI tft = TFT_eSPI();
DeviceID deviceID;
TFT_RoboEyes roboEyes(tft, false, 3);

WifiState currentState = WIFI_CONNECTING;
WifiState lastDisplayedState = WIFI_ERROR;
bool bootButtonPressed = false;

// TCP 기반 객체
TcpDeviceClient tcpClient(TCP_SERVER_HOST, TCP_SERVER_PORT, PROTOTYPE_SERIAL_ID);
SensorManager sensorManager;
RelayLedController relayLedController;
FaceEmotionController faceEmotionController(&roboEyes);

// --- state_update 콜백 ---
void onStateUpdate(bool hasLed, bool isLedOn, bool hasFace, const String& face) {
  if (hasLed) {
    relayLedController.applyLedState(isLedOn);
  }
  if (hasFace) {
    faceEmotionController.applyFace(face);
  }
}

// --- Setup ---
void setup() {
  Serial.begin(115200);
  delay(100);

  // 프로토타입 고정 시리얼 ID 설정
  deviceID.clearCustomID();
  delay(50);
  deviceID.setCustomID(PROTOTYPE_SERIAL_ID);

  // LCD 초기화
  initLCD();
  printLCD(10, 100, "Initializing...", TFT_WHITE, 2);
  delay(500);

  // 센서 초기화
  if (sensorManager.init()) {
    sensorManager.setSensorReadIntervalMs(SENSOR_READ_INTERVAL_MS);
    sensorManager.setUploadIntervalMs(SENSOR_UPLOAD_INTERVAL_MS);
  }

  // 릴레이 초기화
  relayLedController.begin(RELAY_SIGNAL_PIN, RELAY_COM_PIN);

  // TCP 콜백 등록
  tcpClient.onStateUpdate(onStateUpdate);

  // GPIO 0 (BOOT 버튼) 설정
  pinMode(0, INPUT_PULLUP);

  // WiFiManager 설정
  wifiManager.setDebugOutput(false);
  wifiManager.setAPStaticIPConfig(apIP, gateway, subnet);
  wifiManager.setConfigPortalTimeout(CONFIG_PORTAL_TIMEOUT);

  wifiManager.setAPCallback([](WiFiManager *myWiFiManager) {
    currentState = WIFI_CONFIG_MODE;
    lastDisplayedState = WIFI_ERROR;
    displayConfigMode();
  });

  wifiManager.setSaveConfigCallback([]() {
    currentState = WIFI_CONNECTING;
    lastDisplayedState = WIFI_ERROR;
    displayConnecting();
  });

  currentState = WIFI_CONNECTING;
  displayConnecting();

  if (!wifiManager.autoConnect(AP_NAME, AP_PASSWORD)) {
    currentState = WIFI_ERROR;
    displayError();
    delay(3000);
    ESP.restart();
  } else {
    currentState = WIFI_CONNECTED;
    displayConnected();

    // 센서 업로드 타이머 시작
    if (sensorManager.isInitialized()) {
      sensorManager.startUploadTimer();
    }

    // TCP 연결 시작
    tcpClient.begin();
  }
}

// --- Loop ---
void loop() {
  // BOOT 버튼 체크
  checkBootButton();

  // LCD 업데이트 (항상 즉시 실행)
  if (!bootButtonPressed) {
    updateLCD();

    // WiFi 상태 모니터링 (5초 간격)
    static unsigned long lastCheck = 0;
    static bool wasConnected = true;

    if (millis() - lastCheck > 5000) {
      lastCheck = millis();

      if (WiFi.status() != WL_CONNECTED) {
        if (wasConnected) {
          currentState = WIFI_CONNECTING;
          wasConnected = false;
          lastDisplayedState = WIFI_ERROR;
          displayConnecting();
        }
      } else {
        if (!wasConnected) {
          currentState = WIFI_CONNECTED;
          wasConnected = true;
          lastDisplayedState = WIFI_ERROR;
          displayConnected();
        }
      }
    }
  }

  // TCP + 센서 처리 (WiFi 연결 시에만)
  if (WiFi.status() == WL_CONNECTED) {
    tcpClient.poll();                          // 비차단: 수신 확인 + 콜백
    sensorManager.update();                    // 센서 I2C 읽기
    sensorManager.processUpload(tcpClient);    // TCP로 센서 데이터 전송
  }

  delay(10);
}
