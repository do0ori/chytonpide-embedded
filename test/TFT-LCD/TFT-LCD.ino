#include <TFT_eSPI.h>
#include "RoboEyesTFT_eSPI.h"

// portrait=false, rotation=3 → 320x240 landscape
TFT_eSPI tft = TFT_eSPI();  
TFT_RoboEyes roboEyes(tft, false, 3);

// 자동 감정 변경 타이머
unsigned long moodTimer = 0;
int moodStage = 0;

void setup() {
  tft.init();
  tft.setRotation(3);   // ✔ 가로 320x240

  // RoboEyes 화면 크기 (landscape)
  roboEyes.setScreenSize(320, 240);

  // 50 FPS
  roboEyes.begin(50);

  roboEyes.setColors(TFT_WHITE, TFT_BLACK);

  // 눈 크기, 위치 (가로용)
  roboEyes.setWidth(60, 60);
  roboEyes.setHeight(60, 60);
  roboEyes.setSpacebetween(40);  // 가로형 화면은 눈 사이 조금 더 넓게
  roboEyes.setBorderradius(10, 10);

  // 자동 깜빡임 + idle (마지막 두 파라미터: X축 범위, Y축 범위)
  roboEyes.setAutoblinker(true, 2, 1);
  roboEyes.setIdleMode(true, 4, 1, 15, 15);  // 가운데 기준 ±15픽셀 범위

  moodTimer = millis();
}

void loop() {
  roboEyes.update();

  // 3초마다 다음 감정
  if (millis() - moodTimer > 3000) {
    moodTimer = millis();
    moodStage++;

    if (moodStage == 1) {
      roboEyes.setColors(TFT_GREEN, TFT_BLACK);
      roboEyes.setMood(HAPPY);
    }
    else if (moodStage == 2) {
      roboEyes.setColors(TFT_RED, TFT_BLACK);
      roboEyes.setMood(ANGRY);
    }
    else if (moodStage == 3) {
      roboEyes.setColors(TFT_BLUE, TFT_BLACK);
      roboEyes.setMood(SAD);  // 새로 추가된 SAD 감정 예시
    }
    else {
      roboEyes.setColors(TFT_WHITE, TFT_BLACK);
      roboEyes.setMood(DEFAULT);
      moodStage = 0;
    }
  }
}
