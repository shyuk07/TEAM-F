# offers 영역 확장 설계안 (상점주 O2 할인 관리 · O3 할인 등록/다시 올리기 · O5 판매 중단 · O9 할인 수정 · O10 재고 조정)

- 상태: **설계안 1차 (2026-11-11)**. 사용자가 정한 값은 없다. 이 문서의 D-번호는 모두 "임시"다. TDD는 사용자 지시로 이번 차수 생략이라 `tdd-workflow` §2 테스트 목록 절은 쓰지 않는다(구현 뒤 완료 게이트 `frontend-invariants` §6은 그대로 적용).
- 대상 slice: `features/offers`(확장), `pages/owner-offers`(O2·O10), `pages/offer-new`(O3), `pages/offer-edit`(O9), `pages/offer-deactivate`(O5), `shared`(ui·lib 추가), `app`(라우트·container 테스트)
- 기존 C1 설계 `customer-home.md`와의 관계: `features/offers`의 C1 파일(`OfferCard`, `useNearbyOffers`, `OfferRepository.findNearby`, `homeFilter` 등)은 **바꾸지 않고 파일만 더한다**(§1.2). C2 담당이 더할 `findById`·`useOfferDetail`과 이름이 겹치지 않게 했다(D-3, C-1).
- 정본: `screens.md` O2(355~373줄)·O3(374~409)·O5(410~420)·O9(451~466)·O10(467~478), `wireframe.html` O2(611~639)·O3(640~668)·O5(691~706)·O9(746~769)·O10(770~788), `layout.md` 화면 연결(50~56줄), `states.md`(할인 상태 20~23줄, 기본값 58줄), `open-issues.md` O5·O12, `../../reference/catalog.md` §7·§9·§11~§14, 백엔드 `catalog/presentation/router.py`·`schemas.py`, `catalog/application/service.py`, `catalog/domain/discount_offer.py`·`exceptions.py`.

## 0. 백엔드 실재 확인 (`frontend-orchestration.md` §6)

| 항목 | 확인 위치 | 결과 |
| --- | --- | --- |
| `GET /v1/stores/{id}/offers?status=…&page&size` (O2 목록). `status` 반복 가능, 생략하면 SCHEDULED·ON_SALE·SOLD_OUT(상점주는 SUSPENDED 포함), CLOSED는 명시해야 나옴. size 1~100 기본 20. 응답 `{items: OfferResponse[], page, size, total}` | `router.py:179~205`, `schemas.py:171~175` | 명세 §9와 같다 |
| `OfferResponse`: `id, product_id, store_id, store_name, product_name, original_price, sale_price, discount_rate, initial_stock, remaining_stock, is_sold_out, sales_start/end, pickup_start/end, status, is_active` | `schemas.py:126~145` | 기존 `Offer` 타입(`features/offers/domain/offer.ts`)과 필드가 같다. **예약 수 필드는 없다**(C-3) |
| `POST /v1/products/{id}/offers` 201 (O3). 본문 `sale_price, initial_stock, sales_start?(기본 지금), sales_end, pickup_start, pickup_end`, 시각은 시간대 필수 | `router.py:305~315`, `schemas.py:81~95` | 명세 §7과 같다 |
| `POST /v1/offers/{id}/relist` 201 (O3 다시 올리기). 본문은 등록과 같다. **`is_active=false`인 할인은 400 `OFFER_CLOSED`("이미 중단된 할인은 재등록할 수 없습니다.")**, 정지된 할인은 `OFFER_SUSPENDED`. 기존 할인은 닫히고(`close`) 새 할인이 생긴다 | `router.py:359~367`, `service.py:353~377`, `discount_offer.py:277~280` | 명세 §13과 같다. 화면 명세와 부딪친다(C-2) |
| `PATCH /v1/offers/{id}` (O9). 보낸 필드만. `null` 금지, `is_active`는 단독. 예약이 있으면 400 `OFFER_HAS_RESERVATIONS`, 종료·중단된 할인은 400 `OFFER_CLOSED`. `initial_stock`을 바꾸면 `remaining_stock`도 같은 만큼 바뀌고 "현재까지 줄어든 수량"(`initial − remaining`)보다 작게는 400 | `router.py:328~337`, `schemas.py:97~123`, `discount_offer.py:320~350`, 명세 §11 | 명세와 같다. 예약 유무는 **응답에 없고 PATCH를 보내 봐야 안다**(C-3) |
| `POST /v1/offers/{id}/deactivate {reason(1~200), cancel_reservations=false}` 200 → `{offer, cancelled_reservation_count}` (O5). 이미 중단된 할인은 400 `OFFER_CLOSED`, 픽업 완료 예약이 있으면 일괄 취소 400 `PICKED_UP_RESERVATION_EXISTS`, 판매가 끝난 할인은 `OFFER_ENDED` | `router.py:340~357`, `schemas.py:204~225`, `exceptions.py` | 명세 §12와 같다 |
| `POST /v1/offers/{id}/stock-adjustments {amount(0 제외), reason?(≤200)}` 200 → `{offer_id, initial_stock, remaining_stock, is_sold_out, status, log_id}` (O10). 0은 400, 중단된 할인은 400 `OFFER_CLOSED`, 남은 재고보다 많이 빼면 400 `INSUFFICIENT_STOCK`, `initial_stock + amount > 9999`이면 400 | `router.py:372~381`, `discount_offer.py:378~392`, `exceptions.py:70~76` | 명세 §14와 같다. 더하기는 "최초 수량"도 같이 늘어난다(재고 입고) |
| `GET /v1/offers/{id}` → `OfferDetailResponse{offer, description, product_image, pickup_address, …}` 공개. 정지된 할인은 상점주 토큰이면 조회 | `router.py:318~325`, 명세 §10 | O9·O3(다시 올리기)·O5가 새로고침 진입(딥링크)에서 쓴다(D-3) |
| 공통 `error_code`: `STORE_SUSPENDED`, `STORE_CLOSED`, `PRODUCT_INACTIVE`, `OFFER_ALREADY_OPEN`, `OFFER_SUSPENDED`, `VALIDATION_ERROR`, `DATA_INCONSISTENT`(500, 일괄 취소 중 데이터 불일치) | `domain/exceptions.py:30~170`, `router.py:350~355` | 화면 분기는 `errorCode`(F11) |

## 1. slice 목록과 계층

