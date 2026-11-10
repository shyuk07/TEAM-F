# app 계층 설계: 라우터·셸·의존성 조립

- 대상: `app` 계층(`app/router`, `app/layouts`, `app/container.ts`, `main.tsx`)과 이를 받치는 `widgets/owner-nav`, `shared/config/routes.ts`
- 대응 화면: 상점주 O1, O2, O3(라우트 자리만), O4, O6, O11 / 공개 A1(자리만). O12·O5·O7·O8·O9·O10은 이번 범위 밖
- 상태: 설계안 2차. 사용자 확정 결정(D-1, D-2, D-5, Q-1, Q-3, Q-4, Q-5)을 반영했다. 구현을 막는 미결정 항목은 없다(§10).
- 정본: `../../design-system/layout.md`, `screens.md`, `wireframe.html`, `components/TabBar|AppBar/README.md`, `components/bundle.css`, `frontend/.claude/skills/{fsd-structure,layer-architecture,react-implementation,api-client,tdd-workflow,code-annotations}`
- 코드 현황: `src/main.tsx`는 `App`만 렌더, `src/app/App.tsx`는 `BrowserRouter` + 자리표시 `/`, `src/shared/{api,config,lib}` 구현 완료, features·entities·widgets·pages 없음, `tests/`에는 `setup.ts`와 `shared/`뿐

## 1. 계층 배치

| 대상 | 계층·위치 | 이유 |
| --- | --- | --- |
| 라우트 정의 | `app/router/routes.tsx`(배열), `app/router/index.tsx`(`createBrowserRouter`) | `react-implementation` §5 |
| 경로 상수 | `shared/config/routes.ts` | app 라우터, widgets(탭 링크), pages(이동)가 모두 씀. 위 계층이 app을 import할 수 없으므로 shared에 둠 |
| 상점주 셸(프레임 `.app` + 조건부 TabBar + Outlet) | `app/layouts/OwnerLayout.tsx` | 역할별 레이아웃 라우트(`react-implementation` §5) |
| TabBar·TopNav·AccountButton(상점주용 묶음) | `widgets/owner-nav/` | §3 |
| 자리 page | `app/router/placeholders.tsx` | D-8 |
| 의존성 조립 | `app/container.ts` | `layer-architecture` §6.7 |

`app/layouts/`는 용도별 폴더이다. `check_layers.mjs`는 app 아래에서 4계층 이름 폴더만 금지하므로 위반이 아니다(C-3 해소).

## 2. 라우트 표 (경로 확정, D-1)

| 화면 | 경로 | 레이아웃 | TabBar | 요소 | 비고 |
| --- | --- | --- | --- | --- | --- |
| A1 로그인 | `/login` | 없음(공개) | 없음 | 자리 `LoginPlaceholder` | auth 설계 때 교체 |
| O1 오늘·픽업 | `/owner/today` | OwnerLayout | 있음(오늘 활성) | 자리 page 「O1 오늘」 | |
| O2 할인 관리 | `/owner/offers` | OwnerLayout | 있음(할인 활성) | 자리 page 「O2 할인」 | |
| O3 할인 등록 | `/owner/offers/new` | OwnerLayout | 없음 | 자리 page 「O3 할인 등록」 | 라우트만. 쿼리 형식은 O3 설계 때(D-6) |
| O4 매장·상품 | `/owner/store` | OwnerLayout | 있음(매장 활성) | 자리 page 「O4 매장」 | products 구현 시 교체 |
| O6 상품 등록 | `/owner/products/new` | OwnerLayout | 없음 | 자리 page 「O6 상품 등록」 | |
| O11 상품 수정 | `/owner/products/:productId` | OwnerLayout | 없음 | 자리 page 「O11 상품 수정」 + `productId` 표시 | `useParams`로 읽음 |
| `/owner` | 리다이렉트 → `/owner/today` | | | `<Navigate replace>` | 최종 이동은 auth가 결정 |
| `/` | 기존 `HomePlaceholder` 유지 | 없음 | | D-7 | |
| 그 외 `*` | 리다이렉트 → `/` | 없음 | | `<Navigate to="/" replace>` | Q-4 확정. NotFound 문구는 나중 |

