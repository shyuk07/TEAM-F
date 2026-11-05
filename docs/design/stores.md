# stores 모듈 설계안 (최소 범위)

- 대상: `src/stores` (테이블 `stores`)
- 목적: `docs/design/catalog.md` 2절(StorePort/StoreInfo, StoreRef, `find_store_by_id`, `find_stores_by_ids`, `has_open_offers_for_store`)의 선행 조건 충족
- 기준: `docs/reference/stores.md`, `.claude/skills/db-schema/schema.sql`(stores), `backend-invariants`(R1~R16), `layer-architecture`(§5 추상화, §6 조립), `layer-implementation`, 구현된 `src/auth`(DI·조립은 `layer-architecture`가 정본이며 auth의 직접 생성 방식은 따르지 않는다)
- 상태: 설계 제안. "임시 기본값"은 확정이 아니라 제안이며 마지막 절 표에 모았다. 단 D13·D14는 2026-11-03 사용자가 확정했다(표에 "확정"으로 표시).
- 이번 범위: 도메인 `Store`, `StoreModel`, 추상 레포지토리 + 구현체, 읽기 서비스 2개, **최소 개설 API 1개**(7절), `presentation/dependencies.py`, `src/container.py`의 stores 구역, `main.py` 등록. 승인·폐점·재개점 EP는 후속(8절).
- 갱신 이력: 2026-11-02 작성 → 2026-11-03 R8·R9·R12·layer-architecture §5~§7 반영(추상 레포지토리·Clock 추상, `provide_*`, container 조립, 생성 순환을 container 팩토리 그래프로 기술). 설계 범위와 D1~D12 값은 변경 없음. → 2026-11-03 사용자 확정 반영: D13(Clock은 모듈별 위치, 확정), D14(stores implementer가 `src/container.py` 골격을 먼저 생성, 확정, C9 해소), C10(auth 구역은 범위 밖), `has_open_offers_for_store(store_id, *, now=None) -> bool` 서명 통일(`now=now` 키워드 호출), D15는 catalog.md D22와 동일 결정임을 상호 참조. 그 외 설계 내용은 변경 없음.
- 2026-11-05 갱신(상점주 폐점): 현재 코드(admin 기능 반영: `Store`의 `suspended_*`·`closed_reason`·파생 `status`·`close(now)` 정지 가드, 서비스·레포지토리 `for_update`, `ApprovedOwnerUser`, container의 stores·catalog·admin 구역)를 기준으로 `POST /v1/stores/{store_id}/close`를 **13절**에 설계했다. 기존 D1~D15 값은 유지하고 D15·D8·D7만 상태를 갱신했으며 D16~D24, C11~C16을 추가했다. 재개점(`reopen`)은 범위 밖(D6, 후속). 8절 폐점 메모는 13절로 대체됐다(8절에 표시). 0~12절 중 "현재 코드와 다른 옛 서술"(예: 0절 "stores 비어 있음", 5.1 `OwnerUser`)은 이력으로 남기고, 현재 상태는 13절이 우선한다.

- 2026-11-05 갱신(상점 개설 완성): 사용자 정본(개설 명세, 2026-11-05)과 확정 결정 2건(네이버 지오코딩, 공용 auth 401/403 문구 유지)을 **14절**에 설계했다. 지오코딩(D2), 상점명+주소 중복(D10), 개설 시 좌표를 14절이 대체한다. 기존 D1~D25 값은 유지하고 D2·D10의 상태만 갱신했으며 D26~D40, C17~C21을 추가했다. 0~13절 중 개설 관련 옛 서술(4.2 `open_store`, 5.2 "구현하지 않는다" 문장, 5.3 `StoreResponse`의 좌표 nullable)은 이력이며 현재 상태는 14절이 우선한다.

---

## 0. 차단 이슈

| # | 확인 | 명령·결과 | 해결 |
| --- | --- | --- | --- |
| - | `src/stores` 비어 있음 | `find src/stores -type f` → 파일 전부 0바이트 (`domain/store.py`, `infrastructure/models.py`, `repositories.py`, `application/service.py`, `presentation/router.py`, `schemas.py`, `__init__.py`들). `presentation/dependencies.py`, `domain/repository.py`, `domain/service.py`, `infrastructure/clock.py`는 아직 없음 | 이 설계대로 채운다. 이것이 catalog의 차단 B1이다. |
| - | `src/container.py` 없음 | `ls src/container.py` → 없음 (`src/main.py`에는 `wire_dependencies` 없음) | 11절: **stores implementer가 `container.py` 골격(import, `wire_dependencies`, stores 구역)을 먼저 만든다(D14, 확정).** catalog는 이후 자기 구역만 추가한다. |

차단 아님(확인 완료):
- `(cd src && uv run python -c "import main")` → `main ok`
- `from sqlalchemy import Double` → ok. 추가 의존성·환경변수 없음(`python-multipart` 불필요, 요청은 JSON).
- `OwnerUser`·`Role.OWNER`는 `auth.presentation.dependencies`, `auth.domain.user`에 있음.
- 마이그레이션 도구 없음(`create_all`). 개발 DB에 이미 `stores` 테이블이 있으면 이 설계의 이름 있는 제약(`uq_stores_owner_id`)은 반영되지 않는다. 필요하면 개발 DB를 다시 만든다.
- 확인한 것: `User.name`은 회원가입에서 선택값(`name: str | None`)이라 상점주가 상호 없이 가입할 수 있다 → 개설 시 별도 처리 필요(7절, D3).

---

## 1. 모듈 구성

```
src/stores/
  domain/
    exceptions.py      # 예외
    store.py           # Store
    repository.py      # StoreRepository (ABC)                       [R8]
    service.py         # Clock (ABC, 추상 도메인 서비스)              [R8, D13 확정: 모듈별 위치]
  infrastructure/
    models.py          # StoreModel
    repositories.py    # SqlAlchemyStoreRepository(StoreRepository)
    clock.py           # SystemClock(Clock)
  application/
    service.py         # StoresApplicationService (catalog의 StorePort를 구조적으로 만족)
  presentation/
    schemas.py         # StoreOpenRequest, StoreResponse
    dependencies.py    # provide_stores_service, provide_store_repository  [R9, layer-architecture §7.4]
    router.py          # POST /v1/stores (Depends(provide_stores_service))
```
`application/ports.py`(폐점 시 catalog 호출용 Protocol)는 후속에 추가한다(8절). 지금은 만들지 않는다.
구현체 연결(`SqlAlchemyStoreRepository`, `SystemClock` 생성)은 `src/container.py`에서만 한다(6절). 이 모듈 안 어디에서도 구현체를 직접 만들지 않는다.

---

## 2. 도메인 (domain/)

fastapi, sqlalchemy, pydantic, `database`, 다른 모듈을 import하지 않는다(R1). `uuid`, `datetime`, `abc`만 쓴다.

### 2.1 exceptions.py

| 클래스 | 상속 | 응답 | 쓰는 곳 |
| --- | --- | --- | --- |
| `StoreNotFoundError` | `LookupError` | 404 `NOT_FOUND` "상점을 찾을 수 없습니다." | 후속 EP(폐점 등). 읽기 메서드 `find_*`는 예외 대신 `None`/빈 목록 |
| `NotStoreOwnerError` | `PermissionError` | 403 `FORBIDDEN` "본인 상점만 …" | `Store.ensure_owned_by` (메시지는 호출 측이 전달) |
| `StoreAlreadyExistsError` | `ValueError` | 400 `STORE_ALREADY_EXISTS` "이미 개설된 상점이 있습니다." | 상점주 1인 1상점 (owner_id UNIQUE 위반) |
| `StoreAlreadyClosedError` | `ValueError` | 400 `STORE_ALREADY_CLOSED` "이미 폐점된 상점입니다." | `Store.close` |

`error_code`가 응답에 반영되는 것은 `ValueError` 하위 클래스뿐이다(`error_handlers.py` 기준). 409가 없으므로 `error_handlers.py` 수정은 필요 없다. HTTP 변환은 전역 핸들러가 하고 이 모듈은 `HTTPException`을 만들지 않는다(R6). catalog도 `StoreNotFoundError`를 자체 정의하지만(catalog.md 3.1) 서로 다른 모듈의 별개 클래스이고, catalog는 포트가 `None`을 반환할 때 자기 것을 낸다.

### 2.2 Store

| 속성 | 타입 | 규칙 |
| --- | --- | --- |
| `id` | `UUID \| None` | 저장 전 None |
| `owner_id` | `UUID` | |
| `name` | `str` | 앞뒤 공백 제거 후 1~150자 ("상점명은 1자 이상 150자 이하여야 합니다.") |
| `pickup_address` | `str` | 앞뒤 공백 제거 후 1~500자. 비어 있으면 "주소를 입력해 주세요.", 초과면 "픽업 주소는 500자 이하여야 합니다." |
| `latitude`, `longitude` | `float \| None` | 둘 다 None이거나 둘 다 값. 위도 -90~90, 경도 -180~180, 아니면 ValueError("좌표가 올바르지 않습니다.") |
| `created_at` | `datetime \| None` | 있으면 tz-aware |
| `approval_at` | `datetime \| None` | 있으면 tz-aware. **None = 미승인, 값 = 승인(개설) 시각** |
| `closed_at` | `datetime \| None` | 있으면 tz-aware. **None = 영업 중, 값 = 폐점** |

생성자 불변식: `closed_at`이 있으면 `approval_at`도 있어야 하고(`closed_at >= approval_at`). 위반 시 `ValueError("폐점 시각은 승인 시각 이후여야 합니다.")` (D4).

읽기용 파생값(저장하지 않음):

| 이름 | 반환 | 정의 |
| --- | --- | --- |
| `is_approved` (property) | `bool` | `approval_at is not None` |
| `is_closed` (property) | `bool` | `closed_at is not None` |
| `is_owned_by(user_id)` | `bool` | `owner_id == user_id` |

행위 메서드:

| 메서드 | 동작 | ValueError/예외 조건 |
| --- | --- | --- |
| `Store.open(owner_id, name, pickup_address, now, latitude=None, longitude=None)` (classmethod) | 생성자를 호출하고 `approval_at=now`로 개설. 개설과 동시에 승인 상태 (reference: "개설 시각이 `approval_at`") | 생성자 검증 + `now`가 naive면 ValueError |
| `ensure_owned_by(user_id, message="본인 상점만 접근할 수 있습니다.")` | | 다르면 `NotStoreOwnerError(message)` |
| `approve(now)` | `approval_at = now` | 이미 승인됐으면 `ValueError("이미 승인된 상점입니다.")`; `now`가 naive면 ValueError. 호출하는 EP는 후속, 도메인 메서드는 지금 둔다 |
| `close(now)` | `closed_at = now` | 미승인이면 `ValueError("승인되지 않은 상점은 폐점할 수 없습니다.")`; 이미 폐점이면 `StoreAlreadyClosedError`. "진행 중 할인 없음" 판단은 응용에서 `has_open_offers_for_store`를 먼저 확인한다(8절) |

상태 전이표 (파생 상태 = `approval_at`, `closed_at`의 유무 조합)

| 현재 | 이벤트 | 다음 |
| --- | --- | --- |
| 미승인 (`approval_at=None`) | `approve(now)` | 영업 중 |
| (없음) | `Store.open(...)` | 영업 중 (승인 시각 = 개설 시각) |
| 영업 중 | `close(now)` | 폐점 |
| 폐점 | `close(now)` | 불가 (`StoreAlreadyClosedError`) |
| 폐점 | 재개점 | **후속** (`reopen()`은 이번에 만들지 않음, D6) |
| 미승인 | `close(now)` | 불가 (D4) |

`catalog.application.ports.StoreInfo`가 요구하는 속성 `id, owner_id, name, pickup_address, approval_at, closed_at`은 `Store`의 일반 속성으로 그대로 있다. catalog는 stores를 import하지 않고 구조만 맞춘다. 추가 속성(`latitude`, `longitude`, `created_at`)은 포트가 요구하지 않으며 상위 호환이다.

### 2.3 repository.py — 추상 레포지토리 `StoreRepository(ABC)` (R8, layer-architecture §5.1)

도메인 객체(`Store`)만 주고받는다. 애그리거트 루트가 `Store` 하나이므로 파일 하나로 둔다.

| 추상 메서드 | 시그니처 |
| --- | --- |
| `find_by_id` | `async (store_id: UUID, for_update: bool = False) -> Store \| None` |
| `find_by_ids` | `async (store_ids: Sequence[UUID]) -> list[Store]` |
| `find_by_owner_id` | `async (owner_id: UUID) -> Store \| None` |
| `save` | `async (store: Store) -> Store` |

서비스는 이 네 메서드만 호출한다(R10). 동작 규약(빈 입력, 중복 제거, 정렬, 예외 변환)은 3.2의 구현체 설명이 이 추상의 계약이다.

### 2.4 service.py — 추상 도메인 서비스 `Clock(ABC)` (layer-architecture §5.2, D13 확정)

| 추상 메서드 | 시그니처 | 규약 |
| --- | --- | --- |
| `now` | `() -> datetime` | 항상 tz-aware(UTC) |

시계는 "도메인 규칙이 필요로 하지만 기술에 의존하는 기능"이라 추상으로 둔다. 서비스는 `Callable`이 아니라 `Clock`을 받는다. 테스트는 고정 시각을 돌려주는 fake `Clock`을 넘긴다.

**위치(확정, D13)**: `Clock` ABC는 모듈별로 둔다. stores는 `stores/domain/service.py`에 자기 `Clock`을 둔다. 공용 `src/common/`은 사용하지 않는다(정본 layer-architecture에 공용 위치 규칙이 없음). catalog도 자기 모듈 안에 자기 `Clock`을 두므로 두 모듈의 `Clock`은 별개 클래스이며 서로 import하지 않는다.

---

## 3. 인프라 (infrastructure/)

### 3.1 models.py — `StoreModel` / `stores` (`schema.sql` 그대로, R14)

| 컬럼 | 매핑 | 제약 |
| --- | --- | --- |
| `id` | `UUID(as_uuid=True)` PK, `default=uuid.uuid4`, `server_default=gen_random_uuid()` | |
| `owner_id` | `UUID` | `ForeignKey("users.id")`(문자열만, auth 모델 import 금지), NOT NULL, `UniqueConstraint("owner_id", name="uq_stores_owner_id")` |
| `name` | `String(150)` | NOT NULL |
| `pickup_address` | `String(500)` | NOT NULL |
| `latitude`, `longitude` | `mapped_column(Double)`, `Mapped[float \| None]` | NULL 허용 |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=now()` |
| `approval_at`, `closed_at` | `DateTime(timezone=True)` | NULL 허용 |

`TZ = DateTime(timezone=True)`를 auth처럼 모듈 상단에 둔다. `Mapped[datetime]`만 쓰면 timezone 없는 컬럼이 된다. DB `CHECK`는 `schema.sql`에 없으므로 추가하지 않는다(좌표 범위·`closed_at` 순서는 도메인 검증만).

### 3.2 repositories.py — `SqlAlchemyStoreRepository(StoreRepository)` (R8, layer-architecture §5.3)

생성자 `__init__(self, session: AsyncSession)`. 이름은 `<기술><추상명>` 규칙을 따른다. 모두 도메인 `Store`를 반환·수신한다. `commit()` 금지(`flush()`까지, R5). `*Model`을 밖으로 내보내지 않는다(R4). 변환은 `_to_domain(model)` 한 곳.

| 메서드 | 설명 |
| --- | --- |
| `find_by_id(store_id, for_update=False) -> Store \| None` | catalog 포트용. `for_update=True`는 후속 폐점·재개점에서 사용(8절) |
| `find_by_ids(store_ids: Sequence[UUID]) -> list[Store]` | `WHERE id IN (...)`. 빈 입력이면 쿼리 없이 `[]`. 중복 ID는 제거. 없는 ID는 결과에서 빠짐. 정렬 `id ASC` (결정적 순서) |
| `find_by_owner_id(owner_id) -> Store \| None` | 개설 전 "이미 있음" 사전 확인 |
| `save(store) -> Store` | 신규(`id is None`)는 insert 후 `flush()`, `id`·`created_at` 채움. 기존은 `approval_at`, `closed_at`만 update(이름·주소·좌표·owner는 개설 후 변경 불가). 신규 insert의 `IntegrityError` 중 `uq_stores_owner_id` 위반이면 `StoreAlreadyExistsError`로 변환, 그 외 `IntegrityError`(예: users FK 위반)는 그대로 올림. 대상 행이 없으면 `StoreNotFoundError` |

제약 이름 판별: `"uq_stores_owner_id" in str(err.orig)`. auth의 `UserRepository.save`는 모든 `IntegrityError`를 변환하지만, 여기서는 FK 위반을 "이미 개설된 상점"으로 잘못 알리지 않으려고 구분한다.

### 3.3 clock.py — `SystemClock(Clock)`

`now()`는 `datetime.now(timezone.utc)`를 반환한다. 상태가 없어 container에서 모듈 전역 싱글턴으로 만든다(layer-architecture §6.2).

### 3.4 동시성
- 읽기(`find_*`)는 잠금이 없다.
- 상점주 1인 1상점: 사전 확인(`find_by_owner_id`)은 최적화일 뿐이고, 동시에 두 요청이 오면 `uq_stores_owner_id`가 막고 레포지토리가 `StoreAlreadyExistsError`로 바꾼다. `with_for_update()`는 필요 없다.
- 폐점 vs catalog 할인 등록 경합은 8절 메모.

---

## 4. 응용 (application/)

```python
class StoresApplicationService:
    def __init__(self, session: AsyncSession, stores: StoreRepository, clock: Clock): ...
