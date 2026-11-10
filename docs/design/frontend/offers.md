# offers 영역 1차: C1 홈 · 주변 할인 + 고객 셸

- 대상: `features/offers`(영역 첫 생성), `widgets/customer-nav`(신규), `pages/home`(신규), `app/layouts/CustomerLayout.tsx`(신규), `app/router/routes.tsx`(`/` 교체), `app/container.ts`(`wireOffers` 한 줄), `shared/lib/routes.ts`(경로 2개 추가), `shared/lib/useNow.ts`(신규)
- 대응 화면: C1 홈 · 주변 할인(비로그인 가능). 고객 셸(하단 탭 홈·내 예약·마이). 범위 밖: C1a 본 구현(자리만, D-4·D-33), C2 이후, 상점주 화면
- 상태: 설계안 1차. 사용자가 D-1~D-34와 Q-1~Q-12를 결정했다(2026-11-10). D-4·D-6·D-12는 추천 ① 확정. 나머지 D는 적힌 값 그대로 확정. 단 문구·표기 정본이 없는 D-11·D-15·D-16·D-20·D-21·D-23·D-32는 "정본이 생길 때까지 이 임시 문구·표기로 진행"이 확정된 것이라 값 자체는 임시이고 M-1·M-9 TODO가 남는다(결정 표 상태 열에 구분 표시). 구현을 막는 항목은 없다. Q-8·Q-9는 프론트 범위 밖이라 사용자에게 보고됨, 미결(외부).
- 정본: 화면 `../../design-system/screens.md` C1·C1a, `layout.md`(역할별 셸·화면 골격), `states.md`(할인·계산값), `content.md`(숫자·시간), `open-issues.md`(C1a), `wireframe.html` 301~323줄, `components/{OfferCard,TabBar,AppBar,Chip,StatusTag,EmptyState,Skeleton}/README.md`(EmptyState `preview.html` 6줄 문구). API `../../reference/catalog.md` 공통 객체 Offer·§8, `../../reference/README.md`
- 백엔드 실재 확인(`frontend-orchestration.md` §6): `backend/src/catalog/presentation/router.py:136~158`(`GET /v1/offers`, 인증 없음, `lat`·`lng`·`radius_km`·`category`·`keyword`·`status`(`PublicOfferStatus`, 기본 `ON_SALE`, 단일 값)·`sort`·`page`·`size`(1~100)), `schemas.py:126~168`(`OfferResponse`), `:308~326`(`NearbyOfferItem{offer, distance, unit}`, `NearbyOfferListResponse{items,page,size,total}`), `service.py:172~209`(`list_nearby_offers`: `sort.ensure_usable(area)`, 위치 없으면 반경 필터 없음·`distance` null), `domain/search.py:8·37~45·59`(`DISTANCE_UNIT="km"`, `OfferSort`, `distance` 정렬은 위치 필요, 거리 소수 2자리), `infrastructure/repositories.py:192~209·333~386`(상태 조건·정렬·페이지), `domain/discount_offer.py:273~275`(할인율 정수 버림). URI·필드·정렬 값은 명세 §8과 같다. 차이는 C-1~C-3.
- 기존 코드 현황: `/`는 `app/router/placeholders.tsx`의 `HomePlaceholder`(`<h1>마감 직전</h1>`). 하단 탭은 `widgets/owner-nav`·`widgets/admin-nav`만 있고 고객용은 없다. `shared/lib/useAsync.ts`(abort·reload 처리), `shared/lib/di.ts`, `features/auth`(`useAuth`, `loginRedirectState`, `ROUTES.ownerSignup`)가 있다. `features/offers`·`entities/offer`·`widgets/customer-nav`·`pages/home`은 없다.

## 1. 계층 배치와 slice

| FSD | slice | 화면 | 내용 |
| --- | --- | --- | --- |
| shared | `shared/lib/useNow.ts` | 공통 | 일정 간격으로 `Date`를 갱신하는 훅. 업무를 모름 |
| shared | `shared/lib/routes.ts` | 공통 | `ROUTES.reservations`(`/reservations`), `ROUTES.my`(`/my`) 추가 (D-6) |
| features | `features/offers` | C1 (이후 C1a, C2, O2…) | 포트·구현체·훅·화면 부품. 이번에는 주변 할인 조회·위치·카드·정렬·검색 |
| widgets | `widgets/customer-nav` | 고객 셸 | 하단 탭 바 3개(홈·내 예약·마이). 비로그인 탭 → A1 이동 규칙 |
| pages | `pages/home` | C1 | `HomePage`: 상단 바·검색·정렬·목록·입점 신청 링크 조립 |
| app | `app/layouts/CustomerLayout.tsx` | 고객 셸 | 420px 가운데 프레임 + `.app` + 탭 바(핸들이 있는 라우트만). 가드 없음 (D-5) |
| app | `app/layouts/CustomerLayout.module.css` | 고객 셸 | PC 420px 프레임(CSS Module, 토큰 변수만, D-5) |
| app | `app/router/routes.tsx`, `app/container.ts` | 조립 | `/`를 `HomePage`로, `...wireOffers()` 한 줄 |

- `entities/offer`는 만들지 않는다(D-3): 이번에 `Offer`를 쓰는 영역은 offers 하나뿐이다. C2(예약 생성이 할인을 읽음)에서 `reservations`가 필요로 할 때 `Offer` 타입·`OfferRepository` 포트·토큰·표시 규칙만 내린다(`fsd-structure` §6). `OfferCard`도 그때 내릴지 정한다.
- 사용자 설계 요청의 "`widgets/<명사>`"는 `customer-nav`로 한다(`owner-nav`·`admin-nav`와 같은 이름 규칙, `fsd-structure` §5).

## 2. 파일 목록과 export

### 2.1 `shared`

- `shared/lib/routes.ts`: `ROUTES.reservations = '/reservations'`, `ROUTES.my = '/my'` 추가만.
- `shared/lib/useNow.ts`: `useNow(intervalMs: number): Date`. 마운트 시 `new Date()`, `intervalMs`마다 갱신, 언마운트에서 `clearInterval`. (`new Date()`는 domain이 아니라 이 훅에서만 부른다, `layer-architecture` §3)

### 2.2 `features/offers/domain` (순수 TypeScript, F6)

- `offer.ts`
  - `OfferStatus = 'SCHEDULED' | 'ON_SALE' | 'SOLD_OUT' | 'CLOSED' | 'SUSPENDED'`
  - `Offer { id, productId, storeId, storeName, productName, originalPrice, salePrice, discountRate, initialStock, remainingStock, isSoldOut, salesStart: Date, salesEnd: Date, pickupStart: Date, pickupEnd: Date, status: OfferStatus, isActive }`
  - `NearbyOffer { offer: Offer; distanceKm: number | null }`
  - `NearbyOfferPage { items: NearbyOffer[]; page: number; size: number; total: number }`
- `offerFormat.ts` (`content.md` 숫자 표)
  - `formatWon(n: number): string` → `"11,500원"`
  - `formatPlainPrice(n: number): string` → `"12,000"` (정가, "원" 없음)
  - `formatDiscountRate(rate: number): string` → `"50%"`
  - `formatDistance(km: number | null): string | null` → `"0.4km"`, null이면 null
  - `formatStoreLine(storeName: string, km: number | null): string` → `"망원베이커리 · 0.4km"`, 거리 없으면 상점명만
  - `formatRemaining(n: number): string` → `"남은 3개"`
- `offerCard.ts` (`states.md` "화면에서 계산하는 값"·할인 표)
  - `OfferCardState = 'onSale' | 'soldOut' | 'ended' | 'scheduled'`
  - `offerCardState(o: Offer, now: Date): OfferCardState`
  - `minutesUntilSalesEnd(o: Offer, now: Date): number` (올림, 0 이상)
  - `formatSalesEndLabel(minutes: number): string` → `"판매 마감 42분 전"`
  - `formatPickupWindow(o: Offer, now: Date): string` → `"오늘 18:00–20:00"`
  - `CARD_STATE_TAG: Record<'soldOut'|'ended'|'scheduled', { text: string; tone: 'mute' | 'none' }>` — `품절`(mute), `판매 종료`(mute), `판매 예정`(태그 톤 없음: `states.md` 할인 표)
- `search.ts`
  - `GeoPoint { lat: number; lng: number }`, `SearchArea { point: GeoPoint; radiusKm: number }`
  - `DEFAULT_RADIUS_KM = 3`, `WIDEN_RADIUS_KM = 5`, `PAGE_SIZE = 20`, `KEYWORD_MAX_LENGTH = 100`
  - `OfferSortKey = 'sales_end' | 'distance' | 'discount_rate' | 'price'` (서버 `sort` 값 그대로)
  - `SORT_CHIPS: readonly { key: OfferSortKey; label: string }[]` — 마감 임박, 가까운 순, 할인율, 낮은 가격 순서
  - `DEFAULT_SORT: OfferSortKey = 'sales_end'`
  - `isSortSelectable(key, hasLocation): boolean`, `resolveSort(key, hasLocation): OfferSortKey`
  - `normalizeKeyword(raw: string): string | undefined`
  - `NearbyOfferQuery { area: SearchArea | null; keyword: string | undefined; sort: OfferSortKey; page: number; size: number }`
  - `queryKey(q: Omit<NearbyOfferQuery, 'page'>): string` (페이지를 뺀 조회 조건의 식별 문자열, 훅이 조건 변경을 알아채는 데 씀)
  - `hasNextPage(p: NearbyOfferPage): boolean`, `appendPage(prev: NearbyOffer[], next: NearbyOffer[]): NearbyOffer[]` (id 중복 제거, 앞쪽 우선)
  - `LocationStatus = 'locating' | 'located' | 'unavailable'`, `locationChipLabel(status, radiusKm): string`
- `offerEmpty.ts`
  - `EmptyAction = 'clearKeyword' | 'widenRadius' | null`
  - `emptyView(input: { keyword: string | undefined; hasLocation: boolean; radiusKm: number }): { title: string; reason: string; action: EmptyAction; actionLabel: string | null }`
- `offerRepository.ts` (domain 포트, §3.1)
- 시그니처 표현용 타입을 해당 파일에서 export한다(소비자는 같은 slice 안과 테스트, `index.ts`로는 내보내지 않음): `EmptyView`(`offerEmpty.ts`, `emptyView`의 반환 타입)

### 2.3 `features/offers/application`

- `ports.ts`: `LocationProvider`, `LocationResult` (§3.1)
- `tokens.ts`: `OfferRepositoryToken`, `LocationProviderToken`
- `errorInfo.ts`: `readErrorInfo(e: unknown): { status; errorCode; message }` (`shared/api`의 `ApiError`를 application이 import할 수 없어 구조로 읽는다. `features/admin/application/errorInfo.ts`와 같은 방식)
- `nearbyListState.ts`: 순수 reducer `nearbyListReducer(state, action): NearbyListState`와 초기값 `initialNearbyListState` (React 없음, §3.2)
- `useCurrentLocation.ts`: `useCurrentLocation(): { status: LocationStatus; point: GeoPoint | null; retry(): void }`
- `useNearbyOffers.ts`: `useNearbyOffers(query: NearbyOfferQuery | null): NearbyOffersView`
- `useHomeOffers.ts`: `useHomeOffers(): HomeOffers` (위치·반경·정렬·검색어를 묶어 조회 조건을 만들고 목록을 돌려줌)
- 시그니처 표현용 타입을 해당 파일에서 export한다(`index.ts`로는 `HomeOffers`만 내보냄, F2·F18과 무관): `NearbyListState`·`NearbyListAction`(`nearbyListState.ts`), `NearbyOffersView`(`useNearbyOffers.ts`)

### 2.4 `features/offers/infrastructure`

- `httpOfferRepository.ts`: `HttpOfferRepository implements OfferRepository` (DTO 타입·변환은 이 파일 안에서만)
- `browserLocationProvider.ts`: `BrowserLocationProvider implements LocationProvider` (`navigator.geolocation`)

### 2.5 `features/offers/presentation`

- `OfferCard.tsx`: `OfferCard({ item, now })`
- `OfferCardSkeleton.tsx`: `OfferCardSkeleton()`
- `SortChips.tsx`: `SortChips({ sort, hasLocation, onSelect })`
- `OfferSearchForm.tsx`: `OfferSearchForm({ keyword, onSubmit })`
- 시그니처 표현용 props 타입을 각 파일에서 export한다(`index.ts`로는 내보내지 않음): `OfferCardProps`, `SortChipsProps`, `OfferSearchFormProps`. `widgets/customer-nav/domain/customerTabs.ts`는 `CustomerTab`, `TabTarget`을 export한다.
- `LocationChip.tsx`: `LocationChip({ label })` (비대화형, D-4)
- `NearbyOfferSection.tsx`: `NearbyOfferSection({ home })` — 로딩·오류·빈·성공·더 보기를 그리는 목록 영역
- `SortChips.module.css`: `Chip` 비활성 모양 한 곳뿐(C-5, M-7). 그 밖의 CSS Module은 만들지 않는다.

### 2.6 `features/offers/wiring.ts`

```ts
export function wireOffers(): Binding[] {
  return [
    bind(OfferRepositoryToken, new HttpOfferRepository()),
    bind(LocationProviderToken, new BrowserLocationProvider()),
  ]
}
```
- 두 토큰 모두 offers 영역이 소유·등록한다. `app/container.ts`는 `import { wireOffers } from '@/features/offers/wiring'`와 `...wireOffers()` 한 줄만 더한다. `tests/app/container.test.ts` 토큰 목록에 `OfferRepositoryToken`·`LocationProviderToken`을 같은 커밋에서 더한다(`layer-architecture` §6.7).

### 2.7 공개 API

`features/offers/index.ts`
```ts
export type { Offer, OfferStatus, NearbyOffer, NearbyOfferPage } from './domain/offer'
export type { GeoPoint, SearchArea, OfferSortKey, NearbyOfferQuery } from './domain/search'
export type { OfferRepository } from './domain/offerRepository'
export type { LocationProvider, LocationResult } from './application/ports'
export { OfferRepositoryToken, LocationProviderToken } from './application/tokens'
export { useHomeOffers } from './application/useHomeOffers'
export type { HomeOffers } from './application/useHomeOffers'
export { OfferCard } from './presentation/OfferCard'
export { OfferSearchForm } from './presentation/OfferSearchForm'
export { SortChips } from './presentation/SortChips'
export { LocationChip } from './presentation/LocationChip'
export { NearbyOfferSection } from './presentation/NearbyOfferSection'
```
- infrastructure와 `wiring.ts`는 내보내지 않는다(F18). `useNearbyOffers`·`useCurrentLocation`·domain 함수는 공개하지 않는다(page가 쓰지 않음). C1a가 들어오면 그때 `LocationSheet`를 더한다.

`widgets/customer-nav/index.ts`: `CustomerTabBar`, `CUSTOMER_TABS`, `activeCustomerTab`, `type CustomerTabKey`.
`pages/home/index.ts`: `HomePage`.

## 3. 동작 규칙

### 3.1 포트

| 포트 | 위치 | 시그니처 | 토큰 | 구현체(소유 영역) |
| --- | --- | --- | --- | --- |
| `OfferRepository` | `features/offers/domain/offerRepository.ts` (domain 포트, 이번에는 이 영역만 씀 → D-3) | `findNearby(q: NearbyOfferQuery, signal?: AbortSignal): Promise<NearbyOfferPage>` | `OfferRepositoryToken` (`application/tokens.ts`) | `HttpOfferRepository` (offers) |
| `LocationProvider` | `features/offers/application/ports.ts` (application 포트: 브라우저 기능, 도메인 규칙과 무관) | `current(signal?: AbortSignal): Promise<LocationResult>`. 거절하지 않는다 | `LocationProviderToken` | `BrowserLocationProvider` (offers) |

- `LocationResult = { status: 'located'; point: GeoPoint } | { status: 'unavailable' }`. 권한 거부·미지원·시간 초과·위치 확인 실패를 모두 `unavailable`로 합친다(화면 동작이 같다, D-9). `signal`이 이미 abort되면 결과를 무시한다(geolocation은 취소할 수 없음).
- `OfferRepository`에는 `findById`를 이번에 만들지 않는다(C2 범위).

