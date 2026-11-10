# 고객 셸·홈·마이 설계: 하단 탭·C1·C1a·C6·C7·C10·C11 + 기존 화면 누락 보완

- 대상: `widgets/customer-nav`(신규), `app/layouts/CustomerLayout.tsx`·`CustomerFrame.tsx`(신규), `app/layouts/AccountLayout.tsx`(수정), `features/offers`(신규 영역), `features/auth`(확장), `pages/home`·`pages/my`·`pages/point-history`·`pages/withdraw`(신규), `pages/login`(안내 한 줄), `app/router/routes.tsx`·`placeholders.tsx`, `app/container.ts`, `shared/lib/routes.ts`·`format.ts`·`useNow.ts`·`useModalFocus.ts`
- 대응 화면: 고객 하단 탭 바(홈·내 예약·마이)·고객 가드, C1 홈·주변 할인(비로그인 가능), C1a 위치·반경, C6 마이, C10 로그아웃 확인(고객 쪽 진입), C7 회원 탈퇴 확인, C11 포인트 내역 전체. 기존 A1·A2·A3·C8·C9·O8의 와이어프레임 누락 보완(§3.7).
- 범위 밖: C2 할인 상세(catalog 담당), C5·C5a·C5b 내 예약(reservations 담당), C3·C3a·C4 결제(payments 담당). 이번에는 C2·C5 자리 page와 연결 안내(§5)만 둔다.
- 상태: 설계안 1차. 사용자가 결정을 위임해 D-1~D-31을 권장안으로 확정했다(2026-11-10). 구현을 막는 항목은 없다. "확인 필요"(§9)는 임시 동작으로 구현하고 주석으로 추적한다.
- 이어받는 설계: `auth.md`(1차), `auth-account.md`(2차, §11 "C11·고객 셸을 위한 메모"를 이 문서가 이어받음), `app-shell.md`(경로 상수 D-17, 자리 page D-8·D-15, 탭 handle). 그 문서들의 D·C 번호는 `auth-account.md D-18`처럼 파일명과 함께 가리킨다.
- 정본: 화면 `../../design-system/screens.md` C1·C1a·C6·C7·C10·C11·E1(+A1·A2·A3·C8·C9·O8), `layout.md`(고객 셸 420px·화면 골격·연결 지도), `wireframe.html` 164~343·477~552줄, `content.md`(숫자·시간 표기), `states.md`(포인트 내역 종류·화면 계산 값·화면 상태 공통), `open-issues.md`(C1a), `components/{TabBar,OfferCard,Chip,BottomSheet,ListRow,EmptyState,Skeleton,Notice,StatusTag,AppBar,Box}/README.md`, `components/bundle.css`(`.tabs`·`.card`·`.price`·`.cd`·`.chip`·`.scroll`·`.dim`·`.sheet`·`.list`·`.li`·`.kv`·`.empty`·`.sk`·`.warn`). API `../../reference/catalog.md` §공통 객체 Offer·§8, `../../reference/auth.md` §3·§4·§5·§12, `api-map.md` C1·C1a·C6·C7·C10·C11.
- 백엔드 실재 확인(`frontend-orchestration.md` §6): `backend/src/catalog/presentation/router.py:136~158` `GET /v1/offers`(쿼리 `lat`·`lng`·`radius_km`·`category`·`keyword`(최대 100)·`status`(기본 `ON_SALE`)·`sort`(기본 `sales_end`)·`page`(1부터)·`size`), 응답 `schemas.py:308~322` `NearbyOfferItem{offer: OfferResponse, distance, unit}`, `OfferResponse` `schemas.py:126~145`(이미지 필드 없음, `status`에 `SUSPENDED` 포함), 정렬 `catalog/domain/search.py:37~45`(`distance` + 위치 없음 → 400 `distance 정렬은 위치 정보가 필요합니다.`). `backend/src/auth/presentation/router.py:65~73` 로그아웃 204, `:130~137` `POST /v1/users/me/withdraw`(`WithdrawalResponse{id,status,deleted_at,cancelled_reservation_count}`), `:140~153` `GET /v1/users/me/points`(`page` 0부터·`size` 1~100), `schemas.py:43~58` `PointLogListResponse{users_point, logs[{id,amount,point_type,balance_after|null,created_at}], page, size, total_elements}`, `:75~76` `WithdrawRequest.password` 1~128자. URI·필드·상태 코드는 명세와 같다. 차이는 C-12.
- 기존 코드 현황(3ddea13): `/`는 `HomePlaceholder`(`<h1>마감 직전</h1>`), 고객 셸·고객 가드·`features/offers` 없음. `features/auth`는 로그인·로그아웃·가입·재설정·프로필·비밀번호 변경까지(`auth-account.md`). `LogoutConfirmSheet`는 상점주 O8에서만 쓰임. `AccountLayout`에 M-6 TODO(고객 셸 프레임), `LoginPage`에 진입 안내 한 줄 TODO.

## 1. 계층 배치와 slice

| slice | 계층 | 이번 변경 | 이유 |
| --- | --- | --- | --- |
| `widgets/customer-nav` | domain, presentation | 신규 | 고객 탭 바는 C1·C5·C6 세 화면에 반복되는 큰 블록(`fsd-structure` §4 4번). `widgets/owner-nav`와 같은 모양 |
| `features/offers` | domain, application, infrastructure, presentation, `wiring.ts` | 신규 | `GET /v1/offers`는 catalog의 할인 엔드포인트(`fsd-structure` §1.1 offers). C2 담당이 같은 영역에 더한다(C-1) |
| `features/auth` | domain, application, infrastructure, presentation | 확장 | `/v1/users/me/points`·`/withdraw`·로그아웃은 auth(`fsd-structure` §1.1) |
| `pages/home` | presentation | 신규 | C1 라우트 하나(C1a는 C1 위 시트) |
| `pages/my` | presentation | 신규 | C6 라우트 하나(C10은 C6 위 시트) |
| `pages/point-history` | presentation | 신규 | C11 |
| `pages/withdraw` | presentation | 신규 | C7 |
| `pages/login` | presentation | 수정 | A1 진입 경로별 안내 한 줄(§3.7) |
| `app` | `layouts/CustomerLayout.tsx`·`CustomerFrame.tsx` 신규, `layouts/AccountLayout.tsx`·`router/routes.tsx`·`router/placeholders.tsx`·`container.ts` 수정 | | 고객 셸·가드·라우트·`wireOffers()` |
| `shared/lib` | (용도별 폴더) | `routes.ts` 수정, `format.ts`·`useNow.ts`·`useModalFocus.ts` 신규 | 경로 상수, 업무를 모르는 숫자·날짜 표기·시계·시트 포커스(§2.1) |

- entities는 만들지 않는다(D-8). `Offer`는 지금 offers 영역만 쓴다. C2의 예약 생성(reservations)은 page에서 두 영역 부품을 조합하므로 entities가 필요 없다. 다른 영역 훅이 할인 데이터를 직접 읽어야 할 때 `entities/offer`로 내린다(`fsd-structure` §6).
- C1a·C10은 라우트 없는 오버레이다. 각 page가 시트를 열면 `.body` 자리에 `.dim`을 그린다(와이어프레임 258·330줄 구조, D-15·D-23).

## 2. 파일 목록과 export

### 2.1 `shared/lib`

| 파일 | 상태 | export |
| --- | --- | --- |
| `routes.ts` | 수정(추가만) | `ROUTES`에 `offerDetail: (id: string) => \`/offers/${encodeURIComponent(id)}\``, `reservations: '/reservations'`, `me: '/me'`, `mePoints: '/me/points'`, `meWithdraw: '/me/withdraw'`. `ROUTE_PATTERNS`에 `offerDetail: '/offers/:offerId'`. `home: '/'`는 기존 값 |
| `format.ts` | 신규 | `groupDigits(n: number): string`(정수 천 단위 쉼표, 음수는 `-` 접두. `Intl` 없이 계산), `formatHm(d: Date): string`(`HH:mm`, 24시간, 로컬 시각), `formatMd(d: Date): string`(`MM/DD`), `isSameLocalDate(a: Date, b: Date): boolean` |
| `useNow.ts` | 신규 | `useNow(intervalMs?: number): Date` — 기본 30초마다 갱신, 언마운트 시 타이머 정리 |
| `useModalFocus.ts` | 신규 | `useModalFocus(ref: RefObject<HTMLElement \| null>, onClose: () => void): void` — 마운트 시 첫 포커스 가능 요소에 포커스, Tab·Shift+Tab을 ref 안에서 순환, Escape → `onClose`. 기존 `OwnerAccountButton`의 트랩은 이번에 바꾸지 않는다(C-11) |

### 2.2 `widgets/customer-nav`

| 파일 | export |
| --- | --- |
| `domain/customerTabs.ts` | `type CustomerTabKey = 'home' \| 'reservations' \| 'me'`, `type CustomerTab = { key; label; path }`, `CUSTOMER_TABS`(홈 `/`, 내 예약 `/reservations`, 마이 `/me`), `activeCustomerTab(pathname: string): CustomerTabKey \| null` |
| `presentation/CustomerTabBar.tsx` | `CustomerTabBar()` — `<nav className="tabs" aria-label="고객 메뉴">`, 탭마다 `Link`, 현재 탭은 `<b>`로 감싸고 `aria-current="page"`, 나머지는 `<span>`(`OwnerNavItems`와 같은 마크업) |
| `index.ts` | `CUSTOMER_TABS`, `activeCustomerTab`, `type CustomerTabKey`, `CustomerTabBar` |

`aria-label` 「고객 메뉴」는 임시(D-6). 720px 상단 nav는 만들지 않는다: 고객 셸은 PC에서도 420px 프레임이라 컨테이너가 720px에 닿지 않는다(`layout.md` 역할별 셸).

### 2.3 `features/offers` (신규 영역)

**domain** (순수 TypeScript, F6)

| 파일 | export |
| --- | --- |
| `domain/offer.ts` | `type OfferStatus = 'SCHEDULED' \| 'ON_SALE' \| 'SOLD_OUT' \| 'CLOSED' \| 'SUSPENDED'`, `type Offer = { id; productId; storeId; storeName; productName; originalPrice: number; salePrice: number; discountRate: number; initialStock: number; remainingStock: number; isSoldOut: boolean; salesStart: Date; salesEnd: Date; pickupStart: Date; pickupEnd: Date; status: OfferStatus; isActive: boolean }`, `type NearbyOffer = { offer: Offer; distanceKm: number \| null }`, `type OfferPage = { items: NearbyOffer[]; page: number; size: number; total: number }`, `isSoldOut(offer: Offer): boolean` |
| `domain/nearbyQuery.ts` | `type GeoPoint = { lat: number; lng: number }`, `type OfferSort = 'sales_end' \| 'distance' \| 'discount_rate' \| 'price'`, `type RadiusKm = 1 \| 3 \| 5 \| 10`, `type NearbyQuery = { location: GeoPoint \| null; radiusKm: RadiusKm; sort: OfferSort; keyword: string; page: number; size: number }`, `NEARBY_PAGE_SIZE = 20`, `RADIUS_OPTIONS: readonly RadiusKm[] = [1, 3, 5, 10]`, `DEFAULT_RADIUS_KM = 3`, `KEYWORD_MAX_LENGTH = 100` |
| `domain/offerRepository.ts` | `interface OfferRepository { findNearby(query: NearbyQuery, signal?: AbortSignal): Promise<OfferPage> }` (C2 담당이 `findById`를 더한다, §5.4) |
| `domain/offerFormat.ts` | `salesCountdown(salesEnd: Date, now: Date): string \| null`, `pickupWindow(start: Date, end: Date, now: Date): string`, `formatDistance(km: number \| null): string \| null`, `formatWon(n: number): string`, `type OfferCardView = { storeLine; title; rate; salePrice; originalPrice; pickup; countdown: string \| null; remaining: string \| null; soldOut: boolean; ended: boolean }`, `toOfferCardView(item: NearbyOffer, now: Date): OfferCardView` |
| `domain/homeFilter.ts` | `type HomeFilter = { sort: OfferSort; radiusKm: RadiusKm; keyword: string }`, `DEFAULT_HOME_FILTER`, `SORT_OPTIONS: readonly { sort: OfferSort; label: string }[]`, `readHomeFilter(search: string): HomeFilter`, `toHomeSearch(filter: HomeFilter): string`, `isSortAvailable(sort: OfferSort, hasLocation: boolean): boolean`, `effectiveSort(sort: OfferSort, hasLocation: boolean): OfferSort`, `nextRadius(r: RadiusKm): RadiusKm \| null`, `locationChipLabel(hasLocation: boolean, r: RadiusKm): string`, `locationStatusText(hasLocation: boolean): string`, `toNearbyQuery(filter: HomeFilter, location: GeoPoint \| null, page: number): NearbyQuery` |
| `domain/offerMessages.ts` | 문구 상수(§3.1 표) |

**application**

| 파일 | export |
| --- | --- |
| `application/ports.ts` | `interface LocationProvider { current(signal?: AbortSignal): Promise<GeoPoint \| null> }` (유스케이스 전용 기술 기능 = application 포트, `layer-architecture` §6) |
| `application/tokens.ts` | `OfferRepositoryToken = createToken<OfferRepository>('OfferRepository')`, `LocationProviderToken = createToken<LocationProvider>('LocationProvider')` |
| `application/useDeviceLocation.ts` | `type DeviceLocation = { status: 'pending' \| 'ok' \| 'unavailable'; point: GeoPoint \| null; request(): void }`, `useDeviceLocation(): DeviceLocation` |
| `application/useNearbyOffers.ts` | `type NearbyOffersState = { status: 'loading' \| 'success' \| 'empty' \| 'error'; items: NearbyOffer[]; total: number; hasMore: boolean; loadingMore: boolean; loadMoreFailed: boolean; loadMore(): void; retry(): void }`, `useNearbyOffers(filter: HomeFilter, location: GeoPoint \| null, ready: boolean): NearbyOffersState` |

**infrastructure**

| 파일 | export |
| --- | --- |
| `infrastructure/httpOfferRepository.ts` | `class HttpOfferRepository implements OfferRepository` (DTO 타입은 파일 안에서만) |
| `infrastructure/browserLocationProvider.ts` | `class BrowserLocationProvider implements LocationProvider` |

