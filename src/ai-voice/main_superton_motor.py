#!/usr/bin/env python3
"""
SuperTone TTS + Azure Speech REST API STT 음성 어시스턴트
라즈베리파이 제로 WH (Python 3.7.3) 호환

Azure Speech SDK 대신 REST API를 사용하여 Raspberry Pi Zero (ARMv6) 호환성 확보
AIY Projects 모듈(aiy.voice.audio)을 사용하여 마이크와 스피커 제어
"""

import io
import logging
import os
import subprocess
import sys
import tempfile
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

# 경로 설정 (servo 패키지처럼)
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

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("requests가 설치되지 않았습니다: pip3 install requests")
    sys.exit(1)

# AIY Projects 모듈 (시스템에 이미 설치된 것 사용)
try:
    from aiy.voice.audio import AudioFormat, Recorder, play_wav

    HAS_AIY_AUDIO = True
except ImportError:
    HAS_AIY_AUDIO = False
    print("경고: AIY Projects audio 모듈을 찾을 수 없습니다.")

try:
    from aiy.board import Board, Led

    HAS_BOARD = True
except ImportError:
    HAS_BOARD = False

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

# Azure Speech 설정 (STT용)
AZURE_SPEECH_API_KEY = os.environ.get("AZURE_SPEECH_API_KEY")
AZURE_SPEECH_REGION = os.environ.get("AZURE_SPEECH_REGION")
AZURE_SPEECH_ENDPOINT = os.environ.get("AZURE_SPEECH_ENDPOINT")

# SuperTone 설정 (TTS용)
SUPERTON_API_KEY = os.environ.get("SUPERTON_API_KEY")
SUPERTON_VOICE_ID = os.environ.get("SUPERTON_VOICE_ID")

# 트리거 단어 설정 (Wake word)
TRIGGER_WORDS = os.environ.get("TRIGGER_WORDS", "치피")

# Sleep mode 타임아웃 설정
SLEEP_TIMEOUT = float(os.environ.get("SLEEP_TIMEOUT", "10.0"))

# VAD 설정 (시끄러운 환경 대응)
VAD_ENERGY_THRESHOLD = float(os.environ.get("VAD_ENERGY_THRESHOLD", "0.005"))
VAD_SILENCE_DURATION = float(os.environ.get("VAD_SILENCE_DURATION", "0.8"))
VAD_MIN_SPEECH_DURATION = float(os.environ.get("VAD_MIN_SPEECH_DURATION", "0.3"))

# 검증
if not AZURE_SPEECH_API_KEY or not AZURE_SPEECH_REGION:
    logger.error(
        "AZURE_SPEECH_API_KEY와 AZURE_SPEECH_REGION이 .env 파일에 설정되어야 합니다."
    )
    sys.exit(1)

if not SUPERTON_API_KEY or not SUPERTON_VOICE_ID:
    logger.error(
        "SUPERTON_API_KEY와 SUPERTON_VOICE_ID가 .env 파일에 설정되어야 합니다."
    )
    sys.exit(1)

# Azure Speech REST API 엔드포인트 설정
# 참고: 최신 형식은 https://{region}.stt.speech.microsoft.com
# 구버전 형식은 자동으로 새 형식으로 변환됩니다.
if AZURE_SPEECH_ENDPOINT:
    AZURE_SPEECH_ENDPOINT = AZURE_SPEECH_ENDPOINT.rstrip("/")
    # 구버전 형식 감지 (.api.cognitive.microsoft.com 또는 .cognitiveservices.azure.com)
    if (
        ".api.cognitive.microsoft.com" in AZURE_SPEECH_ENDPOINT
        or ".cognitiveservices.azure.com" in AZURE_SPEECH_ENDPOINT
    ):
        logger.info("구버전 엔드포인트 감지, 새 형식으로 변환합니다.")
        logger.info(f"원본: {AZURE_SPEECH_ENDPOINT}")
        # Region 기반으로 새 엔드포인트 생성
        AZURE_SPEECH_ENDPOINT = (
            f"https://{AZURE_SPEECH_REGION}.stt.speech.microsoft.com"
        )
        logger.info(f"변환됨: {AZURE_SPEECH_ENDPOINT}")
else:
    # 기본 STT 엔드포인트 형식 (권장)
    AZURE_SPEECH_ENDPOINT = f"https://{AZURE_SPEECH_REGION}.stt.speech.microsoft.com"

