#!/usr/bin/env python3
"""
LED 상태 설정 스크립트
사용법: python set_led.py [serial] [led_state] [server_url]
예시: python set_led.py xJN2wsF850yqWQfBUkGP true
"""

import sys

import requests


def set_led_state(
    serial="xJN2wsF850yqWQfBUkGP", led_on=True, server_url="http://localhost:8000"
):
    """LED 상태를 설정하는 함수"""
    url = f"{server_url}/devices/{serial}"
    payload = {"is_led_on": "true" if led_on else "false"}

    try:
        response = requests.patch(url, data=payload)
        response.raise_for_status()

        result = response.json()
        print("=" * 50)
        print("LED 상태 설정 성공!")
        print(f"Serial: {result['serial']}")
        print(f"업데이트된 필드: {', '.join(result['updated_fields'])}")
        print("=" * 50)
        return True
    except requests.exceptions.RequestException as e:
        print(f"오류 발생: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"응답: {e.response.text}")
        return False


def get_led_state(
    serial="xJN2wsF850yqWQfBUkGP", server_url="http://localhost:8000"
):
    """LED 상태를 조회하는 함수"""
    url = f"{server_url}/devices/{serial}/led"

    try:
        response = requests.get(url)
        response.raise_for_status()

        result = response.json()
        print("=" * 50)
        print("LED 상태 조회 성공!")
        print(f"Serial: {serial}")
        print(f"LED 상태: {'ON' if result['is_led_on'] else 'OFF'}")
        print(f"업데이트 시간: {result['updated_at']}")
        print("=" * 50)
        return True
    except requests.exceptions.RequestException as e:
        print(f"오류 발생: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"응답: {e.response.text}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법:")
        print("  설정: python set_led.py [serial] [led_state] [server_url]")
        print("  조회: python set_led.py [serial] --get [server_url]")
        print("\n예시:")
        print("  python set_led.py xJN2wsF850yqWQfBUkGP true")
        print("  python set_led.py xJN2wsF850yqWQfBUkGP false")
        print("  python set_led.py xJN2wsF850yqWQfBUkGP --get")
        sys.exit(1)

    # 조회 모드 확인
    if len(sys.argv) > 2 and sys.argv[2] == "--get":
        serial = sys.argv[1]
        server_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"
        get_led_state(serial, server_url)
    else:
        # 설정 모드
        serial = sys.argv[1]
        led_state_str = sys.argv[2] if len(sys.argv) > 2 else "true"
        server_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"

        # 문자열을 boolean으로 변환
        led_on = led_state_str.lower() in ("true", "1", "on", "yes")

        set_led_state(serial, led_on, server_url)