### 3.2 domain

**`formatWon(n)`**: 정수 원 단위, 천 단위 쉼표 + "원". 로케일 의존 API(`toLocaleString`)를 쓰지 않고 정규식으로 쉼표를 넣는다(실행 환경 차이 방지). 0 → `0원`.
**`formatPlainPrice(n)`**: 같은 규칙, "원" 없음.
**`formatDiscountRate(rate)`**: `` `${rate}%` ``. 할인율은 서버 값을 그대로 쓴다(계산하지 않음, D-14, C-1).
**`formatDistance(km)`**: null → null. 아니면 `Math.round(km * 10) / 10`을 소수 1자리로 + `km` (`0.35` → `0.4km`, `0` → `0.0km`, `1` → `1.0km`, `12.34` → `12.3km`). `toFixed`만으로 반올림하지 않는다(부동소수점 `0.35.toFixed(1)` = `"0.3"`). 서버 `unit`은 `km` 고정(`search.py:8`)이라 쓰지 않는다(D-17).
**`formatStoreLine(name, km)`**: 거리가 있으면 `"<name> · <거리>"`(구분자 가운뎃점, `content.md`), 없으면 `name`.

**`minutesUntilSalesEnd(o, now)`**: `Math.ceil((o.salesEnd - now) / 60000)`, 0 미만은 0. `salesEnd - now`가 정확히 42분 → 42, 41분 30초 → 42, 1초 → 1, 0 → 0, 음수 → 0 (D-15: 올림. 판매 중인데 "0분 전"이 보이지 않게).
**`formatSalesEndLabel(minutes)`** (`content.md` "판매 마감 N분 전" / "N시간 N분 전", 와이어프레임 `판매 마감 1시간 10분 전`):
- 1~59 → `판매 마감 N분 전`
- 60 이상: 시간 = `floor(m/60)`, 분 = `m % 60`. 분이 0이면 `판매 마감 N시간 전`, 아니면 `판매 마감 N시간 M분 전` (D-15, 임시: 정각·24시간 이상 표기 정본 없음)
- 0 → `판매 마감 0분 전` (`offerCardState`가 `ended`가 아닐 때만 호출되므로 실제로는 거의 안 나옴)
**`offerCardState(o, now)`** (서버 우선순위 `CLOSED > SUSPENDED > 마감 경과 > SCHEDULED > SOLD_OUT > ON_SALE`, `discount_offer.py:203`):
1. `status`가 `CLOSED`·`SUSPENDED`이거나 `salesEnd <= now` → `ended` (정각은 마감: 백엔드 `sales_end > now`가 판매 중, `repositories.py:203`)
2. `status === 'SCHEDULED'` → `scheduled`
3. `status === 'SOLD_OUT'` 또는 `remainingStock === 0` → `soldOut`
4. 그 외 → `onSale`
**`formatPickupWindow(o, now)`** (`content.md`: 24시간·en dash `–`·날짜 MM/DD): 시작일이 `now`와 같은 날(브라우저 로컬 시간)이면 `오늘 HH:mm–HH:mm`, 다른 날이면 `MM/DD HH:mm–HH:mm`. 끝 시각은 시:분만(자정을 넘겨도 날짜 붙이지 않음). 시·분·월·일은 0으로 채운다(`09:05`, `11/07`) (D-16, 임시: 다른 날 표기 정본 없음). 시간대는 브라우저 로컬(D-28).

**`isSortSelectable(key, hasLocation)`**: `distance`만 위치가 필요(`ensure_usable`, 서버가 400을 냄). **`resolveSort(key, hasLocation)`**: 선택 불가면 `DEFAULT_SORT`. 위치가 나중에 사라져도 400을 부르지 않게 한다(D-9).
**`normalizeKeyword(raw)`**: 앞뒤 공백 제거 후 빈 문자열이면 `undefined`, 100자 초과는 100자로 자른다(서버 `max_length=100`, 초과 시 422). 서버도 공백만 입력하면 조건을 건너뛰지만(`catalog.md` §8 확정) 요청에서 뺀다.
**`queryKey(q)`**: `lat`·`lng`·`radiusKm`·`keyword`·`sort`·`size`를 구분자로 이은 문자열. 한 값만 달라도 달라지고, 같은 값이면 같다.
**`hasNextPage(p)`**: `p.page * p.size < p.total`.
**`appendPage(prev, next)`**: `prev` 뒤에 `next`를 붙이되 `offer.id`가 이미 있는 것은 뺀다(스크롤 중 마감·품절로 항목이 밀려 같은 항목이 두 쪽에 나올 수 있음).
**`locationChipLabel(status, radiusKm)`**: 반경은 `3km`·`0.5km`(정수면 소수점 없음). `located` → `내 주변 · 3km`, `locating` → `위치 확인 중`, `unavailable` → `위치 없음` (D-21, 임시: 와이어프레임의 「망원동 · 3km」는 동 이름을 알 수 있어야 하는데 방법이 없음, C-4).
**`emptyView(input)`**:
- 검색어 있음 → `{ title: '검색 결과가 없어요', reason: '다른 상품명으로 검색해 보세요.', action: 'clearKeyword', actionLabel: '검색어 지우기' }` (임시, D-32)
- 검색어 없음 → `title: '근처에 마감 할인이 없어요'`, `reason: '반경을 넓히거나 저녁 시간에 다시 확인해 보세요.'` (`components/EmptyState/preview.html` 6줄). `hasLocation`이고 `radiusKm < WIDEN_RADIUS_KM`이면 `action: 'widenRadius'`, `actionLabel: '반경 5km로 넓히기'`(EmptyState README), 아니면 `action: null`
  - 위치가 없으면 반경이 적용되지 않으므로 넓히기를 내지 않는다.

### 3.3 application

**`nearbyListReducer`** 상태: `{ status: 'loading' | 'error' | 'ready'; key: string; items: NearbyOffer[]; page: number; total: number; hasMore: boolean; loadingMore: boolean; moreFailed: boolean; error: unknown }`. 액션:
- `queryChanged(key)` → 로딩, `items=[]`, `page=0`, 이전 오류·더 보기 상태 초기화
- `firstLoaded(key, page)` → `ready`, `items = page.items`, `hasMore = hasNextPage(page)`. `key`가 현재와 다르면 무시(늦게 온 이전 요청)
- `firstFailed(key, error)` → `error`
- `moreRequested` → `ready`이고 `hasMore`이고 `!loadingMore`일 때만 `loadingMore = true`, `moreFailed = false`. 그 외는 같은 상태
- `moreLoaded(key, page)` → `items = appendPage(items, page.items)`, `page = page.page`, `hasMore`, `loadingMore = false`. `key`가 현재와 다르면 무시(늦게 온 더 보기 응답이 다른 조건의 목록에 섞이지 않게)
- `moreFailed(key, error)` → 목록 유지, `loadingMore = false`, `moreFailed = true`. `key`가 현재와 다르면 무시
- (`firstLoaded`·`firstFailed`·`moreLoaded`·`moreFailed` 모두 `key` 불일치면 무시한다)
- `reload` → `queryChanged`와 같은 효과

**`useNearbyOffers(query)`** → `NearbyOffersView`:
`{ status: 'loading' | 'error' | 'empty' | 'success'; items: NearbyOffer[]; total: number; hasMore: boolean; loadingMore: boolean; moreFailed: boolean; loadMore(): void; reload(): void }`
- 포트는 `useDep(OfferRepositoryToken)`. `query`가 `null`이면 로딩이고 포트를 부르지 않는다(위치 확인 중).
- 조회 조건(`queryKey`)이 바뀌면 이전 요청을 abort하고 1쪽부터 다시 로딩한다. 첫 요청은 `page: 1, size: PAGE_SIZE`.
- 리듀서 state의 `key`가 현재 질의 key와 다르면 `loading`으로 본다(질의 변경 직후 한 프레임 이전 목록이 보이지 않게).
- 첫 쪽 성공 + `items.length === 0` → `empty`(`total === 0`). 그 외 성공 → `success`.
- `loadMore()`는 `success`이고 `hasMore`이며 더 불러오는 중이 아닐 때만 `page + 1`을 요청한다. 실패해도 목록은 남고 `moreFailed`가 켜지며 `loadMore()`를 다시 부르면 재시도한다.
- 언마운트·조건 변경 시 `AbortController`로 정리하고 정리된 요청의 결과로는 상태를 바꾸지 않는다(F10). `reload()`는 첫 쪽부터 다시.
- 오류는 `status: 'error'`로만 알린다. 문구는 presentation이 고정 문구를 쓴다(D-23). 서버 `message`는 쓰지 않는다.

**`useCurrentLocation()`**: 포트 `useDep(LocationProviderToken)`. 마운트 시 `current(signal)` 호출. 대기 중 `locating`, `located`(+`point`), `unavailable`. 포트가 예외를 던져도 `unavailable`로 본다. `retry()`는 다시 `locating`으로 돌려 다시 요청한다(C1a의 「◎ 현재 위치 사용」이 쓸 자리). 언마운트 시 결과 무시.

**`useHomeOffers()`** → `HomeOffers`:
```
{ now: Date
  location: { status: LocationStatus; hasLocation: boolean; retry(): void }
  radiusKm: number; setRadiusKm(km: number): void      // C1a가 쓸 자리 (D-33)
  sort: OfferSortKey; hasLocation: boolean; selectSort(key: OfferSortKey): void
  keyword: string | undefined; submitKeyword(raw: string): void
  chipLabel: string
  list: NearbyOffersView
  empty: ReturnType<typeof emptyView>; runEmptyAction(): void }
```
- `now = useNow(30_000)`(D-15).
- 조회 조건: 위치 상태가 `locating`이면 `query = null`(목록은 로딩). `located`면 `area = { point, radiusKm }`, `unavailable`이면 `area = null`(`lat`·`lng`·`radius_km`을 보내지 않음. 백엔드는 반경 필터 없이 전체 조회·`distance: null`, `catalog.md` §8 확정과 `service.py:186~193`).
- `sort`는 사용자가 고른 값에 `resolveSort(selected, hasLocation)`를 적용해 돌려준다. `selectSort(key)`는 `isSortSelectable`이 거짓이면 아무것도 하지 않는다.
- `submitKeyword(raw)`는 `normalizeKeyword`를 거쳐 저장, 조건이 바뀌면 1쪽부터 다시 조회.
- `runEmptyAction()`: `clearKeyword`면 검색어를 지우고, `widenRadius`면 `setRadiusKm(WIDEN_RADIUS_KM)`, `null`이면 아무것도 하지 않는다.
- 반경은 `DEFAULT_RADIUS_KM = 3`으로 시작. `// open-issues: C1a 위치는 현재 위치만 쓴다(주소 → 좌표 변환 확인 필요)`를 `BrowserLocationProvider`에 남긴다.
- 이 훅은 `useAuth`를 쓰지 않는다. 공개 API라 로그인 상태와 무관하다.

### 3.4 infrastructure

**`HttpOfferRepository.findNearby(q, signal)`**: `apiGet<NearbyOfferListDto>('/v1/offers?' + URLSearchParams, signal)`.
- 쿼리 순서와 포함 규칙: `lat`, `lng`, `radius_km`(세 값은 `q.area`가 있을 때만), `keyword`(`undefined`가 아닐 때만), `sort`, `page`, `size`. `status`·`category`는 보내지 않는다(서버 기본 `ON_SALE`, D-12). 숫자는 `String(n)`.
- 요청은 `apiGet`을 쓴다. 토큰이 있으면 `Authorization` 헤더가 붙지만 이 엔드포인트는 인증을 보지 않아 영향 없다(`router.py:136~158`에 `viewer` 의존성 없음). 응답이 401이 되는 경로가 없어 `features/auth` FIXME(`useAuthController.ts:12`)와 무관(D-26).
- 변환(DTO → domain, F9):

| 명세·스키마 필드 | 타입 | domain 필드 | 변환 |
| --- | --- | --- | --- |
| `items[].offer.id` | UUID | `offer.id` | 문자열 |
| `.product_id`, `.store_id` | UUID | `productId`, `storeId` | 문자열 |
| `.store_name`, `.product_name` | string | `storeName`, `productName` | |
| `.original_price`, `.sale_price` | int | `originalPrice`, `salePrice` | number |
| `.discount_rate` | int | `discountRate` | 서버 값 그대로 (C-1) |
| `.initial_stock`, `.remaining_stock` | int | `initialStock`, `remainingStock` | |
| `.is_sold_out` | bool | `isSoldOut` | |
| `.sales_start/_end`, `.pickup_start/_end` | datetime(오프셋 포함 ISO, DB `timezone=True`) | `salesStart/End`, `pickupStart/End` | `new Date(s)` |
| `.status` | enum 5종 | `status` | 알 수 없는 값이면 `Error`를 던진다(목록 오류 화면) |
| `.is_active` | bool | `isActive` | |
| `items[].distance` | float \| null | `NearbyOffer.distanceKm` | |
| `items[].unit` | string | (쓰지 않음) | `km` 고정, D-17 |
| `page`, `size`, `total` | int | `NearbyOfferPage` 같은 이름 | |

- 명세 `reference/catalog.md` 공통 객체 Offer와 `schemas.py` `OfferResponse`의 필드는 같다(17개 필드 대조). 이미지 필드는 둘 다 없다(C-3).
- 오류: `ApiError`를 그대로 던진다. 400(`lat과 lng는 함께`, `distance 정렬은 위치 정보가 필요`)은 `resolveSort`·`area` 규칙 때문에 정상 흐름에서는 나오지 않는다.

**`BrowserLocationProvider.current(signal)`**: `navigator.geolocation`이 없거나 정책상 막히면 `{status:'unavailable'}`. 있으면 `getCurrentPosition(ok, fail, { enableHighAccuracy: false, timeout: 10_000, maximumAge: 300_000 })`(D-8, 확정). 성공 → `located`, 실패(어떤 코드든) → `unavailable`. `signal.aborted`이면 호출 결과를 쓰지 않는다. 위치 값은 저장하지 않는다(메모리에만, 새로고침하면 다시 요청).

### 3.5 presentation

모든 화면 문구는 아래 표를 따른다. 정본이 있는 것은 출처를, 없는 것은 "임시"로 표시한다(D-20 한 묶음으로 결정).

| 문구 | 값 | 출처 |
| --- | --- | --- |
| 상단 로고 | 마감직전 | `wireframe.html:303` (D-24) |
| 로그인 링크 | 로그인 | `screens.md` C1 |
| 입점 신청 링크 | 사장님이신가요? 입점 신청 | `screens.md` C1 |
| 검색 입력 | 상품명 검색 | `wireframe.html:305` |
| 정렬 칩 | 마감 임박 / 가까운 순 / 할인율 / 낮은 가격 | `screens.md` C1 |
| 하단 탭 | 홈 / 내 예약 / 마이 | `screens.md` C1, `TabBar/README.md` |
| 품절 / 판매 종료 / 판매 예정 | 태그 | `screens.md` C1, `states.md` 할인 표 |
| 빈 목록(검색어 없음) | 근처에 마감 할인이 없어요 / 반경을 넓히거나 저녁 시간에 다시 확인해 보세요. / 반경 5km로 넓히기 | `EmptyState/preview.html`, README |
| 빈 목록(검색어 있음) | 검색 결과가 없어요 / 다른 상품명으로 검색해 보세요. / 검색어 지우기 | **임시** (D-32) |
| 로딩 | 카드 모양 Skeleton, `aria-label="불러오는 중"` | `Skeleton/README.md`, 문구는 `admin.md`의 `ListSkeleton`과 같은 **임시** |
| 오류 | 할인 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요. / 다시 시도 | **임시** (D-23, `auth.md` D-9의 「다시 시도」 재사용) |
| 더 보기 | 더 보기 / 처리 중… (불러오는 동안) | 「처리 중…」은 `states.md` 공통, 「더 보기」는 **임시** (D-11) |
| 더 보기 실패 | 더 불러오지 못했어요. 다시 시도해 주세요. | **임시** |
| 위치 칩 | 내 주변 · 3km / 위치 확인 중 / 위치 없음 | **임시** (D-21) |

