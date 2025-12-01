#!/usr/bin/env python3
"""
Google Cloud Speech-to-Text + Azure OpenAI LLM + SuperTone TTS 음성 어시스턴트
라즈베리파이 제로 WH (Python 3.7.3) 호환

Google Cloud Speech-to-Text API 사용 (VAD 내장)
SuperTone API를 사용한 TTS
Azure OpenAI를 사용한 LLM
"""

import io
import json
import logging
import os
import subprocess
import sys
import threading
import time

# 한글 출력 깨짐 방지 (Python 3.7.3 호환)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv가 설치되지 않았습니다: pip3 install python-dotenv")
    sys.exit(1)

# AIY Projects 모듈
try:
    from aiy.board import Board, Led

    HAS_BOARD = True
except ImportError:
    HAS_BOARD = False
    print("경고: AIY Projects board 모듈을 찾을 수 없습니다.")

try:
    from aiy.cloudspeech import CloudSpeechClient

    HAS_CLOUDSPEECH = True
except ImportError:
    HAS_CLOUDSPEECH = False
    print("❌ aiy.cloudspeech 모듈을 찾을 수 없습니다.")
    print("AIY Projects가 설치되어 있는지 확인하세요.")
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# 환경 변수 로드
# ============================================================================

# .env 파일 경로 찾기
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config", ".env")
if os.path.exists(config_path):
    load_dotenv(config_path)
else:
    # 상위 디렉토리에서 찾기
    parent_config = os.path.join(os.path.dirname(current_dir), "config", ".env")
    if os.path.exists(parent_config):
        load_dotenv(parent_config)
    else:
        # 기본 경로
        load_dotenv()

# SuperTone 설정 (TTS용)
SUPERTON_API_KEY = os.environ.get("SUPERTON_API_KEY")
SUPERTON_VOICE_ID = os.environ.get("SUPERTON_VOICE_ID")

# 트리거 단어 설정 (Wake word)
TRIGGER_WORDS = os.environ.get("TRIGGER_WORDS", "치피")

# 트리거 단어 사용 여부 (False면 트리거 단어 없이 바로 시작)
USE_TRIGGER_WORD = os.environ.get("USE_TRIGGER_WORD", "true").lower() in (
    "true",
    "1",
    "yes",
)

# Sleep mode 타임아웃 설정
SLEEP_TIMEOUT = float(os.environ.get("SLEEP_TIMEOUT", "10.0"))

# Google Cloud Speech 언어 코드
GOOGLE_SPEECH_LANGUAGE = os.environ.get("GOOGLE_SPEECH_LANGUAGE", "ko_KR")

# 얼굴 표정 제어 설정
DEVICE_SERIAL = os.environ.get("DEVICE_SERIAL")
SERVER_URL = os.environ.get(
    "SERVER_URL", "https://chytonpide.azurewebsites.net"
)  # 기본값: 프로덕션 서버 URL

# 검증
if not SUPERTON_API_KEY or not SUPERTON_VOICE_ID:
    logger.error(
        "SUPERTON_API_KEY와 SUPERTON_VOICE_ID가 .env 파일에 설정되어야 합니다."
    )
    sys.exit(1)

# ============================================================================
# SuperTone TTS (REST API)
# ============================================================================

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("requests가 설치되지 않았습니다: pip3 install requests")
    sys.exit(1)

try:
    import tempfile
except ImportError:
    print("tempfile 모듈을 사용할 수 없습니다.")
    sys.exit(1)

# AIY Projects audio 모듈 (TTS 재생용)
try:
    from aiy.voice.audio import play_wav

    HAS_AIY_AUDIO = True
except ImportError:
    HAS_AIY_AUDIO = False
    print("경고: AIY Projects audio 모듈을 찾을 수 없습니다.")


