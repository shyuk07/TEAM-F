# offers 영역 설계: C2 할인 상세

- 대상 화면: C2 할인 상세 전체(상품 이미지, 상점명·주소, 할인가·정가·할인율, 판매 마감, 남은 수량, 픽업 시간, 취소 가능 시한, 안내·취소 정책 문구, 품절·판매 종료 표시) + 예약 영역(`ReserveOfferPanel` 끼우기) + 비로그인 → A1 → 같은 수량으로 C2 복귀. E1 중 C2의 로딩·오류·없음 상태.
- 제외: C3 이후(이미 구현), 길찾기 지도 연동(`customer-home.md` D-18 미정 유지), 백엔드 변경, 예약 패널 내부 동작(`reservations.md`).
- 상태: 설계안 1차(임시 결정 포함). 구현을 막는 항목은 §7 참고.
- 이어받는 설계: `customer-home.md` §5.3~§5.6(경로·자리 page 교체·`findById` 추가·로그인 복귀), D-8(entities 만들지 않음). `reservations.md` §2 `ReserveOfferPanel` props, D-1(수량 상한), C-1(이 문서가 닫음). 다른 문서의 번호는 `reservations.md C-1`처럼 파일명과 함께 쓴다.
- 정본: 화면 `../../design-system/screens.md` C2, `wireframe.html` 346~364줄, `content.md` 40줄(취소 가능 문구), `states.md` 55줄(수량 상한), `layout.md` 34~38줄(C1→C2→A1·C3). API `../../reference/catalog.md` §10 할인 상세·§공통 객체 Offer·§17 상품 이미지 조회.
- 백엔드 실재 확인: `backend/src/catalog/presentation/router.py:318~325` `GET /v1/offers/{offer_id}`(`OptionalUser`, 공개), 응답 `schemas.py:233~257` `OfferDetailResponse{offer: OfferResponse, description|null, product_image: string[], pickup_address, latitude|null, longitude|null, notice, cancel_policy{cancellable_until, description}}`. reference §10과 필드가 같다.
- 지킬 규칙: F1~F19(`frontend-invariants`), `layer-architecture` §1~§6, `tdd-workflow` §2.

## 1. 계층 배치와 slice

| FSD 계층 | slice | 이번 변경 | 이유 |
| --- | --- | --- | --- |
| features | `features/offers` | 확장(파일 추가) | `GET /v1/offers/{id}`는 catalog 할인 엔드포인트(`fsd-structure` §1.1). `customer-home.md` §5.4 |
| features | `features/reservations` | 변경 없음(공개 API `ReserveOfferPanel` 사용) | 예약 생성은 reservations 영역 |
| features | `features/auth` | 변경 없음(`useAuth`, `loginRedirectState`, `readFrom` 사용) | 로그인 복귀는 §5.6 방식 그대로 |
| pages | `pages/offer-detail` | 신규 | C2 라우트 하나. offers·reservations·auth 부품 조립 |
| app | `router/routes.tsx`·`router/placeholders.tsx` 수정 | | `customer-home.md` §5.3 한 줄 교체 |
| entities | 만들지 않음 | | page가 offers 결과를 패널 props로 넘기므로 다른 영역이 `Offer`를 직접 읽지 않는다(`customer-home.md` D-8 유지, D-2) |

## 2. 파일 목록과 export

### 2.1 `features/offers` 추가분

**domain** (순수 TypeScript, F6)