- 하위 화면(O3·O6·O11)은 TabBar가 없고, PC(720px 이상)에서는 TopNav가 AppBar 안에 보인다.
- 라우트 요소는 `pages` 공개 API만 쓴다. 이번 단계 자리 page는 `app/router/placeholders.tsx`에 둔다(D-8).
- `routes`(배열)를 export하고 `createBrowserRouter(routes)`는 `app/router/index.tsx`에서만 호출한다. 테스트는 같은 `routes`를 `createMemoryRouter`에 넣는다.
- 탭 표시 여부는 라우트 `handle: { tabBar: true }`로 정한다.

## 3. 상점주 셸 구조와 부품 위치

### 3.1 구성

```text
OwnerLayout (app/layouts)                  <div className="app"> 프레임
 ├─ <Outlet />                             page가 AppBar + .body (+ CtaBar)를 그림
 └─ route handle.tabBar === true 일 때 <OwnerTabBar />   (마지막 형제)
```

- 모바일 TabBar ↔ PC TopNav 전환은 `bundle.css`의 `@container app (min-width:720px)`가 한다(`.nav`는 기본 `display:none`, 720px 이상에서 `flex`, `.tabs`는 반대). 미디어 쿼리를 새로 쓰지 않고, TabBar와 TopNav를 항상 둘 다 렌더한다.
- AppBar는 page가 그린다. 그 안의 nav·계정 버튼은 `widgets/owner-nav`가 준다(slot 방식, D-3).
- 활성 탭 판정은 domain 순수 함수 `activeOwnerTab(pathname)`(F7).
- 하위 화면 활성 항목(Q-3 확정): `/owner/offers/new` → 「할인」, `/owner/products/new`, `/owner/products/:id` → 「매장」. 이 때 TabBar는 없고 TopNav 활성만 표시된다.

### 3.2 `widgets/owner-nav` (D-2 확정)

| 계층 | 파일 | export |
| --- | --- | --- |
| domain | `domain/ownerTabs.ts` | `OwnerTabKey`, `OWNER_TABS`, `activeOwnerTab` |
| presentation | `presentation/OwnerTabBar.tsx`, `OwnerTopNav.tsx`, `OwnerAccountButton.tsx` | 컴포넌트 3개 |

- 탭 라벨은 `components/TabBar/README.md`: 오늘·할인·매장.
- 마크업(Q-5 확정, `wireframe.html:587`·`:606` 기준, 스타일은 `bundle.css` `.nav`/`.tabs`/`.acct`):
  - TopNav: `<span class="nav">` 안에 항목마다 활성은 `<b>`, 비활성은 `<span>`. 각 항목 안에 `<Link to=경로>라벨</Link>`.
  - TabBar: `<div class="tabs">` 안에 같은 구성.
  - 현재 항목의 `<Link>`에 `aria-current="page"`를 붙인다.
  - AccountButton: `<button type="button" class="acct">계정</button>`(접근 이름 「계정」).
- `OwnerAccountButton`은 동작이 없다(D-4, 남길 주석 §9 A-2).
- application·infrastructure는 만들지 않는다(F4). 공개 API: `OwnerTabBar`, `OwnerTopNav`, `OwnerAccountButton`, `activeOwnerTab`, `OWNER_TABS`, `OwnerTabKey`.

## 4. `app/container.ts` (D-5 확정)

- 빈 `new Container([])`로 시작하고, 영역 wiring은 만들 때 한 줄씩 추가한다. 주석에는 `wireXxx`를 코드로 쓰지 않는다.
- `main.tsx`에서 모듈 최상위 1회 `const container = createContainer()`. `createContainer`는 매번 새 `Container`를 반환한다(싱글턴 없음).
- `main.tsx`: `<StrictMode><DepsProvider container={container}><App /></DepsProvider></StrictMode>`.
- 영역이 추가될 때 `tests/app/container.test.ts` 토큰 목록을 같은 커밋에서 늘린다.

## 5. 인증 가드·401 처리

