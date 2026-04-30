import os
import json
import requests
from typing import Optional
from datetime import datetime
from openai import OpenAI
from redis import Redis
from dotenv import load_dotenv
from sheets_logger import save_chat_log_to_sheet

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")  # 롤백 대비 유지, 코드에서 사용 안 함

SYSTEM_PROMPT = "너는 70대 국밥집 욕쟁이 할머니 핀테크 챗봇이다. 사용자의 소비 내역을 듣고 잔소리하며 소비 코칭을 한다."

redis_conn = Redis.from_url(os.getenv("REDIS_URL"))


# =========================
# 1️⃣ 사용자 상태 관리
# =========================

def get_user_state(user_id: str):
    print("📦 [State] 불러오기")

    data = redis_conn.get(f"user_state:{user_id}")
    if not data:
        print("📦 [State] 신규 상태 생성")
        return {
            "emotion_tags": [],
            "spending_categories": {},
            "monthly_data": {},
            "recent_messages": []
        }

    print("📦 [State] 기존 상태 로드 완료")
    return json.loads(data)


def save_user_state(user_id: str, state: dict):
    redis_conn.set(
        f"user_state:{user_id}",
        json.dumps(state, ensure_ascii=False)
    )
    print("💾 [State] 저장 완료")


# =========================
# 3️⃣ 감정 태깅
# =========================

def update_emotion_state(state: dict, message: str):
    emotion_keywords = {
        "스트레스": "stress",
        "우울": "sad",
        "짜증": "anger",
        "보상": "reward",
        "충동": "impulse"
    }

    for k, v in emotion_keywords.items():
        if k in message:
            state["emotion_tags"].append(v)

    state["recent_messages"].append(message)
    state["recent_messages"] = state["recent_messages"][-10:]

    print("🧠 [Emotion] 업데이트 완료")
    return state


# =========================
# 4️⃣ 소비 카테고리 누적
# =========================

def update_spending_category(state: dict, message: str):
    categories = {
        "배달": "food_delivery",
        "택시": "transport",
        "커피": "cafe",
        "쇼핑": "shopping",
        "술": "alcohol"
    }

    for k, v in categories.items():
        if k in message:
            state["spending_categories"][v] = \
                state["spending_categories"].get(v, 0) + 1

    print("💳 [Spending] 카테고리 누적 완료")
    return state


# =========================
# 5️⃣ 월별 데이터 누적
# =========================

def update_monthly_data(state: dict, message: str):
    now = datetime.now()
    month_key = now.strftime("%Y-%m")

    if month_key not in state["monthly_data"]:
        state["monthly_data"][month_key] = {}

    categories = {
        "배달": "food_delivery",
        "택시": "transport",
        "커피": "cafe",
        "쇼핑": "shopping",
        "술": "alcohol"
    }

    for k, v in categories.items():
        if k in message:
            state["monthly_data"][month_key][v] = \
                state["monthly_data"][month_key].get(v, 0) + 1

    print("📅 [Monthly] 업데이트 완료")
    return state


# =========================
# 6️⃣ 월간 리포트 생성
# =========================

def generate_monthly_report(user_state: dict):
    now = datetime.now()
    month_key = now.strftime("%Y-%m")

    monthly_data = user_state.get("monthly_data", {}).get(month_key, {})

    if not monthly_data:
        return "이번 달은 아직 소비 기록이 없네. 숨기고 있는 거 아니지? 🤔"

    total_events = sum(monthly_data.values())
    worst_category = max(monthly_data, key=monthly_data.get)

    report = f"""
📊 {month_key} 소비 리포트

총 소비 이벤트: {total_events}회

가장 많이 쓴 분야: {worst_category}

지금 패턴 유지하면 다음 달도 같은 루트다 💀
줄일 거야? 아니면 또 반복할 거야?
"""

    print("📊 [Report] 생성 완료")
    return report.strip()


# =========================
# 7️⃣ 메인 처리 함수
# =========================

def process_kakao_message(
    user_id: str,
    user_message: str,
    callback_url: str,
    image_url: Optional[str] = None
):
    print(f"\n🚀 ===== 처리 시작 =====")
    print(f"👤 user_id={user_id}")
    print(f"💬 message={user_message}")

    try:
        user_state = get_user_state(user_id)

        # 🔥 월간 리포트 요청
        if "월간 리포트" in user_message:
            print("📊 월간 리포트 트리거 감지")
            report = generate_monthly_report(user_state)

            print("📤 카카오 전송 시작")
            send_to_kakao(callback_url, report)
            print("📤 카카오 전송 완료")
            return

        # 상태 업데이트
        user_state = update_emotion_state(user_state, user_message)
        user_state = update_spending_category(user_state, user_message)
        user_state = update_monthly_data(user_state, user_message)
        save_user_state(user_id, user_state)

        # Responses API 호출
        print("🤖 Responses API 호출")
        response = client.responses.create(
            model="gpt-4o",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
        )

        assistant_reply = response.output_text

        if not assistant_reply:
            assistant_reply = "옘병, 말이 길어졌다. 다시 말해봐라."

        # =========================
        # 📄 Google Sheets 로그 저장
        # =========================
        print("📄 [Sheets] 저장 시도 시작")

        try:
            save_chat_log_to_sheet(
                user_id=user_id,
                user_message=user_message,
                assistant_reply=assistant_reply
            )
            print("📄 [Sheets] 저장 성공")
        except Exception as sheet_error:
            print("❌ [Sheets] 저장 실패:", sheet_error)

        # 카카오 전송
        print("📤 카카오 응답 전송")
        send_to_kakao(callback_url, assistant_reply)
        print("✅ ===== 처리 완료 =====")

    except Exception as e:
        print("❌ 서버 오류 발생:", e)
        import traceback
        traceback.print_exc()

        send_to_kakao(callback_url, "서버 오류가 발생했습니다.")


# =========================
# 8️⃣ 카카오 응답
# =========================

def send_to_kakao(callback_url, text):
    print("📡 카카오 API 호출")
    requests.post(
        callback_url,
        json={
            "version": "2.0",
            "template": {
                "outputs": [
                    {"simpleText": {"text": text}}
                ]
            }
        },
        timeout=5
    )
