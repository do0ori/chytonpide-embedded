#ifndef I2SAUDIORECEIVER_H
#define I2SAUDIORECEIVER_H

#include <WiFi.h>
#include <WiFiClient.h>

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

#include "driver/i2s.h"
#include <esp_log.h>
#include "Arduino.h"

class I2SAudioReceiver
{
public:
    I2SAudioReceiver();
    ~I2SAudioReceiver();

    // I2S 설정
    void setI2sBus(int bus_num);
    void setAudioQuality(int sample_rate, int sample_size, int channels);
    void setI2sPin(int sck, int sd, int ws);
    void setDmaBuf(int len, int count);
    void i2sBegin();

    // Wi-Fi 설정
    void setWifiClient(WiFiClient &wifiClient);

    // 서버 주소 설정
    void setServerAddr(const char *ip, uint16_t port);

    // 수신하며 오디오 재생
    String startSteam();
    int playStreamData();

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

    uint8_t tempBuffer[1026];
    uint8_t dataBuffer[1024];
    uint8_t mac[6];

    WiFiClient *client;

    char *serverIP;
    uint16_t serverPort;

    QueueHandle_t i2s_queue; // DMA 상태이벤트 구현은 추후 다른 프로젝트때 해야겠다.

    bool _connectServer();
    void _disconnectServer();
    void _sendReadyToRecvProtocol(); // 수신 준비 완료 신호 전송

    bool _readFully(uint8_t *buffer, size_t length);

    void _clearI2sBus();
    uint16_t _receiveServerData(); // 1028바이트 데이터 수신후 2바이트(uint16_t)는 반환하고,1024 dataBuffer맴버변수에 저장
    bool _playData(int size);      // 1024바이트 데이터를 I2S로 전송

    int8_t isDmaBroken();
};

#endif