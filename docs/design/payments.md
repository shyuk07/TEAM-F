# payments 모듈 설계안 (결제·환불)

- 작성 기준일: 2026-11-03, 브랜치 `feature/payments`
- 대상: `src/payments` (`payments`, `refunds` 테이블)
- 기준 문서: `docs/reference/payments.md`, `docs/reference/README.md`, `docs/reference/reservations.md`, `.claude/skills/db-schema/{SKILL.md,schema.sql}`, `.claude/skills/layer-implementation/{SKILL.md,testing.md}`, `.claude/skills/layer-check/SKILL.md`
- 이 문서는 설계만 담습니다. 코드는 수정하지 않았습니다.
- **임시 기본값은 확정이 아니라 제안입니다.** 모두 `payments/domain/rules.py` 한 파일(또는 enum)에 모아 나중에 바꾸기 쉽게 합니다.
- **결정 현황은 8.1절(결제 담당 결정)과 8.2절(팀 답변 반영)을 기준으로 합니다.** 본문의 "제안", "승인 대기" 표현보다 8.1·8.2절이 우선합니다.

---

## 0. 차단 이슈

실행해서 확인한 결과입니다.

| # | 확인 명령 | 결과 | 의미 / 해결 |
| --- | --- | --- | --- |
| B-1 | `(cd src && uv run python -c "import main")` | `import main OK` | 현재 코드는 불러와집니다. |
| B-2 | `uv run python -c "import jwt, passlib, sqlalchemy, asyncpg, fastapi, httpx, anyio"` | 모두 설치됨 (fastapi 0.162.0) | 새 의존성 필요 없음. `Form`/`File`을 쓰지 않아 `python-multipart`도 불필요(`import multipart` 실패 확인, 영향 없음). |
| B-3 | `.env.example` 확인 | `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | payments가 새로 요구하는 키 없음. |
| B-4 | `python .claude/skills/layer-check/check_layers.py` | **위반 4건** (아래) | 이 설계안의 4절·5절에서 해결합니다. |
| B-5 | `uv run pytest -m "not db" -q -rs` | 73 passed, 24 deselected | 현재 `tests/payments/test_payments_api.py`는 통과하지만 헤더 인증(`X-User-Id`), `/api/v1` 접두사에 묶여 있어 리팩터링하면 전부 다시 써야 합니다. |
| B-6 | `uv run pytest -m db -q -rs` | 전부 skip (`sssssss`) | 로컬 PostgreSQL(`docker compose up -d`)이 꺼져 있음. DB 테스트는 DB를 켠 뒤 `-rs`로 확인해야 완료입니다. |
| B-7 | `src/reservations/**`, `src/catalog/**`, `src/stores/**` 확인 | **모든 `.py`가 0바이트** (폴더 구조만 있음) | 예약·상품·상점 테이블, 서비스, 모델이 아직 없습니다. `payments.reservation_id`의 FK 대상(`pickup_reservations`)도 없어 지금은 FK를 선언할 수 없습니다. |
| B-8 | `src/main.py` 확인 | auth, payments의 models와 router만 등록 | 예약·카탈로그·상점 모델은 `create_all` 전에 import되지 않음. |

`layer-check` 위반 4건:
1. `payments/infrastructure/repositories.py:7` → `payments.application` 참조 (`ConflictError`)
2. `payments/infrastructure/reservation_stub.py:10` → `payments.application` 참조 (`ReservationInfo`)
3. `payments/presentation/dependencies.py:10` → `payments.infrastructure` 참조 (`SqlAlchemyPaymentRepository`)
4. `payments/presentation/dependencies.py:11` → `payments.infrastructure` 참조 (`InMemoryReservationGateway`)

**차단 해결 방법 요약**
- 새 의존성 추가 없음. `pyproject.toml` 변경 없음.
- 예약 모듈이 비어 있어서 payments는 `ReservationPort`(Protocol)와 임시 메모리 구현으로 먼저 구현합니다(6절).
- 개발 DB에 이미 옛 `payments`/`refunds` 테이블이 `create_all`로 만들어져 있다면 컬럼이 바뀌어도 `create_all`은 변경하지 않습니다. 설계안 적용 때 개발 DB의 두 테이블을 지우고 다시 만들어야 합니다(팀 공용 DB가 아닌 로컬 기준).

---

## 1. 명세 분석

### 1.1 엔드포인트 (docs/reference/payments.md)

| # | Method | URI (제안) | 권한 | 요청 | 응답 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | POST | `/v1/payments` | 회원(본인 예약) | `{reservation_id}` | `{id, reservation_id, amount, status, paid_at}` | 201 | 400 결제할 수 없는 예약 / 401 / 404 예약 없음 / 409 이미 결제된 예약 / 422 / 500 |
| 2 | GET | `/v1/payments/{payment_id}` | 회원(본인 결제) | 없음 | 위와 같은 5개 필드 | 200 | 401 / 403 조회 권한 없음 / 404 / 422 |
| 3 | POST | `/v1/payments/{payment_id}/refunds` | 회원(본인 결제) | `{reason}` (필수, 최대 200자) | `{id, payment_id, refund_amount, penalty_amount, status}` | 201 | 400 환불할 수 없는 결제 / 401 / 403 환불 처리 권한 없음 / 404 / 409 이미 환불 처리된 결제 / 422 / 500 |
| 4 | GET | `/v1/refunds/{refund_id}` | 회원(본인 환불) | 없음 | `{id, payment_id, refund_amount, penalty_amount, status, completed_at}` | 200 | 401 / 403 / 404 / 422 |

URI는 노션에 없고 reference 문서가 제안한 값입니다(README "URI를 정한 규칙"). 목록 API는 payments에 없으므로 페이지네이션도 없습니다.

### 1.2 포인트 정책 (README, payments 서비스가 내부 처리)

| point_type | 시점 | amount |
| --- | --- | --- |
| `USE` | 결제 요청 시 | 음수, 100P 단위, 잔액 이하 |
| `EARN` | 결제 승인(`READY` → `PAID`) 직후 | 결제 금액 × 1% (소수점 버림) |
| `RESTORE` | 환불 시 | `total_price − payments.amount` |
| `REVOKE` | 환불 시 | 결제 금액 × 1%, 잔액 한도 |

auth에 `use_points`, `earn_points`, `restore_points`, `revoke_points`(모두 `commit=False` 지원)가 이미 있어서 payments가 바로 쓸 수 있습니다.

### 1.3 사용자가 보여준 노션 원본과 docs/reference의 차이

본문(요청·응답·에러 코드)은 같습니다. 차이는 아래와 같습니다.

| # | 항목 | 노션(사용자 제공) | docs/reference | 영향 |
| --- | --- | --- | --- | --- |
| 1 | URI | payments API에는 URI가 없음 | `/v1/payments`, `/v1/payments/{id}/refunds`, `/v1/refunds/{id}`를 **제안** | 팀 확정 필요 |
| 2 | 결제 요청 본문 | `{reservation_id}`만 | `use_point`(선택, 100 단위) 추가를 "확인 필요"로 제안 | 포인트 `USE`를 어디서 입력받는지 결정 필요 |
| 3 | 500 에러 | 없음 | 결제 요청, 환불 요청에 `500 서버 오류` 추가 | 별도 코드 불필요(전역 기본) |
| 4 | 환불 응답 필드 설명 | 결제 조회 설명이 복사됨 | 응답 예시에 맞게 정정, `completed_at` 포함 여부를 "확인 필요"로 남김 | POST 응답에 `completed_at`을 넣을지 결정 필요 |
| 5 | 포인트 정책 | 포인트 내역 조회 페이지에만 있음 | README에 표로 옮기고 payments 서비스 담당이라고 명시 | payments가 포인트 4종 처리 |
| 6 | 상태 값 | 결제 `PAID`, 환불 `COMPLETED`만 등장 | `READY`, `PAID`(+실패?), 환불 `COMPLETED`(+?)로 정리 | 실패·환불 상태 값 결정 필요 |
| 7 | 에러 형식 | auth만 `success/error_code/message` | 전역 핸들러로 통일 제안 | 구현됨(`error_handlers.py`) |
| 8 | 422 | payments는 422 | 같음. 단 README 공통 확인 3번에 "auth는 400, FastAPI는 422" 불일치를 적음 | 아래 D-17 |
| 9 | 예약 취소 | "환불 관련 처리는 결제·환불 도메인과 연동" | 같음 + "취소 시 재고를 되돌리고 `stock_log` 양수 기록" 구현 참고 추가 | 예약 취소와 환불의 호출 방향 결정 필요 |
| 10 | 예약 취소 에러 | 409 이미 취소되었거나 취소 불가 | 같음 | |

### 1.4 명세에 실제로 없는지 확인한 항목

`docs/reference/*.md`를 읽고 확인했습니다. 아래는 모두 명세에 정의가 없거나 "확인 필요"로 남아 있습니다. 8절의 결정 목록(D-xx)으로 옮겼습니다.
- 위약금 계산 규칙: payments.md "취소 정책에 따라"만 있고 구체 규칙 없음(README 확인 필요 23번).
- 환불 요청 권한 주체: 권한 열에 "회원(본인 결제)"만 있음. 상점주·관리자 가능 여부는 없음.
- 부분 환불: 요청 본문에 금액 필드가 없음(= 전액 기준 환불만 가능해 보임). 스키마는 1:N이라 "확인 필요".
- 환불 후 예약·재고 처리와 순서: payments.md, reservations.md 모두 "확인 필요".
- 상점주 사유 전액 환불: catalog.md 12절에 한 줄. 호출 방식 없음.
- 결제 실패 표현: 결제 상태 실패 값, 실패 응답 형식 없음.
- 타인 예약 결제 시 응답: "403이 없음"이라고 명시.

---

## 2. 테이블 / ERD (db-schema 기준)

```
users 1─N pickup_reservations 1─N payments 1─N refunds
                (reservations)       (payments 모듈)
```

`payments`, `refunds`는 payments 모듈이 소유하고, `pickup_reservations`는 reservations 모듈 소유입니다. 다른 모듈의 모델 클래스는 import하지 않고 `ForeignKey("pickup_reservations.id")` 문자열로만 연결합니다.

### 2.1 schema.sql 기준 컬럼

| 테이블 | 컬럼 | 타입 | 제약 |
| --- | --- | --- | --- |
| `payments` | `id` | UUID | PK, `gen_random_uuid()` |
| | `reservation_id` | UUID | NOT NULL, FK → `pickup_reservations.id`, 인덱스 `ix_payments_reservation_id` |
| | `amount` | INTEGER | `CHECK (amount >= 0)` |
| | `status` | VARCHAR(30) | 값 제약 없음(확인 필요) |
| | `provider_payment_id` | VARCHAR(255) | 모의 PG 결제 번호 |
| | `created_at` | TIMESTAMPTZ | NOT NULL, `now()` |
| | `paid_at` / `failed_at` | TIMESTAMPTZ | |
| | `failed_response` | JSONB | |
| `refunds` | `id` | UUID | PK |
| | `payment_id` | UUID | NOT NULL, FK → `payments.id`, 인덱스 |
| | `refund_amount`, `penalty_amount` | INTEGER | 각 `CHECK (>= 0)` |
| | `reason` | VARCHAR(200) | |
| | `status` | VARCHAR(30) | |
| | `created_at` | TIMESTAMPTZ | NOT NULL, `now()` |
| | `completed_at` | TIMESTAMPTZ | |
| | `refund_reason` | JSONB | `reason`과 역할 구분 미정(확인 필요) |

### 2.2 현재 `infrastructure/models.py`와 schema.sql의 불일치

| # | 현재 코드 | schema.sql | 조치 |
| --- | --- | --- | --- |
| 1 | `payments.user_id` 컬럼이 있음 | 없음 | 스키마 변경 제안 S-1에서 결정. 기본은 스키마를 따라 제거 |
| 2 | `payments.reservation_id`에 `unique=True` | 인덱스만(1:N, 실패 후 재시도 고려) | UNIQUE 제거, S-2의 부분 UNIQUE 인덱스로 대체 |
| 3 | `refunds.payment_id`에 `unique=True` | 인덱스만 | 부분 환불을 하지 않는다는 임시 기본값(D-5)이면 UNIQUE 유지, 스키마 변경 제안 S-3 |
| 4 | `status String(20)` | `VARCHAR(30)` | 30으로 맞춤 |
| 5 | `created_at`, `provider_payment_id`, `failed_at`, `failed_response`, `refund_reason` 없음 | 있음 | 추가 |
| 6 | `id`에 default 없음(도메인에서 `uuid4`) | `gen_random_uuid()` | `default=uuid.uuid4, server_default=text("gen_random_uuid()")` (skill 패턴) |
| 7 | CHECK 제약 없음 | `amount >= 0` 등 | `ck_payments_amount`, `ck_refunds_refund_amount`, `ck_refunds_penalty_amount` 추가 |
| 8 | FK 없음(TODO 주석) | `reservation_id` → `pickup_reservations.id` | **예약 모델이 생긴 뒤**에 추가(6절 2단계). 지금 추가하면 `create_all`이 대상 테이블을 못 찾아 실패 |

### 2.3 스키마 변경 제안 (schema.sql, SKILL.md는 이 설계가 직접 고치지 않음)

| # | 제안 | 이유 | 영향 |
| --- | --- | --- | --- |
| S-1 | (**팀 합의: 추가 방향**, 8.2절) `payments.user_id UUID NOT NULL REFERENCES users(id)` 추가 | 결제·환불 조회의 본인 확인을 예약 모듈 없이 할 수 있음. 지금도 코드에 있는 컬럼. 예약을 거치지 않으니 조회 API 2개가 예약 모듈과 완전히 독립됨 | 승인되면 `Payment.user_id`가 도메인에 추가되고 `ReservationPort.get` 호출이 조회 API에서 사라짐. 승인 전 기본 설계는 컬럼 없이 `ReservationPort`로 소유자를 확인 |
| S-2 | `CREATE UNIQUE INDEX uq_payments_active_reservation ON payments (reservation_id) WHERE status <> 'FAILED'` | "성공한 결제는 예약당 1건"(db-schema 2절)을 DB가 마지막으로 막음. 실패 후 재시도(1:N)는 허용 | `PaymentModel.__table_args__`에 `Index(..., unique=True, postgresql_where=text("status <> 'FAILED'"))` |
| S-3 | `refunds.payment_id`에 UNIQUE | 부분 환불 없음(D-5) 가정. db-schema 2절이 "UNIQUE 추가(확인 필요)"라고 이미 적어 둠 | 이중 환불 방어 |
| S-4 | 상태 값이 확정되면 `CHECK (status IN (...))` | db-schema 5절 3항 | `payments`: READY/PAID/FAILED/REFUNDED, `refunds`: COMPLETED(+?) 제안 |
| S-5 | `payments.amount`, `status`, `refunds.refund_amount`, `penalty_amount`, `status`를 NOT NULL로 | 도메인이 항상 값을 보장하는데 DB는 NULL을 허용. NULL이 읽히면 도메인 생성자가 막지만 원인 추적이 어려움 | 낮은 우선순위 |
| S-6 | (선택) `payments.point_used INTEGER NOT NULL DEFAULT 0` | `RESTORE = reservation.total_price − payments.amount`는 예약 금액이 바뀌지 않는다는 가정에 기댐. 컬럼이 있으면 환불에서 예약을 읽지 않고도 복구액을 앎 | 기본 설계는 README 공식을 따르고 이 컬럼은 쓰지 않음 |
| S-7 | `refunds.refund_reason`(JSONB)은 쓰지 않음 | `reason`(VARCHAR 200)이 API 필드와 일치. 두 컬럼의 구분은 팀 확인(D-14) | 모델에는 컬럼을 매핑하되 도메인에서 쓰지 않음 |

---

## 3. 현재 `src/payments` 상태와 규칙 위반

테스트 통과(73개 중 payments 포함)와 규칙 준수는 별개입니다. 아래는 코드를 읽고 `layer-check`를 실행해 확인한 결과입니다.

| # | 파일 | 위반·문제 | 근거 규칙 | 해결 방향 (이 설계의 절) |
| --- | --- | --- | --- | --- |
| V-1 | `presentation/dependencies.py` | infrastructure(`SqlAlchemyPaymentRepository`, `InMemoryReservationGateway`)를 직접 import (layer-check `[의존방향]` 2건) | presentation → infrastructure 금지 | 서비스가 자기 세션으로 레포지토리를 만들고(`PaymentApplicationService(db)`), 의존성은 서비스만 반환(5절) |
| V-2 | `infrastructure/repositories.py`, `reservation_stub.py` | infrastructure가 `payments.application`을 import (`ConflictError`, `ReservationInfo`) (`[의존방향]` 2건) | infrastructure → application 금지 | 예외는 `domain/exceptions.py`로, 예약 값 객체는 `domain/reservation_snapshot.py`로 이동(4.1절) |
| V-3 | `infrastructure/repositories.py` `_commit()`, `add_payment`, `add_refund` | 레포지토리가 `commit()`/`rollback()`을 호출 | 레포지토리는 `flush()`까지, `commit()`은 서비스 | `save()`는 flush만. 서비스가 `await self.db.commit()`을 한 번 호출(4.3절) |
| V-4 | `application/service.py` `pay()` | `add_payment`(내부 commit) 후 `mark_paid`를 따로 호출 → 예약이 실제 DB가 되면 결제만 커밋되고 예약 상태는 안 바뀌는 불일치 가능 | 여러 모듈 흐름은 `commit=False` 후 마지막에 한 번 commit | 4.3절 시나리오 |
| V-5 | `application/service.py` `refund()` | `ValueError`를 `ConflictError`(409)로 변환 | 명세: "환불할 수 없는 결제"=400, "이미 환불"=409 | 전용 예외 2종으로 구분(4.1절 예외표) |
| V-6 | `application/service.py` | `PaymentError`, `NotFoundError`, `ForbiddenError`, `ConflictError`가 `Exception` 하위 클래스를 application에 정의, router가 `HTTPException`으로 변환 | 도메인 전용 예외 + 전역 핸들러, router에서 try/except 금지 | `domain/exceptions.py`와 `error_handlers.py` 한 줄(4.1, 5.4절) |
| V-7 | `presentation/router.py` | `try/except` 후 `HTTPException` 생성, 접두사 `/api/v1` | router는 예외를 그대로 올림, URI는 `/v1` | 접두사 `/v1`, try/except 제거 |
| V-8 | `presentation/router.py` | **환불 요청 `POST /v1/payments/{payment_id}/refunds`가 없음** (명세 3번) | 명세 | 5절에 추가 |
| V-9 | `application/ports.py`, `presentation/dependencies.py` | `CurrentUser`, `UserRole`을 payments가 자체 정의, 헤더(`X-User-Id`, `X-User-Role`)로 인증 흉내 | auth의 `CurrentUser`(`auth.presentation.dependencies`), `Role`(`auth.domain.user`) 사용 | 5.3절. auth는 main에 들어와 있고 `Role.OWNER`가 이미 있음 |
| V-10 | `domain/payment.py` | 생성자 검증 없음(`pay_mock`에서만 금액 검증). `Payment(amount=-1)`이 그대로 만들어짐 | 도메인 생성자 검증 | 4.1절 |
| V-11 | `domain/payment.py`, `domain/refund.py` | `PaymentStatus(str, Enum)`, 상태 전이 메서드는 `mark_refunded` 하나, `Refund.refund_mock`이 인자로 받은 `Payment`를 몰래 바꿈(부수 효과) | 전이표와 전이별 메서드, `StrEnum` | 4.1절 `Payment.refund()`가 환불을 만들고 자기 상태를 바꿈 |
| V-12 | `domain/*.py` | `id`를 `uuid4()`로 도메인에서 생성, `user_id` 필드가 스키마에 없음 | skill 패턴은 `id: UUID | None = None`, 스키마에 맞춤 | 4.1절, S-1 |
| V-13 | `models.py` | schema.sql과 불일치(2.2절) | db-schema | 2.2절 |
| V-14 | 상태 값 | 결제 `PENDING`(명세는 `READY`), 예약 `CONFIRMED`(명세에 없음, `RESERVED(?)`) | README 상태 값 표 | `READY`, `RESERVED`로 맞춤(D-8, D-9) |
| V-15 | `application/service.py` `get_refund()` | 매장주·관리자도 환불 조회 허용 | 명세는 "회원(본인 환불)"뿐 | 기본은 본인만, 확장 역할은 `rules.py` 상수 한 곳(D-4) |
| V-16 | `application/service.py` `pay()` | 고객(`CUSTOMER`)만 결제 가능 | 명세 권한은 "회원" | `CurrentUser`로 완화(D-12) |
| V-17 | 포인트 | USE, EARN, RESTORE, REVOKE가 전혀 구현되지 않음 | README 포인트 정책 | 4.3절 |
| V-18 | 응답 스키마 | `RefundResponse`에 명세에 없는 `reason` 필드 | 명세 | 제거 |
| V-19 | `tests/payments/test_payments_api.py` | 서비스 `refund()`를 `asyncio.run`으로 직접 호출, 환불 API는 검증 못 함, 헤더 인증 | testing.md | 7절로 교체 |

잘 되어 있는 점(유지): 서비스가 `ReservationGateway` Protocol에 의존해 예약 모듈 없이 동작, 금액을 서버가 예약에서 계산, 레포지토리가 도메인 객체를 반환(`*Model` 노출 없음), 동시 요청 시 `IntegrityError`를 도메인 예외로 바꾸려는 의도.

---

## 4. 4개 기능 설계 (계층별)

### 4.1 domain/ (순수 파이썬)

파일: `payments/domain/{payment.py, refund.py, reservation_snapshot.py, cancellation_policy.py, rules.py, exceptions.py}`

#### 4.1.1 `rules.py` (임시 기본값을 모으는 한 곳)

| 상수 | 임시 기본값 | 근거 |
| --- | --- | --- |
| `POINT_EARN_PERCENT` | `1` | README 포인트 정책 |
| `RESERVATION_PAYABLE_STATUS` | `"PENDING_PAYMENT"` | 예약 생성 응답 예시 |
| `RESERVATION_PAID_STATUS` | `"RESERVED"` | 예약 목록 응답 예시 (D-9) |
| `REFUNDABLE_RESERVATION_STATUSES` | `{"RESERVED"}` | 임시. 픽업 완료·취소 예약은 환불 불가 (D-7) |
| `REFUND_REASON_MAX_LENGTH` | `200` | 명세 |
| `EXTRA_VIEWER_ROLES` | `frozenset()` | 명세 "본인". 관리자·상점주 허용은 D-4 |
| `DEFAULT_CANCELLATION_POLICY` | `FullRefundPolicy()` (위약금 0원) | 규칙이 명세에 없으므로 지어내지 않음 (D-1) |

#### 4.1.2 `Payment` (엔티티)

| 속성 | 타입 | 비고 |
| --- | --- | --- |
| `id` | `uuid.UUID \| None` | 저장 전 None, 레포지토리가 채움 |
| `reservation_id` | `uuid.UUID` | 필수 |
| `amount` | `int` | 실제 결제 금액(= 예약 총액 − 사용 포인트) |
| `status` | `PaymentStatus` (`StrEnum`) | `READY`, `PAID`, `FAILED`, `REFUNDED` |
| `provider_payment_id` | `str \| None` | 모의 PG 번호 |
| `created_at`, `paid_at`, `failed_at` | `datetime \| None` | timezone 필수 |
| `failed_response` | `dict \| None` | |

생성자 검증 (`ValueError`, 400 `VALIDATION_ERROR`):
- `amount`가 `int`가 아니거나 음수 → "결제 금액은 0원 이상이어야 합니다."
- `status`가 `PaymentStatus`가 아님
- 시간 값에 timezone 없음
- 상태와 시간 불일치: `PAID`/`REFUNDED`인데 `paid_at` 없음, `FAILED`인데 `failed_at` 없음, `READY`인데 `paid_at` 있음

팩토리·행위 메서드:

| 메서드 | 하는 일 | 내는 예외 |
| --- | --- | --- |
| `Payment.request(reservation_id, total_price, use_point=0, now=None)` | `READY` 결제 생성. `amount = total_price − use_point` | `total_price`가 None/음수 → `ReservationNotPayableError`(400). `use_point < 0` 또는 `use_point > total_price` → `ValueError` (100P 단위·잔액은 auth `User.use_points`가 검증, 단위 규칙을 두 곳에 두지 않음) |
| `approve(provider_payment_id, now=None)` | `READY → PAID`, `paid_at` 기록 | `READY`가 아니면 `InvalidPaymentTransitionError`(400 `INVALID_PAYMENT_STATE`) |
| `fail(response, now=None)` | `READY → FAILED`, `failed_at`, `failed_response` 기록 | 같음 |
| `refund(penalty_amount, reason, now=None) -> Refund` | `PAID`일 때만 환불 객체를 만들고 자기 상태를 `REFUNDED`로 바꿈 | `REFUNDED` → `PaymentAlreadyRefundedError`(409). `READY`/`FAILED` → `PaymentNotRefundableError`(400 `PAYMENT_NOT_REFUNDABLE`). `penalty_amount`가 `0..amount` 밖 → `ValueError`. `reason`이 비었거나 200자 초과 → `ValueError` |
| `earn_point_amount()` | `amount * POINT_EARN_PERCENT // 100` | 없음(0이면 서비스가 적립을 건너뜀) |

상태 허용 전이표:

| 현재 \ 다음 | READY | PAID | FAILED | REFUNDED |
| --- | --- | --- | --- | --- |
| (생성) | 생성 | - | - | - |
| READY | - | `approve` | `fail` | - (400) |
| PAID | - | - | - | `refund` |
| FAILED | - | - | - | - (400, 종단) |
| REFUNDED | - | - | - | - (409, 종단) |

#### 4.1.3 `Refund` (엔티티)

| 속성 | 타입 | 검증 |
| --- | --- | --- |
| `id` | `uuid.UUID \| None` | |
| `payment_id` | `uuid.UUID` | 필수 |
| `refund_amount`, `penalty_amount` | `int` | 각각 0 이상 |
| `reason` | `str` | 공백 아님, 200자 이하 |
| `status` | `RefundStatus` (`StrEnum`) | 임시: `COMPLETED`만 (D-8). 명세에 없는 `PENDING`/`FAILED`는 확정 전까지 만들지 않음 |
| `created_at`, `completed_at` | `datetime \| None` | timezone 필수, `COMPLETED`면 `completed_at` 필수 |

환불은 모의라서 생성 즉시 `COMPLETED`입니다. 전이 메서드는 없습니다(변경 불가 이력). `refund_amount + penalty_amount == payment.amount`는 `Payment.refund()`가 보장합니다.

#### 4.1.4 `ReservationSnapshot` (값 객체, 결제에 필요한 예약 정보)

`@dataclass(frozen=True)`: `id`, `user_id`, `total_price: int | None`, `status: str`, `pickup_start: datetime | None`

기존 `application/ports.py`의 `ReservationInfo`를 domain으로 옮기고 `store_owner_id`는 뺍니다(상점주 조회 허용은 D-4 확정 후 추가).

| 메서드 | 내는 예외 |
| --- | --- |
| `ensure_payable_by(user_id)` | 본인 예약이 아니면 `PaymentAccessDeniedError`(403) (D-12). 상태가 `PENDING_PAYMENT`가 아니면 `ReservationNotPayableError`(400 `RESERVATION_NOT_PAYABLE`) |
| `ensure_viewable_by(user_id, role)` | 본인이 아니고 `role`이 `EXTRA_VIEWER_ROLES`에도 없으면 `PaymentAccessDeniedError`(403) |
| `ensure_refundable_by(user_id)` | 본인이 아니면 `RefundAccessDeniedError`(403) |
| `ensure_refundable_state()` | 예약 상태가 `REFUNDABLE_RESERVATION_STATUSES`가 아니면 `PaymentNotRefundableError`(400) (D-7) |

권한 판단(본인 여부)과 상태 판단이 모두 도메인 메서드에 있어서 서비스에는 if-else가 남지 않습니다. 소유권 확인은 auth 규칙대로 의존성이 아니라 도메인에서 `PermissionError` 하위 예외로 합니다.

#### 4.1.5 `CancellationPolicy` (위약금 계산, D-1, D-2)

```
class CancellationPolicy(Protocol):
    def penalty(self, paid_amount: int, pickup_start: datetime | None, now: datetime) -> int: ...
class FullRefundPolicy:   # 임시 기본값: 항상 0원
```
- 결과는 항상 `0 <= penalty <= paid_amount`를 만족해야 하고, 위반하면 `Payment.refund()`가 `ValueError`로 막습니다.
- 상점주 사유 취소(전액 환불)는 정책을 호출하지 않고 서비스가 `waive_penalty=True`로 위약금 0을 넘깁니다.
- 규칙이 정해지면 `TimeBasedPolicy` 같은 클래스 하나만 추가하고 `rules.py`의 기본값을 바꿉니다. catalog의 `cancel_policy.cancellable_until`(할인 상세)도 같은 정책 클래스를 써야 하므로(catalog.md 확인 필요) 공용 위치는 D-2에서 정합니다.

#### 4.1.6 `exceptions.py`

| 예외 | 상위 | HTTP | `error_code` | 명세 대응 |
| --- | --- | --- | --- | --- |
| `PaymentNotFoundError` | `LookupError` | 404 | `NOT_FOUND` | 결제 정보 없음 |
| `RefundNotFoundError` | `LookupError` | 404 | `NOT_FOUND` | 환불 정보 없음 |
| `ReservationNotFoundError` | `LookupError` | 404 | `NOT_FOUND` | 예약 정보 없음 |
| `PaymentAccessDeniedError` | `PermissionError` | 403 | `FORBIDDEN` | 결제 정보 조회 권한 없음 |
| `RefundAccessDeniedError` | `PermissionError` | 403 | `FORBIDDEN` | 환불 처리·조회 권한 없음 |
| `ReservationNotPayableError` | `ValueError` | 400 | `RESERVATION_NOT_PAYABLE` | 결제할 수 없는 예약 |
| `PaymentNotRefundableError` | `ValueError` | 400 | `PAYMENT_NOT_REFUNDABLE` | 환불할 수 없는 결제 |
| `InvalidPaymentTransitionError` | `ValueError` | 400 | `INVALID_PAYMENT_STATE` | (내부 전이 오류) |
| `PaymentFailedError` | `ValueError` | 400 | `PAYMENT_FAILED` | 모의 결제 실패 (D-11, 실패 경로를 채택할 때만) |
| `PaymentConflictError` | `Exception` | 409 | 하위 클래스의 `error_code` | 409 공통 부모. `ValueError`를 상속하면 400이 되므로 `Exception` |
| `PaymentAlreadyExistsError` | `PaymentConflictError` | 409 | `PAYMENT_ALREADY_EXISTS` | 이미 결제된 예약 |
| `PaymentAlreadyRefundedError` | `PaymentConflictError` | 409 | `PAYMENT_ALREADY_REFUNDED` | 이미 환불 처리된 결제 |

- 400/409 구분 규칙: **상태가 맞지 않아 아예 할 수 없다 = 400**, **이미 처리되어 중복이다 = 409**.
- `error_code`는 명세에 payments용 값이 없으므로 제안입니다(D-17). 응답에 반영되는 것은 `ValueError` 하위와 409 핸들러뿐이고 404·403은 고정입니다.

### 4.2 infrastructure/

#### 4.2.1 모델 (`models.py`)
2.1절 컬럼과 2.2절 정리를 따릅니다. 시간 컬럼은 `DateTime(timezone=True)`, UUID는 `UUID(as_uuid=True)`.
`__table_args__`: `ck_payments_amount (amount >= 0)`, `ck_refunds_refund_amount`, `ck_refunds_penalty_amount`, S-2 승인 시 부분 UNIQUE 인덱스, S-3 승인 시 `UniqueConstraint("payment_id")`.
FK `reservation_id → pickup_reservations.id`는 reservations 모델이 생긴 뒤 추가합니다(6절).

#### 4.2.2 레포지토리 (`repositories.py`, `commit()` 없음, `flush()`까지)

`PaymentRepository(db)`:

| 메서드 | 반환 | 설명 |
| --- | --- | --- |
| `find_by_id(payment_id, for_update=False)` | `Payment \| None` | 환불은 `for_update=True` |
| `find_active_by_reservation(reservation_id)` | `Payment \| None` | `FAILED`를 뺀 결제(READY, PAID, REFUNDED). 중복 결제 확인용 |
| `find_paid_by_reservation(reservation_id, for_update=False)` | `Payment \| None` | `PAID`만. 예약 취소 연동 환불용 |
| `save(payment)` | `Payment` | `id is None`이면 INSERT, 있으면 UPDATE(status, provider_payment_id, paid_at, failed_at, failed_response). INSERT 시 부분 UNIQUE 위반(`IntegrityError`)을 `PaymentAlreadyExistsError`로 변환 |

`RefundRepository(db)`:

| 메서드 | 반환 | 설명 |
| --- | --- | --- |
| `find_by_id(refund_id)` | `Refund \| None` | |
| `find_by_payment_id(payment_id)` | `Refund \| None` | 환불 여부 확인 |
| `save(refund)` | `Refund` | UNIQUE 위반을 `PaymentAlreadyRefundedError`로 변환 |

공통: `_to_domain()` 변환, `*Model`은 밖으로 내보내지 않음(layer-check `[레포반환]`), `find_*` 반환 타입 어노테이션 필수.
기존 `SqlAlchemyPaymentRepository` 하나를 위 둘로 나눕니다(auth의 `UserRepository`, `PointLogRepository`처럼).

`MockPaymentGateway` (`infrastructure/mock_gateway.py`): `async charge(payment) -> GatewayResult(success, provider_payment_id, failure_response)`. 임시 기본값은 항상 성공, `provider_payment_id = "mock_" + uuid4().hex`. `GatewayResult`는 domain의 값 객체(`payments/domain/gateway_result.py`)에 둡니다.

#### 4.2.3 동시성 위험 지점

| # | 지점 | 위험 | 대책 |
| --- | --- | --- | --- |
| C-1 | 같은 예약을 동시에 결제 | 이중 결제 | 예약 행 `SELECT ... FOR UPDATE`(`ReservationPort.get(for_update=True)`, reservations 구현 필요) + S-2 부분 UNIQUE 인덱스(마지막 방어선, 예약 모듈이 없어도 동작) |
| C-2 | 같은 결제를 동시에 환불 | 이중 환불, 포인트 이중 복구 | `payments` 행 `with_for_update()` + `refunds.payment_id` UNIQUE(S-3) |
| C-3 | 동시 포인트 사용·적립 | 음수 잔액 | auth가 `_locked_user`로 `FOR UPDATE` 처리(이미 구현) |
| C-4 | 예약 취소와 환불 요청이 동시에 | 교착(deadlock) | **락 순서 고정: 예약 → 결제 → (환불 INSERT) → 회원(포인트)**. 환불 API는 결제를 락 없이 읽어 `reservation_id`를 얻고, 예약을 먼저 잠근 뒤 결제를 다시 읽으며 잠금 |
| C-5 | 결제 중 예약이 취소됨 | 취소된 예약에 결제 | 예약 행 잠금으로 직렬화. 예약 락 안에서 상태를 재확인 |

### 4.3 application/ (`PaymentApplicationService`)

기존 `PaymentService`를 skill 이름 규칙에 맞춰 `PaymentApplicationService`로 바꾸는 것을 제안합니다.

```
PaymentApplicationService(
    db: AsyncSession, *,
    reservations: ReservationPort,           # 필수. 조립은 presentation/dependencies.py
    payments: PaymentRepository | None = None,
    refunds: RefundRepository | None = None,
    auth: AuthApplicationService | None = None,   # 같은 세션
    gateway: PaymentGateway | None = None,        # 기본 MockPaymentGateway
    policy: CancellationPolicy | None = None,     # 기본 rules.DEFAULT_CANCELLATION_POLICY
)
```

`application/ports.py`에는 Protocol 두 개만 둡니다(레포지토리 Protocol과 `CurrentUser`/`UserRole`은 삭제).

```
class ReservationPort(Protocol):
    async def get(self, reservation_id, *, for_update=False) -> ReservationSnapshot | None
    async def mark_paid(self, reservation_id, *, commit=False) -> None             # PENDING_PAYMENT → RESERVED
    async def cancel_for_refund(self, reservation_id, reason, *, commit=False) -> None  # 예약 취소 + 재고 복구, 환불은 호출하지 않음
class PaymentGateway(Protocol):
    async def charge(self, payment) -> GatewayResult
```

#### 4.3.1 결제 요청 `pay(user, reservation_id, use_point=0) -> Payment`

1. `snapshot = await reservations.get(reservation_id, for_update=True)`. 없으면 `ReservationNotFoundError`(404)
2. `snapshot.ensure_payable_by(user.id)`의 소유 확인 부분 → 403 (D-12)
3. `find_active_by_reservation` 결과가 있으면 `PaymentAlreadyExistsError`(409). **상태 확인보다 먼저** 합니다. 이미 결제된 예약은 상태가 `RESERVED`라서 상태 확인을 먼저 하면 409가 아닌 400이 나옵니다(현재 코드는 이 순서 때문에 메시지가 잘못 나감).
4. 예약 상태 확인(`ensure_payable_by`의 상태 부분) → `ReservationNotPayableError`(400)
5. `payment = Payment.request(reservation_id, snapshot.total_price, use_point)` (READY)
6. `use_point > 0`이면 `await auth.use_points(user.id, use_point, commit=False)` (100P 단위·잔액 오류는 `ValueError` 400)
7. `result = await gateway.charge(payment)`
   - 성공: `payment.approve(result.provider_payment_id)`
   - 실패: (D-11 채택 시) `await db.rollback()`으로 포인트 사용을 되돌린 뒤 `payment.fail(...)`을 새 트랜잭션에서 저장·`commit()`하고 `PaymentFailedError`(400). 기본 모의 게이트웨이는 실패하지 않으므로 이 분기는 게이트웨이 fake로만 검증
8. `await payments.save(payment)` (flush). 중복 INSERT면 `PaymentAlreadyExistsError` → `await db.rollback()` 후 다시 raise (auth `signup` 패턴)
9. `earn = payment.earn_point_amount()`가 0보다 크면 `await auth.earn_points(user.id, earn, commit=False)`
10. `await reservations.mark_paid(reservation_id, commit=False)`
11. **`await db.commit()` 한 번.** 5~10 중 하나라도 예외가 나면 커밋되지 않고 세션이 닫히며 롤백됩니다(V-4 해결).
12. `Payment` 반환

#### 4.3.2 결제 조회 `get_payment(user, payment_id) -> Payment`

1. `payments.find_by_id` → 없으면 `PaymentNotFoundError`(404)
2. `snapshot = await reservations.get(payment.reservation_id)` → 없으면 `ReservationNotFoundError`
3. `snapshot.ensure_viewable_by(user.id, user.role)` → 403
4. 반환. 읽기 전용이므로 `commit()` 없음. (S-1이 승인되면 2~3단계가 `payment.ensure_viewable_by(...)`로 바뀌어 예약 모듈이 필요 없어집니다.)

#### 4.3.3 환불 요청 `refund(user, payment_id, reason) -> Refund` (`POST /v1/payments/{id}/refunds`)

1. `payments.find_by_id(payment_id)` (락 없음) → 없으면 404
2. `snapshot = await reservations.get(payment.reservation_id, for_update=True)` (락 순서 1번째) → `snapshot.ensure_refundable_by(user.id)` → 403
3. `payment = await payments.find_by_id(payment_id, for_update=True)` (락 순서 2번째, 다시 읽기)
4. 환불 가능 여부 판단 순서: **404 → 403 → 409(이미 환불) → 400(환불 불가)**. 본인이 아닌 사람에게 환불 상태를 알려 주지 않기 위해 403이 먼저입니다. 409는 `Payment.refund()` 안에서 `REFUNDED`를, 400은 `READY`/`FAILED`와 `snapshot.ensure_refundable_state()`를 처리
5. `penalty = policy.penalty(payment.amount, snapshot.pickup_start, now)` (D-1, D-2)
6. `refund = payment.refund(penalty, reason)` (도메인이 검증하고 `payment.status = REFUNDED`)
7. `_apply_refund(payment, refund, snapshot)` (아래 공통 부분)
8. `await reservations.cancel_for_refund(snapshot.id, reason, commit=False)` (예약 `CANCELLED` + 재고 복구, D-6)
9. `await db.commit()` 한 번

`_apply_refund` (공통, 커밋하지 않음):
- `await refunds.save(refund)`, `await payments.save(payment)`
- 사용 포인트 복구: `used = snapshot.total_price − payment.amount`가 0보다 크면 `await auth.restore_points(snapshot.user_id, used, commit=False)`
- 적립 포인트 회수: `earned = payment.earn_point_amount()`가 0보다 크면 `await auth.revoke_points(snapshot.user_id, earned, commit=False)` (잔액 한도는 auth가 처리)

#### 4.3.4 예약 취소 연동 환불 `refund_for_cancelled_reservation(snapshot, reason, *, waive_penalty=False, commit=True) -> Refund | None`

reservations(고객 취소)와 catalog(상점주 판매 중단 일괄 취소)가 부르는 **내부용** 메서드입니다. HTTP 엔드포인트가 없습니다.

1. `payments.find_paid_by_reservation(snapshot.id, for_update=True)`. 없으면 `None`을 반환합니다(미결제 예약 취소는 환불할 것이 없음).
2. 권한 확인은 하지 않습니다(호출한 모듈이 이미 확인한 내부 호출). `snapshot`은 호출한 쪽이 이미 가진 값을 그대로 넘겨 payments가 reservations를 다시 부르지 않게 합니다(순환 import 방지, 6.3절).
3. `penalty = 0 if waive_penalty else policy.penalty(...)`
4. `refund = payment.refund(penalty, reason)` → `_apply_refund`
5. `commit=True`일 때만 `await db.commit()`. reservations가 `commit=False`로 부르고 자기 트랜잭션 끝에서 한 번만 commit합니다.

#### 4.3.5 환불 조회 `get_refund(user, refund_id) -> Refund`

1. `refunds.find_by_id` → 없으면 `RefundNotFoundError`(404)
2. `payment = payments.find_by_id(refund.payment_id)` → `snapshot = reservations.get(payment.reservation_id)`
3. `snapshot.ensure_viewable_by(user.id, user.role)` → 403 (메시지는 "환불 정보 조회 권한 없음")
4. 반환

#### 4.3.6 트랜잭션 경계 정리

| 흐름 | 락 순서 | commit 위치 |
| --- | --- | --- |
| 결제 요청 | 예약 → (포인트 회원 행) → 결제 INSERT | `pay()` 끝 한 번 |
| 환불 요청(API) | 예약 → 결제 → 환불 INSERT → 회원 | `refund()` 끝 한 번(예약 취소·재고 복구 포함) |
| 고객 예약 취소 | 예약(reservations가 잠금) → 결제 → 환불 INSERT → 회원 | reservations 서비스 끝 한 번(`commit=False`로 payments 호출) |
| 상점주 판매 중단 일괄 취소 | 예약별로 위와 동일 | catalog/reservations가 정함 |

### 4.4 presentation/ (요약, 상세는 5절)

---

## 5. presentation/

### 5.1 엔드포인트 표

| Method | URI | 인증 | 요청 스키마 | 응답 스키마 | 성공 | 에러 (400/401/403/404/409) |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/v1/payments` | `CurrentUser` | `PaymentCreateRequest` | `PaymentResponse` | 201 | 400 `RESERVATION_NOT_PAYABLE`(또는 포인트·형식 오류 `VALIDATION_ERROR`), 401, 403(D-12), 404 `NOT_FOUND`, 409 `PAYMENT_ALREADY_EXISTS` |
| GET | `/v1/payments/{payment_id}` | `CurrentUser` | - | `PaymentResponse` | 200 | 400(잘못된 UUID, 전역 핸들러), 401, 403, 404 |
| POST | `/v1/payments/{payment_id}/refunds` | `CurrentUser` | `RefundCreateRequest` | `RefundResponse` | 201 | 400 `PAYMENT_NOT_REFUNDABLE`, 401, 403, 404, 409 `PAYMENT_ALREADY_REFUNDED` |
| GET | `/v1/refunds/{refund_id}` | `CurrentUser` | - | `RefundResponse` | 200 | 400(잘못된 UUID), 401, 403, 404 |

- 명세는 형식 오류를 422로 적었지만 현재 `error_handlers.py`는 `RequestValidationError`를 400 `VALIDATION_ERROR`로 바꿉니다. 이 모듈은 전역 규칙을 따릅니다(D-17).
- `error_code` 값은 제안입니다(D-17).
- 에러 본문은 공통 형식 `{"success": false, "error_code": "...", "message": "..."}`.
- 목록 API가 없으므로 검색·필터·정렬·페이지네이션 쿼리는 없습니다.

### 5.2 스키마 (`schemas.py`)

| 스키마 | 필드 | 비고 |
| --- | --- | --- |
| `PaymentCreateRequest` | `reservation_id: UUID`, `use_point: int = Field(0, ge=0)` | `use_point` 추가는 **팀 합의된 방향**(D-10, 8.2절). 단, 사용 단위(100P 등)는 미정. 선택 필드라서 노션 원본(`{reservation_id}`만)과 호환 |
| `PaymentResponse` | `id`, `reservation_id`, `amount`, `status`, `paid_at` | `from_attributes=True`. 명세 5개 필드 그대로 |
| `RefundCreateRequest` | `reason: str = Field(min_length=1, max_length=200)` | 명세 "최대 200자" |
| `RefundResponse` | `id`, `payment_id`, `refund_amount`, `penalty_amount`, `status`, `completed_at` | 환불 요청 응답과 조회 응답이 같은 스키마(요청 응답에도 `completed_at`이 포함됨, D-13). 현재 코드의 `reason` 필드는 제거 |

`status`는 `str`로 두고 `Field(description="READY / PAID / FAILED / REFUNDED")`처럼 설명을 적습니다. 시간은 timezone 포함 `datetime`이며 서버는 UTC로 내보냅니다(예시의 `+09:00`과 같은 시각).

### 5.3 라우터 / 의존성

- `router = APIRouter(prefix="/v1")`, `tags=["결제"]`/`["환불"]`. 서비스 호출만 하고 try/except 없음.
- 인증은 `from auth.presentation.dependencies import CurrentUser`. 현재의 `get_current_user`(헤더 흉내)와 `UserRole`/`CurrentUser`(payments 자체 정의)를 삭제합니다. 서비스에는 `auth.domain.user.User`를 넘깁니다(application이 다른 모듈의 domain을 참조하는 것은 허용).
- **조립 위치(규칙 확인 결과)**: layer-check는 presentation → infrastructure를 금지합니다. 프로젝트 스킬(`layer-implementation` 6절)의 정답 예시는 router가 `get_catalog_service(db) -> CatalogApplicationService(db)`만 만들고, 서비스가 자기 생성자에서 레포지토리를 만드는 구조입니다. 따라서 payments도 `presentation/dependencies.py`의 `get_payment_service(db)`는 아래만 합니다.
  ```
  def get_payment_service(db = Depends(get_db)) -> PaymentApplicationService:
      return PaymentApplicationService(db, reservations=<ReservationPort 구현>)
  ```
  레포지토리·게이트웨이·정책은 서비스 생성자의 기본값이 만듭니다. presentation은 `payments.application`과 `auth.presentation`만 import합니다(V-1 해결).
- `<ReservationPort 구현>`은 1단계에는 `payments/application/reservation_stub.py`의 `InMemoryReservationPort`(임시, 삭제 예정), 2단계에는 `payments/application/reservation_adapter.py`의 `ReservationAdapter(ReservationApplicationService(db))`입니다(6.3절). 둘 다 application 계층이라 presentation이 import할 수 있고, 교체 지점은 `get_payment_service` 한 줄입니다.

### 5.4 모듈 밖 변경 제안 (이 설계는 고치지 않음)

| 파일 | 변경 | 시점 |
| --- | --- | --- |
| `src/error_handlers.py` | 409 핸들러 한 줄 추가: `@app.exception_handler(PaymentConflictError)`에서 `_response(409, exc.error_code, str(exc))`, `from payments.domain.exceptions import PaymentConflictError` | 구현 시 필수. 이 파일은 src 루트 파일이라 기능 모듈의 domain만 import 가능(조건 만족). 다른 모듈의 409도 필요하므로 `common`의 공통 `ConflictError`로 합치는 것도 팀과 논의 |
| `src/main.py` | 1단계는 변경 없음(payments models/router는 이미 등록). 2단계에서 `from reservations.infrastructure import models as reservations_models  # noqa: F401`가 `create_all` 전에 import되어야 FK가 동작 | 예약 모델이 생길 때 |
| `.claude/skills/db-schema/{SKILL.md,schema.sql}` | S-1~S-7 중 승인된 항목 반영 (두 파일을 함께 수정) | 스키마 담당 승인 후 |
| `tests/` | 기존 `tests/payments/test_payments_api.py` 교체(7절) | 구현 시 |

---

## 6. 예약 도메인 연결

### 6.1 연결 지점

| # | 연결 지점 | payments가 필요로 하는 것 | reservations(다른 팀원)가 제공해야 할 것 |
| --- | --- | --- | --- |
| R-1 | 예약 조회 | 결제 대상 예약의 `id`, `user_id`, `total_price`, `status`, 위약금 계산용 `pickup_start`. 결제·환불 시 행 잠금 | `get_reservation(reservation_id, for_update=False)`. `pickup_start`는 `pickup_reservations`에 컬럼이 없고 `discount_offers.pickup_start`에 있으므로 예약 서비스가 catalog 서비스를 거쳐 채워 줘야 함 |
| R-2 | 결제 후 예약 상태 변경 | `PENDING_PAYMENT → 결제 완료 상태`를 **같은 트랜잭션**에서 변경 | `mark_paid(reservation_id, *, commit=False)`. 결제 완료 상태 이름 확정(D-9). `pickup_code`를 이때 발급할지(reservations 확인 필요 18번, D-18) |
| R-3 | 예약 취소 시 환불 호출 | 결제된 예약이면 환불 | reservations의 취소 서비스가 상태를 `CANCELLED`로 바꾸고 재고를 복구한 뒤 `PaymentApplicationService(db).refund_for_cancelled_reservation(snapshot, reason, commit=False)`를 호출하고 한 번만 commit |
| R-4 | 환불 API가 예약을 취소 | 환불 후 예약 `CANCELLED` + 재고 복구 | `cancel_for_refund(reservation_id, reason, *, commit=False)`: 이미 `CANCELLED`면 오류 없이 통과(멱등), 환불을 다시 호출하지 않음 |
| R-5 | 위약금 계산 주체 | 정책 입력(결제 금액, 픽업 시작, 현재 시각) | 임시 기본값: **payments가 계산**(명세가 환불 API에 "위약금을 계산"이라 적었고, 두 진입점(R-3, R-4)이 같은 계산을 쓰게 하려는 목적). 현재 코드 주석은 "예약 쪽에서 계산해서 넘겨줌"이라 반대 (D-2) |
| R-6 | FK | `payments.reservation_id → pickup_reservations.id` | `pickup_reservations` 모델(`PickupReservationModel`) + main.py의 models import. 그 전에는 FK 선언 불가 |
| R-7 | 상점주 사유 일괄 취소 | `waive_penalty=True`로 전액 환불 | catalog의 `close_offer(cancel_reservations=True)`가 예약별 취소 → 4.3.4 호출 |
| R-8 | 미결제 예약 만료 | 결제 제한 시간이 있다면 만료된 예약 결제는 400 | reservations 확인 필요 항목(재고 반환 시점). 예약 상태가 `EXPIRED`류로 바뀐다면 `RESERVATION_PAYABLE_STATUS` 외의 상태는 모두 400이라 payments는 변경 없음 |

### 6.2 상태 흐름 (제안)

```
예약:  PENDING_PAYMENT --결제 성공--> RESERVED --픽업--> PICKED_UP
            |                            |
            +--- 취소 ------------------>+--- 취소(+환불) ---> CANCELLED
결제:  READY --approve--> PAID --refund--> REFUNDED          (READY --fail--> FAILED)
```
예약 상태 값은 reservations 담당이 확정합니다. payments는 `rules.py`의 상수만 바꾸면 됩니다.

### 6.3 순환 의존 방지

`reservations.application`이 `payments.application`을 import하고(취소 → 환불), payments도 예약 정보가 필요해서 서로 import하면 순환이 생깁니다. 제안하는 방향은 아래와 같습니다.

- `payments.application.service`는 **reservations를 import하지 않습니다.** `ReservationPort`(Protocol)만 알고, 환불 연동 호출(4.3.4)은 호출자가 `snapshot`을 넘겨 줍니다.
- 실제 어댑터 `ReservationAdapter`(`payments/application/reservation_adapter.py`)만 `reservations.application.service`를 import합니다. 이 어댑터는 `payments.application.service`를 import하지 않으므로 그래프에 순환이 없습니다(`reservations.application → payments.application`, `payments.presentation → reservation_adapter → reservations.application`).
- infrastructure에서 다른 모듈의 application을 import하는 것은 layer-check가 막으므로 어댑터는 application 계층에 둡니다.
- 서비스를 서로 기본 생성하면 무한 재귀가 되므로 `reservations`는 `ReservationPort`를 필수 인자로 받고 기본 생성하지 않습니다.

### 6.4 지금 구현 가능 / 다른 팀원 필요

| # | 작업 | 지금 가능? | 필요한 것 |
| --- | --- | --- | --- |
| 1 | domain 전체(`Payment`, `Refund`, `ReservationSnapshot`, `CancellationPolicy`, 예외, `rules.py`) + 도메인 단위 테스트 | 가능 | 없음 |
| 2 | 모델·레포지토리(FK 없이) + DB 테스트 | 가능 | 로컬 PostgreSQL. `reservation_id`가 FK가 아니라 임의 UUID로 테스트 가능 |
| 3 | `MockPaymentGateway` | 가능 | 없음 |
| 4 | 서비스(`pay`, `get_payment`, `refund`, `get_refund`, `refund_for_cancelled_reservation`) + fake 주입 서비스 테스트 | 가능 | `ReservationPort`는 fake로 대체 |
| 5 | 포인트 `USE`/`EARN`/`RESTORE`/`REVOKE` 연동 | 가능 | auth에 이미 `commit=False` 메서드가 있음 |
| 6 | 스키마·라우터 4개(환불 요청 포함), auth 인증(`CurrentUser`) 교체, `/v1` 접두사 | 가능 | auth는 main에 있음. `error_handlers.py` 409 한 줄(5.4절) |
| 7 | layer-check 위반 4건과 V-1~V-19 해결 | 가능 | 없음 |
| 8 | API 테스트(서비스·인증 override) | 가능 | 없음 |
| 9 | Swagger 수동 확인용 임시 메모리 예약 | 가능(임시) | 1단계에서만. 2단계에서 삭제 |
| 10 | 위약금 규칙 구현(`TimeBasedPolicy`) | 대기 | 당분간 위약금 0원(`FullRefundPolicy`)으로 팀 합의(8.2절). 실제 규칙과 계산 담당(D-2)은 미정 |
| 11 | 실제 `ReservationPort` 어댑터 | **불가** | reservations 서비스의 R-1, R-2, R-4 메서드 |
| 12 | `payments.reservation_id` FK, 교차 모듈 DB 테스트 | **불가** | `pickup_reservations` 모델(R-6), main.py import |
| 13 | 예약 취소 → 환불 자동 호출 | **불가** | reservations의 취소 서비스(R-3) |
| 14 | 상점주 판매 중단 일괄 환불 | **불가** | catalog + reservations(R-7) |
| 15 | 결제 시 예약 행 `FOR UPDATE`, `pickup_start` 제공 | **불가** | reservations + catalog |
| 16 | 미결제 예약 만료 처리 | **불가** | reservations 결정(R-8) |
| 17 | `payments.user_id`(S-1) | 가능(방향 합의) | 팀이 추가 방향에 합의(8.2절). `schema.sql`·`SKILL.md` 반영 후 구현하면 #2, #4의 조회 API가 예약 의존 없이 완성 |

**구현 순서 제안** (skill의 domain → infrastructure → application → presentation → main.py → 테스트 순서)
1. (1단계, 지금) 위 1~9번을 `rules.py`, `domain`, `models`, `repositories`, `service`, `schemas`, `router` 순서로 구현하고, 각 단계에서 도메인 테스트를 먼저 씁니다. 마지막에 `python .claude/skills/layer-check/check_layers.py`, `cd src && uv run python -c "import main"`, `uv run pytest -rs`.
2. (2단계, reservations 완성 후) `reservation_stub.py` 삭제, `ReservationAdapter` 추가, `get_payment_service` 한 줄 교체, FK 추가, 계약 테스트(7.6절) 실행, 교차 모듈 DB 테스트 추가.

---

## 7. Mock 데이터를 활용한 테스트 방법 (testing.md 규칙)

공통: 비동기 테스트는 `pytest.mark.anyio` + 파일마다 `anyio_backend` fixture(`"asyncio"`)를 둡니다(`pytest-asyncio`는 없음, `@pytest.mark.asyncio` 금지). 전용 예외 클래스로 확인하고(`pytest.raises(PaymentNotFoundError)`), `LookupError` 같은 넓은 클래스로 확인하지 않습니다. 에러 응답은 본문 전체를 비교합니다.
파일은 `tests/payments/`에 두고 `__init__.py`는 이미 있습니다.

### 7.1 공용 fake (`tests/payments/fakes.py` 또는 `conftest.py`)

여러 테스트 파일이 같이 쓰므로 testing.md 안내(모듈 conftest에 둠)에 따라 한 곳에 둡니다.

| fake | 역할 |
| --- | --- |
| `FakeSession` | `commits`, `rollbacks` 횟수만 셈 |
| `FakePaymentRepository` | 메모리 dict. `find_by_id`, `find_active_by_reservation`, `find_paid_by_reservation`, `save`. 실제 DB의 부분 UNIQUE를 흉내 내어 같은 예약의 `FAILED`가 아닌 결제가 이미 있으면 `PaymentAlreadyExistsError` |
| `FakeRefundRepository` | 같은 `payment_id`의 환불이 있으면 `PaymentAlreadyRefundedError` |
| `FakeReservationPort` | `add(user_id, total_price, status, pickup_start)`로 mock 예약 생성. `mark_paid`, `cancel_for_refund` 호출과 `commit` 인자를 기록. 실패 주입(`raise_on_mark_paid`) 지원 |
| `FakeAuth` | `use_points`, `earn_points`, `restore_points`, `revoke_points` 호출(user_id, amount, commit)을 기록. 잔액 부족 주입 지원 |
| `FakeGateway`, `FailingGateway` | 성공·실패 결과 반환 |
| `FixedPolicy(n)` | 위약금을 `n`으로 고정. 시간 계산 없이 위약금 로직을 검증 |
| 고정 시각 | `now`를 인자로 주입 |

mock 데이터 예: 예약 12,000원, 사용자 A/B, 상점주 O, 픽업 시작 2026-10-29 18:00. 기존 `reservation_stub.py`의 데모 UUID는 Swagger 수동 확인용이고 테스트에는 `uuid4()`를 씁니다.

### 7.2 도메인 단위 테스트 (`test_domain.py`, DB 없음, 동기 함수)

- `Payment`: 음수 금액·naive datetime·상태/시간 불일치가 `ValueError`
- `Payment.request`: `use_point` 계산(12,000 − 2,000 = 10,000), `use_point > total_price` 거부, `total_price`가 None이면 `ReservationNotPayableError`
- 전이표를 `parametrize`로 전부 검증: 허용 3개(READY→PAID, READY→FAILED, PAID→REFUNDED)와 나머지 거부
- `refund()`: PAID 성공(금액 합계 일치), REFUNDED → 409 예외 클래스, READY/FAILED → 400 예외 클래스, 위약금 범위 밖 `ValueError`, 사유 공백·201자 거부
- `earn_point_amount`: 99 → 0, 100 → 1, 12,345 → 123 (버림)
- `ReservationSnapshot`: 본인·타인(403), 상태(400), `EXTRA_VIEWER_ROLES` 동작
- `CancellationPolicy`: 기본 0원, `FixedPolicy` 범위
- 예외 계층: `ValueError`/`PermissionError`/`LookupError`를 상속하고 `PaymentConflictError`는 `ValueError`를 상속하지 않음(상속하면 409가 400으로 바뀜)

### 7.3 서비스 테스트 (`test_service.py`, fake 주입, DB 없음)

- 결제 성공: `commits == 1`, 호출 순서(`use_points → charge → save → earn_points → mark_paid`), `mark_paid`가 `commit=False`로 불림, 포인트 `commit=False`
- **원자성 회귀 테스트**: `FakeReservationPort`가 `mark_paid`에서 예외를 내면 `commits == 0`(V-4)
- 에러 순서: 예약 없음 404 → 타인 403 → 중복 409 → 상태 400. 특히 이미 결제된 예약(상태 `RESERVED`)이 400이 아닌 409
- 포인트 사용: 잔액 부족·100 단위 위반이 `ValueError`이고 결제가 저장되지 않음
- 결제 실패(`FailingGateway`, D-11): `FAILED` 저장 후 `PaymentFailedError`, 포인트는 롤백
- 동시 INSERT 충돌 흉내: `save`가 `PaymentAlreadyExistsError`를 내면 `rollbacks == 1`
- 환불: 위약금(`FixedPolicy(2000)`) → `refund_amount == 10000`, 결제 `REFUNDED`, 예약 `cancel_for_refund` 호출, `RESTORE`/`REVOKE` 금액, `commits == 1`
- 환불 에러 순서: 404 → 403 → 409 → 400, 그리고 이미 환불된 결제를 다시 환불하면 409 예외
- `refund_for_cancelled_reservation`: 결제 없음 → `None` 반환, `waive_penalty=True` → 위약금 0, `commit=False` → `commits == 0`
- 조회 권한: 본인 성공, 타인 403(결제·환불 각각)

### 7.4 API 테스트, DB 없음 (`test_api.py`)

- `app.dependency_overrides[get_payment_service] = lambda: service`(fake 주입 서비스), `app.dependency_overrides[auth.presentation.dependencies.get_current_user] = lambda: User(...)`로 로그인 사용자 주입. `CurrentUser`는 이 의존성에 기대므로 override가 먹습니다. fixture에서 `dependency_overrides.clear()`
- 엔드포인트마다 성공 1건과 대표 에러 1건 이상. 응답 본문 필드를 명세와 비교(`{id, reservation_id, amount, status, paid_at}` 등. 환불 응답에 `reason`이 없는지도)
- 토큰 없음 → 401(override 하지 않은 별도 테스트. 토큰이 없으면 DB에 닿기 전에 `AuthenticationError`)
- 잘못된 UUID 경로값 → 400 `VALIDATION_ERROR`(전역 핸들러)
- 409 응답이 `{"success": false, "error_code": "PAYMENT_ALREADY_EXISTS", ...}`인지(핸들러 한 줄 추가를 검증하는 테스트)
- `error_handlers.py`가 바뀌므로 `tests/test_error_handlers.py` 쪽에 409 핸들러 케이스를 추가할지 팀에 제안

### 7.5 API + DB 테스트 (`test_api_db.py`, `@pytest.mark.db`)

testing.md의 `session_factory`/`client` fixture 패턴을 그대로 씁니다. skip은 `OSError`(서버에 닿지 못함)로만 좁히고 `-rs`로 이유를 확인합니다. `lastcall_test` DB가 없으면 직접 만듭니다.
- 1단계(예약 모듈 없음): `ReservationPort`는 fake를 `get_payment_service` override로 주입하고, 레포지토리·포인트(`AuthApplicationService`)는 실제 DB 사용. 토큰은 API로 가입·로그인해서 받음
- 레포지토리 왕복(시간대 포함, `Mapped` 변환), 결제 후 `users_point`·`point_log` 확인(`USE`, `EARN`)
- 동시성: 같은 예약에 `asyncio.gather`로 결제를 동시에 요청 → 정확히 1건만 201, 나머지는 409(S-2 부분 UNIQUE). 같은 결제에 환불을 동시에 요청 → 1건만 201(S-3 UNIQUE). 실패한 작업은 `await db.rollback()`
- 포인트 복구·회수: 환불 후 `users_point`가 `RESTORE`/`REVOKE`만큼 변함
- 2단계: 실제 예약 서비스로 교차 모듈 시나리오(예약 생성 → 결제 → 취소 → 환불 → 재고 복구)

### 7.6 계약 테스트 (2단계)

같은 테스트 본문을 `FakeReservationPort`와 실제 `ReservationAdapter` 둘에 모두 돌려 fake가 실제와 같은 규칙(`get`이 없으면 `None`, `mark_paid` 상태 변경, `cancel_for_refund` 멱등)을 따르는지 확인합니다. fake가 실제와 어긋나 테스트만 통과하는 위험을 줄입니다.

### 7.7 실행

```
uv run pytest -m "not db" -q          # DB 없는 테스트
uv run pytest tests/payments -rs      # 모듈 전체, skip 이유 표시
uv run pytest -m db -rs               # DB 켠 뒤. skip이면 완료가 아님
python .claude/skills/layer-check/check_layers.py   # 위반 0건이어야 함
```
보고에는 passed/failed/skipped 수와 skip 이유를 적습니다.

---

## 8. 질문 목록과 임시 기본값 (명세에 없어 결정이 필요한 항목)

임시 기본값은 확정이 아니라 **제안**입니다. 코드에서는 `payments/domain/rules.py`(상수), enum, 서비스 생성자의 기본 인자 한곳에 모읍니다.

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 |
| --- | --- | --- | --- | --- |
| D-1 | **위약금 계산 규칙** (픽업까지 남은 시간 기준 등). 명세에 구체 규칙 없음 | payments.md 3절 확인 필요, README 확인 23번, catalog 10절 | `FullRefundPolicy`: 위약금 항상 0원. 정책 클래스를 교체 가능하게 설계 | 규칙을 지어내지 않음. 예시의 2,000원/12,000원은 기준을 알 수 없음 |
| D-2 | **위약금 계산 주체와 정책 코드 위치**. payments가 계산하는지 reservations가 계산해서 넘기는지, catalog의 `cancel_policy`와 같은 규칙을 어디에 공유하는지 | payments.md(환불 API 설명), catalog.md 10절, 현재 `service.py` 주석 | payments가 `CancellationPolicy`로 계산. 공용화가 필요하면 그때 `common`으로 이동 제안 | 명세가 환불 API에 "취소 정책에 따라 위약금을 계산"이라 적음 |
| D-3 | **환불 요청 권한 주체**: 본인만인지, 상점주·관리자도 환불 처리를 할 수 있는지 | payments.md 3절 권한 열 "회원(본인 결제)", 403 "환불 처리 권한 없음" | 결제한 예약의 본인 회원만 | 명세 권한 열 |
| D-4 | **결제·환불 조회 권한**: 상점주·관리자도 볼 수 있는지 (현재 코드는 허용) | payments.md 2, 4절 "회원(본인)" | 본인만. `EXTRA_VIEWER_ROLES`를 비워 둠 | 명세. 확장 시 상수 한 줄 |
| D-5 | **부분 환불 여부**. 요청에 금액이 없고 스키마는 `refunds` 1:N | payments.md, db-schema 2절 확인 필요 | 부분 환불 없음. 결제당 환불 1건, `refunds.payment_id` UNIQUE(S-3) | 요청 본문에 금액 필드가 없음 |
| D-6 | **환불과 예약 취소의 관계·순서**: 예약 취소가 환불을 자동으로 만드는지, 고객이 환불을 따로 요청하는지, 환불 API가 예약 상태와 재고도 되돌리는지 | README 확인 20번, payments.md 3절, reservations.md 3절 | 두 진입점 모두 지원. 예약 취소는 결제가 있으면 환불을 자동 호출, 환불 API는 환불 후 예약 취소·재고 복구까지 한 트랜잭션 | 명세 "환불 관련 처리는 결제·환불 도메인과 연동", 두 API가 모두 있음 |
| D-7 | **환불 가능 조건("환불할 수 없는 결제" 400)**: 결제 상태 외에 픽업 완료·취소 예약을 막을지, 픽업 시간 이후를 막을지 | payments.md 3절 에러 표(조건 설명 없음) | 결제 `PAID` + 예약 `RESERVED`(픽업 완료·취소 예약은 400). 시간 제한은 두지 않음 | 명세에 조건이 없어 최소한의 상태 규칙만 제안 |
| D-8 | **결제·환불 상태 값**: 명세는 `READY`, `PAID`(+실패?), 환불 `COMPLETED`(+?). 환불 후 결제를 `REFUNDED`로 바꿀지 | README 상태 값 표, db-schema 5절 3항 | 결제 `READY/PAID/FAILED/REFUNDED`, 환불 `COMPLETED`만. 현재 코드의 `PENDING`은 `READY`로 | 명세 `READY`, `PAID` 외에는 제안. "이미 환불 처리된 결제 409" 판정에 필요 |
| D-9 | **예약 상태 값**: `RESERVED(?)`가 결제 완료 상태인지 | README 상태 값 표, reservations.md 확인 필요 | `PENDING_PAYMENT` 결제 대기, `RESERVED` 결제 완료. 현재 코드의 `CONFIRMED`는 폐기 | 예약 목록 응답 예시 |
| D-10 | **포인트 사용 입력(`use_point`)과 적립·회수 범위**: 요청 본문에 필드가 없음. 위약금이 있을 때 적립 회수 기준 | payments.md 1절 확인 필요, README 확인 21번, 포인트 정책 | `use_point`(선택, 기본 0, 100 단위)를 요청에 추가. `EARN = 결제 금액 × 1% 버림`, `REVOKE = 같은 금액(잔액 한도)`, `RESTORE = total_price − payments.amount`. 위약금은 포인트 처리에 영향 없음 | 명세 포인트 정책 표 |
| D-11 | **모의 결제 실패를 어떻게 만들지** (`failed_at`, `failed_response` 컬럼이 있음) | payments.md 1절 확인 필요 | 모의 게이트웨이는 항상 성공. 실패는 `PaymentGateway`에 fake를 주입해 테스트만 하고, 실패 시 `FAILED` 저장 + 400 `PAYMENT_FAILED` 경로를 설계에 포함 | 스키마에 실패 컬럼이 있음 |
| D-12 | **타인 예약을 결제하려 할 때 응답** (명세에 403 없음). 그리고 결제 요청 권한이 `CUSTOMER`만인지 로그인한 모든 회원인지 | payments.md 1절 확인 필요, README 권한 표 | 타인 예약은 403(`FORBIDDEN`), 역할 제한 없이 로그인 회원(`CurrentUser`). 404로 존재를 숨기는 방식은 대안 | 명세 권한 "회원(본인 예약)", skill의 소유권 규칙은 `PermissionError`(403) |
| D-13 | **환불 요청 응답에 `completed_at` 포함 여부** | payments.md 3절 확인 필요 | 포함(조회 응답과 같은 스키마). `reason`은 응답에 넣지 않음 | 한 스키마로 관리, 추가 필드는 호환성에 영향 없음 |
| D-14 | **`refunds.reason`과 `refund_reason`(JSONB) 구분** | db-schema 5절 2항 | `reason`만 사용, `refund_reason`은 모델에 매핑만 하고 비워 둠(S-7) | API 필드가 `reason` |
| D-15 | **결제 제한 시간과 미결제 예약의 재고 반환 시점** | reservations.md 1절 확인 필요 | 결제 제한 시간 없음. `PENDING_PAYMENT`가 아닌 예약은 모두 400 | reservations 담당 결정 사항. payments는 상태 값만 확인 |
| D-16 | **상점주 사유 일괄 취소의 전액 환불 호출 방식** | payments.md 3절 확인 필요, catalog.md 12절 | `refund_for_cancelled_reservation(..., waive_penalty=True)`로 위약금 0. 공개 API에는 노출하지 않음 | 명세 "전액 환불" |
| D-17 | **오류 코드 체계**: 명세의 422(형식 오류)와 현재 전역 핸들러의 400, payments용 `error_code` 이름 | README 확인 3, 4번 | 형식 오류는 전역 핸들러대로 400 `VALIDATION_ERROR`. 4.1.6절의 `RESERVATION_NOT_PAYABLE` 등은 제안 값 | 교안의 `ValueError → 400`, 노션에 payments용 코드 없음 |
| D-18 | **`pickup_code` 발급 시점** (결제 완료 시 발급하는지) | README 확인 18번 | payments는 관여하지 않음. `mark_paid`가 필요하면 예약 쪽에서 발급 | reservations 담당 |
| D-19 | **0원 결제 허용** (전액 포인트 결제) | 명세에 없음, 스키마 `amount >= 0` | 허용(`amount >= 0`) | 스키마 CHECK |
| D-20 | **`payments.user_id` 컬럼 추가** (S-1) | 현재 코드에 있음, 스키마에 없음 | 기본은 컬럼 없음, 예약 모듈로 소유자 확인. **추가를 권장** | 지금 구현 가능한 범위를 넓힘 |

### 8.1 결정 기록 (2026-11-03, 결제·환불 담당)

payments 모듈 안에서만 영향이 있는 항목은 담당자가 확정했습니다.

| # | 결정 | 비고 |
| --- | --- | --- |
| D-3 | 환불 요청은 결제한 본인만 | 기본값과 같음 |
| D-4 | 결제·환불 조회는 본인만 | 기본값과 같음. 현재 코드의 상점주·관리자 허용은 제거 |
| D-5 | 부분 환불 없음. 결제당 환불 1건 | 기본값과 같음 |
| D-7 | 결제 `PAID` + 예약 `RESERVED`일 때만 환불. 픽업 완료·취소 예약은 400. 시간 제한 없음 | 기본값과 같음 |
| D-8 | 결제 `READY/PAID/FAILED/REFUNDED`, 환불 `COMPLETED`만 | 기본값과 같음 |
| D-11 | 모의 결제는 항상 성공. 실패 경로는 fake 게이트웨이 테스트로만 검증 | 기본값과 같음 |
| D-12 | 타인 예약 결제는 403 | 기본값과 같음. 노션 명세 결제 요청 에러 목록에 403 추가 요청 필요 |
| D-13 | **환불 요청(POST) 응답에 `completed_at`을 넣지 않음** (노션 응답 예시 그대로) | **기본값과 다름.** 요청용 응답 스키마와 조회용 응답 스키마(`completed_at` 포함)를 따로 둠 |
| D-14 | `reason`만 사용, `refund_reason`은 비워 둠 | 기본값과 같음 |
| D-19 | 0원 결제 허용 | 기본값과 같음 |

팀 확인이 필요한 항목은 8.2절에 팀 답변을 반영했습니다.

### 8.2 팀 답변 반영 (2026-11-03)

#### 합의된 항목

| # | 합의 내용 | 설계 반영 |
| --- | --- | --- |
| D-16 | 점주 사유 취소는 위약금 없이 전액 환불 | `refund_for_cancelled_reservation(..., waive_penalty=True)` (4.3.4절, R-7) |
| D-1 | 위약금은 우선 0원으로 적용 | `DEFAULT_CANCELLATION_POLICY = FullRefundPolicy()`. 정책 클래스는 교체 가능하게 유지 |
| D-10 (일부) | 결제 요청에 `use_point`를 추가하는 방향 | `PaymentCreateRequest.use_point` 선택 필드(기본 0). 사용 단위·적립률은 아래 미정 |
| D-20 / S-1 | `payments.user_id` 컬럼을 추가하는 방향 | 결제·환불 조회의 본인 확인을 `user_id`로 처리. `schema.sql`·`SKILL.md` 함께 수정 필요 |
| D-17 | API 오류 코드에 팀원 이견 없음 | 형식 오류 400 `VALIDATION_ERROR`(전역 핸들러), payments용 `error_code` 이름(4.1.6절), 409 응답 기준을 그대로 사용 |

#### 아직 미정 (임시 기본값 유지, 확정되면 `rules.py`·어댑터만 수정)

| # | 미정 항목 | 관련 절 | 현재 임시 기본값 |
| --- | --- | --- | --- |
| D-2 | **위약금 계산 담당** (payments / reservations) | 4.1, R-5 | payments의 `CancellationPolicy`가 계산 |
| D-9, R-2 | **예약 상태 변경 방식** (결제 완료 시 상태 이름, `mark_paid` 호출 방식) | 6.1, 6.2 | `PENDING_PAYMENT` → `RESERVED`, `mark_paid(commit=False)` |
| D-6, R-3, R-4 | **예약 취소와 환불의 구체적인 처리 순서** | 4.3.3, 4.3.4, 6.1 | 두 진입점 모두 지원, 한 트랜잭션에서 commit 1번 |
| D-15, D-18 | **결제 제한 시간과 픽업 코드 발급 시점** | 6.1 | 결제 제한 시간 없음, 픽업 코드는 payments가 관여하지 않음 |
| D-10 (일부) | **포인트 사용 단위와 적립률** | 1.2, 4.3.1 | 100P 단위(auth `use_points`가 검증), 적립 결제 금액 × 1% 버림 |

---

## 부록 A. 파일 목록 (구현 시 변경 대상)

| 계층 | 파일 | 변경 |
| --- | --- | --- |
| domain | `rules.py` (신규), `exceptions.py` (신규), `reservation_snapshot.py` (신규), `cancellation_policy.py` (신규), `gateway_result.py` (신규), `payment.py`, `refund.py` | 재작성 |
| infrastructure | `models.py` | 스키마 일치 |
| | `repositories.py` | `PaymentRepository`, `RefundRepository`로 분리, commit 제거 |
| | `mock_gateway.py` (신규) | |
| | `reservation_stub.py` | 1단계는 `application/reservation_stub.py`로 이동(infrastructure에서 application 타입을 쓰지 않도록), 2단계 삭제 |
| application | `ports.py` | `ReservationPort`, `PaymentGateway`만 |
| | `service.py` | `PaymentApplicationService`로 재작성 |
| | `reservation_adapter.py` | 2단계 신규 |
| presentation | `dependencies.py` | `get_payment_service`만(auth 의존성 사용) |
| | `schemas.py`, `router.py` | 4개 엔드포인트, `/v1`, try/except 제거 |
| 모듈 밖 | `src/error_handlers.py` | 409 핸들러 한 줄 |
| tests | `tests/payments/{fakes.py, test_domain.py, test_service.py, test_api.py, test_api_db.py}` | 기존 `test_payments_api.py` 대체 |
