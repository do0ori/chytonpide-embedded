# ESP32 AI Speaker 서버 테스트 가이드

## 서버 구조

이 서버는 **TCP 소켓 기반 바이너리 프로토콜**을 사용합니다. HTTP/HTTPS가 아닙니다.

### 포트

-   **33819**: TTS (Text-to-Speech) 서버

    -   ESP32 → 서버: 텍스트 전송 (MAC 주소 기반)
    -   서버 → ESP32: GPT 응답 텍스트 + 음성 파일 전송

-   **33823**: STT (Speech-to-Text) 서버
    -   ESP32 → 서버: 오디오 파일 전송
    -   서버 → ESP32: Whisper로 변환된 텍스트 반환

## 로컬 테스트 방법

### 1. 서버 실행

```bash
cd test/ai-speaker/server
python main.py
```

서버가 다음 포트에서 실행됩니다:

-   `0.0.0.0:33819` (TTS)
-   `0.0.0.0:33823` (STT)

### 2. 테스트 클라이언트 실행

#### STT 테스트 (오디오 → 텍스트)

```bash
python test_client.py stt input.wav
```

또는 특정 호스트/포트 지정:

```bash
python test_client.py stt input.wav localhost 33823
```

#### TTS 테스트 (텍스트 → 음성)

```bash
python test_client.py tts "안녕하세요 테스트입니다"
```

또는:

```bash
python test_client.py tts "안녕하세요" localhost 33819
```

## 외부에서 접근하기

현재 서버는 `0.0.0.0`으로 바인딩되어 있어 로컬 네트워크에서는 접근 가능합니다.

### 방법 1: 로컬 네트워크 (같은 WiFi)

**중요:** ESP32와 서버 PC가 **같은 WiFi 네트워크**에 연결되어 있어야 합니다.

#### PC의 로컬 IP 확인 방법

**Windows:**

```bash
# 명령 프롬프트(cmd) 또는 PowerShell에서
ipconfig

# 또는 간단하게
ipconfig | findstr "IPv4"
```

출력 예시:

```
무선 LAN 어댑터 Wi-Fi:
   IPv4 주소 . . . . . . . . : 192.168.0.200
```

**Linux/Mac:**

```bash
# Linux
hostname -I

# 또는
ifconfig | grep "inet "
```

**빠른 확인 스크립트:**

-   Windows: `check_ip.bat` 실행
-   Git Bash: `bash check_ip.sh` 실행

#### ESP32 코드에 IP 설정

PC에서 확인한 IP 주소를 ESP32 코드에 입력:

```cpp
const char* SERVER_IP = "192.168.0.200";  // 서버 실행 중인 PC의 로컬 IP
```

**예시:**

-   PC IP가 `192.168.1.100`이면 → `SERVER_IP = "192.168.1.100"`
-   PC IP가 `192.168.0.50`이면 → `SERVER_IP = "192.168.0.50"`

### 방법 2: 포트 포워딩 (공유기 설정)

라우터에서 포트 포워딩 설정:

-   외부 포트 → 내부 IP:33819
-   외부 포트 → 내부 IP:33823

### 방법 3: ngrok (임시 터널링)

```bash
# TTS 서버
ngrok tcp 33819

# STT 서버
ngrok tcp 33823
```

ngrok이 제공하는 주소를 사용하면 됩니다.

### 방법 4: Cloudflare Tunnel / Tailscale 등

영구적인 터널링 서비스를 사용할 수 있습니다.

## 프로토콜 구조

각 패킷은 1026바이트 고정:

-   헤더: 2바이트 (little endian)
-   데이터: 최대 1024바이트
-   패딩: 나머지 공간

### 시그널 코드

-   `3006`: MAC 주소 전송 (SIGNAL_MAC)
-   `3001`: 종료 신호 (SIGNAL_END)
-   `0-1024`: 실제 데이터 크기

## 주의사항

1. **HTTP API가 아닙니다** - 웹 브라우저나 curl로는 테스트 불가
2. **바이너리 프로토콜** - 데이터는 바이트 단위로 전송
3. **순서가 중요합니다** - MAC 주소 → 데이터 → 종료 신호 순서
4. **보안** - 현재 인증이나 암호화가 없습니다 (로컬 네트워크용)