| 계층 | slice | 대응 화면 | 안에 두는 계층 |
| --- | --- | --- | --- |
| `shared` | `ui`(`Chip`, `Stepper` 추가), `lib`(`routes` 경로 2개, `useAppWide` 추가) | O2~O10 | (4계층 없음, F3) |
| `features` | `offers`(기존, 확장) | O2·O3·O5·O9·O10 | domain, application, infrastructure, presentation, `wiring.ts` |
| `pages` | `owner-offers` | O2 + O10(시트·우측 패널) | presentation |
| `pages` | `offer-new` | O3 | presentation |
| `pages` | `offer-edit` | O9 | presentation |
| `pages` | `offer-deactivate` | O5 | presentation |
| `app` | `router/routes.tsx`, `router/placeholders.tsx`, `container.ts`(바꿀 일 없음) | | |

- **entities는 만들지 않는다**(D-1). `Offer`는 `features/offers/domain`에 그대로 둔다(`customer-home.md` D-8). 두 번째 영역이 `Offer`가 필요해지는 시점은 §6 질문 Q-6.
- 상품 정보(O3의 "상품 *" 선택, 정가)는 `entities/product`(`Product`, `ProductRepositoryToken`)를 쓴다. 구현체는 `features/products`가 이미 등록한다(`products.md` §1.1). `features/offers`는 `features/products`를 import하지 않는다(F1).
- 상점 ID는 page가 `useOwnerStore().id`(entities/store)로 읽어 훅에 인자로 넘긴다(`products.md` §1과 같은 방식).
- 의존: `pages → features/offers·entities/product·entities/store·widgets/owner-nav·shared`. `features/offers → entities/product(토큰·타입)·shared`.

### 1.1 라우트 (D-4)

| 화면 | 경로 | 비고 |
| --- | --- | --- |
| O2 | `/owner/offers` (`ROUTES.ownerOffers`, 기존, 탭 바 있음) | 자리 page 교체 |
| O3 | `/owner/offers/new` (`ROUTES.ownerOfferNew`, 기존). 쿼리 `productId`(`ownerOfferNewFor`, 기존) 또는 `relistFrom=<offerId>`(새 `ROUTES.ownerOfferRelist(offerId)`) | 자리 page 교체. 탭 바 없음 |
| O9 | `/owner/offers/:offerId/edit` (새 `ROUTES.ownerOfferEdit(id)`, `ROUTE_PATTERNS.ownerOfferEdit`) | 탭 바 없음 |
| O5 | `/owner/offers/:offerId/deactivate` (새 `ROUTES.ownerOfferDeactivate(id)`, `ROUTE_PATTERNS.ownerOfferDeactivate`) | 탭 바 없음. O7(`/owner/store/close`)처럼 확인 화면은 라우트 |
| O10 | 라우트 없음. O2 안의 상태(`adjusting: Offer \| null`) | 모바일 `Overlay` 바텀시트, PC(앱 폭 720px 이상)는 O2 우측 패널 |

- 세 경로 모두 기존 `OwnerLayout` 아래에 한 줄씩 더한다. `/owner/offers/new`와 `/:offerId/edit`는 세그먼트가 달라 순서가 상관없다.
- 이동: O2 수정 → O9, 판매 중단 → O5, 다시 올리기 → O3(`relistFrom`), "+ 할인 등록" → O3, 재고 조정 → O10. O9 「판매 중단 (O5)」 → O5. 성공(O3 등록·O9 저장·O5 중단) 뒤 `ROUTES.ownerOffers`로 `replace`가 아닌 `navigate`. 취소·← 는 `ROUTES.ownerOffers`.
- 가드: 상점 유무 가드(`OwnerStoreGate`)와 상점주 가드(`OwnerLayout`)를 그대로 쓴다. 새 가드 없음.

### 1.2 기존 C1 파일과 겹침 (충돌 금지)

| 기존 파일 | 이번 변경 |
| --- | --- |
| `domain/offer.ts` | 바꾸지 않음. (상단 TODO "상품 정보가 entities/product와 겹침 … 언제: O3 구현 시"는 D-12로 처리) |
| `domain/offerRepository.ts` | `findNearby`를 두고 **메서드 2개를 더함**(`findByStore`, `findOfferById`). C2 담당이 `findById`를 더할 자리는 비워 둔다 |
| `infrastructure/httpOfferRepository.ts` | `OfferDto`·`toOffer`·`toStatus`를 새 `infrastructure/offerDto.ts`로 **옮기고**(파일 내용 변경 없음) 두 메서드를 더한다. `findNearby` 동작 불변 |
| `application/tokens.ts` | `OfferCommandsToken` 한 줄 추가. `OfferRepositoryToken`·`LocationProviderToken` 불변 |
| `wiring.ts` | `bind(OfferCommandsToken, new HttpOfferCommands())` 한 줄 추가 |
| `index.ts` | export 추가만(§4) |
| `domain/offerFormat.ts` | 바꾸지 않음. `salesCountdown`·`pickupWindow`·`formatWon`을 O2 행이 재사용 |

## 2. 파일 목록과 export (`features/offers` 추가분)

### 2.1 domain

| 파일 | export |
| --- | --- |
| `ownerOffer.ts` | `OWNER_FILTERS`(`['ON_SALE','SCHEDULED','SOLD_OUT','CLOSED']`와 라벨), `type OwnerFilter`, `ownerStatusTag(offer): {label, tone}`, `ownerRowActions(offer, now): OwnerRowAction[]`, `countByFilter(offers): {onSale, scheduled, soldOut}`, `matchesFilter(offer, filter)`, `ownerRowSummary(offer, now): {title, meta, countdown}` |
| `offerDraft.ts` | `type OfferDraft`, `type SalesStart = 'now' \| Date`, `QUICK_PICKS`(30·60·120·180분), `defaultDraft(now, base?)`, `applyQuickPick(draft, minutes, now)`, `pickupLeadMinutes(draft, now)`, `cancelDeadline(draft)`, `isCancelBlocked(draft, now)`, `quickPickLabel(minutes)`, `validateDraft(draft, originalPrice, now): DraftIssue[]`, `toCreateInput(draft): NewOffer` |
| `offerEdit.ts` | `type OfferEditValues`, `quantityFloor(offer)`, `diffOfferChanges(offer, values): OfferChanges`, `hasChanges(changes)`, `isEditable(offer, now)` |
| `stockAdjustment.ts` | `type StockMode = 'subtract' \| 'add'`, `STOCK_REASON_MAX = 200`, `STOCK_MAX = 9999`, `amountBounds(offer, mode): {min, max}`, `signedAmount(mode, amount)`, `stockAfter(offer, mode, amount)`, `validateStockAdjust(offer, mode, amount, reason): StockIssue \| null` |
| `deactivation.ts` | `DEACTIVATE_REASON_MAX = 200`, `type DeactivateInput = {reason, cancelReservations}`, `validateDeactivate(input): 'reason-empty' \| 'reason-too-long' \| null` |
| `offerCommands.ts` | 포트 `OfferCommands`(§3), 타입 `NewOffer`, `OfferChanges`, `StockAdjustResult`, `DeactivateResult` |
| `ownerOfferMessages.ts` | 정본 문구 상수와 임시 문구 상수(§5), `ownerOfferErrorMessage(info: ErrorInfo): string` |

