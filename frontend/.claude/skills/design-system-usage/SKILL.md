---
name: design-system-usage
description: 마감 직전 프론트엔드에서 디자인 시스템(../docs/design-system)을 쓰는 규칙입니다. tokens.css·bundle.css를 src/app/styles/에 복사해 두고 원본과 동기화하는 절차와 차이 확인 명령, 토큰 변수·컴포넌트 클래스만 쓰는 규칙, 19종 컴포넌트를 React 컴포넌트로 감싸는 위치(shared/ui), 720px 컨테이너 반응형·역할별 셸, 화면 문구·상태 문구를 screens.md·content.md·states.md와 맞추는 방법, 글꼴 로드를 다룹니다. 화면이나 UI 컴포넌트를 구현할 때, 디자인 시스템 파일이 바뀌었을 때, 색·간격·문구를 확인할 때 사용합니다.
---

# 디자인 시스템 사용

정본은 `../docs/design-system/`입니다. 이 스킬은 **프론트 코드에서 그것을 어떻게 쓰는가**만 정합니다. 규칙 ID(F12, F13)는 `frontend-invariants`가 정본입니다.

읽는 순서: `../docs/design-system/README.md` → `layout.md` → `screens.md`의 해당 화면 → `components/<이름>/README.md` → `content.md`·`states.md`

## 1. CSS 복사본 관리

| 원본 | 복사본 |
| --- | --- |
| `../docs/design-system/tokens.css` | `src/app/styles/tokens.css` |
| `../docs/design-system/components/bundle.css` | `src/app/styles/bundle.css` |

- 복사본은 **직접 고치지 않습니다**. 값이 틀리면 원본(`tokens.json`과 와이어프레임)을 고치고 다시 복사합니다. 원본 `tokens.css`도 생성 파일입니다(`../docs/design-system/HOW-TO-USE.md`).
- 불러오는 순서는 `tokens.css` → `bundle.css`입니다. `src/main.tsx`(또는 `app/styles/index.css`)에서 이 순서로 import합니다.

복사와 확인은 `scripts/sync_styles.mjs`로 합니다. Node만 있으면 Windows PowerShell·macOS·Linux에서 같은 명령입니다(`frontend` 폴더에서 실행).

```powershell
node .claude/skills/design-system-usage/scripts/sync_styles.mjs copy    # 원본 → src/app/styles/ 다시 복사
node .claude/skills/design-system-usage/scripts/sync_styles.mjs check   # 같은지 확인 (다르면 종료코드 1)
```
- `check`는 줄바꿈(CRLF/LF) 차이를 같은 내용으로 봅니다. Windows에서 git이 줄바꿈을 바꿔도 불일치로 나오지 않습니다.
- 차이가 있으면 "복사본 불일치"로 보고합니다. 어느 쪽이 맞는지 판단하지 않고, 다시 복사할지 사용자에게 묻습니다.
- 검증 담당(`fe-qa`)은 `check`만 실행합니다. `copy`는 사용자가 요청했을 때 개발자가 실행합니다.

## 2. 색·간격·모양 (F12)
- 색은 토큰 변수만 씁니다: `var(--fg)`, `var(--accent)` 등. hex·`rgb()`를 쓰지 않습니다(`layer-check`의 `[하드코딩색]`).
- **accent는 돈·시간·오류에만**, **ok는 성공·정상에만** 씁니다. 선택 상태는 `fg`입니다(`README.md` 원칙).
- 간격은 `--s1`~`--s5`, 모서리·그림자도 토큰만 씁니다.
- `bundle.css`에 없는 컴포넌트 클래스를 새로 만들지 않습니다. 필요하면 만들지 말고 보고합니다.
- 화면 고유 CSS가 꼭 필요하면 그 slice의 presentation에 CSS Module(`*.module.css`)로 두고 토큰 변수만 씁니다.

## 3. 컴포넌트와 레이아웃
- 디자인 시스템 컴포넌트 19종(Button, Chip, Input, Stepper, OfferCard, BottomSheet 등)은 마크업과 클래스를 감싸는 React 컴포넌트로 `shared/ui/`에 둡니다. 업무를 모르는 것만 둡니다.
  - 업무 데이터를 받는 것(예: `Offer`를 받는 OfferCard)은 `entities/offer/presentation/`에 두고, 내부에서 `shared/ui`와 클래스를 씁니다.
- 마크업과 클래스 이름은 `components/<이름>/preview.html`과 같게 씁니다. 상태 클래스(disabled, selected 등)도 그 README를 따릅니다.
- 반응형 기준은 화면 폭이 아니라 **앱 컨테이너 폭 720px**입니다(`@container app`). `bundle.css`가 처리하므로 미디어 쿼리를 새로 쓰지 않습니다.
- 화면 골격(AppBar → 본문 → CtaBar → TabBar), 역할별 셸은 `layout.md`를 따르고 `app`의 레이아웃 라우트로 구현합니다(`react-implementation` §5).
- 글꼴(IBM Plex Sans KR, IBM Plex Mono)은 `index.html`에서 Google Fonts로 불러옵니다.

## 4. 문구 (F13)
- 화면 제목, 버튼, 안내, 오류 문구는 `screens.md`의 해당 화면 문구를 **그대로** 씁니다. 말을 다듬지 않습니다.
- 숫자·금액·시간 표기는 `content.md`를 따르고, domain 함수로 만듭니다(예: `formatWon`, `formatMinutesLeft`).
- 상태 enum → 한국어 문구는 `states.md` 표를 domain의 상수 표로 옮겨 씁니다. 고객·상점주 화면에는 한국어만, 관리자 화면에만 상태 코드를 함께 씁니다.
- `open-issues.md`에 있는 항목은 거기 적힌 임시 동작으로 구현하고, 코드에 `// open-issues: <항목>` 주석을 남깁니다.

## 5. 화면 구현 전 확인 목록
1. 화면 ID와 `screens.md` 명세(컴포넌트, 문구, 동작 메모)
2. `api-map.md`의 엔드포인트(`api-client` §5)
3. 상태별 표시: 로딩·빈·에러·권한 없음(`states.md`, E1)
4. 되돌리기 어려운 동작이면 확인 화면 여부
5. 720px 이상에서 CtaBar → 패널 버튼(`.dk`) 전환
