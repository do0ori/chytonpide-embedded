# Citonphyde Sensor Server

ESP32 기반 IoT 디바이스를 위한 RESTful API 서버입니다.

## 빠른 시작

### 설치

```bash
# 의존성 설치
pip install -r requirements.txt
```

### 실행

```bash
python main.py
```

서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

### API 문서 확인

서버 실행 후 다음 URL에서 인터랙티브 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 기능

- ✅ 센서 데이터 수신 (온도, 습도, 조도)
- ✅ LED 상태 제어 (설정/조회)
- ✅ Face Emotion 상태 제어 (설정/조회)
- ✅ RESTful API 설계
- ✅ 자동 API 문서 (Swagger/ReDoc)

## API 명세

자세한 API 명세는 [API.md](./API.md)를 참고하세요.

## 주요 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `GET` | `/health` | 서버 상태 확인 |
| `POST` | `/sensor_data` | 센서 데이터 업로드 |
| `POST` | `/led` | LED 상태 설정 |
| `GET` | `/led` | LED 상태 조회 |
| `POST` | `/face_emotion` | Face Emotion 설정 |
| `GET` | `/face_emotion` | Face Emotion 조회 |

## 테스트 스크립트

### LED 제어 테스트

```bash
# LED 켜기
python set_led.py 0000541217D9B4DC true

# LED 끄기
python set_led.py 0000541217D9B4DC false
```

### Face Emotion 테스트

```bash
# Face Emotion 설정
python set_face_emotion.py 0000541217D9B4DC HAPPY

# Face Emotion 조회
python set_face_emotion.py 0000541217D9B4DC --get
```

## 프로덕션 배포

프로덕션 환경에서는 환경 변수나 설정 파일을 통해 Base URL을 변경하세요.

```python
# 기본값
SERVER_BASE_URL = "http://localhost:8000"

# 프로덕션
SERVER_BASE_URL = "https://chytonpide.azurewebsites.net"
```

## 기술 스택

- **FastAPI**: 현대적인 웹 프레임워크
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증

## 라이선스

MIT

