# app 계층 설계: 라우터·셸·의존성 조립

- 대상: `app` 계층(`app/router`, `app/layouts`, `app/container.ts`, `main.tsx`)과 이를 받치는 `widgets/owner-nav`, `shared/lib/routes.ts`
- 대응 화면: 상점주 O1, O2, O3(라우트 자리만), O4, O6, O11 / 공개 A1(자리만). O12·O5·O7·O8·O9·O10은 이번 범위 밖
- 차수 변경(2026-11-11): 4차에 D-30(오버레이 `[hidden]` 전역 규칙, 사용자 확정)과 C-17·C-18 추가. 인라인 `display:none` 편차 해소.
- 차수 변경(2026-11-11, 5차): 남은 결정 기록. 사용자 위임("남은 작업은 오케스트레이터 판단", 출처 표기 "오케스트레이터 판단(사용자 위임 2026-11-11)")으로 D-22 변경, D-28 확정, D-29 변경(`.dk` 복사본 삭제), D-31~D-36 추가, Q-8·Q-11·Q-12·Q-13 해결, A-7·A-9 철회, C-13 해소·C-19·C-20 추가. 새 절: §11.13(고객 C10·C1a를 `Overlay`로 이전), §12.12(`.dk` 삭제로 바뀌는 테스트).
- 상태: 설계안 5차(§11.13, §12.12 추가). 4차:(§11 오버레이 결정 확정, §12 프레임 바깥 배경·A1~A3 셸 추가). 이전: 3차. 사용자 확정 결정(D-1, D-2, D-5, D-17, Q-1, Q-3, Q-4, Q-5)을 반영했다. 구현을 막는 미결정 항목은 없다(§10).
- 정본: `../../design-system/layout.md`, `screens.md`, `wireframe.html`, `components/TabBar|AppBar/README.md`, `components/bundle.css`, `frontend/.claude/skills/{fsd-structure,layer-architecture,react-implementation,api-client,tdd-workflow,code-annotations}`
- 코드 현황: `src/main.tsx`는 `App`만 렌더, `src/app/App.tsx`는 `BrowserRouter` + 자리표시 `/`, `src/shared/{api,config,lib}` 구현 완료, features·entities·widgets·pages 없음, `tests/`에는 `setup.ts`와 `shared/`뿐

## 1. 계층 배치

| 대상 | 계층·위치 | 이유 |
| --- | --- | --- |
| 라우트 정의 | `app/router/routes.tsx`(배열), `app/router/index.tsx`(`createBrowserRouter`) | `react-implementation` §5 |
| 경로 상수 | `shared/lib/routes.ts` | app 라우터, widgets(탭 링크·domain), pages(이동)가 모두 씀. 위 계층이 app을 import할 수 없으므로 shared에 두고, domain이 쓸 수 있도록 `shared/lib`에 둠(F6, D-17) |
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
| O0 상점 개설 | `/owner/start` | OwnerLayout | 없음 | `pages/owner-start` `OwnerStartPage` | stores.md D-1에 추가(C-5 해소) |
| O7 상점 폐점 | `/owner/store/close` | OwnerLayout | 없음 | `pages/store-close` `StoreClosePage` | stores.md D-12에 추가(C-5 해소) |
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
| C-1 | `layer-architecture` §6.7 container 예시는 7개 wiring을 모두 import해 지금은 `tsc`가 깨진다. D-5 확정 운영은 "만든 영역만 추가" | 해소: 오케스트레이터가 `layer-architecture` §6.7에 '빈 배열로 시작, 영역 wiring 생성 시 한 줄씩 추가' 안내를 반영함(커밋 eb9d163) |
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
| D-14 | O4 폐점 링크(O7)·계정 행 | 자리만 → 폐점 링크 부분은 stores.md D-12로 대체(구현 시 해소): stores 구현 시 O4 자리 page에 「상점 폐점」 링크(`/owner/store/close`)를 채운다. 계정 행은 자리 그대로 | 확정 | 사용자(stores.md Q-5) | |
| D-15 | 자리 page 문구 | 화면 ID 표시(예: 「O1 오늘」). 개발용 임시값이며 해당 화면 구현 때 교체 | 확정 | 사용자(Q-1) | |
| D-16 | 정의되지 않은 경로 | `/`로 리다이렉트 | 확정 | 사용자(Q-4) | |
| D-17 | 경로 상수(`ROUTES`, `ROUTE_PATTERNS`) 위치 | `src/shared/lib/routes.ts` | 확정 | 사용자 결정. 골격 단계 layer-check 위반 `[외부의존] widgets/owner-nav/domain/ownerTabs.ts:1 domain → shared/config (F6)`: domain은 shared 중 `shared/lib`만 쓸 수 있고, 경로 상수는 업무 로직 없는 순수 값이다. 검토했으나 채택하지 않은 안: 탭 목록을 인자로 주입, F6 예외 인정 | |

## 8. 골격과 테스트

### 8.1 골격 (`tdd-workflow` §3)

그대로 만들 것(타입·상수·경로 상수·라우트 배열·공개 API):

| 파일 | 내용 |
| --- | --- |
| `src/shared/lib/routes.ts` | `export const ROUTES = { login: '/login', home: '/', owner: '/owner', ownerToday: '/owner/today', ownerOffers: '/owner/offers', ownerOfferNew: '/owner/offers/new', ownerStore: '/owner/store', ownerProductNew: '/owner/products/new', ownerProduct: (id: string) => \`/owner/products/${encodeURIComponent(id)}\` } as const`, `ROUTE_PATTERNS`(`ownerProduct: '/owner/products/:productId'`) |
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

## 11. 오버레이 층 설계 (fe-reviewer R-2, fe-qa round3)

### 11.1 결함과 근거

- 정본: `layout.md` "화면 골격"(오버레이는 본문 자리에 `.dim` + `.sheet`), `wireframe.html` C10(:255~269, `.bar` → `.dim` → `.tabs`), `design-system-usage` §3.2.
- 현재: `shared/ui/Overlay.tsx:33~34`와 `widgets/owner-nav/presentation/OwnerDialogLayer.tsx:47~58`(+`useOwnerDialog.tsx`)이 `.app` **끝**에 `.dim`을 포털로 붙인다. DOM 순서가 `.bar → .body → .tabs → .dim`이라 (1) `.body`와 `.dim`이 둘 다 `flex:1`이라 높이를 나눠 갖고, (2) 탭이 시트 위에 그려진다. fe-qa round3 `overlay.json`: O4 로그아웃 dim 300px / body 332px.
- 사용처: O8·O4/O8 로그아웃(`OwnerAccountButton`, `OwnerLogoutLink`, `OwnerAccountRows` → `useOwnerDialog` → `OwnerDialogLayer`), M2 `SanctionSheet`, M4 `PointGrantSheet`, O12 `PhotoPickSheet`(→ `Overlay`).
- 정상인 곳(대조): C10 `pages/my/presentation/MyPage.tsx:46~50`은 열림 동안 `.body`를 **렌더하지 않고** `.dim`을 그린다. C1a `LocationSheet`도 `useModalFocus` 방식(page 상태).

### 11.2 사실 확인 (설계 제약)

1. 오버레이를 여는 상태가 **`.body` 안쪽 컴포넌트에 있다**: `OwnerLogoutLink`·`OwnerAccountRows`(O4 본문 안), `SanctionSheet`·`PointGrantSheet`를 여는 admin 패널, `PhotoPickSheet`의 `PhotoField`. `.body`를 언마운트하면 오버레이 상태와 열림 버튼이 함께 사라진다. MyPage 방식은 상태가 page에 있어서만 가능하다.
2. page는 `.bar`와 `.body`를 fragment로 반환하고(C-6), `.body`는 각 page가 직접 그린다(`shared/ui`에 Body 컴포넌트 없음). 셸(`OwnerLayout` 등)은 `.body`에 손댈 수 없다.
3. `useOwnerDialog.close`는 `setOpen(false)` 직후 동기로 `buttonRef.focus()`를 호출한다. 본문을 숨긴 상태에서는 트리거(본문 안 버튼)가 `display:none`이라 이 포커스가 무시된다. 포커스 복귀를 "숨김 해제 뒤"로 옮겨야 한다.
4. `.app` 중첩은 현재 없다: `CustomerFrame`은 `div[data-shell=customer]`이지 `.app`이 아니고, `AccountLayout` 고객 경로도 `CustomerFrame > page의 .app` 한 겹이다. `closest('.app')`는 가장 안쪽 `.app`이라 맞고, 자식 탐색은 `:scope > .body`(직계)로 한정해 바깥 프레임을 잘못 건드리지 않게 한다.
5. wireframe에서 오버레이 동안: `.bar`는 항상 보임(O8·C1a·C3a·C10·O10). `.tabs`는 C10·O10에서만 보이고 O8·C1a·C3a에는 없다(탭이 없는 화면일 수도 있어 의도 불명). `.cta`는 C3a(주 버튼이 있는 화면)에서 보이지 않는다.

