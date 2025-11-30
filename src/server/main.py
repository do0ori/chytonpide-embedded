from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, Form, Path
from pydantic import BaseModel

app = FastAPI(title="Citonphyde Sensor Server", version="1.0.0")

# LED 상태 저장 (serial별로 관리)
led_states = {}

# Face Emotion 상태 저장 (serial별로 관리)
face_emotion_states = {}


@app.get("/")
async def root():
    return {
        "message": "Citonphyde Sensor Server",
        "status": "running",
        "endpoints": {
            "POST /sensor_data": "Send sensor data (temperature, humidity, serial, illuminance)",
            "GET /health": "Health check",
            "GET /devices/:serial/led": "Get LED state",
            "GET /devices/:serial/lcd": "Get LCD face emotion state",
            "PATCH /devices/:serial": "Update device (is_led_on, led_face)",
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


@app.get("/devices/{serial}/led")
async def get_led_state(serial: str = Path(..., description="Device serial ID")):
    """
    LED 상태를 조회하는 엔드포인트

    Path Parameters:
    - serial: 디바이스 시리얼 ID (예: "xJN2wsF850yqWQfBUkGP")
    """
    # LED 상태가 설정되지 않았으면 기본값(off) 반환
    if serial not in led_states:
        return {
            "is_led_on": False,  # 기본값: 꺼짐
            "updated_at": datetime.now().isoformat(),
        }

    state = led_states[serial]
    return {
        "is_led_on": state["is_led_on"],
        "updated_at": state["updated_at"],
    }


@app.get("/devices/{serial}/lcd")
async def get_lcd_state(serial: str = Path(..., description="Device serial ID")):
    """
    LCD Face Emotion 상태를 조회하는 엔드포인트

    Path Parameters:
    - serial: 디바이스 시리얼 ID (예: "xJN2wsF850yqWQfBUkGP")
    """
    # Face Emotion 상태가 설정되지 않았으면 기본값("NEUTRAL") 반환
    if serial not in face_emotion_states:
        return {
            "face": "NEUTRAL",  # 기본값
            "updated_at": datetime.now().isoformat(),
        }

    state = face_emotion_states[serial]
    return {
        "face": state["face"],
        "updated_at": state["updated_at"],
    }


@app.patch("/devices/{serial}")
async def update_device(
    serial: str = Path(..., description="Device serial ID"),
    is_led_on: Optional[str] = Form(None),
    led_face: Optional[str] = Form(None),
):
    """
    디바이스 상태를 업데이트하는 엔드포인트

    Path Parameters:
    - serial: 디바이스 시리얼 ID (예: "xJN2wsF850yqWQfBUkGP")

    Form Data:
    - is_led_on: LED 상태 ("true" 또는 "false", 선택사항)
    - led_face: Face Emotion 상태 (예: "HAPPY", "SAD", "NEUTRAL", 선택사항)
    """
    updated_fields = []

    # LED 상태 업데이트
    if is_led_on is not None:
        led_on_bool = is_led_on.lower() in ("true", "1", "on", "yes")
        led_states[serial] = {
            "is_led_on": led_on_bool,
            "updated_at": datetime.now().isoformat(),
        }
        updated_fields.append(f"LED: {'ON' if led_on_bool else 'OFF'}")

    # Face Emotion 상태 업데이트
    if led_face is not None:
        face_emotion_states[serial] = {
            "face": led_face,
            "updated_at": datetime.now().isoformat(),
        }
        updated_fields.append(f"Face: {led_face}")

    # 로그 출력
    if updated_fields:
        print("=" * 50)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 디바이스 상태 업데이트")
        print(f"  Serial: {serial}")
        for field in updated_fields:
            print(f"  {field}")
        print("=" * 50)

    return {
        "status": "success",
        "message": "Device updated",
        "serial": serial,
        "updated_fields": updated_fields,
    }


if __name__ == "__main__":
    print("Starting Citonphyde Sensor Server...")
    print("Server will be available at http://localhost:8000")
    print("API docs available at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
