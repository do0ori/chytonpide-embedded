#ifndef RELAY_LED_CONTROLLER_H
#define RELAY_LED_CONTROLLER_H

#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include "DeviceID.h"

/**
 * RelayLedController
 * -------------------
 * 서버에서 장치의 LED 상태를 주기적으로 조회하여 릴레이를 제어한다.
 * - /led/state?device_id=... 엔드포인트를 호출
 * - WiFi 연결 상태가 유지될 때만 동작
 */
class RelayLedController {
 public:
  RelayLedController(const char* baseUrl, const char* stateEndpoint, DeviceID* device);

  // 릴레이 핀 초기화 (signal 핀 필수, COM 핀은 선택)
  void begin(uint8_t relayPin, uint8_t relayComPin = 0xFF);

  // loop()에서 반복 호출하여 주기적으로 서버를 확인
  void update();

  void setCheckInterval(unsigned long intervalMs) { checkIntervalMs = intervalMs; }

 private:
  const char* serverBaseUrl;
  const char* ledStateEndpoint;
  DeviceID* device;

  uint8_t relaySignalPin;
  uint8_t relayComPin;
  bool currentRelayState;
  bool initialized;

  unsigned long lastCheckTime;
  unsigned long checkIntervalMs;

  String urlEncode(const String& raw) const;
  void ensurePinsInitialized();
  void fetchAndApplyLedState();
  int parseLedStateFromJson(const String& json) const;
  void setRelayState(bool turnOn);
};

#endif