| 파일 | 상태 | export |
| --- | --- | --- |
| `domain/offerDetail.ts` | 신규 | `type OfferDetail = { offer: Offer; description: string \| null; imageUrls: string[]; pickupAddress: string; latitude: number \| null; longitude: number \| null; notice: string; cancellableUntil: Date; cancelPolicyText: string }` |
| `domain/offerAvailability.ts` | 신규 | `type UnavailableReason = 'soldOut' \| 'ended' \| 'notStarted' \| 'inactive'`, `type OfferAvailability = { reservable: true } \| { reservable: false; reason: UnavailableReason }`, `offerAvailability(offer: Offer, now: Date): OfferAvailability`, `unavailableMessage(reason: UnavailableReason): string` |
| `domain/offerFormat.ts` | 수정(추가) | `relativeDay(d: Date, now: Date): string`(기존 private `pickupDay`를 이름 바꿔 export, `pickupWindow`가 그대로 사용), `cancelDeadlineText(until: Date, now: Date): string` |
| `domain/detailQuantity.ts` | 신규 | `QUANTITY_PARAM = 'qty'`, `readQuantityParam(search: string): number \| null`, `detailReturnPath(pathname: string, quantity: number): string` |
| `domain/offerRepository.ts` | 수정 | `findById(id: string, signal?: AbortSignal): Promise<OfferDetail>` 추가. 상단 주석 「C2 담당이 findById를 더한다」 삭제 |
| `domain/offerMessages.ts` | 수정(추가) | `OFFER_DETAIL_LOAD_FAILED_MESSAGE`, `OFFER_NOT_FOUND_MESSAGE`, `MAX_PER_RESERVATION_TEXT`, `PRODUCT_IMAGE_PLACEHOLDER`, `PICKUP_TIME_LABEL`, `CANCEL_DEADLINE_LABEL` (값은 §3.3) |

**application**

| 파일 | export |
| --- | --- |
| `application/useOfferDetail.ts` | `type OfferDetailState = { status: 'loading' \| 'success' \| 'notFound' \| 'error'; detail: OfferDetail \| null; retry(): void }`, `useOfferDetail(offerId: string): OfferDetailState` — 컨테이너에서 `OfferRepositoryToken`을 꺼냄(`useNearbyOffers`와 같은 방식) |

**infrastructure**

| 파일 | 상태 | 내용 |
| --- | --- | --- |
| `infrastructure/httpOfferRepository.ts` | 수정 | `findById` 구현. `OfferDetailDto`는 파일 안에서만(F9). `toOffer` 재사용. 이미지 주소 변환 `toImageUrl`(파일 내부, §3.1) |

**presentation**

| 파일 | export |
| --- | --- |
| `presentation/OfferImage.tsx` | `OfferImage({ urls, alt }: { urls: string[]; alt: string })` — 첫 장만 `<img>`, 없거나 로드 실패면 `.ph` |
| `presentation/OfferDetailBody.tsx` | `OfferDetailBody({ detail, now }: { detail: OfferDetail; now: Date })` — `.body` 안 내용(이미지~안내 문구, 와이어프레임 350~357줄). 예약 패널은 포함하지 않음 |
| `presentation/OfferDetailSkeleton.tsx` | `OfferDetailSkeleton()` — `.ph` 이미지 자리 + `.sk` 줄 3개 |

**`index.ts` 추가**: `type OfferDetail`, `type UnavailableReason`, `type OfferAvailability`, `offerAvailability`, `unavailableMessage`, `readQuantityParam`, `detailReturnPath`, `useOfferDetail`, `OfferImage`, `OfferDetailBody`, `OfferDetailSkeleton`, `OFFER_DETAIL_LOAD_FAILED_MESSAGE`, `OFFER_NOT_FOUND_MESSAGE`. 구현체·DTO는 내보내지 않음. `wiring.ts`는 바꾸지 않음(§5.4).

### 2.2 `pages/offer-detail`

| 파일 | export |
| --- | --- |
| `presentation/OfferDetailPage.tsx` | `OfferDetailPage()` |
| `index.ts` | `OfferDetailPage` |

### 2.3 app

| 파일 | 변경 |
| --- | --- |
| `app/router/routes.tsx` | `{ path: ROUTE_PATTERNS.offerDetail, element: <OfferDetailPage /> }`(공개 `CustomerLayout access="public"` 아래 그대로, handle 없음 = 탭 바 없음) + import 한 줄 |
| `app/router/placeholders.tsx` | `OfferDetailPlaceholder` 삭제, 파일 맨 위 TODO `언제:`에서 「C2 구현 시」 삭제 |

reservations 쪽 후속(이 설계 범위 밖, 제안): `ReserveOfferPanel.tsx`의 C-1 TODO 삭제, `pages/checkout`의 D-20 TODO(C3a 취소 후 C2로) 처리 — C-3.

## 3. 동작 규칙

### 3.1 infrastructure: `findById`

