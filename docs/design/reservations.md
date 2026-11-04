# reservations 모듈 설계안 (예약·취소·픽업)

- 작성 기준일: 2026-11-04, 브랜치 `claude/reservations` (`origin/main` 3fe2389 기준)
- 대상: `src/reservations` (테이블 `pickup_reservations`)
- 기준 문서: `docs/reference/reservations.md`, `docs/reference/README.md`, `.claude/skills/db-schema/{SKILL.md,schema.sql}`, `docs/design/{catalog,payments,stores,auth}.md`, `src/catalog/**`, `src/payments/**`, `src/container.py`, `src/main.py`
- 이 문서는 설계만 담습니다. 코드는 수정하지 않았습니다.
- **임시 기본값은 확정이 아니라 제안입니다.** 모두 `reservations/domain/rules.py` 한 파일(또는 enum)에 모아 나중에 바꾸기 쉽게 합니다(9절).
- 결정 표(D-번호)는 8절, 다른 모듈에 필요한 변경(C-번호)은 9절, 사용자 질문(Q-번호)은 10절입니다.

---

## 0. 차단 이슈

| # | 확인 명령 | 결과 | 의미 / 해결 |
| --- | --- | --- | --- |
| B-1 | `(cd src && uv run python -c "import main")` | 성공 (`IMPORT_OK`) | 현재 코드는 불러와집니다. |
| B-2 | `uv run python -c "import jwt, passlib, sqlalchemy, asyncpg, fastapi, httpx, anyio"` | 모두 설치됨 | 새 의존성 없음. `Form`/`File`을 쓰지 않아 `python-multipart`도 불필요. |
| B-3 | `.env.example` 확인 | `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | reservations가 새로 요구하는 키 없음. |
| B-4 | `python3 .claude/skills/layer-check/check_layers.py` | **위반 2건**, 경고 3건 | **기준선(이 설계와 무관)**: `payments/application/service.py:19`, `:20`이 `payments.infrastructure`를 import(`[의존방향]`). 경고 3건은 `error_handlers.py`의 넓은 예외 핸들러. reservations 파일은 모두 0바이트라 새 위반 없음. 구현 후에도 위반이 이 2건에서 늘지 않아야 합니다. |
| B-5 | `Glob`/`wc -l src/reservations/**` | 모든 `.py`가 0줄(`domain/pickup_reservation.py`, `domain/reservation.py` 포함) | 빈 골격만 있습니다. `reservation.py`는 대응 테이블이 없어(db-schema 3절) 쓰지 않을 것을 제안합니다(D-23). |
| B-6 | `src/catalog/**`에서 `deduct_stock`·`restore_stock`·`reserve` 검색 | **catalog에 재고 차감·복구 서비스 메서드와 도메인 메서드가 없음.** `DiscountOffer`에는 `adjust_stock`(상점주 수동 조정)만 있고 `StockLog`는 `initial_stock`/`manual_adjustment`/`offer_edit` 팩토리뿐 | **제한 사항(사용자 결정 2026-11-04: reservations만 구현, 재고는 fake/임시)**: 실제 재고 차감·복구·`stock_log`는 catalog 변경(C-1)이 머지돼야 동작합니다. 그 전까지 container는 읽기 전용 임시 포트(7.1절, D-25)를 연결하므로 **실서버에서 예약이 재고를 줄이지 않습니다.** 도메인·응용 계층은 fake `StockPort`로 구현·테스트합니다. |
| B-7 | `src/payments/application/{ports,service,reservation_stub}.py` | payments `ReservationPort`는 `get`, `mark_paid` 두 개뿐. `cancel_for_refund`, `refund_for_cancelled_reservation`, `Payment.user_id`, container 연결이 없음(`get_payment_service`가 `InMemoryReservationPort()`를 직접 만듦). `payments.reservation_id`는 `unique=True`이고 FK 없음 | **차단 아님**: 예약 취소 시 환불 호출은 임시 구현으로 연결하고(D-15), payments 쪽 변경은 C-3~C-5로 올립니다. |
| B-8 | `src/container.py` | `create_reservation_lookup`·`create_reservation_cancel`이 인자 없는 함수로 `NoReservationLookup`·`NoReservationCancel` 싱글턴을 돌려줌(CI-10, CI-11 표시) | reservations 구현 PR이 이 두 팩토리를 교체해야 합니다(5절). `tests/catalog/test_wiring.py`의 `NoReservation*` 단언도 함께 바뀝니다(C-2). |
| B-9 | 원격 브랜치 `git branch -r`, `git diff origin/main...<브랜치> -- src/reservations docs/design/reservations.md tests/reservations`, `git ls-tree -r origin/main` | `origin/claude/auth-optional-user`, `origin/claude/epic-fermat-c6nae5`, `origin/claude/improve-agents-skills`, `origin/feat/stores`, `origin/feature/payments` 모두 reservations 변경 없음. `origin/main`의 reservations 파일은 `chore: setup` 커밋의 빈 골격뿐 | **겹치는 작업 없음.** |
| B-10 | `git status --short` (설계 작성 전) | 변경 없음 | 깨끗한 worktree. |

---

## 1. 도메인 (`domain/`)

파일: `pickup_reservation.py`, `offer_ref.py`, `rules.py`, `exceptions.py`, `repository.py`, `service.py`. 모두 순수 파이썬(R1)입니다. 다른 모듈은 import하지 않습니다(R11).

### 1.1 용어

| 용어 | 뜻 | 출처 |
| --- | --- | --- |
| 예약 (`PickupReservation`) | 회원이 할인(`offer`)의 수량을 잡아 둔 것. 결제 후 매장에서 픽업 | 명세, `pickup_reservations` |
| 예약번호 (`pickup_code`) | 상점주가 픽업 때 확인하는 코드 | 명세 §4 |
| 할인 참조 (`OfferRef`) | 예약 컨텍스트가 catalog에서 받은 읽기 전용 값(가격, 매장명, 상점주 ID, 픽업 시간) | layer-architecture §3.4 |

### 1.2 `ReservationStatus` (StrEnum)

`PENDING_PAYMENT`(결제 대기), `RESERVED`(결제 완료·픽업 대기), `PICKED_UP`(픽업 완료), `CANCELLED`(취소). 명세 상태 값 표 기준이며 `RESERVED`의 의미는 **확인 필요(Q-1)**입니다. 값은 payments `rules.py`의 `RESERVATION_PAYABLE_STATUS`/`RESERVATION_PAID_STATUS`와 같습니다(D-1).

**허용 전이표**

| 현재 \ 행위 | `mark_paid()` | `cancel(now)` | `pick_up(code, now)` |
| --- | --- | --- | --- |
| `PENDING_PAYMENT` | → `RESERVED` | → `CANCELLED` | 불가 (`ReservationNotPaidError` 409) |
| `RESERVED` | 불가 (`ReservationStateError` 409) | → `CANCELLED` | 코드 일치 시 → `PICKED_UP`, 불일치 시 `PickupCodeMismatchError` 400 |
| `PICKED_UP` | 불가 (409) | 불가 (`ReservationAlreadyPickedUpError` 409) | 불가 (`ReservationAlreadyPickedUpError` 409) |
| `CANCELLED` | 불가 (409) | 불가 (`ReservationAlreadyCancelledError` 409) | 불가 (`ReservationAlreadyCancelledError` 409) |

`PICKED_UP`, `CANCELLED`는 종료 상태입니다. 결제 대기 만료(`EXPIRED` 등)는 두지 않습니다(Q-2).

### 1.3 `PickupReservation` (엔티티, 애그리거트 루트)

| 속성 | 타입 | 생성자 검증 |
| --- | --- | --- |
| `id` | `uuid.UUID \| None` | 저장 전 None |
| `user_id` | `uuid.UUID` | 필수 |
| `offer_id` | `uuid.UUID` | 필수 |
| `quantity` | `int` | bool 거부, `>= 1` ("수량은 1개 이상이어야 합니다.") |
| `unit_price` | `int` | bool 거부, `>= 0` |
| `total_price` | `int` | `unit_price * quantity`와 같아야 함 ("총액이 단가×수량과 다릅니다.") |
| `status` | `ReservationStatus` | `ReservationStatus(status)`로 변환(잘못된 값은 ValueError) |
| `pickup_code` | `str` | 공백 제거 후 1~20자 (`pickup_reservations.pickup_code VARCHAR(20)`) |
| `store_name` | `str` | 1~150자 (예약 시점 스냅샷) |
| `pickup_address` | `str` | 1~500자 (스냅샷) |
| `product_name` | `str` | 1~200자 (스냅샷) |
| `created_at` | `datetime \| None` | 있으면 timezone 필수 |
| `cancelled_at` | `datetime \| None` | 있으면 timezone 필수. `CANCELLED`일 때만 값이 있어야 함 |
| `picked_up_at` | `datetime \| None` | 있으면 timezone 필수. `PICKED_UP`일 때만 값이 있어야 함 |

스키마의 `price`는 매핑하지 않습니다(S-3). 스키마상 NULL 허용인 `total_price`·`status` 등은 도메인에서 필수로 취급합니다(S-2).

**팩토리·행위 메서드** (모두 `now`는 인자, 도메인은 시계를 부르지 않음)

| 메서드 | 동작 | 내는 예외 |
| --- | --- | --- |
| `create(user_id, offer: OfferRef, quantity, pickup_code, now)` (classmethod) | `unit_price = offer.sale_price`, `total_price = unit_price * quantity`, 스냅샷(`store_name`, `product_name`, `pickup_address`) 복사, `status = PENDING_PAYMENT`, `created_at = now` | 생성자 검증의 `ValueError`(400), `now`가 naive면 `ValueError` |
| `ensure_owned_by(user_id, message)` | 예약자가 아니면 거부 | `NotReservationOwnerError` (403) |
| `mark_paid()` | `PENDING_PAYMENT → RESERVED` | 그 외 상태 `ReservationStateError` (409, 상태에 따라 취소·픽업 하위 예외) |
| `cancel(now)` | `PENDING_PAYMENT`/`RESERVED → CANCELLED`, `cancelled_at = now` | `CANCELLED` → `ReservationAlreadyCancelledError`, `PICKED_UP` → `ReservationAlreadyPickedUpError` (둘 다 409), `now` naive → `ValueError` |
| `pick_up(pickup_code, now)` | 상태 검사 → 코드 비교 → `PICKED_UP`, `picked_up_at = now` | `PENDING_PAYMENT` → `ReservationNotPaidError`(409), `CANCELLED`/`PICKED_UP` → 위 409 예외, 코드 불일치 → `PickupCodeMismatchError`(400). **검사 순서: 상태 → 코드** (D-9) |
| `is_paid` (property) | `status == RESERVED` | |
| `holds_stock` (property) | `status in (PENDING_PAYMENT, RESERVED)`: 재고를 잡고 있는 상태 | |

코드 비교는 `rules.PICKUP_CODE_CASE_SENSITIVE=False`이면 양쪽을 `strip().upper()`로 정규화한 뒤 `hmac.compare_digest`로 비교합니다(표준 라이브러리라 순수 파이썬 유지).

### 1.4 `OfferRef` (값 객체, catalog에서 받은 값의 복사본)

`catalog.domain.store_ref.StoreRef`와 같은 패턴입니다. 속성: `offer_id`, `owner_id`(상점주 `users.id`), `store_name`, `product_name`, `pickup_address`, `sale_price`, `pickup_start`, `pickup_end`. `OfferRef.from_info(info)`(classmethod, `Any`를 받아 속성으로 복사), `ensure_owned_by(user_id, message)` → `NotPickupStoreOwnerError`(403), `ensure_not_owned_by(user_id)` → `ValueError`(400, `ALLOW_OWNER_SELF_RESERVATION=False`일 때만 사용), `ensure_in_pickup_window(now)` → `ValueError`(400, `PICKUP_WINDOW_ENFORCED=True`일 때만 사용).

### 1.5 추상 (`repository.py`, `service.py`)

- `ReservationRepository(ABC)`: 2.2절 메서드 표.
- `Clock(ABC)`: `now() -> datetime`(timezone 포함). stores·catalog와 같은 형태이지만 모듈별 별개 타입입니다(catalog D21).
- `PickupCodeGenerator(ABC)`: `generate() -> str`.

### 1.6 예외 (`exceptions.py`) → 전역 핸들러 변환

| 예외 | 부모 | HTTP | `error_code` | 메시지(기본) |
| --- | --- | --- | --- | --- |
| `ReservationNotFoundError` | `LookupError` | 404 | `NOT_FOUND` (고정) | "예약 정보를 찾을 수 없습니다." |
| `NotReservationOwnerError` | `PermissionError` | 403 | `FORBIDDEN` (고정) | "본인 예약만 취소할 수 있습니다." (조회는 쓰지 않음, 취소 전용 문구) |
| `NotPickupStoreOwnerError` | `PermissionError` | 403 | `FORBIDDEN` (고정) | "해당 매장의 상점주만 픽업 완료 처리할 수 있습니다." |
| `PickupCodeMismatchError` | `ValueError` | 400 | `PICKUP_CODE_MISMATCH` | "예약번호가 일치하지 않습니다." |
| `PickedUpReservationExistsError` | `ValueError` | 400 | `PICKED_UP_RESERVATION_EXISTS` | catalog의 같은 이름 예외와 **같은 error_code·메시지**(D-17). 일괄 취소 포트 전용 |
| `ReservationStateError` | `ReservationConflictError` | 409 | `RESERVATION_INVALID_STATE` | "처리할 수 없는 예약 상태입니다." |
| `ReservationAlreadyCancelledError` | `ReservationStateError` | 409 | `RESERVATION_ALREADY_CANCELLED` | "이미 취소된 예약입니다." |
| `ReservationAlreadyPickedUpError` | `ReservationStateError` | 409 | `RESERVATION_ALREADY_PICKED_UP` | "이미 픽업 완료된 예약입니다." |
| `ReservationNotPaidError` | `ReservationStateError` | 409 | `RESERVATION_NOT_PAID` | "결제가 완료되지 않은 예약입니다." |

409는 `ValueError`를 상속하면 400이 되므로 reservations 전용 `ReservationConflictError(Exception)`(`error_code` 속성 보유)를 상속하고 핸들러 한 줄을 `error_handlers.py`에 둡니다(D-16, C-6). 재고 임시 포트용으로 `OfferNotFoundError(LookupError, 404)`, `OfferNotReservableError`(409 `OFFER_NOT_RESERVABLE`), `OutOfStockError`(409 `OUT_OF_STOCK`)도 이 도메인에 둡니다(D-25). 명세의 422(형식 오류)는 전역 핸들러대로 400 `VALIDATION_ERROR`입니다(payments D-17과 같은 처리, Q-14).

재고·판매 상태 관련 409(`OUT_OF_STOCK`, `OFFER_NOT_RESERVABLE`)는 catalog 도메인이 냅니다(C-1).

### 1.7 `rules.py` — 임시 기본값 모음 (바뀔 수 있는 값은 이 파일 한 곳)

| 상수 | 임시 기본값 | 관련 질문 |
| --- | --- | --- |
| `PAYMENT_TIMEOUT` | `None` (결제 제한 시간 없음) | Q-2 |
| `PICKUP_WINDOW_ENFORCED` | `False` (픽업 시간 밖에서도 처리 가능) | Q-5 |
| `ALLOW_OWNER_SELF_RESERVATION` | `True` (상점주가 자기 매장 할인을 예약해도 막지 않음) | Q-3 |
| `PICKUP_CODE_CASE_SENSITIVE` | `False` | Q-4 |
| `PICKUP_CODE_LETTERS`, `PICKUP_CODE_DIGITS` | `1`, `5` (예: `A12345`) | Q-4 |
| `CUSTOMER_CANCEL_REASON` | `"고객 요청 취소"` | Q-7 |
| `LIST_DEFAULT_SIZE`, `LIST_MAX_SIZE` | `20`, `100` | Q-9 |

---

## 2. 인프라 (`infrastructure/`)

### 2.1 `models.py` — `PickupReservationModel` (`__tablename__ = "pickup_reservations"`, `schema.sql`과 동일, R14)

| 컬럼 | SQLAlchemy 타입 | NULL | 제약·기본값 |
| --- | --- | --- | --- |
| `id` | `UUID(as_uuid=True)` PK | X | `default=uuid.uuid4`, `server_default=gen_random_uuid()` |
| `user_id` | `UUID` | X | FK `users.id`, `index=True` (`ix_pickup_reservations_user_id`) |
| `offer_id` | `UUID` | X | FK `discount_offers.id`, `index=True` (`ix_pickup_reservations_offer_id`) |
| `quantity` | `int` | X | `CheckConstraint("quantity >= 1", name="ck_reservations_quantity")` |
| `created_at` | `DateTime(timezone=True)` | X | `server_default=now()` |
| `total_price` | `int` | O (스키마 그대로) | |
| `status` | `String(20)` | O (스키마 그대로) | |
| `unit_price` | `int` | O | |
| `pickup_code` | `String(20)` | O | |
| `cancelled_at` | `DateTime(timezone=True)` | O | |
| `picked_up_at` | `DateTime(timezone=True)` | O | |
| `store_name` | `String(150)` | O | 예약 시점 스냅샷 |
| `pickup_address` | `String(500)` | O | 스냅샷 |
| `product_name` | `String(200)` | O | 스냅샷 |
| `price` | — | — | **매핑하지 않음** (catalog S3와 같은 방식, S-3) |

FK는 문자열(`ForeignKey("users.id")`, `ForeignKey("discount_offers.id")`)로만 연결하고 다른 모듈 모델을 import하지 않습니다(db-schema 3절). 레포지토리는 NULL 허용 컬럼을 읽을 때 도메인 필수 값이 None이면 `ValueError`를 내지 않고 데이터 이상으로 보고 실패시킵니다(테스트에서 확인).

### 2.2 `repositories.py` — `SqlAlchemyReservationRepository(ReservationRepository)`

| 메서드 | 반환 | 설명 |
| --- | --- | --- |
| `find_by_id(reservation_id, for_update=False)` | `PickupReservation \| None` | `for_update`면 `.with_for_update().execution_options(populate_existing=True)` (catalog와 같은 방식. 같은 세션 안에서 앞서 잠금 없이 읽어 둔 값이 낡았을 수 있어 `populate_existing` 필수) |
| `find_by_user(user_id, *, status, page, size)` | `tuple[list[PickupReservation], int]` | `status`가 None이면 전체. **정렬 `created_at DESC, id DESC`** 고정. `total`은 같은 조건의 `COUNT(*)`. 잠금 없음 |
| `find_by_offer(offer_id, *, for_update=False)` | `list[PickupReservation]` | 일괄 취소용. **`ORDER BY id`** 로 잠금 순서를 고정(교착 방지). `for_update`면 위와 같은 잠금 |
| `exists_by_offer(offer_id)` | `bool` | catalog `has_reservations_for_offer`용. **상태와 관계없이** 한 건이라도 있으면 True(catalog D28) |
| `save(reservation)` | `PickupReservation` | `id is None`이면 INSERT(`created_at`이 있으면 함께 저장) 후 `flush()`로 `id`·`created_at` 채움. 있으면 `session.get`으로 모델을 얻어 가변 필드(`status`, `cancelled_at`, `picked_up_at`)만 갱신하고 `flush()`. 없으면 `ReservationNotFoundError`. **`commit()` 금지**(R5) |
| `_to_domain(model)` | 정적 메서드 | `*Model`은 밖으로 나가지 않음(R4) |

### 2.3 그 밖의 구현체

- `clock.py`: `SystemClock(Clock)` — `datetime.now(timezone.utc)`.
- `pickup_code.py`: `SecretsPickupCodeGenerator(PickupCodeGenerator)` — `secrets.choice`로 대문자 1자 + 숫자 5자(`rules` 값). 시계처럼 상태가 없어 container 싱글턴.
- `payment_refund_stub.py`: `NoPaymentRefund` — 임시. `RefundPort`를 구조적으로 만족(application을 import하지 않음, R2). 환불 없이 즉시 반환(D-15, C-4에서 교체).

### 2.4 동시성 위험 지점과 잠금

| 지점 | 위험 | 대응 |
| --- | --- | --- |
| 예약 생성 vs 예약 생성 | 마지막 재고를 두 명이 동시에 예약 (오버셀) | catalog `reserve`가 `discount_offers` 행을 `SELECT ... FOR UPDATE`로 잠그고 차감한 뒤 예약 INSERT. DB `ck_offer_remaining_stock`이 마지막 방어선 |
| 예약 생성 vs 할인 수정(#11) | 예약이 생기는 순간 "예약 0건일 때만 수정" 판정과 어긋남 | 둘 다 offer 행을 잠근 뒤에만 예약을 INSERT/판정하므로 직렬화(catalog CI-10) |
| 같은 예약을 동시에 취소 | 재고 이중 복구 | 예약 행 `FOR UPDATE` 안에서 `cancel(now)`가 상태를 먼저 검사하고, 통과한 뒤에만 재고를 복구. 두 번째는 대기 후 `CANCELLED`를 보고 409 |
| 결제(`pay`) vs 취소 | 취소된 예약에 결제 | 둘 다 `offer → reservation` 순서로 잠그고 잠금 안에서 상태 재확인 |
| 픽업 vs 취소 | 픽업된 예약을 취소 | 픽업은 예약 행만 잠금(offer 잠금 불필요). 둘 다 예약 행을 잠그므로 직렬화 |
| 판매 중단 일괄 취소(catalog #12) vs 고객 취소 | **교착**: #12는 offer 잠금 → 예약 잠금, 고객 취소는 (예약 먼저 잠그면) 예약 → offer 잠금 | **전역 잠금 순서 `product → offer → reservation → payment → refund → user(포인트)`** 고정(D-6). 고객 취소는 잠금 없이 읽어 `offer_id`를 얻고 offer를 먼저 잠근 뒤 예약을 잠금 |
| 일괄 취소 중 예약이 여러 건 | 여러 예약을 서로 다른 순서로 잠그면 교착 | `find_by_offer(for_update=True)`가 `ORDER BY id` |
| 같은 세션의 낡은 객체 | 앞서 잠금 없이 읽은 모델이 identity map에 남아 잠금 후에도 낡은 값 | 잠금 읽기는 모두 `populate_existing=True` |

---

## 3. 응용 (`application/`)

서비스는 둘로 나눕니다(D-5). 결제·catalog 판매 중단과 얽힌 **생성 순환**(R12)을 끊기 위해서입니다(5.2절).

| 서비스 | 파일 | 역할 | 의존 |
| --- | --- | --- | --- |
| `ReservationLifecycleService` | `lifecycle_service.py` | 예약 상태 전이 + 재고 복구 + 일괄 취소의 **결제를 모르는** 부분. payments 어댑터(`ReservationPort`)와 `ReservationApplicationService`가 사용 | `ReservationRepository`, `StockPort`, `Clock` |
| `ReservationApplicationService` | `service.py` | 엔드포인트 4개 유스케이스, 환불 호출, **commit 담당** | `ReservationLifecycleService`, `ReservationRepository`, `StockPort`, `RefundPort`, `Clock`, `PickupCodeGenerator`, `AsyncSession` |

모든 생성자 인자는 필수이며 기본 생성이 없습니다(R8). commit은 `ReservationApplicationService`(와 `commit=True`로 부른 Lifecycle 메서드)만 합니다(R5).

### 3.1 포트 (`ports.py`, 쓰는 쪽 reservations가 정의, R11)

```
class OfferTermsInfo(Protocol):          # catalog가 구조적으로 만족하는 읽기 값
    offer_id: UUID; owner_id: UUID; store_name: str; product_name: str
    pickup_address: str; sale_price: int; pickup_start: datetime; pickup_end: datetime

class StockPort(Protocol):               # 재고와 할인 조건. commit하지 않는다(R13)
    async def get_terms(self, offer_id, *, for_update=False) -> OfferTermsInfo
    async def reserve(self, offer_id, quantity, *, user_id, now) -> OfferTermsInfo
    async def release(self, offer_id, quantity, *, user_id, reason) -> bool

class RefundPort(Protocol):              # 결제 모듈. commit하지 않는다(R13)
    async def refund_for_cancelled_reservation(
        self, target: RefundTarget, *, reason: str, waive_penalty: bool = False) -> None
```

- `get_terms(for_update=True)`: offer 행 잠금 + 조건 반환. 없으면 `OfferNotFoundError`(404, catalog 기존 예외, `LookupError`).
- `reserve`: offer 잠금 → `offer.deduct_stock(quantity, now)` → 저장 → `stock_log`(`amount = -quantity`) 추가 → 조건 반환. 오류: 404, 400(수량), 409 `OFFER_NOT_RESERVABLE`/`OUT_OF_STOCK`.
- `release`: offer 잠금 → `offer.restore_stock(quantity, now)` → 저장 → `stock_log`(`+quantity`). **할인이 `is_active=false`(중단·재등록으로 닫힘)면 재고·로그를 건드리지 않고 `False`** 를 돌려준다(catalog D40, 5.2절).
- `RefundTarget`은 reservations 응용 계층의 값 객체(`reservation_id`, `user_id`, `total_price`, `pickup_start`, `status`). payments의 `ReservationSnapshot`으로의 변환은 어댑터가 합니다(C-4).

### 3.2 `ReservationLifecycleService` (결제 모름)

내부 헬퍼 `_load_locked(reservation_id)`(잠금 순서 `offer → reservation`):
1. `peek = reservations.find_by_id(reservation_id)` (잠금 없음) → 없으면 None
2. `terms = stock.get_terms(peek.offer_id, for_update=True)` (offer 잠금)
3. `reservation = reservations.find_by_id(reservation_id, for_update=True)` (예약 잠금, `populate_existing`)
4. `(reservation, OfferRef.from_info(terms))` 반환

| 메서드 | 시나리오 |
| --- | --- |
| `get_snapshot(reservation_id, *, for_update=False) -> ReservationView \| None` | `for_update=False`: `find_by_id` → `stock.get_terms(offer_id)` → `ReservationView(reservation, offer)`. `True`: `_load_locked`. 없으면 `None`(404는 호출자). payments 어댑터의 `get`이 사용 |
| `mark_paid(reservation_id, *, commit=False)` | `_load_locked`(이미 잠겨 있으면 재획득은 no-op) → `reservation.mark_paid()` → `save` → `commit`이면 commit |
| `cancel(reservation_id, *, reason, actor_user_id, commit=False) -> Reservation` | `_load_locked` → 없으면 `ReservationNotFoundError` → **`reservation.cancel(now)`(상태 검사·전이)** → `stock.release(offer_id, quantity, user_id=actor_user_id, reason=reason)` → `save` → `commit`이면 commit. 상태 검사가 재고 복구보다 먼저라 이중 복구가 없음 |
| `cancel_for_refund(reservation_id, reason, *, commit=False) -> None` | payments `refund()`용. 이미 `CANCELLED`면 **아무것도 하지 않고 통과(멱등)**, 환불을 다시 호출하지 않음. 그 외는 `cancel`과 같음. `PICKED_UP`이면 409 |
| `cancel_all_for_offer(offer_id, *, reason) -> list[Reservation]` | `find_by_offer(offer_id, for_update=True)` → **`PICKED_UP`이 하나라도 있으면 아무것도 바꾸기 전에 `PickedUpReservationExistsError`** → `holds_stock`인 것마다 `reservation.cancel(now)` + `save`. **재고는 복구하지 않음**(D40). 이번에 취소한 예약 목록 반환(이미 `CANCELLED`는 제외). commit 없음 |

`now`는 `self.clock.now()`입니다. Lifecycle은 환불·포인트를 호출하지 않습니다.

### 3.3 `ReservationApplicationService` 시나리오

**① `create_reservation(user_id, offer_id, quantity) -> PickupReservation`** (한 트랜잭션: 재고 차감 + `stock_log` + 예약 저장)
1. `now = clock.now()`
2. `terms = await stock.reserve(offer_id, quantity, user_id=user_id, now=now)` — offer 행 `FOR UPDATE`, 도메인 `deduct_stock`(판매 중 `ON_SALE` 확인, 수량·재고 검사), `stock_log` 음수 기록. 404/400/409는 여기서 남
3. `offer = OfferRef.from_info(terms)`; `ALLOW_OWNER_SELF_RESERVATION`이 False면 `offer.ensure_not_owned_by(user_id)`(기본값은 True라 호출하지 않음, Q-3)
4. `reservation = PickupReservation.create(user_id, offer, quantity, code_generator.generate(), now)` — 단가는 **서버가 `terms.sale_price`로 정함**(클라이언트가 가격을 보내지 않음)
5. `await reservations.save(reservation)` (flush)
6. `await session.commit()` — **한 번만**. 2~5 중 예외가 나면 커밋되지 않고 세션이 닫히며 롤백되어 재고도 되돌아감

**② `list_my_reservations(user_id, status, page, size) -> Page[PickupReservation]`** — `reservations.find_by_user` 한 번. 읽기 전용, commit 없음. 본인 것만 조회되므로 IDOR 없음

**③ `cancel_reservation(user_id, reservation_id) -> PickupReservation`** (한 트랜잭션: 상태 전이 + 재고 복구 + 환불)
1. `view = await lifecycle.get_snapshot(reservation_id)` (잠금 없음) → None이면 `ReservationNotFoundError`(404)
2. `view.reservation.ensure_owned_by(user_id, "본인 예약만 취소할 수 있습니다.")` → 403. **잠금보다 먼저** 해서 타인이 남의 offer를 잠그지 못하게 함
3. `was_paid = view.reservation.is_paid`; `target = RefundTarget(...)`(취소 전 상태 `RESERVED`로 만든 값)
4. `await lifecycle.cancel(reservation_id, reason=CUSTOMER_CANCEL_REASON, actor_user_id=user_id)` — offer 잠금 → 예약 잠금 → 상태 검사(이미 취소·픽업이면 409) → 재고 복구
5. `was_paid`면 `await refunds.refund_for_cancelled_reservation(target, reason=..., waive_penalty=False)` (결제가 있으면 환불, 없으면 payments가 아무것도 안 함)
6. `await session.commit()` — **한 번만**. 5에서 실패하면 취소·재고 복구도 롤백

**④ `complete_pickup(owner_id, reservation_id, pickup_code) -> PickupReservation`**
1. `view = await lifecycle.get_snapshot(reservation_id)` → None이면 404
2. `view.offer.ensure_owned_by(owner_id, ...)` → 403 (해당 매장 상점주가 아님). 역할(`OWNER`)은 router의 `OwnerUser`가 확인
3. `reservation = await reservations.find_by_id(reservation_id, for_update=True)` — 예약 행만 잠금(재고를 건드리지 않음). `populate_existing`
4. `reservation.pick_up(pickup_code, clock.now())` — 상태 → 코드 순서
5. `await reservations.save(reservation)` → `await session.commit()`
(`PICKUP_WINDOW_ENFORCED=True`일 때만 `view.offer.ensure_in_pickup_window(now)`를 4번 앞에 호출. 기본 False, Q-5)

**⑤ `cancel_all_for_offer(offer_id, *, reason) -> int`** (catalog `ReservationCancelPort`용, **commit 없음**)
1. `cancelled = await lifecycle.cancel_all_for_offer(offer_id, reason=reason)` (픽업 완료가 있으면 예외로 전체 중단, D40: 재고 복구 없음)
2. `cancelled` 중 결제된 것(취소 전 `RESERVED`)마다 `await refunds.refund_for_cancelled_reservation(target, reason=reason, waive_penalty=True)` — 점주 사유라 전액 환불(payments D-16)
3. `return len(cancelled)` — commit은 catalog `deactivate_offer`가 마지막에 한 번(R13)

### 3.4 모듈 간 트랜잭션 경계

| 흐름 | 세션 | commit 위치 | 실패 시 |
| --- | --- | --- | --- |
| 예약 생성 (reservations → catalog) | 요청 세션 하나 | `create_reservation` 끝 한 번 | catalog 호출 포함 전부 롤백 |
| 고객 취소 (reservations → catalog → payments) | 같음 | `cancel_reservation` 끝 한 번 | 환불 실패 시 취소·재고 복구도 롤백 |
| 결제 (payments → reservations) | 같음 | payments `pay()` 끝 한 번. `mark_paid(commit=False)` | payments가 `mark_paid`·포인트까지 한 트랜잭션으로 롤백 |
| 환불 API (payments → reservations) | 같음 | payments `refund()` 끝 한 번. `cancel_for_refund(commit=False)` | 같음 |
| 판매 중단 일괄 취소 (catalog → reservations → payments) | 같음 | catalog `deactivate_offer` 끝 한 번. 포트는 commit하지 않음 | 픽업 완료 예약이 있으면 예외로 전체 롤백 |
| 결제 실패 시 재고 | — | — | **예약이 `PENDING_PAYMENT`로 남고 재고도 그대로 잡혀 있음**(결제 실패 시 payments가 롤백만 하고 예약 상태를 바꾸지 않음). 고객이 재시도하거나 취소하면 그때 재고 복구. 자동 취소·만료 없음(Q-2) |

---

## 4. 표현 (`presentation/`)

### 4.1 엔드포인트 (URI·필드는 `docs/reference/reservations.md`를 따름, R15)

| # | Method | URI | 권한(의존성) | 요청 | 응답 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 22 | POST | `/v1/reservations` | `CurrentUser` | `ReservationCreateRequest` | `ReservationCreateResponse` | 201 | 400 `VALIDATION_ERROR`(수량 등, 명세의 422), 401, 404 `NOT_FOUND`(할인 없음), 409 `OUT_OF_STOCK`/`OFFER_NOT_RESERVABLE` |
| 23 | GET | `/v1/users/me/reservations` | `CurrentUser` | 쿼리 `status`, `page`, `size` | `ReservationListResponse` | 200 | 400 `VALIDATION_ERROR`(잘못된 `status`·`page`·`size`), 401 |
| 24 | POST | `/v1/reservations/{reservation_id}/cancel` | `CurrentUser`(+서비스에서 본인 확인) | 없음 | `ReservationCancelResponse` | 200 | 400(잘못된 UUID), 401, 403 `FORBIDDEN`, 404 `NOT_FOUND`, 409 `RESERVATION_ALREADY_CANCELLED`/`RESERVATION_ALREADY_PICKED_UP` |
| 25 | POST | `/v1/reservations/{reservation_id}/pickup` | `OwnerUser`(+서비스에서 해당 매장 확인) | `PickupRequest` | `PickupResponse` | 200 | 400 `PICKUP_CODE_MISMATCH`/`VALIDATION_ERROR`, 401, 403 `FORBIDDEN`(역할 불일치 또는 다른 매장), 404 `NOT_FOUND`, 409 `RESERVATION_NOT_PAID`/`RESERVATION_ALREADY_*` |

- 인증·권한 별칭은 `auth.presentation.dependencies`의 `CurrentUser`, `OwnerUser`만 씁니다(D-인증의존성). 401은 auth가 `WWW-Authenticate: Bearer`와 함께 내고, 403(역할)도 auth가 냅니다. 소유권(본인 예약, 해당 매장)은 도메인 메서드의 `PermissionError` 하위 예외입니다.
- router는 서비스만 호출하고 예외를 잡지 않으며 `HTTPException`을 만들지 않습니다(R6, R7). 에러 형식은 전역 핸들러가 `{success, error_code, message}`로 만듭니다.
- 라우터는 `APIRouter(prefix="/v1")`, `tags=["예약"]`, 엔드포인트마다 `summary`.
- `/v1/users/me/reservations`는 auth의 `/v1/users/me`, `/v1/users/me/points`와 경로가 겹치지 않습니다(확인함).

### 4.2 스키마 (`schemas.py`, 응답은 `from_attributes=True`로 도메인 객체를 직렬화)

| 스키마 | 필드 |
| --- | --- |
| `ReservationCreateRequest` | `offer_id: UUID`, `quantity: int = Field(..., ge=1)` (상한은 두지 않음: 남은 재고가 한도. 0·음수·문자열 → 400 `VALIDATION_ERROR`) |
| `ReservationCreateResponse` | `id, user_id, offer_id, quantity, unit_price, total_price, status, created_at, store_name, product_name` (명세 10개 그대로) |
| `ReservationListItem` | `id, offer_id, store_name, product_name, quantity, total_price, status, created_at` (명세) **+ 제안 필드 `pickup_code`, `pickup_address`** (Q-4: 고객이 픽업 때 보여줄 값이 어디에도 없음. 추가는 호환되는 확장이라 기본으로 포함하되 명세 확정 전까지 표시) |
| `ReservationListResponse` | `reservations: list[ReservationListItem]` (명세) **+ 제안 `page`, `size`, `total`** (README 확인 5번, 목록 API 교안 요구. `page` 시작 값은 1로 catalog와 같음) |
| `ReservationCancelResponse` | `id, status, cancelled_at` |
| `PickupRequest` | `pickup_code: str = Field(..., min_length=1, max_length=20)` (앞뒤 공백은 도메인이 정리) |
| `PickupResponse` | `id, pickup_code, status, picked_up_at` |

민감 정보는 없습니다. `pickup_code`는 본인 예약 목록(`ReservationListItem`)과 픽업 응답에만 나가고 다른 사용자에게는 노출되지 않습니다.

### 4.3 목록 쿼리 매개변수 (#23)

| 이름 | 타입 | 기본 | 검증 | 설명 |
| --- | --- | --- | --- | --- |
| `status` | `ReservationStatus` (선택) | 전체 | 잘못된 값 → 400 `VALIDATION_ERROR` | 상태 필터 |
| `page` | int | 1 | `ge=1` | catalog `PageParam`과 같은 정의를 따름(구현 시 catalog의 별칭을 재사용하지 말고 reservations `schemas.py`에 같은 값으로 따로 정의: R11) |
| `size` | int | 20 | `1..100` | |
| 정렬 | — | `created_at DESC` 고정 | | 정렬 매개변수 없음(Q-9) |

### 4.4 `dependencies.py` (플레이스홀더, R9)

- `provide_reservation_service() -> ReservationApplicationService`
- `provide_reservation_lifecycle_service() -> ReservationLifecycleService` (payments 어댑터가 `Depends`로 받음, C-3)

둘 다 `raise NotImplementedError("... 의존성이 주입되지 않았습니다.")`이고 `wire_dependencies`에 매핑합니다. router는 `Annotated[ReservationApplicationService, Depends(provide_reservation_service)]`만 씁니다.

---

## 5. 조립 (`src/container.py`, `src/main.py`)

### 5.1 container의 reservations 구역

| 항목 | 내용 |
| --- | --- |
| 싱글턴 | `_reservations_clock: ReservationsClock = ReservationsSystemClock()`, `_pickup_code_generator: PickupCodeGenerator = SecretsPickupCodeGenerator()`, `_payment_refund: RefundPort = NoPaymentRefund()`(**임시**, C-4). Clock은 모듈별 별개 타입이라 stores·catalog와 별칭으로 구분 |
| 팩토리 | `create_reservation_repository(session)`, `create_stock_port(offers=Depends(create_discount_offer_repository), products=Depends(create_product_repository), stores=Depends(create_store_port)) -> StockPort` → **임시 구현 `ReadOnlyOfferStockPort`**(7.1절. catalog C-1 머지 후 `CatalogStockService`로 한 줄 교체), `create_refund_port() -> RefundPort`, `create_reservation_lifecycle_service(session, reservations, stock)`, `create_reservation_service(session, lifecycle, reservations, stock, refunds)` |
| catalog 구역에 추가(C-1) | `create_catalog_stock_service(stores=Depends(create_store_port), products, offers, stock_logs) -> CatalogStockService` |
| catalog 포트 교체(CI-10, CI-11) | `create_reservation_lookup(reservations=Depends(create_reservation_repository)) -> ReservationLookupPort` → `OfferReservationLookup(reservations)`. `create_reservation_cancel(service=Depends(create_reservation_service)) -> ReservationCancelPort` → `OfferReservationCanceller(service)`. 둘 다 이제 요청마다 만들고 싱글턴 `_reservation_lookup`, `_reservation_cancel`은 삭제 |
| `wire_dependencies` 매핑 추가 | `provide_reservation_service: create_reservation_service`, `provide_reservation_lifecycle_service: create_reservation_lifecycle_service` (catalog 매핑 4개는 유지) |

어댑터 파일(`application/catalog_adapters.py`, reservations가 소유): `OfferReservationLookup`(레포지토리 `exists_by_offer` 호출), `OfferReservationCanceller`(`ReservationApplicationService.cancel_all_for_offer` 호출). 둘 다 catalog의 포트를 import하지 않고 구조적으로 맞춥니다(catalog가 쓰는 쪽이므로 포트 정의는 catalog `application/ports.py`).

### 5.2 의존 방향과 생성 순환 해결 (layer-architecture §3.4, §4, §6)

```
reservations.presentation -> reservations.application -> reservations.domain
reservations.infrastructure -> reservations.domain
reservations.application -> reservations.application.ports  (StockPort, RefundPort Protocol만. catalog·payments를 import하지 않음)
catalog.application  -> catalog.application.ports (ReservationLookupPort, ReservationCancelPort Protocol만, 변경 없음)
payments.application -> payments.application.ports (ReservationPort Protocol, 변경 없음)

src/container.py가 catalog, payments, reservations 구현을 모두 아는 유일한 곳
```

객체 생성(Depends) 그래프는 한 방향이어야 합니다.

```
StorePort(StoresService) ──▶ CatalogStockService ──▶ StockPort
                                      │
                       ReservationLifecycleService ◀── (payments의 ReservationAdapter, C-3)
                                      │
            RefundPort(PaymentApplicationService 어댑터, 임시 NoPaymentRefund)
                                      │
                       ReservationApplicationService ──▶ OfferReservationCanceller
                                                                  │
                                                      CatalogApplicationService (deactivate_offer)
```

- **순환 지점 1 (catalog ↔ reservations)**: `CatalogApplicationService`는 `ReservationCancelPort`(= reservations 서비스)를 받고, 예약 생성이 `CatalogApplicationService`를 받으면 생성이 순환합니다(catalog C12). 그래서 재고 처리는 **`CatalogApplicationService`가 아니라 예약 포트를 모르는 별도 `CatalogStockService`**(C-1)가 맡습니다. 이 서비스는 `ReservationLookupPort`·`ReservationCancelPort`를 받지 않습니다.
- **순환 지점 2 (reservations ↔ payments)**: payments `pay()`는 `ReservationPort`(= `ReservationLifecycleService`의 어댑터)를 받고, 예약 취소는 `RefundPort`(= payments 서비스)를 받습니다. 서비스를 하나로 두면 서로를 생성자로 받아 순환하므로 Lifecycle(결제 모름)과 ApplicationService(결제 호출)로 나눴습니다. payments가 쓰는 쪽은 Lifecycle, reservations의 ApplicationService가 쓰는 쪽은 payments 서비스로 한 방향입니다.
- 서비스 생성자 안에서 다른 서비스를 만들지 않습니다(R12). 생성은 container 팩토리만 합니다.
- `stores`가 나중에 폐점 검사에 reservations를 쓰려면(`has_pickup_pending_for_store`) stores가 포트를 정의하고 container가 연결합니다(C-8).

### 5.3 `src/main.py`

- `from reservations.infrastructure import models as reservations_models  # noqa: F401` 를 **catalog models 뒤에** import(FK 대상 `users`, `discount_offers`가 먼저 등록돼야 함, `create_all` 전에 반드시 import).
- `from reservations.presentation.router import router as reservations_router`, `app.include_router(reservations_router)`를 catalog 라우터 뒤에 추가.
- 그 밖의 `main.py` 수정은 없습니다. payments의 FK 추가 때 models import 순서는 `create_all`이 FK 순서로 정렬하므로 import만 `lifespan` 앞이면 됩니다.

---

## 6. 테스트 계획 (구현자에게 전달, `layer-implementation/testing.md` 기준)

- `tests/reservations/test_domain.py`: 생성자 검증, 전이표 전체(허용·거부 모든 칸), `pick_up` 검사 순서(상태 → 코드), 코드 정규화·비교, `created_at`/`cancelled_at` 일관성.
- `tests/reservations/test_service.py`: fake 레포지토리·fake `StockPort`·fake `RefundPort`·고정 `Clock`. 호출 순서(잠금 순서 `get_terms(for_update)` → 예약 잠금 → `release`)를 fake에 기록해 단언, 생성 `commits == 1`, 중간 예외 시 `commits == 0`, 취소 403이 잠금 호출보다 먼저, 이미 취소된 예약의 이중 복구 없음, `cancel_all_for_offer`가 `commit`하지 않음·픽업 완료 시 변경 0건, 환불 호출 조건(`was_paid`일 때만), 상점주 불일치 403.
- `tests/reservations/test_api_db.py`(db 마커, skip은 통과가 아님 R16): 생성 201과 재고 차감·`stock_log` 음수 1건, 재고 초과 409, 동시 예약 `asyncio.gather`로 재고 1에 두 요청 → 정확히 1건 201, 취소 후 재고 복구·`stock_log` 양수, 타인 취소 403, 이중 취소 409, 픽업 성공·코드 불일치 400·다른 매장 상점주 403·결제 전 409, 목록 본인 것만·페이지네이션·`status` 필터, 401 `WWW-Authenticate` 헤더, 에러 본문 형식(R7).
- `tests/reservations/test_wiring.py`: `provide_*` 2개가 모두 매핑(R9), `create_reservation_lookup`/`cancel`이 더는 `NoReservation*`가 아님(C-2), `create_refund_port()`가 현재 `NoPaymentRefund`(payments 연결 시 실패해 교체를 상기시킴).
- 계약 테스트: `ReservationLifecycleService`가 payments `ReservationPort`가 기대하는 동작(`get_snapshot`이 없으면 None, `mark_paid` 상태 변경, `cancel_for_refund` 멱등)을 지키는지 payments의 `FakeReservationPort`와 같은 본문으로 확인.
- 게이트(R16, `backend-invariants` §7): `python3 .claude/skills/layer-check/check_layers.py`(기준선 2건 외 증가 없음), `(cd src && uv run python -c "import main")`, `uv run pytest -rs`.

---

## 7. 구현 순서와 파일 목록

**구현자 쓰기 범위 (확정, 사용자 2026-11-04)**

| 허용 | 금지 |
| --- | --- |
| `src/reservations/**`, `tests/reservations/**`, `src/main.py`의 reservations 두 줄(models import, router 등록), `src/container.py`의 reservations 구역(+ `wire_dependencies` 매핑 2개, `create_reservation_lookup`·`create_reservation_cancel` 교체), `src/error_handlers.py`의 409 핸들러 한 줄 | catalog, payments, stores, auth, `src/common/`, `docs/reference/`, `.claude/`, `pyproject.toml`, `tests/` 중 `tests/reservations/` 밖(단, `tests/catalog/test_wiring.py`의 `NoReservation*` 단언은 container 교체로 깨지므로 C-2 변경 제안으로 보고하고, 구현자는 건드리지 않음 — 깨지면 보고) |

이번 구현 범위: **reservations만 구현하고 재고는 임시 구현으로 연결합니다**(D-25). catalog 재고 기능(C-1), catalog·payments 파일 변경(C-2~C-5, C-7)은 각 담당자에게 넘길 **변경 제안**일 뿐 이번에 하지 않습니다. **payments의 `InMemoryReservationPort` stub과 `get_payment_service`는 그대로 남습니다**(C-3은 제안). 따라서 실서버에서 결제는 계속 메모리 예약을 보며, 실제 `pickup_reservations`는 `RESERVED`가 될 수 없습니다.

### 7.1 런타임 임시 구현 (C-1, C-4 머지 전까지)

| 항목 | 이름·위치 | 동작 | 한계 |
| --- | --- | --- | --- |
| 재고 포트 | `ReadOnlyOfferStockPort` — `src/reservations/application/interim_stock_port.py`(application 계층: catalog `domain.repository`의 **추상** 레포지토리와 `StorePort` 구조만 사용, infrastructure 미import) | 생성자 `offers: DiscountOfferRepository, products: ProductRepository, stores: StorePort`(catalog의 기존 추상·포트, container가 구현 주입). `get_terms`: `offers.find_by_id` → `products.find_by_id` → `stores.find_store_by_id`로 `OfferTermsInfo`(가격·상점명·상품명·픽업 주소·픽업 시간·`owner_id`)를 만든다. 없으면 `OfferNotFoundError`(catalog 기존 404 예외 대신 **reservations 도메인의 `OfferNotFoundError(LookupError)`**를 새로 둠). `reserve`: `get_terms` + **읽기 전용 검사**(`offer.effective_status(now) != ON_SALE` → reservations `OfferNotReservableError` 409, `quantity > offer.remaining_stock` → `OutOfStockError` 409)만 하고 **재고를 차감하지 않으며 `stock_log`도 쓰지 않음**. `release`: 아무것도 하지 않고 `False`. `get_terms(for_update=True)`도 잠그지 않음 | **실서버에서 예약이 재고를 줄이지 않는다**(오버셀 가능, 잠금 없음, 취소해도 복구 없음, `stock_log` 기록 없음). 이 한계를 `Swagger` 설명이 아니라 클래스 docstring과 `tests/reservations/test_wiring.py`의 단언(`create_stock_port`가 `ReadOnlyOfferStockPort`)에 남겨 C-1 머지 때 교체를 상기시킴 |
| catalog 기존 기능으로 읽기가 가능한가 | **가능** (차단 아님). `CatalogApplicationService.get_offer_detail`은 상점주 ID를 주지 않고 서비스를 주입하면 `create_catalog_service` ↔ `create_reservation_cancel` 생성 순환이 되므로 쓰지 않는다. 대신 위 추상 레포지토리 + `StorePort`는 이미 container에 `create_discount_offer_repository`, `create_product_repository`, `create_store_port`로 있다 | | `DiscountOffer.effective_status`·`remaining_stock`은 catalog 도메인 공개 속성(읽기만) |
| 환불 포트 | `NoPaymentRefund` — `src/reservations/infrastructure/payment_refund_stub.py` | `refund_for_cancelled_reservation(...)`이 아무것도 하지 않고 반환 | 결제된 예약 취소 시 환불·포인트 복구가 일어나지 않는다. 현재 `RESERVED` 행이 생길 수 없어(payments는 stub 예약 사용) 영향 없음. payments가 C-3·C-4를 적용할 때 같은 PR에서 교체 |
| 목록·취소 포트 | `OfferReservationLookup`, `OfferReservationCanceller` (`application/catalog_adapters.py`) | 실제 구현. catalog의 `NoReservation*` 임시 구현을 대체 | 일괄 취소는 재고를 복구하지 않는 것이 원래 계약(D40)이라 임시 재고 포트와 충돌 없음 |

| 계층 | 파일 | 내용 |
| --- | --- | --- |
| domain | `pickup_reservation.py`, `offer_ref.py`, `rules.py`, `exceptions.py`, `repository.py`, `service.py` | 1절. 비어 있는 `reservation.py`는 삭제(D-23) |
| infrastructure | `models.py`, `repositories.py`, `clock.py`, `pickup_code.py`, `payment_refund_stub.py`(임시) | 2절 |
| application | `ports.py`, `lifecycle_service.py`, `service.py`, `catalog_adapters.py`, `interim_stock_port.py`(임시), `views.py`(`ReservationView`, `RefundTarget`, `Page`) | 3절, 7.1절 |
| presentation | `schemas.py`, `dependencies.py`, `router.py` | 4절 |

순서: domain → infrastructure → application(fake 포트로 서비스 테스트) → presentation → container/main(7.1절의 임시 구현으로 연결) → `error_handlers.py` 409 핸들러 → DB 통합 테스트. 재고 차감·`stock_log`·동시 예약 테스트는 임시 포트로는 검증할 수 없으므로 이번에는 **fake `StockPort` 서비스 테스트까지**만 하고, 실제 차감 DB 테스트는 C-1 이후 과제로 보고합니다(skip으로 숨기지 않음, R16: 만들지 않고 "미구현"으로 보고).

---

## 8. 결정 표 (D-번호)

상태 열: **확정**(문서·코드·사용자 결정으로 정해진 것) / **임시**(제안). **2026-11-04 사용자가 Q-1~Q-16 임시 기본값으로 진행하기로 승인**했으므로 아래 "임시"는 모두 "임시(사용자 승인, 2026-11-04)"입니다. 값은 확정이 아니며 `rules.py`·enum 한 곳에 모아 나중에 바꾸기 쉽게 둡니다.

| # | 결정 | 근거 | 상태 |
| --- | --- | --- | --- |
| D-1 | 예약 상태 값은 `PENDING_PAYMENT`, `RESERVED`, `PICKED_UP`, `CANCELLED`. `RESERVED` = 결제 완료·픽업 대기 | payments D-9, payments `rules.py`, 명세 상태 값 표 | 임시 (Q-1) |
| D-2 | 예약 생성 응답 필드와 코드: 명세 10개 그대로, 201, 서버가 `unit_price = offer.sale_price`로 계산 | 명세 §1, R15 | 확정 |
| D-3 | 예약 생성은 `OfferRef`가 아니라 catalog `reserve`가 offer 행을 `FOR UPDATE` 잠근 안에서 차감·`stock_log`·예약 INSERT, commit은 `ReservationApplicationService`가 한 번 | 명세 §1 구현 참고, db-schema §7, R13 | 확정 |
| D-4 | 인증은 `CurrentUser`(생성·목록·취소), `OwnerUser`(픽업). 본인 예약·해당 매장 확인은 서비스·도메인의 `PermissionError` 하위 예외 | auth D-인증의존성, layer-implementation §6 | 확정 |
| D-5 | 서비스를 `ReservationLifecycleService`(결제 모름)와 `ReservationApplicationService`(결제 호출·commit)로 분리 | R12, layer-architecture §4, 5.2절의 생성 순환 | **확정** (사용자, 2026-11-04) |
| D-6 | 전역 잠금 순서 `product → offer → reservation → payment → refund → user`. 고객 취소·`pay`·환불은 `offer`를 먼저 잠근 뒤 예약을 잠금 | catalog D49(product → offer), catalog #12가 offer → 예약, 교착 방지 | 임시 (payments C-4 변경 필요) |
| D-7 | 재고 연동은 reservations가 정의한 `StockPort`(`get_terms`/`reserve`/`release`)로 하고, container가 주입. **지금은 임시 `ReadOnlyOfferStockPort`(D-25, 7.1절), catalog의 새 `CatalogStockService`(C-1)가 머지되면 교체** | R11, catalog 6.4 후속("reservations 설계 때 확정"), catalog C12 | 포트 구조는 확정, 구현체는 임시 (D-25) |
| D-8 | 취소 시 재고 복구는 `release`가 담당. **할인이 `is_active=false`면 복구하지 않음** | catalog D40(닫힌 할인에 재고 안 돌려줌, `stock_log` 합 불변식) | 확정(catalog D40을 따름) |
| D-9 | 픽업 검사 순서: 404 → 403(해당 매장) → 409(상태) → 400(코드). 취소: 404 → 403(본인) → 409. 생성: 400 → 401 → 404 → 409 | 상태가 이미 종료인 예약에 대해 코드 일치 여부를 알려 주지 않으려는 의도, payments D-12 방식 | 임시 |
| D-10 | 취소는 상태(`PENDING_PAYMENT`/`RESERVED`)만 확인하고 **시간 제한을 두지 않음** | 명세에 시한 없음, payments D-7(시간 제한 없음) | 임시 (Q-6, catalog C14) |
| D-11 | 결제한 예약 취소는 환불을 **자동 호출**(`RefundPort`, 위약금 payments 정책 = 현재 0원). 고객이 별도 환불 API를 호출하는 경로(payments `refund()` → `cancel_for_refund`)도 지원 | payments D-6(두 진입점 지원), payments D-1(위약금 0) | 임시 (Q-8) |
| D-12 | 점주 사유 일괄 취소는 `waive_penalty=True`로 전액 환불, 재고 복구 없음, 취소 사유는 환불 사유로만 전달(예약 행에 저장하지 않음) | payments D-16, catalog D40·D42 | 확정(payments D-16·catalog D40) |
| D-13 | `pickup_code`는 **예약 생성 때 발급**(대문자 1 + 숫자 5), 전역 고유 보장 없음(검증은 `reservation_id`와 함께) | 명세 확인 필요, payments D-18("예약 쪽에서 발급"), 명세 예시 `A12345` | 임시 (Q-4) |
| D-14 | 픽업 시간 창 검사와 결제 제한 시간은 두지 않음(`rules`의 상수 두 개) | 명세 확인 필요 | 임시 (Q-2, Q-5) |
| D-15 | `RefundPort`의 임시 구현 `NoPaymentRefund`(환불 없음, 7.1절)를 container에 연결. payments 2단계(C-3~C-5)에서 어댑터로 교체. payments의 `InMemoryReservationPort` stub은 이번에 그대로 남음 | payments 코드에 `refund_for_cancelled_reservation` 없음(B-7). 지금은 결제된(`RESERVED`) 예약이 DB에 생길 수 없어 영향 없음(payments가 아직 stub 예약을 씀) | 임시(사용자 승인, 2026-11-04) |
| D-25 | **재고는 임시 포트로 연결**: container `create_stock_port`가 `ReadOnlyOfferStockPort`(7.1절)를 반환. 가격·상점·상품 스냅샷은 catalog의 기존 추상 레포지토리(`DiscountOfferRepository`, `ProductRepository`)와 `StorePort`를 읽기 전용으로 사용. 재고 차감·`stock_log`·복구·잠금은 하지 않음(실서버에서 예약이 재고를 줄이지 않음). 서비스 테스트는 fake `StockPort` | 사용자 결정 2026-11-04(B-6), catalog C-1 미머지 | **확정**(범위 결정) / 임시 구현체는 C-1 머지 시 교체 |
| D-16 | **409 예외는 reservations 전용 기반 `ReservationConflictError(Exception)`(속성 `error_code`)을 상속**하고(`ReservationStateError`, `OfferNotReservableError`, `OutOfStockError` 모두), `src/error_handlers.py`에 이 기반 클래스 하나를 409로 변환하는 핸들러 **한 줄**을 추가한다(auth `EmailDuplicatedError` 패턴). 공용 `ConflictError`는 도입하지 않음. 422는 쓰지 않고 400 `VALIDATION_ERROR` | layer-implementation 예외 절(409는 `Exception` 상속 + 핸들러 한 줄), 사용자 결정 2026-11-04 | **확정** (C-6, Q-14는 임시) |
| D-17 | `PickedUpReservationExistsError`는 reservations 도메인에 **같은 이름·같은 `error_code`·같은 메시지**로 따로 정의(catalog 도메인을 import하지 않음). 두 예외 모두 `ValueError` → 전역 핸들러가 같은 400 응답을 만듦 | R11, catalog 포트 계약(Q28)·Q29 | 임시 (C-2: catalog 포트 docstring의 "catalog 예외" 표현 완화) |
| D-18 | 목록 응답에 `page`, `size`, `total`과 쿼리 `status`, `page`, `size` 추가 | README 확인 5번, 명세의 제안 | 임시 (Q-9) |
| D-19 | 목록 항목과 픽업에 `pickup_code`, `pickup_address` 추가(고객이 픽업 때 쓸 값) | 명세 확인 필요(목록 항목 3) | 임시 (Q-4) |
| D-20 | 취소 응답은 `{id, status, cancelled_at}`, 픽업 응답은 `{id, pickup_code, status, picked_up_at}` 명세 그대로 | 명세 §3, §4, R15 | 확정 |
| D-21 | 소유권 오류는 404로 숨기지 않고 403 | 명세 §3 에러 표(403 본인 예약이 아님) | 확정 |
| D-22 | 테이블 정의는 `schema.sql` 그대로(NULL 허용 컬럼 포함), `price`는 매핑하지 않음 | R14, catalog S3와 같은 방식 | 임시 (S-3) |
| D-23 | 비어 있는 `domain/reservation.py`는 쓰지 않고 삭제 | db-schema 3절("대응 테이블 없음, 확인 필요"), B-5 | 임시 |
| D-24 | payments에 주는 `ReservationPort` 계약: `get` ⇒ `ReservationLifecycleService.get_snapshot(for_update)`(`for_update=True`는 `offer → reservation` 잠금), `mark_paid` ⇒ `mark_paid`, `cancel_for_refund` ⇒ 멱등 취소 + 재고 복구. 어댑터는 payments `application/reservation_adapter.py`에 둠(payments.md 6.3) | payments 6.1·6.3 | 임시 (C-3) |

---

## 9. 정합 이슈 (C-번호) — 다른 모듈에 필요한 변경

이 설계는 아래 파일을 **수정하지 않았습니다.** **C-1~C-5, C-7~C-9는 이번 구현에서 하지 않고 각 담당자에게 넘길 변경 제안입니다**(사용자 결정 2026-11-04). 예외: **C-6의 `src/error_handlers.py` 핸들러 한 줄은 reservations 구현자가 추가**합니다. C-2 중 container 교체는 구현자 범위(7절)이고 `tests/catalog/test_wiring.py` 단언 교체는 catalog 담당 제안입니다(구현자는 깨지는 것만 보고).

| # | 대상 | 문제 | 필요한 변경 | 막는 것 |
| --- | --- | --- | --- | --- |
| C-1 | **catalog** (`domain/discount_offer.py`, `domain/stock_log.py`, `domain/exceptions.py`, `application/`) | 재고 차감·복구가 없음(B-6). `CatalogApplicationService`에 넣으면 `ReservationCancelPort`를 받는 그 서비스를 예약 생성이 받아 생성 순환(catalog C12, CI-11) | ① 도메인 `DiscountOffer.deduct_stock(quantity, now)`: 수량 `int >= 1`(ValueError), `effective_status(now)`가 `ON_SALE`이 아니면 새 `OfferNotReservableError`(409 `OFFER_NOT_RESERVABLE`), 재고 부족·품절이면 새 `OutOfStockError`(409 `OUT_OF_STOCK`), 차감 후 `_sync_status`. `restore_stock(quantity, now) -> bool`: `is_active=false`면 변경 없이 False(D40), 초기 재고 초과면 ValueError. ② `StockLog.reservation(offer_id, user_id, quantity)`(`-quantity`, 이유 "예약"), `StockLog.reservation_release(offer_id, user_id, quantity, reason)`(`+quantity`). ③ **예약 포트를 받지 않는** 새 `CatalogStockService`(`application/stock_service.py`; 생성자 `stores: StorePort, products, offers, stock_logs`, session·clock 없음)에 `get_terms(offer_id, *, for_update=False)`, `reserve(offer_id, quantity, *, user_id, now)`, `release(offer_id, quantity, *, user_id, reason)`. `OfferTerms` 값 객체(`offer_id, owner_id, store_name, product_name, pickup_address, sale_price, pickup_start, pickup_end`)는 catalog `views.py`. 모두 commit하지 않음, 할인 행 `for_update=True`(offer만, product는 잠그지 않음) ④ container `create_catalog_stock_service` | 예약 생성·취소 (DB 통합 테스트와 container 연결) |
| C-2 | **catalog** (`tests/catalog/test_wiring.py`, `application/ports.py` docstring, `infrastructure/reservation_lookup.py`·`reservation_cancel.py`) | CI-10, CI-11 교체. `test_wiring.py`가 `NoReservation*`를 단언. `ReservationCancelPort` docstring이 "`PickedUpReservationExistsError`를 낸다"로 catalog 예외를 가리킴 | reservations 구현 PR에서 단언을 "`NoReservation*`가 아님"으로 교체하고, 임시 `NoReservationLookup`·`NoReservationCancel`과 두 파일은 삭제. docstring은 "같은 `error_code`의 `ValueError` 하위 예외"로 완화(D-17). 두 포트의 container 팩토리가 세션을 쓰게 되어 인자 없는 싱글턴이 아님(5.1절) | container 교체 |
| C-3 | **payments** (`presentation/dependencies.py`, `application/reservation_stub.py`, `application/ports.py`) | 지금 `InMemoryReservationPort()`를 쓰고 container 밖에서 서비스를 만듦. 설계(payments.md 6.3)는 `payments/application/reservation_adapter.py`의 `ReservationAdapter`가 `reservations.application`을 import | `ReservationAdapter(lifecycle: ReservationLifecycleService)`가 `get`(→ `get_snapshot`, `ReservationView`를 payments `ReservationSnapshot(id, user_id, total_price, status, pickup_start=view.offer.pickup_start)`으로 변환, 없으면 None), `mark_paid`(→ Lifecycle `mark_paid`), `cancel_for_refund`(→ Lifecycle `cancel_for_refund`)를 구현. `get_payment_service`는 `Depends(provide_reservation_lifecycle_service)`를 받아 어댑터를 만든다(또는 payments도 container 구역으로 이동). `reservation_stub.py` 삭제 | 결제 ↔ 예약 실제 연결 |
| C-4 | **payments** (`application/service.py`) + container | `refund_for_cancelled_reservation(snapshot, reason, *, waive_penalty=False, commit=True)`가 아직 없음. reservations는 payments 서비스를 `RefundPort` 어댑터로 받아야 하는데 `PaymentApplicationService`가 container에 등록돼 있지 않음 | payments에 해당 메서드와 container 팩토리(`create_payment_service`)를 추가하고, reservations 쪽 `application/payment_refund_adapter.py`(`RefundTarget` → payments `ReservationSnapshot` 변환 후 호출, 구조적 `RefundPort`)를 container의 `create_refund_port`에 연결, 임시 `NoPaymentRefund` 삭제. **스냅샷에는 취소 전 상태 `RESERVED`를 넘김**(payments의 `ensure_refundable_state`와 맞추기 위해) | 결제된 예약 취소 시 환불 |
| C-5 | **payments** (`application/service.py` `refund()`, 문서 4.3.3, C-4 잠금 순서) | payments 문서의 잠금 순서가 "예약 → 결제"이고 `reservations.get(for_update=True)`를 먼저 부름. D-6의 전역 순서는 "offer → 예약" | 어댑터의 `get(for_update=True)`가 이미 offer를 먼저 잠그므로(D-24) payments 코드는 호출 순서 변경 없이 맞음. payments.md C-4의 잠금 순서 문구에 `offer`를 앞에 추가하고, `payments.reservation_id`의 `unique=True`를 제거·부분 UNIQUE로 바꾸는 payments S-2와 FK(`pickup_reservations.id`) 추가를 reservations 모델이 머지된 뒤에 진행 | 교착 방지 문서 정합, FK |
| C-6 | **`src/error_handlers.py`** (사용자 결정 2026-11-04: 공용 `ConflictError`/`src/common` 도입 안 함. **이 항목만 reservations 구현자가 직접 수정**) | 409 처리가 없음(auth는 `EmailDuplicatedError` 전용, payments는 router에서 `HTTPException` 변환) | reservations `domain/exceptions.py`의 `ReservationConflictError`를 import해 `@app.exception_handler(ReservationConflictError)`로 409 `{success: false, error_code: exc.error_code, message}`를 내는 핸들러 **한 개(한 줄 규모)** 추가. 다른 모듈의 409는 각자 같은 방식으로 추가 | 409 응답 |
| C-7 | **catalog** 문서 (`docs/design/catalog.md` 6.4 후속, CI-10, CI-11, C9, C12) | 이 설계가 요구사항 "reservations가 `deduct_stock`을 주입받는다"를 `StockPort` + `CatalogStockService`로 바꿈 | 6.4절 후속 문구와 C12 해법("읽기/쓰기 분리")을 이 설계 5.2절로 갱신. C9 답: **예약은 할인의 `is_active`·`status`와 무관하게 자기 상태로 진행**(픽업·취소 가능, 취소 시 재고만 복구하지 않음) | 문서 정합 |
| C-8 | **stores** (`docs/design/stores.md` 폐점 시 "픽업 대기 예약" 확인) | `has_pickup_pending_for_store`에 필요한 예약의 매장 정보가 `pickup_reservations`에 없음(`store_id` 컬럼 없음, `store_name`은 스냅샷뿐). reservations가 catalog·stores의 테이블을 조인하면 R11 위반 | 후속. 스키마 변경 S-4(`store_id` 스냅샷 컬럼) 또는 catalog가 `offer_ids_by_store`를 포트로 제공. 지금은 stores가 `PickupPendingPort`를 정의하고 구현은 후속 | 폐점 검사 (이번 범위 아님) |
| C-9 | **docs/reference** (`reservations.md`) | 명세 자체의 빈칸: `pickup_code`가 응답에 없음, 상점주용 예약 목록 없음, 페이지네이션 없음, `RESERVED` 의미, 422 vs 400 | 사용자 결정(10절) 후 명세에 반영 | R15 |

---

## 스키마 변경 제안 (S-번호, `db-schema` 기준. 이번 구현은 변경 없이 진행)

| # | 제안 | 이유 | 영향 |
| --- | --- | --- | --- |
| S-1 | `status`에 `CHECK (status IN ('PENDING_PAYMENT','RESERVED','PICKED_UP','CANCELLED'))` | 상태 값 확정 후 DB 방어선(db-schema 5절 3항) | `schema.sql`·`SKILL.md`·`models.py` 동시 수정 |
| S-2 | `status`, `unit_price`, `total_price`, `pickup_code`, `store_name`, `pickup_address`, `product_name`을 NOT NULL로, `CHECK (total_price = unit_price * quantity)` | 도메인은 모두 필수로 취급 | 기존 행이 없어 안전 |
| S-3 | `price` 컬럼 삭제(db-schema 5절 1항) | `unit_price`/`total_price`와 중복. catalog `discount_offers.price`와 같은 처리 | 현재는 매핑하지 않음 |
| S-4 | `store_id UUID REFERENCES stores(id)` 스냅샷 컬럼 + 인덱스 | 폐점 검사(C-8), 상점주용 예약 목록(Q-10), 픽업 시 상점주 확인을 catalog 조회 없이 가능 | 새 컬럼. 선택 |
| S-5 | `cancel_reason VARCHAR(200)`, `cancelled_by`(`CUSTOMER`/`OWNER`/`SYSTEM`) | 일괄 취소 사유 저장(catalog Q28) | 선택 |
| S-6 | 인덱스 `(user_id, created_at DESC)` | 목록 정렬·페이지네이션 | 성능 |

---

## 10. 질문 목록과 임시 기본값

**Q-1~Q-16 전부 "임시(사용자 승인, 2026-11-04)"**: 아래 기본값으로 진행하되 확정은 아닙니다. 임시 기본값은 확정이 아니라 **제안**입니다. 코드는 `reservations/domain/rules.py`·enum 한곳에 모읍니다(1.7절).

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 |
| --- | --- | --- | --- | --- |
| Q-1 | `RESERVED`가 결제 완료 상태인지, `PENDING_PAYMENT`와의 관계 | 명세 §2 확인 필요, README 상태 값 표, db-schema 5절 3항 | `PENDING_PAYMENT` 결제 대기, `RESERVED` 결제 완료·픽업 대기 | payments D-9, 예약 목록 응답 예시 |
| Q-2 | 결제하지 않은 예약(`PENDING_PAYMENT`)의 결제 제한 시간과 재고 반환 시점 | 명세 §1 확인 필요, payments D-15 | 결제 제한 시간 없음, 만료 상태 없음. **위험: 결제하지 않은 예약이 재고를 계속 잡고 있음.** 고객 취소로만 복구 | payments D-15가 같은 값을 가정 |
| Q-3 | 상점주가 자기 매장 할인을 예약할 수 있는지 | 명세 §1 확인 필요 | 허용(`ALLOW_OWNER_SELF_RESERVATION=True`). 생성은 로그인한 모든 역할(`CurrentUser`) | 명세에 금지 규칙 없음, payments D-12 방식 |
| Q-4 | `pickup_code` 발급 시점·형식·고유 범위, 고객에게 보여 줄 위치 | 명세 §2·§4 확인 필요, README 확인 18번, db-schema 5절 5항 | 생성 때 발급, `A12345` 형식(대문자 1+숫자 5), 전역 고유 아님, 목록 항목과 픽업 응답에 `pickup_code`·`pickup_address` 추가 | payments D-18, 명세 예시 |
| Q-5 | 픽업 시간(`pickup_start`~`pickup_end`) 밖에서 픽업 처리 가능 여부 | 명세 §4 확인 필요 | 가능(`PICKUP_WINDOW_ENFORCED=False`) | 명세에 제한 없음 |
| Q-6 | 취소 가능 시한(catalog `cancel_policy`의 "픽업 시작 1시간 전")을 예약 취소가 강제하는지 | catalog D55·C14, 명세 §3(409은 상태만) | 강제하지 않음(상태만 확인). 위약금은 payments 정책(현재 0원) | payments D-1, D-7 |
| Q-7 | 취소 주체·사유를 예약 행에 저장할지 | catalog Q28 | 저장하지 않음(`cancelled_at`만). 사유는 환불 사유로만 전달 | 스키마에 컬럼 없음 |
| Q-8 | 결제한 예약 취소가 환불을 자동으로 만드는지, 환불 API를 따로 호출해야 하는지 | 명세 §3 확인 필요, README 확인 20번, payments D-6 | 취소가 자동 환불을 호출하고 환불 API 경로도 지원(둘 다) | payments D-6 임시 기본값 |
| Q-9 | 목록 `page`/`size`/`total`, `status` 필터, 정렬 | 명세 §2 확인 필요, README 확인 5번 | `page=1`, `size=20`(최대 100), `status` 선택, 응답에 `page`·`size`·`total` 추가, 정렬 `created_at DESC` 고정 | catalog 목록과 같은 형식 |
| Q-10 | 상점주가 `reservation_id`를 알 방법(상점주용 예약 목록 또는 `pickup_code`만으로 처리) | 명세 §4 확인 필요, README 확인 19번 | 이번 범위는 명세의 4개 엔드포인트만. 상점주 목록 API는 **만들지 않음**(픽업이 `reservation_id` 필요). S-4와 함께 후속 | 명세 범위 |
| Q-11 | 같은 사용자의 중복 예약, 1인 최대 수량, 멱등 키 | 명세에 없음 | 제한 없음, 멱등 키 없음(재전송하면 새 예약이 생김) | 지어내지 않음 |
| Q-12 | 픽업 코드 입력 실패 횟수 제한 | 명세에 없음(보안 위험: 6자리 코드 무차별 대입) | 제한 없음. 접근이 `OwnerUser`이면서 해당 매장·알려진 `reservation_id`로 한정돼 위험을 낮춤. 필요하면 후속으로 시도 횟수 컬럼 | 지어내지 않음, 위험만 표시 |
| Q-13 | 결제 실패 시 예약·재고 처리 | 사용자 요청 (b), payments D-11 | 예약 `PENDING_PAYMENT` 유지, 재고 유지, 재시도·취소 가능. 자동 복구 없음 | payments가 실패 시 롤백만 함 |
| Q-14 | 형식 오류 코드(명세 422 vs 프로젝트 400) | 명세, README 확인 3번 | 400 `VALIDATION_ERROR` | payments D-17, 전역 핸들러 |
| Q-15 | 폐점된 상점·비활성 상품의 예약된 건의 픽업·취소 | catalog C9·C10, stores 폐점 | 예약은 할인·상품·상점 상태와 무관하게 자기 상태로 진행(C-7) | catalog C9 요구사항 |
| Q-16 | 이 설계가 규칙과 충돌하는 요구 | `backend-invariants` | 충돌 없음. 단 명세의 `409`(상태 충돌)는 R6·R7을 지키려고 `ReservationConflictError` + 핸들러 한 줄(D-16, C-6)이 필요하고, 명세의 `422`는 전역 핸들러대로 400 (R15 예외, 이유 보고) | R6, R7, R15 |

---

## 11. 불변 규칙 점검 (설계 기준)

R1(domain은 `hmac` 등 표준 라이브러리만, `secrets`는 infrastructure에서 사용), R2(application은 포트·도메인만, infrastructure·presentation import 없음), R3(전이·소유·코드 검증은 엔티티), R4(`*Model` 미노출), R5(commit은 ApplicationService, 레포 `flush`), R6(도메인 예외, HTTPException 없음), R7(전역 핸들러), R8(생성자 필수·기본 생성 없음), R9(`provide_*` 2개 매핑), R10(포트 선언 메서드만 호출), R11(catalog·payments는 reservations 정의 포트로만, ORM·레포·서비스 내부 미사용), R12(5.2절의 한 방향 생성 그래프), R13(같은 세션, 호출되는 쪽 `commit=False`/commit 없음), R14(`schema.sql`과 동일, `price`는 매핑 제외 사유 명시), R15(명세 필드·URI, 추가·변경은 D-16·D-18·D-19·Q-14로 표시), R16(새 의존성·시크릿 없음).
