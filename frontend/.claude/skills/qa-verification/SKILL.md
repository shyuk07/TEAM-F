---
name: qa-verification
description: 마감 직전 프론트엔드의 품질 검증 절차와 PASS/FAIL 판정 기준입니다. package.json 검증 스크립트 정의(lint, format:check, typecheck, test, test:e2e, build), ESLint 0 error·0 warning, Prettier 차이 0, tsc 0 error, Vitest failed 0·skip 0, Playwright E2E 시나리오 작성·실행, 빌드 산출물 확인, 화면 상태(로딩·빈·에러) 확인, 디자인 시스템 복사본 동기화 확인을 다룹니다. 구현 결과를 검증할 때, "QA 해줘", "테스트 돌려줘", "E2E 확인"을 요청받았을 때, 실패하는 테스트(Red)를 먼저 작성할 때 사용합니다.
---

# QA 검증

규칙 ID와 완료 게이트 명령은 `frontend-invariants` §6이 정본입니다. 이 스킬은 그 명령의 **판정 방법과 E2E 작성법**을 정합니다.

## 1. package.json 스크립트 (정본)

검증 명령 이름은 아래로 고정합니다. 프로젝트를 만들 때 이 이름으로 추가합니다.

| 스크립트 | 명령 | PASS 기준 |
| --- | --- | --- |
| `lint` | `eslint . --max-warnings 0` | 0 error, 0 warning |
| `format:check` | `prettier --check .` | 차이 0 파일 |
| `format` | `prettier --write .` | (수정용, 검증에 쓰지 않음) |
| `typecheck` | `tsc -b --noEmit` | 0 error |
| `test` | `vitest run` | failed 0, skipped 0, todo 0 |
| `test:e2e` | `playwright test` | failed 0, flaky 0, skipped 0 |
| `build` | `tsc -b && vite build` | 성공, `dist/index.html` 존재 |

스크립트가 없으면 FAIL이 아니라 **"스크립트 없음"**으로 보고하고, 위 표의 명령을 추가하라고 적습니다. 대신 `npx`로 직접 실행해 결과를 참고로 적을 수 있습니다.

## 2. 검증 순서

앞 단계가 실패해도 다음 단계를 계속 실행해 전체 결과를 모읍니다. 단, `npm install` 실패는 이후 전부 "실행 불가"입니다. 명령은 한 줄씩 실행하며 Windows PowerShell·macOS·Linux에서 같습니다.

```powershell
npm ci                                              # package-lock.json 기준 설치
node .claude/skills/layer-check/check_layers.mjs    # 위반 0건
npm run lint
npm run format:check
npm run typecheck
npm run test
npm run build
npm run test:e2e                                    # 화면 흐름을 바꿨거나 머지 전이면
```
디자인 시스템 복사본 동기화도 확인합니다.
```powershell
node .claude/skills/design-system-usage/scripts/sync_styles.mjs check
```

## 3. 판정 기준
- 경고도 실패입니다(`--max-warnings 0`). "경고라서 무시"로 판정하지 않습니다.
- `skipped`, `todo`, `.only`가 있으면 FAIL입니다. 개수와 위치를 적습니다(F16).
- 실패 테스트를 다시 돌려서 통과하면 **flaky**로 적고 PASS로 치지 않습니다.
- 검사를 통과시키려고 테스트·설정·규칙을 고치지 않습니다. 고쳐야 할 것은 보고만 합니다.
- 변경한 domain 함수·훅·컴포넌트에 테스트가 없으면 "테스트 없음"으로 적고, 필요한 테스트 목록을 제안합니다(`react-implementation` §7 표 기준).

## 4. Playwright E2E

### 위치와 설정
- 테스트는 `frontend/e2e/<흐름>.spec.ts`에 둡니다(`src` 밖).
- `playwright.config.ts`의 `webServer`가 dev 서버를 띄우게 하거나, `vite-run` 스킬로 띄운 서버에 `baseURL`로 붙습니다. 둘을 섞어 서버를 두 번 띄우지 않습니다.
- 프로젝트는 모바일(360×740)과 데스크톱(1280×800) 두 가지로 돌립니다(720px 컨테이너 기준 전환 확인).

### 시나리오 작성
- 흐름 단위로 씁니다. 화면 ID를 테스트 이름에 넣습니다: `test('C1 → C2 → A1: 비로그인 예약 시 로그인으로 이동', ...)`
- 요소는 `getByRole`, `getByLabel`, `getByText`(screens.md 문구 그대로)로 찾습니다.
- 백엔드에 의존하는 흐름은 두 가지 중 하나로 씁니다. 어느 쪽인지 테스트 파일 첫 줄 주석에 적습니다.
  - **모킹**: `page.route('**/v1/**', ...)`로 응답을 고정. 상태 분기(빈 목록, 409, 500)를 확인할 때.
  - **실서버**: 백엔드(8001)를 띄우고 실행. 실제 연동을 확인할 때. 백엔드가 꺼져 있으면 실행하지 않고 "백엔드 필요"로 보고합니다(skip으로 통과시키지 않음).
- 최소 시나리오 후보(화면 연결 지도는 `../docs/design-system/layout.md`):
  1. C1 홈 로딩 → 목록 / 빈 상태 / 에러 상태
  2. C2 상세 → 비로그인 "예약하고 결제" → A1 로그인 → C3 결제
  3. C3 결제 → C4 완료 → C5 내 예약
  4. C5 → C5a 예약 취소 확인 → 취소 결과
  5. 새로고침·직접 주소 입력(SPA fallback): `/` 외 라우트에서 `page.reload()` 후 같은 화면

## 5. TDD Red 작성
설계안을 받아 테스트를 먼저 쓸 때는:
1. 설계안(`../docs/design/frontend/<slice>.md`)의 domain 규칙·경계값, 훅의 상태 전이, 화면 상태별 표시를 테스트로 옮깁니다.
2. 실행해서 **모두 실패하는지** 확인하고 실패 이유(구현 없음)를 적습니다. 다른 이유로 실패하면(문법, import 경로) 고친 뒤 다시 확인합니다.
3. 구현 중 테스트를 고쳐야 하면 이유를 보고서에 적습니다(단언 약화 금지, F16).

## 6. 보고 형식
| 단계 | 결과 | 비고 |
| --- | --- | --- |
| 설치(`npm ci`) | PASS/FAIL | |
| layer-check | | 위반 수, 태그별 |
| lint | | error·warning 수 |
| format:check | | 차이 파일 수 |
| typecheck | | error 수 |
| test | | passed·failed·skipped |
| build | | |
| test:e2e | | passed·failed·flaky, 모킹/실서버 |
| 디자인 복사본 | | 동기화 / 불일치 |

마지막 줄에 **PASS / FAIL**과, FAIL이면 실패 항목과 재현 명령을 적습니다.
