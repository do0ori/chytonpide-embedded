#!/usr/bin/env python3
"""
Face Emotion 상태 설정 스크립트
사용법: python set_face_emotion.py [serial] [emotion] [server_url]
예시: python set_face_emotion.py xJN2wsF850yqWQfBUkGP HAPPY
"""

import sys

import requests


def set_face_emotion(
    serial="xJN2wsF850yqWQfBUkGP",
    emotion="HAPPY",
    server_url="http://localhost:8000",
):
    """Face Emotion 상태를 설정하는 함수"""
    url = f"{server_url}/devices/{serial}"
    payload = {"led_face": emotion}

    try:
        response = requests.patch(url, data=payload)
        response.raise_for_status()

        result = response.json()
        print("=" * 50)
        print("Face Emotion 상태 설정 성공!")
        print(f"Serial: {result['serial']}")
        print(f"업데이트된 필드: {', '.join(result['updated_fields'])}")
        print("=" * 50)
        return True
    except requests.exceptions.RequestException as e:
        print(f"오류 발생: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"응답: {e.response.text}")
        return False


def get_face_emotion_state(
    serial="xJN2wsF850yqWQfBUkGP", server_url="http://localhost:8000"
):
    """Face Emotion 상태를 조회하는 함수"""
    url = f"{server_url}/devices/{serial}/lcd"

    try:
        response = requests.get(url)
        response.raise_for_status()

        result = response.json()
        print("=" * 50)
        print("Face Emotion 상태 조회 성공!")
        print(f"Serial: {serial}")
        print(f"Face: {result['face']}")
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
        print("  설정: python set_face_emotion.py [serial] [emotion] [server_url]")
        print("  조회: python set_face_emotion.py [serial] --get [server_url]")
        print("\n예시:")
        print("  python set_face_emotion.py xJN2wsF850yqWQfBUkGP HAPPY")
        print("  python set_face_emotion.py xJN2wsF850yqWQfBUkGP SAD")
        print("  python set_face_emotion.py xJN2wsF850yqWQfBUkGP --get")
        sys.exit(1)

    # 조회 모드 확인
    if len(sys.argv) > 2 and sys.argv[2] == "--get":
        serial = sys.argv[1]
        server_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"
        get_face_emotion_state(serial, server_url)
    else:
        # 설정 모드
        serial = sys.argv[1]
        emotion = sys.argv[2] if len(sys.argv) > 2 else "HAPPY"
        server_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"

        set_face_emotion(serial, emotion, server_url)

