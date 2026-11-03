# catalog 모듈 설계안 (1차 범위)

- 대상: `src/catalog` (products, discount_offers, stock_log)
- 기준 문서: `docs/reference/catalog.md`, `.claude/skills/db-schema/schema.sql`, `.claude/skills/backend-invariants`(R1~R16), `.claude/skills/layer-architecture`(§3.4, §5~§8), `.claude/skills/layer-implementation`
- 1차 범위 EP 9개: #1 상품 등록, #2 상점 상품 목록, #4 상품 상세, #5 상품 수정, #6 상품 노출 중단, #7 할인 등록, #9 상점 할인 목록, #13 할인 재등록, #14 재고 수동 조정
- 상태: 설계 제안. "임시 기본값"은 확정이 아니라 제안이며, 12절 표에 모았다.
- 2026-11-03 갱신: 추상 레포지토리·Clock 추상, `provide_*`와 `src/container.py` 조립 기준으로 재작성(14절에 변경 위치). EP 9개와 도메인 규칙, D1~D20 값은 바꾸지 않았다.
- 2026-11-03 2차 갱신: 사용자 확정 결정 반영 — D21 확정, B3 해결 방법 확정(구현 순서 stores → catalog), CI-1·CI-2 해소, CI-4 범위 밖 처리, D22 stores.md D15 상호 참조(14절 하단 표).
- 2026-11-03 3차 갱신: stores 구현(#6)과 auth의 container 이전(#8)이 main에 머지된 실제 코드 기준으로 재검토 — B1·B3 해소, CI-1·CI-4 재판정, `OptionalUser`·container 초안·stores 매핑 수정(14절 3차 표). EP 9개와 D1~D24 값은 바꾸지 않았다.

---

## 0. 차단 이슈

| # | 이슈 | 확인 명령·결과 | 해결 방법 |
| --- | --- | --- | --- |
| B1 | **해소(2026-11-03 3차).** `stores` 모듈이 구현되어 `StoreModel`과 읽기 메서드 2개가 있다. 남은 선행은 catalog 쪽 import 순서뿐이다. | `find src/stores -type f`로 파일 확인, `src/stores/infrastructure/models.py:13-14` `StoreModel`/`__tablename__ = "stores"`, `src/stores/application/service.py:18,21` `find_store_by_id`·`find_stores_by_ids`. `(cd src && uv run python -c "import main")` → 성공(`main ok`). | catalog `models.py`는 stores 모델 클래스를 import하지 않고 `ForeignKey("stores.id")` 문자열만 쓴다. `main.py`는 이미 auth → stores 순서로 import하므로(`src/main.py:7,15`) catalog models는 **stores 뒤**에 추가한다. 단, `src/catalog/**`는 현재 전부 0바이트(구현 전)다. |
| B2 | 스키마와 명세 불일치 (재고 사유 컬럼 없음 등) | 3절 | 4절 "스키마 변경 제안"을 팀이 승인해야 `models.py`를 확정할 수 있다. 미승인 시 임시 기본값 사용. |
| B3 | **해소(2026-11-03 3차).** `src/container.py`와 `wire_dependencies(app)` 호출이 있다. 남은 일은 catalog 구역 추가뿐이다. | `src/container.py:75-82` `wire_dependencies`(auth 1개 + stores 2개 매핑), `src/main.py:10,32` `from container import wire_dependencies` / `wire_dependencies(app)  # 라우터 등록 전에`(`include_router` 33-34행보다 앞). | catalog implementer는 container의 **catalog 구역 팩토리와 `wire_dependencies` 매핑 2개**(`provide_store_port`, `provide_catalog_service`)만 추가한다(9.2절). 골격은 만들지 않는다. 구현 순서 stores → catalog는 충족됨. |

차단 아님(확인 완료):
- `(cd src && uv run python -c "import main")` → `main ok`
- `uv run python -c "import jwt, passlib, sqlalchemy, asyncpg, pydantic"` → `pkgs ok`. 추가 의존성 없음. 요청은 전부 JSON이라 `python-multipart`도 필요 없다.
- `.env.example`: `DATABASE_URL`, `JWT_*` 있음. catalog가 새로 요구하는 환경변수 없음.
- Alembic 마이그레이션 폴더 없음(`create_all` 방식). 이미 만들어진 개발 DB는 컬럼 변경이 반영되지 않으므로, 스키마 변경 승인 시 개발 DB를 다시 만들어야 한다.
- `OwnerUser`(`Role.OWNER`)는 auth에 이미 있다. 상점주 역할 값 `OWNER`는 auth의 임시값을 그대로 쓴다.
- auth는 이미 container 방식이다: `src/auth/presentation/dependencies.py:13` `provide_auth_service`(플레이스홀더), `src/container.py:47,78`에서 `create_auth_service`로 바인딩. `get_auth_service`는 존재하지 않는다. catalog의 `OptionalUser`는 `provide_auth_service`를 쓴다(7.1, CI-4 해소).
- `src/container.py` 현재 상태: `_stores_clock`(29행)과 `SystemClock` import(stores 것, 22행)가 이미 있어 catalog 구역은 이름을 구분해야 한다(9.2).

---

## 1. 모듈 구성

```
src/catalog/
  domain/
    exceptions.py            # 예외
    store_ref.py             # StoreRef (stores에서 받은 값의 읽기 전용 복사본)
    product.py               # Product
    discount_offer.py        # DiscountOffer, OfferStatus
    stock_log.py             # StockLog
    service.py               # Clock (ABC) — 추상 도메인 서비스
    repository/
      __init__.py
      product_repository.py          # ProductRepository (ABC)
      discount_offer_repository.py   # DiscountOfferRepository (ABC)
      stock_log_repository.py        # StockLogRepository (ABC)
  infrastructure/
    models.py                # ProductModel, DiscountOfferModel, StockLogModel
    repositories.py          # SqlAlchemyProductRepository, SqlAlchemyDiscountOfferRepository, SqlAlchemyStockLogRepository
    clock.py                 # SystemClock (Clock 구현체)
  application/
    ports.py                 # StorePort (Protocol), StoreInfo (Protocol)
    views.py                 # OfferView, ProductDetailView, Page
    service.py               # CatalogApplicationService
  presentation/
    dependencies.py          # provide_catalog_service, provide_store_port, OptionalUser
    schemas.py
    router.py
```

- 레포지토리는 애그리거트 루트(Product, DiscountOffer, StockLog)마다 하나라서 `domain/repository/<애그리거트>_repository.py`로 나눈다(layer-architecture §5.1, 결정 D24). 구현체 이름은 `SqlAlchemy<추상명>`(§5.3).
- `Clock`은 시계라는 기술 의존 기능이므로 domain에 추상, infrastructure에 구현체를 둔다(§5.2, R8, 결정 D21). **`Clock` ABC는 모듈별로 둔다**(catalog는 자기 모듈 domain 안). 공용 `src/common/`에 두지 않는다(D21 확정, stores.md D13과 동일 결정).
- 조립은 모듈 밖 `src/container.py`가 한다(9.2절). 모듈 안에는 구현체를 만드는 코드가 없다.

---

## 2. 선행 의존: stores 최소 인터페이스와 의존 방향

### 2.1 catalog가 stores에서 필요한 것

| 필요 | 쓰는 곳 | stores가 제공할 것 |
| --- | --- | --- |
| 상점 존재 확인 | #1, #2, #9 | `find_store_by_id(store_id) -> StoreInfo \| None` (실제: `StoresApplicationService.find_store_by_id`, `src/stores/application/service.py:18`, 없으면 `None`) |
| owner 확인 | #1, #5, #6, #7, #13, #14 | `StoreInfo.owner_id` |
| 승인 여부 | #1, #7, #13 | `StoreInfo.approval_at is not None` |
| 폐점 여부 | #1, #7, #13 | `StoreInfo.closed_at is not None` |
| `store_name`, `pickup_address` 조인 | #4, #7(응답), #9, #13(응답) | `StoreInfo.name`, `StoreInfo.pickup_address` |
| 여러 상점 일괄 조회 | 후속 #8(주변 할인) | `find_stores_by_ids(ids) -> list[StoreInfo]` (실제: `service.py:21`, `Sequence[UUID]` 입력, 1차에서는 쓰지 않음) |

**실제 `Store`(`src/stores/domain/store.py:19-31`)와 포트·`StoreRef` 대조 (2026-11-03 확인)**

| `StoreInfo`/`StoreRef` 필드 | 실제 `Store` | 판정 |
| --- | --- | --- |
| `id: UUID` | `id: UUID \| None`(저장 후 항상 값) | 호환(Protocol에서 `UUID`로 선언해도 저장된 값만 받음. 구조 검사는 정적 타입이라 런타임 영향 없음) |
| `owner_id: UUID` | `owner_id: UUID` | 일치 |
| `name: str`, `pickup_address: str` | 같은 이름의 `str` | 일치 |
| `approval_at`, `closed_at: datetime \| None` | 같은 이름 | 일치 |
| `StoreRef.approved` / `closed` | `Store.is_approved` / `is_closed`(프로퍼티) | catalog는 `approval_at`/`closed_at` 유무로 계산하므로 stores의 프로퍼티에 의존하지 않음 |
| (후속 #8) `latitude`, `longitude` | `float \| None` | 존재. C1 후속 때 `StoreInfo`에 추가 |

`Store.ensure_owned_by`(stores 쪽)는 stores 예외 `NotStoreOwnerError`를 낸다. catalog `StoreRef.ensure_owner`는 catalog 자기 예외를 내므로 stores 메서드를 호출하지 않는다(R11, C5).

### 2.2 의존 방향 결정: "포트(Protocol)를 catalog가 정의하고, 연결은 `src/container.py`가 한다"

- `catalog/application/ports.py`에 `StoreInfo`(필드: `id, owner_id, name, pickup_address, approval_at, closed_at`)와 `StorePort`(메서드: `find_store_by_id`, `find_stores_by_ids`)를 `typing.Protocol`로 정의한다. 쓰는 쪽이 포트를 정의하는 방식이다(layer-architecture §3.4, R11).
- stores의 서비스가 같은 이름의 메서드를 제공하고 반환하는 `Store` 도메인 객체가 위 필드를 가지면, catalog는 stores를 **import하지 않고** 구조적으로 맞춘다.
- 조립: `catalog/presentation/dependencies.py`가 `provide_store_port() -> StorePort`를 선언하고, container의 `create_store_port`가 stores 서비스 인스턴스를 돌려준다. `CatalogApplicationService`는 생성자에서 `StorePort`를 필수 인자로 받는다. router는 `provide_catalog_service`만 쓴다(R9). 같은 요청 세션을 공유한다(`Depends(get_db)`, R13).
- stores 폐점(stores 명세 #2)은 "진행 중·예정 할인이 있으면 폐점 불가"라서 stores가 catalog를 필요로 한다. 의존 표현과 생성 순환은 9절에서 다룬다.
- catalog application은 받은 `StoreInfo`를 `StoreRef`(domain, 값 복사)로 바꿔서 쓴다. 상점주 확인·승인·폐점 판단은 `StoreRef` 메서드에 둔다(비즈니스 검증은 도메인, R3).
- 테스트에서는 `StorePort`를 만족하는 fake 객체를 생성자에 넣어 DB 없이 서비스를 검증한다.

### 2.3 catalog가 stores에 제공하는 것 (역방향, 엔드포인트 없음)

`CatalogApplicationService.has_open_offers_for_store(store_id, *, now=None) -> bool` — stores 폐점 시 사용. `now`는 키워드 전용이며, 생략하면 주입된 `Clock`으로 현재 시각을 얻는다(CI-2 확정). 1차에 함께 구현하는 것을 권장한다(레포지토리 쿼리 `exists_open_by_store`가 #6, #7과 같은 "진행 중" 정의를 공유하므로).

stores는 이 메서드를 자기 쪽 포트(`OpenOffersPort`, stores.md 8절)로 받는다. catalog 서비스가 구조적으로 만족하므로 catalog는 stores 포트를 import하지 않는다. 연결은 container의 `create_catalog_service`가 반환한 인스턴스를 stores 구역이 받는 것으로 끝난다(9절).

### 2.4 stores 쪽 최소 구현 요청 (catalog 구현자가 요구하는 것, stores 설계 범위는 아님)
아래 4개는 2026-11-03 3차 시점에 모두 충족됨(확인):
1. `StoreModel`(`stores` 테이블): `src/stores/infrastructure/models.py:13`.
2. `find_store_by_id`, `find_stores_by_ids`: `src/stores/application/service.py:18,21`.
3. `main.py`의 stores models import: `src/main.py:15`. catalog models는 이 뒤에 추가한다.
4. container의 `create_stores_service`: `src/container.py:68`.
남은 stores 쪽 항목은 폐점 시 `OpenOffersPort`(후속, 9.3)뿐이다. 현재 `StoresApplicationService`에는 `has_open_offers`용 인자가 없다.

상점주 승인 상태(`users`에 저장할 곳 없음)는 stores/auth의 미결 사항이라 catalog는 "상점 `approval_at` 유무"만 본다.

---

## 3. 도메인 (domain/)

fastapi, sqlalchemy, pydantic, `database`, 다른 모듈을 import하지 않는다(R1, R11). `auth.domain`의 예외·엔티티도 import하지 않는다(CI-3).

### 3.1 exceptions.py

| 클래스 | 상속 | 응답 | 쓰는 곳 |
| --- | --- | --- | --- |
| `ProductNotFoundError` | `LookupError` | 404 `NOT_FOUND` "상품을 찾을 수 없습니다." | |
| `OfferNotFoundError` | `LookupError` | 404 "할인 판매를 찾을 수 없습니다." | |
| `StoreNotFoundError` | `LookupError` | 404 "상점을 찾을 수 없습니다." | 포트가 `None` 반환 시 |
| `NotStoreOwnerError` | `PermissionError` | 403 `FORBIDDEN` | 메시지는 생성 시 EP별로 전달 |
| `StoreNotApprovedError` | `ValueError` | 400 `STORE_NOT_APPROVED` | |
| `StoreClosedError` | `ValueError` | 400 `STORE_CLOSED` | |
| `ProductInactiveError` | `ValueError` | 400 `PRODUCT_INACTIVE` | 비활성 상품 할인 등록 |
| `OpenOfferExistsError` | `ValueError` | 400 `OFFER_ALREADY_OPEN` | 이미 진행 중인 할인 |
| `ProductAlreadyInactiveError` | `ValueError` | 400 `PRODUCT_ALREADY_INACTIVE` | |
| `ProductHasOpenOfferError` | `ValueError` | 400 `PRODUCT_HAS_OPEN_OFFER` | |
| `OfferClosedError` | `ValueError` | 400 `OFFER_CLOSED` | 중단된 할인 재등록·재고 조정 |
| `InsufficientStockError` | `ValueError` | 400 `INSUFFICIENT_STOCK` | 재고 조정 시 남은 수량 초과 차감 |

그 외 입력 검증은 단순 `ValueError`(400 `VALIDATION_ERROR`). `error_handlers.py` 수정은 필요 없다(409 없음). domain·application·router에서 `HTTPException`을 만들지 않는다(R6).

### 3.2 StoreRef (값 객체, 읽기 전용)
- 속성: `id, owner_id: UUID, name: str, pickup_address: str, approved: bool, closed: bool`
- `StoreRef.from_info(info)`: `approved = info.approval_at is not None`, `closed = info.closed_at is not None`
- `ensure_owner(user_id, message)`: 다르면 `NotStoreOwnerError(message)`
- `ensure_can_register(what: str)`: 미승인이면 `StoreNotApprovedError("승인되지 않은 상점에는 {what}을 등록할 수 없습니다.")`, 폐점이면 `StoreClosedError("폐점된 상점에서는 {what}을 등록할 수 없습니다.")` (`what`은 "상품" 또는 "할인"). 검사 순서는 폐점 → 미승인(결정 D9).

### 3.3 Product
| 속성 | 타입 | 규칙 |
| --- | --- | --- |
| `id` | `UUID \| None` | 저장 전 None |
| `store_id` | `UUID` | |
| `name` | `str` | 앞뒤 공백 제거 후 1~200자 |
| `category` | `str \| None` | 최대 80자, 빈 문자열은 None으로 정규화하지 않음(그대로 검증: 비어 있으면 오류) |
| `description` | `str \| None` | |
| `original_price` | `int` | 0보다 큼 ("정상 가격은 0보다 커야 합니다."). `bool` 거부 |
| `is_active` | `bool` | 기본 True |
| `product_image` | `list[str]` | 최대 10개("이미지는 최대 10개까지 등록할 수 있습니다."), 항목은 공백 아닌 문자열. 내부에 복사본 저장 |

메서드:
| 메서드 | 동작 | ValueError 조건 |
| --- | --- | --- |
| `Product.register(store_id, name, original_price, category=None, description=None, product_image=None)` | 생성자 호출, `is_active=True` | 생성자 검증 |
| `apply_changes(changes: dict, open_offer_sale_price: int \| None)` | `changes`는 보낸 키만 포함. 허용 키 `name, category, description, original_price, product_image`. 값 검증은 생성자와 같은 규칙을 공유하는 `_validate_*` 정적 메서드 사용 | `changes`가 비어 있으면 "수정할 항목이 없습니다."; `name`/`original_price`/`product_image`가 None이면 검증 오류; `original_price`를 바꾸는데 `open_offer_sale_price`가 있고 `new_price <= open_offer_sale_price`면 `ValueError("정상 가격은 진행 중인 할인 가격보다 커야 합니다.")` |
| `deactivate(has_open_offer: bool)` | `is_active=False` | 이미 비활성이면 `ProductAlreadyInactiveError("이미 비활성화된 상품입니다.")`; `has_open_offer`면 `ProductHasOpenOfferError("진행 중인 할인 판매가 있어 비활성화할 수 없습니다.")` (비활성 검사가 먼저) |
| `ensure_active_for_offer()` | | 비활성이면 `ProductInactiveError("비활성화된 상품은 할인 등록할 수 없습니다.")` |

상태 전이: `is_active` true → false (#6). false → true(재노출)는 1차 범위에 API가 없어 메서드도 만들지 않는다(결정 D13).

### 3.4 DiscountOffer
`OfferStatus(StrEnum)`: `SCHEDULED, ON_SALE, SOLD_OUT, CLOSED`.

| 속성 | 타입 |
| --- | --- |
| `id` | `UUID \| None` |
| `product_id` | `UUID` |
| `sale_price` | `int` |
| `initial_stock` | `int` |
| `remaining_stock` | `int` |
| `sales_start, sales_end, pickup_start, pickup_end` | `datetime` (timezone 필수) |
| `status` | `OfferStatus` (저장된 값) |
| `is_active` | `bool` |

상수: `MAX_INITIAL_STOCK = 9999`.

생성자 불변식(저장된 데이터에도 항상 참): `sale_price > 0`; `0 <= remaining_stock <= initial_stock`; `initial_stock >= 0`; 모든 datetime은 tz-aware; `sales_end > sales_start`; `pickup_end > pickup_start`.

| 메서드 | 동작 | ValueError 조건 |
| --- | --- | --- |
| `DiscountOffer.register(original_price, product_id, sale_price, initial_stock, sales_end, pickup_start, pickup_end, now, sales_start=None)` | `sales_start`가 None이면 `now`. `remaining=initial`. status = `SCHEDULED if sales_start > now else ON_SALE`. `is_active=True` | `initial_stock`가 1~9999 밖: "수량은 1개 이상 9999개 이하여야 합니다."; `sale_price <= 0`; `sale_price >= original_price`: "할인 가격은 정상 가격보다 낮아야 합니다."; `sales_end <= sales_start`: "판매 마감 시간은 판매 시작 시간 이후여야 합니다."; `sales_end <= now`(D10): "판매 마감 시간은 현재 시각 이후여야 합니다."; `pickup_end < sales_end`: "픽업 마감 시간은 판매 마감 시간 이후여야 합니다."; `pickup_end <= pickup_start`: "픽업 마감 시간은 픽업 시작 시간 이후여야 합니다." |
| `effective_status(now) -> OfferStatus` | 규칙은 아래 표. 저장된 `status`가 시간 경과로 낡을 수 있어(스케줄러 없음, D3) 응답·필터·판정은 이 값을 쓴다 | |
| `is_open(now) -> bool` | "진행 중": `is_active and now < sales_end` (D4). 즉 유효 상태가 SCHEDULED/ON_SALE/SOLD_OUT | |
| `is_sold_out -> bool` | `remaining_stock == 0` | |
| `discount_rate(original_price) -> int` | `(original_price - sale_price) * 100 // original_price` 정수 연산, 버림 (D1) | |
| `ensure_relistable()` | | `not is_active`이면 `OfferClosedError("이미 중단된 할인은 재등록할 수 없습니다.")` |
| `close(now)` | `is_active=False`, `status=CLOSED`. #13에서 기존 할인을 닫을 때 사용(#12도 후속에서 재사용) | 이미 `not is_active`면 `OfferClosedError("이미 중단된 할인입니다.")` |
| `adjust_stock(amount, now)` | 아래 시나리오 | 아래 |
| `_sync_status(now)` | 변경 후 `self.status = effective_status(now)` | |

도메인 메서드는 `now`를 인자로 받는다. 현재 시각은 application이 `Clock`에서 얻어 넘기므로 도메인은 시계를 직접 부르지 않는다.

`effective_status(now)` 우선순위:
1. `not is_active` → `CLOSED`
2. `now >= sales_end` → `CLOSED`
3. `now < sales_start` → `SCHEDULED`
4. `remaining_stock == 0` → `SOLD_OUT`
5. 그 외 `ON_SALE`

`adjust_stock(amount, now)`:
- `amount == 0` → `ValueError("조정 수량은 0이 될 수 없습니다.")`
- `not is_active` → `OfferClosedError("중단된 할인은 재고를 조정할 수 없습니다.")` (시간만 지나 종료된 할인은 허용, D8)
- `amount < 0`이고 `-amount > remaining_stock` → `InsufficientStockError("차감할 수량이 남은 재고보다 많습니다.")`
- `amount > 0`: `initial_stock += amount`, `remaining_stock += amount`. `initial_stock > 9999`이면 `ValueError("최초 수량은 9999개를 넘을 수 없습니다.")` (먼저 검사, 상태 변경 전)
- `amount < 0`: `remaining_stock += amount`. `initial_stock`은 그대로(명세는 증가 시에만 initial을 늘린다)
- 마지막에 `_sync_status(now)`: 재고 0 → `SOLD_OUT`, 0에서 증가 → 판매 중이면 `ON_SALE`, 시작 전이면 `SCHEDULED` 유지 (D5)

허용 전이 (저장 status 기준):

| 현재 | 이벤트 | 다음 |
| --- | --- | --- |
| (없음) | 등록(`sales_start > now`) | SCHEDULED |
| (없음) | 등록(그 외) | ON_SALE |
| SCHEDULED | 시간 경과 `now >= sales_start` | ON_SALE (조회 시 계산, 저장은 다음 쓰기 때 갱신) |
| ON_SALE | 재고 0 | SOLD_OUT |
| SOLD_OUT | 재고 > 0 | ON_SALE |
| SCHEDULED/ON_SALE/SOLD_OUT | 중단(`close`), 재등록으로 기존 건 닫힘 | CLOSED |
| CLOSED | 어떤 이벤트도 | 전이 없음 (재고 조정·재등록·재중단 모두 `OfferClosedError`) |

> 후속(예약 모듈): `deduct_stock(quantity, now)` / `restore_stock(quantity, now)`를 같은 클래스에 추가한다. 예약 가능 판정은 `effective_status(now) == ON_SALE`로 한다. 1차에서는 만들지 않는다.

### 3.5 StockLog
- 속성: `id: UUID | None`, `offer_id: UUID`, `user_id: UUID | None`, `amount: int`(입고 +, 차감 −), `reason: str | None`(최대 200자), `created_at: datetime | None`
- 검증: `amount != 0`, `reason`은 200자 이하(공백뿐이면 None). 불변(append-only)이라 행위 메서드 없음.
- 팩토리: `StockLog.initial_stock(offer_id, user_id, quantity)` (reason `"최초 입고"`), `StockLog.manual_adjustment(offer_id, user_id, amount, reason)`.

### 3.6 추상 레포지토리 (`domain/repository/`)

도메인 객체만 주고받는다(R4). 인프라 구현체는 5.2절. 메서드 목록은 구현체와 같고, 서비스는 여기 선언된 메서드만 호출한다(R10).

| 추상 | 파일 | 메서드 |
| --- | --- | --- |
| `ProductRepository(ABC)` | `product_repository.py` | `find_by_id(product_id, for_update=False) -> Product \| None`; `find_by_store(store_id, *, category, is_active, page, size) -> tuple[list[Product], int]`; `save(product) -> Product` |
| `DiscountOfferRepository(ABC)` | `discount_offer_repository.py` | `find_by_id(offer_id, for_update=False) -> DiscountOffer \| None`; `find_open_by_product(product_id, now) -> DiscountOffer \| None`; `exists_open_by_store(store_id, now) -> bool`; `find_by_store(store_id, *, status, now, page, size) -> tuple[list[tuple[DiscountOffer, Product]], int]`; `save(offer) -> DiscountOffer` |
| `StockLogRepository(ABC)` | `stock_log_repository.py` | `add(log) -> StockLog` |

### 3.7 추상 도메인 서비스 (`domain/service.py`)

```python
class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime: ...   # timezone-aware(UTC)
```
- 시간 의존 규칙(진행 중, 유효 상태, 등록 시각 검증)을 테스트에서 고정하기 위한 추상이다(결정 D21).
- `Clock`은 catalog 모듈 domain 안에 둔다. 모듈 간 공용 `src/common/`으로 옮기지 않는다(D21 확정). container의 `SystemClock` 싱글턴도 catalog 구역에서 자기 모듈의 `Clock` 구현체를 만든다.

---

## 4. 스키마 변경 제안 (`schema.sql`·`db-schema` 문서는 이 문서가 고치지 않는다)

| # | 대상 | 현재 | 제안 | 이유 | 미승인 시 임시 처리 |
| --- | --- | --- | --- | --- | --- |
| S1 | `products.name`, `products.original_price` | NULL 허용 | `NOT NULL` | 명세상 필수. 도메인 불변식과 일치 | `models.py`는 NOT NULL로 선언(도메인이 항상 값을 보장). DDL 문서는 팀이 수정 |
| S2 | `stock_log.reason` | 없음 | `reason VARCHAR(200)` NULL 허용 추가 | #14 `reason`, 최초 입고 사유 저장 | 컬럼 추가를 기본값으로 채택. 거부되면 레포지토리에서 `reason` 저장만 생략(도메인 속성은 유지) |
| S3 | `discount_offers.price` | `sale_price`와 중복, 명세에 없음 | 컬럼 삭제 | 어느 API도 쓰지 않음 | `models.py`에 매핑하지 않음 |
| S4 | `discount_offers.sales_start` | NULL 허용 | `NOT NULL` | 등록 시 항상 값 결정(기본 현재 시각). 상태 계산에 필요 | `models.py`는 NOT NULL |
| S5 | `discount_offers.is_active`, `status` | 두 값이 겹침(중단 = `is_active=false` + `CLOSED`) | 유지. 두 값은 도메인 `close()`가 함께 바꾼다 | 명세 #12 | 변경 없음 |
| S6 | `products` 생성 시각 | 없음 | `created_at TIMESTAMPTZ NOT NULL DEFAULT now()` 추가(선택) | 상품 목록 최신순 정렬 | 미승인 시 `name ASC, id ASC` 정렬(D15) |
| S7 | `discount_offers` 진행 중 할인 유일성 | 없음 | DB 부분 유니크 인덱스는 **만들 수 없음** | "진행 중"이 `now() < sales_end`라서 `WHERE`에 시간 조건을 쓸 수 없음 | 상품 행 `FOR UPDATE` 잠금으로 직렬화(5.3절) |
| S8 | `discount_offers.sale_price < original_price` | 테이블 간 검증이라 CHECK 불가 | 도메인 검증만 | | |
| S9 | `discount_offers` CHECK | `initial_stock >= 0` | 앱 규칙 `1~9999`는 DB에 두지 않음(재고 수동 차감 시 `initial`은 유지) | | |

---

## 5. 인프라 (infrastructure/)

### 5.1 models.py

공통: `TZ = DateTime(timezone=True)`, UUID PK `default=uuid.uuid4, server_default=gen_random_uuid()`, 다른 모듈 모델은 import하지 않고 `ForeignKey("stores.id")` 문자열만 사용(R11, R14).

| 모델 / 테이블 | 컬럼·제약 |
| --- | --- |
| `ProductModel` / `products` | `id`; `store_id UUID FK stores.id, index`; `name String(200) NOT NULL`; `category String(80) NULL`; `description Text NULL`; `original_price int NOT NULL, CHECK >= 0`; `is_active bool NOT NULL default true`; `product_image JSON`(리스트, 기본 `[]`) |
| `DiscountOfferModel` / `discount_offers` | `id`; `product_id FK products.id, index`; `sale_price int NOT NULL CHECK >= 0`; `initial_stock int NOT NULL CHECK >= 0`; `remaining_stock int NOT NULL`; `sales_start, sales_end, pickup_start, pickup_end TZ NOT NULL`; `status String(20) NOT NULL CHECK IN (...)`; `is_active bool NOT NULL default true`; 제약 `ck_offer_remaining_stock`, `ck_offer_pickup_window` (schema.sql 그대로) |
| `StockLogModel` / `stock_log` | `id`; `offer_id FK discount_offers.id, index`; `user_id FK users.id NULL`; `amount int NOT NULL`; `reason String(200) NULL`(S2); `created_at TZ server_default now()` |

### 5.2 repositories.py (추상 3.6절의 구현체)
모두 도메인 객체를 반환·수신한다(R4). `commit()` 금지, `flush()`까지(R5). 생성자는 `session: AsyncSession` 하나를 받는다. `*Model`은 밖으로 내보내지 않고 `_to_domain`에서 변환한다.

`SqlAlchemyProductRepository(session)` — `ProductRepository` 구현
- `find_by_id(product_id, for_update=False) -> Product | None`
- `find_by_store(store_id, *, category=None, is_active=True, page, size) -> tuple[list[Product], int]` (`total`은 같은 필터의 `count(*)`; 정렬 D15)
- `save(product) -> Product` (신규 insert, 기존은 변경 필드 update)

`SqlAlchemyDiscountOfferRepository(session)` — `DiscountOfferRepository` 구현
- `find_by_id(offer_id, for_update=False) -> DiscountOffer | None`
- `find_open_by_product(product_id, now) -> DiscountOffer | None` (`is_active AND sales_end > now`)
- `exists_open_by_store(store_id, now) -> bool` (products 조인, 같은 모듈이라 허용)
- `find_by_store(store_id, *, status, now, page, size) -> tuple[list[tuple[DiscountOffer, Product]], int]` (products 조인, 정렬 `sales_end ASC, id ASC`)
- `save(offer) -> DiscountOffer`
- 상태 필터 SQL은 `_status_clause(status, now)` 한 곳에서 만들고 3.4의 `effective_status` 우선순위와 같은 조건을 쓴다. 두 구현이 어긋나지 않게 "같은 데이터로 두 방식 결과 비교" 테스트를 둔다.

`SqlAlchemyStockLogRepository(session)` — `StockLogRepository` 구현
- `add(log) -> StockLog` (insert 후 `flush()`, `id` 채움)
- (후속) `find_by_offer(offer_id, page, size)` — 재고 이력 조회 API 계획은 명세에 없다. 추가할 때는 추상에도 함께 선언한다.

`SystemClock` (`clock.py`) — `Clock` 구현. `datetime.now(timezone.utc)`를 돌려준다. 상태가 없어 container에서 싱글턴으로 둔다.

### 5.3 동시성

| 지점 | 위험 | 대응 |
| --- | --- | --- |
| #14 재고 조정 | 예약의 재고 차감과 동시에 갱신되면 lost update | `offers.find_by_id(offer_id, for_update=True)` (`SELECT ... FOR UPDATE`). 예약 모듈도 같은 행을 같은 방식으로 잠근다 |
| #7, #13 할인 등록·재등록 | 같은 상품에 동시에 두 번 등록해 "진행 중" 할인이 2개가 됨(S7: DB 유니크 불가) | 상품 행 `products.find_by_id(product_id, for_update=True)`로 직렬화한 뒤 `find_open_by_product` 검사 |
| #6 노출 중단 vs #7 할인 등록 | 중단 직후 할인이 등록되는 경합 | 둘 다 상품 행 잠금 |
| #5 가격 수정 vs #7 할인 등록 | `sale_price < original_price` 위반 | 둘 다 상품 행 잠금 |
| 잠금 순서(교착 방지) | | 항상 **product → offer** 순서. #13은 offer를 잠금 없이 읽어 `product_id`를 얻고 → product 잠금 → offer 잠금 순으로 한다 |
| DB 안전망 | | `ck_offer_remaining_stock` |

---

## 6. 응용 (application/)

### 6.1 구성
```python
class CatalogApplicationService:
    def __init__(
        self,
        session: AsyncSession,
        stores: StorePort,
        products: ProductRepository,
        offers: DiscountOfferRepository,
        stock_logs: StockLogRepository,
        clock: Clock,
    ): ...
```
- **모든 인자는 필수다.** `|` None 기본값이나 `x or 구현체(...)` 같은 기본 생성을 두지 않는다(R8, layer-architecture §5.4). `products`, `offers`, `stock_logs`, `clock`은 추상 타입이고, `stores`는 catalog가 정의한 `StorePort`다. infrastructure·stores 구현체를 import하지 않는다(R2, R11).
- 서비스 생성자 안에서 다른 서비스나 구현체를 만들지 않는다(R12). 만드는 곳은 container의 `create_*` 팩토리뿐이다.
- 테스트는 fake `ProductRepository`·`DiscountOfferRepository`·`StockLogRepository`·`StorePort`와 고정 `Clock`을 넘긴다.
- 서비스 메서드는 로그인한 회원을 `User` 객체가 아니라 `user_id: UUID`로 받는다. auth 도메인 엔티티를 application이 import하지 않게 하기 위해서다(R11, 결정 D23). router가 `owner.id`를 넘긴다.
- 읽기 결과 타입(`views.py`): `Page[T](items, page, size, total)`, `ProductDetailView(product, store_name, pickup_address)`, `OfferView(offer, product, store_name, status, discount_rate, is_sold_out)`(`status`는 `effective_status(now)`).
- 내부 헬퍼 `_load_store(store_id) -> StoreRef`: 포트가 None이면 `StoreNotFoundError`.
- `now`는 서비스 메서드 시작 시 `self.clock.now()`로 한 번만 얻어 도메인과 레포지토리에 넘긴다.
- `MAX_PAGE_SIZE = 100`은 schema의 `Query(le=100)`로 막는다.

### 6.2 시나리오 (쓰기: 조회 → 도메인 → save → commit)

**#1 `create_product(user_id, store_id, data) -> Product`**
1. `store = _load_store(store_id)` (404)
2. `store.ensure_owner(user_id, "본인 상점에만 상품을 등록할 수 있습니다.")` (403)
3. `store.ensure_can_register("상품")` (400)
4. `Product.register(...)` (400)
5. `products.save` → `session.commit()`

**#5 `update_product(user_id, product_id, changes: dict) -> Product`**
1. `products.find_by_id(product_id, for_update=True)` (404)
2. `store = _load_store(product.store_id)`; `ensure_owner(..., "본인 상점의 상품만 수정할 수 있습니다.")`
3. `open_offer = offers.find_open_by_product(product_id, now)` (`original_price`를 바꿀 때만 조회)
4. `product.apply_changes(changes, open_offer.sale_price if open_offer else None)`
5. `products.save` → `commit()`

**#6 `deactivate_product(user_id, product_id) -> Product`**
1. 상품 `for_update` 조회 (404) → 소유 확인("본인 상점의 상품만 변경할 수 있습니다.")
2. `has_open = offers.find_open_by_product(...) is not None`
3. `product.deactivate(has_open)` → `save` → `commit()`

**#7 `register_offer(user_id, product_id, data) -> OfferView`**
1. 상품 `for_update` 조회 (404)
2. `store = _load_store(product.store_id)`; `ensure_owner(..., "본인 상점의 상품만 할인 등록할 수 있습니다.")`; `ensure_can_register("할인")`
3. `product.ensure_active_for_offer()`
4. `offers.find_open_by_product(product_id, now)`가 있으면 `OpenOfferExistsError("이미 진행 중인 할인 판매가 있습니다.")`
5. `DiscountOffer.register(original_price=product.original_price, ..., now=now)`
6. `offers.save(offer)`; `stock_logs.add(StockLog.initial_stock(offer.id, user_id, offer.initial_stock))`
7. `commit()` 한 번 → `OfferView` 반환
- 할인·재고 로그는 한 트랜잭션이다. 둘 중 하나가 실패하면 둘 다 롤백된다.

**#13 `relist_offer(user_id, offer_id, data) -> OfferView` (단일 트랜잭션)**
1. `old = offers.find_by_id(offer_id)` (404) — `product_id`를 얻기 위한 잠금 없는 조회
2. `product = products.find_by_id(old.product_id, for_update=True)` (잠금 순서 product → offer)
3. `old = offers.find_by_id(offer_id, for_update=True)` (상태 재확인. 없으면 404)
4. `store = _load_store(product.store_id)`; `ensure_owner(..., "본인 상점의 할인만 재등록할 수 있습니다.")`; `ensure_can_register("할인")`
5. `old.ensure_relistable()` (400 "이미 중단된 할인은 재등록할 수 없습니다.")
6. `product.ensure_active_for_offer()`
7. `old.close(now)` → `offers.save(old)` (기존 예약은 그대로 둔다. 기존 건의 `remaining_stock`은 변경하지 않음)
8. `new = DiscountOffer.register(original_price=product.original_price, ...)` (가격 400은 여기서 발생)
9. `offers.find_open_by_product(...)`가 남아 있으면(예: 데이터 불일치) `OpenOfferExistsError` — 7번에서 기존 건을 이미 닫았으므로 정상 흐름에서는 None
10. `offers.save(new)`; `stock_logs.add(StockLog.initial_stock(new.id, user_id, new.initial_stock))`
11. **`commit()` 한 번.** 중간 예외(가격 검증 실패 포함)가 나면 커밋되지 않아 기존 할인도 닫히지 않는다(세션 종료 시 롤백).

**#14 `adjust_stock(user_id, offer_id, amount, reason) -> StockAdjustResult`**
1. `offer = offers.find_by_id(offer_id, for_update=True)` (404) — **행 잠금 시작**
2. `product = products.find_by_id(offer.product_id)`; `store = _load_store(product.store_id)`; `ensure_owner(..., "본인 상점의 재고만 조정할 수 있습니다.")` (D8: 명세의 "이력만 조회" 문구는 복사 오류로 보고 교체)
3. `offer.adjust_stock(amount, now)` (0, 중단, 초과 차감, 9999 초과, 상태 전환은 도메인)
4. `offers.save(offer)`
5. `log = stock_logs.add(StockLog.manual_adjustment(offer.id, user_id, amount, reason))` (`amount`는 요청의 부호 그대로)
6. `commit()` 한 번 (잠금 해제). 응답: `offer_id, initial_stock, remaining_stock, is_sold_out, status, log_id`
- 소유 확인을 잠금 뒤에 두는 이유는 단순함이다. 비소유자의 요청이 잠깐 행을 잡지만 곧 403으로 풀린다. (잠금 전에 확인하려면 조회를 한 번 더 해야 한다.)

### 6.3 시나리오 (읽기)

**#2 `list_products(viewer_id: UUID | None, store_id, category, is_active, page, size) -> Page[Product]`**
1. `store = _load_store(store_id)` (404)
2. `is_active=False`를 요청하면: 소유자(`viewer_id == store.owner_id`)가 아니면 `NotStoreOwnerError("본인 상점의 비활성 상품만 조회할 수 있습니다.")` (D6). **비로그인(401) 판정은 router가 한다**(7.1절, CI-3): `is_active=False`인데 `viewer`가 `None`이면 router가 `auth.domain.exceptions.AuthenticationError`를 낸다(`HTTPException`이 아니므로 R6 위반 아님, 401 형식·헤더는 전역 핸들러).
3. `products.find_by_store(...)`

**#4 `get_product(viewer_id: UUID | None, product_id) -> ProductDetailView`**
1. 상품 조회 (404) → `store = _load_store(...)`
2. `product.is_active`가 False이고 `viewer_id`가 소유자가 아니면 `ProductNotFoundError` (D7)
3. `ProductDetailView(product, store.name, store.pickup_address)`

**#9 `list_offers_by_store(store_id, status, page, size) -> Page[OfferView]`**
1. `store = _load_store(store_id)` (404)
2. `offers.find_by_store(store_id, status=status, now=now, ...)` → 각 항목을 `OfferView`로 변환 (`store_name`은 한 번만 조회한 값 사용)

### 6.4 모듈 간 트랜잭션 경계
- 1차 범위에서 catalog는 다른 모듈의 쓰기를 호출하지 않는다. stores는 읽기만 한다(같은 요청 세션, container에서 `Depends(get_db)` 공유).
- 후속(예약 연계): reservations가 container에서 `CatalogApplicationService`(또는 reservations 쪽 포트)를 주입받아 `deduct_stock(..., commit=False)`를 호출하고 마지막에 한 번 `commit()`한다(R13). 결제 실패·예약 취소 시 `restore_stock(commit=False)`. reservations 서비스는 catalog 서비스를 생성자에서 만들지 않는다(R12). 이 메서드들의 설계는 reservations 설계 때 확정한다.
- stores 폐점 → catalog `has_open_offers_for_store`는 읽기 전용이다.

---

## 7. 표현 (presentation/)

### 7.1 의존성 (`presentation/dependencies.py`)
- `provide_catalog_service() -> CatalogApplicationService`: 플레이스홀더. 본문은 `raise NotImplementedError("CatalogApplicationService 의존성이 주입되지 않았습니다.")`. router는 `Annotated[CatalogApplicationService, Depends(provide_catalog_service)]`만 쓴다(R9). router 안에서 서비스·레포지토리·stores 서비스를 조립하지 않는다.
- `provide_store_port() -> StorePort`: 플레이스홀더. container의 `create_store_port`가 바인딩한다. 다른 곳에서 직접 쓰지는 않지만 catalog가 요구하는 포트의 주입 지점을 선언해 `wire_dependencies` 매핑에서 확인하게 한다(R9).
- `OwnerUser`를 쓴다 (`auth.presentation.dependencies`): 토큰 없음/오류 401, 역할이 `OWNER`가 아니면 403.
- `OptionalUser`(이 파일, 2026-11-03 3차 갱신): auth가 container 방식이므로 `auth.presentation.dependencies`의 `bearer_scheme`와 `provide_auth_service`를 쓴다. auth 파일은 수정하지 않는다.
  ```python
  async def get_optional_user(
      credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
      service: Annotated[AuthApplicationService, Depends(provide_auth_service)],
  ) -> User | None:
      if credentials is None or not credentials.credentials:
          return None                      # 헤더 없음 = 비로그인
      return (await service.authenticate(credentials.credentials)).user   # 토큰 오류는 AuthenticationError(401)

  OptionalUser = Annotated[User | None, Depends(get_optional_user)]
  ```
  `provide_auth_service`는 이미 `wire_dependencies`에 매핑되어 있어(`src/container.py:78`) catalog가 매핑을 추가하지 않는다. 같은 요청 안에서 `Depends(get_db)` 세션이 공유된다. `AuthApplicationService`·`User` 타입은 이 파일의 타입 표기에만 쓰고 catalog 서비스(application)는 `user_id`만 받는다(D23). 다른 모듈 presentation에서 auth application 타입을 import하는 것이 `layer-checker`에 걸리는지는 확인 필요(질문 Q-A). 대안은 auth 쪽에 `OptionalUser`를 두는 모듈 밖 변경 제안이다.
- 위 `provide_*` 2개는 모두 `src/container.py`의 `wire_dependencies`에 매핑되어야 한다(R9, 9.2절).

### 7.2 엔드포인트 (prefix `/v1`, tags `["카탈로그"]`)

| # | Method | URI | 요청 | 응답 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | POST | `/v1/stores/{store_id}/products` | `ProductCreateRequest` | `ProductResponse` | 201 | 400(가격, 미승인·폐점 상점), 401, 403(`OWNER` 아님/본인 상점 아님), 404(상점) |
| 2 | GET | `/v1/stores/{store_id}/products` | 쿼리 | `ProductListResponse` | 200 | 400(page/size 형식), 401·403(`is_active=false` 비소유), 404(상점) |
| 4 | GET | `/v1/products/{product_id}` | - | `ProductDetailResponse` | 200 | 404(없음, 또는 비활성+비소유) |
| 5 | PATCH | `/v1/products/{product_id}` | `ProductUpdateRequest` | `ProductResponse` | 200 | 400(항목 없음, 할인가 이하), 401, 403, 404 |
| 6 | POST | `/v1/products/{product_id}/deactivate` | 없음 | `ProductResponse` | 200 | 400(이미 비활성, 진행 중 할인), 401, 403, 404 |
| 7 | POST | `/v1/products/{product_id}/offers` | `OfferCreateRequest` | `OfferResponse` | 201 | 400(가격·시간·비활성 상품·진행 중 할인·상점), 401, 403, 404 |
| 9 | GET | `/v1/stores/{store_id}/offers` | 쿼리 | `OfferListResponse` | 200 | 400(status 값 등), 404(상점) |
| 13 | POST | `/v1/offers/{offer_id}/relist` | `OfferCreateRequest` | `OfferResponse`(신규) | 201 | 400(이미 중단, 가격·시간), 401, 403, 404 |
| 14 | POST | `/v1/offers/{offer_id}/stock-adjustments` | `StockAdjustmentRequest` | `StockAdjustmentResponse` | 200 | 400(0, 초과 차감, 중단, 상한), 401, 403, 404 |

- 요청 형식 오류(Pydantic)는 프로젝트 전역 핸들러가 **400 `VALIDATION_ERROR`**로 바꾼다(`error_handlers.py`). 명세의 422는 반영되지 않는다(D14).
- 모든 에러 본문은 `{"success": false, "error_code", "message"}`(R7).
- 라우터는 서비스만 호출하고 예외를 잡지 않는다. 쓰기 EP는 `owner.id`를, 읽기 EP #2·#4는 `viewer.id if viewer else None`을 서비스에 넘긴다.
- 경로 충돌: 후속 `GET /v1/products/search`는 `GET /v1/products/{product_id}`보다 **먼저** 등록한다.

### 7.3 스키마 (명세 필드명 그대로)

| 스키마 | 필드 |
| --- | --- |
| `ProductCreateRequest` | `name`(1~200), `category`(≤80, 선택), `description`(선택), `original_price`(int, `gt=0`), `product_image`(≤10, 선택) |
| `ProductUpdateRequest` | 위 5개 모두 선택. 라우터는 `body.model_dump(exclude_unset=True)`를 서비스에 전달. 빈 본문 `{}`은 도메인에서 400 "수정할 항목이 없습니다." |
| `ProductResponse` | `id, store_id, name, category, description, original_price, is_active, product_image`(`from_attributes`) |
| `ProductDetailResponse` | `ProductResponse` + `store_name, pickup_address` |
| `ProductListResponse` | `items: list[ProductResponse], page, size, total` |
| `OfferCreateRequest` | `sale_price`, `initial_stock`(`ge=1, le=9999`), `sales_start`(선택), `sales_end`, `pickup_start`, `pickup_end`. datetime은 timezone 필수(aware 검증 validator; naive 입력은 400) |
| `OfferResponse` | Offer 공통 객체: `id, product_id, store_id, store_name, product_name, original_price, sale_price, discount_rate, initial_stock, remaining_stock, is_sold_out, sales_start, sales_end, pickup_start, pickup_end, status, is_active`. `OfferResponse.from_view(view)` |
| `OfferListResponse` | `items: list[OfferResponse], page, size, total` |
| `StockAdjustmentRequest` | `amount: int`(0은 도메인에서 거부), `reason: str \| None`(≤200) |
| `StockAdjustmentResponse` | `offer_id, initial_stock, remaining_stock, is_sold_out, status, log_id` |

### 7.4 목록 쿼리 매개변수

| EP | 이름 | 타입 | 기본 | 검증 |
| --- | --- | --- | --- | --- |
| #2 | `category` | str | - | 정확 일치 |
| #2 | `is_active` | bool | `true` | `false`는 소유자만(D6) |
| #2, #9 | `page` | int | 1 | `ge=1` |
| #2, #9 | `size` | int | 20 | `ge=1, le=100` |
| #9 | `status` | `OfferStatus` enum | `ON_SALE` | 허용 외 값은 400. 유효 상태 기준 필터. 정렬 `sales_end` 오름차순 |

정렬 옵션은 1차에서 제공하지 않는다(명세에 #2·#9 정렬 매개변수 없음).

---

## 8. 후속 (2·3차, 이번 설계 대상 아님)

- #3 상품 검색 `GET /v1/products/search` — 위경도 하버사인 거리와 `has_active_offer`, `store_name` 조인이 필요해 stores 좌표 조회 방식이 먼저 정해져야 함.
- #8 주변 할인 목록 `GET /v1/offers` — 반경·정렬(`distance/price/sales_end/discount_rate`)·`StorePort.find_stores_by_ids`(좌표 포함) 필요.
- #10 할인 상세 `GET /v1/offers/{offer_id}` — `notice`, `cancel_policy` 저장·계산 규칙이 미정(명세 14번 이슈).
- #11 할인 수정 `PATCH /v1/offers/{offer_id}` — "예약 0건일 때만 수정"이라 reservations 조회 포트가 필요(catalog가 포트를 정의하고 container가 연결).
- #12 할인 중단 `POST /v1/offers/{offer_id}/close` — `reason` 저장 컬럼, 예약 일괄 취소·환불(reservations/payments 연계)이 필요.
- 상품 재노출 `POST /v1/products/{product_id}/activate` — 명세에 없음(D13).
- reservations용 `deduct_stock/restore_stock` (6.4).

---

## 9. 조립(container)과 의존 방향

### 9.1 의존 방향 요약

```
catalog.presentation -> catalog.application -> catalog.domain
                    \-> auth.presentation.dependencies (OwnerUser, OptionalUser의 기반)
catalog.infrastructure -> catalog.domain
catalog.application  -> catalog.application.ports (StorePort Protocol; stores를 import하지 않음)

src/container.py -> catalog.{application, domain, infrastructure, presentation.dependencies}
src/container.py -> stores.{application, presentation.dependencies, ...}   (조립 지점만 양쪽을 안다)
```
- catalog.presentation·catalog.application은 stores를 import하지 않는다. stores도 catalog를 import하지 않는다(stores는 자기 쪽 `OpenOffersPort`를 정의, stores.md 8절). 두 모듈이 서로를 아는 곳은 `src/container.py`뿐이다(R2, R11, R12).
- 이전 설계의 "catalog.presentation이 stores.application을 조립", "stores.application → catalog.application"(폐점 호출) 화살표는 없어졌다. 연결은 모두 container의 팩토리이며, 순환 import도 생기지 않는다.
- `models.py`는 다른 모듈 모델 클래스를 import하지 않고 FK는 문자열만 쓴다.

### 9.2 container 초안 (`src/container.py`, 모듈 밖 변경 — 11절)

파일 골격은 이미 있다(`src/container.py`, auth·stores 구역과 `wire_dependencies`, B3 해소). 아래는 **catalog implementer가 추가하는 catalog 구역**이다. 현재 파일에 이미 있는 이름: `StoresClock`(stores `Clock` 별칭), `SystemClock`(**stores의 것**, 22행), `_stores_clock`, `create_store_repository`, `create_stores_service`. 이름 충돌을 피하려고 catalog 구현체는 별칭으로 import한다.

```python
# import 추가 (기존 `from stores.infrastructure.clock import SystemClock`는 그대로 둔다)
#   from catalog.infrastructure.clock import SystemClock as CatalogSystemClock
#   from catalog.domain.service import Clock as CatalogClock
#   from catalog.application.ports import StorePort
#   from catalog.presentation.dependencies import provide_catalog_service, provide_store_port
#   (그 외 CatalogApplicationService, 레포지토리 ABC 3종과 SqlAlchemy* 3종 import)

# 상태 없는 유틸 싱글턴 영역(26~29행)에 추가
_catalog_clock: CatalogClock = CatalogSystemClock()

# ── catalog ─────────────────────────────


def create_product_repository(session: AsyncSession = Depends(get_db)) -> ProductRepository:
    return SqlAlchemyProductRepository(session)


def create_discount_offer_repository(session: AsyncSession = Depends(get_db)) -> DiscountOfferRepository:
    return SqlAlchemyDiscountOfferRepository(session)


def create_stock_log_repository(session: AsyncSession = Depends(get_db)) -> StockLogRepository:
    return SqlAlchemyStockLogRepository(session)


def create_store_port(
    stores_service: StoresApplicationService = Depends(create_stores_service),   # stores 구역 팩토리
) -> StorePort:
    return stores_service


def create_catalog_service(
    session: AsyncSession = Depends(get_db),
    stores: StorePort = Depends(create_store_port),
    products: ProductRepository = Depends(create_product_repository),
    offers: DiscountOfferRepository = Depends(create_discount_offer_repository),
    stock_logs: StockLogRepository = Depends(create_stock_log_repository),
) -> CatalogApplicationService:
    return CatalogApplicationService(
        session=session, stores=stores, products=products,
        offers=offers, stock_logs=stock_logs, clock=_catalog_clock,
    )


# wire_dependencies(app)의 기존 dict(auth 1개 + stores 2개, container.py:76-81) 끝에 추가
#   provide_store_port: create_store_port,
#   provide_catalog_service: create_catalog_service,
```
- 한 요청 안에서 `Depends(get_db)`가 같은 세션을 돌려주므로 catalog와 stores의 레포·서비스가 한 트랜잭션을 공유한다(R13).
- `src/main.py`: `wire_dependencies(app)` 호출은 이미 있다(`src/main.py:32`, 라우터 등록 33-34행보다 앞). catalog implementer는 `catalog.infrastructure.models`를 stores models(15행) **뒤**에 import하고 `catalog_router`를 `include_router`로 등록만 한다.
- 이름 구분: stores 구역은 `_stores_clock`을 이미 쓰므로 catalog는 `_catalog_clock`, stores의 `SystemClock` import가 이미 있어 catalog 것은 `CatalogSystemClock` 별칭으로 가져온다. 모듈별 `Clock`이라 서로 다른 타입이다(D21).
- `create_store_port`의 반환 타입 `StorePort`(Protocol)에 `StoresApplicationService`가 구조적으로 맞는지는 구현 후 타입 검사로 확인한다(메서드 이름·인자 `find_store_by_id(store_id)`, `find_stores_by_ids(ids)`는 2.1에서 대조 완료, 반환 `Store`는 `StoreInfo` 속성을 모두 가짐).

### 9.3 stores 폐점이 catalog를 호출할 때의 생성 순환 (stores.md C2·C3 대응)

- **현재 상태(2026-11-03 3차 확인): `StoresApplicationService`는 읽기·개설만 가진 단일 서비스이고 `StoreQueryService`와 `OpenOffersPort`는 아직 없다**(`src/stores/application/service.py`, `src/container.py:68-72`). 그래서 1차 `create_store_port`는 `create_stores_service`의 인스턴스를 그대로 반환한다.
- **1차 범위에는 순환이 없다.** stores 서비스는 `find_store_by_id`/`find_stores_by_ids` 읽기만 하고 catalog를 필요로 하지 않으므로 `create_catalog_service` → `create_store_port` → `create_stores_service` 한 방향이다.
- **폐점(후속)을 넣으면** stores 서비스가 `OpenOffersPort`(= catalog 서비스)를 생성자 필수 인자로 받아야 해서, `create_store_port`가 같은 stores 서비스를 돌려주는 구조에서는 `create_catalog_service` ↔ `create_stores_service`가 `Depends`로 순환한다(FastAPI가 의존성 해석 중 무한 재귀). 생성자 안에서 서로를 만들어 푸는 방식은 R12 위반이라 쓰지 않는다.
- 해법(임시 기본값 D22, stores.md D15와 동일 결정): stores 쪽을 **읽기 전용 서비스(`StoreQueryService`: 레포지토리만 받음)**와 **쓰기 서비스(`StoresApplicationService`: 레포지토리 + `OpenOffersPort`)**로 나눈다. container에서
  - `create_store_port` → `StoreQueryService` (catalog가 사용; catalog를 모른다)
  - `create_catalog_service`는 `Depends(create_store_port)`
  - `create_stores_service`(쓰기, 폐점용)는 `Depends(create_catalog_service)`를 `OpenOffersPort`로 받는다
  순서가 `StoreQueryService → CatalogApplicationService → StoresApplicationService`로 한 방향이라 순환이 없다.
- stores.md도 같은 해법을 D15로 두고 이번 범위에서는 분리하지 않는다(폐점 구현 시점에 채택). 이름(`StoreQueryService`, `create_store_port`, `create_stores_service`, `OpenOffersPort`)은 stores.md와 일치함을 확인했다(CI-1 해소).

---

## 10. 테스트 계획 (요약)

- domain: `Product`, `DiscountOffer`(등록 검증, 시간 경계, `effective_status` 표, 재고 조정 전 경우, 9999 상한), `StoreRef`, `discount_rate` 버림
- application: fake 레포지토리 3종(추상 구현), fake `StorePort`, 고정 `Clock`. #13 중간 예외 시 기존 할인이 닫히지 않음, #14의 `StockLog` 부호, `commit` 호출 횟수(쓰기 EP마다 1회)
- infrastructure(`@pytest.mark.db`): `_status_clause`와 `effective_status` 결과 일치, `find_by_store` 페이지·total, `for_update` 직렬화(동시 2건 조정)
- presentation: `app.dependency_overrides`로 `provide_catalog_service`를 fake 서비스로 바꿔 역할 401/403, 공개 목록의 `is_active=false` 제어, 에러 본문 형식 검증
- 조립: `wire_dependencies` 후 `provide_catalog_service`, `provide_store_port`가 `dependency_overrides`에 모두 매핑됐는지 확인하는 테스트 1개(R9), `(cd src && uv run python -c "import main")`로 순환 import 없음 확인(R12)

---

## 11. 모듈 밖 변경 제안 (이 문서는 쓰지 않는다)

- **`src/container.py`**(B3 해소): 골격은 이미 있다. catalog implementer는 catalog 구역(9.2절)과 `wire_dependencies` 매핑 2개(`provide_store_port`, `provide_catalog_service`), 별칭 import만 추가한다.
- `src/main.py`: `catalog.infrastructure.models`를 stores models 뒤에 import, `catalog_router` 등록. `wire_dependencies(app)` 호출은 이미 있다.
- `.claude/skills/db-schema/schema.sql`·`SKILL.md`: S1~S4, S6(승인 시) 반영 (R14)
- `docs/reference/catalog.md`: #14 403 메시지 교체, 페이지네이션 검증 오류 코드(422 → 400) 정리
- `docs/design/stores.md`: 2.4절 요구사항 반영(CI-1·CI-2 이름·서명 일치 확인됨), 폐점 구현 시 읽기/쓰기 서비스 분리(9.3절, stores.md D15)
- `tests/`: `app.dependency_overrides` 기반 테스트 픽스처(구현 단계)
- `pyproject.toml`·`error_handlers.py`·`.env.example`: 변경 없음
- auth의 container 이전은 완료되어 있다(`provide_auth_service`). 이 문서가 auth에 요구하는 변경은 없다(선택: auth 쪽 `OptionalUser` 제공, 7.1 Q-A).

---

## 12. 질문 목록과 임시 기본값 (결정 필요)

임시 기본값은 확정이 아니라 제안이다. 코드에서는 아래 위치에 모아 두어 바꾸기 쉽게 한다. D1~D20은 기존 값 그대로다(사용자 미확정). D21은 2026-11-03에 **확정**됐다. D22 이후는 임시 기본값이다.

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 | 코드 위치 |
| --- | --- | --- | --- | --- | --- |
| D1 | `discount_rate` 반올림/버림 | 명세 공통 객체 | **버림** `(원가-할인가)*100 // 원가` (정수 연산) | 포인트 정책이 "소수점 버림"이라 팀 관례와 맞음, 부동소수 오차 없음 | `DiscountOffer.discount_rate` |
| D2 | 등록 시 `status` 결정 | 명세 #7 | `sales_start > now` → `SCHEDULED`, 아니면 `ON_SALE` | 명세 제안 | `DiscountOffer.register` |
| D3 | 시간 경과에 따른 상태(스케줄러 없음) | 설계 중 발견 | **조회 시 계산**(`effective_status`), 저장 `status`는 쓰기 때 동기화 | 배치 인프라가 없음 | `effective_status`, `_status_clause` |
| D4 | "진행 중인 할인" 정의 (#5, #6, #7, 폐점) | 명세 #5·#6·#7 | `is_active and now < sales_end` (유효 상태 SCHEDULED/ON_SALE/SOLD_OUT) | 판매가 끝나 픽업만 남은 할인이 다음 날 할인 등록을 막지 않게 | `DiscountOffer.is_open` |
| D5 | 재고 0 ↔ `SOLD_OUT`/`ON_SALE` 전환 | 명세 #14 | 0이 되면 `SOLD_OUT`, 0에서 늘면 `ON_SALE`(시작 전이면 `SCHEDULED`) 자동 | 명세 제안 + `is_sold_out` 계산 값과 일치 | `adjust_stock` |
| D6 | 공개 목록의 `is_active=false` | 명세 #2 | 기본은 활성만. `false` 요청은 해당 상점 소유자만(비로그인 401, 타인 403) | 명세 제안 | `list_products`, router |
| D7 | 비활성 상품 상세 노출 | 명세 #4 | 소유자 외에는 404 | D6과 일관 | `get_product` |
| D8 | #14 누락 에러 | 명세 #14 | 초과 차감 400 `INSUFFICIENT_STOCK`; `amount=0` 400; 중단된 할인(`is_active=false`) 400 `OFFER_CLOSED`(시간만 지난 건 허용); 증가 후 `initial > 9999` 400; 403 문구 "본인 상점의 재고만 조정할 수 있습니다." | 명세 제안 + 최초 수량 상한 1~9999 | 도메인 `adjust_stock` |
| D9 | 폐점·미승인 상점 에러 문구 | 명세 #1 확인 필요 | "폐점된 상점에서는 {상품/할인}을 등록할 수 없습니다." (400 `STORE_CLOSED`), 미승인은 명세 문구 그대로. 할인 등록·재등록에도 같은 검사 적용 | stores 명세 "폐점된 상점에서는 상품 및 할인 판매를 등록할 수 없다" | `StoreRef.ensure_can_register` |
| D10 | 시간 규칙 보강 | 명세 #7 | `sales_end > now` 필요, `pickup_end >= sales_end`(같아도 허용), `pickup_start`와 `sales_end` 사이 제약 없음(명세 예시가 겹침) | 명세 예시·에러 문구 | `DiscountOffer.register` |
| D11 | 재등록 규칙 | 명세 #13 | 기존 할인이 `is_active=true`이면 시간이 지났어도 재등록 가능. 기존 건의 `remaining_stock`은 유지, 기존 예약은 그대로, 신규 건에 `+initial` 로그. 상품 활성·상점 미폐점 필요 | "기존 예약은 유지" | `relist_offer` |
| D12 | `reason` 저장 | 명세 #14, 스키마 | `stock_log.reason` 컬럼 추가(S2). 최초 입고 사유는 `"최초 입고"` | 명세 요청 사항 | `StockLog`, S2 |
| D13 | 상품 재노출 API | 명세 #6 | 1차에서 만들지 않음 | 범위 외 | - |
| D14 | 형식 오류 코드와 페이지네이션 | README 공통 3·5번 | 전역 핸들러대로 400 `VALIDATION_ERROR`; `page` 1부터, `size` 1~100, 응답 `items,page,size,total` | `error_handlers.py`, 명세 | `schemas.py`(Query 제약) |
| D15 | 상품 목록 정렬 | 명세에 없음 | `name ASC, id ASC` (`created_at` 컬럼 승인 시 최신순 `created_at DESC, id`) | 컬럼이 없음(S6) | `SqlAlchemyProductRepository.find_by_store` |
| D16 | PATCH에서 null | 명세 #5 | `category`, `description`은 null로 비우기 허용. `name`, `original_price`, `product_image`는 null 거부 | 필수 값 | `Product.apply_changes` |
| D17 | 비활성 상품·폐점 상점의 상품 수정 | 명세 #5 | 허용 | 제한 규칙이 명세에 없음 | `update_product` |
| D18 | 이미지 URL 검증 | 명세 #1 | 개수(≤10)와 공백 아님만 검사, URL 형식·길이 검증 안 함 | 명세에 없음 | `Product` |
| D19 | 상점주 역할 값, 승인 상태 저장 | auth 명세 7번, 스키마 5절 | 역할 `OWNER`(이미 코드에 있음). 승인 판단은 상점 `approval_at` 유무 | 명세 예시, 기존 auth 코드 | `Role.OWNER`, `StoreRef.approved` |
| D20 | 스키마 변경 S1~S4, S6 승인 | 4절 | S1·S3·S4는 `models.py`에 반영, S2 채택, S6 보류 | 4절 | `models.py` |
| D21 | 시계 주입 방식 | R8, layer-architecture §5.2 | **확정(2026-11-03, 사용자 결정).** `Clock`(ABC)은 **모듈별로 둔다**(catalog는 자기 모듈 `domain/service.py`). 공용 `src/common/`에 두지 않는다. infrastructure `SystemClock`을 container 싱글턴으로 서비스 생성자에 필수 인자로 주입. 이전의 `Callable` 기본값 방식은 폐기. **stores.md D13과 동일 결정** | 시계는 기술 의존 기능이라 추상화 대상(§5.2), 기본 구현체 생성 금지(R8), 모듈 독립성 | `domain/service.py`, `infrastructure/clock.py`, container catalog 구역 `_catalog_clock` |
| D22 | stores 폐점 연계 시 생성 순환 해법 (신규) | R12, stores.md C3 | stores를 읽기 전용 `StoreQueryService`와 쓰기 서비스로 분리, catalog의 `StorePort`는 읽기 전용 서비스가 구현(9.3절). 1차 범위는 stores 서비스 하나로 충분. **값은 임시 그대로이며 stores.md D15와 동일 결정이다**(상호 참조) | 생성자 안에서 서로를 만드는 방식은 R12 위반, 팩토리 단방향 | container `create_store_port` |
| D23 | 서비스 입력 사용자 타입 (신규) | R11 | 서비스는 `user_id: UUID`만 받고 auth의 `User`·예외를 import하지 않는다. 비로그인 401은 router가 낸다 | auth 도메인에 의존하지 않기 위함 | `CatalogApplicationService`, router |
| D24 | 레포지토리 추상 배치 (신규) | layer-architecture §5.1 | 애그리거트 3개라 `domain/repository/<애그리거트>_repository.py`로 나눔, 구현체는 `infrastructure/repositories.py` 한 파일 `SqlAlchemy*` | §5.1 "애그리거트가 여럿이면 나눈다" | 1절 |

차단 여부(2026-11-03 3차): B1·B3은 해소되었다. 남은 차단은 없고, B2(스키마 변경 승인)만 `models.py` 확정을 좌우한다(미승인 시 임시 기본값으로 진행). D1~D20, D22~D24는 임시 기본값(확정 아님)으로 진행 가능하고, D21은 확정이다.

---

## 13. 정합 이슈

### 13.1 stores.md 9절 C1~C7의 처리

| stores 이슈 | 처리 | 이유 |
| --- | --- | --- |
| C1 (StoreInfo에 좌표 없음) | 미해소(후속) | #8 구현 때 `StoreInfo`에 `latitude`, `longitude`를 추가한다. 상위 호환이라 1차에는 영향 없음 |
| C2 (단방향 표현) | **해소** | 양쪽 application이 서로 import하지 않고, 연결은 container만 한다(9.1절). "stores → catalog 단방향" 표현은 쓰지 않는다. 9절 다이어그램의 `stores.application → catalog.application` 화살표 삭제 |
| C3 (생성 순환) | **해소(조건부)** | container 팩토리 한 방향 구조(9.3절). 폐점 구현 시 stores 읽기/쓰기 서비스 분리(D22)가 필요하며, stores.md가 이를 수용해야 완전히 닫힌다(CI-1) |
| C4 (stores 범위 확대) | 영향 없음 | catalog는 stores의 개설 API 유무와 무관하게 `StorePort`만 사용 |
| C5 (`StoreNotFoundError` 이름 중복) | 유지 | 서로 다른 모듈의 별개 클래스. catalog는 stores 예외를 import하지 않음(R11) |
| C6 (API 개설 상점은 항상 승인) | 영향 없음 | catalog `StoreRef`는 `approval_at` 유무만 검사(D19) |
| C7 (폐점 차단의 "진행 중" 정의) | 유지 | `has_open_offers_for_store`가 D4 정의를 그대로 공유(2.3절) |

### 13.2 새 정합 이슈

| # | 상태 | 위치 | 이슈 | 영향 | 제안 |
| --- | --- | --- | --- | --- | --- |
| CI-1 | **해소(이름 정합, 3차에서 실제 코드로 재확인)** — 2026-11-03 | 2.2, 9.2, 9.3 ↔ stores.md 4절·5.1절·8절 | 병렬 갱신 중인 stores 설계와 이름·구조가 어긋날 수 있었다. 오케스트레이터가 stores.md 갱신본의 이름(`provide_store_port`, `create_store_port`, `create_stores_service`, `OpenOffersPort`, `StoreQueryService`)이 이 문서와 일치함을 확인했다 | 이름 불일치로 구현자가 임의로 맞출 위험은 없어졌다 | 기준 구조(catalog가 `StorePort`와 `provide_store_port`·`provide_catalog_service`를 선언, container의 `create_store_port`가 stores 서비스 인스턴스를, `create_catalog_service`가 `Depends(create_store_port)`를 받음)를 유지. 읽기/쓰기 서비스 분리의 시점(폐점 구현 때)은 stores.md D15와 D22가 같다. 실제 코드 확인: `create_stores_service`, `provide_stores_service`, `provide_store_repository`가 있고(`src/container.py:68,80,79`), `provide_store_port`·`create_store_port`·`OpenOffersPort`·`StoreQueryService`는 아직 없다(catalog가 추가하거나 후속) |
| CI-2 | **해소(확정)** — 2026-11-03 | 2.3 ↔ stores.md 8절 | `has_open_offers_for_store`의 `now` 인자 서명이 두 문서에서 다를 수 있었다 | 서명이 다르면 구조적 만족이 깨져 container 연결에서 타입 오류 | **확정 서명 `has_open_offers_for_store(store_id, *, now=None) -> bool`(`now`는 키워드 전용).** catalog 서비스는 `now`가 None이면 주입된 `Clock`으로 현재 시각을 얻는다. 두 문서 모두 이 서명을 쓴다 |
| CI-3 | 유지 | 6.1, 6.3, 7.1 | 이전 설계는 application이 `auth.domain.exceptions.AuthenticationError`를 import해 비로그인 401을 냈고 서비스가 auth의 `User`를 받았다(R11 위반 소지). 갱신 설계는 서비스가 `user_id`만 받고 401은 router가 낸다. 대신 router가 `is_active=false` 조건을 알아야 한다 | router에 약한 규칙 지식(비활성 조회는 로그인 필요)이 남는다 | 규칙 자체(소유자만)는 서비스·도메인(`NotStoreOwnerError`)에 있고 router는 인증 여부만 판단한다. 팀이 router 분기를 원하지 않으면 `is_active=false` 목록을 별도 EP(`OwnerUser`)로 분리하는 안을 명세 변경으로 논의 |
| CI-4 | **해소** — 2026-11-03 3차 | 7.1 | 이전 설계는 auth가 `get_auth_service` 방식이라고 가정했다. 실제로는 auth가 container 방식이다 | 근거: `src/auth/presentation/dependencies.py:13` `provide_auth_service`, `src/container.py:17,47,78`. `OptionalUser`는 `provide_auth_service`를 쓰도록 7.1에서 교체했다 | 남은 확인은 Q-A(presentation의 타입 import가 계층 검사에 걸리는지)뿐이다 |
| CI-5 | 유지 | 3.7, 5.2 | 시간 의존 코드(`effective_status`, `_status_clause`)는 `Clock`과 DB `now()` 두 출처를 섞으면 안 된다 | DB 시각과 앱 시각이 어긋나면 상태 필터와 응답 값이 불일치 | 레포지토리 쿼리는 항상 인자로 받은 `now`(Clock 값)만 사용하고 SQL `now()`를 쓰지 않는다. 테스트로 확인(10절) |

---

## 14. 2026-11-03 갱신 이력 (변경 위치)

| 항목 | 위반·변경 | 반영 절 |
| --- | --- | --- |
| V3 (R9) | router에서 서비스·stores 서비스를 조립하던 서술 삭제 → `provide_catalog_service`/`provide_store_port` + container 팩토리 | 2.2, 7.1, 9.1, 9.2 |
| V2 (R8) | 레포지토리 3개를 domain ABC(`domain/repository/`)와 `SqlAlchemy*` 구현체로 분리 | 1, 3.6, 5.2, D24 |
| V1 (R8) | 서비스 생성자의 `\| None` 기본값·`or 구현체` 제거, 모든 인자 필수, `clock`을 `Clock` ABC로 교체 | 3.7, 6.1, D21 |
| V5 (§6.1, §7.4) | `presentation/dependencies.py`에 `provide_catalog_service`, `provide_store_port` 추가 | 1, 7.1 |
| V6 (R9, R11, R12) | stores 폐점 ↔ catalog 호출을 container 팩토리 기준으로 재기술, 생성 순환 해법 | 2.3, 9.1, 9.3, 13.1 |
| 참고 | `src/container.py` 부재를 B3으로 명시, 모듈 밖 변경 제안 | 0, 9.2, 11 |
| 새로 찾은 위반 | 서비스가 auth `User`·`AuthenticationError`를 import(R11) → `user_id` 입력, 401은 router | 6.1, 6.3, 7.1, D23, CI-3 |
| 새로 찾은 위반 | 서비스 시계가 `Callable` 기본값(R8) → `Clock` | 6.1, D21 |
| 새로 찾은 위반 | 6.4 "서비스를 만들어" 서술(R12 소지) → container 주입 | 6.4 |
| 새로 찾은 위반 | 테스트 계획에 조립·`dependency_overrides` 검증 없음(R9) | 10 |

### 2차 갱신 (사용자 확정 결정 반영)

| 항목 | 변경 | 반영 절 |
| --- | --- | --- |
| D21 | 임시 → **확정**. `Clock` ABC는 모듈별(공용 `src/common/` 사용 안 함). stores.md D13과 상호 참조 | 1, 3.7, 12(D21) |
| B3 | 해결 방법 확정: stores implementer가 `src/container.py` 골격을 먼저 만들고(stores.md D14), catalog implementer는 catalog 구역만 추가. 구현 순서 stores → catalog | 0(B3), 9.2, 11, 12 |
| CI-1 | 이름 정합 부분 해소(`provide_store_port`, `create_store_port`, `create_stores_service`, `OpenOffersPort`, `StoreQueryService` 일치 확인) | 2.4, 9.3, 13.2 |
| CI-2 | 해소: `has_open_offers_for_store(store_id, *, now=None) -> bool` 확정 | 2.3, 13.2 |
| CI-4 | 상태를 "범위 밖, 별도 작업"으로 갱신. auth 이전 전까지 catalog는 auth의 현재 인증 의존성을 그대로 사용 | 0, 7.1, 11, 13.2 |
| D22 | 값은 임시 그대로. stores.md D15와 동일 결정이라는 상호 참조만 추가 | 9.3, 12(D22) |

### 3차 갱신 (main의 stores 구현·auth container 이전 반영)

| 항목 | 변경 | 반영 절 |
| --- | --- | --- |
| B1 | stores 구현됨 → 해소. 근거 `StoreModel`, `find_store_by_id`, `find_stores_by_ids` | 0(B1), 2.4 |
| B3 | container·`wire_dependencies` 호출 존재 → 해소. 남은 일은 catalog 구역 추가 | 0(B3), 9.2, 11, 12(차단 여부) |
| CI-4 | `get_auth_service` 가정 폐기, `provide_auth_service` 기준으로 해소 | 0(차단 아님 목록), 7.1, 11, 13.2 |
| `OptionalUser` | `get_optional_user`를 `provide_auth_service` 기반으로 재설계 | 7.1 |
| 2.1 | 실제 `Store` 필드와 `StoreInfo`/`StoreRef` 대조 표, 메서드 위치 | 2.1, 2.4 |
| 9.2 | 실제 container 구조 반영: 이미 있는 이름(`SystemClock`는 stores 것, `_stores_clock`), catalog는 `CatalogSystemClock`·`_catalog_clock` 별칭, 매핑 위치 | 9.2, 12(D21 코드 위치) |
| 9.3 | stores 서비스가 아직 단일 서비스임을 현재 상태로 명시 | 9.3, 13.2(CI-1) |
| 확인 | `src/catalog/**`는 아직 전부 0바이트, `import main` 성공, `schema.sql`·4절 S1~S4 일치 재확인 | 0 |
| 변경 없음 | EP 9개, D1~D24 값 | - |