규칙(F7: 모두 domain 함수):

- `ownerStatusTag`: `states.md` 할인 표. ON_SALE → 「판매 중」(ok), SCHEDULED → 「판매 예정」(`—`, tone 없음), SOLD_OUT → 「품절」(mute), CLOSED → 「판매 종료」(mute). SUSPENDED는 정본 문구가 없다(Q-3). 임시로 「판매 종료」(hot)로 그린다.
- `ownerRowActions(offer, now)` (D-6, 와이어프레임 O2 + 백엔드 규칙):
  - `status` ON_SALE·SCHEDULED·SOLD_OUT 이고 `isActive` → `['edit','adjust','deactivate']` (SOLD_OUT에서는 `adjust`가 「더하기」만 쓸모 있지만 버튼은 둔다).
  - `status` CLOSED 이고 `isActive`(마감 시각이 지나 종료) → `['relist']`.
  - `status` CLOSED 이고 `!isActive`(판매 중단) → **`['relist']`**. 백엔드는 `/relist`를 거절하므로 O3가 등록 API로 대신 채운다(D-7, C-2).
  - `status` SUSPENDED → `[]` (모든 조작이 `OFFER_SUSPENDED`로 400).
- `defaultDraft(now, base?)` (`states.md` 58줄): `salesStart = 'now'`, `pickupStart = now + 120분`, `salesEnd = pickupStart`, `pickupEnd = pickupStart + 120분`. `base`(다시 올리기)가 있으면 `salePrice`·`initialStock`만 가져오고 시각은 새 기본값.
- `applyQuickPick(draft, m, now)`: `pickupStart = now + m분`, `salesEnd = pickupStart`, `pickupEnd = pickupStart + 120분`, `salesStart = 'now'`. 선택한 칩 값 `m`은 `draft.quickPick`에 기억하고, 시각을 직접 고치면 `'custom'`.
- `pickupLeadMinutes(draft, now) = floor((pickupStart − now) / 60000)`. `isCancelBlocked`: `pickupLeadMinutes ≤ 60` (「1시간 이하」, 경계 60분 정각 포함 = 경고. `screens.md` O3 "1시간 이하를 고르면"). `cancelDeadline = pickupStart − 60분`(`catalog.md` §10 `cancellable_until`과 같은 기준).
- `validateDraft`: `0 < salePrice < originalPrice`, `salePrice`·`initialStock`은 정수, `1 ≤ initialStock ≤ 9999`, `salesEnd > (salesStart === 'now' ? now : salesStart)`, `pickupEnd > salesEnd`(명세 §7), `pickupEnd > pickupStart`. 어기면 `DraftIssue` 코드를 돌려주고, 저장 버튼 비활성에만 쓴다(문구는 §5 Q-4). 경계: `salePrice = originalPrice`(무효), `salePrice = originalPrice − 1`(유효), `initialStock` 0·1·9999·10000, `pickupEnd = salesEnd`(무효).
- `toCreateInput`: `salesStart === 'now'`이면 `sales_start`를 **보내지 않는다**(서버가 현재 시각, 시계 어긋남 방지. D-8).
- `quantityFloor(offer) = initialStock − remainingStock`, 최소 1(스텝퍼 최솟값 = 이미 줄어든 수. `screens.md` O9 "이미 팔린 수보다 작게 못 줄임" = 백엔드 `initial − remaining`). 경계: 줄어든 수 0 → 최솟값 1, 줄어든 수 3 → 3.
- `diffOfferChanges`: 바뀐 필드만 담는다(`screens.md` O9 "바꾼 값만 보냄"). `isActive`는 다루지 않는다. 변경 0이면 저장 버튼 비활성.
- `amountBounds(offer, mode)`: subtract → `{min: 1, max: remainingStock}`, add → `{min: 1, max: 9999 − initialStock}`. `max < min`이면 그 모드의 「적용」 비활성(subtract는 남은 재고 0, add는 최초 수량 9999). `signedAmount`: subtract → `−n`, add → `+n`. `stockAfter` = `remaining + signedAmount`. `validateStockAdjust`: `n < 1` → `'amount-zero'`, subtract이고 `n > remaining` → `'over-remaining'`(화면 문구 「남은 재고보다 많이 뺄 수 없어요.」), add이고 `initial + n > 9999` → `'over-max'`, 사유 200자 초과 → `'reason-too-long'`.
- `validateDeactivate`: 사유를 `trim`한 뒤 1~200자(백엔드 `min_length=1, max_length=200`, 공백만은 서버가 400이라고 명세 §12). 경계: 공백만, 200자, 201자.

### 2.2 application

| 파일 | export |
| --- | --- |
| `tokens.ts`(변경) | `OfferCommandsToken` 추가 |
| `useOwnerOffers.ts` | `useOwnerOffers(storeId): {status, openOffers, closedOffers, counts, filter, setFilter, loadClosed, reload}`. 첫 요청 `findByStore(storeId, [SCHEDULED,ON_SALE,SOLD_OUT,SUSPENDED], 1, 100)`, 「판매 종료」 칩을 처음 고르면 `[CLOSED]` 20개씩 이어 붙임(D-5) |
| `useOwnerOffer.ts` | `useOwnerOffer(offerId): {status:'loading'\|'success'\|'error', offer, failure, reload}` (`findOfferById`) |
| `useSellableProducts.ts` | `useSellableProducts(storeId): {status, products}`. `ProductRepositoryToken.findByStore`에서 `isActive`인 것만(domain `selectSellable`) |
| `createOffer.ts` | `createOffer(deps:{commands}, input:{mode:'new'\|'relist'\|'refill', productId, sourceOfferId?, draft, now})` — mode에 따라 `register`/`relist` 선택(D-7) |
| `useCreateOffer.ts` | `{submit(), status, errorMessage, errorCode}` |
| `saveOffer.ts` / `useSaveOffer.ts` | 변경 0이면 호출 안 함. 오류코드 `OFFER_HAS_RESERVATIONS`는 `locked`로 올려 보냄 |
| `deactivateOffer.ts` / `useDeactivateOffer.ts` | `validateDeactivate` 뒤 `commands.deactivate` |
| `adjustStock.ts` / `useAdjustStock.ts` | `validateStockAdjust` 뒤 `commands.adjustStock`. 성공하면 호출자가 목록을 `reload()` |
| `useOfferRun.ts` | `useProductRun`(`features/products`)과 같은 제출 흐름(중복 제출 방지, 언마운트 abort, 오류 코드·문구). 영역끼리 import 금지라 **복사**한다(D-9) |
| `useOpenOfferCount.ts` | `useOpenOfferCount(storeId): {status, count}` — O7이 쓸 수 있는 읽기 훅(§6 Q-5). `findByStore(storeId,[SCHEDULED,ON_SALE,SOLD_OUT,SUSPENDED],1,1).total` |

