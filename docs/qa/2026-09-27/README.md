# 2026-09-27 모바일 UX 진단 증거

대상: `main @ b46e3a4` / 장부 AI. **수정 전 진단이며 릴리스 검증이 아니다.**

## 합성 동작 재현

`current-behavior.repro.tsx`는 실제 LedgerProvider/페이지와 mocked API를 조합한다. 외부 요청과 실제 사용자의 데이터는 사용하지 않았다.

2026-09-27 실행 결과: Vitest 3.2.7, 1 file / **5 tests passed**. 테스트가 결함의 존재를 assert하므로 정상 동작을 뜻하지 않는다.

| 재현 | 결과 |
|---|---|
| POST 성공 후 summary 503 | 거래가 state에 있지만 createTransaction reject |
| POST 성공 후 plan 503 | 거래가 state에 있지만 createTransaction reject |
| POST 성공 후 localStorage 삭제 예외 | 거래 1건, 입력 화면에 저장 실패 alert |
| 이전 달 날짜로 입력 후 성공 | `/ledger`로만 이동, 해당 날짜 heading 없음 |
| preview 성공 → 수정 → 새 preview 실패 | 기존 preview로 확인 버튼이 계속 enabled |

재실행 방법 (같은 기준 코드에서):

```bash
# 저장소 루트에서 실행. 기존 파일이 있으면 중단한다.
(
  set -eu
  test ! -e frontend/src/UXAudit.repro.test.tsx
  cp docs/qa/2026-09-27/current-behavior.repro.tsx frontend/src/UXAudit.repro.test.tsx
  trap 'rm -f frontend/src/UXAudit.repro.test.tsx' EXIT
  npm --prefix frontend test -- --reporter=verbose src/UXAudit.repro.test.tsx
)
```

실제 실행에 사용한 임시 `frontend/src/UXAudit.repro.test.tsx`는 제거했다. 이후 구현자는 정상 결과를 assert하는 테스트를 정규 suite에 추가한다. 이 파일은 역사적 재현 자료로 유지한다.

## 로컬 화면 캡처

- 로컬 Vite, Chromium 414×896 CSS px, deviceScaleFactor 1, 애니메이션을 완료시킨 정지 캡처.
- 기존 `?demo=1` 합성 fixture. 외부 도메인의 요청을 차단했다.
- `plan-before-414.png`는 데모의 활성 계획에서 “계획 수정”을 눌러 진입한 1단계다. 사용자 화면은 신규 계획이지만 같은 폼/CSS를 사용한다.
- `settings-before-414.png`는 데모라 인증된 프로필 카드가 없다. 실제 카카오 프로필의 시각 검증 자료가 아니다.
- fullPage 캡처의 하단 탭/FAB는 캡처 시 viewport 위치에 나타난다. 긴 캡처 한 장만으로 최하단 콘텐츠 접근 불가를 단정하지 않는다.
- 원본 사용자 스크린샷은 이 폴더로 복사하지 않았다.

| 화면 | 파일 |
|---|---|
| 홈 | [home-before-414.png](home-before-414.png) |
| 계획 1단계 | [plan-before-414.png](plan-before-414.png) |
| 거래 입력 | [add-before-414.png](add-before-414.png) |
| 캘린더 | [ledger-before-414.png](ledger-before-414.png) |
| 리포트 | [report-before-414.png](report-before-414.png) |
| 설정 | [settings-before-414.png](settings-before-414.png) |

측정 결과: [layout-observations.json](layout-observations.json).

- 문서 너비는 6개 화면 모두 414px. **iOS date input 넘침을 Chromium에서 재현하지 못했다.**
- plan grid rows `145px 94px 487px`, 실제 진행 막대 높이 5px. 진행 막대는 y187, form은 y299. `align-content:normal`에 의해 내용보다 큰 행이 생기는 것을 확인했다.
- 계획 폼/리포트 비교 카드의 내부 여백 누락, 계정처럼 보이는 홈 장식, 설정 스위치 트랙 미표시도 캡처에서 확인했다.

재실행 도구: [layout-audit.mjs](layout-audit.mjs). 기존 설치된 Playwright module과 Chromium 경로를 환경변수 `PLAYWRIGHT_MODULE`, `CHROMIUM_EXECUTABLE`로 지정한다. Vite를 `127.0.0.1:3015`에 띄운 뒤 저장소 루트에서 실행한다. 새 의존성 설치는 필요하지 않다. 캡처 파일은 덮어쓰므로 수정 후 증거는 별도 날짜/after 경로로 보존한다.

## 확인하지 않은 범위

실제 실패 요청의 status/error code, Render 로그, 실계정 거래 조회/저장, iPhone Safari/WKWebView DOM 측정, 화면 크기 전체 매트릭스, 새 운영 배포 E2E. 이 범위는 실행 명세에 다음 검증으로 기록했다.

## 인계

[전체 실행 명세](../../plans/2026-09-27-mobile-ux-repair-handoff.md) · [다른 모델용 요청](../../plans/2026-09-27-execution-prompt.md)
