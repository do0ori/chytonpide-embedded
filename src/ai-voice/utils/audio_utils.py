#!/usr/bin/env python3
"""
오디오 파일 재생 유틸리티

공통 오디오 재생 함수들을 제공합니다.
"""

import json
import logging
import os
import subprocess
import threading

logger = logging.getLogger(__name__)

# AIY Projects play_wav import 시도
try:
    from aiy.voice.audio import play_wav

    HAS_AIY_AUDIO = True
except ImportError:
    HAS_AIY_AUDIO = False


def play_intro_audio(tts=None, trigger_words=None, use_trigger_word=None):
    """intro.wav 파일 재생

    Args:
        tts: TTS 객체 (파일을 찾을 수 없거나 재생 실패 시 대체용)
        trigger_words: 트리거 단어 리스트 (대체용)
        use_trigger_word: 트리거 단어 사용 여부 (대체용)
    """
    # 현재 파일의 위치를 기준으로 경로 찾기
    current_file = os.path.abspath(__file__)
    utils_dir = os.path.dirname(current_file)
    ai_voice_dir = os.path.dirname(utils_dir)

    intro_paths = [
        # utils/audio/intro.wav (현재 디렉토리 기준)
        os.path.join(utils_dir, "audio", "intro.wav"),
        # ai-voice 디렉토리 기준
        os.path.join(ai_voice_dir, "utils", "audio", "intro.wav"),
        # 절대 경로 (라즈베리파이 기본 경로)
        "/home/pi/chytonpide/src/ai-voice/utils/audio/intro.wav",
        os.path.expanduser("~/chytonpide/src/ai-voice/utils/audio/intro.wav"),
    ]

    intro_file = None
    for path in intro_paths:
        abs_path = os.path.abspath(os.path.expanduser(path))
        if os.path.exists(abs_path):
            intro_file = abs_path
            break

    if not intro_file:
        logger.warning("intro.wav 파일을 찾을 수 없습니다. TTS로 대체합니다.")
        # 파일을 찾을 수 없으면 기본 안내 음성 재생
        if tts:
            if use_trigger_word and trigger_words:
                main_trigger = trigger_words[0] if trigger_words else "치피"
                if hasattr(tts, "speak"):
                    # SupertonTTS
                    tts.speak(
                        f"안녕하세요! 저는 {main_trigger}입니다. 대화하고 싶을 때 저를 불러주세요.",
                        language="ko",
                        style="neutral",
                    )
                elif hasattr(tts, "synthesize"):
                    # AzureSpeechRESTTTS
                    tts.synthesize(
                        f"안녕하세요! 저는 {main_trigger}입니다. 트리거 단어를 말씀해주세요."
                    )
            else:
                if hasattr(tts, "speak"):
                    tts.speak(
                        "안녕하세요! 저는 치피입니다. 말씀해주세요.",
                        language="ko",
                        style="neutral",
                    )
                elif hasattr(tts, "synthesize"):
                    tts.synthesize("안녕하세요! 저는 치피입니다. 말씀해주세요.")
        return

    try:
        logger.info(f"intro.wav 재생: {intro_file}")
        # AIY Projects play_wav 또는 aplay 사용
        if HAS_AIY_AUDIO:
            play_wav(intro_file)
        else:
            subprocess.run(["aplay", "-q", intro_file], check=True)
        logger.debug("intro.wav 재생 완료")
    except Exception as e:
        logger.error(f"intro.wav 재생 오류: {e}", exc_info=True)
        # 재생 실패 시 TTS로 대체
        if tts:
            if use_trigger_word and trigger_words:
                main_trigger = trigger_words[0] if trigger_words else "치피"
                if hasattr(tts, "speak"):
                    tts.speak(
                        f"안녕하세요! 저는 {main_trigger}입니다. 대화하고 싶을 때 저를 불러주세요.",
                        language="ko",
                        style="neutral",
                    )
                elif hasattr(tts, "synthesize"):
                    tts.synthesize(
                        f"안녕하세요! 저는 {main_trigger}입니다. 트리거 단어를 말씀해주세요."
                    )
            else:
                if hasattr(tts, "speak"):
                    tts.speak(
                        "안녕하세요! 저는 치피입니다. 말씀해주세요.",
                        language="ko",
                        style="neutral",
                    )
                elif hasattr(tts, "synthesize"):
                    tts.synthesize("안녕하세요! 저는 치피입니다. 말씀해주세요.")