| 항목 | 이번 | 미룸 |
| --- | --- | --- |
| `OwnerLayout` 가드 | 항상 통과. 자리만 둔다(D-9) | auth 영역 |
| 인증 Context | 만들지 않음 | auth 설계 |
| `SessionStore` 접근 | app은 `tokenStorage`를 직접 호출하지 않는다(F17) | `entities/session` |
| 401 처리 | 하지 않음 | auth |
| 로그인 후 돌아가기 | 미정 | Q-2: auth 설계 때 |

## 6. 정합 이슈

| C | 내용 | 상태 |
| --- | --- | --- |
| C-1 | `layer-architecture` §6.7 container 예시는 7개 wiring을 모두 import해 지금은 `tsc`가 깨진다. D-5 확정 운영은 "만든 영역만 추가" | 정본 §6.7 예시를 오케스트레이터가 갱신 예정 |
| C-2 | `react-implementation` §5는 `createBrowserRouter`, 현재 코드는 `<BrowserRouter><Routes>` | 구현 때 `createBrowserRouter`로 교체 |
| C-3 | `app/layouts/`의 `[구조]` 허용 여부 | 해소: app 아래 4계층 이름 폴더만 금지(오케스트레이터 확인) |
| C-4 | 가드 항상 통과 상태로는 배포하지 않는다 | 남길 주석 A-1(FIXME)로 추적 |
| C-5 | `components/`에 `TopNav`·`AccountButton` README가 없다 | 해소: Q-5 확정으로 `wireframe.html` 기준 |
| C-6 | page는 AppBar와 `.body`를 fragment로 반환해야 `.app` 안 형제가 맞는다 | 구현 규칙 |
| C-7 | O1의 "백엔드 필요" 두 항목은 범위 밖이므로 자리 page만 둔다 | 범위 제한 |

## 7. 결정 표

| D | 항목 | 값 | 상태 | 근거 | 구현을 막는가 |
| --- | --- | --- | --- | --- | --- |
| D-1 | 경로 | §2 표 | 확정 | 사용자 | 아니오 |
| D-2 | 셸 위치 | `widgets/owner-nav` + `app/layouts/OwnerLayout` | 확정 | 사용자 | 아니오 |
| D-3 | AppBar와 nav 연결 | page가 AppBar를 그리고 nav·계정은 slot(`shared/ui/AppBar`는 구현 전이라 이번 범위에서는 자리 page가 직접 `.bar` 마크업을 쓴다) | 임시 | 제목·← 유무가 화면마다 다름 | 아니오. AppBar 컴포넌트 구현 때 확정 |
| D-4 | 계정 버튼 | 동작 없음, O8은 auth 단계 | 임시 | 사용자 결정(O4 계정 행 자리만)을 확장 | 아니오 |
| D-5 | container | 빈 배열, 영역 생길 때 한 줄씩 | 확정 | 사용자 | 아니오 |
| D-6 | O3 쿼리 | `/owner/offers/new`, 상품 전달 방식은 O3 설계 | 확정(경로) / 쿼리 미정 | 사용자 | 아니오 |
| D-7 | `/` | `HomePlaceholder` 유지 | 임시 | 고객 홈 미설계 | 아니오 |
| D-8 | 자리 page 위치 | `app/router/placeholders.tsx` | 임시 | pages 미존재 | 아니오 |
| D-9 | 가드 | `OwnerLayout`에서 가드, 항상 통과 | 임시 | auth 미설계 | 아니오 |
| D-10 | 라우터 API | `createBrowserRouter(routes)` + 테스트용 `createMemoryRouter(routes)` | 임시 | `react-implementation` §5 | 아니오 |
| D-11 | 토큰 보관 | `localStorage` | 확정 | `api-client` §2.1 | |
| D-12 | 테스트 위치 | `tests/` | 확정 | `react-implementation` §7 | |
| D-13 | DI 도구 | `shared/lib/di.ts` + `DepsProvider.tsx` | 확정 | 구현 완료 | |
| D-14 | O4 폐점 링크(O7)·계정 행 | 자리만 | 확정 | 사용자 | |
| D-15 | 자리 page 문구 | 화면 ID 표시(예: 「O1 오늘」). 개발용 임시값이며 해당 화면 구현 때 교체 | 확정 | 사용자(Q-1) | |
| D-16 | 정의되지 않은 경로 | `/`로 리다이렉트 | 확정 | 사용자(Q-4) | |

