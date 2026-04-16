# firmware_tcp - ESP32 TCP Client Firmware

HTTP polling 기반 펌웨어를 **TCP 서버 푸시 모델**로 전환하는 버전입니다.
기존 `src/firmware/firmware.ino`는 유지하고, 이 폴더에서 독립적으로 개발합니다.

## 배경: 왜 TCP인가

### 현재 병목 (`src/firmware/`)

메인 루프가 10ms 주기로 돌지만, HTTP 요청이 직렬로 끼어들어 LCD 애니메이션이 끊깁니다.

```
loop() — 10ms cycle
  ├─ updateLCD() → roboEyes.update()      // ~0ms
  ├─ sensorManager.processUpload()        // 30초마다 HTTP POST, 100~500ms 블로킹
  ├─ relayLedController.update()          // 1초마다 HTTP GET,  100~500ms 블로킹
  ├─ faceEmotionController.update()       // 2초마다 HTTP GET,  100~500ms 블로킹
  └─ delay(10)
```

최악의 경우 한 사이클에서 HTTP 3건이 겹치면 **~1.5초 블로킹**이 발생합니다.
`roboEyes.update()`는 자주 호출돼야 부드러운 표정 애니메이션이 나오는데, 이 사이에 네트워크 요청이 끼면 프레임이 뚝뚝 끊깁니다.

추가로, 각 컨트롤러가 매번 `HTTPClient`를 생성/소멸하므로 TCP 연결 오버헤드도 반복됩니다.

### 전환 핵심: Polling -> Server Push

```
기존 (HTTP polling):
  Device --(GET /devices/{serial}/led)--> Server --(JSON)--> Device  (매 1초)
  Device --(GET /devices/{serial}/lcd)--> Server --(JSON)--> Device  (매 2초)

변경 (TCP push):
  Device --(hello)--> Server --(hello_ack + 현재 상태)--> Device
                      Server --(state_update, 변경 시에만 push)--> Device
  Device --(sensor_data, 30초)--> Server --(ack)--> Device
```

- LED/LCD 상태는 **서버가 변경 시에만 push** -> 디바이스는 polling 불필요
- loop()에서는 소켓에 데이터가 있을 때만 **비차단으로 읽기** -> LCD 렌더링 방해 없음
- 센서 업로드만 디바이스->서버 방향으로 남음 (write는 빠름)

---

## TCP 프로토콜

**전송 포맷:** newline-delimited JSON (`\n` 구분, 한 줄에 하나의 JSON 메시지)

### 메시지 타입

| 방향 | 타입 | 설명 | 예시 |
|------|------|------|------|
| Device -> Server | `hello` | 디바이스 연결 등록 | `{"type":"hello","serial":"xJN2wsF850yqWQfBUkGP"}` |
| Server -> Device | `hello_ack` | 연결 확인 + 현재 상태 | `{"type":"hello_ack","is_led_on":false,"face":"NEUTRAL"}` |
| Device -> Server | `sensor_data` | 센서 업로드 | `{"type":"sensor_data","serial":"...","temperature":25.5,"humidity":60.0,"illuminance":0}` |
| Server -> Device | `ack` | 업로드 성공 | `{"type":"ack"}` |
| Server -> Device | `state_update` | 상태 변경 push | `{"type":"state_update","is_led_on":true}` 또는 `{"type":"state_update","face":"HAPPY"}` 또는 둘 다 |
| Server -> Device | `ping` | Keepalive 요청 | `{"type":"ping"}` |
| Device -> Server | `pong` | Keepalive 응답 | `{"type":"pong"}` |
| Server -> Device | `error` | 에러 | `{"type":"error","message":"unknown serial"}` |

### 필드명

- `is_led_on` (boolean): LED 릴레이 상태
- `face` (string): 감정 표정. 값: `HAPPY`, `SAD`, `ANGRY`, `TIRED`, `SURPRISED`, `CALM`, `NEUTRAL`, `DEFAULT`

기존 HTTP 서버의 `led_face` (PATCH 입력) vs `face` (GET 응답) 네이밍 불일치를 TCP에서는 `face`로 통일합니다.

### hello_ack에 현재 상태를 포함하는 이유

디바이스가 접속(또는 재접속) 직후 별도로 상태 조회를 할 필요 없이, handshake 한 번으로 현재 LED/LCD 상태를 동기화합니다.
재접속 시 서버에서 변경됐을 수 있는 상태를 즉시 반영할 수 있습니다.

---

## 구현 설계

### 파일 구조

```
src/firmware_tcp/
├── firmware_tcp.ino          # 메인 스케치 (loop 구조 변경)
├── TcpDeviceClient.h         # [신규] TCP 클라이언트 헤더
├── TcpDeviceClient.cpp       # [신규] 비차단 수신, 재접속, keepalive
├── SensorManager.h           # HTTP 의존 제거
├── SensorManager.cpp         # TCP 전송으로 변경
├── RelayLedController.h      # polling 제거, applyLedState만 남김
├── RelayLedController.cpp    # polling 제거
├── FaceEmotionController.h   # polling 제거, applyFace만 남김
├── FaceEmotionController.cpp # polling 제거
├── LCDDisplay.h              # 변경 없음
├── LCDDisplay.cpp            # 변경 없음
├── DeviceID.h                # 변경 없음
├── DeviceID.cpp              # 변경 없음
├── WiFiManager.h/cpp         # 변경 없음
├── ButtonHandler.h/cpp       # 변경 없음
└── (라이브러리 파일들)        # 변경 없음
```

