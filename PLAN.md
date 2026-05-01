# Development Plan — fintech-chatbot V2

## 🎯 Current State

- **Phase**: 1 (Responses API 전환 + 프롬프트 V2 + Validator)
- **Active Task**: 1.4
- **Last Session**: 2026-05-01 (Task 1.3 완료 — 프롬프트 V2 + build_context)
- **Last Commit**: a47169f
- **Branch**: main

---

## 📋 Phase 1: Responses API 전환 + 프롬프트 V2 + Validator

목표: V1의 핵심 결함 4가지(thread 누적 / state 미주입 / 필터 우회 문구 / 단발성 메시지) 해결.

성공 시 페르소나 일관성 70~80% 회복 예상. 50턴 연속 대화 후에도 톤 유지가 핵심 검증 지표.

---

### Task 1.1: Responses API 단순 전환 ✅ 1f7be48

**Status**: ✅ Done  
**Goal**: tasks.py의 LLM 호출 부분을 Assistants API에서 Responses API로 교체. 프롬프트는 그대로 유지.

**Files to modify**:
- `tasks.py` (대대적 리팩토링)

**Files NOT to modify**:
- `app.py`, `worker.py`, `sheets_logger.py` — Phase 1 전체에서 손 안 댐

**Implementation steps**:
1. 기존 `get_or_create_thread` 함수 제거
2. `process_kakao_message` 안의 thread/message/run/polling 로직 제거 (`client.beta.threads.*` 호출 모두 삭제)
3. `client.responses.create()` 호출로 교체
   - `model`: 일단 `gpt-4o`로 시작 (Phase 1 후반에 4o-mini와 비교)
   - `input`: 기존 시스템 프롬프트(Assistant instructions에 있던 것)를 첫 system 메시지로, user 메시지를 두 번째로 전달
4. 응답 파싱: `response.output_text` 또는 `response.output[0].content[0].text` 사용
5. 기존 `ASSISTANT_ID` 환경변수는 코드에서 사용하지 않되, .env에서는 지우지 않음 (롤백 대비)
6. polling 관련 `time.sleep(0.7)` 등 모두 제거

**Acceptance**:
- [ ] `grep -r "client.beta.threads" tasks.py` 결과 없음 (Assistants API 호출 0회)
- [ ] `grep -r "client.responses" tasks.py` 결과 있음 (Responses API 호출 정상)
- [ ] `python3 -m py_compile tasks.py` 에러 없음
- [ ] `get_or_create_thread` 함수 정의 없음
- [ ] 응답 시간 단축 확인 (polling 제거)

**Verification**:
- 코드: `grep` 명령으로 Assistants API 흔적 없는지 확인
- 컴파일: `py_compile`로 syntax 에러 없는지 확인
- (실제 카카오톡 테스트는 Task 1.4 끝나고 Phase 1 통합 테스트에서)

**Estimated effort**: 1 세션 (1~2시간)

**참조**: 
- TECHSPEC Section 5 (시스템 아키텍처)
- TECHSPEC Section 6 (LLM 호출 방식)
- TECHSPEC Section 10 Phase 1 / Commit 1

**주의사항**:
- Responses API는 Chat Completions와도 다르고 Assistants와도 다름. OpenAI 공식 docs 참조: https://platform.openai.com/docs/guides/migrate-to-responses
- openai 라이브러리 버전이 Responses API 지원하는지 확인 (1.50+ 권장). 부족하면 `pip install -U openai` + requirements.txt 갱신.

---

### Task 1.2: recent_messages user/assistant 페어 저장 ✅ 5decf9d

**Status**: ✅ Done  
**Goal**: V1에서 user 메시지만 저장되던 recent_messages를 user/assistant 페어로 저장. 멀티턴 컨텍스트 정상 유지.

**Files to modify**:
- `tasks.py`

**Implementation steps**:
1. `update_emotion_state` 함수에서 `state["recent_messages"].append(message)` 부분 제거 (역할 분리)
2. 새 함수 `save_message_pair(state, role, content)` 추가
   - role은 "user" 또는 "assistant"
   - state["recent_messages"]에 `{"role": role, "content": content}` 형태로 append
   - 최근 20개(=10턴) 유지: `state["recent_messages"] = state["recent_messages"][-20:]`
