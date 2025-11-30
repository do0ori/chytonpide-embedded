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

### 3. 디바이스 제어

디바이스의 LED 및 LCD(Face Emotion) 상태를 조회하거나 업데이트합니다.

#### 3.1 LED 상태 조회

**`GET /devices/:serial/led`**

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `serial` | string | ✅ | 디바이스 시리얼 ID (예: `xJN2wsF850yqWQfBUkGP`) |

#### 요청 예시

```bash
curl "http://localhost:8000/devices/xJN2wsF850yqWQfBUkGP/led"
```

#### 응답

```json
{
  "is_led_on": true,
  "updated_at": "2025-11-29T11:50:00.123456+09:00"
}
```

**참고**: LED 상태가 설정되지 않은 디바이스는 기본값(`is_led_on: false`)을 반환합니다.

---

#### 3.2 LCD Face Emotion 상태 조회

**`GET /devices/:serial/lcd`**

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `serial` | string | ✅ | 디바이스 시리얼 ID (예: `xJN2wsF850yqWQfBUkGP`) |

#### 요청 예시

```bash
curl "http://localhost:8000/devices/xJN2wsF850yqWQfBUkGP/lcd"
```

#### 응답

```json
{
  "face": "HAPPY",
  "updated_at": "2025-11-29T11:50:00.123456+09:00"
}
```

**참고**: Face Emotion 상태가 설정되지 않은 디바이스는 기본값(`face: "NEUTRAL"`)을 반환합니다.

---

#### 3.3 디바이스 상태 업데이트

**`PATCH /devices/:serial`**

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `serial` | string | ✅ | 디바이스 시리얼 ID (예: `xJN2wsF850yqWQfBUkGP`) |

#### 요청 헤더

```
Content-Type: application/x-www-form-urlencoded
```

#### Form Data

| 필드 | 타입 | 필수 | 설명 |
|-----|------|------|------|
| `is_led_on` | string | ❌ | LED 상태 (`"true"` 또는 `"false"`) |
| `led_face` | string | ❌ | Face Emotion 상태 (예: `"HAPPY"`, `"SAD"`, `"NEUTRAL"`, `"ANGRY"` 등) |

**참고**: 두 필드 모두 선택사항이며, 전송한 필드만 업데이트됩니다.

#### 요청 예시

**LED만 업데이트:**
```bash
curl -X PATCH "http://localhost:8000/devices/xJN2wsF850yqWQfBUkGP" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "is_led_on=true"
```

**Face Emotion만 업데이트:**
```bash
curl -X PATCH "http://localhost:8000/devices/xJN2wsF850yqWQfBUkGP" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "led_face=HAPPY"
```

**둘 다 업데이트:**
```bash
curl -X PATCH "http://localhost:8000/devices/xJN2wsF850yqWQfBUkGP" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "is_led_on=true&led_face=HAPPY"
```

#### 응답

```json
{
  "status": "success",
  "message": "Device updated",
  "serial": "xJN2wsF850yqWQfBUkGP",
  "updated_fields": ["LED: ON", "Face: HAPPY"]
}
```

---

## 테스트 스크립트

API 테스트를 위한 Python 스크립트가 제공됩니다.

### LED 제어

```bash
# LED 켜기
python src/server/set_led.py xJN2wsF850yqWQfBUkGP true

# LED 끄기
python src/server/set_led.py xJN2wsF850yqWQfBUkGP false
```

### Face Emotion 제어

```bash
# Face Emotion 설정
python src/server/set_face_emotion.py xJN2wsF850yqWQfBUkGP HAPPY

# Face Emotion 조회
python src/server/set_face_emotion.py xJN2wsF850yqWQfBUkGP --get
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
- 디바이스 업데이트 API는 `application/x-www-form-urlencoded` 형식입니다.
- 모든 타임스탬프는 ISO 8601 형식(`YYYY-MM-DDTHH:mm:ss.ssssss+09:00`)입니다.
- 상태가 설정되지 않은 디바이스는 기본값을 반환합니다:
  - LED: `is_led_on: false`
  - Face Emotion: `face: "NEUTRAL"`
- 디바이스 시리얼 ID는 프로토타입의 경우 `xJN2wsF850yqWQfBUkGP`를 사용합니다.

