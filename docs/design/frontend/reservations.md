# reservations 영역 설계: 예약하기·결제 나가기·내 예약·예약 취소

- 대상 화면: C2(예약 영역만: 수량 조절·「예약하고 결제」·「결제 이어하기」), C3a 결제 화면 나가기, C5 내 예약(진행 중), C5b 지난 예약, C5a 예약 취소 확인, E1(위 화면의 로딩·빈 상태·처리 중·취소 마감 카드)
- 함께 보는 설계안: 결제(C3·C4)는 `payments.md`. C2 상세 본문은 offers 설계(아직 없음).
- 제외: O1 픽업 처리(2차), O5·O7, C11, C2 상세 본문
- 정본: 화면 `../../design-system/screens.md` C2·C3a·C5·C5a·C5b·E1, 상태 `../../design-system/states.md` "예약 (고객 화면)", 문구 `content.md`, API `../../reference/reservations.md` §1~§3, 실제 응답 `../../../backend/src/reservations/presentation/schemas.py`
- 지킬 규칙: F1~F19(`frontend-invariants`), `layer-architecture` §5·§6, `tdd-workflow` §2

## 1. 계층 배치와 slice

| FSD 계층 | slice | 화면 | 비고 |
| --- | --- | --- | --- |
| features | `features/reservations` | C2 예약 영역, C3a, C5, C5b, C5a | 영역 slice(`fsd-structure` §1.1) |
| pages | `pages/my-reservations` | C5, C5b, C5a(오버레이) | 새 slice |
| pages | `pages/offer-detail` | C2 | **offers 소유.** 이 설계는 `ReserveOfferPanel`을 끼울 자리만 정한다(C-1) |
| pages | `pages/checkout`, `pages/payment-complete` | C3·C3a, C4 | `payments.md` §1 |
| entities | 만들지 않음 | | payments가 예약 데이터를 직접 쓰지 않고 page가 조립하므로 두 번째 영역의 공유 필요가 아직 없다(`fsd-structure` §4 "미리 만들지 않음"). D-12 |

## 2. 파일 목록과 export (`features/reservations`)

### 2.1 domain (순수 TypeScript, F6. 시각은 모두 인자 `now: Date`로 받는다)

| 파일 | export |
| --- | --- |
| `domain/reservation.ts` | `type ReservationStatus = 'PENDING_PAYMENT' \| 'RESERVED' \| 'PICKED_UP' \| 'CANCELLED'`, `type CancelledBy = 'CUSTOMER' \| 'STORE' \| 'SYSTEM' \| null`, `type Reservation = { id: string; offerId: string; storeName: string; productName: string; quantity: number; totalPrice: number; status: ReservationStatus; createdAt: Date; pickupCode: string; pickupAddress: string; cancelledBy: CancelledBy; pickupStart: Date; pickupEnd: Date; cancellableUntil: Date }`, `type CreatedReservation = { id: string; offerId: string; quantity: number; unitPrice: number; totalPrice: number; status: ReservationStatus; createdAt: Date; storeName: string; productName: string }` |
| `domain/quantity.ts` | `MAX_QUANTITY = 5`, `MIN_QUANTITY = 1`, `maxQuantity(remainingStock: number): number` (= `min(remainingStock, 5)`, 음수·0이면 0), `clampQuantity(q: number, remainingStock: number): number`, `canIncrease(q, remainingStock): boolean`, `canDecrease(q): boolean`, `canReserve(q, remainingStock): boolean` (1 ≤ q ≤ max) |
| `domain/display.ts` | `type DisplayState = 'PENDING_PAYMENT' \| 'RESERVED' \| 'PICKUP_MISSED' \| 'PICKED_UP' \| 'CANCELLED_BY_CUSTOMER' \| 'CANCELLED_BY_STORE' \| 'CANCELLED'`, `displayState(r: Reservation, now: Date): DisplayState`, `statusLabel(s: DisplayState): string`, `statusTone(s: DisplayState): 'hot' \| 'ok' \| 'mute'`, `isPickupMissed(r, now): boolean` (RESERVED && now > pickupEnd) |
| `domain/grouping.ts` | `type ReservationTab = 'active' \| 'past'`, `isVisibleToCustomer(r): boolean` (cancelledBy ≠ SYSTEM), `tabOf(r: Reservation, now: Date): ReservationTab`, `splitByTab(list: Reservation[], now: Date): { active: Reservation[]; past: Reservation[] }` (SYSTEM 제외, 각 탭 `createdAt` 최신순) |
| `domain/cancellation.ts` | `type CancelAvailability = { kind: 'cancellable'; until: Date \| null } \| { kind: 'deadlinePassed'; until: Date } \| { kind: 'none' }`, `cancelAvailability(r: Reservation, now: Date): CancelAvailability`, `findPendingForOffer(list: Reservation[], offerId: string): Reservation \| null` |
| `domain/format.ts` | `formatWon(n: number): string` (`11,500원`), `formatTime(d: Date): string` (`17:00`), `formatTimeRange(a: Date, b: Date): string` (`18:00–20:00`, en dash), `formatDate(d: Date): string` (`11/07`), `formatQuantity(name: string, q: number): string` (`식빵 모둠 × 2`) |
| `domain/messages.ts` | 문구 상수와 `cancelErrorMessage(e: { errorCode: string; message: string }): string`, `reserveErrorMessage(e): string` (§3.1 표) |

