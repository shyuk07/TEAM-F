# reservations 영역(상점주 쪽) 설계안 (O1 오늘 · 픽업 처리)

- 상태: **설계안 1차 (2026-11-11)**. 사용자가 정한 값은 없다. D-번호는 모두 "임시"다. TDD는 사용자 지시로 이번 차수 생략이라 테스트 목록 절은 쓰지 않는다(구현 뒤 완료 게이트 `frontend-invariants` §6은 적용).
- **결론 먼저: O1의 핵심 동작(코드만 입력해 픽업 완료)은 백엔드에 없어서 지금은 만들 수 없다**(차단 B-1, B-2). 목록·탭·칩·정지 안내는 만들 수 있고, 픽업 제출은 Q-1 결정을 기다린다. 임시 응답이나 임시 API는 만들지 않았다.
- 대상 slice: `features/reservations`(신규, 이번에는 상점주 쪽 파일만), `pages/owner-today`, `app`(라우트 1줄 교체, `container.ts` 1줄 추가)
- 대응 화면: O1. C5(내 예약)·C3a 등 고객 쪽 reservations 파일은 담당 팀원 몫이고 같은 영역에 파일을 더한다(`customer-home.md` §5).
- 정본: `screens.md` O1(335~354줄), `wireframe.html` O1(583~610줄), `layout.md` 화면 연결, `states.md`, `open-issues.md` O1(13~14줄), `../../reference/reservations.md`(목록 263~310줄, 픽업 195~262줄), 백엔드 `reservations/presentation/router.py:75~116`·`schemas.py:54~93`·`domain/exceptions.py`, `../../requirements/reservations.md`.

## 0. 백엔드 실재 확인 (`frontend-orchestration.md` §6)

| 항목 | 확인 위치 | 결과 |
| --- | --- | --- |
| `GET /v1/stores/{store_id}/reservations?status=&page=&size=` 상점주 전용(정지된 상점주 허용). 응답 `{reservations:[{id, product_name, quantity, total_price, status, created_at}], page, size, total}`. 정렬 = 예약 시각 내림차순. `status` 한 개: `PENDING_PAYMENT`/`RESERVED`/`PICKED_UP`/`CANCELLED`. size 1~100 기본 20 | `router.py:75~93`, `schemas.py:54~71`, 명세 263~310줄 | 명세와 같다 |
| 목록 항목에 **`pickup_start`·`pickup_end`가 없다**. `offer_id`·할인 정보·고객 정보·`pickup_code`도 없다(고객 정보와 코드는 의도적으로 뺌, R-REQ25) | `schemas.py:54~64` | `open-issues.md` O1 첫째 줄이 **현재도 사실**이다(차단 B-1) |
| `POST /v1/reservations/{reservation_id}/pickup {pickup_code(1~20자)}` 200 → `{id, pickup_code, status, picked_up_at}`. **경로에 예약 ID가 필요**하다. 코드만으로 예약을 찾는 엔드포인트는 `reservations/presentation/router.py` 전체에 없다 | `router.py:108~116`, `schemas.py:83~93` | `open-issues.md` O1 둘째 줄이 **현재도 사실**이다(차단 B-2) |
| 픽업 오류: 403 해당 매장 상점주 아님, 404 예약 없음, 400 `PICKUP_OUTSIDE_WINDOW`(픽업 시작~마감 밖), 409 이미 픽업·유효하지 않은 상태(`RESERVATION_ALREADY_PICKED_UP`·`RESERVATION_INVALID_STATE`), 400 `PICKUP_CODE_MISMATCH`. 판단 순서 403 → 404 → 400(시간) → 409(상태) → 400(코드) | `exceptions.py:61~118`, 명세 249~262줄 | 명세와 같다. 시간 검사가 코드 검사보다 먼저라서 시간 밖이면 코드가 맞아도 `PICKUP_OUTSIDE_WINDOW`가 먼저 온다 |
| 미수령(결제 완료 뒤 픽업 마감이 지나도 `RESERVED`) 표시 방식은 정해지지 않았다 | 명세 195줄 | 화면에서 구분할 수단이 지금 없다(B-1 때문에 `pickup_end`를 모른다) |