**presentation**

| 파일 | export |
| --- | --- |
| `presentation/OfferCard.tsx` | `OfferCard({ item, now }: { item: NearbyOffer; now: Date })` — `Link className="card"` → `ROUTES.offerDetail(id)` |
| `presentation/OfferCardSkeleton.tsx` | `OfferCardSkeleton()` (E1 542줄 마크업) |
| `presentation/SortChips.tsx` | `SortChips({ value, hasLocation, onChange })` |
| `presentation/LocationSheet.tsx` | `LocationSheet({ hasLocation, locating, radiusKm, onUseCurrentLocation, onApply, onClose })` (C1a) |
| `presentation/NearbyEmpty.tsx` | `NearbyEmpty({ action, onAction }: { action: RadiusKm \| null; onAction(r: RadiusKm): void })` (E1 546줄) |

**`wiring.ts`**: `wireOffers(): Binding[]` → `bind(OfferRepositoryToken, new HttpOfferRepository())`, `bind(LocationProviderToken, new BrowserLocationProvider())`.

**`index.ts`**: `type Offer`, `type OfferStatus`, `type NearbyOffer`, `type OfferPage`, `type GeoPoint`, `type OfferSort`, `type RadiusKm`, `type HomeFilter`, `type OfferRepository`, `type LocationProvider`, `OfferRepositoryToken`, `LocationProviderToken`, `isSoldOut`, `salesCountdown`, `pickupWindow`, `formatDistance`, `formatWon`, `readHomeFilter`, `toHomeSearch`, `nextRadius`, `locationChipLabel`, `useDeviceLocation`, `useNearbyOffers`, `OfferCard`, `OfferCardSkeleton`, `SortChips`, `LocationSheet`, `NearbyEmpty`, 문구 상수 `OFFERS_LOAD_FAILED_MESSAGE`. (구현체·DTO는 내보내지 않음.)

### 2.4 `features/auth` (확장)

| 파일 | 상태 | export |
| --- | --- | --- |
| `domain/points.ts` | 신규 | `type PointType = 'EARN' \| 'USE' \| 'RESTORE' \| 'REVOKE' \| 'GRANT' \| 'EXPIRE'`, `POINT_TYPES`, `type PointLog = { id; amount: number; type: PointType; balanceAfter: number \| null; createdAt: Date }`, `type PointPage = { balance: number; logs: PointLog[]; page: number; size: number; total: number }`, `POINT_PAGE_SIZE = 20`, `RECENT_POINT_COUNT = 3`, `pointTypeLabel(t: PointType): string`, `formatPoint(n: number): string`, `formatPointDelta(n: number): string`, `pointLogMeta(log: PointLog, variant: 'short' \| 'full'): string`, `pointExpiryText(balance: number): string` |
| `domain/accountMessages.ts` | 수정(추가) | `WITHDRAW_PASSWORD_MISMATCH_MESSAGE`, `WITHDRAW_RESERVATIONS_TEXT`(임시), `POINTS_EMPTY_MESSAGE`(임시), `POINTS_LOAD_FAILED_MESSAGE`(임시), `RETRY_LABEL`(임시 「다시 시도」), `withdrawErrorView(e: ErrorLike): FieldError<'password' \| 'form'>` |
| `domain/redirect.ts` | 수정 | `type LoginEntry = 'reservation' \| 'customerTab'`, `LoginLocationState`에 `entry?: LoginEntry` 추가, `readLoginEntry(state: unknown): LoginEntry \| null`, `loginRedirectState(cause, currentPath, entry?: LoginEntry)`(세 번째 인자 추가. 기존 호출 그대로 동작) |
| `domain/loginMessage.ts` | 수정(추가) | `loginEntryMessage(entry: LoginEntry): string` |
| `application/ports.ts` | 수정(추가) | `AccountGateway`에 `findPoints(query: { page: number; size: number }, signal?: AbortSignal): Promise<PointPage>`, `withdraw(password: string, signal?: AbortSignal): Promise<void>` |
| `application/points.ts` | 신규 | `loadPoints(deps: { account: AccountGateway; session: SessionStore }, query: { page: number; size: number }, signal?: AbortSignal): Promise<PointPage>` |
| `application/withdraw.ts` | 신규 | `withdrawAccount(deps: { account: AccountGateway; session: SessionStore }, password: string, signal?: AbortSignal): Promise<void>` |
| `application/usePointHistory.ts` | 신규 | `type PointHistoryState = { status: 'loading' \| 'success' \| 'empty' \| 'error'; balance: number \| null; logs: PointLog[]; total: number; hasMore: boolean; loadingMore: boolean; loadMoreFailed: boolean; loadMore(): void; retry(): void }`, `usePointHistory(pageSize: number): PointHistoryState` |
| `application/useWithdraw.ts` | 신규 | `useWithdraw(): { submit(password: string): Promise<boolean>; pending: boolean; error: ErrorInfo \| null }` (`useSubmit` 사용) |
| `application/authContext.ts` | 수정 | `AuthContextValue`에 `withdraw(password: string, signal?: AbortSignal): Promise<void>` 추가(D-24) |
| `application/useAuthController.ts` | 수정 | `withdraw` 구현 |
| `infrastructure/httpAccountGateway.ts` | 수정 | `findPoints`, `withdraw` 추가 |
| `presentation/PointLogList.tsx` | 신규 | `PointLogList({ logs, variant }: { logs: PointLog[]; variant: 'short' \| 'full' })` — `.list` + 행 |
| `presentation/PointLogSkeleton.tsx` | 신규 | `PointLogSkeleton({ rows }: { rows: number })` |
| `presentation/WithdrawForm.tsx` | 신규 | `WithdrawForm({ balance, cancelTo }: { balance: number; cancelTo: string })` — 본문 box·비밀번호 칸·`.cta`(취소·탈퇴하기) 전체 |
| `presentation/LogoutConfirmSheet.tsx` | 수정 | 설명 한 줄 추가(D-23). props 그대로 |

`index.ts` 추가: `type PointLog`, `type PointType`, `type PointPage`, `type LoginEntry`, `readLoginEntry`, `loginEntryMessage`, `formatPoint`, `pointExpiryText`, `RECENT_POINT_COUNT`, `POINT_PAGE_SIZE`, `POINTS_EMPTY_MESSAGE`, `POINTS_LOAD_FAILED_MESSAGE`, `RETRY_LABEL`, `usePointHistory`, `useWithdraw`, `PointLogList`, `PointLogSkeleton`, `WithdrawForm`. `wiring.ts`는 그대로(새 토큰 없음).

### 2.5 pages·app

| 파일 | export |
| --- | --- |
| `pages/home/presentation/HomePage.tsx`, `pages/home/index.ts` | `HomePage` |
| `pages/my/presentation/MyPage.tsx`, `pages/my/index.ts` | `MyPage` |
| `pages/point-history/presentation/PointHistoryPage.tsx`, `index.ts` | `PointHistoryPage` |
| `pages/withdraw/presentation/WithdrawPage.tsx`, `index.ts` | `WithdrawPage` |
| `app/layouts/CustomerFrame.tsx` | `CustomerFrame({ children })` — `<div data-shell="customer" style={{ maxWidth: 420, marginInline: 'auto', minHeight: '100dvh', display: 'flex', flexDirection: 'column', borderInline: '1px solid var(--line)' }}>`. 토큰 변수만 씀(F12) |
| `app/layouts/CustomerLayout.tsx` | `CustomerLayout({ access }: { access: 'public' \| 'customer' })` |
| `app/router/placeholders.tsx` | `HomePlaceholder` 삭제, `OfferDetailPlaceholder`(C2), `ReservationsPlaceholder`(C5) 추가 |
| `app/container.ts` | `wireOffers()` 한 줄 추가 |

## 3. 동작 규칙

### 3.1 domain

**`shared/lib/format.ts`**: `groupDigits(1240) = '1,240'`, `(-500) = '-500'`, `(1000000) = '1,000,000'`, `(0) = '0'`. `formatHm`은 두 자리 0 채움(`'09:05'`). 로컬 시각 기준(D-13).

**`salesCountdown(salesEnd, now)`** (`content.md` "판매 마감 N분 전 / N시간 N분 전", `states.md` 화면 계산 값)
- `diff = salesEnd − now`(ms). `diff <= 0` → `null`(판매 종료).
- `m = ceil(diff / 60000)`(30초 남음 → 1분. 「0분 전」을 만들지 않음).
- `m < 60` → `판매 마감 ${m}분 전`. 그 외 `h = floor(m/60)`, `r = m % 60`: `r === 0` → `판매 마감 ${h}시간 전`, 아니면 `판매 마감 ${h}시간 ${r}분 전`. 24시간 이상도 시간으로 셈(`25시간 3분 전`). 정각 표기·1분 미만 올림·24시간 이상은 임시(D-13, Q-9).

**`pickupWindow(start, end, now)`**: 날짜 표시 = `isSameLocalDate(start, now)` → `오늘`, 다음 날 → `내일`, 그 외 `formatMd(start)`. 결과 `${날짜} ${formatHm(start)}–${formatHm(end)}`(en dash U+2013, `content.md`). 화면은 앞에 「픽업 」을 붙인다.

**`formatDistance(km)`**: `null` → `null`(위치 없음 → 거리 숨김). `v = Math.round(km * 10) / 10`, `v < 0.1`이면 0.1. 결과 `${v.toFixed(1)}km`(`0.42 → '0.4km'`, `2.3 → '2.3km'`, `0.03 → '0.1km'`, `12 → '12.0km'`). 0.05km 미만 처리는 임시(Q-10).

**`formatWon(n)`**: `${groupDigits(n)}원`. 정가는 `groupDigits(originalPrice)`(「원」 없이 취소선, `content.md`).

**`isSoldOut(offer)`**: `offer.isSoldOut || offer.status === 'SOLD_OUT' || offer.remainingStock <= 0`.

**`toOfferCardView(item, now)`** (`OfferCard` README 정보 순서)
- `storeLine`: 거리 문자열이 있으면 `${storeName} · ${거리}`, 없으면 `storeName`.
- `title` = `productName`, `rate` = `${discountRate}%`(서버 값 그대로, catalog "확인 필요" 계산식은 서버 몫), `salePrice` = `formatWon(salePrice)`, `originalPrice` = `groupDigits(originalPrice)`, `pickup` = `pickupWindow(…)`.
- `soldOut = isSoldOut(offer)`. 품절이면 `countdown = null`, `remaining = null`.
- 품절이 아니면 `countdown = salesCountdown(salesEnd, now)`, `remaining = 남은 ${remainingStock}개`, `ended = countdown === null`.

**`homeFilter.ts`**
- `SORT_OPTIONS` = `[{sales_end, '마감 임박'}, {distance, '가까운 순'}, {discount_rate, '할인율'}, {price, '낮은 가격'}]`(와이어프레임 306줄 순서, API `sort` 값과 1:1, catalog §8 정렬 방향).
- `DEFAULT_HOME_FILTER = { sort: 'sales_end', radiusKm: 3, keyword: '' }`.
- `readHomeFilter(search)`: `URLSearchParams`에서 `sort`(목록에 없으면 기본), `radius`(`Number`가 `RADIUS_OPTIONS`에 없으면 3), `q`(`trim()` 뒤 앞 100자). 모르는 키는 무시.
- `toHomeSearch(filter)`: 기본값과 다른 것만 `sort`·`radius`·`q` 순서로. 모두 기본이면 `''`, 아니면 `'?…'`.
- `isSortAvailable(sort, hasLocation)`: `sort !== 'distance' || hasLocation`. `effectiveSort`: 쓸 수 없으면 `'sales_end'`(400 「distance 정렬은 위치 정보가 필요합니다.」를 미리 막음).
- `nextRadius`: 1→3, 3→5, 5→10, 10→`null`.
- `locationChipLabel(true, r)` = `현재 위치 · ${r}km`, `(false, _)` = `전체 지역`. `locationStatusText(true)` = `지금: 현재 위치`, `(false)` = `지금: 전체 지역`. 지역 이름(「망원동」)은 주소 변환이 없어 쓰지 않는다(임시, C-2, D-16).
- `toNearbyQuery(filter, location, page)`: `{ location, radiusKm, sort: effectiveSort(filter.sort, location !== null), keyword: filter.keyword, page, size: NEARBY_PAGE_SIZE }`.

**문구 상수(`offerMessages.ts`)**

| 상수 | 값 | 정본 |
| --- | --- | --- |
| `NEARBY_EMPTY_TITLE` | `근처에 마감 할인이 없어요` | `wireframe.html:546` |
| `NEARBY_EMPTY_HINT` | `반경을 넓히거나 저녁 시간에 다시 확인해 보세요.` | `wireframe.html:546` |
| `widenRadiusLabel(r)` | `반경 ${r}km로 넓히기` | `wireframe.html:546`(5km 예시를 반경 값으로) |
| `LOCATION_SHEET_TITLE` | `어디서 찾을까요?` | `wireframe.html:332` |
| `USE_CURRENT_LOCATION_LABEL` | `◎ 현재 위치 사용` | `screens.md` C1a |
| `LOCATION_DENIED_HINT` | `위치를 허용하지 않으면 거리 없이 전체 할인을 보여 줘요.` | `wireframe.html:337` |
| `OWNER_APPLY_LINK` | `사장님이신가요? 입점 신청` | `wireframe.html:320` |
| `OFFERS_LOAD_FAILED_MESSAGE` | `불러오지 못했어요. 잠시 후 다시 시도해 주세요.` | **임시**(`auth.md` D-9 문구 재사용) |
| `LOAD_MORE_LABEL` | `더 보기` | `wireframe.html:530`(C11과 같은 말) |
| `SEARCH_LABEL` | `상품명 검색` | `wireframe.html:305` |
| `SORT_GROUP_LABEL` | `정렬` | **임시**(칩 묶음의 접근 이름) |

