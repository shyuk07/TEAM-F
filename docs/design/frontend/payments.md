# payments 영역 설계: 결제(C3)·결제 완료(C4)

- 대상 화면: C3 결제, C4 결제 완료(예약 확정), E1(해당분). C3a 시트는 `reservations.md`(`LeaveCheckoutSheet`)
- 정본: screens.md C3·C4, content.md(포인트·적립 표기), states.md("적립 예정"), `../../reference/payments.md` §1, 실제 응답 `../../../backend/src/payments/presentation/schemas.py`, 포인트 규칙 `../../requirements/payments.md` REQ-17~21·26·27
- 지킬 규칙: F1~F19, `layer-architecture` §5·§6, `tdd-workflow` §2

## 1. 계층 배치

| FSD 계층 | slice | 화면 | 비고 |
| --- | --- | --- | --- |
| features | `features/payments` | C3 결제 폼 | 영역 slice |
| pages | `pages/checkout` | C3 + C3a | `reservations.useMyReservation(id)`로 요약, `auth.useAuth()`로 보유 포인트(`user.point`)를 읽어 `PaymentForm`에 prop으로 넘김(F1: features끼리 import 금지) |
| pages | `pages/payment-complete` | C4 | `reservations.useMyReservation(id)`로 픽업 코드·시간·주소·취소 가능 시각 |

## 2. 파일 목록과 export (`features/payments`)

### 2.1 domain

| 파일 | export |
| --- | --- |
| `domain/payment.ts` | `type PaymentStatus = string`(백엔드 enum 값 확인 필요, C-3), `type Payment = { id: string; reservationId: string; amount: number; status: PaymentStatus; paidAt: Date \| null }` |
| `domain/point.ts` | `POINT_UNIT = 100`, `maxUsablePoint(balance: number, total: number): number` (= `floor(min(balance, total)/100)*100`, 음수 → 0), `type PointInputError = 'notInteger' \| 'notUnit' \| 'overBalance' \| 'overTotal' \| null`, `validatePointInput(raw: string, balance: number, total: number): { value: number; error: PointInputError }` (빈 문자열 = 0), `payAmount(total: number, usePoint: number): number`, `earnPreview(amount: number): number` (`amount <= 99`이면 0, 아니면 `floor(amount × 0.01)`) |
| `domain/format.ts` | `formatWon(n)`, `formatPoint(n)` (`1,240P`) |
| `domain/messages.ts` | 입력 오류 문구(D-5, 임시), `payErrorMessage(e: { status: number; errorCode: string; message: string }): string`(서버 message, 비면 임시 대체 문구, D-7) |

규칙 근거: 100P 단위·보유 이하 REQ-17, 총액 이하 REQ-21, 총액 끝자리(100 미만)는 포인트 불가 REQ-27(그래서 `floor(.../100)*100`), 적립 1% 버림 REQ-18, 99원 이하 미적립 REQ-26.

### 2.2 application

| 파일 | export |
| --- | --- |
| `domain/ports.ts` | `interface PaymentRepository { pay(input: { reservationId: string; usePoint: number }, signal?: AbortSignal): Promise<Payment> }` |
| `application/tokens.ts` | `PaymentRepositoryToken` |
| `application/errorInfo.ts` | 내부(`reservations.md` C-9) |
| `application/usePay.ts` | `usePay(): { pay(input): Promise<Payment \| null>; pending: boolean; error: { status: number; errorCode: string; message: string } \| null }`(`status`는 409 분기용, C-2) — 처리 중 중복 호출 무시, 실패해도 예약은 그대로(재시도 가능, REQ-32) |

### 2.3 infrastructure

`infrastructure/httpPaymentRepository.ts`: `class HttpPaymentRepository implements PaymentRepository` — `POST /v1/payments {reservation_id, use_point}` → 201 `{id, reservation_id, amount, status, paid_at}` → `Payment`(`paid_at` null 유지).

### 2.4 presentation

`presentation/PaymentForm.tsx`: `PaymentForm(props: { reservationId: string; productName: string; quantity: number; totalPrice: number; pointBalance: number; onPaid(payment: Payment): void })` — KeyValue 요약, Input 「포인트 사용 (100P 단위)」, Chip 「전액」(= `maxUsablePoint`), 적립 예정 `결제 후 {N}P 적립 (1%)`, CtaBar 「결제하기 {formatWon(payAmount)}」.

### 2.5 공개 API·wiring

- `index.ts`: `PaymentForm`, `type Payment`
- `wiring.ts`: `wirePayments()` = `bind(PaymentRepositoryToken, new HttpPaymentRepository())`, `app/container.ts`에 한 줄

### 2.6 pages