## 1. slice 목록과 계층

| 계층 | slice | 대응 화면 | 안에 두는 계층 |
| --- | --- | --- | --- |
| `features` | `reservations`(신규 영역 디렉터리) | O1 (+ 이후 C2 예약 생성·C3a·C5·C5a·C5b는 담당 팀원) | domain, application, infrastructure, presentation, `wiring.ts` |
| `pages` | `owner-today` | O1 | presentation |
| `app` | `router/routes.tsx`(`ownerToday` 자리 page 교체), `container.ts`(`...wireReservations()` 1줄), `router/placeholders.tsx`(`OwnerTodayPlaceholder` 삭제), `layouts/OwnerStoreGate.tsx`(FIXME 삭제, §3) | | |

- **widgets/entities는 만들지 않는다**(D-1). 오늘 픽업 목록은 O1에서만 쓰므로 `fsd-structure` §4에 따라 widget으로 올리지 않는다. 할인 정보가 필요 없다(상점주 예약 목록에 `offer_id`가 없고 화면도 상품명·수량·금액·예약 시각만 쓴다). 그래서 `Offer`를 `entities/offer`로 내릴 이유가 O1에는 없다(`offers.md` D-1).
- 상점 ID·상점명·상태는 page가 `useOwnerStore()`(entities/store)에서 읽어 훅에 넘긴다.
- 영역 이름 충돌 방지: 고객 쪽 담당이 같은 영역에 파일을 더하므로 상점주 쪽 이름에는 `Store`·`Pickup`을 붙였다(`StoreReservationRepository`, `PickupGateway`). `ReservationRepository`는 고객 쪽에 남겨 둔다(C-3).

## 2. 파일 목록과 export

### 2.1 domain

| 파일 | export |
| --- | --- |
| `storeReservation.ts` | `type StoreReservationStatus = 'PENDING_PAYMENT'\|'RESERVED'\|'PICKED_UP'\|'CANCELLED'`, `type StoreReservation {id, productName, quantity, totalPrice, status, createdAt: Date}`, `type StoreReservationPage {items, page, size, total}` |
| `pickupQueue.ts` | `splitQueue(items, now): {waiting: StoreReservation[], doneToday: StoreReservation[]}`, `queueCounts(…)`, `isSameLocalDay(date, now)` |
| `pickupCode.ts` | `PICKUP_CODE_MAX = 20`, `validatePickupCode(raw): 'empty' \| 'too-long' \| null`, `normalizePickupCode(raw) = raw.trim()` |
| `reservationFormat.ts` | `rowTitle(r) = "{productName} × {quantity}"`, `rowMeta(r) = "{금액}원 · {HH:mm} 예약"`, `handoverLine(r) = "{productName} × {quantity} 전달하세요"` (금액은 `shared/lib/format`의 `groupDigits` + `원`) |
| `pickupGateway.ts` | 포트 `PickupGateway`(§3) 와 `PickupResult {id, status, pickedUpAt: Date}` |
| `storeReservationRepository.ts` | 포트 `StoreReservationRepository`(§3) |
| `pickupMessages.ts` | 정본 문구·임시 문구 상수, `pickupErrorMessage(info: ErrorInfo): string` |

규칙(F7):

