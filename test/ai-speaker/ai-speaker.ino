#include <TFT_eSPI.h>
#include <SPI.h>

#include <ScrollElement.h>
#include <ScrollContainer.h>
#include <fonts/NotoSans.h>
#include <TextToSprite.h>

#include <WiFi.h>
#include <WiFiClient.h>

#include <I2SAudioReceiver.h>
#include <I2SAudioSender.h>

#define VERTICAL_STEP 16
#define BG_COLOR 12712
#define START_Y 160  // 320x240 화면 기준 (원래 210에서 조정)
#define BOOT_BUTTON_PIN 0  // GPIO 0 (BOOT 버튼)

// 화면 크기 정의 (320x240 landscape)
#define SCREEN_WIDTH  320
#define SCREEN_HEIGHT 240

// 버튼 상태 관리
bool buttonPressed = false;
bool buttonWasPressed = false;
unsigned long buttonPressTime = 0;

WiFiClient client;
I2SAudioSender sendVoice;
I2SAudioReceiver recvVoice;

TFT_eSPI tft = TFT_eSPI();
ScrollContainer container(&tft);

void pressedButton();

void setup(void)
{
    Serial.begin(115200);
  
    WiFi.begin("ssid", "pw");
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(1000);
    }

    recvVoice.setWifiClient(client);
    recvVoice.setServerAddr("192.168.0.27", 33819); // String ip, int port

    sendVoice.setWifiClient(client);
    sendVoice.setServerAddr("192.168.0.27", 33823); // String ip, int port
    sendVoice.setI2sBus(1);                          // 0 or 1
    sendVoice.setAudioQulity(16000, 16, 1);          // int sample_rate, int sample_size, int channels(only 1 tested)
    sendVoice.setI2sPin(18, 17, 16);         // int sck, int sd, int ws
    sendVoice.setDmaBuf(1024, 6);                    // int len(only 1024 tested), int count
    sendVoice.i2sBegin();

    recvVoice.setI2sBus(0);                  // 0 or 1
    recvVoice.setAudioQuality(16000, 16, 1); // int sample_rate, int sample_size(only 16), int channels(only 1)
    recvVoice.setI2sPin(8, 19, 20);                  // int sck, int sd, int ws
    recvVoice.setDmaBuf(1024, 6);            // int len(only 1024 tested), int count
    recvVoice.i2sBegin();

    tft.init();
    tft.setRotation(3);   // Landscape 320x240 (TFT-LCD.ino와 동일)
    tft.fillScreen(BG_COLOR);     // 배경색상 흰색 지정
    tft.loadFont(NotoSansBold15); // NotoSansd에 정의됨
    tft.setTextColor(TFT_WHITE, BG_COLOR);

    // BOOT 버튼 초기화 (INPUT_PULLUP)
    pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);

    footerUI(0);
}
void loop()
{
    // BOOT 버튼 상태 체크
    bool currentButtonState = (digitalRead(BOOT_BUTTON_PIN) == LOW);
    
    if (currentButtonState)
    {
        if (!buttonPressed)
        {
            // 버튼이 처음 눌림
            buttonPressed = true;
            buttonWasPressed = false;
            buttonPressTime = millis();
            pressedButton();
            sendVoice.openFile();
        }
        else
        {
            // 버튼을 누르고 있는 중
            sendVoice.writeData();
        }
    }
    else
    {
        if (buttonPressed)
        {
            // 버튼이 방금 놓임
            buttonPressed = false;
            String whisper = sendVoice.closeFile();
            
            // 텍스트 너비: 320 화면 기준으로 조정 (16 * 20 = 320 픽셀)
            TextToSprite *ttsprites = new TextToSprite(&tft, whisper, 16 * 20, 1);
            ttsprites->setBackgroundColor(BG_COLOR);
            while (true)
            {
                TFT_eSprite *sprite = ttsprites->getNextSprite(10, START_Y);
                if (sprite != nullptr)
                {
                    container.addElement(new ScrollElement(10, START_Y, sprite->width(), sprite->height(), sprite, 1));
                    container.updateAndDraw(VERTICAL_STEP);
                }
                else
                {
                    ESP_LOGD("TextToSprite", "sprite is null");
                    delete ttsprites; // TextToSprite 객체 메모리 해제
                    break;
                }
            }

            String gptmsg = recvVoice.startSteam();
            // 텍스트 너비: 320 화면 기준으로 조정 (16 * 20 = 320 픽셀)
            TextToSprite *ttsprites2 = new TextToSprite(&tft, gptmsg, 16 * 20, 1);
            ttsprites2->setBackgroundColor(BG_COLOR);

            while (true)
            {
                TFT_eSprite *sprite = ttsprites2->getNextSprite(10, START_Y);
                if (sprite != nullptr)
                {
                    container.addElement(new ScrollElement(10, START_Y, sprite->width(), sprite->height(), sprite, 1));
                    container.updateAndDraw(VERTICAL_STEP);
                }
                else
                {
                    ESP_LOGD("TextToSprite", "sprite is null");
                    delete ttsprites2; // TextToSprite 객체 메모리 해제
                    break;
                }
            }

            int err = recvVoice.playStreamData();
            buttonWasPressed = true;
        }
    }
}

void pressedButton()
{
    footerUI(1);
    tft.drawString("listening...", 10, START_Y);
}


// 하단 UI 변경 (320x240 화면 기준)
void footerUI(int state)
{
    int footerY = SCREEN_HEIGHT - 45;  // 하단에서 45픽셀 위
    int footerX = 10;
    int footerWidth = SCREEN_WIDTH - 20;  // 양쪽 여백 10픽셀
    int footerHeight = 35;
    int textY = footerY + 10;
    
    if (state == 0)
    {
        tft.drawRoundRect(footerX, footerY, footerWidth, footerHeight, 8, TFT_WHITE);
        tft.drawString("Press BOOT for voice", footerX + 5, textY, 0);
    }
    else if (state == 1)
    {
        tft.fillRect(footerX + 5, textY - 2, footerWidth - 10, 18, BG_COLOR);  // 문자영역 지우기
        tft.drawString("Voice recognition...", footerX + 5, textY, 1);
    }
    else if (state == 2)
    {
        tft.fillRect(footerX + 5, textY - 2, footerWidth - 10, 18, BG_COLOR);  // 문자영역 지우기
        tft.drawString("Press BOOT for voice", footerX + 5, textY, 1);
    }
}
