import os

from dotenv import load_dotenv
from openai import AzureOpenAI


class JarvisMemoryManager:
    def __init__(self):
        load_dotenv()

        # Azure OpenAI 환경 변수
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        if not azure_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT가 설정되지 않았습니다.")

        # Azure OpenAI 클라이언트 초기화
        if azure_api_key:
            # API 키 인증
            self.client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=azure_endpoint,
                api_key=azure_api_key,
            )
        else:
            # 암호 없는 인증
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()
            self.client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=azure_endpoint,
                azure_ad_token_provider=lambda: credential.get_token(
                    "https://cognitiveservices.azure.com/.default"
                ).token,
            )

        self.deployment_name = deployment_name
        self.messages = self.load_memory()

        # AI별 시스템 프롬프트 설정
        self.system_prompts = {
            "jarvis_4": os.environ.get(
                "SYSTEM_PROMPT_JARVIS_4",
                "You are Jarvis, a helpful AI assistant. Respond in Korean.",
            ),
            "jarvis_3.5": os.environ.get(
                "SYSTEM_PROMPT_JARVIS_35",
                "You are Jarvis, a helpful AI assistant. Respond in Korean.",
            ),
            "Terminal_AI": os.environ.get(
                "SYSTEM_PROMPT_TERMINAL",
                'You are a terminal AI assistant. When you need to execute terminal commands, wrap them in [터미널]["command"]. Respond in Korean.',
            ),
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
                    if msg.get("role") != "system":
                        f.write(f"{msg['role']}:{msg['content']}\n")
        except Exception as e:
            print(f"히스토리 저장 오류: {e}")

    def create_new_memory(self):
        """새 대화 히스토리 생성"""
        self.messages = []
        self.save_memory()

    def add_msg(self, msg):
        """사용자 메시지 추가"""
        self.messages.append({"role": "user", "content": msg})

    def get_run_id(self, ai_name):
        """호환성을 위한 메서드 (실제로는 사용하지 않음)"""
        # 이전 인터페이스 호환성을 위해 유지
        return ai_name

    def wait_run(self, ai_name):
        """AI 응답 생성 및 반환"""
        # 시스템 프롬프트 확인 및 추가
        system_prompt = self.system_prompts.get(
            ai_name, "You are a helpful assistant. Respond in Korean."
        )

        if not any(msg.get("role") == "system" for msg in self.messages):
            self.messages.insert(0, {"role": "system", "content": system_prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=self.messages,
                max_tokens=4096,
                temperature=1.0,
                top_p=1.0,
            )

            assistant_message = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": assistant_message})
            self.save_memory()

            return assistant_message

        except Exception as e:
            error_msg = f"응답 생성 오류: {e}"
            print(f"❌ {error_msg}")
            return error_msg


if __name__ == "__main__":
    manager = JarvisMemoryManager()
    manager.add_msg("내 이름이 뭐라고?")
    print(manager.wait_run("jarvis_3.5"))

    manager.add_msg("내 이름은 김철수야")
    print(manager.wait_run("jarvis_3.5"))

    manager.add_msg("내 이름이 뭐라고?")
    print(manager.wait_run("jarvis_3.5"))

    manager.create_new_memory()

    manager.add_msg("내 이름이 뭐라고?")
    print(manager.wait_run("jarvis_3.5"))
    print(manager.wait_run("jarvis_3.5"))