- `splitQueue`: `waiting` = `status === 'RESERVED'`. `doneToday` = `status === 'PICKED_UP'`이고 `createdAt`이 `now`와 같은 로컬 날짜. `PENDING_PAYMENT`·`CANCELLED`는 어느 탭에도 넣지 않는다(화면 탭이 둘뿐). 정렬은 서버 순서(예약 시각 내림차순) 유지. **`doneToday`의 날짜 기준이 예약 시각인 것은 임시**다. 픽업 완료 시각이 목록에 없기 때문(D-4, Q-3). 경계: 자정 직전·직후 예약, 같은 날 0건.
- `validatePickupCode`: `trim` 뒤 비면 `'empty'`, 20자 초과 `'too-long'`(백엔드 `min_length=1, max_length=20`). 대소문자·형식 정규화는 하지 않는다(형식 미정, 명세 255줄). 경계: 공백만, 20자, 21자.
- `pickupErrorMessage`(`errorCode`로 분기, F11): `PICKUP_CODE_MISMATCH` → 「코드가 맞지 않아요. 다시 확인해 주세요.」(정본). `PICKUP_OUTSIDE_WINDOW`·`RESERVATION_ALREADY_PICKED_UP`·`RESERVATION_INVALID_STATE`·404·403·`NETWORK_ERROR` → 서버 `message` 또는 공통 임시 문구(Q-4).

### 2.2 application

| 파일 | export |
| --- | --- |
| `tokens.ts` | `StoreReservationRepositoryToken`, `PickupGatewayToken` |
| `useStoreQueue.ts` | `useStoreQueue(storeId): {status:'loading'\|'success'\|'error', waiting, doneToday, counts:{waiting,done}, hasMore, loadMore, reload}`. `RESERVED`와 `PICKED_UP`을 각각 한 번씩(size 100, 최신순) 요청해 합친다. 창이 다시 포커스를 받으면 `reload()`(D-5) |
| `completePickup.ts` | 유스케이스 `completePickup(deps:{gateway}, input:{reservationId, code})` — `validatePickupCode` 후 `gateway.pickup` |
| `usePickup.ts` | `usePickup(onDone): {submit(code), status:'idle'\|'running'\|'error', errorMessage, lastDone: {reservation, doneAt} \| null, reset}`. 성공하면 `lastDone`에 방금 처리한 행(목록에서 `id`로 찾음)을 담고 큐를 `reload()` |
| `useRun.ts` | 제출 흐름(중복 제출 방지, 언마운트 abort). `offers.md` D-9와 같은 이유로 영역 안에 둔다 |

- 모든 훅은 `useDep(토큰)`으로 포트를 받는다(F18). 요청은 `AbortController`로 정리(F10).
- **`usePickup.submit(code)`가 어떤 예약을 대상으로 하는지는 Q-1이 정한다.** 아래 두 안 중 하나가 결정되면 `completePickup`의 `input`이 정해진다(§3).

### 2.3 infrastructure

| 파일 | 내용 |
| --- | --- |
| `storeReservationDto.ts` | `StoreReservationListDto`, `toStoreReservation`(`created_at` → `Date`, 알 수 없는 `status`는 오류). 이 파일 안에서만 쓴다(F9) |
| `httpStoreReservationRepository.ts` | `GET /v1/stores/{id}/reservations?status=&page=&size=` |
| `httpPickupGateway.ts` | `POST /v1/reservations/{id}/pickup` 본문 `{pickup_code}` → `PickupResult` |

### 2.4 presentation

| 파일 | 하는 일 |
| --- | --- |
| `PickupTabs.tsx` | 칩 「픽업 대기 N」「완료 N」(`Chip`, `shared/ui/Chip`은 `offers.md` §2.5가 추가) |
| `PickupList.tsx` | 행 목록(`TableRow` 또는 `Box`). 행 선택·버튼 없음(화면 명세). 로딩·빈·오류 표시 |
| `PickupRow.tsx` | `rowTitle`, 금액, `HH:mm 예약`. **「픽업 시간」 칸은 데이터가 없어 그리지 않는다**(B-1, D-6) |
| `HandoverNotice.tsx` | 방금 처리 확인 상자(초록, `Box`/`Notice`): 「✓ 픽업 완료」「방금」「{상품} × {수량} 전달하세요」「{HH:mm} 예약 · 완료 목록으로 옮겼어요」 |
| `PickupCodeForm.tsx` | 「픽업 코드 입력」 라벨, 안내 「고객 화면의 코드를 입력해야 픽업 완료돼요.」, `Input`, `FieldError`(입력칸 바로 아래), 「픽업 완료」 버튼. 모바일은 `.cta` 안, PC는 `.split.r` 우측 패널 안(`.dk`)에 같은 상태를 공유하는 두 벌(`LoginPage` 방식) |