### 11.3 후보 비교

| | A. 열림 동안 형제 `.body` 숨김 + `.dim`을 `.body` 자리에 삽입 (Overlay가 DOM 처리) | B. page가 오버레이 상태를 알고 `.body` 대신 `.dim` 렌더 (MyPage 방식) | C. 숨기지 않고 `.body`에 인라인 `flex:none;height:0` |
| --- | --- | --- | --- |
| 변경 범위 | `shared/ui/Overlay` + 신규 `shared/lib` DOM 도우미 + `widgets/owner-nav`(`OwnerDialogLayer` 제거). 사용처 page·패널은 안 바뀜 | 사용처 7곳 + 그 상위 page 전부(상태를 위로 올림) | A와 비슷하나 인라인 레이아웃 스타일(F12 취지에 어긋남) |
| 상태 보존 | `.body`가 마운트된 채라 열림 상태·폼 입력 보존 | `.body` 언마운트: 본문 안에 상태가 있는 `OwnerLogoutLink`·`OwnerAccountRows`·admin 패널은 **불가능**(11.2-1) | 보존 |
| 스크롤 위치 | `display:none`이면 scrollTop을 잃을 수 있어 열 때 저장, 닫을 때 복원(fe-qa 실측 필요) | 잃음 | 보존 |
| 포커스 복귀 | 숨김 해제 뒤 opener로 복귀(11.4) | page가 직접(MyPage `returnFocusRef`) | 보존 |
| 스크린리더 | 형제에 `inert` + 시트 `aria-modal`. 숨긴 `.body`는 접근성 트리에서 빠짐 | `.body` 부재 | `.body`가 남아 `inert` 필요 |
| 판정 | **권고** | 기각(제약 1) | 기각(인라인 레이아웃 스타일) |

### 11.4 권고안 A의 동작

`shared/lib/shellOverlay.ts`(React 없는 DOM 도우미, 업무 모름)가 `openShellOverlay(anchor: Element)`를 제공하고 `Overlay`가 effect에서 호출한다.

1. 프레임 = `anchor.closest('.app')`. 없으면 `document.body`로 폴백하고 아무것도 숨기지 않는다(현재 Overlay의 폴백 유지).
2. 프레임의 직계 `.body`를 모두 찾아 `scrollTop`을 저장하고 `hidden`을 부여한다. 직계 `.cta`에도 `hidden`을 부여한다(임시 D-19). `.body`·`.cta`의 클래스 `display`는 `bundle.css`의 전역 `[hidden]` 규칙이 이기므로 인라인 `display`를 따로 주지 않는다(D-30).
3. 프레임의 직계 `.bar`·`.tabs`·`.nav`에 `inert`를 부여한다(보이되 조작 불가, `aria-modal` 대응).
4. `.dim` 요소(`className="dim"`)를 **직접 만들어** 마지막 직계 `.body` 바로 뒤에 넣는다. `.body`가 없으면 첫 직계 `.cta`·`.tabs` 앞, 그것도 없으면 프레임 끝. DOM 순서가 `.bar → .dim → .tabs`가 되어 `design-system-usage` §3.2와 wireframe C10에 맞는다. `Overlay`는 이 `.dim`을 포털 대상으로 쓰므로 새 클래스·인라인 스타일이 필요 없다. 바깥 눌림은 `.dim`에 붙인 네이티브 click 리스너(`e.target === dim`)로 받는다.
5. 열림 동안 프레임에 `.body`가 새로 생기면(로딩 → 로드 교체) 그것도 숨긴다: 프레임 `childList`만 보는 `MutationObserver`.
6. 닫힘(cleanup): observer 해제 → `.dim` 제거 → `hidden`·`inert` 해제 → `scrollTop` 복원 → **그다음** 포커스 복귀(opener가 연결돼 있으면 opener, 아니면 프레임에 `tabIndex=-1` 후 포커스). 한 프레임에 오버레이가 둘 이상 열리면 마지막 하나가 닫힐 때만 해제하도록 프레임별 열림 수를 센다(`WeakMap<Element, number>`).
7. 포커스 복귀 대상: `Overlay`에 선택 prop `returnFocusRef?: RefObject<HTMLElement | null>`를 추가한다. 있으면 그것(Safari는 버튼을 눌러도 `document.activeElement`가 버튼이 아닐 수 있고, `useOwnerDialog`가 이미 `buttonRef`를 갖고 있음), 없으면 열기 직전 `document.activeElement`.

8. (5차, D-31·D-32) **제약**: 한 프레임에 오버레이를 둘 이상 동시에 열지 않는다(중첩 미지원). 두 `.dim`이 높이를 나눠 갖고 `Esc`가 둘 다 닫는다. 열 때 이미 `hidden`인 요소는 숨김 목록에 넣지 않으므로 닫을 때 되살리지 않는다. 이 두 줄을 `shellOverlay.ts` 파일 머리 주석에 적는다.

### 11.5 통일 여부

- `OwnerDialogLayer`는 `Overlay`와 하는 일(포털, Tab 트랩, Esc·바깥 닫기)이 같고 `dismissible`·자동 포커스·포커스 복귀만 빠져 있다. **`Overlay` 하나로 통일**하고 `OwnerDialogLayer.tsx`를 지운다. `useOwnerDialog.layer`는 `open`일 때 `<Overlay onClose={close} returnFocusRef={buttonRef}>`를 그린다(`target` 상태·`closest('.app')` 계산 제거). `close`는 `setOpen(false)`만 하고 포커스는 Overlay가 복귀한다. `onOpen`(열 때 메뉴로 초기화)은 그대로.
- (5차: 아래 단락은 4차 판단이며 D-22 변경으로 §11.13이 대체한다.) 고객 C10(`MyPage LogoutDim`)·C1a(`LocationSheet`, 홈)는 **이번 차수에서 바꾸지 않는다.** 지금 정상 동작하고 customer-home.md 결정(D-15, D-23)과 테스트(`MyPage.test`, `HomePage.test`)가 걸려 있다. 다만 MyPage 방식은 닫으면 `.body`를 다시 그려 스크롤을 잃으므로, 이 층이 QA를 통과한 뒤 같은 `Overlay`로 옮길지 사용자에게 묻는다(Q-8).
- `Overlay`의 Tab 트랩은 `shared/lib/useModalFocus.ts`와 사실상 같다. 이번에는 합치지 않고(범위 밖) 중복으로 남긴다(`TODO` A-7).

### 11.6 영향 파일·소유·순서

| 순서 | 파일 | 변경 | 소유 |
| --- | --- | --- | --- |
| 1 | `src/shared/lib/shellOverlay.ts` (신규) | 11.4의 DOM 도우미 | `shared` |
| 2 | `src/shared/ui/Overlay.tsx` | 도우미 사용, `returnFocusRef` prop, 포털 대상 변경 | `shared/ui` |
| 3 | `src/widgets/owner-nav/presentation/OwnerDialogLayer.tsx` | 삭제 | `widgets/owner-nav` |
| 3 | `src/widgets/owner-nav/presentation/useOwnerDialog.tsx` | `Overlay` 사용, `target` 제거, 동기 포커스 호출 제거 | `widgets/owner-nav` |
| 영향만 | `src/features/admin/presentation/{SanctionSheet,PointGrantSheet}.tsx` | `Overlay` prop 불변이라 수정 없음. 확인만 | `features/admin` |
| 영향만 | `src/features/products/presentation/PhotoPickSheet.tsx` | 사용 방식 불변. **다른 세션(frontend-a7) 소유 slice**라 건드리지 않는다. `tests/features/products/presentation/PhotoPickSheet.test.tsx`와 `e2e/products.spec.ts`가 `.dim` 위치·포커스 복귀에 의존하는지 오케스트레이터가 확인 | `features/products` |
| 없음 | `bundle.css`, `OwnerLayout`·`AdminLayout`·`CustomerLayout`·`AccountLayout`, `MyPage`, `HomePage` | 변경 없음 | |

순서는 1 → 2 → 3(아래 계층부터, `tdd-workflow` §1). 새 slice·공개 API·포트·토큰·wiring 변경 없음(`shared/lib`는 slice가 없다, F3). `fsd-structure` §7 대응표는 바꾸지 않는다(제안 없음).

### 11.7 결정 표 (이어서)

