#include <Wire.h>
#include <Adafruit_SHT31.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <HTTPClient.h>

// I2C 핀 설정 (SHT31 센서)
#define SDA_PIN 4
#define SCL_PIN 5

// TFT LCD 객체
TFT_eSPI tft = TFT_eSPI();

// SHT31 센서 객체
Adafruit_SHT31 sht31 = Adafruit_SHT31();

// 센서 읽기 간격 (밀리초)
unsigned long lastReadTime = 0;
const unsigned long readInterval = 2000; // 2초마다 읽기

// 서버 업로드 간격 (밀리초)
unsigned long lastUploadTime = 0;
const unsigned long uploadInterval = 10000; // 10초마다 업로드

// 센서 연결 상태
bool sensorConnected = false;
bool wifiConnected = false;

// 서버 URL
const char* SERVER_URL = "https://2b7b6839efed.ngrok-free.app/sensor/data";

// WiFi 설정 (하드코딩)
const char* WIFI_SSID = "YOUR_WIFI_SSID";      // WiFi SSID 입력
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";  // WiFi 비밀번호 입력

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("SHT31 온습도 센서 테스트 시작");
  
  // I2C 초기화 (SDA=GPIO4, SCL=GPIO5)
  Wire.begin(SDA_PIN, SCL_PIN);
  
  // LCD 초기화
  tft.init();
  tft.setRotation(3); // 가로 모드 (320x240)
  tft.fillScreen(TFT_BLACK);
  
  // LCD 초기 메시지
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.println("SHT31 Sensor");
  tft.setCursor(10, 40);
  tft.println("Initializing...");
  
  // SHT31 센서 초기화
  if (!sht31.begin(0x44)) { // 기본 I2C 주소는 0x44
    Serial.println("SHT31 센서를 찾을 수 없습니다!");
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.setCursor(10, 70);
    tft.println("Sensor Error!");
    sensorConnected = false;
  } else {
    Serial.println("SHT31 센서 연결 성공!");
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.setCursor(10, 70);
    tft.println("Sensor OK!");
    sensorConnected = true;
  }
  
  delay(1000);
  
  // WiFi 연결
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.println("Connecting WiFi...");
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("WiFi 연결 성공!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    wifiConnected = true;
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.setCursor(10, 40);
    tft.println("WiFi OK!");
    delay(1000);
  } else {
    Serial.println();
    Serial.println("WiFi 연결 실패!");
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.setCursor(10, 40);
    tft.println("WiFi Failed!");
    delay(3000);
    ESP.restart();
  }
  
  // 화면 지우기
  tft.fillScreen(TFT_BLACK);
}

void loop() {
  if (!sensorConnected) {
    // 센서가 연결되지 않은 경우 에러 메시지 표시
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.setTextSize(2);
    tft.setCursor(10, 100);
    tft.println("Sensor Not");
    tft.setCursor(10, 130);
    tft.println("Connected!");
    delay(5000);
    return;
  }
  
  // 주기적으로 센서 읽기
  if (millis() - lastReadTime >= readInterval) {
    lastReadTime = millis();
    
    // 온도와 습도 읽기
    float temperature = sht31.readTemperature();
    float humidity = sht31.readHumidity();
    
    // 유효성 검사
    if (!isnan(temperature) && !isnan(humidity)) {
      // 시리얼 모니터에 출력
      Serial.print("온도: ");
      Serial.print(temperature);
      Serial.print(" °C, 습도: ");
      Serial.print(humidity);
      Serial.println(" %");
      
      // LCD 화면 업데이트
      updateDisplay(temperature, humidity);
      
      // 서버로 데이터 전송 (10초마다)
      if (wifiConnected && (millis() - lastUploadTime >= uploadInterval)) {
        uploadToServer(temperature, humidity);
        lastUploadTime = millis();
      }
    } else {
      Serial.println("센서 읽기 오류!");
      tft.fillScreen(TFT_BLACK);
      tft.setTextColor(TFT_RED, TFT_BLACK);
      tft.setTextSize(2);
      tft.setCursor(10, 100);
      tft.println("Read Error!");
    }
  }
  
  // WiFi 재연결 체크
  if (WiFi.status() != WL_CONNECTED) {
    wifiConnected = false;
  } else if (!wifiConnected) {
    wifiConnected = true;
    Serial.println("WiFi 재연결됨!");
  }
}

void updateDisplay(float temp, float humidity) {
  // 화면 지우기
  tft.fillScreen(TFT_BLACK);
  
  // 제목
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.println("SHT31 Sensor");
  
  // 구분선
  tft.drawLine(10, 40, 310, 40, TFT_DARKGREY);
  
  // 온도 표시
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 60);
  tft.print("Temperature:");
  
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(3);
  tft.setCursor(10, 90);
  tft.print(temp, 1);
  tft.setTextSize(2);
  tft.print(" ");
  tft.setTextSize(3);
  tft.print("C");
  
  // 습도 표시
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 140);
  tft.print("Humidity:");
  
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(3);
  tft.setCursor(10, 170);
  tft.print(humidity, 1);
  tft.setTextSize(2);
  tft.print(" ");
  tft.setTextSize(3);
  tft.print("%");
  
  // 업데이트 시간 표시
  tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
  tft.setTextSize(1);
  tft.setCursor(10, 220);
  tft.print("Update: ");
  tft.print(millis() / 1000);
  tft.print("s");
  
  // 업로드 상태 표시
  if (wifiConnected) {
    unsigned long timeSinceUpload = millis() - lastUploadTime;
    if (timeSinceUpload < uploadInterval) {
      unsigned long remaining = (uploadInterval - timeSinceUpload) / 1000;
      tft.setCursor(200, 220);
      tft.setTextColor(TFT_GREEN, TFT_BLACK);
      tft.print("Up:");
      tft.print(remaining);
      tft.print("s");
    }
  } else {
    tft.setCursor(200, 220);
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.print("No WiFi");
  }
}

// 서버로 센서 데이터 전송
void uploadToServer(float temperature, float humidity) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skipping upload");
    return;
  }
  
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  
  // Device ID 생성 (MAC 주소 기반)
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char deviceId[18];
  snprintf(deviceId, sizeof(deviceId), "%02X%02X%02X%02X%02X%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  
  // JSON 페이로드 생성
  String payload = "{";
  payload += "\"temperature\":";
  payload += String(temperature, 2);
  payload += ",\"humidity\":";
  payload += String(humidity, 2);
  payload += ",\"device_id\":\"";
  payload += deviceId;
  payload += "\"";
  payload += "}";
  
  Serial.print("Uploading to server: ");
  Serial.println(SERVER_URL);
  Serial.print("Payload: ");
  Serial.println(payload);
  
  int httpCode = http.POST(payload);
  
  if (httpCode > 0) {
    Serial.printf("HTTP Response code: %d\n", httpCode);
    if (httpCode == HTTP_CODE_OK) {
      String response = http.getString();
      Serial.print("Server response: ");
      Serial.println(response);
    }
  } else {
    Serial.printf("HTTP POST failed, error: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
}
