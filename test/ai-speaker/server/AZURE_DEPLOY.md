# Azure VM 배포 가이드

## 1. Azure VM 생성

### 필수 설정

1. **운영 체제**: Ubuntu 22.04 LTS (또는 원하는 Linux)
2. **VM 크기**: 
   - 최소: Standard_B2s (2 vCPU, 4GB RAM) - Whisper base 모델용
   - 권장: Standard_B4ms (4 vCPU, 16GB RAM) - 더 빠른 처리
3. **공개 IP 주소**: **예**로 설정 (필수!)
4. **네트워크 보안 그룹**: 포트 열기 필요

### 네트워크 보안 그룹 (NSG) 설정

다음 포트를 열어야 합니다:

| 포트 | 프로토콜 | 설명 |
|------|----------|------|
| 33819 | TCP | TTS 서버 |
| 33823 | TCP | STT 서버 |
| 22 | TCP | SSH (관리용) |

Azure Portal에서:
1. VM → 네트워킹 → 인바운드 포트 규칙 추가
2. 각 포트에 대해 추가:
   - 이름: `tts-server` (포트 33819)
   - 우선순위: 1000
   - 소스: 모든 소스 (`*`)
   - 대상: 모든 대상
   - 서비스: 사용자 지정
   - 프로토콜: TCP
   - 포트 범위: 33819

같은 방식으로 33823 포트도 추가

## 2. 서버 설치

### VM에 SSH 접속

```bash
ssh azureuser@<VM_PUBLIC_IP>
```

### 필수 패키지 설치

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 설치
sudo apt install python3 python3-pip python3-venv -y

# 오디오 라이브러리 (Whisper용)
sudo apt install ffmpeg -y

# Git 설치
sudo apt install git -y
```

### 프로젝트 클론 및 설정

```bash
# 홈 디렉토리로 이동
cd ~

# 프로젝트 디렉토리 생성
mkdir ai-speaker-server
cd ai-speaker-server

# 코드 업로드 (로컬에서)
# 방법 1: Git 사용
git clone <your-repo> .

# 방법 2: SCP로 파일 전송
# 로컬 PC에서:
# scp -r test/ai-speaker/server/* azureuser@<VM_IP>:~/ai-speaker-server/

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# Whisper 모델 다운로드 (처음 실행 시 자동)
python -c "import whisper; whisper.load_model('base')"
```

## 3. 서버 실행

### 방법 1: 직접 실행 (테스트용)

```bash
cd ~/ai-speaker-server
source venv/bin/activate
python main.py
```

### 방법 2: systemd 서비스 (프로덕션)

서비스 파일 생성:
```bash
sudo nano /etc/systemd/system/ai-speaker.service
```

다음 내용 입력:
```ini
[Unit]
Description=AI Speaker Server
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/ai-speaker-server
Environment="PATH=/home/azureuser/ai-speaker-server/venv/bin"
ExecStart=/home/azureuser/ai-speaker-server/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

서비스 시작:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-speaker
sudo systemctl start ai-speaker

# 상태 확인
sudo systemctl status ai-speaker

# 로그 확인
journalctl -u ai-speaker -f
```

## 4. ESP32 코드 수정

Azure VM의 공개 IP 주소를 사용:

```cpp
const char* SERVER_IP = "20.123.45.67";  // Azure VM의 공개 IP 주소
const int   STT_PORT  = 33819;
const int   TTS_PORT  = 33823;
```

## 5. 공개 IP 주소 확인

Azure Portal에서:
1. VM → 개요 → 공용 IP 주소

또는 VM에서:
```bash
curl ifconfig.me
```

## 6. 보안 고려사항

⚠️ **현재 서버는 보안이 없습니다!**

### 권장 보안 조치:

1. **방화벽 추가**
   - 특정 IP만 허용 (예: ESP32의 고정 IP)
   - 또는 VPN 사용

2. **인증 추가**
   - MAC 주소 인증
   - API 키/토큰 인증

3. **TLS/SSL 암호화**
   - TCP 소켓을 TLS로 래핑

4. **Rate Limiting**
   - DDoS 공격 방지

## 7. 비용 추정

Azure VM 가격 (2024 기준, 한국 리전):
- Standard_B2s: 약 $30-40/월
- Standard_B4ms: 약 $70-90/월

실시간 가격 확인: https://azure.microsoft.com/pricing/details/virtual-machines/

## 8. 대안: Azure Container Instances

더 간단한 배포 방법:

```bash
# Dockerfile 생성
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 33819 33823

CMD ["python", "main.py"]
```

```bash
# Azure Container Registry에 푸시
az acr build --registry <your-registry> --image ai-speaker:latest .

# Container Instance 실행
az container create \
  --resource-group <your-rg> \
  --name ai-speaker \
  --image <your-registry>.azurecr.io/ai-speaker:latest \
  --cpu 2 \
  --memory 4 \
  --ports 33819 33823 \
  --ip-address Public \
  --dns-name-label <unique-name>
```

## 9. 트러블슈팅

### 연결 안 됨
1. NSG 포트 규칙 확인
2. VM 방화벽 확인: `sudo ufw status`
3. 서버 로그 확인: `journalctl -u ai-speaker -n 50`

### 성능 문제
1. VM 크기 업그레이드
2. Whisper 모델 크기 조정 (base → small)

### IP 변경
- 공개 IP를 고정 IP로 설정 (추가 비용)