- `pages/checkout/presentation/CheckoutPage.tsx`: 예약 로딩(Skeleton) / 못 찾음·오류(Notice) / 예약이 PENDING_PAYMENT가 아니면 결제 폼 대신 안내(D-6) / 성공 → `PaymentForm`. 뒤로 가기(AppBar ←) → `LeaveCheckoutSheet`. 결제 성공 → C4 경로(`reservationId` 전달).
- `pages/payment-complete/presentation/PaymentCompletePage.tsx`: `useMyReservation(reservationId)`(단건 GET, D-1) → StatusTag 「예약 확정」, PickupCode + `매장에서 이 코드를 보여 주세요`, KeyValue 「픽업」(시간대)·「매장」(매장명·주소)·「취소 가능」(`오늘 HH:mm까지`), 버튼 「길찾기」(reservations D-18) / 「내 예약 보기」 → C5. 로딩 Skeleton, 못 찾음 Notice + 「내 예약 보기」.

## 3. C4 픽업 코드를 얻는 방법 (근거)

- `PaymentResponse`(schemas.py)는 `id, reservation_id, amount, status, paid_at`만 있고 **픽업 코드가 없다**.
- `ReservationCreateResponse`(reservations schemas.py)도 픽업 코드·픽업 시간이 없다.
- 백엔드가 예약 단건 조회 `GET /v1/reservations/{id}`를 추가했다(`../../reference/reservations.md` §2-1). 응답에 `pickup_code`·`pickup_address`·`pickup_start/end`·`cancellable_until`이 있다.
- 결정(D-1, 확정): C4는 URL의 `reservationId`로 `reservations.useMyReservation(id)`(= `ReservationRepository.get`)를 호출한다. 목록 순회 방식은 폐기. open-issues.md C4 "이슈 18"의 답: **예약 단건 조회로 다시 받는다.**

## 4. 결정 표

| D | 항목 | 값 | 임시/확정 | 근거 | 차단 |
| --- | --- | --- | --- | --- | --- |
| D-1 | C4 픽업 코드 출처 | 예약 단건 조회 `GET /v1/reservations/{id}`(`useMyReservation`). 목록 순회 폐기 | 확정 | §3, reservations.md D-8 | 아니오 |
| D-2 | 포인트 단위·상한 | 100P 단위, ≤ min(보유, 총액) 내림 100 | 확정 | 발주서 3, REQ-17·21·27 | 아니오 |
| D-3 | 적립 예정 표시 | floor(결제 금액 × 1%), 99원 이하 0 → 0이면 줄 숨김(숨김은 임시) | 계산 확정 / 숨김 임시 | REQ-18·26, states.md | 아니오 |
| D-4 | 보유 포인트 출처 | `auth.useAuth().state.user.point`(page가 전달) | 임시 | auth.md `User.point` | 아니오 |
| D-5 | 입력 오류 문구 | 정본 없음 → 임시: 단위 `100P 단위로 입력해 주세요.` / 보유 초과 `보유 포인트보다 많이 쓸 수 없어요.` / 총액 초과 `결제 금액보다 많이 쓸 수 없어요.` | **임시, 사용자 결정 필요** | content.md에 없음 | 아니오 |
| D-6 | PENDING이 아닌 예약으로 C3 진입 | 결제 폼 대신 안내 + 「내 예약 보기」 | 임시 | 정본 없음 | 아니오 |
| D-7 | 결제 오류 문구 | 서버 message(400 `RESERVATION_NOT_PAYABLE`·`PAYMENT_FAILED`·`INVALID_POINT_AMOUNT`·`VALIDATION_ERROR`, 409) | 임시 | reference/payments.md §1, F11 | 아니오 |
| D-8 | 경로 | C3 `/checkout/:reservationId`, C4 `/checkout/:reservationId/complete`. 임시 `CustomerLayout` 아래 | 임시 확정(정식 고객 셸 설계 때 재검토) | reservations.md C-5 임시 해결 | 아니오 |
| D-9 | 결제 후 보유 포인트 갱신 | C4에서 `useAuth().reload()`를 **호출하지 않음**(reload가 세션을 loading으로 바꾸면 `CustomerLayout`이 C4를 다시 마운트해 반복될 위험). 보유 포인트는 다음 세션 조회 때 갱신 | 임시 | 갱신 규칙 정본 없음. 정식 고객 셸·세션 갱신 방식 설계 때 재검토 | 아니오 |

## 5. 정합 이슈