- `request<OfferDetailDto>(\`/v1/offers/${encodeURIComponent(id)}\`, { auth: false, signal })`. 공개 API라 토큰을 붙이지 않는다(`customer-home.md` D-19와 같은 이유). 상점주 본인 정지 할인 조회는 C2 대상이 아니다(D-4).
- 매핑: `offer → toOffer`, `description`, `product_image → imageUrls(toImageUrl)`, `pickup_address → pickupAddress`, `latitude`, `longitude`, `notice`, `cancel_policy.cancellable_until → cancellableUntil(Date)`, `cancel_policy.description → cancelPolicyText`.
- `toImageUrl(s)`: `/`로 시작하면(업로드 이미지 `/v1/products/{id}/images/{image_id}`, catalog §17) `${API_BASE_URL}${s}`, 그 밖(외부 URL)은 그대로. 이미지 조회 API를 따로 호출하지 않고 `<img src>`로 쓴다(§17 「화면의 `<img src>`에 서버 주소를 붙여 쓴다」). D-3.
- 오류는 `ApiError` 그대로 throw(404·400 구분은 훅이 함).

### 3.2 domain

**`offerAvailability(offer, now)`** — 판정 순서(앞이 우선):
1. `isSoldOut(offer)` → `soldOut`
2. `offer.status === 'CLOSED' || offer.status === 'SUSPENDED' || offer.salesEnd <= now` → `ended`
3. `!offer.isActive` → `inactive`
4. `offer.status === 'SCHEDULED' || offer.salesStart > now` → `notStarted`
5. 그 외(`ON_SALE`이고 `salesStart ≤ now < salesEnd`) → `{ reservable: true }`
- 마감 시각 정각(`salesEnd == now`)은 `ended`(`salesCountdown`이 `diff <= 0`을 null로 보는 것과 맞춤).
- `SUSPENDED`는 백엔드가 404로 숨기지만(catalog §10) 방어로 `ended` 처리.

**`unavailableMessage(reason)`** (전부 임시, D-6): `soldOut` → `품절됐어요.`, `ended` → `판매가 종료됐어요.`, `inactive` → `지금은 판매하지 않는 상품이에요.`, `notStarted` → `아직 판매 전이에요.`

**`relativeDay(d, now)`**: 같은 로컬 날짜 `오늘`, 다음 날 `내일`, 그 외 `formatMd(d)`(기존 `pickupDay` 규칙 그대로).

**`cancelDeadlineText(until, now)`**: `${relativeDay(until, now)} ${formatHm(until)}까지 (이후 취소 불가)` (`content.md` 40줄, 와이어프레임 355줄). 이미 지났어도 같은 문구(D-7).

**`readQuantityParam(search)`**: `URLSearchParams(search).get('qty')`가 `^[1-9][0-9]*$`이면 정수, 아니면 `null`. 상한 처리는 하지 않는다(패널 `clampQuantity`가 `min(남은 재고, 5)`로 자름, `reservations.md` D-1).

**`detailReturnPath(pathname, quantity)`**: `${pathname}?qty=${quantity}`(`customer-home.md` §5.6 그대로).

### 3.3 화면 구성(`OfferDetailBody` + page)

| 위치 | 내용 | 정본 |
| --- | --- | --- |
| `.bar` | `<Link to={back} aria-label={BACK_LABEL}>←</Link><h1 className="t">{productName}</h1><span className="sp" />`. 로딩·오류·없음일 때 제목은 `할인 상세`(임시 D-8) | wireframe 348, `customer-home.md` §5.5 |
| 이미지 | `OfferImage`: `imageUrls[0]` → `<img alt={productName}>`(`minHeight 170`, 토큰만, F12). 없음·`onError` → `<div className="ph" style={{ minHeight: 170 }}>상품 이미지</div>` | wireframe 350, D-3 |
| 상점 | `<div className="m">{storeName} · {pickupAddress}</div>` | 351 |
| 가격 | `.price`: `<span className="pct">{discountRate}%</span><b>{formatWon(salePrice)}</b><s>{groupDigits(originalPrice)}</s>` | 352 |
| 마감·수량 | `.row`: 판매 가능이면 `<span className="cd">{salesCountdown}</span>` + `<span className="m">남은 {remainingStock}개</span>`. 판매 불가면 카운트다운·남은 수량 대신 `StatusTag`/`.m`로 사유 한 줄(`unavailableMessage`) | 353, screens C2 동작 메모 4 |
| `.box` `.kv` | `픽업 시간` / `pickupWindow(...)`, `취소 가능` / `cancelDeadlineText(...)` | 354~355 |
| 상품 설명 | `description`이 있으면 `.m` 한 줄(와이어프레임에 없음, D-9 임시) | catalog §10 |
| 안내 | `<div className="m">{notice}</div>`(서버 문구, C-2) | 356 |
| 수량 안내 | `<div className="m">한 번에 최대 5개까지 예약할 수 있어요.</div>` (`MAX_PER_RESERVATION_TEXT`) | 357 |
| 예약 영역 | `ReserveOfferPanel`(§3.4). 패널이 사유·오류 줄과 `.cta`를 그림 | 358~360 |

