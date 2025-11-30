import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

# openai 버전에 따라 다른 import (Python 3.7.3 호환)
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

# 상대 경로로 import 시도 (servo 패키지처럼)
# psycopg2가 없어도 계속 진행할 수 있도록 try-except로 처리
DatabaseManager = None
try:
    from database.db_manager import DatabaseManager
except (ImportError, Exception):
    try:
        # 현재 디렉토리 기준으로 시도
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from database.db_manager import DatabaseManager
    except (ImportError, Exception):
        try:
            # 상위 디렉토리 기준으로 시도
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(os.path.dirname(current_dir))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            from database.db_manager import DatabaseManager
        except (ImportError, OSError, Exception) as e:
            print(f"⚠️  DatabaseManager를 import할 수 없습니다: {e}")
            print("⚠️  데이터베이스 기능 없이 계속 진행합니다.")
            DatabaseManager = None

class ChipiBrain:
    def __init__(self):
        # Python 3.7.3 호환: encoding 파라미터는 Python 3.9+에서만 지원
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'config', '.env')
        try:
            if os.path.exists(config_path):
                load_dotenv(config_path, encoding='utf-8')
            else:
                load_dotenv(encoding='utf-8')
        except TypeError:
            # encoding 파라미터가 지원되지 않는 경우 (Python 3.7)
            if os.path.exists(config_path):
                load_dotenv(config_path)
            else:
                load_dotenv()

        # ==========================================
        # 1. Azure OpenAI 설정
        # ==========================================
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        if not azure_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT가 설정되지 않았습니다.")

        # Azure OpenAI 클라이언트 초기화 (openai 버전에 따라 다르게 처리)
        if HAS_AZURE_OPENAI_CLASS:
            # openai 1.x 버전
            if azure_api_key:
                # API 키 인증
                self.client = AzureOpenAI(
                    api_version=api_version,
                    azure_endpoint=azure_endpoint,
                    api_key=azure_api_key,
                )
            else:
                # 암호 없는 인증 (Managed Identity 등)
                try:
                    from azure.identity import DefaultAzureCredential
                    credential = DefaultAzureCredential()
                    self.client = AzureOpenAI(
                        api_version=api_version,
                        azure_endpoint=azure_endpoint,
                        azure_ad_token_provider=lambda: credential.get_token(
                            "https://cognitiveservices.azure.com/.default"
                        ).token,
                    )
                except ImportError:
                    raise ValueError("azure-identity 패키지가 필요합니다.")
        else:
            # openai 0.28.x 버전
            if not azure_api_key:
                raise ValueError("openai 0.28.x에서는 API 키가 필요합니다.")
            openai.api_type = "azure"
            openai.api_base = azure_endpoint
            openai.api_key = azure_api_key
            openai.api_version = api_version
            self.client = None  # 0.28.x에서는 클라이언트 객체가 없음

        self.deployment_name = deployment_name
        self.messages = self.load_memory()

        # ==========================================
        # 3. 데이터베이스 초기화
        # ==========================================
        print("   데이터베이스 연결 시도 중...", end=" ", flush=True)
        try:
            # DatabaseManager가 없거나 import 실패한 경우 None으로 설정
            if DatabaseManager is None:
                print("건너뜀 (DatabaseManager 없음)", flush=True)
                self.db_manager = None
            else:
                self.db_manager = DatabaseManager()
                # connect_timeout 파라미터로 타임아웃 설정 (5초)
                self.db_manager.connect(timeout=5)
                print("✅ 완료", flush=True)
        except (ImportError, TimeoutError, Exception) as e:
            # 오류 메시지는 간단하게만 표시
            error_str = str(e)
            if "Connection timed out" in error_str or "could not connect" in error_str:
                print("❌ 실패 (연결 타임아웃)", flush=True)
            elif "psycopg2" in error_str.lower() or "libpq" in error_str.lower():
                print("❌ 실패 (psycopg2 오류)", flush=True)
            else:
                # 오류 메시지가 너무 길면 잘라서 표시
                short_msg = error_str[:60] + "..." if len(error_str) > 60 else error_str
                print(f"❌ 실패 ({short_msg})", flush=True)
            self.db_manager = None

        # ==========================================
        # 2. 시스템 프롬프트 설정 (.env에서 읽음)
        # ==========================================
        self.system_prompts = {
            "jarvis_4": os.environ.get("SYSTEM_PROMPT_JARVIS_4"),
            "jarvis_3.5": os.environ.get("SYSTEM_PROMPT_JARVIS_35"),
            "Terminal_AI": os.environ.get("SYSTEM_PROMPT_TERMINAL"),
            "chipi": os.environ.get("SYSTEM_PROMPT_CHIPI"),
        }

    def load_memory(self):
        """대화 히스토리 로드"""
        history_file = "memory.txt"
        messages = []

        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if ":" in line:
                            # 첫 번째 콜론만 분리 (내용에 콜론이 있을 수 있으므로)
                            role, content = line.split(":", 1)
                            messages.append(
                                {"role": role.strip(), "content": content.strip()}
                            )
            except Exception as e:
                print(f"히스토리 로드 오류: {e}")

        return messages

    def save_memory(self):
        """대화 히스토리 저장"""
        history_file = "memory.txt"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                for msg in self.messages:
                    # 시스템 메시지는 저장하지 않음 (매번 설정에 따라 달라질 수 있으므로)
                    if msg.get("role") != "system":
                        # 줄바꿈 문자가 있을 경우 파일 형식이 깨질 수 있으므로 replace 처리 등을 고려할 수 있음
                        clean_content = msg['content'].replace("\n", " ") 
                        f.write(f"{msg['role']}:{clean_content}\n")
        except Exception as e:
            print(f"히스토리 저장 오류: {e}")

    def create_new_memory(self):
        """새 대화 히스토리 생성 (초기화)"""
        self.messages = []
        # 파일을 비움
        with open("memory.txt", "w", encoding="utf-8") as f:
            pass

    def add_msg(self, msg):
        """사용자 메시지 추가"""
        self.messages.append({"role": "user", "content": msg})

    def get_run_id(self, ai_name):
        """호환성을 위한 메서드"""
        return ai_name

    def wait_run(self, ai_name, device_serial=None):
        """AI 응답 생성 및 반환

        Args:
            ai_name: AI 페르소나 이름 (chipi, jarvis_4 등)
            device_serial: 디바이스 시리얼 (DB 컨텍스트 추가용, 선택사항)
        """
        # 0. 최근 사용자 메시지 가져오기
        last_user_msg = ""
        for msg in reversed(self.messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "").lower()
                break

        # 0-1. 특정 상황 감지 및 시스템 프롬프트 수정 (LLM이 다양하게 응답하도록)
        user_name = None
        special_context = ""

        if device_serial and self.db_manager:
            user_info = self.db_manager.get_user_by_device_serial(device_serial)
            user_name = user_info.get('name') if user_info else None

        # 물 주기 표현 감지
        if any(k in last_user_msg for k in ["물 줄게", "물 줘", "물을 줄게", "물을 줘"]):
            special_context += "## 특별 상황: user가 물을 주려고 해!\n감사를 표현하고 user의 건강을 먼저 생각해줘. 다양하게 응답해.\n"

        # 온도 질문 감지 ("온도 어때?", "지금 온도?" 등)
        has_temp_keyword = any(k in last_user_msg for k in ["온도", "따뜻", "더워", "추워"])
        if has_temp_keyword and "습도" not in last_user_msg:
            if device_serial and self.db_manager:
                sensor_data = self.db_manager.get_sensor_data_by_serial(device_serial)
                if sensor_data and sensor_data.get('temperature') is not None:
                    temp = sensor_data.get('temperature')
                    special_context += f"## 특별 상황: user가 온도를 묻고 있어!\n현재 온도는 {temp}도야. 이 정보를 바탕으로 다양하게 응답해.\n"

        # 습도 질문 감지 ("습도 어때?", "지금 습도?" 등)
        has_humidity_keyword = any(k in last_user_msg for k in ["습도", "건조", "말라"])
        if has_humidity_keyword and "온도" not in last_user_msg:
            if device_serial and self.db_manager:
                sensor_data = self.db_manager.get_sensor_data_by_serial(device_serial)
                if sensor_data and sensor_data.get('humidity') is not None:
                    humidity = sensor_data.get('humidity')
                    special_context += f"## 특별 상황: user가 습도를 묻고 있어!\n현재 습도는 {humidity}%야. 이 정보를 바탕으로 다양하게 응답해.\n"

        # 1. 선택된 AI의 시스템 프롬프트 가져오기
        system_prompt = self.system_prompts.get(
            ai_name, "You are a helpful assistant. Respond in Korean."
        )

        # 2. DB 컨텍스트 추가 (device_serial이 있을 경우)
        db_context = ""
        if device_serial and self.db_manager:
            # 온도 또는 습도만 묻는지 확인
            has_temp_keyword = any(k in last_user_msg for k in ["온도", "따뜻", "더워", "추워"])
            has_humidity_keyword = any(k in last_user_msg for k in ["습도", "건조", "말라"])

            db_context, user_name = self.db_manager.build_context(device_serial,
                                                                    only_temperature=has_temp_keyword and not has_humidity_keyword,
                                                                    only_humidity=has_humidity_keyword and not has_temp_keyword)

        # 최종 시스템 프롬프트 (DB 정보 포함)
        final_system_prompt = system_prompt

        # 사용자 이름으로 "user" 치환 (없으면 "user" 유지)
        if user_name:
            final_system_prompt = final_system_prompt.replace("user", user_name)
            print(f"📝 사용자 호칭: {user_name}")
        else:
            print(f"📝 사용자 호칭: user (기본값)")

        if db_context:
            final_system_prompt += f"\n\n## 사용자 컨텍스트\n{db_context}"
            print(f"📝 DB 컨텍스트 추가됨 (길이: {len(db_context)}자)")
        else:
            print(f"⚠️  DB 컨텍스트 없음")

        # special_context 추가 (특별 상황 처리)
        if special_context:
            final_system_prompt += f"\n\n{special_context}"
            print(f"📝 특별 상황 감지됨")
        else:
            # special_context가 없으면 일반 대화 모드 강조
            final_system_prompt += "\n\n## 일반 대화 모드\nuser와 자연스럽게 대화해. 친근하게 질문하고 관심 보여줘."
            print(f"📝 일반 대화 모드")

        # 3. 시스템 메시지 처리
        # 현재 메시지 목록에 시스템 메시지가 없거나, 다른 페르소나의 메시지일 수 있으므로
        # 가장 첫 번째 메시지가 system인지 확인하고 교체하거나 추가합니다.
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0] = {"role": "system", "content": final_system_prompt}
        else:
            self.messages.insert(0, {"role": "system", "content": final_system_prompt})

        try:
            print(f"📤 API 요청 중... (메시지 개수: {len(self.messages)})")
            
            if HAS_AZURE_OPENAI_CLASS:
                # openai 1.x 버전
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=self.messages,
                    max_tokens=100,
                    temperature=0.7, # 치피의 감성적인 대화를 위해 약간 높임
                    top_p=1.0,
                )

                print(f"📥 API 응답 받음:")
                print(f"   - choices 개수: {len(response.choices)}")
                print(f"   - finish_reason: {response.choices[0].finish_reason}")

                # 콘텐츠 필터 체크
                if hasattr(response.choices[0], 'content_filter_results') and response.choices[0].content_filter_results:
                    print(f"   - content_filter_results: {response.choices[0].content_filter_results}")

                assistant_message = response.choices[0].message.content
            else:
                # openai 0.28.x 버전
                response = openai.ChatCompletion.create(
                    engine=self.deployment_name,
                    messages=self.messages,
                    max_tokens=100,
                    temperature=0.7,
                    top_p=1.0,
                )

                print(f"📥 API 응답 받음:")
                print(f"   - choices 개수: {len(response['choices'])}")
                print(f"   - finish_reason: {response['choices'][0]['finish_reason']}")

                assistant_message = response["choices"][0]["message"]["content"]
            
            print(f"✓ 응답 메시지: {assistant_message}")

            # 응답이 None인 경우 처리
            if assistant_message is None:
                print("⚠️  응답이 None입니다! (content 값이 비어있음)")
                if response.choices[0].finish_reason == 'content_filter':
                    print("   → 원인: Azure 콘텐츠 필터 (안전 정책 위반)")
                print(f"   전체 message 객체: {response.choices[0].message}")
                assistant_message = "어, 지금은 잘 모르겠어. 잠시만 기다려줄래?"

            # 응답 추가 및 저장
            self.messages.append({"role": "assistant", "content": assistant_message})
            self.save_memory()

            return assistant_message

        except Exception as e:
            error_msg = "어, 뭔가 잘못됐나봐. 잠시만 기다려줄래?"
            print(f"❌ 응답 생성 오류: {e}")
            print(f"❌ 최종 시스템 프롬프트:\n{final_system_prompt}\n")
            print(f"❌ 메시지 목록:\n{self.messages}\n")
            import traceback
            traceback.print_exc()
            return error_msg

    # def _generate_continuation(self, ai_name, device_serial, system_prompt):
    #     """대화 이어가기용 내부 메서드 (후속 질문/제안 생성)
    #     [대화 이어가기는 system prompt에 포함되어 자동으로 동작함]
    #
    #     Args:
    #         ai_name: AI 페르소나 이름
    #         device_serial: 디바이스 시리얼
    #         system_prompt: 현재 시스템 프롬프트
    #
    #     Returns:
    #         str: 후속 질문/제안
    #     """
    #     # 대화 이어가기 지시 추가
    #     continuation_system_prompt = system_prompt + "\n\n## 중요: 대화 이어가기\n당신의 마지막 응답 다음에 후속 질문이나 따뜻한 제안을 간단하게 추가해줘. 20단어 정도의 짧은 문장으로. 사용자가 대화를 계속하도록 자연스럽게 유도해줘."
    #
    #     # 임시 메시지 목록 생성 (원본은 보존)
    #     temp_messages = self.messages.copy()
    #
    #     # 시스템 메시지 업데이트
    #     if temp_messages and temp_messages[0].get("role") == "system":
    #         temp_messages[0] = {"role": "system", "content": continuation_system_prompt}
    #     else:
    #         temp_messages.insert(0, {"role": "system", "content": continuation_system_prompt})
    #
    #     try:
    #         print(f"📤 대화 이어가기 생성 중...")
    #         response = self.client.chat.completions.create(
    #             model=self.deployment_name,
    #             messages=temp_messages,
    #             max_tokens=50,
    #             temperature=0.7,
    #             top_p=1.0,
    #         )
    #
    #         continuation = response.choices[0].message.content
    #
    #         if continuation is None:
    #             continuation = ""
    #
    #         return continuation
    #
    #     except Exception as e:
    #         print(f"❌ 대화 이어가기 오류: {e}")
    #         return ""

    # def continue_conversation(self, ai_name, device_serial=None):
    #     """대화를 자동으로 이어가기 (후속 질문/제안 추가)
    #     [나중에 필요시 사용 가능한 메서드]
    #
    #     Args:
    #         ai_name: AI 페르소나 이름
    #         device_serial: 디바이스 시리얼 (선택사항)
    #
    #     Returns:
    #         str: 후속 질문/제안 포함된 응답
    #     """
    #     # 시스템 프롬프트 수정 (대화 이어가기 지시 추가)
    #     system_prompt = self.system_prompts.get(
    #         ai_name, "You are a helpful assistant. Respond in Korean."
    #     )
    #
    #     # DB 컨텍스트 추가
    #     db_context = ""
    #     user_name = None
    #     if device_serial and self.db_manager:
    #         db_context, user_name = self.db_manager.build_context(device_serial)
    #
    #     final_system_prompt = system_prompt
    #
    #     # 사용자 이름 치환
    #     if user_name:
    #         final_system_prompt = final_system_prompt.replace("user", user_name)
    #
    #     if db_context:
    #         final_system_prompt += f"\n\n## 사용자 컨텍스트\n{db_context}"
    #
    #     # 대화 이어가기 명시 지시
    #     final_system_prompt += "\n\n## 중요: 대화 이어가기\n지금 당신의 마지막 응답에 후속 질문이나 따뜻한 제안을 추가해줘. 사용자가 대화를 계속하도록 자연스럽게 유도해줘."
    #
    #     # 시스템 메시지 업데이트
    #     if self.messages and self.messages[0].get("role") == "system":
    #         self.messages[0] = {"role": "system", "content": final_system_prompt}
    #     else:
    #         self.messages.insert(0, {"role": "system", "content": final_system_prompt})
    #
    #     try:
    #         print(f"📤 대화 이어가기 요청 중...")
    #         response = self.client.chat.completions.create(
    #             model=self.deployment_name,
    #             messages=self.messages,
    #             max_tokens=100,
    #             temperature=0.7,
    #             top_p=1.0,
    #         )
    #
    #         continuation = response.choices[0].message.content
    #
    #         if continuation is None:
    #             continuation = ""
    #
    #         return continuation
    #
    #     except Exception as e:
    #         print(f"❌ 대화 이어가기 오류: {e}")
    #         return ""

    def __del__(self):
        """소멸자: 데이터베이스 연결 종료"""
        if hasattr(self, 'db_manager') and self.db_manager:
            try:
                self.db_manager.close()
            except:
                pass


# ==========================================
# 실행 테스트
# ==========================================
if __name__ == "__main__":
    manager = ChipiBrain()
    
    # 1. 메모리 초기화 (새로운 대화 시작)
    manager.create_new_memory()
    
    print("--- 대화 시작 (AI: 치피) ---")

    # 디바이스 시리얼 (env에서 자동 읽음)
    device_serial = os.environ.get("DEVICE_SERIAL")