- 훅은 `useDep(OfferRepositoryToken | OfferCommandsToken | ProductRepositoryToken)`만 쓴다(F18). 효과 안의 요청은 `AbortController`로 정리한다(F10).
- 로딩·에러·빈 상태를 훅이 함께 돌려준다. 빈 = 선택한 칩에 해당하는 할인 0건.

### 2.3 infrastructure

| 파일 | 내용 |
| --- | --- |
| `offerDto.ts`(이동) | `OfferDto`, `toOffer`, `toStatus`(기존 `httpOfferRepository.ts`에서 이동, 내용 동일) |
| `httpOfferRepository.ts`(변경) | `findByStore`, `findOfferById` 추가 |
| `httpOfferCommands.ts`(신규) | `HttpOfferCommands implements OfferCommands` |

| 메서드 | 요청 | DTO ↔ domain |
| --- | --- | --- |
| `findByStore(storeId, statuses, page, size)` | `GET /v1/stores/{id}/offers?status=A&status=B&page=&size=` | `{items,page,size,total}` → `OfferPage`형 `{items: Offer[], page, size, total}`. C1의 `OfferPage`는 `NearbyOffer[]`라 **새 타입 `OfferList`**를 쓴다(D-3) |
| `findOfferById(id)` | `GET /v1/offers/{id}` | 응답 `offer`만 `toOffer`로 변환(나머지 필드는 버림) |
| `register(productId, input)` | `POST /v1/products/{id}/offers` | `sale_price, initial_stock, sales_start?, sales_end, pickup_start, pickup_end`(ISO 8601, `toISOString()`) → `Offer` |
| `relist(offerId, input)` | `POST /v1/offers/{id}/relist` | 위와 같은 본문 → 새 `Offer` |
| `update(offerId, changes)` | `PATCH /v1/offers/{id}` | `OfferChanges`의 키만 snake_case로. `null`은 보내지 않는다 |
| `deactivate(offerId, {reason, cancelReservations})` | `POST /v1/offers/{id}/deactivate` | `{reason, cancel_reservations}` → `{offer, cancelled_reservation_count}` → `DeactivateResult{offer, cancelledCount}` |
| `adjustStock(offerId, amount, reason?)` | `POST /v1/offers/{id}/stock-adjustments` | `{amount, reason}`(사유 비면 생략) → `StockAdjustResult{remainingStock, isSoldOut, status}` |

모든 호출은 `shared/api`의 `request`/`apiGet`/`apiPost`를 쓴다(F8). 상점주 호출은 토큰을 붙인다(`auth:false` 아님).

### 2.4 presentation

| 파일 | 하는 일 |
| --- | --- |
| `OwnerOfferChips.tsx` | 「판매 중 N」「판매 예정 N」「품절」「판매 종료」 칩(`Chip`). 숫자는 앞 두 칩만(`screens.md`). 현재 칩 `aria-pressed` |
| `OwnerOfferRow.tsx` | `Box`(태그 + 제목)에 한 할인. 와이어프레임: `식빵 모둠 5종 · 6,000원 (50%)`, `남은 3 / 10 · 픽업 18:00–20:00`, 태그, 카운트다운, 행동 버튼(`ownerRowActions`) |
| `OwnerOfferList.tsx` | 행 목록 + 로딩(`Skeleton`)·빈(`EmptyState`)·오류 표시 |
| `StockAdjustForm.tsx` | O10 본문(칩 빼기/더하기, `Stepper`, 사유 `Input`, 「조정 후 남은 재고 N개」, `FieldError`, 「적용」). 시트·패널이 같은 본문을 쓴다(C-4) |
| `StockAdjustSheet.tsx` | `Overlay` + `StockAdjustForm`(모바일). 제출 중 `dismissible=false` |
| `OfferCreateForm.tsx` | O3 본문. 상품 선택(`useSellableProducts`), 정가, 할인가, 수량 `Stepper`, 빠른 선택 칩, 「판매」「픽업」「고객 취소 가능」 `KeyValue` 줄, 경고 `Notice`, 「시간 직접 바꾸기」, 모바일 `.cta` + PC `.dk` 「할인 등록」 |
| `OfferScheduleFields.tsx` | 네 시각 입력(직접 바꾸기를 눌렀을 때). `datetime-local` 입력(D-10) |
| `OfferEditForm.tsx` | O9 본문. 할인가·최초 수량 `Stepper`·판매 마감·픽업 입력, 잠금 상태(`Notice` 「예약이 있는 할인은 수정할 수 없어요. 판매를 중단하고 다시 올려 주세요.」), 「판매 중단 (O5)」 링크, 「저장」 |
| `OfferDeactivateForm.tsx` | O5 본문. 요약 줄, 「중단 사유 *」 입력, 「기존 예약은?」 라디오(그대로 두기 / 모두 취소하고 전액 환불), 「취소」「판매 중단」 |
| `OfferLoadError.tsx` | `useOwnerOffer` 실패(404·403·네트워크) 안내 + 다시 시도(`ProductLoadError`와 같은 방식, D-11) |

- 화면 문구는 §5. 새 색·새 클래스 없음(F12). 사용 컴포넌트: AppBar·CtaBar·Chip·Button·Input·FieldError·Notice·KeyValue·Box·Stepper·StatusTag·SplitLayout(`.split.r`).

### 2.5 shared 추가

| 파일 | 내용 |
| --- | --- |
| `shared/ui/Chip.tsx` | `components/Chip` README의 마크업(`.chip`, `.on`). `selected`, `onClick`, `disabled`, `children` |
| `shared/ui/Stepper.tsx` | `components/Stepper` README의 `.step`. `value`, `min`, `max`, `onChange`, 접근 이름. 범위 밖 입력은 clamp, 최솟값·최댓값에서 해당 버튼 `disabled` |
| `shared/lib/routes.ts` | `ownerOfferRelist`, `ownerOfferEdit`, `ownerOfferDeactivate`와 `ROUTE_PATTERNS.ownerOfferEdit`·`ownerOfferDeactivate` |
| `shared/lib/useAppWide.ts` | 가까운 `.app`의 폭이 720px(`--bp-wide`) 이상인지 `ResizeObserver`로 돌려주는 훅. jsdom에서는 항상 `false`(모바일). O10 시트/패널 선택에만 쓴다(D-13) |

### 2.6 pages

