#include "I2SAudioSender.h"
#include "esp_err.h"

I2SAudioSender::I2SAudioSender()
{
    // 생성자에서 필요한 초기화 수행
    this->serverIP = nullptr;
    this->serverPort = 0;

    // I2S 구성
    this->setI2sBus(0);
    this->setAudioQulity(16000, 16, 1);
    this->setI2sPin(5, 6, 7);
    this->setDmaBuf(1024, 5);

    WiFi.macAddress(this->mac);
}

I2SAudioSender::~I2SAudioSender()
{
    // 소멸자에서 필요한 자원 해제 수행
    if (serverIP != nullptr)
    {
        delete[] serverIP;
    }
}

void I2SAudioSender::setI2sBus(int i2s_bus_num)
{
    if (i2s_bus_num == 0)
    {
        this->i2sBusNum = I2S_NUM_0;
    }
    else
    {
        this->i2sBusNum = I2S_NUM_1;
    }
}

void I2SAudioSender::setAudioQulity(int sample_rate, int sample_size, int channels)
{
    this->sampleRate = sample_rate;
    this->sampleSize = sample_size;
    this->ch = channels;
}
void I2SAudioSender::setI2sPin(int sck, int sd, int ws)
{
    this->sckPin = sck;
    this->sdPin = sd;
    this->wsPin = ws;
}
void I2SAudioSender::setDmaBuf(int len, int count)
{
    this->dmaLen = len;
    this->dmaCount = count;
}

void I2SAudioSender::i2sBegin()
{
    this->i2sConfig = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = this->sampleRate,
        .bits_per_sample = (i2s_bits_per_sample_t)this->sampleSize,
        .channel_format = this->ch == 1 ? I2S_CHANNEL_FMT_ONLY_RIGHT : I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = this->dmaCount,
        .dma_buf_len = this->dmaLen,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0};

    this->pinConfig = {
        .bck_io_num = this->sckPin,
        .ws_io_num = this->wsPin,
        .data_out_num = -1,
        .data_in_num = this->sdPin};

    i2s_driver_install(this->i2sBusNum, &this->i2sConfig, 4, &this->i2s_queue);
    i2s_set_pin(this->i2sBusNum, &this->pinConfig);
    i2s_stop(this->i2sBusNum);
}

// Wi-Fi 관련
void I2SAudioSender::setWifiClient(WiFiClient &wifiClient)
{
    client = &wifiClient;
}

void I2SAudioSender::setServerAddr(const char *ip, uint16_t port)
{
    if (serverIP != nullptr)
    {
        delete[] serverIP;
    }
    serverIP = new char[strlen(ip) + 1];
    strcpy(serverIP, ip);
    serverPort = port;
}

void I2SAudioSender::openFile()
{
    this->_connectServer();
    this->_clearI2sBus();
    this->_sendOpenFileProtocol();
}

void I2SAudioSender::writeData()
{
    this->_sendFileData();
}

String I2SAudioSender::closeFile()
{
    i2s_stop(this->i2sBusNum); // TODO: 이거 정리
    this->_sendCloseFileProtocol();
    this->_disconnectServer();
    return whisper_translate;
}

String I2SAudioSender::getWhisperString(){
    return whisper_translate;
}
bool I2SAudioSender::_connectServer()
{
    if (!this->client->connected())
    {
        if (this->client->connect(this->serverIP, this->serverPort))
        {
            return true;
        }
    }
    return false;
}

void I2SAudioSender::_clearI2sBus()
{
    i2s_zero_dma_buffer(this->i2sBusNum);
    i2s_start(this->i2sBusNum);
}

void I2SAudioSender::_sendOpenFileProtocol()
{
    uint16_t signal_start = 3006;
    memcpy(this->dataBuffer, &signal_start, sizeof(signal_start));
    memcpy(this->dataBuffer + 2, this->mac, 6);
    this->client->write(this->dataBuffer, 1026);
}

void I2SAudioSender::_sendFileData()
{
    size_t bytes_read;
    i2s_read(this->i2sBusNum, &this->audioData, sizeof(this->audioData), &bytes_read, portMAX_DELAY); // 클래스 멤버 변수 i2sBusNum 사용
    memcpy(this->dataBuffer, &bytes_read, sizeof(bytes_read));
    memcpy(&this->dataBuffer[2], this->audioData, bytes_read);
    this->client->write(this->dataBuffer, 1026);
}

void I2SAudioSender::_sendCloseFileProtocol()
{
    uint16_t signal_end = 3001;
    memcpy(this->dataBuffer, &signal_end, sizeof(signal_end));
    this->client->write(dataBuffer, 1026);

    this->_readFully(this->dataBuffer, 1026);
    uint16_t returnValue = *((uint16_t *)this->dataBuffer);
    whisper_translate = "";
    for (int i = 2; i < 2 + returnValue; ++i)
    {
        whisper_translate += (char)dataBuffer[i];
    }
    Serial.println(whisper_translate);
    
    // ESP_LOGI("I2SAudioSender", "서버로부터 받은 응답: %s", whisper_translate.c_str());
}

void I2SAudioSender::_disconnectServer()
{
    if (this->client->connected())
    {
        this->client->stop();
    }
}

int8_t I2SAudioSender::getDmaEvent()
{
    i2s_event_t event;
    if (xQueueReceive(i2s_queue, &event, 0)) // Non-blocking
    {
        switch (event.type)
        {
        case I2S_EVENT_DMA_ERROR:
            ESP_LOGE("I2S", "DMA 오류 발생");
            // DMA 오류 처리
            break;
        case I2S_EVENT_TX_DONE:
            ESP_LOGI("I2S", "전송 완료");
            // 전송 완료 처리
            break;
        case I2S_EVENT_RX_DONE:
            ESP_LOGI("I2S", "수신 완료");
            // 수신 완료 처리
            break;
        case I2S_EVENT_TX_Q_OVF:
            ESP_LOGW("I2S", "전송 큐 오버플로");
            // 전송 큐 오버플로 처리
            break;
        case I2S_EVENT_RX_Q_OVF:
            ESP_LOGW("I2S", "수신 큐 오버플로");
            // 수신 큐 오버플로 처리
            break;
        default:
            ESP_LOGI("I2S", "기타 이벤트");
            // 기타 이벤트 처리
            break;
        }
    }
    // 현재 DMA 카운트를 반환하는 로직 구현
    return 0; // 임시 반환 값
}

bool I2SAudioSender::_readFully(uint8_t *buffer, size_t length)
{
    size_t totalBytesRead = 0;
    int bytesRead = 0;
    while (totalBytesRead < length)
    {
        bytesRead = this->client->read(buffer + totalBytesRead, length - totalBytesRead);
        if (bytesRead > 0)
        {

            totalBytesRead += bytesRead;
        }
        else if (bytesRead < 0)
        {
            // 오류 발생
            ESP_LOGE("_readFully()", "서버로부터 데이터 수신 중 오류 발생");
            return false;
        }
        // else if (bytesRead == 0)
        // {
        //     ESP_LOGD("_readFully()", "esp32 처리속도 부족으로 TCP프로토콜에 의한 지연");
        // }
    }
    if (totalBytesRead == length)
    {
        return true;
    }
    else
    {
        ESP_LOGE("_readFully()", "요청된 길이만큼 데이터를 읽지못함");
        return false;
    }
}