| D | 항목 | 값 | 상태 | 근거 | 구현을 막는가 |
| --- | --- | --- | --- | --- | --- |
| D-18 | `.body` 자리 대신하는 방법 | 후보 A: 열림 동안 직계 `.body` `hidden`, `.dim`을 마지막 `.body` 뒤에 삽입, `scrollTop` 저장·복원 | 확정 | 사용자 결정 2026-11-11(A안 승인), 11.2-1, 11.3 | 아니오 |
| D-19 | 오버레이 동안 `.cta`·`.tabs` | `.cta` 숨김, `.tabs`·`.bar`는 보이되 `inert` | 확정 | 사용자 결정 2026-11-11, 11.2-5 | 아니오 |
| D-20 | 배경 차단 | 형제 `.bar`·`.tabs`·`.nav`에 `inert`, 시트는 각자 `role="dialog" aria-modal="true"` | 확정 | D-19(보이되 inert)의 구현 그 자체. 오케스트레이터 전달: 사용자가 A안·D-19를 승인(§11.12 판단) | 아니오 |
| D-21 | `Overlay`와 `OwnerDialogLayer` | `Overlay`로 통일, `OwnerDialogLayer` 삭제 | 확정 | A안은 `.dim`을 `.body` 자리에 넣으므로 `.app` 끝에 붙이는 `OwnerDialogLayer`를 남기면 결함이 재발한다. 오케스트레이터 전달: 사용자가 A안을 승인(§11.12) | 아니오 |
| D-22 | 고객 C10·C1a의 page 방식 | **변경(5차)**: 두 시트를 `shared/ui/Overlay`로 옮긴다(§11.13). 화면 동작·문구는 그대로 | 확정 | 오케스트레이터 판단(사용자 위임 2026-11-11). 근거: fe-qa 4차 실측에서 C10 로그아웃 시트를 닫으면 `.body` scrollTop이 120 → 0으로 초기화(열림 동안 `.body`를 DOM에서 빼고 다시 그림). 이전 값: "이번 차수 유지"(임시) | 아니오 |
| D-23 | 포커스 복귀 | `Overlay`가 숨김 해제 뒤 복귀, 선택 `returnFocusRef` | 확정 | A안의 필수 부수 수정(11.2-3, C-10). 오케스트레이터 전달: 사용자가 A안을 승인(§11.12) | 아니오 |
| D-24 | 열림 중 새 `.body` | 프레임 `childList` `MutationObserver`로 숨김 | 확정 | A안 동작의 일부(로딩 → 로드 교체 대응). 오케스트레이터 전달: 사용자가 A안을 승인(§11.12) | 아니오 |
| D-25 | O8 PC 드롭다운 | 이번 설계에서 제외, 하단 시트 유지 | 확정 | 요청(결정 4번 대기) | 아니오 |

### 11.8 정합 이슈

| C | 내용 | 양쪽 근거 |
| --- | --- | --- |
| C-8 | `design-system-usage` §3.2는 ".body 자리를 대신하게 그린다"고만 하고 방법(page 렌더 vs DOM 처리)과 `.tabs`·`.cta` 처리는 정하지 않는다 | `design-system-usage/SKILL.md` §3.2 ↔ `wireframe.html` C10(tabs 있음)·C3a(tabs·cta 없음) |
| C-9 | 같은 오버레이를 세 가지로 구현: 공용 `Overlay`, `OwnerDialogLayer`, 고객 `useModalFocus`+page `LogoutDim`/`LocationSheet` | 11.1, 11.5 |
| C-10 | `useOwnerDialog.close`의 동기 포커스 복귀는 본문이 숨겨진 상태에서 동작하지 않는다(A 채택의 부수 수정) | `useOwnerDialog.tsx` close ↔ 11.2-3 |
| C-11 | O8·C1a·C3a 와이어프레임에는 `.tabs`가 없고 C10·O10에는 있다. 의도인지 생략인지 불명 | `wireframe.html:258~270, 279, 330, 388, 774` |
| C-12 | `Overlay` 단위 테스트가 없다(`tests/shared/ui/`에 파일 없음). 간접 테스트는 `PhotoPickSheet.test` 등뿐 | `tests/shared/ui/` 목록 |

### 11.9 테스트 목록 (`tdd-workflow` §2, 위치 `tests/` 아래)

공통 준비: `.app` 안에 `.bar`, `.body`(트리거 버튼과 입력), `.cta`, `.tabs`를 직접 그리는 테스트용 프레임. 가짜 구현체·`vi.mock` 없이 실제 `Overlay`를 쓴다.

**`tests/shared/lib/shellOverlay.test.ts`** (jsdom)
- 열면 직계 `.body`에 `hidden`이 생기고 `.dim`이 `.body` 바로 뒤, `.cta`·`.tabs` 앞에 있다(자식 순서 `.bar, .body, .dim, .cta, .tabs`).
- `.cta`에는 `hidden`, `.bar`·`.tabs`에는 `inert`가 생긴다(`.tabs`는 `hidden`이 아니다).
- 닫으면 `.dim`이 사라지고 `hidden`·`inert`가 모두 해제된다.
- 닫으면 열기 전에 저장한 `.body.scrollTop`을 복원한다.
- 열려 있는 동안 새 `.body`가 추가되면 그것도 `hidden`이다(MutationObserver 콜백 후).
- `.body`가 없는 프레임: `.dim`이 `.cta`·`.tabs` 앞에, 둘 다 없으면 끝에 들어간다.
- 직계가 아닌 `.body`는 숨기지 않는다.
- 오버레이 둘을 열고 하나를 닫으면 `hidden`이 유지되고, 마지막을 닫으면 해제된다.
- `.app`이 없는 앵커는 `document.body`에 `.dim`을 붙이고 아무것도 숨기지 않는다.

**`tests/shared/ui/Overlay.test.tsx`** (신규, C-12)
- 열림: 자식이 `.dim` 안에 그려지고 `.dim`은 `.app`의 직계 자식이다.
- 열림 동안 `.body`는 `hidden`이지만 마운트돼 있다(입력에 쓴 값이 닫힌 뒤에도 남는다).
- Esc → `onClose`. `dismissible={false}`이면 호출하지 않는다.
- 바깥(`.dim` 자체) 클릭 → `onClose`, 시트 안 클릭 → 호출하지 않는다. `dismissible={false}`이면 바깥 클릭도 무시한다.
- 열리면 `data-autofocus` 요소에, 없으면 첫 포커스 가능 요소에 포커스가 간다.
- Tab·Shift+Tab이 시트 안에서만 돈다(마지막 → 첫 번째, 첫 번째 → 마지막).
- 닫히면 포커스가 `returnFocusRef` 요소로, 없으면 열기 전 `activeElement`로 돌아간다(그 시점에 `.body`는 이미 `hidden`이 해제됨: `document.activeElement`가 그 버튼인지로 확인).
- opener가 사라졌으면 프레임으로 포커스가 간다.
- 열림 동안 형제 `.bar`·`.tabs`는 `inert`다.
- 닫힌 뒤(언마운트 포함) `.dim`·`hidden`·`inert`가 DOM에 남지 않는다.

**`tests/widgets/owner-nav/presentation/*.test.tsx`** (기존 파일 보강)
- `OwnerLogoutLink`: 「로그아웃」 클릭 → `.dim` 안에 확인 시트, `.body` `hidden`; 「취소」·Esc → 닫힘, `.body` 복원, 포커스가 트리거 버튼으로 복귀.
- `OwnerAccountButton`: 「계정」 클릭 → 메뉴 시트(`.dim` 안), 다시 열면 메뉴부터 시작, 로그아웃 확인으로 전환해도 같은 `.dim`, 닫으면 「계정」 버튼에 포커스.
- `OwnerAccountRows`: 행의 로그아웃 → 시트, 닫으면 같은 버튼에 포커스(본문이 숨었다 돌아와도 상태 유지).
- `OwnerDialogLayer`를 직접 import하는 테스트는 지운다(없으면 해당 없음).

**기존 테스트 영향 확인(수정 소유는 각 slice)**: `PhotoPickSheet.test`(products 세션 소유), admin 시트 테스트, `MyPage.test`·`HomePage.test`(변경 없음 예상).

**fe-qa 실측 (`qa-verification` §4.1 오버레이, 360×740·1280×800, 스크린샷 직접 확인)**
- O4 로그아웃·O8·M4·M2·O12: 열린 상태에서 `.body`가 `hidden` 속성만으로 `display:none`(인라인 style 없음, D-30), `.dim`이 `.bar`와 `.tabs` 사이, `.dim`+`.bar`+`.tabs` 높이 = 앱 높이.
- 본문을 중간까지 스크롤 → 열고 닫기 → `.body.scrollTop`이 같다(복원 실패 시 설계 보완).
- 닫은 뒤 `.bar`·`.tabs` 클릭 가능, 열린 동안 `.tabs`가 눌리지 않는다.
- 1280에서 `.nav`·`.cta`/`.dk` 상태, 고객 C10 대조군과 시각 비교.
- 시트 안 포커스 순환과 닫은 뒤 트리거 포커스.
- 로딩 → 로드로 `.body`가 교체되는 화면에서 열려 있는 동안 새 본문이 비치지 않는다(D-24).

