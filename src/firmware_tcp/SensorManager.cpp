#include "SensorManager.h"

// 정적 멤버 변수 (인스턴스 포인터 저장용)
static SensorManager* sensorManagerInstance = nullptr;

SensorManager::SensorManager()
  : sht31(Adafruit_SHT31()),
    sensorInitialized(false),
    hasValidSample(false),
    lastTemperature(0.0f),
    lastHumidity(0.0f),
    lastSensorSampleMs(0),
    sensorReadIntervalMs(2000),
    shouldUploadSensorData(false),
    sensorUploadTimer(nullptr),
    uploadIntervalUs(10ULL * 1000ULL * 1000ULL) {
  sensorManagerInstance = this;
}

SensorManager::~SensorManager() {
  stopUploadTimer();
  sensorManagerInstance = nullptr;
}

bool SensorManager::init() {
  Wire.begin(SHT31_SDA_PIN, SHT31_SCL_PIN);
  delay(100);
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
    return;
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

void SensorManager::processUpload(TcpDeviceClient& tcpClient) {
  if (!shouldUploadSensorData) {
    return;
  }

  shouldUploadSensorData = false;

  if (!hasValidSample) {
    if (!readData()) {
      return;
    }
  }

  tcpClient.sendSensorData(lastTemperature, lastHumidity, 0);
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
  if (sensorManagerInstance != nullptr) {
    sensorManagerInstance->shouldUploadSensorData = true;
  }
}