**`points.ts`** (`states.md` 포인트 내역 종류, `content.md` 포인트·날짜 표기)
- `pointTypeLabel`: EARN 적립 / USE 사용 / RESTORE 복구 / REVOKE 회수 / GRANT 지급 / EXPIRE 소멸.
- `formatPoint(n)` = `${groupDigits(n)}P`. `formatPointDelta(n)`: `n > 0` → `+${groupDigits(n)}P`, `n < 0` → `−${groupDigits(-n)}P`(U+2212, 와이어프레임·`content.md`의 「−」), `0` → `0P`.
- `pointLogMeta(log, 'short')` = `formatMd(createdAt)`(C6, 와이어프레임 490줄의 날짜). `'full'` = `${MM/DD} ${HH:mm} · 잔액 ${formatPoint(balanceAfter)}`, `balanceAfter === null`이면 `${MM/DD} ${HH:mm}`(C11 메모 "잔액이 없는 옛 내역은 잔액 생략"). 와이어프레임의 사유(「결제」·「환불로 적립 취소」·「이벤트 보상」)는 API에 없어 쓰지 않는다(C-5).
- `pointExpiryText(balance)` = `${formatPoint(balance)} 소멸`(와이어프레임 508줄).

**`accountMessages.ts` 추가**

| 상수·함수 | 값·규칙 | 정본 |
| --- | --- | --- |
| `WITHDRAW_PASSWORD_MISMATCH_MESSAGE` | `비밀번호가 일치하지 않습니다.` | `screens.md` C7(서버 문구 `현재 비밀번호가 올바르지 않습니다.`와 다름, C9와도 다름) |
| `WITHDRAW_RESERVATIONS_TEXT` | `모두 취소·환불` | **임시**(와이어프레임 「1건 취소·환불」의 건수를 알 수 없음, C-6) |
| `POINTS_EMPTY_MESSAGE` | `포인트 내역이 없어요` | **임시**(C6·C11 빈 상태 문구 없음) |
| `POINTS_LOAD_FAILED_MESSAGE` | `불러오지 못했어요. 잠시 후 다시 시도해 주세요.` | **임시** |
| `RETRY_LABEL` | `다시 시도` | **임시**(`auth.md` D-9) |
| `withdrawErrorView(e)` | `CURRENT_PASSWORD_MISMATCH` → `{ field: 'password', message: WITHDRAW_PASSWORD_MISMATCH_MESSAGE }` / 그 외 → `{ field: 'form', message: accountErrorMessage(e) }`(서버 문구, `content.md` 계정·보안 합니다체) | D-24 |

**`redirect.ts`·`loginMessage.ts` 추가** (A1 진입 안내, `wireframe.html:170`·`screens.md` A1 동작 메모)
- `readLoginEntry(state)`: `{ entry: 'reservation' | 'customerTab' }`이면 그 값, 아니면 `null`.
- `loginRedirectState(cause, path, entry)`: `cause === 'loggedOut'`이면 `undefined`(기존), 아니면 `entry`가 있을 때 `{ from: path, entry }`, 없으면 `{ from: path }`.
- `loginEntryMessage('reservation')` = `예약을 이어가려면 로그인하세요.`(와이어프레임 170줄 원문), `('customerTab')` = `예약 내역을 보려면 로그인하세요.`(**임시**: 정본은 「예약 내역을 보려면…」까지만, C-7).

**`activeCustomerTab(pathname)`**: 끝 `/` 제거·소문자로 비교(`activeOwnerTab`과 같은 방식). `'/'` → `home`, `/reservations`·`/reservations/…` → `reservations`, `/me`·`/me/…` → `me`, 그 외(`/offers/1`, `/login`) → `null`.

### 3.2 application

**`useDeviceLocation()`** (D-9)
- 마운트 때 한 번 `LocationProvider.current(signal)`. 그동안 `status: 'pending'`. 결과가 좌표면 `ok`, `null`이면 `unavailable`. 언마운트 시 abort, 그 뒤 상태를 바꾸지 않는다(F10).
- `request()`: `pending`으로 바꾸고 다시 요청(C1a 「◎ 현재 위치 사용」). 진행 중이면 무시.

**`useNearbyOffers(filter, location, ready)`**
- `ready === false`(위치 확인 중)면 요청하지 않고 `status: 'loading'`.
- `ready`가 되거나 `filter`(sort·radiusKm·keyword)·`location`이 바뀌면 진행 중 요청을 abort하고 `toNearbyQuery(filter, location, 1)`로 첫 페이지를 새로 받는다(목록 초기화). 결과 0건 → `empty`, 그 외 `success`. 실패 → `error`(abort 오류는 무시).
- `hasMore = items.length < total`. `loadMore()`: `hasMore`이고 진행 중이 아니면 다음 페이지를 받아 **이어 붙인다**. 실패하면 목록은 그대로, `loadMoreFailed = true`. 같은 id가 다시 오면(목록 변동) 뒤에 온 것을 버린다.
- `retry()`: 첫 페이지 다시.

**`loadPoints(deps, query, signal)`**: `account.findPoints(query, signal)`. 오류 `status === 401`이면 `session.clear()` 후 같은 오류 throw(`auth-account.md` D-18과 같은 방식). 그 외 그대로 throw.

**`withdrawAccount(deps, password, signal)`**: `account.withdraw(password, signal)` 성공 → `session.clear()`. 401 → `session.clear()` 후 throw. 그 외(400·403·500) → `clear` 없이 throw.

**`usePointHistory(pageSize)`**: 마운트 때 `loadPoints({ page: 0, size: pageSize })`. `balance = users_point`, 0건 → `empty`(잔액은 있음). `hasMore = logs.length < total`. `loadMore()`는 `page + 1`을 이어 붙임(`useNearbyOffers`와 같은 규칙). 401은 유스케이스가 세션을 지워 가드가 A1로 보낸다. 언마운트 abort.

**`AuthContextValue.withdraw(password, signal)`** (`useAuthController`)
- `loggingOut` ref를 켜고(구독이 `anonymous other`로 바꾸지 않게) `withdrawAccount({ account, session }, password, signal)`.
- 성공 → `setState({ status: 'anonymous', cause: 'loggedOut' })`(로그아웃과 같은 상태, C7 → C1, D-24).
- 실패 → 세션이 지워졌으면(`!session.hasSession()`, 401) `setState({ anonymous, cause: 'other' })` 후 throw, 아니면 상태 그대로 throw. `finally`에서 ref 끔.

**`useWithdraw()`**: `useSubmit((password, signal) => withdraw(password, signal))`. `submit` 성공 `true`, 실패 `false`(+`error`).

### 3.3 infrastructure

| 메서드 | 엔드포인트 | 요청 | 응답 → domain |
| --- | --- | --- | --- |
| `HttpOfferRepository.findNearby` | `GET /v1/offers` (`auth: false`) | 쿼리: `location`이 있으면 `lat`·`lng`·`radius_km`, `keyword.trim() !== ''`이면 `keyword`, 항상 `sort`·`page`·`size`. `status`는 보내지 않음(기본 `ON_SALE`) | `items[].offer` → `Offer`(snake → camel, 날짜 `new Date`, `status`가 5개 밖이면 throw), `items[].distance` → `distanceKm`, `page`·`size`·`total` 그대로. `unit`은 버림(항상 `km`) |
| `BrowserLocationProvider.current` | `navigator.geolocation.getCurrentPosition` | `{ enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 }` | 성공 `{ lat: coords.latitude, lng: coords.longitude }`. 오류·`navigator.geolocation` 없음·abort → `null`(throw 안 함) |
| `HttpAccountGateway.findPoints` | `GET /v1/users/me/points?page=&size=` | 토큰 붙임 | `users_point` → `balance`, `logs[]` → `PointLog`(`point_type` → `type`, 모르는 값이면 throw, `balance_after` null 유지), `total_elements` → `total` |
| `HttpAccountGateway.withdraw` | `POST /v1/users/me/withdraw` | `{ password }`(trim 안 함) | 200 `WithdrawalResponse` → 쓰지 않음(`void`) |

- 모두 `shared/api` `request<T>`(F8), `signal` 전달.
- 공개 API에 `auth: false`(D-19): 남은 만료 토큰이 공개 목록 요청을 막지 않게 한다.
- `page`: 할인 목록은 1부터·`total`, 포인트는 0부터·`total_elements`(백엔드 기준. reference "확인 필요"는 C-10).

### 3.4 고객 셸·가드

**`CustomerLayout({ access })`**
- 공통: `CustomerFrame` 안에 `<div className="app" style={{ flex: 1 }}>` + `<Outlet />` + (매치된 라우트 중 `isTabBarHandle(handle)`이 있으면) `<CustomerTabBar />`. 탭 유무 판정은 `OwnerLayout`과 같은 `useMatches()` 방식(`app/router/handle.ts` 재사용).
- `access === 'public'`: 가드 없음. 세션 확인 중에도 바로 그린다(C1은 비로그인 화면, `screens.md` C1).
- `access === 'customer'`: `decideAccess(useAuth().state, 'CUSTOMER')`, 그리고 `wasAllowed` ref(이 레이아웃 인스턴스가 한 번이라도 `allow`를 그렸는지).

| decision | 렌더 |
| --- | --- |
| `loading` | 프레임 + `<div className="app" aria-busy="true" />` |
| `allow` | 프레임 + `.app` + Outlet + 탭(handle). `wasAllowed = true` |
| `login` | `<Navigate to={ROUTES.login} replace state={loginRedirectState('other', pathname+search+hash, 'customerTab')} />` |
| `login-without-from` 이고 `wasAllowed` | `<Navigate to={ROUTES.home} replace />` — 이 화면에서 방금 로그아웃·탈퇴(C10·C7 → C1) |
| `login-without-from` 이고 `!wasAllowed` | `login`과 같음(로그아웃한 뒤 나중에 내 예약·마이 탭을 누른 경우. 누른 탭으로 돌아와야 함, `screens.md` C1) |
| `home` (상점주·관리자) | `<Navigate to={ROUTES.home} replace />`(기존 `decideAccess` 규칙) |
| `error` | `AccountLayout`과 같은 `err` + 「다시 시도」 |

- 비로그인 고객이 탭 바의 「내 예약」·「마이」를 누르면 일반 링크 이동 → 이 가드가 A1로 보낸다. 탭 바는 로그인 여부를 따지지 않는다(D-6).

**`AccountLayout` 수정**: `allow`이고 `state.user.role === 'CUSTOMER'`이면 `<CustomerFrame><Outlet /></CustomerFrame>`, 그 외 기존대로 `<Outlet />`. M-6 TODO 삭제(C8·C9를 고객 셸 420px 규칙에 맞춤).

### 3.5 C1 홈 · C1a 위치·반경 (`pages/home/presentation/HomePage.tsx`)

- `filter = readHomeFilter(location.search)`, `device = useDeviceLocation()`, `hasLocation = device.status === 'ok'`, `offers = useNearbyOffers(filter, device.point, device.status !== 'pending')`, `now = useNow()`, `auth = useAuth().state`, `sheetOpen` 상태.
- 필터 변경은 `navigate({ search: toHomeSearch(next) }, { replace: true })`(D-10).
- 마크업(와이어프레임 300~322줄 순서)
  - `.bar`: `<h1 className="logo">마감직전</h1>`(D-27) / `<button type="button" className={sheetOpen ? 'chip on' : 'chip'} aria-haspopup="dialog" aria-expanded={sheetOpen}>{locationChipLabel(hasLocation, filter.radiusKm)}</button>` / `.sp` / `auth.status === 'anonymous'`일 때만 `<Link className="link" to={ROUTES.login} state={{ from: pathname + search }}>로그인</Link>`(entry 없음 → A1 안내 줄 없음, `screens.md` A1).
  - 시트가 닫혀 있으면 `.body`:
    - `<form role="search">` 안 `<input className="in" type="search" aria-label="상품명 검색" placeholder="상품명 검색" maxLength={100} defaultValue={filter.keyword}>`. 제출(Enter) → `keyword` 바꿈. 지운 뒤 제출하면 검색 해제.
    - `SortChips`: `<div className="scroll" role="group" aria-label="정렬">`, 칩마다 `<button className={on ? 'chip on' : 'chip'} aria-pressed={on}>`. 선택 표시는 `effectiveSort(filter.sort, hasLocation)` 기준. 「가까운 순」은 `!hasLocation`이면 `aria-disabled="true"`, 눌러도 무시.
    - 목록(`<div aria-busy={loading}>`): `loading` → `OfferCardSkeleton` 3개 / `error` → `<div className="warn" role="alert">{OFFERS_LOAD_FAILED_MESSAGE}</div>` + `<button className="btn sm">다시 시도</button>` / `empty` → `NearbyEmpty action={hasLocation ? nextRadius(filter.radiusKm) : null}` / `success` → `OfferCard` 목록.
    - `hasMore`이면 `<button type="button" className="link">더 보기</button>`(처리 중 「처리 중…」 + `aria-disabled`). `loadMoreFailed`이면 그 위에 `warn` 한 줄.
  - 시트가 열려 있으면 `.body` 대신 `<div className="dim" onClick={바깥이면 닫기}>` 안 `LocationSheet`.
  - `auth.status !== 'authenticated'`일 때 `.body`(또는 `.dim`) 다음, 탭 바 바로 위에 `<Link className="link" style={{ padding: 'var(--s2)' }} to={ROUTES.ownerSignup}>사장님이신가요? 입점 신청</Link>`(와이어프레임 320줄. 목록 끝이 아니라 고정 위치, `screens.md` C1, D-18).
- `OfferCard`(와이어프레임 307~318줄): `<Link className="card" to={ROUTES.offerDetail(id)} state={{ from: pathname + search }}>` > `<div className="ph" aria-hidden="true" />`(이미지 없음, C-4) + 정보 열: `.m` storeLine / `.t` title / `.price`(`span.pct` rate, `b` salePrice, `s` originalPrice) / `.m` 「픽업 」+ (품절 아니면 `<b>`) pickup / `.row`: 품절이면 `<span className="tag mute">품절</span>`, `ended`면 `<span className="tag mute">판매 종료</span>`(임시, `states.md` 할인 문구), 그 외 `<span className="cd">{countdown}</span><span className="m">{remaining}</span>`.
- `NearbyEmpty`(E1 546줄): `<div className="box empty"><div className="ic" /><b>근처에 마감 할인이 없어요</b><span className="m">반경을 넓히거나 저녁 시간에 다시 확인해 보세요.</span>{action !== null ? <button className="btn sm">반경 {action}km로 넓히기</button> : null}</div>`. 버튼 → `radiusKm = action`.
- `LocationSheet`(와이어프레임 331~339줄): `<div className="sheet" role="dialog" aria-modal="true" aria-labelledby>` > `.t`(17px) 「어디서 찾을까요?」 / `btn` 「◎ 현재 위치 사용」(`locating`이면 「처리 중…」·`aria-disabled`) / `.m` `locationStatusText(hasLocation)` / `.lbl` 「반경」 / `.scroll` 칩 1·3·5·10km(`aria-pressed`, 시트 안 선택값, 처음은 `radiusKm`) / `.m` 「위치를 허용하지 않으면 거리 없이 전체 할인을 보여 줘요.」 / `btn pri` 「적용」 → `onApply(선택값)` 후 닫힘. `useModalFocus`(첫 포커스 「◎ 현재 위치 사용」, Escape·바깥 누름 → 적용 없이 닫힘). 닫으면 위치 칩으로 포커스.
- 상태 표

