# catalog 모듈 설계안

- 대상: `src/catalog` (products, discount_offers, stock_log)
- 기준 문서: `docs/reference/catalog.md`, `.claude/skills/db-schema/schema.sql`, `.claude/skills/backend-invariants`(R1~R16), `.claude/skills/layer-architecture`(§3.4, §5~§8), `.claude/skills/layer-implementation`
- 범위 EP 12개: #1 상품 등록, #2 상점 상품 목록, #4 상품 상세, #5 상품 수정, #6 상품 노출 중단, #7 할인 등록, #9 상점 할인 목록, #10 할인 상세, #11 할인 수정, #12 할인 판매 중단, #13 할인 재등록, #14 재고 수동 조정
- 번호는 `docs/reference/catalog.md`의 절 번호이고, `docs/reference/README.md` 표에서는 #10(할인 상세)이 17번 행, #12(할인 판매 중단)가 19번 행이다.
- "임시"로 표시한 결정은 확정이 아니라 제안이며 12절 표에 모았다.

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
    ports.py                 # StorePort, StoreInfo, ReservationLookupPort, ReservationCancelPort (Protocol)
    views.py                 # OfferView, OfferDetailView, ProductDetailView, StockAdjustResult, DeactivateOfferResult, Page
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
| 여러 상점 일괄 조회 | 후속 #8(주변 할인) | `find_stores_by_ids(ids) -> list[StoreInfo]` (지금은 쓰지 않음) |

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
- `ensure_can_register(what: str)`: 폐점이면 `StoreClosedError("폐점된 상점에서는 {what}을 등록할 수 없습니다.")`, 미승인이면 `StoreNotApprovedError("승인되지 않은 상점에는 {what}을 등록할 수 없습니다.")` (`what`은 "상품" 또는 "할인"). 검사 순서는 폐점 → 미승인(D9).
- `ensure_not_closed(action)`: 이미 등록된 대상에 대한 동작용. 폐점이면 `StoreClosedError("폐점된 상점에서는 {action}할 수 없습니다.")`. 미승인은 검사하지 않는다(할인 재개에서 `"할인을 재개"`를 넘긴다).

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

`effective_status(now)` 우선순위:
1. `not is_active` → `CLOSED`
2. `now >= sales_end` → `CLOSED`
3. `now < sales_start` → `SCHEDULED`
4. `remaining_stock == 0` → `SOLD_OUT`
5. 그 외 `ON_SALE`

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
| `DiscountOfferRepository(ABC)` | `discount_offer_repository.py` | `find_by_id(offer_id, for_update=False) -> DiscountOffer \| None`; `find_with_product(offer_id) -> tuple[DiscountOffer, Product] \| None`; `find_open_by_product(product_id, now) -> DiscountOffer \| None`; `exists_open_by_store(store_id, now) -> bool`; `find_by_store(store_id, *, statuses, now, page, size) -> tuple[list[tuple[DiscountOffer, Product]], int]`; `save(offer) -> DiscountOffer` |
| `StockLogRepository(ABC)` | `stock_log_repository.py` | `add(log) -> StockLog` |

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
- `find_by_store(store_id, *, statuses, now, page, size) -> tuple[list[tuple[DiscountOffer, Product]], int]` (products 조인, `or_(*[_status_clause(s, now) for s in statuses])`, 정렬 `sales_end ASC, id ASC`)
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
   - `changes == {"is_active": True}`: `store.ensure_not_closed("할인을 재개")`; `has_other = offers.find_open_by_product(product.id, now) is not None`(자기 자신은 `is_active=false`라 걸리지 않음); `offer.resume(now, product_active=product.is_active, has_other_open_offer=has_other)`
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

**#9 `list_offers_by_store(store_id, statuses: Sequence[OfferStatus] | None, page, size) -> Page[OfferView]`**
1. `store = _load_store(store_id)` (404)
2. `statuses`가 None이거나 비어 있으면 `OPEN_OFFER_STATUSES`, 아니면 중복 제거(`dict.fromkeys`) 후 사용(D25)
3. `offers.find_by_store(store_id, statuses=..., now=now, ...)` → 각 항목을 `OfferView`로 변환 (`store_name`은 한 번만 조회한 값 사용)

