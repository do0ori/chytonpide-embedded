#include "FaceEmotionController.h"

FaceEmotionController::FaceEmotionController(TFT_RoboEyes* roboEyesRef)
  : roboEyes(roboEyesRef),
    currentFace("NEUTRAL") {
}

void FaceEmotionController::applyFace(const String& face) {
  if (!roboEyes || face.length() == 0) {
    return;
  }

  if (face != currentFace) {
    currentFace = face;
    uint8_t mood = emotionStringToMood(face);
    applyMoodPreset(mood);
    Serial.printf("[FACE] Applied: %s\n", face.c_str());
  }
}

uint8_t FaceEmotionController::emotionStringToMood(const String& emotion) const {
  String e = emotion;
  e.toUpperCase();
  e.trim();

  if (e == "HAPPY") return HAPPY;
  if (e == "SAD") return SAD;
  if (e == "ANGRY") return ANGRY;
  if (e == "TIRED") return TIRED;
  if (e == "SURPRISED") return SURPRISED;
  if (e == "CALM") return CALM;
  if (e == "NEUTRAL" || e == "DEFAULT") return DEFAULT;

  return DEFAULT;
}

MoodPreset FaceEmotionController::getMoodPreset(uint8_t mood) {
  switch (mood) {
    case DEFAULT:   return {DEFAULT, TFT_WHITE, TFT_BLACK, 60, 60, 12, 50};
    case TIRED:     return {TIRED, TFT_ORANGE, TFT_BLACK, 80, 30, 10, 40};
    case HAPPY:     return {HAPPY, TFT_GREEN, TFT_BLACK, 40, 90, 20, 60};
    case ANGRY:     return {ANGRY, TFT_RED, TFT_BLACK, 40, 90, 20, 55};
    case SAD:       return {SAD, TFT_SKYBLUE, TFT_BLACK, 40, 90, 20, 55};
    case SURPRISED: return {SURPRISED, TFT_CYAN, TFT_BLACK, 60, 60, 30, 70};
    case CALM:      return {CALM, TFT_BLUE, TFT_BLACK, 40, 90, 20, 55};
    default:        return {DEFAULT, TFT_WHITE, TFT_BLACK, 60, 60, 12, 50};
  }
}

void FaceEmotionController::applyMoodPreset(uint8_t mood) {
  if (!roboEyes) {
    return;
  }

  MoodPreset preset = getMoodPreset(mood);

  roboEyes->setColors(preset.color, preset.bgColor);
  roboEyes->setWidth(preset.eyeWidth, preset.eyeWidth);
  roboEyes->setHeight(preset.eyeHeight, preset.eyeHeight);
  roboEyes->setBorderradius(preset.borderRadius, preset.borderRadius);
  roboEyes->setSpacebetween(preset.spaceBetween);
  roboEyes->setMood(preset.mood);
}