**`HomePage` (`pages/home`)**: `useHomeOffers()`와 `useAuth()`를 한 번씩 부르고 아래를 조립한다. `.app`과 탭 바는 `CustomerLayout`이 그린다.
```
.bar   : span.logo 마감직전 · <LocationChip label=chipLabel/> · span.sp · 로그인 링크
.body  : <OfferSearchForm/> · <SortChips/> · <NearbyOfferSection home=.../>
.link  : 사장님이신가요? 입점 신청  → ROUTES.ownerSignup   (.body 밖, 탭 바 바로 위)
```
- 로그인 링크는 `useAuth().state.status === 'anonymous'`일 때만 보인다. `ROUTES.login`(`state` 없음: `screens.md` A1 "홈 상단 링크 → 문구 없음"). 로딩·오류·로그인됨에서는 숨긴다(D-22). 홈은 `useAuth`의 `error` 상태에서도 목록을 그린다(공개 화면).
- 입점 신청 링크는 항상 보인다(`screens.md`에 숨기는 조건이 없음, D-22). 목록이 길어도 `.body` 밖이라 항상 탭 바 위에 있다.
- `.body`는 스크롤, 그 아래 링크·탭 바는 고정(`layout.md` 화면 골격).

**`OfferCard({ item, now })`** (`OfferCard/README.md` 순서, 모든 카드 같은 형식): 사진 칸 `.ph`(썸네일 76px, 이미지 필드가 없어 항상 기본 그림, `aria-hidden`, D-19) + 정보 열.
1. `.m` `formatStoreLine(storeName, distanceKm)`
2. `.t` 상품명
3. `.price`: `.pct` `formatDiscountRate`, `<b>` `formatWon(salePrice)`, `<s>` `formatPlainPrice(originalPrice)`
4. `.m` `픽업 <b>{formatPickupWindow}</b>`
5. 상태별 마지막 줄 `offerCardState(offer, now)`:
   - `onSale` → `.row`: `.cd` `formatSalesEndLabel(minutesUntilSalesEnd)` + `.m` `formatRemaining(remainingStock)`
   - `soldOut` / `ended` / `scheduled` → `.row`: `span.tag.mute` 품절 / 판매 종료, `scheduled`는 `span.tag` 판매 예정. 이때 "판매 마감 N분 전"·남은 수량은 그리지 않는다.
- 카드는 이동하지 않는다(`div.card`, D-18). 문자열은 JSX 텍스트로만 출력한다(F17, `dangerouslySetInnerHTML` 금지).

**`SortChips`**: `.scroll` 안에 `button.chip` 4개. 선택은 `.on` + `aria-pressed="true"`. `distance` 칩은 `hasLocation`이 거짓이면 `disabled` + `aria-disabled="true"`, 눌러도 아무 일도 없다. 비활성 모양은 `components/bundle.css`에 `.chip` 비활성 규칙이 없어(C-5) `SortChips.module.css`의 `opacity: 0.4`(`.btn:disabled`와 같은 값, 토큰 변수 불필요)만 둔다. 임시이며 정본이 정해지면 바꾼다.

**`OfferSearchForm`**: `<form role="search">` + `.in` 입력(`placeholder` 상품명 검색, `aria-label` 상품명 검색, `maxLength=100`). 제출(Enter)할 때만 `onSubmit(raw)`를 부르고, 입력 중에는 조회하지 않는다(D-13). 별도 제출 버튼은 없다. 비어 있게 제출하면 검색어를 지운다. 부모 `keyword` prop이 바뀌면(「검색어 지우기」 포함) 입력칸이 그 값에 맞춰진다(지운 뒤 이전 검색어가 입력칸에 남지 않음).

**`LocationChip({ label })`**: `span.chip`(비대화형). C1a가 들어오면 `button`으로 바꾸고 시트를 연다(D-4).

**`NearbyOfferSection({ home })`**: `home.list.status`로 분기한다.
- `loading` → `OfferCardSkeleton` 3개(`aria-busy`).
- `error` → `.warn role="alert"` 문구 + `button.btn.sm` 「다시 시도」(`list.reload`).
- `empty` → `.box.empty`: `.ic`, `<b>title</b>`, `.m reason`, 버튼(있을 때만, `.btn.sm`, `runEmptyAction`).
- `success` → `OfferCard` 목록. `hasMore`이면 목록 아래 「더 보기」 버튼(`btn`, 불러오는 동안 `disabled`·「처리 중…」). `moreFailed`이면 버튼 위에 오류 한 줄.
- 위치가 없을 때(`unavailable`)도 목록은 정상 표시하고 거리만 숨긴다. 별도 안내 문구는 만들지 않는다(정본 없음, D-9).

**`CustomerTabBar`** (`widgets/customer-nav`): `div.tabs` 안에 탭 3개. 현재 탭은 `<b><Link aria-current="page"/></b>`, 나머지는 `<span><Link/></span>`(`OwnerNavItems`와 같은 마크업). 탭 이동 대상은 domain `tabTarget`이 정한다(§4.2).

## 4. 라우트·고객 셸·탭

### 4.1 라우트

| 경로 | 화면 | 하단 탭 |
| --- | --- | --- |
| `/` | C1 (`HomePage`) | 있음 |
| `/reservations`, `/my` | 아직 화면 없음. 정의하지 않는다. 기존 `*` → `/` 이동이 받음 (D-6) | — |

```tsx
// routes.tsx (HomePlaceholder 줄 삭제, import 정리)
{ element: <CustomerLayout />, children: [{ path: ROUTES.home, element: <HomePage />, handle: TAB_BAR_HANDLE }] },
```
- `placeholders.tsx`에서 `HomePlaceholder`와 그 export만 지운다. 나머지 상점주 자리 page·파일 맨 위 TODO는 그대로다(`언제:`에 C1이 없어 주석 수정 불필요, D-27).
- `{ path: '*', element: <Navigate to={ROUTES.home} replace /> }`는 그대로(`routes.tsx:61` TODO 유지).

### 4.2 `app/layouts/CustomerLayout.tsx`

- 가드 없음. 로그인 여부와 무관하게 항상 `Outlet`을 그린다(C1은 공개, 세션 확인이 느리거나 실패해도 막지 않음, D-5). 세션 복원은 `App.tsx`의 `AuthProvider`가 하고, 헤더의 로그인 링크만 상태를 읽는다.
- 구조: 바깥 `div.outer`(배경 `var(--bg)`, 전체 높이) → `div.frame`(`max-width: var(--customer-pc-w)`, 가운데, 좌우 `1px solid var(--line)`, 배경 `var(--paper)`, 전체 높이) → `div.app`(`layout.md`: 고객 PC는 모바일 화면 그대로 가운데 420px). `.app`은 `container: app`이라 폭 420px이면 720px 규칙(`.tabs` 숨김)이 켜지지 않는다. 모바일에서는 `max-width`가 의미 없다. 이 CSS는 `bundle.css`에 없어(`--customer-pc-w` 토큰만 있음, C-6) `CustomerLayout.module.css`에 토큰 변수만 쓴다(F12, `design-system-usage` §2). 실제 화면은 `vite-run`으로 확인.
- `useMatches().some(m => isTabBarHandle(m.handle))`이면 `<CustomerTabBar/>`를 `.app` 안 `Outlet` 뒤에 그린다(`OwnerLayout`과 같은 패턴).

### 4.3 탭 이동 (`widgets/customer-nav/domain/customerTabs.ts`)

- `CUSTOMER_TABS`: `{ key: 'home', label: '홈', path: ROUTES.home, requiresLogin: false }`, `{ key: 'reservations', label: '내 예약', path: ROUTES.reservations, requiresLogin: true }`, `{ key: 'my', label: '마이', path: ROUTES.my, requiresLogin: true }`
- `activeCustomerTab(pathname): CustomerTabKey | null`: 홈은 `/` 정확히만(끝 `/` 제거, 대소문자 무시, `OwnerNav`와 같은 방식), 예약·마이는 해당 경로와 그 하위. 그 외(예: 이후 C2 `/offers/…`)는 null = 탭 없는 하위 화면.
- `tabTarget(tab, authStatus): TabTarget` (`TabTarget = { to: string; state?: ReturnType<typeof loginRedirectState> }`. `LoginLocationState`는 `features/auth` 공개 API에 없어 `loginRedirectState`의 반환 타입으로 표기한다): `tab.requiresLogin`이고 `authStatus === 'anonymous'`면 `{ to: ROUTES.login, state: loginRedirectState('other', tab.path) }`(→ A1, 로그인 뒤 `resolvePostLoginPath`가 그 경로로 보냄. `screens.md` C1·`layout.md` "누른 탭으로 돌아옴"). 그 외(`loading`·`authenticated`·`error`·홈 탭)는 `{ to: tab.path }`. 로딩 중에는 이동만 하고, 이후 C5·C6 화면의 고객 가드가 막는다(D-6).
- 지금은 `/reservations`·`/my`가 화면이 없어, 로그인한 사용자가 누르면 `*` 규칙으로 `/`로 돌아온다. 비로그인 사용자는 A1 → 로그인 → `/reservations` → `/`다(`from`이 안전한 내부 경로이므로 고객은 `/reservations`로 가고 그 뒤 `*`가 홈으로 보냄).

## 5. 정합 이슈

| C | 내용 | 양쪽 근거 | 처리 |
| --- | --- | --- | --- |
| C-1 | 할인율 계산식이 명세에 "확인 필요"로 남아 있는데 백엔드는 정수 버림으로 확정 | `reference/catalog.md:45` ↔ `backend/src/catalog/domain/discount_offer.py:273~275` | 프론트는 `discount_rate`를 계산하지 않고 서버 값을 그대로 쓴다(D-14). 명세 갱신은 문서 소유자에게 제안 |
| C-2 | 화면은 한 목록에 「품절」 카드가 섞여 나오는데, API의 `status`는 값 하나(기본 `ON_SALE`)이고 `ON_SALE`은 `remaining_stock > 0`만이라 품절 항목은 기본 조회에 포함되지 않음 | `screens.md` C1 상태 태그·`wireframe.html:315~318`·`OfferCard/README.md` ↔ `reference/catalog.md` §8 `status`·`router.py:144`·`repositories.py:203~209` | 카드는 `soldOut`을 그릴 수 있게 만들되 목록에는 안 나옴(D-12). 질문 Q-3 |
| C-3 | OfferCard는 사진을 쓰는데 할인 응답(Offer)에 이미지 필드가 없음 | `OfferCard/README.md` "사진은 … 없으면 기본 그림" ↔ `reference/catalog.md` 공통 객체 Offer, `schemas.py:126~145` | 항상 기본 그림(D-19). 백엔드에 이미지 필드 추가는 확인 필요(Q-8) |
| C-4 | 위치 칩 「망원동 · 3km」의 동 이름을 얻을 API가 없음(좌표 → 동네 이름 변환 없음. open-issues C1a는 주소 → 좌표만 언급) | `screens.md` C1 칩·동작 메모 ↔ `open-issues.md` C1a, `api-map.md` C1·C1a 행 | 임시 라벨(D-21). Q-5 |
| C-5 | `Chip`에 비활성(「가까운 순」 비활성) 모양 정본이 없음. `bundle.css`에는 `.btn:disabled`만 있음 | `screens.md` C1 동작 메모 ↔ `components/Chip/README.md`, `bundle.css:215~246` | 디자인 시스템은 고치지 않고 `SortChips.module.css`로 임시 처리(M-7). Q-9 |
| C-6 | 고객 PC 420px 프레임 규칙이 문서에만 있고 `bundle.css` 클래스가 없음(토큰 `--customer-pc-w`만 있음) | `layout.md:7` ↔ `tokens.css:30`, `bundle.css`에 `420` 없음 | `CustomerLayout.module.css`로 구현(D-5). 디자인 시스템 쪽 클래스 추가를 제안만 |
| C-7 | C1 "연결 화면"에 C2가 없는데 연결 지도는 C1 → C2. 카드를 눌러 갈 화면 | `screens.md` C1 연결 화면(A1·A2·C1a) ↔ `layout.md` 연결 지도 `C1 --> C2` | 카드는 C2 전까지 이동하지 않음(D-18) |
| C-8 | "페이지 목록"이라는 설명만 있고 다음 쪽을 보는 화면 방식·문구가 없음. API는 `page`·`size`·`total`을 줌 | `screens.md` C1 동작 메모 ↔ `reference/catalog.md` §8 | 「더 보기」 버튼(임시, D-11). Q-4 |
| C-9 | 요청서의 "서버 정렬 파라미터가 있는지, 클라이언트 정렬인지": 서버 `sort`(`distance`·`price`·`sales_end`·`discount_rate`) 지원, 위치 없는 `distance`는 400. 정렬 방향·동률 규칙은 확정됨. 화면 명세와는 충돌 없음 | `reference/catalog.md` §8 확정(2026-11-06) ↔ `search.py:37~45`, `repositories.py:355~366` | 서버 정렬만 쓴다. 클라이언트 정렬은 만들지 않음(D-10) |
| C-10 | 요청서의 "위치 권한이 없을 때 API 동작": `lat`·`lng` 없이 호출하면 200, 반경 필터 없이 전체 조회, `distance: null`. 명세와 백엔드가 같음. 한쪽만 보내면 400 | `catalog.md` §8 확정·에러 표 ↔ `service.py:186~193`, `schemas.py:310` | 위치가 없으면 `lat`·`lng`·`radius_km`을 모두 뺀다(D-9). 차이 없음 |
| C-11 | 요청 범위를 넘어선 추가: 검색어 입력(`screens.md` C1 컴포넌트에 Input이 있어 포함), `shared/lib/useNow.ts`·`routes.ts` 상수 추가, `반경 5km로 넓히기`(EmptyState 문구 정본)의 동작 | 사용자 요청 §1 ↔ 이 설계안 D-13·D-25·D-33 | 결정 항목으로 올림 |
| C-12 | 홈 로고·플레이스홀더 문구 차이: `HomePlaceholder`는 「마감 직전」, 와이어프레임 로고는 「마감직전」 | `placeholders.tsx:54` ↔ `wireframe.html:303` | 와이어프레임을 따름(D-24) |

## 6. 골격 (`tdd-workflow` §3)

설계안 §2의 공개 API·시그니처를 그대로 파일로 만들고 본문은 비운다. 타입·포트(`interface`)·토큰·상수(`DEFAULT_RADIUS_KM`, `SORT_CHIPS`, `CUSTOMER_TABS`, `CARD_STATE_TAG`)·`index.ts`·`wiring.ts`는 실제로 만들고, 함수 본문은 `throw new Error('not implemented: <이름>')`, 컴포넌트는 `null`, 훅은 `not implemented`로 둔다. `routes.tsx`의 `/` 교체와 `container.ts` 줄은 골격 단계에서 하되 `HomePage` 골격이 `null`이라 기존 라우트 테스트는 `HomePlaceholder` 기대를 쓰지 않는지 확인한다(`tests/app/router/routes.test.tsx`의 홈 기대값을 Red 단계에서 같이 고침: Q-10).

## 7. 테스트 목록 (`tdd-workflow` §2, 위치 `tests/` 아래)

시간 고정값: `now = new Date(2026, 10, 10, 17, 18, 0)`(로컬 시간 생성자, 시간대 의존 없음). 가짜 구현체는 `tests/features/offers/fakes/`(`fakeOfferRepository.fake.ts`: 호출 인자 기록·결과/오류/지연 설정, `fakeLocationProvider.fake.ts`: 결과 설정·`resolve()` 수동), 고정 데이터는 `tests/features/offers/fakes/offers.ts`(`offerOnSale`: salesEnd = now+42분·남은 3개·할인율 50·`sale 6000/original 12000`, `offerSoldOut`, `offerEnded`). 오류는 `new ApiError(status, errorCode, message)`. 렌더 보조: `tests/support/renderWithAuth.tsx` + offers 가짜 두 개를 더한 컨테이너.

### (a) domain