| 상태 | 표시 |
| --- | --- |
| 위치 확인 중 | 칩 「전체 지역」, 목록 Skeleton 3개(요청 없음) |
| 위치 허용 | 칩 `현재 위치 · 3km`, 카드에 거리, 「가까운 순」 사용 가능 |
| 위치 거부·실패·8초 초과 | 칩 「전체 지역」, 거리 숨김, 「가까운 순」 비활성, 반경 무시(위치 없이 요청) |
| 로딩 | Skeleton 3개, `aria-busy="true"` |
| 성공 | 카드 목록, 남은 게 있으면 「더 보기」 |
| 빈 결과 | EmptyState(위치 있고 10km 미만일 때만 넓히기 버튼, C-8) |
| 오류(네트워크·400) | `warn` 임시 문구 + 「다시 시도」 |
| 비로그인 | 상단 「로그인」, 하단 「입점 신청」 |
| 고객 로그인 | 둘 다 없음 |
| 카드 누름 | `/offers/:offerId`(C2 자리 page) |

### 3.6 C6 마이 · C10 로그아웃 · C11 · C7

**C6 `pages/my/presentation/MyPage.tsx`** (와이어프레임 477~499줄, 가드 안이라 `user` 보장)
- `points = usePointHistory(RECENT_POINT_COUNT)`, `logoutOpen` 상태.
- `.bar`: `<h1 className="logo">마이</h1>` + `.sp`.
- 시트가 닫혀 있으면 `.body`:
  - `.box`: `.t` `user.name ?? user.email` / `.m` `user.email` / `.kv` 「포인트」 + `<b>{formatPoint(points.balance ?? user.point)}</b>`(D-22).
  - `.list`: `<Link className="li" to={ROUTES.accountProfile} state={{ from: ROUTES.me }}>프로필 변경 <span className="m">›</span></Link>`, 같은 모양 「비밀번호 변경」(`accountPassword`), `<button className="li">로그아웃 <span className="m">›</span></button>` → `logoutOpen = true`. (와이어프레임의 「C8 ›」 화면 번호는 설계 표기, `content.md` 버튼·링크.)
  - `.row`: `<span className="lbl" style={{ flex: 1 }}>최근 포인트 내역</span>` + `<Link className="link" to={ROUTES.mePoints}>전체 보기</Link>`.
  - 최근 내역: 로딩 `PointLogSkeleton rows=3` / 오류 `warn` + 「다시 시도」 / 빈 `.m` `포인트 내역이 없어요` / 성공 `PointLogList variant="short"`.
  - `<Link className="link" to={ROUTES.meWithdraw}>회원 탈퇴</Link>`(맨 아래 조용한 링크, `ListRow` README).
- 시트가 열려 있으면 `.body` 대신 `.dim` + `LogoutConfirmSheet onClose={() => setLogoutOpen(false)}`. 바깥 누름·Escape → 닫힘(`useModalFocus`는 page가 `.dim`에 건다). 로그아웃 성공 → 인증 상태 `loggedOut` → `CustomerLayout`이 C1로(§3.4).
- C8·C9 ← 는 `state.from = '/me'`라 `resolvePostLoginPath(CUSTOMER, '/me') = '/me'`로 C6에 돌아온다(기존 규칙 그대로).

**C10 `LogoutConfirmSheet` 수정** (와이어프레임 260~263줄): 제목 다음에 `<div className="m">진행 중인 예약은 그대로 남아요. 다시 로그인하면 볼 수 있어요.</div>`. 역할과 관계없이 넣는다(C10은 공용 화면, D-23). `aria-describedby`로 연결.

**`PointLogList`** (`ListRow` README 포인트 내역): `<div className="list">` > 행마다 `<div className="li"><div><b>{pointTypeLabel}</b><div className="m">{pointLogMeta(log, variant)}</div></div><b>{formatPointDelta(amount)}</b></div>`.

**C11 `pages/point-history/presentation/PointHistoryPage.tsx`** (와이어프레임 517~534줄)
- `points = usePointHistory(POINT_PAGE_SIZE)`.
- `.bar`: `<Link to={ROUTES.me} aria-label={BACK_LABEL}>←</Link>` + `<h1 className="t">포인트</h1>` + `.sp`(탭 바 없음: 하위 화면).
- `.body`: `<div className="box" style={{ background: 'var(--fill)' }}>` > `.lbl` 「보유 포인트」 + `<b style={{ fontSize: 22 }}>{formatPoint(balance ?? user.point)}</b>` + `.m` 「결제 금액의 1% 적립 · 100P 단위로 사용」 / 목록 `PointLogList variant="full"` / `hasMore`이면 `<button className="link">더 보기</button>`.

| 상태 | 표시 |
| --- | --- |
| 로딩 | 잔액 칸은 `user.point`, 목록 `PointLogSkeleton rows=5` |
| 성공 | 최신순 20개, `logs.length < total`이면 「더 보기」 |
| 더 보기 중 | 「처리 중…」 + `aria-disabled` |
| 더 보기 실패 | 목록 유지 + `warn` 한 줄, 버튼 그대로 |
| 빈 | `box empty`: `.ic` + `<b>포인트 내역이 없어요</b>` + `<Link className="btn sm" to={ROUTES.home}>할인 보러 가기</Link>`(E1 547줄 버튼 문구) |
| 오류 | `warn` + 「다시 시도」 |
| 401 | 세션 정리 → 가드가 `/login`(`from: /me/points`, entry `customerTab`) |

**C7 `pages/withdraw/presentation/WithdrawPage.tsx`** (와이어프레임 501~515줄)
- `points = usePointHistory(1)`(잔액만 씀). `.bar`: ← `ROUTES.me` + `<h1 className="t">회원 탈퇴</h1>`.
- `WithdrawForm balance={points.balance ?? user.point} cancelTo={ROUTES.me}`:
  - `<form noValidate style={{ display: 'contents' }}>` > `.body`: `.box` > `.t` 「탈퇴하면 이렇게 돼요」 / `.kv` 「진행 중 예약」 + `<b>모두 취소·환불</b>`(임시, C-6) / `.kv` 「남은 포인트」 + `<b className="cd">{pointExpiryText(balance)}</b>` / `.m` 「되돌릴 수 없어요.」. 이어서 `label.lbl` 「현재 비밀번호 *」 + `input.in`(`type="password"`, `autoComplete="current-password"`, `maxLength=128`) + 칸 아래 `err`(password 오류) + 폼 오류 `err`.
  - `.cta`: `<Link className="btn" to={cancelTo}>취소</Link>` + `<button type="submit" className="btn dark">탈퇴하기</button>`(비밀번호가 `''`이면 `aria-disabled`, 처리 중 「처리 중…」·연타 무시). 고객 셸은 420px라 `.dk` 두 벌은 두지 않는다(D-5).
- 성공 → 인증 상태 `loggedOut` → 가드가 C1로. 안내 문구 없음(C-15).

| 상태 | 표시 |
| --- | --- |
| 처음 | 잔액(불러오기 전 `user.point`), 「탈퇴하기」 비활성 |
| 400 `CURRENT_PASSWORD_MISMATCH` | 비밀번호 칸 아래 `비밀번호가 일치하지 않습니다.`, 입력 유지 |
| 400 `VALIDATION_ERROR`·403·500 `DATA_INCONSISTENT`·네트워크 | 폼 오류 자리에 `accountErrorMessage`(서버 문구) |
| 401 | 세션 정리 → `/login`(`from: /me/withdraw`) |
| 200 | 세션 정리, C1로 `replace` |

### 3.7 기존 화면 누락 보완 (와이어프레임 대조 결과)

| 화면 | 보완 | 위치 |
| --- | --- | --- |
| A1 | 진입 경로별 안내 한 줄(`wireframe.html:170`): `readLoginEntry(location.state)`가 있으면 `<h1>로그인</h1>` 바로 아래 `<div className="m">{loginEntryMessage(entry)}</div>`. 고객 가드는 `customerTab`, C2는 `reservation`(§5.6), 홈 상단 링크는 없음 | `pages/login/presentation/LoginPage.tsx`(TODO 삭제) |
| C10 | 설명 한 줄(`wireframe.html:261`) | `features/auth/presentation/LogoutConfirmSheet.tsx` |
| C10 | 고객 진입(C6 → C10 → C1, `wireframe.html:268` 메모) | §3.6, §3.4 |
| C8·C9 | 고객으로 열면 고객 셸 프레임(420px) 안(M-6 해소) | `app/layouts/AccountLayout.tsx` |
| C8 | 「상호 변경은 고객센터에 문의해 주세요.」(`wireframe.html:230`) — **보완하지 않음**(`auth-account.md` D-22 확정 유지) | — |
| A2 | 「C2에서 왔으면 같은 수량으로 예약 이어가기」(`wireframe.html:201`) — C2 담당 몫. `from`에 수량 쿼리를 넣는 방법을 §5.6에 안내 | — |
| O8 | PC 드롭다운(`wireframe.html:292`) — 기존 TODO 유지(`auth.md` D-3) | — |

## 4. 라우트

| 화면 | 경로 | 레이아웃 | 접근 | 탭 바 |
| --- | --- | --- | --- | --- |
| C1 (+C1a 시트) | `/` | `CustomerLayout access="public"` | 공개 | 있음(`TAB_BAR_HANDLE`) |
| C2 (자리 page) | `/offers/:offerId` | `CustomerLayout access="public"` | 공개 | 없음 |
| C5 (자리 page) | `/reservations` | `CustomerLayout access="customer"` | CUSTOMER | 있음 |
| C6 (+C10 시트) | `/me` | `CustomerLayout access="customer"` | CUSTOMER | 있음 |
| C11 | `/me/points` | `CustomerLayout access="customer"` | CUSTOMER | 없음 |
| C7 | `/me/withdraw` | `CustomerLayout access="customer"` | CUSTOMER | 없음 |

`routes.tsx` 최종 모양(골격 단계에서 이대로 만든다):

```tsx
export const routes: RouteObject[] = [
  {
    element: <CustomerLayout access="public" />,
    children: [
      { path: ROUTES.home, element: <HomePage />, handle: TAB_BAR_HANDLE },
      // C2: catalog 담당이 <OfferDetailPage />로 바꾼다(customer-home.md §5.3)
      { path: ROUTE_PATTERNS.offerDetail, element: <OfferDetailPlaceholder /> },
    ],
  },
  { path: ROUTES.login, element: <LoginPage /> },
  { path: ROUTES.signup, element: <SignupPage /> },
  { path: ROUTES.passwordReset, element: <PasswordResetPage /> },
  { path: ROUTES.account, element: <Navigate to={ROUTES.accountProfile} replace /> },
  { element: <AccountLayout />, children: [/* 기존 C8·C9 */] },
  {
    element: <CustomerLayout access="customer" />,
    children: [
      // C5: reservations 담당이 <ReservationsPage />로 바꾼다(customer-home.md §5.3)
      { path: ROUTES.reservations, element: <ReservationsPlaceholder />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.me, element: <MyPage />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.mePoints, element: <PointHistoryPage /> },
      { path: ROUTES.meWithdraw, element: <WithdrawPage /> },
      // 탭 바 없는 고객 전용 화면(결제 C3·C4, 예약 하위 화면)은 여기에 handle 없이 한 줄씩(customer-home.md §5.5)
    ],
  },
  { path: ROUTES.owner, element: <Navigate to={ROUTES.ownerToday} replace /> },
  { element: <OwnerLayout />, children: [/* 기존 */] },
  { path: '*', element: <Navigate to={ROUTES.home} replace /> },
];
```

자리 page(`placeholders.tsx`, `app-shell.md` D-15 방식 — 화면 ID 표시, 개발용 임시값):
- `OfferDetailPlaceholder`: `<div className="bar"><Link to={ROUTES.home} aria-label="뒤로">←</Link><h1 className="t">C2 할인 상세</h1><span className="sp" /></div><div className="body"><p>{offerId}</p></div>`
- `ReservationsPlaceholder`: `<div className="bar"><h1 className="logo">C5 내 예약</h1><span className="sp" /></div><div className="body" />`
- 두 자리 page 모두 `.app`은 `CustomerLayout`이 그린다(자리 page는 `.bar`·`.body`만).

## 5. 연결 안내 (catalog·reservations·payments 담당용)

### 5.1 경로 상수 규칙 (`shared/lib/routes.ts`)
- 경로 문자열은 이 파일의 `ROUTES`에만 쓴다. 코드에서 `'/offers/' + id`처럼 직접 만들지 않는다(`app-shell.md` D-17).
- 고정 경로는 문자열(`reservations: '/reservations'`), 매개변수 경로는 함수(`offerDetail: (id) => \`/offers/${encodeURIComponent(id)}\``)로 `ROUTES`에, 라우터 등록용 패턴은 `ROUTE_PATTERNS`(`offerDetail: '/offers/:offerId'`)에 같은 키로 둔다.
- 이미 정한 키(바꾸지 않음): `home`, `offerDetail`, `reservations`, `me`, `mePoints`, `meWithdraw`. 새 키는 추가만 한다(예: `reservationDetail`, `payment`). 키 추가는 자기 발주서에 적힌 담당이 한다.

