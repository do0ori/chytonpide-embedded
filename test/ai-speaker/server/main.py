import datetime
import re
import signal
import socket
import subprocess
import sys
import threading
import wave

import whisper
from esp32_tcp import ESP32TCPAudioRecv, ESPTCPAudioSend
from simple_gpt import JarvisMemoryManager
from text_to_wav import GoogleTextToWavConverter


class YoutubeAIspeakerAudioSender(ESPTCPAudioSend):
    def __init__(self, client_socket, client_address, work_list, lock):
        super().__init__(client_socket, client_address)
        self.work_list = work_list
        self.lock = lock
        self.GPT = JarvisMemoryManager()
        self.converter = GoogleTextToWavConverter()

    def start(self):
        try:
            signal, validData = self.recv_exact21024()
            if signal == self.SIGNAL_MAC:
                mac_str = "".join("{:02X}".format(b) for b in validData)
                filename = f"tts_{mac_str}.wav"

                print("전체", self.work_list)
                text_from_user = self.update_work_list(validData)
                print("해당입력문장", text_from_user[1])

                self.GPT.add_msg(text_from_user[1])
                result = self.GPT.wait_run("Terminal_AI")
                # result = "하이 방가방가"

                print("파싱전:", result)
                parsed_commands, cleaned_string = self.parse_terminal_string(result)
                print("대답파싱:", parsed_commands, cleaned_string)
                # 파싱된 명령어 실행
                for cmd in parsed_commands:
                    output, error = self.execute_command(cmd)
                    print("Executing command:", cmd)
                    print("Output:", output)
                    print("Error:", error)

                # 줄바꿈 문자 제거 및 비어있는 경우 처리
                cleaned_string = self.clean_and_check_string(cleaned_string)

                answer_bytes = cleaned_string.encode()
                self.send_21024(len(answer_bytes), answer_bytes)
                if self.converter.convert_to_wav(cleaned_string, filename):
                    print("음성파일 생성 성공")
                else:
                    print("음성파일 생성 실패")

                signal, validData = self.recv_exact21024()
                self.wav_file = wave.open(filename, "rb")
                while True:
                    frames_to_send = self.wav_file.readframes(self.FRAME_SIZE)
                    if not frames_to_send:
                        self.send_21024(self.SIGNAL_END, b"")
                        print("전송종료")
                        break
                    self.send_21024(len(frames_to_send), frames_to_send)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.wav_file.close()
            self.close()

    def execute_command(self, command):
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return result.stdout.decode(), result.stderr.decode()
        except subprocess.CalledProcessError as e:
            return e.stdout.decode(), e.stderr.decode()

    def parse_terminal_string(self, input_string):
        pattern = r'\[터미널\]\["(.*?)"\]'
        parsed_contents = re.findall(pattern, input_string)
        # 입력 문자열에서 파싱된 부분 제거
        cleaned_string = re.sub(pattern, "", input_string)
        return parsed_contents, cleaned_string

    def clean_and_check_string(self, string):
        # 줄바꿈 문자 제거
        cleaned_string = string.replace("\n", "").strip()
        # 문자열이 비어 있거나 공백만 있는 경우 "..."로 대체
        if not cleaned_string:
            cleaned_string = "..."
        return cleaned_string

    def update_work_list(self, macaddress, text=None):

        current_time = datetime.datetime.now()

        with self.lock:
            # 2분 이상 지난 항목 제거
            self.work_list[:] = [
                item
                for item in self.work_list
                if (current_time - item[2]).seconds <= 120
            ]

            if text is not None:
                # 텍스트가 주어진 경우: 덮어쓰기 또는 추가
                for item in self.work_list:
                    if item[0] == macaddress:
                        item[1] = text
                        item[2] = current_time
                        return
                self.work_list.append([macaddress, text, current_time])
            else:
                # 텍스트가 주어지지 않은 경우: 해당 인덱스 찾아서 pop 및 반환
                for i, item in enumerate(self.work_list):
                    if item[0] == macaddress:
                        return self.work_list.pop(i)
            return None  # 맥주소가 리스트에 없는 경우


