# Technical Specification — fintech-chatbot

> **이 문서는 immutable입니다.**  
> 변경하려면 PLAN.md에 "TECHSPEC 수정: <섹션>" task를 만들고 사용자 승인 받기.  
> 작성일: 2026-04-30

---

## 1. 목표 (What)

카카오톡 채널에서 사용자가 소비 내역을 보고하면, 70대 국밥집 욕쟁이 할머니 페르소나가 잔소리 + 합리적 소비 코칭을 응답하는 핀테크 챗봇.

V1 MVP는 작동하지만 페르소나 일관성과 답변 품질이 부족함. V2의 목표는 인프라(Flask + Redis + RQ + 카카오 콜백)를 유지한 채로 LLM 응답 생성 방식을 개선하는 것.

핵심 변경: OpenAI Assistants API → Responses API 전환 + 응답 하네스 재설계.

---

## 2. 동기 (Why)

### 시장 갭
- Cleo (영국 핀테크 챗봇)의 "roast mode"가 한국 시장엔 없음
- 기존 한국 가계부 앱들은 친절한 톤 일변도 → 사용자 행동 변화 유도력 약함
- 욕쟁이 할머니 페르소나가 한국 정서에 맞는 차별화 포인트

### V1의 실패 원인 (분석된 핵심 결함 4가지)
1. Assistants API thread 영구보존 → 페르소나 드리프트 (50턴 후 톤 사라짐)
2. user_state를 LLM에 안 보냄 → 일반론만 함, Cleo의 "구체성" 결여
3. "필터 우회" 문구가 RLHF 방어모드 트리거 → 욕쟁이가 점점 친절해짐
4. 관계 진화 축 부재 → 1턴 사용자/100턴 사용자 반응 동일

이 4가지가 전체 문제의 80%. V2에서 모두 해결.

---

## 3. 범위 (Scope)

### In Scope (Phase 1)
- OpenAI Responses API 전환
- 새 프롬프트 V2 (예시 중심, 캐릭터 정당화)
- recent_messages를 user/assistant 페어로 저장
- 페르소나 리마인더 sandwich 패턴
- 가벼운 응답 validator (3문장/금지어/1회 리라이트)

### Out of Scope (Phase 1)
- 본격 intent 분류 (LLM 기반) → Phase 2
- turn_policy 모듈 → Phase 2
- 친밀도 단계 명시 + 단계별 어조 → Phase 2
- LLM 기반 상태 추출 (키워드 매칭 폐기) → Phase 2
- JSON 구조화 출력 (visible_reply + state_update) → Phase 2
- 장기 기억 RAG (이원적 요약 + 임베딩) → Phase 3
- 이미지/영수증 처리 (별도 트랙)
- 멀티 캐릭터 (다른 페르소나)
- 음성 기능
- 결제/구독
- 멀티 사용자 스케일링 최적화

### 가정 (Assumptions)
- OpenAI API 키와 Responses API 접근 가능
- Assistants API는 2026년 8월 26일 종료 → 그 전에 마이그레이션 완료
- 기존 인프라(Flask + Redis + RQ + 카카오 콜백 + Google Sheets) 유지
- 카카오톡 5초 룰은 비동기 콜백으로 이미 해결됨
- 사용자는 한국어로 입력하고 한국어로 응답받음
- few-shot 예시는 한국어로 작성

---

## 4. 사용자 / 페르소나

### 주요 사용자
- 20~30대 한국어 사용자
- 카카오톡으로 소비 내역을 보고하고 싶은 사람
- 친절한 가계부 앱에 지친 사람, 감정적 자극 통한 행동 변화를 원하는 사람

### 캐릭터 페르소나 (욕쟁이 할머니)
- 70대 국밥집 50년 운영
- 입은 험하지만 손주 챙기듯 진심으로 사용자의 경제적 자립을 돕고 싶어 함
- 알고 보면 미국 우량주/ETF 장기투자로 큰 돈 굴리는 "숨은 투자 고수"
- 거친 말투는 욕설이 아니라 한국 시장통 세대의 애정 표현
- 핵심: 욕설 단어가 아니라 **생활감 있는 비유 + 장부 검사 톤 + 정 많은 잔소리**

---

## 5. 시스템 아키텍처

### 다이어그램 (V2)

