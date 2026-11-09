# admin 모듈 설계안 (관리자 기능 9개 EP)

- 대상: 새 모듈 `src/admin` + 기존 `auth`·`stores`·`catalog`에 생기는 관리자용 도메인 규칙·서비스 메서드·스키마 변경
- 작성: 2026-11-04, `layer-architect`
- 명세 원문: 사용자가 대화에서 제공한 "관리자 API 명세" 9개 EP. 아직 `docs/reference/`에 없다(이 문서의 C2에서 반영 제안). 이 설계안의 EP 번호는 명세의 1~9번이다.
- 기준: `backend-invariants`(R1~R16), `layer-architecture`(§3.4, §4, §5, §6), `layer-implementation`, `db-schema`(`schema.sql`), 기존 설계안 `docs/design/{auth,stores,catalog,payments}.md`, 실제 코드 `src/{auth,stores,catalog,container.py,main.py,error_handlers.py}`
- 상태: 2026-11-04 사용자가 D2, D4, D10, D12, D13, D35, D39를 확정했고, **2026-11-05 사용자가 D3·2절 스키마(S1~S12)와 나머지 D(D1, D5~D9, D11, D14~D34, D36~D38)를 현재 값 그대로 확정하고, D2를 `/v1/admin`으로 변경하고, C17을 선택지 ①로 해소(D40)했다.** 11절 표의 "상태" 열이 정본이다. **2026-11-05에 새로 추가한 D41~D44는 임시(사용자 결정 필요)다.** 기존 설계안의 확정 결정(auth D-서비스생성자·D-포인트트랜잭션, stores D13·D14, catalog D13·D21·D25~D58 등)은 그대로 유지하고 인용만 한다.
- **갱신 이력 (2026-11-05)**: ① 사용자 확정 반영(D3·S1~S12·나머지 D 확정, D2 변경, D40 신설) ② D2 `/v1/admin` 반영: URI·접두사·테스트 문구 전부, auth 라우터의 기존 관리자 EP 2개와의 공존(D42, C18) ③ B-6 재작성: reservations가 구현됨, 단 재고 복구 `release()`는 no-op·환불은 `NoPaymentRefund`·payments는 `InMemoryReservationPort` → `ReservationAdminPort`를 실제 reservations 메서드로 재설계, 매장 단위 조회는 catalog 포트안(D41), 임시 구현 `NoReservationAdmin` 삭제 ④ B-7·D29: `ensure_admin` + `ADMIN_EMAIL`/`ADMIN_PASSWORD` 시드가 이미 있음 ⑤ C3 범위 정정(payments 테스트는 영향 없음) ⑥ 코드와 어긋난 곳 정정: `UserNotFoundError`는 이미 있음, `login`은 토큰 문자열을 반환(D40으로 변경), 기존 auth 관리자 EP가 `UserResponse`를 씀(D38 영향), `AuthApplicationService`에 `clock`을 container 전역으로 주입(`build_auth_service`·`tests/test_container.py` 호출 불변), 기준선 수치 재측정 ⑦ Store.close 가드는 stores.md 담당(C19 교차 참조).
- **범위 변경 (2026-11-05, 사용자): 이번 라운드는 admin만 구현한다. `src/reservations/**`·`tests/reservations/**`는 바꾸지 않는다.** ① 예약 연동은 자리표시자로 되돌림: `ReservationAdminPort` + `NoReservationAdmin`(취소 0건·예약 검사 False), container admin 구역에서 연결 ② RV1~RV5는 5.2절 "후속(reservations 담당)" 목록으로 이동 ③ 포트는 `cancel_reserved_for_user(user_id, *, reason) -> int`, `has_reserved_for_store(store_id) -> bool`로 확정(D41 보류 중에도 admin이 바뀌지 않게. catalog `list_offer_ids_of_store`는 이번 라운드에서 **삭제**) ④ D41·D43·D44 보류, D42는 임시(기본값 적용) ⑤ D35는 부분 효력(`SuspendedAllowedOwnerUser`는 auth에 만들되 픽업 router 교체는 후속). **EP 4는 예약을 취소하지 않고, EP 6의 RESERVED 검사는 항상 통과한다 = 미연계(R16)**.
- 재측정 기준선(2026-11-05): `import main`(인라인 env) 성공, `check_layers.py`(`uv run python`) 검사 110파일·위반 2건(payments)·경고 3건.
- 이 문서는 설계만 담는다. 코드·테스트·reference·다른 설계안은 수정하지 않았다. 다른 문서에 바꿀 점은 8절(정합 이슈)과 10절(모듈 밖 변경 제안)에만 적는다.

| EP | Method | URI (명세) | 한 줄 |
| --- | --- | --- | --- |
| 1 | PATCH | `/v1/admin/owners/{owner_id}/approve` | 상점주 계정 승인 (PENDING → APPROVED) |
| 2 | PATCH | `/v1/admin/owners/{owner_id}/reject` | 상점주 계정 거부 (PENDING → REJECTED, 사유 필수) |
| 3 | PATCH | `/v1/admin/users/{user_id}/suspend` | 회원 정지 (+ 상점주면 소유 상점 정지) |
| 4 | DELETE | `/v1/admin/users/{user_id}` | 강제 탈퇴 (soft delete, RESERVED 예약 취소, 상점주면 상점 폐점) |
| 5 | PATCH | `/v1/admin/stores/{store_id}/suspend` | 상점 정지 |
| 6 | PATCH | `/v1/admin/stores/{store_id}/close` | 상점 강제 폐점 (+ 판매 중 할인 종료) |
| 7 | PATCH | `/v1/admin/offers/{offer_id}/suspend` | 할인 상품 정지 |
| 8 | GET | `/v1/admin/users/{user_id}/points` | 회원 포인트 잔액·이력 조회 |
| 9 | POST | `/v1/admin/users/{user_id}/points` | 회원 포인트 지급 |

범위 제외: 상점주가 직접 폐점하는 `POST /v1/stores/{store_id}/close`는 `docs/design/stores.md`가 설계한다. admin이 그와 맞물리는 지점은 C19(교차 참조)에만 적는다.

---

## 0. 차단 이슈 (실행으로 확인)

| # | 확인 명령 | 결과 | 판정 / 해결 |
| --- | --- | --- | --- |
| B-1 | `(cd src && uv run python -c "import main")` | **실패**: `RuntimeError: DATABASE_URL 환경변수가 설정되지 않았습니다.` (`src/database.py:19`). 저장소 루트에 `.env`가 없음(`ls -a` → `.env.example`만) | 코드 결함이 아니라 로컬 환경 문제. `.env.example`을 `.env`로 복사하면 해결(README 3단계). 설계 차단 아님 |
| B-1b | 같은 명령에 `DATABASE_URL`·`JWT_SECRET_KEY`를 인라인 지정 (2026-11-05 재실행) | `main ok (with inline env)`. env 없이는 같은 `DATABASE_URL` RuntimeError | 현재 코드(auth, stores, catalog, reservations, payments 포함)는 불러와진다 |
| B-2 | `uv run python -c "import jwt, passlib, sqlalchemy, asyncpg, fastapi"` | `pkgs ok 0.162.0` | 새 의존성 필요 없음. `pyproject.toml` 변경 없음 |
| B-3 | `uv run python -c "import multipart"` | `ModuleNotFoundError` | 이 설계는 `Form`·`File`·`OAuth2PasswordRequestForm`을 쓰지 않는다(전부 JSON). `python-multipart` 불필요 |
| B-4 | `.env.example` 키 확인 (2026-11-05 재확인) | `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` + 선택 `ADMIN_EMAIL`, `ADMIN_PASSWORD`(주석) | 설계가 요구하는 새 키 없음 |
| B-5 | `PYTHONIOENCODING=utf-8 uv run python .claude/skills/layer-check/check_layers.py` (2026-11-05 재실행) | 검사 모듈 auth·catalog·payments·reservations·stores, **110개 파일**. **기존 위반 2건**: `payments\application\service.py:19`, `:20` (application → payments.infrastructure). 경고 3건(`error_handlers.py:50,54,58` 넓은 예외) | admin 범위 밖(payments). 기준선으로 기록. admin 구현 후 새 위반 0이어야 한다. 참고: 시스템 `python`(3.11)으로 실행하면 `catalog\application\views.py:9` 파싱 실패가 추가로 나온다(3.12+ 문법). **반드시 `uv run python`(3.13)으로 실행**한다. 이 환경에는 `python3`가 없다 |
| B-6 (**2026-11-05 재작성**) | `wc -c src/reservations/*/*.py`(25개 파일 43KB), `Read` `application/{service,lifecycle_service,ports,interim_stock_port}.py`, `infrastructure/{payment_refund_stub,repositories}.py`, `src/container.py`, `payments/presentation/dependencies.py` | **reservations는 구현됨**(이전 "전부 0바이트"는 사실이 아님). 그러나 ① `container.create_stock_port`는 `ReadOnlyOfferStockPort`: `release()`는 아무것도 안 하고 `False`, `reserve()`는 재고를 줄이지 않고 행을 잠그지 않음 ② `create_refund_port`는 `NoPaymentRefund`(환불·포인트 복구 없음) ③ `payments`는 `get_payment_service`에서 `InMemoryReservationPort()`를 직접 만들어 쓴다 → 실서버에서 `pickup_reservations`가 `RESERVED`로 바뀔 수 없음 ④ container는 catalog 포트 `NoReservationLookup`·`NoReservationCancel`을 계속 연결 ⑤ `pickup_reservations`에 `store_id` 컬럼 없음(`offer_id`만) ⑥ 레포지토리에 사용자·매장 단위 조회가 없음(`find_by_user`는 페이지 목록, 잠금은 `find_by_id`·`find_by_offer`만) ⑦ 기존 `lifecycle.cancel_all_for_offer`는 재고를 복구하지 않는다(reservations D-40) | **차단 아님.** **범위 변경(2026-11-05): 이번 라운드에 reservations는 바꾸지 않으므로 `ReservationAdminPort`는 임시 구현 `NoReservationAdmin`(취소 0건, 검사 False)으로 둔다.** 따라서 **EP 4는 예약을 취소하지 않고 EP 6의 RESERVED 검사는 항상 통과한다 = D12 효력 없음(미연계, R16)**. 실제 reservations 메서드 설계(RV1~RV5)는 5.2절 "후속" 목록에 남기고, 그때는 container 바인딩만 교체한다. 매장 단위 조회(⑤)는 D41(보류) |
| B-7 (**2026-11-05 재작성**) | `Grep ensure_admin\|ADMIN_EMAIL src tests`, `Read src/main.py`, `src/auth/application/service.py:83` | **ADMIN 계정 생성 경로가 있다**: `AuthApplicationService.ensure_admin`, `User.register_admin`, `main.py` `lifespan`의 `seed_admin()`(`ADMIN_EMAIL`·`ADMIN_PASSWORD`가 둘 다 설정됐을 때). `Role.for_signup`은 여전히 ADMIN을 거부. auth 라우터에 이미 `GET /v1/admin/users/{user_id}`(회원 조회)·`POST /v1/admin/token-blacklist/purge`가 있고 `AdminUser`를 쓴다 | 수동 확인은 `.env`에 두 값을 넣으면 가능. 테스트는 `ensure_admin`을 부르거나 fixture로 직접 insert(D29). `register_admin`은 새 `status` 기본값 `APPROVED`를 쓴다. 기존 관리자 EP와의 공존은 D42·C18 |
| B-11 | 같은 URI·다른 메서드의 라우터 공존 실험(`uv run python -c`, 파일 쓰기 없음): `/v1/admin/users/{u}` GET(라우터 A) + 같은 경로 DELETE(라우터 B, prefix `/v1/admin`) | GET→A 응답, DELETE→B 응답, PATCH→405 | 경로가 겹쳐도 메서드가 다르면 **충돌 없음**(Starlette는 경로만 맞는 라우트를 부분 일치로 건너뛴다). D42의 근거 |
| B-8 | 에러 핸들러 동작 실험 (scratchpad 없이 `-c`): `reason: str = Field(min_length=1)` 본문에 `""`, 경로에 잘못된 UUID | 둘 다 **400** `VALIDATION_ERROR` (`reason: String should have at least 1 character`, `path.i: Input should be a valid UUID...`) | 명세의 요청 검증 오류는 400이고 핸들러도 400이라 **상태 코드는 일치**한다(422 아님). 단 **메시지는 명세 문구("정지 사유를 입력해 주세요.")와 다르다** → 문구는 도메인 `ValueError`에서 내도록 `reason`에 Pydantic 길이 제약을 두지 않는다(D26) |
| B-9 | `httpx.Client.delete` 시그니처 / FastAPI DELETE + 본문 | `delete(url, params, headers, cookies, auth, follow_redirects, timeout, extensions)`에 본문 인자 없음. `client.request("DELETE", url, json=...)`는 FastAPI에서 본문을 받음(`{'r': 'x'}`) | EP 4는 DELETE에 JSON 본문이 있다. 라우터는 문제없고, **테스트는 `client.delete(..., json=)`이 아니라 `client.request("DELETE", ..., json=)`을 써야 한다** |
| B-10 | 개발 DB 마이그레이션 | Alembic은 `pyproject.toml` 의존성에만 있고 폴더(`alembic*`, `migrations`)는 없음. `create_all` 방식 | 2절의 컬럼 추가는 이미 만들어진 개발 DB에 반영되지 않는다. 로컬 DB를 다시 만들거나 2.4절의 `ALTER` SQL을 수동 실행해야 한다(스키마 변경을 승인받은 뒤) |

차단 이슈 요약 (2026-11-05): **구현을 막는 것은 없다. 단 주의 1건: C3의 `tests/reservations/test_api_db.py:24` `seed_offer`(OWNER 가입→상점 개설)는 D4로 깨지는데 이번 라운드에 `tests/reservations`를 못 바꾼다. `tests/helpers.py`의 `token_for(..., "OWNER")`가 상점주를 APPROVED로 만들도록 공용 헬퍼를 고치면 reservations 테스트 수정 없이 해소된다(기본 제안). 이 헬퍼 변경 자체의 승인은 사용자 확인 필요.** 2절 스키마·D3은 확정됐다. 남는 것은 (1) **미연계**: 재고 `release` no-op·`NoPaymentRefund`·payments `InMemoryReservationPort`가 남아 있는 동안 EP 4의 예약 취소는 재고 복구·환불을 하지 않는다(B-6, R16), (2) D41~D44 임시 결정에 대한 사용자 확인(11절), (3) D4는 기존 테스트의 OWNER 가입→상점 개설 헬퍼에 영향을 준다(C3). reservations.md의 W-5~W-8 구현이 먼저 끝나야 하는 것은 아니다(admin은 포트만 호출).

---

## 1. 모듈 배치 비교와 구성

### 1.1 비교 (결정 D1)

| | A. 별도 `src/admin` (오케스트레이션) | B. 각 컨텍스트에 관리자 유스케이스 분산 (auth·stores·catalog에 admin 라우터) |
| --- | --- | --- |
| 도메인 규칙 위치 | 상태 전이 규칙은 **소유 컨텍스트**의 엔티티(`User`, `Store`, `DiscountOffer`)에 둔다(R3). admin은 흐름만 조합 | 같음 |
| 다중 모듈 흐름 (3: 회원→상점, 4: 회원→예약·상점·할인, 6: 상점→할인·예약) | admin 한 곳에서 조합. admin이 **맨 위**에 있어 아무도 admin에 의존하지 않는다 | auth가 stores·reservations를 알아야 한다. auth는 모든 모듈이 의존하는 **맨 아래**(reservations·payments → auth)인데 위쪽을 부르면 방향이 뒤집힌다 |
| 생성 순환 (R12) | 없음. `create_admin_service`는 `create_auth/stores/catalog_service`를 `Depends`로 받기만 한다 | `create_auth_service → (예약 포트) → reservations 서비스 → create_auth_service`(포인트 복구) 순환 위험. stores.md D15·catalog.md D22가 이미 겪는 문제를 auth에서 반복 |
| 권한·URI | `/v1/admin` 라우터 한 파일에서(기존 auth 관리자 EP 2개는 D42) `AdminUser` 일괄 적용. 목록·문서가 한 곳 | 라우터가 3곳에 흩어지고 권한 누락 위험 |
| 단점 | 모듈이 하나 늘고, 각 컨텍스트가 관리자용 application 메서드를 노출해야 한다 | 모듈 경계는 그대로지만 위 순환·방향 문제 |
| layer-check | 기능 모듈은 4계층 폴더를 모두 가져야 한다(`check_layers.py`) → admin도 `domain/`이 필요 | 해당 없음 |

**임시 기본값: A.** 근거: `layer-architecture` §3.4(상대 상태를 바꿀 때 상대 application 서비스 호출, 호출자가 한 번 commit), §4(순환 금지), R11·R12·R13. admin 안에는 엔티티가 없다(빈약한 엔티티를 만들지 않는다, R3). admin의 domain은 `Clock` 추상 하나뿐이다(D31). 비즈니스 규칙(상태 전이·검증)은 전부 소유 컨텍스트 도메인에 있다.

admin은 다른 모듈을 **쓰는 쪽이 정의한 포트(Protocol)**로 받는다(§3.4 2행, catalog `StorePort`와 같은 방식, D30). 다른 모듈의 application 클래스·domain을 import하지 않는다(R11, catalog D23과 같은 선택).

### 1.2 구성

```
src/admin/
  __init__.py
  domain/
    __init__.py
    service.py          # Clock (ABC)                                          [R8, D31]
  infrastructure/
    __init__.py
    clock.py            # SystemClock(Clock)
    reservation_admin.py# NoReservationAdmin — 임시 구현 (B-6, C10, 후속 reservations PR이 교체)
  application/
    __init__.py
    ports.py            # AccountAdminPort, StoreAdminPort, OfferAdminPort, ReservationAdminPort (Protocol) + 결과 Protocol. 예약 포트는 이번 라운드 `NoReservationAdmin`이 만족(B-6), 후속 reservations 작업이 실제 구현으로 교체
    service.py          # AdminApplicationService (9개 유스케이스)
  presentation/
    __init__.py
    schemas.py
    dependencies.py     # provide_admin_service
    router.py           # APIRouter(prefix=ADMIN_PREFIX = "/v1/admin"), 전부 AdminUser (D2)
```

models 없음(새 테이블 없음, D28). `src/main.py`에는 router 등록만 추가한다.

---

## 2. 스키마 변경 제안 (`schema.sql`·`db-schema/SKILL.md`는 이 문서가 고치지 않는다, R14)

현재 `schema.sql`·모델에는 아래 컬럼이 **하나도 없다**(`src/auth/infrastructure/models.py`, `stores/infrastructure/models.py`, `catalog/...`와 대조). 구현 시 `schema.sql`·`db-schema/SKILL.md`·`models.py`를 함께 고친다(R14).

### 2.1 users

| # | 컬럼 | 타입·제약 | 용도 |
| --- | --- | --- | --- |
| S1 | `status` | `VARCHAR(20) NOT NULL DEFAULT 'APPROVED'`, `CONSTRAINT ck_users_status CHECK (status IN ('PENDING','APPROVED','REJECTED','SUSPENDED','WITHDRAWN'))` | 계정 상태. DEFAULT가 `APPROVED`라 기존 행(기존 상점주 포함)은 승인 상태로 유지된다(D4) |
| S2 | `approved_at` | `TIMESTAMPTZ NULL` | EP 1 |
| S3 | `rejected_reason` / `rejected_at` | `VARCHAR(500) NULL` / `TIMESTAMPTZ NULL` | EP 2 |
| S4 | `suspended_reason` / `suspended_at` / `suspended_until` | `VARCHAR(500) NULL` / `TIMESTAMPTZ NULL` / `TIMESTAMPTZ NULL` | EP 3. `suspended_until IS NULL`이면 무기한 |
| S5 | `deleted_at` / `deleted_reason` | `TIMESTAMPTZ NULL` / `VARCHAR(500) NULL` | EP 4 (soft delete). `deleted_reason`은 명세에 컬럼이 없어 **추가 제안**(D14) |

### 2.2 point_log

| # | 컬럼·변경 | 내용 |
| --- | --- | --- |
| S6 | `point_type` CHECK에 `'GRANT'` 추가 | `CHECK (point_type IN ('EARN','USE','RESTORE','REVOKE','GRANT'))`, 제약 이름 `ck_point_log_type` 유지. 관리자 지급 전용 값 (D23) |
| S7 | `reason` | `VARCHAR(500) NULL`. 지급 사유(EP 9). 시스템 이벤트(EARN/USE/RESTORE/REVOKE)는 NULL |
| S8 | `balance_after` | `INTEGER NULL`. 이후 **모든 신규 기록**이 채운다. 이미 있는 행은 NULL(소급 계산 안 함, D23) |
| S9 | `created_by` | `UUID NULL REFERENCES users (id)`, 인덱스 불필요. 관리자 ID. 시스템 이벤트는 NULL |

### 2.3 stores / discount_offers

| # | 대상 | 변경 | 내용 |
| --- | --- | --- | --- |
| S10 | `stores` | `suspended_reason VARCHAR(500) NULL`, `suspended_at TIMESTAMPTZ NULL`, `closed_reason VARCHAR(500) NULL` | `closed_at`은 이미 있음. **`status` 컬럼은 추가하지 않는다**(D16): `status`는 `closed_at`(CLOSED) > `suspended_at`(SUSPENDED) > 그 외(ACTIVE)로 계산. 대안 B(`status VARCHAR(20) CHECK` 컬럼 추가)는 `closed_at`과 이중 상태가 되어(catalog S5와 같은 문제) 채택하지 않음 |
| S11 | `discount_offers` | `suspended_reason VARCHAR(500) NULL`, `suspended_at TIMESTAMPTZ NULL`, `status` CHECK에 `'SUSPENDED'` 추가 | `CHECK (status IN ('SCHEDULED','ON_SALE','SOLD_OUT','CLOSED','SUSPENDED'))`. `is_active`는 건드리지 않는다(D19) |
| S12 | `stores.approval_at` | **변경 없음** | 이름과 달리 "개설 시각"이다(stores.md D5, `Store.open`). 상점주 계정 승인(`users.approved_at`)과 **별개**다(D6, C1) |

### 2.4 개발 DB 수동 반영용 SQL (제안, 실행하지 않음)

