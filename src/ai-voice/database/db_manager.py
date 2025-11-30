import os

from dotenv import load_dotenv

# psycopg2 import (시스템 라이브러리 없어도 계속 진행 가능하도록)
# ImportError뿐만 아니라 OSError(시스템 라이브러리 누락)도 처리
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    HAS_PSYCOPG2 = True
except (ImportError, OSError, Exception) as e:
    HAS_PSYCOPG2 = False
    # psycopg2가 없어도 클래스는 정의되지만 사용 시 오류 발생
    print(f"⚠️  psycopg2를 import할 수 없습니다: {e}")
    print("⚠️  데이터베이스 기능을 사용하려면 다음을 설치하세요:")
    print("   sudo apt-get install libpq-dev")
    print("   또는 archive 저장소 사용:")
    print(
        "   echo 'deb http://archive.raspbian.org/raspbian buster main' | sudo tee /etc/apt/sources.list.d/archive.list"
    )
    print("   sudo apt-get update && sudo apt-get install libpq-dev")


class DatabaseManager:
    """PostgreSQL 데이터베이스 연결 및 조회"""

    def __init__(self):
        if not HAS_PSYCOPG2:
            raise ImportError(
                "psycopg2가 설치되지 않았습니다. "
                "데이터베이스 기능을 사용하려면 다음을 설치하세요:\n"
                "  sudo apt-get install libpq-dev\n"
                "  pip3 install psycopg2-binary"
            )
        # Python 3.7.3 호환: encoding 파라미터는 Python 3.9+에서만 지원
        # Python 3.7에서는 기본적으로 UTF-8을 사용하므로 encoding 파라미터 제거
        try:
            load_dotenv(encoding="utf-8")
        except TypeError:
            # encoding 파라미터가 지원되지 않는 경우 (Python 3.7)
            load_dotenv()

        # 데이터베이스 연결 정보
        self.host = os.environ.get("DB_HOST")
        self.port = os.environ.get("DB_PORT", "5432")
        self.database = os.environ.get("DB_NAME", "chytonpide_production")
        self.user = os.environ.get("DB_USER", "postgres")
        self.password = os.environ.get("DB_PASSWORD")

        if not self.host:
            raise ValueError("DB_HOST가 설정되지 않았습니다.")

        self.conn = None

    def connect(self, timeout=5):
        """데이터베이스 연결

        Args:
            timeout: 연결 타임아웃 (초, 기본값: 5)
        """
        if not HAS_PSYCOPG2:
            raise ImportError("psycopg2가 설치되지 않았습니다.")

        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                connect_timeout=timeout,  # 연결 타임아웃 설정
            )
            print("✓ PostgreSQL 연결 성공")
        except psycopg2.OperationalError as e:
            # 연결 오류는 상세 메시지 없이 간단하게만 표시
            error_msg = str(e)
            if "Connection timed out" in error_msg:
                raise TimeoutError("데이터베이스 연결 타임아웃")
            else:
                raise
        except Exception:
            raise

    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()
            print("✓ PostgreSQL 연결 종료")

    def get_user_by_email(self, email):
        """
        이메일로 사용자 정보 조회

        Args:
            email: 사용자 이메일

        Returns:
            dict: 사용자 정보 (id, name, email, etc.)
        """
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)

            try:
                cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cur.fetchone()
                return dict(user) if user else None
            finally:
                cur.close()

        except Exception as e:
            print(f"❌ 이메일로 사용자 조회 오류: {e}")
            self.conn.rollback()
            return None

    def get_user_by_device_serial(self, serial):
        """
        디바이스 시리얼로 사용자 정보 조회

        Args:
            serial: 디바이스 시리얼 번호

        Returns:
            dict: 사용자 정보 (id, name, email, etc.)
        """
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)

            try:
                # 디바이스에서 user_id 조회
                cur.execute("SELECT user_id FROM devices WHERE serial = %s", (serial,))
                device = cur.fetchone()

                if not device:
                    print(
                        f"⚠️  시리얼 '{serial}'에 해당하는 디바이스를 찾을 수 없습니다."
                    )
                    return None

                user_id = device["user_id"]

                # 사용자 정보 조회
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cur.fetchone()

                return dict(user) if user else None
            finally:
                cur.close()

        except Exception as e:
            print(f"❌ 사용자 조회 오류: {e}")
            self.conn.rollback()  # 트랜잭션 초기화
            return None

    def get_device_info(self, serial):
        """
        디바이스 정보 조회

        Args:
            serial: 디바이스 시리얼 번호

        Returns:
            dict: 디바이스 정보
        """
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("SELECT * FROM devices WHERE serial = %s", (serial,))
            device = cur.fetchone()
            cur.close()

            return dict(device) if device else None

        except Exception as e:
            print(f"❌ 디바이스 조회 오류: {e}")
            return None

    def get_latest_sensor_data(self, device_id, limit=1):
        """
        최신 센서 데이터 조회 (30분 주기)

        Args:
            device_id: 디바이스 ID
            limit: 조회 개수 (기본 1개 = 최신)

        Returns:
            list: 센서 데이터 리스트
        """
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)

            cur.execute(
                """
                SELECT * FROM sensor_data
                WHERE device_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (device_id, limit),
            )
            data = cur.fetchall()
            cur.close()

            return [dict(row) for row in data] if data else []

        except Exception as e:
            print(f"❌ 센서 데이터 조회 오류: {e}")
            return []

    def get_sensor_data_by_serial(self, serial):
        """
        디바이스 시리얼로 최신 센서 데이터 직접 조회
        (updated_at 기준으로 가장 최신 데이터)

        Args:
            serial: 디바이스 시리얼 번호

        Returns:
            dict: 최신 센서 데이터 (temperature, humidity 포함)
        """
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)

            try:
                # sensor_data 테이블에서 직접 serial로 최신 데이터 조회 (updated_at 기준)
                cur.execute(
                    """
                    SELECT * FROM sensor_data
                    WHERE serial = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (serial,),
                )
                data = cur.fetchone()

                if data:
                    print(f"✓ 센서 데이터 조회 성공: {dict(data)}")
                    return dict(data)
                else:
                    print(f"⚠️  센서 데이터 없음 (시리얼: {serial})")
                    return None
            finally:
                cur.close()

        except Exception as e:
            print(f"❌ 센서 데이터 조회 오류: {e}")
            self.conn.rollback()  # 트랜잭션 초기화
            import traceback

            traceback.print_exc()
            return None

    def get_recent_logs(self, user_id, limit=5):
        """
        최근 사용 로그 조회

        Args:
            user_id: 사용자 ID
            limit: 조회 개수

        Returns:
            list: 로그 리스트
        """
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)

            cur.execute(
                """
                SELECT * FROM logs
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            logs = cur.fetchall()
            cur.close()

            return [dict(row) for row in logs] if logs else []

        except Exception as e:
            print(f"❌ 로그 조회 오류: {e}")
            return []

    def get_user_kits(self, user_id):
        """
        사용자가 소유한 키트 정보 조회

        Args:
            user_id: 사용자 ID

        Returns:
            list: 키트 정보 리스트
        """
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("SELECT * FROM kits WHERE user_id = %s", (user_id,))
            kits = cur.fetchall()
            cur.close()

            return [dict(kit) for kit in kits] if kits else []

        except Exception as e:
            print(f"❌ 키트 조회 오류: {e}")
            return []

    def get_plant_status(self, temperature, humidity):
        """
        온습도 데이터를 기반으로 식물 상태 판단
        (바질 최적 조건: 온도 20~26℃, 습도 40% 이상)

        Args:
            temperature: 온도 (도씨)
            humidity: 습도 (%)

        Returns:
            dict: {status, condition_status, message}
        """
        try:
            # 조건 범주 정의
            temp_min, temp_max = 20, 26
            humidity_min = 40

            issues = []

            # 온도 체크
            if temperature < temp_min:
                issues.append("너무 추워")
            elif temperature > temp_max:
                issues.append("너무 더워")

            # 습도 체크
            if humidity < humidity_min:
                issues.append("목이 말라")

            # 상태 판단
            if not issues:
                condition_status = "good"
                message = "지금 딱 좋은 환경이야"
            else:
                condition_status = "bad"
                message = "치피를 좀 더 신경 써줘!"

            return {
                "status": condition_status,
                "condition_status": condition_status,
                "message": message,
                "issues": issues,
            }

        except Exception as e:
            print(f"❌ 식물 상태 판단 오류: {e}")
            return {
                "status": "unknown",
                "condition_status": "unknown",
                "message": "",
                "issues": [],
            }

    def build_context(self, device_serial, only_temperature=False, only_humidity=False):
        """
        디바이스 시리얼을 기반으로 AI에 전달할 컨텍스트 생성
        (sensor_data 테이블에서 직접 조회)

        Args:
            device_serial: 디바이스 시리얼 번호
            only_temperature: True면 온도만 포함
            only_humidity: True면 습도만 포함

        Returns:
            tuple: (context: str, user_name: str or None) - 컨텍스트 문자열과 사용자 이름
        """
        try:
            user_name = None

            # 1. 환경 변수에서 USER_EMAIL 가져오기
            user_email = os.environ.get("USER_EMAIL")

            # 2. 이메일로 먼저 조회 시도
            if user_email:
                user = self.get_user_by_email(user_email)
                user_name = user.get("name") if user else None
                if user_name:
                    print(f"✓ 사용자 조회 성공 (이메일): {user_name}")

            # 3. 이메일로 못 찾으면 시리얼로 조회
            if not user_name:
                user = self.get_user_by_device_serial(device_serial)
                user_name = user.get("name") if user else None
                if user_name:
                    print(f"✓ 사용자 조회 성공 (시리얼): {user_name}")

            # 4. 못 찾으면 None 설정 (시스템 프롬프트에서 기본값 '주인님' 사용)
            if not user_name:
                print("⚠️  사용자 정보를 찾을 수 없습니다. 기본값 'user' 사용")

            # 최신 센서 데이터 직접 조회 (시리얼 기반)
            sensor_data = self.get_sensor_data_by_serial(device_serial)

            # 컨텍스트 생성
            context = "## 현재 센서 데이터\n"

            if sensor_data:
                temperature = sensor_data.get("temperature", "N/A")
                humidity = sensor_data.get("humidity", "N/A")
                measured_time = sensor_data.get("created_at", "N/A")

                # datetime 객체를 문자열로 변환
                if hasattr(measured_time, "strftime"):
                    measured_time = measured_time.strftime("%Y-%m-%d %H:%M:%S")

                # 온도만 표시
                if only_temperature:
                    context += f"- 온도: {temperature}도\n"
                # 습도만 표시
                elif only_humidity:
                    context += f"- 습도: {humidity}%\n"
                # 둘 다 표시 (기본)
                else:
                    context += f"- 온도: {temperature}도\n"
                    context += f"- 습도: {humidity}%\n"

                context += f"- 측정시간: {measured_time}\n"

                # 식물 상태 판단 (온도와 습도 둘 다 필요할 때만)
                if (
                    not only_temperature
                    and not only_humidity
                    and temperature != "N/A"
                    and humidity != "N/A"
                ):
                    plant_status = self.get_plant_status(
                        float(temperature), float(humidity)
                    )
                    context += "\n## 현재 치피 상태\n"
                    context += f"- 조건: {plant_status['condition_status']}\n"
                    if plant_status["issues"]:
                        context += f"- 문제: {', '.join(plant_status['issues'])}\n"
                    context += f"- 상태 메시지: {plant_status['message']}\n"

            else:
                context += "- 현재 센서 데이터를 불러올 수 없습니다.\n"

            return context, user_name

        except Exception as e:
            print(f"❌ 컨텍스트 생성 오류: {e}")
            return "", None