logger.info(f"STT 엔드포인트: {AZURE_SPEECH_ENDPOINT}")

# ============================================================================
# Azure Speech REST API STT
# ============================================================================


class AzureSpeechRESTSTT:
    """Azure Speech Service REST API를 사용한 음성 인식 (STT)"""

    def __init__(self, language="ko-KR"):
        """
        Args:
            language: 언어 코드 (기본값: ko-KR)
        """
        self.language = language
        self.api_key = AZURE_SPEECH_API_KEY
        self.stt_url = f"{AZURE_SPEECH_ENDPOINT}/speech/recognition/conversation/cognitiveservices/v1"
        logger.info(f"Azure Speech REST API STT 초기화 완료 (언어: {language})")

    def recognize_from_file(self, audio_file_path):
        """
        오디오 파일로부터 음성을 인식합니다.

        Args:
            audio_file_path: WAV 파일 경로

        Returns:
            인식된 텍스트 또는 None
        """
        try:
            # 오디오 파일 읽기
            with open(audio_file_path, "rb") as audio_file:
                audio_data = audio_file.read()

            # 헤더 설정
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000; channels=1",
                "Accept": "application/json",
            }

            # 파라미터 (language는 필수)
            params = {"language": self.language}

            # 요청
            logger.info("음성 인식 중...")
            response = requests.post(
                self.stt_url,
                headers=headers,
                params=params,
                data=audio_data,
                timeout=15,
            )

            if response.status_code == 200:
                result = response.json()
                logger.debug(f"STT 응답: {result}")

                # 응답 형식 확인
                if "RecognitionStatus" in result:
                    if result["RecognitionStatus"] == "Success":
                        # DisplayText와 Text 모두 확인
                        text = result.get("DisplayText", "") or result.get("Text", "")
                        text = text.strip()
                        if text:
                            logger.info(f"인식된 텍스트: {text}")
                            return text
                        else:
                            logger.warning("인식은 성공했지만 텍스트가 비어있습니다.")
                            logger.debug(f"전체 응답: {result}")
                            # 오디오 파일 크기 확인
                            try:
                                file_size = os.path.getsize(audio_file_path)
                                logger.debug(f"오디오 파일 크기: {file_size} bytes")
                            except Exception:
                                pass
                            return None
                    else:
                        status = result.get("RecognitionStatus", "Unknown")
                        error_details = result.get("ErrorDetails", "")
                        logger.warning(f"인식 실패: {status} - {error_details}")
                        return None
                elif "DisplayText" in result:
                    # 직접 DisplayText가 있는 경우
                    text = result["DisplayText"].strip()
                    logger.info(f"인식된 텍스트: {text}")
                    return text
                else:
                    logger.warning(f"예상치 못한 응답 형식: {result}")
                    return None
            elif response.status_code == 401:
                logger.error("STT API 인증 오류 (401): API 키를 확인하세요.")
                logger.error(f"응답: {response.text}")
                return None
            elif response.status_code == 404:
                logger.error("STT API 엔드포인트 오류 (404): URL을 확인하세요.")
                logger.error(f"사용된 URL: {self.stt_url}")
                logger.error(f"Region: {AZURE_SPEECH_REGION}")
                logger.error(f"응답: {response.text}")
                return None
            else:
                logger.error(f"STT API 오류 ({response.status_code}): {response.text}")
                return None

        except Exception as e:
            logger.error(f"STT 오류: {e}", exc_info=True)
            return None


# ============================================================================
# SuperTone TTS (REST API)
# ============================================================================


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
# VAD (Voice Activity Detection) - 간단한 에너지 기반
# ============================================================================

# 기본 오디오 포맷
if HAS_AIY_AUDIO:
    DEFAULT_AUDIO_FORMAT = AudioFormat(
        sample_rate_hz=16000, num_channels=1, bytes_per_sample=2
    )
else:
    DEFAULT_AUDIO_FORMAT = None


def calculate_rms(audio_data):
    """오디오 데이터의 RMS 에너지 계산"""
    if not audio_data:
        return 0.0

    import array

    samples = array.array("h", audio_data)
    if len(samples) == 0:
        return 0.0

    # RMS 계산
    sum_squares = sum(float(s) ** 2 for s in samples)
    mean_square = sum_squares / len(samples)
    rms = mean_square**0.5
    # 정규화 (16-bit: 최대값 32768)
    normalized = min(rms / 32768.0, 1.0)
    return normalized