- `cancelPolicyText`(서버 취소 정책 설명, 위약금 언급)는 보이지 않는다. 화면은 `content.md` 문구만 쓴다(C-2, D-7).
- 시계: page에서 `useNow()`(30초)로 `now`를 만들어 Body·`offerAvailability`에 넘긴다. 마감 시각이 지나면 다음 틱에 버튼이 비활성으로 바뀐다.

### 3.4 page 조립(`OfferDetailPage`)

```
offerId = useParams().offerId
state = useOfferDetail(offerId)
auth = useAuth()
now = useNow()
back = readFrom(location.state) ?? ROUTES.home
initialQuantity = readQuantityParam(location.search) ?? undefined
```

- `loading` → `.bar`(제목 「할인 상세」) + `OfferDetailSkeleton`. 패널 없음.
- `error` → `.warn`(D-14)에 `OFFER_DETAIL_LOAD_FAILED_MESSAGE` + 「다시 시도」(`RETRY_LABEL`) → `retry()`. 패널 없음.
- `notFound`(404, 400 잘못된 UUID) → `.warn`(D-14)에 `OFFER_NOT_FOUND_MESSAGE` + 「홈으로」 링크(`ROUTES.home`). 패널 없음. 정지 할인도 여기(발주서 3 확정).
- `success` →  `OfferDetailBody` + 패널:

| `ReserveOfferPanel` prop | 값 |
| --- | --- |
| `offerId` | `detail.offer.id` |
| `unitPrice` | `detail.offer.salePrice` |
| `remainingStock` | `detail.offer.remainingStock` |
| `reservable` | `availability.reservable` |
| `unavailableReason` | 불가면 `unavailableMessage(reason)`, 가능하면 `null` |
| `isLoggedIn` | `auth.state.status === 'authenticated'` |
| `onRequireLogin(q)` | `navigate(ROUTES.login, { state: loginRedirectState('other', detailReturnPath(location.pathname, q), 'reservation') })` |
| `onGoToCheckout(id)` | `navigate(ROUTES.checkout(id))` (`useCallback`으로 고정 — 패널 `useEffect` 의존성) |
| `initialQuantity` | `readQuantityParam(location.search) ?? undefined` |
| `key` | `detail.offer.id` (다른 할인으로 이동하면 수량 상태 초기화) |

- 패널은 `success`에서만 마운트한다. 패널의 `useState` 초기값이 첫 렌더에서만 `clampQuantity(initialQuantity, remainingStock)`을 계산하므로 데이터가 온 뒤 마운트해야 같은 수량이 유지된다.
- 로그인 복귀 후 자동 예약하지 않는다. 수량만 채워진 상태로 돌아오고 사용자가 「예약하고 결제」를 다시 누른다(D-5).
- 로그인 복귀 후 URL의 `?qty=`는 그대로 둔다(D-5). 새로고침해도 같은 수량.
- 로그인·가입 뒤 C2로 돌아오면 `location.state.from`이 없으므로 ← 는 홈(`ROUTES.home`)으로 간다(D-1).
- 세션 확인 중(`auth.state.status === 'loading'`)에는 `isLoggedIn=false`로 넘기되, 그 사이 누르면 A1로 간다. 임시(C-4).

## 4. 흐름