| page | 구성 |
| --- | --- |
| `pages/owner-offers/OwnerOffersPage` (O2) | `.bar`(로고 「할인」, `OwnerTopNav`, `OwnerAccountButton`) + `.body`: (정지 상점이면 `StoreSuspendedNotice`는 O1에만 둔다, D-14) `+ 할인 등록` 큰 버튼(PC `.dk`), `OwnerOfferChips`, `OwnerOfferList`, PC는 `.split.r` 오른쪽에 `StockAdjustForm`, 모바일은 `StockAdjustSheet`. `.cta`에 `+ 할인 등록`(모바일) |
| `pages/offer-new/OfferNewPage` (O3) | `AppBar`(← 할인 등록) + `OfferCreateForm`. 쿼리 `productId`·`relistFrom` 해석(`relistFrom`이면 `useOwnerOffer`로 이전 값 채움) |
| `pages/offer-edit/OfferEditPage` (O9) | `useOwnerOffer(offerId)` + `OfferEditForm`, 로딩·오류 처리 |
| `pages/offer-deactivate/OfferDeactivatePage` (O5) | `useOwnerOffer(offerId)` + `OfferDeactivateForm` |

## 3. 포트 (F18)

| 포트 | 위치 | 메서드 | 토큰 | 구현체 · 소유 영역 |
| --- | --- | --- | --- | --- |
| `OfferRepository`(기존, 메서드 추가) | `features/offers/domain/offerRepository.ts` | `findNearby`(기존), `findByStore(storeId, statuses, page, size, signal?): Promise<OfferList>`, `findOfferById(id, signal?): Promise<Offer>` | `OfferRepositoryToken`(기존) | `HttpOfferRepository` · offers |
| `OfferCommands`(신규) | `features/offers/domain/offerCommands.ts` | `register(productId, NewOffer, signal?): Promise<Offer>`, `relist(offerId, NewOffer, signal?): Promise<Offer>`, `update(offerId, OfferChanges, signal?): Promise<Offer>`, `deactivate(offerId, DeactivateInput, signal?): Promise<DeactivateResult>`, `adjustStock(offerId, amount, reason, signal?): Promise<StockAdjustResult>` | `OfferCommandsToken`(신규) | `HttpOfferCommands` · offers |

- `ProductRepositoryToken`은 이 영역이 등록하지 않는다(products 소유). `wireOffers()`에는 `OfferCommandsToken` 한 줄만 더한다. `tests/app/container.test.ts` 토큰 목록에 `OfferCommandsToken`을 같은 커밋에서 더한다(`layer-architecture` §6.9-6).

## 4. 공개 API (`features/offers/index.ts` 추가분)

```ts
export type { OfferList } from './domain/offer'              // 새 타입
export type { OfferCommands, NewOffer, OfferChanges, StockAdjustResult, DeactivateResult } from './domain/offerCommands'
export type { OwnerFilter } from './domain/ownerOffer'
export { OWNER_FILTERS, ownerStatusTag, ownerRowActions } from './domain/ownerOffer'
export type { OfferDraft } from './domain/offerDraft'
export { defaultDraft, QUICK_PICKS } from './domain/offerDraft'
export type { StockMode } from './domain/stockAdjustment'
export { OfferCommandsToken } from './application/tokens'
export { useOwnerOffers } from './application/useOwnerOffers'
export { useOwnerOffer } from './application/useOwnerOffer'
export { useCreateOffer } from './application/useCreateOffer'
export { useSaveOffer } from './application/useSaveOffer'
export { useDeactivateOffer } from './application/useDeactivateOffer'
export { useAdjustStock } from './application/useAdjustStock'
export { useOpenOfferCount } from './application/useOpenOfferCount'
export { OwnerOfferChips } from './presentation/OwnerOfferChips'
export { OwnerOfferList } from './presentation/OwnerOfferList'
export { StockAdjustForm } from './presentation/StockAdjustForm'
export { StockAdjustSheet } from './presentation/StockAdjustSheet'
export { OfferCreateForm } from './presentation/OfferCreateForm'
export { OfferEditForm } from './presentation/OfferEditForm'
export { OfferDeactivateForm } from './presentation/OfferDeactivateForm'
export { OfferLoadError } from './presentation/OfferLoadError'
```

- 구현체(`HttpOfferCommands`, `offerDto.ts`)와 `wiring.ts`는 내보내지 않는다(F18). 기존 export는 모두 그대로다.
- `wiring.ts`가 등록하는 토큰: `OfferRepositoryToken`(`HttpOfferRepository`), `LocationProviderToken`(`BrowserLocationProvider`), **`OfferCommandsToken`(`HttpOfferCommands`)**. `app/container.ts`는 이미 `wireOffers()`를 부르므로 바꾸지 않는다.

## 5. 화면별 동작 · 상태 · 문구

공통: 로딩 `Skeleton`, 오류는 `.err` + 「다시 시도」(임시 문구, 상점주 기존 화면과 같은 `MY_STORE_ERROR_FALLBACK_MESSAGE` 방식, 서버 문구는 노출하지 않음). 권한 없음: 상점주 가드가 앞에서 처리하므로 화면에는 없다. 401은 `AuthFailureBridge`가 처리한다.

### 5.1 O2 할인 관리 · 재고 조정

- 문구(정본): 「+ 할인 등록」「수정」「재고 조정」「판매 중단」(링크)「다시 올리기」「적용」, 칩 「판매 중 N」「판매 예정 N」「품절」「판매 종료」, 태그 「판매 중」「판매 종료」(+ `states.md`의 「판매 예정」「품절」).
- 상태: 로딩(Skeleton 3), 빈(선택한 칩에 0건. 문구 정본 없음 → E1 공통 `EmptyState` 임시, Q-4), 오류(「다시 시도」), 성공. 기본 칩 「판매 중」.
- 칩 숫자: 첫 요청 결과를 `countByFilter`로 센다(`SUSPENDED`는 어느 칩에도 세지 않음). 「판매 종료」(CLOSED)는 처음 고를 때 20개씩 요청하고 「더 보기」로 잇는다(`customer-home.md` D-12 방식).
- 행의 시계: 카운트다운은 기존 `salesCountdown(salesEnd, now)`와 `useNow()`(30초) 재사용.
- 재고 조정: 「재고 조정」 → `adjusting = offer`. 모바일은 `StockAdjustSheet`(Overlay), PC(`useAppWide()`)는 `.split.r` 오른쪽 패널에 같은 `StockAdjustForm`. 「적용」 성공 → `adjusting = null`, 목록 `reload()`. 실패는 폼 안 `FieldError`(`INSUFFICIENT_STOCK`은 「남은 재고보다 많이 뺄 수 없어요.」).
- 「판매 중단」 링크 → O5, 「수정」 → O9, 「다시 올리기」 → O3.

### 5.2 O3 할인 등록 · 다시 올리기