규칙 (정본: `states.md`, 결정 D-1~D-6):

- `displayState`: PENDING_PAYMENT → `결제 대기`(hot) / RESERVED이고 `now <= pickupEnd` → `예약 확정`(ok) / RESERVED이고 `now > pickupEnd` → `픽업 시간 지남`(mute) / PICKED_UP → `픽업 완료`(mute) / CANCELLED+CUSTOMER → `취소됨`(mute, 보조 문구 `직접 취소`) / CANCELLED+STORE → `매장 사정으로 취소됨`(mute) / CANCELLED+null → `취소됨`(mute). SYSTEM은 목록에서 빠지므로 `displayState`에 오면 `취소됨`.
- `tabOf`: 진행 중 = PENDING_PAYMENT, RESERVED(`now <= pickupEnd`), CANCELLED+STORE(`now <= pickupEnd`). 나머지는 지난 예약. 경계: `now == pickupEnd`는 진행 중(백엔드 픽업 허용이 양 끝 포함, `reference/reservations.md` §4).
- `cancelAvailability`: PENDING_PAYMENT → `cancellable, until: null`(시간 무관, `reference/reservations.md` §3) / RESERVED이고 `now <= cancellableUntil` → `cancellable, until` / RESERVED이고 `now > cancellableUntil` → `deadlinePassed` / 그 외 `none`. 경계: 정각은 취소 가능(서버도 정각 허용).
- 미수령(`픽업 시간 지남`) 카드는 `deadlinePassed`가 되지만 지난 예약 탭이라 취소 링크를 그리지 않는다(환불 없음, D-46 확정).

### 2.2 application

| 파일 | export |
| --- | --- |
| `domain/ports.ts` (domain 포트, §6.2) | `interface ReservationRepository { create(input: { offerId: string; quantity: number }, signal?: AbortSignal): Promise<CreatedReservation>; listMine(query: { status?: ReservationStatus; page: number; size: number }, signal?: AbortSignal): Promise<{ items: Reservation[]; page: number; size: number; total: number }>; get(id: string, signal?: AbortSignal): Promise<Reservation>; cancel(id: string, signal?: AbortSignal): Promise<{ id: string; status: ReservationStatus; cancelledBy: CancelledBy }> }` (`get`: 403·404는 ApiError 그대로, D-8) |
| `application/tokens.ts` | `ReservationRepositoryToken = createToken<ReservationRepository>('ReservationRepository')` |
| `application/errorInfo.ts` | 내부 파일. `readErrorInfo(e: unknown)` (auth와 같은 모양. 공유화는 C-9) |
| `application/fetchAllMine.ts` | `fetchAllMine(repo, signal, status?): Promise<Reservation[]>` — `size: 100`으로 page 1부터 `total`까지 반복(D-7) |
| `application/reserveOffer.ts` | `reserveOffer(repo, input, signal: AbortSignal): Promise<{ kind: 'created'; reservationId: string } \| { kind: 'pendingExists'; reservationId: string \| null }>` — 409 `PENDING_RESERVATION_EXISTS`이면 `fetchAllMine(repo, signal, 'PENDING_PAYMENT')` + `findPendingForOffer`로 ID를 찾는다. 그 외 오류는 그대로 throw |
| `application/useNow.ts` | `useNow(intervalMs = 30000): Date` — 주기적으로 갱신(D-9). 테스트는 `vi.useFakeTimers` |
| `application/useReserveOffer.ts` | `useReserveOffer(offerId: string): { submit(quantity: number): Promise<void>; pending: boolean; error: { errorCode: string; message: string } \| null; pendingReservationId: string \| null; createdReservationId: string \| null }` |
| `application/useMyReservations.ts` | `useMyReservations(): { status: 'loading' } \| { status: 'error'; errorCode: string; message: string } \| { status: 'success'; active: Reservation[]; past: Reservation[] }` + `reload(): void`. 마운트 시 `fetchAllMine`, 언마운트 abort(F10) |
| `application/useMyReservation.ts` | `useMyReservation(id: string)` — `repo.get(id)` 단건 조회(D-8). `loading / notFound(403·404) / error / success(reservation)`, 언마운트 abort. C3·C4 page가 씀 |
| `application/useCancelReservation.ts` | `useCancelReservation(): { cancel(id: string): Promise<boolean>; pending: boolean; error: {...} \| null }` — 성공 시 true. 처리 중 중복 호출 무시 |

### 2.3 infrastructure (`implements`, DTO는 파일 안에서만, F9)

