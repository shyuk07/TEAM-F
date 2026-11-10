---
name: layer-check
description: 마감 직전 프론트엔드의 FSD 계층 import 규칙, slice 공개 API, slice 안 4계층(presentation, application, domain, infrastructure) 의존 방향, domain 순수성, fetch 위치, 하드코딩 색 사용을 자동으로 검사합니다. 코드를 작성하거나 수정한 뒤, PR이나 머지 전에, 또는 "계층 구조 확인", "FSD 규칙 검사", "import 방향 검사"를 요청받았을 때 사용합니다.
---

# FSD·4계층 규칙 검사

## 실행
`frontend` 폴더에서 실행합니다. 의존성 설치 없이 Node만 있으면 되고, Windows PowerShell·macOS·Linux에서 같은 명령입니다.

```powershell
node .claude/skills/layer-check/check_layers.mjs
```
- 기본 검사 대상은 `src/`입니다. 다른 경로는 인자로 넘깁니다: `node .claude/skills/layer-check/check_layers.mjs <경로>`
- 위반이 있으면 종료코드 1, 없으면 0입니다. `src/`가 없으면 "검사 대상 없음"을 출력하고 0으로 끝납니다.
- 파일을 읽기만 하고 쓰지 않습니다.

## 출력 태그

| 태그 | 규칙 | 잡는 것 |
| --- | --- | --- |
| `[계층방향]` | F1 | 아래 계층이 위 계층을 import (entities → features) |
| `[같은계층]` | F1 | 같은 계층의 다른 slice를 import (features/a → features/b) |
| `[공개API]` | F2 | 다른 slice의 내부 경로를 import (`@/entities/offer/domain/offer`) |
| `[구조]` | F3, F4 | 계층 바로 아래 파일, slice 루트의 `index.ts` 외 파일, slice 안 4계층 외 폴더(`ui`, `model` 등), `app`·`shared` 안 4계층 폴더, FSD 계층 밖 폴더 |
| `[의존방향]` | F5, F8 | slice 안 금지 방향(presentation → infrastructure, domain → application 등), presentation·application의 `shared/api` import |
| `[외부의존]` | F6 | domain의 `react`·`react-router` import, `window`·`document`·`localStorage`·`import.meta.env` 사용, `shared/lib` 외 shared import |
| `[fetch위치]` | F8 | `shared/api` 밖의 `fetch(` 호출 |
| `[하드코딩색]` | F12 | `.ts`·`.tsx`·`.css`의 hex·`rgb()`·`hsl()` 색 값 (`app/styles/tokens.css`, `bundle.css` 복사본은 제외) |

## 검사 범위와 한계
- 경로 해석은 `@/`(= `src/`) 별칭과 상대 경로만 합니다. 다른 별칭을 추가하면 `resolveSpec`을 고칩니다.
- `*.test.ts(x)`·`*.spec.ts(x)`는 `[구조]`와 `[하드코딩색]`만 검사합니다. 테스트는 모킹 때문에 infrastructure를 참조할 수 있습니다.
- `//`·`/* */` 주석 안의 내용은 무시합니다. 문자열 안의 `window.` 같은 글자는 잡힐 수 있으니, 오탐이면 보고서에 "오탐"으로 적습니다. 스크립트를 고쳐 끄지 않습니다(F16).
- 정독이 필요한 규칙(F7 비즈니스 로직 위치, F9 DTO 노출, F10 비동기 상태, F13 문구, F14 명세)은 잡지 못합니다. `fe-architect`·`fe-reviewer`가 판정합니다.

## 위반을 고치는 방법

| 태그 | 고치는 방법 |
| --- | --- |
| `[계층방향]`, `[같은계층]` | 공통 부분을 아래 계층(entities·shared)으로 내리거나, 위 계층(widgets·pages)에서 두 slice를 조립합니다(`fsd-structure` §2). |
| `[공개API]` | 대상 slice의 `index.ts`에 export를 추가하고 그 경로로 import합니다. infrastructure는 공개하지 않습니다. |
| `[구조]` | 파일을 slice 안의 맞는 4계층 폴더로 옮깁니다(`layer-architecture` §1). |
| `[의존방향]` | presentation → infrastructure 호출은 application 훅으로 감쌉니다. |
| `[외부의존]` | 시각은 `now: Date` 인자로, 환경값은 infrastructure·`shared/config`에서 읽어 인자로 넘깁니다. |
| `[fetch위치]` | `shared/api`의 `apiGet`·`apiPost` 등을 infrastructure에서 씁니다(`api-client` §2). |
| `[하드코딩색]` | `var(--accent)` 같은 토큰 변수나 `bundle.css` 클래스로 바꿉니다(`design-system-usage` §2). |