def _find_audio_dir():
    """오디오 디렉토리 경로 찾기"""
    current_file = os.path.abspath(__file__)
    utils_dir = os.path.dirname(current_file)
    ai_voice_dir = os.path.dirname(utils_dir)

    audio_paths = [
        # utils/audio (현재 디렉토리 기준)
        os.path.join(utils_dir, "audio"),
        # ai-voice/utils/audio
        os.path.join(ai_voice_dir, "utils", "audio"),
        # 절대 경로 (라즈베리파이 기본 경로)
        "/home/pi/chytonpide/src/ai-voice/utils/audio",
        os.path.expanduser("~/chytonpide/src/ai-voice/utils/audio"),
    ]

    for path in audio_paths:
        abs_path = os.path.abspath(os.path.expanduser(path))
        if os.path.exists(abs_path) and os.path.isdir(abs_path):
            return abs_path

    return None


def play_audio_file(filename):
    """
    오디오 파일 재생

    Args:
        filename: 오디오 파일명 (예: "a_01.wav", "intro.wav")

    Returns:
        bool: 재생 성공 여부
    """
    audio_dir = _find_audio_dir()
    if not audio_dir:
        logger.warning("오디오 디렉토리를 찾을 수 없습니다.")
        return False

    audio_file = os.path.join(audio_dir, filename)
    if not os.path.exists(audio_file):
        logger.warning(f"오디오 파일을 찾을 수 없습니다: {audio_file}")
        return False

    try:
        logger.info(f"오디오 파일 재생: {audio_file}")
        # AIY Projects play_wav 또는 aplay 사용
        if HAS_AIY_AUDIO:
            play_wav(audio_file)
        else:
            subprocess.run(["aplay", "-q", audio_file], check=True)
        logger.debug(f"오디오 파일 재생 완료: {filename}")
        return True
    except Exception as e:
        logger.error(f"오디오 파일 재생 오류 ({filename}): {e}", exc_info=True)
        return False


def _find_audio_file_path(filename):
    """
    오디오 파일의 전체 경로 찾기

    Args:
        filename: 오디오 파일명 (예: "a_01.wav")

    Returns:
        str or None: 오디오 파일의 전체 경로 또는 None
    """
    current_file = os.path.abspath(__file__)
    utils_dir = os.path.dirname(current_file)
    ai_voice_dir = os.path.dirname(utils_dir)

    possible_paths = [
        # utils/audio (현재 디렉토리 기준)
        os.path.join(utils_dir, "audio", filename),
        # ai-voice/utils/audio
        os.path.join(ai_voice_dir, "utils", "audio", filename),
        # 절대 경로 (라즈베리파이 기본 경로)
        "/home/pi/chytonpide/src/ai-voice/utils/audio/" + filename,
        os.path.expanduser("~/chytonpide/src/ai-voice/utils/audio/" + filename),
    ]

    for path in possible_paths:
        abs_path = os.path.abspath(os.path.expanduser(path))
        if os.path.exists(abs_path):
            return abs_path

    return None


def load_audio_mapping():
    """
    오디오 매핑 JSON 파일 로드 및 오디오 파일 경로 미리 찾기

    Returns:
        dict: 사용자 발화 -> (오디오 파일 경로, 응답 텍스트) 매핑 딕셔너리
    """
    current_file = os.path.abspath(__file__)
    utils_dir = os.path.dirname(current_file)
    ai_voice_dir = os.path.dirname(utils_dir)

    mapping_paths = [
        # utils/audio_mapping.json (현재 디렉토리 기준)
        os.path.join(utils_dir, "audio_mapping.json"),
        # ai-voice/utils/audio_mapping.json
        os.path.join(ai_voice_dir, "utils", "audio_mapping.json"),
        # 절대 경로
        "/home/pi/chytonpide/src/ai-voice/utils/audio_mapping.json",
        os.path.expanduser("~/chytonpide/src/ai-voice/utils/audio_mapping.json"),
    ]

    for path in mapping_paths:
        abs_path = os.path.abspath(os.path.expanduser(path))
        if os.path.exists(abs_path):
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    mappings = data.get("audio_mappings", [])
                    # 사용자 발화 -> (오디오 파일 경로, 응답 텍스트) 매핑 생성
                    result = {}
                    for mapping in mappings:
                        audio_file = mapping.get("audio_file")
                        response_text = mapping.get("response_text", "")
                        user_inputs = mapping.get("user_input", [])

                        # 오디오 파일 경로 미리 찾기
                        audio_file_path = (
                            _find_audio_file_path(audio_file) if audio_file else None
                        )

                        if audio_file_path:
                            # 경로를 찾은 경우
                            for user_input in user_inputs:
                                # 소문자로 정규화하여 저장
                                result[user_input.lower().strip()] = (
                                    audio_file_path,
                                    response_text,
                                )
                            logger.debug(
                                f"오디오 파일 경로 찾음: {audio_file} -> {audio_file_path}"
                            )
                        else:
                            # 경로를 찾지 못한 경우
                            logger.warning(
                                f"오디오 파일을 찾을 수 없습니다: {audio_file}"
                            )
                            # 파일명만 저장 (나중에 찾을 수 있도록)
                            for user_input in user_inputs:
                                result[user_input.lower().strip()] = (
                                    audio_file,  # 파일명만 저장
                                    response_text,
                                )

                    logger.info(
                        f"오디오 매핑 로드 완료: {len(result)}개 항목 (경로 포함)"
                    )
                    return result
            except Exception as e:
                logger.warning(f"오디오 매핑 파일을 읽을 수 없습니다 ({abs_path}): {e}")
                continue

    logger.warning("오디오 매핑 파일을 찾을 수 없습니다.")
    return {}


