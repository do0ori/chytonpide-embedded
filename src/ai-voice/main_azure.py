#!/usr/bin/env python3
# Copyright 2024
# Azure Speech Service (REST API) + Azure OpenAI GPT-4o 음성 어시스턴트
#
# Azure Speech SDK 대신 REST API를 사용하여 Raspberry Pi Zero (ARMv6) 호환성 확보
# 모든 코드가 하나의 파일에 통합되어 있습니다.
# AIY Projects 모듈(aiy.board, aiy.voice.audio)은 시스템에 이미 설치된 것을 사용합니다.

"""
Azure Speech REST API STT -> Trigger Word 감지 -> Azure OpenAI GPT-4o -> Azure Speech REST API TTS 음성 어시스턴트

사용 방법:
    1. .env 파일에 Azure OpenAI 및 Azure Speech 설정 추가
    2. 필요한 패키지 설치: pip3 install requests openai python-dotenv
    3. 실행: python3 ai_assistant_rest.py
"""

import argparse
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time

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

# openai 버전에 따라 다른 import
try:
    import openai

    # openai 버전 확인
    try:
        openai_version = openai.__version__
    except AttributeError:
        if hasattr(openai, "ChatCompletion"):
            openai_version = "0.28.x"
        else:
            openai_version = "0.0.0"

    HAS_AZURE_OPENAI_CLASS = False
    AzureOpenAI = None

    if openai_version.startswith("1."):
        try:
            from openai import AzureOpenAI

            HAS_AZURE_OPENAI_CLASS = True
        except (ImportError, AttributeError):
            HAS_AZURE_OPENAI_CLASS = False
except ImportError:
    print("openai 패키지가 설치되지 않았습니다.")
    print("라즈베리 파이 제로의 경우 다음 명령을 사용하세요:")
    print("  pip3 install 'openai>=0.28.0,<1.0' python-dotenv")
    sys.exit(1)

# AIY Projects 모듈 (시스템에 이미 설치된 것 사용)
try:
    from aiy.board import Board, Led

    HAS_BOARD = True
except ImportError:
    HAS_BOARD = False

try:
    from aiy.voice.audio import AudioFormat, Recorder, play_wav

    HAS_AIY_AUDIO = True
except ImportError:
    HAS_AIY_AUDIO = False
    print("경고: AIY Projects audio 모듈을 찾을 수 없습니다.")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# 환경 변수 로드
# ============================================================================

load_dotenv()

# Azure OpenAI 설정
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.environ.get(
    "AZURE_OPENAI_API_VERSION", "2024-12-01-preview"
)

# Azure Speech 설정
AZURE_SPEECH_API_KEY = os.environ.get("AZURE_SPEECH_API_KEY")
AZURE_SPEECH_REGION = os.environ.get("AZURE_SPEECH_REGION")
AZURE_SPEECH_ENDPOINT = os.environ.get("AZURE_SPEECH_ENDPOINT")

# 트리거 단어 설정
TRIGGER_WORDS = os.environ.get("TRIGGER_WORDS", "치피")

# 검증
if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
    logger.error(
        "AZURE_OPENAI_ENDPOINT와 AZURE_OPENAI_API_KEY가 .env 파일에 설정되어야 합니다."
    )
    sys.exit(1)

if not AZURE_SPEECH_API_KEY or not AZURE_SPEECH_REGION:
    logger.error(
        "AZURE_SPEECH_API_KEY와 AZURE_SPEECH_REGION이 .env 파일에 설정되어야 합니다."
    )
    sys.exit(1)

# Azure Speech REST API 엔드포인트 설정
# 참고: 최신 형식은 https://{region}.stt.speech.microsoft.com
# 구버전 형식(api.cognitive.microsoft.com)은 자동으로 새 형식으로 변환됩니다.
if AZURE_SPEECH_ENDPOINT:
    # 사용자 지정 엔드포인트의 끝 슬래시 제거
    AZURE_SPEECH_ENDPOINT = AZURE_SPEECH_ENDPOINT.rstrip("/")

    # 구버전 형식을 새 형식으로 변환
    # .api.cognitive.microsoft.com 또는 .cognitiveservices.azure.com 형식 감지
    if (
        ".api.cognitive.microsoft.com" in AZURE_SPEECH_ENDPOINT
        or ".cognitiveservices.azure.com" in AZURE_SPEECH_ENDPOINT
    ):
        # 구버전 엔드포인트 → 새 형식 (https://{region}.stt.speech.microsoft.com)
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

