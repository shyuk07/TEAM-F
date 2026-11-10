# 예약·결제 프론트엔드 검증 인수인계

- 작성일: 2026-11-10 (Asia/Seoul)
- 작업 폴더: `C:\Users\qodba\last-call-fe-res`
- 상태: 최종 검증 완료. 사용자 승인 후 구현 커밋을 feature 브랜치에 푸시했고 PR 제목·본문을 준비했다.
- 새 기능은 시작하지 않았다. 기존 Claude 구현을 보존하고 발견된 결함만 수정했다.

## 검증 종료 당시 Git 상태와 검증 범위

- 브랜치: `feat/reservations-frontend`
- HEAD: `fd8a643340038fc97994e940f04e4184892b49ca` (작업 전후 동일)
- upstream: `origin/main`
- 최종 로컬 origin/main: `3ddea13bd8ffbb31ef1fbcd521af79eac29d75f3`
- HEAD는 origin/main보다 15개 커밋 뒤다. 시작 시 6개였으나 작업 중 원격 추적 ref가 갱신됐다.
- 검증 대상은 위 HEAD와 현재 미커밋 변경이다. 최신 main을 merge/rebase하지 않았고 통합 결과는 검증하지 않았다.
- 검증 단계에서는 commit/push/PR 생성, stash/reset/restore/checkout/clean을 수행하지 않았다. 이후 사용자에게 커밋·푸시 승인을 받았으며 PR 생성은 요청되지 않았다.
- `git diff --check` 통과. 기존 docs/reference/README.md의 LF→CRLF 안내만 출력된다.

## Claude가 남긴 기존 변경

- 예약·결제 feature 4계층과 DI wiring.
- checkout, payment-complete, my-reservations page 및 임시 CustomerLayout·라우팅.
- 예약 목록 응답 확장과 단건 조회 API, 관련 백엔드 테스트·API 문서.
- 프론트엔드 설계 문서 2개와 화면 ↔ slice 대응표.
- 기존 기준선 재실행: 프론트엔드 단위 테스트 452개, 전체 E2E 40개 통과.
- E2E 40개 중 예약·결제 실서버 흐름은 4개, 나머지 36개는 기존 모킹 테스트였다.

설계 정본은 [예약](../design/frontend/reservations.md), [결제](../design/frontend/payments.md)다. 기존 D/C 결정과 임시 동작은 유지했다.

## 이번에 추가 수정한 결함

| ID | 문제 | 수정 |
| --- | --- | --- |
| FE-R1 | 사용 포인트를 모르는 상태에서 예약 총액을 현금 환불액으로 표시 | CancelReservationSheet의 숫자 환불행 제거. D-14대로 기존 환불 안내 문구만 유지 |
| FE-R2 | 긴 목록의 시트가 화면 밖에 표시되고 배경 결제·키보드 접근 가능 | body portal의 고정 모달, 안전한 초기 포커스, 양방향 Tab 제한, 배경 inert, 스크롤 잠금·복원, 닫을 때 포커스 복귀. 처리 중 닫기·이동 차단 |
| FE-R3 | 취소 마감 400·상태 충돌 409 이후 목록이 오래된 상태로 남음 | 오류 시트와 메시지를 유지하면서 목록만 다시 조회 |
| QA-W1 | PC 고객 화면의 테두리 포함 외곽이 422px | CustomerLayout에 border-box 적용, 외곽 420px |
| ARCH-1 | 신규 예약·결제 토큰의 컨테이너 검증 누락 | tests/app/container.test.ts에 토큰 2개 추가 |
| ARCH-2 | presentation에서 예약 예정 총액을 직접 계산 | domain/price.ts로 계산 이동, 경계 테스트 추가 |

새 내부 보조 파일: `frontend/src/features/reservations/presentation/ReservationModal.tsx`, `frontend/src/features/reservations/domain/price.ts`.
두 파일은 기존 설계 파일 목록에 아직 열거되지 않았으나 독립 구조 검토에서 허용된 내부 분리로 확인했다.

제품 코드 변경 범위는 reservations feature, my-reservations page, CustomerLayout뿐이다.
설정·의존성·CSS 복사본·shared·백엔드 제품 코드는 이번 검증에서 추가 수정하지 않았다.

## 회귀 확인과 독립 리뷰