## 8. 골격과 테스트

### 8.1 골격 (`tdd-workflow` §3)

그대로 만들 것(타입·상수·경로 상수·라우트 배열·공개 API):

| 파일 | 내용 |
| --- | --- |
| `src/shared/config/routes.ts` | `export const ROUTES = { login: '/login', home: '/', owner: '/owner', ownerToday: '/owner/today', ownerOffers: '/owner/offers', ownerOfferNew: '/owner/offers/new', ownerStore: '/owner/store', ownerProductNew: '/owner/products/new', ownerProduct: (id: string) => \`/owner/products/${encodeURIComponent(id)}\` } as const`, `ROUTE_PATTERNS`(`ownerProduct: '/owner/products/:productId'`) |
| `src/widgets/owner-nav/domain/ownerTabs.ts` | `export type OwnerTabKey = 'today' \| 'offers' \| 'store'`, `export type OwnerTab = { key; label; path }`, `OWNER_TABS` 실제 값. `activeOwnerTab(pathname: string): OwnerTabKey \| null`은 본문을 `void pathname; throw new Error('not implemented: activeOwnerTab')`로 비움 |
| `src/widgets/owner-nav/index.ts` | §3.2 공개 API |
| `src/app/router/routes.tsx` | `export const routes: RouteObject[]` 실제 구조(경로·`handle.tabBar`·리다이렉트·`*`)와 `element`로 자리 page·`OwnerLayout` 연결 |
| `src/app/router/index.tsx` | `export const router = createBrowserRouter(routes)` |
| `src/app/container.ts` | `createContainer()`는 실제 구현(`new Container([])`)이 간단하므로 그대로 만들고 빈 배열 반환. 테스트가 Green인 항목은 §8.3 참고 |

본문을 비울 것(컴포넌트·함수):

| 파일 | export | 골격 본문 |
| --- | --- | --- |
| `widgets/owner-nav/presentation/OwnerTabBar.tsx` | `OwnerTabBar()` | `return null` |
| `…/OwnerTopNav.tsx` | `OwnerTopNav()` | `return null` |
| `…/OwnerAccountButton.tsx` | `OwnerAccountButton()` | `return null` |
| `app/layouts/OwnerLayout.tsx` | `OwnerLayout()` | `return null` |
| `app/router/placeholders.tsx` | `LoginPlaceholder`, `OwnerTodayPlaceholder`, `OwnerOffersPlaceholder`, `OwnerOfferNewPlaceholder`, `OwnerStorePlaceholder`, `OwnerProductNewPlaceholder`, `OwnerProductEditPlaceholder`, `HomePlaceholder`(기존 코드 이동) | `return null` (`HomePlaceholder`는 기존 그대로) |
| `app/App.tsx` | `App()` | `RouterProvider router={router}`로 교체(골격 단계에서 가능) |
| `main.tsx` | | `DepsProvider` 감싸기 |

골격 파일 수: 신규 11개(`routes.ts`, `ownerTabs.ts`, `owner-nav/index.ts`, 컴포넌트 3, `OwnerLayout.tsx`, `placeholders.tsx`, `routes.tsx`, `router/index.tsx`, `container.ts`) + 수정 2개(`App.tsx`, `main.tsx`).

### 8.2 테스트 목록 (`tdd-workflow` §2, 위치 `tests/` 아래)

**(a) `tests/widgets/owner-nav/domain/ownerTabs.test.ts` — domain (7개 대상 묶음, 케이스 15)**

| 입력 | 기대 |
| --- | --- |
| `/owner/today` | `'today'` |
| `/owner/offers` | `'offers'` |
| `/owner/offers/` | `'offers'` |
| `/owner/offers/new` | `'offers'` (Q-3) |
| `/owner/store` | `'store'` |
| `/owner/products/new` | `'store'` (Q-3) |
| `/owner/products/p1` | `'store'` (Q-3) |
| `/owner` | `null` |
| `/login` | `null` |
| `/` | `null` |
| `/owner/offersx` (접두사 비슷함) | `null` |
| `OWNER_TABS` 길이·라벨 순서 | 3, 오늘·할인·매장 |
| `OWNER_TABS` 경로 | `ROUTES.ownerToday`, `ownerOffers`, `ownerStore` 순서 |