### 5.2 고객 가드 — 라우트를 어디에 넣는가
- 가드는 경로 접두어가 아니라 **어느 레이아웃의 children에 넣었는가**로 정해진다. `/reservations/*`·`/me/*`·결제 화면은 `routes.tsx`의 `<CustomerLayout access="customer" />` children에 넣는다. 그러면 비로그인 → `/login`(`from` = 그 경로 + 쿼리, A1 안내 「예약 내역을 보려면…」), 상점주·관리자 → `/`가 자동으로 된다. 페이지 안에서 가드를 다시 쓰지 않는다.
- 공개 화면(C2)은 `<CustomerLayout access="public" />` children에 넣는다.
- 가드 안 page에서 사용자: `const { state } = useAuth(); const user = state.status === 'authenticated' ? state.user : null;`(가드 안이면 항상 `authenticated`).

### 5.3 자리표시자를 자기 page로 바꾸는 한 줄
- C2: `routes.tsx`의 `{ path: ROUTE_PATTERNS.offerDetail, element: <OfferDetailPlaceholder /> }`에서 `element`만 `<OfferDetailPage />`로 바꾸고 import 한 줄을 더한다. 이어서 `placeholders.tsx`의 `OfferDetailPlaceholder`를 지우고 파일 맨 위 TODO의 `언제:`에서 「C2 구현 시」를 지운다.
- C5: 같은 방식으로 `{ path: ROUTES.reservations, element: <ReservationsPlaceholder />, handle: TAB_BAR_HANDLE }`의 `element`만 바꾼다. **`handle: TAB_BAR_HANDLE`은 남긴다**(탭 화면).
- page 컴포넌트는 `.app`을 그리지 않는다. `.bar` + `.body`(+`.cta`)만 그린다(`.app`·프레임·탭 바는 `CustomerLayout`).

### 5.4 할인 데이터(C2)
- `features/offers`는 이 문서가 만든다. C2 담당은 같은 영역에 파일을 **더한다**: `OfferRepository`에 `findById(id, signal?)` 추가, `HttpOfferRepository`에 구현, `application/useOfferDetail.ts`, presentation 부품, `index.ts`에 export 추가. `wiring.ts`는 이미 `OfferRepositoryToken`을 등록하므로 바꾸지 않는다.
- 카드 표기 규칙은 다시 만들지 않고 `salesCountdown`, `pickupWindow`, `formatWon`, `isSoldOut`(공개 API)을 쓴다. C2의 「취소 가능 오늘 17:00까지」 계산은 C2 설계 몫.
- 카드 링크는 `state={{ from: '/?sort=…' }}`(홈 경로 + 쿼리)를 넘긴다. C2 ←는 `readFrom(location.state) ?? ROUTES.home`으로 필터가 유지된 홈으로 돌아갈 수 있다.

### 5.5 탭 바 없는 화면 붙이기(결제 C3·C3a·C4 등)
- `<CustomerLayout access="customer" />` children에 `handle` **없이** 넣는다: `{ path: ROUTE_PATTERNS.payment, element: <PaymentPage /> }`. 탭 바는 `handle: TAB_BAR_HANDLE`이 있는 라우트에서만 그려진다.
- 하위 화면 AppBar는 `<Link to={…} aria-label={BACK_LABEL}>←</Link><h1 className="t">제목</h1><span className="sp" />`(`auth-account.md` D-20). 주 버튼은 `.cta` 안 하나(고객 셸은 420px라 `.dk`는 보이지 않음).
- 결제 경로를 `/reservations/:id/…` 아래로 두면 §5.2 규칙을 그대로 받는다. 경로는 payments 설계가 정한다.

### 5.6 비로그인 → 로그인 → 복귀(from)
- 가드 안 화면: 자동(§5.2).
- 공개 화면에서 로그인이 필요한 행동(C2 「예약하고 결제」):

```tsx
import { useLocation, useNavigate } from 'react-router';
import { loginRedirectState, useAuth } from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

const { state } = useAuth();
const navigate = useNavigate();
const location = useLocation();

function onReserve(quantity: number) {
  if (state.status !== 'authenticated') {
    // 수량을 쿼리에 넣어 두면 로그인·가입 뒤 같은 수량으로 돌아온다(screens.md A2 동작 메모)
    const from = `${location.pathname}?qty=${quantity}`;
    navigate(ROUTES.login, { state: loginRedirectState('other', from, 'reservation') });
    return;
  }
  // 예약 생성…
}
```

- A1은 `entry: 'reservation'`이면 「예약을 이어가려면 로그인하세요.」를 보이고, 로그인·가입(A2)·재설정(A3) 뒤 `resolvePostLoginPath`가 고객을 `from`으로 보낸다(상점주 경로가 아니면 그대로). A1 → A2·A3 링크는 이미 `from`을 넘긴다(`auth-account.md` D-7). `entry`는 A2·A3를 거치면 사라진다(안내 한 줄은 A1에서만).
- `from`은 내부 경로만(`readFrom`이 검사). `/login`은 넣지 않는다.

### 5.7 의존성 등록
- 새 영역은 `features/<영역>/wiring.ts`의 `wire<영역>()`을 만들고 `app/container.ts`에 한 줄 더한다(`[...wireAuth(), ...wireOffers(), ...wireReservations()]`). 테스트용 컨테이너(`tests/support/authFakes.ts`의 `createAuthContainer`)에도 가짜를 등록해야 전체 `routes`를 렌더하는 테스트가 깨지지 않는다.

## 6. 와이어프레임 대조표

구현 여부: ✓ 구현됨(3ddea13) / 이번 = 이번 계획 / 보류 = 이유와 함께 넣지 않음 / 팀원 = 다른 담당.

| 화면 | 요소 | `wireframe.html` 줄 | 상태 |
| --- | --- | --- | --- |
| A1 | ✕ 닫기 → 홈 | 167 | ✓ |
| A1 | 제목 「로그인」 | 169 | ✓ |
| A1 | 진입 경로별 안내 한 줄(C2·내 예약·마이) | 170, 179 | **이번**(누락, §3.7, C-7) |
| A1 | 이메일·비밀번호·오류·로그인 버튼 | 171~174 | ✓ |
| A1 | 「비밀번호 재설정」 | 175 | ✓ |
| A1 | 「계정이 없나요?」·「회원가입」·「사장님이신가요? 입점 신청」 | 177 | ✓ |
| A2 | ← · 제목 | 185 | ✓ |
| A2 | 역할 선택 2카드·안내 문구 | 187~192 | ✓ |
| A2 | 이름·이메일·중복 오류·비밀번호·전화·가입하기 | 193~199 | ✓ |
| A2 | C2에서 왔으면 같은 수량으로 이어가기 | 201 | 팀원(C2, §5.6) |
| A3 | 1단계·2단계 상자, 코드 다시 받기, 오류 | 207~218 | ✓ |
| C8 | 이메일(변경 불가)·이름·전화·저장 | 226~233 | ✓ |
| C8 | 상점주 상호 잠금 | 230 | ✓ |
| C8 | 「상호 변경은 고객센터에 문의해 주세요.」 | 230 | 보류(`auth-account.md` D-22) |
| C8·C9 | 고객으로 열 때 고객 셸 프레임 | `layout.md` 역할별 셸 | **이번**(M-6) |
| C9 | 세 칸·오류·안내·버튼 | 241~249 | ✓ |
| C10 | 제목 「로그아웃할까요?」 | 260 | ✓ |
| C10 | 설명 「진행 중인 예약은 그대로 남아요. 다시 로그인하면 볼 수 있어요.」 | 261 | **이번**(누락) |
| C10 | 로그아웃(dark)·취소 | 262~263 | ✓ |
| C10 | 고객 마이 위 시트 + 탭 바, 로그아웃 후 C1 | 257, 266, 268 | **이번** |
| O8 | 이름·이메일·역할, 행 3개, 상점주 안내 | 281~287 | ✓ |
| O8 | PC 드롭다운 | 292 | 보류(`auth.md` D-3) |
| C1 | 로고 「마감직전」 | 303 | 이번(D-27) |
| C1 | 위치 칩 → C1a | 303, 323 | 이번(지역 이름은 C-2) |
| C1 | 상단 「로그인」(비로그인) | 303 | 이번 |
| C1 | 「상품명 검색」 | 305 | 이번 |
| C1 | 정렬 칩 4개(마감 임박·가까운 순·할인율·낮은 가격), 위치 없으면 가까운 순 비활성 | 306, 323 | 이번 |
| C1 | 카드: 사진·상점 · 거리·상품명·할인율·할인가·정가 | 307~308 | 이번(사진은 기본 그림, C-4) |
| C1 | 카드: 「픽업 오늘 18:00–20:00」 | 309 | 이번 |
| C1 | 카드: 「판매 마감 N분 전」·「N시간 N분 전」 + 「남은 N개」 | 310, 314 | 이번 |
| C1 | 카드: 품절 태그(카운트다운 줄 대신) | 318 | 이번(기본 목록에 품절이 거의 없음, C-3) |
| C1 | 탭 바 바로 위 고정 「사장님이신가요? 입점 신청」 → A2 상점주 | 320, 323 | 이번 |
| C1 | 탭 바 홈·내 예약·마이 | 321 | 이번 |
| C1 | 비로그인 내 예약·마이 → A1 → 누른 탭 | 323 | 이번(§3.4) |
| C1 | 위치 권한 없으면 거리 숨김 | 323 | 이번 |
| C1 | 페이지 목록 | 323 | 이번(「더 보기」, D-12) |
| C1a | 칩 on 상태 | 329 | 이번 |
| C1a | 「어디서 찾을까요?」 | 332 | 이번 |
| C1a | 「◎ 현재 위치 사용」 | 333 | 이번 |
| C1a | 「지금: 망원동 (현재 위치)」 | 334 | 이번(「지금: 현재 위치」, C-2) |
| C1a | 「반경」 + 1·3·5·10km | 335~336 | 이번 |
| C1a | 위치 거부 안내 | 337 | 이번 |
| C1a | 「적용」 | 338 | 이번 |
| C1a | 주소 입력으로 위치 변경 | 342 | 보류(`open-issues.md` C1a) |
| C6 | 상단 「마이」 | 480 | 이번 |
| C6 | 이름·이메일·포인트 상자 | 482 | 이번 |
| C6 | 프로필 변경·비밀번호 변경·로그아웃 행 | 484~486 | 이번 |
| C6 | 「최근 포인트 내역」 + 「전체 보기」 | 488 | 이번 |
| C6 | 최근 내역 3행(종류·날짜·금액) | 490~492 | 이번(사유 「결제」·「환불」은 C-5) |
| C6 | 「회원 탈퇴」 조용한 링크 | 494 | 이번 |
| C6 | 탭 바(마이 굵게) | 496 | 이번 |
| C7 | ← · 「회원 탈퇴」 | 504 | 이번 |
| C7 | 「탈퇴하면 이렇게 돼요」 상자, 진행 중 예약, 남은 포인트 소멸, 「되돌릴 수 없어요.」 | 506~509 | 이번(예약 건수는 C-6) |
| C7 | 「현재 비밀번호 *」·오류 | 510~511 | 이번 |
| C7 | 취소·탈퇴하기(dark) | 513 | 이번 |
| C11 | ← · 「포인트」 | 520 | 이번 |
| C11 | 보유 포인트 상자 + 안내 | 522 | 이번 |
| C11 | 행: 종류·날짜 시각 · 잔액·금액 | 524~525 | 이번 |
| C11 | 행: 사유(환불로 적립 취소·이벤트 보상) | 526~528 | 보류(API에 없음, C-5) |
| C11 | 「더 보기」(total_elements 기준) | 530, 533 | 이번 |
| E1 | 로딩 카드 뼈대 | 542 | 이번(C1·C6·C11) |
| E1 | 빈 상태 「근처에 마감 할인이 없어요」 + 반경 넓히기 | 546 | 이번 |
| E1 | 「아직 예약이 없어요」·「할인 보러 가기」 | 547 | 팀원(C5). 「할인 보러 가기」 버튼만 C11 빈 상태에서 재사용 |
| E1 | 취소 마감 지난 예약 카드 | 544 | 팀원(C5) |
| C2·C5·C3~ | 화면 전체 | 345~475 | 팀원(자리 page·연결 안내) |

## 7. 골격·Red·Green 진행과 병렬 갈래

한 구현 에이전트가 골격 → Red → Green을 이어서 한다(사용자 지정 방식. 오케스트레이션 표준 흐름에서 Red를 `fe-qa`에게 줄지는 오케스트레이터가 발주서에 적는다, C-13).

### 7.1 골격 (한 번에, 공용 파일은 최종 모양으로)

**최종 모양으로 만드는 공용 파일**(이후 갈래에서 고치지 않음): `shared/lib/routes.ts`(§2.1 전부), `app/router/routes.tsx`(§4 그대로, 요소 연결 포함), `app/router/placeholders.tsx`(`HomePlaceholder` 삭제, 자리 page 2개 실제 구현, TODO `언제:`에 「C2 구현 시, C5 구현 시」 추가), `app/container.ts`(`wireOffers()`), `features/offers/wiring.ts`, `features/offers/index.ts`, `features/auth/index.ts`, `widgets/customer-nav/index.ts`, `pages/*/index.ts` 4개, `features/auth/application/authContext.ts`(`withdraw` 타입), `features/auth/application/ports.ts`(메서드 2개).

**실제로 만드는 것**: 모든 타입, 상수(`SORT_OPTIONS`, `RADIUS_OPTIONS`, `CUSTOMER_TABS`, 문구 상수 전부), 포트, 토큰.

**본문을 비우는 것**: domain 함수 전부(`throw new Error('not implemented: …')`), 유스케이스·훅, `HttpOfferRepository`·`BrowserLocationProvider` 메서드, `HttpAccountGateway.findPoints`·`withdraw`, `useAuthController`의 `withdraw`(기존 동작 유지), 새 컴포넌트·page·레이아웃(`return null`), `shared/lib` 새 함수·훅. 기존 파일 `LoginPage.tsx`·`LogoutConfirmSheet.tsx`·`AccountLayout.tsx`는 골격에서 건드리지 않는다.

### 7.2 Red
§8 테스트를 모두 쓰고 케이스 단위 실패를 확인한다(`tdd-workflow` §4). 기존 테스트 교체 4건(D-27)도 이 단계에서.

### 7.3 Green — 선행 0 → 병렬 A·B

**Green 0 (먼저, 한 갈래)**: 두 갈래가 함께 쓰는 아래 계층.
- `src/shared/lib/format.ts`, `src/shared/lib/useNow.ts`, `src/shared/lib/useModalFocus.ts`
- `src/app/layouts/CustomerFrame.tsx`
- `src/features/auth/domain/redirect.ts`(`readLoginEntry`, `loginRedirectState` entry), `src/features/auth/domain/loginMessage.ts`(`loginEntryMessage`)