```sql
ALTER TABLE users ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'APPROVED';
ALTER TABLE users ADD CONSTRAINT ck_users_status CHECK (status IN ('PENDING','APPROVED','REJECTED','SUSPENDED','WITHDRAWN'));
ALTER TABLE users ADD COLUMN approved_at TIMESTAMPTZ, ADD COLUMN rejected_reason VARCHAR(500), ADD COLUMN rejected_at TIMESTAMPTZ,
  ADD COLUMN suspended_reason VARCHAR(500), ADD COLUMN suspended_at TIMESTAMPTZ, ADD COLUMN suspended_until TIMESTAMPTZ,
  ADD COLUMN deleted_at TIMESTAMPTZ, ADD COLUMN deleted_reason VARCHAR(500);
ALTER TABLE point_log DROP CONSTRAINT ck_point_log_type;
ALTER TABLE point_log ADD CONSTRAINT ck_point_log_type CHECK (point_type IN ('EARN','USE','RESTORE','REVOKE','GRANT'));
ALTER TABLE point_log ADD COLUMN reason VARCHAR(500), ADD COLUMN balance_after INTEGER, ADD COLUMN created_by UUID REFERENCES users (id);
ALTER TABLE stores ADD COLUMN suspended_reason VARCHAR(500), ADD COLUMN suspended_at TIMESTAMPTZ, ADD COLUMN closed_reason VARCHAR(500);
ALTER TABLE discount_offers DROP CONSTRAINT <기존 status CHECK 이름>;   -- 이름은 DB에서 확인 (models.py의 CheckConstraint 이름)
ALTER TABLE discount_offers ADD CONSTRAINT ck_offer_status CHECK (status IN ('SCHEDULED','ON_SALE','SOLD_OUT','CLOSED','SUSPENDED'));
ALTER TABLE discount_offers ADD COLUMN suspended_reason VARCHAR(500), ADD COLUMN suspended_at TIMESTAMPTZ;
```

주의: 기존 `status` CHECK 제약 이름은 이 설계가 확인하지 않았다(catalog `models.py` 구현을 구현자가 읽고 맞춘다).

---

## 3. 도메인 (domain/)

모든 도메인은 순수 파이썬(R1). 새 예외는 모듈 전용 클래스이고 `HTTPException`을 만들지 않는다(R6). **모든 사유(reason) 검증은 공백 제거 후 빈 값이면 명세 문구의 `ValueError`, 500자 초과면 "사유는 500자 이하여야 합니다."**(D27). 사유 검증 상수·함수는 모듈 간 공유 코드를 만들지 않으려고 각 도메인에 따로 둔다(`REASON_MAX_LENGTH = 500`이 세 곳에 중복. 값이 바뀌면 세 곳을 함께 고친다).

### 3.1 auth 도메인 확장 (`src/auth/domain/`)

#### 3.1.1 `UserStatus` / `User` 속성 추가

`UserStatus(StrEnum)`: `PENDING, APPROVED, REJECTED, SUSPENDED, WITHDRAWN`.

| 추가 속성 | 타입 | 규칙 |
| --- | --- | --- |
| `status` | `UserStatus` | 기본 `APPROVED` |
| `approved_at`, `rejected_at`, `suspended_at`, `suspended_until`, `deleted_at` | `datetime \| None` | 있으면 tz-aware |
| `rejected_reason`, `suspended_reason`, `deleted_reason` | `str \| None` | |

생성자 불변식(저장된 데이터에도 참): `PENDING`/`REJECTED`는 `role == OWNER`일 때만; `REJECTED`는 `rejected_reason`·`rejected_at` 필수; `SUSPENDED`는 `suspended_reason`·`suspended_at` 필수, `suspended_until`이 있으면 `suspended_at`보다 뒤; `WITHDRAWN`은 `deleted_at` 필수. 위반 시 `ValueError`. (`OWNER`의 `APPROVED`는 `approved_at` NULL을 허용한다: 기존 상점주 행.)

`User.register(...)`: `status = PENDING if role == OWNER else APPROVED` (D4). 그 외 입력 검증 불변.

#### 3.1.2 상태 전이표

| 현재 | 이벤트 | 다음 | 메서드 |
| --- | --- | --- | --- |
| PENDING (OWNER) | 승인 | APPROVED (`approved_at`) | `approve_owner(now)` |
| PENDING (OWNER) | 거부 | REJECTED (`rejected_reason`, `rejected_at`) | `reject_owner(reason, now)` |
| APPROVED | 정지 | SUSPENDED (`suspended_*`) | `suspend(reason, until, now)` |
| SUSPENDED | `suspended_until` 경과 | **APPROVED로 간주** (조회 시 계산, 저장은 다음 쓰기 때) | `effective_status(now)` |
| PENDING / APPROVED / REJECTED / SUSPENDED | 강제 탈퇴 | WITHDRAWN (`deleted_at`, `deleted_reason`) | `withdraw(reason, now)` |
| REJECTED | 승인·거부 | 불가 (종단. 재심사 없음) | |
| WITHDRAWN | 모든 변경 | 불가 (종단) | |
| (없음) | 정지 해제 | **EP 없음**(D10). 무기한 정지는 해제할 수단이 없다 | |

정지는 `APPROVED`만 가능하다(D36): 한 컬럼(`status`)이 승인 상태와 정지를 함께 나타내므로, 정지가 끝났을 때 돌아갈 상태를 `APPROVED` 하나로 고정하려는 선택이다.

#### 3.1.3 행위 메서드와 예외 (검사 순서가 곧 우선순위. 명세 에러 순서를 따른다)

| 메서드 | 동작 | 예외 (순서대로) |
| --- | --- | --- |
| `approve_owner(now)` | `status=APPROVED`, `approved_at=now` | ① `role != OWNER` → `OwnerNotFoundError`(404 "상점주를 찾을 수 없습니다.", D7) ② `status != PENDING` → `OwnerNotPendingError`(400 `OWNER_NOT_PENDING` "승인 대기 중인 상점주가 아닙니다.") ③ naive `now` → ValueError |
| `reject_owner(reason, now)` | `status=REJECTED`, `rejected_reason`(공백 제거), `rejected_at=now` | ① 사유: 비면 ValueError "거부 사유를 입력해 주세요." ② `OwnerNotFoundError` ③ `OwnerNotPendingError`. 명세 에러 순서(거부 사유 → 대기 아님)에 맞춰 사유 검사가 먼저 |
| `suspend(reason, until, now)` | `status=SUSPENDED`, `suspended_reason`, `suspended_at=now`, `suspended_until=until` | ① 사유 비면 "정지 사유를 입력해 주세요." ② `until`이 naive면 ValueError, `until <= now`면 `InvalidSuspensionEndError`(400 `INVALID_SUSPENSION_END` "정지 종료 시각은 현재 이후여야 합니다.") ③ `is_suspended(now)` → `UserAlreadySuspendedError`(400 `USER_ALREADY_SUSPENDED` "이미 정지된 회원입니다.") ④ `WITHDRAWN` → `UserWithdrawnError`(400 `USER_WITHDRAWN` "탈퇴한 회원입니다.") ⑤ `role == ADMIN` → `AdminAccountProtectedError`(400 `ADMIN_ACCOUNT_PROTECTED` "관리자 계정은 정지할 수 없습니다.") ⑥ `status` 가 `PENDING`/`REJECTED` → `UserNotSuspendableError`(400 `USER_NOT_SUSPENDABLE` "승인된 회원만 정지할 수 있습니다.", **명세에 없는 에러, D36**). 만료된 정지(`effective_status == APPROVED`)는 재정지 가능 |
| `ensure_withdrawable(reason)` | 부수 효과 없음 | ① 사유 비면 "탈퇴 사유를 입력해 주세요." ② `WITHDRAWN` → `UserAlreadyWithdrawnError`(400 `USER_ALREADY_WITHDRAWN` "이미 탈퇴한 회원입니다.") ③ `ADMIN` → `AdminAccountProtectedError`("관리자 계정은 탈퇴시킬 수 없습니다.") |
| `withdraw(reason, now)` | `ensure_withdrawable` 후 `status=WITHDRAWN`, `deleted_at=now`, `deleted_reason` | 위와 같음 |
| `grant_points(amount, reason)` | `users_point += amount`. 정규화된 사유를 돌려준다 | ① `amount < 1`(또는 bool/비정수) → ValueError "지급 포인트는 1 이상이어야 합니다." ② 사유 비면 "지급 사유를 입력해 주세요." ③ `WITHDRAWN` → `UserWithdrawnError` ④ `users_point + amount > POINT_MAX_BALANCE(2_147_483_647)` → ValueError "포인트 잔액이 한도를 넘습니다."(DB `INTEGER` 상한 방어, D24) |
| `effective_status(now) -> UserStatus` | `SUSPENDED`이고 `suspended_until`이 있고 `<= now`면 `APPROVED`, 아니면 `status` | |
| `is_suspended(now)` | `effective_status(now) == SUSPENDED` | |
| `ensure_can_login(now)` | 로그인 허용 확인 | `WITHDRAWN` → `InvalidCredentialsError`(401, 역할 무관, 존재하지 않는 계정처럼 보이게, D9); `is_suspended`이고 **`role != OWNER`** → `AccountSuspendedError`(403 `FORBIDDEN` "정지된 계정입니다.", D8). **정지된 OWNER는 로그인 허용**(D39 확정: 정지 기간에도 픽업 처리를 계속하기 위함, D35). **PENDING·REJECTED는 허용**(D5). 정지된 ADMIN은 정지 자체가 불가(3.1.3 `suspend`) |
| `ensure_can_authenticate(now, *, allow_suspended: bool = False)` | 보호 API 허용 확인 | `WITHDRAWN` → `AuthenticationError("유효하지 않은 토큰입니다.")`(기존 "회원 없음" 문구와 동일, `allow_suspended`와 무관하게 항상); `is_suspended`이고 `allow_suspended`가 False → `AccountSuspendedError`. **기본값 False라 모든 기존 보호 API는 정지 회원을 막는다. True는 정지된 상점주의 픽업 EP 하나만 쓴다(D35 확정, 5.5절)** |
| `ensure_approved_owner()` | 상점 개설·폐점 전 확인 | `role != OWNER` → 기존 `require_role`이 먼저 403; `PENDING` → `OwnerNotApprovedError`(403 `FORBIDDEN` "승인 대기 중인 상점주 계정입니다."); `REJECTED` → `OwnerNotApprovedError("승인이 거부된 상점주 계정입니다.")`(문구는 임시, 명세에 없음). `APPROVED`와 `SUSPENDED`는 통과(정지 회원은 `ensure_can_authenticate`에서 이미 차단) |

새 예외(auth, R6): `UserNotFoundError(LookupError)`는 **이미 `auth/domain/exceptions.py`에 있다**(404 "회원을 찾을 수 없습니다.", `get_user`·`_locked_user`가 사용 → 재사용, 새로 만들지 않음), `OwnerNotFoundError(LookupError)`, `InvalidPageError(ValueError)`(400 `INVALID_PAGE` "페이지 값이 올바르지 않습니다.") 외 위 표의 클래스. `AccountSuspendedError`·`OwnerNotApprovedError`는 `PermissionError` 하위(→ 403 `FORBIDDEN` 고정이라 `error_handlers.py` 변경 없음).

#### 3.1.4 PointLog 확장

- `PointType.GRANT` 추가. 규칙: `GRANT`는 금액 양수(EARN·RESTORE와 같은 그룹).
- 속성 추가: `reason: str | None`, `balance_after: int | None`, `created_by: uuid.UUID | None`. 여전히 불변(영속화 시 `id`·`created_at` 채우기만 허용).
- `PointLog.record(user_id, point_type, amount, balance_after, reason=None, created_by=None)`: **`balance_after`는 신규 기록에서 필수**(변경 후 `user.users_point`). 기존 호출 4곳(`use/earn/restore/revoke_points`)이 이 값을 넘기도록 auth 서비스 내부를 고친다(외부 시그니처 불변, C3). `balance_after < 0` → ValueError.

### 3.2 stores 도메인 확장 (`src/stores/domain/`)

`StoreStatus(StrEnum)`: `ACTIVE, SUSPENDED, CLOSED`.

| 추가 속성 | 타입 | 규칙 |
| --- | --- | --- |
| `suspended_reason`, `suspended_at` | `str \| None`, `datetime \| None` | 둘 다 있거나 둘 다 없음. `suspended_at` tz-aware |
| `closed_reason` | `str \| None` | `closed_at`이 있을 때만 값 가능 |
| `status` (property) | `StoreStatus` | `closed_at` → `CLOSED`, 아니면 `suspended_at` → `SUSPENDED`, 아니면 `ACTIVE` (D16). 저장하지 않음 |

기존 불변식 유지: `closed_at`이 있으면 `approval_at`도 있고 `closed_at >= approval_at`.

| 메서드 | 동작 | 예외 (순서대로) |
| --- | --- | --- |
| `suspend(reason, now)` | `suspended_reason`, `suspended_at = now` | ① 사유 비면 "정지 사유를 입력해 주세요." ② 폐점 → `StoreClosedError`(400 `STORE_CLOSED` "폐점된 상점입니다.") ③ 이미 정지 → `StoreAlreadySuspendedError`(400 `STORE_ALREADY_SUSPENDED` "이미 정지된 상점입니다."). 명세 나열 순서는 "이미 정지 → 폐점"이지만 둘이 겹치는 경우(정지 후 폐점된 상점)는 `status == CLOSED`이므로 폐점 문구를 우선한다 |
| `suspend_if_active(reason, now) -> bool` | 회원 정지의 연쇄 정지용. 폐점 또는 이미 정지면 **오류 없이 False**, 아니면 `suspend` 후 True | 사유·naive `now` 검증만 (D11) |
| `ensure_force_closable(reason)` | 부수 효과 없음 | ① 사유 비면 "폐점 사유를 입력해 주세요." ② 이미 폐점 → 기존 `StoreAlreadyClosedError`(400 `STORE_ALREADY_CLOSED` "이미 폐점된 상점입니다.") |
| `force_close(reason, now, has_reserved_reservations: bool)` | `closed_at = now`, `closed_reason` | ① `ensure_force_closable` ② `has_reserved_reservations` → `StoreHasReservedReservationsError`(400 `STORE_HAS_RESERVED_RESERVATIONS` "처리되지 않은 예약이 있는 상점은 폐점할 수 없습니다.") ③ 미승인 상점 → 기존 ValueError "승인되지 않은 상점은 폐점할 수 없습니다."(D37) ④ `now < approval_at` → 기존 ValueError. 정지된 상점도 폐점 가능 |
| `close(now)` (기존, 상점주 폐점) | **admin이 stores에 요구하는 인터페이스(설계는 stores.md 담당, C19)**: 정지된 상점이면 `StoreSuspendedError`(400 `STORE_SUSPENDED` "관리자에 의해 정지된 상점입니다.")를 내는 가드. 이 문서는 상점주 폐점 EP(`POST /v1/stores/{store_id}/close`)를 설계하지 않는다. 가드는 `Store.status`·`suspended_at`(S10)에 의존하므로 두 설계의 속성 이름이 같아야 한다 | 순서 제안: 이미 폐점 → 정지 → 미승인 (D17) |

전이표 (`status` 기준):

| 현재 | 이벤트 | 다음 |
| --- | --- | --- |
| ACTIVE | `suspend` / `suspend_if_active` | SUSPENDED |
| SUSPENDED | `suspend` | 불가 (`StoreAlreadySuspendedError`) |
| ACTIVE / SUSPENDED | `force_close` (관리자) | CLOSED |
| ACTIVE | `close` (상점주, 기존) | CLOSED |
| SUSPENDED | `close` (상점주) | 불가 (`StoreSuspendedError`, D17) |
| CLOSED | 모든 정지·폐점 | 불가 (`StoreClosedError` / `StoreAlreadyClosedError`) |
| SUSPENDED | 정지 해제 / 재개점 | **EP 없음**(D10, stores.md D6 재개점 후속) |

stores 새 예외: `StoreClosedError`, `StoreAlreadySuspendedError`, `StoreSuspendedError`, `StoreHasReservedReservationsError`(전부 `ValueError`, `error_code` 보유 → 400, `error_handlers.py` 변경 없음).

### 3.3 catalog 도메인 확장 (`src/catalog/domain/`)

