#include <TFT_eSPI.h>
#include "RoboEyesTFT_eSPI.h"

// portrait=false, rotation=3 → 320x240 landscape
TFT_eSPI tft = TFT_eSPI();  
TFT_RoboEyes roboEyes(tft, false, 3);

// 감정 순환 테스트 구성
struct MoodPreset {
  uint8_t mood;
  uint16_t color;
  uint16_t bgColor;
  uint8_t eyeWidth;
  uint8_t eyeHeight;
  uint8_t borderRadius;
};

const MoodPreset moodTests[] = {
  {DEFAULT,    TFT_WHITE,   TFT_BLACK, 60, 60, 12},
  {TIRED,      TFT_ORANGE,  TFT_BLACK, 80, 30, 10},
  {HAPPY,      TFT_GREEN,   TFT_BLACK, 40, 90, 20},
  {ANGRY,      TFT_RED,     TFT_BLACK, 40, 90, 20},
  {SAD,        TFT_SKYBLUE, TFT_BLACK, 40, 90, 20},
  {SURPRISED,  TFT_CYAN,    TFT_BLACK, 60, 60, 30},
  {CALM,       TFT_BLUE,    TFT_BLACK, 40, 90, 20},
};

const size_t moodTestCount = sizeof(moodTests) / sizeof(moodTests[0]);

unsigned long shapeTimer = 0;
size_t currentMoodIndex = 0;

void applyMoodPreset(size_t index) {
  const MoodPreset &preset = moodTests[index];
  roboEyes.setColors(preset.color, preset.bgColor);
  roboEyes.setWidth(preset.eyeWidth, preset.eyeWidth);
  roboEyes.setHeight(preset.eyeHeight, preset.eyeHeight);
  roboEyes.setBorderradius(preset.borderRadius, preset.borderRadius);
  roboEyes.setMood(preset.mood);
}

void setup() {
  tft.init();
  tft.setRotation(3);   // ✔ 가로 320x240

  // RoboEyes 화면 크기 (landscape)
  roboEyes.setScreenSize(320, 240);

  // 50 FPS
  roboEyes.begin(50);

  // 눈 크기, 위치 (가로용)
  roboEyes.setSpacebetween(40);  // 가로형 화면은 눈 사이 조금 더 넓게

  // 자동 깜빡임 + idle (마지막 두 파라미터: X축 범위, Y축 범위)
  roboEyes.setAutoblinker(true, 2, 1);
  roboEyes.setIdleMode(true, 4, 1, 15, 15);  // 가운데 기준 ±15픽셀 범위

  shapeTimer = millis();
  applyMoodPreset(currentMoodIndex);
}

void loop() {
  roboEyes.update();

  // 3초마다 다음 감정
  if (millis() - shapeTimer > 3000) {
    shapeTimer = millis();
    currentMoodIndex = (currentMoodIndex + 1) % moodTestCount;
    applyMoodPreset(currentMoodIndex);
  }
}