`tests/features/offers/domain/offerFormat.test.ts`
- `formatWon`: 0 → `0원` / 999 → `999원` / 1000 → `1,000원` / 11500 → `11,500원` / 1234567 → `1,234,567원` (5)
- `formatPlainPrice`: 12000 → `12,000` / 0 → `0` / 999 → `999` (3)
- `formatDiscountRate`: 50 → `50%` / 0 → `0%` (2)
- `formatDistance`: null → null / 0.4 → `0.4km` / 0.35 → `0.4km` / 0.04 → `0.0km` / 0 → `0.0km` / 1 → `1.0km` / 12.34 → `12.3km` (7)
- `formatStoreLine`: (`망원베이커리`, 0.4) → `망원베이커리 · 0.4km` / (`망원베이커리`, null) → `망원베이커리` (2)
- `formatRemaining`: 3 → `남은 3개` / 0 → `남은 0개` (2)

`tests/features/offers/domain/offerCard.test.ts`
- `minutesUntilSalesEnd`: +42분 → 42 / +41분 30초 → 42 / +1초 → 1 / 정각(0) → 0 / 과거 → 0 / +60분 → 60 (6)
- `formatSalesEndLabel`: 1 → `판매 마감 1분 전` / 42 → `판매 마감 42분 전` / 59 → `판매 마감 59분 전` / 60 → `판매 마감 1시간 전` / 70 → `판매 마감 1시간 10분 전` / 125 → `판매 마감 2시간 5분 전` / 1500 → `판매 마감 25시간 전` (7)
- `offerCardState`: `ON_SALE`·남은 3·마감 미래 → `onSale` / `SOLD_OUT` → `soldOut` / `ON_SALE`이지만 `remainingStock` 0 → `soldOut` / `salesEnd`가 정확히 now → `ended` / `salesEnd`가 now+1초 → `onSale` / `CLOSED` → `ended` / `SUSPENDED` → `ended` / `SCHEDULED`·마감 미래 → `scheduled` / 품절이지만 마감 지남 → `ended` (우선순위) (9)
- `formatPickupWindow`: 오늘 18:00–20:00 → `오늘 18:00–20:00` / 내일 → `11/11 18:00–20:00` / 09:05–10:00 → `오늘 09:05–10:00` / 23:00–다음 날 01:00 → `오늘 23:00–01:00` / 1월 7일 → `01/07 …` / 시작이 어제 → `11/09 …` (6)

`tests/features/offers/domain/search.test.ts`
- `resolveSort`: (`distance`, false) → `sales_end` / (`distance`, true) → `distance` / (`price`, false) → `price` / (`sales_end`, false) → `sales_end` (4)
- `isSortSelectable`: `distance`·위치 없음 → false / `distance`·위치 있음 → true / `discount_rate`·위치 없음 → true (3)
- `normalizeKeyword`: `'  빵 '` → `'빵'` / `'   '` → undefined / `''` → undefined / 100자 → 그대로 / 101자 → 100자 / `'식빵 모둠'`(안쪽 공백 유지) (6)
- `queryKey`: 같은 조건 → 같은 키 / `radiusKm`만 다름 → 다름 / `sort`만 다름 → 다름 / `area: null` vs 위치 있음 → 다름 (4)
- `hasNextPage`: (1, 20, 21) → true / (1, 20, 20) → false / (1, 20, 0) → false / (2, 20, 40) → false (4)
- `appendPage`: 겹치지 않음 → 뒤에 붙음 / 같은 `offer.id` → 앞쪽 유지·중복 제거 / 빈 `next` → 그대로 (3)
- `locationChipLabel`: (`located`, 3) → `내 주변 · 3km` / (`located`, 0.5) → `내 주변 · 0.5km` / (`locating`, 3) → `위치 확인 중` / (`unavailable`, 3) → `위치 없음` (4)
- `SORT_CHIPS`: 순서·라벨·키 (마감 임박→`sales_end`, 가까운 순→`distance`, 할인율→`discount_rate`, 낮은 가격→`price`) (1)

`tests/features/offers/domain/offerEmpty.test.ts`
- 위치 있음·반경 3·검색어 없음 → `widenRadius`, 버튼 `반경 5km로 넓히기`, 제목 `근처에 마감 할인이 없어요` / 반경 5 → action null / 위치 없음 → null / 검색어 있음 → `clearKeyword`·`검색어 지우기` / 검색어 + 위치 있음 → `clearKeyword`(검색어 우선) (5)

`tests/widgets/customer-nav/domain/customerTabs.test.ts`
- `CUSTOMER_TABS`: 순서·라벨·경로(홈 `/`, 내 예약 `/reservations`, 마이 `/my`) (1)
- `activeCustomerTab`: `/` → home / `/reservations` → reservations / `/reservations/` → reservations / `/my` → my / `/offers/abc` → null / `/MY` → my (6)
- `tabTarget`: 홈·anonymous → `{to:'/'}` / 내 예약·anonymous → `{to:'/login', state:{from:'/reservations'}}` / 마이·anonymous → `{from:'/my'}` / 내 예약·authenticated → `{to:'/reservations'}` / 내 예약·loading → `{to:'/reservations'}` / 마이·error → `{to:'/my'}` (6)

### (b) application (가짜 포트)

`tests/features/offers/application/nearbyListState.test.ts` (reducer, React 없음)
- 초기 → `queryChanged` → `loading` / `firstLoaded` → `ready`·items·`hasMore` 계산 / `firstLoaded`의 `key`가 다름 → 무시 / `firstFailed` → `error` / `moreRequested` 정상 → `loadingMore` / `moreRequested`가 `hasMore` false → 변화 없음 / `moreRequested`가 `loadingMore` 중 → 변화 없음 / `moreLoaded` → 중복 제거하며 이어붙음 / `moreFailed` → 목록 유지·`moreFailed` true (9)

`tests/features/offers/application/useCurrentLocation.test.tsx`
- 처음 `locating` / 성공 → `located`+`point` / `unavailable` 결과 → `unavailable` / 포트가 예외 → `unavailable` / `retry()` → `locating`을 거쳐 다시 요청, 호출 횟수 2 / 언마운트 뒤 늦은 결과로 상태가 바뀌지 않음 (6)

`tests/features/offers/application/useNearbyOffers.test.tsx`
- `query` null → `loading`, 포트 호출 0 / 성공 → `loading` → `success`(items·total) / 결과 0건 → `empty` / 실패(`ApiError(500)`) → `error` / `reload()` → 다시 `loading` → `success` / 조건이 바뀜 → 이전 `signal.aborted === true`, 새 조건으로 1쪽 요청 / 첫 요청 인자 `page: 1, size: 20` / `loadMore()` → `page: 2` 요청, `loadingMore` true → 이어붙음 / 마지막 쪽에서 `hasMore` false, `loadMore()`는 호출 안 함 / `loadMore()` 실패 → 목록 유지·`moreFailed` true → 다시 `loadMore()`로 성공 / 불러오는 중 `loadMore()` 두 번 → 요청 1회 / 언마운트 → `signal.aborted`, 이후 상태 변경 없음 (12)

`tests/features/offers/application/useHomeOffers.test.tsx`
- 위치 `locating` 동안 목록 `loading`, 저장소 호출 0 / 위치 `located` → `findNearby`가 `area: {point, radiusKm: 3}`, `sort: 'sales_end'`로 호출 / 위치 `unavailable` → `area: null`, `hasLocation` false / `selectSort('distance')` 위치 있음 → `sort: 'distance'`로 재조회 / `selectSort('distance')` 위치 없음 → 상태·호출 변화 없음 / 위치가 있다가 `retry()`가 `unavailable`이 됨 + 선택 `distance` → 반환 `sort`가 `sales_end` / `submitKeyword('  빵 ')` → `keyword: '빵'`으로 재조회 / `submitKeyword('   ')` → 검색어 지움 / `runEmptyAction()`(`widenRadius`) → `radiusKm` 5로 재조회, `chipLabel`이 `내 주변 · 5km` / `runEmptyAction()`(`clearKeyword`) → 검색어 지움 / `chipLabel` 세 상태 (11)

`tests/shared/lib/useNow.test.tsx` (fake timers)
- 처음 값이 현재 시각 / `intervalMs` 경과마다 갱신 / 언마운트 후 타이머 정리 (3)

### (c) infrastructure (`vi.mock('@/shared/api/client')`만 허용)

`tests/features/offers/infrastructure/httpOfferRepository.test.ts`
- 위치 있음·검색어 있음 → `/v1/offers?lat=37.5&lng=126.9&radius_km=3&keyword=빵&sort=sales_end&page=1&size=20`(순서 고정, 한글은 인코딩) / 위치 없음 → `lat`·`lng`·`radius_km` 없음 / 검색어 `undefined` → `keyword` 없음 / `status`·`category` 없음 / `signal` 전달 (5)
- 응답 변환: 필드 대조표대로 `Offer`(snake → camel), 날짜 문자열 → `Date`(`getTime()` 일치), `distance` null → `distanceKm` null, `discount_rate`를 계산 없이 그대로 (3)
- 알 수 없는 `status` → `Error` / `ApiError` 전파 (2)

`tests/features/offers/infrastructure/browserLocationProvider.test.ts` (`navigator.geolocation` 가짜)
- 성공 → `located`+좌표 / 오류 콜백(권한 거부) → `unavailable` / `geolocation` 없음 → `unavailable` / 옵션 `timeout 10000`·`maximumAge 300000` 전달 / 이미 abort된 `signal` → 결과 무시(거절하지 않음) (5)

### (d) presentation·pages·app

`tests/features/offers/presentation/OfferCard.test.tsx`
- 판매 중: 상점·거리 줄, 상품명, `50%`·`6,000원`·`12,000`(취소선 `<s>`), `픽업 오늘 18:00–20:00`, `판매 마감 42분 전`, `남은 3개` / 거리 null → `·`와 `km` 없음 / 품절 → 태그 `품절`, `판매 마감`·`남은` 없음 / 판매 종료 → 태그 `판매 종료` / 판매 예정 → 태그 `판매 예정` / `now`가 바뀌면 라벨이 바뀜(`41분`) / 링크·버튼이 아님(역할 `link` 0) (7)

`tests/features/offers/presentation/SortChips.test.tsx`
- 칩 4개 순서·라벨 / `sort` 칩에 `aria-pressed="true"` / 위치 있음 → `가까운 순` 활성, 클릭 시 `onSelect('distance')` / 위치 없음 → `가까운 순` `disabled`, 클릭해도 `onSelect` 호출 0 / 다른 칩 클릭 → `onSelect` 키 (5)

`tests/features/offers/presentation/OfferSearchForm.test.tsx`
- `role="search"`·입력 `placeholder` `상품명 검색` / 글자 입력만으로는 `onSubmit` 0 / Enter → `onSubmit('빵')` / 빈 입력 Enter → `onSubmit('')` / `maxLength` 100 (5)

`tests/pages/home/HomePage.test.tsx` (가짜 저장소·위치, `renderRoutesWithAuth`)
- 위치 확인 중: Skeleton(`aria-busy`)·`위치 확인 중` 칩, 목록 없음 / 위치 허용 + 성공: 카드 N개, 칩 `내 주변 · 3km`, 거리 표시, `마감 임박` 선택 / 위치 거부 + 성공: 카드 N개, 거리 숨김, `가까운 순` 비활성, 칩 `위치 없음` / 오류: `할인 목록을 불러오지 못했어요…` `role="alert"` + `다시 시도` → 재조회 성공하면 목록 / 빈(검색어 없음·위치 있음): `근처에 마감 할인이 없어요`·`반경 5km로 넓히기` → 클릭 → 재조회, 칩 `5km` / 빈(검색어 있음): `검색 결과가 없어요`·`검색어 지우기` / 빈(위치 없음): 버튼 없음 / 더 보기: `hasMore`면 `더 보기` 버튼 → 클릭 → 2쪽 카드가 이어 붙음, 불러오는 동안 `처리 중…`·`disabled` / 더 보기 실패: 오류 한 줄 + 목록 유지 / 정렬 칩 `할인율` 클릭 → `sort=discount_rate`로 재조회, `aria-pressed` 이동 / 검색어 Enter → `keyword`로 재조회 / 위치 칩이 `button`이 아님(역할 `button` 중 칩 이름 없음) **(C1a로 대체: §12.7 HomePage 변경 단언)** / 로그인 링크: anonymous면 `로그인`(→ `/login`, `state` 없음), authenticated·loading·error면 없음 / 입점 신청 링크: `사장님이신가요? 입점 신청` → `/signup?role=owner`, 로그인 상태와 무관하게 있음 (14)

`tests/widgets/customer-nav/presentation/CustomerTabBar.test.tsx`
- 탭 3개 라벨·순서 / `/`에서 홈이 `aria-current="page"`·굵게(`<b>`) / anonymous가 `내 예약` 클릭 → `/login`, `location.state.from === '/reservations'` / anonymous가 `마이` 클릭 → `from === '/my'` / authenticated가 `내 예약` 클릭 → `/reservations`로 이동 시도(라우트가 없으면 `/`로 돌아옴) / auth `loading`에서 클릭 → 경로 이동 / `/offers/x` 같은 하위 경로에서 현재 탭 없음 (7)

`tests/app/layouts/CustomerLayout.test.tsx`
- anonymous로 `/` → 홈이 보임(가드 없음, `/login`으로 안 감) / auth `error`여도 홈이 보임 / 탭 핸들이 있는 라우트 → 탭 바 있음 / 핸들 없는 라우트 → 탭 바 없음 / `.app` 프레임 존재 (5)

`tests/app/router/routes.test.tsx` (추가)
- `/` → `HomePage`(로고 `마감직전`) / `/reservations`·`/my` → `/`로 이동 / 기존 홈 플레이스홀더 기대가 있으면 `HomePage` 기대로 바꿈 (3)

`tests/app/container.test.ts` (추가)
- `OfferRepositoryToken`·`LocationProviderToken`이 풀림, 중복 등록 오류 없음 (1)

### (e) E2E — `e2e/home.spec.ts` (백엔드 응답은 `page.route('**/v1/offers**')`, 위치는 Playwright `geolocation` 권한)

- 위치 허용 → 요청에 `lat`·`lng`·`radius_km=3`, 카드와 거리 표시 / 위치 거부 → 요청에 `lat` 없음, 거리 없음, `가까운 순` 비활성 / `할인율` 칩 → `sort=discount_rate` 요청 / 검색어 Enter → `keyword` 요청 / 응답 500 → 오류 문구 → 다시 시도 / 비로그인 `내 예약` 탭 → `/login` → (백엔드 로그인 응답 가짜) 로그인 → 홈으로 돌아옴 / 420px 프레임: 뷰포트 1280px에서 앱 폭이 420px (7)

### 테스트 수 합계

| 구분 | 내용 | 개수 |
| --- | --- | --- |
| domain | offerFormat 21 + offerCard 28 + search 29 + offerEmpty 5 + customerTabs 13 | 96 |
| application | reducer 9 + useCurrentLocation 6 + useNearbyOffers 12 + useHomeOffers 11 + useNow 3 | 41 |
| infrastructure | httpOfferRepository 10 + browserLocationProvider 5 | 15 |
| presentation·pages·app | OfferCard 7 + SortChips 5 + OfferSearchForm 5 + HomePage 14 + CustomerTabBar 7 + CustomerLayout 5 + routes 3 + container 1 | 47 |
| E2E | `e2e/home.spec.ts` | 7 |
| 합계 | | 206 |

- 개수는 목록의 `/`로 이어 적은 케이스를 하나씩 센 값이다. 구현 중 케이스를 쪼개거나 더해도 되지만 줄이지는 않는다(`tdd-workflow` §5).

정본이 없어 목록에서 뺀 것: 「더 보기」·오류·빈(검색어 있음)·위치 칩 문구의 최종 값(임시값 기대는 넣었고, 정본이 정해지면 문구 상수와 기대값을 함께 고침), 시간 정각·24시간 이상 표기의 확정값(임시값으로만 검증).

## 8. 남길 작업 주석 (`code-annotations`, F19)

