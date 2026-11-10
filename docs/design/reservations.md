# reservations 모듈 설계안 (예약·취소·픽업)

- 작성 기준일: 2026-11-04, 브랜치 `claude/reservations` (`origin/main` 3fe2389 기준)
- 대상: `src/reservations` (테이블 `pickup_reservations`)
- 기준 문서: `docs/reference/reservations.md`, `docs/reference/README.md`, `.claude/skills/db-schema/{SKILL.md,schema.sql}`, `docs/design/{catalog,payments,stores,auth}.md`, `src/catalog/**`, `src/payments/**`, `src/container.py`, `src/main.py`
- 이 문서는 설계만 담습니다. 코드는 수정하지 않았습니다.
- **임시 기본값은 확정이 아니라 제안입니다.** 모두 `reservations/domain/rules.py` 한 파일(또는 enum)에 모아 나중에 바꾸기 쉽게 합니다(9절).
- 결정 표(D-번호)는 8절, 다른 모듈에 필요한 변경(C-번호)은 9절, 사용자 질문(Q-번호)은 10절입니다.
- **갱신 2026-11-05**: 사용자가 준 예약 3개 EP 명세(생성·내 목록·취소)와 reference·이 설계안·구현 커밋 `66532ac`의 코드를 대조했습니다. 결과는 **12절(3자 대조표)**, admin 설계와의 정합은 **13절**입니다. 새 번호는 D-26~D-30, C-10~C-14, Q-17~Q-21입니다. **같은 날 D-26~D-30, Q-17~Q-21은 사용자가 확정했고 C-10·C-11은 구현 시 수정으로 승인됐습니다. 구현자 작업 목록은 14절입니다.** 기존 확정 결정과 픽업 EP(#25) 내용은 바꾸지 않았고, 0절·8절 D-9 한 곳만 실행 결과로 고쳤습니다. 이 문서의 4~5절 등은 "설계 당시" 서술이며 12절과 다르면 12절이 최신입니다.

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
| B-11 (2026-11-05) | `git log --oneline -- src/reservations docs/design/reservations.md src/error_handlers.py`, `Glob src/reservations/**/*.py`, `tests/reservations/**` | 커밋 `66532ac`로 `src/reservations/**` 25개 파일과 `tests/reservations/**` 7개 파일이 구현됨 | **B-5의 "모든 .py가 0줄"은 설계 당시 상태이며 더는 사실이 아닙니다.** 이후 대조는 실제 코드 기준입니다(12절). |
| B-12 | `(cd src && uv run python -c "import main")` (`.env`가 없어 `DATABASE_URL`, `JWT_SECRET_KEY` 등을 **셸 환경변수로만** 지정) | 환경변수 없이는 `RuntimeError: DATABASE_URL 환경변수가 설정되지 않았습니다.`, 지정하면 `IMPORT_OK` | 코드는 불러와집니다. 저장소에 `.env`가 없는 것은 로컬 환경 사정이며 `.env.example`에는 필요한 키 4개가 있습니다(B-3과 같음). |
| B-13 | `python3 .claude/skills/layer-check/check_layers.py` → `bash: python3: command not found`. 대신 `uv run python .claude/skills/layer-check/check_layers.py` | 위반 2건(`payments/application/service.py:19`, `:20`, `[의존방향]`), 경고 3건 | B-4 기준선과 같음. **reservations 위반 0건**(검사한 파일 110개, reservations 포함). |
| B-14 | `uv run pytest ...` → `An Application Control policy has blocked this file. (os error 4551)`. 대신 `uv run python -m pytest tests/reservations -rs -q` | `47 passed, 7 skipped` (skipped 7건은 모두 `tests/reservations/test_api_db.py`, 사유: 테스트 DB 접속 실패 `password authentication failed`) | **DB 테스트 7건은 이번에 실행하지 못했습니다. R16에 따라 skip은 통과가 아닙니다.** 12절의 "실행 확인"은 fake 서비스를 주입한 HTTP 레벨 실험과 코드 정독 결과이고, DB를 쓰는 실제 동작(재고 차감 등)은 확인하지 못했습니다. |
| B-15 | `TestClient`로 fake 서비스를 주입해 예외별 HTTP 응답을 확인(12.2절) | 도메인 예외는 모두 공통 형식으로 변환되지만 **처리되지 않은 예외(500)는 `{success, error_code, message}` 형식이 아닌 평문 `Internal Server Error`** | `src/error_handlers.py`에 `Exception` 핸들러가 없음. R7 위반 후보(C-10). |
| B-16 | `Grep NoReservation\|catalog_adapters\|InMemoryReservationPort src` | `src/container.py:70-71`, `:151-156`이 여전히 catalog의 `NoReservationLookup`·`NoReservationCancel`을 연결하고, `reservations/application/catalog_adapters.py`는 만들어졌지만 **container에서 쓰이지 않음**. payments는 `payments/presentation/dependencies.py:34`에서 `InMemoryReservationPort()`를 그대로 씀. `src/admin/**`는 없음 | 7절·5.1절의 "container 교체(CI-10, CI-11)"가 **미이행**입니다(C-11). 실서버에서 결제된 예약(`RESERVED`)이 생길 수 없다는 7.1절 전제는 그대로입니다. |

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

`catalog.domain.store_ref.StoreRef`와 같은 패턴입니다. 속성: `offer_id`, `owner_id`(상점주 `users.id`), `store_name`, `product_name`, `pickup_address`, `sale_price`, `pickup_start`, `pickup_end`. `OfferRef.from_info(info)`(classmethod, `Any`를 받아 속성으로 복사), `ensure_owned_by(user_id, message)` → `NotPickupStoreOwnerError`(403), `ensure_not_owned_by(user_id)` → `ValueError`(400, `ALLOW_OWNER_SELF_RESERVATION=False`일 때만 사용), `ensure_pickup_time(now)` → `PickupOutsideWindowError`(400 `PICKUP_OUTSIDE_WINDOW`, 항상 검사, `pickup_start <= now <= pickup_end` 양 끝 포함).

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
| ~~`PICKUP_WINDOW_ENFORCED`~~ | 삭제(2026-11-10). 픽업 시간 제한은 확정 규칙이라 스위치를 두지 않는다 | Q-5 확정 |
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
| `exists_by_offer(offer_id)` | `bool` | **(D-39로 catalog 어댑터에서는 더 쓰지 않음)** 상태와 관계없이 한 건이라도 있으면 True. 삭제 여부는 C-21 |
| `exists_non_cancelled_by_offer(offer_id)` | `bool` | catalog `has_reservations_for_offer`용(catalog D28·D81, 요구 조건 REQ-17). **`CANCELLED`가 아닌** 예약(`PENDING_PAYMENT`·`RESERVED`·`PICKED_UP`)이 한 건이라도 있으면 True. 구현: `SELECT id FROM pickup_reservations WHERE offer_id = :id AND status <> 'CANCELLED' LIMIT 1`(`offer_id` 인덱스). 잠금 없음(호출 측 catalog #11이 할인 행을 먼저 `FOR UPDATE`로 잠그고, 예약 생성도 할인 잠금 아래에서 insert하므로 직렬화된다). 추상 `ReservationRepository`에 선언하고 `SqlAlchemyReservationRepository`가 구현 |
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
(4번 앞에서 항상 `view.offer.ensure_pickup_time(now)`를 호출한다: `pickup_start <= now <= pickup_end`(양 끝 포함)가 아니면 400 `PICKUP_OUTSIDE_WINDOW`, 쓰기 없음. Q-5 확정, 사용자 결정 2026-11-10. 순서: 403(상점주 아님) → 404 → 400(시간) → 409(상태) → 400(코드))

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
| 23 | GET | `/v1/reservations/me` (D-27 확정, 2026-11-05. 이전 `/v1/users/me/reservations`) | `CurrentUser` | 쿼리 `status`, `page`, `size` | `ReservationListResponse` | 200 | 400 `VALIDATION_ERROR`(잘못된 `status`·`page`·`size`), 401 |
| 24 | PATCH (D-26 확정, 2026-11-05. 이전 POST) | `/v1/reservations/{reservation_id}/cancel` | `CurrentUser`(+서비스에서 본인 확인) | 없음 | `ReservationCancelResponse` | 200 | 400(잘못된 UUID), 401, 403 `FORBIDDEN`, 404 `NOT_FOUND`, 409 `RESERVATION_ALREADY_CANCELLED`/`RESERVATION_ALREADY_PICKED_UP` |
| 25 | POST | `/v1/reservations/{reservation_id}/pickup` | `OwnerUser`(+서비스에서 해당 매장 확인) | `PickupRequest` | `PickupResponse` | 200 | 400 `PICKUP_CODE_MISMATCH`/`VALIDATION_ERROR`, 401, 403 `FORBIDDEN`(역할 불일치 또는 다른 매장), 404 `NOT_FOUND`, 409 `RESERVATION_NOT_PAID`/`RESERVATION_ALREADY_*` |

- 인증·권한 별칭은 `auth.presentation.dependencies`의 `CurrentUser`, `OwnerUser`만 씁니다(D-인증의존성). 401은 auth가 `WWW-Authenticate: Bearer`와 함께 내고, 403(역할)도 auth가 냅니다. 소유권(본인 예약, 해당 매장)은 도메인 메서드의 `PermissionError` 하위 예외입니다.
- router는 서비스만 호출하고 예외를 잡지 않으며 `HTTPException`을 만들지 않습니다(R6, R7). 에러 형식은 전역 핸들러가 `{success, error_code, message}`로 만듭니다.
- 라우터는 `APIRouter(prefix="/v1")`, `tags=["예약"]`, 엔드포인트마다 `summary`.
- `/v1/reservations/me`(D-27 확정)는 현재 다른 EP와 겹치지 않습니다(실행 확인: 변경 전 404). 나중에 `GET /v1/reservations/{reservation_id}`가 생기면 `/me`를 먼저 선언합니다. 라우트 목록은 라우터 한 곳에서 보이게 `/me`를 `{reservation_id}` 경로보다 위에 둡니다.

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

어댑터 파일(`application/catalog_adapters.py`, reservations가 소유): `OfferReservationLookup`(레포지토리 `exists_non_cancelled_by_offer` 호출, D-39. 메서드 이름 `has_reservations_for_offer`는 catalog 포트 서명이라 그대로), `OfferReservationCanceller`(`ReservationApplicationService.cancel_all_for_offer` 호출). 둘 다 catalog의 포트를 import하지 않고 구조적으로 맞춥니다(catalog가 쓰는 쪽이므로 포트 정의는 catalog `application/ports.py`).

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
- 확정 경로·메서드(D-26, D-27) 단언: `PATCH /v1/reservations/{id}/cancel`, `GET /v1/reservations/me`, `POST /v1/reservations`, `POST /v1/reservations/{id}/pickup`이 등록돼 있고, `POST .../cancel`은 405, `GET /v1/users/me/reservations`는 404. `test_api_db.py`의 목록 호출도 `/v1/reservations/me`로 바꿉니다.
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
| D-9 | 픽업 검사 순서: 404 → 403(해당 매장) → 409(상태) → 400(코드). 취소: 404 → 403(본인) → 409. 생성: **401 → 400(형식·수량) → 404 → 409** (2026-11-05 실행 확인으로 수정: 인증 의존성이 본문 검증보다 먼저라 토큰 없이 `quantity: 0`을 보내면 401. 이전 문구 "400 → 401"은 틀렸음) | 상태가 이미 종료인 예약에 대해 코드 일치 여부를 알려 주지 않으려는 의도, payments D-12 방식 | 임시 |
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
| D-26 | **취소 HTTP 메서드**: 사용자 명세는 `PATCH /v1/reservations/{id}/cancel`, reference·4.1절·코드는 `POST`. 임시 기본값은 **명세대로 `PATCH` 하나로 통일**(`POST`는 제거). 코드는 `router.py:57`(데코레이터), `tests/reservations/test_wiring.py`의 라우트 목록, `test_api_db.py`가 바뀜 | 사용자 명세(2026-11-05), R15. 실행 확인: 현재 `PATCH`는 `405 HTTP_ERROR "Method Not Allowed"`(`Allow: POST`) | **확정** (사용자, 2026-11-05, Q-17). 4.1절 #24 행을 `PATCH`로 갱신함 |
| D-27 | **내 목록 URI**: 사용자 명세는 `GET /v1/reservations/me`, reference·4.1절·코드는 `GET /v1/users/me/reservations`. 임시 기본값은 **명세 경로로 변경**. 이후 `GET /v1/reservations/{reservation_id}` 상세가 생기면 `/me`를 먼저 선언해야 함 | 사용자 명세, R15. 실행 확인: 현재 `/v1/reservations/me`는 `404 NOT_FOUND "Not Found"`, 다른 EP와 겹치지 않음(`/reservations/{id}/cancel`뿐) | **확정** (사용자, 2026-11-05, Q-18). 4.1절 #23 행 갱신. reference README #23 행·`reservations.md` §2도 같이 바뀜(C-12) |
| D-28 | **400과 422의 경계**: 명세는 400="잘못된 수량", 422="요청 데이터 형식 오류". 전역 핸들러는 `RequestValidationError` 전부를 **400 `VALIDATION_ERROR`**로 변환하므로 수량 0·음수·문자열·소수·누락, 잘못된 UUID(본문·경로), 잘못된 `status`·`page`가 모두 400(12.2절 실행 결과). 임시 기본값은 **현재대로 전부 400**(Q-14와 같음). 대안은 형식 오류만 422로 나누는 것이지만 전역 핸들러 변경이라 auth·payments·admin 응답까지 바뀜 | 사용자 명세, payments D-17, admin B-8·D26, `error_handlers.py:38-48` | **확정** (사용자, 2026-11-05, Q-19: 전부 400, 422 쓰지 않음). R15 예외 사유: 프로젝트 전체가 400을 쓰고 있어 한 모듈만 422로 바꾸면 일관성이 깨짐 |
| D-29 | **목록 기본 페이지 크기**: 명세는 페이지네이션이 없어 전체를 돌려주는 것으로 읽힘. 코드는 `size` 기본 20(최대 100)이라 21번째부터는 `page=2`를 요청해야 보임. 임시 기본값은 **D-18 유지**(`page`·`size`·`total` 확장, 기본 20). 명세만 보고 만든 클라이언트가 20건에서 잘린다는 점을 질문으로 올림 | 명세 §2, README 확인 5번, D-18 | **확정** (사용자, 2026-11-05, Q-20: D-18 유지). 명세에 페이지네이션 추가가 필요하다는 점은 C-12에 포함 |
| D-30 | **취소 때 환불 필요 여부를 잠금 후 상태로 판정**: 현재 `service.py:66`이 `was_paid`를 **잠금 전** `get_snapshot`으로 구하고, `lifecycle.cancel`(`lifecycle_service.py:60-79`)이 나중에 잠그고 전이함. 그 사이 결제(`pay`)가 `PENDING_PAYMENT → RESERVED`를 커밋하면 취소는 성공하지만 `was_paid=False`라 **환불이 호출되지 않아 결제 금액·포인트가 사라짐**(`pay`와 취소가 같은 예약에 동시에 올 때). 제안: `lifecycle.cancel`이 잠금 안에서 **취소 직전 상태로 `RefundTarget`을 만들어** 반환(`cancel_all_for_offer`의 `CancelledReservation(reservation, refund_target)`과 같은 방식)하고, 서비스는 그 값으로만 환불 호출 여부를 정함. 전이표·메서드 이름은 그대로 | 3.3절 ③ 3단계, 2.4절 "결제 vs 취소" 행("잠금 안에서 상태 재확인")과 불일치, D-6 | **확정** (사용자, 2026-11-05), 코드 변경 필요(14절 W-5). 지금은 payments가 stub 예약만 쓰므로 실서버 영향 없음(B-16). payments 연결(C-3) 전에 반영 필요 |

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
| C-10 | **`src/error_handlers.py`** (모듈 밖 공용 파일, 이번에 수정하지 않음) | 처리되지 않은 예외가 `{success, error_code, message}` 형식이 아니라 평문 `Internal Server Error`로 나감(12.2절 실행: `RuntimeError` → `500`, 본문 평문). 명세 3개 EP 모두 `500 서버 오류`를 적었고 R7은 모든 에러 응답이 공통 형식이라고 정함 | `@app.exception_handler(Exception)` 한 개 추가: `500`, `error_code="INTERNAL_SERVER_ERROR"`(이름은 임시), 메시지는 고정 문구(예외 내용·스택 비노출), 서버 로그에 예외 기록. 모든 모듈에 적용되므로 소유자·이름은 사용자 결정 (Q-21). 추가해도 기존 `ValueError`·`LookupError` 핸들러는 가장 가까운 클래스가 우선이라 영향 없음 | 500 응답 형식 (R7). **구현 시 수정(사용자 승인 2026-11-05)**, 14절 W-6 |
| C-11 | **`src/container.py`**, `tests/catalog/test_wiring.py` (7절 쓰기 범위 안이지만 **구현 누락**) | 5.1절 "catalog 포트 교체(CI-10, CI-11)"가 코드에 없음(B-16). `catalog_adapters.py`는 있으나 연결되지 않아, catalog가 예약 존재를 항상 "없음"으로 알고 일괄 취소도 0건. 예약이 있는 할인도 수정·판매 중단될 수 있고 중단해도 예약이 취소되지 않음 | `create_reservation_lookup(reservations=Depends(create_reservation_repository)) -> OfferReservationLookup`, `create_reservation_cancel(service=Depends(create_reservation_service)) -> OfferReservationCanceller`로 교체하고 `_reservation_lookup`·`_reservation_cancel` 싱글턴과 `NoReservation*` import 삭제(5.1절). `tests/catalog/test_wiring.py`의 `isinstance(... NoReservation*)` 단언 교체(C-2). 생성 순환이 없는지 `import main`으로 확인(`create_reservation_service` → catalog 서비스를 받지 않으므로 5.2절대로 순환 없음) | 예약 중인 할인 보호, 취소 흐름의 상류. **구현 시 수정(사용자 승인 2026-11-05)**: catalog `NoReservation*` 교체에 더해 **payments `InMemoryReservationPort` 교체**(payments C-3, `payments/presentation/dependencies.py:34`)도 승인 범위. 14절 W-7·W-8 |
| C-12 | **docs/reference** (`reservations.md` §2·§3, `README.md` #23·#24 행) | D-26·D-27이 확정되면 메서드·경로가 바뀜. 또한 사용자 명세의 3개 EP 에러 표는 reference와 같은 내용(차이 없음) | D-26·D-27 확정(2026-11-05)에 따라 `PATCH .../cancel`, `GET /v1/reservations/me`로 갱신(R15). **D-29 확정에 따라 §2에 `page`·`size`·`status` 쿼리, 응답의 `page`·`size`·`total`, 항목의 `pickup_code`·`pickup_address`(D-18·D-19)도 명세에 추가**(사용자 명세 원문에는 없음). 400/422는 전부 400(D-28)이므로 §1~§4 에러 표의 422 행을 "400 `VALIDATION_ERROR`"로 바꾸거나 주석 | 문서 정합. reference는 이번 설계 작업에서 수정하지 않음 |
| C-13 | **auth** (정지 계정 처리, admin.md D8·D35 연동) | admin이 구현되면 정지된 CUSTOMER는 `CurrentUser` 의존성에서 403 `FORBIDDEN`("정지된 계정입니다.")이 됨. 사용자 명세의 생성·목록·취소 에러 표에는 403(생성·목록)이 없음. 취소의 403은 "본인 예약이 아님"으로만 적혀 있어 같은 `error_code`로 섞임 | admin 구현 때 reference에 "정지된 계정 403"을 추가할지 결정. reservations 코드 변경은 없음(`CurrentUser` 그대로, admin.md 5.5절도 고객 취소 EP는 차단 유지) | 에러 표 정합 |
| C-14 | **admin** 요구사항(13절 전체) | admin.md는 reservations가 비어 있다는 전제로 쓰였음. 이 설계에 없는 `ReservationAdminPort` 어댑터 2개, 사용자별·매장별 조회, 픽업 의존성 교체가 필요 | 13절의 A-1~A-6을 reservations가 받아야 할 요구로 기록. admin.md는 수정하지 않음 | admin EP 4·6 |

---

## 스키마 변경 제안 (S-번호, `db-schema` 기준. 이번 구현은 변경 없이 진행)

| # | 제안 | 이유 | 영향 |
| --- | --- | --- | --- |
| S-1 | `status`에 `CHECK (status IN ('PENDING_PAYMENT','RESERVED','PICKED_UP','CANCELLED'))` | 상태 값 확정 후 DB 방어선(db-schema 5절 3항) | `schema.sql`·`SKILL.md`·`models.py` 동시 수정 |
| S-2 | `status`, `unit_price`, `total_price`, `pickup_code`, `store_name`, `pickup_address`, `product_name`을 NOT NULL로, `CHECK (total_price = unit_price * quantity)` | 도메인은 모두 필수로 취급 | 기존 행이 없어 안전 |
| S-3 | `price` 컬럼 삭제(db-schema 5절 1항) | `unit_price`/`total_price`와 중복. catalog `discount_offers.price`와 같은 처리 | 현재는 매핑하지 않음 |
| S-4 | `store_id UUID REFERENCES stores(id)` 스냅샷 컬럼 + 인덱스 | 폐점 검사(C-8), 상점주용 예약 목록(Q-10), 픽업 시 상점주 확인을 catalog 조회 없이 가능 | 새 컬럼. 선택 |
| S-5 | `cancel_reason VARCHAR(200)`, `cancelled_by`(`CUSTOMER`/`STORE`/`SYSTEM`, §16 D-40 확정값) | 일괄 취소 사유 저장(catalog Q28) | 선택 |
| S-6 | 인덱스 `(user_id, created_at DESC)` | 목록 정렬·페이지네이션 | 성능 |

---

## 10. 질문 목록과 임시 기본값

**Q-1~Q-16 전부 "임시(사용자 승인, 2026-11-04)"**: 아래 기본값으로 진행하되 확정은 아닙니다. **Q-17~Q-21(2026-11-05 추가)은 같은 날 사용자가 임시 기본값 그대로 "확정"했습니다**(각 행 참조). 임시 기본값은 확정이 아니라 **제안**입니다. 코드는 `reservations/domain/rules.py`·enum 한곳에 모읍니다(1.7절).

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 |
| --- | --- | --- | --- | --- |
| Q-1 | `RESERVED`가 결제 완료 상태인지, `PENDING_PAYMENT`와의 관계 | 명세 §2 확인 필요, README 상태 값 표, db-schema 5절 3항 | `PENDING_PAYMENT` 결제 대기, `RESERVED` 결제 완료·픽업 대기 | payments D-9, 예약 목록 응답 예시 |
| Q-2 | 결제하지 않은 예약(`PENDING_PAYMENT`)의 결제 제한 시간과 재고 반환 시점 | 명세 §1 확인 필요, payments D-15 | 결제 제한 시간 없음, 만료 상태 없음. **위험: 결제하지 않은 예약이 재고를 계속 잡고 있음.** 고객 취소로만 복구 | payments D-15가 같은 값을 가정 |
| Q-3 | 상점주가 자기 매장 할인을 예약할 수 있는지 | 명세 §1 확인 필요 | 허용(`ALLOW_OWNER_SELF_RESERVATION=True`). 생성은 로그인한 모든 역할(`CurrentUser`) | 명세에 금지 규칙 없음, payments D-12 방식 |
| Q-4 | `pickup_code` 발급 시점·형식·고유 범위, 고객에게 보여 줄 위치 | 명세 §2·§4 확인 필요, README 확인 18번, db-schema 5절 5항 | 생성 때 발급, `A12345` 형식(대문자 1+숫자 5), 전역 고유 아님, 목록 항목과 픽업 응답에 `pickup_code`·`pickup_address` 추가 | payments D-18, 명세 예시 |
| Q-5 | 픽업 시간(`pickup_start`~`pickup_end`) 밖에서 픽업 처리 가능 여부 | 명세 §4 확인 필요 | **확정(2026-11-10, 사용자 결정)**: 불가. 픽업 시작·마감 포함, 밖이면 400 `PICKUP_OUTSIDE_WINDOW`. 마감 후 미수령 예약 처리는 미정 | 이전 임시값: 가능(`PICKUP_WINDOW_ENFORCED=False`, 삭제) |
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
| Q-17 | 취소 메서드를 명세대로 `PATCH`로 바꿀지 (D-26) | 사용자 명세 §3 vs reference·코드 `POST` | **확정(2026-11-05): `PATCH`로 통일**(`POST` 제거) | 명세가 정본(R15) |
| Q-18 | 내 목록 경로를 명세대로 `/v1/reservations/me`로 바꿀지 (D-27) | 사용자 명세 §2 vs reference·코드 `/v1/users/me/reservations` | **확정(2026-11-05): `/v1/reservations/me`로 변경** | 명세가 정본(R15) |
| Q-19 | 400(잘못된 수량)과 422(형식 오류)를 나눌지 (D-28, Q-14 재확인) | 사용자 명세 §1~3 | **확정(2026-11-05): 나누지 않고 전부 400 `VALIDATION_ERROR`** | 전역 핸들러·payments D-17·admin D26이 같은 처리(프로젝트 공통) |
| Q-20 | 내 목록에 페이지네이션을 둘지, 기본 크기가 20이어도 되는지 (D-29, Q-9 재확인) | 사용자 명세 §2(페이지네이션 없음) vs README 확인 5번(교안 요구) | **확정(2026-11-05): D-18 유지**(기본 20, 최대 100, 응답에 `page`·`size`·`total`). 명세에 페이지네이션 추가 필요(C-12) | 교안 목록 요구 |
| Q-21 | 500 응답 공통 핸들러를 누가 어떤 `error_code`로 추가할지 (C-10) | 사용자 명세 §1~3의 500, R7 | **확정(2026-11-05): `error_code="INTERNAL_SERVER_ERROR"`, 고정 메시지 "서버 오류가 발생했습니다.", 스택 비노출.** 핸들러 추가는 구현 단계에서 수정(C-10, 사용자 승인) | R7(모든 에러 응답이 공통 형식) |

---

## 11. 불변 규칙 점검 (설계 기준)

R1(domain은 `hmac` 등 표준 라이브러리만, `secrets`는 infrastructure에서 사용), R2(application은 포트·도메인만, infrastructure·presentation import 없음), R3(전이·소유·코드 검증은 엔티티), R4(`*Model` 미노출), R5(commit은 ApplicationService, 레포 `flush`), R6(도메인 예외, HTTPException 없음), R7(전역 핸들러), R8(생성자 필수·기본 생성 없음), R9(`provide_*` 2개 매핑), R10(포트 선언 메서드만 호출), R11(catalog·payments는 reservations 정의 포트로만, ORM·레포·서비스 내부 미사용), R12(5.2절의 한 방향 생성 그래프), R13(같은 세션, 호출되는 쪽 `commit=False`/commit 없음), R14(`schema.sql`과 동일, `price`는 매핑 제외 사유 명시), R15(명세 필드·URI, 추가·변경은 D-16·D-18·D-19·Q-14로 표시), R16(새 의존성·시크릿 없음).

---

## 12. 사용자 명세(2026-11-05) 3자 대조표 — 생성·내 목록·취소

비교 대상: **명세**(사용자 제공 원문, 이하 "명세") / **reference**(`docs/reference/reservations.md`) / **설계**(이 문서 기존 절) / **코드**(커밋 `66532ac`의 `src/reservations/**`, `src/error_handlers.py`). 명세와 reference의 필드·에러 표는 3개 EP 모두 문구까지 같습니다(차이는 12.1의 경로·메서드뿐). **아래 표의 "차이" 중 D-26~D-30과 Q-17~Q-21은 2026-11-05에 사용자가 확정했고, 코드 반영은 14절 작업 목록입니다(표 본문은 대조 당시 상태를 보존).** "실행"은 12.2절의 실험, "정독"은 코드를 읽은 결과입니다.

### 12.1 EP별 대조

**EP1 `POST /v1/reservations`**

| 항목 | 명세 | reference | 설계 | 코드 | 판정 |
| --- | --- | --- | --- | --- | --- |
| 경로·메서드 | `POST /v1/reservations` | 같음 | 같음(#22) | 같음(`router.py:29`) | 일치 |
| 헤더 | `Content-Type: application/json`, `Authorization: Bearer` | 같음 | `CurrentUser` | `CurrentUser`(`router.py:35`) | 일치 |
| 요청 필드 | `offer_id` UUID 필수, `quantity` int 필수 | 같음 | 같음(상한 없음, `ge=1`) | `schemas.py:7-9` 같음 | 일치 |
| 응답 필드 10개 | id, user_id, offer_id, quantity, unit_price, total_price, status, created_at, store_name, product_name | 같음 | D-2 같음 | `ReservationCreateResponse` 10개 같음(`schemas.py:12-24`) | 일치 (`created_at` 예시는 `+09:00`, 코드는 UTC로 만들므로 같은 시각의 다른 오프셋 표기. 정독, 영향 없음) |
| 성공 코드 | 201 | 201 | 201 | `status_code=201` | 일치 |
| 생성 직후 `status` | `PENDING_PAYMENT` | 같음 | `PENDING_PAYMENT`(1.2절) | `PickupReservation.create`가 `PENDING_PAYMENT` | 일치 |
| 400 | 잘못된 수량 | 같음 | 400 `VALIDATION_ERROR` | `ge=1`이 막아 400 `VALIDATION_ERROR`(실행: 0, -1 모두 `quantity: Input should be greater than or equal to 1`) | 일치. 단 형식 오류(422)와 구분되지 않음 → **D-28** |
| 401 | 로그인 필요 | 같음 | 같음 | 401 `UNAUTHORIZED` "로그인이 필요합니다." + `WWW-Authenticate: Bearer`(실행) | 일치. 단 **401이 400보다 먼저**(토큰 없이 `quantity:0` → 401, 실행) → D-9 문구 정정함 |
| 404 | 할인 상품 없음 | 같음 | 404 `NOT_FOUND` | `OfferNotFoundError`(`LookupError`) → 404 `NOT_FOUND` "할인 상품을 찾을 수 없습니다."(실행, fake 서비스) | 일치 |
| 409 재고 부족·예약 불가 | 409 | 같음 | 409 `OUT_OF_STOCK`/`OFFER_NOT_RESERVABLE` | 둘 다 `ReservationConflictError` 하위 → **409**(실행, 400 아님). 조건은 정독: 판매 중(`effective_status == ON_SALE`)이 아니면 `OFFER_NOT_RESERVABLE`, `quantity > remaining_stock`이면 `OUT_OF_STOCK`. **품절(`remaining_stock == 0`)은 `SOLD_OUT`이라 `OFFER_NOT_RESERVABLE`이 먼저** | 일치. 단 임시 포트(D-25)는 재고를 차감하지 않아 실서버에서는 동시 예약이 재고를 넘길 수 있음(B-6, DB 테스트 미실행 B-14) |
| 422 | 요청 형식 오류 | 같음 | 400으로 대체(1.6절, Q-14) | 400 `VALIDATION_ERROR`(실행: 문자열, 소수, 누락, 잘못된 UUID 모두 400) | **차이 → D-28** |
| 500 | 서버 오류 | 같음 | 언급 없음 | 평문 `Internal Server Error`(실행) | **차이 → C-10** |
| 스냅샷 저장 ("예약 당시 상품 정보 및 금액 정보") | 저장 | 저장 | `PickupReservation.create`가 단가·상점명·상품명·픽업 주소를 복사(1.3절) | `repositories.py:72-85`가 `unit_price`, `total_price`, `store_name`, `pickup_address`, `product_name`, `pickup_code`를 `pickup_reservations`에 저장. 응답의 `store_name`, `product_name`, `unit_price`는 **저장된 스냅샷에서** 나옴(오퍼를 다시 읽지 않음) | 일치 (아래 12.3) |

**EP2 `GET /v1/reservations/me`**

| 항목 | 명세 | reference | 설계 | 코드 | 판정 |
| --- | --- | --- | --- | --- | --- |
| 경로·메서드 | `GET /v1/reservations/me` | `GET /v1/users/me/reservations`("URI (제안)") | `/v1/users/me/reservations`(#23, 4.1절) | `router.py:40` `/users/me/reservations`. 실행: `GET /v1/reservations/me` → 404 | **차이 → D-27** |
| 요청 | 본문·쿼리 없음 | 쿼리 "노션에 없음", 확인 필요로 `status`·`page`·`size` 제안 | 쿼리 `status`, `page`, `size`(4.3절) | `status`(enum), `page>=1`, `size` 1~100(`router.py:44-54`) | **차이(확장) → D-18·D-29**. 잘못된 `status`·`page=0`은 400(실행) |
| 응답 래퍼 | `{"reservations": [...]}` | 같음 | + `page`, `size`, `total`(4.2절) | `ReservationListResponse`에 `page`, `size`, `total` 추가 | **차이(확장) → D-18·D-29** |
| 응답 항목 8필드 | id, offer_id, store_name, product_name, quantity, total_price, status, created_at | 같음 | + `pickup_code`, `pickup_address`(D-19) | `ReservationListItem`에 두 필드 추가(`schemas.py:38-40`) | 명세 8개는 일치. 확장 2개는 **D-19(기존)** |
| 정렬·범위 | 명세 없음(본인 것만) | 같음 | `created_at DESC, id DESC`, 본인만 | `find_by_user`가 `user_id`로 필터, 같은 정렬(`repositories.py:25-47`) | 일치(본인 것만 조회, 정독) |
| `status` 값 | 예시 `RESERVED`(생성 예시는 `PENDING_PAYMENT`) | 같음, 확인 필요 | 결제 전 `PENDING_PAYMENT`, 결제 후 `RESERVED`(D-1, Q-1 임시) | enum 4개 | 일치(두 예시는 결제 전·후 서로 다른 예약이라는 해석, Q-1 임시). 단 **실서버에서는 `RESERVED`가 생길 수 없음**(payments가 stub 예약 사용, B-16) |
| 200 | 200 | 200 | 200 | 기본 200 | 일치 |
| 401 | 로그인 필요 | 같음 | 같음 | 401 + `WWW-Authenticate`(실행) | 일치 |
| 422 | 형식 오류 | 같음 | 400 | 쿼리 오류는 400(실행) | **D-28** |
| 500 | 서버 오류 | 같음 | 없음 | 평문(실행) | **C-10** |

**EP3 `PATCH /v1/reservations/{id}/cancel`**

| 항목 | 명세 | reference | 설계 | 코드 | 판정 |
| --- | --- | --- | --- | --- | --- |
| 메서드 | `PATCH` | `POST` | `POST`(#24) | `@router.post`(`router.py:57`). 실행: `PATCH` → `405`, `Allow: POST` | **차이 → D-26** |
| 경로 | `/v1/reservations/{id}/cancel` | `/{reservation_id}/cancel` | 같음 | `/reservations/{reservation_id}/cancel` | 일치(경로 변수 이름만 다르며 외부에 영향 없음) |
| 요청 본문 | 없음 | 없음 | 없음 | 없음 | 일치 |
| 응답 3필드 | id, status, cancelled_at | 같음 | D-20 | `ReservationCancelResponse` 3개 | 일치 |
| 성공 코드 | 200 | 200 | 200 | 기본 200 | 일치 |
| 401 | 로그인 필요 | 같음 | 같음 | 401(실행) | 일치 |
| 403 | 본인 예약이 아님 | 같음 | D-21 403 | `NotReservationOwnerError`(`PermissionError`) → 403 `FORBIDDEN` "본인 예약만 취소할 수 있습니다."(실행) | 일치 (메시지 원문은 명세에 없음) |
| 404 | 예약 정보 없음 | 같음 | 404 | `ReservationNotFoundError` → 404 `NOT_FOUND` "예약 정보를 찾을 수 없습니다."(실행) | 일치 |
| 409 이미 취소·취소 불가 | 409 | 같음 | 409 `RESERVATION_ALREADY_CANCELLED`/`_PICKED_UP` | 둘 다 **409**(실행, 400 아님) | 일치 |
| 422 | 형식 오류 | 같음 | 400 | 잘못된 UUID 경로값 → 400 `path.reservation_id: Input should be a valid UUID...`(실행) | **D-28** |
| 500 | 서버 오류 | 같음 | 없음 | 평문(실행) | **C-10** |
| 확인 순서 | 404 → 403 → 409 | — | D-9 같음 | `service.py:62-74`: `get_snapshot`(404) → `ensure_owned_by`(403, 잠금 전) → `lifecycle.cancel`(상태 검사 409) | 일치 |
| 취소 가능 상태 | "이미 취소되었거나 취소 불가 상태"만 409 | 같음 | `PENDING_PAYMENT`·`RESERVED` → `CANCELLED`, 시간 제한 없음(D-10) | `PickupReservation.cancel`이 `CANCELLED`·`PICKED_UP`만 거부(`pickup_reservation.py:141-158`) | 일치. 시한은 명세에 없어 Q-6 임시 유지 |
| 취소 시각 기록 | 기록 | 같음 | `cancelled_at = clock.now()` | 도메인 `cancel(now)`가 기록, 저장(`repositories.py:96-98`) | 일치 |
| 재고 복구 | reference 구현 참고에 있음(명세는 환불만 언급) | `stock_log` 양수 | `StockPort.release`(D-8) | 임시 포트는 아무것도 안 하고 `False`(`interim_stock_port.py:79-82`). **실서버에서는 복구되지 않음**(B-6, D-25) | 차이 아님(알려진 제한). C-1 머지 전까지 |
| 환불 연동·트랜잭션 | "결제·환불 도메인과 연동" | 확인 필요 | 취소가 자동 환불 호출(D-11), 한 번 commit | `service.py:80-84`: 취소(`commit=False`) → `was_paid`이면 `refunds.refund_for_cancelled_reservation` → **`session.commit()` 한 번**. 환불 실패 시 취소·재고 복구도 롤백(R13). 환불 포트는 임시 `NoPaymentRefund`(D-15)라 환불 없음 | 일치(트랜잭션 경계). 단 **환불 판정 경합 → D-30** |
| 권한 | 로그인 | 회원 | `CurrentUser` | `CurrentUser`. admin 구현 후 정지 고객은 403 | **C-13**(명세 외 에러 코드) |

### 12.2 실행 확인 기록 (2026-11-05)

`DATABASE_URL`, `JWT_SECRET_KEY` 등을 셸 환경변수로만 지정하고 `fastapi.testclient.TestClient(main.app, raise_server_exceptions=False)`에 `get_current_user`와 `provide_reservation_service`를 override(예외를 던지는 fake 서비스)해서 응답을 봤습니다. 저장소에는 아무 파일도 쓰지 않았습니다. **DB 없이 한 실험이라 서비스 내부 동작(재고, 잠금, SQL)은 이 표에 없습니다.**

| 요청 | 결과 |
| --- | --- |
| `POST /v1/reservations` `quantity` 0 / -1 / `"abc"` / 1.5 / 누락, `offer_id: "x"` | 모두 400 `VALIDATION_ERROR`, 메시지는 `필드: 오류` 형식(예 `quantity: Input should be greater than or equal to 1`) |
| 서비스가 `OutOfStockError` / `OfferNotReservableError` | 409 `OUT_OF_STOCK` / 409 `OFFER_NOT_RESERVABLE` (공통 형식) |
| 서비스가 `OfferNotFoundError` | 404 `NOT_FOUND` |
| 서비스가 `RuntimeError("boom")` (생성·취소·목록 모두) | **500, 본문 `Internal Server Error`(평문, 공통 형식 아님)** |
| `POST .../{id}/cancel`에서 `ReservationAlreadyCancelledError` / `ReservationAlreadyPickedUpError` | 409 `RESERVATION_ALREADY_CANCELLED` / `RESERVATION_ALREADY_PICKED_UP` |
| `NotReservationOwnerError` / `ReservationNotFoundError` | 403 `FORBIDDEN` / 404 `NOT_FOUND` |
| `PATCH .../{id}/cancel` | 405 `HTTP_ERROR` "Method Not Allowed", `Allow: POST` |
| `POST .../xyz/cancel` | 400 `VALIDATION_ERROR` `path.reservation_id: ...valid UUID...` |
| `GET /v1/reservations/me` | 404 `NOT_FOUND` "Not Found" |
| `GET /v1/users/me/reservations?status=RESERVED_X` / `?page=0` | 400 `VALIDATION_ERROR` |
| 토큰 없이 생성(`quantity:0`) / 취소 / 목록 | 모두 401 `UNAUTHORIZED` "로그인이 필요합니다.", 생성에서 `WWW-Authenticate: Bearer` 확인 |

**400과 422의 경계 정리**: 명세의 의도는 "수량 값이 잘못됨(0·음수 등) = 400, 타입·형식 오류(문자열, 누락, UUID 형식) = 422"로 읽힙니다. 현재 프로젝트에서는 두 경우가 같은 `RequestValidationError`이고 상태 코드는 모두 400입니다(`error_handlers.py:38-48`). 도메인의 `ValueError`(`_int`가 내는 "수량은 1개 이상이어야 합니다.")는 Pydantic이 먼저 막아 API로는 닿지 않는 방어선입니다. 임시 기본값은 전부 400이며(D-28) 둘을 나누려면 `RequestValidationError`를 `type`별로 갈라 422를 내야 하는데 이는 전역 핸들러 변경입니다.

### 12.3 스냅샷 출처와 스키마 대조

| 응답 필드 | 출처 | `pickup_reservations` 컬럼(`schema.sql:91-107`) | 판정 |
| --- | --- | --- | --- |
| `unit_price` | 예약 시점 `offer.sale_price`를 `create`가 복사 | `unit_price INTEGER` | 있음 |
| `total_price` | `unit_price * quantity` | `total_price INTEGER` | 있음 |
| `store_name`, `product_name` | 예약 시점 상점·상품 이름 복사 | `store_name VARCHAR(150)`, `product_name VARCHAR(200)` | 있음 |
| `pickup_address`(목록 확장) | 같음 | `pickup_address VARCHAR(500)` | 있음 |
| `pickup_code`(목록 확장) | 생성 때 발급 | `pickup_code VARCHAR(20)` | 있음 |
| `status`, `created_at`, `cancelled_at`, `quantity`, `user_id`, `offer_id` | 예약 자체 | 있음 | 있음 |

**결론: 3개 EP를 구현하는 데 스키마 변경은 필요 없습니다.** 기존 S-제안은 그대로 두며, 아래 한 가지만 다시 표시합니다. 스냅샷 컬럼과 `status`·가격이 NULL 허용이라(S-2) 값이 NULL인 행은 `_to_domain`의 도메인 검증에서 `ValueError`가 되고, 전역 핸들러가 이를 **400 `VALIDATION_ERROR`로 응답**합니다(데이터 이상이 클라이언트 오류처럼 보임, 정독). S-2(NOT NULL)를 적용하면 막을 수 있습니다. 예약 시점의 `pickup_start`·`pickup_end`는 저장하지 않고 취소 때 offer에서 다시 읽는데, 2.4절의 "예약 0건일 때만 할인 수정" 규칙(catalog CI-10)이 container 미연결(C-11)이라 아직 지켜지지 않습니다.

### 12.4 불일치 요약

| EP | 불일치 개수 | ID |
| --- | --- | --- |
| 1 생성 | 2 (422, 500) | D-28, C-10 |
| 2 내 목록 | 6행 (경로, 쿼리 확장, 응답 래퍼 확장, 항목 확장, 422, 500). 확장 3행은 기존 결정 D-18·D-19에 속하고 새 결정은 D-29 | D-27, D-18·D-19·D-29, D-28, C-10 |
| 3 취소 | 5 (메서드, 422, 500, 환불 판정 경합, 정지 고객 403) | D-26, D-28, C-10, D-30, C-13 |
| 공통(코드 정합) | 1 (container 미교체) | C-11 |

---

## 13. admin 설계와의 정합 (`docs/design/admin.md`는 수정하지 않음)

admin.md는 reservations가 비어 있다는 전제(B-6 `NoReservationAdmin`, C10)로 쓰였습니다. 아래는 **reservations 쪽이 받아야 할 요구**의 기록이며 구현은 하지 않았습니다(C-14). admin.md의 사용자 확정(2026-11-04)은 **D2, D4, D10, D12, D13, D35, D39**이고 나머지 admin 결정은 임시입니다. 여기서는 확정 항목을 인용만 하고 바꾸지 않습니다.

| # | admin 쪽 요구 (출처) | reservations 현황 | 받아야 할 일 (제안) |
| --- | --- | --- | --- |
| A-1 | `ReservationAdminPort.cancel_reserved_for_user`: 회원의 **RESERVED만** 취소, 재고 복구(`stock_log` 양수), **전액 환불·사용 포인트 복구**(`waive_penalty=True`), commit 금지·같은 세션·취소 수 반환·중복 호출 멱등 (admin C10, **D12 확정**) | 없음. `cancel_all_for_offer`는 offer 단위이고 **재고를 복구하지 않음**(D40) | `ReservationRepository.find_by_user_and_status(user_id, status, for_update)`(`ORDER BY offer_id, id`)와 Lifecycle 메서드를 추가. 재고는 `stock.release`가 닫힌 할인이면 알아서 복구하지 않으므로(D-8) 일괄 취소와 달리 호출함. 환불은 `refund_for_cancelled_reservation(..., waive_penalty=True)`. 어댑터는 reservations 소유(`catalog_adapters.py`와 같은 방식). **`PENDING_PAYMENT`는 D12대로 대상이 아님** |
| A-2 | `has_reserved_for_store`: 매장의 모든 할인에 걸친 RESERVED가 하나라도 있으면 True, RESERVED 행을 `FOR UPDATE`로 읽음 (admin EP 6, C10, **D13 확정**: 있으면 400 `STORE_HAS_RESERVED_RESERVATIONS`로 전체 롤백) | 없음. `pickup_reservations`에 `store_id`가 없어 매장 단위 조회 불가(C-8) | S-4(`store_id` 스냅샷 컬럼) 또는 catalog가 `offer_ids_by_store` 포트를 제공. 어느 쪽이든 R11 때문에 reservations가 catalog·stores 테이블을 조인하지 않음. **S-4의 필요성이 높아졌음** |
| A-3 | 잠금 순서 D34 `stores → products → discount_offers → pickup_reservations → payments → users`, `id` 오름차순 (admin 4.3, 임시) | D-6 `product → offer → reservation → payment → refund → user` | **양립함**(admin 순서는 D-6 앞에 `stores`를 붙이고 `refund`를 payments 안에 포함). 새 요구는 **한 사용자의 여러 예약**(A-1)을 offer 하나씩 `offer → reservation` 순서로, offer id 오름차순으로 잠그는 것. 고객 취소는 offer 하나뿐이라 교착 없음 |
| A-4 | 정지된 OWNER도 자기 상점의 기존 `RESERVED` 예약 **픽업은 가능**, 로그인도 허용 (**D35·D39 사용자 확정**, admin 5.5) | 픽업 라우터가 `OwnerUser`를 씀(`router.py:72`). admin 구현 후에는 정지된 OWNER가 403 | **픽업 EP(#25)의 의존성을 admin의 `SuspendedAllowedOwnerUser`로 바꿔야 함.** 이번 명세 범위 밖이라 4.1절 #25 행·D-4는 **바꾸지 않았음**. 생성·목록·취소는 `CurrentUser` 유지(정지된 고객 차단, admin D8·5.5절) |
| A-5 | 강제 탈퇴된 고객은 `WITHDRAWN`이라 취소도 401, 정지된 고객은 403 (admin D8·D9, 임시) | 결제하지 않은 `PENDING_PAYMENT` 예약은 D12가 취소 대상에서 제외 → **정지·탈퇴 고객의 `PENDING_PAYMENT` 예약이 재고를 영구 점유**(admin D12 위험 문구, Q-2) | Q-2(결제 제한 시간) 답이 필요. 임시 기본값은 그대로 두고 위험만 유지 |
| A-6 | `create_reservation_admin()`이 `NoReservationAdmin`을 돌려주는지 단언(admin 테스트 계획) | 해당 팩토리는 admin 구현 때 생김 | reservations 어댑터를 연결하면서 그 단언을 같은 PR에서 교체. 지금은 `src/admin/**`가 없어 할 일 없음(B-16) |

설계 충돌 없음: admin의 요구는 reservations의 전이표(1.2절)와 잠금 순서를 바꾸지 않습니다. 단 A-1은 **새 레포지토리 메서드 1개와 Lifecycle 메서드 1개**, A-2는 **스키마(S-4) 또는 catalog 포트**가 필요합니다.

---

## 14. 구현자 작업 목록 (2026-11-05 확정 반영, `layer-implementer` 발주용)

**근거 결정**: D-26, D-27, D-28(변경 없음), D-29(변경 없음), D-30, Q-21, C-10·C-11(구현 시 수정, 사용자 승인 2026-11-05). R1~R16 준수. 이 절에 없는 항목(C-13, A-1~A-6, S-4 스키마 변경, Q-2, 픽업 EP #25와 `SuspendedAllowedOwnerUser`)은 **이번 구현에서 하지 않습니다**(S-4는 미승인 유지).

| # | 작업 | 위치 | 확인 방법 |
| --- | --- | --- | --- |
| W-1 | 취소를 `@router.patch("/reservations/{reservation_id}/cancel")`로 변경, `POST` 제거 (D-26) | `src/reservations/presentation/router.py` | `PATCH`가 200, `POST`가 405 |
| W-2 | 내 목록 경로를 `/reservations/me`로 변경, 이전 `/users/me/reservations` 제거. 쿼리·응답은 그대로(D-18, D-29) (D-27) | 같음 | `GET /v1/reservations/me` 200, 이전 경로 404 |
| W-3 | 경로·메서드 단언 갱신(6절 첫 항목), 목록 호출 경로 교체 | `tests/reservations/test_wiring.py`, `test_api_db.py` | 갱신 후 통과 |
| W-4 | 400 유지(D-28): 코드 변경 없음. 422를 쓰지 않는 것을 테스트로 고정(수량 0·문자열·잘못된 UUID가 400) | `tests/reservations/` | 단언 추가 |
| W-5 | **D-30**: `ReservationLifecycleService.cancel`이 잠금 안에서 취소 직전 상태로 `RefundTarget`을 만들어(`CancelledReservation`과 같은 방식) 반환하고, `ReservationApplicationService.cancel_reservation`은 잠금 전 `was_paid` 대신 그 값으로만 `refund_for_cancelled_reservation` 호출 여부를 정함. 소유 확인(403)은 계속 잠금 전. 전이표·응답은 불변 | `lifecycle_service.py:60-79`, `service.py:59-85`, `views.py` | fake 테스트: 스냅샷 시점 `PENDING_PAYMENT`, 잠금 시점 `RESERVED`로 바뀌는 경합을 재현하면 환불이 호출됨. 반대로 취소 직전 `PENDING_PAYMENT`면 호출되지 않음. `commits == 1` 유지 |
| W-6 | **C-10 / Q-21**: `@app.exception_handler(Exception)` 추가. 응답 500 `{"success": false, "error_code": "INTERNAL_SERVER_ERROR", "message": "서버 오류가 발생했습니다."}`, 예외 내용·스택은 응답에 넣지 않고 서버 로그에만 기록. 기존 `ValueError`·`LookupError`·`PermissionError`·409·401 핸들러 응답이 바뀌지 않아야 함 | `src/error_handlers.py` | `RuntimeError`가 500 + 위 본문(`raise_server_exceptions=False`), 기존 응답 불변 |
| W-7 | **C-11 (catalog 포트)**: `create_reservation_lookup`·`create_reservation_cancel`을 5.1절대로 `OfferReservationLookup`·`OfferReservationCanceller`로 교체, 싱글턴 `_reservation_lookup`·`_reservation_cancel`과 `NoReservation*` import 제거. `tests/catalog/test_wiring.py`의 `NoReservation*` 단언을 새 어댑터 단언으로 교체(깨지는 단언이라 이 승인 범위). 필요하면 미사용이 된 `catalog/infrastructure/reservation_lookup.py`·`reservation_cancel.py` 삭제는 catalog 담당 확인 후(삭제는 이 승인에 포함되지 않음, 보고만) | `src/container.py`, `tests/catalog/test_wiring.py` | `(cd src && uv run python -c "import main")` 성공(생성 순환 없음, R12), `tests/reservations/test_wiring.py`가 새 어댑터 단언 |
| W-8 | **C-11 (payments `InMemoryReservationPort` 교체)**: payments C-3·C-4를 따름. `ReservationAdapter(lifecycle)`로 `get`·`mark_paid`·`cancel_for_refund` 구현, `get_payment_service`의 `InMemoryReservationPort()` 제거, container 구역에 payments 서비스 팩토리 추가, reservations `create_refund_port`를 payments 서비스 기반 어댑터(`RefundTarget` → 스냅샷 변환, 상태 `RESERVED`)로 교체하고 `NoPaymentRefund` 삭제, `reservation_stub.py` 삭제. **W-5를 먼저 끝낼 것**(결제와 취소의 환불 경합) | `src/payments/**`, `src/container.py`, `src/reservations/infrastructure/payment_refund_stub.py`(삭제), `tests/payments/**`, `tests/reservations/test_wiring.py` | 결제 → `RESERVED` → 취소 → 환불 통합 흐름 테스트, `tests/reservations/test_wiring.py`의 `NoPaymentRefund` 단언 교체(7.1절이 예고한 대로). 이 작업은 payments 모듈을 건드리므로 보고서에 범위 확장으로 표시 |

**쓰기 범위(이 작업 목록 한정)**: 7절 허용 범위 + `src/error_handlers.py`(W-6) + `src/container.py`(W-7·W-8) + `tests/catalog/test_wiring.py`(W-7) + `src/payments/**`·`tests/payments/**`(W-8, 사용자 승인 2026-11-05). `docs/reference/`(C-12)와 `docs/design/admin.md`는 수정하지 않습니다.

**완료 게이트(R16, `backend-invariants` §7)**: `uv run python .claude/skills/layer-check/check_layers.py`(`python3`가 없는 환경에서는 이 형태. 기준선 2건은 W-8에서 payments가 `infrastructure`를 직접 import하는 부분을 함께 고치면 0건이 될 수 있음), `(cd src && uv run python -c "import main")`, `uv run python -m pytest -rs`(이 환경은 `uv run pytest`가 Application Control로 차단됨, B-14). DB 테스트 skip은 통과가 아님: DB가 없으면 "미실행"으로 보고합니다.

---

## 통합 기록 (2026-11-05)

이 절은 **새로 추가한 절**입니다. 기존 절(1~11)은 고치지 않았습니다. 두 갈래의 번호를 **섞지 않고 병행**합니다.

- **D-/C-/Q-/S-**: 이 문서(main, PR #15)의 번호.
- **RD-/RC-**: 원래 브랜치 `feature/reservations`(커밋 b7eae41)의 `docs/design/reservations.md`에서 온 번호. 이 브랜치(`integrate/reservations-on-main`)에는 그 문서가 없고, 이 절이 요약만 옮깁니다.
- 충돌하는 경우 이 절의 "사용자 확정"이 해당 D-번호의 본문(7.1절, 8절)을 **덮어씁니다**. 코드·DB·git은 바꾸지 않았습니다.

### 통합.1 사용자 확정으로 대체된 main 결정

| main 결정 | 대체 | 확정 내용 | 이유 |
| --- | --- | --- | --- |
| D-15 (임시 `NoPaymentRefund`가 환불 없이 통과) | **RD-26** | **fail-closed**. 결제된(`RESERVED`였던) 예약의 취소는 **503 `REFUND_NOT_CONNECTED`** | 돈이 나가야 하는데 오류 없이 넘어가는 사고를 막기 위해 |
| D-25 (읽기 전용 임시 재고 포트로 예약 생성 통과) | **RD-25** | 재고 미연동 시 **예약 생성 503 `STOCK_NOT_CONNECTED`**. 할인 없음 404, 판매 불가·재고 부족 409 검사는 먼저 하고 통과하면 503 | 가짜 성공·초과 판매를 막기 위해. 임시 기간에 예약이 생기지 않으므로, 실제 재고 연동 후 `release`할 때 재고 초과 오류 위험이 없음 |

- **503 변환 위치(사용자 결정)**: 예약 라우터(`presentation/router.py`)에서 변환. `src/error_handlers.py`는 수정하지 않음. 공통 에러 형식 `{"success": false, "error_code", "message"}`는 유지(R7). R6·R7 예외이며 임시(연동 후 제거, 코드에 TODO 표시).
- **409**: main 공용 핸들러 사용(`src/error_handlers.py`의 `ReservationConflictError` 핸들러, D-16·C-6). 원래 RD-29(router 변환)는 채택하지 않음.
- **수량**: `ReservationCreateRequest.quantity`는 `StrictInt` + `Field(ge=1)`. `true`·`1.5`·문자열은 400 `VALIDATION_ERROR`.

현재 코드 위치(작업 폴더 `src/reservations/` 기준, 커밋 전 작업 트리 변경)

| 대상 | 파일:심볼 |
| --- | --- |
| 재고 임시 포트, 503 | `application/interim_stock_port.py`: `reserve`(검사 통과 후 `StockNotConnectedError`) |
| 환불 임시 포트, 503 | `infrastructure/payment_refund_stub.py`: `NoPaymentRefund.refund_for_cancelled_reservation`(`RefundNotConnectedError`) |
| 예외 | `domain/exceptions.py`: `ReservationConflictError`(1행, 409 기반), `IntegrationNotReadyError`(99행, `Exception` 상속이라 400·403·404·409로 잡히지 않음), `StockNotConnectedError`(113행), `RefundNotConnectedError`(122행) |
| 503 변환 | `presentation/router.py`: `_not_ready_response`, `create_reservation`·`cancel_reservation`의 `except IntegrationNotReadyError` |
| 수량 검증 | `presentation/schemas.py`: `ReservationCreateRequest.quantity` (`StrictInt`) |

### 통합.2 번호 대응표 (병행)

| 원래(RD) | main(D/C/S) | 내용 | 채택 |
| --- | --- | --- | --- |
| RD-2 | D-11 | 결제한 예약 취소 시 환불 자동 호출, 환불 API도 `cancel_for_refund`로 예약 취소·재고 복구까지(RD-2 확정 = A안) | 같은 방향, 병합 |
| RD-25 | D-25 | 임시 재고 포트 | **RD-25**(503), D-25 대체 |
| RD-26 | D-15 | 임시 환불 포트 | **RD-26**(fail-closed 503), D-15 대체 |
| RD-29 | D-16 / C-6 | 409 변환 방식 | **main 공용 409 핸들러**, RD-29 미채택 |
| RD-8 | D-13 | `pickup_code` 형식 | main(통합.3) |
| RD-14 | D-19 | 목록·응답에 `pickup_code` 포함 | main(통합.3) |
| RD-30 | S-3 | `price` 매핑 | main S-3 |

원래 문서의 그 밖의 **확정** 결정(main에 같은 번호 없음, 요약)

| 번호 | 확정 내용 | 원래 문서 위치 |
| --- | --- | --- |
| RD-3 | 위약금은 결제 모듈이 계산, 금액은 당분간 0원. reservations는 `pickup_start`·`cancellable_until`만 제공 | 13.6.1 |
| RD-5 | 전역 잠금 순서 상품 → 할인 → 예약 → 결제 → 환불 → 회원(건너뛰기 허용, 역방향 금지), 순서 회귀 테스트 필수 | 13.6.1 (7.2절) |
| RD-32 | 개발 DB는 서버 재시작 + 수동 `ALTER`, 재생성·alembic 안 함, 실행은 사용자 | 13.6.1 |
| RD-33 | `payments.reservation_id` FK는 가짜 예약 스텁 제거와 같은 작업에서 모델 FK + `ALTER` | 13.6.1 |
| RD-34 | 모듈 경계 예외는 어댑터가 번역, 공용 `error_handlers.py` 수정 안 함 | 13.6.1 |
| RD-35 | 직전 `RESERVED`인데 결제 없음·이미 환불 등 불일치는 통과가 아니라 드러냄(기본값과 다르게 확정) | 13.6.2~13.6.5 |
| RD-36 | `OfferPort`의 `get_snapshot`·`reserve`·`release`를 한 번에 교체, 부분 교체 금지 | 13.6.1 |
| RD-37 | DB 테스트·개발 DB 변경은 승인 절차 | 13.4.5 |
| RD-38 | 불일치 시 500 `DATA_INCONSISTENT` + ERROR 로그 + 전부 롤백 | 13.7 |
| RD-39 | `PENDING_PAYMENT` 취소 시 `PAID` 결제가 남아 있으면 같은 방식으로 막음 | 13.8 |
| RD-40 | `PENDING_PAYMENT` + 결제 `REFUNDED`도 불일치로 볼지: **미정**(임시 기본값: 막지 않음) | 13.8 마지막 표 |

- 위 위치는 원래 브랜치 `feature/reservations`의 커밋 `b7eae41`의 `docs/design/reservations.md` 13.6~13.8절입니다. 결제 쪽 정본은 `payments.md` 10.7~10.9절이며, **이 브랜치의 `docs/design/payments.md`에 10.7(결정 확정 기록), 10.8(D-29), 10.9(RD-39)가 이미 있습니다**(결제 2차 merge, `809976b`, 열람으로 확인).
- RD-35·RD-38·RD-39의 구현(500 `DATA_INCONSISTENT`)은 이 통합에서 다루지 않았습니다. main 코드에 해당 변환이 있는지는 **확인 필요**.

### 통합.3 남은 미정 (사용자 지시로 main 쪽을 기본값으로 둠)

| 항목 | main | 원래 | 현재 기본값 |
| --- | --- | --- | --- |
| 픽업 코드 형식 | D-13 | RD-8 | main 형식 |
| 목록의 `pickup_code` 포함 | D-19 | RD-14 | main(포함) |
| `PICKED_UP` 취소 에러 코드 | main의 예외·`error_code` | 원래 `ReservationNotCancellableError` 등 | main 사용 |
| `price` 매핑 | S-3 | RD-30 | main S-3 |

모두 확정이 아니라 **임시 기본값**입니다. 바꿀 때는 해당 상수·예외 한곳에서 바꿉니다.

### 통합.4 정합 이슈 (신규)

| # | 이슈 | 근거 | 제안 |
| --- | --- | --- | --- |
| C-통합-1 | **취소 흐름의 순서**: main `cancel_reservation`은 `lifecycle.cancel(commit=False)` 안에서 `stock.release`가 `refund_for_cancelled_reservation`보다 **먼저** 호출됨 | `application/lifecycle_service.py:60-78`(`cancel`, `release` 73행), `application/service.py:59-84`(환불 81행, commit 84행) | 같은 트랜잭션이라 환불 단계에서 예외가 나면 롤백되므로 지금은 안전함(RD-26의 503도 `commit` 전). 실제 재고 연동 시 `release`가 외부 효과를 내면 순서를 재검토하고, 환불을 먼저 하는 순서(원래 RD-2: 환불 먼저·재고 복구 나중)와 맞출지 결정 필요 |

---

## 15. 회원 탈퇴 연동: 회원별 일괄 취소, 매장별 픽업 대기 확인, 정지 상점주 픽업 (2026-11-05 추가)

이 절은 **새로 추가한 절**이다. 1~14절은 고치지 않았다. 설계만 있고 코드는 바꾸지 않았다. 번호는 D-31부터, C-15부터, Q-A1부터 쓴다.

- 근거(확정): `docs/requirements/auth.md` REQ-34 ①②③, REQ-34-1, REQ-36, B-2, B-3. 사용자 결정(2026-11-05): 요구조건이 admin.md D12(RESERVED만)보다 우선. 팀원 동의(태환 님·유민 님) 받음. admin.md D13·D35·D39는 유지.
- 13절 A-1(RESERVED만)·A-2(S-4 필요)·A-4는 이 절이 **대체**한다(A-1은 D-31, A-2는 D-34, A-4는 D-38).
- 실행 확인: `Read`로 `src/reservations/**`, `src/payments/application/service.py`, `src/container.py`, `src/admin/application/{ports,service}.py`, `src/stores/application/{ports,service}.py`, `src/auth/presentation/dependencies.py`, `src/auth/application/service.py`. `grep restore_points|revoke_points|use_points src/payments src/reservations` 결과 **0건**(payments 코드는 포인트를 아직 쓰지 않음, `service.py:56` TODO). 이 절은 DB·서버를 실행하지 않았다.

### 15.1 현재 코드에서 확인한 사실

| # | 사실 | 위치 | 영향 |
| --- | --- | --- | --- |
| F-1 | 위약금 면제 경로가 **이미 있다**: `RefundPort.refund_for_cancelled_reservation(target, reason=, waive_penalty=True)` → `PaymentApplicationService.refund_for_cancelled_reservation(..., waive_penalty)`가 `penalty = 0 if waive_penalty`. commit 없음 | `reservations/application/ports.py`, `adapters.py:PaymentRefundAdapter`, `payments/application/service.py` | payments 위약금 코드 변경 없음 |
| F-2 | 포인트 복구·회수는 **payments 코드에 없다**. `pay()`에 `use_point`가 없고 `refund_for_cancelled_reservation`에 `restore_points`/`revoke_points` 호출이 없다. 지금은 사용·적립된 포인트 자체가 없어서 복구할 것도 없다 | `payments/application/service.py:56`(TODO D-10), grep 0건 | C-16 |
| F-3 | `cancel_all_for_offer`는 재고를 복구하지 않고(D40) PICKED_UP이 있으면 전체 중단한다. 회원 일괄 취소는 **재고를 복구**하고 PICKED_UP·CANCELLED는 **건너뛴다**. 같은 코드를 재사용할 수 없고 새 메서드가 필요하다 | `lifecycle_service.py:cancel_all_for_offer` | D-31 |
| F-4 | `ReservationAdminPort.cancel_reserved_for_user`는 이름이 "RESERVED만"이고 `has_reserved_for_store`는 RESERVED 전용 | `admin/application/ports.py:153` | D-32 |
| F-5 | `pickup_reservations`에 `store_id`가 없다(S-4 미승인). `offer_id`에 인덱스가 있다. catalog 추상 레포지토리에는 "상점의 할인 ID 목록"이 없다(`find_by_store`는 `(offer, product)`를 페이지로, `exists_open_by_store`는 진행 중만) | `reservations/infrastructure/models.py:25`, `catalog/domain/repository/discount_offer_repository.py` | D-34, C-15 |
| F-6 | container: `_pickup_pending = NoPickupPendingReservations()`(항상 False), `_reservation_admin = NoReservationAdmin()` | `src/container.py:101,105` | D-36 |
| F-7 | 픽업 EP는 `OwnerUser`. `SuspendedAllowedOwnerUser`는 정의만 되어 있고 어디에도 연결되지 않음 | `reservations/presentation/router.py:72`, `auth/presentation/dependencies.py:98` | D-38 |
| F-8 | 환불 후 포인트 복구는 payments가 회원 행을 잠그므로 **잠금 순서의 마지막(user)**이다. `withdraw_user`도 회원 행을 잠그지만 같은 트랜잭션이라 문제없음 | auth `_locked_user` | 15.5 |

### 15.2 도메인 (`domain/`)

- 엔티티·상태 전이표 **변경 없음**. 일괄 취소는 기존 `PickupReservation.cancel(now)`만 쓴다(PENDING_PAYMENT, RESERVED → CANCELLED). PICKED_UP·CANCELLED는 `holds_stock`이 False라서 서비스가 건너뛴다(예외를 내지 않음).
- `rules.py`에 상수 1개 추가(바뀔 수 있는 값은 한곳): `WITHDRAWAL_CANCEL_REASON = "회원 탈퇴"`(Q-A6). 호출자가 사유를 넘기면(admin 강제 탈퇴 사유) 그 값을 쓴다.
- `repository.py`(추상)에 메서드 2개 추가:
  - `find_by_user_and_statuses(user_id, statuses: Sequence[ReservationStatus], *, for_update=False) -> list[PickupReservation]` — `ORDER BY offer_id, id`(교착 방지, D34).
  - `exists_by_offers_and_status(offer_ids: Sequence[uuid.UUID], status: ReservationStatus) -> bool` — 빈 목록이면 쿼리 없이 False.
- 새 예외 없음. 불일치는 기존 `DataInconsistentError`(500).

### 15.3 인프라 (`infrastructure/`)

- 스키마 변경 **없음**(S-4 기각 유지, D-34).
- `SqlAlchemyReservationRepository`:
  - `find_by_user_and_statuses`: `WHERE user_id = :u AND status IN (...) ORDER BY offer_id, id`, `for_update`면 `.with_for_update().execution_options(populate_existing=True)`(기존 `find_by_offer`와 같은 방식). `user_id` 인덱스 있음.
  - `exists_by_offers_and_status`: `SELECT id ... WHERE offer_id = ANY(:ids) AND status = :s LIMIT 1`. `offer_id` 인덱스 사용. 행 잠금은 하지 않는다(D-35 이유).
- catalog 쪽 변경(C-15): `DiscountOfferRepository.find_ids_by_store(store_id, *, for_update=False) -> list[uuid.UUID]` 추상 + SQLAlchemy 구현. `SELECT d.id FROM discount_offers d JOIN products p ON p.id = d.product_id WHERE p.store_id = :s ORDER BY d.id`, `for_update`면 `FOR UPDATE OF d`. `products.store_id`·`discount_offers.product_id` 인덱스를 쓴다. 도메인 객체를 반환하지 않고 ID만 돌려주는 조회라 R4와 충돌하지 않는다(ID는 값).
- 동시성: 새 쿼리가 쓰는 잠금은 전부 `offer 행(id 오름차순) → reservation 행(offer_id, id 오름차순)`이다. 기존 취소·`pay`·예약 생성이 모두 offer를 먼저 잠그므로 같은 순서다(D-6).

### 15.4 응용 (`application/`)

#### 15.4.1 포트 (reservations가 정의, R11)

`application/ports.py`에 추가:

```python
class StoreOffersPort(Protocol):
    """매장의 할인 ID 목록. catalog 추상 레포지토리를 쓰는 어댑터가 만족한다. commit 없음 (R13)."""
    async def list_offer_ids_of_store(self, store_id: uuid.UUID, *, for_update: bool = False) -> list[uuid.UUID]: ...
```

#### 15.4.2 `ReservationLifecycleService.cancel_all_for_user(user_id, *, reason) -> list[CancelledReservation]` (commit 없음)

1. `peek = reservations.find_by_user_and_statuses(user_id, [PENDING_PAYMENT, RESERVED])`(무잠금). 비면 `[]`.
2. 서로 다른 `offer_id`를 **오름차순**으로 `stock.get_terms(offer_id, for_update=True)`(offer 잠금 먼저, D-6). 같은 offer는 한 번만. `terms`는 환불용 `pickup_start`를 얻는 데 쓴다(`dict[offer_id, terms]`).
3. offer를 다 잠근 뒤 `reservations.find_by_user_and_statuses(user_id, [...], for_update=True)`로 **다시 읽는다**(정본 목록. 그 사이 고객이 직접 취소·결제한 것을 반영, 멱등).
4. 각 예약마다(`offer_id, id` 순):
   - `holds_stock`이 False면 건너뛴다(방어).
   - `check_paid_payment = reservation.is_pending_payment`, `RefundTarget`은 `is_paid`일 때만 **취소 직전 상태**(`status="RESERVED"`)로 만든다(`cancel_all_for_offer`와 같은 방식).
   - `reservation.cancel(now)` → `_release_stock(reservation, user_id=reservation.user_id, reason=reason)`(**재고 복구**, 닫힌 할인이면 포트가 False를 주는 정상 경로 D40) → `reservations.save`.
5. `CancelledReservation` 목록 반환. PICKED_UP·CANCELLED는 조회 조건에서 빠지므로 **기록은 그대로 남는다**(REQ-34 ③). `PickedUpReservationExistsError`는 내지 않는다.

`_release_stock`이 `DataInconsistentError`(상한 초과)를 내면 그대로 올린다. 호출한 응용 서비스가 처리한다(아래).

#### 15.4.3 `ReservationApplicationService.cancel_all_for_user(user_id, *, reason) -> int` (**commit 하지 않음**, R13)

`cancel_all_for_offer`와 같은 모양이다.

1. `cancelled = lifecycle.cancel_all_for_user(...)`. `DataInconsistentError`(재고 복구 불일치)가 나면 `session.rollback()`, `_log_inconsistency("cancel_all_for_user", error.details)`(요청당 ERROR 로그 1건), 다시 raise.
2. 각 항목: `refund_target`이 있으면 `refunds.refund_for_cancelled_reservation(target, reason=reason, waive_penalty=True)`(**전액 환불, F-1**). `refund_target`이 없고 `check_paid_payment`면 `refunds.ensure_no_paid_payment(id)`(RD-39).
3. 환불·확인에서 나온 `DataInconsistentError`는 끝까지 모아 1건이라도 있으면 `rollback()` + 로그 1건 + `DataInconsistentError(모은 목록)` raise(RD-38). 정상이면 `len(cancelled)` 반환(PENDING_PAYMENT와 RESERVED 취소 수의 합).
4. 환불에 따른 **포인트 복구·회수**는 `refund_for_cancelled_reservation` 안에서 payments가 한다(C-16). reservations는 포인트를 모른다.

#### 15.4.4 `StoreReservationQuery` (신규, `application/store_query.py`)

생성자: `reservations: ReservationRepository`, `store_offers: StoreOffersPort`. 서비스가 아니라 읽기 전용 질의 객체다(commit 없음).

```python
async def has_reserved_for_store(self, store_id, *, excluding_user_id: uuid.UUID | None = None) -> bool:
    ids = await self.store_offers.list_offer_ids_of_store(store_id, for_update=True)  # offer 잠금(id 오름차순)
    return await self.reservations.exists_by_offers_and_status(ids, ReservationStatus.RESERVED, excluding_user_id=excluding_user_id)

async def has_pickup_pending_for_store(self, store_id) -> bool:  # stores PickupPendingPort
    return await self.has_reserved_for_store(store_id)
```

(`exists_by_offers_and_status`에 `excluding_user_id: uuid.UUID | None = None` 선택 인자를 둔다. 위 15.2절 시그니처에 포함해서 구현한다. 값이 있으면 `AND user_id != :u`.)

- 이 객체 하나가 stores `PickupPendingPort`와 admin 포트의 매장 확인을 **구조적으로 만족**한다(R11, 서로의 모듈을 import하지 않음).
- **offer 행을 잠그는 이유**: `pay`·고객 취소·예약 생성은 모두 offer를 먼저 잠그므로, 확인 뒤 폐점이 끝나기 전까지 RESERVED가 새로 생기거나 사라지지 못한다. 예약 행은 잠그지 않는다(픽업은 RESERVED를 줄이기만 해서 안전). admin.md의 "RESERVED 행을 FOR UPDATE"와 다르다(D-35).
- 비용: 쿼리 2회(할인 ID 조회 + 예약 존재 조회). 할인이 아주 많은 매장이면 `ANY(ids)` 목록이 커진다. 지금 규모에서는 문제가 없고, 느려지면 S-4(`store_id` 스냅샷 컬럼)로 한 번의 인덱스 조회로 바꾼다(포트 시그니처 불변이라 어댑터만 교체).

#### 15.4.5 어댑터 (reservations 소유, 구조적 포트 만족)

- `application/store_adapters.py`: `CatalogStoreOffersAdapter(offers: DiscountOfferRepository)`가 `StoreOffersPort`를 만족. catalog **추상 레포지토리**만 쓴다(R11 §3.4 1행). catalog 서비스는 받지 않는다(R12).
- `application/admin_adapters.py`: `ReservationAdminAdapter(service: ReservationApplicationService, query: StoreReservationQuery)`가 admin 새 포트(D-32)를 만족.
  - `cancel_active_for_user(user_id, *, reason) -> int` → `service.cancel_all_for_user(user_id, reason=reason)`
  - **관리자 강제 탈퇴 전용 `AdminWithdrawalReservationAdapter`(하위 클래스, 2026-11-10 사용자 결정)**: `cancel_active_for_user`는 넘어온 관리자 사유를 쓰지 않고 `rules.ADMIN_WITHDRAWAL_CANCEL_REASON`("관리자 강제 탈퇴")으로 `service.cancel_all_for_user`를 부른다. 관리자 원문 사유(최대 500자)는 탈퇴 기록(`users.deleted_reason`)과 강제 폐점 사유에만 남고, 200자 제한이 있는 환불 사유에는 고정 문구가 들어간다(201~500자 사유로도 탈퇴·전액 환불 가능). container는 `create_admin_service`에만 이 어댑터(`create_reservation_admin_for_admin`)를 주입하고, 본인 탈퇴(auth)는 기존 어댑터와 `SELF_WITHDRAWAL_REASON`을 그대로 쓴다. 재고 복구 기록 사유는 원래 catalog 고정 문구("예약 취소 복구")라 영향 없음.
  - `has_reserved_for_store(store_id, *, excluding_user_id=None) -> bool` → `query.has_reserved_for_store(...)`
  - `DataInconsistentError`는 admin이 정의한 `ReservationDataInconsistentError`로 **번역만** 한다(로그 없음. 서비스가 이미 1건 기록, `catalog_adapters.OfferReservationCanceller`와 같은 방식, C-17).

#### 15.4.6 탈퇴 흐름과 트랜잭션 경계 (R5, R13)

한 요청 세션(`Depends(get_db)`), **마지막에 `commit()` 한 번**은 흐름을 시작한 서비스(admin 또는 자진 탈퇴 서비스)가 한다. 호출되는 쪽은 전부 commit하지 않는다.

| 순서 | 호출 | 잠그는 것 (D34 / D-6) |
| --- | --- | --- |
| ① | `accounts.get_account`, `check_withdrawable` | 없음(읽기, 400 검증을 먼저) |
| ② | OWNER면 `stores.lock_store_of_owner` | stores |
| ③ | 상점이 있고 폐점 전이면 `offers.end_all_sales_of_store(commit=False)` | discount_offers(진행 중, id 오름차순) |
| ④ | 상점이 있으면 `reserved = reservations.has_reserved_for_store(store.id, excluding_user_id=user_id)` | discount_offers(상점 전체, id 오름차순) |
| ⑤ | `cancelled = reservations.cancel_active_for_user(user_id, reason)` | discount_offers(이 회원 예약의 offer, 오름차순) → pickup_reservations → payments → refunds → users(포인트 복구) |
| ⑥ | 상점이 있고 폐점 전이면 `stores.close_store_by_admin(..., has_reserved_reservations=reserved, commit=False)`(타 고객 RESERVED가 있으면 400 `STORE_HAS_RESERVED_RESERVATIONS`, 전체 롤백, D13) | stores |
| ⑦ | `accounts.withdraw_user(commit=False)`(auth가 남은 포인트 소멸, REQ-34 ④) | users |
| ⑧ | `commit()` | |

- **④를 ⑤보다 먼저 두는 이유**: admin.md 4번 흐름은 ⑤(취소) 뒤에 매장 확인을 했다. 그러면 payments·users를 잠근 **뒤에** 다른 offer를 잠그게 되어 D34(offers → … → users) 역방향이다. 매장 확인을 먼저 하고 자기 자신 예약(`excluding_user_id`)은 제외하면 같은 결과(자기 예약은 어차피 ⑤에서 취소)이면서 순서가 지켜진다. ⑥은 admin이 ④의 결과를 인자로 넘긴다(기존 시그니처 `has_reserved_reservations` 그대로).
- ⑤ 안의 offer들은 이미 ③④에서 잠근 것과 겹칠 수 있다(같은 트랜잭션이라 재잠금은 즉시 통과). 배치 내부는 오름차순이지만 ③④배치와 ⑤배치 사이의 전역 오름차순은 보장되지 않는다. **동시에 서로 다른 두 회원을 탈퇴시키는 드문 경우에만** 교착 가능성이 남는다(DB가 한쪽을 중단시키며 500이 날 수 있음, Q-A8).
- 예외가 나면 커밋되지 않고 세션이 닫힐 때 롤백된다(reservations는 불일치 때 명시적 `rollback()` 후 로그 1건).
- **자진 탈퇴(REQ-33)**: 같은 ①~⑧을 쓴다(REQ-34-1). 자진 탈퇴 EP·서비스는 auth 쪽 작업이다(F: `src/auth/presentation/router.py`에 탈퇴 EP가 없음). **생성 순환 주의(R12)**: `AuthApplicationService`가 예약 포트를 직접 받으면 `auth → reservations → payments → auth(포인트)`로 순환한다. 그래서 흐름은 `AuthApplicationService` **밖**의 조율 서비스(예: auth가 포트를 정의하는 `AccountWithdrawalService`, 또는 admin의 `withdraw_user`를 재사용)가 맡는다. 이 선택은 C-18로 올린다. reservations 쪽 계약(15.4.5의 두 메서드)은 어느 쪽이든 같다.

### 15.5 표현 (`presentation/`)

- **새 엔드포인트 없음**(내부 포트 호출만). 명세 `docs/reference/` 변경 없음(R15).
- 픽업 EP `POST /v1/reservations/{reservation_id}/pickup`(1건)만 `OwnerUser` → `SuspendedAllowedOwnerUser`로 교체(D-38). 나머지 EP(생성·목록·취소)는 `CurrentUser` 그대로 → 정지된 고객은 계속 403.

| EP | 의존성 | 정지된 상점주 | 탈퇴한 회원 |
| --- | --- | --- | --- |
| 픽업 | `SuspendedAllowedOwnerUser` | 통과(자기 매장 예약만, 소유 확인은 기존 `PermissionError`) | 401(`allow_suspended`와 무관, admin D9) |
| 생성·목록·취소 | `CurrentUser` | 정지 고객은 403 | 401 |

- 픽업 조건에 상점·할인 정지 상태를 쓰지 않는다(admin D35). 현재 `complete_pickup`은 이미 그렇다(`ensure_owned_by`, `ensure_pickup_time`만).
- 탈퇴한 회원의 **기록은 남는다**(REQ-34 ③). "탈퇴 후 본인도 볼 수 없다"는 `WITHDRAWN` 토큰이 401이라 자동으로 지켜진다(목록 EP 변경 없음).

### 15.6 조립 (`src/container.py`)

| 대상 | 변경 | 위치 |
| --- | --- | --- |
| `_pickup_pending`, `NoPickupPendingReservations` import | 삭제 | stores 구역 |
| `create_pickup_pending_port()` | 자리 표시 함수(`raise NotImplementedError`)로 바꾸고 `wire_dependencies`가 `create_store_reservation_query`로 override | stores 구역은 reservations 구역보다 **위**라 `Depends`로 직접 못 부름(기존 `create_reservation_lookup`과 같은 방식) |
| `create_store_offers_port(offers = Depends(create_discount_offer_repository))` | 신규 → `CatalogStoreOffersAdapter` | reservations 구역 |
| `create_store_reservation_query(reservations = Depends(create_reservation_repository), store_offers = Depends(create_store_offers_port))` | 신규 → `StoreReservationQuery` | reservations 구역 |
| `_reservation_admin`, `NoReservationAdmin` import | 삭제 | admin 구역 |
| `create_reservation_admin(service = Depends(create_reservation_service), query = Depends(create_store_reservation_query))` | `ReservationAdminAdapter`를 반환 | admin 구역(reservations 구역보다 아래라 직접 `Depends` 가능) |
| `wire_dependencies` | `create_pickup_pending_port: create_store_reservation_query` 한 줄 추가 | |

- 삭제 파일: `src/stores/infrastructure/pickup_pending.py`, `src/admin/infrastructure/reservation_admin.py`(사용처 없어진 뒤, 담당자 확인 후).
- **생성 순환 검사(R12)**: stores 서비스 → `StoreReservationQuery` → (reservations 레포지토리, catalog 레포지토리). 서비스를 받지 않으므로 순환 없음. admin → `ReservationAdminAdapter` → (예약 서비스 → lifecycle, 환불 포트 → payments 서비스 → lifecycle) + `StoreReservationQuery`. 이 중 admin을 받는 것은 없다. 예약 서비스·payments 서비스는 auth를 받지 않는다(포인트 연동이 붙으면 payments → auth 서비스가 생기는데 auth가 reservations·payments를 받지 않는 한 순환 아님. 자진 탈퇴 조율은 `AuthApplicationService` 밖, C-18). 확인 방법: `(cd src && uv run python -c "import main")`, `tests/reservations/test_wiring.py`에 `create_pickup_pending_port`·`create_reservation_admin`이 새 어댑터로 풀리는지 단언.

### 15.7 테스트 계획 (`layer-implementation/testing.md` 기준)

- 도메인: 변경 없음. 기존 `cancel` 전이 테스트 유지.
- 서비스(fake, DB 없음, `tests/reservations/test_service.py`·`fakes.py`에 fake 레포지토리 새 메서드 추가):
  - lifecycle `cancel_all_for_user`: PENDING 2건·RESERVED 1건·PICKED_UP 1건·CANCELLED 1건 → 앞의 3건만 CANCELLED, PICKED_UP·CANCELLED는 그대로, `release` 3회(재고 `quantity`), 반환 3건, 환불 대상은 RESERVED 1건만. PICKED_UP이 있어도 `PickedUpReservationExistsError`가 나지 않음.
  - offer 잠금 호출 순서가 `offer_id` 오름차순, 중복 offer는 1회, 잠금 후 재조회에서 그 사이 취소된 예약은 건너뜀(멱등). 빈 목록은 0.
  - 응용 `cancel_all_for_user`: `refund_for_cancelled_reservation`이 **`waive_penalty=True`**로 RESERVED에만 호출, PENDING은 `ensure_no_paid_payment`, `session.commits == 0`(commit 안 함), 반환 수. 환불 불일치 → `rollback` 1회·ERROR 로그 1건·`DataInconsistentError`(모은 목록). 재고 복구 불일치도 같음.
  - 닫힌 할인이면 `release`가 False여도 취소는 진행(D40).
  - `StoreReservationQuery`: RESERVED만 True, PENDING_PAYMENT·PICKED_UP·CANCELLED만 있으면 False, 상점에 할인이 없으면 False(예약 조회 안 함), `excluding_user_id` 제외, `for_update=True`로 offer ID를 조회하는지, `has_pickup_pending_for_store`가 같은 결과.
- 어댑터: `ReservationAdminAdapter`가 `DataInconsistentError`를 admin 예외로 번역(로그 없음). `CatalogStoreOffersAdapter` 위임.
- wiring: `NoPickupPendingReservations`·`NoReservationAdmin` 단언을 새 어댑터 단언으로 교체. 픽업 EP가 `SuspendedAllowedOwnerUser`를 쓰는지 단언.
- DB 통합(`tests/reservations/test_api_db.py` 또는 새 `test_withdrawal_db.py`, **실행은 사용자 승인 후**, R16: skip은 통과가 아님): 정지된 상점주 토큰으로 픽업 200, 정지된 상점주가 예약 생성·취소하면 403(정지된 CUSTOMER도 403), 탈퇴한 상점주 토큰 픽업 401. 실제 레포지토리: `find_by_user_and_statuses`의 정렬·상태 필터, `exists_by_offers_and_status`, catalog `find_ids_by_store`(타 상점 제외). 흐름: 탈퇴 → PENDING 취소+재고 복구(`stock_log` 양수), RESERVED 취소+환불 1건(`penalty_amount == 0`, `refund_amount == payment.amount`)+재고 복구, PICKED_UP 기록 유지, 결과가 **한 번 커밋**(중간 예외 시 전부 롤백).
- 포인트: payments 포인트 연동(C-16)이 구현된 뒤에 "환불 후 `users_point`가 `RESTORE`/`REVOKE`만큼 변하고 이어서 탈퇴가 잔액을 0으로 소멸" 테스트를 추가. 지금은 사용·적립이 없으므로 "환불 금액만 확인"으로 둔다.

### 15.8 구현자 쓰기 범위 (`layer-implementer` 발주용)

| 범위 | 파일 | 비고 |
| --- | --- | --- |
| reservations | `src/reservations/domain/{repository,rules}.py`, `application/{ports,lifecycle_service,service,store_query,store_adapters,admin_adapters}.py`, `infrastructure/repositories.py`, `presentation/router.py`(픽업 의존성 1줄), `tests/reservations/**` | 기존 EP·응답·전이표 불변 |
| container | `src/container.py`의 stores 구역(`create_pickup_pending_port`, `_pickup_pending`), reservations 구역(신규 팩토리 2개), admin 구역(`create_reservation_admin`, `_reservation_admin`), `wire_dependencies` 1줄 | 다른 구역 불변 |
| payments | **이 설계의 범위에서는 변경 없음**(F-1). 포인트 연동(C-16)은 payments 설계(`docs/design/payments.md`) 작업에서 함 | `src/payments/**`는 건드리지 않음 |
| **확정 범위 확장** (사용자 승인 2026-11-05, 팀원 허락: C-15, C-17, C-19) | catalog: `domain/repository/discount_offer_repository.py`(`find_ids_by_store` 추상), `infrastructure/repositories.py`, `tests/catalog/**`의 fake 레포지토리 / admin: `application/ports.py`(D-32), `application/service.py`(호출 순서·인자), `domain/exceptions.py`(신규, `ReservationDataInconsistentError`)와 500 변환(admin 라우터), `infrastructure/reservation_admin.py` 삭제, `tests/admin/**` / stores: `infrastructure/pickup_pending.py` 삭제, `application/ports.py` docstring, `tests/stores/**`의 관련 단언 | 구현자가 쓴다 |
| 하지 않음 (확정) | `src/payments/**`·`tests/payments/**`(포인트 연동은 payments 작업, C-16), `src/auth/**`(자진 탈퇴 EP·포인트 소멸·조율 서비스는 C-18), `docs/reference/`, `schema.sql` | |

완료 게이트는 `backend-invariants` §7과 같다. R1~R16 준수, 특히 R5(어댑터·서비스 `cancel_all_for_user`는 commit 금지), R11(catalog는 추상 레포지토리만), R12(생성 순환 없음), R13(같은 세션).

### 15.9 결정 표 (D-번호)

| # | 결정 | 근거 | 상태 |
| --- | --- | --- | --- |
| D-31 | 회원별 일괄 취소는 **PENDING_PAYMENT와 RESERVED를 모두** 취소한다. 재고 복구(`stock.release`, 닫힌 할인은 D40대로 건너뜀), RESERVED는 전액 환불(`waive_penalty=True`), PICKED_UP·CANCELLED는 건드리지 않고 기록 유지. 새 메서드 `lifecycle.cancel_all_for_user`·`service.cancel_all_for_user`(commit 안 함) | REQ-34 ①②③, REQ-34-1, B-3(요구조건이 admin D12보다 우선, 사용자 결정 2026-11-05) | 확정(요구조건) |
| D-32 | admin 포트 변경: `cancel_reserved_for_user` → **`cancel_active_for_user(user_id, *, reason) -> int`**(이름과 뜻을 요구조건에 맞춤, 결제 대기 포함 취소 수), `has_reserved_for_store(store_id, *, excluding_user_id=None)`(선택 인자 추가). admin `withdraw_user`는 ④(매장 확인)를 ⑤(취소)보다 먼저 호출(15.4.6). `NoReservationAdmin`은 삭제 | 이름이 뜻과 다르면 오해(F-4). 잠금 순서 D34 | **확정** (사용자, 2026-11-05, Q-A4) |
| D-33 | 환불은 payments 기존 연결(`PaymentRefundAdapter` → `refund_for_cancelled_reservation(waive_penalty=True)`)을 **그대로** 재사용. payments 코드 변경 없음. 포인트 복구·회수는 payments가 같은 메서드 안에서 하며 아직 코드에 없음(C-16) | F-1, F-2, payments.md 4.3.4 `_apply_refund` | 확정(위약금), 포인트는 C-16 |
| D-34 | 매장별 확인은 **S-4(스키마) 없이** `offer_ids = catalog 추상 레포지토리 find_ids_by_store` → `reservations.exists_by_offers_and_status(ids, RESERVED)` 두 단계. `StoreReservationQuery` 하나가 stores `PickupPendingPort`와 admin `has_reserved_for_store`를 둘 다 만족. 둘 다 **RESERVED만** 센다 | admin D41(b안)과 같음, R11(조인 금지), R14(스키마 변경 없음), F-5 | **확정** (사용자, 2026-11-05, Q-A1·Q-A2·Q-A9, S-4 안 함) |
| D-35 | 매장 확인은 **offer 행을 `FOR UPDATE`(id 오름차순)로 잠그고** 예약 행은 잠그지 않는다 | 모든 RESERVED 생성·소멸 경로가 offer를 먼저 잠금(D-6), admin.md "예약 행 FOR UPDATE"를 대체해 D34 순서 유지 | **확정** (사용자, 2026-11-05) |
| D-36 | 조립: `create_pickup_pending_port`는 자리 표시 + override, `create_reservation_admin`은 직접 `Depends` | R9, R12, 기존 `create_reservation_lookup` 방식 | 확정(방식) |
| D-37 | 불일치(RD-38·RD-39)는 일괄 취소에서도 **전부 롤백 + ERROR 로그 1건 + 500**. 불일치 예약이 1건이라도 있으면 탈퇴 전체가 실패한다. admin 쪽 번역 예외는 admin이 정의 | RD-38, `cancel_all_for_offer` 선례, R7 | **확정** (사용자, 2026-11-05, Q-A3) |
| D-38 | 픽업 EP 1건만 `SuspendedAllowedOwnerUser`로 교체. 소유 확인·상태·시간 검사는 불변 | admin D35·D39 확정, auth B-2 | 확정 |
| D-39 | catalog 할인 수정 가드용 예약 존재 판정은 **취소되지 않은 예약만** 센다. `ReservationRepository.exists_non_cancelled_by_offer(offer_id)`를 추가하고 `OfferReservationLookup.has_reservations_for_offer`가 그것을 호출한다. catalog 포트 서명은 불변 | `docs/requirements/catalog-offers.md` REQ-17(확정 2026-11-06), catalog.md D81 | 확정(요구 조건 확정) |

### 15.10 정합 이슈 (C-번호)

| # | 대상 | 내용 |
| --- | --- | --- |
| C-15 | **catalog** | 추상 `DiscountOfferRepository`에 `find_ids_by_store(store_id, *, for_update=False)` 추가 필요(F-5). catalog 담당(태환 님) 확인. `tests/catalog` fake 레포지토리도 같이 고쳐야 한다(추상 메서드 추가라 깨짐). `docs/design/catalog.md` 갱신 제안 |
| C-16 | **payments** (읽기만 확인, 수정 안 함) | `refund_for_cancelled_reservation`에 사용 포인트 복구(`restore_points`)·적립 회수(`revoke_points`)가 아직 없다(F-2). payments.md 4.3.3·4.3.4의 `_apply_refund`가 정본이고, `pay()`의 `use_point`·적립(D-10)과 **같이** 구현해야 한다. 순서는 환불 INSERT → 결제 저장 → 포인트(users는 잠금 순서의 마지막). 구현 전에는 탈퇴 환불이 금액만 처리한다(포인트가 쓰인 적이 없어서 결과는 정확함). 배유민 님 작업(#22). **확정(사용자, 2026-11-05, Q-A5)**: 포인트 복구·회수는 payments 포인트 연결 작업(payments.md 10절, `_apply_refund`)에서 함께 구현된다. 이 설계의 구현 범위에는 payments가 없다 |
| C-17 | **admin** | D-32 포트 변경과 `ReservationDataInconsistentError`(500 `DATA_INCONSISTENT`) 정의·변환 필요(admin 라우터는 현재 불일치 변환이 없음). admin.md D12(RESERVED만)·D43(자리표시자)·D44(stock_log user_id)를 이 절로 갱신(D44: `user_id`는 예약자, `reason`은 사유) |
| C-18 | **auth** | 자진 탈퇴 EP(REQ-33)·비밀번호 재확인(REQ-36)·남은 포인트 소멸(REQ-34 ④, `withdraw_user` 확장)은 auth 작업. 조율을 `AuthApplicationService` 밖에 두지 않으면 R12 순환(15.4.6). 포인트 소멸은 환불 복구(⑤) **뒤**여야 한다(⑦) |
| C-19 | **stores** | `PickupPendingPort`의 docstring("미연계")과 `NoPickupPendingReservations` 삭제. stores.md D21 갱신 |
| C-20 | **docs/design/admin.md** | 13절 A-1·A-2·A-4와 admin D12·D41·D43·D44는 이 절이 대체한다(admin.md는 수정하지 않았음, 담당자에게 전달) |
| C-21 | **reservations** (`src/reservations/domain/repository.py:30`, `infrastructure/repositories.py:63`, `application/catalog_adapters.py:19-20`) ↔ catalog D81 | D-39 구현: 추상·구현에 `exists_non_cancelled_by_offer` 추가, 어댑터 호출 교체. 추상 메서드가 늘어 `tests/reservations/fakes.py:79`와 `tests/payments/test_integration.py:120`의 fake 레포지토리도 구현해야 한다(인스턴스 생성 실패, catalog CI-12와 같은 유형). `tests/reservations/test_adapters.py:197-199`는 "취소 예약만 있으면 False, 그 외 True"로 단언을 보강한다 | `exists_by_offer`는 이번에 지우지 않는다(사용처가 사라지면 삭제는 사용자 결정, catalog CI-17) |

### 15.11 질문 목록과 기본값 (**확정, 사용자 2026-11-05**: Q-A1~Q-A9 모두 아래 "임시 기본값" 열의 값 그대로 확정. Q-A4·Q-A9는 admin·catalog·stores 변경 허락을 받아 범위 확장 승인)

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 |
| --- | --- | --- | --- | --- |
| Q-A1 | 폐점·상점주 탈퇴 때 **PENDING_PAYMENT** 예약도 막아야 하는가(폐점 뒤 결제되면 RESERVED가 폐점 매장에 생김) | stores `has_pickup_pending_for_store`, admin D13 | 막지 않음(RESERVED만). 단 폐점 전에 `end_all_sales`가 새 예약을 막고, 결제는 offer를 잠그므로 확인과 폐점 사이에 끼어들 수 없음. 폐점 뒤 결제는 별도 위험으로 남김 | admin D13 "RESERVED", 명세 "처리되지 않은 RESERVED" |
| Q-A2 | 픽업 시간이 지난(노쇼) RESERVED도 계속 폐점을 막는가(자동 만료 없음) | D-34 | 계속 막는다 | 명세 "처리되지 않은 RESERVED", 만료 규칙 없음 |
| Q-A3 | 불일치 예약이 있으면 탈퇴가 500으로 막혀도 되는가 | D-37, RD-38 | 전체 롤백(막힘). 운영자가 데이터를 고친 뒤 재시도 | RD-38, R16(검사를 약하게 하지 않음) |
| Q-A4 | admin 포트 이름·시그니처 변경 범위(D-32), admin 코드 수정 허용 | admin.md D30(포트 admin 소유) | 이름 변경 + `excluding_user_id` 추가, admin 담당(서상혁 님) 본인 변경 | 요구조건 우선, 사용자 동의 |
| Q-A5 | 환불에 따른 포인트 복구·회수 시점(payments 포인트 연동 전) | C-16, payments D-10 | payments 연동 때 같은 메서드가 처리. 그 전에는 금액만 환불 | payments.md 4.3.4 |
| Q-A6 | 일괄 취소의 사유 문구 | REQ-34, admin 강제 탈퇴 사유 | 자진 탈퇴 `rules.WITHDRAWAL_CANCEL_REASON = "회원 탈퇴"`, 강제 탈퇴는 admin이 넘긴 사유 | 한곳(rules)에 모음 |
| Q-A7 | 탈퇴 처리 중 같은 회원이 보낸 **새 예약 생성**(이미 인증을 통과한 요청)이 커밋 직전에 끼어들 가능성 | 15.4.2 3단계 | 막지 않음(잠그는 offer 범위 밖의 offer는 못 막음). 탈퇴 커밋 뒤 만들어진 예약은 `WITHDRAWN` 회원의 `PENDING_PAYMENT`로 남을 수 있어 재고를 점유함. 완화는 예약 생성이 회원 상태를 다시 확인하는 것(auth 의존성 변경, C-18) | 잠금 순서 D-6(회원이 마지막) |
| Q-A8 | 서로 다른 회원 둘을 동시에 탈퇴시킬 때의 교착 가능성(15.4.6) | D34 | 허용(DB가 한쪽을 중단, 재시도) | 드문 경우, 모든 offer를 한꺼번에 먼저 잠그는 방식은 과함 |
| Q-A9 | catalog `find_ids_by_store`를 추상 레포지토리에 추가하는 것을 catalog 담당이 받아들이는가(C-15). 거부하면 S-4(`store_id` 컬럼)로 | D-34 | 추가한다 | admin D41 (b)안 |

### 15.12 불변 규칙 점검

R1(도메인 변경은 추상 메서드 선언뿐), R2·R11(catalog는 추상 레포지토리, 포트는 reservations 정의, admin·stores는 reservations를 import하지 않음), R3(상태 전이는 `PickupReservation.cancel`, 서비스는 조율만), R4(ID 목록·도메인 객체만 반환), R5·R13(`cancel_all_for_user`·어댑터·질의는 commit 안 함, 시작한 서비스가 1회), R6·R7(새 예외는 `DataInconsistentError`/admin 번역 예외, 500 형식 유지), R8~R10(추상만 받음, 선언된 메서드만 호출), R12(15.6 검사), R14(스키마 불변), R15(명세 불변), R16(검사를 약하게 하지 않음, DB 테스트는 승인 후 실행). 충돌하는 요구 없음.

## 16. 취소 주체(`cancelled_by`) 기록과 조회 노출 (2026-11-09 추가)

- 기준: `origin/main` c954de2. 사용자 결정(**확정, 2026-11-09**): 코드에 취소 주체를 추가한다. 목적은 고객 화면(와이어프레임 C5 "직접 취소", C5b "매장 사정 취소")에서 두 경우를 구분해 보여 주는 것이다.
- 이 절의 세부 결정(값 집합·NULL 허용·시그니처 방식)은 모두 **확정(위임, 2026-11-09)** 이다. 질문은 16.10에 따로 모은다.
- 범위 밖: "픽업 시간 지남"은 DB 변경 없이 화면이 `pickup_end`로 계산한다. 이 절은 다루지 않는다.
- 용어: 취소 주체 = `cancelled_by`(누가 취소를 일으켰는가). 사유 문구(`reason`, 재고·환불 기록용)와 다르며 저장하지 않던 `reason`은 이번에도 저장하지 않는다.

### 16.0 차단 이슈

없음. 확인: `git status --short`(깨끗함), `grep -rn "cancel" src`로 취소 경로 전수 조사(16.1). 새 의존성·환경변수 없음. 스키마 변경은 개발 DB에 ALTER가 필요하다(16.3, `create_all`은 기존 테이블에 컬럼을 추가하지 않는다).

### 16.1 현재 취소 경로 전수 조사와 주체 매핑

예약 상태를 CANCELLED로 만드는 곳은 `PickupReservation.cancel` 호출 4곳뿐이다(`src/reservations/application/lifecycle_service.py:98,114,141,~190`).

| # | 경로 | 진입점 (파일:위치) | 호출 시그니처(불변) | 주체 | 근거 |
| --- | --- | --- | --- | --- | --- |
| P1 | 고객 직접 취소 `POST /v1/reservations/{id}/cancel` | `reservations/application/service.py:74 cancel_reservation` -> `lifecycle.cancel` | 외부 호출 없음(EP) | `CUSTOMER` | 본인 요청 |
| P2 | 고객 환불 요청으로 인한 취소 `POST /v1/payments/{id}/refunds` | `payments/application/service.py:160` -> `ReservationLifecyclePort.cancel_for_refund(reservation_id, reason, commit)` -> `lifecycle.cancel_for_refund` | **불변** | `CUSTOMER` | 환불 EP는 `CurrentUser`가 본인 결제를 환불(`payments/presentation/router.py:78-88`). 고객이 시작한 취소 |
| P3 | 점주 판매 중단(`cancel_reservations=true`) | `catalog/application/service.py:278` -> `ReservationCancelPort.cancel_all_for_offer(offer_id, *, reason)` -> `reservations/application/service.py:135` | **불변** | `STORE` | 호출자는 `OwnerUser` 전용 EP(`catalog/presentation/router.py:247`) |
| P4 | 자진 회원 탈퇴 | `auth/application/withdrawal_service.py:~58` -> `cancel_active_for_user(user_id, *, reason="회원 탈퇴")` -> `service.cancel_all_for_user` | **불변** | `SYSTEM` | 탈퇴 처리의 부수 효과 |
| P5 | 관리자 강제 탈퇴 | `admin/application/service.py:98` -> `cancel_active_for_user` -> `service.cancel_all_for_user` | **불변** | `SYSTEM` | P4와 같은 메서드라 포트가 구분하지 못한다(아래 결정 D-42) |
| P6 | 상점 폐점·관리자 정지(`end_all_sales_of_store`) | `catalog/application/service.py:462` | - | (해당 없음) | **예약을 취소하지 않는다**. 할인만 종료(`offer.end_sale`)하고, 타 고객 RESERVED가 있으면 폐점이 거부된다(`has_reserved_for_store`). 취소 경로가 아니다 |
| P7 | 관리자 할인 정지(`suspended_reason`) | catalog | - | (해당 없음) | `ReservationCancelPort`는 `deactivate_offer` 한 곳에서만 쓴다(`grep ReservationCancelPort`). 예약을 취소하지 않는다 |

조사 결론
- 주체 값 최소 집합: **`CUSTOMER`, `STORE`, `SYSTEM`** 세 개. 추천안에 있던 `ADMIN`은 **넣지 않는다**: 관리자가 예약을 직접 취소하는 경로가 없고(P5는 회원 탈퇴 처리), 강제 탈퇴된 회원은 토큰이 401이라 자기 예약 목록을 볼 수 없다. 나중에 경로가 생기면 값 하나와 CHECK 한 줄을 추가한다.
- `SYSTEM`(P4·P5)은 탈퇴한 회원의 예약에만 붙으므로 **고객 화면에 노출되지 않는다**. 값은 데이터 정합(누가 취소했는지 감사)용이다. 점주 목록(`/stores/{id}/reservations`)에도 넣지 않는다(16.5).
- 화면 매핑(와이어프레임 쪽에 전달): `CUSTOMER` -> C5 "직접 취소", `STORE` -> C5b "매장 사정 취소", `null`(기존 취소 행) -> 구분 없이 "취소됨", `SYSTEM` -> 노출되지 않음(방어적으로 "취소됨").

### 16.2 도메인 (`domain/`, R1·R3)

- 새 `StrEnum` `CancelActor`(`domain/cancel_actor.py`, 순수 파이썬): `CUSTOMER`, `STORE`, `SYSTEM`. 값 문자열은 DB CHECK·응답과 같다.
- `PickupReservation.__init__`에 `cancelled_by: CancelActor | None = None` 추가(**기존 인자 순서 뒤에 키워드로 추가**, 기존 호출 불변).
  - 검증 추가: `cancelled_by`가 있으면 `CancelActor(cancelled_by)`로 변환(값 오류는 `ValueError`), 그리고 `status`가 `CANCELLED`여야 한다. 아니면 `ValueError("취소 주체는 취소된 예약에만 있어야 합니다.")`.
  - **`CANCELLED`인데 `cancelled_by`가 None인 것은 허용**한다(기존 행, 16.3). 새 취소는 `cancel`이 반드시 채운다.
- 시그니처 변경(**R3: 규칙은 엔티티에**): `cancel(self, now: datetime, cancelled_by: CancelActor) -> None`. 기본값을 두지 않는다(호출부가 빠뜨리면 즉시 `TypeError`로 드러나게).
  - 검사 순서: ① `_raise_terminal()`(이미 취소·픽업이면 기존 예외 그대로) ② `now` timezone ③ `CancelActor(cancelled_by)` 변환 실패 시 `ValueError`. 기존 예외 순서·메시지는 바뀌지 않는다.
  - 성공 시 `status=CANCELLED`, `cancelled_at=now`, `cancelled_by` 저장.
- 상태 전이표 불변(PENDING_PAYMENT/RESERVED -> CANCELLED). 주체는 전이 조건이 아니다(누구든 같은 규칙).
- 상수는 `domain/rules.py`에 한곳으로 모은다: `REFUND_REQUEST_CANCEL_ACTOR = CancelActor.CUSTOMER`(P2), `OFFER_CLOSE_CANCEL_ACTOR = CancelActor.STORE`(P3), `WITHDRAWAL_CANCEL_ACTOR = CancelActor.SYSTEM`(P4·P5). (`pickup_reservation.py`가 `rules.py`를 이미 import하므로, `CancelActor`를 별도 파일 `domain/cancel_actor.py`에 두어 `rules.py`·`pickup_reservation.py`가 함께 import한다. 순환 없음.)

### 16.3 인프라와 스키마 변경 제안 (S-번호, R14)

`schema.sql`·`db-schema/SKILL.md`는 이 작업에서 **고치지 않는다**(설계는 변경안만). 구현 시 R14에 따라 두 파일을 함께 고친다(`.claude/` 수정이므로 16.9의 범위 확장, 사용자 승인 필요).

| 항목 | 값 |
| --- | --- |
| 테이블 | `pickup_reservations` |
| 새 컬럼 | `cancelled_by VARCHAR(20)` |
| NULL | **허용**. 기존 취소 행과 CANCELLED가 아닌 행은 NULL |
| CHECK 1 | `ck_reservation_cancelled_by`: `cancelled_by IN ('CUSTOMER','STORE','SYSTEM')` (NULL은 통과) |
| CHECK 2 | `ck_reservation_cancelled_by_status`: `cancelled_by IS NULL OR status = 'CANCELLED'` |
| 하지 않는 것 | `status = 'CANCELLED'`이면 NOT NULL을 요구하는 CHECK는 **넣지 않는다**(기존 취소 행이 위반됨) |
| `models.py` | `cancelled_by: Mapped[str \| None] = mapped_column(String(20))` + 위 두 `CheckConstraint`(`__table_args__`) |

기존 취소 행 처리: **백필하지 않고 NULL로 둔다**(확정 위임). 이유: 저장된 `reason`이 없어 고객 취소(CUSTOMER)와 판매 중단(STORE)을 사후에 구분할 근거가 없다. 추측으로 CUSTOMER를 채우면 판매 중단 취소가 "직접 취소"로 잘못 보인다. 응답에서는 `null`이다.

개발 DB ALTER문(이미 만들어진 DB용, 되돌리기 포함):

```sql
ALTER TABLE pickup_reservations ADD COLUMN cancelled_by VARCHAR(20);
ALTER TABLE pickup_reservations
    ADD CONSTRAINT ck_reservation_cancelled_by
    CHECK (cancelled_by IN ('CUSTOMER', 'STORE', 'SYSTEM'));
ALTER TABLE pickup_reservations
    ADD CONSTRAINT ck_reservation_cancelled_by_status
    CHECK (cancelled_by IS NULL OR status = 'CANCELLED');
-- 되돌리기: ALTER TABLE pickup_reservations DROP COLUMN cancelled_by;  (CHECK도 함께 삭제됨)
```

실행은 사용자가 한다(설계자·구현자는 DB를 바꾸지 않는다). 컬럼이 없는 DB에 새 코드를 띄우면 예약 조회·저장이 모두 실패하므로 **ALTER를 먼저** 적용한다. 테스트 DB가 `create_all`이면 이미 있는 테이블에는 컬럼이 안 생기므로 테스트 DB도 같은 ALTER가 필요하다(또는 테스트 DB 재생성).

레포지토리(`infrastructure/repositories.py`): `save`의 신규 INSERT와 UPDATE 분기 모두 `cancelled_by=...`를 쓰고(UPDATE는 `model.cancelled_by = reservation.cancelled_by`, 현재 `repositories.py:164` 부근), `_to_domain`은 `CancelActor(model.cancelled_by)`(None이면 None)로 변환한다. 추상 `ReservationRepository`의 메서드 목록은 불변(R10). 동시성: 기존 `for_update` 경로 그대로. 새 잠금 없음.

### 16.4 응용 (`application/`)

핵심 원칙: **다른 모듈이 부르는 포트 시그니처는 바꾸지 않는다.** 주체는 reservations가 진입점별로 직접 정한다(D-41).

| 메서드 | 변경 |
| --- | --- |
| `ReservationApplicationService.cancel_reservation` (P1) | `lifecycle.cancel(..., cancelled_by=CancelActor.CUSTOMER, ...)` |
| `ReservationLifecycleService.cancel` | 키워드 인자 `cancelled_by: CancelActor` 추가(필수) -> `reservation.cancel(now, cancelled_by)` |
| `ReservationLifecycleService.cancel_for_refund` (P2) | 내부에서 `rules.REFUND_REQUEST_CANCEL_ACTOR`를 `reservation.cancel`에 전달. 시그니처 불변(payments 포트·어댑터 `adapters.py:52` 불변) |
| `ReservationLifecycleService.cancel_all_for_offer` (P3) | `reservation.cancel(now, rules.OFFER_CLOSE_CANCEL_ACTOR)`. 시그니처 불변 |
| `ReservationLifecycleService.cancel_all_for_user` (P4·P5) | `reservation.cancel(now, rules.WITHDRAWAL_CANCEL_ACTOR)`. 시그니처 불변 |
| `ReservationApplicationService.cancel_all_for_offer`·`cancel_all_for_user` | 변경 없음(`reason`만 받는다) |

- 트랜잭션 경계·잠금 순서·환불 순서(RD-5, D-6, 13.6.4)는 불변이다. 주체 기록은 같은 `save()`에 실린다.
- `cancel_reservation`의 호출 시그니처 `(user_id, reservation_id)`와 응답은 불변. 반환 도메인 객체에 `cancelled_by`가 실려 응답에 나간다.

### 16.5 표현 (`presentation/`, R15)

`GET /v1/users/me/reservations`와 `POST /v1/reservations/{id}/cancel`만 바꾼다. **별도 상세 조회 EP는 없다**(`router.py`에 `GET /reservations/{id}` 없음). 기존 필드의 이름·타입·순서·의미는 불변이고 필드 하나만 **추가**한다.

| 스키마 | 추가 필드 | 타입 | 값 |
| --- | --- | --- | --- |
| `ReservationListItem` (내 예약 목록 항목) | `cancelled_by` | `str \| None` | `CUSTOMER`/`STORE`/`SYSTEM`. 취소되지 않았거나 기존 취소 행이면 `null` |
| `ReservationCancelResponse` (취소 EP 응답) | `cancelled_by` | `str \| None` | 이 EP로는 항상 `CUSTOMER`(직접 취소). 타입은 목록과 같게 둔다 |

- `ReservationCreateResponse`, `StoreReservationListItem`(점주용)에는 넣지 않는다(고객 구분 화면이 목적이고, 점주 목록은 고객 정보 최소화 원칙 R-REQ25와 같은 방향).
- 에러 코드·상태 코드 불변(400/401/403/404/409).
- 이 필드 때문에 목록의 `status=CANCELLED`로 거르는 쿼리·정렬은 바뀌지 않는다(`cancelled_by`로 필터하는 쿼리 매개변수는 추가하지 않는다).

명세 변경(`docs/reference/reservations.md`, 구현자 쓰기 범위): ① 2절 "내 예약 목록" 응답 표에 `cancelled_by`(string 또는 null) 행과 값 설명(`CUSTOMER` 고객 직접 취소, `STORE` 매장 사정 취소, `SYSTEM` 시스템 처리, `null` 취소 주체를 알 수 없음) 추가, ② 3절 취소 응답 표(`:164` 부근)와 JSON 예시에 `"cancelled_by": "CUSTOMER"` 추가. 3절의 "확인 필요"는 그대로 둔다. `docs/reference/README.md`의 상태 값 표 옆에 취소 주체 값 표를 두는 것은 선택(16.10 Q-38).

### 16.6 다른 모듈 영향 (R11, R12)

| 모듈 | 영향 | 변경 필요 |
| --- | --- | --- |
| catalog | `ReservationCancelPort.cancel_all_for_offer(offer_id, *, reason)` 불변 | 없음 |
| admin | `cancel_active_for_user(user_id, *, reason)` 불변 | 없음 |
| auth(탈퇴 조정) | 같은 포트 불변 | 없음 |
| payments | `cancel_for_refund(reservation_id, reason, *, commit)` 불변 | 없음 |
| stores | 영향 없음 | 없음 |
| `src/container.py` | 조립 변경 없음(새 의존성 없음) | 없음 |

그러므로 **이 설계는 범위 확장이 없다**(src/reservations 안과 문서·스키마 파일만). 단 P4와 P5를 `SYSTEM` 하나로 합친 것은 포트를 바꾸지 않기 위한 선택이다. 나중에 "관리자 강제 탈퇴"를 따로 구분하려면 admin 포트에 주체 인자를 더해야 하므로 그때 범위 확장(admin·auth 수정)으로 다룬다(Q-37).

### 16.7 테스트 계획 (`tests/reservations/**`, `testing.md` 기준)

기존 `reservation.cancel(now)` 직접 호출은 시그니처 변경으로 깨진다. 호출 수정 위치: `tests/reservations/test_domain.py`, `tests/reservations/test_service.py`, `tests/payments/test_integration.py`(payments 테스트가 `.cancel(`를 직접 부르는지 구현자가 확인; 부르면 **범위 확장**으로 표시하고 보고).

| 구분 | 케이스 |
| --- | --- |
| 도메인 | `cancel(now, CUSTOMER/STORE/SYSTEM)`이 `cancelled_by`·`cancelled_at`·`status`를 세팅 / 잘못된 문자열이면 `ValueError` / 이미 CANCELLED·PICKED_UP에서는 주체와 상관없이 기존 예외가 먼저 / 생성자: `cancelled_by`가 있는데 상태가 CANCELLED가 아니면 `ValueError`, CANCELLED + None은 허용(기존 행) |
| 서비스(fake) | P1 `cancel_reservation` -> `CUSTOMER` / P2 `cancel_for_refund` -> `CUSTOMER` / P3 `cancel_all_for_offer` -> 취소된 모든 예약이 `STORE` / P4·P5 `cancel_all_for_user` -> `SYSTEM` / 멱등: 이미 취소된 예약의 `cancelled_by`는 덮어쓰지 않는다(`cancel_for_refund`의 `is_cancelled` 조기 반환 유지) |
| 표현 | 취소 응답과 내 목록 항목에 `cancelled_by` 포함, 취소 안 된 항목은 `null`, 기존 필드 그대로(기존 `test_api.py` 단언 불변으로 통과) |
| DB(`-m db`) | ALTER 적용 후 `save`/`find_by_id` 왕복에서 `cancelled_by` 보존 / CHECK 위반 값 INSERT 거부 / `cancelled_by`가 있고 status가 CANCELLED가 아니면 거부 / 기존 취소 행(NULL)이 `_to_domain`으로 읽힘 |

DB 테스트 skip은 통과가 아니다(R16). 이 절의 변경은 테스트 DB에 ALTER가 먼저 적용되어야 DB 테스트가 돈다.

### 16.8 구현 순서

1. `domain/cancel_actor.py`, `PickupReservation.cancel`·생성자, `rules.py` 상수 -> 2. `models.py`(+CHECK), `repositories.py` -> 3. `lifecycle_service.py`, `service.py`(`cancel_reservation`) -> 4. `schemas.py` 필드 두 개 -> 5. 테스트 수정·추가 -> 6. `docs/reference/reservations.md` -> 7. (승인 후) `schema.sql`·`db-schema/SKILL.md`.

### 16.9 구현자 쓰기 범위 (`layer-implementer` 발주용)

| 구분 | 경로 |
| --- | --- |
| 쓴다 | `src/reservations/**`, `tests/reservations/**`, `docs/reference/reservations.md` |
| **범위 확장(사용자 승인 후)** | `.claude/skills/db-schema/schema.sql`, `.claude/skills/db-schema/SKILL.md`(R14: models와 같이 고쳐야 함), `tests/payments/**`(`.cancel(` 직접 호출이 있을 때만) |
| 쓰지 않는다 | `src/catalog/**`, `src/admin/**`, `src/auth/**`, `src/payments/**`, `src/stores/**`, `src/container.py`, `src/main.py`, `docs/reference/README.md` |
| 사용자가 직접 | 개발·테스트 DB에 16.3 ALTER 실행 |

완료 게이트는 `backend-invariants` §7과 같다.

### 16.10 결정 표(D-번호), 정합 이슈(C-번호), 질문(Q-번호)

결정(이어서 번호: 기존 최대는 D-39(15.9), C-21(15.10), Q-36이며 `RD-40`은 별도 계열이다. 이 절은 D-40, C-22, Q-37부터 쓴다)

| # | 결정 | 근거 | 상태 |
| --- | --- | --- | --- |
| D-40 | 취소 주체 값은 `CUSTOMER`·`STORE`·`SYSTEM` 3개(`ADMIN` 제외). 컬럼 `pickup_reservations.cancelled_by VARCHAR(20)` NULL 허용 + CHECK 2개(16.3) | 16.1 경로 조사: 관리자 직접 취소 경로 없음, SYSTEM은 탈퇴 전용 | 확정(위임, 2026-11-09) |
| D-41 | 규칙은 도메인 `PickupReservation.cancel(now, cancelled_by)`(기본값 없음). 주체 결정은 reservations 내부(진입점별 상수 `rules.*_CANCEL_ACTOR`)이고 **타 모듈 포트 시그니처는 바꾸지 않는다** | R3, R11, 범위 최소화 | 확정(위임, 2026-11-09) |
| D-42 | 자진 탈퇴(P4)와 관리자 강제 탈퇴(P5)는 모두 `SYSTEM`. 두 경우 모두 대상 회원이 목록을 볼 수 없어 구분 이득이 없고, 구분하려면 admin·auth 포트 변경이 필요 | 16.1, 범위 확장 회피 | 확정(위임, 2026-11-09) |
| D-43 | 기존 취소 행은 백필하지 않고 NULL. 응답 `null` | 취소 사유가 저장돼 있지 않아 사후 추정 불가 | 확정(위임, 2026-11-09) |
| D-44 | 응답 필드 이름은 `cancelled_by`(기존 `cancelled_at`과 같은 형태). 내 목록 항목과 취소 응답에만 추가, 기존 필드 불변. 점주 목록·생성 응답은 불변 | R15, 호환성 | 확정(위임, 2026-11-09) |
| D-45 | "픽업 시간 지남"은 저장하지 않고 화면이 `pickup_end`로 계산(DB·API 변경 없음) | 사용자 결정 2026-11-09 | 확정 |

정합 이슈

| # | 대상 | 내용 |
| --- | --- | --- |
| C-22 | `.claude/skills/db-schema/schema.sql`, `SKILL.md` (R14) | 16.3 컬럼·CHECK 반영과 ERD(`pickup_reservations`)에 `cancelled_by` 추가. 이 작업은 설계만 하므로 아직 반영하지 않았다. `.claude/` 변경이라 사용자 승인 필요 |
| C-23 | `docs/reference/reservations.md` | 16.5 명세 변경. 코드와 같은 변경에서 갱신(R15) |
| C-24 | 개발·테스트 DB | 16.3 ALTER를 코드 배포 전에 적용(사용자). 미적용이면 예약 API 전체가 컬럼 없음 오류 |
| C-25 | `tests/payments/test_integration.py` | `.cancel(` 직접 호출이 있으면 새 시그니처로 수정 필요(범위 확장, 16.9) |

질문 목록과 임시 기본값(위 확정 외에 남은 것)

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 |
| --- | --- | --- | --- | --- |
| Q-37 | 관리자 강제 탈퇴를 `SYSTEM`과 구분해(`ADMIN`) 기록할지 | D-42 | 구분하지 않음(`SYSTEM`) | 화면 노출 없음, 포트 변경 회피. 값 상수는 `rules.py`와 enum 한곳이라 나중에 바꾸기 쉽다 |
| Q-38 | `docs/reference/README.md`에 취소 주체 값 표를 둘지 | 16.5 | 두지 않고 `reservations.md` 한 곳에만 쓴다 | "정본은 하나" 원칙(AGENTS.md) |
| Q-39 | 내 목록 항목에 `cancelled_at`도 추가할지(화면이 취소 시각을 보여야 하면) | 현재 목록 항목에 없음 | 추가하지 않음(이번 요구는 취소 주체만) | 요구 범위, 필요하면 같은 방식으로 추가 |
| Q-40 | `SYSTEM`/`null`을 화면이 어떻게 표시할지 | 16.1 | 둘 다 "취소됨"(구분 없음) | `SYSTEM`은 노출되지 않음, `null`은 주체 불명 |

### 16.11 불변 규칙 점검

R1(`cancel_actor.py`·`pickup_reservation.py`는 표준 라이브러리만), R2·R4(레포지토리는 도메인 객체만, `CancelActor` 변환은 `_to_domain`), R3(주체 검증·상태 전이는 엔티티 `cancel`, 서비스는 상수를 넘기기만), R5·R13(commit 위치·트랜잭션 불변), R6·R7(새 예외 없음, 도메인 `ValueError`는 기존 400 `VALIDATION_ERROR`), R8~R10(추상 메서드 목록 불변), R11·R12(타 모듈 포트·조립 불변, 새 import 방향 없음), R14(models와 schema.sql·SKILL.md를 함께 고쳐야 함: C-22 승인 전에는 불일치 상태가 되므로 7단계를 같은 PR에서 처리), R15(응답은 필드 추가만, 명세 C-23), R16(테스트를 약하게 하지 않음, DB 테스트는 ALTER 후 실행). 충돌하는 요구 없음.