### 2.5 공개 API (`features/reservations/index.ts`, 상점주 쪽)

```ts
export type { StoreReservation, StoreReservationStatus } from './domain/storeReservation'
export { splitQueue } from './domain/pickupQueue'
export { StoreReservationRepositoryToken, PickupGatewayToken } from './application/tokens'
export { useStoreQueue } from './application/useStoreQueue'
export { usePickup } from './application/usePickup'
export { PickupTabs } from './presentation/PickupTabs'
export { PickupList } from './presentation/PickupList'
export { HandoverNotice } from './presentation/HandoverNotice'
export { PickupCodeForm } from './presentation/PickupCodeForm'
```

- `wiring.ts`(`wireReservations()`)가 등록하는 토큰: `StoreReservationRepositoryToken`(`HttpStoreReservationRepository`), `PickupGatewayToken`(`HttpPickupGateway`). 고객 쪽 담당이 자기 토큰을 같은 함수에 더한다(토큰당 한 곳 등록, F18). `app/container.ts`에 `...wireReservations()` 한 줄, `tests/app/container.test.ts` 토큰 목록에 두 토큰을 같은 커밋에서 더한다(`layer-architecture` §6.7).
- `index.ts`는 구현체·DTO·wiring을 내보내지 않는다.

## 3. 포트

| 포트 | 위치 | 메서드 | 토큰 | 구현체 · 소유 |
| --- | --- | --- | --- | --- |
| `StoreReservationRepository` | `features/reservations/domain/storeReservationRepository.ts` | `findByStore(storeId, status, page, size, signal?): Promise<StoreReservationPage>` | `StoreReservationRepositoryToken` | `HttpStoreReservationRepository` · reservations |
| `PickupGateway` | `features/reservations/domain/pickupGateway.ts` | `pickup(reservationId, code, signal?): Promise<PickupResult>` — **지금 백엔드가 지원하는 유일한 형태**. `pickupByCode(storeId, code, signal?)`는 **백엔드 API가 생긴 뒤에만 포트에 더한다**(만들지 않음, 차단 B-2) | `PickupGatewayToken` | `HttpPickupGateway` · reservations |

## 4. 화면 상태와 동작 (O1)

- 문구(정본): 「픽업 완료」(버튼), 칩 「픽업 대기 N」「완료 N」, 상태 태그 「영업 중」(`storeStatusLabel`), 입력 라벨 「상품 · 수량」「픽업 시간」「금액」「예약 시각」(표 머리, **「픽업 시간」 열은 B-1 해소 전 그리지 않음**), 「픽업 코드 입력」·「고객 화면의 코드를 입력해야 픽업 완료돼요.」, 오류 「코드가 맞지 않아요. 다시 확인해 주세요.」.
- 상태: 로딩(`Skeleton`), 빈(해당 탭에 0건: E1 공통 `EmptyState`, 문구 정본 없음 → 임시 Q-4), 오류(「다시 시도」), 성공. 탭 기본은 「픽업 대기」.
- 정지 상점(`useOwnerStore().status === 'SUSPENDED'`): `.body` 맨 위, 확인 상자 위에 기존 `StoreSuspendedNotice`(features/stores)를 놓는다 → **이것으로 `OwnerStoreGate.tsx`의 FIXME(정지 안내 고정)를 해소**한다(D-3). page는 `features/stores`의 공개 API를 import한다(pages → features 허용). 정지여도 목록 조회·픽업은 백엔드가 허용하므로(`SuspendedAllowedOwnerUser`) 화면은 막지 않는다. 폐점 상태(`CLOSED`) 안내는 `stores.md` 소관(가드가 처리)이라 O1은 `ACTIVE`·`SUSPENDED`만 가정한다.
- 헤더: `.bar`에 상점명 + `StatusTag`, `OwnerTopNav`(오늘·할인·매장), `OwnerAccountButton`. 하단 탭은 `OwnerStoreGate`가 붙인다(`TAB_BAR_HANDLE`).
- 레이아웃: 모바일은 `.body` 목록 + `.cta` 코드 입력, PC는 `.split.r`(목록 | 코드 입력 패널).
- 픽업 성공(해당하는 안이 정해지면): 코드 입력칸 비움, 확인 상자 표시, 그 행이 「완료」로 이동(큐 `reload`), 상자는 다음 제출 또는 탭 이동까지 유지(임시, D-7).
- 새로고침: 창이 포커스를 되찾을 때 큐를 다시 불러온다(자동 주기 폴링 없음, D-5).

