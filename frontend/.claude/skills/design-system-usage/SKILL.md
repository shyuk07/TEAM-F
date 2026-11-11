---
name: design-system-usage
description: 마감 직전 프론트엔드에서 디자인 시스템(../docs/design-system)을 쓰는 규칙입니다. tokens.css·bundle.css를 src/app/styles/에 복사해 두고 원본과 동기화하는 절차와 차이 확인 명령, 토큰 변수·컴포넌트 클래스만 쓰는 규칙, 19종 컴포넌트를 React 컴포넌트로 감싸는 위치(shared/ui), 720px 컨테이너 반응형 클래스(.mob·.dk·.hide 등)·역할별 셸 계약(높이·본문 스크롤·오버레이)·실제 요소 기본 모양, 화면 문구·상태 문구를 screens.md·content.md·states.md와 맞추는 방법, 글꼴 로드를 다룹니다. 화면이나 UI 컴포넌트를 구현할 때, 디자인 시스템 파일이 바뀌었을 때, 색·간격·문구를 확인할 때 사용합니다.
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

### 3.1 셸·반응형 클래스 (bundle.css에 이미 있는 것)
새 클래스나 인라인 스타일로 만들기 전에 아래 표와 `bundle.css`를 먼저 찾습니다. "디자인 시스템에 없다"고 판단하거나 주석에 적기 전에 `grep -n "<클래스>" src/app/styles/bundle.css`로 확인합니다.

| 클래스 | 720px 미만 | 720px 이상 | 쓰는 곳 |
| --- | --- | --- | --- |
| `.tabs` / `.nav` | 하단 탭 보임 / nav 숨김 | 반대 | 셸이 둘 다 렌더 |
| `.cta` / `.dk` | 하단 고정 바 보임 / 숨김 | 반대 | 주 버튼을 두 곳에 같은 동작으로 둔다 |
| `.mob` | 보임 | 숨김 | 모바일에만 있는 행·링크(예: 계정 행, 본문 안 ←) |
| `.hide` | 숨김 | 보임 | 표의 넓은 화면 전용 칸 |
| `.split`, `.split.r`, `.split.h` | 1열 | 300px\|1fr, 1fr\|340px, 1fr\|1fr | 목록+패널, 폼 두 열 |
| `.tr` | 접힘 줄 | 5열 표 | 관리자·상점주 목록 |

- 고객 셸은 프레임 폭이 420px이라 720px 규칙이 켜지지 않습니다. PC에서도 고객 화면은 모바일 배치(`.tabs`·`.cta`)가 정상입니다.

### 3.2 셸 계약 (layout.md "화면 골격")
- 앱 높이는 화면 높이, 스크롤은 `.body` 하나만. 이 동작은 `bundle.css`의 `.app`·`.body` 규칙이 맡습니다. 레이아웃·page에서 `height`·`overflow`·`position: fixed`를 따로 주지 않습니다. 바가 고정되지 않으면 우회하지 말고 보고합니다.
- `.app` 안의 자식 순서는 `.bar` → `.body`(또는 오버레이 `.dim`) → `.cta` → `.tabs`입니다. `.bar`·`.cta`·`.tabs`는 `.body` 밖에 둡니다(안에 두면 함께 스크롤됩니다).
- 셸이 `.app`을 그리고 page가 또 `.app`을 그리는 중첩을 만들 때는 바깥 프레임(flex column)이 안쪽 `.app`에도 남은 높이를 주는지 확인합니다. 같은 역할의 다른 셸이 쓰는 방식을 따릅니다.
- 오버레이는 본문 자리에 뜹니다(`.dim` + `.sheet`). `.dim`을 `.body`와 나란히 추가하면 본문과 높이를 나눠 가지므로, 열려 있는 동안 `.body` 자리를 대신하게 그립니다.

### 3.3 와이어프레임에 없는 실제 요소
와이어프레임·`preview.html`은 대부분 `div`로 그려져 있어 실제 `<a>`·`<button>`·`<input>`·`<textarea>`의 브라우저 기본 모양(파란 밑줄, 회색 버튼, 좁은 입력칸)이 드러나지 않습니다. 실제 요소로 바꿔 쓸 때는 다음을 지킵니다.
- 요소 기본 모양 제거는 `bundle.css`가 맡습니다. 화면마다 인라인 스타일로 지우지 않습니다.
- 클래스를 실제 요소에 붙였을 때 모양이 preview와 다르면(예: `.in`을 붙인 `<input>`이 폼 폭을 채우지 않음) 화면에서 우회하지 말고 보고합니다. 원본 수정 여부는 사용자가 정합니다(§1).
- jsdom 테스트는 레이아웃을 계산하지 않습니다. 모양은 `qa-verification` §4.1 레이아웃 실측으로만 확인됩니다.

## 4. 문구 (F13)
- 화면 제목, 버튼, 안내, 오류 문구는 `screens.md`의 해당 화면 문구를 **그대로** 씁니다. 말을 다듬지 않습니다.
- 숫자·금액·시간 표기는 `content.md`를 따르고, domain 함수로 만듭니다(예: `formatWon`, `formatMinutesLeft`).
- 상태 enum → 한국어 문구는 `states.md` 표를 domain의 상수 표로 옮겨 씁니다. 고객·상점주 화면에는 한국어만, 관리자 화면에만 상태 코드를 함께 씁니다.
- `open-issues.md`에 있는 항목은 거기 적힌 임시 동작으로 구현하고, 코드에 `// open-issues: <항목>` 주석을 남깁니다(형식은 `code-annotations` §1~§2).

## 5. 화면 구현 전 확인 목록
1. 화면 ID와 `screens.md` 명세(컴포넌트, 문구, 동작 메모)
2. `api-map.md`의 엔드포인트(`api-client` §5)
3. 상태별 표시: 로딩·빈·에러·권한 없음(`states.md`, E1)
4. 되돌리기 어려운 동작이면 확인 화면 여부
5. 720px 이상에서 CtaBar → 패널 버튼(`.dk`) 전환
6. 모바일 전용·PC 전용 요소의 클래스(`.mob`·`.hide`·`.dk`, §3.1)와 셸 계약(§3.2)
7. 실제 `<a>`·`<button>`·`<input>`을 쓰는 곳의 모양 확인 계획(§3.3)
