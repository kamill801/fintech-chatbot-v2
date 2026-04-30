# 욕쟁이 할머니 챗봇 V2 — 작업 인계 노트

> **작성일**: 2026-04-29  
> **상태**: agent-dev 스킬 설치 완료, 프로젝트 적용 직전  
> **다음 작업**: 스킬 실행 → 인터뷰 → 스캐폴딩 → TECHSPEC 작성

---

## 현재까지 확정된 결정

### 프로젝트 정체성
- **이름**: 욕쟁이 할머니 핀테크 챗봇 (fintech-chatbot)
- **레퍼런스**: Cleo (영국 핀테크 챗봇, "roast mode")
- **페르소나**: 70대 국밥집 할머니, 손주에게 잔소리하듯 소비 코칭
- **채널**: 카카오톡

### 기술 스택 (유지)
- Python 3.11, Flask + RQ + Redis
- 배포: 클라우드타입
- 로깅: Google Sheets

### 핵심 결정사항
1. **OpenAI Assistants API → Responses API 마이그레이션** 
   (Assistants는 2026/8/26 종료. Chat Completions가 아니라 Responses로 직행)
2. **OpenAI 유지** (Claude로 안 갈아탐 — 토큰 결제 이슈)
3. **개발 도구**: Claude Code CLI (Anthropic, macOS)
4. **글로벌 스킬 설치 완료**: ~/.claude/skills/agent-dev/ (16개 파일)

---

## 진단 — 욕쟁이 할머니 V1의 실패 원인

### 핵심 결함 4가지 (전체의 80%)
1. **Assistants API thread 영구보존** → 페르소나 드리프트
2. **user_state를 LLM에 안 보냄** → 일반론만 함, Cleo의 "구체성" 결여
3. **"필터 우회" 문구가 RLHF 방어모드 발동** → 욕쟁이가 점점 친절해짐
4. **관계 진화 축 부재** → 1턴 사용자/100턴 사용자 반응 동일

전체 17개 결함 카탈로그는 채팅 이력 참조.

---

## 적용할 5대 메커니즘 (Character.AI / 크랙 / RisuAI / Cleo 분석)

1. **레이어 1 — Static Persona**: 지시 → 예시 중심으로 재작성
2. **레이어 2 — Dynamic State**: 매 응답에 숨겨진 메타데이터 (JSON 구조화 출력 권장 — GPT 버전이 더 안정적)
3. **레이어 3 — Long-term Memory**: Hypa Memory 방식 RAG (Phase 3로 미룸)
4. **레이어 4 — Sandwich Context Assembly**: 페르소나 리마인더를 user 메시지 직전에 주입
5. **레이어 5 — Bias Suppression**: "우회"가 아니라 "재정의"로

---

## Phase 로드맵

### Phase 1 (3~4일) — Responses API + 프롬프트 V2 + 기본 validator
- Assistants → Responses API 마이그레이션
- 프롬프트 V2 (예시 중심, 필터 우회 문구 제거)
- recent_messages user/assistant 페어로 저장
- user_state를 매 턴 시스템 컨텍스트에 주입
- 가벼운 응답 validator (3문장 체크, 금지어 체크, 1회 리라이트)

### Phase 2 (5~7일) — JSON 구조화 출력 + turn_policy + 친밀도
- visible_reply + state_update JSON 분리
- turn_policy 모듈 (코드가 매 턴 목표/제약 결정)
- 친밀도 단계 명시 + 단계별 어조
- LLM 기반 상태 추출 (키워드 매칭 폐기)

### Phase 3 (1~2주) — 장기 기억 RAG
- 이원적 요약 (관계 + 사용자 상태)
- 메모리 필터링 (실시간 데이터 충돌 처리)
- 임베딩 기반 검색

---

## 코드 손 댈 곳 / 안 댈 곳

### 수정 대상
- `tasks.py` — LLM 호출 + 상태 관리 (대대적 리팩토링)

### 건드리지 말 것 (Phase 1)
- `app.py` — Flask 라우팅
- `worker.py` — RQ 워커
- `sheets_logger.py` — 로깅
- 인프라 (Redis, RQ, 카카오 콜백) 일체

---

## 내일 시작하는 법

### Step 1: 환경 확인
```bash
cd ~/Downloads/fintech-chatbot-main
ls ~/.claude/skills/agent-dev/  # 스킬 살아있는지 확인
```

### Step 2: Claude Code 새 세션
- 터미널에서 `claude` 입력
- `/skills` 로 agent-dev 보이는지 확인

### Step 3: 스킬 트리거
다음 명령을 그대로 입력:
```
@HANDOFF.md 읽고, agent-dev 스킬을 시작하자. 욕쟁이 할머니 핀테크 챗봇 프로젝트야. 이미 코드가 있는 기존 프로젝트라서 is_greenfield는 false. 현재 디렉터리는 ~/Downloads/fintech-chatbot-main이고 이 폴더에 스캐폴딩을 얹을 거야. Phase A 인터뷰 시작해줘.
```

### Step 4: Phase A 인터뷰 답변 가이드

스킬이 물어볼 질문들에 다음과 같이 답하면 돼요:

| 질문 | 답변 |
|---|---|
| 프로젝트 이름 | `fintech-chatbot` |
| 한 줄 설명 | 카카오톡 기반, 70대 욕쟁이 할머니 페르소나로 소비 코칭하는 핀테크 챗봇 (Cleo 벤치마킹) |
| 도메인 | chatbot |
| LLM Provider | OpenAI (Responses API) |
| 백엔드 | Python + Flask + RQ + Redis |
| 배포 | 클라우드타입 |
| Greenfield? | No (기존 코드 있음) |
| 초기 스코프 | MVP (Phase 1 완성 = 페르소나 안정화) |
| 참고 | Cleo (https://meetcleo.com), 크랙(뤼튼), RisuAI |
| Don't touch 파일 | app.py, worker.py, sheets_logger.py |

### Step 5: Phase C TECHSPEC 작성
스킬이 TECHSPEC 같이 채울 거예요. 위에 정리된 결정사항들을 그대로 녹이면 됨.

---

## 만약 막히면

- 채팅 이력: claude.ai 사이드바에서 "소비 비판 챗봇의 대화 흐름 개선" 검색
- 핵심 자료: 채팅 안에 Cleo 메모리 블로그, 크랙 공식 문서, Anthropic harness 글 링크 다 있음
- 17개 결함 카탈로그: 채팅에서 "Part 1. 프롬프트 자체의 문제" 검색

---

## 안 하기로 한 것 (Phase 1 범위 외)

- 이미지/영수증 처리 (별도 트랙)
- 멀티 캐릭터 (다른 페르소나)
- 음성 기능
- 결제/구독
- 멀티 사용자 스케일링

이런 거 인터뷰에서 물어보면 "Out of Scope"라고 답할 것.

---

## 한 줄 요약

> agent-dev 스킬 설치 완료. 내일은 욕쟁이 할머니 프로젝트 폴더에서 스킬 트리거 → 인터뷰 → 스캐폴딩 → TECHSPEC 작성 → Phase 1 코드 작업 시작.