**갈래 A — 셸 + C1 + C1a**
- `src/widgets/customer-nav/domain/customerTabs.ts`, `src/widgets/customer-nav/presentation/CustomerTabBar.tsx`
- `src/app/layouts/CustomerLayout.tsx`
- `src/features/offers/domain/{offer,nearbyQuery,offerRepository,offerFormat,homeFilter,offerMessages}.ts`
- `src/features/offers/application/{ports,tokens,useDeviceLocation,useNearbyOffers}.ts`
- `src/features/offers/infrastructure/{httpOfferRepository,browserLocationProvider}.ts`
- `src/features/offers/presentation/{OfferCard,OfferCardSkeleton,SortChips,LocationSheet,NearbyEmpty}.tsx`
- `src/pages/home/presentation/HomePage.tsx`
- 테스트: `tests/widgets/customer-nav/**`, `tests/features/offers/**`, `tests/pages/home/**`, `tests/app/layouts/CustomerLayout.test.tsx`

**갈래 B — C6 + C7 + C10 + C11 + 누락 보완**
- `src/features/auth/domain/{points,accountMessages}.ts`
- `src/features/auth/application/{points,withdraw,usePointHistory,useWithdraw,useAuthController}.ts`
- `src/features/auth/infrastructure/httpAccountGateway.ts`
- `src/features/auth/presentation/{PointLogList,PointLogSkeleton,WithdrawForm,LogoutConfirmSheet}.tsx`
- `src/pages/my/presentation/MyPage.tsx`, `src/pages/point-history/presentation/PointHistoryPage.tsx`, `src/pages/withdraw/presentation/WithdrawPage.tsx`
- `src/pages/login/presentation/LoginPage.tsx`, `src/app/layouts/AccountLayout.tsx`
- 테스트: `tests/features/auth/**`(추가분), `tests/pages/{my,point-history,withdraw,login}/**`, `tests/app/layouts/AccountLayout.test.tsx`

- 겹치는 파일 없음. `tests/support/authFakes.ts`·`renderWithAuth.tsx`(가짜 등록 확장)와 `tests/app/router/routes.test.tsx`·`tests/app/App.test.tsx`·`tests/app/container.test.ts`는 Red 단계에서 최종 모양으로 쓰고 Green에서 고치지 않는다.
- B의 `MyPage`는 A의 탭 바 없이도 단위 테스트가 돈다(page는 `.bar`·`.body`만). 전체 라우트 테스트(`routes.test.tsx`)는 두 갈래가 끝난 뒤 통과한다.

## 8. 테스트 목록 (`tdd-workflow` §2, 위치 `tests/` 아래)

공통 준비(Red에서 만듦)
- `tests/features/offers/fakes/fakeOfferRepository.fake.ts`(`findNearby: vi.fn`, 기본 빈 페이지), `fakeLocationProvider.fake.ts`(`current: vi.fn`, 기본 `null`), `offers.ts`(고정 `Offer` 생성기 `makeOffer(over)`).
- `tests/support/authFakes.ts`: `AuthFakes`에 `offers`, `location` 추가, `createAuthContainer`가 `OfferRepositoryToken`·`LocationProviderToken`도 등록. `fakeAccountGateway`에 `findPoints`(기본 잔액 0·빈 목록)·`withdraw`.
- 시각 고정: `vi.useFakeTimers({ now: new Date('2026-11-10T17:18:00+09:00') })`, 테스트 환경 `TZ=Asia/Seoul` 전제(이미 쓰는 설정이 없으면 `fe-qa`가 보고).

### (a) domain — 55

**`tests/shared/lib/format.test.ts` — 5**: `groupDigits` 0·1240·1000000·-500 (1, 표 하나) / `formatHm(9:05)` `'09:05'` / `formatMd(11/7)` `'11/07'` / `isSameLocalDate` 같은 날 23:59와 00:00 false / 같은 날 true.

**`tests/features/offers/domain/offerFormat.test.ts` — 18**
- `salesCountdown`: 42분 → `판매 마감 42분 전` / 30초 → `1분 전` / 59분 30초 → `1시간 전` / 60분 → `1시간 전` / 70분 → `1시간 10분 전` / 25시간 3분 → `25시간 3분 전` / 0 → `null` / −1분 → `null` (8)
- `pickupWindow`: 오늘 18:00–20:00 → `오늘 18:00–20:00`(en dash 확인) / 내일 → `내일 …` / 모레 → `11/12 …` (3)
- `formatDistance`: `null` → `null` / 0.42 → `0.4km` / 0.03 → `0.1km` / 12 → `12.0km` (4)
- `toOfferCardView`: 거리 있음 → `storeLine` `망원베이커리 · 0.4km`, `salePrice` `6,000원`, `originalPrice` `12,000`, `rate` `50%` / 품절(`remainingStock 0`) → `soldOut`, `countdown`·`remaining` `null` / `salesEnd` 지남 → `ended: true` (3)

**`tests/features/offers/domain/homeFilter.test.ts` — 12**
- `readHomeFilter`: `''` → 기본 / `?sort=price&radius=5&q=%20빵%20` → `{price, 5, '빵'}` / `?sort=x&radius=7` → 기본 sort·3 / `q` 101자 → 100자 (4)
- `toHomeSearch`: 기본 → `''` / `{distance,10,'빵'}` → `?sort=distance&radius=10&q=빵`(왕복하면 같은 값) (2)
- `effectiveSort('distance', false)` → `sales_end` / `('distance', true)` → `distance` / `isSortAvailable('price', false)` → true (3)
- `nextRadius` 3→5 / 10→`null` (2)
- `locationChipLabel(true,3)` `현재 위치 · 3km` / `(false,3)` `전체 지역` (1, 묶음)

**`tests/features/auth/domain/points.test.ts` — 12**
- `pointTypeLabel` 6종 표 → 적립·사용·복구·회수·지급·소멸 (1, 표 하나)
- `formatPointDelta`: 115 → `+115P` / −500 → `−500P`(U+2212) / 1000 → `+1,000P` / 0 → `0P` (4)
- `formatPoint(1240)` → `1,240P` (1)
- `pointLogMeta`: short → `11/07` / full + 잔액 → `11/07 18:02 · 잔액 1,240P` / full + `null` → `11/07 18:02` (3)
- `pointExpiryText(1240)` → `1,240P 소멸` / `(0)` → `0P 소멸` (2)
- `withdrawErrorView`: `CURRENT_PASSWORD_MISMATCH` + 서버 문구 → `{password, '비밀번호가 일치하지 않습니다.'}` (1)

**`tests/features/auth/domain/accountMessages.test.ts` 추가 — 2**: `withdrawErrorView` `FORBIDDEN '정지된 계정입니다.'` → `{form, 그 문구}` / `message ''` → `{form, ACCOUNT_FALLBACK_MESSAGE}`.

**`tests/features/auth/domain/redirect.test.ts`·`loginMessage.test.ts` 추가 — 6**: `loginRedirectState('other','/me','customerTab')` → `{from:'/me', entry:'customerTab'}` / `('loggedOut','/me','customerTab')` → `undefined` / `readLoginEntry({entry:'reservation'})` → `'reservation'` / `({entry:'x'})` → `null` / `loginEntryMessage('reservation')` → `예약을 이어가려면 로그인하세요.` / `('customerTab')` → 임시 문구.

### (b) application — 22

- `tests/features/offers/application/useDeviceLocation.test.tsx` — 3: 처음 `pending` → 좌표 → `ok`·`point` / `null` → `unavailable` / `request()` → 다시 호출, `pending` 거쳐 `ok`.
- `useNearbyOffers.test.tsx` — 7: `ready=false`면 `findNearby` 미호출·`loading` / `ready` → 쿼리 `{location, radiusKm:3, sort:'sales_end', keyword:'', page:1, size:20}` / 위치 없음 + `sort:'distance'` → 요청 `sort:'sales_end'` / 0건 → `empty` / 실패 → `error`, `retry()` → 다시 1페이지 / `total 25`·20개 → `hasMore`, `loadMore()` → `page:2`, 이어 붙여 25개 / 필터 바뀌면 앞 요청 `signal.aborted`, 목록 초기화.
- `tests/features/auth/application/points.test.ts` — 2: 성공 → 그대로 반환 / 401 → `session.clear` 후 reject.
- `withdraw.test.ts` — 3: 성공 → `account.withdraw('pw')` 뒤 `session.clear`(순서) / `CURRENT_PASSWORD_MISMATCH` → `clear` 미호출, reject / 401 → `clear` 후 reject.
- `usePointHistory.test.tsx` — 4: 마운트 → `findPoints({page:0,size:3})`, `balance`·`logs` / 0건 → `empty`, `balance` 있음 / `total 25` → `hasMore`, `loadMore()` → `page:1` 이어 붙임 / 실패 → `error`.
- `useAuthController.test.tsx` 추가 — 3: `withdraw` 성공 → `{anonymous, cause:'loggedOut'}` / 400 → 상태 `authenticated` 그대로, reject / 401 → `{anonymous, cause:'other'}`, reject.

### (c) infrastructure — 9

- `tests/features/offers/infrastructure/httpOfferRepository.test.ts` — 4 (`vi.mock('@/shared/api/client')`): 위치 있음 → `/v1/offers?lat=…&lng=…&radius_km=3&sort=sales_end&page=1&size=20`, `auth:false` / 위치 없음 → `lat`·`lng`·`radius_km` 없음, `keyword` 공백만이면 없음 / DTO → `Offer`(`salesEnd` `Date`, `distance` → `distanceKm`) / `status:'WEIRD'` → reject.
- `browserLocationProvider.test.ts` — 3: 성공 → `{lat,lng}`, 옵션 `timeout:8000` / 오류 콜백 → `null` / `navigator.geolocation` 없음 → `null`.
- `httpAccountGateway.test.ts` 추가 — 2: `findPoints({page:0,size:20})` → `/v1/users/me/points?page=0&size=20`, DTO → `PointPage`(`balance_after:null` 유지, `total_elements` → `total`) / `withdraw('pw')` → `POST /v1/users/me/withdraw` `{password:'pw'}`.

### (d) presentation·pages·app — 48

**`tests/widgets/customer-nav/customerTabs.test.ts` — 3**: `/` → home / `/me/points` → me, `/reservations/` → reservations / `/offers/1`·`/login` → `null`.

**`tests/app/layouts/CustomerLayout.test.tsx` — 7**: public + anonymous → Outlet 보임, 탭(handle 있을 때) / customer + anonymous → `/login`, `state` `{from:'/me?x=1', entry:'customerTab'}` / customer + OWNER → `/` / customer + loading → `aria-busy`, Outlet 없음 / allow 뒤 로그아웃(`loggedOut`) → `/` / 처음부터 `loggedOut` 상태로 `/reservations` → `/login`(`from` 있음) / 탭 바: 홈 링크 `aria-current="page"`가 `<b>` 안, handle 없는 라우트(`/me/points`)는 탭 없음.

**`tests/pages/home/HomePage.test.tsx` — 14** (`renderRoutesWithAuth` + 전체 `routes`)
1. 로고 heading 「마감직전」, 탭 바 「홈」 현재
2. 위치 거부(`null`) → 칩 「전체 지역」, 카드 상점명만(「·」 거리 없음), 「가까운 순」 `aria-disabled="true"`, 누르면 요청 변화 없음
3. 위치 허용 → 칩 `현재 위치 · 3km`, 카드 `망원베이커리 · 0.4km`
4. 카드: `6,000원`·`12,000`(취소선 `s`)·`50%`·「픽업 오늘 18:00–20:00」·`판매 마감 42분 전`·`남은 3개`
5. 품절 카드 → `tag mute` 「품절」, 카운트다운·남은 수량 없음
6. 카드 클릭 → URL `/offers/<id>`, 「C2 할인 상세」
7. 정렬 「할인율」 → URL `?sort=discount_rate`, 요청 `sort:'discount_rate'`, 칩 `aria-pressed`
8. 검색어 입력 + Enter → 요청 `keyword:'빵'`, URL `?q=빵`
9. 로딩 → 뼈대 카드 3개, `aria-busy="true"` / 실패 → 임시 문구 + 「다시 시도」 → 재요청
10. 빈 결과(위치 3km) → 「근처에 마감 할인이 없어요」 + 「반경 5km로 넓히기」 → 요청 `radiusKm:5` / 위치 없음 빈 결과 → 버튼 없음
11. `total 25` → 「더 보기」 → 2페이지 요청, 카드 25개
12. 비로그인 → 상단 「로그인」(`href=/login`, state `from:'/'`) + 「사장님이신가요? 입점 신청」 `href="/signup?role=owner"`, 고객 로그인 → 둘 다 없음
13. C1a: 위치 칩 → dialog 「어디서 찾을까요?」, 「◎ 현재 위치 사용」·「지금: 현재 위치」·반경 칩 4개·거부 안내·「적용」, `.body` 대신 `.dim`(목록 안 보임), 첫 포커스 「◎ 현재 위치 사용」
14. C1a: 「10km」 → 「적용」 → 시트 닫힘, URL `?radius=10`, 요청 `radiusKm:10`, 칩 `현재 위치 · 10km` / Escape → 적용 없이 닫힘, 포커스 위치 칩

**`tests/pages/my/MyPage.test.tsx` — 8**
1. 「마이」 heading, 이름·이메일, 포인트 `1,240P`(`findPoints` 잔액), 탭 바 「마이」 현재
2. 행 「프로필 변경」 `href=/account/profile`, 「비밀번호 변경」 `href=/account/password`, 클릭 시 `state.from === '/me'`
3. 최근 내역 3행: 「적립」·`11/07`·`+115P` / 「사용」·`−500P`
4. 「전체 보기」 `href=/me/points`, 「회원 탈퇴」 `href=/me/withdraw`
5. 포인트 불러오기 실패 → 상자는 `user.point`, 내역 자리 임시 문구 + 「다시 시도」 / 0건 → 「포인트 내역이 없어요」
6. 「로그아웃」 → `.dim` 안 alertdialog 「로그아웃할까요?」 + 「진행 중인 예약은 그대로 남아요. 다시 로그인하면 볼 수 있어요.」, 「취소」 → 시트 닫힘
7. 「로그아웃」 확정 → `auth.logout` 호출, URL `/`, 상단 「로그인」 보임
8. `/me`로 비로그인 진입 → `/login`, A1에 「예약 내역을 보려면 로그인하세요.」, 로그인(CUSTOMER) → `/me`

