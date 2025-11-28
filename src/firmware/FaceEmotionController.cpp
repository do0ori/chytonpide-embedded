#include "FaceEmotionController.h"
#include <ctype.h>

FaceEmotionController::FaceEmotionController(const char* baseUrl, const char* emotionEndpoint, DeviceID* deviceRef, TFT_RoboEyes* roboEyesRef)
  : serverBaseUrl(baseUrl),
    emotionEndpoint(emotionEndpoint),
    device(deviceRef),
    roboEyes(roboEyesRef),
    currentEmotion(""),
    initialized(false),
    lastCheckTime(0),
    checkIntervalMs(2000) {
  initialized = (device != nullptr && roboEyes != nullptr);
}

void FaceEmotionController::update() {
  if (!initialized) {
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  unsigned long now = millis();
  if (now - lastCheckTime < checkIntervalMs) {
    return;
  }
  lastCheckTime = now;

  fetchAndApplyEmotion();
}

void FaceEmotionController::fetchAndApplyEmotion() {
  if (!device || !serverBaseUrl || !emotionEndpoint || !roboEyes) {
    return;
  }

  String deviceId = device->getID();
  if (deviceId.length() == 0) {
    return;
  }

  HTTPClient http;
  String encodedDeviceId = urlEncode(deviceId);
  String url = String(serverBaseUrl) + emotionEndpoint + "?device_id=" + encodedDeviceId;

  http.begin(url);
  int httpCode = http.GET();

  if (httpCode == HTTP_CODE_OK) {
    String response = http.getString();
    String emotion = parseEmotionFromJson(response);
    
    if (emotion.length() > 0 && emotion != currentEmotion) {
      currentEmotion = emotion;
      uint8_t mood = emotionStringToMood(emotion);
      applyMoodPreset(mood);
    } else if (emotion.length() == 0 && currentEmotion.length() == 0) {
      // 서버에서 기본값(NEUTRAL)을 반환했거나 응답이 없으면 DEFAULT로 설정 (최초 1회만)
      currentEmotion = "NEUTRAL";
      applyMoodPreset(DEFAULT);
    }
  }

  http.end();
}

String FaceEmotionController::parseEmotionFromJson(const String& json) const {
  // JSON에서 "emotion": "HAPPY" 형태를 찾음
  int emotionIndex = json.indexOf("\"emotion\":");
  if (emotionIndex == -1) {
    return "";
  }

  int valueStart = json.indexOf(':', emotionIndex) + 1;
  while (valueStart < json.length() && (isspace(json.charAt(valueStart)) || json.charAt(valueStart) == '"')) {
    valueStart++;
  }

  int valueEnd = valueStart;
  while (valueEnd < json.length() && json.charAt(valueEnd) != '"' && json.charAt(valueEnd) != ',' && json.charAt(valueEnd) != '}') {
    valueEnd++;
  }

  if (valueEnd <= valueStart) {
    return "";
  }

  String emotion = json.substring(valueStart, valueEnd);
  emotion.trim();
  
  // 따옴표 제거
  if (emotion.startsWith("\"")) {
    emotion = emotion.substring(1);
  }
  if (emotion.endsWith("\"")) {
    emotion = emotion.substring(0, emotion.length() - 1);
  }

  return emotion;
}

uint8_t FaceEmotionController::emotionStringToMood(const String& emotion) const {
  String emotionUpper = emotion;
  emotionUpper.toUpperCase();
  emotionUpper.trim();

  // 서버에서 받은 문자열을 mood 상수로 변환
  if (emotionUpper == "HAPPY") {
    return HAPPY;
  } else if (emotionUpper == "SAD") {
    return SAD;
  } else if (emotionUpper == "ANGRY") {
    return ANGRY;
  } else if (emotionUpper == "TIRED") {
    return TIRED;
  } else if (emotionUpper == "SURPRISED") {
    return SURPRISED;
  } else if (emotionUpper == "CALM") {
    return CALM;
  } else if (emotionUpper == "NEUTRAL" || emotionUpper == "DEFAULT") {
    return DEFAULT;
  }

  // 알 수 없는 감정은 기본값 반환
  return DEFAULT;
}

MoodPreset FaceEmotionController::getMoodPreset(uint8_t mood) {
  // TFT-LCD.ino의 moodTests 배열과 동일한 설정
  switch (mood) {
    case DEFAULT:
      return {DEFAULT, TFT_WHITE, TFT_BLACK, 60, 60, 12, 50};
    case TIRED:
      return {TIRED, TFT_ORANGE, TFT_BLACK, 80, 30, 10, 40};
    case HAPPY:
      return {HAPPY, TFT_GREEN, TFT_BLACK, 40, 90, 20, 60};
    case ANGRY:
      return {ANGRY, TFT_RED, TFT_BLACK, 40, 90, 20, 55};
    case SAD:
      return {SAD, TFT_SKYBLUE, TFT_BLACK, 40, 90, 20, 55};
    case SURPRISED:
      return {SURPRISED, TFT_CYAN, TFT_BLACK, 60, 60, 30, 70};
    case CALM:
      return {CALM, TFT_BLUE, TFT_BLACK, 40, 90, 20, 55};
    default:
      return {DEFAULT, TFT_WHITE, TFT_BLACK, 60, 60, 12, 50};
  }
}

void FaceEmotionController::applyMoodPreset(uint8_t mood) {
  if (!roboEyes) {
    return;
  }
  
  MoodPreset preset = getMoodPreset(mood);
  
  // MoodPreset에 따라 RoboEyes 설정
  roboEyes->setColors(preset.color, preset.bgColor);
  roboEyes->setWidth(preset.eyeWidth, preset.eyeWidth);
  roboEyes->setHeight(preset.eyeHeight, preset.eyeHeight);
  roboEyes->setBorderradius(preset.borderRadius, preset.borderRadius);
  roboEyes->setSpacebetween(preset.spaceBetween);
  roboEyes->setMood(preset.mood);
}

String FaceEmotionController::urlEncode(const String& raw) const {
  String encoded = "";
  for (size_t i = 0; i < raw.length(); ++i) {
    char c = raw.charAt(i);
    if (isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_' || c == '.' || c == '~') {
      encoded += c;
    } else {
      encoded += '%';
      if ((uint8_t)c < 0x10) encoded += '0';
      encoded += String(static_cast<uint8_t>(c), HEX);
    }
  }
  encoded.toUpperCase();
  return encoded;
}