| M | 위치 | 태그 | 내용 |
| --- | --- | --- | --- |
| M-1 | `features/offers/presentation/NearbyOfferSection.tsx`, `domain/offerEmpty.ts`, `domain/search.ts`(`locationChipLabel`) | TODO | `// TODO: 임시 문구다(빈 목록(검색어 있음), 오류, 「더 보기」, 더 보기 실패, 위치 칩 라벨).`<br>`//   왜: screens.md·content.md에 C1 목록 상태 문구가 없다 (docs/design/frontend/offers.md D-20, D-21, D-23, D-32)`<br>`//   언제: 결정 후 (디자인 시스템: content.md C1 문구 확정)` |
| M-2 **(C1a로 대체: 이번에 제거, §12.9)** | `features/offers/presentation/LocationChip.tsx` | TODO | `// TODO: 위치 칩이 누를 수 없는 표시다. 눌러서 C1a 시트(위치·반경)를 연다.`<br>`//   왜: C1a가 아직 없어 죽은 버튼을 만들지 않는다 (docs/design/frontend/offers.md D-4)`<br>`//   언제: C1a 구현 시` |
| M-3 | `features/offers/infrastructure/browserLocationProvider.ts` | open-issues | `// open-issues: C1a 위치는 현재 위치만 사용한다(주소 → 좌표 변환 확인 필요).` |
| M-4 | `features/offers/presentation/OfferCard.tsx` | TODO | `// TODO: 카드가 이동하지 않는다. 눌러서 C2(할인 상세)로 보낸다.`<br>`//   왜: C2 경로·화면이 아직 없다 (docs/design/frontend/offers.md D-18, C-7)`<br>`//   언제: C2 구현 시` |
| M-5 | `features/offers/presentation/OfferCard.tsx` | TODO | `// TODO: 썸네일이 항상 기본 그림이다.`<br>`//   왜: 할인 응답에 이미지 필드가 없다 (docs/design/frontend/offers.md C-3, D-19)`<br>`//   언제: 결정 후 (백엔드: 할인 응답에 이미지 필드 추가)` |
| M-6 | `features/offers/application/useHomeOffers.ts`(조회 조건 만드는 곳) | TODO | `// TODO: 목록에 품절 카드가 나오지 않는다(status 기본 ON_SALE만 조회).`<br>`//   왜: 서버 status가 값 하나라 판매 중과 품절을 한 번에 못 받는다 (docs/design/frontend/offers.md C-2, D-12)`<br>`//   언제: 결정 후 (사용자: 품절 카드 표시 방법)` |
| M-7 | `features/offers/presentation/SortChips.tsx`(CSS Module import 줄 위) | TODO | `// TODO: 비활성 칩 모양이 임시다(opacity 0.4).`<br>`//   왜: Chip 비활성 상태 정본이 없다 (docs/design/frontend/offers.md C-5)`<br>`//   언제: 결정 후 (디자인 시스템: Chip 비활성 상태)` |
| M-8 | `widgets/customer-nav/domain/customerTabs.ts` | FIXME | `// FIXME: 내 예약·마이 탭의 경로(/reservations, /my)에 화면이 없다. 로그인한 사용자가 누르면 홈으로 돌아온다.`<br>`//   왜: C5·C6이 아직 없다 (docs/design/frontend/offers.md D-6)`<br>`//   언제: C5 구현 시, C6 구현 시, 늦어도 배포 전` |
| M-9 | `domain/offerCard.ts`(`formatSalesEndLabel`, `formatPickupWindow`) | TODO | `// TODO: 1시간 정각·24시간 이상의 남은 시간과 다른 날 픽업 표기가 임시다.`<br>`//   왜: content.md에 해당 경우의 표기가 없다 (docs/design/frontend/offers.md D-15, D-16)`<br>`//   언제: 결정 후 (디자인 시스템: content.md 시간 표기 확정)` |
| M-10 | `app/layouts/CustomerLayout.tsx`(CSS Module을 import하는 줄 위) | TODO | `// TODO: 420px 프레임이 이 파일의 CSS Module에만 있다.`<br>`//   왜: bundle.css에 고객 PC 프레임 클래스가 없다 (docs/design/frontend/offers.md C-6, D-5)`<br>`//   언제: 결정 후 (디자인 시스템: 고객 셸 프레임 클래스 추가)` |
| M-11 | `app/layouts/AccountLayout.tsx:11` (기존 TODO 수정) | TODO | `언제:`를 `고객 셸 구현 시` → `C6 구현 시`로, `왜:` 끝에 `고객 셸은 offers.md D-5로 생겼으나 C8·C9로 가는 고객 진입점(C6)이 아직 없다 (docs/design/frontend/offers.md D-7)`를 덧붙인다 |

- `FIXME`는 M-8 하나뿐이다. 나머지는 `TODO`·`open-issues`다. M-8은 지금 동작이 맞지만(비로그인 흐름은 정상, 로그인 상태에서 화면이 없을 뿐) 그대로 두면 탭이 죽은 것처럼 보여 C5·C6 시점에 반드시 고쳐야 해 `FIXME`다.
- `useAuthController.ts:12` FIXME(다른 영역 401 처리): `GET /v1/offers`는 인증이 필요 없어 401이 나지 않으므로 이번에 건드리지 않는다(D-26). `client.ts:23·34` TODO(NETWORK_ERROR 문구·비JSON 2xx)는 그대로 둔다. 목록 오류 화면은 서버·클라이언트 `message`를 쓰지 않고 고정 문구를 보이므로(D-23) 두 TODO와 겹치지 않는다. 비JSON 2xx로 `SyntaxError`가 오면 `error` 상태가 되어 같은 오류 화면이 나온다. `routes.tsx:61` NotFound TODO는 그대로(D-6의 `/reservations`·`/my`가 이 규칙을 지나감).

## 9. 결정 표

사용자가 모두 확정했다(2026-11-10). 상태 열에 "(… 임시)"가 붙은 행은 값(방식)은 확정이지만 문구·표기 정본이 없어 **정본이 생길 때까지 임시 문구로 진행**하는 것이며, 해당 TODO(M-1·M-9)는 남긴다. 구현을 막는 항목은 없다.

| D | 항목 | 값 | 상태 | 근거 | 구현을 막는가 |
| --- | --- | --- | --- | --- | --- |
| D-1 | 문서 배치 | `offers.md` 하나에 offers 영역·`customer-nav`·`pages/home`·고객 셸을 함께 적음 | 확정(사용자, 2026-11-10) | 첫 화면이라 영역·셸·page가 한 흐름. 이후 C2·O2 등은 이 파일에 추가분만 적거나 새 파일 | 아니오 |
| D-2 | 이번 범위 | C1 + 고객 셸(`CustomerLayout`, `customer-nav`) + `/` 교체. C1a는 자리만(`useCurrentLocation.retry`, `radiusKm`·`setRadiusKm`, 위치 칩) | 확정(사용자, 2026-11-10) | 요청서 §1, `layout.md` 고객 셸, `fsd-structure` §6 | 아니오 |
| D-3 | `entities/offer` | 만들지 않음. `Offer`·`OfferRepository`·`OfferCard`는 `features/offers`. C2(예약이 할인을 읽음)에서 `reservations`가 필요로 할 때 내림 | 확정(사용자, 2026-11-10) | `fsd-structure` §4 "미리 entities를 만들지 않습니다", `auth-account.md` D-26과 같은 방식 | 아니오 |
| D-4 | C1a가 없을 때 위치 칩 | 누를 수 없는 `span.chip` 표시. C1a 구현 시 `button`으로 바꿔 시트를 연다(M-2). **→ C1a로 대체: D-35·D-41(§12).** 선택지: ① 표시만(추천) ② 눌러서 현재 위치 재요청(`retry`) ③ 칩을 숨김 | 확정(사용자, 2026-11-10) | 와이어프레임에는 칩이 있음. 이동할 곳이 없는 버튼은 죽은 버튼이 됨(`auth.md` C-7 방침). ②는 거부 후에는 브라우저가 다시 묻지 않아 효과가 없음 | 아니오 |
| D-5 | 고객 셸 | `app/layouts/CustomerLayout`(가드 없음) + `CustomerLayout.module.css`(PC 420px 가운데, 토큰 변수만) + 탭 바(핸들 라우트만). 고객 가드(`decideAccess(…,'CUSTOMER')`)는 C5·C6 설계 때 그 화면의 레이아웃에 | 확정(사용자, 2026-11-10) | `layout.md:7`, `screens.md` C1 "로그인 없이 열림", `auth.md` §4 "고객 셸은 이후 `decideAccess(…, 'CUSTOMER')`", C-6 | 아니오 |
| D-6 | 탭 동작과 경로 | 탭 3개(홈·내 예약·마이). 경로 `ROUTES.reservations = '/reservations'`, `ROUTES.my = '/my'`(임시 이름, 화면은 없음). 비로그인이 내 예약·마이를 누르면 `/login` + `state.from = 탭 경로`. 로그인 후에는 `from`으로 이동하나 화면이 없어 `*` 규칙으로 홈에 도착. 로그인한 사용자가 눌러도 화면이 없어 홈으로 돌아옴(M-8). 선택지: ① 위 방식(추천) ② 홈 탭만 두고 나머지는 C5·C6에서 추가 ③ 두 탭을 비활성 | 확정(사용자, 2026-11-10) | `screens.md` C1·`layout.md:71`·`TabBar/README.md`(비로그인 탭 → A1 → 돌아옴), `redirect.ts:63`(고객은 안전한 `from`으로 이동), `auth-account.md` D-3(경로는 뜻으로) | 아니오 |
| D-7 | `AccountLayout.tsx:11` TODO(고객 셸 구현 시) | 이번에 고치지 않음. `언제:`를 `C6 구현 시`로 갱신(M-11). C8·C9는 역할 무관 하위 화면이라 고객이 오는 길은 C6뿐 | 확정(사용자, 2026-11-10) | `auth-account.md` §4·§11, 고객이 C8·C9에 도달하는 경로가 C6 이후 | 아니오 |
| D-8 | 위치 요청 옵션 | `enableHighAccuracy: false`, `timeout: 10_000`ms, `maximumAge: 300_000`ms. 확인되기 전까지 목록은 로딩. 시간 초과는 `unavailable` | 확정(사용자, 2026-11-10) | 정본 없음. 거절·시간 초과 때 영원히 로딩하지 않게 상한이 필요 | 아니오 |
| D-9 | 위치를 못 얻었을 때 | `lat`·`lng`·`radius_km`을 모두 빼고 호출(전체 조회, `distance: null`), 거리 숨김, 「가까운 순」 비활성, 선택돼 있던 `distance`는 `sales_end`로. 별도 안내 문구 없음 | 확정(사용자, 2026-11-10) | `screens.md` C1 동작 메모, `catalog.md` §8 확정, `service.py:186~193`, C-10 | 아니오 |
| D-10 | 정렬 | 서버 `sort`만 사용(`sales_end`/`distance`/`discount_rate`/`price`). 기본 「마감 임박」. 칩 ↔ 서버 값은 `SORT_CHIPS` | 확정(사용자, 2026-11-10) | C-9, `catalog.md` §8 확정(정렬 방향·동률) | 아니오 |
| D-11 | 다음 쪽 보기 | `size=20`, 목록 아래 「더 보기」 버튼(임시 문구), 중복 제거해 이어붙임. 선택지: ① 버튼(추천, 문구 필요) ② 무한 스크롤(문구는 필요 없으나 테스트·접근성 부담) ③ 첫 쪽만 | 확정(진행 방식·문구는 임시) | `screens.md` "페이지 목록이라 끝까지 안 내려감", C-8 | 아니오 |
| D-12 | 조회 `status`와 품절 카드 | `status`를 보내지 않음(서버 기본 `ON_SALE`). 카드 부품은 품절·판매 종료·판매 예정을 그릴 수 있게 하되 목록에는 나오지 않음(M-6). 선택지: ① 위 방식(추천) ② 판매 중 목록이 끝난 뒤 `status=SOLD_OUT`을 이어서 조회해 뒤에 붙임 ③ 백엔드에 다중 status 요청(`§9` 상점 할인 목록은 반복 가능) | 확정(사용자, 2026-11-10) | C-2 | 아니오 |
| D-13 | 검색 | `Input`(상품명 검색), 제출(Enter) 시에만 조회, 앞뒤 공백 제거·100자 제한, 입력 중 자동 조회 없음 | 확정(사용자, 2026-11-10) | `screens.md` C1 컴포넌트 목록에 Input, `wireframe.html:305`, `catalog.md` §8 `keyword`, 요청 수를 줄임 | 아니오 |
| D-14 | 할인율 | 서버 `discount_rate`를 그대로 표시(클라이언트 계산 없음) | 확정(사용자, 2026-11-10) | C-1, F7(규칙이 두 곳이 되지 않게) | 아니오 |
| D-15 | 남은 시간 | 분은 올림, 갱신 주기 30초(`useNow(30_000)`), 60분 이상은 `N시간 M분 전`(정각이면 `N시간 전`, 24시간 이상도 시간으로), 마감이 지난 카드는 `판매 종료` 태그 | 확정(정각·24시간 이상 표기는 임시, M-9) | `content.md` 숫자·시간 표, `states.md` 계산값, `discount_offer.py:203`(마감 후 CLOSED), 정각·24시간 이상 정본 없음(M-9) | 아니오 |
| D-16 | 픽업 시간 표기 | 오늘이면 `오늘 HH:mm–HH:mm`, 다른 날은 `MM/DD HH:mm–HH:mm`, 끝 시각은 시:분만 | 확정(다른 날 표기는 임시, M-9) | `content.md` 시간대·날짜(목록) 행, 다른 날 표기 정본 없음(M-9) | 아니오 |
| D-17 | 거리 표기 | `Math.round(km*10)/10`을 소수 1자리 + `km`. 서버 `unit`은 쓰지 않음(`km` 고정) | 확정(사용자, 2026-11-10) | `content.md` 거리 행, `search.py:8` | 아니오 |
| D-18 | 카드 클릭 | 이동하지 않음(`div.card`). C2 구현 시 `Link`로 바꿈(M-4) | 확정(사용자, 2026-11-10) | C-7, `auth.md` C-7 방침(죽은 링크 금지) | 아니오 |
| D-19 | 썸네일 | 항상 기본 그림(`.ph`) | 확정(사용자, 2026-11-10) | C-3 | 아니오 |
| D-20 | 문구 묶음 | §3.5 표의 "임시" 문구 전부를 한 번에 결정받는다(빈 목록(검색어 있음), 로딩 라벨, 오류, 더 보기, 더 보기 실패) | 확정(문구는 임시, M-1) | 정본 없음. 정본이 정해지면 문구 상수와 기대값을 함께 고침 | 아니오 |
| D-21 | 위치 칩 라벨 | `내 주변 · 3km` / `위치 확인 중` / `위치 없음` | 확정(라벨은 임시, M-1) | C-4(동 이름을 알 방법이 없음) | 아니오 |
| D-22 | 상단 로그인·입점 신청 링크 | 로그인: `anonymous`일 때만. 입점 신청: 항상(로그인 상태와 무관) | 확정(사용자, 2026-11-10) | `screens.md` C1("상단 로그인은 선택 사항", 입점 신청 링크는 조건 없음). 로그인한 고객에게 입점 신청을 숨길지는 정본 없음 | 아니오 |
| D-23 | 목록 오류 표시 | 오류 종류와 상관없이 고정 문구 + 「다시 시도」(재조회). 서버 `message`·`NETWORK_ERROR` 문구를 쓰지 않음 | 확정(문구는 임시, M-1) | `ApiError(UNKNOWN)`의 `message`가 영문 `statusText`일 수 있음(`error.ts`), `auth.md` D-9(「다시 시도」), `states.md` 오류는 화면 전체면 Notice | 아니오 |
| D-24 | 로고 문구 | 「마감직전」 | 확정(사용자, 2026-11-10) | `wireframe.html:303` (C-12) | 아니오 |
| D-25 | `shared/lib/useNow.ts` | 새로 만듦(업무를 모르는 시각 갱신 훅) | 확정(사용자, 2026-11-10) | domain이 `now`를 인자로 받는 규칙(`layer-architecture` §3), `fsd-structure` §4 1번 | 아니오 |
| D-26 | `useAuthController.ts:12` FIXME | 건드리지 않음. `GET /v1/offers`는 인증을 보지 않아 401·TOKEN_REVOKED가 나지 않음 | 확정(사용자, 2026-11-10) | `router.py:136~158`(viewer 의존성 없음) | 아니오 |
| D-27 | `placeholders.tsx:1` TODO | `HomePlaceholder`만 지우고 TODO·`언제:`는 그대로(그 목록에 C1이 없음) | 확정(사용자, 2026-11-10) | 요청서 §10 | 아니오 |
| D-28 | 시간대 | 브라우저 로컬 시간으로 표기. 서버는 오프셋 포함 ISO(`DateTime(timezone=True)`)를 보냄 | 확정(사용자, 2026-11-10) | `catalog/infrastructure/models.py:10`, 서비스 대상 지역이 한국 | 아니오 |
| D-29 | 위치 값 보관 | 저장하지 않음(메모리에만). 새로고침하면 다시 요청 | 확정(사용자, 2026-11-10) | 개인정보 최소화. F17의 토큰 규칙과 같은 방향 | 아니오 |
| D-30 | 조회 파라미터 | `lat`·`lng`·`radius_km`(위치 있을 때)·`keyword`(있을 때)·`sort`·`page`·`size`만. `category`는 화면에 없어 안 보냄, `status`는 기본값 | 확정(사용자, 2026-11-10) | `screens.md` C1에 카테고리 칩 없음 | 아니오 |
| D-31 | 세션 확인 중 탭 클릭 | `loading`·`error`에서는 탭 경로로 이동(로그인 이동은 `anonymous`일 때만) | 확정(사용자, 2026-11-10) | 로딩 중 잘못 `/login`으로 보내지 않음. 이후 보호 화면의 가드가 최종 판단 | 아니오 |
| D-32 | 검색어가 있는 빈 목록 | 문구·버튼 임시(`검색 결과가 없어요` / `다른 상품명으로 검색해 보세요.` / `검색어 지우기`). 위치가 없으면 반경 넓히기 버튼 없음 | 확정(문구는 임시, M-1) | `EmptyState/README.md`(버튼은 다음 행동 하나), 정본 문구는 검색어 없음 경우만 있음 | 아니오 |
| D-33 | 반경 상태 | `useHomeOffers`가 `radiusKm`(기본 3)·`setRadiusKm`을 가짐. 지금은 빈 목록의 「반경 5km로 넓히기」만 이를 바꿈. C1a가 같은 값을 씀. 범위 검증(0.1~20)은 C1a에서 **(→ D-37·D-48로 구현, §12)** | 확정(사용자, 2026-11-10) | `catalog.md` §8 `radius_km` 기본 3, EmptyState 문구, C-11 | 아니오 |
| D-34 | 로그인 상태의 상단 오른쪽 | 비어 있음(로그인 링크 숨김). 이름·계정 버튼 등은 정본 없음 | 확정(사용자, 2026-11-10) | `screens.md` C1 | 아니오 |