**`tests/pages/point-history/PointHistoryPage.test.tsx` — 5**: 제목 「포인트」, ← `href=/me`, 탭 바 없음 / 「보유 포인트」 `1,240P`·「결제 금액의 1% 적립 · 100P 단위로 사용」 / 행 `11/07 18:02 · 잔액 1,240P`, `balance_after null` 행은 `· 잔액` 없음 / `total 25` → 「더 보기」 → `page:1`, 25행, 끝나면 버튼 없음 / 0건 → 「포인트 내역이 없어요」 + 「할인 보러 가기」 `href=/`.

**`tests/pages/withdraw/WithdrawPage.test.tsx` — 6**: 제목 「회원 탈퇴」, 「탈퇴하면 이렇게 돼요」·「진행 중 예약」 임시 문구·`1,240P 소멸`·「되돌릴 수 없어요.」 / 「현재 비밀번호 *」 `type=password`·`autoComplete=current-password`, 「탈퇴하기」 처음 `aria-disabled` / 「취소」 `href=/me` / 제출 → `account.withdraw('pw123456')`, `session.clear`, URL `/` / `CURRENT_PASSWORD_MISMATCH` → 칸 아래 「비밀번호가 일치하지 않습니다.」, 입력 유지 / 처리 중 「처리 중…」·연타 1회.

**`tests/pages/login/LoginPage.test.tsx` 추가 — 2**: `state {from:'/offers/1', entry:'reservation'}` → 「예약을 이어가려면 로그인하세요.」 / `entry` 없음 → 안내 `.m` 없음.

**`tests/app/layouts/AccountLayout.test.tsx` 추가 — 1**: CUSTOMER → `[data-shell="customer"]` 안에 본문 / OWNER → 프레임 없음(묶음 1).

**`tests/app/router/routes.test.tsx` 변경·추가 — 교체 1 + 1**: 교체 「/는 「마감 직전」」 → 「/는 heading 「마감직전」과 탭 바」. 추가: `/offers/abc` 비로그인 → 「C2 할인 상세」·`abc` / `/reservations` CUSTOMER → 「C5 내 예약」·탭 현재 「내 예약」 / `/me/points` 비로그인 → `/login`(묶음 1).

**기존 테스트 교체(D-27, Red 범위)**: `tests/app/App.test.tsx:17`, `tests/app/router/routes.test.tsx:49~51`, `e2e/account.spec.ts:55`, `e2e/auth.spec.ts:134`의 heading 「마감 직전」 → 「마감직전」. `tests/app/container.test.ts` 토큰 목록에 `OfferRepositoryToken`·`LocationProviderToken` 추가.

### (e) E2E — `e2e/customer.spec.ts` 신규 3 (`page.route`로 응답, `context.grantPermissions`/`geolocation`)

1. 비로그인 홈(위치 권한 없음): 카드에 거리 없음, 「가까운 순」 비활성, 「판매 마감 N분 전」 보임 → 카드 클릭 → `/offers/<id>` 「C2 할인 상세」 → ← → 홈 → 「사장님이신가요? 입점 신청」 → `/signup?role=owner` 「상점주」 선택됨.
2. 비로그인 「마이」 탭 → A1 「예약 내역을 보려면 로그인하세요.」 → 고객 로그인 → `/me`(잔액·최근 3행) → 「전체 보기」 → C11 「더 보기」로 2페이지 요청(`page=1`).
3. 고객 `/me` → 「로그아웃」 → 설명 문구 → 확정 → `/`(상단 「로그인」). 다시 로그인 → `/me/withdraw` → 400 `CURRENT_PASSWORD_MISMATCH` 문구 → 200 → `/`, `localStorage` 토큰 없음.

### 테스트 수 합계

domain 55, application 22, infrastructure 9, presentation·pages·app 48(customerTabs 3, CustomerLayout 7, HomePage 14, MyPage 8, PointHistoryPage 5, WithdrawPage 6, LoginPage 추가 2, AccountLayout 추가 1, routes 교체 1 + 추가 1). 신규·추가 단위·컴포넌트 **약 134개**, E2E 신규 3개. 기존 테스트 교체 4건(heading 문구) + `container.test.ts`·`tests/support` 확장.

## 9. 남길 작업 주석 (`code-annotations`, F19)

**이번에 지운다·고친다**

| 위치 | 주석 | 처리 |
| --- | --- | --- |
| `src/pages/login/presentation/LoginPage.tsx:12~14` | TODO 진입 경로별 안내 한 줄 없음 | 안내 한 줄 구현으로 삭제(C2 진입은 §5.6 안내로 C2 담당이 `entry`를 넘김) |
| `src/app/layouts/AccountLayout.tsx:11~13` | TODO C8·C9 고객 셸 프레임(`auth-account.md` M-6) | `CustomerFrame` 적용으로 삭제 |
| `src/app/router/placeholders.tsx:1~3` | TODO 자리 page 교체 | `언제:`에 「C2 구현 시, C5 구현 시」 추가 |
| `src/features/auth/application/useAuthController.ts` FIXME(다른 영역 401) | | **그대로 둔다.** `왜:`에 "customer-home.md D-25: C6·C7·C11은 유스케이스가 직접 clear()" 덧붙임. C1은 공개 API(`auth:false`)라 해당 없음 |

**새로 남긴다**

| ID | 위치 | 태그 | 원문 초안 |
| --- | --- | --- | --- |
| H-1 | `features/offers/domain/offerMessages.ts`, `features/auth/domain/accountMessages.ts` 임시 상수 위 | TODO | `// TODO: 임시 문구다(목록 불러오기 실패, 정렬 묶음 이름, 탈퇴 예약 줄, 포인트 빈·실패, 다시 시도). 정본 문구가 정해지면 바꾼다.`<br>`//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/customer-home.md §3.1)`<br>`//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)` |
| H-2 | `features/offers/domain/homeFilter.ts` `locationChipLabel` | TODO | `// TODO: 위치 칩에 동네 이름(망원동) 대신 「현재 위치」·「전체 지역」을 쓴다.`<br>`//   왜: 좌표 → 동네 이름 변환 API가 없다 (customer-home.md C-2, D-16)`<br>`//   언제: 결정 후 (백엔드: 고객용 주소 변환)` |
| H-3 | `features/offers/presentation/LocationSheet.tsx` | open-issues | `// open-issues: C1a 주소를 입력해 위치 바꾸기 없음 (현재 위치만)` |
| H-4 | `features/offers/presentation/OfferCard.tsx` 썸네일 | TODO | `// TODO: 카드 사진 자리에 기본 그림만 둔다.`<br>`//   왜: 주변 할인 목록 응답(Offer)에 상품 이미지 필드가 없다 (customer-home.md C-4)`<br>`//   언제: 결정 후 (백엔드: Offer 응답에 이미지)` |
| H-5 | `features/offers/infrastructure/httpOfferRepository.ts` | TODO | `// TODO: 기본 상태(ON_SALE)만 받아 품절 카드가 거의 나오지 않는다.`<br>`//   왜: status는 한 값만 받는다. 판매 중 + 품절을 함께 보여 줄지 정해지지 않았다 (customer-home.md C-3)`<br>`//   언제: 결정 후 (사용자: 홈 목록에 품절 포함 여부)` |
| H-6 | `features/auth/presentation/PointLogList.tsx` | TODO | `// TODO: 포인트 내역 사유(결제·환불·이벤트 보상)를 보여 주지 않는다.`<br>`//   왜: 포인트 내역 응답에 사유 필드가 없다 (customer-home.md C-5)`<br>`//   언제: 결정 후 (백엔드: point_log 사유)` |
| H-7 | `features/auth/presentation/WithdrawForm.tsx` 예약 줄 | TODO | `// TODO: 진행 중 예약 건수 대신 「모두 취소·환불」을 보인다.`<br>`//   왜: 예약 건수는 reservations 영역 API가 필요하다 (customer-home.md C-6)`<br>`//   언제: C5 구현 시` |
| H-8 | `pages/withdraw/presentation/WithdrawPage.tsx` | TODO | `// TODO: 탈퇴 뒤 안내 없이 홈으로 보낸다.`<br>`//   왜: 탈퇴 완료 뒤 화면·문구가 정본에 없고 알림 컴포넌트도 없다 (customer-home.md C-15)`<br>`//   언제: 결정 후 (디자인 시스템: 탈퇴 완료 안내)` |

## 10. 정합 이슈

| C | 내용 | 근거 | 처리 |
| --- | --- | --- | --- |
| C-1 | `features/offers`를 이 문서(C1)와 catalog 담당(C2)이 함께 쓴다. `frontend-orchestration.md` §4는 slice당 한 명 | `fsd-structure` §1.1(C1·C2 모두 offers) / `frontend-orchestration.md` §4 | 이 문서가 영역 뼈대(타입·포트·토큰·wiring)를 먼저 만들고, C2는 파일 추가 + `OfferRepository`·`index.ts`에 줄 추가만(§5.4). 두 작업은 순차 머지 |
| C-2 | 와이어프레임 위치 칩 「망원동 · 3km」, C1a 「지금: 망원동 (현재 위치)」에 동네 이름이 있으나 좌표 → 동네 이름 변환이 없다 | `wireframe.html:303·334` / `open-issues.md` C1a(카카오 변환은 상점 개설용만) | 「현재 위치 · Nkm」·「지금: 현재 위치」·「전체 지역」 임시(D-16, H-2) |
| C-3 | 와이어프레임 C1 품절 카드가 있으나 `GET /v1/offers` 기본 `status=ON_SALE`이라 품절(`SOLD_OUT`)은 목록에 안 나온다. `status`는 한 값만 | `wireframe.html:315~318`, `OfferCard` README / `catalog.md` §8, `router.py:146` | 기본값으로 요청, 응답에 품절이 섞이면(`remaining_stock 0`) 태그 표시. 확인 필요(Q-3, H-5) |
| C-4 | `OfferCard` README "사진 4:3, 없으면 기본 그림"인데 Offer 응답에 이미지가 없다 | `components/OfferCard/README.md` / `schemas.py:126~145` | 기본 그림(`.ph`)만(H-4) |
| C-5 | 포인트 행 보조 줄의 사유(「결제」·「환불로 적립 취소」·「이벤트 보상」)가 API에 없다 | `wireframe.html:490~492·524~528` / `auth.md` §5, `schemas.py:43~50` | 날짜(·잔액)만(H-6). 종류로 사유를 추측하지 않음 |
| C-6 | C7 「진행 중 예약 1건 취소·환불」 건수는 예약 API(reservations 영역)가 필요. 탈퇴 응답 `cancelled_reservation_count`는 탈퇴 뒤에 옴 | `wireframe.html:507` / `auth.md` §12, `reservations.md` | 「모두 취소·환불」 임시(H-7). reservations 영역이 생기면 `entities/reservation` 포트로 건수를 받을지 그때 결정 |
| C-7 | A1 내 예약·마이 진입 문구가 「예약 내역을 보려면…」까지만 있다 | `screens.md` A1 동작 메모, `wireframe.html:179` | 「예약 내역을 보려면 로그인하세요.」 임시(C2 문구 「예약을 이어가려면 로그인하세요.」와 같은 꼴) |
| C-8 | `EmptyState` README·`states.md` "빈 상태는 다음 행동 버튼 하나"인데, 위치가 없거나 이미 10km면 줄 수 있는 행동이 없다 | `components/EmptyState/README.md`, `states.md` 화면 상태 공통 | 그 경우 버튼 없이 문구만(D-17). Q-6 |
| C-9 | 로고 문구: 와이어프레임 「마감직전」 ↔ 기존 자리 page·테스트 4건 「마감 직전」 | `wireframe.html:303·329` / `placeholders.tsx`, `App.test.tsx:17` 등 | 와이어프레임 문구(F13, D-27). 기존 테스트 4건은 Red에서 교체 |
| C-10 | `reference/auth.md` §5 "확인 필요: 이 API만 page 0부터·total_elements" | `auth.md` §5 / `router.py:150~151`(`ge=0`) | 백엔드(0부터)를 따른다. 백엔드가 1부터로 바뀌면 infrastructure만 고침 |
| C-11 | 요청 범위를 넘은 추가: `LogoutConfirmSheet` 설명 줄이 상점주 O8에도 보임, `shared/lib` 새 파일 3개, `AuthContextValue.withdraw` 추가, `AccountLayout` 고객 프레임. `OwnerAccountButton`의 포커스 트랩을 `useModalFocus`로 바꾸는 정리는 하지 않음(제안) | 요청서 §3 "누락 보완" / §2.1, D-23·D-24·D-26 | 사용자 위임으로 포함 확정. `OwnerAccountButton` 정리는 별도 작업 제안 |
| C-12 | 백엔드 `OfferResponse.status`에 `SUSPENDED`(소유자에게만)가 있으나 reference Offer 표에는 4개 | `schemas.py:142~144` / `catalog.md` §공통 객체 | domain `OfferStatus`에 5개 모두 둠(모르는 값만 throw) |
| C-13 | 사용자 지정 "한 에이전트가 골격 → Red → Green"과 `tdd-workflow` §1·`frontend-orchestration.md` §2 5번(Red를 쓴 `fe-qa`는 구현을 맡지 않음, 수정자 ≠ 점검자) | 요청서 / `tdd-workflow` §1 표, `frontend-orchestration.md` §2 | 설계는 단계 순서만 적는다(§7). 담당 배정은 오케스트레이터가 사용자와 정함 |
| C-14 | C1a에 닫기(취소) 버튼이 와이어프레임에 없다 | `wireframe.html:331~339`, `BottomSheet` README(취소는 아래) | Escape·바깥 누름으로 닫힘(D-15) |
| C-15 | C7 탈퇴 성공 뒤 이동·안내가 정본에 없다 | `screens.md` C7(연결 화면 없음) | C1로 이동, 안내 없음(D-24, H-8). Q-7 |

## 11. 결정 표