```
- 세 인자 모두 **필수**다(기본값 없음, 기본 구현체를 만들지 않는다, R8). 타입은 domain의 추상(`StoreRepository`, `Clock`)이고 infrastructure를 import하지 않는다(R2).
- 서비스는 `commit()`만 한다(R5). 생성은 `src/container.py`의 `create_stores_service`만 한다(R9, R12).
- 테스트: fake 레포지토리·fake `Clock`을 넘겨 DB 없이 검증한다.

### 4.1 catalog `StorePort`를 만족하는 읽기 메서드

catalog.md 2.1의 시그니처와 이름을 그대로 맞춘다(catalog는 위치 인자로 호출).

| 메서드 | 반환 | 시나리오 |
| --- | --- | --- |
| `async find_store_by_id(self, store_id: UUID)` | `Store \| None` | `stores.find_by_id(store_id)`만 호출. 없으면 **예외 없이 `None`** (catalog가 자기 `StoreNotFoundError`를 낸다). `commit` 없음 |
| `async find_stores_by_ids(self, ids: Sequence[UUID])` | `list[Store]` | `stores.find_by_ids(ids)`. 없는 ID는 생략, 빈 입력이면 `[]`. 이번 범위에서 catalog는 쓰지 않음(후속 #8) |

두 메서드는 조회만 하며 같은 요청 세션을 쓰는 catalog 서비스의 트랜잭션에 영향을 주지 않는다(R13: 호출되는 쪽은 커밋하지 않음).

### 4.2 쓰기 (최소 개설 API용)

**`open_store(owner_id: UUID, owner_name: str | None, pickup_address: str) -> Store`**
1. `stores.find_by_owner_id(owner_id)`가 있으면 `StoreAlreadyExistsError` (400)
2. `Store.open(owner_id, name=owner_name or "", pickup_address, now=self.clock.now())` — 이름이 비어 있으면 도메인이 400 ("상점명은 1자 이상 150자 이하여야 합니다."). 좌표는 None (D2)
3. `stores.save(store)` → (동시 요청 시 레포지토리가 `StoreAlreadyExistsError`로 변환) → `session.commit()` 한 번 → 반환

서비스는 `auth.domain.user.User`를 import하지 않고 `owner_id`, `owner_name` 원시 값만 받는다(stores가 auth 도메인에 의존하지 않게 하려는 선택). 비즈니스 검증은 전부 `Store`에 있고 서비스는 조율만 한다(R3).

### 4.3 모듈 간 트랜잭션 경계
- 이번 범위에서 stores는 다른 모듈의 쓰기를 부르지 않는다. catalog가 stores를 같은 요청 세션으로 읽을 뿐이다. 한 요청 안에서 `Depends(get_db)`는 같은 세션을 주므로 container가 만든 stores 서비스와 catalog 서비스는 같은 세션을 공유한다(R13).
- 후속 폐점은 8절.

---

## 5. 표현 (presentation/)

### 5.1 의존성·조립 (R9, layer-architecture §6)
- 인증: `auth.presentation.dependencies.OwnerUser` (토큰 없음/잘못됨 401, 역할 불일치 403).
- `presentation/dependencies.py`에 플레이스홀더만 선언한다. 구현체나 서비스를 만들지 않는다.

```python
def provide_store_repository() -> StoreRepository:   # catalog 외 모듈이 추상 레포를 쓸 때용
    raise NotImplementedError("StoreRepository 의존성이 주입되지 않았습니다.")

def provide_stores_service() -> StoresApplicationService:
    raise NotImplementedError("StoresApplicationService 의존성이 주입되지 않았습니다.")
```
- router는 `Annotated[StoresApplicationService, Depends(provide_stores_service)]`만 쓴다. 라우터 안의 `get_stores_service`·`StoresApplicationService(db)` 생성은 두지 않는다.
- catalog 쪽 조립(catalog.md 2.2, 7.1)은 router가 아니라 **container**에서 한다: `create_store_port`가 stores 서비스를 받아 `StorePort`로 돌려준다(6절). stores는 catalog를 import하지 않는다.

### 5.2 엔드포인트 (prefix `/v1`, tags `["상점"]`)

| Method | URI | 요청 | 응답 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- |
| POST | `/v1/stores` | `StoreOpenRequest` | `StoreResponse` | 201 | 400(주소 없음·길이·상호 없음·이미 개설된 상점), 401, 403(`OWNER` 아님) |

- 명세의 400 "주소를 찾을 수 없습니다"(지오코딩 실패), 400 "동일한 상점명과 주소의 상점이 이미 존재합니다", 403 "승인 대기 중인 상점주 계정입니다"는 이번에 구현하지 않는다(D2, D5, D7). 명세의 "422 대신 400" 규칙은 전역 핸들러대로(`VALIDATION_ERROR`).

### 5.3 스키마 (명세 필드명 그대로, R15)

| 스키마 | 필드 |
| --- | --- |
| `StoreOpenRequest` | `pickup_address: str` (`max_length=500`; 빈 값 검사는 도메인에서 해 명세 문구 "주소를 입력해 주세요."를 낸다) |
| `StoreResponse` (`from_attributes=True`) | `id, owner_id, name, pickup_address, latitude: float \| None, longitude: float \| None, created_at, approval_at, closed_at: datetime \| None` |

router는 서비스만 호출하고 예외를 잡지 않는다(R6, R7): `service.open_store(owner.id, owner.name, body.pickup_address)`.

### 5.4 목록 쿼리
이번 범위에 목록 API는 없다. 상점 목록·검색은 명세에 없고 catalog 후속(#8)이 좌표를 `find_stores_by_ids`로 가져간다.

---

## 6. 조립 — `src/container.py` / `src/main.py` (모듈 밖 변경 제안, 이 문서는 쓰지 않는다)

R9: 구현체 연결은 `src/container.py`에서만 한다. 현재 `src/container.py`는 없다(0절). **확정(D14): stores implementer가 골격(import, `wire_dependencies`, stores 구역)을 먼저 만든다.** catalog는 이후 자기 구역만 추가한다. `docs/operations/orchestration.md` §4에 따라 implementer는 자기 모듈 구역만 쓴다. 아래는 stores 구역이다.

### 6.1 container.py — stores 구역

```python
# ── stores ───────────────────────────
_clock = SystemClock()   # 상태 없는 유틸은 싱글턴


def create_store_repository(session: AsyncSession = Depends(get_db)) -> StoreRepository:
    return SqlAlchemyStoreRepository(session)


def create_stores_service(
    session: AsyncSession = Depends(get_db),
    stores: StoreRepository = Depends(create_store_repository),
) -> StoresApplicationService:
    return StoresApplicationService(session=session, stores=stores, clock=_clock)
```
`wire_dependencies(app)` 매핑에 추가: `provide_store_repository: create_store_repository`, `provide_stores_service: create_stores_service`. R9에 따라 stores의 `provide_*`는 전부 매핑한다.

골격 범위(D14, C10): 이번 범위의 container에는 **auth 구역을 넣지 않는다**. auth의 container 이전은 별도 작업이다. 따라서 골격의 `wire_dependencies`는 stores 매핑만 가진다.

### 6.2 catalog와의 연결 (catalog 구역, catalog 설계가 정본)

기준 제안(catalog 설계와 어긋나면 9절 C8로 정리한다):
- catalog가 `catalog/presentation/dependencies.py`에 `provide_store_port() -> StorePort`를 선언한다.
- container의 `create_store_port(stores: StoresApplicationService = Depends(create_stores_service)) -> StorePort`가 stores 서비스 인스턴스를 그대로 돌려준다(구조적 만족).
- `create_catalog_service`는 `Depends(create_store_port)`로 `StorePort`를 받는다. 같은 요청 세션이 공유된다.
- 의존 그래프(이번 범위): `get_db → create_store_repository → create_stores_service → create_store_port → create_catalog_service`. 순환 없음(R12).

### 6.3 main.py
```python
# 모든 models.py는 lifespan(create_all)보다 먼저 import해야 한다. FK 대상이 먼저 등록돼야 하므로 순서는 auth → stores → catalog.
from auth.infrastructure import models as auth_models      # noqa: F401  (users)
from stores.infrastructure import models as stores_models  # noqa: F401  (stores)  ← 추가
from catalog.infrastructure import models as catalog_models  # noqa: F401  (catalog 구현 시 추가)
from container import wire_dependencies                     # 추가
from stores.presentation.router import router as stores_router  # 추가

register_exception_handlers(app)
wire_dependencies(app)              # 라우터 등록 전에 (추가)
app.include_router(stores_router)   # 추가
```
`create_all`은 FK 의존 순서대로 테이블을 만들지만, import 순서가 어긋나 `stores` 모델이 로드되지 않으면 catalog에서 `NoReferencedTableError`가 난다(catalog.md B1). import 정렬 도구가 알파벳순으로 `catalog`를 앞에 두지 않도록 `# noqa` 옆에 주석으로 순서 이유를 적는 것을 권장한다. `container.py`와 `main.py`는 조립 지점이라 `layer-check` 제외 대상이다.

---

## 7. 시연·테스트용 상점 확보 방법