### 4.1 픽업 제출 — 차단된 부분 (Q-1이 정함)

화면 명세는 "행을 고르지 않고 코드만 입력해 픽업"이다. 백엔드는 "예약 ID + 코드"다. 선택지:

| 안 | 내용 | 영향 |
| --- | --- | --- |
| A. 화면을 백엔드에 맞춤 | 행을 눌러 선택 → 코드 입력 → `POST /v1/reservations/{id}/pickup`. 화면 명세의 "행 선택·버튼 없음"과 "코드 없이 완료할 버튼 없음" 중 앞의 것만 바뀜 | 프론트만 바꾸면 됨. 디자인 시스템(`screens.md`/`wireframe.html`) 수정은 소유자 몫 |
| B. 백엔드에 코드 조회 API 추가 | `open-issues.md`가 요청한 "상점 범위 안에서 코드로 픽업" API(예: `POST /v1/stores/{id}/pickup {pickup_code}`) | 백엔드 작업. 생기면 `PickupGateway.pickupByCode` 추가, 화면은 명세 그대로 |
| C. 프론트에서 반복 호출 | `RESERVED` 예약마다 `POST …/pickup`을 차례로 보내 코드가 맞는 것을 찾음 | **권하지 않음**: 요청 폭주, `PICKUP_OUTSIDE_WINDOW`(시간 검사가 코드 검사보다 먼저)와 코드 불일치를 구분할 수 없음, 틀린 코드 시도를 서버가 잠금할 수 있음 |

설계자는 어느 안도 정하지 않는다(Q-1). 안이 정해지기 전에 구현자는 `PickupCodeForm`을 만들되 제출 버튼이 호출하는 훅은 만들지 않고 `// TODO` 주석(§9)을 남긴다.

## 5. 결정 표 (모두 임시)

| D | 항목 | 값 | 임시/확정 | 근거 |
| --- | --- | --- | --- | --- |
| D-1 | slice | `features/reservations`(영역)와 `pages/owner-today`. widgets·entities 없음 | 임시 | `fsd-structure` §4, §1.1 `reservations`·O1 |
| D-2 | 영역 이름 규칙 | 상점주 쪽 포트·토큰은 `StoreReservationRepository`·`PickupGateway`, 고객 쪽은 담당이 `ReservationRepository` 사용 | 임시 | 같은 영역 안 이름 충돌 방지(C-3) |
| D-3 | 정지 안내 위치 | `StoreSuspendedNotice`를 O1 `.body` 맨 위. 정지여도 O1 목록·픽업은 열어 둠 | 임시 | `OwnerStoreGate.tsx` FIXME, `stores.md` §4.4·D-22 |
| D-4 | 「완료」 탭 범위 | `PICKED_UP` 중 예약 시각이 오늘(로컬)인 것. 「픽업 대기」는 `RESERVED` 전부(최신 100건) | 임시 | 픽업 시각·완료 시각이 목록에 없다(B-1). "오늘"의 정의는 Q-3 |
| D-5 | 새로고침 | 포커스 복귀 시 재조회. 주기 폴링 없음 | 임시 | 명세에 갱신 방식 없음 |
| D-6 | 「픽업 시간」 | 데이터가 오기 전까지 행에서 뺌 | 임시 | `open-issues.md` O1 첫 줄(숫자·시간을 지어내지 않음) |
| D-7 | 확인 상자 수명 | 다음 제출 성공·탭 전환·페이지 이탈까지 | 임시 | `screens.md` O1 "목록 위에 초록 확인 상자", 해제 조건 정본 없음 |
| D-8 | 100건 초과 | `hasMore`면 「더 보기」로 이어 붙임(문구는 offers의 `LOAD_MORE_LABEL`과 같은 말을 이 영역 상수로 복사) | 임시 | 영역끼리 import 금지(F1) |
| D-9 | 코드 입력 정규화 | `trim`만. 대문자화·하이픈 제거 없음 | 임시 | 코드 형식 정본 없음(`reference/reservations.md` 255줄) |