- C1 카드 → C2 (`state.from = '/?sort=…'`) → ← 는 필터 유지된 홈.
- 비로그인 「예약하고 결제」 → A1(`entry: 'reservation'`, `from: /offers/{id}?qty=N`) → 로그인(또는 A2·A3 경유) → `resolvePostLoginPath`가 고객을 `from`으로 → C2가 수량 N(최대 min(재고,5))으로 열림.
- 로그인 「예약하고 결제」 → 201 → C3 `/checkout/{id}`. 409 결제 대기 → 「결제 이어하기」(패널 내부, `reservations.md` §3).

## 5. 결정 표

| ID | 항목 | 값 | 상태 | 근거 | 차단 |
| --- | --- | --- | --- | --- | --- |
| D-1 | ← 뒤로 가기 대상 | `readFrom(location.state) ?? ROUTES.home`. 브라우저 history back은 쓰지 않음(외부·직접 진입 시 앱 밖으로 나가는 것 방지) | 임시 | `customer-home.md` §5.4 안내, screens C2에 정본 없음 | 아니오 |
| D-2 | entities/offer | 만들지 않음 | 확정 | `customer-home.md` D-8 확정 유지, page 조립 | 아니오 |
| D-3 | 이미지 표시 | `product_image[0]` 한 장만 `<img src>`. `/`로 시작하면 `API_BASE_URL` 접두, 외부 URL은 그대로. 빈 배열·로드 실패 → `.ph` 「상품 이미지」. 여러 장 슬라이드 없음 | 임시 | catalog §10·§17, wireframe 350(한 칸), open-issues O12(사진 1장 규칙) | 아니오 |
| D-4 | 상세 요청 인증 | 토큰 없이(`auth: false`) | 임시 | 공개 API, `customer-home.md` D-19 | 아니오 |
| D-5 | 로그인 복귀 수량 | `from`에 `?qty=N`(§5.6). C2가 `readQuantityParam` → 패널 `initialQuantity`, 상한은 패널이 자름. 자동 예약 안 함, 쿼리 지우지 않음 | 임시(방식은 `customer-home.md` §5.6 안내, 자동 예약 여부·쿼리 정리는 설계자 값) | screens C2 "같은 수량으로 이어감" | 아니오 |
| D-6 | 판매 불가 사유 문구 4종 | §3.2 | 임시 | screens C2 "버튼 비활성 + 사유", 문구 정본 없음 | 아니오 |
| D-7 | 취소 가능 표기 | `content.md` 40줄 문구를 프론트가 `cancellable_until`로 만듦. 서버 `cancel_policy.description`은 숨김. 시각이 지나도 같은 문구 | 임시 | content.md 40, wireframe 457 이슈 23 | 아니오 |
| D-8 | 로딩·오류·없음 시 AppBar 제목 / 문구 | 제목 `할인 상세`, 오류 `할인 정보를 불러오지 못했어요.`, 없음 `할인을 찾을 수 없어요.`, 버튼 `다시 시도`·`홈으로` | 임시 | E1·states.md 공통, C2 전용 문구 없음 | 아니오 |
| D-9 | 상품 설명(`description`) 표시 | 있으면 안내 문구 위에 `.m` 한 줄 | 임시 | 와이어프레임에 없음 | 아니오 |
| D-10 | 상세 화면 시계 | `useNow()` 30초 | 임시 | `customer-home.md` D-13 같은 값 | 아니오 |
| D-11 | 수량 상한 | min(남은 재고, 5) — 패널(`reservations.md` D-1)이 처리 | 확정 | 발주서 3 | 아니오 |
| D-12 | 경로·셸 | `/offers/:offerId`, `CustomerLayout access="public"`, 탭 바 없음 | 확정 | 발주서 3, `customer-home.md` §5.3 | 아니오 |
| D-13 | 정지 할인 | 404 → 없음 상태 | 확정 | 발주서 3, catalog §10 | 아니오 |
| D-14 | 없음·오류 상태 표시 부품 | shared에 `EmptyState`가 없어 `.body` 안 `.warn` 문구 + `.btn`(없음: 「홈으로」 `Link`, 오류: 「다시 시도」 `button`)으로 그림. §3.4의 `EmptyState`/`Notice` 대신 | 확정(구현 차이 승인) | `OfferDetailPage.tsx`, fe-developer 보고 | 아니오 |
| D-15 | 「홈으로」·로딩 제목 문구 위치 | `offerMessages.ts`가 아니라 page 상수 `GO_HOME_LABEL`·`FALLBACK_TITLE`(D-8 TODO 주석과 함께). 문구 값 자체는 D-8 임시 그대로 | 확정(구현 차이 승인) | `OfferDetailPage.tsx` 상단 | 아니오 |
| D-16 | 400/404 판정 방식 | `useOfferDetail`이 `ApiError instanceof` 대신 오류 객체의 `status`를 구조로 읽음(application이 `shared/api`를 import하지 않도록, F5) | 확정(구현 차이 승인) | `useOfferDetail.ts` `isNotFound` | 아니오 |
| D-17 | `?qty=` 상한 처리 위치 | `readQuantityParam`은 양의 정수만 걸러 내고 상한은 자르지 않음. 상한은 패널 `clampQuantity`(min(남은 재고, 5))가 자름(§3.2와 같음, D-11) | 확정(구현 차이 승인) | `detailQuantity.ts`, `reservations.md` D-1 | 아니오 |