3. `process_kakao_message`에서:
   - LLM 호출 **전**: user 메시지를 `save_message_pair(state, "user", user_message)`로 저장
   - LLM 호출 **후**: assistant 응답을 `save_message_pair(state, "assistant", assistant_reply)`로 저장
4. LLM 호출 시 `recent_messages`를 input의 system 메시지 다음에 그대로 전달 (페어 형태 그대로 사용)
5. **마이그레이션 처리**: 기존 V1 사용자의 recent_messages가 문자열 배열일 수 있음
   - state 로드 시 첫 항목이 dict가 아니면 빈 배열로 초기화 (간단한 방어 코드)
   - 또는 V2는 새 사용자만 받는다고 가정 (배포 후 사용자 거의 없으면 OK)

**Acceptance**:
- [ ] `recent_messages`가 `[{"role": "user/assistant", "content": "..."}]` 형태로 저장됨
- [ ] 최근 20개로 제한됨
- [ ] LLM 호출 시 페어가 input에 정상 포함됨
- [ ] 기존 V1 데이터(문자열 배열)가 있어도 크래시 안 남
- [ ] `python3 -m py_compile tasks.py` 에러 없음

**Verification**:
- 코드: `update_emotion_state` 안에 `recent_messages.append` 없는지 확인
- 코드: `save_message_pair` 함수 정의 확인
- 마이그레이션: 기존 Redis 데이터로 테스트 (필요 시 mock state)

**Estimated effort**: 0.5~1 세션 (30~60분)

**참조**: 
- TECHSPEC Section 7 (데이터 모델 — recent_messages 형식)
- TECHSPEC Section 10 Phase 1 / Commit 2

---

### Task 1.3: 새 프롬프트 V2 + Few-shot + Persona Reminder ✅ a47169f

**Status**: ✅ Done  
**Goal**: V1의 단계 지시 기반 프롬프트를 예시 중심 V2로 교체. Sandwich 패턴으로 Lost in the Middle 방어.

**Files to create** (신규):
- `prompts/persona.md` — Static Persona (캐릭터 정당화 포함, "필터 우회" 문구 X)
- `prompts/few_shot.md` — 10~12개 예시 (다양한 시나리오, 각 1~3문장)
- `prompts/reminder.md` — 사용자 메시지 직전 reinjection용 (3~5줄)

**Files to modify**:
- `tasks.py`

**Implementation steps**:

1. `prompts/` 폴더 생성

2. `prompts/persona.md` 작성:
   - 70대 국밥집 욕쟁이 할머니 정체성
   - "거친 말투는 한국 시장통 세대의 애정 표현" 정당화 (캐릭터 안에서)
   - 어휘 풀: "옘병", "썩을 놈", "지랄", "디진다", "대가리", "똥강아지", 그러나 **본질은 단어가 아니라 생활 비유 + 장부 검사 톤**
   - 친절한 금융 상담사 말투 금지 (긍정적 재정의)

3. `prompts/few_shot.md` 작성 (최소 10개, 다양한 시나리오):
   - 예산 설정 / 새 소비 보고 / 반복 소비 / 스트레스성 소비 / 절약 성공 / 고액 쇼핑 / 감정 토로 / 말투 조절 요청 등
   - 각 예시: `[시나리오 라벨]\n사용자: ...\n할미: ...` 형식
   - 응답은 1~3문장, 생활 비유 사용

4. `prompts/reminder.md` 작성 (3~5줄):
```
   [잊지 마라: 너는 욕쟁이 할미다. 친절한 금융 상담사 말투 절대 금지.
   3문장 이내로 답하고, 첫 마디는 호통이나 혀 차는 소리로 시작한다.
   소비 이유를 모르면 조언하지 말고 이유부터 추궁한다.
   생활 비유 사용. 단어("옘병", "썩을 놈")보다 톤이 본질이다.]
```

5. `tasks.py`에 새 함수 `build_context(user_state, user_message)` 추가:
   - prompts/ 폴더의 .md 파일을 읽어 시스템 메시지로 조립
   - 조립 순서 (Sandwich):
```
     [1] system: persona.md 내용
     [2] system: few_shot.md 내용 (선택된 예시들)
     [3] system: user_state 요약 (단순 형태 — Phase 1)
     [4] user/assistant 페어: recent_messages
     [5] system: reminder.md 내용 (★ 사용자 메시지 직전)
     [6] user: user_message
```

