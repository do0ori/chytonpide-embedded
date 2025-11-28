#!/usr/bin/env python3
"""
Face Emotion 상태 설정 스크립트
사용법: python set_face_emotion.py [device_id] [emotion] [server_url]
예시: python set_face_emotion.py 0000541217D9B4DC HAPPY
"""

import sys

import requests


def set_face_emotion(
    device_id="0000541217D9B4DC",
    emotion="HAPPY",
    server_url="http://localhost:8000",
):
    """Face Emotion 상태를 설정하는 함수"""
    url = f"{server_url}/face_emotion"
    payload = {"device_id": device_id, "emotion": emotion}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        print("=" * 50)
        print("Face Emotion 상태 설정 성공!")
        print(f"Device ID: {result['face_emotion_state']['device_id']}")
        print(f"Emotion: {result['face_emotion_state']['emotion']}")
        print(f"업데이트 시간: {result['face_emotion_state']['updated_at']}")
        print("=" * 50)
        return True
    except requests.exceptions.RequestException as e:
        print(f"오류 발생: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"응답: {e.response.text}")
        return False


def get_face_emotion_state(
    device_id="0000541217D9B4DC", server_url="http://localhost:8000"
):
    """Face Emotion 상태를 조회하는 함수"""
    url = f"{server_url}/face_emotion"
    params = {"device_id": device_id} if device_id else None

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        result = response.json()
        print("=" * 50)
        print("Face Emotion 상태 조회 성공!")
        
        if "face_emotion_state" in result:
            # 단일 디바이스
            state = result["face_emotion_state"]
            print(f"Device ID: {state['device_id']}")
            print(f"Emotion: {state['emotion']}")
            print(f"업데이트 시간: {state['updated_at']}")
        else:
            # 모든 디바이스
            states = result.get("face_emotion_states", {})
            print(f"총 {len(states)}개의 디바이스 상태:")
            for dev_id, state in states.items():
                print(f"  - {dev_id}: {state['emotion']} (updated: {state['updated_at']})")
        
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
        print("  설정: python set_face_emotion.py [device_id] [emotion] [server_url]")
        print("  조회: python set_face_emotion.py [device_id] --get [server_url]")
        print("\n예시:")
        print("  python set_face_emotion.py 0000541217D9B4DC HAPPY")
        print("  python set_face_emotion.py 0000541217D9B4DC SAD")
        print("  python set_face_emotion.py 0000541217D9B4DC --get")
        print("  python set_face_emotion.py --get  # 모든 디바이스 조회")
        sys.exit(1)

    # 조회 모드 확인
    if sys.argv[1] == "--get":
        device_id = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "--get" else None
        server_url = (
            sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "--get" else "http://localhost:8000"
        )
        get_face_emotion_state(device_id, server_url)
    else:
        # 설정 모드
        device_id = sys.argv[1]
        emotion = sys.argv[2] if len(sys.argv) > 2 else "HAPPY"
        server_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"

        set_face_emotion(device_id, emotion, server_url)