## 10. 질문 목록 (추천안 포함)

| Q | 질문 | 추천 | 관련 |
| --- | --- | --- | --- |
| Q-1 | 이번 범위를 C1 + 고객 셸 + `/` 교체로 하고, C1a는 자리만 둘지 | 그렇게 한다 | D-2, D-5 |
| Q-2 | C1a 전 위치 칩 동작: ① 표시만 ② 현재 위치 재요청 ③ 숨김 | ① | D-4 |
| Q-3 | 품절 카드를 목록에 보일지(판매 중 뒤에 이어 붙이려면 두 번째 조회가 필요, 백엔드가 다중 `status`를 받는 방법도 있음). 지금은 안 보임 | 이번에는 안 보임(D-12 ①), 필요하면 ② | C-2, D-12 |
| Q-4 | 다음 쪽 보기: 「더 보기」 버튼 / 무한 스크롤 / 첫 쪽만. 문구 「더 보기」 | 버튼 | C-8, D-11 |
| Q-5 | 위치 칩의 동 이름(「망원동」)을 어떻게 얻을지(좌표 → 동네 이름 변환 API 없음). 지금은 `내 주변 · 3km` | 임시 라벨로 진행, C1a 설계 때 주소 변환과 함께 결정 **(→ Q-13, §12.11)** | C-4, D-21 |
| Q-6 | 비로그인 `내 예약`·`마이` 탭 → A1 → 로그인 뒤 돌아올 경로와 이름(`/reservations`, `/my`) | 임시 이름으로 진행, C5·C6 설계 때 확정 | D-6, M-8 |
| Q-7 | 로그인한 고객에게도 「사장님이신가요? 입점 신청」을 항상 보일지 | 항상 보임(명세 그대로) | D-22 |
| Q-8 | 할인 응답에 이미지(상품 `product_image` 첫 장)를 넣을지(백엔드). 지금은 항상 기본 그림 | 백엔드 팀에 요청 | C-3, D-19 |
| Q-9 | `Chip` 비활성 모양과 고객 PC 420px 프레임 클래스를 디자인 시스템에 추가할지(지금은 CSS Module 임시) | 디자인 시스템에 요청 | C-5, C-6 |
| Q-10 | `tests/app/router/routes.test.tsx`에 `HomePlaceholder`를 기대하는 단언이 있으면 Red 단계에서 `HomePage` 기대로 바꾸는 것을 `fe-qa`에게 맡길지 | 그렇게 한다 | §6 |
| Q-11 | 임시 문구 묶음(D-20, D-21, D-32): 정본 문구가 생길 때까지 임시값으로 진행해도 되는지 | 진행 | M-1 |
| Q-12 | 남은 시간 1시간 정각(`판매 마감 1시간 전`)·24시간 이상, 다른 날 픽업(`MM/DD …`) 표기 | 임시값으로 진행 | D-15, D-16, M-9 |

### 질문 결정 결과 (2026-11-10)

| Q | 결과 |
| --- | --- |
| Q-1 | 추천안대로 확정(C1 + 고객 셸 + `/` 교체, C1a는 자리만) |
| Q-2 | ① 확정(D-4: 표시만, C1a 때 button) |
| Q-3 | ① 확정(D-12: status 안 보냄, 품절 카드는 목록에 안 나옴, 카드 부품은 품절을 그림) |
| Q-4 | 추천안대로 확정(「더 보기」 버튼, 문구는 임시) |
| Q-5 | 추천안대로 확정(임시 라벨로 진행) |
| Q-6 | ① 확정(D-6: 임시 경로, 비로그인 → A1 → 탭 경로 복귀, M-8 FIXME 유지) |
| Q-7 | 추천안대로 확정(입점 신청 항상 보임) |
| Q-8 | 프론트 범위 밖. 사용자에게 보고됨, 미결(외부). C-3·D-19·M-5 임시 처리 유지 |
| Q-9 | 프론트 범위 밖. 사용자에게 보고됨, 미결(외부). C-5·C-6·M-7·M-10 임시 처리 유지 |
| Q-10 | 추천안대로 확정(Red 단계에서 `fe-qa`가 routes.test의 `HomePlaceholder` 단언을 `HomePage` 기대로 바꿈) |
| Q-11 | 추천안대로 확정(임시 문구로 진행) |
| Q-12 | 추천안대로 확정(임시 표기로 진행) |

## 11. 차단 이슈

없음. 모든 미정 항목에 임시값이 있어 골격·Red를 시작할 수 있다. 결정이 바뀌면 영향을 받는 코드: 위치 칩(D-4, 작음), 품절 카드 조회(D-12, 조회 조건·훅), 탭 경로(D-6, `routes.ts` 상수), 임시 문구(D-20, 문구 상수 한 곳씩).

---

## 12. 2차: C1a 위치 · 반경 (바텀시트)

- 대상: `features/offers`(시트·훅·domain 추가), `pages/home`(시트를 여는 조립). 새 page·새 라우트·새 포트·새 토큰·새 구현체 없음(`wiring.ts`·`app/container.ts`·`infrastructure` 변경 없음).
- 상태: **사용자 결정 완료, 차단 없음**(2026-11-10). §1~§11(C1)은 고치지 않았고, C1a로 바뀌는 곳(D-2·D-4·D-33·M-2·Q-5, §7(d) 위치 칩 단언)에만 "C1a로 대체" 표시를 붙였다. D-35~D-49와 Q-13~Q-22를 사용자가 확정했다(§12.11 "질문 결정 결과"). 문구 정본이 없는 D-40·D-43은 "임시 문구로 진행"이 확정된 것이라 값은 임시이고 M-13 TODO가 남는다. 백엔드에 연결할 수 없어 프론트 범위만 진행하며 백엔드 요청·변경은 하지 않는다. 구현을 막는 항목은 없다(§12.12).
- 정본: `screens.md` C1a(138~150줄), `wireframe.html` 326~341줄(시트 문구·구성, 329줄 `chip on`), `components/BottomSheet/README.md`, `Chip/README.md`, `open-issues.md` C1a(8줄), `api-map.md` C1a 행, `reference/catalog.md` §8(`radius_km` 0.1~20, 기본 3).
- 백엔드 실재 확인: `backend/src/catalog/presentation/router.py:111`(`RadiusParam = float | None, ge=0.1, le=20`), `:136~158`(`GET /v1/offers`가 `radius_km: RadiusParam`을 받음), `backend/src/error_handlers.py:53~63`(`RequestValidationError` → **400** `VALIDATION_ERROR`). 범위 0.1~20은 명세·화면 명세·백엔드가 일치한다. 상태 코드 표기 차이는 C-15.
- 재사용: `shared/ui/Overlay`(admin `SanctionSheet`·`PointGrantSheet`과 같은 방식. 딤 클릭·Esc 닫기, 포커스 가두기·복귀, `.app` 프레임에 포털), `useHomeOffers`의 `radiusKm`·`setRadiusKm`·`location.retry`(D-33, D-2). 새 CSS·새 클래스 없음(`.sheet`·`.t`·`.btn`·`.btn.pri`·`.m`·`.lbl`·`.scroll`·`.chip`은 `bundle.css`에 있는 클래스: F12).

### 12.1 계층 배치

| FSD | slice | 내용 |
| --- | --- | --- |
| features | `features/offers` | 시트 domain 규칙·시트 상태 훅·`LocationSheet`·`LocationChip` 대화형화 |
| pages | `pages/home` | `HomePage`가 `useLocationSheet(home)`로 시트를 열고 `LocationSheet`를 그린다 |
| shared | `shared/ui/Overlay` | 그대로 사용(변경 없음) |

- `entities`는 만들지 않는다(D-3 그대로: 시트는 offers 영역만 씀).

### 12.2 파일 목록과 export (신규 / 변경)

| 구분 | 파일 | export |
| --- | --- | --- |
| 신규 | `features/offers/domain/locationSheet.ts` | `MIN_RADIUS_KM = 0.1`, `MAX_RADIUS_KM = 20`, `RADIUS_CHIPS: readonly number[] = [1, 3, 5, 10]`, `isValidRadiusKm(km: number): boolean`, `formatRadiusKm(km: number): string`(`3` → `3km`, `0.5` → `0.5km`), `locationStatusLine(status: LocationStatus): string`, `canRefreshLocation(status: LocationStatus): boolean` |
| 신규 | `features/offers/application/useLocationSheet.ts` | `useLocationSheet(home: Pick<HomeOffers, 'radiusKm' \| 'setRadiusKm' \| 'location'>): LocationSheetState`, `type LocationSheetState` |
| 신규 | `features/offers/presentation/LocationSheet.tsx` | `LocationSheet({ sheet })`, `type LocationSheetProps = { sheet: LocationSheetState }` |
| 변경 | `features/offers/domain/search.ts` | `locationChipLabel`이 비공개 `formatRadius` 대신 `formatRadiusKm`을 쓴다(출력 `내 주변 · 3km`·`0.5km` 그대로, 기존 테스트 무변경). 그 위 M-1 TODO 주석은 그대로 |
| 변경 | `features/offers/application/useHomeOffers.ts` | `setRadiusKm(km)`이 `isValidRadiusKm(km)`이 거짓이면 아무것도 하지 않는다(D-48). `HomeOffers` 타입·그 밖은 그대로 |
| 변경 | `features/offers/presentation/LocationChip.tsx` | `LocationChip({ label, open, onClick })`: `span.chip` → `button.chip`. M-2 TODO 삭제 |
| 변경 | `features/offers/index.ts` | `export { useLocationSheet } from './application/useLocationSheet'`, `export type { LocationSheetState } from './application/useLocationSheet'`, `export { LocationSheet } from './presentation/LocationSheet'` 추가 |
| 변경 | `pages/home/presentation/HomePage.tsx` | `const sheet = useLocationSheet(home)`, `<LocationChip label open={sheet.isOpen} onClick={sheet.open}/>`, `{sheet.isOpen ? <LocationSheet sheet={sheet}/> : null}`(`.link` 아래, `.bar` 밖) |

- 공개 API 변경은 위 `index.ts` 세 줄 추가뿐이다. infrastructure·`wiring.ts`는 내보내지 않는다(F18). `isValidRadiusKm` 등 domain 함수는 page가 쓰지 않아 공개하지 않는다.
- 시그니처 표현용 타입(`LocationSheetState`)은 `useLocationSheet.ts`에서 export하고 `index.ts`로도 내보낸다(`LocationSheetProps`는 내보내지 않음).

### 12.3 domain 규칙 (`locationSheet.ts`, 순수 TypeScript, F6·F7)

- `isValidRadiusKm(km)`: `Number.isFinite(km) && km >= 0.1 && km <= 20`. 경계 0.1·20은 포함(백엔드 `ge=0.1, le=20`과 같음). `NaN`·`±Infinity`는 거짓.
- `RADIUS_CHIPS`: `[1, 3, 5, 10]`(`screens.md` C1a 칩). 모두 `isValidRadiusKm`이 참이다. `DEFAULT_RADIUS_KM`(3)·`WIDEN_RADIUS_KM`(5)은 `search.ts`에 그대로 두며 둘 다 칩 값이라, 시트에서 어떤 값이 선택돼 있어도 칩 하나가 `on`이다.
- `formatRadiusKm(km)`: `` `${km}km` ``. 정수면 소수점 없음(`3km`), 소수는 그대로(`0.5km`). 칩 라벨과 위치 칩 라벨이 한 함수를 쓴다.
- `locationStatusLine(status)`(D-40, 임시): `located` → `지금: 현재 위치`, `locating` → `지금: 위치 확인 중`, `unavailable` → `지금: 위치 없음`.
- `canRefreshLocation(status)`: `locating`이면 거짓, 그 외 참(위치 확인 중에 요청이 겹치지 않게).

### 12.4 application (`useLocationSheet`)

포트는 새로 받지 않는다. `useHomeOffers()`가 돌려준 값(`radiusKm`, `setRadiusKm`, `location`)만 받는다(application → application, F5·F18 무관). 시트 상태는 이 훅이 갖고, page는 훅과 컴포넌트를 연결만 한다(D-36).

```
LocationSheetState = {
  isOpen: boolean
  open(): void                  // isOpen = true, draftRadiusKm = home.radiusKm (열 때마다 현재 값으로 시작)
  close(): void                 // isOpen = false, draft 버림. home.radiusKm 불변
  draftRadiusKm: number
  selectRadius(km: number): void // isValidRadiusKm이 참일 때만 draft 변경. home·목록은 안 바뀜
  apply(): void                 // isOpen일 때 home.setRadiusKm(draft) 후 닫기. draft가 현재와 같으면 재조회 없음
  statusLine: string            // locationStatusLine(home.location.status)
  canUseCurrent: boolean        // canRefreshLocation(home.location.status)
  refreshLocation(): void       // canUseCurrent일 때만 home.location.retry() (시트 유지, draft 유지)
}
```
- 상태 전이: `closed` → `open()` → `open(draft=현재 반경)` → `selectRadius*` → `apply()`(→ `closed`, 반경 반영, 목록 재조회) 또는 `close()`(→ `closed`, 반영 없음).
- 「적용」 전까지 목록·위치 칩 라벨은 바뀌지 않는다(D-38). 「현재 위치 사용」은 적용 전이라도 위치 확인을 즉시 다시 한다(D-39). 그 결과 위치 상태가 `locating` → `located`/`unavailable`로 바뀌며 `useHomeOffers`가 기존 규칙(§3.3)대로 목록을 다시 조회한다.
- 위치 확인 중에도 「적용」은 가능하다(반경 값만 저장되고 위치가 확정되면 조회에 쓰인다). 위치가 없으면(`unavailable`) 반경은 조회에 쓰이지 않는다(D-9, `area: null`). 반경 값은 보관되어 위치가 생기면 쓰인다(D-42).
- 비동기 요청을 직접 하지 않으므로 abort·언마운트 정리는 `useCurrentLocation`(기존)이 한다(F10).
- 오류 상태: 위치 요청 실패는 `unavailable`로 합쳐져 있어(D-9) 이 훅에 오류 상태를 더하지 않는다. **검증 오류 표시는 없다**: 입력이 칩뿐이라(D-37) 범위 밖 값이 화면에서 나오지 않고, 코드 경로로 들어온 범위 밖 값은 무시한다(D-48).

