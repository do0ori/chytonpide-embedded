# Chipi 음성 어시스턴트

라즈베리파이 제로 WH에서 동작하는 음성 인식 및 음성 합성 기반 AI 어시스턴트

## 📋 개요

이 프로젝트는 라즈베리파이 제로 WH (Python 3.7.3, ARMv6)에서 동작하는 음성 어시스턴트입니다. 두 가지 실행 파일을 제공합니다:

-   **`main_azure.py`**: Azure Speech TTS + Azure Speech STT + Azure OpenAI
-   **`main_superton.py`**: SuperTone TTS + Azure Speech STT + Azure OpenAI (ChipiBrain 통합)

## 🏗️ 아키텍처

### 공통 구조

두 파일 모두 다음과 같은 흐름으로 동작합니다:

```
음성 입력 (마이크)
  → VAD (Voice Activity Detection)
    → STT (Speech-to-Text)
      → 트리거 단어 감지 (Wake Word)
        → LLM (Azure OpenAI GPT-4o)
          → TTS (Text-to-Speech)
            → 음성 출력 (스피커)
```

### 주요 구성 요소

#### 1. **VAD (Voice Activity Detection)**

-   **에너지 기반 음성 감지**: RMS 에너지 계산을 통한 음성/침묵 구분
-   **파라미터 조정**: 라즈베리파이 제로 WH 환경에 최적화
    -   `energy_threshold=0.005`: 더 민감한 음성 감지
    -   `silence_duration=0.8초`: 침묵 시간 감지
    -   `min_speech_duration=0.3초`: 최소 음성 길이

#### 2. **STT (Speech-to-Text)**

-   **Azure Speech REST API** 사용
-   ARMv6 아키텍처 호환을 위해 SDK 대신 REST API 직접 호출
-   엔드포인트 자동 변환: 구버전 형식 → 새 형식 (`https://{region}.stt.speech.microsoft.com`)

#### 3. **Wake Word & Sleep Mode**

-   **트리거 단어**: 환경 변수로 설정 가능 (기본값: "치피")
-   **Sleep Mode**: 트리거 단어가 없으면 응답하지 않음
-   **Wake Mode**: 트리거 단어 감지 후 모든 말에 응답
-   **자동 전환**: 일정 시간(기본 10초) 말이 없으면 Sleep Mode로 전환

#### 4. **LLM (Large Language Model)**

-   **Azure OpenAI GPT-4o** 사용
-   `main_superton.py`는 `ChipiBrain` 클래스를 통해 데이터베이스 연동 및 컨텍스트 관리

#### 5. **TTS (Text-to-Speech)**

-   **`main_azure.py`**: Azure Speech REST API TTS
-   **`main_superton.py`**: SuperTone API TTS (감정 톤 지원)

### 파일별 차이점

| 기능             | main_azure.py                    | main_superton.py                 |
| ---------------- | -------------------------------- | -------------------------------- |
| **TTS 엔진**     | Azure Speech REST API            | SuperTone API                    |
| **LLM 통합**     | 단일 파일 내 `AzureOpenAIClient` | `ChipiBrain` 클래스 (외부 모듈)  |
| **데이터베이스** | 없음                             | PostgreSQL 연동 (선택적)         |
| **감정 톤**      | 없음                             | 슬픈 키워드 감지 시 슬픈 톤 적용 |
| **구조**         | 모든 코드가 하나의 파일          | 모듈화된 구조                    |

## 🔧 라즈베리파이 제로 WH 호환성

### 1. **Python 버전 호환성 (3.7.3)**

#### 한글 출력 깨짐 방지

```python
# Python 3.7.3에서는 sys.stdout.reconfigure()가 없음
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

#### 환경 변수 로드

```python
# Python 3.7에서는 encoding 파라미터 미지원
try:
    load_dotenv(encoding="utf-8")
except TypeError:
    load_dotenv()  # encoding 파라미터 없이 호출
```

### 2. **ARMv6 아키텍처 호환성**

#### Azure Speech SDK 대신 REST API 사용

-   **문제**: Azure Speech SDK는 ARMv6를 지원하지 않음
-   **해결**: REST API를 직접 호출하여 플랫폼 독립적 구현

```python
# REST API 직접 호출
response = requests.post(
    f"{endpoint}/speech/recognition/conversation/cognitiveservices/v1",
    headers={
        "Ocp-Apim-Subscription-Key": api_key,
        "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000; channels=1",
    },
    params={"language": "ko-KR"},
    data=audio_data,
)
```

#### 오픈소스 라이브러리 버전 제한

-   `openai>=0.28.0,<1.0.0`: Python 3.7 호환 버전
-   `python-dotenv>=0.19.0,<1.0.0`: Python 3.7 호환 버전
-   `requests>=2.25.0,<3.0.0`: Python 3.7 호환 버전

### 3. **AIY Projects 모듈 활용**

#### 하드웨어 제어

-   **마이크/스피커**: `aiy.voice.audio` 모듈 사용
    -   `Recorder`: 마이크 입력
    -   `play_wav`: 스피커 출력
-   **LED 표시**: `aiy.board` 모듈 사용
    -   VAD 상태를 LED로 표시 (듣는 중: ON, 대기: OFF)

```python
# AIY Projects 모듈은 시스템에 이미 설치된 것을 사용
try:
    from aiy.voice.audio import AudioFormat, Recorder, play_wav
    from aiy.board import Board, Led