| 파일 | export |
| --- | --- |
| `infrastructure/httpReservationRepository.ts` | `class HttpReservationRepository implements ReservationRepository` (`shared/api`의 `request`·`apiGet`·`apiPost`, F8) |

| 메서드 | 엔드포인트 | DTO → domain |
| --- | --- | --- |
| `create` | `POST /v1/reservations {offer_id, quantity}` → 201 | `id, offer_id→offerId, quantity, unit_price→unitPrice, total_price→totalPrice, status, created_at→createdAt(Date), store_name, product_name`. `user_id`는 버린다. **픽업 코드·픽업 시간 없음**(schemas.py `ReservationCreateResponse`) |
| `listMine` | `GET /v1/users/me/reservations?status&page&size` → 200 | `reservations[]`의 14필드 → `Reservation`(datetime 5개는 `new Date`), `page/size/total` 그대로. 쿼리는 `URLSearchParams`, `status` 없으면 생략 |
| `get` | `GET /v1/reservations/{id}` → 200 (`reference/reservations.md` §2-1) | `ReservationListItem`과 같은 14필드 → `Reservation`(`listMine`과 같은 변환 함수). 403·404는 ApiError 그대로 |
| `cancel` | `POST /v1/reservations/{id}/cancel` → 200 | `id, status, cancelled_by→cancelledBy`. `cancelled_at`은 화면에서 안 씀 |

- `status`·`cancelled_by`가 정의 밖 문자열이면 다른 값으로 바꾸지 않고 `Error`를 던진다(조용한 보정 금지, 임시 D-21). 테스트 (f)-4.

### 2.4 presentation

| 파일 | export | 화면 |
| --- | --- | --- |
| `presentation/ReserveOfferPanel.tsx` | `ReserveOfferPanel(props: { offerId: string; unitPrice: number; remainingStock: number; reservable: boolean; unavailableReason: string \| null; isLoggedIn: boolean; onRequireLogin(quantity: number): void; onGoToCheckout(reservationId: string): void; initialQuantity?: number })` | C2 하단: Stepper + CtaBar 「예약하고 결제 12,000원」 / 「결제 이어하기」 |
| `presentation/ReservationCard.tsx` | `ReservationCard({ reservation, now, onCancel, onContinuePayment })` | C5·C5b 카드 1장 |
| `presentation/MyReservationList.tsx` | `MyReservationList({ tab, onTabChange, onCancel, onContinuePayment })` | C5·C5b 본문(칩 + 목록 + E1 상태) |
| `presentation/CancelReservationSheet.tsx` | `CancelReservationSheet({ reservation, onClose, onCancelled })` | C5a |
| `presentation/LeaveCheckoutSheet.tsx` | `LeaveCheckoutSheet({ reservationId, onContinue, onCancelled, onPayLater })` | C3a(C3 page가 띄움) |

### 2.5 공개 API (`features/reservations/index.ts`)

`ReserveOfferPanel`, `MyReservationList`, `CancelReservationSheet`, `LeaveCheckoutSheet`, `useMyReservation`, `type Reservation`, `type ReservationStatus`, `formatWon`, `formatTime`, `formatTimeRange`, `displayState`, `statusLabel`, `statusTone`, `MY_RESERVATIONS_LINK_LABEL`, `DIRECTIONS_LABEL`(pages가 C3·C4를 그리는 데 씀, D-22. domain 순수 함수·문구 상수라 F18 위반 아님. features/payments는 F1 때문에 import할 수 없어 자체 포맷을 둔다, C-9). 구현체·wiring은 내보내지 않는다(F18).

### 2.6 `wiring.ts`

`wireReservations(): Binding[]` = `bind(ReservationRepositoryToken, new HttpReservationRepository())`. `app/container.ts`에 `...wireReservations()` 한 줄.

### 2.7 pages

| slice | 파일 | 내용 |
| --- | --- | --- |
| `pages/my-reservations` | `presentation/MyReservationsPage.tsx`, `index.ts` | AppBar 「내 예약」 + `MyReservationList` + 고객 TabBar(C-5). 탭은 쿼리 `?tab=past`(D-10). 「예약 취소」 → 같은 화면 위 `CancelReservationSheet`(D-11). 「결제 이어하기」 → C3 경로 |
| `pages/offer-detail` (offers 소유) | — | offers 설계가 `ReserveOfferPanel`을 넣는다. 로그인 여부는 page가 `features/auth`의 `useAuth`로 읽어 prop으로 넘김(F1) |

## 3. 화면 상태와 문구

### 3.1 문구 (정본 위치)

