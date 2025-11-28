#include "I2SAudioReceiver.h"
#include "esp_err.h"

I2SAudioReceiver::I2SAudioReceiver()
{
    // 생성자에서 필요한 초기화 수행
    this->serverIP = nullptr;
    this->serverPort = 0;

    // I2S 구성
    this->setI2sBus(1);
    this->setAudioQuality(16000, 16, 1);
    this->setI2sPin(15, 16, 17);
    this->setDmaBuf(1024, 5);
    WiFi.macAddress(this->mac);
}

I2SAudioReceiver::~I2SAudioReceiver()
{
    // 소멸자에서 필요한 자원 해제 수행
    if (serverIP != nullptr)
    {
        delete[] serverIP;
    }
}

// I2S 관련

void I2SAudioReceiver::setI2sBus(int i2s_bus_num)
{
    // I2S 버스 설정 로직 구현
    if (i2s_bus_num == 0)
    {
        this->i2sBusNum = I2S_NUM_0;
    }
    else
    {
        this->i2sBusNum = I2S_NUM_1;
    }
}

void I2SAudioReceiver::setAudioQuality(int sample_rate, int sample_size, int channels)
{
    // 오디오 품질 설정 로직 구현
    this->sampleRate = sample_rate;
    this->sampleSize = sample_size;
    this->ch = channels;
}

void I2SAudioReceiver::setI2sPin(int sck, int sd, int ws)
{
    // I2S 핀 설정 로직 구현
    this->sckPin = sck;
    this->sdPin = sd;
    this->wsPin = ws;
}

void I2SAudioReceiver::setDmaBuf(int len, int count)
{
    // DMA 버퍼 설정 로직 구현
    this->dmaLen = len;
    this->dmaCount = count;
}

void I2SAudioReceiver::i2sBegin()
{
    // I2S 초기화 로직 구현
    this->i2sConfig = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = this->sampleRate,
        .bits_per_sample = (i2s_bits_per_sample_t)this->sampleSize,
        .channel_format = this->ch == 1 ? I2S_CHANNEL_FMT_ONLY_LEFT : I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = this->dmaCount,
        .dma_buf_len = this->dmaLen,
        .use_apll = false};

    this->pinConfig = {
        .bck_io_num = this->sckPin,
        .ws_io_num = this->wsPin,
        .data_out_num = this->sdPin,
        .data_in_num = -1};

    i2s_driver_install(this->i2sBusNum, &this->i2sConfig, 4, &this->i2s_queue);
    i2s_set_pin(this->i2sBusNum, &this->pinConfig);
    i2s_stop(this->i2sBusNum);
}

// Wi-Fi 관련
void I2SAudioReceiver::setWifiClient(WiFiClient &wifiClient)
{
    client = &wifiClient;
}

// 서버 주소 설정
void I2SAudioReceiver::setServerAddr(const char *ip, uint16_t port)
{
    // 서버 주소 설정 로직 구현
    if (serverIP != nullptr)
    {
        delete[] serverIP;
    }
    serverIP = new char[strlen(ip) + 1];
    strcpy(serverIP, ip);
    serverPort = port;
}
String I2SAudioReceiver::startSteam()
{
    this->_connectServer();
    this->_clearI2sBus();
    this->_sendReadyToRecvProtocol();

    this->_readFully(this->tempBuffer, 1026);
    uint16_t returnValue = *((uint16_t *)this->tempBuffer);
    String server_msg = "";
    for (int i = 2; i < 2 + returnValue; ++i)
    {
        server_msg += (char)tempBuffer[i];
    }
    return server_msg;
}
int I2SAudioReceiver::playStreamData()
{
    
    int result = 0;
    bool done = false;
    this->client->write(tempBuffer, 1026); //더미 보내기
    while (!done)
    {
        uint16_t size = this->_receiveServerData();
        //  size가 3001이면 파일끝, -1이면 오류
        if (0 < size && size <= 1024)
        {
            ESP_LOGE("음성 출력", "고고");
            bool success = this->_playData(size);
            if (!success)
            {
                ESP_LOGE("소켓 나가리", "서버꺼졌니?");
                result = 1;
                break;
            }
        }
        else if (size == 3001) // 파일끝
        {
            done = true;
        }
        else if (size == 65535) // socket 오류
        {
            ESP_LOGE("소켓 나가리", "서버꺼졌니?");
            result = 1;
            break;
        }

        int8_t event = isDmaBroken();
        if (event > 0)
        {
            ESP_LOGE("소켓 나가리", "서버꺼졌니?");
            result = 1;
            break;
        }
    }

    this->_disconnectServer();
    i2s_zero_dma_buffer(this->i2sBusNum);
    i2s_stop(this->i2sBusNum);
    return 0;
}