# TTS 엔드포인트는 별도로 설정
if AZURE_SPEECH_REGION:
    AZURE_SPEECH_TTS_ENDPOINT = (
        f"https://{AZURE_SPEECH_REGION}.tts.speech.microsoft.com"
    )
else:
    # Region이 없으면 STT 엔드포인트와 유사한 형식 사용
    AZURE_SPEECH_TTS_ENDPOINT = (
        AZURE_SPEECH_ENDPOINT.replace(".stt.", ".tts.")
        if ".stt." in AZURE_SPEECH_ENDPOINT
        else None
    )

logger.info(f"STT 엔드포인트: {AZURE_SPEECH_ENDPOINT}")
logger.info(f"TTS 엔드포인트: {AZURE_SPEECH_TTS_ENDPOINT}")

# ============================================================================
# Azure OpenAI 클라이언트
# ============================================================================


class AzureOpenAIClient:
    """Azure OpenAI GPT-4o 클라이언트"""

    def __init__(self):
        self.endpoint = AZURE_OPENAI_ENDPOINT
        self.api_key = AZURE_OPENAI_API_KEY
        self.api_version = AZURE_OPENAI_API_VERSION
        self.deployment_name = AZURE_OPENAI_DEPLOYMENT_NAME
        self.conversation_history = []

        # System prompt
        self.system_prompt = os.environ.get(
            "SYSTEM_PROMPT",
            "당신은 친절하고 도움이 되는 AI 어시스턴트입니다. 이름은 '치피'입니다. 이모지를 사용하지 않고 한국어로 자연스럽고 간결하게 대답해주세요.",
        )

        # OpenAI 클라이언트 초기화
        if HAS_AZURE_OPENAI_CLASS:
            # openai 1.x 버전
            self.client = AzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.endpoint,
            )
            logger.info("Azure OpenAI 클라이언트 초기화 완료 (openai 1.x)")
        else:
            # openai 0.28.x 버전
            openai.api_type = "azure"
            openai.api_base = self.endpoint
            openai.api_key = self.api_key
            openai.api_version = self.api_version
            self.client = None
            logger.info("Azure OpenAI 클라이언트 초기화 완료 (openai 0.28.x)")

    def chat(self, user_message):
        """사용자 메시지를 처리하고 AI 응답을 반환"""
        try:
            # 대화 기록에 사용자 메시지 추가
            self.conversation_history.append({"role": "user", "content": user_message})

            # 메시지 구성 (시스템 프롬프트 + 대화 기록)
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.conversation_history[-10:])  # 최근 10개 메시지만 유지

            if HAS_AZURE_OPENAI_CLASS:
                # openai 1.x 버전
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                    temperature=0.8,
                    max_tokens=300,
                )
                assistant_message = response.choices[0].message.content
            else:
                # openai 0.28.x 버전
                response = openai.ChatCompletion.create(
                    engine=self.deployment_name,
                    messages=messages,
                    temperature=0.8,
                    max_tokens=300,
                )
                assistant_message = response["choices"][0]["message"]["content"]

            # 대화 기록에 어시스턴트 응답 추가
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_message}
            )

            return assistant_message.strip()

        except Exception as e:
            logger.error(f"Azure OpenAI 오류: {e}", exc_info=True)
            return "죄송합니다. 오류가 발생했습니다."


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

        # STT API URL (전역 엔드포인트 사용)
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
                timeout=15,  # 타임아웃 단축
            )

            if response.status_code == 200:
                result = response.json()
                logger.debug(f"STT 응답: {result}")

                # 응답 형식 확인
                if "RecognitionStatus" in result:
                    if result["RecognitionStatus"] == "Success":
                        text = result.get("DisplayText", "").strip()
                        if text:
                            logger.info(f"인식된 텍스트: {text}")
                            return text
                        else:
                            logger.warning("인식은 성공했지만 텍스트가 비어있습니다.")
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
# Azure Speech REST API TTS
# ============================================================================