- QA가 기존 단언을 유지하며 회귀 단위 테스트 5개와 E2E 시나리오 3개 × 2 viewport를 추가했다.
- 수정 전 단위 회귀: 새 5개 실패, 기존 대상 13개 통과. 오케스트레이터도 동일 실패를 직접 확인했다.
- 수정 전 E2E 회귀: 5개 실패, 정상 모바일 폭 1개 통과.
- 배경 결제 버튼에 focus 후 Enter를 누르면 실제 결제 요청이 1회 발생하는 결함까지 재현했다.
- 수정 담당자와 QA·리뷰 담당자를 분리했다.
- 최종 정확성 독립 재리뷰: **APPROVE**, 차단·중요 지적 0.
- 최종 프론트엔드 구조 정독: **PASS**.
- 백엔드 독립 정확성·계층 정성 검토: **PASS**, 필수 수정 사항 없음.

## 최종 실행 결과

| 검사 | 명령/방법 | 결과 |
| --- | --- | --- |
| 프론트엔드 계층 | `node .claude/skills/layer-check/check_layers.mjs` | 96파일, 위반 0, exit 0 |
| lint | `npm run lint` | 오류·경고 0, exit 0 |
| format | `npm run format:check` | 차이 0, exit 0 |
| typecheck | `npm run typecheck` | 오류 0, exit 0 |
| 단위 테스트 | `npm run test` | 57파일, **460 passed**, failed/skipped/todo 0 |
| build | `npm run build` | 성공, 180 modules, dist/index.html 생성 |
| 작업 주석 | `annotations.mjs check` / `list` | 형식 위반 0, 36개: FIXME 2 / TODO 33 / open-issues 1 |
| 디자인 CSS | `sync_styles.mjs check` | 복사본 2개 동기화 |
| 전체 E2E | `npm run test:e2e` | **46 passed**, failed/flaky/skipped 0, 11.2초 |
| Vite dev | run_vite.mjs dev/check | 첫 화면·SPA fallback·백엔드·JSON proxy PASS |
| Vite preview | run_vite.mjs preview/check | 첫 화면·SPA fallback·백엔드 PASS. preview에는 dev proxy 검사 비적용 |
| 백엔드 의존성 | `uv sync --check --offline` | lockfile·기존 venv 일치, 변경 없음 |
| 백엔드 계층 | `python .claude/skills/layer-check/check_layers.py` | 147파일, 위반 0, 기존 넓은 예외 핸들러 경고 3 |
| 백엔드 import | 기존 venv에서 `import main` | 성공 |
| 백엔드 전체 테스트 | 기존 venv에서 `python -m pytest -q -rs` | **1847 passed**, failed/skipped 0, 505.36초 |
| HTTP smoke | 저장소 smoke_auth.sh의 동일 단언 | **51 PASS / 0 FAIL** |
| 공백 검사 | `git diff --check` | 통과 |

최종 E2E 구성: 실서버 예약·결제 4개 + 기존 모킹 36개 + 새 모달·폭 회귀 모킹 6개.
프론트엔드 계층·typecheck·460개 단위 테스트는 오케스트레이터도 직접 재실행해 확인했다.
기존 node_modules의 `npm ls`가 정상이라 불필요한 npm ci 재설치는 생략했다.

HTTP smoke의 초기 실행은 Windows cp949, Git Bash 임시 경로, CRLF stdout 문제로 실패했다.
원본 파일·제품 코드·단언은 바꾸지 않고 UTF-8, cygpath 경로 변환, stdout CR 제거, 동일 JSON의 stdin 전달을 실행 래퍼에서 적용한 뒤 51개가 통과했다. 초기 실패 로그도 보존했다.

## 브라우저·시각 확인

- 모바일 360×740: 시트 x=0, y=465, 폭 360, 높이 275. 안내 문구와 버튼 모두 화면 안에 표시.
- PC 1280×800: 고객 앱·시트 x=430, 폭 420, 시트 y=525, 높이 275.
- 취소 시트의 안전한 초기 초점은 「돌아가기」다.
- 긴 목록, 양방향 Tab, 배경 결제 차단, 닫은 뒤 초점 복귀, 직접 URL 새로고침을 확인했다.
- QA와 오케스트레이터가 최종 모바일·PC 스크린샷을 각각 직접 확인했다.

## 격리 DB와 프로세스

