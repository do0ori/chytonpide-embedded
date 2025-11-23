#ifndef _TFT_ROBOEYES_H
#define _TFT_ROBOEYES_H

#include <TFT_eSPI.h>

#define DEFAULT_BGCOLOR   TFT_BLACK
#define DEFAULT_MAINCOLOR TFT_WHITE

#define DEFAULT   0
#define TIRED     1
#define ANGRY     2
#define HAPPY     3
#define SAD       4  // 새 감정 추가 예시

#define ON  1
#define OFF 0

#define N   1
#define NE  2
#define E   3
#define SE  4
#define S   5
#define SW  6
#define W   7
#define NW  8

class TFT_RoboEyes {
  public:
    TFT_eSPI *tft;
    TFT_eSprite *sprite;

    int screenWidth = 240;
    int screenHeight = 320;
    uint16_t bgColor;
    uint16_t mainColor;

    int frameInterval;
    unsigned long fpsTimer;

    bool tired;
    bool angry;
    bool happy;
    bool sad;  // 새 감정 플래그 추가
    bool curious;
    bool cyclops;
    bool eyeL_open;
    bool eyeR_open;

    int eyeLwidthDefault, eyeLheightDefault;
    int eyeLwidthCurrent, eyeLheightCurrent;
    int eyeLwidthNext, eyeLheightNext;
    int eyeLheightOffset;
    uint8_t eyeLborderRadiusDefault, eyeLborderRadiusCurrent, eyeLborderRadiusNext;

    int eyeRwidthDefault, eyeRheightDefault;
    int eyeRwidthCurrent, eyeRheightCurrent;
    int eyeRwidthNext, eyeRheightNext;
    int eyeRheightOffset;
    uint8_t eyeRborderRadiusDefault, eyeRborderRadiusCurrent, eyeRborderRadiusNext;

    int eyeLxDefault, eyeLyDefault;
    int eyeLx, eyeLy;
    int eyeLxNext, eyeLyNext;

    int eyeRxDefault, eyeRyDefault;
    int eyeRx, eyeRy;
    int eyeRxNext, eyeRyNext;

    uint8_t eyelidsHeightMax;
    uint8_t eyelidsTiredHeight, eyelidsTiredHeightNext;
    uint8_t eyelidsAngryHeight, eyelidsAngryHeightNext;
    uint8_t eyelidsHappyBottomOffsetMax;
    uint8_t eyelidsHappyBottomOffset, eyelidsHappyBottomOffsetNext;
    uint8_t eyelidsSadTopOffset, eyelidsSadTopOffsetNext;  // SAD 감정용: 위쪽 눈꺼풀 오프셋
    int spaceBetweenDefault, spaceBetweenCurrent, spaceBetweenNext;

    bool hFlicker;
    bool hFlickerAlternate;
    uint8_t hFlickerAmplitude;
    bool vFlicker;
    bool vFlickerAlternate;
    uint8_t vFlickerAmplitude;

    bool autoblinker;
    int blinkInterval;
    int blinkIntervalVariation;
    unsigned long blinktimer;

    bool idle;
    int idleInterval;
    int idleIntervalVariation;
    unsigned long idleAnimationTimer;
    int idleRangeX;  // X축 움직임 범위 (기본 위치 기준 ±값)
    int idleRangeY;  // Y축 움직임 범위 (기본 위치 기준 ±값)

    bool confused;
    unsigned long confusedAnimationTimer;
    int confusedAnimationDuration;
    bool confusedToggle;

    bool laugh;
    unsigned long laughAnimationTimer;
    int laughAnimationDuration;
    bool laughToggle;

    bool blinkingActive;
    unsigned long blinkCloseDurationTimer;
    int blinkCloseDuration = 150;