### 11.10 남길 작업 주석

| ID | 위치 | 태그 | 원문 초안 |
| --- | --- | --- | --- |
| A-7 | `src/shared/ui/Overlay.tsx` Tab 트랩 | TODO | **(철회, 5차)** D-36(`useModalFocus.ts` 삭제)으로 중복이 사라지므로 이 `TODO`를 지운다. 4차 원문: `// TODO: Tab 포커스 트랩이 shared/lib/useModalFocus.ts와 중복이다. 한 구현으로 합친다.`<br>`//   왜: 오버레이 층 수정(app-shell.md §11) 범위를 넘는다`<br>`//   언제: 리팩터링 시, 고객 C10·C1a를 Overlay로 옮길 때(app-shell.md Q-8)` |
| A-8 | `shellOverlay.ts` `.cta` 숨김 | TODO | `// TODO: 오버레이 동안 .cta를 숨기고 .tabs는 남긴다. 정본이 화면별로 정하면 맞춘다.`<br>`//   왜: wireframe마다 .tabs 유무가 달라 의도가 불명이다 (app-shell.md C-11, D-19)`<br>`//   언제: 결정 후 (사용자: 오버레이 동안 탭·CTA 표시)` |

FIXME 없음, `open-issues:` 대상 없음.

### 11.11 질문 목록

| Q | 내용 | 임시 동작(구현을 막지 않음) |
| --- | --- | --- |
| Q-7 | 오버레이가 열려 있을 때 `.tabs`와 `.cta`를 보일까요? | 해결: D-19 확정(`.tabs`·`.bar` 보이되 inert, `.cta` 숨김). 남길 주석 A-8의 `언제:`는 유지(정본이 화면별로 다르게 정하면 맞춤) |
| Q-8 | 고객 C10(`MyPage`)·C1a(`HomePage`)도 이 층이 QA를 통과한 뒤 같은 `Overlay`로 옮길까요? 옮기면 본문을 다시 그리지 않아 스크롤이 유지되고 포커스 우회 코드가 사라집니다. | 해결: D-22 변경(옮긴다, §11.13) |
| Q-9 | O8 "PC는 계정 버튼 아래 드롭다운"은 `bundle.css`에 클래스가 없어 결정 4번 대기입니다. | D-25: 하단 시트 |
| Q-10 | `PhotoPickSheet`(products 세션 소유)는 사용 방식이 그대로지만 `Overlay` 동작이 바뀝니다. 머지 순서를 어떻게 할지 오케스트레이터 조정이 필요합니다. | 파일 겹침 없음 |

### 11.12 D-20~D-24 확정 판단 (2026-11-11)

- 사용자는 D-18(A안)·D-19만 확정했고 나머지는 따로 정하지 않았다. 설계자 판단으로 아래만 "확정"(근거: 오케스트레이터 전달 "사용자가 A안·D-19를 승인")으로 올린다. 사용자가 바꾸면 되돌린다.
  - D-20: D-19의 "보이되 inert" 그 자체다. 별개 선택지가 없다.
  - D-21: A안에서는 `.dim`을 `.body` 자리에 넣으므로 `.app` 끝에 포털하는 `OwnerDialogLayer`를 남기면 같은 결함이 그대로 남는다. 선택지가 없다.
  - D-23: `.body`가 숨겨지면 동기 포커스 복귀가 무시되므로(C-10) A안의 필수 부수 수정이다.
  - D-24: A안이 열림 동안 `.body`를 숨기는 동작의 일부다.
- D-22(고객 C10·C1a를 이번 차수에 유지)는 A안의 귀결이 아니라 범위 선택이며 Q-8이 열려 있으므로 **임시로 둔다**. D-25는 이미 확정이다.

### 11.13 고객 C10·C1a를 `Overlay`로 옮기는 설계 (5차, D-22·D-34~D-36)

화면 동작·문구는 바꾸지 않는다. 바뀌는 것은 시트를 여는 방식뿐이다.

**현재(코드 확인)**
- `src/pages/my/presentation/MyPage.tsx`: `logoutOpen ? <LogoutDim/> : <div className="body">…`. `LogoutDim`이 `useModalFocus`로 Esc·Tab을 처리하고 `.dim` 클릭을 직접 듣는다. 닫을 때 `.body`를 새로 그리므로 스크롤을 잃고, 버튼이 다시 생긴 뒤 포커스를 옮기려고 `returnFocusRef` 불리언 + `useEffect`를 둔다(:23~:32).
- `src/pages/home/presentation/HomePage.tsx`: `sheetOpen ? <div className="dim" onClick=…><LocationSheet/></div> : <div className="body">…`. 닫으면 `closeSheet`가 `chipRef.current?.focus()`를 부른다(:46~:49). `LocationSheet`(`features/offers`)가 안에서 `useModalFocus(sheetRef, onClose)`를 부른다(:33).
- 둘 다 `.app`은 `CustomerLayout`이 그린다. `Overlay`는 `anchor.closest('.app')`로 이 `.app`을 찾고 직계 `.body`를 `hidden`으로 숨겨 마운트를 유지한다. `.bar`·`.tabs`는 `inert`, `.cta`는 `hidden`이다(D-19). 홈 하단의 입점 신청 링크(`.app` 직계, 비로그인만)는 지금과 같이 `.dim` 뒤에 그대로 보인다(변화 없음).

**바꿀 파일**

| 파일 | 변경 | 소유 |
| --- | --- | --- |
| `src/pages/my/presentation/MyPage.tsx` | `logoutOpen`일 때 `.body`를 **항상 그리고**, 그 뒤에 `{logoutOpen ? <Overlay onClose={() => setLogoutOpen(false)} returnFocusRef={logoutRef}><LogoutConfirmSheet onClose={…} /></Overlay> : null}`를 둔다. `LogoutDim`, `useModalFocus` import, `returnFocusRef` 불리언·`useEffect`, `closeLogout` 삭제 | `pages/my` |
| `src/pages/home/presentation/HomePage.tsx` | `.body`를 항상 그리고 `{sheetOpen ? <Overlay onClose={closeSheet} returnFocusRef={chipRef}><LocationSheet …/></Overlay> : null}`. `closeSheet`는 `setSheetOpen(false)`만(포커스 호출 삭제). `onApply`는 `changeFilter` 뒤 `closeSheet()` 그대로. `.dim`·인라인 `onClick` 삭제 | `pages/home` |
| `src/features/offers/presentation/LocationSheet.tsx` | `useModalFocus(sheetRef, onClose)`와 `sheetRef`·import 삭제(D-34). `onClose` prop은 남는가: 시트 안에 닫기 버튼이 없고 Esc·바깥은 `Overlay`가 부르므로 **prop을 지운다**(호출처 `HomePage`만). 공개 API 이름 `LocationSheet`는 그대로 | `features/offers` |
| `src/features/auth/presentation/LogoutConfirmSheet.tsx` | 「취소」에 `data-autofocus`, `cancelRef`·포커스 `useEffect`·`useRef`(cancel) 삭제(D-35). `onClose` 호출·문구·`role="alertdialog"` 그대로 | `features/auth` |
| `src/shared/lib/useModalFocus.ts` | 삭제(D-36), 위 두 사용처 정리 뒤 `git grep -n useModalFocus -- src tests` 0건 확인 | `shared` |
| `src/shared/ui/Overlay.tsx` | A-7 `TODO` 주석 3줄만 삭제(D-36). 동작 변경 없음 | `shared/ui` |

**공개 API 변경**: `pages/my`·`pages/home`의 `index.ts`(`MyPage`, `HomePage`) 불변. `features/offers`·`features/auth` `index.ts`는 이름 불변(`LocationSheet`의 prop만 줄어듦). 포트·토큰·wiring·`fsd-structure` §7 대응표 변경 없음.

**포커스 우회 코드 제거 지점**
1. `MyPage.tsx:23~32` 불리언 ref + effect + `closeLogout`
2. `HomePage.tsx:46~49` `closeSheet`의 `chipRef.current?.focus()`(닫기 전 `inert`인 `.bar` 안이라 무시됨)
3. `LocationSheet.tsx:33` `useModalFocus`
4. `LogoutConfirmSheet.tsx`의 `cancelRef` 포커스 effect(`data-autofocus`로 대체)

**닫은 뒤 동작**: `Overlay` cleanup이 `hidden`·`inert` 해제와 `scrollTop` 복원 뒤에 `returnFocusRef`(「로그아웃」 버튼, 위치 칩)로 포커스를 돌린다(D-23). 로그아웃을 확정하면 인증 상태가 바뀌어 `CustomerLayout` 가드가 `/`로 보내며 `MyPage`가 언마운트되고, `Overlay`는 언마운트 cleanup으로 `.dim`·`hidden`을 정리한다(`Overlay.test` "언마운트 포함" 케이스가 이미 보장).