```
KakaoTalk
  ↓
Flask /question (app.py)
  ↓
Redis Queue (kakao)
  ↓
RQ Worker (worker.py)
  ↓
process_kakao_message (tasks.py)
  ├─→ load_user_state (Redis)
  ├─→ load_recent_messages (Redis)
  ├─→ build_context (sandwich 조립)
  │    ├─ Static Persona (prompts/persona.md)
  │    ├─ Few-shot Examples (prompts/few_shot.md)
  │    ├─ User State Summary
  │    ├─ Recent Messages (user/assistant 페어)
  │    └─ Persona Reminder (prompts/reminder.md)
  ├─→ Responses API 호출 (OpenAI)
  ├─→ validate_reply (3문장/금지어 체크)
  ├─→ rewrite_if_needed (1회 한정)
  ├─→ save_recent_messages (user + assistant 페어)
  ├─→ save_user_state (키워드 매칭 누적)
  ├─→ Google Sheets 로그 저장
  └─→ 카카오 callback 전송
```

### 컴포넌트
- **app.py**: 카카오 웹훅 수신, RQ 큐 등록 (수정 안 함)
- **worker.py**: RQ 워커 (수정 안 함)
- **tasks.py**: LLM 호출 + 상태 관리 + 응답 처리 (대대적 리팩토링)
- **sheets_logger.py**: Google Sheets 로깅 (수정 안 함)
- **prompts/persona.md**: Static Persona 정의 (신규)
- **prompts/few_shot.md**: Few-shot 예시 모음 (신규)
- **prompts/reminder.md**: 사용자 메시지 직전 reinjection (신규)

### 데이터 흐름
1. 사용자 카카오톡 메시지 → Flask /question → Redis Queue
2. Worker가 큐에서 작업 꺼냄
3. Redis에서 user_state, recent_messages 로드
4. 컨텍스트 조립 (sandwich 패턴)
5. Responses API 호출 → 응답 받음
6. Validator 검사 → 실패 시 1회 리라이트
7. user 메시지 + assistant 응답 → recent_messages에 페어로 저장
8. Sheets 로그 + 카카오 callback 전송

---

## 6. 기술 스택 / 의존성

### LLM
- Provider: OpenAI
- API: Responses API (`client.responses.create()`)
- 모델: `gpt-4o` 또는 `gpt-4o-mini` (Phase 1에서 비용 vs 품질 검증 후 결정)
- 호출 방식: 매 턴 컨텍스트 직접 조립, thread 사용 안 함

### 백엔드
- Python 3.11.6
- Flask (웹훅 수신)
- RQ (Redis Queue, 비동기 작업)
- openai 라이브러리 (Responses API 지원 버전)
- redis-py
- python-dotenv

### 데이터 / 상태 저장
- Redis (사용자 상태, 최근 메시지, 세션 데이터)
- 키 패턴:
  - `user_state:{user_id}` → 사용자 상태 JSON
  - 기존 `thread:{user_id}` → 사용 안 함 (Phase 1 끝나면 정리)

### 외부 서비스
- 카카오톡 웹훅
- Google Sheets API (로깅)
- OpenAI Responses API

### 배포
- 환경: Cloudtype
- Python 3.11.6
- Gunicorn

---

## 7. 데이터 모델

### user_state (Redis: `user_state:{user_id}`)

```json
{
  "emotion_tags": ["stress", "impulse"],
  "spending_categories": {
    "food_delivery": 5,
    "cafe": 3
  },
  "monthly_data": {
    "2026-04": {
      "food_delivery": 12,
      "cafe": 8
    }
  },
  "recent_messages": [
    {"role": "user", "content": "오늘 배달 18000원 씀"},
    {"role": "assistant", "content": "옘병, 또 배달이여?"}
  ]
}
```

**Phase 1 핵심 변경**: `recent_messages`가 문자열 배열에서 `{role, content}` 객체 배열로 바뀜.

**Phase 2 추가 예정 필드** (Phase 1엔 없음):
- `current_phase`, `pending_question`, `relationship_level`, `char_state` 등

### Phase 1에서 안 만드는 것
- 별도 monthly_budget, remaining_budget 필드 (단순 카운트만)
- structured_state JSON 출력 (Phase 2)

---

## 8. 인터페이스

### 입력
- 카카오톡 웹훅 POST `/question`
- Body: `{"userRequest": {"utterance": "...", "user": {"id": "..."}, "callbackUrl": "..."}}`