| 키 | 문구 | 정본 |
| --- | --- | --- |
| 예약 버튼 | `예약하고 결제 {formatWon(unitPrice×q)}` | screens.md C2 |
| 이어하기 | `결제 이어하기` | screens.md C2 |
| 결제 대기 중복 | `이 상품에 결제하지 않은 예약이 이미 있어요.` | screens.md C2(「(오류 예시)」는 표기 제외, D-13 임시) |
| 칩 | `진행 중` / `지난 예약` | screens.md C5 |
| 취소 링크 | `예약 취소 · {HH:mm}까지` (PENDING은 `예약 취소`만, D-5) | screens.md C5 |
| 마감 지남 | `취소 마감 지남 ({HH:mm})` 회색, 누를 수 없음 | states.md "화면에서 계산하는 값" |
| 코드 라벨 | `매장에서 보여 주세요` | screens.md C5 |
| 예약 시각 | `{HH:mm} 예약` | screens.md C5 동작 메모 |
| C5a 버튼 | `돌아가기` / `예약 취소`, 라벨 `돌려받는 금액` | screens.md C5a |
| C5a 환불 안내 | §3.3, **임시**(D-14) | — |
| C3a 버튼 | `결제 계속하기`(주) / `예약 취소하고 나가기`(테두리) / 링크 `나중에 결제 (내 예약에 남음)` | screens.md C3a |
| 처리 중 | `처리 중…` (버튼 비활성) | states.md, screens.md E1 |
| 빈 상태 행동 | `할인 보러 가기` → `/` | screens.md E1 |
| 빈 상태 본문 | **정본 없음**(C-7, D-15 임시: 진행 중 `진행 중인 예약이 없어요.` / 지난 예약 `지난 예약이 없어요.`) | — |
| 취소 마감 오류(400 `CANCELLATION_DEADLINE_PASSED`) | 서버 `message` 그대로(D-16 임시) | reference/reservations.md §3 |
| 그 외 오류 | 서버 `message`, 비어 있으면 auth의 대체 문구 방식(D-16 임시) | F11 |

### 3.2 상태별 표시

| 화면 | 로딩 | 빈 | 에러 | 성공 |
| --- | --- | --- | --- | --- |
| C5/C5b | 카드 모양 Skeleton 3장 | EmptyState + 「할인 보러 가기」 | Notice(메시지) + 다시 시도(D-17 임시: 버튼 문구 `다시 시도`, 정본 없음) | 칩 + 카드 목록 |
| C5 카드 | | | | 상태 태그(states.md), 상품 `× N`, 매장 · 픽업 시간대, PENDING: 「결제 이어하기」, RESERVED(진행 중): PickupCode + `HH:mm 예약` + 「길찾기」(D-18) + 오른쪽 취소 링크 또는 마감 문구, STORE 취소: 태그만 |
| C5b 카드 | | | | 태그 + `MM/DD` + 상품·금액. 「더 보기」 없음(D-7) |
| C2 패널 | (page가 offer 로딩 처리) | | 오류는 FieldError 칸 | `reservable=false`면 버튼 비활성 + `unavailableReason`. 수량 `+`는 `canIncrease` false면 비활성 |
| C5a | | | FieldError(취소 오류) | 상품·금액 KeyValue + 환불 안내 + 버튼 |
| 처리 중(공통) | | | | 누른 버튼만 비활성 + `처리 중…` |

### 3.3 C5a 환불 안내 (임시, 사용자 결정 필요 D-14)

현재 API(`ReservationListItem`)에는 결제 금액·사용 포인트·적립 포인트가 없어 복구(RESTORE)·회수(REVOKE) 숫자를 정확히 보여 줄 수 없다. 제안:

- RESERVED: `돌려받는 금액` = `{formatWon(totalPrice)}` 아래 줄 `결제한 금액은 결제 수단으로, 사용한 포인트는 포인트로 돌려드려요. 이 예약으로 적립된 포인트는 회수돼요.`
- PENDING_PAYMENT(C5에서 결제 대기 취소): 환불 줄 없음, `결제 전이라 돌려받을 금액이 없어요.`
- `totalPrice`는 포인트 포함 예약 총액이다(결제 금액 아님). 그대로 「돌려받는 금액」에 쓰면 포인트 사용분이 섞이므로, 사용자 결정 전까지 이 줄을 "예약 금액"으로 쓸지도 함께 결정한다.

## 4. 흐름

- **C2 예약하기**: 비로그인 → `onRequireLogin(q)`(page가 A1로, 돌아올 때 `initialQuantity`. 수량 보존 방식은 offers/auth 결정 C-1). 로그인 → `submit(q)` → 201이면 `onGoToCheckout(id)` → C3. 409 `PENDING_RESERVATION_EXISTS` → 문구 표시 + 버튼이 「결제 이어하기」로 바뀌고 누르면 찾은 ID의 C3. 찾지 못하면(null) 「결제 이어하기」 대신 `내 예약` 이동(D-19 임시). 409 `OUT_OF_STOCK`/`OFFER_NOT_RESERVABLE`, 400 `VALIDATION_ERROR`, 404 → 서버 메시지.
- **C5 결제 이어하기**: C3 경로로 이동.
- **C5a**: 「예약 취소」 → `cancel(id)` → 성공 시 시트 닫고 `reload()`. 400 `CANCELLATION_DEADLINE_PASSED`, 409 → 메시지 표시 후 버튼 다시 활성, 목록 `reload()`.
- **C3a**(C3 page가 뒤로 가기에서 띄움): 「결제 계속하기」 닫기 / 「예약 취소하고 나가기」 → `cancel` 성공 시 `onCancelled`(page가 홈 `/`으로 replace 이동, D-20) / 「나중에 결제」 → `onPayLater`(C5로).

