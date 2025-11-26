#include "SensorManager.h"
#include <ctype.h>

// 정적 멤버 변수 (인스턴스 포인터 저장용)
static SensorManager* sensorManagerInstance = nullptr;

static constexpr const char* DEFAULT_ILLUMINANCE_VALUE = "0";

SensorManager::SensorManager(const char* baseUrl, const char* endpoint, DeviceID* deviceId)
  : sht31(Adafruit_SHT31()),
    sensorInitialized(false),
    hasValidSample(false),
    lastTemperature(0.0f),
    lastHumidity(0.0f),
    lastSensorSampleMs(0),
    sensorReadIntervalMs(2000),
    serverBaseURL(baseUrl),
    sensorEndpoint(endpoint),
    shouldUploadSensorData(false),
    sensorUploadTimer(nullptr),
    uploadIntervalUs(10ULL * 1000ULL * 1000ULL),
    deviceID(deviceId) {
  sensorManagerInstance = this;
}

SensorManager::~SensorManager() {
  stopUploadTimer();
  sensorManagerInstance = nullptr;
}

bool SensorManager::init() {
  Wire.begin(SHT31_SDA_PIN, SHT31_SCL_PIN);
  delay(100);  // I2C 안정화 대기
  sensorInitialized = sht31.begin(0x44);
  
  if (sensorInitialized) {
    readData();
  }
  
  return sensorInitialized;
}

void SensorManager::update() {
  if (!sensorInitialized) {
    return;
  }

  unsigned long now = millis();
  if (now - lastSensorSampleMs >= sensorReadIntervalMs) {
    if (readData()) {
      lastSensorSampleMs = now;
    }
  }
}

bool SensorManager::readData() {
  if (!sensorInitialized) {
    return false;
  }
  
  float temperature = sht31.readTemperature();
  float humidity = sht31.readHumidity();
  
  if (isnan(temperature) || isnan(humidity)) {
    return false;
  }

  lastTemperature = temperature;
  lastHumidity = humidity;
  lastSensorSampleMs = millis();
  hasValidSample = true;
  return true;
}

void SensorManager::startUploadTimer() {
  if (sensorUploadTimer != nullptr) {
    return;  // 이미 시작됨
  }
  
  const esp_timer_create_args_t timer_args = {
    .callback = &SensorManager::timerCallback,
    .name = "sensor_upload_timer"
  };
  
  esp_timer_create(&timer_args, &sensorUploadTimer);
  esp_timer_start_periodic(sensorUploadTimer, uploadIntervalUs);
}

void SensorManager::stopUploadTimer() {
  if (sensorUploadTimer != nullptr) {
    esp_timer_stop(sensorUploadTimer);
    esp_timer_delete(sensorUploadTimer);
    sensorUploadTimer = nullptr;
  }
}

void SensorManager::processUpload() {
  if (!shouldUploadSensorData) {
    return;  // 업로드 플래그가 설정되지 않음
  }
  
  if (WiFi.status() != WL_CONNECTED) {
    shouldUploadSensorData = false;  // WiFi 미연결 시 플래그 리셋
    return;
  }
  
  shouldUploadSensorData = false;  // 플래그 리셋
  
  if (!hasValidSample) {
    if (!readData()) {
      return;
    }
  }
  
  if (!serverBaseURL || !sensorEndpoint) {
    return;
  }

  HTTPClient http;
  String url = String(serverBaseURL) + sensorEndpoint;
  http.begin(url);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  
  // Device ID 가져오기
  String deviceIdentifier = deviceID->getID();
  
  // form 데이터 생성
  String payload = "serial=";
  payload += deviceIdentifier;
  payload += "&temperature=";
  payload += String(lastTemperature, 2);
  payload += "&humidity=";
  payload += String(lastHumidity, 2);
  payload += "&illuminance=";
  payload += DEFAULT_ILLUMINANCE_VALUE;
  
  int httpCode = http.POST(payload);
  (void)httpCode;
  
  http.end();
}

void SensorManager::setSensorReadIntervalMs(uint32_t intervalMs) {
  if (intervalMs == 0) {
    return;
  }
  sensorReadIntervalMs = intervalMs;
}

void SensorManager::setUploadIntervalMs(uint32_t intervalMs) {
  if (intervalMs == 0) {
    return;
  }

  uploadIntervalUs = static_cast<uint64_t>(intervalMs) * 1000ULL;

  if (sensorUploadTimer != nullptr) {
    esp_timer_stop(sensorUploadTimer);
    esp_timer_start_periodic(sensorUploadTimer, uploadIntervalUs);
  }
}

// 정적 타이머 콜백 함수 (ISR에서 호출됨)
void IRAM_ATTR SensorManager::timerCallback(void* arg) {
  // ISR에서는 플래그만 설정 (HTTP 요청은 시간이 걸리므로 loop()에서 처리)
  if (sensorManagerInstance != nullptr) {
    sensorManagerInstance->shouldUploadSensorData = true;
  }
}