**유지되는 동작(회귀 방지)**: 「적용」 때만 반경 반영(Esc·바깥은 적용 없이 닫힘, `customer-home.md` D-15), 시트 안 반경 선택값은 열 때마다 `radiusKm`으로 초기화(시트가 매번 새로 마운트됨), `aria-expanded`·`aria-haspopup`, 로그아웃 처리 중 「처리 중…」·`aria-disabled`.

**테스트 목록 (`tdd-workflow` §2, 위치 `tests/` 아래)**

*고객 C10·C1a 묶음(번들 B)*

`tests/pages/my/MyPage.test.tsx` (기존 보강)
- (기존 유지, 이름 그대로 통과해야 함) 「로그아웃」 시트 열기·취소 닫기, 첫 포커스 「취소」, Esc·취소로 닫으면 포커스가 「로그아웃」으로, 확정 시 `logout` 호출 후 `/`.
- (신규) 시트가 열려 있는 동안 `.body`는 `hidden`이지만 DOM에 남아 있고 `.dim`이 `.app` 직계 자식이다(순서 `.bar`, `.body`, `.dim`). 닫으면 `.body`의 `hidden`이 없다.
- (신규) 닫은 뒤의 `.body`는 열기 전과 **같은 노드**다(`toBe`): 다시 그리지 않는다. 열기 전 `.body.scrollTop = 120`을 주면 닫은 뒤에도 120이다.
- (신규) 시트 안 Tab·Shift+Tab이 시트 안에서만 돈다(`Overlay` 담당이므로 한 케이스).
- (수정) 기존 「전체 보기 링크가 없다」 단언은 `.body` hidden 단언으로 바꾼다(`queryByRole`이 숨은 요소를 제외하므로 통과는 하지만 의도가 달라짐). 약화가 아니라 의도에 맞춘 교체임을 보고에 적는다.

`tests/pages/home/HomePage.test.tsx` (기존 보강)
- (기존 유지) C1a 열기(첫 포커스 「◎ 현재 위치 사용」, `aria-pressed`, 문구), 「10km」→「적용」으로 URL `?radius=10`·칩 갱신, Esc는 적용 없이 닫고 칩으로 포커스.
- (신규) 열려 있는 동안 `.body`는 `hidden`이지만 마운트돼 있고, 검색창에 입력한 값(제출 전 「빵」)이 시트를 닫은 뒤에도 남는다.
- (신규) 닫은 뒤 `.body.scrollTop`이 열기 전 값이다(120).
- (신규) 바깥(`.dim` 자체) 클릭은 적용 없이 닫고 URL이 그대로다. 시트 안 클릭은 닫지 않는다.
- (수정) 「목록 대신 보인다」 단언(`queryByRole('link', {name:/소금빵 세트/})`, `queryByRole('searchbox')`)은 유지하되 `.body` hidden 단언을 함께 둔다.
- (신규) 「적용」 뒤 포커스가 위치 칩으로 돌아온다(`inert`가 풀린 뒤).

`tests/features/auth/presentation/LogoutConfirmSheet.test.tsx` (파일이 있으면 보강, 없으면 `MyPage.test`와 `OwnerAccountButton` 테스트가 대신함을 보고)
- 「취소」에 `data-autofocus`가 있다. `Overlay` 안에서 열면 포커스가 「취소」다(「로그아웃」 아님).

`tests/features/offers/presentation/LocationSheet.test.tsx` (있으면)
- `onClose` prop 제거에 맞춰 호출부 수정. Esc·Tab 단언은 `Overlay` 담당이므로 이 파일에서는 지우고 `HomePage.test`가 대신한다(검사를 옮긴 것이므로 보고에 적는다).

*fe-qa 실측 (`qa-verification` §4.1 오버레이, 360×740·1280×800)*
- C10: 마이 화면을 스크롤(120) → 로그아웃 시트 열고 닫기 → `.body.scrollTop` 120 유지(fe-qa 4차 실측의 120 → 0 재현이 사라짐).
- C1a: 홈 목록을 스크롤 → 위치 시트 열고 닫기 → 스크롤 유지, 불러온 카드가 다시 로딩으로 돌아가지 않음.
- 두 화면 모두 열린 동안 `.dim` + `.bar` + `.tabs` 높이 = 앱 높이, 닫은 뒤 탭 클릭 가능.

**남길 작업 주석**: 없음(`FIXME`·`TODO` 새로 만들지 않음). 철회: A-7(D-36).

**의존·순서**: 번들 B는 번들 A와 파일이 겹치지 않아 병렬 가능하다. 단 `Overlay.tsx`는 A-7 주석 삭제만 하므로 `shellOverlay.ts`를 만지는 번들 A와 충돌하지 않는다. 순서는 `LogoutConfirmSheet`·`LocationSheet`(features) → `MyPage`·`HomePage`(pages) → `useModalFocus.ts` 삭제.

### 11.14 정합 이슈 (5차)

| C | 내용 | 양쪽 근거 |
| --- | --- | --- |
| C-19 | `customer-home.md` D-15·D-23과 §3에는 C10·C1a가 "page 안에서 `.body` 자리에 `.dim`을 그린다"로 적혀 있다. D-22 변경으로 사실과 어긋난다 | `customer-home.md:29·750·758` ↔ 이 문서 D-22. 소유 설계안이라 이 발주에서 고치지 않음, 후속에서 `customer-home.md` 해당 줄에 "app-shell.md D-22로 `Overlay` 사용" 각주 필요 |
| C-20 | `LogoutConfirmSheet`의 포커스(`cancelRef.focus()`)가 `Overlay`의 첫 포커스에 덮여 O8·O4 상점주 로그아웃에서도 첫 포커스가 「로그아웃」일 가능성이 있다(코드 읽기 기준, 실행 미확인) | `LogoutConfirmSheet.tsx` effect ↔ `Overlay.tsx:55~61`. D-35에서 바로잡고, `OwnerAccountButton` 테스트에 포커스 단언이 있는지 fe-qa가 확인 |

## 12. 프레임 바깥 배경과 공개 화면(A1~A3) 셸 (2026-11-11, 사용자 결정 반영)

### 12.1 프레임 바깥 배경 (확정, D-26)

- 정본: `layout.md` 역할별 셸 표 고객 행 "가운데 420px, 좌우 1px `line`, 바깥은 `bg`". fe-qa round3 실측: PC에서 프레임 바깥 `body`가 `rgb(255,255,255)`로 `bg`가 아니다.
- 원인: 디자인 시스템 원본 `components/bundle.css`의 `body { background: var(--paper) }`(복사본 `src/app/styles/bundle.css:8~13`)가 `--bg`가 아니다.
- 결정: 원본 `body` 배경을 `var(--bg)`로 바꾸는 것을 사용자가 승인했다(별도 fe-developer가 원본 수정 후 `sync_styles.mjs copy`). 이 설계안은 근거만 기록하고 CSS는 건드리지 않는다. `.app` 자체의 배경은 `var(--paper)`로 그대로다(프레임 안만 paper, 바깥만 bg).
- 영향: 상점주·관리자 셸은 PC에서 `.app`이 전체 폭이라 바깥이 보이지 않는다. 고객 프레임 바깥만 바뀐다. 테스트는 jsdom으로 못 보므로 fe-qa 실측(1280px에서 `getComputedStyle(body).backgroundColor`가 `--bg` 값)으로 확인한다.

### 12.2 현황 (코드 확인)

- `src/app/router/routes.tsx:42~44`: `/login`·`/signup`·`/password-reset`이 레이아웃 없이 최상위에 있다. PC에서 전체 폭이다.
- 세 page(`LoginPage.tsx:31`, `SignupPage.tsx:35`, `PasswordResetPage.tsx:31`)는 각자 `<div className="app">` 안에 `.bar` → `.body` → `.cta`를 그리고, 로딩 중에는 `<div className="app" aria-busy="true" />`를 반환한다.
- `CustomerFrame.tsx`는 현재 `data-shell="customer"` + `maxWidth:420` + 가운데 + 좌우 1px 선만 있고 높이·flex 인라인이 없다. 자식 `.app`의 `height:100dvh`(`bundle.css:40~50`)가 그대로 적용된다. 따라서 page의 `.app`을 프레임에 바로 넣으면 높이·스크롤이 정상이다(`.body`만 스크롤, 바는 고정).

### 12.3 결정 표 (이어서)