class EnergyBasedVAD:
    """에너지 기반 Voice Activity Detection"""

    def __init__(
        self,
        energy_threshold=0.01,
        silence_duration=1.0,
        min_speech_duration=0.3,
        chunk_duration=0.1,
    ):
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.min_speech_duration = min_speech_duration
        self.chunk_duration = chunk_duration

    def record(self, on_start=None, on_stop=None, filename=None):
        """
        음성을 감지하고 녹음합니다.

        Returns:
            오디오 데이터 (bytes) 또는 None
        """
        if not HAS_AIY_AUDIO:
            logger.error("AIY Projects audio 모듈이 필요합니다.")
            return None

        silence_chunks = 0
        speech_chunks = 0
        speech_started = False

        silence_chunks_threshold = int(self.silence_duration / self.chunk_duration)
        min_speech_chunks = int(self.min_speech_duration / self.chunk_duration)

        logger.info("VAD 대기 중...")

        audio_chunks = []

        with Recorder() as recorder:
            chunks = recorder.record(
                DEFAULT_AUDIO_FORMAT,
                chunk_duration_sec=self.chunk_duration,
                on_start=lambda: None,
                on_stop=lambda: None,
                filename=filename,
            )

            for chunk in chunks:
                energy = calculate_rms(chunk)

                if not speech_started:
                    if energy > self.energy_threshold:
                        speech_started = True
                        speech_chunks = 1
                        audio_chunks.append(chunk)
                        if on_start:
                            on_start()
                        logger.info("음성 감지됨")
                else:
                    audio_chunks.append(chunk)
                    if energy > self.energy_threshold:
                        speech_chunks += 1
                        silence_chunks = 0
                    else:
                        silence_chunks += 1
                        # 충분한 침묵이 감지되면 즉시 종료
                        if silence_chunks >= silence_chunks_threshold:
                            if speech_chunks >= min_speech_chunks:
                                recorder.done()
                                if recorder._process:
                                    recorder._process.terminate()
                                    time.sleep(0.05)
                                if on_stop:
                                    on_stop()
                                logger.info("음성 종료 감지됨")
                                break
                            else:
                                # 너무 짧은 음성, 재시작
                                speech_started = False
                                speech_chunks = 0
                                silence_chunks = 0
                                audio_chunks = []

        if audio_chunks and speech_chunks >= min_speech_chunks:
            # 오디오 데이터 합치기
            import array

            combined = array.array("h")
            for chunk in audio_chunks:
                combined.extend(array.array("h", chunk))

            # WAV 파일로 변환 (파일명이 제공된 경우에만)
            if filename:
                import wave

                try:
                    with wave.open(filename, "wb") as wav_file:
                        wav_file.setnchannels(DEFAULT_AUDIO_FORMAT.num_channels)
                        wav_file.setsampwidth(DEFAULT_AUDIO_FORMAT.bytes_per_sample)
                        wav_file.setframerate(DEFAULT_AUDIO_FORMAT.sample_rate_hz)
                        wav_file.writeframes(combined.tobytes())
                    logger.debug(f"오디오 파일 저장 완료: {filename}")
                except Exception as e:
                    logger.warning(f"파일 저장 오류: {e}")

            return combined.tobytes()

        return None


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