### TcpDeviceClient (핵심 신규 모듈)

HTTP를 직접 쓰는 각 컨트롤러 대신, TCP 송수신을 담당하는 공통 클라이언트.

**책임:**
- 서버 접속 및 재접속 (지수 백오프: 1s -> 2s -> 4s -> ... -> 최대 30s)
- `hello` handshake 수행 및 `hello_ack` 파싱
- **비차단 수신:** `WiFiClient.available()`로 데이터 유무만 확인, 없으면 즉시 리턴
- 라인 버퍼링: 수신 데이터를 내부 버퍼에 누적, `\n`이 올 때까지 대기 (partial read 처리)
- JSON 파싱 후 콜백 호출 (`onStateUpdate`)
- 센서 데이터 전송
- Keepalive: `ping` 수신 시 `pong` 응답

**비차단 수신 패턴:**

```cpp
// loop()에서 매번 호출 -- 데이터 없으면 즉시 리턴
void TcpDeviceClient::poll() {
    if (!client.connected()) {
        tryReconnect();  // 백오프 타이머 체크 후 시도
        return;
    }

    // 비차단: 도착한 바이트만 버퍼에 추가
    while (client.available()) {
        char c = client.read();
        if (c == '\n') {
            processLine(lineBuffer);
            lineBuffer = "";
        } else {
            if (lineBuffer.length() < MAX_LINE_LENGTH) {
                lineBuffer += c;
            } else {
                // 비정상 메시지 -- 버퍼 리셋
                lineBuffer = "";
            }
        }
    }
    lastActivity = millis();  // keepalive 타이머 갱신
}
```

`poll()` 호출 시 소켓에 데이터가 없으면 **0ms**, 있어도 JSON 한 줄 파싱 **~1ms** 수준.

### 컨트롤러 변경

**RelayLedController** -- "폴링하는 컨트롤러"에서 "push 받은 상태를 적용하는 액추에이터"로 변경:

```cpp
// 기존: update()에서 HTTP GET 수행 (매 1초, 100~500ms 블로킹)
// 변경: applyLedState()만 남기고, TcpDeviceClient 콜백에서 호출
class RelayLedController {
public:
    void begin(int signalPin, int comPin);
    void applyLedState(bool isLedOn);  // GPIO 제어만 담당
private:
    bool currentState = false;
    int signalPin, comPin;
};
```

**FaceEmotionController** -- 동일한 패턴:

```cpp
class FaceEmotionController {
public:
    void begin(LCDDisplay* lcd);
    void applyFace(const String& face);  // 표정 프리셋 적용만 담당
private:
    String currentFace = "NEUTRAL";
    LCDDisplay* lcdDisplay;
};
```

**SensorManager** -- HTTP POST를 TCP write로 교체:

```cpp
// processUpload()에서 HTTPClient 대신 TcpDeviceClient 사용
void SensorManager::processUpload(TcpDeviceClient& tcpClient) {
    if (!uploadFlag) return;
    uploadFlag = false;
    tcpClient.sendSensorData(serial, avgTemp, avgHumidity, illuminance);
}
```

### 개선된 loop() 흐름

```cpp
void loop() {
    checkBootButton();
    updateLCD();                          // roboEyes.update() -- 항상 즉시 실행

    if (wifiConnected) {
        tcpClient.poll();                 // 비차단: 수신 확인 + state_update 콜백
        sensorManager.update();           // 센서 I2C 읽기 (~1ms)
        sensorManager.processUpload(tcpClient);  // TCP write (~0-1ms)
    }

    delay(10);
}
```

- LED/LCD polling이 사라짐 -> loop당 네트워크 블로킹 최대 ~1ms
- `roboEyes.update()`가 10ms 주기로 안정적으로 호출됨

---

## Keepalive 및 재접속

| 항목 | 값 |
|------|-----|
| 서버 ping 주기 | 30초 |
| 디바이스 pong 응답 | ping 수신 즉시 |
| 서버 측 타임아웃 | pong 60초 미수신 시 연결 종료 |
| 디바이스 측 타임아웃 | 서버로부터 아무 메시지 없이 60초 경과 시 재접속 |
| 재접속 백오프 | 1s -> 2s -> 4s -> 8s -> 16s -> 30s (최대), 성공 시 리셋 |
| WiFi 복구 | WiFi 재연결 감지 시 TCP 재접속 시도, hello handshake로 상태 동기화 |

---

## 리스크

- **TCP write 블로킹:** `WiFiClient.write()`가 전송 버퍼 포화 시 블로킹 가능. sensor_data payload가 작으므로 (~200 bytes) 실질적 문제 가능성 낮음. 필요 시 `client.setNoDelay(true)` (Nagle 비활성화) 적용.
- **라인 버퍼 오버플로:** 비정상 메시지 시 최대 라인 길이(1KB) 초과하면 버퍼 리셋.
- **연속 state_update:** 빠르게 연속 set_device가 오면 state_update가 여러 개 push될 수 있음. 디바이스는 마지막 상태만 적용하면 되므로 문제없음.

---

## 빌드 참고

- 이 폴더가 Arduino IDE에서 독립 프로젝트로 인식되려면 **폴더명과 .ino 파일명이 일치**해야 합니다 (`firmware_tcp/firmware_tcp.ino`).
- 나머지 `.h`/`.cpp` 파일은 같은 폴더에 있으면 자동으로 컴파일에 포함됩니다.
- 기존 `src/firmware/`와 동시에 열지 않도록 주의 (Arduino IDE가 같은 이름의 파일을 충돌로 인식할 수 있음).
