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

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

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


def save_message_pair(state: dict, role: str, content: str):
    # V1 마이그레이션: 문자열 배열이면 초기화
    if state["recent_messages"] and not isinstance(state["recent_messages"][0], dict):
        state["recent_messages"] = []

    state["recent_messages"].append({"role": role, "content": content})
    state["recent_messages"] = state["recent_messages"][-20:]


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
# 6️⃣ 컨텍스트 조립 (Sandwich)
# =========================

def load_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


_KEYWORD_TO_TAGS = [
    (["배달", "음식", "치킨", "피자", "족발", "보쌈"], ["배달", "배달반복"]),
    (["커피", "카페", "아메리카노", "라떼", "음료"], ["커피소액"]),
    (["참았", "절약", "아꼈", "안 샀", "안 마셨"], ["절약성공"]),
    (["택시"], ["택시소액", "택시고액"]),
    (["쇼핑", "옷", "코트", "신발", "가방", "질렀"], ["쇼핑고액"]),
    (["스트레스", "힘들", "우울", "짜증", "지쳐"], ["스트레스소비", "감정토로"]),
    (["결산", "리포트", "정리"], ["결산요청"]),
    (["예산", "목표", "저축", "모으"], ["예산설정"]),
]
_DEFAULT_TAGS = ["배달", "절약성공", "감정토로"]


def _parse_few_shot_sections(raw: str) -> dict:
    sections = {}
    current_tag = None
    current_lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]") and len(stripped) > 2 and " " not in stripped:
            if current_tag is not None:
                sections[current_tag] = "\n".join(current_lines).strip()
            current_tag = stripped[1:-1]
            current_lines = []
        elif current_tag is not None:
            current_lines.append(line)
    if current_tag is not None and current_lines:
        sections[current_tag] = "\n".join(current_lines).strip()
    return sections


def select_few_shot(user_message: str) -> str:
    raw = load_prompt("few_shot.md")
    sections = _parse_few_shot_sections(raw)

    selected_tags = []
    for keywords, tags in _KEYWORD_TO_TAGS:
        if any(kw in user_message for kw in keywords):
            selected_tags.extend(tags)

    seen = set()
    final_tags = []
    for tag in selected_tags + _DEFAULT_TAGS:
        if tag not in seen and tag in sections:
            seen.add(tag)
            final_tags.append(tag)

    examples = [sections[tag] for tag in final_tags[:5]]
    return "[예시 — 욕쟁이 할미 응답 패턴]\n\n" + "\n\n".join(examples)


def build_state_summary(user_state: dict) -> str:
    month_key = datetime.now().strftime("%Y-%m")
    monthly = user_state.get("monthly_data", {}).get(month_key, {})
    emotions = user_state.get("emotion_tags", [])[-3:]
    spending = user_state.get("spending_categories", {})

    lines = ["[현재 사용자 상태]"]
    if monthly:
        lines.append("- 이번 달 소비: " + ", ".join(f"{k} {v}회" for k, v in monthly.items()))
    else:
        lines.append("- 이번 달 소비: 기록 없음")
    if emotions:
        lines.append("- 최근 감정: " + ", ".join(emotions))
    if spending:
        lines.append("- 누적 카테고리: " + ", ".join(f"{k} {v}회" for k, v in spending.items()))

    return "\n".join(lines)


def build_context(user_state: dict, user_message: str) -> list:
    persona = load_prompt("persona.md")
    few_shot = select_few_shot(user_message)
    state_summary = build_state_summary(user_state)
    reminder = load_prompt("reminder.md")

    # recent_messages[-1]은 현재 user 메시지 (Task 1.2에서 LLM 호출 전에 저장)
    # recent_messages[:-1]은 이전 대화 히스토리
    recent = user_state.get("recent_messages", [])
    history = recent[:-1] if len(recent) > 1 else []

    messages = [
        {"role": "system", "content": persona},
        {"role": "system", "content": few_shot},
        {"role": "system", "content": state_summary},
        *history,
        {"role": "system", "content": reminder},
        {"role": "user", "content": user_message},
    ]

    print(f"🔍 [Context] {len(messages)}개 메시지 (history={len(history)}턴)")
    return messages


# =========================
# 7️⃣ 월간 리포트 생성
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

        # user 메시지 페어 저장 (LLM 호출 전)
        save_message_pair(user_state, "user", user_message)

        # Responses API 호출 (sandwich 컨텍스트)
        print("🤖 Responses API 호출")
        response = client.responses.create(
            model="gpt-4o",
            input=build_context(user_state, user_message)
        )

        assistant_reply = response.output_text

        if not assistant_reply:
            assistant_reply = "옘병, 말이 길어졌다. 다시 말해봐라."

        # assistant 응답 페어 저장 + state 최종 저장
        save_message_pair(user_state, "assistant", assistant_reply)
        save_user_state(user_id, user_state)

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
