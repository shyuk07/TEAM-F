# catalog 모듈 설계안

- 대상: `src/catalog` (products, discount_offers, stock_log)
- 기준 문서: `docs/reference/catalog.md`, `.claude/skills/db-schema/schema.sql`, `.claude/skills/backend-invariants`(R1~R16), `.claude/skills/layer-architecture`(§3.4, §5~§8), `.claude/skills/layer-implementation`
- 범위 EP 14개: #1 상품 등록, #2 상점 상품 목록, #3 상품 검색(`GET /v1/products`, 14절), #4 상품 상세, #5 상품 수정, #6 상품 노출 중단, #7 할인 등록, #8 주변 할인 목록(`GET /v1/offers`, 14절), #9 상점 할인 목록, #10 할인 상세, #11 할인 수정, #12 할인 판매 중단, #13 할인 재등록, #14 재고 수동 조정. #3·#8의 설계는 14절에 모았고, 결정은 D59~D77, 열린 질문은 Q30~Q44(Q30은 닫힘), 정합 이슈는 CI-12~CI-15·C15이다. 2026-11-06 확정된 할인 요구 조건(`docs/requirements/catalog-offers.md`) 반영분은 D81~D87, Q45~Q47(Q45·Q46은 닫힘), CI-16~CI-17이다(REQ-17 예약 판정 범위, #9·#10 공개 범위, 상태 판정 순서, 정지 상점의 할인 재개, 정지 사유 상한). 커밋 e133e13 반영분은 D86·D87·Q47
- 번호는 `docs/reference/catalog.md`의 절 번호이고, `docs/reference/README.md` 표에서는 #10(할인 상세)이 17번 행, #12(할인 판매 중단)가 19번 행이다.
- "임시"로 표시한 결정은 확정이 아니라 제안이며 12절 표에 모았다. 단 D59~D77·Q30~Q44는 2026-11-06 사용자가 확정했다("그대로 진행").

---

## 0. 차단 이슈

차단 이슈는 없다. 확인한 명령과 결과:

| 확인 | 명령 | 결과 |
| --- | --- | --- |
| 코드 로딩 | `(cd src && uv run python -c "import main")` | 성공 |
| 계층 규칙 | `python3 .claude/skills/layer-check/check_layers.py` | 위반 없음 (경고 3건은 `error_handlers.py`의 광범위 예외 핸들러로 catalog와 무관) |
| 의존성 | `uv run python -c "import jwt, passlib, sqlalchemy, asyncpg, pydantic"` | 추가 의존성 없음. 요청은 전부 JSON이라 `python-multipart`도 필요 없다 |
| 환경변수 | `.env.example` | catalog가 새로 요구하는 키 없음 |
| 마이그레이션 | Alembic 폴더 없음(`create_all` 방식) | 컬럼이 바뀌면 이미 만들어진 개발 DB를 다시 만들어야 한다 |
| 인증 | `OwnerUser`(`Role.OWNER`)는 auth에 있다 | 상점주 역할 값은 `OWNER` |

유지해야 하는 제약:

| # | 제약 | 근거·대응 |
| --- | --- | --- |
| B1 | catalog `models.py`는 stores 모델 클래스를 import하지 않고 `ForeignKey("stores.id")` 문자열만 쓴다. `main.py`에서 catalog models는 stores models **뒤**에 import한다 | 순서가 어긋나면 `create_all`이 `NoReferencedTableError`를 낸다. `src/main.py:15,19` |
| B4 | `src/reservations/**`·`src/payments/**`는 구현되지 않았다(파일 크기 0). 예약 존재 확인과 예약 일괄 취소는 catalog가 정의한 포트와 임시 구현(항상 0건)으로 연결돼 있다 | 3.1, 6.4, 9.2, CI-10, CI-11 |

---

## 1. 모듈 구성

```
src/catalog/
  domain/
    exceptions.py            # 예외
    store_ref.py             # StoreRef (stores에서 받은 값의 읽기 전용 복사본, 좌표 포함)
    product.py               # Product
    discount_offer.py        # DiscountOffer, OfferStatus, CancelPolicy, OPEN_OFFER_STATUSES, 취소 정책·안내 문구 상수
    stock_log.py             # StockLog
    search.py                # SearchArea, OfferSort, normalize_keyword, 검색 상수 (#3·#8, 14.2절)
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
    reservation_lookup.py    # NoReservationLookup — 임시 구현 (D28, CI-10)
    reservation_cancel.py    # NoReservationCancel — 임시 구현 (D42, CI-11)
  application/
    ports.py                 # StorePort(+find_visible_stores), StoreInfo, StoreWithDistance, ReservationLookupPort, ReservationCancelPort (Protocol)
    views.py                 # OfferView, OfferDetailView, ProductDetailView, StockAdjustResult, DeactivateOfferResult, Page, StoreSearchHit, SearchedProduct, NearbyOfferView
    service.py               # CatalogApplicationService
  presentation/
    dependencies.py          # provide_catalog_service, provide_store_port, provide_reservation_lookup, provide_reservation_cancel, OptionalUser
    schemas.py
    router.py
```

- 레포지토리는 애그리거트 루트(Product, DiscountOffer, StockLog)마다 하나라서 `domain/repository/<애그리거트>_repository.py`로 나눈다(layer-architecture §5.1, D24). 구현체 이름은 `SqlAlchemy<추상명>`(§5.3).
- `Clock`은 시계라는 기술 의존 기능이므로 domain에 추상, infrastructure에 구현체를 둔다(§5.2, R8, D21). `Clock` ABC는 모듈별로 두며 공용 `src/common/`에 두지 않는다.
- 조립은 모듈 밖 `src/container.py`가 한다(9.2절). 모듈 안에는 구현체를 만드는 코드가 없다.

---

## 2. stores 연계: 최소 인터페이스와 의존 방향

### 2.1 catalog가 stores에서 필요한 것

