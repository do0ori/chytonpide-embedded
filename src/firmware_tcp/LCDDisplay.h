#ifndef LCD_DISPLAY_H
#define LCD_DISPLAY_H

#include <TFT_eSPI.h>
#include <WiFi.h>
#include <Preferences.h>
#include "WiFiState.h"
#include "DeviceID.h"
#include "RoboEyesTFT_eSPI.h"

extern TFT_eSPI tft;
extern DeviceID deviceID;
extern WifiState currentState;
extern WifiState lastDisplayedState;
extern const char* AP_NAME;
extern TFT_RoboEyes roboEyes;  // firmware.ino에서 선언됨
extern unsigned long wifiConnectedTime;
extern bool showFace;
extern bool roboEyesInitialized;

// LCD 화면 초기화 및 기본 설정
void initLCD();

// LCD 화면 지우기
void clearLCD();

// LCD에 텍스트 출력
void printLCD(int x, int y, const char* text, uint16_t color = TFT_WHITE, uint8_t size = 2);

// WiFi 설정 모드 화면 표시
void displayConfigMode();

// WiFi 연결 중 화면 표시
void displayConnecting();

// WiFi 연결 성공 화면 표시
void displayConnected();

// 에러 화면 표시
void displayError();

// LCD 업데이트 함수
void updateLCD();

// RoboEyes 초기화
void initRoboEyes();

// 얼굴 표시 시작
void startFaceDisplay();

#endif