| D | 항목 | 값 | 상태 | 근거 | 구현을 막는가 |
| --- | --- | --- | --- | --- | --- |
| D-26 | 프레임 바깥 배경 | 원본 `bundle.css` `body` 배경 `var(--paper)` → `var(--bg)` | 확정 | 사용자 승인 2026-11-11, `layout.md` 역할별 셸, fe-qa round3 | 아니오 |
| D-27 | A1~A3 프레임 | PC에서 고객과 같은 420px 가운데 프레임(`CustomerFrame`) | 확정 | 사용자 결정 2026-11-11 | 아니오 |
| D-28 | A1~A3 레이아웃 라우트 | 신규 `app/layouts/PublicFrameLayout.tsx`(`<CustomerFrame><Outlet /></CustomerFrame>`) 유지 | 확정(5차) | 오케스트레이터 판단(사용자 위임 2026-11-11). 3줄짜리이고 `CustomerLayout`의 접근 가드와 섞지 않는다. 12.4 비교 | 아니오 |
| D-29 | A1~A3 PC 패널 버튼(`.dk`) | **변경(5차)**: `.dk` 복사본을 **지운다**(`LoginPage`의 `.body > .dk` 가입 안내 블록, `SignupForm`·`PasswordResetForm`의 `btn pri dk` 제출 버튼). `.cta` 한 벌만 남긴다. C-13 주석도 같은 수정에서 바로잡고 A-9 `TODO`는 남기지 않는다 | 확정(5차) | 오케스트레이터 판단(사용자 위임 2026-11-11). 420px 프레임 안에서 `.dk`는 항상 `display:none`인 죽은 마크업이고(12.5) 주석(C-13)은 사실과 어긋난다. 이전 값: "둔다"(임시). 바뀌는 테스트 §12.12 | 아니오 |
| D-30 | 오버레이의 `.body`·`.cta` 숨김과 `hidden` 속성 | 원본 `components/bundle.css`(요소 기본 모양 제거 블록 뒤)에 `[hidden]:not([hidden='until-found' i]) { display: none !important; }` 추가, 복사본 동기화 완료(셀렉터는 `wireframe.html:1`과 같음). `shellOverlay.ts`는 `hidden` 속성만 쓰고 인라인 `display` 우회를 제거한다. D-18·D-19의 `hidden` 부여 방식은 그대로이며 C-17 해소 | 확정 | 사용자 결정 2026-11-11 | 아니오. 구현은 fe-developer 진행 중 |
| D-31 | `shellOverlay.hide()`가 이미 `hidden`인 요소 | 열 때 이미 `hidden`인 요소는 숨김 목록(`state.hidden`)과 `scrolls`에 **넣지 않는다**. 닫을 때 원래 숨겨 둔 요소를 살리지 않는다 | 확정 | 오케스트레이터 판단(사용자 위임 2026-11-11), fe-reviewer 사소 지적. 지금은 `el.hidden = true`를 무조건 부여하고 닫을 때 목록 전부를 `hidden=false`로 돌려, 원래 숨긴 `.body`·`.cta`(예: 로딩 분기가 숨겨 둔 요소)가 되살아난다 | 아니오 |
| D-32 | 오버레이 중첩 | **지원하지 않는 사용**으로 제약을 명시한다(§11.4-8). 한 프레임에 오버레이를 둘 이상 동시에 열지 않는다. 두 `.dim`이 높이를 나누고 `Esc`가 둘 다 닫는다(각 `Overlay`가 `document` `keydown`을 따로 듣는다). 열림 수를 세는 `count`는 해제 시점 방어로 유지하고 중첩 동작은 보장하지 않는다 | 확정 | 오케스트레이터 판단(사용자 위임 2026-11-11), fe-reviewer 사소 지적. 시트 위 시트가 필요한 화면이 지금 없다(O8 메뉴 → 로그아웃 확인은 같은 `Overlay`의 내용 교체) | 아니오 |
| D-33 | `layout.md`에 공개 화면(A1~A3) 프레임 반영 | 하지 않는다. 디자인 시스템 정본은 프론트 작업에서 고치지 않는다. 정본 소유자에게 보고하는 항목으로 둔다(C-14) | 확정 | 오케스트레이터 판단(사용자 위임 2026-11-11), Q-11. 작업 원칙 "디자인 시스템은 프론트 작업에서 고치지 않는다" | 아니오 |
| D-34 | 이전 후 시트의 포커스·Esc·Tab | `Overlay`가 맡는다. 그래서 `LocationSheet`는 `useModalFocus` 호출을 **지운다**(남기면 Esc가 `onClose`를 두 번 부르고 Tab 트랩이 두 겹). `MyPage`의 `LogoutDim`·`returnFocusRef` 불리언·효과, `HomePage`의 `closeSheet` 안 `chipRef.focus()`도 지운다(칩은 `inert`인 `.bar` 안이라 닫기 전 `focus()`는 무시됨). 포커스 복귀는 `Overlay`의 `returnFocusRef`(`logoutRef`, `chipRef`) | 확정 | 오케스트레이터 판단(사용자 위임 2026-11-11), D-23, §11.13 | 아니오 |
| D-35 | 로그아웃 확인의 첫 포커스 | `LogoutConfirmSheet`의 「취소」 버튼에 `data-autofocus`를 달고 `cancelRef`와 포커스 effect를 지운다 | 확정 | 오케스트레이터 판단(사용자 위임 2026-11-11). `Overlay`는 시트 안 effect 뒤에 `[data-autofocus]` 없으면 첫 포커스 요소(「로그아웃」)로 포커스를 옮겨, 기존 `cancelRef.focus()`를 덮어쓴다(자식 effect → 부모 effect 순서). O8·O4 상점주 로그아웃도 같은 시트를 `Overlay`로 쓰므로 함께 바로잡힌다 | 아니오 |
| D-36 | `shared/lib/useModalFocus.ts` | 두 사용처(`LocationSheet`, `MyPage`)가 사라지면 파일을 **삭제**하고 `Overlay.tsx`의 A-7 `TODO`도 지운다. 삭제 전 `git grep -n useModalFocus -- src tests`가 0건이어야 한다 | 확정 | 오케스트레이터 판단(사용자 위임 2026-11-11). Tab 트랩 중복 해소(A-7). `tests/shared/lib/`에 이 훅의 테스트는 없다 | 아니오 |

### 12.4 라우터 구성 비교 (D-28)

| | 새 `PublicFrameLayout` | 기존 `<CustomerLayout access="public" />` 재사용 |
| --- | --- | --- |
| 동작 | `CustomerFrame` 한 겹. page의 `.app`이 프레임 직계 | `CustomerFrame > .app(셸) > Outlet`. page의 `.app`이 셸 `.app` 안에 중첩 |
| 세션 가드 | 없음 | 없음(`access="public"`은 `CustomerShell`이라 가드를 타지 않는다. `CustomerLayout.tsx:16`) |
| TabBar | 없음 | 라우트에 `TAB_BAR_HANDLE`이 없으면 안 나온다(`CustomerLayout.tsx:20`). 지금 만들면 안 나오지만 나중에 handle이 붙으면 나온다 |
| 중첩 `.app` | 없음 | 있음. `bundle.css:53~58` `.app > .app`이 처리하므로 동작은 하나 A1~A3는 고객 탭 화면이 아니다 |
| 의미 | 공개(로그인 전) 화면의 프레임. 이름이 맞다 | A1~A3를 "고객 셸"로 묶는다. A1은 상점주·관리자도 쓰는 화면이라 이름이 어긋난다 |
| 비용 | 파일 1개(5줄)와 테스트 1개 | 파일 없음, 라우트만 옮김 |

권고: **새 `PublicFrameLayout`**. 이유는 (1) page가 이미 `.app`을 그려 셸 `.app`이 불필요하다, (2) 가드·TabBar 부재가 레이아웃 이름과 코드로 보장된다, (3) A1은 모든 역할이 쓴다. 재사용도 동작은 하므로 사용자가 파일을 늘리기 싫으면 대안이다(그 경우 라우트 3줄만 `CustomerLayout access="public"` 그룹 `children`에 옮긴다).

`PublicFrameLayout` 골격(사용자 코드 규칙: 주석·토큰만):

```tsx
import { Outlet } from 'react-router';
import { CustomerFrame } from './CustomerFrame';

// 공개(로그인 전) 화면 프레임 A1~A3: PC에서 420px 가운데(app-shell.md §12). 가드·TabBar 없음.
export function PublicFrameLayout() {
  return (
    <CustomerFrame>
      <Outlet />
    </CustomerFrame>
  );
}
```

### 12.5 PC 패널 버튼(.dk) 판단 (D-29)