## 5. 결정 표

| D | 항목 | 값 | 임시/확정 | 근거 | 차단 |
| --- | --- | --- | --- | --- | --- |
| D-1 | 수량 범위·상한 | 1~5, 상한 min(남은 재고, 5) | 확정 | 발주서 3, screens.md C2 | 아니오 |
| D-2 | 미수령 표시 | RESERVED && now > pickup_end → `픽업 시간 지남`, 지난 예약, 환불·취소 없음 | 확정 | 발주서 3, `../reservations.md` D-46 | 아니오 |
| D-3 | 고객 취소 | `POST /cancel` 하나로 결제 완료 예약도 전액 환불, 위약금 없음, `cancellable_until` 지나면 서버 400 | 확정 | 발주서 3, reference §3 | 아니오 |
| D-4 | 취소 마감 경계 | `now <= cancellable_until`이면 취소 가능(정각 포함), 화면은 응답 필드 사용(직접 계산 안 함) | 확정(서버 규칙) / 화면 적용은 임시 | reference §3 "정각 허용" | 아니오 |
| D-5 | 결제 대기 카드의 취소 | 시간 제한 없이 `예약 취소` 링크(마감 시각 표기 없음) | 임시 | reference §3(대기 예약은 시간 무관). 화면 명세에 대기 카드 취소 표기 없음 | 아니오 |
| D-6 | SYSTEM 취소 | 목록에서 숨김 | 확정 | states.md | 아니오 |
| D-7 | 목록 페이지 처리 | size=100으로 전 페이지를 받아 앱에서 탭 분리, 「더 보기」 미구현 | 임시 | screens.md C5b("그 전에는 전체를 받아 앱에서 나눔"). 서버 페이지는 생겼지만 진행 중/지난 분류가 화면 계산(pickup_end)이라 서버 `status` 필터로 탭을 나눌 수 없음 | 아니오 |
| D-8 | 예약 1건 조회 | `GET /v1/reservations/{id}` 단건 조회(`ReservationRepository.get`). 403·404 → notFound. 목록 순회(`findMine`) 폐기 | 확정 | `reference/reservations.md` §2-1(백엔드 추가), C-3 해결 | 아니오 |
| D-9 | 현재 시각 갱신 | `useNow` 30초 주기 | 임시 | 정본 없음 | 아니오 |
| D-10 | 경로 | C5 `/me/reservations`, C5b `/me/reservations?tab=past`. 임시 `CustomerLayout` 아래(C-5) | 임시 확정(정식 고객 셸 설계 때 재검토) | C-5 임시 해결 | 아니오 |
| D-11 | C5a 형태 | 내 예약 화면 위 오버레이(라우트 없음) | 임시 | screens.md C5a 컴포넌트는 AppBar·CtaBar(하위 화면 모양) — 단건 GET이 생겼으므로(D-8) 별도 라우트도 가능, 정식 고객 셸 설계 때 재검토 | 아니오 |
| D-12 | entities/reservation | 만들지 않음, C3·C4 page가 `useMyReservation`을 조립 | 임시 | fsd-structure §4 | 아니오 |
| D-13 | 중복 예약 문구 | `이 상품에 결제하지 않은 예약이 이미 있어요.` | 임시 | screens.md C2(「오류 예시」 표기) | 아니오 |
| D-14 | C5a 환불 금액 표시 | §3.3 문구로 대체(숫자 없음) | **임시, 사용자 결정 필요** | 발주서 3, schemas.py에 결제·포인트 필드 없음 | 아니오(문구만 교체) |
| D-15 | 빈 상태 본문 | §3.1 | 임시 | 정본 없음(C-7) | 아니오 |
| D-16 | 오류 문구 | 서버 message 사용 | 임시 | F11, 화면 명세 문구 없음 | 아니오 |
| D-17 | 목록 오류 재시도 버튼 | `다시 시도` | 임시 | 정본 없음 | 아니오 |
| D-18 | 「길찾기」 | `pickupAddress`로 외부 지도 링크. 어떤 지도 서비스·URL인지 정본 없음 → 이번엔 버튼만 두고 동작은 TODO | 임시 | screens.md C4·C5에 버튼만 | 아니오 |
| D-19 | 중복 예약 ID를 못 찾음 | 「결제 이어하기」 대신 내 예약으로 이동 | 임시 | 정본 없음 | 아니오 |
| D-20 | C3a 취소 후 이동 | 홈 `/`(replace). C2 경로가 생기면 C2(`/offers/{offerId}`)로 변경 | 임시 | screens.md C3a에 이동 대상 없음, C2 경로 미정(C-1) | 아니오 |
| D-21 | 알 수 없는 status·cancelled_by | 변환 시 Error | 임시 | 정본 없음 | 아니오 |
| D-22 | 공개 API에 표시용 domain 함수·문구 추가 | `formatTime`, `displayState`, `statusLabel`, `statusTone`, `MY_RESERVATIONS_LINK_LABEL`, `DIRECTIONS_LABEL` export(§2.5) | 임시 | C4(`pages/payment-complete`)가 상태 태그·시각·버튼 문구를 그려야 함. C4 표시가 늘면 `features/reservations`에 표시 컴포넌트(예: 예약 확정 요약)를 두고 export를 줄이는 안 재검토 | 아니오 |