## 6. 정합 이슈

| ID | 내용 | 근거 | 처리 |
| --- | --- | --- | --- |
| C-1 | `reservations.md C-1` 닫음: 패널 props는 §3.4 표로 확정 제안. 단 `cancel_policy`는 패널에 넘기지 않음(패널 props에 없음). `ReserveOfferPanel.tsx`의 C-1 TODO 삭제는 reservations 담당 | `ReserveOfferPanel.tsx:26~28` | 사용자 확인 후 reservations.md C-1 해결 표시(이 설계 쓰기 범위 밖) |
| C-2 | 문구 불일치: 서버 `notice`("…예약 확인 코드를 보여주세요…")와 와이어프레임 356줄("…예약 코드를 보여 주세요. 시간이 지나면 수령할 수 없어요.")이 다름. 서버 `cancel_policy.description`은 위약금 언급, 디자인은 "이후 취소 불가"(wireframe 457 이슈 23). 이 설계는 `notice`는 서버 값, 취소는 `content.md` 문구(D-7) | catalog §10 응답 예시, wireframe 356·457 | 질문 Q-1 |
| C-3 | C3a 취소 후 이동이 홈 임시(`reservations.md` D-20, `pages/checkout` TODO). C2 경로가 생겼으므로 `ROUTES.offerDetail(offerId)`로 바꿀 수 있음. 범위 밖 | `reservations.md` D-20 | reservations 담당에 제안 |
| C-4 | 세션 확인 중(`loading`)에 「예약하고 결제」를 누르면 비로그인으로 취급돼 A1로 감. 패널 props에 `loading` 표현이 없음 | `ReserveOfferPanel.tsx` props | 질문 Q-3 |
| C-5 | 패널은 사유(`.m`)·오류(`.err`)를 `.cta` 바깥 형제로 그림. 와이어프레임 358줄은 오류 box(`.box` 강조 테두리 + 「결제 이어하기」 sm 버튼)를 `.body` 안에 둠. page는 패널을 `.body` 다음에 놓으므로 사유·오류 줄이 `.body`와 `.cta` 사이에 옴 | `ReserveOfferPanel.tsx:56~66`, wireframe 358 | 표시 차이로 보고(패널 마크업은 reservations 소유) |
| C-6 | `notStarted`(예정) 할인은 홈 목록(기본 `ON_SALE`)에서 안 보이지만 직접 링크로 들어올 수 있음. 판매 시작 전 표시 정본 없음 | catalog §공통 객체 status | D-6 임시 |

## 7. 차단 이슈와 질문 목록

차단 이슈: 없음(모든 미결은 임시값으로 구현 가능, 주석으로 추적).

질문(사용자 결정):
- Q-1 (C-2) 안내 문구는 서버 `notice`를 그대로 쓸지, `content.md`/와이어프레임 문구를 프론트 상수로 쓸지. 취소 정책 서버 문구(위약금)를 백엔드에서 고칠지(이슈 23).
- Q-2 (D-1) ← 대상: `from` 없으면 홈으로 충분한지, history back을 원하는지.
- Q-3 (C-4) 세션 확인 중 예약 버튼을 비활성할지(패널 props 추가 필요 → reservations 변경).
- Q-4 (D-5) 로그인 복귀 후 자동으로 예약을 이어 만들지, 수량만 채워 둘지.
- Q-5 (D-3) 이미지 여러 장일 때 슬라이드가 필요한지.
- Q-6 (D-6·D-8) 사유·오류·없음 문구 확정.