except ImportError:
    # 모듈이 없어도 계속 진행 (옵션 기능)
    pass
```

### 4. **경로 설정 및 Import 해결**

#### 동적 경로 설정

```python
# 현재 디렉토리와 상위 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
```

#### 다중 경로 Import 시도

```python
# 여러 경로에서 모듈 import 시도
try:
    from core.chipi_brain import ChipiBrain
except ImportError:
    try:
        # 상위 디렉토리에서 시도
        from src.core.chipi_brain import ChipiBrain
    except ImportError:
        # 최상위 디렉토리에서 시도
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(os.path.dirname(current_dir))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from core.chipi_brain import ChipiBrain
```

### 5. **데이터베이스 연결 안정성**

#### psycopg2 Import 실패 처리

```python
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except (ImportError, OSError):
    # libpq.so.5가 없어도 프로그램은 계속 실행
    HAS_PSYCOPG2 = False
    print("⚠️ 데이터베이스 기능을 사용할 수 없습니다.")
```

#### 연결 타임아웃 설정

```python
# 데이터베이스 연결 타임아웃 (5초)
self.conn = psycopg2.connect(
    ...,
    connect_timeout=5,
)
```

## 📦 설치 및 실행

### 필수 요구사항

-   **하드웨어**: 라즈베리파이 제로 WH
-   **OS**: Raspbian Buster 이상
-   **Python**: 3.7.3
-   **AIY Projects**: 시스템에 설치되어 있어야 함

### 패키지 설치

```bash
pip3 install -r requirements.txt
```

### 환경 변수 설정

`config/env.example` 파일을 참고해 `config/.env` 파일을 생성

### 실행

```bash
# Azure TTS 사용
python3 main_azure.py

# SuperTone TTS 사용
python3 main_superton.py
```

## 🎯 주요 기능

### 1. **Wake Word 감지**

-   트리거 단어를 말하면 Wake Mode로 전환
-   여러 트리거 단어 지원 (쉼표로 구분)

### 2. **Sleep/Wake Mode**

-   **Sleep Mode**: 트리거 단어가 없으면 응답하지 않음
-   **Wake Mode**: 트리거 단어 없이 모든 말에 응답
-   일정 시간 말이 없으면 자동으로 Sleep Mode로 전환

### 3. **LED 상태 표시** (AIY Projects Board 사용 시)

-   듣는 중: LED ON
-   대기 중: LED OFF

### 4. **감정 톤 지원** (main_superton.py만)

-   슬픈 키워드 감지 시 슬픈 톤으로 응답
-   피치 조정: 슬픈 톤일 때 -10

### 5. **데이터베이스 연동** (main_superton.py만)

-   사용자 정보 조회
-   센서 데이터 조회 (온도/습도)
-   식물 상태 판단

## 🔍 문제 해결

### STT 인식이 잘 안 될 때

1. **오디오 파일 크기 확인**: 로그에서 오디오 파일 크기와 길이 확인
2. **VAD 파라미터 조정**: `energy_threshold`, `silence_duration` 조정
3. **마이크 위치**: 마이크를 더 가까이 두거나 볼륨 조정

### 데이터베이스 연결 실패

-   `libpq.so.5` 오류: `sudo apt-get install libpq-dev` (Raspbian Buster의 경우 archive 저장소 사용)
-   연결 타임아웃: 방화벽 설정 확인, IP 화이트리스트 확인

### Import 오류

-   경로 문제: `sys.path`에 현재 디렉토리와 상위 디렉토리가 포함되어 있는지 확인
-   모듈 누락: `requirements.txt`의 패키지가 모두 설치되었는지 확인

## 📝 참고사항

-   **AIY Projects**: Google AIY Projects 보드와 마이크/스피커 보드가 필요합니다
-   **네트워크**: 인터넷 연결이 필요합니다 (Azure API 호출)
-   **성능**: 라즈베리파이 제로 WH는 성능이 제한적이므로 응답 시간이 다소 걸릴 수 있습니다

## 📄 라이선스

이 프로젝트는 교육 및 개인 사용 목적으로 제공됩니다.

### 서드파티 라이선스

-   **Azure Speech Services**: Microsoft Software License Terms
-   **SuperTone API**: SuperTone API Terms of Service
-   **AIY Projects**: Apache 2.0 License