class SupertonTTS:
    """SuperTone API를 사용한 TTS 클래스 (AIY Projects play_wav 사용)"""

    def __init__(self, voice_id=None, api_key=None):
        """
        초기화

        Args:
            voice_id: 음성 ID (기본값: env의 SUPERTON_VOICE_ID)
            api_key: API 키 (기본값: env의 SUPERTON_API_KEY)
        """
        self.api_key = api_key or SUPERTON_API_KEY
        self.voice_id = voice_id or SUPERTON_VOICE_ID

        if not self.api_key:
            raise ValueError("❌ SUPERTON_API_KEY가 설정되지 않았습니다.")

        logger.info("SuperTone TTS 초기화 완료 (음성 ID: %s)", self.voice_id)

    def generate(
        self,
        text,
        language="ko",
        style="neutral",
        output_format="wav",
        pitch_shift=0,
        speed=1,
        pitch_variance=1,
    ):
        """
        SuperTone API를 사용하여 음성 생성

        Args:
            text: 텍스트
            language: 언어 (기본값: "ko")
            style: 스타일 (기본값: "neutral")
            output_format: 출력 형식 - "wav" 또는 "mp3" (기본값: "wav")
            pitch_shift: 음높이 조정 (-20 ~ 20, 기본값: 0)
            speed: 재생 속도 (0.5 ~ 2, 기본값: 1)
            pitch_variance: 음높이 변동성 (0 ~ 2, 기본값: 1)

        Returns:
            음성 바이트 데이터 또는 None
        """
        url = f"https://supertoneapi.com/v1/text-to-speech/{self.voice_id}"

        headers = {"x-sup-api-key": self.api_key, "Content-Type": "application/json"}

        payload = {
            "text": text,
            "language": language,
            "style": style,
            "model": "sona_speech_1",
            "output_format": output_format,
            "voice_settings": {
                "pitch_shift": pitch_shift,
                "pitch_variance": pitch_variance,
                "speed": speed,
            },
        }

        try:
            logger.debug(f"SuperTone 음성 생성 중: {text[:20]}...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                logger.debug("SuperTone 음성 생성 완료")
                return response.content
            else:
                logger.error(
                    f"SuperTone API 오류 (상태: {response.status_code}): {response.text}"
                )
                return None

        except requests.exceptions.Timeout:
            logger.error("SuperTone 요청 시간 초과 (30초)")
            return None
        except Exception as e:
            logger.error(f"SuperTone 오류: {e}", exc_info=True)
            return None

    def speak(
        self,
        text,
        language="ko",
        style="neutral",
        pitch_shift=0,
        speed=1,
        pitch_variance=1,
    ):
        """
        텍스트를 음성으로 변환하고 재생 (AIY Projects play_wav 사용)

        Args:
            text: 말할 텍스트
            language: 언어 (기본값: "ko")
            style: 스타일 (기본값: "neutral")
            pitch_shift: 음높이 조정 (-20 ~ 20, 기본값: 0)
            speed: 재생 속도 (0.5 ~ 2, 기본값: 1)
            pitch_variance: 음높이 변동성 (0 ~ 2, 기본값: 1)
        """
        audio_data = self.generate(
            text,
            language,
            style,
            output_format="wav",
            pitch_shift=pitch_shift,
            speed=speed,
            pitch_variance=pitch_variance,
        )

        if audio_data:
            try:
                # 임시 파일로 저장
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as tmp_file:
                    tmp_file.write(audio_data)
                    tmp_file_path = tmp_file.name

                try:
                    # 재생 (AIY Projects play_wav 사용)
                    if HAS_AIY_AUDIO:
                        play_wav(tmp_file_path)
                    else:
                        import subprocess

                        subprocess.run(["aplay", "-q", tmp_file_path], check=True)

                    logger.debug("SuperTone 음성 출력 완료")
                finally:
                    try:
                        os.unlink(tmp_file_path)
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"SuperTone 재생 오류: {e}", exc_info=True)


# ============================================================================
# 메인 함수
# ============================================================================

# 상대 경로로 import 시도 (현재 디렉토리 기준)
try:
    from core.chipi_brain import ChipiBrain
except ImportError:
    # 상위 디렉토리 기준으로 시도
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from core.chipi_brain import ChipiBrain
    except ImportError:
        # 최상위 디렉토리 기준으로 시도
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(os.path.dirname(current_dir))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            from core.chipi_brain import ChipiBrain
        except ImportError as e:
            print(f"❌ ChipiBrain을 import할 수 없습니다: {e}")
            sys.exit(1)

# 상수 import
try:
    from constants import (
        EMOTION_CHECK_ORDER,
        EMOTION_DEFAULT,
        EMOTION_KEYWORDS,
        EXIT_COMMANDS,
        LED_OFF_KEYWORDS,
        LED_ON_KEYWORDS,
        SAD_TONE_KEYWORDS,
        SERVO_KEYWORDS,
        SLEEP_COMMANDS,
    )
except ImportError:
    # 현재 디렉토리 기준으로 시도
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from constants import (
        EMOTION_CHECK_ORDER,
        EMOTION_DEFAULT,
        EMOTION_KEYWORDS,
        EXIT_COMMANDS,
        LED_OFF_KEYWORDS,
        LED_ON_KEYWORDS,
        SAD_TONE_KEYWORDS,
        SERVO_KEYWORDS,
        SLEEP_COMMANDS,
    )