- 문구(정본): 라벨 「상품 *」「정가」「할인가 *」「수량 * (1~9999)」「픽업 시작 · 빠른 선택」「판매」「픽업」「고객 취소 가능」, 칩 「30분 후 · 취소 불가」「1시간 후 · 취소 불가」「2시간 후」「3시간 후」「직접 입력」, 링크 「시간 직접 바꾸기」, 버튼 「할인 등록」, 경고 「취소 마감(픽업 시작 1시간 전)이 이미 지나 고객이 예약을 취소할 수 없어요.」(`screens.md` O3 오류·경고 문구 줄에서 앞의 "1시간 이하를 고르면 표시:"는 조건 설명이라 화면에 쓰지 않는다).
- 모드: `new`(상품 선택, `productId` 쿼리가 있으면 고정), `relist`(`relistFrom`; 상품 칸은 읽기 전용, 이전 할인가·수량으로 채움, 시각은 새 기본값). 「다시 올리기」일 때 AppBar 제목은 정본이 없다(Q-4) → 임시 「다시 올리기」.
- 보내기: `new` → `register(productId)`. `relist` → 이전 할인이 `isActive`이면 `relist(offerId)`, 아니면(판매 중단된 할인) `register(sourceOffer.productId)`(D-7, C-2).
- 상품 목록 0건(숨김뿐이거나 없음): 빈 안내(임시) + O6 링크(`ROUTES.ownerProductNew`).
- 저장 버튼은 `validateDraft`가 비면 활성, 제출 중 비활성. 모바일 `.cta`와 PC `.dk`에 같은 동작 두 벌.
- 오류 분기(`errorCode`, F11): `OFFER_ALREADY_OPEN`·`PRODUCT_INACTIVE`·`STORE_SUSPENDED`·`STORE_CLOSED`·`VALIDATION_ERROR`·`OFFER_CLOSED`(relist) 모두 폼 위 `.err`에 **서버 `message`**를 보인다(임시, Q-4. 백엔드 메시지는 한국어).

### 5.3 O9 할인 수정

- 문구(정본): 「할인가 (정가 12,000원보다 낮게)」(금액은 `original_price`로 채움)「최초 수량」「판매 마감」「픽업」「예약이 생긴 할인을 열면」「예약이 있는 할인은 수정할 수 없어요. 판매를 중단하고 다시 올려 주세요.」「판매 중단 (O5)」「저장」.
- 와이어프레임 머리줄 `식빵 모둠 5종 판매 예정 · 예약 0건`의 **「예약 N건」은 만들 수 없다**(응답에 예약 수가 없다, C-3). 임시로 머리줄은 `상품명 + 태그`만, 잠금은 **저장이 `OFFER_HAS_RESERVATIONS`로 거절될 때** 칸을 잠그고 안내 `Notice`를 띄운다(D-15).
- 수정 가능 여부 `isEditable`: `isActive`이고 `status`가 ON_SALE·SCHEDULED·SOLD_OUT. 그 밖(CLOSED·SUSPENDED)이면 칸을 잠그고 「판매 중단」만 숨긴다(안내 문구 정본 없음, Q-4).
- 스텝퍼 최솟값 `quantityFloor`, 최댓값 9999. 판매 마감·픽업은 `datetime-local`. 저장은 `diffOfferChanges`가 빈 값이 아닐 때만 활성. 성공 → O2.

### 5.4 O5 판매 중단 확인

- 문구(정본): 「중단 사유 *」, 「취소」「판매 중단」, 라벨 「기존 예약 3건은?」의 **숫자(3건)와 머리줄 「픽업 대기 예약 3건」은 만들 수 없다**(C-3). 임시 라벨 「기존 예약은?」, 머리줄은 상품명·할인가만(D-15). 라디오 두 줄(「그대로 두기 새 예약만 막고, 예약한 고객은 픽업 가능」, 「모두 취소하고 전액 환불 고객 앱의 예약에 "매장 사정으로 취소됨 · 전액 환불"로 표시돼요. 문자·알림은 가지 않아요.」)은 `wireframe.html` 702~703줄 문구 그대로.
- 기본 선택: 「그대로 두기」(`cancel_reservations=false`). 사유가 비면 「판매 중단」 비활성.
- 오류: `OFFER_CLOSED`(이미 중단)·`OFFER_ENDED`·`PICKED_UP_RESERVATION_EXISTS`(일괄 취소 거절)·`DATA_INCONSISTENT`(500)·`OFFER_SUSPENDED` → `.err`에 서버 `message`(임시, Q-4). 성공 → O2.
- 알림 약속은 넣지 않는다(`open-issues.md` O5).

### 5.5 O10 재고 조정

- 문구(정본): 칩 「빼기 (파손·소진)」「더하기 (추가 입고)」, 라벨 「사유 (선택, 200자)」, 「적용」, 오류 「남은 재고보다 많이 뺄 수 없어요.」. 머리줄은 `재고 조정 식빵 모둠 5종 · 지금 남은 3개`(와이어프레임), 합계 줄은 「조정 후 남은 재고 N개」.
- 기본 모드: 빼기. 스텝퍼 1~`amountBounds.max`. 모드를 바꾸면 수량을 1로 되돌림. 0개가 되면 자동 품절은 서버가 처리하고 목록 `reload`로 반영.
- PC 우측 패널의 와이어프레임(`재고 조정 · 식빵 모둠`, 부호 있는 스텝퍼 `− −1 +`, `사유 파손`)은 O10 모바일(칩 + 양수 스텝퍼)과 모양이 다르다(C-4). 한 본문을 쓰는 안을 임시로 정했다(D-13).

## 6. 결정 표 (모두 임시)

