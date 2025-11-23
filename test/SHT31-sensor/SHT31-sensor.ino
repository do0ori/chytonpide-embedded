#include <Wire.h>
#include <Adafruit_SHT31.h>
#include <TFT_eSPI.h>

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

// 센서 연결 상태
bool sensorConnected = false;

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
    } else {
      Serial.println("센서 읽기 오류!");
      tft.fillScreen(TFT_BLACK);
      tft.setTextColor(TFT_RED, TFT_BLACK);
      tft.setTextSize(2);
      tft.setCursor(10, 100);
      tft.println("Read Error!");
    }
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
  
  // 업데이트 시간 표시 (선택사항)
  tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
  tft.setTextSize(1);
  tft.setCursor(10, 220);
  tft.print("Update: ");
  tft.print(millis() / 1000);
  tft.print("s");
}
