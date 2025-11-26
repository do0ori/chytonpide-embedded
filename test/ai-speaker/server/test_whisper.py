"""
Whisper 음성 인식 테스트 스크립트
사용법: python test_whisper.py [wav_file_path]
주의사항: 반드시 ffmpeg 설치 필요 (choco install ffmpeg)
"""

import os
import sys
from pathlib import Path

import whisper


def test_whisper(audio_file: str, model_name: str = "base"):
    """
    Whisper를 사용하여 음성 파일을 텍스트로 변환

    Args:
        audio_file: 변환할 오디오 파일 경로
        model_name: 사용할 Whisper 모델 (tiny, base, small, medium, large)
    """
    print(f"Whisper 모델 로딩 중: {model_name}...")
    try:
        model = whisper.load_model(model_name)
        print(f"✓ 모델 로딩 완료: {model_name}")
    except Exception as e:
        print(f"❌ 모델 로딩 실패: {e}")
        return None

    # 파일 경로 정규화 (절대 경로로 변환)
    audio_path = Path(audio_file).resolve()

    if not audio_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {audio_path}")
        print(f"   현재 작업 디렉토리: {os.getcwd()}")
        return None

    print(f"\n음성 파일 변환 중: {audio_path}...")
    print(f"   파일 크기: {audio_path.stat().st_size / 1024:.2f} KB")

    try:
        result = model.transcribe(str(audio_path))
        transcribed_text = result["text"]

        print(f"\n{'='*50}")
        print("변환 결과:")
        print(f"{'='*50}")
        print(transcribed_text)
        print(f"{'='*50}")

        # 언어 정보 출력
        if "language" in result:
            print(f"\n감지된 언어: {result['language']}")

        # 세그먼트 정보 출력 (선택사항)
        if "segments" in result and len(result["segments"]) > 0:
            print(f"\n세그먼트 수: {len(result['segments'])}")
            print("처음 3개 세그먼트:")
            for i, segment in enumerate(result["segments"][:3], 1):
                print(
                    f"  [{i}] {segment.get('start', 0):.2f}s - {segment.get('end', 0):.2f}s: {segment.get('text', '')[:50]}..."
                )

        return transcribed_text

    except FileNotFoundError as e:
        print(f"❌ 파일을 찾을 수 없습니다: {e}")
        return None
    except Exception as e:
        print(f"❌ 변환 실패: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    # 명령줄 인자 확인
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        # 기본 파일명 시도
        audio_file = "ECDA3B45E7A0.wav"
        print(f"파일 경로가 지정되지 않아 기본 파일을 사용합니다: {audio_file}")

    # 모델 선택 (선택사항)
    model_name = "base"
    if len(sys.argv) > 2:
        model_name = sys.argv[2]

    print(f"\n{'='*50}")
    print("Whisper 음성 인식 테스트")
    print(f"{'='*50}")
    print(f"오디오 파일: {audio_file}")
    print(f"모델: {model_name}")
    print(f"{'='*50}\n")

    result = test_whisper(audio_file, model_name)

    if result:
        print("\n✓ 테스트 완료!")
    else:
        print("\n❌ 테스트 실패!")
        sys.exit(1)