### 12.5 presentation

**`LocationChip({ label, open, onClick })`**: `<button type="button" className={open ? 'chip on' : 'chip'} aria-haspopup="dialog" aria-expanded={open} onClick={onClick}>{label}</button>`. 접근 이름은 `label`(`내 주변 · 3km`). 열려 있을 때 `chip on`은 와이어프레임 329줄(D-41).

**`LocationSheet({ sheet })`** (사용: `BottomSheet`·`Chip`·`Button`, `shared/ui/Overlay`):
```
<Overlay onClose={sheet.close}>
  <div className="sheet" role="dialog" aria-modal="true" aria-labelledby=titleId>
    <div className="t" id=titleId style={{ fontSize: 17 }}>어디서 찾을까요?</div>     (admin 시트와 같은 17px 인라인)
    <button type="button" className="btn" aria-disabled={!sheet.canUseCurrent ? 'true' : undefined} onClick={sheet.refreshLocation}>◎ 현재 위치 사용</button>
    <div className="m" aria-live="polite">{sheet.statusLine}</div>
    <div className="lbl" id=labelId>반경</div>
    <div className="scroll" role="group" aria-labelledby=labelId>
      {RADIUS_CHIPS.map(km => <button type="button" className={km === sheet.draftRadiusKm ? 'chip on' : 'chip'} aria-pressed={km === sheet.draftRadiusKm} onClick={() => sheet.selectRadius(km)}>{formatRadiusKm(km)}</button>)}
    </div>
    <div className="m">위치를 허용하지 않으면 거리 없이 전체 할인을 보여 줘요.</div>
    <button type="button" className="btn pri" onClick={sheet.apply}>적용</button>
  </div>
</Overlay>
```
- `Overlay`: `dismissible` 기본 참(대기 중 상태가 없음). 열리면 첫 포커스 가능 요소(「◎ 현재 위치 사용」)에 포커스, 닫히면 칩 버튼으로 포커스 복귀(Overlay 기본 동작). 시트에 「취소」 버튼은 두지 않는다(와이어프레임·`screens.md`에 없음, C-16, D-38).
- 화면 상태별: **로딩**(위치 확인 중) = 상태 줄 `지금: 위치 확인 중`, 「현재 위치 사용」 `aria-disabled`, 반경 칩·「적용」은 동작. **위치 불가**(`unavailable`) = 상태 줄 `지금: 위치 없음`, 나머지 같음, 안내 문구가 이미 상태를 설명한다. **정상**(`located`) = `지금: 현재 위치`. **검증 오류·빈·서버 오류**는 이 시트에 없다(서버를 직접 부르지 않고 입력이 칩뿐). 「적용」은 `onClick`에서 `sheet.apply`를 부르고 시트는 훅이 닫는다.
- 문구 출처(F13): 제목 「어디서 찾을까요?」·상태 줄 형식·안내 「위치를 허용하지 않으면 거리 없이 전체 할인을 보여 줘요.」는 `wireframe.html:332~337`(`screens.md` C1a에는 없음, C-14). 「◎ 현재 위치 사용」·「적용」·「반경」·칩 「1km」「3km」「5km」「10km」는 `screens.md` C1a. 「지금: …」의 값(`현재 위치`·`위치 확인 중`·`위치 없음`)은 동 이름을 모르는 임시(C-4, D-40, M-13).
- 문자열은 JSX 텍스트로만 출력(F17). 파일 첫머리에 `// open-issues: C1a 주소 입력(주소 → 좌표 변환)은 고객용 API가 없어 만들지 않는다. 현재 위치만 쓴다.`(M-12).

### 12.6 `HomePage` 변경

- `useHomeOffers()`와 `useAuth()` 한 번씩에 `useLocationSheet(home)` 한 번을 더한다. 다른 조립은 그대로다.
- `.bar`의 칩만 `onClick`·`open`을 받는다. 시트는 `Overlay`가 `.app`에 포털로 띄우므로 위치는 `.link` 아래 아무 곳이어도 된다.
- 셸(`CustomerLayout`)·탭 바 변경 없음. 시트가 열려도 탭 바는 딤 아래에 있다(딤이 `.app`을 덮음).

### 12.7 테스트 목록 (`tdd-workflow` §2, 위치 `tests/` 아래)

시간·가짜: §7과 같다(`tests/features/offers/fakes/*.fake.ts`, `FakeLocationProvider`는 `resolve()` 수동·호출 횟수 기록, `FakeOfferRepository`는 호출 인자 기록, `renderHome`·`renderWithOffers`). 시트 단독 렌더 테스트는 `.app` 래퍼 없이 해도 된다(Overlay가 `document.body`로 대체). 시트 안 칩 조회는 `getByRole('dialog')`로 범위를 좁히고 이름은 정확히 일치(`exact`)로 찾는다(「반경 5km로 넓히기」 버튼·위치 칩과 겹침 방지).

**(a) domain** `tests/features/offers/domain/locationSheet.test.ts` (20)
- `isValidRadiusKm`: 0.1 → true / 0.09 → false / 0 → false / -1 → false / 3 → true / 20 → true / 20.1 → false / NaN → false / Infinity → false (9)
- `RADIUS_CHIPS`: `[1, 3, 5, 10]`이고 모두 유효하며 `DEFAULT_RADIUS_KM`·`WIDEN_RADIUS_KM`을 포함 (1)
- `formatRadiusKm`: 1 → `1km` / 3 → `3km` / 10 → `10km` / 0.5 → `0.5km` (4)
- `locationStatusLine`: located → `지금: 현재 위치` / locating → `지금: 위치 확인 중` / unavailable → `지금: 위치 없음` (3)
- `canRefreshLocation`: locating → false / located → true / unavailable → true (3)
- 회귀(기존 `search.test.ts` `locationChipLabel` 4건, 단언 변경 없이 통과해야 함)

**(b) application**
- `tests/features/offers/application/useHomeOffers.test.tsx` (추가 6): `setRadiusKm(10)` → `radiusKm` 10, 재조회 `area.radiusKm` 10, `chipLabel` `내 주변 · 10km` / `setRadiusKm(0.1)` → 반영(경계) / `setRadiusKm(20)` → 반영(경계) / `setRadiusKm(0.09)` → 상태·재조회 변화 없음 / `setRadiusKm(20.1)` → 변화 없음 / `setRadiusKm(NaN)` → 변화 없음
- `tests/features/offers/application/useLocationSheet.test.tsx` (신규 17, `renderHook(() => { const home = useHomeOffers(); return { home, sheet: useLocationSheet(home) } })`):
  - 처음 `isOpen` false, `draftRadiusKm` 3 (1)
  - `open()` → `isOpen` true, `draftRadiusKm`이 현재 `radiusKm` (1)
  - `selectRadius(5)` → `draftRadiusKm` 5, `home.radiusKm` 3 그대로, 저장소 호출 수 불변(적용 전 목록 유지) (1)
  - `selectRadius(25)`·`selectRadius(NaN)` → draft 변화 없음 (1)
  - `apply()` → `home.radiusKm` 5, 저장소가 `area.radiusKm` 5로 재조회, `isOpen` false, `home.chipLabel` `내 주변 · 5km` (1)
  - draft가 현재와 같을 때 `apply()` → 저장소 추가 호출 0, `isOpen` false (1)
  - `close()` → `isOpen` false, `home.radiusKm` 불변, 저장소 호출 불변 (1)
  - `selectRadius(10)` 뒤 `close()`, 다시 `open()` → draft가 현재 반경(10이 아님) (1)
  - 5로 적용한 뒤 `open()` → draft 5 (1)
  - `refreshLocation()`(located) → 위치 provider 호출 +1, `locating` → `located`, `isOpen` 그대로 (1)
  - `refreshLocation()`(locating 중) → provider 호출 불변, `canUseCurrent` false (1)
  - `refreshLocation()`(unavailable) → provider 다시 호출, 결과가 다시 unavailable이어도 `isOpen` 유지 (1)
  - `statusLine`: located·locating·unavailable 각각 domain 문구와 같음 (3)
  - `selectRadius(5)` 뒤 `refreshLocation()` → draft 5 유지 (1)
  - 위치 확인 중 `apply()` → 반경 반영, 위치가 확정되면 그 반경으로 조회 (1)
  - 위치 `unavailable`에서 `apply()` → `radiusKm` 반영, 조회 `area` null 그대로(저장소 재조회 없음) (1)

**(c) infrastructure**: 변경 없음. 새 테스트 없음(포트·구현체 변경 없음).

**(d) presentation·pages**
- `tests/features/offers/presentation/LocationChip.test.tsx` (신규 5): 역할 `button`, 이름 `내 주변 · 3km` / 클릭 → `onClick` 1회 / `open`이면 `chip on` 클래스·`aria-expanded="true"` / 닫히면 `aria-expanded="false"`·`on` 없음 / `aria-haspopup="dialog"`
- `tests/features/offers/presentation/LocationSheet.test.tsx` (신규 14, 가짜 `sheet` 객체):
  - 제목 `어디서 찾을까요?`, `role="dialog"`·`aria-modal="true"`·`aria-labelledby`가 제목을 가리킴 (1)
  - 버튼 `◎ 현재 위치 사용`·`적용`, 라벨 `반경`, 안내 `위치를 허용하지 않으면 거리 없이 전체 할인을 보여 줘요.` (1)
  - 반경 칩 4개가 1km·3km·5km·10km 순서 (1)
  - `draftRadiusKm` 칩만 `aria-pressed="true"`·`on` (1)
  - 칩 클릭 → `selectRadius(5)` (1)
  - `statusLine`이 보임(`지금: 현재 위치`) (1)
  - 「◎ 현재 위치 사용」 클릭 → `refreshLocation` (1)
  - `canUseCurrent` false → `aria-disabled="true"`, 클릭해도 `refreshLocation` 0회 (1)
  - 「적용」 클릭 → `apply` (1)
  - Esc → `close` (1)
  - 딤 클릭 → `close` / 시트 안쪽 클릭 → `close` 아님 (2)
  - 열릴 때 첫 포커스가 「◎ 현재 위치 사용」 (1)
  - 「취소」 버튼이 없음 (1)
- `tests/pages/home/HomePage.test.tsx`
  - **변경 1건**: `:171` `위치 칩은 button이 아니다` → `위치 칩은 button이고 이름이 칩 라벨이다`: `getByRole('button', { name: '내 주변 · 3km' })`가 있다(기존 `not.toBeInTheDocument` 단언을 반대로 바꿈).
  - **추가 6건**: 칩 클릭 → `dialog` 보임·칩 `aria-expanded` / 시트에서 `5km` 선택(적용 전): 저장소 호출 수 불변·칩 `내 주변 · 3km` 유지 / 「적용」 → 시트 닫힘·`area.radiusKm` 5 재조회·칩 `내 주변 · 5km` / Esc → 닫힘·반경 3 유지·포커스가 칩으로 복귀 / 「현재 위치 사용」 → 위치 provider 호출 +1·시트 유지 / 위치 거부: 칩 `위치 없음`·시트 `지금: 위치 없음`·`5km` 적용해도 조회 `area` null
- 그 밖에 바뀌는 기존 단언은 없다: `tests/features/offers/presentation/SortChips.test.tsx:8`(`getAllByRole('button')`)은 `SortChips`만 렌더해 영향 없고, `OfferCard.test.tsx:69`도 같다. `HomePage.test.tsx`의 `findByText('내 주변 · 3km')`는 `button` 텍스트에도 맞아 그대로 통과한다. `tests/app/container.test.ts`(토큰 불변), `routes.test.tsx`, `CustomerLayout.test.tsx` 무변경.

**(e) E2E** `e2e/home.spec.ts`에 `C1a` describe 추가(D-47, 기존 `mockOffers`·`SEOUL` 재사용, 시트 안 칩은 `getByRole('dialog').getByRole('button', { name: '5km', exact: true })`) (3)
- 백엔드에 연결할 수 없으므로 E2E는 기존처럼 `page.route('**/v1/offers**')` 모킹만 쓴다. 실행 검증에서 Vite proxy → 백엔드 실제 응답 확인은 **범위 밖**이다.
- 위치 허용: 칩 `내 주변 · 3km` 클릭 → 시트 → `5km` 선택 → 적용 전 새 요청 없음 → 「적용」 → 요청 `radius_km=5`, 칩 `내 주변 · 5km`, 시트 닫힘
- 위치 허용: 시트에서 `10km` 선택 후 Esc → 닫힘, 새 요청 없음, 다시 열면 `3km` 선택 상태(draft 버림), 마지막 요청은 `radius_km=3`
- 위치 거부(기존 거부 describe 방식): 칩 `위치 없음` → 시트 `지금: 위치 없음` → `5km` 적용 → 요청에 `lat`·`radius_km` 없음 → 「◎ 현재 위치 사용」 클릭 후에도 `lat` 없음·시트가 열려 있음

| 구분 | 내용 | 신규 개수 |
| --- | --- | --- |
| domain | locationSheet 20 | 20 |
| application | useHomeOffers 추가 6 + useLocationSheet 17 | 23 |
| presentation·pages | LocationChip 5 + LocationSheet 14 + HomePage 추가 6 | 25 |
| E2E | `e2e/home.spec.ts` | 3 |
| 합계 | (HomePage 변경 단언 1건은 개수에 넣지 않음) | 71 |

정본이 없어 목록에서 뺀 것: 「지금: …」 값의 최종 문구(임시값 기대는 넣음, 정본이 정해지면 상수와 기대값을 함께 고침), 위치 거부 상태에서 「현재 위치 사용」을 눌렀을 때 안내 문구(Q-19), 직접 입력 반경(Q-15).

### 12.8 골격 (`tdd-workflow` §3)

`locationSheet.ts` 전체(상수·함수)는 함수 본문을 `throw new Error('not implemented: <이름>')`로 두되 상수(`MIN_RADIUS_KM`·`MAX_RADIUS_KM`·`RADIUS_CHIPS`)는 실제 값으로 만든다. `useLocationSheet`은 `LocationSheetState` 타입을 실제로 만들고 본문은 `not implemented`. `LocationSheet`는 `null`. `LocationChip`은 시그니처(`open`, `onClick`)를 받고 현재의 `span.chip`을 그대로 유지한다(Red에서 `button` 단언이 실패해야 하므로). `index.ts`·`HomePage` 연결은 골격에서 하되 `HomePage`는 `sheet.isOpen`이 거짓이면 아무것도 안 그리므로 기존 홈 테스트는 통과한다(**`tdd-workflow` §3 예외, 확정(사용자, 2026-11-10)**: `useLocationSheet`이 `not implemented`를 던지면 기존 홈 테스트가 깨지므로 골격 훅은 던지지 않고 닫힌 상태 객체를 돌려준다: `isOpen: false`, 나머지 함수는 빈 본문. 이유는 기존 홈 테스트 보호). `useHomeOffers`의 `setRadiusKm` 가드는 Green에서 한다(골격은 그대로).

### 12.9 남길·지울 작업 주석 (`code-annotations`, F19)