| C | 내용 | 근거 |
| --- | --- | --- |
| C-1 | screens.md C4 "결제 응답 → 예약 확정"의 표시 항목(픽업 코드 등)이 결제 응답에 없음 | schemas.py `PaymentResponse`, screens.md C4 |
| C-2 | 결제 409(`PaymentConflictError`)는 라우터가 `HTTPException(detail=...)`으로 던져 응답 `error_code` 값이 공통 핸들러(`error_handlers.py:77`)에 달려 있다. 화면은 status 409로만 분기하도록 설계(error_code 확정 필요) | backend payments/presentation/router.py:63-64 |
| C-3 | `PaymentStatus` enum 값을 reference가 나열하지 않음. 화면은 status를 쓰지 않으므로 string으로 둠 | reference/payments.md §1, payments/domain/payment.py |
| C-4 | reference/payments.md §1 "확인 필요": 다른 사람 예약 결제 시 응답(403 없음) — 화면 분기 없음, 기록만 | reference/payments.md:68 |

## 6. 질문 목록

1. 포인트 입력 오류 문구(D-5), 적립 0원일 때 줄 숨김(D-3)
2. 결제 409 error_code(C-2)
3. 정식 고객 셸(reservations.md C-5, D-8) — 임시 `CustomerLayout`으로 차단 해제
4. 결제 후 포인트 재조회 방식(D-9)

## 7. 테스트 목록 (`tests/features/payments/`)

### (a) `domain/point.test.ts`
1. `maxUsablePoint(1240, 11500)` → 1200; `(50000, 11550)` → 11500; `(99, 5000)` → 0; `(0, 5000)` → 0; `(1000, 0)` → 0
2. `validatePointInput('', 1240, 11500)` → `{0, null}`; `'500'` → null; `'550'` → notUnit; `'1300'` → overBalance; 보유 50000·총액 11550에서 `'11600'` → overTotal; `'abc'`·`'-100'`·`'1.5'` → notInteger
3. `payAmount(11500, 500)` → 11000; `(11500, 0)` → 11500; 전액 포인트 → 0
4. `earnPreview(11500)` → 115; `(99)` → 0; `(100)` → 1; `(0)` → 0; `(199)` → 1
5. `formatPoint(1240)` `1,240P`

### (b) `infrastructure/httpPaymentRepository.test.ts`
1. `POST /v1/payments`, 본문 `{reservation_id, use_point}`; 201 → `Payment`(`paidAt` Date, null 유지)
2. 400 `INVALID_POINT_AMOUNT` → ApiError 그대로

### (c) `application/usePay.test.tsx`
1. pending 중 두 번째 호출 무시; 성공 → Payment 반환, error null; 실패 → null + error `{status, errorCode, message}`(409면 status 409), pending false; 언마운트 후 상태 변경 없음
2. `payErrorMessage({status, errorCode, message})`: message 있으면 그대로, 비면 대체 문구

### (d) `presentation/PaymentForm.test.tsx`
1. 초기 버튼 `결제하기 11,500원`(총액 11500), 적립 `결제 후 115P 적립 (1%)`
2. 「전액」 → 입력 1200(보유 1240), 버튼 `결제하기 10,300원`
3. `550` 입력 → 오류 문구 표시 + 버튼 비활성(문구 단언은 D-5 확정 뒤, 지금은 버튼 비활성만)
4. 클릭 → `pay({reservationId, usePoint})`, `처리 중…` 비활성, 성공 → `onPaid`
5. 서버 오류 → message 표시, 버튼 다시 활성

### (e) pages (임시 `CustomerLayout` 아래)
1. CheckoutPage: 로딩 Skeleton / 못 찾음 Notice / PENDING 아님 안내 / ← → C3a 시트
2. PaymentCompletePage: 단건 조회(`get`) 결과로 코드 `A12345`, `매장에서 이 코드를 보여 주세요`, `예약 확정` 태그, `18:00–20:00`, `내 예약 보기` 이동

## 8. 남길 작업 주석

| 위치 | 태그 | 요약 | 언제 |
| --- | --- | --- | --- |
| `domain/messages.ts` 입력 오류 문구 | `TODO` | 임시 문구(D-5) | 결정 후 (사용자: 포인트 오류 문구) |
| `PaymentCompletePage.tsx` 포인트 재조회 | `TODO` | 결제 뒤 `useAuth().reload()` 미호출(D-9) | 결정 후 (사용자: 고객 셸·세션 갱신 방식) |

## 9. 변경 이력

| 날짜 | 변경 | 관련 |
| --- | --- | --- |
| 2026-11-10 | C4 픽업 코드를 예약 단건 조회(`GET /v1/reservations/{id}`)로 확정, 목록 순회 폐기 | D-1 확정, §3, §8 |
| 2026-11-10 | `usePay().error`에 `status` 추가, `payErrorMessage` 인자 `{status, errorCode, message}` | §2.1·§2.2, §7 (c) |
| 2026-11-10 | 임시 `CustomerLayout` 아래 C3·C4 경로 연결(차단 해제) | D-8 임시 확정, §6 |
| 2026-11-10 | C4에서 `useAuth().reload()` 미호출(재마운트 반복 위험) | D-9 변경(임시), §8 |