| 안 | 내용 | 장점 | 단점 |
| --- | --- | --- | --- |
| A. lifespan 시드 | 서버 시작 시 `main.py`에서 상점을 insert | API 없이 즉시 데이터 | 상점은 `OWNER` 회원을 FK로 요구하므로 시드가 회원(이메일·비밀번호 해시)도 만들어야 하고, 고정 계정 비밀번호가 코드·환경변수에 들어감(R16 주의). `main.py`·`.env.example` 수정과 환경변수 게이트(운영 보호) 필요. 매 시작마다 멱등 검사. catalog 테스트의 토큰 획득도 결국 로그인 API가 필요 |
| **B. 최소 생성 API (기본값)** | `POST /v1/stores` (명세 EP#1의 축소판, 5절) | 시연 흐름이 운영과 같음: 회원가입(OWNER, `name`=상호) → 로그인 → 상점 개설 → catalog EP. 비밀번호·시드 코드 없음. 후속에서 버릴 코드 없음(명세 EP#1 그대로 확장) | 이번 범위에 presentation 1파일 쌍 추가. 지오코딩·승인 대기 판단은 생략(D2, D7) |

기본값: **B**. 단위·서비스·DB 테스트는 API 없이 `Store.open(...)`과 `SqlAlchemyStoreRepository.save`/fake 레포지토리로 상점을 만든다. 승인 전·폐점 상태 상점이 필요한 catalog 테스트는 `Store(...)`를 직접 생성(`approval_at=None` 또는 `closed_at` 지정)해 레포지토리로 저장한다(API는 승인된 상점만 만든다).

---

## 8. 후속 (이번 범위 아님)

EP 목록(한 줄씩):
- 개설 확장: `POST /v1/stores` — 지오코딩(주소→좌표, 실패 시 400), 상점명+주소 중복 400, 승인 대기 상점주 403 (stores.md #1 확인 필요 3건) — **승인 대기 403은 구현됨(D7), 지오코딩·중복은 14절에 설계됨(2026-11-05)**
- 폐점: `POST /v1/stores/{store_id}/close` (stores.md #2) — **13절에 설계됨(2026-11-05)**
- 재개점: `POST /v1/stores/{store_id}/reopen` (명세 제안, 명세 확인 필요)
- 관리자 승인: 명세에 EP 없음. "관리자 승인"이 상점 승인인지 상점주 계정 승인인지 미정(D5). 승인 EP가 생기면 `Store.approve(now)` 사용
- 상점 단건/목록 조회: 명세에 없음

폐점 시 catalog 호출 메모 (**2026-11-05: 13절로 대체됨. 아래는 이력이며 순서·잠금·순환 해소는 13절이 정본. 특히 항목 1의 "서비스에서 if로 400"은 R3에 따라 도메인 `close(now, *, has_open_offers, has_pickup_pending)`로 바뀌었다**):
1. `close_store(user, store_id)` 순서: `stores.find_by_id(store_id, for_update=True)`(404) → `ensure_owned_by(user.id, "본인 상점만 폐점할 수 있습니다.")`(403) → **`open_offers.has_open_offers_for_store(store_id, now=now)`가 True면 `StoreHasOpenOffersError`(400 "진행 중이거나 예정된 할인 판매가 있어 폐점할 수 없습니다.")** → (reservations 연계 `has_pickup_pending_for_store` 400 "픽업 대기 중인 예약이 있어 폐점할 수 없습니다.") → `store.close(now)` → `save` → `commit()`. 호출 위치는 **응용 계층 서비스**이며 도메인 `close`에는 넣지 않는다. `now`는 키워드 인자로만 넘긴다(확정 서명: `has_open_offers_for_store(store_id, *, now=None) -> bool`, catalog.md 2.3·CI-2와 동일).
2. 방향(R11): stores는 catalog를 import하지 않고 `stores/application/ports.py`에 쓰는 쪽 포트 `OpenOffersPort`(`typing.Protocol` 또는 ABC, `has_open_offers_for_store(store_id, *, now=None) -> bool`, `now`는 키워드 전용)를 정의한다. `StoresApplicationService` 생성자에 `open_offers: OpenOffersPort`를 **필수 인자**로 추가한다. catalog 서비스가 구조적으로 만족하며(catalog.md 2.3 시그니처와 동일), 연결은 container의 `create_open_offers_port`(catalog 서비스를 반환)가 한다. `stores/presentation/dependencies.py`에는 `provide_*`만 추가한다.
3. **생성 순환 주의(R12)**: 이 시점에 container 팩토리 그래프가 `create_stores_service → create_open_offers_port → create_catalog_service → create_store_port → create_stores_service`로 순환한다(FastAPI `Depends` 재귀). 서비스 생성자 안에서 다른 서비스를 만들어 해결하지 않는다. 해결: 읽기 전용 `StoreQueryService`(`find_store_by_id`, `find_stores_by_ids`, 의존은 `StoreRepository`뿐)를 stores 안에 분리하고 `create_store_port`가 이것을 반환하게 한다. 그러면 그래프는 `repo → StoreQueryService → create_store_port → catalog 서비스 → create_open_offers_port → StoresApplicationService(close 포함)`로 비순환이 된다. 이번 범위에서는 순환이 없으므로 분리하지 않는다(D15 = catalog.md D22와 동일 결정, 9절 C2·C3).
4. 동시성: catalog의 할인 등록은 상품 행만 잠그므로(catalog.md 5.3) "폐점 확인 직후 할인 등록" 경합이 남는다. 상점 행 잠금 순서 확정 필요(결정 D8).
5. 폐점 후 재개점은 같은 행의 `closed_at`을 `NULL`로 되돌리는 방식(owner UNIQUE 때문, 명세 확인 필요 항목과 일치).

---

## 9. 정합 이슈 (catalog.md는 고치지 않고 기록만)

| # | catalog.md 위치 | 이슈 | 영향 | 제안 |
| --- | --- | --- | --- | --- |
| C1 | 2.2 / 8절 | `StoreInfo` 필드가 `id, owner_id, name, pickup_address, approval_at, closed_at`뿐이다. 그러나 8절 후속 #8(주변 할인)은 "좌표 포함 `find_stores_by_ids`"를 요구한다. | 지금은 영향 없음. #8 때 포트 확장이 필요 | stores의 `Store`는 `latitude`, `longitude`를 이미 가지므로 catalog가 `StoreInfo`에 두 필드를 추가하면 된다(상위 호환) |
| C2 | 2.2 "stores → catalog 단방향" vs 9절 다이어그램 | (container 기준으로 갱신) 조립이 router가 아니라 `src/container.py`로 옮겨졌다. 따라서 catalog.md의 `catalog.presentation -> stores.application`(조립) 화살표는 사라지고, 두 모듈의 presentation·application은 서로를 import하지 않는다. 연결은 container만 안다(`container → stores.application`, `container → catalog.application`). stores 쪽 `OpenOffersPort`(8절)를 두면 `stores.application`도 catalog를 import하지 않는다. | 문서 표현. 양쪽 모듈 간 import 순환 없음 | catalog.md 9절의 `stores.application -> catalog.application`·`catalog.presentation -> stores.application` 화살표를 "container가 연결"로 바꾼다 |
| C3 | 2.3 | (container 기준으로 갱신) `has_open_offers_for_store(store_id, *, now=None)` 호출 시 팩토리 그래프가 순환한다(8절 메모 3). catalog.md에는 이 순환 언급이 없다. | 폐점 구현 시 `Depends` 재귀 | 8절 메모 3의 `StoreQueryService` 분리(D15, catalog.md D22와 동일 결정)를 폐점 구현 때 채택. 그때 catalog의 `create_store_port`는 `StoreQueryService`를 반환 |
| C4 | 2.4 | stores에 요구한 범위는 모델과 읽기 2개뿐이다. 이 설계는 시연용 개설 API(7절 B안)를 더했다. | catalog 구현은 영향 없음 | 팀이 A안·범위 축소를 택하면 5절의 router·schemas·`open_store`만 빼면 된다(container·dependencies의 stores 구역은 유지) |
| C5 | 3.1 `StoreNotFoundError` | catalog와 stores가 같은 이름의 예외를 각자 정의한다. | 둘 다 `LookupError` 404 `NOT_FOUND`라 응답은 동일. import 시 혼동 가능 | 그대로 두되 서로의 예외를 import하지 않는다 |
| C6 | 3.2 `StoreRef.approved` / D19 | 이 설계의 API는 개설 즉시 `approval_at=now`(reference: "개설 시각이 `approval_at`")라서 API로 만든 상점은 항상 승인 상태다. `StoreNotApprovedError`는 시드·테스트로 만든 `approval_at=NULL` 상점에서만 일어난다. | 동작 차이 없음, 의미 확인용 | 관리자 승인 정의(D5)가 정해지면 catalog의 문구·검사 유지 여부 재검토 |
| C7 | 2.3, D4 vs stores.md #2 | catalog의 "진행 중" 정의(`is_active and now < sales_end`)는 매진(`SOLD_OUT`)도 포함한다. stores 명세의 폐점 차단은 "진행 중이거나 예정된 할인"이라 매진 건도 막는지 모호하다. | 폐점 구현 시 | 임시로 catalog 정의를 그대로 사용(D9) |
| C8 | 2.2, 7.1, 9절 (catalog.md 구버전 서술) | 포트·`provide_*`·팩토리 이름 정합. 이 설계의 기준: 포트 `StorePort`(catalog 정의), `catalog/presentation/dependencies.py`의 `provide_store_port() -> StorePort`, container의 `create_store_port`가 stores 서비스를 반환. catalog.md가 병렬 갱신 중이라 이름이 다를 수 있다. 또한 구버전 서술에는 router 조립(`get_catalog_service`에서 `StoresApplicationService(db)` 생성)과 `products: ... \| None = None` 기본 생성자 인자, `stores: StorePort` 필수·나머지 기본 생성이 남아 있어 R8·R9와 충돌한다. | 이름 불일치 시 container 구현 단계에서 import·매핑 오류 | catalog 설계 갱신본의 포트·provide·create 이름을 확인해 맞춘다(stores는 `StorePort` 이름을 요구하지 않고 구조만 만족하므로 stores 쪽 변경은 없음) |
| C9 | (container 신설) | `src/container.py`가 없어 stores와 catalog 구현자가 각자 파일을 만들 수 있다(쓰기 경합). | **해소(2026-11-03 사용자 확정, D14)** | stores implementer가 골격(import, `wire_dependencies`, stores 구역)을 먼저 만들고, catalog는 이후 자기 구역만 추가한다. 구현 순서는 오케스트레이터가 stores → catalog로 정한다 |
| C10 | (auth 기존 구현) | `src/auth`는 아직 서비스 내부 생성·`get_db` 직접 조립 방식이다(layer-architecture 이전 방식). stores의 `OwnerUser` 의존은 auth의 현행 의존성을 그대로 쓰므로 영향 없지만, container에 auth 구역이 없다. | 범위 밖, 별도 작업 (2026-11-03 사용자 확정) | 이번 범위에서 container에 auth 구역을 넣지 않는다. auth의 container 이전은 별도 작업으로 다룬다 |
| C11 | `docs/design/admin.md` C11·C19, D17, D22 | admin이 stores에 요청한 세 가지를 13절이 받는다: ① `Store.close` 정지 가드(`StoreSuspendedError`, 순서 폐점 → 정지 → 미승인)는 **코드에 이미 구현**(`store.py:153-161`), 13.1이 순서를 유지한 채 플래그 검사를 그 뒤에 붙인다 ② 8절 메모에 "정지된 상점은 상점주 폐점 불가" 추가 → 13.2 ③ `has_open_offers_for_store`가 정지된 할인을 "진행 중"으로 세므로(admin.md D22, `DiscountOffer.is_open`: `is_active and now < sales_end`, `discount_offer.py:194`) 정지 할인이 `sales_end`를 넘길 때까지 상점주는 폐점할 수 없다 → 13.2의 "알려진 영향" | 해소(문서) | admin.md C11·C19를 닫아도 된다(admin.md는 이 문서에서 고치지 않음) |
| C12 | `catalog/application/service.py:187-199` `register_offer`, `create_product:117-131`, `relist_offer` | 상점 행을 잠그지 않고 포트로 읽기만 한다(`_load_store` → `find_store_by_id`, 잠금 없음). 상점주 폐점은 상점 행만 잠그고 할인 존재를 비잠금 조회하므로 "확인 직후 등록" 경합이 남는다(13.6) | 폐점된 상점에 진행 중 할인이 생길 수 있음(드묾) | 후속 제안(범위 밖): catalog가 `register_offer`·`relist_offer`에서 `product_id`를 잠금 없이 읽고 → **상점 행 잠금(stores `lock_store`를 StorePort에 추가) → 상품 행 잠금** 순으로 바꾼다. 순서가 `store → product → offer`이어야 admin `close_store`(상점 → 상품 → 할인, admin.md D34)와 교착하지 않는다. 현재 `product → store(비잠금)`을 `product → store(잠금)`으로만 바꾸면 admin과 역순이 되어 **교착 위험**이므로 금지 |
| C13 | `admin/infrastructure/reservation_admin.py`, `catalog/infrastructure/reservation_lookup.py` | reservations가 미연계라 같은 종류의 임시 구현이 모듈마다 생긴다(admin·catalog·stores). 실제 연계 시 세 곳을 따로 교체해야 한다 | 후속 reservations PR의 작업량 | stores 쪽은 `PickupPendingPort` 하나만 교체(container `_pickup_pending` 한 줄). reservations 담당이 한 어댑터가 여러 포트를 만족시키는지 정한다 |
| C14 | `tests/stores/test_service.py:65`, `tests/stores/test_admin_service.py`(생성 호출), `tests/admin/test_wiring.py:69` | 13.7로 `StoresApplicationService` 생성자에 필수 인자(`open_offers`, `pickup_pending`)가 늘고 `find_store_by_id`·`find_stores_by_ids`는 `StoreQueryService`로 이동한다. 기존 테스트가 3인자로 만들고 이 메서드들을 호출한다 | 기존 stores 테스트 수정 필요(구현자 소유 `tests/stores/**`) | 13.9 파일 목록에 포함. `admin/test_wiring.py`는 `StoreAdminPort` 구조 만족만 보므로 변경 없음(`lock_store` 등은 유지) |
| C15 | `src/container.py:157-160`, 구역 소유권(orchestration §4) | `create_store_port`는 catalog 구역에 있고 지금 `create_stores_service`를 부른다. 13.7이 이 본문을 `create_store_query_service`로 바꾸고, stores 팩토리 배치를 **catalog 구역 뒤로** 옮겨야 한다(Python 기본 인자 `Depends(...)`는 정의 시점에 평가되어 순서 의존) | 한 사람이 stores·catalog 구역을 함께 고침 | 오케스트레이터가 stores implementer에게 `create_store_port` 한 함수 수정과 stores 팩토리 재배치를 허용한다(13.7, 13.9) |
| C16 | 이 문서 0절·5.1·D7의 옛 서술 | 0절("stores 비어 있음", "container 없음"), 5.1(`OwnerUser`), D7("검사하지 않음")은 현재 코드와 다르다 | 문서 혼동 | 0절 표는 이력, 5.1·D7은 13절·D7 갱신행이 우선(헤더 갱신 이력에 명시) |

---

## 10. 테스트 계획 (요약)

- domain (`tests/stores/test_domain.py`): `Store` 생성 검증(이름·주소 길이/공백, 좌표 쌍·범위, naive datetime 거부), `closed_at` 불변식, `open`, `approve`/`close` 전이와 예외, `is_approved`/`is_closed`/`is_owned_by`
- service (`test_service.py`): fake `StoreRepository`(추상 상속)·fake `Clock`. `find_store_by_id` 없음 → `None`, `find_stores_by_ids` 빈 입력/누락 ID, `open_store`의 중복(사전 확인) 400, 상호 없음 400, 커밋 1회, 개설 시각이 fake `Clock` 값
- infrastructure (`@pytest.mark.db`): `SqlAlchemyStoreRepository` 저장·조회 왕복(tz 유지, 좌표 NULL), `uq_stores_owner_id` 위반이 `StoreAlreadyExistsError`로 변환, users FK 위반은 변환되지 않음, `find_by_ids` 중복·누락
- presentation (`@pytest.mark.db`): 401/403(CUSTOMER)/201, 두 번째 개설 400, 에러 본문 형식 `{"success": false, ...}`. 필요 시 `app.dependency_overrides[provide_stores_service]`로 fake 서비스 주입
- 조립: `wire_dependencies(app)` 후 `provide_store_repository`, `provide_stores_service`가 `app.dependency_overrides`에 모두 있는지(R9), `import main` 성공(R12)
- 호환성: catalog의 `StorePort`/`StoreInfo` Protocol(`runtime_checkable` 또는 mypy 수준)에 `StoresApplicationService`·`Store`가 맞는지 확인하는 테스트 1개(catalog 구현 시 추가)

---

## 11. 모듈 밖 변경 제안 (이 문서는 쓰지 않는다)

- `src/container.py` **신설**(6.1, D14 확정): stores implementer가 먼저 만든다. imports, 모듈 전역 `_clock`, stores 구역 팩토리 2개, `wire_dependencies(app)`(stores `provide_*` 2개 매핑)로 골격을 구성한다. auth 구역은 넣지 않는다(C10, 별도 작업). catalog 구역(`create_store_port` 등)은 이후 catalog 구현자가 자기 구역만 추가한다. 쓰기 소유권: implementer는 자기 모듈 구역만(`docs/operations/orchestration.md` §4).
- `src/main.py`: 6.3의 import 순서(auth → stores → catalog), `wire_dependencies(app)` 호출(`register_exception_handlers` 뒤, 라우터 등록 전), `stores_router` 등록
- `docs/design/catalog.md`: 9절 정합 이슈 C1~C3, C8 반영 여부 검토 (이번 갱신에서 수정하지 않음)
- `docs/reference/stores.md`: 지오코딩·승인 정의가 정해지면 확인 필요 항목 갱신
- (2026-11-05, 폐점) `src/container.py`: `create_store_port` 본문 변경, stores 팩토리 재배치, `_pickup_pending` 싱글턴, `create_open_offers_port` 추가(13.7, C15). 구역 경계를 넘으므로 오케스트레이터 조정 필요. `src/main.py`는 변경 없음(라우터는 기존 `stores_router`에 EP 추가)
- (2026-11-05, 폐점) `docs/reference/stores.md` §2: 상태 보존 변경 제안 없음. 선택 제안: 400 "정지된 상점입니다"(`STORE_SUSPENDED`)가 에러 표에 없다(D16). 명세 정본이므로 이 문서에서 고치지 않고 오케스트레이터가 판단
- (2026-11-05, 폐점) `docs/design/admin.md`: C11·C19를 해소로 표시 가능(C11 행). 이 문서에서 고치지 않음
- (2026-11-05, 폐점) catalog: **이번 범위에서 변경 없음.** `has_open_offers_for_store(store_id, *, now=None)`가 이미 있고(`catalog/application/service.py:333`) 레포지토리 `exists_open_by_store`도 있다. 잠금 보강은 C12·D22 후속 제안
- `pyproject.toml`·`error_handlers.py`·`.env.example`·`schema.sql`: 변경 없음 (스키마 변경 제안 없음. 단 `uq_stores_owner_id` 이름은 `models.py`의 이름 지정일 뿐 DDL 의미는 `schema.sql`과 같다)

---

## 12. 결정 필요 항목 (임시 기본값)

임시 기본값은 확정이 아니라 제안이다(사용자 미확정). 단 **D13·D14는 2026-11-03 사용자가 확정**했다(표에 "확정"으로 표시). 코드에서는 표의 위치에 모아 바꾸기 쉽게 한다. D1~D12는 값을 바꾸지 않았고 코드 위치만 DI 구조에 맞게 고쳤다.

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 | 코드 위치 |
| --- | --- | --- | --- | --- | --- |
| D1 | 시연용 상점 확보 방식 | 요청 4 | 최소 생성 API(`POST /v1/stores`, 7절 B안) | 시드는 회원·비밀번호 시드가 따로 필요하고 운영 흐름과 다름 | `presentation/router.py`, `application/service.open_store` |
| D2 | 주소 → 좌표 변환 | stores.md #1 확인 필요 | **(2026-11-05 갱신: 14절 D26~D31이 대체)** 네이버 지오코딩으로 변환, 실패 시 개설 불가. 원래 값("변환하지 않음, NULL")은 폐기 | 스키마가 NULL 허용, 외부 API 미정 | `StoresApplicationService.open_store` (후속에 추상 `Geocoder`를 domain에 두고 container에서 주입) |
| D3 | 상점명 출처 / 상호 없는 상점주 | stores.md #1, auth `User.name` 선택값 | `name = user.name`(상호). 비어 있으면 400 "상점명은 1자 이상 150자 이하여야 합니다." | 명세 "가입 시 등록한 상호로 자동 설정" | `Store.open`, 라우터 인자 |
| D4 | 미승인 상점의 폐점, `closed_at` ≥ `approval_at` | 도메인 일관성 | 미승인 폐점 불가, 폐점 시각은 승인 시각 이후 | 승인 전에는 "영업 중"이 아님 | `Store.__init__`, `Store.close` |
| D5 | "관리자 승인"의 대상과 승인 EP | README 상태 값, stores.md #1 | 승인 EP 없음. 개설 시각 = `approval_at` 즉시 기록. 승인 상태 확인은 `approval_at` 유무 | 명세 "개설 시각이 `approval_at`", catalog D19와 동일 | `Store.open`, `Store.is_approved` |
| D6 | 재개점 | stores.md #2 확인 필요 | 이번에 만들지 않음. 후속에서 같은 행의 `closed_at` NULL 복원 | owner UNIQUE, 명세 | 후속 `Store.reopen()` |
| D7 | 승인 대기 상점주 403 | stores.md #1·#2, 스키마 5절 7 | **(2026-11-05 갱신) 해소됨**: `users.status`가 생겨 auth의 `ApprovedOwnerUser`(PENDING·REJECTED 403)를 개설·폐점 라우터가 쓴다(코드 확인: `router.py:5`, `auth/presentation/dependencies.py:80-96`). 원래 값("검사하지 않음")은 폐기 | auth `ensure_approved_owner` | 개설·폐점 router |
| D8 | 폐점과 할인 등록 경합 | 8절 메모 4 | **(2026-11-05 갱신)** 폐점 시 상점 행 `FOR UPDATE` 채택(13.6). catalog 쪽 잠금 보강은 사용자 확인 후속(D22, C12) | catalog `register_offer`는 상품 행만 잠금(`catalog/application/service.py:189`) | `_locked_store`(구현됨) |
| D9 | 폐점 차단의 "진행 중" 정의 | stores.md #2, catalog D4 | catalog `has_open_offers_for_store` 정의(매진 포함)를 그대로 사용 | 한곳에서 정의 | catalog `DiscountOffer.is_open` |
| D10 | 상점명+주소 중복, 이름·주소 변경 | stores.md #1 | **(2026-11-05 갱신: 중복 검사는 14절 D32·D33이 대체, 원래 "검사 안 함"은 폐기)** 개설 후 이름·주소·좌표·owner는 `save()`에서 갱신하지 않음 | 명세 "개설 후 변경 불가" | `SqlAlchemyStoreRepository.save` |
| D11 | 상점명·주소 길이 | 스키마 | 이름 1~150자, 주소 1~500자 | `schema.sql` VARCHAR 길이, 명세 "최대 500자" | `Store` 생성자 |
| D12 | 상점주 역할 값 | auth 명세, `Role.OWNER` | `OWNER` | 이미 구현된 auth 코드 | `auth.domain.user.Role` |
| D13 | 시계 주입 형태·위치 | V1, layer-architecture §5.2 | **확정(2026-11-03, 사용자 승인)**: 추상 `Clock(ABC).now()`는 **모듈별로 둔다**. stores는 `stores/domain/service.py`에 자기 `Clock`을 두고 `SystemClock`(infrastructure)을 container 싱글턴으로 주입한다. 공용 `src/common/`은 사용하지 않는다. 기존 `Callable[[], datetime]`·기본 `datetime.now`는 폐기 | §5.2가 "시계"를 추상 도메인 서비스 예로 듦, R8. 정본(layer-architecture)에 공용 위치 규칙이 없음 | `domain/service.py`, `infrastructure/clock.py`, `container._clock` |
| D14 | `src/container.py` 최초 생성 책임 | 0절, C9 | **확정(2026-11-03, 사용자 승인)**: stores implementer가 `src/container.py` 골격(import, `wire_dependencies`, stores 구역)을 먼저 만든다. catalog는 이후 자기 구역만 추가한다. 이번 범위에 auth 구역은 넣지 않는다(C10). C9(동시 생성 경합)는 이 결정으로 해소 | orchestration §4, layer-architecture §6.2·§6.3 | `src/container.py`, `src/main.py` |
| D15 | 폐점 도입 시 팩토리 순환 해소 방식 | V4, R12 | **(2026-11-05 갱신: 폐점 구현과 함께 채택, 13.7)** 읽기 전용 `StoreQueryService` 분리, `create_store_port`가 이를 반환. (임시 기본값, 사용자 미확정이나 catalog.md D22와 같은 결정이고 대안이 더 크다. 13.7 대안 비교) | 서비스 생성자 안 생성 금지(R12), 순환 `Depends` 불가 | 후속 `application/query_service.py`. 비고: **catalog.md D22와 동일 결정**(상호 참조, 값은 두 문서에서 함께 바꾼다) |

| D16 | 폐점 검사 순서와 정지·미승인 가드 충돌 | 명세 §2 에러 표, admin.md D17 | 인증 의존성(401 → 역할 403 → 승인 대기 403) → 404 → 403(본인 아님) → **이미 폐점 400 → 정지 400 `STORE_SUSPENDED` → (미승인 400)** → 진행 중 할인 400 → 픽업 대기 예약 400. 상태 가드가 상품·예약 검사보다 먼저다 (임시, 미확정) | 폐점·정지 상점은 폐점 가능 여부가 이미 결정되어 있어 하위 조회가 의미 없고, 명세 표 순서(폐점 → 할인 → 예약)와 admin.md D17 순서(폐점 → 정지 → 미승인)를 모두 보존 | `Store.close` (13.1) |
| D17 | 새 예외와 예약 메시지 재사용 | 명세 §2 에러 표 | **새로** `StoreHasOpenOffersError`(`ValueError`, 400 `STORE_HAS_OPEN_OFFERS`, 명세 문구). 예약은 **기존** `StoreHasReservedReservationsError`를 재사용하되 명세 문구 "픽업 대기 중인 예약이 있어 폐점할 수 없습니다."를 생성자 인자로 넘긴다(관리자 강제 폐점의 기본 문구는 그대로) (임시) | 상점주 폐점과 관리자 폐점은 같은 사유(처리 안 된 예약)이므로 `error_code` 공유가 프론트에 유리. 문구만 명세별로 다름 | `stores/domain/exceptions.py`, `Store.close` |
| D18 | 도메인 `close` 시그니처 | R3, `force_close` 선례 | `close(now, *, has_open_offers: bool = False, has_pickup_pending: bool = False)`. 서비스는 두 값을 조회해 넘기기만 하고 if를 두지 않는다. **기본값 False는 기존 호출(`close(now)` 테스트 ~9곳)과의 호환용이며, 서비스가 항상 명시 전달**한다(서비스 테스트로 고정) (임시) | `force_close(reason, now, has_reserved_reservations)` 선례. 필수 인자로 바꾸면 기존 테스트 호출부 전부 수정 필요 | `Store.close` |
| D19 | 인증 의존성과 정지된 상점주 | R7, auth D5·D35, admin.md D17 | `ApprovedOwnerUser`. PENDING·REJECTED 상점주 403(명세 문구 "승인 대기 중인 상점주 계정입니다."), **정지된 상점주 계정은 403 "정지된 계정입니다."**(`get_current_user`가 `allow_suspended=False`, `user.py:333`) — 정지 계정은 폐점 불가(admin 문서 "폐점 등 나머지 보호 API는 403"과 일치). `SuspendedAllowedOwnerUser`는 쓰지 않는다 (임시) | 개설 EP와 같은 의존성, 명세 403 표 | `presentation/router.py` |
| D20 | 폐점 응답 필드 | R15, 명세 §2 응답 | 명세대로 `id, name, closed_at`만(`StoreCloseResponse`). `status`·`closed_reason`은 넣지 않는다(항상 CLOSED·None이라 정보 없음) (임시) | 명세 일치 | `presentation/schemas.py` |
| D21 | 픽업 대기 예약 확인 포트 | 사용자 지시, R11, R16 | stores 소유 포트 `PickupPendingPort.has_pickup_pending_for_store(store_id) -> bool`(`stores/application/ports.py`) + 임시 구현 `NoPickupPendingReservations`(항상 False, **미연계**, `stores/infrastructure/pickup_pending.py`). 실제 구현은 후속(reservations 담당). "픽업 대기"의 상태 집합(`RESERVED`/`PAID` 등)도 reservations 후속에서 정함 (임시) | admin `NoReservationAdmin.has_reserved_for_store` 선례(`admin/infrastructure/reservation_admin.py`) | `application/ports.py`, `infrastructure/pickup_pending.py`, container |
| D22 | 폐점 vs 할인 등록 잔여 경합 | 8절 메모 4, R13 | **확정(사용자, 2026-11-05)**: 이번 범위는 **상점 행 잠금만** 하고 잔여 경합(폐점 확인 직후 다른 트랜잭션의 `register_offer`)은 인정해 문서화. 해소안(catalog가 상점 행을 `store → product → offer` 순으로 잠금)은 catalog 변경이라 **후속으로 남김**(C12) | catalog 코드를 이번 범위에서 고치지 않기로 한 사용자 범위 | 13.6, C12 |
| D23 | 서비스 메서드 형태 | R5, R13 | `close_store(owner_id, store_id, *, commit: bool = True) -> Store`. `now`는 `self.clock.now()` 한 번 | `suspend_store` 등 기존 메서드와 같은 패턴 | `StoresApplicationService` |
| D24 | 재개점 | 사용자 범위, D6 | 이번 범위 아님. `Store.reopen`·EP 만들지 않음(D6 유지). `closed_at`·`closed_reason`을 되돌려야 하므로 후속 설계 때 `closed_reason` 처리를 정한다 | D6 | 후속 |

차단 여부: 없음. D13·D14는 확정이고, 나머지 D1~D12·D15~D24는 임시 기본값으로 구현을 진행할 수 있다. | D25 | 관리자 정지 할인과 상점주 폐점 | admin.md D22, 사용자 결정 | **확정(사용자, 2026-11-05)**: 관리자가 정지한 할인도 "진행 중"으로 계속 센다. 따라서 상점주는 그 할인의 `sales_end`가 지나거나 관리자가 상점을 강제 폐점하기 전까지 폐점할 수 없다(400 `STORE_HAS_OPEN_OFFERS`). **의도된 동작**이며 설계 변경 없음. 근거: 상점주가 폐점으로 관리자 정지를 우회하지 못하게 한다 | `DiscountOffer.is_open` 불변(catalog), `Store.close` 플래그 | 13.2 |

차단 여부 없음. 사용자 확정: D13·D14·D22·D25. 나머지 D16~D21·D23·D24·D15는 기술적 임시 기본값으로 설계대로 진행한다.

---

## 13. 상점주 폐점 `POST /v1/stores/{store_id}/close` (2026-11-05 추가)

범위: 이 EP 하나. 재개점은 후속(D24). reservations 내부는 설계하지 않고 stores 소유 포트와 미연계 임시 구현만 둔다(D21). 기준: `docs/reference/stores.md` §2, `backend-invariants` R1~R16, `docs/design/admin.md` D17·D22·C19.

### 13.0 차단 이슈 확인 (실행 결과)

| 확인 | 명령 | 결과 |
| --- | --- | --- |
| 계층 검사 기준선 | `PYTHONIOENCODING=utf-8 uv run python .claude/skills/layer-check/check_layers.py` | 검사 123개 파일, **위반 2건**(`payments\application\service.py:19`, `:20` application → payments.infrastructure, 예상한 기준선), 경고 3건(`error_handlers.py` 넓은예외, 종료 코드 무관). stores 위반 없음 |
| 현재 코드 import | `(cd src && DATABASE_URL=postgresql+asyncpg://x:x@localhost/x uv run python -c "import main")` | 성공(출력 없음, 종료 0) |
| catalog 포트 존재 | `Grep has_open_offers_for_store` | **이미 있음**: `catalog/application/service.py:333` `has_open_offers_for_store(self, store_id, *, now=None) -> bool` → `offers.exists_open_by_store(store_id, now)`(`catalog/infrastructure/repositories.py:186`, 추상 `discount_offer_repository.py:23`). catalog 변경 불필요 |
| 정지 할인 포함 | `catalog/domain/discount_offer.py:194` `is_open = is_active and now < sales_end` | 정지·매진·예정 할인 모두 "진행 중". 상점주는 이 할인이 `sales_end`를 넘기거나 비활성화(`deactivate_offer`)돼야 폐점 가능(admin.md D22) |
| 추가 의존성·환경변수 | 요청 본문 없음, `Form`·`File` 없음 | 없음. `pyproject.toml`·`.env.example` 변경 없음 |
| 생성 순환(R12) | 코드 읽기: `container.py:157-160` `create_store_port → create_stores_service`, `:171-189` `create_catalog_service → create_store_port`. 여기에 `create_stores_service → create_open_offers_port → create_catalog_service`를 더하면 `stores → catalog → stores` | **순환 확정**(코드 읽기 근거, 코드를 바꾸지 않았으므로 실행 재현은 하지 않음). 기본 인자 `Depends(...)`는 def 시점에 평가돼 정의 순서상 불가능하기도 하다. 해소는 13.7 |
| 정지 계정 | `auth/domain/user.py:333-334` `ensure_can_authenticate`: 정지면 `AccountSuspendedError`(403 "정지된 계정입니다.") | `ApprovedOwnerUser`는 `get_current_user`(allow_suspended 아님)를 거치므로 정지된 상점주 계정은 폐점 403 |

### 13.1 도메인 (domain/)

**exceptions.py** — 신규 1개, 재사용 3개.

| 클래스 | 상속 | 응답 | 메시지(기본) | 비고 |
| --- | --- | --- | --- | --- |
| `StoreHasOpenOffersError` (**신규**) | `ValueError` | 400 `STORE_HAS_OPEN_OFFERS` | "진행 중이거나 예정된 할인 판매가 있어 폐점할 수 없습니다." | 명세 문구 그대로. `error_code` 클래스 속성(기존 예외 패턴) |
| `StoreHasReservedReservationsError` (재사용) | `ValueError` | 400 `STORE_HAS_RESERVED_RESERVATIONS` | 기본 "처리되지 않은 예약이 있는 상점은 폐점할 수 없습니다."(관리자용). **상점주 폐점은 `Store.close`가 "픽업 대기 중인 예약이 있어 폐점할 수 없습니다."를 인자로 넘김** | D17. 생성자가 이미 `message`를 받는다(`exceptions.py:65`) |
| `StoreAlreadyClosedError`, `StoreSuspendedError` (재사용) | `ValueError` | 400 `STORE_ALREADY_CLOSED` / `STORE_SUSPENDED` | 기존 | 변경 없음 |
| `StoreNotFoundError`, `NotStoreOwnerError` (재사용) | `LookupError`/`PermissionError` | 404 / 403 | 403 메시지는 호출 측이 "본인 상점만 폐점할 수 있습니다."로 전달 | 변경 없음 |

**store.py** — `close`만 바꾼다. `_close`, `force_close`, `suspend` 등 admin 메서드는 건드리지 않는다.

```python
def close(
    self,
    now: datetime,
    *,
    has_open_offers: bool = False,
    has_pickup_pending: bool = False,
) -> None:
    _ensure_aware(now, "폐점 시각")
    if now is None:
        raise ValueError("폐점 시각이 필요합니다.")
    if self.is_closed:
        raise StoreAlreadyClosedError()
    if self.is_suspended:
        raise StoreSuspendedError()
    if has_open_offers:
        raise StoreHasOpenOffersError()
    if has_pickup_pending:
        raise StoreHasReservedReservationsError("픽업 대기 중인 예약이 있어 폐점할 수 없습니다.")
    self._close(now)   # 미승인 ValueError, now < approval_at ValueError, closed_at 기록 (closed_reason은 None)
```

- 검사 순서(D16): `now` 형식 → 이미 폐점 → 정지 → 진행 중 할인 → 픽업 대기 예약 → (`_close`) 미승인 → 승인 시각보다 이른 `now`. 이 순서의 앞 세 단계는 기존 코드 그대로(`store.py:153-161`)이고, 두 플래그 검사만 정지와 `_close` 사이에 들어간다.
- 미승인 + 진행 중 할인은 현실적으로 없다(catalog `ensure_can_register`가 미승인 상점의 상품·할인 등록을 막는다, `store_ref.py:72-79`). 그래서 미승인 검사를 플래그 앞으로 옮기지 않고 `_close`에 둔다.
- 플래그 이름은 `force_close(..., has_reserved_reservations)` 선례를 따른 것이다. 도메인은 flag의 출처(catalog, reservations)를 모른다(R1).
- 폐점은 `closed_at`만 기록한다. `closed_reason`은 None(관리자 폐점만 사유를 가짐). `Store` 생성자 불변식(`closed_reason`은 `closed_at`이 있어야 함, `closed_at ≥ approval_at`)은 변경 없음.

상태 전이표 갱신 (2.2절 표 대체)

| 현재 파생 상태 | 이벤트 | 결과 |
| --- | --- | --- |
| ACTIVE | `close(now)` 플래그 둘 다 False | CLOSED (`closed_at=now`) |
| ACTIVE | `close(now, has_open_offers=True)` | 불가, `StoreHasOpenOffersError` |
| ACTIVE | `close(now, has_pickup_pending=True)` (할인 플래그 False) | 불가, `StoreHasReservedReservationsError` |
| ACTIVE | 두 플래그 모두 True | 불가, **할인 쪽 예외가 먼저**(명세 표 순서) |
| SUSPENDED | `close(now)` | 불가, `StoreSuspendedError` (플래그 값과 무관) |
| CLOSED | `close(now)` | 불가, `StoreAlreadyClosedError` (정지 여부와 무관, CLOSED > SUSPENDED) |
| 미승인(`approval_at=None`) | `close(now)` | 불가, ValueError "승인되지 않은 상점은 폐점할 수 없습니다." |
| CLOSED | 재개점 | 후속(D24) |

### 13.2 에러 검사 순서 (명세 에러 표와의 대응, D16)

| 순서 | 판정 위치 | 조건 | HTTP | error_code | 메시지 |
| --- | --- | --- | --- | --- | --- |
| 1 | `get_current_principal` | 토큰 없음·무효 | 401 | (auth) | auth 문구(명세 "인증이 필요합니다."와 문구 차이는 auth 소관, stores가 바꾸지 않음) |
| 2 | `authenticate` | 정지된 상점주 **계정**(`users.status`) | 403 | `FORBIDDEN` | "정지된 계정입니다." (명세 §2 표에 없음, auth 명세 3·admin 설계) |
| 3 | `require_roles(OWNER)` | 역할이 OWNER 아님 | 403 | `FORBIDDEN` | auth 문구("상점주 권한이 필요합니다." 계열) |
| 4 | `ensure_approved_owner` | PENDING | 403 | `FORBIDDEN` | "승인 대기 중인 상점주 계정입니다." (명세 §2) |
| 4 | 〃 | REJECTED | 403 | `FORBIDDEN` | "승인이 거부된 상점주 계정입니다." (auth 기존) |
| 5 | FastAPI 경로 검증 | `store_id`가 UUID 아님 | 400 | `VALIDATION_ERROR` | `필드: 오류` |
| 6 | 서비스 `_locked_store` | 상점 없음 | 404 | `NOT_FOUND` | "상점을 찾을 수 없습니다." |
| 7 | `Store.ensure_owned_by` | 본인 상점 아님 | 403 | `FORBIDDEN` | "본인 상점만 폐점할 수 있습니다." |
| 8 | `Store.close` | 이미 폐점 | 400 | `STORE_ALREADY_CLOSED` | "이미 폐점된 상점입니다." |
| 9 | 〃 | 정지된 상점 | 400 | `STORE_SUSPENDED` | "관리자에 의해 정지된 상점입니다." |
| 10 | 〃 | 진행 중이거나 예정된 할인 | 400 | `STORE_HAS_OPEN_OFFERS` | "진행 중이거나 예정된 할인 판매가 있어 폐점할 수 없습니다." |
| 11 | 〃 | 픽업 대기 예약 | 400 | `STORE_HAS_RESERVED_RESERVATIONS` | "픽업 대기 중인 예약이 있어 폐점할 수 없습니다." |
| 12 | 〃(`_close`) | 미승인 상점 | 400 | `VALIDATION_ERROR` | "승인되지 않은 상점은 폐점할 수 없습니다." |

충돌 판정과 기본값(D16)
- 명세 표의 순서(폐점 → 할인 → 예약)와 코드의 가드(폐점 → 정지)는 서로 모순이 없다. 정지 400은 명세 표에 없는 추가 행이라 **폐점 다음, 할인 앞**에 둔다(admin.md D17 순서 보존). 대안은 "정지를 할인·예약 뒤에" 두는 것이지만, 정지된 상점의 폐점 불가는 상태 규칙이므로 상태 가드가 먼저다.
- 403(승인 대기 계정)이 404·403(본인 아님)보다 앞서는 것은 의존성이 먼저 실행되기 때문이다. 존재하지 않는 `store_id`로 호출해도 승인 대기 상점주는 403을 받는다. 개설 EP와 같은 규칙(auth D5).
- 정지된 **상점**(admin이 정지)은 소유자가 400 `STORE_SUSPENDED`를 받고, 정지된 **계정**은 2번에서 403이다. 둘은 별개다.
- 남의 상점은 403(존재 노출)이다. 명세 §2가 404와 403을 따로 두었으므로 따른다.
- **의도된 동작(D25, 확정)**: 관리자가 정지한 할인도 "진행 중"으로 세므로, 상점주는 그 할인의 `sales_end`가 지나거나 관리자가 상점을 강제 폐점하기 전까지 폐점할 수 없고 400 `STORE_HAS_OPEN_OFFERS`를 받는다(admin.md D22). 근거: 상점주가 폐점으로 관리자 정지를 우회하는 것을 막는다. 이 규칙은 바꾸지 않는다. 정지 할인을 상점주가 중단(`deactivate_offer`)할 수 있는지는 catalog 소관이며 이 설계는 의존하지 않는다.

### 13.3 인프라 (infrastructure/)

변경 없음. 필요한 메서드가 이미 있다.

- `SqlAlchemyStoreRepository.find_by_id(store_id, for_update=True)` → `with_for_update()` + `populate_existing=True`(`repositories.py:20-25`): 잠금 대기 후 최신 행으로 갱신되어, 동시 폐점의 두 번째 요청이 `closed_at`을 새로 읽는다.
- `save(store)`는 기존 행 update 시 `approval_at, closed_at, suspended_*, closed_reason`을 모두 쓴다(`:71-75`). 폐점은 `closed_at`(+ `closed_reason=None`)만 바뀐다. `flush()`까지(R5).
- 스키마 변경 없음(`stores.closed_at`, `closed_reason` 이미 존재, R14). 새 레포지토리 메서드 없음.
- 신규 인프라 파일 1개: `infrastructure/pickup_pending.py`의 `NoPickupPendingReservations`(13.4 포트의 임시 구현, 항상 `False`, 미연계).

### 13.4 응용 (application/)

**포트** — 신규 파일 `stores/application/ports.py` (쓰는 쪽 stores가 정의, R11. catalog·reservations를 import하지 않는다).

```python
class OpenOffersPort(Protocol):
    """catalog가 구조적으로 만족한다 (catalog/application/service.py:333)."""
    async def has_open_offers_for_store(
        self, store_id: uuid.UUID, *, now: datetime | None = None
    ) -> bool: ...

class PickupPendingPort(Protocol):
    """픽업 대기 중인 예약이 있는지 묻는 읽기 포트. 미연계(R16): 구현은 NoPickupPendingReservations(항상 False).
    commit하지 않는다(R13). "픽업 대기"의 상태 집합은 reservations 후속에서 정한다 (D21)."""
    async def has_pickup_pending_for_store(self, store_id: uuid.UUID) -> bool: ...
```
`now`는 키워드 전용이다(catalog.md 2.3·CI-2 확정 서명). 호출은 `now=now`.

**서비스** — `StoresApplicationService.__init__`에 필수 인자 2개 추가, 기본값 없음(R8): `open_offers: OpenOffersPort`, `pickup_pending: PickupPendingPort`. 읽기 메서드 `find_store_by_id`·`find_stores_by_ids`는 13.7의 `StoreQueryService`로 이동한다(C14).

`close_store(self, owner_id: UUID, store_id: UUID, *, commit: bool = True) -> Store` (D23)

1. `now = self.clock.now()` (한 번)
2. `store = await self._locked_store(store_id)` — `find_by_id(for_update=True)`, 없으면 `StoreNotFoundError` (404). **여기서 상점 행 잠금**
3. `store.ensure_owned_by(owner_id, "본인 상점만 폐점할 수 있습니다.")` — 403
4. `has_open = await self.open_offers.has_open_offers_for_store(store_id, now=now)`
5. `pending = await self.pickup_pending.has_pickup_pending_for_store(store_id)`
6. `store.close(now, has_open_offers=has_open, has_pickup_pending=pending)` — 도메인이 400 순서를 정함
7. `await self.stores.save(store)` → `await self._finish(commit)` → `return store`

- 서비스에 비즈니스 if-else 없음(R3). 4·5는 조회만 하고 서비스가 판단하지 않는다.
- 이미 폐점·정지 상점도 4·5를 조회한 뒤 6에서 예외가 난다(불필요 조회 2회). 단순성을 위해 허용하며, 성능이 문제가 되면 후속에 `Store.ensure_closable()`을 분리한다.
- 예외가 나면 `save`·`commit`에 도달하지 않는다. 도메인 객체의 메모리 변경은 6에서 예외가 나므로 일어나지 않는다. 세션은 요청이 끝날 때 닫혀 잠금이 풀린다.
- R13: `commit=False`는 이 메서드를 다른 서비스가 같은 세션에서 부를 때를 위한 키워드이며 이번 EP는 기본값(True)으로 호출한다. 다른 모듈의 쓰기는 호출하지 않는다(catalog·reservations 호출은 읽기 포트뿐이라 트랜잭션 경계는 stores 한 곳이다).
- 트랜잭션 경계: 단일 트랜잭션 `BEGIN → (store FOR UPDATE) → SELECT offers(비잠금) → UPDATE stores → COMMIT`. 같은 요청 세션을 공유하므로 catalog·stores가 한 트랜잭션에서 읽는다(R13).

### 13.5 표현 (presentation/)

| Method | URI | 요청 | 응답 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- |
| POST | `/v1/stores/{store_id}/close` | 없음 (경로 `store_id: UUID`) | `StoreCloseResponse` | 200 | 400(이미 폐점·정지·진행 중 할인·픽업 대기 예약·UUID 형식 오류), 401, 403(승인 대기·역할·본인 상점 아님·정지 계정), 404 |

- 인증: `ApprovedOwnerUser`(D19). 개설 EP(`router.py:22`)와 같다. `OwnerUser`만 쓰면 승인 대기 상점주가 404·403(본인 아님)을 받아 명세 §2의 403 "승인 대기 중인 상점주 계정입니다."를 어긴다. 정지된 상점주 계정은 403, `SuspendedAllowedOwnerUser`는 픽업 전용이라 쓰지 않는다.
- 스키마(`schemas.py`에 추가, D20): `StoreCloseResponse(from_attributes=True)` — `id: UUID`, `name: str`, `closed_at: datetime`(명세는 null 아님). `closed_at`은 서비스가 항상 값을 채우므로 `datetime`(비 Optional). 기존 `StoreResponse`는 재사용하지 않는다(필드 과다·`closed_at` nullable).
- router: `service.close_store(owner.id, store_id, ...)`만 호출하고 예외를 잡지 않는다(R6, R7). `tags=["상점"]`, `summary="상점 폐점"`, `status_code=200`.
- 목록·쿼리 매개변수 없음.

### 13.6 동시성과 잠금 순서

| 대상 | 잠금 | 근거 |
| --- | --- | --- |
| `stores` 행 | `SELECT ... FOR UPDATE` (`find_by_id(for_update=True)`) — **필요** | 같은 상점에 대한 동시 폐점·관리자 정지·관리자 폐점을 직렬화 |
| `discount_offers` | 잠금 없음(`exists_open_by_store`는 일반 SELECT) | 존재 확인만 하므로 행 잠금 불필요 |
| `users` | 잠금 없음(`authenticate`는 `for_update` 없음. `auth/application/service.py`에서 `for_update=True`는 `:182` 한 곳뿐, 탈퇴 경로) | 폐점은 사용자 행을 바꾸지 않음 |

전역 잠금 순서(기존 합의): `store → user`(admin.md D34 "상점 먼저") 그리고 `store → product → offer`(admin `close_store`: `check_force_closable` 상점 잠금 → `end_all_sales_of_store`의 상품 → 할인). 상점주 폐점은 **상점 행 하나만** 잠그고 아무것도 더 잠그지 않으므로 이 순서를 역행하지 않는다.

교착 분석
- 폐점 ↔ 폐점(같은 상점): 두 번째 요청이 `FOR UPDATE`에서 대기하다 첫 커밋 뒤 `populate_existing`으로 새 행을 읽고 `StoreAlreadyClosedError`(400). 교착 없음.
- 폐점 ↔ 관리자 `suspend_store`/`close_store_by_admin`/`suspend_stores_of_owner`: 모두 상점 행을 가장 먼저 잠근다. 직렬화되고 결과는 먼저 커밋한 쪽이 이긴다. 정지가 먼저면 상점주 400 `STORE_SUSPENDED`, 관리자 폐점이 먼저면 400 `STORE_ALREADY_CLOSED`, 상점주 폐점이 먼저면 관리자는 `StoreAlreadyClosedError`. 교착 없음.
- 폐점 ↔ catalog `register_offer`/`deactivate_offer`/`end_all_sales`: catalog는 상품 → 할인 순이고 상점 행은 잠금 없이 읽는다(PostgreSQL MVCC라 `FOR UPDATE`가 읽기를 막지 않음). 서로 상대의 잠금을 기다리지 않으므로 교착 없음.
- 폐점 ↔ 탈퇴·정지(auth): 폐점은 `users`를 잠그지 않는다. admin이 `store → user` 순이므로 역행 없음.
- 격리 수준: `database.py`에 격리 수준 설정 없음 → PostgreSQL 기본 READ COMMITTED(**확인 필요**: 설정 파일이 아닌 기본값에 의존).

**잔여 경합(D22, C12)**: 폐점 트랜잭션 T1이 `exists_open_by_store`로 "없음"을 확인한 뒤 커밋 전에, 다른 트랜잭션 T2의 `register_offer`가 상점을 비잠금 읽기(아직 `closed_at` 없음)로 통과해 할인을 삽입·커밋하면 폐점된 상점에 진행 중 할인이 남는다. 발생 창은 T1의 확인~커밋 사이로 짧다. 이번 범위(stores만)에서는 막지 못하고 인정한다. 해소는 catalog 변경(C12: 상점 행 잠금 → 상품 행 잠금 순서)이며 **역순(상품 → 상점 잠금)은 admin 폐점과 교착하므로 금지**. D22는 사용자가 확정했다: 이번에는 catalog를 바꾸지 않고 후속으로 남긴다.
- reservations 후속 요구: 예약 생성이 상점 상태를 확인한다면 같은 순서(상점 → 상품 → 할인)를 지키고, 같은 잔여 경합(폐점 확인 직후 신규 예약)을 `has_pickup_pending_for_store` 구현 때 함께 다룬다(후속, reservations 담당).

### 13.7 조립 — 생성 순환 해소와 container 코드 (R9, R12, D15)

**방식(D15)**: 읽기 전용 `StoreQueryService`를 stores에 분리한다. catalog·reservations가 쓰는 `StorePort`는 이 서비스가 만족하고, 상점주 폐점을 가진 `StoresApplicationService`는 catalog를 `open_offers`로 받는다.

- 신규 `stores/application/query_service.py`: `StoreQueryService(stores: StoreRepository)` — `find_store_by_id`, `find_stores_by_ids`(현 `service.py:19-23`을 이동, 동작 동일). 세션·`Clock` 불필요, 커밋 없음.
- 의존 그래프: `get_db → create_store_repository → create_store_query_service → create_store_port → create_catalog_service → create_open_offers_port → create_stores_service → create_admin_service`. 역방향 간선 없음(R12). `create_stores_service`의 소비자는 router(`provide_stores_service` 매핑)와 `create_admin_service`(`container.py:246`)이고, `create_store_port`의 소비자는 `create_catalog_service`·`create_stock_port`(reservations, `container.py:173,200`)라 모두 `StoreQueryService`만 필요로 한다.
- 한 요청 안에서 FastAPI가 `create_catalog_service`를 한 번만 만들어 admin·stores가 같은 catalog 서비스(같은 세션)를 쓴다.

대안 비교(채택하지 않음)

| 대안 | 내용 | 채택하지 않은 이유 |
| --- | --- | --- |
| B. 별도 `StoreClosureService` | 폐점 전용 서비스를 새로 두고 `StoresApplicationService`는 그대로 | 변경 파일은 더 적지만 한 모듈에 서비스가 둘(상점주 명령용·관리자 연계용)이고 재개점이 생기면 또 어디에 둘지 모호. 사용자 미확정 D15와 catalog.md D22가 이미 `StoreQueryService`를 가리킴 |
| C. 좁은 포트 어댑터 | catalog 쪽에 `has_open_offers_for_store`만 가진 객체를 따로 생성 | 객체가 별도라도 `create_catalog_service`가 `create_store_port`를 필요로 하므로 순환은 그대로 |

`src/container.py` 변경 (stores·catalog 구역, C15). **Python 기본 인자는 정의 시점에 평가되므로 아래 순서를 지킨다**: `create_store_repository`, `create_store_query_service`, `create_store_port`(catalog 구역) → `create_catalog_service` → `create_open_offers_port`, `create_pickup_pending_port`, `create_stores_service` → reservations → admin.

```python
# 상단 싱글턴 (기존 목록에 추가)
_pickup_pending: PickupPendingPort = NoPickupPendingReservations()  # 임시 (stores.md D21): reservations 후속 PR이 교체

# ── stores (읽기: catalog보다 먼저 정의) ──
def create_store_repository(session: AsyncSession = Depends(get_db)) -> StoreRepository:
    return SqlAlchemyStoreRepository(session)           # 기존


def create_store_query_service(
    stores: StoreRepository = Depends(create_store_repository),
) -> StoreQueryService:
    return StoreQueryService(stores=stores)

# ── catalog ──  (기존 create_store_port 본문만 교체)
def create_store_port(
    query: StoreQueryService = Depends(create_store_query_service),
) -> StorePort:
    return query

# ... create_catalog_service 등 기존 그대로 ...

# ── stores (쓰기: catalog 뒤에 정의, R12) ──
def create_open_offers_port(
    catalog: CatalogApplicationService = Depends(create_catalog_service),
) -> OpenOffersPort:
    return catalog


def create_pickup_pending_port() -> PickupPendingPort:
    return _pickup_pending


def create_stores_service(
    session: AsyncSession = Depends(get_db),
    stores: StoreRepository = Depends(create_store_repository),
    open_offers: OpenOffersPort = Depends(create_open_offers_port),
    pickup_pending: PickupPendingPort = Depends(create_pickup_pending_port),
) -> StoresApplicationService:
    return StoresApplicationService(
        session=session, stores=stores, clock=_stores_clock,
        open_offers=open_offers, pickup_pending=pickup_pending,
    )
```
- `wire_dependencies` 매핑은 변경 없음: `provide_stores_service: create_stores_service`, `provide_store_port: create_store_port`, `provide_store_repository: create_store_repository`. 새 `provide_*`는 없다(`StoreQueryService`·두 포트는 container 내부 `Depends`로만 쓰이고 router가 직접 받지 않는다, R9 충족).
- `main.py`: 변경 없음.
- 주의: `create_stores_service`가 catalog 구역 뒤로 이동하므로 admin 구역(`create_admin_service`)이 그 뒤에 있어야 한다(현재도 마지막 구역이라 만족).
- `NoPickupPendingReservations`·`OpenOffersPort`·`PickupPendingPort`·`StoreQueryService` import를 container 상단에 추가한다.

### 13.8 테스트 계획

기존 기준선: `tests/stores/test_domain.py`, `test_service.py`(`FakeSession`·`FakeClock`·`FakeStoreRepository`), `test_api_db.py`, `test_wiring.py`, `test_admin_*.py`.

**도메인** (`tests/stores/test_domain.py`에 추가)
- 정상 폐점: 플래그 기본값 → `closed_at=now`, `closed_reason is None`, `status == CLOSED`
- `has_open_offers=True` → `StoreHasOpenOffersError`(`error_code == "STORE_HAS_OPEN_OFFERS"`, 명세 문구)
- `has_pickup_pending=True` → `StoreHasReservedReservationsError`, 메시지가 명세 문구
- 두 플래그 모두 True → 할인 예외가 먼저
- 이미 폐점이면 플래그와 무관하게 `StoreAlreadyClosedError`, 정지면 플래그와 무관하게 `StoreSuspendedError`, 정지+폐점이면 `StoreAlreadyClosedError`
- 예외가 난 모든 경우 `closed_at`이 None으로 유지됨
- 기존 `close(now)` 호출·naive `now` 거부·미승인·`now < approval_at` 테스트는 그대로 통과해야 함

**서비스** (`tests/stores/test_service.py` 갱신 + 추가). fake: `FakeOpenOffers`(`has_open_offers_for_store(store_id, *, now=None)`가 반환값·호출 인자 기록), `FakePickupPending`. 생성 호출 3인자 → 5인자로 수정(C14).
- 성공: 커밋 1회, `store.closed_at == FIXED`, `FakeStoreRepository.save` 1회, `find_by_id`가 `for_update=True`로 불림(fake가 인자 기록)
- 없음 → `StoreNotFoundError`, 커밋 0
- 남의 상점 → `NotStoreOwnerError`(메시지 "본인 상점만 폐점할 수 있습니다."), **포트 호출 0회**(권한이 조회보다 먼저)
- 진행 중 할인 → `StoreHasOpenOffersError`, 커밋 0·save 0. `now=FIXED`가 키워드로 전달됨
- 예약 대기 → `StoreHasReservedReservationsError`
- 이미 폐점 → `StoreAlreadyClosedError`, 정지 상점 → `StoreSuspendedError`(할인 플래그가 True여도 정지 쪽이 이김, D16)
- `commit=False` → 커밋 0회, 상점은 CLOSED(호출자가 커밋)
- 서비스가 두 플래그를 항상 명시해 `Store.close`에 넘기는지(D18): fake 포트 반환값이 그대로 반영되는 위 케이스들로 고정
- `StoreQueryService`: `find_store_by_id` 없음 → None, `find_stores_by_ids` 빈 입력·누락 ID(기존 서비스 테스트를 이동)

**API/DB** (`tests/stores/test_api_db.py`, `@pytest.mark.db`; `token_for`·`approve_owner`·`bearer` 헬퍼 사용). 아래 케이스는 응답 본문이 `{"success": false, "error_code", "message"}` 형식인지(R7)도 확인.
- 200: 개설 → `POST /v1/stores/{id}/close` → 본문 `id, name, closed_at`만(키 집합 비교), `closed_at` tz-aware, DB에서 `closed_at` 저장 확인
- 401: 토큰 없음, `WWW-Authenticate: Bearer`
- 403: CUSTOMER 토큰(`FORBIDDEN`), 승인 대기 OWNER(`approve_owner` 안 함, "승인 대기 중인 상점주 계정입니다."), **다른 OWNER의 상점**("본인 상점만 폐점할 수 있습니다."), 정지된 상점주 계정("정지된 계정입니다.")
- 404: 없는 `store_id`
- 400: 잘못된 UUID 경로값(`VALIDATION_ERROR`), 이미 폐점(두 번째 호출 `STORE_ALREADY_CLOSED`), 정지된 상점(`StoreModel.suspended_*` 직접 UPDATE → `STORE_SUSPENDED`), 진행 중 할인(catalog 모델·서비스로 상품·할인 삽입 후 → `STORE_HAS_OPEN_OFFERS`, 상점 `closed_at`이 여전히 NULL), 정지된 할인도 진행 중으로 센다(`DiscountOfferModel.suspended_*` 직접 설정 후 400, admin.md D22), 마감 지난 할인·`is_active=False`는 통과해 200
- 예약 대기 400: 미연계(`NoPickupPendingReservations`)라 API로 재현 불가. `app.dependency_overrides[create_pickup_pending_port]`로 항상 True인 fake를 주입해 400 `STORE_HAS_RESERVED_RESERVATIONS`를 확인하고 override를 정리(finally)
- 동시성(`asyncio.gather`, catalog `test_api_db.py:449` 패턴, `client.session_factory` 사용): 같은 상점 폐점 2건 동시 → 정확히 하나 200, 하나 400 `STORE_ALREADY_CLOSED`, DB `closed_at` 한 번만 기록. 폐점 ↔ 관리자 정지 동시(admin 라우트가 같은 앱에 있을 때) → 결과는 (폐점 200, 정지 400) 또는 (정지 200, 폐점 400)이고 `closed_at`과 `suspended_at`이 **둘 다 값을 갖지 않는다**
- 잔여 경합(C12)은 테스트하지 않는다(재현 불가·범위 밖). 테스트 주석에 후속임을 남긴다

**조립** (`tests/stores/test_wiring.py` 갱신): 기존 `test_all_provides_are_wired`는 그대로 통과. 추가: `create_store_port`가 `StoreQueryService`를 돌려주는지, `import main` 성공(R12), `create_stores_service`가 `create_catalog_service`와 같은 요청에서 같은 인스턴스를 받는 의존 그래프 구성(FastAPI `dependency_overrides` 없이 `get_dependant`로 순환 없음 확인하거나 간단히 `import main` 성공으로 갈음)

### 13.9 구현 파일 목록 (layer-implementer, 모듈별)

| 모듈 | 파일 | 변경 |
| --- | --- | --- |
| stores | `src/stores/domain/exceptions.py` | `StoreHasOpenOffersError` 추가 |
| stores | `src/stores/domain/store.py` | `close(now, *, has_open_offers=False, has_pickup_pending=False)`, import에 새 예외 추가 |
| stores | `src/stores/application/ports.py` | **신규** `OpenOffersPort`, `PickupPendingPort` |
| stores | `src/stores/application/query_service.py` | **신규** `StoreQueryService`(읽기 2메서드 이동) |
| stores | `src/stores/application/service.py` | 생성자 인자 2개 추가, `close_store` 추가, `find_store_by_id`·`find_stores_by_ids` 제거(QueryService로 이동) |
| stores | `src/stores/infrastructure/pickup_pending.py` | **신규** `NoPickupPendingReservations`(항상 False, 미연계 주석) |
| stores | `src/stores/presentation/schemas.py` | `StoreCloseResponse` 추가 |
| stores | `src/stores/presentation/router.py` | `POST /stores/{store_id}/close` 추가(`ApprovedOwnerUser`) |
| stores | `tests/stores/test_domain.py`, `test_service.py`, `test_api_db.py`, `test_wiring.py` | 13.8대로 추가·수정. `test_admin_service.py` 등 `StoresApplicationService`를 3인자로 만드는 테스트가 있으면 5인자로 수정 (확인 필요: `test_admin_service.py`의 생성 방식은 읽지 않았다) |
| container/main | `src/container.py` | 13.7대로 stores 팩토리 재배치, `create_store_port` 본문 교체, `_pickup_pending`·`create_open_offers_port`·`create_pickup_pending_port`·`create_stores_service` 변경. **catalog 구역의 `create_store_port` 한 함수를 건드리므로 오케스트레이터 승인 필요(C15)** |
| container/main | `src/main.py` | 변경 없음 |
| catalog | (없음) | 포트 메서드 이미 있음. C12 잠금 보강은 사용자 결정(D22) 전까지 하지 않음 |
| admin | (없음) | `StoreAdminPort` 구조 변경 없음. `admin/application/service.py`는 건드리지 않음 |

완료 게이트(R16·§7): `python3 .claude/skills/layer-check/check_layers.py` 위반 0(단 payments 기존 2건은 이 작업 범위 밖), `(cd src && uv run python -c "import main")` 성공, `uv run pytest -rs` db skip 0.

### 13.10 후속 (이번 범위 아님)
- 재개점 `POST /v1/stores/{store_id}/reopen`(D24): `closed_at`·`closed_reason` 복원 규칙, 정지 상태와의 관계
- reservations 연계(C13, D21): `PickupPendingPort` 실제 구현으로 container 바인딩 교체, "픽업 대기" 상태 집합 정의, 신규 예약 vs 폐점 경합 처리 (reservations 담당)
- catalog 상점 행 잠금 보강(C12, D22): `store → product → offer` 순서
- 정지 할인으로 상점주 폐점이 막히는 것은 의도된 동작(D25, 확정)이라 후속 없음

---

## 14. 상점 개설 완성 `POST /v1/stores` (2026-11-05 추가)

정본: 사용자가 2026-11-05에 붙여 넣은 개설 명세(요청 `{pickup_address}`, 응답 201 `{id, owner_id, name, pickup_address, latitude: double, longitude: double, created_at, approval_at, closed_at: null}`, 에러 7종). `docs/reference/stores.md` §1과 같은 내용이다. 이번 범위는 현재 코드(상호를 이름으로 쓰고 좌표 NULL, 중복은 owner UNIQUE만)와의 차이를 메우는 것이다.

사용자 확정(2026-11-05): ① 지오코딩은 **네이버 Geocoding API(Naver Cloud Platform Maps)**, 도메인 추상 + 인프라 구현체 + container 주입, 테스트는 fake(네트워크 금지). ② **공용 auth 401/403 문구는 바꾸지 않는다**(C17).

### 14.0 차단 이슈 확인 (실행 결과)

| 확인 | 명령 | 결과 |
| --- | --- | --- |
| 계층 검사 기준선 | `PYTHONIOENCODING=utf-8 uv run python .claude/skills/layer-check/check_layers.py` | 검사 126개 파일, 위반 2건(`payments\application\service.py:19`, `:20` application → payments.infrastructure, 기존 기준선, stores 무관), 경고 3건(`error_handlers.py` 넓은예외) |
| 현재 코드 import | `(cd src && DATABASE_URL=postgresql+asyncpg://x:x@localhost/x uv run python -c "import main")` | 성공(`IMPORT_OK`). 네이버 환경변수 없이도 성공해야 하므로 설계는 import 시점에 환경변수를 강제하지 않는다(D28) |
| httpx 런타임 여부 | `pyproject.toml` 읽기 | **`httpx>=0.28.1`이 `[dependency-groups] dev`에만 있다.** `dependencies`에는 없다. `uv run python -I -c "import httpx"` → 성공(0.28.1, dev 그룹이 설치돼 있어서). `grep -rn httpx src` → 사용처 없음. 인프라 구현체가 `import httpx`를 하면 `uv sync --no-dev` 환경(배포)에서 `ModuleNotFoundError`로 서버가 시작하지 않는다. 해결: 모듈 밖 변경 제안 1번(`uv add httpx`) |
| 환경변수 | `.env.example` 읽기 | 네이버 키 없음. 추가 제안은 14.10 |
| 환경변수 읽는 방식 | `src/auth/infrastructure/settings.py` 읽기 | `load_dotenv()` + `os.getenv`, 오류는 `RuntimeError`. auth의 JWT는 lifespan에서 fail-fast(`main.py:52`). 같은 패턴을 쓰되 네이버는 fail-fast하지 않는다(D28) |
| 중복 유니크 제약 | `schema.sql:51-66` 읽기 | `stores`에는 `uq_stores_owner_id`뿐, **(name, pickup_address) 유니크 없음** → 스키마 변경 제안 14.3(D33) |
| 503 핸들러 | `src/error_handlers.py` 읽기 | `ValueError`→400, `PermissionError`→403, `LookupError`→404, 409 두 개뿐. **5xx 핸들러 없음** → 잡히지 않은 예외는 공통 형식이 아닌 Starlette 기본 500이 된다(R7 위반). 해결: 모듈 밖 변경 제안 2번 |
| 기존 호출부 영향 | `Grep "v1/stores\""` tests | `tests/catalog/test_api_db.py:43`, `tests/reservations/test_api_db.py:25`, `tests/admin/test_api_db.py:145`, `tests/stores/test_admin_api_db.py:21`이 실제 배선으로 `POST /v1/stores`를 호출한다. catalog 테스트는 `o2@test.com` 두 번째 상점주를 같은 이름("홍길동", `tests/helpers.py:9`)·같은 주소("서울 강남구")로 개설한다(`test_api_db.py:101,203,235,389`). 지오코더 fake 주입과 중복 규칙 때문에 그대로는 깨진다 → C18 |
| 네이버 API 실제 응답 | (실행 불가: 인터넷·키 없음) | **확인 필요.** 14.2의 엔드포인트·헤더·필드는 가정이다(D27) |

차단 이슈(구현을 막는 것): 없음. 단 배포 전 해결 필요 1건(httpx 런타임 의존성), 사용자 확인 필요 항목은 14.11의 "확인" 열.

### 14.1 도메인 (domain/)

R1: `unicodedata`, `math`, `dataclasses`, `abc` 같은 표준 라이브러리만 쓴다.

**exceptions.py — 신규 3개**

| 클래스 | 상속 | 응답 | 메시지 | 쓰는 곳 |
| --- | --- | --- | --- | --- |
| `AddressNotFoundError` | `ValueError` | 400 `ADDRESS_NOT_FOUND` | "주소를 찾을 수 없습니다." | `Geocoder` 구현체가 검색 결과 0건일 때 |
| `StoreDuplicatedError` | `ValueError` | 400 `STORE_DUPLICATED` | "동일한 상점명과 주소의 상점이 이미 존재합니다." | `Store.ensure_can_open`, 레포지토리의 `uq_stores_name_address` 위반 변환 |
| `GeocodingUnavailableError` | `Exception` (**`ValueError` 아님**) | **503** `GEOCODING_UNAVAILABLE` | "주소 변환 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요." | 네트워크·타임아웃·업스트림 4xx/5xx·응답 형식 오류·자격증명 없음 |

`GeocodingUnavailableError`를 `ValueError`로 하면 전역 핸들러가 400으로 바꿔 "사용자 입력 오류"처럼 보이므로 `Exception`을 상속하고 핸들러를 한 줄 추가한다(409 패턴, `layer-implementation` 예외 절). 기존 `StoreAlreadyExistsError`(400 `STORE_ALREADY_EXISTS`, "이미 개설된 상점이 있습니다.")는 변경 없음.

**coordinates.py — 신규 값 객체**

| 이름 | 속성 | 규칙 |
| --- | --- | --- |
| `Coordinates` (`@dataclass(frozen=True)`) | `latitude: float`, `longitude: float` | `math.isfinite` 이고 위도 -90~90, 경도 -180~180. 아니면 `ValueError("좌표가 올바르지 않습니다.")` |

`Store.__init__`의 기존 좌표 검사는 `Coordinates(latitude, longitude)` 생성으로 대체해 규칙을 한 곳에 둔다(동작·메시지 동일, 둘 다 None 또는 둘 다 값 규칙은 유지).

**service.py — 추상 도메인 서비스 `Geocoder(ABC)` 추가 (layer-architecture §5.2, R8)**

```python
class Geocoder(ABC):
    @abstractmethod
    async def geocode(self, address: str) -> Coordinates:
        """정규화된 주소를 좌표로 바꾼다.
        결과 없음 -> AddressNotFoundError. 그 외 모든 실패(네트워크, 타임아웃, 업스트림 오류,
        응답 형식 오류, 자격증명 없음) -> GeocodingUnavailableError."""
```
`Clock`과 같은 파일에 둔다(D13의 모듈별 위치 규칙과 동일). 구현체가 도메인 예외를 낸다(인프라 → 도메인 방향이라 R2 위반 없음). 이렇게 하면 "없으면 예외" 판단이 서비스 if가 아니라 계약이 된다(R3).

**store.py 변경**

| 항목 | 변경 |
| --- | --- |
| 텍스트 정규화 (모듈 함수 `_normalize_text`) | `" ".join(unicodedata.normalize("NFC", value or "").split())` — NFC 정규화 + 앞뒤 공백 제거 + 내부 연속 공백(전각 공백 포함)을 한 칸으로. 이름·주소 모두에 쓴다 (D32) |
| `Store.normalize_address(raw) -> str` (staticmethod, 신규) | 정규화 후 비어 있으면 `ValueError("주소를 입력해 주세요.")`, 500자 초과면 `ValueError("픽업 주소는 500자 이하여야 합니다.")` |
| `Store.normalize_name(raw) -> str` (staticmethod, 신규) | 정규화 후 1~150자가 아니면 `ValueError("상점명은 1자 이상 150자 이하여야 합니다.")` |
| `Store.__init__` | 이름·주소를 위 두 정규화로 처리. **검사 순서를 주소 → 상점명으로 바꾼다**(명세 에러 표가 주소를 먼저 나열). 둘 다 틀린 입력일 때만 보이는 차이다 |
| `Store.ensure_can_open(*, owner_already_has_store: bool, duplicate_exists: bool)` (staticmethod, 신규) | 순서대로 `owner_already_has_store` → `StoreAlreadyExistsError`, `duplicate_exists` → `StoreDuplicatedError`. 서비스가 두 값을 조회해 넘기기만 한다(D18의 `close` 플래그 패턴, R3) |
| `Store.open(owner_id, name, pickup_address, now, coordinates: Coordinates)` | **`coordinates` 필수**(기본값 None 제거, D34). `latitude`·`longitude`는 `coordinates`에서 꺼내 생성자에 전달. `now`가 naive면 기존대로 ValueError. 개설 시각이 `approval_at` |

`Store.__init__`은 좌표를 계속 `None`으로 받을 수 있다(2.2절 규칙 유지). 이 설계 이전에 만들어진 행(C20)과 catalog·reservations 테스트의 직접 생성 때문이다. "새로 개설된 상점은 항상 좌표가 있다"는 규칙은 `open`이 책임진다.

상태 전이표: 변경 없음(`Store.open` → 영업 중, `approval_at`=개설 시각).

### 14.2 인프라 (infrastructure/)

**신규 파일**

| 파일 | 내용 |
| --- | --- |
| `infrastructure/settings.py` | `NaverGeocodingSettings`(frozen dataclass: `client_id`, `client_secret`, `url`, `timeout_seconds`)와 `get_naver_geocoding_settings() -> NaverGeocodingSettings \| None` |
| `infrastructure/geocoder.py` | `NaverGeocoder(Geocoder)` |

**환경변수** (이름은 제안, D28)

| 키 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `NAVER_MAP_CLIENT_ID` | 개설에 필요 | (없음) | NCP Maps API Gateway 키 ID |
| `NAVER_MAP_CLIENT_SECRET` | 개설에 필요 | (없음) | NCP Maps API Gateway 키. **로그·예외·응답에 넣지 않는다**(R16) |
| `NAVER_MAP_GEOCODE_URL` | 아니오 | `https://maps.apigw.ntruss.com/map-geocode/v2/geocode` | 확인 필요(D27). 도메인이 바뀌어도 코드 수정 없이 교체 |
| `NAVER_MAP_TIMEOUT_SECONDS` | 아니오 | `5` | 총 타임아웃(초). 연결은 별도로 3초 상한. 숫자가 아니거나 0 이하면 기본값을 쓰고 경고 로그 |

`get_naver_geocoding_settings()`: `load_dotenv()` 후 읽는다(auth `settings.py` 패턴). ID·키 중 하나라도 비었으면 `None`(경고 로그 1회, 값은 로그에 넣지 않음). 예외를 던지지 않는다 → `import main`이 키 없이도 성공한다.

**네이버 HTTP 호출 — 가정(확인 필요, D27)**

| 항목 | 가정한 값 | 근거 |
| --- | --- | --- |
| 메서드·URL | `GET https://maps.apigw.ntruss.com/map-geocode/v2/geocode` | 기억에 의한 값. 구 도메인 `naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode`도 존재했다. 어느 쪽이 현행인지 **확인 필요**하므로 URL은 환경변수 |
| 인증 헤더 | `x-ncp-apigw-api-key-id: {client_id}`, `x-ncp-apigw-api-key: {client_secret}` | 헤더 이름은 대소문자 무관. 구 문서는 `X-NCP-APIGW-API-KEY-ID`/`X-NCP-APIGW-API-KEY`. **확인 필요** |
| 요청 | 쿼리 `query={주소}` (필수). 그 외 파라미터 사용 안 함. 헤더 `Accept: application/json` | httpx `params={"query": address}`로 URL 인코딩 위임(문자열 연결 금지) |
| 정상 응답 | `{"status": "OK", "meta": {"totalCount": N, "page": 1, "count": N}, "addresses": [{"roadAddress", "jibunAddress", "x": "127.02...", "y": "37.49...", ...}], "errorMessage": ""}` | 사용자 지시. **`x`=경도, `y`=위도, 둘 다 문자열** |
| 결과 없음 | HTTP 200, `meta.totalCount == 0`, `addresses == []` | 사용자 지시. 확인 필요 |
| 오류 | 인증 오류·한도 초과·잘못된 요청은 HTTP 4xx(본문 형식 미확인), 서버 오류는 5xx | 확인 필요. 아래 매핑은 상태 코드만 본다 |

구현자는 실제 키가 생기면 한 번 호출해(테스트 아님, 수동) 위 가정을 확인하고 어긋난 부분만 이 표와 `NaverGeocoder`를 고친다. 로컬에서 키 없이 개발해도 fake 주입으로 모든 테스트가 통과해야 한다.

**`NaverGeocoder` 동작** (생성자: `settings: NaverGeocodingSettings | None`, `transport: httpx.AsyncBaseTransport | None = None` — 후자는 테스트가 `httpx.MockTransport`를 넣는 이음새이며 기본 구현체를 만드는 것이 아니다)

1. `settings is None` → HTTP 호출 없이 `GeocodingUnavailableError` (D28)
2. 호출마다 `async with httpx.AsyncClient(timeout=httpx.Timeout(total, connect=3.0), follow_redirects=False, transport=...)`로 `GET`. 클라이언트를 공유하지 않는다 — 개설은 드문 호출이고, 공유 클라이언트의 종료 훅이 `main.py` lifespan 수정을 요구하기 때문이다(D30)
3. `httpx.HTTPError`(타임아웃, 연결 실패 포함) → `GeocodingUnavailableError`(원인 체인 유지, 로그에는 예외 클래스 이름과 상태 코드만)
4. HTTP 상태가 200이 아님(3xx 리다이렉트, 400, 401, 403, 429, 5xx 모두) → `GeocodingUnavailableError`. 업스트림 400을 "주소 없음"으로 바꾸지 않는다: 키·요청 오류가 사용자 입력 오류로 숨는 것을 막기 위함이다(D29)
5. JSON 파싱 실패, `status`가 있고 `"OK"`가 아님, `meta.totalCount`·`addresses` 형식이 이상함 → `GeocodingUnavailableError`
6. `totalCount == 0` 또는 `addresses`가 비어 있음 → `AddressNotFoundError`
7. 여러 건이면 **첫 번째** 항목 사용(D36). `latitude=float(y)`, `longitude=float(x)`로 `Coordinates` 생성(**x/y 순서 주의**). `KeyError`/`TypeError`/`ValueError`(NaN·범위 밖 포함)는 `GeocodingUnavailableError`(업스트림 결함이지 사용자 입력 오류가 아니므로 400 `VALIDATION_ERROR`로 새면 안 된다)
8. 로그: 실패 시 `logging.getLogger(__name__).warning`으로 사유 분류(`timeout`, `http_503` 등)만. 요청 헤더·키·주소 본문은 기록하지 않는다(R16)

**models.py / repositories.py**

| 항목 | 변경 |
| --- | --- |
| `StoreModel.__table_args__` | `UniqueConstraint("name", "pickup_address", name="uq_stores_name_address")` 추가 — **스키마 변경 제안 14.3이 승인된 뒤에만**(R14, D33) |
| `StoreRepository.exists_by_name_and_address(name: str, pickup_address: str) -> bool` (추상 + 구현, 신규) | 정확 일치(`=`) 비교, `select(exists().where(...))`. **폐점·정지 상점도 포함**(D32). 호출자가 이미 정규화한 값을 넘긴다 |
| `SqlAlchemyStoreRepository.save` | 신규 insert의 `IntegrityError` 판별을 제약 이름 표로 확장: `uq_stores_owner_id` → `StoreAlreadyExistsError`, `uq_stores_name_address` → `StoreDuplicatedError`, 그 외(users FK 위반 등)는 그대로 올림. 현재 `_OWNER_UNIQUE` 상수 한 개 → 이름·예외 매핑 한 곳으로 정리 |

`save`는 좌표를 이미 insert하고 있다(`repositories.py:50-51`). 변경 없음. 개설 후 이름·주소·좌표는 update하지 않는 규칙(D10 후반)도 그대로다. `find_*`·`_to_domain` 변경 없음.

### 14.3 스키마 변경 (R14, **사용자 승인 완료 2026-11-05**, D33) — 아래 "승인되지 않으면(대안)"은 폐기, `models.py` 제약은 바로 구현한다

`stores`에 이름 있는 유니크 제약 추가:

```sql
CONSTRAINT uq_stores_name_address UNIQUE (name, pickup_address)
```

- 이유: 앱의 사전 확인(`exists_by_name_and_address`)은 동시 두 요청을 막지 못한다(14.7). 유일한 확정적 방어선은 DB 제약이다.
- 승인 시 함께 고칠 것(R14): `.claude/skills/db-schema/schema.sql`의 stores 정의, `.claude/skills/db-schema/SKILL.md` 2절 관계 목록(`stores` 행 비고), `src/stores/infrastructure/models.py`. `docs/reference/stores.md` §1 확인 필요 항목도 갱신.
- 인덱스 크기: `name`(≤150자)+`pickup_address`(≤500자)를 UTF-8 3바이트로 보면 최대 약 1,950바이트로 PostgreSQL btree 행 상한(약 2,700바이트) 안이다. 4바이트 문자(이모지)만 650자 채우면 2,600바이트로 한계에 가깝다 — 그런 값은 도메인 길이 검사로 사실상 나오지 않지만 구현자가 `DataError`가 새는지 DB 테스트 1개로 확인한다(경계값 `"가"*500`).
- 이미 만들어진 개발 DB: `create_all`은 기존 테이블에 제약을 더하지 않는다. 다시 만들거나 아래를 실행한다(마이그레이션 도구 없음).
  ```sql
  SELECT name, pickup_address, count(*) FROM stores GROUP BY 1, 2 HAVING count(*) > 1;  -- 먼저 0건 확인
  ALTER TABLE stores ADD CONSTRAINT uq_stores_name_address UNIQUE (name, pickup_address);
  ```
- **승인되지 않으면(대안)**: 제약 없이 앱 확인만 둔다. 동시 요청으로 같은 이름·주소가 둘 생길 수 있음을 인정하고 문서화한다(발생 조건: 서로 다른 상점주 둘이 같은 상호·같은 주소로 거의 동시에 개설). `StoreModel`·`save` 변환 코드는 제약이 없으면 동작하지 않을 뿐 해가 없다. 이 경우 14.7 동시성 테스트와 DB 중복 테스트를 건너뛰지 말고 "인정한 경합"으로 문서화한 테스트 주석을 남긴다.

### 14.4 응용 (application/)

생성자에 필수 인자 1개 추가(기본값 없음, R8): `geocoder: Geocoder`.

```python
class StoresApplicationService:
    def __init__(self, session, stores, clock, open_offers, pickup_pending, geocoder: Geocoder): ...
```

**`open_store(owner_id: UUID, owner_name: str | None, pickup_address: str) -> Store`** (시그니처 유지)

| 단계 | 호출 | 실패 시 | 비고 |
| --- | --- | --- | --- |
| 1 | `address = Store.normalize_address(pickup_address)` | 400 "주소를 입력해 주세요." / 500자 초과 | 외부 호출 전 입력 검증 |
| 2 | `name = Store.normalize_name(owner_name)` | 400 "상점명은 1자 이상 150자 이하여야 합니다." (D37) | 상호 없는 상점주 |
| 3 | `has_store = await stores.find_by_owner_id(owner_id) is not None`, `duplicate = await stores.exists_by_name_and_address(name, address)` | | 조회만(`for_update` 없음) |
| 4 | `Store.ensure_can_open(owner_already_has_store=has_store, duplicate_exists=duplicate)` | 400 `STORE_ALREADY_EXISTS` → 400 `STORE_DUPLICATED` 순 | 서비스에 if 없음(R3) |
| 5 | `coordinates = await geocoder.geocode(address)` | 400 `ADDRESS_NOT_FOUND` / 503 `GEOCODING_UNAVAILABLE` | **외부 호출은 여기 한 번** |
| 6 | `now = clock.now()`; `store = Store.open(owner_id, name, address, now, coordinates)` | | 개설 시각 = 지오코딩 직후(호출에 걸린 시간이 `approval_at`에 앞서 섞이지 않게 `now`는 5 뒤에 읽는다) |
| 7 | `await stores.save(store)` | 동시 요청이면 레포지토리가 400 `STORE_ALREADY_EXISTS` 또는 `STORE_DUPLICATED`로 변환 | 쓰기는 이 한 줄뿐 |
| 8 | `await session.commit()` → `return store` | | 커밋 한 번(R5) |

**순서의 이유 (검증 → 중복 확인 → 지오코딩 → 쓰기)**
- 지오코딩은 느리고(최대 5초), 외부 한도(쿼터)를 쓰고, 실패할 수 있다. 어차피 거절될 요청(주소 공백, 이미 개설, 중복)에는 호출하지 않는다. 중복 확인이 로컬 쿼리 둘이라 값이 싸다.
- 쓰기(`save`)와 `commit`은 지오코딩 뒤에 둔다. 외부 호출 동안 **행 잠금도 쓰기 트랜잭션도 없다**: 3의 두 쿼리는 일반 SELECT라 행 잠금이 없고(`with_for_update()` 없음), 5가 실패하면 쓸 것이 없어 롤백할 것도 없다.
- 남는 비용: 요청 세션이 인증 의존성의 `users` 조회부터 열린 트랜잭션이라 최대 5초 동안 풀 연결 하나를 쥔다(행 잠금은 아님). 개설은 상점주당 사실상 한 번이라 허용한다. 풀 고갈이 관측되면 후속으로 5 앞에서 세션을 반납하는 구조를 검토한다(이번 범위 아님).
- 지오코딩 실패 시 사용자가 재시도하면 4가 다시 돈다 — 중복 확인 쿼리 두 개 비용뿐이다.

트랜잭션 경계: 단일 트랜잭션, 다른 모듈의 쓰기 없음(R13 해당 없음). `catalog`·`auth`를 호출하지 않는다(서비스는 `owner_id`, `owner_name` 원시 값만 받는다, 4.2절 유지).

### 14.5 표현 (presentation/)

| Method | URI | 요청 | 응답 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- |
| POST | `/v1/stores` | `StoreOpenRequest` (`pickup_address: str`, `max_length=500`, 필수) | `StoreResponse` | 201 | 400(주소 없음·길이·상호 없음·주소 못 찾음·이미 개설·중복), 401, 403(승인 대기·역할·정지 계정), **503**(지오코딩 불가, 명세에 없음, D29) |

- 인증: `ApprovedOwnerUser` 그대로(`router.py:27`). 변경 없음. router는 `service.open_store(owner.id, owner.name, body.pickup_address)`만 호출하고 예외를 잡지 않는다(R6, R7).
- `StoreResponse`: `latitude: float`, `longitude: float`로 **None 불가**로 바꾼다(명세 double). 이 스키마는 개설 응답에만 쓰인다(`schemas.py:21-31`, 폐점은 `StoreCloseResponse`). `closed_at: datetime | None`(개설 시 null), `approval_at`은 명세상 값이 있으므로 `datetime`(None 불가)로 좁혀도 되지만 변경하지 않아도 응답은 같다(임시 유지).
- 응답 예시: `{"id": "...", "owner_id": "...", "name": "마감베이커리", "pickup_address": "서울특별시 강남구 테헤란로 123", "latitude": 37.4979, "longitude": 127.0276, "created_at": "...", "approval_at": "...", "closed_at": null}`. 비밀·내부 정보 없음(R15).
- 응답의 `pickup_address`는 **정규화한 사용자 입력**이다(D35). 네이버의 도로명 주소로 바꿔 저장하지 않는다.

**에러 검사 순서**

| 순서 | 판정 위치 | 조건 | HTTP | error_code | 메시지 |
| --- | --- | --- | --- | --- | --- |
| 0 | FastAPI 본문 파싱 | JSON 문법 오류 | 400 | `VALIDATION_ERROR` | `필드: 오류`(FastAPI는 본문을 의존성보다 먼저 읽는다. **확인 필요**: 구현자가 테스트로 확정) |
| 1 | `get_current_principal` | 토큰 없음·무효 | 401 | (auth) | "로그인이 필요합니다." (C17) |
| 2 | `authenticate` | 정지된 상점주 계정 | 403 | `FORBIDDEN` | "정지된 계정입니다." |
| 3 | `require_roles(OWNER)` | OWNER 아님 | 403 | `FORBIDDEN` | "접근 권한이 없습니다." (C17) |
| 4 | `ensure_approved_owner` | PENDING | 403 | `FORBIDDEN` | "승인 대기 중인 상점주 계정입니다." (명세와 일치) |
| 4 | 〃 | REJECTED | 403 | `FORBIDDEN` | "승인이 거부된 상점주 계정입니다." (auth 기존) |
| 5 | Pydantic | `pickup_address` 없음·null·501자 이상 | 400 | `VALIDATION_ERROR` | `pickup_address: ...` (C21) |
| 6 | `Store.normalize_address` | 공백뿐 / 정규화 후 500자 초과 | 400 | `VALIDATION_ERROR` | "주소를 입력해 주세요." / "픽업 주소는 500자 이하여야 합니다." |
| 7 | `Store.normalize_name` | 상점주 `name` 없음·150자 초과 | 400 | `VALIDATION_ERROR` | "상점명은 1자 이상 150자 이하여야 합니다." (D37) |
| 8 | `Store.ensure_can_open` | 이미 상점이 있음(폐점·정지 포함) | 400 | `STORE_ALREADY_EXISTS` | "이미 개설된 상점이 있습니다." |
| 9 | 〃 | 같은 상점명·주소가 이미 있음 | 400 | `STORE_DUPLICATED` | "동일한 상점명과 주소의 상점이 이미 존재합니다." |
| 10 | `Geocoder.geocode` | 결과 0건 | 400 | `ADDRESS_NOT_FOUND` | "주소를 찾을 수 없습니다." |
| 10 | 〃 | 호출 실패 | 503 | `GEOCODING_UNAVAILABLE` | "주소 변환 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요." |
| 11 | `save` (경합) | 동시 요청이 8 또는 9를 통과 | 400 | `STORE_ALREADY_EXISTS` / `STORE_DUPLICATED` | 위와 같음 |

**명세 에러 표와의 차이(D40)**: 명세 표는 "주소를 찾을 수 없습니다"를 "이미 개설된 상점이 있습니다" 앞에 나열한다. 이 설계는 지오코딩(외부 호출)을 중복 확인 **뒤에** 둔다(14.4). 관찰되는 차이는 "주소도 못 찾고 이미 상점도 있는" 요청이 "이미 개설된 상점이 있습니다."를 받는다는 것 하나다. 두 코드 모두 400이다.

### 14.6 조립 — `src/container.py` (stores 구역)

```python
from stores.domain.service import Geocoder
from stores.infrastructure.geocoder import NaverGeocoder
from stores.infrastructure.settings import get_naver_geocoding_settings

# 상태 없는 싱글턴. 키가 없어도 import는 성공하고, 개설 호출 때 503이 된다 (D28)
_geocoder: Geocoder = NaverGeocoder(get_naver_geocoding_settings())


def create_geocoder() -> Geocoder:
    return _geocoder


def create_stores_service(
    session: AsyncSession = Depends(get_db),
    stores: StoreRepository = Depends(create_store_repository),
    open_offers: OpenOffersPort = Depends(create_open_offers_port),
    pickup_pending: PickupPendingPort = Depends(create_pickup_pending_port),
    geocoder: Geocoder = Depends(create_geocoder),
) -> StoresApplicationService:
    return StoresApplicationService(
        session=session, stores=stores, clock=_stores_clock,
        open_offers=open_offers, pickup_pending=pickup_pending, geocoder=geocoder,
    )
```

- `create_geocoder`는 `provide_*`가 아니다(router가 직접 받지 않는다). `create_pickup_pending_port`와 같은 취급이라 `wire_dependencies` 매핑 변경은 없고 R9는 그대로 충족된다. 테스트는 `app.dependency_overrides[create_geocoder]`로 바꾼다.
- 의존 그래프: `create_geocoder`는 다른 팩토리에 의존하지 않는 잎이라 순환이 생기지 않는다(R12). `create_admin_service`가 `create_stores_service`를 받으므로 admin 요청도 `create_geocoder`를 거치지만 호출은 `open_store`에서만 일어난다.
- 상단 싱글턴 구역 주석: `# 네이버 지오코딩: NAVER_MAP_* 환경변수가 없으면 개설이 503 (stores.md D28)`.
- `main.py` 변경 없음(lifespan에 fail-fast를 넣지 않는다, D28). `import main`은 키 없이 성공해야 한다.

### 14.7 동시성

| 경합 | 대응 |
| --- | --- |
| 같은 상점주의 두 요청 | 사전 확인 통과 후 둘 다 insert → `uq_stores_owner_id` 위반이 400으로 변환. 같은 상점주가 같은 주소로 보내면 `uq_stores_name_address`가 먼저 걸릴 수 있어 둘 중 어느 코드든 400(테스트는 집합으로 판정) |
| 서로 다른 상점주가 같은 상호·주소 | 14.3 제약이 있으면 둘 중 하나가 400 `STORE_DUPLICATED`. 제약이 없으면(승인 안 됨) 둘 다 성공한다(인정한 경합) |
| 잠금 | 행 잠금(`with_for_update`) 필요 없음: 대상 행이 아직 없는 insert 경합이라 `FOR UPDATE`로 직렬화할 행이 없다. advisory lock(`pg_advisory_xact_lock`)도 쓰지 않는다 — 제약이 방어선이다 |
| 지오코딩과 잠금 | 외부 호출 중 보유한 DB 행 잠금 없음(14.4) |
| `populate_existing`/잠금 순서 | 개설은 `users`·다른 `stores` 행을 잠그지 않아 13.6의 `store → user` 순서와 충돌하지 않는다 |

격리 수준: 13.6과 같이 PostgreSQL 기본 READ COMMITTED(**확인 필요** 유지).

### 14.8 테스트 계획 (네트워크 금지, R16)

공통: 지오코더는 **fake**(`Geocoder`를 상속). 네트워크 호출 테스트 없음. `NaverGeocoder`는 `httpx.MockTransport`로만 검증한다.

**fake** — `FakeGeocoder(Geocoder)`: 호출 인자 기록(`calls`), 기본은 고정 좌표(예 `Coordinates(37.4979, 127.0276)`) 반환, 주소 문자열에 따라 결과를 바꾸는 `results: dict[str, Coordinates | Exception]` 지원. 주소가 `results`에 없으면 기본 좌표. 서비스 테스트에서 호출 순서(지오코더 vs 레포 vs 시계)를 기록할 수 있게 공유 `events` 리스트를 받는다.

**도메인** (`tests/stores/test_domain.py`)
- `_normalize_text`: NFD 입력(예 `"서울"`의 자모 분해형)이 NFC로 저장됨, 앞뒤 공백·내부 연속 공백·전각 공백 정리
- `Store.normalize_address`: 공백뿐 → "주소를 입력해 주세요.", 정규화 후 500자 경계(500 OK, 501 거부), 내부 공백 정리 후 길이 판정
- `Store.normalize_name`: None·공백 → 거부, 150 OK/151 거부
- 생성자 검사 순서: 주소·이름이 둘 다 틀리면 주소 메시지가 먼저
- `Coordinates`: 범위 경계(±90, ±180 OK, 초과 거부), `nan`·`inf` 거부, 동등성(frozen)
- `Store.open(..., coordinates)`: `latitude`·`longitude`가 좌표에서 채워지고 `approval_at == now`, naive `now` 거부, `coordinates` 인자 없으면 `TypeError`
- `Store.ensure_can_open`: (False, False) 통과, (True, False) → `StoreAlreadyExistsError`, (False, True) → `StoreDuplicatedError`, (True, True) → **`StoreAlreadyExistsError`가 먼저**
- 예외 속성: `AddressNotFoundError.error_code == "ADDRESS_NOT_FOUND"`, 메시지, `StoreDuplicatedError`, `GeocodingUnavailableError`는 `ValueError`가 아님

**서비스** (`tests/stores/test_service.py` 갱신, `FakeStoreRepository`에 `exists_by_name_and_address` 추가)
- 성공: 지오코더가 **정규화된 주소**로 정확히 1회 호출됨, 저장된 `Store`의 좌표가 fake 값, `pickup_address`가 정규화 값, `approval_at == FIXED`, 커밋 1회, `save` 1회
- 호출 순서(events): `find_by_owner_id`/`exists_by_name_and_address` → `geocode` → `clock.now` → `save` → `commit`
- 주소 공백 → 400, **지오코더 호출 0회**, 조회 0회, 커밋 0회
- 상호 없음(`None`, `""`, 공백) → 400, 지오코더 0회
- 이미 상점 있음 → `StoreAlreadyExistsError`, **지오코더 0회**, 커밋 0회 (폐점된 상점도 동일)
- 같은 이름·주소 다른 상점주 → `StoreDuplicatedError`, 지오코더 0회. 정규화 차이(공백 수, NFD)가 있어도 중복으로 판정. 폐점 상점과도 중복
- 상점주 있음 + 중복 동시 → `StoreAlreadyExistsError`가 이긴다
- 주소 못 찾음(fake가 `AddressNotFoundError`) → 전파, 커밋 0, `save` 0
- 지오코더 불가(fake가 `GeocodingUnavailableError`) → 전파, 커밋 0, `save` 0
- 경합: `save`가 `StoreDuplicatedError`를 던지는 fake 레포 → 전파, 커밋 0 (기존 `race_on_save` 패턴 확장)
- 생성자: `StoresApplicationService(...)`에 `geocoder` 인자가 필수임(없으면 `TypeError`)

**인프라 단위** (`tests/stores/test_geocoder.py` 신규, DB·네트워크 없음, `@pytest.mark.db` 아님)
- 성공: `MockTransport` 응답 `{"status":"OK","meta":{"totalCount":1},"addresses":[{"x":"127.0276","y":"37.4979"}]}` → `Coordinates(latitude=37.4979, longitude=127.0276)` (**x/y 바뀜 방지 단언**)
- 요청 검증: 메서드 GET, 설정한 URL, 쿼리 `query`가 주소(한글·공백·`&`·`#` 포함해도 쿼리 값으로 온전히 인코딩됨), 헤더 `x-ncp-apigw-api-key-id`·`x-ncp-apigw-api-key`에 설정값
- 여러 건 → 첫 번째
- `totalCount == 0` / `addresses == []` → `AddressNotFoundError`
- HTTP 400, 401, 403, 429, 500, 503 → 각각 `GeocodingUnavailableError`(400이 `AddressNotFoundError`가 **아님**을 단언)
- 302 리다이렉트 → `GeocodingUnavailableError`(따라가지 않음)
- `httpx.ReadTimeout`, `httpx.ConnectError` 발생 → `GeocodingUnavailableError`
- 깨진 응답: JSON 아님, `status != "OK"`, `x` 없음, `x`가 숫자 아님, `"nan"`, 위도 91 → 전부 `GeocodingUnavailableError`(400이 아님)
- `settings=None` → `MockTransport` 핸들러가 호출되지 않은 채 `GeocodingUnavailableError`
- 비밀 유출 없음: 모든 실패 예외의 `str()`과 캡처한 로그에 `client_secret` 값이 없음
- 설정: ID·키 모두 있음 → 객체, 하나만 있음/둘 다 없음 → `None`, `NAVER_MAP_TIMEOUT_SECONDS`가 숫자 아님·0 이하 → 기본 5초, `NAVER_MAP_GEOCODE_URL` 미설정 → 기본 URL (`monkeypatch.setenv`/`delenv`, `load_dotenv`가 실제 `.env`를 덮어쓰지 않게 `monkeypatch`로 키를 명시적으로 삭제)

**DB** (`tests/stores/test_api_db.py`, `@pytest.mark.db`)
- 레포지토리: `exists_by_name_and_address` 존재/부재, 이름만 같음·주소만 같음 → False, 대소문자 다르면 False(대소문자 구분), **폐점 상점·정지 상점도 True**
- 왕복: 좌표(double precision) 저장·조회 동일, tz 유지
- `uq_stores_name_address` 위반 → `StoreDuplicatedError`로 변환, `uq_stores_owner_id` 위반 → `StoreAlreadyExistsError` 유지, users FK 위반은 변환되지 않음(기존 테스트 유지)
- 경계: 주소 500자(`"가"*500`) + 이름 150자 저장이 인덱스 크기 오류 없이 성공
- 제약 없는 상태에서 기대가 어긋나지 않게: 14.3이 승인되지 않으면 이 그룹은 "인정한 경합" 주석 테스트로 대체

**API/DB** (`client` 픽스처가 fake 지오코더를 주입, C18)
- 201: 본문 키 집합이 정확히 `{id, owner_id, name, pickup_address, latitude, longitude, created_at, approval_at, closed_at}`, `latitude`·`longitude`는 `float`이고 fake 값과 같음, `name`은 가입 상호, `closed_at is None`, `approval_at`·`created_at` tz-aware, DB 행의 좌표 확인, `pickup_address`가 정규화 값(앞뒤 공백 제거)
- 400 주소 공백 → "주소를 입력해 주세요.", **DB에 행 없음**, fake 호출 0회
- 400 상호 없는 상점주(기존 `test_open_store_owner_without_name` 유지)
- 400 주소 못 찾음(fake가 `AddressNotFoundError`) → `{"success": false, "error_code": "ADDRESS_NOT_FOUND", "message": "주소를 찾을 수 없습니다."}`, DB 행 없음
- 400 이미 개설(두 번째 호출, 폐점 후에도) → `STORE_ALREADY_EXISTS`, fake 호출은 첫 번째 호출 1회뿐
- 400 중복: 상점주 둘이 같은 상호("홍길동", `signup` 헬퍼 기본값)·같은 주소 → 두 번째가 `STORE_DUPLICATED`, 메시지 "동일한 상점명과 주소의 상점이 이미 존재합니다.", fake 호출 수에 두 번째가 포함되지 않음
- 503 지오코딩 불가(fake가 `GeocodingUnavailableError`) → 상태 503, 본문 `{"success": false, "error_code": "GEOCODING_UNAVAILABLE", ...}`(R7 형식), DB 행 없음, 본문에 키·URL 없음
- 401(토큰 없음, `WWW-Authenticate: Bearer`, 본문 형식), 403(CUSTOMER → "접근 권한이 없습니다.", 승인 대기 → "승인 대기 중인 상점주 계정입니다.", 정지 계정), **401이 본문 검증 400보다 우선**(유효하지 않은 본문 + 토큰 없음 → 401, 순서 0의 확인)
- 400 검증: 본문 `{}`·501자(기존 `test_open_store_validation` 유지)
- 동시성(`asyncio.gather`, `client.session_factory`, 14.3 승인 시): 서로 다른 상점주 둘이 같은 상호·주소를 동시에 개설 → 정확히 하나 201, 하나 400 `STORE_DUPLICATED`, `stores` 행 1개. 같은 상점주 동시 두 요청 → 하나 201, 하나 400 (`STORE_ALREADY_EXISTS` 또는 `STORE_DUPLICATED`), 행 1개
- 실제 네이버 호출 테스트는 만들지 않는다(키·네트워크 필요). 수동 확인 절차는 14.2

**조립** (`tests/stores/test_wiring.py`, `tests/test_container.py`)
- `create_stores_service` 직접 호출 시 `geocoder`를 넘겨야 함(기존 `test_wiring.py:44`의 4개 위치 인자 호출을 갱신)
- `create_geocoder()`가 `Geocoder` 인스턴스(`NaverGeocoder`)를 돌려줌
- `NAVER_MAP_*` 환경변수가 없는 상태에서 `import main`(= `container` import)이 성공(R12, D28)
- `test_every_provide_function_is_wired`는 변경 없이 통과(새 `provide_*` 없음, R9)

**기존 테스트 수정 목록**: 14.9의 stores 테스트 수정 행, 모듈 밖 변경 제안 4번.

### 14.9 구현 파일 목록 (layer-implementer, 모듈별)

| 모듈 | 파일 | 변경 |
| --- | --- | --- |
| stores | `src/stores/domain/exceptions.py` | `AddressNotFoundError`, `StoreDuplicatedError`, `GeocodingUnavailableError` 추가 |
| stores | `src/stores/domain/coordinates.py` | **신규** `Coordinates` |
| stores | `src/stores/domain/service.py` | `Geocoder(ABC)` 추가 (`Clock` 유지) |
| stores | `src/stores/domain/store.py` | `_normalize_text`, `Store.normalize_address`·`normalize_name`·`ensure_can_open`, 생성자 정규화·검사 순서·`Coordinates` 사용, `Store.open(..., coordinates)` (14.1) |
| stores | `src/stores/domain/repository.py` | `exists_by_name_and_address` 추상 메서드 |
| stores | `src/stores/infrastructure/settings.py` | **신규** `NaverGeocodingSettings`, `get_naver_geocoding_settings` |
| stores | `src/stores/infrastructure/geocoder.py` | **신규** `NaverGeocoder` |
| stores | `src/stores/infrastructure/repositories.py` | `exists_by_name_and_address`, `save`의 제약 이름 → 예외 매핑 확장 |
| stores | `src/stores/infrastructure/models.py` | `uq_stores_name_address` (**14.3 승인 후**) |
| stores | `src/stores/application/service.py` | 생성자 `geocoder` 추가, `open_store`를 14.4 흐름으로 교체 |
| stores | `src/stores/presentation/schemas.py` | `StoreResponse`의 `latitude`·`longitude`를 `float`(None 불가)로 |
| stores | `src/stores/presentation/router.py` | 변경 없음 (`ApprovedOwnerUser` 유지) |
| stores | `tests/stores/test_domain.py`, `test_service.py`, `test_api_db.py`, `test_wiring.py` | 14.8대로 추가·수정. `Store.open(OWNER, "상호", "주소", NOW)` 호출부는 `coordinates` 인자를 추가: `test_domain.py:75,81,86,110,124,147` |
| stores | `tests/stores/test_admin_domain.py:22`, `test_admin_service.py:20`, `test_admin_api_db.py:36,64` | `Store.open(...)`에 `coordinates` 추가. `test_admin_api_db.py:21`(`POST /v1/stores`)은 fake 지오코더 주입 후 통과해야 함 |
| stores | `tests/stores/test_geocoder.py` | **신규** (14.8 인프라 단위) |
| stores | `tests/stores/test_service.py:65` 근처 | `StoresApplicationService(...)` 생성에 `geocoder` 추가, `FakeStoreRepository.exists_by_name_and_address` 추가 |
| container | `src/container.py` | stores 구역만: `_geocoder`, `create_geocoder`, `create_stores_service`에 인자 추가, import 3줄 (14.6). 다른 구역은 건드리지 않음 |
| container | `src/main.py` | 변경 없음 |

완료 게이트(R16·§7): `python3 .claude/skills/layer-check/check_layers.py` 위반 0(단 payments 기존 2건은 범위 밖), `(cd src && uv run python -c "import main")` 성공(**네이버 환경변수 없이**), `uv run pytest -rs` db skip 0. 모듈 밖 변경(아래)이 적용되기 전에는 다른 모듈의 `POST /v1/stores` 테스트가 깨지므로 적용 순서는 오케스트레이터가 정한다.

### 14.10 모듈 밖 변경 제안 (이 문서는 쓰지 않는다, 적용은 오케스트레이터·사용자 판단)

| # | 파일 | 변경 | 비고 |
| --- | --- | --- | --- |
| 1 | `pyproject.toml`, `uv.lock` | **`uv add httpx`**(런타임 의존성). 현재 dev 그룹에만 있음. 추가 후 dev 그룹 항목은 `uv remove --dev httpx`로 정리하거나 남겨도 무방 | R16(의존성은 `uv add`로만), **사용자 확인 필요**: `pyproject.toml`·`uv.lock`이 바뀐다 |
| 2 | `src/error_handlers.py` | `GeocodingUnavailableError` 전역 핸들러 추가: `_response(503, exc.error_code, str(exc))`. `GeocodingUnavailableError`에 클래스 속성 `error_code = "GEOCODING_UNAVAILABLE"`. 핸들러는 `Exception` 계열이라 `ValueError` 핸들러와 겹치지 않는다. import: `from stores.domain.exceptions import GeocodingUnavailableError` | R7. 없으면 503이 아니라 Starlette 기본 500(공통 형식 아님) |
| 3 | `.env.example` | 아래 4줄 추가(값은 비워 둠, R16) | |
| 4 | `tests/conftest.py`, `tests/helpers.py`, `tests/catalog/test_api_db.py`, `tests/reservations/test_api_db.py`, `tests/admin/test_api_db.py` | ① `conftest.py`의 `client` 픽스처가 `app.dependency_overrides[create_geocoder]`에 `FakeGeocoder`를 기본 주입하고 종료 시 제거, `client.geocoder`로 테스트가 조정 가능하게 한다. `FakeGeocoder`는 새 `tests/fakes.py`(또는 `helpers.py`)에 둔다. ② `tests/catalog/test_api_db.py:41` `owner_with_store`와 `tests/reservations/test_api_db.py:22` `seed_offer`가 두 번째 상점주를 같은 이름·같은 주소로 만들어 `STORE_DUPLICATED`가 되므로, 주소를 이메일로 구분(`f"서울 강남구 {email}"` 등)한다 | 소유 모듈 구현자(catalog·reservations·admin) 또는 오케스트레이터가 적용. C18 |
| 5 | `.claude/skills/db-schema/schema.sql`, `.claude/skills/db-schema/SKILL.md` | 14.3의 `uq_stores_name_address` 추가(승인 시, R14). SKILL.md 2절 관계 목록 `stores` 행에 "이름+주소 유니크" 비고 | **사용자 확인 필요**(D33) |
| 6 | `docs/reference/stores.md` | ① §1 "확인 필요" 첫 항목(주소 → 좌표 변환 방법)을 해결됨(네이버 지오코딩)으로 갱신 ② 에러 표에 503 `GEOCODING_UNAVAILABLE` 행과, 명세 400들의 `error_code`(`ADDRESS_NOT_FOUND`, `STORE_ALREADY_EXISTS`, `STORE_DUPLICATED`) 추가 ③ 401·403 행의 문구는 사용자 결정(C17)대로 두되 "공용 auth 문구" 주석 | 정본이라 이 문서에서 고치지 않음 |
| 7 | `docs/design/catalog.md` | (참고) `StoreInfo`에 좌표가 필요한 후속 #8의 전제(C1)가 이제 개설 시 좌표가 채워진다는 사실로 충족. 레거시 NULL 행(C20)은 후속 | 수정 불필요 |
| 8 | `README.md` | 환경변수 표가 있다면 `NAVER_MAP_*` 4개를 추가 | 선택 |

`.env.example` 추가분:
```
# 상점 개설 시 주소를 좌표로 바꾸는 네이버 지오코딩 (NCP Maps). 비워 두면 서버는 뜨지만
# POST /v1/stores 가 503 GEOCODING_UNAVAILABLE 로 거절됩니다.
NAVER_MAP_CLIENT_ID=
NAVER_MAP_CLIENT_SECRET=
# 선택: 엔드포인트와 타임아웃(초). 기본값은 stores 설계 14.2 참고
# NAVER_MAP_GEOCODE_URL=https://maps.apigw.ntruss.com/map-geocode/v2/geocode
# NAVER_MAP_TIMEOUT_SECONDS=5
```

### 14.11 결정 표 (D26~D40) — 임시 기본값은 확정이 아니라 제안

2026-11-05 사용자가 D28·D29·D33·D38을 확정했다. **남은 사용자 확인은 D27(네이버 엔드포인트·헤더, 오프라인 확인 불가, URL은 설정 가능) 하나뿐이다.** 나머지는 기술적 임시 기본값으로 구현을 진행한다. 코드 위치에 모아 두어 바꾸기 쉽게 한다.

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 | 코드 위치 | 확인 |
| --- | --- | --- | --- | --- | --- | --- |
| D26 | 지오코더 추상과 위치 | 사용자 확정 1, R8, layer-architecture §5.2 | `Geocoder(ABC).geocode(address) -> Coordinates`를 `stores/domain/service.py`(Clock 옆)에 두고, 구현체 `NaverGeocoder`는 infrastructure, container가 주입. 결과 없음은 `AddressNotFoundError`, 그 밖의 실패는 `GeocodingUnavailableError`로 구현체가 낸다 | 서비스 if 제거(R3), 모듈별 `Clock` 선례(D13) | `domain/service.py`, `infrastructure/geocoder.py`, container | 확정(사용자 결정의 구체화, 별도 확인 불필요) |
| D27 | 네이버 엔드포인트·헤더·응답 필드 | 사용자 확정 1, 인터넷 없음 | `GET https://maps.apigw.ntruss.com/map-geocode/v2/geocode`, 헤더 `x-ncp-apigw-api-key-id`/`x-ncp-apigw-api-key`, 쿼리 `query`, 응답 `addresses[].x`(경도)·`y`(위도) 문자열, `meta.totalCount`. **URL은 `NAVER_MAP_GEOCODE_URL`로 교체 가능** | 사용자 제공 정보 + 기억(구 도메인 `naveropenapi.apigw.ntruss.com` 존재) | `infrastructure/settings.py`, `geocoder.py` | **필요**(NCP 콘솔·공식 문서로 현행 도메인·헤더·오류 본문 확인) |
| D28 | 자격증명 없을 때 동작 | 사용자 요청 | **fail-fast하지 않는다.** 키가 없으면 서버는 정상 시작(경고 로그 1회), `POST /v1/stores`만 503 `GEOCODING_UNAVAILABLE`. 대체 구현(고정 좌표 등)으로 폴백하지 않는다. 키 이름 `NAVER_MAP_CLIENT_ID`/`NAVER_MAP_CLIENT_SECRET` | 팀원이 키 없이 auth·catalog·reservations를 개발·테스트해야 함, `import main` 게이트(R12)가 키에 의존하면 안 됨. 가짜 좌표로 상점이 저장되는 폴백은 데이터 오염(R16 정신). 대안: lifespan에서 fail-fast(JWT 선례) — 모든 개발자에게 키를 요구 | `infrastructure/settings.py`, container `_geocoder` | **확정(사용자, 2026-11-05)**: 키 없이 서버 시작(경고 로그), 개설은 503 `GEOCODING_UNAVAILABLE`. fail-fast 없음 |
| D29 | 지오코딩 실패의 HTTP 매핑 | 사용자 요청, 명세에 5xx 없음 | 0건 → 400 `ADDRESS_NOT_FOUND`. 네트워크·타임아웃·리다이렉트·업스트림 4xx/5xx·응답 형식 오류·자격증명 없음 → **503 `GEOCODING_UNAVAILABLE`**(공통 형식). 업스트림 400을 "주소 없음"으로 바꾸지 않는다 | 사용자 입력 오류(400)와 서비스 장애(5xx)를 구분, 502 대신 503은 일시적·재시도 가능을 뜻함. 모든 업스트림 실패를 한 코드로 합쳐 클라이언트 처리를 단순화 | `domain/exceptions.py`, `error_handlers.py`(모듈 밖 2번) | **확정(사용자, 2026-11-05)**: 네트워크·타임아웃·업스트림 오류·키 없음 → 503 `GEOCODING_UNAVAILABLE`, 0건 → 400 `ADDRESS_NOT_FOUND`. 명세에 없는 코드라 `docs/reference/stores.md` 추가는 14.10 6번 |
| D30 | 타임아웃·재시도·클라이언트 수명 | 사용자 요청 | 총 5초, 연결 3초, 재시도 없음, 호출마다 `httpx.AsyncClient` 생성·종료(공유 클라이언트·lifespan 종료 훅 없음), `follow_redirects=False`. 환경변수 `NAVER_MAP_TIMEOUT_SECONDS`로 조정 | 개설은 드문 쓰기 경로, 쓰기 요청은 사용자 재시도가 안전, `main.py` 수정 회피 | `infrastructure/geocoder.py`, `settings.py` | 불필요 |
| D31 | 외부 호출 위치와 트랜잭션 | 사용자 요청 | 입력 검증 → 이미 개설·중복 조회 → 지오코딩 → `Store.open` → `save` → `commit`. 지오코딩 중 행 잠금·쓰기 없음, 요청 세션의 연결 하나만 최대 5초 점유(허용) | 14.4 | `application/service.open_store` | 불필요 |
| D32 | "동일한 상점명과 주소" 정의 | 명세 에러 표, 사용자 요청 | 비교 대상은 저장될 값 그대로: `name`·`pickup_address` 둘 다 **NFC 정규화 + 앞뒤 공백 제거 + 내부 연속 공백을 한 칸으로** 한 뒤 **정확 일치(대소문자 구분)**. 대상에 **폐점·정지 상점도 포함**(소프트 삭제된 행이 남아 있고 재개점이 같은 행을 쓰기 때문). 좌표·도로명 주소 동일성은 보지 않음(표기가 다른 같은 주소는 다른 것으로 취급) | 명세 "이미 존재"에 폐점 제외 문구 없음, DB 제약과 앱 확인이 같은 규칙이어야 함, 한국어 NFD 입력(macOS) 방지. 대소문자·표기 정규화는 오탐 위험이 커서 하지 않음 | `domain/store.py`(`_normalize_text`), `repositories.exists_by_name_and_address` | 불필요(범위를 바꾸려면 D33과 함께 사용자 결정) |
| D33 | 중복의 DB 강제 | R14, 14.7 | `stores`에 `UNIQUE (name, pickup_address)` 이름 `uq_stores_name_address` **추가 제안**(스키마 변경). 앱 확인은 친절한 400과 지오코딩 호출 절감용, 확정적 방어는 제약. 승인 전에는 `models.py`·`schema.sql`을 바꾸지 않는다 | 앱 확인만으로는 동시 요청을 못 막음. 인덱스 크기 상한 안(14.3) | `models.py`, `schema.sql`, SKILL.md | **확정(사용자, 2026-11-05)**: `UNIQUE (name, pickup_address)` `uq_stores_name_address` 추가 승인. 14.3 대안은 폐기. `models.py`·`schema.sql`·SKILL.md를 함께 고친다(R14) |
| D34 | 개설 시 좌표 필수 | 명세 응답 `latitude: double`, R3 | `Store.open`의 `coordinates` 필수, `StoreResponse.latitude/longitude`는 `float`(None 불가). `Store.__init__`은 레거시 행을 위해 None 허용 유지 | 명세, 개설이 항상 좌표를 가진다는 규칙을 도메인이 책임 | `domain/store.py`, `presentation/schemas.py` | 불필요 |
| D35 | 저장·응답하는 주소 | 명세 응답 `pickup_address` | 정규화한 **사용자 입력**. 네이버가 돌려주는 `roadAddress`로 대체하지 않는다 | 명세 "주소를 좌표로 변환"만 요구, 개설 후 주소 변경 불가라 입력 보존이 안전, 중복 비교 기준이 사용자 입력과 같음 | `application/service.open_store` | 불필요 |
| D36 | 검색 결과가 여러 건일 때 | 네이버 응답 | **첫 번째** 항목 사용(네이버가 관련도순으로 정렬한다고 가정, D27 확인 항목에 포함). 모호성 때문에 거절하지 않음 | "변환 실패 시만 개설 불가"라는 명세, 복수 결과를 거절하면 합법 주소가 막힘 | `infrastructure/geocoder.py` | 불필요 |
| D37 | 상호가 없는 상점주 (D3 유지) | auth `name` 선택값 | 기존 D3 유지: 400 "상점명은 1자 이상 150자 이하여야 합니다."를 **지오코딩 전에** 판정. 가입 시 OWNER에 `name` 필수화는 auth 소관의 후속 제안 | 명세 "가입 시 등록한 상호로 자동 설정" | `Store.normalize_name` | 불필요 |
| D38 | `httpx` 런타임 의존성 | 14.0, R16 | `uv add httpx`(모듈 밖 변경 제안 1) | dev 그룹에만 있어 배포(`--no-dev`)에서 깨짐 | `pyproject.toml` | **확정(사용자, 2026-11-05)**: `uv add httpx`를 런타임 의존성으로 추가 |
| D39 | 테스트의 지오코더 주입 방식 | 사용자 확정 1 | `Geocoder` 상속 `FakeGeocoder`를 서비스 테스트에 직접 주입, API 테스트는 `app.dependency_overrides[create_geocoder]`. `NaverGeocoder`는 `httpx.MockTransport`로만 검증. 네트워크 금지 | R8(생성자 추상), 기존 `create_pickup_pending_port` override 선례(13.8) | `tests/**` | 불필요 |
| D40 | 에러 검사 순서 | 명세 에러 표 | 14.5의 표. 주소 → 상점명 → 이미 개설 → 중복 → 지오코딩 → 경합. 명세 표와의 차이는 "주소 못 찾음"이 "이미 개설" 뒤라는 것 하나(모두 400) | 외부 호출 비용·한도 절감(D31). 명세는 표를 검사 순서로 못 박지 않음 | `application/service.open_store` | 불필요 |

### 14.12 정합 이슈 (C17~C21)

| # | 위치 | 이슈 | 영향 | 제안 |
| --- | --- | --- | --- | --- |
| C17 | `docs/reference/stores.md` §1 에러 표 vs `src/auth/domain/exceptions.py:5,43`, `auth/presentation/dependencies.py:23` | 사용자 명세는 401 "인증이 필요합니다.", 403 "상점주 권한이 필요합니다."인데 공용 auth는 "로그인이 필요합니다.", "접근 권한이 없습니다."를 낸다. **사용자 확정(2026-11-05): 공용 auth 문구를 바꾸지 않는다.** 상태 코드는 일치. 403 "승인 대기 중인 상점주 계정입니다."는 일치 | 알려진 문구 차이(R15 예외 보고) | stores는 이 문구를 만들지 않는다. 테스트는 auth 현행 문구를 단언한다. `docs/reference/stores.md`는 현행 문구를 유지(14.10 6번) |
| C18 | `tests/catalog/test_api_db.py:41-45`, `tests/reservations/test_api_db.py:22-26`, `tests/admin/test_api_db.py:145`, `tests/stores/test_admin_api_db.py:21`, `tests/helpers.py:9` | 실제 배선으로 `POST /v1/stores`를 호출하는 다른 모듈 테스트가 ① 지오코더 fake 없이는 503이 되고 ② 상점주 둘이 같은 상호("홍길동")·같은 주소("서울 강남구")로 개설하면 `STORE_DUPLICATED`가 된다 | 모듈 밖 테스트 수정 없이는 해당 테스트 실패 | 14.10 4번(conftest 기본 fake 주입, 주소를 이메일로 구분). 오케스트레이터가 적용 순서 조정 |
| C19 | `docs/reference/stores.md` §1 | 명세는 `error_code`가 없고 503이 없다. "확인 필요: 주소 → 좌표 변환 방법"이 이번에 해소됨 | 문서 불일치 | 14.10 6번 |
| C20 | `stores.latitude/longitude` 기존 행 | 이 설계 이전 개설 상점은 좌표 NULL로 저장됨(D2 옛 값). 새 규칙은 신규 개설에만 적용 | catalog 후속 #8(주변 할인)은 NULL 상점을 만날 수 있음 | 이번 범위 아님. 백필(지오코딩 일회성 스크립트)·NULL 처리는 후속 |
| C21 | `StoreOpenRequest.pickup_address` 필수 필드 vs 명세 에러 "주소를 입력해 주세요." | 필드 누락·null은 Pydantic이 400 `VALIDATION_ERROR` "pickup_address: Field required"로 처리해 명세 문구가 아님. 공백뿐인 값만 명세 문구 | R15 문구 차이 | 필수 필드(명세 "필수 O") 유지, 기존 `test_open_store_validation`과 일치. 문구를 맞추려면 필드를 `str \| None = None`으로 두고 도메인이 거절(명세 필수 표기와 OpenAPI가 달라짐) — 사용자가 원할 때만 |

### 14.13 후속 (이번 범위 아님)
- 기존 좌표 NULL 상점 백필(C20), catalog 주변 할인(좌표 사용)
- 지오코딩 호출 한도·캐시, 공유 `AsyncClient`와 lifespan 종료
- 풀 연결 점유를 줄이는 세션 반납 구조(14.4)
- OWNER 가입 시 `name` 필수화(auth, D37)
- 주소 표기 정규화(도로명/지번 동일 판정)로 중복 판정 강화(D32)