## 6. 정합 이슈

| C | 내용 | 양쪽 근거 |
| --- | --- | --- |
| C-1 | 화면은 상점주 목록에 「픽업 시간」이 있다고 보지만 API 응답에 없다 | `wireframe.html` 590~595줄·`screens.md` O1 ↔ `reservations/presentation/schemas.py:54~64` |
| C-2 | 화면은 "행을 고르지 않고 코드만 입력해 픽업"이지만 API는 예약 ID가 필요하다 | `screens.md` O1 동작 메모 ↔ `reservations/presentation/router.py:108~116` |
| C-3 | `features/reservations`는 고객 쪽(C2 예약 생성·C3a·C5…, 담당 팀원)과 같은 영역이다. 같은 파일(`tokens.ts`, `wiring.ts`, `index.ts`, `container.test.ts`)을 두 사람이 고칠 수 있다 | `customer-home.md` §5, `fsd-structure` §1.1 |
| C-4 | 화면 칩 「완료 11」은 "오늘 완료"로 읽히지만 목록 API에는 완료 시각이 없고 `total`은 상태 전체 건수다 | `wireframe.html` 590줄 ↔ `reference/reservations.md` 282줄 |
| C-5 | `reference/reservations.md` 138줄(고객 목록) 등에서 이미 쓰는 "픽업 시간"은 고객 쪽 목록 응답에도 아직 없다고 적혀 있다. 고객 C5 담당과 같은 질문이 될 수 있다 | `reference/reservations.md` 138줄 |

## 7. 차단 이슈와 질문 목록

차단:

- **B-1**: 상점주 예약 목록에 `pickup_start`·`pickup_end` 없음 → 「픽업 시간」 열, "오늘 픽업"의 정확한 구분, 미수령 구분 불가. 풀리는 조건: 백엔드가 목록 항목에 두 필드를 더함(`open-issues.md` O1 첫 줄).
- **B-2**: 코드만으로 픽업하는 API 없음 → O1의 「픽업 완료」를 화면 명세대로 만들 수 없음. 풀리는 조건: Q-1에서 A(화면 변경)/B(백엔드 API) 중 선택.

질문:

- Q-1: 픽업 제출을 어떻게 할 것인가(§4.1의 A·B·C). 설계자 의견: A는 지금 바로 가능하고 B는 명세가 원하는 흐름이다. C는 권하지 않는다.
- Q-2: B-1을 해소하기 위해 백엔드에 두 필드를 요청할 것인가. 요청하지 않으면 「픽업 시간」 열을 영구히 뺀다.
- Q-3: "오늘"의 정의. (a) 픽업 시작일이 오늘인 예약만(B-1 필요) (b) 지금 임시(D-4)처럼 `RESERVED` 전부 + 오늘 예약한 `PICKED_UP`. 미수령(`RESERVED` 그대로)이 「픽업 대기」에 계속 쌓이는 문제(명세 195줄)도 같이 정해야 한다.
- Q-4: 정본 문구가 없는 것들: 빈 상태(두 탭), 오류 기본 문구, `PICKUP_OUTSIDE_WINDOW`·409·404 화면 문구(서버 `message`를 그대로 보일지).
- Q-5: O7 폐점을 막는 항목 보여 주기(`StoreCloseForm` TODO). 픽업 대기 예약 수는 이 영역의 `RESERVED` 목록 `total`로 만들 수 있다(`useStoreQueue`의 `counts.waiting` 또는 `findByStore(…RESERVED,1,1).total`). 단 미수령 예약은 폐점을 막지 않는데(명세 195줄) 화면에서 구분할 수 없다(B-1). 이번 범위에서는 결정하지 않는다. 적용하면 `pages/store-close`가 두 영역(offers, reservations)의 훅 값을 `StoreCloseForm`에 prop으로 넘기는 방식을 권한다(`offers.md` Q-5).