| D | 항목 | 값 | 임시/확정 | 근거 |
| --- | --- | --- | --- | --- |
| D-1 | entities | `entities/offer`를 만들지 않는다. `Offer`는 `features/offers/domain` | 임시 | `fsd-structure` §4 "처음에는 영역 안", `customer-home.md` D-8. O1은 할인 정보가 필요 없고(`owner-today.md` §2), O7 막는 항목 수는 page가 훅 값을 prop으로 넘기면 된다(Q-5) |
| D-2 | 영역 | 상점주 할인 화면 5개를 모두 `features/offers`에 둔다. 새 영역 없음 | 임시 | `fsd-structure` §1.1 `offers` 행(C1·C1a·C2·O2·O3·O5·O9·O10) |
| D-3 | 읽기 포트 | `findByStore`·`findOfferById`를 기존 `OfferRepository`에 더함. 반환 `OfferList`(`items: Offer[]`)는 새 타입. C2의 `findById`(상세 전체)와 이름을 분리 | 임시 | `customer-home.md` §5.4가 `findById`를 C2에 배정. 같은 엔드포인트지만 반환형이 다르다(상점주는 `offer`만 필요) |
| D-4 | 라우트 | §1.1. O5·O9는 라우트, O10은 O2 안 상태 | 임시 | `layout.md` 화면 연결 지도, O7이 확인 화면을 라우트로 둔 선례(`stores.md`) |
| D-5 | O2 목록 요청 | 첫 요청 `[SCHEDULED, ON_SALE, SOLD_OUT, SUSPENDED]` size 100(칩 숫자용), 「판매 종료」(CLOSED)는 처음 고를 때 20개씩 | 임시 | 명세 §9 기본 목록. CLOSED는 명시해야 나옴. 정렬은 서버 순서 그대로(정렬 정본 없음, Q-7) |
| D-6 | 행 동작 | `ownerRowActions` §2.1 | 임시 | 와이어프레임 O2, 백엔드 `ensure_relistable`·`OFFER_SUSPENDED` |
| D-7 | 판매 중단된 할인 「다시 올리기」 | 이전 할인 `isActive`면 `/relist`, 아니면 `POST /products/{id}/offers`로 같은 값을 채워 등록 | 임시 | 백엔드는 중단된 할인의 `/relist`를 거절(C-2). `screens.md` O2·O9가 "중단 후 다시 올림"을 전제 |
| D-8 | 판매 시작 | "지금"이면 `sales_start`를 보내지 않음(서버 현재 시각) | 임시 | 명세 §7 "기본값은 현재 시각", 브라우저·서버 시계 어긋남 방지 |
| D-9 | 제출 흐름 훅 | `useOfferRun`을 offers에 복사(`useProductRun`과 동일 동작) | 임시 | 영역끼리 import 금지(F1). `shared/lib`로 올리는 정리는 TODO(§9) |
| D-10 | 시각 입력 | `datetime-local`. 「시간 직접 바꾸기」와 칩 「직접 입력」은 같은 입력 패널을 연다 | 임시 | 디자인 시스템에 날짜·시간 입력 컴포넌트가 없다(`screens.md` O3는 칩과 링크만). 모양은 구현 때 보고(`design-system-usage` §3.3) |
| D-11 | 읽기 실패 | `OfferLoadError`: 404 → 「할인을 찾을 수 없어요」급 임시 문구 + O2로, 그 외 다시 시도 | 임시 | `products.md`의 `ProductLoadError` 선례. 정본 문구 없음(Q-4) |
| D-12 | 기존 TODO(`offer.ts`) | `Offer`의 상품 필드는 응답이 이미 준 값이라 `entities/product`를 거치지 않는다. 금액은 기존 `formatWon`을 그대로 쓴다(C1 공개 API 유지). TODO 주석은 구현자가 "O3에서 `Product` 정가를 `formatProductPrice`로 표기하는 곳 외에는 통합하지 않음"으로 고친다 | 임시 | `offer.ts` 상단 TODO, `products.md` D-7 |
| D-13 | 시트/패널 분기 | `useAppWide()`로 JS가 앱 폭 720px 기준을 판정, PC는 `.split.r` 우측 패널, 모바일은 `Overlay`. 본문은 `StockAdjustForm` 하나 | 임시 | 와이어프레임이 두 곳에 같은 기능을 둠. CSS만으로는 `Overlay` 포털의 `.dim`이 PC에서도 뜬다 |
| D-14 | 정지 안내 위치 | O2·O3 등에는 정지 안내를 두지 않는다(O1에만, `owner-today.md` D-3). 정지 상점의 등록·재개 거절은 `STORE_SUSPENDED` 서버 문구로 보인다 | 임시 | `StoreSuspendedNotice`가 O1용 부품(`stores.md` D-22), `screens.md`에 O2 정지 문구 없음 |
| D-15 | 예약 수 | 응답에 없는 「예약 N건」은 보이지 않는다. O9 잠금은 `OFFER_HAS_RESERVATIONS` 응답으로, O5 라벨은 숫자 없이 | 임시 | C-3. 숫자를 지어내지 않음(`open-issues.md` 규칙) |
| D-16 | 재고 조정 한도 | 더하기 최대 `9999 − initialStock`, 빼기 최대 `remainingStock` | 임시 | `discount_offer.py:384~392`. 화면 명세는 하한(1)과 "남은 재고 초과 빼기 금지"만 적음 |
| D-17 | O3 기본 시각 | `states.md` 58줄 그대로. 칩 선택 시 `now`를 칩을 누른 순간으로 다시 잡음 | 임시 | `screens.md` O3 동작 메모 |

## 7. 정합 이슈

| C | 내용 | 양쪽 근거 |
| --- | --- | --- |
| C-1 | C2 담당이 `OfferRepository.findById`·`useOfferDetail`을 같은 영역에 더한다고 `customer-home.md`가 배정했다. 이 설계도 같은 파일(`offerRepository.ts`, `httpOfferRepository.ts`, `index.ts`, `application/tokens.ts`, `wiring.ts`)에 메서드를 더한다. 이름은 겹치지 않지만 **같은 파일을 두 사람이 고칠 수 있다** | `customer-home.md` §5.4 ↔ 이 문서 §1.2 |
| C-2 | 화면은 판매 중단 뒤 「다시 올리기」(O3 `/relist`)를 전제하지만(`screens.md` O2 연결 화면, O9 문구 「판매를 중단하고 다시 올려 주세요」), 백엔드 `/relist`는 중단된 할인(`is_active=false`)을 400 `OFFER_CLOSED`로 거절한다 | `screens.md` O2·O3·O9 ↔ `discount_offer.py:277~280`, `reference/catalog.md` §13 에러 표(67줄 "이미 중단된 할인은 재등록할 수 없습니다.") |
| C-3 | 화면은 할인별 예약 수를 쓴다(O5 「기존 예약 3건은?」·「픽업 대기 예약 3건」, O9 「예약 0건」). `OfferResponse`에도 상점주 예약 목록(`StoreReservationListItem`: `id, product_name, quantity, total_price, status, created_at`)에도 `offer_id`·할인별 개수가 없다 | `wireframe.html` 695·758줄 ↔ `catalog/presentation/schemas.py:126~145`, `reservations/presentation/schemas.py:54~71` |
| C-4 | O10 모바일(칩 빼기/더하기 + 양수 스텝퍼)과 O2 PC 우측 패널(부호 있는 스텝퍼, 칩 없음)의 와이어프레임 모양이 다르다. `screens.md`는 "PC는 O2 우측 패널"만 적는다 | `wireframe.html` 611~639줄(패널) ↔ 770~788줄(O10) |
| C-5 | 명세 §10~§11 안내문 "예약 여부는 예약 기능이 생기기 전까지 항상 '예약 없음'으로 처리됩니다"(`catalog.md` 647줄)는 현재 코드와 다르다. `update_offer`는 `reservations.has_reservations_for_offer`로 실제 예약을 본다 | `reference/catalog.md` 647줄 ↔ `service.py:415~418` |
| C-6 | `screens.md` O10은 「적용」 후 "0개가 되면 자동으로 품절"이라 적었다. 백엔드는 `SOLD_OUT`을 시각·재고로 **계산**하므로 응답 `status`·`is_sold_out`로 반영된다(같은 결과, 확인용) | `screens.md` O10 ↔ `discount_offer.py:216~217` |