## 8. 골격 (`tdd-workflow` §3)

Red 전에 export 이름·시그니처만 있는 빈 파일: `domain/offerDetail.ts`, `domain/offerAvailability.ts`, `domain/detailQuantity.ts`, `offerFormat.ts`의 `relativeDay`·`cancelDeadlineText`, `offerRepository.ts`의 `findById`, `application/useOfferDetail.ts`, presentation 3개, `pages/offer-detail`. `tests/support`의 가짜 `OfferRepository`에 `findById` 추가.

## 9. 테스트 목록 (위치 `tests/features/offers/`, `tests/pages/offer-detail/`)

### 9.1 domain

`offerAvailability` (`now` = 2026-11-04 17:30 로컬, 기본 offer: ON_SALE, isActive, remaining 3, salesStart 16:00, salesEnd 18:00)
1. 기본 → `{ reservable: true }`
2. `remainingStock 0` → `soldOut`; `isSoldOut true` → `soldOut`; `status SOLD_OUT` → `soldOut`
3. 품절 + `CLOSED` → `soldOut`(품절 우선)
4. `status CLOSED` → `ended`; `SUSPENDED` → `ended`
5. `salesEnd == now`(정각) → `ended`; `salesEnd = now + 1ms` → reservable
6. `isActive false` → `inactive`
7. `status SCHEDULED` → `notStarted`; `ON_SALE`이지만 `salesStart = now + 1분` → `notStarted`
8. `unavailableMessage` 4종이 §3.2 문자열

`relativeDay` / `cancelDeadlineText`
9. 같은 날 17:00 → `오늘 17:00까지 (이후 취소 불가)`
10. 다음 날 09:05 → `내일 09:05까지 (이후 취소 불가)`
11. 이틀 뒤 → `11/06 …`(formatMd)
12. 이미 지난 시각도 같은 형식
13. `pickupWindow` 기존 테스트가 그대로 통과(리팩터 회귀)

`readQuantityParam` / `detailReturnPath`
14. `?qty=2` → 2, `?qty=5` → 5, `?qty=9` → 9(자르지 않음)
15. `?qty=0`, `?qty=-1`, `?qty=abc`, `?qty=1.5`, `?qty=`, `''`, `?other=1` → null
16. `detailReturnPath('/offers/abc', 3)` → `/offers/abc?qty=3`

### 9.2 infrastructure (`httpOfferRepository.findById`, fetch 가짜)
17. `GET {API_BASE_URL}/v1/offers/{id}`, Authorization 헤더 없음
18. 응답 매핑: `cancellableUntil` Date, `pickupAddress`, `notice`, `description` null 유지, `offer` 17필드 매핑
19. `product_image` `['/v1/products/p/images/i']` → `API_BASE_URL + 경로`, `['https://x/a.jpg']` → 그대로, `[]` → `[]`
20. 404 → `ApiError(status 404)` throw

### 9.3 application (`useOfferDetail`, 가짜 repo)
21. 마운트 → `loading` → 성공 `success` + detail
22. 404 → `notFound`; 400 → `notFound`
23. 500·네트워크 → `error`; `retry()` → `loading` → `success`
24. 언마운트 시 signal abort, abort 후 상태 갱신 없음
25. `offerId` 바뀌면 이전 요청 abort, 새 id로 다시 요청

### 9.4 presentation
`OfferImage`
26. urls 있으면 `img`(alt=상품명, src=첫 장)
27. urls 빈 배열 → `.ph` 「상품 이미지」, `img` 없음
28. `img` `error` 이벤트 → `.ph`로 바뀜

`OfferDetailBody`
29. 상점명·주소 `망원베이커리 · 서울시 …`, `50%`·`6,000원`·`12,000`(취소선)
30. 판매 가능 → `판매 마감 30분 전`, `남은 3개`
31. 품절 → 카운트다운·남은 수량 없음, `품절됐어요.` 표시
32. `픽업 시간` `오늘 18:00–20:00`, `취소 가능` `오늘 17:00까지 (이후 취소 불가)`
33. `notice` 텍스트, `한 번에 최대 5개까지 예약할 수 있어요.`
34. `description` 있으면 표시, null이면 없음
35. `cancelPolicyText`는 표시되지 않음