bool I2SAudioReceiver::_connectServer()
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

void I2SAudioReceiver::_disconnectServer()
{
    if (this->client->connected())
    {
        this->client->stop();
    }
}

void I2SAudioReceiver::_clearI2sBus()
{
    i2s_stop(this->i2sBusNum);
    i2s_zero_dma_buffer(this->i2sBusNum);
    i2s_start(this->i2sBusNum);
}

bool I2SAudioReceiver::_readFully(uint8_t *buffer, size_t length)
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
            ESP_LOGE("수신중에", "소켓 오류 발생");
            return false;
        }
    }
    if (totalBytesRead == length)
    {
        return true;
    }
    else
    {
        ESP_LOGE("나가리", "요청된 길이만큼 데이터를 읽지못함");
        return false;
    }
}

uint16_t I2SAudioReceiver::_receiveServerData()
{
    if (!_readFully(this->tempBuffer, 1026))
    {
        return 65535; // 오류 발생
    }
    // 처음 2바이트 파싱, 3001 이면 파일끝, 0 ~ 1024 이면 유요한 데이터
    uint16_t returnValue = *((uint16_t *)this->tempBuffer);
    memcpy(this->dataBuffer, this->tempBuffer + 2, 1024);
    return returnValue;
}

void I2SAudioReceiver::_sendReadyToRecvProtocol()
{
    // 소캣 flush
    while (this->client->available() > 0)
    {
        this->client->read();
    }

    // 수신 준비 완료 신호 전송 로직
    uint16_t signal_start = 3006;
    memcpy(tempBuffer, &signal_start, sizeof(signal_start));
    memcpy(tempBuffer + 2, this->mac, 6);
    this->client->write(tempBuffer, 1026);
}

bool I2SAudioReceiver::_playData(int size)
{
    size_t bytes_written = 0;
    size_t total_bytes_written = 0;

    while (total_bytes_written < size)
    {
        i2s_write(this->i2sBusNum, this->dataBuffer + total_bytes_written, size - total_bytes_written, &bytes_written, portMAX_DELAY);
        if (bytes_written > 0)
        {
            total_bytes_written += bytes_written;
        }
        else
        {
            // bytes_written이 0이면 쓰기 작업에 실패한 것으로 간주
            // 버퍼 오버플로가 발생했을 수 있음
            // 하드웨어 처리속도 한계
            // 물리적 손상
            // arduino-esp 더 뒤져보자
            // 그냥 맘편하게 네트워크지연으로 싸잡아 처리하면될듯
            ESP_LOGE("i2s작성 실패", "이거 보이면 좌절하셈");
            return 0;
        }
    }
    return 1;
}

int8_t I2SAudioReceiver::isDmaBroken()
{
    // I2S_EVENT_DMA_ERROR DMA 오류 발생
    // I2S_EVENT_TX_DONE 전송 완료
    // I2S_EVENT_RX_DONE 수신 완료
    // I2S_EVENT_TX_Q_OVF 전송 큐 오버플로
    // I2S_EVENT_RX_Q_OVF 수신 큐 오버플로
    i2s_event_t event;
    if (xQueueReceive(i2s_queue, &event, 0)) // 0이 논블로킹이였던가 어차피 노상관
    {
        switch (event.type)
        {
        case I2S_EVENT_TX_Q_OVF:
            ESP_LOGE("DMA 이상감지", "DMA 오버플로우 발생");
            return 1;

        case I2S_EVENT_DMA_ERROR:
            ESP_LOGE("DMA 이상감지", "DMA 오류 발생");
            return 2;
        }
    }
    return 0;
}