| 변경 | 내용 |
| --- | --- |
| `OfferStatus.SUSPENDED` 추가 | |
| `DiscountOffer` 속성 | `suspended_reason: str \| None`, `suspended_at: datetime \| None` (둘 다 있거나 없음, tz-aware). `is_suspended` property |
| `effective_status(now)` 우선순위 (catalog.md 3.4 표 수정) | 1. `not is_active` → CLOSED, **2. `is_suspended` → SUSPENDED**, 3. `now >= sales_end` → CLOSED, 4. `now < sales_start` → SCHEDULED, 5. 재고 0 → SOLD_OUT, 6. ON_SALE. (C6) |
| `is_open(now)` | **변경 없음**(`is_active and now < sales_end`). 정지된 할인도 "진행 중"으로 센다 → 같은 상품에 중복 등록·상점주 폐점을 우회하지 못한다(D22). 단 catalog.md 10절의 "`OPEN_OFFER_STATUSES`가 `is_open`이 참인 effective_status 집합과 같음" 테스트는 SUSPENDED가 추가되어 깨진다(C6) |
| `suspend(reason, now)` | `suspended_reason`, `suspended_at = now`, `status = SUSPENDED`(저장값). `is_active`는 바꾸지 않는다(D19) |
| `suspend` 예외 (명세 순서) | ① 사유 비면 "정지 사유를 입력해 주세요." ② 이미 정지 → `OfferAlreadySuspendedError`(400 `OFFER_ALREADY_SUSPENDED` "이미 정지된 상품입니다.") ③ 판매 종료(`not is_active` 또는 `now >= sales_end`) → `OfferSalesEndedError`(400 `OFFER_SALES_ENDED` "판매가 종료된 상품입니다."). `SCHEDULED`·`SOLD_OUT`은 정지 가능(D21) |
| `end_sale(now) -> bool` | 관리자 상점 폐점용. `is_active=False`, `status=CLOSED`, 이미 `not is_active`면 아무 것도 안 하고 False. 정지된 할인도 종료한다(정지 정보는 이력으로 남김). 재고·`stock_log` 불변(catalog D40과 같은 방식) |
| 상점주 조작 가드 | `pause`, `resume`, `close`(#12), `apply_changes`(#11), `adjust_stock`(#14), `ensure_relistable`(#13)은 **정지된 할인이면 `OfferSuspendedError`**(400 `OFFER_SUSPENDED` "관리자에 의해 정지된 상품입니다.")를 가장 먼저 낸다(D20). 상점주가 `is_active:true` 재개나 재등록으로 관리자 정지를 우회하지 못하게 한다 |
| `StoreRef`(catalog) | `suspended: bool`(`StoreInfo.suspended_at is not None`) 추가. `ensure_can_register`의 순서를 폐점 → **정지(`StoreSuspendedError`, 400 `STORE_SUSPENDED`)** → 미승인으로 확장. `ensure_visible_to(viewer_id)`: 정지된 상점이고 `viewer_id`가 소유자가 아니면 `StoreNotFoundError`(404) |

허용 전이(저장 `status` 기준 추가분): SCHEDULED/ON_SALE/SOLD_OUT --`suspend`--> SUSPENDED. SUSPENDED --`end_sale`--> CLOSED(상점 강제 폐점). SUSPENDED에서 되돌리는 전이는 **없다**(해제 EP 없음, D10). 기존 `CLOSED`/비활성 할인은 정지 불가.

예약 가능 판정은 catalog.md 3.4 후속 메모대로 `effective_status(now) == ON_SALE`이므로 SUSPENDED는 신규 예약이 자동으로 막힌다. **기존 RESERVED 예약은 할인 상태와 무관하게 진행**되어야 한다(catalog.md C9, 6절 요구).

### 3.4 admin 도메인

엔티티 없음. `domain/service.py`의 `Clock(ABC).now() -> datetime`(tz-aware UTC)만 둔다(D31, stores D13·catalog D21과 같은 모듈별 Clock). 규칙은 전부 소유 컨텍스트에 있다.

---

## 4. 인프라 (infrastructure/)

### 4.1 모델 변경 (2절 스키마와 1:1, R14)

| 모델 | 변경 |
| --- | --- |
| `UserModel` | S1~S5 컬럼. `status`는 `String(20)`, `server_default="APPROVED"`, `ck_users_status`. 시간은 `DateTime(timezone=True)` |
| `PointLogModel` | S6~S9. `created_by`는 `ForeignKey("users.id")`(같은 모듈이라 문자열 FK 그대로). `ck_point_log_type`에 `GRANT` 추가 |
| `StoreModel` | S10 컬럼 3개 |
| `DiscountOfferModel` | S11. status CHECK에 `SUSPENDED` 추가 |
| admin | 모델 없음 |

### 4.2 레포지토리 (추상은 각 `domain/repository*`, 구현체는 `SqlAlchemy*`. 도메인 객체만 주고받고 `flush()`까지, R4·R5)

| 모듈 | 추상 메서드 변경 | 구현 메모 |
| --- | --- | --- |
| auth `UserRepository` | 시그니처 변경 없음. `save`가 새 컬럼 9개를 쓰고 `_to_domain`이 읽는다 | `find_by_id(for_update=True)`는 이미 있음(`SELECT ... FOR UPDATE`). `status` 문자열 → `UserStatus` |
| auth `PointLogRepository` | `add`가 `reason`, `balance_after`, `created_by`를 쓴다. `find_by_user(user_id, *, point_type, offset, limit)`·`count_by_user`는 그대로 재사용(최신순 `created_at desc, id desc`) | EP 8은 `offset=(page-1)*size` |
| stores `StoreRepository` | `find_by_owner_id(owner_id, for_update: bool = False)`로 **인자 추가**. `find_by_id(store_id, for_update)`는 이미 있음 | `save`의 UPDATE 대상에 `suspended_reason`, `suspended_at`, `closed_reason`, `closed_at` 추가(기존은 `approval_at`·`closed_at`만) — stores.md D10 "개설 후 이름·주소·좌표·owner는 갱신하지 않음"은 유지 |
| catalog `ProductRepository` | `find_all_by_store_for_update(store_id) -> list[Product]` 추가 (`id` 오름차순, `FOR UPDATE`) | 상점 폐점 시 상품 행을 먼저 잠그려는 용도(product → offer 순서, catalog.md 5.3) |
| catalog `DiscountOfferRepository` | `find_open_by_store_for_update(store_id, now) -> list[DiscountOffer]` 추가 (`is_active AND sales_end > now`, `id` 오름차순, `FOR UPDATE` + `populate_existing`). `_status_clause`·`save`·`_to_domain`에 `SUSPENDED`·`suspended_*` 반영 | `_status_clause(CLOSED/SCHEDULED/ON_SALE/SOLD_OUT)`는 `effective_status` 우선순위와 같게 "`suspended_at IS NULL`" 조건을 추가하고, `SUSPENDED`는 `is_active AND suspended_at IS NOT NULL`(CI-5 일관성 테스트 확대). 공개 목록의 `status` 허용 값에는 SUSPENDED를 넣지 않는다(D20) |
| admin | 레포지토리 없음 | `SystemClock`, `NoReservationAdmin`(임시). reservations·catalog 레포지토리 변경은 **이번 라운드에 없다**(후속 RV1·RV4는 5.2절 후속 목록) |

### 4.3 동시성과 잠금 순서 (D34)

**전역 잠금 순서: `stores` → `products` → `discount_offers` → `pickup_reservations` → `payments` → `users`. 같은 종류 안에서는 `id` 오름차순.** 근거: catalog.md 5.3(product → offer), payments.md 4.2.3 C-4(예약 → 결제 → 환불 → 회원), db-schema §7(offer 먼저). 어긋나면 교착이 난다.

| EP | 잠금 | 위험 / 대응 |
| --- | --- | --- |
| 1, 2 | `users` 행 `FOR UPDATE` | 동시 승인·거부(둘 다 PENDING을 보고 통과) → 행 잠금 후 상태 재확인(도메인이 다시 검사) |
| 3 | (OWNER면) `stores` 행 → `users` 행 | 3과 4가 같은 상점주에 동시에 오면 순서가 다르면 교착 → **둘 다 store → user 순서** |
| 4 | `stores`(소유 상점) → `products` → `discount_offers`(상점 폐점) → `pickup_reservations`·`payments`(본인 예약 취소, 예약 모듈 담당) → `users` | 4에서 상점 쪽을 **예약 취소보다 먼저** 하는 이유: 상점주가 자기 상점 할인을 예약했을 때(`reservations/domain/rules.py` `ALLOW_OWNER_SELF_RESERVATION = True`, 즉 허용) 예약 취소가 offer를 잠근 뒤 상점의 product를 잠그면 catalog 쪽 `product → offer`와 역순이 되어 교착한다. 후속 reservations 구현은 회원의 여러 RESERVED 예약을 `offer_id, id` 오름차순으로 한 건씩 `offer → reservation` 순서로 잠가야 한다(5.2절 RV2). 이번 라운드는 자리표시자라 예약을 잠그지 않는다 |
| 5 | `stores` 행 | 동시 정지 → 행 잠금 후 상태 재확인 |
| 6 | `stores` → `products` → `discount_offers` → `pickup_reservations`(RESERVED 조회를 `FOR UPDATE`) | 할인을 먼저 종료해 신규 예약을 막은 **뒤에** RESERVED를 조회한다(순서가 반대면 조회 직후 새 예약이 끼어든다). RESERVED 행 `FOR UPDATE`는 결제 확정(`PENDING_PAYMENT → RESERVED`, `lifecycle.mark_paid`가 offer → 예약 순으로 잠금)과 직렬화하려는 것이다. **종료·마감된 할인(`end_all_sales`의 `find_open_by_store_for_update` 대상 밖)의 RESERVED 예약도 픽업 대기 중일 수 있으므로** 후속 실제 구현은 상점의 **모든** 할인의 예약을 조회해야 한다(방법은 D41 보류). 이번 라운드는 `NoReservationAdmin`이라 항상 False. 잔여 위험: 상점 행 잠금과 무관하게 새 상품을 만들어 곧바로 할인을 등록하는 요청은 상품 잠금으로 막히지 않는다(catalog 기존 동작, 폐점 커밋 뒤에는 `StoreClosedError`로 거부됨. 수용) |
| 7 | `products` → `discount_offers` | 정지와 동시에 들어오는 #11·#12·#14와 직렬화(catalog 기존 패턴: offer를 무잠금으로 읽어 `product_id`를 얻고 → product → offer) |
| 9 | `users` 행 `FOR UPDATE`(`_locked_user`) | 지급과 결제 포인트 사용이 겹쳐도 잔액이 틀리지 않게. 이력 insert와 잔액 변경은 같은 트랜잭션 |
| 8 | 없음 | 읽기 전용. 잔액(`users_point`)과 이력은 별도 SELECT라 순간적 불일치는 허용 |
| 로그인·인증 | 없음 | 정지·탈퇴 확인은 이미 하는 `users` 조회에 얹는다(추가 쿼리 없음) |

---

## 5. 응용 (application/)

### 5.1 원칙

- 쓰기 EP는 **admin 서비스가 마지막에 한 번 `session.commit()`** 한다(R5, R13). 호출하는 다른 모듈 서비스 메서드는 모두 `commit=False`로 부른다. 예외가 나면 커밋되지 않고 세션이 닫힐 때 롤백된다.
- 모든 흐름은 `now = self.clock.now()`를 **한 번** 얻어 각 모듈에 넘긴다(한 요청의 `suspended_at`·`closed_at`이 같은 시각).
- 시나리오의 "조회 → 도메인 메서드 → save → commit"은 각 모듈 서비스 안에서 일어난다. admin 서비스는 호출 순서와 commit만 정한다(R3).
- 현재 어느 서비스도 R13의 `commit` 인자를 가진 관리자 메서드가 없다. 아래 5.3절이 각 모듈에 **새로 생기는 메서드**다.

### 5.2 포트 (`admin/application/ports.py`, `typing.Protocol`, 쓰는 쪽이 정의, D30)

```python
class AccountAdminPort(Protocol):               # AuthApplicationService가 구조적으로 만족
    async def get_account(self, user_id) -> AccountInfo: ...                           # 404, 무잠금. AccountInfo: id, role(str), status(str)
    async def approve_owner(self, user_id, *, now, commit: bool = True) -> UserAdminInfo: ...
    async def reject_owner(self, user_id, reason, *, now, commit: bool = True) -> UserAdminInfo: ...
    async def suspend_user(self, user_id, reason, suspended_until, *, now, commit: bool = True) -> UserAdminInfo: ...
    async def check_withdrawable(self, user_id, reason) -> None: ...                    # 부수 효과 없음, 무잠금
    async def withdraw_user(self, user_id, reason, *, now, commit: bool = True) -> UserAdminInfo: ...
    async def grant_points(self, user_id, amount, reason, admin_id, *, now, commit: bool = True) -> PointLogInfo: ...
    async def list_points(self, user_id, page, size) -> PointHistoryInfo: ...

class StoreAdminPort(Protocol):                 # StoresApplicationService가 구조적으로 만족
    async def lock_store(self, store_id) -> StoreAdminInfo: ...                         # 404, FOR UPDATE
    async def lock_store_of_owner(self, owner_id) -> StoreAdminInfo | None: ...         # 없으면 None, FOR UPDATE
    async def suspend_store(self, store_id, reason, *, now, commit: bool = True) -> StoreAdminInfo: ...
    async def suspend_stores_of_owner(self, owner_id, reason, *, now, commit: bool = True) -> StoreAdminInfo | None: ...  # 연쇄 정지, 폐점·이미 정지·상점 없음은 건너뜀
    async def check_force_closable(self, store_id, reason) -> None: ...                 # lock + 사유·이미 폐점 검사 (명세 에러 순서 유지용)
    async def close_store_by_admin(self, store_id, reason, *, has_reserved_reservations: bool, now, commit: bool = True) -> StoreAdminInfo: ...

class OfferAdminPort(Protocol):                 # CatalogApplicationService가 구조적으로 만족
    async def suspend_offer(self, offer_id, reason, *, now, commit: bool = True) -> OfferAdminInfo: ...
    async def end_all_sales_of_store(self, store_id, *, now, commit: bool = True) -> int: ...   # 종료한 할인 수

class ReservationAdminPort(Protocol):           # 이번 라운드: NoReservationAdmin (B-6). 후속: reservations 실제 구현으로 container 바인딩만 교체
    async def cancel_reserved_for_user(self, user_id, *, reason: str) -> int: ...               # commit 인자 없음: 호출자가 commit, 이 메서드는 절대 commit하지 않는다 (R13)
    async def has_reserved_for_store(self, store_id) -> bool: ...                               # D41 보류 중에도 시그니처 고정(가장 작은 변경)
```

- **후속 (reservations 담당) — 이번 구현에 포함하지 않음 (사용자 범위 변경 2026-11-05)**: 아래 RV1~RV5는 reservations 작업 때 쓸 설계 초안이다. 이번 라운드에 `src/reservations/**`·`tests/reservations/**`는 바뀌지 않는다. RV1·RV4의 매장 단위 조회는 D41(보류)이 정해야 한다: (b)안이면 RV4가 `has_reserved_for_offers(offer_ids)`가 되고, 그 경우 container의 어댑터가 reservations 서비스와 catalog를 묶어 `has_reserved_for_store(store_id)`를 만족시키면 admin 코드는 바뀌지 않는다(admin 포트 시그니처 고정).

  | # | 파일 | 추가·변경 | 상세 |
  | --- | --- | --- | --- |
  | RV1 | `domain/repository.py` + `infrastructure/repositories.py` | `find_by_user_and_status`, `find_by_offers_and_status` 추가(4.2절) | 도메인 객체만 반환(R4), `flush` 없음(읽기) |
  | RV2 | `application/lifecycle_service.py` | `ReservationLifecycleService.cancel_reserved_for_user(user_id, *, reason: str) -> list[CancelledReservation]` | ① `peek = reservations.find_by_user_and_status(user_id, RESERVED)`(무잠금, `offer_id, id` 순) ② 각 예약마다 `stock.get_terms(offer_id, for_update=True)`(offer 먼저) → `reservations.find_by_id(id, for_update=True)` ③ 잠금 후 **상태 재확인**: `RESERVED`가 아니면 건너뜀(고객이 동시에 취소했거나 이미 픽업. 멱등) ④ `RefundTarget(status=RESERVED)`를 **취소 직전 상태로** 만든 뒤(reservations.md W-5/D-30과 같은 방식) `reservation.cancel(now)` → `stock.release(offer_id, quantity, user_id=reservation.user_id, reason=reason)`(재고 복구, `cancel_all_for_offer`와 달리 복구함) → `reservations.save` ⑤ `CancelledReservation(reservation, target)` 목록 반환. `commit` 없음, `PENDING_PAYMENT`는 대상 아님(D12). 기존 `_load_locked`를 재사용해도 된다(같은 잠금 순서) |
  | RV3 | `application/service.py` | `ReservationApplicationService.cancel_reserved_for_user(user_id, *, reason) -> int` | `cancelled = await lifecycle.cancel_reserved_for_user(...)` → 각 항목의 `refund_target`에 대해 `refunds.refund_for_cancelled_reservation(target, reason=reason, waive_penalty=True)` → `len(cancelled)` 반환. **`session.commit()` 호출 금지**(`cancel_all_for_offer`와 같은 형태, R5·R13). 환불 실패 예외는 그대로 올려 admin이 롤백하게 한다 |
  | RV4 | `application/service.py` | `ReservationApplicationService.has_reserved_for_offers(offer_ids) -> bool` | `reservations.find_by_offers_and_status(offer_ids, RESERVED, for_update=True)` 결과가 비어 있지 않으면 True. 읽기+행 잠금, commit 없음 |
  | RV5 | `presentation/router.py` | 픽업 EP의 의존성 `OwnerUser` → `SuspendedAllowedOwnerUser` (D35, C14) | 이 EP 하나만. 다른 EP 불변 |

  (후속) 이 메서드들은 **다른 모듈 호출 인자 `commit`이 없는 대신 "절대 commit하지 않는다"**가 계약이다(기존 `cancel_all_for_offer`와 동일). **자리표시자와의 관계(미연계, R16)**: RV2의 `stock.release`는 현재 `ReadOnlyOfferStockPort`라 no-op, RV3의 `refunds`는 `NoPaymentRefund`라 no-op이다. 그래서 지금은 **예약 상태만 `CANCELLED`로 바뀌고 재고·환불·포인트는 변하지 않는다.** 구현체를 교체하면 이 코드는 그대로 완전한 D12 동작이 된다. 또한 payments가 `InMemoryReservationPort`를 쓰는 동안은 `RESERVED` 행이 실서버에 생기지 않아 취소 수는 보통 0이다. 테스트는 fake `StockPort`·`RefundPort`로 호출 인자(`waive_penalty=True`, 재고 `quantity`)를 단언한다.
- 결과 타입(`UserAdminInfo`, `StoreAdminInfo`, `OfferAdminInfo`, `PointLogInfo`, `PointHistoryInfo`)은 필요한 속성만 선언한 Protocol이다. 도메인 객체(`User`, `Store`, `OfferView`, `PointLog`)가 속성 이름만 맞으면 구조적으로 만족한다(catalog `StoreInfo`와 같은 방식). 응답 스키마는 `from_attributes=True`로 읽는다.
- **이번 라운드 임시 구현** `NoReservationAdmin`(`admin/infrastructure/reservation_admin.py`): `cancel_reserved_for_user`는 0, `has_reserved_for_store`는 False를 돌려주고 아무것도 하지 않는다. **미연계(R16)**: EP 4는 예약을 취소하지 않고(`cancelled_reservation_count`는 항상 0), EP 6의 RESERVED 검사는 항상 통과한다. 후속 reservations PR은 container 바인딩만 교체한다.
- `ReservationAdminPort` 계약 (후속 실제 구현의 목표, RV2~RV4): ① `cancel_reserved_for_user`는 해당 회원의 **RESERVED** 예약만 취소하고 재고를 복구하며(stock_log 양수) 결제된 금액을 **전액 환불·사용 포인트 복구**를 payments에 요청한다(위약금 면제 `waive_penalty=True`). `commit` 금지(R5), 같은 세션(R13), 취소 수 반환, 중복 호출 멱등. ② `has_reserved_for_store`는 상점의 모든 할인에 걸린 RESERVED 예약이 하나라도 있는지 `FOR UPDATE`로 잠가 읽는다(상점→할인 변환 방식은 D41 보류). catalog `ReservationCancelPort`(catalog.md 6.4)와는 **별개 포트**다.
- 포트를 쓰므로 admin은 `auth`·`stores`·`catalog`·`reservations`를 import하지 않는다(R2, R11). 연결은 container만 안다.

### 5.3 각 모듈에 생기는 application 메서드 (R13 `commit` 인자, 도메인 메서드 호출 + `save()`)

| 모듈 | 메서드 | 시나리오 |
| --- | --- | --- |
| auth | `get_account(user_id)` | `users.find_by_id` → 없으면 `UserNotFoundError`. 읽기 |
| auth | `approve_owner(user_id, *, now, commit)` | `_locked_user`(FOR UPDATE) → `user.approve_owner(now)` → `users.save` → `_finish(commit)` |
| auth | `reject_owner(user_id, reason, *, now, commit)` | 같은 패턴, `user.reject_owner(reason, now)` |
| auth | `suspend_user(user_id, reason, suspended_until, *, now, commit)` | `_locked_user` → `user.suspend(reason, until, now)` → `save` → `_finish` |
| auth | `check_withdrawable(user_id, reason)` | `find_by_id`(무잠금) → `user.ensure_withdrawable(reason)` |
| auth | `withdraw_user(user_id, reason, *, now, commit)` | `_locked_user` → `user.withdraw(reason, now)` → `save` → `_finish` |
| auth | `grant_points(user_id, amount, reason, admin_id, *, now, commit)` | `_locked_user` → `normalized = user.grant_points(amount, reason)` → `users.save` → `point_logs.add(PointLog.record(user.id, GRANT, amount, user.users_point, reason=normalized, created_by=admin_id))` → `_finish`. 이력과 잔액이 한 트랜잭션(명세 9) |
| auth | `list_points(user_id, page, size)` | `page < 1` 또는 `size`가 1~100 밖이면 `InvalidPageError` → `find_by_id`(404 `UserNotFoundError`) → `point_logs.find_by_user(offset=(page-1)*size, limit=size)` + `count_by_user`. 응답 `balance = user.users_point` |
| auth | **기존 메서드 변경** | `login`: 비밀번호 검증 **성공 후** `user.ensure_can_login(now)`(틀린 비밀번호는 상태와 무관하게 `INVALID_CREDENTIALS`, 계정 열거 방지, D8). **D40: 반환 타입이 현재 `str`(토큰)에서 `LoginResult(token: str, status: str)` 값 객체(auth application)로 바뀐다**(`status = user.effective_status(now).value`). router는 `TokenResponse(access_token=result.token, token_type="bearer", status=result.status)`. 정지된 CUSTOMER는 403, **정지된 OWNER는 토큰을 발급**(D39), 탈퇴는 역할 무관 401. 서비스에 역할 분기를 두지 않고 규칙은 `ensure_can_login`에 있다(R3). `authenticate(token, *, allow_suspended: bool = False)`: `user.ensure_can_authenticate(now, allow_suspended=allow_suspended)`(D35, 5.5절). `use/earn/restore/revoke_points`: `PointLog.record`에 `balance_after` 전달. 생성자에 **`clock: Clock` 필수 인자 추가**(D33) |
| stores | `lock_store`, `lock_store_of_owner` | `find_by_id(for_update=True)` / `find_by_owner_id(for_update=True)`. 없으면 `StoreNotFoundError`(owner 조회는 None) |
| stores | `suspend_store(store_id, reason, *, now, commit)` | `find_by_id(for_update=True)` → 404 → `store.suspend(reason, now)` → `save` → `_finish` |
| stores | `suspend_stores_of_owner(owner_id, reason, *, now, commit)` | `find_by_owner_id(for_update=True)` → 없으면 None → `store.suspend_if_active(reason, now)` → True면 `save` |
| stores | `check_force_closable(store_id, reason)` | `find_by_id(for_update=True)` → 404 → `store.ensure_force_closable(reason)` |
| stores | `close_store_by_admin(store_id, reason, *, has_reserved_reservations, now, commit)` | `find_by_id(for_update=True)` → 404 → `store.force_close(reason, now, has_reserved_reservations)` → `save` → `_finish` |
| catalog | `suspend_offer(offer_id, reason, *, now, commit)` | 할인을 무잠금으로 읽어 `product_id` 확보(404 `OfferNotFoundError`) → 상품 `FOR UPDATE` → 할인 `FOR UPDATE` → `offer.suspend(reason, now)` → `offers.save` → `_finish`. 응답용으로 `OfferView`(상점명은 `StorePort`) |
| catalog | `end_all_sales_of_store(store_id, *, now, commit)` | `products.find_all_by_store_for_update(store_id)` → `offers.find_open_by_store_for_update(store_id, now)` → 각 `offer.end_sale(now)` → `offers.save` → 종료 수 반환. 재고·`stock_log` 불변(D18) |
| catalog | **기존 읽기 메서드 변경** | `list_products`·`get_product`·`list_offers_by_store`·`get_offer_detail`: `_load_store` 뒤 `store.ensure_visible_to(viewer_id)`(D17). `get_offer_detail`에 `viewer_id`를 추가하고 할인이 정지(`effective_status == SUSPENDED`)이면 소유자 외 `OfferNotFoundError`(D20). `create_product`·`register_offer`·`relist_offer`는 `ensure_can_register`가 정지 상점을 막음 |

`commit` 인자 규칙(R13): `commit=True`가 기본이라 기존 호출자에는 영향이 없다. admin은 항상 `commit=False`로 부른다.

### 5.5 정지된 상점주의 픽업 허용 (D35 확정)

명세 5("기존 RESERVED 예약은 유지되어 픽업 처리가 가능")를 명세 3("정지된 회원은 보호 API를 사용할 수 없다")보다 우선한다. 정지 확인은 계속 공통 `authenticate` 한 곳에 있고(기본 차단), **픽업 EP만 예외 의존성을 쓰는 방식**으로 공존시킨다.

| 위치 | 설계 |
| --- | --- |
| auth application | `authenticate(token, *, allow_suspended: bool = False)`. 기본 호출은 그대로 정지 회원을 막는다. 규칙 자체(정지·탈퇴 판정)는 `User.ensure_can_authenticate`에 있다(R3). 탈퇴·토큰 폐기·위조 검사는 `allow_suspended`와 무관하게 동일 |
| auth presentation | `dependencies.py`에 `get_current_principal_allow_suspended`(내부에서 `service.authenticate(token, allow_suspended=True)`)와 별칭 `SuspendedAllowedOwnerUser = Annotated[User, Depends(require_roles_allow_suspended(Role.OWNER))]`를 **새로 추가**한다. `require_roles`·`CurrentUser`·`OwnerUser` 등 기존 별칭은 불변(전부 정지 차단). `provide_auth_service`를 그대로 쓰므로 새 `provide_*` 없음(R9) |
| reservations presentation (**후속, 이번 라운드 제외**: 사용자 범위 변경 2026-11-05. D35는 이 교체 전까지 **부분 효력**: 로그인 허용(D39)·`SuspendedAllowedOwnerUser` 존재까지만이고 정지된 상점주의 픽업은 아직 403) | **`POST /v1/reservations/{reservation_id}/pickup` 한 EP만** `OwnerUser` 대신 `SuspendedAllowedOwnerUser`를 쓴다. 해당 매장 소유 확인(403)·`pickup_code` 검증은 reservations 서비스·도메인이 기존대로 한다 |
| 허용 범위 | 정지된 상점주는 **픽업 처리만** 가능하다. 상점 정보 변경·상품·할인 등록·재고 조정·폐점·로그아웃·포인트 조회 등 나머지 보호 API는 명세 3대로 403 `FORBIDDEN` "정지된 계정입니다."이다. 정지된 상점의 상품·할인 숨김, 신규 예약 차단(D17)은 그대로 |
| 탈퇴 | 강제 탈퇴된 상점주는 `WITHDRAWN`이라 픽업도 401이다(탈퇴 시 RESERVED는 취소되거나 폐점이 거부되므로 픽업할 예약이 남지 않는다, D12·D13) |

고객 쪽 영향은 없다(정지된 고객은 계속 차단, 고객의 예약 취소 EP도 `CurrentUser` 그대로 차단). **D39 확정: 정지된 OWNER는 로그인할 수 있다**(`ensure_can_login`의 OWNER 예외). 그래서 정지 기간 내내 새 토큰을 받아 픽업 EP를 쓸 수 있다. 로그인 후에도 픽업 EP 외 보호 API는 403이다(`allow_suspended` 기본 False). 정지된 CUSTOMER는 D8대로 로그인 403, 탈퇴는 역할 무관 401(D9)이다.

**C17 해소 (D40, 2026-11-05 확정, 선택지 ①)**: 로그인 응답 `TokenResponse`에 `status` 필드를 추가한다.
- 필드: `status: str`, 값 = 로그인 시점의 **유효 상태** `user.effective_status(now)`: `APPROVED`(만료된 정지 포함) / `PENDING` / `REJECTED` / `SUSPENDED`. `WITHDRAWN`은 로그인이 401이라 응답에 나오지 않는다. 정지된 CUSTOMER는 로그인이 403이라 `SUSPENDED`는 사실상 **정지된 OWNER에게만** 나온다. 사유·기간은 노출하지 않는다(D8). JWT 클레임은 바꾸지 않는다(상태 변경과 어긋나는 문제 회피).
- 구현 영향: `AuthApplicationService.login`의 반환을 `LoginResult(token, status)`로(5.3절), `TokenResponse`에 `status: str = Field(..., description=...)` 추가(필수 필드. 응답 전용이라 하위 호환 추가 필드), `login` 라우트 한 줄 수정. 로그인 응답을 검사하는 기존 테스트(`tests/auth/test_api_db.py`, `test_service.py`의 `login` 반환값 사용)와 `tests/helpers.py`는 `["access_token"]`만 쓰므로 영향이 작지만, `login`이 `str`을 반환한다고 가정한 서비스 테스트는 `.token`으로 바꾼다(미검증: 해당 테스트 목록은 구현자가 `Grep login(`으로 확인).
- 테스트: 정지된 OWNER 로그인 200 `status == "SUSPENDED"`, PENDING 상점주 `status == "PENDING"`, 일반 고객 `APPROVED`, 정지 만료 후 `APPROVED`, 응답에 `reason`·`suspended_*`가 없음.
- `docs/reference/auth.md` 변경 제안은 10절.

### 5.4 admin 서비스 `AdminApplicationService` — EP별 시나리오

```python
class AdminApplicationService:
    def __init__(self, session: AsyncSession, accounts: AccountAdminPort, stores: StoreAdminPort,
                 offers: OfferAdminPort, reservations: ReservationAdminPort, clock: Clock): ...   # 전부 필수 (R8)
```

인증은 router의 `AdminUser`가 처리하고, 서비스에는 `admin_id: UUID`만 넘긴다(catalog D23과 같은 선택: application이 auth 도메인을 import하지 않음).

| EP | 메서드 | 흐름 (commit은 마지막 1회) |
| --- | --- | --- |
| 1 | `approve_owner(owner_id)` | `now` → `accounts.approve_owner(owner_id, now=now, commit=False)` → `commit` → 반환. 404 `OwnerNotFoundError`, 400 `OwnerNotPendingError` |
| 2 | `reject_owner(owner_id, reason)` | 같은 패턴. 사유 검증이 상태 검사보다 먼저 |
| 3 | `suspend_user(user_id, reason, suspended_until)` | ① `acct = accounts.get_account(user_id)`(404, 무잠금) ② `acct.role == "OWNER"`이면 `stores.lock_store_of_owner(user_id)`(상점 행 먼저, 4와 같은 순서) ③ `user = accounts.suspend_user(..., commit=False)`(여기서 모든 400 검증) ④ OWNER면 `stores.suspend_stores_of_owner(user_id, reason, now=now, commit=False)`(이미 정지·폐점·상점 없음은 건너뜀, D11) ⑤ `commit`. ③이 실패하면 ④는 실행되지 않고 롤백 |
| 4 | `withdraw_user(user_id, reason)` | ① `acct = accounts.get_account(user_id)`(404) ② `accounts.check_withdrawable(user_id, reason)`(사유·이미 탈퇴·관리자 400을 **무거운 작업 전에** 확인) ③ OWNER면 `store = stores.lock_store_of_owner(user_id)` ④ 상점이 있고 `status != "CLOSED"`면 `offers.end_all_sales_of_store(store.id, now=now, commit=False)` ⑤ `cancelled = reservations.cancel_reserved_for_user(user_id, reason=reason)`(이번 라운드 `NoReservationAdmin` → 항상 0, 미연계, B-6) ⑥ 상점이 있고 폐점 전이면 `reserved = reservations.has_reserved_for_store(store.id)`(임시 구현은 항상 False) → `stores.close_store_by_admin(store.id, reason, has_reserved_reservations=reserved, now=now, commit=False)` ⑦ `accounts.withdraw_user(user_id, reason, now=now, commit=False)` ⑧ `commit` → `{id, status, deleted_at, cancelled_reservation_count=cancelled}`. ⑥에서 타 고객의 RESERVED 예약이 남아 있으면 `StoreHasReservedReservationsError`(400)로 **전체 롤백**(탈퇴도 취소되지 않음)(D13). 자기 상점을 자기가 예약한 경우는 ⑤에서 먼저 취소되어 ⑥을 막지 않는다 |
| 5 | `suspend_store(store_id, reason)` | `stores.suspend_store(store_id, reason, now=now, commit=False)` → `commit`. 응답 `owner_id`·`name`은 상점에서 |
| 6 | `close_store(store_id, reason)` | ① `stores.check_force_closable(store_id, reason)`(상점 행 잠금, 404 → 사유 → 이미 폐점 순서 보장) ② `offers.end_all_sales_of_store(store_id, now=now, commit=False)`(신규 예약 차단) ③ `reserved = reservations.has_reserved_for_store(store_id)`(임시 구현은 항상 False) ④ `stores.close_store_by_admin(store_id, reason, has_reserved_reservations=reserved, now=now, commit=False)`(예약이 있으면 400, 모든 변경 롤백) ⑤ `commit` |
| 7 | `suspend_offer(offer_id, reason)` | `offers.suspend_offer(offer_id, reason, now=now, commit=False)` → `commit` |
| 8 | `get_user_points(user_id, page, size)` | `accounts.list_points(user_id, page, size)`. 읽기, commit 없음 |
| 9 | `grant_points(admin_id, user_id, amount, reason)` | `accounts.grant_points(user_id, amount, reason, admin_id, now=now, commit=False)` → `commit` → 지급 이력 반환(201) |

트랜잭션 경계 정리:

| 흐름 | 한 트랜잭션에 묶이는 것 | 롤백 조건 |
| --- | --- | --- |
| 3 | 회원 정지 + 상점 정지 | ③ 검증 실패(상점 정지 미실행), ④ 중 예외 → 회원 정지도 취소 |
| 4 | 할인 종료 + 예약 취소(+재고 복구·환불·포인트 복구는 예약·결제 모듈) + 상점 폐점 + 회원 탈퇴 | ⑥ 예약 남음 400, 포트 예외 → 전체 롤백 |
| 6 | 할인 종료 + 상점 폐점 | 예약 남음 400 → 할인 종료도 롤백 |
| 9 | 잔액 + 이력 | `users_point` UPDATE와 `point_log` INSERT는 같은 세션의 같은 commit |

**재고 복구·환불의 책임**: admin은 재고나 결제를 직접 만지지 않는다. `ReservationAdminPort.cancel_reserved_for_user`가 예약 모듈 안에서 `catalog`(재고 복구)·`payments`(환불)를 호출한다(생성 순환 회피는 catalog.md 9.3, C12를 따른다). **이번 라운드는 `NoReservationAdmin`이라 EP 4는 예약을 하나도 취소하지 않고(재고 복구·환불·포인트 복구 없음) EP 6의 RESERVED 검사는 항상 통과한다 = D12 미연계(B-6, R16)**. 완료 보고에 "미연계"로 적는다. 후속 실제 구현 뒤에도 재고·환불 포트가 자리표시자인 동안은 상태만 취소된다.

---

## 6. 표현 (presentation/)

### 6.1 의존성·조립 (R9)

- `presentation/dependencies.py`: `provide_admin_service() -> AdminApplicationService` 플레이스홀더만 선언.
- 라우터는 `Annotated[AdminApplicationService, Depends(provide_admin_service)]`만 쓴다. 모든 EP에 `AdminUser`(auth, 401·403)를 건다.
- URI 접두사는 `presentation/router.py`의 상수 `ADMIN_PREFIX = "/v1/admin"` 한 곳(D2, 2026-11-05 사용자 변경: `/admin` → `/v1/admin`. `docs/reference/README.md`의 "관리자 전용 API는 `/v1/admin/...`"과 기존 auth 관리자 EP와 같음).
- **기존 auth 관리자 EP와의 공존 (D42 임시, C18)**: auth 라우터에는 `GET /v1/admin/users/{user_id}`(회원 조회)와 `POST /v1/admin/token-blacklist/purge`가 이미 있다. 이 설계의 새 라우터는 `DELETE /v1/admin/users/{user_id}`와 `GET /v1/admin/users/{user_id}/points` 등을 추가한다. **경로 충돌 없음**(B-11 실험: 같은 경로라도 메서드가 다르면 각자 응답, 다른 메서드는 405). 기본값: 기존 2개는 **auth 라우터에 그대로 둔다**(소유 컨텍스트에 가깝고 reference auth.md 6·7이 이미 문서화, 이동하면 auth.md·테스트 `tests/auth/test_admin_api.py`가 바뀐다). 새 admin 라우터 URI는 위 9개뿐이다. 이동하는 안(admin 라우터로 일원화)은 사용자 확인 후 별도 작업으로 한다. 부수 효과: `GET /v1/admin/users/{user_id}`의 `UserResponse`에도 D38의 `status`가 나온다.
- 라우터는 서비스만 호출하고 예외를 잡지 않는다(R6, R7).

### 6.2 엔드포인트 표 (명세 필드명 그대로, R15)

| # | Method | URI | 요청 스키마 | 응답 스키마 | 성공 | 에러 (명세 문구 / `error_code`) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | PATCH | `/v1/admin/owners/{owner_id}/approve` | 없음 | `OwnerApprovalResponse` `{id, email, name, role, status, approved_at}` | 200 | 400 `OWNER_NOT_PENDING` 승인 대기 중인 상점주가 아닙니다. / 401 / 403 / 404 상점주를 찾을 수 없습니다. |
| 2 | PATCH | `/v1/admin/owners/{owner_id}/reject` | `ReasonRequest {reason}` | `OwnerRejectionResponse` `{id, email, name, role, status, rejected_reason, rejected_at}` | 200 | 400 거부 사유를 입력해 주세요.(`VALIDATION_ERROR`) / 400 `OWNER_NOT_PENDING` / 401 / 403 / 404 |
| 3 | PATCH | `/v1/admin/users/{user_id}/suspend` | `UserSuspendRequest {reason, suspended_until: datetime \| null}` | `UserSuspensionResponse` `{id, email, role, status, suspended_reason, suspended_at, suspended_until}` | 200 | 400 정지 사유를 입력해 주세요. / 400 `INVALID_SUSPENSION_END` / 400 `USER_ALREADY_SUSPENDED` / 400 `USER_WITHDRAWN` / 400 `ADMIN_ACCOUNT_PROTECTED` / (추가) 400 `USER_NOT_SUSPENDABLE`(D36) / 401 / 403 / 404 회원을 찾을 수 없습니다. |
| 4 | DELETE | `/v1/admin/users/{user_id}` | `ReasonRequest {reason}` (DELETE 본문, B-9) | `UserWithdrawalResponse` `{id, status, deleted_at, cancelled_reservation_count}` | 200 | 400 탈퇴 사유를 입력해 주세요. / 400 `USER_ALREADY_WITHDRAWN` / 400 `ADMIN_ACCOUNT_PROTECTED` / (추가) 400 `STORE_HAS_RESERVED_RESERVATIONS`(D13) / 401 / 403 / 404 |
| 5 | PATCH | `/v1/admin/stores/{store_id}/suspend` | `ReasonRequest` | `StoreSuspensionResponse` `{id, owner_id, name, status, suspended_reason, suspended_at}` | 200 | 400 정지 사유를 입력해 주세요. / 400 `STORE_ALREADY_SUSPENDED` / 400 `STORE_CLOSED` / 401 / 403 / 404 상점을 찾을 수 없습니다. |
| 6 | PATCH | `/v1/admin/stores/{store_id}/close` | `ReasonRequest` | `StoreClosureResponse` `{id, owner_id, name, status, closed_reason, closed_at}` | 200 | 400 폐점 사유를 입력해 주세요. / 400 `STORE_ALREADY_CLOSED` / 400 `STORE_HAS_RESERVED_RESERVATIONS` / 401 / 403 / 404 |
| 7 | PATCH | `/v1/admin/offers/{offer_id}/suspend` | `ReasonRequest` | `OfferSuspensionResponse` `{id, store_id, title, status, suspended_reason, suspended_at}` (`title` = 상품명) | 200 | 400 정지 사유를 입력해 주세요. / 400 `OFFER_ALREADY_SUSPENDED` / 400 `OFFER_SALES_ENDED` / 401 / 403 / 404 상품을 찾을 수 없습니다.(catalog 기존 문구 "할인 판매를 찾을 수 없습니다."와 다름, D32) |
| 8 | GET | `/v1/admin/users/{user_id}/points?page=1&size=20` | 쿼리 `page`, `size` | `PointHistoryPageResponse` `{user_id, balance, history[{id, amount, type, reason, balance_after, created_by, created_at}], page, size, total}` | 200 | 400 `INVALID_PAGE` 페이지 값이 올바르지 않습니다. / 401 / 403 / 404 회원을 찾을 수 없습니다. |
| 9 | POST | `/v1/admin/users/{user_id}/points` | `PointGrantRequest {amount: int, reason}` | `PointGrantResponse` `{id, user_id, amount, type, reason, balance_after, created_by, created_at}` | **201** | 400 지급 포인트는 1 이상이어야 합니다. / 400 지급 사유를 입력해 주세요. / 400 `USER_WITHDRAWN` / 401 / 403 / 404 |

공통:
- 경로의 잘못된 UUID와 본문 필드 누락·타입 오류는 전역 핸들러가 **400 `VALIDATION_ERROR`**(B-8, 422 아님). 메시지는 `필드: 오류` 형식이라 명세 문구와 다르다.
- 요청 스키마에 `min_length`를 두지 않는다. `reason: str`, `amount: int`는 타입만 검증하고 값 검증(빈 사유·1 미만)은 도메인에서 명세 문구로 낸다(D26). `suspended_until`은 `datetime | None = None`. naive datetime은 도메인이 거부한다.
- 401·403 문구는 현재 `AdminUser`의 "로그인이 필요합니다."·"접근 권한이 없습니다."이고 명세("인증이 필요합니다.", "관리자 권한이 필요합니다.")와 다르다(D32). 상태 코드는 일치.
- 응답의 `status`는 EP 1·2·3·4는 `UserStatus` 값, 5·6은 `StoreStatus`, 7은 `OfferStatus` 값 문자열이다. EP 3의 `status`는 항상 `SUSPENDED`, EP 4는 `WITHDRAWN`.
- EP 8 `type`은 `point_type` 값을 그대로 낸다(`EARN/USE/RESTORE/REVOKE/GRANT`). 명세의 `GRANT | USE`는 부분집합이다(D23). 기존 행의 `reason`·`balance_after`·`created_by`는 null일 수 있어 스키마를 `str | None`, `int | None`, `UUID | None`로 둔다.

### 6.3 목록 쿼리 (EP 8 하나)

`page: int = 1`(1부터), `size: int = 20`. 검색·필터·정렬 없음, 정렬은 최신순 고정(`created_at desc, id desc`). 범위 검증은 `Query(ge=..)`가 아니라 서비스에서 한다(명세 문구 "페이지 값이 올바르지 않습니다."를 내려고. `Query` 제약을 쓰면 `page: Input should be greater than or equal to 1`이 나온다). `size` 최대 100. 숫자가 아닌 값은 전역 핸들러의 일반 400.

---

## 7. 조립 — `src/container.py` / `src/main.py` (모듈 밖 변경 제안)

```python
# ── admin ────────────────────────────
_admin_clock: AdminClock = AdminSystemClock()
_reservation_admin: ReservationAdminPort = NoReservationAdmin()   # 임시 (B-6, C10): 후속 reservations PR이 이 바인딩만 교체

def create_reservation_admin() -> ReservationAdminPort:
    return _reservation_admin

def create_admin_service(
    session: AsyncSession = Depends(get_db),
    accounts: AuthApplicationService = Depends(create_auth_service),
    stores: StoresApplicationService = Depends(create_stores_service),
    offers: CatalogApplicationService = Depends(create_catalog_service),
    reservations: ReservationAdminPort = Depends(create_reservation_admin),
) -> AdminApplicationService:
    return AdminApplicationService(session=session, accounts=accounts, stores=stores, offers=offers,
                                   reservations=reservations, clock=_admin_clock)
```

- `wire_dependencies`에 `provide_admin_service: create_admin_service`를 추가(R9). `provide_*`는 admin에서 이것 하나.
- auth 구역: `_auth_clock = AuthSystemClock()`을 만들어 `create_auth_service`가 **함수 안에서** `clock=_auth_clock`을 전달한다(D33). 함수 시그니처는 그대로라 `build_auth_service`와 `tests/test_container.py`의 `create_auth_service(marker x4)` 호출은 바뀌지 않는다.
- 예약 쪽은 admin 구역의 `create_reservation_admin`(싱글턴 `NoReservationAdmin`)뿐이다. reservations의 기존 container 구역은 건드리지 않는다.
- 의존 그래프(비순환, R12): `get_db → create_*_repository → create_auth/stores/catalog_service → create_admin_service`. 아무도 admin에 의존하지 않는다. 한 요청 안에서 `Depends(get_db)`가 같은 세션을 돌려주므로 admin과 세 서비스가 한 트랜잭션을 공유한다(R13, auth.md B-9 실험).
- 같은 요청 안에서 `create_stores_service`는 `create_catalog_service`(→ `create_store_port`)와 admin이 **같은 인스턴스를 공유**한다(FastAPI 캐시). 공유해도 상태가 없어 문제없다.
- `src/main.py`: `from admin.presentation.router import router as admin_router` + `app.include_router(admin_router)`. admin은 models가 없어 models import 추가 없음.
- stores.md D15(폐점 시 `OpenOffersPort`로 stores ↔ catalog 생성 순환)는 **이 설계가 만들지 않는다**: 관리자 강제 폐점은 admin이 stores와 catalog를 각각 부르므로 stores 서비스가 catalog를 알 필요가 없다. 상점주 폐점(stores.md 8절)은 여전히 D15가 필요하다(C11).

---

## 8. 기존 동작에 미치는 영향과 정합 이슈 (C-번호)

설계안 작성자는 아래 파일을 고치지 않는다. 오케스트레이터가 사용자 승인 후 소유 에이전트에게 재발주한다.

| ID | 위치 | 이슈 | 영향 / 제안 |
| --- | --- | --- | --- |
| C1 | `docs/design/stores.md:379` D5, `:340` C6, `:319` | "관리자 승인"의 대상이 미정이었다(D5). 이 명세가 **상점주 계정 승인**(`users.status`)으로 정한다. `stores.approval_at`은 "개설 시각"으로 유지(`Store.open`, reference stores.md 개설 시각) | 두 값은 독립이다: 상점주 승인(`users.approved_at`) ≠ 상점 `approval_at`. stores.md D5·C6의 "승인 EP 없음"은 갱신 필요. catalog의 `StoreNotApprovedError`(catalog.md D19, `StoreRef.approved`)는 계속 `approval_at` 유무만 본다 → 의미 변화 없음, 문구만 확인 |
| C2 | `docs/reference/README.md:156`(11번 "관리자 승인 API 없음"), `:85`(상점주 역할 값), 전체 API 목록 표 | admin 9개 EP가 reference에 없다 | `docs/reference/admin.md` 신설 + README 목록에 9행 추가(오케스트레이터). 확인 필요 11번 해소. `error_code` 값 표(`OWNER_NOT_PENDING` 등)도 추가 |
| C3 | `docs/design/auth.md:5`("외부 동작 불변"), `:53` D-상점주승인, `:539` 질문 #3, `:91-92` 2.4 "변경하지 않음", `:101` 3절 "도메인 규칙은 그대로", `:84` 테스트 영향, `:235` 5.1 생성자 | auth.md의 전제 5가지가 깨진다: ① 도메인 엔티티 변경 없음 → `User`·`PointLog` 확장 ② `signup`이 OWNER를 `PENDING`으로 만든다(D4) ③ 로그인·보호 API가 정지·탈퇴 회원을 막는다(D8, D9) ④ `AuthApplicationService` 생성자에 `clock` 추가(D33) ⑤ 포인트 4종이 `balance_after`를 기록 ⑥ (D35) `authenticate`에 `allow_suspended` 인자, 새 의존성 `SuspendedAllowedOwnerUser`(C14) ⑦ (D39) 로그인이 정지된 OWNER에게 토큰을 발급(`ensure_can_login`의 OWNER 예외, auth.md의 "로그인 동작 불변" 전제 변경) | **기존 테스트 영향 (2026-11-05 정정; 이전 "14곳, payments 포함"은 틀림)**: `tests/payments/test_payments_api.py`는 `X-User-Id`·`X-User-Role` 가짜 헤더와 fake 서비스를 쓰고 실제 가입을 하지 않아 **영향 없음**. D4(OWNER → PENDING)로 **깨지는 곳은 가입한 OWNER로 상점을 여는 헬퍼**다(상점 개설이 403이 됨): ① `tests/stores/test_api_db.py:20` `owner_token`(헬퍼, 사용처 다수)과 `:81` `test_open_store_owner_without_name`(직접 가입 후 `POST /v1/stores`) ② `tests/catalog/test_api_db.py:42` `owner_with_store` ③ `tests/reservations/test_api_db.py:24` `seed_offer`(reservations 구현으로 새로 생긴 사용처). 깨지지 않지만 `status` 단언을 추가할 곳: `tests/auth/test_api_db.py:48`(`test_signup_owner_ok`), `:242`(역할 의존성 테스트, 정지·승인 확인과 무관), `tests/auth/test_domain.py:77`(`test_register`), `tests/reservations/test_api_db.py:187`(타 상점주 토큰, PENDING이어도 픽업 403 유지), `tests/stores/test_api_db.py:90` `_owner_id`(레포지토리 직접 사용). 호출 지점 수(정의 포함, `Grep` 집계): `owner_with_store(`·`owner_token(`·`seed_offer(`·`_owner_id(` 합계 62 = catalog 42·stores 11+1(`test_service.py`)·reservations 8. **개별 테스트별 깨짐 수는 미검증**(DB 테스트라 이 환경에서 실행하지 않음). 헬퍼가 상점주를 `APPROVED`로 만들도록 고쳐야 한다(승인 EP를 거치거나 ADMIN fixture·직접 UPDATE로 `status` 지정. `tests/helpers.py`에 `approved_owner_token` 같은 공용 헬퍼를 추가). `tests/test_container.py`는 `create_auth_service(marker x4)` 시그니처가 그대로라 호출 변경 없음, 단 `DEPENDENCY_MODULES`에 `admin.presentation.dependencies`를 추가한다. auth.md의 "84 passed" 기준선은 새 기준선으로 갱신 |
| C4 | `docs/design/auth.md:290`(`AdminUser`·`require_roles` 의미·실패 코드 불변), `:353` | `AdminUser`의 403 문구가 명세와 다르다("접근 권한이 없습니다." vs "관리자 권한이 필요합니다.", 401도 "로그인이 필요합니다." vs "인증이 필요합니다.") | 임시: 유지(D32). 바꾸려면 `User.require_role(*roles, message=...)`와 `require_roles`에 문구 인자 추가가 필요하고 전 모듈 문구가 같이 바뀐다(R15) |
| C5 | `docs/design/auth.md:336`(`/v1/users/me/points` `page>=0`, `total_elements`), `docs/reference/README.md:126-133` | 포인트 조회 페이지네이션이 두 개다: 본인 조회는 0부터·`total_elements`, 관리자 조회(명세 8)는 1부터·`total` | README 공통 확인 5번이 이미 미결. admin은 명세대로 1부터·`total`(D25). 통일 결정 시 `list_points`/`list_point_logs`를 함께 정리 |
| C6 | `docs/design/catalog.md:186` `OPEN_OFFER_STATUSES`, `:208-213` `effective_status` 우선순위, `:667` 도메인 테스트("`OPEN_OFFER_STATUSES`가 `is_open`이 참인 `effective_status` 집합과 같음"), `:816` CI-5 `_status_clause` 일치 테스트 | `OfferStatus`에 `SUSPENDED`가 추가되어 ① 우선순위 표가 바뀌고(3.3절) ② `is_open`이 참인 유효 상태 집합이 `SCHEDULED/ON_SALE/SOLD_OUT/SUSPENDED`가 되어 위 동일성 테스트가 깨지고 ③ `_status_clause` 4종 조건과 신규 `SUSPENDED` 조건을 맞춰야 한다 | catalog.md 3.4·10절·12절 갱신. 기본 목록(`OPEN_OFFER_STATUSES`)에는 SUSPENDED를 넣지 않는다(D20). 동일성 테스트는 "`is_open` 참 집합 − {SUSPENDED}"로 수정하거나 상수를 분리 |
| C7 | `docs/design/catalog.md:777` D56(#10 할인 상세는 인증 없이 중단·마감·품절 모두 조회, 에러는 404 하나), `:754` D23(서비스는 `user_id`만) | 명세 7은 정지 상품을 "목록·검색·상세에서 숨김"이라 D56과 부분 충돌 | D56에 "정지된 할인·정지된 상점의 할인은 소유자 외 404"를 예외로 추가. `get_offer_detail(offer_id)`에 `viewer_id: UUID \| None` 추가(비로그인 허용 유지, D6·D7과 같은 패턴, router는 `OptionalUser`). D56의 "401·403 없음"은 유지 |
| C8 | `docs/design/catalog.md:737-738` D6·D7, `:815` CI-3 | 정지 상점 숨김은 D6·D7(비활성은 소유자만)과 같은 패턴이다 | 재사용: `StoreRef.ensure_visible_to(viewer_id)`. 목록(`list_products`, `list_offers_by_store`)도 소유자 외 404(`StoreNotFoundError`) |
| C9 | `docs/design/catalog.md:615-616` 후속 #3(검색)·#8(주변 할인), `:81-83` StorePort | **정지 상점의 상품을 목록·검색에서 숨기는 규칙을 후속 #3·#8에 적용하기 어렵다.** 두 EP는 여러 상점을 가로지르는 조회라 상점 상태로 거를 방법이 필요한데, catalog는 `stores` 테이블을 join할 수 없다(R11). `find_stores_by_ids`로 가져온 뒤 걸러내면 페이지네이션(`total`)이 틀어진다 | 후속 #3·#8 설계 때 StorePort에 "노출 가능한 상점만 반환하는 질의"(예: 좌표 범위 + 상태 필터를 stores가 수행)를 추가하거나 `ProductModel`/`DiscountOfferModel`에 상점 상태 비정규화 컬럼을 두는 안을 결정해야 한다. 이번 범위(#9, #10 등 상점 단위 조회)는 영향 없음 |
| C10 | `docs/design/catalog.md:818` CI-10, `:819` CI-11, `:825` C9, `:828` C12, `:338` 5.3 잠금 순서 / `docs/design/payments.md:334` C-4, `:405` 4.3.4 | ① admin이 예약 포트 2개를 새로 요구한다(`ReservationAdminPort`). reservations 설계(미작성)에 전달: (D35) 픽업 EP는 `SuspendedAllowedOwnerUser`를 쓰고 상점·할인 정지 상태를 픽업 조건에 쓰지 않는다(C14). `cancel_reserved_for_user`(RESERVED만, 재고 복구, 전액 환불·포인트 복구, `commit` 금지), `has_reserved_for_store`(RESERVED `FOR UPDATE`). ② **잠금 순서 불일치**: catalog는 `product → offer → (예약 포트)`, payments는 `예약 → 결제 → 환불 → 회원`, 예약 취소가 재고를 복구하면 `예약 → offer`가 되어 catalog의 `offer → 예약`과 역순이다(교착 가능) | reservations 설계에 "예약 취소·결제 확정은 offer(필요 시 product)를 **먼저** 잠근 뒤 예약 행을 잠근다"를 요구하고 4.3절의 전역 순서를 공유한다. **(2026-11-05 갱신) reservations가 구현됐지만 사용자 범위 변경으로 이번 라운드에 reservations는 바뀌지 않아 `NoReservationAdmin`을 유지**: 후속 요구는 5.2절 RV1~RV5로 구체화됨(레포 메서드 2, lifecycle 1, application 2, 픽업 의존성 1). 후속 PR은 container 바인딩만 교체. 잠금 순서는 reservations.md 13절 A-3이 "양립"으로 확인(`offer → reservation`, 여러 예약은 `offer_id, id` 순). `reservations.md`(미커밋 사용자 편집 포함)는 이 문서가 수정하지 않는다: 13절 A-1·A-2·A-4·A-6의 "받아야 할 일"을 이 문서의 RV·D41로 대체한다는 점을 reservations.md 담당 갱신 때 반영(A-2의 S-4 안 vs catalog 포트안은 D41 보류, A-6의 `create_reservation_admin()`이 `NoReservationAdmin`을 돌려준다는 단언은 이번 라운드에 유효하고 후속 PR이 교체). **미연계**: 이번 라운드 EP 4는 예약을 취소하지 않고 EP 6 검사는 항상 통과(B-6) |
| C11 | `docs/design/stores.md:324-326` 8절 메모 2·3, D15 | 관리자 강제 폐점은 admin이 조합하므로 stores ↔ catalog 생성 순환을 만들지 않는다. 그러나 상점주 폐점(후속)은 D15가 여전히 필요하다. 또 `has_open_offers_for_store`가 정지된 할인을 "진행 중"으로 세므로 상점주는 정지된 할인이 `sales_end`를 넘길 때까지 폐점할 수 없다(D22) | stores.md 8절 메모에 "정지된 상점은 상점주 폐점 불가(`Store.close` 가드)"와 위 영향 추가 |
| C12 | `docs/design/stores.md:121` `find_by_owner_id`, `:81` 불변식, `:111` `StoreInfo` 구조적 만족, `docs/design/catalog.md:99` `StoreInfo` 필드 | ① `StoreRepository.find_by_owner_id`에 `for_update` 인자 추가 ② `Store`에 `suspended_*`·`closed_reason`·`status` 추가 ③ catalog `StoreInfo` Protocol에 `suspended_at: datetime \| None` 추가(`StoresApplicationService`가 `Store`를 그대로 돌려주므로 stores 쪽 추가 변경 없이 구조적으로 만족) → **tests/catalog의 fake `StoreInfo`에 속성 추가 필요**(catalog.md 10절 #10 때와 같은 문제) | 구현 시 stores·catalog 구현자가 함께 반영 |
| C13 | `docs/design/payments.md:405-413` 4.3.4 `refund_for_cancelled_reservation(waive_penalty=True)`, `:497` R-7 | 명세 4(강제 탈퇴)는 "RESERVED 예약 자동 취소와 재고 복구"만 말하고 **환불을 말하지 않는다.** RESERVED는 결제 완료 상태라 환불 없이 취소하면 고객이 돈과 포인트를 잃는다 | 임시 기본값: 환불·포인트 복구도 한다(D12). `ReservationAdminPort` 계약에 포함(C10). 환불을 원치 않으면 D12를 바꾼다 |
| C14 | `src/auth/application/service.py` `authenticate`(`:90`), `login`(`:80`), `src/auth/presentation/dependencies.py:18-45`, `docs/design/auth.md:290`·`:353`(의존성 별칭 "이름·의미·실패 코드 불변"), `docs/reference/reservations.md` 4 픽업 완료(권한 "상점주(해당 매장)") | 정지 확인은 공통 `authenticate`(`get_current_principal → authenticate`)에 들어가 한 요청당 추가 쿼리는 없고 `Clock`만 쓴다. **D35 확정: 정지된 상점주도 픽업 처리는 가능**해야 하므로 `authenticate`에 `allow_suspended` 키워드 인자(기본 False)를 두고, auth에 예외 의존성 `SuspendedAllowedOwnerUser`를 추가해 픽업 EP 하나만 쓴다(5.5절). auth.md의 "별칭 불변" 전제는 기존 별칭에 한해 유지되고 **새 별칭이 추가**된다. `ensure_can_authenticate` 시그니처가 바뀐다 | auth 구현자: `authenticate`·`User.ensure_can_authenticate`·새 의존성. reservations 설계: 픽업 EP가 `SuspendedAllowedOwnerUser`를 쓰고 상점·할인 상태(정지·폐점·SUSPENDED 할인)를 픽업 가능 여부에 쓰지 않는다. reservations.md(reference)에 "정지된 상점주도 픽업 가능" 주석 추가 제안. 로그인: D39 확정으로 정지된 OWNER는 `login`이 토큰을 발급(`ensure_can_login`의 OWNER 예외), 정지된 CUSTOMER는 403 유지. 로그인 응답으로 정지 상태를 알 수 없는 문제는 C17 |
| C15 | `src/main.py`, `src/container.py`(`create_auth_service`) | 라우터 등록 1줄, container admin 구역·`_auth_clock` 추가. 순서: admin router는 어느 위치든 무관(models 없음) | 구현자 소유 범위(orchestration §4) |
| C16 | `.claude/skills/db-schema/schema.sql`, `SKILL.md` §5 항목 7("상점주 승인 상태: users에 컬럼 없음") | 2절 스키마가 승인되면 항목 7이 해소되고 ERD·관계 목록·표(`users`, `point_log`, `stores`, `discount_offers`)·`status` CHECK 설명을 고쳐야 한다(R14) | 오케스트레이터(`.claude/**` 소유) |
| C17 | `docs/reference/auth.md` 로그인 응답(`access_token`, `token_type`), `docs/design/auth.md:333`(`TokenResponse`), 토큰 클레임(`sub`, `role`, `jti`, `exp`, reference README 인증 절) | D39 확정으로 정지된 OWNER가 로그인에 성공하지만 응답·토큰에는 상태가 없어 클라이언트가 정지 사실을 알 수 없다. 이후 호출에서 403 "정지된 계정입니다."를 받고서야 안다 | **해소 (2026-11-05, 사용자: 선택지 ① 확정 → D40, 5.5절).** 이하는 검토했던 선택지: ① 로그인 응답에 `status` 추가(하위 호환 추가 필드, `TokenResponse` 변경) ② 토큰 클레임에 상태 추가(토큰 발급 후 상태 변경과 어긋남) ③ 그대로 두고 `GET /v1/users/me`로 확인(단 이 EP도 정지 OWNER에게는 403이라 불가) ④ `users/me`도 정지 OWNER 예외. (해소로 "임시: 변경 없음"은 폐기) |
| C18 | `src/auth/presentation/router.py:83-100`(`GET /v1/admin/users/{user_id}`, `POST /v1/admin/token-blacklist/purge`), `docs/reference/README.md`(관리자 API `/v1/admin/...`, 목록 30·31번), `docs/reference/auth.md` 6·7 | D2 변경(`/v1/admin`)으로 관리자 EP가 두 라우터(auth, admin)에 나뉜다. 경로는 겹치는 곳(`/v1/admin/users/{user_id}` GET vs DELETE)이 있지만 메서드가 달라 충돌 없음(B-11). `UserResponse`에 D38 `status`가 붙어 기존 EP 응답도 바뀐다 | **임시(D42)**: 기존 2개는 auth에 둔다. reference는 `admin.md`를 새로 만들 때(C2) "관리자 회원 조회는 auth.md 6"으로 상호 링크. 일원화하려면 사용자 결정 후 별도 작업 |
| C19 | **`docs/design/stores.md`**(상점주 폐점 EP `POST /v1/stores/{store_id}/close`, 다른 설계자 담당) | admin이 stores에 요구하는 것: ① `Store.close(now)`에 정지된 상점 가드 `StoreSuspendedError`(400 `STORE_SUSPENDED`, 3.2절) ② 상점주 폐점도 정지 상태 `Store.suspended_at`(S10)을 같은 이름으로 쓸 것 ③ `StoreRepository.save`가 `closed_at`·`closed_reason`·`suspended_*`를 저장(4.2절) ④ 상점주 폐점의 `StoreHasReservedReservationsError`는 admin과 같은 예외·`error_code`(`STORE_HAS_RESERVED_RESERVATIONS`)를 쓸 것(stores.md 쪽이 `OpenOffersPort`·예약 포트를 어떻게 연결하든 R12 순환 주의, C11) | 이 문서는 EP를 설계하지 않는다. stores.md 재개 후 ①~④ 정합을 대조 |
| C20 | `docs/design/reservations.md` 13절·14절, `tests/reservations/test_wiring.py`(`NoPaymentRefund` 단언) | reservations.md 14절 W-8이 `NoPaymentRefund`·`InMemoryReservationPort`를 교체하는 작업을 계획한다. **이번 라운드에 reservations는 바뀌지 않는다.** 후속에서 RV1~RV5와 W-8이 끝나면 container 바인딩 교체만으로 admin EP 4의 취소·환불·재고 복구가 동작한다(admin 코드 변경 불필요). W-8이 `create_refund_port`·`create_stock_port`의 반환 타입을 바꿔도 `StockPort`·`RefundPort` 메서드 시그니처가 유지돼야 한다 | 교체 시 admin 서비스·테스트는 영향 없음. 통합 테스트(결제 → RESERVED → 강제 탈퇴 → 환불·재고 복구)는 W-8 이후에만 가능해 **그 전에는 만들지 않고 "미연계"로 보고**(skip으로 숨기지 않음, R16) |

---

## 9. 테스트 계획 (요약)

DB 테스트는 `@pytest.mark.db`, skip은 통과가 아니다(R16). ADMIN 계정은 fixture가 직접 insert한다(D29).

- **auth domain**: `User` 불변식(상태별 필수 필드, ADMIN·CUSTOMER의 PENDING 거부), 전이표 전부(승인·거부·정지·탈퇴), 에러 순서(사유 → until → 이미 정지 → 탈퇴 → 관리자), `effective_status`의 만료 경계(`until == now`는 만료), 만료된 정지의 재정지, `ensure_can_login`(PENDING·REJECTED 허용, **정지된 OWNER 허용(D39)**, 정지된 CUSTOMER 403, WITHDRAWN은 역할 무관 401)/`ensure_can_authenticate`(SUSPENDED 403, WITHDRAWN 401, `allow_suspended=True`면 SUSPENDED 통과·WITHDRAWN은 여전히 401), `grant_points` 순서와 int4 한도, `PointLog.record` 필수 `balance_after`·GRANT 부호.
- **stores domain**: `suspend`/`suspend_if_active`(폐점·이미 정지는 False), `ensure_force_closable`/`force_close` 에러 순서, `status` 파생(CLOSED > SUSPENDED > ACTIVE), 정지 상태에서 상점주 `close` 거부.
- **catalog domain**: `suspend`(순서, 종료·SOLD_OUT·SCHEDULED), `effective_status` 우선순위 6단, `end_sale` 멱등, 정지된 할인에 대한 `pause/resume/close/apply_changes/adjust_stock/relist` 거부, `StoreRef` 정지 가시성·등록 가드.
- **admin service (fake 포트 4개 + fake Clock)**: EP별 `commit` 1회·실패 시 0회; 3에서 상점주만 `suspend_stores_of_owner` 호출·고객은 미호출·`suspend_user` 실패 시 상점 호출 0회; 4의 호출 순서(`get_account → check_withdrawable → lock_store_of_owner → end_all_sales → cancel_reserved → has_reserved → close_store_by_admin → withdraw_user → commit`)를 fake가 기록해 단언, 고객은 상점 단계 생략, 예약 남음이면 `commit == 0`; 6의 순서(`check_force_closable → end_all_sales → has_reserved → close → commit`); 모든 모듈 호출이 `commit=False`; 포트에 없는 메서드를 부르지 않음(fake가 Protocol만 구현, R10).
- **infrastructure (DB)**: 새 컬럼 왕복(tz 유지, NULL), `ck_users_status`·`ck_point_log_type`(GRANT)·offer status CHECK, `find_open_by_store_for_update`·`find_all_by_store_for_update`의 정렬, `_status_clause`와 `effective_status` 일치(SUSPENDED 포함), 동시 승인 2건 중 1건만 성공, 동시 지급 2건이 잔액·`balance_after` 합과 일치, 지급 이력과 잔액이 같은 트랜잭션(중간 예외 시 둘 다 없음).
- **presentation (DB)**: 9개 EP 각각 200/201, 401(`WWW-Authenticate`), 403(CUSTOMER·OWNER 토큰), 404, 400 각 케이스의 `error_code`와 본문 형식(R7). 빈 사유의 400 문구가 명세 문구와 같은지. EP 4는 `client.request("DELETE", ..., json=)`(B-9). 연쇄: 상점주 정지 → 소유 상점 `status == SUSPENDED`, 같은 상점주 로그인 403, 이미 발급한 토큰으로 보호 API 403, 정지 만료 후 로그인 성공. **(D39) 정지된 OWNER 로그인 200(토큰 발급)·그 토큰으로 픽업 외 보호 API 403, 정지된 CUSTOMER 로그인 403 `FORBIDDEN` "정지된 계정입니다.", 정지된 사용자의 틀린 비밀번호는 401 `INVALID_CREDENTIALS`, 탈퇴한 OWNER·CUSTOMER 로그인 401.** **정지된 상점주의 토큰으로 픽업 EP는 200(해당 매장 RESERVED), 그 외 보호 API(예: 상품 등록·`GET /v1/users/me`)는 403, 탈퇴한 상점주 토큰은 픽업도 401**(D35, reservations 구현 후). 강제 탈퇴 후 로그인 401, 이메일 재가입 409. 정지 상점의 상품 목록·상세가 비소유자에게 404, 소유자에게 200. 정지 할인이 공개 목록·상세에서 사라짐. 승인되지 않은 상점주의 `POST /v1/stores` 403.
- **(후속, 이번 라운드 제외) reservations 새 메서드 테스트 (RV1~RV5, `tests/reservations/`는 이번에 바뀌지 않음)**: fake `StockPort`·`RefundPort`·fake 레포로 ① `cancel_reserved_for_user`가 RESERVED만 취소(PENDING_PAYMENT·CANCELLED·PICKED_UP 제외), 건당 `stock.release(quantity)` 호출, 환불 `waive_penalty=True`, 취소 수 반환, `commit` 0회 ② 잠금 후 상태 재확인(스냅샷 RESERVED, 잠금 시점 CANCELLED면 건너뛰고 재고·환불 호출 0회) ③ 호출 순서 `offer_id, id` 오름차순 ④ `has_reserved_for_offers` 빈 목록 False·RESERVED만 True ⑤ DB: 두 레포 메서드의 정렬·상태 필터. 픽업 EP가 정지된 OWNER 토큰을 허용(RV5). 환불·재고가 자리표시자인 동안의 **통합 단언은 "예약 상태만 CANCELLED"까지**(재고·환불 단언은 만들지 않고 미연계로 보고, C20).
- **D40**: 로그인 응답 `status`(5.5절 테스트 목록). **D2**: 9개 EP URI가 모두 `/v1/admin/...`, 기존 auth 관리자 EP 2개가 그대로 동작(`tests/auth/test_admin_api.py` 불변), `DELETE /v1/admin/users/{id}`와 `GET` 공존, 이전 `/admin/...`는 404.
- **조립**: `wire_dependencies` 후 `provide_admin_service` 매핑(R9), `import main` 성공(R12), `tests/test_container.py`의 `DEPENDENCY_MODULES`에 admin 추가, `create_reservation_admin()`이 `NoReservationAdmin`을 돌려주는지(후속 교체 시 이 단언을 바꿔 상기). `NoReservationAdmin` 단위 테스트: 0·False. admin 서비스 테스트(fake 포트)에서 예약 포트가 호출 순서에 따라 불리는지만 단언하고 재고·환불 단언은 만들지 않는다(미연계, R16).
- 완료 게이트(backend-invariants §7): `uv run python .claude/skills/layer-check/check_layers.py` 위반 0(기준선 payments 2건 제외 후 새 위반 0), `(cd src && uv run python -c "import main")` 성공, `uv run pytest -rs` failed 0·db 마커 skip 0.

---

## 10. 모듈 밖 변경 제안 (이 문서는 쓰지 않는다)

- `.claude/skills/db-schema/schema.sql`·`SKILL.md`: 2절 스키마 반영(R14), 5절 항목 7 해소 표시(C16).
- `docs/reference/admin.md` 신설, `docs/reference/README.md` 목록·확인 필요 11번·역할/상태 값 표(상점주 승인 상태 값 추가) 갱신(C2).
- `docs/design/{auth,stores,catalog}.md`: C1, C3~C8, C11, C12 반영 여부 검토(소유 에이전트에게 재발주).
- `docs/design/reservations.md`(이 문서는 쓰지 않음, 미커밋 사용자 편집 있음): **후속** reservations 작업 때 13절 A-1·A-2·A-4·A-6을 이 문서의 RV1~RV5·D41로 갱신(C10, C20). 이번 라운드 변경 없음.
- **`docs/reference/auth.md` (D40 함의, 오케스트레이터)**: 로그인 응답 예시와 필드 표에 `status`(string, 로그인 시점 유효 상태 `APPROVED`/`PENDING`/`REJECTED`/`SUSPENDED`) 추가. 정지된 OWNER는 로그인 성공(`status: "SUSPENDED"`), 정지된 CUSTOMER 403, 탈퇴 401 에러 행 추가. 가입·내 정보 응답의 `status`(D38), 6번 관리자 회원 조회 응답도 같이 갱신. `docs/reference/README.md`는 상점주 승인 상태 값과 admin 9개 EP(C2, `/v1/admin/...`) 추가.
- 구현자가 건드리는 모듈 밖 파일 목록은 12절.
- `src/container.py`: admin 구역, auth 구역에 `_auth_clock`. `src/main.py`: admin router 등록. `src/error_handlers.py`: **변경 없음**(409 없음, 새 `ValueError` 하위 클래스는 `error_code`로 400, `PermissionError` 하위는 `FORBIDDEN` 고정).
- `pyproject.toml`·`.env.example`: 변경 없음.
- `tests/helpers.py`·`tests/{stores,catalog,reservations}`(+ `tests/auth` status 단언): 가입한 OWNER를 APPROVED로 만드는 헬퍼(C3). `tests/payments`는 영향 없음.
- 시연용 ADMIN: 이미 `ADMIN_EMAIL`·`ADMIN_PASSWORD` 시드가 있다(B-7, D29). 추가 시드 불필요.

---

## 11. 결정 표와 질문 목록 (D-번호, 임시 기본값)

2026-11-04 사용자 확정: D2(2026-11-05 `/v1/admin`으로 변경), D4, D10, D12, D13, D35, D39. **2026-11-05 사용자 확정: D1, D3(+2절 S1~S12 전체), D5~D9, D11, D14~D34, D36~D38은 아래 값 그대로, D40 신설.** **D41·D43·D44는 보류(reservations 작업 시 결정), D42는 임시 기본값 적용(사용자 미확정)이다.** 코드에서는 "코드 위치" 열의 한곳에 모아 바꾸기 쉽게 한다. 번호는 코드·테스트가 주석으로 참조하므로 다시 매기지 않는다.

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 | 코드 위치 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | 모듈 배치 | 요청 판단 1 | 별도 `src/admin`(오케스트레이션) + 규칙은 소유 컨텍스트 | layer-architecture §3.4·§4, R11~R13. 1.1절 비교 | `src/admin/**` | **확정**(사용자, 2026-11-05) |
| D2 | URI 접두사 | 명세 `/admin/...`, reference README "관리자 전용 API는 `/v1/admin/...`", 기존 auth 관리자 EP | `ADMIN_PREFIX = "/v1/admin"` | R15, reference README | `admin/presentation/router.py` 상수 1곳 | **확정 (2026-11-05 변경: /admin → /v1/admin)** (최초 2026-11-04 `/admin` 확정) |
| D3 | `users.status` 모델 | 명세 1~4 | 컬럼 `status`(5값 CHECK) + 시각·사유 컬럼 | 상태 값이 5개라 시각만으로 파생 불가 | `UserModel`, `UserStatus` | **확정**(사용자, 2026-11-05) |
| D4 | 상점주 가입 직후 상태 | 명세 1, reference stores.md 403 | OWNER 가입 → `PENDING`, CUSTOMER → `APPROVED`. DDL 기본값 `APPROVED`(기존 행 보존) | 명세 "승인 대기(PENDING) 상점주" | `User.register`, S1 | **확정**(사용자, 2026-11-04) |
| D5 | PENDING·REJECTED 상점주의 로그인·보호 API | reference stores.md "403 승인 대기 중인 상점주 계정입니다." | **허용**. 상점 개설·폐점만 403(`ApprovedOwnerUser` 의존성) | 403 문구가 "로그인 후 개설 시도"를 전제 | `ensure_approved_owner`, `auth.presentation.dependencies` | **확정**(사용자, 2026-11-05) |
| D6 | 상점주 승인과 `stores.approval_at`의 관계 | stores.md D5, 요청 판단 2 | 독립. `approval_at`은 "개설 시각" 유지, 승인 상태는 `users.status` | stores.md D5 "개설 시각 = approval_at" | C1 | **확정**(사용자, 2026-11-05) |
| D7 | approve/reject 대상이 OWNER가 아닌 경우 | 명세 1·2 404 문구 | 404 "상점주를 찾을 수 없습니다."(고객·관리자 ID 포함) | 문구가 "상점주" 한정 | `User.approve_owner` | **확정**(사용자, 2026-11-05) |
| D8 | 정지 회원의 로그인·보호 API 응답 | 명세 3 "사용할 수 없다"(코드 미명시) | 403 `FORBIDDEN` "정지된 계정입니다."(사유·기간 비노출). 로그인은 **비밀번호 검증 성공 후**에만 확인 | `PermissionError` 하위라 핸들러 변경 불필요, 계정 열거 방지. **로그인은 OWNER 예외가 생겼다: 정지된 OWNER는 로그인 허용(D39 확정). 정지된 CUSTOMER 로그인·모든 정지 회원의 보호 API(픽업 EP 제외, D35)는 이 행대로 403** | `User.ensure_can_login`, `ensure_can_authenticate` | **확정**(사용자, 2026-11-05) |
| D9 | 탈퇴 회원 처리 | 명세 4 | 로그인 401 `INVALID_CREDENTIALS`, 보호 API 401 "유효하지 않은 토큰입니다.", 같은 이메일 재가입 409 유지(soft delete라 행이 남음) | 존재하지 않는 계정처럼 보이게 | 위와 동일 | **확정**(사용자, 2026-11-05) |
| D10 | 정지 해제 EP, `suspended_until` 경과 | 요청 판단 5 | 해제 EP 없음. 만료는 **조회 시 계산**(`effective_status`)로 자동 해제(회원만). 무기한 정지·상점·할인 정지는 해제 수단 없음 | catalog D3과 같은 방식(스케줄러 없음) | `User.effective_status` | **확정**(사용자, 2026-11-04). 무기한 정지·상점·할인 정지의 해제 수단 부재는 후속 과제 |
| D11 | 회원 정지 연쇄 | 명세 3, 요청 판단 5 | 소유 상점이 이미 정지·폐점이거나 없으면 건너뜀(오류 없음). 회원 정지가 끝나도 상점은 자동 해제 안 됨 | 연쇄는 "함께 정지" 의미, 해제 EP 없음 | `Store.suspend_if_active`, 5.4절 EP 3 | **확정**(사용자, 2026-11-05) |
| D12 | 강제 탈퇴의 예약 취소 범위·환불 | 명세 4, payments.md 4.3.4 | 본인의 `RESERVED`만 취소(PENDING_PAYMENT는 대상 아님), 재고 복구 + **전액 환불·포인트 복구**(위약금 면제)를 예약 모듈에 위임. 위험: PENDING_PAYMENT 예약의 재고가 영구 점유될 수 있다(reservations.md "결제 제한 시간" 미정과 같은 문제) | 명세 문구 그대로 + 환불은 payments R-3·R-7 | `ReservationAdminPort.cancel_reserved_for_user` | **확정**(사용자, 2026-11-04) |
| D13 | 탈퇴 대상 상점주의 상점에 **타 고객의 RESERVED 예약**이 남은 경우 | 명세 4 vs 6 | 폐점 규칙(6)과 같게 400 `STORE_HAS_RESERVED_RESERVATIONS`로 **전체 롤백**(탈퇴도 불가). 대안: 일괄 취소+환불 후 진행 | 명세 6 "처리되지 않은 RESERVED가 있으면 폐점 불가"를 우회하지 않음 | 5.4절 EP 4 ⑥ | **확정**(사용자, 2026-11-04) |
| D14 | 탈퇴 사유 저장 | 명세 4(`reason` 필수, 저장 컬럼 미명시) | `users.deleted_reason`(S5)에 저장, 같은 사유를 상점 `closed_reason`에도 사용 | 필수 입력을 버리지 않음 | S5, `User.withdraw` | **확정**(사용자, 2026-11-05) |
| D15 | `WITHDRAWN`과 `deleted_at` | 명세 4, 요청 판단 5 | 둘 다 저장, `WITHDRAWN`이면 `deleted_at` 필수(불변식) | soft delete | `User.__init__` | **확정**(사용자, 2026-11-05) |
| D16 | 상점 `status` 저장 방식 | 요청 판단 2 | 컬럼 없이 파생(CLOSED > SUSPENDED > ACTIVE). 대안: `status` 컬럼(이중 상태 위험) | 단일 진실원(`closed_at`·`suspended_at`) | `Store.status`, S10 | **확정**(사용자, 2026-11-05) |
| D17 | 정지 상점의 영향 | 명세 5 | 소유자 외 상품·할인 목록·상세 404, 신규 상품·할인 등록 400 `STORE_SUSPENDED`, 상점주 폐점 400, **기존 RESERVED 예약의 픽업은 허용**(예약 모듈에 요구) | 명세 5, catalog D6·D7 패턴 | `StoreRef.ensure_visible_to`/`ensure_can_register`, `Store.close` | **확정**(사용자, 2026-11-05) |
| D18 | 상점 폐점 시 상품 처리 | 명세 6 "상품은 모두 판매 종료" | 진행 중(`is_open`) 할인을 `end_sale`로 일괄 종료(재고·stock_log 불변). 상품 `is_active`는 바꾸지 않음 | catalog D34·D40과 같은 종료 방식 | `end_all_sales_of_store` | **확정**(사용자, 2026-11-05) |
| D19 | 할인 정지 표현 | 명세 7 | 저장 `status = SUSPENDED` + `suspended_*`, `is_active`는 불변. `effective_status` 우선순위 CLOSED(비활성) > SUSPENDED > 시간경과 | `is_active=false`로 두면 상점주가 `is_active:true`로 우회 | `DiscountOffer.suspend` | **확정**(사용자, 2026-11-05) |
| D20 | 정지된 할인의 소유자 조작·노출 | 명세 7 | 상점주의 중단·재개·수정·재고조정·재등록 400 `OFFER_SUSPENDED`. 공개 목록·상세 404, 소유자는 상세 조회 가능. 공개 목록의 `status` 값에 SUSPENDED 불허 | 우회 방지, 숨김 | `DiscountOffer` 가드, `get_offer_detail(viewer_id)` | **확정**(사용자, 2026-11-05) |
| D21 | 할인 정지 가능 범위 | 명세 7 | `SCHEDULED`·`ON_SALE`·`SOLD_OUT` 가능. 비활성·판매 마감 경과는 400 `OFFER_SALES_ENDED` | 명세 "판매가 종료된 상품" | `DiscountOffer.suspend` | **확정**(사용자, 2026-11-05) |
| D22 | 정지된 할인이 "진행 중"인가 | catalog D4, stores.md D9 | 진행 중으로 센다(중복 등록·상점주 폐점 차단) | 정지로 제약을 우회하지 못하게 | `DiscountOffer.is_open` 불변 | **확정**(사용자, 2026-11-05) |
| D23 | 포인트 `type`, 새 컬럼 | 명세 8·9, `schema.sql` point_log | `type` = `point_type` 그대로(`GRANT` 추가, 명세의 `GRANT \| USE`는 부분집합). `reason` NULL 허용(시스템 이벤트), `balance_after`는 신규 전부 기록·기존 NULL, `created_by` NULL 허용 | 정보 손실 없음. **USE의 발생처는 payments(결제 시 포인트 사용)이고 admin은 USE를 만들지 않는다** | S6~S9, `PointLog` | **확정**(사용자, 2026-11-05) |
| D24 | 포인트 지급 대상·한도 | 명세 9 | 정지·미승인·관리자 계정에도 지급 가능(탈퇴만 거부). 건당 상한 없음, 잔액이 `INTEGER` 한도(2,147,483,647)를 넘으면 400 | 명세에 없는 규칙을 만들지 않음, DB 오버플로 방어 | `User.grant_points`, `POINT_MAX_BALANCE` | **확정**(사용자, 2026-11-05) |
| D25 | 포인트 조회 페이지네이션 | 명세 8, README 공통 5 | 1부터, `size` 1~100(기본 20), 위반 400 `INVALID_PAGE`, 응답 `total` | 명세 | `list_points` | **확정**(사용자, 2026-11-05) |
| D26 | 요청 검증 오류 코드·문구 | 명세 에러 400, B-8 실행 | 400 `VALIDATION_ERROR`(핸들러 실제 동작과 일치). 사유·수량 문구는 도메인이 낸다(스키마에 길이 제약 없음). **필드 누락·타입 오류의 문구는 일반 형식(`필드: 오류`)**이라 명세와 다름 | R15, `error_handlers.py` | `schemas.py` | **확정**(사용자, 2026-11-05) |
| D27 | 사유 길이 상한 | 명세에 없음 | 500자(컬럼 `VARCHAR(500)`) | 컬럼 제안 | 각 도메인 `REASON_MAX_LENGTH` | **확정**(사용자, 2026-11-05) |
| D28 | 감사 기록(처리 관리자) | 요청 판단 5 | 별도 테이블 없음. 명세가 정한 `point_log.created_by`만 저장. 후속 후보: `admin_audit_log(admin_id, action, target, reason, created_at)` | 명세에 없음 | - | **확정**(사용자, 2026-11-05) |
| D29 | ADMIN 계정 확보 | B-7 | 회원가입 불가 유지. 테스트는 fixture로 직접 insert(또는 `ensure_admin`). **2026-11-05 보강**: 시연용 계정은 이미 `ensure_admin` + `ADMIN_EMAIL`·`ADMIN_PASSWORD` 시드로 만들 수 있다(B-7), 추가 시드 불필요 | stores.md 7절 시드안 A의 R16 주의와 동일 | `tests/helpers.py` | **확정**(사용자, 2026-11-05) |
| D30 | admin의 다른 모듈 접근 | R11 | admin이 포트 4개 정의, 각 모듈 서비스가 구조적으로 만족(예약 포트는 이번 라운드 `NoReservationAdmin`, 후속 PR이 바인딩 교체, B-6) | layer-architecture §3.4 2행, catalog `StorePort` 선례 | `admin/application/ports.py`, container | **확정**(사용자, 2026-11-05) |
| D31 | admin domain 구성 | layer-check(4계층 폴더 필수) | 엔티티 없음, `Clock`만 | R3(빈약한 엔티티 금지) | `admin/domain/service.py` | **확정**(사용자, 2026-11-05) |
| D32 | 401·403·404 문구 | 명세 vs 현재 `AdminUser`·catalog | 현재 문구 유지(코드는 일치). EP 7의 404는 catalog 기존 "할인 판매를 찾을 수 없습니다." | 전 모듈 일관성, R15 불일치는 여기서 보고 | C4 | **확정**(사용자, 2026-11-05) |
| D33 | auth `Clock` | 정지 만료 계산 | auth에 모듈별 `Clock`(domain/service.py ABC, infrastructure `SystemClock`)을 두고 `AuthApplicationService`에 필수 인자 추가 | stores D13·catalog D21과 같은 선택 | auth `domain/service.py`, container `_auth_clock` | **확정**(사용자, 2026-11-05) |
| D34 | 잠금 순서 | 4.3절 | stores → products → discount_offers → pickup_reservations → payments → users, `id` 오름차순 | catalog.md 5.3, payments.md C-4 | 각 서비스 | **확정**(사용자, 2026-11-05) |
| D35 | 정지된 상점주의 픽업 | 명세 3 vs 5 | **임시 기본값에서 변경.** 정지된 상점주도 자기 상점(연쇄 정지 포함)의 기존 RESERVED 예약 **픽업 처리는 가능**하고, 그 외 보호 API는 명세 3대로 차단. 구현: `authenticate(allow_suspended=)` + 픽업 EP 전용 의존성 `SuspendedAllowedOwnerUser`(5.5절) | 명세 5 "기존 RESERVED 예약은 유지되어 픽업 처리가 가능"을 우선 | `User.ensure_can_authenticate`, `auth.presentation.dependencies`, reservations 픽업 router, C14 | **확정**(사용자, 2026-11-04) |
| D39 | 정지된 상점주의 **로그인** | D35 파생 | **임시 기본값(로그인 차단)에서 변경.** 정지된 OWNER는 로그인 가능(정지 기간 중 픽업 처리 지속, D35). 로그인 후 픽업 EP 외 보호 API는 403 유지. 정지된 CUSTOMER 로그인은 D8대로 403, 탈퇴는 역할 무관 401(D9) | 사용자 결정(명세 3 "로그인 불가"보다 명세 5 픽업 지속을 우선) | `User.ensure_can_login`(OWNER 분기), 로그인 응답 상태 노출은 C17 | **확정**(사용자, 2026-11-04) |
| D36 | 정지 가능한 회원 상태 | 명세 3 | `APPROVED`만. `PENDING`·`REJECTED`는 400 `USER_NOT_SUSPENDABLE`(**명세에 없는 에러**) | 정지 종료 후 복귀 상태를 하나로 고정 | `User.suspend` | **확정**(사용자, 2026-11-05) |
| D37 | 미승인 상점(`approval_at` NULL)의 강제 폐점 | stores 불변식 | 기존 규칙대로 400 "승인되지 않은 상점은 폐점할 수 없습니다." (API로 만든 상점은 항상 승인됨) | stores.md D4 | `Store.force_close` | **확정**(사용자, 2026-11-05) |
| D38 | 응답에 `status` 노출 | reference auth.md | 가입·내 정보 `UserResponse`에 `status` 추가(가입 직후 PENDING을 알 수 있도록) | 추가 필드라 하위 호환 | auth `schemas.py` | **확정**(사용자, 2026-11-05) |

| D40 | 로그인 응답의 상태 노출 (C17 해소) | C17, 사용자 선택지 ① | `TokenResponse`에 `status: str`(= `user.effective_status(now)` 값: `APPROVED`/`PENDING`/`REJECTED`/`SUSPENDED`) 추가. `login`은 `LoginResult(token, status)` 반환. JWT 클레임 불변, 사유·기간 비노출 | 사용자 결정(하위 호환 추가 필드), D8·D39 | auth `service.py`·`schemas.py`·`router.py`, 5.5절, 10절(reference auth.md) | **확정**(사용자, 2026-11-05) |
| D41 | 매장 단위 RESERVED 예약 조회 방법 (`has_reserved_for_store`) | reservations.md A-2·C-8, B-6 ⑤ | **(b) catalog 포트안**: catalog가 상점의 모든 할인 ID를 제공하고 reservations 쪽이 `has_reserved_for_offers(offer_ids)`로 조회한다. 어느 안이든 admin 포트는 `has_reserved_for_store(store_id)` 그대로이고 container 어댑터가 흡수한다. **이번 라운드에는 구현하지 않으며(범위 변경) catalog 메서드도 만들지 않는다 = 더 작은 변경.** **(a) S-4(`pickup_reservations.store_id` 스냅샷 컬럼)는 기각**: 스키마 변경·기존 행 백필·reservations 모델 수정이 필요하고, reservations.md가 S-4를 미승인으로 유지 중이며, (b)는 기존 테이블·ID만 쓰므로 R11·R14에 영향 없음. 비교: (a)는 한 번의 인덱스 조회이고 잠금 범위가 정확하지만 마이그레이션이 필요(B-10), (b)는 `IN (...)` 쿼리 1회가 늘고 할인 수가 매우 많은 상점에서 느릴 수 있음 | R11(조인 금지)·R14(스키마 변경은 승인 필요) | (보류 중, 이번 라운드 코드 없음) 후속: catalog `find_ids_by_store`·`list_offer_ids_of_store`(삭제됨), reservations RV1·RV4. admin 포트는 `has_reserved_for_store(store_id)`로 고정 | **보류 (reservations 작업 시 결정)** |
| D42 | 기존 auth 관리자 EP 2개와 새 admin 라우터의 공존 | D2 변경, B-7, B-11, C18 | 기존 `GET /v1/admin/users/{user_id}`·`POST /v1/admin/token-blacklist/purge`는 **auth 라우터에 유지**, 새 admin 라우터는 9개 EP만 추가. 경로 충돌 없음(같은 경로라도 메서드가 다름, B-11). 대안: 두 EP를 admin 라우터로 이동(일원화, reference·테스트 수정 필요) | 변경 최소, 소유 컨텍스트 유지, reference auth.md 6·7 이미 존재 | `auth/presentation/router.py`(불변), `admin/presentation/router.py` | **임시 (기본값 적용, 사용자 미확정)** |
| D43 | 자리표시자 동안 EP 4의 동작(D12 효력) | B-6, R16 | **이번 라운드: `NoReservationAdmin`이라 EP 4는 예약을 취소하지 않는다(재고·환불·포인트 변화 없음).** 후속 실제 구현 뒤에도 재고 `release` no-op·`NoPaymentRefund`가 남아 있으면 상태만 취소된다. 구현체가 교체되면 admin 코드 변경 없이 D12 완전 동작. 이 상태를 막으려면(자리표시자가 남은 동안 EP 4가 예약이 있는 회원의 탈퇴를 거부하는 안) 별도 결정 필요: 기본은 **막지 않음** | D12는 확정이지만 의존 구현이 아직 없음. 환불 없는 취소는 고객 손실 위험이므로 사용자 인지 필요 | `ReservationApplicationService.cancel_reserved_for_user`(RV3), container(자리표시자 교체) | **보류 (reservations 작업 시 결정)** |
| D44 | 예약 취소 시 재고 `stock_log`의 `user_id`·사유 | RV2, reservations `StockPort.release(user_id, reason)` | `user_id = 예약자`(기존 `cancel_for_refund`와 같음, 관리자 ID는 포트 시그니처에 없음), `reason`은 admin이 넘기는 탈퇴 사유 문자열 | 기존 `ReservationLifecycleService.cancel_for_refund` 선례, 포트 시그니처 불변 | RV2 | **보류 (reservations 작업 시 결정)** |

확정 현황 (2026-11-05): **확정** D1~D40 전부(D2는 `/v1/admin`으로 변경, D3·S1~S12 확정, D40 신설. D35는 reservations 픽업 router 교체가 후속이라 부분 효력). **임시(기본값 적용, 사용자 미확정)**: D42. **보류(reservations 작업 시 결정)**: D41, D43, D44.

## 12. 구현이 건드리는 파일 (모듈별, 쓰기 소유권 기준)

| 소유 | 파일 | 내용 |
| --- | --- | --- |
| **admin** (신규) | `src/admin/__init__.py`, `domain/{__init__,service}.py`, `infrastructure/{__init__,clock,reservation_admin}.py`, `application/{__init__,ports,service}.py`, `presentation/{__init__,schemas,dependencies,router}.py`, `tests/admin/**` | 9개 EP, 포트 4개, Clock, 임시 `NoReservationAdmin` |
| **auth** | `src/auth/domain/{user,point_log,exceptions,service}.py`(+ `Clock`), `src/auth/infrastructure/{models,repositories}.py`(+ `SystemClock` 파일), `src/auth/application/service.py`(admin 메서드, `clock`, `LoginResult`), `src/auth/presentation/{dependencies,schemas,router}.py`(`SuspendedAllowedOwnerUser`, `ApprovedOwnerUser`, `TokenResponse.status`, `UserResponse.status`), `tests/auth/**` | S1~S9, D4·D8·D9·D35·D38·D39·D40 |
| **stores** | `src/stores/domain/{store,exceptions}.py`, `src/stores/infrastructure/{models,repositories}.py`, `src/stores/application/service.py`, `tests/stores/**` | S10, 정지·강제 폐점 메서드, `find_by_owner_id(for_update)`. 상점주 폐점 EP는 **stores.md 담당**(C19)이라 이 목록에서 제외, `Store.close` 정지 가드만 공유 |
| **catalog** | `src/catalog/domain/{discount_offer,exceptions,...}`, `src/catalog/domain/repository/{discount_offer,product}_repository.py`, `src/catalog/infrastructure/{models,repositories}.py`, `src/catalog/application/{service,ports}.py`, `tests/catalog/**` | S11, 정지·종료, `find_open_by_store_for_update`·`find_all_by_store_for_update`(`find_ids_by_store`는 이번 라운드 제외), `StoreRef`·`StoreInfo` 정지 속성 |
| **reservations** | **없음** (`src/reservations/**`·`tests/reservations/**` 불변, 사용자 범위 변경) | 후속(reservations 담당): RV1~RV5(5.2절), 픽업 router의 `SuspendedAllowedOwnerUser` 교체(D35 부분 효력), container 바인딩 교체 |
| 공용(오케스트레이터 조정 가능) | `src/container.py`(admin 구역, `_auth_clock`), `src/main.py`(admin router 1줄), `tests/helpers.py`, `tests/test_container.py` | `error_handlers.py`·`pyproject.toml`·`.env.example` 변경 없음 |
| 오케스트레이터(`.claude/**`, `docs/reference/**`) | `.claude/skills/db-schema/{schema.sql,SKILL.md}`(S1~S12, C16), `docs/reference/{admin.md 신설, README.md, auth.md}`(C2, D40) | 이 문서는 쓰지 않음 |

구현 순서 제안: auth → stores → catalog(서로 독립 가능, 단 `container.py`·`main.py`·`tests/helpers.py`는 순차) → admin. 단 C3 때문에 `tests/reservations/test_api_db.py:24`의 `seed_offer`가 OWNER 승인 없이는 깨진다: **reservations 테스트는 이번에 못 고치므로**, 깨짐을 막으려면 D4의 영향을 `tests/helpers.py`의 `token_for(..., "OWNER")`가 자동 승인하도록 공용 헬퍼에서 흡수하는 안을 구현자가 택하거나, 사용자가 `tests/reservations` 헬퍼 수정을 허용해야 한다(차단 항목, 아래 보고 참고). 완료 게이트는 `backend-invariants` §7(`uv run python .claude/skills/layer-check/check_layers.py` 새 위반 0, `import main`, `uv run python -m pytest -rs`).

R번호와 충돌하는 요구는 없다. 재고 포트(`ReadOnlyOfferStockPort.release` no-op)·환불 포트(`NoPaymentRefund`)·payments `InMemoryReservationPort`가 남아 있는 동안 EP 4의 재고 복구·환불·포인트 복구(D12)는 효력이 없고, 이는 R16(검사를 약하게 만들지 않음)과 관련해 완료 보고에서 **"미연계"**로 명시해야 한다. 이번 라운드(reservations 변경 없음)에는 `NoReservationAdmin`이라 EP 4는 예약을 취소하지 않고 EP 6의 RESERVED 검사는 항상 통과한다(미연계).

---

## 13. 회원 목록 `GET /v1/admin/users` (2026-11-09 추가)

- 상태: **설계(코드 변경 없음).** 새 EP 하나(10번)를 추가할 뿐 기존 EP 1~9의 설계는 바꾸지 않는다. 이 EP에 한해 §1~§12와 다른 내용이 있으면 이 절이 우선한다. 선행 설계: **`docs/design/auth.md` §18**(회원 조회 레포지토리·응용 메서드·입력 검증 VO·SQL). 이 절은 admin 쪽(포트·서비스·스키마·라우터·EP 수준 테스트)과 사용자 대면 결정·질문의 정본이다.
- 배경: 관리자 EP는 모두 이미 아는 ID가 필요하다. `PATCH /v1/admin/owners/{owner_id}/approve`는 `owner_id`가 필요한데 회원 목록·검색 EP가 없어, 새 상점주는 DB를 직접 보지 않으면 영원히 `PENDING`이다(2026-11-09 확인). 이 EP는 역할·상태로 거르고 페이지로 나눈 목록으로 승인 대기 상점주를 찾게 한다.
- 번호: 이 문서의 마지막 결정은 **D44**, 마지막 정합 이슈는 **C20**이다(`grep`으로 확인. 본문 안의 "D56"·"D58" 등은 catalog.md 인용). 이 절은 **D45~D58, C21~C25**를 쓴다. 다른 문서 인용은 항상 문서 이름을 붙인다.
- 기준: R1~R16, `layer-architecture` §3.4, 실제 코드 `src/admin/**`(특히 `application/{ports,service}.py`, `presentation/{router,schemas}.py`), `src/auth/**`, `src/container.py`, `docs/reference/{README,admin,auth}.md`, `tests/admin/**`.
- 쓰기 범위: 이 절과 `docs/design/auth.md` §18만 썼다. 코드·테스트·reference는 바꾸지 않았다. 바꿀 점은 §13.11(모듈 밖 변경 제안)·§13.13(정합 이슈)에만 있다.

| EP | Method | URI | 한 줄 |
| --- | --- | --- | --- |
| 10 | GET | `/v1/admin/users?role=&status=&email=&page=&size=` | 회원 목록(역할·상태·이메일 부분 일치, 가입 오래된 순, 1부터 페이지) |

### 13.0 차단 이슈 (실행·정독 결과)

| # | 확인 명령 | 결과 | 판정 / 해결 |
| --- | --- | --- | --- |
| B-12 | `(cd src && uv run python -c "import main")`, `uv run python -c "import jwt, passlib, ..."`, `.venv/Scripts/python.exe --version`, `python3 .claude/skills/layer-check/check_layers.py`(`uv run python` 경유) | **전부 실행 불가**: `error: Failed to spawn: python / Caused by: An Application Control policy has blocked this file. (os error 4551)`. `.venv/Scripts/python.exe`는 `Permission denied`. 시스템 `python`은 3.11.9이고 `sqlalchemy` 등 의존성이 없음(`ModuleNotFoundError: sqlalchemy`) | **이 설계 작성 환경의 제약**이며 코드 결함이 아니다. `import main`·`check_layers.py`·pytest는 **이 설계에서 실행하지 못했다(미검증)**. 구현자는 정책이 허용되는 환경에서 `backend-invariants` §7 게이트를 직접 실행한다. 기준선은 §0의 B-1b·B-5(2026-11-05)를 따르되 오래됐다(그 뒤 커밋: reservations·payments·auth 요구조건 반영) |
| B-13 | 라우트 공존 실험: `PYTHONPATH=.venv/Lib/site-packages python -B -c ...`(시스템 3.11 + 가상환경의 starlette, 파일 쓰기 없음). 라우트 4개 `GET /v1/admin/users/{user_id}`, `GET /v1/admin/users`, `DELETE /v1/admin/users/{user_id}`, `GET /v1/admin/users/{user_id}/points`를 `Route.matches`로 대조 | `GET /v1/admin/users` → `/v1/admin/users`만 **FULL**, 나머지 3개 NONE. `GET /v1/admin/users/` → 전부 NONE(슬래시 리다이렉트 대상). `GET /v1/admin/users/abc` → 단건 GET **FULL**, DELETE는 **PARTIAL**(메서드 불일치), 목록·points NONE. 정적 확인: auth 라우터가 `GET /v1/admin/users/{user_id}`를 가진다(`src/auth/presentation/router.py:151-158`), admin 라우터에 `/users` 경로 라우트는 아직 없다(`src/admin/presentation/router.py`) | **공존한다**: `{user_id}`는 빈 문자열과 일치하지 않아 `/v1/admin/users`가 단건 GET과 겹치지 않는다. 한계: 앱 전체(`main.app`)를 띄운 확인이 아니라 Starlette `Route` 매칭 확인이다. 앱 수준 확인은 §13.8 테스트(`test_wiring` 경로 단언)로 고정한다 |
| B-14 | `icontains(autoescape=True)`의 PostgreSQL 컴파일: `PYTHONPATH=.venv/Lib/site-packages python -B -c ...`(SQLAlchemy 2.1.6) | `email ILIKE '%' \|\| 'a/%b/_c' \|\| '%' ESCAPE '/'`(입력 `a%b_c`, 바인드 `a/%b/_c`) | 와일드카드 이스케이프를 **ORM 기능으로** 할 수 있다(직접 문자열 치환 불필요). 질문 Q2의 임시 기본값 근거 |
| B-15 | 패키지: `.venv/Lib/site-packages` 목록(`fastapi-0.162.0`, `sqlalchemy-2.1.6`, `asyncpg-0.32.0`, `passlib-1.7.4`, `jwt`, `starlette` 설치 확인) | 새 패키지 필요 없음. 이 설계는 `Form`·`File`을 쓰지 않아 `python-multipart` 불필요 | `pyproject.toml` 변경 없음. (`uv run python -c "import ..."`는 B-12 때문에 못 돌렸고 설치 디렉터리로 대신 확인했다) |
| B-16 | `.env.example` 키 확인(`git status`: `M .env.example`는 이 작업 전부터 있던 변경) | `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, 선택 `ADMIN_*`, `KAKAO_*` | 설계가 요구하는 새 키 없음 |
| B-17 | 다른 모듈 의존: `Grep`·`Read` `src/container.py:420-461`, `src/admin/application/ports.py` | admin은 이미 `AccountAdminPort`로 `AuthApplicationService`를 받는다(`create_admin_service`의 `accounts: AuthApplicationService = Depends(create_auth_service)`). 새 모듈·테이블·`provide_*` 필요 없음 | 먼저 만들 모듈 없음. **순서 의존만 있다**: auth `list_users`가 먼저 있어야 `tests/admin/test_wiring.py::test_real_services_satisfy_port_signatures`(포트의 모든 메서드를 `inspect`로 서비스와 비교)가 통과한다(§13.7) |
| B-18 | EP 8의 실제 페이지 처리: `src/admin/presentation/router.py:105-115`, `src/auth/application/service.py:336-338`, `tests/admin/test_api_db.py:529-531` | router는 `page: int = 1, size: int = 20`(Query 제약 없음). 서비스가 `page < 1 or size < 1 or size > 100`이면 `InvalidPageError`(400 `INVALID_PAGE` "페이지 값이 올바르지 않습니다."). 숫자가 아니면 전역 핸들러 400 `VALIDATION_ERROR` | 이 EP는 **같은 방식**을 쓴다(D47·D48). 위치만 서비스 `if`가 아니라 도메인 VO(auth.md §18.3) |
| B-19 | `src/admin/presentation/router.py:4` | `from fastapi import APIRouter, Depends, status`(HTTP 상태 상수) | 쿼리 매개변수 이름 `status`를 함수 인자로 쓰면 이 import를 가려 `status.HTTP_201_CREATED` 등이 깨진다. **인자 이름은 `status_filter`, 쿼리 이름은 `Query(alias="status")`**(§13.5) |
| B-20 | `grep -rn "def find_by_email" src tests` | 테스트 가짜 `UserRepository` 2개가 추상 메서드 추가로 깨진다(auth.md B-43). admin 쪽은 `tests/admin/test_service.py`의 `FakeAccounts`(덕 타이핑 클래스, ABC 아님)라 `list_users`를 추가해야 새 테스트가 돈다 | 구현 범위에 포함(§13.9) |

**B-12 해결 (2026-11-09, 사용자 승인): 래퍼 사용.** `uv run python` 대신 `bash "C:/Users/kantf/AppData/Local/Temp/claude/b078265c25c9dcad/58d5214f-5ea0-4d8c-ba25-713fabd13041/scratchpad/py.sh"`(uv가 설치한 기본 Python 3.13 + venv site-packages를 PYTHONPATH로 연결)를 쓴다. 오케스트레이터가 `import main`·`check_layers`·pytest 수집을 확인했다.

차단 이슈 요약: **구현을 막는 것은 없다.** 주의 두 가지: ① 이 환경에서 `import main`·`check_layers.py`·pytest를 못 돌렸다(B-12) → 구현자가 §7 게이트를 직접 실행해야 한다. ② 구현 순서는 auth → admin(B-17).

### 13.1 범위

- 포함: `GET /v1/admin/users` 하나. 읽기 전용, `commit` 없음.
- 제외(D49, 사용자 확정): 관리자 상점 목록(`GET /v1/admin/stores?status=...`)은 **범위 밖**이다. 후속 제안은 §13.11.
- 기존 EP 1~9, auth의 `GET /v1/admin/users/{user_id}`(단건 조회)·`POST /v1/admin/token-blacklist/purge`는 바꾸지 않는다(D42 유지).

### 13.2 도메인 (domain/)

admin에는 엔티티·규칙을 **새로 두지 않는다**(R3, D31). 입력 검증(page·size·role·status·email)은 소유 컨텍스트(auth)의 도메인 VO가 한다 → `docs/design/auth.md` §18.3. admin의 `Clock`은 이 EP에서 쓰지 않는다(`now`는 auth가 자기 `Clock`으로 얻는다).

### 13.3 인프라 (infrastructure/)

admin 인프라 변경 **없음**(레포지토리·모델 없음, D28). 테이블 변경 **없음**(`users`를 읽기만 함). 쿼리·정렬·페이지·잠금은 `docs/design/auth.md` §18.4가 정본이다. 동시성: 읽기 전용이라 `with_for_update()` 불필요.

### 13.4 응용 (application/)

**포트 확장 (`admin/application/ports.py`)** — 기존 `AccountAdminPort`에 메서드를 **추가**한다(D46). `AuthApplicationService`가 구조적으로 만족한다(R11: admin은 auth를 import하지 않는다).

```python
class UserListItemInfo(Protocol):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    status: str            # 실효 상태 (D55)
    created_at: datetime


class UserPageInfo(Protocol):
    items: list[UserListItemInfo]
    page: int
    size: int
    total: int


class AccountAdminPort(Protocol):
    ...
    async def list_users(
        self,
        *,
        role: str | None = None,
        status: str | None = None,
        email: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> UserPageInfo: ...
```

- 기본값(`1`, `20`)은 auth `list_users`와 **같아야** 한다. `test_real_services_satisfy_port_signatures`가 이름·종류·기본값을 비교한다(auth.md §18.5).
- 포트 이름을 새로 만들지 않고 `AccountAdminPort`를 확장한 이유: ① 같은 서비스(`AuthApplicationService`)가 만족하고 `list_points`(읽기)가 이미 같은 포트에 있다 ② 새 포트는 `container`·`AdminApplicationService` 생성자에 인자를 늘린다(`tests/admin/test_service.py`의 `Ctx`·생성자 인자 단언이 모두 바뀜). 대안 비교는 D46.

**서비스 (`AdminApplicationService`)**

```python
# EP 10 (읽기 전용, commit 없음)
async def list_users(
    self,
    *,
    role: str | None,
    status: str | None,
    email: str | None,
    page: int,
    size: int,
) -> UserPageInfo:
    return await self.accounts.list_users(
        role=role, status=status, email=email, page=page, size=size
    )
```

시나리오(조회 → 도메인 → save → commit 중 읽기만): router가 쿼리 값을 그대로 넘김 → admin 서비스는 포트를 **한 번** 호출 → auth가 VO 검증 → 목록·개수 조회 → DTO 반환. `session.commit()` 0회, `Clock` 사용 0회, 다른 모듈 호출 1회라 트랜잭션 경계 이슈가 없다(R13 해당 없음). 규칙을 admin 서비스에 두지 않는다(R3).

### 13.5 표현 (presentation/)

**엔드포인트 (명세 필드명 규칙, R15)**

| # | Method | URI | 요청 | 응답 스키마 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | GET | `/v1/admin/users` | 쿼리 `role?`, `status?`, `email?`, `page=1`, `size=20` | `UserPageResponse` `{items[{id, email, name, role, status, created_at}], page, size, total}` | 200 | 400 `INVALID_PAGE` 페이지 값이 올바르지 않습니다. / 400 `VALIDATION_ERROR`(잘못된 role·status·긴 email, 숫자가 아닌 page·size) / 401 `UNAUTHORIZED`·`TOKEN_REVOKED`(`WWW-Authenticate: Bearer`) / 403 `FORBIDDEN`(관리자 아님) |

(404 없음: 필터에 맞는 회원이 없으면 200 + 빈 `items`. 마지막 페이지를 넘어서도 200 + 빈 `items` + 실제 `total`.)

**쿼리 매개변수**

| 이름 | 타입 | 필수 | 기본 | 설명 |
| --- | --- | --- | --- | --- |
| `role` | string | X | 없음 | `CUSTOMER` / `OWNER` / `ADMIN`. 대문자 정확 일치(D50). 공백만 있으면 없는 것으로 본다(D57) |
| `status` | string | X | 없음 | `PENDING` / `APPROVED` / `REJECTED` / `SUSPENDED` / `WITHDRAWN`. **실효 상태** 기준(D55) |
| `email` | string | X | 없음 | 이메일 **부분 일치**, 대소문자 무시. `%`·`_`는 글자 그대로(D56). 255자 초과는 400(D57) |
| `page` | integer | X | 1 | 1부터(D47). 1 미만은 400 `INVALID_PAGE` |
| `size` | integer | X | 20 | 1~100(D53). 범위 밖은 400 `INVALID_PAGE` |

정렬은 고정이다: 가입 시각 오름차순(오래 기다린 순), 동률은 `id` 오름차순(D51). 정렬 매개변수는 두지 않는다.

**스키마 (`presentation/schemas.py`)** — 기존 `_FromAttributes`·`from_attributes`를 재사용한다.

```python
class UserListItemResponse(_FromAttributes):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    status: str = Field(..., description="PENDING / APPROVED / REJECTED / SUSPENDED / WITHDRAWN (기간이 지난 정지는 APPROVED)")
    created_at: datetime = Field(..., description="가입 시각")


class UserPageResponse(_FromAttributes):
    items: list[UserListItemResponse]
    page: int
    size: int
    total: int = Field(..., description="필터에 맞는 전체 건수")
```

비밀번호 해시·전화번호·포인트·사업자번호·정지/거부/탈퇴 사유·시각·토큰 정보는 **스키마에 필드로 두지 않는다**(R15, D52). `response_model`이 필터 역할을 하고, auth의 `UserSummary`가 1차로 담지 않는다(이중 방어, auth.md D-목록요약).

**라우터 (`presentation/router.py`)** — `Query` import를 추가한다.

```python
# 기존 EP 8처럼 page/size 범위는 Query 제약이 아니라 도메인(auth VO)이 명세 문구(INVALID_PAGE)로 검증한다 (§6.3)
# 쿼리 이름 'status'는 위의 `from fastapi import status`를 가리지 않도록 status_filter + alias로 받는다 (B-19)
@router.get(
    "/users",
    response_model=UserPageResponse,
    tags=TAGS,
    summary="회원 목록 조회",
)
async def list_users(
    admin: AdminUser,
    service: Service,
    role: Annotated[str | None, Query(description="CUSTOMER / OWNER / ADMIN")] = None,
    status_filter: Annotated[
        str | None,
        Query(alias="status", description="PENDING / APPROVED / REJECTED / SUSPENDED / WITHDRAWN"),
    ] = None,
    email: Annotated[str | None, Query(description="이메일 부분 일치(대소문자 무시)")] = None,
    page: int = 1,
    size: int = 20,
):
    return await service.list_users(
        role=role, status=status_filter, email=email, page=page, size=size
    )
```

- `Annotated`는 이미 import돼 있다(`router.py:2`). `Query`는 `from fastapi import APIRouter, Depends, Query, status`로 추가한다.
- 인증 의존성은 쿼리 검증보다 먼저 실행된다(auth.md B-23과 같은 FastAPI 동작): **토큰 없이 `page=x`는 400이 아니라 401**이다. 테스트로 순서를 고정한다.
- 경로는 `/users`이고 `ADMIN_PREFIX`가 `/v1/admin`을 붙인다(D2). 라우터는 서비스만 호출하고 예외를 잡지 않는다(R6, R7).

### 13.6 조립 — `src/container.py` / `src/main.py`

**변경 없음.** `create_admin_service`는 이미 `accounts: AuthApplicationService = Depends(create_auth_service)`를 받고(`container.py:447-461`), 새 메서드는 같은 클래스에 생기므로 포트를 구조적으로 만족한다. `provide_*`·`wire_dependencies`·`main.py`(라우터는 이미 등록됨)·`tests/test_container.py` 모두 불변. 오케스트레이터가 따로 연결할 모듈 간 작업도 없다(포트는 admin이 정의하고 구현은 기존 auth 서비스).

### 13.7 구현 순서

1. **auth 먼저**(`docs/design/auth.md` §18.7): 예외 → VO → 레포 추상 → 레포 구현 → 응용 → 테스트(가짜 2개 갱신 포함). auth 테스트가 통과한 뒤 다음으로 간다.
2. admin: ① `ports.py`(Protocol·포트 메서드) ② `service.py`(`list_users`) ③ `schemas.py` ④ `router.py` ⑤ 테스트(`test_service.py` 가짜·서비스 테스트 → `test_wiring.py` → `test_api_db.py`).
3. 게이트: `backend-invariants` §7 세 명령(위반 0, `import main`, `pytest -rs` failed 0·db skip 0).
4. 모듈 밖: §13.11(reference·요구 조건 문서)은 오케스트레이터가 별도로.

순서를 지켜야 하는 이유: 2-①을 먼저 하면 `test_real_services_satisfy_port_signatures`가 auth에 `list_users`가 없어 실패한다(B-17).

### 13.8 테스트 계획 (admin / EP 수준)

DB 테스트는 `@pytest.mark.db`, skip은 통과가 아니다(R16). auth 쪽 도메인·서비스·레포지토리 테스트는 auth.md §18.6. ADMIN 계정은 기존 `admin_headers`(fixture 직접 insert)를 쓴다(D29).

**서비스 (`tests/admin/test_service.py`, fake 포트)** — `FakeAccounts`에 `list_users`를 추가(`rec.record("list_users", ...)`, 고정 결과 반환):
- 인자(`role`·`status`·`email`·`page`·`size`)를 **그대로** 포트에 전달, 결과 객체를 **그대로** 반환
- `commit` 0회, 포트 호출 정확히 1회, `Clock` 미사용(`FakeClock` 호출 0)
- 포트 실패(`fail_on["list_users"]`)가 그대로 전파(예외를 삼키지 않음)

**조립 (`tests/admin/test_wiring.py`)**: 경로 목록에 `("GET", "/v1/admin/users")` 추가(앱 수준 공존 확인, B-13의 한계 보완). `test_real_services_satisfy_port_signatures`는 포트에 `list_users`가 생기면 **자동으로** 이 메서드의 시그니처를 대조한다(수정 불필요, 단 auth 구현이 먼저 있어야 함). 단건 `GET /v1/admin/users/{user_id}`는 auth 소유로 별도(기존 테스트 `tests/admin/test_api_db.py:121-` `test_old_prefix_is_gone_and_auth_admin_endpoints_coexist`가 공존을 확인하므로 같은 테스트에 목록 호출도 추가).

**API (`tests/admin/test_api_db.py`, `db` 마커)** — 시드 헬퍼: `signup(c, email, "OWNER")`는 PENDING 상점주(D4), `signup(..., "CUSTOMER")`는 APPROVED 고객, `EP 1`로 승인한 상점주, `EP 2`로 거부한 상점주(사유 있음), 기간 정지(`EP 3`)한 고객, 직접 UPDATE한 기간 지난 정지, 강제 탈퇴(EP 4)한 고객.

| 구분 | 케이스 |
| --- | --- |
| 성공 | 200, 본문 키가 **정확히** `{items, page, size, total}`, 항목 키가 정확히 `{id, email, name, role, status, created_at}`, 기본 `page == 1`·`size == 20` 에코, `total`이 실제 건수 |
| 인증 | 토큰 없음 → 401 `UNAUTHORIZED` + `WWW-Authenticate: Bearer`, 형식 `{success, error_code, message}` 3키(R7). 로그아웃된 토큰 → 401 `TOKEN_REVOKED`. **토큰 없이 `page=x` → 401**(인증이 먼저) |
| 권한 | `CUSTOMER` 토큰 → 403 `FORBIDDEN`, `OWNER` 토큰 → 403 |
| **PENDING 필터** | 시드: PENDING 상점주 2, 승인 상점주 1, 거부 상점주 1, 고객 2, 관리자 1. `?status=PENDING` → `total == 2`, **모든 항목이 `role == OWNER`·`status == PENDING`**, 이메일 집합이 PENDING 상점주 2개와 같음, 가입 순서(오래된 순). `?status=PENDING&role=OWNER`도 같은 결과, `?status=PENDING&role=CUSTOMER` → `total == 0`·`items == []` |
| 승인 흐름(B2 목적) | 목록에서 얻은 `id`로 `PATCH /v1/admin/owners/{id}/approve` → 200 → 다시 `?status=PENDING`에서 그 `id`가 빠지고 `?status=APPROVED&role=OWNER`에 나타남 |
| role 필터 | `role=OWNER`/`CUSTOMER`/`ADMIN` 각각 해당 역할만. 필터 없음 → 모든 역할(탈퇴 회원 포함, D54) |
| status 필터 | 각 상태 값으로 해당 회원만. `status=WITHDRAWN` → 강제 탈퇴한 회원만. 필터 없는 목록에 `WITHDRAWN` 포함(D54) |
| **실효 상태(D55)** | 저장 `SUSPENDED` + 과거 `suspended_until`인 회원: `status=APPROVED` 목록에 포함되고 항목 `status == "APPROVED"`, `status=SUSPENDED` 목록에서 제외. 무기한·미래 정지: `status=SUSPENDED`에 포함, 항목 `status == "SUSPENDED"` |
| email 검색 | 부분 일치(`email=pend`), 대소문자 무시(`email=PEND`), 앞뒤 공백 무시, 일치 없음 → 200 + 빈 목록, `role`·`status`와 조합. **와일드카드**: `email=%25`(= `%`)는 `%`가 들어간 이메일만(없으면 빈 목록, 전체가 아님), `email=_`는 임의 한 글자가 아님(직접 INSERT한 `a_b@…`, `axb@…`로 `email=a_b`가 전자만) |
| 페이지 경계 | `size=2`로 5명: `page=1`(2건)·`page=2`(2건)·`page=3`(1건), `page=4` → **200 + 빈 `items` + `total == 5`**(400 아님), 항목이 페이지 사이에 중복·누락 없이 정렬 순서와 같음. `size=100` 통과, 기본 `size`는 20(21명 시드로 첫 페이지 20건) |
| 잘못된 page·size | `page=0`, `page=-1`, `size=0`, `size=101` → 400 `INVALID_PAGE` "페이지 값이 올바르지 않습니다."(기존 EP 8 테스트와 같은 방식). `page=x`·`size=x` → 400 `VALIDATION_ERROR` |
| 잘못된 필터 | `role=BAD`, `status=BAD`, 소문자 `role=owner`·`status=pending` → 400 `VALIDATION_ERROR`, 본문 3키. page와 필터가 둘 다 틀리면 `INVALID_PAGE` 우선(검증 순서). 공백만 있는 `role=%20`은 필터 없음(D57). 256자 `email` → 400 |
| 민감 필드 없음 | 응답 JSON 문자열에 `password`·`hash`·`phone`·`users_point`·`business_number`·`rejected_reason`·`suspended_reason`·`deleted_reason`·`token`이 없음. 거부 사유·정지 사유가 있는 회원이 목록에 있어도 항목 키 집합이 그대로 |
| 공존 | `GET /v1/admin/users/{user_id}`(auth 단건 조회)가 여전히 200, `DELETE /v1/admin/users/{user_id}`·`GET .../points`가 여전히 동작, `/v1/admin/users`(슬래시 없음)가 단건 라우트에 잡히지 않음 |
| 쓰기 없음 | 호출 전후 `users` 행·`point_log` 행 수·값 불변 |

- 완료 게이트: `backend-invariants` §7. 새 `layer-check` 위반 0(admin은 `auth.application`·`auth.domain`을 import하지 않는다 — `ports.py`는 `typing`·`uuid`·`datetime`만).

### 13.9 구현 파일 목록 (모듈별)

| 소유 | 파일 | 내용 |
| --- | --- | --- |
| **auth** (먼저) | `src/auth/domain/{user_list_query,exceptions}.py`, `src/auth/domain/repository/user_repository.py`, `src/auth/infrastructure/repositories.py`, `src/auth/application/service.py`, `tests/auth/{test_user_list_query,test_user_list_service,test_user_list_repository_db}.py`(신규), `tests/auth/{test_service,test_optional_user}.py`(가짜 갱신) | auth.md §18.7 |
| **admin** | `src/admin/application/ports.py`(`UserListItemInfo`, `UserPageInfo`, `AccountAdminPort.list_users`), `src/admin/application/service.py`(`list_users`), `src/admin/presentation/schemas.py`(`UserListItemResponse`, `UserPageResponse`), `src/admin/presentation/router.py`(EP 10, `Query` import), `tests/admin/test_service.py`(`FakeAccounts.list_users`, 서비스 테스트), `tests/admin/test_wiring.py`(경로 1줄), `tests/admin/test_api_db.py`(EP 10 테스트) | §13.4~§13.8 |
| 변경 없음 | `src/admin/{domain,infrastructure}/**`, `src/admin/presentation/dependencies.py`, `src/container.py`, `src/main.py`, `src/error_handlers.py`, `pyproject.toml`, `.env.example`, `schema.sql`, `models.py` | |
| 오케스트레이터(`docs/reference/**`, `docs/requirements/**`) | §13.11 | 이 문서는 쓰지 않음 |

### 13.10 결정 표 (D45~D58)

사용자 확정(2026-11-09): D45~D58 전부(D46, D50~D58은 같은 날 추가 확정, D55 = 실효 상태로 계산). 코드에서는 "코드 위치" 열의 한곳에 모아 바꾸기 쉽게 한다.

| # | 결정 | 출처 | 값 | 근거 | 코드 위치 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| D45 | EP 소유·데이터 위치 | 사용자 | EP는 **admin 모듈**(`src/admin` 라우터, `AdminUser`). 회원 데이터 조회(레포지토리·응용 메서드)는 **auth**. admin은 admin이 정의한 포트로 부르고 auth의 application·domain을 import하지 않는다 | D1, D30, R11, §3.4 | `admin/presentation/router.py`, `auth/application/service.py` | **확정**(사용자, 2026-11-09) |
| D46 | 포트 형태 | D45의 선택지 | 새 포트가 아니라 **`AccountAdminPort` 확장**(`list_users` 추가). 대안: 새 `AccountQueryPort`를 만들고 서비스 생성자·container 인자 추가 | 같은 서비스가 만족, `list_points`(읽기)가 이미 같은 포트, 생성자·`Ctx`·container 변경 없음 | `admin/application/ports.py` | **확정**(사용자, 2026-11-09) |
| D47 | 페이지 형식 | 사용자 | 기존 admin 포인트 이력 EP와 같게: `page`는 **1부터**, 응답에 `page`·`size`·`total`. 컬렉션 필드명은 `items`(D58) | EP 8·D25 | `UserListQuery`, `UserPageResponse` | **확정**(사용자, 2026-11-09). README 이슈 5(프로젝트 전체 통일)는 열린 채 |
| D48 | 잘못된 page·size | 사용자 + 코드 확인(B-18) | 기존 EP와 같은 방식: `page < 1`·`size < 1`·`size > 100` → 400 `INVALID_PAGE`(`InvalidPageError`), 숫자가 아니면 400 `VALIDATION_ERROR`. router에 `Query` 제약 없음 | `service.py:336-338`, D26 | `UserListQuery.create` | **확정**(사용자, 2026-11-09) |
| D49 | 관리자 상점 목록 | 사용자 | **범위 밖**. 후속 제안만(§13.11) | 사용자 결정 | - | **확정**(사용자, 2026-11-09) |
| D50 | 필터 | 기본값 | `role`, `status`, `email` **모두 선택**. 값이 잘못된 `role`·`status`는 400 `VALIDATION_ERROR`. 입력은 **대문자 정확 일치**(`owner`는 400). 필터끼리는 AND | 요청 기본값, `UserStatus`·`Role` 값 | `UserListQuery.create` | **확정**(사용자, 2026-11-09) |
| D51 | 정렬 | 기본값 | 가입 시각(`created_at`) **오름차순**, 동률은 `id` 오름차순. 정렬 매개변수 없음 | 오래 기다린 승인 대기를 먼저 | `SqlAlchemyUserRepository.find_all` | **확정**(사용자, 2026-11-09) |
| D52 | 응답 항목 필드 | 기본값 | `id`, `email`, `name`, `role`, `status`, `created_at`. 해시·전화번호·정지/거부/탈퇴 사유는 넣지 않는다(상세는 `GET /v1/admin/users/{user_id}`) | R15 | `UserListItemResponse`, `UserSummary` | **확정**(사용자, 2026-11-09) |
| D53 | `size` | 기본값 | 기본 **20**, 최대 **100** | EP 8과 같음 | `user_list_query.py` 상수 | **확정**(사용자, 2026-11-09) |
| D54 | 탈퇴 회원 | 기본값 | `WITHDRAWN`도 목록에 **포함**, `status=WITHDRAWN`으로 거를 수 있다. 필터가 없으면 모든 상태 | 요청 기본값(관리자는 탈퇴 처리 결과도 봐야 함) | 레포지토리에 상태 제외 조건 없음 | **확정**(사용자, 2026-11-09) |
| D55 | **기간이 끝난 정지**(저장 `SUSPENDED`, `suspended_until <= now`)의 `status` 필터·응답 | 확인 필요 1 | **실효 상태로 계산**: 필터와 응답 `status` 모두 `effective_status(now)`와 같다(만료된 정지는 `APPROVED`). 선택지·장단점은 §13.12 Q1 | 로그인·권한 판정과 같은 의미(D10), 필터 결과와 응답이 모순되지 않음 | auth `_status_clause`, `UserSummary.from_user` | **확정**(사용자, 2026-11-09) |
| D56 | email 검색의 `%`·`_` | 확인 필요 2 | **글자 그대로**(와일드카드 아님): SQLAlchemy `icontains(autoescape=True)` → `ILIKE ... ESCAPE '/'`(B-14) | 관리자가 `a_b`를 찾는데 `axb`가 섞이면 안 됨, 구현이 한 줄 | auth `_conditions` | **확정**(사용자, 2026-11-09) |
| D57 | 빈 값·긴 값 | 설계자 제안 | `role`·`status`·`email`이 **공백뿐이거나 비면 필터 없음**(프런트가 빈 선택값을 보내도 400이 되지 않게). `email` 앞뒤 공백 제거, **255자 초과는 400**(`users.email VARCHAR(255)`) | 폼에서 빈 값 전송이 흔함. 대안: 빈 `role`·`status`를 400으로 | `UserListQuery.create` | **확정**(사용자, 2026-11-09) |
| D58 | 응답 컬렉션 이름 | 설계자 제안 | `items`(README의 상품·할인 목록과 같음). EP 8은 `history`지만 그것은 이력 | `docs/reference/README.md:155` | `UserPageResponse` | **확정**(사용자, 2026-11-09) |

확정 현황(2026-11-09): **확정** D45~D58 전부. 임시 없음. C22(단건 조회와의 `status` 불일치)는 열린 채 후속으로 둔다.

### 13.11 모듈 밖 변경 제안·후속 제안 (이 문서는 쓰지 않는다)

**`docs/reference/` (오케스트레이터, R15)**
- `docs/reference/admin.md`: 새 절 "10. 회원 목록 조회"(`GET /v1/admin/users`)를 추가한다. 요청 쿼리 표(§13.5), 응답 예시(`items`·`page`·`size`·`total`), 에러 표(400 `INVALID_PAGE`, 400 `VALIDATION_ERROR`, 공통 401·403), 설명 "정렬: 가입 오래된 순", "`status`는 실효 상태(기간이 끝난 정지는 `APPROVED`)", "탈퇴 회원 포함". 머리글 "관리자 기능 9개"를 10개로, "기존 관리자 API (auth)" 절에 "단건 조회는 auth.md 6번, 목록은 admin.md 10번" 연결을 추가.
- `docs/reference/README.md`: 전체 목록 표에 admin 10번째 행(`GET /v1/admin/users`, 관리자, 200)을 추가하고 admin 개수(`README.md:17`의 9)를 10으로. 페이지 형식 표(`:154-155`)에 "관리자 회원 목록: `page=1`, `items`·`page`·`size`·`total`" 행. **이슈 5(페이지네이션 형식 통일)는 열어 둔다**(이 EP는 기존 1부터·`total` 쪽에 합류).

**`docs/requirements/`**: `docs/requirements/admin.md`(초안)에 "관리자는 회원을 역할·상태·이메일로 찾고 승인 대기 상점주를 확인할 수 있다" 요구(REQ)가 없다. 요구 번호는 요구 조건 담당이 매긴다(이 설계는 번호를 만들지 않는다).

**후속 제안 (이번 범위 아님)**
- **관리자 상점 목록** `GET /v1/admin/stores?status=...`(D49): 정지·폐점 상점을 찾으려면 필요하다. stores 컨텍스트가 소유하고 admin이 포트로 부르는 같은 구조를 쓴다.
- 이름 검색, 가입일 범위 필터, 정렬 매개변수(`sort=created_at,-created_at`): 필요가 확인되면.
- 인덱스: 회원이 수만 명이 되면 `(status, created_at, id)` 복합 인덱스를 제안한다(스키마 변경이므로 R14에 따라 `schema.sql`·`db-schema`와 함께, 이번엔 하지 않음).
- 목록 한 행이 `User` 불변식을 어기면 그 페이지 전체가 500(auth.md §18.4). 문제가 생기면 `_to_domain` 예외 처리 방안을 별도 결정.
- 기존 `GET /v1/admin/users/{user_id}`의 `status`를 실효 상태로 맞출지(C22).

### 13.12 질문 목록과 임시 기본값

**2026-11-09 사용자 결정: Q1~Q8 모두 아래 임시 기본값대로 확정.** C22는 열린 채 후속.

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 |
| --- | --- | --- | --- | --- |
| Q1 | **기간이 끝난 정지 회원**(저장 `SUSPENDED`, `suspended_until` 경과 → 실효 `APPROVED`)을 `status` 필터와 응답에서 어떻게 보일지 | 사용자 요청 "확인 필요", `User.effective_status`(`user.py:278`), D10 | **B안: 실효 상태로 계산**(D55) | D10(만료는 조회 시 자동 해제), 로그인·권한 판정과 같음 |
| Q2 | email 검색의 `%`·`_` 와일드카드 | 사용자 요청 "확인 필요" | **글자 그대로 검색**(D56) | 관리자는 정확한 부분 문자열을 찾는다. B-14로 ORM 기능으로 가능함을 확인 |
| Q3 | 빈 문자열(`role=`, `status=`, `email=`)과 공백뿐인 값 | 설계자 제안(요청 기본값은 "잘못된 값은 400"만 말함) | **필터 없음으로 처리**(D57). `email`만 255자 초과 400 | 폼의 빈 선택값이 400이 되지 않게. 반대 해석(빈 `role`도 400)은 `UserListQuery.create` 한 곳 |
| Q4 | `role`·`status` 입력의 대소문자 | 설계자 제안 | **대문자 정확 일치**, 소문자는 400(D50) | 응답·reference의 값 표기와 같음. 대소문자 무시로 바꾸는 것은 VO 한 줄 |
| Q5 | 포트를 `AccountAdminPort` 확장으로 할지 새 포트로 할지 | 사용자 결정의 선택지 | **확장**(D46) | §13.4. 새 포트면 `AdminApplicationService` 생성자·container·테스트 `Ctx` 변경 |
| Q6 | 응답 컬렉션 필드명 `items` vs `history` 스타일 | 설계자 제안 | `items`(D58) | README 목록 표와 같음 |
| Q7 | 탈퇴 회원 포함 여부와 기본 목록에서의 노출 | 사용자 요청 기본값 | 포함(D54). 기본 화면에서 숨기고 싶으면 `status` 기본값을 두는 대안이 있으나 이번엔 만들지 않음 | 요청 기본값 |
| Q8 | 목록 항목 `status`와 단건 `GET /v1/admin/users/{user_id}`의 `status` 불일치(C22) | 설계자 발견 | 이번엔 단건·EP 1~4 응답을 **바꾸지 않는다** | 범위, 단건은 auth 소유 |

(R번호와 충돌하는 요구는 없다. 설계 전체가 R1~R16을 지킨다: R1 VO 순수 파이썬, R2·R8 서비스는 추상 레포·포트만, R3 검증·상태 판정은 도메인 VO·엔티티, R4 `UserSummary`·`User`만 밖으로, R5 읽기라 commit 없음, R6 전용 예외+전역 핸들러, R7 에러 3키·401 헤더, R9 새 `provide_*` 없음, R10 추상에 있는 메서드만, R11 admin은 auth를 import하지 않음, R12 새 의존 방향 없음, R13 해당 없음, R14 스키마 변경 없음, R15 필드명·민감 정보 제외, R16 새 키·skip 없음.)

### 13.13 정합 이슈 (C21~C25)

| ID | 위치 | 내용 | 제안 / 상태 |
| --- | --- | --- | --- |
| C21 | `docs/reference/admin.md`(EP 9개), `docs/reference/README.md:17,56-66,154-155` | 명세에 이 EP가 없다(R15). 또 "관리자 기능 9개"가 코드·reference 전체에 박혀 있다 | §13.11의 reference 변경을 오케스트레이터가 반영. 구현이 reference보다 먼저 나가면 완료 보고에 "reference 미반영"을 적는다 |
| C22 | `GET /v1/admin/users/{user_id}`의 `UserResponse.status`(`src/auth/presentation/schemas.py:30`, 저장값), EP 1·2·3·4의 `status`(저장값), `docs/design/auth.md` §18(C-41) | D55(실효 상태)를 택하면 **목록에서 `APPROVED`인 회원이 단건 조회에서는 `SUSPENDED`로 나올 수 있다**(기간이 끝난 정지, 저장값이 아직 갱신되지 않음). 로그인 응답은 이미 실효 상태다(D40) | 임시: 이번엔 단건을 바꾸지 않고 둘의 차이를 reference에 한 줄 적는다. 일관되게 하려면 (a) 단건·EP 응답도 실효 상태로(auth 변경) 또는 (b) D55를 저장값(A안)으로. Q1에서 사용자가 정하면 함께 정리 |
| C23 | `tests/admin/test_wiring.py:101-109`의 주석("auth 관리자 EP … main 7594d43에서 auth에서 제거됨"), `src/auth/presentation/router.py:151-168` | 주석이 현재 사실과 다르다. `7594d43`이 제거했지만 `a343f05`가 복원했고(`git log`로 확인) 현재 auth 라우터에 두 EP가 있다. D42 기본값과 일치한다 | 테스트 주석만 어긋남. 구현자가 `test_wiring.py`를 고칠 때 주석도 바로잡는다(범위: admin 테스트) |
| C24 | 이 문서 §5.2·§5.4·B-6·B-7·§6.1(EP 4 예약 포트 `cancel_reserved_for_user`·`NoReservationAdmin`, "9개"), 실제 코드 `src/admin/application/{ports,service}.py` | 본문 일부가 코드와 다르다: 코드는 `cancel_active_for_user`·`has_reserved_for_store(excluding_user_id=)`·`ReservationAdminAdapter`(reservations 구현됨), `AccountWithdrawalService`(auth.md C-25) 등으로 바뀌었다 | 이 절은 이 부분을 건드리지 않았다. admin.md 본문 갱신은 별도 작업으로 제안 |
| C25 | `docs/reference/README.md:154-155,169`(이슈 5) | 목록 API의 페이지 시작(0/1)·총건수 이름이 프로젝트 전체로 통일돼 있지 않다. 이 EP는 1부터·`total`을 쓰므로 **1부터 쪽이 하나 늘어난다** | 이슈 5는 열린 채 둔다(사용자 결정). 통일되면 이 EP는 변경 없이 맞을 가능성이 높다(1부터·`total`이 다수) |
