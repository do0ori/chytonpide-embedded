#!/usr/bin/env python3
"""
LED 상태 설정 스크립트
사용법: python set_led.py [device_id] [led_state] [server_url]
예시: python set_led.py 0000541217D9B4DC true
"""

import sys

import requests


def set_led_state(
    device_id="0000541217D9B4DC", led_on=True, server_url="http://localhost:8000"
):
    """LED 상태를 설정하는 함수"""
    url = f"{server_url}/led/set"
    payload = {"device_id": device_id, "led_on": led_on}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        print("=" * 50)
        print("LED 상태 설정 성공!")
        print(f"Device ID: {result['led_state']['device_id']}")
        print(f"LED 상태: {'ON' if result['led_state']['led_on'] else 'OFF'}")
        print(f"업데이트 시간: {result['led_state']['updated_at']}")
        print("=" * 50)
        return True
    except requests.exceptions.RequestException as e:
        print(f"오류 발생: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"응답: {e.response.text}")
        return False


if __name__ == "__main__":
    # 명령줄 인자 처리
    device_id = sys.argv[1] if len(sys.argv) > 1 else "0000541217D9B4DC"
    led_state_str = sys.argv[2] if len(sys.argv) > 2 else "true"
    server_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"

    # 문자열을 boolean으로 변환
    led_on = led_state_str.lower() in ("true", "1", "on", "yes")

    set_led_state(device_id, led_on, server_url)