### 출력
- 카카오톡 callback URL로 POST
- Body: `{"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "..."}}]}}`
- 응답 길이: 1~3문장

### 에러 처리
- LLM 호출 실패 → fallback 답변 ("옘병, 말이 길어졌다. 다시 말해봐라.")
- Redis 연결 실패 → 카카오에 에러 메시지 전송
- Validator 1회 리라이트 실패 → fallback 답변

---

## 9. 성공 기준 (Success Criteria)

> 이 섹션이 feature_list.json의 source of truth.

### Phase 1 완료 기준

**기능적 기준**:
- [ ] F001: Responses API 호출이 정상 작동 (Assistants API 호출 0회)
- [ ] F002: 50턴 연속 대화 후에도 페르소나 톤 유지 (생활 비유, 장부 검사 느낌)
- [ ] F003: recent_messages가 user/assistant 페어로 Redis에 저장됨
- [ ] F004: 응답이 1~3문장 이내로 유지됨 (95% 이상)
- [ ] F005: 금지어("제가 도와드릴게요", "요약하자면" 등) 응답 0회
- [ ] F006: 페르소나 리마인더가 사용자 메시지 직전에 sandwich됨

**품질 기준** (수동 평가):
- [ ] F007: 12개 테스트 케이스 (Section 10.5 참조) 통과
- [ ] F008: 절약 성공 보고 시 퉁명스러운 칭찬 (욕만 X)
- [ ] F009: 감정 토로 시 정 묻은 반응 (욕만 X)
- [ ] F010: 소비 이유 모를 때 조언 안 하고 이유부터 추궁

### 평가 시 금지 항목 (중요)
- ❌ 특정 욕설 단어("옘병", "썩을 놈" 등)가 계속 나오는지 평가하지 말 것
- ✅ 평가해야 할 것: 생활 비유, 장부 검사 톤, 정 많은 잔소리, 소비 맥락 반영

---

## 10. Phase 분해

### Phase 1: Responses API 전환 + 프롬프트 V2 + Validator (목표 4커밋)

**Commit 1: Responses API 단순 전환**
- Assistants API thread/run/polling 로직 제거
- `client.responses.create()` 호출로 교체
- 기존 프롬프트는 그대로 시스템 메시지로 전달
- 검증: 카카오톡으로 1~3턴 대화 → 응답 정상

**Commit 2: recent_messages user/assistant 페어 저장**
- `update_emotion_state`에서 user 메시지만 append하던 것 변경
- user 메시지 + assistant 응답을 페어로 저장
- 최근 10턴 (= 20 메시지) 유지
- 응답 생성 시 페어를 컨텍스트에 포함
- 검증: Redis 직접 확인 + 멀티턴 대화에서 맥락 유지

**Commit 3: 새 프롬프트 V2 + Few-shot + Persona Reminder**
- `prompts/persona.md` 작성 (Static Persona, 캐릭터 정당화)
- `prompts/few_shot.md` 작성 (10~12개 예시, 다양한 시나리오)
- `prompts/reminder.md` 작성 (3~5줄, 사용자 메시지 직전 sandwich용)
- few-shot 선택은 간단 키워드 매칭 (배달/커피/택시/쇼핑/저축)
- user_state 요약을 시스템 메시지로 단순 주입
- "필터 우회" 문구 제거, 캐릭터 정당화로 대체
- 검증: 50턴 연속 대화 후 톤 유지 확인

**Commit 4: Response Validator + 리라이트**
- 3문장 초과 검사
- 금지어 체크 (`제가 도와드릴게요`, `요약하자면`, `결론적으로`, `AI로서`, `안녕하세요`, `도움이 필요하시면`)
- 1회 리라이트 시도
- 실패 시 fallback 답변
- 검증: 일부러 길이/금지어 유발하는 입력 시도

### Phase 2 (예정): JSON 구조화 출력 + turn_policy + 친밀도
- visible_reply + state_update JSON 분리 (Responses API structured output)
- turn_policy 모듈 (코드가 매 턴 목표/제약 결정)
- 친밀도 단계 명시 + 단계별 어조
- LLM 기반 상태 추출 (키워드 매칭 폐기)
- 입력 타입 구분 (open-ended vs 트랜잭션)