| M | 위치 | 처리 | 내용 |
| --- | --- | --- | --- |
| M-2 | `features/offers/presentation/LocationChip.tsx:1` | **삭제**(이번에 고침) | `언제: C1a 구현 시` 이행. `annotations.mjs list --match C1a`에서 사라져야 한다 |
| M-3 | `features/offers/infrastructure/browserLocationProvider.ts:3` | **유지** | `// open-issues: C1a 위치는 현재 위치만 사용한다(주소 → 좌표 변환 확인 필요).` |
| M-12 | `features/offers/presentation/LocationSheet.tsx` 첫머리 | 신규 `open-issues` | `// open-issues: C1a 주소 입력(주소 → 좌표 변환)은 고객용 API가 없어 만들지 않는다. 현재 위치만 쓴다.` |
| M-13 | `features/offers/domain/locationSheet.ts`(`locationStatusLine` 위) | 신규 TODO | `// TODO: 시트 상태 줄이 「지금: 현재 위치」로 임시다. 와이어프레임은 「지금: 망원동 (현재 위치)」.`<br>`//   왜: 좌표 → 동 이름을 얻을 API가 없다 (docs/design/frontend/offers.md C-4, C-17, D-40, Q-13)`<br>`//   언제: 결정 후 (백엔드: 좌표 → 동 이름 변환 제공)` |
| M-1 | `search.ts`·`offerEmpty.ts:12`·`NearbyOfferSection.tsx`(문구 TODO) | **유지, 수정 없음** | 위치 칩 라벨을 C1a가 바꾸지 않으므로(D-44) 세 TODO의 요약·`왜:`·`언제:`가 그대로 맞다. Q-13이 동 이름 표시로 결정되면 그때 `locationChipLabel` 시그니처와 세 TODO를 함께 고친다 |

- 새 `FIXME`는 없다. `annotations.mjs check` 위반 0이어야 한다.
- 범위 밖 TODO 11건·FIXME 1건(`customerTabs.ts:15`, 언제: C5·C6 구현 시)은 이번에 손대지 않는다.

### 12.10 결정 표 (D-35~)

| D | 항목 | 값 | 상태 | 근거 | 구현을 막는가 |
| --- | --- | --- | --- | --- | --- |
| D-35 | 배치 | 새 page·라우트 없음. 시트·훅·domain은 `features/offers`, 여는 조립은 `pages/home`. `shared/ui/Overlay` 재사용 | 확정(발주서 §1) | `fsd-structure` §7, admin 시트와 같은 방식 | 아니오 |
| D-36 | 시트 상태 위치 | `isOpen`·`draftRadiusKm`·적용 로직은 `useLocationSheet`(application). page는 연결만. 선택지: ① 훅(추천) ② page `useState`+시트 안 draft(훅 테스트 불가, 조립 코드에 규칙이 섞임) | 확정(사용자, 2026-11-10) | F7, 훅 상태 전이를 단위 테스트로 잠그기 위해 | 아니오 |
| D-37 | 반경 입력 | 칩 4개(1·3·5·10km)만. 직접 입력 없음. 「반경」은 칩 그룹의 라벨. 선택지: ① 칩만(추천) ② 칩 + 숫자 입력(0.1~20 검증 오류 표시 필요, 문구 정본 없음) | 확정(사용자, 2026-11-10) | `screens.md` C1a 칩·입력 라벨, `wireframe.html:335~336`(칩만), C-18 | 아니오 |
| D-38 | 「적용」 전까지 | 시트 안 선택은 draft. 「적용」을 누르기 전까지 목록·칩 라벨 불변. 「적용」 = 반경 반영 + 닫기. Esc·딤 클릭 = draft 버리고 닫기. 「취소」 버튼 없음. 선택지: ① 위 방식(추천) ② 칩을 누르는 즉시 적용 | 확정(사용자, 2026-11-10) | `screens.md` C1a 버튼 「적용」(적용 단계가 있음), `wireframe.html:338`, C-16 | 아니오 |
| D-39 | 「◎ 현재 위치 사용」 | 누르면 즉시 `location.retry()`(위치 재요청). 시트 유지, draft 유지. 위치 확인 중에는 `aria-disabled`·무동작. 선택지: ① 즉시(추천) ② 「적용」 때 함께 실행 | 확정(사용자, 2026-11-10) | `retry`가 C1a용 자리(D-2), D-4(거부 뒤에는 브라우저가 다시 묻지 않을 수 있음) | 아니오 |
| D-40 | 시트 상태 줄 | `지금: 현재 위치` / `지금: 위치 확인 중` / `지금: 위치 없음`(M-13) | 확정(사용자, 2026-11-10, 문구는 임시로 진행: M-13) | `wireframe.html:334` 「지금: 망원동 (현재 위치)」의 동 이름을 알 수 없음(C-4) | 아니오 |
| D-41 | 위치 칩 | `button.chip`, 라벨 그대로(D-21), `aria-haspopup="dialog"`, 열린 동안 `chip on`+`aria-expanded` | 확정(사용자, 2026-11-10) | `wireframe.html:303`(`chip`)·`329`(`chip on`), D-4 | 아니오 |
| D-42 | 위치 없음(`unavailable`)일 때 | 반경 칩·「적용」은 그대로 동작(값 보관). 조회는 반경 없이 전체(D-9). 안내는 정본 문구 「위치를 허용하지 않으면…」(항상 표시)만. 선택지: ① 허용(추천) ② 칩 비활성 | 확정(사용자, 2026-11-10) | `wireframe.html:337`, D-9, `catalog.md` §8(`radius_km`만 보내면 서버가 무시) | 아니오 |
| D-43 | 시트 문구 출처 | 제목·안내·상태 줄 형식은 `wireframe.html:332~337`, 버튼·칩·라벨은 `screens.md` C1a | 확정(사용자, 2026-11-10, 와이어프레임 문구를 임시로 진행: C-14, M-13) | F13: `screens.md`에 없는 문구는 와이어프레임을 따르고 출처를 적는다 | 아니오 |
| D-44 | 위치 칩 라벨 | C1a에서 바꾸지 않는다(D-21 유지, M-1 유지). 동 이름이 가능해지면 Q-13 결정에 따라 `locationChipLabel`을 바꿈 | 확정(사용자, 2026-11-10) | C-4, Q-5 | 아니오 |
| D-45 | 주소 입력·주소 → 좌표 | 만들지 않는다. 시트에 입력칸 없음. `// open-issues:` 유지(M-3)·추가(M-12) | 확정(사용자, 2026-11-10) | `open-issues.md` C1a, `screens.md` C1a 동작 메모 "그 전까지는 현재 위치만" | 아니오 |
| D-46 | 시트 닫힘 방식 | `Overlay` 기본(`dismissible` 참). 대기 중 상태가 없어 닫힘 차단 없음. 닫히면 포커스가 칩으로 복귀 | 확정(사용자, 2026-11-10) | `Overlay.tsx:7~10`, `LogoutConfirmSheet` 패턴 | 아니오 |
| D-47 | E2E | 별도 파일 없이 `e2e/home.spec.ts`에 `C1a` describe 3건 추가 | 확정(사용자, 2026-11-10) | 같은 화면·같은 모킹(`mockOffers`·`SEOUL`) 재사용 | 아니오 |
| D-48 | `setRadiusKm` 범위 밖 값 | 무시(클램프하지 않음). 가드는 `useHomeOffers.setRadiusKm` 한 곳, 규칙은 domain `isValidRadiusKm`. 선택지: ① 무시(추천, `selectSort`와 같은 방식) ② 0.1~20으로 잘라 반영 | 확정(사용자, 2026-11-10) | D-33(검증은 C1a), `router.py:111`(`ge=0.1, le=20`), 서버가 400을 내므로 보내지 않음 | 아니오 |
| D-49 | 반경 표기 함수 | `formatRadiusKm`을 `locationSheet.ts`에 두고 `locationChipLabel`이 재사용(출력 동일) | 확정(사용자, 2026-11-10) | 칩 라벨과 위치 칩 라벨이 한 규칙(F7) | 아니오 |

### 12.11 정합 이슈와 질문

**정합 이슈 (C-13부터, 기존 마지막 C-12)**

| C | 내용 | 양쪽 근거 | 처리 |
| --- | --- | --- | --- |
| C-13 | `screens.md` C1a 칩 목록에 「망원동 · 3km」가 있으나 와이어프레임 C1a는 그 칩을 시트 뒤 `.bar`에 그리고 시트 안에는 반경 칩 4개만 있음 | `screens.md:144` ↔ `wireframe.html:329·336` | 「망원동 · 3km」는 시트 뒤 위치 칩으로 해석(D-41) |
| C-14 | 시트 제목 「어디서 찾을까요?」, 「지금: 망원동 (현재 위치)」, 안내 「위치를 허용하지 않으면 거리 없이 전체 할인을 보여 줘요.」가 와이어프레임에만 있고 `screens.md` C1a 버튼·칩·라벨 목록에는 없음 | `wireframe.html:332~337` ↔ `screens.md:143~145` | 와이어프레임 문구를 쓰고 출처 표시(D-43) |
| C-15 | 반경 범위 오류 응답 표기가 어긋남: `/v1/offers` 에러 표에는 반경 범위 오류 행이 없고, 상품 검색(§7) 표는 422·같은 절 비고는 400이다. 백엔드는 `RequestValidationError`를 400 `VALIDATION_ERROR`로 돌려준다. 범위 값 0.1~20은 모두 일치 | `reference/catalog.md:216·219·428` ↔ `error_handlers.py:53~63`, `router.py:111·141` | 프론트는 범위 밖 값을 보내지 않는다(D-48). 상태 코드 표기 정정은 문서 소유자에게 제안 |
| C-16 | BottomSheet README는 버튼 순서의 마지막을 「취소」로 규정하는데 C1a 와이어프레임·`screens.md`에는 「취소」가 없고 「적용」만 있음 | `components/BottomSheet/README.md:6` ↔ `wireframe.html:338`, `screens.md:143` | 화면 명세를 따라 「취소」 없이 Esc·딤으로 닫음(D-38). Q-18 |
| C-17 | 좌표 → 동 이름 변환 API가 없다(C-4와 같은 뿌리). open-issues C1a는 주소 → 좌표만 다룸 | `open-issues.md:8` ↔ `api-map.md` C1·C1a 행(`GET /v1/offers`만) | 임시 문구(D-40·D-44). Q-13 |
| C-18 | `screens.md`의 「입력 라벨: 반경」은 입력칸이 아니라 와이어프레임에서는 칩 그룹 위 `.lbl`이다. 0.1~20 범위는 API 제약이지 화면 입력 규칙이 아님 | `screens.md:145·149` ↔ `wireframe.html:335~336` | 라벨로 해석(D-37). 직접 입력은 Q-15 |

**질문 목록 (Q-13부터, 기존 마지막 Q-12, 추천안 포함)**

| Q | 질문 | 추천 | 관련 |
| --- | --- | --- | --- |
| Q-13 | (Q-5 이어서) 위치 칩·시트에 동 이름(「망원동」)을 어떻게 얻을지. ① 임시 라벨 유지(`내 주변`·`현재 위치`) ② 백엔드에 좌표 → 동 이름 변환 API 요청(프론트 범위 밖) ③ 프론트에서 외부 지도 API 직접 호출(키 노출, F8 위반 소지) | ① 유지하고 ②를 백엔드에 요청. ③은 하지 않음 | C-4, C-17, D-40, D-44, M-13 |
| Q-14 | 주소 입력으로 위치를 바꾸는 기능(주소 → 좌표 변환 고객용 API) | 이번에 만들지 않음. 백엔드 요청(Q-13과 묶음), 시트에 입력칸 없음 | D-45, open-issues C1a |
| Q-15 | 반경을 칩 외에 직접 입력할지(입력하면 0.1~20 검증 오류 문구가 필요하고 정본 없음) | 칩만(D-37 ①) | D-37, D-48 |
| Q-16 | 「적용」 전까지 목록을 바꾸지 않고, Esc·딤으로 닫으면 선택을 버릴지 | 그렇게 한다(D-38 ①) | D-38 |
| Q-17 | 「◎ 현재 위치 사용」을 누르면 즉시 위치를 다시 확인할지, 「적용」 때 함께 할지 | 즉시(D-39 ①) | D-39 |
| Q-18 | 시트에 「취소」 버튼을 넣을지(BottomSheet README는 있고 C1a 명세는 없음) | 넣지 않는다(C-16) | C-16, D-38 |
| Q-19 | 위치 권한이 거부된 상태에서 「현재 위치 사용」을 눌렀을 때 별도 안내(예: 브라우저 설정에서 허용) 문구를 둘지. 정본 문구 없음 | 두지 않는다(와이어프레임 안내 문구만). 필요하면 디자인 시스템에 문구 요청 | D-39, D-42 |
| Q-20 | 시트가 열린 동안 위치 칩을 `chip on`으로 보일지 | 와이어프레임대로 보인다(D-41) | D-41 |
| Q-21 | 위치가 없을 때(`unavailable`) 반경 칩·「적용」을 허용할지 | 허용(D-42 ①). 값은 보관 | D-42 |
| Q-22 | E2E를 `e2e/home.spec.ts`에 추가할지(새 파일 대신) | 추가(D-47) | D-47 |

**질문 결정 결과 (2026-11-10)** — 사용자 원문: "we cant connect to the backend for now so just do the frontend". 오케스트레이터 해석: 추천안을 모두 수용하고 프론트 범위만 진행, 백엔드 요청·변경은 하지 않음.

| Q | 결과 |
| --- | --- |
| Q-13 | 추천 ① 확정(임시 라벨 유지). 백엔드 연결 불가라 지금은 요청하지 않음. C-17·M-13 임시 처리 유지, `언제: 결정 후 (백엔드: 좌표 → 동 이름 변환 제공)` 그대로 |
| Q-14 | 확정(주소 입력 만들지 않음, D-45). M-12 open-issues 유지. 백엔드 요청도 하지 않음 |
| Q-15 | 추천안대로 확정(칩만, D-37) |
| Q-16 | 추천안대로 확정(적용 전 목록 유지, 닫으면 draft 버림, D-38) |
| Q-17 | 추천안대로 확정(즉시 위치 재확인, D-39) |
| Q-18 | 추천안대로 확정(「취소」 버튼 없음, C-16) |
| Q-19 | 추천안대로 확정(추가 안내 문구 없음) |
| Q-20 | 추천안대로 확정(열린 동안 `chip on`, D-41) |
| Q-21 | 추천안대로 확정(위치 없어도 반경 칩·적용 허용, D-42) |
| Q-22 | 추천안대로 확정(`e2e/home.spec.ts`에 추가, D-47) |
| 골격 예외 | 확정: `useLocationSheet` 골격은 throw 대신 닫힌 상태 객체(§12.8, `tdd-workflow` §3 예외) |
| 기존 단언 변경 | 확정: `tests/pages/home/HomePage.test.tsx:171`을 Red 단계에서 `fe-qa`가 「button이고 이름이 칩 라벨이다」로 바꿈(Q-10과 같은 방식) |
| C-13~C-18 | 설계안의 처리 방식 유지. C-15(상태 코드 표기)는 문서 소유자 제안으로 남김 |

### 12.12 차단 이슈

없음. 모든 미정 항목에 임시값이 있어 골격·Red를 시작할 수 있다. 결정이 바뀌면 영향을 받는 코드: 직접 입력(Q-15, 시트·domain에 검증 오류 상태와 문구 추가), 즉시 적용(Q-16, 훅의 `draft` 제거), 「현재 위치 사용」 시점(Q-17, 훅 `refreshLocation`과 `apply`), 「취소」(Q-18, 시트 한 곳), 동 이름(Q-13, `locationChipLabel`·`locationStatusLine`·M-1·M-13).

### 12.13 구조 확인 (설계 시점)

- F1·F2: `pages/home`은 `@/features/offers` 공개 API만 import. F4: 신규 파일은 `domain`·`application`·`presentation` 안. F5: `useLocationSheet`(application)은 `useHomeOffers`의 타입·domain만 import, `LocationSheet`(presentation)는 application 타입·domain·`shared/ui/Overlay`만 import. F6: `locationSheet.ts`는 순수. F18: 포트·토큰·구현체·`wiring` 변경 없음, `index.ts`는 infrastructure를 내보내지 않음. F12: 새 색·클래스 없음(기존 `bundle.css` 클래스만). F13: 문구 출처를 §12.5에 표시.
