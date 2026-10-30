# Task8.5 재개 지점

이번 run7/7 종료, Task8.5 미완료. pass8이나 자동 새 run을 만들지 않는다. 명시적 새 실행 요청을 받으면 과거 실패/시도 이력을 보존하며 새 계약을 먼저 기록한다.

1. `RESULTS.md`, `rounds.json`, `verification.json`, Git/제공자 SHA를 읽는다. 마지막 확인 main/운영 후보는 `2af944facc7b48a1bf482002e0e4c5c5c13bce17`. `.agents/`, `AGENTS.md`, 옛 `docs/qa/2026-10-12/RESUME.md`는 변경·커밋하지 않는다.
2. 마지막 미커밋 F28–F32 범위는 `FINAL-REPAIR-PLAN.md`, 지문은 `source-manifest.json`. F33은 미수정이다. TECHSPEC/원래 기록/계산/계정/키/app.py/worker.py/sheets_logger.py를 보존한다.
3. CUA browser transport부터 복구 확인한다. 마지막 UI 읽기조차 실패했다. 다른 앱/사용자 브라우저 작업을 방해하거나 토큰/쿠키/숨은 API로 우회하지 않는다. 이전 IAB browser3/tab3, Chrome browser1의 QA탭1211556755, Render탭1211556762는 시점 의존이다.
4. 복구되면 원래 계정에서 모드를off로 복원하고 reload 읽기 확인한다. 마지막 QA상태는on. `[QA1030-02] 이체 확인` 수동 합성 계좌는 필요하면 숨기되 삭제하지 않는다. 원래 현금 계좌·프로필·목표는 변경하지 않는다. QA 브라우저 viewport 재정의도 원복한다.
5. 마지막 경로는 QA점심 거래 `6fa829bf-b1c5-46c5-a52f-5b855a226713`. 사유 `QA: 계획한 기본 점심 식사이므로 필요한 지출로 평가합니다.`로 수정 제출했지만 저장 여부 미확인이다. 먼저 읽고 중복 제출하지 않는다. 돌아보기 ‘잘 쓴 돈’ 저장은 확인됐다.
6. F33 기본값 ‘필요한 만남이었어요.’를 회귀로 재현해 빈 초기값/placeholder/명시적 사유 저장/모달 재진입을 고친다. 자동검증 결과는 verification.json에서 원래 실패와 구분해 읽는다.
7. 기존 Vercel `upglow/jangbu-ai`, Render `jangbu-api`에만 동일 검증 SHA를 쓴다. Supabase 기존 `kkzsyprcujrxzrsognhb`(zkzkdh1789, Free/Seoul), Render 소유 gyqlswh112. 새 프로젝트/키/요금제/권한 변경 없음. 현재 상태는 다시 읽는다.
8. 전체 A–M 행렬/동결 PERSONA-RUBRIC을 유지한다. 운영2af의9사례4통과/5미달은 최종 수정본 효과가 아니다. fallback을 모델 성공으로 세지 않고, 원래 프로필을 고정 fixture로 덮지 않는다.
9. 과거 공급자 슬롯22/36 사용. 추가 호출 전 새 실행의 숫자 한도를 명시하고 과거 이력을 보존한다. 사용자 지시대로 로컬401 키 교체/새 로컬 유료 호출은 하지 않는다.
10. 검증된 최종본만 scoped stage/비밀 검사/commit/push/동일SHA배포/최대2회 확인을 수행한다. 전체 서비스3회, 최종9사례, 물리 iPhone을 자동 테스트/HTTP200으로 대신하지 않는다.

로컬 검증 서버 정리는 rounds.json의cleanup을 읽는다. 다른 사용자의Redis/시뮬레이터/Chrome/서버를 종료하지 않는다. QA계좌/기록은 보존하고 CSV원문은 업로드하지 않는다.
