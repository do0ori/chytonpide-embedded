#ifndef FACE_EMOTION_CONTROLLER_H
#define FACE_EMOTION_CONTROLLER_H

#include <Arduino.h>
#include <TFT_eSPI.h>
#include "RoboEyesTFT_eSPI.h"

/**
 * FaceEmotionController (TCP version)
 * -------------------
 * HTTP polling을 제거하고, 서버 push로 받은 감정 상태를 LCD에 적용하는 액추에이터.
 * TcpDeviceClient의 state_update 콜백에서 applyFace()를 호출한다.
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
  FaceEmotionController(TFT_RoboEyes* roboEyes);
  void applyFace(const String& face);
  String getCurrentFace() const { return currentFace; }

private:
  TFT_RoboEyes* roboEyes;
  String currentFace;

  uint8_t emotionStringToMood(const String& emotion) const;
  void applyMoodPreset(uint8_t mood);
  static MoodPreset getMoodPreset(uint8_t mood);
};

#endif