def find_mapped_audio(user_text, audio_mapping):
    """
    사용자 발화에 매핑된 오디오 파일 찾기

    Args:
        user_text: 사용자 발화 텍스트
        audio_mapping: 오디오 매핑 딕셔너리 (파일 경로 또는 파일명 포함)

    Returns:
        tuple: (오디오 파일 경로, 응답 텍스트) 또는 (None, None)
    """
    if not user_text or not audio_mapping:
        return None, None

    user_text_lower = user_text.lower().strip()

    # 1. 정확한 매칭 시도
    if user_text_lower in audio_mapping:
        audio_path_or_file, response_text = audio_mapping[user_text_lower]

        # 전체 경로인지 확인
        if os.path.isabs(audio_path_or_file) and os.path.exists(audio_path_or_file):
            logger.debug(
                f"오디오 매핑 정확한 매칭: '{user_text}' -> {audio_path_or_file}"
            )
            return audio_path_or_file, response_text
        else:
            # 파일명만 있는 경우 경로 찾기 시도
            audio_file_path = _find_audio_file_path(audio_path_or_file)
            if audio_file_path:
                logger.debug(
                    f"오디오 매핑 정확한 매칭 (경로 찾음): '{user_text}' -> {audio_file_path}"
                )
                return audio_file_path, response_text

        # 경로를 찾지 못한 경우
        logger.warning(f"오디오 파일 경로를 찾을 수 없습니다: {audio_path_or_file}")
        return None, None

    # 2. 부분 매칭 시도 (매핑의 키가 사용자 발화에 포함되거나, 사용자 발화가 키에 포함되는 경우)
    for key, (audio_path_or_file, response_text) in audio_mapping.items():
        key_lower = key.lower().strip()
        # 매핑 키가 사용자 발화에 포함되거나, 사용자 발화가 매핑 키에 포함되는 경우
        if key_lower in user_text_lower or user_text_lower in key_lower:
            # 전체 경로인지 확인
            if os.path.isabs(audio_path_or_file) and os.path.exists(audio_path_or_file):
                logger.debug(
                    f"오디오 매핑 부분 매칭: '{user_text}' -> {audio_path_or_file} (키: '{key}')"
                )
                return audio_path_or_file, response_text
            else:
                # 파일명만 있는 경우 경로 찾기 시도
                audio_file_path = _find_audio_file_path(audio_path_or_file)
                if audio_file_path:
                    logger.debug(
                        f"오디오 매핑 부분 매칭 (경로 찾음): '{user_text}' -> {audio_file_path} (키: '{key}')"
                    )
                    return audio_file_path, response_text

    return None, None


def play_audio_file_by_path(file_path):
    """
    전체 경로로 오디오 파일 재생

    Args:
        file_path: 오디오 파일의 전체 경로

    Returns:
        bool: 재생 성공 여부
    """
    if not os.path.exists(file_path):
        logger.warning(f"오디오 파일을 찾을 수 없습니다: {file_path}")
        return False

    try:
        logger.info(f"오디오 파일 재생: {file_path}")
        # AIY Projects play_wav 또는 aplay 사용
        if HAS_AIY_AUDIO:
            play_wav(file_path)
        else:
            subprocess.run(["aplay", "-q", file_path], check=True)
        logger.debug(f"오디오 파일 재생 완료: {file_path}")
        return True
    except Exception as e:
        logger.error(f"오디오 파일 재생 오류 ({file_path}): {e}", exc_info=True)
        return False


def play_audio_file_async(filename_or_path):
    """
    오디오 파일을 비동기로 재생 (별도 스레드에서)

    Args:
        filename_or_path: 오디오 파일명 (예: "a_01.wav") 또는 전체 경로

    Returns:
        threading.Thread: 시작된 스레드 객체
    """

    def _audio_worker():
        try:
            # 전체 경로인지 파일명인지 확인
            if os.path.isabs(filename_or_path) and os.path.exists(filename_or_path):
                # 전체 경로인 경우
                play_audio_file_by_path(filename_or_path)
            else:
                # 파일명인 경우 (기존 로직)
                play_audio_file(filename_or_path)
        except Exception as e:
            logger.error(f"오디오 파일 비동기 재생 오류 ({filename_or_path}): {e}")

    thread = threading.Thread(target=_audio_worker, daemon=True)
    thread.start()
    logger.info(f"오디오 파일 비동기 재생 시작: {filename_or_path}")
    return thread