D-1~D-31은 사용자 위임으로 권장안을 확정했다(2026-11-10). 구현을 막는 항목은 없다. 문구 중 "임시"(§3.1)는 확정된 임시값이며 content.md가 정해지면 바꾼다(H-1).

| D | 항목 | 값 | 상태 | 근거 | 구현을 막는가 |
| --- | --- | --- | --- | --- | --- |
| D-1 | 문서·범위 | 새 파일 `customer-home.md`. 고객 셸·C1·C1a·C6·C7·C10·C11 + 기존 화면 누락 보완(§3.7). C2·C5·C3~는 자리 page + 연결 안내 | 확정(위임, 2026-11-10) | 사용자 범위. `auth-account.md` §11 이어받음 | 아니오 |
| D-2 | 고객 셸 구조 | `widgets/customer-nav`(탭) + `app/layouts/CustomerLayout({access})` + `CustomerFrame`. 탭 유무는 라우트 `handle: TAB_BAR_HANDLE` | 확정(위임, 2026-11-10) | 상점주 셸(`app-shell.md` D-2)과 같은 구조, handle 재사용 | 아니오 |
| D-3 | 경로 | 고정 계약 `home '/'`, `offerDetail(id)`, `reservations`, `me`, `mePoints` + `meWithdraw: '/me/withdraw'`, `ROUTE_PATTERNS.offerDetail` | 확정(위임, 2026-11-10) | 사용자 고정 계약. C7은 `/me/*` 가드를 받도록 그 아래 | 아니오 |
| D-4 | 고객 가드 | §3.4 표. `login-without-from`은 이 레이아웃이 방금 `allow`였을 때만 홈(로그아웃·탈퇴 직후), 아니면 A1(+from, entry `customerTab`). 다른 역할 → `/` | 확정(위임, 2026-11-10) | `screens.md` C10(로그아웃 후 C1)·C1(비로그인 탭 → A1 → 누른 탭). 로그아웃 뒤 남는 `cause:'loggedOut'` 때문에 탭이 홈으로 튕기는 문제 방지 | 아니오 |
| D-5 | PC 프레임 | `CustomerFrame` 420px 가운데·좌우 1px `--line`(인라인 style, 토큰만). 컨테이너가 720px에 닿지 않아 `.cta`만 보임, 고객 전용 화면(C7)은 `.dk` 두 벌을 두지 않음. C8·C9는 고객일 때 같은 프레임 | 확정(위임, 2026-11-10) | `layout.md` 역할별 셸. bundle.css에 프레임 클래스 없음(F12) | 아니오 |
| D-6 | 탭 바 | 홈·내 예약·마이, 현재 탭 `<b>` + `aria-current`, 로그인 여부를 따지지 않고 링크(가드가 A1로). `nav` 접근 이름 「고객 메뉴」 임시 | 확정(위임, 2026-11-10) | `TabBar` README, `OwnerNavItems` 마크업 | 아니오 |
| D-7 | A1 진입 안내 | `LoginLocationState.entry`(`reservation`·`customerTab`), A1 `h1` 아래 `.m` 한 줄. 문구는 §3.1 | 확정(위임, 2026-11-10) | `wireframe.html:170·179`. 기존 TODO 해소 | 아니오 |
| D-8 | 할인 영역·entities | `features/offers` 신설, `Offer`·`OfferRepository`는 영역 안(entities 없음). C2가 같은 영역에 더함 | 확정(위임, 2026-11-10) | `fsd-structure` §4 "미리 entities를 만들지 않습니다" | 아니오 |
| D-9 | 위치 | application 포트 `LocationProvider` + `BrowserLocationProvider`(geolocation, 8초, 5분 캐시). C1 마운트 때 한 번 요청, 결과 전까지 목록 요청 안 함. 실패·거부·초과는 모두 「위치 없음」 | 확정(위임, 2026-11-10) | `screens.md` C1a "기본은 기기 위치". 요청 두 번(위치 없이 → 위치로)을 피함 | 아니오 |
| D-10 | 필터 보관 | 정렬·반경·검색어를 URL 쿼리(`sort`·`radius`·`q`, 기본값 생략)에, 바꿀 때 `replace`. 좌표는 URL에 넣지 않음 | 확정(위임, 2026-11-10) | C2에서 돌아와도 필터 유지, 위치는 기기 상태 | 아니오 |
| D-11 | 정렬 칩 | 마감 임박=`sales_end`(기본)·가까운 순=`distance`·할인율=`discount_rate`·낮은 가격=`price`. 위치 없으면 가까운 순 `aria-disabled`, 요청은 `effectiveSort` | 확정(위임, 2026-11-10) | `wireframe.html:306`, `catalog.md` §8, `search.py:43~45` | 아니오 |
| D-12 | 페이지 목록 | 20개씩, 목록 끝 「더 보기」로 이어 붙임(C11과 같은 방식) | 확정(위임, 2026-11-10) | `screens.md` C1 "페이지 목록", C11 「더 보기」 | 아니오 |
| D-13 | 카드 표기 | §3.1(`salesCountdown` 올림·정각 「N시간 전」·24시간 이상도 시간, 판매 종료 → 「판매 종료」 태그, 거리 소수 1자리·최소 0.1km, 픽업 오늘/내일/MM/DD). 시각은 브라우저 로컬 | 확정(위임, 2026-11-10) | `content.md` 숫자·시간 표기, `states.md`. 경계 표기는 정본 없음(Q-9·Q-10) | 아니오 |
| D-14 | 시계 | `useNow()` 30초마다 갱신, 카드 카운트다운에 사용 | 확정(위임, 2026-11-10) | 「판매 마감 N분 전」이 화면을 보는 동안 맞게 | 아니오 |
| D-15 | C1a 시트 | 라우트 없음. `.body` 자리에 `.dim` + `LocationSheet`(와이어프레임 구조). 반경은 「적용」 때 반영, 「◎ 현재 위치 사용」은 바로 위치 재요청. Escape·바깥 누름은 적용 없이 닫힘 | 확정(위임, 2026-11-10) | `wireframe.html:330~339`, `BottomSheet` README, C-14 | 아니오 |
| D-16 | 위치 문구 | 칩 `현재 위치 · Nkm` / `전체 지역`, 시트 `지금: 현재 위치` / `지금: 전체 지역` | 확정(위임, 2026-11-10) | C-2 | 아니오 |
| D-17 | 빈·오류·로딩 | 로딩 Skeleton 3개, 빈 상태 E1 문구 + 다음 반경 버튼(위치 있고 10km 미만일 때만), 오류는 `.warn` 임시 문구 + 「다시 시도」(서버 문구 노출 안 함) | 확정(위임, 2026-11-10) | `states.md` 화면 상태 공통, E1, C-8 | 아니오 |
| D-18 | 상단 로그인·입점 신청 | 비로그인일 때만 둘 다 보임. 로그인 링크는 `state.from = 홈 경로+쿼리`(entry 없음 → A1 안내 없음). 입점 신청은 탭 바 바로 위 고정 | 확정(위임, 2026-11-10) | `screens.md` C1·A1. A2는 비로그인 전용(`auth-account.md` D-5) | 아니오 |
| D-19 | 할인 목록 요청 | `auth:false`, `status` 생략(ON_SALE), `keyword`는 trim 뒤 비면 생략 | 확정(위임, 2026-11-10) | 공개 API, 남은 토큰 영향 차단. C-3 | 아니오 |
| D-20 | 포인트 API | `AccountGateway.findPoints({page,size})`·`withdraw(password)`. `type` 필터는 쓰지 않음. 훅 하나 `usePointHistory(pageSize)`를 C6(3)·C7(1)·C11(20)이 씀 | 확정(위임, 2026-11-10) | `auth-account.md` §11 메모, 화면에 종류 필터 없음 | 아니오 |
| D-21 | 포인트 행 표기 | C6 `MM/DD`, C11 `MM/DD HH:mm · 잔액 N P`(잔액 없으면 생략), 금액 `+N P`/`−N P`(U+2212) | 확정(위임, 2026-11-10) | `content.md`, `screens.md` C11, C-5 | 아니오 |
| D-22 | C6·C7·C11 잔액 | 포인트 응답 `users_point`, 받기 전·실패 시 `useAuth` 사용자의 `point` | 확정(위임, 2026-11-10) | 결제 뒤 세션 사용자 잔액이 낡을 수 있음. 화면 상자는 항상 채움 | 아니오 |
| D-23 | C10 | page 안 `.dim` + 기존 `LogoutConfirmSheet`, 설명 한 줄 추가(역할 무관). 로그아웃 후 고객은 C1(가드 D-4) | 확정(위임, 2026-11-10) | `wireframe.html:257~268`, C10 공용 | 아니오 |
| D-24 | C7 | `AuthContextValue.withdraw` → 성공 시 `anonymous loggedOut` → C1(안내 없음). 오류는 `withdrawErrorView`. 예약 줄 「모두 취소·환불」 임시 | 확정(위임, 2026-11-10) | 로그아웃과 같은 상태 전이로 가드가 C1로 보냄. C-6·C-15 | 아니오 |
| D-25 | 401 처리 | `loadPoints`·`withdrawAccount`가 401이면 `session.clear()` 후 throw → 가드가 A1(+from) | 확정(위임, 2026-11-10) | `auth-account.md` D-18과 같은 방식 | 아니오 |
| D-26 | shared 추가 | `shared/lib/format.ts`·`useNow.ts`·`useModalFocus.ts` | 확정(위임, 2026-11-10) | 숫자·날짜 표기를 offers·auth·이후 payments가 함께 씀(업무 모름 → shared) | 아니오 |
| D-27 | 홈 로고 | `<h1 className="logo">마감직전</h1>`, 기존 「마감 직전」 테스트 4건 교체 | 확정(위임, 2026-11-10) | `wireframe.html:303`, F13, C-9 | 아니오 |
| D-28 | 자리 page | `placeholders.tsx`에 `OfferDetailPlaceholder`(C2)·`ReservationsPlaceholder`(C5), 화면 ID 표시 | 확정(위임, 2026-11-10) | `app-shell.md` D-8·D-15 | 아니오 |
| D-29 | pages 이름 | `home`(C1), `my`(C6), `point-history`(C11), `withdraw`(C7) | 확정(위임, 2026-11-10) | `fsd-structure` §5(뜻으로) | 아니오 |
| D-30 | 진행·분할 | 골격(공용 파일 최종 모양) → Red → Green 0(shared·CustomerFrame·redirect) → 갈래 A·B 병렬(§7) | 확정(위임, 2026-11-10) | 사용자 지정 방식, 쓰기 범위 겹침 0 | 아니오 |
| D-31 | 이어받는 확정값 | 토큰 `localStorage`, 경로 상수 위치(`app-shell.md` D-17), `location.state` 복귀(`auth.md` D-1), `useSubmit`·AbortSignal(`auth-account.md` D-32), 하위 화면 AppBar(`auth-account.md` D-20), 역할별 도착지 | 확정(이전 결정) | 다시 묻지 않음 | |

## 12. 정책·보안 메모

- 위치 좌표는 요청 쿼리에만 쓰고 URL·`location.state`·저장소에 남기지 않는다.
- 탈퇴 비밀번호는 입력 칸 값 외에 상태·로그·URL에 두지 않는다. 탈퇴 성공 뒤 세션을 먼저 지우고 이동한다.
- `from`은 `readFrom`·`resolvePostLoginPath`의 내부 경로 검사를 거친 값만 쓴다. 카드 링크의 `state.from`도 같은 방식으로 읽는다.
- 할인 목록은 토큰을 붙이지 않는다(`auth:false`). 포인트·탈퇴는 토큰을 붙인다.
- 서버 문구는 JSX 텍스트로만 출력한다(F17).

## 13. 확인 필요·질문 목록 (임시 동작으로 진행)

| Q | 질문 | 임시 동작 | 상태 |
| --- | --- | --- | --- |
| Q-1 | 위치 칩·C1a의 동네 이름(망원동)을 보이려면 고객용 좌표 → 주소 변환이 필요하다(C-2) | 「현재 위치」·「전체 지역」 | 확인 필요(백엔드) |
| Q-2 | C1a 주소 입력으로 위치 바꾸기(`open-issues.md` C1a) | 현재 위치만 | 확인 필요(open-issues) |
| Q-3 | 홈 목록에 품절 할인을 함께 보여 줄지(기본 ON_SALE, `status` 한 값만, C-3) | ON_SALE만 요청 | 확인 필요(사용자·백엔드) |
| Q-4 | Offer 응답에 상품 이미지(C-4) | 기본 그림 | 확인 필요(백엔드) |
| Q-5 | 포인트 내역 사유 필드(C-5) | 날짜·잔액만 | 확인 필요(백엔드) |
| Q-6 | 빈 상태에서 줄 행동이 없을 때(위치 없음·10km) 버튼(C-8) | 버튼 없음 | 확인 필요(디자인) |
| Q-7 | 탈퇴 완료 뒤 이동·안내(C-15) | C1, 안내 없음 | 확인 필요(디자인) |
| Q-8 | C7 진행 중 예약 건수(C-6) | 「모두 취소·환불」 | C5 구현 때 결정 |
| Q-9 | 카운트다운 경계 표기(1분 미만, 정각, 24시간 이상, 판매 종료) | §3.1 | 확인 필요(content.md) |
| Q-10 | 0.05km 미만 거리 표기 | 0.1km | 확인 필요(content.md) |
| Q-11 | A1 「예약 내역을 보려면…」 전체 문장(C-7) | 「예약 내역을 보려면 로그인하세요.」 | 확인 필요(content.md) |
| Q-12 | 임시 문구(§3.1 **임시**, H-1) | 해요체 임시값 | 확인 필요(content.md) |
| Q-13 | 표시 시각 기준: 브라우저 로컬(한국 시각 전제) | 로컬 | 확인 필요(배포 대상) |
| Q-14 | `discount_rate` 계산식(`catalog.md` "확인 필요") | 서버 값 그대로 | 백엔드 몫 |
| Q-15 | 포인트 API만 page 0부터(C-10) | 백엔드 따름 | 확인 필요(명세) |
| Q-16 | 구현 담당 배정: 한 에이전트 골격→Red→Green과 수정자 ≠ 점검자 규칙(C-13) | 오케스트레이터가 발주서에 명시 | 오케스트레이터 |
