#ifndef _TFT_ROBOEYES_H
#define _TFT_ROBOEYES_H

#include <TFT_eSPI.h>

#define DEFAULT_BGCOLOR   TFT_BLACK
#define DEFAULT_MAINCOLOR TFT_WHITE

#define DEFAULT    0
#define TIRED      1
#define ANGRY      2
#define HAPPY      3
#define SAD        4
#define SURPRISED  5
#define CALM       6

#define ON  1
#define OFF 0

// 눈 모양 타입 정의
// 사용 예시:
//   eyes.setEyeShape(EYE_SHAPE_CIRCLE, EYE_SHAPE_CIRCLE);  // 양쪽 모두 원형
//   eyes.setEyeShape(EYE_SHAPE_ROUND_RECT, EYE_SHAPE_CAPSULE_V);  // 왼쪽은 둥근 사각형, 오른쪽은 세로 캡슐형
//   eyes.setMood(ANGRY);  // 감정 설정 시 자동으로 적절한 눈 모양 적용
#define EYE_SHAPE_ROUND_RECT            0  // 기본 둥근 사각형
#define EYE_SHAPE_CIRCLE                1  // 원형
#define EYE_SHAPE_CAPSULE_V             2  // 세로 캡슐형
#define EYE_SHAPE_WIDE                  3  // 넓은 눈 (놀란 눈)
#define EYE_SHAPE_NARROW                4  // 좁은 눈 (졸린 눈)
#define EYE_SHAPE_CAPSULE_V_SLANT_LEFT  5  // 세로 캡슐 + 왼쪽이 낮아지는 사선
#define EYE_SHAPE_CAPSULE_V_SLANT_RIGHT 6  // 세로 캡슐 + 오른쪽이 낮아지는 사선
#define EYE_SHAPE_CAPSULE_V_ARCH        7  // 세로 캡슐 상단만 남긴 아치형 (행복)

// 입 모양 타입 정의
#define MOUTH_NONE    0  // 입 없음
#define MOUTH_SMILE   1  // 웃는 입 (아치형)
#define MOUTH_O       2  // O자형 입
#define MOUTH_LINE    3  // -자형 입 (직선)

