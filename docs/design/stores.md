# stores 모듈 설계안 (최소 범위)

- 대상: `src/stores` (테이블 `stores`)
- 목적: `docs/design/catalog.md` 2절(StorePort/StoreInfo, StoreRef, `find_store_by_id`, `find_stores_by_ids`, `has_open_offers_for_store`)의 선행 조건 충족
- 기준: `docs/reference/stores.md`, `.claude/skills/db-schema/schema.sql`(stores), `backend-invariants`(R1~R16), `layer-architecture`(§5 추상화, §6 조립), `layer-implementation`, 구현된 `src/auth`(DI·조립은 `layer-architecture`가 정본이며 auth의 직접 생성 방식은 따르지 않는다)
- 상태: 설계 제안. "임시 기본값"은 확정이 아니라 제안이며 마지막 절 표에 모았다. 단 D13·D14는 2026-11-03 사용자가 확정했다(표에 "확정"으로 표시).
- 이번 범위: 도메인 `Store`, `StoreModel`, 추상 레포지토리 + 구현체, 읽기 서비스 2개, **최소 개설 API 1개**(7절), `presentation/dependencies.py`, `src/container.py`의 stores 구역, `main.py` 등록. 승인·폐점·재개점 EP는 후속(8절).
- 갱신 이력: 2026-11-02 작성 → 2026-11-03 R8·R9·R12·layer-architecture §5~§7 반영(추상 레포지토리·Clock 추상, `provide_*`, container 조립, 생성 순환을 container 팩토리 그래프로 기술). 설계 범위와 D1~D12 값은 변경 없음. → 2026-11-03 사용자 확정 반영: D13(Clock은 모듈별 위치, 확정), D14(stores implementer가 `src/container.py` 골격을 먼저 생성, 확정, C9 해소), C10(auth 구역은 범위 밖), `has_open_offers_for_store(store_id, *, now=None) -> bool` 서명 통일(`now=now` 키워드 호출), D15는 catalog.md D22와 동일 결정임을 상호 참조. 그 외 설계 내용은 변경 없음.

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
- 개설 확장: `POST /v1/stores` — 지오코딩(주소→좌표, 실패 시 400), 상점명+주소 중복 400, 승인 대기 상점주 403 (stores.md #1 확인 필요 3건)
- 폐점: `POST /v1/stores/{store_id}/close` (stores.md #2) — 응답 `id, name, closed_at`
- 재개점: `POST /v1/stores/{store_id}/reopen` (명세 제안, 명세 확인 필요)
- 관리자 승인: 명세에 EP 없음. "관리자 승인"이 상점 승인인지 상점주 계정 승인인지 미정(D5). 승인 EP가 생기면 `Store.approve(now)` 사용
- 상점 단건/목록 조회: 명세에 없음

폐점 시 catalog 호출 메모:
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
- `pyproject.toml`·`error_handlers.py`·`.env.example`·`schema.sql`: 변경 없음 (스키마 변경 제안 없음. 단 `uq_stores_owner_id` 이름은 `models.py`의 이름 지정일 뿐 DDL 의미는 `schema.sql`과 같다)

---

## 12. 결정 필요 항목 (임시 기본값)

임시 기본값은 확정이 아니라 제안이다(사용자 미확정). 단 **D13·D14는 2026-11-03 사용자가 확정**했다(표에 "확정"으로 표시). 코드에서는 표의 위치에 모아 바꾸기 쉽게 한다. D1~D12는 값을 바꾸지 않았고 코드 위치만 DI 구조에 맞게 고쳤다.

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 | 코드 위치 |
| --- | --- | --- | --- | --- | --- |
| D1 | 시연용 상점 확보 방식 | 요청 4 | 최소 생성 API(`POST /v1/stores`, 7절 B안) | 시드는 회원·비밀번호 시드가 따로 필요하고 운영 흐름과 다름 | `presentation/router.py`, `application/service.open_store` |
| D2 | 주소 → 좌표 변환 | stores.md #1 확인 필요 | 변환하지 않음. `latitude`/`longitude`는 NULL | 스키마가 NULL 허용, 외부 API 미정 | `StoresApplicationService.open_store` (후속에 추상 `Geocoder`를 domain에 두고 container에서 주입) |
| D3 | 상점명 출처 / 상호 없는 상점주 | stores.md #1, auth `User.name` 선택값 | `name = user.name`(상호). 비어 있으면 400 "상점명은 1자 이상 150자 이하여야 합니다." | 명세 "가입 시 등록한 상호로 자동 설정" | `Store.open`, 라우터 인자 |
| D4 | 미승인 상점의 폐점, `closed_at` ≥ `approval_at` | 도메인 일관성 | 미승인 폐점 불가, 폐점 시각은 승인 시각 이후 | 승인 전에는 "영업 중"이 아님 | `Store.__init__`, `Store.close` |
| D5 | "관리자 승인"의 대상과 승인 EP | README 상태 값, stores.md #1 | 승인 EP 없음. 개설 시각 = `approval_at` 즉시 기록. 승인 상태 확인은 `approval_at` 유무 | 명세 "개설 시각이 `approval_at`", catalog D19와 동일 | `Store.open`, `Store.is_approved` |
| D6 | 재개점 | stores.md #2 확인 필요 | 이번에 만들지 않음. 후속에서 같은 행의 `closed_at` NULL 복원 | owner UNIQUE, 명세 | 후속 `Store.reopen()` |
| D7 | 승인 대기 상점주 403 | stores.md #1·#2, 스키마 5절 7 | 이번 범위에서 검사하지 않음 | `users`에 저장할 컬럼 없음 | 후속 (auth 협의) |
| D8 | 폐점과 할인 등록 경합 | 8절 메모 4 | 후속에서 폐점 시 상점 행 `FOR UPDATE`, catalog 쪽 잠금 방식은 별도 합의 | 현재 catalog.md 5.3은 상품 행만 잠금 | 후속 |
| D9 | 폐점 차단의 "진행 중" 정의 | stores.md #2, catalog D4 | catalog `has_open_offers_for_store` 정의(매진 포함)를 그대로 사용 | 한곳에서 정의 | catalog `DiscountOffer.is_open` |
| D10 | 상점명+주소 중복, 이름·주소 변경 | stores.md #1 | 중복 검사 안 함(스키마에 유니크 없음). 개설 후 이름·주소·좌표·owner는 `save()`에서 갱신하지 않음 | 명세 "개설 후 변경 불가" | `SqlAlchemyStoreRepository.save` |
| D11 | 상점명·주소 길이 | 스키마 | 이름 1~150자, 주소 1~500자 | `schema.sql` VARCHAR 길이, 명세 "최대 500자" | `Store` 생성자 |
| D12 | 상점주 역할 값 | auth 명세, `Role.OWNER` | `OWNER` | 이미 구현된 auth 코드 | `auth.domain.user.Role` |
| D13 | 시계 주입 형태·위치 | V1, layer-architecture §5.2 | **확정(2026-11-03, 사용자 승인)**: 추상 `Clock(ABC).now()`는 **모듈별로 둔다**. stores는 `stores/domain/service.py`에 자기 `Clock`을 두고 `SystemClock`(infrastructure)을 container 싱글턴으로 주입한다. 공용 `src/common/`은 사용하지 않는다. 기존 `Callable[[], datetime]`·기본 `datetime.now`는 폐기 | §5.2가 "시계"를 추상 도메인 서비스 예로 듦, R8. 정본(layer-architecture)에 공용 위치 규칙이 없음 | `domain/service.py`, `infrastructure/clock.py`, `container._clock` |
| D14 | `src/container.py` 최초 생성 책임 | 0절, C9 | **확정(2026-11-03, 사용자 승인)**: stores implementer가 `src/container.py` 골격(import, `wire_dependencies`, stores 구역)을 먼저 만든다. catalog는 이후 자기 구역만 추가한다. 이번 범위에 auth 구역은 넣지 않는다(C10). C9(동시 생성 경합)는 이 결정으로 해소 | orchestration §4, layer-architecture §6.2·§6.3 | `src/container.py`, `src/main.py` |
| D15 | 폐점 도입 시 팩토리 순환 해소 방식 | V4, R12 | 읽기 전용 `StoreQueryService` 분리, `create_store_port`가 이를 반환(8절 메모 3). 이번 범위에서는 분리하지 않음 (임시 기본값, 미확정) | 서비스 생성자 안 생성 금지(R12), 순환 `Depends` 불가 | 후속 `application/query_service.py`. 비고: **catalog.md D22와 동일 결정**(상호 참조, 값은 두 문서에서 함께 바꾼다) |

차단 여부: 없음. D13·D14는 확정이고, 나머지 D1~D12·D15는 임시 기본값으로 구현을 진행할 수 있다.
