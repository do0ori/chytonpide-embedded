# server_tcp - TCP Device Server

ESP32 디바이스와 외부 제어 클라이언트를 위한 TCP 서버입니다.
기존 `src/server/main.py` (FastAPI HTTP)는 유지하고, 이 폴더에서 TCP 전용 서버를 구현합니다.

## 개요

기존 HTTP 서버는 디바이스가 LED/LCD 상태를 **매 1~2초마다 polling**하는 구조였습니다.
이 TCP 서버는 상태 변경 시 **서버가 디바이스에 push**하는 모델로, 디바이스의 불필요한 네트워크 요청을 제거합니다.

```
기존 HTTP:
  Device --(GET /led, 매 1초)--> Server   (디바이스가 물어봄)
  Device --(GET /lcd, 매 2초)--> Server   (디바이스가 물어봄)

TCP push:
  Control --(set_device)--> Server --(state_update)--> Device  (변경 시에만 push)
```

---

## TCP 프로토콜

**전송 포맷:** newline-delimited JSON (`\n` 구분)

### 클라이언트 유형

서버는 두 종류의 TCP 클라이언트를 받습니다:

| 유형 | 첫 메시지 | 역할 |
|------|-----------|------|
| **device** | `hello` | ESP32 디바이스. 상태 push 수신, 센서 데이터 전송 |
| **control** | `set_device` | 외부 제어 클라이언트 (AI voice, 웹 대시보드 등). 디바이스 상태 변경 |

### 메시지 타입

| 방향 | 타입 | 설명 |
|------|------|------|
| Device -> Server | `hello` | `{"type":"hello","serial":"xJN2wsF850yqWQfBUkGP"}` |
| Server -> Device | `hello_ack` | `{"type":"hello_ack","is_led_on":false,"face":"NEUTRAL"}` |
| Device -> Server | `sensor_data` | `{"type":"sensor_data","serial":"...","temperature":25.5,"humidity":60.0,"illuminance":0}` |
| Server -> Device | `ack` | `{"type":"ack"}` |
| Control -> Server | `set_device` | `{"type":"set_device","serial":"...","is_led_on":true,"face":"HAPPY"}` |
| Server -> Control | `ack` / `error` | 처리 결과 |
| Server -> Device | `state_update` | `{"type":"state_update","is_led_on":true}` 또는 `{"type":"state_update","face":"HAPPY"}` 또는 둘 다 |
| Server -> Device | `ping` | `{"type":"ping"}` (30초 간격) |
| Device -> Server | `pong` | `{"type":"pong"}` |

### 필드명

- `is_led_on` (boolean): LED 릴레이 상태
- `face` (string): 감정 표정 (`HAPPY`, `SAD`, `ANGRY`, `TIRED`, `SURPRISED`, `CALM`, `NEUTRAL`, `DEFAULT`)

기존 HTTP 서버의 `led_face` / `face` 네이밍 불일치를 TCP에서는 `face`로 통일합니다.

---

## 서버 구현 설계

### 기술 스택

- Python 3.7+
- `asyncio.start_server()` 기반
- 외부 라이브러리 의존 없음 (stdlib만 사용)

### 연결 관리

```python
# serial -> StreamWriter 매핑 (접속 중인 디바이스 추적)
device_connections: dict[str, asyncio.StreamWriter] = {}

# 디바이스 상태 저장
device_states: dict[str, dict] = {}
# 기본값: {"is_led_on": False, "face": "NEUTRAL"}
```

### 연결 흐름

**디바이스 연결:**
1. TCP 연결 수립
2. 디바이스가 `hello` 전송 (serial 포함)
3. 서버가 `device_connections[serial] = writer`로 등록
4. 서버가 `hello_ack` 응답 (현재 상태 포함)
5. 이후 서버가 `state_update`를 push, 디바이스가 `sensor_data`를 전송
6. 서버가 30초마다 `ping` 전송, 디바이스가 `pong` 응답
7. 연결 종료 시 `device_connections`에서 제거

**제어 클라이언트 연결:**
1. TCP 연결 수립
2. 클라이언트가 `set_device` 전송
3. 서버가 상태 저장 + 해당 디바이스에 `state_update` push
4. 서버가 `ack` 응답
5. 연결 유지 또는 종료 (control 클라이언트는 일회성이어도 됨)

### Push 로직 (핵심)

```python
async def handle_set_device(serial: str, data: dict):
    state = device_states.setdefault(serial, {"is_led_on": False, "face": "NEUTRAL"})

    update = {}
    if "is_led_on" in data:
        state["is_led_on"] = data["is_led_on"]
        update["is_led_on"] = data["is_led_on"]
    if "face" in data:
        state["face"] = data["face"]
        update["face"] = data["face"]

    # 디바이스가 접속 중이면 즉시 push
    if serial in device_connections:
        msg = json.dumps({"type": "state_update", **update}) + "\n"
        writer = device_connections[serial]
        writer.write(msg.encode())
        await writer.drain()
    # 미접속이면 상태만 저장 -- 다음 hello 때 hello_ack에 포함됨
```

### 상태 기본값

기존 HTTP 서버와 동일:
- LED 미설정 시: `is_led_on: false`
- LCD 미설정 시: `face: "NEUTRAL"`

---

## Keepalive

| 항목 | 값 |
|------|-----|
| 서버 ping 주기 | 30초마다 접속 중인 모든 디바이스에 `ping` 전송 |
| 디바이스 pong 타임아웃 | 60초 내 pong 미수신 시 연결 종료, `device_connections`에서 제거 |
| 연결 종료 처리 | writer 닫기 + `device_connections` 정리 + 로그 출력 |

---

## 실행

```bash
cd src/server_tcp
python main.py
```

기본 포트: `9000` (예정, 기존 HTTP 서버 8000과 분리)

### 수동 테스트

`nc` (netcat) 또는 `telnet`으로 테스트 가능:

```bash
# 디바이스 시뮬레이션
nc localhost 9000
{"type":"hello","serial":"test-device-001"}
# -> {"type":"hello_ack","is_led_on":false,"face":"NEUTRAL"}

# 다른 터미널에서 제어 클라이언트
nc localhost 9000
{"type":"set_device","serial":"test-device-001","face":"HAPPY"}
# -> {"type":"ack"}
# 첫 번째 터미널에 {"type":"state_update","face":"HAPPY"} 가 push됨
```

---

## 검증 시나리오

1. **hello -> hello_ack:** 기본 상태(is_led_on=false, face=NEUTRAL) 포함 확인
2. **sensor_data -> ack:** 센서 데이터 수신 및 로그 출력
3. **set_device -> state_update push:** control 클라이언트에서 상태 변경 시 디바이스에 즉시 push
4. **미접속 디바이스 set_device:** 상태 저장만 되고, 이후 hello 시 hello_ack에 반영
5. **ping/pong:** 30초 후 ping 전송 확인, pong 미응답 시 60초 후 연결 종료
6. **디바이스 재접속:** 연결 끊김 후 재접속 시 hello_ack에 최신 상태 반영

---

## 향후 옵션 (2단계)

- 기존 `src/server/main.py`의 `PATCH /devices/{serial}`이 같은 상태 dict를 공유하도록 병행
  - 이 경우 TCP 서버에 간단한 HTTP 엔드포인트를 추가하거나, 프로세스 간 상태 공유(Redis 등) 필요
- 센서 데이터 DB 영속화 (현재는 in-memory, 서버 재시작 시 소실)
- 다중 디바이스 관리 (serial 기반 라우팅은 이미 설계에 포함)