### 9.5 page (`OfferDetailPage`, MemoryRouter + 컨테이너 가짜, `routes` 전체 렌더)
36. 로딩 → 스켈레톤, 제목 `할인 상세`, 예약 버튼 없음
37. 성공 → h1이 상품명, 예약 버튼 `예약하고 결제 6,000원`(수량 1)
38. 오류 → 오류 문구 + `다시 시도` 클릭 시 재요청 후 성공 표시
39. 404 → `할인을 찾을 수 없어요.` + `홈으로` 링크(`/`)
40. ← 링크: `state.from = '/?sort=price'`로 들어오면 `/?sort=price`, state 없으면 `/`, `from = '//evil.com'`이면 `/`
41. 품절 → 예약 버튼 비활성, 사유 `품절됐어요.`
42. 비로그인 + 수량 2로 + → 예약 클릭 → `/login`으로 이동, location.state = `{ from: '/offers/{id}?qty=2', entry: 'reservation' }`
43. `/offers/{id}?qty=2`로 진입(로그인) → 스테퍼 2, 버튼 `예약하고 결제 12,000원`
44. `?qty=9`, 남은 재고 3 → 스테퍼 3(패널 clamp)
45. 로그인 + 예약 성공(201, id r1) → `/checkout/r1`
46. 시계 진행으로 `salesEnd` 지나면(가짜 타이머 30초) 버튼 비활성 + `판매가 종료됐어요.`
47. 라우트: `/offers/:id`가 공개(비로그인 접근 가능), 탭 바 없음
48. A1 왕복 통합: 비로그인 C2 → 예약(수량 2) → A1에 `예약을 이어가려면 로그인하세요.` → 로그인 성공 → `/offers/{id}?qty=2`, 스테퍼 2

정본이 없어 목록에서 뺀 것: 자동 예약(Q-4), 세션 확인 중 버튼 상태(Q-3), 이미지 슬라이드(Q-5).

## 10. 남길 작업 주석 (`code-annotations`, F19)

| 위치 | 태그 | 왜 | 언제 |
| --- | --- | --- | --- |
| `domain/offerAvailability.ts` `unavailableMessage` | TODO | 사유 문구 정본 없음 (offers.md D-6) | 결정 후 (디자인 시스템: content.md 문구 확정) |
| `presentation/OfferImage.tsx` | TODO | 첫 장만 표시, 슬라이드 미정 (offers.md D-3, Q-5) | 결정 후 (사용자: 여러 장 표시) |
| `presentation/OfferDetailBody.tsx` notice | TODO | 서버 notice와 와이어프레임 문구 다름, 취소 정책 서버 문구 숨김 (offers.md C-2, D-7) | 결정 후 (사용자: 안내·취소 문구 정본) |
| `pages/offer-detail/.../OfferDetailPage.tsx` ← | TODO | from 없을 때 홈으로 (offers.md D-1) | 결정 후 (사용자: 뒤로 가기 대상) |
| 같은 파일 `isLoggedIn` | TODO | 세션 확인 중 비로그인 취급 (offers.md C-4) | 결정 후 (사용자: 확인 중 버튼 상태) |
| 같은 파일 `initialQuantity` | TODO | 복귀 시 자동 예약 안 함·qty 쿼리 유지 (offers.md D-5) | 결정 후 (사용자: 자동 예약 여부) |
| `offerMessages.ts` 오류·없음 문구 | TODO | C2 전용 문구 정본 없음 (offers.md D-8) | 결정 후 (디자인 시스템) |

## 11. 변경 이력

- 2026-11-11 1차 작성(C2 전체, `reservations.md` C-1 대응).
- 2026-11-11 구조 점검 후 구현 차이 반영: D-14(없음·오류 `.warn`+`.btn`), D-15(「홈으로」·로딩 제목 page 상수), D-16(400/404 `status` 구조 판정, F5), D-17(`?qty=` 상한은 패널이 자름) 추가, §3.4 `EmptyState`/`Notice` 표기를 `.warn`으로 고침.
