#ifndef FACE_EMOTION_CONTROLLER_H
#define FACE_EMOTION_CONTROLLER_H

#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <TFT_eSPI.h>
#include "DeviceID.h"
#include "RoboEyesTFT_eSPI.h"

/**
 * FaceEmotionController
 * -------------------
 * 서버에서 장치의 Face Emotion 상태를 주기적으로 조회하여 화면 얼굴 상태를 동기화한다.
 * - GET /face_emotion?device_id=... 엔드포인트를 호출
 * - WiFi 연결 상태가 유지될 때만 동작
 * - 기본값은 DEFAULT (설정되지 않은 경우)
 * - TFT-LCD.ino처럼 MoodPreset을 사용하여 각 감정마다 적절한 설정을 적용
 */
struct MoodPreset {
  uint8_t mood;
  uint16_t color;
  uint16_t bgColor;
  uint8_t eyeWidth;
  uint8_t eyeHeight;
  uint8_t borderRadius;
  int spaceBetween;
};

class FaceEmotionController {
 public:
  FaceEmotionController(const char* baseUrl, const char* emotionEndpoint, DeviceID* device, TFT_RoboEyes* roboEyes);

  // loop()에서 반복 호출하여 주기적으로 서버를 확인
  void update();

  void setCheckInterval(unsigned long intervalMs) { checkIntervalMs = intervalMs; }

 private:
  const char* serverBaseUrl;
  const char* emotionEndpoint;
  DeviceID* device;
  TFT_RoboEyes* roboEyes;

  String currentEmotion;
  bool initialized;

  unsigned long lastCheckTime;
  unsigned long checkIntervalMs;

  String urlEncode(const String& raw) const;
  void fetchAndApplyEmotion();
  String parseEmotionFromJson(const String& json) const;
  uint8_t emotionStringToMood(const String& emotion) const;
  void applyMoodPreset(uint8_t mood);
  static MoodPreset getMoodPreset(uint8_t mood);
};

#endif

