#ifndef I2SAUDIOSENDER_H
#define I2SAUDIOSENDER_H

#include <WiFi.h>
#include <WiFiClient.h>

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

#include "driver/i2s.h"
#include <esp_log.h>
#include "Arduino.h"

class I2SAudioSender
{

public:
    I2SAudioSender();
    ~I2SAudioSender();

    // I2S 설정
    void setI2sBus(int bus_num);
    void setAudioQulity(int sample_rate, int sample_size, int channels);
    void setI2sPin(int sck, int sd, int ws);
    void setDmaBuf(int len, int count);
    void i2sBegin();

    // Wi-Fi 설정
    void setWifiClient(WiFiClient &wifiClient);
    // 서버 주소 설정
    void setServerAddr(const char *ip, uint16_t port);

    void openFile();
    void writeData();
    String closeFile();
    int8_t getDmaEvent();
    String whisper_translate = "";
    String getWhisperString();

private:
    int sampleRate;
    int sampleSize;
    int ch;
    int sckPin;
    int sdPin;
    int wsPin;
    int dmaLen;
    int dmaCount;

    i2s_port_t i2sBusNum;
    i2s_config_t i2sConfig;
    i2s_pin_config_t pinConfig;

    uint8_t dataBuffer[1026]; // 4바이트 크기 정보 + 1024바이트 데이터
    int16_t audioData[512];
    uint8_t mac[6];

    WiFiClient *client;

    char *serverIP;
    uint16_t serverPort;

    QueueHandle_t i2s_queue;
    bool _connectServer();
    void _disconnectServer();

    void _clearI2sBus();
    void _sendOpenFileProtocol();
    void _sendCloseFileProtocol();
    void _sendFileData();
    bool _readFully(uint8_t *buffer, size_t length);
};

#endif