## 8. 연결 정리 (자리 page · 가드)

| 파일 | 변경 |
| --- | --- |
| `src/app/router/routes.tsx` | `ROUTES.ownerToday`의 `<OwnerTodayPlaceholder />` → `<OwnerTodayPage />` (`pages/owner-today`) |
| `src/app/router/placeholders.tsx` | `OwnerTodayPlaceholder` 삭제. `offers.md`의 O2·O3 교체와 함께 하면 상단 TODO의 O1·O2·O3 항목이 모두 해소되고 C2·C5 자리 page만 남는다. TODO의 `언제:`를 `C2 구현 시, C5 구현 시`로 줄인다 |
| `src/app/layouts/OwnerStoreGate.tsx` | 상단 FIXME 삭제(O1이 정지 안내를 그리므로). 가드 동작은 불변 |

## 9. 남길 작업 주석 (`code-annotations`)

| 태그 | 위치 | 요약 | 왜 | 언제 |
| --- | --- | --- | --- | --- |
| FIXME | `PickupCodeForm.tsx` (제출 연결 자리) | 픽업 제출이 연결되지 않았다. 코드를 입력해도 픽업 완료가 처리되지 않는다 | 코드만으로 픽업하는 API가 없다 (owner-today.md B-2, Q-1) | 결정 후 (사용자: 픽업 제출 방식), 늦어도 배포 전 |
| TODO | `PickupRow.tsx` | 「픽업 시간」 열이 없다 | 목록 응답에 pickup_start·pickup_end가 없다 (owner-today.md B-1) | 결정 후 (백엔드: 목록에 픽업 시간 추가) |
| TODO | `pickupQueue.ts` | 「완료」 범위를 예약 시각 기준으로 임시 정했다 | 완료 시각이 목록에 없다 (owner-today.md D-4, Q-3) | 결정 후 (사용자: 오늘의 정의) |
| TODO | `pickupMessages.ts` | 빈 상태·오류 문구가 임시다 | content.md에 정본이 없다 (owner-today.md Q-4) | 결정 후 (디자인 시스템: content.md 문구 확정) |
| open-issues | `PickupList.tsx` | `// open-issues: O1 픽업 시간·고객 정보·픽업 코드는 목록에 없음` | `open-issues.md` O1 | (한 줄 형식) |
| 해소 | `OwnerStoreGate.tsx` FIXME, `placeholders.tsx` TODO(O1 부분) | §8 | O1 구현 | 이 구현에서 |
| 해소 | `StoreCloseForm.tsx` TODO | **해소하지 않음**(Q-5, 이번 범위 밖). `언제:`는 그대로 | | |

`FIXME` 하나는 "O1 구현 시"에 풀지 못하는 일이다(B-2). 배포 전 점검(`list --tag FIXME`)에 걸리게 두는 것이 의도다.

## 10. 구현 순서 제안

1. Q-1 결정(최소한 A/B 선택)을 받는다. 결정 없이 가능한 범위: 목록·탭·칩·정지 안내.
2. features/reservations: domain → 포트·DTO·구현체·토큰·wiring(+`container.ts`, `container.test.ts`) → `useStoreQueue` → presentation → `pages/owner-today` → 라우트·자리 page 정리.
3. 완료 게이트 `frontend-invariants` §6, 화면 흐름 변경이므로 `npm run test:e2e`.
