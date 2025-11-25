#include <WiFi.h>
#include <HTTPClient.h>

// 릴레이 핀 설정
#define RELAY_S_PIN 48   // Signal 핀
#define RELAY_COM_PIN 47 // Common 핀 (일반적으로 GND에 연결, 코드에서는 사용 안 함)

// 서버 설정
const char* SERVER_URL = "https://2542c3beade0.ngrok-free.app";  // 서버 기본 URL
const char* LED_STATE_ENDPOINT = "/led/state";  // LED 상태 조회 엔드포인트

// 서버 조회 간격 (밀리초)
unsigned long lastCheckTime = 0;
const unsigned long checkInterval = 2000; // 2초마다 서버에서 LED 상태 확인

// WiFi 설정 (하드코딩)
const char* WIFI_SSID = "YOUR_WIFI_SSID";      // WiFi SSID 입력
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";  // WiFi 비밀번호 입력


// 상태 변수
bool wifiConnected = false;
bool currentLedState = false;  // 현재 LED 상태 (릴레이 상태)
String deviceId = "";  // 디바이스 ID (MAC 주소 기반)

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("릴레이 LED 제어 테스트 시작");
  
  // 릴레이 핀 초기화
  pinMode(RELAY_S_PIN, OUTPUT);
  digitalWrite(RELAY_S_PIN, LOW);  // 초기 상태: LED 꺼짐
  Serial.println("릴레이 핀 초기화 완료 (GPIO48)");
  
  // Device ID 생성 (Efuse MAC 주소 기반 - 64비트를 16진수 문자열로)
  uint64_t chipid = ESP.getEfuseMac();
  char deviceIdBuffer[17];
  snprintf(deviceIdBuffer, sizeof(deviceIdBuffer), "%016llX", chipid);
  deviceId = String(deviceIdBuffer);
  Serial.print("Device ID: ");
  Serial.println(deviceId);
  
  // WiFi 연결
  Serial.println("WiFi 연결 중...");
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
  } else {
    Serial.println();
    Serial.println("WiFi 연결 실패!");
    delay(3000);
    ESP.restart();
  }
  
  Serial.println("초기화 완료");
  Serial.println("서버에서 LED 상태를 주기적으로 확인합니다...");
}

void loop() {
  // WiFi 재연결 체크
  if (WiFi.status() != WL_CONNECTED) {
    if (wifiConnected) {
      Serial.println("WiFi 연결 끊김!");
      wifiConnected = false;
    }
    // WiFi 재연결 시도
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    delay(1000);
    return;
  } else if (!wifiConnected) {
    Serial.println("WiFi 재연결됨!");
    wifiConnected = true;
  }
  
  // 주기적으로 서버에서 LED 상태 확인
  if (millis() - lastCheckTime >= checkInterval) {
    lastCheckTime = millis();
    checkLedStateFromServer();
  }
  
  delay(100);  // CPU 부하 감소
}

// URL 인코딩 함수 (간단한 버전)
String urlEncode(String str) {
  String encoded = "";
  char c;
  for (int i = 0; i < str.length(); i++) {
    c = str.charAt(i);
    if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
      encoded += c;
    } else {
      encoded += "%";
      if (c < 16) encoded += "0";
      encoded += String(c, HEX);
    }
  }
  return encoded;
}

// 서버에서 LED 상태 확인
void checkLedStateFromServer() {
  if (!wifiConnected) {
    return;
  }
  
  HTTPClient http;
  // device_id를 URL 인코딩하여 전송
  String encodedDeviceId = urlEncode(deviceId);
  String url = String(SERVER_URL) + LED_STATE_ENDPOINT + "?device_id=" + encodedDeviceId;
  
  Serial.print("요청 URL: ");
  Serial.println(url);
  
  http.begin(url);
  
  int httpCode = http.GET();
  
  if (httpCode > 0) {
    if (httpCode == HTTP_CODE_OK) {
      String response = http.getString();
      Serial.print("서버 응답: ");
      Serial.println(response);
      
      // 간단한 JSON 파싱 (ArduinoJson 없이)
      // 응답 형식: {"status":"success","led_state":{"device_id":"...","led_on":true/false,"updated_at":"..."}}
      int parsedState = parseLedStateFromJson(response);
      
      if (parsedState != -1) {  // 파싱 성공
        bool serverLedState = (parsedState == 1);
        
        // 상태가 변경되었는지 확인
        if (serverLedState != currentLedState) {
          currentLedState = serverLedState;
          setRelayState(currentLedState);
          
          Serial.print("LED 상태 변경: ");
          Serial.println(currentLedState ? "ON" : "OFF");
        }
      } else {
        Serial.println("JSON 파싱 실패 또는 led_state 정보 없음");
      }
    } else {
      Serial.printf("HTTP GET 실패, 코드: %d\n", httpCode);
    }
  } else {
    Serial.printf("HTTP GET 실패, 오류: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
}

// JSON에서 LED 상태 파싱 (간단한 문자열 파싱)
// -1: 파싱 실패, 0: false, 1: true
int parseLedStateFromJson(String json) {
  // "led_on": 다음의 true/false 찾기
  int ledOnIndex = json.indexOf("\"led_on\":");
  if (ledOnIndex == -1) {
    return -1;  // led_on 필드를 찾을 수 없음
  }
  
  // "led_on": 다음의 값 찾기
  int valueStart = json.indexOf(':', ledOnIndex) + 1;
  
  // 공백 건너뛰기
  while (valueStart < json.length() && (json.charAt(valueStart) == ' ' || json.charAt(valueStart) == '\t')) {
    valueStart++;
  }
  
  // true 또는 false 확인
  if (json.substring(valueStart, valueStart + 4) == "true") {
    return 1;
  } else if (json.substring(valueStart, valueStart + 5) == "false") {
    return 0;
  }
  
  return -1;  // 파싱 실패
}

// 릴레이 상태 설정 (LED 제어)
void setRelayState(bool ledOn) {
  // 릴레이는 HIGH일 때 켜짐 (일반적으로)
  // 만약 반대라면 !ledOn으로 변경
  digitalWrite(RELAY_S_PIN, ledOn ? HIGH : LOW);
  
  Serial.print("릴레이 상태: ");
  Serial.println(ledOn ? "ON (LED 켜짐)" : "OFF (LED 꺼짐)");
}