문구 정본: `components/TabBar/README.md`.

**(b) `tests/widgets/owner-nav/presentation/OwnerNav.test.tsx` — 컴포넌트 (케이스 8)**
- `MemoryRouter` 초기 `/owner/offers`에서 `OwnerTabBar`: 링크 3개(이름 오늘·할인·매장), `href`는 `ROUTES` 값과 같다.
- 같은 경로에서 「할인」 링크만 `aria-current="page"`이고 나머지 두 링크에는 없다.
- `/owner/products/p1`에서 `OwnerTabBar`의 「매장」 링크가 `aria-current="page"`.
- `OwnerTopNav`: 같은 3항목·`href`, 현재 항목에만 `aria-current="page"`. `/owner/offers/new`에서 「할인」이 활성.
- `/login`에서는 어느 항목에도 `aria-current`가 없다.
- `OwnerAccountButton`: 접근 이름 「계정」인 button이고, 클릭해도 URL이 바뀌지 않는다.

**(c) `tests/app/router/routes.test.tsx` — 라우트 (`createMemoryRouter(routes)` + `DepsProvider(new Container([]))`, 케이스 12)**

| 초기 경로 | 기대 |
| --- | --- |
| `/owner` | `router.state.location.pathname === '/owner/today'` |
| `/owner/today` | 제목 「O1 오늘」, TabBar 링크 3개 |
| `/owner/offers` | 제목 「O2 할인」, TabBar 있음 |
| `/owner/store` | 제목 「O4 매장」, TabBar 있음 |
| `/owner/offers/new` | 제목 「O3 할인 등록」, TabBar 없음 |
| `/owner/products/new` | 제목 「O6 상품 등록」, TabBar 없음 |
| `/owner/products/p1` | 제목 「O11 상품 수정」과 `p1` 표시, TabBar 없음 |
| `/login` | 로그인 자리 렌더, `href="/owner/today"` 링크 없음(셸 없음) |
| `/` | 「마감 직전」 제목(`HomePlaceholder`) |
| `/nope` | 경로가 `/`로 바뀐다 |
| `/owner/nope` | 경로가 `/`로 바뀐다 |
| 가드 | 쓰지 않는다(항상 통과이므로) |

기준: 자리 page 문구는 D-15(개발용 임시값). TabBar 유무는 「오늘」 링크 수로 단언(탭 화면 2개: TabBar+TopNav, 하위 화면 1개: TopNav만).

**(d) `tests/app/layouts/OwnerLayout.test.tsx` — 레이아웃 (케이스 4)**
- `handle.tabBar: true`인 테스트용 라우트: TabBar가 Outlet 내용 뒤(`nextSibling` 관계)에 있다.
- `handle.tabBar` 없음: TabBar 링크 없음.
- 프레임 요소에 `app` 클래스가 있다.
- 탭 화면에서 「오늘」 링크가 TabBar와 TopNav 두 곳에 있어 총 2개다(전환은 CSS 몫).
- 720px 레이아웃은 jsdom에서 검증할 수 없다 → fe-qa E2E에서 뷰포트 두 가지로 확인.

**(e) `tests/app/container.test.ts` — 조립 (케이스 3)**
- `createContainer()`가 예외 없이 `Container` 인스턴스를 반환한다(골격에서 이미 통과할 수 있다. Red 판정에서 "통과한 테스트"로 보고하고 허용).
- 두 번 호출하면 서로 다른 인스턴스.
- 토큰 목록 배열을 순회해 `get`이 던지지 않는지 확인(현재 빈 배열). 영역이 추가될 때마다 같은 커밋에서 토큰을 추가한다는 주석을 둔다.

**(f) `tests/app/App.test.tsx` — 앱 (케이스 1)**
- `DepsProvider`로 감싼 `App`이 `/`에서 오류 없이 「마감 직전」을 보여 준다.

