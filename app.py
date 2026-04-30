from flask import Flask, request, jsonify
from redis import Redis
from rq import Queue
import os

from tasks import process_kakao_message

app = Flask(__name__)

redis_url = os.getenv("REDIS_URL")
print(f"🔗 Redis URL: {redis_url}")

try:
    redis_conn = Redis.from_url(redis_url, socket_connect_timeout=10)
    redis_conn.ping()
    print("✅ Redis 연결 성공!")
except Exception as e:
    print(f"❌ Redis 연결 실패: {e}")

q = Queue("kakao", connection=redis_conn)


@app.route("/question", methods=["POST"])
def question():
    body = request.json
    print(f"📥 받은 요청 전체: {body}")

    try:
        user_message = body["userRequest"]["utterance"]
        user_id = body["userRequest"]["user"]["id"]

        # ✅ 이미지 URL 파싱 (여러 경로 시도)
        image_url = None
        
        # 경로 1: params.media.imageUrl
        if not image_url:
            image_url = (
                body.get("userRequest", {})
                    .get("params", {})
                    .get("media", {})
                    .get("imageUrl")
            )
        
        # 경로 2: params.imageUrl (직접)
        if not image_url:
            image_url = (
                body.get("userRequest", {})
                    .get("params", {})
                    .get("imageUrl")
            )
        
        # 경로 3: utterance가 카카오 CDN URL인 경우 (현재 상황)
        if not image_url and user_message and user_message.startswith("https://talk.kakaocdn.net"):
            image_url = user_message
            user_message = "사진을 보냈습니다"
            print(f"🖼️ utterance에서 이미지 URL 감지!")

        # 카카오톡이 자동 생성한 콜백 URL 추출
        callback_url = body.get("userRequest", {}).get("callbackUrl")
        if not callback_url:
            callback_url = body.get("callbackUrl")

        print(f"👤 사용자 ID: {user_id}")
        print(f"💬 사용자 메시지: {user_message}")
        print(f"🖼️ 이미지 URL: {image_url}")
        print(f"🔗 콜백 URL: {callback_url}")

        if not callback_url:
            print("❌ 콜백 URL을 찾을 수 없습니다!")
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{
                        "simpleText": {
                            "text": "콜백 URL이 없습니다. 스킬 설정을 확인해주세요."
                        }
                    }]
                }
            })

        # 비동기 작업 큐잉
        job = q.enqueue(
            process_kakao_message,
            user_id,
            user_message,
            callback_url,
            image_url,
            job_timeout='10m'
        )
        print(f"✅ Job 등록 성공: {job.id}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    # 카카오톡에 즉시 응답 (3초 룰 대응)
    return jsonify({
        "version": "2.0",
        "useCallback": True
    })