    TFT_RoboEyes(TFT_eSPI &display, bool portrait = true, int rotations = 1) {
      tft = &display;

      if (portrait) {
        screenWidth = 240;
        screenHeight = 320;
        tft->setRotation(rotations);
      } else {
        screenWidth = 320;
        screenHeight = 240;
        tft->setRotation(rotations);
      }

      bgColor = DEFAULT_BGCOLOR;
      mainColor = DEFAULT_MAINCOLOR;

      frameInterval = 1000 / 50;
      fpsTimer = 0;

      tired = angry = happy = sad = curious = cyclops = false;
      eyeL_open = eyeR_open = false;

      eyeLwidthDefault = 36;
      eyeLheightDefault = 36;
      eyeLwidthCurrent = eyeLwidthDefault;
      eyeLheightCurrent = 1;
      eyeLwidthNext = eyeLwidthDefault;
      eyeLheightNext = eyeLheightDefault;
      eyeLheightOffset = 0;
      eyeLborderRadiusDefault = 8;
      eyeLborderRadiusCurrent = eyeLborderRadiusDefault;
      eyeLborderRadiusNext = eyeLborderRadiusDefault;

      eyeRwidthDefault = eyeLwidthDefault;
      eyeRheightDefault = eyeLheightDefault;
      eyeRwidthCurrent = eyeRwidthDefault;
      eyeRheightCurrent = 1;
      eyeRwidthNext = eyeRwidthDefault;
      eyeRheightNext = eyeRheightDefault;
      eyeRheightOffset = 0;
      eyeRborderRadiusDefault = 8;
      eyeRborderRadiusCurrent = eyeRborderRadiusDefault;
      eyeRborderRadiusNext = eyeRborderRadiusDefault;

      spaceBetweenDefault = 10;
      spaceBetweenCurrent = spaceBetweenDefault;
      spaceBetweenNext = spaceBetweenDefault;

      eyeLxDefault = (screenWidth - (eyeLwidthDefault + spaceBetweenDefault + eyeRwidthDefault)) / 2;
      eyeLyDefault = (screenHeight - eyeLheightDefault) / 2;
      eyeLx = eyeLxDefault;
      eyeLy = eyeLyDefault;
      eyeLxNext = eyeLx;
      eyeLyNext = eyeLy;

      eyeRxDefault = eyeLxDefault + eyeLwidthDefault + spaceBetweenDefault;
      eyeRyDefault = eyeLyDefault;
      eyeRx = eyeRxDefault;
      eyeRy = eyeRyDefault;
      eyeRxNext = eyeRx;
      eyeRyNext = eyeRy;

      eyelidsHeightMax = eyeLheightDefault / 2;
      eyelidsTiredHeight = eyelidsTiredHeightNext = 0;
      eyelidsAngryHeight = eyelidsAngryHeightNext = 0;
      eyelidsHappyBottomOffsetMax = eyeLheightDefault / 2 + 3;
      eyelidsHappyBottomOffset = eyelidsHappyBottomOffsetNext = 0;
      eyelidsSadTopOffset = eyelidsSadTopOffsetNext = 0;  // SAD 감정 초기화

      hFlicker = vFlicker = confused = laugh = false;
      hFlickerAlternate = vFlickerAlternate = true;
      hFlickerAmplitude = 2;
      vFlickerAmplitude = 10;

      autoblinker = false;
      blinkInterval = 1;
      blinkIntervalVariation = 4;
      blinktimer = 0;

      idle = false;
      idleInterval = idleIntervalVariation = 1;
      idleAnimationTimer = 0;
      idleRangeX = 20;  // 기본값: X축 ±20픽셀 범위
      idleRangeY = 20;  // 기본값: Y축 ±20픽셀 범위

      confusedAnimationDuration = 500;
      confusedToggle = true;

      laughAnimationDuration = 500;
      laughToggle = true;

      blinkingActive = false;
      blinkCloseDurationTimer = 0;
    }

    void begin(byte frameRate = 50) {
      sprite = new TFT_eSprite(tft);
      sprite->setColorDepth(8);
      sprite->createSprite(screenWidth, screenHeight);
      sprite->fillSprite(bgColor);

      eyeLheightCurrent = 1;
      eyeRheightCurrent = 1;
      setFramerate(frameRate);
    }

    void update() {
      if (millis() - fpsTimer >= frameInterval) {
        drawEyes();
        sprite->pushSprite(0, 0);
        fpsTimer = millis();
      }
    }