**#10 `get_offer_detail(offer_id) -> OfferDetailView`** (공개, 잠금 없음, commit 없음)
1. `now = clock.now()`
2. `found = offers.find_with_product(offer_id)` — 없으면 `OfferNotFoundError()` (404)
3. `offer, product = found`; `info = stores.find_store_by_id(product.store_id)`, `store = StoreRef.from_info(info)` — 포트가 None이면 `OfferNotFoundError()` (404 "할인 판매를 찾을 수 없습니다.", D56. FK상 정상 데이터에서는 발생하지 않는다). `_load_store`는 쓰지 않는다
4. 공개 범위(D56): 할인 `is_active`·`status`(중단·마감·품절), 상품 `is_active=false`, 상점 폐점(`closed_at`)을 이유로 숨기지 않는다. 상태는 응답의 `offer.status`·`offer.is_active`로 표시하고 상품·상점 상태 값은 응답에 추가하지 않는다
5. `OfferDetailView(view=_offer_view(offer, product, store.name, now), description=product.description, product_image=product.product_image, pickup_address=store.pickup_address, latitude=store.latitude, longitude=store.longitude, notice=OFFER_NOTICE, cancel_policy=offer.cancel_policy())`
- 비즈니스 계산(취소 가능 시각, 할인율, 유효 상태)은 도메인 메서드가 하고 서비스는 조합만 한다(R3). 인증을 받지 않으므로 서비스 인자에 `user_id`가 없고 router도 인증 의존성이 없다.
- 오류: 404 하나(할인 없음). 잘못된 UUID는 전역 핸들러의 400 `VALIDATION_ERROR`.

### 6.4 모듈 간 트랜잭션 경계