def load_voice_hints():
    """voice_hints.json 파일에서 자주 사용하는 문장 로드"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    hints_file = os.path.join(current_dir, "config", "voice_hints.json")

    # 상위 디렉토리에서도 찾기
    if not os.path.exists(hints_file):
        parent_config = os.path.join(
            os.path.dirname(current_dir), "config", "voice_hints.json"
        )
        if os.path.exists(parent_config):
            hints_file = parent_config

    if os.path.exists(hints_file):
        try:
            with open(hints_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("common_phrases", [])
        except Exception as e:
            logger.warning(f"voice_hints.json 파일을 읽을 수 없습니다: {e}")
            return []
    else:
        logger.debug(f"voice_hints.json 파일을 찾을 수 없습니다: {hints_file}")
        return []


def get_hints(language_code, trigger_words=None):
    """언어 코드에 따른 힌트 구문 반환

    Args:
        language_code: 언어 코드
        trigger_words: 트리거 단어 리스트 (옵션)
    """
    if language_code.startswith("ko_"):
        hints = []

        # 1. 트리거 단어 기반 힌트
        if trigger_words:
            # 기본 트리거 단어들
            hints.extend(trigger_words)
            # 트리거 단어 + 호격 조사 (야, 아, 이여 등)
            for word in trigger_words:
                hints.append(f"{word}야")
                hints.append(f"{word}아")
                hints.append(f"{word}이")
            # 트리거 단어 + 일반적인 명령어 (짧은 음성 인식 향상)
            for word in trigger_words:
                hints.append(f"{word}야 안녕")
                hints.append(f"{word}야 뭐해")
                hints.append(f"{word}야 잘있어")

        # 2. JSON 파일에서 자주 사용하는 문장 로드
        common_phrases = load_voice_hints()
        if common_phrases:
            hints.extend(common_phrases)
            logger.info(
                f"JSON 파일에서 {len(common_phrases)}개의 힌트 문장을 로드했습니다."
            )

        if hints:
            return tuple(set(hints))  # 중복 제거
        return None
    return None


def _contains_trigger_word(text, trigger_words):
    """텍스트에 트리거 단어가 포함되어 있는지 확인 (유연한 매칭)

    짧은 음성("치피야" 등)도 잘 인식되도록 부분 매칭 지원
    """
    if not text or not trigger_words:
        return False

    text_lower = text.lower().strip()

    # 완전 일치 또는 포함 확인
    for trigger in trigger_words:
        trigger_lower = trigger.lower()
        if trigger_lower in text_lower:
            return True

        # 부분 매칭: 트리거 단어가 텍스트의 시작 부분에 있는지 확인
        # 예: "치피야" -> "치피" 매칭
        if text_lower.startswith(trigger_lower):
            return True

        # 호격 조사 포함 확인: "치피야", "치피아", "치피이" 등
        for suffix in ["야", "아", "이", "여", "이야", "이여"]:
            if text_lower.startswith(trigger_lower + suffix):
                return True

    return False


def _find_servo_script_path():
    """서보 스크립트 경로 찾기"""
    # 현재 파일의 디렉토리 기준으로 경로 찾기
    main_file_dir = os.path.dirname(os.path.abspath(__file__))
    main_file_parent = os.path.dirname(main_file_dir)

    # 여러 가능한 경로 시도
    possible_paths = [
        # 현재 디렉토리 기준 (src/ai-voice/servo/examples/plant_shaker.py)
        os.path.join(main_file_dir, "servo", "examples", "plant_shaker.py"),
        # 상위 디렉토리 기준
        os.path.join(main_file_parent, "servo", "examples", "plant_shaker.py"),
        # 홈 디렉토리 기준 (~/chytonpide/servo/examples/plant_shaker.py)
        os.path.expanduser("~/chytonpide/servo/examples/plant_shaker.py"),
        # 절대 경로 (라즈베리파이 기본 경로)
        "/home/pi/chytonpide/servo/examples/plant_shaker.py",
    ]

    for path in possible_paths:
        abs_path = os.path.abspath(os.path.expanduser(path))
        if os.path.exists(abs_path):
            logger.info(f"서보 스크립트 경로 찾음: {abs_path}")
            return abs_path

    logger.warning("서보 스크립트를 찾을 수 없습니다. 가능한 경로:")
    for path in possible_paths:
        logger.warning(f"  - {os.path.abspath(os.path.expanduser(path))}")
    return None


def _run_servo_plant_shake():
    """서보 모터로 화분 흔들기 실행 (subprocess 사용, 비블로킹)"""
    script_path = _find_servo_script_path()
    if not script_path:
        logger.error("서보 스크립트를 찾을 수 없습니다.")
        return False

    try:
        logger.info(f"서보 모터 실행: {script_path}")
        # sudo 권한으로 비블로킹 실행 (Popen 사용)
        process = subprocess.Popen(
            ["sudo", "python3", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # 프로세스가 시작되면 즉시 반환 (비블로킹)
        logger.debug(f"서보 모터 프로세스 시작됨 (PID: {process.pid})")

        # 백그라운드에서 완료 대기
        def _wait_for_completion():
            try:
                stdout, stderr = process.communicate(timeout=30)
                if process.returncode == 0:
                    logger.info("서보 모터 실행 완료")
                    if stdout:
                        logger.debug(f"서보 출력: {stdout}")
                else:
                    logger.error(f"서보 모터 실행 실패 (코드: {process.returncode})")
                    if stderr:
                        logger.error(f"서보 오류: {stderr}")
            except subprocess.TimeoutExpired:
                logger.error("서보 모터 실행 시간 초과 (30초)")
                process.kill()
                process.wait()
            except Exception as e:
                logger.error(f"서보 모터 실행 오류: {e}", exc_info=True)

        # 완료 대기를 별도 스레드에서 실행
        threading.Thread(target=_wait_for_completion, daemon=True).start()

        return True

    except Exception as e:
        logger.error(f"서보 모터 실행 오류: {e}", exc_info=True)
        return False


def _run_servo_async():
    """서보 모터를 비동기로 실행 (별도 스레드에서)"""

    def _servo_worker():
        try:
            _run_servo_plant_shake()
        except Exception as e:
            logger.error(f"서보 모터 비동기 실행 오류: {e}")

    thread = threading.Thread(target=_servo_worker, daemon=True)
    thread.start()
    logger.info("서보 모터 비동기 실행 시작")
    return thread


# 오디오 유틸리티 import
try:
    from utils.audio_utils import (
        find_mapped_audio,
        load_audio_mapping,
        play_audio_file,
        play_audio_file_async,
        play_audio_file_by_path,
        play_intro_audio,
    )
except ImportError:
    # 상위 디렉토리에서 시도
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from utils.audio_utils import (
            find_mapped_audio,
            load_audio_mapping,
            play_audio_file,
            play_audio_file_async,
            play_audio_file_by_path,
            play_intro_audio,
        )
    except ImportError:
        logger.error("utils.audio_utils를 import할 수 없습니다.")

        # 폴백 함수 정의
        def play_intro_audio(*args, **kwargs):
            logger.error("play_intro_audio 함수를 사용할 수 없습니다.")
            return False

        def load_audio_mapping():
            return {}

        def find_mapped_audio(user_text, audio_mapping):
            return None, None

        def play_audio_file(filename):
            return False

        def play_audio_file_async(filename):
            return None

        def play_audio_file_by_path(file_path):
            return False


def _contains_servo_keywords(text):
    """서보 모터 실행 키워드 감지"""
    if not text:
        return False

    text_lower = text.lower()
    return any(keyword in text_lower for keyword in SERVO_KEYWORDS)


def _detect_face_emotion_from_response(text):
    """
    LLM 응답 텍스트를 분석하여 적절한 얼굴 표정 감지 (키워드 기반)

    Args:
        text: LLM 응답 텍스트

    Returns:
        str: 감정 상수 ("HAPPY", "SAD", "ANGRY", "SURPRISED", "TIRED", "CALM", "DEFAULT")
    """
    if not text:
        return EMOTION_DEFAULT

    text_lower = text.lower()

    # 우선순위대로 감정 체크
    for emotion in EMOTION_CHECK_ORDER:
        keywords = EMOTION_KEYWORDS.get(emotion, [])
        if any(keyword in text_lower for keyword in keywords):
            logger.debug(f"감정 감지: {emotion} (키워드 매칭)")
            return emotion

    # 키워드가 없으면 기본값 (NEUTRAL/DEFAULT)
    return EMOTION_DEFAULT


def _set_face_emotion(emotion, serial=None, server_url=None):
    """
    얼굴 표정 설정

    Args:
        emotion: 감정 상수 ("HAPPY", "SAD", "ANGRY", "SURPRISED", "TIRED", "CALM", "DEFAULT")
        serial: 디바이스 시리얼 (기본값: 환경 변수 DEVICE_SERIAL)
        server_url: 서버 URL (기본값: 환경 변수 SERVER_URL)

    Returns:
        bool: 성공 여부
    """
    device_serial = serial or DEVICE_SERIAL
    if not device_serial:
        logger.warning("DEVICE_SERIAL이 설정되지 않아 얼굴 표정을 설정할 수 없습니다.")
        return False

    url = f"{server_url or SERVER_URL}/devices/{device_serial}"
    # API 명세: lcd_face 필드만 보내면 됨
    payload = {"lcd_face": emotion}

    try:
        # Content-Type: application/x-www-form-urlencoded (기본값)
        response = requests.patch(url, data=payload, timeout=5)
        response.raise_for_status()

        logger.info(f"얼굴 표정 설정 성공: {emotion}")
        return True
    except requests.exceptions.RequestException as e:
        logger.warning(f"얼굴 표정 설정 실패 ({emotion}): {e}")
        return False


def _contains_led_keywords(text):
    """LED 제어 키워드 감지

    Returns:
        str or None: "on", "off", 또는 None
    """
    if not text:
        return None

    text_lower = text.lower()

    # LED 켜기 키워드 확인
    if any(keyword in text_lower for keyword in LED_ON_KEYWORDS):
        return "on"

    # LED 끄기 키워드 확인
    if any(keyword in text_lower for keyword in LED_OFF_KEYWORDS):
        return "off"

    return None


def _set_led_state(led_on, serial=None, server_url=None):
    """
    LED 상태 설정

    Args:
        led_on: True면 켜기, False면 끄기
        serial: 디바이스 시리얼 (기본값: 환경 변수 DEVICE_SERIAL)
        server_url: 서버 URL (기본값: 환경 변수 SERVER_URL)

    Returns:
        bool: 성공 여부
    """
    device_serial = serial or DEVICE_SERIAL
    if not device_serial:
        logger.warning("DEVICE_SERIAL이 설정되지 않아 LED를 제어할 수 없습니다.")
        return False

    url = f"{server_url or SERVER_URL}/devices/{device_serial}"
    # API 명세: is_led_on 필드만 보내면 됨 (문자열로 "true" 또는 "false")
    payload = {"is_led_on": "true" if led_on else "false"}

    try:
        # Content-Type: application/x-www-form-urlencoded (기본값)
        response = requests.patch(url, data=payload, timeout=5)
        response.raise_for_status()

        state_str = "켜기" if led_on else "끄기"
        logger.info(f"LED {state_str} 성공")
        return True
    except requests.exceptions.RequestException as e:
        state_str = "켜기" if led_on else "끄기"
        logger.warning(f"LED {state_str} 실패: {e}")
        return False


def main():
    device_serial = os.environ.get("DEVICE_SERIAL")
    if not device_serial:
        print("⚠️ DEVICE_SERIAL 없음")

    # 트리거 단어 처리
    trigger_words = []
    if USE_TRIGGER_WORD:
        trigger_words_str = TRIGGER_WORDS.strip()
        if "," in trigger_words_str:
            trigger_words = [w.strip().lower() for w in trigger_words_str.split(",")]
        elif " " in trigger_words_str:
            trigger_words = [w.strip().lower() for w in trigger_words_str.split()]
        else:
            trigger_words = [trigger_words_str.lower()]

        # 빈 단어 제거
        trigger_words = [w for w in trigger_words if w]
        if not trigger_words:
            trigger_words = ["치피"]

    print(
        "\n============== ⚡ 치피(Chipi) Google STT + SuperTone TTS 모드 시작 ==============\n"
    )
    print(f"STT: Google Cloud Speech-to-Text (언어: {GOOGLE_SPEECH_LANGUAGE})")
    print("LLM: Azure OpenAI")
    print("TTS: SuperTone")
    if USE_TRIGGER_WORD:
        print(f"트리거 단어: {', '.join(trigger_words)}")
        print(f"Sleep timeout: {SLEEP_TIMEOUT}초")
        print("Sleep mode에서 시작합니다. 트리거 단어를 말하면 Wake mode로 전환됩니다.")
        print("Wake mode에서는 트리거 단어 없이 모든 말에 응답합니다.")
        print("일정 시간 동안 말이 없으면 자동으로 Sleep mode로 전환됩니다.")
    else:
        print("트리거 단어: 사용 안 함 (바로 시작)")
        print(f"Sleep timeout: {SLEEP_TIMEOUT}초")
        print("트리거 단어 없이 바로 모든 말에 응답합니다.")
        print("일정 시간 동안 말이 없으면 Sleep mode로 전환됩니다.")
    print("종료하려면 '종료'라고 말하거나 Ctrl+C를 누르세요.\n")

    def indicate_listening(is_listening):
        """듣는 중 상태를 LED로 표시"""
        if board and board.led:
            if is_listening:
                board.led.state = Led.ON
            else:
                board.led.state = Led.OFF

    try:
        # Board context manager 사용 (원본 예제와 동일 - 음성 인식 성능 향상)
        # 원본 예제처럼 with Board() as board: 형태로 사용
        if HAS_BOARD:
            board_ctx = Board()
        else:
            from contextlib import nullcontext

            board_ctx = nullcontext()

        with board_ctx as board:
            print("🌐 Google Cloud Speech-to-Text 초기화 중...", end=" ", flush=True)
            # 트리거 단어를 힌트로 제공 (짧은 음성 인식 향상을 위해)
            hints = get_hints(
                GOOGLE_SPEECH_LANGUAGE, trigger_words if USE_TRIGGER_WORD else None
            )
            if hints:
                logger.info(f"힌트 구문 {len(hints)}개 설정: {', '.join(hints[:5])}...")
            logger.info(f"Initializing for language {GOOGLE_SPEECH_LANGUAGE}...")
            client = CloudSpeechClient()
            logger.info(
                f"Google Cloud Speech-to-Text 초기화 완료 (언어: {GOOGLE_SPEECH_LANGUAGE})"
            )
            print("✅ 완료")

            print("🧠 두뇌(LLM) 연결 중...", end=" ", flush=True)
            brain = ChipiBrain()
            print("✅ 완료")

            print("🎤 음성(SuperTone TTS) 연결 중...", end=" ", flush=True)
            tts = SupertonTTS()
            print("✅ 완료\n")

            # 오디오 매핑 로드
            print("📁 오디오 매핑 로드 중...", end=" ", flush=True)
            audio_mapping = load_audio_mapping()
            if audio_mapping:
                print(f"✅ 완료 ({len(audio_mapping)}개 항목)")
            else:
                print("⚠️ 매핑 없음")

            # Sleep/Wake 모드 관리
            # 트리거 단어를 사용하지 않으면 바로 Wake mode로 시작
            sleep_mode = USE_TRIGGER_WORD  # 트리거 단어 사용 시만 Sleep mode로 시작
            last_interaction_time = None
            last_response = ""  # 중복 응답 방지용

            # 시작 안내 음성 (intro.wav 파일 재생)
            play_intro_audio(
                tts=tts, trigger_words=trigger_words, use_trigger_word=USE_TRIGGER_WORD
            )

            # 슬픈 톤을 사용할 키워드 목록 (constants에서 가져옴)
            sad_keywords = SAD_TONE_KEYWORDS

            # Main loop
            while True:
                try:
                    # Sleep mode: 타임아웃 체크
                    if not sleep_mode and last_interaction_time:
                        time_since_last = time.time() - last_interaction_time
                        if time_since_last >= SLEEP_TIMEOUT:
                            logger.info(
                                f"Wake mode 타임아웃 ({SLEEP_TIMEOUT}초). Sleep mode로 전환합니다."
                            )
                            sleep_mode = True
                            last_interaction_time = None

                    print("\n👂 듣는 중...", end=" ", flush=True)
                    indicate_listening(True)

                    # Google Cloud Speech-to-Text로 음성 인식 (VAD 내장)
                    user_text = client.recognize(
                        language_code=GOOGLE_SPEECH_LANGUAGE, hint_phrases=hints
                    )

                    indicate_listening(False)

                    if user_text is None:
                        print("🔕 (침묵 또는 인식 실패)", flush=True)
                        continue

                    user_text = user_text.strip()
                    if not user_text:
                        print("🔕 (빈 텍스트)", flush=True)
                        continue

                    print(f'✅ 인식됨: "{user_text}"', flush=True)
                    logger.info(f"사용자: {user_text}")

                    # Sleep mode: 트리거 단어 확인 (트리거 단어가 활성화된 경우만)
                    if sleep_mode and USE_TRIGGER_WORD:
                        if _contains_trigger_word(user_text, trigger_words):
                            logger.info("트리거 단어 감지! Wake mode로 전환합니다.")
                            sleep_mode = False
                            last_interaction_time = time.time()
                            # 트리거 단어 제거 (예: "치피 안녕하세요" → "안녕하세요")
                            cleaned_text = user_text
                            for trigger in trigger_words:
                                cleaned_text = cleaned_text.replace(
                                    trigger, "", 1
                                ).strip()
                            if cleaned_text:
                                user_text = cleaned_text
                            else:
                                # 트리거 단어만 있는 경우
                                logger.info("트리거 단어만 감지되었습니다.")
                                tts.speak(
                                    "네, 말씀해주세요.", language="ko", style="neutral"
                                )
                                continue
                        else:
                            continue
                    elif sleep_mode and not USE_TRIGGER_WORD:
                        # 트리거 단어가 비활성화되어 있으면 바로 Wake mode로 전환
                        sleep_mode = False
                        last_interaction_time = time.time()

                    # Wake mode: 상호작용 시간 업데이트
                    if not sleep_mode:
                        last_interaction_time = time.time()

                    # 종료 명령 확인
                    if any(cmd in user_text.lower() for cmd in EXIT_COMMANDS):
                        logger.info("종료 명령을 받았습니다.")
                        tts.speak("안녕히 가세요!", language="ko", style="neutral")
                        break

                    # Sleep 명령 확인 (Sleep mode로 전환)
                    if any(cmd in user_text.lower() for cmd in SLEEP_COMMANDS):
                        logger.info("Sleep mode로 전환합니다.")
                        sleep_mode = True
                        last_interaction_time = None
                        continue

                    # 서보 모터 실행 키워드 감지
                    if _contains_servo_keywords(user_text):
                        logger.info("서보 모터 실행 키워드 감지!")
                        print("🔄 서보 모터 실행 중...", flush=True)
                        # 비동기로 실행 (서보 실행과 동시에 AI 응답도 처리 가능)
                        _run_servo_async()
                        print("✅ 서보 모터 실행 시작 (백그라운드)", flush=True)

                    # LED 제어 키워드 감지
                    led_action = _contains_led_keywords(user_text)
                    if led_action:
                        logger.info(f"LED {led_action.upper()} 키워드 감지!")
                        print(f"💡 LED {led_action.upper()} 중...", flush=True)
                        # 비동기로 LED 제어 (다른 작업과 동시에 실행 가능)
                        led_state = led_action == "on"
                        threading.Thread(
                            target=lambda: _set_led_state(led_state),
                            daemon=True,
                        ).start()
                        print(
                            f"✅ LED {led_action.upper()} 요청 완료 (백그라운드)",
                            flush=True,
                        )

                    # 오디오 매핑 확인 (LLM 우회)
                    mapped_audio_path, mapped_response_text = find_mapped_audio(
                        user_text, audio_mapping
                    )

                    if mapped_audio_path:
                        # 매핑된 오디오 파일이 있으면 LLM을 거치지 않고 바로 재생
                        logger.info(f"매핑된 오디오 파일 발견: {mapped_audio_path}")
                        print(
                            f"🎵 매핑된 오디오 재생: {os.path.basename(mapped_audio_path)}",
                            flush=True,
                        )

                        # 응답 텍스트 설정
                        ai_response = mapped_response_text
                        print(f"🤖 치피: {ai_response}", flush=True)

                        # 얼굴 표정 감지 및 설정 (응답 텍스트 기반)
                        detected_emotion = _detect_face_emotion_from_response(
                            ai_response
                        )
                        print(f"😊 감지된 표정: {detected_emotion}", flush=True)
                        if DEVICE_SERIAL:
                            threading.Thread(
                                target=lambda: _set_face_emotion(detected_emotion),
                                daemon=True,
                            ).start()

                        # TTS 재생 시작 시 시간 업데이트
                        if not sleep_mode:
                            last_interaction_time = time.time()

                        # 서보 모터와 오디오 파일을 정확히 동시에 시작
                        # 서보 모터 스크립트 경로를 미리 찾기 (블로킹 방지)
                        servo_script_path = _find_servo_script_path()

                        # 서보 모터를 먼저 시작하는 함수 (바로 실행)
                        def _start_servo():
                            if servo_script_path:
                                try:
                                    process = subprocess.Popen(
                                        ["sudo", "python3", servo_script_path],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True,
                                    )
                                    logger.debug(
                                        f"서보 모터 프로세스 시작됨 (PID: {process.pid})"
                                    )

                                    # 완료 대기는 백그라운드에서
                                    def _wait_servo():
                                        try:
                                            process.communicate(timeout=30)
                                            if process.returncode == 0:
                                                logger.info("서보 모터 실행 완료")
                                        except subprocess.TimeoutExpired:
                                            process.kill()
                                            logger.error("서보 모터 실행 시간 초과")
                                        except Exception as e:
                                            logger.error(f"서보 모터 오류: {e}")

                                    threading.Thread(
                                        target=_wait_servo, daemon=True
                                    ).start()
                                except Exception as e:
                                    logger.error(f"서보 모터 실행 오류: {e}")
                            else:
                                logger.error("서보 스크립트를 찾을 수 없습니다.")

                        # 오디오 재생 함수 (1초 지연)
                        def _start_audio():
                            time.sleep(1.0)  # 서보 모터 시작 시간 확보를 위해 1초 대기
                            play_audio_file_by_path(mapped_audio_path)

                        # 서보 모터를 먼저 시작 (별도 스레드)
                        servo_thread = threading.Thread(
                            target=_start_servo, daemon=True
                        )
                        servo_thread.start()

                        # 오디오 재생 시작 (1초 지연 후 재생)
                        audio_thread = threading.Thread(
                            target=_start_audio, daemon=True
                        )
                        audio_thread.start()

                        logger.info(
                            f"서보 모터와 오디오 파일을 동시에 시작: {mapped_audio_path}"
                        )

                        # TTS 재생 완료 후 시간 업데이트
                        if not sleep_mode:
                            last_response = ai_response
                            last_interaction_time = time.time()

                        continue  # LLM 호출 없이 다음 루프로 (LED 제어는 이미 위에서 실행됨)

                    # 슬픈 톤 키워드 감지
                    is_sad_topic = any(keyword in user_text for keyword in sad_keywords)
                    print(f"🔍 슬픈 토픽 감지: {is_sad_topic}", flush=True)

                    # AI 응답 생성 (LLM 호출)
                    print("🧠 생각하는 중...", end=" ", flush=True)
                    brain.add_msg(user_text)
                    ai_response = brain.wait_run(
                        ai_name="chipi", device_serial=device_serial
                    )
                    print("✅ 완료", flush=True)
                    logger.info(f"AI: {ai_response}")

                    if not ai_response:
                        response_style = "sad" if is_sad_topic else "neutral"
                        pitch_shift = -10 if is_sad_topic else 0
                        tts.speak(
                            "미안, 다시 말해줄래?",
                            language="ko",
                            style=response_style,
                            pitch_shift=pitch_shift,
                        )
                        continue

                    # 중복 응답 방지
                    if ai_response == last_response:
                        continue

                    # 답변 출력 및 음성 재생
                    print(f"🤖 치피: {ai_response}")

                    # TTS 재생 시작 시 시간 업데이트
                    if not sleep_mode:
                        last_interaction_time = time.time()

                    # 얼굴 표정 감지 및 설정 (키워드 기반)
                    detected_emotion = _detect_face_emotion_from_response(ai_response)
                    print(f"😊 감지된 표정: {detected_emotion}", flush=True)
                    # 비동기로 얼굴 표정 설정 (TTS와 동시에 실행)
                    if DEVICE_SERIAL:
                        threading.Thread(
                            target=lambda: _set_face_emotion(detected_emotion),
                            daemon=True,
                        ).start()

                    # 슬픈 키워드가 있으면 슬픈 톤으로, 없으면 중립 톤으로 재생
                    response_style = "sad" if is_sad_topic else "neutral"
                    pitch_shift = -10 if is_sad_topic else 0
                    print(
                        f"🎤 응답 톤: {response_style}, 피치: {pitch_shift}", flush=True
                    )

                    # TTS 재생과 동시에 서보 모터 실행 (비동기)
                    _run_servo_async()

                    tts.speak(
                        ai_response,
                        language="ko",
                        style=response_style,
                        pitch_shift=pitch_shift,
                    )

                    # TTS 재생 완료 후 시간 업데이트
                    if not sleep_mode:
                        last_response = ai_response
                        last_interaction_time = time.time()

                except KeyboardInterrupt:
                    logger.info("\n사용자에 의해 종료됨")
                    break
                except Exception as e:
                    logger.error(f"루프 중 오류 발생: {e}", exc_info=True)
                    print(f"\n⚠️ 오류 발생: {e}")
                    time.sleep(1)  # 오류 후 잠시 대기

    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 종료됨")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback

        traceback.print_exc()
        input("종료하려면 엔터...")
    finally:
        # Board 정리
        if board:
            try:
                board.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