6. **간단한 few-shot 선택** (intent 분류 X, 단순 키워드 매칭만):
   - user_message에 "배달" 포함 → 배달 관련 예시 우선 선택
   - "커피" 포함 → 커피 예시
   - "택시" 포함 → 택시 예시
   - "예산" 포함 → 예산 설정 예시
   - 매칭 안 되면 → 기본 예시 3~4개 사용
   - **이는 Phase 2의 본격 intent 분류로 가기 전 임시 방편**

7. user_state 요약 (단순 형태):
```
   [현재 사용자 상태]
   - 이번 달 누적 소비: {len(monthly_data) > 0 시 카테고리별 카운트}
   - 최근 감정 태그: {emotion_tags[-3:]}
   - 누적 소비 카테고리: {spending_categories}
```

8. **기존 V1 시스템 프롬프트 텍스트는 코드에서 완전 제거**. "필터 우회" 문구 사라져야 함.

**Acceptance**:
- [ ] `prompts/` 폴더에 3개 .md 파일 존재
- [ ] `tasks.py`에 `build_context` 함수 정의됨
- [ ] V1의 시스템 프롬프트 텍스트 흔적 없음 (`grep -i "필터 우회" tasks.py` 결과 없음)
- [ ] LLM 호출 input이 위 6단계 sandwich 구조로 조립됨
- [ ] reminder.md 내용이 user 메시지 직전에 위치
- [ ] `python3 -m py_compile tasks.py` 에러 없음

**Verification**:
- 코드: 위 grep + 함수 정의 확인
- 시스템 메시지 출력: 디버깅용 print로 input 구조 확인
- (실제 페르소나 톤 검증은 Task 1.4 + 통합 테스트에서)

**Estimated effort**: 1.5~2 세션 (2~3시간) — prompts 작성 시간 포함

**참조**: 
- TECHSPEC Section 4 (캐릭터 페르소나)
- TECHSPEC Section 5 (시스템 아키텍처 — sandwich 조립)
- TECHSPEC Section 9 (Success Criteria F002, F006, F008~F010)
- TECHSPEC Section 10 Phase 1 / Commit 3

**주의사항**:
- 어휘 풀 나열보다 **상황별 용례**가 강력. "할미는 이렇게 말한다: ..." 형식.
- few_shot 예시는 자연스럽게 1~3문장. 길게 쓰면 모델이 따라서 길게 답함.
- "안전 필터를 우회하라" 류 문구 절대 금지 (RLHF 방어모드 트리거).

---

### Task 1.4: Response Validator + 1회 리라이트 ⏳

**Status**: ⏳ Active  
**Goal**: 카카오 전송 전 응답 검증. 기준 미달 시 1회 리라이트, 그래도 실패 시 fallback.

**Files to create** (신규):
- `validators.py`

**Files to modify**:
- `tasks.py`

**Implementation steps**:

1. `validators.py` 작성:
```python
   FORBIDDEN_PHRASES = [
       "제가 도와드릴게요", "도와드리겠습니다",
       "요약하자면", "결론적으로",
       "AI로서", "인공지능으로서",
       "안녕하세요",
       "도움이 필요하시면",
   ]
   
   FALLBACK_REPLY = "옘병, 말이 길어졌다. 다시 말해봐라, 얼마 썼고 왜 썼냐?"
   
   def count_sentences(text: str) -> int:
       # 한국어 문장 끝 표시(. ? ! 다.)로 분리
       # 정확하진 않아도 대략 카운트
       ...
   
   def validate_reply(text: str) -> tuple[bool, str]:
       # (is_valid, reason)
       if count_sentences(text) > 3:
           return False, "3문장 초과"
       for phrase in FORBIDDEN_PHRASES:
           if phrase in text:
               return False, f"금지어 포함: {phrase}"
       if "?" in text and text.count("?") > 1:
           return False, "질문 2개 이상"
       return True, ""
   
   def build_rewrite_prompt(original: str, reason: str) -> str:
       return f"""직전 응답이 다음 기준을 어겼다: {reason}
   
   원래 답변: {original}
   
   같은 의도로 더 짧게(1~3문장), 욕쟁이 할미 톤으로, 금지어 없이 다시 답해라."""
```