def _contains_trigger_word(text, trigger_words):
    """텍스트에 트리거 단어가 포함되어 있는지 확인"""
    if not text or not trigger_words:
        return False
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in trigger_words)


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
    """서보 모터로 화분 흔들기 실행 (subprocess 사용)"""
    script_path = _find_servo_script_path()
    if not script_path:
        logger.error("서보 스크립트를 찾을 수 없습니다.")
        return False

    try:
        logger.info(f"서보 모터 실행: {script_path}")
        # sudo 권한으로 실행
        result = subprocess.run(
            ["sudo", "python3", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,  # 최대 30초 대기
            text=True,
        )

        if result.returncode == 0:
            logger.info("서보 모터 실행 완료")
            if result.stdout:
                logger.debug(f"서보 출력: {result.stdout}")
            return True
        else:
            logger.error(f"서보 모터 실행 실패 (코드: {result.returncode})")
            if result.stderr:
                logger.error(f"서보 오류: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("서보 모터 실행 시간 초과 (30초)")
        return False
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


def _contains_servo_keywords(text):
    """서보 모터 실행 키워드 감지"""
    if not text:
        return False

    servo_keywords = [
        "화분 흔들어",
        "화분 흔들어줘",
        "모터 움직여",
        "서보 움직여",
        "흔들어줘",
        "흔들어",
        "모터 실행",
        "서보 실행",
    ]

    text_lower = text.lower()
    return any(keyword in text_lower for keyword in servo_keywords)


def main():
    device_serial = os.environ.get("DEVICE_SERIAL")
    if not device_serial:
        print("⚠️ DEVICE_SERIAL 없음")

    # 트리거 단어 처리
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

    print("\n============== ⚡ 치피(Chipi) SuperTone TTS 모드 시작 ==============\n")
    print(f"트리거 단어: {', '.join(trigger_words)}")
    print(f"Sleep timeout: {SLEEP_TIMEOUT}초")
    print("Sleep mode에서 시작합니다. 트리거 단어를 말하면 Wake mode로 전환됩니다.")
    print("Wake mode에서는 트리거 단어 없이 모든 말에 응답합니다.")
    print("일정 시간 동안 말이 없으면 자동으로 Sleep mode로 전환됩니다.")
    print("종료하려면 '종료'라고 말하거나 Ctrl+C를 누르세요.\n")

    # Board (LED) 초기화
    board = None
    if HAS_BOARD:
        try:
            board = Board()
            logger.info("Board 초기화 완료")
        except Exception as e:
            logger.warning(f"Board 초기화 실패: {e}")

    def indicate_listening(is_listening):
        """듣는 중 상태를 LED로 표시"""
        if board and board.led:
            if is_listening:
                board.led.state = Led.ON
            else:
                board.led.state = Led.OFF

    try:
        print("🧠 두뇌(LLM) 연결 중...", end=" ", flush=True)
        brain = ChipiBrain()
        print("✅ 완료")

        print("🎤 음성(SuperTone TTS) 연결 중...", end=" ", flush=True)
        tts = SupertonTTS()
        print("✅ 완료")

        print("👂 음성 인식(STT) 연결 중...", end=" ", flush=True)
        stt = AzureSpeechRESTSTT(language="ko-KR")
        print("✅ 완료\n")

        # VAD 초기화 (환경 변수로 설정 가능, 시끄러운 환경 대응)
        # 시끄러운 환경에서는 환경 변수로 조정:
        # VAD_ENERGY_THRESHOLD=0.02 (배경 소음 무시)
        # VAD_SILENCE_DURATION=1.2 (말 끝까지 더 기다림)
        # VAD_MIN_SPEECH_DURATION=0.5 (더 긴 음성만 인식)
        vad = EnergyBasedVAD(
            energy_threshold=VAD_ENERGY_THRESHOLD,
            silence_duration=VAD_SILENCE_DURATION,
            min_speech_duration=VAD_MIN_SPEECH_DURATION,
        )
        logger.info(
            f"VAD 설정: energy_threshold={VAD_ENERGY_THRESHOLD}, "
            f"silence_duration={VAD_SILENCE_DURATION}, "
            f"min_speech_duration={VAD_MIN_SPEECH_DURATION}"
        )

        # Sleep/Wake 모드 관리
        sleep_mode = True  # 초기 상태: Sleep mode
        last_interaction_time = None
        last_response = ""  # 중복 응답 방지용

        # 시작 안내 음성 (Sleep mode)
        main_trigger = trigger_words[0] if trigger_words else "치피"
        tts.speak(
            f"안녕하세요! 저는 {main_trigger}입니다. 대화하고 싶을 때 저를 불러주세요.",
            f"안녕하세요! 저는 {main_trigger}입니다. 트리거 단어를 말씀해주세요.",
            language="ko",
            style="neutral",
        )

        # 프로그램 시작 시 서보 모터 한 번 실행 (TTS와 동시에)
        print("🔄 프로그램 시작: 서보 모터 실행 중...", flush=True)
        logger.info("프로그램 시작: 서보 모터 자동 실행 (비동기)")
        try:
            _run_servo_async()
            print("✅ 서보 모터 실행 시작 (백그라운드)\n", flush=True)
        except Exception as e:
            logger.warning(f"서보 모터 실행 중 오류: {e}")

        # 슬픈 톤을 사용할 키워드 목록
        sad_keywords = [
            "죽고",
            "자살",
            "끝내고",
            "절망",
            "극도로 힘들",
            "살기싫",
            "뛰어내리",
        ]

        while True:
            # 1. VAD로 음성 녹음
            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_wav.close()

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

                # 모드 표시
                mode_str = "WAKE" if not sleep_mode else "SLEEP"
                logger.debug(f"[{mode_str} MODE] 음성 입력 대기 중...")

                print("\n👂 듣는 중...", end=" ", flush=True)
                indicate_listening(True)

                audio_data = vad.record(
                    on_start=lambda: indicate_listening(True),
                    on_stop=lambda: indicate_listening(False),
                    filename=temp_wav.name,
                )

                indicate_listening(False)

                if not audio_data:
                    print("🔕 (침묵)", flush=True)
                    continue

                # 오디오 파일 크기 확인 (디버깅)
                try:
                    file_size = os.path.getsize(temp_wav.name)
                    duration = len(audio_data) / (16000 * 2)  # 16kHz, 16-bit (2 bytes)
                    logger.info(
                        f"오디오 파일: {file_size} bytes, 길이: {duration:.2f}초"
                    )

                    # 너무 짧은 오디오는 건너뛰기
                    if duration < 0.2:
                        logger.warning(
                            f"오디오가 너무 짧습니다: {duration:.2f}초 (최소 0.2초 필요)"
                        )
                        continue
                except Exception as e:
                    logger.debug(f"오디오 파일 정보 확인 실패: {e}")

                # 2. STT로 텍스트 변환
                print("📝 인식 중...", end=" ", flush=True)
                user_text = stt.recognize_from_file(temp_wav.name)

                if not user_text:
                    print("❌ 인식 실패", flush=True)
                    continue

                print(f'✅ 인식됨: "{user_text}"', flush=True)
                logger.info(f"사용자: {user_text}")

                # Sleep mode: 트리거 단어 확인
                if sleep_mode:
                    if _contains_trigger_word(user_text, trigger_words):
                        logger.info("트리거 단어 감지! Wake mode로 전환합니다.")
                        sleep_mode = False
                        last_interaction_time = time.time()
                        # 트리거 단어 제거 (예: "치피 안녕하세요" → "안녕하세요")
                        cleaned_text = user_text
                        for trigger in trigger_words:
                            cleaned_text = cleaned_text.replace(trigger, "", 1).strip()
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
                        logger.debug(
                            f"Sleep mode: 트리거 단어({', '.join(trigger_words)})가 감지되지 않았습니다."
                        )
                        continue

                # Wake mode: 상호작용 시간 업데이트
                if not sleep_mode:
                    last_interaction_time = time.time()

                # 종료 명령 확인
                if any(
                    cmd in user_text.lower()
                    for cmd in ["종료", "끝내", "그만", "exit", "quit"]
                ):
                    logger.info("종료 명령을 받았습니다.")
                    tts.speak("안녕히 가세요!", language="ko", style="neutral")
                    break

                # Sleep 명령 확인 (Sleep mode로 전환)
                if any(
                    cmd in user_text.lower()
                    for cmd in ["잘자", "sleep", "휴식", "쉬어"]
                ):
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

                # 슬픈 톤 키워드 감지
                is_sad_topic = any(keyword in user_text for keyword in sad_keywords)
                print(f"🔍 슬픈 토픽 감지: {is_sad_topic}", flush=True)

                # 3. AI 응답 생성
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
                    logger.debug("이전과 동일한 응답입니다. TTS를 건너뜁니다.")
                    continue

                # 4. 답변 출력 및 음성 재생
                print(f"🤖 치피: {ai_response}")

                # TTS 재생 시작 시 시간 업데이트
                if not sleep_mode:
                    last_interaction_time = time.time()

                # 슬픈 키워드가 있으면 슬픈 톤으로, 없으면 중립 톤으로 재생
                response_style = "sad" if is_sad_topic else "neutral"
                pitch_shift = -10 if is_sad_topic else 0
                print(f"🎤 응답 톤: {response_style}, 피치: {pitch_shift}", flush=True)

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

            finally:
                # 임시 파일 삭제
                try:
                    os.unlink(temp_wav.name)
                except Exception:
                    pass

            # 최소한의 대기
            time.sleep(0.1)

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