## 6. 정합 이슈

| C | 내용 | 근거 |
| --- | --- | --- |
| C-1 | C2 page(`pages/offer-detail`)와 상세 본문은 offers 설계 범위인데 offers 설계안이 없다. `ReserveOfferPanel` props(남은 재고·예약 가능 여부·사유·단가)는 offers 상세 응답(`remaining_stock`, `is_sold_out`, `cancel_policy`)에서 page가 넘기는 것으로 가정. 비로그인 → A1 → 같은 수량 복귀 방식도 offers·auth와 맞춰야 함 | screens.md C2, reference/catalog.md §10, fsd §1.1 |
| C-2 | 결제 대기 중복의 HTTP 코드: 발주서는 "서버 오류", 명세·화면 명세는 409 `PENDING_RESERVATION_EXISTS`. 설계는 409+error_code로 분기 | reference/reservations.md §1 에러 표, backend reservations/domain/exceptions.py:132 |
| C-3 | **해결.** 예약 단건 조회 API가 없어 목록 전체 검색으로 대신했으나, 백엔드가 `GET /v1/reservations/{id}`를 추가해 D-8 확정 | reference/reservations.md §2-1 |
| C-4 | screens.md·open-issues.md C5는 "백엔드 cancel()이 마감 시각을 검사하지 않음", C5b는 "목록 API에 페이지 매개변수 없음"이라 적혀 있으나 현재 명세·코드는 둘 다 반영됨(400 `CANCELLATION_DEADLINE_PASSED`, `status/page/size`). 디자인 문서 갱신 필요(이 설계 범위 밖, 제안) | screens.md C5·C5b, open-issues.md C5, reference/reservations.md §2·§3, router.py:60~70 |
| C-5 | **임시 해결.** 고객 셸(고객 TabBar widget, 고객 로그인 가드, 고객 라우트 경로)이 설계되지 않았다. 임시 `app/layouts/CustomerLayout.tsx`(CUSTOMER만 허용, 비로그인 → `/login`에 `from` 유지, OWNER·ADMIN → `/`, TabBar 없음)로 C5·C5b·C3·C4 경로를 연결. 정식 고객 셸 설계 때 재검토 | app-shell.md §2, src/app/layouts/CustomerLayout.tsx, src/app/router/routes.tsx |
| C-6 | screens.md C5a "환불액·포인트 복구·회수는 포인트 정책대로 계산해 보여 줌" ↔ 목록 응답에 결제 금액·사용 포인트 없음 | screens.md C5a, schemas.py `ReservationListItem` |
| C-7 | E1에 내 예약 빈 상태 본문 문구가 없다(행동 버튼만) | screens.md E1 |
| C-8 | reference/reservations.md §2의 JSON 예시에는 새 필드(pickup_*·cancellable_until)와 page/size/total이 빠져 있고, 하단 "확인 필요"에 쿼리 매개변수 제안이 남아 있다(표는 갱신됨). 설계는 표·schemas.py를 따름 | reference/reservations.md §2 |
| C-9 | `readErrorInfo`·금액 포맷이 auth·reservations·payments에 중복될 수 있다. 업무를 모르므로 `shared/lib`로 내리는 안을 제안(범위 밖, 사용자·오케스트레이터 결정) | features/auth/application/errorInfo.ts, fsd §4 |

## 7. 차단 이슈와 질문 목록

1. 정식 고객 셸(TabBar 등) 설계(C-5, D-10). 임시 `CustomerLayout`으로 차단 해제됨.
2. C5a 환불 안내 문구 대체안 승인 여부와 「돌려받는 금액」에 예약 총액을 쓸지(D-14, C-6). 정확한 숫자가 필요하면 백엔드에 결제 금액·사용 포인트 필드 추가 요청.
4. 빈 상태·재시도 문구(D-15, D-17), 「길찾기」 지도 링크 방식(D-18).
5. C2 offers 설계와 패널 props·로그인 복귀 수량 보존 방식 합의(C-1).
6. 결제 대기 카드의 취소 링크 표기(D-5).