    void setFramerate(byte fps) {
      frameInterval = 1000 / fps;
    }

    void updateEyePositions() {
      // 눈 위치를 중앙으로 재계산
      eyeLxDefault = (screenWidth - (eyeLwidthDefault + spaceBetweenDefault + eyeRwidthDefault)) / 2;
      eyeLyDefault = (screenHeight - eyeLheightDefault) / 2;

      eyeRxDefault = eyeLxDefault + eyeLwidthDefault + spaceBetweenDefault;
      eyeRyDefault = eyeLyDefault;

      eyeLxNext = eyeLxDefault;
      eyeLyNext = eyeLyDefault;
      eyeRxNext = eyeRxDefault;
      eyeRyNext = eyeRyDefault;
    }

    void setScreenSize(int w, int h) {
      screenWidth = w;
      screenHeight = h;

      updateEyePositions();

      if (sprite) {
        sprite->deleteSprite();
        sprite->createSprite(screenWidth, screenHeight);
      }
    }

    void setWidth(byte leftEye, byte rightEye) {
      eyeLwidthNext = leftEye;
      eyeRwidthNext = rightEye;
      eyeLwidthDefault = leftEye;
      eyeRwidthDefault = rightEye;
      updateEyePositions();  // 크기 변경 후 위치 재계산
    }

    void setHeight(byte leftEye, byte rightEye) {
      eyeLheightNext = leftEye;
      eyeRheightNext = rightEye;
      eyeLheightDefault = leftEye;
      eyeRheightDefault = rightEye;
      updateEyePositions();  // 크기 변경 후 위치 재계산
    }

    void setBorderradius(byte leftEye, byte rightEye) {
      eyeLborderRadiusNext = leftEye;
      eyeRborderRadiusNext = rightEye;
      eyeLborderRadiusDefault = leftEye;
      eyeRborderRadiusDefault = rightEye;
    }

    void setSpacebetween(int space) {
      spaceBetweenNext = space;
      spaceBetweenDefault = space;
      updateEyePositions();  // 간격 변경 후 위치 재계산
    }

    void setMood(uint8_t mood) {
      tired = angry = happy = sad = false;
      if (mood == TIRED) tired = true;
      else if (mood == ANGRY) angry = true;
      else if (mood == HAPPY) happy = true;
      else if (mood == SAD) sad = true;  // 새 감정 처리 추가
    }

    void setAutoblinker(bool active, int interval = 1, int variation = 4) {
      autoblinker = active;
      blinkInterval = interval;
      blinkIntervalVariation = variation;

      blinktimer = millis() +
        (blinkInterval * 1000UL) +
        (random(blinkIntervalVariation) * 1000UL);

      blinkingActive = false;
    }

    void setIdleMode(bool active, int interval = 1, int variation = 3, int rangeX = 20, int rangeY = 20) {
      idle = active;
      idleInterval = interval;
      idleIntervalVariation = variation;
      idleRangeX = rangeX;
      idleRangeY = rangeY;
    }

    void setCuriosity(bool v) { curious = v; }

    void setHFlicker(bool v, uint8_t amp = 2) {
      hFlicker = v; hFlickerAmplitude = amp;
    }

    void setVFlicker(bool v, uint8_t amp = 10) {
      vFlicker = v; vFlickerAmplitude = amp;
    }

    void setColors(uint16_t main, uint16_t bg) {
      mainColor = main;
      bgColor = bg;
    }

    int getScreenConstraint_X() {
      return screenWidth - eyeLwidthCurrent - spaceBetweenCurrent - eyeRwidthCurrent;
    }

    int getScreenConstraint_Y() {
      return screenHeight - eyeLheightDefault;
    }

    void close() {
      eyeLheightNext = 1;
      eyeRheightNext = 1;
      eyeL_open = eyeR_open = false;
      eyeLborderRadiusNext = eyeRborderRadiusNext = 0;
    }