// 방향 매크로 (mbedtls와의 충돌 방지를 위해 EYE_DIR_ 접두사 사용)
// HTTPClient가 mbedtls를 포함하므로 단일 문자 매크로는 사용하지 않음
#define EYE_DIR_N   1
#define EYE_DIR_NE  2
#define EYE_DIR_E   3
#define EYE_DIR_SE  4
#define EYE_DIR_S   5
#define EYE_DIR_SW  6
#define EYE_DIR_W   7
#define EYE_DIR_NW  8

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
    uint8_t eyeLshapeType, eyeLshapeTypeNext;  // 왼쪽 눈 모양 타입

    int eyeRwidthDefault, eyeRheightDefault;
    int eyeRwidthCurrent, eyeRheightCurrent;
    int eyeRwidthNext, eyeRheightNext;
    int eyeRheightOffset;
    uint8_t eyeRborderRadiusDefault, eyeRborderRadiusCurrent, eyeRborderRadiusNext;
    uint8_t eyeRshapeType, eyeRshapeTypeNext;  // 오른쪽 눈 모양 타입

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
    
    // 입 관련 변수
    uint8_t mouthType, mouthTypeNext;  // 입 모양 타입
    int mouthYOffset;  // 눈 아래로부터의 거리
    int mouthWidth;  // 입 너비

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
      eyeLshapeType = eyeLshapeTypeNext = EYE_SHAPE_ROUND_RECT;

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
      eyeRshapeType = eyeRshapeTypeNext = EYE_SHAPE_ROUND_RECT;

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
      
      mouthType = mouthTypeNext = MOUTH_NONE;
      mouthYOffset = 20;  // 눈 아래로부터 20픽셀
      mouthWidth = 30;  // 기본 입 너비

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

    void setEyeShape(uint8_t leftShape, uint8_t rightShape) {
      eyeLshapeTypeNext = leftShape;
      eyeRshapeTypeNext = rightShape;
    }

    void setMouth(uint8_t mouth) {
      mouthTypeNext = mouth;
    }
    
    void setMouthYOffset(int offset) {
      mouthYOffset = offset;
    }
    
    void setMouthWidth(int width) {
      mouthWidth = width;
    }

    void setMood(uint8_t mood) {
      tired = angry = happy = sad = false;

      switch (mood) {
        case TIRED:
          tired = true;
          setEyeShape(EYE_SHAPE_NARROW, EYE_SHAPE_NARROW);  // 졸린 눈 - 좁은 눈
          setMouth(MOUTH_NONE);  // 입 없음
          break;

        case ANGRY:
          angry = true;
          // 화난 눈: 왼쪽은 오른쪽이 낮아지고, 오른쪽은 왼쪽이 낮아짐 (안쪽으로 모임)
          setEyeShape(EYE_SHAPE_CAPSULE_V_SLANT_RIGHT, EYE_SHAPE_CAPSULE_V_SLANT_LEFT);
          setMouth(MOUTH_NONE);  // 입 없음
          break;

        case HAPPY:
          happy = true;
          setEyeShape(EYE_SHAPE_CAPSULE_V_ARCH, EYE_SHAPE_CAPSULE_V_ARCH);  // 즐거운 눈 - 아치형
          setMouth(MOUTH_NONE);  // 입 없음
          break;

        case SAD:
          sad = true;
          // 슬픈 눈: 왼쪽은 왼쪽이 낮아지고, 오른쪽은 오른쪽이 낮아짐 (바깥쪽으로 처짐)
          setEyeShape(EYE_SHAPE_CAPSULE_V_SLANT_LEFT, EYE_SHAPE_CAPSULE_V_SLANT_RIGHT);
          setMouth(MOUTH_NONE);  // 입 없음
          break;

        case SURPRISED:
          setEyeShape(EYE_SHAPE_CIRCLE, EYE_SHAPE_CIRCLE);  // 놀란 눈 - 원형
          setMouth(MOUTH_NONE);  // 입 없음
          break;

        case CALM:
          setEyeShape(EYE_SHAPE_CAPSULE_V, EYE_SHAPE_CAPSULE_V);  // 차분한 눈 - 세로 캡슐
          setMouth(MOUTH_NONE);  // 입 없음
          break;

        case DEFAULT:
        default:
          setEyeShape(EYE_SHAPE_ROUND_RECT, EYE_SHAPE_ROUND_RECT);  // 기본 둥근 사각형
          setMouth(MOUTH_NONE);  // 입 없음
          break;
      }
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

    void drawEyeShape(int x, int y, int width, int height, uint8_t shapeType, uint8_t borderRadius, uint16_t color) {
      int centerX = x + width / 2;
      int centerY = y + height / 2;
      int radius = min(width, height) / 2;

      switch (shapeType) {
        case EYE_SHAPE_CIRCLE:
          sprite->fillCircle(centerX, centerY, radius, color);
          break;

        case EYE_SHAPE_CAPSULE_V:
          // 세로 캡슐형 (상하 원 + 사각형) - 두 원의 중심 거리가 지름
          {
            int capsuleRadius = width / 2;  // 가로 방향이 반지름
            int diameter = width;  // 지름 = width
            int topCircleY = y + capsuleRadius;
            int bottomCircleY = topCircleY + diameter;  // 두 원의 중심 거리 = 지름

            sprite->fillCircle(centerX, topCircleY, capsuleRadius, color);
            sprite->fillCircle(centerX, bottomCircleY, capsuleRadius, color);
            sprite->fillRect(x, topCircleY, width, diameter, color);  // 가운데 사각형 한 변 = 지름
          }
          break;

        case EYE_SHAPE_CAPSULE_V_SLANT_LEFT:
        case EYE_SHAPE_CAPSULE_V_SLANT_RIGHT:
          // 세로 캡슐형 상단을 사선으로 잘라 감정을 표현 - 두 원의 중심 거리가 지름
          {
            int capsuleRadius = width / 2;
            int diameter = width;  // 지름 = width
            int topCircleY = y + capsuleRadius;
            int bottomCircleY = topCircleY + diameter;  // 두 원의 중심 거리 = 지름

            sprite->fillCircle(centerX, topCircleY, capsuleRadius, color);
            sprite->fillCircle(centerX, bottomCircleY, capsuleRadius, color);
            sprite->fillRect(x, topCircleY, width, diameter, color);  // 가운데 사각형 한 변 = 지름

            int slantHeight = max(4, height / 2);
            if (shapeType == EYE_SHAPE_CAPSULE_V_SLANT_LEFT) {
              // 왼쪽이 낮아지는 사선
              sprite->fillTriangle(
                x, y,
                x, y + slantHeight,
                x + width, y,
                bgColor
              );
            } else {
              // 오른쪽이 낮아지는 사선
              sprite->fillTriangle(
                x + width, y,
                x + width, y + slantHeight,
                x, y,
                bgColor
              );
            }
          }
          break;

        case EYE_SHAPE_CAPSULE_V_ARCH:
          // 세로 캡슐형에서 아래쪽 원을 제거해 아치 형태를 만듦 (행복)
          {
            int capsuleRadius = width / 2;
            int diameter = width;
            int topCircleY = y + capsuleRadius;
            int bottomCircleY = topCircleY + diameter;

            // 전체 세로 캡슐 먼저 그리기
            sprite->fillCircle(centerX, topCircleY, capsuleRadius, color);
            sprite->fillCircle(centerX, bottomCircleY, capsuleRadius, color);
            sprite->fillRect(x, topCircleY, width, diameter, color);

            // 아래쪽 원 영역과 그 아래를 배경색으로 덮어 아치 형태로 만들기
            sprite->fillCircle(centerX, bottomCircleY, capsuleRadius, bgColor);
          }
          break;

        case EYE_SHAPE_WIDE:
          // 넓은 눈 (놀란 눈)
          sprite->fillRoundRect(x, y, width, height * 3 / 4, borderRadius, color);
          break;

        case EYE_SHAPE_NARROW:
          // 좁은 눈 (졸린 눈)
          sprite->fillRoundRect(x, y + height / 4, width, height / 2, borderRadius, color);
          break;

        case EYE_SHAPE_ROUND_RECT:
        default:
          // 기본 둥근 사각형
          sprite->fillRoundRect(x, y, width, height, borderRadius, color);
          break;
      }
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

      // 눈 모양 타입 부드럽게 전환
      eyeLshapeType = eyeLshapeTypeNext;
      eyeRshapeType = eyeRshapeTypeNext;

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

      // 왼쪽 눈 그리기
      drawEyeShape(
        eyeLx, eyeLy,
        eyeLwidthCurrent, eyeLheightCurrent,
        eyeLshapeType,
        eyeLborderRadiusCurrent,
        mainColor
      );

      // 오른쪽 눈 그리기 (사이클롭스 모드가 아닐 때)
      if (!cyclops) {
        drawEyeShape(
          eyeRx, eyeRy,
          eyeRwidthCurrent, eyeRheightCurrent,
          eyeRshapeType,
          eyeRborderRadiusCurrent,
          mainColor
        );
      }

      eyelidsTiredHeight = (eyelidsTiredHeight + eyelidsTiredHeightNext) / 2;
      eyelidsAngryHeight = (eyelidsAngryHeight + eyelidsAngryHeightNext) / 2;
      eyelidsHappyBottomOffset = (eyelidsHappyBottomOffset + eyelidsHappyBottomOffsetNext) / 2;
      eyelidsSadTopOffset = (eyelidsSadTopOffset + eyelidsSadTopOffsetNext) / 2;

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

      // 입 그리기
      mouthType = mouthTypeNext;
      if (mouthType != MOUTH_NONE) {
        drawMouth();
      }
    }
    
    void drawMouth() {
      // 입 위치: 두 눈 사이 중앙, 눈 아래로 mouthYOffset 픽셀
      int mouthCenterX = (eyeLx + eyeLwidthCurrent + eyeRx) / 2;
      int mouthY = max(eyeLy, eyeRy) + eyeLheightDefault + mouthYOffset;
      int mouthHeight = 8;  // 입 높이
      
      switch (mouthType) {
        case MOUTH_SMILE:
          // 웃는 입 (아치형) - 아래로 볼록한 호 (fillRoundRect로 근사)
          {
            int arcHeight = mouthHeight / 2;
            sprite->fillRoundRect(
              mouthCenterX - mouthWidth / 2,
              mouthY,
              mouthWidth,
              arcHeight,
              arcHeight,  // borderRadius를 arcHeight로 설정하여 아래쪽만 둥글게
              mainColor
            );
          }
          break;
          
        case MOUTH_O:
          // O자형 입 (타원형) - fillCircle 사용
          {
            int radius = min(mouthWidth / 2, mouthHeight / 2);
            sprite->fillCircle(mouthCenterX, mouthY + mouthHeight / 2, radius, mainColor);
            // 안쪽을 배경색으로 채워서 O자형 만들기
            sprite->fillCircle(mouthCenterX, mouthY + mouthHeight / 2, radius - 2, bgColor);
          }
          break;
          
        case MOUTH_LINE:
          // -자형 입 (직선)
          sprite->fillRect(
            mouthCenterX - mouthWidth / 2,
            mouthY + mouthHeight / 2 - 1,
            mouthWidth,
            3,
            mainColor
          );
          break;
          
        default:
          break;
      }
    }

};

#endif