## 8. 골격 (`tdd-workflow` §3)

- 그대로 만들 것: `domain/reservation.ts`(타입), `domain/ports.ts`, `application/tokens.ts`, `application/errorInfo.ts`(실제 구현), `domain/quantity.ts`의 상수, `domain/messages.ts`의 문구 상수, `wiring.ts`, `index.ts`, `app/container.ts` 한 줄.
- 본문 비울 것: domain 함수 전부, application 함수·훅, `HttpReservationRepository` 메서드, presentation 컴포넌트(`return null`), `pages/my-reservations`.
- 라우트 연결은 C-5 해결 뒤.

## 9. 테스트 목록 (`tdd-workflow` §2, 위치 `tests/features/reservations/` 아래)

공통 픽스처: `pickupStart=2026-11-10T18:00+09:00`, `pickupEnd=20:00`, `cancellableUntil=17:00`.

### (a) `domain/quantity.test.ts`
1. `maxQuantity(10)` → 5, `maxQuantity(5)` → 5, `maxQuantity(3)` → 3, `maxQuantity(1)` → 1, `maxQuantity(0)` → 0, `maxQuantity(-1)` → 0
2. `canIncrease(4, 10)` true, `canIncrease(5, 10)` false, `canIncrease(3, 3)` false
3. `canDecrease(2)` true, `canDecrease(1)` false
4. `canReserve(0, 10)` false, `canReserve(1, 10)` true, `canReserve(5, 10)` true, `canReserve(6, 10)` false, `canReserve(1, 0)` false
5. `clampQuantity(7, 3)` → 3, `clampQuantity(0, 3)` → 1

### (b) `domain/display.test.ts`
1. PENDING_PAYMENT → `결제 대기`/hot
2. RESERVED, now 19:59 → `예약 확정`/ok; now 20:00(정각) → `예약 확정`; now 20:00:01 → `픽업 시간 지남`/mute
3. PICKED_UP → `픽업 완료`/mute
4. CANCELLED+CUSTOMER → `취소됨`(보조 `직접 취소`), +STORE → `매장 사정으로 취소됨`, +null → `취소됨`, 모두 mute

### (c) `domain/grouping.test.ts`
1. PENDING → active, RESERVED(now ≤ end) → active, RESERVED(now > end) → past, PICKED_UP → past, CANCELLED+CUSTOMER → past
2. CANCELLED+STORE: now 20:00 → active, 20:00:01 → past
3. SYSTEM은 두 탭 모두에 없음
4. 각 탭 `createdAt` 내림차순, 빈 배열 → 두 탭 빈 배열

### (d) `domain/cancellation.test.ts`
1. PENDING, now가 cancellableUntil 이후여도 → `cancellable, until null`
2. RESERVED now 16:59 → cancellable(until 17:00), 17:00 정각 → cancellable, 17:00:01 → deadlinePassed
3. PICKED_UP·CANCELLED → none
4. `findPendingForOffer`: 같은 offerId의 PENDING 반환, RESERVED만 있으면 null, 빈 배열 null

### (e) `domain/format.test.ts`
`formatWon(11500)` `11,500원`, `formatWon(0)` `0원`; `formatTimeRange` `18:00–20:00`(U+2013); `formatDate` `11/07`; `formatTime` 24시간(`17:00`, `09:05`); `formatQuantity('식빵 모둠', 2)` `식빵 모둠 × 2`

### (f) `infrastructure/httpReservationRepository.test.ts` (fetch 가짜)
1. `create` → `POST /v1/reservations`, 본문 `{offer_id, quantity}`, 201 응답을 camelCase·Date로
2. `listMine({page:1,size:100})` → 쿼리 `page=1&size=100`(status 없음), `status` 있으면 포함; 14필드 매핑, `cancelled_by:null` → `null`
3. `cancel` → `POST /v1/reservations/{id}/cancel`, `cancelled_by` 매핑
3-1. `get` → `GET /v1/reservations/{id}`, 14필드 매핑; 404 → `ApiError(404)` 그대로
4. 409 응답 → `ApiError(409, 'PENDING_RESERVATION_EXISTS')`가 그대로 올라옴; 알 수 없는 `status` 문자열 → 오류
5. id에 특수문자 → `encodeURIComponent`

### (g) application (가짜 포트)
1. `fetchAllMine`: total 150 → page 1·2 두 번 호출, 합쳐 150건; total 0 → 1번 호출, 빈 배열; status 전달
2. (폐기) `findMine` — D-8 단건 조회로 대체
3. `reserveOffer(repo, input, signal)`: 성공 → `created`; 409 PENDING → `pendingExists` + 찾은 id(목록 조회 status=PENDING_PAYMENT); 못 찾으면 id null; 409 OUT_OF_STOCK → throw
4. `useMyReservations`: loading → success(탭 분리); 오류 → error(errorCode·message); 빈 → success(빈 배열 둘); 언마운트 시 signal aborted, 이후 상태 변경 없음; `reload()` 재조회
5. `useCancelReservation`: pending true 동안 두 번째 호출 무시; 성공 true; 400 → error, false
6. `useReserveOffer`: 성공 → createdReservationId; 409 → pendingReservationId·error
7. `useMyReservation`: `repo.get(id)` 호출 → loading → success; 403·404 → notFound; 그 외 → error; 언마운트 abort; id 바뀌면 loading 후 재조회