class AzureSpeechRESTTTS:
    """Azure Speech Service REST API를 사용한 음성 합성 (TTS)"""

    def __init__(self, language="ko-KR", voice_name="ko-KR-SunHiNeural"):
        """
        Args:
            language: 언어 코드 (기본값: ko-KR)
            voice_name: 음성 이름 (기본값: ko-KR-SunHiNeural)
        """
        self.language = language
        self.voice_name = voice_name
        self.api_key = AZURE_SPEECH_API_KEY
        self.endpoint = AZURE_SPEECH_TTS_ENDPOINT
        self.tts_url = f"{self.endpoint}/cognitiveservices/v1"
        logger.info(f"Azure Speech REST API TTS 초기화 완료 (음성: {voice_name})")

    def synthesize(self, text):
        """텍스트를 음성으로 변환하여 재생합니다."""
        try:
            if not text or not isinstance(text, str) or len(text.strip()) < 1:
                logger.warning("TTS: 빈 텍스트입니다.")
                return False

            # SSML 생성
            ssml = f"""<speak version='1.0' xml:lang='{self.language}'>
    <voice xml:lang='{self.language}' name='{self.voice_name}'>
        {text}
    </voice>
</speak>"""

            # 헤더 설정
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
            }

            # 요청 (참고 코드처럼 빠르게 처리)
            logger.debug(f"TTS 음성 생성 중: {text[:50]}...")
            response = requests.post(
                self.tts_url, headers=headers, data=ssml.encode("utf-8"), timeout=15
            )

            if response.status_code == 200:
                audio_data = response.content

                # 임시 파일에 저장
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as tmp_file:
                    tmp_file.write(audio_data)
                    tmp_file_path = tmp_file.name

                try:
                    # 재생
                    if HAS_AIY_AUDIO:
                        play_wav(tmp_file_path)
                    else:
                        subprocess.run(["aplay", "-q", tmp_file_path], check=True)

                    logger.debug("TTS 음성 출력 완료")
                    return True
                finally:
                    try:
                        os.unlink(tmp_file_path)
                    except Exception:
                        pass
            else:
                logger.error(f"TTS API 오류: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"TTS 오류: {e}", exc_info=True)
            return False


# ============================================================================
# VAD (Voice Activity Detection) - 간단한 에너지 기반
# ============================================================================

# 기본 오디오 포맷
DEFAULT_AUDIO_FORMAT = AudioFormat(
    sample_rate_hz=16000, num_channels=1, bytes_per_sample=2
)


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
                        # 참고 코드처럼: 충분한 침묵이 감지되면 즉시 종료
                        if silence_chunks >= silence_chunks_threshold:
                            if speech_chunks >= min_speech_chunks:
                                recorder.done()
                                if recorder._process:
                                    recorder._process.terminate()
                                    # 참고 코드: 불필요한 sleep 제거
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
            # 오디오 데이터 합치기 (참고 코드처럼 빠르게 처리)
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
# Voice Assistant 메인 클래스
# ============================================================================


class VoiceAssistant:
    """음성 어시스턴트 메인 클래스"""

    def __init__(self, use_board=False):
        """
        Args:
            use_board: Board (LED) 사용 여부
        """
        logger.info("음성 어시스턴트 초기화 중...")

        # 트리거 단어 처리 (환경 변수에서 읽기)
        trigger_words_str = TRIGGER_WORDS.strip()
        if "," in trigger_words_str:
            self.trigger_words = [
                w.strip().lower() for w in trigger_words_str.split(",")
            ]
        elif " " in trigger_words_str:
            self.trigger_words = [w.strip().lower() for w in trigger_words_str.split()]
        else:
            self.trigger_words = [trigger_words_str.lower()]

        # 빈 단어 제거
        self.trigger_words = [w for w in self.trigger_words if w]
        if not self.trigger_words:
            self.trigger_words = ["치피"]

        logger.info(f"트리거 단어: {', '.join(self.trigger_words)}")

        # Azure OpenAI 클라이언트
        self.openai_client = AzureOpenAIClient()

        # Azure Speech REST API STT/TTS
        self.stt = AzureSpeechRESTSTT(language="ko-KR")
        self.tts = AzureSpeechRESTTTS(
            language="ko-KR",
            voice_name=os.environ.get("AZURE_TTS_VOICE", "ko-KR-SunHiNeural"),
        )

        # VAD 초기화 (실시간 응답을 위해 조정)
        # 참고 코드처럼 빠른 응답: 침묵 시간 단축, 최소 음성 시간 단축
        self.vad = EnergyBasedVAD(
            energy_threshold=0.01, silence_duration=0.5, min_speech_duration=0.15
        )

        # Board 초기화
        self.board = None
        if use_board and HAS_BOARD:
            try:
                self.board = Board()
                logger.info("Board 초기화 완료")
            except Exception as e:
                logger.warning(f"Board 초기화 실패: {e}")

        self.running = False
        self.last_response = ""  # 중복 응답 방지용
        self.sleep_mode = True  # Sleep/Wake 모드 관리
        self.last_interaction_time = None  # 마지막 상호작용 시간
        self.sleep_timeout = float(
            os.environ.get("SLEEP_TIMEOUT", "10.0")
        )  # Sleep 모드 전환 대기 시간 (초)

    def _indicate_listening(self, is_listening):
        """듣는 중 상태를 LED로 표시"""
        if self.board and self.board.led:
            if is_listening:
                self.board.led.state = Led.ON
            else:
                self.board.led.state = Led.OFF

    def _contains_trigger_word(self, text):
        """텍스트에 트리거 단어가 포함되어 있는지 확인"""
        if not text:
            return False
        text_lower = text.lower()
        # 여러 트리거 단어 중 하나라도 포함되어 있으면 True
        return any(trigger in text_lower for trigger in self.trigger_words)

    def _process_user_input(self, user_text, force_wake=False):
        """
        사용자 입력 처리

        Args:
            user_text: 사용자 입력 텍스트
            force_wake: Sleep mode에서 트리거 단어로 wake한 경우 True
        """
        if not user_text:
            return

        logger.info(f"사용자: {user_text}")

        # Sleep mode에서 트리거 단어 확인 (wake하지 않은 경우)
        if self.sleep_mode and not force_wake:
            if not self._contains_trigger_word(user_text):
                logger.debug(
                    f"Sleep mode: 트리거 단어({', '.join(self.trigger_words)})가 감지되지 않았습니다."
                )
                return

            # 트리거 단어 감지 → Wake mode로 전환
            logger.info("트리거 단어 감지! Wake mode로 전환합니다.")
            self.sleep_mode = False
            self.last_interaction_time = time.time()
            # 트리거 단어 제거 (예: "치피 안녕하세요" → "안녕하세요")
            cleaned_text = user_text
            for trigger in self.trigger_words:
                cleaned_text = cleaned_text.replace(trigger, "", 1).strip()
            if cleaned_text:
                user_text = cleaned_text
            else:
                # 트리거 단어만 있는 경우 기본 응답
                logger.info("트리거 단어만 감지되었습니다.")
                self.tts.synthesize("네, 말씀해주세요.")
                return "wake"

        # Wake mode: 트리거 단어 확인 없이 모든 말에 응답
        if not self.sleep_mode:
            self.last_interaction_time = time.time()  # 상호작용 시간 업데이트

        # 종료 명령 확인
        if any(
            cmd in user_text.lower() for cmd in ["종료", "끝내", "그만", "exit", "quit"]
        ):
            logger.info("종료 명령을 받았습니다.")
            self.tts.synthesize("안녕히 가세요!")
            return "quit"

        # Sleep 명령 확인 (Sleep mode로 전환)
        if any(cmd in user_text.lower() for cmd in ["잘자", "sleep", "휴식", "쉬어"]):
            logger.info("Sleep mode로 전환합니다.")
            self.sleep_mode = True
            self.last_interaction_time = None
            # TTS 없이 로그만 남김
            return "sleep"

        # AI 응답 생성
        logger.info("AI 응답 생성 중...")
        response_text = self.openai_client.chat(user_text)
        logger.info(f"AI: {response_text}")

        # 중복 응답 방지
        if response_text == self.last_response:
            logger.debug("이전과 동일한 응답입니다. TTS를 건너뜁니다.")
            return

        # TTS로 음성 출력 (재생 시작 시 시간 업데이트)
        # TTS 재생 중에도 타임아웃이 발생하지 않도록 재생 시작 시점에 시간 업데이트
        if not self.sleep_mode:
            self.last_interaction_time = time.time()

        success = self.tts.synthesize(response_text)
        if success:
            self.last_response = response_text
            # TTS 재생 완료 후에도 시간 업데이트 (다음 타임아웃 시작점)
            if not self.sleep_mode:
                self.last_interaction_time = time.time()

        return response_text

    def run(self):
        """어시스턴트 실행"""
        logger.info("=" * 50)
        logger.info("음성 어시스턴트 시작 (REST API 버전)")
        logger.info(f"트리거 단어: {', '.join(self.trigger_words)}")
        logger.info(f"Sleep timeout: {self.sleep_timeout}초")
        logger.info(
            "Sleep mode에서 시작합니다. 트리거 단어를 말하면 Wake mode로 전환됩니다."
        )
        logger.info("Wake mode에서는 트리거 단어 없이 모든 말에 응답합니다.")
        logger.info("일정 시간 동안 말이 없으면 자동으로 Sleep mode로 전환됩니다.")
        logger.info("종료하려면 '종료'라고 말하거나 Ctrl+C를 누르세요.")
        logger.info("=" * 50)

        # 시작 안내 음성 (Sleep mode)
        main_trigger = self.trigger_words[0] if self.trigger_words else "치피"
        self.tts.synthesize(
            f"안녕하세요! 저는 {main_trigger}입니다. 트리거 단어를 말씀해주세요."
        )

        self.running = True
        self.sleep_mode = True  # 초기 상태: Sleep mode

        try:
            while self.running:
                try:
                    # Sleep mode: 타임아웃 체크 (VAD 대기 중에만 체크)
                    # TTS 재생 중에는 타임아웃이 발생하지 않도록 VAD 대기 상태에서만 체크
                    if not self.sleep_mode and self.last_interaction_time:
                        time_since_last = time.time() - self.last_interaction_time
                        if time_since_last >= self.sleep_timeout:
                            logger.info(
                                f"Wake mode 타임아웃 ({self.sleep_timeout}초). Sleep mode로 전환합니다."
                            )
                            self.sleep_mode = True
                            self.last_interaction_time = None
                            # TTS 없이 로그만 남김

                    # 모드 표시
                    mode_str = "WAKE" if not self.sleep_mode else "SLEEP"
                    logger.debug(f"[{mode_str} MODE] 음성 입력 대기 중...")

                    # 듣는 중 표시
                    self._indicate_listening(True)

                    # VAD로 음성 녹음
                    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    temp_wav.close()

                    try:
                        audio_data = self.vad.record(
                            on_start=lambda: self._indicate_listening(True),
                            on_stop=lambda: self._indicate_listening(False),
                            filename=temp_wav.name,
                        )

                        self._indicate_listening(False)

                        if not audio_data:
                            logger.debug("음성이 감지되지 않았습니다.")
                            continue

                        # 음성 종료 감지 즉시 STT 호출
                        logger.debug("음성 종료 감지, STT 처리 시작...")
                        user_text = self.stt.recognize_from_file(temp_wav.name)

                        if not user_text:
                            continue

                        # Sleep mode: 트리거 단어 확인 후 wake
                        force_wake = False
                        if self.sleep_mode:
                            if self._contains_trigger_word(user_text):
                                force_wake = True
                                logger.info("트리거 단어 감지! Wake mode로 전환합니다.")
                                self.sleep_mode = False
                                self.last_interaction_time = time.time()
                                # 트리거 단어 제거
                                cleaned_text = user_text
                                for trigger in self.trigger_words:
                                    cleaned_text = cleaned_text.replace(
                                        trigger, "", 1
                                    ).strip()
                                if cleaned_text:
                                    user_text = cleaned_text
                                else:
                                    # 트리거 단어만 있는 경우
                                    self.tts.synthesize("네, 말씀해주세요.")
                                    continue

                        # 사용자 입력 처리
                        result = self._process_user_input(
                            user_text, force_wake=force_wake
                        )

                        if result == "quit":
                            break
                        elif result == "sleep":
                            continue  # Sleep mode로 전환됨
                        elif result == "wake":
                            continue  # Wake mode로 전환됨

                    finally:
                        # 임시 파일 삭제
                        try:
                            os.unlink(temp_wav.name)
                        except Exception:
                            pass

                    # 최소한의 대기
                    time.sleep(0.1)

                except KeyboardInterrupt:
                    logger.info("\n사용자에 의해 중단됨")
                    break
                except Exception as e:
                    logger.error(f"루프 오류: {e}", exc_info=True)
                    self._indicate_listening(False)
                    time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n종료 중...")

        finally:
            self.cleanup()

    def cleanup(self):
        """리소스 정리"""
        logger.info("리소스 정리 중...")
        self.running = False
        if self.board:
            try:
                self.board.close()
            except Exception:
                pass
        logger.info("종료 완료")


# ============================================================================
# 메인 함수
# ============================================================================


def signal_handler(sig, frame):
    """시그널 핸들러"""
    logger.info("\n시그널 수신: 종료 중...")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Azure Speech REST API + Azure OpenAI 음성 어시스턴트"
    )
    parser.add_argument(
        "--no-board", action="store_true", help="Board (LED) 사용 안 함"
    )
    parser.add_argument(
        "--voice-name",
        type=str,
        default=os.environ.get("AZURE_TTS_VOICE", "ko-KR-SunHiNeural"),
        help="TTS 음성 이름 (기본값: .env의 AZURE_TTS_VOICE 또는 ko-KR-SunHiNeural)",
    )

    args = parser.parse_args()

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        assistant = VoiceAssistant(use_board=not args.no_board)

        # TTS 음성 변경
        default_voice = os.environ.get("AZURE_TTS_VOICE", "ko-KR-SunHiNeural")
        if args.voice_name != default_voice:
            assistant.tts = AzureSpeechRESTTTS(
                language="ko-KR", voice_name=args.voice_name
            )

        assistant.run()

    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 종료됨")
    except Exception as e:
        logger.error(f"치명적 오류: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
