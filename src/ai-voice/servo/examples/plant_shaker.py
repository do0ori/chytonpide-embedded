#!/usr/bin/env python3
"""
화분 흔들기 예제 프로그램

서보 모터에 화분을 연결하여 흔들흔들 효과를 만드는 예제입니다.

동작: 90도 -> (45도 <-> 135도) x 5회 -> 90도

실행 방법:
    sudo python3 plant_shaker.py
"""

import os
import sys

# 현재 파일의 절대 경로: ~/chytonpide/servo/examples/plant_shaker.py
current_file = os.path.abspath(__file__)
# examples 디렉토리: ~/chytonpide/servo/examples/
examples_dir = os.path.dirname(current_file)
# servo 디렉토리: ~/chytonpide/servo/
servo_dir = os.path.dirname(examples_dir)
# servo의 부모 디렉토리: ~/chytonpide/
parent_dir = os.path.dirname(servo_dir)

# ~/chytonpide/를 Python 경로에 추가하여 servo 패키지를 찾을 수 있게 함
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from servo import ServoController


def main():
    """메인 함수"""
    controller = None

    try:
        print("=" * 50)
        print("화분 흔들기 프로그램")
        print("=" * 50)
        print("초기화 중...")

        # 서보 컨트롤러 생성
        controller = ServoController()
        print("서보 모터 준비 완료!")
        print("\n동작: 90도 -> (45도 <-> 135도) x 5회 -> 90도")
        print("시작합니다...\n")

        # 화분 흔들기 동작 실행
        controller.plant_shake(
            repeat=5,  # 5회 반복
            min_angle=45,  # 최소 각도
            max_angle=135,  # 최대 각도
            step=5,  # 각도 증가 폭 (작을수록 부드러움)
            delay=0.01,  # 지연 시간 (작을수록 빠름)
        )

        print("\n완료! 화분이 흔들렸습니다.")

    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if controller is not None:
            print("\n정리 중...")
            controller.cleanup()
            print("정리 완료.")


if __name__ == "__main__":
    main()
