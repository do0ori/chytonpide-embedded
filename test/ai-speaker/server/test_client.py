"""
ESP32 AI Speaker 서버 테스트 클라이언트

이 스크립트는 서버의 TCP 프로토콜을 테스트하기 위한 클라이언트입니다.
"""

import os
import socket
import sys
import tempfile
import wave

try:
    from pydub import AudioSegment

    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    print("경고: pydub이 설치되지 않았습니다. 오디오 변환이 제한적일 수 있습니다.")
    print("설치: pip install pydub")


class ESP32TCPClient:
    SIGNAL_NONE = 3000
    SIGNAL_END = 3001
    SIGNAL_MAC = 3006

    TOTAL_SIZE = 1026
    PACKET_SIZE = 1024
    HEADER_SIZE = 2

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        """서버에 연결"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((self.host, self.port))
            print(f"✓ {self.host}:{self.port} 연결 성공")
            return True
        except Exception as e:
            print(f"✗ 연결 실패: {e}")
            return False

    def send_21024(self, header, data):
        """1026바이트 패킷 전송"""
        if not isinstance(header, int):
            raise TypeError("header must be an integer")
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")

        header_bytes = header.to_bytes(2, "little")
        padding = b"\x00" * (self.PACKET_SIZE - len(data))
        packet = header_bytes + data + padding
        self.socket.sendall(packet)
        print(f"  → 전송: header={header}, data_len={len(data)}")

    def recv_exact21024(self):
        """1026바이트 패킷 수신"""
        data = bytearray()
        while len(data) < self.TOTAL_SIZE:
            packet = self.socket.recv(self.TOTAL_SIZE - len(data))
            if not packet:
                return None, None
            data.extend(packet)

        signal_data = int.from_bytes(data[: self.HEADER_SIZE], "little")
        if signal_data >= self.SIGNAL_NONE:
            validData = data[
                self.HEADER_SIZE : self.HEADER_SIZE + signal_data - self.SIGNAL_NONE
            ]
        else:
            validData = data[self.HEADER_SIZE : self.HEADER_SIZE + signal_data]

        print(f"  ← 수신: header={signal_data}, data_len={len(validData)}")
        return signal_data, validData

    def close(self):
        """연결 종료"""
        if self.socket:
            self.socket.close()
            print("연결 종료")


def test_stt_server(host, port, wav_file=None):
    """
    STT 서버 (33823) 테스트
    오디오 파일을 서버로 전송하고 텍스트 결과를 받음
    """
    print("\n" + "=" * 50)
    print("STT 서버 테스트 (Port 33823)")
    print("=" * 50)

    client = ESP32TCPClient(host, port)
    if not client.connect():
        return

    try:
        # MAC 주소 전송 (시그널 3006)
        mac_address = b"\xec\xda\x3b\x45\xe7\xa0"  # 예제 MAC 주소
        print(f"\n1. MAC 주소 전송: {mac_address.hex()}")
        client.send_21024(client.SIGNAL_MAC, mac_address)

        # 오디오 파일 전송
        if wav_file:
            print(f"\n2. 오디오 파일 전송: {wav_file}")

            converted_file = None
            should_delete = False

            # pydub로 변환 (가능한 경우)
            if HAS_PYDUB:
                try:
                    audio = AudioSegment.from_wav(wav_file)
                    print(f"   원본: {audio.frame_rate}Hz, {audio.channels}ch")

                    # 16000Hz, mono로 변환
                    audio = audio.set_frame_rate(16000)
                    audio = audio.set_channels(1)

                    # 임시 파일로 저장
                    with tempfile.NamedTemporaryFile(
                        suffix=".wav", delete=False
                    ) as tmp:
                        converted_file = tmp.name
                        audio.export(converted_file, format="wav")

                    should_delete = True
                    print("   변환: 16000Hz, 1ch")
                except Exception as e:
                    print(f"   경고: pydub 변환 실패, 원본 사용: {e}")

            file_to_use = converted_file if converted_file else wav_file

            try:
                with wave.open(file_to_use, "rb") as wf:
                    rate = wf.getframerate()
                    channels = wf.getnchannels()
                    width = wf.getsampwidth()
                    print(f"   최종: {rate}Hz, {channels}ch, {width*8}bit")

                    # 서버는 16000Hz, mono, 16-bit 기대
                    if rate != 16000 or channels != 1 or width != 2:
                        print(
                            "   ⚠️  경고: 파일 형식이 서버 요구사항과 다를 수 있습니다."
                        )
                        print("      요구: 16000Hz, 1ch, 16bit")

                    # 16-bit mono = 2바이트/샘플
                    # 한 번에 최대 512 샘플 = 1024 바이트
                    chunk_samples = 512

                    while True:
                        frames = wf.readframes(chunk_samples)
                        if not frames:
                            break

                        # 최대 1024바이트로 제한
                        if len(frames) > 1024:
                            frames = frames[:1024]

                        if len(frames) > 0:
                            client.send_21024(len(frames), frames)
            finally:
                # 임시 파일 삭제
                if should_delete and converted_file and os.path.exists(converted_file):
                    try:
                        os.unlink(converted_file)
                    except Exception:
                        pass

            # 종료 신호 전송
            print("\n3. 종료 신호 전송")
            client.send_21024(client.SIGNAL_END, b"")

            # 응답 수신 (텍스트)
            print("\n4. 서버 응답 대기...")
            signal, data = client.recv_exact21024()
            if signal and data:
                text = data.decode("utf-8", errors="ignore").rstrip("\x00")
                print(f"\n✓ 변환된 텍스트: {text}")
        else:
            print("\n오디오 파일이 제공되지 않았습니다.")
            print("사용법: python test_client.py stt <wav_file>")

    except Exception as e:
        print(f"\n✗ 에러 발생: {e}")
        import traceback

        traceback.print_exc()
    finally:
        client.close()


def test_tts_server(host, port, text="안녕하세요 테스트입니다"):
    """
    TTS 서버 (33819) 테스트
    텍스트를 서버로 전송하고 음성 파일을 받음
    """
    print("\n" + "=" * 50)
    print("TTS 서버 테스트 (Port 33819)")
    print("=" * 50)

    client = ESP32TCPClient(host, port)
    if not client.connect():
        return

    try:
        # MAC 주소 전송
        mac_address = b"\xec\xda\x3b\x45\xe7\xa0"
        print(f"\n1. MAC 주소 전송: {mac_address.hex()}")
        client.send_21024(client.SIGNAL_MAC, mac_address)

        # 서버에서 텍스트 응답 대기 (work_list에서 가져옴)
        print("\n2. 서버 응답 대기 (텍스트)...")
        signal, data = client.recv_exact21024()
        if signal and data:
            response_text = data.decode("utf-8", errors="ignore").rstrip("\x00")
            print(f"   응답: {response_text}")

        # 준비 완료 신호 전송 (더미 데이터)
        print("\n3. 준비 완료 신호 전송")
        client.send_21024(client.PACKET_SIZE, b"\x00" * client.PACKET_SIZE)

        # 음성 파일 수신
        print("\n4. 음성 파일 수신 중...")
        output_file = "received_audio.wav"

        # WAV 파일 초기화
        with wave.open(output_file, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)

            audio_received = False
            while True:
                signal, data = client.recv_exact21024()
                if not signal:
                    break

                if signal == client.SIGNAL_END:
                    print("\n✓ 음성 파일 수신 완료")
                    break
                elif 0 < signal <= 1024:
                    # 오디오 데이터
                    if not audio_received:
                        print("   오디오 데이터 수신 중...")
                        audio_received = True
                    wf.writeframes(data[:signal])

        if audio_received:
            print(f"\n✓ 저장된 파일: {output_file}")
        else:
            print("\n✗ 오디오 데이터를 받지 못했습니다.")

    except Exception as e:
        print(f"\n✗ 에러 발생: {e}")
        import traceback

        traceback.print_exc()
    finally:
        client.close()


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법:")
        print("  STT 테스트: python test_client.py stt <wav_file> [host] [port]")
        print("  TTS 테스트: python test_client.py tts [text] [host] [port]")
        print("\n예시:")
        print("  python test_client.py stt test.wav")
        print("  python test_client.py stt test.wav 192.168.0.200 33823")
        print("  python test_client.py tts '안녕하세요'")
        print("  python test_client.py tts '안녕하세요' 192.168.0.200 33819")
        return

    mode = sys.argv[1].lower()
    host = sys.argv[3] if len(sys.argv) > 3 else "localhost"

    if mode == "stt":
        wav_file = sys.argv[2] if len(sys.argv) > 2 else None
        port = int(sys.argv[4]) if len(sys.argv) > 4 else 33823
        test_stt_server(host, port, wav_file)

    elif mode == "tts":
        text = sys.argv[2] if len(sys.argv) > 2 else "안녕하세요 테스트입니다"
        port = int(sys.argv[4]) if len(sys.argv) > 4 else 33819
        test_tts_server(host, port, text)

    else:
        print(f"알 수 없는 모드: {mode}")
        print("사용 가능한 모드: stt, tts")


if __name__ == "__main__":
    main()
