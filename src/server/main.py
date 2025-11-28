from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, Form
from pydantic import BaseModel

app = FastAPI(title="Citonphyde Sensor Server", version="1.0.0")

# LED 상태 저장 (device_id별로 관리, serial/device_id 모두 지원)
led_states = {}

# Face Emotion 상태 저장 (device_id별로 관리)
face_emotion_states = {}


class LEDStateRequest(BaseModel):
    device_id: str
    led_on: bool


class FaceEmotionRequest(BaseModel):
    device_id: str
    emotion: str  # 자유 형식 텍스트 (예: "HAPPY", "SAD", "NEUTRAL" 등)


@app.get("/")
async def root():
    return {
        "message": "Citonphyde Sensor Server",
        "status": "running",
        "endpoints": {
            "POST /sensor_data": "Send sensor data (temperature, humidity, serial, illuminance)",
            "GET /health": "Health check",
            "POST /led": "Set LED state (on/off)",
            "GET /led": "Get LED state",
            "POST /face_emotion": "Set face emotion (free text format)",
            "GET /face_emotion": "Get face emotion state",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/sensor_data")
async def receive_sensor_data(
    serial: str = Form(...),
    temperature: float = Form(...),
    humidity: float = Form(...),
    illuminance: str = Form("0"),
):
    """
    SHT31 센서 데이터를 받는 엔드포인트

    Firmware에서 form-urlencoded 형식으로 전송:
    - serial: 디바이스 ID (필수)
    - temperature: 온도 (필수)
    - humidity: 습도 (필수)
    - illuminance: 조도 (선택, 기본값: "0")

    Request Body (application/x-www-form-urlencoded):
    serial=ESP32-S3-001&temperature=25.5&humidity=60.0&illuminance=0
    """
    timestamp = datetime.now().isoformat()

    # 로그 출력
    print("=" * 50)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 센서 데이터 수신")
    print(f"  Serial/Device ID: {serial}")
    print(f"  온도: {temperature:.2f} °C")
    print(f"  습도: {humidity:.2f} %")
    print(f"  조도: {illuminance}")
    print(f"  Timestamp: {timestamp}")
    print("=" * 50)

    # 응답 반환
    return {
        "status": "success",
        "message": "Sensor data received",
        "received_data": {
            "serial": serial,
            "temperature": temperature,
            "humidity": humidity,
            "illuminance": illuminance,
            "timestamp": timestamp,
        },
    }


@app.post("/led")
async def set_led_state(request: LEDStateRequest):
    """
    LED 상태를 설정하는 엔드포인트

    Request Body:
    {
        "device_id": "ESP32-S3-001",
        "led_on": true  // true: 켜기, false: 끄기
    }
    """
    # LED 상태 저장
    led_states[request.device_id] = {
        "led_on": request.led_on,
        "updated_at": datetime.now().isoformat(),
    }

    # 로그 출력
    print("=" * 50)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] LED 상태 설정")
    print(f"  Device ID: {request.device_id}")
    print(f"  LED 상태: {'ON' if request.led_on else 'OFF'}")
    print("=" * 50)

    return {
        "status": "success",
        "message": "LED state updated",
        "led_state": {
            "device_id": request.device_id,
            "led_on": request.led_on,
            "updated_at": led_states[request.device_id]["updated_at"],
        },
    }


@app.get("/led")
async def get_led_state(device_id: Optional[str] = None):
    """
    LED 상태를 조회하는 엔드포인트

    Query Parameters:
    - device_id: 조회할 디바이스 ID (선택사항, 없으면 모든 디바이스 상태 반환)
    """
    if device_id:
        # 특정 디바이스의 LED 상태 조회
        # firmware에서 요청할 때 device_id가 없으면 기본값(false) 반환
        if device_id not in led_states:
            # LED 상태가 설정되지 않았으면 기본값(off) 반환
            return {
                "status": "success",
                "led_state": {
                    "device_id": device_id,
                    "led_on": False,  # 기본값: 꺼짐
                    "updated_at": datetime.now().isoformat(),
                },
            }

        state = led_states[device_id]
        return {
            "status": "success",
            "led_state": {
                "device_id": device_id,
                "led_on": state["led_on"],
                "updated_at": state["updated_at"],
            },
        }
    else:
        # 모든 디바이스의 LED 상태 조회
        return {
            "status": "success",
            "led_states": {
                device_id: {
                    "led_on": state["led_on"],
                    "updated_at": state["updated_at"],
                }
                for device_id, state in led_states.items()
            },
        }


@app.post("/face_emotion")
async def set_face_emotion(request: FaceEmotionRequest):
    """
    Face Emotion 상태를 설정하는 엔드포인트

    Request Body:
    {
        "device_id": "ESP32-S3-001",
        "emotion": "HAPPY"  // 자유 형식 텍스트 (예: "HAPPY", "SAD", "NEUTRAL", "ANGRY" 등)
    }
    """
    # Face Emotion 상태 저장
    face_emotion_states[request.device_id] = {
        "emotion": request.emotion,
        "updated_at": datetime.now().isoformat(),
    }

    # 로그 출력
    print("=" * 50)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Face Emotion 상태 설정")
    print(f"  Device ID: {request.device_id}")
    print(f"  Emotion: {request.emotion}")
    print("=" * 50)

    return {
        "status": "success",
        "message": "Face emotion state updated",
        "face_emotion_state": {
            "device_id": request.device_id,
            "emotion": request.emotion,
            "updated_at": face_emotion_states[request.device_id]["updated_at"],
        },
    }


@app.get("/face_emotion")
async def get_face_emotion_state(device_id: Optional[str] = None):
    """
    Face Emotion 상태를 조회하는 엔드포인트

    Query Parameters:
    - device_id: 조회할 디바이스 ID (선택사항, 없으면 모든 디바이스 상태 반환)
    """
    if device_id:
        # 특정 디바이스의 Face Emotion 상태 조회
        if device_id not in face_emotion_states:
            # Face Emotion 상태가 설정되지 않았으면 기본값("NEUTRAL") 반환
            return {
                "status": "success",
                "face_emotion_state": {
                    "device_id": device_id,
                    "emotion": "NEUTRAL",  # 기본값
                    "updated_at": datetime.now().isoformat(),
                },
            }

        state = face_emotion_states[device_id]
        return {
            "status": "success",
            "face_emotion_state": {
                "device_id": device_id,
                "emotion": state["emotion"],
                "updated_at": state["updated_at"],
            },
        }
    else:
        # 모든 디바이스의 Face Emotion 상태 조회
        return {
            "status": "success",
            "face_emotion_states": {
                device_id: {
                    "emotion": state["emotion"],
                    "updated_at": state["updated_at"],
                }
                for device_id, state in face_emotion_states.items()
            },
        }


if __name__ == "__main__":
    print("Starting Citonphyde Sensor Server...")
    print("Server will be available at http://localhost:8000")
    print("API docs available at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