### Phase 3 (예정): 장기 기억 RAG
- 이원적 요약 (관계 + 사용자 상태)
- 메모리 필터링 (실시간 데이터 충돌 처리)
- Redis Stack RediSearch 또는 외부 벡터 DB
- 임베딩 기반 유사도 검색

---

## 10.5 Phase 1 테스트 케이스

```
1. 이번 달 예산 50만원이야         (예산 설정)
2. 오늘 배달 18000원 씀             (소비 보고)
3. 오늘도 배달 시켰어 22000원       (반복 소비)
4. 스트레스 받아서 치킨 시켰어      (스트레스성 소비)
5. 커피 5800원 마셨어               (작은 소비)
6. 오늘 커피 안 사고 참았어         (절약 성공)
7. 택시비 13000원 나갔어            (교통)
8. 택시 38000원 썼어                (고액 교통)
9. 코트 23만원 질렀어               (고액 쇼핑)
10. 너무 세게 말하지 마             (말투 조절 요청)
11. 이번 주 결산해줘                (리포트 요청)
12. 요즘 너무 힘들어서 돈 막 쓰게 돼  (감정 토로)
```

추가:
- 13. 30턴 연속 대화 후 톤 유지 (시작 톤 vs 30턴 후 톤 비교)
- 14. 50턴 연속 대화 후 톤 유지 (실제 페르소나 드리프트 측정)

---

## 11. 핵심 결정 사항 (Decisions Log)

| # | 결정 | 옵션 | 선택 | 이유 | 날짜 |
|---|------|------|------|------|------|
| 1 | LLM Provider | OpenAI / Anthropic | OpenAI 유지 | Claude로 갈아타면 토큰 결제 또 필요 | 2026-04-29 |
| 2 | OpenAI API | Assistants / Chat Completions / Responses | Responses API | Assistants 4개월 후 종료, Responses가 새 표준 | 2026-04-29 |
| 3 | 메모리 트릭 | 정규식 메타데이터 / JSON 구조화 출력 | JSON 구조화 (Phase 2) | OpenAI/Claude 둘 다 안정적 | 2026-04-29 |
| 4 | 페르소나 정의 | 단계 지시 / Few-shot 예시 | Few-shot 예시 | 모델은 지시보다 예시 따름 | 2026-04-29 |
| 5 | 편향 억제 | 필터 우회 / 캐릭터 정당화 | 캐릭터 정당화 | RLHF 방어모드 회피 | 2026-04-29 |
| 6 | 컨텍스트 조립 | 단방향 / Sandwich | Sandwich (앞뒤 reinjection) | Lost in the middle 방어 | 2026-04-29 |
| 7 | Phase 1 커밋 수 | 6커밋 / 4커밋 | 4커밋 | 빠른 검증 후 다음 결정 | 2026-04-30 |
| 8 | 프롬프트 형식 | Python 모듈 / 마크다운 파일 | 마크다운 파일 | 프롬프트 튜닝 시 코드 안 건드려도 됨 | 2026-04-30 |
| 9 | Phase 1 intent 분류 | LLM 기반 / 키워드 매칭 / 안 함 | 간단 키워드 매칭 (few-shot 선택용만) | LLM 호출 2배 회피, Phase 2에서 JSON으로 통합 | 2026-04-30 |

---

## 12. 참고 자료

- Cleo: https://meetcleo.com (메모리 블로그, Sifted 인터뷰)
- 크랙 (뤼튼): https://help.crack.wrtn.ai (공식 헬프 문서, 유저 커뮤니티)
- RisuAI: https://namu.wiki/w/RisuAI (Hypa Memory)
- ChatHaruhi: https://github.com/LC1332/Chat-Haruhi-Suzumiya
- Character-LLM (EMNLP 2023): https://github.com/choosewhatulike/trainable-agents
- arXiv 2511.00222 (2025): persona drift 측정
- arXiv 2501.09959: Multi-Turn LLM Survey, LOCOMO 벤치마크
- Anthropic Effective Harnesses (Nov 2025)
- Anthropic Harness Design (Mar 2026)
- OpenAI Responses API: https://platform.openai.com/docs/guides/migrate-to-responses

---

## 13. 변경 이력

| 날짜 | 변경 내용 | 관련 PLAN task | 승인자 |
|------|-----------|---------------|--------|
| 2026-04-30 | 초안 작성 (V2 통합본 → TECHSPEC 형식 변환) | Task 0.1 | 사용자 |
