#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include <Wire.h>
#include <Adafruit_SHT31.h>
#include <HTTPClient.h>
#include <esp_timer.h>
#include <WiFi.h>
#include "DeviceID.h"

class SensorManager {
private:
  // SHT31 센서 설정
  static const uint8_t SHT31_SDA_PIN = 4;
  static const uint8_t SHT31_SCL_PIN = 5;
  
  Adafruit_SHT31 sht31;
  bool sensorInitialized;
  bool hasValidSample;
  float lastTemperature;
  float lastHumidity;
  unsigned long lastSensorSampleMs;
  uint32_t sensorReadIntervalMs;
  
  // 서버 설정
  const char* serverBaseURL;
  const char* sensorEndpoint;
  bool shouldUploadSensorData;  // 타이머 인터럽트에서 설정하는 플래그
  esp_timer_handle_t sensorUploadTimer;
  uint64_t uploadIntervalUs;
  
  // DeviceID 참조
  DeviceID* deviceID;
  
  // 타이머 콜백 (정적 함수)
  static void IRAM_ATTR timerCallback(void* arg);
  
public:
  SensorManager(const char* baseUrl, const char* endpoint, DeviceID* deviceId);
  ~SensorManager();
  
  // 센서 초기화
  bool init();
  void update();
  
  // 센서 데이터 읽기
  bool readData();
  
  // 최신 센서 데이터 가져오기
  float getTemperature() const { return lastTemperature; }
  float getHumidity() const { return lastHumidity; }
  bool isInitialized() const { return sensorInitialized; }
  
  // 서버 업로드 타이머 시작/중지
  void startUploadTimer();
  void stopUploadTimer();
  
  // 서버로 데이터 전송 (loop()에서 호출)
  void processUpload();

  // 주기 설정
  void setSensorReadIntervalMs(uint32_t intervalMs);
  void setUploadIntervalMs(uint32_t intervalMs);
};

#endif