class YoutubeAIspeakerAudioReciver(ESP32TCPAudioRecv):
    def __init__(self, client_socket, client_address, work_list, lock):
        super().__init__(client_socket, client_address)
        self.work_list = work_list
        self.lock = lock
        self.model = whisper.load_model("base")

    def start(self):
        global trynum
        try:
            macaddress = ""
            while True:
                signal, validData = self.recv_exact21024()
                if signal == self.SIGNAL_MAC:
                    self.mkWaveFile(validData)
                    macaddress = validData
                if signal == self.SIGNAL_END:
                    self.wav_file.close()
                    break
                if 0 < signal <= 1024:
                    amplified_data = self.amplify_audio_data(validData, 10)
                    self.wav_file.writeframes(amplified_data)

            # 위스퍼 문자열생성
            result = self.model.transcribe("ECDA3B45E7A0.wav")
            print(result["text"])
            print(self.work_list)

            self.update_work_list(macaddress, result["text"])
            self.send_21024(len(result["text"].encode()), result["text"].encode())

        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.close()

    def update_work_list(self, macaddress, text=None):

        current_time = datetime.datetime.now()

        with self.lock:
            # 2분 이상 지난 항목 제거
            self.work_list[:] = [
                item
                for item in self.work_list
                if (current_time - item[2]).seconds <= 120
            ]

            if text is not None:
                # 텍스트가 주어진 경우: 덮어쓰기 또는 추가
                for item in self.work_list:
                    if item[0] == macaddress:
                        item[1] = text
                        item[2] = current_time
                        return
                self.work_list.append([macaddress, text, current_time])
            else:
                # 텍스트가 주어지지 않은 경우: 해당 인덱스 찾아서 pop 및 반환
                for i, item in enumerate(self.work_list):
                    if item[0] == macaddress:
                        return self.work_list.pop(i)
            return None  # 맥주소가 리스트에 없는 경우


class YoutubeAISpeakerTCPServer:

    def __init__(self, host, port, audio_class, work_list, lock):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1.0)  # 1초 timeout으로 Ctrl+C 반응성 향상
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.audio_class = audio_class
        self.work_list = work_list
        self.lock = lock
        self.running = True

    def handle_client(self, client_socket, client_address):
        audio_instance = self.audio_class(
            client_socket, client_address, self.work_list, self.lock
        )
        audio_instance.start()

    def start(self):
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client, args=(client_socket, client_address)
                )
                client_thread.daemon = True  # 데몬 스레드로 설정
                client_thread.start()
            except socket.timeout:
                # timeout은 정상적인 상황 (Ctrl+C 체크를 위해)
                continue
            except OSError:
                # 소켓이 닫혔을 때
                break

    def stop(self):
        """서버 종료"""
        self.running = False
        try:
            self.server_socket.close()
        except Exception:
            pass


if __name__ == "__main__":
    work_list: list = []
    list_lock = threading.Lock()

    server1 = YoutubeAISpeakerTCPServer(
        "0.0.0.0", 33819, YoutubeAIspeakerAudioSender, work_list, list_lock
    )
    server2 = YoutubeAISpeakerTCPServer(
        "0.0.0.0", 33823, YoutubeAIspeakerAudioReciver, work_list, list_lock
    )

    server1_thread = threading.Thread(target=server1.start)
    server1_thread.daemon = True
    server1_thread.start()
    print("server1 시작")

    server2_thread = threading.Thread(target=server2.start)
    server2_thread.daemon = True
    server2_thread.start()
    print("server2 시작")

    def signal_handler(sig, frame):
        """시그널 핸들러 (Ctrl+C 처리)"""
        print("\n서버 종료 중...")
        server1.stop()
        server2.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 메인 스레드가 종료되지 않도록 대기
        while True:
            server1_thread.join(timeout=1)
            server2_thread.join(timeout=1)
            if not server1_thread.is_alive() and not server2_thread.is_alive():
                break
    except KeyboardInterrupt:
        signal_handler(None, None)