- catalog는 stores를 읽기만 한다(같은 요청 세션, container에서 `Depends(get_db)` 공유).
- 예약 존재 확인(읽기, #11): `ReservationLookupPort.has_reservations_for_offer(offer_id) -> bool` (D28). 임시 구현 `NoReservationLookup`은 항상 False. "예약"은 상태와 관계없이 한 건이라도 있으면 포함한다(취소 건 포함). #11은 할인 행을 `FOR UPDATE`로 잠근 상태에서 포트를 호출하고, 예약 생성도 할인 행을 잠그고 재고를 차감한 뒤 INSERT 해야 직렬화된다(5.3, db-schema §7, CI-10).
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
| 4 | GET | `/v1/products/{product_id}` | - | `ProductDetailResponse` | 200 | 404(없음, 또는 비활성+비소유) |
| 5 | PATCH | `/v1/products/{product_id}` | `ProductUpdateRequest` | `ProductResponse` | 200 | 400(항목 없음, 할인가 이하), 401, 403, 404 |
| 6 | POST (상품 노출 중단) | `/v1/products/{product_id}/deactivate` | 없음 | `ProductResponse` | 200 | 400(이미 비활성, 진행 중 할인), 401, 403, 404 |
| 7 | POST | `/v1/products/{product_id}/offers` | `OfferCreateRequest` | `OfferResponse` | 201 | 400(가격·시간·비활성 상품·진행 중 할인·상점), 401, 403, 404 |
| 9 | GET | `/v1/stores/{store_id}/offers` | 쿼리(`status` 반복 가능) | `OfferListResponse` | 200 | 400(status 값 등), 404(상점) |
| 10 | GET | `/v1/offers/{offer_id}` | - | `OfferDetailResponse` | 200 | 400(잘못된 UUID `VALIDATION_ERROR`), 404(할인 없음). 인증 없음(공개) |
| 11 | PATCH | `/v1/offers/{offer_id}` | `OfferUpdateRequest` | `OfferResponse` | 200 | 400(항목 없음·종료·예약 있음·가격·시간·재개 조건), 401, 403, 404 |
| 12 | POST (할인 판매 중단) | `/v1/offers/{offer_id}/deactivate` | `OfferDeactivateRequest{reason, cancel_reservations}` | `OfferDeactivateResponse{offer, cancelled_reservation_count}` | 200 | 400(이미 중단, 픽업 완료 예약, `VALIDATION_ERROR`), 401, 403, 404 |
| 13 | POST | `/v1/offers/{offer_id}/relist` | `OfferCreateRequest` | `OfferResponse`(신규) | 201 | 400(이미 중단, 가격·시간), 401, 403, 404 |
| 14 | POST | `/v1/offers/{offer_id}/stock-adjustments` | `StockAdjustmentRequest` | `StockAdjustmentResponse` | 200 | 400(0, 초과 차감, 중단, 상한), 401, 403, 404 |

- 요청 형식 오류(Pydantic)는 프로젝트 전역 핸들러가 **400 `VALIDATION_ERROR`**로 바꾼다(`error_handlers.py`). 명세의 422는 반영되지 않는다(D14).
- 모든 에러 본문은 `{"success": false, "error_code", "message"}`(R7).
- 라우터는 서비스만 호출하고 예외를 잡지 않는다. 쓰기 EP는 `owner.id`를, 읽기 EP #2·#4는 `viewer.id if viewer else None`을 서비스에 넘긴다.
- 경로 충돌: 후속 `GET /v1/products/search`는 `GET /v1/products/{product_id}`보다 **먼저** 등록한다.
- 같은 경로 `/v1/offers/{offer_id}`에 #10 GET과 #11 PATCH가 공존한다. FastAPI는 경로와 메서드 조합으로 라우트를 구분하므로 두 함수를 같은 router에 등록하면 충돌하지 않고 순서도 무관하다. 후속 #8 `GET /v1/offers`는 경로가 달라 영향이 없다. `/v1/offers/` 아래에 `{offer_id}` 하나를 받는 정적 경로(예: `/offers/search`)를 만들게 되면 `{offer_id}`보다 먼저 등록한다.
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
| #9 | `status` | `list[OfferStatus]` (반복 가능) | 미지정 시 `SCHEDULED`+`ON_SALE`+`SOLD_OUT`(진행 중 전체, D25) | 허용 외 값은 400. 유효 상태 기준 필터(여러 값은 OR). `CLOSED`는 명시할 때만. 정렬 `sales_end` 오름차순. `?status=ON_SALE` 단일 호출도 동작 |

정렬 옵션은 제공하지 않는다(명세에 #2·#9 정렬 매개변수 없음). 주변 할인 목록(후속 #8)은 구매자 탐색용이라 기본 `ON_SALE`을 유지한다.

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

- #3 상품 검색 `GET /v1/products/search` — 위경도 하버사인 거리와 `has_active_offer`, `store_name` 조인이 필요해 stores 좌표 조회 방식이 먼저 정해져야 함.
- #8 주변 할인 목록 `GET /v1/offers` — 반경·정렬(`distance/price/sales_end/discount_rate`)·`StorePort.find_stores_by_ids`(좌표 포함) 필요.
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
- 예약 포트 교체(CI-10, CI-11): reservations 구현 시 `create_reservation_lookup`은 reservations의 추상 레포지토리(`exists_by_offer`)를 받는 어댑터를, `create_reservation_cancel`은 reservations 서비스를 `commit=False`로 부르는 어댑터를 돌려주게 바꾼다. 어댑터는 reservations 쪽 또는 container가 소유하고 catalog는 import하지 않는다.

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

- **domain**: `Product`(등록·수정 검증, `deactivate` 순서), `DiscountOffer`(등록 검증, 시간 경계, `effective_status` 표, 재고 조정 전 경우, 9999 상한, `close`/`pause`/`resume`, `apply_changes`), `StoreRef`(`ensure_not_closed` 포함), `StockLog.offer_edit`, `discount_rate` 버림, `cancel_policy()`(`pickup_start − CANCEL_LEAD_TIME`, `pickup_start`가 이미 지나 있어도 계산, timezone 유지, 설명 문구는 상수), `StoreRef.from_info`의 좌표 복사(값·None), `OPEN_OFFER_STATUSES`가 `is_open`이 참인 `effective_status` 집합과 같음.
  - `apply_changes`: 필드별 성공; 빈 dict·허용 외 키·None 거부; 병합 검증(`sale_price`만 바꿔도 `original_price`와 비교, `sales_end`만 바꿔 `pickup_end`보다 늦으면 400, `sales_start`만 바꿔 `sales_end` 이후면 400); `initial_stock` 증감(+/-)과 반환 delta; 수동 차감 후 `initial_stock`을 줄여 `remaining`이 음수가 되는 경우 400; 중단·마감 지난 할인 `OfferClosedError`; `has_reservations=True` `OfferHasReservationsError`; 검사 순서(닫힘이 예약보다 먼저); 실패 시 상태가 일부도 바뀌지 않음.
  - `pause/resume`: 정상, 이미 중단, 이미 활성, 마감 지남(양쪽), 비활성 상품, 다른 진행 중 할인, 재개 후 `effective_status`(재고 0이면 `SOLD_OUT`, 시작 전이면 `SCHEDULED`).
  - `close`: 활성 할인은 `is_active=False`·`CLOSED`, 재호출은 `OfferClosedError("이미 중단된 할인입니다.")`, 마감 지난 활성 할인도 통과(Q24).
- **application (fake 레포 3종·`StorePort`·두 예약 포트·고정 `Clock`)**:
  - 쓰기 EP마다 `commit` 1회, 실패 시 0회. #13 중간 예외 시 기존 할인이 닫히지 않음. #14의 `StockLog` 부호.
  - #9: `statuses=None` → 레포에 `OPEN_OFFER_STATUSES` 전달, 중복 제거, 값 지정 시 그대로(D25).
  - #10: 레포가 None이면 `OfferNotFoundError`; 상점 포트가 None이면 `OfferNotFoundError`(`StoreNotFoundError` 아님, D56); 중단·마감·비활성 상품·폐점 상점 fake 데이터에서도 예외 없이 `OfferDetailView`를 돌려줌(D56); `commit` 0회; 좌표 None 전달; `notice`·`cancel_policy`가 도메인 상수·메서드 값; 기존 fake `StoreInfo`에 `latitude`·`longitude` 속성을 추가해 `StoreRef.from_info`가 깨지지 않게 한다.
  - #11: 잠금 호출 순서(product → offer)를 fake에서 기록해 단언, 403 비소유자, 404, `delta != 0`일 때만 `stock_log` 1건, 예약 포트 True면 400, 재개 시 `find_open_by_product` 호출.
  - #12: `cancel_reservations=false`면 포트 호출 0회·상품 `is_active` 불변·`remaining_stock`/`stock_log` 불변(D40)·`products.save` 호출 없음; `true`이고 포트가 3을 돌려주면 올바른 `offer_id`·`reason`으로 1회 호출되고 `cancelled_reservation_count == 3`; 포트가 `PickedUpReservationExistsError`면 전파되고 `commits == 0`; 이미 중단된 할인은 `OfferClosedError`·포트 호출 0회; 마감 지난 활성 할인 성공(Q24); 404 → 403 순서; 폐점 상점 성공(Q14); 잠금 순서(할인 무잠금 조회 → 상품 `for_update` → 할인 `for_update` → 포트 → `commit`).
- **infrastructure (DB)**: `_status_clause`와 `effective_status` 결과 일치(상태 4종 × 시간 경계, CI-5), `find_by_store` 페이지·total(다중 상태 포함), `save` 갱신 후 다시 읽어 가격·시간 5개 컬럼과 `status` 반영(CI-7), `for_update` 직렬화(동시 2건 조정), 동시 PATCH vs `adjust_stock`에서 `stock_log` 합 = `remaining_stock`, 동시 #12 vs `adjust_stock`·#12 vs `relist_offer`에서 교착 없음(product → offer 순서).
- **presentation (DB, 실제 임시 포트)**:
  - #9: 기본 호출에 `SCHEDULED`·`ON_SALE`·`SOLD_OUT`이 나오고 `CLOSED`(중단, 마감 지남)는 안 나옴; `status=CLOSED` 명시 시 나옴; 다중 `status`; 단일 `status=ON_SALE`; 잘못된 값 400 `VALIDATION_ERROR`.
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
| D28 | "예약 0건일 때만 수정" 판정 | 명세 #11, reservations 미구현 | catalog가 `ReservationLookupPort.has_reservations_for_offer(offer_id)`를 정의하고, 임시 구현 `NoReservationLookup`(항상 False)을 container에 연결. "예약"은 상태와 관계없이 한 건이라도 있으면 포함(취소 건 포함). reservations 구현 때 바인딩 교체 | R11(포트는 쓰는 쪽이 정의), 현재 데이터와 일치(예약 자체가 없음), 가드 위치가 코드에 남음 | `application/ports.py`, `infrastructure/reservation_lookup.py`, container `create_reservation_lookup` | 확정 |
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
| D56 | #10 공개 범위·에러 | 사용자 결정 | 인증 없이 누구나 조회. 중단·마감·품절 할인, 비활성 상품의 할인, 폐점 상점의 할인 모두 조회되고 `offer.status`·`offer.is_active`로 상태를 표시한다. 에러는 할인 없음 404 하나(401·403 없음) | 사용자 결정 | `get_offer_detail`, router | 확정 |
| D57 | #10 응답 구성 | 명세 §10, 사용자 결정 | `OfferDetailResponse`는 명세 필드 그대로이고 `offer`는 기존 `OfferResponse`를 재사용한다. `latitude`·`longitude`는 catalog `StoreInfo`·`StoreRef`에 추가해 상점에서 받고 null 가능. `cancel_policy`는 중첩 객체 | 명세 필드명 유지(R15), stores가 이미 좌표를 제공 | `schemas.py`, `application/ports.py`, `StoreRef` | 확정 |
| D58 | #10 조회 방식 | 설계 | 할인+상품을 `find_with_product` 한 번의 JOIN으로 읽고 상점은 `StorePort`로 읽는다. 잠금·commit 없음 | 읽기 전용, 5.3절 | `find_with_product`, `get_offer_detail` | 확정 |
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
| - | 스키마 S3(`discount_offers.price` 삭제), S6(`products.created_at`) | 4절, db-schema §5 | S3 삭제 보류(모델은 매핑 안 함), S6 보류 | 4절 | `schema.sql`, `db-schema/SKILL.md` | 팀 확인 |
| - | 명세 #14의 403 문구와 422 표기 | 11절 | D8, D14 | 전역 핸들러 동작 | `docs/reference/catalog.md` | 팀 확인 |

---

## 13. 정합 이슈

### 13.1 stores와의 정합 (stores.md 9절)

| stores 이슈 | 상태 | 내용 |
| --- | --- | --- |
| C1 (StoreInfo에 좌표 없음) | 닫힘 | #10 때문에 catalog `StoreInfo`에 `latitude`, `longitude`를 추가한다. stores의 `Store`가 이미 제공하므로 stores 변경은 없다(2.1절). #8도 같은 필드를 쓴다 |
| C3 (생성 순환) | 열림(후속, 조건부) | container 팩토리 한 방향 구조(9.3절). 폐점 구현 시 stores 읽기/쓰기 서비스 분리(D22)가 필요하며 stores.md가 이를 수용해야 닫힌다 |
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

### 13.3 예약·결제 연계 이슈

| # | 내용 | 영향·해결 |
| --- | --- | --- |
| C9 | `cancel_reservations=false`로 닫힌 할인에 남은 예약(결제 완료 포함)의 픽업·취소·환불을 reservations·payments가 어떻게 다룰지(할인이 CLOSED여도 픽업 가능해야 하는지) 정해지지 않았다. #11 중단과 같은 문제다 | reservations 설계에 요구사항으로 전달: "예약은 할인 `is_active`·`status`와 무관하게 자기 상태로 진행", 예약 생성은 할인 행 잠금 아래에서 `is_active`·`sales_end`를 재확인(5.3, CI-10), 잠금 순서는 상품 → 할인 → 예약 |
| C10 | 할인이 종료돼 폐점이 가능해지고(폐점은 "진행 중 할인이 있으면 불가", 2.3절) 예약이 남은 상점이 폐점될 수 있다 | Q27·C9와 함께 reservations·stores 설계에서 확인 |
| C11 | DB에 "상품당 진행 중 할인 1건" 유니크 제약이 없어 앱 규칙(상품 행 잠금 아래 `find_open_by_product`)에만 의존한다(S7). #12는 할인 1건을 ID로 지정해 중단하므로 이 문제와 무관하다 | 스키마 변경 제안 없음 |
| C12 | **재고·순환**: 예약 취소가 보통 catalog에 재고 복구를 요청한다(reservations → catalog). #12는 catalog → reservations(포트)이므로 어댑터가 reservations 서비스를 쓰고 그 서비스가 catalog 서비스를 쓰면 container에서 생성 순환(R12)이 된다 | 일괄 취소 유스케이스는 재고를 되돌리지 않는 전용 메서드로 만들고(D40) 이 어댑터 경로에서 catalog 서비스를 부르지 않게 한다. 불가피하면 9.3절의 읽기/쓰기 분리 패턴을 쓴다. reservations 설계에 요구사항으로 전달 |
| C13 | 임시 포트 `NoReservationCancel`이 container에 남아 있는 동안 `cancel_reservations=true`도 실제 취소·환불을 하지 않고 `cancelled_reservation_count=0`만 돌려준다 | CI-11(reservations 구현 시 어댑터로 교체). 명세 §12 "확인 필요"에 미연계 상태가 적혀 있다 |
| C14 | #10 `cancel_policy.cancellable_until = pickup_start − 1시간`(D55)은 고객에게 보여주는 약속이다. payments의 위약금·환불 규칙(예약 취소 시 전액 환불 vs 위약금 부과 경계)이 이 시각을 기준으로 해야 화면과 실제 환불이 어긋나지 않는다 | payments·reservations 설계에 요구사항으로 전달: 취소 허용·위약금 경계는 `DiscountOffer.cancel_policy().cancellable_until`(또는 같은 `CANCEL_LEAD_TIME`)에서 가져오고 별도 상수를 두지 않는다. 기준이 바뀌면 `CANCEL_LEAD_TIME`과 `CANCEL_POLICY_DESCRIPTION`(D55)을 함께 고친다 |