대상별 합계: domain 13(묶음 1파일), 컴포넌트 6, 라우트 12(가드 제외 11), 레이아웃 4, 조립 3, 앱 1. E2E는 이번 설계 범위 밖(720px 전환은 fe-qa).

## 9. 남길 작업 주석 (`layer-architecture` §5 항목 13, `code-annotations`)

| ID | 위치 | 태그 | 원문 초안 |
| --- | --- | --- | --- |
| A-1 | `app/layouts/OwnerLayout.tsx` 가드 자리 | FIXME | `// FIXME: 인증 가드가 항상 통과한다. 로그인하지 않아도 상점주 화면이 열린다.`<br>`//   왜: auth 영역 구현 전이라 세션을 확인할 수단이 없다 (docs/design/frontend/app-shell.md D-9)`<br>`//   언제: auth 구현 시, 늦어도 배포 전` |
| A-2 | `widgets/owner-nav/presentation/OwnerAccountButton.tsx` | TODO | `// TODO: 계정 버튼을 눌러도 아무 동작이 없다. O8(계정 메뉴)로 이동하게 연결한다.`<br>`//   왜: O8은 auth 영역 몫이라 이번 범위 밖 (docs/design/frontend/app-shell.md D-4, 사용자: 계정 행은 자리만)`<br>`//   언제: auth 구현 시` |
| A-3 | `app/router/placeholders.tsx` 파일 맨 위 | TODO | `// TODO: 자리 page가 화면 ID만 표시한다. 정식 page(pages/*)로 교체하고 이 파일을 지운다.`<br>`//   왜: 문구 정본이 없는 개발용 표기다 (docs/design/frontend/app-shell.md D-8, D-15)`<br>`//   언제: O1 구현 시, O2 구현 시, O3 구현 시, O4 구현 시, O6 구현 시, O11 구현 시 (각 화면의 자리 page를 교체)` |
| A-4 | `app/container.ts` | TODO | `// TODO: 영역 wiring이 없어 빈 배열이다. 영역을 만들 때 wire<영역>() 한 줄을 추가한다.`<br>`//   왜: features 영역이 아직 없다 (docs/design/frontend/app-shell.md D-5)`<br>`//   언제: auth 구현 시` |
| A-5 | `app/router/routes.tsx` 로그인 라우트 | TODO | `// TODO: 로그인 후 원래 화면으로 돌아가는 방식을 정한다.`<br>`//   왜: from state·쿼리 중 어느 쪽인지 미정 (docs/design/frontend/app-shell.md Q-2)`<br>`//   언제: auth 구현 시` |
| A-6 | `app/router/routes.tsx` `*` 라우트 | TODO | `// TODO: 정의되지 않은 경로를 /로 보낸다. 전용 NotFound 화면과 문구를 정한다.`<br>`//   왜: 문구 정본이 없다 (docs/design/frontend/app-shell.md D-16)`<br>`//   언제: 결정 후 (사용자: NotFound 문구)` |

A-1은 `list --tag FIXME`에 남으므로 배포 전 0건이어야 한다. `open-issues:` 주석 대상은 이번 범위에 없다.

## 10. 질문 목록

| Q | 내용 | 상태 |
| --- | --- | --- |
| Q-1 | 자리 page 문구 | 해결: 화면 ID 표시(D-15). 해당 화면 구현 때 교체 |
| Q-2 | 가드의 `/login` 이동과 돌아가기 방식 | 미결정. auth 설계 때 정한다. 구현을 막지 않음 |
| Q-3 | 하위 화면 TopNav 활성 항목 | 해결: O3 → 할인, O6·O11 → 매장 |
| Q-4 | NotFound | 해결: 정의되지 않은 경로는 `/`로 보낸다. 문구는 나중 |
| Q-5 | TopNav·AccountButton 마크업과 `aria-current` | 해결: `wireframe.html` 기준, 현재 항목에 `aria-current="page"` |
| Q-6 | D-1, D-2, D-5 확정 | 해결: 모두 확정. 남은 임시값(D-3, D-4, D-7~D-10)은 구현을 막지 않는다 |