| 필요 | 쓰는 곳 | stores가 제공하는 것 |
| --- | --- | --- |
| 상점 존재 확인 | #1, #2, #9 | `find_store_by_id(store_id) -> StoreInfo \| None` (`StoresApplicationService.find_store_by_id`, 없으면 `None`) |
| owner 확인 | #1, #5, #6, #7, #11, #12, #13, #14 | `StoreInfo.owner_id` |
| 승인 여부 | #1, #7, #13 | `StoreInfo.approval_at is not None` |
| 폐점 여부 | #1, #7, #11(재개), #13 | `StoreInfo.closed_at is not None` |
| `store_name`, `pickup_address` 조인 | #4, #7(응답), #9, #10, #11·#12·#13(응답) | `StoreInfo.name`, `StoreInfo.pickup_address` |
| 상점 좌표 | #10 | `StoreInfo.latitude`, `StoreInfo.longitude` (`float \| None`) |
| 여러 상점 일괄 조회 | (쓰지 않음) | `find_stores_by_ids(ids) -> list[StoreInfo]` (#3·#8은 14.3절의 `find_visible_stores`를 쓴다. 노출 상태 필터와 거리 계산을 id 목록 조회로는 할 수 없다, D65) |
| 노출 가능한 상점 + 거리 | #3, #8 | `find_visible_stores(latitude, longitude, radius_km) -> list[StoreWithDistance]` (14.3절. **stores 쪽 신규 메서드 필요**, 11절) |

실제 `Store`(`src/stores/domain/store.py`)와 포트·`StoreRef` 대조:

| `StoreInfo`/`StoreRef` 필드 | 실제 `Store` | 판정 |
| --- | --- | --- |
| `id: UUID \| None` | `id: UUID \| None` | 일치 |
| `owner_id: UUID`, `name: str`, `pickup_address: str` | 같은 이름·타입 | 일치 |
| `approval_at`, `closed_at: datetime \| None` | 같은 이름 | 일치 |
| `StoreRef.approved` / `closed` | `Store.is_approved` / `is_closed`(프로퍼티) | catalog는 `approval_at`/`closed_at` 유무로 계산하므로 stores의 프로퍼티에 의존하지 않음 |
| `latitude`, `longitude: float \| None` | `float \| None` (`src/stores/domain/store.py`, 둘 다 있거나 둘 다 없음) | 일치. `StoresApplicationService.find_store_by_id`가 `Store` 도메인 객체를 그대로 돌려주므로(`src/stores/application/service.py`) stores 변경 없이 구조적으로 만족한다(C1) |

`Store.ensure_owned_by`(stores 쪽)는 stores 예외를 낸다. catalog `StoreRef.ensure_owner`는 catalog 자기 예외를 내므로 stores 메서드를 호출하지 않는다(R11, C5).

### 2.2 의존 방향: 포트(Protocol)는 catalog가 정의하고 연결은 `src/container.py`가 한다

- `catalog/application/ports.py`에 `StoreInfo`(필드 `id, owner_id, name, pickup_address, latitude, longitude, approval_at, closed_at`)와 `StorePort`(`find_store_by_id`, `find_stores_by_ids`)를 `typing.Protocol`로 정의한다. 쓰는 쪽이 포트를 정의하는 방식이다(layer-architecture §3.4, R11).
- stores의 서비스가 같은 이름의 메서드를 제공하고 반환하는 `Store`가 위 필드를 가지므로, catalog는 stores를 import하지 않고 구조적으로 맞춘다.
- 조립: `catalog/presentation/dependencies.py`의 `provide_store_port() -> StorePort`를 container의 `create_store_port`가 stores 서비스 인스턴스로 연결한다. `CatalogApplicationService`는 생성자에서 `StorePort`를 필수 인자로 받는다. router는 `provide_catalog_service`만 쓴다(R9). 같은 요청 세션을 공유한다(`Depends(get_db)`, R13).
- catalog application은 받은 `StoreInfo`를 `StoreRef`(domain, 값 복사)로 바꿔서 쓴다. 상점주 확인·승인·폐점 판단은 `StoreRef` 메서드에 둔다(R3).
- 테스트에서는 `StorePort`를 만족하는 fake 객체를 생성자에 넣어 DB 없이 서비스를 검증한다.

### 2.3 catalog가 stores에 제공하는 것 (역방향, 엔드포인트 없음)

`CatalogApplicationService.has_open_offers_for_store(store_id, *, now=None) -> bool` — stores 폐점 시 사용한다(CI-2). `now`는 키워드 전용이며 생략하면 주입된 `Clock`으로 현재 시각을 얻는다. 레포지토리 쿼리 `exists_open_by_store`가 "진행 중"(D4) 정의를 #5·#6·#7·#11과 공유한다.

stores는 이 메서드를 자기 쪽 포트(`OpenOffersPort`, stores.md 8절)로 받는다. catalog 서비스가 구조적으로 만족하므로 catalog는 stores 포트를 import하지 않는다. 폐점 구현은 후속이며 생성 순환 해법은 9.3절(D22)이다.

상점주 승인 상태(`users`에 저장할 곳 없음)는 stores/auth의 미결 사항이라 catalog는 "상점 `approval_at` 유무"만 본다(D19).

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
| `StoreNotApprovedError` | `ValueError` | 400 `STORE_NOT_APPROVED` | 상품·할인 등록 |
| `StoreClosedError` | `ValueError` | 400 `STORE_CLOSED` | 상품·할인 등록, 할인 재개 |
| `ProductInactiveError` | `ValueError` | 400 `PRODUCT_INACTIVE` | 비활성 상품 할인 등록, 비활성 상품의 할인 재개 |
| `OpenOfferExistsError` | `ValueError` | 400 `OFFER_ALREADY_OPEN` | 이미 진행 중인 할인이 있을 때 등록·재등록·재개 |
| `ProductAlreadyInactiveError` | `ValueError` | 400 `PRODUCT_ALREADY_INACTIVE` | #6 상품 노출 중단 |
| `ProductHasOpenOfferError` | `ValueError` | 400 `PRODUCT_HAS_OPEN_OFFER` | #6 상품 노출 중단 |
| `PickedUpReservationExistsError` | `ValueError` | 400 `PICKED_UP_RESERVATION_EXISTS`(임시 이름, Q29) | #12, 예약 일괄 취소 포트가 낸다 |
| `OfferClosedError` | `ValueError` | 400 `OFFER_CLOSED` | 중단된 할인의 재등록·재고 조정·수정·재중단 |
| `InsufficientStockError` | `ValueError` | 400 `INSUFFICIENT_STOCK` | 재고 조정 시 남은 수량 초과 차감 |
| `OfferEndedError` | `ValueError` | 400 `OFFER_ENDED` | 판매 마감이 지난 할인의 #11 중단·재개 |
| `OfferHasReservationsError` | `ValueError` | 400 `OFFER_HAS_RESERVATIONS` | 예약이 있는 할인 정보 수정 |
| `OfferAlreadyActiveError` | `ValueError` | 400 `OFFER_ALREADY_ACTIVE` | 이미 활성인 할인 재개 |

`ValueError` 하위는 전역 핸들러가 400 + 클래스의 `error_code`로 바꾼다. 그 외 입력 검증은 단순 `ValueError`(400 `VALIDATION_ERROR`). 409가 없으므로 `error_handlers.py` 수정은 필요 없다. domain·application·router에서 `HTTPException`을 만들지 않는다(R6).

### 3.2 StoreRef (값 객체, 읽기 전용)
- 속성: `id, owner_id: UUID, name: str, pickup_address: str, latitude: float | None, longitude: float | None, approved: bool, closed: bool`
- `StoreRef.from_info(info)`: `latitude`·`longitude`는 값을 그대로 복사, `approved = info.approval_at is not None`, `closed = info.closed_at is not None`
- `is_owned_by(user_id)`: `user_id`가 None이 아니고 `owner_id`와 같으면 True
- `ensure_owner(user_id, message)`: 다르면 `NotStoreOwnerError(message)`
- `ensure_can_register(what: str)`: 폐점이면 `StoreClosedError("폐점된 상점에서는 {what}을 등록할 수 없습니다.")`, 정지(`suspended`)면 `StoreSuspendedError("관리자에 의해 정지된 상점입니다.")`(400 `STORE_SUSPENDED`), 미승인이면 `StoreNotApprovedError("승인되지 않은 상점에는 {what}을 등록할 수 없습니다.")` (`what`은 "상품" 또는 "할인"). 검사 순서는 폐점 → 정지 → 미승인(D9, admin D17, D86). 할인 등록(#7)·재등록(#13)이 정지 상점에서 막히는 것은 코드(`store_ref.py:81-88`)가 이미 한다.
- `ensure_not_closed(action)`: 이미 등록된 대상에 대한 동작용. 폐점이면 `StoreClosedError("폐점된 상점에서는 {action}할 수 없습니다.")`. 미승인은 검사하지 않는다. 정지는 보지 않는다(D86 이후 할인 재개는 이 메서드를 쓰지 않고 아래 `ensure_can_resume`를 쓴다).
- `ensure_can_resume()` (신규, D86): 폐점이면 `StoreClosedError("폐점된 상점에서는 할인을 재개할 수 없습니다.")`(400 `STORE_CLOSED`, 현재와 같은 문구), 정지면 `StoreSuspendedError("관리자에 의해 정지된 상점입니다.")`(400 `STORE_SUSPENDED`, 기존 예외 재사용). 순서는 폐점 → 정지. 미승인은 검사하지 않는다.

### 3.3 Product
| 속성 | 타입 | 규칙 |
| --- | --- | --- |
| `id` | `UUID \| None` | 저장 전 None |
| `store_id` | `UUID` | |
| `name` | `str` | 앞뒤 공백 제거 후 1~200자 |
| `category` | `str \| None` | 공백 제거 후 1~80자(빈 문자열은 오류) |
| `description` | `str \| None` | |
| `original_price` | `int` | 0보다 큼 ("정상 가격은 0보다 커야 합니다."). `bool` 거부 |
| `is_active` | `bool` | 기본 True |
| `product_image` | `list[str]` | 최대 10개("이미지는 최대 10개까지 등록할 수 있습니다."), 항목은 공백 아닌 문자열. 내부에 복사본 저장 |

메서드:
| 메서드 | 동작 | ValueError 조건 |
| --- | --- | --- |
| `Product.register(store_id, name, original_price, category=None, description=None, product_image=None)` | 생성자 호출, `is_active=True` | 생성자 검증 |
| `apply_changes(changes: dict, open_offer_sale_price: int \| None)` | `changes`는 보낸 키만 포함. 허용 키 `name, category, description, original_price, product_image`. 모두 검증한 뒤 한꺼번에 반영한다. 값 검증은 생성자와 같은 `_validate_*` 정적 메서드를 쓴다 | `changes`가 비어 있으면 "수정할 항목이 없습니다."; 허용 외 키; `name`/`original_price`/`product_image`가 None이면 검증 오류(D16); `original_price`를 바꾸는데 `open_offer_sale_price`가 있고 `new_price <= open_offer_sale_price`면 "정상 가격은 진행 중인 할인 가격보다 커야 합니다." |
| `deactivate(has_open_offer: bool)` | `is_active=False` | 이미 비활성이면 `ProductAlreadyInactiveError("이미 비활성화된 상품입니다.")`(먼저 검사); `has_open_offer`면 `ProductHasOpenOfferError("진행 중인 할인 판매가 있어 비활성화할 수 없습니다.")` |
| `ensure_active_for_offer()` | | 비활성이면 `ProductInactiveError("비활성화된 상품은 할인 등록할 수 없습니다.")` |

상태 전이: `is_active` true → false (`deactivate`)만 있다. 상품 재노출 API는 없어 메서드도 만들지 않는다(D13). #12 할인 판매 중단은 상품이 아니라 **할인**을 바꾼다.

### 3.4 DiscountOffer
`OfferStatus(StrEnum)`: `SCHEDULED, ON_SALE, SOLD_OUT, CLOSED, SUSPENDED`(`SUSPENDED`는 admin.md 3.3 추가분, 코드에 이미 있음).

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

상수: `CANCEL_LEAD_TIME = timedelta(hours=1)`(취소 가능 시각 = `pickup_start` − 이 값, D55), `OFFER_NOTICE`·`CANCEL_POLICY_DESCRIPTION`(고정 문구, D54·D55), `MAX_INITIAL_STOCK = 9999`, `OPEN_OFFER_STATUSES = (SCHEDULED, ON_SALE, SOLD_OUT)`(`is_open`(D4)과 같은 집합. 상점 할인 목록의 기본 상태 집합이며 바꾸려면 이 상수 한 곳만 고친다, D25).

생성자 불변식(저장된 데이터에도 항상 참): `sale_price > 0`; `0 <= remaining_stock <= initial_stock`; `initial_stock >= 0`; 모든 datetime은 tz-aware; `sales_end > sales_start`; `pickup_end > pickup_start`.

| 메서드 | 동작 | 예외 조건 |
| --- | --- | --- |
| `DiscountOffer.register(original_price, product_id, sale_price, initial_stock, sales_end, pickup_start, pickup_end, now, sales_start=None)` | `sales_start`가 None이면 `now`. `remaining=initial`. status = `SCHEDULED if sales_start > now else ON_SALE`. `is_active=True` | `initial_stock`가 1~9999 밖: "수량은 1개 이상 9999개 이하여야 합니다."; `sale_price <= 0`; `sale_price >= original_price`: "할인 가격은 정상 가격보다 낮아야 합니다."; `sales_end <= sales_start`: "판매 마감 시간은 판매 시작 시간 이후여야 합니다."; `sales_end <= now`(D10): "판매 마감 시간은 현재 시각 이후여야 합니다."; `pickup_end < sales_end`(D10): "픽업 마감 시간은 판매 마감 시간 이후여야 합니다."; `pickup_end <= pickup_start`: "픽업 마감 시간은 픽업 시작 시간 이후여야 합니다." |
| `effective_status(now) -> OfferStatus` | 규칙은 아래 표. 저장된 `status`가 시간 경과로 낡을 수 있어(스케줄러 없음, D3) 응답·필터·판정은 이 값을 쓴다 | |
| `is_open(now) -> bool` | "진행 중": `is_active and now < sales_end` (D4). 즉 유효 상태가 SCHEDULED/ON_SALE/SOLD_OUT | |
| `is_sold_out -> bool` | `remaining_stock == 0` | |
| `cancel_policy() -> CancelPolicy` | `CancelPolicy(cancellable_until=pickup_start - CANCEL_LEAD_TIME, description=CANCEL_POLICY_DESCRIPTION)`. 값 객체 `CancelPolicy`는 같은 파일의 불변 dataclass. 상태·시각과 무관하게 항상 계산해 돌려준다(이미 지난 시각이어도 그대로) | |
| `discount_rate(original_price) -> int` | `(original_price - sale_price) * 100 // original_price` 정수 연산, 버림 (D1) | |
| `ensure_relistable()` | | `not is_active`이면 `OfferClosedError("이미 중단된 할인은 재등록할 수 없습니다.")` |
| `close(now)` | `is_active=False`, `status=CLOSED`. #12와 #13(기존 할인 닫기)이 쓴다. `now`는 쓰지 않으므로 판매 마감이 지난 활성 할인도 통과한다(Q24) | 이미 `not is_active`면 `OfferClosedError("이미 중단된 할인입니다.")` |
| `pause(now)` | `close`와 같은 결과. #11 `is_active:false` 전용 진입점으로 마감 전 검사를 더한다 | `not is_active` → `OfferClosedError("이미 중단된 할인입니다.")`; `now >= sales_end` → `OfferEndedError("판매가 끝난 할인은 중단할 수 없습니다.")` |
| `resume(now, *, product_active, has_other_open_offer)` | `is_active=True` 후 `_sync_status(now)` | `is_active` → `OfferAlreadyActiveError("이미 활성화된 할인입니다.")`; `now >= sales_end` → `OfferEndedError("판매가 끝난 할인은 재개할 수 없습니다.")`; `not product_active` → `ProductInactiveError("비활성화된 상품의 할인은 재개할 수 없습니다.")`; `has_other_open_offer` → `OpenOfferExistsError("이미 진행 중인 할인 판매가 있습니다.")` |
| `apply_changes(changes, *, original_price, has_reservations, now) -> int` | 아래 상세. 반환값은 `initial_stock` 증감량(0이면 재고 로그 없음, D29) | 아래 |
| `adjust_stock(amount, now)` | 아래 시나리오 | 아래 |
| `_sync_status(now)` | 변경 후 `self.status = effective_status(now)` | |

도메인 메서드는 `now`를 인자로 받는다. 현재 시각은 application이 `Clock`에서 얻어 넘기므로 도메인은 시계를 직접 부르지 않는다. 포트도 모르고 `has_reservations`, `product_active`, `has_other_open_offer`를 인자로 받는다(R1, R3).

`effective_status(now)` 우선순위 (요구 조건 "상태와 전이" 판정 순서 중단 → 정지 → 마감 → 시작 전 → 품절 → 판매 중, admin.md 3.3·C6과 같다, D85):
1. `not is_active` → `CLOSED` (중단. 정지된 할인이 상점 강제 폐점 등으로 `is_active=false`가 되어도 `CLOSED`)
2. `is_suspended` → `SUSPENDED`
3. `now >= sales_end` → `CLOSED`
4. `now < sales_start` → `SCHEDULED`
5. `remaining_stock == 0` → `SOLD_OUT`
6. 그 외 `ON_SALE`

`OPEN_OFFER_STATUSES`(= SCHEDULED, ON_SALE, SOLD_OUT)는 **공개 목록의 기본 집합**이며 SUSPENDED를 넣지 않는다(admin D20). 정지 할인도 "진행 중"(`is_open`)이지만 이 상수와 `is_open`이 참인 유효 상태 집합은 SUSPENDED 만큼 다르다. 상수를 하나 더 둔다(D84): `OWNER_DEFAULT_OFFER_STATUSES = OPEN_OFFER_STATUSES + (SUSPENDED,)` — 상점주의 #9 기본 집합. 도메인 테스트는 "`is_open` 참 집합 == `OWNER_DEFAULT_OFFER_STATUSES`, `OPEN_OFFER_STATUSES` == 그 집합 − {SUSPENDED}"로 쓴다(admin C6).

`apply_changes`(D26~D29): 허용 키 `sale_price, initial_stock, sales_start, sales_end, pickup_start, pickup_end`. 검사 순서는 ① 키 검사 ② 닫힘 ③ 예약 ④ 병합값 검증이다. 모두 검증한 뒤 한꺼번에 반영하고 `_sync_status(now)`를 부른다.
- ① 빈 dict → `ValueError("수정할 항목이 없습니다.")`; 값이 None → `ValueError("{항목}은(는) null일 수 없습니다.")`; 허용 외 키 → `ValueError`
- ② `not is_active` 또는 `now >= sales_end` → `OfferClosedError("종료된 할인은 수정할 수 없습니다.")`
- ③ `has_reservations` → `OfferHasReservationsError("예약이 있는 할인은 수정할 수 없습니다. 재등록을 이용하세요.")`
- ④ 병합값(보내지 않은 필드는 기존 값) 기준으로 할인 등록과 같은 규칙: `sale_price` 정수 0 초과, `sale_price >= original_price` 거부, `initial_stock` 1~9999, 시각 aware, `sales_end > sales_start`, `sales_end > now`(D10), `pickup_end >= sales_end`, `pickup_end > pickup_start`; `remaining_stock + 증감 < 0` → `ValueError("최초 수량은 현재까지 줄어든 수량({n}개)보다 작을 수 없습니다.")`
- `initial_stock`을 바꾸면 `remaining_stock`은 같은 값으로 재설정하지 않고 증감한 만큼 더한다(D29).

`adjust_stock(amount, now)`:
- `amount == 0` → `ValueError("조정 수량은 0이 될 수 없습니다.")`
- `not is_active` → `OfferClosedError("중단된 할인은 재고를 조정할 수 없습니다.")` (시간만 지나 종료된 할인은 허용, D8)
- `amount < 0`이고 `-amount > remaining_stock` → `InsufficientStockError("차감할 수량이 남은 재고보다 많습니다.")`
- `amount > 0`: `initial_stock + amount > 9999`이면 `ValueError("최초 수량은 9999개를 넘을 수 없습니다.")`(먼저 검사, 상태 변경 전). 통과하면 `initial_stock += amount`, `remaining_stock += amount`
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
| SCHEDULED/ON_SALE/SOLD_OUT | 중단: #12 `close`, #11 `pause`, #13에서 기존 건 `close` | CLOSED (`is_active=false`) |
| SCHEDULED/ON_SALE/SOLD_OUT(판매 마감 지남) | #12 `close` | CLOSED (`is_active=false`로 바뀜, Q24) |
| CLOSED(`is_active=false`, 마감 전) | #11 `is_active:true` 재개(`resume`) | `effective_status(now)`(SCHEDULED/ON_SALE/SOLD_OUT) |
| CLOSED(`is_active=false`, 마감 지남) | 재개 | 전이 없음 (`OfferEndedError`) |
| CLOSED | 재고 조정·재등록·재중단·필드 수정 | 전이 없음 (`OfferClosedError`) |

#12로 중단한 할인도 마감 전이고, 같은 상품에 다른 진행 중 할인이 없고, 상품이 활성이고, 상점이 폐점이 아니면 #11 `is_active:true`로 되살릴 수 있다(Q19). 취소된 예약은 되살아나지 않는다.

> 후속(예약 모듈): `deduct_stock(quantity, now)` / `restore_stock(quantity, now)`를 같은 클래스에 추가한다. 예약 가능 판정은 `effective_status(now) == ON_SALE`로 한다. 지금은 만들지 않는다.

### 3.5 StockLog
- 속성: `id: UUID | None`, `offer_id: UUID`, `user_id: UUID | None`, `amount: int`(입고 +, 차감 −), `reason: str | None`(최대 200자), `created_at: datetime | None`
- 검증: `amount != 0`, `reason`은 200자 이하(공백뿐이면 None). 불변(append-only)이라 행위 메서드 없음.
- 팩토리: `StockLog.initial_stock(offer_id, user_id, quantity)` (reason `"최초 입고"`), `StockLog.manual_adjustment(offer_id, user_id, amount, reason)`, `StockLog.offer_edit(offer_id, user_id, amount)` (reason `"할인 수정"`, `amount`는 증감량 부호 그대로).

### 3.6 추상 레포지토리 (`domain/repository/`)

도메인 객체만 주고받는다(R4). 인프라 구현체는 5.2절. 서비스는 여기 선언된 메서드만 호출한다(R10).

| 추상 | 파일 | 메서드 |
| --- | --- | --- |
| `ProductRepository(ABC)` | `product_repository.py` | `find_by_id(product_id, for_update=False) -> Product \| None`; `find_by_store(store_id, *, category, is_active, page, size) -> tuple[list[Product], int]`; `save(product) -> Product` |
| `DiscountOfferRepository(ABC)` | `discount_offer_repository.py` | `find_by_id(offer_id, for_update=False) -> DiscountOffer \| None`; `find_with_product(offer_id) -> tuple[DiscountOffer, Product] \| None`; `find_open_by_product(product_id, now) -> DiscountOffer \| None`; `exists_open_by_store(store_id, now) -> bool`; `find_by_store(store_id, *, statuses, now, exposed_only, page, size) -> tuple[list[tuple[DiscountOffer, Product]], int]` (`exposed_only`는 **필수 키워드 인자**, D83); `save(offer) -> DiscountOffer` |
| `StockLogRepository(ABC)` | `stock_log_repository.py` | `add(log) -> StockLog` |

#3·#8용 추상 메서드(`ProductRepository.search_store_ids`·`find_matching_in_stores`, `DiscountOfferRepository.search_in_stores`)의 시그니처는 14.4절이다. 위 표는 현재 구현의 일부이며 14.4의 세 메서드를 더하면 기존 fake 레포지토리(ABC)도 구현해야 인스턴스를 만들 수 있다(CI-12).

### 3.7 추상 도메인 서비스 (`domain/service.py`)

```python
class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime: ...   # timezone-aware(UTC)
```
- 시간 의존 규칙(진행 중, 유효 상태, 등록 시각 검증)을 테스트에서 고정하기 위한 추상이다(D21).
- `Clock`은 catalog 모듈 domain 안에 둔다. container의 catalog 구역이 자기 모듈의 `Clock` 구현체 싱글턴을 만든다.

---

## 4. 스키마 (`schema.sql`·`db-schema` 문서는 이 문서가 고치지 않는다)

| # | 대상 | 상태 | 내용 |
| --- | --- | --- | --- |
| S1 | `products.name`, `products.original_price` | `schema.sql`에 반영됨(NOT NULL) | 명세상 필수. 도메인 불변식과 일치. `models.py`도 NOT NULL |
| S2 | `stock_log.reason` | `schema.sql`에 반영됨(`VARCHAR(200)` NULL) | #14 `reason`, 최초 입고·할인 수정 사유 저장 |
| S3 | `discount_offers.price` | `schema.sql`에 남아 있음, `models.py`는 매핑하지 않음 | `sale_price`와 중복이고 어느 API도 쓰지 않는다. 컬럼 삭제는 팀 확인 필요 |
| S4 | `discount_offers.sales_start` | `schema.sql`에 반영됨(NOT NULL) | 등록 시 항상 값 결정(기본 현재 시각). 상태 계산에 필요 |
| S5 | `discount_offers.is_active`, `status` | 변경 없음 | 두 값이 겹친다(중단 = `is_active=false` + `CLOSED`). 도메인 `close()`/`pause()`가 함께 바꾼다 |
| S6 | `products` 생성 시각 | 미채택 | `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`를 추가하면 상품 목록을 최신순으로 정렬할 수 있다. 지금은 `name ASC, id ASC`(D15) |
| S7 | "진행 중 할인 유일성" | DB 제약 불가 | "진행 중"이 `now() < sales_end`라서 부분 유니크 인덱스의 `WHERE`에 시간 조건을 쓸 수 없다. 상품 행 `FOR UPDATE` 잠금으로 직렬화(5.3절)하며 DB 유니크 제약은 없다(C11) |
| S8 | `sale_price < original_price` | 도메인 검증만 | 테이블 간 검증이라 CHECK 불가 |
| S9 | 재고 수량 상한 1~9999 | 도메인 검증만 | DB에는 `initial_stock >= 0`, `remaining_stock BETWEEN 0 AND initial_stock`만 둔다 |

---

## 5. 인프라 (infrastructure/)

### 5.1 models.py

공통: `TZ = DateTime(timezone=True)`, UUID PK `default=uuid.uuid4, server_default=gen_random_uuid()`, 다른 모듈 모델은 import하지 않고 `ForeignKey("stores.id")` 문자열만 사용(R11, R14).

| 모델 / 테이블 | 컬럼·제약 |
| --- | --- |
| `ProductModel` / `products` | `id`; `store_id UUID FK stores.id, index`; `name String(200) NOT NULL`; `category String(80) NULL`; `description Text NULL`; `original_price int NOT NULL, CHECK >= 0`; `is_active bool NOT NULL default true`; `product_image JSON`(리스트, 기본 `[]`) |
| `DiscountOfferModel` / `discount_offers` | `id`; `product_id FK products.id, index`; `sale_price int NOT NULL CHECK >= 0`; `initial_stock int NOT NULL CHECK >= 0`; `remaining_stock int NOT NULL`; `sales_start, sales_end, pickup_start, pickup_end TZ NOT NULL`; `status String(20) NOT NULL CHECK IN (...)`; `is_active bool NOT NULL default true`; 제약 `ck_offer_remaining_stock`, `ck_offer_pickup_window` (`schema.sql` 그대로) |
| `StockLogModel` / `stock_log` | `id`; `offer_id FK discount_offers.id, index`; `user_id FK users.id NULL`; `amount int NOT NULL`; `reason String(200) NULL`; `created_at TZ server_default now()` |

### 5.2 repositories.py (추상 3.6절의 구현체)
모두 도메인 객체를 반환·수신한다(R4). `commit()` 금지, `flush()`까지(R5). 생성자는 `session: AsyncSession` 하나를 받는다. `*Model`은 밖으로 내보내지 않고 `_to_domain`에서 변환한다.

`SqlAlchemyProductRepository(session)` — `ProductRepository` 구현
- `find_by_id(product_id, for_update=False) -> Product | None`
- `find_by_store(store_id, *, category=None, is_active=True, page, size) -> tuple[list[Product], int]` (`total`은 같은 필터의 `count(*)`; 정렬 D15)
- `save(product) -> Product` (신규 insert, 기존은 변경 필드 update)

`SqlAlchemyDiscountOfferRepository(session)` — `DiscountOfferRepository` 구현
- `find_by_id(offer_id, for_update=False) -> DiscountOffer | None` (`for_update=True`는 `with_for_update()`와 `populate_existing`을 함께 써서 잠금 뒤 최신 값을 읽는다)
- `find_with_product(offer_id) -> tuple[DiscountOffer, Product] | None` (#10. `discount_offers` JOIN `products` 한 번의 SELECT, 잠금 없음, 활성·상태 조건 없음)
- `find_open_by_product(product_id, now) -> DiscountOffer | None` (`is_active AND sales_end > now`, `LIMIT 1`)
- `exists_open_by_store(store_id, now) -> bool` (products 조인, 같은 모듈이라 허용)
- `find_by_store(store_id, *, statuses, now, exposed_only, page, size) -> tuple[list[tuple[DiscountOffer, Product]], int]` (products 조인, 정렬 `sales_end ASC, id ASC`). 조건(목록 쿼리와 `COUNT(*)` 쿼리가 같은 `conditions` 리스트를 쓴다, D83):
  - 항상: `ProductModel.store_id == store_id`, `or_(*[_status_clause(s, now) for s in statuses])`
  - `exposed_only=True`(비소유자)일 때 추가: `ProductModel.is_active.is_(True)`(D62와 같은 기준), `not_(_status_clause(OfferStatus.SUSPENDED, now))`(정지 할인 제외, 새 SQL을 만들지 않고 기존 절을 부정)
  - `exposed_only=False`(소유자): 위 두 조건 없음. 상품 노출 여부와 무관하게 본인 상점 할인 전부
  - 상점 폐점·정지 판정은 SQL이 아니라 서비스가 `StoreRef`로 한다(R11, 쿼리는 `stores`를 조인하지 않는다). 이 메서드를 부르는 서비스는 상점 숨김 판정을 먼저 통과해야 한다
- `save(offer) -> DiscountOffer`: 신규는 insert. 갱신 경로는 `sale_price`, `sales_start`, `sales_end`, `pickup_start`, `pickup_end`, `initial_stock`, `remaining_stock`, `status`, `is_active`를 모두 쓴다(CI-7)
- 상태 필터 SQL은 `_status_clause(status, now)` 한 곳에서 만들고 3.4의 `effective_status` 우선순위와 같은 조건을 쓴다. 두 구현이 어긋나지 않게 "같은 데이터로 두 방식 결과 비교" 테스트를 둔다(CI-5).

`SqlAlchemyStockLogRepository(session)` — `StockLogRepository` 구현
- `add(log) -> StockLog` (insert 후 `flush()`, `id`·`created_at` 채움)
- (후속) `find_by_offer(offer_id, page, size)` — 재고 이력 조회 API는 명세에 없다. 추가할 때는 추상에도 함께 선언한다.

`SystemClock` (`clock.py`) — `Clock` 구현. `datetime.now(timezone.utc)`를 돌려준다. 상태가 없어 container에서 싱글턴으로 둔다.

`NoReservationLookup`(`reservation_lookup.py`)·`NoReservationCancel`(`reservation_cancel.py`) — 예약 포트의 임시 구현(6.4절). application의 포트를 import할 수 없어(R2) 상속하지 않고 구조적으로 맞춘다.

### 5.3 동시성

| 지점 | 위험 | 대응 |
| --- | --- | --- |
| #14 재고 조정 | 예약의 재고 차감과 동시에 갱신되면 lost update | `offers.find_by_id(offer_id, for_update=True)` (`SELECT ... FOR UPDATE`). 예약 모듈도 같은 행을 같은 방식으로 잠근다 |
| #7, #13 할인 등록·재등록 | 같은 상품에 동시에 두 번 등록해 "진행 중" 할인이 2개가 됨(S7: DB 유니크 불가) | 상품 행 `products.find_by_id(product_id, for_update=True)`로 직렬화한 뒤 `find_open_by_product` 검사 |
| #6 상품 노출 중단 vs #7 할인 등록 | 중단 직후 할인이 등록되는 경합 | 둘 다 상품 행 잠금 |
| #5 가격 수정 vs #7 할인 등록 | `sale_price < original_price` 위반 | 둘 다 상품 행 잠금 |
| #11 할인 수정, #12 할인 판매 중단, #13 재등록 vs #5·#6·#7·#14·예약 | 가격·상태·재고·예약 판정이 겹침 | 할인을 잠금 없이 읽어 `product_id`를 얻고 → 상품 행 `FOR UPDATE` → 할인 행 `FOR UPDATE`(`populate_existing`) → (필요 시) 예약 포트 순서로 한다. #14는 할인 행만 잠그므로 교착 없이 대기한 뒤 `OfferClosedError`를 본다 |
| 잠금 순서(교착 방지) | | 항상 **product → offer** 순서 |
| #10 할인 상세 | 읽기 전용 | **잠금 없음**(`with_for_update()` 쓰지 않음). 할인+상품은 한 번의 JOIN SELECT라 한 시점의 값이고, 상점은 같은 세션의 별도 읽기라 상점 이름 변경과의 경합은 허용한다 |
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
        reservations: ReservationLookupPort,
        reservation_cancel: ReservationCancelPort,
    ): ...
```
- **모든 인자는 필수다.** `|` None 기본값이나 `x or 구현체(...)` 같은 기본 생성을 두지 않는다(R8, layer-architecture §5.4). `products`, `offers`, `stock_logs`, `clock`은 추상 타입이고, `stores`·`reservations`·`reservation_cancel`은 catalog가 정의한 포트다. infrastructure·stores 구현체를 import하지 않는다(R2, R11).
- 서비스 생성자 안에서 다른 서비스나 구현체를 만들지 않는다(R12). 만드는 곳은 container의 `create_*` 팩토리뿐이다.
- 테스트는 fake 레포지토리 3종·`StorePort`·두 예약 포트와 고정 `Clock`을 넘긴다.
- 서비스 메서드는 로그인한 회원을 `User` 객체가 아니라 `user_id: UUID`로 받는다. auth 도메인 엔티티를 application이 import하지 않게 하기 위해서다(R11, D23). router가 `owner.id`를 넘긴다.
- 읽기 결과 타입(`views.py`): `Page[T](items, page, size, total)`, `ProductDetailView(product, store_name, pickup_address)`, `OfferView(offer, product, store_name, status, discount_rate, is_sold_out)`(`status`는 `effective_status(now)`), `OfferDetailView(view: OfferView, description, product_image, pickup_address, latitude, longitude, notice, cancel_policy: CancelPolicy)`, `StockAdjustResult(offer, status, log_id)`, `DeactivateOfferResult(view, cancelled_reservation_count)`.
- 내부 헬퍼 `_load_store(store_id) -> StoreRef`: 포트가 None이면 `StoreNotFoundError`. `_get_product(product_id, for_update=False)`: 없으면 `ProductNotFoundError`. `_offer_view(...)`.
- `now`는 서비스 메서드 시작 시 `self.clock.now()`로 한 번만 얻어 도메인과 레포지토리에 넘긴다.
- `MAX_PAGE_SIZE = 100`은 router의 `Query(le=100)`로 막는다.

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
3. `original_price`를 바꿀 때만 `offers.find_open_by_product(product_id, now)` 조회
4. `product.apply_changes(changes, open_offer.sale_price if open_offer else None)`
5. `products.save` → `commit()`

**#6 `deactivate_product(user_id, product_id) -> Product`** (상품 노출 중단, D45)
1. 상품 `for_update` 조회 (404) → 소유 확인("본인 상점의 상품만 변경할 수 있습니다.") (403)
2. `has_open = offers.find_open_by_product(product_id, now) is not None`
3. `product.deactivate(has_open)` (400) → `products.save` → `commit()`

**#7 `register_offer(user_id, product_id, data) -> OfferView`**
1. 상품 `for_update` 조회 (404)
2. `store = _load_store(product.store_id)`; `ensure_owner(..., "본인 상점의 상품만 할인 등록할 수 있습니다.")`; `ensure_can_register("할인")`
3. `product.ensure_active_for_offer()`
4. `offers.find_open_by_product(product_id, now)`가 있으면 `OpenOfferExistsError("이미 진행 중인 할인 판매가 있습니다.")`
5. `DiscountOffer.register(original_price=product.original_price, ..., now=now)`
6. `offers.save(offer)`; `stock_logs.add(StockLog.initial_stock(offer.id, user_id, offer.initial_stock))`
7. `commit()` 한 번 → `OfferView` 반환
- 할인·재고 로그는 한 트랜잭션이다. 둘 중 하나가 실패하면 둘 다 롤백된다.

**#11 `update_offer(user_id, offer_id, changes: dict) -> OfferView`**
1. `now = clock.now()`
2. `old = offers.find_by_id(offer_id)` (잠금 없음, 404) — `product_id`를 얻기 위한 조회
3. `product = _get_product(old.product_id, for_update=True)` (404)
4. `offer = offers.find_by_id(offer_id, for_update=True)` (404)
5. `store = _load_store(product.store_id)`; `store.ensure_owner(user_id, "본인 상점의 할인만 수정할 수 있습니다.")` (403)
6. 분기(요청 본문 형태는 `OfferUpdateRequest`가 이미 보장: `is_active`가 있으면 다른 키가 없다):
   - `changes == {"is_active": False}`: `offer.pause(now)`
   - `changes == {"is_active": True}`: `store.ensure_can_resume()`(폐점 → 정지, D86; 이전에는 `ensure_not_closed("할인을 재개")`); `has_other = offers.find_open_by_product(product.id, now) is not None`(자기 자신은 `is_active=false`라 걸리지 않음); `offer.resume(now, product_active=product.is_active, has_other_open_offer=has_other)`
   - 그 외: `has_res = reservations.has_reservations_for_offer(offer.id)`; `delta = offer.apply_changes(changes, original_price=product.original_price, has_reservations=has_res, now=now)`
   - 이 분기는 어느 도메인 메서드를 부를지만 고른다. 규칙 판단은 모두 도메인 메서드 안에 있다.
7. `offers.save(offer)`; `delta != 0`이면 `stock_logs.add(StockLog.offer_edit(offer.id, user_id, delta))`
8. `session.commit()` → `OfferView`(`status`는 `effective_status(now)`)

오류 우선순위: 404(할인/상품/상점) → 403 → 400. 400은 수정이면 키 검사 → 종료·마감 → 예약 있음 → 값 검증, 재개면 상점 폐점 → 이미 활성 → 마감 → 상품 비활성 → 다른 진행 중 할인, 중단이면 이미 중단 → 마감 순이다. 다른 모듈 호출은 읽기 포트 2개(`StorePort`, `ReservationLookupPort`)뿐이고 쓰기는 catalog 자기 테이블만이다.

**#12 `deactivate_offer(user_id, offer_id, reason, cancel_reservations) -> DeactivateOfferResult`** (할인 판매 중단, D46)
1. `now = clock.now()`
2. `old = offers.find_by_id(offer_id)` (잠금 없음) → 없으면 `OfferNotFoundError()` (404)
3. `product = _get_product(old.product_id, for_update=True)` — 잠금 1: 상품(직렬화용, 상품은 바뀌지 않음)
4. `offer = offers.find_by_id(offer_id, for_update=True)` — 잠금 2: 할인. 없으면 404
5. `store = _load_store(product.store_id)`; `store.ensure_owner(user_id, "본인 상점의 할인만 중단할 수 있습니다.")` (403). `ensure_not_closed`는 부르지 않는다(폐점 상점 허용, Q14)
6. `offer.close(now)` — 이미 `is_active=false`면 `OfferClosedError`(400 "이미 중단된 할인입니다."). 포트 호출보다 먼저 해서 이미 중단된 할인의 예약을 취소하지 않는다
7. `cancel_reservations`가 true면 `cancelled = reservation_cancel.cancel_all_for_offer(offer.id, reason=reason)`. 픽업 완료 예약이 있으면 `PickedUpReservationExistsError`(400)가 나고 commit 전이라 전부 롤백된다. false면 포트를 호출하지 않는다(D41)
8. `offers.save(offer)` → `session.commit()` 한 번
9. `DeactivateOfferResult(view=_offer_view(offer, product, store.name, now), cancelled_reservation_count=cancelled)`. `view.status`는 `CLOSED`, `is_active`는 `false`

오류 우선순위(D48): 404(할인 없음) → 403 → 400 이미 중단 → 400 픽업 완료. 본문 검증 오류(`reason` 누락·201자 등)는 서비스 전에 400 `VALIDATION_ERROR`다. `products.save`·`stock_logs.add`는 호출하지 않는다(상품·재고 불변, D40). `reason`은 저장하지 않고 포트에만 넘긴다(D38).

**#13 `relist_offer(user_id, offer_id, data) -> OfferView` (단일 트랜잭션)**
1. `old = offers.find_by_id(offer_id)` (404) — `product_id`를 얻기 위한 잠금 없는 조회
2. `product = products.find_by_id(old.product_id, for_update=True)` (잠금 순서 product → offer)
3. `old = offers.find_by_id(offer_id, for_update=True)` (상태 재확인. 없으면 404)
4. `store = _load_store(product.store_id)`; `ensure_owner(..., "본인 상점의 할인만 재등록할 수 있습니다.")`; `ensure_can_register("할인")`
5. `old.ensure_relistable()` (400 "이미 중단된 할인은 재등록할 수 없습니다.")
6. `product.ensure_active_for_offer()`
7. `new = DiscountOffer.register(original_price=product.original_price, ...)` — 가격·시간 검증(400)을 기존 할인을 닫기 전에 한다
8. `old.close(now)` → `offers.save(old)` (기존 예약은 그대로 둔다. 기존 건의 `remaining_stock`과 `stock_log`는 변경하지 않음)
9. `offers.find_open_by_product(...)`가 남아 있으면(데이터 불일치) `OpenOfferExistsError` — 8번에서 기존 건을 이미 닫았으므로 정상 흐름에서는 None
10. `offers.save(new)`; `stock_logs.add(StockLog.initial_stock(new.id, user_id, new.initial_stock))`
11. **`commit()` 한 번.** 중간 예외가 나면 커밋되지 않아 기존 할인도 닫히지 않는다(세션 종료 시 롤백).

**#14 `adjust_stock(user_id, offer_id, amount, reason) -> StockAdjustResult`**
1. `offer = offers.find_by_id(offer_id, for_update=True)` (404) — **행 잠금 시작**
2. `product = _get_product(offer.product_id)`; `store = _load_store(product.store_id)`; `ensure_owner(..., "본인 상점의 재고만 조정할 수 있습니다.")` (D8: 명세의 "이력만 조회" 문구는 복사 오류로 보고 교체)
3. `offer.adjust_stock(amount, now)` (0, 중단, 초과 차감, 9999 초과, 상태 전환은 도메인)
4. `offers.save(offer)`
5. `log = stock_logs.add(StockLog.manual_adjustment(offer.id, user_id, amount, reason))` (`amount`는 요청의 부호 그대로)
6. `commit()` 한 번 (잠금 해제). 응답: `offer_id, initial_stock, remaining_stock, is_sold_out, status, log_id`
- 소유 확인을 잠금 뒤에 두는 이유는 단순함이다. 비소유자의 요청이 잠깐 행을 잡지만 곧 403으로 풀린다.

### 6.3 시나리오 (읽기)

**#2 `list_products(viewer_id: UUID | None, store_id, category, is_active, page, size) -> Page[Product]`**
1. `store = _load_store(store_id)` (404)
2. `is_active=False`를 요청하면: 소유자(`store.is_owned_by(viewer_id)`)가 아니면 `NotStoreOwnerError("본인 상점의 비활성 상품만 조회할 수 있습니다.")` (D6). **비로그인(401) 판정은 router가 한다**(7.1절, CI-3): `is_active=False`인데 `viewer`가 `None`이면 router가 `auth.domain.exceptions.AuthenticationError`를 낸다(`HTTPException`이 아니므로 R6 위반 아님, 401 형식·헤더는 전역 핸들러).
3. `products.find_by_store(...)`

**#4 `get_product(viewer_id: UUID | None, product_id) -> ProductDetailView`**
1. 상품 조회 (404) → `store = _load_store(...)`
2. `product.is_active`가 False이고 `viewer_id`가 소유자가 아니면 `ProductNotFoundError` (D7)
3. `ProductDetailView(product, store.name, store.pickup_address)`

**#9 `list_offers_by_store(viewer_id: UUID | None, store_id, statuses: Sequence[OfferStatus] | None, page, size) -> Page[OfferView]`** (서명은 현재 코드와 같다. 동작이 바뀐다, D83·D84)
1. `now = clock.now()`; `store = _load_store(store_id)` (404)
2. `store.ensure_products_visible_to(viewer_id)` — 폐점 또는 정지 상점이면 소유자 외 `StoreNotFoundError`(404, #2·#4와 같은 응답). 기존 `ensure_visible_to`(정지만)를 이 호출로 **교체**한다(D83). `StoreRef.ensure_products_visible_to`·`are_products_visible_to`의 docstring("할인 조회(#9·#10)는 is_visible_to를 그대로 쓴다")은 "#10만 `is_visible_to`"로 고친다. 메서드 이름은 유지한다(이름 변경은 호출처 #2·#4·테스트에 번지므로 하지 않는다)
3. `is_owner = store.is_owned_by(viewer_id)`
4. 허용 값 검사: `statuses`에 `SUSPENDED`가 있고 `not is_owner`이면 `OfferStatusNotAllowedError`(400 `VALIDATION_ERROR`, D84)
5. 선택 집합: `statuses`가 None이거나 비어 있으면 소유자는 `OWNER_DEFAULT_OFFER_STATUSES`, 비소유자는 `OPEN_OFFER_STATUSES`. 값을 주면 중복 제거(`dict.fromkeys`)한 그 값들(D25, D84)
6. `offers.find_by_store(store_id, statuses=selected, now=now, exposed_only=not is_owner, page=page, size=size)` → 각 항목을 `OfferView`로 변환 (`store_name`은 한 번만 조회한 값 사용)
- 소유자가 폐점·정지 상점 목록을 읽는 것은 허용이다(본인 상점은 전부 본다, 정책 표 "상점 할인 목록"). 비소유자는 4단계의 `exposed_only=True`로 노출 중 상품·비정지 할인만 SQL에서 걸러 `total`·페이지가 맞다(D65·D74와 같은 이유).

**#10 `get_offer_detail(offer_id) -> OfferDetailView`** (공개, 잠금 없음, commit 없음)
1. `now = clock.now()`
2. `found = offers.find_with_product(offer_id)` — 없으면 `OfferNotFoundError()` (404)
3. `offer, product = found`; `info = stores.find_store_by_id(product.store_id)`, `store = StoreRef.from_info(info)` — 포트가 None이면 `OfferNotFoundError()` (404 "할인 판매를 찾을 수 없습니다.", D56. FK상 정상 데이터에서는 발생하지 않는다). `_load_store`는 쓰지 않는다
4. 공개 범위(D56, admin C7, D82): **정지된 할인과 정지된 상점의 할인만** 비소유자에게 404(`store.is_visible_to(viewer_id)`, `offer.is_visible(now, viewer_is_owner=is_owner)` — 현재 코드 그대로). 할인 `is_active`·`status`(중단·마감·품절), 상품 `is_active=false`(노출 중단), 상점 폐점(`closed_at`)을 이유로 숨기지 않는다. 상태는 응답의 `offer.status`·`offer.is_active`로 표시하고 상품·상점 상태 값은 응답에 추가하지 않는다. 코드 변경 없음(요구 조건 정책 표 "할인 상세 조회"와 일치)
5. `OfferDetailView(view=_offer_view(offer, product, store.name, now), description=product.description, product_image=product.product_image, pickup_address=store.pickup_address, latitude=store.latitude, longitude=store.longitude, notice=OFFER_NOTICE, cancel_policy=offer.cancel_policy())`
- 비즈니스 계산(취소 가능 시각, 할인율, 유효 상태)은 도메인 메서드가 하고 서비스는 조합만 한다(R3). 인증을 받지 않으므로 서비스 인자에 `user_id`가 없고 router도 인증 의존성이 없다.
- 오류: 404 하나(할인 없음). 잘못된 UUID는 전역 핸들러의 400 `VALIDATION_ERROR`.

### 6.4 모듈 간 트랜잭션 경계

- catalog는 stores를 읽기만 한다(같은 요청 세션, container에서 `Depends(get_db)` 공유).
- 예약 존재 확인(읽기, #11): `ReservationLookupPort.has_reservations_for_offer(offer_id) -> bool` (D28). 포트 서명·이름은 유지한다(D81). 반환 의미만 **"취소되지 않은 예약이 한 건이라도 있으면 True"**(REQ-17: `PENDING_PAYMENT`·`RESERVED`·`PICKED_UP`만 센다, `CANCELLED`만 있으면 False)로 좁힌다. 이 판정은 reservations 어댑터가 `ReservationRepository.exists_non_cancelled_by_offer`로 한다(11절, reservations.md 2.2). 임시 구현 `NoReservationLookup`은 항상 False이며 container에서는 이미 어댑터로 교체돼 있어야 한다(C-11). 에러 코드·메시지(`OFFER_HAS_RESERVATIONS`, "예약이 있는 할인은 수정할 수 없습니다. 재등록을 이용하세요.")는 `docs/reference/catalog.md`가 정한 문구라 바꾸지 않는다(R15). #11은 할인 행을 `FOR UPDATE`로 잠근 상태에서 포트를 호출하고, 예약 생성도 할인 행을 잠그고 재고를 차감한 뒤 INSERT 해야 직렬화된다(5.3, db-schema §7, CI-10).
- 예약 일괄 취소(쓰기, #12): `ReservationCancelPort.cancel_all_for_offer(offer_id, *, reason) -> int` (D42). 임시 구현 `NoReservationCancel`은 항상 0. 계약:

| 항목 | 계약 |
| --- | --- |
| 입력 | `offer_id`, `reason`(검증된 1~200자). 취소 주체는 상점주 사유로 기록(구분 값은 reservations가 정함, Q28) |
| 반환 | 이번 호출에서 취소한 예약 수. 이미 취소된 예약은 세지 않는다 |
| 예외 | 픽업 완료(`PICKED_UP`) 예약이 하나라도 있으면 **아무것도 취소하기 전에** `PickedUpReservationExistsError`를 낸다(어댑터는 `catalog.domain.exceptions`를 import, infrastructure → domain이라 허용) |
| 트랜잭션 | **commit하지 않는다**(R5, R13). 포트에 `commit` 인자를 두지 않아 catalog가 커밋을 시키지 못하게 하고, 어댑터가 reservations·payments 서비스를 `commit=False`로 호출한다. 같은 요청 세션을 쓰고 commit은 catalog 서비스가 마지막에 한 번 한다 |
| 재고 | 닫히는 할인에 재고를 되돌리지 않는다(D40). 되돌리면 reservations가 catalog를 호출하는 순환(R12)과 닫힌 할인 재고 조정(`OFFER_CLOSED`)이 생긴다 |
| 환불 | 전액 환불 요청(위약금 0)은 reservations·payments 책임. catalog는 결과 건수만 받는다 |

- 후속(예약 연계, reservations → catalog): reservations가 container에서 `CatalogApplicationService`(또는 reservations 쪽 포트)를 주입받아 `deduct_stock(..., commit=False)`를 호출하고 마지막에 한 번 `commit()`한다(R13). 결제 실패·예약 취소 시 `restore_stock(commit=False)`. reservations 서비스는 catalog 서비스를 생성자에서 만들지 않는다(R12). 이 메서드들의 설계는 reservations 설계 때 확정한다.
- stores 폐점 → catalog `has_open_offers_for_store`는 읽기 전용이다.

---

## 7. 표현 (presentation/)

### 7.1 의존성 (`presentation/dependencies.py`)
- `provide_catalog_service() -> CatalogApplicationService`: 플레이스홀더. 본문은 `raise NotImplementedError("CatalogApplicationService 의존성이 주입되지 않았습니다.")`. router는 `Annotated[CatalogApplicationService, Depends(provide_catalog_service)]`만 쓴다(R9). router 안에서 서비스·레포지토리·stores 서비스를 조립하지 않는다.
- `provide_store_port() -> StorePort`, `provide_reservation_lookup() -> ReservationLookupPort`, `provide_reservation_cancel() -> ReservationCancelPort`: 플레이스홀더. container가 바인딩한다. 다른 곳에서 직접 쓰지는 않지만 catalog가 요구하는 포트의 주입 지점을 선언해 `wire_dependencies` 매핑에서 확인하게 한다(R9).
- `OwnerUser`를 쓴다 (`auth.presentation.dependencies`): 토큰 없음/오류 401, 역할이 `OWNER`가 아니면 403.
- `OptionalUser`(이 파일): auth의 `bearer_scheme`와 `provide_auth_service`를 쓴다. auth 파일은 수정하지 않는다.
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
  `provide_auth_service`는 auth 구역이 이미 `wire_dependencies`에 매핑해 두었으므로 catalog가 매핑을 추가하지 않는다. 같은 요청 안에서 `Depends(get_db)` 세션이 공유된다. `AuthApplicationService`·`User` 타입은 이 파일의 타입 표기에만 쓰고 catalog 서비스(application)는 `user_id`만 받는다(D23). `layer-check`는 이 import를 위반으로 잡지 않는다.
- `provide_*` 4개는 모두 `src/container.py`의 `wire_dependencies`에 매핑되어야 한다(R9, 9.2절).

### 7.2 엔드포인트 (prefix `/v1`, tags `["카탈로그"]`)

| # | Method | URI | 요청 | 응답 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | POST | `/v1/stores/{store_id}/products` | `ProductCreateRequest` | `ProductResponse` | 201 | 400(가격, 미승인·폐점 상점), 401, 403(`OWNER` 아님/본인 상점 아님), 404(상점) |
| 2 | GET | `/v1/stores/{store_id}/products` | 쿼리 | `ProductListResponse` | 200 | 400(page/size 형식), 401·403(`is_active=false` 비소유), 404(상점) |
| 3 | GET | `/v1/products` | 쿼리(14.5절) | `ProductSearchResponse` | 200 | 400(`lat`·`lng` 한쪽만, 범위·형식 `VALIDATION_ERROR`). 401·403·404 없음. 인증 없음(공개) |
| 4 | GET | `/v1/products/{product_id}` | - | `ProductDetailResponse` | 200 | 404(없음, 또는 비활성+비소유) |
| 5 | PATCH | `/v1/products/{product_id}` | `ProductUpdateRequest` | `ProductResponse` | 200 | 400(항목 없음, 할인가 이하), 401, 403, 404 |
| 6 | POST (상품 노출 중단) | `/v1/products/{product_id}/deactivate` | 없음 | `ProductResponse` | 200 | 400(이미 비활성, 진행 중 할인), 401, 403, 404 |
| 6-1 | POST (상품 재노출) | `/v1/products/{product_id}/activate` | 없음 | `ProductResponse` | 200 | 400(이미 노출 중 `PRODUCT_ALREADY_ACTIVE`, 폐점 `STORE_CLOSED`), 401, 403, 404 (D79) |
| 7 | POST | `/v1/products/{product_id}/offers` | `OfferCreateRequest` | `OfferResponse` | 201 | 400(가격·시간·비활성 상품·진행 중 할인·상점), 401, 403, 404 |
| 8 | GET | `/v1/offers` | 쿼리(14.5절) | `NearbyOfferListResponse` | 200 | 400(`lat`·`lng` 한쪽만, `distance` 정렬에 위치 없음, status·sort 허용 외, 범위·형식). 401·403·404 없음. 인증 없음(공개) |
| 9 | GET | `/v1/stores/{store_id}/offers` | 쿼리(`status` 반복 가능, 7.4절) | `OfferListResponse` | 200 | 400(status 값 등. 비소유자의 `status=SUSPENDED` 포함, D84), 404(상점 없음, 또는 폐점·정지 상점의 비소유자 조회, D83). 인증은 선택(`OptionalUser`) |
| 10 | GET | `/v1/offers/{offer_id}` | - | `OfferDetailResponse` | 200 | 400(잘못된 UUID `VALIDATION_ERROR`), 404(할인 없음). 인증 없음(공개) |
| 11 | PATCH | `/v1/offers/{offer_id}` | `OfferUpdateRequest` | `OfferResponse` | 200 | 400(항목 없음·종료·예약 있음·가격·시간·재개 조건), 401, 403, 404 |
| 12 | POST (할인 판매 중단) | `/v1/offers/{offer_id}/deactivate` | `OfferDeactivateRequest{reason, cancel_reservations}` | `OfferDeactivateResponse{offer, cancelled_reservation_count}` | 200 | 400(이미 중단, 픽업 완료 예약, `VALIDATION_ERROR`), 401, 403, 404 |
| 13 | POST | `/v1/offers/{offer_id}/relist` | `OfferCreateRequest` | `OfferResponse`(신규) | 201 | 400(이미 중단, 가격·시간), 401, 403, 404 |
| 14 | POST | `/v1/offers/{offer_id}/stock-adjustments` | `StockAdjustmentRequest` | `StockAdjustmentResponse` | 200 | 400(0, 초과 차감, 중단, 상한), 401, 403, 404 |

- 요청 형식 오류(Pydantic)는 프로젝트 전역 핸들러가 **400 `VALIDATION_ERROR`**로 바꾼다(`error_handlers.py`). 명세의 422는 반영되지 않는다(D14).
- 모든 에러 본문은 `{"success": false, "error_code", "message"}`(R7).
- 라우터는 서비스만 호출하고 예외를 잡지 않는다. 쓰기 EP는 `owner.id`를, 읽기 EP #2·#4는 `viewer.id if viewer else None`을 서비스에 넘긴다.
- 경로 충돌 없음: `GET /v1/products`(#3)와 `GET /v1/products/{product_id}`(#4)는 경로 모양이 달라(뒤 경로 세그먼트 유무) 등록 순서와 무관하다. `/v1/products/`처럼 끝에 `/`가 붙은 요청은 FastAPI가 `/v1/products`로 리다이렉트한다(`redirect_slashes`). 이 경로를 "먼저 등록"해야 한다는 이전 문구(`/v1/products/search` 시절)는 폐기했다(D59).
- 같은 경로 `/v1/offers/{offer_id}`에 #10 GET과 #11 PATCH가 공존한다. FastAPI는 경로와 메서드 조합으로 라우트를 구분하므로 두 함수를 같은 router에 등록하면 충돌하지 않고 순서도 무관하다. #8 `GET /v1/offers`(14절)도 경로가 달라 영향이 없다(`/v1/offers/{offer_id}`와 순서 무관). `/v1/offers/` 아래에 `{offer_id}` 하나를 받는 정적 경로(예: `/offers/search`)를 만들게 되면 `{offer_id}`보다 먼저 등록한다.
- #10은 `OwnerUser`·`OptionalUser`를 쓰지 않는다. 토큰이 있어도 읽지 않고 401·403이 없다(D56).
- #11과 #12는 모두 할인을 `is_active=false`, `CLOSED`로 만들 수 있다. #12는 사유·예약 일괄 취소·`{offer, count}` 응답이 있고 판매 마감이 지난 활성 할인도 중단할 수 있다. #11 중단은 마감 후 400 `OFFER_ENDED`이고 사유·예약 연계가 없다. 두 진입점은 공존한다(D53).

### 7.3 스키마 (명세 필드명 그대로)

값 검증과 에러 메시지는 도메인이 한다(명세의 400 메시지 유지). 요청 스키마는 타입과 시각 timezone 같은 형식만 막는다.

| 스키마 | 필드 |
| --- | --- |
| `ProductCreateRequest` | `name`, `category`(선택), `description`(선택), `original_price`(int), `product_image`(선택). 길이·범위·개수는 도메인 검증 |
| `ProductUpdateRequest` | 위 5개 모두 선택. 라우터는 `body.model_dump(exclude_unset=True)`를 서비스에 전달. 빈 본문 `{}`은 도메인에서 400 "수정할 항목이 없습니다." |
| `ProductResponse` | `id, store_id, name, category, description, original_price, is_active, product_image`(`from_attributes`) |
| `ProductDetailResponse` | `ProductResponse` + `store_name, pickup_address` |
| `ProductListResponse` | `items: list[ProductResponse], page, size, total` |
| `OfferCreateRequest` | `sale_price`, `initial_stock`, `sales_start`(선택), `sales_end`, `pickup_start`, `pickup_end`. datetime은 timezone 필수(naive 입력은 400) |
| `OfferUpdateRequest` | `sale_price, initial_stock, sales_start, sales_end, pickup_start, pickup_end, is_active` 모두 선택. 시각은 timezone 필수. `model_validator`: 보낸 키 중 null이 있으면 거부, `is_active`를 보내면서 다른 키도 보내면 거부(400 `VALIDATION_ERROR`). 라우터는 `model_dump(exclude_unset=True)`를 전달 |
| `OfferResponse` | Offer 공통 객체: `id, product_id, store_id, store_name, product_name, original_price, sale_price, discount_rate, initial_stock, remaining_stock, is_sold_out, sales_start, sales_end, pickup_start, pickup_end, status, is_active`(명세 `Offer`와 같은 17개). `OfferResponse.from_view(view)`. `status`는 계산 상태이고 `is_active`로 중단 여부를 구분한다 |
| `OfferListResponse` | `items: list[OfferResponse], page, size, total` |
| `CancelPolicyResponse` | `cancellable_until: datetime`(timezone 포함), `description: str` |
| `OfferDetailResponse` | 명세 #10 필드 그대로: `offer: OfferResponse`(기존 스키마 재사용), `description: str \| None`, `product_image: list[str]`, `pickup_address: str`, `latitude: float \| None`, `longitude: float \| None`, `notice: str`, `cancel_policy: CancelPolicyResponse`. `OfferDetailResponse.from_view(view)`. `description`은 상품 설명이 비어 있을 수 있어 null 허용, 좌표는 상점이 좌표 없이 개설되면 null(D57) |
| `OfferDeactivateRequest` | `reason: str`(필수, `min_length=1, max_length=200`, 공백만이면 거부하는 검증기, Q16), `cancel_reservations: bool = False`. `reason`이 필수라 본문 없는 요청은 400 `VALIDATION_ERROR` |
| `OfferDeactivateResponse` | `offer: OfferResponse`, `cancelled_reservation_count: int`. `OfferDeactivateResponse.from_result(result)` |
| `StockAdjustmentRequest` | `amount: int`(0은 도메인에서 거부), `reason: str \| None`(≤200) |
| `StockAdjustmentResponse` | `offer_id, initial_stock, remaining_stock, is_sold_out, status, log_id` |

### 7.4 목록 쿼리 매개변수

| EP | 이름 | 타입 | 기본 | 검증 |
| --- | --- | --- | --- | --- |
| #2 | `category` | str | - | 정확 일치 |
| #2 | `is_active` | bool | `true` | `false`는 소유자만(D6) |
| #2, #9 | `page` | int | 1 | `ge=1` |
| #2, #9 | `size` | int | 20 | `ge=1, le=100` |
| #9 | `status` | `list[OfferListStatus]` (반복 가능, 아래) | 비소유자: `SCHEDULED`+`ON_SALE`+`SOLD_OUT`(`OPEN_OFFER_STATUSES`, D25). 소유자: 위 + `SUSPENDED`(`OWNER_DEFAULT_OFFER_STATUSES`, D84) | 허용 외 값은 400. 유효 상태 기준 필터(여러 값은 OR). `CLOSED`는 명시할 때만. 정렬 `sales_end` 오름차순. `?status=ON_SALE` 단일 호출도 동작 |

#9 `status` 허용 값(D84): router의 타입을 `PublicOfferStatus`에서 `presentation/schemas.py`의 새 `OfferListStatus(StrEnum)`(`SCHEDULED, ON_SALE, SOLD_OUT, CLOSED, SUSPENDED`)로 바꾼다. 소유 여부는 서비스만 알 수 있으므로(router는 `OptionalUser`로 `viewer.id`만 넘김) 비소유자의 `SUSPENDED`는 서비스가 막는다: `OfferStatusNotAllowedError(ValueError)`(`catalog/domain/exceptions.py`, `error_code = "VALIDATION_ERROR"`, 메시지 임시 "status: SUSPENDED은(는) 상점주만 지정할 수 있습니다." — 기존 형식 오류 메시지 `필드: 오류`와 같은 모양, Q45) → 전역 핸들러가 400. 비소유자에게는 허용 값이 기존과 같고(`SUSPENDED`만 400) 응답 코드도 같은 400 `VALIDATION_ERROR`다. 비로그인도 비소유자와 같다. `PublicOfferStatus`는 #8이 계속 쓴다(D64).

정렬 옵션은 제공하지 않는다(명세에 #2·#9 정렬 매개변수 없음). 주변 할인 목록(#8)은 구매자 탐색용이라 기본 `ON_SALE`을 유지한다. #3·#8의 쿼리 매개변수는 14.5절.

### 7.5 에러 (#11, #12)

#11 `PATCH /v1/offers/{offer_id}`

| 상황 | 상태 | `error_code` | 메시지 |
| --- | --- | --- | --- |
| 형식 오류(null, 시각 timezone 없음, `is_active`와 다른 항목 동시) | 400 | `VALIDATION_ERROR` | `필드: 오류` |
| 빈 본문 / 시간·가격·수량 규칙 위반 / 줄어든 수량 미만 | 400 | `VALIDATION_ERROR` | 3.4절 `apply_changes` |
| 중단 또는 마감이 지난 할인 수정 | 400 | `OFFER_CLOSED` | 종료된 할인은 수정할 수 없습니다. |
| 예약이 있는 할인 수정 | 400 | `OFFER_HAS_RESERVATIONS` | 예약이 있는 할인은 수정할 수 없습니다. 재등록을 이용하세요. |
| 이미 중단된 할인 중단 | 400 | `OFFER_CLOSED` | 이미 중단된 할인입니다. |
| 마감 지난 할인 중단·재개 | 400 | `OFFER_ENDED` | 판매가 끝난 할인은 중단할 수 없습니다. / …재개할 수 없습니다. |
| 이미 활성인 할인 재개 | 400 | `OFFER_ALREADY_ACTIVE` | 이미 활성화된 할인입니다. |
| 비활성 상품의 할인 재개 | 400 | `PRODUCT_INACTIVE` | 비활성화된 상품의 할인은 재개할 수 없습니다. |
| 다른 진행 중 할인이 있을 때 재개 | 400 | `OFFER_ALREADY_OPEN` | 이미 진행 중인 할인 판매가 있습니다. |
| 정지된 상점에서 재개 | 400 | `STORE_SUSPENDED` | 관리자에 의해 정지된 상점입니다. (D86, 기존 예외 재사용) |

#11 재개(`is_active:true`) 오류 우선순위(D86, 위에서 아래로 먼저 걸리는 것): 404 할인 없음 → 403 소유자 아님 → 400 `STORE_CLOSED` → 400 `STORE_SUSPENDED` → 400 `OFFER_SUSPENDED`(`resume` 첫 검사, 정지된 할인) → 400 `OFFER_ALREADY_ACTIVE` → 400 `OFFER_ENDED` → 400 `PRODUCT_INACTIVE` → 400 `OFFER_ALREADY_OPEN`. 상점 검사가 `offer.resume` 앞에 있는 현재 순서를 유지하므로 정지된 상점의 정지된 할인은 `STORE_SUSPENDED`가 먼저 나온다(Q47).
| 폐점 상점에서 재개 | 400 | `STORE_CLOSED` | 폐점된 상점에서는 할인을 재개할 수 없습니다. |
| 토큰 없음 / 오류 | 401 | `UNAUTHORIZED`(auth 기존 값) + `WWW-Authenticate: Bearer` | 인증이 필요합니다. |
| 상점주 아님 / 본인 상점 아님 | 403 | `FORBIDDEN` | 본인 상점의 할인만 수정할 수 있습니다. |
| 할인·상품·상점 없음, 잘못된 UUID | 404 / 400 | `NOT_FOUND` / `VALIDATION_ERROR` | 할인 판매를 찾을 수 없습니다. |

#12 `POST /v1/offers/{offer_id}/deactivate`

| 상황 | 상태 | `error_code` | 메시지 | 비고 |
| --- | --- | --- | --- | --- |
| 이미 중단된 할인 | 400 | `OFFER_CLOSED` | 이미 중단된 할인입니다. | `is_active=false`인 할인. 마감 지난 활성 할인은 해당하지 않음(Q24) |
| 픽업 완료 예약이 있어 일괄 취소 불가 | 400 | `PICKED_UP_RESERVATION_EXISTS`(임시) | 픽업 완료된 예약이 있어 일괄 취소할 수 없습니다. | `cancel_reservations=true`일 때만. 임시 포트는 내지 않음 |
| `reason` 누락·201자 이상·공백만, 본문 없음, 잘못된 UUID | 400 | `VALIDATION_ERROR` | `reason: …` / `offer_id: …` | 전역 핸들러 |
| 토큰 없음 | 401 | `UNAUTHORIZED` + `WWW-Authenticate: Bearer` | 인증이 필요합니다. | R7 |
| 본인 상점 아님·상점주 아님 | 403 | `FORBIDDEN` | 본인 상점의 할인만 중단할 수 있습니다. | 폐점 상점의 할인도 허용(Q14) |
| 할인 없음 | 404 | `NOT_FOUND` | 할인 판매를 찾을 수 없습니다. | `OfferNotFoundError` 기본 메시지 |

`src/error_handlers.py`는 변경 없음(신규 예외가 모두 `ValueError` 하위). 에러 본문 형식은 R7 그대로.

---

## 8. 후속 (이번 설계 대상 아님)

- (이번 설계로 이동) #3 상품 검색 `GET /v1/products`, #8 주변 할인 목록 `GET /v1/offers` — 14절. 구현은 stores 쪽 `find_visible_stores` 추가(11절)가 먼저다.
- 상품 재노출 `POST /v1/products/{product_id}/activate` — 만들지 않는다(D13). 필요해지면 후속에서 새로 설계한다.
- `reason`(#12 중단 사유) 저장 — 컬럼 추가가 필요하다(Q22).
- reservations용 `deduct_stock/restore_stock` (6.4).

---

## 9. 조립(container)과 의존 방향

### 9.1 의존 방향 요약

```
catalog.presentation -> catalog.application -> catalog.domain
                    \-> auth.presentation.dependencies (OwnerUser, OptionalUser의 기반)
catalog.infrastructure -> catalog.domain
catalog.application  -> catalog.application.ports (포트 Protocol; stores·reservations를 import하지 않음)

src/container.py -> catalog.{application, domain, infrastructure, presentation.dependencies}
src/container.py -> stores.{application, presentation.dependencies, ...}   (조립 지점만 양쪽을 안다)
```
- catalog.presentation·catalog.application은 stores를 import하지 않는다. stores도 catalog를 import하지 않는다(stores는 자기 쪽 `OpenOffersPort`를 정의, stores.md 8절). 두 모듈이 서로를 아는 곳은 `src/container.py`뿐이다(R2, R11, R12).
- `models.py`는 다른 모듈 모델 클래스를 import하지 않고 FK는 문자열만 쓴다.

### 9.2 container (`src/container.py`의 catalog 구역)

| 항목 | 내용 |
| --- | --- |
| 싱글턴 | `_catalog_clock: CatalogClock = CatalogSystemClock()`, `_reservation_lookup = NoReservationLookup()`(임시, CI-10), `_reservation_cancel = NoReservationCancel()`(임시, CI-11). stores 구역의 `SystemClock`·`_stores_clock`과 이름이 겹치므로 catalog 것은 `CatalogSystemClock`·`CatalogClock` 별칭으로 import한다(Clock은 모듈별 별개 타입, D21) |
| 팩토리 | `create_product_repository`, `create_discount_offer_repository`, `create_stock_log_repository`(각각 `Depends(get_db)` 세션), `create_store_port`(`Depends(create_stores_service)`가 돌려주는 stores 서비스를 `StorePort`로 반환), `create_reservation_lookup()`, `create_reservation_cancel()`, `create_catalog_service`(세션·포트·레포 3종·두 예약 포트를 `Depends`로 받아 `CatalogApplicationService`를 생성) |
| `wire_dependencies` 매핑 | `provide_store_port: create_store_port`, `provide_catalog_service: create_catalog_service`, `provide_reservation_lookup: create_reservation_lookup`, `provide_reservation_cancel: create_reservation_cancel` |

- 한 요청 안에서 `Depends(get_db)`가 같은 세션을 돌려주므로 catalog와 stores의 레포·서비스가 한 트랜잭션을 공유한다(R13).
- `src/main.py`: `wire_dependencies(app)`를 라우터 등록보다 앞에서 부르고, `catalog.infrastructure.models`를 stores models 뒤에 import하고, `catalog_router`를 `include_router`로 등록한다(B1).
- 예약 포트 교체(CI-10, CI-11): reservations 구현 시 `create_reservation_lookup`은 reservations의 추상 레포지토리(`exists_non_cancelled_by_offer`를 호출하는 `OfferReservationLookup`, D81. 이전 `exists_by_offer`가 아니다)를 받는 어댑터를, `create_reservation_cancel`은 reservations 서비스를 `commit=False`로 부르는 어댑터를 돌려주게 바꾼다. 어댑터는 reservations 쪽 또는 container가 소유하고 catalog는 import하지 않는다.

### 9.3 stores 폐점이 catalog를 호출할 때의 생성 순환 (후속, D22)

- 지금 `StoresApplicationService`는 읽기·개설만 가진 단일 서비스이고 `StoreQueryService`와 `OpenOffersPort`는 없다. 그래서 `create_store_port`는 `create_stores_service`의 인스턴스를 그대로 반환하고, `create_catalog_service` → `create_store_port` → `create_stores_service` 한 방향이라 순환이 없다.
- **폐점을 넣으면** stores 서비스가 `OpenOffersPort`(= catalog 서비스)를 생성자 필수 인자로 받아야 해서, `create_store_port`가 같은 stores 서비스를 돌려주는 구조에서는 `create_catalog_service` ↔ `create_stores_service`가 `Depends`로 순환한다(FastAPI가 의존성 해석 중 무한 재귀). 생성자 안에서 서로를 만들어 푸는 방식은 R12 위반이라 쓰지 않는다.
- 해법(D22, stores.md D15와 동일): stores 쪽을 **읽기 전용 서비스(`StoreQueryService`: 레포지토리만 받음)**와 **쓰기 서비스(`StoresApplicationService`: 레포지토리 + `OpenOffersPort`)**로 나눈다. container에서
  - `create_store_port` → `StoreQueryService` (catalog가 사용; catalog를 모른다)
  - `create_catalog_service`는 `Depends(create_store_port)`
  - `create_stores_service`(쓰기, 폐점용)는 `Depends(create_catalog_service)`를 `OpenOffersPort`로 받는다
  순서가 `StoreQueryService → CatalogApplicationService → StoresApplicationService`로 한 방향이라 순환이 없다.

---

## 10. 테스트 계획

기준 경로는 `tests/catalog/`의 4개 파일(`test_domain.py`, `test_service.py`, `test_api_db.py`, `test_wiring.py`)이다. DB 테스트는 `@pytest.mark.db`이고 skip은 통과가 아니다(R16).

- **domain**: `Product`(등록·수정 검증, `deactivate` 순서), `DiscountOffer`(등록 검증, 시간 경계, `effective_status` 표, 재고 조정 전 경우, 9999 상한, `close`/`pause`/`resume`, `apply_changes`), `StoreRef`(`ensure_not_closed` 포함), `StockLog.offer_edit`, `discount_rate` 버림, `cancel_policy()`(`pickup_start − CANCEL_LEAD_TIME`, `pickup_start`가 이미 지나 있어도 계산, timezone 유지, 설명 문구는 상수), `StoreRef.from_info`의 좌표 복사(값·None), `OWNER_DEFAULT_OFFER_STATUSES`가 `is_open`이 참인 `effective_status` 집합과 같고 `OPEN_OFFER_STATUSES`는 그 집합에서 `SUSPENDED`를 뺀 것과 같음(admin C6, D84); `effective_status` 우선순위 표(중단 → 정지 → 마감 → 시작 전 → 품절 → 판매 중) 전 조합, 특히 정지+`is_active=false`(→ `CLOSED`)와 정지+마감 지남(→ `SUSPENDED`)(D85).
  - `apply_changes`: 필드별 성공; 빈 dict·허용 외 키·None 거부; 병합 검증(`sale_price`만 바꿔도 `original_price`와 비교, `sales_end`만 바꿔 `pickup_end`보다 늦으면 400, `sales_start`만 바꿔 `sales_end` 이후면 400); `initial_stock` 증감(+/-)과 반환 delta; 수동 차감 후 `initial_stock`을 줄여 `remaining`이 음수가 되는 경우 400; 중단·마감 지난 할인 `OfferClosedError`; `has_reservations=True` `OfferHasReservationsError`; 검사 순서(닫힘이 예약보다 먼저); 실패 시 상태가 일부도 바뀌지 않음.
  - `pause/resume`: 정상, 이미 중단, 이미 활성, 마감 지남(양쪽), 비활성 상품, 다른 진행 중 할인, 재개 후 `effective_status`(재고 0이면 `SOLD_OUT`, 시작 전이면 `SCHEDULED`).
  - `close`: 활성 할인은 `is_active=False`·`CLOSED`, 재호출은 `OfferClosedError("이미 중단된 할인입니다.")`, 마감 지난 활성 할인도 통과(Q24).
- **application (fake 레포 3종·`StorePort`·두 예약 포트·고정 `Clock`)**:
  - 쓰기 EP마다 `commit` 1회, 실패 시 0회. #13 중간 예외 시 기존 할인이 닫히지 않음. #14의 `StockLog` 부호.
  - #9(D25·D83·D84): 비소유자 `statuses=None` → 레포에 `OPEN_OFFER_STATUSES`와 `exposed_only=True` 전달; 소유자 `statuses=None` → `OWNER_DEFAULT_OFFER_STATUSES`와 `exposed_only=False`; 중복 제거, 값 지정 시 그대로; 폐점 상점·정지 상점의 비소유자·비로그인 → `StoreNotFoundError`이고 레포 호출 0회; 같은 상점의 소유자는 통과; 비소유자·비로그인의 `statuses=[SUSPENDED]`(다른 값과 섞어도) → `OfferStatusNotAllowedError`·레포 호출 0회; 소유자의 `[SUSPENDED]`는 통과; `commit` 0회. 기존 "정지만 숨김" 단언(폐점 상점 비소유자가 200)은 404 단언으로 **교체**한다.
  - #10: 레포가 None이면 `OfferNotFoundError`; 상점 포트가 None이면 `OfferNotFoundError`(`StoreNotFoundError` 아님, D56); 중단·마감·비활성 상품·폐점 상점 fake 데이터에서도 예외 없이 `OfferDetailView`를 돌려줌(D56); `commit` 0회; 좌표 None 전달; `notice`·`cancel_policy`가 도메인 상수·메서드 값; 기존 fake `StoreInfo`에 `latitude`·`longitude` 속성을 추가해 `StoreRef.from_info`가 깨지지 않게 한다.
  - #11: 잠금 호출 순서(product → offer)를 fake에서 기록해 단언, 403 비소유자, 404, `delta != 0`일 때만 `stock_log` 1건, 예약 포트 True면 400, 재개 시 `find_open_by_product` 호출.
  - #12: `cancel_reservations=false`면 포트 호출 0회·상품 `is_active` 불변·`remaining_stock`/`stock_log` 불변(D40)·`products.save` 호출 없음; `true`이고 포트가 3을 돌려주면 올바른 `offer_id`·`reason`으로 1회 호출되고 `cancelled_reservation_count == 3`; 포트가 `PickedUpReservationExistsError`면 전파되고 `commits == 0`; 이미 중단된 할인은 `OfferClosedError`·포트 호출 0회; 마감 지난 활성 할인 성공(Q24); 404 → 403 순서; 폐점 상점 성공(Q14); 잠금 순서(할인 무잠금 조회 → 상품 `for_update` → 할인 `for_update` → 포트 → `commit`).
- **infrastructure (DB)**: `_status_clause`와 `effective_status` 결과 일치(상태 4종 × 시간 경계, CI-5), `find_by_store` 페이지·total(다중 상태 포함), `find_by_store`의 `exposed_only`(D83): `True`면 노출 중단 상품(`products.is_active=false`)의 할인과 정지 할인이 빠지고 `total`·페이지가 빠진 결과와 맞음(예: 11건 중 3건 제외 → `size=5`에서 `total=8`, 마지막 쪽 3건), `False`면 같은 데이터에서 두 종류 모두 포함, `statuses=OWNER_DEFAULT_OFFER_STATUSES`에서 `exposed_only=False`가 SUSPENDED를 돌려주고 `OPEN_OFFER_STATUSES`로는 안 돌려줌, `save` 갱신 후 다시 읽어 가격·시간 5개 컬럼과 `status` 반영(CI-7), `for_update` 직렬화(동시 2건 조정), 동시 PATCH vs `adjust_stock`에서 `stock_log` 합 = `remaining_stock`, 동시 #12 vs `adjust_stock`·#12 vs `relist_offer`에서 교착 없음(product → offer 순서).
- **presentation (DB, 실제 임시 포트)**:
  - #9: 기본 호출에 `SCHEDULED`·`ON_SALE`·`SOLD_OUT`이 나오고 `CLOSED`(중단, 마감 지남)는 안 나옴; `status=CLOSED` 명시 시 나옴; 다중 `status`; 단일 `status=ON_SALE`; 잘못된 값 400 `VALIDATION_ERROR`. D83·D84 추가: (비로그인·타 상점주) 노출 중단 상품의 할인·정지 할인이 목록과 `total`에서 빠짐, 폐점 상점·정지 상점은 404 `NOT_FOUND`(#2와 같은 응답), 타인의 `status=SUSPENDED` 400 `VALIDATION_ERROR`, 비로그인도 같음; (소유자 토큰) 기본 목록에 정지 할인과 노출 중단 상품의 할인이 포함, `status=SUSPENDED` 단독 200에 정지 할인만, 폐점 상점도 200; 정지 할인의 `status` 값이 `SUSPENDED`.
  - #11 재개(D86): 정지된 상점에서 `is_active:true` → 400 `STORE_SUSPENDED`(`StoreSuspendedError`), 폐점 상점 → `STORE_CLOSED`(문구 불변), 폐점+정지 → `STORE_CLOSED`(순서), 정지 상점에서도 중단(`is_active:false`)·#12·재고 조정은 성공, 정지된 상점의 #7·#13 → `STORE_SUSPENDED`(기존 동작 회귀 확인). 상점 검사가 `offer.resume`보다 먼저인 순서 단언(Q47).
  - #11 REQ-17(D81): 예약이 `CANCELLED`뿐인 할인은 PATCH 200, `PENDING_PAYMENT`·`RESERVED`·`PICKED_UP` 중 하나라도 있으면 400 `OFFER_HAS_RESERVATIONS`(예약 상태별 3건 파라미터화). reservations 쪽: `exists_non_cancelled_by_offer`는 예약 없음 False, `CANCELLED`만 False, 취소와 `PENDING_PAYMENT` 혼합 True, 다른 offer의 예약 무시(fake와 실제 DB 양쪽, `tests/reservations`).
  - #6: 본문 없이 호출 → 200 `ProductResponse`(`is_active == false`), 진행 중 할인이 있으면 400 `PRODUCT_HAS_OPEN_OFFER`, 이미 비활성이면 400 `PRODUCT_ALREADY_INACTIVE`, 401, 403, 404.
  - #11: 200(필드별·응답 `status`·`is_active`), 400 각 케이스(7.5 표), 401(`WWW-Authenticate`), 403(고객·타인 상점), 404, 잘못된 UUID 400, `is_active`와 다른 필드 동시 400, `is_active: null` 400, 중단 후 재개 왕복, 재개 후 #7 중복 등록 400, 수량 범위 메시지.
  - #12: 진행 중 할인 중단 → 200, `offer.status == "CLOSED"`, `is_active == false`, 응답 필드 17개가 명세 `Offer`와 일치, `cancelled_reservation_count == 0`; 이후 기본 상점 할인 목록에서 사라지고 `status=CLOSED` 목록에 나타남; 상품 `is_active`와 `discount_offers` 외 행은 변하지 않음; `cancel_reservations=true`/생략; 이미 중단 → 400 `OFFER_CLOSED`; 마감 지난 활성 할인 200; 없는 `offer_id` 404; 중단 후 #11 재개 200(마감 전, Q19), #13 400 `OFFER_CLOSED`, #14 400 `OFFER_CLOSED`; `reason` 누락·빈 문자열·공백만·201자·본문 없음·잘못된 UUID → 400 `VALIDATION_ERROR`(200자는 성공); 401·403(문구 "본인 상점의 할인만 중단할 수 있습니다.")·에러 본문 형식(R7); 폐점 상점의 할인도 성공.
  - #10: 진행 중 할인 200 — 응답 최상위 필드가 명세 #10과 일치하고 `offer`가 17개 필드; `description`·`product_image`가 상품 값; `pickup_address`·`latitude`·`longitude`가 상점 값; `notice`·`cancel_policy.description`이 상수와 같음; `cancel_policy.cancellable_until == pickup_start − 1시간`. 인증 헤더 없이 200(401·403 없음), 고객·타 상점주 토큰으로도 200. 중단된 할인(`status == CLOSED`, `is_active == false`), 판매 마감이 지난 할인, 품절(`SOLD_OUT`), 비활성 상품의 할인, 폐점 상점의 할인이 모두 200이고 상태가 `offer.status`·`offer.is_active`에 반영됨. 좌표 없는 상점이면 `latitude`·`longitude`가 null. 없는 `offer_id` 404 `NOT_FOUND`("할인 판매를 찾을 수 없습니다."), 잘못된 UUID 400 `VALIDATION_ERROR`, 같은 경로의 PATCH가 여전히 동작(공존).
- **조립**: `wire_dependencies` 후 `provide_*` 4개가 `dependency_overrides`에 모두 매핑됐는지(R9), `create_reservation_lookup()`·`create_reservation_cancel()`이 현재 `NoReservationLookup`·`NoReservationCancel`을 돌려주는지(reservations 구현 시 이 단언이 실패해 교체를 상기시킴, CI-10, CI-11), 라우트 12개 등록, 서비스 생성자 인자 필수, `(cd src && uv run python -c "import main")`로 순환 import 없음(R12).

완료 게이트(backend-invariants §7): `python3 .claude/skills/layer-check/check_layers.py` 위반 0, `(cd src && uv run python -c "import main")` 성공, `uv run pytest -rs` failed 0·db 마커 skip 0.

---

## 11. 모듈 밖 변경 (이 문서는 쓰지 않는다)

현재 반영 상태:
- `src/container.py`: catalog 구역(9.2절)과 `wire_dependencies` 매핑 4개가 있다.
- `src/main.py`: `catalog.infrastructure.models`를 stores models 뒤에 import하고 `catalog_router`를 등록한다.
- `.claude/skills/db-schema/schema.sql`·`SKILL.md`: S1·S2·S4가 반영되어 있다(R14). S3 `price` 컬럼 삭제 여부는 팀 확인이 필요하다.
- `pyproject.toml`·`error_handlers.py`·`.env.example`: 변경 없음.
- `docs/reference/catalog.md`·`README.md`: #6 상품 노출 중단, #11 할인 수정(`is_active`, 재개 조건, 에러 표), #12 할인 판매 중단(README 19번 행)이 반영되어 있다.

- #10 구현에 stores 변경은 없다. `Store`가 `latitude`·`longitude`(`float | None`)를 이미 가지고 `StoresApplicationService.find_store_by_id`가 그 객체를 그대로 반환하며 폐점 상점도 반환한다(`src/stores/domain/store.py:22-53`, `src/stores/application/service.py:18`, `src/stores/infrastructure/repositories.py:20-25,76-77`). catalog 쪽 `StoreInfo` Protocol과 `StoreRef`만 확장한다. `src/container.py`·`src/main.py` 변경도 없다(서비스 생성자 인자가 늘지 않고 `provide_*` 매핑이 같다).

- #3·#8(14절) 구현에는 **stores 변경이 필요하다**(C15): `StoreRepository.find_visible_near`, `SqlAlchemyStoreRepository` 구현, `StoreQueryService.find_visible_stores`, `StoreWithDistance`. 설계는 `docs/design/stores.md` 15절에 반영했다(D41~D47, C22·C23). `src/container.py`·`src/main.py`·스키마(`schema.sql`)·`pyproject.toml`·`error_handlers.py`는 변경 없다(새 `provide_*`·테이블·의존성·예외 클래스가 없다). 구현 순서는 stores → catalog.
- `docs/reference/catalog.md` §3의 `/v1/products/search`와 `docs/reference/README.md` 10번 행·"FastAPI 주의" 문구는 이번에 `/v1/products`로 정정했다(D59).

- 2026-11-06 요구 조건 반영(D81~D85)이 필요로 하는 모듈 밖 변경: reservations 쪽 `exists_non_cancelled_by_offer` 추가와 어댑터 호출 교체, fake 2곳(`tests/reservations/fakes.py`, `tests/payments/test_integration.py`) 갱신(reservations.md D-39·C-21). `docs/reference/catalog.md`는 바꾸지 않는다(에러 코드·문구 유지, 단 "예약이 있는"의 의미가 "취소되지 않은 예약"임을 명세 §11 설명에 한 줄 보강하는 것을 제안한다, 승인 전에는 바꾸지 않는다).

`docs/reference/catalog.md` 갱신 제안(직접 수정 금지, 승인 후 반영, D81·D86):
| 위치 | 현재 | 제안 |
| --- | --- | --- |
| 572행 §11 "재개 조건" 인용문 | "…상품이 활성이고 상점이 폐점이 아니며, 같은 상품에 다른 진행 중 할인이 없어야 합니다." | "…상품이 활성이고 상점이 폐점·정지 상태가 아니며, 같은 상품에 다른 진행 중 할인이 없어야 합니다." |
| 586행 §11 에러 표 `STORE_CLOSED` 행 바로 아래(새 행) | (없음) | `\| 400 \| STORE_SUSPENDED \| 관리자에 의해 정지된 상점입니다. \|` |
| 580행 §11 에러 표 `OFFER_HAS_RESERVATIONS` 행 | 메시지만 있음, 의미 설명 없음 | 메시지·코드는 그대로 두고 표 아래 한 줄 추가: "예약이 있는 할인이란 취소되지 않은 예약(결제 대기·예약 완료·픽업 완료)이 한 건이라도 있는 할인을 말합니다. 모두 취소된 할인은 수정할 수 있습니다." |
| 568~571행 §11 설명문 중 "예약 여부는 예약 기능이 생기기 전까지 항상 '예약 없음'으로 처리됩니다." | 현재 문구 | 예약 기능이 연결돼 있으므로 이 문장을 삭제(또는 위 한 줄로 대체) |
| §7 할인 등록·§13 재등록 에러 표 | 정지 상점 행이 없으면 | `\| 400 \| STORE_SUSPENDED \| 관리자에 의해 정지된 상점입니다. \|` 추가(코드는 이미 동작, 행 존재 여부는 구현자가 확인) |

남은 제안(명세·타 모듈, 승인 전에는 바꾸지 않는다):
- `docs/reference/catalog.md` §10: "확인 필요" 인용문을 아래 확정 내용으로 바꾼다. `notice`는 고정 문구, `cancel_policy.cancellable_until = pickup_start − 1시간`, `cancel_policy.description`은 고정 문구(문구는 D54·D55), 중단·마감 할인·비활성 상품의 할인·폐점 상점의 할인도 조회되며 상태는 `offer.status`·`offer.is_active`로 구분, `latitude`·`longitude`는 상점이 좌표 없이 개설되면 null, `description`은 null 가능. 응답 예시를 추가한다(`offer`는 Offer 공통 객체 예시 재사용).
  ```json
  {
    "offer": { "...": "Offer 17개 필드" },
    "description": "오늘 구운 식빵 5종 모둠",
    "product_image": ["https://example.com/bread.jpg"],
    "pickup_address": "서울시 마포구 월드컵북로 1",
    "latitude": 37.5563,
    "longitude": 126.9236,
    "notice": "<OFFER_NOTICE 확정 문구>",
    "cancel_policy": {
      "cancellable_until": "2026-11-04T17:00:00+09:00",
      "description": "<CANCEL_POLICY_DESCRIPTION 확정 문구>"
    }
  }
  ```
- `docs/reference/README.md` 17번 행은 변경 없음(공개, 200, 404).- `docs/reference/catalog.md` #14: 403 메시지 "본인 상점의 이력만 조회할 수 있습니다."를 "본인 상점의 재고만 조정할 수 있습니다."로 교체(D8), 페이지네이션·허용 외 `status`의 422를 전역 핸들러와 같은 400 `VALIDATION_ERROR`로 정리(D14).
- `docs/design/stores.md`: 폐점 구현 시 읽기/쓰기 서비스 분리(9.3절, stores.md D15).
- `docs/design/reservations.md`가 생기면 CI-10, CI-11, C9, C12의 요구사항을 반영한다.

---

## 12. 결정과 질문 목록

임시 기본값은 확정이 아니라 제안이다. 코드에서는 "코드 위치" 열의 한곳에 모아 두어 바꾸기 쉽게 한다. 상태 열: 확정 = 사용자 결정 또는 명세로 정해짐, 임시 = 제안이며 사용자 확정 전. 번호는 코드와 테스트가 주석으로 참조하므로 빈 번호가 있어도 다시 매기지 않는다.

### 12.1 결정 표

| # | 항목 | 출처 | 결정 값 | 근거 | 코드 위치 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | `discount_rate` 반올림/버림 | 명세 공통 객체 | **버림** `(원가-할인가)*100 // 원가` (정수 연산) | 포인트 정책이 "소수점 버림"이라 팀 관례와 맞음, 부동소수 오차 없음 | `DiscountOffer.discount_rate` | 임시 |
| D2 | 등록 시 `status` 결정 | 명세 #7 | `sales_start > now` → `SCHEDULED`, 아니면 `ON_SALE` | 명세 제안 | `DiscountOffer.register` | 임시 |
| D3 | 시간 경과에 따른 상태(스케줄러 없음) | 설계 | **조회 시 계산**(`effective_status`), 저장 `status`는 쓰기 때 동기화 | 배치 인프라가 없음 | `effective_status`, `_status_clause` | 임시 |
| D4 | "진행 중인 할인" 정의 (#5, #6, #7, #11 재개, 폐점) | 명세 #5·#6·#7 | `is_active and now < sales_end` (유효 상태 SCHEDULED/ON_SALE/SOLD_OUT) | 판매가 끝나 픽업만 남은 할인이 다음 날 할인 등록을 막지 않게 | `DiscountOffer.is_open` | 임시 |
| D5 | 재고 0 ↔ `SOLD_OUT`/`ON_SALE` 전환 | 명세 #14 | 0이 되면 `SOLD_OUT`, 0에서 늘면 `ON_SALE`(시작 전이면 `SCHEDULED`) 자동 | 명세 제안 + `is_sold_out` 계산 값과 일치 | `adjust_stock` | 임시 |
| D6 | 공개 목록의 `is_active=false` | 명세 #2 | 기본은 활성만. `false` 요청은 해당 상점 소유자만(비로그인 401, 타인 403) | 명세 제안 | `list_products`, router | 임시 |
| D7 | 비활성 상품 상세 노출 | 명세 #4 | 소유자 외에는 404 | D6과 일관 | `get_product` | 임시 |
| D8 | #14 누락 에러 | 명세 #14 | 초과 차감 400 `INSUFFICIENT_STOCK`; `amount=0` 400; 중단된 할인(`is_active=false`) 400 `OFFER_CLOSED`(시간만 지난 건 허용); 증가 후 `initial > 9999` 400; 403 문구 "본인 상점의 재고만 조정할 수 있습니다." | 명세 제안 + 최초 수량 상한 1~9999 | `adjust_stock` | 임시 |
| D9 | 폐점·미승인 상점 에러 문구 | 명세 #1 | "폐점된 상점에서는 {상품/할인}을 등록할 수 없습니다." (400 `STORE_CLOSED`), 미승인은 명세 문구 그대로. 할인 등록·재등록에도 같은 검사 적용 | stores 명세 "폐점된 상점에서는 상품 및 할인 판매를 등록할 수 없다" | `StoreRef.ensure_can_register` | 임시 |
| D10 | 시간 규칙 보강 | 명세 #7 | `sales_end > now` 필요, `pickup_end >= sales_end`(같아도 허용), `pickup_start`와 `sales_end` 사이 제약 없음(명세 예시가 겹침) | 명세 예시·에러 문구 | `DiscountOffer.register`, `apply_changes` | 임시 |
| D11 | 재등록 규칙 | 명세 #13 | 기존 할인이 `is_active=true`이면 시간이 지났어도 재등록 가능. 기존 건의 `remaining_stock`은 유지, 기존 예약은 그대로, 신규 건에 `+initial` 로그. 상품 활성·상점 미폐점 필요 | "기존 예약은 유지" | `relist_offer` | 임시 |
| D12 | `reason` 저장 | 명세 #14, 스키마 | `stock_log.reason` 컬럼(S2). 최초 입고 사유는 `"최초 입고"`, 할인 수정은 `"할인 수정"` | 명세 요청 사항 | `StockLog`, S2 | 임시 |
| D13 | 상품 재노출 API | 명세 #6 | 만들지 않는다. `Product.activate`·재노출 EP 없음 | 범위 외, 사용자 결정 | - | 확정 |
| D14 | 형식 오류 코드와 페이지네이션 | README 공통 3·5번 | 전역 핸들러대로 400 `VALIDATION_ERROR`; `page` 1부터, `size` 1~100, 응답 `items,page,size,total` | `error_handlers.py`, 명세 | router(`Query` 제약) | 임시 |
| D15 | 상품 목록 정렬 | 명세에 없음 | `name ASC, id ASC` (`created_at` 컬럼이 생기면 최신순, S6) | 컬럼이 없음 | `SqlAlchemyProductRepository.find_by_store` | 임시 |
| D16 | PATCH에서 null | 명세 #5 | `category`, `description`은 null로 비우기 허용. `name`, `original_price`, `product_image`는 null 거부 | 필수 값 | `Product.apply_changes` | 임시 |
| D17 | 비활성 상품·폐점 상점의 상품 수정 | 명세 #5 | 허용 | 제한 규칙이 명세에 없음 | `update_product` | 임시 |
| D18 | 이미지 URL 검증 | 명세 #1 | 개수(≤10)와 공백 아님만 검사, URL 형식·길이 검증 안 함 | 명세에 없음 | `Product` | 임시 |
| D19 | 상점주 역할 값, 승인 상태 저장 | auth 명세 7번, 스키마 5절 | 역할 `OWNER`(이미 코드에 있음). 승인 판단은 상점 `approval_at` 유무 | 명세 예시, 기존 auth 코드 | `Role.OWNER`, `StoreRef.approved` | 임시 |
| D20 | 스키마 변경 S1~S4, S6 | 4절 | S1·S2·S4는 `schema.sql`에 반영, S3 `price`는 `models.py`가 매핑하지 않음, S6은 보류 | 4절 | `models.py` | 임시 |
| D21 | 시계 주입 방식 | R8, layer-architecture §5.2 | `Clock`(ABC)은 **모듈별로 둔다**(catalog는 자기 모듈 `domain/service.py`). 공용 `src/common/`에 두지 않는다. infrastructure `SystemClock`을 container 싱글턴으로 서비스 생성자에 필수 인자로 주입. stores.md D13과 동일 결정 | 시계는 기술 의존 기능이라 추상화 대상(§5.2), 기본 구현체 생성 금지(R8), 모듈 독립성 | `domain/service.py`, `infrastructure/clock.py`, container `_catalog_clock` | 확정 |
| D22 | stores 폐점 연계 시 생성 순환 해법 | R12, stores.md C3 | stores를 읽기 전용 `StoreQueryService`와 쓰기 서비스로 분리, catalog의 `StorePort`는 읽기 전용 서비스가 구현(9.3절). 폐점 구현 전에는 stores 서비스 하나로 충분. stores.md D15와 동일 결정 | 생성자 안에서 서로를 만드는 방식은 R12 위반, 팩토리 단방향 | container `create_store_port` | 임시 |
| D23 | 서비스 입력 사용자 타입 | R11 | 서비스는 `user_id: UUID`만 받고 auth의 `User`·예외를 import하지 않는다. 비로그인 401은 router가 낸다 | auth 도메인에 의존하지 않기 위함 | `CatalogApplicationService`, router | 임시 |
| D24 | 레포지토리 추상 배치 | layer-architecture §5.1 | 애그리거트 3개라 `domain/repository/<애그리거트>_repository.py`로 나눔, 구현체는 `infrastructure/repositories.py` 한 파일 `SqlAlchemy*` | §5.1 "애그리거트가 여럿이면 나눈다" | 1절 | 임시 |
| D25 | 상점 할인 목록 기본 `status` (#9) | 사용자 요청, 명세 §9 | `status`를 반복 가능한 다중 값으로 받고, 미지정 시 `SCHEDULED`+`ON_SALE`+`SOLD_OUT`(D4 "진행 중"과 같은 집합). 값을 주면 그 값들만(OR). `CLOSED`는 명시할 때만. 주변 할인 목록(§8) 기본 `ON_SALE`은 바꾸지 않음 | 등록 직후 `SCHEDULED`인 할인이 기본 `ON_SALE` 필터에서 빠져 "등록한 할인이 안 보이는" 문제를 막는다. 단일 `status` 호출과 호환되고 권한 분기가 없다 | `OPEN_OFFER_STATUSES`(`domain/discount_offer.py`), router `status`, `find_by_store(statuses=…)` | 확정 |
| D26 | 할인 수정 PATCH의 "상태 변경" 의미 (#11) | 사용자 요청 | 계산 상태(SCHEDULED/ON_SALE/SOLD_OUT)는 직접 바꾸지 않는다. 직접 바꾸는 값은 `is_active`뿐이고 PATCH 본문의 `is_active`(false=중단, true=재개)로 받는다. `is_active`는 다른 필드와 함께 보낼 수 없다. 응답은 `OfferResponse`(계산 `status` + `is_active`) | 명세 #11 응답이 Offer라 `status` 확인 가능. README "상태만 바꾸는 동작은 `POST /{id}/동사`" 규칙의 예외로 README에 명시됨 | `OfferUpdateRequest`, `update_offer` | 확정 |
| D27 | 할인 수정 가능 필드·검증 | 명세 #11 | 수정 필드 `sale_price`, `initial_stock`, `sales_start`, `sales_end`, `pickup_start`, `pickup_end`. null 거부, 빈 요청 400 "수정할 항목이 없습니다.". 중단됐거나 판매 마감이 지난 할인은 400 "종료된 할인은 수정할 수 없습니다.". 시간 일부만 바꿔도 **병합한 전체 값**에 할인 등록과 같은 검증. 이미 시작한 할인의 `sales_start` 변경도 허용 | 명세 #11 확인 필요 문구, D10 일관성 | `DiscountOffer.apply_changes` | 확정 |
| D28 | "예약 0건일 때만 수정" 판정 | 명세 #11, reservations 미구현 | catalog가 `ReservationLookupPort.has_reservations_for_offer(offer_id)`를 정의하고, 임시 구현 `NoReservationLookup`(항상 False)을 container에 연결. ~~"예약"은 상태와 관계없이 한 건이라도 있으면 포함(취소 건 포함)~~ → **D81로 변경: 취소되지 않은 예약만 센다.** reservations 구현 때 바인딩 교체 | R11(포트는 쓰는 쪽이 정의), 현재 데이터와 일치(예약 자체가 없음), 가드 위치가 코드에 남음 | `application/ports.py`, `infrastructure/reservation_lookup.py`, container `create_reservation_lookup` | 확정(포트 구조), 판정 범위는 D81 |
| D29 | `initial_stock` 수정 시 `remaining_stock` | 명세 #11 | `remaining_stock`을 재설정하지 않고 **증감한 만큼** 더한다(`remaining += new_initial - old_initial`). 증감이 0이 아니면 `stock_log`에 그 증감을 기록한다. 결과가 음수가 되면 400 | 수동 차감(포장 파손 등)이 수정으로 되살아나지 않게, `stock_log` 합 = `remaining_stock` 유지 | `apply_changes`, `StockLog.offer_edit` | 확정 |
| D30 | 중단·재개 규칙, #12·#13과의 관계 | 명세 #11~#13 | 중단(`pause`)은 `is_active=true`이고 마감 전일 때만. 재개(`resume`)는 `is_active=false`이고 마감 전, 상품 활성, 같은 상품에 다른 진행 중 할인 없음, 상점 미폐점일 때만. 중단은 기존 예약을 건드리지 않는다. #13 재등록은 중단된 할인에 불가 | 상태 값이 `is_active` 하나뿐이라 도메인 상태는 공유 | `DiscountOffer.pause/resume`, `StoreRef.ensure_not_closed` | 확정 |
| D34 | #12의 중단 방식 | 팀 명세 | `DiscountOffer.close(now)`를 재사용한다 | `close`가 `is_active=false`, `CLOSED`를 만들고 #13도 같은 메서드를 쓴다 | `deactivate_offer` | 확정 |
| D38 | #12 `reason` 처리 | 팀 명세, 사용자 결정 | 검증만 하고(1~200자, 공백만 거부) 저장하지 않는다. 포트에만 넘긴다 | 스키마 변경 없이 진행, 저장은 후속(Q22) | `OfferDeactivateRequest` | 확정 |
| D40 | #12의 재고 영향 | 사용자 결정 | 재고·`stock_log`를 바꾸지 않는다. 예약 취소 시에도 닫히는 할인에 재고를 되돌리지 않고 `remaining_stock`을 유지한다 | #13의 기존 할인 종료와 같은 방식, `stock_log` 합 불변식, reservations ↔ catalog 순환 방지(R12) | `deactivate_offer`, 포트 계약 | 확정 |
| D41 | `cancel_reservations=false` | 명세 기본값 | 포트를 호출하지 않고 예약을 건드리지 않는다 | 명세 기본값 | `deactivate_offer` 7단계 | 확정 |
| D42 | 예약 일괄 취소 포트 | 사용자 결정, R11 | catalog가 `ReservationCancelPort.cancel_all_for_offer(offer_id, *, reason) -> int`(할인 1건 기준)를 정의하고 임시 구현 `NoReservationCancel`(항상 0)을 container에 연결 | R11(쓰는 쪽이 포트 정의), reservations 미구현 | `application/ports.py`, `infrastructure/reservation_cancel.py`, container `create_reservation_cancel` | 확정 |
| D45 | #6 상품 노출 중단 | 명세 §6 | 상품 `is_active=false`. 진행 중 할인이 있으면 400 `PRODUCT_HAS_OPEN_OFFER`, 이미 비활성이면 400 `PRODUCT_ALREADY_INACTIVE`. 응답 `ProductResponse`, 본문 없음, 403 문구 "본인 상점의 상품만 변경할 수 있습니다." | 명세, 사용자 결정 | `Product.deactivate`, `deactivate_product` | 확정 |
| D46 | #12 할인 판매 중단의 대상 | 팀 명세 | **할인 1건**을 `close(now)`로 중단한다. 상품 `is_active`·`remaining_stock`·`stock_log`는 바뀌지 않는다 | 팀 명세 | `deactivate_offer` | 확정 |
| D47 | "이미 중단된 할인" 판정 범위 | 명세 에러 표 | `not is_active`만 400. **마감이 지난 활성 할인도 #12로 중단할 수 있다**(Q24) | 명세 에러에 "판매 마감" 400이 없고, 마감 후 픽업 대기 예약을 상점주가 일괄 취소하는 수단이 남는다 | `DiscountOffer.close` | 확정 |
| D48 | #12 에러 우선순위 | R7 | 404(할인 없음) → 403(소유 아님) → 400 이미 중단 → 400 픽업 완료 예약(포트). 이미 중단 검사를 포트 호출보다 먼저 해서 불필요한 취소를 막는다 | 에러 일관성 | `deactivate_offer` | 확정 |
| D49 | #12 잠금 순서 | 5.3 | 할인 무잠금 조회 → 상품 `FOR UPDATE` → 할인 `FOR UPDATE`(`populate_existing`) → 예약·결제(포트 내부). #11·#13과 같은 패턴 | 교착 방지 | `deactivate_offer` | 확정 |
| D50 | #12 흐름 순서 | R5, R13 | `offer.close(now)` → `cancel_reservations`이면 포트 호출 → `offers.save` → `commit()` 한 번. 포트 예외는 commit 전이라 전부 롤백 | 한 트랜잭션 | `deactivate_offer` | 확정 |
| D51 | #12 응답 구조 | 팀 명세 | `OfferDeactivateResponse{offer: OfferResponse, cancelled_reservation_count}`. `offer.status`는 항상 `CLOSED`, `is_active`는 `false` | `OfferResponse`가 명세 `Offer`와 같은 17개 필드 | `OfferDeactivateResponse.from_result` | 확정 |
| D53 | #11 `is_active:false`와 #12의 공존 | 사용자 결정 | 둘 다 유지한다. #12는 사유·예약 일괄 취소·`{offer, count}`·마감 후 중단 허용, #11 중단은 마감 후 400 `OFFER_ENDED`이고 사유·예약 연계가 없다. 명세 §11이 두 방법을 모두 안내한다 | 사용자 결정. 없애면 D26·`pause()`·테스트가 바뀐다 | `pause`, `close` | 확정 |
| D54 | #10 `notice` | 사용자 결정 | 고정 문구 상수 `OFFER_NOTICE`(스키마 변경 없음). 문구는 "마감 시간이 가까운 상품으로 수량이 한정되어 있습니다. 픽업 시간 안에 매장을 방문해 예약 확인 코드를 보여주세요. 픽업 시간이 지나면 수령할 수 없습니다." | 저장 컬럼이 없음, 사용자 결정 | `domain/discount_offer.py` 상수 | 확정 |
| D55 | #10 `cancel_policy` | 사용자 결정 | `cancellable_until = pickup_start − CANCEL_LEAD_TIME(1시간)`을 `DiscountOffer.cancel_policy()`가 계산, `description`은 고정 문구 상수. payments 위약금 규칙이 같은 기준을 따라야 한다(13.3 C14). `description` 문구는 "픽업 시작 1시간 전까지 취소할 수 있습니다. 이후에는 취소가 제한되거나 위약금이 부과될 수 있습니다." | 사용자 결정, 명세 §10 제안 | `DiscountOffer.cancel_policy`, `CANCEL_LEAD_TIME`, `CANCEL_POLICY_DESCRIPTION` | 확정 |
| D56 | #10 공개 범위·에러 | 사용자 결정, admin.md C7·D20, requirements 정책 표 "할인 상세 조회" | 인증 없이 누구나 조회(토큰이 있으면 소유자 판별에만 쓰는 `OptionalUser`). **정지된 할인과 정지된 상점의 할인만** 비소유자에게 404. 폐점 상점의 할인, 노출 중단 상품의 할인, 중단·종료·품절 할인은 모두 조회되고 `offer.status`·`offer.is_active`로 상태를 표시한다. 에러는 할인 없음 404 하나(401·403 없음). 갱신 근거와 코드 확인은 D82 | 사용자 결정, `docs/requirements/catalog-offers.md` 정책 표 | `get_offer_detail`, router | 확정 |
| D57 | #10 응답 구성 | 명세 §10, 사용자 결정 | `OfferDetailResponse`는 명세 필드 그대로이고 `offer`는 기존 `OfferResponse`를 재사용한다. `latitude`·`longitude`는 catalog `StoreInfo`·`StoreRef`에 추가해 상점에서 받고 null 가능. `cancel_policy`는 중첩 객체 | 명세 필드명 유지(R15), stores가 이미 좌표를 제공 | `schemas.py`, `application/ports.py`, `StoreRef` | 확정 |
| D58 | #10 조회 방식 | 설계 | 할인+상품을 `find_with_product` 한 번의 JOIN으로 읽고 상점은 `StorePort`로 읽는다. 잠금·commit 없음 | 읽기 전용, 5.3절 | `find_with_product`, `get_offer_detail` | 확정 |
| D59 | #3 상품 검색 경로 | 사용자 결정 | `GET /v1/products`(공개, 200). 이전 제안 `/v1/products/search`는 폐기. `GET /v1/products/{product_id}`(#4)와 경로가 달라 등록 순서 제약이 없다 | 사용자 확정 | router | 확정 |
| D60 | #8 주변 할인 목록 경로 | 사용자 결정, 명세 §8 | `GET /v1/offers`(공개, 200). #9 `GET /v1/stores/{store_id}/offers`는 변경 없음 | 사용자 확정 | router | 확정 |
| D61 | 공개 검색·주변 목록에 노출되는 상점 | requirements 정책 표("노출 중 상품 조회: 상점이 폐점이 아님", "폐점 상점의 상품 읽기·검색: 상점주 외 불가, 존재하지 않는 것처럼 다룸"), admin.md D17·명세 7 | `approval_at IS NOT NULL AND closed_at IS NULL AND suspended_at IS NULL`인 상점만. stores가 이 조건으로 거른다(14.3). 미승인은 requirements가 등록 차단만 정하고 검색 노출은 언급이 없어 같은 조건에 포함(상점 개설이 `approval_at`을 채워 실제로는 거의 없음) | 폐점·정지 상점은 근거가 명시돼 있고, 미승인은 보수적으로 숨김 | stores `find_visible_near`, `Store`의 노출 조건 한곳 | 확정(사용자 결정) |
| D62 | 노출되는 상품 | requirements 정책 표("노출 중단 상품 조회: 상점주 외 불가") | `products.is_active = true`만. #8도 상품이 비활성인 할인은 제외(D56 #10 단건 상세는 ID로 직접 접근하므로 숨기지 않는 것과 다르다) | 공개 탐색 목록에서 노출 중단 상품을 뺀다 | #3 상품 조건(`search_store_ids`·`find_matching_in_stores`)과 #8 `search_in_stores`의 `WHERE` | 확정(사용자 결정) |
| D63 | 소유자 예외 | 사용자 결정(인증 없음), requirements 정책 표 | 두 EP는 `OptionalUser`도 쓰지 않는다. 소유자라도 폐점·노출 중단 상품이 검색에 나오지 않는다. 소유자는 #2(`is_active=false`)로 본다 | 사용자 확정 "인증 없음". requirements의 "폐점 상점의 상품 검색: 상점주 허용"과 충돌(Q31) | router | 확정(사용자 결정) |
| D64 | 정지 할인 | admin.md D20·명세 7 | 공개 목록·검색에서 정지된 할인은 숨긴다. #8 `status`는 `PublicOfferStatus`(`SUSPENDED` 없음)이고 `_status_clause`가 정지 할인을 `ON_SALE`·`SCHEDULED`·`SOLD_OUT`에서 뺀다. `has_active_offer`에도 세지 않는다 | admin 명세 7 | `_status_clause`, `PublicOfferStatus` | 확정(admin 설계) |
| D65 | 여러 상점 조회·거리 계산 방식 | admin.md C9, R11, layer-architecture §3.4 | `StorePort.find_visible_stores`를 추가해 stores가 "노출 상점 + 거리"를 계산·정렬하고 catalog는 상점 id 목록으로 자기 테이블을 `= ANY(:ids)` 필터한다. catalog가 `stores`를 조인하지 않는다. 비정규화 컬럼은 쓰지 않는다 | `find_stores_by_ids` 후 걸러내면 `total`이 틀어지고(C9), 비정규화는 스키마 변경과 동기화 부담이 크다 | `ports.py`, stores `StoreQueryService` | 확정(사용자 결정) |
| D66 | 거리 계산 | 명세 §3·§8 "확인 필요"(PostGIS 없음) | SQL 하버사인(구면, 지구 반지름 6371.0km), `distance <= radius_km`(경계 포함). 위도 범위 선필터. 좌표 없는 상점은 위치 지정 시 제외 | PostGIS가 스택에 없음. 하버사인은 명세 제안 | stores `find_visible_near` | 확정(사용자 결정) |
| D67 | 위치 미입력 동작, `unit` | 명세 §3·§8 | 위치 없이 호출하면 반경 필터 없이 노출 상점 전체를 대상으로 하고 `distance`는 `null`, `unit`은 항상 `"km"`. `radius_km`만 오면 무시. 거리는 소수 둘째 자리로 반올림 | 명세 제안(`distance`는 `null`). 응답 스키마가 `distance: float`이라 null 허용은 명세와 다름(Q32) | `search.py` 상수 `DISTANCE_UNIT`, `DISTANCE_DECIMALS` | 확정(사용자 결정) |
| D68 | #3 정렬 (D77로 개정) | 명세에 정렬 매개변수 없음 | **상점** 정렬은 stores가 돌려준 순서(`array_position`): 위치가 있으면 거리 오름차순 → `id`, 없으면 `name ASC, id ASC`(Q42). 상점 안 `products[]`는 `name ASC, id ASC`(Q43, D15와 같음) | 명세에 없음, 상점 상품 목록 기본 정렬과 일관 | `ProductRepository.search_store_ids`, `find_matching_in_stores` | 확정(사용자 결정) |
| D69 | 검색어·카테고리 매칭 | 명세 §3·§8 | `keyword`는 앞뒤 공백 제거 후 부분 일치, 대소문자 무시(`ILIKE`, `%`·`_`·`\` 이스케이프), 100자 이하. #3은 상품명·설명, #8은 상품명만(명세). `category`는 정확 일치(#2와 같음) | 명세 설명, #2 | `search.py`, 레포 쿼리 | 확정(사용자 결정) |
| D70 | `has_active_offer` 정의 | 명세 §3 "진행 중인 할인 여부", requirements 용어 "진행 중인 할인 상품" | 같은 상품에 유효 상태가 `OPEN_OFFER_STATUSES`(SCHEDULED/ON_SALE/SOLD_OUT, 정지 제외)인 할인이 있으면 true. #9 기본 목록과 같은 집합 | 상태 집합을 한곳에서 관리(D25) | `OPEN_OFFER_STATUSES`, `_status_clause` | 확정(사용자 결정) |
| D71 | #8 정렬 방향 | 명세 §8 "확인 필요" 제안 | `distance`·`price`·`sales_end` 오름차순, `discount_rate` 내림차순. 동률은 `sales_end ASC, id ASC`. 기본 `sort=sales_end` | 명세 제안 그대로 | `DiscountOfferRepository.search_in_stores` | 확정(사용자 결정) |
| D72 | #8 검증 | 명세 §8 에러 표 | `lat`·`lng` 한쪽만 400, `sort=distance`에 위치 없음 400(명세 문구). `status` 허용 외 값은 명세의 422가 아니라 400(D14). `status`는 단일 값, 기본 `ON_SALE` | 명세, D14 | `SearchArea`, `OfferSort` | 확정(사용자 결정) |
| D73 | 응답 구성(폐기) | 사용자 확정 명세 | ~~#3 `items[]`는 4필드 평면 구조~~ → **D76으로 대체**. #8 `items[]` 구성(`offer`, `distance`, `unit`)은 유지 | - | - | 폐기(#3 부분) |
| D74 | 페이지·`total` 정합 | admin.md C9 | 상점 필터를 레포 쿼리 안(`= ANY(:ids)`)에 두어 `total`과 페이지가 같은 조건에서 계산된다. 거리순 정렬은 `array_position(:ids, store_id)`. 배열 바인드 한 개라 asyncpg 파라미터 상한(32767)에 걸리지 않는다 | `IN (...)` 전개 금지 | 레포 쿼리 | 확정(사용자 결정) |
| D75 | 읽기 전용·오류 코드 | R5, D14 | 두 EP는 잠금·`commit`이 없고 상점 조회와 상품·할인 조회가 한 시점이 아니다(허용). 형식·범위 오류는 전역 핸들러의 400 `VALIDATION_ERROR` | 읽기 전용, D14 | 서비스, router | 확정(사용자 결정) |
| D76 | #3 응답 구조 (D77로 대체) | 사용자 결정(Q30) | ~~`items[]` = `product` + `store` + `distance` + `unit` + `has_active_offer` 평면 구조(상품 단위)~~ → 사용자가 상점 단위 묶음으로 다시 결정해 **폐기**. `StoreSummaryResponse`(`id, name, pickup_address, latitude, longitude`)와 "`StoreInfo`로 채운다"는 부분은 D77이 이어받는다 | - | - | 폐기 |
| D77 | #3 응답 구조: 상점 단위 묶음 (D76 대체) | 사용자 결정 | `items[]` 한 건 = 검색 조건(`keyword`·`category`·반경)에 맞는 상품을 1개 이상 가진 **상점 하나**: `{store: {id, name, pickup_address, latitude, longitude}, distance, unit, products: [ProductResponse 필드 + has_active_offer, …]}`. `products[]`에는 그 상점의 조건 일치 상품을 전부 담는다(상한 없음, Q44). **`page`·`size`·`total`은 상점 수 기준.** 조건 일치 상품이 없는 상점은 나오지 않는다. #8 응답은 바뀌지 않는다. `store`는 `StoreWithDistance.store`(`StoreInfo`)로 채워 stores·`StorePort` 추가 변경이 없다 | 사용자 결정, `StoreInfo`가 5개 필드를 이미 가짐 | `schemas.py`, `StoreSearchHit`, 레포 쿼리(14.4) | 확정(사용자 결정) |
| D78 | 정상 가격 상한 | requirements REQ-3(사용자 결정 "1억 이상 입력 금지") | 1 이상 99,999,999 이하. 상한은 새 입력(`Product.register`, `apply_changes`)에서만 검사하고 생성자(DB 복원)는 검사하지 않는다. 기존 행이 1억 이상이어도 읽기가 깨지지 않게 하기 위함. DB `CHECK`는 추가하지 않는다 | 사용자 결정, 기존 데이터 호환 | `product.py` 모듈 상수 `MAX_PRICE`, `Product._validate_new_price` | 확정(사용자 결정) |
| D79 | 상품 재노출 EP | requirements 상태와 전이(노출 중단 → 노출 중), 명세 §6 "확인 필요" | `POST /v1/products/{product_id}/activate`. 노출 상태 전환은 #6·#6-1 전용 명령으로만 하고 PATCH(#5)로 받지 않는다. 검사 순서: 상품 존재(404) → 소유자(403) → 폐점(`STORE_CLOSED`) → 이미 노출 중(`PRODUCT_ALREADY_ACTIVE`). 상품 행 `FOR UPDATE` 후 `commit`. 예전 할인은 되살리지 않는다 | 사용자 결정. 전환마다 조건이 달라 PATCH에 섞으면 REQ-10과 함께 원인 파악이 어렵다 | `Product.reactivate`, `reactivate_product`, router | 확정(사용자 결정) |
| D80 | 폐점 상점의 상품 숨김 (CI-15 해결) | requirements 정책 표(폐점 상점의 상품 조회: 상점주 외 불가) | `StoreRef.are_products_visible_to`: 폐점 또는 정지면 소유자에게만 보인다. #2·#4와 **#9(D83)**가 쓰고, #10(할인 상세)만 기존 `is_visible_to`(정지만)를 유지한다(D82). 숨김 응답은 기존과 같은 404 `StoreNotFoundError` | 사용자 결정(상품에만 적용, 할인은 할인 요구 조건에서 결정 → 2026-11-06 D82·D83으로 닫힘) | `store_ref.py`, `list_products`, `get_product`, `list_offers_by_store` | 확정(사용자 결정) |
| D81 | #11 수정을 막는 예약 범위 (REQ-17, D28 변경) | `docs/requirements/catalog-offers.md` REQ-17("취소되지 않은 예약이 한 건이라도 있는 할인 상품은 판매 조건을 수정할 수 없다. 예약이 모두 취소됐으면 수정할 수 있다") | 수정을 막는 예약은 `PENDING_PAYMENT`·`RESERVED`·`PICKED_UP`(= `CANCELLED`가 아닌 것). `ReservationLookupPort.has_reservations_for_offer(offer_id) -> bool` 서명·이름·`DiscountOffer.apply_changes(has_reservations=...)`·`OfferHasReservationsError` 코드·메시지는 **유지**하고 reservations 쪽만 좁힌다: 추상 `ReservationRepository`에 `exists_non_cancelled_by_offer(offer_id) -> bool`(`WHERE offer_id = :id AND status <> 'CANCELLED' LIMIT 1`)을 추가하고 `OfferReservationLookup.has_reservations_for_offer`가 이것을 호출한다. 잠금 순서(상품 → 할인 → 예약 insert)는 변하지 않는다 | REQ-17, R11(포트는 쓰는 쪽 정의), R15(에러 코드·문구는 `docs/reference/catalog.md` 그대로) | catalog: 코드 변경 없음(문구·테스트 설명만). reservations: `domain/repository.py`, `infrastructure/repositories.py`, `application/catalog_adapters.py`, fake 2곳(11절) | 확정(요구 조건 확정) |
| D82 | #10 공개 범위 문구 갱신 | requirements 정책 표 "할인 상세 조회", admin.md C7 | D56 문구를 admin.md C7이 요구한 예외(정지된 할인·정지된 상점의 할인은 비소유자 404)와 요구 조건 정책 표(폐점 상점·노출 중단 상품·중단·종료 할인은 공개)에 맞춰 고쳤다. 코드는 이미 같은 동작이다(`src/catalog/application/service.py` `get_offer_detail`: `store.is_visible_to(viewer_id)`와 `offer.is_visible(now, viewer_is_owner=...)`). 폐점 상점은 `is_visible_to`가 숨기지 않으므로 공개가 유지된다 | requirements 정책 표 | `get_offer_detail`(변경 없음), 6.3절·10절 문구 | 확정(요구 조건 확정) |
| D83 | #9 상점 할인 목록 공개 범위 | requirements 정책 표 "상점 할인 목록"("상점주 외에는 공개 노출 상점의, 노출 중 상품의, 정지되지 않은 할인 상품만 보인다(주변 할인 목록과 같은 기준). 상점주는 본인 상점 것을 모두 본다") | ① 비소유자: 서비스가 `store.ensure_products_visible_to(viewer_id)`로 폐점·정지 상점을 404(#2·#4와 같은 `StoreNotFoundError`). ② 비소유자 목록은 노출 중 상품(`products.is_active`)의 비정지 할인만 — **SQL 안**에서 거른다(페이지 `total`이 맞도록, D65·D74와 같은 이유). ③ 소유자: 상품 노출 조건 없음·정지 제외 없음, 폐점·정지 상점도 본인 것이면 조회. ④ 레포 서명: `find_by_store(store_id, *, statuses, now, exposed_only, page, size)`, `exposed_only`는 필수 키워드 인자(기본값이 없어 호출처·fake가 모두 컴파일 시점이 아니라 호출 시점에 드러난다, CI-16). `exposed_only=not is_owner` | requirements 정책 표, D62·D65·D74·D80 | `StoreRef`(변경 없음, docstring만), `list_offers_by_store`, `DiscountOfferRepository.find_by_store`(추상·구현), fake 1곳 | 확정(요구 조건 확정) |
| D84 | #9 소유자 기본 목록에 정지 할인 포함·`status` 허용 값 | 사용자 결정(2026-11-06, 이 설계 발주): 소유자의 기본 목록(status 미지정)에 정지된 할인을 포함한다. 요구 조건 용어 "진행 중인 할인 상품(관리자가 정지한 할인 상품도 포함)", 정책 표 "상점주는 본인 상점 것을 모두 본다" | 상수 `OWNER_DEFAULT_OFFER_STATUSES = OPEN_OFFER_STATUSES + (SUSPENDED,)`(`discount_offer.py`, `OPEN_OFFER_STATUSES` 바로 아래). `OPEN_OFFER_STATUSES`는 공개 기본 집합이라 바꾸지 않는다(admin D20). 소유자는 `status`로 `SUSPENDED`를 지정할 수 있다. router 타입을 `OfferListStatus`(`SCHEDULED, ON_SALE, SOLD_OUT, CLOSED, SUSPENDED`)로 바꾸고, 비소유자·비로그인의 `SUSPENDED`는 서비스가 `OfferStatusNotAllowedError(ValueError, error_code="VALIDATION_ERROR")`로 400 처리해 기존 비소유자 허용 값과 응답 코드를 유지한다. #8은 `PublicOfferStatus`를 그대로 쓴다(D64) | 사용자 결정. 소유 여부는 서비스만 알 수 있어 router의 Pydantic 열거로는 소유자 전용 값을 구분할 수 없다 | `discount_offer.py` 상수, `schemas.py` `OfferListStatus`, `router.py`(#9 `status` 타입), `exceptions.py`, `list_offers_by_store` 4~5단계 | 확정(사용자 결정). 400 메시지 문구는 Q45 |
| D85 | 상태 판정 순서 문서 정합 | requirements "상태와 전이"(중단 → 정지 → 마감 → 시작 전 → 품절 → 판매 중), admin.md 3.3·C6 | 3.4절 `effective_status` 우선순위 설명이 `SUSPENDED` 없이 5단계였던 것을 6단계로 고쳤다(`is_suspended`는 중단 다음, 마감 앞). 코드(`discount_offer.py` `effective_status`, `repositories.py` `_status_clause`)는 이미 이 순서이며 변경 없음 | 요구 조건 순서와 코드가 같음 | 3.4절 | 확정 |
| D86 | 정지된 상점의 할인 등록·재등록·재개 | requirements(커밋 e133e13) 정책 표 "할인 등록·재개·재등록"("상점이 폐점·정지(·미승인)가 아님"), 상태와 전이 표, admin.md D17 | ① 등록(#7)·재등록(#13): `StoreRef.ensure_can_register("할인")`(폐점 → 정지 → 미승인)이 이미 정지를 막는다(400 `STORE_SUSPENDED`). 코드 변경 없음. ② 재개(#11 `is_active:true`): `update_offer`가 `store.ensure_not_closed("할인을 재개")`를 부르던 곳(`service.py:359`)을 `store.ensure_can_resume()`로 교체한다. 검사 위치는 소유자 확인(403) 뒤, `offer.resume` 앞(현재와 같은 자리). 신규 `StoreRef.ensure_can_resume()`: 폐점 → `StoreClosedError`(문구 불변) → 정지 → `StoreSuspendedError`(400 `STORE_SUSPENDED`, 기존 예외 재사용, 새 에러 코드 없음). 오류 우선순위는 7.5절(Q47). 미승인은 검사하지 않는다(이미 열린 할인 재개, D30). ③ 중단(#12·#11 중단)·재고 조정은 정지 상점에서도 허용(요구 조건이 상점 정지를 조건으로 두지 않음) | requirements 정책 표·상태 전이 표 | `store_ref.py`(`ensure_can_resume` 추가), `service.py` `update_offer` | 확정(요구 조건 확정) |
| D87 | 관리자 정지 사유 상한 | requirements 경계값 표(커밋 e133e13: 1~500자) | catalog.md에는 정지 사유 200자 문구가 없음(정지 사유는 admin.md가 다룸). 200은 판매 중단 사유(#12)·재고 조정 사유 전용이며 바뀌지 않는다. 정지 사유 500은 admin 설계·코드가 정본 | requirements, admin.md | catalog 변경 없음 | 확정 |
| Q12 | 종료되는 할인의 남은 재고를 `stock_log`로 기록하거나 복구하는가 | 재고 영향 | 기록·복구하지 않고 `remaining_stock` 유지 (D40) | #13 재등록의 기존 할인 종료와 같은 방식 | `close` | 확정 |
| Q14 | 폐점된 상점의 할인도 중단 허용 | 현재 코드 | 허용(#12는 `ensure_not_closed`를 호출하지 않음). #11 재개는 폐점이면 막는다 | 이미 열려 있던 할인을 닫는 동작은 폐점과 모순되지 않는다 | `deactivate_offer` | 확정 |
| Q16 | #12 `reason` 검증 범위 | 명세(필수·최대 200자) | `min_length=1`, 공백만이면 거부 | "필수"를 빈 값 거부로 해석 | `OfferDeactivateRequest` | 확정 |
| Q19 | #12로 중단한 할인을 #11 `is_active:true`로 재개 | 코드 동작 | 허용(취소된 예약은 복구되지 않음). 마감이 지났으면 `OfferEndedError`, 상품이 비활성이면 `ProductInactiveError`로 막힘 | PATCH 중단과 같은 규칙, 상품이 활성이므로 | `DiscountOffer.resume` | 확정 |
| Q24 | 마감 지난 활성 할인을 #12로 중단할 수 있는가 | 명세 에러 표 | 허용 (D47) | 명세에 "판매 마감" 400이 없고 마감 후 예약 일괄 취소 수단이 남는다 | `deactivate_offer` 6단계 `offer.close(now)` | 확정 |

### 12.2 열린 확인 필요 항목

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 | 바뀔 때 고칠 곳 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| Q22 | #12 `reason`(취소 사유) 저장 | 팀 명세 | 저장하지 않음, 스키마 변경 없음 | 사용자 결정 | `schema.sql`·`db-schema`·`models.py`·서비스(R14) | 후속 |
| Q27 | `cancel_reservations=false`이면 예약이 유지되는 것이 상점주 의도와 맞는지(고객은 예약이 남은 채 할인만 닫힘, C9) | 명세 기본값 | 유지(D41) | 명세 기본값 | `deactivate_offer` 7단계 | 확인 |
| Q28 | `ReservationCancelPort` 계약: 재고 복구 없음, `commit` 금지, 픽업 완료 시 사전 검사, 취소 주체 구분 값(상점주 사유), 취소 사유 저장, 환불은 reservations·payments 책임, 중복 호출 멱등 | 6.4절 | 6.4절 표의 계약 | R5·R12·R13 | `ports.py` docstring과 reservations 어댑터 | 확인(reservations 설계) |
| Q29 | `PickedUpReservationExistsError`의 `error_code` 이름 | 명세에 에러 코드 없음 | `PICKED_UP_RESERVATION_EXISTS` | 기존 `OFFER_CLOSED`·`PRODUCT_INACTIVE` 명명 관례 | `exceptions.py` 한 곳, 7.5 표 | 임시 |
| Q30 | #3 응답에 상품 정보가 없다 | 사용자 확정 명세, reference §3 | 닫힘: 사용자 결정으로 D76, 이후 상점 단위 묶음 D77로 확정 | 사용자 결정 | `schemas.py` | 닫힘(사용자 결정) |
| Q31 | 검색에서도 소유자 예외를 둘 것인가. requirements는 "폐점 상점의 상품 읽기·검색: 상점주 허용"인데 사용자는 인증 없음으로 확정 | requirements 정책 표, 사용자 결정 | 예외 없음, 소유자는 #2로 조회(D63) | 사용자 확정 우선 | router(`OptionalUser` 추가 + 서비스 `viewer_id` + stores 질의 확장) | 확정(사용자 결정) |
| Q32 | 위치 없이 검색할 때 동작: 반경 필터 생략, `distance=null`(명세 필드 타입은 `float`) | reference §3·§8 | 필터 생략, `distance: null`, `radius_km` 무시(D67) | 명세 제안 | `SearchArea.of`, 스키마 `distance` | 확정(사용자 결정) |
| Q33 | `unit` 값과 거리 소수 자리 | reference §3 | `"km"`, 소수 둘째 자리 반올림 | `radius_km` 단위가 km | `search.py` 상수 | 확정(사용자 결정) |
| Q34 | 좌표 없는 상점(지오코딩 실패로 `latitude`·`longitude`가 null)의 처리 | stores 도메인(둘 다 있거나 둘 다 없음) | 위치 지정 시 제외, 미지정 시 포함(`distance=null`) | 거리를 못 구함 | stores `find_visible_near` | 확정(사용자 결정) |
| Q35 | #8 정렬 방향과 동률 처리 | reference §8 확인 필요 | `price` 오름차순, `discount_rate` 내림차순, `sales_end` 마감 임박순, `distance` 가까운 순, 동률 `sales_end → id`(D71) | 명세 제안 | `search_in_stores`의 `ORDER BY` | 확정(사용자 결정) |
| Q36 | 검색어 매칭 방식 | reference §3·§8 | 부분 일치·대소문자 무시, #3 이름+설명, #8 이름만, 100자(D69) | 명세 설명 | `search.py`, 레포 쿼리 | 확정(사용자 결정) |
| Q37 | `has_active_offer`의 "진행 중" 범위(`ON_SALE`만으로 좁힐지) | reference §3, requirements 용어 | SCHEDULED·ON_SALE·SOLD_OUT 포함(D70) | #9 기본 목록과 같은 집합 | `OPEN_OFFER_STATUSES` 사용처 한곳 | 확정(사용자 결정) |
| Q38 | 공개 노출 제외 규칙(폐점·정지·미승인 상점, 노출 중단 상품, 정지 할인). #8에서 상품이 비활성인 할인도 숨길지(#10은 숨기지 않음, D56) | requirements 정책 표 3행, admin 명세 7 | 모두 제외(D61·D62·D64) | 근거 인용은 D61~D64 | stores 노출 조건, 레포 `WHERE` | 확정(사용자 결정) |
| Q39 | 위치 없는 호출은 노출 상점 전체 id를 catalog로 가져온다. 상점 수 상한과 대안 | 14.4 | 상한 없음(현 규모 전제) | 배열 바인드로 파라미터 상한은 회피 | 규모가 커지면 상점 상태·좌표 비정규화(admin C9 대안) 또는 stores가 상한·페이지를 가짐 | 확정(사용자 결정) |
| Q40 | #3 `store` 객체에 더 필요한 필드(예: 상점 상태, 평점 등). 현재 제안은 `id, name, pickup_address, latitude, longitude`(D77) | 사용자 결정 후속 | 5개 필드로 확정 구현, 추가 없음 | `StoreInfo`가 가진 값만 사용 | `StoreSummaryResponse` | 확정(사용자 결정) |
| Q41 | #8 `GET /v1/offers`에도 같은 원칙(할인 + `store` 객체)을 적용할지. 사용자가 명시하지 않음 | 사용자 결정 후속 | 적용하지 않음: `items[]`는 `offer`(이미 `store_id`·`store_name` 포함)·`distance`·`unit` 유지. 적용 시 `NearbyOfferItem`에 `store: StoreSummaryResponse` 추가(StoreInfo로 채울 수 있어 stores 변경 없음) | 사용자 명세는 §8 그대로, 확정되지 않은 변경은 지어내지 않음 | `NearbyOfferItem`·`NearbyOfferView` | 확정(사용자 결정) |
| Q42 | #3 상점 정렬 기준. 위치가 있으면 거리순이지만 없을 때 기준이 없다 | 사용자 결정 후속 | 위치 없으면 상점명 `name ASC`, 같으면 `id ASC`. 이를 위해 stores의 `find_visible_stores`가 위치 미지정일 때 `name ASC, id ASC`로 돌려주도록 계약을 바꿨다(14.3). 대안: 조건 일치 상품 수 내림차순, `has_active_offer` 있는 상점 우선 | 상점명은 사용자가 예측 가능하고 stores만으로 정렬 가능 | stores `find_visible_near`의 `ORDER BY`, D68 | 확정(사용자 결정) |
| Q43 | 한 상점 안 `products[]` 정렬 | 사용자 결정 후속 | `name ASC, id ASC`(#2와 같음). 대안: `has_active_offer=true` 우선 후 `name` | #2 상점 상품 목록 기본 정렬(D15) | `find_matching_in_stores`의 `ORDER BY` | 확정(사용자 결정) |
| Q44 | 한 상점의 `products[]` 개수 상한 필요 여부 | 사용자 결정 후속 | 상한 없음. 한 요청은 상점 최대 100개(`size le=100`)의 일치 상품 전체를 한 번에 읽는다. 대안: 상점당 상위 N개만 담고 `product_total` 필드를 더하는 안(응답 필드 추가라 별도 확인) | 상점당 상품 수가 많지 않다는 전제(요구 조건에 상점당 상품 상한 없음, requirements "상점당 상품 개수 상한 없음") | `find_matching_in_stores`, 스키마 | 확정(사용자 결정) |
| Q45 | #9에서 비소유자가 `status=SUSPENDED`를 보냈을 때 400 메시지 문구(코드는 `VALIDATION_ERROR` 고정) | D84, 요구 조건에 문구 없음 | "status: SUSPENDED은(는) 상점주만 지정할 수 있습니다." | 기존 Pydantic 오류의 `필드: 오류` 형식과 맞춤 | `OfferStatusNotAllowedError` 한 곳 | 닫힘(사용자 결정, 2026-11-06: 임시안 문구 그대로 확정) |
| Q46 | 상점 강제 폐점으로 `is_active=false`가 된 정지 할인(유효 상태 `CLOSED`, 정지 이력 있음)이 비소유자에게 보이는가 | D83, requirements "정지 → 상점 강제 폐점 → 종료(중단됨)" | 유효 상태 기준이라 `CLOSED`로 취급: #10은 공개, #9는 폐점 상점 자체가 404라 목록에 나오지 않음(결과적으로 문제없음) | #10 `is_visible`·`_status_clause`가 유효 상태 기준 | `DiscountOffer.is_visible` | 닫힘(사용자 결정, 2026-11-06: 제안대로 공개 확정) |
| Q47 | 정지된 상점의 정지된 할인을 #11로 재개할 때 어느 에러가 먼저인가 | D86, 요구 조건에 순서 없음 | `STORE_SUSPENDED`가 먼저(현재 코드 순서 유지: 상점 검사 → `offer.resume`) | 코드 변경 최소 | `update_offer` 재개 분기 | 닫힘(사용자 결정, 2026-11-06: 그대로 진행) |
| - | 스키마 S3(`discount_offers.price` 삭제), S6(`products.created_at`) | 4절, db-schema §5 | S3 삭제 보류(모델은 매핑 안 함), S6 보류 | 4절 | `schema.sql`, `db-schema/SKILL.md` | 팀 확인 |
| - | 명세 #14의 403 문구와 422 표기 | 11절 | D8, D14 | 전역 핸들러 동작 | `docs/reference/catalog.md` | 팀 확인 |

---

## 13. 정합 이슈

### 13.1 stores와의 정합 (stores.md 9절)

| stores 이슈 | 상태 | 내용 |
| --- | --- | --- |
| C1 (StoreInfo에 좌표 없음) | 닫힘 | #10 때문에 catalog `StoreInfo`에 `latitude`, `longitude`를 추가한다. stores의 `Store`가 이미 제공하므로 stores 변경은 없다(2.1절). #8도 같은 필드를 쓴다 |
| C3 (생성 순환) | 열림(후속, 조건부) | container 팩토리 한 방향 구조(9.3절). 폐점 구현 시 stores 읽기/쓰기 서비스 분리(D22)가 필요하며 stores.md가 이를 수용해야 닫힌다 |
| admin.md C9 (정지 상점 숨김을 여러 상점 조회 #3·#8에 적용) | 설계로 닫음 | stores가 노출 상점과 거리를 계산하는 `find_visible_stores`(14.3, D65)로 해결. stores 쪽 구현이 필요해 C15로 이어진다 |
| C5 (`StoreNotFoundError` 이름 중복) | 유지 | 서로 다른 모듈의 별개 클래스. catalog는 stores 예외를 import하지 않음(R11) |
| C7 (폐점 차단의 "진행 중" 정의) | 유지 | `has_open_offers_for_store`가 D4 정의를 그대로 공유(2.3절) |

### 13.2 catalog 정합 이슈

| # | 위치 | 이슈 | 영향·제안 |
| --- | --- | --- | --- |
| CI-2 | 2.3 ↔ stores.md 8절 | `has_open_offers_for_store(store_id, *, now=None) -> bool` 서명이 두 문서에서 같아야 구조적 만족이 깨지지 않는다 | 확정 서명이다. `now`는 키워드 전용이고 None이면 주입된 `Clock`을 쓴다 |
| CI-3 | 6.1, 6.3, 7.1 | 서비스는 `user_id`만 받고 비로그인 401은 router가 낸다. 대신 router가 "`is_active=false` 조회는 로그인 필요"를 알아야 한다 | 규칙 자체(소유자만)는 서비스·도메인(`NotStoreOwnerError`)에 있고 router는 인증 여부만 판단한다. 팀이 router 분기를 원하지 않으면 `is_active=false` 목록을 별도 EP(`OwnerUser`)로 분리하는 안을 명세 변경으로 논의 |
| CI-5 | 3.7, 5.2 | 시간 의존 코드(`effective_status`, `_status_clause`)는 `Clock`과 DB `now()` 두 출처를 섞으면 안 된다 | 레포지토리 쿼리는 항상 인자로 받은 `now`(Clock 값)만 사용하고 SQL `now()`를 쓰지 않는다. 테스트로 확인(10절) |
| CI-7 | 5.2 `save` | `save`의 갱신 경로가 가격·시간 컬럼을 빠뜨리면 #11 수정이 DB에 반영되지 않는 조용한 실패가 된다 | 갱신 경로가 `sale_price`, `sales_start`, `sales_end`, `pickup_start`, `pickup_end`를 모두 쓴다. 왕복 테스트로 확인(10절) |
| CI-10 | 6.4 ↔ reservations 설계(미작성) | catalog → reservations(예약 존재 확인)와 reservations → catalog(재고 차감, 6.4)가 양방향이다 | 둘 다 쓰는 쪽이 포트를 정의하고 container가 연결하면 import 순환은 없다. 생성 순환을 피하려면 `create_reservation_lookup`이 reservations **레포지토리만** 받아야 한다(catalog 서비스에 의존 금지). 예약 생성이 offer 행 잠금 아래에서 INSERT 되어야 #11 검사와 직렬화된다(5.3, db-schema §7). reservations 설계에 요구사항으로 전달: `exists_by_offer(offer_id)` 추상 메서드, 잠금 순서(offer 잠금 → 예약 insert). reservations 구현 PR에서 container 바인딩과 `test_wiring.py`의 `NoReservationLookup` 단언을 교체 |
| CI-11 | 6.4 `ReservationCancelPort` ↔ reservations 설계(미작성) | catalog → reservations 쓰기 포트(일괄 취소·환불 요청)가 임시 `NoReservationCancel`(0건)로 연결돼 있다. 어댑터가 reservations 서비스를 `commit=False`로 부르고 그 서비스가 catalog 서비스를 부르면 생성 순환(R12, C12) | 어댑터 경로는 catalog 서비스를 쓰지 않는다(재고 복구 없는 전용 취소 메서드). 픽업 완료 예약 사전 검사 후 `PickedUpReservationExistsError`, commit 금지, 같은 세션. reservations 구현 PR에서 `create_reservation_cancel()` 교체 + `test_wiring.py`의 `NoReservationCancel` 단언 교체 |
| CI-12 | 14.3·14.4 ↔ 기존 fake/구현 | `StorePort`에 메서드가 늘고 `ProductRepository`·`DiscountOfferRepository`(ABC)에 추상 메서드가 늘면 `tests/catalog/test_service.py`의 `FakeStores`·`FakeProducts`·`FakeOffers`가 구현하지 않아 인스턴스 생성(ABC) 또는 호출(Protocol)에서 깨진다. `StorePort`는 Protocol이라 stores 구현이 없어도 import·조립은 성공하고 호출할 때 `AttributeError`가 난다 | 구현 PR이 fake 3종을 함께 갱신하고 `test_wiring.py`가 `create_store_port()` 결과에 `find_visible_stores`가 있는지 확인한다 |
| CI-13 | 14.4 `has_active_offer` ↔ #9 기본 목록 | 같은 "진행 중 할인" 집합을 두 곳이 쓴다 | `OPEN_OFFER_STATUSES`·`_status_clause`만 쓰고 별도 조건을 만들지 않는다. CI-5의 비교 테스트를 `has_active_offer`까지 넓힌다 |
| CI-14 | 14.4 SQL `rate` ↔ 도메인 `discount_rate` | 도메인은 파이썬 정수 연산(버림, D1), SQL 정렬은 두 번째 구현이다. `int4 * 100`은 원가가 21억 근처에서 오버플로하고 DB `CHECK`는 원가 0을 허용해 0으로 나눌 수 있다 | `::bigint` 캐스트와 `NULLIF(original_price, 0)`를 쓰고 도메인 값과 비교하는 테스트를 둔다 |
| CI-15 | 기존 #2·#4·#9 ↔ requirements 정책 표 | requirements는 "폐점 상점의 상품은 상점주 외에는 존재하지 않는 것처럼 다룬다"인데 현재 `StoreRef.is_visible_to`는 정지만 숨기고 폐점은 숨기지 않는다(`src/catalog/domain/store_ref.py:64-66`). 이번 검색은 폐점 상점을 숨기므로 단건·목록 조회와 규칙이 어긋난다 | **닫힘(D80, D82, D83).** 상품(#2·#4)과 상점 할인 목록(#9)이 폐점·정지 상점을 비소유자에게 숨긴다. 할인 상세(#10)는 정지만 숨기고 폐점 상점의 할인은 공개한다(요구 조건 정책 표) |
| CI-16 | `find_by_store` 서명 변경 ↔ 기존 fake·테스트 | `DiscountOfferRepository.find_by_store`에 필수 키워드 `exposed_only`가 늘면 `tests/catalog/test_service.py:192` `FakeOffers.find_by_store(self, store_id, *, statuses, now, page, size)`가 `TypeError`로 깨지고, 직접 부르는 `tests/catalog/test_api_db.py:815,819`·`tests/catalog/test_admin_api_db.py:125,131`도 인자 누락으로 깨진다. 구현 `repositories.py:290-320`·서비스 `service.py:414`도 함께 바뀐다. `tests/admin/test_service.py:194` `FakeOffers`는 별도 클래스(admin 포트용)라 `find_by_store`가 없으면 영향 없음 | 구현 PR이 fake 1곳과 직접 호출 4곳을 `exposed_only`(소유자 검증은 `False`, 공개 검증은 `True`)로 함께 고치고, 새 인자의 두 값에 대한 테스트를 추가한다(CI-12와 같은 유형). `exposed_only`는 **필수 키워드 인자로 확정**(사용자 확인 완료, 2026-11-06). 기본값을 두면 잘못 호출해도 드러나지 않기 때문이다 |
| CI-17 | `exists_by_offer` 사용처 축소 ↔ reservations | D81 이후 `ReservationRepository.exists_by_offer`는 `OfferReservationLookup`에서 더 쓰이지 않는다(`src/reservations/application/catalog_adapters.py:19`가 새 메서드를 호출). 추상 메서드가 남으면 fake 두 곳(`tests/reservations/fakes.py:79`, `tests/payments/test_integration.py:120`)도 계속 구현해야 한다 | 이번 변경은 **추가만** 한다(삭제는 별도 결정). 다른 호출처가 없음을 구현자가 `Grep exists_by_offer\b src`로 확인한 뒤, 사용자가 승인하면 추상·구현·fake에서 삭제한다. 새 추상 메서드 때문에 fake 2곳은 어차피 `exists_non_cancelled_by_offer`를 추가해야 한다. **사용자 결정 대기**: `exists_by_offer` 삭제 여부, `tests/payments/test_integration.py` fake 수정(payments 소유 파일) 승인. 결정 전에는 삭제하지 않고 추가만 한다 |
### 13.3 예약·결제 연계 이슈

| # | 내용 | 영향·해결 |
| --- | --- | --- |
| C9 | `cancel_reservations=false`로 닫힌 할인에 남은 예약(결제 완료 포함)의 픽업·취소·환불을 reservations·payments가 어떻게 다룰지(할인이 CLOSED여도 픽업 가능해야 하는지) 정해지지 않았다. #11 중단과 같은 문제다 | reservations 설계에 요구사항으로 전달: "예약은 할인 `is_active`·`status`와 무관하게 자기 상태로 진행", 예약 생성은 할인 행 잠금 아래에서 `is_active`·`sales_end`를 재확인(5.3, CI-10), 잠금 순서는 상품 → 할인 → 예약 |
| C10 | 할인이 종료돼 폐점이 가능해지고(폐점은 "진행 중 할인이 있으면 불가", 2.3절) 예약이 남은 상점이 폐점될 수 있다 | Q27·C9와 함께 reservations·stores 설계에서 확인 |
| C11 | DB에 "상품당 진행 중 할인 1건" 유니크 제약이 없어 앱 규칙(상품 행 잠금 아래 `find_open_by_product`)에만 의존한다(S7). #12는 할인 1건을 ID로 지정해 중단하므로 이 문제와 무관하다 | 스키마 변경 제안 없음 |
| C12 | **재고·순환**: 예약 취소가 보통 catalog에 재고 복구를 요청한다(reservations → catalog). #12는 catalog → reservations(포트)이므로 어댑터가 reservations 서비스를 쓰고 그 서비스가 catalog 서비스를 쓰면 container에서 생성 순환(R12)이 된다 | 일괄 취소 유스케이스는 재고를 되돌리지 않는 전용 메서드로 만들고(D40) 이 어댑터 경로에서 catalog 서비스를 부르지 않게 한다. 불가피하면 9.3절의 읽기/쓰기 분리 패턴을 쓴다. reservations 설계에 요구사항으로 전달 |
| C13 | 임시 포트 `NoReservationCancel`이 container에 남아 있는 동안 `cancel_reservations=true`도 실제 취소·환불을 하지 않고 `cancelled_reservation_count=0`만 돌려준다 | CI-11(reservations 구현 시 어댑터로 교체). 명세 §12 "확인 필요"에 미연계 상태가 적혀 있다 |
| C14 | #10 `cancel_policy.cancellable_until = pickup_start − 1시간`(D55)은 고객에게 보여주는 약속이다. payments의 위약금·환불 규칙(예약 취소 시 전액 환불 vs 위약금 부과 경계)이 이 시각을 기준으로 해야 화면과 실제 환불이 어긋나지 않는다 | payments·reservations 설계에 요구사항으로 전달: 취소 허용·위약금 경계는 `DiscountOffer.cancel_policy().cancellable_until`(또는 같은 `CANCEL_LEAD_TIME`)에서 가져오고 별도 상수를 두지 않는다. 기준이 바뀌면 `CANCEL_LEAD_TIME`과 `CANCEL_POLICY_DESCRIPTION`(D55)을 함께 고친다 |
| C15 | stores 설계(`docs/design/stores.md` 15절에 반영 완료, 2026-11-06)에  `StoreRepository.find_visible_near`·`StoreQueryService.find_visible_stores`·`StoreWithDistance` 추가와 노출 조건(`approval_at` 있음, `closed_at`·`suspended_at` 없음)·하버사인 SQL이 필요하다. 노출 조건이 `Store` 도메인의 `status`/`is_approved`와 SQL 두 곳에 있어 어긋날 수 있다 | 해결 방향 확정(stores 15절). stores 구현자에게 전달: 노출 조건 SQL과 `Store.status == ACTIVE and is_approved`가 같은 결과인지 비교하는 테스트, 좌표 없는 상점 처리, 거리·경계 테스트. #3·#8 구현은 이 PR이 먼저다 |

---

## 14. #3 상품 검색 · #8 주변 할인 목록 (후속 설계, 코드 미구현)

사용자 확정: #3 경로는 `GET /v1/products`(이전 문서의 `/v1/products/search`는 제안값이었고 폐기), #8 경로는 `GET /v1/offers`. 두 EP는 공개(인증 없음)이고 읽기 전용이다(잠금·`commit` 없음, D75). 기존 `GET /v1/stores/{store_id}/offers`(#9)는 바꾸지 않는다.

### 14.1 핵심 결정 요약

| 쟁점 | 결정 | 결정 번호 |
| --- | --- | --- |
| 여러 상점을 가로지르는 조회에서 폐점·정지 상점을 거르고 거리를 계산하는 방법 (catalog는 `stores` 테이블을 조인할 수 없다, R11) | stores가 "노출 가능한 상점 + 거리"를 계산해 돌려주고(`StorePort.find_visible_stores`), catalog는 그 상점 id 목록으로 자기 테이블을 필터·정렬·페이지한다. 필터가 SQL 안에 있어 `total`이 맞다 (admin.md C9 해법) | D65, D74 |
| 거리 계산 | PostGIS 없음 → stores 인프라의 SQL 하버사인 | D66 |
| 응답 | #3 `items[]` 한 건 = 조건에 맞는 상품을 가진 상점 하나(`store`, `distance`, `unit`, `products[]`). `page`·`size`·`total`은 상점 수 기준 | D77 |

### 14.2 도메인 (`domain/search.py`, 순수 파이썬, R1)

상수(한 곳에 모은다, D67·D69): `DEFAULT_RADIUS_KM = 3.0`, `MIN_RADIUS_KM = 0.1`, `MAX_RADIUS_KM = 20.0`, `DISTANCE_UNIT = "km"`, `DISTANCE_DECIMALS = 2`, `KEYWORD_MAX_LENGTH = 100`.

| 대상 | 정의 | `ValueError` 조건 (전부 400 `VALIDATION_ERROR`) |
| --- | --- | --- |
| `SearchArea` (불변 VO) | `lat: float`, `lng: float`, `radius_km: float` | 아래 `of` |
| `SearchArea.of(lat, lng, radius_km) -> SearchArea \| None` | `lat`·`lng`가 모두 None이면 None(반경 필터 없음, `radius_km`는 무시, D67). 둘 다 있으면 `radius_km`가 None일 때 `DEFAULT_RADIUS_KM`을 써서 생성 | 한쪽만 None: "lat과 lng는 함께 입력해야 합니다."(명세 문구); `lat`이 유한하지 않거나 -90~90 밖: "위도는 -90~90 범위여야 합니다."; `lng`가 -180~180 밖: "경도는 -180~180 범위여야 합니다."; `radius_km`가 0.1~20 밖: "검색 반경은 0.1~20km여야 합니다." (범위는 router `Query`도 막지만 도메인이 정본이다) |
| `OfferSort(StrEnum)` | `DISTANCE="distance"`, `PRICE="price"`, `SALES_END="sales_end"`, `DISCOUNT_RATE="discount_rate"` | - |
| `OfferSort.ensure_usable(area)` | 정렬이 위치 정보를 쓸 수 있는지 확인 | `DISTANCE`인데 `area is None`: "distance 정렬은 위치 정보가 필요합니다."(명세 문구) |
| `normalize_keyword(raw) -> str \| None` | 앞뒤 공백 제거, 빈 문자열이면 None | 100자 초과: "검색어는 100자 이하여야 합니다." |
| `round_distance(km) -> float \| None` | None이면 None, 아니면 `round(km, DISTANCE_DECIMALS)` | - |

- 검증 순서(#8): `SearchArea.of` → `OfferSort.ensure_usable` → `normalize_keyword`. 명세 에러 표의 순서(lat/lng → distance 정렬)와 같다.
- 거리 계산 자체는 도메인에 두지 않는다. 계산은 stores가 SQL로 하고 catalog는 결과값을 받는다(14.3절). 노출 규칙(어떤 상점·상품·할인이 공개 검색에 보이는가)은 14.4의 쿼리 조건 한곳과 stores의 노출 조건 한곳에 있고 D61·D62·D64가 정본이다.

### 14.3 stores 연계: `StorePort` 확장

`catalog/application/ports.py`에 추가한다(쓰는 쪽이 포트를 정의, R11). 기존 `find_store_by_id`, `find_stores_by_ids`는 그대로 둔다.

```python
class StoreWithDistance(Protocol):
    store: StoreInfo
    distance_km: float | None            # 위치 미지정이면 None

class StorePort(Protocol):
    ...
    async def find_visible_stores(
        self,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_km: float | None = None,
    ) -> list[StoreWithDistance]: ...
```

계약:

| 항목 | 계약 |
| --- | --- |
| 노출 가능한 상점 (D61) | `approval_at IS NOT NULL AND closed_at IS NULL AND suspended_at IS NULL` |
| 위치 지정 (`latitude`·`longitude` 모두) | 좌표가 있는 상점만, 하버사인 거리(km) `<= radius_km`(`radius_km`가 None이면 `DEFAULT_RADIUS_KM`은 호출자가 채워 넘긴다). 정렬 거리 오름차순, 같으면 `id` 오름차순. `distance_km`는 반올림하지 않은 값 |
| 위치 미지정 (둘 다 None) | 노출 가능한 모든 상점, `distance_km=None`, `name` 오름차순 → `id` 오름차순(Q42). `radius_km`는 무시 |
| 한쪽만 지정 | stores가 `ValueError`(호출자 catalog가 먼저 막으므로 도달하지 않는 방어) |
| 트랜잭션 | 읽기 전용. 잠금·`commit` 없음. 같은 요청 세션 |

stores 쪽 구현(11절의 제안, 이 문서는 stores를 바꾸지 않는다, C15):
- `StoreRepository.find_visible_near(*, latitude, longitude, radius_km) -> list[StoreWithDistance]` 추상 메서드(`docs/design/stores.md` 15절)와 `SqlAlchemyStoreRepository` 구현.
- `StoreQueryService.find_visible_stores(...)`가 이를 그대로 돌려준다. `StoreWithDistance`는 stores 도메인의 불변 dataclass(`store: Store`, `distance_km: float | None`)다. catalog는 stores를 import하지 않고 구조적으로 맞춘다. container 변경은 없다(`create_store_port`가 이미 `StoreQueryService`를 돌려준다, 9.3절).
- SQL 하버사인(D66): `d = 2 * 6371.0 * asin(sqrt(least(1.0, sin(radians(lat2-lat1)/2)^2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lng2-lng1)/2)^2)))`. `least(1.0, …)`는 부동소수 오차로 `asin` 정의역을 벗어나는 오류를 막는다. 선필터로 위도 범위 `lat1 ± radius/111.0`도(`BETWEEN`)만 쓴다. 경도 범위는 날짜 변경선·극 근처에서 틀리기 쉬워 쓰지 않는다.

### 14.4 인프라: 레포지토리 메서드와 SQL

추상(3.6절 표에 추가)과 구현 시그니처:

| 추상 | 메서드 |
| --- | --- |
| `ProductRepository` | `search_store_ids(*, store_ids: Sequence[uuid.UUID], keyword: str \| None, category: str \| None, page: int, size: int) -> tuple[list[uuid.UUID], int]` — 조건에 맞는 상품을 1개 이상 가진 상점 id를 페이지 단위로(상점 순서 유지)와 상점 수 `total`; `find_matching_in_stores(*, store_ids: Sequence[uuid.UUID], keyword: str \| None, category: str \| None, now: datetime) -> list[tuple[Product, bool]]` — 그 상점들의 조건 일치 상품과 `has_active_offer` |
| `DiscountOfferRepository` | `search_in_stores(*, store_ids: Sequence[uuid.UUID], status: OfferStatus, keyword: str \| None, category: str \| None, sort: OfferSort, now: datetime, page: int, size: int) -> tuple[list[tuple[DiscountOffer, Product]], int]` |

- 두 메서드 모두 도메인 객체만 주고받고 `*Model`을 내보내지 않는다(R4). `commit`·`flush` 없음(읽기). `now`는 인자로만 받고 SQL `now()`를 쓰지 않는다(CI-5).
- `store_ids`는 stores가 돌려준 순서(위치 지정이면 거리 오름차순)를 그대로 가진다. 빈 목록이면 서비스가 레포를 부르지 않는다(14.6).
- 상점 필터(D74): `ProductModel.store_id = ANY(:ids)`(배열 바인드 파라미터 하나, `ARRAY(UUID(as_uuid=True))`). `IN (...)`처럼 id마다 바인드 파라미터를 만들면 asyncpg의 쿼리 파라미터 상한(32767)에 걸리므로 쓰지 않는다. 거리순 정렬은 같은 배열로 `array_position(:ids, products.store_id)`를 쓴다(stores가 계산한 거리 순서가 그대로 정렬 키가 된다).

**상품 검색 쿼리 (상점 단위 페이지, D77)**: 요청당 쿼리는 상점 조회 1 + `search_store_ids` 2(`count`, id 페이지) + `find_matching_in_stores` 1 = 4개다. 상점 id를 페이지로 먼저 정한 뒤 그 상점들의 일치 상품만 읽으므로 `total`과 페이지가 상점 수 기준이고 상품 행이 페이지를 잡아먹지 않는다. 공통 상품 조건(`상품 조건`)은 두 메서드가 같은 함수로 만든다.

| 상품 조건 | SQL |
| --- | --- |
| 노출 상점 | `products.store_id = ANY(:ids)` |
| 노출 상품 (D62) | `products.is_active` |
| 카테고리 | `products.category = :category` (정확 일치, #2와 같음) |
| 검색어 (D69) | `products.name ILIKE :pat ESCAPE '\' OR products.description ILIKE :pat ESCAPE '\'`. `pat = '%' + escape(keyword) + '%'`이고 `escape`는 `\`·`%`·`_`를 `\`로 이스케이프 |

| 메서드 | SQL |
| --- | --- |
| `search_store_ids` total | `SELECT count(DISTINCT products.store_id) FROM products WHERE <상품 조건>` |
| `search_store_ids` 페이지 | `SELECT products.store_id FROM products WHERE <상품 조건> GROUP BY products.store_id ORDER BY array_position(:ids, products.store_id) OFFSET (page-1)*size LIMIT size`. `:ids`는 stores가 정렬해 준 순서(거리순, 없으면 상점명순, Q42)라 항상 이 정렬 키를 쓴다(이전의 `by_store_order` 인자는 없다) |
| `find_matching_in_stores` | `SELECT products.*, EXISTS(<has_active_offer>) FROM products WHERE <상품 조건> AND products.store_id = ANY(:page_ids) ORDER BY products.name, products.id` (D68, Q43). `has_active_offer`는 상관 `EXISTS (SELECT 1 FROM discount_offers o WHERE o.product_id = products.id AND (<_status_clause(SCHEDULED)> OR <_status_clause(ON_SALE)> OR <_status_clause(SOLD_OUT)>))`이고 `OPEN_OFFER_STATUSES`·`_status_clause`를 그대로 쓴다(D70, CI-13). 행 수 상한 없음(Q44) |

**주변 할인 쿼리 (`DiscountOfferRepository.search_in_stores`)**: `discount_offers JOIN products`.

| 조건 | SQL |
| --- | --- |
| 노출 상점·상품 | `products.store_id = ANY(:ids) AND products.is_active` (D61·D62) |
| 상태 | `_status_clause(status, now)` 하나. `status`는 `PublicOfferStatus`(`SUSPENDED` 없음)라 정지된 할인은 어떤 값으로도 나오지 않는다(D64) |
| 카테고리 / 검색어 | `products.category = :category` / `products.name ILIKE :pat ESCAPE '\'`(상품명만, 명세) |

| `sort` | `ORDER BY` (D71) |
| --- | --- |
| `distance` | `array_position(:ids, products.store_id) ASC, discount_offers.sales_end ASC, discount_offers.id ASC` |
| `price` | `discount_offers.sale_price ASC, discount_offers.sales_end ASC, discount_offers.id ASC` |
| `sales_end` | `discount_offers.sales_end ASC, discount_offers.id ASC` |
| `discount_rate` | `rate DESC, discount_offers.sales_end ASC, discount_offers.id ASC` |

- `rate` SQL은 도메인 `discount_rate`(D1, 버림 정수 연산)와 같아야 한다: `((products.original_price - discount_offers.sale_price)::bigint * 100) / NULLIF(products.original_price, 0)`. `bigint` 캐스트가 필요하다(`int4 * 100`이 21억 근처 가격에서 오버플로, CI-14). 정수 나눗셈이라 버림이다. 테스트는 같은 데이터로 도메인 값과 SQL 정렬 결과를 비교한다.
- 스키마 변경은 없다(S 번호 추가 없음). 키워드 `ILIKE '%…%'`는 인덱스를 못 쓰고 `products`를 훑는다. 상점 id 필터가 먼저 범위를 줄인다. 규모가 커지면 `pg_trgm` GIN 인덱스를 검토한다(지금은 보류, 별도 요청 때 `schema.sql`·`db-schema`와 함께).

### 14.5 표현: 쿼리·응답·에러·등록

**쿼리 매개변수** (모두 선택, 형식 오류·범위 위반은 전역 핸들러가 400 `VALIDATION_ERROR`로 바꾼다. 명세의 422는 반영되지 않는다, D14·D75)

| EP | 이름 | 타입 | 기본 | 검증 (`Query`) |
| --- | --- | --- | --- | --- |
| #3 | `keyword` | str | - | `max_length=100`, 빈 값·공백은 미지정 취급 |
| #3 | `category` | str | - | `max_length=80`, 정확 일치 |
| #3 | `lat` / `lng` | float | - | `ge=-90, le=90` / `ge=-180, le=180`. 한쪽만 보내면 도메인이 400 "lat과 lng는 함께 입력해야 합니다." |
| #3 | `radius_km` | float | `DEFAULT_RADIUS_KM`(3) | `ge=0.1, le=20`. 위치 없이 보내면 무시(범위 검증은 항상) |
| #3 | `page` / `size` | int | 1 / 20 | `PageParam` / `SizeParam`(`ge=1`, `size le=100`, 기존 별칭 재사용) |
| #8 | `lat`, `lng`, `radius_km`, `category`, `page`, `size` | #3과 같음 | | |
| #8 | `keyword` | str | - | `max_length=100`, 상품명만 검색 |
| #8 | `status` | `PublicOfferStatus` (**단일 값**, 명세) | `ON_SALE` | 허용 외 값 400. `SUSPENDED`는 허용하지 않는다(D64). #9처럼 반복 가능한 목록이 아니다 |
| #8 | `sort` | `OfferSort` | `sales_end` | 허용 외 값 400. `distance`는 위치 필요(D72) |

**응답 스키마** (`schemas.py`)

| 스키마 | 필드 |
| --- | --- |
| `StoreSummaryResponse` | `id: UUID`, `name: str`, `pickup_address: str`, `latitude: float \| None`, `longitude: float \| None` (D77). `StoreInfo`가 이미 모두 가진다 |
| `SearchedProductResponse` | `ProductResponse`의 모든 필드(`id, store_id, name, category, description, original_price, is_active, product_image`, #4와 같은 정의 재사용) + `has_active_offer: bool` |
| `StoreSearchItem` | `store: StoreSummaryResponse`, `distance: float \| None`, `unit: str`, `products: list[SearchedProductResponse]`(1개 이상) |
| `ProductSearchResponse` | `items: list[StoreSearchItem], page, size, total`(상점 수 기준, D77) |
| `NearbyOfferItem` | `offer: OfferResponse`(17개 필드 재사용), `distance: float \| None`, `unit: str` |
| `NearbyOfferListResponse` | `items: list[NearbyOfferItem], page, size, total` |

- 각 스키마는 `from_hit` / `from_view` 팩토리로 만든다. `distance`는 view에서 `round_distance`를 거친 값이고 `unit`은 항상 `DISTANCE_UNIT`(위치가 없어도 "km", D67).
- `OfferResponse.status`는 `effective_status`라 `SUSPENDED`가 나오지 않는다(`status` 필터가 걸러냄).

**에러** (R7 형식 `{"success": false, "error_code", "message"}`)

| 상황 | 상태 | `error_code` | 메시지 | EP |
| --- | --- | --- | --- | --- |
| `lat`·`lng` 한쪽만 | 400 | `VALIDATION_ERROR` | lat과 lng는 함께 입력해야 합니다. | #3, #8 |
| `sort=distance`인데 위치 없음 | 400 | `VALIDATION_ERROR` | distance 정렬은 위치 정보가 필요합니다. | #8 |
| `radius_km`·`lat`·`lng` 범위 위반, `page`·`size`, `status`·`sort` 허용 외 값 | 400 | `VALIDATION_ERROR` | `필드: 오류` | #3, #8 (명세의 422) |
| 결과 없음 | 200 | - | `items: []`, `total: 0` | #3, #8 |

401·403·404는 없다(공개, 상점·상품 존재 판단 없음).

**라우터** (`presentation/router.py`): 함수 2개(`search_products`, `list_nearby_offers`)를 추가한다. 인증 의존성(`OwnerUser`·`OptionalUser`)을 쓰지 않는다. 서비스는 `Depends(provide_catalog_service)`로 받고(R9) 예외를 잡지 않는다(R6). 등록 순서는 무관하다(7.2절). 새 `provide_*`는 없다.

### 14.6 응용: 서비스 시나리오 (읽기 전용: 조회 → 조합, `commit` 없음)

`views.py`에 추가: `StoreSearchHit(store: StoreInfo, distance_km, products: list[SearchedProduct])`, `SearchedProduct(product, has_active_offer)`, `NearbyOfferView(view: OfferView, distance_km)`. 서비스 생성자 인자는 늘지 않는다(포트가 확장될 뿐이다).

**#3 `search_products(*, keyword, category, lat, lng, radius_km, page, size) -> Page[StoreSearchHit]`**
1. `now = clock.now()`
2. `area = SearchArea.of(lat, lng, radius_km)` (400); `kw = normalize_keyword(keyword)` (400)
3. `visible = stores.find_visible_stores(latitude=area.lat, longitude=area.lng, radius_km=area.radius_km)` (`area`가 None이면 인자 모두 None)
4. `visible`이 비면 `Page(items=[], page, size, total=0)`를 돌려주고 끝낸다(레포 호출 없음)
5. `page_ids, total = products.search_store_ids(store_ids=[v.store.id …], keyword=kw, category=category, page=page, size=size)` — `total`은 상점 수. `page_ids`가 비면 빈 `Page`(`total` 유지)를 돌려주고 끝낸다
6. `rows = products.find_matching_in_stores(store_ids=page_ids, keyword=kw, category=category, now=now)`
7. `by_id = {v.store.id: v}`; `rows`를 `product.store_id`로 묶고(`page_ids` 순서대로 `items`를 만든다) 각 상점마다 `StoreSearchHit(store=by_id[sid].store, distance_km=round_distance(by_id[sid].distance_km), products=[SearchedProduct(p, flag), …])`. 묶기는 조합일 뿐이고 비즈니스 판단이 없다(R3)

**#8 `list_nearby_offers(*, lat, lng, radius_km, category, keyword, status, sort, page, size) -> Page[NearbyOfferView]`**
1. `now`; `area = SearchArea.of(...)` (400); `sort.ensure_usable(area)` (400); `kw = normalize_keyword(keyword)`
2. `visible = stores.find_visible_stores(...)`; 비면 빈 `Page`
3. `rows, total = offers.search_in_stores(store_ids=…, status=status, keyword=kw, category=category, sort=sort, now=now, page=page, size=size)`
4. 각 `(offer, product)`를 `_offer_view(offer, product, store_name, now)`로 `OfferView`로 만들고(`store_name`은 `by_id[product.store_id].store.name`), `distance_km=round_distance(...)`와 함께 `NearbyOfferView`로 묶는다

- 두 시나리오의 상점 조회(1개 쿼리)와 상품·할인 조회(`count` + 페이지, 2개 쿼리)는 같은 요청 세션에서 따로 실행되어 한 시점이 아니다. 그 사이에 상점이 폐점·정지되면 한 번 더 노출될 수 있으며 읽기 전용이라 허용한다(D75).
- 비즈니스 판단(위치 쌍 검증, 정렬 사용 가능 여부, 거리 반올림)은 도메인 함수가 하고 서비스는 조합한다(R3). 서비스에 `select()`가 없다(R3).

### 14.7 테스트 계획 (추가분)

- **domain** (`tests/catalog/test_domain.py`): `SearchArea.of` — 둘 다 None → None, 한쪽만 → 명세 문구, 경계값(-90/90/-180/180/0.1/20 통과, 범위 밖·NaN·inf 거부), `radius_km=None`이면 3, 위치 없이 `radius_km`를 줘도 None; `OfferSort.ensure_usable`; `normalize_keyword`(공백, 빈 값, 100자/101자); `round_distance`.
- **application** (fake 레포·`StorePort`·고정 `Clock`): `FakeStores`에 `find_visible_stores`를 추가한다(기존 fake가 이 메서드가 없으면 호출 시 `AttributeError`, CI-12). #3·#8 공통: 상점이 비면 레포 호출 0회·`total=0`, `commit` 0회, `store_ids`가 stores가 준 순서(거리순)대로 전달, #3은 `search_store_ids` → `find_matching_in_stores` 순서로 호출하고 `page_ids`가 비면 두 번째 호출이 없음, 상점 단위 묶기(상점당 `products[]`, `page_ids` 순서 유지), 위치 없으면 인자 모두 None, 거리 반올림, 상점 이름 매핑, 400 순서(`lat`/`lng` 쌍 → distance 정렬).
- **infrastructure (DB)**: 상점 필터 `= ANY(array)`가 id 배열이 32767개를 넘어도 동작(바인드 파라미터 상한 회귀 방지), 키워드 이스케이프(`%`, `_`, `\` 포함 검색어가 리터럴로 매칭), 대소문자 무시, 상품 `is_active=false` 제외, `has_active_offer` — 할인 4종(SCHEDULED/ON_SALE/SOLD_OUT/CLOSED)·정지·마감 지남에서 `OPEN_OFFER_STATUSES` 기준 값(CI-13), `total`이 상점 수와 일치(상품이 많은 상점이 페이지를 차지하지 않음, 한 상점의 일치 상품 3개가 `total`을 1로 셈), 조건 일치 상품이 없는 상점은 제외, `array_position` 정렬이 입력 id 순서와 일치, `products[]` 정렬 `name, id`, #8 정렬 4종의 방향·동률 처리, SQL `rate` 정렬이 도메인 `discount_rate`와 같은 순서(원가 21억대 가격 포함, 오버플로 없음).
- **presentation (DB, 실제 임시 포트·실제 stores 구현)**: 인증 헤더 없이 200; 폐점·정지 상점, 노출 중단 상품, 정지 할인이 검색·주변 목록에 안 나옴; 반경 안·밖 경계, 좌표 없는 상점(위치 지정 시 제외, 미지정 시 `distance: null`), 위치 미지정 시 전체; `lat`만/`lng`만 → 400 명세 문구; `sort=distance` 위치 없음 → 400 명세 문구; `radius_km=0.09/20.1`, `lat=91`, 허용 외 `status`·`sort` → 400 `VALIDATION_ERROR`; `GET /v1/products`와 `GET /v1/products/{product_id}` 공존(둘 다 200), `GET /v1/offers`와 `GET /v1/offers/{offer_id}` 공존; 응답 최상위·`items[]` 필드 집합이 확정 구조와 정확히 일치(#3 `items[]`는 `store`·`distance`·`unit`·`products`, `store`는 5개 필드, `products[]` 항목은 #4와 같은 `ProductResponse` 필드 + `has_active_offer`; #8 `offer`·`distance`·`unit`); 한 상점의 일치 상품이 `products[]`에 모두 들어가고 일치하지 않는 상품은 빠짐.
- **조립**: `create_store_port()`가 돌려주는 객체가 `find_visible_stores`를 가졌는지(CI-12). `test_wiring.py`의 라우트 수 단언은 이 두 EP만큼(+2) 늘린다(현재 값은 구현 시 확인).