    void open() {
      eyeL_open = eyeR_open = true;
      eyeLheightNext = eyeLheightDefault;
      eyeRheightNext = eyeRheightDefault;
      eyeLborderRadiusNext = eyeLborderRadiusDefault;
      eyeRborderRadiusNext = eyeRborderRadiusDefault;
    }

    void drawEyes() {
      if (curious) {
        eyeLheightOffset = (eyeLxNext <= 10) ? 8 : 0;
        eyeRheightOffset = (eyeRxNext >= screenWidth - eyeRwidthCurrent - 10) ? 8 : 0;
      } else {
        eyeLheightOffset = 0;
        eyeRheightOffset = 0;
      }

      eyeLheightCurrent = (eyeLheightCurrent + eyeLheightNext + eyeLheightOffset) / 2;
      eyeLy += (eyeLheightDefault - eyeLheightCurrent) / 2;
      eyeLy -= eyeLheightOffset / 2;

      eyeRheightCurrent = (eyeRheightCurrent + eyeRheightNext + eyeRheightOffset) / 2;
      eyeRy += (eyeRheightDefault - eyeRheightCurrent) / 2;
      eyeRy -= eyeRheightOffset / 2;

      if (eyeL_open && eyeLheightCurrent <= 1 + eyeLheightOffset) eyeLheightNext = eyeLheightDefault;
      if (eyeR_open && eyeRheightCurrent <= 1 + eyeRheightOffset) eyeRheightNext = eyeRheightDefault;

      eyeLwidthCurrent = (eyeLwidthCurrent + eyeLwidthNext) / 2;
      eyeRwidthCurrent = (eyeRwidthCurrent + eyeRwidthNext) / 2;
      spaceBetweenCurrent = (spaceBetweenCurrent + spaceBetweenNext) / 2;

      eyeLx = (eyeLx + eyeLxNext) / 2;
      eyeLy = (eyeLy + eyeLyNext) / 2;

      eyeRxNext = eyeLxNext + eyeLwidthCurrent + spaceBetweenCurrent;
      eyeRyNext = eyeLyNext;
      eyeRx = (eyeRx + eyeRxNext) / 2;
      eyeRy = (eyeRy + eyeRyNext) / 2;

      eyeLborderRadiusCurrent = (eyeLborderRadiusCurrent + eyeLborderRadiusNext) / 2;
      eyeRborderRadiusCurrent = (eyeRborderRadiusCurrent + eyeRborderRadiusNext) / 2;

      if (autoblinker && !blinkingActive) {
        if (millis() >= blinktimer) {
          close();
          blinkingActive = true;
          blinkCloseDurationTimer = millis() + blinkCloseDuration;
          blinktimer = millis() +
            (blinkInterval * 1000UL) +
            (random(blinkIntervalVariation) * 1000UL);
        }
      }

      if (blinkingActive && millis() >= blinkCloseDurationTimer) {
        open();
        blinkingActive = false;
      }

      if (idle && millis() >= idleAnimationTimer) {
        // 기본 위치 기준으로 제한된 범위 내에서만 움직임
        int minX = eyeLxDefault - idleRangeX;
        int maxX = eyeLxDefault + idleRangeX;
        int minY = eyeLyDefault - idleRangeY;
        int maxY = eyeLyDefault + idleRangeY;
        
        // 화면 경계 체크
        if (minX < 0) minX = 0;
        if (maxX > getScreenConstraint_X()) maxX = getScreenConstraint_X();
        if (minY < 0) minY = 0;
        if (maxY > getScreenConstraint_Y()) maxY = getScreenConstraint_Y();
        
        eyeLxNext = random(minX, maxX + 1);
        eyeLyNext = random(minY, maxY + 1);
        idleAnimationTimer = millis() +
          (idleInterval * 1000UL) +
          (random(idleIntervalVariation) * 1000UL);
      }

      if (hFlicker) {
        if (hFlickerAlternate) {
          eyeLx += hFlickerAmplitude;
          eyeRx += hFlickerAmplitude;
        } else {
          eyeLx -= hFlickerAmplitude;
          eyeRx -= hFlickerAmplitude;
        }
        hFlickerAlternate = !hFlickerAlternate;
      }

      if (vFlicker) {
        if (vFlickerAlternate) {
          eyeLy += vFlickerAmplitude;
          eyeRy += vFlickerAmplitude;
        } else {
          eyeLy -= vFlickerAmplitude;
          eyeRy -= vFlickerAmplitude;
        }
        vFlickerAlternate = !vFlickerAlternate;
      }

      if (cyclops) {
        eyeRwidthCurrent = 0;
        eyeRheightCurrent = 0;
        spaceBetweenCurrent = 0;
      }

      sprite->fillSprite(bgColor);

      sprite->fillRoundRect(
        eyeLx, eyeLy,
        eyeLwidthCurrent, eyeLheightCurrent,
        eyeLborderRadiusCurrent,
        mainColor
      );

      if (!cyclops) {
        sprite->fillRoundRect(
          eyeRx, eyeRy,
          eyeRwidthCurrent, eyeRheightCurrent,
          eyeRborderRadiusCurrent,
          mainColor
        );
      }

      eyelidsTiredHeight = (eyelidsTiredHeight + eyelidsTiredHeightNext) / 2;
      eyelidsAngryHeight = (eyelidsAngryHeight + eyelidsAngryHeightNext) / 2;
      eyelidsHappyBottomOffset = (eyelidsHappyBottomOffset + eyelidsHappyBottomOffsetNext) / 2;
      eyelidsSadTopOffset = (eyelidsSadTopOffset + eyelidsSadTopOffsetNext) / 2;
      
      // SAD 감정: 슬픈 눈 표현 (위쪽 눈꺼풀을 내려서 눈을 반쯤 가림)
      if (sad) {
        eyelidsSadTopOffsetNext = eyeLheightDefault / 2 + 2;
      } else {
        eyelidsSadTopOffsetNext = 0;
      }

      sprite->fillTriangle(
        eyeLx, eyeLy - 1,
        eyeLx + eyeLwidthCurrent, eyeLy - 1,
        eyeLx, eyeLy + eyelidsTiredHeight - 1,
        bgColor
      );

      sprite->fillTriangle(
        eyeRx, eyeRy - 1,
        eyeRx + eyeRwidthCurrent, eyeRy - 1,
        eyeRx + eyeRwidthCurrent, eyeRy + eyelidsTiredHeight - 1,
        bgColor
      );

      sprite->fillTriangle(
        eyeLx, eyeLy - 1,
        eyeLx + eyeLwidthCurrent, eyeLy - 1,
        eyeLx + eyeLwidthCurrent, eyeLy + eyelidsAngryHeight - 1,
        bgColor
      );

      sprite->fillTriangle(
        eyeRx, eyeRy - 1,
        eyeRx + eyeRwidthCurrent, eyeRy - 1,
        eyeRx, eyeRy + eyelidsAngryHeight - 1,
        bgColor
      );

      sprite->fillRoundRect(
        eyeLx - 1,
        (eyeLy + eyeLheightCurrent) - eyelidsHappyBottomOffset + 1,
        eyeLwidthCurrent + 2, eyeLheightDefault,
        eyeLborderRadiusCurrent,
        bgColor
      );

      sprite->fillRoundRect(
        eyeRx - 1,
        (eyeRy + eyeRheightCurrent) - eyelidsHappyBottomOffset + 1,
        eyeRwidthCurrent + 2, eyeRheightDefault,
        eyeRborderRadiusCurrent,
        bgColor
      );

      // SAD 감정: 위쪽 눈꺼풀을 내려서 눈을 반쯤 가림
      if (eyelidsSadTopOffset > 0) {
        sprite->fillRoundRect(
          eyeLx - 1,
          eyeLy - 1,
          eyeLwidthCurrent + 2, eyelidsSadTopOffset + 2,
          eyeLborderRadiusCurrent,
          bgColor
        );
        sprite->fillRoundRect(
          eyeRx - 1,
          eyeRy - 1,
          eyeRwidthCurrent + 2, eyelidsSadTopOffset + 2,
          eyeRborderRadiusCurrent,
          bgColor
        );
      }
    }

};

#endif