2. `tasks.py`의 `process_kakao_message`에 통합:
```python
   reply = call_responses_api(...)
   is_valid, reason = validate_reply(reply)
   
   if not is_valid:
       print(f"⚠️ 검증 실패: {reason}, 1회 리라이트 시도")
       rewrite_prompt = build_rewrite_prompt(reply, reason)
       reply = call_responses_api_with_rewrite(rewrite_prompt)
       
       is_valid_retry, reason_retry = validate_reply(reply)
       if not is_valid_retry:
           print(f"❌ 리라이트도 실패: {reason_retry}, fallback 사용")
           reply = FALLBACK_REPLY
```

3. fallback 답변은 캐릭터 톤 유지 (친절한 에러 메시지 X):
   - "옘병, 말이 길어졌다. 다시 말해봐라."
   - "지랄, 할미 머리 아프다. 간단히 말해봐라."
   등 2~3개 중 랜덤 선택 가능

**Acceptance**:
- [ ] `validators.py` 파일 존재
- [ ] `validate_reply`, `build_rewrite_prompt`, `count_sentences`, `FORBIDDEN_PHRASES`, `FALLBACK_REPLY` 정의됨
- [ ] `tasks.py`에서 validator 호출 통합됨
- [ ] 일부러 4문장짜리 응답을 만들어서 입력 → 리라이트 또는 fallback 작동 확인
- [ ] 일부러 "안녕하세요" 포함된 응답 만들기 → 리라이트 작동 확인
- [ ] `python3 -m py_compile tasks.py validators.py` 에러 없음

**Verification**:
- 단위 테스트: `validate_reply("이 문장은. 3문장. 4문장이다. 너무. 많아.")` → False
- 단위 테스트: `validate_reply("옘병, 또 배달이여? 이번 주만 세 번째다.")` → True
- 단위 테스트: `validate_reply("안녕하세요, 욕쟁이 할미입니다.")` → False (금지어)
- 통합: tasks.py 안에서 validator가 실제 호출되는지 print 출력으로 확인

**Estimated effort**: 1 세션 (1~1.5시간)

**참조**: 
- TECHSPEC Section 8 (에러 처리)
- TECHSPEC Section 9 (Success Criteria F004, F005)
- TECHSPEC Section 10 Phase 1 / Commit 4

---

## 🎯 Phase 1 완료 후 통합 테스트

Task 1.4까지 끝나면 카카오톡 실제 테스트 (별도 세션):

1. `.env` 새 OpenAI API 키 발급해서 채우기
2. 로컬에서 `python app.py` + `python worker.py` 실행
3. ngrok 등으로 카카오톡 콜백 URL 노출
4. TECHSPEC Section 10.5의 12개 테스트 케이스 + 30턴/50턴 연속 대화
5. 결과를 progress.txt에 통합 테스트 결과 블록으로 추가
6. 통과하면 Phase 1 완료 → Phase 2 task 정의 시작

---

## 📋 Phase 2 (예정): JSON 구조화 출력 + turn_policy + 친밀도

> Phase 1 통과 후 정의. 현재는 비어 있는 게 정상.

미리 알고 있는 task 후보:
- visible_reply + state_update JSON 분리 (Responses API structured output)
- turn_policy 모듈 (코드가 매 턴 목표/제약 결정)
- 친밀도 단계 (관계 진화 축)
- LLM 기반 상태 추출 (키워드 매칭 폐기)

---

## 📋 Phase 3 (예정): 장기 기억 RAG

> Phase 2 끝나고 정의.

---

## Backlog (언젠가)
- 이미지/영수증 처리 (별도 트랙)
- 멀티 캐릭터 (다른 페르소나)
- 음성 기능
- 결제/구독
- gpt-4o vs gpt-4o-mini 비용/품질 비교 결정

---

## Status Legend

- ⏳ Active (현재 작업 중)
- 📋 Blocked / Waiting (선행 task 대기)
- ✅ Done (commit SHA 함께 기록)
- ❌ Cancelled
- ⏸ Paused

## 갱신 규칙

- 매 세션 종료 시 `/end-session` 명령으로 마킹 갱신
- task 완료 시 ✅ + commit SHA 기록 (예: `✅ abc1234`)
- 새 task 추가는 사용자 승인 후
- TECHSPEC 변경 시 별도 task 만들기 (immutable 원칙)
