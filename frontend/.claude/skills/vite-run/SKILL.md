---
name: vite-run
description: 마감 직전 프론트엔드의 Vite 개발 서버와 빌드 미리보기(preview)를 백그라운드로 띄우고 끄며, 백엔드 proxy(/v1 → localhost:8001) 연결과 SPA 라우트 응답을 실제로 확인합니다. Node 스크립트라 Windows PowerShell·macOS·Linux에서 같은 명령으로 동작합니다. 구현한 화면이 실제로 뜨는지 확인할 때, Playwright E2E 전에 서버가 필요할 때, proxy·빌드 결과를 점검할 때 사용합니다.
---

# Vite 서버 실행과 확인

명령은 모두 `frontend` 폴더에서 실행합니다. 서버는 `scripts/run_vite.mjs`로만 띄우고 끕니다. `pkill`·`taskkill`로 이름을 찾아 끄지 않습니다(다른 사람의 서버까지 끕니다).

## 1. 스크립트

Node만 있으면 Windows PowerShell·macOS·Linux에서 같은 명령입니다.

```powershell
node .claude/skills/vite-run/scripts/run_vite.mjs dev       # 개발 서버 백그라운드 실행 (기본 5173)
node .claude/skills/vite-run/scripts/run_vite.mjs preview   # 빌드 미리보기 (기본 4173, 먼저 npm run build)
node .claude/skills/vite-run/scripts/run_vite.mjs check     # 화면·SPA 라우트·proxy 확인
node .claude/skills/vite-run/scripts/run_vite.mjs stop      # 이 스크립트가 띄운 서버만 종료
node .claude/skills/vite-run/scripts/run_vite.mjs status
```

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--port <번호>` | dev 5173 / preview 4173 | 이미 쓰는 포트면 실패합니다 |
| `--state-dir <폴더>` | OS 임시 폴더의 `lastcall-vite` | PID·로그를 두는 곳. 에이전트는 scratchpad를 지정합니다 |
| `--backend <URL>` | `http://localhost:8001` | check가 확인할 백엔드 주소 |
| `--wait <초>` | 30 | 서버 응답을 기다리는 시간 |

`check`, `stop`, `status`에도 `dev`와 같은 `--state-dir`를 넘깁니다. 다르면 띄운 서버를 찾지 못합니다.

동작 방식:
- `npm run dev` 대신 `node node_modules/vite/bin/vite.js`를 직접 띄웁니다. 셸(cmd·PowerShell·bash) 차이가 없고, `vite.config.ts`는 그대로 적용됩니다. `package.json`의 `dev`·`preview` 스크립트에 `vite` 외 옵션을 넣으면 이 스크립트에도 같은 옵션을 추가해야 합니다.
- 종료는 자식 프로세스까지 끕니다. Windows는 `taskkill /T /F`, macOS·Linux는 프로세스 그룹에 SIGTERM → 10초 뒤 SIGKILL입니다.

## 2. check가 확인하는 것

| 항목 | 방법 | PASS 기준 |
| --- | --- | --- |
| 첫 화면 | `GET /` | 200, HTML에 `<div id="root">` |
| SPA 라우트 | `GET /__spa_check__/1` | 200, `index.html`과 같은 HTML (dev·preview 모두 fallback 동작) |
| 백엔드 실행 | `GET {backend}/docs` | 200 (꺼져 있으면 "백엔드 꺼짐"으로 SKIP) |
| proxy (dev만) | `GET /v1/offers` | 응답 `Content-Type`이 JSON (HTML이면 proxy 설정 누락) |

check는 실패 항목이 있으면 종료코드 1을 냅니다. 백엔드가 꺼져 있으면 proxy 항목은 SKIP이며 통과로 치지 않습니다. 백엔드는 `../backend/README.md`로 띄웁니다(이 스킬은 백엔드를 띄우지 않습니다).

## 3. 화면 동작 확인
- 브라우저로 직접 볼 때는 출력된 주소를 엽니다. 자동 확인은 Playwright(`qa-verification` §4)를 씁니다.
- 고객 화면은 모바일 폭(360px)과 PC 폭(1280px) 두 번 확인합니다. 720px 컨테이너 기준으로 TabBar ↔ nav, CtaBar ↔ 패널 버튼이 바뀌는지 봅니다(`design-system-usage` §3).
- 작업이 끝나면 성공·실패와 관계없이 `stop`으로 서버를 끕니다.