- 정본 근거: `layout.md` 역할별 셸 표는 고객을 "모바일 화면 그대로 가운데 420px"로 정한다. `design-system-usage` §3.1 "고객 셸은 프레임 폭이 420px이라 720px 규칙이 켜지지 않는다. PC에서도 고객 화면은 모바일 배치(`.tabs`·`.cta`)가 정상". `bundle.css:526~528·565~567`의 `.dk`는 `.app` 컨테이너 720px 이상에서만 보인다.
- 따라서 A1~A3를 프레임에 넣으면 PC에서도 `.cta`(모바일 배치)가 보이고 `.dk`는 숨는다. 이것은 사용자 결정(D-27 "고객과 같은 프레임")의 결과이며 정본과 맞는다. `screens.md` A1~A3는 컴포넌트에 CtaBar만 적고 PC 패널 전용 동작은 없다(A1: AppBar·CtaBar·Button·Input·FieldError).
- `.dk` 복사본은 `LoginPage.tsx:49~57`, `SignupForm.tsx:122`, `PasswordResetForm.tsx`의 `btn pri dk` 등에 있다. 프레임 안에서는 `display:none`이라 화면·접근성 트리에서 모두 빠진다(`display:none`은 접근성 트리에서 제외). (4차 판단 "무해하므로 지우지 않는다"는 5차 D-29 변경으로 대체됐다. 지울 때 바뀌는 테스트는 §12.12.) 단 jsdom은 CSS를 계산하지 않아 `getByRole('button', {name})`이 `.dk`·`.cta` 두 개를 잡는 기존 테스트 방식은 변하지 않는다.
- 주의: SignupForm의 `.dk`·`.cta`가 같은 `<form>`의 `type="submit"` 두 개라, 프레임 안에서는 `.cta`만 보이며 Enter 제출은 그대로 동작한다.

### 12.6 변경 원문 (diff, 어느 세션이 반영해도 그대로 옮길 수 있게)

`src/app/router/routes.tsx` (`frontend-a7`·products 차수가 미커밋 수정 중인 파일. 아래 두 줄 위치는 현재 작업 트리 기준):

```diff
@@ import
 import { OwnerLayout } from '@/app/layouts/OwnerLayout';
+import { PublicFrameLayout } from '@/app/layouts/PublicFrameLayout';
 import { PasswordChangePage } from '@/pages/account-password';
@@
-  { path: ROUTES.login, element: <LoginPage /> },
-  { path: ROUTES.signup, element: <SignupPage /> },
-  { path: ROUTES.passwordReset, element: <PasswordResetPage /> },
+  {
+    // A1~A3: 고객과 같은 420px 가운데 프레임. 가드·TabBar 없음(app-shell.md §12)
+    element: <PublicFrameLayout />,
+    children: [
+      { path: ROUTES.login, element: <LoginPage /> },
+      { path: ROUTES.signup, element: <SignupPage /> },
+      { path: ROUTES.passwordReset, element: <PasswordResetPage /> },
+    ],
+  },
```

`tests/app/router/routes.test.tsx`: 기존 단언은 대부분 그대로 통과한다(`/login`·`/signup`·`/password-reset` 렌더 단언은 프레임이 있어도 같다). 아래 한 케이스만 추가한다(위치: 현재 `'/login은 셸 없이 로그인 자리를 그린다'`(`:38`) 바로 뒤).

```diff
+  it.each(['/login', '/signup', '/password-reset'])(
+    '%s: 420px 프레임(data-shell="customer") 안에 그려지고 TabBar는 없다 (app-shell.md D-27)',
+    async (path) => {
+      renderAt(path, anonymousFakes());
+      await screen.findByRole('heading', { name: /로그인|회원가입|비밀번호 재설정/ });
+      expect(document.querySelector('[data-shell="customer"] > .app')).not.toBeNull();
+      expect(document.querySelector('.tabs')).toBeNull();
+    },
+  );
```

`'/login은 셸 없이 로그인 자리를 그린다'`(`:38`)의 제목 「셸 없이」는 틀린 설명이 된다. 이름을 `'/login은 상점주 셸 없이 로그인 화면을 그린다'`로 고친다(단언 변경 없음, 약화 아님).

### 12.7 영향 파일·순서

| 순서 | 파일 | 변경 | 소유 |
| --- | --- | --- | --- |
| 1 | `docs/design-system/components/bundle.css` `body` 배경 + `src/app/styles/bundle.css` 복사 | D-26. 별도 fe-developer가 진행 중 | 디자인 시스템 원본 → 복사본 |
| 2 | `src/app/layouts/PublicFrameLayout.tsx` (신규) | 12.4 | `app` |
| 3 | `src/app/router/routes.tsx` | 12.6 diff | `app`(다른 세션과 조정) |
| 4 | `tests/app/layouts/PublicFrameLayout.test.tsx` (신규), `tests/app/router/routes.test.tsx` | 12.8 | fe-qa |
| 영향만 | `e2e/auth.spec.ts`, `e2e/account.spec.ts` | 12.8 확인 | fe-qa |

새 slice·공개 API·포트·wiring 변경 없음. `fsd-structure` §7 대응표의 A1·A2·A3 행에 "프레임: `app/layouts/PublicFrameLayout`"을 덧붙이는 제안은 아래 12.10에 둔다(§7은 설계자가 쓸 수 있으나 이번 지시 범위는 이 문서만이라 제안으로만 적는다).

### 12.8 테스트 목록 (`tdd-workflow` §2)

**`tests/app/layouts/PublicFrameLayout.test.tsx`** (신규, 케이스 3)
- 자식 라우트 내용이 `[data-shell="customer"]` 안에 렌더된다.
- 프레임 직계가 자식 라우트가 그린 `.app`이다(셸이 `.app`을 따로 추가하지 않는다: `[data-shell="customer"] > .app`이 정확히 1개).
- 세션 가드가 없다: `AuthProvider` 없이(또는 비로그인 가짜로) 렌더해도 리다이렉트하지 않고 내용이 보인다. `.tabs` 없음.

**`tests/app/router/routes.test.tsx`** (12.6 diff, 케이스 +3)
- `/login`·`/signup`·`/password-reset`: 프레임 안, TabBar 없음.
- 기존 `/login`·`/signup` 로그인 사용자 리다이렉트 단언은 변경 없음(OWNER → `/owner/today`).

**E2E 영향 확인(fe-qa, 소유는 fe-qa)**
- `e2e/auth.spec.ts`·`e2e/account.spec.ts`: 두 프로젝트(mobile 360, desktop 1280)에서 돈다(`playwright.config.ts:15~16`). 현재 헬퍼는 "지금 뷰포트에서 보이는 것을 누른다"(`account.spec.ts:14·19`)이므로 desktop에서도 `.cta`를 누르는 쪽으로 자동 전환돼 통과할 것으로 본다. 단 `.dk`를 직접 선택하거나 "desktop에서 `.dk`만 보인다"고 단언하는 줄이 있으면 깨진다. 오케스트레이터가 `git grep -n "\.dk" -- e2e`로 확인한다(이 문서 작성 시점에 `auth.spec.ts`에는 `.dk`·`1280` 언급이 없다).
- 실측(`qa-verification` §4.1, 1280×800): A1·A2·A3에서 프레임 폭 420px·가운데·좌우 선, 바깥 `body` 배경이 `--bg`(D-26), `.cta` 보임·`.dk` `display:none`, `.body`만 스크롤, 높이가 화면 높이. 로딩 상태(`.app aria-busy`)도 프레임 안.

### 12.9 정합 이슈

| C | 내용 | 양쪽 근거 |
| --- | --- | --- |
| C-13 | 로그인 page 주석이 "PC(720px 이상)용 한 벌 .dk"라고 하지만 프레임 안에서는 켜지지 않는다. 주석이 사실과 어긋난다 | `LoginPage.tsx:49~51`·`SignupForm.tsx:15` ↔ `design-system-usage` §3.1, 12.5. **해소(5차)**: D-29로 `.dk`와 함께 주석 삭제. `SignupForm.tsx:15` 주석은 「주 버튼 .dk·.cta 두 벌」 → 「주 버튼(.cta)」 |
| C-14 | `layout.md` 역할별 셸 표는 "고객"만 420px 프레임으로 적고 공개 화면(A1~A3)은 따로 적지 않는다. 이번 결정(D-27)이 정본에 없다 | `layout.md` 역할별 셸 표 ↔ 사용자 결정 2026-11-11. 5차: D-33으로 프론트는 수정하지 않는다. **정본 소유자 보고 항목**(보강 여부는 소유자·사용자) |
| C-15 | `routes.test.tsx:38` 케이스 이름 "셸 없이"가 프레임 도입 뒤 부정확하다 | 12.6 |
| C-16 | 원본 `bundle.css` `body{background:var(--paper)}`와 `layout.md` "바깥은 bg"가 어긋났다(D-26로 해소) | `components/bundle.css` ↔ `layout.md` |
| C-17 | 오버레이가 `.body`·`.cta`를 숨길 때 `.body{display:grid}` 등이 `hidden` 속성을 덮어, `hidden` + 인라인 `display:none`을 함께 쓰는 편차가 있었다(`shellOverlay.ts` 주석 "인라인 display도 함께 끈다"). D-30으로 해소: 원본 `bundle.css`의 `[hidden]` 전역 규칙 사용, 인라인 우회 제거 | `src/shared/lib/shellOverlay.ts` ↔ `components/bundle.css:39` |
| C-18 | D-30의 전역 `[hidden]{display:none !important}`가 기존 `hidden` 사용처에 미치는 영향. 판정: **화면 변화 없음**. `.lbl`(`bundle.css:150`)은 `font-size`·`color`만 있고 `display`가 없어 `<label hidden>`은 UA 기본 `display:none`으로 이미 숨어 있었다(ApprovalsPanel.tsx:46, MembersPanel.tsx:92). `PhotoPickSheet.tsx:45·52`의 `<input type=file hidden>`과 `Overlay.tsx:91`의 `<span hidden>`은 클래스가 없어 마찬가지다. `src` 전체 `hidden` 속성 사용처는 이 5곳과 `shellOverlay.ts`뿐이다 | `bundle.css:150~153` ↔ 위 5곳 |

