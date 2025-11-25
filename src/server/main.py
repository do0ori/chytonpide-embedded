from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Citonphyde Sensor Server", version="1.0.0")

# LED 상태 저장 (device_id별로 관리)
led_states = {}


class SensorData(BaseModel):
    temperature: float
    humidity: float
    device_id: str = "unknown"
    timestamp: str = None


class LEDStateRequest(BaseModel):
    device_id: str
    led_on: bool


class LEDStateResponse(BaseModel):
    device_id: str
    led_on: bool
    updated_at: str


@app.get("/")
async def root():
    return {
        "message": "Citonphyde Sensor Server",
        "status": "running",
        "endpoints": {
            "POST /sensor/data": "Send sensor data (temperature, humidity)",
            "GET /health": "Health check",
            "POST /led/set": "Set LED state (on/off)",
            "GET /led/state": "Get LED state",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/sensor/data")
async def receive_sensor_data(data: SensorData):
    """
    SHT31 센서 데이터를 받는 엔드포인트

    Request Body:
    {
        "temperature": 25.5,
        "humidity": 60.0,
        "device_id": "ESP32-S3-001",
        "timestamp": "2024-01-01T12:00:00" (optional)
    }
    """
    # 타임스탬프가 없으면 서버에서 생성
    if not data.timestamp:
        data.timestamp = datetime.now().isoformat()

    # 로그 출력
    print("=" * 50)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 센서 데이터 수신")
    print(f"  Device ID: {data.device_id}")
    print(f"  온도: {data.temperature:.2f} °C")
    print(f"  습도: {data.humidity:.2f} %")
    print(f"  Timestamp: {data.timestamp}")
    print("=" * 50)

    # 응답 반환
    return {
        "status": "success",
        "message": "Sensor data received",
        "received_data": {
            "device_id": data.device_id,
            "temperature": data.temperature,
            "humidity": data.humidity,
            "timestamp": data.timestamp,
        },
    }


@app.post("/led/set")
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


@app.get("/led/state")
async def get_led_state(device_id: Optional[str] = None):
    """
    LED 상태를 조회하는 엔드포인트

    Query Parameters:
    - device_id: 조회할 디바이스 ID (선택사항, 없으면 모든 디바이스 상태 반환)
    """
    if device_id:
        # 특정 디바이스의 LED 상태 조회
        if device_id not in led_states:
            raise HTTPException(
                status_code=404,
                detail=f"LED state not found for device_id: {device_id}",
            )

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


if __name__ == "__main__":
    print("Starting Citonphyde Sensor Server...")
    print("Server will be available at http://localhost:8000")
    print("API docs available at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
