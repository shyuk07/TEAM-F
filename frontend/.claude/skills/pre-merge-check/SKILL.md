---
name: pre-merge-check
description: 마감 직전 프론트엔드에서 브랜치나 PR을 main에 머지하기 전에 실행하는 검증 순서입니다. 변경 범위·저장소 위생, FSD·4계층 규칙, 린트·포맷·타입, 단위 테스트, 빌드, 디자인 시스템 복사본 동기화, E2E·실제 실행, 코드 리뷰를 차례로 확인하고 머지 가능 여부를 판단합니다. "머지 전 점검", "PR 검증"을 요청받았을 때 사용합니다.
---

# 머지 전 점검

아래 순서대로 실행하고, 앞 단계가 실패하면 원인을 먼저 보고합니다. 검사를 통과시키려고 규칙이나 테스트를 끄지 않습니다(F16). 명령은 `frontend` 폴더에서 한 줄씩 실행합니다. Windows PowerShell·macOS·Linux에서 같은 명령입니다.

## 1. 변경 범위와 저장소 위생
```powershell
git fetch origin main
git diff --stat origin/main...HEAD -- .
```
- 변경된 FSD 계층·slice를 정리합니다.
- `node_modules/`, `dist/`, `.env*.local`, `playwright-report/`, `test-results/`가 변경 목록에 있으면 바로 위반입니다(F15).
- `package.json`의 dependencies가 바뀌었는데 `package-lock.json`이 바뀌지 않았으면 위반입니다.

## 2. 구조 규칙
```powershell
node .claude/skills/layer-check/check_layers.mjs
```
위반 0건이어야 합니다. 새 slice를 만들었거나 옮겼으면 `fe-architect`로 F7·F9 정독 점검과 `fsd-structure` §7 대응표 갱신을 확인합니다.

## 3. 정적 검사와 테스트
`qa-verification` §2 순서대로 실행합니다(`npm ci` → lint → format:check → typecheck → test → build). 판정은 `qa-verification` §3을 따릅니다.

## 4. 디자인 시스템 복사본
```powershell
node .claude/skills/design-system-usage/scripts/sync_styles.mjs check
```
불일치면 어느 쪽이 맞는지 판단하지 않고 보고합니다.

## 5. 실제 동작
```powershell
node .claude/skills/vite-run/scripts/run_vite.mjs dev
node .claude/skills/vite-run/scripts/run_vite.mjs check
npm run test:e2e
node .claude/skills/vite-run/scripts/run_vite.mjs stop
```
- 백엔드는 `../backend/README.md`로 띄웁니다. 꺼져 있으면 proxy·실서버 E2E는 "백엔드 필요"로 적고 통과로 치지 않습니다.
- `npm run build` 뒤 `run_vite.mjs preview` → `check` → `stop`으로 빌드 결과의 SPA fallback도 확인합니다.
- 서버는 성공·실패와 관계없이 `stop`으로 끕니다.

## 6. 코드 리뷰
`fe-reviewer` 에이전트로 `fe-code-review` 스킬 절차를 실행합니다. 차단·중요 지적이 있으면 머지 불가입니다.

내장 리뷰 스킬을 함께 쓸 때 `origin/HEAD` ref가 없으면 `unknown revision`으로 실패합니다. 먼저 확인합니다.
```powershell
git rev-parse --verify -q origin/HEAD
```
아무것도 출력되지 않으면 ref가 없으므로 만듭니다.
```powershell
git remote set-head origin -a
```

## 보고 형식
| 단계 | 결과 | 비고 |
| --- | --- | --- |
| 변경 범위·위생 | | |
| 구조 규칙 | | 위반 수 |
| lint / format / typecheck | | |
| test | | passed·failed·skipped |
| build | | |
| 디자인 복사본 | | |
| 실제 동작·E2E | | check 결과, E2E passed·failed, 백엔드 실행 여부 |
| 코드 리뷰 | | APPROVE / REQUEST_CHANGES |

마지막 줄에 **머지 가능 / 수정 후 머지 / 머지 불가** 중 하나와 그 이유를 적습니다.
