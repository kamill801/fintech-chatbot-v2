# fintech-chatbot V2

카카오톡 기반 핀테크 챗봇. 페르소나: 70대 욕쟁이 할머니. Cleo 벤치마킹.

## Stack
- Python 3.11.6, Flask + RQ + Redis
- OpenAI Responses API (Assistants API에서 마이그레이션 중, 2026/8/26 종료)
- 배포: Cloudtype / 로깅: Google Sheets

## 작업 방식 (반드시 준수)

1. **TECHSPEC-First**: 코드 작업 전 반드시 @TECHSPEC.md 확인. 모호하면 사용자에게 질문.
2. **PLAN 기반**: @PLAN.md의 active task만 작업. 여러 task 동시 진행 금지.
3. **Get Bearings**: 매 세션 시작 시 pwd → progress.txt 마지막 블록 → @PLAN.md → `git log --oneline -10`.
4. **Plan Mode**: 파일 수정 전 변경 계획 제시 → 사용자 승인 → 실행.
5. **Incremental**: 한 세션 = 한 task = 한 커밋. 한 번에 다 하지 말 것.
6. **Clean Exit**: 세션 종료 시 commit + progress.txt 추가 + PLAN.md 마킹 갱신.
7. **Self-Verify**: 기능 완료 표시 전 end-to-end 테스트. 코드 read만으로 "완료" 판단 금지.
8. **막히면 멈춘다**: 가정 기반 진행 금지. 환경변수/외부 API/비즈니스 로직은 반드시 질문.

## 절대 원칙

- @TECHSPEC.md는 immutable. 수정하려면 PLAN.md에 dedicated task 필요.
- progress.txt는 **append-only**. 과거 항목 수정 금지.
- 페르소나 작업 시:
  - "필터 우회" 같은 표현 절대 금지 → 캐릭터 정당화로 대체
  - 페르소나는 "지시"가 아니라 "예시"로 정의
  - user_state는 매 턴 시스템 컨텍스트에 주입
  - recent_messages는 user/assistant 페어로 저장
  - 페르소나 리마인더는 사용자 메시지 *직전*에 sandwich
- 건드리지 말 것: app.py, worker.py, sheets_logger.py (Phase 1 한정)

## 주요 문서

- @PLAN.md — 작업 큐, 현재 active task
- @TECHSPEC.md — 불변 명세
- progress.txt — 세션 인수인계 노트 (append-only)
- HANDOFF.md — V1→V2 전환 컨텍스트 (참고용)

## 잊지 마라

세션 시작 시 가장 먼저 progress.txt 마지막 블록을 읽는다. 
TECHSPEC을 함부로 수정하지 않는다. 
하나의 세션에 하나의 task만 작업한다.
욕쟁이 할머니는 욕설 단어가 본질이 아니라 생활 비유 + 장부 검사 톤 + 정 많은 잔소리다.