- 기존 `last-call-postgres-1` / 호스트 5433에는 접속·쓰기·초기화·중지를 하지 않았다.
- 별도 컨테이너: `codex-fe-res-verify-20261110`, postgres:17, 호스트 `127.0.0.1:55437`.
- 데이터 경로는 tmpfs이며 기존 볼륨 mount는 0개다.
- pytest는 `lastcall_verify_test`, 서버·E2E는 `lastcall_verify_e2e`를 사용했다.
- DATABASE_URL과 TEST_DATABASE_URL을 명시적으로 격리 DB로 지정했다. destructive fixture는 이 전용 DB에서만 실행됐다.
- E2E에는 E2E_BACKEND_URL, E2E_DATABASE_URL, E2E_BACKEND_PYTHON을 별도로 지정했다.
- 검증 백엔드 8001, Vite dev 5173, preview 4173은 모두 종료했고 리스너가 없음을 확인했다.
- 격리 DB 컨테이너는 저장소 운영 지침대로 실행 상태로 남겼다. tmpfs이므로 컨테이너 중지 시 데이터는 유지되지 않는다.
- 브라우저가 없어 검증 캐시에 Chromium headless shell을 설치했다. 프로젝트 패키지·설정 변경은 없다.

## 로그·스크린샷

모두 Git ignored 경로에 보존했으며 커밋 대상이 아니다.

`backend/.pytest_cache/codex-verification/`

- `pytest-full.log`: 백엔드 전체 테스트
- `root-final-vitest.log`: 오케스트레이터 최종 전체 단위 테스트
- `smoke-auth-win-compat.log`: 최종 HTTP smoke
- `frontend-artifacts/final-verification-summary.log`: 최종 QA 요약
- `frontend-artifacts/final-*.log`: 명령별 최종 결과
- `frontend-artifacts/red-*.log`: 수정 전 실패 근거
- `frontend-artifacts/final-customer-modal-360.png`
- `frontend-artifacts/final-customer-modal-1280.png`
- `frontend-artifacts/final-visual-observations.json`
- `frontend-artifacts/browsers/`: Playwright 캐시

재실행 시 PLAYWRIGHT_BROWSERS_PATH는 위 browsers 절대경로로 지정한다.
기존 `frontend/.verification-codex`는 안전 경로 확인 후 위 ignored 경로로 이동했고 남아 있지 않다.

## 기존 제한과 후속 인수인계

이번 범위의 차단·중요 결함은 해결했다. 아래는 새 기능으로 진행하지 않았다.

- 고객 정식 셸·TabBar, C2 전체 page와 ReserveOfferPanel 통합, 길찾기 링크, 임시 문구·환불 표시 정책.
- 결제 후 세션 포인트 즉시 갱신은 payments D-9의 임시 미갱신 동작 유지.
- 지난 예약 전체 페이지 조회 방식은 reservations D-7 유지.
- 기존 FIXME 2개: OwnerLayout의 상점주 승인 상태 가드, useAuthController의 보호 API 401/TOKEN_REVOKED 세션 정리. 기존 명시된 구현·배포 전 처리 시점 유지.
- 백엔드 목록의 서로 다른 할인마다 get_terms를 호출하는 N+1 성능 주의: 최대 100건에서 추가 조회 약 300회 가능. 필수 수정으로 판정되지 않아 유지.
- 최신 main 15개 커밋 통합·통합 결과 검증은 수행하지 않았다.

## 게시 결과와 다음 단계

- 사용자 승인: 2026-11-10, 커밋·푸시·PR 본문 준비.
- 구현 커밋: [c28a0ee](https://github.com/shyuk07/TEAM-F/commit/c28a0ee141f38b148ea2dac0fdc468428e4b269e).
- 원격 feature 브랜치: [feat/reservations-frontend](https://github.com/shyuk07/TEAM-F/tree/feat/reservations-frontend).
- 구현 커밋 푸시 후 원격 SHA와 일치를 확인했고 upstream을 `origin/feat/reservations-frontend`로 설정했다.
- PR 제목·본문 초안: [PR 본문](2026-11-10-reservations-frontend-pr.md).
- PR 생성은 요청되지 않아 수행하지 않았다. [PR 작성 화면](https://github.com/shyuk07/TEAM-F/compare/main...feat/reservations-frontend?expand=1)에서 준비한 본문을 사용할 수 있다.
- 문서의 게시 결과를 갱신하는 후속 문서 커밋이 추가될 수 있다. 최종 브랜치 SHA는 git log와 원격 ref로 확인한다.
- 최신 main 통합·충돌 해결·통합 결과 검증은 별도 후속 범위다. 이번 검증 수치를 통합 결과의 통과로 해석하지 않는다.