### 12.10 남길 작업 주석, §7 대응표 제안

| ID | 위치 | 태그 | 원문 초안 |
| --- | --- | --- | --- |
| A-9 | (철회, 5차) | 없음 | D-29 변경으로 `.dk`를 지우므로 `TODO`를 남기지 않는다. 이 ID는 다시 쓰지 않는다 |

FIXME 없음. 기존 `LoginPage.tsx:49` 주석의 "PC(720px 이상)용"은 `.dk` 블록과 함께 지운다(C-13 해소).

`fsd-structure` §7 제안(오케스트레이터 또는 다음 설계자가 반영): A1·A2·A3 행의 "쓰는 features" 칸에 `app/layouts/PublicFrameLayout`(프레임, 가드 없음)을 덧붙인다.

### 12.11 질문 목록

| Q | 내용 | 임시 동작(구현을 막지 않음) |
| --- | --- | --- |
| Q-11 | `layout.md` 역할별 셸 표에 공개 화면(A1~A3)의 420px 프레임을 적을지(C-14). 정본 수정은 사용자 소관 | 해결: D-33(프론트는 수정 안 함, 정본 소유자 보고 항목) |
| Q-12 | A1~A3의 `.dk` 복사본을 이번에 지울지, 숨은 채로 둘지(A-9) | 해결: D-29 변경(지운다) |
| Q-13 | 새 `PublicFrameLayout` 대신 `CustomerLayout access="public"`을 재사용할지(12.4) | 해결: D-28 확정(새 레이아웃) |

### 12.12 `.dk` 삭제와 셸 5차 변경의 테스트 (5차, D-29·D-31·D-32, 번들 A)

**코드 변경 요약**
- `src/pages/login/presentation/LoginPage.tsx`: `.body > .dk` 가입 안내 블록과 「PC(720px 이상)용」 주석 삭제. `.cta`의 「모바일용 한 벌」 주석은 「가입 안내(.cta)」로 고친다. `SignupLinks`는 `.cta` 한 곳에서만 쓴다.
- `src/features/auth/presentation/SignupForm.tsx`: `btn pri dk` 제출 버튼 삭제, 파일 머리 주석 「주 버튼 .dk·.cta 두 벌」 → 「주 버튼(.cta)」. `.cta`의 `submit` 버튼이 유일한 제출 버튼이며 Enter 제출은 그대로다.
- `src/features/auth/presentation/PasswordResetForm.tsx`: `btn pri dk` 제출 버튼 삭제.
- `src/shared/lib/shellOverlay.ts`: `hide()`가 이미 `el.hidden`인 요소는 목록·`scrolls`에 넣지 않음(D-31), 파일 머리에 중첩 미지원 제약 주석(D-32).

**바뀌는 기존 테스트 (jsdom이 컨테이너 쿼리를 평가하지 않아 `.dk`·`.cta` 두 벌이 모두 잡히던 곳)**

| 파일:줄 | 현재 | 바꿀 내용 |
| --- | --- | --- |
| `tests/pages/login/LoginPage.test.tsx:54~69` 「회원가입·비밀번호 재설정·입점 신청은 A2·A3로 가는 링크다」 | `getAllByText('계정이 없나요?')` 길이 2, `회원가입` 링크 2개, `입점 신청` 링크 2개 | 길이 1, `getByRole`/`getByText`로 단건. 주석 「jsdom은 컨테이너 쿼리를 평가하지 않아 …」 삭제 |
| `LoginPage.test.tsx:71~85` 「가입 안내는 PC용 .dk … 두 벌이고」 | `.body > .dk`와 `.app > .cta` 둘 | 이름을 「가입 안내는 .cta 한 벌이고 .cta는 display를 직접 정하지 않는다」로, `.body > .dk`가 **없음**(`toBeNull`)을 단언, `.cta` 안 「계정이 없나요?」·「회원가입」(`btn`)·「입점 신청」(`link`)은 유지. 「비밀번호 재설정」의 `nextElementSibling` 단언은 삭제(근거 블록이 없어짐) |
| `LoginPage.test.tsx:228~248` `it.each([0, 1])` 두 케이스(「회원가입」, 「입점 신청」) | 0번째·1번째 벌을 눌러 `from` 전달 확인 | `it.each` 제거, 단건 `getByRole`로 한 번 누르고 같은 단언(`/signup`, `?role=owner`, `state.from`) |
| `tests/pages/signup/SignupPage.test.tsx:47` `submitButtons` 와 `:114~` 「`가입하기`는 .cta 안과 .dk 두 벌이고…」 | `getAllByRole` 길이 2, `.cta` 1개, `.dk` 1개 | 이름을 「`가입하기`는 .cta 안 한 벌이고 처음에는 비활성이다」로, 길이 1·`.cta` 안, `.dk` 없음 단언. `expectAllDisabled(submitButtons(), …)`와 `submitButtons()[0]` 사용 줄(:125·:128·:136·:151~:239)은 헬퍼를 `getByRole`로 바꿔 한 번에 수정(단언 기대값은 그대로) |
| `tests/pages/password-reset/PasswordResetPage.test.tsx:36` `confirmButtons` 와 `:72~74` 「`비밀번호 바꾸기` 두 벌이 비활성」 | `getAllByRole` 길이 2 | 이름을 「…한 벌이 비활성」, `getByRole`로, 길이 단언 삭제(대신 `.cta` 안임을 단언). 사용 줄(:109·:111·:119·:137·:151·:169·:266)은 헬퍼 수정으로 해결 |

- 단언을 약하게 만드는 변경이 아니다(두 벌 → 한 벌로 줄어든 마크업에 맞춘 것). 보고에 "삭제한 단언은 `.dk` 존재·개수뿐"이라고 적는다(F16).
- `e2e/account.spec.ts:14·19` 「`.cta`와 `.dk` 두 벌」 주석은 A1~A3 부분을 고친다(`visibleButton`·`visibleLink`는 `visible` 필터라 동작 변화 없음). `:193` C8은 `ProfileForm`의 `.dk`라 그대로다. `e2e/auth.spec.ts`는 `.dk` 언급이 없다.

**신규 테스트**

`tests/shared/lib/shellOverlay.test.ts` (케이스 +2, D-31)
- 열기 전 `.body`가 이미 `hidden`이면 닫은 뒤에도 `hidden`이다(되살리지 않는다). 같은 프레임의 다른 `.body`는 정상적으로 복원된다.
- 열기 전 이미 `hidden`인 `.cta`도 닫은 뒤 `hidden`이 유지된다.
- (D-32 방어 유지) 기존 「오버레이 둘을 열고 하나를 닫으면 hidden 유지, 마지막을 닫으면 해제」 케이스는 그대로 둔다. 중첩 사용을 허용한다는 뜻이 아니라 `count` 방어 검증이며, 케이스 이름에 「(방어, 지원하는 사용 아님)」을 덧붙인다.

`tests/pages/login/LoginPage.test.tsx`
- 프레임 안(420px) 렌더에서 `.dk` 요소가 하나도 없다: `document.querySelector('.dk')`가 `null`. (`SignupPage`·`PasswordResetPage` 테스트에도 같은 한 줄)

**번들 A 완료 조건**: `tdd-workflow` §6의 생략 대상이 아니므로 Red 대상은 위 신규 3건과 바뀐 단언들이다. 삭제만으로 통과하는 변경이 많아 골격 단계는 없고, 테스트를 먼저 고쳐 Red(`.dk`가 아직 있음)를 확인한 뒤 마크업을 지운다.
