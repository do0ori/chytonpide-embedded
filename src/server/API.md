# Citonphyde Sensor Server API 명세

> RESTful API for Citonphyde IoT Device Management

## 목차

- [기본 정보](#기본-정보)
- [인증](#인증)
- [API 엔드포인트](#api-엔드포인트)
  - [헬스 체크](#1-헬스-체크)
  - [센서 데이터](#2-센서-데이터)
  - [LED 제어](#3-led-제어)
  - [Face Emotion](#4-face-emotion)

---

## 기본 정보

- **Base URL**: `http://localhost:8000` (로컬) / `https://chytonpide.azurewebsites.net` (프로덕션)
- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Content-Type**: 
  - `application/json` (대부분의 API)
  - `application/x-www-form-urlencoded` (센서 데이터 업로드)

---

## 인증

현재 버전은 인증을 사용하지 않습니다.

---

## API 엔드포인트

### 1. 헬스 체크

서버 상태를 확인합니다.

**`GET /health`**

#### 응답

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.123456"
}
```

---

### 2. 센서 데이터

ESP32 디바이스에서 센서 데이터를 업로드합니다.

**`POST /sensor_data`**

#### 요청 헤더

```
Content-Type: application/x-www-form-urlencoded
```

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `serial` | string | ✅ | 디바이스 ID (예: `ESP32-S3-001`) |
| `temperature` | float | ✅ | 온도 (°C) |
| `humidity` | float | ✅ | 습도 (%) |
| `illuminance` | string | ❌ | 조도 (기본값: `"0"`) |

#### 요청 예시

```bash
curl -X POST "http://localhost:8000/sensor_data" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "serial=ESP32-S3-001&temperature=25.5&humidity=60.0&illuminance=0"
```

#### 응답

```json
{
  "status": "success",
  "message": "Sensor data received",
  "received_data": {
    "serial": "ESP32-S3-001",
    "temperature": 25.5,
    "humidity": 60.0,
    "illuminance": "0",
    "timestamp": "2024-01-15T10:30:00.123456"
  }
}
```

---

### 3. LED 제어

디바이스의 LED 상태를 설정하거나 조회합니다.

#### 3.1 LED 상태 설정

**`POST /led`**

#### 요청 헤더

```
Content-Type: application/json
```

#### 요청 Body

```json
{
  "device_id": "0000541217D9B4DC",
  "led_on": true
}
```

| 필드 | 타입 | 필수 | 설명 |
|-----|------|------|------|
| `device_id` | string | ✅ | 디바이스 ID |
| `led_on` | boolean | ✅ | LED 상태 (`true`: ON, `false`: OFF) |

#### 요청 예시

```bash
curl -X POST "http://localhost:8000/led" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "0000541217D9B4DC",
    "led_on": true
  }'
```

#### 응답

```json
{
  "status": "success",
  "message": "LED state updated",
  "led_state": {
    "device_id": "0000541217D9B4DC",
    "led_on": true,
    "updated_at": "2024-01-15T10:30:00.123456"
  }
}
```

#### 3.2 LED 상태 조회

**`GET /led`**

#### Query Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `device_id` | string | ❌ | 조회할 디바이스 ID (없으면 모든 디바이스 조회) |

#### 요청 예시

**특정 디바이스 조회:**
```bash
curl "http://localhost:8000/led?device_id=0000541217D9B4DC"
```

**모든 디바이스 조회:**
```bash
curl "http://localhost:8000/led"
```

#### 응답 (특정 디바이스)

```json
{
  "status": "success",
  "led_state": {
    "device_id": "0000541217D9B4DC",
    "led_on": false,
    "updated_at": "2024-01-15T10:30:00.123456"
  }
}
```

#### 응답 (모든 디바이스)

```json
{
  "status": "success",
  "led_states": {
    "0000541217D9B4DC": {
      "led_on": true,
      "updated_at": "2024-01-15T10:30:00.123456"
    },
    "ESP32-S3-001": {
      "led_on": false,
      "updated_at": "2024-01-15T10:25:00.123456"
    }
  }
}
```

**참고**: LED 상태가 설정되지 않은 디바이스는 기본값(`led_on: false`)을 반환합니다.

---

### 4. Face Emotion

디바이스의 표정(감정) 상태를 설정하거나 조회합니다.

#### 4.1 Face Emotion 설정

**`POST /face_emotion`**

#### 요청 헤더

```
Content-Type: application/json
```

#### 요청 Body

```json
{
  "device_id": "0000541217D9B4DC",
  "emotion": "HAPPY"
}
```

| 필드 | 타입 | 필수 | 설명 |
|-----|------|------|------|
| `device_id` | string | ✅ | 디바이스 ID |
| `emotion` | string | ✅ | 감정 상태 (자유 형식 텍스트, 예: `"HAPPY"`, `"SAD"`, `"NEUTRAL"`, `"ANGRY"` 등) |

#### 요청 예시

```bash
curl -X POST "http://localhost:8000/face_emotion" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "0000541217D9B4DC",
    "emotion": "HAPPY"
  }'
```

#### 응답

```json
{
  "status": "success",
  "message": "Face emotion state updated",
  "face_emotion_state": {
    "device_id": "0000541217D9B4DC",
    "emotion": "HAPPY",
    "updated_at": "2024-01-15T10:30:00.123456"
  }
}
```

#### 4.2 Face Emotion 조회

**`GET /face_emotion`**

#### Query Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `device_id` | string | ❌ | 조회할 디바이스 ID (없으면 모든 디바이스 조회) |

#### 요청 예시

**특정 디바이스 조회:**
```bash
curl "http://localhost:8000/face_emotion?device_id=0000541217D9B4DC"
```

**모든 디바이스 조회:**
```bash
curl "http://localhost:8000/face_emotion"
```

#### 응답 (특정 디바이스)

```json
{
  "status": "success",
  "face_emotion_state": {
    "device_id": "0000541217D9B4DC",
    "emotion": "NEUTRAL",
    "updated_at": "2024-01-15T10:30:00.123456"
  }
}
```

#### 응답 (모든 디바이스)

```json
{
  "status": "success",
  "face_emotion_states": {
    "0000541217D9B4DC": {
      "emotion": "HAPPY",
      "updated_at": "2024-01-15T10:30:00.123456"
    },
    "ESP32-S3-001": {
      "emotion": "SAD",
      "updated_at": "2024-01-15T10:25:00.123456"
    }
  }
}
```

**참고**: Face Emotion 상태가 설정되지 않은 디바이스는 기본값(`emotion: "NEUTRAL"`)을 반환합니다.

---

## 테스트 스크립트

API 테스트를 위한 Python 스크립트가 제공됩니다.

### LED 제어

```bash
# LED 켜기
python src/server/set_led.py 0000541217D9B4DC true

# LED 끄기
python src/server/set_led.py 0000541217D9B4DC false
```

### Face Emotion 제어

```bash
# Face Emotion 설정
python src/server/set_face_emotion.py 0000541217D9B4DC HAPPY

# Face Emotion 조회
python src/server/set_face_emotion.py 0000541217D9B4DC --get

# 모든 디바이스 조회
python src/server/set_face_emotion.py --get
```

---

## 에러 처리

### 일반적인 에러 응답 형식

```json
{
  "detail": "Error message here"
}
```

### HTTP 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| `200` | 성공 |
| `400` | 잘못된 요청 (파라미터 오류) |
| `404` | 리소스를 찾을 수 없음 |
| `500` | 서버 내부 오류 |

---

## 서버 실행

```bash
# 로컬 서버 실행
python src/server/main.py

# 또는
cd src/server
python main.py
```

서버는 기본적으로 `http://0.0.0.0:8000`에서 실행됩니다.

---

## FastAPI 자동 문서

서버 실행 후 다음 URL에서 인터랙티브 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 참고사항

- 센서 데이터는 `application/x-www-form-urlencoded` 형식으로만 전송됩니다.
- LED 및 Face Emotion API는 `application/json` 형식입니다.
- 모든 타임스탬프는 ISO 8601 형식(`YYYY-MM-DDTHH:mm:ss.ssssss`)입니다.
- 상태가 설정되지 않은 디바이스는 기본값을 반환합니다:
  - LED: `led_on: false`
  - Face Emotion: `emotion: "NEUTRAL"`