## 8. 차단 이슈와 질문 목록

차단(구현 불가 또는 정본 없음):

- **차단 B-1 (C-3)**: O5의 「기존 예약 N건」, O9의 「예약 0건」은 데이터가 없어 구현할 수 없다. 임시(D-15)로 숫자 없이 구현한다. 풀리는 조건: 사용자가 백엔드에 할인 응답의 예약 수(또는 상점 예약 목록의 `offer_id`) 추가를 요청.

질문(사용자 결정 필요):

- Q-1 (C-2): 판매 중단된 할인을 「다시 올리기」할 때 임시(D-7: 등록 API로 대신 채움)로 괜찮은가, 아니면 백엔드 `/relist`가 중단된 할인도 받게 요청할 것인가, 중단 할인에는 「다시 올리기」를 빼고 O3 「+ 할인 등록」만 쓸 것인가.
- Q-2 (C-3, B-1): 할인별 예약 수를 백엔드에 요청할 것인가. 요청하지 않으면 O5·O9의 숫자는 영구히 뺀다.
- Q-3: 관리자가 정지한 할인(`status=SUSPENDED`)을 상점주 O2에서 어떤 문구·색으로 보일지. `states.md`에 할인 정지 행이 없다(임시 「판매 종료」).
- Q-4: 정본 문구가 없는 임시 문구들: O2 빈 상태, O3 「다시 올리기」 제목, O3 상품 0건 안내, O3·O5 서버 `message` 그대로 노출 여부, O9의 종료·정지 할인 안내, `OfferLoadError`.
- Q-5: `StoreCloseForm`의 TODO(O7이 막는 항목을 먼저 보여 주기)를 이번에 적용할 것인가. 가능한 방법: offers의 `useOpenOfferCount(storeId)`(진행 중·예정 할인 수 = SCHEDULED+ON_SALE+SOLD_OUT+SUSPENDED의 `total`)를 `pages/store-close`가 호출해 `StoreCloseForm`에 prop으로 넘긴다. `StoreCloseForm`은 `features/stores`라 offers를 import하지 못하므로 `entities/offer` 없이도 된다. 픽업 대기 예약 수는 reservations 쪽 훅이 필요하다(`owner-today.md` 참조). 이번 범위에서는 결정하지 않는다.
- Q-6: 두 번째 영역(예: C5 내 예약, C2)이 `Offer` 타입을 가져와야 하면 `entities/offer`로 내린다. 지금 C2·C5 담당과 일정을 맞출 것인가.
- Q-7: O2 목록의 정렬(서버 기본 순서에 의존)과 「판매 종료」 목록의 기간 제한(오래된 종료 할인 전부 이어 붙임)을 정할 것인가.
- Q-8: 판매 시작이 과거인 입력(직접 바꾸기), 판매 시작이 미래(예약 판매)를 O3에서 허용할 것인가. 현재 명세는 허용하는 것으로 읽힌다(`SCHEDULED` 상태가 있음).

## 9. 남길 작업 주석 (`code-annotations`)

| 태그 | 위치 | 요약 | 왜 | 언제 |
| --- | --- | --- | --- | --- |
| TODO | `OfferEditForm.tsx` | 할인별 예약 수를 모르므로 잠금을 저장 거절 후에야 안다 | 응답에 예약 수가 없다 (offers.md C-3, D-15) | 결정 후 (사용자: 할인별 예약 수 백엔드 요청) |
| TODO | `OfferDeactivateForm.tsx` | 「기존 예약은?」 라벨에 건수가 없다 | 같은 이유 (offers.md C-3, D-15) | 결정 후 (사용자: 할인별 예약 수 백엔드 요청) |
| TODO | `createOffer.ts` | 중단된 할인의 다시 올리기를 등록 API로 대신한다 | 백엔드 `/relist`가 중단된 할인을 거절한다 (offers.md C-2, D-7) | 결정 후 (사용자: 중단 할인 다시 올리기 방식) |
| TODO | `ownerOfferMessages.ts` | 임시 문구(빈 상태, 다시 올리기 제목, 읽기 실패, 서버 message 노출) | content.md에 정본이 없다 (offers.md D-11, Q-4) | 결정 후 (디자인 시스템: content.md 문구 확정) |
| TODO | `OfferScheduleFields.tsx` | 날짜·시간 입력이 디자인 시스템에 없어 `datetime-local`을 쓴다 | components에 해당 컴포넌트가 없다 (offers.md D-10) | 결정 후 (디자인 시스템: 시간 입력 컴포넌트) |
| TODO | `useOfferRun.ts` | `useProductRun`과 같은 코드를 복사했다 | 영역끼리 import 금지 (offers.md D-9) | 리팩터링 시 (`shared/lib`로 올리기) |
| TODO | `OwnerOfferRow.tsx` | 관리자 정지 할인 라벨이 임시다 | `states.md`에 정지 할인 행이 없다 (offers.md Q-3) | 결정 후 (디자인 시스템: states.md 할인 정지 문구) |
| open-issues | `OfferDeactivateForm.tsx` | `// open-issues: O5 알림 약속을 넣지 않음` | `open-issues.md` O5 | (한 줄 형식) |
| 해소 | `placeholders.tsx` 상단 TODO | O2·O3 자리 page 삭제(`OwnerOffersPlaceholder`, `OwnerOfferNewPlaceholder`) | 정식 page로 교체 (`언제: O2 구현 시, O3 구현 시` 해소). 파일 전체는 O1(`owner-today.md`)·C2·C5가 남아 있어 지우지 않는다 | 이 구현에서 |
| 해소 | `offer.ts` 상단 TODO | D-12로 갱신 | `언제: O3 구현 시` 도달 | 이 구현에서 |

## 10. 구현 순서 제안

1. shared: `Chip`·`Stepper`·`useAppWide`·`routes` 경로.
2. features/offers: domain → 포트·DTO·구현체·토큰·wiring(+`tests/app/container.test.ts`) → 훅 → presentation.
3. pages 4개 + `routes.tsx` 교체 + `placeholders.tsx`에서 O2·O3 자리 page 삭제.
4. 완료 게이트 `frontend-invariants` §6, 화면 흐름이 바뀌었으므로 `npm run test:e2e`(상점주 할인 등록 → 목록 → 재고 조정 → 중단).