### (h) presentation (`DepsProvider` 가짜 컨테이너, `vi.setSystemTime`)
1. `ReserveOfferPanel`: 기본 수량 1, 버튼 `예약하고 결제 6,000원`(단가 6000); `+` 5회 후 비활성(재고 10), 재고 3이면 3에서 비활성; `-`는 1에서 비활성; `reservable=false` → 버튼 비활성 + 사유 표시; 비로그인 클릭 → `onRequireLogin(q)`, 저장소 호출 없음; 처리 중 `처리 중…` 비활성; 201 → `onGoToCheckout(id)`; 409 PENDING → 문구 `이 상품에 결제하지 않은 예약이 이미 있어요.` + 버튼 `결제 이어하기` 클릭 시 `onGoToCheckout(찾은 id)`
2. `MyReservationList`: 로딩 Skeleton(role/testid), 빈 → `할인 보러 가기`, 에러 → Notice + `다시 시도`, 칩 `진행 중`/`지난 예약` 전환
3. `ReservationCard`: RESERVED 16:00 → PickupCode `A12345`, `매장에서 보여 주세요`, `예약 취소 · 17:00까지` 링크; 17:00:01 → `취소 마감 지남 (17:00)` 텍스트, 링크 없음; PENDING → `결제 이어하기` 버튼; STORE 취소 → `매장 사정으로 취소됨` 태그, 취소 링크·코드 없음; 미수령 → `픽업 시간 지남`; 시간대 `18:00–20:00`; 예약 시각 `HH:mm 예약`
4. `CancelReservationSheet`: `돌아가기` → onClose; `예약 취소` → cancel 호출, 처리 중 비활성, 성공 → onCancelled; 400 CANCELLATION_DEADLINE_PASSED → 서버 메시지 표시. 환불 안내 문구 단언은 D-14 확정 뒤(지금은 존재 여부만)
5. `LeaveCheckoutSheet`: 주 버튼 `결제 계속하기` → onContinue; `예약 취소하고 나가기` → cancel 후 onCancelled; `나중에 결제 (내 예약에 남음)` → onPayLater, cancel 호출 없음

### (i) E2E — 임시 `CustomerLayout`(C-5) 아래 경로로 작성. 시나리오: C2 예약 → C3 → C4 코드 표시 → C5 확정 카드 → C5a 취소 → C5b `취소됨`

## 10. 남길 작업 주석 (`code-annotations`, F19)

| 위치 | 태그 | 요약 | 언제 |
| --- | --- | --- | --- |
| `CancelReservationSheet.tsx` 환불 안내 | `TODO` | 숫자 대신 안내 문구(D-14) | 결정 후 (사용자: C5a 환불 표시) |
| `ReservationCard.tsx` 「길찾기」 | `TODO` | 지도 링크 미정(D-18) | 결정 후 (사용자: 지도 서비스) |
| `MyReservationList.tsx` 빈 상태·재시도 문구 | `TODO` | 정본 없음(D-15, D-17) | 결정 후 (디자인 시스템: E1 문구) |
| `fetchAllMine.ts` | `TODO` | 「더 보기」 미구현, 전체 조회(D-7) | 결정 후 (사용자: 지난 예약 페이지 방식) |

## 11. 변경 이력

| 날짜 | 변경 | 관련 |
| --- | --- | --- |
| 2026-11-10 | 단건 조회 확정: `ReservationRepository.get` 추가, `findMine` 삭제, `useMyReservation`이 `GET /v1/reservations/{id}` 사용(403·404 → notFound) | D-8 확정, C-3 해결, D-11 근거 갱신, §2.2·§2.3·§9 (f)(g), §10 |
| 2026-11-10 | `reserveOffer(repo, input, signal)` 서명 반영 | §2.2, §9 (g)-3 |
| 2026-11-10 | 임시 `CustomerLayout`(CUSTOMER만, 비로그인 → `/login` + from, OWNER·ADMIN → `/`)로 고객 경로 차단 해제 | C-5 임시 해결, D-10 임시 확정, §7, §9 (i) |
| 2026-11-10 | 공개 API에 `formatTime`·`displayState`·`statusLabel`·`statusTone`·`MY_RESERVATIONS_LINK_LABEL`·`DIRECTIONS_LABEL` 추가 | D-22 신설, §2.5 |
| 2026-11-10 | C3a 취소 후 홈(`/`)으로(C2 경로 생기면 변경). D-14 등 임시 문구는 임시 유지 | D-20, §4 |
